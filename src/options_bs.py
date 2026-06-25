"""Options : Black-Scholes, Grecques, surface de volatilité, stratégies de couverture.

L'indice « portefeuille » est normalisé à un spot (config: options.spot). On
construit une surface de vol implicite (skew actions + structure par terme),
on price les options par Black-Scholes et on calcule les Grecques, puis on
applique des couvertures (protective put, covered call, collar).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


def _d1_d2(S, K, T, r, sigma):
    T = max(T, 1e-6); sigma = max(sigma, 1e-6)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return d1, d2


def bs_price(S, K, T, r, sigma, typ="call"):
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    if typ == "call":
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def greeks(S, K, T, r, sigma, typ="call") -> dict:
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    pdf = norm.pdf(d1)
    delta = norm.cdf(d1) if typ == "call" else norm.cdf(d1) - 1
    gamma = pdf / (S * sigma * np.sqrt(T))
    vega = S * pdf * np.sqrt(T) / 100                       # par 1 pt de vol
    if typ == "call":
        theta = (-S * pdf * sigma / (2 * np.sqrt(T))
                 - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
        rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100
    else:
        theta = (-S * pdf * sigma / (2 * np.sqrt(T))
                 + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365
        rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100
    return {"delta": delta, "gamma": gamma, "vega": vega,
            "theta": theta, "rho": rho}


def implied_vol_surface(cfg: dict) -> pd.DataFrame:
    """Surface IV = base − skew·(moneyness−1) + term·√T (skew actions)."""
    o = cfg["options"]
    S = o["spot"]
    expiries = o["expiries_days"]
    strikes = np.round(np.linspace(0.7, 1.3, 13) * S, 0)
    rows = []
    for d in expiries:
        T = d / 365
        for K in strikes:
            m = K / S
            iv = o["base_iv"] - o["skew"] * (m - 1) + o["term"] * np.sqrt(T)
            iv = float(np.clip(iv, 0.05, 1.0))
            rows.append({"echeance_j": d, "strike": K, "iv": round(iv, 4)})
    return pd.DataFrame(rows)


def iv_at(cfg: dict, K: float, days: int) -> float:
    o = cfg["options"]; S = o["spot"]; T = days / 365
    m = K / S
    return float(np.clip(o["base_iv"] - o["skew"] * (m - 1) + o["term"] * np.sqrt(T), 0.05, 1.0))


def option_chain(cfg: dict, days: int) -> pd.DataFrame:
    """Chaîne d'options (calls & puts) pour une échéance donnée."""
    o = cfg["options"]; S = o["spot"]; r = o["rf"]; T = days / 365
    strikes = np.round(np.linspace(0.8, 1.2, 17) * S, 0)
    rows = []
    for K in strikes:
        iv = iv_at(cfg, K, days)
        for typ in ("call", "put"):
            px = bs_price(S, K, T, r, iv, typ)
            g = greeks(S, K, T, r, iv, typ)
            rows.append({"type": typ, "strike": K, "iv": round(iv, 4),
                         "prix": round(px, 2), "delta": round(g["delta"], 3),
                         "gamma": round(g["gamma"], 4), "vega": round(g["vega"], 3),
                         "theta": round(g["theta"], 4)})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Stratégies de couverture du portefeuille (indice = spot)
# --------------------------------------------------------------------------
def hedge_payoff(cfg: dict, strategy: str, days: int,
                 put_moneyness: float = 0.95, call_moneyness: float = 1.05):
    """Profil de P&L à l'échéance : portefeuille seul vs couvert."""
    o = cfg["options"]; S = o["spot"]; r = o["rf"]; T = days / 365
    ST = np.linspace(0.6 * S, 1.4 * S, 161)
    base = ST - S                                          # portefeuille nu

    Kp = round(put_moneyness * S, 0)
    Kc = round(call_moneyness * S, 0)
    put_cost = bs_price(S, Kp, T, r, iv_at(cfg, Kp, days), "put")
    call_prem = bs_price(S, Kc, T, r, iv_at(cfg, Kc, days), "call")

    if strategy == "protective_put":
        hedged = base + np.maximum(Kp - ST, 0) - put_cost
        cost = put_cost
        legs = f"Long put K={Kp:.0f} (coût {put_cost:.2f})"
    elif strategy == "covered_call":
        hedged = base - np.maximum(ST - Kc, 0) + call_prem
        cost = -call_prem
        legs = f"Short call K={Kc:.0f} (prime +{call_prem:.2f})"
    elif strategy == "collar":
        hedged = base + np.maximum(Kp - ST, 0) - np.maximum(ST - Kc, 0) - put_cost + call_prem
        cost = put_cost - call_prem
        legs = f"Long put {Kp:.0f} / Short call {Kc:.0f} (coût net {cost:.2f})"
    else:
        hedged = base.copy(); cost = 0.0; legs = "—"

    df = pd.DataFrame({"spot_echeance": ST, "portefeuille_nu": base, "couvert": hedged})
    return df, {"cout_net": float(cost), "jambes": legs, "Kp": Kp, "Kc": Kc}
