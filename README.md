# Auto Video Clipper

A Python-based automated video clipping system designed to ingest gameplay videos, detect highlight moments using combined audio and vision analysis, generate accurate synchronized subtitles with Whisper, and render polished short-form clips with burned-in captions via FFmpeg.

---

## Features

- **Video Ingestion**: Fetch videos from YouTube/streams (`yt-dlp`) or ingest local raw gameplay files.
- **Multimodal Highlight Detection**:
  - **Audio Analysis**: RMS energy thresholding, peak detection, and audio excitement scoring (`librosa`, `scipy`).
  - **Vision Analysis**: Scene change detection, optical flow/motion analysis, and HUD/template matching (`opencv-python`).
  - **Weighted Scoring**: Multi-factor scoring model combining audio spikes, motion dynamics, and HUD events.
- **Automated Transcription & Alignment**: Word-level caption generation using `openai-whisper` and `whisperx`.
- **Clip Production**: Automated clipping, aspect ratio conversion (e.g., 9:16 vertical shorts), and subtitle burning via `FFmpeg` and `moviepy`.
- **Interfaces**: Streamlit dashboard for interactive review and FastAPI for programmatic pipeline runs.

---

## Folder Structure

```text
auto-clipper/
│
├── src/                  # Core Python modules and pipeline logic
│   └── __init__.py
│
├── input/                # Raw input videos (ignored by git)
│   └── .gitkeep
│
├── output/               # Rendered final clips and exports (ignored by git)
│   └── .gitkeep
│
├── temp/                 # Temporary working files (frames, extracted audio, intermediates)
│   └── .gitkeep
│
├── models/               # Local ML model weights and checkpoints (ignored by git)
│   └── .gitkeep
│
├── tests/                # Unit and integration test suites
│   └── __init__.py
│
├── config.yaml           # Pipeline configuration and parameter tuning
├── requirements.txt      # Project dependencies
├── .gitignore            # Git ignore rules for environments, temp files, and media
└── README.md             # Project documentation
```

---

## Prerequisites

1. **Python 3.10+**
2. **FFmpeg**: Ensure `ffmpeg` and `ffprobe` are installed and added to your system's `PATH`.
   - Windows: Install via `winget install Gyan.FFmpeg` or `choco install ffmpeg`.
   - Linux: `sudo apt update && sudo apt install ffmpeg`
   - macOS: `brew install ffmpeg`
3. *(Optional)* **NVIDIA GPU with CUDA**: Recommended for accelerated Whisper transcription and computer vision tasks.

---

## Setup Instructions

1. **Clone or navigate into the repository**:
   ```bash
   cd auto-clipper
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**:
   - **Windows (PowerShell)**:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - **Windows (CMD)**:
     ```cmd
     .\venv\Scripts\activate.bat
     ```
   - **Linux / macOS**:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## Configuration

Pipeline parameters can be customized in [`config.yaml`](./config.yaml):

- **`paths`**: Directory paths for input videos, outputs, temporary cache, and model weights.
- **`audio`**: Sampling rates, RMS percentile thresholds, and clip window durations.
- **`vision`**: Template matching thresholds and sample FPS for frame analysis.
- **`scoring`**: Weights for balancing audio excitement, motion activity, and HUD event triggers.
- **`whisper`**: Model scale (`tiny`, `base`, `small`, `medium`, `large-v2`/`large-v3`), compute device, and language.
- **`output`**: Max number of clips generated and aspect ratio format settings.
