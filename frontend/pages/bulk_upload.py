# bulk_upload_ui.py

import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import requests
from db import get_connection
from config import BASE_URL


# ---------------- FIX: NUMPY → PYTHON ----------------
def convert_numpy(obj):
    if isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy(i) for i in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    else:
        return obj


def show_bulk_upload(conn):

    st.header("📤 Bulk Upload Projections")

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
    })

    buffer = BytesIO()
    sample_data.to_excel(buffer, index=False)
    buffer.seek(0)

    st.download_button("Download Sample Excel", buffer, "projection_sample.xlsx")

    st.divider()

    # ---------------- FILE UPLOAD ----------------
    file = st.file_uploader("Upload File", type=["xlsx", "csv"])

    if not file:
        return

    try:
        df = pd.read_excel(file) if file.name.endswith("xlsx") else pd.read_csv(file)
    except Exception as e:
        st.error(f"File read error: {e}")
        return

    if df.empty:
        st.error("Uploaded file is empty")
        return

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

    expense_type_id = int(pd.read_sql(
        "SELECT id FROM expense_types WHERE expense_type_name='Projected'", conn
    ).iloc[0]["id"])

    valid_rows = []
    error_details = []

    # ---------------- PROCESS ----------------
    for i, row in df.iterrows():

        try:
            # Client
            client_match = clients[clients.client_name == row["Client"]]
            if client_match.empty:
                raise Exception(f"Invalid Client: {row['Client']}")
            client_id = int(client_match.iloc[0]["id"])

            # Program
            program_match = programs[
                (programs.program_name == row["Program"]) &
                (programs.client_id == client_id)
            ]
            if program_match.empty:
                raise Exception(f"Invalid Program: {row['Program']}")
            program_id = int(program_match.iloc[0]["id"])

            # Category
            category_match = categories[
                categories.category_name == row["Category"]
            ]
            if category_match.empty:
                raise Exception(f"Invalid Category: {row['Category']}")
            category_id = int(category_match.iloc[0]["id"])

            # User
            user_match = users[users.name == row["Projection Added By"]]
            if user_match.empty:
                raise Exception(f"Invalid User: {row['Projection Added By']}")
            created_by = int(user_match.iloc[0]["id"])

            # Amount
            amount = float(row["ClientBilledAmount"])
            if amount <= 0:
                raise Exception("Amount must be greater than 0")

            # Month + FY
            invoice_month = str(row["InvoiceMonth"]).strip().title()

            year = int("20" + invoice_month.split("-")[1])
            fy = (
                f"FY {year-1}-{year}"
                if invoice_month.startswith(("Jan", "Feb", "Mar"))
                else f"FY {year}-{year+1}"
            )

            # ---------------- Vendors ----------------
            vendor_entries = []
            v = 1

            while f"Vendor{v}Name" in df.columns:
                v_name = row.get(f"Vendor{v}Name")
                v_amt = row.get(f"Vendor{v}Amount", 0)

                if pd.notna(v_name) and v_name != "" and float(v_amt) > 0:

                    vm = vendors[vendors.vendor_name == v_name]

                    if vm.empty:
                        raise Exception(f"Invalid Vendor{v}: {v_name}")

                    vendor_entries.append({
                        "vendor_id": int(vm.iloc[0]["id"]),
                        "amount": float(v_amt)
                    })

                v += 1

            # ---------------- FINAL ROW ----------------
            valid_rows.append({
                "client_id": int(client_id),
                "program_id": int(program_id),
                "expense_type_id": int(expense_type_id),
                "category_id": int(category_id),
                "description": str(row["InvoiceDescription"]),
                "amount": float(amount),
                "invoice_month": str(invoice_month),
                "financial_year": str(fy),
                "vendors": vendor_entries,
                "created_by": int(created_by)
            })

        except Exception as e:
            error_details.append({
                "Row": i + 1,
                "Error": str(e)
            })

    # ---------------- DISPLAY ----------------
    st.success(f"Valid Rows: {len(valid_rows)}")
    st.error(f"Errors: {len(error_details)}")

    if error_details:
        st.subheader("❌ Error Details")
        st.dataframe(pd.DataFrame(error_details))

    if valid_rows:
        st.subheader("✅ Preview Valid Data")
        st.dataframe(pd.DataFrame(valid_rows).head())

    # ---------------- API CALL ----------------
    if st.button("Upload Valid Data"):

        token = st.session_state.get("token")

        if not token:
            st.error("User not authenticated")
            return

        try:
            with st.spinner("Uploading data..."):

                payload = convert_numpy(valid_rows)   # 🔥 FIX APPLIED

                res = requests.post(
                    f"{BASE_URL}/api/bulk-upload",
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=60
                )

            st.write("Status:", res.status_code)
            st.write("Response:", res.text)

            if res.status_code == 200:
                result = res.json()

                st.success(f"Inserted: {result['inserted']}")
                st.warning(f"Failed: {result['failed']}")

                if result["errors"]:
                    st.dataframe(pd.DataFrame(result["errors"]))

            else:
                st.error("Upload failed")

        except Exception as e:
            st.error(f"API Error: {e}")