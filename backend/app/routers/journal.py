from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.journal import (
    JournalEntryCreate,
    JournalEntryUpdate,
    JournalEntryResponse,
    JournalEntryList,
    PromptResponse,
    SemanticSearchResponse,
)
from app.services import journal as journal_service
from app.services.auth import get_current_user

router = APIRouter(prefix="/entries", tags=["journal"])


@router.post("", response_model=JournalEntryResponse, status_code=status.HTTP_201_CREATED)
def create_entry(
    entry: JournalEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return journal_service.create_entry(db, entry, user_id=current_user.id)


@router.get("/search", response_model=SemanticSearchResponse)
def search_entries(
    q: str = Query(..., min_length=1, description="Natural-language search query"),
    limit: int = Query(5, ge=1, le=20, description="Max results to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Semantic search across the user's journal entries.

    Uses vector cosine similarity — finds entries that *mean* something similar
    to the query, not just entries that contain the same keywords.

    Examples:
      - "times I felt proud of myself"
      - "conflicts with my manager"
      - "moments of clarity or insight"
    """
    results = journal_service.semantic_search(db, user_id=current_user.id, query=q, limit=limit)
    return SemanticSearchResponse(query=q, results=results)


@router.get("/prompts", response_model=PromptResponse)
def get_reflection_prompts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return 4 reflection questions tailored to the user's most recent mood.

    Registered before /{entry_id} so FastAPI doesn't treat 'prompts' as an ID.
    """
    return journal_service.get_reflection_prompts(db, user_id=current_user.id)


@router.get("", response_model=JournalEntryList)
def list_entries(
    skip: int = Query(0, ge=0, description="Number of entries to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max entries to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entries, total = journal_service.get_entries(db, user_id=current_user.id, skip=skip, limit=limit)
    return JournalEntryList(entries=entries, total=total, skip=skip, limit=limit)


@router.get("/{entry_id}", response_model=JournalEntryResponse)
def get_entry(
    entry_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = journal_service.get_entry(db, entry_id, user_id=current_user.id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.put("/{entry_id}", response_model=JournalEntryResponse)
def update_entry(
    entry_id: str,
    data: JournalEntryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = journal_service.update_entry(db, entry_id, data, user_id=current_user.id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    entry_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not journal_service.delete_entry(db, entry_id, user_id=current_user.id):
        raise HTTPException(status_code=404, detail="Entry not found")
