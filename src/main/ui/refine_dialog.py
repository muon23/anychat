from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QSizePolicy
)

from spell_check_text_edit import SpellCheckTextEdit


class RefineDialog(QDialog):
    def __init__(self, refine_prompt: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Refine Assistant Message")
        self.setModal(True)
        self.setMinimumSize(500, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.refine_prompt = refine_prompt
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Create text edit with word wrapping and spell checking
        self.text_edit = SpellCheckTextEdit(self)
        self.text_edit.setPlainText("")
        self.text_edit.setAcceptRichText(False)
        self.text_edit.setLineWrapMode(SpellCheckTextEdit.LineWrapMode.WidgetWidth)
        self.text_edit.setPlaceholderText("Enter comments to refine the assistant message (optional)...")
        
        # Create button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()  # Push buttons to the right
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        # Refine button
        self.refine_button = QPushButton("Refine", self)
        self.refine_button.setToolTip("Refine the assistant message based on your comments (or regenerate if empty).")
        self.refine_button.clicked.connect(self.accept)
        button_layout.addWidget(self.refine_button)
        
        # Store reference to parent to check LLM call status
        self.parent_window = parent
        
        # Add widgets to layout
        layout.addWidget(self.text_edit)
        layout.addLayout(button_layout)
        
        # Set layout margins
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
    
    def get_text(self) -> str:
        """Returns the current text in the text edit."""
        return self.text_edit.toPlainText().strip()
    
    def get_refine_prompt(self) -> str:
        """Returns the refine prompt to use."""
        return self.refine_prompt
    
    def set_refine_button_enabled(self, enabled: bool):
        """Enable or disable the refine button."""
        if self.refine_button:
            self.refine_button.setEnabled(enabled)

