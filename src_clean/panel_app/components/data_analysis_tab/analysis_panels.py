"""
Tab 3 Data Analysis - Analysis Panels & Widget Management

Handles all widget creation and analysis-specific settings.
Each analysis type gets its own widget creation methods.

Architecture: Widget factory pattern with analysis-specific panels.
"""

import panel as pn
import param
from typing import Dict, List, Any

# Registry imports for dynamic configuration
from src_clean.analysis.registry import get_analysis_registry


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
        
        # Get analysis registry for dynamic configuration
        self.registry = get_analysis_registry()
        
        # Cache for dynamically created settings panels
        self.settings_panels_cache = {}

    def _create_all_panels(self):
        """Create all widget panels."""

        # Groups selection panel (always visible)
        self._create_groups_panel()

        # Create analysis-specific settings panels dynamically from registry
        self._create_registry_based_settings_panels()

        # Filters panel (collapsible)
        self._create_filters_panel()

    # ===== GROUPS SECTION =====

    def _create_groups_panel(self):
        """Create groups selection panel (always visible)."""

        # Groups checkbox list
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

        # Button event handlers
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

    def _create_registry_based_settings_panels(self):
        """Create analysis-specific settings panels dynamically from registry."""
        
        try:
            # Get all available analyses from registry
            available_analyses = self.registry.list_analyses()
            
            for analysis_config in available_analyses:
                analysis_id = analysis_config.analysis_id
                analysis_name = analysis_config.name
                
                # Create settings panel for this analysis type
                settings_panel = self._create_settings_panel_for_analysis(analysis_config)
                
                # Cache the panel
                self.settings_panels_cache[analysis_id] = {
                    'panel': settings_panel,
                    'config': analysis_config,
                    'widgets': {}  # Will store references to widgets for value retrieval
                }
                
                print(f"✅ Created registry-based settings panel for {analysis_name}")
                
        except Exception as e:
            print(f"⚠️  Failed to create registry-based settings panels, using fallback: {e}")
            self._create_fallback_settings_panels()
    
    def _create_settings_panel_for_analysis(self, analysis_config):
        """Create a settings panel for a specific analysis based on registry config."""
        
        analysis_id = analysis_config.analysis_id
        analysis_name = analysis_config.name
        
        # Default settings based on analysis type
        settings_widgets = []
        widget_refs = {}  # Store widget references for value retrieval
        
        # Analysis-specific settings based on analysis ID
        if analysis_id == "basic_statistics":
            # Metrics selection
            metrics_widget = pn.widgets.CheckBoxGroup(
                name="Metrics to Include",
                options=["Duration", "Start Voltage", "End Voltage", "Voltage Range", "Capacity", "Energy"],
                value=["Duration", "Start Voltage", "End Voltage", "Capacity"],
                width=300
            )
            settings_widgets.append(metrics_widget)
            widget_refs['metrics'] = metrics_widget
            
            # Statistics type selection
            stats_widget = pn.widgets.CheckBoxGroup(
                name="Statistics to Compute",
                options=["Mean", "Std Dev", "Min", "Max", "Count"],
                value=["Mean", "Std Dev", "Count"],
                width=300
            )
            settings_widgets.append(stats_widget)
            widget_refs['statistics'] = stats_widget
            
        elif analysis_id == "dqdv_analysis":
            # Method selection
            method_widget = pn.widgets.Select(
                name="dQ/dV Method",
                options=["Numerical Derivative", "Curve Smoothing", "Moving Average"],
                value="Numerical Derivative",
                width=300
            )
            settings_widgets.append(method_widget)
            widget_refs['method'] = method_widget
            
            # Window size
            window_widget = pn.widgets.IntSlider(
                name="Smoothing Window",
                start=1, end=50, value=5, step=1,
                width=300
            )
            settings_widgets.append(window_widget)
            widget_refs['window_size'] = window_widget
            
            # Smoothing factor
            smoothing_widget = pn.widgets.FloatSlider(
                name="Smoothing Factor",
                start=0.0, end=1.0, value=0.1, step=0.01,
                width=300
            )
            settings_widgets.append(smoothing_widget)
            widget_refs['smoothing'] = smoothing_widget
            
        elif analysis_id == "kinetics_analysis":
            # Fitting model
            fit_type_widget = pn.widgets.Select(
                name="Fitting Model",
                options=["Exponential", "Power Law", "Combined"],
                value="Combined",
                width=300
            )
            settings_widgets.append(fit_type_widget)
            widget_refs['fit_type'] = fit_type_widget
            
            # Time range
            time_range_widget = pn.widgets.RangeSlider(
                name="Time Range (s)",
                start=0, end=1000, value=(10, 100), step=1,
                width=300
            )
            settings_widgets.append(time_range_widget)
            widget_refs['time_range'] = time_range_widget
            
            # Quality threshold
            quality_widget = pn.widgets.FloatSlider(
                name="Quality Threshold (R²)",
                start=0.5, end=1.0, value=0.95, step=0.01,
                width=300
            )
            settings_widgets.append(quality_widget)
            widget_refs['quality_threshold'] = quality_widget
            
        elif analysis_id in ["resistance_analysis", "equilibrium_analysis", "current_decay_analysis"]:
            # Simple analyses with minimal settings
            info_widget = pn.pane.HTML(
                f"<em>Analysis '{analysis_name}' uses default settings.</em>"
            )
            settings_widgets.append(info_widget)
        
        else:
            # Generic fallback for unknown analysis types
            info_widget = pn.pane.HTML(
                f"<em>Analysis '{analysis_name}' - settings not yet configured.</em>"
            )
            settings_widgets.append(info_widget)
        
        # Store widget references for value retrieval
        if analysis_id in self.settings_panels_cache:
            self.settings_panels_cache[analysis_id]['widgets'] = widget_refs
        
        # Create panel with header and settings
        panel = pn.Column(
            pn.pane.HTML(f"<strong>{analysis_name} Settings</strong>"),
            *settings_widgets,
            width=320,
            visible=False  # Start hidden
        )
        
        return panel
    
    def _create_fallback_settings_panels(self):
        """Fallback settings panels if registry fails."""
        
        # Basic fallback panel
        fallback_panel = pn.Column(
            pn.pane.HTML("<strong>Analysis Settings</strong>"),
            pn.pane.HTML("<em>Using default settings for analysis.</em>"),
            width=320
        )
        
        # Cache fallback for basic_statistics
        self.settings_panels_cache["basic_statistics"] = {
            'panel': fallback_panel,
            'config': None,
            'widgets': {}
        }

    def _create_filters_panel(self):
        """Create general filters panel (used by all analysis types)."""

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
        """Get settings panel for current analysis type using registry."""

        # Create container for current settings panel
        self.settings_container = pn.Column(width=320)
        
        # Show initial panel (basic_statistics)
        self.show_settings_for_analysis(self.current_analysis)
        
        return self.settings_container

    def show_settings_for_analysis(self, analysis_type: str):
        """Show settings panel for specific analysis type using registry."""

        self.current_analysis = analysis_type
        
        try:
            # Hide all existing panels first
            for cached_analysis in self.settings_panels_cache.values():
                if cached_analysis.get('panel'):
                    cached_analysis['panel'].visible = False
            
            # Get the panel for this analysis type
            analysis_cache = self.settings_panels_cache.get(analysis_type)
            
            if analysis_cache and analysis_cache.get('panel'):
                # Show the registry-based panel
                target_panel = analysis_cache['panel']
                target_panel.visible = True
                
                # Update container contents
                if hasattr(self, 'settings_container'):
                    self.settings_container.clear()
                    self.settings_container.append(target_panel)
                    
                    # Always show filters at bottom
                    self.settings_container.append(self.filters_panel)
                    
                print(f"✅ Showing registry-based settings for {analysis_type}")
                
            else:
                # Fallback: create simple settings panel
                print(f"⚠️  No registry settings found for {analysis_type}, using fallback")
                fallback_panel = pn.Column(
                    pn.pane.HTML(f"<strong>{analysis_type.replace('_', ' ').title()} Settings</strong>"),
                    pn.pane.HTML("<em>Using default settings for this analysis.</em>"),
                    width=320
                )
                
                if hasattr(self, 'settings_container'):
                    self.settings_container.clear()
                    self.settings_container.append(fallback_panel)
                    self.settings_container.append(self.filters_panel)
                    
        except Exception as e:
            print(f"❌ Error showing settings for {analysis_type}: {e}")
            # Show basic fallback
            if hasattr(self, 'settings_container'):
                self.settings_container.clear()
                self.settings_container.append(
                    pn.pane.HTML(f"<em>Error loading settings for {analysis_type}</em>")
                )
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
        """Get current settings for specified analysis type using registry."""

        try:
            # Get cached analysis info
            analysis_cache = self.settings_panels_cache.get(analysis_type, {})
            widgets = analysis_cache.get('widgets', {})
            
            if not widgets:
                # Return default settings for analyses without widgets
                return {'analysis_type': analysis_type}
            
            # Extract current values from widgets
            settings = {'analysis_type': analysis_type}
            
            for setting_name, widget in widgets.items():
                try:
                    settings[setting_name] = widget.value
                except Exception as widget_error:
                    print(f"⚠️  Error getting value for {setting_name}: {widget_error}")
                    settings[setting_name] = None
            
            print(f"✅ Retrieved registry-based settings for {analysis_type}: {list(settings.keys())}")
            return settings
            
        except Exception as e:
            print(f"⚠️  Error getting settings for {analysis_type}, using fallback: {e}")
            return {'analysis_type': analysis_type}

    def get_selected_groups(self) -> List[str]:
        """Get currently selected group IDs for backend calls."""

        # Convert display names back to group IDs using the mapping
        selected_display_names = self.groups_checkboxes.value
        selected_ids = []

        for display_name in selected_display_names:
            group_id = self.group_id_mapping.get(display_name)
            if group_id:
                selected_ids.append(str(group_id))

        return selected_ids

    def get_filter_settings(self) -> Dict[str, Any]:
        """Get current filter settings."""

        return {
            'technique_filters': self.technique_filters.value,
            'voltage_range': self.voltage_range.value
        }