"""
Camera Anomaly Detector Service for FlockSense.

Evaluates behavioral deviation using an unsupervised Isolation Forest model.
Maps raw decision function scores to a normalized Camera Behaviour Deviation Score (0-100).
Provides transparent explainability reasons comparing feature values to baseline statistics.

IMPORTANT:
- Validation Status: PROTOTYPE_ONLY_SYNTHETIC_DATA
- Real-World Validated: NO
- Clinical / Disease Inference: NONE
- Purpose: Unsupervised behavioural deviation detector for architectural verification
  and subsequent Audio + Camera Fusion prototyping.
"""

import json
import pickle
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

# Core behavioral, spatial, and social features used for anomaly scoring
FEATURE_NAMES = [
    "movement_rate",
    "movement_variance",
    "distance_travelled_pixels",
    "stationary_duration",
    "stationary_ratio",
    "standing_ratio",
    "feeding_ratio",
    "sitting_ratio",
    "spreading_ratio",
    "preening_ratio",
    "resting_ratio",
    "walking_ratio",
    "behaviour_transition_rate",
    "distance_to_nearest_bird",
    "distance_to_flock_centroid",
    "relative_isolation_score",
    "relative_activity",
    "zone_transition_count"
]

class CameraAnomalyDetector:
    """
    Evaluates behavioral deviation using Isolation Forest.
    
    Transforms raw Isolation Forest anomaly decision function scores into
    a human-readable 'Camera Behaviour Deviation Score' (0 to 100).
    Provides transparent explainability by comparing bird features against baseline statistics.
    
    IMPORTANT: This score measures behavior deviation from flock baseline.
    It does NOT represent disease probability or clinical infection.
    """
    def __init__(self, model_path="models/camera_anomaly_model.pkl", config_path="config/camera_anomaly_config.json"):
        self.model_path = Path(model_path)
        self.config_path = Path(config_path)
        self.model = None
        self.scaler = None
        self.feature_names = FEATURE_NAMES
        self.baseline_stats = {}
        self.validation_status = "PROTOTYPE_ONLY_SYNTHETIC_DATA"
        self.training_data_type = "SYNTHETIC"
        self.load_model()

    def load_model(self):
        if self.model_path.exists():
            with open(self.model_path, "rb") as f:
                saved = pickle.load(f)
                self.model = saved.get("model")
                self.scaler = saved.get("scaler")
                self.feature_names = saved.get("feature_names", FEATURE_NAMES)
                self.baseline_stats = saved.get("baseline_stats", {})
                meta = saved.get("metadata", {})
                self.validation_status = meta.get("validation_status", "PROTOTYPE_ONLY_SYNTHETIC_DATA")
                self.training_data_type = meta.get("training_data_type", "SYNTHETIC")

        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if not self.baseline_stats:
                    self.baseline_stats = cfg.get("baseline_stats", {})
                self.validation_status = cfg.get("validation_status", self.validation_status)

    def is_trained(self) -> bool:
        return self.model is not None

    def predict_camera_anomaly(self, feature_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reusable inference interface matching FlockSense service contract.

        Expected return:
        {
            "camera_deviation_score": float (0-100),
            "status": "NORMAL_PATTERN" | "WATCH_DEVIATION" | "HIGH_DEVIATION",
            "raw_anomaly_score": float,
            "reasons": List[str],
            "validation_status": "PROTOTYPE_ONLY_SYNTHETIC_DATA",
            "training_data_type": "SYNTHETIC",
            "real_world_validated": False,
            "clinical_validated": False
        }
        """
        score, status, reasons, raw_score = self.compute_anomaly_score_full(feature_dict)
        return {
            "camera_deviation_score": score,
            "status": status,
            "raw_anomaly_score": raw_score,
            "reasons": reasons,
            "validation_status": self.validation_status,
            "training_data_type": self.training_data_type,
            "real_world_validated": False,
            "clinical_validated": False
        }

    def compute_anomaly_score(self, feature_dict: Dict[str, Any]) -> Tuple[float, str, List[str]]:
        """Convenience method returning (deviation_score, status, reasons)."""
        score, status, reasons, _ = self.compute_anomaly_score_full(feature_dict)
        return score, status, reasons

    def compute_anomaly_score_full(self, feature_dict: Dict[str, Any]) -> Tuple[float, str, List[str], float]:
        """
        Computes the Camera Behaviour Deviation Score (0–100), status level,
        contributing reasons, and raw anomaly decision function score.
        """
        if not self.is_trained():
            return 0.0, "NORMAL_PATTERN", ["Model uninitialized"], 0.0

        # Vectorize features in preserved feature order
        x_vec = np.array([float(feature_dict.get(f, 0.0)) for f in self.feature_names]).reshape(1, -1)
        if self.scaler:
            x_scaled = self.scaler.transform(x_vec)
        else:
            x_scaled = x_vec

        # IsolationForest decision_function returns positive for baseline inliers, negative for outliers
        # Typical baseline range is approx [-0.04, +0.10]. Anomalies fall well below 0.0 (down to -0.30 or lower)
        raw_score = float(self.model.decision_function(x_scaled)[0])

        # Normalized mapping:
        # Lower raw_score (more anomalous) -> Higher deviation_score (closer to 100)
        # Decision function of +0.06 -> ~40 (normal)
        # Decision function of 0.00 -> 50 (borderline watch)
        # Decision function of -0.15 -> ~74 (high deviation)
        # Formula: deviation_score = clip(50.0 - (raw_score * 160.0), 0.0, 100.0)
        normalized_deviation = 50.0 - (raw_score * 160.0)
        deviation_score = float(np.clip(normalized_deviation, 0.0, 100.0))

        # Provisional synthetic thresholds
        if deviation_score >= 70.0:
            status = "HIGH_DEVIATION"
        elif deviation_score >= 45.0:
            status = "WATCH_DEVIATION"
        else:
            status = "NORMAL_PATTERN"

        # Generate explainability reasons by comparing against baseline stats
        reasons = self._generate_explainability_reasons(feature_dict)

        return round(deviation_score, 1), status, reasons, round(raw_score, 4)

    def _generate_explainability_reasons(self, feature_dict: Dict[str, Any]) -> List[str]:
        """
        Identifies specific behavioural and spatial metrics that deviate substantially
        from baseline distribution statistics.
        Does NOT generate medical or disease labels.
        """
        reasons = []
        if not self.baseline_stats:
            return ["Baseline statistics unavailable for detailed attribution"]

        # 1. Activity & Movement
        movement = float(feature_dict.get("movement_rate", 0.0))
        base_movement_stats = self.baseline_stats.get("movement_rate", {})
        base_mov_med = base_movement_stats.get("median", 2.5)
        rel_activity = float(feature_dict.get("relative_activity", 1.0))
        
        if rel_activity < 0.35 and base_mov_med > 1.0:
            reasons.append("movement rate substantially below flock median baseline")
        elif movement > 50.0 and base_mov_med < 10.0:
            reasons.append("unusually elevated locomotor activity exceeding normal baseline")

        # 2. Stationary duration & ratio
        stat_dur = float(feature_dict.get("stationary_duration", 0.0))
        stat_ratio = float(feature_dict.get("stationary_ratio", 0.0))
        base_stat = self.baseline_stats.get("stationary_duration", {}).get("mean", 3.2)
        if stat_ratio > 0.85 and stat_dur > (base_stat * 1.3):
            reasons.append("prolonged stationary duration exceeding peer baseline")

        # 3. Social & Spatial Isolation
        iso_score = float(feature_dict.get("relative_isolation_score", 0.0))
        base_iso = self.baseline_stats.get("relative_isolation_score", {}).get("mean", 0.26)
        dist_nearest = float(feature_dict.get("distance_to_nearest_bird", 0.0))
        dist_flock = float(feature_dict.get("distance_to_flock_centroid", 0.0))
        if base_iso > 0 and (iso_score / base_iso) >= 1.35:
            reasons.append("unusually high spatial isolation from nearest birds and flock centroid")
        elif dist_flock > 320.0:
            reasons.append("spatial position significantly peripheral relative to flock cluster")

        # 4. Posture & Behavioral shifts
        sitting_ratio = float(feature_dict.get("sitting_ratio", 0.0))
        base_sitting = self.baseline_stats.get("sitting_ratio", {}).get("mean", 0.16)
        if sitting_ratio > 0.65 and (sitting_ratio > base_sitting * 2.0):
            reasons.append("predominant sitting posture relative to moving flock peers")

        feeding_ratio = float(feature_dict.get("feeding_ratio", 0.0))
        base_feeding = self.baseline_stats.get("feeding_ratio", {}).get("mean", 0.33)
        if base_feeding > 0.20 and feeding_ratio == 0.0 and stat_ratio > 0.70:
            reasons.append("reduced feeding activity observed during active flock interval")

        # 5. Zone transitions
        zone_transitions = int(feature_dict.get("zone_transition_count", 0))
        base_zone_trans = self.baseline_stats.get("zone_transition_count", {}).get("max", 1)
        if zone_transitions > (base_zone_trans + 2):
            reasons.append("unusually frequent zone transitions indicating agitation")

        if not reasons:
            reasons.append("behaviour patterns within normal baseline parameters")

        return reasons

if __name__ == "__main__":
    detector = CameraAnomalyDetector()
    print("Camera Anomaly Detector initialized. Is trained:", detector.is_trained())
    sample_feat = {
        "movement_rate": 54.0,
        "movement_variance": 194.4,
        "distance_travelled_pixels": 286.0,
        "stationary_duration": 0.0,
        "stationary_ratio": 0.0,
        "standing_ratio": 0.5,
        "feeding_ratio": 0.0,
        "sitting_ratio": 0.5,
        "spreading_ratio": 0.0,
        "preening_ratio": 0.0,
        "resting_ratio": 0.0,
        "walking_ratio": 0.0,
        "behaviour_transition_rate": 0.201,
        "distance_to_nearest_bird": 273.4,
        "distance_to_flock_centroid": 185.9,
        "relative_isolation_score": 0.2482,
        "relative_activity": 2.0,
        "zone_transition_count": 1
    }
    result = detector.predict_camera_anomaly(sample_feat)
    print("Sample Inference Result:")
    print(json.dumps(result, indent=2))
