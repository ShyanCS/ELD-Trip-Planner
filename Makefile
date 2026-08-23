.PHONY: install test lint lock clean

# ── Backend ────────────────────────────────────────────────────────────────────
backend-install:
	cd backend && pip install -r requirements.txt

backend-test:
	cd backend && python -m coverage run --source=trip manage.py test trip.tests
	cd backend && python -m coverage report --fail-under=70

backend-lint:
	cd backend && ruff check .

# Regenerate the pinned lockfile from requirements.in (single source of truth).
lock:
	cd backend && pip install pip-tools && pip-compile requirements.in --output-file requirements.txt --no-header

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
