# Equity & Derivatives Desk

Plateforme Streamlit de **gestion de portefeuille actions (marchés US)**, de la
sélection à la couverture. Trois briques quant fusionnées en une seule chaîne :

```
Screener factoriel  →  Optimisation (Markowitz)  →  Couverture options
   value/momentum         frontière efficiente         Black-Scholes / Grecques
     /quality              max Sharpe · VaR             protective put · collar
```

## Sections de l'app

| # | Section | Contenu |
|---|---------|---------|
| 1 | Accueil | Indice de l'univers, KPI |
| 2 | Univers & données | Source (simulée / yfinance), fondamentaux, secteurs |
| 3 | **Screener factoriel** | Z-scores value · momentum · quality, ranking, shortlist |
| 4 | **Optimisation** | Frontière efficiente, max Sharpe, min variance, poids |
| 5 | **Risque** | VaR / CVaR, drawdown, contributions au risque |
| 6 | **Couverture options** | Surface de vol implicite, Grecques, protective put / covered call / collar |
| 7 | **Backtest intégré** | screen → optimise → rebalance vs équipondéré & indice |
| 8 | Export | Rapport Excel complet |

## Données

- **Simulée (défaut)** : univers de 24 actions US généré par un modèle à
  facteurs (marché + secteur + idiosyncratique) avec un alpha lié aux
  fondamentaux value/quality → les facteurs ont un vrai pouvoir prédictif.
  Générée à la volée et mise en cache : l'app s'affiche instantanément.
- **Réelle** : bascule sur `yfinance` (cours, fondamentaux, chaînes d'options)
  si le réseau est disponible ; repli automatique sur le simulé sinon.

## Lancer en local

```bash
./run_app.sh          # crée le venv, installe, démarre
# ou :
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Déploiement Streamlit Cloud

Voir **[DEPLOIEMENT.md](DEPLOIEMENT.md)** — pousser sur GitHub puis déployer sur
https://share.streamlit.io (Main file = `app.py`). Aucune donnée à committer :
tout est généré côté serveur.

## Stack

`numpy` · `pandas` · `scipy` (optimisation + Black-Scholes) · `plotly` ·
`streamlit` · `xlsxwriter` · `yfinance` (optionnel).

> Données simulées par défaut ⇒ les performances ne sont pas indicatives de
> résultats réels. Objectif : démontrer la chaîne sélection → optimisation →
> couverture.
