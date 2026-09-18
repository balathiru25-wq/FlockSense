"""
Inference & Synthetic Stress Testing for FlockSense Camera Anomaly Detection.

Tests:
1. Evaluation on genuine extracted feature rows from bird_behavior_features.csv.
2. Synthetic software stress tests verifying model deviation scoring logic:
   - Case A: Very low movement, very high stationary ratio (lethargy-like archetype)
   - Case B: High spatial isolation, low relative activity (isolated perimeter bird)
   - Case C: Normal baseline-conforming values (active peer)
3. Rolling score persistence and smoothing test (isolated spike rejection).
4. Score decay test (gradual normalization when returning to normal baseline).

IMPORTANT:
- Validation Status: PROTOTYPE_ONLY_SYNTHETIC_DATA
- Real-World Validated: NO
- Clinical / Disease Diagnoses: NONE
"""

import csv
import json
from pathlib import Path
from vision.camera_anomaly_model import CameraAnomalyDetector
from vision.track_state import TrackState

def test_existing_csv_rows(detector: CameraAnomalyDetector):
    print("\n" + "=" * 75)
    print("1. EVALUATION ON EXTRACTED FEATURE CSV ROWS")
    print("=" * 75)

    csv_path = Path("outputs/vision/features/bird_behavior_features.csv")
    if not csv_path.exists():
        print(f"Error: {csv_path} not found.")
        return

    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"Loaded {len(rows)} track window rows from {csv_path}:\n")
    print(f"{'Track ID':<10} | {'Move Rate':<10} | {'Stat Ratio':<11} | {'Behaviors':<22} | {'Isolation':<10} | {'Dev Score':<10} | {'Status':<16} | {'Reasons'}")
    print("-" * 125)

    for r in rows:
        tid = r.get("track_id", "?")
        m_rate = float(r.get("movement_rate", 0.0))
        s_ratio = float(r.get("stationary_ratio", 0.0))
        stand_r = float(r.get("standing_ratio", 0.0))
        feed_r = float(r.get("feeding_ratio", 0.0))
        sit_r = float(r.get("sitting_ratio", 0.0))
        preen_r = float(r.get("preening_ratio", 0.0))
        iso_score = float(r.get("relative_isolation_score", 0.0))

        # Build behavior summary string
        beh_items = []
        if feed_r > 0: beh_items.append(f"feed:{feed_r:.1f}")
        if stand_r > 0: beh_items.append(f"stand:{stand_r:.1f}")
        if sit_r > 0: beh_items.append(f"sit:{sit_r:.1f}")
        if preen_r > 0: beh_items.append(f"preen:{preen_r:.1f}")
        beh_summary = ", ".join(beh_items)

        # Run inference
        res = detector.predict_camera_anomaly(r)
        score = res["camera_deviation_score"]
        status = res["status"]
        reasons = "; ".join(res["reasons"])

        print(f"{tid:<10} | {m_rate:<10.1f} | {s_ratio:<11.2f} | {beh_summary:<22} | {iso_score:<10.3f} | {score:<10.1f} | {status:<16} | {reasons}")

def test_synthetic_stress_cases(detector: CameraAnomalyDetector):
    print("\n" + "=" * 75)
    print("2. SYNTHETIC SOFTWARE STRESS TESTS (LOGIC VERIFICATION)")
    print("=" * 75)

    # Case A: Very low movement, very high stationary duration & ratio, prolonged sitting, zero feeding
    case_a = {
        "movement_rate": 0.0,
        "movement_variance": 0.0,
        "distance_travelled_pixels": 0.0,
        "stationary_duration": 4.9,
        "stationary_ratio": 1.0,
        "standing_ratio": 0.0,
        "feeding_ratio": 0.0,
        "sitting_ratio": 0.95,
        "spreading_ratio": 0.0,
        "preening_ratio": 0.05,
        "resting_ratio": 0.0,
        "walking_ratio": 0.0,
        "behaviour_transition_rate": 0.0,
        "distance_to_nearest_bird": 280.0,
        "distance_to_flock_centroid": 190.0,
        "relative_isolation_score": 0.25,
        "relative_activity": 0.0,
        "zone_transition_count": 0
    }

    # Case B: High spatial isolation, low relative activity, distant from flock cluster
    case_b = {
        "movement_rate": 4.0,
        "movement_variance": 5.0,
        "distance_travelled_pixels": 20.0,
        "stationary_duration": 3.8,
        "stationary_ratio": 0.75,
        "standing_ratio": 0.70,
        "feeding_ratio": 0.0,
        "sitting_ratio": 0.10,
        "spreading_ratio": 0.0,
        "preening_ratio": 0.20,
        "resting_ratio": 0.0,
        "walking_ratio": 0.0,
        "behaviour_transition_rate": 0.1,
        "distance_to_nearest_bird": 480.0,
        "distance_to_flock_centroid": 390.0,
        "relative_isolation_score": 0.52,
        "relative_activity": 0.25,
        "zone_transition_count": 0
    }

    # Case C: Normal-like baseline values (active feeding / standing, cohesive flock position)
    case_c = {
        "movement_rate": 18.0,
        "movement_variance": 45.0,
        "distance_travelled_pixels": 95.0,
        "stationary_duration": 2.5,
        "stationary_ratio": 0.50,
        "standing_ratio": 0.40,
        "feeding_ratio": 0.40,
        "sitting_ratio": 0.10,
        "spreading_ratio": 0.0,
        "preening_ratio": 0.10,
        "resting_ratio": 0.0,
        "walking_ratio": 0.0,
        "behaviour_transition_rate": 0.15,
        "distance_to_nearest_bird": 275.0,
        "distance_to_flock_centroid": 180.0,
        "relative_isolation_score": 0.25,
        "relative_activity": 1.1,
        "zone_transition_count": 0
    }

    cases = [
        ("CASE A (Hypoactive / Prolonged Stationary)", case_a),
        ("CASE B (Peripheral Social Isolation)", case_b),
        ("CASE C (Normal Flock Baseline Activity)", case_c)
    ]

    results = {}
    for label, feat in cases:
        res = detector.predict_camera_anomaly(feat)
        results[label] = res
        print(f"\n>>> {label}")
        print(f"    Raw Anomaly Decision Score: {res['raw_anomaly_score']}")
        print(f"    Camera Behaviour Deviation: {res['camera_deviation_score']} / 100")
        print(f"    Status:                     {res['status']}")
        print(f"    Explainability Reasons:     {res['reasons']}")

    score_a = results["CASE A (Hypoactive / Prolonged Stationary)"]["camera_deviation_score"]
    score_b = results["CASE B (Peripheral Social Isolation)"]["camera_deviation_score"]
    score_c = results["CASE C (Normal Flock Baseline Activity)"]["camera_deviation_score"]

    print("\n-----------------------------------------------------------")
    print(f"LOGIC SANITY CHECK: Case A ({score_a}) & Case B ({score_b}) vs Case C ({score_c})")
    assert score_a > score_c, f"Case A score ({score_a}) expected to be > Case C ({score_c})"
    assert score_b > score_c, f"Case B score ({score_b}) expected to be > Case C ({score_c})"
    print("SUCCESS: Deviant behavioral profiles scored strictly higher than baseline-conforming profile.")

def test_score_persistence_and_decay(detector: CameraAnomalyDetector):
    print("\n" + "=" * 75)
    print("3. SCORE PERSISTENCE & DECAY SIMULATION (TrackState)")
    print("=" * 75)

    track = TrackState(
        track_id=17,
        initial_bbox=[100, 100, 150, 150],
        initial_zone="ZONE_1",
        timestamp=0.0
    )

    # Test 1: Isolated spike rejection
    print("--- Test 1: Isolated Spike Rejection on Track #17 ---")
    sequence_1 = [12.0, 14.0, 88.0, 13.0, 11.0]
    for i, raw_dev in enumerate(sequence_1):
        ts = float(i * 5.0)
        track.update_camera_anomaly(
            deviation_score=raw_dev,
            status="HIGH_DEVIATION" if raw_dev >= 70 else "NORMAL_PATTERN",
            reasons=["test reason"],
            timestamp=ts,
            raw_anomaly_score=-0.2 if raw_dev >= 70 else 0.05
        )
        print(f"Window {i+1} (t={ts:4.1f}s) | Raw Input: {raw_dev:4.1f} -> Smoothed Score: {track.camera_anomaly_score:4.1f} | Status: {track.camera_anomaly_status}")

    assert track.camera_anomaly_status != "HIGH_DEVIATION", "Single isolated spike should NOT trigger persistent HIGH_DEVIATION!"
    print("PASS: Single isolated spike of 88.0 was smoothed and did not cause persistent HIGH_DEVIATION.")

    # Test 2: Persistent high deviation
    print("\n--- Test 2: Persistent High Deviation ---")
    track_persistent = TrackState(track_id=22, initial_bbox=[200, 200, 260, 260], initial_zone="ZONE_3", timestamp=0.0)
    sequence_2 = [74.0, 81.0, 79.0, 76.0, 82.0]
    for i, raw_dev in enumerate(sequence_2):
        ts = float(i * 5.0)
        track_persistent.update_camera_anomaly(
            deviation_score=raw_dev,
            status="HIGH_DEVIATION",
            reasons=["movement below synthetic baseline"],
            timestamp=ts,
            raw_anomaly_score=-0.22
        )
        print(f"Window {i+1} (t={ts:4.1f}s) | Raw Input: {raw_dev:4.1f} -> Smoothed Score: {track_persistent.camera_anomaly_score:4.1f} | Status: {track_persistent.camera_anomaly_status}")

    assert track_persistent.camera_anomaly_status == "HIGH_DEVIATION", "Persistent deviations must maintain HIGH_DEVIATION!"
    print("PASS: Persistent deviation inputs maintained HIGH_DEVIATION.")

    # Test 3: Gradual score decay when returning to baseline
    print("\n--- Test 3: Score Decay When Behaviour Returns to Baseline ---")
    sequence_3 = [80.0, 78.0, 72.0, 55.0, 39.0, 24.0]
    for i, raw_dev in enumerate(sequence_3):
        ts = float((len(sequence_2) + i) * 5.0)
        track_persistent.update_camera_anomaly(
            deviation_score=raw_dev,
            status="HIGH_DEVIATION" if raw_dev >= 70 else ("WATCH_DEVIATION" if raw_dev >= 45 else "NORMAL_PATTERN"),
            reasons=["recovering"],
            timestamp=ts,
            raw_anomaly_score=-0.15 if raw_dev >= 70 else 0.05
        )
        print(f"Decay Step {i+1} (t={ts:4.1f}s) | Raw Input: {raw_dev:4.1f} -> Smoothed Score: {track_persistent.camera_anomaly_score:4.1f} | Status: {track_persistent.camera_anomaly_status}")

    assert track_persistent.camera_anomaly_status != "HIGH_DEVIATION", "Score decay must transition away from HIGH_DEVIATION when behaviour normalizes!"
    print("PASS: Score decayed smoothly and normalized back to lower deviation status.")

if __name__ == "__main__":
    detector = CameraAnomalyDetector()
    test_existing_csv_rows(detector)
    test_synthetic_stress_cases(detector)
    test_score_persistence_and_decay(detector)
    print("\n" + "=" * 75)
    print("ALL TESTS COMPLETED SUCCESSFULLY (PROTOTYPE ONLY - SYNTHETIC DATA)")
    print("=" * 75)
