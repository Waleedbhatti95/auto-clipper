import os
import math
from typing import List, Dict, Any

from src.analyze_audio import detect_highlights
from src.analyze_vision import detect_visual_action
from src.clipper import cut_clip
from src.transcribe import generate_subtitles
from src.caption_render import burn_subtitles

def _normalize(values: List[float]) -> List[float]:
    if not values: return values
    lo, hi = min(values), max(values)
    span = hi - lo
    if span == 0: return [0.5] * len(values)
    return [(v - lo) / span for v in values]

def _build_combined_timeline(
    audio_highlights: List[Dict[str, Any]],
    vision_scores: List[Dict[str, Any]],
    total_duration: float,
    audio_weight: float,
    vision_weight: float,
) -> List[float]:
    total_secs = math.ceil(total_duration)
    combined = [0.0] * total_secs

    audio_raw = [0.0] * total_secs
    if audio_highlights:
        for hl in audio_highlights:
            start_s = int(hl["start"])
            end_s = min(int(math.ceil(hl["end"])), total_secs)
            peak_score = float(hl.get("score", 0.0))
            for s in range(start_s, end_s):
                if peak_score > audio_raw[s]: audio_raw[s] = peak_score

    audio_norm = _normalize(audio_raw)

    vision_map: Dict[int, float] = {}
    for entry in vision_scores:
        vision_map[int(entry["second"])] = float(entry["score"])

    vision_raw = [vision_map.get(s, 0.0) for s in range(total_secs)]
    vision_norm = _normalize(vision_raw)

    for s in range(total_secs):
        combined[s] = round(audio_weight * audio_norm[s] + vision_weight * vision_norm[s], 4)

    return combined

def _pick_top_highlights(
    combined: List[float],
    n: int,
    clip_duration: float,
    min_gap_sec: float,
    total_duration: float,
) -> List[Dict[str, Any]]:
    total_secs = len(combined)
    if total_secs == 0: return []

    sorted_secs = sorted(range(total_secs), key=lambda s: combined[s], reverse=True)
    accepted: List[int] = []
    
    for sec in sorted_secs:
        if len(accepted) >= n: break
        if all(abs(sec - a) >= min_gap_sec for a in accepted):
            accepted.append(sec)

    results: List[Dict[str, Any]] = []
    for sec in accepted:
        start = max(0.0, float(sec) - (clip_duration / 2))
        end = min(total_duration, start + clip_duration)
        if end == total_duration:
            start = max(0.0, end - clip_duration)

        if end > start:
            results.append({
                "peak_time": float(sec),
                "start": round(start, 2),
                "end": round(end, 2),
                "score": combined[sec],
            })

    results.sort(key=lambda h: h["start"])
    return results

def process_video(input_video_path: str, config: dict) -> List[str]:
    if not os.path.isfile(input_video_path):
        raise FileNotFoundError(f"Input video file not found: {input_video_path}")

    paths_cfg = config.get("paths", {})
    output_dir = paths_cfg.get("output_dir", "output")
    temp_dir = paths_cfg.get("temp_dir", "temp")
    audio_cfg = config.get("audio_analysis", config.get("audio", {}))
    vis_cfg = config.get("vision_analysis", config.get("vision", {}))
    video_out_cfg = config.get("video_output", {})

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)

    audio_weight: float = float(vis_cfg.get("audio_weight", 0.5))
    vision_weight: float = float(vis_cfg.get("vision_weight", 0.5))
    vision_enabled: bool = bool(vis_cfg.get("enabled", True))
    min_gap: float = float(audio_cfg.get("min_peak_distance_sec", 3))
    max_clips: int = int(config.get("output", {}).get("max_clips", 3))
    
    # NAYA: Manual Duration
    clip_duration: float = float(video_out_cfg.get("clip_duration_sec", 15))

    print("\n" + "=" * 65)
    print("STARTING AUTO-CLIPPER MASTER PIPELINE")
    print(f"Clip Duration : {clip_duration} seconds")
    print(f"Scoring       : audio×{audio_weight} + vision×{vision_weight}")
    print("=" * 65)

    print("\n[Step A] Analysing Audio...")
    audio_highlights = detect_highlights(video_path=input_video_path, config=config)

    if audio_highlights:
        total_duration: float = max(h["end"] for h in audio_highlights)
    else:
        import cv2
        cap = cv2.VideoCapture(input_video_path)
        fps_v = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames_v = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        total_duration = total_frames_v / fps_v

    vision_scores: List[Dict[str, Any]] = []
    if vision_enabled:
        print("\n[Step A2] Analysing Video Motion...")
        try:
            vision_scores = detect_visual_action(video_path=input_video_path, config=config)
        except Exception as exc:
            print(f"[Step A2] Vision analysis failed ({exc}). Continuing with audio only.")
            audio_weight, vision_weight = 1.0, 0.0
    else:
        audio_weight, vision_weight = 1.0, 0.0

    if not audio_highlights and not vision_scores:
        print("\n[Pipeline] No signal from audio or vision analysis. Exiting.")
        return []

    print("\n[Step B] Combining Scores...")
    combined_timeline = _build_combined_timeline(
        audio_highlights, vision_scores, total_duration, audio_weight, vision_weight
    )

    top_highlights = _pick_top_highlights(
        combined=combined_timeline,
        n=max_clips,
        clip_duration=clip_duration, 
        min_gap_sec=min_gap,
        total_duration=total_duration,
    )

    if not top_highlights:
        print("\n[Pipeline] Combined scoring found no highlight windows. Exiting.")
        return []

    final_clips: List[str] = []

    for idx, highlight in enumerate(top_highlights, 1):
        start_time = highlight["start"]
        end_time = highlight["end"]
        
        print("\n" + "-" * 65)
        print(f"--- Processing Highlight {idx} of {len(top_highlights)} ---")
        print(f"Time Window : {start_time:.2f}s -> {end_time:.2f}s ({end_time-start_time:.2f}s)")
        print("-" * 65)

        raw_clip_path = os.path.join(temp_dir, f"raw_highlight_{idx:02d}.mp4")
        cut_clip(input_path=input_video_path, start_time=start_time, end_time=end_time, output_path=raw_clip_path)

        ass_path = os.path.join(temp_dir, f"highlight_{idx:02d}.ass")
        generate_subtitles(video_path=raw_clip_path, output_ass_path=ass_path, config=config)

        final_output_path = os.path.join(output_dir, f"highlight_{idx:02d}.mp4")
        burn_subtitles(
            video_path=raw_clip_path, 
            ass_path=ass_path, 
            output_path=final_output_path,
            config=config # <-- Config pass kiya gaya hai
        )

        final_clips.append(final_output_path)

    print("\n" + "=" * 65)
    print(f"PIPELINE COMPLETE. {len(final_clips)} clips generated.")
    print("=" * 65)

    return final_clips