#!/bin/zsh
# OpenMarvis launcher — starts backend + frontend and opens the browser.
# Usage: ./start.sh   or double-click OpenMarvis.command on the Desktop

set -e

PROJECT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$PROJECT/apps/backend"
WEB="$PROJECT/apps/web"
LOG_DIR="$PROJECT/.logs"
mkdir -p "$LOG_DIR"

BACKEND_PID=""
WEB_PID=""

cleanup() {
  echo ""
  echo "[OpenMarvis] Shutting down..."
  [[ -n "$BACKEND_PID" ]] && kill "$BACKEND_PID" 2>/dev/null || true
  [[ -n "$WEB_PID"     ]] && kill "$WEB_PID"     2>/dev/null || true
  wait "$BACKEND_PID" "$WEB_PID" 2>/dev/null || true
  echo "[OpenMarvis] Stopped. Run ./start.sh again to restart."
}
trap cleanup INT TERM

port_in_use() { lsof -i ":$1" -sTCP:LISTEN -t &>/dev/null; }

# ── Preflight checks ────────────────────────────────────────────────
if [[ ! -f "$BACKEND/.venv/bin/uvicorn" ]]; then
  echo "[ERROR] Backend not installed. Run: cd $PROJECT && make install"
  exit 1
fi

if [[ ! -f "$WEB/node_modules/.bin/next" ]]; then
  echo "[ERROR] Frontend not installed. Run: cd $PROJECT && make install"
  exit 1
fi

if [[ ! -f "$BACKEND/.env" ]]; then
  echo "[ERROR] Missing $BACKEND/.env"
  echo "        Run: cp $BACKEND/.env.example $BACKEND/.env"
  echo "        Then add your API key (ANTHROPIC_API_KEY / DEEPSEEK_API_KEY)"
  exit 1
fi

# ── Backend ─────────────────────────────────────────────────────────
if port_in_use 8000; then
  echo "[OpenMarvis] Port 8000 already in use — skipping backend start"
else
  echo "[OpenMarvis] Starting backend on :8000 ..."
  cd "$BACKEND"
  .venv/bin/uvicorn openmarvis.main:app --port 8000 \
    > "$LOG_DIR/backend.log" 2>&1 &
  BACKEND_PID=$!

  for i in $(seq 1 20); do
    sleep 0.5
    curl -s http://127.0.0.1:8000/healthz &>/dev/null && break
    if [[ $i -eq 20 ]]; then
      echo "[ERROR] Backend failed to start. Check: $LOG_DIR/backend.log"
      exit 1
    fi
  done
  echo "[OpenMarvis] Backend ready"
fi

# ── Frontend ─────────────────────────────────────────────────────────
if port_in_use 3000; then
  echo "[OpenMarvis] Port 3000 already in use — skipping frontend start"
else
  echo "[OpenMarvis] Starting frontend on :3000 ..."
  cd "$WEB"
  npm run dev > "$LOG_DIR/web.log" 2>&1 &
  WEB_PID=$!

  for i in $(seq 1 40); do
    sleep 1
    curl -s http://localhost:3000 &>/dev/null && break
    if [[ $i -eq 40 ]]; then
      echo "[ERROR] Frontend failed to start. Check: $LOG_DIR/web.log"
      exit 1
    fi
  done
  echo "[OpenMarvis] Frontend ready"
fi

# ── Open browser ─────────────────────────────────────────────────────
echo "[OpenMarvis] Opening http://localhost:3000"
open http://localhost:3000

echo ""
echo "  Backend log : $LOG_DIR/backend.log"
echo "  Frontend log: $LOG_DIR/web.log"
echo ""
echo "  Press Ctrl+C to stop all services."
echo ""

wait "$BACKEND_PID" "$WEB_PID" 2>/dev/null || true
