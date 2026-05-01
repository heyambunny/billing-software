import streamlit as st
import requests
from config import BASE_URL


def _inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap');

    /* ── Page background ── */
    html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {
        background: #EEE9FF !important;
        font-family: 'DM Sans', sans-serif !important;
        color: #1A0A3D !important;
    }
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(ellipse 70% 50% at 50% -5%, rgba(107,63,255,0.18) 0%, transparent 65%),
            radial-gradient(ellipse 40% 30% at 92% 85%, rgba(255,60,120,0.10) 0%, transparent 55%),
            #EEE9FF !important;
        min-height: 100vh;
    }

    /* ── Hide Streamlit chrome ── */
    [data-testid="stHeader"], header,
    [data-testid="stSidebar"],
    [data-testid="stBottomBlockContainer"],
    [data-testid="stDecoration"],
    #MainMenu, footer {
        display: none !important;
        visibility: hidden !important;
    }

    /* ── Outer centering wrapper ── */
    .block-container {
        max-width: 480px !important;
        margin: 0 auto !important;
        padding: 3vh 0 4rem !important;
    }

    /* ── The white card lives on stMainBlockContainer ── */
    /* Brand sits ABOVE the card, form sits INSIDE the card.        */
    /* We split by wrapping form fields in a .card-body div via     */
    /* st.markdown, then use a sticky ::before on the stVerticalBlock */
    /* that wraps just the form section.                             */

    /* Target the vertical block that holds the form inputs + button */
    div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"] {
        background: #FFFFFF !important;
        border-radius: 22px !important;
        border: 1.5px solid rgba(107,63,255,0.13) !important;
        box-shadow:
            0 4px 40px rgba(107,63,255,0.10),
            0 1px 4px rgba(0,0,0,0.04) !important;
        padding: 2rem 2rem 1.75rem !important;
    }

    /* ── Brand header ── */
    .brand-wrap { text-align: center; margin-bottom: 1.75rem; padding: 0 1rem; }
    .brand-icon {
        width: 72px; height: 72px;
        margin: 0 auto 0.9rem;
        background: linear-gradient(135deg, #6B3FFF 0%, #FF3C78 100%);
        border-radius: 20px;
        display: flex; align-items: center; justify-content: center;
        font-size: 2rem;
        box-shadow: 0 8px 28px rgba(107,63,255,0.30);
    }
    .brand-title {
        font-family: 'Syne', sans-serif !important;
        font-weight: 800; font-size: 2.1rem;
        letter-spacing: -0.04em; color: #1A0A3D;
        margin-bottom: 0.2rem;
    }
    .brand-sub {
        font-size: 0.70rem; font-weight: 500;
        letter-spacing: 0.14em; text-transform: uppercase;
        color: #8A78BF;
    }

    /* ── Input labels ── */
    [data-testid="stTextInput"] label {
        font-size: 0.70rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.10em !important;
        text-transform: uppercase !important;
        color: #8A78BF !important;
        font-family: 'DM Sans', sans-serif !important;
        margin-bottom: 0.3rem !important;
    }

    /* ── Input fields ── */
    [data-testid="stTextInput"] input {
        background: #F8F6FF !important;
        border: 1.5px solid rgba(107,63,255,0.15) !important;
        border-radius: 12px !important;
        color: #1A0A3D !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.95rem !important;
        padding: 0.75rem 1rem !important;
        transition: border-color 0.18s, box-shadow 0.18s !important;
        box-shadow: none !important;
    }
    [data-testid="stTextInput"] input:focus {
        border-color: #6B3FFF !important;
        background: #FFFFFF !important;
        box-shadow: 0 0 0 3px rgba(107,63,255,0.10) !important;
        outline: none !important;
    }
    [data-testid="stTextInput"] input::placeholder { color: #C4B8EA !important; }

    /* Kill ALL baseweb borders/outlines including red validation state */
    [data-testid="stTextInput"] [data-baseweb="base-input"],
    [data-testid="stTextInput"] [data-baseweb="input-container"],
    [data-testid="stTextInput"] [data-baseweb="input-container"]:focus-within,
    [data-testid="stTextInput"] [data-baseweb="input-container"]:hover,
    [data-testid="stTextInput"] > div,
    [data-testid="stTextInput"] > div > div,
    [data-testid="stTextInput"] > div > div:focus-within {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
        padding: 0 !important;
    }

    /* Nuke the red border Streamlit adds on password fields */
    [data-testid="stTextInput"] input:invalid,
    [data-testid="stTextInput"] input[aria-invalid="true"],
    [data-testid="stTextInput"] * {
        border-color: transparent !important;
        box-shadow: none !important;
    }

    /* ── Full-width button ── */
    [data-testid="stButton"],
    [data-testid="stButton"] > div,
    [data-testid="stBaseButton-secondary"] {
        width: 100% !important;
    }
    [data-testid="stButton"] > button,
    [data-testid="stBaseButton-secondary"] {
        width: 100% !important;
        background: linear-gradient(135deg, #6B3FFF 0%, #9B6BFF 100%) !important;
        color: #FFFFFF !important;
        font-family: 'Syne', sans-serif !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        letter-spacing: 0.02em !important;
        border: none !important;
        border-radius: 13px !important;
        padding: 0.85rem 1.5rem !important;
        cursor: pointer !important;
        box-shadow: 0 4px 20px rgba(107,63,255,0.38) !important;
        transition: all 0.18s ease !important;
        margin-top: 0.5rem !important;
    }
    [data-testid="stButton"] > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 8px 28px rgba(107,63,255,0.48) !important;
        background: linear-gradient(135deg, #7B4FFF 0%, #AB7BFF 100%) !important;
    }
    [data-testid="stButton"] > button:active {
        transform: translateY(0) !important;
        box-shadow: 0 2px 10px rgba(107,63,255,0.3) !important;
    }

    /* ── Alerts ── */
    [data-testid="stAlert"] {
        border-radius: 12px !important;
        border: none !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.88rem !important;
    }

    /* ── Fade-up ── */
    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(14px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .animate { animation: fadeUp 0.45s ease both; }
    </style>
    """, unsafe_allow_html=True)


def _init_session():
    defaults = {
        "logged_in": False,
        "token":     None,
        "user_id":   None,
        "user_name": None,
        "role_id":   None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _restore_session():
    if st.session_state["logged_in"]:
        return
    token = st.query_params.get("token")
    if not token:
        return
    try:
        res = requests.get(
            f"{BASE_URL}/api/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8,
        )
        if res.status_code == 200:
            user = res.json()
            st.session_state.update({
                "token":     token,
                "user_id":   user["id"],
                "user_name": user["name"],
                "role_id":   user["role_id"],
                "logged_in": True,
            })
            st.rerun()
    except Exception:
        pass


def show_login():
    _inject_css()
    _init_session()
    _restore_session()

    # ── Brand sits OUTSIDE the card ──────────
    st.markdown("""
    <div class="brand-wrap animate">
        <div class="brand-icon">💎</div>
        <div class="brand-title">Margin Monitor</div>
        <div class="brand-sub">Billing &amp; Finance Platform</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Everything inside st.container() becomes a nested
    #    stVerticalBlock which we style as the white card ──
    with st.container():

        if st.session_state["logged_in"]:
            st.markdown(f"""
            <div style="text-align:center; padding: 0.5rem 0 1rem;">
                <div style="font-size:2rem; margin-bottom:0.5rem;">👋</div>
                <div style="font-family:'Syne',sans-serif;font-weight:700;
                            font-size:1.3rem;color:#1A0A3D;margin-bottom:0.2rem;">
                    Welcome back, {st.session_state['user_name']}
                </div>
                <div style="font-size:0.82rem;color:#8A78BF;letter-spacing:0.04em;">
                    You're signed in successfully
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("Sign out", key="logout_btn", use_container_width=True):
                logout()

        else:
            email = st.text_input(
                "Email Address",
                placeholder="you@company.com",
                key="email_input",
            )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="••••••••••",
                key="pass_input",
            )

            if st.button("Sign in  →", key="login_btn", use_container_width=True):
                if not email or not password:
                    st.warning("⚠️  Please enter both your email and password.")
                else:
                    with st.spinner("Authenticating…"):
                        try:
                            res = requests.post(
                                f"{BASE_URL}/api/login",
                                json={"email": email.strip(), "password": password.strip()},
                                timeout=10,
                            )
                            if res.status_code != 200:
                                st.error("❌  Invalid credentials. Please try again.")
                            else:
                                data  = res.json()
                                token = data["access_token"]
                                st.session_state.update({
                                    "token":     token,
                                    "user_id":   data["user"]["id"],
                                    "user_name": data["user"]["name"],
                                    "role_id":   data["user"]["role_id"],
                                    "logged_in": True,
                                })
                                st.query_params["token"] = token
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌  Could not reach the server. ({e})")

            # Divider inside the card
            st.markdown("""
            <div style="display:flex;align-items:center;gap:10px;margin:1.5rem 0 0;color:#C4B8EA;font-size:0.72rem;">
                <div style="flex:1;height:1px;background:rgba(107,63,255,0.12);"></div>
                <span style="
                    display:inline-flex;align-items:center;gap:5px;
                    background:#F0EDFD;color:#6B3FFF;
                    font-size:0.68rem;font-weight:500;letter-spacing:0.06em;
                    padding:3px 10px;border-radius:20px;border:1px solid #DDD7F9;">
                    &#9679;&nbsp; Secured with JWT
                </span>
                <div style="flex:1;height:1px;background:rgba(107,63,255,0.12);"></div>
            </div>
            """, unsafe_allow_html=True)

    # ── Footer sits OUTSIDE the card ─────────
    st.markdown("""
    <div style="text-align:center;font-size:0.72rem;color:#A898D8;
                margin-top:1.25rem;letter-spacing:0.02em;">
        Protected by 256-bit encryption &nbsp;·&nbsp; &copy; 2025 Evolve Brands Pvt Ltd
    </div>
    """, unsafe_allow_html=True)


def logout():
    st.session_state.clear()
    st.query_params.clear()
    st.rerun()