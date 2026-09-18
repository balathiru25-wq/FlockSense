"""
FlockSense Sensor Gateway Domain Models and Schemas.
Represents standardized models for physical and virtual farm sensors (cameras, microphones).
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import time

class DeviceType(str, Enum):
    CAMERA = "CAMERA"
    MICROPHONE = "MICROPHONE"
    CAMERA_WITH_AUDIO = "CAMERA_WITH_AUDIO"
    ENVIRONMENT_SENSOR = "ENVIRONMENT_SENSOR"

class ConnectionType(str, Enum):
    RTSP = "RTSP"
    ONVIF = "ONVIF"
    HTTP_MJPEG = "HTTP_MJPEG"
    LOCAL_WEBCAM = "LOCAL_WEBCAM"
    NETWORK_AUDIO = "NETWORK_AUDIO"
    LOCAL_MICROPHONE = "LOCAL_MICROPHONE"
    DEMO_FEED = "DEMO_FEED"

class DeviceStatus(str, Enum):
    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"
    RECONNECTING = "RECONNECTING"
    OFFLINE = "OFFLINE"

class SensorDevice(BaseModel):
    """
    Standardized internal & persistent sensor device model.
    """
    device_id: str = Field(..., description="Unique hardware/device identifier, e.g. cam-001")
    name: str = Field(..., description="Farmer-friendly device name, e.g. 'Shed 1 Feeding Area Camera'")
    device_type: DeviceType = Field(..., description="Device category")
    connection_type: ConnectionType = Field(..., description="Network or local protocol")
    host: Optional[str] = Field(None, description="IP address or hostname")
    stream_url: str = Field(..., description="RTSP, HTTP, or device index URL")
    
    # Farm & spatial placement
    farm: str = Field("Main Farm", description="Farm identifier")
    shed: str = Field("Shed 1", description="Shed identifier")
    zone: str = Field("ZONE_1", description="Assigned primary virtual shed zone")
    assigned_zone_ids: List[str] = Field(default_factory=lambda: ["ZONE_1"], description="List of configured zones covered by this device")
    
    # Capabilities & flags
    enabled: bool = Field(True, description="Whether device is enabled for active streaming")
    status: DeviceStatus = Field(DeviceStatus.OFFLINE, description="Operational connection state")
    has_video: bool = Field(True, description="Provides video feed")
    has_audio: bool = Field(False, description="Provides audio feed")
    is_demo: bool = Field(False, description="Indicates a mock or recorded test asset")
    
    # Timestamps & telemetry
    last_seen: Optional[float] = Field(None, description="Unix timestamp of latest frame/chunk")
    fps: float = Field(0.0, description="Observed video frames per second")
    latency_ms: float = Field(0.0, description="Observed stream transmission latency")
    error_message: Optional[str] = Field(None, description="Latest diagnostic error if disconnected")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary adapter metadata")

class DeviceResponse(BaseModel):
    """
    Client-safe representation of a device (strictly redacting passwords and secret URLs).
    """
    device_id: str
    name: str
    device_type: str
    connection_type: str
    host: Optional[str]
    sanitized_url: str
    farm: str
    shed: str
    zone: str
    assigned_zone_ids: List[str] = []
    enabled: bool
    status: str
    has_video: bool
    has_audio: bool
    is_demo: bool
    last_seen: Optional[float]
    fps: float
    latency_ms: float
    error_message: Optional[str]

class AddCameraRequest(BaseModel):
    device_id: Optional[str] = None
    name: str
    connection_type: ConnectionType = ConnectionType.RTSP
    host: Optional[str] = None
    stream_url: str
    username: Optional[str] = None
    password: Optional[str] = None
    farm: Optional[str] = "Main Farm"
    shed: Optional[str] = "Shed 1"
    zone: Optional[str] = "ZONE_1"
    assigned_zone_ids: Optional[List[str]] = None
    has_audio: bool = False
    is_demo: bool = False

class AddMicrophoneRequest(BaseModel):
    device_id: Optional[str] = None
    name: str
    connection_type: ConnectionType = ConnectionType.NETWORK_AUDIO
    host: Optional[str] = None
    stream_url: str
    username: Optional[str] = None
    password: Optional[str] = None
    farm: Optional[str] = "Main Farm"
    shed: Optional[str] = "Shed 1"
    zone: Optional[str] = "ZONE_1"
    assigned_zone_ids: Optional[List[str]] = None
    is_demo: bool = False

class DiscoveredDevice(BaseModel):
    device_id: str
    name: str
    model: Optional[str] = "Generic ONVIF IP Camera"
    host: str
    connection_type: ConnectionType
    requires_credentials: bool = True
    suggested_zone: str = "ZONE_1"

class DeviceTestResult(BaseModel):
    success: bool
    device_id: Optional[str] = None
    message: str
    fps: float = 0.0
    resolution: Optional[str] = None
    has_audio: bool = False

class SensorGatewayStatus(BaseModel):
    total_devices: int
    online_devices: int
    cameras_online: int
    total_cameras: int
    microphones_online: int
    total_microphones: int
    gateway_status: str
    timestamp: float
