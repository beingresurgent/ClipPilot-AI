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
    "surprising",
    "hidden",
    "important",
    "amazing",
    "crazy",
    "insane",
    "worst",
    "best",
    "unbelievable",
    "surprise",
    "finally",
    "epic",
]


def score_moment(text):
    text_lower = text.lower().strip()
    words = text_lower.split()

    if not words:
        return 0

    score = 20

    hook_matches = sum(
        1
        for word in HOOK_WORDS
        if re.search(r"\b" + re.escape(word) + r"\b", text_lower)
    )
    score += min(hook_matches * 7, 28)

    curiosity_phrases = [
        "what happened",
        "you won't believe",
        "the truth",
        "guess what",
        "but wait",
        "how did",
        "why is",
        "what if",
    ]

    if any(phrase in text_lower for phrase in curiosity_phrases):
        score += 12

    emotion_words = [
        "amazing",
        "crazy",
        "insane",
        "unbelievable",
        "terrifying",
        "shocking",
        "funny",
        "incredible",
        "dangerous",
        "secret",
        "impossible",
        "epic",
    ]

    emotion_matches = sum(
        1
        for word in emotion_words
        if re.search(r"\b" + re.escape(word) + r"\b", text_lower)
    )
    score += min(emotion_matches * 5, 15)

    if "?" in text:
        score += 8

    if "!" in text:
        score += 5

    if 8 <= len(words) <= 35:
        score += 10
    elif len(words) < 5:
        score -= 10

    if text_lower.endswith(("and", "but", "or", "because", "with", "to")):
        score -= 5

    return max(0, min(round(score), 100))


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

    if video_end < min_duration:
        return {
            "total_candidates": 0,
            "requested_clips": max_clips,
            "selected_clips": 0,
            "duration_mode": duration_mode,
            "moments": [],
        }

    clip_duration = min(target, video_end)

    # Generate overlapping candidate windows.
    # Final selection will remove overlapping clips.
    step = max(1, clip_duration / 2)

    starts = []
    position = 0.0

    while position + clip_duration <= video_end:
        starts.append(position)
        position += step

    # Ensure the final part of the video is also checked.
    final_start = max(0, video_end - clip_duration)
    starts.append(final_start)

    # Remove duplicate start positions.
    starts = sorted(set(round(s, 2) for s in starts))

    candidates = []

    for start in starts:
        end = min(start + clip_duration, video_end)
        duration = end - start

        if duration < min_duration:
            continue

        text_parts = []
        segment_scores = []

        for segment in segments:
            segment_start = float(segment["start"])
            segment_end = float(segment["end"])

            if segment_start < end and segment_end > start:
                text = segment.get("text", "").strip()

                if text:
                    text_parts.append(text)
                    segment_scores.append(score_moment(text))

        combined_text = " ".join(text_parts).strip()

        if len(combined_text.split()) < 8:
            continue

        average_score = (
            sum(segment_scores) / len(segment_scores) if segment_scores else 0
        )

        if duration_mode == "auto":
            score_adjusted = average_score - abs(duration - 30) * 0.3
        else:
            score_adjusted = average_score

        candidates.append(
            {
                "start": round(start, 2),
                "end": round(end, 2),
                "duration": round(duration, 2),
                "text": combined_text,
                "score": round(max(0, min(score_adjusted, 100)), 2),
            }
        )

    # Rank candidates by score.
    candidates.sort(key=lambda item: item["score"], reverse=True)

    # Select only non-overlapping clips.
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
