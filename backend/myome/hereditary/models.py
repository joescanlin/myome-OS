"""Hereditary module database models"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, String, Text,
    JSON, Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from myome.core.database import Base
from myome.core.models.mixins import TimestampMixin


class FamilyRelationship(str, Enum):
    """Family relationship types"""
    MOTHER = "mother"
    FATHER = "father"
    MATERNAL_GRANDMOTHER = "maternal_grandmother"
    MATERNAL_GRANDFATHER = "maternal_grandfather"
    PATERNAL_GRANDMOTHER = "paternal_grandmother"
    PATERNAL_GRANDFATHER = "paternal_grandfather"
    SISTER = "sister"
    BROTHER = "brother"
    DAUGHTER = "daughter"
    SON = "son"
    MATERNAL_AUNT = "maternal_aunt"
    MATERNAL_UNCLE = "maternal_uncle"
    PATERNAL_AUNT = "paternal_aunt"
    PATERNAL_UNCLE = "paternal_uncle"
    OTHER = "other"


# Genetic relatedness coefficients
RELATEDNESS_COEFFICIENTS = {
    FamilyRelationship.MOTHER: 0.5,
    FamilyRelationship.FATHER: 0.5,
    FamilyRelationship.SISTER: 0.5,
    FamilyRelationship.BROTHER: 0.5,
    FamilyRelationship.DAUGHTER: 0.5,
    FamilyRelationship.SON: 0.5,
    FamilyRelationship.MATERNAL_GRANDMOTHER: 0.25,
    FamilyRelationship.MATERNAL_GRANDFATHER: 0.25,
    FamilyRelationship.PATERNAL_GRANDMOTHER: 0.25,
    FamilyRelationship.PATERNAL_GRANDFATHER: 0.25,
    FamilyRelationship.MATERNAL_AUNT: 0.25,
    FamilyRelationship.MATERNAL_UNCLE: 0.25,
    FamilyRelationship.PATERNAL_AUNT: 0.25,
    FamilyRelationship.PATERNAL_UNCLE: 0.25,
    FamilyRelationship.OTHER: 0.125,
}


class FamilyMember(Base, TimestampMixin):
    """
    Family member health record.
    
    Stores health information about relatives for hereditary risk calculation.
    Can be populated from:
    - Manual questionnaire entry
    - Uploaded medical documents
    - Connected family member's Myome account
    """
    __tablename__ = "family_members"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Relationship info
    relationship: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Demographics
    birth_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    death_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    biological_sex: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_living: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Health conditions (JSON array of condition objects)
    # Format: [{"condition": "type_2_diabetes", "onset_age": 55, "current": true}]
    conditions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Biomarker snapshots (JSON object with biomarker values)
    # Format: {"ldl": {"value": 188, "unit": "mg/dL", "age_at_measurement": 58}}
    biomarkers: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Medications (JSON array)
    medications: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Lifestyle factors
    smoking_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    alcohol_use: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Cause of death if deceased
    cause_of_death: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    age_at_death: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Connected Myome user (if family member has their own account)
    connected_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    
    # Data source tracking
    data_source: Mapped[str] = mapped_column(String(50), default="manual")  # manual, document, connected
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    @property
    def relatedness(self) -> float:
        """Get genetic relatedness coefficient"""
        try:
            rel = FamilyRelationship(self.relationship)
            return RELATEDNESS_COEFFICIENTS.get(rel, 0.125)
        except ValueError:
            return 0.125
    
    @property
    def current_age(self) -> Optional[int]:
        """Calculate current age or age at death"""
        if not self.birth_year:
            return None
        if self.death_year:
            return self.death_year - self.birth_year
        return datetime.now().year - self.birth_year


class FamilyDocument(Base, TimestampMixin):
    """
    Uploaded family medical document.
    
    Stores original document and extracted data.
    """
    __tablename__ = "family_documents"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    family_member_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("family_members.id"), nullable=True
    )
    
    # Document info
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)  # lab_report, discharge_summary, prescription
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Extraction status
    extraction_status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, processing, completed, failed
    extracted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Extracted data (JSON)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    extraction_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # User verification
    user_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class WatchlistItem(Base, TimestampMixin):
    """
    Personalized health watchlist item based on family history.
    
    Tracks biomarkers with family-calibrated alert thresholds.
    """
    __tablename__ = "watchlist_items"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Biomarker info
    biomarker: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Alert threshold
    alert_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    alert_direction: Mapped[str] = mapped_column(String(20), default="above")  # above, below
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Family context
    family_context: Mapped[str] = mapped_column(Text, nullable=False)
    contributing_family_member_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("family_members.id"), nullable=True
    )
    
    # Priority and recommendations
    priority: Mapped[str] = mapped_column(String(20), default="medium")  # critical, high, medium, low
    recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    trigger_count: Mapped[int] = mapped_column(Integer, default=0)


class HereditaryArtifactRecord(Base, TimestampMixin):
    """
    Record of generated hereditary artifacts.
    
    Stores metadata about generated artifacts for tracking and retrieval.
    """
    __tablename__ = "hereditary_artifacts"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Artifact info
    artifact_version: Mapped[str] = mapped_column(String(20), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Data coverage
    data_start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    data_end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Privacy settings used
    privacy_settings: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Storage
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_encrypted: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Signature
    signature: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    
    # Sharing
    shared_with: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # List of recipient info
