# FlockSense — Vision & Behavior Tracking Technical Report

**Project**: FlockSense — AI-Powered Poultry Farm Early-Warning System  
**Pipeline**: Video Behavior Detection, Temporary Chicken Tracking & Virtual Zone Monitoring  
**Phase**: Vision & Multi-Object Tracking Integration  
**Date**: September 2026  

---

## 1. Executive Summary

In this phase, FlockSense has integrated video processing, multi-object chicken tracking, virtual shed zoning, and per-bird behavior history on top of Roboflow's serverless behavior detection model (`chicken-behavior-detection-within-real-time/17`).

The system answers:
* **Which chickens are visible?** (Temporary session Track IDs assigned and tracked across occlusions)
* **What behavior is each visible chicken showing?** (Standing, Feeding, Sitting, Spreading, Preening)
* **Can we temporarily follow the same chicken as it moves?** (ByteTrack with generic `CHICKEN` class prevents ID fragmentation when behavior changes)
* **Which virtual zone is it currently in?** (6-zone shed layout with point-in-polygon testing and debounce filtering)
* **How does its behavior change over time?** (Chronological behavior timeline stored per Track ID, with temporal confidence-weighted voting)

> **Important Principle**: The vision subsystem observes behavioral and spatial metrics only. It **does NOT diagnose disease or infer health status**. Changes in activity, resting duration, or feeding frequency are recorded as observable features for future multimodal analysis.

---

## 2. Roboflow Model & API Configuration

* **Model ID**: `chicken-behavior-detection-within-real-time/17`
* **Hosted Architecture**: Object Detection with Behavior Classification
* **Classes Detected**: `standing`, `feeding`, `sitting`, `spreading`, `preening`, `resting`, `walking`
* **API Endpoint**: `https://serverless.roboflow.com`
* **Authentication**: Header-based transport (`Authorization: Bearer <API_KEY>`, avoiding query-string exposure)
* **Bandwidth Reduction & Rate Limiting**:
  * **Frame Sampling**: Configurable inference interval (`behavior_inference_every_n_frames: 10`, processing ~3 requests/sec at 30 FPS).
  * **Frame Downsampling**: Frames resized to max width 960px prior to transmission.
  * **Compression**: Quality-controlled JPEG encoding (`jpeg_quality: 75`).
  * **Failure Resilience**: Network timeouts, quota limits, or API disconnects are caught gracefully without terminating video processing; tracks mark behavior as cached/stale and continue spatial tracking.

---

## 3. Video Processing & Tracking Details

* **Input Video**: `dataset/video/sample_chickens.mp4`
* **Resolution**: 960 x 540 pixels
* **Framerate**: 30.0 FPS
* **Total Frames**: 150 frames (5.0 seconds test sequence)
* **Tracker Used**: Supervision `ByteTrack`
  * `lost_track_buffer`: 30 frames (preserves track state across temporary occlusions by feeders or other birds)
  * `track_activation_threshold`: 0.25
  * `minimum_matching_threshold`: 0.80
* **Critical Tracking Rule Enforced**: Every detection is passed to ByteTrack as generic class `CHICKEN`. Behavior labels are maintained separately as metadata. When a chicken transitions from *sitting* to *standing*, its **Track ID remains identical**.

---

## 4. Virtual Zones & Transition Debounce

The shed camera view is divided into a 6-zone normalized grid:

```text
┌──────────────┬──────────────┬──────────────┐
│    ZONE 1    │    ZONE 2    │    ZONE 3    │
│  (Top-Left)  │ (Top-Center) │ (Top-Right)  │
├──────────────┼──────────────┼──────────────┤
│    ZONE 4    │    ZONE 5    │    ZONE 6    │
│(Bottom-Left) │(Bottom-Center│(Bottom-Right)│
└──────────────┴──────────────┴──────────────┘
```

* **Configuration**: `config/zones.json` (normalized polygon coordinates `[0.0, 1.0]`).
* **Debounce Filter**: Requires **3 consecutive frames** in the candidate zone before logging a `ZONE_TRANSITION` event, preventing false transitions caused by birds standing on boundary lines.

---

## 5. Critical Scenario Validation

### Scenario Test: Bird moves from Zone 3 to Zone 2 and changes behavior
* **Initial State (T = 0.0s)**: Track #1 in **ZONE 3**, behavior: **sitting**.
* **Transition (T = 2.3s)**: Bird stands up, walks across boundary into **ZONE 2**, behavior: **standing**.
* **Validation Results**:
  * **Same ID Retained**: **YES** (Track #1 maintained throughout movement and behavior change).
  * **Behavior History Retained**: **YES** (Chronological log records: 9 frames *sitting* followed by 20 frames *standing*).
  * **Zone History Updated**: **YES** (`['ZONE_3', 'ZONE_2']`).
  * **Boundary Debounce**: Transition confirmed with zero jitter.

---

## 6. Generated Files & Artifacts

| Component | Path | Description |
|---|---|---|
| **Annotated Video** | `outputs/vision/videos/flocksense_behavior_tracking.mp4` | Video with bounding boxes, HUD overlay, behavior labels, and virtual zones |
| **Track Events Log** | `outputs/vision/logs/track_events.csv` | Chronological events (`TRACK_STARTED`, `ZONE_TRANSITION`, `BEHAVIOR_CHANGED`) |
| **Tracking State Data** | `outputs/vision/logs/tracking_data.jsonl` | Frame-by-frame JSON Lines containing per-track positions, speeds, and behavior ages |
| **Vision Configuration**| `config/vision_config.yaml` | Sampling rates, tracker parameters, and smoothing settings |
| **Zone Configuration**  | `config/zones.json` | 6-zone normalized coordinates |
| **Detector Module**     | `vision/roboflow_behavior_detector.py` | Cloud API client with header authentication and bandwidth reduction |
| **Tracker Module**      | `vision/behavior_tracker.py` | ByteTrack wrapper with generic CHICKEN conversion and query API |
| **State & History**     | `vision/track_state.py` & `vision/behavior_history.py` | State structures and confidence-weighted voting |
| **Visualizer**          | `vision/visualization.py` | Zone overlays and HUD dashboard |
| **Runner Script**       | `vision/run_behavior_video.py` | Command-line video processor |

---

## 7. Known Limitations

1. **Temporary Track Identities**: Track IDs are session-based and do not represent permanent biological identity. If a bird leaves the field of view for extended periods, it will be assigned a new ID upon re-entry.
2. **Cloud API Latency & Internet Dependency**: Roboflow serverless API introduces round-trip latency (~40–150ms). Running inference every 10th frame effectively mitigates bandwidth constraints while keeping behavioral records current.
3. **Flock Density & Occlusion**: In high-density commercial sheds, severe bird-on-bird occlusions can degrade bounding box localization. ByteTrack's 30-frame buffer recovers identity during brief crossovers, but long occlusions terminate the track honestly.
4. **Observable Activity Only**: Visual detections describe physical state (sitting, standing, feeding) and movement velocity; they must never be treated as disease confirmation without multimodal correlation.
