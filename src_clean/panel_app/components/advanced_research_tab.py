"""
Advanced Research Analytics Tab

Professional 3-panel interface for advanced electrochemical data exploration
using Perspective integration with real-time data analysis capabilities.

Features:
- Multi-cell data selection with filtering
- Interactive Perspective workspace
- Professional styling consistent with existing tabs
- Real-time dataset loading and analysis
"""

import panel as pn
import param
import pandas as pd
import polars as pl
from typing import List, Dict, Any, Optional
import logging

# Configure extensions
pn.extension('tabulator', 'perspective')

logger = logging.getLogger(__name__)

class AdvancedResearchTab(param.Parameterized):
    """
    Advanced Research Analytics Tab with Perspective integration.
    
    Provides 3-panel layout for comprehensive electrochemical data exploration:
    - Data Selection Panel: Cell selection and filtering
    - Quick Actions Panel: Load dataset, refresh, info
    - Perspective Workspace: Interactive analysis and visualization
    """
    
    # Status parameters
    status_message = param.String(default="Ready", doc="Current status message")
    dataset_loaded = param.Boolean(default=False, doc="Whether dataset is loaded")
    perspective_ready = param.Boolean(default=False, doc="Whether Perspective is ready")
    
    def __init__(self, api, **params):
        super().__init__(**params)
        self.api = api
        
        # State management
        self.selected_cells = []
        self.current_temperature_filter = "All"
        self.current_dataset = None
        self.dataset_info = {}
        
        # Create components
        self._create_components()
        self._setup_layout()
        self._setup_callbacks()
        
        # Initialize data
        self._refresh_cells()
        
        logger.info("Advanced Research Tab initialized")
    
    def _create_components(self):
        """Create all UI components for 3-panel layout."""
        
        # === DATA SELECTION PANEL ===
        self._create_data_selection_components()
        
        # === QUICK ACTIONS PANEL ===
        self._create_quick_actions_components()
        
        # === PERSPECTIVE WORKSPACE ===
        self._create_perspective_components()
    
    def _create_data_selection_components(self):
        """Create data selection panel components."""
        
        # Cell selection table
        self.cell_tabulator = pn.widgets.Tabulator(
            value=pd.DataFrame({
                'Cell Name': [],
                'Segments': [],
                'Files': [],
                'Techniques': []
            }),
            pagination='local',
            page_size=15,
            sizing_mode='stretch_width',
            selectable='checkbox',
            sortable=True,
            show_index=False,
            configuration={
                'layout': 'fitData',
                'height': '300px',
                'placeholder': 'No cells available',
                'tooltips': True,
                'columnDefaults': {'tooltip': True}
            },
            height=300,
            margin=(5, 5)
        )
        
        # Temperature filter
        self.temperature_filter = pn.widgets.Select(
            name="Temperature Filter",
            value="All",
            options=["All", "25°C", "45°C", "60°C"],
            width=280,
            margin=(5, 5)
        )
        
        # Data info display
        self.data_info_display = pn.pane.HTML("""
            <div style='background: #F8F9FA; padding: 10px; border-radius: 4px; 
                        text-align: center; color: #666; font-size: 14px;'>
                <strong>Data Selection</strong><br>
                <small>Select cells to analyze</small>
            </div>
            """,
            height=80,
            margin=(5, 5)
        )
    
    def _create_quick_actions_components(self):
        """Create quick actions panel components."""
        
        # Load Dataset button (primary action)
        self.load_dataset_btn = pn.widgets.Button(
            name="Load Dataset",
            button_type="primary",
            disabled=True,
            width=180,
            margin=(5, 5)
        )
        
        # Refresh cells button
        self.refresh_cells_btn = pn.widgets.Button(
            name="Refresh Cells",
            button_type="default",
            width=180,
            margin=(5, 5)
        )
        
        # Dataset info button
        self.dataset_info_btn = pn.widgets.Button(
            name="Dataset Info",
            button_type="light",
            disabled=True,
            width=180,
            margin=(5, 5)
        )
        
        # Status indicator
        self.status_indicator = pn.pane.HTML("""
            <div style='padding: 10px; border-radius: 4px; text-align: center; 
                        background: #E9ECEF; color: #495057; font-size: 13px;'>
                <strong>Status:</strong> Ready
            </div>
            """,
            height=50,
            margin=(5, 5)
        )
    
    def _create_perspective_components(self):
        """Create perspective workspace components."""
        
        # Perspective viewer (main component)
        self.perspective_viewer = pn.pane.Perspective(
            object=pd.DataFrame(),  # Start empty
            sizing_mode='stretch_both',
            min_height=600,
            margin=(5, 5)
        )
        
        # Perspective status
        self.perspective_status = pn.pane.HTML("""
            <div style='padding: 8px; border-radius: 4px; text-align: center; 
                        background: #FFF3CD; color: #856404; font-size: 12px;'>
                <strong>Perspective Workspace</strong><br>
                <small>Load dataset to begin analysis</small>
            </div>
            """,
            height=60,
            margin=(5, 5)
        )
    
    def _setup_layout(self):
        """Setup the 3-panel responsive layout."""
        
        # Data Selection Panel (320px fixed width)
        data_panel = pn.Column(
            pn.pane.HTML("<h4 style='margin: 10px 5px; color: #333;'>📊 Data Selection</h4>"),
            self.temperature_filter,
            self.cell_tabulator,
            self.data_info_display,
            width=320,
            sizing_mode='fixed',
            styles={
                'background': '#FFFFFF',
                'border': '1px solid #E0E0E0',
                'border-radius': '8px',
                'box-shadow': '0 2px 4px rgba(0,0,0,0.1)'
            },
            margin=(5, 5)
        )
        
        # Quick Actions Panel (200px fixed width)
        actions_panel = pn.Column(
            pn.pane.HTML("<h4 style='margin: 10px 5px; color: #333;'>⚡ Quick Actions</h4>"),
            self.load_dataset_btn,
            self.refresh_cells_btn,
            self.dataset_info_btn,
            pn.Spacer(height=20),
            self.status_indicator,
            width=200,
            sizing_mode='fixed',
            styles={
                'background': '#FFFFFF',
                'border': '1px solid #E0E0E0',
                'border-radius': '8px',
                'box-shadow': '0 2px 4px rgba(0,0,0,0.1)'
            },
            margin=(5, 5)
        )
        
        # Perspective Workspace (flexible width)
        workspace_panel = pn.Column(
            pn.pane.HTML("<h4 style='margin: 10px 5px; color: #333;'>🔬 Perspective Workspace</h4>"),
            self.perspective_status,
            self.perspective_viewer,
            sizing_mode='stretch_both',
            min_width=600,
            styles={
                'background': '#FFFFFF',
                'border': '1px solid #E0E0E0',
                'border-radius': '8px',
                'box-shadow': '0 2px 4px rgba(0,0,0,0.1)'
            },
            margin=(5, 5)
        )
        
        # Main layout - 3-panel row
        self.layout = pn.Row(
            data_panel,
            actions_panel,
            workspace_panel,
            sizing_mode='stretch_width',
            min_height=700
        )
    
    def _setup_callbacks(self):
        """Setup all component callbacks and interactions."""
        
        # Button callbacks
        self.load_dataset_btn.on_click(self._on_load_dataset)
        self.refresh_cells_btn.on_click(self._on_refresh_cells)
        self.dataset_info_btn.on_click(self._on_show_dataset_info)
        
        # Selection callbacks
        self.cell_tabulator.param.watch(self._on_cell_selection_changed, 'selection')
        self.temperature_filter.param.watch(self._on_temperature_filter_changed, 'value')
    
    def _refresh_cells(self):
        """Refresh available cells from backend."""
        try:
            self._update_status("Loading available cells...", "loading")
            
            # Get cells from backend
            available_cells = self.api.get_available_research_cells()
            
            if not available_cells:
                self._update_status("No cells available for research", "warning")
                return
            
            # Get summary data for each cell
            cell_data = []
            for cell_name in available_cells:
                try:
                    summary = self.api.get_research_data_summary([cell_name])
                    cell_data.append({
                        'Cell Name': cell_name,
                        'Segments': summary.get('total_segments', 0),
                        'Files': summary.get('total_files', 0),
                        'Techniques': ', '.join(summary.get('techniques', [])[:3])  # Show first 3
                    })
                except Exception as e:
                    logger.warning(f"Failed to get summary for {cell_name}: {e}")
                    cell_data.append({
                        'Cell Name': cell_name,
                        'Segments': 'N/A',
                        'Files': 'N/A',
                        'Techniques': 'N/A'
                    })
            
            # Update tabulator
            self.cell_tabulator.value = pd.DataFrame(cell_data)
            self._update_status(f"Loaded {len(available_cells)} cells", "success")
            
        except Exception as e:
            logger.error(f"Failed to refresh cells: {e}")
            self._update_status(f"Failed to load cells: {str(e)}", "error")
    
    def _on_load_dataset(self, event):
        """Handle load dataset button click."""
        if not self.selected_cells:
            self._update_status("Please select cells first", "warning")
            return
        
        try:
            self._update_status("Loading dataset for Perspective...", "loading")
            
            # Get temperature filter
            temp_filter = None if self.current_temperature_filter == "All" else float(self.current_temperature_filter.replace('°C', ''))
            
            # Load dataset from backend
            dataset = self.api.get_research_dataset_for_perspective(
                cells=self.selected_cells,
                temperature=temp_filter
            )
            
            if dataset.is_empty():
                self._update_status("No data found for selected criteria", "warning")
                return
            
            # Convert Polars to Pandas for Perspective
            pandas_df = dataset.to_pandas()
            
            # Update perspective viewer
            self.perspective_viewer.object = pandas_df
            self.current_dataset = dataset
            
            # Update status and buttons
            self.dataset_loaded = True
            self.perspective_ready = True
            self.dataset_info_btn.disabled = False
            
            # Update data info
            rows, cols = pandas_df.shape
            self._update_data_info(f"Dataset: {rows:,} rows × {cols} columns")
            self._update_perspective_status("Dataset loaded successfully", "success")
            self._update_status(f"Dataset loaded: {rows:,} rows", "success")
            
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            self._update_status(f"Failed to load dataset: {str(e)}", "error")
    
    def _on_refresh_cells(self, event):
        """Handle refresh cells button click."""
        self._refresh_cells()
    
    def _on_show_dataset_info(self, event):
        """Show dataset information modal."""
        if not self.current_dataset:
            self._update_status("No dataset loaded", "warning")
            return
        
        try:
            # Get summary information
            summary = self.api.get_research_data_summary(cells=self.selected_cells)
            
            # Create info content
            info_content = f"""
            <h4>Dataset Information</h4>
            <table style='width:100%; border-collapse: collapse;'>
                <tr><td style='padding:8px; border:1px solid #ddd;'><strong>Total Segments:</strong></td>
                    <td style='padding:8px; border:1px solid #ddd;'>{summary.get('total_segments', 'N/A')}</td></tr>
                <tr><td style='padding:8px; border:1px solid #ddd;'><strong>Total Files:</strong></td>
                    <td style='padding:8px; border:1px solid #ddd;'>{summary.get('total_files', 'N/A')}</td></tr>
                <tr><td style='padding:8px; border:1px solid #ddd;'><strong>Date Range:</strong></td>
                    <td style='padding:8px; border:1px solid #ddd;'>{summary.get('date_range', 'N/A')}</td></tr>
                <tr><td style='padding:8px; border:1px solid #ddd;'><strong>Techniques:</strong></td>
                    <td style='padding:8px; border:1px solid #ddd;'>{', '.join(summary.get('techniques', []))}</td></tr>
                <tr><td style='padding:8px; border:1px solid #ddd;'><strong>Selected Cells:</strong></td>
                    <td style='padding:8px; border:1px solid #ddd;'>{', '.join(self.selected_cells)}</td></tr>
            </table>
            """
            
            # Show modal
            modal = pn.Column(
                pn.pane.HTML(info_content, sizing_mode='stretch_width'),
                pn.widgets.Button(name="Close", button_type="primary"),
                width=500, height=300
            )
            
            modal[1].on_click(lambda event: modal.close())
            modal.show()
            
        except Exception as e:
            logger.error(f"Failed to show dataset info: {e}")
            self._update_status(f"Failed to show info: {str(e)}", "error")
    
    def _on_cell_selection_changed(self, event):
        """Handle cell selection change."""
        try:
            selected_indices = event.new if event.new else []
            selected_cells = []
            
            if selected_indices and not self.cell_tabulator.value.empty:
                for idx in selected_indices:
                    if idx < len(self.cell_tabulator.value):
                        cell_name = self.cell_tabulator.value.iloc[idx]['Cell Name']
                        selected_cells.append(cell_name)
            
            self.selected_cells = selected_cells
            
            # Update load button state
            self.load_dataset_btn.disabled = len(selected_cells) == 0
            
            # Update status
            if selected_cells:
                self._update_status(f"Selected {len(selected_cells)} cells", "info")
            else:
                self._update_status("No cells selected", "info")
                
        except Exception as e:
            logger.error(f"Cell selection error: {e}")
            self._update_status("Selection error", "error")
    
    def _on_temperature_filter_changed(self, event):
        """Handle temperature filter change."""
        self.current_temperature_filter = event.new
        if self.selected_cells:
            self._update_status(f"Filter changed to {event.new}", "info")
    
    def _update_status(self, message: str, status_type: str = "info"):
        """Update status indicator with message and type."""
        self.status_message = message
        
        color_map = {
            "info": "#17A2B8",
            "success": "#28A745", 
            "warning": "#FFC107",
            "error": "#DC3545",
            "loading": "#6F42C1"
        }
        
        bg_color_map = {
            "info": "#D1ECF1",
            "success": "#D4EDDA",
            "warning": "#FFF3CD", 
            "error": "#F8D7DA",
            "loading": "#E2D9F3"
        }
        
        color = color_map.get(status_type, color_map["info"])
        bg_color = bg_color_map.get(status_type, bg_color_map["info"])
        
        self.status_indicator.object = f"""
            <div style='padding: 10px; border-radius: 4px; text-align: center; 
                        background: {bg_color}; color: {color}; font-size: 13px;'>
                <strong>Status:</strong> {message}
            </div>
        """
    
    def _update_data_info(self, message: str):
        """Update data info display."""
        self.data_info_display.object = f"""
            <div style='background: #F8F9FA; padding: 10px; border-radius: 4px; 
                        text-align: center; color: #666; font-size: 14px;'>
                <strong>Data Selection</strong><br>
                <small>{message}</small>
            </div>
        """
    
    def _update_perspective_status(self, message: str, status_type: str = "info"):
        """Update perspective workspace status."""
        color_map = {
            "info": "#856404",
            "success": "#155724",
            "warning": "#856404", 
            "error": "#721C24"
        }
        
        bg_color_map = {
            "info": "#FFF3CD",
            "success": "#D4EDDA",
            "warning": "#FFF3CD",
            "error": "#F8D7DA"
        }
        
        color = color_map.get(status_type, color_map["info"])
        bg_color = bg_color_map.get(status_type, bg_color_map["info"])
        
        self.perspective_status.object = f"""
            <div style='padding: 8px; border-radius: 4px; text-align: center; 
                        background: {bg_color}; color: {color}; font-size: 12px;'>
                <strong>Perspective Workspace</strong><br>
                <small>{message}</small>
            </div>
        """
    
    @property
    def panel(self):
        """Return the main panel layout."""
        return self.layout


class AdvancedResearchTabWrapper:
    """
    Integration wrapper for Advanced Research Tab.
    
    Provides standardized interface for main application integration
    with cleanup and state management capabilities.
    """
    
    def __init__(self, api, **kwargs):
        """Initialize wrapper with backend API."""
        self.api = api
        self.tab = AdvancedResearchTab(api=api, **kwargs)
        logger.info("Advanced Research Tab Wrapper initialized")
    
    @property
    def panel(self):
        """Return the tab panel for integration."""
        return self.tab.panel
    
    def cleanup(self):
        """Cleanup resources and connections."""
        try:
            # Clear any loaded datasets
            if hasattr(self.tab, 'current_dataset'):
                self.tab.current_dataset = None
            
            # Reset perspective viewer
            if hasattr(self.tab, 'perspective_viewer'):
                self.tab.perspective_viewer.object = pd.DataFrame()
            
            logger.info("Advanced Research Tab cleaned up")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current tab state for debugging/monitoring."""
        return {
            'selected_cells': getattr(self.tab, 'selected_cells', []),
            'dataset_loaded': getattr(self.tab, 'dataset_loaded', False),
            'perspective_ready': getattr(self.tab, 'perspective_ready', False),
            'status': getattr(self.tab, 'status_message', 'Unknown')
        }