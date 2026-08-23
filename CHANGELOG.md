# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-08-23

### Added
- Typed API error schema: `trip/exceptions.py` defines a `TripPlanError` hierarchy
  (`GEOCODE_FAILED`, `ROUTE_FAILED`, `HOS_FAILED`, `UPSTREAM_UNAVAILABLE`,
  `VALIDATION_FAILED`, `INTERNAL_ERROR`) and `POST /api/trip/plan/` now returns
  `{error: {code, message, details}}` for every failure mode
- Upstream OpenRouteService outages surface as `503 UPSTREAM_UNAVAILABLE`
  instead of an opaque 500
- Fully offline test runs: `OfflineTestRunner` blocks all non-loopback
  sockets/DNS during the suite; unmocked outbound calls fail loudly
  (`trip/tests/test_offline_guard.py` pins the behavior)
- Frontend production build gate (`npm run build`) and coverage artifact
  upload in CI; frontend dependency audit job (`npm audit --omit=dev --audit-level=high`)
- Prettier enforcement: devDependency, `format` / `format:check` scripts,
  `.prettierignore`, and a CI formatting gate in the frontend-lint job
- PropTypes contracts on all prop-taking components (TripForm, ErrorBanner,
  LoadingSpinner, MapView, TripSummary, TripTimeline, LogSheet)
- `logSheetDraw.js`: canvas drawing layer extracted from LogSheet.jsx, with
  unit tests for `parseTime` and `buildSegments`
- `trip/hos_helpers.py`: pure HOS primitives (event construction, day totals,
  24-hour invariant assertion) extracted from hos_calculator.py
- Deploy pipeline: GHCR Docker image publishing for backend + frontend on
  pushes to main and semver tags (built-in GITHUB_TOKEN, no external secrets)
- Production frontend image: multi-stage `frontend/Dockerfile` (nginx SPA
  serving with `/api` proxy) plus nginx config
- Devcontainer (`.devcontainer/devcontainer.json`) for one-command onboarding
- PEP 621 `[project]` metadata in `backend/pyproject.toml` (dynamic deps from
  requirements.txt); explicit `LOCATION_PATTERN` / `VALIDATION_PATTERNS` in
  serializers.py with injection-rejection tests

### Changed
- **BREAKING**: backend lockfile renamed `requirements.lock` → `requirements.txt`
  (standard pip manifest name); install with `pip install -r requirements.txt`
- **BREAKING**: API error responses moved from `{"error": "<string>"}` to the
  typed schema above; frontend `App.jsx` consumes the new shape
- axios bumped to ^1.19.0 clearing 7 high-severity advisories; dompurify
  moderates cleared via lockfile refresh
- TripForm mirrors the backend location pattern client-side for instant
  feedback on invalid characters
- README documents the error schema, offline testing guarantee, and updated
  project structure/test inventory

### Verified
- Fresh-clone proof: `git clone` → pip install from requirements.txt →
  migrate → 132 backend tests OK; npm ci → lint → format check → 72 frontend
  tests OK, with no manual steps beyond the documented quickstart

## [1.0.0] - 2026-08-21

### Added
- Full-stack ELD Trip Planner: Django REST API backend + React frontend
- HOS (Hours of Service) Calculator enforcing FMCSA 70-hour/8-day rules
  - 11-hour driving limit, 14-hour window, 30-minute break rule
  - Fuel stops every 1,000 miles, 34-hour restart for cycle reset
- Geocoding and route planning via OpenRouteService API
- FMCSA-compliant daily log sheets rendered on HTML5 Canvas
- Interactive Leaflet map with route polyline and stop markers
- PDF export of daily log sheets
- Trip summary stats (distance, duration, days, stops)
- Input validation in both the React frontend and Django serializers
- `GET /api/health/` liveness probe endpoint
- Structured logging via Python `logging.config.dictConfig`
- GitHub Actions CI pipeline (backend tests, ruff lint, frontend tests, ESLint)
- Dependabot configuration for pip, npm, and GitHub Actions
- Root `.gitignore` (Python, Django, Node, env files)
- Pinned exact dependency versions for reproducible installs
- `pyproject.toml` with ruff linter/formatter configuration
