
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

### 安装部署

准备一台 Linux 服务器，安装好 [Docker](https://docs.docker.com/get-docker/) 与 Docker Compose，推荐使用 Docker Compose 启动。

根目录 `docker-compose.yaml` 默认会基于当前仓库源码构建 `gosqlbot-app`，适合本地安装与调试。

#### 默认模式：app + postgresql

```bash
docker compose up -d
```

#### 可选模式：app + redis + postgresql

```bash
docker compose -f docker-compose.yaml -f docker-compose.redis.yaml up -d
```

> 如果你使用安装器产物中的 Compose 文件，则默认继续走预构建镜像模式；仓库根目录 Compose 更偏向源码构建与开发调试。

#### 服务端口

| 服务 | 皴露端口 | 用途 |
|------|---------|------|
| gosqlbot-app | 8000 | FastAPI 应用 (Web UI) |
| gosqlbot-app | 8001 | MCP 服务 |
| postgresql | 5432 | PostgreSQL 数据库 |
| redis | 6379 | Redis 缓存（可选） |

#### 数据目录

- `./data/sqlbot/excel` → Excel 文件
- `./data/sqlbot/file` → 上传文件
- `./data/sqlbot/images` → 图片与嵌入资源
- `./data/sqlbot/logs` → 应用日志
- `./data/postgresql` → PostgreSQL 数据
- `./data/redis` → Redis 数据（仅 Redis 模式)

#### 配置环境变量

常用环境变量（可通过 `.env` 或 `docker-compose.yaml` 默认值）：

| 变量 | 默认值 | 说明 |
|-----|---------|------|
| `SQLBOT_PG_DB` | `sqlbot` | PostgreSQL 数据库名 |
| `SQLBOT_PG_USER` | `root` | PostgreSQL 用户名 |
| `SQLBOT_PG_PASSWORD` | `Password123@pg` | PostgreSQL 密码 |
| `SQLBOT_PG_PORT` | `5432` | PostgreSQL 端口 |
| `SQLBOT_CACHE_TYPE` | `memory` | 缓存类型 (`memory` 或 `redis`) |
| `SQLBOT_CACHE_REDIS_URL` | `redis://redis:6379/0` | Redis URL（仅 Redis 模式) |
| `SQLBOT_DATA_DIR` | `./data/sqlbot` | 应用数据目录 |
| `SQLBOT_PG_DATA_DIR` | `./data/postgresql` | PostgreSQL 数据目录 |
| `SQLBOT_REDIS_DATA_DIR` | `./data/redis` | Redis 数据目录（仅 Redis 模式) |

#### 回滚策略

如需回退到旧的捆绑部署模式：
- 使用安装器提供的预构建镜像和 Compose 文件
- 保持 `./data/postgresql` 数据目录不变

#### 迁移现有数据

如需从旧的捆绑部署迁移到新的分离部署模式

1. 停止现有容器：`docker compose down`
2. 备份 PostgreSQL 数据目录： `cp -r ./data/postgresql ./data/postgresql-backup`
3. 使用新的 Compose 配置启动：
```bash
docker compose up -d
```
4. 数据将自动保留在 `./data/postgresql` 目录中

## 质量与发布门禁

- 代码质量门禁：`.github/workflows/quality-check.yml`
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
