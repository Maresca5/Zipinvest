import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
from scipy.optimize import minimize

OPTIMIZER_INSTRUMENTS = {
    "VWCE.DE": "VWCE — All-World",
    "SXR8.DE": "SXR8 — S&P 500",
    "EIMI.AS": "EIMI — Emerging Markets",
    "AGGH.AS": "AGGH — Global Bonds",
    "IS04.DE": "IS04 — EUR Govt Bonds",
    "IBGM.AS": "IBGM — Corp Bonds EUR",
}


@st.cache_data(ttl=7200, show_spinner=False)
def fetch_returns(tickers: list, years_back: int = 5) -> pd.DataFrame:
    from datetime import date, timedelta
    end = date.today().strftime("%Y-%m-%d")
    start = (date.today() - timedelta(days=365 * years_back)).strftime("%Y-%m-%d")
    try:
        raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
        if len(tickers) == 1:
            prices = raw[['Close']].rename(columns={'Close': tickers[0]})
        else:
            prices = raw['Close']
        returns = prices.pct_change().dropna()
        return returns
    except Exception:
        return pd.DataFrame()


def portfolio_performance(weights: np.ndarray, mean_returns: np.ndarray, cov_matrix: np.ndarray, rf: float = 0.04):
    ret = np.dot(weights, mean_returns) * 252
    vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix * 252, weights)))
    sharpe = (ret - rf) / vol if vol > 0 else 0
    return ret, vol, sharpe


def neg_sharpe(weights, mean_returns, cov_matrix, rf):
    _, _, sharpe = portfolio_performance(weights, mean_returns, cov_matrix, rf)
    return -sharpe


def min_variance(weights, mean_returns, cov_matrix, rf):
    _, vol, _ = portfolio_performance(weights, mean_returns, cov_matrix, rf)
    return vol


def optimize_portfolio(returns: pd.DataFrame, rf: float = 0.04, objective: str = "sharpe") -> dict:
    mean_returns = returns.mean()
    cov_matrix = returns.cov()
    n = len(returns.columns)
    constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
    bounds = tuple((0.0, 1.0) for _ in range(n))
    x0 = np.array([1 / n] * n)

    obj_fn = neg_sharpe if objective == "sharpe" else min_variance

    result = minimize(
        obj_fn, x0,
        args=(mean_returns, cov_matrix, rf),
        method='SLSQP',
        bounds=bounds,
        constraints=constraints,
        options={'maxiter': 1000}
    )

    if result.success:
        weights = result.x
        ret, vol, sharpe = portfolio_performance(weights, mean_returns, cov_matrix, rf)
        return {
            "weights": weights,
            "return": ret,
            "volatility": vol,
            "sharpe": sharpe,
            "tickers": list(returns.columns)
        }
    return {}


def generate_efficient_frontier(returns: pd.DataFrame, n_portfolios: int = 1000, rf: float = 0.04) -> pd.DataFrame:
    mean_returns = returns.mean()
    cov_matrix = returns.cov()
    n = len(returns.columns)

    results = []
    for _ in range(n_portfolios):
        w = np.random.dirichlet(np.ones(n))
        ret, vol, sharpe = portfolio_performance(w, mean_returns, cov_matrix, rf)
        results.append({"return": ret * 100, "volatility": vol * 100, "sharpe": sharpe, "weights": w.tolist()})

    return pd.DataFrame(results)


def render():
    st.markdown('<div class="section-header">Optymalizator portfela — Markowitz / Sharpe</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        selected = st.multiselect(
            "Wybierz aktywa do optymalizacji",
            options=[f"{t} — {n}" for t, n in OPTIMIZER_INSTRUMENTS.items()],
            default=["VWCE.DE — VWCE — All-World", "SXR8.DE — SXR8 — S&P 500",
                     "AGGH.AS — AGGH — Global Bonds", "IS04.DE — IS04 — EUR Govt Bonds"],
            help="Wybierz min. 2 instrumenty (max. 6)"
        )
        tickers = [s.split(" — ")[0] for s in selected]

    with col2:
        years_back = st.selectbox("Dane historyczne (lata)", [3, 5, 7, 10], index=1)
        rf_pct = st.slider("Stopa wolna od ryzyka (%)", 0.0, 8.0, 4.0, 0.5,
                           help="Np. rentowność polskich obligacji skarbowych")
        rf = rf_pct / 100
        objective = st.radio("Cel optymalizacji", ["Maksymalny Sharpe", "Minimalna wariancja"])

    if len(tickers) < 2:
        st.warning("Wybierz co najmniej 2 instrumenty.")
        return

    with st.spinner("Pobieranie danych i optymalizacja portfela..."):
        returns = fetch_returns(tickers, years_back)

    available_tickers = [t for t in tickers if t in returns.columns]
    if len(available_tickers) < 2:
        st.error("Niewystarczające dane historyczne dla wybranych instrumentów.")
        return

    returns = returns[available_tickers].dropna()

    obj_key = "sharpe" if "Sharpe" in objective else "variance"

    with st.spinner("Optymalizacja..."):
        frontier_df = generate_efficient_frontier(returns, n_portfolios=800, rf=rf)
        optimal = optimize_portfolio(returns, rf=rf, objective=obj_key)

    if not optimal:
        st.error("Optymalizacja nie powiodła się. Spróbuj innych instrumentów.")
        return

    # ---- EFFICIENT FRONTIER CHART ----
    fig = go.Figure()

    # Random portfolios
    fig.add_trace(go.Scatter(
        x=frontier_df["volatility"],
        y=frontier_df["return"],
        mode='markers',
        marker=dict(
            size=4,
            color=frontier_df["sharpe"],
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(title="Sharpe", thickness=12, len=0.8),
            opacity=0.6
        ),
        name="Portfele losowe",
        hovertemplate="Ryzyko: %{x:.1f}%<br>Zwrot: %{y:.1f}%<extra></extra>"
    ))

    # Optimal portfolio
    fig.add_trace(go.Scatter(
        x=[optimal["volatility"] * 100],
        y=[optimal["return"] * 100],
        mode='markers',
        marker=dict(size=18, color='#10b981', symbol='star', line=dict(color='white', width=2)),
        name=f"Portfel optymalny (Sharpe={optimal['sharpe']:.2f})",
        hovertemplate=f"<b>OPTYMALNY</b><br>Ryzyko: {optimal['volatility']*100:.1f}%<br>Zwrot: {optimal['return']*100:.1f}%<extra></extra>"
    ))

    # Equal weight reference
    ew_weights = np.array([1 / len(available_tickers)] * len(available_tickers))
    ew_ret, ew_vol, ew_sharpe = portfolio_performance(ew_weights, returns.mean(), returns.cov(), rf)
    fig.add_trace(go.Scatter(
        x=[ew_vol * 100], y=[ew_ret * 100],
        mode='markers',
        marker=dict(size=14, color='#3b82f6', symbol='diamond', line=dict(color='white', width=2)),
        name=f"Equal Weight (Sharpe={ew_sharpe:.2f})",
        hovertemplate=f"<b>EQUAL WEIGHT</b><br>Ryzyko: {ew_vol*100:.1f}%<br>Zwrot: {ew_ret*100:.1f}%<extra></extra>"
    ))

    fig.update_layout(
        title="Granica efektywna (Efficient Frontier)",
        xaxis_title="Roczne ryzyko (volatility, %)",
        yaxis_title="Oczekiwany zwrot roczny (%)",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='DM Sans', color='#374151'),
        xaxis=dict(gridcolor='#f3f4f6', ticksuffix="%"),
        yaxis=dict(gridcolor='#f3f4f6', ticksuffix="%"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=480,
        margin=dict(l=0, r=0, t=60, b=0)
    )

    st.plotly_chart(fig, use_container_width=True)

    # ---- OPTIMAL WEIGHTS ----
    st.markdown('<div class="section-header" style="font-size:1.1rem">Optymalne wagi portfela</div>', unsafe_allow_html=True)

    col_weights, col_metrics = st.columns([1, 1])

    with col_weights:
        weight_data = {
            OPTIMIZER_INSTRUMENTS.get(t, t): f"{w*100:.1f}%"
            for t, w in zip(optimal["tickers"], optimal["weights"])
            if w > 0.001
        }
        weight_df = pd.DataFrame.from_dict(weight_data, orient='index', columns=['Waga'])
        st.dataframe(weight_df, use_container_width=True)

        # Pie chart
        labels = list(weight_data.keys())
        values = [float(v.strip('%')) for v in weight_data.values()]
        fig_pie = go.Figure(go.Pie(
            labels=labels, values=values,
            hole=0.5,
            marker_colors=['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'],
            textfont=dict(family='DM Mono', size=11)
        ))
        fig_pie.update_layout(
            showlegend=True,
            height=300,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='DM Sans')
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_metrics:
        monthly = st.session_state.get('monthly_contribution', 1000)
        horizon = st.session_state.get('investment_horizon', 20)
        projected_value = monthly * 12 * horizon * (1 + optimal["return"]) ** (horizon / 2)

        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Oczekiwany zwrot roczny</div>
            <div class="metric-value">{optimal['return']*100:.1f}%</div>
        </div>
        <br>
        <div class="metric-card">
            <div class="metric-label">Roczna volatility</div>
            <div class="metric-value">{optimal['volatility']*100:.1f}%</div>
        </div>
        <br>
        <div class="metric-card-green">
            <div class="metric-label">Sharpe Ratio</div>
            <div class="metric-value">{optimal['sharpe']:.2f}</div>
            <div class="metric-delta">Powyżej 1.0 = dobry, 2.0+ = doskonały</div>
        </div>
        """, unsafe_allow_html=True)

    # ---- CORRELATION MATRIX ----
    with st.expander("🔗 Macierz korelacji aktywów"):
        corr = returns.rename(columns=OPTIMIZER_INSTRUMENTS).corr()
        fig_corr = go.Figure(go.Heatmap(
            z=corr.values,
            x=corr.columns.tolist(),
            y=corr.index.tolist(),
            colorscale='RdYlGn',
            zmin=-1, zmax=1,
            text=np.round(corr.values, 2),
            texttemplate="%{text}",
            textfont=dict(family='DM Mono', size=11)
        ))
        fig_corr.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='DM Sans')
        )
        st.plotly_chart(fig_corr, use_container_width=True)
        st.caption("Niższe korelacje = lepsza dywersyfikacja portfela. Wartości bliskie 0 lub ujemne = idealne połączenie.")

    st.markdown("""
    <div class="warning-box">
    ⚠️ Optymalizacja Markowitza opiera się na danych historycznych. Przyszłe zwroty i korelacje mogą być inne. 
    Model klasyczny nie uwzględnia fat tails, reżimów rynkowych ani kosztów transakcyjnych.
    </div>
    """, unsafe_allow_html=True)
