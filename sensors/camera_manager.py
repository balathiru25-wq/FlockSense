"""
Camera Manager for FlockSense Sensor Gateway.
Factory that instantiates appropriate adapters (RTSP, HTTP, Webcam, Demo)
and manages live video ingestion.
"""

import logging
from typing import Optional, Dict
from sensors.models import SensorDevice, ConnectionType
from sensors.adapters import BaseCameraAdapter
from sensors.adapters.rtsp_camera import RtspCameraAdapter
from sensors.adapters.http_camera import HttpMjpegCameraAdapter
from sensors.adapters.local_camera import LocalCameraAdapter
from sensors.adapters.demo_camera import DemoCameraAdapter

logger = logging.getLogger("flocksense.sensors.camera_manager")

class CameraManager:
    def __init__(self):
        self._active_adapters: Dict[str, BaseCameraAdapter] = {}

    def get_adapter(self, device: SensorDevice, authenticated_url: Optional[str] = None) -> BaseCameraAdapter:
        if device.device_id in self._active_adapters:
            return self._active_adapters[device.device_id]

        stream_url = authenticated_url if authenticated_url else device.stream_url

        if device.connection_type == ConnectionType.DEMO_FEED or device.is_demo:
            adapter = DemoCameraAdapter(device.device_id, stream_url)
        elif device.connection_type in (ConnectionType.RTSP, ConnectionType.ONVIF):
            adapter = RtspCameraAdapter(device.device_id, stream_url)
        elif device.connection_type == ConnectionType.HTTP_MJPEG:
            adapter = HttpMjpegCameraAdapter(device.device_id, stream_url)
        elif device.connection_type == ConnectionType.LOCAL_WEBCAM:
            adapter = LocalCameraAdapter(device.device_id, stream_url)
        else:
            adapter = DemoCameraAdapter(device.device_id, stream_url)

        self._active_adapters[device.device_id] = adapter
        return adapter

    def release_adapter(self, device_id: str):
        if device_id in self._active_adapters:
            try:
                self._active_adapters[device_id].disconnect()
            except Exception as e:
                logger.error("Error disconnecting camera adapter %s: %s", device_id, e)
            del self._active_adapters[device_id]
