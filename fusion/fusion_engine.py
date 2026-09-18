"""
Core Multimodal Fusion Engine for FlockSense.
Combines:
- Global Flock Audio Abnormality (context/urgency)
- Per-Bird Camera Behavioural Deviation (primary ranking driver)
- Temporal Persistence & Historical Memory
- Temporary Track IDs & Zone Mobility
To calculate:
- Per-Bird Inspection Priority Scores (0-100)
- Flock-Level Early Warning Status (NORMAL / WATCH / ALERT)
- Detailed Explainability Reasons

IMPORTANT:
All weights and thresholds are PROVISIONAL DEVELOPMENT PARAMETERS.
Inspection Priority is NOT a disease probability.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from fusion.models import (
    AudioEvent,
    CameraTrackState,
    InspectionCandidate,
    FlockStatus,
    EarlyWarningAlert
)
from fusion.audio_event import AudioEventManager
from fusion.temporal_memory import TemporalMemoryManager
from fusion.candidate_ranker import CandidateRanker
from fusion.alert_engine import AlertEngine

class FusionEngine:
    """
    Coordinates multimodal signal processing between audio bioacoustics and vision tracking.
    """
    def __init__(self, config_path: str = "config/fusion_config.yaml"):
        self.config_path = Path(config_path)
        self.load_config()

        # Initialize sub-modules
        sync_cfg = self.config.get("synchronization", {})
        mem_cfg = self.config.get("temporal_memory", {})
        rank_cfg = self.config.get("candidate_ranker", {})
        log_cfg = self.config.get("logging", {})

        self.audio_manager = AudioEventManager(
            timeout_seconds=sync_cfg.get("audio_context_timeout_seconds", 15.0),
            deduplication_seconds=sync_cfg.get("event_deduplication_window_seconds", 2.0)
        )
        self.memory_manager = TemporalMemoryManager(
            history_length=mem_cfg.get("score_history_length", 6),
            smoothing_alpha=mem_cfg.get("smoothing_alpha", 0.35),
            decay_rate=mem_cfg.get("decay_rate_per_normal_window", 0.25)
        )
        self.ranker = CandidateRanker(
            top_n=rank_cfg.get("default_top_n", 5),
            include_temporarily_lost=rank_cfg.get("include_temporarily_lost", True)
        )
        self.alert_engine = AlertEngine(
            alerts_csv_path=log_cfg.get("alerts_csv", "outputs/fusion/logs/alerts.csv")
        )

        # Active tracking states: Dict[int, CameraTrackState]
        self.active_tracks: Dict[int, CameraTrackState] = {}
        self.jsonl_log_path = Path(log_cfg.get("fusion_events_jsonl", "outputs/fusion/logs/fusion_events.jsonl"))
        self.jsonl_log_path.parent.mkdir(parents=True, exist_ok=True)

    def load_config(self):
        if not self.config_path.exists():
            # Fallback default configuration
            self.config = {
                "fusion_mode": "GLOBAL_AUDIO",
                "weights": {
                    "camera_deviation_weight": 0.50,
                    "persistence_weight": 0.25,
                    "isolation_weight": 0.15,
                    "activity_deviation_weight": 0.10,
                    "global_audio_urgency_max_boost": 15.0,
                    "audio_boost_camera_threshold": 45.0
                },
                "thresholds": {
                    "status_levels": {
                        "NORMAL": {"max_score": 45.0},
                        "WATCH": {"min_score": 45.0, "max_score": 70.0},
                        "ALERT": {"min_score": 70.0, "max_score": 100.0}
                    }
                }
            }
            return

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    # -------------------------------------------------------------------------
    # Audio Ingestion & Processing
    # -------------------------------------------------------------------------
    def ingest_audio_event(self, event: AudioEvent) -> AudioEvent:
        """Ingests and records an acoustic event."""
        return self.audio_manager.add_event(event)

    def ingest_audio_inference(
        self,
        inference_result: Dict[str, Any],
        timestamp_start: float,
        localization_available: bool = False,
        estimated_zone: Optional[str] = None
    ) -> AudioEvent:
        """Helper to ingest raw dictionary output from FlockSenseAudioInference."""
        event = self.audio_manager.create_event_from_inference_dict(
            inference_result=inference_result,
            timestamp_start=timestamp_start,
            localization_available=localization_available,
            estimated_zone=estimated_zone
        )
        return self.ingest_audio_event(event)

    # -------------------------------------------------------------------------
    # Camera Track Ingestion & Processing
    # -------------------------------------------------------------------------
    def update_camera_track(self, track_state: CameraTrackState) -> InspectionCandidate:
        """
        Ingests or updates the behavioral observation for a tracked chicken.
        Calculates multimodal inspection priority and returns candidate.
        """
        tid = track_state.track_id
        current_time = track_state.timestamp

        # Update or record track state
        if tid not in self.active_tracks:
            track_state.initial_evidence_zone = track_state.current_zone
            self.active_tracks[tid] = track_state
        else:
            # Preserve initial evidence zone across migrations
            existing = self.active_tracks[tid]
            track_state.initial_evidence_zone = existing.initial_evidence_zone
            track_state.previous_zone = existing.current_zone
            self.active_tracks[tid] = track_state

        # 1. Update temporal memory
        smoothed_dev, persistence_score = self.memory_manager.update_track(
            track_id=tid,
            raw_deviation_score=track_state.camera_anomaly_score,
            current_zone=track_state.current_zone,
            timestamp=current_time,
            camera_status=track_state.camera_status
        )

        # 2. Get active audio context at current timestamp
        global_audio_state = self.audio_manager.get_current_global_audio_state(current_time)
        global_audio_score = global_audio_state.get("global_audio_score", 0.0)
        audio_localized = global_audio_state.get("audio_localized", False)

        # 3. Calculate multimodal inspection priority score
        candidate = self._calculate_inspection_candidate(
            track_state=track_state,
            smoothed_deviation=smoothed_dev,
            persistence_score=persistence_score,
            global_audio_score=global_audio_score,
            audio_localized=audio_localized,
            current_time=current_time
        )

        # 4. Check for alerts
        self.alert_engine.generate_track_alert(
            candidate=candidate,
            timestamp=current_time,
            flock_audio_score=global_audio_score,
            audio_localized=audio_localized
        )

        # 5. Log fusion event to JSONL
        self._log_fusion_event(candidate, track_state, global_audio_state)

        return candidate

    def mark_track_lost(self, track_id: int):
        if track_id in self.active_tracks:
            self.active_tracks[track_id].tracking_status = "TEMPORARILY_LOST"
        self.memory_manager.mark_lost(track_id)

    def mark_track_ended(self, track_id: int):
        if track_id in self.active_tracks:
            self.active_tracks[track_id].tracking_status = "TRACK_ENDED"
        self.memory_manager.mark_ended(track_id)

    # -------------------------------------------------------------------------
    # Multimodal Inspection Priority Calculation
    # -------------------------------------------------------------------------
    def _calculate_inspection_candidate(
        self,
        track_state: CameraTrackState,
        smoothed_deviation: float,
        persistence_score: float,
        global_audio_score: float,
        audio_localized: bool,
        current_time: float
    ) -> InspectionCandidate:
        """
        Core multimodal calculation of per-bird inspection priority score (0–100).
        Follows FlockSense architectural principle:
        Camera behavioral deviation is primary.
        Flock acoustic abnormality acts as an urgency context modifier for elevated birds.
        """
        weights = self.config.get("weights", {})
        w_dev = float(weights.get("camera_deviation_weight", 0.50))
        w_pers = float(weights.get("persistence_weight", 0.25))
        w_iso = float(weights.get("isolation_weight", 0.15))
        w_act = float(weights.get("activity_deviation_weight", 0.10))

        # Spatial isolation component (scaled 0 to 100, where baseline is ~25, max 50+)
        # relative_isolation_score is roughly 0.15 - 0.50
        iso_val = float(track_state.relative_isolation_score)
        iso_score = min(100.0, max(0.0, (iso_val - 0.20) * 333.3))

        # Activity deviation component (divergence from flock median activity=1.0)
        act_val = float(track_state.relative_activity)
        # Lethargic (act < 0.3) or agitated (act > 2.5) both score higher activity deviation
        if act_val < 1.0:
            act_dev_score = (1.0 - act_val) * 100.0
        else:
            act_dev_score = min(100.0, (act_val - 1.0) * 50.0)

        # Baseline behavioral inspection priority (pure camera evidence)
        base_priority = (
            w_dev * smoothed_deviation +
            w_pers * persistence_score +
            w_iso * iso_score +
            w_act * act_dev_score
        )

        # Audio Urgency Context Modifier
        # CRITICAL RULE: If a bird's camera behavior is normal (< threshold), audio boost is ZERO.
        # This prevents healthy chickens from becoming false-positive alerts just because an audio anomaly exists.
        max_boost = float(weights.get("global_audio_urgency_max_boost", 15.0))
        cam_thresh = float(weights.get("audio_boost_camera_threshold", 45.0))
        audio_boost = 0.0

        if global_audio_score >= 35.0 and smoothed_deviation >= cam_thresh:
            # Scale boost proportionally to audio severity and bird's camera deviation
            audio_factor = (global_audio_score - 35.0) / 65.0 # 0.0 to 1.0
            cam_factor = min(1.0, (smoothed_deviation - cam_thresh) / 30.0) # 0.0 to 1.0
            audio_boost = max_boost * audio_factor * cam_factor

        # Spatial Localized Audio Boost (Future Mode B path)
        if audio_localized and self.config.get("fusion_mode") == "LOCALIZED_AUDIO":
            active_events = self.audio_manager.get_active_events(current_time)
            for ae in active_events:
                if ae.estimated_zone and ae.estimated_zone == track_state.current_zone:
                    audio_boost += 15.0 # Spatial congruence bonus

        final_priority = float(min(100.0, max(0.0, base_priority + audio_boost)))

        # Status determination
        if final_priority >= 70.0:
            status = "ALERT"
        elif final_priority >= 45.0:
            status = "WATCH"
        else:
            status = "NORMAL"

        # Construct explainability reasons
        reasons = self._build_candidate_reasons(
            track_state=track_state,
            smoothed_deviation=smoothed_deviation,
            persistence_score=persistence_score,
            global_audio_score=global_audio_score,
            audio_boost=audio_boost,
            audio_localized=audio_localized
        )

        candidate = InspectionCandidate(
            rank=0, # Assigned later by ranker
            track_id=track_state.track_id,
            current_zone=track_state.current_zone,
            initial_evidence_zone=track_state.initial_evidence_zone,
            inspection_priority=final_priority,
            status=status,
            tracking_status=track_state.tracking_status,
            camera_deviation_score=smoothed_deviation,
            persistence_score=persistence_score,
            audio_urgency_boost=audio_boost,
            audio_localized=audio_localized,
            reasons=reasons,
            last_seen_timestamp=track_state.timestamp
        )
        return candidate

    def _build_candidate_reasons(
        self,
        track_state: CameraTrackState,
        smoothed_deviation: float,
        persistence_score: float,
        global_audio_score: float,
        audio_boost: float,
        audio_localized: bool
    ) -> List[str]:
        """Generates transparent, rule-backed explanations for the candidate's inspection priority."""
        reasons = []

        # Camera explainability from model
        if track_state.camera_reasons:
            for r in track_state.camera_reasons:
                if "within normal" not in r:
                    reasons.append(r)

        # Persistence reasoning
        if persistence_score >= 60.0:
            reasons.append(f"behavioural deviation sustained across multiple observation windows (persistence: {persistence_score:.0f}/100)")
        elif persistence_score < 30.0 and smoothed_deviation >= 50.0:
            reasons.append("recent deviation spike (under observation for temporal persistence)")

        # Zone movement context
        if track_state.current_zone != track_state.initial_evidence_zone and track_state.initial_evidence_zone != "UNKNOWN":
            reasons.append(f"bird transitioned from {track_state.initial_evidence_zone} to {track_state.current_zone} while maintaining elevated deviation profile")

        # Audio context explanation
        if global_audio_score >= 70.0 and audio_boost > 0:
            if audio_localized:
                reasons.append(f"spatially associated with active acoustic anomaly in {track_state.current_zone} (urgency boost: +{audio_boost:.1f})")
            else:
                reasons.append(
                    f"flock-wide acoustic alert currently active (urgency boost: +{audio_boost:.1f}). "
                    f"Notice: Audio source is not localized to this bird"
                )
        elif global_audio_score >= 70.0 and audio_boost == 0.0:
            reasons.append("flock-wide acoustic alert active, but camera behaviour remains normal (no individual attribution)")

        if not reasons:
            reasons.append("behaviour patterns and flock acoustic environment within normal baseline bounds")

        return reasons

    # -------------------------------------------------------------------------
    # Candidate Ranking & Flock Status Queries
    # -------------------------------------------------------------------------
    def get_top_candidates(self, current_time: Optional[float] = None) -> List[InspectionCandidate]:
        """Computes and ranks all current active inspection candidates."""
        candidates = []
        for tid, tstate in self.active_tracks.items():
            if tstate.tracking_status == "TRACK_ENDED":
                continue
            
            # Recompute candidate score with latest audio context
            mem = self.memory_manager.get_or_create(tid, initial_zone=tstate.current_zone)
            pers_score = mem.compute_persistence_score()
            
            eval_time = current_time if current_time is not None else tstate.timestamp
            global_audio = self.audio_manager.get_current_global_audio_state(eval_time)
            
            cand = self._calculate_inspection_candidate(
                track_state=tstate,
                smoothed_deviation=mem.smoothed_score,
                persistence_score=pers_score,
                global_audio_score=global_audio.get("global_audio_score", 0.0),
                audio_localized=global_audio.get("audio_localized", False),
                current_time=eval_time
            )
            candidates.append(cand)

        return self.ranker.rank_candidates(candidates)

    def get_flock_status(self, current_time: float) -> FlockStatus:
        """
        Synthesizes flock-level early warning status across all sensors.
        """
        audio_state = self.audio_manager.get_current_global_audio_state(current_time)
        audio_score = audio_state.get("global_audio_score", 0.0)
        audio_status = audio_state.get("global_audio_status", "NORMAL")
        audio_localized = audio_state.get("audio_localized", False)

        ranked_candidates = self.get_top_candidates(current_time)
        
        # Count high-deviation and watch-deviation birds
        high_cam = sum(1 for c in ranked_candidates if c.camera_deviation_score >= 70.0)
        watch_cam = sum(1 for c in ranked_candidates if 45.0 <= c.camera_deviation_score < 70.0)
        total_active = len([t for t in self.active_tracks.values() if t.tracking_status != "TRACK_ENDED"])

        # Determine flock-level status:
        # ALERT if audio alert active OR multiple birds show high camera deviation
        if audio_status == "ALERT" or high_cam >= 2:
            flock_stat = "ALERT"
            rec = "Significant flock acoustic or behavioral deviation detected. Promptly inspect the shed, high-priority birds, and ventilation."
        elif audio_status == "WATCH" or high_cam == 1 or watch_cam >= 2:
            flock_stat = "WATCH"
            rec = "Moderate flock deviation observed. Monitor behavioral trends and inspect highlighted candidate birds when practical."
        else:
            flock_stat = "NORMAL"
            rec = "Routine automated monitoring. Peacetime flock acoustics and behavior observed."

        top_ids = [c.track_id for c in ranked_candidates[:3]]

        status_obj = FlockStatus(
            flock_status=flock_stat,
            global_audio_score=audio_score,
            global_audio_status=audio_status,
            active_audio_event_count=audio_state.get("active_events_count", 0),
            audio_localized=audio_localized,
            total_active_tracks=total_active,
            high_camera_deviation_count=high_cam,
            watch_camera_deviation_count=watch_cam,
            top_candidate_ids=top_ids,
            timestamp=float(current_time),
            recommendation=rec
        )
        return status_obj

    def get_active_alerts(self, limit: int = 10) -> List[EarlyWarningAlert]:
        return self.alert_engine.get_recent_alerts(limit=limit)

    def get_track_fusion_state(self, track_id: int) -> Optional[Dict[str, Any]]:
        """Returns comprehensive fusion state for a single track ID."""
        if track_id not in self.active_tracks:
            return None
        tstate = self.active_tracks[track_id]
        mem = self.memory_manager.get_or_create(track_id, initial_zone=tstate.current_zone)
        return {
            "track_id": track_id,
            "track_state": tstate.to_dict(),
            "smoothed_deviation_score": mem.smoothed_score,
            "persistence_score": mem.compute_persistence_score(),
            "tracking_status": mem.tracking_status,
            "initial_evidence_zone": mem.initial_evidence_zone,
            "current_zone": mem.current_zone,
            "observation_count": len(mem.history)
        }

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------
    def _log_fusion_event(self, candidate: InspectionCandidate, track_state: CameraTrackState, global_audio_state: Dict[str, Any]):
        """Appends a structured event record to outputs/fusion/logs/fusion_events.jsonl."""
        record = {
            "timestamp": round(track_state.timestamp, 2),
            "track_id": track_state.track_id,
            "current_zone": track_state.current_zone,
            "initial_evidence_zone": track_state.initial_evidence_zone,
            "camera_anomaly_score": round(track_state.camera_anomaly_score, 1),
            "smoothed_camera_deviation": round(candidate.camera_deviation_score, 1),
            "persistence_score": round(candidate.persistence_score, 1),
            "global_audio_score": round(global_audio_state.get("global_audio_score", 0.0), 1),
            "global_audio_status": global_audio_state.get("global_audio_status", "NORMAL"),
            "audio_urgency_boost": round(candidate.audio_urgency_boost, 1),
            "fusion_mode": self.config.get("fusion_mode", "GLOBAL_AUDIO"),
            "inspection_priority": round(candidate.inspection_priority, 1),
            "status": candidate.status,
            "tracking_status": candidate.tracking_status,
            "reasons": candidate.reasons,
            "audio_localized": global_audio_state.get("audio_localized", False)
        }
        with open(self.jsonl_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
