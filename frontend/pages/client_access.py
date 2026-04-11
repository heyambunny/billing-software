import streamlit as st
import pandas as pd
import bcrypt
import requests
from config import BASE_URL

from utils.refresh import refresh_listener
_ = refresh_listener()

def show_client_access(conn):

    st.header("🔐 Access & Master Management")

    # ================= SESSION =================
    if "success_msg" not in st.session_state:
        st.session_state.success_msg = None

    if st.session_state.success_msg:
        st.success(st.session_state.success_msg)
        st.session_state.success_msg = None

    tab1, tab2 = st.tabs(["🔐 Client Access", "🗂️ Masters"])

    # =================================================
    # 🔐 CLIENT ACCESS (API)
    # =================================================
    with tab1:

        token = st.session_state.get("token")
        headers = {"Authorization": f"Bearer {token}"}

        res = requests.get(f"{BASE_URL}/api/client-access-data", headers=headers)

        if res.status_code != 200:
            st.error("Failed to load data")
            return

        data = res.json()

        users = pd.DataFrame(data["users"])
        clients = pd.DataFrame(data["clients"])

        clients.rename(columns={"name": "client_name"}, inplace=True)

        user_name = st.selectbox("Select User", users["name"])
        user_id = int(users[users["name"] == user_name]["id"].iloc[0])

        res = requests.get(f"{BASE_URL}/api/user-clients/{user_id}", headers=headers)
        assigned = res.json() if res.status_code == 200 else []

        assigned_names = [c["name"] for c in assigned]

        st.subheader("Assigned Clients")

        if assigned:
            for c in assigned:
                col1, col2 = st.columns([3,1])
                col1.write(c["name"])

                if col2.button("Remove", key=f"{user_id}_{c['id']}"):
                    requests.post(
                        f"{BASE_URL}/api/remove-client",
                        json={"user_id": user_id, "client_id": c["id"]},
                        headers=headers
                    )
                    st.rerun()
        else:
            st.info("No clients assigned")

        st.divider()

        st.subheader("Assign Clients")

        available = [c for c in clients["client_name"] if c not in assigned_names]

        selected = st.multiselect("Select Clients", available)

        if st.button("Save Access"):

            if not selected:
                st.warning("Please select at least one client")
                return

            # remove existing
            for c in assigned:
                requests.post(
                    f"{BASE_URL}/api/remove-client",
                    json={"user_id": user_id, "client_id": c["id"]},
                    headers=headers
                )

            # add new
            for name in selected:
                cid = int(clients[clients["client_name"] == name]["id"].iloc[0])

                requests.post(
                    f"{BASE_URL}/api/assign-client",
                    json={"user_id": user_id, "client_id": cid},
                    headers=headers
                )

            st.success("Access updated")
            st.rerun()

    # =================================================
    # 🗂️ MASTERS
    # =================================================
    with tab2:

        master = st.selectbox("Select Master", ["User", "Client", "Vendor", "Program"])

        # ---------- USER ----------
        if master == "User":

            roles = pd.read_sql("SELECT id, role_name FROM roles", conn)
            role_map = dict(zip(roles["role_name"], roles["id"]))

            with st.form("user_form"):
                name = st.text_input("Username")
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                role = st.selectbox("Role", list(role_map.keys()))

                submit = st.form_submit_button("Create User")

                if submit:

                    if not name or not email or not password:
                        st.warning("All fields required")
                    else:
                        cursor = conn.cursor()

                        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

                        cursor.execute("""
                            INSERT INTO users (name, email, password_hash, role_id, created_at, is_active)
                            VALUES (%s, %s, %s, %s, NOW(), TRUE)
                        """, (name, email, hashed, role_map[role]))

                        conn.commit()
                        st.success("User created")

            # 🔥 FIXED USER TABLE (NO PASSWORD)
            st.subheader("👤 Users List")

            users_df = pd.read_sql("""
                SELECT 
                    u.id,
                    u.name,
                    u.email,
                    r.role_name,
                    u.is_active,
                    u.created_at
                FROM users u
                LEFT JOIN roles r ON u.role_id = r.id
                ORDER BY u.created_at DESC
            """, conn)

            st.dataframe(users_df, use_container_width=True, hide_index=True)

        # ---------- CLIENT ----------
        elif master == "Client":

            with st.form("client_form"):
                name = st.text_input("Client Name")
                submit = st.form_submit_button("Create Client")

                if submit:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO clients (client_name) VALUES (%s)", (name,))
                    conn.commit()
                    st.success("Client created")

            st.subheader("🏢 Clients List")
            st.dataframe(pd.read_sql("SELECT * FROM clients", conn), use_container_width=True)

        # ---------- VENDOR ----------
        elif master == "Vendor":

            with st.form("vendor_form"):
                name = st.text_input("Vendor Name")
                submit = st.form_submit_button("Create Vendor")

                if submit:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO vendors (vendor_name) VALUES (%s)", (name,))
                    conn.commit()
                    st.success("Vendor created")

            st.subheader("🏭 Vendors List")
            st.dataframe(pd.read_sql("SELECT * FROM vendors", conn), use_container_width=True)

        # ---------- PROGRAM ----------
        elif master == "Program":

            clients = pd.read_sql("SELECT id, client_name FROM clients", conn)

            with st.form("program_form"):
                name = st.text_input("Program Name")
                client = st.selectbox("Client", clients["client_name"])
                submit = st.form_submit_button("Create Program")

                if submit:
                    cid = int(clients[clients["client_name"] == client]["id"].iloc[0])

                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO programs (program_name, client_id)
                        VALUES (%s, %s)
                    """, (name, cid))

                    conn.commit()
                    st.success("Program created")

            st.subheader("📦 Programs List")
            st.dataframe(pd.read_sql("SELECT * FROM programs", conn), use_container_width=True)