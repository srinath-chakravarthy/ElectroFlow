"""
Tab 3 Data Analysis - Analysis Panels & Widget Management

Handles all widget creation and analysis-specific settings.
Each analysis type gets its own widget creation methods.

Architecture: Widget factory pattern with analysis-specific panels.
"""

import panel as pn
import param
from typing import Dict, List, Any


class AnalysisPanels:
    """
    Handles all widget creation and analysis-specific settings.
    Each analysis type gets its own widget creation methods.
    
    Phase 1: Basic groups selection and placeholder settings
    Phase 2: Functional groups selection with backend integration  
    Phase 3: Analysis-specific settings panels
    Phase 4: Advanced filtering and parameter controls
    """
    
    def __init__(self, api):
        self.api = api
        
        # Store reference to main tab for button updates
        self.main_tab = None
        
        # Create all panels
        self._create_all_panels()
        
        # Current state
        self.current_analysis = "basic_statistics"
        self.selected_groups = []
    
    def _create_all_panels(self):
        """Create all widget panels."""
        
        # Groups selection panel (always visible)
        self._create_groups_panel()
        
        # Analysis-specific settings panels
        self._create_basic_statistics_settings()
        self._create_dqdv_settings()
        self._create_kinetics_settings()
        
        # Filters panel (collapsible)
        self._create_filters_panel()
    
    # ===== GROUPS SECTION =====
    
    def _create_groups_panel(self):
        """Create groups selection panel (always visible)."""
        
        # Groups checkbox list (placeholder for Phase 1)
        self.groups_checkboxes = pn.widgets.CheckBoxGroup(
            name="Available Groups",
            options=[],
            value=[],
            width=300
        )
        
        # Selection summary
        self.groups_summary = pn.pane.HTML(
            "<em>No groups available. Please select a cell.</em>",
            width=300
        )
        
        # Quick selection buttons
        self.select_all_btn = pn.widgets.Button(
            name="Select All", 
            button_type="primary",
            width=80,
            disabled=True
        )
        
        self.clear_all_btn = pn.widgets.Button(
            name="Clear All",
            button_type="default", 
            width=80,
            disabled=True
        )
        
        # Button event handlers (Phase 2: functional)
        self.select_all_btn.on_click(self._on_select_all)
        self.clear_all_btn.on_click(self._on_clear_all)
        
        # Groups selection change handler  
        self.groups_checkboxes.param.watch(self._on_groups_selection_changed, 'value')
        
        # Groups panel layout
        self.groups_panel = pn.Column(
            self.groups_checkboxes,
            self.groups_summary,
            pn.Row(
                self.select_all_btn,
                self.clear_all_btn,
                margin=(10, 0)
            ),
            width=320
        )
    
    def get_groups_panel(self):
        """Return the groups selection panel."""
        return self.groups_panel
    
    # ===== ANALYSIS SETTINGS BY TYPE =====
    
    def _create_basic_statistics_settings(self):
        """Basic Statistics analysis settings panel."""
        
        self.basic_stats_metrics = pn.widgets.CheckBoxGroup(
            name="Metrics to Include",
            options=[
                "Duration", "Start Voltage", "End Voltage", 
                "Voltage Range", "Capacity", "Energy"
            ],
            value=["Duration", "Start Voltage", "End Voltage", "Capacity"],
            width=300
        )
        
        self.basic_stats_statistics = pn.widgets.CheckBoxGroup(
            name="Statistics to Compute", 
            options=["Mean", "Std Dev", "Min", "Max", "Count"],
            value=["Mean", "Std Dev", "Count"],
            width=300
        )
        
        self.basic_statistics_panel = pn.Column(
            pn.pane.HTML("<strong>Basic Statistics Settings</strong>"),
            self.basic_stats_metrics,
            self.basic_stats_statistics,
            width=320
        )
    
    def _create_dqdv_settings(self):
        """dQ/dV Analysis specific settings panel."""
        
        self.dqdv_method = pn.widgets.Select(
            name="Method",
            options=["Savitzky-Golay", "Spline", "Finite Difference"],
            value="Savitzky-Golay",
            width=200
        )
        
        self.dqdv_window = pn.widgets.IntSlider(
            name="Window Size", 
            start=5, end=21, step=2, value=7,
            width=200
        )
        
        self.dqdv_smoothing = pn.widgets.Select(
            name="Smoothing",
            options=["Auto", "Light", "Heavy", "Custom"],
            value="Auto",
            width=200
        )
        
        self.dqdv_panel = pn.Column(
            pn.pane.HTML("<strong>dQ/dV Analysis Settings</strong>"),
            self.dqdv_method,
            self.dqdv_window, 
            self.dqdv_smoothing,
            width=320,
            visible=False  # Hidden initially
        )
    
    def _create_kinetics_settings(self):
        """Kinetics Analysis specific settings panel."""
        
        self.kinetics_fit_type = pn.widgets.Select(
            name="Fit Type",
            options=["Exponential", "Square Root", "Both"],
            value="Both",
            width=200
        )
        
        self.kinetics_time_range = pn.widgets.Select(
            name="Time Range", 
            options=["Auto", "Custom"],
            value="Auto",
            width=200
        )
        
        self.kinetics_quality_threshold = pn.widgets.FloatSlider(
            name="Min R² Threshold",
            start=0.5, end=1.0, step=0.01, value=0.8,
            width=200
        )
        
        self.kinetics_panel = pn.Column(
            pn.pane.HTML("<strong>Kinetics Analysis Settings</strong>"),
            self.kinetics_fit_type,
            self.kinetics_time_range,
            self.kinetics_quality_threshold,
            width=320,
            visible=False  # Hidden initially
        )
    
    # ===== FILTERS SECTION =====
    
    def _create_filters_panel(self):
        """Create filters section (collapsible)."""
        
        self.technique_filters = pn.widgets.CheckBoxGroup(
            name="Technique Filters",
            options=["REST", "CC", "CV", "EIS", "CP"],
            value=["REST", "CC", "CV"],
            width=300
        )
        
        self.voltage_range = pn.widgets.RangeSlider(
            name="Voltage Range (V)",
            start=0.0, end=5.0, value=(2.5, 4.2), step=0.1,
            width=300
        )
        
        self.apply_filters_btn = pn.widgets.Button(
            name="Apply Filters",
            button_type="primary",
            width=120
        )
        
        self.reset_filters_btn = pn.widgets.Button(
            name="Reset All",
            button_type="default",
            width=120
        )
        
        self.filters_panel = pn.Column(
            pn.pane.HTML("<strong>🔍 Filters</strong>"),
            self.technique_filters,
            self.voltage_range,
            pn.Row(
                self.apply_filters_btn,
                self.reset_filters_btn,
                margin=(10, 0)
            ),
            width=320
        )
    
    # ===== PANEL MANAGEMENT =====
    
    def get_current_settings_panel(self):
        """Get settings panel for current analysis type.""" 
        
        # Container that will hold the current settings panel
        self.settings_container = pn.Column(
            self.basic_statistics_panel,  # Default to basic statistics
            width=320
        )
        
        return self.settings_container
    
    def show_settings_for_analysis(self, analysis_type: str):
        """Show settings panel for specific analysis type."""
        
        self.current_analysis = analysis_type
        
        # Hide all panels first
        self.basic_statistics_panel.visible = False
        self.dqdv_panel.visible = False  
        self.kinetics_panel.visible = False
        
        # Show appropriate panel
        if analysis_type == "basic_statistics":
            self.basic_statistics_panel.visible = True
        elif analysis_type == "dqdv_analysis":
            self.dqdv_panel.visible = True
        elif analysis_type == "kinetics_analysis":
            self.kinetics_panel.visible = True
        
        # Update container contents
        self.settings_container.clear()
        if analysis_type == "basic_statistics":
            self.settings_container.append(self.basic_statistics_panel)
        elif analysis_type == "dqdv_analysis":
            self.settings_container.append(self.dqdv_panel)
        elif analysis_type == "kinetics_analysis":  
            self.settings_container.append(self.kinetics_panel)
        
        # Always show filters at bottom
        self.settings_container.append(self.filters_panel)
    
    # ===== GROUPS MANAGEMENT =====
    
    def update_available_groups(self, cell_name: str):
        """Update available groups for selected cell - Phase 2: Real API integration."""
        
        try:
            # Phase 2: Get real groups from API
            groups_data = self.api.get_cell_groups_with_counts(cell_name)
            
            if groups_data:
                # Format groups for display: "GroupName (15 segments)"
                group_options = [
                    f"{group['group_name']} ({group['segment_count']} segments)" 
                    for group in groups_data
                ]
                
                # Store group IDs for backend calls
                self.group_id_mapping = {
                    f"{group['group_name']} ({group['segment_count']} segments)": group['group_id']
                    for group in groups_data
                }
            else:
                # Fallback to placeholder if no groups
                group_options = [
                    f"No groups available for {cell_name}",
                ]
                self.group_id_mapping = {}
            
            self.groups_checkboxes.options = group_options
            self.groups_checkboxes.value = []
            
            # Enable/disable buttons based on availability
            has_groups = len(group_options) > 0 and not group_options[0].startswith("No groups")
            self.select_all_btn.disabled = not has_groups
            self.clear_all_btn.disabled = not has_groups
            
            # Update summary
            self._update_groups_summary()
            
        except Exception as e:
            print(f"Error updating groups for {cell_name}: {e}")
            # Fallback to placeholder
            placeholder_groups = [
                f"Template_All_Rest ({cell_name})",
                f"Template_All_CC ({cell_name})", 
                f"User_Custom_Group ({cell_name})"
            ]
            self.groups_checkboxes.options = placeholder_groups
            self.groups_checkboxes.value = []
            self.group_id_mapping = {group: f"placeholder_{i}" for i, group in enumerate(placeholder_groups)}
            
            self.select_all_btn.disabled = False
            self.clear_all_btn.disabled = False
            self._update_groups_summary()
    
    def clear_groups(self):
        """Clear groups selection."""
        
        self.groups_checkboxes.options = []
        self.groups_checkboxes.value = []
        self.selected_groups = []
        
        # Disable buttons
        self.select_all_btn.disabled = True
        self.clear_all_btn.disabled = True
        
        # Update summary
        self.groups_summary.object = "<em>No groups available. Please select a cell.</em>"
    
    def _update_groups_summary(self):
        """Update groups selection summary."""
        
        total_groups = len(self.groups_checkboxes.options)
        selected_count = len(self.groups_checkboxes.value)
        
        if total_groups == 0:
            self.groups_summary.object = "<em>No groups available.</em>"
        else:
            self.groups_summary.object = f"""
            <div style='color: #666; font-size: 13px; margin: 5px 0;'>
                Selected: <strong>{selected_count}</strong> of {total_groups} groups
            </div>
            """
    
    # ===== EVENT HANDLERS =====
    
    def _on_select_all(self, event):
        """Select all available groups."""
        self.groups_checkboxes.value = list(self.groups_checkboxes.options)
        self._update_groups_summary()
    
    def _on_clear_all(self, event):
        """Clear all group selections."""
        self.groups_checkboxes.value = []
        self._update_groups_summary()
    
    def _on_groups_selection_changed(self, event):
        """Handle groups selection change - enable/disable analyze button."""
        self._update_groups_summary()
        
        # Enable/disable analyze button based on selection
        if hasattr(self, 'main_tab') and self.main_tab:
            selected_count = len(self.groups_checkboxes.value)
            if hasattr(self.main_tab, 'analyze_btn'):
                self.main_tab.analyze_btn.disabled = (selected_count == 0)
    
    # ===== SETTINGS MANAGEMENT =====
    
    def get_current_settings(self, analysis_type: str) -> Dict[str, Any]:
        """Get current settings for specified analysis type."""
        
        if analysis_type == "basic_statistics":
            return {
                'metrics': self.basic_stats_metrics.value,
                'statistics': self.basic_stats_statistics.value
            }
        elif analysis_type == "dqdv_analysis":
            return {
                'method': self.dqdv_method.value,
                'window_size': self.dqdv_window.value,
                'smoothing': self.dqdv_smoothing.value
            }
        elif analysis_type == "kinetics_analysis":
            return {
                'fit_type': self.kinetics_fit_type.value,
                'time_range': self.kinetics_time_range.value,
                'quality_threshold': self.kinetics_quality_threshold.value
            }
        else:
            return {}
    
    def get_selected_groups(self) -> List[str]:
        """Get currently selected group IDs for backend calls."""
        selected_display_names = list(self.groups_checkboxes.value)
        
        # Convert display names to group IDs if mapping exists
        if hasattr(self, 'group_id_mapping') and self.group_id_mapping:
            return [self.group_id_mapping.get(display_name, display_name) 
                   for display_name in selected_display_names]
        
        # Fallback to display names
        return selected_display_names
    
    def get_filter_settings(self) -> Dict[str, Any]:
        """Get current filter settings.""" 
        return {
            'techniques': self.technique_filters.value,
            'voltage_range': self.voltage_range.value
        }