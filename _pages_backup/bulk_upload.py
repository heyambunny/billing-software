import streamlit as st
import pandas as pd
from db import get_connection
from io import BytesIO


def show_bulk_upload(conn):

    st.header("📤 Bulk Upload Projections")

    cursor = conn.cursor()

    # ---------------- SAMPLE FILE ----------------
    st.subheader("⬇ Download Sample File")

    sample_data = pd.DataFrame({
        "Client": ["V-Guard"],
        "Program": ["Loyalty"],
        "Category": ["Reward"],
        "InvoiceMonth": ["Apr-26"],
        "InvoiceDescription": ["Campaign"],
        "ClientBilledAmount": [50000],
        "Projection Added By": ["Himanshu"],

        # Vendors (extendable)
        "Vendor1Name": ["Vendor A"],
        "Vendor1Amount": [20000],
        "Vendor2Name": [""],
        "Vendor2Amount": [0],
        "Vendor3Name": [""],
        "Vendor3Amount": [0],
        "Vendor4Name": [""],
        "Vendor4Amount": [0],
        "Vendor5Name": [""],
        "Vendor5Amount": [0],
    })

    buffer = BytesIO()
    sample_data.to_excel(buffer, index=False)
    buffer.seek(0)

    st.download_button(
        "Download Sample Excel",
        buffer,
        "projection_sample.xlsx"
    )

    st.divider()

    # ---------------- FILE UPLOAD ----------------
    file = st.file_uploader("Upload File", type=["xlsx", "csv"])

    if not file:
        return

    df = pd.read_excel(file) if file.name.endswith("xlsx") else pd.read_csv(file)

    st.subheader("📄 Uploaded Data Preview")
    st.dataframe(df.head())

    # ---------------- REQUIRED COLUMNS ----------------
    required_cols = [
        "Client", "Program", "Category",
        "InvoiceMonth", "InvoiceDescription",
        "ClientBilledAmount", "Projection Added By"
    ]

    missing = [c for c in required_cols if c not in df.columns]

    if missing:
        st.error(f"Missing columns: {missing}")
        return

    # ---------------- MASTER DATA ----------------
    clients = pd.read_sql("SELECT id, client_name FROM clients", conn)
    programs = pd.read_sql("SELECT id, program_name, client_id FROM programs", conn)
    categories = pd.read_sql("SELECT id, category_name FROM categories", conn)
    vendors = pd.read_sql("SELECT id, vendor_name FROM vendors", conn)
    users = pd.read_sql("SELECT id, name FROM users", conn)

    cursor.execute("""
    SELECT id FROM expense_types WHERE expense_type_name = 'Projected'
    """)
    expense_type_id = cursor.fetchone()[0]

    # ---------------- EXISTING DATA (DUP CHECK) ----------------
    existing = pd.read_sql("""
        SELECT client_id, program_id, category_id, invoice_month, invoice_description
        FROM billing_entries
        WHERE expense_type_id = %s
    """, conn, params=(expense_type_id,))

    valid_rows = []
    insert_preview = []
    error_details = []
    duplicate_count = 0

    # ---------------- PROCESS ----------------
    for i, row in df.iterrows():

        try:
            # CLIENT
            client_name = row["Client"]
            client = clients[clients["client_name"] == client_name]
            if client.empty:
                raise Exception(f"Invalid Client: {client_name}")
            client_id = int(client.iloc[0]["id"])

            # PROGRAM
            program_name = row["Program"]
            program = programs[
                (programs["program_name"] == program_name) &
                (programs["client_id"] == client_id)
            ]
            if program.empty:
                raise Exception(f"Invalid Program: {program_name}")
            program_id = int(program.iloc[0]["id"])

            # CATEGORY
            category_name = row["Category"]
            category = categories[categories["category_name"] == category_name]
            if category.empty:
                raise Exception(f"Invalid Category: {category_name}")
            category_id = int(category.iloc[0]["id"])

            # USER
            user_name = row["Projection Added By"]
            user_match = users[users["name"] == user_name]
            if user_match.empty:
                raise Exception(f"Invalid User: {user_name}")
            created_by = int(user_match.iloc[0]["id"])

            # AMOUNT
            amount = float(row["ClientBilledAmount"])
            if amount <= 0:
                raise Exception("Amount must be > 0")

            # ---------------- MONTH ----------------
            invoice_month_raw = row["InvoiceMonth"]

            if pd.isna(invoice_month_raw):
                raise Exception("InvoiceMonth is empty")

            if isinstance(invoice_month_raw, pd.Timestamp):
                invoice_month = invoice_month_raw.strftime("%b-%y")
            else:
                invoice_month = str(invoice_month_raw).strip()

            invoice_month = invoice_month.title().strip()

            if len(invoice_month) != 6 or "-" not in invoice_month:
                raise Exception(f"Invalid InvoiceMonth format: {invoice_month}")

            # ---------------- FY ----------------
            year_suffix = invoice_month.split("-")[1]
            year = int("20" + year_suffix)

            if invoice_month.startswith(("Jan", "Feb", "Mar")):
                fy = f"FY {year-1}-{year}"
            else:
                fy = f"FY {year}-{year+1}"

            # ---------------- DUPLICATE CHECK ----------------
            dup = existing[
                (existing["client_id"] == client_id) &
                (existing["program_id"] == program_id) &
                (existing["category_id"] == category_id) &
                (existing["invoice_month"] == invoice_month) &
                (existing["invoice_description"] == row["InvoiceDescription"])
            ]

            if not dup.empty:
                duplicate_count += 1
                raise Exception("Duplicate entry")

            # ---------------- VENDORS (DYNAMIC) ----------------
            vendor_entries = []
            vendor_debug = []

            v = 1
            while f"Vendor{v}Name" in df.columns:

                v_name = row.get(f"Vendor{v}Name")
                v_amt = row.get(f"Vendor{v}Amount", 0)

                if pd.notna(v_name) and v_name != "" and float(v_amt) > 0:

                    vm = vendors[vendors["vendor_name"] == v_name]

                    if vm.empty:
                        raise Exception(f"Invalid Vendor{v}: {v_name}")

                    vendor_id = int(vm.iloc[0]["id"])

                    vendor_entries.append((vendor_id, float(v_amt)))
                    vendor_debug.append(f"{v_name} ({vendor_id})")

                v += 1

            # ---------------- PREVIEW ----------------
            insert_preview.append({
                "Row": i+1,
                "Client": client_name,
                "Program": program_name,
                "Amount": amount,
                "Month": invoice_month,
                "FY": fy,
                "Vendors": ", ".join(vendor_debug)
            })

            valid_rows.append({
                "client_id": client_id,
                "program_id": program_id,
                "category_id": category_id,
                "amount": amount,
                "invoice_month": invoice_month,
                "financial_year": fy,
                "description": row["InvoiceDescription"],
                "vendors": vendor_entries,
                "created_by": created_by
            })

        except Exception as e:
            error_details.append({
                "Row": i+1,
                "Client": row.get("Client"),
                "Program": row.get("Program"),
                "Error": str(e)
            })

    # ---------------- DISPLAY ----------------

    if insert_preview:
        st.subheader("✅ Data to be Inserted")
        st.dataframe(pd.DataFrame(insert_preview))

    if error_details:
        st.subheader("❌ Errors / Invalid Data")
        st.dataframe(pd.DataFrame(error_details))

    st.success(f"Valid Rows: {len(valid_rows)}")
    st.warning(f"Duplicates: {duplicate_count}")
    st.error(f"Errors: {len(error_details)}")

    # ---------------- INSERT ----------------

    if st.button("Upload Valid Data"):

        for row in valid_rows:

            cursor.execute("""
            INSERT INTO billing_entries
            (
                client_id, program_id, expense_type_id,
                category_id, invoice_description,
                client_billed_amount, invoice_month,
                financial_year, projection_date,
                status, created_by_user_id
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_DATE,'Active',%s)
            RETURNING id
            """,
            (
                row["client_id"],
                row["program_id"],
                expense_type_id,
                row["category_id"],
                row["description"],
                row["amount"],
                row["invoice_month"],
                row["financial_year"],
                row["created_by"]
            ))

            billing_id = cursor.fetchone()[0]

            for v_id, amt in row["vendors"]:
                cursor.execute("""
                INSERT INTO vendor_expenses
                (billing_entry_id, vendor_id, amount)
                VALUES (%s,%s,%s)
                """, (billing_id, v_id, amt))

        conn.commit()

        st.success("Upload completed successfully ✅")