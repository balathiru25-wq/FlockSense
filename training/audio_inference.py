import os
import sys
import json
import argparse
from pathlib import Path
import numpy as np
import torch
import soundfile as sf

# Ensure local imports work
_current_dir = Path(__file__).resolve().parent
_root_dir = _current_dir.parent
for p in [str(_current_dir), str(_root_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from audio_transforms import AudioPreprocessor, LogMelSpectrogram
from models import FlockSenseResNet18

class FlockSenseAudioInference:
    """
    Reusable bioacoustic inference pipeline for FlockSense.
    Processes arbitrary-length recordings via sliding-window segmentation,
    aggregates anomaly scores, and generates early-warning risk alerts.
    """
    def __init__(self, checkpoint_path=None, device=None):
        if checkpoint_path is None:
            checkpoint_path = Path("models/audio_model_best.pth")
        self.checkpoint_path = Path(checkpoint_path).resolve()
        
        if not self.checkpoint_path.exists():
            raise FileNotFoundError(f"Model checkpoint not found at: {self.checkpoint_path}")

        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        # Load checkpoint
        ckpt = torch.load(self.checkpoint_path, map_location=self.device, weights_only=False)
        self.audio_cfg = ckpt.get("audio_config", {"target_sample_rate": 16000, "clip_duration_seconds": 3.0})
        self.risk_thresholds = ckpt.get("risk_thresholds", {"normal_watch_threshold": 0.35, "watch_alert_threshold": 0.70})
        self.class_names = ckpt.get("class_names", ["Healthy", "Unhealthy", "Noise"])

        self.target_sr = self.audio_cfg.get("target_sample_rate", 16000)
        self.clip_duration = self.audio_cfg.get("clip_duration_seconds", 3.0)
        self.target_samples = int(self.target_sr * self.clip_duration)

        # Initialize audio preprocessor and spectrogram extractor
        self.preprocessor = AudioPreprocessor(target_sr=self.target_sr, clip_duration=self.clip_duration)
        self.mel_extractor = LogMelSpectrogram(sample_rate=self.target_sr, n_fft=1024, hop_length=512, n_mels=128)

        # Initialize and load model
        self.model = FlockSenseResNet18(num_classes=len(self.class_names), pretrained=False, dropout=0.0)
        self.model.load_state_dict(ckpt["model_state_dict"])
        self.model.to(self.device)
        self.model.eval()

    def analyze_audio_file(self, audio_path, hop_duration=1.5):
        """
        Analyzes an audio file of arbitrary length and returns comprehensive early-warning risk metrics.
        """
        audio_path = Path(audio_path).resolve()
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Load audio safely
        full_waveform = self.preprocessor.load_audio(audio_path)
        total_samples = full_waveform.shape[-1]
        duration_seconds = total_samples / self.target_sr

        # Segment into sliding windows
        hop_samples = int(hop_duration * self.target_sr)
        if total_samples <= self.target_samples:
            windows = [self.preprocessor.pad_or_crop(full_waveform)]
        else:
            starts = list(range(0, total_samples - self.target_samples + 1, hop_samples))
            if starts[-1] + self.target_samples < total_samples:
                starts.append(total_samples - self.target_samples)
            windows = []
            for st in starts:
                end = st + self.target_samples
                windows.append(full_waveform[:, st:end])

        num_windows = len(windows)
        
        # Batch inference across all windows
        window_batch = torch.stack(windows, dim=0) # [N, 1, samples]
        with torch.no_grad():
            mels = self.mel_extractor(window_batch).to(self.device) # [N, 1, 128, 94]
            logits = self.model(mels)
            probs = torch.softmax(logits, dim=1).cpu().numpy() # [N, 3]

        # Class probabilities: [Healthy (0), Unhealthy (1), Noise (2)]
        healthy_probs = probs[:, 0]
        unhealthy_probs = probs[:, 1]  # Abnormality risk per window
        noise_probs = probs[:, 2]

        mean_abnormal = float(np.mean(unhealthy_probs))
        max_abnormal = float(np.max(unhealthy_probs))
        median_abnormal = float(np.median(unhealthy_probs))

        # Risk aggregation:
        # In poultry health monitoring, even localized bursts of coughs/sneezes/rales within a longer recording
        # signify potential respiratory distress. A pure mean could dilute short localized bursts.
        # Robust composite abnormality score: 0.6 * max_abnormal + 0.4 * mean_abnormal
        if num_windows == 1:
            overall_abnormal_score = max_abnormal
        else:
            overall_abnormal_score = 0.60 * max_abnormal + 0.40 * mean_abnormal

        # High-risk window count (windows where abnormal prob exceeds watch threshold)
        watch_thresh = self.risk_thresholds.get("normal_watch_threshold", 0.35)
        alert_thresh = self.risk_thresholds.get("watch_alert_threshold", 0.70)
        
        high_risk_windows = int(np.sum(unhealthy_probs >= watch_thresh))
        pct_high_risk = float((high_risk_windows / num_windows) * 100.0)

        # Status & Interpretation
        if overall_abnormal_score >= alert_thresh:
            status = "ALERT"
            color_code = "RED"
            emoji = "🔴"
            interpretation = "Significant deviation from normal flock acoustic baseline. Frequent or pronounced abnormal vocalizations detected."
            action = "Immediately inspect the poultry flock and shed ventilation. Check for physical respiratory symptoms. Consult a certified veterinarian and submit samples for professional laboratory confirmation."
        elif overall_abnormal_score >= watch_thresh:
            status = "WATCH"
            color_code = "YELLOW"
            emoji = "🟡"
            interpretation = "Moderate acoustic deviation detected. Occasional unusual vocalization patterns or elevated acoustic variance observed."
            action = "Inspect the shed, review flock activity, check environmental conditions (temperature/humidity/ammonia), and monitor trend over the next 4–12 hours."
        else:
            status = "NORMAL"
            color_code = "GREEN"
            emoji = "🟢"
            # Distinguish clean vocal baseline vs ambient noise
            if np.mean(noise_probs) > 0.60:
                interpretation = "Flock acoustic environment is dominated by ambient equipment / ventilation machinery; no respiratory acoustic anomalies detected."
            else:
                interpretation = "Flock vocal pattern is consistent with healthy baseline acoustic activity. Normal peacetime vocalization."
            action = "Continue regular automated FlockSense acoustic monitoring."

        predicted_acoustic_state = "ABNORMAL" if overall_abnormal_score >= watch_thresh else "NORMAL"

        result = {
            "filename": audio_path.name,
            "filepath": str(audio_path),
            "duration_seconds": round(duration_seconds, 2),
            "windows_analyzed": num_windows,
            "predicted_acoustic_state": predicted_acoustic_state,
            "status": status,
            "color_code": color_code,
            "emoji": emoji,
            "overall_abnormality_probability_pct": round(overall_abnormal_score * 100, 2),
            "max_window_abnormality_pct": round(max_abnormal * 100, 2),
            "mean_window_abnormality_pct": round(mean_abnormal * 100, 2),
            "median_window_abnormality_pct": round(median_abnormal * 100, 2),
            "high_risk_windows": high_risk_windows,
            "high_risk_windows_fraction": f"{high_risk_windows} / {num_windows}",
            "percentage_anomalous_windows": round(pct_high_risk, 1),
            "mean_healthy_prob_pct": round(float(np.mean(healthy_probs)) * 100, 2),
            "mean_noise_prob_pct": round(float(np.mean(noise_probs)) * 100, 2),
            "interpretation": interpretation,
            "recommended_action": action,
            "thresholds": {
                "normal_watch": watch_thresh,
                "watch_alert": alert_thresh
            },
            "disclaimer": "FlockSense is an early-warning bioacoustic screening system, not a medical or veterinary diagnosis. Laboratory testing and veterinary examination are required to confirm clinical cause."
        }
        return result

    def print_report(self, result):
        print("\n" + "=" * 60)
        print("FLOCKSENSE BIOACOUSTIC EARLY-WARNING ANALYSIS")
        print("=" * 60)
        print(f"File:                      {result['filename']}")
        print(f"Duration:                  {result['duration_seconds']} seconds")
        print(f"Windows Analyzed:          {result['windows_analyzed']}")
        print(f"Predicted Acoustic State:  {result['predicted_acoustic_state']}")
        print(f"Status:                    {result['emoji']} {result['status']} ({result['color_code']})")
        print(f"Overall Abnormality Risk:  {result['overall_abnormality_probability_pct']}%")
        print(f"Maximum Window Anomaly:    {result['max_window_abnormality_pct']}%")
        print(f"Mean Window Anomaly:       {result['mean_window_abnormality_pct']}%")
        print(f"Median Window Anomaly:     {result['median_window_abnormality_pct']}%")
        print(f"High-Risk Windows:         {result['high_risk_windows_fraction']} ({result['percentage_anomalous_windows']}%)")
        print("-" * 60)
        print(f"Interpretation:")
        print(f"  {result['interpretation']}")
        print("-" * 60)
        print(f"Recommended Action:")
        print(f"  {result['recommended_action']}")
        print("-" * 60)
        print(f"Notice: {result['disclaimer']}")
        print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="FlockSense Audio Inference — Early-Warning Bioacoustic Screening")
    parser.add_argument("--audio", type=str, required=True, help="Path to input audio file (.wav, .mp3, etc.)")
    parser.add_argument("--checkpoint", type=str, default="models/audio_model_best.pth", help="Path to trained model checkpoint")
    parser.add_argument("--device", type=str, default=None, help="Compute device ('cuda' or 'cpu')")
    parser.add_argument("--hop", type=float, default=1.5, help="Sliding window hop duration in seconds")
    parser.add_argument("--json", action="store_true", help="Output result in JSON format")

    args = parser.parse_args()

    pipeline = FlockSenseAudioInference(checkpoint_path=args.checkpoint, device=args.device)
    result = pipeline.analyze_audio_file(args.audio, hop_duration=args.hop)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        pipeline.print_report(result)

if __name__ == "__main__":
    main()
