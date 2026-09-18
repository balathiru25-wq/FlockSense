"""
FastAPI route endpoints for FlockSense Sensor Gateway.
Exposes device management, network discovery, stream previews, and connection controls.
Never exposes device credentials or secrets to API responses.
"""

import uuid
import time
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query, Response
from fastapi.responses import StreamingResponse

from sensors import device_registry, stream_manager, health_monitor, onvif_discovery
from sensors.models import (
    SensorDevice,
    DeviceResponse,
    AddCameraRequest,
    AddMicrophoneRequest,
    DiscoveredDevice,
    DeviceTestResult,
    SensorGatewayStatus,
    DeviceType,
    DeviceStatus
)

router = APIRouter(prefix="/devices", tags=["Sensor Gateway & Devices"])

@router.get("", response_model=List[DeviceResponse], summary="List all registered sensors")
def list_devices(device_type: Optional[DeviceType] = None):
    devices = device_registry.list_devices(device_type=device_type)
    return [device_registry.to_safe_response(d) for d in devices]

@router.get("/cameras", response_model=List[DeviceResponse], summary="List registered cameras")
def list_cameras():
    cameras = device_registry.list_devices(device_type=DeviceType.CAMERA)
    return [device_registry.to_safe_response(c) for c in cameras]

@router.get("/microphones", response_model=List[DeviceResponse], summary="List registered microphones")
def list_microphones():
    mics = device_registry.list_devices(device_type=DeviceType.MICROPHONE)
    return [device_registry.to_safe_response(m) for m in mics]

@router.get("/status", response_model=SensorGatewayStatus, summary="Get Sensor Gateway health summary")
def get_gateway_status():
    return health_monitor.get_gateway_status()

@router.get("/{device_id}", response_model=DeviceResponse, summary="Get device details")
def get_device(device_id: str):
    device = device_registry.get_device(device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device {device_id} not found.")
    return device_registry.to_safe_response(device)

@router.post("/discover", response_model=List[DiscoveredDevice], summary="Discover ONVIF cameras on farm LAN")
def discover_devices():
    return onvif_discovery.discover_devices()

@router.post("/camera", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED, summary="Register a camera manually")
def add_camera(payload: AddCameraRequest):
    dev_id = payload.device_id or f"cam-{uuid.uuid4().hex[:6]}"
    
    # Check duplicate
    if device_registry.get_device(dev_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Device {dev_id} already registered.")

    device_type = DeviceType.CAMERA_WITH_AUDIO if payload.has_audio else DeviceType.CAMERA
    new_device = SensorDevice(
        device_id=dev_id,
        name=payload.name,
        device_type=device_type,
        connection_type=payload.connection_type,
        host=payload.host,
        stream_url=payload.stream_url,
        farm=payload.farm or "Main Farm",
        shed=payload.shed or "Shed 1",
        zone=payload.zone or "ZONE_1",
        enabled=True,
        status=DeviceStatus.OFFLINE,
        has_video=True,
        has_audio=payload.has_audio,
        is_demo=payload.is_demo
    )

    device_registry.add_device(new_device, username=payload.username, password=payload.password)
    # Auto-start stream
    stream_manager.start_device_stream(dev_id)
    return device_registry.to_safe_response(new_device)

@router.post("/microphone", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED, summary="Register a microphone manually")
def add_microphone(payload: AddMicrophoneRequest):
    dev_id = payload.device_id or f"mic-{uuid.uuid4().hex[:6]}"
    
    if device_registry.get_device(dev_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Device {dev_id} already registered.")

    new_device = SensorDevice(
        device_id=dev_id,
        name=payload.name,
        device_type=DeviceType.MICROPHONE,
        connection_type=payload.connection_type,
        host=payload.host,
        stream_url=payload.stream_url,
        farm=payload.farm or "Main Farm",
        shed=payload.shed or "Shed 1",
        zone=payload.zone or "ZONE_1",
        enabled=True,
        status=DeviceStatus.OFFLINE,
        has_video=False,
        has_audio=True,
        is_demo=payload.is_demo
    )

    device_registry.add_device(new_device, username=payload.username, password=payload.password)
    stream_manager.start_device_stream(dev_id)
    return device_registry.to_safe_response(new_device)

@router.post("/{device_id}/connect", response_model=DeviceResponse, summary="Connect or reconnect a sensor stream")
def connect_device(device_id: str):
    device = device_registry.get_device(device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device {device_id} not found.")
    
    device.enabled = True
    device_registry.save()
    stream_manager.start_device_stream(device_id)
    time.sleep(0.3)
    return device_registry.to_safe_response(device)

@router.post("/{device_id}/disconnect", response_model=DeviceResponse, summary="Disconnect a sensor stream")
def disconnect_device(device_id: str):
    device = device_registry.get_device(device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device {device_id} not found.")

    device.enabled = False
    device_registry.save()
    stream_manager.stop_device_stream(device_id)
    return device_registry.to_safe_response(device)

@router.post("/connect-all", summary="Connect all registered farm devices")
def connect_all_devices():
    results = stream_manager.connect_all()
    return {
        "success": True,
        "message": f"Connected {sum(1 for v in results.values() if v)} of {len(results)} devices.",
        "results": results
    }

@router.post("/{device_id}/test", response_model=DeviceTestResult, summary="Probe test a device stream without persistent lock")
def test_device(device_id: str):
    device = device_registry.get_device(device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device {device_id} not found.")

    auth_url = device_registry.get_authenticated_url(device_id)
    if device.has_video:
        adapter = stream_manager.camera_manager.get_adapter(device, auth_url)
        ok, msg, dims = adapter.test_connection()
        res_str = f"{dims[0]}x{dims[1]}" if dims else None
        return DeviceTestResult(success=ok, device_id=device_id, message=msg, resolution=res_str, has_audio=device.has_audio)
    else:
        adapter = stream_manager.microphone_manager.get_adapter(device, auth_url)
        ok, msg = adapter.test_connection()
        return DeviceTestResult(success=ok, device_id=device_id, message=msg, has_audio=True)

@router.delete("/{device_id}", summary="Remove a device from registry")
def delete_device(device_id: str):
    stream_manager.stop_device_stream(device_id)
    removed = device_registry.remove_device(device_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device {device_id} not found.")
    return {"success": True, "device_id": device_id, "message": "Device removed from farm registry."}

@router.get("/{device_id}/preview.mjpg", summary="Stream browser-friendly MJPEG preview feed")
def stream_camera_preview(device_id: str):
    device = device_registry.get_device(device_id)
    if not device or not device.has_video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found or does not support video.")
    
    return StreamingResponse(
        stream_manager.generate_mjpeg_stream(device_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/{device_id}/snapshot.jpg", summary="Get a single JPEG snapshot")
def get_camera_snapshot(device_id: str):
    jpeg = stream_manager.get_latest_jpeg(device_id)
    if not jpeg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No frame available yet from camera.")
    return Response(content=jpeg, media_type="image/jpeg")
