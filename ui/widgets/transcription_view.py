"""
Transcription view widget.

This module provides a widget for displaying and managing transcriptions.
"""

import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from PySide6.QtCore import Qt, Signal, Slot, QSize, QTimer, QMimeData, QUrl
from PySide6.QtGui import (
    QTextCharFormat, QTextCursor, QTextDocument, QTextFormat,
    QFont, QColor, QTextBlockFormat, QTextLength, QAction,
    QPalette, QDragEnterEvent, QDropEvent, QKeySequence, QIcon
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QMenu, QFileDialog, QMessageBox, QScrollBar, QApplication,
    QLabel, QToolBar, QComboBox, QSpinBox, QSizePolicy
)

from core.constants import AppConstants
from utils.file_utils import ensure_directory_exists

logger = logging.getLogger(__name__)

class TranscriptionView(QWidget):
    """A widget for displaying and managing transcriptions."""
    
    # Signals
    text_cleared = Signal()
    text_modified = Signal()
    text_exported = Signal(str)  # path to exported file
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the transcription view.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # UI state
        self._is_modified = False
        self._file_path = None
        self._auto_scroll = True
        self._font_size = 10
        self._line_height = 1.2
        self._dark_mode = False
        
        # Initialize UI
        self._init_ui()
        self._setup_actions()
        self._setup_shortcuts()
        
        # Set default style
        self._update_style()
    
    def _init_ui(self) -> None:
        """Initialize the user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create toolbar
        self.toolbar = QToolBar("Transcription Toolbar")
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        layout.addWidget(self.toolbar)
        
        # Create text edit
        self.text_edit = QTextEdit()
        self.text_edit.setAcceptRichText(True)
        self.text_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.text_edit.setReadOnly(False)
        self.text_edit.setUndoRedoEnabled(True)
        self.text_edit.setAcceptDrops(True)
        self.text_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.text_edit.customContextMenuRequested.connect(self._show_context_menu)
        
        # Set up document
        self.text_edit.document().setDocumentMargin(10)
        self.text_edit.document().modificationChanged.connect(self._on_modification_changed)
        
        # Set up scroll bar policy
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Connect text changed signal
        self.text_edit.textChanged.connect(self._on_text_changed)
        
        # Add to layout
        layout.addWidget(self.text_edit)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        
        # Status labels
        self.status_label = QLabel("Ready")
        self.word_count_label = QLabel("Words: 0")
        self.char_count_label = QLabel("Chars: 0")
        
        # Add widgets to status bar
        self.status_bar.addWidget(self.status_label, 1)
        self.status_bar.addPermanentWidget(self.word_count_label)
        self.status_bar.addPermanentWidget(self.char_count_label)
        
        # Add status bar to layout
        layout.addWidget(self.status_bar)
        
        # Set up auto-scroll timer
        self.auto_scroll_timer = QTimer(self)
        self.auto_scroll_timer.timeout.connect(self._check_auto_scroll)
        self.auto_scroll_timer.start(100)  # Check every 100ms
    
    def _setup_actions(self) -> None:
        """Set up actions for the toolbar and context menu."""
        # File actions
        self.new_action = QAction("&New", self)
        self.new_action.setShortcut(QKeySequence.StandardKey.New)
        self.new_action.setStatusTip("Create a new document")
        self.new_action.triggered.connect(self.new_document)
        
        self.open_action = QAction("&Open...", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.setStatusTip("Open an existing document")
        self.open_action.triggered.connect(self.open_document)
        
        self.save_action = QAction("&Save", self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.setStatusTip("Save the current document")
        self.save_action.triggered.connect(self.save_document)
        
        self.save_as_action = QAction("Save &As...", self)
        self.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.save_as_action.setStatusTip("Save the current document with a new name")
        self.save_as_action.triggered.connect(lambda: self.save_document(save_as=True))
        
        self.export_action = QAction("&Export...", self)
        self.export_action.setStatusTip("Export the current document to another format")
        self.export_action.triggered.connect(self.export_document)
        
        self.clear_action = QAction("C&lear", self)
        self.clear_action.setStatusTip("Clear the current document")
        self.clear_action.triggered.connect(self.clear_document)
        
        # Edit actions
        self.undo_action = QAction("&Undo", self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.setStatusTip("Undo the last action")
        self.undo_action.triggered.connect(self.text_edit.undo)
        
        self.redo_action = QAction("&Redo", self)
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.setStatusTip("Redo the last undone action")
        self.redo_action.triggered.connect(self.text_edit.redo)
        
        self.cut_action = QAction("Cu&t", self)
        self.cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        self.cut_action.setStatusTip("Cut the selected text")
        self.cut_action.triggered.connect(self.text_edit.cut)
        
        self.copy_action = QAction("&Copy", self)
        self.copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        self.copy_action.setStatusTip("Copy the selected text")
        self.copy_action.triggered.connect(self.text_edit.copy)
        
        self.paste_action = QAction("&Paste", self)
        self.paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        self.paste_action.setStatusTip("Paste the clipboard's content")
        self.paste_action.triggered.connect(self.text_edit.paste)
        
        self.select_all_action = QAction("Select &All", self)
        self.select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        self.select_all_action.setStatusTip("Select all text")
        self.select_all_action.triggered.connect(self.text_edit.selectAll)
        
        # Format actions
        self.bold_action = QAction("&Bold", self)
        self.bold_action.setShortcut(QKeySequence("Ctrl+B"))
        self.bold_action.setCheckable(True)
        self.bold_action.setStatusTip("Make the selected text bold")
        self.bold_action.triggered.connect(self._toggle_bold)
        
        self.italic_action = QAction("&Italic", self)
        self.italic_action.setShortcut(QKeySequence("Ctrl+I"))
        self.italic_action.setCheckable(True)
        self.italic_action.setStatusTip("Make the selected text italic")
        self.italic_action.triggered.connect(self._toggle_italic)
        
        self.underline_action = QAction("&Underline", self)
        self.underline_action.setShortcut(QKeySequence("Ctrl+U"))
        self.underline_action.setCheckable(True)
        self.underline_action.setStatusTip("Underline the selected text")
        self.underline_action.triggered.connect(self._toggle_underline)
        
        # View actions
        self.zoom_in_action = QAction("Zoom &In", self)
        self.zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        self.zoom_in_action.setStatusTip("Zoom in")
        self.zoom_in_action.triggered.connect(self.zoom_in)
        
        self.zoom_out_action = QAction("Zoom &Out", self)
        self.zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        self.zoom_out_action.setStatusTip("Zoom out")
        self.zoom_out_action.triggered.connect(self.zoom_out)
        
        self.zoom_reset_action = QAction("Reset &Zoom", self)
        self.zoom_reset_action.setShortcut(QKeySequence("Ctrl+0"))
        self.zoom_reset_action.setStatusTip("Reset zoom level")
        self.zoom_reset_action.triggered.connect(self.zoom_reset)
        
        # Add actions to toolbar
        self.toolbar.addAction(self.new_action)
        self.toolbar.addAction(self.open_action)
        self.toolbar.addAction(self.save_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.undo_action)
        self.toolbar.addAction(self.redo_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.cut_action)
        self.toolbar.addAction(self.copy_action)
        self.toolbar.addAction(self.paste_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.bold_action)
        self.toolbar.addAction(self.italic_action)
        self.toolbar.addAction(self.underline_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.zoom_in_action)
        self.toolbar.addAction(self.zoom_out_action)
        self.toolbar.addAction(self.zoom_reset_action)
        
        # Update action states
        self._update_action_states()
    
    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts."""
        # Add shortcuts that aren't handled by actions
        self.text_edit.keyPressEvent = self._on_key_press
    
    def _update_action_states(self) -> None:
        """Update the enabled/disabled state of actions."""
        # Update edit actions based on document state
        self.undo_action.setEnabled(self.text_edit.document().isUndoAvailable())
        self.redo_action.setEnabled(self.text_edit.document().isRedoAvailable())
        
        # Update format actions based on current text format
        cursor = self.text_edit.textCursor()
        char_format = cursor.charFormat()
        
        self.bold_action.setChecked(char_format.fontWeight() > QFont.Weight.Normal)
        self.italic_action.setChecked(char_format.fontItalic())
        self.underline_action.setChecked(char_format.fontUnderline())
        
        # Update copy/cut based on selection
        has_selection = cursor.hasSelection()
        self.copy_action.setEnabled(has_selection)
        self.cut_action.setEnabled(has_selection)
        
        # Update paste based on clipboard
        self.paste_action.setEnabled(bool(QApplication.clipboard().text()))
    
    def _update_style(self) -> None:
        """Update the widget's style based on the current theme."""
        if self._dark_mode:
            # Dark theme
            self.setStyleSheet("""
                QTextEdit {
                    background-color: #2b2b2b;
                    color: #e0e0e0;
                    border: 1px solid #3a3a3a;
                    selection-background-color: #3d6e99;
                }
                QStatusBar {
                    background-color: #2b2b2b;
                    color: #a0a0a0;
                    border-top: 1px solid #3a3a3a;
                }
            """)
        else:
            # Light theme
            self.setStyleSheet("""
                QTextEdit {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #c0c0c0;
                    selection-background-color: #a8d1ff;
                }
                QStatusBar {
                    background-color: #f0f0f0;
                    color: #505050;
                    border-top: 1px solid #c0c0c0;
                }
            """)
    
    def _update_status_bar(self) -> None:
        """Update the status bar with document statistics."""
        # Get document text
        text = self.text_edit.toPlainText()
        
        # Count words and characters
        word_count = len(text.split())
        char_count = len(text)
        
        # Update labels
        self.word_count_label.setText(f"Words: {word_count}")
        self.char_count_label.setText(f"Chars: {char_count}")
        
        # Update status message
        if self._file_path:
            self.status_label.setText(f"{self._file_path} - 
{'*' if self._is_modified else ''}")
        else:
            self.status_label.setText("Untitled" + ("*" if self._is_modified else ""))
    
    def _show_context_menu(self, position) -> None:
        """Show the context menu at the given position.
        
        Args:
            position: Position to show the menu at
        """
        menu = QMenu()
        
        # Add edit actions
        menu.addAction(self.undo_action)
        menu.addAction(self.redo_action)
        menu.addSeparator()
        menu.addAction(self.cut_action)
        menu.addAction(self.copy_action)
        menu.addAction(self.paste_action)
        menu.addSeparator()
        menu.addAction(self.select_all_action)
        
        # Show the menu
        menu.exec_(self.text_edit.viewport().mapToGlobal(position))
    
    def _on_text_changed(self) -> None:
        """Handle text changed signal."""
        self._is_modified = True
        self._update_status_bar()
        self.text_modified.emit()
    
    def _on_modification_changed(self, changed: bool) -> None:
        """Handle document modification changed signal.
        
        Args:
            changed: Whether the document has been modified
        """
        self._is_modified = changed
        self._update_status_bar()
    
    def _on_key_press(self, event) -> None:
        """Handle key press events.
        
        Args:
            event: Key press event
        """
        # Handle tab key for indentation
        if event.key() == Qt.Key.Key_Tab:
            cursor = self.text_edit.textCursor()
            cursor.insertText("    ")  # 4 spaces
            return
        
        # Call the base class implementation for other keys
        QTextEdit.keyPressEvent(self.text_edit, event)
        
        # Update action states after key press
        self._update_action_states()
    
    def _toggle_bold(self) -> None:
        """Toggle bold formatting for the selected text."""
        cursor = self.text_edit.textCursor()
        fmt = QTextCharFormat()
        
        if self.bold_action.isChecked():
            fmt.setFontWeight(QFont.Weight.Bold)
        else:
            fmt.setFontWeight(QFont.Weight.Normal)
        
        cursor.mergeCharFormat(fmt)
        self.text_edit.setFocus()
    
    def _toggle_italic(self) -> None:
        """Toggle italic formatting for the selected text."""
        cursor = self.text_edit.textCursor()
        fmt = QTextCharFormat()
        fmt.setFontItalic(self.italic_action.isChecked())
        cursor.mergeCharFormat(fmt)
        self.text_edit.setFocus()
    
    def _toggle_underline(self) -> None:
        """Toggle underline formatting for the selected text."""
        cursor = self.text_edit.textCursor()
        fmt = QTextCharFormat()
        fmt.setFontUnderline(self.underline_action.isChecked())
        cursor.mergeCharFormat(fmt)
        self.text_edit.setFocus()
    
    def _check_auto_scroll(self) -> None:
        """Check if auto-scroll should be performed."""
        if not self._auto_scroll:
            return
            
        # Get the scroll bar
        scroll_bar = self.text_edit.verticalScrollBar()
        
        # If scroll bar is at the bottom, scroll to bottom
        if scroll_bar.value() >= scroll_bar.maximum() - 10:  # Small threshold
            self.text_edit.ensureCursorVisible()
    
    # Public methods
    def clear_document(self) -> None:
        """Clear the current document."""
        if self._is_modified:
            # Ask for confirmation if there are unsaved changes
            reply = QMessageBox.question(
                self,
                "Clear Document",
                "The document has been modified. Are you sure you want to clear it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Clear the document
        self.text_edit.clear()
        self._file_path = None
        self._is_modified = False
        self.text_edit.document().setModified(False)
        self._update_status_bar()
        
        # Emit signal
        self.text_cleared.emit()
    
    def new_document(self) -> None:
        """Create a new document."""
        self.clear_document()
    
    def open_document(self, file_path: Optional[str] = None) -> bool:
        """Open a document from a file.
        
        Args:
            file_path: Path to the file to open. If None, a file dialog will be shown.
            
        Returns:
            bool: True if the file was opened successfully, False otherwise
        """
        # If no file path is provided, show a file dialog
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Open Document",
                "",
                "Text Files (*.txt);;Markdown Files (*.md);;All Files (*)"
            )
            
            if not file_path:
                return False
        
        try:
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Set the document content
            self.text_edit.setPlainText(content)
            
            # Update state
            self._file_path = file_path
            self._is_modified = False
            self.text_edit.document().setModified(False)
            self._update_status_bar()
            
            return True
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open file: {str(e)}"
            )
            return False
    
    def save_document(self, save_as: bool = False) -> bool:
        """Save the current document to a file.
        
        Args:
            save_as: If True, always show the save dialog
            
        Returns:
            bool: True if the file was saved successfully, False otherwise
        """
        # If we don't have a file path or save_as is True, show the save dialog
        if not self._file_path or save_as:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Document",
                self._file_path or "",
                "Text Files (*.txt);;Markdown Files (*.md);;All Files (*)"
            )
            
            if not file_path:
                return False
                
            self._file_path = file_path
        
        try:
            # Write the file
            with open(self._file_path, 'w', encoding='utf-8') as f:
                f.write(self.text_edit.toPlainText())
            
            # Update state
            self._is_modified = False
            self.text_edit.document().setModified(False)
            self._update_status_bar()
            
            return True
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save file: {str(e)}"
            )
            return False
    
    def export_document(self) -> None:
        """Export the current document to another format."""
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Document",
            "",
            "HTML Files (*.html);;PDF Files (*.pdf);;ODT Files (*.odt)"
        )
        
        if not file_path:
            return
        
        try:
            if file_path.lower().endswith('.html') or 'HTML' in selected_filter:
                self._export_to_html(file_path)
            elif file_path.lower().endswith('.pdf') or 'PDF' in selected_filter:
                self._export_to_pdf(file_path)
            elif file_path.lower().endswith('.odt') or 'ODT' in selected_filter:
                self._export_to_odt(file_path)
            else:
                raise ValueError("Unsupported file format")
            
            # Emit signal
            self.text_exported.emit(file_path)
            
            # Show success message
            QMessageBox.information(
                self,
                "Export Successful",
                f"Document exported successfully to:\n{file_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export document: {str(e)}"
            )
    
    def _export_to_html(self, file_path: str) -> None:
        """Export the document to HTML format.
        
        Args:
            file_path: Path to save the HTML file
        """
        # Get the HTML content
        html = self.text_edit.toHtml()
        
        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html)
    
    def _export_to_pdf(self, file_path: str) -> None:
        """Export the document to PDF format.
        
        Args:
            file_path: Path to save the PDF file
        """
        from PySide6.QtPrintSupport import QPrinter
        
        # Create a printer
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(file_path)
        
        # Set page size and margins
        printer.setPageSize(QPrinter.PageSize.Letter)
        printer.setPageMargins(25, 25, 25, 25, QPrinter.Unit.Millimeter)
        
        # Print the document
        self.text_edit.document().print_(printer)
    
    def _export_to_odt(self, file_path: str) -> None:
        """Export the document to ODT format.
        
        Args:
            file_path: Path to save the ODT file
        """
        from PySide6.QtGui import QTextDocumentWriter
        
        # Create a document writer
        writer = QTextDocumentWriter(file_path)
        writer.setFormat(b"ODF")  # ODF format for ODT
        
        # Write the document
        if not writer.write(self.text_edit.document()):
            raise RuntimeError("Failed to write ODT file")
    
    def append_text(self, text: str, move_cursor: bool = True) -> None:
        """Append text to the document.
        
        Args:
            text: Text to append
            move_cursor: If True, move the cursor to the end after appending
        """
        # Save the current cursor position
        cursor = self.text_edit.textCursor()
        at_bottom = cursor.atEnd()
        
        # Move to the end
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # Add a newline if the document is not empty
        if not cursor.atStart():
            cursor.insertText("\n\n")
        
        # Insert the text
        cursor.insertText(text)
        
        # Move the cursor to the end if needed
        if move_cursor or at_bottom:
            self.text_edit.setTextCursor(cursor)
        
        # Auto-scroll if at bottom
        if at_bottom and self._auto_scroll:
            self.text_edit.ensureCursorVisible()
    
    def set_auto_scroll(self, enabled: bool) -> None:
        """Enable or disable auto-scrolling.
        
        Args:
            enabled: Whether to enable auto-scrolling
        """
        self._auto_scroll = enabled
    
    def zoom_in(self, delta: int = 1) -> None:
        """Zoom in the text.
        
        Args:
            delta: Number of points to increase the font size by
        """
        self._font_size += delta
        self._update_font()
    
    def zoom_out(self, delta: int = 1) -> None:
        """Zoom out the text.
        
        Args:
            delta: Number of points to decrease the font size by
        """
        self._font_size = max(6, self._font_size - delta)
        self._update_font()
    
    def zoom_reset(self) -> None:
        """Reset the zoom level to the default."""
        self._font_size = 10
        self._update_font()
    
    def _update_font(self) -> None:
        """Update the font size and line height."""
        font = self.text_edit.font()
        font.setPointSize(self._font_size)
        self.text_edit.setFont(font)
        
        # Update line height
        block_format = QTextBlockFormat()
        block_format.setLineHeight(
            int(self._font_size * self._line_height * 10),
            QTextBlockFormat.LineHeightType.FixedHeight
        )
        
        cursor = self.text_edit.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.mergeBlockFormat(block_format)
        cursor.clearSelection()
    
    def set_dark_mode(self, enabled: bool) -> None:
        """Enable or disable dark mode.
        
        Args:
            enabled: Whether to enable dark mode
        """
        self._dark_mode = enabled
        self._update_style()
    
    def is_modified(self) -> bool:
        """Check if the document has been modified.
        
        Returns:
            bool: True if modified, False otherwise
        """
        return self._is_modified
    
    def get_text(self) -> str:
        """Get the current text content.
        
        Returns:
            str: The document text
        """
        return self.text_edit.toPlainText()
    
    def set_text(self, text: str) -> None:
        """Set the text content.
        
        Args:
            text: Text to set
        """
        self.text_edit.setPlainText(text)
    
    def get_file_path(self) -> Optional[str]:
        """Get the current file path.
        
        Returns:
            Optional[str]: The current file path, or None if not saved
        """
        return self._file_path
    
    def set_file_path(self, path: str) -> None:
        """Set the current file path.
        
        Args:
            path: New file path
        """
        self._file_path = path
        self._update_status_bar()
    
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter events.
        
        Args:
            event: Drag enter event
        """
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop events.
        
        Args:
            event: Drop event
        """
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path:
                    self.open_document(file_path)
                    event.acceptProposedAction()
                    return
        
        event.ignore()


class StatusBar(QWidget):
    """Custom status bar implementation."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the status bar.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(10)
        
        # Status label (takes remaining space)
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # Word count label
        self.word_count_label = QLabel("Words: 0")
        self.word_count_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        # Character count label
        self.char_count_label = QLabel("Chars: 0")
        self.char_count_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        # Add widgets to layout
        layout.addWidget(self.status_label, 1)
        layout.addWidget(self.word_count_label)
        layout.addWidget(self.char_count_label)
        
        # Set size policy
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )
    
    def set_status_text(self, text: str) -> None:
        """Set the status text.
        
        Args:
            text: Status text to display
        """
        self.status_label.setText(text)
    
    def set_word_count(self, count: int) -> None:
        """Set the word count.
        
        Args:
            count: Number of words
        """
        self.word_count_label.setText(f"Words: {count}")
    
    def set_char_count(self, count: int) -> None:
        """Set the character count.
        
        Args:
            count: Number of characters
        """
        self.char_count_label.setText(f"Chars: {count}")
