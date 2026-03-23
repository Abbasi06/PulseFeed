# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# PulseBoard

## What this is
A personalized AI-powered knowledge feed. Users enter their occupation, interests, and hobbies. The app fetches the latest news, articles, research, and upcoming events related to their profile and shows it in a clean dashboard. Refreshes every 6 hours per user.

## Tech stack
- Backend: Python 3.10+, FastAPI, SQLAlchemy, SQLite, APScheduler
- Frontend: React, Vite, TailwindCSS v4, React Router (Node 18+)
- AI: Google Gemini API via `google-genai` SDK (model: `gemini-2.0-flash`) with DuckDuckGo search
- Package manager: `uv` for Python, `npm` for Node

## Environment setup
1. Copy `.env` and set `GEMINI_API_KEY`
2. Backend: `cd backend && uv sync`
3. Frontend: `cd frontend && npm install`

## Commands

### Run
```
cd backend && uv run uvicorn main:app --reload --port 8000
cd frontend && npm run dev
```

### Lint & type-check (run before every commit)
```
cd backend && uv run ruff check . && uv run mypy .
cd frontend && npm run lint
cd frontend && npx prettier --write src/
```

### Test
```
cd backend && uv run pytest tests/ -v                           # all backend tests
cd backend && uv run pytest tests/test_routes.py::test_name -v  # single test
cd frontend && npm run test
```

## Architecture

### Data flow
1. User submits profile (name, occupation, interests, hobbies) via `POST /users`
2. APScheduler triggers feed refresh every 6 hours per user
3. `research_agent.py` calls Gemini with DuckDuckGo search → returns news items
4. `events_agent.py` calls Gemini with DuckDuckGo search → returns events
5. Results are validated, capped (20 news / 10 events), and stored in SQLite
6. Frontend polls `GET /feed/{user_id}` and `GET /events/{user_id}` to render the dashboard

### Backend modules
- `main.py` — FastAPI app, CORS config, router registration
- `database.py` — SQLAlchemy engine + session factory; uses `pulseboard.db` (in-memory SQLite for tests)
- `models.py` — ORM models: `User`, `NewsItem`, `Event`
- `routes/users.py` — CRUD for user profiles; all validation via Pydantic
- `routes/feed.py` — returns cached news items; triggers agent if cache is stale
- `routes/events.py` — same pattern as feed but for events
- `agents/research_agent.py` — Gemini call + DuckDuckGo → news items with required fields
- `agents/events_agent.py` — Gemini call + DuckDuckGo → events with required fields
- `scheduler.py` — APScheduler job that calls both agents for each user

### Frontend pages
- `Onboarding.jsx` — profile creation form (first-time users)
- `Dashboard.jsx` — main feed: `NewsCard` + `EventCard` grids, refresh indicator
- `Settings.jsx` — edit existing profile

### Key config file
`frontend/src/config.js` exports `API_URL = "http://localhost:8000"`. All `fetch` calls import from here — no hardcoded URLs elsewhere.

## Validation rules

### Backend (Pydantic)
- `name`: required, non-empty, max 100 chars
- `occupation`: required, non-empty, max 150 chars
- `interests`: required, 1–10 items, each max 50 chars, no duplicates
- `hobbies`: optional, max 10 items, each max 50 chars, no duplicates
- Strip leading/trailing whitespace on all string fields before saving
- Return HTTP 422 with a clear message for any failure

### Frontend
- Show inline errors for empty name, occupation, or zero interests on submit
- Tags: trim whitespace, silently skip empty/duplicate (case-insensitive)/over-50-char tags
- Show character count hints on name and occupation fields
- Disable submit while API call is in progress
- Show a friendly error banner on API failure — never expose raw error objects

### Agent output validation
- Validate all required keys after each agent call; apply safe defaults for missing fields:
  `title → "Untitled"`, `summary → ""`, `source → "Unknown"`, `url → "#"`, `topic → "General"`, `published_date → today`
- Discard items where both `title` and `summary` are empty
- Discard events missing `name` or `date`
- Log a warning (not an error) when discarding or defaulting; cap at 20 news / 10 events per refresh

## Code conventions
- Python: snake_case, type hints on **all** parameters and return types, no function > 40 lines, no bare `except`
- React: functional components only, camelCase, no `console.log` in committed code
- All Python commands run via `uv run` — never activate the venv manually
- Tests: in-memory SQLite for backend tests; mock the Gemini client — no real API calls in tests
- `pyproject.toml` dev dependencies must include: `ruff`, `mypy`, `pytest`, `pytest-asyncio`, `httpx`
- `package.json` devDependencies must include: `@testing-library/react`, `@testing-library/jest-dom`, `vitest`

## Pre-commit checklist
Fix all failures before marking any feature complete:
```
cd backend && uv run ruff check . && uv run mypy . && uv run pytest tests/ -v
cd frontend && npm run lint && npx prettier --write src/ && npm run test
```
