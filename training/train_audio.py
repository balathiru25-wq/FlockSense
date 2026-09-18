import os
import sys
import time
import json
import csv
import random
from pathlib import Path
import yaml
import numpy as np
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from sklearn.metrics import precision_recall_fscore_support, accuracy_score, confusion_matrix

# Ensure local imports work
_current_dir = Path(__file__).resolve().parent
_root_dir = _current_dir.parent
for p in [str(_current_dir), str(_root_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from audio_dataset import FlockSenseDataset, CLASS_TO_IDX, IDX_TO_CLASS
from models import FlockSenseResNet18

def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

def calculate_class_weights(dataset, num_classes=3):
    counts = dataset.get_class_counts()
    total = sum(counts.values())
    weights = []
    for idx in range(num_classes):
        cname = IDX_TO_CLASS[idx]
        cnt = counts.get(cname, 1)
        w = total / (num_classes * cnt)
        weights.append(w)
    return torch.tensor(weights, dtype=torch.float32)

def train_one_epoch(model, dataloader, criterion, optimizer, device):
    model.train()
    running_loss = 0.0
    all_preds = []
    all_targets = []

    for batch in dataloader:
        specs = batch["spectrogram"].to(device)
        labels = batch["label"].to(device)

        optimizer.zero_grad()
        logits = model(specs)
        loss = criterion(logits, labels)
        loss.backward()
        
        # Gradient clipping for stability
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
        optimizer.step()

        running_loss += loss.item() * specs.size(0)
        preds = torch.argmax(logits, dim=1)
        all_preds.extend(preds.cpu().numpy())
        all_targets.extend(labels.cpu().numpy())

    epoch_loss = running_loss / len(dataloader.dataset)
    epoch_acc = accuracy_score(all_targets, all_preds)
    return epoch_loss, epoch_acc

def evaluate(model, dataloader, criterion, device):
    model.eval()
    running_loss = 0.0
    all_preds = []
    all_targets = []
    all_probs = []

    with torch.no_grad():
        for batch in dataloader:
            specs = batch["spectrogram"].to(device)
            labels = batch["label"].to(device)

            logits = model(specs)
            loss = criterion(logits, labels)

            running_loss += loss.item() * specs.size(0)
            probs = torch.softmax(logits, dim=1)
            preds = torch.argmax(logits, dim=1)

            all_preds.extend(preds.cpu().numpy())
            all_targets.extend(labels.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())

    val_loss = running_loss / len(dataloader.dataset)
    acc = accuracy_score(all_targets, all_preds)
    
    # Per-class and macro metrics
    precision, recall, f1, support = precision_recall_fscore_support(
        all_targets, all_preds, labels=[0, 1, 2], zero_division=0
    )
    macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(
        all_targets, all_preds, average="macro", zero_division=0
    )
    weighted_f1 = precision_recall_fscore_support(
        all_targets, all_preds, average="weighted", zero_division=0
    )[2]

    # Abnormal is class index 1 (Unhealthy)
    abnormal_recall = recall[1]
    abnormal_precision = precision[1]
    abnormal_f1 = f1[1]

    metrics = {
        "val_loss": val_loss,
        "accuracy": acc,
        "macro_precision": macro_p,
        "macro_recall": macro_r,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "abnormal_recall": abnormal_recall,
        "abnormal_precision": abnormal_precision,
        "abnormal_f1": abnormal_f1,
        "per_class_precision": precision.tolist(),
        "per_class_recall": recall.tolist(),
        "per_class_f1": f1.tolist()
    }
    return metrics

def plot_training_history(history, output_dir):
    epochs = [h["epoch"] for h in history]
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("FlockSense Audio AI — Training & Validation Progression", fontsize=14, fontweight="bold")

    # 1. Loss
    ax = axes[0, 0]
    ax.plot(epochs, [h["train_loss"] for h in history], label="Train Loss", color="royalblue", lw=2)
    ax.plot(epochs, [h["val_loss"] for h in history], label="Validation Loss", color="crimson", lw=2)
    ax.set_title("Training vs Validation Loss", fontweight="semibold")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss (Weighted CrossEntropy)")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.5)

    # 2. Accuracy
    ax = axes[0, 1]
    ax.plot(epochs, [h["train_acc"] * 100 for h in history], label="Train Accuracy", color="royalblue", lw=2)
    ax.plot(epochs, [h["val_acc"] * 100 for h in history], label="Validation Accuracy", color="forestgreen", lw=2)
    ax.set_title("Training vs Validation Accuracy (%)", fontweight="semibold")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Accuracy (%)")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.5)

    # 3. Validation Macro F1
    ax = axes[1, 0]
    ax.plot(epochs, [h["val_macro_f1"] * 100 for h in history], label="Macro F1", color="darkorange", lw=2)
    ax.plot(epochs, [h["val_weighted_f1"] * 100 for h in history], label="Weighted F1", color="purple", lw=1.5, linestyle=":")
    ax.set_title("Validation F1-Score Across Epochs (%)", fontweight="semibold")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("F1 Score (%)")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.5)

    # 4. Validation Abnormal Sensitivity / Recall (Class 1)
    ax = axes[1, 1]
    ax.plot(epochs, [h["val_abnormal_recall"] * 100 for h in history], label="Abnormal Recall (Sensitivity)", color="crimson", lw=2.5)
    ax.plot(epochs, [h["val_abnormal_f1"] * 100 for h in history], label="Abnormal F1", color="orchid", lw=1.5, linestyle="--")
    ax.set_title("Abnormal (Unhealthy) Recall / Sensitivity across Epochs (%)", fontweight="semibold")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Recall (%)")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    plot_path = Path(output_dir) / "flocksense_training_progression.png"
    plt.savefig(plot_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved training progression plot to: {plot_path}")

def run_training():
    project_root = Path(".").resolve()
    config_path = project_root / "config" / "audio_config.yaml"
    mapping_path = project_root / "config" / "audio_class_mapping.json"

    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    with open(mapping_path, "r") as f:
        class_mapping = json.load(f)

    seed = cfg.get("seed", 42)
    set_seed(seed)

    # Detect compute device
    if torch.cuda.is_available():
        device = torch.device("cuda")
        dev_name = torch.cuda.get_device_name(0)
        print(f"Training device: CUDA - {dev_name}")
    else:
        device = torch.device("cpu")
        print("Training device: CPU")

    # Datasets and loaders
    train_csv = project_root / "splits" / "train.csv"
    val_csv = project_root / "splits" / "validation.csv"
    
    print("\n--- Initializing Datasets ---")
    train_ds = FlockSenseDataset(
        train_csv, project_root=project_root, clip_duration=cfg["audio"]["clip_duration_seconds"],
        target_sr=cfg["audio"]["target_sample_rate"], is_training=True, augment=True
    )
    val_ds = FlockSenseDataset(
        val_csv, project_root=project_root, clip_duration=cfg["audio"]["clip_duration_seconds"],
        target_sr=cfg["audio"]["target_sample_rate"], is_training=False, augment=False
    )

    batch_size = cfg["training"]["batch_size"]
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0, drop_last=True, pin_memory=torch.cuda.is_available())
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0, drop_last=False, pin_memory=torch.cuda.is_available())

    # Model
    model = FlockSenseResNet18(
        num_classes=cfg["model"]["num_classes"],
        pretrained=cfg["model"]["pretrained"],
        dropout=cfg["model"]["dropout"]
    ).to(device)

    tot_p, trn_p = model.count_parameters()
    print(f"Model: {cfg['model']['architecture'].upper()} (Total params: {tot_p:,}, Trainable: {trn_p:,})")

    # Loss with class weighting
    class_weights = calculate_class_weights(train_ds, num_classes=3).to(device)
    print(f"Class weights (Healthy, Unhealthy, Noise): {[round(w, 3) for w in class_weights.tolist()]}")
    criterion = nn.CrossEntropyLoss(weight=class_weights)

    # Optimizer & Scheduler
    lr = float(cfg["training"]["learning_rate"])
    weight_decay = float(cfg["training"]["weight_decay"])
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    epochs = cfg["training"]["epochs"]
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)

    # Output paths
    models_dir = project_root / cfg["training"]["checkpoint_dir"]
    models_dir.mkdir(parents=True, exist_ok=True)
    best_model_path = models_dir / cfg["training"]["best_model_name"]
    
    reports_dir = project_root / "outputs" / "reports"
    graphs_dir = project_root / "outputs" / "graphs"
    reports_dir.mkdir(parents=True, exist_ok=True)
    graphs_dir.mkdir(parents=True, exist_ok=True)

    # Training loop
    history = []
    best_score = -1.0
    best_epoch = -1
    best_metrics = None
    patience = cfg["training"]["early_stopping_patience"]
    patience_counter = 0

    print("\n" + "=" * 80)
    print(f"{'Epoch':<6}{'Tr Loss':<10}{'Val Loss':<10}{'Tr Acc':<9}{'Val Acc':<9}{'Abn Rec':<10}{'Macro F1':<10}{'LR':<10}")
    print("=" * 80)

    for epoch in range(1, epochs + 1):
        t0 = time.time()
        tr_loss, tr_acc = train_one_epoch(model, train_loader, criterion, optimizer, device)
        val_metrics = evaluate(model, val_loader, criterion, device)
        scheduler.step()
        curr_lr = optimizer.param_groups[0]["lr"]

        elapsed = time.time() - t0

        row = {
            "epoch": epoch,
            "train_loss": round(tr_loss, 4),
            "train_acc": round(tr_acc, 4),
            "val_loss": round(val_metrics["val_loss"], 4),
            "val_acc": round(val_metrics["accuracy"], 4),
            "val_abnormal_recall": round(val_metrics["abnormal_recall"], 4),
            "val_abnormal_precision": round(val_metrics["abnormal_precision"], 4),
            "val_abnormal_f1": round(val_metrics["abnormal_f1"], 4),
            "val_macro_f1": round(val_metrics["macro_f1"], 4),
            "val_weighted_f1": round(val_metrics["weighted_f1"], 4),
            "lr": round(curr_lr, 6)
        }
        history.append(row)

        print(f"{epoch:<6}{tr_loss:<10.4f}{val_metrics['val_loss']:<10.4f}{tr_acc*100:<8.2f}%{val_metrics['accuracy']*100:<8.2f}%{val_metrics['abnormal_recall']*100:<9.2f}%{val_metrics['macro_f1']*100:<9.2f}%{curr_lr:<10.6f}")

        # Model selection metric emphasizing abnormal recall & macro F1
        # Combined composite score: 0.6 * abnormal_recall + 0.4 * macro_f1
        composite_score = 0.6 * val_metrics["abnormal_recall"] + 0.4 * val_metrics["macro_f1"]

        if composite_score > best_score:
            best_score = composite_score
            best_epoch = epoch
            best_metrics = val_metrics
            patience_counter = 0

            # Save full checkpoint
            checkpoint = {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "best_score": best_score,
                "val_metrics": val_metrics,
                "model_architecture": "FlockSenseResNet18",
                "class_names": class_mapping["original_classes"],
                "class_to_idx": CLASS_TO_IDX,
                "idx_to_class": IDX_TO_CLASS,
                "audio_config": cfg["audio"],
                "spectrogram_config": cfg["spectrogram"],
                "risk_thresholds": cfg["risk_thresholds"],
                "seed": seed
            }
            torch.save(checkpoint, best_model_path)
            print(f"  --> Saved new best checkpoint at epoch {epoch} (Abnormal Recall: {val_metrics['abnormal_recall']*100:.2f}%, Macro F1: {val_metrics['macro_f1']*100:.2f}%)")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"\nEarly stopping triggered after {epoch} epochs (no improvement for {patience} epochs).")
                break

    print("=" * 80)
    print(f"Training completed. Best model found at Epoch {best_epoch} with Composite Score {best_score:.4f}")
    print(f"Best Validation Metrics:")
    print(f"  - Accuracy:        {best_metrics['accuracy']*100:.2f}%")
    print(f"  - Macro F1:        {best_metrics['macro_f1']*100:.2f}%")
    print(f"  - Abnormal Recall: {best_metrics['abnormal_recall']*100:.2f}% (Sensitivity)")
    print(f"  - Abnormal F1:     {best_metrics['abnormal_f1']*100:.2f}%")
    print(f"Saved best model to: {best_model_path}")

    # Save training history CSV
    history_csv = reports_dir / "training_history.csv"
    with open(history_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(history[0].keys()))
        writer.writeheader()
        writer.writerows(history)
    print(f"Saved training history CSV to: {history_csv}")

    # Plot graphs
    plot_training_history(history, graphs_dir)

if __name__ == "__main__":
    run_training()
