
<h3 align="center">Intelligent Questioning System Based on Large Models and RAG</h3>
<p align="center">
  <a href="https://trendshift.io/repositories/14540" target="_blank"><img src="https://trendshift.io/api/badge/repositories/14540" alt="dataease%2FmySQLBot | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>
</p>


<p align="center">
  <a href="README.md"><img alt="中文(简体)" src="https://img.shields.io/badge/中文(简体)-d9d9d9"></a>
  <a href="/docs/README.en.md"><img alt="English" src="https://img.shields.io/badge/English-d9d9d9"></a>
</p>
<hr/>

mySQLBot is an intelligent data query system based on large language models and RAG, meticulously crafted by the DataEase open-source project team. With mySQLBot, users can perform conversational data analysis (ChatBI), quickly extracting the necessary data information and visualizations, and supporting further intelligent analysis.

## How It Works

<img width="1105" height="577" alt="image" src="https://github.com/user-attachments/assets/58f147ff-412e-4ac9-a450-5d01a0bbe9f6" />


## Key Features

- **Out-of-the-Box Functionality:** Simply configure the large model and data source; no complex development is required to quickly enable intelligent data collection. Leveraging the large model's natural language understanding and SQL generation capabilities, combined with RAG technology, it achieves high-quality Text-to-SQL conversion.
- **Secure and Controllable:** Provides a workspace-level resource isolation mechanism, building clear data boundaries and ensuring data access security. Supports fine-grained data permission configuration, strengthening permission control capabilities and ensuring compliance and controllability during use.
- **Easy Integration:** Supports multiple integration methods, providing capabilities such as web embedding, pop-up embedding, and MCP invocation. It can be quickly embedded into applications such as n8n, Dify, MaxKB, and DataEase, allowing various applications to quickly acquire intelligent data collection capabilities.
- **Increasingly Accurate with Use:** Supports customizable prompts and terminology library configurations, maintainable SQL example calibration logic, and accurate matching of business scenarios. Efficient operation, based on continuous iteration and optimization using user interaction data, the data collection effect gradually improves with use, becoming more accurate with each use.

## Quick Start

mySQLBot supports two deployment modes: **Development** and **Production**.

---

### Development Environment

Frontend and backend run locally on the host, while Redis and PostgreSQL run in containers.

**1. Configure environment variables**

```bash
cp .env.example .env
```

> In development, the backend process reads runtime variables such as `POSTGRES_*`, `BASE_DIR`, and `UPLOAD_DIR` directly.
> The `SQLBOT_DEV_PG_*` variables are mainly used by `docker-compose.dev.yaml` and related setup scripts.
> The checked-in `.env.example` already aligns these values for the local host-app + containerized-DB workflow.

Key development settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `SQLBOT_DEV_PG_HOST` | `localhost` | Database host |
| `SQLBOT_DEV_PG_PORT` | `15432` | Database port (avoid conflicts) |
| `SQLBOT_DEV_PG_USER` | `sqlbot_user` | Database user |
| `POSTGRES_SERVER` | `localhost` | Actual database host read by the backend |
| `POSTGRES_PORT` | `15432` | Actual database port read by the backend |
| `POSTGRES_USER` | `sqlbot_user` | Actual database user read by the backend |
| `POSTGRES_PASSWORD` | `DevOnly@123456` | Actual database password read by the backend |
| `BASE_DIR` | `.` | Local runtime root |
| `UPLOAD_DIR` | `./data/sqlbot/dev/file` | Uploaded file directory |
| `MCP_IMAGE_PATH` | `./data/sqlbot/dev/images` | Image and embedding asset directory |
| `MCP_BIND_HOST` | `0.0.0.0` | MCP service bind address |
| `MCP_PORT` | `8001` | MCP service port |
| `MCP_PUBLIC_BASE_URL` | `http://localhost:8001` | Public MCP base URL for OpenClaw |
| `EXCEL_PATH` | `./data/sqlbot/dev/excel` | Excel import/export directory |
| `SQLBOT_CACHE_TYPE` | `memory` | Cache type |
| `SQLBOT_CACHE_REDIS_URL` | `redis://localhost:16379/0` | Redis URL |

**2. Start infrastructure (postgresql + redis)**

```bash
# Start postgresql + redis
docker compose -f docker-compose.dev.yaml -f docker-compose.dev.redis.yaml up -d

# Start postgresql only (no redis)
docker compose -f docker-compose.dev.yaml up -d
```

**3. Start frontend and backend**

Recommended one-command local startup:

```bash
bash dev-start.sh
```

This helper starts PostgreSQL, the main backend on `:8000`, the MCP development service on `:8001`, and the frontend build watcher together. If you prefer to launch components manually, use the commands below.

```bash
# Start backend (default :8000)
make backend-dev

# Start MCP development service (default :8001)
make backend-mcp-dev

# Start frontend build watch (browser entry stays on :8000)
make frontend-dev

# Optional internal Vite debug server (default :5173)
make frontend-vite-dev
```

Development access URL: `http://localhost:8000/#/login`

Development MCP endpoint: `http://localhost:8001/mcp`

Development MCP health check: `http://localhost:8001/health`

> Operational note: on the first backend startup, if the `admin` account still has the legacy seeded password, the system automatically syncs it to `DEFAULT_PWD`. If an administrator has already changed the password, the existing password is preserved.

> Operational note: on backend startup, if `sys_assistant` does not yet contain the default embedded assistant (`type=4, oid=1`), the system automatically creates one. Its default `domain` comes from `FRONTEND_HOST`, and later startups do not create duplicates.

**4. Stop development environment**

```bash
bash dev-stop.sh

# Or stop infrastructure only
docker compose -f docker-compose.dev.yaml down
```

---

### Production Environment

Uses prebuilt Docker images. All services run in containers.

The application container is named `mysqlbot-app`.

**1. Install**

Modify installation config:

```bash
cd installer
vim install.conf
```

Run installer:

```bash
bash install.sh
```

> Operational note: during the first startup after installation, if the `admin` account still uses the legacy seeded password, the system automatically syncs it to `DEFAULT_PWD`. If the password has already been changed, it is not overwritten.

> Operational note: during startup, if `sys_assistant` does not yet contain the default embedded assistant (`type=4, oid=1`), the system automatically creates one. Its default `domain` comes from `FRONTEND_HOST`, and later startups do not create duplicates.

**2. Management (via sctl)**

Production MCP startup is included in the normal container boot flow. After `sctl start` launches `mysqlbot-app`, the container entrypoint `start.sh` starts `main:mcp_app` on `:8001` before the main FastAPI app on `:8000`.

| Command | Description |
|---------|-------------|
| `sctl start` | Start services |
| `sctl stop` | Stop services |
| `sctl restart` | Restart services |
| `sctl reload` | Reload configuration |
| `sctl status` | Show status |

**3. Configuration**

After installation, config files are at `/opt/sqlbot/`:

- `/opt/sqlbot/.env` → Environment variables
- `/opt/sqlbot/conf/sqlbot.conf` → Runtime config

Modify and run `sctl reload` to apply.

**4. Upgrade**

Download new version and run:

```bash
cd new-installer-directory
bash install.sh
```

---

### Environment Comparison

| Aspect | Development | Production |
|--------|-------------|------------|
| Frontend | `make frontend-dev` writes `frontend/dist`, optionally `make frontend-vite-dev` for internal Vite debugging | Embedded in `mysqlbot-app` |
| Backend | Local `uv run uvicorn` (`make backend-dev`) + standalone MCP dev process (`make backend-mcp-dev`) | Container `start.sh` starts both main FastAPI and MCP |
| Database | Container (port 15432) | Container (port 5432) |
| Redis | Container (port 16379) | Container (port 6379) |
| Config | `.env` | `install.conf` → `/opt/sqlbot/.env` |
| Start | `make` + `docker compose` | `install.sh` + `sctl` |
| Data dir | `./data/sqlbot/dev/` | `./data/sqlbot/prod/` |

---

### Quality gates

- Local fast checks: `pre-commit run --all-files`
- Frontend CI checks: `npm --prefix frontend run lint:check`, `npm --prefix frontend run typecheck`, `npm --prefix frontend run build`
- Backend CI checks: see `.github/workflows/quality-check.yml` for mypy, Ruff, smoke tests, and pytest coverage


## UI Display

  <tr>
    <img width="1920" height="991" alt="image" src="https://github.com/user-attachments/assets/c9f5e1ff-f654-4375-96be-5511fe30c120" />


  </tr>


## License

This repository is licensed under the [LICENSE](../LICENSE), which is essentially GPLv3 but with some additional restrictions.

You may conduct secondary development based on the mySQLBot source code, but you must adhere to the following:

- You cannot replace or modify the mySQLBot logo and copyright information;

- Derivative works resulting from secondary development must comply with the open-source obligations of GPL v3.
