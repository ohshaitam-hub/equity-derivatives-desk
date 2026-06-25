"""Backtest intégré : screen -> optimise -> rebalance, vs équipondéré & indice."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .common import annualize_return, annualize_vol, max_drawdown
from .factors import compute_factors, screen
from . import optimizer as opt


def _period_key(date, freq: str):
    """Clé de période pour détecter un rebalancement (robuste, sans alias déprécié)."""
    f = (freq or "Q").upper()
    if f.startswith("M"):
        return (date.year, date.month)
    if f.startswith("A") or f.startswith("Y"):
        return (date.year,)
    return (date.year, date.quarter)            # trimestriel par défaut


def run_backtest(prices: pd.DataFrame, fundamentals: pd.DataFrame, cfg: dict):
    bt = cfg["backtest"]
    top_n = bt["top_n"]; look = bt["lookback_days"]; freq = bt["rebalance_freq"]

    daily_rets = prices.pct_change().fillna(0.0)
    strat = pd.Series(0.0, index=prices.index)
    ew = pd.Series(0.0, index=prices.index)
    weights_strat = None
    weights_ew = None
    prev_key = None

    idx = prices.index
    for i, date in enumerate(idx):
        key = _period_key(date, freq)
        # rebalancement au 1er jour de chaque nouvelle période
        if key != prev_key:
            prev_key = key
            hist = prices.loc[:date]
            if len(hist) > look // 2:
                fac = compute_factors(hist, fundamentals)
                sel = screen(fac, top_n)
                try:
                    mu, cov, tk = opt.mean_cov(hist, sel, lookback=look)
                    w = opt.max_sharpe(mu, cov, rf=cfg["optimizer"]["rf_annual"],
                                       allow_short=False, max_w=cfg["optimizer"]["max_weight"])
                    weights_strat = pd.Series(w, index=tk)
                except Exception:
                    weights_strat = pd.Series(1 / len(sel), index=sel)
                weights_ew = pd.Series(1 / len(sel), index=sel)
        # rendement du jour
        if weights_strat is not None and i > 0:
            day = daily_rets.loc[date]
            strat.loc[date] = float((day[weights_strat.index] * weights_strat.values).sum())
            ew.loc[date] = float((day[weights_ew.index] * weights_ew.values).sum())

    index_ret = daily_rets.mean(axis=1)        # indice = équipondéré tout l'univers
    eq_strat = (1 + strat).cumprod()
    eq_ew = (1 + ew).cumprod()
    eq_idx = (1 + index_ret).cumprod()

    curves = pd.DataFrame({"Stratégie (screen+optim)": eq_strat,
                           "Top-N équipondéré": eq_ew,
                           "Indice (univers)": eq_idx})
    metrics = {}
    for name, r in [("Stratégie (screen+optim)", strat),
                    ("Top-N équipondéré", ew), ("Indice (univers)", index_ret)]:
        eq = (1 + r).cumprod()
        vol = annualize_vol(r)
        metrics[name] = {
            "CAGR": annualize_return(r),
            "Vol": vol,
            "Sharpe": (annualize_return(r) - cfg["optimizer"]["rf_annual"]) / vol if vol else 0,
            "Max DD": max_drawdown(eq),
        }
    return curves, pd.DataFrame(metrics).T
