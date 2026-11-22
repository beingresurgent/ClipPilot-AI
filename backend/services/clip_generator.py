```python
import subprocess
import uuid
from pathlib import Path

CLIPS_DIR = Path("storage/clips")
CLIPS_DIR.mkdir(parents=True, exist_ok=True)

FORMATS = {"landscape", "vertical"}


def generate_clip(
    video_path,
    start,
    end,
    keep_original_audio=True,
    output_format="landscape",
):
    video_path = Path(video_path).resolve()

    if not video_path.is_file():
        raise FileNotFoundError("Source video not found")

    if output_format not in FORMATS:
        raise ValueError("Invalid output format")

    start, end = float(start), float(end)

    if start < 0 or end <= start:
        raise ValueError("Invalid clip timestamps")

    output_path = CLIPS_DIR / f"clip_{uuid.uuid4().hex[:10]}.mp4"

    command = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start),
        "-i",
        str(video_path),
        "-t",
        str(end - start),
        "-map",
        "0:v:0",
    ]

    if keep_original_audio:
        command += ["-map", "0:a:0?"]
    else:
        command += ["-an"]

    if output_format == "vertical":
        video_filter = (
            "scale=1080:1920:"
            "force_original_aspect_ratio=increase,"
            "crop=1080:1920"
        )
        command += ["-vf", video_filter]

    nvenc = command + [
        "-c:v",
        "h264_nvenc",
        "-preset",
        "p4",
        "-cq",
        "23",
        "-b:v",
        "0",
        "-pix_fmt",
        "yuv420p",
    ]

    cpu = command + [
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
    ]

    if keep_original_audio:
        audio_options = ["-c:a", "aac", "-b:a", "128k"]
        nvenc += audio_options
        cpu += audio_options

    nvenc += ["-movflags", "+faststart", str(output_path)]
    cpu += ["-movflags", "+faststart", str(output_path)]

    result = subprocess.run(
        nvenc,
        capture_output=True,
        text=True,
    )
    encoder = "h264_nvenc"

    if result.returncode != 0:
        output_path.unlink(missing_ok=True)

        result = subprocess.run(
            cpu,
            capture_output=True,
            text=True,
        )
        encoder = "libx264"

    if result.returncode != 0:
        output_path.unlink(missing_ok=True)
        raise RuntimeError(result.stderr[-2000:])

    return {
        "success": True,
        "filename": output_path.name,
        "path": str(output_path),
        "original_audio": keep_original_audio,
        "duration": round(end - start, 2),
        "encoder": encoder,
        "output_format": output_format,
    }
