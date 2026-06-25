"""Screener factoriel : value / momentum / quality -> score composite & ranking."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .common import zscore


def compute_factors(prices: pd.DataFrame, fundamentals: pd.DataFrame) -> pd.DataFrame:
    """Retourne un DataFrame par ticker avec les z-scores factoriels et le score."""
    f = fundamentals.copy()
    tk = [t for t in f.index if t in prices.columns]
    f = f.loc[tk]

    # VALUE : earnings yield (1/PE) + book yield (1/PB)
    value = zscore(1.0 / f["pe"]) + zscore(1.0 / f["pb"])

    # MOMENTUM : rendement 12 mois en sautant le dernier mois (252-21)
    mom_raw = {}
    for t in tk:
        s = prices[t].dropna()
        if len(s) > 252:
            mom_raw[t] = s.iloc[-21] / s.iloc[-252] - 1
        else:
            mom_raw[t] = s.iloc[-1] / s.iloc[0] - 1
    momentum = zscore(pd.Series(mom_raw))

    # QUALITY : ROE élevé, faible endettement
    quality = zscore(f["roe"]) - zscore(f["dette_capitaux"])

    out = pd.DataFrame({
        "secteur": f["secteur"],
        "value_z": value, "momentum_z": momentum, "quality_z": quality,
    })
    out["score"] = out[["value_z", "momentum_z", "quality_z"]].mean(axis=1)
    out = out.sort_values("score", ascending=False)
    out["rang"] = range(1, len(out) + 1)
    return out


def screen(factors: pd.DataFrame, top_n: int) -> list[str]:
    return list(factors.head(top_n).index)
