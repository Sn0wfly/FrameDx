import os
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from framedx.core.frame_extractor import DetectedSlide, extract_slides
from framedx.core.llm_corrector import correct_transcripts
from framedx.core.matcher import CardPair, match_slides_to_transcript
from framedx.core.transcriber import TranscriptSegment, transcribe, segments_to_srt, segments_to_text


class PipelineWorker(QObject):
    """Runs the full processing pipeline in a background thread."""

    progress = Signal(str, int)  # (message, percentage)
    file_started = Signal(str)  # video filename
    file_finished = Signal(str, list)  # (video filename, list[CardPair])
    file_error = Signal(str, str)  # (video filename, error message)
    all_finished = Signal()

    def __init__(self, video_paths: list[str], settings: dict, parent=None):
        super().__init__(parent)
        self.video_paths = video_paths
        self.settings = settings
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        for i, video_path in enumerate(self.video_paths):
            if self._cancelled:
                break

            filename = Path(video_path).name
            self.file_started.emit(filename)

            try:
                pairs = self._process_single(video_path, i, len(self.video_paths))
                self.file_finished.emit(filename, pairs)
            except Exception as e:
                self.file_error.emit(filename, str(e))

        self.all_finished.emit()

    def _process_single(self, video_path: str, file_idx: int, total_files: int) -> list[CardPair]:
        base_pct = int(file_idx / total_files * 100)
        file_weight = 100 / total_files

        def emit(msg, local_pct=0):
            overall = base_pct + int(local_pct / 100 * file_weight)
            self.progress.emit(msg, min(overall, 99))

        # Create temp working directory for this video
        work_dir = tempfile.mkdtemp(prefix="framedx_")

        # Step 1: Extract audio via ffmpeg
        emit("[1/4] Extracting audio with ffmpeg...", 0)
        audio_path = os.path.join(work_dir, "audio.wav")
        self._extract_audio(video_path, audio_path)
        audio_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        emit(f"[1/4] Audio extracted ({audio_size_mb:.1f} MB)", 5)

        if self._cancelled:
            return []

        # Step 2: Transcribe
        model_name = self.settings.get("whisper_model", "large-v3")
        compute = self.settings.get("compute_type", "int8")
        emit(f"[2/4] Loading Whisper model ({model_name}, {compute})... this may take a minute", 8)
        segments = transcribe(
            audio_path,
            model_size=model_name,
            compute_type=compute,
            language=self.settings.get("language", "auto") or None,
            progress_callback=lambda msg: emit(f"[2/4] {msg}", 30),
        )
        total_words = sum(len(s.words) for s in segments)
        emit(f"[2/4] Transcription complete — {len(segments)} segments, {total_words} words", 50)

        if self._cancelled:
            return []

        # Step 3: Extract frames and detect slides
        emit("[3/4] Scanning video for slide changes...", 55)
        slides = extract_slides(
            video_path,
            work_dir,
            ssim_threshold=self.settings.get("ssim_threshold", 0.85),
            frame_interval=self.settings.get("frame_interval", 2.0),
            progress_callback=lambda msg: emit(f"[3/4] {msg}", 70),
        )
        emit(f"[3/4] Slide detection complete — {len(slides)} slides found", 80)

        if self._cancelled:
            return []

        # Step 4: Match slides to transcript
        emit("[4/4] Matching slides to transcript segments...", 85)
        pairs = match_slides_to_transcript(
            slides,
            segments,
            matching_window=self.settings.get("matching_window", 10),
            pre_context_seconds=self.settings.get("pre_context_seconds", 5),
        )
        emit(f"[4/4] Matched {len(pairs)} slide-transcript pairs", 90)

        # Optional: LLM correction
        if self.settings.get("use_llm_correction") and self.settings.get("anthropic_api_key"):
            emit("Correcting medical terms via LLM...", 92)
            texts = [p.transcript_text for p in pairs]
            corrected = correct_transcripts(
                texts,
                self.settings["anthropic_api_key"],
                progress_callback=lambda msg: emit(msg, 95),
            )
            for pair, text in zip(pairs, corrected):
                pair.transcript_text = text

        emit(f"Done — {len(pairs)} cards ready for review", 100)
        return pairs

    def _extract_audio(self, video_path: str, audio_path: str):
        """Extract audio from video using ffmpeg subprocess."""
        import subprocess

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            audio_path,
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr[:500]}")


class TranscriptWorker(QObject):
    """Transcription-only worker: outputs .txt and/or .srt files."""

    progress = Signal(str, int)
    file_started = Signal(str)
    file_finished = Signal(str, list)  # (filename, []) — empty list, no card pairs
    file_error = Signal(str, str)
    all_finished = Signal()

    def __init__(self, video_paths: list[str], settings: dict, output_dir: str,
                 export_txt: bool = True, export_srt: bool = True, parent=None):
        super().__init__(parent)
        self.video_paths = video_paths
        self.settings = settings
        self.output_dir = output_dir
        self.export_txt = export_txt
        self.export_srt = export_srt
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        for i, video_path in enumerate(self.video_paths):
            if self._cancelled:
                break

            filename = Path(video_path).name
            stem = Path(video_path).stem
            self.file_started.emit(filename)

            try:
                pct_base = int(i / len(self.video_paths) * 100)
                weight = 100 / len(self.video_paths)

                def emit(msg, local_pct=0):
                    overall = pct_base + int(local_pct / 100 * weight)
                    self.progress.emit(msg, min(overall, 99))

                # Extract audio
                emit(f"[1/2] Extracting audio...", 0)
                import tempfile
                work_dir = tempfile.mkdtemp(prefix="framedx_transcript_")
                audio_path = os.path.join(work_dir, "audio.wav")
                self._extract_audio(video_path, audio_path)
                emit(f"[1/2] Audio extracted", 10)

                if self._cancelled:
                    break

                # Transcribe
                model_name = self.settings.get("whisper_model", "large-v3")
                compute = self.settings.get("compute_type", "int8")
                emit(f"[2/2] Transcribing ({model_name}, {compute})...", 15)
                segments = transcribe(
                    audio_path,
                    model_size=model_name,
                    compute_type=compute,
                    language=self.settings.get("language", "auto") or None,
                    progress_callback=lambda msg: emit(f"[2/2] {msg}", 50),
                )

                # Write output files
                os.makedirs(self.output_dir, exist_ok=True)
                saved = []
                if self.export_txt:
                    txt_path = os.path.join(self.output_dir, f"{stem}.txt")
                    with open(txt_path, "w", encoding="utf-8") as f:
                        f.write(segments_to_text(segments))
                    saved.append(txt_path)

                if self.export_srt:
                    srt_path = os.path.join(self.output_dir, f"{stem}.srt")
                    with open(srt_path, "w", encoding="utf-8") as f:
                        f.write(segments_to_srt(segments))
                    saved.append(srt_path)

                total_words = sum(len(s.words) for s in segments)
                emit(f"Done — {len(segments)} segments, {total_words} words → {', '.join(Path(p).name for p in saved)}", 100)
                self.file_finished.emit(filename, [])

            except Exception as e:
                self.file_error.emit(filename, str(e))

        self.all_finished.emit()

    def _extract_audio(self, video_path: str, audio_path: str):
        import subprocess
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            audio_path,
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr[:500]}")


class SlidesWorker(QObject):
    """Slides-only worker: extracts slide images to a named folder."""

    progress = Signal(str, int)
    file_started = Signal(str)
    file_finished = Signal(str, list)  # (filename, []) — empty list
    file_error = Signal(str, str)
    all_finished = Signal()

    def __init__(self, video_paths: list[str], settings: dict, output_dir: str, parent=None):
        super().__init__(parent)
        self.video_paths = video_paths
        self.settings = settings
        self.output_dir = output_dir
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        import shutil

        for i, video_path in enumerate(self.video_paths):
            if self._cancelled:
                break

            filename = Path(video_path).name
            stem = Path(video_path).stem
            self.file_started.emit(filename)

            try:
                pct_base = int(i / len(self.video_paths) * 100)
                weight = 100 / len(self.video_paths)

                def emit(msg, local_pct=0):
                    overall = pct_base + int(local_pct / 100 * weight)
                    self.progress.emit(msg, min(overall, 99))

                import tempfile
                work_dir = tempfile.mkdtemp(prefix="framedx_slides_")

                emit("Scanning video for slide changes...", 5)
                slides = extract_slides(
                    video_path,
                    work_dir,
                    ssim_threshold=self.settings.get("ssim_threshold", 0.85),
                    frame_interval=self.settings.get("frame_interval", 2.0),
                    progress_callback=lambda msg: emit(msg, 50),
                )

                # Copy slides to output folder named after the video
                dest_dir = os.path.join(self.output_dir, stem)
                os.makedirs(dest_dir, exist_ok=True)

                for j, slide in enumerate(slides):
                    ext = Path(slide.image_path).suffix
                    dest = os.path.join(dest_dir, f"{j + 1:03d}{ext}")
                    shutil.copy2(slide.image_path, dest)

                emit(f"Done — {len(slides)} slides saved to {stem}/", 100)
                self.file_finished.emit(filename, [])

            except Exception as e:
                self.file_error.emit(filename, str(e))

        self.all_finished.emit()


def create_pipeline_thread(video_paths: list[str], settings: dict) -> tuple[QThread, PipelineWorker]:
    """Create and wire up a pipeline worker in a QThread. Caller must call thread.start()."""
    thread = QThread()
    worker = PipelineWorker(video_paths, settings)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.all_finished.connect(thread.quit)
    return thread, worker


def create_transcript_thread(
    video_paths: list[str], settings: dict, output_dir: str,
    export_txt: bool = True, export_srt: bool = True,
) -> tuple[QThread, TranscriptWorker]:
    thread = QThread()
    worker = TranscriptWorker(video_paths, settings, output_dir, export_txt, export_srt)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.all_finished.connect(thread.quit)
    return thread, worker


def create_slides_thread(
    video_paths: list[str], settings: dict, output_dir: str,
) -> tuple[QThread, SlidesWorker]:
    thread = QThread()
    worker = SlidesWorker(video_paths, settings, output_dir)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.all_finished.connect(thread.quit)
    return thread, worker
