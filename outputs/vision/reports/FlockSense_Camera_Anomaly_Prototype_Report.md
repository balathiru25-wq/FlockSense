# FlockSense Camera Anomaly Prototype Report

**Document Status**: ARCHITECTURAL VERIFICATION & SYNTHETIC PROTOTYPE  
**Validation Status**: `PROTOTYPE_ONLY_SYNTHETIC_DATA`  
**Real-World Validated**: `NO`  
**Clinical / Disease Diagnoses**: `NONE`  

---

## 1. Executive Summary

This report documents the completion of the unsupervised behavioural deviation detection model for the camera pipeline in the FlockSense poultry monitoring platform. 

The purpose of this subsystem is to map multi-dimensional temporal and spatial behavioral observations into a normalized **Camera Behaviour Deviation Score (0–100)** with human-interpretable rule-backed explainability reasons. This score serves as one of the two primary inputs to the subsequent multimodal **Audio + Camera Fusion** phase.

> **CRITICAL DISCLAIMER**:
> All training, calibration, and validation in this phase were performed strictly on **synthetic poultry footage and simulated baseline profiles**. No real-world poultry video or clinically confirmed abnormal data was used. Consequently:
> - This model does **NOT** diagnose disease (e.g., respiratory infections, Newcastle disease, enteritis).
> - Scores represent **unsupervised behavioural deviation from baseline distributions**, NOT infection probabilities.
> - Diagnostic accuracy, sensitivity, and clinical specificity cannot be reported.

---

## 2. Feature Dataset Audit

- **Input File**: `outputs/vision/features/bird_behavior_features.csv`
- **Source Video**: `dataset/video/sample_chickens.mp4` (Synthetic test sequence)
- **Rows**: 3 track windows (Tracks 1, 2, 3)
- **Duration**: 5.0 seconds (150 video frames at 30 fps)
- **Total Columns**: 27
- **Data Quality Findings**:
  - **Missing Values**: 0 nulls across numerical feature columns.
  - **Constant Features in Seed Video**: Several posture ratios (`spreading_ratio`, `resting_ratio`, `walking_ratio`) were zero in this short 5-second test clip.
  - **Identifier Exclusions**: Non-behavioral identifiers (`track_id`, `timestamp_start`, `timestamp_end`, `current_zone`, `current_behavior`) were stripped from predictive model input to prevent identity-based leakage.
  - **Sufficiency for ML**: To avoid single-tree triviality in `IsolationForest` on only 3 seed samples, a structured 123-sample synthetic baseline distribution was generated incorporating normal behavioral archetypes (active exploring, feeding station, standing/preening, and balanced flock members).

### Selected ML Predictive Features (18 dimensions)
1. `movement_rate`
2. `movement_variance`
3. `distance_travelled_pixels`
4. `stationary_duration`
5. `stationary_ratio`
6. `standing_ratio`
7. `feeding_ratio`
8. `sitting_ratio`
9. `spreading_ratio`
10. `preening_ratio`
11. `resting_ratio`
12. `walking_ratio`
13. `behaviour_transition_rate`
14. `distance_to_nearest_bird`
15. `distance_to_flock_centroid`
16. `relative_isolation_score`
17. `relative_activity`
18. `zone_transition_count`

---

## 3. Model Architecture & Training Parameters

- **Algorithm**: `sklearn.ensemble.IsolationForest`
- **Scaler**: `sklearn.preprocessing.StandardScaler`
- **Number of Estimators**: `100`
- **Contamination**: `0.10` (Status: `PROVISIONAL_DEVELOPMENT_VALUE`)
- **Random State**: `42`
- **Decision Function Baseline Range**: `min = -0.1523`, `median = +0.0320`, `max = +0.0718`
- **Artifacts Saved**:
  - `models/camera_anomaly_model.pkl` (Serialized bundle: model, scaler, feature list, baseline stats, metadata)
  - `models/camera_anomaly_scaler.pkl` (Standalone fitted scaler)
  - `models/camera_anomaly_baseline.json` (Flock baseline statistics: mean, median, std, quartiles)
  - `config/camera_anomaly_config.json` (Centralized configuration and thresholds)

---

## 4. Scoring Logic & Provisional Thresholds

### Raw Score to Deviation Mapping
Isolation Forest decision functions produce positive values for baseline inliers and negative values for abnormal outliers. To produce an intuitive, consistent 0–100 scale:
$$\text{deviation\_score} = \text{clip}\left(50.0 - (\text{raw\_decision\_score} \times 160.0), 0.0, 100.0\right)$$

- Lower scores ($0 \dots 44$) indicate close conformity to the learned baseline.
- Higher scores ($70 \dots 100$) indicate significant behavioural divergence.
- **This is NOT a probability and must never be displayed as a percent chance of disease.**

### Provisional Thresholds
| Status Category | Deviation Score Range | Interpretation |
| :--- | :--- | :--- |
| **NORMAL_PATTERN** | $0.0 \le \text{Score} < 45.0$ | Behaviour conforms to normal flock peer distributions |
| **WATCH_DEVIATION** | $45.0 \le \text{Score} < 70.0$ | Moderate divergence (e.g. reduced feeding or prolonged standing) |
| **HIGH_DEVIATION** | $70.0 \le \text{Score} \le 100.0$ | Substantial deviation (extreme lethargy, severe isolation, agitation) |

Threshold status: `PROVISIONAL_SYNTHETIC_THRESHOLDS`.

---

## 5. Software Stress Test Results

Executed via `python -m vision.test_camera_anomaly`:

### Part 1: Seed CSV Rows
| Track ID | Movement Rate | Stationary Ratio | Observed Postures | Dev Score | Status | Primary Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Track #1** | 54.0 px/s | 0.00 | stand: 0.5, sit: 0.5 | **74.4** | `HIGH_DEVIATION` | Unusually elevated locomotor activity exceeding normal baseline |
| **Track #2** | 0.0 px/s | 1.00 | feed: 1.0 | **59.7** | `WATCH_DEVIATION` | Prolonged stationary duration exceeding peer baseline |
| **Track #3** | 0.0 px/s | 1.00 | stand: 0.7, preen: 0.3 | **47.1** | `WATCH_DEVIATION` | Prolonged stationary duration; reduced feeding during active flock interval |

### Part 2: Behavioral Archetype Logic Sanity Tests
| Test Case | Description | Raw Score | Deviation Score | Status | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Case A** | Hypoactive / prolonged stationary / high sitting | -0.0875 | **64.0 / 100** | `WATCH_DEVIATION` | **PASSED** (Significantly > Case C) |
| **Case B** | Peripheral social isolation / distant from flock | -0.0256 | **54.1 / 100** | `WATCH_DEVIATION` | **PASSED** (Significantly > Case C) |
| **Case C** | Normal flock baseline activity & cohesion | +0.0631 | **39.9 / 100** | `NORMAL_PATTERN` | **PASSED** (Baseline reference) |

### Part 3: Score Persistence & Decay (TrackState)
- **Isolated Spike Rejection**: Sequence $[12.0, 14.0, 88.0, 13.0, 11.0]$ smoothed to a maximum of $39.1$, correctly preventing an erroneous `HIGH_DEVIATION` state from a transient single-window fluctuation.
- **Persistent High Deviation**: Sequence $[74.0, 81.0, 79.0, 76.0, 82.0]$ maintained stable `HIGH_DEVIATION` ($76.5 \dots 78.7$).
- **Score Decay / Normalization**: When behaviour transitioned $[80.0 \to 78.0 \to 72.0 \to 55.0 \to 39.0 \to 24.0]$, the smoothed score smoothly decayed from $79.2 \to 46.4$, demonstrating recovery without permanent alert lock-in.

---

## 6. Known Limitations

1. **Synthetic Footage Only**: Tracking and features were derived from a 5-second simulated video (`sample_chickens.mp4`).
2. **No Real Poultry Baseline**: Natural diurnal rhythms, feeding schedules, lighting changes, and flock densities are not captured in the training distribution.
3. **Absence of Real Abnormal Poultry Video**: Without clinical abnormal footage, false-positive and false-negative rates under commercial conditions cannot be estimated.
4. **Occlusion & Density**: Real broiler sheds exhibit severe visual clutter and occlusions that will impact ByteTrack stability.

---

## 7. Next Requirements for Real-World Deployment

1. Collect continuous multi-hour CCTV video from commercial poultry sheds.
2. Re-extract rolling feature windows across diverse lighting and feeding phases.
3. Re-fit `IsolationForest` on real uninfected flock baselines.
4. Integrate with the completed ResNet-18 audio bioacoustics model in the upcoming **Audio + Camera Fusion** phase.
