"""
Auto Video Clipper - Main Application Entry Point.
"""
import os
import sys
import yaml
import argparse
from src.pipeline import process_video

def main():
    parser = argparse.ArgumentParser(description="Auto Video Clipper - Generate viral clips.")
    parser.add_argument("input_video", help="Path to input video (e.g., input/gameplay.webm)")
    parser.add_argument("-d", "--duration", type=int, help="Clip duration in seconds (e.g., 30, 60)")
    parser.add_argument("-r", "--ratio", choices=["9:16", "16:9"], help="Aspect ratio: '9:16' or '16:9'")
    parser.add_argument("-n", "--num_clips", type=int, help="Number of clips to generate")
    
    args = parser.parse_args()

    print("*" * 65)
    print("           AUTO VIDEO CLIPPER - FULL PIPELINE")
    print("*" * 65)

    # 1. Load configuration
    config_path = "config.yaml"
    if not os.path.isfile(config_path):
        print(f"[Error] Configuration file '{config_path}' not found.")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 2. Validate video
    video_path = args.input_video
    if not os.path.isfile(video_path):
        print(f"[Error] Video file not found at: '{video_path}'")
        sys.exit(1)

    # 3. Override Config with Command Line Arguments
    if "video_output" not in config: config["video_output"] = {}
    if "output" not in config: config["output"] = {}

    if args.duration:
        config["video_output"]["clip_duration_sec"] = args.duration
        print(f"🔧 Overriding duration to {args.duration} seconds.")
        
    if args.ratio:
        config["video_output"]["aspect_ratio"] = args.ratio
        print(f"🔧 Overriding aspect ratio to {args.ratio}.")

    if args.num_clips:
        config["output"]["max_clips"] = args.num_clips
        print(f"🔧 Overriding max clips to {args.num_clips}.")

    # 4. Execute master pipeline
    try:
        final_clips = process_video(input_video_path=video_path, config=config)
        if final_clips:
            print(f"\n[Success] Pipeline finished successfully! Produced {len(final_clips)} clip(s).")
        else:
            print("\n[Finished] Pipeline finished with no clips produced.")
    except Exception as exc:
        print(f"\n[Pipeline Failure] An error occurred during processing: {exc}")
        raise exc

if __name__ == "__main__":
    main()