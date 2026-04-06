import streamlit as st
import pandas as pd
from datetime import datetime

from utils.refresh import refresh_listener
_ = refresh_listener()

def show_add_projection(conn):

    st.header("Add Projection")

    # ---------------- FORM VERSION (CORE FIX) ----------------
    if "form_version" not in st.session_state:
        st.session_state.form_version = 0

    form_key = f"form_{st.session_state.form_version}"

    user_id = int(st.session_state.user_id)
    role_id = st.session_state.role_id

    # ---------------- CLIENTS ----------------
    if role_id == 1:
        clients = pd.read_sql(
            "SELECT id, client_name FROM clients ORDER BY client_name",
            conn
        )
    else:
        clients = pd.read_sql(
            f"""
            SELECT c.id, c.client_name
            FROM clients c
            JOIN user_client_access uca
                ON c.id = uca.client_id
            WHERE uca.user_id = {user_id}
            ORDER BY c.client_name
            """,
            conn
        )

    if clients.empty:
        st.error("No clients assigned to this user")
        st.stop()

    # ---------------- PROGRAMS ----------------
    programs = pd.read_sql(
        "SELECT id, program_name, client_id FROM programs ORDER BY program_name",
        conn
    )

    # ---------------- CATEGORIES ----------------
    categories = pd.read_sql(
        "SELECT id, category_name FROM categories ORDER BY category_name",
        conn
    )

    # ---------------- VENDORS ----------------
    vendors = pd.read_sql(
        "SELECT id, vendor_name FROM vendors ORDER BY vendor_name",
        conn
    )

    # ---------------- CLIENT ----------------
    client_name = st.selectbox(
        "Client",
        clients["client_name"],
        key=f"client_{form_key}"
    )

    client_id = int(
        clients[clients["client_name"] == client_name]["id"].values[0]
    )

    # ---------------- PROGRAM ----------------
    client_programs = programs[programs["client_id"] == client_id]

    if client_programs.empty:
        st.error("No programs found for this client")
        st.stop()

    program_name = st.selectbox(
        "Program",
        client_programs["program_name"],
        key=f"program_{form_key}"
    )

    program_id = int(
        client_programs[
            client_programs["program_name"] == program_name
        ]["id"].values[0]
    )

    # ---------------- CATEGORY ----------------
    category_name = st.selectbox(
        "Category",
        categories["category_name"],
        key=f"category_{form_key}"
    )

    category_id = int(
        categories[categories["category_name"] == category_name]["id"].values[0]
    )

    # ---------------- MONTH ----------------
    months = [
        "Apr","May","Jun","Jul","Aug","Sep",
        "Oct","Nov","Dec","Jan","Feb","Mar"
    ]

    current_year = datetime.now().year
    month_options = [f"{m}-{str(current_year)[2:]}" for m in months]

    invoice_month = st.selectbox(
        "Invoice Month",
        month_options,
        key=f"month_{form_key}"
    )

    year = int("20" + invoice_month.split("-")[1])

    if invoice_month.startswith(("Jan", "Feb", "Mar")):
        financial_year = f"FY {year-1}-{year}"
    else:
        financial_year = f"FY {year}-{year+1}"

    st.write("Financial Year:", financial_year)

    # ---------------- DESCRIPTION ----------------
    description = st.text_area(
        "Invoice Description",
        key=f"desc_{form_key}"
    )

    # ---------------- AMOUNT ----------------
    amount = st.number_input(
        "Client Billed Amount",
        min_value=0.0,
        key=f"amt_{form_key}"
    )

    # ---------------- VENDORS ----------------
    st.subheader("Vendor Expenses")

    if "vendor_rows" not in st.session_state:
        st.session_state.vendor_rows = 1

    col1, col2 = st.columns(2)

    if col1.button("Add Vendor", key=f"add_vendor_{form_key}"):
        st.session_state.vendor_rows += 1

    if col2.button("Remove Vendor", key=f"remove_vendor_{form_key}") and st.session_state.vendor_rows > 1:
        st.session_state.vendor_rows -= 1

    vendor_data = []

    for i in range(st.session_state.vendor_rows):

        vcol1, vcol2 = st.columns(2)

        vendor_name = vcol1.selectbox(
            f"Vendor {i+1}",
            ["None"] + list(vendors["vendor_name"]),
            key=f"vendor_{i}_{form_key}"
        )

        vendor_amount = vcol2.number_input(
            f"Amount {i+1}",
            min_value=0.0,
            key=f"amount_{i}_{form_key}"
        )

        if vendor_name != "None" and vendor_amount > 0:
            vendor_id = int(
                vendors.loc[
                    vendors["vendor_name"] == vendor_name, "id"
                ].iloc[0]
            )
            vendor_data.append((vendor_id, vendor_amount))

    # ---------------- SAVE ----------------
    if st.button("Save Projection", key=f"save_{form_key}"):

        if not description.strip():
            st.error("Description is mandatory")
            st.stop()

        if amount <= 0:
            st.error("Amount must be greater than 0")
            st.stop()

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
            status,
            created_by_user_id
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_DATE,'Active',%s)
        RETURNING id
        """,
        (
            client_id,
            program_id,
            expense_type_id,
            category_id,
            description,
            float(amount),
            invoice_month,
            financial_year,
            user_id
        ))

        billing_id = cursor.fetchone()[0]

        for vendor_id, vendor_amount in vendor_data:
            cursor.execute("""
            INSERT INTO vendor_expenses
            (billing_entry_id, vendor_id, amount)
            VALUES (%s,%s,%s)
            """,
            (
                billing_id,
                vendor_id,
                float(vendor_amount)
            ))

        conn.commit()

        # 🔥 CORE RESET LOGIC
        st.session_state.form_version += 1
        st.session_state.vendor_rows = 1
        st.session_state["projection_saved"] = True

        from utils.refresh import trigger_refresh

        trigger_refresh("✅ Done")

    # ---------------- SUCCESS POPUP ----------------
    if st.session_state.get("projection_saved"):
        st.toast("Projection added successfully ✅")
        st.success("Projection added successfully ✅")
        st.session_state.pop("projection_saved")