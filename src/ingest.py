"""
Video ingestion module using yt-dlp.
Downloads videos from YouTube and other supported sources in MP4 format (up to 1080p).
"""

import os
from pathlib import Path
from typing import Optional
import yt_dlp


def download_video(url: str, output_path: str) -> str:
    """
    Download a video from a URL or local file URI using yt-dlp.

    Args:
        url: Video URL (e.g., YouTube link) or path to a local video file.
        output_path: File path or directory where the video should be saved.

    Returns:
        The absolute path to the downloaded MP4 file.
    """
    print(f"Downloading video from '{url}'...")

    # If a local file path is provided, resolve it to a file:// URI
    if os.path.isfile(url):
        url = Path(url).resolve().as_uri()

    # Ensure parent directory exists
    target_dir = output_path if os.path.isdir(output_path) or output_path.endswith(("/", "\\")) else os.path.dirname(output_path)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    # Determine outtmpl template for yt-dlp
    base, ext = os.path.splitext(output_path)
    if ext.lower() == ".mp4":
        outtmpl = f"{base}.%(ext)s"
    elif os.path.isdir(output_path) or output_path.endswith(("/", "\\")):
        outtmpl = os.path.join(output_path, "%(title)s.%(ext)s")
    else:
        outtmpl = f"{output_path}.%(ext)s"

    ydl_opts = {
        # Best video up to 1080p + best audio, falling back to best combined format <= 1080p
        "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080][ext=mp4]/best[height<=1080]/best",
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "enable_file_urls": True,
        "quiet": False,
        "no_warnings": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        prepared_name = ydl.prepare_filename(info)

        # Handle case where output is merged to .mp4 container
        expected_mp4 = os.path.splitext(prepared_name)[0] + ".mp4"
        if os.path.exists(expected_mp4):
            final_path = os.path.abspath(expected_mp4)
        elif os.path.exists(prepared_name):
            final_path = os.path.abspath(prepared_name)
        elif ext.lower() == ".mp4" and os.path.exists(output_path):
            final_path = os.path.abspath(output_path)
        else:
            raise FileNotFoundError(f"Downloaded video file could not be found at {prepared_name} or {expected_mp4}")

    print(f"Video successfully downloaded to: {final_path}")
    return final_path
