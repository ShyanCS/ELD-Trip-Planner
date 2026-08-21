# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
