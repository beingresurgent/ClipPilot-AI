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

    segments = sorted(segments, key=lambda s: s["start"])

    video_end = max(float(s["end"]) for s in segments)
    candidates = []

    for index, segment in enumerate(segments):
        start = float(segment["start"])
        text_parts = []
        last_end = start
        score = 0

        for current in segments[index:]:
            current_start = float(current["start"])
            current_end = float(current["end"])

            if current_start - last_end > 2.0:
                break

            if duration_mode == "custom":
                target = custom_duration
            else:
                target = 30

            if current_end - start > target:
                break

            text_parts.append(current["text"].strip())
            score += score_moment(current["text"])
            last_end = current_end

            duration = last_end - start
            text = " ".join(text_parts).strip()

            if duration < min_duration:
                continue

            if len(text.split()) < 8:
                continue

            if duration_mode == "auto":
                ideal_duration = 30
                score_adjusted = score - abs(duration - ideal_duration) * 0.3
            else:
                score_adjusted = score

            candidates.append(
                {
                    "start": round(start, 2),
                    "end": round(last_end, 2),
                    "duration": round(duration, 2),
                    "text": text,
                    "score": round(min(score_adjusted, 100), 2),
                }
            )

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
