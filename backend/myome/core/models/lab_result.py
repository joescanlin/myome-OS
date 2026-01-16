"""Lab panel and result models"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from myome.core.database import Base
from myome.core.models.mixins import TimestampMixin, UUIDMixin


class LabPanel(Base, UUIDMixin, TimestampMixin):
    """Lab test panel (e.g., Complete Blood Count, Lipid Panel)"""
    
    __tablename__ = "lab_panels"
    
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    
    # Panel identification
    panel_name: Mapped[str] = mapped_column(String(200), nullable=False)
    panel_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Collection info
    collection_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    fasting: Mapped[Optional[bool]] = mapped_column(nullable=True)
    
    # Lab info
    lab_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    lab_accession_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ordering_provider: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Raw report (for OCR'd documents)
    raw_report: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
    )
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    results: Mapped[list["LabResult"]] = relationship(
        "LabResult",
        back_populates="panel",
    )


class LabResult(Base, UUIDMixin):
    """Individual lab test result within a panel"""
    
    __tablename__ = "lab_results"
    
    panel_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("lab_panels.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    
    # Test identification
    test_name: Mapped[str] = mapped_column(String(200), nullable=False)
    test_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    loinc_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Result
    value: Mapped[str] = mapped_column(String(100), nullable=False)  # String to handle non-numeric
    value_numeric: Mapped[Optional[float]] = mapped_column(nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Reference range
    reference_range: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reference_low: Mapped[Optional[float]] = mapped_column(nullable=True)
    reference_high: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Flags
    flag: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_abnormal: Mapped[Optional[bool]] = mapped_column(nullable=True)
    
    # Relationships
    panel: Mapped["LabPanel"] = relationship("LabPanel", back_populates="results")
