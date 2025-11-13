import logging
import sys
from pathlib import Path

from PySide6.QtCore import QFile, QPoint, Qt, QTimer, QObject, QEvent, QMimeData, QThread, Signal
from PySide6.QtGui import (
    QResizeEvent, QKeyEvent, QWheelEvent, QFontMetrics, QShortcut, QKeySequence, QDragEnterEvent,
    QDragMoveEvent, QDropEvent
)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QPushButton,
    QComboBox, QTreeWidget, QMenu, QMessageBox,
    QTreeWidgetItem, QListWidget, QListWidgetItem,
    QTreeWidgetItemIterator, QDialog, QTextEdit, QLayout, QBoxLayout, QLineEdit
)

# We MUST import PathRole to use it
from chat_history_manager import ChatHistoryManager, PathRole
from chat_message_widget import ChatMessageWidget
from config_manager import ConfigManager
from key_manager import KeyManager
from keys_dialog import KeysDialog
from llm_service import LLMService
from refine_dialog import RefineDialog
from spell_check_text_edit import SpellCheckTextEdit
from system_message_dialog import SystemMessageDialog


class LLMWorker(QThread):
    """Worker thread for asynchronous LLM calls."""
    finished = Signal(str)  # Emits response content
    error = Signal(str)  # Emits error message
    
    def __init__(self, llm_service, model: str, messages: list):
        super().__init__()
        self.llm_service = llm_service
        self.model = model
        self.messages = messages
    
    def run(self):
        """Execute LLM call in background thread."""
        try:
            response_content = self.llm_service.get_response(self.model, self.messages)
            self.finished.emit(response_content)
        except Exception as e:
            error_message = f"Error: {e}"
            self.error.emit(error_message)


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
        self.projectsTree = None  # QTreeWidget for projects
        self.chatsList = None  # QListWidget for top-level chats
        self.chatHistoryTree = None  # Deprecated - kept for backward compatibility
        self.newChatButton = None
        self.newProjectButton = None

        # A variable to hold the path of the currently active chat
        self.current_chat_file_path: Path | None = None
        # Store current messages to avoid re-reading from widgets
        self.current_messages: list[dict] = []
        self._focused_assistant_widget = None  # Track which assistant message is currently focused
        self._llm_call_in_progress = False  # Track if an LLM call is in progress
        self._llm_worker_thread = None  # Thread for async LLM calls
        # Store pending LLM call context
        self._pending_llm_widget = None
        self._pending_llm_list_item = None
        self._pending_llm_list_widget = None
        self._pending_llm_model = None
        self._pending_llm_thinking_bubble = None  # For handle_send_message

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

            # Set smooth scrolling - one line at a time
            scrollbar = self.chatDisplay.verticalScrollBar()
            if scrollbar:
                # Get font metrics to calculate line height
                font = self.chatDisplay.font()
                metrics = QFontMetrics(font)
                line_height = metrics.height()
                # Set single step to one line height for smooth scrolling
                scrollbar.setSingleStep(line_height)
                # Enable smooth scrolling
                scrollbar.setPageStep(viewport_height if (
                                                             viewport_height := self.chatDisplay.viewport().height()) > 0 else line_height * 10)

            # Install event filter for smooth scrolling and arrow key navigation
            self.chatDisplay.installEventFilter(self)
            # Enable keyboard focus for arrow key navigation
            self.chatDisplay.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

            # Create QShortcut for PageUp and PageDown for reliable key handling
            # On Mac, these are Fn+Up and Fn+Down
            self.shortcut_prev_user = QShortcut(QKeySequence(Qt.Key.Key_PageUp), self)
            self.shortcut_prev_user.activated.connect(lambda: self._jump_to_user_message(direction=-1))

            self.shortcut_next_user = QShortcut(QKeySequence(Qt.Key.Key_PageDown), self)
            self.shortcut_next_user.activated.connect(lambda: self._jump_to_user_message(direction=1))

        else:
            print("Warning: 'chatDisplay' (QListWidget) not found.")

        # Initially disable messageInput until a chat is selected
        if self.messageInput:
            self.messageInput.setEnabled(False)

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

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events for PageUp/PageDown key navigation."""
        # Handle PageUp/PageDown keys for navigating user messages
        if self.chatDisplay and self.chatDisplay.isVisible():
            if event.key() == Qt.Key.Key_PageUp:
                # Jump to previous user message from currently focused bubble
                self._jump_to_user_message(direction=-1)
                return
            elif event.key() == Qt.Key.Key_PageDown:
                # Jump to next user message from currently focused bubble
                self._jump_to_user_message(direction=1)
                return

        super().keyPressEvent(event)

    def eventFilter(self, obj, event: QEvent):
        """Event filter for chatDisplay: smooth scrolling, and drag-and-drop for projects tree."""
        # Handle drag-and-drop events for projects tree
        if obj == self.projectsTree:
            if event.type() == QEvent.Type.DragEnter:
                if isinstance(event, QDragEnterEvent):
                    self._projects_tree_drag_enter_event(event)
                    return True
            elif event.type() == QEvent.Type.DragMove:
                if isinstance(event, QDragMoveEvent):
                    self._projects_tree_drag_move_event(event)
                    return True
            elif event.type() == QEvent.Type.Drop:
                if isinstance(event, QDropEvent):
                    self._projects_tree_drop_event(event)
                    return True

        # Handle smooth scrolling for chatDisplay
        if obj == self.chatDisplay:
            if event.type() == QEvent.Type.Wheel:
                if isinstance(event, QWheelEvent):
                    # Get the scrollbar
                    scrollbar = self.chatDisplay.verticalScrollBar()
                    if scrollbar:
                        # Use singleStep for smooth line-by-line scrolling
                        single_step = scrollbar.singleStep()

                        # Get the wheel delta (angleDelta is in 1/8 degree units, typically 120*8 = 960 per click)
                        delta = event.angleDelta().y()

                        # For smooth scrolling, scroll proportionally to the delta
                        # Each 960 units = one "click" = one line
                        # For smaller deltas, scroll proportionally (e.g., 480 units = 0.5 lines)
                        lines_to_scroll = delta / 960.0

                        # Scroll by the calculated number of lines (can be fractional for smoothness)
                        current_value = scrollbar.value()
                        pixels_to_scroll = int(lines_to_scroll * single_step)
                        new_value = current_value - pixels_to_scroll

                        # Clamp to valid range
                        new_value = max(scrollbar.minimum(), min(new_value, scrollbar.maximum()))
                        scrollbar.setValue(new_value)

                        return True  # Event handled

            elif event.type() == QEvent.Type.KeyPress:
                if isinstance(event, QKeyEvent):
                    if event.key() == Qt.Key.Key_Up:
                        # Jump to previous user message from currently focused bubble
                        self._jump_to_user_message(direction=-1)
                        return True
                    elif event.key() == Qt.Key.Key_Down:
                        # Jump to next user message from currently focused bubble
                        self._jump_to_user_message(direction=1)
                        return True

        return super().eventFilter(obj, event)

    def _jump_to_user_message(self, direction: int):
        """
        Jump to the previous (direction=-1) or next (direction=1) user message bubble from the currently focused one.
        """
        if not self.chatDisplay:
            return

        # Find the currently focused/selected item
        # First try to find an item that has a focused widget
        current_item = None
        current_index = -1

        # Check if any item has a focused widget
        for i in range(self.chatDisplay.count()):
            item = self.chatDisplay.item(i)
            if item:
                widget = self.chatDisplay.itemWidget(item)
                if isinstance(widget, ChatMessageWidget):
                    # Check if the widget or its messageContent has focus
                    if widget.hasFocus() or (
                            hasattr(widget, 'ui') and widget.ui.messageContent and widget.ui.messageContent.hasFocus()):
                        current_item = item
                        current_index = i
                        break

        # If no focused item found, try to find the item at the top of the viewport
        if current_item is None:
            scrollbar = self.chatDisplay.verticalScrollBar()
            if scrollbar:
                current_scroll = scrollbar.value()
                # Find the first visible item
                for i in range(self.chatDisplay.count()):
                    item = self.chatDisplay.item(i)
                    if item:
                        item_rect = self.chatDisplay.visualItemRect(item)
                        if item_rect.top() >= current_scroll - 10:  # Allow small tolerance
                            # current_item = item
                            current_index = i
                            break

        # Find all user message items with their indices
        user_items = []
        for i in range(self.chatDisplay.count()):
            item = self.chatDisplay.item(i)
            if item:
                widget = self.chatDisplay.itemWidget(item)
                if isinstance(widget, ChatMessageWidget) and widget.role == "user":
                    user_items.append((i, item))

        if not user_items:
            return

        # Find the target user message based on direction and current position
        target_item = None

        if current_index >= 0:
            # Find user messages relative to current position
            if direction < 0:  # Up - find previous user message
                # Find the last user message before current_index
                for i, item in reversed(user_items):
                    if i < current_index:
                        target_item = item
                        break
                # If no previous user message, stay at current (already at topmost)
                if target_item is None:
                    return
            else:  # Down - find next user message
                # Find the first user message after current_index
                for i, item in user_items:
                    if i > current_index:
                        target_item = item
                        break
                # If no next user message, check if we're at the last message
                if target_item is None:
                    # Check if current item is the last message (user or assistant)
                    if current_index >= self.chatDisplay.count() - 1:
                        return  # Already at last message
                    # Otherwise, go to the last user message
                    target_item = user_items[-1][1]
        else:
            # No current item found, use scroll-based navigation as fallback
            scrollbar = self.chatDisplay.verticalScrollBar()
            if scrollbar:
                current_scroll = scrollbar.value()
                viewport_height = self.chatDisplay.viewport().height()
                current_bottom = current_scroll + viewport_height

                if direction < 0:  # Up
                    # Find the last user message above viewport
                    for i, item in reversed(user_items):
                        item_rect = self.chatDisplay.visualItemRect(item)
                        if item_rect.top() < current_scroll:
                            target_item = item
                            break
                    if target_item is None:
                        target_item = user_items[0][1]  # First user message
                else:  # Down
                    # Find the first user message below viewport
                    for i, item in user_items:
                        item_rect = self.chatDisplay.visualItemRect(item)
                        if item_rect.top() > current_bottom:
                            target_item = item
                            break
                    if target_item is None:
                        # Check if we're at the last message
                        last_item = self.chatDisplay.item(self.chatDisplay.count() - 1)
                        if last_item:
                            last_rect = self.chatDisplay.visualItemRect(last_item)
                            if last_rect.bottom() <= current_bottom:
                                return  # Already showing last message
                        target_item = user_items[-1][1]  # Last user message

        # Scroll to the target item, positioning it at the top
        if target_item:
            self.chatDisplay.scrollToItem(target_item, self.chatDisplay.ScrollHint.PositionAtTop)
            # Set focus to the target item's widget for visual feedback
            widget = self.chatDisplay.itemWidget(target_item)
            if isinstance(widget, ChatMessageWidget):
                widget.setFocus()

    def _find_ui_children_by_name(self):
        """Finds all necessary widgets using findChild."""
        self.keysButton = self.findChild(QPushButton, "keysButton")
        self.sendButton = self.findChild(QPushButton, "sendButton")
        self.modelComboBox = self.findChild(QComboBox, "modelComboBox")
        self.messageInput = self.findChild(QTextEdit, "messageInput")
        self.chatDisplay = self.findChild(QListWidget, "chatDisplay")  # <-- QListWidget
        self.projectsTree = self.findChild(QTreeWidget, "projectsTree")
        self.chatsList = self.findChild(QListWidget, "chatsList")
        self.chatHistoryTree = self.projectsTree  # For backward compatibility
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
            self.projectsTree = self.ui.projectsTree
            self.chatsList = self.ui.chatsList
            self.chatHistoryTree = self.projectsTree  # For backward compatibility
            self.newChatButton = self.ui.newChatButton
            self.newProjectButton = self.ui.newProjectButton

            # Replace messageInput with spell-checking version
            if self.messageInput:
                self._replace_with_spell_check(self.messageInput, "messageInput")

            # Configure input container layout after messageInput is replaced
            self._configure_input_container_layout()

            if self.projectsTree:
                self.projectsTree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            if self.chatsList:
                self.chatsList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

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

            # Replace messageInput with spell-checking version
            if self.messageInput:
                self._replace_with_spell_check(self.messageInput, "messageInput")

            # Configure input container layout after messageInput is replaced
            self._configure_input_container_layout()

            if self.projectsTree:
                self.projectsTree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            if self.chatsList:
                self.chatsList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

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

        if self.projectsTree:
            self.projectsTree.customContextMenuRequested.connect(self._show_projects_context_menu)
            print("Projects tree context menu connected.")
            self.projectsTree.currentItemChanged.connect(self._on_projects_item_selected)
            self.projectsTree.itemChanged.connect(self._on_projects_item_edited)
            # Enable drag-and-drop for projects tree
            self.projectsTree.setDragDropMode(QTreeWidget.DragDropMode.DragDrop)
            self.projectsTree.setDefaultDropAction(Qt.DropAction.MoveAction)

            # Override drag and drop events using lambdas
            def custom_drag_enter(event):
                self._projects_tree_drag_enter_event(event)

            def custom_drag_move(event):
                self._projects_tree_drag_move_event(event)

            def custom_drop(event):
                self._projects_tree_drop_event(event)

            def custom_start_drag(supported_actions):
                return self._projects_tree_start_drag(supported_actions)

            self.projectsTree.dragEnterEvent = custom_drag_enter
            self.projectsTree.dragMoveEvent = custom_drag_move
            self.projectsTree.dropEvent = custom_drop
            self.projectsTree.startDrag = custom_start_drag
            # Install event filter for drag events
            self.projectsTree.installEventFilter(self)
            print("Projects tree item selection connected.")
        else:
            print("Warning: 'projectsTree' not found.")

        if self.chatsList:
            self.chatsList.customContextMenuRequested.connect(self._show_chats_context_menu)
            print("Chats list context menu connected.")
            self.chatsList.currentItemChanged.connect(self._on_chats_item_selected)
            self.chatsList.itemChanged.connect(self._on_chats_item_edited)
            # Enable drag-and-drop for chats list
            self.chatsList.setDragEnabled(True)
            self.chatsList.setAcceptDrops(True)
            self.chatsList.setDefaultDropAction(Qt.DropAction.MoveAction)
            # Override startDrag method using a lambda that captures self
            # original_start_drag = self.chatsList.startDrag

            def custom_start_drag(supported_actions):
                return self._chats_list_start_drag(supported_actions)

            self.chatsList.startDrag = custom_start_drag

            # Override drag and drop events for accepting drops
            def custom_drag_enter(event):
                self._chats_list_drag_enter_event(event)

            def custom_drag_move(event):
                self._chats_list_drag_move_event(event)

            def custom_drop(event):
                self._chats_list_drop_event(event)

            self.chatsList.dragEnterEvent = custom_drag_enter
            self.chatsList.dragMoveEvent = custom_drag_move
            self.chatsList.dropEvent = custom_drop
            print("Chats list item selection connected.")
        else:
            print("Warning: 'chatsList' not found.")

        main_splitter = self.findChild(QSplitter, "mainSplitter")
        if main_splitter:
            main_splitter.splitterMoved.connect(self._on_chat_display_resize)
            print("Main splitter connected to resize.")

        chat_splitter = self.findChild(QSplitter, "chatAreaSplitter")
        if chat_splitter:
            chat_splitter.splitterMoved.connect(self._on_chat_display_resize)
            print("Chat splitter connected to resize.")

    def _replace_with_spell_check(self, old_widget, object_name: str):
        """Replace a QTextEdit widget with SpellCheckTextEdit."""
        try:
            from PySide6.QtWidgets import QTextEdit
            if isinstance(old_widget, QTextEdit):
                # Get parent and layout
                parent = old_widget.parent()
                layout = None

                # Find the layout that contains this widget
                if parent:
                    for child in parent.children():
                        if isinstance(child, QLayout):
                            idx = child.indexOf(old_widget)
                            if idx >= 0:
                                layout = child
                                break

                if layout:
                    # Get widget properties
                    text = old_widget.toPlainText()
                    placeholder = old_widget.placeholderText()
                    max_height = old_widget.maximumHeight()

                    # Create new spell-checking widget
                    new_widget = SpellCheckTextEdit(parent)
                    new_widget.setObjectName(object_name)
                    new_widget.setPlainText(text)
                    new_widget.setPlaceholderText(placeholder)
                    new_widget.setMaximumHeight(max_height)
                    new_widget.setAcceptRichText(old_widget.acceptRichText())

                    # Replace in layout
                    idx = layout.indexOf(old_widget)
                    layout.removeWidget(old_widget)
                    # insertWidget is only available on QBoxLayout (and subclasses like QVBoxLayout, QHBoxLayout)
                    if isinstance(layout, QBoxLayout):
                        layout.insertWidget(idx, new_widget)
                    else:
                        # For other layout types, just add the widget
                        layout.addWidget(new_widget)
                    old_widget.deleteLater()

                    # Update reference
                    self.messageInput = new_widget
                    print(f"Replaced {object_name} with spell-checking version.")
        except Exception as e:
            print(f"Warning: Could not replace {object_name} with spell-checking version: {e}")

    def _configure_input_container_layout(self):
        """Configure inputContainer layout so only messageInput resizes, bottomControlsLayout stays fixed."""
        from PySide6.QtWidgets import QWidget, QVBoxLayout

        input_container = self.findChild(QWidget, "inputContainer")
        if not input_container:
            return

        input_container_layout = input_container.layout()
        if not input_container_layout or not isinstance(input_container_layout, QVBoxLayout):
            return

        # The layout should have 2 items: messageInput (index 0) and bottomControlsLayout (index 1)
        # Set stretch factor: messageInput = 1 (can expand/contract), bottomControlsLayout = 0 (fixed)
        if input_container_layout.count() >= 2:
            # Get messageInput widget (index 0)
            message_input_item = input_container_layout.itemAt(0)
            if message_input_item:
                message_input_widget = message_input_item.widget()
                if message_input_widget:
                    # Remove maximum height constraint so messageInput can expand
                    message_input_widget.setMaximumHeight(16777215)  # Qt's maximum value
                    # Set size policy to allow vertical expansion
                    from PySide6.QtWidgets import QSizePolicy
                    size_policy = message_input_widget.sizePolicy()
                    size_policy.setVerticalPolicy(QSizePolicy.Policy.Expanding)
                    message_input_widget.setSizePolicy(size_policy)
                    # Set stretch factor > 0 so messageInput can expand/contract
                    input_container_layout.setStretchFactor(message_input_widget, 1)

            # Get bottomControlsLayout (index 1)
            bottom_controls_item = input_container_layout.itemAt(1)
            if bottom_controls_item:
                bottom_controls_layout = bottom_controls_item.layout()
                if bottom_controls_layout:
                    # Set stretch factor = 0 so bottomControlsLayout stays fixed
                    input_container_layout.setStretchFactor(bottom_controls_layout, 0)
                else:
                    # If it's a widget instead of a layout, get the widget
                    bottom_controls_widget = bottom_controls_item.widget()
                    if bottom_controls_widget:
                        # Set stretch factor = 0 so bottomControlsLayout stays fixed
                        input_container_layout.setStretchFactor(bottom_controls_widget, 0)

            print("Input container layout configured: messageInput resizes, bottomControlsLayout fixed.")
        else:
            print(f"Warning: inputContainerLayout has {input_container_layout.count()} items, expected 2.")

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
        """Loads projects into projectsTree and top-level chats into chatsList."""
        if not self.chat_history_manager:
            print("Warning: 'chat_history_manager' not found.")
            return

        if self.projectsTree:
            expanded_paths = self._get_expanded_state()
            self.chat_history_manager.load_projects(self.projectsTree)
            self._set_expanded_state(expanded_paths)

        if self.chatsList:
            self.chat_history_manager.load_top_level_chats(self.chatsList)

    def _get_expanded_state(self) -> set:
        """Returns a set of string paths for all expanded items in the projects tree."""
        expanded_paths = set()
        if not self.projectsTree:
            return expanded_paths

        iterator = QTreeWidgetItemIterator(self.projectsTree)
        while iterator.value():
            item = iterator.value()
            if item.isExpanded():
                path_str = item.data(0, PathRole)
                if path_str:
                    expanded_paths.add(path_str)
            iterator += 1
        return expanded_paths

    def _set_expanded_state(self, expanded_paths: set):
        """Restores the expansion state of the projects tree from a set of string paths."""
        if not self.projectsTree or not expanded_paths:
            return

        iterator = QTreeWidgetItemIterator(self.projectsTree)
        while iterator.value():
            item = iterator.value()
            path_str = item.data(0, PathRole)
            if path_str in expanded_paths:
                item.setExpanded(True)
            iterator += 1

    def _add_chat_message(self, role: str, content: str, model: str = None) -> ChatMessageWidget | None:
        """
        Adds a new chat bubble widget to the chatDisplay (QListWidget).
        
        Args:
            role: The message role ("user", "assistant", etc.)
            content: The message content
            model: Optional model name (only used for assistant messages)
        """
        if not self.chatDisplay:
            return None

        chat_widget = ChatMessageWidget()
        list_item = QListWidgetItem(self.chatDisplay)

        chat_widget.editingFinished.connect(self._save_current_chat)
        # Connect action button signals using a slot that finds the widget by sender
        # This avoids capturing widget references that might become invalid
        chat_widget.cutRequested.connect(self._on_cut_requested)
        chat_widget.cutPairRequested.connect(self._on_cut_pair_requested)
        chat_widget.cutBelowRequested.connect(self._on_cut_below_requested)
        chat_widget.regenerateRequested.connect(self._on_regenerate_requested)
        chat_widget.regenerateUserRequested.connect(self._on_regenerate_user_requested)
        # Connect focus signal to update modelComboBox
        chat_widget.focused.connect(self._on_message_focused)

        chat_widget.set_message(role, content, list_item, model)
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
        # Clear focused widget reference
        self._focused_assistant_widget = None
        # Do NOT clear self.current_messages here

    def _on_tree_item_selected(self, current: QTreeWidgetItem, previous: QTreeWidgetItem):
        """Deprecated - use _on_projects_item_selected instead."""
        self._on_projects_item_selected(current, previous)

    def _on_projects_item_selected(self, current: QTreeWidgetItem, previous: QTreeWidgetItem):
        """
        Handles loading a chat when an item in the projects tree is clicked.
        """
        if not current:
            # No item selected - save messageInput content before clearing
            if self.current_chat_file_path:
                self._save_current_chat()
            self.current_chat_file_path = None
            self.current_messages = []  # Clear messages
            self._clear_chat_display()
            # Disable messageInput when no chat is selected
            if self.messageInput:
                self.messageInput.setEnabled(False)
            return

        item_path_str = current.data(0, PathRole)
        if not item_path_str:
            return

        item_path = Path(item_path_str)

        if item_path.is_dir():
            # It's a project, not a chat file. Save messageInput content before clearing.
            if self.current_chat_file_path:
                self._save_current_chat()
            self.current_chat_file_path = None
            self.current_messages = []  # Clear messages
            self._clear_chat_display()
            # Disable messageInput when a directory is selected
            if self.messageInput:
                self.messageInput.setEnabled(False)

        elif item_path.is_file() and item_path.suffix == '.json':
            # Save messageInput content to the previous chat before loading a new one
            if self.current_chat_file_path and self.current_chat_file_path != item_path:
                self._save_current_chat()

            # It's a chat file. Load it.
            print(f"Loading chat: {item_path}")
            self._load_chat_from_file(item_path)

    def _on_chats_item_selected(self, current: QListWidgetItem, previous: QListWidgetItem = None):
        """
        Handles loading a chat when an item in the chats list is clicked.
        """
        if not current:
            # No item selected - save messageInput content before clearing
            if self.current_chat_file_path:
                self._save_current_chat()
            self.current_chat_file_path = None
            self.current_messages = []  # Clear messages
            self._clear_chat_display()
            # Disable messageInput when no chat is selected
            if self.messageInput:
                self.messageInput.setEnabled(False)
            return

        item_path_str = current.data(PathRole)
        if not item_path_str:
            return

        item_path = Path(item_path_str)

        if item_path.is_file() and item_path.suffix == '.json':
            # Save messageInput content to the previous chat before loading a new one
            if self.current_chat_file_path and self.current_chat_file_path != item_path:
                self._save_current_chat()

            # It's a chat file. Load it.
            print(f"Loading chat: {item_path}")
            self._load_chat_from_file(item_path)

    def _load_chat_from_file(self, file_path: Path):
        """Loads a chat from a file and populates the display."""
        self.current_chat_file_path = file_path

        # Enable messageInput when a chat file is loaded
        if self.messageInput:
            self.messageInput.setEnabled(True)

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
        # Filter out system messages - they should not be displayed
        for message in messages_to_display:
            role = message.get("role", "user")
            # Skip system messages in display
            if role == "system":
                continue
            content = message.get("content", "")
            model = message.get("model") if role == "assistant" else None
            self._add_chat_message(role, content, model)

        if self.messageInput:
            self.messageInput.setPlainText(last_message_content)

        # --- Set modelComboBox to the last assistant message's model (if any) ---
        if self.modelComboBox:
            last_assistant_model = None
            # Find the last assistant message with a model
            for message in reversed(self.current_messages):
                if message.get("role") == "assistant" and "model" in message:
                    last_assistant_model = message.get("model")
                    break

            if last_assistant_model:
                # Try to set the combo box to this model
                index = self.modelComboBox.findText(last_assistant_model)
                if index >= 0:
                    self.modelComboBox.setCurrentIndex(index)
                else:
                    print(f"Warning: Model '{last_assistant_model}' from chat history not found in model list.")

        # After loading, update all bubble sizes
        self._on_chat_display_resize()

    def _save_current_chat(self):
        """Saves the current state of the chatDisplay to its file."""
        if not self.current_chat_file_path:
            print("Save skipped: No active chat file selected.")
            return

        if not self.chatDisplay:
            return

        # Get system messages from current_messages (they're not displayed)
        system_messages = [msg for msg in self.current_messages if msg.get("role") == "system"]

        messages_to_save = []
        # Add system messages first (if any)
        messages_to_save.extend(system_messages)

        # Add messages from widgets
        # IMPORTANT: Check widget validity to avoid segfaults
        for i in range(self.chatDisplay.count()):
            item = self.chatDisplay.item(i)
            if not item:
                continue
            widget = self.chatDisplay.itemWidget(item)
            if widget and isinstance(widget, ChatMessageWidget):
                # Skip deleted widgets
                if widget.is_deleted():
                    continue
                # Do not save "thinking" messages
                role = widget.role
                if role in ("user", "assistant"):
                    try:
                        # Use get_message_dict() to preserve model information
                        messages_to_save.append(widget.get_message_dict())
                    except (RuntimeError, AttributeError):
                        # Widget was deleted, skip it
                        continue

        if self.messageInput:
            last_user_message = self.messageInput.toPlainText().strip()
            if last_user_message:
                messages_to_save.append({"role": "user", "content": last_user_message})

        # Save the collected messages to the file
        self.chat_history_manager.save_chat(self.current_chat_file_path, messages_to_save)

        # Update the internal state
        self.current_messages = messages_to_save

    def _show_tree_context_menu(self, position: QPoint):
        """Deprecated - use _show_projects_context_menu instead."""
        self._show_projects_context_menu(position)

    def _show_projects_context_menu(self, position: QPoint):
        """Shows a context menu when right-clicking on the projects tree."""
        context_menu = QMenu(self)
        item = self.projectsTree.itemAt(position)

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

            elif item_path.is_file() and item_path.suffix == '.json':
                # It's a chat file - add "Edit System Message" option
                edit_system_action = context_menu.addAction("Edit System Message")
                edit_system_action.triggered.connect(lambda: self.handle_edit_system_message(item))
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

        context_menu.exec(self.projectsTree.viewport().mapToGlobal(position))

    def _show_chats_context_menu(self, position: QPoint):
        """Shows a context menu when right-clicking on the chats list."""
        context_menu = QMenu(self)
        item = self.chatsList.itemAt(position)

        if item:
            item_path_str = item.data(PathRole)
            if not item_path_str:
                return

            item_path = Path(item_path_str)

            if item_path.is_file() and item_path.suffix == '.json':
                # It's a chat file - add "Edit System Message" option
                edit_system_action = context_menu.addAction("Edit System Message")
                edit_system_action.triggered.connect(lambda: self.handle_edit_system_message_chat(item))
                context_menu.addSeparator()

                rename_action = context_menu.addAction("Rename")
                rename_action.triggered.connect(lambda: self.handle_rename_chat_item(item))

                delete_action = context_menu.addAction("Delete")
                delete_action.triggered.connect(lambda: self.handle_delete_chat_item(item))

        context_menu.exec(self.chatsList.viewport().mapToGlobal(position))

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
        """Handles the 'New Chat' button click (creates a root 'Chat N' with inline editing)."""
        print("New Chat (root) clicked.")
        if self.chatsList and self.chat_history_manager:
            new_item = self.chat_history_manager.create_new_chat_in_list(self.chatsList,
                                                                         self.chat_history_manager.history_root)
            if new_item:
                self.chatsList.setCurrentItem(new_item)
                # Start inline editing
                self._start_inline_edit_chat(new_item)

    def handle_new_root_project(self):
        """Handles the 'New Project' button click (creates a top-level project with inline editing)."""
        print("New Project (root) clicked.")
        if self.projectsTree and self.chat_history_manager:
            new_item = self.chat_history_manager.create_project(self.projectsTree, parent_item=None)
            if new_item:
                self.projectsTree.setCurrentItem(new_item)
                # Start inline editing
                self._start_inline_edit_tree_item(new_item)

    def handle_new_chat_in_project(self, project_item):
        """Creates a named chat inside the selected project with inline editing."""
        print(f"New Chat in '{project_item.text(0)}' clicked.")
        if self.projectsTree and self.chat_history_manager:
            new_item = self.chat_history_manager.create_new_chat(self.projectsTree, parent_project_item=project_item)
            if new_item:
                self.projectsTree.setCurrentItem(new_item)
                # Start inline editing
                self._start_inline_edit_tree_item(new_item)

    def handle_new_subproject(self, project_item: QTreeWidgetItem):
        """Creates a subproject inside the selected project with inline editing."""
        print(f"New Subproject in '{project_item.text(0)}' clicked.")
        if self.projectsTree and self.chat_history_manager:
            new_item = self.chat_history_manager.create_project(self.projectsTree, parent_item=project_item)
            if new_item:
                self.projectsTree.setCurrentItem(new_item)
                # Start inline editing
                self._start_inline_edit_tree_item(new_item)

    def handle_rename_item(self, item: QTreeWidgetItem):
        """Handles the 'Rename' context menu action - starts inline editing."""
        try:
            # Check if it's a project (directory) or chat (file)
            old_path = Path(item.data(0, PathRole))
            if old_path.is_dir() or (old_path.is_file() and old_path.suffix == '.json'):
                # It's a project or chat file in the tree - use tree inline editing
                self._start_inline_edit_tree_item(item)
        except Exception as e:
            print(f"Error during rename: {e}")
            QMessageBox.warning(self, "Error", f"Could not start rename: {e}")

    def handle_delete_item(self, item: QTreeWidgetItem):
        """Handles the 'Delete' context menu action."""
        try:
            path_to_delete = Path(item.data(0, PathRole))
            if self.chat_history_manager.delete_item(path_to_delete, self.show_delete_warning):
                self._load_chat_history()
        except Exception as e:
            print(f"Error during delete: {e}")
            QMessageBox.warning(self, "Error", f"Could not delete item: {e}")

    def handle_rename_chat_item(self, item: QListWidgetItem):
        """Handles the 'Rename' context menu action for chat list items - starts inline editing."""
        try:
            # Use inline editing for chat list items
            self._start_inline_edit_chat(item)
        except Exception as e:
            print(f"Error during rename: {e}")
            QMessageBox.warning(self, "Error", f"Could not start rename: {e}")

    def handle_delete_chat_item(self, item: QListWidgetItem):
        """Handles the 'Delete' context menu action for chat list items."""
        try:
            path_to_delete = Path(item.data(PathRole))
            if self.chat_history_manager.delete_item(path_to_delete, self.show_delete_warning):
                self._load_chat_history()
        except Exception as e:
            print(f"Error during delete: {e}")
            QMessageBox.warning(self, "Error", f"Could not delete item: {e}")

    def _start_inline_edit_tree_item(self, item: QTreeWidgetItem):
        """Starts inline editing for a tree item (project or chat) in the projects tree."""
        if not item or not self.projectsTree:
            return
        # Ensure item is editable
        flags = item.flags()
        if not (flags & Qt.ItemFlag.ItemIsEditable):
            item.setFlags(flags | Qt.ItemFlag.ItemIsEditable)

        # Use a timer to ensure the item is fully displayed before starting edit
        # Store item reference to avoid lambda capture issues
        def start_edit():
            if item and self.projectsTree:
                self.projectsTree.editItem(item, 0)

        QTimer.singleShot(100, start_edit)

    def _start_inline_edit_chat(self, item: QListWidgetItem):
        """Starts inline editing for a chat item in the chats list."""
        if not item or not self.chatsList:
            return

        # QListWidget doesn't have built-in editing, so we'll use a custom approach
        # Store item reference to avoid lambda capture issues
        def start_edit():
            if item and self.chatsList:
                self._edit_chat_item_inline(item)

        QTimer.singleShot(100, start_edit)

    def _edit_chat_item_inline(self, item: QListWidgetItem):
        """Edits a chat list item inline using a custom editor."""
        # Get current name and preserve icon
        old_name = item.text()
        old_path = Path(item.data(PathRole))
        icons = self.chat_history_manager.get_icons()
        file_icon = icons["file"]

        # Ensure icon is set before starting edit
        item.setIcon(file_icon)

        # Create a line edit widget positioned over the item
        # Adjust rect to only cover text area, leaving space for icon
        rect = self.chatsList.visualItemRect(item)
        # QListWidget typically reserves ~20-24px for icon on the left
        icon_width = 24
        text_rect = rect.adjusted(icon_width, 0, 0, 0)  # Move left edge right by icon width

        editor = QLineEdit(self.chatsList.viewport())
        editor.setText(old_name)
        editor.selectAll()
        editor.setGeometry(text_rect)
        editor.show()
        editor.setFocus()

        # Force icon to remain visible after editor is shown
        # Use a timer to ensure icon is set after UI updates
        def ensure_icon():
            if item:
                item.setIcon(file_icon)

        QTimer.singleShot(10, ensure_icon)
        QTimer.singleShot(50, ensure_icon)

        # Flag to prevent multiple calls to finish_edit
        _editing_finished = False

        def finish_edit():
            nonlocal _editing_finished
            if _editing_finished:
                return
            _editing_finished = True

            new_name = editor.text().strip()
            editor.deleteLater()

            # Always restore the icon immediately after editor is removed
            item.setIcon(file_icon)

            if new_name and new_name != old_name:
                # Rename the file
                if self.chat_history_manager.rename_item(old_path, new_name, self):
                    # Update the item
                    item.setText(new_name)
                    # Update the path in the item
                    new_path = old_path.with_stem(new_name) if old_path.is_file() else old_path.with_name(new_name)
                    item.setData(PathRole, str(new_path))
                    # Always set the icon after updating text to ensure it's visible
                    item.setIcon(file_icon)
                    # Ensure item flags are correct (enabled and selectable, but not editable by default)
                    # This matches the flags used when loading existing chats
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    # Verify the path data is correct
                    if not item.data(PathRole) or not Path(item.data(PathRole)).exists():
                        # If path is invalid, reload the list
                        self._load_chat_history()
                        return
                    # Clear selection first, then set it again to ensure proper state
                    self.chatsList.clearSelection()
                    # Process events to ensure the widget is fully updated
                    QApplication.processEvents()
                    # Set the current item - this should trigger currentItemChanged signal
                    # Block signals temporarily to avoid double-triggering, then manually call handler
                    self.chatsList.blockSignals(True)
                    self.chatsList.setCurrentItem(item)
                    self.chatsList.blockSignals(False)
                    # Manually trigger the selection handler to load the chat
                    self._on_chats_item_selected(item, None)
                    # Force widget repaint to ensure context menu works properly
                    self.chatsList.viewport().repaint()
                    # Don't reload - just update the current item to preserve selection and icon
            elif not new_name:
                # Empty name - delete the item
                if old_path.exists():
                    old_path.unlink()
                self._load_chat_history()
            else:
                # Name unchanged, but ensure icon is still there
                item.setIcon(file_icon)

        editor.editingFinished.connect(finish_edit)

        # Handle Escape and Return keys - event filter must inherit from QObject
        class EditorEventFilter(QObject):
            def __init__(self, editor, item, icon, finish_callback):
                super().__init__()
                self.editor = editor
                self.item = item
                self.icon = icon
                self.finish_callback = finish_callback

            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.KeyPress and isinstance(event, QKeyEvent):
                    if event.key() == Qt.Key.Key_Escape:
                        self.editor.deleteLater()
                        # Restore icon when canceling edit
                        if self.item:
                            self.item.setIcon(self.icon)
                        return True
                    elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                        # Accept the edit when Return/Enter is pressed
                        # Use QTimer to defer the callback to avoid issues with event processing
                        from PySide6.QtCore import QTimer
                        QTimer.singleShot(0, lambda: self.finish_callback() if self.finish_callback else None)
                        return True
                return False

        filter_obj = EditorEventFilter(editor, item, file_icon, finish_edit)
        editor.installEventFilter(filter_obj)
        # Store filter to prevent garbage collection
        editor._event_filter = filter_obj

    def _on_projects_item_edited(self, item: QTreeWidgetItem, column: int):
        """Handles when a project tree item is edited inline."""
        if column != 0:
            return

        new_name = item.text(column).strip()
        if not new_name:
            # Empty name - restore old name or delete
            old_path_str = item.data(0, PathRole)
            if old_path_str:
                old_path = Path(old_path_str)
                old_name = old_path.stem if old_path.is_file() else old_path.name
                item.setText(0, old_name)
            return

        old_path_str = item.data(0, PathRole)
        if not old_path_str:
            return

        old_path = Path(old_path_str)
        old_name = old_path.stem if old_path.is_file() else old_path.name

        if new_name != old_name:
            # Rename the file/directory
            if self.chat_history_manager.rename_item(old_path, new_name, self):
                # Update the path in the item
                new_path = old_path.with_stem(new_name) if old_path.is_file() else old_path.with_name(new_name)
                item.setData(0, PathRole, str(new_path))
                self._load_chat_history()
            else:
                # Rename failed - restore old name
                item.setText(0, old_name)

    def _on_chats_item_edited(self, item: QListWidgetItem):
        """Handles when a chat list item is edited inline."""
        # This is called when the item text is changed programmatically
        # The actual editing is handled by _edit_chat_item_inline
        pass

    def handle_edit_system_message(self, item: QTreeWidgetItem):
        """Handles the 'Edit System Message' context menu action for tree items."""
        try:
            item_path = Path(item.data(0, PathRole))
            if not item_path.is_file() or item_path.suffix != '.json':
                return

            self._edit_system_message_for_path(item_path)

        except Exception as e:
            print(f"Error editing system message: {e}")
            QMessageBox.warning(self, "Error", f"Could not edit system message: {e}")

    def handle_edit_system_message_chat(self, item: QListWidgetItem):
        """Handles the 'Edit System Message' context menu action for list items."""
        try:
            item_path = Path(item.data(PathRole))
            if not item_path.is_file() or item_path.suffix != '.json':
                return

            self._edit_system_message_for_path(item_path)

        except Exception as e:
            print(f"Error editing system message: {e}")
            QMessageBox.warning(self, "Error", f"Could not edit system message: {e}")

    def _edit_system_message_for_path(self, item_path: Path):
        """Common method to edit system message for a given path."""
        # If this is the currently loaded chat, save messageInput content first
        if self.current_chat_file_path == item_path:
            self._save_current_chat()

        # Load the chat to get current system message
        messages = self.chat_history_manager.load_chat(item_path)
        system_message = ""
        # Find system message (should be at the beginning)
        for msg in messages:
            if msg.get("role") == "system":
                system_message = msg.get("content", "")
                break

        # Get templates directory from config
        templates_dir = self.config_manager.get_system_message_templates()

        # Open dialog
        dialog = SystemMessageDialog(system_message, self, templates_directory=templates_dir)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_system_text = dialog.get_text()

            # Apply: Remove existing system messages first
            messages = [msg for msg in messages if msg.get("role") != "system"]

            # Add new system message at the beginning if not empty
            if new_system_text:
                system_msg = {"role": "system", "content": new_system_text}
                messages.insert(0, system_msg)

            # Save the updated messages
            self.chat_history_manager.save_chat(item_path, messages)

            # If this is the currently loaded chat, reload it
            if self.current_chat_file_path == item_path:
                self._load_chat_from_file(item_path)

    def handle_send_message(self):
        """Handles the 'Send' button click."""
        if not all([self.messageInput, self.modelComboBox, self.chatDisplay, self.llm_service]):
            print("Error: UI components or services not initialized.")
            return

        if not self.current_chat_file_path:
            QMessageBox.warning(self, "No Chat Selected",
                                "Please select a chat or create a new one before sending a message.")
            return

        # Check if another LLM call is in progress
        if self._llm_call_in_progress:
            QMessageBox.warning(self, "LLM Call In Progress", 
                              "Please wait for the current LLM call to complete.")
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

        # 5. Set flag and disable buttons
        self._llm_call_in_progress = True
        self._set_llm_buttons_enabled(False)
        
        # Store thinking bubble reference for callback
        self._pending_llm_thinking_bubble = thinking_bubble
        self._pending_llm_model = model

        # 6. Call the LLM service asynchronously with the current message history
        # self.current_messages was updated by _save_current_chat()
        self._llm_worker_thread = LLMWorker(self.llm_service, model, list(self.current_messages))
        self._llm_worker_thread.finished.connect(self._on_send_message_response_received)
        self._llm_worker_thread.error.connect(self._on_send_message_error)
        self._llm_worker_thread.start()
    
    def _on_send_message_response_received(self, response_content: str):
        """Handle successful LLM response for send message."""
        try:
            thinking_bubble = self._pending_llm_thinking_bubble
            model = self._pending_llm_model
            
            # Update the "thinking" bubble with the real response
            if thinking_bubble:
                # Find the QListWidgetItem for the thinking bubble
                for i in range(self.chatDisplay.count()):
                    item = self.chatDisplay.item(i)
                    widget = self.chatDisplay.itemWidget(item)
                    if widget == thinking_bubble:
                        widget.set_message("assistant", response_content, item, model)
                        break

            # Save the chat *again* with the new AI response
            self._save_current_chat()
        finally:
            # Clean up and re-enable buttons
            self._llm_call_in_progress = False
            self._set_llm_buttons_enabled(True)
            self._llm_worker_thread = None
            self._pending_llm_thinking_bubble = None
            self._pending_llm_model = None
    
    def _on_send_message_error(self, error_message: str):
        """Handle LLM error for send message."""
        try:
            thinking_bubble = self._pending_llm_thinking_bubble
            model = self._pending_llm_model
            
            if thinking_bubble:
                for i in range(self.chatDisplay.count()):
                    item = self.chatDisplay.item(i)
                    widget = self.chatDisplay.itemWidget(item)
                    if widget == thinking_bubble:
                        widget.set_message("assistant", error_message, item, model)
                        break
            # Save the error message to the chat
            self._save_current_chat()
        finally:
            # Clean up and re-enable buttons
            self._llm_call_in_progress = False
            self._set_llm_buttons_enabled(True)
            self._llm_worker_thread = None
            self._pending_llm_thinking_bubble = None
            self._pending_llm_model = None

    def _handle_cut_message(self, widget: ChatMessageWidget):
        """Handle cut action: copy to clipboard, remove from chat history, and delete widget."""
        # Wrap everything in try-except to catch any access to deleted widgets
        try:
            # Validate widget is still alive and valid
            if not widget:
                return

            # Get the list item - wrap in try-except as widget might be deleted
            try:
                list_item = widget.list_item
                if not list_item:
                    return
            except (RuntimeError, AttributeError):
                # Widget was deleted or list_item is invalid
                return

            # Find the index of this widget in the chat display
            list_widget = list_item.listWidget()
            if not list_widget:
                return

            # Get the index of this item
            item_index = list_widget.row(list_item)
            if item_index < 0:
                return

            # Disconnect all signals from the widget before deletion
            try:
                widget.editingFinished.disconnect()
            except (RuntimeError, TypeError, AttributeError):
                pass
            try:
                widget.cutRequested.disconnect()
            except (RuntimeError, TypeError, AttributeError):
                pass
            try:
                widget.regenerateRequested.disconnect()
            except (RuntimeError, TypeError, AttributeError):
                pass

            # Remove the widget from the display
            # IMPORTANT: Mark widget as deleted first to prevent signal handlers from accessing it
            try:
                widget._is_deleted = True
                widget.setParent(None)
                widget.list_item = None
            except (RuntimeError, AttributeError):
                pass

            # Remove widget from item first
            existing_item = list_widget.item(item_index)
            if existing_item:
                list_widget.removeItemWidget(existing_item)

            # Now take the item
            removed_item = list_widget.takeItem(item_index)
            if removed_item:
                del removed_item
            # Don't call deleteLater() - let Python garbage collect it naturally

            # Save the chat (which will rebuild current_messages without this message)
            self._save_current_chat()
        except Exception as e:
            # Catch any exception including segfault-like errors
            print(f"Error in _handle_cut_message: {e}")
            import traceback
            traceback.print_exc()
            return

    def _build_messages_list(self, list_widget, end_index: int, include_end: bool = True) -> list:
        """Helper to build messages list with system messages and displayed messages up to end_index."""
        messages = []
        
        # Get system messages first
        system_messages = [msg for msg in self.current_messages if msg.get("role") == "system"]
        messages.extend(system_messages)
        
        # Get all displayed messages up to and including end_index
        end = end_index + 1 if include_end else end_index
        for i in range(end):
            item = list_widget.item(i)
            if item:
                item_widget = list_widget.itemWidget(item)
                if isinstance(item_widget, ChatMessageWidget):
                    role = item_widget.role
                    if role in ("user", "assistant"):
                        try:
                            messages.append(item_widget.get_message_dict())
                        except (RuntimeError, AttributeError):
                            continue
        
        return messages
    
    def _set_llm_buttons_enabled(self, enabled: bool):
        """Enable or disable buttons that trigger LLM calls."""
        if self.sendButton:
            self.sendButton.setEnabled(enabled)
        # Disable regenerate buttons on all user message widgets
        if self.chatDisplay:
            for i in range(self.chatDisplay.count()):
                item = self.chatDisplay.item(i)
                if item:
                    widget = self.chatDisplay.itemWidget(item)
                    if isinstance(widget, ChatMessageWidget) and widget.role == "user":
                        if hasattr(widget, 'regenerate_button'):
                            widget.regenerate_button.setEnabled(enabled)
    
    def _call_llm_and_update_widget(
            self, widget: ChatMessageWidget, list_item, list_widget, messages: list, model: str
    ):
        """Helper to show thinking state, call LLM asynchronously, update widget, and handle errors."""
        # Check if another LLM call is in progress
        if self._llm_call_in_progress:
            QMessageBox.warning(self, "LLM Call In Progress", 
                              "Please wait for the current LLM call to complete.")
            return
        
        # Show "thinking" state in the existing bubble
        try:
            widget.set_message("thinking", "...", list_item)
            QApplication.processEvents()  # Update UI immediately
        except (RuntimeError, AttributeError):
            return
        
        # Set flag and disable buttons
        self._llm_call_in_progress = True
        self._set_llm_buttons_enabled(False)
        
        # Store widget references for callback
        self._pending_llm_widget = widget
        self._pending_llm_list_item = list_item
        self._pending_llm_list_widget = list_widget
        self._pending_llm_model = model
        
        # Create and start worker thread
        self._llm_worker_thread = LLMWorker(self.llm_service, model, messages)
        self._llm_worker_thread.finished.connect(self._on_llm_response_received)
        self._llm_worker_thread.error.connect(self._on_llm_error)
        self._llm_worker_thread.start()
    
    def _on_llm_response_received(self, response_content: str):
        """Handle successful LLM response."""
        try:
            widget = self._pending_llm_widget
            list_item = self._pending_llm_list_item
            list_widget = self._pending_llm_list_widget
            model = self._pending_llm_model
            
            # Replace the text in the existing bubble with the response
            try:
                widget.set_message("assistant", response_content, list_item, model)
                # Ensure editingFinished is connected for saving
                try:
                    widget.editingFinished.disconnect()
                except (RuntimeError, TypeError):
                    pass
                widget.editingFinished.connect(self._save_current_chat)
                
                # Scroll to the item to keep it in view
                list_widget.scrollToItem(list_item)
                QApplication.processEvents()  # Force UI update
                
                # Save the chat with the new response
                self._save_current_chat()
            except (RuntimeError, AttributeError) as e:
                print(f"Error updating widget: {e}")
        finally:
            # Clean up and re-enable buttons
            self._llm_call_in_progress = False
            self._set_llm_buttons_enabled(True)
            self._llm_worker_thread = None
            self._pending_llm_widget = None
            self._pending_llm_list_item = None
            self._pending_llm_list_widget = None
            self._pending_llm_model = None
    
    def _on_llm_error(self, error_message: str):
        """Handle LLM error."""
        try:
            widget = self._pending_llm_widget
            list_item = self._pending_llm_list_item
            list_widget = self._pending_llm_list_widget
            model = self._pending_llm_model
            
            try:
                widget.set_message("assistant", error_message, list_item, model)
                list_widget.scrollToItem(list_item)
                QApplication.processEvents()
                self._save_current_chat()
            except (RuntimeError, AttributeError):
                pass
        finally:
            # Clean up and re-enable buttons
            self._llm_call_in_progress = False
            self._set_llm_buttons_enabled(True)
            self._llm_worker_thread = None
            self._pending_llm_widget = None
            self._pending_llm_list_item = None
            self._pending_llm_list_widget = None
            self._pending_llm_model = None

    def _handle_regenerate_message(self, widget: ChatMessageWidget):
        """Handle regenerate for assistant message: show refine dialog and refine/regenerate."""
        try:
            # Validate widget is still alive and valid
            if not widget or widget.role != "assistant":
                return

            # Get the list item - wrap in try-except as widget might be deleted
            try:
                list_item = widget.list_item
                if not list_item:
                    return
            except (RuntimeError, AttributeError):
                return

            if not self.current_chat_file_path:
                QMessageBox.warning(self, "No Chat Selected", "Cannot refine: no active chat.")
                return

            if not self.llm_service or not self.modelComboBox:
                QMessageBox.warning(self, "Error", "LLM service or model selector not available.")
                return

            # Get refine prompt from config
            refine_prompt = self.config_manager.get_refine_prompt()

            # Show refine dialog
            dialog = RefineDialog(refine_prompt=refine_prompt, parent=self)
            # Disable refine button if LLM call is in progress
            if self._llm_call_in_progress:
                dialog.set_refine_button_enabled(False)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                # User cancelled
                return
            
            # Check again if LLM call started while dialog was open
            if self._llm_call_in_progress:
                QMessageBox.warning(self, "LLM Call In Progress", 
                                  "Please wait for the current LLM call to complete.")
                return

            # Get user input from dialog
            user_input = dialog.get_text()

            # Get the model to use from the combo box (user may have changed it)
            # This allows user to regenerate with a different model than the original
            model = self.modelComboBox.currentText()

            # Find the list widget and get the index
            list_widget = list_item.listWidget()
            if not list_widget:
                return

            assistant_index = list_widget.row(list_item)
            if assistant_index < 0:
                return

            # Build messages based on whether user input is empty
            if not user_input:
                # Empty input: regenerate - take chat history up to and including the last user message
                # Find the last user message before this assistant message
                last_user_index = -1
                for i in range(assistant_index - 1, -1, -1):
                    item = list_widget.item(i)
                    if item:
                        item_widget = list_widget.itemWidget(item)
                        if isinstance(item_widget, ChatMessageWidget) and item_widget.role == "user":
                            last_user_index = i
                            break
                
                messages_to_send = self._build_messages_list(list_widget, last_user_index, include_end=True)
            else:
                # Has user input: refine - duplicate chat history up to and including this assistant message
                messages_to_send = self._build_messages_list(list_widget, assistant_index, include_end=True)
                
                # Add the refining user message at the end
                refine_message = f"{refine_prompt}\n\n{user_input}"
                messages_to_send.append({"role": "user", "content": refine_message})

            # Call LLM and update widget
            self._call_llm_and_update_widget(widget, list_item, list_widget, messages_to_send, model)
        except Exception as e:
            # Catch any exception including segfault-like errors
            print(f"Error in _handle_regenerate_message: {e}")
            import traceback
            traceback.print_exc()
            return

    def _on_cut_requested(self):
        """Slot for cutRequested signal - finds widget by sender to avoid capturing references."""
        try:
            sender = self.sender()
            if sender and isinstance(sender, ChatMessageWidget):
                # Check if widget is marked as deleted
                if sender.is_deleted():
                    return
                self._handle_cut_message(sender)
        except (RuntimeError, AttributeError):
            # Widget was deleted
            return

    def _on_regenerate_requested(self):
        """Slot for regenerateRequested signal - finds widget by sender to avoid capturing references."""
        try:
            sender = self.sender()
            if sender and isinstance(sender, ChatMessageWidget):
                # Check if widget is marked as deleted
                if sender.is_deleted():
                    return
                self._handle_regenerate_message(sender)
        except (RuntimeError, AttributeError):
            # Widget was deleted
            return

    def _get_widget_info(self, widget: ChatMessageWidget, expected_role: str = None):
        """
        Helper to extract widget information: list_item, list_widget, and index.
        Returns (list_item, list_widget, index) or (None, None, -1) if invalid.
        """
        if not widget:
            return None, None, -1
        
        if expected_role and widget.role != expected_role:
            return None, None, -1
        
        try:
            list_item = widget.list_item
            if not list_item:
                return None, None, -1
        except (RuntimeError, AttributeError):
            return None, None, -1
        
        list_widget = list_item.listWidget()
        if not list_widget:
            return None, None, -1
        
        index = list_widget.row(list_item)
        if index < 0:
            return None, None, -1
        
        return list_item, list_widget, index

    def _handle_cut_pair(self, widget: ChatMessageWidget):
        """Handle cut pair: remove user message and next assistant message."""
        try:
            list_item, list_widget, user_index = self._get_widget_info(widget, "user")
            if list_item is None:
                return

            # Find the next assistant message
            assistant_item = None
            assistant_index = -1
            for i in range(user_index + 1, list_widget.count()):
                item = list_widget.item(i)
                if item:
                    item_widget = list_widget.itemWidget(item)
                    if isinstance(item_widget, ChatMessageWidget):
                        if item_widget.role == "assistant":
                            # assistant_item = item
                            assistant_index = i
                            break

            # Remove both messages (start from higher index to avoid index shifting)
            if assistant_index >= 0:
                # Remove assistant message first
                self._remove_message_at_index(list_widget, assistant_index)

            # Remove user message
            self._remove_message_at_index(list_widget, user_index)

            # Save the chat
            self._save_current_chat()
        except Exception as e:
            print(f"Error in _handle_cut_pair: {e}")
            import traceback
            traceback.print_exc()

    def _handle_cut_below(self, widget: ChatMessageWidget):
        """Handle cut below: remove this message and all messages below it."""
        try:
            if not widget:
                return

            try:
                list_item = widget.list_item
                if not list_item:
                    return
            except (RuntimeError, AttributeError):
                return

            list_widget = list_item.listWidget()
            if not list_widget:
                return

            start_index = list_widget.row(list_item)
            if start_index < 0:
                return

            # Remove all messages from start_index to the end
            # Remove from end to start to avoid index shifting
            count = list_widget.count()
            for i in range(count - 1, start_index - 1, -1):
                self._remove_message_at_index(list_widget, i)

            # Save the chat
            self._save_current_chat()
        except Exception as e:
            print(f"Error in _handle_cut_below: {e}")
            import traceback
            traceback.print_exc()

    def _handle_regenerate_user_message(self, widget: ChatMessageWidget):
        """Handle regenerate for user message: regenerate the next assistant message."""
        try:
            list_item, list_widget, user_index = self._get_widget_info(widget, "user")
            if list_item is None:
                return

            # Find the next assistant message
            assistant_item = None
            assistant_index = -1
            assistant_widget = None
            for i in range(user_index + 1, list_widget.count()):
                item = list_widget.item(i)
                if item:
                    item_widget = list_widget.itemWidget(item)
                    if isinstance(item_widget, ChatMessageWidget):
                        if item_widget.role == "assistant":
                            assistant_item = item
                            assistant_index = i
                            assistant_widget = item_widget
                            break

            if assistant_index < 0 or not assistant_widget:
                # No assistant message found, can't regenerate
                return

            # Get the model to use
            try:
                model = assistant_widget.model if assistant_widget.model else self.modelComboBox.currentText()
            except (RuntimeError, AttributeError):
                model = self.modelComboBox.currentText()

            # Build message history up to and including the user message
            messages_before = self._build_messages_list(list_widget, user_index, include_end=True)

            # Call LLM and update widget
            self._call_llm_and_update_widget(assistant_widget, assistant_item, list_widget, messages_before, model)
        except Exception as e:
            print(f"Error in _handle_regenerate_user_message: {e}")
            import traceback
            traceback.print_exc()

    @classmethod
    def _remove_message_at_index(cls, list_widget, index: int):
        """Helper method to safely remove a message at a given index."""
        try:
            item = list_widget.item(index)
            if not item:
                return

            widget = list_widget.itemWidget(item)
            if isinstance(widget, ChatMessageWidget):
                # Disconnect all signals
                try:
                    widget.editingFinished.disconnect()
                    widget.cutRequested.disconnect()
                    widget.cutPairRequested.disconnect()
                    widget.cutBelowRequested.disconnect()
                    widget.regenerateRequested.disconnect()
                    widget.regenerateUserRequested.disconnect()
                except (RuntimeError, TypeError, AttributeError):
                    pass

                # Mark as deleted
                try:
                    widget._is_deleted = True
                    widget.setParent(None)
                    widget.list_item = None
                except (RuntimeError, AttributeError):
                    pass

            # Remove widget from item
            list_widget.removeItemWidget(item)

            # Take the item
            removed_item = list_widget.takeItem(index)
            if removed_item:
                del removed_item
        except Exception as e:
            print(f"Error removing message at index {index}: {e}")

    def _on_cut_pair_requested(self):
        """Slot for cutPairRequested signal - cut user message and next assistant message."""
        try:
            sender = self.sender()
            if sender and isinstance(sender, ChatMessageWidget):
                if sender.is_deleted():
                    return
                self._handle_cut_pair(sender)
        except (RuntimeError, AttributeError):
            return

    def _on_cut_below_requested(self):
        """Slot for cutBelowRequested signal - cut this message and all below."""
        try:
            sender = self.sender()
            if sender and isinstance(sender, ChatMessageWidget):
                if sender.is_deleted():
                    return
                self._handle_cut_below(sender)
        except (RuntimeError, AttributeError):
            return

    def _on_message_focused(self, role: str, model: str):
        """Handle message focus - update modelComboBox for assistant messages."""
        if role == "assistant" and self.modelComboBox:
            # Get the widget that emitted the signal
            widget = self.sender()
            if isinstance(widget, ChatMessageWidget):
                # Only update if this is a different widget than the one currently focused
                # This prevents resetting the combo box when user is changing it
                if widget != self._focused_assistant_widget:
                    self._focused_assistant_widget = widget
                    if model:
                        # Find the model in the combo box and set it as current
                        index = self.modelComboBox.findText(model)
                        if index >= 0:
                            self.modelComboBox.setCurrentIndex(index)

    def _on_regenerate_user_requested(self):
        """Slot for regenerateUserRequested signal - regenerate next assistant message."""
        try:
            sender = self.sender()
            if sender and isinstance(sender, ChatMessageWidget):
                if sender.is_deleted():
                    return
                self._handle_regenerate_user_message(sender)
        except (RuntimeError, AttributeError):
            return

    def _create_drag_pixmap_and_exec(self, widget, item, file_path_str: str, display_name: str, 
                                      icon, supported_actions):
        """
        Helper to create custom drag pixmap and execute drag operation.
        
        Args:
            widget: The source widget (chatsList or projectsTree)
            item: The item being dragged
            file_path_str: File path to include in mime data
            display_name: Text to display in drag pixmap
            icon: Icon to display in drag pixmap
            supported_actions: Supported drag actions
        """
        from PySide6.QtGui import QDrag, QPixmap, QPainter
        
        # Get font from the widget
        font = widget.font()
        font_metrics = QFontMetrics(font)
        
        # Calculate size needed
        icon_size = 16  # Standard icon size for drag
        text_width = font_metrics.horizontalAdvance(display_name)
        text_height = font_metrics.height()
        padding = 4
        total_width = icon_size + padding + text_width + padding * 2
        total_height = max(icon_size, text_height) + padding * 2
        
        # Create pixmap
        pixmap = QPixmap(total_width, total_height)
        pixmap.fill(Qt.GlobalColor.transparent)  # Transparent background
        
        # Draw icon and text
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(font)
        
        # Draw icon
        if not icon.isNull():
            icon_pixmap = icon.pixmap(icon_size, icon_size)
            painter.drawPixmap(padding, (total_height - icon_size) // 2, icon_pixmap)
        
        # Draw text in white color
        painter.setPen(Qt.GlobalColor.white)
        text_x = padding + icon_size + padding
        text_y = (total_height + font_metrics.ascent() - font_metrics.descent()) // 2
        painter.drawText(text_x, text_y, display_name)
        painter.end()
        
        # Create mime data with file path
        mime_data = QMimeData()
        mime_data.setText(file_path_str)
        
        # Create drag object
        drag = QDrag(widget)
        drag.setMimeData(mime_data)
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(padding, padding))  # Set hot spot to top-left of icon
        drag.exec(supported_actions, Qt.DropAction.MoveAction)

    def _chats_list_start_drag(self, supported_actions):
        """Override startDrag for chatsList to provide file path in mime data and custom drag pixmap."""
        selected_items = self.chatsList.selectedItems()
        if not selected_items:
            # Call original startDrag if no selection
            QListWidget.startDrag(self.chatsList, supported_actions)
            return

        item = selected_items[0]
        file_path_str = item.data(PathRole)
        if not file_path_str:
            QListWidget.startDrag(self.chatsList, supported_actions)
            return

        # Get display name and icon
        display_name = item.text()
        icon = item.icon()
        
        # Create drag pixmap and execute
        self._create_drag_pixmap_and_exec(
            self.chatsList, item, file_path_str, display_name, icon, supported_actions
        )

    def _projects_tree_start_drag(self, supported_actions):
        """
        Override startDrag for projectsTree to provide file/directory path in mime data and custom drag pixmap
        (for both chat files and project directories).
        """
        selected_items = self.projectsTree.selectedItems()
        if not selected_items:
            # Call original startDrag if no selection
            QTreeWidget.startDrag(self.projectsTree, supported_actions)
            return

        item = selected_items[0]
        path_str = item.data(0, PathRole)
        if not path_str:
            QTreeWidget.startDrag(self.projectsTree, supported_actions)
            return

        path = Path(path_str)
        # Allow dragging both files and directories
        if not path.exists():
            return

        # Get display name and icon
        display_name = item.text(0)
        icon = item.icon(0)
        
        # Create drag pixmap and execute
        self._create_drag_pixmap_and_exec(
            self.projectsTree, item, path_str, display_name, icon, supported_actions
        )

    def _move_chat_file(self, source_path: Path, target_dir: Path, event: QDropEvent = None) -> Path | None:
        """
        Helper to move a chat file from source_path to target_dir.
        Returns the target_path if successful, None otherwise.
        If event is provided, will call event.ignore() on errors.
        """
        target_path = target_dir / source_path.name
        if target_path.exists():
            error_msg = f"A file with this name already exists in the target location."
            QMessageBox.warning(self, "Move Error", error_msg)
            if event:
                event.ignore()
            return None
        
        # Save current chat if it's the one being moved
        if self.current_chat_file_path == source_path:
            self._save_current_chat()
        
        # Move the file
        import shutil
        shutil.move(str(source_path), str(target_path))
        
        # Update current_chat_file_path if it was the moved file
        if self.current_chat_file_path == source_path:
            self.current_chat_file_path = target_path
        
        # Reload the UI
        self._load_chat_history()
        
        return target_path

    def _move_project_directory(self, source_path: Path, target_dir: Path, event: QDropEvent = None) -> Path | None:
        """
        Helper to move a project directory from source_path to target_dir.
        All contents (subdirectories and files) will be moved with it.
        Returns the target_path if successful, None otherwise.
        If event is provided, will call event.ignore() on errors.
        """
        target_path = target_dir / source_path.name
        if target_path.exists():
            error_msg = f"A directory with this name already exists in the target location."
            QMessageBox.warning(self, "Move Error", error_msg)
            if event:
                event.ignore()
            return None
        
        # Save current chat if it's inside the directory being moved
        if self.current_chat_file_path and self.current_chat_file_path.is_relative_to(source_path):
            self._save_current_chat()
        
        # Move the directory (shutil.move handles recursive moves)
        import shutil
        shutil.move(str(source_path), str(target_path))
        
        # Update current_chat_file_path if it was inside the moved directory
        if self.current_chat_file_path and self.current_chat_file_path.is_relative_to(source_path):
            # Recalculate the path relative to the new location
            relative_path = self.current_chat_file_path.relative_to(source_path)
            self.current_chat_file_path = target_path / relative_path
        
        # Reload the UI
        self._load_chat_history()
        
        return target_path

    def _chats_list_drag_enter_event(self, event: QDragEnterEvent):
        """Handle drag enter event for chats list."""
        if event.mimeData().hasText():
            # Check if the drag is from projectsTree (allow moving from projects to chats)
            source = event.source()
            if source == self.projectsTree:
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def _chats_list_drag_move_event(self, event: QDragMoveEvent):
        """Handle drag move event for chats list."""
        if event.mimeData().hasText():
            source = event.source()
            if source == self.projectsTree:
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def _chats_list_drop_event(self, event: QDropEvent):
        """Handle drop event for chats list - move chat files or project directories from projects to top-level."""
        if not event.mimeData().hasText():
            event.ignore()
            return

        source = event.source()
        if source != self.projectsTree:
            event.ignore()
            return

        # Get the source path from mime data
        source_path_str = event.mimeData().text()
        if not source_path_str:
            event.ignore()
            return

        source_path = Path(source_path_str)
        if not source_path.exists():
            event.ignore()
            return

        # Target is always the history root (top-level)
        target_dir = self.chat_history_manager.history_root

        # Don't move if source and target are the same
        if source_path.parent == target_dir:
            event.ignore()
            return

        # Move the file or directory
        try:
            if source_path.is_file():
                target_path = self._move_chat_file(source_path, target_dir, event)
                if target_path:
                    # Select the moved item in the chats list
                    for i in range(self.chatsList.count()):
                        item = self.chatsList.item(i)
                        if item and item.data(PathRole) == str(target_path):
                            self.chatsList.setCurrentItem(item)
                            self.chatsList.scrollToItem(item)
                            break
            else:
                # Move directory to top-level
                target_path = self._move_project_directory(source_path, target_dir, event)
                if target_path:
                    # Select the moved item in the projects tree
                    self._select_item_by_path(target_path)
            
            if target_path:
                event.acceptProposedAction()
        except Exception as e:
            QMessageBox.warning(self, "Move Error", f"Could not move: {e}")
            event.ignore()

    def _projects_tree_drag_enter_event(self, event: QDragEnterEvent):
        """Handle drag enter event for projects tree."""
        if event.mimeData().hasText():
            # Check if the drag is from chatsList or projectsTree
            source = event.source()
            if source == self.chatsList or source == self.projectsTree:
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def _projects_tree_drag_move_event(self, event: QDragMoveEvent):
        """Handle drag move event for projects tree."""
        if event.mimeData().hasText():
            source = event.source()
            if source == self.chatsList or source == self.projectsTree:
                # Get source path from mime data
                source_path_str = event.mimeData().text()
                if source_path_str:
                    source_path = Path(source_path_str)
                    
                    # Check if dropping on a valid target (project folder or tree root)
                    drop_pos = event.position().toPoint()
                    item = self.projectsTree.itemAt(drop_pos)
                    
                    # Check if dropping on the source item itself - treat as empty space
                    if item:
                        item_path_str = item.data(0, PathRole)
                        if item_path_str and Path(item_path_str) == source_path:
                            # Dropping on source item - allow (will be treated as empty space in drop event)
                            event.acceptProposedAction()
                            return
                    
                    # Only treat as dropping into an item if the drop position is within the item's visual rectangle
                    if item:
                        item_rect = self.projectsTree.visualItemRect(item)
                        if item_rect.contains(drop_pos):
                            # Check if it's a folder (project) or file (chat)
                            item_path_str = item.data(0, PathRole)
                            if item_path_str:
                                item_path = Path(item_path_str)
                                if item_path.is_dir():
                                    # Prevent dropping a directory into itself or its descendants
                                    if source_path.is_dir():
                                        # Check if target is the same as source
                                        if item_path == source_path:
                                            event.ignore()
                                            return
                                        
                                        # Check if target is a descendant of source (target is inside source)
                                        try:
                                            item_path.relative_to(source_path)
                                            # If we get here, target is inside source - disallow
                                            event.ignore()
                                            return
                                        except ValueError:
                                            # target is not inside source - this is fine
                                            pass
                                        
                                        # Check if source is inside target (source is a subdirectory of target)
                                        try:
                                            source_path.relative_to(item_path)
                                            # If we get here, source is inside target
                                            # This is fine if they're siblings or if target is not a descendant of source
                                            if item_path.parent == source_path.parent:
                                                # They're siblings - allow
                                                event.acceptProposedAction()
                                                return
                                            elif item_path == source_path.parent:
                                                # target is the parent - allow (no-op case, but allow for visual feedback)
                                                event.acceptProposedAction()
                                                return
                                            else:
                                                # Check if target is a descendant of source (would create a loop)
                                                try:
                                                    item_path.relative_to(source_path)
                                                    # This shouldn't happen since we already checked above
                                                    event.ignore()
                                                    return
                                                except ValueError:
                                                    # target is not a descendant of source, so this is a valid move
                                                    event.acceptProposedAction()
                                                    return
                                        except ValueError:
                                            # source is not inside target - they're completely separate, which is fine
                                            pass
                                    # Dropping on a project folder - allow
                                    event.acceptProposedAction()
                                    return
                    
                    # Dropping on empty area (tree root) - always allow (drop event will handle validation)
                    event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def _projects_tree_drop_event(self, event: QDropEvent):
        """Handle drop event for projects tree - move chat files or project directories."""
        if not event.mimeData().hasText():
            event.ignore()
            return

        source = event.source()
        if source != self.chatsList and source != self.projectsTree:
            event.ignore()
            return

        # Get the source path from mime data
        source_path_str = event.mimeData().text()
        if not source_path_str:
            event.ignore()
            return

        source_path = Path(source_path_str)
        if not source_path.exists():
            event.ignore()
            return

        # Get the target (where to drop)
        drop_pos = event.position().toPoint()
        item = self.projectsTree.itemAt(drop_pos)
        target_dir = self.chat_history_manager.history_root  # Default to root

        # Check if dropping on the source item itself - treat as empty space (no-op)
        if item:
            item_path_str = item.data(0, PathRole)
            if item_path_str:
                item_path = Path(item_path_str)
                # If dropping on the source item itself, ignore (no-op)
                if item_path == source_path:
                    event.ignore()
                    return
                
                # Determine target directory based on what we're dropping on
                item_rect = self.projectsTree.visualItemRect(item)
                # Only treat as dropping into an item if the drop position is clearly within the item's rectangle
                if item_rect.contains(drop_pos):
                    if item_path.is_dir():
                        # Dropping on a project folder
                        target_dir = item_path
                    elif item_path.is_file():
                        # Dropping on a chat file - use its parent directory
                        target_dir = item_path.parent
                # If drop position is outside item rect, target_dir remains as root (empty space)
        # If no item, target_dir is already root (empty space)

        # Don't move if source and target are the same
        if source_path.parent == target_dir:
            event.ignore()
            return

        # Prevent moving a directory into itself or its descendants
        if source_path.is_dir():
            # Check if target is the same as source
            if target_dir == source_path:
                QMessageBox.warning(self, "Move Error", "Cannot move a directory into itself.")
                event.ignore()
                return
            
            # Check if target is a descendant of source (target is inside source)
            try:
                target_dir.relative_to(source_path)
                # If we get here, target is inside source - disallow
                QMessageBox.warning(self, "Move Error", "Cannot move a directory into itself or its subdirectories.")
                event.ignore()
                return
            except ValueError:
                # target is not inside source - this is fine
                pass
            
            # Check if source is inside target (source is a subdirectory of target)
            # This is only a problem if we're trying to move source into a nested subdirectory of itself
            try:
                source_path.relative_to(target_dir)
                # If we get here, source is inside target
                # This is fine if:
                # 1. target_dir is the direct parent of source_path (moving up one level - already checked above)
                # 2. They're siblings (same parent) - moving between siblings is fine
                # 3. target_dir is a completely separate branch (not a descendant of source)
                
                # Check if they're siblings
                if target_dir.parent == source_path.parent:
                    # They're siblings - this is fine
                    pass
                elif target_dir == source_path.parent:
                    # target is the parent - this is fine (no-op case already handled above)
                    pass
                else:
                    # source is inside target, but target is not a sibling or parent
                    # This means we're trying to move into a nested subdirectory
                    # Check if target is a descendant of source (would create a loop)
                    try:
                        target_dir.relative_to(source_path)
                        # This shouldn't happen since we already checked above, but just in case
                        QMessageBox.warning(self, "Move Error", "Cannot move a directory into itself or its subdirectories.")
                        event.ignore()
                        return
                    except ValueError:
                        # target is not a descendant of source, so this is a valid move
                        # (e.g., moving "xxxx" from root into "New Project 1/abcdefg" when "abcdefg" is not inside "xxxx")
                        pass
            except ValueError:
                # source is not inside target - they're completely separate, which is fine
                pass

        # Move the file or directory
        try:
            if source_path.is_file():
                target_path = self._move_chat_file(source_path, target_dir, event)
            else:
                # Move directory
                target_path = self._move_project_directory(source_path, target_dir, event)
            
            if target_path:
                # Select the moved item in the projects tree
                self._select_item_by_path(target_path)
                event.acceptProposedAction()
        except Exception as e:
            QMessageBox.warning(self, "Move Error", f"Could not move: {e}")
            event.ignore()

    def _select_item_by_path(self, file_path: Path):
        """Select an item in the projects tree by its file path."""

        def find_item_recursive(item: QTreeWidgetItem, target_path: Path) -> QTreeWidgetItem | None:
            item_path_str = item.data(0, PathRole)
            if item_path_str:
                item_path = Path(item_path_str)
                if item_path == target_path:
                    return item
            # Check children
            for i in range(item.childCount()):
                child = item.child(i)
                found = find_item_recursive(child, target_path)
                if found:
                    return found
            return None

        # Search through all top-level items
        for i in range(self.projectsTree.topLevelItemCount()):
            top_item = self.projectsTree.topLevelItem(i)
            found = find_item_recursive(top_item, file_path)
            if found:
                self.projectsTree.setCurrentItem(found)
                self.projectsTree.scrollToItem(found)
                break


def setup_logging(config_manager):
    """Setup logging based on configuration."""
    log_level_str = config_manager.get_log_level()

    # Map string level to logging constant
    level_map = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR
    }
    log_level = level_map.get(log_level_str, logging.WARNING)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized at level: {log_level_str.upper()}")


### Main execution block
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Load configuration first (before setting up logging to avoid circular dependency)
    # We'll use print here since logging isn't set up yet
    print("Loading configuration...")
    config_manager = ConfigManager()

    # Now set up logging based on config
    setup_logging(config_manager)
    logger = logging.getLogger(__name__)

    keys_file_str = config_manager.get_keys_file_path()
    chat_history_root_str = config_manager.get_chat_history_root()
    providers = config_manager.get_providers()
    logger.info(f"Properties file loaded: {config_manager.config_file}")
    logger.info(f"Keys file path: {keys_file_str}")
    logger.info(f"Chat history root: {chat_history_root_str}")
    logger.info(f"Providers: {providers}")

    keys_file_path = Path(keys_file_str)
    chat_history_path = Path(chat_history_root_str)

    # Check if keys_file is inside chat_history_root (security check)
    keys_file_resolved = keys_file_path.resolve()
    chat_history_resolved = chat_history_path.resolve()

    try:
        # Check if keys_file is within chat_history_root
        keys_file_relative = keys_file_resolved.relative_to(chat_history_resolved)
        # If we get here without exception, keys_file is inside chat_history_root
        logger.error(f"keys_file ({keys_file_resolved}) is inside chat_history_root ({chat_history_resolved})")
        logger.error(
            "This is not allowed for security reasons. Please configure keys_file outside of chat_history_root.")
        sys.exit(1)
    except ValueError:
        # ValueError means keys_file is NOT inside chat_history_root, which is good
        pass

    key_manager = KeyManager(keys_file_path, providers)
    chat_history_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Chat history root initialized at: {chat_history_path.resolve()}")
    chat_history_manager = ChatHistoryManager(chat_history_path)

    logger.info("Managers injected into MainWindow.")
    window = MainWindow(config_manager, key_manager, chat_history_manager)
    window.show()
    sys.exit(app.exec())
