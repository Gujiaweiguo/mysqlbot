# FastAPI Project - Backend

## Development

### Setup
```bash
uv sync
```

### Run Development Server
```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

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