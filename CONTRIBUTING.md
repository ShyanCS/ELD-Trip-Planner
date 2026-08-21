# Contributing to ELD Trip Planner

Thank you for your interest in contributing! This guide covers everything you need to get set up and start contributing.

## Table of Contents

- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Code Style](#code-style)
- [Commit Conventions](#commit-conventions)
- [Pull Request Process](#pull-request-process)

---

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- An [OpenRouteService API key](https://openrouteservice.org/) (free tier available)

### Backend Setup

```bash
# 1. Clone the repository
git clone https://github.com/ShyanCS/ELD-Trip-Planner.git
cd ELD-Trip-Planner

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate

# 3. Install backend dependencies (exact versions pinned)
cd backend
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit backend/.env and fill in SECRET_KEY and ORS_API_KEY

# 5. Run the development server
python manage.py runserver
```

The backend API will be available at `http://localhost:8000`.

### Frontend Setup

```bash
# From the repo root
cd frontend

# 1. Install dependencies
npm install

# 2. Configure environment variables
cp .env.example .env
# Edit frontend/.env and set VITE_API_URL=http://localhost:8000/api

# 3. Start the dev server
npm run dev
```

The frontend will be available at `http://localhost:5173`.

---

## Running Tests

### Backend Tests

```bash
cd backend
python manage.py test --verbosity=2
```

All tests live under `backend/trip/tests/`. The test suite covers the HOS calculator, geocoder, serializers, and views.

### Frontend Tests

```bash
cd frontend
npm test
```

Frontend tests use [Vitest](https://vitest.dev/) and [@testing-library/react](https://testing-library.com/docs/react-testing-library/intro). Tests live in `frontend/src/components/__tests__/`.

### Linting

```bash
# Backend (requires ruff: pip install ruff)
cd backend
ruff check .

# Frontend
cd frontend
npm run lint
```

---

## Code Style

### Python (Backend)

- Style is enforced by **ruff** (config in `backend/pyproject.toml`)
- Line length: 100 characters
- Import ordering: `ruff` handles this automatically
- Run `ruff check .` before committing; CI will fail otherwise

### JavaScript (Frontend)

- Style is enforced by **ESLint** (config in `frontend/eslint.config.js`)
- Run `npm run lint` before committing; CI will fail otherwise

---

## Commit Conventions

Follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>: <short description>

[optional body]
```

Types:
- `feat:` — new feature
- `fix:` — bug fix
- `test:` — adding or updating tests
- `refactor:` — code restructuring without behavior change
- `docs:` — documentation only
- `chore:` — tooling, config, dependencies
- `ci:` — CI pipeline changes

**Rules:**
- Keep each commit focused: one feature or fix per commit
- Include tests in the same commit as the feature they pin
- Keep commits under ~150 lines of diff where possible
- Avoid mixing formatting/refactoring with feature changes

**Examples:**

```
feat: add trip timeline component with hourly event markers
test: add TripTimeline unit tests for status bar rendering
fix: handle empty geocode response in geocoder.py
chore: pin exact versions in backend/requirements.txt
```

---

## Pull Request Process

1. Fork the repository and create a branch: `git checkout -b feat/your-feature`
2. Make your changes in small, focused commits (see above)
3. Ensure all tests pass locally: `python manage.py test` and `npm test`
4. Ensure linters pass: `ruff check .` and `npm run lint`
5. Open a Pull Request against `main` with a clear description of what you changed and why
6. CI will run automatically — all checks must pass before merging

---

## Project Structure

```
ELD-Trip-Planner/
├── backend/                # Django REST API
│   ├── config/             # Django settings, urls, wsgi
│   ├── trip/               # Main app: views, serializers, geocoder, HOS calculator
│   │   └── tests/          # Backend test suite
│   ├── requirements.txt    # Pinned Python dependencies
│   └── pyproject.toml      # Ruff lint/format config
├── frontend/               # React app (Vite)
│   ├── src/
│   │   ├── api/            # API client + mock data
│   │   ├── components/     # UI components + __tests__/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vitest.config.js
└── .github/
    ├── workflows/ci.yml    # GitHub Actions CI
    └── dependabot.yml
```
