from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class SettingsPanel(QWidget):
    settings_changed = Signal()

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._setup_ui(settings)

    def _setup_ui(self, s: dict):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        group = QGroupBox("Settings")
        form = QFormLayout(group)

        # Whisper model
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v3"])
        self.model_combo.setCurrentText(s.get("whisper_model", "large-v3"))
        form.addRow("Whisper Model:", self.model_combo)

        # Compute type
        self.compute_combo = QComboBox()
        self.compute_combo.addItems(["int8", "int16", "float32"])
        self.compute_combo.setCurrentText(s.get("compute_type", "int8"))
        self.compute_combo.setToolTip("int8 is fastest on CPU, float32 is most accurate")
        form.addRow("Compute Type:", self.compute_combo)

        # SSIM threshold
        ssim_row = QHBoxLayout()
        self.ssim_slider = QSlider(Qt.Horizontal)
        self.ssim_slider.setRange(50, 99)
        self.ssim_slider.setValue(int(s.get("ssim_threshold", 0.85) * 100))
        self.ssim_slider.setToolTip(
            "Lower = more sensitive to changes (detects more slides).\n"
            "Higher = less sensitive (only major changes trigger a new slide)."
        )
        self.ssim_label = QLabel(f"{self.ssim_slider.value() / 100:.2f}")
        self.ssim_slider.valueChanged.connect(
            lambda v: self.ssim_label.setText(f"{v / 100:.2f}")
        )
        ssim_row.addWidget(self.ssim_slider)
        ssim_row.addWidget(self.ssim_label)
        form.addRow("SSIM Threshold:", ssim_row)

        # Frame interval
        self.frame_interval = QDoubleSpinBox()
        self.frame_interval.setRange(0.5, 10.0)
        self.frame_interval.setSingleStep(0.5)
        self.frame_interval.setValue(s.get("frame_interval", 2.0))
        self.frame_interval.setSuffix(" sec")
        self.frame_interval.setToolTip("How often to sample frames for slide detection")
        form.addRow("Frame Interval:", self.frame_interval)

        # Matching window
        self.matching_window = QSpinBox()
        self.matching_window.setRange(3, 30)
        self.matching_window.setValue(s.get("matching_window", 10))
        self.matching_window.setSuffix(" sec")
        self.matching_window.setToolTip("Seconds of audio AFTER a slide change to capture")
        form.addRow("Match Window (after):", self.matching_window)

        # Pre-context
        self.pre_context = QSpinBox()
        self.pre_context.setRange(0, 15)
        self.pre_context.setValue(s.get("pre_context_seconds", 5))
        self.pre_context.setSuffix(" sec")
        self.pre_context.setToolTip("Seconds of audio BEFORE a slide change to capture")
        form.addRow("Pre-context:", self.pre_context)

        # Language
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["auto", "es", "en", "pt", "fr", "de"])
        self.lang_combo.setCurrentText(s.get("language", "auto"))
        form.addRow("Language:", self.lang_combo)

        # LLM correction toggle
        self.llm_check = QCheckBox("Use LLM for medical term correction")
        self.llm_check.setChecked(s.get("use_llm_correction", False))
        form.addRow(self.llm_check)

        # API key
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("sk-ant-...")
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setText(s.get("anthropic_api_key", ""))
        form.addRow("Anthropic API Key:", self.api_key_input)

        # Output directory
        out_row = QHBoxLayout()
        self.output_dir = QLineEdit()
        self.output_dir.setPlaceholderText("Select output directory...")
        self.output_dir.setText(s.get("output_directory", ""))
        self.btn_browse = QPushButton("Browse")
        self.btn_browse.clicked.connect(self._browse_output)
        out_row.addWidget(self.output_dir)
        out_row.addWidget(self.btn_browse)
        form.addRow("Output Directory:", out_row)

        # Dark mode
        self.dark_mode_check = QCheckBox("Dark Mode")
        self.dark_mode_check.setChecked(s.get("dark_mode", False))
        form.addRow(self.dark_mode_check)

        layout.addWidget(group)

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory", self.output_dir.text())
        if folder:
            self.output_dir.setText(folder)

    def get_settings(self) -> dict:
        return {
            "whisper_model": self.model_combo.currentText(),
            "compute_type": self.compute_combo.currentText(),
            "ssim_threshold": self.ssim_slider.value() / 100.0,
            "frame_interval": self.frame_interval.value(),
            "matching_window": self.matching_window.value(),
            "pre_context_seconds": self.pre_context.value(),
            "language": self.lang_combo.currentText(),
            "use_llm_correction": self.llm_check.isChecked(),
            "anthropic_api_key": self.api_key_input.text(),
            "output_directory": self.output_dir.text(),
            "dark_mode": self.dark_mode_check.isChecked(),
        }
