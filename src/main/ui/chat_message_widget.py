from PySide6.QtCore import Qt, QSize, Signal, QEvent, QTimer, QPoint
from PySide6.QtGui import QFontMetrics, QMouseEvent, QCursor, QTextBlockFormat, QTextCursor
from PySide6.QtWidgets import (
    QWidget, QListWidgetItem, QTextEdit, QPushButton,
    QHBoxLayout, QApplication, QGraphicsOpacityEffect, QMenu, QBoxLayout
)

import markdown
import markdown.extensions.nl2br

from spell_check_text_edit import SpellCheckTextEdit

# Import the compiled UI class
try:
    from ui_chat_message_widget import Ui_ChatMessageWidget
except ImportError:
    print("Error: Could not import ui_chat_message_widget.py.")


    class Ui_ChatMessageWidget:
        def setupUi(self, widget): pass

        def __getattr__(self, name): return None


class ChatMessageWidget(QWidget):
    MIN_BUBBLE_WIDTH = 250
    MAX_BUBBLE_RATIO = 0.9
    BUBBLE_PADDING = 8

    editingFinished = Signal()
    # Signals for button actions
    copyRequested = Signal()
    cutRequested = Signal()
    cutPairRequested = Signal()  # Cut this user message and next assistant message
    cutBelowRequested = Signal()  # Cut this message and all below
    forkRequested = Signal()
    regenerateRequested = Signal()  # For assistant messages
    regenerateUserRequested = Signal()  # For user messages - regenerate next assistant
    focused = Signal(str, str)  # Emitted when widget gets focus: (role, model)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_ChatMessageWidget()
        self.ui.setupUi(self)
        self.list_item = None
        self.role = "user"
        self.model = None  # Store the model name for assistant messages
        self._is_deleted = False  # Flag to track if widget is being deleted
        self._regenerate_handler = None  # Store the current regenerate button handler
        
        # Store opacity effects for buttons (public access through method)
        self._button_opacity_effects = {}  # Maps button -> QGraphicsOpacityEffect
        
        # Resize state
        self._is_resizing = False
        self._resize_start_pos = QPoint()
        self._resize_start_size = QSize()
        self._custom_width = None  # Custom width set by user (None = auto)
        self._custom_height = None  # Custom height set by user (None = auto)
        self._resize_moved = False  # Track drag vs click on resize button
        
        # Display mode for assistant messages: "rendered" (default) or "raw"
        self._display_mode = "rendered"  # "rendered" or "raw"
        self._raw_content = ""  # Store raw content for mode switching
        
        # Animation timer for thinking indicator
        self._thinking_timer = QTimer(self)
        self._thinking_timer.timeout.connect(self._update_thinking_animation)
        self._thinking_dot_count = 1
        self._thinking_direction = 1  # 1 = increasing, -1 = decreasing
        
        # Create button container and buttons (including resize button)
        self._create_action_buttons()

        # Replace messageContent with spell-checking version if it's a QTextEdit
        if self.ui.messageContent and isinstance(self.ui.messageContent, QTextEdit):
            self._replace_message_content_with_spell_check()

        if self.ui.messageContent:
            self.ui.messageContent.installEventFilter(self)
        
        # Enable mouse tracking for resize handle
        self.setMouseTracking(True)
    
    def is_deleted(self) -> bool:
        """Public method to check if the widget is marked for deletion."""
        return self._is_deleted
    
    def _create_action_buttons(self):
        """Create action buttons (fork, copy, cut, regenerate) in the lower right."""
        # Create a container widget for buttons positioned absolutely
        self.button_container = QWidget(self)
        self.button_container.setObjectName("buttonContainer")
        self.button_container.setStyleSheet("background-color: transparent;")
        # Set a fixed size for the container - will be updated based on visible buttons
        # Max: 4 buttons * 24px + 3 spacing * 2px = 102px width, 24px height
        # Min: 1 button * 24px = 24px width (for assistant messages)
        self.button_container.setFixedSize(102, 24)
        self.button_container.raise_()  # Raise above other widgets
        
        # Create horizontal layout for buttons
        button_layout = QHBoxLayout(self.button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(2)
        
        # Create resize button as a separate widget (will be positioned based on role)
        self.resize_button = QPushButton("↘️", self)  # Parent is self, not button_container
        self.resize_button.setObjectName("resizeButton")
        self.resize_button.setToolTip("Resize bubble")
        self.resize_button.setFixedSize(24, 24)
        # Use opacity to make the entire button (including emoji) translucent
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0.5)  # 50% opacity
        self.resize_button.setGraphicsEffect(opacity_effect)
        self._button_opacity_effects[self.resize_button] = opacity_effect
        self.resize_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(102, 102, 102, 0.5);
                border-radius: 4px;
                color: white;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.8);
                border: 1px solid #666;
                color: white;
            }
        """)
        self.resize_button.pressed.connect(self._on_resize_pressed)
        self.resize_button.released.connect(self._on_resize_released)
        self.resize_button.hide()  # Initially hidden, shown based on role
        
        # Create buttons with text labels (we'll use simple text for now, can be replaced with icons)
        self.fork_button = QPushButton("🔀", self.button_container)
        self.fork_button.setObjectName("forkButton")
        self.fork_button.setToolTip("Fork chat (create new chat with history up to this message)")
        self.fork_button.setFixedSize(24, 24)
        # Use opacity to make the entire button (including emoji) translucent
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0.5)  # 50% opacity
        self.fork_button.setGraphicsEffect(opacity_effect)
        self._button_opacity_effects[self.fork_button] = opacity_effect
        self.fork_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(102, 102, 102, 0.5);
                border-radius: 4px;
                color: white;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.8);
                border: 1px solid #666;
                color: white;
            }
        """)
        self.fork_button.clicked.connect(self.forkRequested.emit)
        self.fork_button.setEnabled(True)  # Enabled - fork functionality implemented
        
        self.copy_button = QPushButton("📋", self.button_container)
        self.copy_button.setObjectName("copyButton")
        self.copy_button.setToolTip("Copy to clipboard")
        self.copy_button.setFixedSize(24, 24)
        # Use opacity to make the entire button (including emoji) translucent
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0.5)  # 50% opacity
        self.copy_button.setGraphicsEffect(opacity_effect)
        self._button_opacity_effects[self.copy_button] = opacity_effect
        self.copy_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(102, 102, 102, 0.5);
                border-radius: 4px;
                color: white;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.8);
                border: 1px solid #666;
                color: white;
            }
        """)
        self.copy_button.clicked.connect(self._on_copy_clicked)
        
        self.cut_button = QPushButton("✂️", self.button_container)
        self.cut_button.setObjectName("cutButton")
        self.cut_button.setToolTip("Cut (copy and remove)")
        self.cut_button.setFixedSize(24, 24)
        # Use opacity to make the entire button (including emoji) translucent
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0.5)  # 50% opacity
        self.cut_button.setGraphicsEffect(opacity_effect)
        self._button_opacity_effects[self.cut_button] = opacity_effect
        self.cut_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(102, 102, 102, 0.5);
                border-radius: 4px;
                color: white;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.8);
                border: 1px solid #666;
                color: white;
            }
        """)
        self.cut_button.clicked.connect(self._on_cut_clicked)
        
        # Create regenerate button for both user and assistant (shown/hidden based on role)
        self.regenerate_button = QPushButton("🔄", self.button_container)
        self.regenerate_button.setObjectName("regenerateButton")
        self.regenerate_button.setToolTip("Regenerate response")
        self.regenerate_button.setFixedSize(24, 24)
        # Use opacity to make the entire button (including emoji) translucent
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0.5)  # 50% opacity
        self.regenerate_button.setGraphicsEffect(opacity_effect)
        self._button_opacity_effects[self.regenerate_button] = opacity_effect
        self.regenerate_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(102, 102, 102, 0.5);
                border-radius: 4px;
                color: white;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.8);
                border: 1px solid #666;
                color: white;
            }
        """)
        self.regenerate_button.installEventFilter(self)
        
        # Create mode toggle button for assistant messages (pencil for rendered, eye for raw)
        self.mode_toggle_button = QPushButton("✏️", self.button_container)
        self.mode_toggle_button.setObjectName("modeToggleButton")
        self.mode_toggle_button.setToolTip("Switch to raw text mode")
        self.mode_toggle_button.setFixedSize(24, 24)
        # Use opacity to make the entire button (including emoji) translucent
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0.5)  # 50% opacity
        self.mode_toggle_button.setGraphicsEffect(opacity_effect)
        self._button_opacity_effects[self.mode_toggle_button] = opacity_effect
        self.mode_toggle_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(102, 102, 102, 0.5);
                border-radius: 4px;
                color: white;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.8);
                border: 1px solid #666;
                color: white;
            }
        """)
        self.mode_toggle_button.installEventFilter(self)
        self.mode_toggle_button.clicked.connect(self._on_mode_toggle_clicked)
        self.mode_toggle_button.setVisible(False)  # Hidden by default, shown for assistant messages
        
        # Add buttons to layout - resize button is separate for user messages
        # For now, add all buttons except resize (it's separate for user messages)
        button_layout.addWidget(self.fork_button)
        button_layout.addWidget(self.regenerate_button)
        button_layout.addWidget(self.copy_button)
        button_layout.addWidget(self.cut_button)
        
        # Initially hide buttons (show on hover)
        self.button_container.hide()
        
        # Show buttons on hover
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)  # Enable hover events
        if self.ui.messageContent:
            self.ui.messageContent.setMouseTracking(True)
        
        # Also track mouse on button container to keep buttons visible
        self.button_container.setMouseTracking(True)
        self.button_container.installEventFilter(self)
        
        # Install event filters on buttons for hover opacity changes
        self.resize_button.installEventFilter(self)
        self.fork_button.installEventFilter(self)
        self.copy_button.installEventFilter(self)
        self.cut_button.installEventFilter(self)
        self.regenerate_button.installEventFilter(self)
        self.mode_toggle_button.installEventFilter(self)
        
        # Position buttons initially (will be repositioned on hover)
        QTimer.singleShot(100, self._position_buttons)  # Give layout time to settle
    
    def _on_copy_clicked(self):
        """Handle copy button click - copy content to clipboard."""
        content = self.get_content()
        if content:
            clipboard = QApplication.clipboard()
            clipboard.setText(content)
            self.copyRequested.emit()
    
    def _on_cut_clicked(self):
        """Handle cut button click - show menu for user messages, direct cut for assistant."""
        if self.role == "user":
            # Show menu for user messages
            menu = QMenu(self)
            menu.addAction("Cut this query-response pair", self._on_cut_pair)
            menu.addAction("Cut all contents below", self._on_cut_below)
            menu.addAction("Cancel")
            # Show menu at button position
            button_pos = self.cut_button.mapToGlobal(self.cut_button.rect().bottomLeft())
            menu.exec(button_pos)
        else:
            # For assistant messages (shouldn't happen, but handle gracefully)
            content = self.get_content()
            if content:
                clipboard = QApplication.clipboard()
                clipboard.setText(content)
                self.cutRequested.emit()
    
    def _on_cut_pair(self):
        """Handle cut pair action - copy to clipboard and emit signal."""
        content = self.get_content()
        if content:
            clipboard = QApplication.clipboard()
            clipboard.setText(content)
        self.cutPairRequested.emit()
    
    def _on_cut_below(self):
        """Handle cut below action - copy to clipboard and emit signal."""
        content = self.get_content()
        if content:
            clipboard = QApplication.clipboard()
            clipboard.setText(content)
        self.cutBelowRequested.emit()
    
    def _on_resize_pressed(self):
        """Handle resize button press - start resizing."""
        if not self.list_item or not self.ui.messageContent:
            return
        
        self._is_resizing = True
        self._resize_moved = False
        # Get current mouse position
        from PySide6.QtGui import QCursor
        self._resize_start_pos = QCursor.pos()
        
        try:
            list_widget = self.list_item.listWidget()
            if list_widget:
                # Get current bubble size
                content_rect = self.ui.messageContent.geometry()
                self._resize_start_size = QSize(content_rect.width(), content_rect.height())
        except (RuntimeError, AttributeError):
            self._is_resizing = False
            return
        
        # Grab mouse to capture all mouse events during resize
        self.grabMouse()
        # Set cursor for the entire widget during resize
        if self.role == "user":
            self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
    
    def _on_resize_released(self):
        """Handle resize button release - end resizing."""
        if self._is_resizing:
            self._is_resizing = False
            self.releaseMouse()
            # Reset cursor
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            # If no drag occurred, optimize bubble size
            if not self._resize_moved:
                self._optimize_bubble_size()
    
    def enterEvent(self, event):
        """Show buttons when mouse enters the widget."""
        super().enterEvent(event)
        if self.ui.messageContent:
            self._position_buttons()
            self.button_container.show()
            # Position resize button if it's separate (user messages)
            if self.role == "user" and self.resize_button.isVisible():
                self._position_resize_button()
                self.resize_button.show()
    
    def leaveEvent(self, event):
        """Hide buttons when mouse leaves the widget."""
        super().leaveEvent(event)
        QTimer.singleShot(100, self._check_and_hide_buttons)
    
    def _check_and_hide_buttons(self):
        """Check if mouse is still over widget or buttons, hide if not."""
        # Check if mouse is over the widget or button container
        if not self.underMouse() and not self.button_container.underMouse():
            self.button_container.hide()
            # Reset buttons to translucent when hidden
            self._set_buttons_opacity(0.5)
    
    def _set_button_opacity(self, button, opacity: float):
        """Set opacity for a button if it has a QGraphicsOpacityEffect stored."""
        if button and button in self._button_opacity_effects:
            effect = self._button_opacity_effects[button]
            if effect:
                effect.setOpacity(opacity)
    
    def _set_buttons_opacity(self, opacity: float):
        """Set opacity for all visible buttons."""
        buttons = [
            self.resize_button, self.fork_button, self.copy_button, self.cut_button, self.regenerate_button,
            self.mode_toggle_button
        ]
        for button in buttons:
            if button and button.isVisible():
                self._set_button_opacity(button, opacity)
    
    def _position_buttons(self):
        """Position buttons in the lower right of the messageContent bubble."""
        if not self.ui.messageContent:
            return
        
        # Get the messageContent position and size relative to this widget
        content_rect = self.ui.messageContent.geometry()
        
        # Position buttons in lower right corner with small padding
        button_width = self.button_container.width() if self.button_container.width() > 0 else 76
        button_height = self.button_container.height() if self.button_container.height() > 0 else 24
        padding = 4
        
        x = content_rect.right() - button_width - padding
        y = content_rect.bottom() - button_height - padding
        
        # Make sure buttons stay within widget bounds
        widget_width = self.width() if self.width() > 0 else content_rect.width()
        widget_height = self.height() if self.height() > 0 else content_rect.height()
        x = max(0, min(x, widget_width - button_width))
        y = max(0, min(y, widget_height - button_height))
        
        self.button_container.setGeometry(x, y, button_width, button_height)
        self.button_container.raise_()  # Ensure it's on top
        self.button_container.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)  # Make sure it can receive mouse events
    
    def _position_resize_button(self):
        """Position the resize button at lower left for user messages."""
        if not self.ui.messageContent or self.role != "user":
            return
        
        try:
            content_rect = self.ui.messageContent.geometry()
            if not content_rect.isValid() or content_rect.width() <= 0 or content_rect.height() <= 0:
                return
            
            button_size = 24
            padding = 4
            
            # Position at lower left corner of messageContent
            x = content_rect.left() + padding
            y = content_rect.bottom() - button_size - padding
            
            # Ensure coordinates are valid
            if x < 0 or y < 0:
                return
            
            self.resize_button.setGeometry(x, y, button_size, button_size)
            self.resize_button.raise_()  # Ensure it's on top
        except (RuntimeError, AttributeError):
            pass
    
    def _replace_message_content_with_spell_check(self):
        """Replace messageContent QTextEdit with SpellCheckTextEdit."""
        try:
            old_widget = self.ui.messageContent
            layout = self.ui.mainLayout
            
            # Get widget properties
            text = old_widget.toPlainText()
            object_name = old_widget.objectName()
            size_policy = old_widget.sizePolicy()
            vertical_scroll = old_widget.verticalScrollBarPolicy()
            horizontal_scroll = old_widget.horizontalScrollBarPolicy()
            
            # Create new spell-checking widget
            new_widget = SpellCheckTextEdit(self)
            new_widget.setObjectName(object_name)
            new_widget.setPlainText(text)
            new_widget.setSizePolicy(size_policy)
            new_widget.setVerticalScrollBarPolicy(vertical_scroll)
            new_widget.setHorizontalScrollBarPolicy(horizontal_scroll)
            new_widget.setAcceptRichText(old_widget.acceptRichText())
            
            # Replace in layout
            idx = layout.indexOf(old_widget)
            layout.removeWidget(old_widget)
            layout.insertWidget(idx, new_widget)
            old_widget.deleteLater()
            
            # Update reference
            self.ui.messageContent = new_widget
        except Exception as e:
            print(f"Warning: Could not replace messageContent with spell-checking version: {e}")

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move events during resize."""
        # Handle resize drag
        if self._is_resizing:
            try:
                self._handle_resize(event.globalPos())
            except (RuntimeError, AttributeError):
                # Widget might have been deleted
                self._is_resizing = False
                self.releaseMouse()
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release to end resize."""
        if self._is_resizing and event.button() == Qt.MouseButton.LeftButton:
            self._is_resizing = False
            self.releaseMouse()
            # Reset cursor
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            # If no drag occurred, optimize bubble size
            if not self._resize_moved:
                self._optimize_bubble_size()
        super().mouseReleaseEvent(event)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events."""
        super().mousePressEvent(event)
        # When clicked, set focus and emit focused signal for assistant messages
        if event.button() == Qt.MouseButton.LeftButton:
            self.setFocus()
            if self.role == "assistant":
                if self.model:
                    self.focused.emit(self.role, self.model)
                else:
                    self.focused.emit(self.role, "")
    
    def focusInEvent(self, event):
        """Handle focus in event - emit signal with role and model info."""
        super().focusInEvent(event)
        if self.role == "assistant" and self.model:
            self.focused.emit(self.role, self.model)
        elif self.role == "assistant":
            # Even if no model, emit with empty model string
            self.focused.emit(self.role, "")
    
    def eventFilter(self, obj, event: QEvent):
        # No longer handling resize handle events here - using mouse events instead
        
        # Handle events for messageContent
        if obj == self.ui.messageContent:
            if event.type() == QEvent.Type.FocusOut:
                print("Editing finished, triggering save.")
                self.editingFinished.emit()
            elif event.type() == QEvent.Type.FocusIn:
                # When messageContent gets focus, also emit focused signal for assistant messages
                if self.role == "assistant":
                    if self.model:
                        self.focused.emit(self.role, self.model)
                    else:
                        self.focused.emit(self.role, "")
            elif event.type() == QEvent.Type.Enter:
                # Show buttons and resize handle when mouse enters messageContent
                if self.ui.messageContent:
                    self._position_buttons()
                    self.button_container.show()
                    # Keep buttons translucent initially (will become solid on individual hover)
                    self._set_buttons_opacity(0.5)
            elif event.type() == QEvent.Type.Leave:
                # Hide buttons when mouse leaves messageContent
                # Use a small delay to allow mouse to move to buttons
                QTimer.singleShot(100, self._check_and_hide_buttons)
        elif obj == self.button_container:
            if event.type() == QEvent.Type.Enter:
                # Keep buttons visible when mouse enters button container
                self.button_container.show()
                # Keep buttons translucent initially (will become solid on individual hover)
                self._set_buttons_opacity(0.5)
            elif event.type() == QEvent.Type.Leave:
                # Hide buttons when mouse leaves button container
                QTimer.singleShot(100, self._check_and_hide_buttons)
        # Handle button hover events for individual buttons
        elif obj in [
            self.resize_button,
            self.fork_button, self.copy_button, self.cut_button, self.regenerate_button,
            self.mode_toggle_button
        ]:
            if event.type() == QEvent.Type.Enter:
                # Make button solid on hover
                self._set_button_opacity(obj, 1.0)
            elif event.type() == QEvent.Type.Leave:
                # Make button translucent when mouse leaves (but keep visible if container is visible)
                if self.button_container.isVisible():
                    self._set_button_opacity(obj, 0.5)
        return super().eventFilter(obj, event)

    def set_message(self, role: str, content: str, list_item: QListWidgetItem, model: str = None):
        if not self.ui.messageContent:
            return

        self.list_item = list_item
        self.role = role
        self.model = model if role == "assistant" else None  # Only store model for assistant messages
        
        # Store raw content
        self._raw_content = content
        
        # Reset custom size when message changes (user can resize again)
        self._custom_width = None
        self._custom_height = None
        
        # Stop thinking animation if role is changing away from "thinking"
        if self.role == "thinking" and role != "thinking":
            self._thinking_timer.stop()
        
        # For assistant messages, default to rendered mode
        if role == "assistant":
            self._display_mode = "rendered"
            self._update_display_mode()
        elif role == "thinking":
            # For thinking messages, show animated dots
            self.ui.messageContent.setPlainText(".")
            self._thinking_dot_count = 1
            self._thinking_direction = 1  # Start by increasing
            # Start animation timer (update every 500ms)
            self._thinking_timer.start(500)
            # Disable editing for thinking messages
            if isinstance(self.ui.messageContent, SpellCheckTextEdit):
                self.ui.messageContent.setReadOnly(True)
                self.ui.messageContent.setAcceptRichText(False)
        else:
            # For user messages, always use plain text
            self.ui.messageContent.setPlainText(content)
            # Enable editing and spell check for user messages
            if isinstance(self.ui.messageContent, SpellCheckTextEdit):
                self.ui.messageContent.setReadOnly(False)
                self.ui.messageContent.setAcceptRichText(False)

        if role == "user":
            self.ui.messageContent.setStyleSheet("background-color: #333333; color: #FFFFFF;")
            self.ui.mainLayout.setAlignment(self.ui.messageContent, Qt.AlignmentFlag.AlignRight)
        else:
            self.ui.messageContent.setStyleSheet("background-color: #444444; color: #FFFFFF;")
            self.ui.mainLayout.setAlignment(self.ui.messageContent, Qt.AlignmentFlag.AlignLeft)
        
        # Show/hide buttons based on role and set order
        # Assistant messages: regenerate, mode_toggle, copy, resize (from left to right)
        # User messages: resize, fork, regenerate, copy, cut (from left to right)
        if role == "assistant":
            # Hide user-specific buttons
            self.fork_button.setVisible(False)
            self.cut_button.setVisible(False)
            # Show assistant buttons: regenerate, mode_toggle, copy, resize
            self.regenerate_button.setVisible(True)
            self.mode_toggle_button.setVisible(True)
            self.copy_button.setVisible(True)
            self.resize_button.setVisible(True)
            self.resize_button.setText("↘️")
            # Reorder buttons: regenerate, mode_toggle, copy, resize
            layout = self.button_container.layout()
            if layout and isinstance(layout, QBoxLayout):
                # Reorder buttons: regenerate, mode_toggle, copy, resize
                layout.removeWidget(self.regenerate_button)
                layout.removeWidget(self.copy_button)
                layout.insertWidget(0, self.regenerate_button)
                layout.insertWidget(1, self.mode_toggle_button)
                layout.insertWidget(2, self.copy_button)
                layout.insertWidget(3, self.resize_button)
            # Update container size for assistant (4 buttons: regenerate, mode_toggle, copy, resize, with 2px spacing)
            self.button_container.setFixedSize(98, 24)
            # Disconnect any existing handler and connect assistant handler
            if self._regenerate_handler is not None:
                try:
                    self.regenerate_button.clicked.disconnect(self._regenerate_handler)
                except (RuntimeError, TypeError, AttributeError):
                    pass
            # Store and connect the new handler
            self._regenerate_handler = self.regenerateRequested.emit
            self.regenerate_button.clicked.connect(self._regenerate_handler)
        elif role == "user":
            # Show all user buttons: resize (separate, lower left), fork, regenerate, copy, cut (lower right)
            self.resize_button.setVisible(True)
            self.resize_button.setText("↙️")
            # Remove resize button from container layout for user messages (it's positioned separately)
            layout = self.button_container.layout()
            if layout and isinstance(layout, QBoxLayout):
                # Show other buttons: fork, regenerate, copy, cut
                self.fork_button.setVisible(True)
                self.regenerate_button.setVisible(True)
                self.copy_button.setVisible(True)
                self.cut_button.setVisible(True)
                # Reorder buttons: fork, regenerate, copy, cut
                layout.removeWidget(self.fork_button)
                layout.removeWidget(self.regenerate_button)
                layout.removeWidget(self.copy_button)
                layout.removeWidget(self.cut_button)
                layout.insertWidget(0, self.fork_button)
                layout.insertWidget(1, self.regenerate_button)
                layout.insertWidget(2, self.copy_button)
                layout.insertWidget(3, self.cut_button)
            # Update container size for user (4 buttons: fork, regenerate, copy, cut, with 2px spacing)
            self.button_container.setFixedSize(102, 24)
            # Position resize button separately at lower left
            QTimer.singleShot(50, self._position_resize_button)
            # Disconnect any existing handler and connect user handler
            if self._regenerate_handler is not None:
                try:
                    self.regenerate_button.clicked.disconnect(self._regenerate_handler)
                except (RuntimeError, TypeError, AttributeError):
                    pass
            # Store and connect the new handler
            self._regenerate_handler = self._on_regenerate_user_clicked
            self.regenerate_button.clicked.connect(self._regenerate_handler)
        else:
            # For thinking or other roles, hide all buttons
            self.resize_button.setVisible(False)
            self.fork_button.setVisible(False)
            self.regenerate_button.setVisible(False)
            self.copy_button.setVisible(False)
            self.cut_button.setVisible(False)
            self.mode_toggle_button.setVisible(False)
            # Stop thinking animation if role is not "thinking"
            if role != "thinking":
                self._thinking_timer.stop()

        self.update_size()
    
    def _update_thinking_animation(self):
        """Update the thinking indicator animation (cycles through 1, 2, 3, 2, 1 dots)."""
        if self.role != "thinking" or not self.ui.messageContent:
            self._thinking_timer.stop()
            return
        
        # Cycle through: 1, 2, 3, 2, 1, 1, 2, 3, 2, 1, ...
        # This creates a smooth pulsing effect
        # Use direction to track whether we're increasing or decreasing
        if self._thinking_dot_count == 1:
            self._thinking_dot_count = 2
            self._thinking_direction = 1  # Going up
        elif self._thinking_dot_count == 2:
            if self._thinking_direction == 1:
                self._thinking_dot_count = 3  # Continue up
            else:
                self._thinking_dot_count = 1  # Go back down
                self._thinking_direction = 1  # Reset to going up
        elif self._thinking_dot_count == 3:
            self._thinking_dot_count = 2
            self._thinking_direction = -1  # Start going down
        else:
            # Fallback: reset to 1
            self._thinking_dot_count = 1
            self._thinking_direction = 1
        
        # Update the text with the appropriate number of dots
        dots = "." * self._thinking_dot_count
        self.ui.messageContent.setPlainText(dots)
    
    def _on_mode_toggle_clicked(self):
        """Handle mode toggle button click - switch between rendered and raw modes."""
        if self.role != "assistant":
            return
        
        # If switching from raw to rendered, save any edits made in raw mode
        if self._display_mode == "raw" and self.ui.messageContent:
            self._raw_content = self.ui.messageContent.toPlainText()
            # Emit editingFinished signal to trigger save
            self.editingFinished.emit()
        
        # Toggle mode
        if self._display_mode == "rendered":
            self._display_mode = "raw"
        else:
            self._display_mode = "rendered"
        
        self._update_display_mode()
    
    def _update_display_mode(self):
        """Update the display based on current mode (rendered or raw)."""
        if self.role != "assistant" or not self.ui.messageContent:
            return
        
        if self._display_mode == "rendered":
            # Rendered mode: Convert Markdown to HTML and display
            # Use extensions for better markdown support
            extensions = ['fenced_code', 'tables', 'nl2br']

            html_content = markdown.markdown(self._raw_content, extensions=extensions)
            # Add basic styling for dark theme with proper list indentation
            styled_html = f"""
            <style>
                body {{ color: #FFFFFF; background-color: transparent; }}
                code {{ background-color: rgba(0, 0, 0, 0.3); padding: 2px 4px; border-radius: 3px; }}
                pre {{ background-color: rgba(0, 0, 0, 0.3); padding: 8px; border-radius: 4px; overflow-x: auto; }}
                pre code {{ background-color: transparent; padding: 0; }}
                table {{ border-collapse: collapse; margin: 8px 0; }}
                th, td {{ border: 1px solid #666; padding: 6px; }}
                th {{ background-color: rgba(0, 0, 0, 0.2); }}
                a {{ color: #4A9EFF; }}
                ul, ol {{ margin: 4px 0; padding-left: 24px; }}
                ul ul, ol ol, ul ol, ol ul {{ margin: 2px 0; padding-left: 24px; }}
                ul ul ul, ol ol ol, ul ul ol, ol ol ul, ul ol ul, ol ul ol {{ margin: 2px 0; padding-left: 24px; }}
                li {{ margin: 2px 0; }}
                p {{ margin: 0 0 0.75em 0; }}
                p:last-child {{ margin-bottom: 0; }}
                strong, b {{ font-weight: bold; }}
                em, i {{ font-style: italic; }}
                h1, h2, h3, h4, h5, h6 {{ margin: 0.5em 0 0.25em 0; }}
                h1:first-child, h2:first-child, h3:first-child, h4:first-child, h5:first-child, h6:first-child {{ margin-top: 0; }}
            </style>
            {html_content}
            """
            # Block signals temporarily to prevent spell checker from interfering
            was_blocked = self.ui.messageContent.signalsBlocked()
            if not was_blocked:
                self.ui.messageContent.blockSignals(True)
            try:
                self.ui.messageContent.setHtml(styled_html)
                self.ui.messageContent.setReadOnly(True)
                self.ui.messageContent.setAcceptRichText(True)
            finally:
                if not was_blocked:
                    self.ui.messageContent.blockSignals(False)
            # Note: Spell check is disabled in rendered mode since it's read-only
            
            # Update button icon and tooltip
            self.mode_toggle_button.setText("✏️")
            self.mode_toggle_button.setToolTip("Switch to raw text mode")
        else:
            # Raw mode: Display plain text, enable editing and spell check
            # Block signals temporarily to prevent interference
            was_blocked = self.ui.messageContent.signalsBlocked()
            if not was_blocked:
                self.ui.messageContent.blockSignals(True)
            try:
                # Clear first to remove any HTML formatting that might affect spacing
                self.ui.messageContent.clear()
                # Set plain text (this should reset formatting)
                self.ui.messageContent.setPlainText(self._raw_content)
                self.ui.messageContent.setReadOnly(False)
                self.ui.messageContent.setAcceptRichText(False)
                
                # Reset text block format to ensure normal line spacing
                # This prevents double spacing that can occur when switching from HTML mode
                doc = self.ui.messageContent.document()
                if doc:
                    # Reset default block format to ensure single line spacing
                    default_format = QTextBlockFormat()
                    # Set line height to 100% (normal single spacing) using proportional height
                    try:
                        # Use getattr to access LineHeightType enum to avoid IDE warnings
                        # ProportionalHeight with 100 means 100% of font height (single spacing)
                        line_height_type = getattr(QTextBlockFormat, 'LineHeightType', None)
                        if line_height_type:
                            default_format.setLineHeight(100, line_height_type.ProportionalHeight)
                        else:
                            # Fallback: use integer constant if enum doesn't exist
                            default_format.setLineHeight(100, 0)  # 0 = ProportionalHeight
                    except (AttributeError, TypeError):
                        # Fallback: try FixedHeight with 0 (use default)
                        try:
                            line_height_type = getattr(QTextBlockFormat, 'LineHeightType', None)
                            if line_height_type:
                                default_format.setLineHeight(0, line_height_type.FixedHeight)
                            else:
                                # Fallback: use integer constant if enum doesn't exist
                                default_format.setLineHeight(0, 1)  # 1 = FixedHeight
                        except (AttributeError, TypeError):
                            # If line height setting doesn't work, use default format as-is
                            pass
                    
                    # Apply the format to all blocks in the document
                    cursor = QTextCursor(doc)
                    block = doc.firstBlock()
                    while block.isValid():
                        cursor.setPosition(block.position())
                        cursor.setBlockFormat(default_format)
                        block = block.next()
                    
                    # Move cursor to start
                    cursor.movePosition(QTextCursor.MoveOperation.Start)
                    self.ui.messageContent.setTextCursor(cursor)
            finally:
                if not was_blocked:
                    self.ui.messageContent.blockSignals(False)
            # Spell check is already enabled for SpellCheckTextEdit
            
            # Connect to textChanged to update raw_content when user edits
            # Disconnect first to avoid multiple connections
            try:
                if isinstance(self.ui.messageContent, SpellCheckTextEdit):
                    self.ui.messageContent.textChanged.disconnect(self._on_raw_content_changed)
            except (RuntimeError, TypeError):
                pass
            if isinstance(self.ui.messageContent, SpellCheckTextEdit):
                self.ui.messageContent.textChanged.connect(self._on_raw_content_changed)
            
            # Update button icon and tooltip
            self.mode_toggle_button.setText("👁️")
            self.mode_toggle_button.setToolTip("Switch to rendered mode")
    
    def _on_raw_content_changed(self):
        """Update raw_content when user edits in raw mode."""
        if self._display_mode == "raw" and self.ui.messageContent:
            self._raw_content = self.ui.messageContent.toPlainText()
    
    def _on_regenerate_user_clicked(self):
        """Handle regenerate button click for user messages."""
        self.regenerateUserRequested.emit()

    def get_content(self) -> str:
        """Get the current content. For assistant messages, always return raw content."""
        if self.role == "assistant":
            # Always return raw content, regardless of display mode
            if self._display_mode == "raw":
                # If in raw mode, get from the text edit (user may have edited)
                if self.ui.messageContent:
                    self._raw_content = self.ui.messageContent.toPlainText()
            return self._raw_content
        else:
            # For user messages, get from text edit
            if self.ui.messageContent:
                return self.ui.messageContent.toPlainText()
        return ""

    def get_message_dict(self) -> dict:
        """Returns the message as a dictionary with role, content, and optionally model."""
        message = {"role": self.role, "content": self.get_content()}
        if self.role == "assistant" and self.model:
            message["model"] = self.model
        return message

    def update_size(self):
        """
        Calculates and sets the item's size hint. This is the simple, correct logic.
        Now supports custom width/height from resizing.
        """
        if not self.ui.messageContent or not self.list_item:
            return

        list_widget = self.list_item.listWidget()
        if not list_widget:
            return

        viewport_width = list_widget.viewport().width()
        if viewport_width <= 10:
            return

        layout_margins = self.ui.mainLayout.contentsMargins()
        total_layout_margin = layout_margins.left() + layout_margins.right()
        available_width = viewport_width - total_layout_margin

        # 1. Calculate max width
        max_bubble_width = int(available_width * self.MAX_BUBBLE_RATIO)
        max_bubble_width = max(max_bubble_width, self.MIN_BUBBLE_WIDTH)

        # 2. Determine final bubble width (use custom if set, otherwise calculate)
        if self._custom_width is not None:
            final_bubble_width = max(self.MIN_BUBBLE_WIDTH, min(self._custom_width, max_bubble_width))
        else:
            # Get ideal text width (unwrapped)
            doc = self.ui.messageContent.document()
            metrics = QFontMetrics(doc.defaultFont())
            ideal_width = metrics.boundingRect(self.ui.messageContent.toPlainText()).width() + (2 * self.BUBBLE_PADDING)
            final_bubble_width = min(ideal_width, max_bubble_width)
            final_bubble_width = max(final_bubble_width, self.MIN_BUBBLE_WIDTH)

        # 3. Calculate height (use custom if set, otherwise calculate)
        text_wrap_width = final_bubble_width - (2 * self.BUBBLE_PADDING)
        doc = self.ui.messageContent.document()
        doc.setTextWidth(text_wrap_width)
        
        if self._custom_height is not None:
            final_bubble_height = max(doc.size().height() + (2 * self.BUBBLE_PADDING), self._custom_height)
        else:
            final_bubble_height = doc.size().height() + (2 * self.BUBBLE_PADDING)

        # 4. Set the bubble's constraints
        self.ui.messageContent.setMinimumWidth(int(final_bubble_width))
        self.ui.messageContent.setMaximumWidth(int(final_bubble_width))
        self.ui.messageContent.setFixedHeight(int(final_bubble_height))

        # 5. Set the *row's* size hint (this pushes down subsequent messages)
        total_height = final_bubble_height + layout_margins.top() + layout_margins.bottom()
        self.list_item.setSizeHint(QSize(viewport_width, int(total_height)))
        
        # 6. Update button positions after size change
        self._position_buttons()
        # Update resize button position if it's separate (user messages)
        if self.role == "user" and hasattr(self, 'resize_button') and self.resize_button.isVisible():
            self._position_resize_button()
    
    def _handle_resize(self, global_pos: QPoint):
        """Handle resize drag - update widget size based on mouse movement."""
        if not self.list_item or not self.ui.messageContent:
            return
        
        list_widget = self.list_item.listWidget()
        if not list_widget:
            return
        
        # Calculate delta from start position
        delta = global_pos - self._resize_start_pos
        
        # Treat small movement as click (no resize)
        if not self._resize_moved:
            if delta.manhattanLength() < 3:
                return
            self._resize_moved = True
        
        # Get viewport width for max width calculation
        viewport_width = list_widget.viewport().width()
        layout_margins = self.ui.mainLayout.contentsMargins()
        total_layout_margin = layout_margins.left() + layout_margins.right()
        available_width = viewport_width - total_layout_margin
        max_bubble_width = int(available_width * self.MAX_BUBBLE_RATIO)
        max_bubble_width = max(max_bubble_width, self.MIN_BUBBLE_WIDTH)
        
        # Calculate new size based on role
        if self.role == "user":
            # User messages: resize leftward (negative delta.x) and downward (positive delta.y)
            new_width = self._resize_start_size.width() - delta.x()
            new_height = self._resize_start_size.height() + delta.y()
        else:
            # Assistant messages: resize rightward (positive delta.x) and downward (positive delta.y)
            new_width = self._resize_start_size.width() + delta.x()
            new_height = self._resize_start_size.height() + delta.y()
        
        # Clamp width to valid range
        new_width = max(self.MIN_BUBBLE_WIDTH, min(new_width, max_bubble_width))
        # Clamp height to minimum (at least enough for text)
        doc = self.ui.messageContent.document()
        min_height = doc.size().height() + (2 * self.BUBBLE_PADDING)
        new_height = max(min_height, new_height)
        
        # Store custom size
        self._custom_width = int(new_width)
        self._custom_height = int(new_height)
        
        # Update size (this will update text wrapping and push down subsequent messages)
        self.update_size()
        
        # Force immediate update
        QApplication.processEvents()

    def _optimize_bubble_size(self):
        """Reset custom sizing so bubble auto-sizes to content."""
        self._custom_width = None
        self._custom_height = None
        self.update_size()
