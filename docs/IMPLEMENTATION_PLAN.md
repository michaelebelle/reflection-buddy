# IMPLEMENTATION_PLAN.md
> Phased implementation for the Reflection Buddy weekly planner evolution
> Written: 2026-11-01 | Status: Phase 0 complete

---

## Guiding principles

- One working feature at a time. Verify before moving on.
- Reuse existing auth, DB, RAG, and prompt infrastructure.
- No LangChain, LangGraph, or orchestration frameworks.
- New features degrade gracefully — the existing journal always works.
- Trace every request: UI → auth → retrieval → LLM → persistence → UI.

---

## Phase 0 — Documentation and codebase inspection ✅ DONE

**Goal:** Understand exactly what exists before changing anything.

- [x] Read all existing models, services, routers, and frontend code
- [x] Document architecture (`ARCHITECTURE.md`)
- [x] Document RAG pipeline (`RAG.md`)
- [x] Document auth (`AUTH.md`)
- [x] Document data model — existing + proposed (`DATA_MODEL.md`)
- [x] Write implementation plan (`IMPLEMENTATION_PLAN.md`)
- [x] Define evaluation strategy (`EVALUATIONS.md`)
- [x] Record key decisions (`DECISIONS.md`)

**Stop point:** Present findings. Do not write feature code.

---

## Phase 1 — Calendar events and task management (no AI)

**Goal:** Basic CRUD for calendar events and tasks. Fully usable without AI.

### 1a — Backend: calendar events

1. Add `CalendarEvent` model to `backend/app/models/calendar.py`
2. Add `CalendarEventCreate`, `CalendarEventUpdate`, `CalendarEventResponse` schemas
3. Add `services/calendar.py` — create, list (by week), get, update, delete
4. Add `routers/calendar.py` — `GET/POST /calendar/events`, `GET/PUT/DELETE /calendar/events/{id}`, `GET /calendar/events/week?start=YYYY-MM-DD`
5. Register router in `main.py`, add migration in `_run_column_migrations()`
6. Test with curl: CRUD round-trip, user isolation

### 1b — Backend: tasks

1. Add `Task` model to `backend/app/models/task.py`
2. Add task schemas (`TaskCreate`, `TaskUpdate`, `TaskResponse`)
3. Add `services/tasks.py` — create, list (by status), get, update, delete
4. Add `routers/tasks.py` — `GET/POST /tasks`, `GET/PUT/DELETE /tasks/{id}`
5. Register router in `main.py`, add migration
6. Test with curl: create task, update status, list by status

### 1c — Frontend: weekly calendar view

1. Add `view-calendar` section to `index.html` (Mon–Sun grid, time slots)
2. Add "Calendar" nav button in header
3. Implement `showCalendar()` in `app.js`
4. Implement `loadWeekEvents(weekStart)` → `GET /calendar/events/week?start=`
5. Render events as colored blocks in the correct time slot
6. Click empty slot → open create-event modal
7. Click event → open edit/delete modal
8. Category color coding (work=blue, fitness=green, personal=purple, etc.)
9. Week navigation (prev/next buttons, "Today" button)
10. Support 15/30/60-minute slot intervals

### 1d — Frontend: tasks panel

1. Add `view-tasks` section to `index.html` (or sidebar panel on dashboard)
2. Add "Tasks" nav or dashboard section showing active tasks
3. Implement create/edit/complete task UI
4. Filter by status: todo, in_progress, completed
5. Connect to task API endpoints

**Verify Phase 1:** Create a calendar event, create a task, complete the task, navigate weeks, verify user isolation (two accounts can't see each other's data).

---

## Phase 2 — Chatbot interface with intent detection

**Goal:** A simple chat UI that interprets user messages and proposes calendar events or tasks for confirmation — no auto-mutations.

### 2a — Backend: chat endpoint

Add `POST /api/v1/chat` in `routers/chat.py`:

```
Input: { message: str, context_date: str (YYYY-MM-DD) }
Output: { reply: str, proposed_actions: [...], request_id: str }
```

Implementation in `services/chat.py`:

1. **Intent detection** — one structured LLM call:
   ```
   System: "Classify this message as one of: reflection | task_creation | calendar_planning | other.
            If task or calendar, extract: title, description, date, time range, category."
   User: "{message}"
   Output: JSON with {intent, extracted_fields}
   ```
2. **If reflection:** generate a conversational reply using recent entries (no mutations proposed)
3. **If task_creation:** validate extracted fields, return `proposed_actions: [{type: "create_task", ...}]`
4. **If calendar_planning:** validate date/time, check for conflicts in DB, return `proposed_actions: [{type: "create_event", ...}]`
5. **If other:** simple conversational reply

Keep intent handling in one function. No agent loop.

### 2b — Confirmation flow

Frontend receives `proposed_actions`. User sees "I can do this:" with Accept / Reject buttons.

Only on Accept: call the relevant CRUD endpoint (`POST /tasks` or `POST /calendar/events`).

**Verify Phase 2:** Type "I need to work on my ML report tomorrow from 10am to 12pm." → see proposed calendar event → accept → event appears on calendar.

---

## Phase 3 — RAG-powered suggestions in chat

**Goal:** Chatbot retrieves relevant past reflections to provide context-aware suggestions.

### 3a — Connect semantic_search to chat

In `services/chat.py`, after intent detection:

1. Call `semantic_search(db, user_id, query=message, limit=5)` from `services/journal.py`
2. Also query structured DB: `get_active_tasks(user_id)`, `get_week_events(user_id, date)`
3. Inject both into the LLM prompt:

```
=== Your active tasks ===
- [id] Write ML report documentation (due: 2026-11-05)
- [id] ChangeIQ: frontend enhancements

=== Relevant past reflections ===
--- Oct 28 [anxious] (similarity: 0.87) ---
"Working on ChangeIQ today. Got the Success Prediction backend done but still need docs..."

=== Calendar this week ===
- Mon 2pm–4pm: Deep work (work)
- Wed 10am–noon: ML study

User said: "{message}"
```

4. Return source IDs in the response so UI can link back to original entries.

### 3b — Task suggestion from reflection

When intent = reflection:
1. Retrieve similar past entries
2. Check if any mention unfinished work that isn't already a tracked task
3. Propose: "You mentioned needing to write ChangeIQ docs in a past entry — want to track that?"

**Verify Phase 3:** Write a reflection referencing a past project → see chatbot surface relevant past context → decline the suggestion → no task created.

---

## Phase 4 — End-of-day review

**Goal:** Structured end-of-day flow that connects planned activities, actual completion, and reflection.

Add `POST /api/v1/chat/eod-review`:
1. Fetch today's calendar events
2. Fetch active tasks due today
3. Build a review prompt: "You planned to X from Y to Z. How did it go?"
4. User responds in chat
5. Chatbot proposes: mark task complete / move to tomorrow / add follow-up / save reflection
6. User confirms each action

No automatic mutations — every proposed change requires explicit acceptance.

**Verify Phase 4:** Complete end-of-day flow: see day's events, respond to each, accept one task completion, reject one move to tomorrow — verify DB state matches choices.

---

## Phase 5 — Evaluation and refinement

**Goal:** Measure actual behavior, find gaps, improve prompts.

1. Build 10–20 representative test cases (see `EVALUATIONS.md`)
2. Run retrieval evaluation: does semantic_search return relevant entries?
3. Run intent detection evaluation: does the chat endpoint correctly classify messages?
4. Run planning evaluation: does the calendar proposal have valid times, no conflicts?
5. Inspect AI operation logs for validation failures and low-acceptance-rate suggestions
6. Tune system prompts and retrieval parameters based on findings

---

## What NOT to build in MVP

- Drag-and-drop calendar
- Recurring events
- External calendar sync (Google Calendar, etc.)
- Autonomous scheduling agent (LLM decides and executes without confirmation)
- Real-time collaboration
- Push notifications / reminders
- Complex recurrence rules
- Habit management outside onboarding (separate screen)
