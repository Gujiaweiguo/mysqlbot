
<h3 align="center">基于大模型和 RAG 的智能问数系统</h3>

</p>

<p align="center">
  <a href="README.md"><img alt="中文(简体)" src="https://img.shields.io/badge/中文(简体)-d9d9d9"></a>
  <a href="/docs/README.en.md"><img alt="English" src="https://img.shields.io/badge/English-d9d9d9"></a>
</p>
<hr/>

mySQLBot 是一款基于大语言模型和 RAG 的智能问数系统，由 DataEase 开源项目组匠心出品。借助 mySQLBot，用户可以实现对话式数据分析（ChatBI），快速提炼获取所需的数据信息及可视化图表，并且支持进一步开展智能分析。

## 工作原理

<img width="1153" height="563" alt="image" src="https://github.com/user-attachments/assets/8bc40db1-2602-4b68-9802-b9be36281967" />

## 核心优势

- **开箱即用**：仅需简单配置大模型与数据源，无需复杂开发，即可快速开启智能问数；依托大模型自然语言理解与 SQL 生成能力，结合 RAG 技术，实现高质量 Text-to-SQL 转换。
- **安全可控**：提供工作空间级资源隔离机制，构建清晰数据边界，保障数据访问安全；支持细粒度数据权限配置，强化权限管控能力，确保使用过程合规可控。
- **易于集成**：支持多种集成方式，提供 Web 嵌入、弹窗嵌入、MCP 调用等能力；能够快速嵌入到 n8n、Dify、MaxKB、DataEase 等应用，让各类应用快速拥有智能问数能力。
- **越问越准**：支持自定义提示词、术语库配置，可维护 SQL 示例校准逻辑，精准匹配业务场景；高效运营，基于用户交互数据持续迭代优化，问数效果随使用逐步提升，越问越准。

## 快速开始

### 开发命令入口

仓库根目录现在提供统一的开发命令入口，推荐优先使用：

```bash
make install
make backend-dev
make frontend-dev
make lint
make test
```

其中 `Makefile` 负责把命令分发到 `backend/` 和 `frontend/` 内部的实际脚本；如果你需要看底层命令，再进入对应子目录即可。

### 部署模式

项目支持两套部署模式：**开发环境** 和 **生产环境**。

---

#### 开发环境

前端和后端在宿主机本地运行，Redis 和 PostgreSQL 以容器方式运行。

```
前端(:5173) → 后端(:8000) → postgresql 容器(:15432)
                          → redis 容器(:16379)
```

**1. 配置环境变量**

```bash
cp .env.example .env
# 修改 .env 中的数据库和 Redis 连接配置
```

开发环境关键配置：

| 变量 | 开发环境默认值 | 说明 |
|-----|---------|------|
| `SQLBOT_DEV_PG_HOST` | `localhost` | 数据库地址 |
| `SQLBOT_DEV_PG_PORT` | `15432` | 数据库端口（避免冲突） |
| `SQLBOT_DEV_PG_USER` | `sqlbot_user` | 数据库用户名 |
| `SQLBOT_DEV_PG_PASSWORD` | `DevOnly@123456` | 数据库密码 |
| `SQLBOT_CACHE_TYPE` | `memory` | 缓存类型 |
| `SQLBOT_CACHE_REDIS_URL` | `redis://localhost:16379/0` | Redis URL |

**2. 启动基础设施（postgresql + redis）**

```bash
# 启动 postgresql + redis
docker compose -f docker-compose.dev.yaml -f docker-compose.dev.redis.yaml up -d

# 仅启动 postgresql（不用 redis）
docker compose -f docker-compose.dev.yaml up -d

# 查看状态
docker compose -f docker-compose.dev.yaml ps
```

**3. 启动前后端**

```bash
# 启动后端（默认 :8000）
make backend-dev

# 启动前端（默认 :5173）
make frontend-dev
```

> 运维说明：后端首次启动后，如果 `admin` 账号仍然是历史种子密码，系统会自动将其同步为 `DEFAULT_PWD`；如果管理员已经手工修改过密码，则不会被覆盖。

**4. 停止开发环境**

```bash
# 停止基础设施
docker compose -f docker-compose.dev.yaml down

# 停止前后端：在对应终端 Ctrl+C
```

**5. 开发环境数据目录**

- `./data/sqlbot/dev/postgresql` → PostgreSQL 数据
- `./data/sqlbot/dev/redis` → Redis 数据

---

#### 生产环境

使用预构建镜像安装运行，所有服务以容器方式运行。

```
浏览器 → gosqlbot-app(:8000/:8001)
        ├── main FastAPI :8000
        ├── MCP FastAPI :8001
        └── g2-ssr :3000
        ├── postgresql 容器
        └── redis 容器
```

**1. 安装**

准备一台 Linux 服务器，安装好 [Docker](https://docs.docker.com/get-docker/) 与 Docker Compose。

修改安装配置：

```bash
cd installer
# 修改 install.conf，填写数据库密码、端口等配置
vim install.conf
```

执行安装：

```bash
bash install.sh
```

> 运维说明：安装后的首次启动过程中，如果 `admin` 账号仍然保留历史种子密码，系统会自动将其同步为 `DEFAULT_PWD`；如果该密码已经被修改过，则不会覆盖现有密码。

**2. 运行管理（通过 sctl）**

| 命令 | 说明 |
|------|------|
| `sctl start` | 启动服务 |
| `sctl stop` | 停止服务 |
| `sctl restart` | 重启服务 |
| `sctl reload` | 重载配置 |
| `sctl status` | 查看状态 |
| `sctl version` | 查看版本 |

**3. 配置修改**

安装后配置文件位于 `/opt/sqlbot/`：

- `/opt/sqlbot/.env` → 环境变量
- `/opt/sqlbot/conf/sqlbot.conf` → 运行配置
- `/opt/sqlbot/docker-compose.yml` → 服务编排

修改后执行 `sctl reload` 生效。

**4. 升级**

下载新版本安装包，执行：

```bash
cd 新版本installer目录
bash install.sh
```

脚本会自动识别为升级模式。

**5. 卸载**

```bash
bash uninstall.sh
```

**6. 生产环境端口**

| 服务 | 端口 | 用途 |
|------|------|------|
| gosqlbot-app | 8000 | Web UI + API |
| gosqlbot-app | 8001 | MCP 服务 |
| postgresql | 5432 | 数据库 |
| redis | 6379 | 缓存 |

**7. 生产环境数据目录**

- `./data/sqlbot/prod/excel` → Excel 文件
- `./data/sqlbot/prod/file` → 上传文件
- `./data/sqlbot/prod/images` → 图片与嵌入资源
- `./data/sqlbot/prod/logs` → 应用日志
- `./data/sqlbot/prod/postgresql` → PostgreSQL 数据
- `./data/sqlbot/prod/redis` → Redis 数据

---

#### 两套环境对比

| 对比项 | 开发环境 | 生产环境 |
|-------|---------|---------|
| 前端 | 本地 `npm run dev` | 内嵌到 app 容器 |
| 后端 | 本地 `uv run uvicorn` | 容器运行 |
| 数据库 | 容器（端口 15432） | 容器（端口 5432） |
| Redis | 容器（端口 16379） | 容器（端口 6379） |
| 配置文件 | `.env` | `install.conf` → `/opt/sqlbot/.env` |
| 启动方式 | `make` + `docker compose` | `install.sh` + `sctl` |
| 数据目录 | `./data/sqlbot/dev/` | `./data/sqlbot/prod/` |
| 镜像来源 | 本地构建 | 预构建镜像 |

## 质量与发布门禁

- 代码质量门禁：`.github/workflows/quality-check.yml`
- 本地快速门禁：`pre-commit run --all-files`（包含文件卫生检查、backend Ruff、frontend ESLint check）
- 运行时与回归门禁：`.github/workflows/integration-test.yml`
- Embedding provider 说明：`docs/embedding-provider.md`
- 拼写门禁说明：`docs/typos-gate.md`
- 仓库同步门禁说明：`docs/repo-sync-gate.md`
- 发布门禁说明：`docs/regression/release-gates.md`
- Required checks 落地清单：`docs/regression/required-checks-rollout.md`
- 全量回归执行手册：`docs/regression/full-regression-playbook.md`

### 联系我们

如你有更多问题，可以与我们交流。

## UI 展示

<tr>
    <img alt="q&a" src="https://github.com/user-attachments/assets/55526514-52f3-4cfe-98ec-08a986259280"   />
  </tr>

## License

本仓库遵循开源协议，该许可证本质上是 GPLv3，但有一些额外的限制。

你可以基于 mySQLBot 的源代码进行二次开发，但是需要遵守以下规定：

- 不能替换和修改 mySQLBot 的 Logo 和版权信息；
- 二次开发后的衍生作品必须遵守 GPL V3 的开源义务。
