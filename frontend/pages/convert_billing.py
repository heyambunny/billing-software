import streamlit as st
import pandas as pd
from utils.audit import log_audit
from config import BASE_URL

def show_convert_billing(conn):

    st.header("Convert Projection → Billing")
    if "billing_msg" in st.session_state:
        if st.session_state["billing_msg"] == "deleted":
            st.toast("Marked as Deleted ✅")
        else:
            st.toast("Converted to Billing ✅")
        del st.session_state["billing_msg"]

    user_id = int(st.session_state.user_id)
    role_id = st.session_state.role_id

    # ---------------- DATA ----------------

    if role_id == 1:
        query = """
        SELECT
            b.id,
            c.client_name AS "Client",
            p.program_name AS "Program",
            cat.category_name AS "Category",
            b.invoice_month AS "Invoice Month",
            b.financial_year AS "Financial Year",
            b.invoice_description AS "Description",
            b.client_billed_amount AS "Amount"
        FROM billing_entries b
        JOIN clients c ON b.client_id = c.id
        JOIN programs p ON b.program_id = p.id
        JOIN categories cat ON b.category_id = cat.id
        WHERE b.invoice_no IS NULL
        AND b.status = 'Active'
        ORDER BY b.id DESC
        """
        df = pd.read_sql(query, conn)

    else:
        query = """
        SELECT
            b.id,
            c.client_name AS "Client",
            p.program_name AS "Program",
            cat.category_name AS "Category",
            b.invoice_month AS "Invoice Month",
            b.financial_year AS "Financial Year",
            b.invoice_description AS "Description",
            b.client_billed_amount AS "Amount"
        FROM billing_entries b
        JOIN clients c ON b.client_id = c.id
        JOIN programs p ON b.program_id = p.id
        JOIN categories cat ON b.category_id = cat.id
        JOIN user_client_access uca ON b.client_id = uca.client_id
        WHERE b.invoice_no IS NULL
        AND b.status = 'Active'
        AND uca.user_id = %s
        ORDER BY b.id DESC
        """
        df = pd.read_sql(query, conn, params=(user_id,))

    # ---------------- TABLE ----------------

    selected = st.dataframe(
        df,
        use_container_width=True,
        selection_mode="single-row",
        on_select="rerun"
    )

    # ---------------- FORM ----------------

    if selected["selection"]["rows"]:

        row_index = selected["selection"]["rows"][0]
        projection_id = int(df.iloc[row_index]["id"])
        row = df.iloc[row_index]

        st.divider()
        st.subheader("Convert to Billing")

        st.text_input(
            "Invoice Description",
            value=str(row.get("Description", "")),
            disabled=True
        )

        # 🔥 AMOUNT LOCKED
        amount = float(row["Amount"])

        st.text_input(
            "Amount",
            value=str(amount),
            disabled=True,
            key=f"amount_{projection_id}"
        )

        status = st.selectbox(
            "Status",
            ["Active", "Deleted"],
            key=f"status_{projection_id}"
        )

        delete_reason = ""
        if status == "Deleted":
            delete_reason = st.text_area(
                "Delete Reason",
                key=f"reason_{projection_id}"
            )

        funnel_number = st.text_input(
            "Funnel Number",
            key=f"funnel_{projection_id}"
        )

        invoice_no = st.text_input(
            "Invoice Number",
            key=f"invoice_{projection_id}"
        )

        invoice_date = st.date_input(
            "Invoice Date",
            key=f"date_{projection_id}"
        )

        # ---------------- VENDORS ----------------

        st.subheader("Vendor Expenses")

        vendors = pd.read_sql(
            "SELECT id, vendor_name FROM vendors ORDER BY vendor_name",
            conn
        )

        existing_vendors = pd.read_sql("""
            SELECT vendor_id, amount
            FROM vendor_expenses
            WHERE billing_entry_id = %s
        """, conn, params=(projection_id,))

        if st.session_state.get("conv_vendor_id") != projection_id:
            st.session_state.conv_vendor_id = projection_id
            st.session_state.vendor_rows = max(1, len(existing_vendors))

        col1, col2 = st.columns(2)

        if col1.button("Add Vendor", key=f"add_vendor_{projection_id}"):
            st.session_state.vendor_rows += 1

        if col2.button("Remove Vendor", key=f"remove_vendor_{projection_id}") and st.session_state.vendor_rows > 1:
            st.session_state.vendor_rows -= 1

        vendor_data = []
        vendor_options = ["None"] + list(vendors["vendor_name"])

        for i in range(st.session_state.vendor_rows):

            v1, v2 = st.columns(2)

            default_amount = 0.0
            default_vendor_name = "None"

            if i < len(existing_vendors):
                default_amount = float(existing_vendors.iloc[i]["amount"])
                vendor_id = existing_vendors.iloc[i]["vendor_id"]

                # 🔥 FIX: MAP ID → NAME
                match = vendors[vendors["id"] == vendor_id]
                if not match.empty:
                    default_vendor_name = match.iloc[0]["vendor_name"]

            vendor_name = v1.selectbox(
                f"Vendor {i+1}",
                vendor_options,
                index=vendor_options.index(default_vendor_name),
                key=f"vendor_{projection_id}_{i}"
            )

            vendor_amount = v2.number_input(
                f"Amount {i+1}",
                value=default_amount,
                key=f"vendor_amt_{projection_id}_{i}"
            )

            if vendor_name != "None" and vendor_amount > 0:
                vendor_id = int(
                    vendors.loc[
                        vendors["vendor_name"] == vendor_name, "id"
                    ].iloc[0]
                )
                vendor_data.append((vendor_id, vendor_amount))

        # ---------------- SAVE ----------------

        if st.button("Save", key=f"save_{projection_id}"):

            import requests

            token = st.session_state.get("token")

            if not token:
                st.error("User not authenticated")
                return

            payload = {
                "projection_id": projection_id,
                "amount": float(amount),
                "status": status,
                "delete_reason": delete_reason,
                "funnel_number": funnel_number,
                "invoice_no": invoice_no,
                "invoice_date": str(invoice_date),
                "vendors": [
                    {"vendor_id": vid, "amount": amt}
                    for vid, amt in vendor_data
                ]
            }

            headers = {
                "Authorization": f"Bearer {token}"
            }

            try:
                res = requests.post(
                    f"{BASE_URL}/api/convert-billing",
                    json=payload,
                    headers=headers
                )

                st.write(res.status_code, res.text)

                if res.status_code != 200:
                    st.error(res.json().get("detail", "Error"))
                    return

                if status == "Deleted":
                    st.session_state["billing_msg"] = "deleted"
                else:
                    st.session_state["billing_msg"] = "converted"

                st.rerun()
                return

            except Exception as e:
                st.error(f"Error connecting to backend: {e}")