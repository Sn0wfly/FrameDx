from dataclasses import dataclass
from faster_whisper import WhisperModel


@dataclass
class WordTimestamp:
    word: str
    start: float
    end: float


@dataclass
class TranscriptSegment:
    text: str
    start: float
    end: float
    words: list[WordTimestamp]


def transcribe(
    audio_path: str,
    model_size: str = "large-v3",
    compute_type: str = "int8",
    language: str | None = None,
    progress_callback=None,
) -> list[TranscriptSegment]:
    """Transcribe audio file and return segments with word-level timestamps."""
    if progress_callback:
        progress_callback("Loading Whisper model...")

    model = WhisperModel(model_size, device="cpu", compute_type=compute_type)

    lang = None if language == "auto" else language

    if progress_callback:
        progress_callback("Transcribing audio...")

    segments_iter, info = model.transcribe(
        audio_path,
        language=lang,
        word_timestamps=True,
        vad_filter=True,
    )

    if progress_callback:
        progress_callback(f"Detected language: {info.language} (p={info.language_probability:.2f})")

    results = []
    for segment in segments_iter:
        words = []
        if segment.words:
            for w in segment.words:
                words.append(WordTimestamp(word=w.word.strip(), start=w.start, end=w.end))

        results.append(TranscriptSegment(
            text=segment.text.strip(),
            start=segment.start,
            end=segment.end,
            words=words,
        ))

    return results


def _format_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def segments_to_srt(segments: list[TranscriptSegment]) -> str:
    lines = []
    for i, seg in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{_format_srt_time(seg.start)} --> {_format_srt_time(seg.end)}")
        lines.append(seg.text)
        lines.append("")
    return "\n".join(lines)


def segments_to_text(segments: list[TranscriptSegment]) -> str:
    return "\n".join(seg.text for seg in segments)
