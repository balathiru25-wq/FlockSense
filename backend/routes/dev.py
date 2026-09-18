"""
Development-only state ingestion and session management routes.
"""

import time
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from backend.dependencies import get_flock_service, get_fusion_state_manager, FlockSenseService
from backend.schemas import (
    DevTrackStateIngest,
    CandidateItem,
    AudioContextSummary,
    SessionStatusResponse
)
from backend.config import settings
from fusion.state_manager import FusionStateManager
from fusion.models import CameraTrackState

router = APIRouter(tags=["Development & Sessions"])

@router.post("/dev/track-state", response_model=CandidateItem, summary="[DEV ONLY] Ingest TrackState from Vision Tracker")
def dev_ingest_track_state(
    payload: DevTrackStateIngest,
    state_mgr: FusionStateManager = Depends(get_fusion_state_manager)
):
    """
    Development endpoint enabling vision scripts or test runners to push
    TrackState updates to the active FusionStateManager.
    Only active when development_mode = true.
    """
    if not settings.development_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "DEV_MODE_DISABLED", "message": "Development endpoint disabled in production mode."}
        )

    cur_time = payload.timestamp if payload.timestamp is not None else time.time()
    tstate = CameraTrackState(
        track_id=payload.track_id,
        timestamp=cur_time,
        current_zone=payload.current_zone,
        previous_zone=payload.previous_zone or payload.current_zone,
        initial_evidence_zone="UNKNOWN",
        current_behavior=payload.current_behavior,
        stable_behavior=payload.stable_behavior or payload.current_behavior,
        bbox=payload.bbox or [100.0, 100.0, 180.0, 180.0],
        position=tuple(payload.position) if payload.position else (140.0, 140.0),
        camera_anomaly_score=payload.camera_anomaly_score,
        camera_status=payload.camera_anomaly_status or "NORMAL_PATTERN",
        movement_rate=payload.movement_rate,
        distance_travelled_pixels=payload.distance_travelled_pixels,
        stationary_duration=payload.stationary_duration,
        stationary_ratio=payload.stationary_ratio,
        relative_isolation_score=payload.relative_isolation_score,
        relative_activity=payload.relative_activity,
        camera_reasons=payload.camera_anomaly_reasons or [],
        last_seen_timestamp=cur_time
    )

    cand = state_mgr.engine.update_camera_track(tstate)

    audio_state = state_mgr.engine.audio_manager.get_current_global_audio_state(cur_time)
    audio_active = audio_state.get("global_audio_score", 0.0) >= 35.0

    return CandidateItem(
        rank=cand.rank if cand.rank > 0 else 1,
        track_id=cand.track_id,
        current_zone=cand.current_zone,
        initial_evidence_zone=cand.initial_evidence_zone,
        behavior=payload.current_behavior,
        camera_deviation_score=cand.camera_deviation_score,
        persistence_score=cand.persistence_score,
        inspection_priority=cand.inspection_priority,
        status=cand.status,
        tracking_status=cand.tracking_status,
        reasons=cand.reasons,
        audio_context=AudioContextSummary(
            global_audio_active=audio_active,
            audio_localized=cand.audio_localized,
            urgency_boost=cand.audio_urgency_boost
        ),
        last_seen_timestamp=cand.last_seen_timestamp
    )

@router.post("/session/start", response_model=SessionStatusResponse, summary="Start Monitoring Session")
def start_session(service: FlockSenseService = Depends(get_flock_service)):
    res = service.start_session()
    return SessionStatusResponse(
        session_active=res["session_active"],
        session_id=res["session_id"],
        start_time=res["start_time"],
        duration_seconds=0.0,
        mode=res["mode"]
    )

@router.post("/session/stop", response_model=SessionStatusResponse, summary="Stop Monitoring Session")
def stop_session(service: FlockSenseService = Depends(get_flock_service)):
    res = service.stop_session()
    return SessionStatusResponse(
        session_active=res["session_active"],
        session_id=res["session_id"],
        start_time=None,
        duration_seconds=res["duration_seconds"],
        mode=res["mode"]
    )

@router.get("/session/status", response_model=SessionStatusResponse, summary="Get Monitoring Session Status")
def get_session_status(service: FlockSenseService = Depends(get_flock_service)):
    res = service.get_session_status()
    return SessionStatusResponse(
        session_active=res["session_active"],
        session_id=res["session_id"],
        start_time=res["start_time"],
        duration_seconds=res["duration_seconds"],
        mode=res["mode"]
    )

# -----------------------------------------------------------------------------
# Dedicated Judge Demo Controller Endpoints (/api/dev/demo)
# -----------------------------------------------------------------------------
@router.post("/dev/demo/reset", summary="[DEMO] Reset Demonstration State to Baseline")
def demo_reset(
    service: FlockSenseService = Depends(get_flock_service),
    state_mgr: FusionStateManager = Depends(get_fusion_state_manager)
):
    """Resets all tracks, alerts, and active audio contexts to clean initial baseline."""
    if not settings.development_mode:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dev mode disabled.")

    state_mgr.engine.active_tracks.clear()
    state_mgr.engine.memory_manager.track_memories.clear()
    state_mgr.engine.audio_manager.recent_events.clear()
    state_mgr.engine.alert_engine.alerts_history.clear()

    return {
        "success": True,
        "demo_step": "RESET",
        "message": "Demo state reset to clean baseline.",
        "active_tracks": 0,
        "flock_status": "NORMAL"
    }

@router.post("/dev/demo/normal", summary="[DEMO STEP 1] Initialize Peacetime Normal Flock State")
def demo_normal_flock(
    state_mgr: FusionStateManager = Depends(get_fusion_state_manager)
):
    """Sets up standard normal flock monitoring with Tracks #12, #17, and #24 in baseline state."""
    if not settings.development_mode:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dev mode disabled.")

    now = time.time()
    tracks_data = [
        CameraTrackState(
            track_id=12,
            timestamp=now,
            current_zone="ZONE_1",
            current_behavior="feeding",
            camera_anomaly_score=18.0,
            camera_status="NORMAL_PATTERN",
            movement_rate=14.0,
            stationary_duration=1.0,
            relative_isolation_score=0.22,
            relative_activity=1.1,
            camera_reasons=["behaviour patterns within normal baseline parameters"]
        ),
        CameraTrackState(
            track_id=17,
            timestamp=now,
            current_zone="ZONE_3",
            current_behavior="standing",
            camera_anomaly_score=24.0,
            camera_status="NORMAL_PATTERN",
            movement_rate=12.0,
            stationary_duration=1.5,
            relative_isolation_score=0.24,
            relative_activity=1.0,
            camera_reasons=["behaviour patterns within normal baseline parameters"]
        ),
        CameraTrackState(
            track_id=24,
            timestamp=now,
            current_zone="ZONE_4",
            current_behavior="walking",
            camera_anomaly_score=21.0,
            camera_status="NORMAL_PATTERN",
            movement_rate=16.0,
            stationary_duration=0.5,
            relative_isolation_score=0.23,
            relative_activity=1.2,
            camera_reasons=["behaviour patterns within normal baseline parameters"]
        )
    ]

    for t in tracks_data:
        state_mgr.engine.update_camera_track(t)

    flock_stat = state_mgr.get_flock_status(current_time=now)
    return {
        "success": True,
        "demo_step": "STEP_1_NORMAL",
        "flock_status": flock_stat.get("flock_status", "NORMAL"),
        "active_tracks": len(tracks_data),
        "candidates": state_mgr.get_top_candidates(current_time=now)
    }

@router.post("/dev/demo/behavior-deviation", summary="[DEMO STEP 2] Elevate Track #17 Behavioral Deviation")
def demo_behavior_deviation(
    state_mgr: FusionStateManager = Depends(get_fusion_state_manager)
):
    """Simulates gradual behavioral deviation on Track #17 (lethargy, high stationary, isolation)."""
    if not settings.development_mode:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dev mode disabled.")

    now = time.time()
    # Step 17 through sequential elevation windows to establish persistence
    scores = [42.0, 62.0, 82.0]
    cand = None
    for i, s in enumerate(scores):
        t17 = CameraTrackState(
            track_id=17,
            timestamp=now + (i * 2.0),
            current_zone="ZONE_3",
            previous_zone="ZONE_3",
            current_behavior="sitting",
            camera_anomaly_score=s,
            camera_status="HIGH_DEVIATION" if s >= 70 else "WATCH_DEVIATION",
            movement_rate=0.0,
            stationary_duration=4.8,
            stationary_ratio=1.0,
            relative_isolation_score=0.33,
            relative_activity=0.0,
            camera_reasons=[
                "movement rate substantially below flock median baseline",
                "prolonged stationary duration exceeding peer baseline",
                "predominant sitting posture relative to moving flock peers"
            ]
        )
        cand = state_mgr.engine.update_camera_track(t17)

    return {
        "success": True,
        "demo_step": "STEP_2_BEHAVIOR_DEVIATION",
        "track_id": 17,
        "camera_deviation_score": cand.camera_deviation_score,
        "persistence_score": cand.persistence_score,
        "inspection_priority": cand.inspection_priority,
        "status": cand.status,
        "reasons": cand.reasons
    }

@router.post("/dev/demo/zone-transition", summary="[DEMO STEP 3] Migrate Track #17 from ZONE_3 to ZONE_2")
def demo_zone_transition(
    state_mgr: FusionStateManager = Depends(get_fusion_state_manager)
):
    """Simulates Track #17 transitioning from ZONE_3 to ZONE_2, demonstrating risk following the bird."""
    if not settings.development_mode:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dev mode disabled.")

    now = time.time()
    t17_moved = CameraTrackState(
        track_id=17,
        timestamp=now,
        current_zone="ZONE_2",
        previous_zone="ZONE_3",
        current_behavior="sitting",
        camera_anomaly_score=85.0,
        camera_status="HIGH_DEVIATION",
        movement_rate=1.0,
        stationary_duration=4.5,
        stationary_ratio=0.95,
        relative_isolation_score=0.34,
        relative_activity=0.1,
        camera_reasons=[
            "movement rate substantially below flock median baseline",
            "prolonged stationary duration exceeding peer baseline"
        ]
    )
    cand = state_mgr.engine.update_camera_track(t17_moved)

    return {
        "success": True,
        "demo_step": "STEP_3_ZONE_TRANSITION",
        "track_id": 17,
        "current_zone": cand.current_zone,
        "initial_evidence_zone": cand.initial_evidence_zone,
        "inspection_priority": cand.inspection_priority,
        "status": cand.status,
        "reasons": cand.reasons
    }

@router.post("/dev/demo/analyze-test-audio", summary="[DEMO STEP 4/5] Run Real Audio Inference on Staged Test Sample")
def demo_analyze_test_audio(
    mode: str = "abnormal", # "normal" or "abnormal"
    service: FlockSenseService = Depends(get_flock_service)
):
    """Executes genuine ResNet18 audio inference on staged test samples (normal_sample.wav or abnormal_sample.wav)."""
    if not settings.development_mode:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dev mode disabled.")

    audio_file = Path("dataset/audio/abnormal_sample.wav") if mode == "abnormal" else Path("dataset/audio/normal_sample.wav")
    if not audio_file.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Test sample not found: {audio_file}")

    result = service.analyze_audio_file(str(audio_file), filename=audio_file.name)
    inf = result["inference_result"]
    fus = result["fusion_update"]

    return {
        "success": True,
        "demo_step": f"STEP_AUDIO_{mode.upper()}",
        "filename": audio_file.name,
        "predicted_state": inf.get("predicted_acoustic_state"),
        "status": inf.get("status"),
        "overall_abnormality_pct": inf.get("overall_abnormality_probability_pct"),
        "flock_status": fus.get("flock_status"),
        "scope": "FLOCK",
        "audio_localized": False,
        "disclaimer": "Audio anomaly is flock-level and is not attributed to a specific bird."
    }

@router.get("/dev/demo/status", summary="[DEMO] Get Current Demonstration State")
def demo_status(
    state_mgr: FusionStateManager = Depends(get_fusion_state_manager)
):
    now = time.time()
    flock_stat = state_mgr.get_flock_status(current_time=now)
    candidates = state_mgr.get_top_candidates(current_time=now)
    audio_state = state_mgr.engine.audio_manager.get_current_global_audio_state(now)
    return {
        "development_mode": settings.development_mode,
        "flock_status": flock_stat.get("flock_status"),
        "global_audio_score": audio_state.get("global_audio_score"),
        "global_audio_status": audio_state.get("global_audio_status"),
        "active_tracks_count": len(state_mgr.engine.active_tracks),
        "candidates": candidates
    }
