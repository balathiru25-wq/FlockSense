"""
Flock status and inspection candidate routes.
"""

import time
from typing import Optional
from fastapi import APIRouter, Depends, Query
from backend.dependencies import get_fusion_state_manager
from backend.schemas import (
    FlockStatusResponse,
    GlobalAudioContext,
    TrackingSummary,
    CandidateResponse,
    CandidateItem,
    AudioContextSummary
)
from fusion.state_manager import FusionStateManager

router = APIRouter(tags=["Flock Status & Candidates"])

@router.get("/flock-status", response_model=FlockStatusResponse, summary="Flock-Level Early Warning Status")
def get_flock_status(state_mgr: FusionStateManager = Depends(get_fusion_state_manager)):
    """
    Returns current flock-wide early warning status, global acoustic context,
    active tracking numbers, and top candidate IDs.
    """
    current_time = time.time()
    flock_dict = state_mgr.get_flock_status(current_time=current_time)

    # Get audio manager context details
    audio_state = state_mgr.engine.audio_manager.get_current_global_audio_state(current_time)

    # Count high/watch deviation tracks
    all_tracks = list(state_mgr.engine.active_tracks.values())
    active_count = len([t for t in all_tracks if t.tracking_status != "TRACK_ENDED"])
    high_count = sum(1 for t in all_tracks if t.camera_anomaly_score >= 70.0 and t.tracking_status != "TRACK_ENDED")
    watch_count = sum(1 for t in all_tracks if 45.0 <= t.camera_anomaly_score < 70.0 and t.tracking_status != "TRACK_ENDED")

    global_audio = GlobalAudioContext(
        score=audio_state.get("global_audio_score", 0.0),
        status=audio_state.get("global_audio_status", "NORMAL"),
        active=audio_state.get("active_events_count", 0) > 0,
        localized=audio_state.get("audio_localized", False),
        scope=audio_state.get("audio_scope", "FLOCK"),
        last_event_time=current_time if audio_state.get("active_events_count", 0) > 0 else None,
        interpretation=audio_state.get("interpretation", "")
    )

    tracking = TrackingSummary(
        active_tracks=active_count,
        high_deviation_tracks=high_count,
        watch_deviation_tracks=watch_count
    )

    return FlockStatusResponse(
        flock_status=flock_dict.get("flock_status", "NORMAL"),
        global_audio=global_audio,
        tracking=tracking,
        top_candidate_ids=flock_dict.get("top_candidate_ids", []),
        fusion_mode=state_mgr.engine.config.get("fusion_mode", "GLOBAL_AUDIO"),
        timestamp=current_time,
        recommendation=flock_dict.get("recommendation", "Routine automated monitoring."),
        disclaimer="FlockSense is an early-warning screening system and does not diagnose poultry disease."
    )

@router.get("/candidates", response_model=CandidateResponse, summary="Ranked Inspection Candidates")
def get_candidates(
    limit: Optional[int] = Query(default=5, ge=1, le=50, description="Max candidates to return"),
    state_mgr: FusionStateManager = Depends(get_fusion_state_manager)
):
    """
    Returns ranked inspection candidates for farmer visual check.
    Inspection Priority indicates who to check first, NOT a disease probability.
    """
    current_time = time.time()
    raw_candidates = state_mgr.engine.get_top_candidates(current_time=current_time)

    # Audio state
    audio_state = state_mgr.engine.audio_manager.get_current_global_audio_state(current_time)
    audio_active = audio_state.get("global_audio_score", 0.0) >= 35.0

    items = []
    for c in raw_candidates[:limit]:
        # Fetch current behavior from active track
        tstate = state_mgr.engine.active_tracks.get(c.track_id)
        beh = tstate.current_behavior if tstate else "unknown"

        item = CandidateItem(
            rank=c.rank,
            track_id=c.track_id,
            current_zone=c.current_zone,
            initial_evidence_zone=c.initial_evidence_zone,
            behavior=beh,
            camera_deviation_score=c.camera_deviation_score,
            persistence_score=c.persistence_score,
            inspection_priority=c.inspection_priority,
            status=c.status,
            tracking_status=c.tracking_status,
            reasons=c.reasons,
            audio_context=AudioContextSummary(
                global_audio_active=audio_active,
                audio_localized=c.audio_localized,
                urgency_boost=c.audio_urgency_boost
            ),
            last_seen_timestamp=c.last_seen_timestamp
        )
        items.append(item)

    return CandidateResponse(
        total_candidates=len(items),
        candidates=items,
        disclaimer="Inspection Priority indicates which tracked birds the farmer should inspect first. It is not a disease probability."
    )
