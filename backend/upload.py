import os
import uuid
from backend.services.clip_generator import generate_clip
from backend.services.viral_finder import find_viral_moments
from backend.services.transcription import transcribe_video
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from backend.video_analyzer import analyze_video

router = APIRouter()

UPLOAD_DIR = Path("storage/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi"}
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):

    extension = Path(file.filename or "").suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, detail="Only MP4, MOV, MKV and AVI videos are allowed"
        )

    filename = f"{uuid.uuid4().hex}{extension}"
    file_path = UPLOAD_DIR / filename

    size = 0

    try:
        with file_path.open("wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)

                if size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413, detail="Maximum file size is 2 GB"
                    )

                buffer.write(chunk)

    except Exception:
        file_path.unlink(missing_ok=True)
        raise

    finally:
        await file.close()

    return {
        "success": True,
        "filename": filename,
        "original_filename": file.filename,
        "size_bytes": size,
        "message": "Video uploaded successfully!",
    }


@router.get("/analyze/{filename}")
async def analyze_uploaded_video(filename: str):

    video_path = (UPLOAD_DIR / filename).resolve()

    if video_path.parent != UPLOAD_DIR.resolve():
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not video_path.is_file():
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        result = analyze_video(str(video_path))

        return {"success": True, "analysis": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transcribe/{filename}")
async def transcribe_uploaded_video(filename: str):

    video_path = (UPLOAD_DIR / filename).resolve()

    if video_path.parent != UPLOAD_DIR.resolve():
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not video_path.is_file():
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        result = transcribe_video(str(video_path))

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/find-moments/{filename}")
async def find_moments(filename: str, max_clips: int = 12):

    if max_clips < 1 or max_clips > 20:
        raise HTTPException(
            status_code=400, detail="max_clips must be between 1 and 20"
        )

    video_path = (UPLOAD_DIR / filename).resolve()

    if video_path.parent != UPLOAD_DIR.resolve():
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not video_path.is_file():
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        transcript = transcribe_video(str(video_path))

        result = find_viral_moments(transcript["segments"], max_clips=max_clips)

        return {"success": True, "language": transcript["language"], "analysis": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-clip/{filename}")
async def create_clip(
    filename: str, start: float, end: float, keep_original_audio: bool = True
):
    video_path = (UPLOAD_DIR / filename).resolve()

    if video_path.parent != UPLOAD_DIR.resolve():
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not video_path.is_file():
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        result = generate_clip(
            video_path=video_path,
            start=start,
            end=end,
            keep_original_audio=keep_original_audio,
        )
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-multiple-clips/{filename}")
async def create_multiple_clips(
    filename: str,
    max_clips: int = 12,
    keep_original_audio: bool = True,
    duration_mode: str = "auto",
    custom_duration: int = 30,
    min_duration: int = 15,
    max_duration: int = 60,
):
    if max_clips < 1 or max_clips > 20:
        raise HTTPException(
            status_code=400, detail="max_clips must be between 1 and 20"
        )

    video_path = (UPLOAD_DIR / filename).resolve()

    if video_path.parent != UPLOAD_DIR.resolve():
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not video_path.is_file():
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        transcript = transcribe_video(str(video_path))

        analysis = find_viral_moments(
            transcript["segments"],
            max_clips=max_clips,
            duration_mode=duration_mode,
            custom_duration=custom_duration,
            min_duration=min_duration,
            max_duration=max_duration,
        )

        generated_clips = []

        for moment in analysis["moments"]:
            clip = generate_clip(
                video_path=video_path,
                start=moment["start"],
                end=moment["end"],
                keep_original_audio=keep_original_audio,
            )

            generated_clips.append(
                {**clip, "score": moment["score"], "text": moment["text"]}
            )

        return {
            "success": True,
            "language": transcript["language"],
            "requested_clips": max_clips,
            "generated_clips": len(generated_clips),
            "clips": generated_clips,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
