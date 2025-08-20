"""
Professional Main Panel Application - Clean Scientific Interface

Modern, professional interface for electrochemical data analysis with proper visual hierarchy,
card-based design, and scientific color scheme.
"""

import panel as pn
import param
from pathlib import Path

# Import your backend and components (update paths as needed)
from src_clean.backend import get_backend_api
from .components import CellManager, FileUploader, DataViewer, StatusBar, GroupManagementTab
class ElectrochemicalApp(param.Parameterized):
    """
    Professional Panel application for electrochemical data analysis.

    Features:
    - Modern card-based design
    - Professional scientific color scheme
    - Clean component separation
    - Responsive layout
    - Integrated status system
    """

    current_cell = param.String(default="", doc="Currently selected cell")
    current_file = param.String(default="", doc="Currently selected file")

    def __init__(self, **params):
        super().__init__(**params)

        # Configure Panel theme
        self._configure_panel_styling()

        # Initialize backend
        self.api = get_backend_api()

        # Create professional components
        self.cell_manager = CellManager(api=self.api)
        self.file_uploader = FileUploader(api=self.api)
        self.data_viewer = DataViewer(api=self.api)
        self.status_bar = self._create_status_bar()
        self.group_management_tab = GroupManagementTab(api=self.api)

        # Setup component connections
        self._setup_connections()

        # Create professional layout
        self._create_layout()

    def _configure_panel_styling(self):
        """Configure professional Panel styling."""
        # Set Panel configuration
        pn.config.sizing_mode = 'stretch_width'

        # Professional CSS styling
        pn.config.raw_css = ["""
        /* Professional Scientific Interface Styling */
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #F8F9FA;
            margin: 0;
            padding: 0;
        }
        
        /* Card styling */
        .card-container {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin: 10px;
            overflow: hidden;
            transition: box-shadow 0.3s ease;
        }
        
        .card-container:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        /* Header styling */
        .card-header {
            background: linear-gradient(135deg, #2E4057 0%, #1976D2 100%);
            color: white;
            padding: 15px;
            font-weight: 600;
            font-size: 18px;
        }
        
        /* Section headers */
        .section-header {
            color: #2E4057;
            font-size: 16px;
            font-weight: 600;
            margin: 20px 5px 10px 5px;
            padding-bottom: 5px;
            border-bottom: 2px solid #E0E0E0;
        }
        
        /* Status colors */
        .status-success { 
            color: #2E7D32; 
            background: #E8F5E8;
            border-left: 3px solid #2E7D32;
        }
        
        .status-warning { 
            color: #F57C00; 
            background: #FFF3E0;
            border-left: 3px solid #F57C00;
        }
        
        .status-error { 
            color: #D32F2F; 
            background: #FFEBEE;
            border-left: 3px solid #D32F2F;
        }
        
        .status-info { 
            color: #1976D2; 
            background: #E3F2FD;
            border-left: 3px solid #1976D2;
        }
        
        /* File item styling */
        .file-item {
            padding: 8px 12px;
            margin: 4px 0;
            border-left: 3px solid #1976D2;
            background: #F5F5F5;
            border-radius: 0 4px 4px 0;
        }
        
        /* Button styling improvements */
        .bk-btn-primary {
            background: linear-gradient(135deg, #1976D2 0%, #1565C0 100%);
            border: none;
            border-radius: 6px;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        
        .bk-btn-primary:hover {
            background: linear-gradient(135deg, #1565C0 0%, #0D47A1 100%);
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(25, 118, 210, 0.3);
        }
        
        .bk-btn-light {
            background: #F5F5F5;
            border: 1px solid #E0E0E0;
            border-radius: 6px;
            transition: all 0.2s ease;
        }
        
        .bk-btn-light:hover {
            background: #EEEEEE;
            border-color: #BDBDBD;
        }
        
        /* Input styling */
        .bk-input {
            border: 1px solid #E0E0E0;
            border-radius: 6px;
            padding: 8px 12px;
            transition: border-color 0.2s ease;
        }
        
        .bk-input:focus {
            border-color: #1976D2;
            box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.1);
            outline: none;
        }
        
        /* Select widget styling */
        .bk-input-group .bk-input {
            border-radius: 6px;
        }
        
        /* Plot area styling */
        .plot-container {
            background: #FAFAFA;
            border-radius: 4px;
            padding: 10px;
            min-height: 450px;
        }
        
        /* Professional spacing */
        .panel-widget-box {
            padding: 5px;
        }
        
        /* Responsive adjustments */
        @media (max-width: 768px) {
            .card-container {
                margin: 5px;
            }
            
            .card-header {
                padding: 12px;
                font-size: 16px;
            }
        }
        """]

    def _setup_connections(self):
        """Setup professional component connections."""
        # Cell selection updates file uploader
        self.cell_manager.param.watch(
            self._on_cell_selected, 'selected_cell'
        )

        # File selection updates data viewer
        self.file_uploader.param.watch(
            self._on_file_selected, 'selected_file'
        )

        # Status updates from all components
        for component in [self.cell_manager, self.file_uploader, self.data_viewer]:
            component.param.watch(
                self._on_status_update, 'status_message'
            )

    def _on_cell_selected(self, event):
        """Handle cell selection with professional feedback."""
        cell_name = event.new

        # Handle tuple case from Select widget
        if isinstance(cell_name, tuple):
            cell_name = cell_name[1] if len(cell_name) > 1 else cell_name[0]
        elif not isinstance(cell_name, str):
            cell_name = str(cell_name) if cell_name is not None else ""

        self.current_cell = cell_name
        self.file_uploader.set_current_cell(cell_name)

        if cell_name:
            self._update_main_status(f"Selected cell: {cell_name}", "success")
        else:
            self._update_main_status("No cell selected", "info")

    def _on_file_selected(self, event):
        """Handle file selection with professional feedback."""
        file_id = event.new

        # Handle tuple case from Select widget
        if isinstance(file_id, tuple):
            file_id = file_id[1] if len(file_id) > 1 else file_id[0]
        elif not isinstance(file_id, str):
            file_id = str(file_id) if file_id is not None else ""

        self.current_file = file_id
        self.data_viewer.load_file_data(file_id)

        if file_id:
            # Extract readable filename from ID
            display_name = file_id.split('_')[0] if '_' in file_id else file_id
            self._update_main_status(f"Loaded file: {display_name}", "success")
        else:
            self._update_main_status("No file selected", "info")

    def _on_status_update(self, event):
        """Handle status updates from components."""
        message = event.new
        if message:
            # Determine status type from message content
            if "error" in message.lower() or "❌" in message:
                status_type = "error"
            elif "warning" in message.lower() or "⚠️" in message:
                status_type = "warning"
            elif "success" in message.lower() or "✅" in message:
                status_type = "success"
            else:
                status_type = "info"

            self._update_main_status(message, status_type)

    def _create_status_bar(self):
        """Create professional integrated status bar."""
        from datetime import datetime

        # Status display
        self.status_display = pn.pane.HTML(
            """<div class='status-success' style='padding: 8px 15px; border-radius: 4px;'>
               ✅ Electrochemical Analysis Suite Ready
               </div>""",
            margin=(5, 15)
        )

        # System info
        self.system_info = pn.pane.HTML(
            """<div style='color: #666; font-size: 12px; text-align: right; padding: 5px 15px;'>
               Panel Web Interface | HoloViews Plotting | Polars Data Processing
               </div>""",
            margin=(0, 15)
        )

        return pn.Row(
            self.status_display,
            pn.Spacer(),
            self.system_info,
            sizing_mode='stretch_width',
            styles={'background': 'white', 'border-top': '1px solid #E0E0E0'}
        )

    def _update_main_status(self, message: str, status_type: str = "info"):
        """Update main status bar with professional styling."""
        from datetime import datetime

        # Choose styling based on status type
        if status_type == "success":
            icon = "✅"
            css_class = "status-success"
        elif status_type == "warning":
            icon = "⚠️"
            css_class = "status-warning"
        elif status_type == "error":
            icon = "❌"
            css_class = "status-error"
        else:  # info
            icon = "ℹ️"
            css_class = "status-info"

        timestamp = datetime.now().strftime('%H:%M:%S')

        self.status_display.object = f"""
        <div class='{css_class}' style='padding: 8px 15px; border-radius: 4px;'>
            {icon} {message}
            <span style='float: right; opacity: 0.7; font-size: 11px;'>{timestamp}</span>
        </div>
        """

    def _create_layout(self):
        """Create professional scientific interface layout with 3 tabs."""

        # Professional header with branding
        header = pn.pane.HTML("""
        <div style='background: linear-gradient(135deg, #2E4057 0%, #1976D2 100%); 
                    color: white; padding: 20px 30px; margin: 0;'>
            <div style='display: flex; align-items: center; justify-content: space-between;'>
                <div>
                    <h1 style='margin: 0; font-size: 24px; font-weight: 600;'>
                        🔬 Electrochemical Analysis Suite
                    </h1>
                    <p style='margin: 5px 0 0 0; opacity: 0.9; font-size: 14px;'>
                        Professional Battery Data Analysis Platform
                    </p>
                </div>
                <div style='text-align: right; opacity: 0.8; font-size: 12px;'>
                    <div>Version 3.0.0</div>
                    <div>Panel Web Interface</div>
                </div>
            </div>
        </div>
        """, sizing_mode='stretch_width', margin=(0, 0))

        # Tab 1: Cell & File Management (existing 3-column layout)
        tab1_content = pn.Row(
            pn.Column(
                self.cell_manager.panel,
                width=350, min_width=350, max_width=350
            ),
            pn.Column(
                self.file_uploader.panel,
                width=350, min_width=350, max_width=350
            ),
            pn.Column(
                self.data_viewer.panel,
                min_width=400
            ),
            sizing_mode='stretch_width',
            margin=(0, 0)
        )

        # Tab 2: Group Management (new)
        tab2_content = self.group_management_tab.panel

        # Tab 3: Data Analysis (placeholder for now)
        tab3_content = pn.pane.HTML("""
        <div style='text-align: center; padding: 100px; color: #666;'>
            <h2 style='color: #2E4057;'>📊 Advanced Data Analysis</h2>
            <p>Enhanced analytics and group-based analysis coming soon...</p>
        </div>
        """)

        # Create tabs
        tabs = pn.Tabs(
            ("🔋 Cell & File Management", tab1_content),
            ("🔗 Group Management", tab2_content),
            ("📊 Data Analysis", tab3_content),
            dynamic=True,
            sizing_mode='stretch_width'
        )

        # Complete professional layout
        self.layout = pn.Column(
            header,
            tabs,
            self.status_bar,  # Keep status bar at bottom for all tabs
            sizing_mode='stretch_both',
            min_height=800,
            styles={'background': '#F8F9FA'}
        )

    # def _create_layout(self):
    #     """Create professional scientific interface layout."""
    #
    #     # Professional header with branding
    #     header = pn.pane.HTML("""
    #     <div style='background: linear-gradient(135deg, #2E4057 0%, #1976D2 100%);
    #                 color: white; padding: 20px 30px; margin: 0;'>
    #         <div style='display: flex; align-items: center; justify-content: space-between;'>
    #             <div>
    #                 <h1 style='margin: 0; font-size: 24px; font-weight: 600;'>
    #                     🔬 Electrochemical Analysis Suite
    #                 </h1>
    #                 <p style='margin: 5px 0 0 0; opacity: 0.9; font-size: 14px;'>
    #                     Professional Battery Data Analysis Platform
    #                 </p>
    #             </div>
    #             <div style='text-align: right; opacity: 0.8; font-size: 12px;'>
    #                 <div>Version 3.0.0</div>
    #                 <div>Panel Web Interface</div>
    #             </div>
    #         </div>
    #     </div>
    #     """, sizing_mode='stretch_width', margin=(0, 0))
    #
    #     # Main content area - professional 3-column layout
    #     tab1_content = pn.Row(
    #         # Left column - Cell Management (fixed width)
    #         pn.Column(
    #             self.cell_manager.panel,
    #             width=350,
    #             min_width=350,
    #             max_width=350
    #         ),
    #
    #         # Middle column - File Operations (fixed width)
    #         pn.Column(
    #             self.file_uploader.panel,
    #             width=350,
    #             min_width=350,
    #             max_width=350
    #         ),
    #
    #         # Right column - Data Visualization (expandable)
    #         pn.Column(
    #             self.data_viewer.panel,
    #             min_width=400
    #         ),
    #
    #         sizing_mode='stretch_width',
    #         margin=(0, 0)
    #     )
    #     # Tab 2: Group Management (new)
    #     tab2_content = self.group_management_tab.panel
    #
    #     # Tab 3: Data Analysis (placeholder for now)
    #     tab3_content = pn.pane.HTML("<h2>Data Analysis Coming Soon</h2>")
    #
    #     # Professional footer with status
    #     footer = self.status_bar
    #
    #     # Complete professional layout
    #     self.layout = pn.Column(
    #         header,
    #         main_content,
    #         footer,
    #         sizing_mode='stretch_both',
    #         min_height=800,
    #         styles={'background': '#F8F9FA'}
    #     )

    def __panel__(self):
        """Return the professional Panel layout."""
        return self.layout

    def servable(self):
        """Make the app servable with professional title."""
        return self.layout.servable(
            title="Electrochemical Analysis Suite"
        )

# Application launcher function
def create_app():
    """Create and return the professional electrochemical app."""
    app = ElectrochemicalApp()
    return app.servable()

# Command line launcher
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Electrochemical Analysis Suite")
    parser.add_argument("--port", type=int, default=5007, help="Port to serve on")
    parser.add_argument("--show", action="store_true", help="Auto-open browser")
    parser.add_argument("--dev", action="store_true", help="Development mode")

    args = parser.parse_args()

    # Configure Panel server
    if args.dev:
        pn.config.autoreload = True

    # Create and serve app
    app = create_app()

    print(f"""
    🔬 Electrochemical Analysis Suite
    ═══════════════════════════════════
    
    🌐 Server starting on: http://localhost:{args.port}
    🔧 Mode: {'Development' if args.dev else 'Production'}
    
    Features:
    • Professional cell management
    • File upload & processing  
    • Interactive data visualization
    • Nyquist plot support (AC data detection)
    
    Press Ctrl+C to stop server
    """)

    pn.serve(
        app,
        port=args.port,
        show=args.show,
        title="Electrochemical Analysis Suite"
    )