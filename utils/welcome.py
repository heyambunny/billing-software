import streamlit as st
import random

def show_welcome_screen():

    user_name = st.session_state.get("user_name", "Boss 😎")

    quotes = [
        "Code hard, nap harder 😴",
        "Bug today, feature tomorrow 😂",
        "Coffee first, logic later ☕",
        "You are 99% caffeine ☕ and 1% debugging 🐛",
        "Deploy fast, fix faster 🚀"
    ]

    gifs = [
        "https://i.giphy.com/media/3o7btPCcdNniyf0ArS/giphy.gif",
        "https://i.giphy.com/media/xUPGcguWZHRC2HyBRS/giphy.gif",
        "https://i.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif"
    ]

    st.markdown("## 👋 Welcome Back!")
    st.markdown(f"### Hey **{user_name}** Boss 😎")
    st.markdown("### How’s your day going?")

    st.divider()

    st.markdown(f"💬 *{random.choice(quotes)}*")

    st.image(random.choice(gifs), use_container_width=True)

    st.divider()

    if st.button("🚀 Let’s Go to Dashboard"):
        st.session_state.show_welcome = False
        st.rerun()