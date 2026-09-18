"""
Sensor adapter base classes and interfaces for camera and audio streams.
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple, Any
import numpy as np

class BaseCameraAdapter(ABC):
    """
    Abstract interface for video input devices (RTSP, ONVIF, HTTP, Webcam, Demo).
    """
    def __init__(self, device_id: str, source_url: str):
        self.device_id = device_id
        self.source_url = source_url
        self.is_connected: bool = False

    @abstractmethod
    def connect(self) -> bool:
        """Establishes stream connection."""
        pass

    @abstractmethod
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Reads latest BGR frame from stream. Returns (success, frame)."""
        pass

    @abstractmethod
    def disconnect(self):
        """Releases hardware / network stream."""
        pass

    @abstractmethod
    def test_connection(self) -> Tuple[bool, str, Optional[Tuple[int, int]]]:
        """Probes stream without persistent lock. Returns (success, message, (width, height))."""
        pass

class BaseMicrophoneAdapter(ABC):
    """
    Abstract interface for audio input devices (Network audio, RTSP audio, Local Mic, Demo).
    """
    def __init__(self, device_id: str, source_url: str, sample_rate: int = 16000):
        self.device_id = device_id
        self.source_url = source_url
        self.sample_rate = sample_rate
        self.is_connected: bool = False

    @abstractmethod
    def connect(self) -> bool:
        """Establishes audio stream connection."""
        pass

    @abstractmethod
    def read_chunk(self, duration_sec: float = 4.0) -> Tuple[bool, Optional[np.ndarray]]:
        """Captures audio chunk as 1D float32 numpy array normalized to [-1.0, 1.0]."""
        pass

    @abstractmethod
    def disconnect(self):
        """Releases audio stream."""
        pass

    @abstractmethod
    def test_connection(self) -> Tuple[bool, str]:
        """Probes microphone audio stream."""
        pass
