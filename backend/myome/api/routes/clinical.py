"""Clinical integration API routes"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query

from myome.api.deps.auth import CurrentUser
from myome.api.deps.db import DbSession
from myome.clinical.fhir.resources import FHIRResourceGenerator
from myome.clinical.reports.generator import PhysicianReportGenerator

router = APIRouter(prefix="/clinical", tags=["Clinical Integration"])


@router.get("/report")
async def generate_physician_report(
    user: CurrentUser,
    session: DbSession,
    report_date: datetime | None = Query(default=None),
    months: int = Query(default=3, ge=1, le=12),
) -> dict:
    """Generate comprehensive physician report"""
    generator = PhysicianReportGenerator(user.id)
    report = await generator.generate_report(report_date, months)
    return report


@router.get("/report/pdf")
async def generate_physician_report_pdf(
    user: CurrentUser,
    session: DbSession,
    report_date: datetime | None = Query(default=None),
    months: int = Query(default=3, ge=1, le=12),
):
    """Generate physician report as PDF (placeholder)"""
    # In production, use reportlab or weasyprint to generate PDF
    raise HTTPException(
        status_code=501,
        detail="PDF generation not yet implemented. Use /report for JSON format.",
    )


@router.get("/fhir/Patient")
async def get_fhir_patient(
    user: CurrentUser,
) -> dict:
    """Get patient data as FHIR Patient resource"""
    generator = FHIRResourceGenerator(user.id)
    return generator.create_patient(
        {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "date_of_birth": (
                user.date_of_birth.isoformat() if user.date_of_birth else None
            ),
            "biological_sex": user.biological_sex,
        }
    )


@router.get("/fhir/Bundle")
async def get_fhir_bundle(
    user: CurrentUser,
    session: DbSession,
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    include_hr: bool = Query(
        default=True, description="Include heart rate observations"
    ),
    include_glucose: bool = Query(
        default=True, description="Include glucose observations"
    ),
    include_hrv: bool = Query(default=True, description="Include HRV observations"),
) -> dict:
    """Export health data as FHIR Bundle"""
    from myome.analytics.data_loader import TimeSeriesLoader

    if end is None:
        end = datetime.now(UTC)
    if start is None:
        start = end - timedelta(days=7)

    loader = TimeSeriesLoader(user.id)
    fhir = FHIRResourceGenerator(user.id)

    resources = []

    # Add patient
    resources.append(
        fhir.create_patient(
            {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "date_of_birth": (
                    user.date_of_birth.isoformat() if user.date_of_birth else None
                ),
                "biological_sex": user.biological_sex,
            }
        )
    )

    # Add heart rate observations
    if include_hr:
        hr_df = await loader.load_heart_rate(start, end, resample="1H")
        for idx, row in hr_df.iterrows():
            if not row.isna().all():
                resources.append(
                    fhir.create_heart_rate_observation(
                        int(row["heart_rate_bpm"]),
                        idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx,
                    )
                )

    # Add glucose observations
    if include_glucose:
        glucose_df = await loader.load_glucose(start, end, resample="1H")
        for idx, row in glucose_df.iterrows():
            if not row.isna().all():
                resources.append(
                    fhir.create_glucose_observation(
                        float(row["glucose_mg_dl"]),
                        idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx,
                    )
                )

    # Add HRV observations
    if include_hrv:
        hrv_df = await loader.load_hrv(start, end, resample="1H")
        for idx, row in hrv_df.iterrows():
            if "sdnn_ms" in row and not row.isna().all():
                resources.append(
                    fhir.create_hrv_observation(
                        float(row["sdnn_ms"]),
                        idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx,
                    )
                )

    return fhir.create_bundle(resources[:100])  # Limit to 100 resources


@router.get("/fhir/DiagnosticReport")
async def get_fhir_diagnostic_report(
    user: CurrentUser,
    session: DbSession,
    months: int = Query(default=3, ge=1, le=12),
) -> dict:
    """Generate FHIR DiagnosticReport from physician report"""
    report_gen = PhysicianReportGenerator(user.id)
    fhir_gen = FHIRResourceGenerator(user.id)

    report = await report_gen.generate_report(months_lookback=months)

    # Create some sample observations from the report
    observations = []

    # Add cardiovascular observations if available
    cardio = report.get("detailed_analysis", {}).get("cardiovascular", {})
    if cardio.get("resting_heart_rate"):
        rhr = cardio["resting_heart_rate"]
        observations.append(
            fhir_gen.create_heart_rate_observation(
                int(rhr.get("average", 0)),
                datetime.now(UTC),
            )
        )

    if cardio.get("hrv_analysis") and cardio["hrv_analysis"].get("average_sdnn"):
        observations.append(
            fhir_gen.create_hrv_observation(
                float(cardio["hrv_analysis"]["average_sdnn"]),
                datetime.now(UTC),
            )
        )

    # Add metabolic observations if available
    metabolic = report.get("detailed_analysis", {}).get("metabolic", {})
    if metabolic.get("glucose_metrics"):
        glucose = metabolic["glucose_metrics"]
        observations.append(
            fhir_gen.create_glucose_observation(
                float(glucose.get("mean", 0)),
                datetime.now(UTC),
            )
        )

    return fhir_gen.create_diagnostic_report(report, observations)


@router.get("/fhir/Observation/{observation_type}")
async def get_fhir_observations(
    observation_type: str,
    user: CurrentUser,
    session: DbSession,
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    limit: int = Query(default=50, le=200),
) -> dict:
    """Get observations of a specific type as FHIR resources"""
    from myome.analytics.data_loader import TimeSeriesLoader

    if end is None:
        end = datetime.now(UTC)
    if start is None:
        start = end - timedelta(days=7)

    loader = TimeSeriesLoader(user.id)
    fhir = FHIRResourceGenerator(user.id)

    observations = []

    if observation_type == "heart-rate":
        df = await loader.load_heart_rate(start, end)
        for idx, row in df.head(limit).iterrows():
            if not row.isna().all():
                observations.append(
                    fhir.create_heart_rate_observation(
                        int(row["heart_rate_bpm"]),
                        idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx,
                    )
                )

    elif observation_type == "glucose":
        df = await loader.load_glucose(start, end)
        for idx, row in df.head(limit).iterrows():
            if not row.isna().all():
                observations.append(
                    fhir.create_glucose_observation(
                        float(row["glucose_mg_dl"]),
                        idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx,
                    )
                )

    elif observation_type == "hrv":
        df = await loader.load_hrv(start, end)
        for idx, row in df.head(limit).iterrows():
            if "sdnn_ms" in row and not row.isna().all():
                observations.append(
                    fhir.create_hrv_observation(
                        float(row["sdnn_ms"]),
                        idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx,
                    )
                )

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown observation type: {observation_type}. Supported: heart-rate, glucose, hrv",
        )

    return fhir.create_bundle(observations)
