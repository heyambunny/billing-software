from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer

from backend.db import get_connection, release_connection
from backend.auth.jwt_handler import get_current_user

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


@router.post("/bulk-upload")
def bulk_upload(data: list, token: str = Depends(oauth2_scheme)):

    user = get_current_user(token)

    conn = get_connection()
    try:
        cursor = conn.cursor()

        inserted = 0

        for row in data:

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
                row["client_id"],
                row["program_id"],
                row["expense_type_id"],
                row["category_id"],
                row["description"],
                row["amount"],
                row["invoice_month"],
                row["financial_year"],
                row["created_by"]
            ))

            billing_id = cursor.fetchone()[0]

            for v_id, amt in row["vendors"]:
                cursor.execute("""
                INSERT INTO vendor_expenses
                (billing_entry_id, vendor_id, amount)
                VALUES (%s,%s,%s)
                """, (billing_id, v_id, amt))

            inserted += 1

        conn.commit()

        return {"message": f"{inserted} rows inserted"}

    finally:
        release_connection(conn)