import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow, QSplitter
# These are only needed for the fallback method
from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.ui = None  # A placeholder for the UI object
        self._load_ui()

        # Now you can access your widgets. Note the difference in access below.
        # It's safer to use findChild for a consistent approach in a hybrid model.
        splitter = self.findChild(QSplitter, "mainSplitter")
        if splitter:
            splitter.setSizes([200, 600])
            print("Splitter found and resized.")

    def _load_ui(self):
        """
        Tries to load the UI from a compiled .py file first,
        then falls back to loading the .ui file directly.
        """
        try:
            # First, try to import from the compiled file
            from ui_main_window import Ui_MainWindow

            print("Loading UI from compiled ui_main_window.py...")
            self.ui = Ui_MainWindow()
            self.ui.setupUi(self)

        except ImportError:
            # If the import fails, fall back to dynamic loading
            print("Fallback: Loading UI directly from main_window.ui...")

            ui_file_path = Path(__file__).parent / "main_window.ui"
            ui_file = QFile(ui_file_path)
            if not ui_file.exists():
                print(f"UI file not found at {ui_file_path}")
                return

            ui_file.open(QFile.OpenModeFlag.ReadOnly)
            loader = QUiLoader()
            # In this case, loader.load returns the main window widget itself
            # We pass 'self' so it loads the UI *onto* our existing MainWindow instance
            loader.load(ui_file, self)
            # We don't assign to self.ui here because the widgets are now direct children of 'self'


### Main execution block
if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
