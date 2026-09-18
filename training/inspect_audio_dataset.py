import os
import sys
import glob
import hashlib
import json
import csv
import math
from pathlib import Path
import soundfile as sf
import numpy as np

def find_dataset_root(search_dir="."):
    """Finds the dataset directory recursively."""
    for root, dirs, files in os.walk(search_dir):
        if "Chicken_Audio_Dataset" in dirs:
            return Path(root) / "Chicken_Audio_Dataset"
    # Fallback to direct check
    for p in Path(search_dir).glob("**/Chicken_Audio_Dataset"):
        if p.is_dir():
            return p
    return None

def compute_file_hash(filepath):
    """Computes SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def inspect_dataset():
    project_root = Path(".").resolve()
    print("=" * 60)
    print("FlockSense — Audio Dataset Inspector")
    print("=" * 60)
    
    dataset_root = find_dataset_root(project_root)
    if not dataset_root or not dataset_root.exists():
        print(f"ERROR: Could not locate 'Chicken_Audio_Dataset' under {project_root}")
        sys.exit(1)
        
    rel_dataset_path = dataset_root.relative_to(project_root)
    print(f"Dataset location: {dataset_root}")
    print(f"Project-relative path: {rel_dataset_path}\n")

    # Ensure output directories exist
    reports_dir = project_root / "outputs" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    # Check for metadata files in dataset parent directories
    metadata_files = []
    curr = dataset_root
    while curr != project_root.parent and curr != project_root:
        for ext in ["*.csv", "*.json", "*.txt", "*.xlsx", "*.tsv"]:
            metadata_files.extend(list(curr.glob(ext)))
        curr = curr.parent

    # Collect all audio files
    audio_extensions = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
    all_audio_paths = []
    for ext in audio_extensions:
        all_audio_paths.extend(dataset_root.rglob(f"*{ext}"))
        all_audio_paths.extend(dataset_root.rglob(f"*{ext.upper()}"))
    all_audio_paths = sorted(list(set(all_audio_paths)))

    print(f"Total audio files found: {len(all_audio_paths)}")
    
    classes = sorted([d.name for d in dataset_root.iterdir() if d.is_dir()])
    print(f"Classes (subdirectories): {classes}\n")

    metadata_rows = []
    hash_to_files = {}
    class_counts = {c: 0 for c in classes}
    sample_rates = {}
    channel_counts = {}
    durations = []
    file_sizes = []
    corrupted_files = []
    empty_files = []
    short_files = [] # < 0.5s

    for audio_path in all_audio_paths:
        filename = audio_path.name
        parent_folder = audio_path.parent.name
        ext = audio_path.suffix.lower()
        file_size = audio_path.stat().st_size
        file_sizes.append(file_size)
        original_class = parent_folder
        if original_class in class_counts:
            class_counts[original_class] += 1
            
        # Map class for FlockSense early-warning context
        # Healthy -> NORMAL
        # Unhealthy -> ABNORMAL
        # Noise -> NOISE / NON_VOCAL (or background)
        if original_class.lower() == "healthy":
            mapped_class = "NORMAL"
        elif original_class.lower() == "unhealthy":
            mapped_class = "ABNORMAL"
        elif original_class.lower() == "noise":
            mapped_class = "NOISE"
        else:
            mapped_class = "UNKNOWN"

        file_hash = compute_file_hash(audio_path)
        if file_hash not in hash_to_files:
            hash_to_files[file_hash] = []
        hash_to_files[file_hash].append(str(audio_path.relative_to(project_root)))

        validity = "VALID"
        duration = 0.0
        sr = 0
        channels = 0

        if file_size == 0:
            validity = "EMPTY_FILE"
            empty_files.append(str(audio_path))
        else:
            try:
                info = sf.info(str(audio_path))
                duration = info.duration
                sr = info.samplerate
                channels = info.channels
                durations.append(duration)
                sample_rates[sr] = sample_rates.get(sr, 0) + 1
                channel_counts[channels] = channel_counts.get(channels, 0) + 1

                if duration < 0.5:
                    short_files.append((str(audio_path), duration))
            except Exception as e:
                validity = f"CORRUPTED: {str(e)}"
                corrupted_files.append((str(audio_path), str(e)))

        # Potential group identifier
        # In this dataset, files are 1.wav, 2.wav, etc. inside Healthy, Noise, Unhealthy.
        # We also check if duplicate hashes exist across or within folders.
        group_id = f"{parent_folder}_{filename.split('.')[0]}"
        
        metadata_rows.append({
            "filepath": str(audio_path.relative_to(project_root)).replace("\\", "/"),
            "filename": filename,
            "parent_folder": parent_folder,
            "original_class": original_class,
            "mapped_class": mapped_class,
            "duration_seconds": round(duration, 4),
            "sample_rate": sr,
            "channels": channels,
            "extension": ext,
            "file_size_bytes": file_size,
            "sha256": file_hash,
            "recording_group": group_id,
            "validity_status": validity
        })

    # Find duplicates
    exact_duplicates = {h: paths for h, paths in hash_to_files.items() if len(paths) > 1}

    # Duration stats
    durations_arr = np.array(durations) if durations else np.array([0])
    min_dur = float(np.min(durations_arr))
    max_dur = float(np.max(durations_arr))
    mean_dur = float(np.mean(durations_arr))
    median_dur = float(np.median(durations_arr))
    total_dur = float(np.sum(durations_arr))

    # Save metadata CSV
    metadata_csv_path = reports_dir / "audio_dataset_metadata.csv"
    with open(metadata_csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "filepath", "filename", "parent_folder", "original_class", "mapped_class",
            "duration_seconds", "sample_rate", "channels", "extension",
            "file_size_bytes", "sha256", "recording_group", "validity_status"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(metadata_rows)

    print(f"Saved metadata CSV to: {metadata_csv_path}")

    # Generate comprehensive report text
    report_path = reports_dir / "audio_dataset_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("FLOCKSENSE AUDIO DATASET INSPECTION REPORT\n")
        f.write("=" * 70 + "\n\n")
        
        f.write(f"1. DATASET LOCATION:\n")
        f.write(f"   Absolute Path: {dataset_root}\n")
        f.write(f"   Project-Relative: {rel_dataset_path}\n\n")
        
        f.write(f"2. OVERVIEW & TOTALS:\n")
        f.write(f"   Total Audio Files: {len(all_audio_paths)}\n")
        f.write(f"   Total Duration: {total_dur:.2f} seconds ({total_dur/60:.2f} minutes, {total_dur/3600:.2f} hours)\n")
        f.write(f"   Total Dataset Size: {sum(file_sizes) / (1024*1024):.2f} MB\n\n")

        f.write(f"3. CLASS DISTRIBUTION:\n")
        for c, cnt in class_counts.items():
            pct = (cnt / len(all_audio_paths) * 100) if all_audio_paths else 0
            f.write(f"   - {c}: {cnt} files ({pct:.1f}%)\n")
        f.write("\n")

        f.write(f"4. TASK FORMULATION:\n")
        f.write("   The dataset contains 3 primary categories: 'Healthy', 'Unhealthy', 'Noise'.\n")
        f.write("   In the FlockSense early-warning framework:\n")
        f.write("   - Healthy -> NORMAL flock vocalization baseline\n")
        f.write("   - Unhealthy -> ABNORMAL flock vocalization (acoustic anomaly / symptoms)\n")
        f.write("   - Noise -> Farm background sound (feeders, fans, machinery, environmental)\n")
        f.write("   The core model can learn a 3-class classifier or a targeted NORMAL vs ABNORMAL detector\n")
        f.write("   with NOISE either as an explicit rejection/environmental class or separate category.\n\n")

        f.write(f"5. DURATION STATISTICS:\n")
        f.write(f"   Minimum Duration: {min_dur:.4f} s\n")
        f.write(f"   Maximum Duration: {max_dur:.4f} s\n")
        f.write(f"   Mean Duration:    {mean_dur:.4f} s\n")
        f.write(f"   Median Duration:  {median_dur:.4f} s\n\n")

        f.write(f"6. AUDIO ENCODING & FORMATS:\n")
        f.write(f"   Sample Rate Distribution:\n")
        for sr, cnt in sample_rates.items():
            f.write(f"     * {sr} Hz: {cnt} files ({cnt/len(all_audio_paths)*100:.1f}%)\n")
        f.write(f"   Channel Distribution:\n")
        for ch, cnt in channel_counts.items():
            ch_name = "Mono (1)" if ch == 1 else ("Stereo (2)" if ch == 2 else f"{ch} channels")
            f.write(f"     * {ch_name}: {cnt} files ({cnt/len(all_audio_paths)*100:.1f}%)\n")
        f.write("\n")

        f.write(f"7. DATASET INTEGRITY & ANOMALIES:\n")
        f.write(f"   Corrupted / Undecodable Files: {len(corrupted_files)}\n")
        if corrupted_files:
            for path, err in corrupted_files:
                f.write(f"     - {path}: {err}\n")
        f.write(f"   Empty Files (0 bytes): {len(empty_files)}\n")
        f.write(f"   Extremely Short Files (< 0.5s): {len(short_files)}\n")
        if short_files:
            for path, dur in short_files[:10]:
                f.write(f"     - {path}: {dur:.3f} s\n")
            if len(short_files) > 10:
                f.write(f"     ... and {len(short_files) - 10} more\n")
        f.write("\n")

        f.write(f"8. DUPLICATE & GROUP DETECTION:\n")
        f.write(f"   Exact File Hash Duplicates: {len(exact_duplicates)} groups\n")
        if exact_duplicates:
            for h, paths in exact_duplicates.items():
                f.write(f"     - Hash {h[:12]}... duplicated across:\n")
                for p in paths:
                    f.write(f"         {p}\n")
        else:
            f.write("     None found.\n")
        f.write("\n")

        f.write(f"9. METADATA FILES FOUND IN REPOSITORY:\n")
        if metadata_files:
            for mf in metadata_files:
                f.write(f"   - {mf}\n")
        else:
            f.write("   No external metadata files (CSV/JSON/Excel) found in dataset directory.\n")
        f.write("\n")

    print(f"Saved dataset report to: {report_path}")
    print("\nDataset inspection completed successfully!")

if __name__ == "__main__":
    inspect_dataset()
