import re

HOOK_WORDS = [
    "secret", "truth", "never", "why", "how", "shocking",
    "danger", "mistake", "because", "impossible", "revealed",
    "warning", "surprising", "hidden", "important", "amazing",
    "crazy", "insane", "worst", "best", "unbelievable",
    "surprise", "finally", "epic", "betrayal", "attack",
    "escape", "death", "mission", "enemy", "explosion"
]

CURIOSITY_PHRASES = [
    "what happened", "you won't believe", "the truth",
    "guess what", "but wait", "how did", "why is",
    "what if", "find out", "what they are hiding"
]

EMOTION_WORDS = [
    "amazing", "crazy", "insane", "unbelievable",
    "terrifying", "shocking", "funny", "incredible",
    "dangerous", "secret", "impossible", "epic",
    "killed", "attack", "enemy", "explosion"
]


def score_moment(text):
    text_lower = text.lower().strip()
    words = re.findall(r"\b[\w']+\b", text_lower)

    if not words:
        return 0

    score = 20

    hooks = sum(
        bool(re.search(r"\b" + re.escape(word) + r"\b", text_lower))
        for word in HOOK_WORDS
    )
    score += min(hooks * 6, 24)

    curiosity = sum(
        phrase in text_lower for phrase in CURIOSITY_PHRASES
    )
    score += min(curiosity * 10, 20)

    emotion = sum(
        bool(re.search(r"\b" + re.escape(word) + r"\b", text_lower))
        for word in EMOTION_WORDS
    )
    score += min(emotion * 4, 16)

    if "?" in text:
        score += 7

    if "!" in text:
        score += 5

    if 8 <= len(words) <= 45:
        score += 10
    elif len(words) < 5:
        score -= 10

    if text_lower.endswith(
        ("and", "but", "or", "because", "with", "to")
    ):
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

    segments = sorted(
        segments or [],
        key=lambda s: float(s["start"])
    )

    video_end = max(
        (float(s["end"]) for s in segments),
        default=0
    )

    empty_result = {
        "total_candidates": 0,
        "requested_clips": max_clips,
        "selected_clips": 0,
        "duration_mode": duration_mode,
        "moments": [],
    }

    if video_end < min_duration:
        return empty_result

    if duration_mode == "custom":
        durations = [custom_duration]
    else:
        # Automatically test different clip lengths.
        durations = [
            min_duration, 20, 25, 30, 35, 40, 45, 50, max_duration
        ]
        durations = sorted(set(
            d for d in durations
            if min_duration <= d <= max_duration
            and d <= video_end
        ))

        if not durations:
            durations = [min(video_end, max_duration)]

    candidates = []
    seen = set()

    for clip_duration in durations:
        if clip_duration > video_end:
            continue

        max_start = max(0, video_end - clip_duration)

        # Check regular windows and transcript-aligned starts.
        starts = set()
        position = 0.0

        while position <= max_start:
            starts.add(round(position, 2))
            position += 5

        starts.add(round(max_start, 2))

        for segment in segments:
            segment_start = float(segment["start"])

            for proposed in (
                segment_start,
                segment_start - 2,
                segment_start - clip_duration / 2
            ):
                starts.add(round(
                    max(0, min(proposed, max_start)), 2
                ))

        for start in sorted(starts):
            end = min(start + clip_duration, video_end)
            key = (round(start, 2), round(end, 2))

            if key in seen:
                continue
            seen.add(key)

            text_parts = []
            weighted_scores = []
            speech_time = 0.0

            for segment in segments:
                seg_start = float(segment["start"])
                seg_end = float(segment["end"])

                overlap = max(
                    0,
                    min(end, seg_end) - max(start, seg_start)
                )

                if overlap <= 0:
                    continue

                text = segment.get("text", "").strip()

                if not text:
                    continue

                text_parts.append(text)
                weighted_scores.append(
                    (score_moment(text), overlap)
                )
                speech_time += overlap

            combined_text = " ".join(text_parts).strip()
            word_count = len(combined_text.split())

            if word_count < 5 or not weighted_scores:
                continue

            total_weight = sum(
                weight for _, weight in weighted_scores
            )

            average_score = sum(
                score * weight
                for score, weight in weighted_scores
            ) / total_weight

            speech_density = min(
                speech_time / max(end - start, 1), 1
            )

            # Reward meaningful speech without over-rewarding
            # long clips or dense transcripts.
            final_score = (
                average_score * 0.80
                + speech_density * 12
            )

            if duration_mode == "auto":
                final_score -= max(0, clip_duration - 35) * 0.12

            candidates.append({
                "start": round(start, 2),
                "end": round(end, 2),
                "duration": round(end - start, 2),
                "text": combined_text,
                "score": round(
                    max(0, min(final_score, 100)), 2
                ),
            })

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    selected = []

    for candidate in candidates:
        overlaps = any(
            candidate["start"] < item["end"]
            and candidate["end"] > item["start"]
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
