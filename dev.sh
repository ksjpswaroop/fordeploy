#!/usr/bin/env bash
set -euo pipefail

BACKEND_PORT=${BACKEND_PORT:-8011}
FRONTEND_PORT_PREF=${FRONTEND_PORT:-3000}
LOG_DIR=logs
mkdir -p "$LOG_DIR"

echo "[dev] Starting combined dev environment (backend:${BACKEND_PORT} frontend:${FRONTEND_PORT_PREF}*)"

# Backend
if lsof -nP -iTCP:${BACKEND_PORT} -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[dev] Backend already running on :${BACKEND_PORT}"
else
  echo "[dev] Launching backend on :${BACKEND_PORT}";
  (uvicorn app.main:app --reload --port ${BACKEND_PORT} > ${LOG_DIR}/backend_dev.log 2>&1 &) 
  sleep 2
  if lsof -nP -iTCP:${BACKEND_PORT} -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[dev] Backend up (logs -> ${LOG_DIR}/backend_dev.log)"
  else
    echo "[dev] ERROR backend failed to start; check ${LOG_DIR}/backend_dev.log"; exit 1
  fi
fi

# Frontend
pushd frontend >/dev/null
if pgrep -f "next dev" >/dev/null 2>&1; then
  echo "[dev] Frontend already running (next dev)"
else
  echo "[dev] Launching frontend (pref port ${FRONTEND_PORT_PREF})";
  (npm run dev > ../${LOG_DIR}/frontend_dev.log 2>&1 &)
  # wait a bit then detect chosen port
  sleep 4
fi
popd >/dev/null

CHOSEN_FE_PORT=$(grep -Eo 'http://localhost:[0-9]+' logs/frontend_dev.log | tail -1 | awk -F: '{print $3}')
if [ -n "${CHOSEN_FE_PORT}" ]; then
  echo "[dev] Frontend up on :${CHOSEN_FE_PORT} (logs -> ${LOG_DIR}/frontend_dev.log)"
else
  echo "[dev] Could not determine frontend port yet; check ${LOG_DIR}/frontend_dev.log"
fi

echo "[dev] Ready: API http://localhost:${BACKEND_PORT}  UI http://localhost:${CHOSEN_FE_PORT:-<pending>}"
