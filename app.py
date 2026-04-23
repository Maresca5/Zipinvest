import streamlit as st

st.set_page_config(
    page_title="IKE/IKZE Optimizer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.main-header {
    font-family: 'DM Serif Display', serif;
    font-size: 2.8rem;
    color: #1a1a2e;
    letter-spacing: -0.02em;
    line-height: 1.1;
}

.main-subtitle {
    font-family: 'DM Mono', monospace;
    font-size: 0.85rem;
    color: #6b7280;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-top: -0.5rem;
}

.metric-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border-radius: 16px;
    padding: 1.5rem;
    color: white;
    border: 1px solid rgba(255,255,255,0.08);
}

.metric-card-green {
    background: linear-gradient(135deg, #065f46 0%, #047857 100%);
    border-radius: 16px;
    padding: 1.5rem;
    color: white;
    border: 1px solid rgba(255,255,255,0.1);
}

.metric-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    opacity: 0.7;
    margin-bottom: 0.3rem;
}

.metric-value {
    font-family: 'DM Serif Display', serif;
    font-size: 2rem;
    line-height: 1.1;
}

.metric-delta {
    font-size: 0.8rem;
    opacity: 0.8;
    margin-top: 0.2rem;
}

.section-header {
    font-family: 'DM Serif Display', serif;
    font-size: 1.4rem;
    color: #1a1a2e;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #e5e7eb;
}

.info-box {
    background: #f0fdf4;
    border-left: 4px solid #10b981;
    border-radius: 0 8px 8px 0;
    padding: 1rem 1.2rem;
    margin: 1rem 0;
}

.warning-box {
    background: #fffbeb;
    border-left: 4px solid #f59e0b;
    border-radius: 0 8px 8px 0;
    padding: 1rem 1.2rem;
    margin: 1rem 0;
    font-size: 0.85rem;
    color: #78350f;
}

.tab-content {
    padding-top: 1.5rem;
}

[data-testid="stSidebar"] {
    background: #1a1a2e;
}

[data-testid="stSidebar"] * {
    color: #e5e7eb !important;
}

[data-testid="stSidebar"] .stSlider label {
    color: #9ca3af !important;
    font-size: 0.8rem;
    font-family: 'DM Mono', monospace;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.sidebar-logo {
    font-family: 'DM Serif Display', serif;
    font-size: 1.5rem;
    color: #10b981 !important;
    margin-bottom: 0.2rem;
}

.sidebar-tagline {
    font-size: 0.72rem;
    color: #6b7280 !important;
    font-family: 'DM Mono', monospace;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: 2rem;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
    background: transparent;
}

.stTabs [data-baseweb="tab"] {
    font-family: 'DM Mono', monospace;
    font-size: 0.78rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    border-radius: 8px;
    padding: 0.5rem 1rem;
}

.stTabs [aria-selected="true"] {
    background: #1a1a2e !important;
    color: #10b981 !important;
}
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown('<div class="sidebar-logo">IKE·IKZE</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-tagline">Strategy Optimizer</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**PARAMETRY PORTFELA**")

    st.session_state['investment_horizon'] = st.slider(
        "Horyzont inwestycji (lata)", 5, 40, 20
    )

    st.session_state['monthly_contribution'] = st.number_input(
        "Miesięczna wpłata (PLN)", 200, 10000, 1000, 100
    )

    st.session_state['initial_capital'] = st.number_input(
        "Kapitał startowy (PLN)", 0, 500000, 0, 1000
    )

    st.markdown("---")
    st.markdown("**TYP KONTA**")

    st.session_state['account_type'] = st.selectbox(
        "Wybierz konto",
        ["IKE", "IKZE", "IKE + IKZE", "Zwykłe konto"]
    )

    if st.session_state['account_type'] in ["IKZE", "IKE + IKZE"]:
        st.session_state['tax_bracket'] = st.selectbox(
            "Próg podatkowy",
            ["12% (do 120 000 PLN)", "32% (powyżej 120 000 PLN)"]
        )
    else:
        st.session_state['tax_bracket'] = "12% (do 120 000 PLN)"

    st.markdown("---")
    st.markdown("**LIMITY 2026**")
    st.markdown('<span style="font-size:0.75rem; font-family: DM Mono; color:#9ca3af">IKE: 28 260 PLN/rok</span>', unsafe_allow_html=True)
    st.markdown('<span style="font-size:0.75rem; font-family: DM Mono; color:#9ca3af">IKZE: 10 281,60 PLN/rok</span>', unsafe_allow_html=True)
    st.markdown('<span style="font-size:0.75rem; font-family: DM Mono; color:#9ca3af">IKZE samo. dz.: 15 422,40 PLN/rok</span>', unsafe_allow_html=True)

    st.markdown("---")
    st.caption("⚠️ Aplikacja ma charakter edukacyjny. Nie stanowi doradztwa inwestycyjnego.")

# Main content
st.markdown('<div class="main-header">IKE / IKZE<br><i>Strategy Optimizer</i></div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">Planowanie emerytalne · Backtesting · Optymalizacja portfela</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📊  Kalkulator IKE/IKZE",
    "📈  Backtesting ETF",
    "⚖️  Optymalizator portfela",
    "🗂️  Mój portfel"
])

with tab1:
    from tabs.tax_calculator import render
    render()

with tab2:
    from tabs.backtesting import render
    render()

with tab3:
    from tabs.optimizer import render
    render()

with tab4:
    from tabs.portfolio import render
    render()
