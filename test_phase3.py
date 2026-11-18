"""
Phase 3 Test Script: Subtitle Generation (Whisper) & Caption Burning (FFmpeg).

This script tests:
1. Loading the pipeline configuration from config.yaml.
2. Locating the 10-second clip from Phase 1 (output/test_clip.mp4) or cutting one on demand.
3. Transcribing the audio using OpenAI Whisper to generate an .srt file in temp/.
4. Burning the subtitles onto the video using FFmpeg and saving the captioned result in output/.
"""

import os
import sys
import yaml
from pathlib import Path
from src.transcribe import generate_subtitles
from src.caption_render import burn_subtitles
from src.clipper import cut_clip


def main():
    print("=" * 65)
    print("Running Phase 3 Pipeline Test: Caption Generation & Burning")
    print("=" * 65)

    # 1. Load config.yaml
    config_file = "config.yaml"
    if not os.path.isfile(config_file):
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    print(f"Loading pipeline settings from '{config_file}'...")
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

    paths_cfg = config.get("paths", {})
    output_dir = paths_cfg.get("output_dir", "output")
    temp_dir = paths_cfg.get("temp_dir", "temp")
    input_dir = paths_cfg.get("input_dir", "input")

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)

    # 2. Locate or prepare 10-second test clip
    test_clip_path = os.path.join(output_dir, "test_clip.mp4")
    if not os.path.isfile(test_clip_path):
        source_video = os.path.join(input_dir, "test_video.mp4")
        if not os.path.isfile(source_video):
            raise FileNotFoundError(
                f"Source video not found at '{source_video}'. "
                "Please run test_phase1.py first to prepare input media."
            )
        print(f"Phase 1 clip not found. Cutting a new 10s clip from '{source_video}'...")
        cut_clip(source_video, "00:00:10", "00:00:20", test_clip_path)

    print(f"Using clip: '{test_clip_path}' ({os.path.getsize(test_clip_path):,} bytes)")

    # 3. Generate subtitles with Whisper
    srt_output_path = os.path.join(temp_dir, "test_clip.srt")
    print(f"\nGenerating subtitles to '{srt_output_path}'...")
    generate_subtitles(
        video_path=test_clip_path,
        output_srt_path=srt_output_path,
        config=config
    )

    # Display the actual Whisper transcription output from the SRT file
    print("\n" + "-" * 65)
    print("WHISPER TRANSCRIBED SRT CONTENT:")
    print("-" * 65)
    with open(srt_output_path, "r", encoding="utf-8") as f:
        srt_content = f.read().strip()
    print(srt_content if srt_content else "(No speech transcribed in this segment)")
    print("-" * 65)

    # 4. Burn subtitles into video
    final_captioned_video = os.path.join(output_dir, "clip_with_captions.mp4")
    print(f"\nBurning captions to create final video: '{final_captioned_video}'...")
    burn_subtitles(
        video_path=test_clip_path,
        srt_path=srt_output_path,
        output_path=final_captioned_video
    )

    # 5. Verify final output
    if not os.path.isfile(final_captioned_video):
        raise FileNotFoundError(f"Final captioned video was not created: {final_captioned_video}")

    final_size = os.path.getsize(final_captioned_video)
    print("\n" + "=" * 65)
    print("Phase 3 Pipeline Test Completed Successfully!")
    print(f"Source Clip       : {test_clip_path}")
    print(f"Generated SRT     : {srt_output_path}")
    print(f"Captioned Video   : {final_captioned_video} ({final_size:,} bytes)")
    print("=" * 65)


if __name__ == "__main__":
    main()
