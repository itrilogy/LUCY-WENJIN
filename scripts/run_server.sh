#!/usr/bin/env bash
# 生产友好启动：默认关闭 debug
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export FLASK_DEBUG="${FLASK_DEBUG:-0}"
export GAOKAO_HOST="${GAOKAO_HOST:-0.0.0.0}"
export GAOKAO_PORT="${GAOKAO_PORT:-5080}"
# 可选：export GAOKAO_API_TOKEN=your-token
# 可选：export DEEPSEEK_API_KEY=...
# 可选：export GAOKAO_PLAN_YEAR=2026 GAOKAO_SCORE_YEAR=2025

if command -v gunicorn >/dev/null 2>&1; then
  exec gunicorn -b "${GAOKAO_HOST}:${GAOKAO_PORT}" -w 1 --threads 4 "app:app"
else
  exec python3 app.py
fi
