import os
import sys
import types
import whisper

# Windows compatibility fix
try:
    import numpy.random
except Exception:
    mock_random = types.ModuleType("numpy.random")
    mock_random.__path__ = []
    mock_bit_generator = types.ModuleType("numpy.random.bit_generator")
    class BitGenerator: pass
    class Generator: pass
    class RandomState: pass
    mock_bit_generator.BitGenerator = BitGenerator
    mock_random.bit_generator = mock_bit_generator
    mock_random.Generator = Generator
    mock_random.RandomState = RandomState
    sys.modules["numpy.random"] = mock_random
    sys.modules["numpy.random.bit_generator"] = mock_bit_generator
    import numpy as _np
    _np.random = mock_random

def format_time_ass(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int((seconds - int(seconds)) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"

def generate_subtitles(video_path: str, output_ass_path: str, config: dict) -> str:
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Input video file not found: {video_path}")

    whisper_cfg = config.get("whisper", {})
    paths_cfg = config.get("paths", {})
    style_cfg = config.get("caption_styling", {})

    model_size = whisper_cfg.get("model_size", "tiny")
    language = whisper_cfg.get("language", "en")
    models_dir = paths_cfg.get("models_dir", "models")

    # Styling Variables from Config
    font_name = style_cfg.get("font_name", "Arial")
    font_size = style_cfg.get("font_size", 85)
    primary_color = style_cfg.get("primary_color", "&H0000FFFF")
    outline_color = style_cfg.get("outline_color", "&H00000000")
    animation = style_cfg.get("animation", "pop").lower()

    os.makedirs(os.path.dirname(output_ass_path) or ".", exist_ok=True)
    model = whisper.load_model(model_size, download_root=models_dir)
    result = model.transcribe(video_path, language=language, word_timestamps=True)

    # Dynamic ASS Header based on Config
    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary_color},&H000000FF,{outline_color},&H00000000,-1,0,0,0,100,100,0,0,1,6,0,2,10,10,150,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    dialogue_lines = []
    
    for segment in result.get("segments", []):
        words = segment.get("words", [])
        if not words: continue

        chunk_size = 3 # 3 words per screen
        for i in range(0, len(words), chunk_size):
            chunk = words[i:i + chunk_size]
            start_time = chunk[0]["start"]
            end_time = chunk[-1]["end"]
            text = " ".join([w["word"].strip() for w in chunk]).upper()
            if not text: continue

            # Animation Logic
            anim_tag = ""
            if animation == "fade":
                anim_tag = r"{\fad(100,100)}" 
            elif animation == "pop":
                anim_tag = r"{\t(0,200,\fscx110\fscy110)}"

            start_str = format_time_ass(start_time)
            end_str = format_time_ass(end_time)
            dialogue_lines.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{anim_tag}{text}")

    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(dialogue_lines))

    return os.path.abspath(output_ass_path)