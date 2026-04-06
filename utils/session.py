import time
import streamlit as st

SESSION_TIMEOUT = 1800  # 30 minutes


def check_session():

    # ❌ Not logged in
    if not st.session_state.get("logged_in"):
        return False

    now = time.time()

    last_activity = st.session_state.get("last_activity")

    # 🔥 FIX: handle None case
    if last_activity is None:
        st.session_state["last_activity"] = now
        return True

    # 🔐 Session expired
    if now - last_activity > SESSION_TIMEOUT:
        logout()
        st.warning("Session expired due to inactivity")
        return False

    # ✅ Update activity
    st.session_state["last_activity"] = now

    return True


def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]

    st.query_params.clear()