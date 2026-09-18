"""
Track query and inspection detail routes.
"""

import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from backend.dependencies import get_fusion_state_manager
from backend.schemas import (
    TrackListResponse,
    TrackSummaryItem,
    TrackDetailResponse,
    AudioContextSummary
)
from fusion.state_manager import FusionStateManager

router = APIRouter(prefix="/tracks", tags=["Track States"])

@router.get("", response_model=TrackListResponse, summary="List Active Monitored Tracks")
def list_tracks(state_mgr: FusionStateManager = Depends(get_fusion_state_manager)):
    """
    Returns all active and temporarily lost tracked chickens with their zone,
    behavior, camera deviation score, and current inspection priority.
    """
    current_time = time.time()
    all_tracks = state_mgr.engine.active_tracks
    
    # Evaluate candidates to get priority and status
    candidates = state_mgr.engine.get_top_candidates(current_time=current_time)
    cand_by_id = {c.track_id: c for c in candidates}

    track_items = []
    for tid, t in all_tracks.items():
        if t.tracking_status == "TRACK_ENDED":
            continue

        cand = cand_by_id.get(tid)
        priority = cand.inspection_priority if cand else t.camera_anomaly_score
        c_status = cand.status if cand else ("ALERT" if t.camera_anomaly_score >= 70 else ("WATCH" if t.camera_anomaly_score >= 45 else "NORMAL"))

        track_items.append(TrackSummaryItem(
            track_id=t.track_id,
            tracking_status=t.tracking_status,
            current_zone=t.current_zone,
            previous_zone=t.previous_zone,
            initial_evidence_zone=t.initial_evidence_zone,
            current_behavior=t.current_behavior,
            stable_behavior=t.stable_behavior,
            behavior_confidence=t.behavior_confidence if hasattr(t, "behavior_confidence") else 0.9,
            movement_rate=t.movement_rate,
            stationary_duration=t.stationary_duration,
            camera_deviation_score=t.camera_anomaly_score,
            inspection_priority=round(priority, 1),
            status=c_status,
            last_seen=t.last_seen_timestamp if t.last_seen_timestamp > 0 else t.timestamp
        ))

    # Sort tracks by inspection priority descending
    track_items.sort(key=lambda x: x.inspection_priority, reverse=True)

    return TrackListResponse(
        total_tracks=len(track_items),
        tracks=track_items
    )

@router.get("/{track_id}", response_model=TrackDetailResponse, summary="Get Track Detail by ID")
def get_track_detail(
    track_id: int,
    state_mgr: FusionStateManager = Depends(get_fusion_state_manager)
):
    """
    Returns comprehensive inspection state, zone movement history, behavioral observations,
    and explainability reasons for a specific Track ID.
    Returns 404 if the Track ID is not found.
    """
    t = state_mgr.engine.active_tracks.get(track_id)
    if not t:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TRACK_NOT_FOUND", "message": f"Track #{track_id} not found in active session."}
        )

    current_time = time.time()
    candidates = state_mgr.engine.get_top_candidates(current_time=current_time)
    cand = next((c for c in candidates if c.track_id == track_id), None)
    
    mem = state_mgr.engine.memory_manager.get_or_create(track_id, initial_zone=t.current_zone)
    persistence = mem.compute_persistence_score()
    smoothed_dev = mem.smoothed_score

    audio_state = state_mgr.engine.audio_manager.get_current_global_audio_state(current_time)
    audio_active = audio_state.get("global_audio_score", 0.0) >= 35.0

    if cand:
        priority = cand.inspection_priority
        f_status = cand.status
        reasons = cand.reasons
        audio_boost = cand.audio_urgency_boost
        audio_localized = cand.audio_localized
    else:
        priority = smoothed_dev
        f_status = "NORMAL"
        reasons = t.camera_reasons or ["Behavior within normal parameters"]
        audio_boost = 0.0
        audio_localized = False

    return TrackDetailResponse(
        track_id=t.track_id,
        tracking_status=t.tracking_status,
        current_zone=t.current_zone,
        previous_zone=t.previous_zone,
        initial_evidence_zone=t.initial_evidence_zone,
        position=t.position,
        bbox=t.bbox,
        current_behavior=t.current_behavior,
        stable_behavior=t.stable_behavior,
        behavior_confidence=0.9,
        movement_rate=t.movement_rate,
        distance_travelled_pixels=t.distance_travelled_pixels,
        stationary_duration=t.stationary_duration,
        stationary_ratio=t.stationary_ratio,
        relative_isolation_score=t.relative_isolation_score,
        relative_activity=t.relative_activity,
        camera_deviation_score=round(smoothed_dev, 1),
        persistence_score=round(persistence, 1),
        inspection_priority=round(priority, 1),
        fusion_status=f_status,
        reasons=reasons,
        audio_context=AudioContextSummary(
            global_audio_active=audio_active,
            audio_localized=audio_localized,
            urgency_boost=audio_boost
        ),
        first_seen=t.timestamp,
        last_seen=t.last_seen_timestamp if t.last_seen_timestamp > 0 else t.timestamp,
        disclaimer="Audio source is not localized to this individual bird. FlockSense prioritizes visual inspections and does not diagnose disease."
    )
