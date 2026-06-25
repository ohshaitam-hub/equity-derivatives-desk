"""Utilitaires communs : config, chemins, helpers numériques."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_config(path=None) -> dict:
    p = Path(path) if path else ROOT / "config.yaml"
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def zscore(s: pd.Series) -> pd.Series:
    """Z-score robuste (évite division par zéro)."""
    mu, sd = s.mean(), s.std(ddof=0)
    if sd == 0 or np.isnan(sd):
        return pd.Series(0.0, index=s.index)
    return (s - mu) / sd


def annualize_return(daily: pd.Series) -> float:
    return float((1 + daily.mean()) ** 252 - 1)


def annualize_vol(daily: pd.Series) -> float:
    return float(daily.std(ddof=0) * np.sqrt(252))


def max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    return float((equity / peak - 1).min())
