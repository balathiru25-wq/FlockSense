"""
FastAPI route endpoints for FlockSense Smart Farm Setup Flow and Dynamic Zones.
Handles:
- POST /api/setup/flock
- GET /api/setup/recommendation
- POST /api/setup/confirm
- GET /api/setup/status
- POST /api/setup/auto-assign
- POST /api/setup/start-monitoring
- GET /api/zones
- POST /api/zones/generate
- PATCH /api/zones/{zone_id}
- PATCH /api/devices/{device_id}/zones
"""

import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status

from sensors.farm_setup import farm_setup_manager
from sensors.recommendation_engine import recommendation_engine
from sensors.zone_layout_generator import zone_layout_generator
from sensors import device_registry

logger = logging.getLogger("flocksense.backend.routes.setup")

router = APIRouter(prefix="/setup", tags=["Farm Setup & Zones"])
zones_router = APIRouter(prefix="/zones", tags=["Zones"])

# Schemas
class FlockSetupRequest(BaseModel):
    flock_size: int = Field(..., gt=0, description="Number of chickens in the shed")
    shed_length_m: Optional[float] = Field(None, gt=0, description="Optional length in meters")
    shed_width_m: Optional[float] = Field(None, gt=0, description="Optional width in meters")
    farm_name: Optional[str] = "Main Poultry Farm"
    shed_name: Optional[str] = "Broiler Shed A"

class SetupConfirmRequest(BaseModel):
    cameras: int = Field(..., ge=1)
    microphones: int = Field(..., ge=1)
    zones: int = Field(..., ge=1)
    recreate_zones: bool = True

class DeviceZonePatchRequest(BaseModel):
    assigned_zone_ids: List[str] = Field(..., min_length=1)

class ZoneRenameRequest(BaseModel):
    display_name: str = Field(..., min_length=1)

class ZoneGenerateRequest(BaseModel):
    num_zones: int = Field(..., ge=1, le=24)
    aspect_ratio: Optional[float] = 1.5

@router.post("/flock", summary="Submit flock size and optional dimensions, returns sensor recommendation")
def submit_flock_info(payload: FlockSetupRequest):
    res = farm_setup_manager.set_flock(
        flock_size=payload.flock_size,
        shed_length_m=payload.shed_length_m,
        shed_width_m=payload.shed_width_m,
        farm_name=payload.farm_name,
        shed_name=payload.shed_name
    )
    return res

@router.get("/recommendation", summary="Get current sensor recommendation")
def get_recommendation(flock_size: int = 250, length_m: Optional[float] = None, width_m: Optional[float] = None):
    return recommendation_engine.recommend(
        flock_size=flock_size,
        shed_length_m=length_m,
        shed_width_m=width_m
    )

@router.post("/confirm", summary="Confirm sensor counts and auto-generate zones")
def confirm_setup(payload: SetupConfirmRequest):
    res = farm_setup_manager.confirm_setup(
        cameras=payload.cameras,
        microphones=payload.microphones,
        zones=payload.zones,
        recreate_zones=payload.recreate_zones
    )
    return res

@router.get("/status", summary="Get setup status, checklist, and readiness")
def get_setup_status():
    state = farm_setup_manager.state
    cams = device_registry.list_devices(device_type=None)
    online_cams = [d for d in cams if d.has_video and d.status.value == "ONLINE"]
    online_mics = [d for d in cams if d.has_audio and d.status.value == "ONLINE"]
    
    zones = zone_layout_generator.load_zones()
    
    # Check if devices have zone assignments
    cams_with_zones = [d for d in cams if d.has_video and getattr(d, "assigned_zone_ids", None)]
    mics_with_zones = [d for d in cams if d.has_audio and getattr(d, "assigned_zone_ids", None)]

    issues = []
    if state.get("flock_size", 0) <= 0:
        issues.append("Flock size not configured")
    if not zones:
        issues.append("No monitoring zones created")
    if len(online_cams) == 0 and len(online_mics) == 0:
        issues.append("No active cameras or microphones online")
    
    is_ready = len(issues) == 0

    return {
        "farm_setup": state,
        "is_ready": is_ready,
        "checklist": {
            "flock_size_configured": state.get("flock_size", 0) > 0,
            "zones_created": len(zones) > 0,
            "num_zones": len(zones),
            "cameras_online": len(online_cams),
            "microphones_online": len(online_mics),
            "cameras_assigned": len(cams_with_zones),
            "microphones_assigned": len(mics_with_zones),
        },
        "issues": issues,
        "ready_message": "Ready to Start Monitoring" if is_ready else f"{len(issues)} items need attention."
    }

@router.post("/auto-assign", summary="Auto-assign cameras (1-to-1) and microphones (balanced multi-zone)")
def auto_assign_devices():
    devices = device_registry.list_devices()
    cameras = [{"device_id": d.device_id, "name": d.name} for d in devices if d.has_video]
    mics = [{"device_id": d.device_id, "name": d.name} for d in devices if d.has_audio]
    zones = zone_layout_generator.load_zones()
    
    assignments = farm_setup_manager.auto_assign_devices(cameras, mics, zones)
    
    # Apply to registered devices
    for d in devices:
        if d.has_video and d.device_id in assignments["camera_assignments"]:
            assigned = assignments["camera_assignments"][d.device_id]
            d.assigned_zone_ids = assigned
            if assigned:
                d.zone = assigned[0]
        elif d.has_audio and d.device_id in assignments["microphone_assignments"]:
            assigned = assignments["microphone_assignments"][d.device_id]
            d.assigned_zone_ids = assigned
            if assigned:
                d.zone = assigned[0]
                
    device_registry.save()
    return {
        "success": True,
        "assignments": assignments,
        "message": "Auto-assigned devices to zones successfully."
    }

@router.post("/start-monitoring", summary="Mark setup completed and start live monitoring")
def start_monitoring():
    res = farm_setup_manager.complete_setup()
    return {
        "success": True,
        "message": "FlockSense monitoring is now active.",
        "state": res
    }

# Zones router
@zones_router.get("", summary="Get all current zones")
def get_zones():
    zones = zone_layout_generator.load_zones()
    return {"zones": zones, "count": len(zones)}

@zones_router.post("/generate", summary="Generate normalized grid zones")
def generate_zones(payload: ZoneGenerateRequest):
    zones = zone_layout_generator.generate_zones(
        num_zones=payload.num_zones,
        aspect_ratio=payload.aspect_ratio or 1.5
    )
    zone_layout_generator.save_zones(zones)
    return {"zones": zones, "count": len(zones)}

@zones_router.patch("/{zone_id}", summary="Rename a zone")
def rename_zone(zone_id: str, payload: ZoneRenameRequest):
    zones = zone_layout_generator.load_zones()
    found = False
    for z in zones:
        if z["zone_id"] == zone_id:
            z["name"] = payload.display_name
            z["display_name"] = payload.display_name
            found = True
            break
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Zone {zone_id} not found.")
    zone_layout_generator.save_zones(zones)
    return {"success": True, "zone_id": zone_id, "display_name": payload.display_name}

# Patch device zones
@router.patch("/devices/{device_id}/zones", summary="Update assigned zones for a device")
def update_device_zones(device_id: str, payload: DeviceZonePatchRequest):
    dev = device_registry.get_device(device_id)
    if not dev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device {device_id} not found.")
    dev.assigned_zone_ids = payload.assigned_zone_ids
    if payload.assigned_zone_ids:
        dev.zone = payload.assigned_zone_ids[0]
    device_registry.save()
    return device_registry.to_safe_response(dev)
