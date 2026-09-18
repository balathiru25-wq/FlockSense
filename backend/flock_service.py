"""
Central service container and model loader for FlockSense API.
Loads the audio model, camera anomaly model, and FusionStateManager ONCE during startup.
"""

import os
import time
import uuid
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from backend.config import settings
from fusion.state_manager import FusionStateManager
from fusion.models import AudioEvent, CameraTrackState
from vision.camera_anomaly_model import CameraAnomalyDetector

logger = logging.getLogger("flocksense.backend")

class FlockSenseService:
    """
    Singleton service maintaining pre-loaded models and active fusion state.
    """
    def __init__(self):
        self.audio_inference_pipeline = None
        self.camera_anomaly_detector = None
        self.state_manager: Optional[FusionStateManager] = None
        self.is_initialized: bool = False
        
        # Session state
        self.session_active: bool = False
        self.session_id: Optional[str] = None
        self.session_start_time: Optional[float] = None

    def initialize(self):
        """
        Loads models and fusion engine once at application startup.
        """
        logger.info("Initializing FlockSense Backend Services...")

        # 1. Load Audio Inference Pipeline
        try:
            if settings.audio_checkpoint_path.exists():
                from training.audio_inference import FlockSenseAudioInference
                self.audio_inference_pipeline = FlockSenseAudioInference(
                    checkpoint_path=str(settings.audio_checkpoint_path)
                )
                logger.info("Audio Model: LOADED successfully from %s", settings.audio_checkpoint_path)
            else:
                logger.warning("Audio Model checkpoint NOT found at %s", settings.audio_checkpoint_path)
        except Exception as e:
            logger.error("Failed to load Audio Model: %s", e)
            self.audio_inference_pipeline = None

        # 2. Load Camera Anomaly Detector
        try:
            if settings.camera_anomaly_model_path.exists():
                self.camera_anomaly_detector = CameraAnomalyDetector(
                    model_path=str(settings.camera_anomaly_model_path)
                )
                logger.info("Camera Anomaly Model: LOADED successfully from %s", settings.camera_anomaly_model_path)
            else:
                logger.warning("Camera Anomaly Model NOT found at %s", settings.camera_anomaly_model_path)
        except Exception as e:
            logger.error("Failed to load Camera Anomaly Model: %s", e)
            self.camera_anomaly_detector = None

        # 3. Initialize FusionStateManager
        try:
            self.state_manager = FusionStateManager(
                config_path=str(settings.fusion_config_path)
            )
            logger.info("Fusion Engine: READY (Mode: %s)", self.state_manager.engine.config.get("fusion_mode", "GLOBAL_AUDIO"))
        except Exception as e:
            logger.error("Failed to initialize FusionStateManager: %s", e)
            self.state_manager = None

        self.is_initialized = True
        logger.info("FlockSense backend initialized successfully.")

    # -------------------------------------------------------------------------
    # Audio Analysis Service Method
    # -------------------------------------------------------------------------
    def analyze_audio_file(self, temp_audio_path: str, filename: str) -> Dict[str, Any]:
        """
        Executes inference using the pre-loaded audio model and forwards the result
        to the fusion engine as a global flock audio event.
        """
        if self.audio_inference_pipeline is None:
            raise RuntimeError("Audio model is not loaded or unavailable on server.")

        # Run inference using existing pipeline
        inference_result = self.audio_inference_pipeline.analyze_audio_file(temp_audio_path)

        # Build and ingest AudioEvent into FusionStateManager
        current_time = time.time()
        audio_score = float(inference_result.get("overall_abnormality_probability_pct", 0.0))
        abnormal_prob = audio_score / 100.0
        raw_status = inference_result.get("status", "NORMAL")
        
        status_map = {
            "ALERT": "HIGH_ACOUSTIC_DEVIATION",
            "WATCH": "WATCH_ACOUSTIC_DEVIATION",
            "NORMAL": "NORMAL_ACOUSTIC_PATTERN"
        }
        event_status = status_map.get(raw_status, "NORMAL_ACOUSTIC_PATTERN")

        evt = AudioEvent(
            event_id=f"audio-{uuid.uuid4().hex[:8]}",
            timestamp_start=current_time,
            timestamp_end=current_time + float(inference_result.get("duration_seconds", 3.0)),
            abnormal_probability=abnormal_prob,
            confidence=round(max(0.70, abnormal_prob), 4),
            status=event_status,
            audio_score=audio_score,
            localization_available=False,
            estimated_zone=None,
            audio_scope="FLOCK",
            interpretation=inference_result.get("interpretation", "")
        )

        if self.state_manager:
            self.state_manager.update_audio_event(evt)
            flock_status = self.state_manager.get_flock_status(current_time=current_time)
            top_candidates = flock_status.get("top_candidate_ids", [])
            flock_stat = flock_status.get("flock_status", "NORMAL")
        else:
            top_candidates = []
            flock_stat = "NORMAL"

        return {
            "inference_result": inference_result,
            "fusion_update": {
                "flock_status": flock_stat,
                "global_audio_score": audio_score,
                "top_candidate_ids": top_candidates
            }
        }

    # -------------------------------------------------------------------------
    # Session Management
    # -------------------------------------------------------------------------
    def start_session(self) -> Dict[str, Any]:
        self.session_active = True
        self.session_id = f"session-{uuid.uuid4().hex[:8]}"
        self.session_start_time = time.time()
        return {
            "session_active": True,
            "session_id": self.session_id,
            "start_time": self.session_start_time,
            "mode": "ACTIVE_MONITORING"
        }

    def stop_session(self) -> Dict[str, Any]:
        duration = time.time() - self.session_start_time if self.session_start_time else 0.0
        sid = self.session_id
        self.session_active = False
        self.session_id = None
        self.session_start_time = None
        return {
            "session_active": False,
            "session_id": sid,
            "duration_seconds": round(duration, 2),
            "mode": "STANDBY"
        }

    def get_session_status(self) -> Dict[str, Any]:
        dur = time.time() - self.session_start_time if (self.session_active and self.session_start_time) else 0.0
        return {
            "session_active": self.session_active,
            "session_id": self.session_id,
            "start_time": self.session_start_time,
            "duration_seconds": round(dur, 1),
            "mode": "ACTIVE_MONITORING" if self.session_active else "STANDBY"
        }

# Global singleton
flock_service = FlockSenseService()
