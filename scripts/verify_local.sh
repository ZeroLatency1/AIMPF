#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
command -v python3.12 >/dev/null || { echo 'python3.12 is required'; exit 1; }
command -v docker >/dev/null || { echo 'docker is required for PostgreSQL'; exit 1; }
docker compose up -d postgres
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
(cd backend && alembic upgrade head && python seed.py && python auth_seed.py)
python -m compileall backend/app backend/tests backend/alembic
(cd backend && pytest -q)
(cd frontend && npm install && npm run typecheck && npm run build)
(cd frontend && npx playwright install chromium && (npm run dev >/tmp/aimpf-next.log 2>&1 & echo $! >/tmp/aimpf-next.pid))
trap 'kill "$(cat /tmp/aimpf-next.pid)" 2>/dev/null || true' EXIT
sleep 3
(cd frontend && npx playwright test)
echo 'AIMPF LOCAL VERIFICATION PASS'
