"""
RTSP IP Camera adapter using OpenCV VideoCapture.
Supports TCP/UDP transport, low buffer latency, and robust frame reading.
"""

import cv2
import time
import os
import logging
from typing import Optional, Tuple
import numpy as np

from sensors.adapters import BaseCameraAdapter

logger = logging.getLogger("flocksense.sensors.rtsp")

class RtspCameraAdapter(BaseCameraAdapter):
    def __init__(self, device_id: str, source_url: str):
        super().__init__(device_id, source_url)
        self.cap: Optional[cv2.VideoCapture] = None

    def connect(self) -> bool:
        if self.is_connected and self.cap and self.cap.isOpened():
            return True

        logger.info("Connecting to RTSP Camera %s at %s...", self.device_id, self.source_url)
        try:
            # Tell FFmpeg to use TCP for reliable streaming in farm LANs
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|fflags;nobuffer|max_delay;500000"
            self.cap = cv2.VideoCapture(self.source_url, cv2.CAP_FFMPEG)
            if self.cap.isOpened():
                # Read 1 frame to verify video decoding
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    self.is_connected = True
                    logger.info("RTSP Camera %s CONNECTED (%dx%d)", self.device_id, frame.shape[1], frame.shape[0])
                    return True

            self.disconnect()
            return False
        except Exception as e:
            logger.error("RTSP Camera %s connection error: %s", self.device_id, e)
            self.disconnect()
            return False

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self.is_connected or not self.cap or not self.cap.isOpened():
            return False, None
        try:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                self.is_connected = False
                return False, None
            return True, frame
        except Exception as e:
            logger.error("RTSP Camera %s read error: %s", self.device_id, e)
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
        logger.info("RTSP Camera %s disconnected.", self.device_id)

    def test_connection(self) -> Tuple[bool, str, Optional[Tuple[int, int]]]:
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|fflags;nobuffer"
        test_cap = cv2.VideoCapture(self.source_url, cv2.CAP_FFMPEG)
        if not test_cap.isOpened():
            return False, "Could not establish RTSP network connection.", None
        
        ret, frame = test_cap.read()
        test_cap.release()
        if ret and frame is not None:
            h, w = frame.shape[:2]
            return True, f"Connection verified. Stream resolution {w}x{h}", (w, h)
        return False, "Connected to RTSP server but failed to decode video frames.", None
