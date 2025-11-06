import logging

from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QTextCharFormat, QTextCursor, QColor
from PySide6.QtWidgets import QTextEdit, QMenu

logger = logging.getLogger(__name__)

try:
    import enchant
    SPELLCHECKER_AVAILABLE = True
except ImportError:
    enchant = None  # Explicitly set to None when import fails
    SPELLCHECKER_AVAILABLE = False
    logger.warning("pyenchant not installed. Spell checking disabled.")
    logger.info("Install it with: pip install pyenchant")
    logger.info("Note: You also need to install enchant library on your system.")
    logger.info("  On macOS: brew install enchant")


class SpellCheckTextEdit(QTextEdit):
    """QTextEdit with spell checking functionality."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.spell_checker = None
        self.misspelled_format = QTextCharFormat()
        # Use a wavy red underline for misspelled words
        # Try different underline styles that are commonly available
        underline_style = QTextCharFormat.UnderlineStyle.SpellCheckUnderline
        # Check if WaveUnderline is available (Qt 6.5+)
        if hasattr(QTextCharFormat.UnderlineStyle, 'WaveUnderline'):
            underline_style = QTextCharFormat.UnderlineStyle.WaveUnderline
        elif hasattr(QTextCharFormat.UnderlineStyle, 'SingleUnderline'):
            underline_style = QTextCharFormat.UnderlineStyle.SingleUnderline
        
        self.misspelled_format.setUnderlineStyle(underline_style)
        self.misspelled_format.setUnderlineColor(QColor(255, 0, 0))  # Red underline
        
        if SPELLCHECKER_AVAILABLE:
            try:
                self._init_enchant()
            except Exception as e:
                logger.warning(f"Failed to initialize spell checker: {e}")
                self.spell_checker = None
        else:
            logger.warning("Spell checker not available. Install pyenchant to enable spell checking.")
        
        # Debounce timer to avoid checking on every keystroke
        self.check_timer = QTimer(self)
        self.check_timer.setSingleShot(True)
        self.check_timer.timeout.connect(self._perform_spell_check)
        
        # Connect signals for spell checking
        self.textChanged.connect(self._on_text_changed_handler)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        # Track last cursor position to detect word completion
        self.last_cursor_position = 0
        
        # Track words ignored for this session (temporary)
        self.session_ignored_words = set()
    
    def _init_enchant(self):
        """Initialize using pyenchant package."""
        try:
            # Try to create a dictionary for English (US)
            self.spell_checker = enchant.Dict("en_US")
            logger.debug("Spell checker initialized successfully with en_US dictionary.")
        except enchant.errors.DictNotFoundError:
            # Try English (UK) as fallback
            try:
                self.spell_checker = enchant.Dict("en_GB")
                logger.debug("Spell checker initialized successfully with en_GB dictionary.")
            except enchant.errors.DictNotFoundError:
                # Try generic English
                try:
                    self.spell_checker = enchant.Dict("en")
                    logger.debug("Spell checker initialized successfully with en dictionary.")
                except enchant.errors.DictNotFoundError:
                    logger.warning("No English dictionary found for enchant.")
                    logger.info("On macOS, you may need to install aspell dictionaries:")
                    logger.info("  brew install aspell --lang=en")
                    self.spell_checker = None
        except Exception as e:
            logger.warning(f"Failed to initialize enchant: {e}")
            self.spell_checker = None
        
        # Enable spell check underlines in the document
        if self.document():
            self.document().setUseDesignMetrics(True)
        
        # Store current misspelled word position for context menu
        self.current_misspelled_word = None
        self.current_misspelled_start = -1
        self.current_misspelled_end = -1
    
    def _on_text_changed_handler(self):
        """Handle text changes - check if word was completed."""
        if not self.spell_checker:
            return
        
        # Get current cursor position and text
        cursor = self.textCursor()
        current_pos = cursor.position()
        text = self.toPlainText()
        
        # Check if user just typed a space or punctuation (word completion)
        if 0 < current_pos <= len(text):
            char_before = text[current_pos - 1]
            # If space or punctuation, check immediately (word was completed)
            if char_before in ' \n\t.,!?;:':
                # Cancel any pending timer and check immediately
                self.check_timer.stop()
                QTimer.singleShot(50, self._perform_spell_check)  # Small delay to ensure text is updated
                return
        
        # Otherwise, schedule delayed check for continuous typing
        self._schedule_spell_check()
    
    def _schedule_spell_check(self):
        """Schedule spell check after a short delay (debouncing)."""
        if not self.spell_checker:
            return
        # Wait 500ms after user stops typing before checking
        self.check_timer.stop()
        self.check_timer.start(500)
    
    def _perform_spell_check(self):
        """Perform spell check on the document."""
        if not self.spell_checker:
            return
        
        # Get the document
        doc = self.document()
        if not doc:
            return
        
        # Get plain text
        text = self.toPlainText()
        if not text:
            return
        
        # Block signals to avoid recursion
        was_blocked = self.signalsBlocked()
        if not was_blocked:
            self.blockSignals(True)
        
        try:
            # First, clear all underlines from the document
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
            
            # Create format without underline
            no_underline_format = QTextCharFormat()
            no_underline_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.NoUnderline)
            cursor.setCharFormat(no_underline_format)
            
            # Extract words and check spelling
            words = self._extract_words_with_positions(text)
            
            # Apply underline to misspelled words
            misspelled_count = 0
            for word, start_pos, end_pos in words:
                if not self._is_word_spelled_correctly(word):
                    misspelled_count += 1
                    # Create cursor for this word
                    word_cursor = QTextCursor(doc)
                    word_cursor.setPosition(start_pos)
                    word_cursor.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)
                    
                    # Apply the misspelled format
                    word_cursor.setCharFormat(self.misspelled_format)
            
            if misspelled_count > 0:
                logger.debug(f"Spell check: Found {misspelled_count} misspelled word(s)")
        finally:
            # Always unblock signals
            if not was_blocked:
                self.blockSignals(False)
    
    def setPlainText(self, text: str):
        """Override to trigger spell check after setting text."""
        super().setPlainText(text)
        if self.spell_checker:
            # Trigger spell check immediately when text is set
            QTimer.singleShot(100, self._perform_spell_check)

    @classmethod
    def _extract_words_with_positions(cls, text: str):
        """Extract words with their positions in the text."""
        import re
        words = []
        for match in re.finditer(r'\b[a-zA-Z]+\b', text):
            word = match.group()
            start_pos = match.start()
            end_pos = match.end()
            words.append((word, start_pos, end_pos))
        return words
    
    def _is_word_spelled_correctly(self, word: str) -> bool:
        """Check if a word is spelled correctly."""
        if not self.spell_checker:
            return True
        
        # Convert to lowercase for checking
        word_lower = word.lower()
        
        # Skip very short words (likely abbreviations or initials)
        if len(word_lower) <= 2:
            return True
        
        # Skip words with numbers or special characters (except apostrophes in contractions)
        if not word_lower.replace("'", "").isalpha():
            return True
        
        # Check if word is in session-ignored list
        if word_lower in self.session_ignored_words:
            return True
        
        # Check spelling with enchant
        try:
            # enchant.Dict.check() returns True if word is correctly spelled
            return self.spell_checker.check(word_lower)
        except Exception:
            # If checking fails, assume it's correct to avoid false positives
            return True
    
    def _show_context_menu(self, position: QPoint):
        """Show context menu with spell suggestions."""
        cursor = self.cursorForPosition(position)
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        word = cursor.selectedText().strip()
        
        # Create context menu
        menu = QMenu(self)
        
        # Check if word is misspelled
        if word and not word.isdigit() and not self._is_word_spelled_correctly(word):
            # Word is misspelled, show suggestions first
            self.current_misspelled_word = word
            self.current_misspelled_start = cursor.selectionStart()
            self.current_misspelled_end = cursor.selectionEnd()
            
            # Get suggestions
            suggestions = self._get_suggestions(word)
            
            if suggestions:
                # Add suggestion actions
                for suggestion in suggestions[:5]:  # Limit to 5 suggestions
                    action = menu.addAction(suggestion)
                    action.triggered.connect(lambda checked, s=suggestion: self._replace_word(s))
            else:
                # No suggestions available
                no_suggestions_action = menu.addAction("No suggestions")
                no_suggestions_action.setEnabled(False)
            
            menu.addSeparator()
            
            # Add "Ignore" option
            ignore_action = menu.addAction("Ignore")
            ignore_action.triggered.connect(self._ignore_word)
            
            # Add "Add to dictionary" option
            add_action = menu.addAction("Add to dictionary")
            add_action.triggered.connect(lambda: self._add_to_dictionary(word))
            
            menu.addSeparator()
        
        # Add standard text edit actions
        cut_action = menu.addAction("Cut")
        cut_action.setEnabled(self.textCursor().hasSelection())
        cut_action.triggered.connect(self.cut)
        
        copy_action = menu.addAction("Copy")
        copy_action.setEnabled(self.textCursor().hasSelection())
        copy_action.triggered.connect(self.copy)
        
        paste_action = menu.addAction("Paste")
        paste_action.triggered.connect(self.paste)
        
        menu.addSeparator()
        
        select_all_action = menu.addAction("Select All")
        select_all_action.triggered.connect(self.selectAll)
        
        menu.exec(self.mapToGlobal(position))
    
    def _get_suggestions(self, word: str) -> list:
        """Get spelling suggestions for a word."""
        if not self.spell_checker:
            return []
        
        try:
            # enchant.Dict.suggest() returns a list of suggestions
            suggestions = self.spell_checker.suggest(word.lower())
            # Return up to 5 suggestions
            return suggestions[:5] if suggestions else []
        except Exception:
            return []
    
    def _replace_word(self, replacement: str):
        """Replace the misspelled word with the selected suggestion."""
        if self.current_misspelled_start < 0 or self.current_misspelled_end < 0:
            return
        
        cursor = QTextCursor(self.document())
        cursor.setPosition(self.current_misspelled_start)
        cursor.setPosition(self.current_misspelled_end, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(replacement)
        
        # Reset
        self.current_misspelled_word = None
        self.current_misspelled_start = -1
        self.current_misspelled_end = -1
    
    def _ignore_word(self):
        """Ignore the misspelled word (temporary, for this session)."""
        if self.current_misspelled_word:
            # Add word to session-ignored set (temporary, lost when widget is destroyed)
            word_lower = self.current_misspelled_word.lower()
            self.session_ignored_words.add(word_lower)
            self._perform_spell_check()  # Refresh highlights
    
    def _add_to_dictionary(self, word: str):
        """Add word to dictionary (permanent)."""
        if self.spell_checker:
            # Add word to personal word list (permanent)
            try:
                self.spell_checker.add(word.lower())
                self._perform_spell_check()  # Refresh highlights
            except Exception as e:
                logger.warning(f"Could not add word to dictionary: {e}")
    

