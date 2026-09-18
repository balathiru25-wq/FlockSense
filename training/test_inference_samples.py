import os
import sys
import csv
from pathlib import Path

_current_dir = Path(__file__).resolve().parent
_root_dir = _current_dir.parent
for p in [str(_current_dir), str(_root_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from audio_inference import FlockSenseAudioInference

def verify_test_samples():
    project_root = Path(".").resolve()
    inference_pipeline = FlockSenseAudioInference(
        checkpoint_path=project_root / "models" / "audio_model_best.pth"
    )

    with open(project_root / "splits" / "test.csv", "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    samples_to_test = [
        ("Healthy (Long flock recording, 39.8s)", [r for r in rows if r["label"] == "Healthy"][0]),
        ("Unhealthy (Isolated sneeze/rale event, 1.18s)", [r for r in rows if r["label"] == "Unhealthy" and float(r["duration_seconds"]) < 2.0][0]),
        ("Unhealthy (Continuous flock recording, 22.6s)", [r for r in rows if r["label"] == "Unhealthy" and float(r["duration_seconds"]) > 20.0][0]),
        ("Noise (Farm shed equipment / background, 14.2s)", [r for r in rows if r["label"] == "Noise"][0]),
    ]

    print("=" * 70)
    print("VERIFYING INFERENCE PIPELINE ON GENUINE HELD-OUT TEST RECORDINGS")
    print("=" * 70)

    for desc, r in samples_to_test:
        fpath = project_root / r["filepath"]
        print(f"\n>>> Running analysis on: {desc}")
        print(f"    File: {r['filename']} (Group: {r['group_id']}, True Label: {r['label']})")
        res = inference_pipeline.analyze_audio_file(fpath)
        inference_pipeline.print_report(res)

if __name__ == "__main__":
    verify_test_samples()
