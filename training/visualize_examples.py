import os
import sys
import csv
from pathlib import Path
import torch
import matplotlib.pyplot as plt
import numpy as np

from audio_transforms import AudioPreprocessor, LogMelSpectrogram

def generate_example_visualizations():
    project_root = Path(".").resolve()
    splits_csv = project_root / "splits" / "train.csv"
    if not splits_csv.exists():
        print("Missing splits/train.csv. Run create_splits.py first.")
        return

    with open(splits_csv, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Pick 1 sample for each class
    sample_per_class = {}
    for r in rows:
        cls = r["label"]
        if cls not in sample_per_class:
            sample_per_class[cls] = r
        if len(sample_per_class) == 3:
            break

    preprocessor = AudioPreprocessor(target_sr=16000, clip_duration=3.0)
    mel_extractor = LogMelSpectrogram(sample_rate=16000, n_fft=1024, hop_length=512, n_mels=128)

    examples_dir = project_root / "outputs" / "examples"
    examples_dir.mkdir(parents=True, exist_ok=True)

    plt.style.use("default")
    fig, axes = plt.subplots(3, 2, figsize=(14, 10))
    fig.suptitle("FlockSense Bioacoustic Representations (Waveform & Log-Mel Spectrogram)", fontsize=14, fontweight="bold")

    class_order = ["Healthy", "Unhealthy", "Noise"]
    color_map = {"Healthy": "forestgreen", "Unhealthy": "crimson", "Noise": "royalblue"}
    early_warning_status = {"Healthy": "NORMAL (Flock Baseline)", "Unhealthy": "ABNORMAL (Acoustic Anomaly / Distress)", "Noise": "NORMAL (Ambient Shed Equipment)"}

    for row_idx, cls_name in enumerate(class_order):
        if cls_name not in sample_per_class:
            continue
        row_info = sample_per_class[cls_name]
        filepath = project_root / row_info["filepath"]
        
        # Load waveform
        waveform = preprocessor.load_audio(filepath)
        window = preprocessor.pad_or_crop(waveform, start_idx=0) # 3.0s window
        
        # Extract Log-Mel
        with torch.no_grad():
            log_mel = mel_extractor(window) # [1, 1, 128, time]
            spec_np = log_mel.squeeze().numpy()

        time_axis = np.linspace(0, 3.0, window.shape[-1])
        wave_np = window.squeeze().numpy()

        # Plot waveform
        ax_wave = axes[row_idx, 0]
        ax_wave.plot(time_axis, wave_np, color=color_map[cls_name], alpha=0.85, linewidth=0.8)
        ax_wave.set_title(f"Waveform — {cls_name} [{early_warning_status[cls_name]}]\nFile: {row_info['filename']} (Group: {row_info['group_id']})", fontsize=10, fontweight="semibold")
        ax_wave.set_xlabel("Time (seconds)")
        ax_wave.set_ylabel("Amplitude")
        ax_wave.set_ylim(-1.1, 1.1)
        ax_wave.grid(True, linestyle="--", alpha=0.5)

        # Plot spectrogram
        ax_spec = axes[row_idx, 1]
        im = ax_spec.imshow(spec_np, origin="lower", aspect="auto", cmap="inferno", extent=[0, 3.0, 50, 8000])
        ax_spec.set_title(f"Log-Mel Spectrogram (128 bins) — {cls_name}", fontsize=10, fontweight="semibold")
        ax_spec.set_xlabel("Time (seconds)")
        ax_spec.set_ylabel("Frequency (Hz)")
        fig.colorbar(im, ax=ax_spec, format="%+2.1f", pad=0.02)

    plt.tight_layout()
    output_img_path = examples_dir / "flocksense_audio_representations.png"
    plt.savefig(output_img_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved example representations to: {output_img_path}")

if __name__ == "__main__":
    generate_example_visualizations()
