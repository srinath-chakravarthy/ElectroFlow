"""
Main Panel Application - Clean and Modern Web Interface

A clean, organized Panel application with proper separation of concerns.
"""

import panel as pn
import param
from pathlib import Path

from src_clean.backend import get_backend_api
from .components import CellManager, FileUploader, DataViewer, StatusBar

class ElectrochemicalApp(param.Parameterized):
    """
    Main Panel application for electrochemical data analysis.
    
    Clean architecture with separate components:
    - Cell management
    - File upload and processing  
    - Data visualization
    - Status and logging
    """
    
    # Application state
    current_cell = param.String(default="", doc="Currently selected cell")
    current_file = param.String(default="", doc="Currently selected file")
    
    def __init__(self, **params):
        super().__init__(**params)
        
        # Initialize backend
        self.api = get_backend_api()
        
        # Create components
        self.cell_manager = CellManager(api=self.api)
        self.file_uploader = FileUploader(api=self.api)
        self.data_viewer = DataViewer(api=self.api)
        self.status_bar = StatusBar()
        
        # Setup component connections
        self._setup_connections()
        
        # Create layout
        self._create_layout()
    
    def _setup_connections(self):
        """Setup inter-component communication."""
        # Cell selection updates file uploader
        self.cell_manager.param.watch(
            self._on_cell_selected, 'selected_cell'
        )
        
        # File selection updates data viewer
        self.file_uploader.param.watch(
            self._on_file_selected, 'selected_file'
        )
        
        # Status updates
        for component in [self.cell_manager, self.file_uploader, self.data_viewer]:
            component.param.watch(
                self._on_status_update, 'status_message'
            )
    
    def _on_cell_selected(self, event):
        """Handle cell selection."""
        cell_name = event.new
        self.current_cell = cell_name
        self.file_uploader.set_current_cell(cell_name)
        self.status_bar.update_status(f"Selected cell: {cell_name}")
    
    def _on_file_selected(self, event):
        """Handle file selection."""
        file_id = event.new
        self.current_file = file_id
        self.data_viewer.load_file_data(file_id)
        self.status_bar.update_status(f"Loaded file: {file_id}")
    
    def _on_status_update(self, event):
        """Handle status updates from components."""
        message = event.new
        if message:
            self.status_bar.update_status(message)
    
    def _create_layout(self):
        """Create the main application layout."""
        # Header
        header = pn.pane.HTML("""
        <h1 style='color: #2E4057; margin: 0; padding: 20px;'>
            🔬 Electrochemical Analysis Suite
        </h1>
        <hr style='margin: 0; border: 1px solid #ddd;'>
        """, sizing_mode='stretch_width')
        
        # Main content - 3 column layout
        main_content = pn.Row(
            # Left column - Cell management
            pn.Column(
                self.cell_manager.panel,
                width=300,
                name="Cell Management"
            ),
            
            # Middle column - File operations
            pn.Column(
                self.file_uploader.panel,
                width=350,
                name="File Operations"
            ),
            
            # Right column - Data visualization (expandable)
            pn.Column(
                self.data_viewer.panel,
                name="Data Visualization"
            ),
            
            sizing_mode='stretch_width'
        )
        
        # Footer with status
        footer = pn.Row(
            self.status_bar.panel,
            sizing_mode='stretch_width'
        )
        
        # Complete layout
        self.layout = pn.Column(
            header,
            main_content,
            footer,
            sizing_mode='stretch_both',
            min_height=800
        )
    
    def __panel__(self):
        """Return the Panel layout."""
        return self.layout
    
    def servable(self):
        """Make the app servable."""
        return self.layout.servable(title="Electrochemical Analysis Suite")