"""Microstructure de marché : Bid-Ask en direct, carnet d'ordres, coût de liquidité.

Le « flux en direct » est rafraîchi périodiquement par l'app (st.fragment).
Par défaut il est SIMULÉ de façon réaliste : le mid suit une marche aléatoire,
le spread (en bp) est mean-reverting et s'élargit dans les phases de stress,
les tailles bid/ask varient. Un mode `yfinance` (snapshot) est disponible si
le réseau le permet.

Métriques fournies : spread, spread en bp, mid, microprice (pondéré par les
tailles), profondeur du carnet, et coût d'exécution (slippage) pour une taille
d'ordre donnée en « marchant » dans le carnet.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------
# Génération du flux simulé
# --------------------------------------------------------------------------
def liquidity_tier(price: float) -> float:
    """Spread de base (bp) selon le niveau de prix (proxy de liquidité)."""
    if price >= 200:
        return 2.0
    if price >= 80:
        return 3.5
    if price >= 30:
        return 5.0
    return 8.0


def new_state(ticker: str, last_price: float, seed: int = 0) -> dict:
    return {"ticker": ticker, "mid": float(last_price),
            "base_bps": liquidity_tier(last_price), "stress": 0.0,
            "tick": 0, "seed": seed}


def next_tick(state: dict) -> dict:
    """Fait évoluer le mid, le spread et les tailles d'un cran."""
    rng = np.random.default_rng(state["seed"] * 100003 + state["tick"] + 1)
    mid = state["mid"] * float(np.exp(rng.normal(0, 0.0008)))     # marche aléatoire
    # régime de stress mean-reverting (élargit le spread par à-coups)
    stress = 0.92 * state["stress"] + rng.normal(0, 0.25)
    stress = float(np.clip(stress, 0, 3))
    half_bps = state["base_bps"] * (1 + 0.6 * stress) / 2
    bid = mid * (1 - half_bps / 1e4)
    ask = mid * (1 + half_bps / 1e4)
    bid_size = int(rng.integers(3, 40) * (1 + (rng.random() < 0.15) * 5))
    ask_size = int(rng.integers(3, 40) * (1 + (rng.random() < 0.15) * 5))
    new = dict(state)
    new.update({"mid": mid, "stress": stress, "tick": state["tick"] + 1,
                "bid": bid, "ask": ask, "bid_size": bid_size, "ask_size": ask_size})
    return new


def spread_metrics(q: dict) -> dict:
    bid, ask = q["bid"], q["ask"]
    mid = 0.5 * (bid + ask)
    bs, as_ = q["bid_size"], q["ask_size"]
    micro = (ask * bs + bid * as_) / (bs + as_)          # microprice
    return {"mid": mid, "spread": ask - bid,
            "spread_bps": (ask - bid) / mid * 1e4,
            "microprice": micro,
            "imbalance": (bs - as_) / (bs + as_)}


def order_book(q: dict, n_levels: int = 8) -> pd.DataFrame:
    """Carnet synthétique : N niveaux de chaque côté, tailles décroissantes."""
    rng = np.random.default_rng(q["seed"] * 7 + q["tick"])
    mid = 0.5 * (q["bid"] + q["ask"])
    tick = max(round(mid * 0.0001, 2), 0.01)            # pas de cotation
    rows = []
    for i in range(n_levels):
        p_bid = q["bid"] - i * tick
        p_ask = q["ask"] + i * tick
        decay = np.exp(-0.25 * i)
        rows.append({"cote": "bid", "niveau": i + 1, "prix": round(p_bid, 2),
                     "taille": int(q["bid_size"] * decay * rng.uniform(0.6, 1.4)) + 1})
        rows.append({"cote": "ask", "niveau": i + 1, "prix": round(p_ask, 2),
                     "taille": int(q["ask_size"] * decay * rng.uniform(0.6, 1.4)) + 1})
    return pd.DataFrame(rows)


def liquidity_cost(book: pd.DataFrame, side: str, qty: int, mid: float) -> dict:
    """Marche dans le carnet pour exécuter `qty` (lots) -> prix moyen & slippage."""
    side_book = book[book["cote"] == ("ask" if side == "achat" else "bid")].copy()
    side_book = side_book.sort_values("prix", ascending=(side == "achat"))
    remaining = qty
    cost = 0.0
    filled = 0
    for _, lvl in side_book.iterrows():
        take = min(remaining, lvl["taille"])
        cost += take * lvl["prix"]
        filled += take
        remaining -= take
        if remaining <= 0:
            break
    if filled == 0:
        return {"prix_moyen": mid, "slippage_bps": 0.0, "rempli": 0, "demande": qty}
    avg = cost / filled
    slip = (avg - mid) / mid * 1e4 * (1 if side == "achat" else -1)
    return {"prix_moyen": avg, "slippage_bps": slip, "rempli": int(filled), "demande": qty}


def quality(spread_bps: float) -> tuple[str, str]:
    """Étiquette de qualité de liquidité (libellé, couleur)."""
    if spread_bps < 3:
        return "Excellente", "#1B998B"
    if spread_bps < 6:
        return "Bonne", "#0E9AA7"
    if spread_bps < 12:
        return "Moyenne", "#F2A65A"
    return "Faible", "#C0392B"


# --------------------------------------------------------------------------
# Mode réel (snapshot yfinance) — optionnel
# --------------------------------------------------------------------------
def yf_quote(ticker: str):
    try:
        import yfinance as yf
        fi = yf.Ticker(ticker).fast_info
        bid, ask = fi.get("bid"), fi.get("ask")
        if bid and ask and ask > bid > 0:
            return {"bid": float(bid), "ask": float(ask),
                    "bid_size": 0, "ask_size": 0}
    except Exception:
        pass
    return None
