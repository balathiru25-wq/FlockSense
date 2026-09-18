import sys
from pathlib import Path

_curr = Path(__file__).resolve().parent
_root = _curr.parent
for p in [str(_curr), str(_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from audio_inference import FlockSenseAudioInference

pipeline = FlockSenseAudioInference(checkpoint_path='models/audio_model_best.pth')

test_files = [
    # 3 Normal (from 3 different groups)
    ('Healthy/36.wav', 'Normal', 'Healthy_block_05', 'Poultry Vocalization Signal Dataset for Early Disease Detection/Poultry Vocalization Signal Dataset for Early Disease Detection/Chicken_Audio_Dataset/Healthy/36.wav'),
    ('Healthy/100.wav', 'Normal', 'Healthy_block_14', 'Poultry Vocalization Signal Dataset for Early Disease Detection/Poultry Vocalization Signal Dataset for Early Disease Detection/Chicken_Audio_Dataset/Healthy/100.wav'),
    ('Noise/10.wav', 'Normal', 'Noise_block_01', 'Poultry Vocalization Signal Dataset for Early Disease Detection/Poultry Vocalization Signal Dataset for Early Disease Detection/Chicken_Audio_Dataset/Noise/10.wav'),
    # 3 Abnormal (from 3 different groups)
    ('Unhealthy/1.wav', 'Abnormal', 'Unhealthy_block_00', 'Poultry Vocalization Signal Dataset for Early Disease Detection/Poultry Vocalization Signal Dataset for Early Disease Detection/Chicken_Audio_Dataset/Unhealthy/1.wav'),
    ('Unhealthy/100.wav', 'Abnormal', 'Unhealthy_block_14', 'Poultry Vocalization Signal Dataset for Early Disease Detection/Poultry Vocalization Signal Dataset for Early Disease Detection/Chicken_Audio_Dataset/Unhealthy/100.wav'),
    ('Unhealthy/113.wav', 'Abnormal', 'Unhealthy_block_16', 'Poultry Vocalization Signal Dataset for Early Disease Detection/Poultry Vocalization Signal Dataset for Early Disease Detection/Chicken_Audio_Dataset/Unhealthy/113.wav')
]

print(f"{'Filename':<20} | {'True Label':<12} | {'Predicted Label':<16} | {'Abnormal Prob':<14} | {'Confidence':<12} | {'Correct / Incorrect':<18}")
print("-" * 105)

for fname, true_bin, grp, fpath in test_files:
    res = pipeline.analyze_audio_file(fpath)
    pred_lbl = 'Abnormal' if res['predicted_acoustic_state'] == 'ABNORMAL' else 'Normal'
    is_corr = 'Correct' if pred_lbl == true_bin else 'Incorrect'
    abn_prob_val = res['overall_abnormality_probability_pct']
    abn_prob_str = f"{abn_prob_val:.2f}%"
    conf_val = abn_prob_val if pred_lbl == 'Abnormal' else (100.0 - abn_prob_val)
    conf_str = f"{conf_val:.2f}%"
    print(f"{fname:<20} | {true_bin:<12} | {pred_lbl:<16} | {abn_prob_str:<14} | {conf_str:<12} | {is_corr:<18}")
