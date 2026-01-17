"""Create TimescaleDB hypertables

Revision ID: 002_hypertables
Revises: 001_initial
Create Date: 2026-01-16

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_hypertables"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Convert time-series tables to TimescaleDB hypertables"""

    # Heart rate readings - 1 week chunks for high-frequency data
    op.execute(
        """
        SELECT create_hypertable(
            'heart_rate_readings',
            'timestamp',
            chunk_time_interval => INTERVAL '1 week',
            if_not_exists => TRUE
        );
    """
    )

    # HRV readings - 1 week chunks
    op.execute(
        """
        SELECT create_hypertable(
            'hrv_readings',
            'timestamp',
            chunk_time_interval => INTERVAL '1 week',
            if_not_exists => TRUE
        );
    """
    )

    # Glucose readings - 1 week chunks for CGM data (every 5 min)
    op.execute(
        """
        SELECT create_hypertable(
            'glucose_readings',
            'timestamp',
            chunk_time_interval => INTERVAL '1 week',
            if_not_exists => TRUE
        );
    """
    )

    # Sleep epochs - 1 month chunks (30-sec epochs, less frequent)
    op.execute(
        """
        SELECT create_hypertable(
            'sleep_epochs',
            'timestamp',
            chunk_time_interval => INTERVAL '1 month',
            if_not_exists => TRUE
        );
    """
    )

    # Activity readings - 1 week chunks
    op.execute(
        """
        SELECT create_hypertable(
            'activity_readings',
            'timestamp',
            chunk_time_interval => INTERVAL '1 week',
            if_not_exists => TRUE
        );
    """
    )

    # Body composition - 1 year chunks (daily/weekly measurements)
    op.execute(
        """
        SELECT create_hypertable(
            'body_composition',
            'timestamp',
            chunk_time_interval => INTERVAL '1 year',
            if_not_exists => TRUE
        );
    """
    )

    # Enable compression on heart rate data (most voluminous)
    op.execute(
        """
        ALTER TABLE heart_rate_readings SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'user_id'
        );
    """
    )

    # Add compression policy - compress data older than 30 days
    op.execute(
        """
        SELECT add_compression_policy('heart_rate_readings', INTERVAL '30 days');
    """
    )

    # Enable compression on glucose readings
    op.execute(
        """
        ALTER TABLE glucose_readings SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'user_id'
        );
    """
    )

    op.execute(
        """
        SELECT add_compression_policy('glucose_readings', INTERVAL '30 days');
    """
    )

    # Enable compression on HRV readings
    op.execute(
        """
        ALTER TABLE hrv_readings SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'user_id'
        );
    """
    )

    op.execute(
        """
        SELECT add_compression_policy('hrv_readings', INTERVAL '30 days');
    """
    )


def downgrade() -> None:
    """Remove compression policies (hypertables remain but lose optimization)"""
    # Remove compression policies
    op.execute(
        "SELECT remove_compression_policy('heart_rate_readings', if_exists => TRUE);"
    )
    op.execute(
        "SELECT remove_compression_policy('glucose_readings', if_exists => TRUE);"
    )
    op.execute("SELECT remove_compression_policy('hrv_readings', if_exists => TRUE);")

    # Note: Converting hypertables back to regular tables is complex and typically
    # not done. The tables will remain as hypertables but can still function normally.
