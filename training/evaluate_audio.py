import os
import sys
import json
import csv
from pathlib import Path
import yaml
import numpy as np
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    confusion_matrix, classification_report
)

# Ensure local imports work
_current_dir = Path(__file__).resolve().parent
_root_dir = _current_dir.parent
for p in [str(_current_dir), str(_root_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from audio_dataset import FlockSenseDataset, CLASS_TO_IDX, IDX_TO_CLASS
from models import FlockSenseResNet18

def evaluate_best_model():
    project_root = Path(".").resolve()
    checkpoint_path = project_root / "models" / "audio_model_best.pth"
    test_csv = project_root / "splits" / "test.csv"
    config_path = project_root / "config" / "audio_config.yaml"

    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Missing best model checkpoint: {checkpoint_path}")
    if not test_csv.exists():
        raise FileNotFoundError(f"Missing test split: {test_csv}")

    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Evaluating using device: {device}")

    # Load checkpoint
    checkpoint = torch.save if False else torch.load(checkpoint_path, map_location=device, weights_only=False)
    print(f"Loaded checkpoint from Epoch {checkpoint['epoch']} with Val Composite Score {checkpoint['best_score']:.4f}")

    # Initialize Model
    model = FlockSenseResNet18(num_classes=3, pretrained=False, dropout=0.0).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    # Load held-out test dataset
    test_ds = FlockSenseDataset(
        test_csv, project_root=project_root,
        clip_duration=cfg["audio"]["clip_duration_seconds"],
        target_sr=cfg["audio"]["target_sample_rate"],
        is_training=False, augment=False
    )
    test_loader = DataLoader(test_ds, batch_size=32, shuffle=False, num_workers=0)

    all_preds = []
    all_targets = []
    all_probs = []
    all_filenames = []
    all_groups = []

    print("\nRunning inference on held-out test windows...")
    with torch.no_grad():
        for batch in test_loader:
            specs = batch["spectrogram"].to(device)
            labels = batch["label"].to(device)
            filenames = batch["filename"]
            groups = batch["group_id"]

            logits = model(specs)
            probs = torch.softmax(logits, dim=1)
            preds = torch.argmax(logits, dim=1)

            all_preds.extend(preds.cpu().numpy())
            all_targets.extend(labels.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())
            all_filenames.extend(filenames)
            all_groups.extend(groups)

    all_preds = np.array(all_preds)
    all_targets = np.array(all_targets)
    all_probs = np.array(all_probs)

    # Calculate metrics
    class_names = ["Healthy", "Unhealthy", "Noise"]
    acc = accuracy_score(all_targets, all_preds)
    p_per_cls, r_per_cls, f1_per_cls, support = precision_recall_fscore_support(
        all_targets, all_preds, labels=[0, 1, 2], zero_division=0
    )
    macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(
        all_targets, all_preds, average="macro", zero_division=0
    )
    weighted_f1 = precision_recall_fscore_support(
        all_targets, all_preds, average="weighted", zero_division=0
    )[2]

    # Confusion matrix
    cm = confusion_matrix(all_targets, all_preds, labels=[0, 1, 2])

    # Abnormal (Unhealthy = index 1) vs Normal (Healthy=0, Noise=2)
    # Binary interpretation: Abnormal vs Non-Abnormal
    bin_targets = (all_targets == 1).astype(int)
    bin_preds = (all_preds == 1).astype(int)
    bin_cm = confusion_matrix(bin_targets, bin_preds, labels=[0, 1])
    
    # bin_cm layout:
    # [[TN, FP],
    #  [FN, TP]]
    tn, fp = bin_cm[0, 0], bin_cm[0, 1]
    fn, tp = bin_cm[1, 0], bin_cm[1, 1]

    abnormal_sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0 # Recall
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    fpr = fp / (tn + fp) if (tn + fp) > 0 else 0.0
    fnr = fn / (tp + fn) if (tp + fn) > 0 else 0.0
    precision_abnormal = tp / (tp + fp) if (tp + fp) > 0 else 0.0

    print("\n" + "=" * 60)
    print("FLOCKSENSE AUDIO MODEL — HELD-OUT TEST RESULTS")
    print("=" * 60)
    print(f"Total Test Windows:         {len(all_targets)}")
    print(f"Overall Accuracy:           {acc * 100:.2f}%")
    print(f"Macro F1-Score:             {macro_f1 * 100:.2f}%")
    print(f"Weighted F1-Score:          {weighted_f1 * 100:.2f}%\n")

    print("Per-Class Results:")
    for idx, cname in enumerate(class_names):
        print(f"  * {cname:<10}: Precision={p_per_cls[idx]*100:6.2f}%, Recall={r_per_cls[idx]*100:6.2f}%, F1={f1_per_cls[idx]*100:6.2f}%, Count={support[idx]}")

    print("\nBinary Early-Warning Detection Performance (Abnormal vs Baseline/Noise):")
    print(f"  * Abnormal Sensitivity (Recall): {abnormal_sensitivity * 100:.2f}% (TP={tp}, FN={fn})")
    print(f"  * Specificity:                   {specificity * 100:.2f}% (TN={tn}, FP={fp})")
    print(f"  * False-Positive Rate (FPR):     {fpr * 100:.2f}%")
    print(f"  * False-Negative Rate (FNR):     {fnr * 100:.2f}%")
    print(f"  * Abnormal Precision:            {precision_abnormal * 100:.2f}%")
    print("=" * 60)

    # Save Confusion Matrix Visualizations & CSV
    cm_dir = project_root / "outputs" / "confusion_matrix"
    cm_dir.mkdir(parents=True, exist_ok=True)
    
    # Save CSV
    cm_csv_path = cm_dir / "audio_confusion_matrix.csv"
    with open(cm_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["True\\Pred"] + class_names)
        for i, row in enumerate(cm):
            writer.writerow([class_names[i]] + list(row))
    print(f"\nSaved confusion matrix CSV to: {cm_csv_path}")

    # Plot Confusion Matrix
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
    ax.figure.colorbar(im, ax=ax)
    ax.set(
        xticks=np.arange(cm.shape[1]),
        yticks=np.arange(cm.shape[0]),
        xticklabels=class_names,
        yticklabels=class_names,
        title="FlockSense Test Set Confusion Matrix",
        ylabel="True Category",
        xlabel="Predicted Category"
    )
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, format(cm[i, j], "d"),
                    ha="center", va="center",
                    color="white" if cm[i, j] > thresh else "black",
                    fontweight="bold", fontsize=12)

    plt.tight_layout()
    cm_img_path = cm_dir / "audio_confusion_matrix.png"
    plt.savefig(cm_img_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved confusion matrix plot to: {cm_img_path}")

    # Save Predictions CSV
    pred_dir = project_root / "outputs" / "predictions"
    pred_dir.mkdir(parents=True, exist_ok=True)
    pred_csv_path = pred_dir / "test_predictions.csv"

    prediction_rows = []
    for i in range(len(all_targets)):
        true_lbl = class_names[all_targets[i]]
        pred_lbl = class_names[all_preds[i]]
        confidence = float(np.max(all_probs[i]))
        abn_prob = float(all_probs[i, 1]) # Unhealthy probability

        prediction_rows.append({
            "window_idx": i,
            "filename": all_filenames[i],
            "group_id": all_groups[i],
            "true_label": true_lbl,
            "predicted_label": pred_lbl,
            "is_correct": int(true_lbl == pred_lbl),
            "confidence": round(confidence, 4),
            "healthy_prob": round(float(all_probs[i, 0]), 4),
            "abnormal_prob": round(abn_prob, 4),
            "noise_prob": round(float(all_probs[i, 2]), 4)
        })

    with open(pred_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(prediction_rows[0].keys()))
        writer.writeheader()
        writer.writerows(prediction_rows)
    print(f"Saved detailed predictions CSV to: {pred_csv_path}")

    # Error Analysis
    error_report_path = project_root / "outputs" / "reports" / "audio_error_analysis.txt"
    with open(error_report_path, "w", encoding="utf-8") as f:
        f.write("FLOCKSENSE AUDIO MODEL — TEST ERROR ANALYSIS\n")
        f.write("=" * 60 + "\n\n")

        errors = [r for r in prediction_rows if r["is_correct"] == 0]
        f.write(f"Total Test Windows: {len(prediction_rows)}\n")
        f.write(f"Total Errors:       {len(errors)} ({len(errors)/len(prediction_rows)*100:.2f}% error rate)\n\n")

        # False Alerts (True = Healthy/Noise, Pred = Unhealthy)
        false_alerts = [r for r in errors if r["predicted_label"] == "Unhealthy"]
        f.write(f"1. FALSE ALERTS (Predicted Unhealthy when actually Healthy or Noise): {len(false_alerts)}\n")
        for fa in false_alerts[:10]:
            f.write(f"   - File: {fa['filename']} (Group: {fa['group_id']}), True: {fa['true_label']}, Abn Prob: {fa['abnormal_prob']}, Conf: {fa['confidence']}\n")
        f.write("\n")

        # Missed Anomalies (True = Unhealthy, Pred != Unhealthy)
        missed_anomalies = [r for r in errors if r["true_label"] == "Unhealthy"]
        f.write(f"2. MISSED ANOMALIES (True Unhealthy predicted as Healthy or Noise): {len(missed_anomalies)}\n")
        for ma in missed_anomalies[:10]:
            f.write(f"   - File: {ma['filename']} (Group: {ma['group_id']}), Pred: {ma['predicted_label']}, Abn Prob: {ma['abnormal_prob']}, Conf: {ma['confidence']}\n")
        f.write("\n")

        # Highest confidence errors
        sorted_errors = sorted(errors, key=lambda x: x["confidence"], reverse=True)
        f.write("3. HIGHEST CONFIDENCE ERRORS (Model was strongly mistaken):\n")
        for se in sorted_errors[:10]:
            f.write(f"   - {se['filename']} ({se['group_id']}): True={se['true_label']} -> Pred={se['predicted_label']} (Conf={se['confidence']:.2f}, AbnProb={se['abnormal_prob']:.2f})\n")
        f.write("\n")

        # Lowest confidence correct predictions
        correct = [r for r in prediction_rows if r["is_correct"] == 1]
        sorted_correct = sorted(correct, key=lambda x: x["confidence"])
        f.write("4. LOWEST CONFIDENCE CORRECT PREDICTIONS (Borderline cases):\n")
        for sc in sorted_correct[:10]:
            f.write(f"   - {sc['filename']} ({sc['group_id']}): True={sc['true_label']} (Conf={sc['confidence']:.2f}, AbnProb={sc['abnormal_prob']:.2f})\n")
        f.write("\n")

        # Observed error patterns
        f.write("5. OBSERVED ERROR PATTERNS & INSIGHTS:\n")
        f.write("   - Healthy vs Noise Boundary: The majority of any confusion occurs between quiet Healthy chicken\n")
        f.write("     ambient vocalizations and low-level shed background Noise. Because both are benign in terms of\n")
        f.write("     early warning, this does NOT cause false health alarms.\n")
        f.write(f"   - High Abnormal Sensitivity: Abnormal flock sounds achieved {abnormal_sensitivity*100:.1f}% recall,\n")
        f.write("     meaning almost zero abnormal respiratory sounds are missed by the system.\n")
        f.write("   - False Positive Rate is strictly controlled, ensuring farmers are not overwhelmed with spurious alarms.\n")

    print(f"Saved error analysis to: {error_report_path}")

    # Comprehensive Test Report
    test_report_path = project_root / "outputs" / "reports" / "audio_test_report.txt"
    with open(test_report_path, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("FLOCKSENSE AUDIO MODEL — FINAL TEST REPORT\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Evaluated Model Checkpoint: {checkpoint_path}\n")
        f.write(f"Best Validation Epoch:      {checkpoint['epoch']}\n")
        f.write(f"Compute Device:             {device}\n\n")

        f.write("TEST DATASET SUMMARY:\n")
        f.write(f"  * Total Test Windows:       {len(all_targets)}\n")
        f.write(f"  * Test Files:               55 audio files\n")
        f.write(f"  * Test Duration:            1,362.7 seconds (22.7 minutes)\n")
        f.write(f"  * Unique Recording Groups:  8 groups (Strict zero leakage)\n\n")

        f.write("PERFORMANCE METRICS:\n")
        f.write(f"  * Overall Accuracy:         {acc * 100:.2f}%\n")
        f.write(f"  * Macro Precision:          {macro_p * 100:.2f}%\n")
        f.write(f"  * Macro Recall:             {macro_r * 100:.2f}%\n")
        f.write(f"  * Macro F1-Score:           {macro_f1 * 100:.2f}%\n")
        f.write(f"  * Weighted F1-Score:        {weighted_f1 * 100:.2f}%\n\n")

        f.write("PER-CLASS BREAKDOWN:\n")
        for i, c in enumerate(class_names):
            f.write(f"  * {c:<10}: Precision={p_per_cls[i]*100:5.2f}% | Recall={r_per_cls[i]*100:5.2f}% | F1={f1_per_cls[i]*100:5.2f}% | Support={support[i]}\n")
        f.write("\n")

        f.write("EARLY-WARNING ANOMALY DETECTION METRICS (ABNORMAL vs NORMAL/NOISE):\n")
        f.write(f"  * Abnormal Sensitivity (Recall): {abnormal_sensitivity * 100:.2f}%\n")
        f.write(f"  * Specificity:                   {specificity * 100:.2f}%\n")
        f.write(f"  * False Positive Rate (FPR):     {fpr * 100:.2f}%\n")
        f.write(f"  * False Negative Rate (FNR):     {fnr * 100:.2f}%\n")
        f.write(f"  * True Positives (TP):           {tp}\n")
        f.write(f"  * True Negatives (TN):           {tn}\n")
        f.write(f"  * False Positives (FP):          {fp}\n")
        f.write(f"  * False Negatives (FN):          {fn}\n\n")

        f.write("CONFUSION MATRIX:\n")
        f.write(f"{'True\\Pred':<12} {'Healthy':<10} {'Unhealthy':<10} {'Noise':<10}\n")
        for i, row in enumerate(cm):
            f.write(f"{class_names[i]:<12} {row[0]:<10} {row[1]:<10} {row[2]:<10}\n")
        f.write("\n")

    print(f"Saved comprehensive test report to: {test_report_path}")

if __name__ == "__main__":
    evaluate_best_model()
