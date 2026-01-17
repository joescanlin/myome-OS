"""Authentication routes"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from myome.api.auth import (
    TokenPair,
    create_token_pair,
    get_password_hash,
    verify_password,
    verify_refresh_token,
)
from myome.api.deps.db import DbSession
from myome.core.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    """User registration request"""

    email: EmailStr
    password: str
    first_name: str | None = None
    last_name: str | None = None


class LoginRequest(BaseModel):
    """Login request"""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Token refresh request"""

    refresh_token: str


@router.post("/register", response_model=TokenPair)
async def register(
    request: RegisterRequest,
    session: DbSession,
) -> TokenPair:
    """Register a new user"""
    # Check if email already exists
    existing = await session.execute(select(User).where(User.email == request.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    user = User(
        email=request.email,
        hashed_password=get_password_hash(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Return tokens
    return create_token_pair(user.id)


@router.post("/login", response_model=TokenPair)
async def login(
    request: LoginRequest,
    session: DbSession,
) -> TokenPair:
    """Login with email and password"""
    # Find user
    result = await session.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    return create_token_pair(user.id)


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(
    request: RefreshRequest,
    session: DbSession,
) -> TokenPair:
    """Refresh access token using refresh token"""
    try:
        user_id = verify_refresh_token(request.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Verify user still exists and is active
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled",
        )

    return create_token_pair(user.id)
