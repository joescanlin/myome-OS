"""Alert management routes"""

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from myome.analytics.alerts.manager import AlertManager, AlertStatus
from myome.api.deps.auth import CurrentUser

router = APIRouter(prefix="/alerts", tags=["Alerts"])


class AlertResponse(BaseModel):
    """Alert response"""

    id: str
    created_at: str
    status: str
    priority: str
    title: str
    message: str
    recommendation: str | None
    biomarker: str
    value: float


@router.get("/", response_model=list[AlertResponse])
async def list_alerts(
    user: CurrentUser,
    status_filter: AlertStatus | None = Query(default=None, alias="status"),
    priority: str | None = Query(default=None),
) -> list[AlertResponse]:
    """List user's alerts"""
    manager = AlertManager(user.id)

    # In production, load alerts from database
    # For now, return active alerts from manager
    alerts = manager.get_active_alerts()

    # Apply filters
    if status_filter:
        alerts = [a for a in alerts if a.status == status_filter]
    if priority:
        alerts = [a for a in alerts if a.anomaly.priority.value == priority]

    return [
        AlertResponse(
            id=a.id,
            created_at=a.created_at.isoformat(),
            status=a.status.value,
            priority=a.anomaly.priority.value,
            title=a.title,
            message=a.message,
            recommendation=a.recommendation,
            biomarker=a.anomaly.biomarker,
            value=a.anomaly.value,
        )
        for a in alerts
    ]


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    user: CurrentUser,
) -> dict:
    """Acknowledge an alert"""
    manager = AlertManager(user.id)

    if manager.acknowledge_alert(alert_id):
        return {"status": "acknowledged"}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Alert not found or already processed",
    )


@router.post("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    user: CurrentUser,
) -> dict:
    """Resolve an alert"""
    manager = AlertManager(user.id)

    if manager.resolve_alert(alert_id):
        return {"status": "resolved"}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Alert not found or already processed",
    )


@router.post("/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: str,
    user: CurrentUser,
) -> dict:
    """Dismiss an alert"""
    manager = AlertManager(user.id)

    if manager.dismiss_alert(alert_id):
        return {"status": "dismissed"}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Alert not found or already processed",
    )
