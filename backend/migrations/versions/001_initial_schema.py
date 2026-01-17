"""Initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-01-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enable required extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")

    # Create enum types (using DO block to check if they exist first)
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE biological_sex_enum AS ENUM ('male', 'female', 'other');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE units_system_enum AS ENUM ('metric', 'imperial');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE devicetype AS ENUM (
                'smartwatch', 'fitness_tracker', 'cgm', 'smart_ring', 'smart_scale',
                'blood_pressure', 'pulse_oximeter', 'thermometer', 'sleep_tracker',
                'air_quality', 'other'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE devicevendor AS ENUM (
                'apple', 'garmin', 'fitbit', 'oura', 'whoop', 'withings',
                'dexcom', 'abbott', 'levels', 'polar', 'awair', 'eve', 'generic'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """
    )

    # Users table
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("last_name", sa.String(100), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column(
            "biological_sex",
            postgresql.ENUM(
                "male", "female", "other", name="biological_sex_enum", create_type=False
            ),
            nullable=True,
        ),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="UTC"),
        sa.Column(
            "units_system",
            postgresql.ENUM(
                "metric", "imperial", name="units_system_enum", create_type=False
            ),
            nullable=False,
            server_default="metric",
        ),
        sa.Column(
            "privacy_settings", postgresql.JSONB(), nullable=False, server_default="{}"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # Health profiles table
    op.create_table(
        "health_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("height_cm", sa.Float(), nullable=True),
        sa.Column("baseline_weight_kg", sa.Float(), nullable=True),
        sa.Column("ethnicity", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column(
            "medical_conditions",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "medications", postgresql.JSONB(), nullable=False, server_default="[]"
        ),
        sa.Column("allergies", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column(
            "family_history", postgresql.JSONB(), nullable=False, server_default="{}"
        ),
        sa.Column("smoking_status", sa.String(50), nullable=True),
        sa.Column("alcohol_frequency", sa.String(50), nullable=True),
        sa.Column("exercise_frequency", sa.String(50), nullable=True),
        sa.Column("diet_type", sa.String(50), nullable=True),
        sa.Column("typical_sleep_hours", sa.Float(), nullable=True),
        sa.Column("typical_bedtime", sa.String(10), nullable=True),
        sa.Column("typical_wake_time", sa.String(10), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # Devices table
    op.create_table(
        "devices",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "device_type",
            postgresql.ENUM(
                "smartwatch",
                "fitness_tracker",
                "cgm",
                "smart_ring",
                "smart_scale",
                "blood_pressure",
                "pulse_oximeter",
                "thermometer",
                "sleep_tracker",
                "air_quality",
                "other",
                name="devicetype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "vendor",
            postgresql.ENUM(
                "apple",
                "garmin",
                "fitbit",
                "oura",
                "whoop",
                "withings",
                "dexcom",
                "abbott",
                "levels",
                "polar",
                "awair",
                "eve",
                "generic",
                name="devicevendor",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("serial_number", sa.String(100), nullable=True),
        sa.Column("firmware_version", sa.String(50), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_connected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "api_credentials", postgresql.JSONB(), nullable=False, server_default="{}"
        ),
        sa.Column(
            "calibration_params",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "device_metadata", postgresql.JSONB(), nullable=False, server_default="{}"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_devices_user_id", "devices", ["user_id"])

    # Device readings table
    op.create_table(
        "device_readings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("device_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reading_type", sa.String(50), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("raw_data", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_device_readings_device_id", "device_readings", ["device_id"])
    op.create_index("ix_device_readings_user_id", "device_readings", ["user_id"])
    op.create_index("ix_device_readings_timestamp", "device_readings", ["timestamp"])
    op.create_index(
        "ix_device_readings_reading_type", "device_readings", ["reading_type"]
    )

    # Biomarker definitions table
    op.create_table(
        "biomarker_definitions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("reference_range_low", sa.Float(), nullable=True),
        sa.Column("reference_range_high", sa.Float(), nullable=True),
        sa.Column("optimal_range_low", sa.Float(), nullable=True),
        sa.Column("optimal_range_high", sa.Float(), nullable=True),
        sa.Column(
            "adjusted_ranges", postgresql.JSONB(), nullable=False, server_default="{}"
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("high_interpretation", sa.Text(), nullable=True),
        sa.Column("low_interpretation", sa.Text(), nullable=True),
        sa.Column("loinc_code", sa.String(20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_biomarker_definitions_code", "biomarker_definitions", ["code"])
    op.create_index(
        "ix_biomarker_definitions_category", "biomarker_definitions", ["category"]
    )

    # Biomarker readings table
    op.create_table(
        "biomarker_readings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("biomarker_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("is_abnormal", sa.Boolean(), nullable=True),
        sa.Column("flag", sa.String(10), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("lab_panel_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["biomarker_id"], ["biomarker_definitions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_biomarker_readings_user_id", "biomarker_readings", ["user_id"])
    op.create_index(
        "ix_biomarker_readings_biomarker_id", "biomarker_readings", ["biomarker_id"]
    )
    op.create_index(
        "ix_biomarker_readings_timestamp", "biomarker_readings", ["timestamp"]
    )

    # Lab panels table
    op.create_table(
        "lab_panels",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("panel_name", sa.String(200), nullable=False),
        sa.Column("panel_code", sa.String(50), nullable=True),
        sa.Column("collection_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fasting", sa.Boolean(), nullable=True),
        sa.Column("lab_name", sa.String(200), nullable=True),
        sa.Column("lab_accession_number", sa.String(100), nullable=True),
        sa.Column("ordering_provider", sa.String(200), nullable=True),
        sa.Column(
            "raw_report", postgresql.JSONB(), nullable=False, server_default="{}"
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lab_panels_user_id", "lab_panels", ["user_id"])

    # Lab results table
    op.create_table(
        "lab_results",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("panel_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("test_name", sa.String(200), nullable=False),
        sa.Column("test_code", sa.String(50), nullable=True),
        sa.Column("loinc_code", sa.String(20), nullable=True),
        sa.Column("value", sa.String(100), nullable=False),
        sa.Column("value_numeric", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("reference_range", sa.String(100), nullable=True),
        sa.Column("reference_low", sa.Float(), nullable=True),
        sa.Column("reference_high", sa.Float(), nullable=True),
        sa.Column("flag", sa.String(10), nullable=True),
        sa.Column("is_abnormal", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["panel_id"], ["lab_panels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lab_results_panel_id", "lab_results", ["panel_id"])
    op.create_index("ix_lab_results_user_id", "lab_results", ["user_id"])

    # Genomic variants table
    op.create_table(
        "genomic_variants",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("rsid", sa.String(20), nullable=True),
        sa.Column("chromosome", sa.String(5), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("reference_allele", sa.String(1000), nullable=False),
        sa.Column("alternate_allele", sa.String(1000), nullable=False),
        sa.Column("genotype", sa.String(10), nullable=False),
        sa.Column("zygosity", sa.String(20), nullable=False),
        sa.Column("gene", sa.String(50), nullable=True),
        sa.Column("consequence", sa.String(100), nullable=True),
        sa.Column("clinical_significance", sa.String(50), nullable=True),
        sa.Column("clinvar_id", sa.String(20), nullable=True),
        sa.Column(
            "associated_conditions",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "annotations", postgresql.JSONB(), nullable=False, server_default="{}"
        ),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_genomic_variants_user_id", "genomic_variants", ["user_id"])
    op.create_index("ix_genomic_variants_rsid", "genomic_variants", ["rsid"])

    # Polygenic scores table
    op.create_table(
        "polygenic_scores",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("condition", sa.String(200), nullable=False),
        sa.Column("condition_code", sa.String(50), nullable=True),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("percentile", sa.Float(), nullable=True),
        sa.Column("risk_category", sa.String(50), nullable=True),
        sa.Column("relative_risk", sa.Float(), nullable=True),
        sa.Column("num_variants", sa.Integer(), nullable=True),
        sa.Column("model_version", sa.String(50), nullable=True),
        sa.Column("reference_population", sa.String(50), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("methodology", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_polygenic_scores_user_id", "polygenic_scores", ["user_id"])
    op.create_index("ix_polygenic_scores_condition", "polygenic_scores", ["condition"])

    # Time-series tables (will be converted to hypertables)

    # Heart rate readings
    op.create_table(
        "heart_rate_readings",
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("heart_rate_bpm", sa.Integer(), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("activity_type", sa.String(50), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("timestamp", "user_id"),
    )
    op.create_index("ix_hr_user_time", "heart_rate_readings", ["user_id", "timestamp"])

    # HRV readings
    op.create_table(
        "hrv_readings",
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("sdnn_ms", sa.Float(), nullable=True),
        sa.Column("rmssd_ms", sa.Float(), nullable=True),
        sa.Column("pnn50_pct", sa.Float(), nullable=True),
        sa.Column("lf_power", sa.Float(), nullable=True),
        sa.Column("hf_power", sa.Float(), nullable=True),
        sa.Column("lf_hf_ratio", sa.Float(), nullable=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("measurement_duration_sec", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("timestamp", "user_id"),
    )
    op.create_index("ix_hrv_user_time", "hrv_readings", ["user_id", "timestamp"])

    # Glucose readings
    op.create_table(
        "glucose_readings",
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("glucose_mg_dl", sa.Float(), nullable=False),
        sa.Column("trend", sa.String(20), nullable=True),
        sa.Column("trend_rate", sa.Float(), nullable=True),
        sa.Column("is_calibrated", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("calibration_factor", sa.Float(), nullable=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("meal_context", sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("timestamp", "user_id"),
    )
    op.create_index(
        "ix_glucose_user_time", "glucose_readings", ["user_id", "timestamp"]
    )

    # Sleep sessions
    op.create_table(
        "sleep_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_sleep_minutes", sa.Integer(), nullable=False),
        sa.Column("time_in_bed_minutes", sa.Integer(), nullable=False),
        sa.Column("sleep_onset_latency_minutes", sa.Integer(), nullable=True),
        sa.Column("wake_after_sleep_onset_minutes", sa.Integer(), nullable=True),
        sa.Column("light_sleep_minutes", sa.Integer(), nullable=True),
        sa.Column("deep_sleep_minutes", sa.Integer(), nullable=True),
        sa.Column("rem_sleep_minutes", sa.Integer(), nullable=True),
        sa.Column("awake_minutes", sa.Integer(), nullable=True),
        sa.Column("sleep_efficiency_pct", sa.Float(), nullable=True),
        sa.Column("sleep_score", sa.Integer(), nullable=True),
        sa.Column("avg_heart_rate_bpm", sa.Integer(), nullable=True),
        sa.Column("min_heart_rate_bpm", sa.Integer(), nullable=True),
        sa.Column("avg_hrv_ms", sa.Float(), nullable=True),
        sa.Column("avg_respiratory_rate", sa.Float(), nullable=True),
        sa.Column("avg_spo2_pct", sa.Float(), nullable=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sleep_user_start", "sleep_sessions", ["user_id", "start_time"])

    # Sleep epochs
    op.create_table(
        "sleep_epochs",
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("stage", sa.String(20), nullable=False),
        sa.Column("heart_rate_bpm", sa.Integer(), nullable=True),
        sa.Column("hrv_ms", sa.Float(), nullable=True),
        sa.Column("movement_intensity", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["session_id"], ["sleep_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("timestamp", "user_id"),
    )
    op.create_index("ix_epoch_session", "sleep_epochs", ["session_id", "timestamp"])

    # Activity readings
    op.create_table(
        "activity_readings",
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("steps", sa.Integer(), nullable=True),
        sa.Column("distance_meters", sa.Float(), nullable=True),
        sa.Column("calories_burned", sa.Float(), nullable=True),
        sa.Column("active_minutes", sa.Integer(), nullable=True),
        sa.Column("activity_type", sa.String(50), nullable=True),
        sa.Column("intensity_level", sa.String(20), nullable=True),
        sa.Column("hr_zone_1_minutes", sa.Integer(), nullable=True),
        sa.Column("hr_zone_2_minutes", sa.Integer(), nullable=True),
        sa.Column("hr_zone_3_minutes", sa.Integer(), nullable=True),
        sa.Column("hr_zone_4_minutes", sa.Integer(), nullable=True),
        sa.Column("hr_zone_5_minutes", sa.Integer(), nullable=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("timestamp", "user_id"),
    )
    op.create_index(
        "ix_activity_user_time", "activity_readings", ["user_id", "timestamp"]
    )

    # Body composition
    op.create_table(
        "body_composition",
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=False),
        sa.Column("body_fat_pct", sa.Float(), nullable=True),
        sa.Column("lean_mass_kg", sa.Float(), nullable=True),
        sa.Column("muscle_mass_kg", sa.Float(), nullable=True),
        sa.Column("bone_mass_kg", sa.Float(), nullable=True),
        sa.Column("water_pct", sa.Float(), nullable=True),
        sa.Column("visceral_fat_level", sa.Integer(), nullable=True),
        sa.Column("bmr_kcal", sa.Integer(), nullable=True),
        sa.Column("metabolic_age", sa.Integer(), nullable=True),
        sa.Column("measurement_method", sa.String(50), nullable=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("timestamp", "user_id"),
    )
    op.create_index(
        "ix_body_comp_user_time", "body_composition", ["user_id", "timestamp"]
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("body_composition")
    op.drop_table("activity_readings")
    op.drop_table("sleep_epochs")
    op.drop_table("sleep_sessions")
    op.drop_table("glucose_readings")
    op.drop_table("hrv_readings")
    op.drop_table("heart_rate_readings")
    op.drop_table("polygenic_scores")
    op.drop_table("genomic_variants")
    op.drop_table("lab_results")
    op.drop_table("lab_panels")
    op.drop_table("biomarker_readings")
    op.drop_table("biomarker_definitions")
    op.drop_table("device_readings")
    op.drop_table("devices")
    op.drop_table("health_profiles")
    op.drop_table("users")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS devicevendor;")
    op.execute("DROP TYPE IF EXISTS devicetype;")
    op.execute("DROP TYPE IF EXISTS units_system_enum;")
    op.execute("DROP TYPE IF EXISTS biological_sex_enum;")
