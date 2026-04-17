# bulk_upload.py

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer
from typing import List
from pydantic import BaseModel

from backend.db import get_connection, release_connection
from backend.auth.jwt_handler import get_current_user

# ---------------- ROUTER ----------------
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


# ---------------- SCHEMAS ----------------
class VendorModel(BaseModel):
    vendor_id: int
    amount: float


class BillingRow(BaseModel):
    client_id: int
    program_id: int
    expense_type_id: int
    category_id: int
    description: str
    amount: float
    invoice_month: str
    financial_year: str
    vendors: List[VendorModel]
    created_by: int


# ---------------- API ----------------
@router.post("/bulk-upload")
def bulk_upload(data: List[BillingRow], token: str = Depends(oauth2_scheme)):

    # Validate user from token
    user = get_current_user(token)

    conn = get_connection()
    try:
        cursor = conn.cursor()

        inserted = 0
        errors = []

        for idx, row in enumerate(data):

            try:
                # -------- Insert into billing_entries --------
                cursor.execute("""
                INSERT INTO billing_entries
                (
                    client_id, program_id, expense_type_id,
                    category_id, invoice_description,
                    client_billed_amount, invoice_month,
                    financial_year, projection_date,
                    status, created_by_user_id
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_DATE,'Active',%s)
                RETURNING id
                """,
                (
                    row.client_id,
                    row.program_id,
                    row.expense_type_id,
                    row.category_id,
                    row.description,
                    row.amount,
                    row.invoice_month,
                    row.financial_year,
                    row.created_by
                ))

                billing_id = cursor.fetchone()[0]

                # -------- Insert vendor expenses --------
                for v in row.vendors:
                    cursor.execute("""
                    INSERT INTO vendor_expenses
                    (billing_entry_id, vendor_id, amount)
                    VALUES (%s,%s,%s)
                    """, (
                        billing_id,
                        v.vendor_id,
                        v.amount
                    ))

                inserted += 1

            except Exception as e:
                errors.append({
                    "row": idx + 1,
                    "error": str(e)
                })

        conn.commit()

        return {
            "inserted": inserted,
            "failed": len(errors),
            "errors": errors
        }

    finally:
        release_connection(conn)