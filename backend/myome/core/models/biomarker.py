"""Biomarker definitions and readings"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from myome.core.database import Base
from myome.core.models.mixins import TimestampMixin, UUIDMixin


class BiomarkerDefinition(Base, UUIDMixin, TimestampMixin):
    """Definition of a biomarker with reference ranges"""
    
    __tablename__ = "biomarker_definitions"
    
    # Identification
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Units
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Reference ranges (can be age/sex adjusted via JSONB)
    reference_range_low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reference_range_high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    optimal_range_low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    optimal_range_high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Age/sex-adjusted ranges
    adjusted_ranges: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
    )
    
    # Clinical interpretation
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    high_interpretation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    low_interpretation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # LOINC code for interoperability
    loinc_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)


class BiomarkerReading(Base, UUIDMixin):
    """Individual biomarker reading from lab or device"""
    
    __tablename__ = "biomarker_readings"
    
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    biomarker_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("biomarker_definitions.id"),
        index=True,
    )
    
    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    
    # Value
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Flags
    is_abnormal: Mapped[Optional[bool]] = mapped_column(nullable=True)
    flag: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # L, H, LL, HH
    
    # Source
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # lab, device, manual
    lab_panel_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
