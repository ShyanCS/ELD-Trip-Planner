.PHONY: install test lint clean backend-install backend-test backend-lint frontend-install frontend-test frontend-lint

# ── Backend ────────────────────────────────────────────────────────────────────
backend-install:
	cd backend && pip install -r requirements.lock

backend-test:
	cd backend && python -m coverage run --source=trip manage.py test trip.tests
	cd backend && python -m coverage report --fail-under=70

backend-lint:
	cd backend && ruff check .

# ── Frontend ───────────────────────────────────────────────────────────────────
frontend-install:
	cd frontend && npm ci

frontend-test:
	cd frontend && npm test -- --run

frontend-lint:
	cd frontend && npm run lint

# ── Combined ───────────────────────────────────────────────────────────────────
install: backend-install frontend-install

test: backend-test frontend-test

lint: backend-lint frontend-lint

clean:
	cd backend && find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	cd frontend && rm -rf node_modules/.cache coverage dist
