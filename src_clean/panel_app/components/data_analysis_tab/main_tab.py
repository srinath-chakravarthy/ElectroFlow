"""
Tab 3 Data Analysis - Main Coordinator

Handles layout coordination, main event handlers, and state management for Tab 3.
This is the central control point that coordinates between analysis panels, plotting, and results.

Architecture: 3-row layout with progressive disclosure and isolated state management.
"""

import panel as pn
import param
import pandas as pd
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
    analysis_results = param.Parameter(default=None, doc="Current analysis results (DataFrame or dict)")

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

        # Set reference for cross-component communication
        self.analysis_panels.main_tab = self

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

        # Complete layout - store in self._panel
        self._panel = pn.Column(
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
                ("Resistance Analysis", "resistance_analysis"),
                ("Kinetics Analysis", "kinetics_analysis"),
                ("dQ/dV Analysis", "dqdv_analysis")
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

            # Analyze button
            pn.pane.HTML("""
            <div style='margin: 20px 5px 10px 5px; border-top: 1px solid #E0E0E0; padding-top: 15px;'>
            </div>
            """),

            self._create_analyze_button(),

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

        return pn.Column(
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                💾 Export & Detailed Results
            </div>
            """),

            # Detailed results placeholder
            self.results_display.get_detailed_results_panel(),

            styles={
                'background': 'white',
                'border': '1px solid #E0E0E0',
                'border-radius': '8px',
                'padding': '15px',
                'margin': '10px'
            },
            height=200
        )

    def _create_analyze_button(self):
        """Create professional analyze button."""

        self.analyze_btn = pn.widgets.Button(
            name="🔍 Run Analysis",
            button_type="primary",
            width=200,
            height=40,
            disabled=True,  # Initially disabled
            margin=(10, 5)
        )
        self.analyze_btn.on_click(self._on_analyze_clicked)

        return self.analyze_btn

    def _setup_basic_event_handlers(self):
        """Setup basic event handlers for main components."""

        # Cell selector change
        self.cell_selector.param.watch(self._on_cell_changed, 'value')

        # Analysis type change
        self.analysis_type_selector.param.watch(self._on_analysis_type_changed, 'value')

    def _initialize_empty_state(self):
        """Initialize with empty/loading state."""

        try:
            # Load available cells
            cells = self.api.get_cells()

            if cells and len(cells) > 0:
                cell_options = [(cell['name'], cell['name']) for cell in cells]  # ✅ cell['name']
                cell_options.insert(0, ("Select a cell...", ""))
                self.cell_selector.options = cell_options
            else:
                self.cell_selector.options = [("No cells available", "")]

        except Exception as e:
            print(f"Error initializing Tab 3 state: {e}")
            self.cell_selector.options = [("Error loading cells", "")]

    # ===== EVENT HANDLERS =====

    def _on_cell_changed(self, event):
        """Handle cell selection change."""

        new_cell = event.new
        # Ensure we have a string value, not a tuple
        if isinstance(new_cell, (tuple, list)) and len(new_cell) > 1:
            new_cell = new_cell[1]  # Take the value part of (label, value) tuple
        elif isinstance(new_cell, (tuple, list)) and len(new_cell) == 1:
            new_cell = new_cell[0]

        # Ensure it's a string
        new_cell = str(new_cell) if new_cell is not None else ""
        self.current_cell = new_cell

        if new_cell:
            # Update groups in analysis panels
            self.analysis_panels.update_available_groups(new_cell)

            # Enable analyze button if we have a cell
            self.analyze_btn.disabled = False

            # Update status
            self._update_status(f"Selected cell: {new_cell}", "info")
        else:
            # Clear groups
            self.analysis_panels.clear_groups()
            self.analyze_btn.disabled = True
            self._update_status("No cell selected", "info")

    def _on_analysis_type_changed(self, event):
        """Handle analysis type change."""
        new_analysis = event.new
        # Ensure we have a string value, not a tuple
        if isinstance(new_analysis, (tuple, list)) and len(new_analysis) > 1:
            new_analysis = new_analysis[1]  # Take the value part of (label, value) tuple
        elif isinstance(new_analysis, (tuple, list)) and len(new_analysis) == 1:
            new_analysis = new_analysis[0]

        # Ensure it's a string
        new_analysis = str(new_analysis) if new_analysis is not None else "basic_statistics"
        old_analysis = self.current_analysis

        self.current_analysis = new_analysis

        # Update analysis settings panel
        self.analysis_panels.show_settings_for_analysis(new_analysis)

        # Update available plot types
        self.plotting_manager.update_available_plots(new_analysis)

        # Update status
        self._update_status(f"Analysis type: {new_analysis}", "info")

    def _on_analyze_clicked(self, event):
        """Handle analyze button click - Phase 2: Real backend integration."""

        try:
            # Update status
            self._update_status("Running analysis...", "info")
            self.analyze_btn.disabled = True

            # Get selected groups
            selected_groups = self.analysis_panels.get_selected_groups()
            if not selected_groups:
                self._update_status("No groups selected", "warning")
                self.analyze_btn.disabled = False
                return

            # Get current analysis settings
            settings = self.analysis_panels.get_current_settings(self.current_analysis)

            # Run analysis based on type
            results = self._run_analysis(self.current_analysis, selected_groups, settings)

            # Update visualization
            plot = self.plotting_manager.create_plot(self.current_analysis, results, settings)
            self.plotting_manager.update_plot_area(plot)

            # Update results display
            self.results_display.update_results_display(self.current_analysis, results)

            # Store results
            self.analysis_results = results

            # Update status
            self._update_status(f"Analysis complete: {len(selected_groups)} groups", "success")

        except Exception as e:
            self._update_status(f"Analysis error: {str(e)}", "error")
            print(f"Analysis error details: {e}")

        finally:
            self.analyze_btn.disabled = False

    def _run_analysis(self, analysis_type: str, selected_groups: List[str], settings: Dict[str, Any]) -> Dict[str, Any]:
        """Run analysis using new registry-based analysis engine."""
        
        try:
            # Import the new analysis engine
            from src_clean.backend.analysis_engine import get_analysis_engine
            from src_clean.core.query_filters import group_filter, AggregationType
            
            # Create analysis engine and data filters
            engine = get_analysis_engine()
            data_filters = group_filter(selected_groups, AggregationType.RAW)
            
            # Execute analysis using registry system
            result = engine.get_analysis(analysis_type, data_filters, settings)
            
            # Log successful registry-based analysis
            # Handle DataFrame vs dict results
            has_error = False
            segments_count = 0
            
            if hasattr(result, 'columns'):  # DataFrame
                has_error = 'error_message' in result.columns and not result['error_message'].isna().all()
                segments_count = len(result) if not has_error else 0
            else:  # Dict
                has_error = "error" in result
                segments_count = result.get('segments_analyzed', 0)
            
            if not has_error:
                print(f"✅ Registry analysis {analysis_type}: {segments_count} segments")
            
            return result
            
        except Exception as e:
            # Fallback to old methods if registry fails (safety net)
            print(f"⚠️  Registry analysis failed, using fallback: {e}")
            return self._run_analysis_fallback(analysis_type, selected_groups, settings)
    
    def _run_analysis_fallback(self, analysis_type: str, selected_groups: List[str], settings: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback to old analysis methods if registry fails."""
        
        if analysis_type == "basic_statistics":
            return self._run_basic_statistics_analysis(selected_groups, settings)
        elif analysis_type == "resistance_analysis":
            return self._run_resistance_analysis(selected_groups, settings)
        elif analysis_type == "kinetics_analysis":
            return self._run_kinetics_analysis(selected_groups, settings)
        elif analysis_type == "dqdv_analysis":
            return self._run_dqdv_analysis(selected_groups, settings)
        else:
            return {"error": f"Unknown analysis type: {analysis_type}"}

    def _run_basic_statistics_analysis(self, selected_groups: List[str], settings: Dict[str, Any]) -> Dict[str, Any]:
        """Run basic statistics analysis using real segment data structure."""

        try:
            print(f"Running basic statistics analysis for groups: {selected_groups}")

            # Get all segments from selected groups with technique information
            all_segments = self.api.get_multi_group_segments(selected_groups)

            if not all_segments:
                return {"error": "No segments found in selected groups", "groups": selected_groups}

            print(f"DEBUG: Got {len(all_segments)} segments from backend")
            if all_segments:
                print(f"DEBUG: First segment keys: {list(all_segments[0].keys())}")

            # Pass through the real segment data structure for plotting
            return {
                "analysis_type": "basic_statistics",
                "groups": selected_groups,
                "segments": all_segments,  # Real segment data with all fields
                "total_segments": len(all_segments),
                "groups_analyzed": len(selected_groups)
            }

        except Exception as e:
            print(f"Error in basic statistics analysis: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e), "groups": selected_groups}

    def _run_resistance_analysis(self, selected_groups: List[str], settings: Dict[str, Any]) -> Dict[str, Any]:
        """Run resistance analysis using existing backend."""

        try:
            # Use the existing electrochemical resistance analysis
            result = self.api.get_electrochemical_resistance_analysis(selected_groups)

            if not result:
                return {"error": "No resistance analysis data available", "groups": selected_groups}

            return {
                "analysis_type": "resistance_analysis",
                "groups": selected_groups,
                "data": result,
                "settings": settings
            }

        except Exception as e:
            print(f"Error in resistance analysis: {e}")
            return {"error": str(e), "groups": selected_groups}

    def _run_kinetics_analysis(self, selected_groups: List[str], settings: Dict[str, Any]) -> Dict[str, Any]:
        """Run kinetics analysis using existing backend."""

        try:
            # Use the existing electrochemical rest analysis for kinetics
            result = self.api.get_electrochemical_rest_analysis(selected_groups)

            if not result:
                return {"error": "No kinetics analysis data available", "groups": selected_groups}

            return {
                "analysis_type": "kinetics_analysis",
                "groups": selected_groups,
                "data": result,
                "settings": settings
            }

        except Exception as e:
            print(f"Error in kinetics analysis: {e}")
            return {"error": str(e), "groups": selected_groups}

    def _run_dqdv_analysis(self, selected_groups: List[str], settings: Dict[str, Any]) -> Dict[str, Any]:
        """dQ/dV analysis not implemented yet."""

        return {
            "error": "dQ/dV analysis is not implemented yet. Coming in future version.",
            "groups": selected_groups,
            "analysis_type": "dqdv_analysis"
        }

    # ===== UTILITY METHODS =====

    def _update_status(self, message: str, status_type: str = "info"):
        """Update status indicator with message and styling."""

        color_map = {
            "info": "#2196F3",
            "success": "#4CAF50",
            "warning": "#FF9800",
            "error": "#F44336"
        }

        icon_map = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌"
        }

        color = color_map.get(status_type, "#666")
        icon = icon_map.get(status_type, "📊")

        self.status_indicator.object = f"""
        <div style='color: {color}; font-size: 14px; padding: 8px;'>
           {icon} {message}
        </div>
        """

    # ===== PUBLIC INTERFACE =====

    @property
    def panel(self):
        """Return main panel for display."""
        if not hasattr(self, '_panel'):
            self._create_layout()
        return self._panel