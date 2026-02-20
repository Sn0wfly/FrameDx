from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from framedx.core.matcher import CardPair


class ImageDialog(QDialog):
    """Full-resolution image viewer."""

    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(Path(image_path).name)
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)
        label = QLabel()
        pixmap = QPixmap(image_path)
        label.setPixmap(pixmap.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))
        label.setAlignment(Qt.AlignCenter)

        scroll = QScrollArea()
        scroll.setWidget(label)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)


class CardWidget(QWidget):
    """Single card: thumbnail + editable text + controls."""

    deleted = Signal(object)  # emits self

    def __init__(self, pair: CardPair, index: int, parent=None):
        super().__init__(parent)
        self.pair = pair
        self._index = index
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.pair.included)
        self.checkbox.stateChanged.connect(
            lambda state: setattr(self.pair, "included", state == Qt.Checked)
        )
        layout.addWidget(self.checkbox)

        # Thumbnail
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(200, 150)
        self.thumb_label.setCursor(Qt.PointingHandCursor)
        self.thumb_label.setToolTip("Click to view full size")
        pixmap = QPixmap(self.pair.image_path)
        if not pixmap.isNull():
            self.thumb_label.setPixmap(
                pixmap.scaled(200, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            self.thumb_label.setText("(no image)")
            self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.mousePressEvent = self._show_full_image
        layout.addWidget(self.thumb_label)

        # Text + info
        text_layout = QVBoxLayout()
        time_label = QLabel(f"Slide #{self._index + 1} @ {self.pair.slide_timestamp:.1f}s")
        time_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        text_layout.addWidget(time_label)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlainText(self.pair.transcript_text)
        self.text_edit.setMaximumHeight(120)
        self.text_edit.textChanged.connect(self._on_text_changed)
        text_layout.addWidget(self.text_edit)
        layout.addLayout(text_layout, stretch=1)

        # Delete button
        btn_delete = QPushButton("Delete")
        btn_delete.setObjectName("danger")
        btn_delete.setFixedWidth(70)
        btn_delete.clicked.connect(lambda: self.deleted.emit(self))
        layout.addWidget(btn_delete, alignment=Qt.AlignTop)

    def _on_text_changed(self):
        self.pair.transcript_text = self.text_edit.toPlainText()

    def _show_full_image(self, _event):
        dialog = ImageDialog(self.pair.image_path, self)
        dialog.exec()


class ReviewPanel(QWidget):
    """Scrollable list of card pairs for review and editing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._card_widgets: list[CardWidget] = []
        self._pairs: list[CardPair] = []
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Top controls
        controls = QHBoxLayout()
        self.label_count = QLabel("No cards")
        controls.addWidget(self.label_count)
        controls.addStretch()

        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.clicked.connect(lambda: self._set_all_checked(True))
        controls.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("Deselect All")
        self.btn_deselect_all.clicked.connect(lambda: self._set_all_checked(False))
        controls.addWidget(self.btn_deselect_all)

        self.btn_export = QPushButton("Export to Anki")
        self.btn_export.setEnabled(False)
        controls.addWidget(self.btn_export)
        outer.addLayout(controls)

        # Scroll area for cards
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.scroll_content)
        outer.addWidget(self.scroll)

    def load_pairs(self, pairs: list[CardPair]):
        """Replace the current display with new card pairs."""
        self._pairs = pairs
        self._clear_cards()

        for i, pair in enumerate(pairs):
            card = CardWidget(pair, i)
            card.deleted.connect(self._on_card_deleted)
            self.scroll_layout.addWidget(card)
            self._card_widgets.append(card)

        self._update_count()
        self.btn_export.setEnabled(len(pairs) > 0)

    def add_pairs(self, pairs: list[CardPair]):
        """Append new card pairs to the existing display."""
        start_idx = len(self._pairs)
        self._pairs.extend(pairs)

        for i, pair in enumerate(pairs):
            card = CardWidget(pair, start_idx + i)
            card.deleted.connect(self._on_card_deleted)
            self.scroll_layout.addWidget(card)
            self._card_widgets.append(card)

        self._update_count()
        self.btn_export.setEnabled(len(self._pairs) > 0)

    def get_included_pairs(self) -> list[CardPair]:
        return [p for p in self._pairs if p.included]

    def _on_card_deleted(self, card_widget: CardWidget):
        self._pairs.remove(card_widget.pair)
        self._card_widgets.remove(card_widget)
        self.scroll_layout.removeWidget(card_widget)
        card_widget.deleteLater()
        self._update_count()

    def _set_all_checked(self, checked: bool):
        for card in self._card_widgets:
            card.checkbox.setChecked(checked)

    def _clear_cards(self):
        for card in self._card_widgets:
            self.scroll_layout.removeWidget(card)
            card.deleteLater()
        self._card_widgets.clear()

    def _update_count(self):
        n = len(self._pairs)
        included = sum(1 for p in self._pairs if p.included)
        self.label_count.setText(f"{included}/{n} cards selected")
        self.btn_export.setEnabled(n > 0)
