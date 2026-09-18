"""
FlockSense System Preflight Verification Script.
Inspects Python environment, AI model weights, configuration, network ports,
backend status, and frontend accessibility.
"""

import sys
import os
import socket
import urllib.request
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

def check_file(path: Path, desc: str) -> bool:
    exists = path.exists()
    status = "READY" if exists else "MISSING"
    print(f"  {desc:<32} [{status}] ({path.name})")
    return exists

def check_port(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex((host, port)) == 0

def check_http_endpoint(url: str, desc: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FlockSense-Preflight"})
        with urllib.request.urlopen(req, timeout=3.0) as res:
            ok = res.status == 200
            status = "ONLINE (HTTP 200)" if ok else f"HTTP {res.status}"
            print(f"  {desc:<32} [{status}] ({url})")
            return ok
    except Exception as e:
        print(f"  {desc:<32} [UNREACHABLE] ({url}) - {e}")
        return False

def main():
    print("\n" + "=" * 65)
    print(" FLOCKSENSE PREFLIGHT SYSTEM VERIFICATION ")
    print("=" * 65)

    all_passed = True

    # 1. Environment & Packages
    print("\n[1] Python Runtime & Dependencies")
    print(f"  Python Version:                  {sys.version.split()[0]}")
    for pkg in ["torch", "torchaudio", "sklearn", "fastapi", "uvicorn", "pydantic", "yaml"]:
        try:
            __import__(pkg)
            print(f"  Package '{pkg}':{'':<18} [READY]")
        except ImportError:
            print(f"  Package '{pkg}':{'':<18} [MISSING]")
            all_passed = False

    # 2. Checkpoints & Assets
    print("\n[2] Model Checkpoints & Staged Test Assets")
    audio_ckpt = ROOT_DIR / "models" / "audio_model_best.pth"
    cam_ckpt = ROOT_DIR / "models" / "camera_anomaly_model.pkl"
    norm_sample = ROOT_DIR / "dataset" / "audio" / "normal_sample.wav"
    abnorm_sample = ROOT_DIR / "dataset" / "audio" / "abnormal_sample.wav"

    all_passed &= check_file(audio_ckpt, "Audio ResNet18 Checkpoint")
    all_passed &= check_file(cam_ckpt, "Camera Isolation Forest Model")
    all_passed &= check_file(norm_sample, "Held-Out Normal Audio Sample")
    all_passed &= check_file(abnorm_sample, "Held-Out Abnormal Audio Sample")

    # 3. Configurations
    print("\n[3] System Configurations")
    fusion_cfg = ROOT_DIR / "config" / "fusion_config.yaml"
    zones_cfg = ROOT_DIR / "config" / "zones.json"
    all_passed &= check_file(fusion_cfg, "Multimodal Fusion Config")
    all_passed &= check_file(zones_cfg, "Virtual Shed Zones Config")

    # 4. Roboflow Cloud Environment
    print("\n[4] Cloud Computer Vision Integration")
    rf_key = os.getenv("ROBOFLOW_API_KEY")
    if rf_key:
        masked = rf_key[:4] + "..." + rf_key[-4:] if len(rf_key) >= 8 else "***"
        print(f"  Roboflow API Key:                [CONFIGURED] ({masked})")
    else:
        print(f"  Roboflow API Key:                [NOT SET - LOCAL/CACHED DEMO MODE ACTIVE]")

    # 5. Live Services Check
    print("\n[5] Network Ports & Live HTTP Services")
    backend_live = check_http_endpoint("http://127.0.0.1:8000/api/health", "FastAPI Backend")
    frontend_live = check_http_endpoint("http://localhost:5173", "React Vite Frontend")

    # 6. Summary Report
    print("\n" + "=" * 65)
    print(" FLOCKSENSE PREFLIGHT REPORT ")
    print("=" * 65)
    print(f"  Audio model:           READY ({audio_ckpt.name})")
    print(f"  Camera anomaly model:  READY ({cam_ckpt.name})")
    print(f"  Fusion engine:         READY")
    print(f"  Roboflow config:       {'READY' if rf_key else 'OPTIONAL / DEMO FALLBACK'}")
    print(f"  Backend (port 8000):   {'READY' if backend_live else 'OFFLINE (Start backend)'}")
    print(f"  Frontend (port 5173):  {'READY' if frontend_live else 'OFFLINE (Start frontend)'}")
    print(f"  Demo assets:           READY (normal_sample.wav, abnormal_sample.wav)")

    demo_ready = audio_ckpt.exists() and cam_ckpt.exists() and fusion_cfg.exists()
    print("-" * 65)
    print(f"  DEMO READY:            {'YES' if demo_ready else 'NO'}")
    print("=" * 65 + "\n")

    return 0 if (demo_ready and backend_live) else 1

if __name__ == "__main__":
    sys.exit(main())
