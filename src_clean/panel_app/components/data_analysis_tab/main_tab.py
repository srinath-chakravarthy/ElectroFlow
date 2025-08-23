"""
Tab 3 Data Analysis - Main Coordinator

Handles layout coordination, main event handlers, and state management for Tab 3.
This is the central control point that coordinates between analysis panels, plotting, and results.

Architecture: 3-row layout with progressive disclosure and isolated state management.
"""

import panel as pn
import param
from typing import Dict, List, Any


class DataAnalysisTab(param.Parameterized):
    """
    Main coordinator for Tab 3 Data Analysis interface.
    Handles layout, state management, and component coordination.
    
    Phase 1: Basic layout structure with placeholders
    Phase 2: Add data pipeline coordination  
    Phase 3: Add visualization coordination
    Phase 4: Add multiple analysis types
    """
    
    # ===== STATE MANAGEMENT =====
    current_cell = param.String(default="", doc="Currently selected cell")
    selected_groups = param.List(default=[], doc="Selected groups for analysis") 
    current_analysis = param.String(default="basic_statistics", doc="Current analysis type")
    analysis_results = param.Dict(default={}, doc="Current analysis results")
    
    def __init__(self, api, **params):
        super().__init__(**params)
        
        # Store API reference
        self.api = api
        
        # Import components (lazy loading to avoid circular imports)
        from .analysis_panels import AnalysisPanels
        from .plotting import PlottingManager  
        from .results import ResultsDisplay
        
        # Initialize specialized components
        self.analysis_panels = AnalysisPanels(api)
        self.plotting_manager = PlottingManager(api)
        self.results_display = ResultsDisplay(api)
        
        # Create layout
        self._create_layout()
        self._setup_basic_event_handlers()
        
        # Initialize with empty state
        self._initialize_empty_state()
    
    def _create_layout(self):
        """Create professional 3-row Tab 3 layout."""
        
        # === ROW 1: CONTEXT BAR ===
        context_bar = self._create_context_bar()
        
        # === ROW 2: MAIN ANALYSIS AREA ===  
        main_area = self._create_main_analysis_area()
        
        # === ROW 3: EXPORT & DETAILED RESULTS ===
        export_results_area = self._create_export_results_area()
        
        # Complete layout
        self.panel = pn.Column(
            context_bar,
            main_area, 
            export_results_area,
            sizing_mode='stretch_both',
            min_height=700,
            styles={'background': '#F8F9FA'}
        )
    
    def _create_context_bar(self):
        """Create Row 1: Context bar with cell selector and analysis type."""
        
        # Cell selector placeholder
        self.cell_selector = pn.widgets.Select(
            name="Cell",
            options=[("No cells available", "")],
            value="",
            width=200
        )
        
        # Analysis type selector  
        self.analysis_type_selector = pn.widgets.Select(
            name="Analysis Type",
            options=[
                ("Basic Statistics", "basic_statistics"),
                ("dQ/dV Analysis", "dqdv_analysis"), 
                ("Kinetics Analysis", "kinetics_analysis")
            ],
            value="basic_statistics",
            width=200
        )
        
        # Status indicator placeholder
        self.status_indicator = pn.pane.HTML(
            """<div style='color: #666; font-size: 14px; padding: 8px;'>
               📊 Ready for analysis
               </div>""",
            width=300
        )
        
        # Context bar layout
        return pn.Row(
            pn.pane.HTML("<strong>📊 Data Analysis</strong>", margin=(10, 5)),
            pn.Spacer(width=20),
            self.cell_selector,
            pn.Spacer(width=20), 
            self.analysis_type_selector,
            pn.Spacer(),  # Push status to right
            self.status_indicator,
            styles={
                'background': 'white',
                'border': '1px solid #E0E0E0',
                'border-radius': '8px',
                'padding': '10px',
                'margin': '10px'
            },
            height=60
        )
    
    def _create_main_analysis_area(self):
        """Create Row 2: Main analysis area with left panels and right visualization."""
        
        # === LEFT COLUMN (30%): ANALYSIS SETUP ===
        left_column = pn.Column(
            # Groups section (always visible)
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                📊 Groups Selection
            </div>
            """),
            
            # Groups panel placeholder
            self.analysis_panels.get_groups_panel(),
            
            # Analysis settings panel (collapsible, analysis-specific)
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 20px 5px 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                ⚙️ Analysis Settings
            </div>
            """),
            
            # Settings panel placeholder  
            self.analysis_panels.get_current_settings_panel(),
            
            width=350,
            styles={
                'background': 'white',
                'border': '1px solid #E0E0E0', 
                'border-radius': '8px',
                'padding': '15px',
                'margin': '10px'
            }
        )
        
        # === RIGHT COLUMN (70%): VISUALIZATION & RESULTS ===
        right_column = pn.Column(
            # Main plot area
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                📈 Visualization
            </div>
            """),
            
            # Plot area placeholder
            self.plotting_manager.get_plot_area(),
            
            # Plot controls (collapsible)
            self.plotting_manager.get_plot_controls(),
            
            # Quick results panel
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 20px 5px 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                🔬 Quick Results
            </div>
            """),
            
            # Results placeholder
            self.results_display.get_quick_results_panel(),
            
            styles={
                'background': 'white',
                'border': '1px solid #E0E0E0',
                'border-radius': '8px', 
                'padding': '15px',
                'margin': '10px'
            }
        )
        
        # Main area layout (30% | 70%)
        return pn.Row(
            left_column,
            right_column,
            sizing_mode='stretch_width',
            min_height=500
        )
    
    def _create_export_results_area(self):
        """Create Row 3: Export options and detailed results (collapsible)."""
        
        # Placeholder for export and detailed results
        export_panel = pn.Column(
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                💾 Export & Detailed Results
            </div>
            """),
            
            pn.pane.HTML("""
            <div style='color: #666; padding: 20px; text-align: center;'>
                <em>Export options and detailed results will appear here...</em>
            </div>
            """),
            
            styles={
                'background': 'white',
                'border': '1px solid #E0E0E0',
                'border-radius': '8px',
                'padding': '15px', 
                'margin': '10px'
            },
            collapsed=True  # Start collapsed
        )
        
        return export_panel
    
    def _setup_basic_event_handlers(self):
        """Setup basic event handlers for Phase 1 (minimal functionality)."""
        
        # Cell selection handler
        self.cell_selector.param.watch(self._on_cell_changed, 'value')
        
        # Analysis type selection handler
        self.analysis_type_selector.param.watch(self._on_analysis_type_changed, 'value')
    
    def _initialize_empty_state(self):
        """Initialize with empty state and populate cell options."""
        
        try:
            # Get available cells
            cells = self.api.get_cells()
            if cells:
                cell_options = [(f"{cell['name']} ({len(self.api.get_cell_files(cell['name']))} files)", 
                               cell['name']) for cell in cells]
                self.cell_selector.options = cell_options
                
                # Auto-select first cell if available
                if cell_options:
                    self.cell_selector.value = cell_options[0][1]
            else:
                self.cell_selector.options = [("No cells available", "")]
                
        except Exception as e:
            print(f"Error initializing Tab 3 state: {e}")
            self.cell_selector.options = [("Error loading cells", "")]
    
    # ===== EVENT HANDLERS =====
    
    def _on_cell_changed(self, event):
        """Handle cell selection change."""
        new_cell = event.new
        self.current_cell = new_cell
        
        if new_cell:
            # Update groups in analysis panels
            self.analysis_panels.update_available_groups(new_cell)
            
            # Update status
            self._update_status(f"Selected cell: {new_cell}", "info")
        else:
            # Clear groups
            self.analysis_panels.clear_groups()
            self._update_status("No cell selected", "info")
    
    def _on_analysis_type_changed(self, event):
        """Handle analysis type change.""" 
        new_analysis = event.new
        old_analysis = self.current_analysis
        
        self.current_analysis = new_analysis
        
        # Update analysis settings panel
        self.analysis_panels.show_settings_for_analysis(new_analysis)
        
        # Update available plot types
        self.plotting_manager.update_available_plots(new_analysis)
        
        # Update status
        self._update_status(f"Analysis type: {new_analysis}", "info")
    
    def _update_status(self, message: str, status_type: str = "info"):
        """Update status indicator."""
        
        status_colors = {
            "info": "#1976D2",
            "success": "#2E7D32", 
            "warning": "#F57C00",
            "error": "#D32F2F"
        }
        
        status_icons = {
            "info": "ℹ️",
            "success": "✅", 
            "warning": "⚠️",
            "error": "❌"
        }
        
        color = status_colors.get(status_type, "#666")
        icon = status_icons.get(status_type, "📊")
        
        self.status_indicator.object = f"""
        <div style='color: {color}; font-size: 14px; padding: 8px;'>
           {icon} {message}
        </div>
        """
    
    # ===== PUBLIC INTERFACE =====
    
    def get_current_state(self):
        """Get current state for components."""
        return {
            'current_cell': self.current_cell,
            'selected_groups': self.selected_groups,
            'current_analysis': self.current_analysis,
            'analysis_results': self.analysis_results
        }
    
    def update_state(self, key: str, value: Any):
        """Update state and notify components."""
        setattr(self, key, value)
        
        # Notify components of state changes if needed
        if key == 'selected_groups':
            self._update_status(f"Selected {len(value)} groups", "info")
    
    def cleanup(self):
        """Cleanup method for tab switching."""
        # Clear any background operations or watchers if needed
        pass