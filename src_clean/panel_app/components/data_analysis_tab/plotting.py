"""
Tab 3 Data Analysis - Clean Plotting with hvplot + bokeh

Clean plotting manager using hvplot + bokeh for all visualizations.
No HTML, just proper interactive plots.
"""

import panel as pn
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import holoviews as hv
import hvplot.pandas

# Enable bokeh backend
hv.extension('bokeh')
pn.extension('bokeh')

class PlottingManager:
    """
    Clean plotting manager using hvplot + bokeh.
    All plots are interactive bokeh plots via hvplot.
    """

    def __init__(self, api):
        self.api = api

        # Plot state
        self.current_plot = None
        self.current_analysis_type = None
        self.current_data = None
        self.current_settings = None

        # Create components
        self._create_plot_area()
        self._create_plot_controls()
        
        # Setup plot type change handler
        self.plot_type_select.param.watch(self._on_plot_type_changed, 'value')

    def _create_plot_area(self):
        """Create plot display area."""

        # Empty state
        self.empty_plot = pn.pane.Markdown("**Select groups and run analysis to see plots**")

        # Main plot pane
        self.plot_pane = pn.pane.HoloViews(
            None,
            sizing_mode='stretch_width',
            height=400
        )

        # Initially show empty message
        self.plot_container = pn.Column(
            self.empty_plot,
            sizing_mode='stretch_width',
            height=400
        )

        self.plot_area = self.plot_container

    def get_plot_area(self):
        """Return the plot area."""
        return self.plot_area

    def _create_plot_controls(self):
        """Create plot controls."""

        self.plot_type_select = pn.widgets.Select(
            name="Plot Type",
            options=["Default"],
            width=200
        )

        self.export_btn = pn.widgets.Button(
            name="Export",
            button_type="light",
            width=100,
            disabled=True
        )

        self.plot_controls = pn.Row(
            self.plot_type_select,
            self.export_btn
        )

    def get_plot_controls(self):
        """Return plot controls."""
        return self.plot_controls

    def create_plot(self, analysis_type: str, data: Dict[str, Any], settings: Dict[str, Any]):
        """Create plot using hvplot."""

        try:
            # Store current data for plot type switching
            self.current_analysis_type = analysis_type
            self.current_data = data
            self.current_settings = settings

            # Handle errors
            if data.get("error"):
                return pn.pane.Markdown(f"**Error:** {data['error']}")

            # Route to appropriate plot method
            if analysis_type == "basic_statistics":
                return self._create_basic_stats_plot(data, settings)
            elif analysis_type == "resistance_analysis":
                return self._create_resistance_plot(data, settings)
            elif analysis_type == "kinetics_analysis":
                return self._create_kinetics_plot(data, settings)
            elif analysis_type == "dqdv_analysis":
                return self._create_dqdv_plot(data, settings)
            else:
                return pn.pane.Markdown(f"**Plot type '{analysis_type}' not implemented yet**")

        except Exception as e:
            print(f"Plot creation error: {e}")
            return pn.pane.Markdown(f"**Plot Error:** {str(e)}")

    def _create_basic_stats_plot(self, data: Dict[str, Any], settings: Dict[str, Any]):
        """Route to appropriate basic statistics visualization based on plot type selector."""
        
        # Get current plot type from selector - handle tuple format
        plot_type_raw = self.plot_type_select.value
        if isinstance(plot_type_raw, tuple) and len(plot_type_raw) > 1:
            plot_type = plot_type_raw[1]  # Get the value part of (label, value) tuple
        else:
            plot_type = str(plot_type_raw)
            
        print(f"DEBUG: Creating basic stats plot, type: {plot_type}")

        # Route to specific plot method
        if plot_type == "technique_count":
            return self._basic_stats_technique_count(data)
        elif plot_type == "duration_analysis":
            return self._basic_stats_duration_analysis(data)
        else:
            return self._basic_stats_technique_count(data)  # Default

    def _basic_stats_technique_count(self, data: Dict[str, Any]):
        """Create technique count bar chart using real segment data."""

        # Get real segments data
        segments = data.get("segments", [])
        
        if not segments:
            return pn.pane.Markdown("**No segments data available for plotting**")

        print(f"DEBUG: Technique count plot with {len(segments)} segments")

        try:
            # Create DataFrame from real segment data
            segments_df = pd.DataFrame(segments)
            
            # Group by technique and count
            technique_counts = segments_df.groupby('fundamental_technique').size().reset_index()
            technique_counts.columns = ['Technique', 'Count']
            
            print(f"DEBUG: Technique counts: {technique_counts.to_dict('records')}")

            # Create bar chart with hvplot
            plot = technique_counts.hvplot.bar(
                x='Technique',
                y='Count',
                title='Technique Count Analysis',
                color='steelblue',
                tools=['pan', 'wheel_zoom', 'box_zoom', 'reset', 'save']
            )

            return plot

        except Exception as e:
            print(f"DEBUG: Error creating technique count plot: {e}")
            import traceback
            traceback.print_exc()
            return pn.pane.Markdown(f"**Error creating plot:** {str(e)}")

    def _basic_stats_duration_analysis(self, data: Dict[str, Any]):
        """Create duration analysis histogram using real segment data."""

        # Get real segments data
        segments = data.get("segments", [])
        
        if not segments:
            return pn.pane.Markdown("**No segments data available for plotting**")

        print(f"DEBUG: Duration analysis plot with {len(segments)} segments")

        try:
            # Create DataFrame from real segment data
            segments_df = pd.DataFrame(segments)
            
            # Check if duration_s exists
            if 'duration_s' not in segments_df.columns:
                return pn.pane.Markdown("**No duration data available in segments**")

            # Filter out null/zero durations
            duration_data = segments_df[segments_df['duration_s'].notna() & (segments_df['duration_s'] > 0)]
            
            if duration_data.empty:
                return pn.pane.Markdown("**No valid duration data available**")

            print(f"DEBUG: Duration range: {duration_data['duration_s'].min():.1f} - {duration_data['duration_s'].max():.1f} seconds")

            # Create histogram with hvplot, colored by technique
            plot = duration_data.hvplot.hist(
                y='duration_s', 
                by='fundamental_technique',
                bins=15,
                title='Duration Analysis by Technique', 
                xlabel='Duration (s)',
                ylabel='Count',
                alpha=0.7,
                tools=['pan', 'wheel_zoom', 'box_zoom', 'reset', 'save']
            )

            return plot

        except Exception as e:
            print(f"DEBUG: Error creating duration analysis plot: {e}")
            import traceback
            traceback.print_exc()
            return pn.pane.Markdown(f"**Error creating plot:** {str(e)}")

    def _create_resistance_plot(self, data: Dict[str, Any], settings: Dict[str, Any]):
        """Create resistance analysis plot."""

        # For now, create a placeholder plot
        # In real implementation, you'd extract resistance data and plot it

        # Create sample data for demo
        x = np.linspace(0, 100, 50)
        y = np.random.normal(10, 2, 50)  # Sample resistance values

        df = pd.DataFrame({'Time': x, 'Resistance': y})

        plot = df.hvplot.line(
            x='Time',
            y='Resistance',
            title='Resistance vs Time',
            width=600,
            height=300,
            color='red'
        )

        return plot

    def _create_kinetics_plot(self, data: Dict[str, Any], settings: Dict[str, Any]):
        """Create kinetics analysis plot."""

        # Sample kinetics data
        t = np.linspace(0, 100, 100)
        current = np.exp(-t/20) * np.random.normal(1, 0.1, 100)

        df = pd.DataFrame({'Time': t, 'Current': current})

        plot = df.hvplot.line(
            x='Time',
            y='Current',
            title='Current Decay (Kinetics)',
            width=600,
            height=300,
            color='green'
        )

        return plot

    def _create_dqdv_plot(self, data: Dict[str, Any], settings: Dict[str, Any]):
        """dQ/dV analysis not implemented yet."""

        return pn.pane.Markdown(
            "**dQ/dV Analysis**\n\n"
            "This analysis type is not implemented yet.\n\n"
            "Will include:\n"
            "- Differential capacity curves\n" 
            "- Phase transition detection\n"
            "- Peak analysis\n\n"
            "*Coming in future version*"
        )

    def update_plot_area(self, plot_object):
        """Update the plot display area."""

        try:
            if plot_object is None:
                # Show empty state
                self.plot_container.objects = [self.empty_plot]
                self.export_btn.disabled = True
            else:
                # Show plot
                if hasattr(plot_object, '__panel__'):
                    # It's a holoviews object
                    self.plot_pane.object = plot_object
                    self.plot_container.objects = [self.plot_pane]
                else:
                    # It's a panel object
                    self.plot_container.objects = [plot_object]

                self.current_plot = plot_object
                self.export_btn.disabled = False

        except Exception as e:
            print(f"Error updating plot area: {e}")
            error_msg = pn.pane.Markdown(f"**Plot Update Error:** {str(e)}")
            self.plot_container.objects = [error_msg]

    def update_available_plots(self, analysis_type: str):
        """Update available plot types based on analysis type."""

        plot_options = {
            "basic_statistics": [
                ("Technique Count", "technique_count"),
                ("Duration Analysis", "duration_analysis")
            ],
            "resistance_analysis": [
                ("Resistance vs Time", "resistance_time"),
                ("Impedance Plot", "impedance_plot")
            ],
            "kinetics_analysis": [
                ("Current Decay", "current_decay"),
                ("Time Constants", "time_constants")
            ],
            "dqdv_analysis": [
                ("dQ/dV Curves", "dqdv_curves"),
                ("Peak Analysis", "peak_analysis")
            ]
        }

        options = plot_options.get(analysis_type, [("Default", "default")])
        self.plot_type_select.options = options
        if options:
            self.plot_type_select.value = options[0][1]

    def _on_plot_type_changed(self, event):
        """Handle plot type selector changes - regenerate plot with new type."""
        
        print(f"DEBUG: Plot type changed to: {event.new}")
        
        # Regenerate plot with current data if available
        if (self.current_analysis_type and self.current_data and self.current_settings):
            try:
                # Regenerate plot with new plot type
                new_plot = self.create_plot(
                    self.current_analysis_type,
                    self.current_data,
                    self.current_settings
                )
                
                # Update the plot area
                self.update_plot_area(new_plot)
                
            except Exception as e:
                print(f"Error switching plot type: {e}")
                error_plot = pn.pane.Markdown(f"**Plot Switch Error:** {str(e)}")
                self.update_plot_area(error_plot)