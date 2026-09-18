import math
import random
import torch
import torch.nn as nn
import torchaudio
import torchaudio.transforms as T
import soundfile as sf
import numpy as np

class AudioPreprocessor:
    """
    Standardizes audio loading, mono-conversion, resampling, and padding/clipping.
    """
    def __init__(self, target_sr=16000, clip_duration=3.0, normalize_peak=True):
        self.target_sr = target_sr
        self.clip_duration = clip_duration
        self.target_samples = int(target_sr * clip_duration)
        self.normalize_peak = normalize_peak

    def load_audio(self, filepath):
        """
        Safely loads audio using soundfile and converts to torch.Tensor [1, samples].
        """
        try:
            data, sr = sf.read(str(filepath), dtype="float32")
        except Exception as e:
            raise RuntimeError(f"Failed to read audio file {filepath}: {e}")

        # Convert to float tensor
        tensor = torch.from_numpy(data)
        if tensor.ndim == 1:
            tensor = tensor.unsqueeze(0)  # [1, samples]
        elif tensor.ndim == 2:
            # If channels first or last: shape could be [channels, samples] or [samples, channels]
            if tensor.shape[0] > tensor.shape[1]:
                tensor = tensor.transpose(0, 1)
            # Downmix to mono
            tensor = torch.mean(tensor, dim=0, keepdim=True)

        # Resample if needed
        if sr != self.target_sr:
            resampler = T.Resample(orig_freq=sr, new_freq=self.target_sr)
            tensor = resampler(tensor)

        # Peak normalization (avoiding division by zero)
        if self.normalize_peak:
            peak = torch.max(torch.abs(tensor))
            if peak > 1e-6:
                tensor = tensor / peak

        return tensor

    def pad_or_crop(self, waveform, start_idx=None):
        """
        Ensures waveform is exactly self.target_samples long.
        """
        num_samples = waveform.shape[-1]
        if num_samples == self.target_samples:
            return waveform
        elif num_samples < self.target_samples:
            # Pad short recordings (repeat or zero pad)
            pad_amount = self.target_samples - num_samples
            pad_left = pad_amount // 2
            pad_right = pad_amount - pad_left
            return torch.nn.functional.pad(waveform, (pad_left, pad_right), mode="constant", value=0.0)
        else:
            # Crop
            if start_idx is None:
                start_idx = 0
            end_idx = start_idx + self.target_samples
            if end_idx > num_samples:
                start_idx = num_samples - self.target_samples
                end_idx = num_samples
            return waveform[:, start_idx:end_idx]


class LogMelSpectrogram(nn.Module):
    """
    Computes Log-Mel Spectrogram from raw waveform tensor.
    """
    def __init__(self, sample_rate=16000, n_fft=1024, hop_length=512, win_length=1024, n_mels=128, f_min=50.0, f_max=8000.0, top_db=80.0):
        super().__init__()
        self.mel_spectrogram = T.MelSpectrogram(
            sample_rate=sample_rate,
            n_fft=n_fft,
            win_length=win_length,
            hop_length=hop_length,
            f_min=f_min,
            f_max=f_max,
            n_mels=n_mels,
            power=2.0
        )
        self.amplitude_to_db = T.AmplitudeToDB(stype="power", top_db=top_db)

    def forward(self, x):
        """
        Input: [batch, 1, samples] or [1, samples]
        Output: Log-Mel spectrogram [batch, 1, n_mels, time_steps]
        """
        mel = self.mel_spectrogram(x)
        log_mel = self.amplitude_to_db(mel)
        # Normalize to approximate [-1, 1] range: typical top_db is 80, values lie in [-80, 0]
        norm_log_mel = (log_mel + 40.0) / 40.0
        return norm_log_mel


class AudioAugmenter:
    """
    Conservative data augmentation applied ONLY during training.
    """
    def __init__(self, time_shift_fraction=0.15, gain_db=3.0, noise_factor=0.003, freq_mask_param=16, time_mask_param=24):
        self.time_shift_fraction = time_shift_fraction
        self.gain_db = gain_db
        self.noise_factor = noise_factor
        self.freq_mask = T.FrequencyMasking(freq_mask_param=freq_mask_param)
        self.time_mask = T.TimeMasking(time_mask_param=time_mask_param)

    def augment_waveform(self, waveform):
        """
        Waveform domain augmentations (shift, gain, subtle farm-like noise).
        """
        out = waveform.clone()
        # 1. Random circular time shift
        if random.random() < 0.5:
            max_shift = int(out.shape[-1] * self.time_shift_fraction)
            shift = random.randint(-max_shift, max_shift)
            out = torch.roll(out, shifts=shift, dims=-1)

        # 2. Random gain / volume change
        if random.random() < 0.5:
            gain_factor = 10.0 ** (random.uniform(-self.gain_db, self.gain_db) / 20.0)
            out = out * gain_factor

        # 3. Additive subtle white/background noise
        if random.random() < 0.3:
            noise = torch.randn_like(out) * self.noise_factor
            out = out + noise

        # Clamp to [-1, 1]
        out = torch.clamp(out, -1.0, 1.0)
        return out

    def augment_spectrogram(self, spec):
        """
        SpecAugment: Frequency and Time masking.
        Input: [1, n_mels, time]
        """
        out = spec.clone()
        if random.random() < 0.4:
            out = self.freq_mask(out)
        if random.random() < 0.4:
            out = self.time_mask(out)
        return out
