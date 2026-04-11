from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from backend.db import get_connection, release_connection
from backend.auth.jwt_handler import get_current_user
from utils.audit import log_audit
import pandas as pd

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


@router.post("/convert-billing")
def convert_billing(data: dict, token: str = Depends(oauth2_scheme)):

    user = get_current_user(token)
    user_id = user["user_id"]
    role_id = user["role_id"]

    conn = get_connection()

    try:
        cursor = conn.cursor()

        projection_id = data.get("projection_id")

        if not projection_id:
            raise HTTPException(status_code=400, detail="Projection ID missing")

        # ---------------- FETCH EXISTING ----------------
        df = pd.read_sql(
            "SELECT * FROM billing_entries WHERE id = %s",
            conn,
            params=(projection_id,)
        )

        if df.empty:
            raise HTTPException(status_code=404, detail="Projection not found")

        old_data = df.iloc[0]

        # ---------------- DELETE FLOW ----------------
        if data.get("status") == "Deleted":

            if not data.get("delete_reason"):
                raise HTTPException(status_code=400, detail="Delete reason required")

            # Audit status change
            log_audit(cursor, "billing_entries", projection_id, "status",
                      old_data["status"], "Deleted", "UPDATE",
                      user_id, role_id, "billing", "HIGH")

            # Audit reason
            log_audit(cursor, "billing_entries", projection_id, "reason",
                      old_data.get("reason", ""), data["delete_reason"],
                      "UPDATE", user_id, role_id, "billing", "MEDIUM")

            cursor.execute("""
                UPDATE billing_entries
                SET status = 'Deleted',
                    reason = %s
                WHERE id = %s
            """, (data["delete_reason"], projection_id))

            conn.commit()
            return {"message": "Marked as Deleted"}

        # ---------------- VALIDATION ----------------
        if not data.get("funnel_number") or not data.get("invoice_no"):
            raise HTTPException(status_code=400, detail="Funnel & Invoice required")

        # ---------------- AUDIT (FIELD LEVEL) ----------------

        if old_data["client_billed_amount"] != data.get("amount"):
            log_audit(cursor, "billing_entries", projection_id,
                      "client_billed_amount",
                      old_data["client_billed_amount"], data.get("amount"),
                      "UPDATE", user_id, role_id, "billing", "HIGH")

        if old_data.get("invoice_no") != data.get("invoice_no"):
            log_audit(cursor, "billing_entries", projection_id,
                      "invoice_no",
                      old_data.get("invoice_no"), data.get("invoice_no"),
                      "UPDATE", user_id, role_id, "billing", "HIGH")

        if str(old_data.get("invoice_date")) != str(data.get("invoice_date")):
            log_audit(cursor, "billing_entries", projection_id,
                      "invoice_date",
                      old_data.get("invoice_date"), data.get("invoice_date"),
                      "UPDATE", user_id, role_id, "billing", "MEDIUM")

        # ---------------- UPDATE BILLING ----------------
        cursor.execute("""
            UPDATE billing_entries
            SET
                client_billed_amount = %s,
                funnel_number = %s,
                invoice_no = %s,
                invoice_date = %s,
                expense_type_id = 2
            WHERE id = %s
        """, (
            data.get("amount"),
            data.get("funnel_number"),
            data.get("invoice_no"),
            data.get("invoice_date"),
            projection_id
        ))

        # ---------------- VENDOR AUDIT ----------------
        existing_vendors = pd.read_sql("""
            SELECT vendor_id, amount
            FROM vendor_expenses
            WHERE billing_entry_id = %s
        """, conn, params=(projection_id,))

        # Log removal
        for _, r in existing_vendors.iterrows():
            log_audit(cursor, "vendor_expenses", projection_id,
                      "vendor_removed",
                      f"vendor_id={r['vendor_id']}, amount={r['amount']}",
                      None, "DELETE",
                      user_id, role_id, "vendor", "HIGH")

        # Delete old
        cursor.execute("""
            DELETE FROM vendor_expenses
            WHERE billing_entry_id = %s
        """, (projection_id,))

        # Insert new
        for v in data.get("vendors", []):
            cursor.execute("""
                INSERT INTO vendor_expenses
                (billing_entry_id, vendor_id, amount)
                VALUES (%s,%s,%s)
            """, (projection_id, v["vendor_id"], v["amount"]))

            log_audit(cursor, "vendor_expenses", projection_id,
                      "vendor_added",
                      None,
                      f"vendor_id={v['vendor_id']}, amount={v['amount']}",
                      "INSERT",
                      user_id, role_id, "vendor", "HIGH")

        conn.commit()

        return {"message": "Converted to Billing"}

    finally:
        release_connection(conn)