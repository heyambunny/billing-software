from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from backend.db import get_connection, release_connection
from backend.auth.jwt_handler import get_current_user
from utils.audit import log_audit

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


@router.post("/edit-projection")
def edit_projection(data: dict, token: str = Depends(oauth2_scheme)):

    user = get_current_user(token)
    user_id = user["user_id"]
    role_id = user["role_id"]

    conn = get_connection()

    try:
        cursor = conn.cursor()

        billing_id = data.get("billing_id")

        if not billing_id:
            raise HTTPException(status_code=400, detail="Missing billing id")

        # ---------------- FETCH OLD ----------------
        cursor.execute("""
            SELECT invoice_description, client_billed_amount
            FROM billing_entries
            WHERE id = %s
        """, (billing_id,))

        old = cursor.fetchone()

        if not old:
            raise HTTPException(status_code=404, detail="Projection not found")

        old_description, old_amount = old

        # ---------------- VALIDATION ----------------
        if not data.get("description"):
            raise HTTPException(status_code=400, detail="Description required")

        if data.get("amount", 0) <= 0:
            raise HTTPException(status_code=400, detail="Invalid amount")

        # ---------------- AUDIT ----------------
        if old_description != data["description"]:
            log_audit(cursor, "billing_entries", billing_id,
                      "invoice_description", old_description, data["description"],
                      "UPDATE", user_id, role_id, "Projection", "Low")

        if float(old_amount) != float(data["amount"]):
            log_audit(cursor, "billing_entries", billing_id,
                      "client_billed_amount", old_amount, data["amount"],
                      "UPDATE", user_id, role_id, "Projection", "High")

        # ---------------- UPDATE ----------------
        cursor.execute("""
            UPDATE billing_entries
            SET invoice_description=%s,
                client_billed_amount=%s
            WHERE id=%s
        """, (data["description"], data["amount"], billing_id))

        # ---------------- VENDORS ----------------
        cursor.execute("DELETE FROM vendor_expenses WHERE billing_entry_id=%s", (billing_id,))

        for v in data.get("vendors", []):
            cursor.execute("""
                INSERT INTO vendor_expenses (billing_entry_id, vendor_id, amount)
                VALUES (%s,%s,%s)
            """, (billing_id, v["vendor_id"], v["amount"]))

        conn.commit()

        return {"message": "Projection updated successfully"}

    finally:
        release_connection(conn)