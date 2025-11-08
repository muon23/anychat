from PySide6.QtCore import Qt, QSize, Signal, QEvent, QTimer
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QWidget, QListWidgetItem, QTextEdit, QPushButton,
    QHBoxLayout, QApplication, QGraphicsOpacityEffect
)

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
    forkRequested = Signal()
    regenerateRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_ChatMessageWidget()
        self.ui.setupUi(self)
        self.list_item = None
        self.role = "user"
        self.model = None  # Store the model name for assistant messages
        self._is_deleted = False  # Flag to track if widget is being deleted
        
        # Create button container and buttons
        self._create_action_buttons()

        # Replace messageContent with spell-checking version if it's a QTextEdit
        if self.ui.messageContent and isinstance(self.ui.messageContent, QTextEdit):
            self._replace_message_content_with_spell_check()

        if self.ui.messageContent:
            self.ui.messageContent.installEventFilter(self)
    
    def _create_action_buttons(self):
        """Create action buttons (fork, copy, cut, regenerate) in the lower right."""
        # Create a container widget for buttons positioned absolutely
        self.button_container = QWidget(self)
        self.button_container.setObjectName("buttonContainer")
        self.button_container.setStyleSheet("background-color: transparent;")
        # Set a fixed size for the container - will be updated when regenerate button is added
        # 3 buttons * 24px + 2 spacing * 2px = 76px width, 24px height
        # With regenerate: 4 buttons * 24px + 3 spacing * 2px = 102px width
        self.button_container.setFixedSize(76, 24)
        self.button_container.raise_()  # Raise above other widgets
        
        # Create horizontal layout for buttons
        button_layout = QHBoxLayout(self.button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(2)
        
        # Create buttons with text labels (we'll use simple text for now, can be replaced with icons)
        self.fork_button = QPushButton("🔀", self.button_container)
        self.fork_button.setObjectName("forkButton")
        self.fork_button.setToolTip("Fork (to be implemented)")
        self.fork_button.setFixedSize(24, 24)
        # Use opacity to make the entire button (including emoji) translucent
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0.5)  # 50% opacity
        self.fork_button.setGraphicsEffect(opacity_effect)
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
        # Store effect reference for hover handling
        self.fork_button._opacity_effect = opacity_effect
        self.fork_button.clicked.connect(self.forkRequested.emit)
        self.fork_button.setEnabled(False)  # Disabled until implemented
        
        self.copy_button = QPushButton("📋", self.button_container)
        self.copy_button.setObjectName("copyButton")
        self.copy_button.setToolTip("Copy to clipboard")
        self.copy_button.setFixedSize(24, 24)
        # Use opacity to make the entire button (including emoji) translucent
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0.5)  # 50% opacity
        self.copy_button.setGraphicsEffect(opacity_effect)
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
        # Store effect reference for hover handling
        self.copy_button._opacity_effect = opacity_effect
        self.copy_button.clicked.connect(self._on_copy_clicked)
        
        self.cut_button = QPushButton("✂️", self.button_container)
        self.cut_button.setObjectName("cutButton")
        self.cut_button.setToolTip("Cut (copy and remove)")
        self.cut_button.setFixedSize(24, 24)
        # Use opacity to make the entire button (including emoji) translucent
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0.5)  # 50% opacity
        self.cut_button.setGraphicsEffect(opacity_effect)
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
        # Store effect reference for hover handling
        self.cut_button._opacity_effect = opacity_effect
        self.cut_button.clicked.connect(self._on_cut_clicked)
        
        # Add buttons to layout
        button_layout.addWidget(self.fork_button)
        button_layout.addWidget(self.copy_button)
        button_layout.addWidget(self.cut_button)
        
        # Regenerate button (only for assistant messages, added dynamically)
        self.regenerate_button = None
        
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
        self.fork_button.installEventFilter(self)
        self.copy_button.installEventFilter(self)
        self.cut_button.installEventFilter(self)
        
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
        """Handle cut button click - copy to clipboard and emit cut signal."""
        content = self.get_content()
        if content:
            clipboard = QApplication.clipboard()
            clipboard.setText(content)
            self.cutRequested.emit()
    
    def enterEvent(self, event):
        """Show buttons when mouse enters the widget."""
        super().enterEvent(event)
        if self.ui.messageContent:
            self._position_buttons()
            self.button_container.show()
    
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
    
    def _set_buttons_opacity(self, opacity: float):
        """Set opacity for all buttons."""
        buttons = [self.fork_button, self.copy_button, self.cut_button]
        if self.regenerate_button:
            buttons.append(self.regenerate_button)
        for button in buttons:
            if button and hasattr(button, '_opacity_effect'):
                button._opacity_effect.setOpacity(opacity)
    
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

    def eventFilter(self, obj, event: QEvent):
        if obj == self.ui.messageContent:
            if event.type() == QEvent.Type.FocusOut:
                print("Editing finished, triggering save.")
                self.editingFinished.emit()
            elif event.type() == QEvent.Type.Enter:
                # Show buttons when mouse enters messageContent
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
        elif obj in [self.fork_button, self.copy_button, self.cut_button] or (self.regenerate_button and obj == self.regenerate_button):
            if event.type() == QEvent.Type.Enter:
                # Make button solid on hover
                if hasattr(obj, '_opacity_effect'):
                    obj._opacity_effect.setOpacity(1.0)
            elif event.type() == QEvent.Type.Leave:
                # Make button translucent when mouse leaves (but keep visible if container is visible)
                if hasattr(obj, '_opacity_effect') and self.button_container.isVisible():
                    obj._opacity_effect.setOpacity(0.5)
        return super().eventFilter(obj, event)

    def set_message(self, role: str, content: str, list_item: QListWidgetItem, model: str = None):
        if not self.ui.messageContent:
            return

        self.list_item = list_item
        self.role = role
        self.model = model if role == "assistant" else None  # Only store model for assistant messages
        self.ui.messageContent.setPlainText(content)

        if role == "user":
            self.ui.messageContent.setStyleSheet("background-color: #333333; color: #FFFFFF;")
            self.ui.mainLayout.setAlignment(self.ui.messageContent, Qt.AlignmentFlag.AlignRight)
        else:
            self.ui.messageContent.setStyleSheet("background-color: #444444; color: #FFFFFF;")
            self.ui.mainLayout.setAlignment(self.ui.messageContent, Qt.AlignmentFlag.AlignLeft)
        
        # Show regenerate button only for assistant messages (not for thinking)
        if self.regenerate_button is None and role == "assistant":
            self._add_regenerate_button()
        elif self.regenerate_button is not None:
            self.regenerate_button.setVisible(role == "assistant")

        self.update_size()
    
    def _add_regenerate_button(self):
        """Add regenerate button for assistant messages."""
        if self.regenerate_button is not None:
            return
        
        self.regenerate_button = QPushButton("🔄", self.button_container)
        self.regenerate_button.setObjectName("regenerateButton")
        self.regenerate_button.setToolTip("Regenerate response")
        self.regenerate_button.setFixedSize(24, 24)
        # Use opacity to make the entire button (including emoji) translucent
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0.5)  # 50% opacity
        self.regenerate_button.setGraphicsEffect(opacity_effect)
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
        # Store effect reference for hover handling
        self.regenerate_button._opacity_effect = opacity_effect
        self.regenerate_button.clicked.connect(self.regenerateRequested.emit)
        
        # Install event filter for hover opacity changes
        self.regenerate_button.installEventFilter(self)
        
        # Insert before fork button
        button_layout = self.button_container.layout()
        if button_layout and isinstance(button_layout, QHBoxLayout):
            button_layout.insertWidget(0, self.regenerate_button)
        elif button_layout:
            # Fallback: add to end if not QHBoxLayout
            button_layout.addWidget(self.regenerate_button)
        
        # Update container size to accommodate regenerate button
        # 4 buttons * 24px + 3 spacing * 2px = 102px width
        self.button_container.setFixedSize(102, 24)

    def get_content(self) -> str:
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

        # 2. Get ideal text width (unwrapped)
        doc = self.ui.messageContent.document()
        metrics = QFontMetrics(doc.defaultFont())
        ideal_width = metrics.boundingRect(self.ui.messageContent.toPlainText()).width() + (2 * self.BUBBLE_PADDING)

        # 3. Determine final bubble width
        final_bubble_width = min(ideal_width, max_bubble_width)
        final_bubble_width = max(final_bubble_width, self.MIN_BUBBLE_WIDTH)

        # 4. Calculate height based on *that* width
        text_wrap_width = final_bubble_width - (2 * self.BUBBLE_PADDING)
        doc.setTextWidth(text_wrap_width)
        final_bubble_height = doc.size().height() + (2 * self.BUBBLE_PADDING)

        # 5. Set the bubble's constraints (this was the checkpoint logic)
        self.ui.messageContent.setMinimumWidth(int(final_bubble_width))
        self.ui.messageContent.setMaximumWidth(int(final_bubble_width))
        self.ui.messageContent.setFixedHeight(int(final_bubble_height))

        # 6. Set the *row's* size hint
        total_height = final_bubble_height + layout_margins.top() + layout_margins.bottom()
        self.list_item.setSizeHint(QSize(viewport_width, int(total_height)))
        
        # 7. Update button positions after size change
        self._position_buttons()
