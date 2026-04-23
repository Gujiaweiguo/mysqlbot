#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
REPO_ROOT="$SCRIPT_DIR"

if [[ -f "$REPO_ROOT/.env" ]]; then
  set -a
  source "$REPO_ROOT/.env"
  set +a
fi

BASE_DIR="${BASE_DIR:-$REPO_ROOT/data/sqlbot/dev/app}"
BACKEND_LOG="${BACKEND_LOG:-/tmp/mysqlbot-backend-dev.log}"
MCP_LOG="${MCP_LOG:-/tmp/mysqlbot-mcp-dev.log}"
FRONTEND_LOG="${FRONTEND_LOG:-/tmp/mysqlbot-frontend-dev.log}"
WITH_REDIS="${WITH_REDIS:-0}"

mkdir -p \
  "$BASE_DIR" \
  "$BASE_DIR/file" \
  "$BASE_DIR/excel" \
  "$BASE_DIR/images" \
  "$BASE_DIR/logs" \
  "$BASE_DIR/models" \
  "$BASE_DIR/scripts" \
  "$BASE_DIR/frontend"

ln -sfn "$REPO_ROOT/frontend/dist" "$BASE_DIR/frontend/dist"

pkill -f 'uvicorn main:app --host 0.0.0.0 --port 8000 --reload' || true
pkill -f 'uvicorn main:mcp_app --host 0.0.0.0 --port 8001 --reload' || true
pkill -f 'vite build --watch' || true
pkill -f 'vite preview --host 127.0.0.1 --port 4173' || true

compose_args=(-f "$REPO_ROOT/docker-compose.dev.yaml")
if [[ "$WITH_REDIS" == "1" ]]; then
  compose_args+=(-f "$REPO_ROOT/docker-compose.dev.redis.yaml")
fi

docker compose "${compose_args[@]}" up -d

nohup make -C "$REPO_ROOT" backend-dev > "$BACKEND_LOG" 2>&1 &
nohup make -C "$REPO_ROOT" backend-mcp-dev > "$MCP_LOG" 2>&1 &
nohup make -C "$REPO_ROOT" frontend-dev > "$FRONTEND_LOG" 2>&1 &

for _ in $(seq 1 60); do
  if curl -sf 'http://127.0.0.1:8000/health' >/dev/null 2>&1 \
    && curl -sf 'http://127.0.0.1:8001/health' >/dev/null 2>&1; then
    printf 'mySQLBot local dev is ready at http://127.0.0.1:8000/#/login\n'
    printf 'Backend log: %s\n' "$BACKEND_LOG"
    printf 'MCP log: %s\n' "$MCP_LOG"
    printf 'Frontend log: %s\n' "$FRONTEND_LOG"
    if [[ "$WITH_REDIS" == "1" ]]; then
      printf 'Redis overlay: enabled\n'
    else
      printf 'Redis overlay: disabled (set WITH_REDIS=1 to enable)\n'
    fi
    printf 'MCP endpoint: http://127.0.0.1:8001/mcp\n'
    exit 0
  fi
  sleep 1
done

printf 'Backend did not become ready in time. Check logs:\n' >&2
printf '  %s\n' "$BACKEND_LOG" >&2
printf '  %s\n' "$MCP_LOG" >&2
printf '  %s\n' "$FRONTEND_LOG" >&2
exit 1
