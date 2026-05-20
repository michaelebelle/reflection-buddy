import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routers import journal


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create tables on startup (idempotent — safe on every cold start).
    # TODO: Replace with Alembic migrations before a multi-instance deployment.
    Base.metadata.create_all(bind=engine)
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
