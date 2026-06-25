"""Equity & Derivatives Desk — application Streamlit.

Chaîne de gestion de portefeuille actions (marchés US) :
sélection factorielle -> optimisation Markowitz -> risque -> couverture
optionnelle -> backtest intégré -> export Excel.

Lancement local :  ./run_app.sh      (ou : streamlit run app.py)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from src.common import load_config
from src import data, factors, optimizer, risk, options_bs as opt_bs, backtest
from src import branding as bd
from src.webexport import build_excel

st.set_page_config(page_title="Equity & Derivatives Desk", page_icon="📈",
                   layout="wide", initial_sidebar_state="expanded")
st.markdown(bd.css(), unsafe_allow_html=True)
st.markdown(bd.header_html(), unsafe_allow_html=True)

CFG = load_config()


# ===================== Données (cache) =====================
@st.cache_data(show_spinner=False)
def _load(source):
    return data.get_data(CFG, source)


@st.cache_data(show_spinner=False)
def _factors(source):
    px, fund, _ = _load(source)
    return factors.compute_factors(px, fund)


@st.cache_data(show_spinner=True)
def _bt(source):
    px, fund, _ = _load(source)
    return backtest.run_backtest(px, fund, CFG)


def bundle():
    return _load(st.session_state.get("source", "synthetique"))


def current_selection():
    px, fund, _ = bundle()
    fac = _factors(st.session_state.get("source", "synthetique"))
    sel = st.session_state.get("selected") or factors.screen(fac, CFG["factors"]["top_n"])
    sel = [t for t in sel if t in px.columns]
    return px, fund, fac, sel


def current_weights():
    px, fund, fac, sel = current_selection()
    w = st.session_state.get("weights")
    if isinstance(w, pd.Series) and set(w.index) <= set(px.columns):
        return px, w
    mu, cov, tk = optimizer.mean_cov(px, sel, lookback=CFG["backtest"]["lookback_days"])
    ws = optimizer.max_sharpe(mu, cov, rf=CFG["optimizer"]["rf_annual"],
                              max_w=CFG["optimizer"]["max_weight"])
    return px, pd.Series(ws, index=tk)


# ===================== Helpers graphiques =====================
def _layout(fig, title=None, h=380):
    fig.update_layout(title=title, height=h, margin=dict(l=10, r=10, t=44, b=10),
                      colorway=bd.PLOTLY_COLORWAY, plot_bgcolor="white",
                      paper_bgcolor="white", font=dict(color=bd.INK),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    fig.update_xaxes(showgrid=True, gridcolor="#eef2f5")
    fig.update_yaxes(showgrid=True, gridcolor="#eef2f5")
    return fig


def line(df, title=None, h=360):
    fig = go.Figure()
    for c in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[c], name=str(c), mode="lines"))
    st.plotly_chart(_layout(fig, title, h), use_container_width=True)


def dl(label, sheets, fname, key):
    try:
        st.download_button("⬇️  " + label, data=build_excel(sheets), file_name=fname,
                           mime="application/vnd.openxmlformats-officedocument."
                                "spreadsheetml.sheet", key=key)
    except Exception as e:
        st.caption(f"(export indisponible : {e})")


# ===================== PAGES =====================
def page_accueil():
    st.subheader("Vue d'ensemble")
    px, fund, mode = bundle()
    idx = (1 + px.pct_change().mean(axis=1).fillna(0)).cumprod() * 100
    c = st.columns(4)
    c[0].metric("Univers", f"{px.shape[1]} actions")
    c[1].metric("Historique", f"{px.index[0].date()} → {px.index[-1].date()}")
    c[2].metric("Perf. indice", f"{idx.iloc[-1]/idx.iloc[0]-1:+.1%}")
    c[3].metric("Source", "réelle (yfinance)" if mode == "reel" else "simulée")
    line(idx.to_frame("Indice équipondéré (base 100)"), "Indice de l'univers")
    st.info("Workflow : **Screener** → **Optimisation** → **Risque** → "
            "**Couverture options** → **Backtest** → **Export**. Navigue par le menu de gauche.")


def page_donnees():
    st.subheader("📥 Univers & données")
    src = st.radio("Source des données", ["synthetique", "reel"],
                   format_func=lambda x: "Simulée (instantané)" if x == "synthetique"
                   else "Réelle — yfinance (nécessite réseau)", horizontal=True,
                   index=0 if st.session_state.get("source", "synthetique") == "synthetique" else 1)
    if src != st.session_state.get("source"):
        st.session_state["source"] = src
        st.rerun()
    px, fund, mode = bundle()
    if src == "reel" and mode != "reel":
        st.warning("yfinance indisponible ou hors-ligne → données simulées utilisées.")
    st.markdown("##### Fondamentaux")
    st.dataframe(fund.drop(columns=[c for c in ["_alpha"] if c in fund.columns]),
                 use_container_width=True)
    st.markdown("##### Répartition sectorielle")
    sec = fund["secteur"].value_counts()
    fig = go.Figure(go.Bar(x=sec.index, y=sec.values, marker_color=bd.TEAL))
    st.plotly_chart(_layout(fig, "Nombre de titres par secteur", 320), use_container_width=True)
    dl("Exporter données (Excel)", {"fondamentaux": fund, "prix": px.tail(252)},
       "univers.xlsx", "dl_data")


def page_screener():
    st.subheader("🔎 Screener factoriel — value · momentum · quality")
    px, fund, _ = bundle()
    fac = _factors(st.session_state.get("source", "synthetique"))
    top_n = st.slider("Taille de la shortlist", 5, min(20, len(fac)),
                      CFG["factors"]["top_n"])
    sel_default = factors.screen(fac, top_n)
    sel = st.multiselect("Actions sélectionnées (ajuste si besoin)",
                         list(fac.index), default=sel_default)
    st.session_state["selected"] = sel
    st.session_state.pop("weights", None)   # invalide l'optim précédente

    fig = go.Figure(go.Bar(x=fac.index, y=fac["score"],
                           marker_color=["#0E9AA7" if t in sel else "#cdd9e0" for t in fac.index]))
    st.plotly_chart(_layout(fig, "Score composite par action (sélection en couleur)"),
                    use_container_width=True)
    st.dataframe(fac.round(3), use_container_width=True)
    dl("Exporter screener (Excel)", {"facteurs": fac.round(4)}, "screener.xlsx", "dl_scr")


def page_optim():
    st.subheader("⚖️ Optimisation — frontière efficiente (Markowitz)")
    px, fund, fac, sel = current_selection()
    if len(sel) < 2:
        st.warning("Sélectionne au moins 2 actions dans le Screener.")
        return
    mu, cov, tk = optimizer.mean_cov(px, sel, lookback=CFG["backtest"]["lookback_days"])
    rf, maxw = CFG["optimizer"]["rf_annual"], CFG["optimizer"]["max_weight"]

    front = optimizer.efficient_frontier(mu, cov, max_w=maxw)
    w_ms = optimizer.max_sharpe(mu, cov, rf=rf, max_w=maxw)
    w_mv = optimizer.min_variance(mu, cov, max_w=maxw)
    _, s_ms = optimizer.weights_table(w_ms, tk, mu, cov, rf)
    _, s_mv = optimizer.weights_table(w_mv, tk, mu, cov, rf)

    fig = go.Figure()
    if len(front):
        fig.add_trace(go.Scatter(x=front["volatilite"], y=front["rendement"],
                                 mode="lines", name="Frontière efficiente", line=dict(color=bd.NAVY)))
    fig.add_trace(go.Scatter(x=[np.sqrt(np.diag(cov))[i] for i in range(len(tk))],
                             y=mu, mode="markers", name="Actions",
                             marker=dict(color="#cdd9e0", size=8), text=tk))
    fig.add_trace(go.Scatter(x=[s_ms["volatilite"]], y=[s_ms["rendement"]], mode="markers",
                             name="Max Sharpe", marker=dict(color=bd.TEAL, size=14, symbol="star")))
    fig.add_trace(go.Scatter(x=[s_mv["volatilite"]], y=[s_mv["rendement"]], mode="markers",
                             name="Min variance", marker=dict(color="#F2A65A", size=13, symbol="diamond")))
    fig.update_xaxes(title="volatilité annualisée"); fig.update_yaxes(title="rendement annualisé")
    st.plotly_chart(_layout(fig, "Frontière efficiente & portefeuilles clés"), use_container_width=True)

    obj = st.radio("Portefeuille retenu", ["Max Sharpe", "Min variance"], horizontal=True)
    w = w_ms if obj == "Max Sharpe" else w_mv
    stats = s_ms if obj == "Max Sharpe" else s_mv
    tab, _ = optimizer.weights_table(w, tk, mu, cov, rf)
    st.session_state["weights"] = pd.Series(w, index=tk)

    cc = st.columns([2, 1])
    with cc[0]:
        fig2 = go.Figure(go.Bar(x=tab.index, y=tab["poids"], marker_color=bd.TEAL))
        st.plotly_chart(_layout(fig2, f"Poids — {obj}", 320), use_container_width=True)
    with cc[1]:
        st.metric("Rendement att.", f"{stats['rendement']:.1%}")
        st.metric("Volatilité", f"{stats['volatilite']:.1%}")
        st.metric("Sharpe", f"{stats['sharpe']:.2f}")
    dl("Exporter portefeuille (Excel)",
       {"poids": tab, "frontiere": front}, "portefeuille.xlsx", "dl_opt")


def page_risque():
    st.subheader("🎲 Risque — VaR / CVaR, drawdown, contributions")
    px, w = current_weights()
    mu, cov, tk = optimizer.mean_cov(px, list(w.index), lookback=CFG["backtest"]["lookback_days"])
    conf = CFG["risk"]["var_confidence"]
    summ = risk.summary(px, w, cov, conf)
    c = st.columns(4)
    c[0].metric(f"VaR {int(conf*100)}% (1j)", f"{summ[f'VaR_{int(conf*100)}_1j']:.2%}")
    c[1].metric(f"CVaR {int(conf*100)}% (1j)", f"{summ[f'CVaR_{int(conf*100)}_1j']:.2%}")
    c[2].metric("Vol annualisée", f"{summ['vol_annualisee']:.1%}")
    c[3].metric("Max drawdown", f"{summ['max_drawdown']:.1%}")

    cc = st.columns(2)
    with cc[0]:
        r = summ["returns"]
        fig = go.Figure(go.Histogram(x=r, nbinsx=60, marker_color=bd.NAVY))
        fig.add_vline(x=-summ[f"VaR_{int(conf*100)}_1j"], line_dash="dash", line_color=bd.RED)
        st.plotly_chart(_layout(fig, "Distribution des rendements quotidiens", 320),
                        use_container_width=True)
    with cc[1]:
        rc = risk.risk_contributions(w, cov).sort_values(ascending=False)
        fig2 = go.Figure(go.Bar(x=rc.index, y=rc.values, marker_color=bd.TEAL))
        st.plotly_chart(_layout(fig2, "Contribution au risque (%)", 320), use_container_width=True)
    line(summ["equity"].to_frame("Équité (base 1)"), "Courbe d'équité du portefeuille", 300)
    dl("Exporter risque (Excel)",
       {"poids": w.to_frame("poids"),
        "contrib_risque": risk.risk_contributions(w, cov).to_frame("contrib")},
       "risque.xlsx", "dl_risk")


def page_options():
    st.subheader("🛡️ Couverture options — surface de vol & Grecques")
    c = st.columns(3)
    days = c[0].selectbox("Échéance (jours)", CFG["options"]["expiries_days"], index=2)
    strat = c[1].selectbox("Stratégie", ["protective_put", "covered_call", "collar"],
                           format_func=lambda s: {"protective_put": "Protective put",
                                                  "covered_call": "Covered call",
                                                  "collar": "Collar"}[s])
    putm = c[2].slider("Strike put (% spot)", 0.80, 1.00, 0.95, 0.01)
    callm = st.slider("Strike call (% spot)", 1.00, 1.20, 1.05, 0.01)

    # Surface de vol
    surf = opt_bs.implied_vol_surface(CFG)
    piv = surf.pivot(index="strike", columns="echeance_j", values="iv")
    fig = go.Figure(go.Heatmap(z=piv.values, x=[str(c) for c in piv.columns],
                               y=piv.index, colorscale="Viridis", colorbar=dict(title="IV")))
    fig.update_xaxes(title="échéance (j)"); fig.update_yaxes(title="strike")
    st.plotly_chart(_layout(fig, "Surface de volatilité implicite", 340), use_container_width=True)

    # Payoff couverture
    pay, info = opt_bs.hedge_payoff(CFG, strat, days, putm, callm)
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=pay["spot_echeance"], y=pay["portefeuille_nu"],
                              name="Portefeuille nu", line=dict(color="#cdd9e0")))
    fig2.add_trace(go.Scatter(x=pay["spot_echeance"], y=pay["couvert"],
                              name="Couvert", line=dict(color=bd.TEAL, width=3)))
    fig2.add_hline(y=0, line_color="#999"); fig2.update_xaxes(title="spot à l'échéance")
    fig2.update_yaxes(title="P&L")
    st.plotly_chart(_layout(fig2, f"Profil de P&L — {strat}", 340), use_container_width=True)
    st.caption(f"Jambes : {info['jambes']} · coût net : {info['cout_net']:.2f}")

    st.markdown("##### Chaîne d'options (échéance sélectionnée)")
    st.dataframe(opt_bs.option_chain(CFG, days), use_container_width=True, height=280)
    dl("Exporter options (Excel)",
       {"surface_iv": surf, "chaine": opt_bs.option_chain(CFG, days), "payoff": pay},
       "options.xlsx", "dl_opt2")


def page_backtest():
    st.subheader("🔁 Backtest intégré — screen → optimise → rebalance")
    curves, metrics = _bt(st.session_state.get("source", "synthetique"))
    line(curves, "Courbes d'équité (base 1)", 380)
    st.dataframe(metrics.style.format({"CAGR": "{:.1%}", "Vol": "{:.1%}",
                                       "Sharpe": "{:.2f}", "Max DD": "{:.1%}"}),
                 use_container_width=True)
    dl("Exporter backtest (Excel)",
       {"equity": curves, "metriques": metrics}, "backtest.xlsx", "dl_bt")


def page_export():
    st.subheader("📑 Export global")
    px, w = current_weights()
    fac = _factors(st.session_state.get("source", "synthetique"))
    mu, cov, tk = optimizer.mean_cov(px, list(w.index))
    sheets = {
        "facteurs": fac.round(4),
        "portefeuille": w.to_frame("poids"),
        "contrib_risque": risk.risk_contributions(w, cov).to_frame("contrib"),
        "surface_iv": opt_bs.implied_vol_surface(CFG),
    }
    st.markdown("Classeur regroupant screener, portefeuille, risque et options.")
    dl("⬇️  Télécharger le rapport complet (Excel)", sheets, "rapport_desk.xlsx", "dl_all")


# ===================== Navigation =====================
PAGES = {
    "🏠  Accueil": page_accueil,
    "📥  Univers & données": page_donnees,
    "🔎  Screener factoriel": page_screener,
    "⚖️  Optimisation": page_optim,
    "🎲  Risque": page_risque,
    "🛡️  Couverture options": page_options,
    "🔁  Backtest intégré": page_backtest,
    "📑  Export": page_export,
}

with st.sidebar:
    st.markdown("<div class='qd-pill'>Marchés US · actions & options</div>",
                unsafe_allow_html=True)
    st.markdown("### Sections")
    choice = st.radio("Navigation", list(PAGES.keys()), label_visibility="collapsed")

PAGES[choice]()

st.markdown("<hr style='border-color:#e1e9ef'>", unsafe_allow_html=True)
st.caption("Equity & Derivatives Desk · prototype · données simulées par défaut "
           "(option yfinance pour le réel).")
