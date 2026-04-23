import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
from datetime import date

DEFAULT_PORTFOLIO = [
    {"ticker": "VWCE.DE", "units": 10.0, "avg_price": 110.0, "currency": "EUR", "account": "IKE"},
    {"ticker": "SXR8.DE", "units": 5.0, "avg_price": 480.0, "currency": "EUR", "account": "IKE"},
]


@st.cache_data(ttl=900, show_spinner=False)
def get_current_prices(tickers: list) -> dict:
    """Fetch current prices for portfolio tickers."""
    prices = {}
    try:
        data = yf.download(tickers, period="2d", auto_adjust=True, progress=False)
        if len(tickers) == 1:
            close = data['Close']
            if hasattr(close, 'iloc'):
                prices[tickers[0]] = float(close.iloc[-1])
        else:
            for ticker in tickers:
                if ticker in data['Close'].columns:
                    prices[ticker] = float(data['Close'][ticker].dropna().iloc[-1])
    except Exception:
        pass
    return prices


def render():
    st.markdown('<div class="section-header">Mój portfel IKE / IKZE</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
    Wprowadź skład swojego portfela poniżej. Aplikacja pobierze aktualne ceny z Yahoo Finance 
    i pokaże bieżącą wycenę oraz zyski/straty na każdej pozycji.
    </div>
    """, unsafe_allow_html=True)

    # ---- PORTFOLIO INPUT ----
    st.markdown("#### Pozycje w portfelu")

    if 'portfolio_rows' not in st.session_state:
        st.session_state['portfolio_rows'] = DEFAULT_PORTFOLIO.copy()

    # Dynamic portfolio editor
    edited_portfolio = st.data_editor(
        pd.DataFrame(st.session_state['portfolio_rows']),
        column_config={
            "ticker": st.column_config.TextColumn("Ticker Yahoo Finance", help="Np. VWCE.DE, SXR8.DE, PKO.WA"),
            "units": st.column_config.NumberColumn("Ilość jednostek", min_value=0.0, format="%.4f"),
            "avg_price": st.column_config.NumberColumn("Śr. cena zakupu", min_value=0.0, format="%.2f"),
            "currency": st.column_config.SelectboxColumn("Waluta", options=["EUR", "PLN", "USD", "CHF"]),
            "account": st.column_config.SelectboxColumn("Konto", options=["IKE", "IKZE", "Zwykłe"]),
        },
        num_rows="dynamic",
        use_container_width=True,
        key="portfolio_editor"
    )

    # PLN/EUR rate input
    col_fx, col_btn = st.columns([2, 1])
    with col_fx:
        eur_pln = st.number_input("Kurs EUR/PLN", 3.5, 6.0, 4.28, 0.01,
                                  help="Aktualny kurs do przeliczenia wyceny na PLN")
        usd_pln = st.number_input("Kurs USD/PLN", 3.0, 6.0, 3.95, 0.01)

    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        refresh = st.button("🔄 Odśwież wycenę", type="primary", use_container_width=True)

    if edited_portfolio is None or len(edited_portfolio) == 0:
        st.warning("Dodaj pozycje do portfela korzystając z tabeli powyżej.")
        return

    portfolio_df = edited_portfolio.dropna(subset=['ticker'])
    tickers = portfolio_df['ticker'].tolist()

    if not tickers:
        return

    with st.spinner("Pobieranie aktualnych cen..."):
        current_prices = get_current_prices(tickers)

    # ---- VALUATION ----
    def to_pln(value, currency):
        if currency == "EUR":
            return value * eur_pln
        elif currency == "USD":
            return value * usd_pln
        return value

    rows_valued = []
    for _, row in portfolio_df.iterrows():
        ticker = row.get('ticker', '')
        units = float(row.get('units', 0))
        avg_price = float(row.get('avg_price', 0))
        currency = row.get('currency', 'EUR')
        account = row.get('account', 'IKE')

        current_price = current_prices.get(ticker, None)

        cost_basis = units * avg_price
        cost_pln = to_pln(cost_basis, currency)

        if current_price is not None:
            current_value = units * current_price
            current_pln = to_pln(current_value, currency)
            pnl = current_value - cost_basis
            pnl_pln = to_pln(pnl, currency)
            pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0
            price_str = f"{current_price:.2f} {currency}"
        else:
            current_pln = None
            pnl_pln = None
            pnl_pct = None
            price_str = "—"

        rows_valued.append({
            "Ticker": ticker,
            "Konto": account,
            "Jedn.": f"{units:.4f}",
            "Śr. cena": f"{avg_price:.2f} {currency}",
            "Aktualna cena": price_str,
            "Wartość (PLN)": f"{current_pln:,.0f}" if current_pln else "—",
            "Koszt (PLN)": f"{cost_pln:,.0f}",
            "P&L (PLN)": f"{pnl_pln:+,.0f}" if pnl_pln is not None else "—",
            "P&L %": f"{pnl_pct:+.1f}%" if pnl_pct is not None else "—",
            "_pnl_pct": pnl_pct,
            "_current_pln": current_pln or cost_pln,
            "_ticker": ticker,
            "_account": account
        })

    if not rows_valued:
        return

    display_df = pd.DataFrame(rows_valued)

    # ---- SUMMARY METRICS ----
    total_value = sum(r['_current_pln'] for r in rows_valued)
    total_cost = sum(to_pln(float(portfolio_df[portfolio_df['ticker'] == r['_ticker']]['units'].iloc[0]) *
                             float(portfolio_df[portfolio_df['ticker'] == r['_ticker']]['avg_price'].iloc[0]),
                             portfolio_df[portfolio_df['ticker'] == r['_ticker']]['currency'].iloc[0])
                     for r in rows_valued)

    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    ike_value = sum(r['_current_pln'] for r in rows_valued if r['_account'] == 'IKE')
    ikze_value = sum(r['_current_pln'] for r in rows_valued if r['_account'] == 'IKZE')

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Wartość portfela</div>
            <div class="metric-value">{total_value:,.0f} PLN</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        color_class = "metric-card-green" if total_pnl >= 0 else "metric-card"
        st.markdown(f"""
        <div class="{color_class}">
            <div class="metric-label">Łączny P&L</div>
            <div class="metric-value">{total_pnl:+,.0f} PLN</div>
            <div class="metric-delta">{total_pnl_pct:+.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">IKE</div>
            <div class="metric-value">{ike_value:,.0f} PLN</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">IKZE</div>
            <div class="metric-value">{ikze_value:,.0f} PLN</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- TABLE WITH CONDITIONAL FORMATTING ----
    show_cols = ["Ticker", "Konto", "Jedn.", "Śr. cena", "Aktualna cena",
                 "Wartość (PLN)", "Koszt (PLN)", "P&L (PLN)", "P&L %"]
    st.dataframe(display_df[show_cols], use_container_width=True, hide_index=True)

    # ---- ALLOCATION CHARTS ----
    st.markdown("<br>", unsafe_allow_html=True)
    col_pie1, col_pie2 = st.columns(2)

    with col_pie1:
        st.markdown("**Alokacja według instrumentu**")
        labels = [r['Ticker'] for r in rows_valued]
        values = [r['_current_pln'] for r in rows_valued]
        fig_pie = go.Figure(go.Pie(
            labels=labels, values=values, hole=0.5,
            marker_colors=['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'],
            textfont=dict(family='DM Mono', size=10)
        ))
        fig_pie.update_layout(
            height=280, margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor='rgba(0,0,0,0)', font=dict(family='DM Sans'),
            showlegend=True, legend=dict(font=dict(size=11))
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_pie2:
        st.markdown("**Alokacja według konta**")
        account_values = {}
        for r in rows_valued:
            account_values[r['_account']] = account_values.get(r['_account'], 0) + r['_current_pln']
        fig_acc = go.Figure(go.Pie(
            labels=list(account_values.keys()),
            values=list(account_values.values()),
            hole=0.5,
            marker_colors=['#10b981', '#3b82f6', '#6b7280'],
            textfont=dict(family='DM Mono', size=12)
        ))
        fig_acc.update_layout(
            height=280, margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor='rgba(0,0,0,0)', font=dict(family='DM Sans'),
            showlegend=True
        )
        st.plotly_chart(fig_acc, use_container_width=True)

    # ---- IKE/IKZE LIMIT TRACKER ----
    st.markdown('<div class="section-header" style="font-size:1.1rem; margin-top:1rem">Tracker limitów na 2026 rok</div>', unsafe_allow_html=True)

    IKE_LIMIT = 28_260
    IKZE_LIMIT = 10_281.60

    col_a, col_b = st.columns(2)
    with col_a:
        ike_used = st.number_input("Wpłacono na IKE w 2026 (PLN)", 0.0, float(IKE_LIMIT), 0.0, 100.0)
        ike_pct = ike_used / IKE_LIMIT * 100
        st.progress(min(ike_pct / 100, 1.0))
        st.caption(f"Wykorzystano: {ike_used:,.0f} / {IKE_LIMIT:,.0f} PLN ({ike_pct:.1f}%) | Pozostało: {IKE_LIMIT - ike_used:,.0f} PLN")

    with col_b:
        ikze_used = st.number_input("Wpłacono na IKZE w 2026 (PLN)", 0.0, float(IKZE_LIMIT), 0.0, 100.0)
        ikze_pct = ikze_used / IKZE_LIMIT * 100
        st.progress(min(ikze_pct / 100, 1.0))
        st.caption(f"Wykorzystano: {ikze_used:,.0f} / {IKZE_LIMIT:,.0f} PLN ({ikze_pct:.1f}%) | Pozostało: {IKZE_LIMIT - ikze_used:,.0f} PLN")

    st.caption("💾 Dane portfela nie są zapisywane między sesjami. Rozważ eksport do CSV lub integrację z arkuszem.")
