import re

HOOK_WORDS = [
    "secret",
    "truth",
    "never",
    "why",
    "how",
    "shocking",
    "danger",
    "mistake",
    "because",
    "impossible",
    "revealed",
    "warning",
    "but",
    "surprising",
    "hidden",
    "important",
]


def score_moment(text):
    text_lower = text.lower()
    score = 30

    for word in HOOK_WORDS:
        if re.search(r"\b" + re.escape(word) + r"\b", text_lower):
            score += 8

    if "?" in text:
        score += 12

    if "!" in text:
        score += 8

    if len(text.split()) >= 12:
        score += 10

    return min(score, 100)


def find_viral_moments(
    segments,
    max_clips=12,
    duration_mode="auto",
    custom_duration=30,
    min_duration=15,
    max_duration=60,
):
    if duration_mode not in ("auto", "custom"):
        raise ValueError("duration_mode must be auto or custom")

    if not 1 <= max_clips <= 20:
        raise ValueError("max_clips must be between 1 and 20")

    if not 5 <= min_duration <= max_duration <= 60:
        raise ValueError("Duration limits must be between 5 and 60 seconds")

    if not min_duration <= custom_duration <= max_duration:
        raise ValueError("custom_duration is outside allowed limits")

    if not segments:
        return {
            "total_candidates": 0,
            "requested_clips": max_clips,
            "selected_clips": 0,
            "duration_mode": duration_mode,
            "moments": [],
        }

    segments = sorted(segments, key=lambda s: float(s["start"]))
    video_end = max(float(s["end"]) for s in segments)

    target = custom_duration if duration_mode == "custom" else min(30, max_duration)

    # Source footage must be long enough.
    if video_end < min_duration:
        return {
            "total_candidates": 0,
            "requested_clips": max_clips,
            "selected_clips": 0,
            "duration_mode": duration_mode,
            "moments": [],
        }

    # If the source is shorter than the requested duration,
    # use the available footage, provided it meets min_duration.
    clip_duration = min(target, video_end)

    candidates = []

    for segment in segments:
        segment_start = float(segment["start"])

        # Keep some context before the interesting moment.
        start = max(0, segment_start - clip_duration * 0.25)

        # Keep the complete clip inside the available timeline.
        end = start + clip_duration

        if end > video_end:
            end = video_end
            start = max(0, end - clip_duration)

        if end - start < min_duration:
            continue

        text_parts = []
        score = 0

        for current in segments:
            current_start = float(current["start"])
            current_end = float(current["end"])

            if current_start < end and current_end > start:
                text = current.get("text", "").strip()

                if text:
                    text_parts.append(text)
                    score += score_moment(text)

        combined_text = " ".join(text_parts).strip()

        if len(combined_text.split()) < 8:
            continue

        candidates.append(
            {
                "start": round(start, 2),
                "end": round(end, 2),
                "duration": round(end - start, 2),
                "text": combined_text,
                "score": round(min(score, 100), 2),
            }
        )

    # Remove duplicate windows.
    unique_candidates = {}

    for candidate in candidates:
        key = (candidate["start"], candidate["end"])

        if key not in unique_candidates:
            unique_candidates[key] = candidate
        elif candidate["score"] > unique_candidates[key]["score"]:
            unique_candidates[key] = candidate

    candidates = list(unique_candidates.values())
    candidates.sort(key=lambda item: item["score"], reverse=True)

    selected = []

    for candidate in candidates:
        overlaps = any(
            candidate["start"] < item["end"] and candidate["end"] > item["start"]
            for item in selected
        )

        if not overlaps:
            selected.append(candidate)

        if len(selected) >= max_clips:
            break

    selected.sort(key=lambda item: item["start"])

    return {
        "total_candidates": len(candidates),
        "requested_clips": max_clips,
        "selected_clips": len(selected),
        "duration_mode": duration_mode,
        "moments": selected,
    }
