from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordBearer

from backend.db import get_connection, release_connection
from backend.auth.jwt_handler import create_access_token, get_current_user

import bcrypt

router = APIRouter()

# 🔥 ADD THIS
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


# ---------------- REQUEST SCHEMA ----------------
class LoginRequest(BaseModel):
    email: str
    password: str


# ---------------- LOGIN API ----------------
@router.post("/login")
def login(data: LoginRequest):

    email = data.email.strip()
    password = data.password.strip()

    if not email or not password:
        raise HTTPException(status_code=400, detail="Missing credentials")

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, password_hash, role_id
            FROM users
            WHERE email = %s AND is_active = TRUE
        """, (email,))

        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user_id, name, db_password, role_id = user

        # ---------------- PASSWORD CHECK ----------------
        if not db_password:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if db_password.startswith("$2b$") or db_password.startswith("$2a$"):
            valid = bcrypt.checkpw(password.encode(), db_password.encode())
        else:
            valid = password == db_password

        if not valid:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # ---------------- TOKEN ----------------
        token = create_access_token({
            "user_id": user_id,
            "name": name,
            "role_id": role_id
        })

        return {
            "access_token": token,
            "user": {
                "id": user_id,
                "name": name,
                "role_id": role_id
            }
        }

    except Exception as e:
        print("Login Error:", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        release_connection(conn)


# =================================================
# 🔥 NEW API (ADD THIS BELOW LOGIN)
# =================================================
@router.get("/me")
def get_me(token: str = Depends(oauth2_scheme)):

    try:
        user = get_current_user(token)

        return {
            "id": user["user_id"],
            "name": user["name"],
            "role_id": user["role_id"]
        }

    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")