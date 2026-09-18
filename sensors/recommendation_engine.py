"""
FlockSense Sensor Recommendation Engine.
Calculates engineering prototype suggestions for cameras, microphones, and zones
based on flock size and optional shed dimensions.
"""

import math
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("flocksense.sensors.recommendation")

class SensorRecommendationEngine:
    def __init__(self, config_path: str = "config/sensor_recommendation.yaml"):
        self.config_path = Path(config_path)
        self.rules = []
        self.large_flock_rules = {"birds_per_camera": 100, "camera_to_mic_ratio": 2.0}
        self.coverage = {
            "max_sqm_per_camera": 60.0,
            "basis": "PROTOTYPE_RECOMMENDATION",
            "disclaimer": "This is a suggested starting setup based on flock size and shed coverage. It is an engineering recommendation for prototype testing, not a scientifically validated poultry requirement."
        }
        self.load_config()

    def load_config(self):
        if not self.config_path.exists():
            logger.warning("Config %s not found, using in-memory prototype defaults.", self.config_path)
            self._set_defaults()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            self.rules = data.get("rules", [])
            self.large_flock_rules = data.get("large_flock_rules", self.large_flock_rules)
            self.coverage = data.get("coverage", self.coverage)
        except Exception as e:
            logger.error("Failed to load recommendation config: %s", e)
            self._set_defaults()

    def _set_defaults(self):
        self.rules = [
            {"max_flock_size": 50, "cameras": 1, "microphones": 1, "zones": 1},
            {"max_flock_size": 150, "cameras": 2, "microphones": 1, "zones": 2},
            {"max_flock_size": 300, "cameras": 4, "microphones": 2, "zones": 4},
            {"max_flock_size": 500, "cameras": 6, "microphones": 3, "zones": 6},
            {"max_flock_size": 750, "cameras": 8, "microphones": 4, "zones": 8},
            {"max_flock_size": 1000, "cameras": 10, "microphones": 5, "zones": 10},
        ]

    def recommend(
        self,
        flock_size: int,
        shed_length_m: Optional[float] = None,
        shed_width_m: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculates recommended cameras, microphones, and zones.
        Ensures minimum 1 camera, 1 microphone, 1 zone.
        """
        if flock_size <= 0:
            flock_size = 1

        rec_cams = 1
        rec_mics = 1
        rec_zones = 1
        matched = False

        for r in self.rules:
            if flock_size <= r["max_flock_size"]:
                rec_cams = r["cameras"]
                rec_mics = r["microphones"]
                rec_zones = r["zones"]
                matched = True
                break

        if not matched:
            birds_per_cam = float(self.large_flock_rules.get("birds_per_camera", 100))
            rec_cams = max(1, math.ceil(flock_size / birds_per_cam))
            ratio = float(self.large_flock_rules.get("camera_to_mic_ratio", 2.0))
            rec_mics = max(1, math.ceil(rec_cams / ratio))
            rec_zones = rec_cams

        reason = f"{rec_cams} cameras, {rec_mics} microphones, and {rec_zones} zones suggested based on flock size of {flock_size} birds."

        # Optional dimension refinement
        if shed_length_m and shed_width_m and shed_length_m > 0 and shed_width_m > 0:
            area_sqm = shed_length_m * shed_width_m
            max_sqm = float(self.coverage.get("max_sqm_per_camera", 60.0))
            cams_by_area = max(1, math.ceil(area_sqm / max_sqm))
            if cams_by_area > rec_cams:
                rec_cams = cams_by_area
                rec_zones = max(rec_zones, rec_cams)
                rec_mics = max(rec_mics, math.ceil(rec_cams / 2))
                reason = f"{rec_cams} cameras suggested based on shed area ({area_sqm:.1f} m²) and flock size ({flock_size} birds)."

        return {
            "flock_size": flock_size,
            "shed_dimensions": {
                "length_m": shed_length_m,
                "width_m": shed_width_m
            } if shed_length_m and shed_width_m else None,
            "recommended_cameras": rec_cams,
            "recommended_microphones": rec_mics,
            "recommended_zones": rec_zones,
            "recommendation_reason": reason,
            "basis": self.coverage.get("basis", "PROTOTYPE_RECOMMENDATION"),
            "disclaimer": self.coverage.get("disclaimer", "")
        }

recommendation_engine = SensorRecommendationEngine()
