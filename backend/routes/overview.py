from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer

from backend.db import get_connection, release_connection
from backend.auth.jwt_handler import get_current_user

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/login"
)


# =========================================================
# SUPERVISOR OVERVIEW
# =========================================================

@router.get("/supervisor-overview")
def supervisor_overview(
    token: str = Depends(oauth2_scheme)
):

    user = get_current_user(token)

    role_id = user["role_id"]

    # =====================================================
    # ADMIN ACCESS ONLY
    # =====================================================

    if role_id != 1:
        return {
            "success": False,
            "message": "Unauthorized access"
        }

    conn = get_connection()

    try:

        cursor = conn.cursor()

        query = """

        SELECT

            u.id AS supervisor_id,

            u.name AS supervisor_name,

            COUNT(
                DISTINCT b.client_id
            ) AS total_clients,

            COALESCE(
                SUM(
                    b.client_billed_amount
                ),
                0
            ) AS total_billing,

            COALESCE(
                SUM(
                    ve.total_vendor_expense
                ),
                0
            ) AS total_vendor_expense,

            COALESCE(
                SUM(
                    cn.total_credit_note
                ),
                0
            ) AS total_credit_notes,

            (

                COALESCE(
                    SUM(
                        b.client_billed_amount
                    ),
                    0
                )

                -

                COALESCE(
                    SUM(
                        ve.total_vendor_expense
                    ),
                    0
                )

                -

                COALESCE(
                    SUM(
                        cn.total_credit_note
                    ),
                    0
                )

            ) AS total_margin,

            CASE

                WHEN COALESCE(
                    SUM(
                        b.client_billed_amount
                    ),
                    0
                ) = 0

                THEN 0

                ELSE ROUND(

                    (

                        (

                            COALESCE(
                                SUM(
                                    b.client_billed_amount
                                ),
                                0
                            )

                            -

                            COALESCE(
                                SUM(
                                    ve.total_vendor_expense
                                ),
                                0
                            )

                            -

                            COALESCE(
                                SUM(
                                    cn.total_credit_note
                                ),
                                0
                            )

                        )

                        /

                        SUM(
                            b.client_billed_amount
                        )

                    ) * 100,

                    2

                )

            END AS margin_percentage

        FROM users u

        INNER JOIN user_client_access uca
            ON u.id = uca.user_id

        INNER JOIN billing_entries b
            ON uca.client_id = b.client_id

        LEFT JOIN (

            SELECT
                billing_entry_id,
                SUM(amount) AS total_vendor_expense
            FROM vendor_expenses
            GROUP BY billing_entry_id

        ) ve
            ON b.id = ve.billing_entry_id

        LEFT JOIN (

            SELECT
                billing_entry_id,
                SUM(cn_amount) AS total_credit_note
            FROM credit_notes
            GROUP BY billing_entry_id

        ) cn
            ON b.id = cn.billing_entry_id

        WHERE
            u.role_id = 3
            AND u.is_active = TRUE
            AND b.status = 'Active'

        GROUP BY
            u.id,
            u.name

        ORDER BY
            total_margin DESC

        """

        cursor.execute(query)

        cols = [
            desc[0]
            for desc in cursor.description
        ]

        data = [
            dict(zip(cols, row))
            for row in cursor.fetchall()
        ]

        return {
            "success": True,
            "data": data
        }

    except Exception as e:

        return {
            "success": False,
            "message": str(e)
        }

    finally:

        release_connection(conn)


# =========================================================
# SUPERVISOR CLIENT BREAKDOWN
# =========================================================

@router.get("/supervisor-client-breakdown")
def supervisor_client_breakdown(
    token: str = Depends(oauth2_scheme)
):

    user = get_current_user(token)

    role_id = user["role_id"]

    if role_id != 1:
        return {
            "success": False,
            "message": "Unauthorized access"
        }

    conn = get_connection()

    try:

        cursor = conn.cursor()

        query = """

        SELECT

            u.id AS supervisor_id,

            u.name AS supervisor_name,

            c.client_name,

            COALESCE(
                SUM(
                    b.client_billed_amount
                ),
                0
            ) AS total_billing,

            COALESCE(
                SUM(
                    ve.total_vendor_expense
                ),
                0
            ) AS total_vendor_expense,

            COALESCE(
                SUM(
                    cn.total_credit_note
                ),
                0
            ) AS total_credit_notes,

            (

                COALESCE(
                    SUM(
                        b.client_billed_amount
                    ),
                    0
                )

                -

                COALESCE(
                    SUM(
                        ve.total_vendor_expense
                    ),
                    0
                )

                -

                COALESCE(
                    SUM(
                        cn.total_credit_note
                    ),
                    0
                )

            ) AS total_margin

        FROM users u

        INNER JOIN user_client_access uca
            ON u.id = uca.user_id

        INNER JOIN clients c
            ON uca.client_id = c.id

        INNER JOIN billing_entries b
            ON c.id = b.client_id

        LEFT JOIN (

            SELECT
                billing_entry_id,
                SUM(amount) AS total_vendor_expense
            FROM vendor_expenses
            GROUP BY billing_entry_id

        ) ve
            ON b.id = ve.billing_entry_id

        LEFT JOIN (

            SELECT
                billing_entry_id,
                SUM(cn_amount) AS total_credit_note
            FROM credit_notes
            GROUP BY billing_entry_id

        ) cn
            ON b.id = cn.billing_entry_id

        WHERE
            u.role_id = 3
            AND u.is_active = TRUE
            AND b.status = 'Active'

        GROUP BY
            u.id,
            u.name,
            c.client_name

        ORDER BY
            u.name,
            total_billing DESC

        """

        cursor.execute(query)

        cols = [
            desc[0]
            for desc in cursor.description
        ]

        data = [
            dict(zip(cols, row))
            for row in cursor.fetchall()
        ]

        return {
            "success": True,
            "data": data
        }

    except Exception as e:

        return {
            "success": False,
            "message": str(e)
        }

    finally:

        release_connection(conn)