from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.journal import JournalEntry
from app.schemas.journal import JournalEntryCreate, JournalEntryUpdate
from app.config import settings


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
    return entry


def delete_entry(db: Session, entry_id: str, user_id: str) -> bool:
    entry = get_entry(db, entry_id, user_id)
    if not entry:
        return False
    db.delete(entry)
    db.commit()
    return True


def get_reflection_prompts(db: Session, user_id: str) -> dict:
    """Return reflection questions tailored to *this user's* most recent mood.

    Queries the user's latest entry that has a mood set and picks the matching
    prompt set from MOOD_PROMPTS.  Falls back to DEFAULT_PROMPTS when no
    mooded entry exists yet (e.g. first-time user).

    TODO: Replace heuristic lookup with RAG — embed the last N entries,
    retrieve semantically similar past moments, and generate prompts with
    an LLM grounded in the user's own history.
    """
    last_mooded = (
        db.query(JournalEntry)
        .filter(JournalEntry.user_id == user_id, JournalEntry.mood.isnot(None))
        .order_by(JournalEntry.created_at.desc())
        .first()
    )
    mood = last_mooded.mood if last_mooded else None
    prompts = MOOD_PROMPTS.get(mood, DEFAULT_PROMPTS) if mood else DEFAULT_PROMPTS
    return {"mood_context": mood, "prompts": prompts}


# ── Future AI service hooks ────────────────────────────────────────────────
# Add async functions here as AI features are built, e.g.:
#
# async def generate_embedding(text: str) -> list[float]: ...
# async def analyze_sentiment(text: str) -> float: ...
# async def detect_themes(text: str) -> list[str]: ...
# async def generate_reflection_prompts(entry: JournalEntry) -> list[str]: ...
# async def semantic_search(query: str, db: Session) -> list[JournalEntry]: ...
