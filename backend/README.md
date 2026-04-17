# FastAPI Project - Backend

## Development

Canonical root-level equivalents:

```bash
make install
make backend-dev
make backend-mcp-dev
make lint
make test
```

The commands below are the backend-specific implementations used under those root entrypoints.

### Setup
```bash
uv sync
```

### Setup with local embedding runtime
```bash
uv sync --extra cpu
```

### Run Development Server
```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Run Development MCP Server
```bash
uv run uvicorn main:mcp_app --host ${MCP_BIND_HOST:-0.0.0.0} --port ${MCP_PORT:-8001} --reload
```

Canonical MCP URLs:

- Endpoint: `http://localhost:8001/mcp`
- Health: `http://localhost:8001/health`

### Linting
```bash
bash scripts/lint.sh
```

### Testing
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=apps --cov=common --cov-report=term-missing

# Run specific test file
uv run pytest tests/common/utils/test_utils.py

# Run specific test
uv run pytest tests/common/utils/test_utils.py::TestTimeUtils::test_get_timestamp_returns_int
```

### Format
```bash
bash scripts/format.sh
```
