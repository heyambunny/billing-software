import streamlit as st
import pandas as pd
import plotly.express as px


# ================= ROLE FILTER =================
def get_allowed_clients(conn):
    role_id = st.session_state.get("role_id")
    user_id = st.session_state.get("user_id")

    if role_id == 1:  # Admin
        return None

    df = pd.read_sql(
        "SELECT client_id FROM user_client_access WHERE user_id = %s",
        conn,
        params=(user_id,)
    )

    return df["client_id"].tolist()


def format_inr(value):
    return f"₹ {value:,.0f}"


def show_dashboard(conn):

    st.set_page_config(layout="wide")
    st.title("📊 Management Dashboard")

    # ---------------- LOAD DATA ----------------

    query = """
    SELECT
        b.id,
        c.client_name,
        b.client_billed_amount,
        b.invoice_month,
        b.financial_year,
        b.expense_type_id,
        b.status,

        COALESCE(ve.total_vendor, 0) AS vendor_cost,
        COALESCE(cn.cn_amount, 0) AS credit_note

    FROM billing_entries b
    LEFT JOIN clients c ON b.client_id = c.id

    LEFT JOIN (
        SELECT billing_entry_id, SUM(amount) AS total_vendor
        FROM vendor_expenses
        GROUP BY billing_entry_id
    ) ve ON b.id = ve.billing_entry_id

    LEFT JOIN credit_notes cn ON b.id = cn.billing_entry_id

    WHERE b.status != 'Deleted'
    """

    allowed_clients = get_allowed_clients(conn)

    if allowed_clients is None:
        df = pd.read_sql(query, conn)
    else:
        query += " AND b.client_id = ANY(%s)"
        df = pd.read_sql(query, conn, params=(allowed_clients,))

    if df.empty:
        st.warning("No data available")
        return

    # ---------------- DATE ----------------

    df["invoice_month_parsed"] = pd.to_datetime(
        df["invoice_month"], format="%b-%y", errors="coerce"
    )

    df["month_num"] = df["invoice_month_parsed"].dt.month

    def get_quarter(m):
        if pd.isna(m):
            return "Unknown"
        if m in [4, 5, 6]:
            return "Q1"
        elif m in [7, 8, 9]:
            return "Q2"
        elif m in [10, 11, 12]:
            return "Q3"
        else:
            return "Q4"

    df["quarter"] = df["month_num"].apply(get_quarter)

    # ---------------- FILTERS ----------------

    st.sidebar.header("🔍 Filters")

    fy_filter = st.sidebar.multiselect(
        "Financial Year",
        sorted(df["financial_year"].dropna().unique())
    )

    client_filter = st.sidebar.multiselect(
        "Client",
        sorted(df["client_name"].dropna().unique())
    )

    if fy_filter:
        df = df[df["financial_year"].isin(fy_filter)]

    if client_filter:
        df = df[df["client_name"].isin(client_filter)]

    # ---------------- CALCULATIONS ----------------

    df["gross_margin"] = (
        df["client_billed_amount"]
        - df["vendor_cost"]
        - df["credit_note"]
    )

    total_billing = df["client_billed_amount"].sum()
    total_vendor = df["vendor_cost"].sum()
    total_cn = df["credit_note"].sum()
    total_margin = df["gross_margin"].sum()

    # ---------------- EXECUTIVE METRICS ----------------

    projection_df = df[df["expense_type_id"] == 1]

    billed_df = df[
        (df["expense_type_id"] == 1) &
        (df["status"] == "Billed")
    ]

    pending_df = df[
        (df["expense_type_id"] == 1) &
        (df["status"] != "Billed")
    ]

    total_projection = projection_df["client_billed_amount"].sum()
    total_billed = billed_df["client_billed_amount"].sum()
    total_pending = pending_df["client_billed_amount"].sum()

    conversion_rate = (total_billed / total_projection * 100) if total_projection else 0

    # ---------------- CLIENT SUMMARY ----------------

    client_df = df.groupby("client_name").agg({
        "client_billed_amount": "sum",
        "vendor_cost": "sum",
        "credit_note": "sum",
        "gross_margin": "sum"
    }).reset_index()

    client_df["margin_percent"] = (
        client_df["gross_margin"] / client_df["client_billed_amount"] * 100
    ).round(2)

    # ---------------- KEY INSIGHTS ----------------

    st.subheader("📌 Key Insights")

    col1, col2, col3 = st.columns(3)

    if not client_df.empty:
        top_client = client_df.sort_values("client_billed_amount", ascending=False).iloc[0]
        low_margin = client_df.sort_values("gross_margin").iloc[0]

        col1.success(f"🏆 Top Client: {top_client['client_name']}")
        col2.error(f"⚠️ Lowest Margin: {low_margin['client_name']}")

    if conversion_rate < 50:
        col3.error("🚨 Low Billing Conversion")
    elif conversion_rate < 75:
        col3.warning("⚠️ Moderate Conversion")
    else:
        col3.success("✅ Strong Conversion")

    st.divider()

    # ---------------- KPI UI ----------------

    st.subheader("🚀 Executive Overview")

    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Projection", format_inr(total_projection))
    col2.metric("✅ Billed", format_inr(total_billed), delta=f"{conversion_rate:.1f}%")
    col3.metric("⏳ Pending", format_inr(total_pending))

    col4, col5, col6 = st.columns(3)
    col4.metric("💸 Vendor Cost", format_inr(total_vendor))
    col5.metric("📉 Credit Notes", format_inr(total_cn))
    col6.metric("📈 Net Margin", format_inr(total_margin))

    st.divider()

    # ---------------- FUNNEL ----------------

    st.subheader("📊 Revenue Funnel")

    funnel_df = pd.DataFrame({
        "Stage": ["Projection", "Billed", "Pending"],
        "Amount": [total_projection, total_billed, total_pending]
    })

    fig_funnel = px.funnel(funnel_df, x="Amount", y="Stage")
    st.plotly_chart(fig_funnel, use_container_width=True)

    # ---------------- CLIENT PERFORMANCE ----------------

    st.subheader("📊 Client Performance")

    fig_client = px.bar(client_df, x="client_name", y="client_billed_amount")
    st.plotly_chart(fig_client, use_container_width=True)

    # ---------------- VENDOR ANALYSIS (FIXED + FUN) ----------------

    st.subheader("💰 Vendor Analysis")

    if allowed_clients is None:
        vendor_query = """
        SELECT v.vendor_name, SUM(ve.amount) AS total_payout
        FROM vendor_expenses ve
        LEFT JOIN vendors v ON ve.vendor_id = v.id
        LEFT JOIN billing_entries b ON ve.billing_entry_id = b.id
        WHERE b.status != 'Deleted'
        GROUP BY v.vendor_name
        ORDER BY total_payout DESC
        """
        vendor_df = pd.read_sql(vendor_query, conn)

    else:
        vendor_query = """
        SELECT v.vendor_name, SUM(ve.amount) AS total_payout
        FROM vendor_expenses ve
        LEFT JOIN vendors v ON ve.vendor_id = v.id
        LEFT JOIN billing_entries b ON ve.billing_entry_id = b.id
        WHERE b.status != 'Deleted'
          AND b.client_id = ANY(%s)
        GROUP BY v.vendor_name
        ORDER BY total_payout DESC
        """
        vendor_df = pd.read_sql(vendor_query, conn, params=(allowed_clients,))

    if not vendor_df.empty:
        fig_vendor = px.pie(
            vendor_df,
            names="vendor_name",
            values="total_payout",
            hole=0.5
        )
        st.plotly_chart(fig_vendor, use_container_width=True)
    else:
        st.info("No vendor expenses found 😅")
        st.markdown("### 💤 Vendors are chilling... no activity!")
        st.image(
            "https://i.giphy.com/media/3o7btPCcdNniyf0ArS/giphy.gif",
            use_container_width=True
        )

    # ---------------- QUARTER SUMMARY ----------------

    st.subheader("📅 Quarter-wise Summary")

    quarter_df = df.groupby(["financial_year", "quarter"]).agg({
        "client_billed_amount": "sum",
        "vendor_cost": "sum",
        "credit_note": "sum",
        "gross_margin": "sum"
    }).reset_index()

    quarter_df["margin_percent"] = (
        quarter_df["gross_margin"] / quarter_df["client_billed_amount"] * 100
    ).round(2)

    st.dataframe(quarter_df, use_container_width=True)

    # ---------------- CLIENT TABLE ----------------

    st.subheader("📋 Client Summary")
    st.dataframe(client_df, use_container_width=True)

    # ---------------- DOWNLOAD ----------------

    st.download_button(
        "⬇ Download Report",
        client_df.to_csv(index=False),
        file_name="dashboard_report.csv"
    )