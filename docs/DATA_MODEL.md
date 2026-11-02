# DATA_MODEL.md
> Existing and proposed entities — as of 2026-11-01

---

## Existing tables

### `users`
**File:** `backend/app/models/user.py`

| Column | Type | Notes |
|---|---|---|
| id | VARCHAR(36) | UUID v4, PK |
| email | VARCHAR(255) | Unique, lowercased |
| hashed_password | VARCHAR(255) | bcrypt |
| created_at | DATETIME(tz) | |

---

### `journal_entries`
**File:** `backend/app/models/journal.py`

| Column | Type | Notes |
|---|---|---|
| id | VARCHAR(36) | UUID v4, PK |
| user_id | VARCHAR(36) | FK → users.id, nullable (legacy) |
| content | TEXT | Main entry body |
| mood | VARCHAR(50) | excited/happy/calm/neutral/anxious/sad/frustrated |
| energy_level | INTEGER | 1–10 |
| q_what_happened | TEXT | Reflection answer |
| q_how_felt | TEXT | Reflection answer |
| q_learned | TEXT | Reflection answer |
| q_improve_tomorrow | TEXT | Reflection answer |
| created_by | VARCHAR(100) | Audit trail |
| updated_by | VARCHAR(100) | Audit trail |
| created_at / updated_at | DATETIME(tz) | |
| embedding | vector(1536) | **Postgres only** — OpenAI embedding, NOT in ORM model |

---

### `user_onboarding`
**File:** `backend/app/models/onboarding.py`

One row per user (UNIQUE on user_id). Baseline self-ratings from onboarding wizard.

| Column | Type | Notes |
|---|---|---|
| id | VARCHAR(36) | UUID v4, PK |
| user_id | VARCHAR(36) | FK → users.id, UNIQUE |
| mood/energy/stress/confidence/discipline/life_satisfaction _baseline | INTEGER | 1–10 each |
| completed_at / updated_at | DATETIME(tz) | |

---

### `user_goals`
**File:** `backend/app/models/onboarding.py`

| Column | Type | Notes |
|---|---|---|
| id | VARCHAR(36) | UUID v4, PK |
| user_id | VARCHAR(36) | FK → users.id |
| category | VARCHAR(50) | career/fitness/relationships/mental_health/discipline/finances/school/creativity/other |
| title | VARCHAR(200) | |
| why_it_matters | TEXT | |
| success_definition | TEXT | |
| target_timeframe | VARCHAR(50) | 1_month/3_months/6_months/1_year/ongoing |
| status | VARCHAR(20) | active/archived/completed; NULL = active |
| cadence_per_week | INTEGER | Weekly habit target |
| schedule_days | VARCHAR(20) | Comma-sep weekdays 0=Mon..6=Sun |
| duration_weeks | INTEGER | |
| end_date | VARCHAR(10) | YYYY-MM-DD |
| created_at / updated_at | DATETIME(tz) | |

---

### `user_stressors`
**File:** `backend/app/models/onboarding.py`

| Column | Type | Notes |
|---|---|---|
| id | VARCHAR(36) | UUID v4, PK |
| user_id | VARCHAR(36) | FK → users.id |
| category | VARCHAR(50) | work/school/relationships/family/money/health/… |
| description | TEXT | |
| intensity | INTEGER | 1–10 |
| frequency | VARCHAR(50) | daily/several_times_per_week/weekly/occasionally |
| created_at | DATETIME(tz) | |

---

### `user_habits`
**File:** `backend/app/models/onboarding.py`

| Column | Type | Notes |
|---|---|---|
| id | VARCHAR(36) | UUID v4, PK |
| user_id | VARCHAR(36) | FK → users.id |
| name | VARCHAR(100) | e.g. "Morning run" |
| desired_frequency | VARCHAR(50) | daily/3x_per_week/5x_per_week/weekly/as_needed |
| positive_or_negative | VARCHAR(20) | positive/negative |
| tracking_type | VARCHAR(20) | boolean/numeric/duration/text |
| schedule_type | VARCHAR(20) | daily/specific_days/x_per_week/unscheduled |
| schedule_days | VARCHAR(20) | Comma-sep weekdays (only when specific_days) |
| goal_id | VARCHAR(36) | FK → user_goals.id, SET NULL on delete |
| created_at | DATETIME(tz) | |

---

### `habit_logs`
**File:** `backend/app/models/checkin.py`

| Column | Type | Notes |
|---|---|---|
| id | VARCHAR(36) | UUID v4, PK |
| user_id | VARCHAR(36) | FK → users.id |
| habit_id | VARCHAR(36) | FK → user_habits.id |
| date | VARCHAR(10) | YYYY-MM-DD (user's local date) |
| completed | BOOLEAN | |
| note | TEXT | Optional free-text |
| value_numeric | FLOAT | Reserved for future numeric tracking |
| created_at / updated_at | DATETIME(tz) | |

**Constraint:** UNIQUE(user_id, habit_id, date) — `uq_habit_log_user_habit_date`

---

## ER diagram (existing)

```
users
  │
  ├──< journal_entries   (user_id FK, embedding column Postgres-only)
  │
  ├──  user_onboarding   (user_id UNIQUE FK)
  │
  ├──< user_goals        (user_id FK)
  │     │
  │     └──< user_habits (goal_id FK, SET NULL on delete)
  │             │
  │             └──< habit_logs (habit_id FK, UNIQUE user+habit+date)
  │
  ├──< user_stressors    (user_id FK)
  │
  └──< habit_logs        (user_id FK)
```

---

## Proposed new tables

These do not exist yet. Defined here for Phase 1 planning.

### `calendar_events` (proposed)

| Column | Type | Notes |
|---|---|---|
| id | VARCHAR(36) | UUID v4, PK |
| user_id | VARCHAR(36) | FK → users.id, NOT NULL |
| title | VARCHAR(200) | NOT NULL |
| description | TEXT | Optional |
| date | VARCHAR(10) | YYYY-MM-DD |
| start_time | VARCHAR(5) | HH:MM (24h) |
| end_time | VARCHAR(5) | HH:MM (24h) |
| category | VARCHAR(50) | work/school/fitness/personal/other |
| status | VARCHAR(20) | planned/completed/missed — default: planned |
| task_id | VARCHAR(36) | FK → tasks.id, SET NULL on delete — optional link |
| created_at | DATETIME(tz) | |
| updated_at | DATETIME(tz) | |

---

### `tasks` (proposed)

| Column | Type | Notes |
|---|---|---|
| id | VARCHAR(36) | UUID v4, PK |
| user_id | VARCHAR(36) | FK → users.id, NOT NULL |
| title | VARCHAR(200) | NOT NULL |
| description | TEXT | Optional |
| status | VARCHAR(20) | todo/in_progress/completed — default: todo |
| due_date | VARCHAR(10) | YYYY-MM-DD, optional |
| category | VARCHAR(50) | Optional |
| source_entry_id | VARCHAR(36) | FK → journal_entries.id, SET NULL — which reflection surfaced this |
| created_at | DATETIME(tz) | |
| updated_at | DATETIME(tz) | |

---

## Design notes

**Why VARCHAR for dates?** Dialect-neutral. ISO strings sort correctly, work identically on SQLite (local) and Postgres (production), and avoid SQLAlchemy Date type casting differences.

**Why no ForeignKey on embedding?** The `embedding` column is a pgvector type not supported by SQLAlchemy directly. It's managed entirely via raw SQL in `_run_column_migrations()` in `main.py`.

**Why nullable `status` on user_goals?** Goals created via onboarding (before the `status` column existed) have `status = NULL`. The service layer treats `NULL` as `active`.

**Migration approach:** No Alembic. `_run_column_migrations()` in `main.py` runs idempotent `ALTER TABLE ADD COLUMN` at startup. Fine for single-instance; replace with Alembic before horizontal scaling.
