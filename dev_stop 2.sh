#!/usr/bin/env bash
set -euo pipefail
log(){ echo "[dev] $*"; }

STOPPED=0
if [ -f .frontend_pid ]; then
  PID=$(cat .frontend_pid || true)
  if [ -n "$PID" ] && ps -p "$PID" >/dev/null 2>&1; then
    log "Stopping frontend $PID"; kill "$PID" || true; STOPPED=1; fi
  rm -f .frontend_pid
fi
if [ -f .backend_pid ]; then
  PID=$(cat .backend_pid || true)
  if [ -n "$PID" ] && ps -p "$PID" >/dev/null 2>&1; then
    log "Stopping backend $PID"; kill "$PID" || true; STOPPED=1; fi
  rm -f .backend_pid
fi
if [ $STOPPED -eq 0 ]; then log "No running dev processes found"; else log "All dev processes stopped"; fi
