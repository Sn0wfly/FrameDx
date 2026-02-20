from dataclasses import dataclass

from framedx.core.frame_extractor import DetectedSlide
from framedx.core.transcriber import TranscriptSegment


@dataclass
class CardPair:
    image_path: str
    slide_timestamp: float
    transcript_text: str
    included: bool = True


def match_slides_to_transcript(
    slides: list[DetectedSlide],
    segments: list[TranscriptSegment],
    matching_window: float = 10.0,
    pre_context_seconds: float = 5.0,
) -> list[CardPair]:
    """Match each detected slide to the transcript text around its timestamp.

    For each slide, grabs text from (slide_time - pre_context_seconds)
    to (slide_time + matching_window).
    """
    if not slides or not segments:
        return []

    # Flatten all words with their timestamps for precise matching
    all_words: list[tuple[str, float, float]] = []
    for seg in segments:
        if seg.words:
            for w in seg.words:
                all_words.append((w.word, w.start, w.end))
        else:
            # Fallback: use segment-level timestamps
            all_words.append((seg.text, seg.start, seg.end))

    pairs = []
    for slide in slides:
        window_start = max(0, slide.timestamp - pre_context_seconds)
        window_end = slide.timestamp + matching_window

        matched_words = [
            word for word, start, end in all_words
            if start >= window_start and start <= window_end
        ]

        text = " ".join(matched_words).strip()

        pairs.append(CardPair(
            image_path=slide.image_path,
            slide_timestamp=slide.timestamp,
            transcript_text=text if text else "(no transcript detected)",
        ))

    return pairs
