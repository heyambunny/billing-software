import streamlit as st
import pandas as pd
#
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

# ---------------- POPUP ---------------- #
def show_log_details(row):
    with st.dialog("🔍 Log Details", width="large"):
        role = row['user_role'] or row['role_name']

        st.markdown(f"""
        **👤 User:** {row['username']} ({role})  
        **📦 Module:** {row['module_name']}  
        **⚡ Action:** {row['action_type']}  
        **⚠️ Impact:** {row['impact_level']}  
        **🕒 Time:** {row['changed_at']}  
        """)

        st.markdown("### 🔄 Changes")

        for change in row['changes']:
            old_val = change['old'] or "NULL"
            new_val = change['new'] or "NULL"

            st.markdown(f"""
            <div style="
                padding:12px;
                border-radius:8px;
                margin-bottom:10px;
                background:#f8f9fa;
                border:1px solid #eee;
            ">
                <b>{change['column']}</b><br>
                <span style="color:#d32f2f;">{old_val}</span>
                →
                <span style="color:#2e7d32;">{new_val}</span>
            </div>
            """, unsafe_allow_html=True)

# ---------------- MAIN FUNCTION ---------------- #
def audit_log_page(conn):
    st.title("📊 Audit Logs")

    # ---------------- SESSION ---------------- #
    if "page" not in st.session_state:
        st.session_state.page = 1

    PAGE_SIZE = 10

    # ---------------- FILTERS ---------------- #
    col1, col2, col3 = st.columns(3)

    module = col1.selectbox("Module", ["All", "billing", "vendor", "auth"])
    action = col2.selectbox("Action", ["All", "INSERT", "UPDATE", "DELETE"])
    impact = col3.selectbox("Impact", ["All", "LOW", "MEDIUM", "HIGH"])

    date_range = st.date_input("Date Range", [])

    # ---------------- TOTAL COUNT ---------------- #
    def get_total_count():
        query = "SELECT COUNT(*) FROM audit_logs a WHERE 1=1"

        if module != "All":
            query += f" AND a.module_name = '{module}'"
        if action != "All":
            query += f" AND a.action_type = '{action}'"
        if impact != "All":
            query += f" AND a.impact_level = '{impact}'"
        if len(date_range) == 2:
            query += f" AND a.changed_at BETWEEN '{date_range[0]}' AND '{date_range[1]}'"

        return pd.read_sql(query, conn).iloc[0, 0]

    # ---------------- FETCH DATA ---------------- #
    def fetch_data(offset):
        query = f"""
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
        FROM audit_logs a
        LEFT JOIN users u ON u.id = a.changed_by
        LEFT JOIN roles r ON r.id = u.role_id
        WHERE 1=1
        """

        if module != "All":
            query += f" AND a.module_name = '{module}'"
        if action != "All":
            query += f" AND a.action_type = '{action}'"
        if impact != "All":
            query += f" AND a.impact_level = '{impact}'"
        if len(date_range) == 2:
            query += f" AND a.changed_at BETWEEN '{date_range[0]}' AND '{date_range[1]}'"

        query += f"""
        GROUP BY 1,2,3,4,5,6,7,8,9
        ORDER BY a.changed_at DESC
        LIMIT {PAGE_SIZE} OFFSET {offset}
        """

        return pd.read_sql(query, conn)

    # ---------------- LOAD ---------------- #
    if st.button("🔍 Load Logs"):
        st.session_state.page = 1

    total_records = get_total_count()
    total_pages = max(1, (total_records // PAGE_SIZE) + (1 if total_records % PAGE_SIZE else 0))

    offset = (st.session_state.page - 1) * PAGE_SIZE
    df = fetch_data(offset)

    if df.empty:
        st.warning("No logs found")
        return

    df = df.reset_index(drop=True)

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

        st.markdown("""
        <div style="border-bottom:1px solid #eee; margin:6px 0;"></div>
        """, unsafe_allow_html=True)

        col1, col2, col3, col4, col5, col6 = st.columns([3,1,2,1,2,1])

        col1.write(f"{row['table_name']} #{row['record_id']}")
        col2.markdown(action_badge(row["action_type"]), unsafe_allow_html=True)
        col3.write(row["username"])
        col4.markdown(impact_badge(row["impact_level"]), unsafe_allow_html=True)
        col5.write(pd.to_datetime(row["changed_at"]).strftime("%d %b %H:%M"))

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