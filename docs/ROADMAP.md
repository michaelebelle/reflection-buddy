# ROADMAP.md
> Last updated: 2026-08-24

---

## Completed

### Phase 1 — Core Journal ✅

| Feature | Status | Notes |
|---|---|---|
| User registration (email + bcrypt password) | ✅ Done | `routers/auth.py`, `services/auth.py` |
| JWT login (7-day token, localStorage) | ✅ Done | HS256, PyJWT |
| Auth gating — all journal routes protected | ✅ Done | `get_current_user` dependency |
| Per-user journal entries (full isolation) | ✅ Done | All queries filtered by user_id |
| Create journal entry | ✅ Done | POST /entries |
| Read entry list (paginated) | ✅ Done | GET /entries |
| Read single entry | ✅ Done | GET /entries/{id} |
| Update entry | ✅ Done | PUT /entries/{id} |
| Delete entry | ✅ Done | DELETE /entries/{id} |
| Mood selection (7 moods) | ✅ Done | excited, happy, calm, neutral, anxious, sad, frustrated |
| Energy level tracking (1–10) | ✅ Done | Stored on entry |
| 4 structured reflection question fields | ✅ Done | q_what_happened, q_how_felt, q_learned, q_improve_tomorrow |
| Dashboard with entry history | ✅ Done | Grouped by day, entry cards |
| Entry detail view | ✅ Done | Full reflection display |
| Mood-based static prompts (heuristic) | ✅ Done | 7 mood × 4 questions in `services/journal.py` |
| Responsive single-page frontend | ✅ Done | Vanilla JS + Tailwind CDN |
| Vercel deployment | ✅ Done | `api/index.py` + `vercel.json` |
| Neon Postgres (production DB) | ✅ Done | `DATABASE_URL` env var |
| Audit trail (created_by, updated_by) | ✅ Done | Populated from user_id on every write |

### Phase 2 — Semantic Search ✅ (Core)

| Feature | Status | Notes |
|---|---|---|
| Entry embeddings on save (OpenAI ada-3-small) | ✅ Done | `services/embeddings.py`, `_store_embedding()` |
| pgvector column on journal_entries | ✅ Done | Added via startup migration on Postgres |
| Semantic search endpoint | ✅ Done | GET /entries/search?q=... returns similarity scores |
| Similar entry retrieval for smart prompts | ✅ Done | Used in `get_smart_prompts()` |
| Smart contextual prompts (Claude Haiku 4.5) | ✅ Done | POST /entries/prompts/smart — takes current text, finds similar past entries, generates questions |
| AI reflection questions (mood-based, Claude) | ✅ Done | GET /entries/prompts — `ReflectionPromptGenerator` |

### User Onboarding ✅

| Feature | Status | Notes |
|---|---|---|
| 4-step onboarding wizard (frontend) | ✅ Done | Goals → Stressors → Habits → Baselines |
| Goal collection (1–3 goals, structured) | ✅ Done | `user_goals` table |
| Stressor collection (0–5, structured) | ✅ Done | `user_stressors` table |
| Habit definition (3–8 habits) | ✅ Done | `user_habits` table |
| Baseline self-ratings (6 dimensions) | ✅ Done | `user_onboarding` table |
| POST / GET / PATCH /onboarding endpoints | ✅ Done | Full CRUD |
| Onboarding gate (new users redirected) | ✅ Done | `bootstrapAuth()` checks onboarding status |
| `build_llm_context()` formatter | ✅ Done | Formats onboarding as LLM-injectable text block |
| Onboarding context injected into smart prompts | ✅ Done | `get_smart_prompts()` calls `build_llm_context()` |
| Habit schedule UI in onboarding wizard | ✅ Done | schedule_type selector + day-picker toggle buttons (Mon–Sun) |

### Phase 3.5 — Goal Check-In ✅

| Feature | Status | Notes |
|---|---|---|
| `schedule_type` + `schedule_days` on `user_habits` | ✅ Done | daily, specific_days, x_per_week, unscheduled |
| `habit_logs` table (UNIQUE user_id+habit_id+date) | ✅ Done | `models/checkin.py` |
| `_is_due()` deterministic scheduling logic | ✅ Done | Service layer only — no LLM involved |
| GET /check-ins/today (with optional ?date= param) | ✅ Done | Accepts browser local date to avoid timezone skew |
| POST /check-ins (idempotent upsert) | ✅ Done | Safe to call multiple times for same habit+date |
| PUT /check-ins/{id} (partial update) | ✅ Done | Update completed flag and/or note |
| Goal Check-In section on dashboard + new entry form | ✅ Done | Dashboard caches check-in data; reused when opening New Entry same day |
| Per-user isolation on check-ins | ✅ Done | All queries filtered by user_id; habit ownership verified on POST |

### Phase 4 — Goal Tracking ✅ (Core)

| Feature | Status | Notes |
|---|---|---|
| Goal status lifecycle (active / archived / completed) | ✅ Done | `status` column on `user_goals`; PUT /goals/{id} |
| Goal scheduling fields (cadence, duration, end_date) | ✅ Done | All nullable; `end_date` computed from `duration_weeks` if not set explicitly |
| GET /goals — list with status filter | ✅ Done | Default excludes archived; pass `?status=archived` to see archived |
| POST /goals — create standalone goal | ✅ Done | Separate from onboarding; sets status=active, computes end_date |
| PUT /goals/{id} — PATCH semantics (only supplied fields updated) | ✅ Done | Preserves historical check-in data regardless of edits |
| GET /goals/progress — weekly deterministic progress | ✅ Done | Counts habit_logs for habits linked via goal_id FK; no LLM |
| Goals view in frontend | ✅ Done | Header nav → Goals; filter tabs; goal cards; inline create/edit form |
| Dashboard goal progress section | ✅ Done | Progress bars per active goal; Manage → link to Goals view |
| Proactive dashboard prompts (GET /entries/prompts/dashboard) | ✅ Done | 2-3 AI prompts on dashboard load; no semantic search; graceful default fallback |
| Smart prompt button always enabled | ✅ Done | Renamed "✦ Refine with what I've written"; no longer requires 10+ chars before enabling |

---

## In Progress

### Phase 2 — Semantic Search (Remaining)

| Feature | Status | Notes |
|---|---|---|
| Search UI in frontend | 🔧 In Progress | Endpoint exists (`GET /entries/search`), no frontend component yet |
| Re-embed existing entries (backfill) | 🔧 In Progress | No batch job or admin endpoint exists; only new/updated entries are embedded |

### Phase 4 — Goal Tracking (Remaining)

| Feature | Status | Notes |
|---|---|---|
| Goal ↔ Habit linking UI | 🔧 In Progress | `goal_id` FK on `user_habits` exists and is used in progress calculation; UI doesn't expose it yet |

---

## Planned

### Phase 3 — Journal RAG (Memory System)

**Goal:** Let users ask natural-language questions about their own journal history.

| Feature | Status |
|---|---|
| "What patterns do you notice in my journal?" | Planned |
| "What causes my stress?" | Planned |
| "When am I most productive?" | Planned |
| "What have I learned recently?" | Planned |
| Retrieval layer — embed query, fetch top-K entries | Planned |
| Prompt construction with retrieved context | Planned |
| Conversational interface / chat view | Planned |
| Journal memory system (long-horizon context) | Planned |
| AI-generated insight cards | Planned |

*Foundation already in place: embeddings, semantic search, and `build_llm_context()` are all live.*

---

### Phase 4 — Goal Tracking (Remaining)

**Goal:** Complete the goal system — goal↔entry linkage, analytics, AI-driven goal insights.

| Feature | Status |
|---|---|
| Goal ↔ Habit linking UI | 🔧 In Progress — `goal_id` FK exists, needs frontend selector |
| Link journal entries to goals | Planned |
| AI-based goal-entry alignment scoring | Planned |
| Goal-specific reflection prompts | Planned |
| Goal-specific analytics (streaks, trend, adherence over time) | Planned |

*Foundation: Full CRUD, scheduling, weekly progress, and status lifecycle are all live. The gap is UI linkage between habits and goals.*

---

### Phase 5 — Habit Analytics & Insights

**Goal:** Streaks, correlations, and AI-generated behavioural insights on top of the check-in data that now exists.

| Feature | Status |
|---|---|
| Daily habit check-in UI | ✅ Done (Phase 3.5) |
| `habit_logs` table | ✅ Done (Phase 3.5) |
| Streak calculation | Planned |
| Habit-mood correlation analysis | Planned |
| Weekly reflection summary (AI-generated) | Planned |
| Monthly review (AI-generated) | Planned |
| Mood trend charts | Planned |
| Energy trend charts | Planned |
| Baseline vs. current comparison | Planned |
| Recurring theme detection | Planned |
| AI coaching recommendations | Planned |

*Foundation: `habit_logs` table live with daily check-ins. `user_habits` has scheduling fields. All baseline data in `user_onboarding`.*

---

### Phase 6 — Personal Knowledge System

**Goal:** Long-term memory and personal operating system.

| Feature | Status |
|---|---|
| Life timeline view | Planned |
| Major life events tagging | Planned |
| Decision tracking | Planned |
| Relationship tracking | Planned |
| Knowledge graph | Planned |
| Advanced semantic retrieval | Planned |
| Personal operating system dashboard | Planned |
