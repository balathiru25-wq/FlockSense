"""
Stream Manager for FlockSense Sensor Gateway.
Coordinates continuous background frame capturing, JPEG preview generation for web browsers,
audio chunk extraction for acoustic inference, connection retry with exponential backoff,
and camera-scoped tracking sessions.
"""

import threading
import time
import cv2
import logging
import numpy as np
from typing import Optional, Dict, Tuple, Generator, Any

from sensors.models import SensorDevice, DeviceStatus, DeviceType
from sensors.registry import DeviceRegistry
from sensors.camera_manager import CameraManager
from sensors.microphone_manager import MicrophoneManager

logger = logging.getLogger("flocksense.sensors.stream_manager")

class StreamManager:
    def __init__(self, registry: DeviceRegistry):
        self.registry = registry
        self.camera_manager = CameraManager()
        self.microphone_manager = MicrophoneManager()
        
        # Latest frame store for HTTP/MJPEG browser streaming: device_id -> (timestamp, jpeg_bytes, raw_bgr_frame)
        self._latest_frames: Dict[str, Tuple[float, bytes, np.ndarray]] = {}
        # Latest audio chunk store: device_id -> (timestamp, numpy_array)
        self._latest_audio_chunks: Dict[str, Tuple[float, np.ndarray]] = {}
        
        # Active stream workers: device_id -> (thread, stop_event)
        self._stream_workers: Dict[str, Tuple[threading.Thread, threading.Event]] = {}
        self._lock = threading.Lock()

    def start_device_stream(self, device_id: str) -> bool:
        """Starts a persistent background worker capturing from a camera or microphone."""
        device = self.registry.get_device(device_id)
        if not device or not device.enabled:
            return False

        with self._lock:
            if device_id in self._stream_workers:
                return True # Already running

            stop_event = threading.Event()
            worker_thread = threading.Thread(
                target=self._stream_loop,
                args=(device_id, stop_event),
                name=f"Worker-{device_id}",
                daemon=True
            )
            self._stream_workers[device_id] = (worker_thread, stop_event)
            worker_thread.start()
            logger.info("Started stream worker for device: %s", device_id)
            return True

    def stop_device_stream(self, device_id: str):
        """Stops stream worker and releases hardware adapter."""
        with self._lock:
            if device_id in self._stream_workers:
                worker_thread, stop_event = self._stream_workers[device_id]
                stop_event.set()
                del self._stream_workers[device_id]

        self.camera_manager.release_adapter(device_id)
        self.microphone_manager.release_adapter(device_id)
        self.registry.update_status(device_id, DeviceStatus.OFFLINE)
        logger.info("Stopped stream worker for device: %s", device_id)

    def connect_all(self) -> Dict[str, bool]:
        """Attempts to start streams for all enabled registered devices."""
        results = {}
        for dev in self.registry.list_devices():
            if dev.enabled:
                success = self.start_device_stream(dev.device_id)
                results[dev.device_id] = success
        return results

    def _stream_loop(self, device_id: str, stop_event: threading.Event):
        """Continuous stream reading loop with graceful reconnect backoff."""
        device = self.registry.get_device(device_id)
        if not device:
            return

        is_camera = device.device_type in (DeviceType.CAMERA, DeviceType.CAMERA_WITH_AUDIO)
        is_mic = device.device_type in (DeviceType.MICROPHONE, DeviceType.CAMERA_WITH_AUDIO)

        auth_url = self.registry.get_authenticated_url(device_id)
        cam_adapter = self.camera_manager.get_adapter(device, auth_url) if is_camera else None
        mic_adapter = self.microphone_manager.get_adapter(device, auth_url) if is_mic else None

        backoff = 2.0
        frame_counter = 0
        fps_timer = time.time()
        current_fps = 0.0

        while not stop_event.is_set():
            connected = True
            if cam_adapter and not cam_adapter.is_connected:
                self.registry.update_status(device_id, DeviceStatus.RECONNECTING)
                connected = cam_adapter.connect()

            if mic_adapter and not mic_adapter.is_connected:
                mic_connected = mic_adapter.connect()
                connected = connected and mic_connected

            if not connected:
                self.registry.update_status(device_id, DeviceStatus.RECONNECTING, error="Connection retry backoff")
                time.sleep(backoff)
                backoff = min(backoff * 1.5, 30.0)
                continue

            # Successfully connected
            backoff = 2.0
            self.registry.update_status(device_id, DeviceStatus.ONLINE)

            # 1. Read Video Frame if camera
            if cam_adapter:
                ok, frame = cam_adapter.read_frame()
                if ok and frame is not None:
                    now = time.time()
                    device.last_seen = now
                    frame_counter += 1
                    
                    # Compute rolling FPS
                    if now - fps_timer >= 1.0:
                        current_fps = round(frame_counter / (now - fps_timer), 1)
                        device.fps = current_fps
                        frame_counter = 0
                        fps_timer = now

                    # Encode resized JPEG preview for web browser streaming
                    preview_h = min(360, frame.shape[0])
                    preview_w = int(frame.shape[1] * (preview_h / frame.shape[0]))
                    small_frame = cv2.resize(frame, (preview_w, preview_h))
                    _, jpeg_buf = cv2.imencode('.jpg', small_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                    
                    with self._lock:
                        self._latest_frames[device_id] = (now, jpeg_buf.tobytes(), frame)
                else:
                    self.registry.update_status(device_id, DeviceStatus.DEGRADED, error="Frame read dropped")

            # 2. Read Audio chunk if mic
            if mic_adapter:
                ok_audio, chunk = mic_adapter.read_chunk(duration_sec=4.0)
                if ok_audio and chunk is not None:
                    now = time.time()
                    device.last_seen = now
                    with self._lock:
                        self._latest_audio_chunks[device_id] = (now, chunk)

            # Limit capture rate (e.g. ~20-30 FPS)
            time.sleep(0.04)

    def get_latest_jpeg(self, device_id: str) -> Optional[bytes]:
        """Returns the latest JPEG preview byte buffer for MJPEG browser feeds."""
        with self._lock:
            val = self._latest_frames.get(device_id)
            return val[1] if val else None

    def get_latest_frame(self, device_id: str) -> Optional[np.ndarray]:
        """Returns the latest raw BGR frame for AI computer vision inference."""
        with self._lock:
            val = self._latest_frames.get(device_id)
            return val[2] if val else None

    def get_latest_audio(self, device_id: str) -> Optional[np.ndarray]:
        """Returns the latest raw audio float32 chunk for bioacoustics inference."""
        with self._lock:
            val = self._latest_audio_chunks.get(device_id)
            return val[1] if val else None

    def generate_mjpeg_stream(self, device_id: str) -> Generator[bytes, None, None]:
        """Yields multipart MJPEG chunks for real-time browser preview."""
        # Automatically activate stream if not already active
        self.start_device_stream(device_id)

        while True:
            jpeg = self.get_latest_jpeg(device_id)
            if jpeg:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n')
            else:
                # Blank placeholder while connecting
                blank = np.zeros((240, 320, 3), dtype=np.uint8)
                cv2.putText(blank, "CONNECTING...", (50, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
                _, buf = cv2.imencode('.jpg', blank)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
            time.sleep(0.08)
