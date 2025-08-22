"""
Professional Status Bar Component - Integrated Status System

Clean, integrated status display with professional styling and real-time updates.
"""

import panel as pn
import param
from datetime import datetime

class StatusBar(param.Parameterized):
    """
    Professional status bar component with integrated design.

    Features:
    - Real-time status updates
    - Professional color coding
    - System information display
    - Timestamp tracking
    - Clean integration with main interface
    """

    def __init__(self, **params):
        super().__init__(**params)
        self.last_update = datetime.now()
        self._create_components()

    def _create_components(self):
        """Create professional status components."""
        # Main status display
        self.status_display = pn.pane.HTML(
            """<div style='background: #E8F5E8; color: #2E7D32; padding: 10px 20px; 
                          border-radius: 6px; border-left: 4px solid #2E7D32;
                          display: flex; align-items: center;'>
               <span style='margin-right: 10px;'>✅</span>
               <span style='font-weight: 500;'>Electrochemical Analysis Suite Ready</span>
               <span style='margin-left: auto; font-size: 12px; opacity: 0.8;'>
                   {time}
               </span>
               </div>""".format(time=self.last_update.strftime('%H:%M:%S')),
            margin=(5, 0)
        )

        # System information
        self.system_info = pn.pane.HTML(
            """<div style='color: #666; font-size: 12px; text-align: right; 
                          padding: 5px 20px; font-style: italic;'>
               Panel Web Interface • HoloViews Plotting • Polars Data Processing
               </div>""",
            margin=(0, 0)
        )

    @property
    def panel(self):
        """Return professional status bar layout."""
        return pn.Column(
            pn.Row(
                self.status_display,
                sizing_mode='stretch_width'
            ),
            self.system_info,
            styles={
                'background': 'white',
                'border-top': '1px solid #E0E0E0',
                'margin': '0'
            },
            margin=(0, 0),
            sizing_mode='stretch_width'
        )

    def update_status(self, message: str, status_type: str = "info"):
        """
        Update status with professional styling.

        Args:
            message: Status message to display
            status_type: Type ('success', 'warning', 'error', 'info', 'processing')
        """
        self.last_update = datetime.now()

        # Professional status styling
        status_configs = {
            "success": {
                "icon": "✅",
                "color": "#2E7D32",
                "bg_color": "#E8F5E8",
                "border_color": "#2E7D32"
            },
            "warning": {
                "icon": "⚠️",
                "color": "#F57C00",
                "bg_color": "#FFF3E0",
                "border_color": "#F57C00"
            },
            "error": {
                "icon": "❌",
                "color": "#D32F2F",
                "bg_color": "#FFEBEE",
                "border_color": "#D32F2F"
            },
            "processing": {
                "icon": "🔄",
                "color": "#1976D2",
                "bg_color": "#E3F2FD",
                "border_color": "#1976D2"
            },
            "info": {
                "icon": "ℹ️",
                "color": "#1976D2",
                "bg_color": "#E3F2FD",
                "border_color": "#1976D2"
            }
        }

        config = status_configs.get(status_type, status_configs["info"])

        # Update status display with animation-ready styling
        self.status_display.object = f"""
        <div style='background: {config["bg_color"]}; color: {config["color"]}; 
                    padding: 10px 20px; border-radius: 6px; 
                    border-left: 4px solid {config["border_color"]};
                    display: flex; align-items: center; transition: all 0.3s ease;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
            <span style='margin-right: 10px; font-size: 16px;'>{config["icon"]}</span>
            <span style='font-weight: 500; flex: 1;'>{message}</span>
            <span style='font-size: 11px; opacity: 0.8; margin-left: 15px;'>
                {self.last_update.strftime('%H:%M:%S')}
            </span>
        </div>
        """

    def update_processing(self, message: str, progress: float = None):
        """
        Update with processing status and optional progress.

        Args:
            message: Processing message
            progress: Optional progress value (0-100)
        """
        progress_bar = ""
        if progress is not None:
            progress_bar = f"""
            <div style='width: 100%; background: rgba(255,255,255,0.3); 
                        border-radius: 10px; height: 4px; margin-top: 5px;'>
                <div style='width: {progress}%; background: #1976D2; 
                           border-radius: 10px; height: 4px; transition: width 0.3s ease;'></div>
            </div>
            """

        self.last_update = datetime.now()

        self.status_display.object = f"""
        <div style='background: #E3F2FD; color: #1976D2; padding: 10px 20px; 
                    border-radius: 6px; border-left: 4px solid #1976D2;
                    display: flex; flex-direction: column; transition: all 0.3s ease;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
            <div style='display: flex; align-items: center;'>
                <span style='margin-right: 10px; font-size: 16px;'>🔄</span>
                <span style='font-weight: 500; flex: 1;'>{message}</span>
                <span style='font-size: 11px; opacity: 0.8; margin-left: 15px;'>
                    {self.last_update.strftime('%H:%M:%S')}
                </span>
            </div>
            {progress_bar}
        </div>
        """

    def clear_status(self):
        """Clear status to ready state."""
        self.update_status("Ready", "success")

    def show_system_stats(self, stats: dict):
        """
        Show system statistics in status area.

        Args:
            stats: Dictionary with system stats (cells, files, etc.)
        """
        cells_count = stats.get('cells', 0)
        files_count = stats.get('files', 0)

        message = f"System: {cells_count} cells, {files_count} files processed"
        self.update_status(message, "info")

    def show_file_stats(self, file_id: str, data_points: int, segments: int):
        """
        Show file statistics.

        Args:
            file_id: File identifier
            data_points: Number of data points
            segments: Number of segments
        """
        message = f"Loaded: {data_points:,} points, {segments} segments"
        self.update_status(message, "success")