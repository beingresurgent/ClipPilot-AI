import subprocess
import uuid
from pathlib import Path

CLIPS_DIR = Path("storage/clips")
CLIPS_DIR.mkdir(parents=True, exist_ok=True)


def generate_clip(video_path, start, end, keep_original_audio=True):
    video_path = Path(video_path).resolve()

    if not video_path.is_file():
        raise FileNotFoundError("Source video not found")

    start = float(start)
    end = float(end)

    if start < 0 or end <= start:
        raise ValueError("Invalid clip timestamps")

    output_name = f"clip_{uuid.uuid4().hex[:10]}.mp4"
    output_path = CLIPS_DIR / output_name

    base_command = [
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
        base_command += ["-map", "0:a:0?"]
    else:
        base_command += ["-an"]

    # First try NVIDIA GPU encoder
    nvenc_command = base_command + [
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

    if keep_original_audio:
        nvenc_command += ["-c:a", "aac", "-b:a", "128k"]

    nvenc_command += ["-movflags", "+faststart", str(output_path)]

    # CPU fallback if NVIDIA encoding fails
    cpu_command = base_command + [
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
        cpu_command += ["-c:a", "aac", "-b:a", "128k"]

    cpu_command += ["-movflags", "+faststart", str(output_path)]

    result = subprocess.run(
        nvenc_command,
        capture_output=True,
        text=True,
    )

    encoder_used = "h264_nvenc"

    if result.returncode != 0:
        # Remove any incomplete output before CPU fallback
        output_path.unlink(missing_ok=True)

        result = subprocess.run(
            cpu_command,
            capture_output=True,
            text=True,
        )

        encoder_used = "libx264"

    if result.returncode != 0:
        output_path.unlink(missing_ok=True)
        raise RuntimeError(result.stderr[-2000:])

    return {
        "success": True,
        "filename": output_name,
        "path": str(output_path),
        "original_audio": keep_original_audio,
        "duration": round(end - start, 2),
        "encoder": encoder_used,
    }
