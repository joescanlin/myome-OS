"""Kalman filter-based dynamic calibration"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np

from myome.sensors.base import CalibrationParams


@dataclass
class CalibrationReference:
    """A reference measurement for calibration (e.g., fingerstick vs CGM)"""
    timestamp: datetime
    sensor_value: float
    reference_value: float


class KalmanCalibrator:
    """
    Adaptive calibration using Kalman filtering
    
    Continuously refines calibration parameters as new reference
    measurements become available (e.g., fingerstick glucose checks).
    """
    
    def __init__(
        self,
        initial_alpha: float = 1.0,
        initial_beta: float = 0.0,
        process_noise: float = 0.001,
        measurement_noise: float = 0.05,
    ):
        # State: [alpha, beta] (scaling and offset)
        self.state = np.array([initial_alpha, initial_beta])
        
        # State covariance (uncertainty in calibration params)
        self.P = np.eye(2) * 0.1
        
        # Process noise (how much params can drift over time)
        self.Q = np.eye(2) * process_noise
        
        # Measurement noise (uncertainty in reference measurements)
        self.R = measurement_noise
        
        # History for tracking
        self._references: list[CalibrationReference] = []
        self._last_update: Optional[datetime] = None
    
    def predict(self) -> None:
        """
        Predict step: params may drift slightly over time
        
        Called periodically even without new reference measurements
        """
        self.P = self.P + self.Q
    
    def update(self, sensor_value: float, reference_value: float) -> CalibrationParams:
        """
        Update calibration when a reference measurement is available
        
        Args:
            sensor_value: Raw sensor reading
            reference_value: Gold-standard reference measurement
            
        Returns:
            Updated calibration parameters
        """
        # Store reference
        self._references.append(CalibrationReference(
            timestamp=datetime.utcnow(),
            sensor_value=sensor_value,
            reference_value=reference_value,
        ))
        
        # Measurement model: reference = alpha * sensor + beta
        # H = [sensor_value, 1.0]
        H = np.array([sensor_value, 1.0])
        
        # Innovation (measurement residual)
        predicted = H @ self.state
        innovation = reference_value - predicted
        
        # Kalman gain
        S = H @ self.P @ H.T + self.R
        K = self.P @ H.T / S
        
        # Update state
        self.state = self.state + K * innovation
        
        # Update covariance
        self.P = (np.eye(2) - np.outer(K, H)) @ self.P
        
        self._last_update = datetime.utcnow()
        
        return self.get_params()
    
    def calibrate(self, raw_value: float) -> float:
        """Apply current calibration to raw sensor reading"""
        alpha, beta = self.state
        return alpha * raw_value + beta
    
    def get_params(self) -> CalibrationParams:
        """Get current calibration parameters"""
        return CalibrationParams(
            alpha=float(self.state[0]),
            beta=float(self.state[1]),
            gamma=0.0,
            updated_at=self._last_update,
        )
    
    def get_uncertainty(self) -> tuple[float, float]:
        """Get uncertainty (std dev) in alpha and beta estimates"""
        return (np.sqrt(self.P[0, 0]), np.sqrt(self.P[1, 1]))
    
    def reset(self, alpha: float = 1.0, beta: float = 0.0) -> None:
        """Reset calibration to initial values"""
        self.state = np.array([alpha, beta])
        self.P = np.eye(2) * 0.1
        self._references.clear()
        self._last_update = None


class MultiPointCalibrator:
    """
    Calibration using multiple reference points
    
    Useful for periodic calibration when several reference
    measurements are collected together (e.g., during lab visit).
    """
    
    def __init__(self, min_points: int = 3):
        self.min_points = min_points
        self._references: list[CalibrationReference] = []
    
    def add_reference(
        self,
        sensor_value: float,
        reference_value: float,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Add a calibration reference point"""
        self._references.append(CalibrationReference(
            timestamp=timestamp or datetime.utcnow(),
            sensor_value=sensor_value,
            reference_value=reference_value,
        ))
    
    def calibrate(self) -> Optional[CalibrationParams]:
        """
        Compute calibration parameters from collected references
        
        Uses least squares regression: reference = alpha * sensor + beta
        """
        if len(self._references) < self.min_points:
            return None
        
        # Prepare data
        sensor_values = np.array([r.sensor_value for r in self._references])
        reference_values = np.array([r.reference_value for r in self._references])
        
        # Least squares: y = ax + b
        # Using numpy's polyfit for linear regression
        coefficients = np.polyfit(sensor_values, reference_values, 1)
        
        alpha = coefficients[0]  # Slope
        beta = coefficients[1]   # Intercept
        
        return CalibrationParams(
            alpha=float(alpha),
            beta=float(beta),
            gamma=0.0,
            updated_at=datetime.utcnow(),
        )
    
    def clear(self) -> None:
        """Clear all reference points"""
        self._references.clear()
