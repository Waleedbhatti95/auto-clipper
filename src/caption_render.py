import os
import shutil
import subprocess

def format_ass_path_for_ffmpeg(ass_path: str) -> str:
    abs_path = os.path.abspath(ass_path).replace("\\", "/")
    drive, rest = os.path.splitdrive(abs_path)
    if drive: return f"{drive[0]}\\\\:{rest}"
    return abs_path

def burn_subtitles(video_path: str, ass_path: str, output_path: str, config: dict) -> str:
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Input video file not found: {video_path}")
    if not os.path.isfile(ass_path):
        raise FileNotFoundError(f"Subtitle file not found: {ass_path}")

    target_dir = os.path.dirname(output_path)
    if target_dir: os.makedirs(target_dir, exist_ok=True)

    final_output = os.path.abspath(output_path)

    if os.path.getsize(ass_path) < 50:
        print("[Caption Render] Notice: No dialogue to burn. Copying video...")
        shutil.copyfile(os.path.abspath(video_path), final_output)
        return final_output

    formatted_ass = format_ass_path_for_ffmpeg(ass_path)
    
    # Aspect Ratio Logic from Config
    video_out_cfg = config.get("video_output", {})
    aspect_ratio = video_out_cfg.get("aspect_ratio", "9:16")

    if aspect_ratio == "9:16":
        print(f"\n[Caption Render] Cropping to 9:16 and Burning ASS subtitles...")
        crop_filter = "crop=ih*9/16:ih:(iw-ih*9/16)/2:0"
        vf_string = f"{crop_filter},ass={formatted_ass}"
    else:
        print(f"\n[Caption Render] Keeping Landscape (16:9) and Burning ASS subtitles...")
        vf_string = f"ass={formatted_ass}"

    cmd = [
        "ffmpeg", "-y",
        "-i", os.path.abspath(video_path),
        "-vf", vf_string,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "copy",
        final_output
    ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg failed:\n{proc.stderr}")
    except FileNotFoundError as err:
        raise RuntimeError("FFmpeg executable not found.") from err

    print(f"[Caption Render] Final video saved to: '{final_output}'")
    return final_output