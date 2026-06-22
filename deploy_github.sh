#!/usr/bin/env bash
# Deploy del repo a GitHub en un comando.
# Requisito: tener GitHub CLI instalado y logueado ->  gh auth login
# Uso:   bash deploy_github.sh
set -e

REPO_NAME="flota-multas"

echo "==> Inicializando git..."
git init -q
git add .
git commit -q -m "Sistema de multas de flota: Supabase + Playwright + Actions + Streamlit"
git branch -M main

echo "==> Creando repo en GitHub y haciendo push..."
gh repo create "$REPO_NAME" --private --source=. --remote=origin --push

echo ""
echo "==> Repo creado. Ahora cargá los secrets (pegá tu service_role key cuando pida):"
read -rsp "SUPABASE_KEY (service_role): " SR_KEY; echo
gh secret set SUPABASE_URL --body "https://cadqikcbppxezlqzdxet.supabase.co"
gh secret set SUPABASE_KEY --body "$SR_KEY"
gh variable set DEMO_MODE --body "true"

echo ""
echo "LISTO. El workflow corre todos los días 02:00 ART."
echo "Para probarlo ya:  gh workflow run scraper.yml"
