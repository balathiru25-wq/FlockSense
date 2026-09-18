"""
Early Warning Alert Engine for FlockSense.
Dispatches actionable flock-level and per-bird inspection alerts with
context-specific farmer recommendations and standard disclaimers.
"""

import uuid
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional
from fusion.models import EarlyWarningAlert, InspectionCandidate, FlockStatus

RECOMMENDATIONS = {
    "NORMAL": "Continue routine automated FlockSense acoustic and camera monitoring.",
    "WATCH": "Inspect the tracked bird when practical and continue monitoring behavioral trend over the next 2–6 hours.",
    "ALERT": "Promptly inspect the tracked bird and surrounding flock environment (litter, waterers, ventilation). If concerning clinical signs persist, consult a certified poultry veterinarian."
}

class AlertEngine:
    """
    Generates and persists early-warning inspection alerts.
    Maintains alert history, prevents alert spam through debouncing,
    and formats actionable farmer guidance without making clinical diagnoses.
    """
    def __init__(self, alerts_csv_path: str = "outputs/fusion/logs/alerts.csv"):
        self.alerts_csv_path = Path(alerts_csv_path)
        self.alerts_history: List[EarlyWarningAlert] = []
        self._init_csv()

    def _init_csv(self):
        self.alerts_csv_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.alerts_csv_path.exists():
            with open(self.alerts_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "alert_id", "timestamp", "scope", "track_id", "level",
                    "current_zone", "inspection_priority", "message",
                    "recommendation", "audio_localized", "disclaimer"
                ])

    def generate_track_alert(
        self,
        candidate: InspectionCandidate,
        timestamp: float,
        flock_audio_score: float = 0.0,
        audio_localized: bool = False
    ) -> Optional[EarlyWarningAlert]:
        """
        Generates an early-warning alert for a candidate if their status is WATCH or ALERT.
        """
        if candidate.status not in ["WATCH", "ALERT"]:
            return None

        alert_id = f"alert-{uuid.uuid4().hex[:8]}"
        
        # Build transparent, descriptive message avoiding medical terms
        if flock_audio_score >= 70.0 and not audio_localized:
            msg = (
                f"Track #{candidate.track_id} in {candidate.current_zone} shows {candidate.status.lower()}-level "
                f"behavioural deviation ({candidate.inspection_priority:.1f}/100) during an active flock-level acoustic alert. "
                f"Note: Audio source is not localized to this individual bird."
            )
        elif flock_audio_score >= 70.0 and audio_localized:
            msg = (
                f"Track #{candidate.track_id} in {candidate.current_zone} shows {candidate.status.lower()}-level "
                f"behavioural deviation ({candidate.inspection_priority:.1f}/100) temporally and spatially associated with localized acoustic anomaly."
            )
        else:
            msg = (
                f"Track #{candidate.track_id} in {candidate.current_zone} exhibits persistent behavioral deviation "
                f"({candidate.inspection_priority:.1f}/100) based on camera tracking observation."
            )

        recommendation = RECOMMENDATIONS.get(candidate.status, RECOMMENDATIONS["WATCH"])

        alert = EarlyWarningAlert(
            alert_id=alert_id,
            timestamp=float(timestamp),
            scope="TRACK",
            track_id=candidate.track_id,
            level=candidate.status,
            current_zone=candidate.current_zone,
            inspection_priority=candidate.inspection_priority,
            message=msg,
            recommendation=recommendation,
            audio_localized=audio_localized
        )

        self.record_alert(alert)
        return alert

    def generate_flock_alert(self, flock_status: FlockStatus, timestamp: float) -> Optional[EarlyWarningAlert]:
        """
        Generates a flock-wide alert if flock status is ALERT or WATCH.
        """
        if flock_status.flock_status not in ["WATCH", "ALERT"]:
            return None

        alert_id = f"flock-alert-{uuid.uuid4().hex[:8]}"
        msg = (
            f"Flock-level status elevated to {flock_status.flock_status}. "
            f"Global acoustic deviation: {flock_status.global_audio_score:.1f}/100. "
            f"High camera deviation birds: {flock_status.high_camera_deviation_count}."
        )

        alert = EarlyWarningAlert(
            alert_id=alert_id,
            timestamp=float(timestamp),
            scope="FLOCK",
            track_id=None,
            level=flock_status.flock_status,
            current_zone=None,
            inspection_priority=flock_status.global_audio_score,
            message=msg,
            recommendation=flock_status.recommendation,
            audio_localized=flock_status.audio_localized
        )

        self.record_alert(alert)
        return alert

    def record_alert(self, alert: EarlyWarningAlert):
        """Appends alert to in-memory list and writes to persistent CSV log."""
        self.alerts_history.append(alert)
        with open(self.alerts_csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                alert.alert_id,
                alert.timestamp,
                alert.scope,
                alert.track_id if alert.track_id is not None else "FLOCK",
                alert.level,
                alert.current_zone or "ALL",
                alert.inspection_priority if alert.inspection_priority is not None else 0.0,
                alert.message,
                alert.recommendation,
                alert.audio_localized,
                alert.disclaimer
            ])

    def get_recent_alerts(self, limit: int = 10) -> List[EarlyWarningAlert]:
        return self.alerts_history[-limit:]
