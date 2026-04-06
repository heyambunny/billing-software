import streamlit as st
import pandas as pd
import datetime

def get_user_clients(conn, user_id):
    df = pd.read_sql(
        """
        SELECT client_id
        FROM user_client_access
        WHERE user_id = %s
        """,
        conn,
        params=(user_id,)
    )
    return df["client_id"].tolist()

def show_reports(conn):

    st.header("📊 Billing Report")

    role_id = st.session_state.get("role_id", 2)
    user_id = st.session_state.get("user_id", 1)

    # ---------------- ACCESS ----------------
    client_ids = get_user_clients(conn, user_id)

    # ---------------- QUERY ----------------
    query = """
    SELECT
        b.id,
        c.client_name AS "Client",
        p.program_name AS "Program",
        et.expense_type_name AS "ExpenseType",

        b.invoice_month AS "InvoiceMonth",
        b.financial_year AS "FinancialYear",

        b.funnel_number AS "Funnel Number",
        b.invoice_no AS "InvoiceNo",
        b.invoice_date AS "InvoiceDate",

        cat.category_name AS "Category",

        b.invoice_description AS "InvoiceDescription",
        b.client_billed_amount AS "ClientBilledAmount",

        b.projection_date AS "Projection Date",
        u.name AS "Projection Added By",

        MAX(CASE WHEN ve.row_num = 1 THEN v.vendor_name END) AS "Vendor1Name",
        MAX(CASE WHEN ve.row_num = 1 THEN ve.amount END) AS "Vendor1Amount",

        MAX(CASE WHEN ve.row_num = 2 THEN v.vendor_name END) AS "Vendor2Name",
        MAX(CASE WHEN ve.row_num = 2 THEN ve.amount END) AS "Vendor2Amount",

        MAX(CASE WHEN ve.row_num = 3 THEN v.vendor_name END) AS "Vendor3Name",
        MAX(CASE WHEN ve.row_num = 3 THEN ve.amount END) AS "Vendor3Amount",

        MAX(CASE WHEN ve.row_num = 4 THEN v.vendor_name END) AS "Vendor4Name",
        MAX(CASE WHEN ve.row_num = 4 THEN ve.amount END) AS "Vendor4Amount",

        MAX(CASE WHEN ve.row_num = 5 THEN v.vendor_name END) AS "Vendor5Name",
        MAX(CASE WHEN ve.row_num = 5 THEN ve.amount END) AS "Vendor5Amount",

        COALESCE(v_total.total_vendor,0) AS "Total Vendor Amount",
        COALESCE(cn.cn_amount,0) AS "TotalCreditNoteAmount",

        (
            b.client_billed_amount
            - COALESCE(v_total.total_vendor,0)
            - COALESCE(cn.cn_amount,0)
        ) AS "GrossMargin",

        b.status AS "Status",
        b.reason AS "Reason",

        cn.credit_note_no AS "Credit Note No",
        cn.credit_note_date AS "Credit Note Date",
        cn.cn_description AS "CN Description"

    FROM billing_entries b

    LEFT JOIN clients c ON b.client_id = c.id
    LEFT JOIN programs p ON b.program_id = p.id
    LEFT JOIN categories cat ON b.category_id = cat.id
    LEFT JOIN expense_types et ON b.expense_type_id = et.id
    LEFT JOIN users u ON b.created_by_user_id = u.id

    LEFT JOIN (
        SELECT
            billing_entry_id,
            vendor_id,
            amount,
            ROW_NUMBER() OVER (
                PARTITION BY billing_entry_id
                ORDER BY id
            ) AS row_num
        FROM vendor_expenses
    ) ve ON b.id = ve.billing_entry_id

    LEFT JOIN vendors v ON ve.vendor_id = v.id

    LEFT JOIN (
        SELECT billing_entry_id, SUM(amount) AS total_vendor
        FROM vendor_expenses
        GROUP BY billing_entry_id
    ) v_total ON b.id = v_total.billing_entry_id

    LEFT JOIN credit_notes cn ON b.id = cn.billing_entry_id
    """

    params = []

    # ---------------- ACCESS CONTROL ----------------
    if role_id != 1:
        if not client_ids:
            st.warning("No client access assigned.")
            return

        query += " WHERE b.client_id = ANY(%s)"
        params.append(client_ids)

    query += """
    GROUP BY
        b.id,
        c.client_name,
        p.program_name,
        et.expense_type_name,
        cat.category_name,
        u.name,
        v_total.total_vendor,
        cn.cn_amount,
        cn.credit_note_no,
        cn.credit_note_date,
        cn.cn_description

    ORDER BY b.id DESC
    """

    df = pd.read_sql(query, conn, params=params if params else None)

    if df.empty:
        st.info("No data available.")
        return

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

    # ---------------- FORMAT (₹) ----------------
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