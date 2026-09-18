# FlockSense Multimodal Audio + Camera Fusion Prototype Report

**Document Status**: ARCHITECTURAL VERIFICATION & FUSION ENGINE PROTOTYPE  
**Validation Status**: `PROTOTYPE_ONLY_SYNTHETIC_DATA`  
**Real-World Validated**: `NO`  
**Clinical / Disease Diagnoses**: `NONE`  
**Active Mode**: `GLOBAL_AUDIO` (Mode A)  
**Future Prepared Mode**: `LOCALIZED_AUDIO` (Mode B interface verified)  

---

## 1. Executive Summary

This report documents the implementation and verification of the **FlockSense Multimodal Audio + Camera Fusion Engine**. 

The purpose of this engine is to synthesize two distinct sensor streams:
1. **Global Flock Bioacoustic Abnormality** (ResNet18 Log-Mel spectrogram classifier, 16 kHz), and
2. **Individual Camera Behavioral Deviation** (ByteTrack + Roboflow behavior classes + Isolation Forest anomaly detector),

along with **temporal persistence**, **temporary Track IDs**, and **virtual shed monitoring zones**, to generate an actionable, real-time:
- **Per-Bird Inspection Priority Score (0–100)**: Guiding poultry farmers on *which currently tracked birds should be physically inspected first*, and
- **Flock-Level Early-Warning Status** (`NORMAL`, `WATCH`, `ALERT`).

> **CRITICAL ARCHITECTURAL CONSTRAINTS**:
> 1. **No Medical Claims**: Inspection priority is strictly a prioritization metric for human visual inspection, **never** a probability of disease (e.g. Newcastle, Bronchitis).
> 2. **Global Audio Context (No False Attribution)**: Because microphone-array sound localization is not currently available, acoustic anomalies represent **shed-wide flock context**. Acoustic scores are **never** directly attributed as the individual risk of a specific bird. Camera-normal birds receive **zero** audio boost.
> 3. **Provisional Weights**: All fusion weights and thresholds are development prototype parameters for architectural validation.

---

## 2. Sensor Subsystems Summary

### 2.1 Audio System
- **Model Checkpoint**: `models/audio_model_best.pth`
- **Architecture**: ResNet18 adapted for 1-channel Log-Mel spectrogram input (128 Mel bins, 16 kHz sample rate, 3.0s window duration, 512 hop length).
- **Inference Pipeline**: `training/audio_inference.py`
- **Output Schema**: Normalized acoustic abnormality probability ($0.0 \dots 1.0$), confidence score, and flock alert state.
- **Localization Availability**: `FALSE` in active production mode (`audio_scope = "FLOCK"`).

### 2.2 Camera System
- **Object Detection & Behavior Model**: Roboflow `chicken-behavior-detection-within-real-time/17` (detects `standing`, `feeding`, `sitting`, `spreading`, `preening`, `resting`, `walking`).
- **Tracking**: ByteTrack (`supervision`), converting behavior classes to generic `CHICKEN` class to guarantee persistent Track IDs across behavior transitions.
- **Virtual Zones**: 6 polygon zones (`config/zones.json`) with frame debouncing.
- **Camera Anomaly Model**: `models/camera_anomaly_model.pkl` (Isolation Forest + StandardScaler, 18 features).
- **Validation Status**: `PROTOTYPE_ONLY_SYNTHETIC_DATA` (derived from synthetic video clip `dataset/video/sample_chickens.mp4`).

---

## 3. Fusion Engine Architecture & Mathematical Formulation

The fusion engine is modularly structured in `fusion/`:
- `models.py`: Strongly typed dataclasses (`AudioEvent`, `CameraTrackState`, `InspectionCandidate`, `FlockStatus`, `EarlyWarningAlert`).
- `audio_event.py`: Acoustic event manager with rolling context and temporal deduplication.
- `temporal_memory.py`: Multi-window exponential smoothing ($α=0.35$), persistence scoring ($0–100$), and evidence decay ($20$s half-life).
- `candidate_ranker.py`: Priority sorting, ranking, and terminal summary reporting.
- `alert_engine.py`: Farmer recommendation generation and persistence to `outputs/fusion/logs/alerts.csv`.
- `fusion_engine.py`: Central coordination and score synthesis.
- `state_manager.py`: Reusable, thread-safe API ready for FastAPI routes.

### Inspection Priority Formula
$$\text{Base Priority} = w_{\text{dev}} \cdot S_{\text{dev}} + w_{\text{pers}} \cdot S_{\text{pers}} + w_{\text{iso}} \cdot S_{\text{iso}} + w_{\text{act}} \cdot S_{\text{act}}$$
$$\text{Inspection Priority} = \min\left(100.0, \max\left(0.0, \text{Base Priority} + \Delta_{\text{audio}}\right)\right)$$

Where:
- $w_{\text{dev}} = 0.50$: Camera behavioral deviation score ($0–100$).
- $w_{\text{pers}} = 0.25$: Temporal persistence score ($0–100$).
- $w_{\text{iso}} = 0.15$: Relative spatial isolation score ($0–100$).
- $w_{\text{act}} = 0.10$: Relative activity deviation score ($0–100$).
- $\Delta_{\text{audio}}$: Global acoustic urgency modifier ($0–15.0$).

### Audio Urgency Modifier Policy
$$\Delta_{\text{audio}} = \begin{cases} 
0.0 & \text{if } S_{\text{dev}} < 45.0 \text{ or } S_{\text{audio}} < 35.0 \\
15.0 \times \left(\frac{S_{\text{audio}} - 35.0}{65.0}\right) \times \min\left(1.0, \frac{S_{\text{dev}} - 45.0}{30.0}\right) & \text{if } S_{\text{dev}} \ge 45.0 \text{ and } S_{\text{audio}} \ge 35.0 
\end{cases}$$

> **Core Rule**: A chicken with normal camera behavior ($S_{\text{dev}} < 45.0$) receives **exactly $0.0$ audio boost**. This strictly avoids false attribution of acoustic anomalies to healthy birds.

---

## 4. Controlled End-to-End Test Results

All 6 controlled test scenarios were executed via `python fusion/test_fusion_engine.py`:

```
================================================================================
TEST 1: GLOBAL AUDIO CONTEXT & MULTI-TRACK RANKING
================================================================================
Global Audio: 86.0/100 (HIGH_ACOUSTIC_DEVIATION, Unlocalized)
Rank  | Track ID  | Current Zone  | Evidence Zone  | Priority  | Status   | Audio Boost | Primary Reason
--------------------------------------------------------------------------------------------------------
1     | #17       | ZONE_3        | ZONE_3         | 87.5      | ALERT    | +11.8       | movement rate below flock median baseline
2     | #24       | ZONE_4        | ZONE_4         | 72.8      | ALERT    | +9.0        | movement rate below flock median baseline
3     | #12       | ZONE_1        | ZONE_1         | 12.0      | NORMAL   | +0.0        | flock-wide alert active, camera behaviour normal
Result: PASSED. Track #17 ranked 1st. Track #12 received 0.0 audio boost. False individual attribution strictly avoided.

================================================================================
TEST 2: TRACK ZONE MIGRATION (RISK FOLLOWS TRACK ID)
================================================================================
Initial (t=10s): Track #17 in ZONE_3 | Priority: 73.7 | Initial Evidence Zone: ZONE_3
Migration (t=20s): Track #17 in ZONE_2 | Priority: 77.5 | Initial Evidence Zone: ZONE_3
Alert logged: New Zone ZONE_2 recorded. Risk followed Track ID; did not stay in ZONE_3.
Result: PASSED.

================================================================================
TEST 3: TEMPORAL PERSISTENCE VS TRANSIENT SPIKE
================================================================================
Track A (Isolated Spike [10, 14, 83, 12, 11]): Priority = 16.5 | Persistence = 12.0 | Status = NORMAL
Track B (Sustained [71, 78, 82, 80, 76]):      Priority = 76.5 | Persistence = 100.0 | Status = ALERT
Result: PASSED. Transient spike rejected; sustained deviation elevated to ALERT.

================================================================================
TEST 4: SCORE DECAY WHEN BEHAVIOR NORMALIZES
================================================================================
Behavior sequence returning to normal: [82 -> 78 -> 65 -> 51 -> 34 -> 20]
Inspection Priority: 62.2 -> 65.3 -> 65.0 -> 60.8 -> 52.1 -> 41.4 (NORMAL)
Drop: -23.6 points into NORMAL range.
Result: PASSED.

================================================================================
TEST 5: GLOBAL AUDIO CONTEXT EXPIRATION
================================================================================
At t=10s (within 15s timeout): Global Audio Score = 88.0 (ALERT)
At t=30s (past 15s timeout):   Global Audio Score = 0.0 (NORMAL)
Result: PASSED. Stale audio events cleanly expire.

================================================================================
TEST 6: SIMULATED LOCALIZED AUDIO PATH (MODE B INTERFACE)
================================================================================
Simulated localized audio targeting ZONE_3 (Score 90.0):
Track #301 in target ZONE_3: Priority = 79.1 | Audio Boost = +21.3
Track #302 in other ZONE_1:  Priority = 64.1 | Audio Boost = +6.3
Result: PASSED. Spatial congruence bonus applied only to target zone.
```

---

## 5. Artifacts and Outputs Created

1. **Configuration**:
   - `config/fusion_config.yaml`
2. **Core Modules**:
   - `fusion/__init__.py`
   - `fusion/models.py`
   - `fusion/audio_event.py`
   - `fusion/temporal_memory.py`
   - `fusion/candidate_ranker.py`
   - `fusion/alert_engine.py`
   - `fusion/fusion_engine.py`
   - `fusion/state_manager.py`
3. **Automated Test Suite**:
   - `fusion/test_fusion_engine.py`
4. **Structured Logs Generated**:
   - `outputs/fusion/logs/fusion_events.jsonl` (45+ structured tracking & fusion records)
   - `outputs/fusion/logs/alerts.csv` (32+ persisted early-warning inspection alerts)

---

## 6. Known Limitations

1. **Absence of Real Microphone Array**: Sound source coordinates $(x, y)$ or zone localization are currently unavailable. Mode A (`GLOBAL_AUDIO`) is strictly active.
2. **Synthetic Video Prototype**: The camera anomaly model was trained on synthetic footage (`sample_chickens.mp4`).
3. **Provisional Fusion Weights**: $w_{\text{dev}}, w_{\text{pers}}, w_{\text{iso}}, w_{\text{act}}$ and $\Delta_{\text{audio}}$ are heuristic development weights pending real farm calibration.
4. **No Medical Inference**: The system produces inspection priority indices, not clinical diagnoses.

---

## 7. Next Steps: Backend & Dashboard Phase

The Fusion Engine is now serialized, verified, and exposes a clean interface via `fusion.state_manager.FusionStateManager`.

The immediate next phase will implement:
1. **FastAPI Web Backend**: Exposing endpoints:
   - `GET /api/flock-status`
   - `GET /api/candidates`
   - `GET /api/tracks`
   - `GET /api/tracks/{track_id}`
   - `GET /api/alerts`
   - `POST /api/audio-event`
2. **React Dashboard**: Modern farmer-facing dashboard displaying real-time shed layout, zone occupancy, top candidate cards, acoustic meters, and actionable inspection guidance.
