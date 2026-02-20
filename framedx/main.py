import sys

from PySide6.QtWidgets import QApplication

from framedx.gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("FrameDX")
    app.setOrganizationName("FrameDX")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
