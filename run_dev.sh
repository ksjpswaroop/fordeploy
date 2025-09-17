#!/usr/bin/env bash
set -euo pipefail

# Simple one-command launcher for backend + frontend (dev bypass auth)
# Usage: ./run_dev.sh

# --- Backend ---
if [ ! -d .venv ]; then
  echo "Python venv .venv not found. Create it first (python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt)" >&2
  exit 1
fi
source .venv/bin/activate
export DEV_BEARER_TOKEN=${DEV_BEARER_TOKEN:-dev-local-token}
export DEV_USER_ROLE=${DEV_USER_ROLE:-recruiter}
export DEV_USER_ID=${DEV_USER_ID:-1}
export DEV_TENANT_ID=${DEV_TENANT_ID:-1}

PORT=${BACKEND_PORT:-8011}
echo "Starting backend on :$PORT (dev token: $DEV_BEARER_TOKEN role: $DEV_USER_ROLE)"
uvicorn app.main:app --host 127.0.0.1 --port "$PORT" &
BACK_PID=$!

# Give backend a moment
sleep 2

# --- Frontend ---
cd frontend
export DEV_BACKEND_PORT=$PORT
export NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL:-http://127.0.0.1:$PORT/api}
export NEXT_PUBLIC_DEV_BEARER=${NEXT_PUBLIC_DEV_BEARER:-$DEV_BEARER_TOKEN}

if [ ! -f node_modules/.package-lock.json ] && [ ! -d node_modules ]; then
  echo "Installing frontend deps..."
  npm install --no-fund --no-audit
fi

echo "Starting frontend on :3000 (proxy to backend :$PORT)"
npm run dev &
FRONT_PID=$!

trap 'echo "Stopping..."; kill $BACK_PID $FRONT_PID 2>/dev/null || true' INT TERM
wait $FRONT_PID
