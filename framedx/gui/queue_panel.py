from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".webm", ".mov", ".wmv"}


class QueuePanel(QWidget):
    files_changed = Signal()  # emitted when the file list changes

    def __init__(self, last_directory: str = "", parent=None):
        super().__init__(parent)
        self._last_dir = last_directory
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        group = QGroupBox("File Queue")
        group_layout = QVBoxLayout(group)

        # Buttons row
        btn_row = QHBoxLayout()
        self.btn_add_files = QPushButton("Add Files")
        self.btn_add_folder = QPushButton("Add Folder")
        self.btn_remove = QPushButton("Remove")
        self.btn_remove.setObjectName("danger")
        self.btn_clear = QPushButton("Clear All")
        self.btn_clear.setObjectName("danger")

        btn_row.addWidget(self.btn_add_files)
        btn_row.addWidget(self.btn_add_folder)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_remove)
        btn_row.addWidget(self.btn_clear)
        group_layout.addLayout(btn_row)

        # File table
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Filename", "Status", "Path"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setColumnHidden(2, True)  # hide full path column
        group_layout.addWidget(self.table)

        layout.addWidget(group)

        # Connect signals
        self.btn_add_files.clicked.connect(self._add_files)
        self.btn_add_folder.clicked.connect(self._add_folder)
        self.btn_remove.clicked.connect(self._remove_selected)
        self.btn_clear.clicked.connect(self._clear_all)

    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Video Files",
            self._last_dir,
            "Video Files (*.mp4 *.mkv *.avi *.webm *.mov *.wmv);;All Files (*)",
        )
        if files:
            self._last_dir = str(Path(files[0]).parent)
            for f in files:
                self._add_file_row(f)
            self.files_changed.emit()

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", self._last_dir)
        if folder:
            self._last_dir = folder
            count = 0
            for path in Path(folder).rglob("*"):
                if path.suffix.lower() in VIDEO_EXTENSIONS:
                    self._add_file_row(str(path))
                    count += 1
            if count:
                self.files_changed.emit()

    def _add_file_row(self, file_path: str):
        # Skip duplicates
        for row in range(self.table.rowCount()):
            if self.table.item(row, 2) and self.table.item(row, 2).text() == file_path:
                return

        row = self.table.rowCount()
        self.table.insertRow(row)
        name_item = QTableWidgetItem(Path(file_path).name)
        name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
        status_item = QTableWidgetItem("Pending")
        status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
        path_item = QTableWidgetItem(file_path)
        self.table.setItem(row, 0, name_item)
        self.table.setItem(row, 1, status_item)
        self.table.setItem(row, 2, path_item)

    def _remove_selected(self):
        rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()), reverse=True)
        for row in rows:
            self.table.removeRow(row)
        if rows:
            self.files_changed.emit()

    def _clear_all(self):
        if self.table.rowCount() > 0:
            self.table.setRowCount(0)
            self.files_changed.emit()

    def get_file_paths(self) -> list[str]:
        paths = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 2)
            if item:
                paths.append(item.text())
        return paths

    def set_file_status(self, filename: str, status: str):
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0) and self.table.item(row, 0).text() == filename:
                self.table.item(row, 1).setText(status)
                break

    def get_last_directory(self) -> str:
        return self._last_dir

    def set_enabled_all(self, enabled: bool):
        self.btn_add_files.setEnabled(enabled)
        self.btn_add_folder.setEnabled(enabled)
        self.btn_remove.setEnabled(enabled)
        self.btn_clear.setEnabled(enabled)
