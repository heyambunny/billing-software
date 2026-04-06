import streamlit as st
import pandas as pd
import bcrypt

from utils.refresh import refresh_listener
_ = refresh_listener()

def show_client_access(conn):

    st.header("🔐 Access & Master Management")

    # ================= SESSION STATE =================
    if "success_msg" not in st.session_state:
        st.session_state.success_msg = None

    if st.session_state.success_msg:
        st.success(st.session_state.success_msg)
        st.session_state.success_msg = None

    # ================= TABS =================
    tab1, tab2 = st.tabs(["🔐 Client Access", "🗂️ Masters"])

    # =================================================
    # 🔐 CLIENT ACCESS TAB
    # =================================================
    with tab1:

        users = pd.read_sql("""
            SELECT u.id, u.name, u.email, r.role_name
            FROM users u
            LEFT JOIN roles r ON u.role_id = r.id
            WHERE u.is_active = TRUE
            ORDER BY u.name
        """, conn)

        clients = pd.read_sql(
            "SELECT id, client_name FROM clients ORDER BY client_name",
            conn
        )

        if users.empty or clients.empty:
            st.warning("Users or Clients missing")
        else:

            user_name = st.selectbox("Select User", users["name"])
            user_row = users[users["name"] == user_name]

            user_id = int(user_row["id"].iloc[0])
            st.caption(f"{user_row['role_name'].iloc[0]} | {user_row['email'].iloc[0]}")

            access = pd.read_sql(
                "SELECT client_id FROM user_client_access WHERE user_id = %s",
                conn,
                params=(user_id,)
            )

            assigned_ids = access["client_id"].tolist()

            selected_clients = st.multiselect(
                "Assign Clients",
                clients["client_name"],
                default=clients[clients["id"].isin(assigned_ids)]["client_name"]
            )

            if st.button("💾 Save Access"):

                cursor = conn.cursor()

                try:
                    cursor.execute("DELETE FROM user_client_access WHERE user_id = %s", (user_id,))

                    for c in selected_clients:
                        cid = int(clients.loc[clients["client_name"] == c, "id"].iloc[0])
                        cursor.execute(
                            "INSERT INTO user_client_access (user_id, client_id) VALUES (%s, %s)",
                            (user_id, cid)
                        )

                    conn.commit()
                    st.session_state.success_msg = "✅ Access updated"
                    from utils.refresh import trigger_refresh

                    trigger_refresh("✅ Done")

                except Exception as e:
                    conn.rollback()
                    st.error(str(e))

        # ================= SUMMARY =================
        st.divider()
        st.subheader("📊 User Access Summary")

        summary = pd.read_sql("""
            SELECT u.id, u.name, u.email, r.role_name, c.client_name
            FROM users u
            LEFT JOIN roles r ON u.role_id = r.id
            LEFT JOIN user_client_access uca ON u.id = uca.user_id
            LEFT JOIN clients c ON uca.client_id = c.id
            WHERE u.is_active = TRUE
            ORDER BY u.name
        """, conn)

        if not summary.empty:

            grouped = (
                summary.groupby(["id", "name", "email", "role_name"])["client_name"]
                .apply(lambda x: ", ".join(sorted(x.dropna())))
                .reset_index()
            )

            grouped.columns = ["User ID", "Name", "Email", "Role", "Clients"]
            grouped["Clients"] = grouped["Clients"].replace("", "All Access")

            search = st.text_input("🔍 Search User")

            if search:
                grouped = grouped[grouped["Name"].str.contains(search, case=False)]

            st.dataframe(grouped, use_container_width=True, hide_index=True)

    # =================================================
    # 🗂️ MASTERS TAB
    # =================================================
    with tab2:

        master_type = st.selectbox(
            "Select Master",
            ["User", "Client", "Vendor", "Program"]
        )

        # ================= USER =================
        if master_type == "User":

            roles = pd.read_sql("SELECT id, role_name FROM roles", conn)
            role_map = dict(zip(roles["role_name"], roles["id"]))

            with st.form("user_form"):

                name = st.text_input("Username", key="u_name")
                email = st.text_input("Email", key="u_email")
                password = st.text_input("Password", type="password", key="u_pass")
                role = st.selectbox("Role", list(role_map.keys()), key="u_role")

                submit = st.form_submit_button("Create User")

                if submit:

                    if not name or not email or not password:
                        st.warning("All fields required")
                    else:
                        cursor = conn.cursor()

                        try:
                            cursor.execute("SELECT 1 FROM users WHERE email=%s", (email,))
                            if cursor.fetchone():
                                st.error("Email exists")
                                return

                            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

                            cursor.execute("""
                                INSERT INTO users (name, email, password_hash, role_id, created_at, is_active)
                                VALUES (%s, %s, %s, %s, NOW(), TRUE)
                            """, (name, email, hashed, role_map[role]))

                            conn.commit()

                            st.session_state.success_msg = "✅ User created"
                            st.session_state.u_name = ""
                            st.session_state.u_email = ""
                            st.session_state.u_pass = ""

                            from utils.refresh import trigger_refresh

                            trigger_refresh("✅ Done")

                        except Exception as e:
                            conn.rollback()
                            st.error(str(e))

            # USERS TABLE
            st.divider()
            st.subheader("👤 Users List")

            users_df = pd.read_sql("""
                SELECT u.id, u.name, u.email, r.role_name, u.is_active, u.created_at
                FROM users u
                LEFT JOIN roles r ON u.role_id = r.id
                ORDER BY u.created_at DESC
            """, conn)

            st.dataframe(users_df, use_container_width=True, hide_index=True)

        # ================= CLIENT =================
        elif master_type == "Client":

            with st.form("client_form"):

                name = st.text_input("Client Name", key="c_name")

                submit = st.form_submit_button("Create Client")

                if submit:

                    if not name:
                        st.warning("Client name required")
                    else:
                        cursor = conn.cursor()

                        try:
                            cursor.execute("SELECT 1 FROM clients WHERE client_name=%s", (name,))
                            if cursor.fetchone():
                                st.error("Client exists")
                            else:
                                cursor.execute(
                                    "INSERT INTO clients (client_name, created_at) VALUES (%s, NOW())",
                                    (name,)
                                )

                                conn.commit()

                                st.session_state.success_msg = "✅ Client created"
                                st.session_state.c_name = ""
                                from utils.refresh import trigger_refresh
                                trigger_refresh("✅ Done")

                        except Exception as e:
                            conn.rollback()
                            st.error(str(e))

            # CLIENT TABLE
            st.divider()
            st.subheader("🏢 Clients List")

            clients_df = pd.read_sql("""
                SELECT id, client_name, created_at
                FROM clients
                ORDER BY created_at DESC
            """, conn)

            st.dataframe(clients_df, use_container_width=True, hide_index=True)

        # ================= VENDOR =================
        elif master_type == "Vendor":

            with st.form("vendor_form"):

                name = st.text_input("Vendor Name", key="v_name")

                submit = st.form_submit_button("Create Vendor")

                if submit:

                    if not name:
                        st.warning("Vendor name required")
                    else:
                        cursor = conn.cursor()

                        try:
                            cursor.execute("SELECT 1 FROM vendors WHERE vendor_name=%s", (name,))
                            if cursor.fetchone():
                                st.error("Vendor exists")
                            else:
                                cursor.execute(
                                    "INSERT INTO vendors (vendor_name, created_at) VALUES (%s, NOW())",
                                    (name,)
                                )

                                conn.commit()

                                st.session_state.success_msg = "✅ Vendor created"
                                st.session_state.v_name = ""
                                from utils.refresh import trigger_refresh
                                trigger_refresh("✅ Done")

                        except Exception as e:
                            conn.rollback()
                            st.error(str(e))

            # VENDOR TABLE
            st.divider()
            st.subheader("🏭 Vendors List")

            vendors_df = pd.read_sql("""
                SELECT id, vendor_name, created_at
                FROM vendors
                ORDER BY created_at DESC
            """, conn)

            st.dataframe(vendors_df, use_container_width=True, hide_index=True)

        # ================= PROGRAM =================
        elif master_type == "Program":

            clients = pd.read_sql("SELECT id, client_name FROM clients", conn)

            if clients.empty:
                st.warning("Create client first")
            else:

                with st.form("program_form"):

                    name = st.text_input("Program Name", key="p_name")
                    client = st.selectbox("Client", clients["client_name"], key="p_client")

                    submit = st.form_submit_button("Create Program")

                    if submit:

                        if not name:
                            st.warning("Program name required")
                        else:
                            cursor = conn.cursor()

                            try:
                                cursor.execute("SELECT 1 FROM programs WHERE program_name=%s", (name,))
                                if cursor.fetchone():
                                    st.error("Program exists")
                                else:
                                    cid = int(clients[clients["client_name"] == client]["id"].iloc[0])

                                    cursor.execute(
                                        "INSERT INTO programs (program_name, client_id, created_at) VALUES (%s, %s, NOW())",
                                        (name, cid)
                                    )

                                    conn.commit()

                                    st.session_state.success_msg = "✅ Program created"
                                    st.session_state.p_name = ""
                                    from utils.refresh import trigger_refresh
                                    trigger_refresh("✅ Done")

                            except Exception as e:
                                conn.rollback()
                                st.error(str(e))

            # PROGRAM TABLE
            st.divider()
            st.subheader("📦 Programs List")

            programs_df = pd.read_sql("""
                SELECT p.id, p.program_name, c.client_name, p.created_at
                FROM programs p
                LEFT JOIN clients c ON p.client_id = c.id
                ORDER BY p.created_at DESC
            """, conn)

            st.dataframe(programs_df, use_container_width=True, hide_index=True)