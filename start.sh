SSR_PATH=/opt/sqlbot/g2-ssr
APP_PATH=/opt/sqlbot/app
PM2_CMD_PATH=$SSR_PATH/node_modules/pm2/bin/pm2
DB_HOST=${POSTGRES_SERVER:-postgresql}
DB_PORT=${POSTGRES_PORT:-5432}
MCP_BIND_HOST=${MCP_BIND_HOST:-0.0.0.0}
MCP_PORT=${MCP_PORT:-8001}

python - <<'PY'
import os
import socket
import time

host = os.getenv("POSTGRES_SERVER", "postgresql")
port = int(os.getenv("POSTGRES_PORT", "5432"))
timeout_seconds = 120
deadline = time.time() + timeout_seconds

while True:
    try:
        with socket.create_connection((host, port), timeout=2):
            print("\033[1;32mPostgreSQL started.\033[0m")
            break
    except OSError:
        if time.time() >= deadline:
            raise SystemExit(f"PostgreSQL not reachable at {host}:{port} within {timeout_seconds}s")
        time.sleep(1)
PY

nohup $PM2_CMD_PATH start $SSR_PATH/app.js &
#nohup node $SSR_PATH/app.js &

nohup uvicorn main:mcp_app --host "$MCP_BIND_HOST" --port "$MCP_PORT" &

cd $APP_PATH
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers
