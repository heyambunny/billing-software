import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Overview Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =====================================================
# GLOBAL CSS
# =====================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

section.main > div { padding-top: 1.5rem !important; }

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background: #f8fafc !important;
}

/* ---- KPI card grid ---- */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 14px;
    margin-bottom: 1.5rem;
}

.kpi-card {
    background: #ffffff;
    border-radius: 12px;
    padding: 18px 18px 14px;
    border: 1px solid #e2e8f0;
    border-top: 4px solid var(--accent);
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    position: relative;
    overflow: hidden;
}

.kpi-card::after {
    content: '';
    position: absolute;
    top: -20px; right: -20px;
    width: 70px; height: 70px;
    background: var(--accent);
    opacity: 0.07;
    border-radius: 50%;
}

.kpi-icon {
    font-size: 1.2rem;
    margin-bottom: 8px;
    display: block;
}

.kpi-label {
    font-size: 0.67rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #94a3b8;
    margin-bottom: 6px;
}

.kpi-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.1rem;
    font-weight: 500;
    color: #1e293b;
    line-height: 1.2;
}

/* ---- Section headers ---- */
.section-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 1.25rem 0 0.6rem;
}

.section-title {
    font-size: 0.92rem;
    font-weight: 600;
    color: #1e293b;
    letter-spacing: -0.01em;
}

.section-pill {
    font-size: 0.67rem;
    font-weight: 600;
    background: #f1f5f9;
    color: #64748b;
    padding: 2px 8px;
    border-radius: 99px;
    letter-spacing: 0.04em;
    border: 1px solid #e2e8f0;
}

/* ---- Supervisor breakdown header ---- */
.sup-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-left: 4px solid #6366f1;
    border-radius: 8px;
    margin: 1rem 0 0.4rem;
}

.sup-name {
    font-size: 0.88rem;
    font-weight: 600;
    color: #334155;
}

.sup-count {
    margin-left: auto;
    font-size: 0.72rem;
    color: #94a3b8;
    font-weight: 500;
}

/* ---- Page title ---- */
.page-title-block {
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #e2e8f0;
}

.page-title-block h1 {
    font-size: 1.4rem;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.03em;
    margin: 0 0 4px;
}

.page-subtitle {
    font-size: 0.75rem;
    color: #94a3b8;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    font-weight: 500;
}

/* ---- Divider ---- */
.custom-divider {
    height: 1px;
    background: linear-gradient(to right, #e2e8f0 60%, transparent);
    margin: 1.25rem 0;
}

/* hide default streamlit metrics */
[data-testid="metric-container"] { display: none !important; }

</style>
""", unsafe_allow_html=True)

# =====================================================
# CHART THEME
# =====================================================

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#ffffff",
    font=dict(family="Inter, sans-serif", color="#64748b", size=11),
    xaxis=dict(
        gridcolor="#f1f5f9",
        linecolor="#e2e8f0",
        tickfont=dict(color="#94a3b8", size=10),
        title_font=dict(color="#94a3b8", size=10)
    ),
    yaxis=dict(
        gridcolor="#f1f5f9",
        linecolor="#e2e8f0",
        tickfont=dict(color="#94a3b8", size=10),
        title_font=dict(color="#94a3b8", size=10)
    ),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(color="#64748b", size=11),
        orientation="h",
        yanchor="bottom", y=1.02,
        xanchor="left", x=0
    ),
    margin=dict(l=8, r=8, t=36, b=8)
)

PAL = {
    "billing": "#3b82f6",
    "margin":  "#10b981",
    "expense": "#f59e0b",
    "credit":  "#ef4444",
    "line":    "#6366f1",
}

# =====================================================
# API CONFIG
# =====================================================

BASE_URL = "http://localhost:8000/api"

# =====================================================
# HELPERS
# =====================================================

def format_inr_cr(amount):
    if amount is None:
        return "₹ 0 Cr"
    crore = float(amount) / 10_000_000
    return f"₹ {crore:,.2f} Cr"


def kpi_card(label, value, icon, accent):
    return f"""
    <div class="kpi-card" style="--accent:{accent}">
        <span class="kpi-icon">{icon}</span>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
    </div>
    """


def section_header(icon, title, pill=None):
    pill_html = f'<span class="section-pill">{pill}</span>' if pill else ""
    st.markdown(f"""
    <div class="section-header">
        <span>{icon}</span>
        <span class="section-title">{title}</span>
        {pill_html}
    </div>
    """, unsafe_allow_html=True)


def supervisor_header(name, client_count):
    st.markdown(f"""
    <div class="sup-header">
        <span>👤</span>
        <span class="sup-name">{name}</span>
        <span class="sup-count">{client_count} client{'s' if client_count != 1 else ''}</span>
    </div>
    """, unsafe_allow_html=True)

# =====================================================
# DATA FETCH
# =====================================================

def fetch_supervisor_overview(token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BASE_URL}/supervisor-overview", headers=headers)
    except Exception:
        return pd.DataFrame()

    if response.status_code != 200:
        st.error("Failed to fetch overview data")
        return pd.DataFrame()

    data = response.json()
    if not data.get("success"):
        st.error(data.get("message"))
        return pd.DataFrame()

    df = pd.DataFrame(data.get("data", []))
    if df.empty:
        return df

    for col in ["total_billing", "total_vendor_expense",
                "total_credit_notes", "total_margin", "margin_percentage"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def fetch_supervisor_client_breakdown(token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BASE_URL}/supervisor-client-breakdown", headers=headers)
    except Exception:
        return pd.DataFrame()

    if response.status_code != 200:
        return pd.DataFrame()

    data = response.json()
    if not data.get("success"):
        return pd.DataFrame()

    df = pd.DataFrame(data.get("data", []))
    if df.empty:
        return df

    for col in ["total_billing", "total_vendor_expense",
                "total_credit_notes", "total_margin"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df

# =====================================================
# MAIN PAGE
# =====================================================

def render_overview_page(token):

    # ---- Page title ----
    st.markdown("""
    <div class="page-title-block">
        <h1>📊 Overview Dashboard</h1>
        <div class="page-subtitle">Financial Performance · All Supervisors</div>
    </div>
    """, unsafe_allow_html=True)

    overview_df = fetch_supervisor_overview(token)

    if overview_df.empty:
        st.warning("No overview data available.")
        return

    # =================================================
    # KPI CARDS  (pure HTML — always renders correctly)
    # =================================================

    total_supervisors    = overview_df["supervisor_id"].nunique()
    total_billing        = overview_df["total_billing"].sum()
    total_vendor_expense = overview_df["total_vendor_expense"].sum()
    total_credit_notes   = overview_df["total_credit_notes"].sum()
    total_margin         = overview_df["total_margin"].sum()
    avg_margin_pct       = overview_df["margin_percentage"].mean()

    st.markdown(f"""
    <div class="kpi-grid">
        {kpi_card("Total Billing",   format_inr_cr(total_billing),        "💰", "#3b82f6")}
        {kpi_card("Total Margin",    format_inr_cr(total_margin),         "📈", "#10b981")}
        {kpi_card("Margin %",        f"{avg_margin_pct:.2f}%",            "🎯", "#6366f1")}
        {kpi_card("Vendor Expense",  format_inr_cr(total_vendor_expense), "🧾", "#f59e0b")}
        {kpi_card("Credit Notes",    format_inr_cr(total_credit_notes),   "📋", "#ef4444")}
        {kpi_card("Supervisors",     str(total_supervisors),              "👥", "#0ea5e9")}
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # =================================================
    # SUPERVISOR COMPARISON TABLE
    # =================================================

    section_header("📋", "Supervisor Comparison", f"{total_supervisors} supervisors")

    cdf = overview_df.copy()
    for col in ["total_billing", "total_vendor_expense", "total_credit_notes", "total_margin"]:
        cdf[col] = cdf[col].apply(format_inr_cr)
    cdf["margin_percentage"] = cdf["margin_percentage"].apply(lambda x: f"{x:.2f}%")

    cdf = cdf[[
        "supervisor_name", "total_clients",
        "total_billing", "total_vendor_expense",
        "total_credit_notes", "total_margin", "margin_percentage"
    ]].rename(columns={
        "supervisor_name":      "Supervisor",
        "total_clients":        "Clients",
        "total_billing":        "Billing",
        "total_vendor_expense": "Vendor Expense",
        "total_credit_notes":   "Credit Notes",
        "total_margin":         "Margin",
        "margin_percentage":    "Margin %"
    })

    st.dataframe(cdf, use_container_width=True, hide_index=True)

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # =================================================
    # CHARTS  row 1
    # =================================================

    chart_df = overview_df.copy()
    chart_df["Billing (Cr)"] = chart_df["total_billing"] / 10_000_000
    chart_df["Margin (Cr)"]  = chart_df["total_margin"]  / 10_000_000

    col_left, col_right = st.columns(2, gap="medium")

    with col_left:
        section_header("📊", "Billing vs Margin")
        fig_bm = go.Figure()
        fig_bm.add_trace(go.Bar(
            name="Billing",
            x=chart_df["supervisor_name"],
            y=chart_df["Billing (Cr)"],
            marker=dict(color=PAL["billing"], line=dict(width=0)),
            opacity=0.9
        ))
        fig_bm.add_trace(go.Bar(
            name="Margin",
            x=chart_df["supervisor_name"],
            y=chart_df["Margin (Cr)"],
            marker=dict(color=PAL["margin"], line=dict(width=0)),
            opacity=0.9
        ))
        fig_bm.update_layout(
            **CHART_LAYOUT,
            barmode="group",
            height=320,
            xaxis_title="Supervisor",
            yaxis_title="₹ Crore",
            bargap=0.25,
            bargroupgap=0.1,
        )
        st.plotly_chart(fig_bm, use_container_width=True,
                        config={"displayModeBar": False})

    with col_right:
        section_header("🎯", "Margin %")
        fig_mp = go.Figure()
        fig_mp.add_trace(go.Scatter(
            x=overview_df["supervisor_name"],
            y=overview_df["margin_percentage"],
            mode="lines+markers+text",
            line=dict(color=PAL["line"], width=2.5),
            marker=dict(size=9, color=PAL["line"],
                        line=dict(color="#ffffff", width=2)),
            text=overview_df["margin_percentage"].apply(lambda v: f"{v:.1f}%"),
            textposition="top center",
            textfont=dict(size=11, color="#334155", family="JetBrains Mono"),
            fill="tozeroy",
            fillcolor="rgba(99,102,241,0.07)"
        ))
        fig_mp.update_layout(
            **CHART_LAYOUT,
            height=320,
            xaxis_title="Supervisor",
            yaxis_title="Margin %",
        )
        st.plotly_chart(fig_mp, use_container_width=True,
                        config={"displayModeBar": False})

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # ---- Expense breakdown ----
    section_header("🧾", "Expense Breakdown by Supervisor")

    exp_df = overview_df.copy()
    exp_df["Vendor Exp (Cr)"]   = exp_df["total_vendor_expense"] / 10_000_000
    exp_df["Credit Notes (Cr)"] = exp_df["total_credit_notes"]   / 10_000_000

    fig_exp = go.Figure()
    fig_exp.add_trace(go.Bar(
        name="Vendor Expense",
        x=exp_df["supervisor_name"],
        y=exp_df["Vendor Exp (Cr)"],
        marker=dict(color=PAL["expense"], line=dict(width=0)),
        opacity=0.9
    ))
    fig_exp.add_trace(go.Bar(
        name="Credit Notes",
        x=exp_df["supervisor_name"],
        y=exp_df["Credit Notes (Cr)"],
        marker=dict(color=PAL["credit"], line=dict(width=0)),
        opacity=0.9
    ))
    fig_exp.update_layout(
        **CHART_LAYOUT,
        barmode="stack",
        height=300,
        xaxis_title="Supervisor",
        yaxis_title="₹ Crore",
        bargap=0.35,
    )
    st.plotly_chart(fig_exp, use_container_width=True,
                    config={"displayModeBar": False})

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # =================================================
    # SUPERVISOR CLIENT BREAKDOWN
    # =================================================

    section_header("👤", "Supervisor-wise Client Revenue")

    client_df = fetch_supervisor_client_breakdown(token)

    if client_df.empty:
        st.warning("No client breakdown available.")
    else:
        for supervisor in client_df["supervisor_name"].unique():

            s_df = client_df[client_df["supervisor_name"] == supervisor].copy()
            supervisor_header(supervisor, len(s_df))

            for col in ["total_billing", "total_vendor_expense",
                        "total_credit_notes", "total_margin"]:
                s_df[col] = s_df[col].apply(format_inr_cr)

            s_df = s_df[[
                "client_name", "total_billing",
                "total_vendor_expense", "total_credit_notes", "total_margin"
            ]].rename(columns={
                "client_name":          "Client",
                "total_billing":        "Billing",
                "total_vendor_expense": "Vendor Expense",
                "total_credit_notes":   "Credit Notes",
                "total_margin":         "Margin"
            })

            st.dataframe(s_df, use_container_width=True, hide_index=True)
            st.markdown("<div style='margin-bottom:0.75rem'></div>",
                        unsafe_allow_html=True)