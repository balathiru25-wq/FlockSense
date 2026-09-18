"""
FastAPI route dependencies for FlockSense API.
Provides dependency-injected access to the pre-loaded FlockSenseService and FusionStateManager.
"""

from fastapi import HTTPException, status
from backend.flock_service import flock_service, FlockSenseService
from fusion.state_manager import FusionStateManager

def get_flock_service() -> FlockSenseService:
    if not flock_service.is_initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "SERVICE_NOT_INITIALIZED", "message": "FlockSense backend service is not yet initialized."}
        )
    return flock_service

def get_fusion_state_manager() -> FusionStateManager:
    service = get_flock_service()
    if service.state_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "FUSION_ENGINE_UNAVAILABLE", "message": "FlockSense Fusion Engine is unavailable."}
        )
    return service.state_manager
