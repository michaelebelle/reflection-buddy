from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.onboarding import OnboardingCreate, OnboardingPatch, OnboardingResponse
from app.services import onboarding as onboarding_service
from app.services.auth import get_current_user

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("", response_model=OnboardingResponse, status_code=status.HTTP_201_CREATED)
def create_onboarding(
    data: OnboardingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit onboarding data. Replaces any existing onboarding for this user."""
    return onboarding_service.save_onboarding(db, user_id=current_user.id, data=data)


@router.get("", response_model=OnboardingResponse | None)
def get_onboarding(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the current user's onboarding data, or null if not yet completed."""
    return onboarding_service.get_onboarding(db, user_id=current_user.id)


@router.patch("", response_model=OnboardingResponse)
def patch_onboarding(
    data: OnboardingPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Partially update onboarding. Only the provided sections are replaced."""
    result = onboarding_service.patch_onboarding(db, user_id=current_user.id, data=data)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Onboarding not found. Complete the full onboarding POST first.",
        )
    return result
