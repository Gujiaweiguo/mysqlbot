#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
REPO_ROOT="$SCRIPT_DIR"

pkill -f 'uvicorn main:app --host 0.0.0.0 --port 8000 --reload' || true
pkill -f 'uvicorn main:mcp_app --host 0.0.0.0 --port 8001 --reload' || true
pkill -f 'vite build --watch' || true
pkill -f 'vite preview --host 127.0.0.1 --port 4173' || true

docker compose -f "$REPO_ROOT/docker-compose.dev.yaml" -f "$REPO_ROOT/docker-compose.dev.redis.yaml" down

printf 'mySQLBot local dev services stopped.\n'
