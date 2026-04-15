backend-install:
	cd backend && uv sync

frontend-install:
	cd frontend && npm install

install: backend-install frontend-install

setup-mallbi-demo:
	cd backend && uv run python scripts/setup_mallbi_demo.py $(SETUP_MALLBI_DEMO_ARGS)

setup-gs-scrm-demo:
	cd backend && uv run python scripts/setup_gs_scrm_demo.py $(SETUP_GS_SCRM_DEMO_ARGS)

backend-dev:
	cd backend && uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

frontend-dev:
	cd frontend && npm run dev

frontend-vite-dev:
	cd frontend && npm run dev:internal

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
