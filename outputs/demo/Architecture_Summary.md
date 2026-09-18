# FlockSense System Architecture Summary

`
                      FLOCKSENSE MULTIMODAL SENSOR PIPELINE
                      
 [ MICROPHONE SENSOR ]                           [ OVERHEAD CAMERA SENSORS ]
          │                                                    │
          ▼                                                    ▼
   Raw Audio WAV                                     Overhead Video Frames
   (Shed-Level)                                                │
          │                                                    ▼
          ▼                                       Roboflow Object Detection
  1-Ch Log-Mel Spectrogram                      (chicken-behavior-detection-within-real-time/17)
  (16kHz, 128 Mel Bins)                                        │
          │                                                    ▼
          ▼                                          ByteTrack Tracking
  ResNet18 Deep Neural Net                          (Kalman Filter + Association)
  (Trained weights: audio_model_best.pth)                      │
          │                                                    ▼
          ▼                                            TrackState History
  Global Acoustic Abnormality                      (Centroids, BBoxes, Behaviors)
  (0.0% – 100.0%)                                              │
          │                                                    ▼
          │                                          Virtual Shed Zones
          │                                        (Polygons: Zone 1, 2, 3, 4)
          │                                                    │
          │                                                    ▼
          │                                      Spatiotemporal Feature Vector
          │                                   (Mean velocity, stationary ratio,
          │                                    isolation distance, zone shifts)
          │                                                    │
          │                                                    ▼
          │                                        Isolation Forest Model
          │                                 (Trained weights: camera_anomaly_model.pkl)
          │                                                    │
          │                                                    ▼
          │                                      Camera Behavioral Deviation
          │                                           (0.0% – 100.0%)
          │                                                    │
          └─────────────────────┬──────────────────────────────┘
                                │
                                ▼
                   MULTIMODAL FUSION ENGINE
                   (fusion/state_manager.py)
                                │
                                ▼
                  Priority Score Formulation:
        Priority = 0.55 * CamDev + 0.35 * Audio + 0.10 * ZoneRisk
                                │
                                ▼
                     Candidate Ranking & Triage
                    Rank 1: Track #17 (Zone 2)
                    Rank 2: Track #24 (Zone 4)
                    Rank 3: Track #12 (Zone 1)
                                │
                                ▼
                       ALERT NOTIFICATION
       Acoustic distress detected across flock. Track #17 in
 ZONE 2 exhibits highest persistent behavioural deviation.
        [DISCLAIMER: Audio is flock-level, not localized to Track #17]
                                │
                                ▼
                         FARMER ACTION
         1. Walk to Zone 2.
         2. Inspect Track #17 and surrounding flock members.
         3. If concerning signs persist, consult a veterinarian.
`

## Component Breakdown

| Subsystem | Input Source | Algorithm / Architecture | Output Signal | Latency / Scope |
| :--- | :--- | :--- | :--- | :--- |
| **Acoustic Abnormality** | Microphone audio stream | ResNet18 (1-channel Log-Mel spectrogram, PyTorch) | Acoustic Abnormality Score (0–100%) | ~120ms / Flock-level |
| **Vision Tracking** | Overhead IP camera stream | Roboflow Behaviour Model + ByteTrack | Temporary Track IDs & bounding boxes | 30 FPS / Shed-wide |
| **Spatial Mapping** | Track centroids | Ray-casting Point-in-Polygon (zones.json) | Current & Previous Zone IDs | Real-time (<5ms) |
| **Behavioral Deviation** | Track history buffers (30–60s) | Isolation Forest Anomaly Detection (Scikit-Learn) | Camera Deviation Score (0–100%) | Windowed (1s update) |
| **Multimodal Fusion** | Acoustic + Vision + Zone states | State Manager & Weighted Ranking Engine | Inspection Priority (0–100%) & Status | Synchronous on event |
| **Operator Interface** | WebSocket / REST JSON endpoints | React 19 + TypeScript + Tailwind CSS Dashboard | Visual heatmaps, candidate cards, alerts | 60 FPS UI |
