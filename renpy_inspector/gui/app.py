"""GUI Application entrypoint for Ren'Py Inspector."""

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QApplication

from renpy_inspector.gui.main_window import MainWindow
from renpy_inspector.gui.theme import DARK_STYLESHEET


def launch_gui(initial_path: Optional[Path] = None) -> int:
    """Initializes and runs the Ren'Py Inspector Qt GUI application."""
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    app.setApplicationName("RenPyInspector")
    app.setApplicationDisplayName("Ren'Py Inspector")
    app.setStyleSheet(DARK_STYLESHEET)

    window = MainWindow(initial_path=initial_path)
    window.show()

    return app.exec()


def main() -> None:
    """CLI entrypoint for the desktop GUI."""
    initial_path = None
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        initial_path = Path(sys.argv[1])

    sys.exit(launch_gui(initial_path))


if __name__ == "__main__":
    main()
