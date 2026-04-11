import streamlit as st
import requests
from config import BASE_URL

# ---------------- LOGIN FUNCTION ----------------
def show_login():

    st.title("🔐 Billing Software Login")

    # ---------------- SESSION INIT ----------------
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if "token" not in st.session_state:
        st.session_state["token"] = None

    if "user_id" not in st.session_state:
        st.session_state["user_id"] = None

    if "user_name" not in st.session_state:
        st.session_state["user_name"] = None

    if "role_id" not in st.session_state:
        st.session_state["role_id"] = None

    # ---------------- RESTORE SESSION ----------------
    if not st.session_state["logged_in"]:
        token = st.query_params.get("token")

        if token:
            try:
                res = requests.get(
                    f"{BASE_URL}/api/me",
                    headers={"Authorization": f"Bearer {token}"}
                )

                if res.status_code == 200:
                    user = res.json()

                    st.session_state["token"] = token
                    st.session_state["user_id"] = user["id"]
                    st.session_state["user_name"] = user["name"]
                    st.session_state["role_id"] = user["role_id"]
                    st.session_state["logged_in"] = True

                    st.rerun()

            except:
                pass

    # ---------------- LOGIN SCREEN ----------------
    if not st.session_state["logged_in"]:

        email = st.text_input("📧 Email")
        password = st.text_input("🔑 Password", type="password")

        if st.button("Login"):

            if not email or not password:
                st.warning("Please enter email and password")
                return

            try:
                res = requests.post(
                    f"{BASE_URL}/api/login",
                    json={"email": email.strip(), "password": password.strip()}
                )

                if res.status_code != 200:
                    st.error("Invalid credentials ❌")
                    return

                data = res.json()
                token = data["access_token"]

                # ✅ STORE SESSION
                st.session_state["token"] = token
                st.session_state["user_id"] = data["user"]["id"]
                st.session_state["user_name"] = data["user"]["name"]
                st.session_state["role_id"] = data["user"]["role_id"]
                st.session_state["logged_in"] = True

                # 🔥 STORE TOKEN IN URL
                st.query_params["token"] = token

                st.success("Login successful ✅")
                st.rerun()

            except Exception as e:
                st.error(f"Error connecting to backend: {e}")

    # ---------------- AFTER LOGIN ----------------
    else:
        st.success(f"Welcome {st.session_state['user_name']} 👋")

        if st.button("Logout"):
            logout()


# ---------------- LOGOUT ----------------
def logout():
    st.session_state.clear()
    st.query_params.clear()
    st.rerun()