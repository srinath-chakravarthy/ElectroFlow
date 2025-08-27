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
        
        # === VISUALIZATION PANEL ===
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
        """Create configuration panel components."""
        
        # Technique selection
        self.technique_select = pn.widgets.Select(
            name="Technique",
            options=["All", "REST", "Galvanostatic", "Potentiostatic", "EIS", "CV"],
            value="All",
            sizing_mode='stretch_width',
            margin=(5, 5)
        )
        
        # Plot trigger button
        self.configure_btn = pn.widgets.Button(
            name="🔧 Configure Explorer",
            button_type="primary",
            disabled=True,
            sizing_mode='stretch_width',
            margin=(5, 5)
        )
        
        # Auto-generated controls placeholder
        self.auto_controls_column = pn.Column(
            pn.pane.HTML("<p><i>Select cells and technique, then click Configure Explorer</i></p>"),
            sizing_mode='stretch_width'
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
        """Setup 3-panel layout for explorer."""
        
        # Panel 1: Cell Selection
        cell_panel = pn.Card(
            pn.Column(
                pn.pane.HTML("<h4>🔋 Cell Selection</h4>"),
                self.cell_tabulator,
                self.refresh_cells_btn,
                self.cell_status_html
            ),
            title="Data Selection",
            sizing_mode='stretch_width',
            margin=(5, 5)
        )
        
        # Panel 2: Configuration  
        config_panel = pn.Card(
            pn.Column(
                pn.pane.HTML("<h4>⚙️ Configuration</h4>"),
                self.technique_select,
                self.configure_btn,
                self.auto_controls_column
            ),
            title="Explorer Configuration",
            sizing_mode='stretch_width',
            margin=(5, 5)
        )
        
        # Panel 3: Visualization
        viz_panel = pn.Card(
            pn.Column(
                pn.pane.HTML("<h4>📊 Data Feedback</h4>"),
                self.data_feedback_tabulator,
                pn.pane.HTML("<h4>🎯 Interactive Visualization</h4>"),
                self.plot_pane
            ),
            title="Visual Explorer",
            sizing_mode='stretch_both',
            margin=(5, 5)
        )
        
        # Main layout
        self.panel = pn.Row(
            pn.Column(cell_panel, config_panel, width=400),
            viz_panel,
            sizing_mode='stretch_both'
        )
    
    def _setup_callbacks(self):
        """Setup component callbacks."""
        
        # Cell selection callbacks
        self.cell_tabulator.param.watch(self._on_cell_selection_changed, 'selection')
        self.refresh_cells_btn.on_click(self._on_refresh_cells)
        
        # Configuration callbacks
        self.technique_select.param.watch(self._on_technique_changed, 'value')
        self.configure_btn.on_click(self._on_configure_explorer)
    
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
            
            # Update configure button state
            self.configure_btn.disabled = len(selected_cells) == 0
            
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
    
    def _on_technique_changed(self, event):
        """Handle technique selection change."""
        self.current_technique = event.new
        if self.selected_cells:
            self._update_status(f"Technique changed to {event.new}", "info")
    
    def _on_refresh_cells(self, event):
        """Handle refresh cells button click."""
        self._refresh_cells()
    
    def _on_configure_explorer(self, event):
        """Handle configure explorer button click."""
        try:
            if not self.selected_cells:
                self._update_status("No cells selected", "warning")
                return
                
            self._update_status("Configuring explorer interface...", "loading")
            
            # Load comprehensive dataset
            self._load_dataset()
            
            # Auto-configure interface based on selections
            self._auto_configure_interface()
            
            self._update_status("Explorer configured successfully", "success")
            
        except Exception as e:
            logger.error(f"Failed to configure explorer: {e}")
            self._update_status(f"Configuration failed: {str(e)}", "error")
    
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
        """Discover available columns from registry and current dataset."""
        try:
            # Get all registered analysis configurations
            registry_analyses = {}
            
            # Get analysis options from registry
            analysis_options = self.registry.get_analysis_options()
            
            for analysis_id, analysis_name in analysis_options:
                config = self.registry.get_analysis(analysis_id)
                if config:
                    # Get available columns for this analysis
                    available_cols = self.registry.get_available_columns(analysis_id)
                    if available_cols:
                        registry_analyses[analysis_id] = {
                            'name': analysis_name,
                            'columns': available_cols
                        }
            
            self.registry_columns = registry_analyses
            
            # Find columns in dataset that match registry pattern
            dataset_columns = list(self.current_dataset.columns)
            self.available_columns = {}
            
            for analysis_id, info in registry_analyses.items():
                matching_columns = []
                for col in dataset_columns:
                    if col.startswith(f"{analysis_id}_"):
                        matching_columns.append(col)
                
                if matching_columns:
                    self.available_columns[analysis_id] = {
                        'name': info['name'],
                        'columns': matching_columns
                    }
            
            logger.info(f"Discovered {len(self.available_columns)} analysis types with columns")
            
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
        """Get available Y-axis metrics from dataset with technique filtering."""
        options = []
        
        # Add registry-based columns (filtered by technique if applicable)
        for analysis_id, info in self.available_columns.items():
            # Filter by technique relevance
            if self.current_technique != "All":
                # Simple technique-analysis mapping
                technique_analysis_map = {
                    "REST": ["kinetics", "equilibrium"],
                    "Galvanostatic": ["resistance", "basic_statistics"], 
                    "Potentiostatic": ["current_decay", "kinetics"],
                    "EIS": ["resistance", "impedance"],
                    "CV": ["basic_statistics"]
                }
                
                relevant_analyses = technique_analysis_map.get(self.current_technique, [])
                if not any(analysis in analysis_id.lower() for analysis in relevant_analyses):
                    continue
            
            for col in info['columns']:
                if col in df.columns:
                    # Create display name
                    display_name = col.replace(f"{analysis_id}_", "").replace("_", " ").title()
                    options.append((col, f"{info['name']}: {display_name}"))
        
        # Add base numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        base_cols = ['duration_s', 'capacity_ah', 'energy_wh', 'start_potential_v', 'end_potential_v',
                     'exp_charge_cap_ah', 'exp_discharge_cap_ah', 'exp_time_cumulative_s']
        
        for col in base_cols:
            if col in numeric_cols and col not in [opt[0] if isinstance(opt, tuple) else opt for opt in options]:
                display_name = col.replace("_", " ").title()
                options.append((col, f"Base: {display_name}"))
        
        # Sort by display name and return just column names
        if options and isinstance(options[0], tuple):
            options.sort(key=lambda x: x[1])
            return [opt[0] for opt in options]
        
        return sorted(options)
    
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
            
            # Update plot pane
            self.plot_pane.object = plot
            
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