import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date
import yfinance as yf

# Curated instrument list for IKE/IKZE
INSTRUMENTS = {
    "ETF — Globalny rynek akcji": {
        "VWCE.DE": "Vanguard FTSE All-World (EUR, Xetra)",
        "WEBN.SW": "Invesco MSCI World ESN (CHF, SIX)",
        "IWDA.AS": "iShares Core MSCI World (EUR, Euronext)",
        "EIMI.AS": "iShares Core MSCI EM IMI (EUR, Euronext)",
    },
    "ETF — Rynek USA": {
        "CSPX.AS": "iShares Core S&P 500 (EUR, Euronext)",
        "SXR8.DE": "iShares Core S&P 500 (EUR, Xetra)",
        "VUAA.AS": "Vanguard S&P 500 (EUR, Euronext)",
    },
    "ETF — Obligacje": {
        "AGGH.AS": "iShares Core Global Agg Bond (EUR hedged)",
        "IS04.DE": "iShares € Govt Bond 7-10yr (EUR, Xetra)",
        "IBGM.AS": "iShares Core € Corp Bond (EUR)",
    },
    "Polskie aktywa": {
        "PKO.WA": "PKO BP (GPW)",
        "KGH.WA": "KGHM Polska Miedź (GPW)",
        "CDR.WA": "CD Projekt (GPW)",
        "LPP.WA": "LPP SA (GPW)",
    },
    "Benchmark / Indeksy": {
        "^GSPC": "S&P 500 Index",
        "^STOXX50E": "Euro Stoxx 50 Index",
    }
}

FLAT_INSTRUMENTS = {ticker: name for cat in INSTRUMENTS.values() for ticker, name in cat.items()}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_data(tickers: list, start: str, end: str) -> pd.DataFrame:
    """Fetch adjusted close prices from Yahoo Finance."""
    try:
        raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
        if len(tickers) == 1:
            prices = raw[['Close']].rename(columns={'Close': tickers[0]})
        else:
            prices = raw['Close']
        prices.dropna(how='all', inplace=True)
        return prices
    except Exception as e:
        return pd.DataFrame()


def simulate_dca(prices: pd.Series, monthly_amount: float, start_capital: float = 0) -> pd.Series:
    """Simulate Dollar-Cost Averaging (monthly purchases)."""
    portfolio_value = []
    units_held = start_capital / prices.iloc[0] if start_capital > 0 and prices.iloc[0] > 0 else 0
    month_tracker = None

    for i, (date_idx, price) in enumerate(prices.items()):
        # Buy on first trading day of each month
        current_month = (date_idx.year, date_idx.month)
        if current_month != month_tracker:
            units_held += monthly_amount / price
            month_tracker = current_month
        portfolio_value.append(units_held * price)

    return pd.Series(portfolio_value, index=prices.index)


def compute_metrics(values: pd.Series, monthly_amount: float, years: float, initial: float = 0) -> dict:
    """Compute performance metrics for a backtest."""
    total_invested = initial + monthly_amount * 12 * years
    final_value = values.iloc[-1]
    total_return = (final_value - total_invested) / total_invested * 100

    # CAGR
    n_years = (values.index[-1] - values.index[0]).days / 365.25
    cagr = ((final_value / values.iloc[0]) ** (1 / max(n_years, 0.1)) - 1) * 100 if values.iloc[0] > 0 else 0

    # Drawdown
    rolling_max = values.cummax()
    drawdown = (values - rolling_max) / rolling_max * 100
    max_drawdown = drawdown.min()

    # Volatility (annualized)
    daily_returns = values.pct_change().dropna()
    volatility = daily_returns.std() * np.sqrt(252) * 100

    # Sharpe (assuming 4% risk-free / Polish bonds)
    rf = 0.04
    sharpe = (cagr / 100 - rf) / (volatility / 100) if volatility > 0 else 0

    return {
        "final_value": final_value,
        "total_invested": total_invested,
        "total_return_pct": total_return,
        "profit": final_value - total_invested,
        "cagr": cagr,
        "max_drawdown": max_drawdown,
        "volatility": volatility,
        "sharpe": sharpe
    }


def render():
    st.markdown('<div class="section-header">Backtesting historyczny — DCA na ETF</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        # Instrument selection
        selected_labels = st.multiselect(
            "Wybierz instrumenty do porównania",
            options=[f"{ticker} — {name}" for ticker, name in FLAT_INSTRUMENTS.items()],
            default=["VWCE.DE — Vanguard FTSE All-World (EUR, Xetra)", "SXR8.DE — iShares Core S&P 500 (EUR, Xetra)"],
            max_selections=4,
            help="Możesz porównać max. 4 instrumenty jednocześnie"
        )
        selected_tickers = [s.split(" — ")[0] for s in selected_labels]

    with col2:
        start_year = st.selectbox("Rok startu backtesting", list(range(2005, 2024)), index=14)
        start_date = f"{start_year}-01-01"
        end_date = date.today().strftime("%Y-%m-%d")
        monthly_amount = st.session_state.get('monthly_contribution', 1000)
        initial = st.session_state.get('initial_capital', 0)
        st.info(f"Wpłata: {monthly_amount:,} PLN/mies.\nKapitał startowy: {initial:,} PLN")

    if not selected_tickers:
        st.warning("Wybierz co najmniej jeden instrument.")
        return

    with st.spinner("Pobieranie danych z Yahoo Finance..."):
        prices_df = fetch_data(selected_tickers, start_date, end_date)

    if prices_df.empty:
        st.error("Nie udało się pobrać danych. Sprawdź połączenie lub spróbuj innych tickerów.")
        return

    if len(selected_tickers) == 1:
        prices_df.columns = selected_tickers

    # Ensure columns match
    available = [t for t in selected_tickers if t in prices_df.columns]
    if not available:
        st.error("Brak danych dla wybranych instrumentów.")
        return

    years_actual = (prices_df.index[-1] - prices_df.index[0]).days / 365.25

    # ---- DCA SIMULATION ----
    colors = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444']
    portfolio_series = {}
    metrics_all = {}

    for ticker in available:
        series = prices_df[ticker].dropna()
        if len(series) < 30:
            continue
        dca = simulate_dca(series, monthly_amount, initial)
        portfolio_series[ticker] = dca
        metrics_all[ticker] = compute_metrics(dca, monthly_amount, years_actual, initial)

    # ---- CHARTS ----
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.65, 0.35],
        shared_xaxes=True,
        subplot_titles=("Wartość portfela DCA (PLN)", "Drawdown (%)"),
        vertical_spacing=0.08
    )

    for i, (ticker, dca) in enumerate(portfolio_series.items()):
        color = colors[i % len(colors)]
        label = FLAT_INSTRUMENTS.get(ticker, ticker)

        fig.add_trace(go.Scatter(
            x=dca.index, y=dca.values,
            name=ticker,
            line=dict(color=color, width=2),
            hovertemplate=f"<b>{ticker}</b><br>%{{x|%Y-%m}}<br>%{{y:,.0f}} PLN<extra></extra>"
        ), row=1, col=1)

        # Invested capital reference (only once)
        if i == 0:
            invested = pd.Series(
                [initial + monthly_amount * ((d.year - prices_df.index[0].year) * 12 + (d.month - prices_df.index[0].month))
                 for d in dca.index],
                index=dca.index
            )
            fig.add_trace(go.Scatter(
                x=invested.index, y=invested.values,
                name="Wpłacony kapitał",
                line=dict(color='#d1d5db', width=1, dash='dot'),
                hovertemplate="Wpłacono: %{y:,.0f} PLN<extra></extra>"
            ), row=1, col=1)

        # Drawdown
        rolling_max = dca.cummax()
        dd = (dca - rolling_max) / rolling_max * 100
        fig.add_trace(go.Scatter(
            x=dd.index, y=dd.values,
            name=f"DD {ticker}",
            line=dict(color=color, width=1),
            fill='tozeroy',
            fillcolor=f'rgba({int(color[1:3], 16)},{int(color[3:5], 16)},{int(color[5:7], 16)},0.15)',
            showlegend=False,
            hovertemplate=f"<b>{ticker}</b> DD: %{{y:.1f}}%<extra></extra>"
        ), row=2, col=1)

    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='DM Sans', color='#374151'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode='x unified',
        height=580,
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis2=dict(gridcolor='#f3f4f6'),
        yaxis=dict(gridcolor='#f3f4f6', tickformat=",.0f"),
        yaxis2=dict(gridcolor='#f3f4f6', ticksuffix="%"),
    )

    st.plotly_chart(fig, use_container_width=True)

    # ---- METRICS TABLE ----
    st.markdown('<div class="section-header" style="font-size:1.1rem">Podsumowanie wyników</div>', unsafe_allow_html=True)

    if metrics_all:
        rows = []
        for ticker, m in metrics_all.items():
            rows.append({
                "Instrument": ticker,
                "Wartość końcowa": f"{m['final_value']:,.0f} PLN",
                "Wpłacono łącznie": f"{m['total_invested']:,.0f} PLN",
                "Zysk": f"{m['profit']:,.0f} PLN",
                "Zwrot %": f"{m['total_return_pct']:+.1f}%",
                "CAGR": f"{m['cagr']:.1f}%",
                "Max DD": f"{m['max_drawdown']:.1f}%",
                "Volatility": f"{m['volatility']:.1f}%",
                "Sharpe": f"{m['sharpe']:.2f}"
            })
        df = pd.DataFrame(rows).set_index("Instrument")
        st.dataframe(df, use_container_width=True)

    st.markdown("""
    <div class="warning-box">
    ⚠️ <b>Ważne zastrzeżenie:</b> Wyniki historyczne nie gwarantują przyszłych stóp zwrotu. 
    Dane z Yahoo Finance mogą zawierać błędy lub luki, zwłaszcza dla ETF-ów notowanych w EUR na Xetra/Euronext 
    (dostępne dane często od 2018-2019). Symulacja nie uwzględnia spreadów, prowizji maklerskich 
    ani różnic kursowych PLN/EUR.
    </div>
    """, unsafe_allow_html=True)

    with st.expander("ℹ️ Jak działa symulacja DCA?"):
        st.markdown("""
        **Dollar-Cost Averaging (uśrednianie ceny zakupu)** — strategia polega na regularnym inwestowaniu 
        stałej kwoty niezależnie od aktualnej ceny instrumentu. W tej symulacji:
        
        - Każdego miesiąca (pierwsza sesja handlowa) kupujemy jednostki za zadaną kwotę
        - Cena zakupu to cena zamknięcia z Yahoo Finance (adjusted close — uwzględnia dywidendy i splity)
        - Portfel wyceniamy codziennie po aktualnej cenie rynkowej
        - Nie uwzględniamy: spreadów, prowizji, podatków w trakcie trwania IKE/IKZE
        """)
