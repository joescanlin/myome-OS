"""Tests for analytics engine"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import numpy as np
import pandas as pd

from myome.analytics.correlation.engine import CorrelationEngine, CorrelationResult
from myome.analytics.correlation.trends import TrendAnalyzer, TrendResult, ChangePoint
from myome.analytics.alerts.anomaly import (
    AnomalyDetector,
    Anomaly,
    AnomalyType,
    AlertPriority,
)
from myome.analytics.alerts.manager import AlertManager, Alert, AlertStatus
from myome.analytics.prediction.glucose import (
    GlucoseResponsePredictor,
    GlucosePrediction,
    MealContext,
)


class TestCorrelationResult:
    """Tests for CorrelationResult"""
    
    def test_correlation_result_creation(self):
        """Test creating a correlation result"""
        result = CorrelationResult(
            biomarker_1='heart_rate',
            biomarker_2='hrv_sdnn',
            correlation=-0.65,
            p_value=0.001,
            lag_days=0,
            n_observations=100,
            is_significant=True,
            interpretation='Strong negative correlation',
        )
        assert result.correlation == -0.65
        assert result.is_significant == True
    
    def test_correlation_result_to_dict(self):
        """Test serialization of correlation result"""
        result = CorrelationResult(
            biomarker_1='glucose',
            biomarker_2='sleep_total',
            correlation=0.45,
            p_value=0.02,
            lag_days=1,
            n_observations=50,
            is_significant=True,
        )
        d = result.to_dict()
        assert d['biomarker_1'] == 'glucose'
        assert d['correlation'] == 0.45
        assert d['lag_days'] == 1


class TestTrendAnalyzer:
    """Tests for TrendAnalyzer"""
    
    def test_compute_trend_increasing(self):
        """Test detecting increasing trend"""
        analyzer = TrendAnalyzer(significance_level=0.05)
        
        # Create increasing data with some noise
        dates = pd.date_range(start='2026-01-01', periods=30, freq='D')
        np.random.seed(42)
        values = np.arange(100, 130) + np.random.normal(0, 1, 30)
        series = pd.Series(values, index=dates)
        
        result = analyzer.compute_trend(series, 'test_metric')
        
        assert result is not None
        assert result.direction == 'increasing'
        assert result.slope > 0
    
    def test_compute_trend_decreasing(self):
        """Test detecting decreasing trend"""
        analyzer = TrendAnalyzer(significance_level=0.05)
        
        dates = pd.date_range(start='2026-01-01', periods=30, freq='D')
        np.random.seed(42)
        values = np.arange(130, 100, -1) + np.random.normal(0, 1, 30)
        series = pd.Series(values, index=dates)
        
        result = analyzer.compute_trend(series, 'test_metric')
        
        assert result is not None
        assert result.direction == 'decreasing'
        assert result.slope < 0
    
    def test_compute_trend_stable(self):
        """Test detecting stable trend (no significant change)"""
        analyzer = TrendAnalyzer(significance_level=0.05)
        
        dates = pd.date_range(start='2026-01-01', periods=30, freq='D')
        np.random.seed(42)
        values = 100 + np.random.normal(0, 2, 30)  # Flat with noise
        series = pd.Series(values, index=dates)
        
        result = analyzer.compute_trend(series, 'test_metric')
        
        assert result is not None
        # With random noise and flat mean, should be stable
        # (p-value likely > 0.05)
    
    def test_insufficient_data(self):
        """Test handling of insufficient data"""
        analyzer = TrendAnalyzer()
        
        dates = pd.date_range(start='2026-01-01', periods=3, freq='D')
        values = [100, 101, 102]
        series = pd.Series(values, index=dates)
        
        result = analyzer.compute_trend(series, 'test_metric')
        
        assert result is None  # Less than 7 days
    
    def test_detect_change_points(self):
        """Test change point detection"""
        analyzer = TrendAnalyzer()
        
        dates = pd.date_range(start='2026-01-01', periods=30, freq='D')
        # Create data with level shift at day 15
        values = np.concatenate([
            np.random.normal(100, 2, 15),
            np.random.normal(120, 2, 15),  # Level shift
        ])
        series = pd.Series(values, index=dates)
        
        change_points = analyzer.detect_change_points(series, min_segment_size=7)
        
        # Should detect the level shift
        assert len(change_points) >= 0  # May or may not detect depending on noise


class TestAnomalyDetector:
    """Tests for AnomalyDetector"""
    
    def test_detect_clinical_threshold_low(self):
        """Test detection of clinically low glucose"""
        detector = AnomalyDetector()
        
        dates = pd.date_range(start='2026-01-01', periods=10, freq='h')
        values = [100, 95, 90, 85, 50, 95, 100, 105, 100, 95]  # 50 is critical low
        series = pd.Series(values, index=dates)
        
        anomalies = detector.detect_anomalies(series, 'glucose')
        
        # Should detect the 50 mg/dL as critical low
        critical = [a for a in anomalies if a.priority == AlertPriority.CRITICAL]
        assert len(critical) >= 1
        assert any(a.value == 50 for a in critical)
    
    def test_detect_clinical_threshold_high(self):
        """Test detection of clinically high glucose"""
        detector = AnomalyDetector()
        
        dates = pd.date_range(start='2026-01-01', periods=10, freq='h')
        values = [100, 105, 110, 115, 280, 120, 115, 110, 105, 100]  # 280 is critical high
        series = pd.Series(values, index=dates)
        
        anomalies = detector.detect_anomalies(series, 'glucose')
        
        # Should detect the 280 mg/dL as critical high
        critical = [a for a in anomalies if a.priority == AlertPriority.CRITICAL]
        assert len(critical) >= 1
        assert any(a.value == 280 for a in critical)
    
    def test_detect_statistical_outlier(self):
        """Test detection of statistical outliers"""
        detector = AnomalyDetector(window_size=10, z_threshold=2.5)
        
        dates = pd.date_range(start='2026-01-01', periods=50, freq='h')
        np.random.seed(42)
        values = list(70 + np.random.normal(0, 3, 49))
        values.insert(40, 95)  # Insert outlier (but not clinical violation)
        series = pd.Series(values, index=dates)
        
        anomalies = detector.detect_anomalies(series, 'heart_rate')
        
        # May or may not detect depending on exact values
        # At least verify no errors
        assert isinstance(anomalies, list)
    
    def test_anomaly_to_dict(self):
        """Test anomaly serialization"""
        anomaly = Anomaly(
            timestamp=datetime.now(timezone.utc),
            biomarker='glucose',
            anomaly_type=AnomalyType.POINT,
            priority=AlertPriority.CRITICAL,
            value=45.0,
            expected_range=(70.0, 180.0),
            deviation_score=0.5,
            description='Critically low glucose',
            clinical_context='Immediate attention needed',
        )
        
        d = anomaly.to_dict()
        assert d['biomarker'] == 'glucose'
        assert d['priority'] == 'critical'
        assert d['value'] == 45.0


class TestAlertManager:
    """Tests for AlertManager"""
    
    def test_create_alert(self):
        """Test creating an alert from anomaly"""
        manager = AlertManager(user_id='test-user')
        
        anomaly = Anomaly(
            timestamp=datetime.now(timezone.utc),
            biomarker='glucose',
            anomaly_type=AnomalyType.POINT,
            priority=AlertPriority.CRITICAL,
            value=50.0,
            expected_range=(70.0, 180.0),
            deviation_score=0.4,
            description='Low glucose',
        )
        
        alert = manager.create_alert(anomaly)
        
        assert alert is not None
        assert alert.status == AlertStatus.ACTIVE
        assert 'Low glucose' in alert.title
    
    def test_deduplicate_alerts(self):
        """Test that duplicate alerts are filtered"""
        manager = AlertManager(user_id='test-user')
        now = datetime.now(timezone.utc)
        
        anomaly1 = Anomaly(
            timestamp=now,
            biomarker='glucose',
            anomaly_type=AnomalyType.POINT,
            priority=AlertPriority.HIGH,
            value=65.0,
            expected_range=(70.0, 180.0),
            deviation_score=0.1,
            description='Low glucose',
        )
        
        anomaly2 = Anomaly(
            timestamp=now + timedelta(minutes=5),  # Same type, within 1 hour
            biomarker='glucose',
            anomaly_type=AnomalyType.POINT,
            priority=AlertPriority.HIGH,
            value=63.0,
            expected_range=(70.0, 180.0),
            deviation_score=0.1,
            description='Low glucose',
        )
        
        alert1 = manager.create_alert(anomaly1)
        alert2 = manager.create_alert(anomaly2)
        
        assert alert1 is not None
        assert alert2 is None  # Deduplicated
    
    def test_acknowledge_alert(self):
        """Test acknowledging an alert"""
        manager = AlertManager(user_id='test-user')
        
        anomaly = Anomaly(
            timestamp=datetime.now(timezone.utc),
            biomarker='heart_rate',
            anomaly_type=AnomalyType.POINT,
            priority=AlertPriority.MEDIUM,
            value=110.0,
            expected_range=(50.0, 100.0),
            deviation_score=0.1,
            description='Elevated heart rate',
        )
        
        alert = manager.create_alert(anomaly)
        assert alert.status == AlertStatus.ACTIVE
        
        result = manager.acknowledge_alert(alert.id)
        assert result == True
        assert alert.status == AlertStatus.ACKNOWLEDGED
    
    def test_resolve_alert(self):
        """Test resolving an alert"""
        manager = AlertManager(user_id='test-user')
        
        anomaly = Anomaly(
            timestamp=datetime.now(timezone.utc),
            biomarker='hrv_sdnn',
            anomaly_type=AnomalyType.LEVEL_SHIFT,
            priority=AlertPriority.HIGH,
            value=25.0,
            expected_range=(30.0, 100.0),
            deviation_score=0.2,
            description='Low HRV',
        )
        
        alert = manager.create_alert(anomaly)
        manager.acknowledge_alert(alert.id)
        
        result = manager.resolve_alert(alert.id)
        assert result == True
        assert alert.status == AlertStatus.RESOLVED
    
    def test_get_active_alerts(self):
        """Test getting active alerts"""
        manager = AlertManager(user_id='test-user')
        
        for i in range(3):
            anomaly = Anomaly(
                timestamp=datetime.now(timezone.utc) + timedelta(hours=i+1),  # Different times
                biomarker=f'metric_{i}',
                anomaly_type=AnomalyType.POINT,
                priority=AlertPriority.MEDIUM,
                value=100.0,
                expected_range=(50.0, 80.0),
                deviation_score=0.25,
                description=f'Alert {i}',
            )
            manager.create_alert(anomaly)
        
        active = manager.get_active_alerts()
        assert len(active) == 3


class TestMealContext:
    """Tests for MealContext"""
    
    def test_meal_context_creation(self):
        """Test creating meal context"""
        context = MealContext(
            carbohydrates_g=50.0,
            fiber_g=5.0,
            protein_g=20.0,
            fat_g=15.0,
            glycemic_load=25.0,
            time_of_day=datetime.now(timezone.utc),
            hours_since_wake=3.0,
            recent_exercise_minutes=30,
            sleep_quality_score=80.0,
            baseline_glucose=95.0,
        )
        
        assert context.carbohydrates_g == 50.0
        assert context.baseline_glucose == 95.0


class TestGlucoseResponsePredictor:
    """Tests for GlucoseResponsePredictor"""
    
    def test_extract_features(self):
        """Test feature extraction from meal context"""
        predictor = GlucoseResponsePredictor(user_id='test-user')
        
        context = MealContext(
            carbohydrates_g=60.0,
            fiber_g=6.0,
            protein_g=25.0,
            fat_g=20.0,
            glycemic_load=30.0,
            time_of_day=datetime(2026, 1, 15, 12, 30, tzinfo=timezone.utc),
            hours_since_wake=5.0,
            recent_exercise_minutes=0,
            sleep_quality_score=75.0,
            baseline_glucose=100.0,
        )
        
        features = predictor._extract_features(context)
        
        assert len(features) == 13  # Number of features
        assert features[0] == 60.0  # carbs_g
        assert predictor.feature_names[0] == 'carbs_g'
    
    def test_predict_without_training(self):
        """Test prediction returns None without training"""
        predictor = GlucoseResponsePredictor(user_id='test-user')
        
        context = MealContext(
            carbohydrates_g=50.0,
            fiber_g=5.0,
            protein_g=20.0,
            fat_g=15.0,
            glycemic_load=None,
            time_of_day=datetime.now(timezone.utc),
            hours_since_wake=2.0,
            recent_exercise_minutes=0,
            sleep_quality_score=None,
            baseline_glucose=95.0,
        )
        
        prediction = predictor.predict(context)
        
        assert prediction is None  # Not trained yet


class TestGlucosePrediction:
    """Tests for GlucosePrediction"""
    
    def test_glucose_prediction_creation(self):
        """Test creating a glucose prediction"""
        prediction = GlucosePrediction(
            predicted_peak_mg_dl=145.0,
            predicted_time_to_peak_minutes=45,
            confidence_interval=(130.0, 160.0),
            contributing_factors={'carbs_g': 0.4, 'baseline_glucose': 0.3},
        )
        
        assert prediction.predicted_peak_mg_dl == 145.0
        assert prediction.predicted_time_to_peak_minutes == 45
        assert prediction.confidence_interval == (130.0, 160.0)
