from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim

# Width to downscale to for SSIM comparison (much faster, same accuracy for change detection)
_COMPARE_WIDTH = 320


@dataclass
class DetectedSlide:
    timestamp: float
    frame_index: int
    image_path: str


def _downscale_gray(frame: np.ndarray) -> np.ndarray:
    """Convert to grayscale and downscale for fast SSIM comparison."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    if w > _COMPARE_WIDTH:
        scale = _COMPARE_WIDTH / w
        new_h = int(h * scale)
        gray = cv2.resize(gray, (_COMPARE_WIDTH, new_h), interpolation=cv2.INTER_AREA)
    return gray


def extract_slides(
    video_path: str,
    output_dir: str,
    ssim_threshold: float = 0.85,
    frame_interval: float = 2.0,
    dedup_threshold: float = 0.95,
    progress_callback=None,
) -> list[DetectedSlide]:
    """Extract slide-change frames from a video using SSIM comparison.

    Returns a list of DetectedSlide with saved PNG paths and timestamps.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    frame_step = max(1, int(fps * frame_interval))

    slides_dir = Path(output_dir) / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)

    prev_small = None
    prev_frame = None
    prev_timestamp = 0.0
    # Store (timestamp, full-res frame) for detected slides
    candidates: list[tuple[float, np.ndarray]] = []
    # Keep downscaled gray of last candidate for dedup
    last_candidate_small: np.ndarray | None = None

    frame_idx = 0
    last_pct = -1

    while True:
        # Sequential skip: grab without decoding, then retrieve only the frames we need
        if frame_idx > 0:
            skip = frame_step - 1
            for _ in range(skip):
                if not cap.grab():
                    break
            ret, frame = cap.read()
        else:
            ret, frame = cap.read()

        if not ret:
            break

        timestamp = frame_idx / fps if fps > 0 else 0
        small = _downscale_gray(frame)

        if prev_small is not None:
            score = ssim(prev_small, small)
            if score < ssim_threshold:
                # New slide detected — save the PREVIOUS frame (fully-loaded slide)
                if last_candidate_small is not None:
                    dup_score = ssim(last_candidate_small, prev_small)
                    if dup_score < dedup_threshold:
                        candidates.append((prev_timestamp, prev_frame.copy()))
                        last_candidate_small = prev_small
                else:
                    candidates.append((prev_timestamp, prev_frame.copy()))
                    last_candidate_small = prev_small

        prev_small = small
        prev_frame = frame
        prev_timestamp = timestamp

        if progress_callback and duration > 0:
            pct = min(100, int(timestamp / duration * 100))
            if pct != last_pct:
                progress_callback(f"Scanning frames: {pct}%")
                last_pct = pct

        frame_idx += frame_step

    cap.release()

    # Save candidate slides as PNGs (full resolution)
    slides = []
    for i, (ts, frame) in enumerate(candidates):
        filename = f"slide_{i:04d}_{ts:.1f}s.png"
        path = str(slides_dir / filename)
        cv2.imwrite(path, frame)
        slides.append(DetectedSlide(timestamp=ts, frame_index=i, image_path=path))

    if progress_callback:
        progress_callback(f"Detected {len(slides)} slides")

    return slides
