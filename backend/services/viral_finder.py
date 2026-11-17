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


def find_viral_moments(segments, max_clips=12):
    candidates = []

    for segment in segments:
        text = segment["text"].strip()
        duration = segment["end"] - segment["start"]

        if duration < 2 or len(text.split()) < 4:
            continue

        score = score_moment(text)

        candidates.append(
            {
                "start": segment["start"],
                "end": segment["end"],
                "duration": round(duration, 2),
                "text": text,
                "score": score,
            }
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)

    selected = candidates[:max_clips]

    return {
        "total_candidates": len(candidates),
        "requested_clips": max_clips,
        "selected_clips": len(selected),
        "moments": selected,
    }
