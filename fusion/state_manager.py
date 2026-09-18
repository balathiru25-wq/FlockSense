"""
State Manager for FlockSense Multimodal Fusion.
Exposes a clean, thread-safe, reusable API for updating audio events, camera tracks,
querying candidates, flock status, and inspection alerts.
Ready to be connected directly to FastAPI routes in the future backend phase.
"""

from typing import Dict, List, Any, Optional
from fusion.fusion_engine import FusionEngine
from fusion.models import (
    AudioEvent,
    CameraTrackState,
    InspectionCandidate,
    FlockStatus,
    EarlyWarningAlert
)

class FusionStateManager:
    """
    Singleton-style manager wrapping FusionEngine.
    Provides the standard external interface for FlockSense services:
    - update_audio_event(event)
    - update_track_state(track_state)
    - get_flock_status()
    - get_top_candidates()
    - get_track_fusion_state(track_id)
    - get_active_alerts()
    """
    def __init__(self, config_path: str = "config/fusion_config.yaml"):
        self.engine = FusionEngine(config_path=config_path)

    def update_audio_event(self, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ingests an audio event from raw dict or AudioEvent object.
        """
        if isinstance(event_dict, AudioEvent):
            evt = self.engine.ingest_audio_event(event_dict)
        else:
            evt = AudioEvent(
                event_id=event_dict.get("event_id", "audio-manual"),
                timestamp_start=float(event_dict.get("timestamp_start", 0.0)),
                timestamp_end=float(event_dict.get("timestamp_end", 3.0)),
                abnormal_probability=float(event_dict.get("abnormal_probability", 0.0)),
                confidence=float(event_dict.get("confidence", 0.9)),
                status=event_dict.get("status", "NORMAL"),
                audio_score=float(event_dict.get("audio_score", event_dict.get("abnormal_probability", 0.0) * 100.0)),
                localization_available=bool(event_dict.get("localization_available", False)),
                estimated_zone=event_dict.get("estimated_zone"),
                audio_scope=event_dict.get("audio_scope", "FLOCK"),
                interpretation=event_dict.get("interpretation", "")
            )
            evt = self.engine.ingest_audio_event(evt)
        return evt.to_dict()

    def update_track_state(self, track_state_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ingests or updates a camera track state from dictionary representation.
        """
        if isinstance(track_state_dict, CameraTrackState):
            cand = self.engine.update_camera_track(track_state_dict)
        else:
            tstate = CameraTrackState(
                track_id=int(track_state_dict["track_id"]),
                timestamp=float(track_state_dict.get("timestamp", 0.0)),
                current_zone=track_state_dict.get("current_zone", "UNKNOWN"),
                previous_zone=track_state_dict.get("previous_zone", "UNKNOWN"),
                initial_evidence_zone=track_state_dict.get("initial_evidence_zone", "UNKNOWN"),
                current_behavior=track_state_dict.get("current_behavior", "unknown"),
                stable_behavior=track_state_dict.get("stable_behavior", "unknown"),
                bbox=track_state_dict.get("bbox", [0.0, 0.0, 0.0, 0.0]),
                position=tuple(track_state_dict.get("position", (0.0, 0.0))),
                tracking_status=track_state_dict.get("tracking_status", "ACTIVE"),
                last_seen_timestamp=float(track_state_dict.get("last_seen", track_state_dict.get("timestamp", 0.0))),
                camera_anomaly_score=float(track_state_dict.get("camera_anomaly_score", 0.0)),
                camera_status=track_state_dict.get("camera_anomaly_status", track_state_dict.get("camera_status", "NORMAL_PATTERN")),
                movement_rate=float(track_state_dict.get("movement_rate", track_state_dict.get("movement_rate_pixels_per_sec", 0.0))),
                distance_travelled_pixels=float(track_state_dict.get("distance_travelled_pixels", 0.0)),
                stationary_duration=float(track_state_dict.get("stationary_duration", track_state_dict.get("stationary_duration_seconds", 0.0))),
                stationary_ratio=float(track_state_dict.get("stationary_ratio", 0.0)),
                relative_isolation_score=float(track_state_dict.get("relative_isolation_score", 0.25)),
                relative_activity=float(track_state_dict.get("relative_activity", 1.0)),
                camera_reasons=track_state_dict.get("camera_anomaly_reasons", track_state_dict.get("camera_reasons", [])),
                raw_anomaly_score=track_state_dict.get("raw_anomaly_score"),
                validation_status=track_state_dict.get("validation_status", "PROTOTYPE_ONLY_SYNTHETIC_DATA")
            )
            cand = self.engine.update_camera_track(tstate)

        return cand.to_dict()

    def get_flock_status(self, current_time: Optional[float] = None) -> Dict[str, Any]:
        """Returns flock-level early warning summary."""
        t = current_time if current_time is not None else 0.0
        return self.engine.get_flock_status(current_time=t).to_dict()

    def get_top_candidates(self, current_time: Optional[float] = None) -> List[Dict[str, Any]]:
        """Returns ranked list of top inspection candidates."""
        candidates = self.engine.get_top_candidates(current_time=current_time)
        return [c.to_dict() for c in candidates]

    def get_track_fusion_state(self, track_id: int) -> Optional[Dict[str, Any]]:
        """Returns detailed fusion and temporal tracking state for an individual bird."""
        return self.engine.get_track_fusion_state(track_id)

    def get_active_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns recent inspection alerts."""
        alerts = self.engine.get_active_alerts(limit=limit)
        return [a.to_dict() for a in alerts]
