from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.journal import JournalEntry
from app.schemas.journal import JournalEntryCreate, JournalEntryUpdate


def create_entry(db: Session, data: JournalEntryCreate) -> JournalEntry:
    entry = JournalEntry(**data.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_entry(db: Session, entry_id: str) -> JournalEntry | None:
    return db.query(JournalEntry).filter(JournalEntry.id == entry_id).first()


def get_entries(db: Session, skip: int = 0, limit: int = 20) -> tuple[list[JournalEntry], int]:
    total = db.query(func.count(JournalEntry.id)).scalar()
    entries = (
        db.query(JournalEntry)
        .order_by(JournalEntry.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return entries, total


def update_entry(db: Session, entry_id: str, data: JournalEntryUpdate) -> JournalEntry | None:
    entry = get_entry(db, entry_id)
    if not entry:
        return None
    # model_dump(exclude_unset=True) only touches fields the caller explicitly sent
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return entry


def delete_entry(db: Session, entry_id: str) -> bool:
    entry = get_entry(db, entry_id)
    if not entry:
        return False
    db.delete(entry)
    db.commit()
    return True


# ── Future AI service hooks ────────────────────────────────────────────────
# Add async functions here as AI features are built, e.g.:
#
# async def generate_embedding(text: str) -> list[float]: ...
# async def analyze_sentiment(text: str) -> float: ...
# async def detect_themes(text: str) -> list[str]: ...
# async def generate_reflection_prompts(entry: JournalEntry) -> list[str]: ...
# async def semantic_search(query: str, db: Session) -> list[JournalEntry]: ...
