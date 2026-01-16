"""User management routes"""

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

from myome.api.deps.auth import CurrentUser
from myome.api.deps.db import DbSession
from myome.core.models import HealthProfile

router = APIRouter(prefix="/users", tags=["Users"])


class UserRead(BaseModel):
    """User response"""
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    
    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """User update request"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class HealthProfileUpdate(BaseModel):
    """Health profile update request"""
    height_cm: Optional[float] = None
    baseline_weight_kg: Optional[float] = None
    ethnicity: Optional[list[str]] = None
    smoking_status: Optional[str] = None
    alcohol_frequency: Optional[str] = None
    exercise_frequency: Optional[str] = None
    diet_type: Optional[str] = None
    typical_sleep_hours: Optional[float] = None


@router.get("/me", response_model=UserRead)
async def get_current_user(user: CurrentUser) -> UserRead:
    """Get current user profile"""
    return UserRead.model_validate(user)


@router.patch("/me", response_model=UserRead)
async def update_current_user(
    update: UserUpdate,
    user: CurrentUser,
    session: DbSession,
) -> UserRead:
    """Update current user profile"""
    update_data = update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await session.commit()
    await session.refresh(user)
    
    return UserRead.model_validate(user)


@router.get("/me/health-profile")
async def get_health_profile(
    user: CurrentUser,
    session: DbSession,
) -> dict:
    """Get user's health profile"""
    if user.health_profile:
        return {
            "height_cm": user.health_profile.height_cm,
            "baseline_weight_kg": user.health_profile.baseline_weight_kg,
            "ethnicity": user.health_profile.ethnicity,
            "smoking_status": user.health_profile.smoking_status,
            "alcohol_frequency": user.health_profile.alcohol_frequency,
            "exercise_frequency": user.health_profile.exercise_frequency,
            "diet_type": user.health_profile.diet_type,
            "typical_sleep_hours": user.health_profile.typical_sleep_hours,
        }
    return {}


@router.put("/me/health-profile")
async def update_health_profile(
    profile_data: HealthProfileUpdate,
    user: CurrentUser,
    session: DbSession,
) -> dict:
    """Create or update user's health profile"""
    if user.health_profile:
        # Update existing
        update_data = profile_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user.health_profile, field, value)
    else:
        # Create new
        profile = HealthProfile(
            user_id=user.id,
            **profile_data.model_dump(exclude_unset=True),
        )
        session.add(profile)
    
    await session.commit()
    
    return {"status": "updated"}
