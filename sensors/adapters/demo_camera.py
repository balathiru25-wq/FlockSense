"""
Demo / Synthetic camera feed adapter.
Generates smooth, realistic synthetic video frames with labeled zones, simulated chicken centroids,
and timecode overlays for hackathons, presentations, and testing when physical cameras are offline.
"""

import cv2
import time
import numpy as np
import logging
from typing import Optional, Tuple

from sensors.adapters import BaseCameraAdapter

logger = logging.getLogger("flocksense.sensors.demo_camera")

class DemoCameraAdapter(BaseCameraAdapter):
    def __init__(self, device_id: str, source_url: str):
        super().__init__(device_id, source_url)
        self.frame_count = 0
        self.width = 640
        self.height = 360

    def connect(self) -> bool:
        self.is_connected = True
        logger.info("Demo Camera %s CONNECTED (Synthetic Feed)", self.device_id)
        return True

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self.is_connected:
            return False, None

        self.frame_count += 1
        # Create dark shed background
        frame = np.full((self.height, self.width, 3), (25, 20, 15), dtype=np.uint8)

        # Draw shed grid lines
        cv2.line(frame, (int(self.width / 3), 0), (int(self.width / 3), self.height), (45, 40, 35), 1)
        cv2.line(frame, (int(self.width * 2 / 3), 0), (int(self.width * 2 / 3), self.height), (45, 40, 35), 1)
        cv2.line(frame, (0, int(self.height / 2)), (self.width, int(self.height / 2)), (45, 40, 35), 1)

        # Animate demo birds
        t = time.time()
        b1_x = int(self.width * 0.18 + np.sin(t * 0.8) * 20)
        b1_y = int(self.height * 0.3 + np.cos(t * 0.8) * 15)
        
        b2_x = int(self.width * 0.5 + np.sin(t * 0.5) * 30)
        b2_y = int(self.height * 0.25 + np.cos(t * 0.5) * 10)

        # Draw chicken markers
        cv2.circle(frame, (b1_x, b1_y), 9, (0, 200, 255), -1)
        cv2.putText(frame, "#12", (b1_x - 10, b1_y - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        cv2.circle(frame, (b2_x, b2_y), 9, (50, 100, 255), -1)
        cv2.putText(frame, "#17", (b2_x - 10, b2_y - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        # Header banner overlay
        cv2.rectangle(frame, (0, 0), (self.width, 28), (15, 10, 5), -1)
        cv2.putText(frame, f"FLOCKSENSE GATEWAY - {self.device_id.upper()} (DEMO FEED)", 
                    (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 230, 150), 1)

        # Timestamp
        time_str = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, time_str, (self.width - 150, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 180, 180), 1)

        return True, frame

    def disconnect(self):
        self.is_connected = False
        logger.info("Demo Camera %s disconnected.", self.device_id)

    def test_connection(self) -> Tuple[bool, str, Optional[Tuple[int, int]]]:
        return True, "Demo video generator verified.", (self.width, self.height)
