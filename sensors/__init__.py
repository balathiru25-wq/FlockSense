"""
FlockSense Sensor Gateway.
Main entry point for physical farm sensor management, network device discovery,
and stream coordination.
"""

from sensors.models import SensorDevice, DeviceResponse, AddCameraRequest, AddMicrophoneRequest
from sensors.registry import DeviceRegistry
from sensors.stream_manager import StreamManager
from sensors.health_monitor import SensorHealthMonitor
from sensors.discovery import OnvifDiscovery

# Global Gateway Singleton
device_registry = DeviceRegistry()
stream_manager = StreamManager(device_registry)
health_monitor = SensorHealthMonitor(device_registry)
onvif_discovery = OnvifDiscovery()
