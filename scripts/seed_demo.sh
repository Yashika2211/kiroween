#!/usr/bin/env bash
# Summon (and optionally resurrect) the three demo repositories on a running API,
# so a fresh deployment shows a populated graveyard to judges.
#
#   scripts/seed_demo.sh [API_URL] [--resurrect]
set -euo pipefail

API="${1:-http://localhost:8000}"
RESURRECT="${2:-}"
REPOS=(opendoor-labs/pyfin eigenhombre/PyClojure nvie/times)

status() { curl -fsS "$API/api/jobs/$1" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])'; }

wait_for() {  # job_id, terminal statuses...
  local id="$1"; shift
  for _ in $(seq 1 200); do
    local s; s="$(status "$id")"
    for want in "$@"; do [[ "$s" == "$want" ]] && { echo "$s"; return; }; done
    sleep 3
  done
  echo "timeout"
}

curl -fsS "$API/api/health" >/dev/null || { echo "API not reachable at $API" >&2; exit 1; }

for repo in "${REPOS[@]}"; do
  id="$(curl -fsS -X POST "$API/api/summon" -H 'Content-Type: application/json' \
        -d "{\"url\":\"https://github.com/$repo\"}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
  printf '%-24s %s  autopsy: %s' "$repo" "$id" "$(wait_for "$id" autopsied failed rejected)"
  if [[ "$RESURRECT" == "--resurrect" ]]; then
    curl -fsS -X POST "$API/api/jobs/$id/resurrect" >/dev/null
    printf '  ritual: %s' "$(wait_for "$id" risen failed)"
  fi
  echo
done
