import sys
from pathlib import Path

from PySide6.QtCore import QFile, QPoint, Qt
from PySide6.QtGui import QResizeEvent
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QPushButton,
    QTextEdit, QComboBox, QTreeWidget, QMenu, QMessageBox,
    QInputDialog, QTreeWidgetItem, QListWidget, QListWidgetItem,
    QTreeWidgetItemIterator
)

# We MUST import PathRole to use it
from chat_history_manager import ChatHistoryManager, PathRole
from chat_message_widget import ChatMessageWidget
from config_manager import ConfigManager
from key_manager import KeyManager
from keys_dialog import KeysDialog
from llm_service import LLMService


class MainWindow(QMainWindow):
    def __init__(self, config_manager, key_manager, chat_history_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.key_manager = key_manager
        self.chat_history_manager = chat_history_manager

        # Init the LLM Service
        self.llm_service = LLMService(self.config_manager, self.key_manager)

        self.providers = self.config_manager.get_providers()

        # Placeholders for UI widgets
        self.ui = None
        self.keysButton = None
        self.sendButton = None
        self.modelComboBox = None
        self.messageInput = None
        self.chatDisplay = None  # This will be a QListWidget
        self.chatHistoryTree = None
        self.newChatButton = None
        self.newProjectButton = None

        # A variable to hold the path of the currently active chat
        self.current_chat_file_path: Path | None = None
        # Store current messages to avoid re-reading from widgets
        self.current_messages: list[dict] = []

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

        # Apply dark stylesheet to the QListWidget background
        if self.chatDisplay:
            self.chatDisplay.setStyleSheet("background-color: #222222; border: none;")
            self.chatDisplay.setSpacing(5)  # Spacing between bubbles

            # Enable horizontal scrollbar as needed
            self.chatDisplay.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        else:
            print("Warning: 'chatDisplay' (QListWidget) not found.")

        # --- Connect UI Elements ---
        self._connect_signals()

        # --- Populate UI ---
        self._populate_models()
        self._load_chat_history()

    def resizeEvent(self, event: QResizeEvent):
        """
        This event is called every time the main window is resized.
        We use it to trigger a size update for all visible chat bubbles.
        """
        # Call the parent class's resizeEvent first
        super().resizeEvent(event)
        self._on_chat_display_resize()

    def _on_chat_display_resize(self):
        """
        Triggers update_size() for all visible chat bubbles.
        Called by resizeEvent and when the viewport resizes.
        """
        if not self.chatDisplay:
            return

        # Iterate over all items in the QListWidget
        for i in range(self.chatDisplay.count()):
            item = self.chatDisplay.item(i)
            widget = self.chatDisplay.itemWidget(item)

            # If it's one of our custom chat widgets, tell it to update its size
            if isinstance(widget, ChatMessageWidget):
                widget.update_size()

    def _find_ui_children_by_name(self):
        """Finds all necessary widgets using findChild."""
        self.keysButton = self.findChild(QPushButton, "keysButton")
        self.sendButton = self.findChild(QPushButton, "sendButton")
        self.modelComboBox = self.findChild(QComboBox, "modelComboBox")
        self.messageInput = self.findChild(QTextEdit, "messageInput")
        self.chatDisplay = self.findChild(QListWidget, "chatDisplay")  # <-- QListWidget
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
            self.chatDisplay = self.ui.chatDisplay  # <-- QListWidget
            self.chatHistoryTree = self.ui.chatHistoryTree
            self.newChatButton = self.ui.newChatButton
            self.newProjectButton = self.ui.newProjectButton

            if self.chatHistoryTree:
                self.chatHistoryTree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

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

            if self.chatHistoryTree:
                self.chatHistoryTree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def _connect_signals(self):
        """Connect all UI signals to their handler methods."""
        if self.keysButton:
            self.keysButton.clicked.connect(self.open_keys_dialog)
            print("Keys button connected.")

        if self.sendButton:
            self.sendButton.clicked.connect(self.handle_send_message)
            print("Send button connected.")

        if self.newChatButton:
            self.newChatButton.clicked.connect(self.handle_new_root_chat)
            print("New Chat button connected.")

        if self.newProjectButton:
            self.newProjectButton.clicked.connect(self.handle_new_root_project)
            print("New Project button connected.")

        if self.chatHistoryTree:
            self.chatHistoryTree.customContextMenuRequested.connect(self._show_tree_context_menu)
            print("Tree context menu connected.")

            self.chatHistoryTree.currentItemChanged.connect(self._on_tree_item_selected)
            print("Tree item selection connected.")
        else:
            print("Warning: 'chatHistoryTree' not found.")

        main_splitter = self.findChild(QSplitter, "mainSplitter")
        if main_splitter:
            main_splitter.splitterMoved.connect(self._on_chat_display_resize)
            print("Main splitter connected to resize.")

        chat_splitter = self.findChild(QSplitter, "chatAreaSplitter")
        if chat_splitter:
            chat_splitter.splitterMoved.connect(self._on_chat_display_resize)
            print("Chat splitter connected to resize.")

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
        """Saves expanded state, reloads the tree, and restores expanded state."""
        if self.chatHistoryTree and self.chat_history_manager:
            expanded_paths = self._get_expanded_state()
            self.chat_history_manager.load_history(self.chatHistoryTree)
            self._set_expanded_state(expanded_paths)
        else:
            print("Warning: 'chatHistoryTree' or 'chat_history_manager' not found.")

    def _get_expanded_state(self) -> set:
        """Returns a set of string paths for all expanded items in the tree."""
        expanded_paths = set()
        if not self.chatHistoryTree:
            return expanded_paths

        iterator = QTreeWidgetItemIterator(self.chatHistoryTree)
        while iterator.value():
            item = iterator.value()
            if item.isExpanded():
                path_str = item.data(0, PathRole)
                if path_str:
                    expanded_paths.add(path_str)
            iterator += 1
        return expanded_paths

    def _set_expanded_state(self, expanded_paths: set):
        """Restores the expansion state of the tree from a set of string paths."""
        if not self.chatHistoryTree or not expanded_paths:
            return

        iterator = QTreeWidgetItemIterator(self.chatHistoryTree)
        while iterator.value():
            item = iterator.value()
            path_str = item.data(0, PathRole)
            if path_str in expanded_paths:
                item.setExpanded(True)
            iterator += 1

    def _add_chat_message(self, role: str, content: str) -> ChatMessageWidget | None:
        """
        Adds a new chat bubble widget to the chatDisplay (QListWidget).
        """
        if not self.chatDisplay:
            return None

        chat_widget = ChatMessageWidget()
        list_item = QListWidgetItem(self.chatDisplay)

        chat_widget.editingFinished.connect(self._save_current_chat)

        chat_widget.set_message(role, content, list_item)
        self.chatDisplay.setItemWidget(list_item, chat_widget)
        self.chatDisplay.scrollToBottom()

        # After adding the widget and scrolling,
        # force a resize of all items *now* that the viewport is stable.
        self._on_chat_display_resize()

        return chat_widget

    def _clear_chat_display(self):
        """Clears all messages from the chat display and input."""
        if self.chatDisplay:
            self.chatDisplay.clear()
        if self.messageInput:
            self.messageInput.clear()
        # Do NOT clear self.current_messages here

    def _on_tree_item_selected(self, current: QTreeWidgetItem, previous: QTreeWidgetItem):
        """
        Handles loading a chat when an item in the tree is clicked.
        """
        if not current:
            # No item selected
            self.current_chat_file_path = None
            self.current_messages = []  # Clear messages
            self._clear_chat_display()
            return

        item_path_str = current.data(0, PathRole)
        if not item_path_str:
            return

        item_path = Path(item_path_str)

        if item_path.is_dir():
            # It's a project, not a chat file. Clear display.
            self.current_chat_file_path = None
            self.current_messages = []  # Clear messages
            self._clear_chat_display()

        elif item_path.is_file() and item_path.suffix == '.json':
            # It's a chat file. Load it.
            print(f"Loading chat: {item_path}")
            self._load_chat_from_file(item_path)

    def _load_chat_from_file(self, file_path: Path):
        """Loads a chat from a file and populates the display."""
        self.current_chat_file_path = file_path

        # Load messages *before* clearing display
        self.current_messages = self.chat_history_manager.load_chat(file_path)

        # Now clear the display
        self._clear_chat_display()

        messages_to_display = self.current_messages
        last_message_content = ""

        # --- Implement your special loading logic ---
        if self.current_messages:
            last_message = self.current_messages[-1]
            if last_message.get("role") == "user":
                messages_to_display = self.current_messages[:-1]
                last_message_content = last_message.get("content", "")

        # --- Populate the chat display ---
        for message in messages_to_display:
            role = message.get("role", "user")
            content = message.get("content", "")
            self._add_chat_message(role, content)

        if self.messageInput:
            self.messageInput.setPlainText(last_message_content)

        # After loading, update all bubble sizes
        self._on_chat_display_resize()

    def _save_current_chat(self):
        """Saves the current state of the chatDisplay to its file."""
        if not self.current_chat_file_path:
            print("Save skipped: No active chat file selected.")
            return

        if not self.chatDisplay:
            return

        messages_to_save = []
        for i in range(self.chatDisplay.count()):
            item = self.chatDisplay.item(i)
            widget = self.chatDisplay.itemWidget(item)
            if isinstance(widget, ChatMessageWidget):
                role, content = widget.get_message_tuple()
                # Do not save "thinking" messages
                if role in ("user", "assistant"):
                    messages_to_save.append({"role": role, "content": content})

        if self.messageInput:
            last_user_message = self.messageInput.toPlainText().strip()
            if last_user_message:
                messages_to_save.append({"role": "user", "content": last_user_message})

        # Save the collected messages to the file
        self.chat_history_manager.save_chat(self.current_chat_file_path, messages_to_save)

        # Update the internal state
        self.current_messages = messages_to_save

    def _show_tree_context_menu(self, position: QPoint):
        """Shows a context menu when right-clicking on the tree."""
        context_menu = QMenu(self)
        item = self.chatHistoryTree.itemAt(position)

        if item:
            item_path_str = item.data(0, PathRole)
            if not item_path_str:
                return

            item_path = Path(item_path_str)

            if item_path.is_dir():
                new_chat_action = context_menu.addAction("New Chat in this Project")
                new_chat_action.triggered.connect(lambda: self.handle_new_chat_in_project(item))

                new_subproject_action = context_menu.addAction("New Subproject")
                new_subproject_action.triggered.connect(lambda: self.handle_new_subproject(item))

                context_menu.addSeparator()

            rename_action = context_menu.addAction("Rename")
            rename_action.triggered.connect(lambda: self.handle_rename_item(item))

            delete_action = context_menu.addAction("Delete")
            delete_action.triggered.connect(lambda: self.handle_delete_item(item))

        else:
            new_root_chat_action = context_menu.addAction("New Chat")
            new_root_chat_action.triggered.connect(self.handle_new_root_chat)

            new_root_project_action = context_menu.addAction("New Project")
            new_root_project_action.triggered.connect(self.handle_new_root_project)

        context_menu.exec(self.chatHistoryTree.viewport().mapToGlobal(position))

    def show_delete_warning(self, path: Path) -> bool:
        """
        Shows a custom warning dialog for deleting non-empty projects.
        """
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Deletion")
        msg_box.setText(f"The project '{path.name}' is not empty. "
                        f"This will permanently delete all chats and subprojects inside it.")
        msg_box.setIcon(QMessageBox.Icon.Warning)
        do_it_button = msg_box.addButton("DO IT!", QMessageBox.ButtonRole.DestructiveRole)
        cancel_button = msg_box.addButton(QMessageBox.StandardButton.Cancel)
        msg_box.setDefaultButton(cancel_button)
        msg_box.exec()
        return msg_box.clickedButton() == do_it_button

    def open_keys_dialog(self):
        """Opens the API Keys management dialog."""
        print("Opening keys dialog...")
        dialog = KeysDialog(self.key_manager, self.providers, self)
        dialog.exec()

    def handle_new_root_chat(self):
        """Handles the 'New Chat' button click (creates a root 'Chat N')."""
        print("New Chat (root) clicked.")
        if self.chatHistoryTree and self.chat_history_manager:
            new_item = self.chat_history_manager.create_new_chat(self.chatHistoryTree, parent_project_item=None)
            if new_item:
                self.chatHistoryTree.setCurrentItem(new_item)

    def handle_new_root_project(self):
        """Handles the 'New Project' button click (creates a top-level project)."""
        print("New Project (root) clicked.")
        if self.chatHistoryTree and self.chat_history_manager:
            new_item = self.chat_history_manager.create_project(self.chatHistoryTree, parent_item=None)
            if new_item:
                self.chatHistoryTree.setCurrentItem(new_item)

    def handle_new_chat_in_project(self, project_item):
        """Creates a named chat inside the selected project."""
        print(f"New Chat in '{project_item.text(0)}' clicked.")
        if self.chatHistoryTree and self.chat_history_manager:
            new_item = self.chat_history_manager.create_new_chat(self.chatHistoryTree, parent_project_item=project_item)
            if new_item:
                self.chatHistoryTree.setCurrentItem(new_item)

    def handle_new_subproject(self, project_item: QTreeWidgetItem):
        """Creates a subproject inside the selected project."""
        print(f"New Subproject in '{project_item.text(0)}' clicked.")
        if self.chatHistoryTree and self.chat_history_manager:
            new_item = self.chat_history_manager.create_project(self.chatHistoryTree, parent_item=project_item)
            if new_item:
                self.chatHistoryTree.setCurrentItem(new_item)

    def handle_rename_item(self, item: QTreeWidgetItem):
        """Handles the 'Rename' context menu action."""
        try:
            old_path = Path(item.data(0, PathRole))
            old_name = old_path.stem if old_path.is_file() else old_path.name

            new_name, ok = QInputDialog.getText(self, "Rename Item", "Enter new name:",
                                                text=old_name)

            if ok and new_name and new_name != old_name:
                if self.chat_history_manager.rename_item(old_path, new_name, self):
                    self._load_chat_history()
        except Exception as e:
            print(f"Error during rename: {e}")
            QMessageBox.warning(self, "Error", f"Could not rename item: {e}")

    def handle_delete_item(self, item: QTreeWidgetItem):
        """Handles the 'Delete' context menu action."""
        try:
            path_to_delete = Path(item.data(0, PathRole))
            if self.chat_history_manager.delete_item(path_to_delete, self.show_delete_warning):
                self._load_chat_history()
        except Exception as e:
            print(f"Error during delete: {e}")
            QMessageBox.warning(self, "Error", f"Could not delete item: {e}")

    def handle_send_message(self):
        """Handles the 'Send' button click."""
        if not all([self.messageInput, self.modelComboBox, self.chatDisplay, self.llm_service]):
            print("Error: UI components or services not initialized.")
            return

        if not self.current_chat_file_path:
            QMessageBox.warning(self, "No Chat Selected",
                                "Please select a chat or create a new one before sending a message.")
            return

        message = self.messageInput.toPlainText().strip()
        model = self.modelComboBox.currentText()
        if not message:
            return

        print(f"Sending to {model}: {message}")

        # 1. Add the user's message to the display
        self._add_chat_message("user", message)

        # 2. Clear the input
        self.messageInput.clear()

        # 3. Save the chat (which now reads from the widgets)
        self._save_current_chat()

        # 4. Show a "thinking" message (but don't save it)
        #    We pass "thinking" as a role so it's not saved
        thinking_bubble = self._add_chat_message("thinking", "...")
        QApplication.processEvents()  # Force UI to update

        # 5. Call the LLM service with the current message history
        try:
            # self.current_messages was updated by _save_current_chat()
            response_content = self.llm_service.get_response(model, list(self.current_messages))

            # 6. Update the "thinking" bubble with the real response
            if thinking_bubble:
                # Find the QListWidgetItem for the thinking bubble
                for i in range(self.chatDisplay.count()):
                    item = self.chatDisplay.item(i)
                    widget = self.chatDisplay.itemWidget(item)
                    if widget == thinking_bubble:
                        widget.set_message("assistant", response_content, item)
                        break

            # 7. Save the chat *again* with the new AI response
            self._save_current_chat()

        except Exception as e:
            print(f"Error calling LLM: {e}")
            error_message = f"Error: {e}"
            if thinking_bubble:
                for i in range(self.chatDisplay.count()):
                    item = self.chatDisplay.item(i)
                    widget = self.chatDisplay.itemWidget(item)
                    if widget == thinking_bubble:
                        widget.set_message("assistant", error_message, item)
                        break
            # Save the error message to the chat
            self._save_current_chat()


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
    chat_history_path.mkdir(parents=True, exist_ok=True)
    print(f"Chat history root initialized at: {chat_history_path.resolve()}")
    chat_history_manager = ChatHistoryManager(chat_history_path)

    print("Managers injected into MainWindow.")
    window = MainWindow(config_manager, key_manager, chat_history_manager)
    window.show()
    sys.exit(app.exec())
