import os
import csv
from pathlib import Path
import torch
from torch.utils.data import Dataset
import numpy as np

import sys
from pathlib import Path

# Add training folder and root to sys.path
_current_dir = Path(__file__).resolve().parent
_root_dir = _current_dir.parent
for p in [str(_current_dir), str(_root_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from audio_transforms import AudioPreprocessor, LogMelSpectrogram, AudioAugmenter

CLASS_TO_IDX = {
    "Healthy": 0,
    "Unhealthy": 1,
    "Noise": 2
}

IDX_TO_CLASS = {
    0: "Healthy",
    1: "Unhealthy",
    2: "Noise"
}

class FlockSenseDataset(Dataset):
    """
    PyTorch Dataset for FlockSense audio recordings.
    Pre-indexes fixed-duration windows (default 3.0s) from the split files.
    All windows from any file remain strictly inside the split.
    """
    def __init__(self, split_csv, project_root=".", clip_duration=3.0, target_sr=16000, 
                 hop_duration=1.5, is_training=False, augment=False, max_windows_per_file=12):
        self.project_root = Path(project_root).resolve()
        self.clip_duration = clip_duration
        self.target_sr = target_sr
        self.target_samples = int(target_sr * clip_duration)
        self.is_training = is_training
        self.augment = augment

        self.preprocessor = AudioPreprocessor(target_sr=target_sr, clip_duration=clip_duration, normalize_peak=True)
        self.mel_extractor = LogMelSpectrogram(sample_rate=target_sr, n_fft=1024, hop_length=512, n_mels=128)
        self.augmenter = AudioAugmenter() if augment else None

        # Cache waveforms in memory or load on demand
        # Since the total dataset is ~1 GB compressed audio (3.16 hours),
        # 137 min of 16kHz float32 is ~520MB uncompressed, perfectly cacheable in RAM!
        self.waveform_cache = {}
        
        self.file_records = []
        self.windows = [] # (file_idx, start_sample, duration_samples, label_idx, group_id)

        with open(split_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                filepath = self.project_root / row["filepath"]
                label_name = row["label"]
                label_idx = CLASS_TO_IDX[label_name]
                group_id = row["group_id"]
                dur = float(row["duration_seconds"])

                file_idx = len(self.file_records)
                self.file_records.append({
                    "filepath": filepath,
                    "filename": row["filename"],
                    "label": label_name,
                    "label_idx": label_idx,
                    "group_id": group_id,
                    "duration": dur
                })

                # Compute windows
                total_samples = int(dur * target_sr)
                hop_samples = int(hop_duration * target_sr)

                if total_samples <= self.target_samples:
                    # Short file: single padded window
                    self.windows.append((file_idx, 0, total_samples, label_idx, group_id))
                else:
                    # Multi-window segmentation
                    starts = list(range(0, total_samples - self.target_samples + 1, hop_samples))
                    # Ensure the end of the file is covered
                    if starts[-1] + self.target_samples < total_samples:
                        starts.append(total_samples - self.target_samples)

                    # In training, cap max windows per file to prevent very long files from dominating batches
                    if is_training and len(starts) > max_windows_per_file:
                        # Select evenly spaced windows across the recording
                        indices = np.round(np.linspace(0, len(starts) - 1, max_windows_per_file)).astype(int)
                        starts = [starts[i] for i in indices]

                    for st in starts:
                        self.windows.append((file_idx, st, self.target_samples, label_idx, group_id))

        print(f"Loaded {split_csv.name}: {len(self.file_records)} files -> {len(self.windows)} windows (Augment={augment})")

    def __len__(self):
        return len(self.windows)

    def _get_waveform(self, file_idx):
        if file_idx not in self.waveform_cache:
            path = self.file_records[file_idx]["filepath"]
            wf = self.preprocessor.load_audio(path)
            self.waveform_cache[file_idx] = wf
        return self.waveform_cache[file_idx]

    def __getitem__(self, idx):
        file_idx, start_sample, dur_samples, label_idx, group_id = self.windows[idx]
        full_wf = self._get_waveform(file_idx)

        # Extract window
        num_samples = full_wf.shape[-1]
        if num_samples <= self.target_samples:
            window = self.preprocessor.pad_or_crop(full_wf)
        else:
            end_sample = min(start_sample + self.target_samples, num_samples)
            chunk = full_wf[:, start_sample:end_sample]
            window = self.preprocessor.pad_or_crop(chunk)

        # Data augmentation (training only)
        if self.augment and self.augmenter is not None:
            window = self.augmenter.augment_waveform(window)

        # Compute Log-Mel Spectrogram
        with torch.no_grad():
            mel = self.mel_extractor(window) # [1, n_mels, time_steps]

        if self.augment and self.augmenter is not None:
            mel = self.augmenter.augment_spectrogram(mel)

        return {
            "spectrogram": mel, # [1, 128, 94]
            "label": torch.tensor(label_idx, dtype=torch.long),
            "file_idx": file_idx,
            "filename": self.file_records[file_idx]["filename"],
            "group_id": group_id
        }

    def get_class_counts(self):
        counts = {c: 0 for c in CLASS_TO_IDX.keys()}
        for _, _, _, label_idx, _ in self.windows:
            cname = IDX_TO_CLASS[label_idx]
            counts[cname] += 1
        return counts
