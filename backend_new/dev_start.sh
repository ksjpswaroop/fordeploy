#!/usr/bin/env bash
set -euo pipefail

BACKEND_PORT=${BACKEND_PORT:-8011}
FRONTEND_PORT=${FRONTEND_PORT:-3000}
BACKEND_HOST=127.0.0.1
HEALTH_PATH=/health
MAX_WAIT=${MAX_WAIT:-25}

log(){ echo "[dev] $*"; }

if [ ! -d .venv ]; then
  log "Python venv missing (.venv). Create it first."; exit 1; fi
source .venv/bin/activate

# Load .env if present (export each non-comment line KEY=VALUE)
if [ -f .env ]; then
  while IFS='=' read -r k v; do
    # skip comments / empty keys
    if [[ -z "$k" || "$k" =~ ^# ]]; then continue; fi
    # preserve existing exported overrides
    if printenv "$k" >/dev/null 2>&1; then continue; fi
    export "$k"="${v}"
  done < <(grep -v '^#' .env | sed '/^$/d')
  log ".env variables loaded (non-empty, non-comment)"
fi

# Kill any stale processes (recorded PIDs)
for f in .backend_pid .frontend_pid; do
  if [ -f "$f" ]; then
    OLD_PID=$(cat "$f" || true)
    if [ -n "${OLD_PID}" ] && ps -p "$OLD_PID" >/dev/null 2>&1; then
      log "Killing stale process $OLD_PID from $f"; kill "$OLD_PID" || true; fi
    rm -f "$f"
  fi
done

export DEV_BEARER_TOKEN=${DEV_BEARER_TOKEN:-dev-local-token}
export DEV_USER_ROLE=${DEV_USER_ROLE:-recruiter}
export DEV_USER_ID=${DEV_USER_ID:-1}
export DEV_TENANT_ID=${DEV_TENANT_ID:-1}

log "Starting backend :$BACKEND_PORT"
uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" &
BACK_PID=$!
printf %s "$BACK_PID" > .backend_pid

# Brief masked visibility for Apollo key presence (avoid leaking full key)
if [ -n "${APOLLO_API_KEY:-}" ]; then
  AK="${APOLLO_API_KEY}"
  if [ ${#AK} -ge 8 ]; then MASKED="${AK:0:4}***${AK: -4}"; else MASKED="***"; fi
  log "Apollo key detected ($MASKED)"
else
  log "Apollo key NOT set (APOLLO_API_KEY empty)"
fi

# Wait for backend health
ATTEMPT=0
until curl -sf "http://$BACKEND_HOST:$BACKEND_PORT$HEALTH_PATH" >/dev/null 2>&1; do
  ATTEMPT=$((ATTEMPT+1))
  if [ $ATTEMPT -ge $MAX_WAIT ]; then
    log "Backend failed to become healthy after $MAX_WAIT attempts"; exit 2; fi
  sleep 1
  if ! ps -p $BACK_PID >/dev/null 2>&1; then
    log "Backend process died (pid $BACK_PID)."; exit 3; fi
  if [ $((ATTEMPT%5)) -eq 0 ]; then log "Still waiting backend... ($ATTEMPT)"; fi
done
log "Backend healthy (pid $BACK_PID)"

cd frontend
export NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE:-http://$BACKEND_HOST:$BACKEND_PORT/api}
export NEXT_PUBLIC_DEV_BEARER=${NEXT_PUBLIC_DEV_BEARER:-$DEV_BEARER_TOKEN}

# Install deps if needed
if [ ! -d node_modules ]; then log "Installing frontend dependencies"; npm install --no-fund --no-audit; fi

log "Starting frontend :$FRONTEND_PORT"
npm run dev -- --port "$FRONTEND_PORT" &
FRONT_PID=$!
printf %s "$FRONT_PID" > ../.frontend_pid

# Simple readiness probe: check root returns something (ignore status codes, just connectivity)
ATTEMPT=0
until curl -sf "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1; do
  ATTEMPT=$((ATTEMPT+1))
  if [ $ATTEMPT -ge $MAX_WAIT ]; then
    log "Frontend failed to respond after $MAX_WAIT attempts"; exit 4; fi
  sleep 1
  if ! ps -p $FRONT_PID >/dev/null 2>&1; then
    log "Frontend process died (pid $FRONT_PID)."; exit 5; fi
  if [ $((ATTEMPT%5)) -eq 0 ]; then log "Still waiting frontend... ($ATTEMPT)"; fi
done
log "Frontend responding (pid $FRONT_PID)"

log "All services up: Backend http://$BACKEND_HOST:$BACKEND_PORT  Frontend http://localhost:$FRONTEND_PORT"
log "Dev bearer token: $DEV_BEARER_TOKEN"

wait $FRONT_PID
