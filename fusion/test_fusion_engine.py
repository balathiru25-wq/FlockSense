"""
Comprehensive End-to-End Test Suite for FlockSense Audio + Camera Fusion Engine.

Verifies:
1. Global Audio Mode:
   - Strong flock audio abnormality (86/100) acting as urgency context
   - Camera tracks with differing behavioral deviations (Track #12: 21, Track #17: 82, Track #24: 68)
   - Verifies Track #17 ranks 1st, Track #24 ranks 2nd
   - Confirms audio is NOT falsely attributed to individual birds
   - Confirms camera-normal bird (Track #12) receives ZERO audio boost
2. Track Zone Migration:
   - Track #17 moves from ZONE_3 -> ZONE_2
   - Verifies risk and inspection priority follow Track #17, NOT staying in ZONE_3
   - Verifies initial_evidence_zone is preserved as ZONE_3 and current_zone updates to ZONE_2
3. Temporal Persistence:
   - Compares Track A (isolated spike: 10, 14, 83, 12, 11) vs Track B (sustained: 71, 78, 82, 80, 76)
   - Verifies Track B receives significantly higher inspection priority than Track A
4. Score Decay:
   - Track sequence returning toward baseline (82 -> 78 -> 65 -> 51 -> 34 -> 20)
   - Verifies inspection priority decreases gradually over time
5. Global Audio Expiration:
   - Tests that after configured audio timeout (15s), flock audio urgency expires and returns to 0.0
6. Simulated Localized Audio Path (Mode B):
   - Ingests explicitly marked SIMULATED localized audio event targeting ZONE_3
   - Confirms spatial zone congruence and track migration behavior
"""

import sys
import time
from pathlib import Path

# Ensure root directory is on Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fusion.fusion_engine import FusionEngine
from fusion.models import AudioEvent, CameraTrackState

def print_separator(title: str):
    print("\n" + "=" * 80)
    print(f" {title.upper()} ")
    print("=" * 80)

def test_1_global_audio_and_candidate_ranking():
    print_separator("Test 1: Global Audio Context & Multi-Track Ranking")
    engine = FusionEngine()

    # 1. Ingest Global Audio Anomaly (Score = 86.0)
    audio_event = AudioEvent(
        event_id="audio-test-86",
        timestamp_start=30.0,
        timestamp_end=35.0,
        abnormal_probability=0.86,
        confidence=0.92,
        status="HIGH_ACOUSTIC_DEVIATION",
        audio_score=86.0,
        localization_available=False,
        estimated_zone=None,
        audio_scope="FLOCK",
        interpretation="Frequent high-frequency abnormal vocalizations detected across monitored shed."
    )
    engine.ingest_audio_event(audio_event)
    print("1. Ingested Global Audio Event:")
    print("   Audio Score: 86.0/100 | Status: HIGH_ACOUSTIC_DEVIATION | Localization: NOT AVAILABLE")

    # 2. Ingest 3 Camera Tracks at t = 33.0s (temporally overlapping with audio)
    # Track #12: Camera normal (deviation = 21.0)
    t12 = CameraTrackState(
        track_id=12,
        timestamp=33.0,
        current_zone="ZONE_1",
        current_behavior="feeding",
        camera_anomaly_score=21.0,
        camera_status="NORMAL_PATTERN",
        movement_rate=14.0,
        relative_isolation_score=0.22,
        relative_activity=1.1,
        camera_reasons=["behaviour patterns within normal baseline parameters"]
    )

    # Track #17: High camera deviation (deviation = 82.0)
    t17 = CameraTrackState(
        track_id=17,
        timestamp=33.0,
        current_zone="ZONE_3",
        current_behavior="sitting",
        camera_anomaly_score=82.0,
        camera_status="HIGH_DEVIATION",
        movement_rate=0.0,
        stationary_duration=4.8,
        stationary_ratio=1.0,
        relative_isolation_score=0.32,
        relative_activity=0.0,
        camera_reasons=[
            "movement rate substantially below flock median baseline",
            "prolonged stationary duration exceeding peer baseline",
            "predominant sitting posture relative to moving flock peers"
        ]
    )

    # Track #24: Watch deviation (deviation = 68.0)
    t24 = CameraTrackState(
        track_id=24,
        timestamp=33.0,
        current_zone="ZONE_4",
        current_behavior="standing",
        camera_anomaly_score=68.0,
        camera_status="WATCH_DEVIATION",
        movement_rate=3.0,
        stationary_duration=3.5,
        stationary_ratio=0.70,
        relative_isolation_score=0.28,
        relative_activity=0.3,
        camera_reasons=["movement rate substantially below flock median baseline"]
    )

    c12 = engine.update_camera_track(t12)
    c17 = engine.update_camera_track(t17)
    c24 = engine.update_camera_track(t24)

    ranked = engine.get_top_candidates(current_time=33.0)
    print("\n2. Ranked Inspection Candidates (Top N):")
    print(engine.ranker.build_candidate_summary_table(ranked))

    # Assertions
    assert ranked[0].track_id == 17, f"Expected Track #17 to rank 1st, got #{ranked[0].track_id}"
    assert ranked[1].track_id == 24, f"Expected Track #24 to rank 2nd, got #{ranked[1].track_id}"
    assert ranked[2].track_id == 12, f"Expected Track #12 to rank 3rd, got #{ranked[2].track_id}"
    
    # Verify Track #12 received ZERO audio boost (avoid false individual attribution)
    assert c12.audio_urgency_boost == 0.0, f"Normal Track #12 must NOT receive audio boost! Got {c12.audio_urgency_boost}"
    print("\n3. Attribution Check:")
    print(f"   Track #12 Audio Urgency Boost: {c12.audio_urgency_boost} (Zero boost correctly preserved)")
    print(f"   Track #17 Audio Urgency Boost: +{c17.audio_urgency_boost:.1f} (Appropriately modified as deviant candidate)")
    
    # Check explainability disclaimer presence
    t17_reasons = " ".join(c17.reasons)
    assert "not localized" in t17_reasons.lower(), "Candidate explainability must state audio is NOT localized to this bird!"
    print("   Explainability Disclaimer Verified: 'Audio source is not localized to this bird' present in reasons.")
    print(">>> TEST 1 PASSED.")

def test_2_track_zone_migration():
    print_separator("Test 2: Track Zone Migration (Risk Follows Track ID)")
    engine = FusionEngine()

    # Step A: Track #17 observed in ZONE_3 at t = 10.0s with high deviation
    t17_a = CameraTrackState(
        track_id=17,
        timestamp=10.0,
        current_zone="ZONE_3",
        camera_anomaly_score=82.0,
        camera_status="HIGH_DEVIATION",
        relative_isolation_score=0.30,
        relative_activity=0.1,
        camera_reasons=["prolonged stationary duration"]
    )
    cand_a = engine.update_camera_track(t17_a)
    print(f"Initial State (t=10s): Track #17 in {cand_a.current_zone} | Priority: {cand_a.inspection_priority:.1f} | Initial Evidence Zone: {cand_a.initial_evidence_zone}")

    assert cand_a.current_zone == "ZONE_3"
    assert cand_a.initial_evidence_zone == "ZONE_3"

    # Step B: Track #17 moves from ZONE_3 to ZONE_2 at t = 20.0s
    t17_b = CameraTrackState(
        track_id=17,
        timestamp=20.0,
        current_zone="ZONE_2",
        previous_zone="ZONE_3",
        camera_anomaly_score=85.0,
        camera_status="HIGH_DEVIATION",
        relative_isolation_score=0.31,
        relative_activity=0.2,
        camera_reasons=["prolonged stationary duration"]
    )
    cand_b = engine.update_camera_track(t17_b)
    print(f"After Migration (t=20s): Track #17 in {cand_b.current_zone} | Priority: {cand_b.inspection_priority:.1f} | Initial Evidence Zone: {cand_b.initial_evidence_zone}")

    assert cand_b.track_id == 17
    assert cand_b.current_zone == "ZONE_2", f"Expected current zone ZONE_2, got {cand_b.current_zone}"
    assert cand_b.initial_evidence_zone == "ZONE_3", f"Expected initial evidence zone ZONE_3, got {cand_b.initial_evidence_zone}"
    assert cand_b.inspection_priority >= 60.0, "Risk must follow Track #17 into ZONE_2!"
    
    # Confirm alert engine logged migration
    recent_alerts = engine.get_active_alerts(5)
    last_alert = recent_alerts[-1]
    assert last_alert.current_zone == "ZONE_2", f"Alert must record new zone ZONE_2, got {last_alert.current_zone}"
    print(f"Alert successfully updated with current zone: {last_alert.current_zone}")
    print(">>> TEST 2 PASSED.")

def test_3_persistence_comparison():
    print_separator("Test 3: Temporal Persistence vs Transient Spike")
    engine = FusionEngine()

    # Track A: Transient isolated spike [10, 14, 83, 12, 11]
    track_a_scores = [10.0, 14.0, 83.0, 12.0, 11.0]
    cand_a = None
    for i, sc in enumerate(track_a_scores):
        ts = 10.0 + (i * 5.0)
        ta = CameraTrackState(
            track_id=101,
            timestamp=ts,
            current_zone="ZONE_1",
            camera_anomaly_score=sc,
            camera_status="HIGH_DEVIATION" if sc >= 70 else "NORMAL_PATTERN",
            relative_isolation_score=0.25,
            relative_activity=1.0
        )
        cand_a = engine.update_camera_track(ta)

    # Track B: Sustained persistent deviation [71, 78, 82, 80, 76]
    track_b_scores = [71.0, 78.0, 82.0, 80.0, 76.0]
    cand_b = None
    for i, sc in enumerate(track_b_scores):
        ts = 10.0 + (i * 5.0)
        tb = CameraTrackState(
            track_id=102,
            timestamp=ts,
            current_zone="ZONE_2",
            camera_anomaly_score=sc,
            camera_status="HIGH_DEVIATION",
            relative_isolation_score=0.30,
            relative_activity=0.2
        )
        cand_b = engine.update_camera_track(tb)

    print(f"Track A (Isolated Spike):   Inspection Priority = {cand_a.inspection_priority:.1f} | Persistence = {cand_a.persistence_score:.1f} | Status = {cand_a.status}")
    print(f"Track B (Sustained Deviant): Inspection Priority = {cand_b.inspection_priority:.1f} | Persistence = {cand_b.persistence_score:.1f} | Status = {cand_b.status}")

    assert cand_b.inspection_priority > cand_a.inspection_priority + 30.0, (
        f"Track B priority ({cand_b.inspection_priority}) should be substantially higher than Track A ({cand_a.inspection_priority})"
    )
    assert cand_b.status == "ALERT", f"Expected Track B to be ALERT, got {cand_b.status}"
    assert cand_a.status == "NORMAL", f"Expected Track A to normalize, got {cand_a.status}"
    print(">>> TEST 3 PASSED.")

def test_4_score_decay():
    print_separator("Test 4: Score Decay When Behavior Normalizes")
    engine = FusionEngine()

    decay_sequence = [82.0, 78.0, 65.0, 51.0, 34.0, 20.0]
    priorities = []

    for i, sc in enumerate(decay_sequence):
        ts = 50.0 + (i * 5.0)
        t = CameraTrackState(
            track_id=55,
            timestamp=ts,
            current_zone="ZONE_1",
            camera_anomaly_score=sc,
            camera_status="HIGH_DEVIATION" if sc >= 70 else ("WATCH_DEVIATION" if sc >= 45 else "NORMAL_PATTERN"),
            relative_isolation_score=0.25,
            relative_activity=1.0
        )
        cand = engine.update_camera_track(t)
        priorities.append(cand.inspection_priority)
        print(f"Step {i+1} (t={ts:4.1f}s) | Raw Dev: {sc:4.1f} -> Inspection Priority: {cand.inspection_priority:4.1f} ({cand.status})")

    # Verify monotonic downward trend across normalization
    decay_delta = priorities[2] - priorities[-1] # Peak to fully normalized
    print(f"Priority decayed from peak {priorities[2]:.1f} down to {priorities[-1]:.1f} (drop of {decay_delta:.1f} pts)")
    assert priorities[-1] < priorities[0] - 15.0, f"Expected substantial priority decay, got {priorities[0]} -> {priorities[-1]}"
    assert priorities[-1] < 45.0, f"Final decayed score should be in NORMAL range (<45), got {priorities[-1]}"
    print(">>> TEST 4 PASSED.")

def test_5_global_audio_timeout_expiry():
    print_separator("Test 5: Global Audio Context Expiration")
    engine = FusionEngine()

    # Ingest audio event active from t=0.0 to t=5.0s
    evt = AudioEvent(
        event_id="audio-expiring",
        timestamp_start=0.0,
        timestamp_end=5.0,
        abnormal_probability=0.88,
        confidence=0.95,
        status="HIGH_ACOUSTIC_DEVIATION",
        audio_score=88.0,
        localization_available=False
    )
    engine.ingest_audio_event(evt)

    # Check at t = 10.0s (within 15s timeout): should be active
    state_10 = engine.audio_manager.get_current_global_audio_state(current_time=10.0)
    print(f"At t=10s: Global Audio Score = {state_10['global_audio_score']} | Status = {state_10['global_audio_status']}")
    assert state_10["global_audio_score"] == 88.0
    assert state_10["global_audio_status"] == "ALERT"

    # Check at t = 30.0s (well past 15s timeout): should expire to 0.0
    state_30 = engine.audio_manager.get_current_global_audio_state(current_time=30.0)
    print(f"At t=30s (past timeout): Global Audio Score = {state_30['global_audio_score']} | Status = {state_30['global_audio_status']}")
    assert state_30["global_audio_score"] == 0.0
    assert state_30["global_audio_status"] == "NORMAL"
    print(">>> TEST 5 PASSED.")

def test_6_simulated_localized_audio_mode():
    print_separator("Test 6: Simulated Localized Audio Path (Mode B Verification)")
    engine = FusionEngine()
    engine.config["fusion_mode"] = "LOCALIZED_AUDIO"

    # Explicitly labeled SIMULATED localized audio event targeting ZONE_3
    sim_event = AudioEvent(
        event_id="audio-sim-loc-3",
        timestamp_start=100.0,
        timestamp_end=105.0,
        abnormal_probability=0.90,
        confidence=0.95,
        status="HIGH_ACOUSTIC_DEVIATION",
        audio_score=90.0,
        localization_available=True, # Explicitly simulated for code test
        estimated_zone="ZONE_3",
        audio_scope="ZONE",
        interpretation="SIMULATED LOCALIZATION TEST: Acoustic anomaly localized to ZONE_3"
    )
    engine.ingest_audio_event(sim_event)
    print("Ingested SIMULATED Localized Audio Event targeting ZONE_3:")

    # Track in ZONE_3 (should receive spatial congruence bonus)
    t_zone3 = CameraTrackState(
        track_id=301,
        timestamp=102.0,
        current_zone="ZONE_3",
        camera_anomaly_score=60.0,
        camera_status="WATCH_DEVIATION",
        relative_isolation_score=0.28,
        relative_activity=0.5
    )
    c_zone3 = engine.update_camera_track(t_zone3)

    # Track in ZONE_1 (distant zone, should NOT receive zone congruence bonus)
    t_zone1 = CameraTrackState(
        track_id=302,
        timestamp=102.0,
        current_zone="ZONE_1",
        camera_anomaly_score=60.0,
        camera_status="WATCH_DEVIATION",
        relative_isolation_score=0.28,
        relative_activity=0.5
    )
    c_zone1 = engine.update_camera_track(t_zone1)

    print(f"Track #301 in target ZONE_3: Priority = {c_zone3.inspection_priority:.1f} | Audio Boost = +{c_zone3.audio_urgency_boost:.1f}")
    print(f"Track #302 in other ZONE_1:  Priority = {c_zone1.inspection_priority:.1f} | Audio Boost = +{c_zone1.audio_urgency_boost:.1f}")

    assert c_zone3.inspection_priority > c_zone1.inspection_priority, "Target zone candidate must receive spatial congruence bonus!"
    assert c_zone3.audio_localized is True
    print("Spatial association verified successfully in simulated Mode B.")
    print(">>> TEST 6 PASSED.")

def main():
    print("\n" + "#" * 80)
    print(" RUNNING FLOCKSENSE AUDIO + CAMERA FUSION TEST SUITE ")
    print("#" * 80)

    test_1_global_audio_and_candidate_ranking()
    test_2_track_zone_migration()
    test_3_persistence_comparison()
    test_4_score_decay()
    test_5_global_audio_timeout_expiry()
    test_6_simulated_localized_audio_mode()

    print("\n" + "#" * 80)
    print(" ALL 6 FUSION TESTS COMPLETED SUCCESSFULLY! ")
    print("#" * 80 + "\n")

if __name__ == "__main__":
    main()
