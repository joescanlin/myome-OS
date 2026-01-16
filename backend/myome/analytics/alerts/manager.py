"""Alert management system"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from myome.analytics.alerts.anomaly import Anomaly, AlertPriority
from myome.core.logging import logger


class AlertStatus(str, Enum):
    """Alert status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


@dataclass
class Alert:
    """User-facing alert"""
    id: str
    user_id: str
    created_at: datetime
    anomaly: Anomaly
    status: AlertStatus
    title: str
    message: str
    recommendation: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'status': self.status.value,
            'priority': self.anomaly.priority.value,
            'title': self.title,
            'message': self.message,
            'recommendation': self.recommendation,
            'biomarker': self.anomaly.biomarker,
            'value': self.anomaly.value,
            'anomaly_type': self.anomaly.anomaly_type.value,
        }


class AlertManager:
    """
    Manage alerts from anomaly detection
    
    Handles:
    - Alert creation and deduplication
    - Priority-based notification routing
    - Alert lifecycle (acknowledge, resolve, dismiss)
    """
    
    # Recommendations for common anomaly patterns
    RECOMMENDATIONS = {
        ('glucose', 'critical_low'): "Check your blood sugar immediately. If below 70 mg/dL, consume 15g fast-acting carbs.",
        ('glucose', 'critical_high'): "High blood sugar detected. Check for ketones if over 250 mg/dL. Contact your healthcare provider.",
        ('heart_rate', 'critical_low'): "Very low heart rate detected at rest. If you feel dizzy or faint, seek medical attention.",
        ('heart_rate', 'critical_high'): "Elevated resting heart rate. Rest and monitor. Seek medical attention if accompanied by chest pain.",
        ('hrv_sdnn', 'low'): "Your HRV has been declining. Consider prioritizing sleep and stress reduction.",
    }
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self._alerts: dict[str, Alert] = {}
        self._recent_anomalies: list[Anomaly] = []
    
    def create_alert(self, anomaly: Anomaly) -> Optional[Alert]:
        """
        Create an alert from an anomaly
        
        Returns None if alert is deduplicated
        """
        # Check for duplicate (same biomarker, same type, within 1 hour)
        if self._is_duplicate(anomaly):
            return None
        
        # Generate title and message
        title = self._generate_title(anomaly)
        message = self._generate_message(anomaly)
        recommendation = self._get_recommendation(anomaly)
        
        alert = Alert(
            id=str(uuid4()),
            user_id=self.user_id,
            created_at=datetime.now(timezone.utc),
            anomaly=anomaly,
            status=AlertStatus.ACTIVE,
            title=title,
            message=message,
            recommendation=recommendation,
        )
        
        self._alerts[alert.id] = alert
        self._recent_anomalies.append(anomaly)
        
        logger.info(f"Created alert {alert.id}: {title}")
        
        return alert
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Mark alert as acknowledged"""
        alert = self._alerts.get(alert_id)
        if alert and alert.status == AlertStatus.ACTIVE:
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.now(timezone.utc)
            return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Mark alert as resolved"""
        alert = self._alerts.get(alert_id)
        if alert and alert.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now(timezone.utc)
            return True
        return False
    
    def dismiss_alert(self, alert_id: str) -> bool:
        """Dismiss alert (user chose to ignore)"""
        alert = self._alerts.get(alert_id)
        if alert and alert.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]:
            alert.status = AlertStatus.DISMISSED
            return True
        return False
    
    def get_active_alerts(self) -> list[Alert]:
        """Get all active alerts"""
        return [
            a for a in self._alerts.values()
            if a.status == AlertStatus.ACTIVE
        ]
    
    def get_alerts_by_priority(self, priority: AlertPriority) -> list[Alert]:
        """Get active alerts of specific priority"""
        return [
            a for a in self._alerts.values()
            if a.status == AlertStatus.ACTIVE and a.anomaly.priority == priority
        ]
    
    def _is_duplicate(self, anomaly: Anomaly) -> bool:
        """Check if anomaly is duplicate of recent alert"""
        for recent in self._recent_anomalies[-50:]:  # Check last 50
            if (
                recent.biomarker == anomaly.biomarker and
                recent.anomaly_type == anomaly.anomaly_type and
                abs((recent.timestamp - anomaly.timestamp).total_seconds()) < 3600
            ):
                return True
        return False
    
    def _generate_title(self, anomaly: Anomaly) -> str:
        """Generate alert title"""
        priority_emoji = {
            AlertPriority.CRITICAL: "🚨",
            AlertPriority.HIGH: "⚠️",
            AlertPriority.MEDIUM: "📊",
            AlertPriority.LOW: "ℹ️",
        }
        
        emoji = priority_emoji.get(anomaly.priority, "")
        return f"{emoji} {anomaly.description}"
    
    def _generate_message(self, anomaly: Anomaly) -> str:
        """Generate detailed alert message"""
        parts = [
            f"Detected at: {anomaly.timestamp.strftime('%Y-%m-%d %H:%M')}",
            f"Current value: {anomaly.value:.1f}",
            f"Expected range: {anomaly.expected_range[0]:.1f} - {anomaly.expected_range[1]:.1f}",
        ]
        
        if anomaly.clinical_context:
            parts.append(f"Context: {anomaly.clinical_context}")
        
        return "\n".join(parts)
    
    def _get_recommendation(self, anomaly: Anomaly) -> Optional[str]:
        """Get recommendation for anomaly type"""
        # Check for specific recommendations
        key = (anomaly.biomarker, anomaly.priority.value)
        if key in self.RECOMMENDATIONS:
            return self.RECOMMENDATIONS[key]
        
        # Generic recommendations by priority
        if anomaly.priority == AlertPriority.CRITICAL:
            return "This requires immediate attention. Consider contacting your healthcare provider."
        elif anomaly.priority == AlertPriority.HIGH:
            return "Monitor closely and discuss with your healthcare provider at your next visit."
        
        return None
