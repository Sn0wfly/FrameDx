LIGHT_STYLE = """
QMainWindow, QWidget {
    background-color: #f5f5f5;
    color: #1a1a1a;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #d0d0d0;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QPushButton {
    background-color: #0078d4;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #106ebe;
}
QPushButton:pressed {
    background-color: #005a9e;
}
QPushButton:disabled {
    background-color: #c0c0c0;
    color: #808080;
}
QPushButton#danger {
    background-color: #d13438;
}
QPushButton#danger:hover {
    background-color: #a4262c;
}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    border: 1px solid #c0c0c0;
    border-radius: 4px;
    padding: 4px 8px;
    background-color: white;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #0078d4;
}
QSlider::groove:horizontal {
    border: none;
    height: 4px;
    background: #c0c0c0;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #0078d4;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}
QProgressBar {
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    text-align: center;
    height: 20px;
}
QProgressBar::chunk {
    background-color: #0078d4;
    border-radius: 3px;
}
QTableWidget {
    border: 1px solid #d0d0d0;
    gridline-color: #e0e0e0;
    background-color: white;
    alternate-background-color: #f9f9f9;
}
QTableWidget::item:selected {
    background-color: #cce4f7;
    color: #1a1a1a;
}
QHeaderView::section {
    background-color: #e8e8e8;
    border: none;
    border-bottom: 1px solid #d0d0d0;
    padding: 6px;
    font-weight: bold;
}
QStatusBar {
    background-color: #e8e8e8;
    border-top: 1px solid #d0d0d0;
}
QScrollArea {
    border: none;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
}
"""

DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1e1e1e;
    color: #d4d4d4;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #3c3c3c;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
    color: #d4d4d4;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QPushButton {
    background-color: #0078d4;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #1a8ad4;
}
QPushButton:pressed {
    background-color: #005a9e;
}
QPushButton:disabled {
    background-color: #3c3c3c;
    color: #666666;
}
QPushButton#danger {
    background-color: #d13438;
}
QPushButton#danger:hover {
    background-color: #e04448;
}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    padding: 4px 8px;
    background-color: #2d2d2d;
    color: #d4d4d4;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #0078d4;
}
QComboBox QAbstractItemView {
    background-color: #2d2d2d;
    color: #d4d4d4;
    selection-background-color: #0078d4;
}
QSlider::groove:horizontal {
    border: none;
    height: 4px;
    background: #3c3c3c;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #0078d4;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}
QProgressBar {
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    text-align: center;
    height: 20px;
    background-color: #2d2d2d;
    color: #d4d4d4;
}
QProgressBar::chunk {
    background-color: #0078d4;
    border-radius: 3px;
}
QTableWidget {
    border: 1px solid #3c3c3c;
    gridline-color: #3c3c3c;
    background-color: #252525;
    alternate-background-color: #2d2d2d;
    color: #d4d4d4;
}
QTableWidget::item:selected {
    background-color: #264f78;
    color: #d4d4d4;
}
QHeaderView::section {
    background-color: #333333;
    border: none;
    border-bottom: 1px solid #3c3c3c;
    padding: 6px;
    font-weight: bold;
    color: #d4d4d4;
}
QStatusBar {
    background-color: #252525;
    border-top: 1px solid #3c3c3c;
    color: #d4d4d4;
}
QScrollArea {
    border: none;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
}
QToolTip {
    background-color: #2d2d2d;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    padding: 4px;
}
"""


def get_style(dark_mode: bool = False) -> str:
    return DARK_STYLE if dark_mode else LIGHT_STYLE
