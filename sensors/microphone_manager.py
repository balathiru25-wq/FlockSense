"""
Microphone Manager for FlockSense Sensor Gateway.
Factory that instantiates appropriate audio adapters (Network Audio, Local Mic, Embedded Cam Audio).
"""

import logging
from typing import Optional, Dict
from sensors.models import SensorDevice, ConnectionType
from sensors.adapters import BaseMicrophoneAdapter
from sensors.adapters.network_audio import NetworkAudioAdapter
from sensors.adapters.local_microphone import LocalMicrophoneAdapter

logger = logging.getLogger("flocksense.sensors.microphone_manager")

class MicrophoneManager:
    def __init__(self):
        self._active_adapters: Dict[str, BaseMicrophoneAdapter] = {}

    def get_adapter(self, device: SensorDevice, authenticated_url: Optional[str] = None) -> BaseMicrophoneAdapter:
        if device.device_id in self._active_adapters:
            return self._active_adapters[device.device_id]

        stream_url = authenticated_url if authenticated_url else device.stream_url

        if device.connection_type == ConnectionType.LOCAL_MICROPHONE:
            adapter = LocalMicrophoneAdapter(device.device_id, stream_url)
        else:
            adapter = NetworkAudioAdapter(device.device_id, stream_url)

        self._active_adapters[device.device_id] = adapter
        return adapter

    def release_adapter(self, device_id: str):
        if device_id in self._active_adapters:
            try:
                self._active_adapters[device_id].disconnect()
            except Exception as e:
                logger.error("Error disconnecting microphone adapter %s: %s", device_id, e)
            del self._active_adapters[device_id]
