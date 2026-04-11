import streamlit as st
import requests
from db import get_connection
from login import show_login
from utils.refresh import init_refresh, trigger_refresh
from utils.welcome import show_welcome_screen
from config import BASE_URL

# ---------------- IMPORT PAGES ----------------
from frontend.pages.dashboard import show_dashboard
from frontend.pages.add_projection import show_add_projection
from frontend.pages.convert_billing import show_convert_billing
from frontend.pages.reports import show_reports
from frontend.pages.client_access import show_client_access
from frontend.pages.finance_dashboard import show_finance_dashboard
from frontend.pages.billed import show_billed_amount
from frontend.pages.edit_projection import show_edit_projection
from frontend.pages.bulk_upload import show_bulk_upload
from frontend.pages.audit_logs import audit_log_page

# ---------------------------
# Page Config
# ---------------------------
st.set_page_config(page_title="Billing Software", layout="wide")

# ---------------------------
# SESSION DEFAULTS
# ---------------------------
defaults = {
    "logged_in": False,
    "user_id": None,
    "user_name": "",
    "role_id": None,
    "token": None
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---------------------------
# 🔥 RESTORE SESSION FROM TOKEN (FIX)
# ---------------------------
if not st.session_state.get("logged_in"):
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

        except Exception as e:
            print("Token restore failed:", e)

# ---------------------------
# LOGIN GUARD
# ---------------------------
if not st.session_state.get("logged_in"):
    show_login()
    st.stop()

# ---------------------------
# UI HEADER
# ---------------------------
st.title("Billing Software")
st.sidebar.write("Logged in as:", st.session_state.get("user_name"))

# ---------------------------
# LOGOUT (FIXED)
# ---------------------------
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.query_params.clear()   # 🔥 IMPORTANT
    st.rerun()

# ---------------------------
# DB CONNECTION
# ---------------------------
conn = get_connection()

# ---------------------------
# ROLE BASED UI
# ---------------------------
role = st.session_state.get("role_id")

# ---------------- ADMIN ----------------
if role == 1:

    tab0, tab1, tab2, tab3, tab4 = st.tabs([
        "Dashboard", "Reports", "Client Access Control", "Bulk Upload", "Audit Logs"
    ])

    with tab0:
        if st.session_state.get("show_welcome", False):
            show_welcome_screen()
        else:
            show_dashboard(conn)

    with tab1:
        show_reports(conn)

    with tab2:
        show_client_access(conn)

    with tab3:
        show_bulk_upload(conn)

    with tab4:
        audit_log_page(conn)

# ---------------- SUPERVISOR ----------------
elif role == 3:

    tab0, tab1 = st.tabs([
        "Dashboard", "Reports"
    ])

    with tab0:
        show_dashboard(conn)

    with tab1:
        show_reports(conn)

# ---------------- OTHER USERS ----------------
else:

    tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Dashboard", "Add Projection", "View Projection", "Billed", "Reports", "Edit Projection"
    ])

    with tab0:
        show_finance_dashboard(conn)

    with tab1:
        show_add_projection(conn)

    with tab2:
        show_convert_billing(conn)

    with tab3:
        show_billed_amount(conn)

    with tab4:
        show_reports(conn)

    with tab5:
        show_edit_projection(conn)