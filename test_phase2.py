"""
Phase 2 Test Script: Audio-based Highlight Detection.

This script tests:
1. Loading the pipeline configuration from config.yaml using PyYAML.
2. Ingesting the video from input/ (downloaded in Phase 1).
3. Analyzing the audio track with librosa and scipy.signal to find energy peaks.
4. Printing the detected highlight timestamps and total count.
"""

import os
import sys
import yaml
from src.analyze_audio import detect_highlights


def format_timestamp(seconds: float) -> str:
    """Format seconds into HH:MM:SS or MM:SS format."""
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins:02d}:{secs:05.2f}"


def main():
    print("=" * 65)
    print("Running Phase 2 Pipeline Test: Audio Highlight Detection")
    print("=" * 65)

    # 1. Load config.yaml
    config_file = "config.yaml"
    if not os.path.isfile(config_file):
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    print(f"Loading pipeline settings from '{config_file}'...")
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

    # 2. Identify input video
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        print(f"Using user-specified video: {video_path}")
    else:
        video_path = os.path.join(config.get("paths", {}).get("input_dir", "input"), "test_video.mp4")
        print(f"Using Phase 1 input video: {video_path}")

    if not os.path.isfile(video_path):
        raise FileNotFoundError(
            f"Input video not found at '{video_path}'. "
            "Please run test_phase1.py first to download/generate a test video."
        )

    # 3. Detect highlights
    highlights = detect_highlights(video_path=video_path, config=config)

    # 4. Display results
    print("\n" + "-" * 65)
    print("DETECTION RESULTS")
    print("-" * 65)

    if not highlights:
        print("No highlight moments detected matching the criteria.")
    else:
        for idx, h in enumerate(highlights, 1):
            start_str = format_timestamp(h["start"])
            end_str = format_timestamp(h["end"])
            peak_str = format_timestamp(h["peak_time"])
            duration = h["end"] - h["start"]
            print(
                f"  [{idx:02d}] Window: {start_str} -> {end_str} ({duration:5.2f}s) | "
                f"Peak: {peak_str} ({h['peak_time']:5.2f}s) | Score: {h['score']:.4f}"
            )

    print("-" * 65)
    print(f"Total Highlights Found: {len(highlights)}")
    print("=" * 65)


if __name__ == "__main__":
    main()
