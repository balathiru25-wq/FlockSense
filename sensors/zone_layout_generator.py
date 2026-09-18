"""
FlockSense Dynamic Zone Layout Generator.
Generates balanced normalized grid polygons [0.0, 1.0] for any given zone count
and persists zones to config/zones.json.
"""

import json
import math
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("flocksense.sensors.zone_generator")

# Default distinct BGR colors for zones
PALETTE_BGR = [
    [255, 120, 0],   # Blue-ish
    [0, 200, 255],   # Amber/Yellow
    [0, 255, 128],   # Green
    [255, 0, 128],   # Magenta
    [128, 0, 255],   # Orange
    [0, 128, 255],   # Azure
    [200, 255, 0],   # Teal
    [255, 0, 255],   # Purple
    [0, 255, 255],   # Pure Yellow
    [128, 255, 0],   # Cyan
    [255, 128, 128], # Pink
    [128, 128, 255], # Light Orange
]

class ZoneLayoutGenerator:
    def __init__(self, config_path: str = "config/zones.json"):
        self.config_path = Path(config_path)

    @staticmethod
    def calculate_grid_dimensions(num_zones: int, aspect_ratio: float = 1.5) -> tuple[int, int]:
        """
        Calculates optimal (rows, cols) for num_zones given approximate shed aspect ratio.
        """
        if num_zones <= 1:
            return 1, 1
        if num_zones == 2:
            return 1, 2
        if num_zones == 3:
            return 1, 3
        if num_zones == 4:
            return 2, 2
        if num_zones == 5:
            return 2, 3  # 6 cells, 5 used
        if num_zones == 6:
            return 2, 3
        if num_zones in (7, 8):
            return 2, 4
        if num_zones in (9, 10):
            return 2, 5
        if num_zones in (11, 12):
            return 3, 4

        # For arbitrary zone counts, find closest factorization
        cols = math.ceil(math.sqrt(num_zones * aspect_ratio))
        rows = math.ceil(num_zones / cols)
        return rows, cols

    def generate_zones(
        self,
        num_zones: int,
        aspect_ratio: float = 1.5,
        custom_names: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generates normalized bounding polygons [0.0, 1.0] for num_zones.
        """
        num_zones = max(1, num_zones)
        rows, cols = self.calculate_grid_dimensions(num_zones, aspect_ratio)
        custom_names = custom_names or {}

        zones = []
        cell_w = 1.0 / cols
        cell_h = 1.0 / rows
        created = 0

        for r in range(rows):
            for c in range(cols):
                if created >= num_zones:
                    break
                z_idx = created + 1
                zone_id = f"ZONE_{z_idx}"
                default_name = f"Zone {z_idx}"
                display_name = custom_names.get(zone_id, default_name)

                x0 = round(c * cell_w, 4)
                y0 = round(r * cell_h, 4)
                x1 = 1.0 if c == cols - 1 or created == num_zones - 1 else round((c + 1) * cell_w, 4)
                y1 = 1.0 if r == rows - 1 else round((r + 1) * cell_h, 4)

                color = PALETTE_BGR[(z_idx - 1) % len(PALETTE_BGR)]

                polygon = [
                    [x0, y0],
                    [x1, y0],
                    [x1, y1],
                    [x0, y1]
                ]

                zones.append({
                    "zone_id": zone_id,
                    "name": display_name,
                    "display_name": display_name,
                    "color_bgr": color,
                    "polygon": polygon,
                    "bounds": {
                        "x0": x0,
                        "y0": y0,
                        "x1": x1,
                        "y1": y1
                    }
                })
                created += 1

        return zones

    def save_zones(self, zones: List[Dict[str, Any]]) -> bool:
        """
        Persists generated zones to config/zones.json.
        """
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "description": f"FlockSense {len(zones)}-Zone Shed Layout (Normalized Coordinates [0.0, 1.0])",
                "zones": zones
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            logger.info("Saved %d zones to %s", len(zones), self.config_path)
            return True
        except Exception as e:
            logger.error("Failed to save zones to %s: %s", self.config_path, e)
            return False

    def load_zones(self) -> List[Dict[str, Any]]:
        if not self.config_path.exists():
            return []
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("zones", [])
        except Exception as e:
            logger.error("Failed to read zones: %s", e)
            return []

zone_layout_generator = ZoneLayoutGenerator()
