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


# ================= THEME =================
BG          = "#FFFFFF"
CARD_BG     = "#FFFFFF"
BORDER      = "#EEEBF5"
TEXT_MAIN   = "#1C1340"
TEXT_SUB    = "#6B63A0"
TEXT_MUTED  = "#A09CC0"
PURPLE      = "#6D28D9"
PURPLE_MID  = "#8B5CF6"
PURPLE_SOFT = "#EDE9FE"
GREEN_BG    = "#ECFDF5"; GREEN_TXT = "#065F46"
AMBER_BG    = "#FFFBEB"; AMBER_TXT = "#92400E"
RED_BG      = "#FEF2F2"; RED_TXT   = "#991B1B"

# Soft, distinct chart palette
CHART_COLORS = [
    "#818CF8",  # soft indigo
    "#34D399",  # soft emerald
    "#60A5FA",  # soft blue
    "#FBBF24",  # soft amber
    "#F472B6",  # soft pink
    "#2DD4BF",  # soft teal
    "#FB923C",  # soft orange
    "#A78BFA",  # soft violet
    "#4ADE80",  # soft green
    "#F87171",  # soft red
    "#38BDF8",  # soft sky
    "#E879F9",  # soft fuchsia
]


def chart_title_html(title, subtitle=""):
    sub = (
        f"<br><span style='font-size:11px;font-weight:400;color:{TEXT_MUTED}'>{subtitle}</span>"
        if subtitle else ""
    )
    return f"<b style='font-size:13px;color:{TEXT_MAIN}'>{title}</b>{sub}"


def make_pie(df_pie, names_col, values_col, title, subtitle, colors):
    fig = px.pie(
        df_pie, names=names_col, values=values_col,
        hole=0.58, color_discrete_sequence=colors
    )
    fig.update_traces(
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>%{percent:.1%}<extra></extra>",
        marker=dict(line=dict(color=CARD_BG, width=2))
    )
    fig.update_layout(
        title=dict(
            text=chart_title_html(title, subtitle),
            x=0, xanchor="left",
            font=dict(size=13, color=TEXT_MAIN),
            pad=dict(l=4, t=4)
        ),
        legend=dict(
            orientation="h",
            x=0.5, y=-0.12,
            xanchor="center", yanchor="top",
            font=dict(size=10, color=TEXT_SUB),
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=20, r=20, t=64, b=70),
        paper_bgcolor=CARD_BG,
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, system-ui, sans-serif"),
        height=400,
    )
    return fig


def show_dashboard(conn):

    st.set_page_config(layout="wide", page_title="Margin Monitor", page_icon="💎")

    # ================= CSS =================
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        .stApp {{
            background-color: {BG} !important;
            font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
        }}
        #MainMenu, footer {{ visibility: hidden; }}
        header {{ visibility: hidden; }}
        /* Show sidebar collapse/expand button */
        [data-testid="collapsedControl"],
        button[kind="header"],
        .st-emotion-cache-dvne4q,
        section[data-testid="stSidebar"] > div > button {{
            visibility: visible !important;
            display: flex !important;
            opacity: 1 !important;
        }}
        .block-container {{
            padding: 2rem 3rem !important;
            max-width: 1440px !important;
        }}

        /* ── Top bar ── */
        .mm-topbar {{
            display: flex; align-items: center; justify-content: space-between;
            padding-bottom: 20px; margin-bottom: 28px;
            border-bottom: 1px solid {BORDER};
        }}
        .mm-logo-row {{ display: flex; align-items: center; gap: 14px; }}
        .mm-gem {{
            width: 40px; height: 40px;
            background: linear-gradient(135deg, {PURPLE_MID}, #C084FC);
            border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            font-size: 20px;
            box-shadow: 0 4px 12px rgba(109,40,217,0.18);
        }}
        .mm-brand-name  {{ font-size: 18px; font-weight: 700; color: {TEXT_MAIN}; letter-spacing: -0.3px; }}
        .mm-brand-sub   {{ font-size: 12px; color: {TEXT_MUTED}; margin-top: 1px; font-weight: 400; }}
        .mm-badges      {{ display: flex; gap: 8px; align-items: center; }}
        .mm-badge {{
            display: inline-flex; align-items: center; gap: 6px;
            background: {CARD_BG}; border: 1px solid {BORDER};
            border-radius: 6px; padding: 5px 12px;
            font-size: 12px; color: {TEXT_SUB}; font-weight: 500;
        }}
        .mm-badge-dot {{ width: 6px; height: 6px; border-radius: 50%; background: #34D399; display: inline-block; }}

        /* ── Section header ── */
        .mm-section-hdr {{
            display: flex; align-items: center; gap: 12px;
            margin: 32px 0 14px 0;
        }}
        .mm-section-hdr-title {{ font-size: 13px; font-weight: 600; color: {TEXT_MAIN}; white-space: nowrap; }}
        .mm-section-hdr-line  {{ flex: 1; height: 1px; background: {BORDER}; }}

        /* ── KPI cards ── */
        .mm-kpi {{
            background: {CARD_BG}; border: 1px solid {BORDER};
            border-radius: 10px; padding: 20px 20px 18px 24px;
            position: relative; overflow: hidden;
        }}
        .mm-kpi:hover {{ box-shadow: 0 4px 16px rgba(109,40,217,0.07); }}
        .mm-kpi-bar {{
            position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
            border-radius: 10px 0 0 10px; background: {PURPLE_MID};
        }}
        .mm-kpi-bar.green  {{ background: #34D399; }}
        .mm-kpi-bar.amber  {{ background: #FBBF24; }}
        .mm-kpi-bar.muted  {{ background: {BORDER}; }}
        .mm-kpi-label {{ font-size: 11px; font-weight: 600; text-transform: uppercase;
                         letter-spacing: 0.7px; color: {TEXT_MUTED}; margin-bottom: 8px; }}
        .mm-kpi-value {{ font-size: 23px; font-weight: 700; color: {TEXT_MAIN};
                         line-height: 1; letter-spacing: -0.4px; }}
        .mm-kpi-tag {{
            display: inline-flex; align-items: center; gap: 4px;
            margin-top: 10px; font-size: 11px; font-weight: 500;
            padding: 2px 8px; border-radius: 4px;
        }}
        .mm-kpi-tag.up   {{ background: {GREEN_BG}; color: {GREEN_TXT}; }}
        .mm-kpi-tag.down {{ background: {RED_BG};   color: {RED_TXT}; }}
        .mm-kpi-tag.flat {{ background: {PURPLE_SOFT}; color: {PURPLE_MID}; }}

        /* ── Chart card ── */
        .mm-chart-card {{
            background: {CARD_BG};
            border: 1px solid {BORDER};
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 1px 6px rgba(109,40,217,0.07);
        }}

        /* Plotly charts that aren't wrapped in mm-chart-card */
        div[data-testid="stPlotlyChart"] > div {{
            border: 1px solid {BORDER} !important;
            border-radius: 10px !important;
            box-shadow: 0 1px 6px rgba(109,40,217,0.07) !important;
            overflow: hidden !important;
        }}
        /* Remove scrollbars from all plotly iframes and containers */
        div[data-testid="stPlotlyChart"] {{
            overflow: hidden !important;
        }}
        div[data-testid="stPlotlyChart"] iframe {{
            display: block !important;
            overflow: hidden !important;
        }}
        .js-plotly-plot, .plot-container {{
            overflow: hidden !important;
        }}

        /* ── Insight card ── */
        .mm-insight {{
            background: {CARD_BG}; border: 1px solid {BORDER};
            border-radius: 10px; padding: 22px;
        }}
        .mm-insight-title {{ font-size: 13px; font-weight: 600; color: {TEXT_MAIN}; margin-bottom: 16px; }}
        .mm-insight-row {{
            display: flex; align-items: flex-start; gap: 12px;
            padding: 12px 0; border-bottom: 1px solid {BORDER};
        }}
        .mm-insight-row:last-child {{ border-bottom: none; padding-bottom: 0; }}
        .mm-insight-row:first-of-type {{ padding-top: 0; }}
        .mm-insight-icon {{
            width: 30px; height: 30px; border-radius: 7px; flex-shrink: 0;
            display: flex; align-items: center; justify-content: center; font-size: 14px;
        }}
        .mm-insight-icon.green  {{ background: {GREEN_BG}; }}
        .mm-insight-icon.amber  {{ background: {AMBER_BG}; }}
        .mm-insight-icon.purple {{ background: {PURPLE_SOFT}; }}
        .mm-insight-lbl  {{ font-size: 12px; font-weight: 600; color: {TEXT_MAIN}; margin-bottom: 3px; }}
        .mm-insight-body {{ font-size: 11px; color: {TEXT_SUB}; line-height: 1.5; }}

        /* ── Quarter cards ── */
        .mm-q {{
            background: {CARD_BG}; border: 1px solid {BORDER};
            border-radius: 10px; padding: 18px; text-align: center;
        }}
        .mm-q-qtr   {{ font-size: 11px; font-weight: 700; color: {TEXT_MUTED};
                       text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 8px; }}
        .mm-q-val   {{ font-size: 20px; font-weight: 700; color: {TEXT_MAIN}; letter-spacing: -0.3px; }}
        .mm-q-badge {{
            display: inline-flex; align-items: center; gap: 3px;
            margin-top: 8px; padding: 2px 8px; border-radius: 4px;
            font-size: 11px; font-weight: 600;
        }}
        .mm-q-badge.up   {{ background: {GREEN_BG}; color: {GREEN_TXT}; }}
        .mm-q-badge.down {{ background: {RED_BG};   color: {RED_TXT}; }}
        .mm-q-badge.base {{ background: {PURPLE_SOFT}; color: {PURPLE_MID}; }}

        /* ── Dataframe ── */
        div[data-testid="stDataFrame"] > div {{
            border: 1px solid {BORDER} !important;
            border-radius: 10px !important;
        }}

        h1, h2, h3 {{ color: {TEXT_MAIN} !important; }}
        [data-testid="column"] {{ padding: 0 5px !important; }}
        </style>
    """, unsafe_allow_html=True)

    # ================= TOP BAR =================
    st.markdown(f"""
        <div class="mm-topbar">
            <div class="mm-logo-row">
                <div class="mm-gem">💎</div>
                <div>
                    <div class="mm-brand-name">Margin Monitor</div>
                    <div class="mm-brand-sub">Billing &amp; Finance Platform &nbsp;·&nbsp; Management Dashboard</div>
                </div>
            </div>
            <div class="mm-badges">
                <span class="mm-badge"><span class="mm-badge-dot"></span> Live</span>
                <span class="mm-badge">📅 FY 2026–27</span>
                <span class="mm-badge">🔒 JWT Secured</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # ================= API =================
    import requests

    token = st.session_state.get("token")
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/api/dashboard", headers=headers)

    if res.status_code != 200:
        st.error("Failed to fetch dashboard data.")
        return

    df = pd.DataFrame(res.json())
    if df.empty:
        st.warning("No data available.")
        return

    # ================= DATE & CALC =================
    df["invoice_month_parsed"] = pd.to_datetime(df["invoice_month"], format="%b-%y", errors="coerce")
    df["month"] = df["invoice_month_parsed"].dt.month

    def get_quarter(m):
        if m in [4, 5, 6]:    return "Q1"
        elif m in [7, 8, 9]:  return "Q2"
        elif m in [10,11,12]: return "Q3"
        else:                  return "Q4"

    df["quarter"]      = df["month"].apply(get_quarter)
    df["gross_margin"] = df["client_billed_amount"] - df["vendor_cost"] - df["credit_note"]

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

    # ================= KPI HELPER =================
    def section(title):
        st.markdown(f"""
            <div class="mm-section-hdr">
                <span class="mm-section-hdr-title">{title}</span>
                <span class="mm-section-hdr-line"></span>
            </div>
        """, unsafe_allow_html=True)

    def kpi_row(sec_title, rows):
        section(sec_title)
        cols = st.columns(4, gap="small")
        for i, (label, val, is_pct, bar_cls, tag_txt, tag_cls) in enumerate(rows):
            val_str  = f"{val:.2f}%" if is_pct else format_inr_short(val)
            tag_html = f'<div class="mm-kpi-tag {tag_cls}">{tag_txt}</div>' if tag_txt else ""
            cols[i].markdown(f"""
                <div class="mm-kpi">
                    <div class="mm-kpi-bar {bar_cls}"></div>
                    <div class="mm-kpi-label">{label}</div>
                    <div class="mm-kpi-value">{val_str}</div>
                    {tag_html}
                </div>
            """, unsafe_allow_html=True)

    # ── A · Billed ──
    kpi_row("A · Billed", [
        ("Revenue",      b_amt, False, "",       "↑ vs last year",     "up"),
        ("Vendor Cost",  b_ven, False, "green",  "↓ vs last year",     "down"),
        ("Gross Margin", b_mar, False, "",       "↑ vs last year",     "up"),
        ("Margin %",     b_pct, True,  "amber",  "↑ pts vs last year", "up"),
    ])

    # ── B · Projected ──
    kpi_row("B · Projected", [
        ("Revenue",      p_amt, False, "muted", "Estimated", "flat"),
        ("Vendor Cost",  p_ven, False, "muted", "Estimated", "flat"),
        ("Gross Margin", p_mar, False, "muted", "Estimated", "flat"),
        ("Margin %",     p_pct, True,  "muted", "Estimated", "flat"),
    ])

    # ── C · Total ──
    kpi_row("C · Total", [
        ("Revenue",      t_amt, False, "",       "Combined", "flat"),
        ("Vendor Cost",  t_ven, False, "green",  "Combined", "flat"),
        ("Gross Margin", t_mar, False, "",       "Combined", "flat"),
        ("Margin %",     t_pct, True,  "amber",  "Blended",  "flat"),
    ])

    # ================= CLIENT AGG =================
    client_df = df.groupby("client_name").agg({
        "client_billed_amount": "sum",
        "vendor_cost": "sum",
        "gross_margin": "sum"
    }).reset_index()
    client_df["efficiency"] = (
        client_df["gross_margin"] / client_df["client_billed_amount"] * 100
    ).round(2)
    client_df = client_df.sort_values("gross_margin", ascending=False).reset_index(drop=True)

    # ================= ROW 1: Client Performance + Funnel =================
    section("Client Performance &amp; Revenue Split")
    col_left, col_right = st.columns([1.7, 1], gap="small")

    with col_left:
        top10 = client_df.head(10).copy()
        top10["margin_%"] = (top10["gross_margin"] / top10["client_billed_amount"] * 100).round(1)
        # Shorten long names for cleaner x-axis
        top10["label"] = top10["client_name"].str.replace(
            r"\b(Limited|Pvt Ltd|Ltd|Private|Industries|Solutions|Systems|India)\b",
            "", regex=True
        ).str.strip().str.rstrip(".")

        fig_c = go.Figure()

        # Stacked: Vendor Cost (bottom) + Gross Margin (top) = Total Billing
        fig_c.add_bar(
            x=top10["label"],
            y=top10["vendor_cost"],
            name="Vendor Cost",
            marker=dict(color="#818CF8", line=dict(width=0)),
            hovertemplate="<b>%{x}</b><br>Vendor Cost: ₹%{y:,.0f}<extra></extra>",
        )
        fig_c.add_bar(
            x=top10["label"],
            y=top10["gross_margin"],
            name="Gross Margin",
            marker=dict(color="#34D399", line=dict(width=0)),
            hovertemplate="<b>%{x}</b><br>Gross Margin: ₹%{y:,.0f}<extra></extra>",
        )

        # Margin % as a dot scatter on secondary y-axis
        fig_c.add_scatter(
            x=top10["label"],
            y=top10["margin_%"],
            name="Margin %",
            mode="markers+text",
            marker=dict(color="#FBBF24", size=9, symbol="circle",
                        line=dict(color="#fff", width=1.5)),
            text=top10["margin_%"].apply(lambda v: f"{v:.0f}%"),
            textposition="top center",
            textfont=dict(size=9, color="#92400E"),
            yaxis="y2",
            hovertemplate="<b>%{x}</b><br>Margin %%: %{y:.1f}%%<extra></extra>",
        )

        fig_c.update_layout(
            barmode="stack",
            title=dict(
                text="<b style='font-size:13px;color:{main}'>Top 10 Clients</b>"
                     "<br><span style='font-size:10px;color:{muted}'>Vendor Cost · Gross Margin · Margin %</span>"
                     .format(main=TEXT_MAIN, muted=TEXT_MUTED),
                x=0, xanchor="left", pad=dict(l=16, t=12)
            ),
            xaxis=dict(
                tickfont=dict(size=10, color=TEXT_MUTED),
                gridcolor="rgba(0,0,0,0)",
                tickangle=-30,
                automargin=True,
            ),
            yaxis=dict(
                gridcolor="#EEE9FB",
                tickfont=dict(size=10, color=TEXT_MUTED),
                tickformat=",.2s",
                title=dict(text="Revenue (₹)", font=dict(size=10, color=TEXT_MUTED)),
                zeroline=False,
            ),
            yaxis2=dict(
                overlaying="y", side="right",
                range=[0, top10["margin_%"].max() * 1.6],
                tickfont=dict(size=10, color="#92400E"),
                tickformat=".0f",
                ticksuffix="%",
                title=dict(text="Margin %", font=dict(size=10, color="#92400E")),
                showgrid=False,
                zeroline=False,
            ),
            legend=dict(
                orientation="h",
                y=1.12, x=0.5,
                xanchor="center", yanchor="top",
                bgcolor="rgba(0,0,0,0)",
                font=dict(size=11, color=TEXT_SUB),
            ),
            paper_bgcolor=CARD_BG,
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, Segoe UI, sans-serif"),
            margin=dict(l=12, r=50, t=72, b=60),
            height=460,
            bargap=0.35,
        )
        st.markdown('<div class="mm-chart-card">', unsafe_allow_html=True)
        st.plotly_chart(fig_c, use_container_width=True, config={"displayModeBar": False, "scrollZoom": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        # Build funnel with value annotations inside; handle near-zero slices
        funnel_df = pd.DataFrame({
            "Stage":  ["Billed", "Projected"],
            "Amount": [b_amt,    p_amt],
            "Color":  ["#818CF8", "#34D399"]
        })
        # Only show textinfo on slices that are meaningfully large (> 1%)
        total_rev = b_amt + p_amt
        b_pct_share = (b_amt / total_rev * 100) if total_rev else 0

        fig_f = go.Figure(go.Pie(
            labels=funnel_df["Stage"],
            values=funnel_df["Amount"],
            hole=0.60,
            marker=dict(
                colors=["#818CF8", "#34D399"],
                line=dict(color=CARD_BG, width=3)
            ),
            textinfo="label+percent",
            textposition="outside",
            textfont=dict(size=12, color=TEXT_MAIN),
            hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}<br>%{percent:.1%}<extra></extra>",
            sort=False,
        ))
        fig_f.update_layout(
            title=dict(
                text="<b style='font-size:13px'>Revenue Split</b>",
                x=0, xanchor="left",
                pad=dict(l=16, t=14)
            ),
            annotations=[dict(
                text=f"<b>{format_inr_short(total_rev)}</b><br><span style='font-size:10px;color:{TEXT_MUTED}'>Total</span>",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=13, color=TEXT_MAIN),
                align="center"
            )],
            showlegend=True,
            legend=dict(
                orientation="h",
                x=0.5, y=-0.06,
                xanchor="center", yanchor="top",
                bgcolor="rgba(0,0,0,0)",
                font=dict(size=11, color=TEXT_SUB),
            ),
            paper_bgcolor=CARD_BG, plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, Segoe UI, sans-serif"),
            margin=dict(l=20, r=20, t=52, b=48),
            height=460,
        )
        st.markdown('<div class="mm-chart-card">', unsafe_allow_html=True)
        st.plotly_chart(fig_f, use_container_width=True, config={"displayModeBar": False, "scrollZoom": False})
        st.markdown('</div>', unsafe_allow_html=True)

    # ================= ROW 2: Ranking + Insights =================
    section("Profitability Ranking &amp; Insights")
    col_rank, col_ins = st.columns([1.7, 1], gap="small")

    with col_rank:
        top10r = client_df.head(10).reset_index(drop=True)
        fig_r = go.Figure()
        fig_r.add_bar(
            y=top10r["client_name"], x=top10r["gross_margin"],
            orientation="h",
            marker=dict(color=CHART_COLORS[:len(top10r)], line=dict(width=0)),
            hovertemplate="<b>%{y}</b><br>Margin: ₹%{x:,.0f}<extra></extra>"
        )
        fig_r.update_layout(
            title=dict(
                text=chart_title_html("Profitability Ranking", "Gross margin by client — top 10"),
                x=0, xanchor="left", pad=dict(l=4, t=4)
            ),
            yaxis=dict(
                autorange="reversed", automargin=True,
                tickfont=dict(size=11, color=TEXT_MUTED),
                gridcolor="rgba(0,0,0,0)"
            ),
            xaxis=dict(
                gridcolor="#EEE9FB", tickformat=",.0s", automargin=True,
                tickfont=dict(size=10, color=TEXT_MUTED)
            ),
            showlegend=False,
            paper_bgcolor=CARD_BG, plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, Segoe UI, sans-serif"),
            margin=dict(l=8, r=16, t=72, b=12),
            height=430, bargap=0.32,
        )
        st.markdown('<div class="mm-chart-card">', unsafe_allow_html=True)
        st.plotly_chart(fig_r, use_container_width=True, config={"displayModeBar": False, "scrollZoom": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with col_ins:
        avg_eff     = client_df["efficiency"].mean()
        top_clients = client_df[client_df["efficiency"] >= avg_eff].head(3)["client_name"].tolist()
        low_clients = client_df.sort_values("efficiency").head(3)["client_name"].tolist()
        st.markdown(f"""
            <div class="mm-insight">
                <div class="mm-insight-title">Smart Insights</div>
                <div class="mm-insight-row">
                    <div class="mm-insight-icon green">🚀</div>
                    <div>
                        <div class="mm-insight-lbl">Scale these clients</div>
                        <div class="mm-insight-body">{" &nbsp;·&nbsp; ".join(top_clients)}</div>
                    </div>
                </div>
                <div class="mm-insight-row">
                    <div class="mm-insight-icon amber">⚠️</div>
                    <div>
                        <div class="mm-insight-lbl">Review margins</div>
                        <div class="mm-insight-body">{" &nbsp;·&nbsp; ".join(low_clients)}</div>
                    </div>
                </div>
                <div class="mm-insight-row">
                    <div class="mm-insight-icon purple">📊</div>
                    <div>
                        <div class="mm-insight-lbl">Portfolio efficiency</div>
                        <div class="mm-insight-body">Avg <b>{avg_eff:.2f}%</b> across all active clients</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # ================= VENDOR & CONTRIBUTION =================
    section("Vendor Distribution &amp; Revenue Contribution")
    col_v, col_c2 = st.columns(2, gap="small")

    vendor_df = df.groupby("client_name").agg({"vendor_cost": "sum"}).reset_index()

    with col_v:
        fig_v = make_pie(vendor_df, "client_name", "vendor_cost",
                         "Vendor Distribution", "Vendor cost share by client", CHART_COLORS)
        st.markdown('<div class="mm-chart-card">', unsafe_allow_html=True)
        st.plotly_chart(fig_v, use_container_width=True, config={"displayModeBar": False, "scrollZoom": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with col_c2:
        fig_cc = make_pie(client_df.head(10), "client_name", "client_billed_amount",
                          "Client Contribution", "Revenue share — top 10 clients", CHART_COLORS)
        st.markdown('<div class="mm-chart-card">', unsafe_allow_html=True)
        st.plotly_chart(fig_cc, use_container_width=True, config={"displayModeBar": False, "scrollZoom": False})
        st.markdown('</div>', unsafe_allow_html=True)

    # ================= TOP vs BOTTOM =================
    section("Top vs Bottom Clients")
    col_top, col_bot = st.columns(2, gap="small")

    with col_top:
        fig_top = make_pie(
            client_df.head(5), "client_name", "gross_margin",
            "Top 5 Clients", "Highest gross margin contributors",
            ["#818CF8", "#34D399", "#60A5FA", "#FBBF24", "#2DD4BF"]
        )
        st.markdown('<div class="mm-chart-card">', unsafe_allow_html=True)
        st.plotly_chart(fig_top, use_container_width=True, config={"displayModeBar": False, "scrollZoom": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with col_bot:
        bottom = client_df.tail(5).copy()
        bottom["gross_margin"] = bottom["gross_margin"].abs()
        fig_bot = make_pie(
            bottom, "client_name", "gross_margin",
            "Bottom 5 Clients", "Lowest gross margin — needs attention",
            ["#F87171", "#FB923C", "#FBBF24", "#F472B6", "#A78BFA"]
        )
        st.markdown('<div class="mm-chart-card">', unsafe_allow_html=True)
        st.plotly_chart(fig_bot, use_container_width=True, config={"displayModeBar": False, "scrollZoom": False})
        st.markdown('</div>', unsafe_allow_html=True)

    # ================= QUARTERLY =================
    section("Quarterly Performance · QoQ Growth")

    quarter_df = df.groupby(["financial_year", "quarter"]).agg({"gross_margin": "sum"}).reset_index()
    order = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
    quarter_df["q_order"] = quarter_df["quarter"].map(order)
    quarter_df = quarter_df.sort_values(["financial_year", "q_order"])
    quarter_df["prev_margin"] = quarter_df.groupby("financial_year")["gross_margin"].shift(1)
    quarter_df["growth_%"] = (
        (quarter_df["gross_margin"] - quarter_df["prev_margin"]) /
        quarter_df["prev_margin"] * 100
    ).round(2).fillna(0)

    for yr in quarter_df["financial_year"].unique():
        yr_df = quarter_df[quarter_df["financial_year"] == yr].reset_index(drop=True)
        st.markdown(
            f'<div style="font-size:11px;color:{TEXT_MUTED};font-weight:600;'
            f'text-transform:uppercase;letter-spacing:0.6px;margin:8px 0 10px;">{yr}</div>',
            unsafe_allow_html=True
        )
        q_cols = st.columns(4, gap="small")
        for i, row in yr_df.iterrows():
            g = row["growth_%"]
            badge_cls = "base" if g == 0 else ("up" if g > 0 else "down")
            badge_txt = "Baseline" if g == 0 else (f"↑ +{g:.1f}%" if g > 0 else f"↓ {g:.1f}%")
            q_cols[i % 4].markdown(f"""
                <div class="mm-q">
                    <div class="mm-q-qtr">{row['quarter']}</div>
                    <div class="mm-q-val">{format_inr_short(row['gross_margin'])}</div>
                    <div><span class="mm-q-badge {badge_cls}">{badge_txt}</span></div>
                </div>
            """, unsafe_allow_html=True)

    # ================= CLIENT TABLE =================
    section("Detailed Client Performance")

    client_df["margin_%"] = (
        client_df["gross_margin"] / client_df["client_billed_amount"] * 100
    ).round(2)

    def get_status(m):
        if m >= 30:   return "🟢 Healthy"
        elif m >= 15: return "🟡 Watch"
        else:         return "🔴 Risk"

    client_df["status"] = client_df["margin_%"].apply(get_status)

    display_df = client_df[[
        "client_name", "client_billed_amount",
        "vendor_cost", "gross_margin", "margin_%", "status"
    ]].copy()
    display_df.columns = ["Client", "Revenue", "Vendor Cost", "Gross Margin", "Margin %", "Status"]

    st.dataframe(
        display_df.style.format({
            "Revenue":      format_inr_short,
            "Vendor Cost":  format_inr_short,
            "Gross Margin": format_inr_short,
            "Margin %":     "{:.2f}%",
        }).set_properties(**{
            "font-size": "13px",
            "background-color": CARD_BG,
            "color": TEXT_MAIN,
        }).set_table_styles([
            {"selector": "thead th", "props": [
                ("background-color", BG),
                ("color",            TEXT_MUTED),
                ("font-size",        "10px"),
                ("text-transform",   "uppercase"),
                ("letter-spacing",   "0.6px"),
                ("font-weight",      "700"),
                ("padding",          "11px 14px"),
                ("border-bottom",    f"1px solid {BORDER}"),
            ]},
            {"selector": "tbody td", "props": [
                ("padding",       "12px 14px"),
                ("border-bottom", f"1px solid {BORDER}"),
                ("font-size",     "13px"),
            ]},
            {"selector": "tbody tr:last-child td", "props": [
                ("border-bottom", "none"),
            ]},
            {"selector": "tbody tr:hover td", "props": [
                ("background-color", "#FAFAFE"),
            ]},
        ]),
        use_container_width=True,
        hide_index=True,
    )

    # ================= FOOTER =================
    st.markdown(f"""
        <div style="text-align:center; padding:32px 0 12px; font-size:11px;
                    color:{TEXT_MUTED}; border-top:1px solid {BORDER}; margin-top:32px;">
            Protected by 256-bit encryption &nbsp;·&nbsp; © 2025 Evolve Brands Pvt Ltd
        </div>
    """, unsafe_allow_html=True)