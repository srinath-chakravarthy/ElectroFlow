"""
Tab 3 Data Analysis - Clean Plotting & Visualization Management

COMPLETE REWRITE: Responsive, consistent, debuggable plotting system.
- Responsive sizing using Panel containers, not hardcoded dimensions
- Redundant but debuggable individual methods for each plot type
- Universal interactivity standards for all plots
- Working plot type switching that actually shows different visualizations

Architecture: Clean plot generation with universal standards.
"""

import panel as pn
import holoviews as hv
import pandas as pd
import hvplot.pandas
from typing import Dict, List, Any, Optional


class PlottingManager:
    """
    Clean plotting system with responsive design and universal standards.

    Design Principles:
    1. Responsive sizing - no hardcoded dimensions, use Panel containers
    2. Redundant but debuggable - individual methods for each plot type
    3. Universal interactivity - same tool set for all plots
    4. Working plot switching - dropdown actually changes visualizations
    """

    def __init__(self, api):
        self.api = api

        # Create plot controls and responsive area
        self._create_plot_area()
        self._create_plot_controls()

        # Current state tracking
        self.current_plot = None
        self.current_analysis_type = None
        self.current_data = None
        self.current_settings = None
        self._updating_plot_options = False  # Prevent recursion

    def _create_plot_area(self):
        """Create responsive plot area using Panel container patterns."""

        # Responsive placeholder
        placeholder = pn.pane.HTML(
            """
            <div style='border: 2px dashed #E0E0E0; border-radius: 8px; 
                        padding: 40px; text-align: center; color: #666;
                        background: #FAFAFA; min-height: 400px;
                        display: flex; align-items: center; justify-content: center;'>
                <div>
                    <div style='font-size: 48px; margin-bottom: 10px;'>ðŸ“Š</div>
                    <div style='font-size: 18px; margin-bottom: 5px;'>Ready for Analysis</div>
                    <div style='font-size: 14px;'>Select groups and click "Analyze" to generate plots</div>
                </div>
            </div>
            """,
            sizing_mode='stretch_width'
        )

        # Responsive plot area - follows Tab 1 pattern
        self.plot_area = pn.Column(
            placeholder,
            min_height=470,
            sizing_mode='stretch_width'
        )

    def get_plot_area(self):
        """Return the responsive plot area."""
        return self.plot_area

    def _create_plot_controls(self):
        """Create plot controls interface."""

        # Plot type selector
        self.plot_type_selector = pn.widgets.Select(
            name="Plot Type",
            options=[("Summary Table", "summary_table")],
            value="summary_table",
            width=200
        )

        # Connect event handler
        self.plot_type_selector.param.watch(self._on_plot_type_changed, 'value')

        # Additional controls
        self.export_plot_btn = pn.widgets.Button(
            name="ðŸ’¾ Export Plot",
            button_type="default",
            width=120,
            disabled=True
        )

        # Controls layout
        self.plot_controls = pn.Row(
            self.plot_type_selector,
            pn.Spacer(width=20),
            self.export_plot_btn,
            margin=(10, 0)
        )

    def get_plot_controls(self):
        """Return the plot controls panel."""
        return self.plot_controls

    # ===== UNIVERSAL PLOT STANDARDS =====

    def _get_universal_plot_config(self):
        """Get universal plot configuration for all hvplot calls."""
        return {
            'tools': ['pan', 'wheel_zoom', 'box_zoom', 'reset', 'save']
            # Remove sizing_mode and min_height - these are for Panel containers, not hvplot
        }

    def _create_hvplot_with_standards(self, df, plot_method, **kwargs):
        """Create hvplot with universal standards applied."""
        config = self._get_universal_plot_config()

        # Remove invalid active_tools parameter that causes bokeh warnings
        plot_kwargs = {**kwargs}
        if 'active_tools' in plot_kwargs:
            del plot_kwargs['active_tools']

        # Apply universal config
        plot_kwargs.update(config)

        # Create the plot using the specified method
        return getattr(df.hvplot, plot_method)(**plot_kwargs)

    def _wrap_plot_in_container(self, plot, title_info=None):
        """Wrap plot in responsive container with optional title info."""
        components = []

        if title_info:
            components.append(title_info)

        # Add plot in responsive container
        if hasattr(plot, 'opts'):
            # HoloViews object
            components.append(pn.pane.HoloViews(plot, sizing_mode='stretch_width'))
        else:
            # Panel object
            components.append(plot)

        return pn.Column(*components, sizing_mode='stretch_width')

    # ===== MAIN PLOT GENERATION DISPATCHER =====

    def create_plot(self, analysis_type: str, data: Dict[str, Any], settings: Dict[str, Any]) -> Any:
        """Main plot generation dispatcher with clean routing."""

        try:
            # Store current data for plot type changes
            self.current_analysis_type = analysis_type
            self.current_data = data
            self.current_settings = settings

            # Update available plot types for this analysis
            self.update_available_plots(analysis_type)

            # Route to appropriate analysis method
            if analysis_type == "basic_statistics":
                return self._create_basic_statistics_plot(data, settings)
            elif analysis_type == "resistance_analysis":
                return self._create_resistance_plot(data, settings)
            elif analysis_type == "kinetics_analysis":
                return self._create_kinetics_plot(data, settings)
            elif analysis_type == "dqdv_analysis":
                return self._create_dqdv_plot(data, settings)
            else:
                return self._create_error_plot(f"Unknown analysis type: {analysis_type}")

        except Exception as e:
            print(f"Plot creation error for {analysis_type}: {e}")
            import traceback
            traceback.print_exc()
            return self._create_error_plot(f"Error creating plot: {str(e)}")

    # ===== BASIC STATISTICS PLOTTING =====

    def _create_basic_statistics_plot(self, data: Dict[str, Any], settings: Dict[str, Any]):
        """Route to appropriate basic statistics visualization."""
        plot_type = self.plot_type_selector.value

        if plot_type == "summary_table":
            return self._basic_stats_summary_table(data)
        elif plot_type == "histogram":
            return self._basic_stats_histogram(data)
        elif plot_type == "box_plot":
            return self._basic_stats_boxplot(data)
        else:
            return self._basic_stats_summary_table(data)  # Default

    def _basic_stats_summary_table(self, data: Dict[str, Any]):
        """Create responsive interactive bar chart for statistics summary."""

        # Extract data
        duration_mean = data.get('duration_mean', 0)
        duration_std = data.get('duration_std', 0)
        voltage_mean = data.get('voltage_mean', 0)
        voltage_std = data.get('voltage_std', 0)
        capacity_mean = data.get('capacity_mean', 0)
        capacity_std = data.get('capacity_std', 0)
        total_segments = data.get('total_segments', 0)
        total_groups = data.get('total_groups', 0)

        # Create plot data
        metrics_df = pd.DataFrame({
            'Metric': ['Duration (s)', 'Start Voltage (V)', 'Capacity (Ah)'],
            'Mean': [duration_mean, voltage_mean, capacity_mean],
            'Std': [duration_std, voltage_std, capacity_std]
        })

        try:
            # Create responsive bar chart
            plot = self._create_hvplot_with_standards(
                metrics_df, 'bar',
                x='Metric', y='Mean',
                title="Basic Statistics Summary",
                xlabel="Metric", ylabel="Mean Value",
                color='#1976D2', alpha=0.8
            )

            # Title info
            title_info = pn.pane.Markdown(f"""
            ### ðŸ“Š Basic Statistics Summary
            **{total_groups} groups â€¢ {total_segments} segments**
            """, margin=(10, 20))

            return self._wrap_plot_in_container(plot, title_info)

        except Exception as e:
            return self._create_error_plot(f"Error creating basic stats summary: {str(e)}")

    def _basic_stats_histogram(self, data: Dict[str, Any]):
        """Create responsive histogram for statistics distribution."""

        backend_results = data.get('backend_results', {})
        if not backend_results:
            return self._create_error_plot("No backend results for histogram")

        # Extract metrics for histogram
        metrics_data = []
        for metric_name, metric_stats in backend_results.items():
            if isinstance(metric_stats, dict) and 'count' in metric_stats:
                metrics_data.append({
                    'metric': metric_name.replace('_', ' ').title(),
                    'mean': metric_stats.get('mean', 0),
                    'count': metric_stats.get('count', 0)
                })

        if not metrics_data:
            return self._create_error_plot("No metric data for histogram")

        try:
            metrics_df = pd.DataFrame(metrics_data)

            # Create responsive bar chart
            plot = self._create_hvplot_with_standards(
                metrics_df, 'bar',
                x='metric', y='count',
                title="Statistical Distribution - Sample Counts",
                xlabel="Metric", ylabel="Sample Count",
                color='#388E3C', alpha=0.8
            )

            title_info = pn.pane.Markdown(f"""
            ### ðŸ“Š Statistical Distributions  
            **{len(metrics_data)} metrics analyzed**
            """, margin=(10, 20))

            return self._wrap_plot_in_container(plot, title_info)

        except Exception as e:
            return self._create_error_plot(f"Error creating histogram: {str(e)}")

    def _basic_stats_boxplot(self, data: Dict[str, Any]):
        """Create responsive box plot for statistics distribution."""

        backend_results = data.get('backend_results', {})
        if not backend_results:
            return self._create_error_plot("No backend results for box plot")

        # Extract metrics for box plot
        metrics_data = []
        for metric_name, metric_stats in backend_results.items():
            if isinstance(metric_stats, dict) and all(k in metric_stats for k in ['min', 'max', 'mean']):
                metrics_data.append({
                    'metric': metric_name.replace('_', ' ').title(),
                    'min': metric_stats.get('min', 0),
                    'max': metric_stats.get('max', 0),
                    'mean': metric_stats.get('mean', 0),
                    'std': metric_stats.get('std', 0)
                })

        if not metrics_data:
            return self._create_error_plot("No metric data for box plot")

        try:
            metrics_df = pd.DataFrame(metrics_data)

            # Create responsive range visualization
            plot = self._create_hvplot_with_standards(
                metrics_df, 'bar',
                x='metric', y='max',
                title="Statistical Ranges - Min/Max Values",
                xlabel="Metric", ylabel="Value Range",
                color='#9C27B0', alpha=0.8
            )

            title_info = pn.pane.Markdown(f"""
            ### ðŸ“¦ Statistical Ranges
            **{len(metrics_data)} metrics analyzed**
            """, margin=(10, 20))

            return self._wrap_plot_in_container(plot, title_info)

        except Exception as e:
            return self._create_error_plot(f"Error creating box plot: {str(e)}")

    # ===== RESISTANCE ANALYSIS PLOTTING =====

    def _create_resistance_plot(self, data: Dict[str, Any], settings: Dict[str, Any]):
        """Route to appropriate resistance visualization."""
        plot_type = self.plot_type_selector.value

        # Extract backend data from main tab wrapper
        backend_data = data.get('backend_results', data)

        if plot_type == "resistance_time":
            return self._resistance_time_plot(backend_data)
        elif plot_type == "resistance_distribution":
            return self._resistance_distribution_plot(backend_data)
        elif plot_type == "resistance_summary":
            return self._resistance_summary_plot(backend_data)
        else:
            return self._resistance_time_plot(backend_data)  # Default

    def _resistance_time_plot(self, data: Dict[str, Any]):
        """Create responsive resistance vs time scatter plot using actual backend structure."""

        # Use actual backend structure: individual_resistances list
        individual_resistances = data.get('individual_resistances', [])
        summary_stats = data.get('summary_statistics', {})

        if not individual_resistances:
            return self._create_error_plot("No individual resistance measurements available")

        # Extract resistance data from actual backend structure
        resistance_data = []
        for measurement in individual_resistances:
            if isinstance(measurement, dict):
                # Use actual field names from backend
                segment_id = measurement.get('segment_id', 0)
                ir_immediate = measurement.get('ir_immediate_ohm')
                ir_10s = measurement.get('ir_10s_ohm')
                ir_30s = measurement.get('ir_30s_ohm')

                # Add multiple time points per segment
                if ir_immediate is not None:
                    resistance_data.append({'time_point': 0, 'resistance': ir_immediate, 'segment': segment_id})
                if ir_10s is not None:
                    resistance_data.append({'time_point': 10, 'resistance': ir_10s, 'segment': segment_id})
                if ir_30s is not None:
                    resistance_data.append({'time_point': 30, 'resistance': ir_30s, 'segment': segment_id})

        if not resistance_data:
            return self._create_error_plot("No valid resistance values found in backend data")

        try:
            # Create plot DataFrame
            df = pd.DataFrame(resistance_data)

            # Create responsive scatter plot
            plot = self._create_hvplot_with_standards(
                df, 'scatter',
                x='time_point', y='resistance',
                title="IR Resistance vs Time",
                xlabel="Time Point (s)", ylabel="Resistance (Î©)",
                color='#F57C00', size=60, alpha=0.8
            )

            # Add trend line if multiple points
            if len(df) > 1:
                df_sorted = df.sort_values('time_point')
                line_plot = self._create_hvplot_with_standards(
                    df_sorted, 'line',
                    x='time_point', y='resistance',
                    color='#F57C00', line_width=2, alpha=0.6
                )
                plot = plot * line_plot

            # Summary info from actual backend
            valid_calcs = summary_stats.get('valid_calculations', 0)
            total_segments = summary_stats.get('total_segments', len(individual_resistances))
            resistance_range = summary_stats.get('resistance_range_ohm', [0, 0])
            avg_resistance = sum(resistance_range) / 2 if len(resistance_range) == 2 else 0

            title_info = pn.pane.Markdown(f"""
            ### âš¡ Resistance vs Time Analysis
            **{len(resistance_data)} measurements â€¢ {valid_calcs}/{total_segments} valid â€¢ Avg: {avg_resistance:.4f} Î©**
            """, margin=(10, 20))

            return self._wrap_plot_in_container(plot, title_info)

        except Exception as e:
            return self._create_error_plot(f"Error creating resistance time plot: {str(e)}")

    def _resistance_distribution_plot(self, data: Dict[str, Any]):
        """Create responsive resistance distribution histogram using actual backend structure."""

        # Use actual backend structure
        individual_resistances = data.get('individual_resistances', [])
        if not individual_resistances:
            return self._create_error_plot("No individual resistance measurements available")

        # Extract all resistance values from backend data
        all_resistance_values = []
        for measurement in individual_resistances:
            if isinstance(measurement, dict):
                ir_immediate = measurement.get('ir_immediate_ohm')
                ir_10s = measurement.get('ir_10s_ohm')
                ir_30s = measurement.get('ir_30s_ohm')

                if ir_immediate is not None:
                    all_resistance_values.append(ir_immediate)
                if ir_10s is not None:
                    all_resistance_values.append(ir_10s)
                if ir_30s is not None:
                    all_resistance_values.append(ir_30s)

        if not all_resistance_values:
            return self._create_error_plot("No valid resistance values for distribution")

        try:
            # Create plot DataFrame
            df = pd.DataFrame({'Resistance': all_resistance_values})

            # Create responsive histogram
            plot = self._create_hvplot_with_standards(
                df, 'hist',
                y='Resistance', bins=15,
                title="Resistance Distribution",
                xlabel="Resistance (Î©)", ylabel="Count",
                color='#2196F3', alpha=0.7
            )

            # Summary info from actual data
            mean_val = sum(all_resistance_values) / len(all_resistance_values)
            std_val = (sum((v - mean_val) ** 2 for v in all_resistance_values) / len(all_resistance_values)) ** 0.5

            title_info = pn.pane.Markdown(f"""
            ### ðŸ“Š Resistance Distribution
            **{len(all_resistance_values)} measurements â€¢ Mean: {mean_val:.4f} Â± {std_val:.4f} Î©**
            """, margin=(10, 20))

            return self._wrap_plot_in_container(plot, title_info)

        except Exception as e:
            return self._create_error_plot(f"Error creating resistance distribution: {str(e)}")

    def _resistance_summary_plot(self, data: Dict[str, Any]):
        """Create responsive resistance analysis summary using actual backend structure."""

        # Use actual backend structure
        individual_resistances = data.get('individual_resistances', [])
        summary_stats = data.get('summary_statistics', {})
        insights = data.get('electrochemical_insights', {})

        if not individual_resistances:
            return self._create_error_plot("No resistance measurements available for summary")

        # Extract summary metrics from actual backend
        total_segments = summary_stats.get('total_segments', 0)
        valid_calculations = summary_stats.get('valid_calculations', 0)
        resistance_range = summary_stats.get('resistance_range_ohm', [0, 0])
        min_resistance = resistance_range[0] if len(resistance_range) > 0 else 0
        max_resistance = resistance_range[1] if len(resistance_range) > 1 else 0
        avg_resistance = (min_resistance + max_resistance) / 2

        try:
            # Create summary metrics DataFrame
            summary_df = pd.DataFrame({
                'Metric': ['Total Segments', 'Valid Calcs', 'Min Resistance', 'Max Resistance'],
                'Value': [total_segments, valid_calculations, min_resistance, max_resistance]
            })

            # Create responsive bar chart
            plot = self._create_hvplot_with_standards(
                summary_df, 'bar',
                x='Metric', y='Value',
                title="Resistance Analysis Summary",
                xlabel="Metric", ylabel="Value",
                color='#FF5722', alpha=0.8
            )

            # Summary info from actual backend insights
            resistance_level = insights.get('resistance_level', 'Unknown')
            consistency = insights.get('consistency', 'Unknown')

            title_info = pn.pane.Markdown(f"""
            ### ðŸ“‹ IR Resistance Summary
            **Quality: {valid_calculations}/{total_segments} measurements â€¢ Range: {min_resistance:.3f}-{max_resistance:.3f} Î©**

            **Insights:** {resistance_level} â€¢ {consistency}
            """, margin=(10, 20))

            return self._wrap_plot_in_container(plot, title_info)

        except Exception as e:
            return self._create_error_plot(f"Error creating resistance summary: {str(e)}")

    # ===== KINETICS ANALYSIS PLOTTING =====

    def _create_kinetics_plot(self, data: Dict[str, Any], settings: Dict[str, Any]):
        """Route to appropriate kinetics visualization."""
        plot_type = self.plot_type_selector.value

        # Extract backend data from main tab wrapper
        backend_data = data.get('backend_results', data)

        if plot_type == "voltage_time":
            return self._kinetics_voltage_time_plot(backend_data)
        elif plot_type == "kinetics_fit":
            return self._kinetics_fit_plot(backend_data)
        elif plot_type == "fit_quality":
            return self._kinetics_quality_plot(backend_data)
        else:
            return self._kinetics_voltage_time_plot(backend_data)  # Default

    def _kinetics_voltage_time_plot(self, data: Dict[str, Any]):
        """Create responsive kinetics voltage progression plot using actual backend structure."""

        # Use actual backend structure
        individual_equilibrium = data.get('individual_equilibrium', [])
        equilibrium_evolution = data.get('equilibrium_evolution', {})

        if not individual_equilibrium:
            return self._create_error_plot("No individual equilibrium measurements available")

        # Extract equilibrium voltages from actual backend structure
        equilibrium_data = []
        for i, measurement in enumerate(individual_equilibrium):
            if isinstance(measurement, dict):
                start_voltage = measurement.get('start_voltage_v')
                end_voltage = measurement.get('end_voltage_v')
                segment_id = measurement.get('segment_id', i)

                if start_voltage is not None:
                    equilibrium_data.append(
                        {'index': i * 2, 'voltage': start_voltage, 'type': 'start', 'segment': segment_id})
                if end_voltage is not None:
                    equilibrium_data.append(
                        {'index': i * 2 + 1, 'voltage': end_voltage, 'type': 'end', 'segment': segment_id})

        if not equilibrium_data:
            return self._create_error_plot("No valid equilibrium voltages for kinetics plot")

        try:
            # Create plot DataFrame
            df = pd.DataFrame(equilibrium_data)

            # Create responsive line plot
            plot = self._create_hvplot_with_standards(
                df, 'line',
                x='index', y='voltage',
                title="Equilibrium Voltage Progression",
                xlabel="Measurement #", ylabel="Equilibrium Voltage (V)",
                color='#2E4057', line_width=3, alpha=0.8
            )

            # Add scatter points with type coloring
            scatter_plot = self._create_hvplot_with_standards(
                df, 'scatter',
                x='index', y='voltage',
                color='type',
                size=80, alpha=0.8
            )

            combined_plot = plot * scatter_plot

            # Summary info from actual backend
            voltage_evolution = equilibrium_evolution.get('voltage_evolution', {})
            initial_v = voltage_evolution.get('initial_v', 0)
            final_v = voltage_evolution.get('final_v', 0)

            title_info = pn.pane.Markdown(f"""
            ### âš—ï¸ Kinetics - Voltage vs Time
            **{len(equilibrium_data)} measurements â€¢ Range: {initial_v:.3f} - {final_v:.3f} V**
            """, margin=(10, 20))

            return self._wrap_plot_in_container(combined_plot, title_info)

        except Exception as e:
            return self._create_error_plot(f"Error creating kinetics voltage plot: {str(e)}")

    def _kinetics_fit_plot(self, data: Dict[str, Any]):
        """Create responsive kinetics fit analysis plot using actual backend structure."""

        # Use actual backend structure: individual_equilibrium list
        individual_equilibrium = data.get('individual_equilibrium', [])
        if not individual_equilibrium:
            return self._create_error_plot("No individual equilibrium data available")

        # Extract time constant data for "fit" analysis
        fit_data = []
        for measurement in individual_equilibrium:
            if isinstance(measurement, dict):
                time_constant_s = measurement.get('time_constant_s')
                r_squared = measurement.get('r_squared')
                segment_id = measurement.get('segment_id', 0)
                technique = measurement.get('technique', 'Unknown')

                if time_constant_s is not None:
                    fit_data.append({
                        'segment': segment_id,
                        'time_constant': time_constant_s,
                        'r_squared': r_squared if r_squared is not None else 0.0,
                        'technique': technique
                    })

        if not fit_data:
            return self._create_error_plot("No valid time constant data for kinetics fit plot")

        try:
            # Create plot DataFrame
            df = pd.DataFrame(fit_data)

            # Create responsive scatter plot showing time constant vs RÂ²
            plot = self._create_hvplot_with_standards(
                df, 'scatter',
                x='time_constant', y='r_squared',
                title="Kinetics Fit - Time Constants vs Quality",
                xlabel="Time Constant Ï„ (s)", ylabel="RÂ² Fit Quality",
                color='#1976D2', size=80, alpha=0.8
            )

            avg_time_constant = sum(d['time_constant'] for d in fit_data) / len(fit_data)
            avg_r_squared = sum(d['r_squared'] for d in fit_data) / len(fit_data)

            title_info = pn.pane.Markdown(f"""
            ### ðŸŽ¯ Kinetics Fit Analysis
            **{len(fit_data)} fits â€¢ Avg Ï„: {avg_time_constant:.2f} s â€¢ Avg RÂ²: {avg_r_squared:.3f}**
            """, margin=(10, 20))

            return self._wrap_plot_in_container(plot, title_info)

        except Exception as e:
            return self._create_error_plot(f"Error creating kinetics fit plot: {str(e)}")

    def _kinetics_quality_plot(self, data: Dict[str, Any]):
        """Create responsive kinetics quality assessment plot using actual backend structure."""

        # Use actual backend structure: diffusion_coefficients dict
        diffusion_coefficients = data.get('diffusion_coefficients', {})
        if not diffusion_coefficients:
            return self._create_error_plot("No diffusion coefficients available")

        # Extract diffusion coefficient data from actual backend structure
        diffusion_data = []
        for segment_id, coefficient in diffusion_coefficients.items():
            if coefficient is not None and isinstance(coefficient, (int, float)):
                diffusion_data.append({
                    'segment_id': segment_id,
                    'diffusion_coefficient': coefficient
                })

        if not diffusion_data:
            return self._create_error_plot("No valid diffusion coefficients for quality plot")

        try:
            # Create plot DataFrame
            df = pd.DataFrame(diffusion_data)

            # Create responsive scatter plot
            plot = self._create_hvplot_with_standards(
                df, 'scatter',
                x='segment_id', y='diffusion_coefficient',
                title="Kinetics Quality - Diffusion Coefficients",
                xlabel="Segment ID", ylabel="D (cmÂ²/s)",
                color='#388E3C', size=80, alpha=0.8
            )

            avg_dc = sum(d['diffusion_coefficient'] for d in diffusion_data) / len(diffusion_data)

            title_info = pn.pane.Markdown(f"""
            ### ðŸ”¬ Kinetics Quality Assessment
            **{len(diffusion_data)} diffusion coefficients â€¢ Avg D: {avg_dc:.2e} cmÂ²/s**
            """, margin=(10, 20))

            return self._wrap_plot_in_container(plot, title_info)

        except Exception as e:
            return self._create_error_plot(f"Error creating kinetics quality plot: {str(e)}")

    # ===== dQ/dV ANALYSIS PLOTTING =====

    def _create_dqdv_plot(self, data: Dict[str, Any], settings: Dict[str, Any]):
        """Route to appropriate dQ/dV visualization."""
        plot_type = self.plot_type_selector.value

        # Extract backend data from main tab wrapper
        backend_data = data.get('backend_results', data)

        if plot_type == "dqdv_voltage":
            return self._dqdv_voltage_plot(backend_data)
        elif plot_type == "peak_analysis":
            return self._dqdv_peak_plot(backend_data)
        elif plot_type == "overlay_comparison":
            return self._dqdv_overlay_plot(backend_data)
        else:
            return self._dqdv_voltage_plot(backend_data)  # Default

    def _dqdv_voltage_plot(self, data: Dict[str, Any]):
        """Create responsive dQ/dV voltage relaxation plot."""

        insights = data.get('electrochemical_insights', {})
        rest_analysis = insights.get('rest_analysis', {})

        if not rest_analysis:
            return self._create_error_plot("No dQ/dV rest analysis data available")

        # Extract relaxation data
        rest_data = []
        for segment_id, segment_data in rest_analysis.items():
            if segment_data and 'voltage_relaxation' in segment_data:
                relaxation = segment_data['voltage_relaxation']
                rest_data.append({
                    'segment': segment_id[:12],
                    'time_constant': relaxation.get('time_constant_s', 0.0),
                    'r_squared': relaxation.get('r_squared', 0.0)
                })

        if not rest_data:
            return self._create_error_plot("No voltage relaxation data for dQ/dV analysis")

        try:
            df = pd.DataFrame(rest_data)

            # Create responsive scatter plot
            plot = self._create_hvplot_with_standards(
                df, 'scatter',
                x='time_constant', y='r_squared',
                title="dQ/dV - Voltage Relaxation Quality",
                xlabel="Time Constant Ï„ (s)", ylabel="Fit Quality RÂ²",
                color='#1976D2', size=80, alpha=0.8
            )

            title_info = pn.pane.Markdown(f"""
            ### âš¡ dQ/dV Voltage Analysis
            **{len(rest_data)} relaxation segments analyzed**
            """, margin=(10, 20))

            return self._wrap_plot_in_container(plot, title_info)

        except Exception as e:
            return self._create_error_plot(f"Error creating dQ/dV voltage plot: {str(e)}")

    def _dqdv_peak_plot(self, data: Dict[str, Any]):
        """Create responsive dQ/dV peak analysis plot."""
        return self._create_error_plot("dQ/dV peak analysis will be implemented in future phases")

    def _dqdv_overlay_plot(self, data: Dict[str, Any]):
        """Create responsive dQ/dV overlay comparison plot."""
        return self._create_error_plot("dQ/dV overlay comparison will be implemented in future phases")

    # ===== PLOT MANAGEMENT =====

    def update_plot_area(self, plot_object):
        """Update the responsive plot area with new plot."""

        self.current_plot = plot_object

        # Clear and update plot area
        self.plot_area.clear()

        if plot_object is None:
            # Responsive placeholder
            placeholder = pn.pane.HTML(
                "<div style='padding: 40px; text-align: center; color: #666;'>No plot to display</div>",
                sizing_mode='stretch_width'
            )
            self.plot_area.append(placeholder)
        else:
            # Add the plot object directly
            self.plot_area.append(plot_object)

        # Enable export when plot available
        self.export_plot_btn.disabled = (plot_object is None)

    def update_available_plots(self, analysis_type: str):
        """Update available plot types for analysis type."""

        # Prevent recursion during updates
        self._updating_plot_options = True

        # Define plot options for each analysis type
        if analysis_type == "basic_statistics":
            plot_options = [
                ("Summary Table", "summary_table"),
                ("Histogram", "histogram"),
                ("Box Plot", "box_plot")
            ]
        elif analysis_type == "resistance_analysis":
            plot_options = [
                ("Resistance vs Time", "resistance_time"),
                ("Resistance Distribution", "resistance_distribution"),
                ("IR Analysis Summary", "resistance_summary")
            ]
        elif analysis_type == "kinetics_analysis":
            plot_options = [
                ("Voltage vs Time", "voltage_time"),
                ("Kinetics Fit", "kinetics_fit"),
                ("Fit Quality", "fit_quality")
            ]
        elif analysis_type == "dqdv_analysis":
            plot_options = [
                ("dQ/dV vs Voltage", "dqdv_voltage"),
                ("Peak Analysis", "peak_analysis"),
                ("Overlay Comparison", "overlay_comparison")
            ]
        else:
            plot_options = [("Summary Table", "summary_table")]

        # Update selector
        self.plot_type_selector.options = plot_options
        self.plot_type_selector.value = plot_options[0][1]

        # Clear recursion flag
        self._updating_plot_options = False

    def _on_plot_type_changed(self, event):
        """Handle plot type selector changes with proper switching."""

        # Skip during option updates
        if hasattr(self, '_updating_plot_options') and self._updating_plot_options:
            return

        print(f"DEBUG: Plot type changed to: {event.new}")

        # Regenerate plot with current data if available
        if (hasattr(self, 'current_analysis_type') and
                hasattr(self, 'current_data') and
                hasattr(self, 'current_settings') and
                self.current_analysis_type and
                self.current_data):

            try:
                # Call the main dispatcher which will route to correct method
                new_plot = self.create_plot(
                    self.current_analysis_type,
                    self.current_data,
                    self.current_settings
                )

                # Update display
                self.update_plot_area(new_plot)

            except Exception as e:
                print(f"Error regenerating plot: {e}")
                self.update_plot_area(self._create_error_plot(f"Error switching plot type: {str(e)}"))

    # ===== UTILITY METHODS =====

    def _create_error_plot(self, message: str):
        """Create responsive error display."""
        return pn.pane.Markdown(f"""
        ### âŒ Plot Error
        **{message}**
        """,
                                styles={'background': '#FFEBEE', 'padding': '20px', 'border-radius': '8px'},
                                margin=(10, 20),
                                sizing_mode='stretch_width'
                                )

    def _create_diagnostic_plot(self, analysis_type: str, analysis_data: Dict[str, Any]):
        """Create responsive diagnostic information display."""

        total = analysis_data.get('total_measurements', 0)
        valid = analysis_data.get('valid_measurements', 0)
        null_count = analysis_data.get('null_measurements', 0)
        invalid_count = analysis_data.get('invalid_measurements', 0)

        return pn.pane.Markdown(f"""
        ### ðŸ” {analysis_type.title()} Analysis Diagnostic

        **Data Status:**
        - Total measurements: **{total}**
        - Valid measurements: **{valid}**
        - Null measurements: **{null_count}**
        - Invalid measurements: **{invalid_count}**

        **Recommendation:** Select groups with relevant technique segments.
        """,
                                styles={'background': '#FFF3CD', 'padding': '20px', 'border-radius': '8px'},
                                margin=(10, 20),
                                sizing_mode='stretch_width'
                                )