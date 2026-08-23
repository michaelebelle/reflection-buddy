# DATABASE_SCHEMA.md
> Last updated: 2026-06-01 — verified against actual SQLAlchemy models

---

## Database Configuration

| Setting | Value |
|---|---|
| Local dev | SQLite (`journal.db` in `backend/`) |
| Production | Neon (PostgreSQL + pgvector extension) |
| ORM | SQLAlchemy 2.0 (DeclarativeBase) |
| Connection file | `backend/app/database.py` |
| Engine config | `pool_pre_ping=True` (serverless-safe), `check_same_thread=False` (SQLite only) |
| Session injection | FastAPI dependency `get_db()` — yields session, closes on teardown |

---

## Schema Files

| File | Tables defined |
|---|---|
| `backend/app/models/user.py` | `users` |
| `backend/app/models/journal.py` | `journal_entries` |
| `backend/app/models/onboarding.py` | `user_onboarding`, `user_goals`, `user_stressors`, `user_habits` |

---

## ER Diagram

```
users
  │
  ├──< journal_entries   (user_id FK, CASCADE DELETE)
  │
  ├──  user_onboarding   (user_id FK UNIQUE, CASCADE DELETE)
  │
  ├──< user_goals        (user_id FK, CASCADE DELETE)
  │
  ├──< user_stressors    (user_id FK, CASCADE DELETE)
  │
  └──< user_habits       (user_id FK, CASCADE DELETE)
```

---

## Table: `users`

**Purpose:** Authentication identity — one row per registered account.

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | VARCHAR(36) | NOT NULL | UUID v4, primary key |
| email | VARCHAR(255) | NOT NULL | Unique, indexed, lowercased on write |
| hashed_password | VARCHAR(255) | NOT NULL | bcrypt hash — never stored plain |
| created_at | DATETIME(tz) | NOT NULL | UTC timestamp of registration |

**Relationships:** `entries` → one-to-many `JournalEntry` (lazy dynamic)
**Indexes:** `email` (unique)

---

## Table: `journal_entries`

**Purpose:** Core journal data. One row per user entry.

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | VARCHAR(36) | NOT NULL | UUID v4, primary key |
| created_at | DATETIME(tz) | NOT NULL | Entry creation time (UTC) |
| updated_at | DATETIME(tz) | NOT NULL | Auto-updated on any change |
| user_id | VARCHAR(36) | YES | FK → users.id (nullable for pre-auth legacy rows) |
| content | TEXT | NOT NULL | Main journal body text |
| mood | VARCHAR(50) | YES | One of: excited, happy, calm, neutral, anxious, sad, frustrated |
| energy_level | INTEGER | YES | 1–10 self-rated energy |
| q_what_happened | TEXT | YES | Reflection answer: what happened |
| q_how_felt | TEXT | YES | Reflection answer: how I felt |
| q_learned | TEXT | YES | Reflection answer: what I learned |
| q_improve_tomorrow | TEXT | YES | Reflection answer: what to improve |
| created_by | VARCHAR(100) | YES | User ID of creator (audit trail) |
| updated_by | VARCHAR(100) | YES | User ID of last editor (audit trail) |
| embedding | vector(1536) | YES | **Postgres only** — OpenAI text-embedding-3-small vector, added via startup migration |

**Relationships:** `user` → many-to-one `User`
**Indexes:** `user_id`
**Notes:**
- `embedding` column does **not** exist in the SQLAlchemy model — it is managed entirely via raw SQL in `_run_column_migrations()` (Postgres only; silently absent on SQLite)
- `user_id` is nullable to preserve entries created before authentication was added

---

## Table: `user_onboarding`

**Purpose:** Baseline self-ratings and completion marker. One row per user (UNIQUE on user_id).

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | VARCHAR(36) | NOT NULL | UUID v4, primary key |
| user_id | VARCHAR(36) | NOT NULL | FK → users.id, UNIQUE |
| mood_baseline | INTEGER | NOT NULL | 1–10 starting mood rating |
| energy_baseline | INTEGER | NOT NULL | 1–10 starting energy rating |
| stress_baseline | INTEGER | NOT NULL | 1–10 starting stress rating |
| confidence_baseline | INTEGER | NOT NULL | 1–10 starting confidence rating |
| discipline_baseline | INTEGER | NOT NULL | 1–10 starting discipline rating |
| life_satisfaction_baseline | INTEGER | NOT NULL | 1–10 starting life satisfaction rating |
| completed_at | DATETIME(tz) | NOT NULL | When onboarding was first submitted |
| updated_at | DATETIME(tz) | NOT NULL | Last PATCH time |

**Indexes:** `user_id` (unique)
**Used by:** `build_llm_context()` injects these as comparison anchors into LLM prompts

---

## Table: `user_goals`

**Purpose:** Active user goals (1–3 per user). Structured for LLM comparison against journal entries.

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | VARCHAR(36) | NOT NULL | UUID v4, primary key |
| user_id | VARCHAR(36) | NOT NULL | FK → users.id |
| category | VARCHAR(50) | NOT NULL | career, fitness, relationships, mental_health, discipline, finances, school, creativity, other |
| title | VARCHAR(200) | NOT NULL | Short goal title |
| why_it_matters | TEXT | NOT NULL | User's stated motivation |
| success_definition | TEXT | NOT NULL | How user defines achievement |
| target_timeframe | VARCHAR(50) | NOT NULL | 1_month, 3_months, 6_months, 1_year, ongoing |
| created_at | DATETIME(tz) | NOT NULL | Row creation time |

**Indexes:** `user_id`
**Notes:** POST /onboarding deletes and replaces all rows for the user (full replace semantics)

---

## Table: `user_stressors`

**Purpose:** Current stressors (0–5 per user). Used to surface recurring negative patterns in AI analysis.

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | VARCHAR(36) | NOT NULL | UUID v4, primary key |
| user_id | VARCHAR(36) | NOT NULL | FK → users.id |
| category | VARCHAR(50) | NOT NULL | work, school, relationships, family, money, health, loneliness, burnout, motivation, time_management, other |
| description | TEXT | NOT NULL | User's description of the stressor |
| intensity | INTEGER | NOT NULL | 1–10 severity |
| frequency | VARCHAR(50) | NOT NULL | daily, several_times_per_week, weekly, occasionally |
| created_at | DATETIME(tz) | NOT NULL | Row creation time |

**Indexes:** `user_id`

---

## Table: `user_habits`

**Purpose:** Habits to track (3–8 per user). Foundation for future streak and correlation analysis.

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | VARCHAR(36) | NOT NULL | UUID v4, primary key |
| user_id | VARCHAR(36) | NOT NULL | FK → users.id |
| name | VARCHAR(100) | NOT NULL | Habit name (e.g. "deep_work", "exercise") |
| desired_frequency | VARCHAR(50) | NOT NULL | daily, 3x_per_week, 5x_per_week, weekly, as_needed |
| positive_or_negative | VARCHAR(20) | NOT NULL | positive or negative |
| tracking_type | VARCHAR(20) | NOT NULL | boolean, numeric, duration, text |
| created_at | DATETIME(tz) | NOT NULL | Row creation time |

**Indexes:** `user_id`
**Notes:** Habits are *defined* here. A `habit_logs` table for daily check-ins does not yet exist — see Future Data Models.

---

## Migration History

| Change | How | File |
|---|---|---|
| Initial tables created | `Base.metadata.create_all()` on startup | `main.py` lifespan |
| Added `created_by`, `updated_by` to `journal_entries` | `_run_column_migrations()` idempotent ALTER | `main.py` |
| Added `user_id` FK to `journal_entries` | `_run_column_migrations()` idempotent ALTER | `main.py` |
| Added `embedding vector(1536)` to `journal_entries` (Postgres only) | `_run_column_migrations()` + `CREATE EXTENSION IF NOT EXISTS vector` | `main.py` |
| Added `user_onboarding`, `user_goals`, `user_stressors`, `user_habits` | `create_all()` (models imported in `main.py`) | `models/onboarding.py` |

**Migration approach:** No Alembic. All migrations run at startup via `_run_column_migrations()`. Idempotent — safe to run on every cold start. Fine for single-instance deployment; replace with Alembic before horizontal scaling.

---

## Journal Data Model

**How entries are stored:** One row in `journal_entries` per save. Structured reflection answers stored as separate TEXT columns (not JSON) for direct SQL querying.

**How users relate to entries:** `user_id` FK. All queries in `journal_service` filter by `user_id = current_user.id`. Cross-user reads are impossible at the service layer.

**How prompts relate to responses:** Prompts are ephemeral — generated per-request and not stored. The reflection columns (`q_what_happened`, etc.) store the *answers*, not the questions. Questions are regenerated fresh on each new entry form load.

**How embeddings are generated:** On entry save/update, `_store_embedding()` calls `EmbeddingService.build_entry_text()` (concatenates mood + content + all reflection fields) → `EmbeddingService.generate()` → stores as `vector(1536)` via raw SQL UPDATE. Silently skipped if `OPENAI_API_KEY` not set or on SQLite.

---

## Future Data Models

### `habit_logs` — Planned
Daily habit check-ins. Does not exist yet.
```
id, user_id, habit_id (FK user_habits), date, value (boolean/int/float/text),
notes, created_at
```

### `goal_progress_events` — Planned
Links journal entries to goals. Does not exist yet.
```
id, user_id, goal_id (FK user_goals), entry_id (FK journal_entries),
alignment_score (0-1 float), notes, created_at
```

### `ai_insights` — Planned
Stored AI-generated summaries and pattern analysis. Does not exist yet.
```
id, user_id, type (weekly_summary | monthly_review | pattern | coaching),
content (text), date_range_start, date_range_end, created_at
```

### Sentiment / Themes columns on `journal_entries` — Planned
The model file has these commented out:
```python
# sentiment_score = Column(Float, nullable=True)
# ai_summary = Column(Text, nullable=True)
# themes = Column(Text, nullable=True)
# generated_prompts = Column(Text, nullable=True)
```
