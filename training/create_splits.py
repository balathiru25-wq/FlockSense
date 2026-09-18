import os
import csv
import json
import random
from pathlib import Path
import numpy as np

def create_group_aware_splits(seed=42):
    random.seed(seed)
    np.random.seed(seed)

    project_root = Path(".").resolve()
    metadata_csv_path = project_root / "outputs" / "reports" / "audio_dataset_metadata.csv"
    if not metadata_csv_path.exists():
        raise FileNotFoundError(f"Missing {metadata_csv_path}. Run inspect_audio_dataset.py first.")

    with open(metadata_csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)

    print(f"Loaded {len(all_rows)} rows from metadata.")

    # Assign group_ids based on class and numerical range blocks (groups of ~7-8 consecutive clips)
    # This prevents contiguous recording sessions from bleeding across train/val/test splits.
    grouped_data = {} # group_id -> list of rows
    for row in all_rows:
        cls = row["original_class"]
        fname_stem = row["filename"].split(".")[0]
        if fname_stem.isdigit():
            idx = int(fname_stem)
            # Group into blocks of 7 consecutive files
            block_num = (idx - 1) // 7
            group_id = f"{cls}_block_{block_num:02d}"
        else:
            group_id = f"{cls}_misc"
        
        row["group_id"] = group_id
        if group_id not in grouped_data:
            grouped_data[group_id] = []
        grouped_data[group_id].append(row)

    print(f"Formed {len(grouped_data)} distinct recording session groups.")

    # Split groups per class to maintain class balance (~70% train, ~15% val, ~15% test)
    train_rows = []
    val_rows = []
    test_rows = []

    classes = sorted(list(set(r["original_class"] for r in all_rows)))
    for cls in classes:
        cls_groups = sorted([gid for gid in grouped_data.keys() if gid.startswith(cls)])
        random.shuffle(cls_groups)
        
        n_groups = len(cls_groups)
        n_test_groups = max(1, int(round(0.15 * n_groups)))
        n_val_groups = max(1, int(round(0.15 * n_groups)))
        n_train_groups = n_groups - n_test_groups - n_val_groups

        test_g = cls_groups[:n_test_groups]
        val_g = cls_groups[n_test_groups:n_test_groups + n_val_groups]
        train_g = cls_groups[n_test_groups + n_val_groups:]

        print(f"Class '{cls}': {n_groups} groups -> Train: {len(train_g)}, Val: {len(val_g)}, Test: {len(test_g)}")

        for g in train_g:
            train_rows.extend(grouped_data[g])
        for g in val_g:
            val_rows.extend(grouped_data[g])
        for g in test_g:
            test_rows.extend(grouped_data[g])

    # Ensure output directory exists
    splits_dir = project_root / "splits"
    splits_dir.mkdir(parents=True, exist_ok=True)

    # Save splits
    for name, rows in [("train", train_rows), ("validation", val_rows), ("test", test_rows)]:
        csv_path = splits_dir / f"{name}.csv"
        with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
            fieldnames = ["filepath", "filename", "label", "mapped_class", "group_id", "duration_seconds", "sample_rate"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                writer.writerow({
                    "filepath": r["filepath"],
                    "filename": r["filename"],
                    "label": r["original_class"],
                    "mapped_class": r["mapped_class"],
                    "group_id": r["group_id"],
                    "duration_seconds": r["duration_seconds"],
                    "sample_rate": r["sample_rate"]
                })
        print(f"Saved {name} split: {len(rows)} samples to {csv_path}")

    # Summary report
    summary_path = splits_dir / "splits_summary.txt"
    with open(summary_path, mode="w", encoding="utf-8") as f:
        f.write("FLOCKSENSE GROUP-AWARE DATASET SPLITS SUMMARY\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Random Seed: {seed}\n")
        f.write(f"Total files: {len(all_rows)}\n")
        f.write(f"Total groups: {len(grouped_data)}\n\n")

        for name, rows in [("TRAIN", train_rows), ("VALIDATION", val_rows), ("TEST", test_rows)]:
            dur = sum(float(r["duration_seconds"]) for r in rows)
            gids = len(set(r["group_id"] for r in rows))
            f.write(f"--- {name} SET ---\n")
            f.write(f"Total samples: {len(rows)} ({len(rows)/len(all_rows)*100:.1f}%)\n")
            f.write(f"Total duration: {dur:.1f} s ({dur/60:.1f} min)\n")
            f.write(f"Unique groups: {gids}\n")
            for cls in classes:
                c_cnt = sum(1 for r in rows if r["original_class"] == cls)
                f.write(f"  * {cls}: {c_cnt} ({c_cnt/len(rows)*100:.1f}% of split)\n")
            f.write("\n")

        # Verify strict zero-leakage between splits
        train_groups = set(r["group_id"] for r in train_rows)
        val_groups = set(r["group_id"] for r in val_rows)
        test_groups = set(r["group_id"] for r in test_rows)

        overlap_tv = train_groups.intersection(val_groups)
        overlap_tt = train_groups.intersection(test_groups)
        overlap_vt = val_groups.intersection(test_groups)

        f.write("DATA LEAKAGE VERIFICATION:\n")
        f.write(f"Train & Val Group Overlap: {len(overlap_tv)} (Expected 0)\n")
        f.write(f"Train & Test Group Overlap: {len(overlap_tt)} (Expected 0)\n")
        f.write(f"Val & Test Group Overlap: {len(overlap_vt)} (Expected 0)\n")
        assert len(overlap_tv) == 0 and len(overlap_tt) == 0 and len(overlap_vt) == 0, "Data leakage detected!"
        f.write("Zero data leakage confirmed: No recording session group appears in more than one split.\n")

    print("\nSplits summary created and zero data leakage verified.")

if __name__ == "__main__":
    create_group_aware_splits(seed=42)
