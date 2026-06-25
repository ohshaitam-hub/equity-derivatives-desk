"""Mesures de risque : VaR / CVaR, drawdown, contributions au risque."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .common import max_drawdown


def portfolio_returns(prices: pd.DataFrame, weights: pd.Series) -> pd.Series:
    tk = list(weights.index)
    rets = prices[tk].pct_change().dropna()
    return rets @ weights.values


def var_cvar(returns: pd.Series, conf: float = 0.95):
    """VaR & CVaR historiques (perte positive) au seuil conf."""
    q = np.quantile(returns, 1 - conf)
    var = -q
    cvar = -returns[returns <= q].mean() if (returns <= q).any() else var
    # VaR paramétrique (gaussienne)
    from scipy.stats import norm
    var_param = -(returns.mean() + norm.ppf(1 - conf) * returns.std(ddof=0))
    return float(var), float(cvar), float(var_param)


def risk_contributions(weights: pd.Series, cov: np.ndarray) -> pd.Series:
    w = weights.values
    port_var = w @ cov @ w
    if port_var <= 0:
        return pd.Series(0.0, index=weights.index)
    mrc = cov @ w                       # contribution marginale
    rc = w * mrc / np.sqrt(port_var)    # contribution absolue (en vol)
    rc = rc / rc.sum()                  # en %
    return pd.Series(rc, index=weights.index)


def summary(prices: pd.DataFrame, weights: pd.Series, cov: np.ndarray, conf=0.95) -> dict:
    r = portfolio_returns(prices, weights)
    equity = (1 + r).cumprod()
    var, cvar, var_p = var_cvar(r, conf)
    return {
        "vol_annualisee": float(r.std(ddof=0) * np.sqrt(252)),
        "rendement_annualise": float((1 + r.mean()) ** 252 - 1),
        f"VaR_{int(conf*100)}_1j": var,
        f"CVaR_{int(conf*100)}_1j": cvar,
        f"VaR_param_{int(conf*100)}": var_p,
        "max_drawdown": max_drawdown(equity),
        "returns": r, "equity": equity,
    }
