import streamlit as st
from db import get_connection
from login import show_login
from utils.refresh import init_refresh, trigger_refresh

from _pages_backup.add_projection import show_add_projection
from _pages_backup.convert_billing import show_convert_billing
from _pages_backup.reports import show_reports
from _pages_backup.client_access import show_client_access
from _pages_backup.dashboard import show_dashboard
from _pages_backup.billed import show_billed_amount
from _pages_backup.finance_dashboard import show_finance_dashboard
from _pages_backup.bulk_upload import show_bulk_upload
from _pages_backup.edit_projection import show_edit_projection
from utils.welcome import show_welcome_screen
from _pages_backup.audit_logs import audit_log_page

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
    "role_id": None
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---------------------------
# LOGIN GUARD (STRICT)
# ---------------------------

if not st.session_state.get("logged_in"):
    show_login()
    st.stop()

# ---------------------------
# UI
# ---------------------------

st.title("Billing Software")
st.sidebar.write("Logged in as:", st.session_state.get("user_name"))

# ---------------------------
# LOGOUT (WORKING)
# ---------------------------

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

init_refresh()

if st.sidebar.button("🔄 Refresh Data"):
    trigger_refresh("🔄 Data refreshed")

# ---------------------------
# DB CONNECTION
# ---------------------------

conn = get_connection()

# ---------------------------
# ROLE BASED UI
# ---------------------------

role = st.session_state.get("role_id")

if role == 1:

    tab0, tab1, tab2, tab3, tab4 = st.tabs([
        "Dashboard", "Reports", "Client Access Control", "Bulk Upload","Audit Logs"
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

elif role == 3:

    tab0, tab1 = st.tabs([
        "Dashboard", "Reports"
    ])

    with tab0:
        show_dashboard(conn)

    with tab1:
        show_reports(conn)

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