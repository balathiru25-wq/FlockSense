import os
import sys
import csv
import json
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

# Setup paths
_curr = Path(__file__).resolve().parent
_root = _curr.parent
for p in [str(_curr), str(_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from audio_dataset import FlockSenseDataset, CLASS_TO_IDX, IDX_TO_CLASS
from models import FlockSenseResNet18
from audio_inference import FlockSenseAudioInference

def run_comprehensive_verification():
    project_root = Path(".").resolve()
    ckpt_path = project_root / "models" / "audio_model_best.pth"
    test_csv = project_root / "splits" / "test.csv"
    train_csv = project_root / "splits" / "train.csv"
    pred_csv_path = project_root / "outputs" / "predictions" / "test_predictions.csv"
    pred_csv_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Leakage Verification
    with open(train_csv, "r", encoding="utf-8") as f:
        train_rows = list(csv.DictReader(f))
    with open(test_csv, "r", encoding="utf-8") as f:
        test_rows = list(csv.DictReader(f))

    train_files = set(r["filepath"] for r in train_rows)
    test_files = set(r["filepath"] for r in test_rows)
    train_groups = set(r["group_id"] for r in train_rows)
    test_groups = set(r["group_id"] for r in test_rows)

    file_overlap = train_files.intersection(test_files)
    group_overlap = train_groups.intersection(test_groups)

    leakage_passed = (len(file_overlap) == 0 and len(group_overlap) == 0)

    # 2. Model Loading & Evaluation across Test Set
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)

    model = FlockSenseResNet18(num_classes=3, pretrained=False, dropout=0.0).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    test_ds = FlockSenseDataset(
        test_csv, project_root=project_root,
        clip_duration=ckpt["audio_config"]["clip_duration_seconds"],
        target_sr=ckpt["audio_config"]["target_sample_rate"],
        is_training=False, augment=False
    )
    test_loader = DataLoader(test_ds, batch_size=32, shuffle=False, num_workers=0)

    all_preds = []
    all_targets = []
    all_probs = []
    all_filenames = []
    all_groups = []
    all_file_indices = []

    with torch.no_grad():
        for batch in test_loader:
            specs = batch["spectrogram"].to(device)
            labels = batch["label"].to(device)
            logits = model(specs)
            probs = torch.softmax(logits, dim=1)
            preds = torch.argmax(logits, dim=1)

            all_preds.extend(preds.cpu().numpy())
            all_targets.extend(labels.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())
            all_filenames.extend(batch["filename"])
            all_groups.extend(batch["group_id"])
            all_file_indices.extend(batch["file_idx"].numpy())

    all_preds = np.array(all_preds)
    all_targets = np.array(all_targets)
    all_probs = np.array(all_probs)

    # Binary Mapping: Normal (Healthy=0, Noise=2) vs Abnormal (Unhealthy=1)
    # Target binary: 1 = Abnormal, 0 = Normal
    bin_targets = (all_targets == 1).astype(int)
    bin_preds = (all_preds == 1).astype(int)

    # Binary Confusion Matrix:
    # [[True Normal (TN), False Alert (FP)],
    #  [Missed Abnormal (FN), Correct Abnormal (TP)]]
    tn = int(np.sum((bin_targets == 0) & (bin_preds == 0)))
    fp = int(np.sum((bin_targets == 0) & (bin_preds == 1)))
    fn = int(np.sum((bin_targets == 1) & (bin_preds == 0)))
    tp = int(np.sum((bin_targets == 1) & (bin_preds == 1)))

    total_test = len(bin_targets)
    acc = (tp + tn) / total_test
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

    spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    fpr = fp / (tn + fp) if (tn + fp) > 0 else 0.0
    fnr = fn / (tp + fn) if (tp + fn) > 0 else 0.0

    # Macro & Weighted F1 for the binary early warning task
    prec_norm = tn / (tn + fn) if (tn + fn) > 0 else 0.0
    rec_norm = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    f1_norm = 2 * (prec_norm * rec_norm) / (prec_norm + rec_norm) if (prec_norm + rec_norm) > 0 else 0.0

    macro_f1 = (f1 + f1_norm) / 2.0
    weight_abn = np.sum(bin_targets == 1) / total_test
    weight_norm = np.sum(bin_targets == 0) / total_test
    weighted_f1 = (weight_abn * f1) + (weight_norm * f1_norm)

    # 3. Save test_predictions.csv
    prediction_rows = []
    for i in range(total_test):
        true_binary = "Abnormal" if bin_targets[i] == 1 else "Normal"
        pred_binary = "Abnormal" if bin_preds[i] == 1 else "Normal"
        abn_p = float(all_probs[i, 1])
        norm_p = float(all_probs[i, 0] + all_probs[i, 2]) # P(Healthy) + P(Noise)
        conf = float(np.max(all_probs[i]))
        is_corr = int(true_binary == pred_binary)
        f_record = test_ds.file_records[all_file_indices[i]]

        prediction_rows.append({
            "filepath": str(f_record["filepath"].relative_to(project_root)).replace("\\", "/"),
            "group_id": all_groups[i],
            "true_label": true_binary,
            "predicted_label": pred_binary,
            "normal_probability": round(norm_p, 4),
            "abnormal_probability": round(abn_p, 4),
            "confidence": round(conf, 4),
            "correct": is_corr,
            "original_class": f_record["label"]
        })

    with open(pred_csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["filepath", "group_id", "true_label", "predicted_label", 
                      "normal_probability", "abnormal_probability", "confidence", "correct"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in prediction_rows:
            writer.writerow({k: r[k] for k in fieldnames})

    # 4. Error Identification
    false_positives = [r for r in prediction_rows if r["true_label"] == "Normal" and r["predicted_label"] == "Abnormal"]
    false_negatives = [r for r in prediction_rows if r["true_label"] == "Abnormal" and r["predicted_label"] == "Normal"]

    top_fp = sorted(false_positives, key=lambda x: x["confidence"], reverse=True)[:5]
    top_fn = sorted(false_negatives, key=lambda x: x["confidence"], reverse=True)[:5]

    # Return structured results
    return {
        "ckpt_path": str(ckpt_path),
        "architecture": "FlockSenseResNet18 (1-Ch Log-Mel Spectrogram + LayerNorm Head)",
        "num_recordings": len(test_rows),
        "num_groups": len(test_groups),
        "num_windows": total_test,
        "num_normal_windows": int(np.sum(bin_targets == 0)),
        "num_abnormal_windows": int(np.sum(bin_targets == 1)),
        "num_normal_files": len([r for r in test_rows if r["label"] in ["Healthy", "Noise"]]),
        "num_abnormal_files": len([r for r in test_rows if r["label"] == "Unhealthy"]),
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "abnormal_sensitivity": rec,
        "specificity": spec,
        "fpr": fpr,
        "fnr": fnr,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
        "top_fp": top_fp,
        "top_fn": top_fn,
        "leakage_passed": leakage_passed,
        "train_groups_count": len(train_groups),
        "test_groups_count": len(test_groups)
    }

if __name__ == "__main__":
    res = run_comprehensive_verification()
    print(json.dumps({k: v for k, v in res.items() if not k.startswith("top")}, indent=2))
    print(f"\nTop FPs count: {len(res['top_fp'])}, Top FNs count: {len(res['top_fn'])}")
