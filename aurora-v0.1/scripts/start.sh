#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python || ! -d frontend/node_modules ]]; then
  echo 'Instale as dependências conforme o README antes de iniciar.'
  exit 1
fi
if [[ ! -f backend/.env && -z "${AURORA_OWNER_TOKEN:-}" ]]; then
  echo 'Execute: python scripts/configure.py'
  exit 1
fi
backend_pid=''
frontend_pid=''
cleanup() {
  trap - EXIT INT TERM
  [[ -z "$backend_pid" ]] || kill "$backend_pid" 2>/dev/null || true
  [[ -z "$frontend_pid" ]] || kill "$frontend_pid" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 &
backend_pid=$!
host='127.0.0.1'
if [[ "${CODESPACES:-}" == 'true' ]]; then host='0.0.0.0'; fi
node frontend/node_modules/vite/bin/vite.js frontend --config frontend/vite.config.js --host "$host" &
frontend_pid=$!
echo 'Aurora: http://localhost:5173 • API: http://localhost:8000/docs'
echo 'Codespaces: abra a porta 5173 na aba Ports e mantenha a visibilidade Private.'
echo 'Ctrl+C encerra frontend e backend. Use somente um worker.'
wait -n "$backend_pid" "$frontend_pid"
