# mySQLBot Embedding Provider Guide

## Goal

The embedding subsystem supports two execution modes:

- `local`: local HuggingFace embeddings with CPU-based torch runtime
- `remote`: OpenAI-compatible remote embeddings API

Recommended deployment strategy:

- **remote-default** for normal deployments
- **local-fallback** for offline or private deployments that need in-process embeddings

For backward compatibility, the application configuration still defaults to `EMBEDDING_PROVIDER=local`. Remote-first deployment means setting `EMBEDDING_PROVIDER=remote` explicitly in your environment or deployment manifest.

## Configuration

Core settings:

- `EMBEDDING_PROVIDER=local|remote`
- `DEFAULT_EMBEDDING_MODEL=<local model id>`
- `REMOTE_EMBEDDING_BASE_URL=<OpenAI-compatible API root, usually ending in /v1>`
- `REMOTE_EMBEDDING_API_KEY=<optional bearer token>`
- `REMOTE_EMBEDDING_MODEL=<remote embedding model id>`
- `REMOTE_EMBEDDING_TIMEOUT_SECONDS=<request timeout>`
- `EMBEDDING_STARTUP_BACKFILL_POLICY=eager|deferred|manual`

## Deployment Modes

### Remote-default

Use the default backend install:

```bash
uv sync
```

Recommended runtime configuration:

```env
EMBEDDING_PROVIDER=remote
REMOTE_EMBEDDING_BASE_URL=http://your-embedding-service/v1
REMOTE_EMBEDDING_API_KEY=...
REMOTE_EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_STARTUP_BACKFILL_POLICY=deferred
```

### Local-fallback

Install the local embedding runtime explicitly:

```bash
uv sync --extra cpu
```

Recommended runtime configuration:

```env
EMBEDDING_PROVIDER=local
DEFAULT_EMBEDDING_MODEL=shibing624/text2vec-base-chinese
EMBEDDING_STARTUP_BACKFILL_POLICY=eager
```

### Docker builds

Docker defaults to remote-friendly dependency installation.

To build an image that includes local embedding runtime:

```bash
docker build --build-arg SQLBOT_EMBEDDING_RUNTIME=local -t sqlbot-local .
```

## Startup Backfill Policy

- `eager`: startup triggers terminology, data-training, and table/datasource embedding backfill
- `deferred`: in remote mode, startup skips embedding backfill, but normal query/write paths still use the configured provider
- `manual`: in remote mode, startup skips embedding backfill and operators are expected to run a re-embedding workflow explicitly

In remote mode, `deferred` is the safest default because it avoids large startup bursts against an external embedding API. Local mode currently preserves eager startup backfill behavior unless you change the implementation further.

## Re-embedding Workflow After Provider or Model Changes

Changing embedding provider or embedding model should be treated as a full reindex event.

Recommended operator workflow:

1. Update provider/model configuration
2. Clear persisted embeddings so they are rebuilt consistently
3. Trigger backfill through startup (`eager`) or a controlled maintenance run
4. Validate terminology, data-training, and datasource/table retrieval quality
5. Review similarity thresholds after reindexing

Example SQL reset:

```sql
UPDATE terminology SET embedding = NULL;
UPDATE data_training SET embedding = NULL;
UPDATE core_table SET embedding = NULL;
UPDATE core_datasource SET embedding = NULL;
```

## Threshold Review

After switching provider or model, review:

- `EMBEDDING_TERMINOLOGY_SIMILARITY`
- `EMBEDDING_DATA_TRAINING_SIMILARITY`
- `TABLE_EMBEDDING_COUNT`
- `DS_EMBEDDING_COUNT`

Different embedding models can change similarity distributions even when storage format remains the same.

## Rollback Strategy

If remote mode degrades quality or reliability:

1. switch `EMBEDDING_PROVIDER` back to `local`
2. install local runtime (`uv sync --extra cpu`)
3. reset persisted embeddings
4. re-run local re-embedding
