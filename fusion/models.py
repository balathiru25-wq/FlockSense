"""
Data structures and domain models for FlockSense Multimodal Fusion.
Defines clean schemas for audio events, camera tracking states, inspection candidates,
flock status, and early-warning alerts.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

@dataclass
class AudioEvent:
    """
    Standard representation of an acoustic event detected by the bioacoustics model.
    In current deployment, localization is not available, representing global flock context.
    """
    event_id: str
    timestamp_start: float
    timestamp_end: float
    abnormal_probability: float  # 0.0 to 1.0 (from ResNet18 Unhealthy class)
    confidence: float            # Model classification confidence
    status: str                  # "NORMAL" | "WATCH" | "ALERT" | "HIGH_ACOUSTIC_DEVIATION"
    audio_score: float           # 0.0 to 100.0 (abnormal_probability * 100)
    
    # Future-ready spatial localization fields
    localization_available: bool = False
    estimated_zone: Optional[str] = None
    source_position: Optional[Tuple[float, float]] = None
    audio_scope: str = "FLOCK"   # "FLOCK" (global) or "ZONE" or "INDIVIDUAL"
    interpretation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp_start": round(self.timestamp_start, 2),
            "timestamp_end": round(self.timestamp_end, 2),
            "abnormal_probability": round(self.abnormal_probability, 4),
            "confidence": round(self.confidence, 4),
            "status": self.status,
            "audio_score": round(self.audio_score, 1),
            "localization_available": self.localization_available,
            "estimated_zone": self.estimated_zone,
            "source_position": list(self.source_position) if self.source_position else None,
            "audio_scope": self.audio_scope,
            "interpretation": self.interpretation
        }

@dataclass
class CameraTrackState:
    """
    Standardized per-bird behavioral and spatial observation state from tracking & anomaly models.
    """
    track_id: int
    timestamp: float
    current_zone: str
    previous_zone: str = "UNKNOWN"
    initial_evidence_zone: str = "UNKNOWN"
    current_behavior: str = "unknown"
    stable_behavior: str = "unknown"
    
    # Coordinates & tracking status
    bbox: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    position: Tuple[float, float] = (0.0, 0.0)
    tracking_status: str = "ACTIVE" # "ACTIVE" | "TEMPORARILY_LOST" | "RECOVERED" | "TRACK_ENDED"
    last_seen_timestamp: float = 0.0

    # Behavioral metrics & anomaly scores
    camera_anomaly_score: float = 0.0
    camera_status: str = "NORMAL_PATTERN" # "NORMAL_PATTERN" | "WATCH_DEVIATION" | "HIGH_DEVIATION"
    movement_rate: float = 0.0
    distance_travelled_pixels: float = 0.0
    stationary_duration: float = 0.0
    stationary_ratio: float = 0.0
    relative_isolation_score: float = 0.0
    relative_activity: float = 1.0
    camera_reasons: List[str] = field(default_factory=list)
    raw_anomaly_score: Optional[float] = None
    validation_status: str = "PROTOTYPE_ONLY_SYNTHETIC_DATA"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "timestamp": round(self.timestamp, 2),
            "current_zone": self.current_zone,
            "previous_zone": self.previous_zone,
            "initial_evidence_zone": self.initial_evidence_zone,
            "current_behavior": self.current_behavior,
            "stable_behavior": self.stable_behavior,
            "bbox": [round(x, 1) for x in self.bbox],
            "position": [round(self.position[0], 1), round(self.position[1], 1)],
            "tracking_status": self.tracking_status,
            "last_seen_timestamp": round(self.last_seen_timestamp, 2),
            "camera_anomaly_score": round(self.camera_anomaly_score, 1),
            "camera_status": self.camera_status,
            "movement_rate": round(self.movement_rate, 1),
            "distance_travelled_pixels": round(self.distance_travelled_pixels, 1),
            "stationary_duration": round(self.stationary_duration, 1),
            "stationary_ratio": round(self.stationary_ratio, 3),
            "relative_isolation_score": round(self.relative_isolation_score, 4),
            "relative_activity": round(self.relative_activity, 3),
            "camera_reasons": self.camera_reasons,
            "raw_anomaly_score": self.raw_anomaly_score,
            "validation_status": self.validation_status
        }

@dataclass
class InspectionCandidate:
    """
    Ranked inspection candidate for farmer decision support.
    Represents inspection priority, NOT disease probability.
    """
    rank: int
    track_id: int
    current_zone: str
    initial_evidence_zone: str
    inspection_priority: float # 0.0 - 100.0
    status: str                # "NORMAL" | "WATCH" | "ALERT"
    tracking_status: str       # "ACTIVE" | "TEMPORARILY_LOST"
    camera_deviation_score: float
    persistence_score: float
    audio_urgency_boost: float
    audio_localized: bool
    reasons: List[str]
    last_seen_timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "track_id": self.track_id,
            "current_zone": self.current_zone,
            "initial_evidence_zone": self.initial_evidence_zone,
            "inspection_priority": round(self.inspection_priority, 1),
            "status": self.status,
            "tracking_status": self.tracking_status,
            "camera_deviation_score": round(self.camera_deviation_score, 1),
            "persistence_score": round(self.persistence_score, 1),
            "audio_urgency_boost": round(self.audio_urgency_boost, 1),
            "audio_localized": self.audio_localized,
            "reasons": self.reasons,
            "last_seen_timestamp": round(self.last_seen_timestamp, 2)
        }

@dataclass
class FlockStatus:
    """
    Overall flock-level early warning health and activity status.
    """
    flock_status: str                 # "NORMAL" | "WATCH" | "ALERT"
    global_audio_score: float         # 0.0 - 100.0
    global_audio_status: str          # "NORMAL" | "WATCH" | "ALERT"
    active_audio_event_count: int
    audio_localized: bool
    total_active_tracks: int
    high_camera_deviation_count: int  # Birds with deviation >= 70
    watch_camera_deviation_count: int # Birds with deviation between 45 and 70
    top_candidate_ids: List[int]
    timestamp: float
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "flock_status": self.flock_status,
            "global_audio_score": round(self.global_audio_score, 1),
            "global_audio_status": self.global_audio_status,
            "active_audio_event_count": self.active_audio_event_count,
            "audio_localized": self.audio_localized,
            "total_active_tracks": self.total_active_tracks,
            "high_camera_deviation_count": self.high_camera_deviation_count,
            "watch_camera_deviation_count": self.watch_camera_deviation_count,
            "top_candidate_ids": self.top_candidate_ids,
            "timestamp": round(self.timestamp, 2),
            "recommendation": self.recommendation
        }

@dataclass
class EarlyWarningAlert:
    """
    Early warning alert event dispatched to farmers or dashboard.
    """
    alert_id: str
    timestamp: float
    scope: str            # "TRACK" | "FLOCK" | "ZONE"
    track_id: Optional[int]
    level: str            # "WATCH" | "ALERT"
    current_zone: Optional[str]
    inspection_priority: Optional[float]
    message: str
    recommendation: str
    audio_localized: bool = False
    disclaimer: str = "FlockSense provides early-warning screening and does not diagnose poultry disease."

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "timestamp": round(self.timestamp, 2),
            "scope": self.scope,
            "track_id": self.track_id,
            "level": self.level,
            "current_zone": self.current_zone,
            "inspection_priority": round(self.inspection_priority, 1) if self.inspection_priority is not None else None,
            "message": self.message,
            "recommendation": self.recommendation,
            "audio_localized": self.audio_localized,
            "disclaimer": self.disclaimer
        }
