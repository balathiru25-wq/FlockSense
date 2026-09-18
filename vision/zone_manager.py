import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np

class ZoneManager:
    """
    Manages virtual shed monitoring zones loaded from config/zones.json.
    Assigns detections/tracks to zones based on point-in-polygon tests.
    """
    def __init__(self, config_path: str = "config/zones.json"):
        self.config_path = Path(config_path)
        self.zones = []
        self.load_zones()

    def load_zones(self):
        if not self.config_path.exists():
            raise FileNotFoundError(f"Zone config not found at: {self.config_path}")
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.zones = data.get("zones", [])

    def get_zone_for_point(self, pt: Tuple[float, float], frame_w: int, frame_h: int) -> str:
        """
        Determines which zone contains point pt=(x, y) in pixel coordinates.
        Returns zone_id (e.g. 'ZONE_1') or 'UNKNOWN'.
        """
        if frame_w <= 0 or frame_h <= 0:
            return "UNKNOWN"

        norm_x = pt[0] / float(frame_w)
        norm_y = pt[1] / float(frame_h)
        point_norm = (norm_x, norm_y)

        for z in self.zones:
            poly = np.array(z["polygon"], dtype=np.float32)
            dist = cv2.pointPolygonTest(poly, point_norm, False)
            if dist >= 0:
                return z["zone_id"]

        return "UNKNOWN"

    def get_zone_info(self, zone_id: str) -> Optional[Dict[str, Any]]:
        for z in self.zones:
            if z["zone_id"] == zone_id:
                return z
        return None

    def get_all_zones(self) -> List[Dict[str, Any]]:
        return self.zones
