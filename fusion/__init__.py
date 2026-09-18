"""
FlockSense Multimodal Fusion Package.
Bridges bioacoustic anomaly detection and computer-vision tracking into actionable
per-bird inspection priorities and flock early-warning alerts.
"""

from fusion.models import (
    AudioEvent,
    CameraTrackState,
    InspectionCandidate,
    FlockStatus,
    EarlyWarningAlert
)
from fusion.audio_event import AudioEventManager
from fusion.temporal_memory import TrackTemporalMemory, TemporalMemoryManager
from fusion.candidate_ranker import CandidateRanker
from fusion.alert_engine import AlertEngine
from fusion.fusion_engine import FusionEngine
from fusion.state_manager import FusionStateManager

__all__ = [
    "AudioEvent",
    "CameraTrackState",
    "InspectionCandidate",
    "FlockStatus",
    "EarlyWarningAlert",
    "AudioEventManager",
    "TrackTemporalMemory",
    "TemporalMemoryManager",
    "CandidateRanker",
    "AlertEngine",
    "FusionEngine",
    "FusionStateManager"
]
