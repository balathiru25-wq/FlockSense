"""
Bioacoustic analysis and upload route.
"""

import os
import tempfile
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from backend.dependencies import get_flock_service, FlockSenseService
from backend.schemas import (
    AudioAnalysisResponse,
    AudioInferenceResult,
    FusionContextUpdate
)
from backend.config import settings

logger = logging.getLogger("flocksense.backend.audio")
router = APIRouter(prefix="/analyze-audio", tags=["Bioacoustics"])

@router.post("", response_model=AudioAnalysisResponse, summary="Analyze Poultry Audio Recording")
async def analyze_audio(
    file: UploadFile = File(..., description="Audio file to analyze (.wav, .mp3, etc.)"),
    service: FlockSenseService = Depends(get_flock_service)
):
    """
    Analyzes an uploaded poultry audio recording via the trained ResNet18 bioacoustics model.
    Updates the global flock acoustic context and triggers early-warning prioritization.
    
    IMPORTANT: Acoustic abnormalities represent flock-level context and are NOT attributed
    to a specific individual chicken.
    """
    # 1. Validate file extension
    filename = file.filename or "unknown.wav"
    suffix = Path(filename).suffix.lower()
    if suffix not in settings.allowed_audio_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_AUDIO_FORMAT",
                "message": f"Unsupported file extension '{suffix}'. Allowed: {settings.allowed_audio_extensions}"
            }
        )

    # 2. Read content & validate file size
    try:
        content = await file.read()
    except Exception as e:
        logger.error("Failed reading upload file: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "FILE_READ_ERROR", "message": "Failed to read audio file contents."}
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMPTY_AUDIO_FILE", "message": "Uploaded audio file is empty (0 bytes)."}
        )

    if len(content) > settings.max_audio_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "AUDIO_TOO_LARGE",
                "message": f"Audio file exceeds maximum size of {settings.max_audio_upload_bytes / (1024*1024):.0f} MB."
            }
        )

    # 3. Write to temporary file for soundfile decoding
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        temp_file.write(content)
        temp_file.close()

        # Run inference using service
        result = service.analyze_audio_file(temp_file.name, filename=filename)
        inf = result["inference_result"]
        fus = result["fusion_update"]

        audio_res = AudioInferenceResult(
            prediction=inf.get("predicted_acoustic_state", "NORMAL"),
            status=inf.get("status", "NORMAL"),
            overall_abnormality_probability_pct=inf.get("overall_abnormality_probability_pct", 0.0),
            score=inf.get("overall_abnormality_probability_pct", 0.0),
            scope="FLOCK",
            localized=False,
            duration_seconds=inf.get("duration_seconds", 0.0),
            windows_analyzed=inf.get("windows_analyzed", 0),
            high_risk_windows=inf.get("high_risk_windows", 0),
            interpretation=inf.get("interpretation", ""),
            recommended_action=inf.get("recommended_action", "")
        )

        fusion_update = FusionContextUpdate(
            flock_status=fus.get("flock_status", "NORMAL"),
            global_audio_score=fus.get("global_audio_score", 0.0),
            top_candidate_ids=fus.get("top_candidate_ids", [])
        )

        return AudioAnalysisResponse(
            success=True,
            filename=filename,
            audio=audio_res,
            fusion=fusion_update,
            disclaimer="Audio abnormality is flock-level and is not attributed to a specific bird."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Audio analysis error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "AUDIO_INFERENCE_ERROR", "message": f"Audio processing failed: {str(e)}"}
        )
    finally:
        if os.path.exists(temp_file.name):
            try:
                os.remove(temp_file.name)
            except Exception:
                pass
