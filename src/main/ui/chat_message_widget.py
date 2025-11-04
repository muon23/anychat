from PySide6.QtCore import Qt, QSize, Signal, QEvent
from PySide6.QtGui import QFontMetrics
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
    MIN_BUBBLE_WIDTH = 250
    MAX_BUBBLE_RATIO = 0.9
    BUBBLE_PADDING = 8

    editingFinished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_ChatMessageWidget()
        self.ui.setupUi(self)
        self.list_item = None
        self.role = "user"

        if self.ui.messageContent:
            self.ui.messageContent.installEventFilter(self)

    def eventFilter(self, obj, event: QEvent):
        if obj == self.ui.messageContent and event.type() == QEvent.Type.FocusOut:
            print("Editing finished, triggering save.")
            self.editingFinished.emit()
        return super().eventFilter(obj, event)

    def set_message(self, role: str, content: str, list_item: QListWidgetItem):
        if not self.ui.messageContent:
            return

        self.list_item = list_item
        self.role = role
        self.ui.messageContent.setPlainText(content)

        if role == "user":
            self.ui.messageContent.setStyleSheet("background-color: #333333; color: #FFFFFF;")
            self.ui.mainLayout.setAlignment(self.ui.messageContent, Qt.AlignmentFlag.AlignRight)
        else:
            self.ui.messageContent.setStyleSheet("background-color: #444444; color: #FFFFFF;")
            self.ui.mainLayout.setAlignment(self.ui.messageContent, Qt.AlignmentFlag.AlignLeft)

        self.update_size()

    def get_content(self) -> str:
        if self.ui.messageContent:
            return self.ui.messageContent.toPlainText()
        return ""

    def get_message_tuple(self) -> tuple:
        return self.role, self.get_content()

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
