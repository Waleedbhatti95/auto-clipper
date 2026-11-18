import os
import subprocess
from typing import Union

def cut_clip(input_path: str, start_time: Union[str, int, float], end_time: Union[str, int, float], output_path: str) -> str:
    input_file = os.path.abspath(input_path)
    if not os.path.isfile(input_file):
        raise FileNotFoundError(f"Input video file not found: {input_path}")

    target_dir = os.path.dirname(output_path)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    final_path = os.path.abspath(output_path)
    start_str = str(start_time).strip()
    end_str = str(end_time).strip()

    print(f"Cutting clip from '{input_file}' [{start_str} to {end_str}]...")

    # Frame-accurate cutting (re-encoding) for perfect sync
    cmd = [
        "ffmpeg", "-y",
        "-ss", start_str,
        "-to", end_str,
        "-i", input_file,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "aac",
        final_path
    ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed:\n{result.stderr}")
    except FileNotFoundError as err:
        raise RuntimeError("FFmpeg executable not found.") from err

    print(f"Clip cut successfully: '{final_path}'")
    return final_path