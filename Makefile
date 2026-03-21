backend-install:
	cd backend && uv sync

frontend-install:
	cd frontend && npm install

install: backend-install frontend-install

backend-dev:
	cd backend && uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

frontend-dev:
	cd frontend && npm run dev

backend-lint:
	cd backend && LINT_SCOPE=full bash scripts/lint.sh

frontend-lint:
	cd frontend && npm run lint:check

lint: backend-lint frontend-lint

backend-test:
	cd backend && uv run pytest

frontend-test:
	cd frontend && npm run typecheck && npm run build

test: backend-test frontend-test
