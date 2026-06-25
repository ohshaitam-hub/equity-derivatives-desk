#!/usr/bin/env bash
# Lance Equity & Derivatives Desk en local.
#   ./run_app.sh
set -e
cd "$(dirname "$0")"

# Mono-thread BLAS (inoffensif ; évite des blocages de thread pool sur
# certaines machines / environnements restreints).
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
       NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1

if [ ! -d ".venv" ]; then
  echo "→ Création du venv et installation des dépendances…"
  python3 -m venv .venv
  ./.venv/bin/pip install -q -r requirements.txt
fi

# Évite le prompt e-mail de Streamlit au premier lancement.
mkdir -p "$HOME/.streamlit"
[ -f "$HOME/.streamlit/credentials.toml" ] || \
  printf '[general]\nemail = ""\n' > "$HOME/.streamlit/credentials.toml"

PORT="${PORT:-8501}"
echo "→ Démarrage… ouvre/rafraîchis http://localhost:${PORT} quand le terminal"
echo "  affiche 'You can now view your Streamlit app'."
exec ./.venv/bin/streamlit run app.py --server.port "${PORT}" --server.address localhost "$@"
