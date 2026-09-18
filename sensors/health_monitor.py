"""
Sensor Gateway Health Monitor and Diagnostic Watchdog.
Periodically audits camera frame rates, audio heartbeat timestamps, and network status.
"""

import time
import logging
from typing import Dict, Any, List
from sensors.registry import DeviceRegistry
from sensors.models import SensorGatewayStatus, DeviceStatus, DeviceType

logger = logging.getLogger("flocksense.sensors.health")

class SensorHealthMonitor:
    def __init__(self, registry: DeviceRegistry):
        self.registry = registry

    def audit_devices(self):
        """Audits devices and flags stale streams as DEGRADED or OFFLINE."""
        now = time.time()
        for dev in self.registry.list_devices():
            if dev.enabled and dev.status == DeviceStatus.ONLINE:
                # If no frame or audio packet arrived in the last 10 seconds
                if dev.last_seen and (now - dev.last_seen > 10.0):
                    dev.status = DeviceStatus.DEGRADED
                    dev.error_message = "Stream data stalled > 10s"

    def get_gateway_status(self) -> SensorGatewayStatus:
        self.audit_devices()
        devices = self.registry.list_devices()
        total_devices = len(devices)
        online_devices = sum(1 for d in devices if d.status == DeviceStatus.ONLINE)

        cameras = [d for d in devices if d.device_type in (DeviceType.CAMERA, DeviceType.CAMERA_WITH_AUDIO)]
        mics = [d for d in devices if d.device_type in (DeviceType.MICROPHONE, DeviceType.CAMERA_WITH_AUDIO)]

        cams_online = sum(1 for c in cameras if c.status == DeviceStatus.ONLINE)
        mics_online = sum(1 for m in mics if m.status == DeviceStatus.ONLINE)

        status_str = "HEALTHY" if online_devices == total_devices and total_devices > 0 else "PARTIAL" if online_devices > 0 else "OFFLINE"

        return SensorGatewayStatus(
            total_devices=total_devices,
            online_devices=online_devices,
            cameras_online=cams_online,
            total_cameras=len(cameras),
            microphones_online=mics_online,
            total_microphones=len(mics),
            gateway_status=status_str,
            timestamp=time.time()
        )
