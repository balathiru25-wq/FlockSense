"""
Inspection and early-warning alerts routes.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from backend.dependencies import get_fusion_state_manager
from backend.schemas import AlertListResponse, AlertItem
from fusion.state_manager import FusionStateManager

router = APIRouter(prefix="/alerts", tags=["Early Warning Alerts"])

@router.get("", response_model=AlertListResponse, summary="Query Early Warning Alerts")
def get_alerts(
    level: Optional[str] = Query(default=None, description="Filter by level: WATCH or ALERT"),
    limit: Optional[int] = Query(default=20, ge=1, le=100, description="Max alerts to return"),
    state_mgr: FusionStateManager = Depends(get_fusion_state_manager)
):
    """
    Returns recent early-warning alerts for farmer review with actionable recommendations.
    """
    all_alerts = state_mgr.engine.get_active_alerts(limit=50)

    filtered = []
    for a in all_alerts:
        if level and a.level.upper() != level.upper():
            continue
        filtered.append(AlertItem(
            alert_id=a.alert_id,
            timestamp=a.timestamp,
            level=a.level,
            scope=a.scope,
            track_id=a.track_id,
            current_zone=a.current_zone,
            inspection_priority=a.inspection_priority,
            message=a.message,
            recommendation=a.recommendation,
            audio_localized=a.audio_localized,
            disclaimer=a.disclaimer
        ))

    # Reverse to return most recent first
    filtered.reverse()

    return AlertListResponse(
        total_alerts=len(filtered[:limit]),
        alerts=filtered[:limit]
    )
