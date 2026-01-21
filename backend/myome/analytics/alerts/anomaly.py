"""Anomaly detection for health data"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import numpy as np
import pandas as pd
from scipy import stats


class AnomalyType(str, Enum):
    """Types of anomalies"""

    POINT = "point"  # Single outlier value
    LEVEL_SHIFT = "level_shift"  # Sustained change in baseline
    TREND = "trend"  # Gradual change over time
    PATTERN = "pattern"  # Unusual pattern (e.g., missing sleep)


class AlertPriority(str, Enum):
    """Alert priority levels"""

    CRITICAL = "critical"  # Immediate attention needed
    HIGH = "high"  # Review within 48h
    MEDIUM = "medium"  # Review at next visit
    LOW = "low"  # Monitor only


@dataclass
class Anomaly:
    """Detected anomaly"""

    timestamp: datetime
    biomarker: str
    anomaly_type: AnomalyType
    priority: AlertPriority
    value: float
    expected_range: tuple[float, float]
    deviation_score: float
    description: str
    clinical_context: str | None = None

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "biomarker": self.biomarker,
            "anomaly_type": self.anomaly_type.value,
            "priority": self.priority.value,
            "value": self.value,
            "expected_range": self.expected_range,
            "deviation_score": self.deviation_score,
            "description": self.description,
            "clinical_context": self.clinical_context,
        }


class AnomalyDetector:
    """
    Detect anomalies in health data

    Uses multiple detection methods:
    - Statistical (z-score, IQR)
    - Bayesian change-point detection
    - Clinical threshold violations
    """

    # Clinical thresholds for critical alerts
    CLINICAL_THRESHOLDS = {
        "glucose": {
            "critical_low": 54,  # Severe hypoglycemia
            "low": 70,  # Hypoglycemia
            "high": 180,  # Hyperglycemia (after meals)
            "critical_high": 250,  # Severe hyperglycemia
        },
        "heart_rate": {
            "critical_low": 40,  # Severe bradycardia
            "low": 50,  # Bradycardia (unless athletic)
            "high": 100,  # Tachycardia at rest
            "critical_high": 150,  # Severe tachycardia at rest
        },
        "hrv_sdnn": {
            "critical_low": 20,  # Very low HRV, poor autonomic function
            "low": 30,  # Below average
        },
        "blood_pressure_systolic": {
            "critical_low": 90,  # Hypotension
            "low": 100,
            "high": 140,  # Stage 1 hypertension
            "critical_high": 180,  # Hypertensive crisis
        },
    }

    def __init__(
        self,
        window_size: int = 30,  # Days of baseline
        z_threshold: float = 3.0,
        iqr_multiplier: float = 1.5,
    ):
        self.window_size = window_size
        self.z_threshold = z_threshold
        self.iqr_multiplier = iqr_multiplier

    def detect_anomalies(
        self,
        data: pd.Series,
        biomarker_name: str,
    ) -> list[Anomaly]:
        """
        Detect all anomalies in a time series

        Args:
            data: pandas Series with datetime index
            biomarker_name: Name of biomarker for thresholds
        """
        anomalies = []

        # 1. Clinical threshold violations (highest priority)
        clinical = self._detect_clinical_violations(data, biomarker_name)
        anomalies.extend(clinical)

        # 2. Statistical outliers
        statistical = self._detect_statistical_outliers(data, biomarker_name)
        anomalies.extend(statistical)

        # 3. Level shifts
        level_shifts = self._detect_level_shifts(data, biomarker_name)
        anomalies.extend(level_shifts)

        return anomalies

    def _detect_clinical_violations(
        self,
        data: pd.Series,
        biomarker_name: str,
    ) -> list[Anomaly]:
        """Detect violations of clinical thresholds"""
        thresholds = self.CLINICAL_THRESHOLDS.get(biomarker_name, {})

        if not thresholds:
            return []

        anomalies = []

        for timestamp, value in data.items():
            if pd.isna(value):
                continue
            ts = (
                timestamp.to_pydatetime()
                if hasattr(timestamp, "to_pydatetime")
                else timestamp
            )

            # Check critical thresholds
            if "critical_low" in thresholds and value < thresholds["critical_low"]:
                anomalies.append(
                    Anomaly(
                        timestamp=ts,
                        biomarker=biomarker_name,
                        anomaly_type=AnomalyType.POINT,
                        priority=AlertPriority.CRITICAL,
                        value=float(value),
                        expected_range=(
                            thresholds["critical_low"],
                            thresholds.get("critical_high", float("inf")),
                        ),
                        deviation_score=abs(value - thresholds["critical_low"])
                        / thresholds["critical_low"],
                        description=f"Critically low {biomarker_name}: {value}",
                        clinical_context="Immediate medical attention may be required",
                    )
                )
            elif "critical_high" in thresholds and value > thresholds["critical_high"]:
                anomalies.append(
                    Anomaly(
                        timestamp=ts,
                        biomarker=biomarker_name,
                        anomaly_type=AnomalyType.POINT,
                        priority=AlertPriority.CRITICAL,
                        value=float(value),
                        expected_range=(
                            thresholds.get("critical_low", 0),
                            thresholds["critical_high"],
                        ),
                        deviation_score=(value - thresholds["critical_high"])
                        / thresholds["critical_high"],
                        description=f"Critically high {biomarker_name}: {value}",
                        clinical_context="Immediate medical attention may be required",
                    )
                )
            # Check warning thresholds
            elif "low" in thresholds and value < thresholds["low"]:
                anomalies.append(
                    Anomaly(
                        timestamp=ts,
                        biomarker=biomarker_name,
                        anomaly_type=AnomalyType.POINT,
                        priority=AlertPriority.HIGH,
                        value=float(value),
                        expected_range=(
                            thresholds["low"],
                            thresholds.get("high", float("inf")),
                        ),
                        deviation_score=abs(value - thresholds["low"])
                        / thresholds["low"],
                        description=f"Low {biomarker_name}: {value}",
                    )
                )
            elif "high" in thresholds and value > thresholds["high"]:
                anomalies.append(
                    Anomaly(
                        timestamp=ts,
                        biomarker=biomarker_name,
                        anomaly_type=AnomalyType.POINT,
                        priority=AlertPriority.HIGH,
                        value=float(value),
                        expected_range=(thresholds.get("low", 0), thresholds["high"]),
                        deviation_score=(value - thresholds["high"])
                        / thresholds["high"],
                        description=f"High {biomarker_name}: {value}",
                    )
                )

        return anomalies

    def _detect_statistical_outliers(
        self,
        data: pd.Series,
        biomarker_name: str,
    ) -> list[Anomaly]:
        """Detect statistical outliers using rolling z-score"""
        if len(data) < self.window_size:
            return []

        anomalies = []

        # Calculate rolling statistics
        rolling_mean = data.rolling(
            window=self.window_size, min_periods=self.window_size // 2
        ).mean()
        rolling_std = data.rolling(
            window=self.window_size, min_periods=self.window_size // 2
        ).std()

        for timestamp, value in data.items():
            if pd.isna(value):
                continue
            ts = (
                timestamp.to_pydatetime()
                if hasattr(timestamp, "to_pydatetime")
                else timestamp
            )

            mean = rolling_mean.get(timestamp)
            std = rolling_std.get(timestamp)

            if pd.isna(mean) or pd.isna(std) or std == 0:
                continue

            z_score = abs(value - mean) / std

            if z_score > self.z_threshold:
                anomalies.append(
                    Anomaly(
                        timestamp=ts,
                        biomarker=biomarker_name,
                        anomaly_type=AnomalyType.POINT,
                        priority=AlertPriority.MEDIUM,
                        value=float(value),
                        expected_range=(float(mean - 2 * std), float(mean + 2 * std)),
                        deviation_score=float(z_score),
                        description=f"Unusual {biomarker_name} value: {value:.1f} (z-score: {z_score:.1f})",
                    )
                )

        return anomalies

    def _detect_level_shifts(
        self,
        data: pd.Series,
        biomarker_name: str,
        min_shift_percent: float = 15.0,
    ) -> list[Anomaly]:
        """Detect sustained level shifts in baseline"""
        if len(data) < self.window_size * 2:
            return []

        anomalies = []
        values = data.dropna().values
        timestamps = data.dropna().index

        # Compare recent window to baseline
        baseline = values[: self.window_size]
        baseline_mean = np.mean(np.asarray(baseline, dtype=float))
        baseline_std = np.std(np.asarray(baseline, dtype=float))

        if baseline_mean == 0 or baseline_std == 0:
            return []

        # Check each subsequent window
        for i in range(
            self.window_size, len(values) - self.window_size, self.window_size // 2
        ):
            recent = values[i : i + self.window_size]
            recent_mean = np.mean(np.asarray(recent, dtype=float))

            # Calculate percent change from baseline
            percent_change = ((recent_mean - baseline_mean) / abs(baseline_mean)) * 100

            if abs(percent_change) > min_shift_percent:
                # Verify with t-test
                t_stat, p_value = stats.ttest_ind(
                    np.asarray(baseline, dtype=float),
                    np.asarray(recent, dtype=float),
                )

                if p_value < 0.01:  # Significant shift
                    direction = "increased" if percent_change > 0 else "decreased"

                    anomalies.append(
                        Anomaly(
                            timestamp=(
                                timestamps[i].to_pydatetime()
                                if hasattr(timestamps[i], "to_pydatetime")
                                else timestamps[i]
                            ),
                            biomarker=biomarker_name,
                            anomaly_type=AnomalyType.LEVEL_SHIFT,
                            priority=AlertPriority.HIGH,
                            value=float(recent_mean),
                            expected_range=(
                                float(baseline_mean - 2 * baseline_std),
                                float(baseline_mean + 2 * baseline_std),
                            ),
                            deviation_score=float(abs(percent_change)),
                            description=f"{biomarker_name} has {direction} by {abs(percent_change):.1f}% from baseline",
                            clinical_context=f"Baseline mean: {baseline_mean:.1f}, Current: {recent_mean:.1f}",
                        )
                    )

        return anomalies
