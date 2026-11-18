"""
Phase 1 Test Script: Ingestion and Lossless Video Clipping.

This script tests:
1. Downloading a video to the input/ folder using yt-dlp (or using a provided local file / fallback).
2. Cutting a 10-second highlight clip (from 10s to 20s) using FFmpeg stream copy.
3. Saving the final clip into the output/ folder.
"""

import os
import sys
import subprocess
from pathlib import Path
from src.ingest import download_video
from src.clipper import cut_clip

# Default publicly accessible test video (Big Buck Bunny, ~33 seconds)
DEFAULT_TEST_URL = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"


def create_offline_sample_video(path: str, duration_sec: int = 30) -> str:
    """Generate a clean synthetic test video with spoken voice audio using FFmpeg when offline."""
    print(f"Creating local test video ({duration_sec}s) at '{path}'...")
    target_dir = os.path.dirname(path)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    speech_text = (
        "Welcome to the gaming highlights. Here comes an incredible move by the player. "
        "What an amazing shot and absolute perfection. Thank you for watching."
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "lavfi",
        "-i", f"testsrc=duration={duration_sec}:size=1280x720:rate=30",
        "-f", "lavfi",
        "-i", f"flite=text='{speech_text}'",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        "-t", str(duration_sec),
        path
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return os.path.abspath(path)


def main():
    print("=" * 60)
    print("Running Phase 1 Pipeline Test")
    print("=" * 60)

    # 1. Determine source video URL or local file path
    if len(sys.argv) > 1:
        source = sys.argv[1]
        print(f"Using user-provided source: {source}")
    else:
        source = DEFAULT_TEST_URL
        print(f"Using default test URL: {source}")

    input_video_path = os.path.join("input", "test_video.mp4")
    output_clip_path = os.path.join("output", "test_clip.mp4")

    # Ensure required directories exist
    os.makedirs("input", exist_ok=True)
    os.makedirs("output", exist_ok=True)

    # 2. Download or ingest video
    downloaded_video = None
    try:
        downloaded_video = download_video(source, input_video_path)
    except Exception as exc:
        print(f"\n[Warning] Could not ingest from '{source}': {exc}")
        print("Checking for local fallback...")
        if os.path.isfile(input_video_path):
            print(f"Using existing input video: {input_video_path}")
            downloaded_video = os.path.abspath(input_video_path)
        else:
            print("Generating local synthetic test video for offline verification...")
            downloaded_video = create_offline_sample_video(input_video_path, duration_sec=30)

    print(f"\nSource video ready: {downloaded_video}")
    print(f"File size: {os.path.getsize(downloaded_video):,} bytes")

    # 3. Cut a 10-second clip (10s to 20s)
    start_time = "00:00:10"
    end_time = "00:00:20"

    print(f"\nExtracting segment: {start_time} -> {end_time}...")
    final_clip = cut_clip(
        input_path=downloaded_video,
        start_time=start_time,
        end_time=end_time,
        output_path=output_clip_path
    )

    # 4. Verify output clip
    if not os.path.isfile(final_clip):
        raise FileNotFoundError(f"Expected output clip was not created: {final_clip}")

    clip_size = os.path.getsize(final_clip)
    print("\n" + "=" * 60)
    print("Phase 1 Pipeline Test Completed Successfully!")
    print(f"Original Video : {downloaded_video}")
    print(f"Final Clip     : {final_clip}")
    print(f"Clip File Size : {clip_size:,} bytes")
    print("=" * 60)


if __name__ == "__main__":
    main()
