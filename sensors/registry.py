"""
Persistent Device Registry and Secure Local Credentials Vault for FlockSense.
Loads and saves registered devices in config/sensors.yaml.
Stores passwords in a local, protected dictionary/vault without returning them to APIs or logging them.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse

from sensors.models import SensorDevice, DeviceResponse, DeviceType, ConnectionType, DeviceStatus

logger = logging.getLogger("flocksense.sensors.registry")

class DeviceRegistry:
    """
    Manages registered hardware sensors and associated credentials.
    """
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else Path("config/sensors.yaml")
        self._devices: Dict[str, SensorDevice] = {}
        # Secure credentials store (keyed by device_id -> (username, password))
        # Never logged, never returned in API responses
        self._credentials_vault: Dict[str, Tuple[Optional[str], Optional[str]]] = {}
        self.load()

    def load(self):
        """Loads devices from config/sensors.yaml."""
        if not self.config_path.exists():
            logger.info("Registry file %s does not exist yet. Creating empty registry.", self.config_path)
            self._devices = {}
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            raw_devices = data.get("devices", [])
            for item in raw_devices:
                device = SensorDevice(**item)
                self._devices[device.device_id] = device

            logger.info("Loaded %d devices from %s", len(self._devices), self.config_path)
        except Exception as e:
            logger.error("Failed to load registry from %s: %s", self.config_path, e)

    def save(self):
        """Saves devices back to config/sensors.yaml with sanitized URLs and without passwords."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            export_list = []
            for dev in self._devices.values():
                d = dev.model_dump(mode="json")
                # Ensure credentials are stripped from URL if any were injected
                d["stream_url"] = self.sanitize_url(d["stream_url"])
                export_list.append(d)

            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump({"devices": export_list}, f, sort_keys=False)
            logger.info("Saved %d devices to %s", len(self._devices), self.config_path)
        except Exception as e:
            logger.error("Failed to save registry to %s: %s", self.config_path, e)

    def sanitize_url(self, url_str: str) -> str:
        """Removes embedded username:password from URLs for safe export and logging."""
        if not url_str or "://" not in url_str:
            return url_str
        try:
            parsed = urlparse(url_str)
            if parsed.username or parsed.password:
                hostname = parsed.hostname or ""
                port = f":{parsed.port}" if parsed.port else ""
                netloc = f"{hostname}{port}"
                return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
            return url_str
        except Exception:
            return url_str

    def register_credentials(self, device_id: str, username: Optional[str], password: Optional[str]):
        """Stores credentials in memory vault securely."""
        if username or password:
            self._credentials_vault[device_id] = (username, password)

    def get_credentials(self, device_id: str) -> Tuple[Optional[str], Optional[str]]:
        """Retrieves credentials for stream connection without exposing them to APIs."""
        return self._credentials_vault.get(device_id, (None, None))

    def get_authenticated_url(self, device_id: str) -> str:
        """Constructs authenticated URL for internal OpenCV/FFmpeg consumption."""
        device = self.get_device(device_id)
        if not device:
            return ""
        
        raw_url = device.stream_url
        user, pwd = self.get_credentials(device_id)
        if not user or not pwd:
            return raw_url

        try:
            parsed = urlparse(raw_url)
            if parsed.scheme in ("rtsp", "http", "https"):
                netloc = f"{user}:{pwd}@{parsed.hostname}"
                if parsed.port:
                    netloc += f":{parsed.port}"
                return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
        except Exception:
            pass
        return raw_url

    def add_device(self, device: SensorDevice, username: Optional[str] = None, password: Optional[str] = None) -> SensorDevice:
        self._devices[device.device_id] = device
        if username or password:
            self.register_credentials(device.device_id, username, password)
        self.save()
        return device

    def remove_device(self, device_id: str) -> bool:
        if device_id in self._devices:
            del self._devices[device_id]
            self._credentials_vault.pop(device_id, None)
            self.save()
            return True
        return False

    def get_device(self, device_id: str) -> Optional[SensorDevice]:
        return self._devices.get(device_id)

    def list_devices(self, device_type: Optional[DeviceType] = None) -> List[SensorDevice]:
        if device_type:
            return [d for d in self._devices.values() if d.device_type == device_type or (device_type == DeviceType.CAMERA and d.device_type == DeviceType.CAMERA_WITH_AUDIO)]
        return list(self._devices.values())

    def update_status(self, device_id: str, status: DeviceStatus, fps: float = 0.0, error: Optional[str] = None):
        device = self.get_device(device_id)
        if device:
            device.status = status
            device.fps = fps
            if error is not None:
                device.error_message = error

    def to_safe_response(self, device: SensorDevice) -> DeviceResponse:
        zone_ids = getattr(device, "assigned_zone_ids", None)
        if not zone_ids:
            zone_ids = [device.zone] if device.zone else ["ZONE_1"]
        return DeviceResponse(
            device_id=device.device_id,
            name=device.name,
            device_type=device.device_type.value,
            connection_type=device.connection_type.value,
            host=device.host,
            sanitized_url=self.sanitize_url(device.stream_url),
            farm=device.farm,
            shed=device.shed,
            zone=device.zone,
            assigned_zone_ids=zone_ids,
            enabled=device.enabled,
            status=device.status.value,
            has_video=device.has_video,
            has_audio=device.has_audio,
            is_demo=device.is_demo,
            last_seen=device.last_seen,
            fps=device.fps,
            latency_ms=device.latency_ms,
            error_message=device.error_message,
        )
