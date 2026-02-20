import json
import os
from pathlib import Path


DEFAULT_SETTINGS = {
    "whisper_model": "large-v3",
    "compute_type": "int8",
    "ssim_threshold": 0.85,
    "matching_window": 10,
    "pre_context_seconds": 5,
    "frame_interval": 2.0,
    "language": "auto",
    "use_llm_correction": False,
    "anthropic_api_key": "",
    "output_directory": "",
    "last_directory": "",
    "dark_mode": False,
}


def _config_path() -> Path:
    app_data = os.environ.get("APPDATA", str(Path.home()))
    config_dir = Path(app_data) / "FrameDX"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "settings.json"


def load_settings() -> dict:
    path = _config_path()
    settings = dict(DEFAULT_SETTINGS)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                stored = json.load(f)
            settings.update(stored)
        except (json.JSONDecodeError, OSError):
            pass
    return settings


def save_settings(settings: dict) -> None:
    path = _config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
