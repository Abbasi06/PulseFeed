# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# PulseBoard

## What this is
A personalized AI-powered knowledge feed. Users enter their occupation, interests, and hobbies. The app fetches the latest news, articles, research, and upcoming events related to their profile and shows it in a clean dashboard. Feed is cached and refreshed on-demand with a 6-hour TTL.

## Tech stack
- Backend: Python 3.13, FastAPI, SQLAlchemy, SQLite, JWT auth (httpOnly cookies)
- Frontend: React 19, Vite, TailwindCSS v4, React Router v7, Framer Motion
- AI: Google Gemini API via `google-genai` SDK (model: `gemini-2.5-flash-lite`) with DuckDuckGo search (`ddgs`)
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
cd backend && uv run pytest tests/ -v                                        # all backend tests
cd backend && uv run pytest tests/test_users.py::test_create_user_success -v # single test
cd frontend && npm run test       # run once
cd frontend && npm run test:watch # watch mode
```

## Architecture

### Data flow
1. User submits profile (name, occupation, interests, hobbies) via `POST /users` → JWT cookie set
2. `GET /feed/{user_id}` and `GET /events/{user_id}` check cache: if `fetched_at` is older than 6 hours (or missing), agents are triggered automatically
3. `research_agent.py` builds programmatic DuckDuckGo queries (no LLM for query generation), sends top results to Gemini for summarization/extraction → returns both news items and events
4. Results are validated, capped (20 news / 10 events), old items deleted, new ones stored in SQLite
5. Frontend fetches `GET /feed/{user_id}` and `GET /events/{user_id}` to render the dashboard; force refresh via `POST /feed/{user_id}/refresh`

### Backend modules
- `main.py` — FastAPI app, CORS config (`http://localhost:5173`), router registration, lifespan startup (table creation + raw SQL column migrations)
- `database.py` — SQLAlchemy engine + session factory (`pulseboard.db`); switch to in-memory SQLite for tests
- `models.py` — ORM models: `User`, `FeedItem`, `Event` (User has cascade-delete relationships to both)
- `schemas.py` — Pydantic models for request/response; `UserCreate` validators handle whitespace stripping and tag deduplication
- `auth.py` — JWT creation/validation; tokens stored as httpOnly cookies (30-day expiry, `secure=False` in dev — must change for production); `SECRET_KEY` defaults to `"dev-secret-change-before-production"`
- `routes/users.py` — CRUD for user profiles + login/logout; `POST /users` creates user and sets cookie; `GET /users/me` validates cookie
- `routes/feed.py` — returns cached feed items; auto-triggers `generate_feed()` if stale; `PATCH /feed/items/{id}/like` toggles like
- `routes/events.py` — same pattern as feed but for events
- `agents/research_agent.py` — **single file handles both feed and events**; `generate_feed()` and `generate_events()` are the two entry points; DuckDuckGo searches run in parallel via `asyncio.gather()`; Gemini calls wrapped in thread-pool executor to avoid blocking; enforces `response_mime_type="application/json"`

### Frontend structure
- `context/AuthContext.jsx` — on mount calls `GET /users/me` to validate httpOnly cookie; provides `user`, `isAuthenticated`, `login()`, `logout()`; all fetches use `credentials: 'include'`
- `pages/Onboarding.jsx` — profile creation form
- `pages/Dashboard.jsx` — two tabs (Feed, Saved); floating hover panels on left (Today's Brief) and right (Events); like toggle; refresh triggers both feed and events in parallel
- `pages/Settings.jsx` — pre-populated edit form; success banner on save
- `components/DashboardLayout.jsx` — sidebar (desktop) + top bar (mobile) with nav; wraps protected routes via `<Outlet />`
- `components/TagInput.jsx` — reusable tag input used for interests and hobbies in both Onboarding and Settings
- `components/NewsCard.jsx` / `EventCard.jsx` — topic/type color badges; image fallback to `picsum.photos` seeded by title hash
- `components/BrainLoader.jsx` — animated brain SVG shown during feed/event generation
- `components/SkeletonCard.jsx` — pulse placeholder during initial load

### Key config
`frontend/src/config.js` exports `API_URL = "http://localhost:8000"`. All `fetch` calls import from here — no hardcoded URLs elsewhere.

## Validation rules

### Backend (Pydantic — `schemas.py`)
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
- If no DuckDuckGo results found, feed returns a single placeholder item; events returns empty array

### Tests
- `backend/tests/conftest.py` — `db` fixture (in-memory SQLite with `StaticPool`) + `client` fixture (FastAPI `TestClient` with `get_db` overridden); `StaticPool` is required so all connections share the same in-memory DB
- `backend/tests/test_auth.py` — JWT token creation/decoding/validation
- `backend/tests/test_users.py` — user CRUD, auth cookie, validation rules
- `backend/tests/test_feed.py` / `test_events.py` — cache TTL logic, forced refresh, like toggle, 403/404 paths; `generate_feed` / `generate_events` are mocked with `AsyncMock` — no real API calls
- `backend/tests/test_agents.py` — pure unit tests for `_validate_feed_items`, `_validate_events`, `_build_*_queries`, `search_web`; all Gemini/DuckDuckGo calls mocked
- **404 vs 403 note:** feed/events/user-update routes check `user_id != current_user_id` (→ 403) *before* the DB lookup (→ 404). Tests that assert 404 must forge a JWT for the non-existent `user_id` via `create_access_token(99999)`.
- Frontend tests live in `src/components/__tests__/`; vitest + `@testing-library/react`; `<img alt="">` has ARIA role `"presentation"`, not `"img"` — use `screen.getByRole('presentation')` for image assertions

## Claude Code configuration (`.claude/`)

### Agents
Specialized subagents available via the Agent tool:
- `frontend-developer` — React/Vite/TailwindCSS component work
- `ui-ux-designer` — UI/UX design decisions and layout
- `backend-architect` — FastAPI, SQLAlchemy, API design
- `code-reviewer` — code quality and review
- `debugger` — root-cause analysis and bug fixing
- `context-manager` — managing large context and summarisation
- `mcp-expert` — MCP server configuration

### Skills
Invocable via the Skill tool (`/skill-name`):
- `ui-ux-pro-max` — advanced UI/UX with design data (colors, typography, icons, React patterns)
- `ui-design-system` — design token generation (`scripts/design_token_generator.py`)
- `frontend-design` — frontend design guidance
- `senior-backend` — backend best practices; includes API load tester, scaffolder, and DB migration tool scripts

### Hooks (`.claude/settings.json`)
All hooks run on `PostToolUse`:
- **simple-notifications** (`*`) — desktop notification on every tool completion (macOS/Linux)
- **smart-commit** (`Edit`) — auto-stages and commits edited files with size-classified message
- **smart-commit** (`Write`) — auto-commits newly written files with `Add new file: …`
- **security-scanner** (`Edit|Write`) — runs semgrep, bandit (`.py` only), gitleaks, and a regex secrets check after every file change

### Permissions (`.claude/settings.json`)
- **Allow:** `npm run lint`, `npm run test:*`, `npm run build`, `npm start`
- **Deny:** read or write to any `.env` / `.env.*` file

### Status line
`python3 .claude/scripts/context-monitor.py` — displays context usage bar, percentage, token count, session duration, and cost; turns red with `⚠ COMPACT SOON` at 85% context usage.

## Code conventions
- Python: snake_case, type hints on **all** parameters and return types, no function > 40 lines, no bare `except`
- React: functional components only, camelCase, no `console.log` in committed code
- All Python commands run via `uv run` — never activate the venv manually
- Tests: in-memory SQLite for backend tests; mock the Gemini client — no real API calls in tests

## Pre-commit checklist
Fix all failures before marking any feature complete:
```
cd backend && uv run ruff check . && uv run mypy . && uv run pytest tests/ -v
cd frontend && npm run lint && npx prettier --write src/ && npm run test
```
