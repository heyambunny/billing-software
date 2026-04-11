from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from backend.db import get_connection, release_connection
from backend.auth.jwt_handler import get_current_user

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


@router.post("/projection")
def add_projection(data: dict, token: str = Depends(oauth2_scheme)):

    user = get_current_user(token)
    user_id = user["user_id"]

    conn = get_connection()

    try:
        cursor = conn.cursor()

        # -------- VALIDATION --------
        if not data.get("description"):
            raise HTTPException(status_code=400, detail="Description required")

        if data.get("amount", 0) <= 0:
            raise HTTPException(status_code=400, detail="Invalid amount")

        # -------- GET EXPENSE TYPE --------
        cursor.execute("""
            SELECT id FROM expense_types
            WHERE expense_type_name = 'Projected'
        """)
        expense_type_id = cursor.fetchone()[0]

        # -------- INSERT BILLING --------
        cursor.execute("""
        INSERT INTO billing_entries
        (
            client_id,
            program_id,
            expense_type_id,
            category_id,
            invoice_description,
            client_billed_amount,
            invoice_month,
            financial_year,
            projection_date,
            status,
            created_by_user_id
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_DATE,'Active',%s)
        RETURNING id
        """,
        (
            data["client_id"],
            data["program_id"],
            expense_type_id,
            data["category_id"],
            data["description"],
            float(data["amount"]),
            data["invoice_month"],
            data["financial_year"],
            user_id
        ))

        billing_id = cursor.fetchone()[0]

        # -------- VENDORS --------
        for vendor in data.get("vendors", []):
            cursor.execute("""
                INSERT INTO vendor_expenses
                (billing_entry_id, vendor_id, amount)
                VALUES (%s,%s,%s)
            """, (
                billing_id,
                vendor["vendor_id"],
                float(vendor["amount"])
            ))

        conn.commit()

        return {"message": "Projection added successfully"}

    finally:
        release_connection(conn)