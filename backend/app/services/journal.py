import logging

from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.models.journal import JournalEntry
from app.schemas.journal import JournalEntryCreate, JournalEntryUpdate
from app.config import settings
from app.services.ai_prompts import prompt_generator
from app.services.embeddings import embedding_service

logger = logging.getLogger(__name__)


# ── Mood-based reflection prompts ─────────────────────────────────────────────
# Each key maps to the 4 reflection questions shown on the new-entry form.
# Ordering matches: q_what_happened, q_how_felt, q_learned, q_improve_tomorrow.
# TODO: Replace with RAG / LLM-generated prompts in a future iteration.

MOOD_PROMPTS: dict[str, list[str]] = {
    "excited": [
        "What has you buzzing with excitement right now?",
        "How did this excitement shape your interactions today?",
        "How are you turning this energy into meaningful action?",
        "What could go wrong, and how will you stay grounded?",
    ],
    "happy": [
        "What specific moment made you feel most alive today?",
        "How did your happiness show up in how you treated others?",
        "What's one thing you want to hold onto from this feeling?",
        "What can you do to create more moments like this?",
    ],
    "calm": [
        "What brought you to this place of stillness today?",
        "How did your sense of calm shape your decisions?",
        "What habits or practices are supporting this peace of mind?",
        "What clarity do you want to carry forward from today?",
    ],
    "neutral": [
        "What stood out most from today, even if nothing dramatic happened?",
        "What were you going through the motions on — and why?",
        "What would have made today feel more alive or intentional?",
        "What small shift could make tomorrow feel more meaningful?",
    ],
    "anxious": [
        "What specific thoughts or situations triggered your anxiety today?",
        "What's one small thing within your control that you can address?",
        "How did your body respond, and what did it need from you?",
        "What would you tell a close friend feeling exactly this way?",
    ],
    "sad": [
        "What loss or disappointment are you sitting with today?",
        "Who or what brought you even a small moment of comfort?",
        "What do you need most right now — rest, connection, or something else?",
        "What would healing look like for you in the days ahead?",
    ],
    "frustrated": [
        "What situation pushed against your values or expectations today?",
        "What part of this is truly within your control?",
        "What would a completely different perspective on this look like?",
        "What needs to change — externally, or in how you're responding?",
    ],
}

DEFAULT_PROMPTS = [
    "What happened today that you want to remember?",
    "How are you feeling, and what's driving that feeling?",
    "What's one thing you learned or noticed about yourself?",
    "What do you want to do differently tomorrow?",
]


def create_entry(db: Session, data: JournalEntryCreate, user_id: str) -> JournalEntry:
    entry = JournalEntry(
        **data.model_dump(),
        user_id=user_id,
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    _store_embedding(db, entry)
    return entry


def get_entry(db: Session, entry_id: str, user_id: str) -> JournalEntry | None:
    """Return an entry only if it belongs to user_id — prevents cross-user access."""
    return (
        db.query(JournalEntry)
        .filter(JournalEntry.id == entry_id, JournalEntry.user_id == user_id)
        .first()
    )


def get_entries(db: Session, user_id: str, skip: int = 0, limit: int = 20) -> tuple[list[JournalEntry], int]:
    base = db.query(JournalEntry).filter(JournalEntry.user_id == user_id)
    total = base.with_entities(func.count(JournalEntry.id)).scalar()
    entries = (
        base
        .order_by(JournalEntry.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return entries, total


def update_entry(db: Session, entry_id: str, data: JournalEntryUpdate, user_id: str) -> JournalEntry | None:
    entry = get_entry(db, entry_id, user_id)
    if not entry:
        return None
    # model_dump(exclude_unset=True) only touches fields the caller explicitly sent
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    entry.updated_by = user_id
    db.commit()
    db.refresh(entry)
    _store_embedding(db, entry)
    return entry


def delete_entry(db: Session, entry_id: str, user_id: str) -> bool:
    entry = get_entry(db, entry_id, user_id)
    if not entry:
        return False
    db.delete(entry)
    db.commit()
    return True


def get_reflection_prompts(db: Session, user_id: str) -> dict:
    """Return reflection questions tailored to this user's recent journal history.

    Strategy (in priority order):
    1. AI-generated — uses the Anthropic API to produce personalised questions
       grounded in the user's last few entries.  Requires ANTHROPIC_API_KEY.
    2. Mood heuristic — if AI is unavailable, fall back to the static
       MOOD_PROMPTS table keyed on the user's most recent mood.
    3. Generic defaults — used when neither AI nor a mood is available
       (e.g. brand-new users who haven't written anything yet).
    """
    # Fetch the user's most recent entries for AI context
    recent_entries = (
        db.query(JournalEntry)
        .filter(JournalEntry.user_id == user_id)
        .order_by(JournalEntry.created_at.desc())
        .limit(prompt_generator.MAX_CONTEXT_ENTRIES)
        .all()
    )

    # Determine current mood from the latest entry that has one set
    last_mooded = next(
        (e for e in recent_entries if e.mood),
        None,
    )
    mood = last_mooded.mood if last_mooded else None

    # 1. Try AI generation
    if settings.anthropic_api_key:
        prompts = prompt_generator.generate(recent_entries, current_mood=mood)
        return {"mood_context": mood, "prompts": prompts, "source": "ai"}

    # 2. Fall back to mood heuristic
    if mood and mood in MOOD_PROMPTS:
        return {"mood_context": mood, "prompts": MOOD_PROMPTS[mood], "source": "heuristic"}

    # 3. Generic defaults
    return {"mood_context": mood, "prompts": DEFAULT_PROMPTS, "source": "default"}


# ── Embedding helpers ─────────────────────────────────────────────────────

def _store_embedding(db: Session, entry: JournalEntry) -> None:
    """Generate and persist an embedding for the given entry.

    Uses a raw SQL UPDATE so the vector column (Postgres-only) doesn't need to
    be declared in the SQLAlchemy model — which keeps local SQLite dev working.
    Silently skips on SQLite or when OPENAI_API_KEY is not set.
    """
    if db.bind.dialect.name != "postgresql":  # type: ignore[union-attr]
        return

    entry_text = embedding_service.build_entry_text(entry)
    vector = embedding_service.generate(entry_text)
    if vector is None:
        return

    vec_str = embedding_service.format_for_sql(vector)
    try:
        db.execute(
            text(
                "UPDATE journal_entries "
                "SET embedding = CAST(:vec AS vector) "
                "WHERE id = :id"
            ),
            {"vec": vec_str, "id": entry.id},
        )
        db.commit()
    except Exception:
        logger.exception("Failed to store embedding for entry %s", entry.id)
        db.rollback()


def semantic_search(
    db: Session,
    user_id: str,
    query: str,
    limit: int = 5,
) -> list[dict]:
    """Return entries semantically similar to *query*, ranked by cosine distance.

    Returns a list of dicts with keys: id, content, mood, created_at, similarity.
    Returns an empty list if:
      - Not on Postgres (SQLite local dev)
      - OPENAI_API_KEY not set
      - No entries have been embedded yet
    """
    if db.bind.dialect.name != "postgresql":  # type: ignore[union-attr]
        return []

    query_vec = embedding_service.generate(query)
    if query_vec is None:
        return []

    vec_str = embedding_service.format_for_sql(query_vec)
    rows = db.execute(
        text(
            "SELECT id, content, mood, created_at, "
            "       1 - (embedding <-> CAST(:vec AS vector)) AS similarity "
            "FROM journal_entries "
            "WHERE user_id = :user_id AND embedding IS NOT NULL "
            "ORDER BY embedding <-> CAST(:vec AS vector) "
            "LIMIT :limit"
        ),
        {"vec": vec_str, "user_id": user_id, "limit": limit},
    ).fetchall()

    return [
        {
            "id": row.id,
            "content": row.content,
            "mood": row.mood,
            "created_at": row.created_at,
            "similarity": round(float(row.similarity), 4),
        }
        for row in rows
    ]


# ── Future AI service hooks ────────────────────────────────────────────────
# Add async functions here as AI features are built, e.g.:
#
# async def generate_embedding(text: str) -> list[float]: ...
# async def analyze_sentiment(text: str) -> float: ...
# async def detect_themes(text: str) -> list[str]: ...
# async def generate_reflection_prompts(entry: JournalEntry) -> list[str]: ...
# async def semantic_search(query: str, db: Session) -> list[JournalEntry]: ...
