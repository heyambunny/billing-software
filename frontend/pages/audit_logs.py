import streamlit as st
import pandas as pd
import requests
from config import BASE_URL

# ---------------- BADGES ---------------- #
def impact_badge(level):
    colors = {
        "HIGH": "#d32f2f",
        "MEDIUM": "#f9a825",
        "LOW": "#2e7d32"
    }
    color = colors.get(level, "#999")

    return f"""
    <span style="
        background:{color}20;
        color:{color};
        padding:4px 10px;
        border-radius:20px;
        font-size:12px;
        font-weight:600;
    ">
        {level}
    </span>
    """

def action_badge(action):
    colors = {
        "INSERT": "#2e7d32",
        "UPDATE": "#1565c0",
        "DELETE": "#c62828"
    }
    color = colors.get(action, "#555")

    return f"""
    <span style="
        background:{color}20;
        color:{color};
        padding:4px 10px;
        border-radius:20px;
        font-size:12px;
        font-weight:600;
    ">
        {action}
    </span>
    """

# ---------------- DETAILS (FIXED) ---------------- #
def show_log_details(row):

    with st.expander("🔍 Log Details", expanded=True):

        role = row.get('user_role') or row.get('role_name')

        st.markdown(f"""
        **👤 User:** {row.get('username')} ({role})  
        **📦 Module:** {row.get('module_name')}  
        **⚡ Action:** {row.get('action_type')}  
        **⚠️ Impact:** {row.get('impact_level')}  
        **🕒 Time:** {row.get('changed_at')}  
        """)

        st.markdown("### 🔄 Changes")

        changes = row.get("changes", [])

        if not isinstance(changes, list):
            changes = []

        for change in changes:
            old_val = change.get('old') or "NULL"
            new_val = change.get('new') or "NULL"

            st.markdown(f"""
            <div style="
                padding:12px;
                border-radius:8px;
                margin-bottom:10px;
                background:#f8f9fa;
                border:1px solid #eee;
            ">
                <b>{change.get('column')}</b><br>
                <span style="color:#d32f2f;">{old_val}</span>
                →
                <span style="color:#2e7d32;">{new_val}</span>
            </div>
            """, unsafe_allow_html=True)

# ---------------- MAIN FUNCTION ---------------- #
def audit_log_page(conn):

    st.title("📊 Audit Logs")

    if "page" not in st.session_state:
        st.session_state.page = 1

    PAGE_SIZE = 10

    # ---------------- FILTERS ---------------- #
    col1, col2, col3 = st.columns(3)

    module = col1.selectbox("Module", ["All", "billing", "vendor", "auth"])
    action = col2.selectbox("Action", ["All", "INSERT", "UPDATE", "DELETE"])
    impact = col3.selectbox("Impact", ["All", "LOW", "MEDIUM", "HIGH"])

    date_range = st.date_input("Date Range", [])

    if st.button("🔍 Load Logs"):
        st.session_state.page = 1

    # ---------------- API CALL ---------------- #
    token = st.session_state.get("token")

    payload = {
        "module": module,
        "action": action,
        "impact": impact,
        "date_range": date_range if len(date_range) == 2 else None,
        "limit": PAGE_SIZE,
        "offset": (st.session_state.page - 1) * PAGE_SIZE
    }

    headers = {
        "Authorization": f"Bearer {token}"
    }

    res = requests.post(
        f"{BASE_URL}/api/audit-logs",
        json=payload,
        headers=headers
    )

    if res.status_code != 200:
        st.error("Failed to fetch logs")
        return

    response = res.json()

    total_records = response.get("total", 0)
    df = pd.DataFrame(response.get("data", []))

    total_pages = max(1, (total_records // PAGE_SIZE) + (1 if total_records % PAGE_SIZE else 0))

    if df.empty:
        st.warning("No logs found")
        return

    df = df.reset_index(drop=True)

    # ---------------- DOWNLOAD BUTTON ---------------- #
    st.download_button(
        "⬇ Download Audit Logs",
        df.to_csv(index=False),
        file_name="audit_logs.csv"
    )

    # ---------------- HEADER ---------------- #
    st.subheader("📋 Audit Logs")

    header = st.columns([3,1,2,1,2,1])
    header[0].markdown("**Entity**")
    header[1].markdown("**Action**")
    header[2].markdown("**User**")
    header[3].markdown("**Impact**")
    header[4].markdown("**Time**")
    header[5].markdown("")

    # ---------------- ROWS ---------------- #
    for i, row in df.iterrows():

        st.markdown(
            "<div style='border-bottom:1px solid #eee; margin:6px 0;'></div>",
            unsafe_allow_html=True
        )

        col1, col2, col3, col4, col5, col6 = st.columns([3,1,2,1,2,1])

        col1.write(f"{row.get('table_name')} #{row.get('record_id')}")
        col2.markdown(action_badge(row.get("action_type")), unsafe_allow_html=True)
        col3.write(row.get("username"))
        col4.markdown(impact_badge(row.get("impact_level")), unsafe_allow_html=True)

        try:
            time_val = pd.to_datetime(row.get("changed_at")).strftime("%d %b %H:%M")
        except:
            time_val = row.get("changed_at")

        col5.write(time_val)

        if col6.button("👁️", key=f"view_{i}"):
            show_log_details(row)

    # ---------------- PAGINATION ---------------- #
    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    if col1.button("⬅️ Prev") and st.session_state.page > 1:
        st.session_state.page -= 1

    col2.markdown(
        f"<div style='text-align:center;'>Page {st.session_state.page} of {total_pages}</div>",
        unsafe_allow_html=True
    )

    if col3.button("Next ➡️") and st.session_state.page < total_pages:
        st.session_state.page += 1