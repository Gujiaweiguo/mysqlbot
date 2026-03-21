
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

### Installation and Deployment

Prepare a Linux server, install [Docker](https://docs.docker.com/get-docker/) and Docker Compose, and start the stack with Docker Compose.

The root `docker-compose.yaml` builds `gosqlbot-app` from the current repository source by default, which is intended for local installation and debugging.

#### Default mode: app + postgresql

```bash
cp .env.example .env
docker compose up -d
```

#### Optional mode: app + redis + postgresql

```bash
docker compose -f docker-compose.yaml -f docker-compose.redis.yaml up -d
```

> The installer-generated Compose files can still stay image-based for distribution, while the repository root Compose is oriented toward source-based local development.

Before starting the stack, copy `.env.example` to `.env` and replace the placeholder values for `SQLBOT_SECRET_KEY`, `SQLBOT_PG_PASSWORD`, and `SQLBOT_DEFAULT_PWD`. The checked-in files now use placeholders instead of committed live secrets.

The `gosqlbot-app` service exposes a health endpoint at `http://localhost:8000/health`, which is used by the container healthcheck to distinguish application readiness from PostgreSQL readiness.

#### Data directories

- `./data/sqlbot/excel` → Excel files
- `./data/sqlbot/file` → Uploaded files
- `./data/sqlbot/images` → Images and embedded assets
- `./data/sqlbot/logs` → Application logs
- `./data/postgresql` → PostgreSQL data
- `./data/redis` → Redis data (Redis mode only)

### Access methods

- Open in your browser: http://<your server IP>:8000/
- Username: admin
- Password: the value you set in `SQLBOT_DEFAULT_PWD`

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
