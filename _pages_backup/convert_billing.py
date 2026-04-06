import streamlit as st
import pandas as pd
from utils.audit import log_audit


def show_convert_billing(conn):

    st.header("Convert Projection → Billing")

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

        JOIN user_client_access uca
            ON b.client_id = uca.client_id
        
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

        amount = st.number_input(
            "Amount",
            value=float(row["Amount"]),
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
            if i < len(existing_vendors):
                default_amount = float(existing_vendors.iloc[i]["amount"])

            vendor_name = v1.selectbox(
                f"Vendor {i+1}",
                vendor_options,
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

            cursor = conn.cursor()

            old_data = pd.read_sql(
                "SELECT * FROM billing_entries WHERE id = %s",
                conn,
                params=(projection_id,)
            ).iloc[0]

            # -------- DELETE CASE --------
            if status == "Deleted":

                if not delete_reason.strip():
                    st.error("Delete reason is mandatory")
                    return

                log_audit(cursor, "billing_entries", projection_id, "status",
                          old_data["status"], "Deleted", "UPDATE",
                          user_id, role_id, "billing", "HIGH")

                log_audit(cursor, "billing_entries", projection_id, "reason",
                          old_data.get("reason", ""), delete_reason.strip(),
                          "UPDATE", user_id, role_id, "billing", "MEDIUM")

                cursor.execute("""
                    UPDATE billing_entries
                    SET status = 'Deleted',
                        reason = %s
                    WHERE id = %s
                """, (delete_reason.strip(), projection_id))

                conn.commit()
                st.success("Marked as Deleted ✅")
                return

            # -------- VALIDATION --------

            if not funnel_number or not invoice_no:
                st.error("Funnel & Invoice required")
                return

            # -------- AUDIT BILLING --------

            if old_data["client_billed_amount"] != amount:
                log_audit(cursor, "billing_entries", projection_id,
                          "client_billed_amount",
                          old_data["client_billed_amount"], amount,
                          "UPDATE", user_id, role_id, "billing", "HIGH")

            if old_data.get("invoice_no") != invoice_no:
                log_audit(cursor, "billing_entries", projection_id,
                          "invoice_no",
                          old_data.get("invoice_no"), invoice_no,
                          "UPDATE", user_id, role_id, "billing", "HIGH")

            if str(old_data.get("invoice_date")) != str(invoice_date):
                log_audit(cursor, "billing_entries", projection_id,
                          "invoice_date",
                          old_data.get("invoice_date"), invoice_date,
                          "UPDATE", user_id, role_id, "billing", "MEDIUM")

            # -------- UPDATE --------

            cursor.execute("""
                UPDATE billing_entries
                SET
                    client_billed_amount = %s,
                    funnel_number = %s,
                    invoice_no = %s,
                    invoice_date = %s,
                    expense_type_id = 2
                WHERE id = %s
            """, (
                amount,
                funnel_number,
                invoice_no,
                invoice_date,
                projection_id
            ))

            # -------- VENDOR AUDIT --------

            existing_vendor_data = pd.read_sql("""
                SELECT vendor_id, amount
                FROM vendor_expenses
                WHERE billing_entry_id = %s
            """, conn, params=(projection_id,))

            for _, r in existing_vendor_data.iterrows():
                log_audit(cursor, "vendor_expenses", projection_id,
                          "vendor_removed",
                          f"vendor_id={r['vendor_id']}, amount={r['amount']}",
                          None, "DELETE",
                          user_id, role_id, "vendor", "HIGH")

            cursor.execute("""
                DELETE FROM vendor_expenses
                WHERE billing_entry_id = %s
            """, (projection_id,))

            for vendor_id, amt in vendor_data:
                cursor.execute("""
                    INSERT INTO vendor_expenses
                    (billing_entry_id, vendor_id, amount)
                    VALUES (%s,%s,%s)
                """, (projection_id, vendor_id, float(amt)))

                log_audit(cursor, "vendor_expenses", projection_id,
                          "vendor_added",
                          None,
                          f"vendor_id={vendor_id}, amount={amt}",
                          "INSERT",
                          user_id, role_id, "vendor", "HIGH")

            conn.commit()

            st.success("Converted to Billing ✅")
            from utils.refresh import trigger_refresh
            trigger_refresh("✅ Done")