# 📈 IKE/IKZE Strategy Optimizer

Aplikacja Streamlit do planowania inwestycji emerytalnych w Polsce.

## Funkcje

- **Kalkulator IKE/IKZE** — porównanie korzyści podatkowych vs. zwykłe konto maklerskie
- **Backtesting ETF** — symulacja historyczna DCA na wybranych ETF-ach (Yahoo Finance)
- **Optymalizator portfela** — granica efektywna Markowitza, maksymalizacja Sharpe Ratio
- **Mój portfel** — śledzenie pozycji z wycenami na żywo

## Uruchomienie lokalne

```bash
# 1. Sklonuj repozytorium
git clone https://github.com/TWOJE_KONTO/ike-ikze-optimizer
cd ike-ikze-optimizer

# 2. Zainstaluj zależności
pip install -r requirements.txt

# 3. Uruchom aplikację
streamlit run app.py
```

## Deployment na Streamlit Cloud (za darmo)

1. Wgraj kod na GitHub (publiczne lub prywatne repo)
2. Wejdź na https://share.streamlit.io
3. Kliknij "New app" → wybierz repo → `app.py` jako główny plik
4. Deploy!

## Struktura projektu

```
ike-optimizer/
├── app.py                  # Główna aplikacja, sidebar, nawigacja
├── requirements.txt        # Zależności Python
├── tabs/
│   ├── __init__.py
│   ├── tax_calculator.py   # Tab 1: Kalkulator IKE/IKZE
│   ├── backtesting.py      # Tab 2: Backtesting historyczny
│   ├── optimizer.py        # Tab 3: Optymalizator Markowitz
│   └── portfolio.py        # Tab 4: Śledzenie portfela
└── README.md
```

## Źródła danych

- **Yahoo Finance** (via `yfinance`) — ceny ETF, akcji, indeksów
- Dane pobierane na żywo z cache'owaniem (TTL: 1h dla danych historycznych, 15 min dla bieżących cen)
- Limity IKE/IKZE zaktualizowane na rok 2026

## Roadmap (pomysły na rozbudowę)

- [ ] Integracja z obligacjami ROS/ROD (ręczne wprowadzanie stopy)
- [ ] Eksport raportu do PDF
- [ ] Symulacja Monte Carlo dla prognozy portfela
- [ ] Powiadomienia o limitach IKE/IKZE (email via SMTP)
- [ ] Porównanie brokerów (prowizje XTB vs. Bossa vs. mBank)
- [ ] Kalkulator FIRE (Financial Independence, Retire Early)

## Disclaimer

> Aplikacja ma charakter **wyłącznie edukacyjny i informacyjny**.  
> Nie stanowi doradztwa inwestycyjnego ani podatkowego w rozumieniu przepisów prawa.  
> Przed podjęciem decyzji inwestycyjnych skonsultuj się z doradcą finansowym.
