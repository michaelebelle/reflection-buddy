"""
Vercel serverless entry point.

Vercel looks for an ASGI/WSGI callable named `app` in this file.
We add the backend directory to sys.path so the existing `app` package
imports work unchanged, then re-export the FastAPI instance.
"""
import sys
import os

# Make `backend/` importable so `from app.xxx import ...` resolves correctly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app  # noqa: F401, E402  — Vercel needs this name
