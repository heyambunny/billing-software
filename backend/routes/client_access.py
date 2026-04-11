from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer

from backend.db import get_connection, release_connection
from backend.auth.jwt_handler import get_current_user

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


@router.get("/client-access-data")
def get_data(token: str = Depends(oauth2_scheme)):

    get_current_user(token)

    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT id, name FROM users WHERE is_active=TRUE ORDER BY name")
        users = cursor.fetchall()

        cursor.execute("SELECT id, client_name FROM clients ORDER BY client_name")
        clients = cursor.fetchall()

        return {
            "users": [{"id": u[0], "name": u[1]} for u in users],
            "clients": [{"id": c[0], "name": c[1]} for c in clients]
        }

    finally:
        release_connection(conn)


@router.get("/user-clients/{user_id}")
def get_user_clients(user_id: int, token: str = Depends(oauth2_scheme)):

    get_current_user(token)

    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT c.id, c.client_name
            FROM user_client_access uca
            JOIN clients c ON c.id = uca.client_id
            WHERE uca.user_id = %s
        """, (user_id,))

        data = cursor.fetchall()

        return [{"id": d[0], "name": d[1]} for d in data]

    finally:
        release_connection(conn)


@router.post("/assign-client")
def assign_client(data: dict, token: str = Depends(oauth2_scheme)):

    get_current_user(token)

    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO user_client_access (user_id, client_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (data["user_id"], data["client_id"]))

        conn.commit()
        return {"message": "Assigned"}

    finally:
        release_connection(conn)


@router.post("/remove-client")
def remove_client(data: dict, token: str = Depends(oauth2_scheme)):

    get_current_user(token)

    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM user_client_access
            WHERE user_id=%s AND client_id=%s
        """, (data["user_id"], data["client_id"]))

        conn.commit()
        return {"message": "Removed"}

    finally:
        release_connection(conn)