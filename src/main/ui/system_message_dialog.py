from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QDialogButtonBox,
    QSizePolicy
)
from spell_check_text_edit import SpellCheckTextEdit


class SystemMessageDialog(QDialog):
    def __init__(self, current_system_message: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit System Message")
        self.setModal(True)
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Create text edit with word wrapping and spell checking
        self.text_edit = SpellCheckTextEdit(self)
        self.text_edit.setPlainText(current_system_message)
        self.text_edit.setAcceptRichText(False)
        self.text_edit.setLineWrapMode(SpellCheckTextEdit.LineWrapMode.WidgetWidth)
        self.text_edit.setPlaceholderText("Enter system message (instructions for the assistant)...")
        
        # Create button box with Save and Cancel
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
            self
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        # Add widgets to layout
        layout.addWidget(self.text_edit)
        layout.addWidget(self.button_box)
        
        # Set layout margins
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
    
    def get_text(self) -> str:
        """Returns the current text in the text edit."""
        return self.text_edit.toPlainText().strip()

