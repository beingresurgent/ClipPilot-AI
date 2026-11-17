from faster_whisper import WhisperModel
from pathlib import Path

# RTX 3050 4GB ke liye safe starting configuration.
# CPU int8 pehle use karenge; GPU acceleration baad mein test karenge.
MODEL_SIZE = "small"

_model = None


def get_model():
    global _model

    if _model is None:
        _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")

    return _model


def transcribe_video(video_path: str):

    path = Path(video_path)

    if not path.is_file():
        raise FileNotFoundError("Video file not found")

    model = get_model()

    segments, info = model.transcribe(
        str(path), language=None, beam_size=5, vad_filter=True
    )

    transcript = []

    for segment in segments:
        transcript.append(
            {
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": segment.text.strip(),
            }
        )

    return {
        "success": True,
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "segments": transcript,
        "total_segments": len(transcript),
    }
