"""
Audio analysis module for highlight detection.
Detects loud and exciting segments in videos using RMS energy and peak finding.
"""

import os
import sys
import subprocess
from typing import List, Dict, Any

# Ensure compatibility on Windows platforms where Application Control / Smart App Control
# policy may prevent loading unsigned C-extensions from numpy.random.
import types

_needs_mock = False
try:
    import numpy.random
except Exception:
    _needs_mock = True

if _needs_mock:
    mock_random = types.ModuleType("numpy.random")
    mock_random.__path__ = []
    mock_bit_generator = types.ModuleType("numpy.random.bit_generator")

    class BitGenerator:
        pass

    class Generator:
        pass

    class RandomState:
        pass

    mock_bit_generator.BitGenerator = BitGenerator
    mock_random.bit_generator = mock_bit_generator
    mock_random.Generator = Generator
    mock_random.RandomState = RandomState
    sys.modules["numpy.random"] = mock_random
    sys.modules["numpy.random.bit_generator"] = mock_bit_generator

    import numpy as _np
    _np.random = mock_random

    mock_stats = types.ModuleType("scipy.stats")
    mock_stats.scoreatpercentile = _np.percentile
    sys.modules["scipy.stats"] = mock_stats

import numpy as np
import librosa
import librosa.feature
from scipy.signal import find_peaks


def _extract_audio_to_wav(video_path: str, output_wav: str, sample_rate: int = 16000) -> str:
    """Extract audio track from video file to a 16kHz mono WAV file using FFmpeg."""
    target_dir = os.path.dirname(output_wav)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vn",
        "-ar", str(sample_rate),
        "-ac", "1",
        output_wav
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg audio extraction failed:\n{proc.stderr}")
    return output_wav


def detect_highlights(video_path: str, config: dict) -> List[Dict[str, Any]]:
    """
    Detect highlight moments (loud/exciting parts) in a video based on RMS audio energy.

    Args:
        video_path: Path to the input video or audio file.
        config: Configuration dictionary containing an 'audio_analysis' or 'audio' section.

    Returns:
        A list of dictionaries representing detected highlight windows:
        [{"start": float, "end": float, "peak_time": float, "score": float}, ...]
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Input video file not found: {video_path}")

    # Extract configuration parameters with sensible defaults
    audio_cfg = config.get("audio_analysis", config.get("audio", {}))
    paths_cfg = config.get("paths", {})

    sample_rate = int(audio_cfg.get("sample_rate", 16000))
    peak_percentile = float(audio_cfg.get("peak_percentile", audio_cfg.get("rms_threshold_percentile", 90)))
    min_peak_distance_sec = float(audio_cfg.get("min_peak_distance_sec", 3))
    pad_before = float(audio_cfg.get("clip_padding_before_sec", 5))
    pad_after = float(audio_cfg.get("clip_padding_after_sec", 10))
    temp_dir = paths_cfg.get("temp_dir", "temp")

    print(f"\n[Audio Analysis] Processing: '{video_path}'")
    print(f"[Audio Analysis] Config -> SR: {sample_rate}Hz | Threshold: {peak_percentile}th percentile | Min Distance: {min_peak_distance_sec}s")

    # 1. Load audio using librosa
    temp_wav = None
    file_ext = os.path.splitext(video_path)[1].lower()
    audio_source = video_path

    try:
        # If input is a video format (e.g. .mp4, .mkv, .mov), extract audio track to WAV first
        if file_ext in [".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv"]:
            os.makedirs(temp_dir, exist_ok=True)
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            temp_wav = os.path.join(temp_dir, f"audio_{video_name}_{sample_rate}hz.wav")
            print(f"[Audio Analysis] Extracting audio stream via FFmpeg to '{temp_wav}'...")
            audio_source = _extract_audio_to_wav(video_path, temp_wav, sample_rate=sample_rate)

        print("[Audio Analysis] Loading audio waveform with librosa...")
        y, sr = librosa.load(audio_source, sr=sample_rate, mono=True)
    finally:
        # Clean up temporary WAV file
        if temp_wav and os.path.exists(temp_wav):
            try:
                os.remove(temp_wav)
            except OSError:
                pass

    total_duration = len(y) / sr
    print(f"[Audio Analysis] Audio loaded: {total_duration:.2f} seconds ({len(y):,} samples at {sr}Hz).")

    if total_duration <= 0 or len(y) == 0:
        print("[Audio Analysis] Warning: Audio track is empty. No highlights detected.")
        return []

    # 2. Calculate RMS energy using librosa.feature.rms
    hop_length = 512
    print("[Audio Analysis] Calculating RMS energy...")
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]

    # 3. Find spikes in RMS energy using scipy.signal.find_peaks
    threshold = float(np.percentile(rms, peak_percentile))
    min_distance_frames = max(1, int(min_peak_distance_sec * sr / hop_length))

    print(f"[Audio Analysis] Finding peaks (Threshold: {threshold:.5f}, Min Distance: {min_distance_frames} frames)...")
    peaks, properties = find_peaks(rms, height=threshold, distance=min_distance_frames)

    # 4. Convert peak frames to timestamps in seconds
    peak_times = librosa.frames_to_time(peaks, sr=sr, hop_length=hop_length)

    # 5. Build highlight windows (-5s before, +10s after, clamped to [0, total_duration])
    highlights: List[Dict[str, Any]] = []
    for i, peak_sec in enumerate(peak_times):
        start_sec = max(0.0, float(peak_sec - pad_before))
        end_sec = min(total_duration, float(peak_sec + pad_after))

        if start_sec < end_sec:
            highlights.append({
                "start": round(start_sec, 2),
                "end": round(end_sec, 2),
                "peak_time": round(float(peak_sec), 2),
                "score": round(float(properties["peak_heights"][i]), 4),
            })

    print(f"[Audio Analysis] Completed: Detected {len(highlights)} highlight window(s).")
    return highlights
