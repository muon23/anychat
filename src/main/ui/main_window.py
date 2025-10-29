import sys
from pathlib import Path

from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
# Import all the widgets we'll need to find
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QPushButton,
    QTextEdit, QComboBox
)

# We no longer import llms here, as the models come from the config
# import llms
from config_manager import ConfigManager
from key_manager import KeyManager
from keys_dialog import KeysDialog


class MainWindow(QMainWindow):
    def __init__(self, config_manager, key_manager, providers: list, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.key_manager = key_manager
        self.providers = providers # Providers for the Keys dialog

        # These will be populated by the UI loading
        self.ui = None
        self.keysButton = None
        self.sendButton = None
        self.modelComboBox = None
        self.messageInput = None
        self.chatDisplay = None

        self._load_ui()

        # Set initial splitter sizes
        main_splitter = self.findChild(QSplitter, "mainSplitter")
        if main_splitter:
            main_splitter.setSizes([250, 750])
            print("Main splitter found and resized.")

        chat_splitter = self.findChild(QSplitter, "chatAreaSplitter")
        if chat_splitter:
            chat_splitter.setSizes([600, 150])
            print("Chat area splitter found and resized.")

        # --- Connect UI Elements ---
        self._connect_signals()

        # --- Populate Model ComboBox ---
        self._populate_models()

    def _find_ui_children_by_name(self):
        """Finds all necessary widgets using findChild."""
        self.keysButton = self.findChild(QPushButton, "keysButton")
        self.sendButton = self.findChild(QPushButton, "sendButton")
        self.modelComboBox = self.findChild(QComboBox, "modelComboBox")
        self.messageInput = self.findChild(QTextEdit, "messageInput")
        self.chatDisplay = self.findChild(QTextEdit, "chatDisplay")

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

            # Find children from the self.ui object
            self.keysButton = self.ui.keysButton
            self.sendButton = self.ui.sendButton
            self.modelComboBox = self.ui.modelComboBox
            self.messageInput = self.ui.messageInput
            self.chatDisplay = self.ui.chatDisplay

        except ImportError as e:
            # If the import fails, fall back to dynamic loading
            print(f"ImportError: {e}. Assuming ui_main_window.py is missing.")
            print("Fallback: Loading UI directly from main_window.ui...")

            ui_file_path = Path(__file__).parent / "main_window.ui"
            ui_file = QFile(ui_file_path)
            if not ui_file.exists():
                print(f"CRITICAL: UI file not found at {ui_file_path}")
                return

            ui_file.open(QFile.OpenModeFlag.ReadOnly)
            loader = QUiLoader()
            # Load the UI onto this instance
            loader.load(ui_file, self)

            # Find children using findChild
            self._find_ui_children_by_name()

    def _connect_signals(self):
        """Connect all UI signals to their handler methods."""
        if self.keysButton:
            self.keysButton.clicked.connect(self.open_keys_dialog)
            print("Keys button connected.")
        else:
            print("Warning: 'keysButton' not found.")

        if self.sendButton:
            self.sendButton.clicked.connect(self.handle_send_message)
            print("Send button connected.")
        else:
            print("Warning: 'sendButton' not found.")

    def _populate_models(self):
        """Populates the modelComboBox with models from the ConfigManager."""
        if self.modelComboBox:
            try:
                # Get the list from the config manager instead of llms
                model_list = self.config_manager.get_models()
                self.modelComboBox.addItems(model_list)
                print(f"Models populated: {model_list}")
            except Exception as e:
                print(f"Error populating models: {e}")
                self.modelComboBox.addItem("Error: Could not load models")
        else:
            print("Warning: 'modelComboBox' not found.")

    def open_keys_dialog(self):
        """Opens the API Keys management dialog."""
        print("Opening keys dialog...")
        # self.providers was set in __init__ from the config
        dialog = KeysDialog(self.key_manager, self.providers, self)
        dialog.exec()

    def handle_send_message(self):
        """Handles the 'Send' button click."""
        if self.messageInput and self.modelComboBox and self.chatDisplay:
            message = self.messageInput.toPlainText().strip()
            model = self.modelComboBox.currentText()

            if not message:
                return  # Don't send empty messages

            print(f"Sending to {model}: {message}")

            # Add message to chat display
            self.chatDisplay.append(f"<b>You:</b> {message}\n")

            # Clear the input
            self.messageInput.clear()

            # --- TODO: Add logic here to call the LLM ---
            # (This is where you would show a "thinking" indicator
            # and then append the AI's response)
            # self.chatDisplay.append(f"<b>{model}:</b> ...thinking...")

### Main execution block
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # --- Load Configuration ---
    print("Loading configuration...")
    config_manager = ConfigManager()

    # Get configuration values
    keys_file = config_manager.get_keys_file_path()
    providers = config_manager.get_providers()
    # Typo fix: config_manger -> config_manager
    print(f"Properties file loaded: {config_manager.config_file}")
    print(f"Keys file path: {keys_file}")
    print(f"Providers: {providers}")

    # Initialize the KeyManager
    key_manager = KeyManager(Path(keys_file), providers)

    # --- Start Application ---
    print("KeyManager and providers injected into MainWindow.")
    window = MainWindow(config_manager, key_manager, providers)
    window.show()
    sys.exit(app.exec())


