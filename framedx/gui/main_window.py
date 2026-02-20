import os
from pathlib import Path

from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from framedx.config.settings import load_settings, save_settings
from framedx.core.anki_exporter import export_deck
from framedx.core.pipeline import create_pipeline_thread, create_transcript_thread, create_slides_thread
from framedx.gui.queue_panel import QueuePanel
from framedx.gui.review_panel import ReviewPanel
from framedx.gui.settings_panel import SettingsPanel
from framedx.gui.styles import get_style


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FrameDX — Medical Lecture Video to Anki Flashcard Extractor")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)

        self._settings = load_settings()
        self._thread = None
        self._worker = None
        self._elapsed_seconds = 0
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick_elapsed)

        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Splitter: left (queue + settings) | right (review)
        splitter = QSplitter(Qt.Horizontal)

        # Left panel
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)

        self.queue_panel = QueuePanel(self._settings.get("last_directory", ""))
        left_layout.addWidget(self.queue_panel)

        self.settings_panel = SettingsPanel(self._settings)
        self.settings_panel.dark_mode_check.stateChanged.connect(self._on_theme_toggle)
        left_layout.addWidget(self.settings_panel)

        # Process button
        btn_row = QHBoxLayout()
        self.btn_process = QPushButton("Start Processing (Anki)")
        self.btn_process.setFixedHeight(36)
        self.btn_process.clicked.connect(self._start_processing)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("danger")
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self._cancel_processing)

        btn_row.addWidget(self.btn_process)
        btn_row.addWidget(self.btn_cancel)
        left_layout.addLayout(btn_row)

        # Quick Tools row
        quick_row = QHBoxLayout()
        self.btn_transcript = QPushButton("Transcript Only")
        self.btn_transcript.setFixedHeight(30)
        self.btn_transcript.setToolTip("Extract transcript as .txt and .srt files")
        self.btn_transcript.clicked.connect(self._start_transcript_only)

        self.btn_slides = QPushButton("Slides Only")
        self.btn_slides.setFixedHeight(30)
        self.btn_slides.setToolTip("Extract slide images to a folder (no Anki, no transcript)")
        self.btn_slides.clicked.connect(self._start_slides_only)

        quick_row.addWidget(self.btn_transcript)
        quick_row.addWidget(self.btn_slides)
        left_layout.addLayout(quick_row)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        left_layout.addWidget(self.progress_bar)

        # Log panel
        log_group = QGroupBox("Processing Log")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(1000)
        self.log_text.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 11px;")
        log_layout.addWidget(self.log_text)
        left_layout.addWidget(log_group, stretch=1)

        splitter.addWidget(left)

        # Right panel: review
        self.review_panel = ReviewPanel()
        self.review_panel.btn_export.clicked.connect(self._export_deck)
        splitter.addWidget(self.review_panel)

        splitter.setSizes([450, 550])
        main_layout.addWidget(splitter)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Ready")
        self.elapsed_label = QLabel("")
        self.status_bar.addWidget(self.status_label, stretch=1)
        self.status_bar.addPermanentWidget(self.elapsed_label)

    def _apply_theme(self):
        dark = self.settings_panel.dark_mode_check.isChecked()
        QApplication.instance().setStyleSheet(get_style(dark))

    def _on_theme_toggle(self):
        self._apply_theme()

    def _start_processing(self):
        paths = self.queue_panel.get_file_paths()
        if not paths:
            QMessageBox.warning(self, "No Files", "Add video files to the queue first.")
            return

        settings = self._save_and_get_settings()
        self._log(f"Starting Anki pipeline for {len(paths)} file(s)")
        self._log(f"Model: {settings.get('whisper_model')} | Compute: {settings.get('compute_type')} | "
                  f"Language: {settings.get('language')}")

        thread, worker = create_pipeline_thread(paths, settings)
        self._start_worker(thread, worker, "Anki Pipeline")

    def _get_output_dir(self) -> str:
        """Get output directory from settings or ask user."""
        output_dir = self._settings.get("output_directory", "")
        if not output_dir:
            output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        return output_dir

    def _save_and_get_settings(self) -> dict:
        s = self.settings_panel.get_settings()
        s["last_directory"] = self.queue_panel.get_last_directory()
        self._settings.update(s)
        save_settings(self._settings)
        return self._settings

    def _start_worker(self, thread, worker, mode_label: str):
        """Shared logic for starting any worker thread."""
        self.btn_process.setEnabled(False)
        self.btn_transcript.setEnabled(False)
        self.btn_slides.setEnabled(False)
        self.btn_cancel.setVisible(True)
        self.queue_panel.set_enabled_all(False)
        self.progress_bar.setValue(0)
        self._elapsed_seconds = 0
        self._timer.start()

        self.log_text.clear()
        self._log(f"Mode: {mode_label}")

        self._thread = thread
        self._worker = worker
        self._worker.progress.connect(self._on_progress)
        self._worker.file_started.connect(self._on_file_started)
        self._worker.file_finished.connect(self._on_file_finished_simple
                                           if mode_label != "Anki Pipeline" else self._on_file_finished)
        self._worker.file_error.connect(self._on_file_error)
        self._worker.all_finished.connect(self._on_all_finished)
        self._thread.start()

    def _on_file_finished_simple(self, filename: str, _pairs: list):
        """For transcript/slides modes that produce no card pairs."""
        self.queue_panel.set_file_status(filename, "Done")
        self._log(f"--- Finished: {filename} ---")

    def _start_transcript_only(self):
        paths = self.queue_panel.get_file_paths()
        if not paths:
            QMessageBox.warning(self, "No Files", "Add video files to the queue first.")
            return

        output_dir = self._get_output_dir()
        if not output_dir:
            return

        settings = self._save_and_get_settings()
        self._log(f"Starting transcript extraction for {len(paths)} file(s)")
        self._log(f"Model: {settings.get('whisper_model')} | Compute: {settings.get('compute_type')} | "
                  f"Language: {settings.get('language')} | Output: {output_dir}")

        thread, worker = create_transcript_thread(
            paths, settings, output_dir, export_txt=True, export_srt=True,
        )
        self._start_worker(thread, worker, "Transcript Only")

    def _start_slides_only(self):
        paths = self.queue_panel.get_file_paths()
        if not paths:
            QMessageBox.warning(self, "No Files", "Add video files to the queue first.")
            return

        output_dir = self._get_output_dir()
        if not output_dir:
            return

        settings = self._save_and_get_settings()
        self._log(f"Starting slide extraction for {len(paths)} file(s)")
        self._log(f"SSIM: {settings.get('ssim_threshold')} | Interval: {settings.get('frame_interval')}s | "
                  f"Output: {output_dir}")

        thread, worker = create_slides_thread(paths, settings, output_dir)
        self._start_worker(thread, worker, "Slides Only")

    def _cancel_processing(self):
        if self._worker:
            self._worker.cancel()
        self.status_label.setText("Cancelling...")

    def _log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.appendPlainText(f"[{timestamp}] {message}")

    def _on_progress(self, message: str, pct: int):
        self.progress_bar.setValue(pct)
        self.status_label.setText(message)
        self._log(message)

    def _on_file_started(self, filename: str):
        self.queue_panel.set_file_status(filename, "Processing...")
        self.status_label.setText(f"Processing: {filename}")
        self._log(f"--- Started: {filename} ---")

    def _on_file_finished(self, filename: str, pairs: list):
        self.queue_panel.set_file_status(filename, f"Done ({len(pairs)} cards)")
        self.review_panel.add_pairs(pairs)
        self._log(f"--- Finished: {filename} — {len(pairs)} cards extracted ---")

    def _on_file_error(self, filename: str, error: str):
        self.queue_panel.set_file_status(filename, f"Error")
        self._log(f"ERROR [{filename}]: {error}")
        QMessageBox.warning(self, f"Error: {filename}", error[:500])

    def _on_all_finished(self):
        self._timer.stop()
        self.btn_process.setEnabled(True)
        self.btn_transcript.setEnabled(True)
        self.btn_slides.setEnabled(True)
        self.btn_cancel.setVisible(False)
        self.queue_panel.set_enabled_all(True)
        self.progress_bar.setValue(100)
        self.status_label.setText("Processing complete")
        m, s = divmod(self._elapsed_seconds, 60)
        self._log(f"=== All processing complete — Total time: {m:02d}:{s:02d} ===")

        # Cleanup thread
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None
            self._worker = None

    def _tick_elapsed(self):
        self._elapsed_seconds += 1
        m, s = divmod(self._elapsed_seconds, 60)
        self.elapsed_label.setText(f"Elapsed: {m:02d}:{s:02d}")

    def _export_deck(self):
        pairs = self.review_panel.get_included_pairs()
        if not pairs:
            QMessageBox.warning(self, "No Cards", "No cards selected for export.")
            return

        output_dir = self._settings.get("output_directory", "")
        if not output_dir:
            output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
            if not output_dir:
                return

        deck_name = "FrameDX Deck"
        output_path = os.path.join(output_dir, "framedx_deck.apkg")

        try:
            result_path = export_deck(
                pairs,
                deck_name=deck_name,
                output_path=output_path,
                source_tag="framedx",
            )
            QMessageBox.information(
                self,
                "Export Complete",
                f"Anki deck exported successfully!\n\n{result_path}\n\n"
                f"{len(pairs)} cards included.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e)[:500])

    def closeEvent(self, event):
        # Save settings on close
        s = self.settings_panel.get_settings()
        s["last_directory"] = self.queue_panel.get_last_directory()
        self._settings.update(s)
        save_settings(self._settings)

        # Cancel any running pipeline
        if self._worker:
            self._worker.cancel()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(3000)

        event.accept()
