from datetime import datetime, time
import streamlit as st
import pandas as pd
from db import get_connection

st.set_page_config(page_title="Billing Software", layout="wide")

st.title("Billing Software")

conn = get_connection()

tab1, tab2, tab3 = st.tabs([
    "Add Projection",
    "Convert Projection to Billing",
    "Reports"
])

# ---------------------------------------------------
# TAB 1 — ADD PROJECTION
# ---------------------------------------------------
# -----------------------------------------
# TAB 1 — ADD PROJECTION
# -----------------------------------------

from datetime import datetime
import pandas as pd
import streamlit as st

with tab1:

    st.header("Add Projection")

    # -----------------------------------------
    # LOAD MASTER TABLES
    # -----------------------------------------

    clients = pd.read_sql(
        "SELECT id, client_name FROM clients ORDER BY client_name",
        conn
    )

    programs = pd.read_sql(
        "SELECT id, program_name, client_id FROM programs ORDER BY program_name",
        conn
    )

    categories = pd.read_sql(
        "SELECT id, category_name FROM categories ORDER BY category_name",
        conn
    )

    vendors = pd.read_sql(
        "SELECT id, vendor_name FROM vendors ORDER BY vendor_name",
        conn
    )

    # -----------------------------------------
    # CLIENT
    # -----------------------------------------

    client_name = st.selectbox(
        "Client",
        clients["client_name"]
    )

    client_id = clients[
        clients["client_name"] == client_name
    ]["id"].values[0]

    # -----------------------------------------
    # PROGRAM (FILTER BY CLIENT)
    # -----------------------------------------

    client_programs = programs[
        programs["client_id"] == client_id
    ]

    program_name = st.selectbox(
        "Program",
        client_programs["program_name"]
    )

    program_id = client_programs[
        client_programs["program_name"] == program_name
    ]["id"].values[0]

    # -----------------------------------------
    # CATEGORY
    # -----------------------------------------

    category_name = st.selectbox(
        "Category",
        categories["category_name"]
    )

    category_id = categories[
        categories["category_name"] == category_name
    ]["id"].values[0]

    # -----------------------------------------
    # INVOICE MONTH
    # -----------------------------------------

    months = [
        "Apr","May","Jun","Jul","Aug","Sep",
        "Oct","Nov","Dec","Jan","Feb","Mar"
    ]

    current_year = datetime.now().year

    month_options = [
        f"{m}-{str(current_year)[2:]}" for m in months
    ]

    invoice_month = st.selectbox(
        "Invoice Month",
        month_options
    )

    # -----------------------------------------
    # FINANCIAL YEAR AUTO
    # -----------------------------------------

    year = int("20" + invoice_month.split("-")[1])

    if invoice_month.startswith(("Jan","Feb","Mar")):
        financial_year = f"FY {year-1}-{year}"
    else:
        financial_year = f"FY {year}-{year+1}"

    st.write("Financial Year:", financial_year)

    # -----------------------------------------
    # DESCRIPTION
    # -----------------------------------------

    description = st.text_area(
        "Invoice Description"
    )

    # -----------------------------------------
    # CLIENT AMOUNT
    # -----------------------------------------

    amount = st.number_input(
        "Client Billed Amount",
        min_value=0.0
    )

    # -----------------------------------------
    # VENDOR SECTION
    # -----------------------------------------

    st.subheader("Vendor Expenses")

    if "vendor_rows" not in st.session_state:
        st.session_state.vendor_rows = 1

    col1, col2 = st.columns(2)

    if col1.button("Add Vendor"):
        st.session_state.vendor_rows += 1

    if col2.button("Remove Vendor") and st.session_state.vendor_rows > 1:
        st.session_state.vendor_rows -= 1

    vendor_data = []

    for i in range(st.session_state.vendor_rows):

        vcol1, vcol2 = st.columns(2)

        vendor_name = vcol1.selectbox(
            f"Vendor {i+1}",
            ["None"] + list(vendors["vendor_name"]),
            key=f"vendor_{i}"
        )

        vendor_amount = vcol2.number_input(
            f"Vendor {i+1} Amount",
            min_value=0.0,
            key=f"vendor_amount_{i}"
        )

        if vendor_name != "None" and vendor_amount > 0:

            vendor_id = vendors[
                vendors["vendor_name"] == vendor_name
            ]["id"].values[0]

            vendor_data.append((vendor_id, vendor_amount))

    # -----------------------------------------
    # SAVE BUTTON
    # -----------------------------------------

    if st.button("Save Projection"):

        cursor = conn.cursor()

        cursor.execute("""
        SELECT id FROM expense_types
        WHERE expense_type_name = 'Projected'
        """)

        expense_type_id = cursor.fetchone()[0]

        cursor.execute("""
        INSERT INTO billing_entries
        (
            client_id,
            program_id,
            expense_type_id,
            category_id,
            invoice_description,
            client_billed_amount,
            invoice_month,
            financial_year,
            projection_date,
            status
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_DATE,'Active')
        RETURNING id
        """,
        (
            int(client_id),
            int(program_id),
            int(expense_type_id),
            int(category_id),
            description,
            float(amount),
            invoice_month,
            financial_year
        ))

        billing_id = cursor.fetchone()[0]

        # SAVE VENDOR EXPENSES

        for vendor_id, vendor_amount in vendor_data:

            cursor.execute("""
            INSERT INTO vendor_expenses
            (billing_entry_id, vendor_id, amount)
            VALUES (%s,%s,%s)
            """,
            (
                int(billing_id),
                int(vendor_id),
                float(vendor_amount)
            ))

        conn.commit()

        st.success("Projection added successfully")

        st.session_state.vendor_rows = 1

        st.rerun()

# ---------------------------------------------------
# TAB 2 — CONVERT PROJECTION → BILLING
# ---------------------------------------------------

with tab2:

    st.header("Convert Projection → Billing")

    # ----------------------------
    # FILTERS
    # ----------------------------

    clients = pd.read_sql(
        "SELECT id, client_name FROM clients ORDER BY client_name", conn
    )

    categories = pd.read_sql(
        "SELECT id, category_name FROM categories ORDER BY category_name", conn
    )

    col1, col2 = st.columns(2)

    with col1:
        client_filter = st.selectbox(
            "Filter by Client",
            ["All"] + list(clients["client_name"])
        )

    with col2:
        category_filter = st.selectbox(
            "Filter by Category",
            ["All"] + list(categories["category_name"])
        )

    # ----------------------------
    # LOAD PROJECTIONS
    # ----------------------------

    query = """

    SELECT
        b.id,
        c.client_name AS "Client",
        p.program_name AS "Program",
        cat.category_name AS "Category",
        b.invoice_month AS "Invoice Month",
        b.invoice_description AS "Description",
        b.client_billed_amount AS "Amount"

    FROM billing_entries b

    LEFT JOIN clients c ON b.client_id = c.id
    LEFT JOIN programs p ON b.program_id = p.id
    LEFT JOIN categories cat ON b.category_id = cat.id

    WHERE b.invoice_no IS NULL
    AND b.status = 'Active'

    ORDER BY b.id DESC

    """

    df = pd.read_sql(query, conn)

    if client_filter != "All":
        df = df[df["Client"] == client_filter]

    if category_filter != "All":
        df = df[df["Category"] == category_filter]

    st.subheader("Projections")

    selected = st.dataframe(
        df,
        use_container_width=True,
        selection_mode="single-row",
        on_select="rerun"
    )

    # ----------------------------
    # EDIT BILLING
    # ----------------------------

    if selected["selection"]["rows"]:

        row_index = selected["selection"]["rows"][0]
        projection_id = df.iloc[row_index]["id"]

        st.divider()

        st.subheader("Enter Billing Details")

        funnel_number = st.text_input("Funnel Number")
        invoice_no = st.text_input("Invoice Number")
        invoice_date = st.date_input("Invoice Date")

        if st.button("Save Billing"):

            cursor = conn.cursor()

            cursor.execute("""
                UPDATE billing_entries
                SET
                    funnel_number = %s,
                    invoice_no = %s,
                    invoice_date = %s
                WHERE id = %s
            """,(
                funnel_number,
                invoice_no,
                invoice_date,
                int(projection_id)
            ))

            conn.commit()

            st.success("Billing details saved")

            st.rerun()


# ---------------------------------------------------
# TAB 3 — REPORTS
# ---------------------------------------------------

with tab3:

    st.header("Billing Report")

    query = """

    SELECT
        c.client_name AS "Client",
        p.program_name AS "Program",
        et.expense_type_name AS "ExpenseType",

        b.funnel_number AS "Funnel Number",
        b.invoice_no AS "InvoiceNo",
        b.invoice_date AS "InvoiceDate",

        TO_CHAR(b.invoice_date, 'YYYY') AS "FinancialYear",
        TO_CHAR(b.invoice_date, 'Mon-YY') AS "InvoiceMonth",

        cat.category_name AS "Category",

        b.invoice_description AS "InvoiceDescription",
        b.client_billed_amount AS "ClientBilledAmount",

        b.projection_date AS "Projection Date",

        NULL AS "Projection Added by",

        MAX(CASE WHEN ve.row_num = 1 THEN v.vendor_name END) AS "Vendor1Name",
        MAX(CASE WHEN ve.row_num = 1 THEN ve.amount END) AS "Vendor1Amount",

        MAX(CASE WHEN ve.row_num = 2 THEN v.vendor_name END) AS "Vendor2Name",
        MAX(CASE WHEN ve.row_num = 2 THEN ve.amount END) AS "Vendor2Amount",

        MAX(CASE WHEN ve.row_num = 3 THEN v.vendor_name END) AS "Vendor3Name",
        MAX(CASE WHEN ve.row_num = 3 THEN ve.amount END) AS "Vendor3Amount",

        COALESCE(SUM(ve.amount),0) AS "Total Vendor Amount",

        (b.client_billed_amount - COALESCE(SUM(ve.amount),0)) AS "GrossMargin",

        b.status AS "Status",
        b.reason AS "Reason",

        cn.credit_note_no AS "Credit Note No",
        cn.credit_note_date AS "Credit Note Date",
        cn.cn_amount AS "CN Amount",
        cn.cn_description AS "CN Description",

        COALESCE(cn.cn_amount,0) AS "TotalCreditNoteAmount"

    FROM billing_entries b

    LEFT JOIN clients c
        ON b.client_id = c.id

    LEFT JOIN programs p
        ON b.program_id = p.id

    LEFT JOIN categories cat
        ON b.category_id = cat.id

    LEFT JOIN expense_types et
        ON b.expense_type_id = et.id

    LEFT JOIN (
        SELECT
            billing_entry_id,
            vendor_id,
            amount,
            ROW_NUMBER() OVER(PARTITION BY billing_entry_id ORDER BY id) AS row_num
        FROM vendor_expenses
    ) ve
        ON b.id = ve.billing_entry_id

    LEFT JOIN vendors v
        ON ve.vendor_id = v.id

    LEFT JOIN credit_notes cn
        ON b.id = cn.billing_entry_id

    GROUP BY
        b.id,
        c.client_name,
        p.program_name,
        et.expense_type_name,
        cat.category_name,
        cn.credit_note_no,
        cn.credit_note_date,
        cn.cn_amount,
        cn.cn_description

    ORDER BY b.id DESC

    """

    report_df = pd.read_sql(query, conn)

    st.dataframe(report_df, use_container_width=True)

    st.divider()

    st.download_button(
        label="Download Excel",
        data=report_df.to_csv(index=False),
        file_name="billing_report.csv",
        mime="text/csv"
    )