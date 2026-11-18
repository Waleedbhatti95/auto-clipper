"""
Vision analysis module for highlight detection.
Detects high-motion scenes (fast movement, action, explosions) using
Optical Flow (Farneback) between downscaled consecutive frames.

Returns a per-second normalized motion score timeline that can be
combined with audio RMS scores in the pipeline for a richer highlight rank.
"""

import os
import sys
import math
from typing import List, Dict, Any

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_visual_action(video_path: str, config: dict) -> List[Dict[str, Any]]:
    """
    Analyze video frames to build a per-second motion score timeline.

    Strategy
    --------
    - Sample frames at a low FPS (default 2 fps) to stay efficient.
    - Downscale each frame to 480p-height (maintaining aspect ratio) before
      computing Optical Flow — this keeps Farneback fast even on long videos.
    - Compute dense Optical Flow (Farneback) between consecutive sampled frames.
    - Convert flow vectors to magnitude; average magnitude = motion score for
      that inter-frame interval.
    - Bucket motion scores into whole-second bins, then normalize [0, 1].
    - Return a list of per-second dicts: {"second": int, "score": float}.

    Args:
        video_path: Path to the input video file.
        config:     Full config dict (uses vision_analysis section).

    Returns:
        List of dicts [{\"second\": int, \"score\": float}, ...] sorted by second.
        Returns an empty list on failure.
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Input video not found: {video_path}")

    vis_cfg = config.get("vision_analysis", config.get("vision", {}))
    fps_to_sample: int = int(vis_cfg.get("fps_to_sample", 2))
    target_height: int = int(vis_cfg.get("downscale_height", 480))

    print(f"\n[Vision Analysis] Processing: '{video_path}'")
    print(f"[Vision Analysis] Config -> Sample FPS: {fps_to_sample} | Downscale height: {target_height}px")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[Vision Analysis] ERROR: Could not open video '{video_path}'.")
        return []

    native_fps: float = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames: int = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    total_duration: float = total_frames / native_fps if native_fps > 0 else 0.0

    print(f"[Vision Analysis] Video info: {total_duration:.2f}s | {native_fps:.2f} native FPS | {total_frames} frames")

    if total_duration <= 0:
        print("[Vision Analysis] WARNING: Could not determine video duration. Skipping.")
        cap.release()
        return []

    # Interval in native frames between each sampled frame
    frame_interval: int = max(1, int(round(native_fps / fps_to_sample)))
    print(f"[Vision Analysis] Sampling every {frame_interval} native frame(s) (~{fps_to_sample} fps)...")

    # --- Helper: downscale a frame to target_height while keeping aspect ratio ---
    def _downscale(frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        if h <= target_height:
            return frame
        scale = target_height / h
        new_w = int(w * scale)
        return cv2.resize(frame, (new_w, target_height), interpolation=cv2.INTER_LINEAR)

    # Collect (timestamp_sec, motion_score) pairs
    motion_samples: List[tuple] = []  # (timestamp_sec, mean_magnitude)

    prev_gray: np.ndarray | None = None
    prev_timestamp: float = 0.0
    frame_idx: int = 0
    sampled: int = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            timestamp_sec: float = frame_idx / native_fps
            small = _downscale(frame)
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

            if prev_gray is not None and gray.shape == prev_gray.shape:
                flow = cv2.calcOpticalFlowFarneback(
                    prev_gray, gray,
                    None,
                    pyr_scale=0.5,
                    levels=3,
                    winsize=15,
                    iterations=3,
                    poly_n=5,
                    poly_sigma=1.2,
                    flags=0,
                )
                # Magnitude of each pixel's flow vector
                mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                mean_mag: float = float(np.mean(mag))

                # Attribute the motion score to the midpoint between frames
                mid_time = (prev_timestamp + timestamp_sec) / 2.0
                motion_samples.append((mid_time, mean_mag))

            prev_gray = gray
            prev_timestamp = timestamp_sec
            sampled += 1

        frame_idx += 1

    cap.release()
    print(f"[Vision Analysis] Processed {sampled} sampled frames → {len(motion_samples)} motion measurements.")

    if not motion_samples:
        print("[Vision Analysis] No motion data collected. Returning empty timeline.")
        return []

    # --- Bucket into whole-second bins ---
    total_secs: int = math.ceil(total_duration)
    second_scores: List[float] = [0.0] * total_secs
    second_counts: List[int] = [0] * total_secs

    for ts, score in motion_samples:
        bucket = min(int(ts), total_secs - 1)
        second_scores[bucket] += score
        second_counts[bucket] += 1

    # Average within each bucket
    averaged: List[float] = [
        (second_scores[s] / second_counts[s]) if second_counts[s] > 0 else 0.0
        for s in range(total_secs)
    ]

    # --- Normalize [0, 1] ---
    max_val = max(averaged) if averaged else 1.0
    if max_val == 0.0:
        max_val = 1.0
    normalized: List[float] = [v / max_val for v in averaged]

    results: List[Dict[str, Any]] = [
        {"second": s, "score": round(normalized[s], 4)}
        for s in range(total_secs)
    ]

    # Quick summary: top-5 seconds by motion
    top5 = sorted(results, key=lambda x: x["score"], reverse=True)[:5]
    top5_str = ", ".join(f"{d['second']}s({d['score']:.2f})" for d in top5)
    print(f"[Vision Analysis] Done. {total_secs} second(s) scored. Top motion moments: [{top5_str}]")

    return results
