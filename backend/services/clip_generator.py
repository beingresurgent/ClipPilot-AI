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

    command += [
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
    ]

    if keep_original_audio:
        command += ["-c:a", "aac", "-b:a", "128k"]

    command += ["-movflags", "+faststart", str(output_path)]

    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(result.stderr[-2000:])

    return {
        "success": True,
        "filename": output_name,
        "path": str(output_path),
        "original_audio": keep_original_audio,
        "duration": round(end - start, 2),
    }
