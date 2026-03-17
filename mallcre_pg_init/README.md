# mallcre PostgreSQL 初始化包

## 内容

- `mallcre_postgres.sql`：已转换好的 PostgreSQL 建表脚本
- `mallcre_seed.sql`：通用测试数据脚本
- `mallcre_seed_realistic.sql`：核心业务真实样例数据脚本
- `convert_mallcre_mysql_to_postgres.py`：MySQL -> PostgreSQL 转换脚本
- `mallcre.sql`：原始 MySQL 脚本
- `init_mallcre.sh`：一键导入示例脚本

## 使用方式

### 方式 1：直接导入已有 PostgreSQL SQL

```bash
createdb -U <user> mallcre
psql -U <user> -d mallcre -f mallcre_postgres.sql
psql -U <user> -d mallcre -f mallcre_seed.sql
psql -U <user> -d mallcre -f mallcre_seed_realistic.sql
```

### 方式 2：使用一键脚本

```bash
bash init_mallcre.sh <host> <port> <user> <database>
```

示例：

```bash
bash init_mallcre.sh localhost 5432 root mallcre
```

脚本会按顺序导入结构、通用测试数据，以及核心业务真实样例数据。密码请通过环境变量 `PGPASSWORD` 提供。
