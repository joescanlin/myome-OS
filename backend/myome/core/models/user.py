"""User model"""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from myome.core.database import Base
from myome.core.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from myome.core.models.health_profile import HealthProfile
    from myome.core.models.device import Device


class User(Base, UUIDMixin, TimestampMixin):
    """User account model"""
    
    __tablename__ = "users"
    
    # Authentication
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Profile
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    biological_sex: Mapped[Optional[str]] = mapped_column(
        Enum("male", "female", "other", name="biological_sex_enum"),
        nullable=True,
    )
    
    # Settings
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    units_system: Mapped[str] = mapped_column(
        Enum("metric", "imperial", name="units_system_enum"),
        default="metric",
    )
    
    # Privacy settings (JSONB for flexibility)
    privacy_settings: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
    )
    
    # Relationships
    health_profile: Mapped[Optional["HealthProfile"]] = relationship(
        "HealthProfile",
        back_populates="user",
        uselist=False,
    )
    devices: Mapped[list["Device"]] = relationship(
        "Device",
        back_populates="user",
    )
    
    def __repr__(self) -> str:
        return f"<User {self.email}>"
    
    @property
    def full_name(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email.split("@")[0]
    
    @property
    def age(self) -> Optional[int]:
        if self.date_of_birth:
            today = date.today()
            return (
                today.year
                - self.date_of_birth.year
                - (
                    (today.month, today.day)
                    < (self.date_of_birth.month, self.date_of_birth.day)
                )
            )
        return None
