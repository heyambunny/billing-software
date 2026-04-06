import streamlit as st
import pandas as pd

from utils.refresh import refresh_listener
_ = refresh_listener()

def show_billed_amount(conn):

    st.header("Billed Invoices")

    # ---------------- SUCCESS MESSAGE ----------------
    if st.session_state.get("show_success"):
        st.success("Updated successfully ✅")
        st.session_state["show_success"] = False

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
        b.invoice_no AS "Invoice No",
        b.invoice_date AS "Invoice Date",
        b.client_billed_amount AS "Billed Amount"
    FROM billing_entries b
    JOIN clients c ON b.client_id = c.id
    JOIN programs p ON b.program_id = p.id
    JOIN categories cat ON b.category_id = cat.id
    """

    # ---------------- ROLE ----------------
    if role == "admin":
        query = base_query + " WHERE b.expense_type_id = 2 ORDER BY b.id DESC"
        df = pd.read_sql(query, conn)
    else:
        query = base_query + """
        JOIN user_client_access uca ON uca.client_id = b.client_id
        WHERE b.expense_type_id = 2 AND uca.user_id = %s
        ORDER BY b.id DESC
        """
        df = pd.read_sql(query, conn, params=(user_id,))

    if df.empty:
        st.info("No billed invoices found")
        return

    # ---------------- TABLE ----------------
    selected = st.dataframe(
        df,
        use_container_width=True,
        selection_mode="single-row",
        on_select="rerun"
    )

    # ---------------- DETAILS ----------------
    if selected["selection"]["rows"]:

        row_index = selected["selection"]["rows"][0]
        billing_id = int(df.iloc[row_index]["id"])
        row = df.iloc[row_index]

        st.divider()
        st.subheader("Billing Details")

        billed_amount = float(row["Billed Amount"])

        st.text_input(
            "Billed Amount",
            value=f"{billed_amount:,.0f}",
            disabled=True
        )

        # ================= CREDIT NOTE (SINGLE) =================
        st.subheader("Credit Note")

        existing_cn = pd.read_sql("""
            SELECT id, credit_note_no, credit_note_date, cn_amount, cn_description
            FROM credit_notes
            WHERE billing_entry_id = %s
            LIMIT 1
        """, conn, params=(billing_id,))

        cn_id = None

        if not existing_cn.empty:
            cn_id = int(existing_cn.iloc[0]["id"])
            default_no = existing_cn.iloc[0]["credit_note_no"]
            default_date = existing_cn.iloc[0]["credit_note_date"]
            default_amt = float(existing_cn.iloc[0]["cn_amount"])
            default_desc = existing_cn.iloc[0]["cn_description"]
        else:
            default_no = ""
            default_date = None
            default_amt = 0.0
            default_desc = ""

        c1, c2 = st.columns(2)
        c3, c4 = st.columns(2)

        cn_no = c1.text_input("CN Number", value=default_no)
        cn_date = c2.date_input("CN Date", value=default_date)
        cn_amt = c3.number_input("CN Amount", min_value=0.0, value=default_amt)
        cn_desc = c4.text_input("CN Description", value=default_desc)

        total_cn = cn_amt if cn_amt else 0

        # ================= VENDORS =================
        st.subheader("Vendor Expenses")

        vendors = pd.read_sql("SELECT id, vendor_name FROM vendors ORDER BY vendor_name", conn)

        existing_vendors = pd.read_sql("""
            SELECT vendor_id, amount
            FROM vendor_expenses
            WHERE billing_entry_id = %s
        """, conn, params=(billing_id,))

        if st.session_state.get("current_billing_id") != billing_id:
            st.session_state.current_billing_id = billing_id
            st.session_state.vendor_rows = max(1, len(existing_vendors))

        col1, col2 = st.columns(2)

        if col1.button("Add Vendor"):
            st.session_state.vendor_rows += 1

        if col2.button("Remove Vendor") and st.session_state.vendor_rows > 1:
            st.session_state.vendor_rows -= 1

        vendor_options = ["None"] + list(vendors["vendor_name"])

        vendor_data = []
        total_vendor = 0

        for i in range(st.session_state.vendor_rows):

            v1, v2 = st.columns(2)

            default_vendor_id = None
            default_amount = 0.0

            if i < len(existing_vendors):
                default_vendor_id = existing_vendors.iloc[i]["vendor_id"]
                default_amount = float(existing_vendors.iloc[i]["amount"])

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
                key=f"vendor_{billing_id}_{i}"
            )

            vendor_amount = v2.number_input(
                f"Amount {i+1}",
                value=default_amount,
                key=f"amt_{billing_id}_{i}"
            )

            if vendor_name != "None" and vendor_amount > 0:
                vendor_id = int(
                    vendors.loc[vendors["vendor_name"] == vendor_name, "id"].iloc[0]
                )
                vendor_data.append((vendor_id, float(vendor_amount)))
                total_vendor += vendor_amount

        # ================= MARGIN =================
        margin = billed_amount - total_vendor - total_cn
        st.subheader(f"💰 Margin: ₹ {margin:,.0f}")

        # ================= SAVE =================
        if st.button("Update Billing"):

            cursor = conn.cursor()

            # -------- CN UPSERT --------
            if cn_no and cn_amt > 0 and cn_desc.strip():

                if cn_id:
                    cursor.execute("""
                        UPDATE credit_notes
                        SET credit_note_no=%s,
                            credit_note_date=%s,
                            cn_amount=%s,
                            cn_description=%s
                        WHERE id=%s
                    """, (cn_no.strip(), cn_date, cn_amt, cn_desc.strip(), cn_id))

                else:
                    cursor.execute("""
                        INSERT INTO credit_notes
                        (billing_entry_id, credit_note_no, credit_note_date, cn_amount, cn_description)
                        VALUES (%s,%s,%s,%s,%s)
                    """, (billing_id, cn_no.strip(), cn_date, cn_amt, cn_desc.strip()))

            # -------- VENDOR SAFE UPDATE --------
            existing_vendor_set = set(
                (int(row["vendor_id"]), float(row["amount"]))
                for _, row in existing_vendors.iterrows()
            )

            new_vendor_set = set(vendor_data)

            if existing_vendor_set != new_vendor_set:

                cursor.execute("""
                    DELETE FROM vendor_expenses
                    WHERE billing_entry_id = %s
                """, (billing_id,))

                for vendor_id, amt in vendor_data:
                    cursor.execute("""
                        INSERT INTO vendor_expenses
                        (billing_entry_id, vendor_id, amount)
                        VALUES (%s,%s,%s)
                    """, (billing_id, vendor_id, amt))

            conn.commit()

            # ✅ Show success AFTER rerun
            st.session_state["show_success"] = True
            from utils.refresh import trigger_refresh

            trigger_refresh("✅ Done")