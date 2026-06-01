.PHONY: dev dev-backend dev-web install test lint typecheck e2e clean

install:
	pnpm install
	cd apps/backend && python3.11 -m venv .venv && .venv/bin/pip install -e ".[dev]"

dev-backend:
	cd apps/backend && .venv/bin/uvicorn openmarvis.main:app --reload --port 8001

dev-web:
	pnpm dev:web

dev:
	@trap 'kill 0' INT; \
	$(MAKE) dev-backend & \
	$(MAKE) dev-web & \
	wait

test:
	cd apps/backend && .venv/bin/pytest -v --cov=openmarvis --cov-report=term-missing

lint:
	cd apps/backend && .venv/bin/ruff check .
	pnpm lint:web

typecheck:
	cd apps/backend && .venv/bin/mypy openmarvis
	pnpm typecheck:web

e2e:
	pnpm e2e

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
	rm -rf apps/backend/.venv apps/web/.next node_modules
