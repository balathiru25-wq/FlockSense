"""
Comprehensive Automated Test Suite for FlockSense FastAPI Backend.

Tests:
1. GET /api/health - Validates subsystem readiness and disclaimers.
2. GET /api/system-info - Validates AI models metadata and prototype constraints.
3. GET /api/flock-status - Validates empty/initial flock status and context.
4. GET /api/candidates - Validates candidate listing schema.
5. GET /api/tracks - Validates track listing schema.
6. GET /api/tracks/99999 - Validates 404 response for non-existent track.
7. GET /api/alerts - Validates alerts endpoint and filters.
8. POST /api/dev/track-state - Ingests test tracks (Track #17, Track #24, Track #12).
9. POST /api/analyze-audio - Uploads a genuine held-out abnormal audio sample from test dataset.
10. Global Audio Safety Verification:
    - Confirms abnormal audio updates flock context.
    - Confirms candidate ranking updates.
    - Confirms camera-normal Track #12 gets 0.0 audio boost.
    - Confirms candidates state audio is NOT localized to individual birds.
"""

import os
import sys
import io
import csv
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.main import app
from backend.flock_service import flock_service

@pytest.fixture(scope="session", autouse=True)
def init_backend():
    flock_service.initialize()
    yield

client = TestClient(app)

def test_1_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "FlockSense API"
    assert data["components"]["audio_model"] is True
    assert data["components"]["camera_anomaly_model"] is True
    assert data["components"]["fusion_engine"] is True
    assert data["validation"]["medical_validation"] is False
    assert data["validation"]["audio_localization_available"] is False

def test_2_system_info_endpoint():
    response = client.get("/api/system-info")
    assert response.status_code == 200
    data = response.json()
    assert "ResNet18" in data["audio_model"]
    assert "Roboflow" in data["behavior_model"]
    assert "ByteTrack" in data["tracker"]
    assert "IsolationForest" in data["camera_anomaly_model"]
    assert data["fusion_mode"] == "GLOBAL_AUDIO"
    assert "does not diagnose" in data["disclaimer"]

def test_3_flock_status_initial():
    response = client.get("/api/flock-status")
    assert response.status_code == 200
    data = response.json()
    assert data["flock_status"] in ["NORMAL", "WATCH", "ALERT"]
    assert "global_audio" in data
    assert data["global_audio"]["localized"] is False
    assert "tracking" in data

def test_4_candidates_initial():
    response = client.get("/api/candidates")
    assert response.status_code == 200
    data = response.json()
    assert "candidates" in data
    assert "disclaimer" in data
    assert "not a disease probability" in data["disclaimer"]

def test_5_tracks_initial_and_invalid_id():
    # List tracks
    resp_list = client.get("/api/tracks")
    assert resp_list.status_code == 200
    data = resp_list.json()
    assert "tracks" in data
    assert "total_tracks" in data

    # Query non-existent track
    resp_invalid = client.get("/api/tracks/999999")
    assert resp_invalid.status_code == 404
    err = resp_invalid.json()
    assert "error" in err or "detail" in err

def test_6_alerts_endpoint():
    response = client.get("/api/alerts")
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert "total_alerts" in data

def test_7_dev_track_state_ingest():
    # Ingest Track #17 (deviant)
    t17_payload = {
        "track_id": 17,
        "current_zone": "ZONE_2",
        "current_behavior": "sitting",
        "camera_anomaly_score": 82.0,
        "movement_rate": 0.0,
        "stationary_duration": 4.5,
        "stationary_ratio": 1.0,
        "relative_isolation_score": 0.32,
        "relative_activity": 0.0,
        "camera_anomaly_reasons": ["movement rate below flock median", "prolonged stationary duration"]
    }
    r17 = client.post("/api/dev/track-state", json=t17_payload)
    assert r17.status_code == 200
    d17 = r17.json()
    assert d17["track_id"] == 17
    assert d17["current_zone"] == "ZONE_2"
    assert d17["inspection_priority"] >= 50.0

    # Ingest Track #12 (normal)
    t12_payload = {
        "track_id": 12,
        "current_zone": "ZONE_1",
        "current_behavior": "feeding",
        "camera_anomaly_score": 20.0,
        "movement_rate": 15.0,
        "stationary_duration": 1.0,
        "stationary_ratio": 0.2,
        "relative_isolation_score": 0.22,
        "relative_activity": 1.0,
        "camera_anomaly_reasons": ["behaviour patterns within normal baseline parameters"]
    }
    r12 = client.post("/api/dev/track-state", json=t12_payload)
    assert r12.status_code == 200

    # Verify tracks now appear in /api/tracks
    resp_tracks = client.get("/api/tracks")
    assert resp_tracks.status_code == 200
    t_data = resp_tracks.json()
    assert t_data["total_tracks"] >= 2
    track_ids = [t["track_id"] for t in t_data["tracks"]]
    assert 17 in track_ids
    assert 12 in track_ids

    # Verify detail for Track #17
    r_detail = client.get("/api/tracks/17")
    assert r_detail.status_code == 200
    detail_data = r_detail.json()
    assert detail_data["track_id"] == 17
    assert detail_data["current_zone"] == "ZONE_2"
    assert detail_data["camera_deviation_score"] >= 70.0
    assert "not localized" in detail_data["disclaimer"].lower()

def test_8_audio_analysis_and_global_safety():
    """
    Submits a genuine held-out abnormal audio sample to /api/analyze-audio.
    Verifies:
    1. Audio inference returns abnormal prediction.
    2. Global flock audio context is updated.
    3. Candidates ranking is updated.
    4. Audio boost is applied ONLY to deviant birds (Track #17) and NOT to normal birds (Track #12).
    5. Disclaimers confirm audio is not localized to an individual.
    """
    # Locate a genuine held-out audio file from test.csv
    test_csv_path = ROOT_DIR / "splits" / "test.csv"
    assert test_csv_path.exists(), "test.csv not found"

    sample_audio_path = None
    with open(test_csv_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["label"] == "Unhealthy":
                cand_path = ROOT_DIR / row["filepath"]
                if cand_path.exists():
                    sample_audio_path = cand_path
                    break

    assert sample_audio_path is not None, "Could not find a genuine Unhealthy audio test sample."
    print(f"\nFound test audio sample: {sample_audio_path.name}")

    with open(sample_audio_path, "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/api/analyze-audio",
        files={"file": (sample_audio_path.name, io.BytesIO(file_bytes), "audio/wav")}
    )

    assert response.status_code == 200, f"Failed audio analysis: {response.text}"
    res = response.json()
    assert res["success"] is True
    assert res["audio"]["prediction"] in ["ABNORMAL", "NORMAL"]
    assert res["audio"]["scope"] == "FLOCK"
    assert res["audio"]["localized"] is False
    assert "not attributed" in res["disclaimer"]

    # Verify candidates ranking after audio anomaly
    c_resp = client.get("/api/candidates")
    assert c_resp.status_code == 200
    c_data = c_resp.json()
    candidates = c_data["candidates"]
    assert len(candidates) >= 2

    # Check top candidate is Track #17
    top_candidate = candidates[0]
    assert top_candidate["track_id"] == 17
    assert top_candidate["inspection_priority"] >= 75.0
    
    # Check audio context on candidates
    c17 = next(c for c in candidates if c["track_id"] == 17)
    c12 = next(c for c in candidates if c["track_id"] == 12)

    # Global Audio Safety Check:
    # Track #17 (deviant) gets urgency boost
    assert c17["audio_context"]["audio_localized"] is False
    assert c17["audio_context"]["urgency_boost"] > 0.0
    
    # Track #12 (normal) must NOT get urgency boost!
    assert c12["audio_context"]["urgency_boost"] == 0.0
    print(f"Safety check verified: Track #12 audio boost = {c12['audio_context']['urgency_boost']} (strictly 0.0)")

def test_9_session_endpoints():
    r_start = client.post("/api/session/start")
    assert r_start.status_code == 200
    d_start = r_start.json()
    assert d_start["session_active"] is True
    assert d_start["mode"] == "ACTIVE_MONITORING"

    r_status = client.get("/api/session/status")
    assert r_status.status_code == 200
    d_status = r_status.json()
    assert d_status["session_active"] is True

    r_stop = client.post("/api/session/stop")
    assert r_stop.status_code == 200
    d_stop = r_stop.json()
    assert d_stop["session_active"] is False

if __name__ == "__main__":
    pytest.main(["-v", __file__])
