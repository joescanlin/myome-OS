"""Hereditary artifact and family health API routes"""

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select

from myome.api.deps.auth import CurrentUser
from myome.api.deps.db import DbSession
from myome.hereditary.artifact import HereditaryArtifact, PrivacySettings
from myome.hereditary.document_processor import FamilyDocumentProcessor
from myome.hereditary.models import FamilyMember, WatchlistItem
from myome.hereditary.risk import (
    ComprehensiveRiskAssessment,
    FamilyOutcome,
    FamilyRiskCalculator,
)
from myome.hereditary.watchlist import FamilyHistoryPDFGenerator, WatchlistGenerator

router = APIRouter(prefix="/hereditary", tags=["Hereditary Health"])


# ============== Pydantic Schemas ==============


class PrivacySettingsRequest(BaseModel):
    """Privacy settings for artifact generation"""

    exclude_categories: list[str] = []
    anonymize_location: bool = True
    include_interpretations: bool = True


class GenerateArtifactRequest(BaseModel):
    """Request to generate hereditary artifact"""

    privacy_settings: PrivacySettingsRequest
    start_date: datetime | None = None
    end_date: datetime | None = None


class FamilyMemberCreate(BaseModel):
    """Create a new family member"""

    relationship: str
    name: str | None = None
    birth_year: int | None = None
    death_year: int | None = None
    biological_sex: str | None = None
    is_living: bool = True
    conditions: list[dict] | None = None
    biomarkers: dict | None = None
    medications: list[dict] | None = None
    smoking_status: str | None = None
    alcohol_use: str | None = None
    cause_of_death: str | None = None
    notes: str | None = None


class FamilyMemberUpdate(BaseModel):
    """Update a family member"""

    name: str | None = None
    birth_year: int | None = None
    death_year: int | None = None
    biological_sex: str | None = None
    is_living: bool | None = None
    conditions: list[dict] | None = None
    biomarkers: dict | None = None
    medications: list[dict] | None = None
    smoking_status: str | None = None
    alcohol_use: str | None = None
    cause_of_death: str | None = None
    notes: str | None = None


class ConditionInput(BaseModel):
    """Input for single condition risk calculation"""

    condition: str
    family_outcomes: list[dict]


# ============== Family Member Routes ==============


@router.get("/family")
async def list_family_members(
    user: CurrentUser,
    session: DbSession,
) -> list[dict]:
    """List all family members"""
    result = await session.execute(
        select(FamilyMember).where(FamilyMember.user_id == user.id)
    )
    members = result.scalars().all()

    return [
        {
            "id": m.id,
            "relationship": m.relationship,
            "name": m.name,
            "birth_year": m.birth_year,
            "death_year": m.death_year,
            "biological_sex": m.biological_sex,
            "is_living": m.is_living,
            "conditions": m.conditions,
            "biomarkers": m.biomarkers,
            "medications": m.medications,
            "smoking_status": m.smoking_status,
            "cause_of_death": m.cause_of_death,
            "age_at_death": m.age_at_death,
            "current_age": m.current_age,
            "relatedness": m.relatedness,
            "data_source": m.data_source,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in members
    ]


@router.post("/family")
async def create_family_member(
    member: FamilyMemberCreate,
    user: CurrentUser,
    session: DbSession,
) -> dict:
    """Create a new family member"""
    fm = FamilyMember(
        id=str(uuid4()),
        user_id=user.id,
        relationship=member.relationship,
        name=member.name,
        birth_year=member.birth_year,
        death_year=member.death_year,
        biological_sex=member.biological_sex,
        is_living=member.is_living,
        conditions=member.conditions,
        biomarkers=member.biomarkers,
        medications=member.medications,
        smoking_status=member.smoking_status,
        alcohol_use=member.alcohol_use,
        cause_of_death=member.cause_of_death,
        age_at_death=(
            member.death_year - member.birth_year
            if member.death_year and member.birth_year
            else None
        ),
        notes=member.notes,
        data_source="manual",
    )

    session.add(fm)
    await session.commit()
    await session.refresh(fm)

    return {
        "id": fm.id,
        "relationship": fm.relationship,
        "name": fm.name,
        "relatedness": fm.relatedness,
        "created": True,
    }


@router.patch("/family/{member_id}")
async def update_family_member(
    member_id: str,
    update: FamilyMemberUpdate,
    user: CurrentUser,
    session: DbSession,
) -> dict:
    """Update a family member"""
    result = await session.execute(
        select(FamilyMember).where(
            FamilyMember.id == member_id,
            FamilyMember.user_id == user.id,
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=404, detail="Family member not found")

    # Update fields
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(member, field, value)

    # Recalculate age at death if needed
    if member.death_year and member.birth_year:
        member.age_at_death = member.death_year - member.birth_year

    await session.commit()

    return {"id": member.id, "updated": True}


@router.delete("/family/{member_id}")
async def delete_family_member(
    member_id: str,
    user: CurrentUser,
    session: DbSession,
) -> dict:
    """Delete a family member"""
    result = await session.execute(
        select(FamilyMember).where(
            FamilyMember.id == member_id,
            FamilyMember.user_id == user.id,
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=404, detail="Family member not found")

    await session.delete(member)
    await session.commit()

    return {"id": member_id, "deleted": True}


# ============== Document Processing Routes ==============


@router.post("/family/{member_id}/document")
async def upload_family_document(
    member_id: str,
    user: CurrentUser,
    session: DbSession,
    document_type: str = Query(default="lab_report"),
    age_at_document: int | None = Query(default=None),
    document_text: str = Query(
        ..., description="Extracted text from document (OCR if needed)"
    ),
) -> dict:
    """
    Process uploaded family medical document

    In production, this would accept file upload and perform OCR.
    For now, accepts pre-extracted text.
    """
    # Verify family member exists
    result = await session.execute(
        select(FamilyMember).where(
            FamilyMember.id == member_id,
            FamilyMember.user_id == user.id,
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=404, detail="Family member not found")

    # Process document
    processor = FamilyDocumentProcessor()
    extraction = await processor.process_document(
        text=document_text,
        document_type=document_type,
        relative_age_at_document=age_at_document,
    )

    # Convert to family member data format
    processor.convert_to_family_member_data(
        extraction=extraction,
        relationship=member.relationship,
        age_at_document=age_at_document,
    )

    # Merge with existing member data
    if extraction.biomarkers:
        existing_biomarkers = member.biomarkers or {}
        for b in extraction.biomarkers:
            existing_biomarkers[b.name] = {
                "value": b.value,
                "unit": b.unit,
                "age_at_measurement": age_at_document,
                "is_abnormal": b.is_abnormal,
            }
        member.biomarkers = existing_biomarkers

    if extraction.conditions:
        existing_conditions = member.conditions or []
        for c in extraction.conditions:
            # Check if condition already exists
            existing_names = [ec.get("condition") for ec in existing_conditions]
            if c.name not in existing_names:
                existing_conditions.append(
                    {
                        "condition": c.name,
                        "onset_age": None,
                        "current": c.status == "active",
                    }
                )
        member.conditions = existing_conditions

    if extraction.medications:
        existing_meds = member.medications or []
        for m in extraction.medications:
            existing_names = [em.get("name") for em in existing_meds]
            if m.name not in existing_names:
                existing_meds.append(
                    {
                        "name": m.name,
                        "dosage": m.dosage,
                    }
                )
        member.medications = existing_meds

    member.data_source = "document"
    await session.commit()

    return {
        "member_id": member_id,
        "extraction_confidence": extraction.overall_confidence,
        "biomarkers_found": len(extraction.biomarkers),
        "conditions_found": len(extraction.conditions),
        "medications_found": len(extraction.medications),
        "extracted_data": {
            "biomarkers": [
                {"name": b.name, "value": b.value, "unit": b.unit}
                for b in extraction.biomarkers
            ],
            "conditions": [c.name for c in extraction.conditions],
            "medications": [m.name for m in extraction.medications],
        },
    }


# ============== Watchlist Routes ==============


@router.get("/watchlist")
async def get_watchlist(
    user: CurrentUser,
    session: DbSession,
) -> list[dict]:
    """Get personalized health watchlist based on family history"""
    # Get family members
    result = await session.execute(
        select(FamilyMember).where(FamilyMember.user_id == user.id)
    )
    members = result.scalars().all()

    if not members:
        return []

    # Calculate user age
    user_age = 35  # Default, should come from user profile
    if user.date_of_birth:
        user_age = datetime.now().year - user.date_of_birth.year

    # Generate watchlist
    generator = WatchlistGenerator(user_age)
    watchlist = generator.generate_watchlist(list(members))

    return [
        {
            "biomarker": item.biomarker,
            "display_name": item.display_name,
            "unit": item.unit,
            "alert_threshold": item.alert_threshold,
            "alert_direction": item.alert_direction,
            "priority": item.priority,
            "family_context": item.family_context,
            "recommendation": item.recommendation,
        }
        for item in watchlist
    ]


@router.post("/watchlist/regenerate")
async def regenerate_watchlist(
    user: CurrentUser,
    session: DbSession,
) -> dict:
    """Regenerate watchlist and save to database"""
    # Get family members
    result = await session.execute(
        select(FamilyMember).where(FamilyMember.user_id == user.id)
    )
    members = result.scalars().all()

    if not members:
        return {"items_created": 0}

    # Calculate user age
    user_age = 35
    if user.date_of_birth:
        user_age = datetime.now().year - user.date_of_birth.year

    # Generate watchlist
    generator = WatchlistGenerator(user_age)
    watchlist = generator.generate_watchlist(list(members))

    # Delete existing watchlist items
    existing = await session.execute(
        select(WatchlistItem).where(WatchlistItem.user_id == user.id)
    )
    for item in existing.scalars().all():
        await session.delete(item)

    # Create new items
    for config in watchlist:
        item = WatchlistItem(
            id=str(uuid4()),
            user_id=user.id,
            biomarker=config.biomarker,
            display_name=config.display_name,
            alert_threshold=config.alert_threshold,
            alert_direction=config.alert_direction,
            unit=config.unit,
            family_context=config.family_context,
            priority=config.priority,
            recommendation=config.recommendation,
            contributing_family_member_id=config.contributing_family_member_id,
        )
        session.add(item)

    await session.commit()

    return {"items_created": len(watchlist)}


# ============== Risk Assessment Routes ==============


@router.get("/risk")
async def get_comprehensive_risk(
    user: CurrentUser,
    session: DbSession,
) -> dict:
    """Get comprehensive family-calibrated risk assessment"""
    # Get family members
    result = await session.execute(
        select(FamilyMember).where(FamilyMember.user_id == user.id)
    )
    members = result.scalars().all()

    # Convert to FamilyOutcome objects
    outcomes = []
    for member in members:
        if not member.conditions:
            continue

        for cond in member.conditions:
            outcomes.append(
                FamilyOutcome(
                    condition=cond.get("condition", ""),
                    onset_age=cond.get("onset_age"),
                    relatedness=member.relatedness,
                    relationship=member.relationship,
                )
            )

    # Calculate user age
    user_age = 35
    if user.date_of_birth:
        user_age = datetime.now().year - user.date_of_birth.year

    # Run comprehensive assessment
    assessment = ComprehensiveRiskAssessment(user_age)
    risks = assessment.assess_all_risks(outcomes)

    # Get priority conditions
    priority_conditions = assessment.get_priority_conditions(risks)

    return {
        "user_age": user_age,
        "family_members_analyzed": len(members),
        "conditions_analyzed": len(risks),
        "risks": {
            condition: {
                "population_risk": round(risk.population_risk * 100, 1),
                "family_calibrated_risk": round(risk.family_calibrated_risk * 100, 1),
                "risk_increase_factor": round(risk.risk_increase_factor, 2),
                "confidence_interval": [
                    round(risk.confidence_interval[0] * 100, 1),
                    round(risk.confidence_interval[1] * 100, 1),
                ],
                "contributing_factors": risk.contributing_factors,
                "recommendation": risk.recommendation,
            }
            for condition, risk in risks.items()
        },
        "priority_conditions": [
            {
                "condition": risk.condition,
                "risk_increase_factor": round(risk.risk_increase_factor, 2),
                "recommendation": risk.recommendation,
            }
            for risk in priority_conditions
        ],
    }


@router.post("/risk/calculate")
async def calculate_single_risk(
    input: ConditionInput,
    user: CurrentUser,
) -> dict:
    """Calculate risk for a specific condition"""
    # Convert input to FamilyOutcome objects
    outcomes = [
        FamilyOutcome(
            condition=o.get("condition", input.condition),
            onset_age=o.get("onset_age"),
            relatedness=o.get("relatedness", 0.5),
            relationship=o.get("relationship", "unknown"),
        )
        for o in input.family_outcomes
    ]

    # Calculate user age
    user_age = 35
    if user.date_of_birth:
        user_age = datetime.now().year - user.date_of_birth.year

    calculator = FamilyRiskCalculator(input.condition)
    result = calculator.calculate_risk(outcomes, user_age)

    return {
        "condition": input.condition,
        "population_risk_pct": round(result.population_risk * 100, 1),
        "family_calibrated_risk_pct": round(result.family_calibrated_risk * 100, 1),
        "risk_increase_factor": round(result.risk_increase_factor, 2),
        "confidence_interval_pct": [
            round(result.confidence_interval[0] * 100, 1),
            round(result.confidence_interval[1] * 100, 1),
        ],
        "contributing_factors": result.contributing_factors,
        "recommendation": result.recommendation,
    }


# ============== Family History Document Routes ==============


@router.get("/history/summary")
async def get_family_history_summary(
    user: CurrentUser,
    session: DbSession,
) -> dict:
    """Get family health history summary document"""
    # Get family members
    result = await session.execute(
        select(FamilyMember).where(FamilyMember.user_id == user.id)
    )
    members = list(result.scalars().all())

    # Calculate user age
    user_age = 35
    if user.date_of_birth:
        user_age = datetime.now().year - user.date_of_birth.year

    # Generate watchlist
    generator = WatchlistGenerator(user_age)
    watchlist = generator.generate_watchlist(members)

    # Generate summary
    pdf_gen = FamilyHistoryPDFGenerator()
    summary = pdf_gen.generate_summary(
        user_profile={
            "name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
            "age": user_age,
            "biological_sex": user.biological_sex,
        },
        family_members=members,
        watchlist=watchlist,
    )

    return summary


# ============== Artifact Routes ==============


@router.post("/artifact/generate")
async def generate_artifact(
    request: GenerateArtifactRequest,
    user: CurrentUser,
    session: DbSession,
) -> dict:
    """Generate a new hereditary health artifact"""
    # Get family members to include
    result = await session.execute(
        select(FamilyMember).where(FamilyMember.user_id == user.id)
    )
    members = list(result.scalars().all())

    privacy = PrivacySettings(
        exclude_categories=request.privacy_settings.exclude_categories,
        anonymize_location=request.privacy_settings.anonymize_location,
        include_interpretations=request.privacy_settings.include_interpretations,
    )

    artifact = HereditaryArtifact(user.id)
    data = await artifact.generate(
        privacy_settings=privacy,
        start_date=request.start_date,
        end_date=request.end_date,
        family_members=members,
    )

    return {
        "artifact_id": artifact.artifact_id,
        "size_bytes": artifact.size_bytes,
        "family_members_included": len(members),
        "data": data,
    }


@router.get("/artifact/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    user: CurrentUser,
    session: DbSession,
) -> dict:
    """Retrieve a generated artifact"""
    raise HTTPException(
        status_code=501,
        detail="Artifact storage not yet implemented. Use /artifact/generate for on-demand generation.",
    )
