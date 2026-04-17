import streamlit as st
import pandas as pd
from config import BASE_URL

def show_finance_dashboard(conn):

    st.title("💼 Finance Dashboard")

    # ================= API CALL =================
    import requests

    token = st.session_state.get("token")
    headers = {"Authorization": f"Bearer {token}"}

    res = requests.get(
        f"{BASE_URL}/api/finance-dashboard",
        headers=headers
    )

    if res.status_code != 200:
        st.error("Failed to fetch data")
        return

    df = pd.DataFrame(res.json())

    if df.empty:
        st.info("No data available")
        return

    # ================= DATE PARSING =================
    def parse_month(val):
        try:
            return pd.to_datetime(val, format="%b-%y")
        except:
            try:
                return pd.to_datetime(val)
            except:
                return pd.NaT

    df["invoice_month_date"] = df["invoice_month"].apply(parse_month)

    # ================= FILTER PENDING =================
    df = df[
        (df["status"] == "Active") &
        (df["expense_type_id"] == 1)
    ].copy()

    if df.empty:
        st.success("No pending billing 🎉")
        return

    # ================= REMOVE FUTURE =================
    today = pd.Timestamp.today()
    current_year = today.year
    current_month = today.month

    df = df[
        (df["invoice_month_date"].dt.year < current_year) |
        (
            (df["invoice_month_date"].dt.year == current_year) &
            (df["invoice_month_date"].dt.month <= current_month)
        )
    ]

    if df.empty:
        st.success("No pending billing 🎉")
        return

    # ================= KPI =================
    total_pending_amount = df["client_billed_amount"].sum()
    total_pending_count = len(df)

    col1, col2 = st.columns(2)
    col1.metric("Total Pending Amount", f"₹ {total_pending_amount:,.0f}")
    col2.metric("Total Pending Bills", total_pending_count)

    st.divider()

    # ============================================================
    # ================= CLIENT SUMMARY TABLE =====================
    # ============================================================

    st.subheader("📊 Client-wise Pending Summary")

    summary_df = df.groupby("client_name").agg({
        "client_billed_amount": "sum",
        "id": "count"
    }).rename(columns={
        "client_billed_amount": "Pending Amount",
        "id": "Pending Count"
    }).reset_index()

    summary_df = summary_df.sort_values(by="Pending Amount", ascending=False)

    summary_df["Pending Amount"] = pd.to_numeric(
        summary_df["Pending Amount"], errors="coerce"
    ).round(2)

    st.dataframe(
        summary_df.style.format({"Pending Amount": "₹ {:,.0f}"}),
        use_container_width=True
    )

    st.divider()

    # ============================================================
    # ================= DETAILED TABLE ===========================
    # ============================================================

    st.subheader("⏳ Pending Billing Details")

    # -------- AGING LOGIC (CORRECT) --------
    def get_bucket(date):
        if pd.isna(date):
            return "Unknown"

        inv_year = date.year
        inv_month = date.month

        diff = (current_year - inv_year) * 12 + (current_month - inv_month)

        if diff == 0:
            return "Current"
        elif diff == 1:
            return "1 Month Overdue"
        else:
            return "2+ Months Overdue"

    df["aging_bucket"] = df["invoice_month_date"].apply(get_bucket)

    # -------- COLOR --------
    def highlight_rows(row):
        if row["aging_bucket"] == "Current":
            return ["background-color: #d4edda"] * len(row)
        elif row["aging_bucket"] == "1 Month Overdue":
            return ["background-color: #fff3cd"] * len(row)
        else:
            return ["background-color: #f8d7da"] * len(row)

    # -------- TABLE --------
    display_df = df[[
        "client_name",
        "program_name",
        "category_name",
        "client_billed_amount",
        "invoice_month",
        "aging_bucket",
        "invoice_month_date"
    ]].sort_values(by="invoice_month_date")

    display_df = display_df.drop(columns=["invoice_month_date"])

    display_df["client_billed_amount"] = pd.to_numeric(
        display_df["client_billed_amount"], errors="coerce"
    ).round(2)

    styled_df = display_df.style.format({
        "client_billed_amount": "₹ {:,.0f}"
    }).apply(highlight_rows, axis=1)

    st.dataframe(styled_df, use_container_width=True)

    # ================= DOWNLOAD =================
    st.download_button(
        "⬇ Download Details",
        display_df.to_csv(index=False),
        file_name="pending_billing_details.csv"
    )