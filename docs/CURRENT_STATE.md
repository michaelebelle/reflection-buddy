# CURRENT_STATE.md
> Last updated: 2026-06-01 — read this first when returning to the project

---

## Project Snapshot

Reflection Buddy is a deployed, working AI journaling platform. Users register, complete a 4-step onboarding wizard (goals, stressors, habits, baseline ratings), and then write journal entries with structured reflection questions. When writing, they can click "✦ Generate smart prompts" to get Claude-generated follow-up questions that reference what they just wrote AND semantically similar past entries. Every entry is automatically embedded (OpenAI) and stored as a pgvector on Neon Postgres for future retrieval. The API is deployed on Vercel; the frontend is vanilla JS + Tailwind. Authentication is custom bcrypt/JWT — no third-party auth provider.

---

## Current Architecture Summary

| Layer | Technology | Notes |
|---|---|---|
| **Frontend** | Vanilla JS SPA, Tailwind CDN | `frontend/index.html` + `frontend/js/app.js` — all views in one file, shown/hidden by JS |
| **Backend** | FastAPI (Python), Uvicorn | `backend/app/` — routers → services → ORM pattern |
| **Database (local)** | SQLite | Zero config, no vector search |
| **Database (prod)** | Neon Postgres + pgvector | `embedding vector(1536)` column on journal_entries |
| **Auth** | bcrypt + PyJWT (HS256) | 7-day tokens stored in localStorage |
| **AI — questions** | Anthropic claude-haiku-4-5 | `services/ai_prompts.py` — ~$0.000002/request |
| **AI — embeddings** | OpenAI text-embedding-3-small | `services/embeddings.py` — 1536 dims, ~$0.000002/entry |
| **Deployment** | Vercel (serverless) | `api/index.py` entry point, routes all traffic to FastAPI |

---

## What Works Today

- [x] User registration and login (bcrypt + JWT)
- [x] Token stored in localStorage, validated on every page load
- [x] Onboarding wizard — 4 steps: goals, stressors, habits, baseline ratings
- [x] Onboarding gate — new users redirected to wizard, returning users skip
- [x] Create journal entry with content, mood, energy level
- [x] 4 structured reflection question fields per entry
- [x] Mood-based static prompts (heuristic fallback — 7 moods × 4 questions)
- [x] AI reflection questions via Claude Haiku (GET /entries/prompts)
- [x] **"✦ Generate smart prompts"** button — takes current text, finds similar past entries, generates contextual questions via Claude
- [x] Entry embeddings generated and stored on every save (OpenAI, Postgres only)
- [x] Semantic search endpoint (GET /entries/search?q=...)
- [x] Dashboard — entries grouped by day, entry cards
- [x] Entry detail view
- [x] Edit and delete entries
- [x] `build_llm_context()` — formats onboarding profile into LLM-injectable text block
- [x] Per-user data isolation — all queries filtered by user_id
- [x] Deployed on Vercel + Neon

---

## Currently In Progress

### Search UI
- **Status:** Backend complete, frontend missing
- **Relevant files:** `backend/app/routers/journal.py` (`GET /entries/search`), `frontend/js/app.js`
- **Next step:** Add a search input to the dashboard that calls `api.searchEntries(q)` and renders results

### Embedding backfill
- **Status:** New entries are auto-embedded; no tool to embed existing entries
- **Relevant files:** `backend/app/services/embeddings.py`, `backend/app/services/journal.py`
- **Next step:** One-off admin script or endpoint to embed all entries where `embedding IS NULL`

---

## Next Recommended Task

**Add the semantic search UI to the dashboard**

- **Goal:** Let users search their journal by meaning, not keywords
- **Why it matters:** The backend is 100% ready — the endpoint exists and returns ranked results with similarity scores. The feature is invisible until there's a UI for it. This is the highest-impact low-effort unlock right now.
- **Files affected:**
  - `frontend/index.html` — add search input to dashboard header
  - `frontend/js/app.js` — add `api.searchEntries()`, render search results view
- **Estimated complexity:** Small (2–3 hours)

---

## Active Roadmap Phase

```
Current:  Phase 2 — Semantic Search (core done, search UI remaining)
Next:     Phase 3 — Journal RAG (ask questions about your history)
```

---

## Upcoming Features (Priority Order)

1. **Search UI** — wire existing `GET /entries/search` endpoint to the dashboard
2. **Embedding backfill script** — embed all historical entries so search works immediately
3. **Habit check-in UI** — daily logging against habits defined in onboarding
4. **Goal-entry linkage** — AI scores how much each entry relates to each goal
5. **Weekly AI summary** — Claude-generated summary of the past 7 days using retrieved entries

---

## Important Files

| File | Purpose | Why it matters |
|---|---|---|
| `backend/app/services/journal.py` | All journal business logic | Add any new journal feature here first |
| `backend/app/services/ai_prompts.py` | Claude question generation | Edit `SYSTEM_PROMPT` or `SMART_SYSTEM_PROMPT` to tune AI behavior |
| `backend/app/services/onboarding.py` | Onboarding CRUD + `build_llm_context()` | This function gets injected into every LLM call — keep it accurate |
| `backend/app/services/embeddings.py` | OpenAI embedding generation | Change `MODEL` or `DIMENSIONS` here if switching embedding provider |
| `backend/app/main.py` | App factory + startup migrations | Add new column migrations here; register new routers here |
| `frontend/js/app.js` | All frontend logic | Single file — search for function names to find any UI behavior |
| `backend/app/models/onboarding.py` | 4 onboarding tables | Add new onboarding fields here |

---

## Open Technical Decisions

| Decision | Options | Current Recommendation |
|---|---|---|
| **Migration strategy** | Current: hand-rolled `ALTER TABLE` at startup / Alembic | Move to Alembic before any multi-instance or team deployment |
| **Habit log storage** | New `habit_logs` table vs. JSON column on entry | Separate table — needed for streak queries and time-series analysis |
| **Goal-entry linkage model** | Explicit FK table / implicit via embedding similarity | Start with embedding similarity (no schema change needed); add explicit table when goal dashboard is built |
| **Weekly summary generation** | On-demand endpoint / scheduled cron | On-demand first; cron job once usage patterns are clear |
| **RAG retrieval strategy** | Top-K cosine similarity (current) / hybrid BM25 + vector | Top-K is already implemented; add BM25 when pure semantic retrieval misses keyword-specific queries |
| **Frontend framework** | Stay vanilla / add React/Vue | Stay vanilla until complexity justifies a build step |

---

## Last Major Changes

| Date | Feature | Files Modified | Impact |
|---|---|---|---|
| 2026-06-01 | Smart contextual prompts (POST /entries/prompts/smart) | `services/ai_prompts.py`, `services/journal.py`, `schemas/journal.py`, `routers/journal.py`, `frontend/js/app.js`, `frontend/index.html` | Users can now generate Claude questions grounded in what they're writing + similar past entries |
| 2026-06-01 | User onboarding wizard (4 steps) | `models/onboarding.py`, `schemas/onboarding.py`, `services/onboarding.py`, `routers/onboarding.py`, `main.py`, `frontend/index.html`, `frontend/js/app.js` | All new users captured goals, stressors, habits, baselines — LLM context now available for every user |
| 2026-06-01 | Entry embeddings + semantic search | `services/embeddings.py`, `services/journal.py`, `schemas/journal.py`, `routers/journal.py`, `main.py` | Every entry now auto-embedded; GET /entries/search works in production |
| 2026-06-01 | AI reflection questions (Claude Haiku) | `services/ai_prompts.py`, `services/journal.py` | GET /entries/prompts now uses Claude instead of static strings |
| Prior | Authentication (bcrypt + JWT) | `models/user.py`, `services/auth.py`, `routers/auth.py`, `schemas/auth.py`, `main.py`, `frontend/js/app.js`, `frontend/index.html` | Full user isolation; journal entries are private |

---

## Development Resume Summary

"Built a full-stack AI journaling platform (Reflection Buddy) from scratch, including custom bcrypt/JWT authentication, per-user journal storage with mood and energy tracking, structured reflection prompts, and a 4-step onboarding system that captures user goals, stressors, habits, and baseline self-ratings. Integrated the Anthropic API (Claude Haiku 4.5) for personalized reflection question generation and OpenAI's text-embedding-3-small for entry embeddings stored in a pgvector column on Neon Postgres. Built semantic search across journal history and a 'smart prompts' feature that finds similar past entries and generates contextual follow-up questions grounded in both the current entry and the user's onboarding profile. Deployed on Vercel as a serverless FastAPI application with a vanilla JS single-page frontend."
