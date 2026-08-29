#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r backend/requirements.txt

if [[ ! -d web/node_modules ]]; then
  (cd web && npm install)
fi

export PYTHONPATH="$ROOT/backend"
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://127.0.0.1:43148}"

python -m nightdesk &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true' EXIT

(cd web && npm run dev -- --port 43147 --hostname 127.0.0.1)
