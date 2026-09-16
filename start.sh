#!/usr/bin/env bash
set -euo pipefail

cd /app 2>/dev/null || cd "$(dirname "$0")"

mkdir -p "${DATA_DIR:-/data}" "${LOG_DIR:-/data/logs}"

if [ ! -f "webapp/dist/index.html" ] && [ -f "webapp/package.json" ]; then
  cd webapp
  npm install
  npm run build
  cd ..
fi

python3 -m uvicorn api.main:app --host 0.0.0.0 --port 3000 &
API_PID=$!

if [ -n "${BOT_TOKEN:-}" ]; then
  python3 bot.py &
  BOT_PID=$!
  wait -n "$API_PID" "$BOT_PID"
  EXIT_CODE=$?
  kill "$API_PID" "$BOT_PID" 2>/dev/null || true
  exit "$EXIT_CODE"
fi

echo "BOT_TOKEN is not set; running API/Mini App only."
wait "$API_PID"
