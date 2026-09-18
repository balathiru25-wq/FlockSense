import os
import sys
import time
import json
import csv
import argparse
from pathlib import Path
import yaml
import cv2
import numpy as np

# Ensure local imports work cleanly
_curr = Path(__file__).resolve().parent
_root = _curr.parent
for p in [str(_curr), str(_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from vision.roboflow_behavior_detector import RoboflowBehaviorDetector
    from vision.zone_manager import ZoneManager
    from vision.behavior_history import BehaviorHistoryManager
    from vision.behavior_tracker import BehaviorTracker
    from vision.visualization import VisionVisualizer
except ImportError:
    from roboflow_behavior_detector import RoboflowBehaviorDetector
    from zone_manager import ZoneManager
    from behavior_history import BehaviorHistoryManager
    from behavior_tracker import BehaviorTracker
    from visualization import VisionVisualizer

def load_config(config_path="config/vision_config.yaml"):
    cfg_file = Path(config_path)
    if not cfg_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(cfg_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run_behavior_video(
    source: str,
    config_path: str = "config/vision_config.yaml",
    api_key: str = None,
    output_video: str = None,
    max_frames: int = None,
    mock_api: bool = False
):
    cfg = load_config(config_path)
    
    # 1. Initialize components
    zones_cfg = cfg.get("zones", {}).get("config_file", "config/zones.json")
    zone_mgr = ZoneManager(config_path=zones_cfg)
    history_mgr = BehaviorHistoryManager(
        smoothing_window=cfg.get("behavior_smoothing", {}).get("window_size", 5)
    )

    tracker = BehaviorTracker(
        zone_manager=zone_mgr,
        behavior_history=history_mgr,
        lost_track_buffer=cfg.get("tracking", {}).get("lost_track_buffer", 30),
        frame_rate=cfg.get("tracking", {}).get("frame_rate", 30),
        minimum_matching_threshold=cfg.get("tracking", {}).get("minimum_matching_threshold", 0.80),
        debounce_frames=cfg.get("zones", {}).get("debounce_frames", 3),
        stale_threshold_seconds=cfg.get("behavior_smoothing", {}).get("stale_threshold_seconds", 4.0)
    )

    visualizer = VisionVisualizer(zone_manager=zone_mgr)

    detector = RoboflowBehaviorDetector(
        api_key=api_key,
        max_width=cfg.get("inference_sampling", {}).get("inference_max_width", 960),
        jpeg_quality=cfg.get("inference_sampling", {}).get("jpeg_quality", 75),
        confidence_threshold=cfg.get("roboflow", {}).get("confidence_threshold", 0.30)
    )

    # 2. Open video source
    is_webcam = str(source).isdigit()
    src_input = int(source) if is_webcam else source
    cap = cv2.VideoCapture(src_input)

    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video source: {source}")

    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_src_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print("=" * 70)
    print(" FLOCKSENSE VIDEO BEHAVIOR TRACKING ")
    print("=" * 70)
    print(f"Source:              {source}")
    print(f"Resolution:          {orig_w}x{orig_h}")
    print(f"Source FPS:          {fps:.1f}")
    print(f"Total Video Frames:  {total_src_frames if total_src_frames > 0 else 'Stream'}")
    print(f"Roboflow API Config: {'ONLINE' if detector.is_configured() else 'OFFLINE / UNCONFIGURED'}")
    print(f"Sampling:            Every {cfg.get('inference_sampling', {}).get('behavior_inference_every_n_frames', 10)} frames")
    print("=" * 70)

    # 3. Setup VideoWriter
    out_vid_path = Path(output_video or cfg.get("outputs", {}).get("video_path", "outputs/vision/videos/flocksense_behavior_tracking.mp4"))
    out_vid_path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_vid_path), fourcc, fps, (orig_w, orig_h))

    # 4. Setup Logging
    jsonl_path = Path(cfg.get("outputs", {}).get("tracking_jsonl_path", "outputs/vision/logs/tracking_data.jsonl"))
    events_csv_path = Path(cfg.get("outputs", {}).get("events_csv_path", "outputs/vision/logs/track_events.csv"))
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    events_csv_path.parent.mkdir(parents=True, exist_ok=True)

    jsonl_file = open(jsonl_path, "w", encoding="utf-8")
    
    # 5. Processing Loop
    sample_every_n = cfg.get("inference_sampling", {}).get("behavior_inference_every_n_frames", 10)
    frame_idx = 0
    t_start = time.time()
    last_api_latency = 0.0
    last_api_success = True
    last_predictions = None

    max_simultaneous_tracks = 0
    unique_track_ids = set()

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            frame_idx += 1
            if max_frames and frame_idx > max_frames:
                break

            current_timestamp = frame_idx / fps

            # Decide if this frame runs Roboflow inference
            should_infer = (frame_idx % sample_every_n == 0) or (frame_idx == 1)

            if should_infer:
                if mock_api or not detector.is_configured():
                    # Synthetic/mock detections if no API key is set for offline pipeline verification
                    # Simulates 3 chickens with changing behaviors and crossing from Zone 3 to Zone 2!
                    t_ratio = min(1.0, frame_idx / max(1, total_src_frames if total_src_frames > 0 else 150))
                    
                    # Bird 1: Moves from Zone 3 (top right) -> Zone 2 (top center)
                    # Starts in Zone 3 (x=0.75, y=0.25), moves to Zone 2 (x=0.45, y=0.25)
                    b1_x = (0.75 - 0.30 * t_ratio) * orig_w
                    b1_y = 0.25 * orig_h
                    b1_beh = "sitting" if t_ratio < 0.4 else "standing"

                    # Bird 2: In Zone 5 (bottom center)
                    b2_x = 0.50 * orig_w
                    b2_y = 0.70 * orig_h
                    b2_beh = "feeding"

                    # Bird 3: In Zone 1 (top left)
                    b3_x = 0.20 * orig_w
                    b3_y = 0.30 * orig_h
                    b3_beh = "standing" if t_ratio < 0.6 else "preening"

                    mock_preds = [
                        {
                            "bbox": [b1_x - 45, b1_y - 40, b1_x + 45, b1_y + 40],
                            "center": (b1_x, b1_y),
                            "behavior": b1_beh,
                            "confidence": 0.91
                        },
                        {
                            "bbox": [b2_x - 50, b2_y - 45, b2_x + 50, b2_y + 45],
                            "center": (b2_x, b2_y),
                            "behavior": b2_beh,
                            "confidence": 0.88
                        },
                        {
                            "bbox": [b3_x - 40, b3_y - 35, b3_x + 40, b3_y + 35],
                            "center": (b3_x, b3_y),
                            "behavior": b3_beh,
                            "confidence": 0.84
                        }
                    ]
                    last_predictions = mock_preds
                    last_api_latency = 0.045
                    last_api_success = True
                else:
                    # Genuine Roboflow cloud API inference
                    res = detector.infer_frame(frame)
                    last_api_latency = res["latency_seconds"]
                    last_api_success = res["success"]
                    last_predictions = res["predictions"]
            else:
                # Skipped frame (do not run model, use empty/cached tracker state)
                last_predictions = None

            # Update tracker
            active_tracks = tracker.update(
                roboflow_predictions=last_predictions,
                frame_w=orig_w,
                frame_h=orig_h,
                timestamp=current_timestamp,
                frame_idx=frame_idx
            )

            # Metrics collection
            active_count = sum(1 for t in active_tracks if t.tracking_status in ["ACTIVE", "RECOVERED"])
            if active_count > max_simultaneous_tracks:
                max_simultaneous_tracks = active_count
            for t in active_tracks:
                unique_track_ids.add(t.track_id)

            # Log tracking state to jsonl
            log_record = {
                "timestamp": round(current_timestamp, 3),
                "frame": frame_idx,
                "tracks": [
                    {
                        "track_id": t.track_id,
                        "zone": t.current_zone,
                        "behavior": t.stable_behavior,
                        "behavior_confidence": round(t.behavior_confidence, 3),
                        "behavior_age_seconds": round(max(0.0, current_timestamp - t.last_behavior_timestamp), 2) if t.last_behavior_timestamp > 0 else None,
                        "position": [int(t.center_x), int(t.center_y)],
                        "movement_rate": round(t.movement_rate_pixels_per_second, 1)
                    }
                    for t in active_tracks if t.tracking_status in ["ACTIVE", "RECOVERED"]
                ]
            }
            jsonl_file.write(json.dumps(log_record) + "\n")

            # Render visualization
            annotated = visualizer.draw_zones(frame)
            annotated = visualizer.draw_tracks(annotated, active_tracks)
            elapsed = time.time() - t_start
            proc_fps = frame_idx / max(1e-4, elapsed)
            annotated = visualizer.draw_global_overlay(
                annotated, active_tracks, inference_fps=proc_fps,
                api_latency=last_api_latency, api_success=last_api_success
            )

            writer.write(annotated)

            if frame_idx % 30 == 0 or frame_idx == total_src_frames:
                print(f"  Frame {frame_idx}/{total_src_frames} ({proc_fps:.1f} FPS) | Active Tracks: {active_count} | API: {'OK' if last_api_success else 'FAIL'}")

    finally:
        cap.release()
        writer.release()
        jsonl_file.close()

    # 6. Save Events CSV
    with open(events_csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["timestamp", "frame", "track_id", "event", "previous_zone", "current_zone", "behavior", "behavior_confidence"]
        csv_w = csv.DictWriter(f, fieldnames=fieldnames)
        csv_w.writeheader()
        for ev in tracker.events_log:
            csv_w.writerow({
                "timestamp": ev.get("timestamp"),
                "frame": ev.get("frame"),
                "track_id": ev.get("track_id"),
                "event": ev.get("event"),
                "previous_zone": ev.get("previous_zone"),
                "current_zone": ev.get("current_zone"),
                "behavior": ev.get("behavior"),
                "behavior_confidence": ev.get("behavior_confidence")
            })

    api_stats = detector.get_statistics()
    print("\n" + "=" * 70)
    print(" VIDEO PROCESSING & TRACKING COMPLETE ")
    print("=" * 70)
    print(f"Total Frames Processed:      {frame_idx}")
    print(f"Annotated Video Saved:       {out_vid_path}")
    print(f"Tracking JSONL Log:          {jsonl_path}")
    print(f"Track Events CSV:            {events_csv_path}")
    print(f"Unique Track IDs Created:    {len(unique_track_ids)}")
    print(f"Max Simultaneous Tracks:     {max_simultaneous_tracks}")
    print(f"Roboflow Requests Total:     {api_stats['total_requests']}")
    print(f"Roboflow Requests Success:   {api_stats['successful_requests']}")
    print(f"Roboflow Requests Failed:    {api_stats['failed_requests']}")
    print(f"Average API Latency:         {api_stats['average_latency_seconds']} s")
    print("=" * 70 + "\n")

    return {
        "video_path": str(out_vid_path),
        "jsonl_path": str(jsonl_path),
        "events_csv_path": str(events_csv_path),
        "tracker": tracker,
        "detector": detector,
        "total_frames": frame_idx,
        "fps": fps,
        "resolution": f"{orig_w}x{orig_h}",
        "max_simultaneous_tracks": max_simultaneous_tracks,
        "unique_tracks": len(unique_track_ids)
    }

def main():
    parser = argparse.ArgumentParser(description="FlockSense — Video Behavior Tracking Pipeline")
    parser.add_argument("--source", type=str, default="dataset/video/sample_chickens.mp4", help="Video file path or webcam index (e.g. 0)")
    parser.add_argument("--config", type=str, default="config/vision_config.yaml", help="Path to vision config YAML")
    parser.add_argument("--api_key", type=str, default=None, help="Roboflow API key")
    parser.add_argument("--output", type=str, default=None, help="Path to save annotated output video")
    parser.add_argument("--max_frames", type=int, default=None, help="Maximum number of frames to process")
    parser.add_argument("--mock_api", action="store_true", help="Run with simulated Roboflow behavior detections")

    args = parser.parse_args()
    run_behavior_video(
        source=args.source,
        config_path=args.config,
        api_key=args.api_key,
        output_video=args.output,
        max_frames=args.max_frames,
        mock_api=args.mock_api
    )

if __name__ == "__main__":
    main()
