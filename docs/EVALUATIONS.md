# EVALUATIONS.md
> Evaluation strategy and future test harness — as of 2026-11-01

---

## Philosophy

Build the application so that evaluations can be added incrementally without refactoring. The goal is not a perfect evaluation framework — it's enough structure to detect regressions and improve over time.

**Start with representative examples. Measure real outputs. Improve prompts based on evidence, not intuition.**

---

## What to capture per AI operation

Every AI call should eventually emit a structured trace. For now, capture via structured logging. Use `request_id` (UUID, generated per request) to correlate retrieval + generation + user response.

```python
{
    "request_id": "uuid",
    "user_id": "uuid",           # hashed or pseudonymized for logs
    "timestamp": "ISO-8601",
    "operation": "smart_prompts | dashboard_prompts | intent_detection | eod_review",
    "prompt_version": "v1",      # increment when prompts change
    "model": "claude-haiku-4-5",
    "retrieval_query": "...",
    "retrieved_doc_ids": ["id1", "id2"],
    "retrieved_similarities": [0.87, 0.81],
    "structured_output": {...},  # parsed LLM JSON
    "validation_errors": [],
    "latency_ms": 340,
    "user_accepted": null        # set when user accepts/rejects a proposal
}
```

**Privacy note:** Do not log full journal content in traces. Log IDs and similarity scores only. Keep traces access-controlled (same auth as journal entries).

---

## Evaluation targets

### 1. Retrieval evaluation

**Question:** Does `semantic_search()` return entries that are actually relevant?

**Metrics:**
- **Recall@K:** Given a known relevant entry exists, is it in the top K results?
- **Precision@K:** Of the top K results, how many are actually relevant?
- **Context relevance:** Does the retrieved context meaningfully improve the LLM output?

**Test case format:**
```json
{
    "id": "retrieval-001",
    "query": "feeling overwhelmed at work",
    "user_id": "test_user_1",
    "expected_entry_ids": ["entry_abc", "entry_def"],
    "k": 3
}
```

**How to run:** Pre-seed test entries, run `semantic_search()`, check overlap with `expected_entry_ids`.

**Current state:** No test cases exist. Start with 5–10 hand-written examples using real reflection content.

---

### 2. Intent detection evaluation (Phase 2+)

**Question:** Does the chat endpoint correctly classify user messages?

**Metrics:**
- Classification accuracy (reflection vs. task vs. calendar vs. other)
- Extraction precision (correct title, date, time parsed from message)
- False positive rate (valid message misclassified as task creation)

**Test case format:**
```json
{
    "id": "intent-001",
    "message": "Tomorrow I need to work on my ML report from 10am to noon.",
    "expected_intent": "calendar_planning",
    "expected_fields": {
        "title": "ML report",
        "date": "2026-11-02",
        "start_time": "10:00",
        "end_time": "12:00"
    }
}
```

**How to run:** Call `classify_intent()` service function directly with test messages, compare to expected.

---

### 3. Planning evaluation (Phase 2+)

**Question:** Are proposed calendar events valid and useful?

**Metrics:**
- Structural validity rate: Does the proposed action have all required fields?
- Conflict-free rate: Does the proposal avoid times already blocked?
- User acceptance rate: Tracked via `user_accepted` in operation logs

**Test case format:**
```json
{
    "id": "plan-001",
    "message": "Schedule 2 hours for ChangeIQ work tomorrow afternoon",
    "existing_events": [
        {"date": "2026-11-02", "start_time": "13:00", "end_time": "15:00", "title": "Meeting"}
    ],
    "expected_proposal": {
        "date": "2026-11-02",
        "start_time_not_in": ["13:00", "14:00"],
        "duration_hours": 2
    }
}
```

---

### 4. Reflection quality evaluation (Phase 3+)

**Question:** Do the reflection questions and chatbot responses use retrieved context appropriately?

**Metrics:**
- Context grounding: Does the response reference retrieved entries?
- Fabrication rate: Does the response claim things not in entries or user context?
- Appropriate uncertainty: Does the model say "I notice you've mentioned X before" rather than "You always struggle with X"?

**Test case format:**
```json
{
    "id": "reflect-001",
    "current_entry": "Had a rough day at work...",
    "retrieved_entries": [
        {"id": "entry_abc", "content": "Mentioned conflict with manager last week"}
    ],
    "expected_behaviors": [
        "references retrieved entry",
        "asks follow-up about manager situation",
        "does not fabricate specific details"
    ],
    "prohibited_behaviors": [
        "ignores retrieved context entirely",
        "claims user said something not in entry"
    ]
}
```

**How to evaluate:** Human review for now. LLM-as-judge for scale (use a separate, stronger model to assess).

---

## Minimal test harness for Phase 5

```
tests/
  evals/
    data/
      retrieval_cases.json
      intent_cases.json
      planning_cases.json
    eval_retrieval.py   # runs semantic_search against cases, reports Recall@K
    eval_intent.py      # runs intent detection against cases, reports accuracy
    run_all.py          # runs all evals, prints summary table
```

**How to run:**
```bash
cd backend
python -m tests.evals.run_all
```

**Output format:**
```
Retrieval:     Recall@3 = 0.70  Precision@3 = 0.60  (7/10 cases)
Intent:        Accuracy = 0.85  (17/20 cases)
Planning:      Valid = 0.90  Conflict-free = 0.95  (18/20 cases)
```

---

## What to measure first (Phase 5 priority)

1. **Smart prompts context relevance** — most immediately useful, uses existing RAG
2. **Intent detection accuracy** — gates the whole chatbot feature
3. **User acceptance rate** — from operation logs, no extra setup needed

---

## What to avoid

- Building an elaborate evaluation platform before having features to evaluate.
- Using embedding similarity as a proxy for semantic correctness (circular — you'd be evaluating the embedding model with itself).
- Evaluating on the same data the prompts were tuned against.
- Treating LLM-as-judge scores as ground truth without spot-checking.
