"""
HTTP/MJPEG network camera adapter.
Connects to standard MJPEG IP cameras or video streaming servers.
"""

import cv2
import logging
from typing import Optional, Tuple
import numpy as np

from sensors.adapters import BaseCameraAdapter

logger = logging.getLogger("flocksense.sensors.http")

class HttpMjpegCameraAdapter(BaseCameraAdapter):
    def __init__(self, device_id: str, source_url: str):
        super().__init__(device_id, source_url)
        self.cap: Optional[cv2.VideoCapture] = None

    def connect(self) -> bool:
        if self.is_connected and self.cap and self.cap.isOpened():
            return True

        logger.info("Connecting to HTTP/MJPEG Camera %s at %s...", self.device_id, self.source_url)
        try:
            self.cap = cv2.VideoCapture(self.source_url)
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    self.is_connected = True
                    return True
            self.disconnect()
            return False
        except Exception as e:
            logger.error("HTTP Camera %s connection error: %s", self.device_id, e)
            self.disconnect()
            return False

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self.is_connected or not self.cap:
            return False, None
        try:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                self.is_connected = False
                return False, None
            return True, frame
        except Exception:
            self.is_connected = False
            return False, None

    def disconnect(self):
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        self.is_connected = False

    def test_connection(self) -> Tuple[bool, str, Optional[Tuple[int, int]]]:
        cap = cv2.VideoCapture(self.source_url)
        if not cap.isOpened():
            return False, "Could not open HTTP/MJPEG stream.", None
        ret, frame = cap.read()
        cap.release()
        if ret and frame is not None:
            h, w = frame.shape[:2]
            return True, f"HTTP/MJPEG stream accessible ({w}x{h}).", (w, h)
        return False, "Connected but unable to fetch image frames.", None
