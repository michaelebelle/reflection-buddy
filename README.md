# Reflection Buddy

A minimal personal journal app with a calm, focused UI. Built with FastAPI and vanilla JS on a clean foundation designed to grow into an AI-powered reflection tool.

---

## Quick Start

```
Terminal 1: start the backend API
Terminal 2: open the frontend in a browser
```

---

## 1. Install & Run the Backend

### Prerequisites
- Python 3.11 or newer

### Setup

```bash
# Navigate to the backend directory
cd backend

# Create a virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Copy the example env file (SQLite works out of the box — no config needed)
cp .env.example .env
```

### Run

```bash
# From the backend/ directory, with .venv activated
uvicorn app.main:app --reload
```

The API starts at **http://localhost:8000**

| URL | What you get |
|-----|-------------|
| `http://localhost:8000/health` | Health check |
| `http://localhost:8000/docs` | Interactive API explorer (Swagger UI) |
| `http://localhost:8000/redoc` | Alternative API docs |

### Database

No setup needed. The database is SQLite — a single file (`backend/journal.db`) that is created automatically the first time you start the server. To reset it, delete `journal.db` and restart the server.

To switch to PostgreSQL later: update `DATABASE_URL` in `backend/.env` — no code changes needed:

```
DATABASE_URL=postgresql://user:password@localhost:5432/reflection_buddy
```

Then `pip install psycopg2-binary` and run `uvicorn` again.

---

## 2. Run the Frontend

No build step required.

```bash
# From the project root, just open the file:
open frontend/index.html           # macOS
start frontend/index.html          # Windows
xdg-open frontend/index.html       # Linux
```

Or drag `frontend/index.html` into any browser window.

> **The backend must be running first.** The frontend calls `http://localhost:8000/api/v1` by default. If the server is not running, the dashboard shows an error state with a "Try again" button.

---

## API Reference

| Method   | Endpoint               | Description                      |
|----------|------------------------|----------------------------------|
| `GET`    | `/health`              | Health check                     |
| `POST`   | `/api/v1/entries`      | Create a new journal entry       |
| `GET`    | `/api/v1/entries`      | List entries (paginated)         |
| `GET`    | `/api/v1/entries/{id}` | Get a single entry               |
| `PUT`    | `/api/v1/entries/{id}` | Update an entry                  |
| `DELETE` | `/api/v1/entries/{id}` | Delete an entry                  |

### Pagination

```
GET /api/v1/entries?skip=0&limit=20
```

### Example: create an entry

```bash
curl -X POST http://localhost:8000/api/v1/entries \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Today was a good day.",
    "mood": "happy",
    "energy_level": 8,
    "q_what_happened": "Shipped a feature I had been working on for a week.",
    "q_learned": "Breaking problems into smaller pieces really helps."
  }'
```

---

## Project Structure

```
reflection-buddy/
│
├── backend/
│   ├── app/
│   │   ├── main.py            ← FastAPI app — CORS, startup, route registration
│   │   ├── config.py          ← Settings class (reads from .env via pydantic-settings)
│   │   ├── database.py        ← SQLAlchemy engine, session factory, Base class
│   │   │
│   │   ├── models/
│   │   │   └── journal.py     ← JournalEntry ORM model (future AI columns commented in)
│   │   │
│   │   ├── schemas/
│   │   │   └── journal.py     ← Pydantic request/response schemas
│   │   │
│   │   ├── routers/
│   │   │   └── journal.py     ← Route handlers (thin — delegate to services)
│   │   │
│   │   └── services/
│   │       └── journal.py     ← All business logic and DB queries
│   │                            (future AI service hooks are stubbed here)
│   │
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── index.html             ← Single-page app shell with all three views
│   ├── css/
│   │   └── styles.css         ← Minimal custom CSS (range slider, toast, mood pills)
│   │                            Tailwind CDN handles everything else
│   └── js/
│       └── app.js             ← All frontend logic: API calls, state, rendering
│
└── README.md
```

### Why this structure?

- **`routers/`** only validate input and call services — no DB logic lives there
- **`services/`** own all queries, making it easy to drop in async AI calls alongside existing DB operations
- **`models/`** have future AI columns commented in — one uncomment + migration away
- **`schemas/`** separate from models so API shape and DB shape can evolve independently
- **Frontend** is three views in one HTML file, switched by JS — no framework needed at this scale

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and adjust as needed.

| Variable       | Default                      | Description                          |
|----------------|------------------------------|--------------------------------------|
| `APP_NAME`     | `Reflection Buddy`           | Shown in API docs and health check   |
| `DEBUG`        | `false`                      | Enable debug mode                    |
| `DATABASE_URL` | `sqlite:///./journal.db`     | Any SQLAlchemy-compatible URL        |

---

## Future AI Architecture

The codebase is structured so each AI feature slots in cleanly. Here's the roadmap and where each feature connects:

### Embeddings + Semantic Search
- Uncomment `embedding` column in `backend/app/models/journal.py`
- Add `generate_embedding(text)` to `backend/app/services/journal.py`
- Call it after `db.commit()` in `create_entry()`
- Add a `GET /api/v1/entries/search?q=...` route
- For production: migrate to PostgreSQL + pgvector extension

### Sentiment Analysis
- Uncomment `sentiment_score` column in the model
- Run a lightweight model (e.g. `transformers` pipeline) or call an LLM API in the service layer
- Surface a subtle indicator in the entry card

### Theme & Mood Detection
- Uncomment `themes` column (stored as JSON)
- Call an LLM after save, store structured output
- Future: use themes to generate personalized prompts

### AI-Generated Reflection Prompts
- Uncomment `generated_prompts` column
- Before the user writes: fetch prompts from a `/api/v1/prompts` endpoint
- Generate using RAG over the user's past entries for personalization

### RAG Over Past Entries
- Requires embeddings (above)
- At query time: embed the current entry, find top-k similar past entries, inject as context
- The `services/journal.py` file is the right place for the retrieval logic

### Agentic Workflows
- Weekly summaries, habit nudges, mood pattern alerts
- FastAPI background tasks (`BackgroundTasks`) for lightweight work
- Celery or a cron-triggered endpoint for heavier scheduled workflows

All placeholder columns and service stubs are already in the code — search for `Future AI` to find every hook.
