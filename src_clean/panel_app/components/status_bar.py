"""
Status Bar Component

Provides system status, messages, and basic system information.
"""

import panel as pn
import param
from datetime import datetime

class StatusBar(param.Parameterized):
    """
    Status bar component for the Panel interface.
    
    Provides:
    - Status messages and notifications
    - System information
    - Timestamp display
    - Error/success indicators
    """
    
    def __init__(self, **params):
        super().__init__(**params)
        self.last_update = datetime.now()
        self._create_components()
    
    def _create_components(self):
        """Create the status bar components."""
        # Status message display
        self.status_display = pn.pane.HTML(
            "<span style='color: #2e7d32;'>✅ Ready</span>",
            height=25
        )
        
        # Timestamp display
        self.timestamp_display = pn.pane.HTML(
            f"<span style='color: #666; font-size: 0.85em;'>Last update: {self.last_update.strftime('%H:%M:%S')}</span>",
            height=25
        )
        
        # System info
        self.system_info = pn.pane.HTML(
            "<span style='color: #666; font-size: 0.85em;'>Panel Web Interface | Bokeh Plotting</span>",
            height=25
        )
    
    @property
    def panel(self):
        """Return the Panel layout."""
        return pn.Row(
            self.status_display,
            pn.Spacer(),
            self.system_info,
            pn.Spacer(width=20),
            self.timestamp_display,
            height=35,
            margin=(0, 0),
            sizing_mode='stretch_width',
            styles={'background': '#f5f5f5'}
        )
    
    def update_status(self, message: str, status_type: str = "info"):
        """
        Update status message with optional type styling.
        
        Args:
            message: Status message to display
            status_type: Type of message ('info', 'success', 'warning', 'error')
        """
        self.last_update = datetime.now()
        
        # Choose icon and color based on status type
        if status_type == "success":
            icon = "✅"
            color = "#2e7d32"
        elif status_type == "warning":
            icon = "⚠️"
            color = "#f57c00"
        elif status_type == "error":
            icon = "❌"
            color = "#d32f2f"
        else:  # info
            icon = "ℹ️"
            color = "#1976d2"
        
        # Update status display
        self.status_display.object = f"<span style='color: {color};'>{icon} {message}</span>"
        
        # Update timestamp
        self.timestamp_display.object = f"<span style='color: #666; font-size: 0.85em;'>Last update: {self.last_update.strftime('%H:%M:%S')}</span>"
    
    def clear_status(self):
        """Clear status message to default."""
        self.update_status("Ready", "success")