"""Data normalization for cross-device consistency"""

from dataclasses import dataclass
from datetime import timedelta

import numpy as np

from myome.sensors.base import DataQuality, Measurement, SensorType


@dataclass
class NormalizationRule:
    """Rule for normalizing a specific measurement type"""

    sensor_type: SensorType
    target_unit: str

    # Conversion functions for common units
    conversions: dict[str, callable]

    # Valid range for physiological plausibility
    min_value: float | None = None
    max_value: float | None = None

    def is_valid(self, value: float) -> bool:
        """Check if value is physiologically plausible"""
        if self.min_value is not None and value < self.min_value:
            return False
        if self.max_value is not None and value > self.max_value:
            return False
        return True


class DataNormalizer:
    """Normalizes measurements to standard units and validates data quality"""

    # Normalization rules for each sensor type
    RULES = {
        SensorType.HEART_RATE: NormalizationRule(
            sensor_type=SensorType.HEART_RATE,
            target_unit="bpm",
            conversions={
                "bpm": lambda x: x,
                "hz": lambda x: x * 60,  # Convert Hz to bpm
            },
            min_value=20,  # Minimum physiological HR
            max_value=300,  # Maximum physiological HR
        ),
        SensorType.GLUCOSE: NormalizationRule(
            sensor_type=SensorType.GLUCOSE,
            target_unit="mg/dL",
            conversions={
                "mg/dL": lambda x: x,
                "mg/dl": lambda x: x,
                "mmol/L": lambda x: x * 18.0182,  # Convert mmol/L to mg/dL
                "mmol/l": lambda x: x * 18.0182,
            },
            min_value=20,  # Severe hypoglycemia
            max_value=600,  # Severe hyperglycemia
        ),
        SensorType.BODY_COMPOSITION: NormalizationRule(
            sensor_type=SensorType.BODY_COMPOSITION,
            target_unit="kg",
            conversions={
                "kg": lambda x: x,
                "lb": lambda x: x * 0.453592,
                "lbs": lambda x: x * 0.453592,
            },
            min_value=20,  # Minimum adult weight
            max_value=500,  # Maximum plausible weight
        ),
        SensorType.TEMPERATURE: NormalizationRule(
            sensor_type=SensorType.TEMPERATURE,
            target_unit="celsius",
            conversions={
                "celsius": lambda x: x,
                "c": lambda x: x,
                "fahrenheit": lambda x: (x - 32) * 5 / 9,
                "f": lambda x: (x - 32) * 5 / 9,
            },
            min_value=32,  # Severe hypothermia
            max_value=44,  # Severe hyperthermia
        ),
    }

    def normalize(self, measurement: Measurement) -> Measurement | None:
        """
        Normalize a measurement to standard units and validate

        Returns None if measurement is invalid/implausible
        """
        rule = self.RULES.get(measurement.sensor_type)

        if rule is None:
            # No normalization rule, return as-is
            return measurement

        # Convert to target unit
        unit_lower = measurement.unit.lower()
        converter = rule.conversions.get(unit_lower)

        if converter is None:
            # Unknown unit, return as-is but flag quality
            return Measurement(
                timestamp=measurement.timestamp,
                value=measurement.value,
                unit=measurement.unit,
                sensor_type=measurement.sensor_type,
                confidence=measurement.confidence * 0.5,  # Reduce confidence
                quality=DataQuality.LOW,
                metadata={
                    **measurement.metadata,
                    "normalization_error": "unknown_unit",
                },
            )

        normalized_value = converter(measurement.value)

        # Validate physiological plausibility
        if not rule.is_valid(normalized_value):
            return None  # Discard implausible values

        return Measurement(
            timestamp=measurement.timestamp,
            value=normalized_value,
            unit=rule.target_unit,
            sensor_type=measurement.sensor_type,
            confidence=measurement.confidence,
            quality=measurement.quality,
            metadata={
                **measurement.metadata,
                "original_value": measurement.value,
                "original_unit": measurement.unit,
            },
        )

    def detect_outliers(
        self,
        measurements: list[Measurement],
        window_size: int = 10,
        threshold_std: float = 3.0,
    ) -> list[tuple[Measurement, str]]:
        """
        Detect outliers in a series of measurements

        Returns list of (measurement, reason) tuples for flagged outliers
        """
        if len(measurements) < window_size:
            return []

        values = np.array([m.value for m in measurements])

        outliers = []

        for i in range(window_size, len(values)):
            window = values[i - window_size : i]
            mean = np.mean(window)
            std = np.std(window)

            if std > 0:
                z_score = abs(values[i] - mean) / std
                if z_score > threshold_std:
                    outliers.append(
                        (
                            measurements[i],
                            f"z_score={z_score:.2f} exceeds threshold {threshold_std}",
                        )
                    )

        return outliers

    def impute_missing(
        self,
        measurements: list[Measurement],
        expected_interval: timedelta,
        max_gap: timedelta,
    ) -> list[Measurement]:
        """
        Impute missing values using linear interpolation

        Only imputes gaps smaller than max_gap
        """
        if len(measurements) < 2:
            return measurements

        # Sort by timestamp
        sorted_measurements = sorted(measurements, key=lambda m: m.timestamp)

        result = [sorted_measurements[0]]

        for i in range(1, len(sorted_measurements)):
            prev = sorted_measurements[i - 1]
            curr = sorted_measurements[i]

            gap = curr.timestamp - prev.timestamp

            # Check if gap exceeds expected interval but is within max_gap
            if gap > expected_interval and gap <= max_gap:
                # Calculate number of imputed points
                num_points = int(gap / expected_interval) - 1

                for j in range(1, num_points + 1):
                    # Linear interpolation
                    fraction = j / (num_points + 1)
                    imputed_value = prev.value + fraction * (curr.value - prev.value)
                    imputed_timestamp = prev.timestamp + (fraction * gap)

                    result.append(
                        Measurement(
                            timestamp=imputed_timestamp,
                            value=imputed_value,
                            unit=curr.unit,
                            sensor_type=curr.sensor_type,
                            confidence=0.5,  # Lower confidence for imputed
                            quality=DataQuality.LOW,
                            metadata={
                                "imputed": True,
                                "method": "linear_interpolation",
                            },
                        )
                    )

            result.append(curr)

        return sorted(result, key=lambda m: m.timestamp)
