"""Optimisation de portefeuille — Markowitz (min variance, max Sharpe, frontière)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize


def mean_cov(prices: pd.DataFrame, tickers: list[str], lookback: int | None = None):
    """Rendements espérés (annualisés) et matrice de covariance (annualisée)."""
    px = prices[tickers].dropna()
    if lookback:
        px = px.iloc[-lookback:]
    rets = px.pct_change().dropna()
    mu = rets.mean().values * 252
    cov = rets.cov().values * 252
    return mu, cov, tickers


def _bounds(n, allow_short, max_w):
    lo = -max_w if allow_short else 0.0
    return tuple((lo, max_w) for _ in range(n))


def _port_stats(w, mu, cov, rf):
    ret = float(w @ mu)
    vol = float(np.sqrt(w @ cov @ w))
    sharpe = (ret - rf) / vol if vol > 0 else 0.0
    return ret, vol, sharpe


def min_variance(mu, cov, allow_short=False, max_w=1.0):
    n = len(mu)
    cons = ({"type": "eq", "fun": lambda w: w.sum() - 1},)
    res = minimize(lambda w: w @ cov @ w, np.repeat(1 / n, n), method="SLSQP",
                   bounds=_bounds(n, allow_short, max_w), constraints=cons)
    return res.x


def max_sharpe(mu, cov, rf=0.03, allow_short=False, max_w=1.0):
    n = len(mu)
    cons = ({"type": "eq", "fun": lambda w: w.sum() - 1},)

    def neg_sharpe(w):
        vol = np.sqrt(w @ cov @ w)
        return -((w @ mu - rf) / vol) if vol > 0 else 1e6

    res = minimize(neg_sharpe, np.repeat(1 / n, n), method="SLSQP",
                   bounds=_bounds(n, allow_short, max_w), constraints=cons)
    return res.x


def efficient_frontier(mu, cov, n_points=30, allow_short=False, max_w=1.0):
    n = len(mu)
    lo, hi = float(mu.min()), float(mu.max())
    targets = np.linspace(lo, hi, n_points)
    rows = []
    for t in targets:
        cons = ({"type": "eq", "fun": lambda w: w.sum() - 1},
                {"type": "eq", "fun": lambda w, t=t: w @ mu - t})
        res = minimize(lambda w: w @ cov @ w, np.repeat(1 / n, n), method="SLSQP",
                       bounds=_bounds(n, allow_short, max_w), constraints=cons)
        if res.success:
            vol = float(np.sqrt(res.x @ cov @ res.x))
            rows.append({"rendement": t, "volatilite": vol})
    return pd.DataFrame(rows)


def weights_table(w, tickers, mu, cov, rf):
    ret, vol, sharpe = _port_stats(w, mu, cov, rf)
    tab = pd.DataFrame({"poids": w}, index=tickers)
    tab = tab[tab["poids"].abs() > 1e-4].sort_values("poids", ascending=False)
    return tab, {"rendement": ret, "volatilite": vol, "sharpe": sharpe}
