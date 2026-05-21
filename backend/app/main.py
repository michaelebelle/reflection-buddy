import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.config import settings
from app.database import engine, Base
from app.routers import journal


def _run_column_migrations() -> None:
    """Add new columns to existing tables without touching existing data.

    SQLAlchemy's create_all() creates missing *tables* but never alters
    existing ones.  This function fills that gap for additive changes.
    Works on both SQLite (local) and PostgreSQL (production).
    """
    # Columns to add: (column_name, SQL type)
    new_columns = [
        ("created_by", "VARCHAR(100)"),
        ("updated_by", "VARCHAR(100)"),
    ]
    try:
        existing = {c["name"] for c in inspect(engine).get_columns("journal_entries")}
    except Exception:
        return  # Table not yet created; create_all below handles it

    with engine.begin() as conn:
        for col, col_type in new_columns:
            if col not in existing:
                conn.execute(text(f"ALTER TABLE journal_entries ADD COLUMN {col} {col_type}"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Step 1: create any brand-new tables (idempotent).
    # TODO: Replace with Alembic migrations before multi-instance deployment.
    Base.metadata.create_all(bind=engine)
    # Step 2: add any new columns that create_all won't add to existing tables.
    _run_column_migrations()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="A personal reflection journal API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes — registered first so they take priority over the static catch-all
app.include_router(journal.router, prefix="/api/v1")


@app.get("/health", tags=["meta"])
def health_check():
    return {"status": "ok", "app": settings.app_name}


# ── Static frontend (production only) ─────────────────────────────────────
# When deployed to Vercel, the frontend is served through FastAPI itself.
# In local development, open frontend/index.html directly — no server needed.
if os.getenv("VERCEL"):
    from fastapi.staticfiles import StaticFiles

    _frontend_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
    )
    # html=True makes FastAPI serve index.html for any path not matched above,
    # which is what a single-page app needs.
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
