"""
Pydantic schemas for FlockSense API request and response bodies.
"""

from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

# -----------------------------------------------------------------------------
# Base / Error Schemas
# -----------------------------------------------------------------------------
class APIErrorDetail(BaseModel):
    code: str
    message: str

class APIError(BaseModel):
    success: bool = False
    error: APIErrorDetail

# -----------------------------------------------------------------------------
# Health & System Info Schemas
# -----------------------------------------------------------------------------
class ComponentStatus(BaseModel):
    audio_model: bool
    camera_anomaly_model: bool
    fusion_engine: bool
    roboflow_configured: bool

class ValidationStatus(BaseModel):
    camera_real_world_validated: bool = False
    audio_localization_available: bool = False
    medical_validation: bool = False
    fusion_weights_status: str = "PROVISIONAL_DEVELOPMENT_WEIGHTS"

class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "FlockSense API"
    components: ComponentStatus
    validation: ValidationStatus

class SystemInfoResponse(BaseModel):
    audio_model: str
    behavior_model: str
    tracker: str
    camera_anomaly_model: str
    fusion_mode: str
    version: str
    validation: Dict[str, Any]
    disclaimer: str

# -----------------------------------------------------------------------------
# Flock Status Schemas
# -----------------------------------------------------------------------------
class GlobalAudioContext(BaseModel):
    score: float
    status: str
    active: bool
    localized: bool = False
    scope: str = "FLOCK"
    last_event_time: Optional[float] = None
    interpretation: str = ""

class TrackingSummary(BaseModel):
    active_tracks: int
    high_deviation_tracks: int
    watch_deviation_tracks: int = 0

class FlockStatusResponse(BaseModel):
    flock_status: str
    global_audio: GlobalAudioContext
    tracking: TrackingSummary
    top_candidate_ids: List[int]
    fusion_mode: str
    timestamp: float
    recommendation: str
    disclaimer: str

# -----------------------------------------------------------------------------
# Candidate & Track Schemas
# -----------------------------------------------------------------------------
class AudioContextSummary(BaseModel):
    global_audio_active: bool
    audio_localized: bool = False
    urgency_boost: float = 0.0

class CandidateItem(BaseModel):
    rank: int
    track_id: int
    current_zone: str
    initial_evidence_zone: str
    behavior: str
    camera_deviation_score: float
    persistence_score: float
    inspection_priority: float
    status: str
    tracking_status: str
    reasons: List[str]
    audio_context: AudioContextSummary
    last_seen_timestamp: float

class CandidateResponse(BaseModel):
    total_candidates: int
    candidates: List[CandidateItem]
    disclaimer: str

class TrackSummaryItem(BaseModel):
    track_id: int
    tracking_status: str
    current_zone: str
    previous_zone: str
    initial_evidence_zone: str
    current_behavior: str
    stable_behavior: str
    behavior_confidence: float
    movement_rate: float
    stationary_duration: float
    camera_deviation_score: float
    inspection_priority: float
    status: str
    last_seen: float

class TrackListResponse(BaseModel):
    total_tracks: int
    tracks: List[TrackSummaryItem]

class TrackDetailResponse(BaseModel):
    track_id: int
    tracking_status: str
    current_zone: str
    previous_zone: str
    initial_evidence_zone: str
    position: Tuple[float, float]
    bbox: List[float]
    current_behavior: str
    stable_behavior: str
    behavior_confidence: float
    movement_rate: float
    distance_travelled_pixels: float
    stationary_duration: float
    stationary_ratio: float
    relative_isolation_score: float
    relative_activity: float
    camera_deviation_score: float
    persistence_score: float
    inspection_priority: float
    fusion_status: str
    reasons: List[str]
    audio_context: AudioContextSummary
    first_seen: float
    last_seen: float
    disclaimer: str

# -----------------------------------------------------------------------------
# Alerts Schemas
# -----------------------------------------------------------------------------
class AlertItem(BaseModel):
    alert_id: str
    timestamp: float
    level: str
    scope: str
    track_id: Optional[int] = None
    current_zone: Optional[str] = None
    inspection_priority: Optional[float] = None
    message: str
    recommendation: str
    audio_localized: bool = False
    disclaimer: str

class AlertListResponse(BaseModel):
    total_alerts: int
    alerts: List[AlertItem]

# -----------------------------------------------------------------------------
# Audio Analysis Schemas
# -----------------------------------------------------------------------------
class AudioInferenceResult(BaseModel):
    prediction: str
    status: str
    overall_abnormality_probability_pct: float
    score: float
    scope: str = "FLOCK"
    localized: bool = False
    duration_seconds: float
    windows_analyzed: int
    high_risk_windows: int
    interpretation: str
    recommended_action: str

class FusionContextUpdate(BaseModel):
    flock_status: str
    global_audio_score: float
    top_candidate_ids: List[int]

class AudioAnalysisResponse(BaseModel):
    success: bool
    filename: str
    audio: AudioInferenceResult
    fusion: FusionContextUpdate
    disclaimer: str

# -----------------------------------------------------------------------------
# Dev Mode Ingestion Schema
# -----------------------------------------------------------------------------
class DevTrackStateIngest(BaseModel):
    track_id: int
    timestamp: Optional[float] = None
    current_zone: str = "ZONE_1"
    previous_zone: Optional[str] = None
    current_behavior: str = "standing"
    stable_behavior: Optional[str] = "standing"
    behavior_confidence: float = 0.9
    bbox: Optional[List[float]] = None
    position: Optional[List[float]] = None
    camera_anomaly_score: float = 0.0
    camera_anomaly_status: Optional[str] = "NORMAL_PATTERN"
    movement_rate: float = 10.0
    distance_travelled_pixels: float = 20.0
    stationary_duration: float = 1.0
    stationary_ratio: float = 0.2
    relative_isolation_score: float = 0.25
    relative_activity: float = 1.0
    camera_anomaly_reasons: Optional[List[str]] = None

# -----------------------------------------------------------------------------
# Monitoring Session Schemas
# -----------------------------------------------------------------------------
class SessionStatusResponse(BaseModel):
    session_active: bool
    session_id: Optional[str]
    start_time: Optional[float]
    duration_seconds: Optional[float]
    mode: str
