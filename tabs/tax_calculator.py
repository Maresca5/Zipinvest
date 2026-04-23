import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np

# IKE/IKZE limits 2026
IKE_LIMIT_2026 = 28_260
IKZE_LIMIT_2026 = 10_281.60
IKZE_SELF_EMPLOYED_LIMIT_2026 = 15_422.40
BELKA_TAX = 0.19
IKZE_EXIT_TAX = 0.10  # 10% ryczałt przy wypłacie po 65 roku życia


def calculate_ike(monthly: float, years: int, annual_return: float, initial: float = 0) -> dict:
    """Simulate IKE account growth. No Belka tax on withdrawal."""
    months = years * 12
    balance = initial
    total_invested = initial
    monthly_return = annual_return / 12

    values = []
    for m in range(months):
        balance = balance * (1 + monthly_return) + monthly
        total_invested += monthly
        values.append(balance)

    gross_profit = balance - total_invested
    # No Belka tax!
    net_withdrawal = balance
    tax_saved_vs_regular = gross_profit * BELKA_TAX

    return {
        "balance": balance,
        "total_invested": total_invested,
        "gross_profit": gross_profit,
        "net_withdrawal": net_withdrawal,
        "tax_on_profit": 0,
        "tax_saved": tax_saved_vs_regular,
        "monthly_values": values,
        "label": "IKE"
    }


def calculate_ikze(monthly: float, years: int, annual_return: float, tax_bracket: float, initial: float = 0) -> dict:
    """
    Simulate IKZE account growth.
    - Contributions deductible from PIT (tax_bracket)
    - On withdrawal: 10% flat tax on entire amount (after 65)
    """
    months = years * 12
    balance = initial
    total_invested = initial
    monthly_return = annual_return / 12

    # Effective PIT savings each year (refund from tax return)
    annual_contribution = monthly * 12
    annual_pit_refund = min(annual_contribution, IKZE_LIMIT_2026) * tax_bracket
    total_pit_refunds = annual_pit_refund * years

    values = []
    for m in range(months):
        balance = balance * (1 + monthly_return) + monthly
        total_invested += monthly
        values.append(balance)

    gross_profit = balance - total_invested
    exit_tax = balance * IKZE_EXIT_TAX  # 10% of entire balance on exit
    net_withdrawal = balance - exit_tax + total_pit_refunds

    # vs regular: would pay Belka on profits, would NOT get PIT refund
    belka_on_regular = gross_profit * BELKA_TAX
    net_benefit = (belka_on_regular - exit_tax) + total_pit_refunds

    return {
        "balance": balance,
        "total_invested": total_invested,
        "gross_profit": gross_profit,
        "net_withdrawal": net_withdrawal,
        "exit_tax": exit_tax,
        "total_pit_refunds": total_pit_refunds,
        "tax_saved": net_benefit,
        "monthly_values": values,
        "label": "IKZE"
    }


def calculate_regular(monthly: float, years: int, annual_return: float, initial: float = 0) -> dict:
    """Simulate regular brokerage account with Belka tax."""
    months = years * 12
    balance = initial
    total_invested = initial
    monthly_return = annual_return / 12

    values = []
    for m in range(months):
        balance = balance * (1 + monthly_return) + monthly
        total_invested += monthly
        values.append(balance)

    gross_profit = balance - total_invested
    belka_tax = gross_profit * BELKA_TAX
    net_withdrawal = balance - belka_tax

    return {
        "balance": balance,
        "total_invested": total_invested,
        "gross_profit": gross_profit,
        "net_withdrawal": net_withdrawal,
        "belka_tax": belka_tax,
        "monthly_values": values,
        "label": "Zwykłe konto"
    }


def render():
    st.markdown('<div class="section-header">Kalkulator korzyści podatkowych IKE / IKZE</div>', unsafe_allow_html=True)

    # Get params from session state
    years = st.session_state.get('investment_horizon', 20)
    monthly = st.session_state.get('monthly_contribution', 1000)
    initial = st.session_state.get('initial_capital', 0)
    account_type = st.session_state.get('account_type', 'IKE')
    tax_str = st.session_state.get('tax_bracket', '12% (do 120 000 PLN)')
    tax_bracket = 0.32 if "32%" in tax_str else 0.12

    col_params, col_spacer = st.columns([3, 1])
    with col_params:
        annual_return = st.slider(
            "Zakładana roczna stopa zwrotu (%)",
            1.0, 15.0, 7.0, 0.5,
            help="Historyczna średnia MSCI World ~7-8% p.a. w USD. Przyjmij konserwatywnie 5-7% w PLN."
        ) / 100

    st.markdown("<br>", unsafe_allow_html=True)

    # Calculate all scenarios
    ike = calculate_ike(monthly, years, annual_return, initial)
    ikze = calculate_ikze(monthly, years, annual_return, tax_bracket, initial)
    regular = calculate_regular(monthly, years, annual_return, initial)

    # Limit warnings
    annual_contribution = monthly * 12
    if annual_contribution > IKE_LIMIT_2026:
        st.markdown(f"""
        <div class="warning-box">
        ⚠️ Twoja roczna wpłata ({annual_contribution:,.0f} PLN) przekracza limit IKE na 2026 rok 
        ({IKE_LIMIT_2026:,.0f} PLN). Nadwyżka nie będzie chroniona podatkowo.
        </div>
        """, unsafe_allow_html=True)

    # ---- METRIC CARDS ----
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">IKE — wartość końcowa</div>
            <div class="metric-value">{ike['net_withdrawal']:,.0f} PLN</div>
            <div class="metric-delta">✓ Brak podatku Belki</div>
            <div class="metric-delta" style="margin-top:0.8rem; color:#10b981; font-size:0.9rem">
                +{ike['tax_saved']:,.0f} PLN vs. zwykłe konto
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">IKZE — wartość końcowa (netto)</div>
            <div class="metric-value">{ikze['net_withdrawal']:,.0f} PLN</div>
            <div class="metric-delta">✓ Ulga PIT: {ikze['total_pit_refunds']:,.0f} PLN łącznie</div>
            <div class="metric-delta" style="margin-top:0.8rem; color:#10b981; font-size:0.9rem">
                +{ikze['tax_saved']:,.0f} PLN vs. zwykłe konto
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #374151 0%, #4b5563 100%)">
            <div class="metric-label">Zwykłe konto — wartość końcowa</div>
            <div class="metric-value">{regular['net_withdrawal']:,.0f} PLN</div>
            <div class="metric-delta">✗ Podatek Belki: {regular['belka_tax']:,.0f} PLN</div>
            <div class="metric-delta" style="margin-top:0.8rem; color:#ef4444; font-size:0.9rem">
                Benchmark (punkt odniesienia)
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- GROWTH CHART ----
    months_range = list(range(1, years * 12 + 1))
    years_axis = [m / 12 for m in months_range]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=years_axis, y=ike['monthly_values'],
        mode='lines', name='IKE',
        line=dict(color='#10b981', width=2.5),
        fill='tozeroy', fillcolor='rgba(16,185,129,0.06)'
    ))

    fig.add_trace(go.Scatter(
        x=years_axis, y=ikze['monthly_values'],
        mode='lines', name='IKZE (brutto)',
        line=dict(color='#3b82f6', width=2.5, dash='dot'),
    ))

    fig.add_trace(go.Scatter(
        x=years_axis, y=regular['monthly_values'],
        mode='lines', name='Zwykłe konto (brutto)',
        line=dict(color='#6b7280', width=1.5, dash='dash'),
    ))

    # Add invested capital line
    invested_values = [initial + monthly * m for m in months_range]
    fig.add_trace(go.Scatter(
        x=years_axis, y=invested_values,
        mode='lines', name='Wpłacony kapitał',
        line=dict(color='#d1d5db', width=1, dash='dot'),
    ))

    fig.update_layout(
        title=None,
        xaxis_title="Lata",
        yaxis_title="Wartość portfela (PLN)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='DM Sans', color='#374151'),
        xaxis=dict(gridcolor='#f3f4f6', ticksuffix=" lat"),
        yaxis=dict(gridcolor='#f3f4f6', tickformat=",.0f"),
        hovermode='x unified',
        height=420,
        margin=dict(l=0, r=0, t=20, b=0)
    )

    st.plotly_chart(fig, use_container_width=True)

    # ---- BREAKDOWN TABLE ----
    st.markdown('<div class="section-header" style="font-size:1.1rem">Szczegółowe zestawienie</div>', unsafe_allow_html=True)

    df = pd.DataFrame({
        "Parametr": [
            "Łączne wpłaty",
            "Wartość brutto (przed podatkiem)",
            "Zysk z inwestycji",
            "Podatek Belki (19%)",
            "Ulga PIT (IKZE)",
            "Podatek przy wypłacie z IKZE (10%)",
            "Wartość netto do ręki",
            "Korzyść vs. zwykłe konto"
        ],
        "IKE": [
            f"{ike['total_invested']:,.0f} PLN",
            f"{ike['balance']:,.0f} PLN",
            f"{ike['gross_profit']:,.0f} PLN",
            "0 PLN ✓",
            "—",
            "—",
            f"{ike['net_withdrawal']:,.0f} PLN",
            f"+{ike['tax_saved']:,.0f} PLN 🟢"
        ],
        "IKZE": [
            f"{ikze['total_invested']:,.0f} PLN",
            f"{ikze['balance']:,.0f} PLN",
            f"{ikze['gross_profit']:,.0f} PLN",
            "0 PLN ✓",
            f"+{ikze['total_pit_refunds']:,.0f} PLN ✓",
            f"-{ikze['exit_tax']:,.0f} PLN",
            f"{ikze['net_withdrawal']:,.0f} PLN",
            f"+{ikze['tax_saved']:,.0f} PLN 🟢"
        ],
        "Zwykłe konto": [
            f"{regular['total_invested']:,.0f} PLN",
            f"{regular['balance']:,.0f} PLN",
            f"{regular['gross_profit']:,.0f} PLN",
            f"-{regular['belka_tax']:,.0f} PLN ✗",
            "—",
            "—",
            f"{regular['net_withdrawal']:,.0f} PLN",
            "Punkt odniesienia"
        ]
    })

    st.dataframe(df.set_index("Parametr"), use_container_width=True)

    # ---- INFO BOXES ----
    st.markdown("""
    <div class="info-box">
    <b>💡 Jak działają limity IKE/IKZE?</b><br>
    Limity są ustalane co roku jako wielokrotność przeciętnego wynagrodzenia. W 2026: IKE = 3× prognozowane wynagrodzenie,
    IKZE = ~1,2× wynagrodzenie. Jeśli Twoja wpłata przekracza limit – nadwyżka ląduje na zwykłym koncie maklerskim 
    (możesz obsługiwać to w ramach jednego rachunku w wielu domach maklerskich).
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📋 Szczegóły podatkowe IKE vs IKZE"):
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("""
            **IKE (Indywidualne Konto Emerytalne)**
            - Wpłaty: z opodatkowanego dochodu (brak odliczenia)
            - Wzrost: bez podatku Belki przez cały okres
            - Wypłata po 60. roku życia (lub 55 przy wcześniejszej emeryturze): **0% podatku**
            - Wcześniejsza wypłata: 19% Belki od zysków
            - Limit 2026: **28 260 PLN/rok**
            """)
        with col_b:
            st.markdown("""
            **IKZE (Indywidualne Konto Zabezpieczenia Emerytalnego)**
            - Wpłaty: **odliczane od podstawy PIT** (zwrot 12% lub 32%)
            - Wzrost: bez podatku Belki przez cały okres
            - Wypłata po 65. roku życia: **10% ryczałt** od całej sumy
            - Wcześniejsza wypłata: doliczenie do dochodu roku bieżącego
            - Limit 2026: **10 281,60 PLN/rok** (15 422,40 dla samozatrudnionych)
            """)
