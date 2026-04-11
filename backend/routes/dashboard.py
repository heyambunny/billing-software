from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer
from backend.db import get_connection, release_connection
from backend.auth.jwt_handler import get_current_user

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


@router.get("/dashboard")
def get_dashboard(token: str = Depends(oauth2_scheme)):

    user = get_current_user(token)
    user_id = user["user_id"]
    role_id = user["role_id"]

    conn = get_connection()

    try:
        cursor = conn.cursor()

        query = """
        SELECT
            b.id,
            b.client_id,
            c.client_name,
            b.client_billed_amount,
            b.invoice_month,
            b.financial_year,
            b.status,
            COALESCE(ve.total_vendor, 0) AS vendor_cost,
            COALESCE(cn.cn_amount, 0) AS credit_note
        FROM billing_entries b
        LEFT JOIN clients c ON b.client_id = c.id
        LEFT JOIN (
            SELECT billing_entry_id, SUM(amount) AS total_vendor
            FROM vendor_expenses GROUP BY billing_entry_id
        ) ve ON b.id = ve.billing_entry_id
        LEFT JOIN credit_notes cn ON b.id = cn.billing_entry_id
        WHERE b.status != 'Deleted'
        """

        params = []

        # 🔒 ROLE FILTER
        if role_id != 1:
            cursor.execute(
                "SELECT client_id FROM user_client_access WHERE user_id = %s",
                (user_id,)
            )
            client_ids = [r[0] for r in cursor.fetchall()]

            if not client_ids:
                return []

            query += " AND b.client_id = ANY(%s)"
            params.append(client_ids)

        cursor.execute(query, params if params else None)

        cols = [desc[0] for desc in cursor.description]
        data = [dict(zip(cols, row)) for row in cursor.fetchall()]

        return data

    finally:
        release_connection(conn)