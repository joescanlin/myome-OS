"""Authentication and authorization utilities"""

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel

from myome.core.config import settings
from myome.core.exceptions import AuthenticationException

# JWT settings
ALGORITHM = "HS256"


class TokenPayload(BaseModel):
    """JWT token payload"""

    sub: str  # user_id
    exp: datetime
    type: str  # "access" or "refresh"


class TokenPair(BaseModel):
    """Access and refresh token pair"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(user_id: str) -> str:
    """Create access token"""
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = TokenPayload(
        sub=user_id,
        exp=expire,
        type="access",
    )
    return jwt.encode(payload.model_dump(), settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Create refresh token"""
    expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    payload = TokenPayload(
        sub=user_id,
        exp=expire,
        type="refresh",
    )
    return jwt.encode(payload.model_dump(), settings.secret_key, algorithm=ALGORITHM)


def create_token_pair(user_id: str) -> TokenPair:
    """Create access and refresh token pair"""
    return TokenPair(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


def decode_token(token: str) -> TokenPayload:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        payload_dict = cast(dict[str, Any], payload)
        return TokenPayload(**payload_dict)
    except JWTError as e:
        raise AuthenticationException(f"Invalid token: {e}")


def verify_access_token(token: str) -> str:
    """Verify access token and return user_id"""
    payload = decode_token(token)

    if payload.type != "access":
        raise AuthenticationException("Invalid token type")

    if payload.exp < datetime.now(UTC):
        raise AuthenticationException("Token expired")

    return payload.sub


def verify_refresh_token(token: str) -> str:
    """Verify refresh token and return user_id"""
    payload = decode_token(token)

    if payload.type != "refresh":
        raise AuthenticationException("Invalid token type")

    if payload.exp < datetime.now(UTC):
        raise AuthenticationException("Token expired")

    return payload.sub
