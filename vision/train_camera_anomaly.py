"""
Train Camera Anomaly Isolation Forest Model for FlockSense.

IMPORTANT DISCLAIMER:
- Training Data: SYNTHETIC / DEVELOPMENT PROTOTYPE ONLY
- Real-World Validated: NO
- Clinical / Disease Diagnoses: NONE
- Purpose: Unsupervised behavioural deviation detector for architectural verification
  and subsequent Audio + Camera Fusion prototyping.
"""

import json
import pickle
import csv
from pathlib import Path
from typing import Dict, List, Any, Tuple
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

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

def load_seed_features(csv_path: str = "outputs/vision/features/bird_behavior_features.csv") -> List[Dict[str, float]]:
    """Loads existing extracted feature rows from the CSV."""
    seed_records = []
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Feature CSV not found: {csv_path}")

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed = {}
            for k, v in row.items():
                try:
                    parsed[k] = float(v)
                except ValueError:
                    parsed[k] = v
            seed_records.append(parsed)
    return seed_records

def generate_synthetic_baseline_features(
    seed_records: List[Dict[str, float]], 
    n_samples: int = 150, 
    random_state: int = 42
) -> np.ndarray:
    """
    Generates a synthetic baseline distribution reflecting expected normal flock behavioral variation.
    Includes active birds (standing/walking/exploring), feeding birds, and preening/resting birds,
    cohesive within flock spatial boundaries.
    """
    rng = np.random.RandomState(random_state)
    synthetic_rows = []

    # Realistic normal archetypes for synthetic flock:
    # Archetype 1: Active feeder (moderate movement, high feeding, low stationary)
    # Archetype 2: Active walker/stander (higher movement, standing/walking, low stationary)
    # Archetype 3: Calm feeder (low movement, high stationary feeding)
    # Archetype 4: Preener/stander (low movement, preening & standing, cohesive)
    archetypes = [
        # 1. Moving / exploring bird
        {
            "movement_rate": 35.0, "movement_variance": 120.0, "distance_travelled_pixels": 180.0,
            "stationary_duration": 1.5, "stationary_ratio": 0.30, "standing_ratio": 0.60,
            "feeding_ratio": 0.20, "sitting_ratio": 0.10, "spreading_ratio": 0.0,
            "preening_ratio": 0.0, "resting_ratio": 0.0, "walking_ratio": 0.10,
            "behaviour_transition_rate": 0.20, "distance_to_nearest_bird": 270.0,
            "distance_to_flock_centroid": 180.0, "relative_isolation_score": 0.25,
            "relative_activity": 1.5, "zone_transition_count": 1
        },
        # 2. Feeding station bird
        {
            "movement_rate": 5.0, "movement_variance": 8.0, "distance_travelled_pixels": 25.0,
            "stationary_duration": 4.0, "stationary_ratio": 0.80, "standing_ratio": 0.15,
            "feeding_ratio": 0.80, "sitting_ratio": 0.05, "spreading_ratio": 0.0,
            "preening_ratio": 0.0, "resting_ratio": 0.0, "walking_ratio": 0.0,
            "behaviour_transition_rate": 0.10, "distance_to_nearest_bird": 260.0,
            "distance_to_flock_centroid": 170.0, "relative_isolation_score": 0.24,
            "relative_activity": 0.8, "zone_transition_count": 0
        },
        # 3. Preening / standing bird
        {
            "movement_rate": 2.0, "movement_variance": 3.0, "distance_travelled_pixels": 10.0,
            "stationary_duration": 4.5, "stationary_ratio": 0.90, "standing_ratio": 0.65,
            "feeding_ratio": 0.05, "sitting_ratio": 0.0, "spreading_ratio": 0.0,
            "preening_ratio": 0.30, "resting_ratio": 0.0, "walking_ratio": 0.0,
            "behaviour_transition_rate": 0.15, "distance_to_nearest_bird": 310.0,
            "distance_to_flock_centroid": 220.0, "relative_isolation_score": 0.29,
            "relative_activity": 0.8, "zone_transition_count": 0
        },
        # 4. Balanced flock member
        {
            "movement_rate": 18.0, "movement_variance": 45.0, "distance_travelled_pixels": 90.0,
            "stationary_duration": 2.8, "stationary_ratio": 0.55, "standing_ratio": 0.45,
            "feeding_ratio": 0.35, "sitting_ratio": 0.10, "spreading_ratio": 0.0,
            "preening_ratio": 0.10, "resting_ratio": 0.0, "walking_ratio": 0.0,
            "behaviour_transition_rate": 0.20, "distance_to_nearest_bird": 280.0,
            "distance_to_flock_centroid": 185.0, "relative_isolation_score": 0.26,
            "relative_activity": 1.0, "zone_transition_count": 0
        }
    ]

    for i in range(n_samples):
        base_dict = archetypes[i % len(archetypes)]
        sample_dict = {}

        for k in FEATURE_NAMES:
            val = base_dict[k]
            # Normal flock jitter (10-20%)
            jitter = rng.normal(0, max(0.15 * val, 0.05))
            sample_dict[k] = val + jitter

        # Bound checks
        sample_dict["movement_rate"] = max(0.0, sample_dict["movement_rate"])
        sample_dict["movement_variance"] = max(0.0, sample_dict["movement_variance"])
        sample_dict["distance_travelled_pixels"] = max(0.0, sample_dict["distance_travelled_pixels"])
        sample_dict["stationary_duration"] = max(0.0, min(5.0, sample_dict["stationary_duration"]))
        sample_dict["stationary_ratio"] = max(0.0, min(1.0, sample_dict["stationary_ratio"]))

        # Normalize behavior ratios
        beh_keys = ["standing_ratio", "feeding_ratio", "sitting_ratio", "spreading_ratio", "preening_ratio", "resting_ratio", "walking_ratio"]
        b_vals = np.array([max(0.0, sample_dict[k]) for k in beh_keys])
        if b_vals.sum() > 0:
            b_vals = b_vals / b_vals.sum()
        for k, v in zip(beh_keys, b_vals):
            sample_dict[k] = float(v)

        sample_dict["behaviour_transition_rate"] = max(0.0, sample_dict["behaviour_transition_rate"])
        sample_dict["distance_to_nearest_bird"] = max(150.0, sample_dict["distance_to_nearest_bird"])
        sample_dict["distance_to_flock_centroid"] = max(100.0, sample_dict["distance_to_flock_centroid"])
        sample_dict["relative_isolation_score"] = max(0.15, min(0.38, sample_dict["relative_isolation_score"]))
        sample_dict["relative_activity"] = max(0.4, sample_dict["relative_activity"])
        sample_dict["zone_transition_count"] = max(0, int(round(sample_dict["zone_transition_count"])))

        synthetic_rows.append([sample_dict[f] for f in FEATURE_NAMES])

    # Append exact seed rows from CSV
    for rec in seed_records:
        synthetic_rows.append([float(rec.get(f, 0.0)) for f in FEATURE_NAMES])

    return np.array(synthetic_rows)

def compute_baseline_statistics(features_matrix: np.ndarray) -> Dict[str, Dict[str, float]]:
    """Calculates summary statistics across features for explainability reasoning."""
    stats = {}
    for i, name in enumerate(FEATURE_NAMES):
        vals = features_matrix[:, i]
        stats[name] = {
            "mean": round(float(np.mean(vals)), 4),
            "median": round(float(np.median(vals)), 4),
            "std": round(float(np.std(vals)), 4),
            "min": round(float(np.min(vals)), 4),
            "max": round(float(np.max(vals)), 4),
            "q25": round(float(np.percentile(vals, 25)), 4),
            "q75": round(float(np.percentile(vals, 75)), 4)
        }
    return stats

def train_and_save():
    print("=" * 60)
    print("FlockSense Camera Anomaly: Isolation Forest Baseline Training")
    print("STATUS: PROTOTYPE ONLY (SYNTHETIC DATA)")
    print("=" * 60)

    # 1. Load seed features
    seed_records = load_seed_features()
    print(f"Loaded {len(seed_records)} seed track feature records from CSV.")

    # 2. Generate baseline training feature set
    n_baseline_samples = 120
    random_state = 42
    X_train = generate_synthetic_baseline_features(seed_records, n_samples=n_baseline_samples, random_state=random_state)
    print(f"Constructed baseline feature matrix: {X_train.shape[0]} windows x {X_train.shape[1]} features.")

    # 3. Fit StandardScaler
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)

    # 4. Fit Isolation Forest
    # Using provisional contamination=0.10 for prototype boundary learning
    contamination = 0.10
    n_estimators = 100
    iso_forest = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=random_state,
        n_jobs=-1
    )
    iso_forest.fit(X_scaled)
    print("Fitted Isolation Forest successfully.")

    # 5. Analyze decision function distribution on baseline
    decision_scores = iso_forest.decision_function(X_scaled)
    print(f"Baseline Decision Function Range: min={decision_scores.min():.4f}, "
          f"median={np.median(decision_scores):.4f}, max={decision_scores.max():.4f}")

    # 6. Baseline statistics for explainability
    baseline_stats = compute_baseline_statistics(X_train)

    # 7. Model artifact bundle
    model_payload = {
        "model": iso_forest,
        "scaler": scaler,
        "feature_names": FEATURE_NAMES,
        "baseline_stats": baseline_stats,
        "metadata": {
            "algorithm": "IsolationForest",
            "n_estimators": n_estimators,
            "contamination": contamination,
            "contamination_status": "PROVISIONAL",
            "random_state": random_state,
            "training_data_type": "SYNTHETIC",
            "validation_status": "PROTOTYPE_ONLY_SYNTHETIC_DATA",
            "real_world_validated": False,
            "clinical_validated": False,
            "model_version": "1.0.0-synthetic-proto"
        }
    }

    # Save model pkl
    models_dir = Path("models")
    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / "camera_anomaly_model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model_payload, f)
    print(f"Saved camera anomaly model bundle: {model_path}")

    # Save scaler separately as requested
    scaler_path = models_dir / "camera_anomaly_scaler.pkl"
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)
    print(f"Saved camera anomaly scaler: {scaler_path}")

    # Save baseline stats JSON
    baseline_stats_path = models_dir / "camera_anomaly_baseline.json"
    with open(baseline_stats_path, "w", encoding="utf-8") as f:
        json.dump({
            "validation_status": "PROTOTYPE_ONLY_SYNTHETIC_DATA",
            "training_data_type": "SYNTHETIC",
            "real_world_validated": False,
            "clinical_validated": False,
            "feature_names": FEATURE_NAMES,
            "baseline_statistics": baseline_stats
        }, f, indent=2)
    print(f"Saved baseline statistics: {baseline_stats_path}")

    # 8. Save config
    config_dir = Path("config")
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "camera_anomaly_config.json"
    config_data = {
        "algorithm": "IsolationForest",
        "random_state": random_state,
        "n_estimators": n_estimators,
        "contamination": contamination,
        "contamination_status": "PROVISIONAL_DEVELOPMENT_VALUE",
        "feature_names": FEATURE_NAMES,
        "feature_window_duration_seconds": 5.0,
        "training_data_source": "outputs/vision/features/bird_behavior_features.csv",
        "training_data_type": "SYNTHETIC",
        "validation_status": "PROTOTYPE_ONLY_SYNTHETIC_DATA",
        "real_world_validated": False,
        "clinical_validated": False,
        "scaler_usage": "StandardScaler",
        "model_version": "1.0.0-synthetic-proto",
        "score_mapping": {
            "type": "affine_clamped_decision_function",
            "formula": "deviation_score = clip(50.0 - (raw_decision_score * 160.0), 0.0, 100.0)",
            "range": "0-100",
            "interpretation": "lower=closer to baseline, higher=greater behavioural deviation"
        },
        "thresholds": {
            "status": "PROVISIONAL_SYNTHETIC_THRESHOLDS",
            "NORMAL_PATTERN_max": 45.0,
            "WATCH_DEVIATION_min": 45.0,
            "WATCH_DEVIATION_max": 70.0,
            "HIGH_DEVIATION_min": 70.0
        },
        "score_persistence": {
            "score_history_length": 5,
            "smoothing_method": "exponential_moving_average",
            "smoothing_alpha": 0.35,
            "decay_rate_per_normal_window": 0.25
        }
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)
    print(f"Saved camera anomaly configuration: {config_path}")

if __name__ == "__main__":
    train_and_save()
