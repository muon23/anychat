from PySide6.QtWidgets import QWidget, QListWidgetItem, QSizePolicy

# Import the compiled UI class
try:
    from ui_chat_message_widget import Ui_ChatMessageWidget
except ImportError:
    print("Error: Could not import ui_chat_message_widget.py.")
    class Ui_ChatMessageWidget:
        def setupUi(self, widget): pass
        def __getattr__(self, name): return None

class ChatMessageWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_ChatMessageWidget()
        self.ui.setupUi(self)
        self.list_item = None # We'll store the QListWidgetItem here

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
        self.ui.messageContent.setPlainText(content)

        # 1. Set style and alignment based on role
        if role == "user":
            # User message: dark gray, aligned right
            self.ui.messageContent.setStyleSheet("background-color: #333333; color: #FFFFFF;")
            # Make the LEFT spacer expanding and the RIGHT spacer fixed
            self.ui.leftSpacer.changeSize(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            self.ui.rightSpacer.changeSize(10, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        else:
            # AI (assistant) message: lighter gray, aligned left
            self.ui.messageContent.setStyleSheet("background-color: #444444; color: #FFFFFF;")
            # Make the LEFT spacer fixed and the RIGHT spacer expanding
            self.ui.leftSpacer.changeSize(10, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
            self.ui.rightSpacer.changeSize(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Trigger an initial size update
        self.update_size()

    def get_content(self) -> str:
        """Returns the current text from the text edit."""
        if self.ui.messageContent:
            return self.ui.messageContent.toPlainText()
        return ""

    def update_size(self):
        """
        Automatically resizes the QTextEdit and the QListWidgetItem
        to fit the text content.
        """
        if not self.ui.messageContent or not self.list_item:
            return

        # 1. Get the available width from the QListWidget's viewport
        list_widget = self.list_item.listWidget()
        if not list_widget:
            return

        # This is the max width for the *layout* containing the bubble
        viewport_width = list_widget.viewport().width()

        # 2. Define paddings and constraints
        max_text_width = int(viewport_width * 0.75) # Max bubble width 75%
        min_bubble_width = 50 # Min width for short messages
        text_padding = 20 # 8px padding left/right + 4px buffer
        vertical_padding = 16 # 8px padding top/bottom

        # 3. Calculate ideal width (unconstrained)
        doc = self.ui.messageContent.document()
        doc.setTextWidth(-1) # -1 means no wrapping
        ideal_width = doc.size().width() + text_padding

        # 4. Determine final width
        final_width = min(ideal_width, max_text_width)
        final_width = max(final_width, min_bubble_width)

        # 5. Calculate ideal height *based on final width*
        # Set the document's wrapping width to the final bubble width
        doc.setTextWidth(final_width - text_padding)
        ideal_height = doc.size().height() + vertical_padding

        # 6. Apply the calculated sizes
        self.ui.messageContent.setFixedSize(int(final_width), int(ideal_height))

        # 7. Update the QListWidgetItem's size hint
        total_height = ideal_height + self.layout().contentsMargins().top() + self.layout().contentsMargins().bottom()
        self.setMinimumHeight(int(total_height))
        self.list_item.setSizeHint(self.sizeHint())

