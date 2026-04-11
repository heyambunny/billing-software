from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer

from backend.db import get_connection, release_connection
from backend.auth.jwt_handler import get_current_user

router = APIRouter()  # 🔥 THIS IS MANDATORY

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


@router.post("/audit-logs")
def get_audit_logs(filters: dict, token: str = Depends(oauth2_scheme)):

    user = get_current_user(token)

    conn = get_connection()

    try:
        cursor = conn.cursor()

        module = filters.get("module")
        action = filters.get("action")
        impact = filters.get("impact")
        date_range = filters.get("date_range")
        limit = filters.get("limit", 10)
        offset = filters.get("offset", 0)

        base_query = """
        FROM audit_logs a
        LEFT JOIN users u ON u.id = a.changed_by
        LEFT JOIN roles r ON r.id = u.role_id
        WHERE 1=1
        """

        params = []

        if module and module != "All":
            base_query += " AND a.module_name = %s"
            params.append(module)

        if action and action != "All":
            base_query += " AND a.action_type = %s"
            params.append(action)

        if impact and impact != "All":
            base_query += " AND a.impact_level = %s"
            params.append(impact)

        if date_range and len(date_range) == 2:
            base_query += " AND a.changed_at BETWEEN %s AND %s"
            params.extend(date_range)

        # -------- COUNT --------
        cursor.execute("SELECT COUNT(*) " + base_query, params)
        total = cursor.fetchone()[0]

        # -------- DATA --------
        data_query = f"""
        SELECT 
            a.table_name,
            a.record_id,
            a.action_type,
            COALESCE(u.name, 'Unknown') as username,
            COALESCE(r.role_name, 'Unknown') as role_name,
            a.user_role,
            a.module_name,
            a.impact_level,
            a.changed_at,
            json_agg(
                json_build_object(
                    'column', a.column_name,
                    'old', a.old_value,
                    'new', a.new_value
                )
            ) AS changes
        {base_query}
        GROUP BY 1,2,3,4,5,6,7,8,9
        ORDER BY a.changed_at DESC
        LIMIT %s OFFSET %s
        """

        cursor.execute(data_query, params + [limit, offset])

        cols = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        data = []
        for row in rows:
            record = dict(zip(cols, row))
            if record.get("changes") is None:
                record["changes"] = []
            data.append(record)

        return {
            "total": total,
            "data": data
        }

    finally:
        release_connection(conn)