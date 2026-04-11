import streamlit as st
import pandas as pd
import datetime
from config import BASE_URL

def show_reports(conn):

    st.header("📊 Billing Report")

    # ---------------- API CALL ----------------
    import requests

    token = st.session_state.get("token")

    headers = {
        "Authorization": f"Bearer {token}"
    }

    res = requests.get(
        f"{BASE_URL}/api/reports",
        headers=headers
    )

    if res.status_code != 200:
        st.error("Failed to fetch reports")
        return

    df = pd.DataFrame(res.json())

    if df.empty:
        st.info("No data available.")
        return

    # ---------------- RENAME ----------------
    df.rename(columns={
        "client_name": "Client",
        "program_name": "Program",
        "expense_type_name": "ExpenseType",
        "invoice_month": "InvoiceMonth",
        "financial_year": "FinancialYear",
        "category_name": "Category",
        "invoice_description": "InvoiceDescription",
        "client_billed_amount": "ClientBilledAmount",
        "invoice_no": "InvoiceNo",
        "invoice_date": "InvoiceDate",
        "funnel_number": "Funnel Number",
        "total_vendor": "Total Vendor Amount",
        "total_credit_note": "TotalCreditNoteAmount",
        "gross_margin": "GrossMargin",
        "name": "Projection Added By",

        # 🔥 VENDOR FIELDS
        "vendor1name": "Vendor1Name",
        "vendor1amount": "Vendor1Amount",
        "vendor2name": "Vendor2Name",
        "vendor2amount": "Vendor2Amount",
        "vendor3name": "Vendor3Name",
        "vendor3amount": "Vendor3Amount",
        "vendor4name": "Vendor4Name",
        "vendor4amount": "Vendor4Amount",
        "vendor5name": "Vendor5Name",
        "vendor5amount": "Vendor5Amount",

    }, inplace=True)

    # ---------------- FILTER UI ----------------
    st.subheader("🔎 Filters")

    col1, col2, col3 = st.columns(3)

    with col1:
        client_filter = st.multiselect("Client", sorted(df["Client"].dropna().unique()))
        expense_filter = st.multiselect("Expense Type", sorted(df["ExpenseType"].dropna().unique()))

    with col2:
        category_filter = st.multiselect("Category", sorted(df["Category"].dropna().unique()))
        month_filter = st.multiselect("Invoice Month", sorted(df["InvoiceMonth"].dropna().unique()))

    with col3:
        program_filter = st.multiselect("Program", sorted(df["Program"].dropna().unique()))
        date_range = st.date_input("Invoice Date Range", value=())

    # ---------------- APPLY FILTERS ----------------
    filtered_df = df.copy()

    if client_filter:
        filtered_df = filtered_df[filtered_df["Client"].isin(client_filter)]

    if expense_filter:
        filtered_df = filtered_df[filtered_df["ExpenseType"].isin(expense_filter)]

    if category_filter:
        filtered_df = filtered_df[filtered_df["Category"].isin(category_filter)]

    if month_filter:
        filtered_df = filtered_df[filtered_df["InvoiceMonth"].isin(month_filter)]

    if program_filter:
        filtered_df = filtered_df[filtered_df["Program"].isin(program_filter)]

    # ---------------- DATE FILTER ----------------
    filtered_df["InvoiceDate"] = pd.to_datetime(filtered_df["InvoiceDate"], errors="coerce")

    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date, end_date = date_range

        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date) + pd.Timedelta(days=1)

        filtered_df = filtered_df[
            (filtered_df["InvoiceDate"] >= start_date) &
            (filtered_df["InvoiceDate"] < end_date)
        ]

    # ---------------- FIX DECIMALS ----------------
    numeric_cols = [
        "ClientBilledAmount",
        "Total Vendor Amount",
        "TotalCreditNoteAmount",
        "GrossMargin",
        "Vendor1Amount",
        "Vendor2Amount",
        "Vendor3Amount",
        "Vendor4Amount",
        "Vendor5Amount"
    ]

    for col in numeric_cols:
        if col in filtered_df.columns:
            filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce").round(2)

    # ---------------- COLOR ----------------
    def highlight_billed(row):
        if row["ExpenseType"] == "Billed":
            return ["background-color: #d4edda"] * len(row)
        return [""] * len(row)

    # ---------------- FORMAT ----------------
    styled_df = filtered_df.style.format({
        "ClientBilledAmount": "₹ {:,.2f}",
        "Total Vendor Amount": "₹ {:,.2f}",
        "TotalCreditNoteAmount": "₹ {:,.2f}",
        "GrossMargin": "₹ {:,.2f}"
    }).apply(highlight_billed, axis=1)

    # ---------------- DISPLAY ----------------
    st.dataframe(styled_df, use_container_width=True)

    st.divider()

    # ---------------- DOWNLOAD ----------------
    st.download_button(
        label="⬇️ Download Excel",
        data=filtered_df.to_csv(index=False),
        file_name="billing_report.csv",
        mime="text/csv"
    )