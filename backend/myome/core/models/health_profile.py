"""Health profile model for baseline health information"""

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from myome.core.database import Base
from myome.core.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from myome.core.models.user import User


class HealthProfile(Base, UUIDMixin, TimestampMixin):
    """Extended health profile with baseline measurements and history"""

    __tablename__ = "health_profiles"

    # Foreign key
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
    )

    # Anthropometric baselines
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Ethnicity (for population-adjusted risk scores)
    ethnicity: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
    )

    # Medical history (structured)
    medical_conditions: Mapped[dict] = mapped_column(
        JSONB,
        default=list,
        server_default="[]",
    )
    medications: Mapped[dict] = mapped_column(
        JSONB,
        default=list,
        server_default="[]",
    )
    allergies: Mapped[dict] = mapped_column(
        JSONB,
        default=list,
        server_default="[]",
    )

    # Family history (structured for hereditary analysis)
    family_history: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
    )

    # Lifestyle baselines
    smoking_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    alcohol_frequency: Mapped[str | None] = mapped_column(String(50), nullable=True)
    exercise_frequency: Mapped[str | None] = mapped_column(String(50), nullable=True)
    diet_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Sleep baseline
    typical_sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    typical_bedtime: Mapped[str | None] = mapped_column(String(10), nullable=True)
    typical_wake_time: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="health_profile")

    def __repr__(self) -> str:
        return f"<HealthProfile user_id={self.user_id}>"
