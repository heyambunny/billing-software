from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from backend.db import get_connection, release_connection
from backend.auth.jwt_handler import get_current_user

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


@router.post("/update-billed")
def update_billed(data: dict, token: str = Depends(oauth2_scheme)):

    user = get_current_user(token)

    conn = get_connection()

    try:
        cursor = conn.cursor()

        billing_id = data.get("billing_id")

        if not billing_id:
            raise HTTPException(status_code=400, detail="Missing billing id")

        # -------- CREDIT NOTE UPSERT --------
        cn = data.get("credit_note")

        if cn and cn.get("cn_amount", 0) > 0:

            cursor.execute("""
                SELECT id FROM credit_notes
                WHERE billing_entry_id = %s
                LIMIT 1
            """, (billing_id,))

            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE credit_notes
                    SET credit_note_no=%s,
                        credit_note_date=%s,
                        cn_amount=%s,
                        cn_description=%s
                    WHERE id=%s
                """, (
                    cn["credit_note_no"],
                    cn["credit_note_date"],
                    cn["cn_amount"],
                    cn["cn_description"],
                    existing[0]
                ))
            else:
                cursor.execute("""
                    INSERT INTO credit_notes
                    (billing_entry_id, credit_note_no, credit_note_date, cn_amount, cn_description)
                    VALUES (%s,%s,%s,%s,%s)
                """, (
                    billing_id,
                    cn["credit_note_no"],
                    cn["credit_note_date"],
                    cn["cn_amount"],
                    cn["cn_description"]
                ))

        # -------- VENDOR UPDATE --------
        cursor.execute("""
            DELETE FROM vendor_expenses
            WHERE billing_entry_id = %s
        """, (billing_id,))

        for v in data.get("vendors", []):
            cursor.execute("""
                INSERT INTO vendor_expenses
                (billing_entry_id, vendor_id, amount)
                VALUES (%s,%s,%s)
            """, (billing_id, v["vendor_id"], v["amount"]))

        conn.commit()

        return {"message": "Updated successfully"}

    finally:
        release_connection(conn)