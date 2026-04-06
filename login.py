import streamlit as st
import bcrypt
from db import get_connection


# ---------------- PASSWORD CHECK ----------------
def verify_password(input_password, stored_password):
    try:
        # Handle bcrypt hashed passwords
        if stored_password.startswith("$2b$") or stored_password.startswith("$2a$"):
            return bcrypt.checkpw(input_password.encode(), stored_password.encode())
        else:
            # Fallback for plain text passwords (your current DB case)
            return input_password == stored_password
    except:
        return False


# ---------------- LOGIN FUNCTION ----------------
def show_login():

    conn = get_connection()
    cursor = conn.cursor()

    st.title("🔐 Billing Software Login")

    # ---------------- SESSION INIT ----------------
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if "user_id" not in st.session_state:
        st.session_state["user_id"] = None

    if "user_name" not in st.session_state:
        st.session_state["user_name"] = None

    if "role_id" not in st.session_state:
        st.session_state["role_id"] = None

    # ---------------- LOGIN SCREEN ----------------
    if not st.session_state["logged_in"]:

        email = st.text_input("📧 Email")
        password = st.text_input("🔑 Password", type="password")

        if st.button("Login"):

            if not email or not password:
                st.warning("Please enter email and password")
                return

            # 🔥 Trim to avoid hidden space issues
            email = email.strip()
            password = password.strip()

            cursor.execute("""
                SELECT id, name, password_hash, role_id
                FROM users
                WHERE email = %s AND is_active = TRUE
            """, (email,))

            user = cursor.fetchone()

            if user:

                user_id, name, db_password, role_id = user

                # ✅ PASSWORD CHECK (fixed)
                if verify_password(password, db_password):

                    st.session_state["logged_in"] = True
                    st.session_state["user_id"] = user_id
                    st.session_state["user_name"] = name
                    st.session_state["role_id"] = role_id

                    st.success("Login successful ✅")
                    st.session_state.logged_in = True
                    st.session_state.user_name = name   # or whatever variable you have
                    st.session_state.show_welcome = True
                    st.rerun()

                else:
                    st.error("Invalid credentials ❌")

            else:
                st.error("Invalid credentials ❌")

    # ---------------- AFTER LOGIN ----------------
    else:
        st.success(f"Welcome {st.session_state['user_name']} 👋")

        if st.button("Logout"):
            logout()


# ---------------- LOGOUT ----------------
def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()