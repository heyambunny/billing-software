import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from config import BASE_URL


# ================= FORMAT =================
def format_inr_short(value):
    if value >= 1e7:
        return f"₹ {value/1e7:.2f} Cr"
    elif value >= 1e5:
        return f"₹ {value/1e5:.2f} L"
    return f"₹ {value:,.0f}"


# ================= THEME COLORS =================
PURPLE      = "#7C3AED"
PURPLE_LIGHT= "#C4B5FD"
LAVENDER    = "#E3DFF5"
GREEN       = "#10B981"
AMBER       = "#F59E0B"
RED         = "#EF4444"
BG          = "#EEEAF8"
CARD_BG     = "#FFFFFF"
TEXT_MAIN   = "#1a1040"
TEXT_MUTED  = "#9990CC"


def plotly_layout(fig, height=320):
    """Apply consistent Margin Monitor styling to any plotly figure."""
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI, system-ui, sans-serif", color=TEXT_MAIN),
        margin=dict(l=12, r=12, t=12, b=12),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="left", x=0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11, color=TEXT_MUTED)
        ),
        xaxis=dict(
            gridcolor=LAVENDER,
            linecolor=LAVENDER,
            tickfont=dict(size=11, color=TEXT_MUTED),
            title_font=dict(size=11, color=TEXT_MUTED)
        ),
        yaxis=dict(
            gridcolor=LAVENDER,
            linecolor=LAVENDER,
            tickfont=dict(size=11, color=TEXT_MUTED),
            title_font=dict(size=11, color=TEXT_MUTED)
        )
    )
    return fig


def show_dashboard(conn):

    st.set_page_config(layout="wide", page_title="Margin Monitor", page_icon="💎")

    # ================= GLOBAL CSS =================
    st.markdown(f"""
        <style>
        @import url('https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/tabler-icons.min.css');

        /* ── Page background ── */
        .stApp {{
            background-color: {BG} !important;
        }}

        /* ── Hide default Streamlit chrome ── */
        #MainMenu, footer, header {{ visibility: hidden; }}
        .block-container {{
            padding: 2rem 2.5rem 2rem 2.5rem !important;
            max-width: 1400px !important;
        }}

        /* ── Metric cards ── */
        .mm-card {{
            background: {CARD_BG};
            border: 1px solid {LAVENDER};
            border-radius: 12px;
            padding: 18px 20px;
            position: relative;
            overflow: hidden;
        }}
        .mm-card::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 3px;
            border-radius: 12px 12px 0 0;
            background: linear-gradient(90deg, {PURPLE}, #a855f7);
        }}
        .mm-card.green::before  {{ background: linear-gradient(90deg, #059669, {GREEN}); }}
        .mm-card.amber::before  {{ background: linear-gradient(90deg, #D97706, {AMBER}); }}
        .mm-card.red::before    {{ background: linear-gradient(90deg, #DC2626, {RED}); }}
        .mm-card.muted::before  {{ background: {LAVENDER}; }}

        .mm-card-label {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            color: {TEXT_MUTED};
            margin-bottom: 6px;
            font-weight: 600;
        }}
        .mm-card-value {{
            font-size: 26px;
            font-weight: 700;
            color: {TEXT_MAIN};
            line-height: 1.1;
        }}
        .mm-card-change {{
            font-size: 11px;
            margin-top: 6px;
            color: #059669;
        }}
        .mm-card-change.neg   {{ color: #DC2626; }}
        .mm-card-change.muted {{ color: {TEXT_MUTED}; }}

        /* ── Section labels ── */
        .mm-section {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: {TEXT_MUTED};
            font-weight: 700;
            margin: 28px 0 10px 0;
        }}

        /* ── Chart wrapper ── */
        .mm-chart-card {{
            background: {CARD_BG};
            border: 1px solid {LAVENDER};
            border-radius: 12px;
            padding: 20px;
        }}
        .mm-chart-title {{
            font-size: 14px;
            font-weight: 700;
            color: {TEXT_MAIN};
            margin-bottom: 3px;
        }}
        .mm-chart-sub {{
            font-size: 11px;
            color: {TEXT_MUTED};
            margin-bottom: 0;
        }}

        /* ── Status pills ── */
        .pill {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 700;
        }}
        .pill-healthy {{ background: #D1FAE5; color: #065F46; }}
        .pill-watch   {{ background: #FEF3C7; color: #92400E; }}
        .pill-risk    {{ background: #FEE2E2; color: #991B1B; }}

        /* ── Page header ── */
        .mm-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 28px;
            padding-bottom: 20px;
            border-bottom: 1px solid {LAVENDER};
        }}
        .mm-logo {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .mm-gem {{
            width: 42px; height: 42px;
            background: linear-gradient(135deg, #a855f7, #ec4899);
            border-radius: 12px;
            display: flex; align-items: center; justify-content: center;
            font-size: 22px; color: #fff;
        }}
        .mm-title {{
            font-size: 22px; font-weight: 700; color: {TEXT_MAIN};
        }}
        .mm-subtitle {{
            font-size: 12px; color: {TEXT_MUTED}; margin-top: 2px;
        }}
        .mm-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: {CARD_BG};
            border: 1px solid {LAVENDER};
            border-radius: 20px;
            padding: 6px 14px;
            font-size: 12px;
            color: #5A5280;
        }}
        .mm-dot {{
            width: 7px; height: 7px;
            border-radius: 50%;
            background: {PURPLE};
            display: inline-block;
        }}

        /* ── Rec card ── */
        .mm-rec-card {{
            background: {CARD_BG};
            border: 1px solid {LAVENDER};
            border-radius: 12px;
            padding: 20px;
        }}
        .mm-rec-item {{
            display: flex;
            align-items: flex-start;
            gap: 12px;
            padding: 12px 0;
            border-bottom: 1px solid #F5F3FC;
        }}
        .mm-rec-item:last-child {{ border-bottom: none; padding-bottom: 0; }}
        .mm-rec-item:first-child {{ padding-top: 0; }}
        .mm-rec-icon {{
            width: 32px; height: 32px;
            border-radius: 8px;
            display: flex; align-items: center; justify-content: center;
            flex-shrink: 0; font-size: 16px;
        }}
        .mm-rec-icon.purple {{ background: #EDE9FE; color: #6D28D9; }}
        .mm-rec-icon.amber  {{ background: #FEF3C7; color: #D97706; }}
        .mm-rec-icon.teal   {{ background: #D1FAE5; color: #065F46; }}
        .mm-rec-title {{ font-weight: 700; font-size: 12px; color: {TEXT_MAIN}; margin-bottom: 2px; }}
        .mm-rec-body  {{ font-size: 11px; color: #5A5280; }}

        /* ── Quarter cards ── */
        .mm-quarter-card {{
            background: #FAFAFE;
            border: 1px solid {LAVENDER};
            border-radius: 10px;
            padding: 16px 18px;
            text-align: center;
        }}
        .mm-q-label  {{ font-size: 10px; color: {TEXT_MUTED}; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 700; margin-bottom: 6px; }}
        .mm-q-val    {{ font-size: 20px; font-weight: 700; color: {TEXT_MAIN}; }}
        .mm-q-growth {{ font-size: 11px; margin-top: 6px; color: #059669; }}
        .mm-q-growth.neg {{ color: #DC2626; }}

        /* ── Dataframe styling ── */
        .stDataFrame {{ border-radius: 10px; overflow: hidden; }}
        div[data-testid="stDataFrame"] > div {{
            border: 1px solid {LAVENDER} !important;
            border-radius: 10px !important;
        }}

        /* ── Plotly chart border ── */
        div[data-testid="stPlotlyChart"] > div {{
            border-radius: 0 !important;
        }}

        /* ── Divider ── */
        hr {{ border-color: {LAVENDER} !important; }}

        /* ── Streamlit headings override ── */
        h1, h2, h3 {{ color: {TEXT_MAIN} !important; }}
        </style>
    """, unsafe_allow_html=True)

    # ================= HEADER =================
    st.markdown(f"""
        <div class="mm-header">
            <div class="mm-logo">
                <div class="mm-gem">💎</div>
                <div>
                    <div class="mm-title">Margin Monitor</div>
                    <div class="mm-subtitle">Management Dashboard &nbsp;·&nbsp; FY 2024–25</div>
                </div>
            </div>
            <div style="display:flex; gap:10px; align-items:center;">
                <span class="mm-badge"><span class="mm-dot"></span> Secured with JWT</span>
                <span class="mm-badge">📅 Apr 2025</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # ================= API CALL =================
    import requests

    token = st.session_state.get("token")
    headers = {"Authorization": f"Bearer {token}"}

    res = requests.get(f"{BASE_URL}/api/dashboard", headers=headers)

    if res.status_code != 200:
        st.error("Failed to fetch dashboard data")
        return

    df = pd.DataFrame(res.json())

    if df.empty:
        st.warning("No data available")
        return

    # ================= DATE =================
    df["invoice_month_parsed"] = pd.to_datetime(
        df["invoice_month"], format="%b-%y", errors="coerce"
    )
    df["month"] = df["invoice_month_parsed"].dt.month

    def get_quarter(m):
        if m in [4, 5, 6]:   return "Q1"
        elif m in [7, 8, 9]: return "Q2"
        elif m in [10,11,12]:return "Q3"
        else:                 return "Q4"

    df["quarter"] = df["month"].apply(get_quarter)

    # ================= CALCULATIONS =================
    df["gross_margin"] = (
        df["client_billed_amount"] - df["vendor_cost"] - df["credit_note"]
    )

    # ================= FINANCIAL SPLITS =================
    billed    = df[df["expense_type_id"] != 1]
    projected = df[df["expense_type_id"] == 1]

    def calc(d):
        amt = d["client_billed_amount"].sum()
        ven = d["vendor_cost"].sum()
        mar = d["gross_margin"].sum()
        pct = (mar / amt * 100) if amt else 0
        return amt, ven, mar, pct

    b_amt, b_ven, b_mar, b_pct = calc(billed)
    p_amt, p_ven, p_mar, p_pct = calc(projected)
    t_amt = b_amt + p_amt
    t_ven = b_ven + p_ven
    t_mar = b_mar + p_mar
    t_pct = (t_mar / t_amt * 100) if t_amt else 0

    # ================= METRIC CARD HELPER =================
    def metric_card(label, value, change_text="", change_type="", accent=""):
        val_str = format_inr_short(value) if not label.endswith("%") else f"{value:.2f}%"
        change_cls = f"mm-card-change {change_type}" if change_type else "mm-card-change muted"
        change_html = f'<div class="{change_cls}">{change_text}</div>' if change_text else ""
        return f"""
        <div class="mm-card {accent}">
            <div class="mm-card-label">{label}</div>
            <div class="mm-card-value">{val_str}</div>
            {change_html}
        </div>"""

    def render_metric_row(title, data_tuple, accents=None, change_texts=None, change_types=None):
        amt, ven, mar, pct = data_tuple
        accents = accents or ["", "green", "", "amber"]
        changes = change_texts or ["", "", "", ""]
        ctypes  = change_types  or ["muted", "muted", "muted", "muted"]

        st.markdown(f'<div class="mm-section">{title}</div>', unsafe_allow_html=True)
        cols = st.columns(4)
        items = [
            ("Revenue",    amt, False),
            ("Vendor Cost",ven, False),
            ("Gross Margin",mar, False),
            ("Margin %",   pct, True),
        ]
        for i, (label, val, is_pct) in enumerate(items):
            lbl = label + " %" if is_pct and "%" not in label else label
            val_str = f"{val:.2f}%" if is_pct else format_inr_short(val)
            change_cls = f"mm-card-change {ctypes[i]}"
            change_html = f'<div class="{change_cls}">{changes[i]}</div>' if changes[i] else ""
            cols[i].markdown(f"""
                <div class="mm-card {accents[i]}">
                    <div class="mm-card-label">{label}</div>
                    <div class="mm-card-value">{val_str}</div>
                    {change_html}
                </div>
            """, unsafe_allow_html=True)

    # ── A. Billed ──
    render_metric_row(
        "A. Billed",
        (b_amt, b_ven, b_mar, b_pct),
        accents=["", "green", "", "amber"],
        change_texts=["↑ vs last year", "↓ vs last year", "↑ vs last year", "↑ pts vs last year"],
        change_types=["", "neg", "", ""]
    )

    # ── B. Projected ──
    render_metric_row(
        "B. Projected",
        (p_amt, p_ven, p_mar, p_pct),
        accents=["muted", "muted", "muted", "muted"],
        change_texts=["Estimated", "Estimated", "Estimated", "Estimated"],
        change_types=["muted", "muted", "muted", "muted"]
    )

    # ── C. Total ──
    render_metric_row(
        "C. Total",
        (t_amt, t_ven, t_mar, t_pct),
        accents=["", "green", "", "amber"],
        change_texts=["Combined", "Combined", "Combined", "Blended"],
        change_types=["muted", "muted", "muted", "muted"]
    )

    # ================= CLIENT AGG =================
    client_df = df.groupby("client_name").agg({
        "client_billed_amount": "sum",
        "vendor_cost": "sum",
        "gross_margin": "sum"
    }).reset_index()

    client_df["efficiency"] = (
        client_df["gross_margin"] / client_df["client_billed_amount"] * 100
    ).round(2)

    client_df = client_df.sort_values("gross_margin", ascending=False)

    # ================= CHARTS ROW 1 =================
    st.markdown('<div class="mm-section">Charts &amp; Analysis</div>', unsafe_allow_html=True)

    col_left, col_right = st.columns([1.65, 1])

    with col_left:
        st.markdown("""
            <div class="mm-chart-card">
                <div class="mm-chart-title">Client Performance</div>
                <div class="mm-chart-sub">Billing vs expense vs margin by client</div>
            </div>
        """, unsafe_allow_html=True)

        fig_client = go.Figure()
        fig_client.add_bar(
            x=client_df["client_name"],
            y=client_df["client_billed_amount"],
            name="Billing",
            marker_color=PURPLE,
            marker_line_width=0
        )
        fig_client.add_bar(
            x=client_df["client_name"],
            y=client_df["vendor_cost"],
            name="Expense",
            marker_color=LAVENDER,
            marker_line_width=0
        )
        fig_client.add_scatter(
            x=client_df["client_name"],
            y=client_df["gross_margin"],
            mode="lines+markers",
            name="Margin",
            line=dict(color=GREEN, width=2),
            marker=dict(color=GREEN, size=6),
            yaxis="y2"
        )
        fig_client.update_layout(
            barmode="group",
            yaxis2=dict(overlaying="y", side="right", gridcolor="rgba(0,0,0,0)",
                        tickfont=dict(size=11, color=TEXT_MUTED)),
            legend=dict(orientation="h", y=1.08, x=0, bgcolor="rgba(0,0,0,0)",
                        font=dict(size=11, color=TEXT_MUTED))
        )
        plotly_layout(fig_client, height=320)
        st.plotly_chart(fig_client, use_container_width=True)

    with col_right:
        st.markdown("""
            <div class="mm-chart-card">
                <div class="mm-chart-title">Revenue Funnel</div>
                <div class="mm-chart-sub">Billed vs projected split</div>
            </div>
        """, unsafe_allow_html=True)

        fig_funnel = px.pie(
            pd.DataFrame({"Stage": ["Billed", "Projected"], "Amount": [b_amt, p_amt]}),
            names="Stage", values="Amount",
            hole=0.65,
            color_discrete_sequence=[PURPLE, LAVENDER]
        )
        fig_funnel.update_traces(
            textinfo="percent",
            textfont_size=13,
            hovertemplate="<b>%{label}</b><br>%{percent}<extra></extra>"
        )
        plotly_layout(fig_funnel, height=320)
        st.plotly_chart(fig_funnel, use_container_width=True)

    # ================= CHARTS ROW 2 =================
    col_rank, col_recs = st.columns([1.65, 1])

    with col_rank:
        st.markdown("""
            <div class="mm-chart-card">
                <div class="mm-chart-title">Profitability Ranking</div>
                <div class="mm-chart-sub">Top clients by gross margin</div>
            </div>
        """, unsafe_allow_html=True)

        top10 = client_df.head(10)
        colors = [PURPLE if i < 3 else PURPLE_LIGHT if i < 6 else LAVENDER
                  for i in range(len(top10))]

        fig_rank = px.bar(
            top10,
            x="gross_margin",
            y="client_name",
            orientation="h",
            color_discrete_sequence=[PURPLE]
        )
        fig_rank.update_traces(marker_color=colors, marker_line_width=0)
        fig_rank.update_layout(
            xaxis_title="Gross Margin",
            yaxis_title="",
            yaxis=dict(autorange="reversed")
        )
        plotly_layout(fig_rank, height=340)
        st.plotly_chart(fig_rank, use_container_width=True)

    with col_recs:
        avg_eff    = client_df["efficiency"].mean()
        top_clients = client_df[client_df["efficiency"] >= avg_eff].head(3)["client_name"].tolist()
        low_clients = client_df.sort_values("efficiency").head(3)["client_name"].tolist()

        st.markdown(f"""
            <div class="mm-rec-card">
                <div class="mm-chart-title" style="margin-bottom:14px;">Smart Recommendations</div>
                <div class="mm-rec-item">
                    <div class="mm-rec-icon purple">🚀</div>
                    <div>
                        <div class="mm-rec-title">Scale these clients</div>
                        <div class="mm-rec-body">{", ".join(top_clients)}</div>
                    </div>
                </div>
                <div class="mm-rec-item">
                    <div class="mm-rec-icon amber">⚠️</div>
                    <div>
                        <div class="mm-rec-title">Improve margins on</div>
                        <div class="mm-rec-body">{", ".join(low_clients)}</div>
                    </div>
                </div>
                <div class="mm-rec-item">
                    <div class="mm-rec-icon teal">📊</div>
                    <div>
                        <div class="mm-rec-title">Avg efficiency</div>
                        <div class="mm-rec-body">{avg_eff:.2f}% across all clients</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # ================= VENDOR DISTRIBUTION =================
    st.markdown('<div class="mm-section">Vendor &amp; Contribution</div>', unsafe_allow_html=True)

    col_v, col_c = st.columns(2)

    PIE_COLORS = [PURPLE, PURPLE_LIGHT, "#A78BFA", "#DDD6FE", LAVENDER, "#EDE9FE", "#F5F3FF", "#C4B5FD"]

    def make_pie(df_pie, names_col, values_col, title, subtitle, colors):
        fig = px.pie(
            df_pie, names=names_col, values=values_col, hole=0.52,
            color_discrete_sequence=colors
        )
        fig.update_traces(
            textinfo="none",
            hovertemplate="<b>%{label}</b><br>%{percent:.1%}<extra></extra>"
        )
        fig.update_layout(
            title=dict(
                text=f"<b>{title}</b><br><span style='font-size:11px;color:{TEXT_MUTED}'>{subtitle}</span>",
                x=0, xanchor="left",
                font=dict(size=14, color=TEXT_MAIN),
                pad=dict(l=4)
            ),
            legend=dict(
                orientation="h",
                x=0.5, y=-0.15,
                xanchor="center", yanchor="top",
                font=dict(size=10, color=TEXT_MUTED),
                bgcolor="rgba(0,0,0,0)",
                itemwidth=30,
            ),
            margin=dict(l=16, r=16, t=60, b=80),
            paper_bgcolor=CARD_BG,
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Segoe UI, system-ui, sans-serif"),
            height=400,
        )
        return fig

    with col_v:
        vendor_df = df.groupby("client_name").agg({"vendor_cost": "sum"}).reset_index()
        fig_v = make_pie(vendor_df, "client_name", "vendor_cost",
                         "Vendor Distribution", "Vendor cost by client", PIE_COLORS)
        st.plotly_chart(fig_v, use_container_width=True)

    with col_c:
        fig_c = make_pie(client_df.head(10), "client_name", "client_billed_amount",
                         "Client Contribution", "Revenue share by client (top 10)", PIE_COLORS)
        st.plotly_chart(fig_c, use_container_width=True)

    # ================= TOP vs BOTTOM =================
    st.markdown('<div class="mm-section">Top vs Bottom Clients</div>', unsafe_allow_html=True)

    col_top, col_bot = st.columns(2)

    with col_top:
        fig_top = make_pie(
            client_df.head(5), "client_name", "gross_margin",
            "🏆 Top 5 Clients", "By gross margin",
            [PURPLE, PURPLE_LIGHT, "#A78BFA", "#DDD6FE", LAVENDER]
        )
        st.plotly_chart(fig_top, use_container_width=True)

    with col_bot:
        bottom = client_df.tail(5).copy()
        bottom["gross_margin"] = bottom["gross_margin"].abs()
        fig_bot = make_pie(
            bottom, "client_name", "gross_margin",
            "⚠️ Bottom 5 Clients", "By gross margin (lowest)",
            [RED, AMBER, "#FCA5A5", "#FCD34D", LAVENDER]
        )
        st.plotly_chart(fig_bot, use_container_width=True)

    # ================= QUARTERLY =================
    st.markdown('<div class="mm-section">Quarterly Performance (QoQ Growth)</div>', unsafe_allow_html=True)

    quarter_df = df.groupby(["financial_year", "quarter"]).agg({
        "gross_margin": "sum"
    }).reset_index()

    order = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
    quarter_df["q_order"] = quarter_df["quarter"].map(order)
    quarter_df = quarter_df.sort_values(["financial_year", "q_order"])
    quarter_df["prev_margin"] = quarter_df.groupby("financial_year")["gross_margin"].shift(1)
    quarter_df["growth_%"] = (
        (quarter_df["gross_margin"] - quarter_df["prev_margin"]) /
        quarter_df["prev_margin"] * 100
    ).round(2).fillna(0)

    # Render quarterly as styled cards per row
    years = quarter_df["financial_year"].unique()
    for yr in years:
        yr_df = quarter_df[quarter_df["financial_year"] == yr].reset_index(drop=True)
        st.markdown(f'<div style="font-size:12px; color:{TEXT_MUTED}; margin-bottom:8px; font-weight:600;">{yr}</div>', unsafe_allow_html=True)
        q_cols = st.columns(4)
        for i, row in yr_df.iterrows():
            growth = row["growth_%"]
            growth_html = (
                "Baseline" if growth == 0
                else f'↑ +{growth:.2f}%' if growth > 0
                else f'↓ {growth:.2f}%'
            )
            growth_cls = "" if growth >= 0 else "neg"
            q_cols[i % 4].markdown(f"""
                <div class="mm-quarter-card">
                    <div class="mm-q-label">{row['quarter']}</div>
                    <div class="mm-q-val">{format_inr_short(row['gross_margin'])}</div>
                    <div class="mm-q-growth {growth_cls}">{growth_html}</div>
                </div>
            """, unsafe_allow_html=True)

    # ================= CLIENT TABLE =================
    st.markdown('<div class="mm-section">Detailed Client-wise Performance</div>', unsafe_allow_html=True)

    client_df["margin_%"] = (
        client_df["gross_margin"] / client_df["client_billed_amount"] * 100
    ).round(2)

    def get_status(m):
        if m >= 30:   return "🟢 Healthy"
        elif m >= 15: return "🟡 Watch"
        else:         return "🔴 Risk"

    client_df["status"] = client_df["margin_%"].apply(get_status)

    display_df = client_df[[
        "client_name",
        "client_billed_amount",
        "vendor_cost",
        "gross_margin",
        "margin_%",
        "status"
    ]].copy()

    display_df.columns = ["Client", "Revenue", "Vendor Cost", "Gross Margin", "Margin %", "Status"]

    st.dataframe(
        display_df.style.format({
            "Revenue":      format_inr_short,
            "Vendor Cost":  format_inr_short,
            "Gross Margin": format_inr_short,
            "Margin %":     "{:.2f}%"
        }).set_properties(**{
            "background-color": CARD_BG,
            "color": TEXT_MAIN,
            "border-color": LAVENDER
        }).set_table_styles([
            {"selector": "th", "props": [
                ("background-color", BG),
                ("color", TEXT_MUTED),
                ("font-size", "11px"),
                ("text-transform", "uppercase"),
                ("letter-spacing", "0.5px"),
                ("font-weight", "700"),
                ("border-bottom", f"2px solid {LAVENDER}")
            ]},
            {"selector": "td", "props": [
                ("border-bottom", f"1px solid {LAVENDER}"),
                ("padding", "10px 14px")
            ]},
            {"selector": "tr:hover td", "props": [
                ("background-color", "#FAFAFE")
            ]}
        ]),
        use_container_width=True,
        hide_index=True
    )

    # ================= FOOTER =================
    st.markdown(f"""
        <div style="text-align:center; padding:28px 0 8px; font-size:11px; color:{TEXT_MUTED};">
            Protected by 256-bit encryption &nbsp;·&nbsp; © 2025 Evolve Brands Pvt Ltd
        </div>
    """, unsafe_allow_html=True)