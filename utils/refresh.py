import streamlit as st

def init_refresh():
    if "refresh_flag" not in st.session_state:
        st.session_state.refresh_flag = 0

def trigger_refresh(message=None):
    if message:
        st.session_state.success_msg = message

    st.session_state.refresh_flag += 1

def refresh_listener():
    return st.session_state.get("refresh_flag", 0)