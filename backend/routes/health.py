"""
System health and metadata routes.
"""

import os
from fastapi import APIRouter, Depends
from backend.dependencies import get_flock_service, FlockSenseService
from backend.schemas import HealthResponse, ComponentStatus, ValidationStatus, SystemInfoResponse
from backend.config import settings

router = APIRouter(tags=["System & Health"])

@router.get("/health", response_model=HealthResponse, summary="Service Health Check")
def get_health(service: FlockSenseService = Depends(get_flock_service)):
    """
    Returns operational health status of backend subsystems and operational disclaimers.
    """
    has_audio = service.audio_inference_pipeline is not None
    has_camera = service.camera_anomaly_detector is not None
    has_fusion = service.state_manager is not None
    has_roboflow = bool(os.getenv("ROBOFLOW_API_KEY"))

    return HealthResponse(
        status="ok",
        service=settings.app_title,
        components=ComponentStatus(
            audio_model=has_audio,
            camera_anomaly_model=has_camera,
            fusion_engine=has_fusion,
            roboflow_configured=has_roboflow
        ),
        validation=ValidationStatus(
            camera_real_world_validated=False,
            audio_localization_available=False,
            medical_validation=False,
            fusion_weights_status="PROVISIONAL_DEVELOPMENT_WEIGHTS"
        )
    )

@router.get("/system-info", response_model=SystemInfoResponse, summary="System Architecture & Metadata")
def get_system_info(service: FlockSenseService = Depends(get_flock_service)):
    """
    Returns AI models architecture, tracking algorithm, validation state, and prototype limits.
    """
    return SystemInfoResponse(
        audio_model="ResNet18 Log-Mel Spectrogram (16kHz, 128 Mels)",
        behavior_model="Roboflow chicken-behavior-detection-within-real-time/17",
        tracker="Supervision ByteTrack (Generic CHICKEN tracking)",
        camera_anomaly_model="IsolationForest + StandardScaler (18 features)",
        fusion_mode="GLOBAL_AUDIO",
        version=settings.app_version,
        validation={
            "camera": "PROTOTYPE_ONLY_SYNTHETIC_DATA",
            "audio_localization": False,
            "medical_validation": False,
            "fusion_weights": "PROVISIONAL_DEVELOPMENT_WEIGHTS"
        },
        disclaimer="FlockSense is an early-warning screening system and does not diagnose poultry disease."
    )
