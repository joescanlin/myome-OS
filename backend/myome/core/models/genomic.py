"""Genomic data models"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from myome.core.database import Base
from myome.core.models.mixins import TimestampMixin, UUIDMixin


class GenomicVariant(Base, UUIDMixin, TimestampMixin):
    """Genetic variant (SNP, indel, etc.)"""
    
    __tablename__ = "genomic_variants"
    
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    
    # Variant identification
    rsid: Mapped[Optional[str]] = mapped_column(String(20), index=True, nullable=True)
    chromosome: Mapped[str] = mapped_column(String(5), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_allele: Mapped[str] = mapped_column(String(1000), nullable=False)
    alternate_allele: Mapped[str] = mapped_column(String(1000), nullable=False)
    
    # Genotype
    genotype: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g., "A/G"
    zygosity: Mapped[str] = mapped_column(String(20), nullable=False)  # homozygous, heterozygous
    
    # Gene association
    gene: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    consequence: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Clinical significance (ClinVar)
    clinical_significance: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    clinvar_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Associated conditions
    associated_conditions: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
        server_default="{}",
    )
    
    # Annotations
    annotations: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
    )
    
    # Source
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # 23andme, nebula, clinical


class PolygeniScore(Base, UUIDMixin, TimestampMixin):
    """Polygenic risk score for a condition"""
    
    __tablename__ = "polygenic_scores"
    
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    
    # Condition
    condition: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    condition_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Score
    score: Mapped[float] = mapped_column(Float, nullable=False)
    percentile: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Risk interpretation
    risk_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    relative_risk: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Score details
    num_variants: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Population reference
    reference_population: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Source and methodology
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    methodology: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
