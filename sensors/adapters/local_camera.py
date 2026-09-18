"""
Local USB Webcam / V4L2 / DirectShow adapter for on-site local testing and farm PCs.
"""

import cv2
import logging
from typing import Optional, Tuple
import numpy as np

from sensors.adapters import BaseCameraAdapter

logger = logging.getLogger("flocksense.sensors.local")

class LocalCameraAdapter(BaseCameraAdapter):
    def __init__(self, device_id: str, source_url: str):
        super().__init__(device_id, source_url)
        # Parse device index (e.g. "0" or "video0")
        try:
            cleaned = source_url.replace("video", "").strip()
            self.device_index = int(cleaned)
        except Exception:
            self.device_index = 0
        self.cap: Optional[cv2.VideoCapture] = None

    def connect(self) -> bool:
        if self.is_connected and self.cap and self.cap.isOpened():
            return True

        logger.info("Opening Local Camera %s (Index: %d)...", self.device_id, self.device_index)
        try:
            self.cap = cv2.VideoCapture(self.device_index)
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    self.is_connected = True
                    return True
            self.disconnect()
            return False
        except Exception as e:
            logger.error("Local camera %s error: %s", self.device_id, e)
            self.disconnect()
            return False

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self.is_connected or not self.cap:
            return False, None
        try:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                return False, None
            return True, frame
        except Exception:
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
        cap = cv2.VideoCapture(self.device_index)
        if not cap.isOpened():
            return False, f"Local camera index {self.device_index} not detected.", None
        ret, frame = cap.read()
        cap.release()
        if ret and frame is not None:
            h, w = frame.shape[:2]
            return True, f"Local camera verified ({w}x{h}).", (w, h)
        return False, f"Camera device {self.device_index} opened but could not read frame.", None
