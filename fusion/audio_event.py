"""
Audio Event Handler and Parser for FlockSense.
Bridges raw output from the ResNet18 audio inference pipeline into standard AudioEvents.
Manages event deduplication, sliding window merging, and expiration.
"""

import uuid
from typing import Dict, List, Any, Optional
from fusion.models import AudioEvent

class AudioEventManager:
    """
    Manages and parses audio anomaly events from the FlockSense audio inference pipeline.
    Maintains a rolling buffer of recent acoustic events, handles temporal deduplication,
    and determines current global flock acoustic urgency.
    """
    def __init__(self, timeout_seconds: float = 15.0, deduplication_seconds: float = 2.0):
        self.timeout_seconds = float(timeout_seconds)
        self.deduplication_seconds = float(deduplication_seconds)
        self.recent_events: List[AudioEvent] = []

    def create_event_from_inference_dict(
        self,
        inference_result: Dict[str, Any],
        timestamp_start: float = 0.0,
        timestamp_end: Optional[float] = None,
        localization_available: bool = False,
        estimated_zone: Optional[str] = None
    ) -> AudioEvent:
        """
        Parses output from FlockSenseAudioInference.analyze_audio_file into an AudioEvent.
        """
        dur = float(inference_result.get("duration_seconds", 3.0))
        t_end = timestamp_end if timestamp_end is not None else (timestamp_start + dur)
        
        # Abnormality probability from inference result (0.0 to 1.0)
        overall_pct = float(inference_result.get("overall_abnormality_probability_pct", 0.0))
        abnormal_prob = overall_pct / 100.0
        
        # Status mapping
        raw_status = inference_result.get("status", "NORMAL")
        if raw_status == "ALERT":
            status = "HIGH_ACOUSTIC_DEVIATION"
        elif raw_status == "WATCH":
            status = "WATCH_ACOUSTIC_DEVIATION"
        else:
            status = "NORMAL_ACOUSTIC_PATTERN"

        event = AudioEvent(
            event_id=f"audio-{uuid.uuid4().hex[:8]}",
            timestamp_start=float(timestamp_start),
            timestamp_end=float(t_end),
            abnormal_probability=abnormal_prob,
            confidence=round(max(0.70, abnormal_prob), 4),
            status=status,
            audio_score=overall_pct,
            localization_available=bool(localization_available),
            estimated_zone=estimated_zone,
            audio_scope="ZONE" if (localization_available and estimated_zone) else "FLOCK",
            interpretation=inference_result.get("interpretation", "")
        )
        return event

    def add_event(self, event: AudioEvent) -> AudioEvent:
        """
        Adds an audio event with temporal deduplication to avoid double-counting overlapping windows.
        """
        # Deduplication check: if there is an existing event in the same time vicinity
        for existing in self.recent_events:
            if abs(existing.timestamp_start - event.timestamp_start) <= self.deduplication_seconds:
                # Merge into highest probability event
                if event.abnormal_probability > existing.abnormal_probability:
                    existing.abnormal_probability = event.abnormal_probability
                    existing.audio_score = event.audio_score
                    existing.status = event.status
                    existing.timestamp_end = max(existing.timestamp_end, event.timestamp_end)
                    existing.interpretation = event.interpretation
                return existing

        self.recent_events.append(event)
        return event

    def get_active_events(self, current_time: float) -> List[AudioEvent]:
        """Returns all audio events that are within the active context window."""
        self.cleanup_expired_events(current_time)
        return [
            e for e in self.recent_events 
            if (current_time - e.timestamp_end) <= self.timeout_seconds
        ]

    def get_current_global_audio_state(self, current_time: float) -> Dict[str, Any]:
        """
        Computes the current global flock acoustic score and alert level.
        If no audio event has occurred within the timeout window, score smoothly decays to 0.
        """
        active = self.get_active_events(current_time)
        if not active:
            return {
                "global_audio_score": 0.0,
                "global_audio_status": "NORMAL",
                "active_events_count": 0,
                "audio_scope": "FLOCK",
                "audio_localized": False,
                "interpretation": "Acoustic baseline normal; no recent acoustic anomalies detected."
            }

        # Max score among active events determines urgency
        max_event = max(active, key=lambda e: e.audio_score)
        
        # Check if localized in future mode
        any_localized = any(e.localization_available for e in active)

        if max_event.audio_score >= 70.0:
            status = "ALERT"
        elif max_event.audio_score >= 35.0:
            status = "WATCH"
        else:
            status = "NORMAL"

        return {
            "global_audio_score": max_event.audio_score,
            "global_audio_status": status,
            "active_events_count": len(active),
            "audio_scope": "ZONE" if any_localized else "FLOCK",
            "audio_localized": any_localized,
            "latest_event_id": max_event.event_id,
            "interpretation": max_event.interpretation
        }

    def cleanup_expired_events(self, current_time: float):
        """Removes audio events older than timeout_seconds * 2."""
        cutoff = current_time - (self.timeout_seconds * 2.0)
        self.recent_events = [e for e in self.recent_events if e.timestamp_end >= cutoff]
