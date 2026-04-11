import streamlit as st
import pandas as pd
from db import get_connection
from io import BytesIO
import requests
from config import BASE_URL

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
            client = clients[clients["client_name"] == row["Client"]]
            if client.empty:
                raise Exception(f"Invalid Client: {row['Client']}")
            client_id = int(client.iloc[0]["id"])

            program = programs[
                (programs["program_name"] == row["Program"]) &
                (programs["client_id"] == client_id)
            ]
            if program.empty:
                raise Exception(f"Invalid Program: {row['Program']}")
            program_id = int(program.iloc[0]["id"])

            category = categories[categories["category_name"] == row["Category"]]
            if category.empty:
                raise Exception(f"Invalid Category: {row['Category']}")
            category_id = int(category.iloc[0]["id"])

            user_match = users[users["name"] == row["Projection Added By"]]
            if user_match.empty:
                raise Exception(f"Invalid User: {row['Projection Added By']}")
            created_by = int(user_match.iloc[0]["id"])

            amount = float(row["ClientBilledAmount"])
            if amount <= 0:
                raise Exception("Amount must be > 0")

            invoice_month = str(row["InvoiceMonth"]).strip().title()

            year = int("20" + invoice_month.split("-")[1])
            fy = f"FY {year-1}-{year}" if invoice_month.startswith(("Jan", "Feb", "Mar")) else f"FY {year}-{year+1}"

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

            # Vendors
            vendor_entries = []
            v = 1
            while f"Vendor{v}Name" in df.columns:
                v_name = row.get(f"Vendor{v}Name")
                v_amt = row.get(f"Vendor{v}Amount", 0)

                if pd.notna(v_name) and v_name != "" and float(v_amt) > 0:
                    vm = vendors[vendors["vendor_name"] == v_name]
                    if vm.empty:
                        raise Exception(f"Invalid Vendor{v}: {v_name}")

                    vendor_entries.append((int(vm.iloc[0]["id"]), float(v_amt)))
                v += 1

            insert_preview.append({
                "Row": i+1,
                "Client": row["Client"],
                "Program": row["Program"],
                "Amount": amount,
                "Month": invoice_month,
                "FY": fy
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
            error_details.append({"Row": i+1, "Error": str(e)})

    # ---------------- DISPLAY ----------------
    if insert_preview:
        st.subheader("✅ Data to be Inserted")
        st.dataframe(pd.DataFrame(insert_preview))

    if error_details:
        st.subheader("❌ Errors")
        st.dataframe(pd.DataFrame(error_details))

    st.success(f"Valid Rows: {len(valid_rows)}")
    st.warning(f"Duplicates: {duplicate_count}")
    st.error(f"Errors: {len(error_details)}")

    # ---------------- API INSERT ----------------
    if st.button("Upload Valid Data"):

        token = st.session_state.get("token")

        payload = []
        for row in valid_rows:
            payload.append({
                "client_id": row["client_id"],
                "program_id": row["program_id"],
                "expense_type_id": expense_type_id,
                "category_id": row["category_id"],
                "description": row["description"],
                "amount": row["amount"],
                "invoice_month": row["invoice_month"],
                "financial_year": row["financial_year"],
                "vendors": row["vendors"],
                "created_by": row["created_by"]
            })

        res = requests.post(
            f"{BASE_URL}/api/bulk-upload",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )

        if res.status_code == 200:
            st.success(res.json()["message"])
        else:
            st.error("Upload failed")