"""
Clean Electrochemical Data Explorer - Complete Rewrite

Simplified architecture with Panel-native components, centralized state management,
and proper UI placement. Eliminates technical debt from previous iterations.
"""

import panel as pn
import param
import pandas as pd
import polars as pl
import hvplot.pandas
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

pn.extension('tabulator', 'modal')


class CleanElectrochemicalExplorer(param.Parameterized):
    """
    Clean electrochemical data explorer with simplified architecture.

    Key improvements:
    - Single registry call per analysis change
    - Panel-native components throughout
    - Manual plot updates only
    - Clean multi-plot state management
    - No HTML generation or custom styling
    """

    def __init__(self, api, **params):
        super().__init__(**params)
        self.api = api

        # Initialize registry
        from src_clean.analysis.registry import get_analysis_registry
        self.registry = get_analysis_registry()

        # Core state - simplified
        self.selected_cells = []
        self.dataset = None
        self.plot_configs = [self._create_empty_plot_config()]  # List of plot configurations
        self.active_plot_index = 0

        # Create UI components
        self._create_components()
        self._setup_layout()
        self._setup_callbacks()

        # Initialize
        self._refresh_cells()

    def _create_empty_plot_config(self):
        """Create empty plot configuration dictionary."""
        return {
            'analysis_type': '',
            'analysis_name': '',
            'x_axis': 'start_time_s',
            'y_axes': [],
            'group_by': '',
            'plot_type': 'scatter',
            'x_range': (None, None),
            'y_range': (None, None),
            'plot_object': None
        }

    @property
    def current_config(self):
        """Get current plot configuration."""
        return self.plot_configs[self.active_plot_index]

    def _create_components(self):
        """Create all UI components using Panel-native elements."""

        # === CELL SELECTION ===
        self._create_cell_selection()

        # === MAIN CONTROLS ===
        self._create_main_controls()

        # === PLOT CONFIGURATION ===
        self._create_plot_configuration()

        # === PLOT AREA ===
        self._create_plot_area()

        # === STATUS ===
        self.status_alert = pn.pane.Alert("Ready to analyze electrochemical data", alert_type="info")

    def _create_cell_selection(self):
        """Create cell selection modal - Panel native."""

        # Cell table
        self.cell_table = pn.widgets.Tabulator(
            value=pd.DataFrame(),
            pagination='local',
            page_size=15,
            selectable='checkbox',
            sizing_mode='stretch_width',
            height=300
        )

        # Modal buttons - store references for callbacks
        self.modal_apply_btn = pn.widgets.Button(
            name="Apply Selection", 
            button_type="primary", 
            width=120
        )
        self.modal_cancel_btn = pn.widgets.Button(
            name="Cancel", 
            button_type="light", 
            width=80
        )

        # Modal for cell selection with proper button references
        self.cell_modal = pn.layout.Modal(
            pn.Column(
                pn.pane.Markdown("## 🔋 Select Cells for Analysis"),
                self.cell_table,
                pn.Row(
                    pn.Spacer(),
                    self.modal_apply_btn,
                    self.modal_cancel_btn
                ),
                width=600,
                height=500
            )
        )

        # Trigger button
        self.select_cells_btn = pn.widgets.Button(
            name="Select Cells",
            button_type="primary",  # Valid Panel button types: default, primary, success, warning, danger, light
            width=120
        )

    def _create_main_controls(self):
        """Create main control bar - clean and centered."""

        # Analysis selector
        self.analysis_select = pn.widgets.Select(
            name="Analysis Type",
            options=[("Select cells first", "")],
            width=200
        )

        # Temperature filter
        self.temperature_select = pn.widgets.Select(
            name="Temperature",
            options=[("All", "all"), ("25°C", "25"), ("45°C", "45"), ("60°C", "60")],
            value="all",
            width=120
        )

        # Cell status display
        self.cell_status = pn.pane.Alert("No cells selected", alert_type="warning", width=300)

    def _create_plot_configuration(self):
        """Create plot configuration panel - Panel native cards."""

        # Multi-plot management
        self.plot_tabs = pn.Tabs(
            ("Plot 1", pn.pane.HTML("")),  # Will be populated dynamically
            dynamic=True,
            width=300
        )

        self.add_plot_btn = pn.widgets.Button(name="Add Plot", button_type="primary", width=80)
        self.remove_plot_btn = pn.widgets.Button(name="Remove", button_type="light", width=80, disabled=True)

        # Axis configuration
        self.x_axis_select = pn.widgets.Select(
            name="X-Axis",
            options=[("Time (s)", "start_time_s")],
            width=280
        )

        self.y_axis_multiselect = pn.widgets.MultiSelect(
            name="Y-Axes",
            options=[],
            width=280,
            height=120
        )

        self.group_select = pn.widgets.Select(
            name="Group By",
            options=[("None", ""), ("Cell", "cell_name")],
            width=280
        )

        # Plot type
        self.plot_type_radio = pn.widgets.RadioButtonGroup(
            name="Plot Type",
            options=["scatter", "line", "histogram"],
            value="scatter",
            width=280
        )

        # Range controls - hybrid approach
        self.x_min_input = pn.widgets.FloatInput(name="X Min", width=90)
        self.x_max_input = pn.widgets.FloatInput(name="X Max", width=90)
        self.x_range_slider = pn.widgets.RangeSlider(name="X Range", width=200)

        self.y_min_input = pn.widgets.FloatInput(name="Y Min", width=90)
        self.y_max_input = pn.widgets.FloatInput(name="Y Max", width=90)
        self.y_range_slider = pn.widgets.RangeSlider(name="Y Range", width=200)

        # CENTRAL GENERATE BUTTON
        self.generate_btn = pn.widgets.Button(
            name="Generate Plot",
            button_type="primary",
            width=200,
            height=50,
            styles={'font-size': '16px', 'font-weight': 'bold'}
        )

    def _create_plot_area(self):
        """Create multi-plot display area using GridSpec."""

        self.plot_grid = pn.GridSpec(sizing_mode='stretch_both', min_height=500)

        # Initialize with placeholder
        self.plot_grid[0, 0] = pn.pane.Alert(
            "Configure analysis and generate plots to see results",
            alert_type="info",
            sizing_mode='stretch_both'
        )

    def _setup_layout(self):
        """Setup clean layout with proper spacing and no overlaps."""

        # Header bar - clean and properly spaced
        header_bar = pn.Row(
            self.select_cells_btn,
            pn.Spacer(width=15),  # Fixed: Use Spacer with width for horizontal spacing in Row
            self.analysis_select,
            pn.Spacer(width=10),
            self.temperature_select,
            pn.Spacer(),  # Flexible spacer to push cell status to right
            self.cell_status,
            margin=(10, 20),
            sizing_mode='stretch_width'
        )

        # Configuration panel - clean card layout
        config_panel = pn.Card(
            pn.Column(
                # Plot management
                pn.Row(self.plot_tabs, pn.Spacer(), margin=(5, 0)),
                pn.Row(self.add_plot_btn, self.remove_plot_btn, pn.Spacer(), margin=(5, 0)),

                pn.layout.Divider(),

                # Axis configuration
                self.x_axis_select,
                self.y_axis_multiselect,
                self.group_select,

                pn.layout.Divider(),

                # Plot type
                self.plot_type_radio,

                pn.layout.Divider(),

                # Range controls - properly aligned
                pn.pane.Markdown("**X-Axis Range**"),
                pn.Row(self.x_min_input, self.x_range_slider, self.x_max_input, margin=(5, 0)),

                pn.pane.Markdown("**Y-Axis Range**"),
                pn.Row(self.y_min_input, self.y_range_slider, self.y_max_input, margin=(5, 0)),

                pn.layout.Divider(),

                # PROMINENT GENERATE BUTTON - centered
                pn.Row(pn.Spacer(), self.generate_btn, pn.Spacer(), margin=(10, 0))
            ),
            title="Plot Configuration",
            width=320,
            margin=(10, 10)
        )

        # Main layout - no overlaps, proper spacing
        main_content = pn.Row(
            config_panel,
            self.plot_grid,
            sizing_mode='stretch_both'
        )

        # Complete layout
        self.panel = pn.Column(
            header_bar,
            main_content,
            self.status_alert,
            self.cell_modal,  # Modal overlay
            sizing_mode='stretch_both',
            min_height=600
        )

    def _setup_callbacks(self):
        """Setup callbacks - simplified and focused."""

        # Cell selection
        self.select_cells_btn.on_click(self._on_open_cell_modal)
        self.cell_table.param.watch(self._on_cell_selection_changed, 'selection')
        
        # Modal buttons
        self.modal_apply_btn.on_click(self._on_modal_apply)
        self.modal_cancel_btn.on_click(self._on_modal_cancel)

        # Analysis selection
        self.analysis_select.param.watch(self._on_analysis_changed, 'value')

        # Plot management
        self.plot_tabs.param.watch(self._on_plot_tab_changed, 'active')
        self.add_plot_btn.on_click(self._on_add_plot)
        self.remove_plot_btn.on_click(self._on_remove_plot)

        # Configuration changes - update state only, no auto-plotting
        self.x_axis_select.param.watch(self._on_x_axis_changed, 'value')
        self.y_axis_multiselect.param.watch(self._on_y_axes_changed, 'value')
        self.group_select.param.watch(self._on_group_changed, 'value')
        self.plot_type_radio.param.watch(self._on_plot_type_changed, 'value')

        # Range controls - synchronized but no auto-plotting
        self._setup_range_synchronization()

        # Generate button - single point of plot creation
        self.generate_btn.on_click(self._on_generate_plot)

    def _setup_range_synchronization(self):
        """Synchronize range inputs and sliders without auto-plotting."""

        # X-range synchronization
        def sync_x_slider(event):
            self.x_range_slider.value = (self.x_min_input.value or 0, self.x_max_input.value or 100)
            self.current_config['x_range'] = self.x_range_slider.value

        def sync_x_inputs(event):
            if event.new and len(event.new) == 2:
                self.x_min_input.value = event.new[0]
                self.x_max_input.value = event.new[1]
                self.current_config['x_range'] = event.new

        self.x_min_input.param.watch(sync_x_slider, 'value')
        self.x_max_input.param.watch(sync_x_slider, 'value')
        self.x_range_slider.param.watch(sync_x_inputs, 'value')

        # Y-range synchronization
        def sync_y_slider(event):
            self.y_range_slider.value = (self.y_min_input.value or 0, self.y_max_input.value or 100)
            self.current_config['y_range'] = self.y_range_slider.value

        def sync_y_inputs(event):
            if event.new and len(event.new) == 2:
                self.y_min_input.value = event.new[0]
                self.y_max_input.value = event.new[1]
                self.current_config['y_range'] = event.new

        self.y_min_input.param.watch(sync_y_slider, 'value')
        self.y_max_input.param.watch(sync_y_slider, 'value')
        self.y_range_slider.param.watch(sync_y_inputs, 'value')

    # === EVENT HANDLERS ===

    def _refresh_cells(self):
        """Load available cells."""
        try:
            cells = self.api.get_available_research_cells()
            if cells:
                # Get summary data
                cell_data = []
                for cell_name in cells:
                    summary = self.api.get_research_data_summary([cell_name])
                    cell_data.append({
                        'Cell': cell_name,
                        'Segments': summary.get('total_segments', 0),
                        'Techniques': ', '.join(summary.get('techniques', [])[:2])
                    })

                self.cell_table.value = pd.DataFrame(cell_data)
                self._update_status(f"Found {len(cells)} cells", "success")
            else:
                self._update_status("No cells available", "warning")

        except Exception as e:
            self._update_status(f"Failed to load cells: {e}", "danger")

    def _on_open_cell_modal(self, event):
        """Open cell selection modal and restore previous selections."""
        try:
            # Restore previous selections if any (clean code approach)
            if self.selected_cells and not self.cell_table.value.empty:
                # Find indices of previously selected cells
                restore_indices = []
                for i, row in self.cell_table.value.iterrows():
                    if row['Cell'] in self.selected_cells:
                        restore_indices.append(i)
                
                # Restore selection in table
                if restore_indices:
                    self.cell_table.selection = restore_indices
            
            # Open modal
            self.cell_modal.open = True
            
        except Exception as e:
            logger.error(f"Failed to open cell modal: {e}")
            # Fallback - just open modal without restoring selections
            self.cell_modal.open = True

    def _on_cell_selection_changed(self, event):
        """Handle cell selection change in table (for Modal workflow, changes applied on Modal Apply)."""
        # This method is now passive - selection is tracked by Tabulator
        # Actual application of selection happens in _on_modal_apply
        pass

    def _on_modal_apply(self, event):
        """Apply cell selection from modal and close modal."""
        try:
            # Get currently selected cells from table
            selected_indices = self.cell_table.selection
            selected_cells = []
            
            if selected_indices and not self.cell_table.value.empty:
                for idx in selected_indices:
                    if idx < len(self.cell_table.value):
                        cell_name = self.cell_table.value.iloc[idx]['Cell']
                        selected_cells.append(cell_name)
            
            # Update main UI state
            self.selected_cells = selected_cells
            
            # Update UI feedback
            if selected_cells:
                self._load_analysis_options()
                self.cell_status.object = f"Selected {len(selected_cells)} cells: {', '.join(selected_cells)}"
                self.cell_status.alert_type = "success"
                self._update_status(f"Applied selection: {len(selected_cells)} cells", "success")
            else:
                self.cell_status.object = "No cells selected"
                self.cell_status.alert_type = "warning"
                self._update_status("No cells selected", "warning")
            
            # Close modal
            self.cell_modal.open = False
            
        except Exception as e:
            logger.error(f"Modal apply error: {e}")
            self._update_status(f"Selection apply failed: {e}", "danger")

    def _on_modal_cancel(self, event):
        """Cancel modal without applying changes."""
        # Simply close modal without changing selection
        self.cell_modal.open = False
        self._update_status("Cell selection cancelled", "info")

    def _load_analysis_options(self):
        """Load analysis options - single registry call."""
        try:
            analysis_options = self.registry.get_analysis_options()
            if analysis_options:
                self.analysis_select.options = analysis_options
                self._update_status("Analysis options loaded", "info")

        except Exception as e:
            self._update_status(f"Failed to load analysis options: {e}", "danger")

    def _on_analysis_changed(self, event):
        """Handle analysis selection change."""
        analysis_id = event.new[1] if isinstance(event.new, tuple) and len(event.new) >= 2 else event.new
        if not analysis_id:
            return

        try:
            config = self.registry.get_analysis(analysis_id)
            if config:
                self.current_config['analysis_type'] = analysis_id
                self.current_config['analysis_name'] = config.name

                # Update axis options - single registry call
                self._update_axis_options(analysis_id, config)
                self._update_status(f"Selected {config.name}", "info")

        except Exception as e:
            self._update_status(f"Analysis selection error: {e}", "danger")

    def _update_axis_options(self, analysis_id, config):
        """Update axis options based on analysis."""
        try:
            # X-axis options (time-based defaults)
            x_options = [
                ("Time (s)", "start_time_s"),
                ("Duration (s)", "duration_s"),
                ("Potential (V)", "start_potential_v"),
                ("Capacity (Ah)", "capacity_ah")
            ]
            self.x_axis_select.options = x_options

            # Y-axis options from analysis
            y_options = []
            if hasattr(config, 'output_columns') and config.output_columns:
                if 'metrics' in config.output_columns:
                    for col in config.output_columns['metrics']:
                        unit = self.registry.get_column_unit(analysis_id, col) if hasattr(self.registry, 'get_column_unit') else ''
                        display_name = col.replace('_', ' ').title()
                        if unit:
                            display_name += f" ({unit})"
                        prefixed_col = f"{analysis_id}_{col}"
                        y_options.append((display_name, prefixed_col))

            self.y_axis_multiselect.options = y_options

            # Set defaults and force widget refresh
            if y_options:
                self.y_axis_multiselect.value = [y_options[0][1]]
                self.current_config['y_axes'] = [y_options[0][1]]
                # Trigger param event to ensure UI updates
                self.y_axis_multiselect.param.trigger('options')
                self.y_axis_multiselect.param.trigger('value')

        except Exception as e:
            logger.error(f"Failed to update axis options: {e}")

    def _on_plot_tab_changed(self, event):
        """Handle plot tab selection change."""
        if isinstance(event.new, int):
            self.active_plot_index = event.new
            self._sync_controls_to_plot()

    def _on_add_plot(self, event):
        """Add new plot configuration."""
        if len(self.plot_configs) < 4:  # Limit to 4 plots
            new_config = self._create_empty_plot_config()
            self.plot_configs.append(new_config)

            # Update tabs
            plot_num = len(self.plot_configs)
            self.plot_tabs.append((f"Plot {plot_num}", pn.pane.HTML("")))
            self.plot_tabs.active = plot_num - 1

            # Enable remove button
            self.remove_plot_btn.disabled = False

            self._update_plot_grid()

    def _on_remove_plot(self, event):
        """Remove current plot."""
        if len(self.plot_configs) > 1:
            # Remove config
            self.plot_configs.pop(self.active_plot_index)

            # Update tabs
            self.plot_tabs.pop(self.active_plot_index)

            # Adjust active index
            if self.active_plot_index >= len(self.plot_configs):
                self.active_plot_index = len(self.plot_configs) - 1
                self.plot_tabs.active = self.active_plot_index

            # Disable remove button if only one plot left
            if len(self.plot_configs) == 1:
                self.remove_plot_btn.disabled = True

            self._update_plot_grid()

    def _sync_controls_to_plot(self):
        """Sync control values to active plot configuration."""
        config = self.current_config

        # Sync analysis select - find matching tuple
        if config['analysis_type']:
            for option in self.analysis_select.options:
                if isinstance(option, tuple) and len(option) >= 2 and option[1] == config['analysis_type']:
                    self.analysis_select.value = option
                    break
            else:
                self.analysis_select.value = config['analysis_type']

        # Sync x-axis select - find matching tuple
        if config['x_axis']:
            for option in self.x_axis_select.options:
                if isinstance(option, tuple) and len(option) >= 2 and option[1] == config['x_axis']:
                    self.x_axis_select.value = option
                    break
            else:
                self.x_axis_select.value = config['x_axis']

        # Sync y-axis multiselect - find matching tuples
        if config['y_axes']:
            matching_options = []
            for y_axis in config['y_axes']:
                for option in self.y_axis_multiselect.options:
                    if isinstance(option, tuple) and len(option) >= 2 and option[1] == y_axis:
                        matching_options.append(option)
                        break
            self.y_axis_multiselect.value = matching_options if matching_options else config['y_axes']

        # Sync group select - find matching tuple  
        if config['group_by']:
            for option in self.group_select.options:
                if isinstance(option, tuple) and len(option) >= 2 and option[1] == config['group_by']:
                    self.group_select.value = option
                    break
            else:
                self.group_select.value = config['group_by']

        self.plot_type_radio.value = config['plot_type']

        # Sync range controls
        if config['x_range'][0] is not None:
            self.x_min_input.value = config['x_range'][0]
            self.x_max_input.value = config['x_range'][1]
            self.x_range_slider.value = config['x_range']

    def _on_x_axis_changed(self, event):
        """Update X-axis in current config."""
        x_axis = event.new[1] if isinstance(event.new, tuple) and len(event.new) >= 2 else event.new
        self.current_config['x_axis'] = x_axis

    def _on_y_axes_changed(self, event):
        """Update Y-axes in current config."""
        y_axes = []
        if event.new:
            for item in event.new:
                if isinstance(item, tuple) and len(item) >= 2:
                    y_axes.append(item[1])
                else:
                    y_axes.append(item)
        self.current_config['y_axes'] = y_axes

    def _on_group_changed(self, event):
        """Update grouping in current config."""
        group_by = event.new[1] if isinstance(event.new, tuple) and len(event.new) >= 2 else event.new
        self.current_config['group_by'] = group_by

    def _on_plot_type_changed(self, event):
        """Update plot type in current config."""
        self.current_config['plot_type'] = event.new

    def _on_generate_plot(self, event):
        """Generate plot for current configuration."""
        try:
            # Load dataset if needed
            if self.dataset is None:
                self._load_dataset()

            # Generate plot
            plot = self._create_plot(self.current_config)
            if plot:
                self.current_config['plot_object'] = plot
                self._update_plot_grid()
                self._update_status("Plot generated successfully", "success")

        except Exception as e:
            self._update_status(f"Plot generation failed: {e}", "danger")
            logger.error(f"Plot generation error: {e}")

    def _load_dataset(self):
        """Load dataset for plotting."""
        try:
            self._update_status("Loading dataset...", "info")
            dataset = self.api.get_research_dataset_for_perspective(cells=self.selected_cells)

            if isinstance(dataset, pl.DataFrame):
                self.dataset = dataset.to_pandas()
            else:
                self.dataset = dataset

            logger.info(f"Dataset loaded: {len(self.dataset)} rows")

        except Exception as e:
            raise Exception(f"Failed to load dataset: {e}")

    def _create_plot(self, config):
        """Create hvplot from configuration."""
        if not config['y_axes'] or self.dataset is None:
            return None

        try:
            df = self.dataset.copy()
            x_col = config['x_axis']
            y_cols = config['y_axes']
            group_col = config['group_by'] if config['group_by'] else None
            plot_type = config['plot_type']

            # Extract display names safely for title
            y_display_names = []
            for y_col in y_cols:
                if isinstance(y_col, str) and '_' in y_col:
                    # Convert column name to display name
                    y_display_names.append(y_col.split('_', 1)[1].replace('_', ' ').title())
                else:
                    y_display_names.append(str(y_col))
            
            x_display = x_col.replace('_', ' ').title() if isinstance(x_col, str) else str(x_col)

            # Basic plot parameters  
            plot_kwargs = {
                'x': x_col,
                'y': y_cols[0] if len(y_cols) == 1 else y_cols,
                'width': 600,
                'height': 400,
                'title': f"{config['analysis_name']}: {', '.join(y_display_names)} vs {x_display}"
            }

            # Add grouping
            if group_col and group_col in df.columns:
                plot_kwargs['by'] = group_col

            # Add range limits
            if config['x_range'][0] is not None:
                plot_kwargs['xlim'] = config['x_range']
            if config['y_range'][0] is not None:
                plot_kwargs['ylim'] = config['y_range']

            # Create plot based on type
            if plot_type == 'scatter':
                return df.hvplot.scatter(**plot_kwargs)
            elif plot_type == 'line':
                return df.hvplot.line(**plot_kwargs)
            elif plot_type == 'histogram':
                return df.hvplot.hist(y=y_cols[0], bins=30, **{k: v for k, v in plot_kwargs.items() if k not in ['x', 'xlim']})
            else:
                return df.hvplot.scatter(**plot_kwargs)

        except Exception as e:
            logger.error(f"Plot creation failed: {e}")
            return None

    def _update_plot_grid(self):
        """Update plot grid layout based on number of plots."""
        self.plot_grid.clear()

        num_plots = len(self.plot_configs)

        if num_plots == 1:
            plot_obj = self.plot_configs[0]['plot_object']
            self.plot_grid[0, 0] = plot_obj if plot_obj else pn.pane.Alert("Generate plot to see visualization", alert_type="info")

        elif num_plots == 2:
            for i in range(2):
                plot_obj = self.plot_configs[i]['plot_object']
                self.plot_grid[0, i] = plot_obj if plot_obj else pn.pane.Alert(f"Plot {i+1} - Generate to see visualization", alert_type="info")

        elif num_plots == 3:
            plot_obj = self.plot_configs[0]['plot_object']
            self.plot_grid[0, 0:2] = plot_obj if plot_obj else pn.pane.Alert("Plot 1 - Generate to see visualization", alert_type="info")

            for i in range(1, 3):
                plot_obj = self.plot_configs[i]['plot_object']
                self.plot_grid[1, i-1] = plot_obj if plot_obj else pn.pane.Alert(f"Plot {i+1} - Generate to see visualization", alert_type="info")

        elif num_plots == 4:
            for i in range(4):
                row = i // 2
                col = i % 2
                plot_obj = self.plot_configs[i]['plot_object']
                self.plot_grid[row, col] = plot_obj if plot_obj else pn.pane.Alert(f"Plot {i+1} - Generate to see visualization", alert_type="info")

    def _update_status(self, message, alert_type="info"):
        """Update status display."""
        self.status_alert.object = message
        self.status_alert.alert_type = alert_type


# Wrapper class for integration
class ElectrochemicalExplorerTabWrapper(param.Parameterized):
    """Wrapper to match existing component patterns."""

    def __init__(self, api, **params):
        super().__init__(**params)
        try:
            self.tab = CleanElectrochemicalExplorer(api)
            self.panel = self.tab.panel
        except Exception as e:
            self.panel = pn.pane.Alert(f"Failed to initialize explorer: {e}", alert_type="danger")

    def __panel__(self):
        return self.panel