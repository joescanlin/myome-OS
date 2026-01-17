"""User schemas"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema"""

    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    biological_sex: str | None = None
    timezone: str = "UTC"


class UserCreate(UserBase):
    """Schema for creating a user"""

    password: str = Field(..., min_length=8)


class UserRead(UserBase):
    """Schema for reading a user"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    is_active: bool
    is_verified: bool
    created_at: datetime


class UserUpdate(BaseModel):
    """Schema for updating a user"""

    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    biological_sex: str | None = None
    timezone: str | None = None
