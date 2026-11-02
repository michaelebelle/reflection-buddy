# RAG.md
> Exactly how indexing, retrieval, and context injection work — as of 2026-11-01

---

## Overview

There are two distinct AI-powered prompt paths. Only one of them uses RAG:

| Path | RAG? | Endpoint | Function |
|---|---|---|---|
| Reflection questions on new entry | No | `GET /entries/prompts` | `get_reflection_prompts()` in `services/journal.py` |
| Dashboard proactive prompts | No | `GET /entries/prompts/dashboard` | `get_dashboard_prompts()` in `services/journal.py` |
| **Smart contextual prompts** | **Yes** | `POST /entries/prompts/smart` | `get_smart_prompts()` in `services/journal.py` |
| Semantic search | N/A (raw retrieval) | `GET /entries/search?q=` | `semantic_search()` in `services/journal.py` |

---

## Indexing pipeline

### When does indexing happen?

On every `create_entry()` and `update_entry()` call in `services/journal.py`. There is no batch job — historical entries without embeddings stay unindexed until re-saved.

### Where is it implemented?

`services/journal.py` → `_store_embedding(db, entry)` (lines ~174–201)

### Step by step

```
1. Check dialect: if not PostgreSQL → return immediately (SQLite local dev skips embedding)
2. Build embedding text:
     EmbeddingService.build_entry_text(entry)
     Concatenates: "Mood: {mood}\n{content}\n{q_what_happened}\n{q_how_felt}\n{q_learned}\n{q_improve_tomorrow}"
     Only includes fields that are non-empty.
3. Generate vector:
     EmbeddingService.generate(text) → OpenAI text-embedding-3-small → list[float] of length 1536
     Returns None on failure (app continues, entry saves without embedding)
4. Persist vector:
     Raw SQL UPDATE: UPDATE journal_entries SET embedding = CAST(:vec AS vector) WHERE id = :id
     Uses pgvector's vector(1536) column type
     The embedding column is NOT in the SQLAlchemy model — managed entirely via raw SQL
```

**Key file:** `backend/app/services/embeddings.py`
- `EmbeddingService.MODEL = "text-embedding-3-small"`
- `EmbeddingService.DIMENSIONS = 1536`
- `EmbeddingService.MAX_INPUT_CHARS = 8000`

---

## Retrieval pipeline

### Where is it implemented?

`services/journal.py` → `semantic_search(db, user_id, query, limit=5)` (lines ~205–248)

### Step by step

```
1. Check dialect: if not PostgreSQL → return []
2. Embed the query:
     EmbeddingService.generate(query) → list[float]
3. Run cosine similarity search:
     SQL: SELECT id, content, mood, created_at,
               1 - (embedding <-> CAST(:vec AS vector)) AS similarity
          FROM journal_entries
          WHERE user_id = :user_id AND embedding IS NOT NULL
          ORDER BY embedding <-> CAST(:vec AS vector)
          LIMIT :limit
     The <-> operator is pgvector's L2/cosine distance.
     Similarity score = 1 - distance (higher = more similar).
4. Return list of dicts:
     [{id, content, mood, created_at, similarity}, ...]
```

**User isolation is enforced at the SQL level:** `WHERE user_id = :user_id` — retrieved reflections can never cross user boundaries.

---

## Context injection (smart prompts)

### Where is it implemented?

`services/journal.py` → `get_smart_prompts(db, user_id, content)` (lines ~251–283)

### Full flow

```
User clicks "✦ Refine with what I've written"
  │
  POST /entries/prompts/smart  { content: "..." }
  │
  └── get_smart_prompts(db, user_id, content)
        │
        ├── 1. semantic_search(db, user_id, query=content, limit=3)
        │      Retrieves 3 most similar past entries
        │
        ├── 2. build_llm_context(db, user_id)      [services/onboarding.py]
        │      Returns formatted text block:
        │        "User Goals:\n- Career: ...\nCurrent Stressors:\n- ..."
        │
        └── 3. generate_smart_prompts(current_content, similar_entries, onboarding_context)
                  [services/ai_prompts.py]
                  │
                  Builds prompt:
                  "=== User context ===\n{onboarding_context}\n
                   === What the user just wrote ===\n{current_content}\n
                   === 3 similar past entries ===\n
                   --- Past entry 1 (Oct 15, 2026 [anxious]) ---\n{content[:400]}\n
                   ..."
                  │
                  Claude Haiku 4.5 → 4 follow-up questions as JSON array
                  │
                  Returns: {prompts: [...], similar_count: 3, source: "ai"}
```

### SMART_SYSTEM_PROMPT (in `services/ai_prompts.py`)

Key constraints in the prompt:
- "At least 1 question must directly follow up on something specific they wrote TODAY"
- "If similar past entries exist, at least 1 must reference a pattern or contrast between today and the past"
- JSON array output format: `["Question 1?", "Question 2?", "Question 3?", "Question 4?"]`

---

## Dashboard prompts (no RAG)

`services/journal.py` → `get_dashboard_prompts()` calls `generate_dashboard_prompts()` in `services/ai_prompts.py`.

Uses only: last 3 entries (chronological, no similarity search) + `build_llm_context()` output.

**Intentionally avoids RAG for cost and speed** — the dashboard loads on every page view.

---

## What the RAG pipeline does NOT do

- **No chunking** — each journal entry is one document. No sub-entry splitting.
- **No reranking** — pure cosine similarity, no cross-encoder or MMR.
- **No hybrid search** — no BM25 or keyword fallback.
- **No source attribution in UI** — similar entry IDs are returned in the API response (`similar_count`) but not shown to the user.
- **No backfill job** — entries created before OpenAI key was configured have `embedding IS NULL` and never appear in search.
- **No caching of query embeddings** — every smart prompt call re-embeds the current entry text.

---

## Where to add the next RAG feature

To retrieve historical context in the chatbot (Phase 3), the flow will be:

```
User message → semantic_search(db, user_id, query=message, limit=5)
             → structured DB query for active tasks + calendar events
             → inject both into LLM prompt
```

Reuse `semantic_search()` from `services/journal.py` directly — it already handles user isolation, Postgres detection, and fallback.

Retrieved entries include `id` — use it to link suggestions back to the original entry so users can verify context.
