import streamlit as st
import pandas as pd

#
def show_finance_dashboard(conn):

    st.title("💼 Finance Dashboard")

    user_id = int(st.session_state.user_id)
    role_id = st.session_state.role_id

    # ---------------- TABS ----------------

    tab1, tab2 = st.tabs(["📊 Pending", "📈 Projection vs Billing"])

    # ============================================================
    # ===================== TAB 1: PENDING ========================
    # ============================================================

    with tab1:

        base_query = """
        SELECT
            b.id,
            c.client_name,
            p.program_name,
            cat.category_name,
            b.client_billed_amount,
            b.invoice_month,
            b.financial_year,
            TO_DATE(b.invoice_month, 'Mon-YY') AS invoice_month_date
        FROM billing_entries b
        JOIN clients c ON b.client_id = c.id
        JOIN programs p ON b.program_id = p.id
        JOIN categories cat ON b.category_id = cat.id
        WHERE 
            b.status = 'Active'
            AND b.expense_type_id = 1
            AND TO_DATE(b.invoice_month, 'Mon-YY') 
                <= DATE_TRUNC('month', CURRENT_DATE)
        """

        if role_id == 1:
            df = pd.read_sql(base_query + " ORDER BY invoice_month_date", conn)
        else:
            query = base_query + """
            AND b.client_id IN (
                SELECT client_id FROM user_client_access WHERE user_id = %s
            )
            ORDER BY invoice_month_date
            """
            df = pd.read_sql(query, conn, params=(user_id,))

        df["invoice_month_date"] = pd.to_datetime(df["invoice_month_date"], errors="coerce")

        if df.empty:
            st.success("No pending billing 🎉")
        else:

            today = pd.Timestamp.today().replace(day=1)

            df["months_pending"] = (
                (today.year - df["invoice_month_date"].dt.year) * 12 +
                (today.month - df["invoice_month_date"].dt.month)
            )

            def get_bucket(m):
                if m == 0:
                    return "Current"
                elif m == 1:
                    return "1 Month Overdue"
                else:
                    return "2+ Months Overdue"

            df["aging_bucket"] = df["months_pending"].apply(get_bucket)

            # KPI
            total_pending = df["client_billed_amount"].sum()
            total_count = len(df)

            overdue_amount = df[df["months_pending"] >= 1]["client_billed_amount"].sum()
            overdue_percent = (overdue_amount / total_pending) * 100 if total_pending else 0

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Pending", f"₹ {total_pending:,.0f}")
            col2.metric("Total Bills", total_count)
            col3.metric("Overdue Amount", f"₹ {overdue_amount:,.0f}")
            col4.metric("Overdue %", f"{overdue_percent:.1f}%")

            st.divider()

            # Aging summary
            st.subheader("📊 Aging Summary")

            aging_summary = df.groupby("aging_bucket").agg({
                "client_billed_amount": "sum",
                "id": "count"
            }).rename(columns={"id": "invoice_count"}).reset_index()

            st.dataframe(aging_summary, use_container_width=True)

            # Program summary
            st.subheader("📊 Program-wise Pending")

            program_df = df.groupby("program_name").agg({
                "client_billed_amount": "sum",
                "id": "count"
            }).rename(columns={"id": "invoice_count"}).reset_index()

            st.dataframe(program_df, use_container_width=True)

            # Filters
            st.sidebar.header("Filters")

            client_filter = st.sidebar.multiselect("Client", sorted(df["client_name"].unique()))
            program_filter = st.sidebar.multiselect("Program", sorted(df["program_name"].unique()))
            bucket_filter = st.sidebar.multiselect(
                "Aging Bucket",
                ["Current", "1 Month Overdue", "2+ Months Overdue"]
            )

            filtered_df = df.copy()

            if client_filter:
                filtered_df = filtered_df[filtered_df["client_name"].isin(client_filter)]

            if program_filter:
                filtered_df = filtered_df[filtered_df["program_name"].isin(program_filter)]

            if bucket_filter:
                filtered_df = filtered_df[filtered_df["aging_bucket"].isin(bucket_filter)]

            # Alert
            high_overdue = filtered_df[filtered_df["months_pending"] >= 2]
            if not high_overdue.empty:
                st.error(f"🚨 {len(high_overdue)} bills are 2+ months overdue")

            # Table
            st.subheader("⏳ Pending Billing Details")

            display_df = filtered_df[[
                "client_name",
                "program_name",
                "category_name",
                "client_billed_amount",
                "invoice_month",
                "aging_bucket",
                "invoice_month_date"
            ]].sort_values(by="invoice_month_date")

            st.dataframe(display_df, use_container_width=True)

            # Download
            st.download_button(
                "⬇ Download Pending Billing",
                display_df.to_csv(index=False),
                file_name="pending_billing.csv"
            )

    # ============================================================
    # ============ TAB 2: PROJECTION VS BILLING ===================
    # ============================================================

    with tab2:

        st.subheader("📈 Projection vs Billing (Client + Category)")
    
        # query = """
        # SELECT
        #     c.client_name,
        #     cat.category_name,
        #     b.expense_type_id,
        #     COUNT(b.id) as invoice_count,
        #     SUM(b.client_billed_amount) as amount
        # FROM billing_entries b
        # JOIN clients c ON b.client_id = c.id
        # JOIN categories cat ON b.category_id = cat.id
        # WHERE b.status = 'Active'
        # """
    
        # if role_id == 1:
        #     query += " GROUP BY c.client_name, cat.category_name, b.expense_type_id"
        #     df2 = pd.read_sql(query, conn)
        # else:
        #     query += """
        #     AND b.client_id IN (
        #         SELECT client_id FROM user_client_access WHERE user_id = %s
        #     )
        #     GROUP BY c.client_name, cat.category_name, b.expense_type_id
        #     """
        #     df2 = pd.read_sql(query, conn, params=(user_id,))
    
        # if df2.empty:
        #     st.info("No data available")
        # else:
    
        #     # ---------------- TYPE ----------------
        #     df2["type"] = df2["expense_type_id"].apply(
        #         lambda x: "Billed" if x == 2 else "Projected"
        #     )
    
        #     # ---------------- PIVOT ----------------
        #     final_df = df2.pivot_table(
        #         index=["client_name", "category_name"],
        #         columns="type",
        #         values=["amount", "invoice_count"],
        #         aggfunc="sum",
        #         fill_value=0
        #     )
    
        #     # Flatten columns
        #     final_df.columns = [
        #         f"{metric}_{typ}" for metric, typ in final_df.columns
        #     ]
    
        #     final_df = final_df.reset_index()
    
        #     # ---------------- ENSURE COLUMNS EXIST ----------------
    
        #     required_cols = [
        #         "amount_Projected",
        #         "amount_Billed",
        #         "invoice_count_Projected",
        #         "invoice_count_Billed"
        #     ]
    
        #     for col in required_cols:
        #         if col not in final_df.columns:
        #             final_df[col] = 0
    
        #     # ---------------- RENAME ----------------
    
        #     final_df = final_df.rename(columns={
        #         "amount_Projected": "Total Projected Amount",
        #         "amount_Billed": "Total Billed Amount",
        #         "invoice_count_Projected": "Projected Count",
        #         "invoice_count_Billed": "Billed Count"
        #     })
    
        #     # ---------------- KPIs ----------------
    
        #     total_projected = final_df["Total Projected Amount"].sum()
        #     total_billed = final_df["Total Billed Amount"].sum()
    
        #     col1, col2 = st.columns(2)
        #     col1.metric("Total Projected", f"₹ {total_projected:,.0f}")
        #     col2.metric("Total Billed", f"₹ {total_billed:,.0f}")
    
        #     st.divider()
    
        #     # ---------------- TABLE ----------------
    
        #     st.dataframe(final_df, use_container_width=True)