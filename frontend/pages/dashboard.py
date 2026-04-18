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


def show_dashboard(conn):

    st.set_page_config(layout="wide")

    # ================= UI =================
    st.markdown("""
        <style>
        .card {
            padding: 14px;
            border-radius: 10px;
            background: #FFFFFF;
            border: 1px solid #e6e6e6;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("📊 Management Dashboard")

    # ================= API CALL =================
    import requests

    token = st.session_state.get("token")

    headers = {
        "Authorization": f"Bearer {token}"
    }

    res = requests.get(
        f"{BASE_URL}/api/dashboard",
        headers=headers
    )

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
        if m in [4,5,6]: return "Q1"
        elif m in [7,8,9]: return "Q2"
        elif m in [10,11,12]: return "Q3"
        else: return "Q4"

    df["quarter"] = df["month"].apply(get_quarter)

    # ================= CALCULATIONS =================
    df["gross_margin"] = (
        df["client_billed_amount"] - df["vendor_cost"] - df["credit_note"]
    )

    # ================= FINANCIAL =================
    st.header("📊 Financial Overview")

    billed = df[df["expense_type_id"]!= 1]
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

    def render(title, values):
        st.subheader(title)
        cols = st.columns(4)
        labels = ["Revenue", "Vendor", "Margin", "Margin %"]

        for i in range(4):
            val = values[i]
            text = format_inr_short(val) if i != 3 else f"{val:.2f}%"
            cols[i].markdown(
                f"<div class='card'><b>{labels[i]}</b><br>{text}</div>",
                unsafe_allow_html=True
            )

    render("A. Billed", [b_amt, b_ven, b_mar, b_pct])
    render("B. Projected", [p_amt, p_ven, p_mar, p_pct])
    render("C. Total", [t_amt, t_ven, t_mar, t_pct])

    st.divider()

    # ================= FUNNEL =================
    st.subheader("📊 Revenue Funnel")

    st.plotly_chart(px.funnel(
        pd.DataFrame({"Stage":["Billed","Projected"],"Amount":[b_amt,p_amt]}),
        x="Amount", y="Stage"
    ), use_container_width=True)

    # ================= CLIENT =================
    client_df = df.groupby("client_name").agg({
        "client_billed_amount":"sum",
        "vendor_cost":"sum",
        "gross_margin":"sum"
    }).reset_index()

    client_df["efficiency"] = (
        client_df["gross_margin"] / client_df["client_billed_amount"] * 100
    ).round(2)

    client_df = client_df.sort_values("gross_margin", ascending=False)

    # ================= CLIENT PERFORMANCE =================
    st.subheader("📊 Client Performance")

    fig = go.Figure()
    fig.add_bar(x=client_df["client_name"], y=client_df["client_billed_amount"], name="Billing")
    fig.add_bar(x=client_df["client_name"], y=client_df["vendor_cost"], name="Expense")
    fig.add_scatter(x=client_df["client_name"], y=client_df["gross_margin"],
                    mode="lines+markers", name="Margin", yaxis="y2")

    fig.update_layout(barmode="group", yaxis2=dict(overlaying="y", side="right"))
    st.plotly_chart(fig, use_container_width=True)

    # ================= SMART =================
    st.subheader("🧠 Smart Recommendations")

    avg_eff = client_df["efficiency"].mean()
    top_clients = client_df[client_df["efficiency"] >= avg_eff].head(3)["client_name"].tolist()
    low_clients = client_df.sort_values("efficiency").head(3)["client_name"].tolist()

    st.markdown(f"""
    - 🚀 Scale: **{", ".join(top_clients)}**
    - ⚠️ Improve: **{", ".join(low_clients)}**
    - 📊 Avg Efficiency: **{avg_eff:.2f}%**
    """)

    # ================= VENDOR =================
    st.subheader("💰 Vendor Distribution")

    vendor_df = df.groupby("client_name").agg({
        "vendor_cost": "sum"
    }).reset_index()

    st.plotly_chart(px.pie(vendor_df, names="client_name", values="vendor_cost", hole=0.4),
                    use_container_width=True)

    # ================= CONTRIBUTION =================
    st.subheader("📊 Client Contribution")

    st.plotly_chart(px.pie(client_df.head(10),
                           names="client_name",
                           values="client_billed_amount",
                           hole=0.4),
                    use_container_width=True)

    # ================= RANKING =================
    st.subheader("🏆 Profitability Ranking")

    st.plotly_chart(px.bar(client_df.head(10),
                           x="gross_margin",
                           y="client_name",
                           orientation="h"),
                    use_container_width=True)

    # ================= TOP/BOTTOM =================
    st.subheader("🏆 Top vs Bottom Clients")

    col1, col2 = st.columns(2)

    col1.plotly_chart(px.pie(client_df.head(5),
                            names="client_name",
                            values="gross_margin",
                            hole=0.4),
                      use_container_width=True)

    bottom = client_df.tail(5).copy()
    bottom["gross_margin"] = bottom["gross_margin"].abs()

    col2.plotly_chart(px.pie(bottom,
                            names="client_name",
                            values="gross_margin",
                            hole=0.4),
                      use_container_width=True)

    # ================= QUARTER =================
    st.subheader("📅 Quarterly Performance (QoQ Growth)")

    quarter_df = df.groupby(["financial_year", "quarter"]).agg({
        "gross_margin": "sum"
    }).reset_index()

    order = {"Q1":1,"Q2":2,"Q3":3,"Q4":4}
    quarter_df["q_order"] = quarter_df["quarter"].map(order)

    quarter_df = quarter_df.sort_values(["financial_year", "q_order"])

    quarter_df["prev_margin"] = quarter_df.groupby("financial_year")["gross_margin"].shift(1)

    quarter_df["growth_%"] = (
        (quarter_df["gross_margin"] - quarter_df["prev_margin"]) /
        quarter_df["prev_margin"] * 100
    ).round(2)

    final_quarter_df = quarter_df[[
        "financial_year",
        "quarter",
        "gross_margin",
        "growth_%"
    ]].copy()

    final_quarter_df["growth_%"] = final_quarter_df["growth_%"].fillna(0)

    st.dataframe(
        final_quarter_df.style.format({
            "gross_margin": format_inr_short,
            "growth_%": "{:.2f}%"
        }),
        use_container_width=True
    )

    # ================= CLIENT TABLE =================
    st.subheader("📋 Detailed Client-wise Performance")

    client_df["margin_%"] = (
        client_df["gross_margin"] / client_df["client_billed_amount"] * 100
    ).round(2)

    def get_status(m):
        if m >= 30:
            return "🟢 Healthy"
        elif m >= 15:
            return "🟡 Watch"
        else:
            return "🔴 Risk"

    client_df["status"] = client_df["margin_%"].apply(get_status)

    display_df = client_df[[
        "client_name",
        "client_billed_amount",
        "vendor_cost",
        "gross_margin",
        "margin_%",
        "status"
    ]]

    st.dataframe(
        display_df.style.format({
            "client_billed_amount": format_inr_short,
            "vendor_cost": format_inr_short,
            "gross_margin": format_inr_short,
            "margin_%": "{:.2f}%"
        }),
        use_container_width=True
    )