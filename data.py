"""Données de marché : génération synthétique réaliste + loader yfinance optionnel.

Mode SYNTHÉTIQUE (par défaut) : prix générés par un modèle à facteurs
(marché + secteur + idiosyncratique), avec un alpha caché lié aux
fondamentaux value/quality -> les facteurs ont un vrai pouvoir prédictif,
ce qui donne du sens au screener et au backtest.

Mode RÉEL : si `yfinance` est installé et le réseau disponible, on peut
tirer de vraies données (prix + fondamentaux). Repli automatique sur le
synthétique en cas d'échec.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# (ticker, secteur, bêta de marché)
UNIVERSE = [
    ("AAPL", "Technologie", 1.20), ("MSFT", "Technologie", 1.10),
    ("GOOGL", "Technologie", 1.15), ("AMZN", "Conso. cyclique", 1.30),
    ("META", "Technologie", 1.35), ("NVDA", "Technologie", 1.55),
    ("JPM", "Finance", 1.10), ("BAC", "Finance", 1.20), ("GS", "Finance", 1.25),
    ("XOM", "Énergie", 0.85), ("CVX", "Énergie", 0.80),
    ("JNJ", "Santé", 0.65), ("PFE", "Santé", 0.70), ("UNH", "Santé", 0.85),
    ("PG", "Conso. défensive", 0.55), ("KO", "Conso. défensive", 0.55),
    ("WMT", "Conso. défensive", 0.50), ("HD", "Conso. cyclique", 1.05),
    ("MCD", "Conso. cyclique", 0.70), ("NKE", "Conso. cyclique", 1.00),
    ("BA", "Industrie", 1.40), ("CAT", "Industrie", 1.15),
    ("NEE", "Services publics", 0.60), ("DUK", "Services publics", 0.50),
]


def tickers() -> list[str]:
    return [t for t, _, _ in UNIVERSE]


def generate_fundamentals(cfg: dict) -> pd.DataFrame:
    rng = np.random.default_rng(cfg["seed"])
    rows = []
    for tk, sector, beta in UNIVERSE:
        pe = rng.uniform(9, 42)
        pb = rng.uniform(1.2, 12)
        roe = rng.uniform(0.04, 0.38)
        de = rng.uniform(0.1, 2.4)
        divy = rng.uniform(0.0, 0.045)
        mktcap = rng.uniform(60, 2600)  # milliards USD
        rows.append({"ticker": tk, "secteur": sector, "beta": beta,
                     "pe": round(pe, 1), "pb": round(pb, 2), "roe": round(roe, 3),
                     "dette_capitaux": round(de, 2), "div_yield": round(divy, 4),
                     "mktcap_md": round(mktcap, 0)})
    f = pd.DataFrame(rows).set_index("ticker")
    # alpha caché (drift quotidien) : value + quality -> surperformance
    v = _z(1 / f["pe"]) + _z(1 / f["pb"])
    q = _z(f["roe"]) - _z(f["dette_capitaux"])
    f["_alpha"] = 0.00018 * (v + q)
    return f


def generate_prices(cfg: dict, fundamentals: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(cfg["seed"] + 1)
    n = cfg["universe"]["n_days"]
    dates = pd.bdate_range(cfg["universe"]["start_date"], periods=n)
    sectors = sorted(set(s for _, s, _ in UNIVERSE))
    mkt = rng.normal(0.0004, 0.011, n)                       # facteur marché
    sec_f = {s: rng.normal(0.0, 0.006, n) for s in sectors}  # facteurs secteur

    data = {}
    for tk, sector, beta in UNIVERSE:
        alpha = float(fundamentals.loc[tk, "_alpha"])
        idio = rng.normal(alpha, 0.013, n)
        r = beta * mkt + 0.6 * sec_f[sector] + idio
        p0 = rng.uniform(40, 300)
        data[tk] = p0 * np.exp(np.cumsum(r))
    return pd.DataFrame(data, index=dates)


def try_yfinance(cfg: dict):
    """Tente un chargement réel via yfinance. Retourne (prices, fundamentals) ou None."""
    try:
        import yfinance as yf
    except Exception:
        return None
    try:
        tk = tickers()
        px = yf.download(tk, period="6y", interval="1d", progress=False,
                         auto_adjust=True)["Close"].dropna(how="all")
        if px is None or px.empty:
            return None
        px = px.ffill().dropna(how="any", axis=1)
        # fondamentaux réels (best effort) ; sinon on garde les synthétiques
        fund = generate_fundamentals(cfg).reindex(px.columns)
        return px, fund
    except Exception:
        return None


def get_data(cfg: dict, source: str = "synthetique"):
    """source ∈ {'synthetique', 'reel'}. Repli auto sur synthétique."""
    if source == "reel":
        res = try_yfinance(cfg)
        if res is not None:
            return res[0], res[1], "reel"
    fund = generate_fundamentals(cfg)
    px = generate_prices(cfg, fund)
    return px, fund, "synthetique"


def _z(s):
    sd = s.std(ddof=0)
    return (s - s.mean()) / sd if sd else s * 0.0
