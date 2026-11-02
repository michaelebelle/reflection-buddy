# ARCHITECTURE.md
> Phase 0 documentation — reflects actual codebase as of 2026-11-01

---

## Overview

Reflection Buddy is a FastAPI backend + vanilla JS single-page application. The entire backend runs as a single Vercel serverless function. There is no build step, no framework, no background workers.

```
Browser
  │
  ├── Static files served by Vercel (index.html, app.js, styles.css)
  │
  └── API calls (fetch + Authorization: Bearer <jwt>)
        │
        └── Vercel Serverless → api/index.py
                │
                └── FastAPI app (backend/app/main.py)
                      │
                      ├── /api/v1/auth/*         routers/auth.py
                      ├── /api/v1/entries/*      routers/journal.py
                      ├── /api/v1/onboarding/*   routers/onboarding.py
                      ├── /api/v1/check-ins/*    routers/checkin.py
                      └── /api/v1/goals/*        routers/goals.py
```

**Local dev:** SQLite (`backend/journal.db`), open `frontend/index.html` directly.
**Production:** Neon Postgres (+ pgvector), deployed on Vercel.

---

## Layer responsibilities

| Layer | Rule | Where it lives |
|---|---|---|
| Router | HTTP wiring only — no business logic | `backend/app/routers/*.py` |
| Service | All business logic, DB queries, LLM calls | `backend/app/services/*.py` |
| ORM | Table definitions, relationships | `backend/app/models/*.py` |
| Schema | Request/response validation (Pydantic) | `backend/app/schemas/*.py` |
| Frontend | All UI and API calls | `frontend/index.html`, `frontend/js/app.js` |

---

## All current API endpoints

### Auth — `routers/auth.py`
```
POST /api/v1/auth/register   → creates User, returns UserResponse
POST /api/v1/auth/login      → verifies password, returns {access_token}
GET  /api/v1/auth/me         → returns current user from token
```

### Journal — `routers/journal.py`
```
POST /api/v1/entries                    create entry (triggers embedding)
GET  /api/v1/entries                    list entries (paginated)
GET  /api/v1/entries/{id}               get single entry
PUT  /api/v1/entries/{id}               update entry (re-embeds)
DELETE /api/v1/entries/{id}             delete entry

GET  /api/v1/entries/prompts/dashboard  3 proactive dashboard prompts (Haiku)
GET  /api/v1/entries/prompts            4 reflection questions (Haiku, mood-aware)
POST /api/v1/entries/prompts/smart      4 contextual questions (Haiku + RAG)
GET  /api/v1/entries/search?q=          semantic search (pgvector cosine)

Route order matters: /prompts/dashboard and /search are registered before /{id}
```

### Onboarding — `routers/onboarding.py`
```
POST  /api/v1/onboarding   full replace (goals + stressors + habits + baselines)
GET   /api/v1/onboarding   returns current onboarding data or null
PATCH /api/v1/onboarding   partial update (only supplied sections replaced)
```

### Check-ins — `routers/checkin.py`
```
GET  /api/v1/check-ins/today         today's due habits + existing log state
POST /api/v1/check-ins               create/upsert a habit log (idempotent)
PUT  /api/v1/check-ins/{id}          update completed flag and/or note
```

### Goals — `routers/goals.py`
```
GET  /api/v1/goals/progress          weekly habit_log completion % per goal
GET  /api/v1/goals                   list goals (status filter)
POST /api/v1/goals                   create goal
GET  /api/v1/goals/{id}              get single goal
PUT  /api/v1/goals/{id}/habits       set linked habits (set semantics)
PUT  /api/v1/goals/{id}              update goal fields
```

---

## Frontend architecture

Single-page app. All views live in `frontend/index.html` as `<div class="view hidden">` elements. `frontend/js/app.js` controls visibility via `showView(id)`. No framework, no router library, no build step.

**Views:** auth, onboarding (4 steps), dashboard, new-entry, entry-detail, goals.

**Key JS sections in app.js:**
- `const api = {...}` — all `fetch` calls to the backend, each returns JSON or throws
- `state` object — current entry being edited, check-in state
- `dashboardCache` — caches today's check-ins to avoid a second API call from New Entry
- `obState` — onboarding wizard in-memory state (goals, habits, stressors, baselines)
- Dashboard functions: `loadDashboardData()`, `loadDashboardPrompts()`, `loadDashboardCommitments()`, `loadDashboardGoalProgress()`
- Goals functions: `showGoalForm()`, `handleGoalFormSubmit()`, `loadGoals()`

---

## Startup sequence

`main.py` lifespan runs two steps on every cold start:
1. `Base.metadata.create_all()` — creates any missing tables
2. `_run_column_migrations()` — idempotent `ALTER TABLE ADD COLUMN` for new columns

This replaces Alembic. Safe for single-instance deployment; replace with Alembic before horizontal scaling.

---

## External dependencies

| Service | Used for | Env var |
|---|---|---|
| Anthropic API (claude-haiku-4-5) | Reflection questions, smart prompts, dashboard prompts | `ANTHROPIC_API_KEY` |
| OpenAI API (text-embedding-3-small) | Entry embeddings (1536-dim), semantic search queries | `OPENAI_API_KEY` |
| Neon Postgres + pgvector | Production DB, vector storage/search | `DATABASE_URL` |

Both AI services degrade gracefully — the app works without either (fallback to static prompts, no semantic search).

---

## What does NOT exist yet

- Calendar events (no table, no API, no UI)
- Tasks / tracked items (no table, no API, no UI)
- Chat interface (no endpoint, no UI)
- Streak calculation (data exists in habit_logs, no computation)
- Search UI (endpoint exists, no frontend component)
- Habit management outside onboarding (no edit/delete single habit)
- Multi-turn conversation state (no session, no history)
