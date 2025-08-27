"""
Electrochemical Data Explorer Tab

Unified visual data explorer for electrochemical analysis that enables rapid, 
interactive exploration of segment-level data across single or multiple cells.

Features:
- Cell-centric workflow with multi-select capability
- Technique-based auto-configuration
- Interactive plotting with hvplot integration
- Dual filter system (temporal + data-based)
- Registry-driven column discovery
"""

import panel as pn
import param
import pandas as pd
import polars as pl
import hvplot.pandas
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ElectrochemicalExplorerTab(param.Parameterized):
    """
    Electrochemical Data Explorer Tab with cell-first workflow.
    
    Provides comprehensive visual exploration interface:
    - Cell Selection Panel: Multi-cell selection with summary data
    - Configuration Panel: Technique selection and auto-configured controls
    - Visualization Panel: Interactive plotting with hvplot
    """
    
    # Status parameters
    status_message = param.String(default="Ready", doc="Current status message")
    dataset_loaded = param.Boolean(default=False, doc="Whether dataset is loaded")
    explorer_ready = param.Boolean(default=False, doc="Whether explorer is ready")
    
    def __init__(self, api, **params):
        super().__init__(**params)
        self.api = api
        
        # State management
        self.selected_cells = []
        self.current_technique = "All"
        self.current_dataset = None
        self.available_columns = {}
        self.registry_columns = {}
        
        # Get registry for column discovery
        from src_clean.analysis.registry import get_analysis_registry
        self.registry = get_analysis_registry()
        
        # Create components
        self._create_components()
        self._setup_layout()
        self._setup_callbacks()
        
        # Initialize data
        self._refresh_cells()
        
        logger.info("Electrochemical Explorer Tab initialized")
    
    def _create_components(self):
        """Create all UI components for explorer interface."""
        
        # === CELL SELECTION PANEL ===
        self._create_cell_selection_components()
        
        # === CONFIGURATION PANEL ===
        self._create_configuration_components()
        
        # === RIGHT PANEL COMPONENTS ===
        self._create_right_panel_components()
        
        # === LEGACY VISUALIZATION (for data feedback) ===
        self._create_visualization_components()
    
    def _create_cell_selection_components(self):
        """Create cell selection panel components."""
        
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
        
        # Cell selection controls
        self.refresh_cells_btn = pn.widgets.Button(
            name="🔄 Refresh Cells",
            button_type="primary",
            sizing_mode='stretch_width',
            margin=(5, 5)
        )
        
        # Cell selection status
        self.cell_status_html = pn.pane.HTML(
            """<div style='padding:10px; background:#f8f9fa; border-radius:4px; margin:5px;'>
               <b>Cell Selection:</b> No cells selected
               </div>""",
            sizing_mode='stretch_width'
        )
    
    def _create_configuration_components(self):
        """Create clean left panel configuration components."""
        
        # Analysis Category Selection (Radio buttons)
        self.analysis_category_radio = pn.widgets.RadioButtonGroup(
            name="Analysis Category",
            options=["Basic Statistics", "Resistance", "Kinetics", "Equilibrium", "Current Decay"],
            button_type="primary",
            sizing_mode='stretch_width',
            margin=(5, 5)
        )
        
        # Specific Analysis Selection (Dropdown - populated dynamically)
        self.analysis_select = pn.widgets.Select(
            name="Specific Analysis",
            options=[("Select category first", "")],
            sizing_mode='stretch_width',
            margin=(5, 5)
        )
        
        # Temperature Filter (Optional)
        self.temperature_filter = pn.widgets.Select(
            name="Temperature Filter",
            options=[("All Temperatures", "all"), ("25°C", "25"), ("Room Temp", "rt")],
            value="all",
            sizing_mode='stretch_width',
            margin=(5, 5)
        )
        
        # Status display
        self.config_status = pn.pane.HTML(
            "<p><i>Select cells and analysis to begin</i></p>",
            sizing_mode='stretch_width',
            margin=(5, 5)
        )
    
    def _create_right_panel_components(self):
        """Create right panel with config bar and plot area."""
        
        # Top configuration bar (120px fixed height)
        self.config_bar = pn.Row(
            pn.pane.HTML(
                "<div style='padding:10px; background:#f8f9fa; border-radius:5px;'>"
                "<p><b>📊 Plot Configuration</b> - Select analysis to configure</p>"
                "</div>"
            ),
            height=120,
            sizing_mode='stretch_width',
            margin=(5, 5)
        )
        
        # Bottom plot area (flexible)
        self.plot_area = pn.Column(
            pn.pane.HTML(
                "<div style='text-align:center; padding:50px;'>"
                "<h3>📈 Electrochemical Analysis Plots</h3>"
                "<p>Configure analysis in left panel to generate plots</p>"
                "</div>",
                sizing_mode='stretch_both'
            ),
            sizing_mode='stretch_both',
            margin=(5, 5)
        )
    
    def _create_visualization_components(self):
        """Create visualization panel components."""
        
        # Data feedback display
        self.data_feedback_tabulator = pn.widgets.Tabulator(
            value=pd.DataFrame({
                'Cell': [],
                'Segments': [], 
                'Quality': [],
                'Status': []
            }),
            pagination='local',
            page_size=10,
            sizing_mode='stretch_width',
            sortable=True,
            show_index=False,
            height=200,
            margin=(5, 5)
        )
        
        # Plot area
        self.plot_pane = pn.pane.HTML(
            """<div style='padding:40px; text-align:center; background:#f8f9fa; border-radius:8px; margin:10px;'>
               <h3>📊 Interactive Visualization</h3>
               <p>Configure explorer to generate interactive plots</p>
               </div>""",
            sizing_mode='stretch_both',
            min_height=400
        )
    
    def _setup_layout(self):
        """Setup clean 30/70 proportional layout."""
        
        # LEFT PANEL (30%) - Analysis Selection
        left_panel = pn.Column(
            pn.pane.HTML("<h4>🔋 Cell & Analysis Selection</h4>"),
            
            # Cell Selection Section
            pn.pane.HTML("<h5>Data Selection</h5>"),
            self.cell_tabulator,
            self.refresh_cells_btn,
            self.cell_status_html,
            
            pn.Divider(),
            
            # Analysis Selection Section  
            pn.pane.HTML("<h5>Analysis Configuration</h5>"),
            self.analysis_category_radio,
            self.analysis_select,
            self.temperature_filter,
            self.config_status,
            
            width_policy='max',  # Takes minimum needed space
            sizing_mode='stretch_height',
            margin=(10, 10)
        )
        
        # RIGHT PANEL (70%) - Config Bar + Plot Area
        right_panel = pn.Column(
            self.config_bar,    # Top config bar (120px)
            self.plot_area,     # Bottom plot area (flexible)
            sizing_mode='stretch_both',
            margin=(10, 10)
        )
        
        # MAIN LAYOUT - 30/70 Proportional Split  
        self.panel = pn.Row(
            (left_panel, 30),    # 30% width
            (right_panel, 70),   # 70% width
            sizing_mode='stretch_both'
        )
    
    def _setup_callbacks(self):
        """Setup component callbacks."""
        
        # Cell selection callbacks
        self.cell_tabulator.param.watch(self._on_cell_selection_changed, 'selection')
        self.refresh_cells_btn.on_click(self._on_refresh_cells)
        
        # Analysis selection callbacks
        self.analysis_category_radio.param.watch(self._on_analysis_category_changed, 'value')
        self.analysis_select.param.watch(self._on_analysis_changed, 'value')
    
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
            
            # Update analysis category radio based on available data
            if selected_cells:
                self._update_analysis_options(selected_cells)
            
            # Update cell status
            if selected_cells:
                status_text = f"<b>Cell Selection:</b> {len(selected_cells)} cells selected ({', '.join(selected_cells[:3])}{'...' if len(selected_cells) > 3 else ''})"
                self.cell_status_html.object = f"""<div style='padding:10px; background:#e8f5e8; border-radius:4px; margin:5px; border-left:3px solid #2e7d32;'>
                   {status_text}
                   </div>"""
                self._update_status(f"Selected {len(selected_cells)} cells", "info")
            else:
                self.cell_status_html.object = """<div style='padding:10px; background:#f8f9fa; border-radius:4px; margin:5px;'>
                   <b>Cell Selection:</b> No cells selected
                   </div>"""
                self._update_status("No cells selected", "info")
                
        except Exception as e:
            logger.error(f"Cell selection error: {e}")
            self._update_status("Selection error", "error")
    
    def _on_refresh_cells(self, event):
        """Handle refresh cells button click."""
        self._refresh_cells()
    
    def _on_generate_plot(self, event):
        """Handle generate plot button click."""
        try:
            if not self.selected_cells:
                self._update_status("No cells selected", "warning")
                return
                
            self._update_status("Generating plot...", "loading")
            
            # Get selected columns from active tab
            selected_columns = self._get_selected_columns()
            if not selected_columns:
                self._update_status("No columns selected for plotting", "warning")
                return
            
            # Load dataset if not already loaded
            if self.current_dataset is None:
                self._load_dataset()
            
            # Generate plot with selected columns
            self._generate_analysis_plot(selected_columns)
            
            self._update_status("Plot generated successfully", "success")
            
        except Exception as e:
            logger.error(f"Failed to generate plot: {e}")
            self._update_status(f"Plot generation failed: {str(e)}", "error")
    
    def _update_analysis_options(self, selected_cells):
        """Update analysis options based on available data from selected cells."""
        try:
            # Get available techniques for selected cells
            available_techniques = self._get_available_techniques(selected_cells)
            
            # Update status
            technique_text = f"Available techniques: {', '.join(available_techniques)}" if available_techniques else "Loading techniques..."
            self.config_status.object = f"<p><b>✅ Data Ready:</b> {len(selected_cells)} cells selected<br><small>{technique_text}</small></p>"
            
        except Exception as e:
            logger.error(f"Failed to update analysis options: {e}")
            self.config_status.object = f"<p><b>❌ Configuration Error:</b> {str(e)}</p>"
    
    def _on_analysis_category_changed(self, event):
        """Handle analysis category selection change."""
        category = event.new
        if not category:
            return
            
        try:
            # Map category to analysis IDs using registry
            category_map = {
                "Basic Statistics": "basic_statistics_analytics",
                "Resistance": "resistance_analytics", 
                "Kinetics": "kinetics_analytics",
                "Equilibrium": "equilibrium_analytics",
                "Current Decay": "current_decay_analytics"
            }
            
            if category in category_map:
                analysis_id = category_map[category]
                config = self.registry.get_analysis(analysis_id)
                
                if config:
                    # Update dropdown with single option (can be expanded later)
                    self.analysis_select.options = [(config.name, analysis_id)]
                    self.analysis_select.value = analysis_id
                    
                    logger.info(f"Selected analysis category: {category} -> {analysis_id}")
                
        except Exception as e:
            logger.error(f"Failed to update analysis options for category {category}: {e}")
    
    def _on_analysis_changed(self, event):
        """Handle specific analysis selection change.""" 
        analysis_id = event.new
        if not analysis_id:
            return
            
        try:
            config = self.registry.get_analysis(analysis_id)
            if config:
                # Update config bar for this analysis
                self._update_config_bar(analysis_id, config)
                logger.info(f"Selected analysis: {config.name} ({analysis_id})")
                
        except Exception as e:
            logger.error(f"Failed to handle analysis change to {analysis_id}: {e}")
    
    def _update_config_bar(self, analysis_id, config):
        """Update the top configuration bar for the selected analysis."""
        try:
            # For now, just show analysis info - will be enhanced in Phase B
            config_html = f"""
            <div style='padding:10px;'>
                <h4>📊 {config.name}</h4>
                <p><strong>Description:</strong> {config.description}</p>
                <p><strong>Applicable to:</strong> {', '.join(config.applicable_techniques)}</p>
                <p><em>Plot configuration controls will be added in Phase B</em></p>
            </div>
            """
            
            self.config_bar.clear()
            self.config_bar.append(pn.pane.HTML(config_html, sizing_mode='stretch_width'))
            
        except Exception as e:
            logger.error(f"Failed to update config bar: {e}")
    
    def _get_available_techniques(self, selected_cells):
        """Get available techniques from selected cells."""
        try:
            summary = self.api.get_research_data_summary(selected_cells)
            return summary.get('techniques', [])
        except Exception as e:
            logger.warning(f"Failed to get techniques: {e}")
            return []
    
    # === REMOVED: Complex accordion methods replaced by simple dropdown approach ===
    # Old _populate_trends_section, _populate_quality_section, _populate_insights_section
    # methods removed for cleaner UI approach
    
    # === OLD COLUMN SELECTION METHOD - WILL BE REPLACED IN PHASE B ===
    def _on_column_selection_changed(self, event):
        """Handle column selection change (Phase B implementation)."""
        # TODO: Implement in Phase B with new PlotState system
        pass
    
    def _get_selected_columns(self):
        """Get currently selected columns (Phase B implementation)."""
        # TODO: Implement in Phase B with config bar controls
        return []
    
    def _generate_analysis_plot(self, selected_columns):
        """Generate plot with selected columns using context-sensitive configuration modal."""
        try:
            if not selected_columns:
                self._update_status("No columns selected for plotting", "warning")
                return
            
            # Show plot configuration modal
            self._show_plot_configuration_modal(selected_columns)
            
        except Exception as e:
            logger.error(f"Failed to setup plot configuration: {e}")
            self._update_status(f"Plot configuration error: {str(e)}", "error")
    
    def _show_plot_configuration_modal(self, selected_columns):
        """Show context-sensitive plot configuration modal."""
        try:
            # Create plot configuration modal
            modal_content = self._create_plot_config_modal_content(selected_columns)
            
            # Create modal dialog
            self.plot_config_modal = pn.template.Modal(
                modal_content,
                title="🎯 Configure Plot",
                sizing_mode='stretch_width',
                max_width=800,
                margin=(10, 10)
            )
            
            # Show modal
            self.plot_config_modal.show()
            
        except Exception as e:
            logger.error(f"Failed to show plot configuration modal: {e}")
            self._update_status(f"Modal error: {str(e)}", "error")
    
    def _create_plot_config_modal_content(self, selected_columns):
        """Create content for plot configuration modal with context-sensitive options."""
        
        # Analyze selected columns to determine plot context
        plot_context = self._analyze_plot_context(selected_columns)
        
        # Header with context summary
        header_html = f"""
        <h4>🎯 Plot Configuration</h4>
        <p><strong>Selected Columns:</strong> {len(selected_columns)} columns from {len(set(col['section'] for col in selected_columns))} sections</p>
        <p><strong>Plot Context:</strong> {plot_context['description']}</p>
        """
        
        header = pn.pane.HTML(header_html, margin=(5, 5))
        
        # X-axis configuration
        x_axis_options = self._get_x_axis_options(plot_context)
        self.x_axis_select = pn.widgets.Select(
            name="X-Axis",
            options=x_axis_options,
            value=plot_context['suggested_x_axis'],
            sizing_mode='stretch_width',
            margin=(5, 5)
        )
        
        # Y-axis configuration (multi-select for multiple metrics)
        y_axis_options = [(col['display_name'], col['name']) for col in selected_columns]
        self.y_axis_multiselect = pn.widgets.MultiSelect(
            name="Y-Axis (Multi-Select)",
            options=y_axis_options,
            value=[col['name'] for col in selected_columns[:3]],  # Default to first 3
            size=min(8, len(y_axis_options)),
            sizing_mode='stretch_width',
            margin=(5, 5)
        )
        
        # Plot type selection based on context
        plot_type_options = self._get_plot_type_options(plot_context)
        self.plot_type_select = pn.widgets.RadioButtonGroup(
            name="Plot Type",
            options=plot_type_options,
            value=plot_context['suggested_plot_type'],
            button_type='primary',
            margin=(5, 5)
        )
        
        # Additional options
        self.show_units_checkbox = pn.widgets.Checkbox(
            name="Show units in axis labels",
            value=True,
            margin=(5, 5)
        )
        
        self.auto_scale_checkbox = pn.widgets.Checkbox(
            name="Auto-scale axes",
            value=True,
            margin=(5, 5)
        )
        
        # Action buttons
        generate_btn = pn.widgets.Button(
            name="Generate Plot",
            button_type="primary",
            width=120,
            margin=(10, 5)
        )
        generate_btn.on_click(self._on_modal_generate_plot)
        
        cancel_btn = pn.widgets.Button(
            name="Cancel", 
            button_type="light",
            width=80,
            margin=(10, 5)
        )
        cancel_btn.on_click(self._on_modal_cancel)
        
        # Layout modal content
        modal_content = pn.Column(
            header,
            pn.Divider(),
            pn.pane.HTML("<h5>Axis Configuration</h5>"),
            self.x_axis_select,
            self.y_axis_multiselect,
            pn.Divider(), 
            pn.pane.HTML("<h5>Plot Settings</h5>"),
            self.plot_type_select,
            self.show_units_checkbox,
            self.auto_scale_checkbox,
            pn.Divider(),
            pn.Row(generate_btn, cancel_btn, margin=(10, 5)),
            sizing_mode='stretch_width',
            margin=(10, 10)
        )
        
        return modal_content
    
    def _analyze_plot_context(self, selected_columns):
        """Analyze selected columns to determine optimal plot context and suggestions."""
        
        # Categorize columns by section
        sections = {}
        for col in selected_columns:
            section = col['section']
            if section not in sections:
                sections[section] = []
            sections[section].append(col)
        
        # Determine primary context
        if len(sections) == 1:
            # Single section - specialized context
            section_name = list(sections.keys())[0]
            if section_name == "trends":
                context = {
                    'type': 'time_series',
                    'description': 'Time-series trend analysis',
                    'suggested_x_axis': 'start_time_s',
                    'suggested_plot_type': 'Line Plot'
                }
            elif section_name == "quality":
                context = {
                    'type': 'distribution',
                    'description': 'Quality distribution analysis', 
                    'suggested_x_axis': selected_columns[0]['name'],
                    'suggested_plot_type': 'Histogram'
                }
            else:  # insights
                context = {
                    'type': 'categorical',
                    'description': 'Categorical insight analysis',
                    'suggested_x_axis': selected_columns[0]['name'], 
                    'suggested_plot_type': 'Bar Chart'
                }
        else:
            # Multi-section - correlation context
            context = {
                'type': 'correlation',
                'description': f'Multi-section correlation analysis ({", ".join(sections.keys())})',
                'suggested_x_axis': 'start_time_s',
                'suggested_plot_type': 'Scatter Plot'
            }
        
        return context
    
    def _get_x_axis_options(self, plot_context):
        """Get X-axis options based on plot context."""
        base_options = [
            ("Time (s)", "start_time_s"),
            ("Segment Duration (s)", "duration_s"), 
            ("Start Potential (V)", "start_potential_v"),
            ("End Potential (V)", "end_potential_v")
        ]
        
        # Add context-specific options
        if plot_context['type'] == 'time_series':
            return [("Time (s)", "start_time_s")] + base_options[1:]
        else:
            return base_options
    
    def _get_plot_type_options(self, plot_context):
        """Get plot type options based on context."""
        if plot_context['type'] == 'time_series':
            return ["Line Plot", "Scatter Plot", "Area Plot"]
        elif plot_context['type'] == 'distribution':
            return ["Histogram", "Box Plot", "Violin Plot"]
        elif plot_context['type'] == 'categorical':
            return ["Bar Chart", "Count Plot", "Pie Chart"]
        else:  # correlation
            return ["Scatter Plot", "Line Plot", "Heatmap"]
    
    def _on_modal_generate_plot(self, event):
        """Handle generate plot button click from modal."""
        try:
            # Get configuration from modal
            plot_config = {
                'x_axis': self.x_axis_select.value,
                'y_axes': self.y_axis_multiselect.value,
                'plot_type': self.plot_type_select.value,
                'show_units': self.show_units_checkbox.value,
                'auto_scale': self.auto_scale_checkbox.value
            }
            
            # Close modal
            self.plot_config_modal.hide()
            
            # Generate plot with configuration (Phase 4)
            self._create_configured_plot(plot_config)
            
        except Exception as e:
            logger.error(f"Failed to generate plot from modal: {e}")
            self._update_status(f"Plot generation error: {str(e)}", "error")
    
    def _on_modal_cancel(self, event):
        """Handle cancel button click from modal."""
        self.plot_config_modal.hide()
        self._update_status("Plot configuration cancelled", "info")
    
    def _create_configured_plot(self, plot_config):
        """Create plot with user configuration (Phase 4 implementation)."""
        # TODO: Full implementation in Phase 4
        # For now, show configuration summary
        config_summary = f"""
        <div style='padding:20px; background:#e3f2fd; border-radius:8px; margin:10px;'>
            <h4>🎯 Plot Configuration Applied</h4>
            <p><strong>X-Axis:</strong> {plot_config['x_axis']}</p>
            <p><strong>Y-Axes:</strong> {', '.join(plot_config['y_axes'])}</p>
            <p><strong>Plot Type:</strong> {plot_config['plot_type']}</p>
            <p><strong>Units Display:</strong> {'Enabled' if plot_config['show_units'] else 'Disabled'}</p>
            <p><strong>Auto-Scale:</strong> {'Enabled' if plot_config['auto_scale'] else 'Disabled'}</p>
            <p><em>🚧 Full plot generation will be implemented in Phase 4</em></p>
        </div>
        """
        self.plot_pane.object = config_summary
        self._update_status("Plot configuration complete - ready for Phase 4 implementation", "success")
    
    def _load_dataset(self):
        """Load comprehensive dataset for selected cells."""
        try:
            self._update_status("Loading dataset...", "loading")
            
            # Use existing API method to get comprehensive dataset
            dataset = self.api.get_research_dataset_for_perspective(
                cells=self.selected_cells
            )
            
            if isinstance(dataset, pl.DataFrame):
                self.current_dataset = dataset.to_pandas()
            else:
                self.current_dataset = dataset
            
            self.dataset_loaded = True
            
            logger.info(f"Loaded dataset: {len(self.current_dataset)} rows × {len(self.current_dataset.columns)} columns")
            
            # Discover available columns from registry
            self._discover_registry_columns()
            
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            raise
    
    def _discover_registry_columns(self):
        """Discover available columns from registry static declarations and current dataset."""
        try:
            # Get all registered analysis configurations with static declarations
            registry_analyses = {}
            
            # Get analysis options from registry
            analysis_options = self.registry.get_analysis_options()
            
            if not analysis_options:
                logger.warning("No analysis options found in registry")
                self.available_columns = {}
                return
            
            for analysis_name, analysis_id in analysis_options:
                try:
                    config = self.registry.get_analysis(analysis_id)
                    if config and hasattr(config, 'output_columns') and config.output_columns:
                        # Use static declarations instead of running analysis
                        static_columns = self.registry.get_all_output_columns(analysis_id)
                        categorized_columns = self.registry.get_columns_by_category(analysis_id)
                        
                        if static_columns:
                            registry_analyses[analysis_id] = {
                                'name': analysis_name,
                                'columns': static_columns,
                                'categorized': categorized_columns or {}
                            }
                            logger.debug(f"Added analysis {analysis_id} with {len(static_columns)} columns")
                        else:
                            logger.debug(f"No static columns found for {analysis_id}")
                    else:
                        logger.debug(f"No output columns config for {analysis_id}")
                except Exception as e:
                    logger.warning(f"Error processing analysis {analysis_id}: {e}")
                    continue
            
            self.registry_columns = registry_analyses
            
            # For registry-driven UI, we use static declarations without dataset validation
            # Dataset validation will happen during actual plot generation
            self.available_columns = {}
            
            for analysis_id, info in registry_analyses.items():
                # Use all static columns from registry for UI population
                self.available_columns[analysis_id] = {
                    'name': info['name'],
                    'columns': info['columns'],
                    'categorized': info['categorized']
                }
                
            # If dataset is available, we could filter columns, but for UI setup we show all
            if self.current_dataset is not None:
                dataset_columns = list(self.current_dataset.columns)
                
                # Filter to only show columns that exist in dataset
                filtered_columns = {}
                for analysis_id, info in self.available_columns.items():
                    matching_columns = [col for col in info['columns'] if col in dataset_columns]
                    if matching_columns:
                        # Safely handle categorized columns
                        categorized_filtered = {}
                        if info.get('categorized'):
                            for category, cols in info['categorized'].items():
                                if cols:  # Only process non-empty column lists
                                    filtered_cols = [col for col in cols if col in dataset_columns]
                                    if filtered_cols:  # Only add if we have matching columns
                                        categorized_filtered[category] = filtered_cols
                        
                        filtered_columns[analysis_id] = {
                            'name': info['name'],
                            'columns': matching_columns,
                            'categorized': categorized_filtered
                        }
                self.available_columns = filtered_columns
            
            logger.info(f"Discovered {len(self.available_columns)} analysis types with columns")
            logger.debug(f"Available analyses: {list(self.available_columns.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to discover registry columns: {e}")
            self.available_columns = {}
    
    def _auto_configure_interface(self):
        """Auto-configure interface based on cell and technique selections."""
        try:
            if not self.dataset_loaded:
                return
            
            # Filter dataset by technique if not "All"
            filtered_df = self.current_dataset.copy()
            if self.current_technique != "All":
                if 'technique_name' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['technique_name'].str.contains(
                        self.current_technique, case=False, na=False
                    )]
            
            # Create auto-configured controls
            controls = []
            
            # Y-Metrics multi-select
            y_metrics_options = self._get_y_metrics_options(filtered_df)
            if y_metrics_options:
                self.y_metrics_select = pn.widgets.MultiChoice(
                    name="Y-Axis Metrics",
                    options=y_metrics_options,
                    value=y_metrics_options[:3],  # Default to first 3
                    sizing_mode='stretch_width',
                    margin=(5, 5)
                )
                controls.append(self.y_metrics_select)
            
            # X-Axis variable select
            x_axis_options = self._get_x_axis_options(filtered_df)
            if x_axis_options:
                self.x_axis_select = pn.widgets.Select(
                    name="X-Axis Variable",
                    options=x_axis_options,
                    value=x_axis_options[0] if x_axis_options else None,
                    sizing_mode='stretch_width',
                    margin=(5, 5)
                )
                controls.append(self.x_axis_select)
            
            # Plot type toggle
            self.plot_type_select = pn.widgets.RadioButtonGroup(
                name="Plot Type",
                options=["Line/Scatter", "Distribution"],
                value="Line/Scatter",
                button_type="primary",
                sizing_mode='stretch_width',
                margin=(5, 5)
            )
            controls.append(self.plot_type_select)
            
            # Grouping options
            grouping_options = self._get_grouping_options(filtered_df)
            if grouping_options:
                self.grouping_select = pn.widgets.Select(
                    name="Group/Color By",
                    options=grouping_options,
                    value=grouping_options[0] if grouping_options else None,
                    sizing_mode='stretch_width',
                    margin=(5, 5)
                )
                controls.append(self.grouping_select)
            
            # Update plot button
            self.update_plot_btn = pn.widgets.Button(
                name="🎯 Update Plot",
                button_type="success",
                sizing_mode='stretch_width',
                margin=(5, 5)
            )
            self.update_plot_btn.on_click(self._on_update_plot)
            controls.append(self.update_plot_btn)
            
            # Update auto controls
            self.auto_controls_column.clear()
            self.auto_controls_column.extend(controls)
            
            # Update data feedback
            self._update_data_feedback(filtered_df)
            
            # Generate initial plot
            self._generate_plot(filtered_df)
            
        except Exception as e:
            logger.error(f"Failed to auto-configure interface: {e}")
            raise
    
    def _get_y_metrics_options(self, df):
        """Get available Y-axis metrics from dataset with registry technique filtering."""
        options = []
        
        # Use registry technique filtering
        if self.current_technique != "All":
            # Get applicable analyses for this technique using registry
            applicable_analyses = self.registry.get_analyses_for_technique(self.current_technique)
            applicable_analysis_ids = {config.analysis_id for config in applicable_analyses}
        else:
            # Use all available analyses
            applicable_analysis_ids = set(self.available_columns.keys())
        
        # Add metrics from applicable analyses (prioritize metrics category)
        for analysis_id in applicable_analysis_ids:
            if analysis_id in self.available_columns:
                info = self.available_columns[analysis_id]
                
                # Get metrics columns first (primary for X/Y plotting)
                metrics_cols = info['categorized'].get('metrics', [])
                for col in metrics_cols:
                    if col in df.columns:
                        display_name = col.replace(f"{analysis_id}_", "").replace("_", " ").title()
                        options.append((col, f"{info['name']} Metrics: {display_name}"))
                
                # Add quality columns (good for distribution plots)  
                quality_cols = info['categorized'].get('quality', [])
                for col in quality_cols:
                    if col in df.columns:
                        display_name = col.replace(f"{analysis_id}_", "").replace("_", " ").title()
                        options.append((col, f"{info['name']} Quality: {display_name}"))
                
                # Add insight columns (categorical/bar plots)
                insight_cols = info['categorized'].get('insights', [])
                for col in insight_cols:
                    if col in df.columns:
                        display_name = col.replace(f"{analysis_id}_", "").replace("_", " ").title()
                        options.append((col, f"{info['name']} Insights: {display_name}"))
        
        # Add base numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        base_cols = ['duration_s', 'capacity_ah', 'energy_wh', 'start_potential_v', 'end_potential_v',
                     'exp_charge_cap_ah', 'exp_discharge_cap_ah', 'exp_time_cumulative_s']
        
        for col in base_cols:
            if col in numeric_cols and col not in [opt[0] for opt in options]:
                display_name = col.replace("_", " ").title()
                options.append((col, f"Base: {display_name}"))
        
        # Sort by display name and return just column names
        if options:
            options.sort(key=lambda x: x[1])
            return [opt[0] for opt in options]
        
        return []
    
    def _get_x_axis_options(self, df):
        """Get appropriate X-axis options based on data."""
        options = []
        
        # Time variables
        time_vars = ['time_s', 'start_timestamp', 'exp_time_cumulative_s']
        for var in time_vars:
            if var in df.columns:
                options.append(var)
        
        # Capacity variables  
        capacity_vars = ['exp_charge_cap_ah', 'exp_discharge_cap_ah', 'capacity_ah']
        for var in capacity_vars:
            if var in df.columns:
                options.append(var)
        
        # Voltage variables
        voltage_vars = ['start_potential_v', 'end_potential_v']
        for var in voltage_vars:
            if var in df.columns:
                options.append(var)
        
        return options
    
    def _get_grouping_options(self, df):
        """Get available grouping options."""
        options = ['None']
        
        # Cell name grouping if multiple cells
        if len(self.selected_cells) > 1 and 'cell_name' in df.columns:
            options.append('cell_name')
        
        # Temperature grouping if variation exists
        if 'temperature_c' in df.columns and df['temperature_c'].nunique() > 1:
            options.append('temperature_c')
        
        # Technique grouping
        if 'technique_name' in df.columns and df['technique_name'].nunique() > 1:
            options.append('technique_name')
        
        return options
    
    def _update_data_feedback(self, df):
        """Update data feedback display."""
        try:
            feedback_data = []
            
            # Debug: Check available columns for cell identification
            cell_columns = [col for col in df.columns if 'cell' in col.lower()]
            logger.debug(f"Available cell columns: {cell_columns}")
            
            # Determine cell identification column
            cell_id_col = None
            if 'cell_name' in df.columns:
                cell_id_col = 'cell_name'
            elif 'cell_id' in df.columns:
                cell_id_col = 'cell_id' 
            elif cell_columns:
                cell_id_col = cell_columns[0]
                
            for cell_name in self.selected_cells:
                if cell_id_col:
                    # Filter by actual cell identification
                    if cell_id_col in df.columns:
                        cell_df = df[df[cell_id_col].astype(str).str.contains(cell_name, case=False, na=False)]
                    else:
                        cell_df = df  # Use full dataset if no cell column
                else:
                    # If no cell identification possible, use full dataset 
                    cell_df = df
                
                segments_count = len(cell_df)
                
                # Enhanced quality assessment
                if segments_count > 0:
                    # Check for analysis results or successful segments
                    if 'analysis_status' in cell_df.columns:
                        success_count = len(cell_df[cell_df['analysis_status'] == 'completed'])
                        if success_count > segments_count * 0.8:
                            quality = "High"
                        elif success_count > segments_count * 0.5:
                            quality = "Medium"
                        else:
                            quality = "Low"
                    else:
                        quality = "Available"
                    
                    status = f"✅ {segments_count} segments"
                else:
                    quality = "No Data"
                    status = "❌ No segments"
                
                feedback_data.append({
                    'Cell': cell_name,
                    'Segments': segments_count,
                    'Quality': quality,
                    'Status': status
                })
            
            # Create DataFrame and ensure no NaN values
            feedback_df = pd.DataFrame(feedback_data)
            
            # Fill any remaining NaN values
            feedback_df = feedback_df.fillna({
                'Cell': 'Unknown',
                'Segments': 0,
                'Quality': 'Unknown', 
                'Status': 'No data'
            })
            
            self.data_feedback_tabulator.value = feedback_df
            logger.debug(f"Data feedback updated: {len(feedback_data)} cells")
            
        except Exception as e:
            logger.error(f"Failed to update data feedback: {e}")
            # Create empty feedback on error
            empty_feedback = pd.DataFrame({
                'Cell': ['Error'],
                'Segments': [0],
                'Quality': ['Error'],
                'Status': ['Failed to load data']
            })
            self.data_feedback_tabulator.value = empty_feedback
    
    def _generate_plot(self, df):
        """Generate interactive plot with hvplot and intelligent decimation."""
        try:
            if df.empty:
                self.plot_pane.object = """<div style='padding:40px; text-align:center; background:#fff3e0; border-radius:8px; margin:10px; border-left:3px solid #f57c00;'>
                   <h3>⚠️ No Data Available</h3>
                   <p>No data matches current filters</p>
                   </div>"""
                return
            
            # Get current selections
            y_metrics = getattr(self, 'y_metrics_select', None)
            x_axis = getattr(self, 'x_axis_select', None)
            plot_type = getattr(self, 'plot_type_select', None)
            grouping = getattr(self, 'grouping_select', None)
            
            if not y_metrics or not y_metrics.value:
                self.plot_pane.object = """<div style='padding:40px; text-align:center; background:#f8f9fa; border-radius:8px; margin:10px;'>
                   <h3>📊 Select Metrics</h3>
                   <p>Choose Y-axis metrics to generate plot</p>
                   </div>"""
                return
            
            # Generate plot based on selections
            x_col = x_axis.value if x_axis else df.columns[0] 
            y_cols = y_metrics.value if isinstance(y_metrics.value, list) else [y_metrics.value]
            group_col = grouping.value if grouping and grouping.value != 'None' else None
            
            # Select required columns and handle missing data
            required_cols = [x_col] + y_cols + ([group_col] if group_col else [])
            available_cols = [col for col in required_cols if col in df.columns]
            
            if not available_cols:
                self.plot_pane.object = """<div style='padding:40px; text-align:center; background:#fff3e0; border-radius:8px; margin:10px; border-left:3px solid #f57c00;'>
                   <h3>⚠️ Missing Columns</h3>
                   <p>Selected columns not available in dataset</p>
                   </div>"""
                return
            
            plot_df = df[available_cols].copy().dropna()
            
            # Intelligent decimation for large datasets (>10k points)
            if len(plot_df) > 10000:
                sample_size = min(10000, len(plot_df))
                plot_df = plot_df.sample(n=sample_size, random_state=42)
                decimation_note = f" (showing {sample_size:,} of {len(df):,} points)"
            else:
                decimation_note = f" ({len(plot_df):,} points)"
            
            if plot_type and plot_type.value == "Distribution":
                # Distribution plot for first y-metric
                y_col = y_cols[0]
                if y_col not in plot_df.columns:
                    y_col = y_cols[0] if y_cols else plot_df.select_dtypes(include=['number']).columns[0]
                
                plot = plot_df.hvplot.hist(
                    y=y_col, 
                    by=group_col,
                    bins=30,
                    width=700,
                    height=450,
                    title=f"Distribution: {y_col.replace('_', ' ').title()}{decimation_note}",
                    xlabel=y_col.replace('_', ' ').title(),
                    ylabel="Count",
                    alpha=0.7
                )
            else:
                # Line/Scatter plot - handle multiple y-metrics
                if len(y_cols) == 1:
                    y_col = y_cols[0]
                    if y_col not in plot_df.columns:
                        y_col = plot_df.select_dtypes(include=['number']).columns[0]
                    
                    plot = plot_df.hvplot.scatter(
                        x=x_col,
                        y=y_col,
                        by=group_col,
                        width=700,
                        height=450,
                        title=f"Explorer: {y_col.replace('_', ' ').title()} vs {x_col.replace('_', ' ').title()}{decimation_note}",
                        xlabel=x_col.replace('_', ' ').title(),
                        ylabel=y_col.replace('_', ' ').title(),
                        alpha=0.7,
                        size=60
                    )
                else:
                    # Multiple y-metrics: create simple combined plot
                    # Use first valid y-column for now to avoid Overlay complications
                    valid_y_cols = [col for col in y_cols if col in plot_df.columns]
                    
                    if valid_y_cols:
                        # For now, plot first metric and show others in title
                        y_col = valid_y_cols[0]
                        
                        plot = plot_df.hvplot.scatter(
                            x=x_col,
                            y=y_col,
                            by=group_col,
                            width=700,
                            height=450,
                            title=f"Multi-Metric: {y_col.replace('_', ' ').title()} (+ {len(valid_y_cols)-1} others){decimation_note}",
                            xlabel=x_col.replace('_', ' ').title(),
                            ylabel=f"{y_col.replace('_', ' ').title()} (Primary)",
                            alpha=0.7,
                            size=60
                        )
                        
                        # TODO: Implement proper multi-metric overlay in future enhancement
                        logger.info(f"Multi-metric plot showing primary metric: {y_col}, others available: {valid_y_cols[1:]}")
                        
                    else:
                        raise ValueError("No valid y-columns available")
            
            # Update plot pane - ensure clean object assignment
            try:
                self.plot_pane.object = plot
                logger.debug(f"Plot successfully assigned to pane: {type(plot)}")
            except Exception as plot_assignment_error:
                logger.error(f"Failed to assign plot to pane: {plot_assignment_error}")
                self.plot_pane.object = f"""<div style='padding:40px; text-align:center; background:#ffebee; border-radius:8px; margin:10px; border-left:3px solid #d32f2f;'>
                   <h3>❌ Plot Assignment Error</h3>
                   <p>Failed to display plot: {str(plot_assignment_error)}</p>
                   </div>"""
            
        except Exception as e:
            logger.error(f"Failed to generate plot: {e}")
            self.plot_pane.object = f"""<div style='padding:40px; text-align:center; background:#ffebee; border-radius:8px; margin:10px; border-left:3px solid #d32f2f;'>
               <h3>❌ Plot Error</h3>
               <p>Failed to generate plot: {str(e)}</p>
               <p><small>Debug: x={getattr(x_axis, 'value', 'N/A') if 'x_axis' in locals() else 'N/A'}, y={getattr(y_metrics, 'value', 'N/A') if 'y_metrics' in locals() else 'N/A'}</small></p>
               </div>"""
    
    def _on_update_plot(self, event):
        """Handle update plot button click."""
        try:
            if not self.dataset_loaded:
                self._update_status("No dataset loaded", "warning")
                return
            
            # Filter dataset by technique
            filtered_df = self.current_dataset.copy()
            if self.current_technique != "All":
                if 'technique_name' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['technique_name'].str.contains(
                        self.current_technique, case=False, na=False
                    )]
            
            # Update data feedback and plot
            self._update_data_feedback(filtered_df)
            self._generate_plot(filtered_df)
            
            self._update_status("Plot updated", "success")
            
        except Exception as e:
            logger.error(f"Failed to update plot: {e}")
            self._update_status(f"Plot update failed: {str(e)}", "error")
    
    def _update_status(self, message: str, status_type: str = "info"):
        """Update status indicator with message and type."""
        self.status_message = message
        logger.info(f"Explorer status: {message} ({status_type})")


class ElectrochemicalExplorerTabWrapper(param.Parameterized):
    """Wrapper for Explorer Tab to match existing component patterns."""
    
    def __init__(self, api, **params):
        super().__init__(**params)
        self.tab = ElectrochemicalExplorerTab(api)
        self.panel = self.tab.panel
        
    def __panel__(self):
        return self.panel