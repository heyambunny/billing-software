import streamlit as st
import pandas as pd
from config import BASE_URL

def show_edit_projection(conn):

    st.header("Edit Projections")

    # ---------------- SUCCESS MESSAGE (FIXED) ----------------
    if "success_message" in st.session_state:
        st.success(st.session_state["success_message"])
        del st.session_state["success_message"]

    # ---------------- USER VALIDATION ----------------
    if "user_id" not in st.session_state:
        st.error("User not logged in")
        st.stop()

    user_id = st.session_state.user_id
    role = st.session_state.get("role", "user")

    # ---------------- BASE QUERY ----------------
    base_query = """
    SELECT
        b.id,
        c.client_name AS "Client",
        p.program_name AS "Program",
        cat.category_name AS "Category",
        b.invoice_description AS "Description",
        b.client_billed_amount AS "Amount"
    FROM billing_entries b
    JOIN clients c ON b.client_id = c.id
    JOIN programs p ON b.program_id = p.id
    JOIN categories cat ON b.category_id = cat.id
    """

    # ---------------- ROLE BASED FILTER ----------------
    if role == "admin":
        query = base_query + """
        WHERE b.expense_type_id = 1
        AND b.status != 'Billed'
        ORDER BY b.id DESC
        """
        df = pd.read_sql(query, conn)
    else:
        query = base_query + """
        JOIN user_client_access uca ON uca.client_id = b.client_id
        WHERE b.expense_type_id = 1
        AND b.status != 'Billed'
        AND uca.user_id = %s
        ORDER BY b.id DESC
        """
        df = pd.read_sql(query, conn, params=(user_id,))

    if df.empty:
        st.info("No projections found")
        return

    # ---------------- TABLE ----------------
    selected = st.dataframe(
        df,
        use_container_width=True,
        selection_mode="single-row",
        on_select="rerun"
    )

    # ---------------- STORE SELECTION ----------------
    if selected["selection"]["rows"] and "selected_proj_index" not in st.session_state:
        st.session_state["selected_proj_index"] = selected["selection"]["rows"][0]

    row_index = st.session_state.get("selected_proj_index")

    if row_index is None or row_index >= len(df):
        return

    billing_id = int(df.iloc[row_index]["id"])
    row = df.iloc[row_index]

    st.divider()
    st.subheader("Projection Details")

    # ---------------- LOCKED ----------------
    st.text_input("Client", value=row["Client"], disabled=True)
    st.text_input("Program", value=row["Program"], disabled=True)
    st.text_input("Category", value=row["Category"], disabled=True)

    # ---------------- EDITABLE ----------------
    description = st.text_area("Description", value=row["Description"])
    amount = st.number_input("Amount", min_value=0.0, value=float(row["Amount"]))

    # ================= VENDORS =================
    st.subheader("Vendor Expenses")

    vendors = pd.read_sql(
        "SELECT id, vendor_name FROM vendors ORDER BY vendor_name", conn
    )

    existing_vendors_df = pd.read_sql("""
        SELECT vendor_id, amount
        FROM vendor_expenses
        WHERE billing_entry_id = %s
    """, conn, params=(billing_id,))

    # 🔥 RESET STATE WHEN RECORD CHANGES
    if st.session_state.get("current_proj_id") != billing_id:
        st.session_state.current_proj_id = billing_id
        st.session_state.vendor_rows = max(1, len(existing_vendors_df))

    col1, col2 = st.columns(2)

    # 🔥 UNIQUE KEYS FIX
    if col1.button("Add Vendor", key=f"add_vendor_{billing_id}"):
        st.session_state.vendor_rows += 1

    if col2.button("Remove Vendor", key=f"remove_vendor_{billing_id}") and st.session_state.vendor_rows > 1:
        st.session_state.vendor_rows -= 1

    vendor_options = ["None"] + list(vendors["vendor_name"])

    vendor_data = []
    total_vendor = 0

    for i in range(st.session_state.vendor_rows):

        v1, v2 = st.columns(2)

        default_vendor_id = None
        default_amount = 0.0

        if i < len(existing_vendors_df):
            default_vendor_id = existing_vendors_df.iloc[i]["vendor_id"]
            default_amount = float(existing_vendors_df.iloc[i]["amount"])

        if default_vendor_id:
            try:
                default_name = vendors.loc[
                    vendors["id"] == default_vendor_id, "vendor_name"
                ].iloc[0]
                default_index = vendor_options.index(default_name)
            except:
                default_index = 0
        else:
            default_index = 0

        vendor_name = v1.selectbox(
            f"Vendor {i+1}",
            vendor_options,
            index=default_index,
            key=f"proj_vendor_{billing_id}_{i}"
        )

        vendor_amount = v2.number_input(
            f"Amount {i+1}",
            value=default_amount,
            key=f"proj_amt_{billing_id}_{i}"
        )

        if vendor_name != "None" and vendor_amount > 0:
            vendor_id = int(
                vendors.loc[
                    vendors["vendor_name"] == vendor_name, "id"
                ].iloc[0]
            )
            vendor_data.append((vendor_id, float(vendor_amount)))
            total_vendor += vendor_amount

    # ================= MARGIN =================
    margin = amount - total_vendor
    st.subheader(f"💰 Margin: ₹ {margin:,.0f}")

    # ================= SAVE (API + RESET + MESSAGE FIX) =================
    if st.button("Update Projection", key=f"update_proj_{billing_id}"):

        import requests

        # -------- VALIDATION --------
        if not description.strip():
            st.error("Description is mandatory")
            return

        if amount <= 0:
            st.error("Amount must be greater than 0")
            return

        token = st.session_state.get("token")

        payload = {
            "billing_id": billing_id,
            "description": description.strip(),
            "amount": float(amount),
            "vendors": [
                {"vendor_id": vid, "amount": amt}
                for vid, amt in vendor_data
            ]
        }

        headers = {
            "Authorization": f"Bearer {token}"
        }

        res = requests.post(
            f"{BASE_URL}/api/edit-projection",
            json=payload,
            headers=headers
        )

        if res.status_code != 200:
            st.error("Update failed ❌")
            return

        # 🔥 STORE MESSAGE
        st.session_state["success_message"] = f"Projection {billing_id} updated successfully ✅"

        # 🔥 RESET FORM
        # st.session_state.pop("selected_proj_index", None)
        # st.session_state.pop("current_proj_id", None)
        # st.session_state.pop("vendor_rows", None)

        # Clear all related state
        for key in ["selected_proj_index", "current_proj_id", "vendor_rows"]:
            if key in st.session_state:
                del st.session_state[key]
        
        # ALSO clear dataframe selection trigger
        st.session_state["_dataframe_selection"] = None
        
        st.rerun()