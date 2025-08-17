"""
Main Panel application for battery data analyzer.

Combines all UI components into a cohesive application with tabbed interface.
Provides cell preprocessing, file association, and data analysis capabilities.
"""

import panel as pn
import param
from pathlib import Path
import sys
import logging
import pandas as pd
from typing import List

# Configure Panel
pn.extension('plotly', 'tabulator')

# Add src directory to path for imports
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from ui.backend_api import BackendAPI
from ui.components.cell_manager import CellManagerTab
from ui.components.data_processing import DataProcessingTab

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BatteryAnalyzerApp(param.Parameterized):
    """
    Main Panel application for battery data preprocessing and analysis.
    
    Features:
    - Cell & File Management (create cells, upload files, manage active cell)
    - Cell Data Processing (technique selection, group management, manual plotting)
    - SQLite database backend
    - Active cell workflow across tabs
    """
    
    # Application state parameters
    current_tab = param.String(default="Cell & File Management", doc="Current active tab")
    active_cell_id = param.Integer(default=None, allow_None=True, doc="Active cell ID across tabs")
    active_cell_name = param.String(default="", doc="Active cell name across tabs")
    
    def __init__(self, data_dir: Path = None, db_path: Path = None, **params):
        super().__init__(**params)
        
        # Initialize backend
        self.data_dir = data_dir or Path("data")
        self.db_path = db_path or (self.data_dir / "battery_analyzer.db")
        self.setup_backend()
        
        # Initialize UI components
        self.setup_ui()
        
        logger.info(f"BatteryAnalyzerApp initialized with data_dir: {self.data_dir}")
    
    def setup_backend(self):
        """Initialize backend API and database."""
        try:
            self.api = BackendAPI(self.data_dir, self.db_path)
            logger.info("Backend API initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize backend: {e}")
            raise
    
    def setup_ui(self):
        """Setup the complete UI with all components."""
        
        # Create component tabs
        self.cell_manager = CellManagerTab(self.api)
        self.data_processing = DataProcessingTab(self.api)
        
        # Connect active cell sharing between tabs
        self._setup_active_cell_sharing()
        
        # Create header
        header = self._create_header()
        
        # Create main tabbed interface
        self.tabs = pn.Tabs(
            ("Cell & File Management", self.cell_manager.layout),
            ("Cell Data Processing", self.data_processing.layout),
            tabs_location='above',
            width=1400
        )
        
        # Create footer
        footer = self._create_footer()
        
        # Main application layout
        self.layout = pn.Column(
            header,
            self.tabs,
            footer,
            width=1400
        )
    
    def _setup_active_cell_sharing(self):
        """Setup active cell sharing between tabs."""
        
        # Watch for changes in cell manager's active cell
        def sync_active_cell_from_manager(event):
            if hasattr(event, 'new') and event.new != self.active_cell_id:
                self.active_cell_id = event.new
                # Update data processing tab
                if hasattr(self.data_processing, 'set_active_cell') and self.active_cell_id:
                    cell_name = self.cell_manager.active_cell_name
                    self.active_cell_name = cell_name
                    self.data_processing.set_active_cell(self.active_cell_id, cell_name)
        
        def sync_active_cell_name_from_manager(event):
            if hasattr(event, 'new') and event.new != self.active_cell_name:
                self.active_cell_name = event.new
        
        # Connect cell manager to app state
        self.cell_manager.param.watch(sync_active_cell_from_manager, 'active_cell_id')
        self.cell_manager.param.watch(sync_active_cell_name_from_manager, 'active_cell_name')
    
    def _create_header(self):
        """Create application header."""
        
        # Database stats
        db_stats = self.api.get_database_stats()
        
        if db_stats['success']:
            stats = db_stats['stats']
            stats_text = f"""
            Cells: {stats.get('cells_count', 0)} | 
            Files: {stats.get('files_count', 0)} | 
            DB Size: {stats.get('db_size_bytes', 0) / 1024:.1f} KB
            """
        else:
            stats_text = "Database stats unavailable"
        
        # Application info
        app_info = f"""
        <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 10px;">
            <h1 style="margin: 0; color: #2c3e50;">🔋 Battery Data Analyzer</h1>
            <p style="margin: 5px 0; color: #7f8c8d;">
                Technique-centric battery data processing with active cell workflow
            </p>
            <p style="margin: 0; font-size: 12px; color: #95a5a6;">
                Data Directory: {self.data_dir} | Database: {self.db_path.name} | {stats_text}
            </p>
        </div>
        """
        
        return pn.pane.HTML(app_info, width=1400)
    
    def _create_footer(self):
        """Create application footer."""
        
        # Quick actions
        backup_btn = pn.widgets.Button(name="Backup Database", button_type="light", width=150)
        refresh_btn = pn.widgets.Button(name="Refresh All", button_type="light", width=100)
        
        # Status messages
        status_pane = pn.pane.HTML("", width=600)
        
        def backup_database(event):
            backup_path = self.data_dir / "backups" / f"backup_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.db"
            backup_path.parent.mkdir(exist_ok=True)
            
            result = self.api.backup_database(backup_path)
            if result['success']:
                status_pane.object = f'<p style="color: green;">✓ {result["message"]}</p>'
            else:
                status_pane.object = f'<p style="color: red;">✗ Backup failed: {result["error"]}</p>'
        
        def refresh_all(event):
            # Trigger refresh in all components
            if hasattr(self.cell_manager, 'refresh_trigger'):
                self.cell_manager.refresh_trigger += 1
            if hasattr(self.data_processing, 'refresh_trigger'):
                self.data_processing.refresh_trigger += 1
            
            status_pane.object = '<p style="color: green;">✓ All components refreshed</p>'
        
        backup_btn.on_click(backup_database)
        refresh_btn.on_click(refresh_all)
        
        footer_content = f"""
        <div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin-top: 20px; text-align: center;">
            <p style="margin: 0; font-size: 12px; color: #7f8c8d;">
                Battery Data Analyzer v2.0 | Panel UI with SQLite Backend | 
                <a href="https://github.com/anthropics/claude-code" target="_blank">Generated with Claude Code</a>
            </p>
        </div>
        """
        
        return pn.Column(
            pn.Row(
                backup_btn,
                refresh_btn,
                status_pane,
                sizing_mode='stretch_width'
            ),
            pn.pane.HTML(footer_content, width=1400)
        )
    
    def serve(self, port: int = 5007, show: bool = True, allow_websocket_origin: List[str] = None):
        """
        Serve the Panel application.
        
        Args:
            port: Port to serve on
            show: Whether to show the app in browser
            allow_websocket_origin: Allowed websocket origins
            
        Returns:
            Servable Panel object
        """
        # Configure Panel server settings
        pn.config.throttled = True  # Enable throttling for better performance
        
        # Set up allowed origins for websocket
        if allow_websocket_origin:
            pn.config.allow_websocket_origin = allow_websocket_origin
        else:
            pn.config.allow_websocket_origin = ["localhost:5007", "127.0.0.1:5007"]
        
        # Make layout servable
        servable_app = pn.serve(
            self.layout,
            port=port,
            show=show,
            title="Battery Data Analyzer",
            start=True,
            autoreload=False  # Disable autoreload for production
        )
        
        logger.info(f"Battery Data Analyzer served on port {port}")
        return servable_app
    
    def servable(self):
        """Return servable layout for external serving."""
        return self.layout


def create_app(data_dir: Path = None, db_path: Path = None) -> BatteryAnalyzerApp:
    """
    Create and configure the battery analyzer application.
    
    Args:
        data_dir: Base directory for data storage
        db_path: Path to SQLite database
        
    Returns:
        Configured BatteryAnalyzerApp instance
    """
    return BatteryAnalyzerApp(data_dir, db_path)


def main():
    """Main entry point for running the application."""
    import argparse
    import pandas as pd
    
    parser = argparse.ArgumentParser(description="Battery Data Analyzer - Panel UI")
    parser.add_argument("--data-dir", type=Path, default="data",
                       help="Base directory for data storage (default: data)")
    parser.add_argument("--port", type=int, default=5007,
                       help="Port to serve on (default: 5007)")
    parser.add_argument("--no-show", action="store_true",
                       help="Don't show app in browser")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Configure logging
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    
    # Create and serve app
    app = create_app(data_dir=args.data_dir)
    
    try:
        app.serve(port=args.port, show=not args.no_show)
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise


if __name__ == "__main__":
    main()