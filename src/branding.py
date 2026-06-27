"""Identité visuelle — Equity & Derivatives Desk (thème pro navy/teal)."""
from __future__ import annotations

NAVY = "#14375A"
NAVY_DARK = "#0E2840"
TEAL = "#0E9AA7"
TEAL_LIGHT = "#E6F4F5"
INK = "#15212B"
GREEN = "#1B998B"
RED = "#C0392B"

PLOTLY_COLORWAY = [TEAL, NAVY, "#F2A65A", "#7E57C2", "#1B998B", "#5C7AEA", "#E15F5F"]


def header_html() -> str:
    return f"""
<div class="qd-header">
  <div class="qd-mark">Σ</div>
  <div>
    <div class="qd-name">Equity &amp; Derivatives Desk</div>
    <div class="qd-sub">Sélection factorielle · Optimisation de portefeuille · Couverture optionnelle — marchés US</div>
  </div>
</div>"""


def css() -> str:
    return f"""
<style>
  .qd-header {{ display:flex; align-items:center; gap:14px; padding:14px 18px;
    margin:-6px 0 10px 0; background:{NAVY}; border-radius:12px; }}
  .qd-mark {{ width:44px; height:44px; border-radius:10px; background:{TEAL};
    color:white; font-size:26px; font-weight:800; display:flex;
    align-items:center; justify-content:center; }}
  .qd-name {{ font-size:1.4rem; font-weight:800; color:white; line-height:1.1; }}
  .qd-sub {{ font-size:0.82rem; color:#bcd2e0; margin-top:2px; }}
  section[data-testid="stSidebar"] {{ background:{TEAL_LIGHT}; }}
  div[data-testid="stMetric"] {{ background:white; border:1px solid #e1e9ef;
    border-radius:12px; padding:12px 14px; }}
  div[data-testid="stMetricValue"] {{ color:{NAVY}; }}
  .stDownloadButton button, .stButton button {{ background:{TEAL}; color:white;
    border:none; border-radius:8px; font-weight:600; }}
  .stDownloadButton button:hover, .stButton button:hover {{ background:{NAVY}; color:white; }}
  h2, h3 {{ color:{NAVY}; }}
  .qd-pill {{ display:inline-block; padding:2px 10px; border-radius:999px;
    background:white; color:{NAVY}; font-size:0.78rem; font-weight:700;
    border:1px solid #cfe0e6; }}

  /* Onglets st.tabs */
  div[data-baseweb="tab-list"] {{ gap:4px; border-bottom:1px solid #e1e9ef; }}
  button[data-baseweb="tab"] {{ font-weight:600; color:#5b7286;
    padding:8px 16px; border-radius:8px 8px 0 0; }}
  button[data-baseweb="tab"][aria-selected="true"] {{ color:{NAVY};
    background:{TEAL_LIGHT}; }}
  div[data-baseweb="tab-highlight"], div[data-baseweb="tab-border"] {{
    background-color:{TEAL}; }}

  /* Cartes (st.container border=True) */
  div[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius:12px;
    border-color:#e1e9ef; }}

  /* Bandeau "live" */
  .qd-live {{ display:inline-flex; align-items:center; gap:7px; font-weight:700;
    color:{RED}; font-size:0.9rem; }}
  .qd-dot {{ width:9px; height:9px; border-radius:50%; background:{RED};
    animation:qdpulse 1.4s infinite; }}
  @keyframes qdpulse {{ 0%{{opacity:1}} 50%{{opacity:.25}} 100%{{opacity:1}} }}
</style>"""
