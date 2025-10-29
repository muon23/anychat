import sys
from pathlib import Path

from PySide6.QtCore import QFile, QPoint
from PySide6.QtUiTools import QUiLoader
# Import all the widgets we'll need to find
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QPushButton,
    QTextEdit, QComboBox, QTreeWidget, QMenu
)

from chat_history_manager import ChatHistoryManager, PathRole
from config_manager import ConfigManager
from key_manager import KeyManager
from keys_dialog import KeysDialog


class MainWindow(QMainWindow):
    def __init__(self, config_manager, key_manager, chat_history_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.key_manager = key_manager
        self.chat_history_manager = chat_history_manager

        self.providers = self.config_manager.get_providers()

        # Placeholders for UI widgets
        self.ui = None
        self.keysButton = None
        self.sendButton = None
        self.modelComboBox = None
        self.messageInput = None
        self.chatDisplay = None
        self.chatHistoryTree = None
        self.newChatButton = None
        self.newProjectButton = None

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

        # --- Populate UI ---
        self._populate_models()
        self._load_chat_history()

    def _find_ui_children_by_name(self):
        """Finds all necessary widgets using findChild."""
        self.keysButton = self.findChild(QPushButton, "keysButton")
        self.sendButton = self.findChild(QPushButton, "sendButton")
        self.modelComboBox = self.findChild(QComboBox, "modelComboBox")
        self.messageInput = self.findChild(QTextEdit, "messageInput")
        self.chatDisplay = self.findChild(QTextEdit, "chatDisplay")
        self.chatHistoryTree = self.findChild(QTreeWidget, "chatHistoryTree")
        self.newChatButton = self.findChild(QPushButton, "newChatButton")
        self.newProjectButton = self.findChild(QPushButton, "newProjectButton")

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
            self.chatHistoryTree = self.ui.chatHistoryTree
            self.newChatButton = self.ui.newChatButton
            self.newProjectButton = self.ui.newProjectButton

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
            loader.load(ui_file, self)
            self._find_ui_children_by_name()

    def _connect_signals(self):
        """Connect all UI signals to their handler methods."""
        if self.keysButton:
            self.keysButton.clicked.connect(self.open_keys_dialog)
            print("Keys button connected.")

        if self.sendButton:
            self.sendButton.clicked.connect(self.handle_send_message)
            print("Send button connected.")

        if self.newChatButton:
            # Updated: Creates a "Chat N" in the root
            self.newChatButton.clicked.connect(self.handle_new_root_chat)
            print("New Chat button connected.")

        if self.newProjectButton:
            # Updated: Creates a top-level project
            self.newProjectButton.clicked.connect(self.handle_new_root_project)
            print("New Project button connected.")

        if self.chatHistoryTree:
            # Connect the new right-click menu
            self.chatHistoryTree.customContextMenuRequested.connect(self._show_tree_context_menu)
            print("Tree context menu connected.")
            # TODO: Connect self.chatHistoryTree.currentItemChanged to load a chat
        else:
            print("Warning: 'chatHistoryTree' not found.")

    def _populate_models(self):
        """Populates the modelComboBox with models from the ConfigManager."""
        if self.modelComboBox:
            try:
                model_list = self.config_manager.get_models()
                self.modelComboBox.addItems(model_list)
                print(f"Models populated: {model_list}")
            except Exception as e:
                print(f"Error populating models: {e}")
        else:
            print("Warning: 'modelComboBox' not found.")

    def _load_chat_history(self):
        """Tells the chat manager to load history into the tree."""
        if self.chatHistoryTree and self.chat_history_manager:
            self.chat_history_manager.load_history(self.chatHistoryTree)
        else:
            print("Warning: 'chatHistoryTree' or 'chat_history_manager' not found.")

    def _show_tree_context_menu(self, position: QPoint):
        """Shows a context menu when right-clicking on the tree."""
        item = self.chatHistoryTree.itemAt(position)

        # We only want to show a menu if a project was clicked
        if item and (item.parent() is None or (item.data(0, PathRole) and Path(item.data(0, PathRole)).is_dir())):
            # This is a project or subproject
            context_menu = QMenu(self)

            # Action to create a new chat *inside* this project
            new_chat_action = context_menu.addAction("New Chat in this Project")
            new_chat_action.triggered.connect(lambda: self.handle_new_chat_in_project(item))

            # Action to create a new subproject *inside* this project
            new_subproject_action = context_menu.addAction("New Subproject")
            new_subproject_action.triggered.connect(lambda: self.handle_new_subproject(item))

            # TODO: Add "Rename" and "Delete" actions here

            context_menu.exec(self.chatHistoryTree.viewport().mapToGlobal(position))

    def open_keys_dialog(self):
        """Opens the API Keys management dialog."""
        print("Opening keys dialog...")
        dialog = KeysDialog(self.key_manager, self.providers, self)
        dialog.exec()

    def handle_new_root_chat(self):
        """Handles the 'New Chat' button click (creates a root 'Chat N')."""
        print("New Chat (root) clicked.")
        if self.chatHistoryTree and self.chat_history_manager:
            self.chat_history_manager.create_new_chat(self.chatHistoryTree, parent_project_item=None)

    def handle_new_root_project(self):
        """Handles the 'New Project' button click (creates a top-level project)."""
        print("New Project (root) clicked.")
        if self.chatHistoryTree and self.chat_history_manager:
            self.chat_history_manager.create_project(self.chatHistoryTree, parent_item=None)

    def handle_new_chat_in_project(self, project_item):
        """Creates a named chat inside the selected project."""
        print(f"New Chat in project '{project_item.text(0)}' clicked.")
        self.chat_history_manager.create_new_chat(self.chatHistoryTree, project_item)

    def handle_new_subproject(self, project_item):
        """Creates a subproject inside the selected project."""
        print(f"New Subproject in project '{project_item.text(0)}' clicked.")
        self.chat_history_manager.create_project(self.chatHistoryTree, project_item)

    def handle_send_message(self):
        """Handles the 'Send' button click."""
        if self.messageInput and self.modelComboBox and self.chatDisplay:
            message = self.messageInput.toPlainText().strip()
            model = self.modelComboBox.currentText()

            if not message:
                return  # Don't send empty messages

            print(f"Sending to {model}: {message}")

            self.chatDisplay.append(f"<b>You:</b> {message}\n")
            self.messageInput.clear()

            # --- TODO: Add logic here to call the LLM ---
            # self.chatDisplay.append(f"<b>{model}:</b> ...thinking...")

### Main execution block
if __name__ == "__main__":
    app = QApplication(sys.argv)

    print("Loading configuration...")
    config_manager = ConfigManager()

    keys_file_str = config_manager.get_keys_file_path()
    chat_history_root_str = config_manager.get_chat_history_root()
    providers = config_manager.get_providers()
    print(f"Properties file loaded: {config_manager.config_file}")
    print(f"Keys file path: {keys_file_str}")
    print(f"Chat history root: {chat_history_root_str}")
    print(f"Providers: {providers}")

    keys_file_path = Path(keys_file_str)
    key_manager = KeyManager(keys_file_path, providers)

    chat_history_path = Path(chat_history_root_str)
    chat_history_manager = ChatHistoryManager(chat_history_path)

    print("Managers injected into MainWindow.")
    window = MainWindow(config_manager, key_manager, chat_history_manager)
    window.show()
    sys.exit(app.exec())

