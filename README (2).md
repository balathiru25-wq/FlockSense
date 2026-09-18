# FlockSense — AI-Powered Poultry Farm Early-Warning System

FlockSense is an edge-ready, bioacoustic flock health monitoring system designed to detect subtle behavioral and vocal anomalies in commercial poultry sheds before visual clinical signs appear.

> **Important Principle**: FlockSense is an **early-warning screening system**, NOT a veterinary diagnosis system. It detects that a flock is deviating from its learned normal pattern and generates a risk alert. Veterinary examination and laboratory testing remain responsible for clinical confirmation. Never present AI output as a confirmed medical diagnosis.

---

## 1. Project Architecture

```text
FlockSense/
├── config/
│   ├── audio_config.yaml            # Audio, Mel-spectrogram & training hyperparameters
│   └── audio_class_mapping.json     # Class mapping & early-warning risk definitions
├── dataset/
│   └── audio/                       # Raw read-only poultry bioacoustic recordings
├── models/
│   └── audio_model_best.pth         # Best checkpoint (ResNet18 bioacoustic model)
├── outputs/
│   ├── confusion_matrix/            # Confusion matrix PNG & CSV
│   ├── examples/                    # Sample waveform & log-Mel spectrogram visualizer
│   ├── graphs/                      # Loss, accuracy, F1, and recall progression curves
│   ├── predictions/                 # Test set prediction breakdown CSV
│   └── reports/                     # Inspection report, test report, error analysis & markdown report
├── splits/
│   ├── train.csv                    # Group-aware training split (67.9%)
│   ├── validation.csv               # Group-aware validation split (16.2%)
│   ├── test.csv                     # Held-out test split (15.9%)
│   └── splits_summary.txt           # Data leakage verification summary
├── training/
│   ├── inspect_audio_dataset.py     # Dataset auditor (duration, formats, integrity)
│   ├── create_splits.py             # Group-aware stratified train/val/test splitter
│   ├── audio_transforms.py          # Audio loading, resampling, and log-Mel extractor
│   ├── audio_dataset.py             # PyTorch Dataset with sliding-window segmentation
│   ├── models.py                    # ResNet18 bioacoustic architecture
│   ├── train_audio.py               # Complete training pipeline with early stopping
│   ├── evaluate_audio.py            # Test evaluation on held-out split
│   ├── audio_inference.py           # Long-recording sliding-window inference pipeline
│   ├── test_inference_samples.py    # Test set verification runner
│   └── visualize_examples.py        # Bioacoustic representation visualizer
└── requirements.txt                 # Python dependencies
```

---

## 2. Environment Setup

```bash
# Recommended Python version: 3.10+ (tested on Python 3.12)
pip install -r requirements.txt
```

---

## 3. Audio Model Pipeline

### Step 1: Inspect Audio Dataset
Scans the dataset, validates sample rates and channels, and checks for corrupted files:
```bash
python training/inspect_audio_dataset.py
```
*Outputs:*
* `outputs/reports/audio_dataset_metadata.csv`
* `outputs/reports/audio_dataset_report.txt`

### Step 2: Create Group-Aware Splits (Zero Data Leakage)
Partitions files into groups of contiguous recordings to prevent room reverberation or microphone bias leakage:
```bash
python training/create_splits.py
```
*Outputs:*
* `splits/train.csv` (235 files, 2,369 windows)
* `splits/validation.csv` (56 files, 1,163 windows)
* `splits/test.csv` (55 files, 901 windows)
* `splits/splits_summary.txt`

### Step 3: Visualize Bioacoustic Features
Generates sample waveform and log-Mel spectrogram visualizations across all 3 classes:
```bash
python training/visualize_examples.py
```
*Output:* `outputs/examples/flocksense_audio_representations.png`

### Step 4: Train Bioacoustic Model
Trains the ResNet18 classifier with GPU acceleration, class weighting, SpecAugment, and early stopping:
```bash
python training/train_audio.py
```
*Outputs:*
* `models/audio_model_best.pth` (Checkpoint selected on Abnormal Recall & Macro F1)
* `outputs/graphs/flocksense_training_progression.png`
* `outputs/reports/training_history.csv`

### Step 5: Evaluate on Held-Out Test Set
Evaluates the best checkpoint once against the untouched test set:
```bash
python training/evaluate_audio.py
```
*Outputs:*
* `outputs/reports/audio_test_report.txt`
* `outputs/reports/audio_error_analysis.txt`
* `outputs/confusion_matrix/audio_confusion_matrix.png`
* `outputs/confusion_matrix/audio_confusion_matrix.csv`
* `outputs/predictions/test_predictions.csv`

### Step 6: Run Inference on Any Recording
Analyzes arbitrary-length poultry recordings using multi-window sliding analysis:
```bash
python training/audio_inference.py --audio "path/to/recording.wav"
```

Example JSON output for backend integration:
```bash
python training/audio_inference.py --audio "path/to/recording.wav" --json
```

---

## 4. Test Performance Summary

Evaluated on 901 held-out test windows across 55 independent farm recordings:
* **Overall Accuracy**: **98.45%**
* **Macro F1-Score**: **97.68%**
* **Abnormal Sensitivity (Recall)**: **100.00%** (136/136 detected; 0 missed anomalies)
* **Specificity**: **98.17%**
* **False-Positive Rate**: **1.83%**
* **False-Negative Rate**: **0.00%**

---

## 5. Early-Warning Status Indicators

| Status | Color | Risk Threshold | Meaning | Recommended Action |
|---|---|---|---|---|
| **NORMAL** | 🟢 Green | $< 35\%$ | Flock acoustic pattern matches healthy vocal baseline or ambient shed machinery. | Continue routine monitoring. |
| **WATCH** | 🟡 Yellow | $35\% - 70\%$ | Moderate acoustic anomaly or vocal variance detected. | Physical flock and ventilation inspection. |
| **ALERT** | 🔴 Red | $\ge 70\%$ | Significant respiratory/anomaly pattern detected. | Immediate flock inspection; consult veterinarian for laboratory verification. |

---

## 6. Video AI Model (Roboflow Behavior Detection)

FlockSense integrates Roboflow's **`chicken-behavior-detection-within-real-time/17`** model to monitor chicken behaviors (e.g., feeding, preening, resting, lethargy/clustering) via Serverless Cloud API with header-based authorization.

### Running Video / Image Inference:

```bash
# Set your Roboflow API key
$env:ROBOFLOW_API_KEY="your_api_key_here"  # Windows PowerShell
# or: export ROBOFLOW_API_KEY="your_api_key_here"  # Linux / macOS

# Run behavior analysis on a flock camera frame or image
python training/chicken_behavior_inference.py --image "dataset/video/sample_flock.jpg"

# Output raw JSON payload for backend/dashboard:
python training/chicken_behavior_inference.py --image "dataset/video/sample_flock.jpg" --json
```

---

## 7. Limitations & Scientific Guardrails

* **Early-Warning Only**: FlockSense never claims to diagnose specific pathogens (e.g. Avian Influenza, Infectious Bronchitis). Laboratory testing is mandatory for etiology.
* **Acoustic & Visual Diversity**: Model performance can be influenced by shed geometry, camera angle, and microphone placement; multi-farm acoustic calibration is recommended.

