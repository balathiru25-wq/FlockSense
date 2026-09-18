"""
FlockSense Farm & Shed Setup Manager.
Manages persistent farm setup state (flock size, shed dimensions, zone creation,
and balanced device assignments).
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from sensors.recommendation_engine import recommendation_engine
from sensors.zone_layout_generator import zone_layout_generator

logger = logging.getLogger("flocksense.sensors.farm_setup")

class FarmSetupManager:
    def __init__(self, config_path: str = "config/farm_setup.json"):
        self.config_path = Path(config_path)
        self.state: Dict[str, Any] = self._default_state()
        self.load()

    def _default_state(self) -> Dict[str, Any]:
        return {
            "farm_name": "Main Poultry Farm",
            "shed_id": "SHED_1",
            "shed_name": "Broiler Shed A",
            "flock_size": 250,
            "shed_dimensions": {
                "length_m": 20.0,
                "width_m": 8.0
            },
            "recommended": {
                "cameras": 4,
                "microphones": 2,
                "zones": 4,
                "basis": "PROTOTYPE_RECOMMENDATION"
            },
            "configured": {
                "cameras": 4,
                "microphones": 2,
                "zones": 4
            },
            "is_setup_completed": True,
            "monitoring_active": True,
            "step": 7
        }

    def load(self):
        if not self.config_path.exists():
            # Initial launch defaults: save default state
            self.save()
            return
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.state = json.load(f)
        except Exception as e:
            logger.error("Failed to load farm setup: %s", e)
            self.state = self._default_state()

    def save(self):
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error("Failed to save farm setup: %s", e)

    def set_flock(
        self,
        flock_size: int,
        shed_length_m: Optional[float] = None,
        shed_width_m: Optional[float] = None,
        farm_name: Optional[str] = None,
        shed_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Updates flock information and computes recommendation.
        """
        if flock_size <= 0:
            flock_size = 1

        rec = recommendation_engine.recommend(
            flock_size=flock_size,
            shed_length_m=shed_length_m,
            shed_width_m=shed_width_m
        )

        self.state["flock_size"] = flock_size
        if shed_length_m and shed_width_m:
            self.state["shed_dimensions"] = {
                "length_m": shed_length_m,
                "width_m": shed_width_m
            }
        else:
            self.state["shed_dimensions"] = None

        if farm_name:
            self.state["farm_name"] = farm_name
        if shed_name:
            self.state["shed_name"] = shed_name

        self.state["recommended"] = {
            "cameras": rec["recommended_cameras"],
            "microphones": rec["recommended_microphones"],
            "zones": rec["recommended_zones"],
            "basis": rec["basis"],
            "reason": rec["recommendation_reason"],
            "disclaimer": rec["disclaimer"]
        }

        # Check comparison with current configured
        curr_cams = self.state.get("configured", {}).get("cameras", 0)
        curr_mics = self.state.get("configured", {}).get("microphones", 0)
        curr_zones = self.state.get("configured", {}).get("zones", 0)

        comparison = {
            "is_first_setup": not self.state.get("is_setup_completed", False),
            "current_setup": {
                "cameras": curr_cams,
                "microphones": curr_mics,
                "zones": curr_zones
            },
            "new_recommendation": self.state["recommended"],
            "camera_diff": rec["recommended_cameras"] - curr_cams,
            "mic_diff": rec["recommended_microphones"] - curr_mics,
            "zone_diff": rec["recommended_zones"] - curr_zones,
        }

        self.save()
        return {
            "flock_size": flock_size,
            "shed_dimensions": self.state.get("shed_dimensions"),
            "recommendation": self.state["recommended"],
            "comparison": comparison
        }

    def confirm_setup(
        self,
        cameras: int,
        microphones: int,
        zones: int,
        recreate_zones: bool = True
    ) -> Dict[str, Any]:
        """
        Confirms sensor counts and automatically generates and persists zones.
        """
        cameras = max(1, cameras)
        microphones = max(1, microphones)
        zones = max(1, zones)

        self.state["configured"] = {
            "cameras": cameras,
            "microphones": microphones,
            "zones": zones
        }

        aspect_ratio = 1.5
        dims = self.state.get("shed_dimensions")
        if dims and dims.get("length_m") and dims.get("width_m") and dims["width_m"] > 0:
            aspect_ratio = dims["length_m"] / dims["width_m"]

        generated_zones = []
        if recreate_zones:
            generated_zones = zone_layout_generator.generate_zones(
                num_zones=zones,
                aspect_ratio=aspect_ratio
            )
            zone_layout_generator.save_zones(generated_zones)

        self.save()
        return {
            "configured": self.state["configured"],
            "zones_created": len(generated_zones),
            "zones": generated_zones or zone_layout_generator.load_zones()
        }

    @staticmethod
    def auto_assign_devices(
        cameras: List[Dict[str, Any]],
        microphones: List[Dict[str, Any]],
        zones: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculates suggested 1-to-1 camera assignments and balanced multi-zone microphone coverage.
        """
        num_zones = len(zones)
        zone_ids = [z["zone_id"] for z in zones] if zones else ["ZONE_1"]
        if not zone_ids:
            zone_ids = ["ZONE_1"]

        cam_assignments = {}
        for idx, cam in enumerate(cameras):
            assigned_z = zone_ids[idx % len(zone_ids)]
            cam_assignments[cam["device_id"]] = [assigned_z]

        mic_assignments = {}
        num_mics = len(microphones)
        if num_mics > 0:
            zones_per_mic = max(1, len(zone_ids) // num_mics)
            for m_idx, mic in enumerate(microphones):
                start_z = m_idx * zones_per_mic
                if m_idx == num_mics - 1:
                    # Last microphone covers the remaining zones to avoid coverage gaps
                    assigned_zs = zone_ids[start_z:]
                else:
                    assigned_zs = zone_ids[start_z:start_z + zones_per_mic]
                if not assigned_zs:
                    assigned_zs = [zone_ids[m_idx % len(zone_ids)]]
                mic_assignments[mic["device_id"]] = assigned_zs

        return {
            "camera_assignments": cam_assignments,
            "microphone_assignments": mic_assignments
        }

    def complete_setup(self) -> Dict[str, Any]:
        self.state["is_setup_completed"] = True
        self.state["monitoring_active"] = True
        self.state["step"] = 8
        self.save()
        return self.state

farm_setup_manager = FarmSetupManager()
