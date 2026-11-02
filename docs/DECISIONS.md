# DECISIONS.md
> Important design decisions and their rationale — as of 2026-11-01

---

## Existing decisions (already implemented)

### Custom bcrypt/JWT over third-party auth provider

**Decision:** Custom `services/auth.py` using `bcrypt` directly + `PyJWT`. No Auth0, Clerk, or Firebase.

**Rationale:** Portfolio depth. Interviewers ask "walk me through your authentication." Using a provider makes that question unanswerable. Custom implementation also avoids service dependencies and additional costs for a personal project.

**Where:** `backend/app/services/auth.py`

---

### OpenAI for embeddings, Anthropic for generation

**Decision:** Two separate AI providers — OpenAI `text-embedding-3-small` for embeddings, Anthropic `claude-haiku-4-5` for text generation.

**Rationale:** Anthropic has no embedding API. OpenAI embeddings are $0.02/1M tokens and industry-standard. Haiku is ~$0.000002/request for questions — negligible at personal scale. Keeping providers separate means each can be swapped independently.

**Where:** `services/embeddings.py`, `services/ai_prompts.py`

---

### Embedding column managed via raw SQL, not ORM

**Decision:** The `embedding vector(1536)` column in `journal_entries` is NOT declared in the SQLAlchemy model. It's added via `ALTER TABLE` at startup and written/read via raw SQL.

**Rationale:** pgvector's `vector` type has SQLAlchemy compatibility issues on older versions and doesn't work at all on SQLite. Raw SQL lets local dev (SQLite) work without the column, and production (Postgres + pgvector) get it transparently.

**Where:** `main.py:_run_column_migrations()`, `services/journal.py:_store_embedding()`

---

### Idempotent startup migrations over Alembic

**Decision:** `_run_column_migrations()` in `main.py` runs `ALTER TABLE ADD COLUMN IF NOT EXISTS` on every cold start. No Alembic.

**Rationale:** Zero operational overhead for a personal project with a single instance. Works on both SQLite and Postgres. Add Alembic before multi-instance deployment.

**Tradeoff:** Can't do destructive migrations (column renames, type changes, drops). Acceptable given the stage of the project.

---

### Vanilla JS SPA, no framework, no build step

**Decision:** All frontend code in `frontend/index.html` + `frontend/js/app.js`. No React, Vue, Svelte. No bundler.

**Rationale:** Eliminates build complexity. Easy to read and debug. Tailwind via CDN. Appropriate for a personal project with one developer. Can port to a framework later if complexity justifies it.

**Tradeoff:** `app.js` will grow large. Manage by keeping sections clearly commented and functions small.

---

### Smart prompts are opt-in, dashboard prompts are proactive

**Decision:** Dashboard loads 3 prompts on every page view (no click required). Smart prompts require clicking "✦ Refine with what I've written".

**Rationale:** Dashboard prompts use cheap path (no semantic search, just last 3 entries + onboarding context). Smart prompts use expensive path (OpenAI embedding + pgvector search + Haiku). Making smart prompts opt-in controls costs and avoids latency on every keystroke.

---

### No vector similarity for task completion status

**Decision:** Task status is stored deterministically in the database. Never use embedding similarity to infer whether a task is complete.

**Rationale:** Similarity is a probabilistic relevance signal, not a ground truth. Using it for status would produce false positives ("similar to a completed task" ≠ "this task is done"). Always use the explicit `status` column.

---

## New decisions (proposed for Phase 1+)

### Confirmation before any chatbot mutation

**Decision:** The chat endpoint returns `proposed_actions` but never writes to the database. The frontend presents each proposed action for explicit user acceptance before calling the relevant CRUD endpoint.

**Rationale:** An assistant that silently modifies your calendar or task list is frustrating. Users need to trust the system. Confirmation also creates a natural evaluation signal: `user_accepted = false` means the proposal was wrong or unhelpful.

---

### One structured LLM call for intent detection

**Decision:** Intent detection uses a single `client.messages.create()` call with a structured output format (JSON). No chaining, no agent loop, no LangChain.

**Rationale:** A single call is traceable, debuggable, and testable. Multi-step chains add latency and failure modes without adding value for the three intents we support. Add complexity only when a single call demonstrably can't handle it.

**Implementation:** `services/chat.py:classify_intent()` → returns `{intent, extracted_fields}`.

---

### Separate retrieval from generation in chat

**Decision:** `services/chat.py` calls `semantic_search()` and structured DB queries, then injects results into the LLM prompt. The retrieval and generation are separate function calls, not embedded inside a prompt template.

**Rationale:** Keeps each component independently testable. Can evaluate retrieval quality without running the LLM. Can change the prompt without changing the retrieval logic.

---

### Use VARCHAR(10) for dates everywhere

**Decision:** All date columns (including `calendar_events.date`, `tasks.due_date`) use `VARCHAR(10)` storing ISO strings ("YYYY-MM-DD"), not SQLAlchemy's `Date` type.

**Rationale:** Consistency with existing tables (`habit_logs.date`). Avoids dialect differences between SQLite and Postgres date handling. ISO strings sort correctly as strings. Timezone-neutral — dates represent user's local date, not UTC.

---

### Source IDs in chatbot responses

**Decision:** When the chatbot references past entries, include the `entry_id` in the response payload so the UI can link to the original entry.

**Rationale:** Users should be able to verify where a suggestion came from. Prevents the model from hallucinating past context ("you mentioned X last week" when they didn't). Traceability is also required for evaluation — you need to know which entries were actually retrieved.

---

### No autonomous scheduling

**Decision:** The MVP chatbot does not autonomously find open slots, evaluate priorities, and schedule a full day. It proposes one action at a time for confirmation.

**Rationale:** An autonomous scheduler is high risk (it can trash your calendar) and hard to evaluate. It requires solving conflict detection, priority scoring, and break-time reasoning — each complex independently. Phase 1 deterministic availability + Phase 2 single-action proposals is enough for real use.
