from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QWidget, QListWidgetItem

# Import the compiled UI class
try:
    from ui_chat_message_widget import Ui_ChatMessageWidget
except ImportError:
    print("Error: Could not import ui_chat_message_widget.py.")
    class Ui_ChatMessageWidget:
        def setupUi(self, widget): pass
        def __getattr__(self, name): return None

class ChatMessageWidget(QWidget):
    MIN_BUBBLE_WIDTH = 250  # Minimum width for readability
    MAX_BUBBLE_RATIO = 0.9  # Max 90% of the list view's width
    BUBBLE_PADDING = 8      # 8px padding inside the QTextEdit

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_ChatMessageWidget()
        self.ui.setupUi(self)
        self.list_item = None # We'll store the QListWidgetItem here
        self.role = "user"    # Default role

        # Connect the text content's textChanged signal to our resizing function
        if self.ui.messageContent:
            self.ui.messageContent.textChanged.connect(self.update_size)

    def set_message(self, role: str, content: str, list_item: QListWidgetItem):
        """
        Sets the content, style, and alignment for this chat bubble.
        """
        if not self.ui.messageContent:
            return

        self.list_item = list_item
        self.role = role
        self.ui.messageContent.setPlainText(content)

        # 1. Set style and alignment based on role
        if role == "user":
            # User message: dark gray, aligned right
            self.ui.messageContent.setStyleSheet("background-color: #333333; color: #FFFFFF;")
            # --- NEW ALIGNMENT LOGIC ---
            self.ui.mainLayout.setAlignment(self.ui.messageContent, Qt.AlignmentFlag.AlignRight)
        else:
            # AI (assistant) message: lighter gray, aligned left
            self.ui.messageContent.setStyleSheet("background-color: #444444; color: #FFFFFF;")
            # --- NEW ALIGNMENT LOGIC ---
            self.ui.mainLayout.setAlignment(self.ui.messageContent, Qt.AlignmentFlag.AlignLeft)

        # Trigger an initial size update
        self.update_size()

    def get_content(self) -> str:
        """Returns the current text from the text edit."""
        if self.ui.messageContent:
            return self.ui.messageContent.toPlainText()
        return ""

    def get_message_tuple(self) -> tuple:
        """
        Returns the role and content of this message bubble.
        """
        return (self.role, self.get_content())

    def update_size(self):
        """
        Calculates and sets the item's size hint based on text content and window width.
        """
        if not self.ui.messageContent or not self.list_item:
            return

        list_widget = self.list_item.listWidget()
        if not list_widget:
            return

        viewport_width = list_widget.viewport().width()

        if viewport_width <= 10:
            return

        # Get total horizontal margin of the bubble's layout
        layout_margins = self.ui.mainLayout.contentsMargins()
        total_layout_margin = layout_margins.left() + layout_margins.right()

        # Available width for the bubble is viewport width minus layout margins
        available_width = viewport_width - total_layout_margin

        # 1. Calculate max width based on ratio
        max_bubble_width = int(available_width * self.MAX_BUBBLE_RATIO)
        # Ensure max width is at least the min width
        max_bubble_width = max(max_bubble_width, self.MIN_BUBBLE_WIDTH)

        # 2. Calculate ideal unconstrained text width
        doc = self.ui.messageContent.document()
        doc.setTextWidth(-1) # No wrapping
        # Add 2*padding (for left/right) to the text width
        ideal_bubble_width = doc.size().width() + (2 * self.BUBBLE_PADDING)

        # 3. Determine final bubble width
        # It's the smaller of the ideal width and the max width
        final_bubble_width = min(ideal_bubble_width, max_bubble_width)
        # But it can't be smaller than the minimum
        final_bubble_width = max(final_bubble_width, self.MIN_BUBBLE_WIDTH)

        # 4. Calculate final height based on the *final* width
        # This is the width the document will actually wrap at
        text_wrap_width = final_bubble_width - (2 * self.BUBBLE_PADDING)
        doc.setTextWidth(text_wrap_width)

        # Add 2*padding (for top/bottom) to the text height
        final_bubble_height = doc.size().height() + (2 * self.BUBBLE_PADDING)

        # 5. --- THIS IS THE FIX ---
        # Instead of setFixedSize, we set constraints.
        # This lets the layout manager work while respecting our limits.
        self.ui.messageContent.setMinimumWidth(int(final_bubble_width))
        self.ui.messageContent.setMaximumWidth(int(final_bubble_width))
        self.ui.messageContent.setFixedHeight(int(final_bubble_height))


        # 6. Update the QListWidgetItem's size hint
        # The total height is the bubble's height + layout margins
        total_height = final_bubble_height + layout_margins.top() + layout_margins.bottom()

        # The size hint for the *row* must be the full viewport width
        # to allow the alignment to work.
        self.list_item.setSizeHint(QSize(viewport_width, int(total_height)))

