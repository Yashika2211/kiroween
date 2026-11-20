#!/usr/bin/env bash
# Deploy Necromancer: API on Fly.io, UI on Vercel, then seed the demo graves.
#
# Prerequisites (one time):  fly auth login   and   vercel login
# Optional secrets:          export GITHUB_TOKEN=... ANTHROPIC_API_KEY=...   before running
#
#   scripts/deploy.sh [fly-app-name]
set -euo pipefail
cd "$(dirname "$0")/.."

APP="${1:-necromancer-kiroween}"
API_URL="https://$APP.fly.dev"

echo "==> API: Fly app $APP"
cd backend
if ! fly apps list --json | grep -q "\"Name\": *\"$APP\""; then
  fly apps create "$APP"
fi
if ! fly volumes list -a "$APP" --json | grep -q '"name": *"necro_data"'; then
  fly volumes create necro_data -a "$APP" --region iad --size 10 --yes
fi
secrets=()
[[ -n "${GITHUB_TOKEN:-}" ]] && secrets+=("GITHUB_TOKEN=$GITHUB_TOKEN")
[[ -n "${ANTHROPIC_API_KEY:-}" ]] && secrets+=("ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY")
if ((${#secrets[@]})); then fly secrets set -a "$APP" --stage "${secrets[@]}"; fi
fly deploy -a "$APP" --config fly.toml --ha=false
cd ..

echo "==> Waiting for $API_URL"
for _ in $(seq 1 60); do curl -fsS "$API_URL/api/health" && break; sleep 5; done
echo

echo "==> UI: Vercel"
cd frontend
vercel link --yes --project necromancer >/dev/null
vercel env rm NEXT_PUBLIC_API_URL production --yes >/dev/null 2>&1 || true
printf '%s' "$API_URL" | vercel env add NEXT_PUBLIC_API_URL production >/dev/null
WEB_URL="$(vercel deploy --prod --yes | tail -1)"
cd ..

echo "==> Allow the UI origin on the API"
fly secrets set -a "$APP" NECRO_CORS_ORIGINS="$WEB_URL,https://necromancer.vercel.app"

echo "==> Seeding the graveyard"
scripts/seed_demo.sh "$API_URL" --resurrect || true

echo
echo "API: $API_URL"
echo "UI:  $WEB_URL"
