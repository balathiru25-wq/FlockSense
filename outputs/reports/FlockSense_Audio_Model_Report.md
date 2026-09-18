# FlockSense — Audio Bioacoustics Model Technical Report

**Project**: FlockSense — AI-Powered Poultry Farm Early-Warning & Flock-Health Monitoring System  
**Pipeline**: Bioacoustic Anomaly Screening (Phase 1–6)  
**Date**: September 2026  
**Status**: Model Trained, Validated, Evaluated, and Tested (Checkpoint Saved)

---

## 1. Executive Summary

FlockSense employs continuous bioacoustic monitoring to establish a **Flock Fingerprint** baseline for commercial poultry sheds. Rather than attempting to diagnose specific pathogens from isolated sounds, the system detects meaningful deviations from normal flock acoustic patterns and generates graded early-warning risk scores:
* 🟢 **GREEN (NORMAL)**: Acoustic signals match baseline flock activity or ambient shed machinery.
* 🟡 **YELLOW (WATCH)**: Moderate acoustic deviation; physical flock inspection recommended.
* 🔴 **RED (ALERT)**: Significant abnormal acoustic patterns (e.g. respiratory distress, rales, coughing); veterinary examination and laboratory testing recommended.

On held-out test data with **strict group-aware leakage prevention**, the trained FlockSense ResNet18 bioacoustic model achieved **98.45% overall accuracy**, **97.68% Macro F1**, **100.00% Abnormal Sensitivity (Recall)**, and a low **1.83% False-Positive Rate**.

---

## 2. Dataset Overview & Integrity

* **Dataset Name**: Poultry Vocalization Signal Dataset for Early Disease Detection
* **Physical Location**: `Poultry Vocalization Signal Dataset for Early Disease Detection/Poultry Vocalization Signal Dataset for Early Disease Detection/Chicken_Audio_Dataset`
* **Total Audio Files**: 346 files
* **Total Audio Duration**: 11,381.46 seconds (189.69 minutes, ~3.16 hours)
* **Dataset Disk Size**: 1,042.07 MB
* **File Format & Encoding**: 100% WAV format, 48,000 Hz sample rate, single-channel (Mono)
* **Corrupted / Empty Files**: 0 corrupted, 0 empty files

### Class Breakdown
| Original Category | FlockSense Mapping | File Count | % of Dataset | Total Duration | Duration Range |
|---|---|---|---|---|---|
| **Healthy** | NORMAL (Flock Vocal Baseline) | 139 files | 40.2% | 4,654.1 s (~77.6 min) | 6.09 s – 906.20 s |
| **Unhealthy** | ABNORMAL (Distress / Anomaly) | 121 files | 35.0% | 3,478.6 s (~58.0 min) | 0.46 s – 134.03 s |
| **Noise** | NORMAL (Ambient Shed Equipment) | 86 files | 24.9% | 3,248.8 s (~54.1 min) | 0.58 s – 104.04 s |

---

## 3. Strict Data Leakage Prevention & Splitting Strategy

### The Leakage Problem
Commercial poultry audio recordings are frequently partitioned from longer recording sessions or recorded sequentially within the same shed environment. Random splitting causes the neural network to memorize specific microphone placement, room impulse response (reverberation), feeder machinery, or fan background noise rather than genuine bioacoustic vocalizations.

### Group-Aware Stratified Splitting
Files were segmented into 51 contiguous recording session groups (blocks of ~7 consecutive numbered recordings) and partitioned across classes using a fixed seed (`42`):

| Split | Files | % Files | Duration | Windows (3.0s, 50% hop) | Unique Groups | Group Overlap |
|---|---|---|---|---|---|---|
| **Train** | 235 | 67.9% | 8,253.7 s (137.6 min) | 2,369 windows | 35 groups | **0 (Zero Leakage)** |
| **Validation** | 56 | 16.2% | 1,765.1 s (29.4 min) | 1,163 windows | 8 groups | **0 (Zero Leakage)** |
| **Held-Out Test** | 55 | 15.9% | 1,362.7 s (22.7 min) | 901 windows | 8 groups | **0 (Zero Leakage)** |

*Verified: Zero recording session groups overlap between Train, Validation, and Test.*

---

## 4. Preprocessing & Bioacoustic Representation

* **Target Sample Rate**: 16,000 Hz (preserves bioacoustic frequency band up to 8 kHz Nyquist while reducing compute overhead by 66% compared to raw 48 kHz).
* **Target Window Duration**: 3.0 seconds (48,000 samples).
* **Windowing Strategy**: Sliding window segmentation with 1.5s hop duration (50% overlap). Short symptom bursts (< 3.0s, e.g. 0.5s coughs/sneezes) are centered and symmetrically padded.
* **Audio Normalization**: Safe peak normalization preventing amplitude clipping.
* **Acoustic Representation**: Log-Mel Spectrogram:
  * FFT window size: 1024 (~64 ms)
  * Hop length: 512 (~32 ms)
  * Mel filter banks: 128 bins
  * Frequency range: 50 Hz – 8,000 Hz
  * Scaling: Decibel (power-to-dB, normalized to standard dynamic range)
* **Training Data Augmentation**:
  * Random circular time shifting (±15%)
  * Random gain modulation (±3 dB)
  * Additive subtle background noise (variance 0.003)
  * SpecAugment frequency masking (param=16) and time masking (param=24)
  * Validation and test sets received **zero augmentation**.

---

## 5. Model Architecture

* **Backbone**: ResNet18 with pretrained ImageNet feature extraction
* **Input Layer Adaptation**: First convolution layer (`conv1`) adapted from 3 channels (RGB) to 1 channel (Log-Mel Spectrogram). Weights initialized by averaging the pretrained RGB filter channels.
* **Custom Classification Head**:
  * Global Average Pooling (`avgpool`) → 512 dimensions
  * Dropout ($p=0.30$)
  * Fully-Connected Linear ($512 \rightarrow 128$)
  * Layer Normalization (`LayerNorm(128)`) for batch-size invariance
  * ReLU activation
  * Dropout ($p=0.21$)
  * Output Linear ($128 \rightarrow 3$) producing class logits for `[Healthy, Unhealthy, Noise]`
* **Parameter Count**:
  * Total Parameters: **11,236,547**
  * Trainable Parameters: **11,236,547**
  * Footprint on Disk: ~43 MB (well-suited for farm edge deployment on Raspberry Pi 5 / Jetson Orin Nano).

---

## 6. Training Dynamics & Checkpointing

* **Hardware Acceleration**: NVIDIA GeForce RTX 3050 Laptop GPU (CUDA 13.0 / PyTorch 2.6.0+cu124)
* **Optimizer**: AdamW ($\beta_1=0.9, \beta_2=0.999$, weight decay $10^{-4}$)
* **Learning Rate**: $3 \times 10^{-4}$ governed by `CosineAnnealingLR`
* **Batch Size**: 32
* **Loss Function**: Weighted Cross-Entropy Loss (weights: Healthy=0.787, Unhealthy=1.007, Noise=1.359)
* **Early Stopping**: Patience of 7 epochs monitored on Composite Score ($0.60 \times \text{Abnormal Recall} + 0.40 \times \text{Macro F1}$).
* **Best Model Checkpoint**: Saved at **Epoch 3** (`models/audio_model_best.pth`).
  * Best Validation Accuracy: **95.27%**
  * Best Validation Macro F1: **95.36%**
  * Best Validation Abnormal Recall: **100.00%**
  * Best Validation Abnormal F1: **96.05%**

---

## 7. Held-Out Test Set Performance

The best checkpoint was evaluated **once** on the held-out test split (901 windows from 55 independent recordings, 8 groups never seen during training).

### Overall Metrics
| Metric | Value |
|---|---|
| **Overall Accuracy** | **98.45%** |
| **Macro Precision** | **96.89%** |
| **Macro Recall** | **98.66%** |
| **Macro F1-Score** | **97.68%** |
| **Weighted F1-Score** | **98.47%** |

### Per-Class Evaluation
| Category | Precision | Recall (Sensitivity) | F1-Score | Support (Windows) |
|---|---|---|---|---|
| **Healthy** | 100.00% | 95.98% | 97.95% | 348 |
| **Unhealthy** | 90.67% | **100.00%** | **95.10%** | 136 |
| **Noise** | 100.00% | 100.00% | 100.00% | 417 |

### Binary Early-Warning Risk Detection (Abnormal vs Baseline/Ambient Noise)
* **Abnormal Sensitivity (Recall)**: **100.00%** (136 / 136 detected; **0 missed**)
* **Specificity**: **98.17%** (751 / 765 correct)
* **False-Positive Rate (FPR)**: **1.83%** (14 / 765)
* **False-Negative Rate (FNR)**: **0.00%** (0 / 136)
* **Abnormal Precision**: **90.67%**

### Confusion Matrix
```text
True \ Predicted      Healthy     Unhealthy     Noise
Healthy                 334           14          0
Unhealthy                 0          136          0
Noise                     0            0        417
```

---

## 8. Error Analysis & Insights

1. **Zero Missed Anomalies**: All 136 test windows containing unhealthy respiratory vocalizations were correctly flagged with high confidence ($P(\text{Unhealthy}) > 0.90$).
2. **Benign False Alerts**: The 14 false positives (1.83% FPR) were windows from healthy recordings that exhibited transient vocal stress or loud flapping mistaken for respiratory anomalies. None were mistaken for background machinery noise.
3. **Noise Separation**: Farm background machinery and ventilation sounds were recognized with **100% precision and 100% recall**, demonstrating that normal shed fans and feeder sounds will not trigger spurious disease alerts.

---

## 9. Genuine Test File Demonstrations

| Audio Sample | Category & Group | Duration | Windows | Predicted State | Status | Abnormality Risk | High-Risk Windows |
|---|---|---|---|---|---|---|---|
| `Healthy/134.wav` | Healthy (Group 19) | 39.82 s | 26 | NORMAL | 🟢 NORMAL | 0.50% | 0 / 26 (0.0%) |
| `Unhealthy/100.wav`| Unhealthy (Group 14) | 1.18 s | 1 | ABNORMAL | 🔴 ALERT | 99.46% | 1 / 1 (100.0%) |
| `Unhealthy/1.wav` | Unhealthy (Group 00) | 22.60 s | 15 | ABNORMAL | 🔴 ALERT | 99.49% | 15 / 15 (100.0%) |
| `Noise/36.wav` | Noise (Group 05) | 14.20 s | 9 | NORMAL | 🟢 NORMAL | 1.03% | 0 / 9 (0.0%) |

---

## 10. Important Limitations

1. **Single Public Bioacoustic Dataset**: Model was trained on a single curated benchmark dataset. Shed acoustics vary widely across different farm configurations, wall materials, and fan designs.
2. **Provisional Risk Thresholds**: The current thresholds ($0.35$ for WATCH, $0.70$ for ALERT) are calibrated on validation distributions and represent development thresholds, not medically calibrated clinical standards.
3. **Absence of Longitudinal Farm History**: In real deployment, the "Flock Fingerprint" will incorporate rolling baselines (e.g. 7-day shed averages) to adjust for bird age and growth acoustics.
4. **Early-Warning Only**: FlockSense does not identify whether an anomaly is Infectious Bronchitis, Newcastle Disease, or non-infectious dust irritation. Professional veterinary diagnostic testing is required for etiology.

---

## 11. Artifacts & Generated Files

* **Model Checkpoint**: [`models/audio_model_best.pth`](file:///models/audio_model_best.pth)
* **Dataset Metadata**: [`outputs/reports/audio_dataset_metadata.csv`](file:///outputs/reports/audio_dataset_metadata.csv)
* **Dataset Report**: [`outputs/reports/audio_dataset_report.txt`](file:///outputs/reports/audio_dataset_report.txt)
* **Training History**: [`outputs/reports/training_history.csv`](file:///outputs/reports/training_history.csv)
* **Test Performance Report**: [`outputs/reports/audio_test_report.txt`](file:///outputs/reports/audio_test_report.txt)
* **Error Analysis Report**: [`outputs/reports/audio_error_analysis.txt`](file:///outputs/reports/audio_error_analysis.txt)
* **Detailed Predictions CSV**: [`outputs/predictions/test_predictions.csv`](file:///outputs/predictions/test_predictions.csv)
* **Confusion Matrix CSV & PNG**: [`outputs/confusion_matrix/audio_confusion_matrix.png`](file:///outputs/confusion_matrix/audio_confusion_matrix.png)
* **Training Graphs**: [`outputs/graphs/flocksense_training_progression.png`](file:///outputs/graphs/flocksense_training_progression.png)
* **Example Representations**: [`outputs/examples/flocksense_audio_representations.png`](file:///outputs/examples/flocksense_audio_representations.png)
