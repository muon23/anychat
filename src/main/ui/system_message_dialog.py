import sys
from contextlib import contextmanager

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QSizePolicy, QFileDialog, QMessageBox
)

from spell_check_text_edit import SpellCheckTextEdit


# Context manager to suppress macOS-specific Qt file dialog warnings
# This is a known issue with Qt's native file dialogs on macOS
@contextmanager
def suppress_macos_file_dialog_warnings():
    """Suppresses macOS-specific warnings from Qt file dialogs."""
    if sys.platform == 'darwin':  # macOS only
        # Save original stderr
        original_stderr = sys.stderr
        
        # Create a simple filter class
        class FilteredStderr:
            def __init__(self, original):
                self.original = original
            
            def write(self, text):
                # Filter out the NSOpenPanel warning
                if 'NSOpenPanel' in text and 'overrides' in text and 'identifier' in text:
                    return
                return self.original.write(text)
            
            def flush(self):
                return self.original.flush()
            
            def __getattr__(self, name):
                return getattr(self.original, name)
        
        try:
            sys.stderr = FilteredStderr(original_stderr)
            yield
        finally:
            sys.stderr = original_stderr
    else:
        yield


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
        
        # Create button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()  # Push buttons to the right
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        # Load button
        self.load_button = QPushButton("Load", self)
        self.load_button.setToolTip("Load system message from a .txt file. The current content will be replaced.")
        self.load_button.clicked.connect(self._load_from_file)
        button_layout.addWidget(self.load_button)
        
        # Save button
        self.save_button = QPushButton("Save", self)
        self.save_button.setToolTip("Save the current system message to a .txt file.")
        self.save_button.clicked.connect(self._save_to_file)
        button_layout.addWidget(self.save_button)
        
        # Apply button
        self.apply_button = QPushButton("Apply", self)
        self.apply_button.setToolTip("Apply the system message to the chat. Only applies if the message is not empty.")
        self.apply_button.clicked.connect(self.accept)
        button_layout.addWidget(self.apply_button)
        
        # Add widgets to layout
        layout.addWidget(self.text_edit)
        layout.addLayout(button_layout)
        
        # Set layout margins
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
    
    def _load_from_file(self):
        """Opens a file selection dialog to load a .txt file."""
        with suppress_macos_file_dialog_warnings():
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Load System Message",
                "",
                "Text Files (*.txt);;All Files (*)"
            )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Overwrite current content
                self.text_edit.setPlainText(content)
            except Exception as e:
                QMessageBox.warning(self, "Load Error", f"Could not load file: {e}")
    
    def _save_to_file(self):
        """Opens a file selection dialog to save the current content to a .txt file."""
        with suppress_macos_file_dialog_warnings():
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save System Message",
                "",
                "Text Files (*.txt);;All Files (*)"
            )
        
        if file_path:
            try:
                # Ensure .txt extension if not present
                if not file_path.endswith('.txt'):
                    file_path += '.txt'
                
                content = self.text_edit.toPlainText()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                QMessageBox.warning(self, "Save Error", f"Could not save file: {e}")
    
    def get_text(self) -> str:
        """Returns the current text in the text edit."""
        return self.text_edit.toPlainText().strip()

