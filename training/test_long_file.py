import sys
from pathlib import Path
import numpy as np
import torch

_curr = Path(__file__).resolve().parent
_root = _curr.parent
for p in [str(_curr), str(_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from audio_inference import FlockSenseAudioInference

pipeline = FlockSenseAudioInference(checkpoint_path='models/audio_model_best.pth')

long_file_rel = "Poultry Vocalization Signal Dataset for Early Disease Detection/Poultry Vocalization Signal Dataset for Early Disease Detection/Chicken_Audio_Dataset/Healthy/136.wav"
long_fpath = Path(long_file_rel).resolve()

print("Analyzing Long Audio File:", long_fpath.name)
res = pipeline.analyze_audio_file(long_fpath, hop_duration=1.5)

# Detailed window breakdown
wf = pipeline.preprocessor.load_audio(long_fpath)
total_samples = wf.shape[-1]
hop_samples = int(1.5 * pipeline.target_sr)
target_samples = pipeline.target_samples

starts = list(range(0, total_samples - target_samples + 1, hop_samples))
if starts[-1] + target_samples < total_samples:
    starts.append(total_samples - target_samples)

windows = [wf[:, st:st+target_samples] for st in starts]
window_batch = torch.stack(windows, dim=0)
import torch
with torch.no_grad():
    mels = pipeline.mel_extractor(window_batch).to(pipeline.device)
    logits = pipeline.model(mels)
    probs = torch.softmax(logits, dim=1).cpu().numpy()

unhealthy_probs = probs[:, 1]
print(f"Total Windows: {len(unhealthy_probs)}")
print(f"{'Window':<8} | {'Time Range (s)':<18} | {'Abnormal Prob (%)':<18} | {'Status':<12}")
print("-" * 65)

for i, p in enumerate(unhealthy_probs):
    st_sec = starts[i] / pipeline.target_sr
    end_sec = min(st_sec + 3.0, res['duration_seconds'])
    time_str = f"{st_sec:.1f}s - {end_sec:.1f}s"
    prob_str = f"{p*100:.2f}%"
    status = "Normal" if p < 0.35 else ("Watch" if p < 0.70 else "Alert")
    print(f"{i+1:<8} | {time_str:<18} | {prob_str:<18} | {status:<12}")

print("-" * 65)
print(f"Total Duration:              {res['duration_seconds']} seconds")
print(f"Total Windows:               {res['windows_analyzed']}")
print(f"Mean Abnormal Probability:   {res['mean_window_abnormality_pct']}%")
print(f"Maximum Window Probability:  {res['max_window_abnormality_pct']}%")
print(f"Median Window Probability:   {res['median_window_abnormality_pct']}%")
print(f"Anomalous Windows Count:     {res['high_risk_windows']} / {res['windows_analyzed']}")
print(f"Percentage Anomalous:        {res['percentage_anomalous_windows']}%")
print(f"Overall Abnormality Risk:    {res['overall_abnormality_probability_pct']}%")
print(f"Final Recording-Level State: {res['predicted_acoustic_state']} ({res['status']})")
