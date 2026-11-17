import json
import subprocess
from pathlib import Path

FFPROBE = (
    r"C:\Users\omkar\Downloads"
    r"\ffmpeg-9.0.2-essentials_build"
    r"\ffmpeg-9.0.2-essentials_build"
    r"\bin\ffprobe.exe"
)


def analyze_video(video_path: str):

    path = Path(video_path)

    if not path.exists():
        raise FileNotFoundError("Video file not found")

    command = [
        FFPROBE,
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(path),
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=True)

    data = json.loads(result.stdout)

    video = next((s for s in data["streams"] if s["codec_type"] == "video"), None)

    audio = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)

    if video is None:
        raise ValueError("No video stream found")

    fps = video.get("avg_frame_rate", "0/1")

    if "/" in fps:
        numerator, denominator = map(int, fps.split("/"))
        fps = round(numerator / denominator, 2) if denominator else 0

    width = video.get("width")
    height = video.get("height")

    return {
        "filename": path.name,
        "duration_seconds": float(data["format"].get("duration", 0)),
        "resolution": f"{width}x{height}",
        "fps": fps,
        "video_codec": video.get("codec_name"),
        "audio_available": audio is not None,
        "audio_codec": audio.get("codec_name") if audio else None,
        "orientation": (
            "vertical"
            if height > width
            else "horizontal" if width > height else "square"
        ),
        "file_size_bytes": path.stat().st_size,
    }
