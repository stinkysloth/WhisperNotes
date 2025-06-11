"""
Audio level meter widget.

This module provides a visual audio level meter widget that can be used to display
audio input levels in real-time.
"""

import math
from typing import Optional, Tuple

from PySide6.QtCore import Qt, QTimer, QSize, QRectF
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPaintEvent, QPalette, QPen
from PySide6.QtWidgets import QWidget, QSizePolicy

class AudioMeter(QWidget):
    """A widget that displays audio level meters."""
    
    # Default colors
    DEFAULT_COLORS = {
        'background': QColor(50, 50, 50),
        'border': QColor(100, 100, 100),
        'level_low': QColor(0, 200, 0),      # Green
        'level_med': QColor(255, 200, 0),     # Yellow
        'level_high': QColor(255, 0, 0),      # Red
        'tick': QColor(200, 200, 200, 150),   # Semi-transparent white
        'text': Qt.white
    }
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        orientation: Qt.Orientation = Qt.Horizontal,
        min_value: float = -60.0,
        max_value: float = 0.0,
        warn_threshold: float = -12.0,
        crit_threshold: float = -6.0,
        show_ticks: bool = True,
        show_labels: bool = True,
        show_peak: bool = True,
        peak_hold_time: int = 1000  # ms
    ):
        """Initialize the audio meter widget.
        
        Args:
            parent: Parent widget
            orientation: Orientation of the meter (Horizontal or Vertical)
            min_value: Minimum value in dB
            max_value: Maximum value in dB (usually 0 dB)
            warn_threshold: Warning threshold in dB (yellow zone starts here)
            crit_threshold: Critical threshold in dB (red zone starts here)
            show_ticks: Whether to show tick marks
            show_labels: Whether to show value labels
            show_peak: Whether to show peak hold indicator
            peak_hold_time: How long to hold peak values in milliseconds
        """
        super().__init__(parent)
        
        # Store parameters
        self.orientation = orientation
        self.min_value = min_value
        self.max_value = max_value
        self.warn_threshold = warn_threshold
        self.crit_threshold = crit_threshold
        self.show_ticks = show_ticks
        self.show_labels = show_labels
        self.show_peak = show_peak
        self.peak_hold_time = peak_hold_time
        
        # Current and peak levels
        self.level = self.min_value
        self.peak = self.min_value
        self.peak_timer = QTimer(self)
        self.peak_timer.timeout.connect(self._on_peak_timeout)
        
        # Colors
        self.colors = self.DEFAULT_COLORS.copy()
        
        # Set size policy
        if self.orientation == Qt.Horizontal:
            self.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred
            )
            self.setMinimumHeight(24)
        else:
            self.setSizePolicy(
                QSizePolicy.Policy.Preferred,
                QSizePolicy.Policy.Expanding
            )
            self.setMinimumWidth(24)
    
    def set_level(self, value: float) -> None:
        """Set the current level in dB.
        
        Args:
            value: Level in dB (should be between min_value and max_value)
        """
        # Clamp the value to valid range
        value = max(self.min_value, min(self.max_value, value))
        
        # Update level
        self.level = value
        
        # Update peak if needed
        if value > self.peak:
            self.peak = value
            if self.peak_hold_time > 0:
                self.peak_timer.stop()
                self.peak_timer.start(self.peak_hold_time)
        
        # Request repaint
        self.update()
    
    def set_peak_hold_time(self, ms: int) -> None:
        """Set the peak hold time in milliseconds.
        
        Args:
            ms: Time in milliseconds (0 to disable peak hold)
        """
        self.peak_hold_time = max(0, ms)
    
    def reset_peak(self) -> None:
        """Reset the peak level to minimum."""
        self.peak = self.min_value
        self.update()
    
    def set_color(self, role: str, color: QColor) -> None:
        """Set a color for the specified role.
        
        Args:
            role: Color role ('background', 'border', 'level_low', 'level_med', 
                  'level_high', 'tick', 'text')
            color: QColor to use
        """
        if role in self.colors:
            self.colors[role] = color
            self.update()
    
    def sizeHint(self) -> QSize:
        """Return the recommended size for the widget."""
        if self.orientation == Qt.Horizontal:
            return QSize(200, 24)
        else:
            return QSize(24, 200)
    
    def minimumSizeHint(self) -> QSize:
        """Return the minimum size for the widget."""
        if self.orientation == Qt.Horizontal:
            return QSize(50, 16)
        else:
            return QSize(16, 50)
    
    def paintEvent(self, event: QPaintEvent) -> None:
        """Handle paint events."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get widget dimensions
        rect = self.rect()
        width = rect.width()
        height = rect.height()
        
        # Draw background
        painter.fillRect(rect, self.colors['background'])
        
        # Draw level meter
        self._draw_level_meter(painter, rect)
        
        # Draw ticks and labels if enabled
        if self.show_ticks:
            self._draw_ticks(painter, rect)
        
        # Draw border
        pen = QPen(self.colors['border'])
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect.adjusted(0, 0, -1, -1))
    
    def _draw_level_meter(self, painter: QPainter, rect: QRectF) -> None:
        """Draw the level meter.
        
        Args:
            painter: QPainter to use for drawing
            rect: Bounding rectangle for the meter
        """
        # Calculate level position (0.0 to 1.0)
        level_pos = self._value_to_pos(self.level)
        
        # Create gradient for the level meter
        if self.orientation == Qt.Horizontal:
            gradient = QLinearGradient(rect.left(), 0, rect.right(), 0)
        else:
            gradient = QLinearGradient(0, rect.bottom(), 0, rect.top())
        
        # Add color stops based on thresholds
        low_pos = self._value_to_pos(self.warn_threshold)
        med_pos = self._value_to_pos(self.crit_threshold)
        
        gradient.setColorAt(0.0, self.colors['level_low'])
        gradient.setColorAt(low_pos, self.colors['level_low'])
        gradient.setColorAt(med_pos, self.colors['level_med'])
        gradient.setColorAt(1.0, self.colors['level_high'])
        
        # Draw the level bar
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        
        if self.orientation == Qt.Horizontal:
            level_rect = QRectF(
                rect.left(),
                rect.top(),
                rect.width() * level_pos,
                rect.height()
            )
        else:
            level_rect = QRectF(
                rect.left(),
                rect.bottom() - rect.height() * level_pos,
                rect.width(),
                rect.height() * level_pos
            )
        
        painter.drawRect(level_rect)
        
        # Draw peak indicator if enabled
        if self.show_peak and self.peak > self.min_value:
            peak_pos = self._value_to_pos(self.peak)
            pen = QPen(self.colors['text'])
            pen.setWidth(1)
            painter.setPen(pen)
            
            if self.orientation == Qt.Horizontal:
                x = rect.left() + rect.width() * peak_pos
                painter.drawLine(x, rect.top(), x, rect.bottom())
            else:
                y = rect.bottom() - rect.height() * peak_pos
                painter.drawLine(rect.left(), y, rect.right(), y)
    
    def _draw_ticks(self, painter: QPainter, rect: QRectF) -> None:
        """Draw tick marks and labels.
        
        Args:
            painter: QPainter to use for drawing
            rect: Bounding rectangle for the meter
        """
        # Set up pen for ticks
        pen = QPen(self.colors['tick'])
        pen.setWidth(1)
        painter.setPen(pen)
        
        # Set up font for labels
        font = painter.font()
        font.setPointSize(max(6, font.pointSize() - 2))
        painter.setFont(font)
        
        # Draw ticks at major intervals (every 10 dB)
        tick_values = range(
            int(math.ceil(self.min_value / 10.0)) * 10,
            int(math.floor(self.max_value / 10.0)) * 10 + 1,
            10
        )
        
        for value in tick_values:
            # Skip if outside range
            if value < self.min_value or value > self.max_value:
                continue
            
            # Calculate position
            pos = self._value_to_pos(value)
            
            # Draw tick mark
            if self.orientation == Qt.Horizontal:
                x = rect.left() + rect.width() * pos
                painter.drawLine(x, rect.bottom() - 5, x, rect.bottom())
                
                # Draw label
                if self.show_labels:
                    text = f"{value}dB" if value != 0 else "0dB"
                    text_rect = QRectF(x - 20, rect.top(), 40, 15)
                    painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)
            else:
                y = rect.bottom() - rect.height() * pos
                painter.drawLine(rect.left(), y, rect.left() + 5, y)
                
                # Draw label
                if self.show_labels:
                    text = f"{value}dB" if value != 0 else "0dB"
                    text_rect = QRectF(rect.left() + 7, y - 7, 30, 14)
                    painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
    
    def _value_to_pos(self, value: float) -> float:
        """Convert a dB value to a position (0.0 to 1.0).
        
        Args:
            value: Value in dB
            
        Returns:
            Position in range [0.0, 1.0]
        """
        # Clamp value to valid range
        value = max(self.min_value, min(self.max_value, value))
        
        # Convert from dB to linear scale (0.0 to 1.0)
        # Using a logarithmic scale for better visual representation
        if value <= self.min_value:
            return 0.0
            
        # Convert from dB to position using a logarithmic scale
        db_range = self.max_value - self.min_value
        pos = (value - self.min_value) / db_range
        
        # Apply a slight curve to make the meter more responsive at lower levels
        pos = math.pow(pos, 0.7)
        
        return pos
    
    @Slot()
    def _on_peak_timeout(self) -> None:
        """Handle peak hold timer timeout."""
        self.peak = self.min_value
        self.peak_timer.stop()
        self.update()
