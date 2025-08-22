"""
Visualization Panel - Dependent Plotting Component

Handles all visualization for data analysis tab. Receives data from selection events
and provides interactive plots. Designed as dependent component that visualizes
exactly what the user has selected in the parent data analysis tab.
"""

import panel as pn
import param
import numpy as np
import pandas as pd
import holoviews as hv
from holoviews.operation import decimate
from typing import List, Dict, Any, Optional


class VisualizationPanel(param.Parameterized):
    """
    Dependent visualization component for electrochemical data analysis.

    Features:
    - Receives data directly from parent DataAnalysisTab selections
    - Updates immediately when user loads segments or calculates subset stats
    - Plot type selection dropdown
    - Interactive HoloViews plots with actual column names
    - Technique-specific visualizations
    - Statistical plots (distributions, correlations)
    - Professional styling matching main app
    """

    current_data = param.List(default=[], doc="Current segments data for plotting")
    plot_type = param.String(default="temporal_trends", doc="Selected plot type")
    status_message = param.String(default="", doc="Status message")

    def __init__(self, api, **params):
        super().__init__(**params)
        self.api = api
        self._create_components()
        self._setup_plot_types()

    def _create_components(self):
        """Create visualization UI components."""

        # Plot type selector
        self.plot_type_selector = pn.widgets.Select(
            name="Plot Type",
            options=[],  # Will be populated in _setup_plot_types
            width=200,
            margin=(5, 5)
        )
        self.plot_type_selector.param.watch(self._on_plot_type_changed, 'value')

        # Plot controls
        self.plot_controls = pn.Row(
            margin=(5, 5)
        )

        # Main plot area
        self.plot_pane = pn.pane.HoloViews(
            None,
            min_height=400,
            sizing_mode='stretch_width',
            margin=(10, 5)
        )

        # Plot message (when no data)
        self.plot_message = pn.pane.HTML(
            """<div style='text-align: center; padding: 80px 20px; color: #999;'>
               <span style='font-size: 48px; opacity: 0.3;'>📊</span><br><br>
               <strong style='font-size: 18px;'>Interactive Visualization</strong><br>
               <span style='font-size: 14px;'>Load segments from groups to see plots</span>
               </div>""",
            visible=True,
            margin=(10, 5)
        )

        # Initially hide plot pane
        self.plot_pane.visible = False

        # Plot info display
        self.plot_info_display = pn.pane.HTML(
            "",
            margin=(5, 5)
        )

    def _setup_plot_types(self):
        """Setup available plot types."""
        self.plot_types = {
            "temporal_trends": {
                "name": "📈 Temporal Trends",
                "description": "Base metrics vs time/sequence",
                "requires_data": True
            },
            "distributions": {
                "name": "📊 Distributions",
                "description": "Histograms of base metrics",
                "requires_data": True
            },
            "correlations": {
                "name": "🔗 Correlations",
                "description": "Scatter plots between metrics",
                "requires_data": True
            },
            "technique_specific": {
                "name": "⚡ Technique-Specific",
                "description": "Specialized plots by technique type",
                "requires_data": True
            },
            "group_comparison": {
                "name": "📋 Group Comparison",
                "description": "Compare metrics across groups",
                "requires_data": True
            }
        }

        # Set initial options
        self._update_plot_options()

    def _update_plot_options(self):
        """Update plot type options based on current data."""
        if not self.current_data:
            options = [("Select data first...", "none")]
        else:
            options = [(info["name"], plot_type)
                       for plot_type, info in self.plot_types.items()]

        self.plot_type_selector.options = options

        # Set default selection
        if self.current_data and len(options) > 0:
            self.plot_type_selector.value = options[0][1]

    @property
    def panel(self):
        """Return the visualization panel layout."""

        # Controls section
        controls_section = pn.Column(
            pn.Row(
                pn.Column(
                    pn.pane.HTML(
                        "<label style='font-weight: 500; color: #555; font-size: 14px;'>Visualization Type:</label>"),
                    self.plot_type_selector,
                    width=220
                ),
                self.plot_controls,
                margin=(5, 5)
            ),
            margin=(10, 10)
        )

        # Plot area
        plot_area = pn.Column(
            self.plot_info_display,
            self.plot_message,
            self.plot_pane,
            min_height=450,
            styles={'background': '#FAFAFA', 'border-radius': '4px', 'padding': '10px'},
            margin=(10, 10)
        )

        return pn.Column(
            controls_section,
            plot_area,
            sizing_mode='stretch_width'
        )

    def update_data(self, segments_data: List[Dict]):
        """
        Update visualization with new segments data from parent tab.

        Called immediately when:
        - User loads segments from groups
        - User calculates statistics for subset
        - User changes selections in parent tab

        Args:
            segments_data: List of segment dictionaries with actual column names
        """
        self.current_data = segments_data
        self._update_plot_options()

        if segments_data:
            self._update_plot_info(segments_data)
            self._create_current_plot()
        else:
            self._show_no_data_message()

    def _update_plot_info(self, segments_data):
        """Update plot information display."""
        num_segments = len(segments_data)
        techniques = list(set(seg['technique'] for seg in segments_data))
        groups = list(set(seg.get('group_name', 'Unknown') for seg in segments_data))

        self.plot_info_display.object = f"""
        <div style='background: #E3F2FD; padding: 10px; border-radius: 4px; 
                    border-left: 4px solid #1976D2; margin-bottom: 10px;'>
            <div style='font-weight: 600; color: #1976D2; margin-bottom: 5px;'>
                📊 Dataset Overview
            </div>
            <div style='font-size: 12px; color: #0D47A1; display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px;'>
                <div><strong>Segments:</strong> {num_segments}</div>
                <div><strong>Techniques:</strong> {', '.join(techniques)}</div>
                <div><strong>Groups:</strong> {len(groups)}</div>
            </div>
        </div>
        """

    def _show_no_data_message(self):
        """Show no data message."""
        self.plot_message.visible = True
        self.plot_pane.visible = False
        self.plot_info_display.object = ""

    def _on_plot_type_changed(self, event):
        """Handle plot type selection change."""
        plot_type = event.new
        
        # Handle tuple case from Select widget (display_name, actual_value)
        if isinstance(plot_type, tuple):
            plot_type = plot_type[1] if len(plot_type) > 1 else plot_type[0]
        elif not isinstance(plot_type, str):
            plot_type = str(plot_type) if plot_type is not None else ""
        
        if plot_type and plot_type != "none" and self.current_data:
            self.plot_type = plot_type
            self._create_current_plot()

    def _create_current_plot(self):
        """Create plot based on current plot type and data."""
        if not self.current_data or not self.plot_type:
            return

        try:
            if self.plot_type == "temporal_trends":
                self._create_temporal_trends_plot()
            elif self.plot_type == "distributions":
                self._create_distributions_plot()
            elif self.plot_type == "correlations":
                self._create_correlations_plot()
            elif self.plot_type == "technique_specific":
                self._create_technique_specific_plot()
            elif self.plot_type == "group_comparison":
                self._create_group_comparison_plot()
            else:
                self._show_plot_error(f"Plot type '{self.plot_type}' not implemented yet")

        except Exception as e:
            self._show_plot_error(f"Error creating plot: {str(e)}")

    def _create_temporal_trends_plot(self):
        """Create temporal trends visualization using actual column names."""
        # Convert to DataFrame for plotting
        df = pd.DataFrame(self.current_data)

        # Create time sequence (if no actual timestamps, use segment order)
        df['sequence'] = range(len(df))

        # Choose metric to plot using actual column names (voltage recovery)
        df['voltage_recovery'] = df['end_potential_v'] - df['start_potential_v']

        # Create HoloViews curve
        curve = hv.Curve(df, kdims=['sequence'], vdims=['voltage_recovery'],
                         label='Voltage Recovery')

        # Add technique-based coloring if multiple techniques
        if df['technique'].nunique() > 1:
            # Create separate curves for each technique
            curves = []
            colors = ['#1976D2', '#2E8B57', '#9932CC', '#FF6347', '#FFD700']

            for i, (technique, group_data) in enumerate(df.groupby('technique')):
                color = colors[i % len(colors)]
                tech_curve = hv.Curve(group_data, kdims=['sequence'], vdims=['voltage_recovery'],
                                      label=f'{technique} Recovery')
                curves.append(tech_curve.opts(color=color, line_width=2))

            if curves:
                plot = hv.Overlay(curves)
            else:
                plot = curve.opts(color='#1976D2', line_width=2)
        else:
            plot = curve.opts(color='#1976D2', line_width=2)

        # Apply professional styling
        plot = plot.opts(
            title="Voltage Recovery vs Sequence",
            xlabel="Segment Sequence",
            ylabel="Voltage Recovery (V)",
            width=700,
            height=400,
            tools=['pan', 'wheel_zoom', 'box_zoom', 'reset', 'save'],
            active_tools=['pan', 'wheel_zoom'],
            legend_position='right'
        )

        self.plot_pane.object = plot
        self.plot_pane.visible = True
        self.plot_message.visible = False

    def _create_distributions_plot(self):
        """Create distributions visualization using actual column names."""
        df = pd.DataFrame(self.current_data)

        # Create histogram for voltage recovery using actual column names
        df['voltage_recovery'] = df['end_potential_v'] - df['start_potential_v']

        # Create HoloViews histogram
        hist = hv.Histogram(np.histogram(df['voltage_recovery'], bins=10))

        plot = hist.opts(
            title="Voltage Recovery Distribution",
            xlabel="Voltage Recovery (V)",
            ylabel="Count",
            color='#1976D2',
            alpha=0.7,
            width=700,
            height=400,
            tools=['pan', 'wheel_zoom', 'box_zoom', 'reset', 'save']
        )

        self.plot_pane.object = plot
        self.plot_pane.visible = True
        self.plot_message.visible = False

    def _create_correlations_plot(self):
        """Create correlations visualization using actual column names."""
        df = pd.DataFrame(self.current_data)

        # Create scatter plot: duration vs voltage recovery using actual column names
        df['voltage_recovery'] = df['end_potential_v'] - df['start_potential_v']

        points = hv.Points(df, kdims=['duration_s'], vdims=['voltage_recovery'])

        plot = points.opts(
            title="Duration vs Voltage Recovery",
            xlabel="Duration (s)",
            ylabel="Voltage Recovery (V)",
            color='#1976D2',
            size=8,
            alpha=0.7,
            width=700,
            height=400,
            tools=['pan', 'wheel_zoom', 'box_zoom', 'reset', 'save', 'hover']
        )

        self.plot_pane.object = plot
        self.plot_pane.visible = True
        self.plot_message.visible = False

    def _create_technique_specific_plot(self):
        """Create technique-specific visualization."""
        df = pd.DataFrame(self.current_data)

        # Group by technique and create appropriate plots
        techniques = df['technique'].unique()

        if 'REST' in techniques:
            # Focus on REST phase analysis using actual column names
            rest_data = df[df['technique'] == 'REST']
            rest_data['voltage_recovery'] = rest_data['end_potential_v'] - rest_data['start_potential_v']

            # Create voltage recovery plot
            points = hv.Points(rest_data, kdims=['duration_s'], vdims=['voltage_recovery'])

            plot = points.opts(
                title="REST Phase Analysis: Duration vs Voltage Recovery",
                xlabel="Rest Duration (s)",
                ylabel="Voltage Recovery (V)",
                color='#2E8B57',
                size=10,
                alpha=0.8,
                width=700,
                height=400,
                tools=['pan', 'wheel_zoom', 'box_zoom', 'reset', 'save', 'hover']
            )
        else:
            # Generic technique plot using actual column names
            df['voltage_recovery'] = df['end_potential_v'] - df['start_potential_v']
            sequence = range(len(df))

            curve = hv.Curve(list(zip(sequence, df['voltage_recovery'])),
                             kdims=['sequence'], vdims=['voltage_recovery'])

            plot = curve.opts(
                title=f"Technique Analysis: {', '.join(techniques)}",
                xlabel="Sequence",
                ylabel="Voltage Recovery (V)",
                color='#9932CC',
                line_width=2,
                width=700,
                height=400,
                tools=['pan', 'wheel_zoom', 'box_zoom', 'reset', 'save']
            )

        self.plot_pane.object = plot
        self.plot_pane.visible = True
        self.plot_message.visible = False

    def _create_group_comparison_plot(self):
        """Create group comparison visualization."""
        df = pd.DataFrame(self.current_data)

        # Create box plots by group (if multiple groups) using actual column names
        if 'group_name' in df.columns and df['group_name'].nunique() > 1:
            df['voltage_recovery'] = df['end_potential_v'] - df['start_potential_v']

            # Create box plot using HoloViews
            # Note: This is a simplified version - real implementation might use BoxWhisker
            plots = []
            colors = ['#1976D2', '#2E8B57', '#9932CC', '#FF6347']

            for i, (group, group_data) in enumerate(df.groupby('group_name')):
                color = colors[i % len(colors)]
                points = hv.Points(group_data, kdims=['group_name'], vdims=['voltage_recovery'],
                                   label=group)
                plots.append(points.opts(color=color, size=8, alpha=0.7))

            if plots:
                plot = hv.Overlay(plots).opts(
                    title="Voltage Recovery by Group",
                    xlabel="Group",
                    ylabel="Voltage Recovery (V)",
                    width=700,
                    height=400,
                    legend_position='right'
                )
            else:
                plot = hv.Text(0, 0, 'No group data available')
        else:
            # Single group - show message
            plot = hv.Text(0.5, 0.5, 'Multiple groups required for comparison').opts(
                title="Group Comparison",
                width=700,
                height=400
            )

        self.plot_pane.object = plot
        self.plot_pane.visible = True
        self.plot_message.visible = False

    def _show_plot_error(self, error_message):
        """Show plot error message."""
        self.plot_message.object = f"""
        <div style='text-align: center; padding: 80px 20px; color: #D32F2F;'>
            <span style='font-size: 48px; opacity: 0.3;'>⚠️</span><br><br>
            <strong style='font-size: 18px;'>Visualization Error</strong><br>
            <span style='font-size: 14px;'>{error_message}</span>
        </div>
        """
        self.plot_message.visible = True
        self.plot_pane.visible = False


# Standalone testing
if __name__ == "__main__":
    class MockAPI:
        pass


    # Create test data using actual column names
    test_data = [
        {
            'segment_id': 'seg_001',
            'technique': 'REST',
            'start_potential_v': 3.75,
            'end_potential_v': 3.82,
            'duration_s': 300.0,
            'group_name': 'GITT Rest'
        },
        {
            'segment_id': 'seg_002',
            'technique': 'REST',
            'start_potential_v': 3.78,
            'end_potential_v': 3.85,
            'duration_s': 295.0,
            'group_name': 'GITT Rest'
        },
        {
            'segment_id': 'seg_003',
            'technique': 'CC',
            'start_potential_v': 3.0,
            'end_potential_v': 4.2,
            'duration_s': 3600.0,
            'group_name': 'Formation'
        }
    ]

    # Create and test component
    api = MockAPI()
    viz_panel = VisualizationPanel(api)
    viz_panel.update_data(test_data)

    # Create Panel app for testing
    pn.extension('bokeh')
    hv.extension('bokeh')

    app = pn.Column(
        pn.pane.HTML("<h2>Visualization Panel Test</h2>"),
        viz_panel.panel,
        sizing_mode='stretch_width'
    )

    app.show(port=5010)