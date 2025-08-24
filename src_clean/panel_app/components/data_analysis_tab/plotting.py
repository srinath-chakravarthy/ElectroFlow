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

# Registry imports for dynamic plotting
from src_clean.analysis.registry import get_analysis_registry

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

        # Get analysis registry for dynamic plotting
        self.registry = get_analysis_registry()
        
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
        """Create plot using registry-driven generic DataFrame plotting."""

        try:
            # Store current data for plot type switching
            self.current_analysis_type = analysis_type
            self.current_data = data
            self.current_settings = settings

            # Handle errors
            if data.get("error"):
                return pn.pane.Markdown(f"**Error:** {data['error']}")

            # Get current plot type from selector
            plot_type_raw = self.plot_type_select.value
            if isinstance(plot_type_raw, tuple) and len(plot_type_raw) > 1:
                plot_type = plot_type_raw[1]  # Get the value part of (label, value) tuple
            else:
                plot_type = str(plot_type_raw)
            
            print(f"✅ Creating registry-driven plot: {analysis_type}, plot_type: {plot_type}")
            
            # Use registry-driven generic plotting
            return self._create_registry_driven_plot(analysis_type, data, settings, plot_type)

        except Exception as e:
            print(f"❌ Plot creation error: {e}")
            return pn.pane.Markdown(f"**Plot Error:** {str(e)}")

    def _create_registry_driven_plot(self, analysis_type: str, data: Dict[str, Any], settings: Dict[str, Any], plot_type: str):
        """Create plot using registry-driven generic DataFrame approach."""
        
        try:
            # Get analysis configuration from registry
            analysis_config = self.registry.get_analysis(analysis_type)
            if not analysis_config:
                return pn.pane.Markdown(f"**Unknown analysis type:** {analysis_type}")
            
            # Extract DataFrame from analysis results
            plot_df = self._extract_dataframe_for_plotting(analysis_type, data, plot_type)
            if plot_df is None or plot_df.empty:
                return pn.pane.Markdown(f"**No data available for plotting {plot_type}**")
            
            # Create plot using generic DataFrame plotting
            plot = self._create_generic_dataframe_plot(plot_df, analysis_type, plot_type, settings)
            
            print(f"✅ Created registry-driven plot for {analysis_type}: {plot_type}")
            return plot
            
        except Exception as e:
            print(f"❌ Registry-driven plot creation failed: {e}")
            # Fallback to legacy plotting if available
            return self._create_fallback_plot(analysis_type, data, settings, plot_type)
    
    def _extract_dataframe_for_plotting(self, analysis_type: str, data: Dict[str, Any], plot_type: str) -> Optional[pd.DataFrame]:
        """Extract appropriate DataFrame for plotting based on analysis type and plot type."""
        
        try:
            # Handle different analysis result structures
            if analysis_type == "basic_statistics":
                return self._extract_basic_statistics_dataframe(data, plot_type)
            elif analysis_type == "resistance_analysis":
                return self._extract_resistance_dataframe(data, plot_type)
            elif analysis_type == "kinetics_analysis":
                return self._extract_kinetics_dataframe(data, plot_type)
            elif analysis_type == "equilibrium_analysis":
                return self._extract_equilibrium_dataframe(data, plot_type)
            elif analysis_type == "current_decay_analysis":
                return self._extract_current_decay_dataframe(data, plot_type)
            elif analysis_type == "dqdv_analysis":
                return self._extract_dqdv_dataframe(data, plot_type)
            else:
                # Generic fallback - try to extract segments data
                segments = data.get("segments", [])
                if segments:
                    return pd.DataFrame(segments)
                return None
                
        except Exception as e:
            print(f"⚠️ Error extracting DataFrame for {analysis_type}.{plot_type}: {e}")
            return None
    
    def _extract_basic_statistics_dataframe(self, data: Dict[str, Any], plot_type: str) -> Optional[pd.DataFrame]:
        """Extract DataFrame for basic statistics plotting."""
        
        segments = data.get("segments", [])
        if not segments:
            return None
        
        df = pd.DataFrame(segments)
        
        if plot_type == "technique_count":
            # Group by technique and count
            technique_counts = df.groupby('fundamental_technique').size().reset_index()
            technique_counts.columns = ['technique', 'count']
            return technique_counts
            
        elif plot_type == "duration_analysis":
            # Return duration data with techniques
            if 'duration_s' in df.columns and 'fundamental_technique' in df.columns:
                duration_df = df[df['duration_s'].notna() & (df['duration_s'] > 0)]
                return duration_df[['duration_s', 'fundamental_technique']]
                
        return df
    
    def _extract_resistance_dataframe(self, data: Dict[str, Any], plot_type: str) -> Optional[pd.DataFrame]:
        """Extract DataFrame for resistance analysis plotting."""
        
        resistance_data = data.get('resistance_data', [])
        if not resistance_data:
            return None
        
        # Convert resistance measurements to DataFrame format
        plot_data = []
        
        for measurement in resistance_data:
            if not isinstance(measurement, dict):
                continue
                
            segment_id = measurement.get('segment_id')
            ir_immediate = measurement.get('ir_immediate_ohm')
            ir_10s = measurement.get('ir_10s_ohm')
            ir_30s = measurement.get('ir_30s_ohm')
            start_voltage = measurement.get('start_potential_v')
            time = measurement.get('start_time_s', 0)
            
            # Add different resistance types as separate rows
            if ir_immediate is not None:
                plot_data.append({
                    'segment_id': segment_id,
                    'resistance': ir_immediate,
                    'resistance_type': 'Immediate',
                    'voltage': start_voltage,
                    'time': time
                })
            if ir_10s is not None:
                plot_data.append({
                    'segment_id': segment_id,
                    'resistance': ir_10s,
                    'resistance_type': '10s',
                    'voltage': start_voltage,
                    'time': time + 10
                })
            if ir_30s is not None:
                plot_data.append({
                    'segment_id': segment_id,
                    'resistance': ir_30s,
                    'resistance_type': '30s',
                    'voltage': start_voltage,
                    'time': time + 30
                })
        
        return pd.DataFrame(plot_data) if plot_data else None
    
    def _extract_kinetics_dataframe(self, data: Dict[str, Any], plot_type: str) -> Optional[pd.DataFrame]:
        """Extract DataFrame for kinetics analysis plotting."""
        
        kinetics_data = data.get('kinetics_data', [])
        if not kinetics_data:
            return None
        
        # Convert kinetics measurements to DataFrame format
        plot_data = []
        
        for i, measurement in enumerate(kinetics_data):
            if not isinstance(measurement, dict):
                continue
                
            segment_id = measurement.get('segment_id')
            equilibrium_value = measurement.get('equilibrium_value')
            fit_type = measurement.get('fit_type', 'exponential')
            r_squared = measurement.get('r_squared', 0.0)
            rmse = measurement.get('rmse')
            time_constant = measurement.get('time_constant')
            amplitude = measurement.get('amplitude')
            variable_type = measurement.get('variable_type', 'voltage')
            
            # Only process voltage measurements
            if variable_type == 'voltage':
                plot_data.append({
                    'segment_id': segment_id,
                    'sequence': i + 1,
                    'equilibrium_voltage': equilibrium_value,
                    'fit_type': 'Exponential' if fit_type == 'exponential' else 'sqrt(t)',
                    'r_squared': r_squared,
                    'rmse': rmse,
                    'time_constant': time_constant,
                    'amplitude': amplitude,
                    'normalized_error': rmse / abs(equilibrium_value) if rmse and equilibrium_value else None
                })
        
        return pd.DataFrame(plot_data) if plot_data else None
    
    def _extract_equilibrium_dataframe(self, data: Dict[str, Any], plot_type: str) -> Optional[pd.DataFrame]:
        """Extract DataFrame for equilibrium analysis plotting."""
        
        equilibrium_data = data.get('equilibrium_data', [])
        if not equilibrium_data:
            return None
        
        return pd.DataFrame(equilibrium_data)
    
    def _extract_current_decay_dataframe(self, data: Dict[str, Any], plot_type: str) -> Optional[pd.DataFrame]:
        """Extract DataFrame for current decay analysis plotting."""
        
        decay_data = data.get('current_decay_data', [])
        if not decay_data:
            return None
        
        return pd.DataFrame(decay_data)
    
    def _extract_dqdv_dataframe(self, data: Dict[str, Any], plot_type: str) -> Optional[pd.DataFrame]:
        """Extract DataFrame for dQ/dV analysis plotting."""
        
        # dQ/dV not implemented yet
        return None
    
    def _create_generic_dataframe_plot(self, df: pd.DataFrame, analysis_type: str, plot_type: str, settings: Dict[str, Any]):
        """Create plot using generic DataFrame plotting based on plot type."""
        
        try:
            # Define generic plotting configurations
            plot_configs = {
                # Basic Statistics plots
                "technique_count": {
                    "plot_func": "bar",
                    "x": "technique",
                    "y": "count",
                    "title": "Technique Count Analysis",
                    "xlabel": "Technique",
                    "ylabel": "Count"
                },
                "duration_analysis": {
                    "plot_func": "hist",
                    "y": "duration_s",
                    "by": "fundamental_technique",
                    "title": "Duration Analysis by Technique",
                    "xlabel": "Duration (s)",
                    "ylabel": "Count",
                    "bins": 15,
                    "alpha": 0.7
                },
                # Resistance plots
                "temporal_resistance": {
                    "plot_func": "line",
                    "x": "time",
                    "y": "resistance",
                    "by": "resistance_type",
                    "title": "Temporal Resistance Evolution",
                    "xlabel": "Time (s)",
                    "ylabel": "Resistance (Ω)"
                },
                "resistance_voltage": {
                    "plot_func": "scatter",
                    "x": "voltage",
                    "y": "resistance",
                    "by": "resistance_type",
                    "title": "Resistance vs Voltage Correlation",
                    "xlabel": "Starting Voltage (V)",
                    "ylabel": "Resistance (Ω)",
                    "size": 80,
                    "alpha": 0.8
                },
                "resistance_distribution": {
                    "plot_func": "hist",
                    "y": "resistance",
                    "by": "resistance_type",
                    "title": "Resistance Distribution Analysis",
                    "xlabel": "Resistance (Ω)",
                    "ylabel": "Count",
                    "bins": 20,
                    "alpha": 0.8
                },
                # Kinetics plots
                "voltage_relaxation": {
                    "plot_func": "line",
                    "x": "sequence",
                    "y": "equilibrium_voltage",
                    "by": "fit_type",
                    "title": "Voltage Relaxation Evolution",
                    "xlabel": "Measurement Sequence",
                    "ylabel": "Equilibrium Voltage (V)"
                },
                "relaxation_stability": {
                    "plot_func": "scatter",
                    "x": "sequence",
                    "y": "normalized_error",
                    "by": "fit_type",
                    "title": "Relaxation Stability (Normalized RMSE)",
                    "xlabel": "Measurement Sequence",
                    "ylabel": "RMSE / |V∞|",
                    "size": 50,
                    "alpha": 0.7
                }
            }
            
            # Get plot configuration
            config = plot_configs.get(plot_type)
            if not config:
                return pn.pane.Markdown(f"**Plot configuration not found for {plot_type}**")
            
            # Extract configuration parameters
            plot_func = config.pop("plot_func")
            
            # Get the hvplot method
            if plot_func == "bar":
                hvplot_method = df.hvplot.bar
            elif plot_func == "hist":
                hvplot_method = df.hvplot.hist
            elif plot_func == "line":
                hvplot_method = df.hvplot.line
            elif plot_func == "scatter":
                hvplot_method = df.hvplot.scatter
            else:
                return pn.pane.Markdown(f"**Unknown plot function: {plot_func}**")
            
            # Add standard tools
            config["tools"] = ['pan', 'wheel_zoom', 'box_zoom', 'reset', 'save']
            config["width"] = 700
            config["height"] = 400
            
            # Create the plot
            plot = hvplot_method(**config)
            
            print(f"✅ Created generic DataFrame plot: {analysis_type}.{plot_type}")
            return plot
            
        except Exception as e:
            print(f"❌ Generic DataFrame plot creation failed: {e}")
            return pn.pane.Markdown(f"**Generic plot error:** {str(e)}")
    
    def _create_fallback_plot(self, analysis_type: str, data: Dict[str, Any], settings: Dict[str, Any], plot_type: str):
        """Fallback plotting if registry-driven approach fails."""
        
        # Simple fallback based on analysis type
        if analysis_type == "basic_statistics":
            segments = data.get("segments", [])
            if segments:
                df = pd.DataFrame(segments)
                if 'fundamental_technique' in df.columns:
                    technique_counts = df.groupby('fundamental_technique').size().reset_index()
                    technique_counts.columns = ['Technique', 'Count']
                    return technique_counts.hvplot.bar(
                        x='Technique', y='Count',
                        title=f'Basic Statistics - {plot_type}',
                        tools=['pan', 'wheel_zoom', 'box_zoom', 'reset', 'save']
                    )
        
        return pn.pane.Markdown(f"**Fallback plot for {analysis_type}.{plot_type}**\n\nRegistry-driven plotting failed, and no suitable fallback available.")

    def _legacy_basic_stats_technique_count(self, data: Dict[str, Any]):
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

    def _legacy_basic_stats_duration_analysis(self, data: Dict[str, Any]):
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

    def _legacy_create_resistance_plot(self, data: Dict[str, Any], settings: Dict[str, Any]):
        """Route to appropriate resistance visualization based on plot type selector."""
        
        # Get current plot type from selector - handle tuple format
        plot_type_raw = self.plot_type_select.value
        if isinstance(plot_type_raw, tuple) and len(plot_type_raw) > 1:
            plot_type = plot_type_raw[1]  # Get the value part of (label, value) tuple
        else:
            plot_type = str(plot_type_raw)
            
        print(f"DEBUG: Creating resistance plot, type: {plot_type}")

        # Route to specific plot method
        if plot_type == "temporal_resistance":
            return self._resistance_temporal(data)
        elif plot_type == "resistance_voltage":
            return self._resistance_vs_voltage(data)
        elif plot_type == "resistance_distribution":
            return self._resistance_distribution(data)
        else:
            return self._resistance_temporal(data)  # Default

    def _resistance_temporal(self, data: Dict[str, Any]):
        """Create temporal resistance evolution plot (All 3 resistances vs time)."""

        # Get backend data - handle both direct data and nested structure
        backend_data = data.get('data', data)
        individual_resistances = backend_data.get('individual_resistances', [])
        core_segments_data = backend_data.get('core_segment_data', [])
        
        if not individual_resistances:
            return pn.pane.Markdown("**No resistance data available for temporal analysis**")

        print(f"DEBUG: Temporal resistance plot with {len(individual_resistances)} measurements")

        try:
            # Extract resistance data for all 3 types over time
            resistance_data = []
            i = 0
            for measurement, segment_data in zip(individual_resistances,core_segments_data):
                i += 1
                if isinstance(measurement, dict):
                    segment_id = measurement.get('segment_id', i)
                    
                    # Get time information - use start_time_s if available, otherwise sequence
                    time_value = segment_data.get('start_time_s', 0)
                    
                    # Get all 3 resistance values
                    ir_immediate = measurement.get('ir_immediate_ohm')
                    ir_10s = measurement.get('ir_10s_ohm') 
                    ir_30s = measurement.get('ir_30s_ohm')
                    
                    # Add each resistance type as separate point
                    if ir_immediate is not None:
                        resistance_data.append({
                            'time': time_value,
                            'resistance': ir_immediate, 
                            'type': 'Immediate IR',
                            'segment_id': segment_id
                        })
                    if ir_10s is not None:
                        resistance_data.append({
                            'time': time_value + 10,  # 10 seconds after start
                            'resistance': ir_10s, 
                            'type': '10s IR',
                            'segment_id': segment_id
                        })
                    if ir_30s is not None:
                        resistance_data.append({
                            'time': time_value + 30,  # 30 seconds after start
                            'resistance': ir_30s, 
                            'type': '30s IR',
                            'segment_id': segment_id
                        })

            if not resistance_data:
                return pn.pane.Markdown("**No valid resistance measurements found**")

            # Create DataFrame and plot
            df = pd.DataFrame(resistance_data)
            
            # Create line plot colored by resistance type  
            plot = df.hvplot.line(
                x='time', 
                y='resistance',
                by='type',
                title='TEMPORAL RESISTANCE EVOLUTION',
                xlabel='Time (s)',
                ylabel='Resistance (Ω)',
                width=700,
                height=400,
                tools=['pan', 'wheel_zoom', 'box_zoom', 'reset', 'save']
            )

            return plot

        except Exception as e:
            print(f"DEBUG: Error creating temporal resistance plot: {e}")
            return pn.pane.Markdown(f"**Error creating plot:** {str(e)}")

    def _resistance_vs_voltage(self, data: Dict[str, Any]):
        """Create resistance vs voltage plot (All 3 resistances vs starting voltage)."""

        # Get backend data
        backend_data = data.get('data', data)
        individual_resistances = backend_data.get('individual_resistances', [])
        core_segments_data = backend_data.get('core_segment_data', [])
        
        if not individual_resistances:
            return pn.pane.Markdown("**No resistance data available for voltage analysis**")

        print(f"DEBUG: Resistance vs voltage plot with {len(individual_resistances)} measurements")

        try:
            # Extract resistance vs voltage data
            resistance_data = []
            for measurement, segment_data in zip(individual_resistances, core_segments_data):
                if isinstance(measurement, dict):
                    start_voltage = segment_data.get('start_potential_v')
                    if start_voltage is None:
                        continue
                        
                    # Get all 3 resistance values
                    ir_immediate = measurement.get('ir_immediate_ohm')
                    ir_10s = measurement.get('ir_10s_ohm')
                    ir_30s = measurement.get('ir_30s_ohm')
                    
                    # Add each resistance type vs voltage
                    if ir_immediate is not None:
                        resistance_data.append({
                            'voltage': start_voltage, 
                            'resistance': ir_immediate, 
                            'type': 'Immediate'
                        })
                    if ir_10s is not None:
                        resistance_data.append({
                            'voltage': start_voltage, 
                            'resistance': ir_10s, 
                            'type': '10s'
                        })
                    if ir_30s is not None:
                        resistance_data.append({
                            'voltage': start_voltage, 
                            'resistance': ir_30s, 
                            'type': '30s'
                        })

            if not resistance_data:
                return pn.pane.Markdown("**No valid resistance vs voltage data found**")

            # Create DataFrame and plot
            df = pd.DataFrame(resistance_data)
            
            # Create scatter plot colored by resistance type
            plot = df.hvplot.scatter(
                x='voltage', 
                y='resistance',
                by='type',
                title='RESISTANCE vs VOLTAGE CORRELATION',
                xlabel='Starting Voltage (V)',
                ylabel='Resistance (Ω)',
                size=80,
                alpha=0.8,
                width=700,
                height=400,
                tools=['pan', 'wheel_zoom', 'box_zoom', 'reset', 'save']
            )

            return plot

        except Exception as e:
            print(f"DEBUG: Error creating resistance vs voltage plot: {e}")
            return pn.pane.Markdown(f"**Error creating plot:** {str(e)}")

    def _resistance_distribution(self, data: Dict[str, Any]):
        """Create resistance distribution histogram for all 3 resistance types."""

        # Get backend data
        backend_data = data.get('data', data)
        individual_resistances = backend_data.get('individual_resistances', [])
        
        if not individual_resistances:
            return pn.pane.Markdown("**No resistance data available for distribution analysis**")

        print(f"DEBUG: Resistance distribution plot with {len(individual_resistances)} measurements")

        try:
            # Extract all resistance values
            resistance_data = []
            for measurement in individual_resistances:
                if isinstance(measurement, dict):
                    # Get all 3 resistance values
                    ir_immediate = measurement.get('ir_immediate_ohm')
                    ir_10s = measurement.get('ir_10s_ohm')
                    ir_30s = measurement.get('ir_30s_ohm')
                    
                    # Add each resistance type
                    if ir_immediate is not None:
                        resistance_data.append({'resistance': ir_immediate, 'type': 'Immediate'})
                    if ir_10s is not None:
                        resistance_data.append({'resistance': ir_10s, 'type': '10s'})
                    if ir_30s is not None:
                        resistance_data.append({'resistance': ir_30s, 'type': '30s'})

            if not resistance_data:
                return pn.pane.Markdown("**No valid resistance values found**")

            # Create DataFrame and plot
            df = pd.DataFrame(resistance_data)
            
            # Create histogram by resistance type
            plot = df.hvplot.hist(
                y='resistance',
                by='type',
                bins=20,
                title='RESISTANCE DISTRIBUTION ANALYSIS',
                xlabel='Resistance (Ω)',
                ylabel='Count',
                alpha=0.8,
                width=700,
                height=400,
                tools=['pan', 'wheel_zoom', 'box_zoom', 'reset', 'save']
            )

            return plot

        except Exception as e:
            print(f"DEBUG: Error creating resistance distribution plot: {e}")
            return pn.pane.Markdown(f"**Error creating plot:** {str(e)}")

    def _legacy_create_kinetics_plot(self, data: Dict[str, Any], settings: Dict[str, Any]):
        """Route to appropriate kinetics visualization based on plot type selector."""
        
        # Get current plot type from selector - handle tuple format
        plot_type_raw = self.plot_type_select.value
        if isinstance(plot_type_raw, tuple) and len(plot_type_raw) > 1:
            plot_type = plot_type_raw[1]  # Get the value part of (label, value) tuple
        else:
            plot_type = str(plot_type_raw)
            
        print(f"DEBUG: Creating kinetics plot, type: {plot_type}")

        # Route to specific plot method
        if plot_type == "voltage_relaxation":
            return self._kinetics_voltage_relaxation(data)
        elif plot_type == "relaxation_stability":
            return self._kinetics_relaxation_stability(data)
        elif plot_type == "voltage_kinetics":
            return self._kinetics_voltage_kinetics(data)
        elif plot_type == "kinetics_quality":
            return self._kinetics_quality_comparison(data)
        else:
            return self._kinetics_voltage_relaxation(data)  # Default

    def _kinetics_voltage_relaxation(self, data: Dict[str, Any]):
        """Create voltage relaxation evolution plot (End voltages vs time)."""

        # Get backend data - handle both direct data and nested structure
        backend_data = data.get('data', data)
        individual_kinetics = backend_data.get('individual_kinetics', [])
        core_segments_data = backend_data.get('core_segment_data', [])
        
        if not individual_kinetics:
            return pn.pane.Markdown("**No kinetics data available for voltage relaxation analysis**")

        print(f"DEBUG: Voltage relaxation plot with {len(individual_kinetics)} measurements")

        try:
            # Extract voltage relaxation data
            relaxation_data = []
            i = 0
            for measurement, segment_data in zip(individual_kinetics, core_segments_data):
                i += 1
                if isinstance(measurement, dict):
                    # Get voltage from RelaxationKinetics structure
                    equilibrium_voltage = measurement.get('equilibrium_value')
                    fit_type = measurement.get('fit_type', 'exponential')
                    variable_type = measurement.get('variable_type', 'voltage')
                    
                    # Only process voltage measurements
                    if variable_type == 'voltage' and equilibrium_voltage is not None:
                        fit_type_label = 'Exponential' if fit_type == 'exponential' else 'sqrt(t)'
                        
                        relaxation_data.append({
                            'sequence': i,
                            'voltage': equilibrium_voltage,
                            'fit_type': fit_type_label,
                            'segment_id': measurement.get('segment_id', i)
                        })

            if not relaxation_data:
                return pn.pane.Markdown("**No valid voltage relaxation data found**")

            # Create DataFrame and plot
            df = pd.DataFrame(relaxation_data)
            
            # Create line plot colored by fit type
            plot = df.hvplot.line(
                x='sequence', 
                y='voltage',
                by='fit_type',
                title='Voltage Relaxation Evolution',
                xlabel='Measurement Sequence',
                ylabel='Equilibrium Voltage (V)',
                tools=['pan', 'wheel_zoom', 'box_zoom', 'reset', 'save']
            )

            return plot

        except Exception as e:
            print(f"DEBUG: Error creating voltage relaxation plot: {e}")
            return pn.pane.Markdown(f"**Error creating plot:** {str(e)}")

    def _kinetics_relaxation_stability(self, data: Dict[str, Any]):
        """Create relaxation stability plot (Normalized RMSE vs time)."""

        # Get backend data
        backend_data = data.get('data', data)
        individual_kinetics = backend_data.get('individual_kinetics', [])
        core_segments_data = backend_data.get('core_segment_data', [])
        
        if not individual_kinetics:
            return pn.pane.Markdown("**No kinetics data available for stability analysis**")

        print(f"DEBUG: Relaxation stability plot with {len(individual_kinetics)} measurements")

        try:
            # Extract normalized error data
            stability_data = []
            i = 0
            for measurement, segment_data in zip(individual_kinetics, core_segments_data):
                i += 1
                if isinstance(measurement, dict):
                    # Get stability data from RelaxationKinetics structure
                    rmse = measurement.get('rmse')
                    equilibrium_value = measurement.get('equilibrium_value')
                    fit_type = measurement.get('fit_type', 'exponential')
                    variable_type = measurement.get('variable_type', 'voltage')
                    
                    # Only process voltage measurements with valid data
                    if (variable_type == 'voltage' and rmse is not None and 
                        equilibrium_value is not None and equilibrium_value != 0):
                        normalized_error = rmse / abs(equilibrium_value)
                        fit_type_label = 'Exponential' if fit_type == 'exponential' else 'sqrt(t)'
                        
                        stability_data.append({
                            'sequence': i,
                            'normalized_error': normalized_error,
                            'fit_type': fit_type_label
                        })

            if not stability_data:
                return pn.pane.Markdown("**No valid stability data found**")

            # Create DataFrame and plot
            df = pd.DataFrame(stability_data)
            
            # Create scatter plot colored by fit type
            plot = df.hvplot.scatter(
                x='sequence', 
                y='normalized_error',
                by='fit_type',
                title='Relaxation Stability (Normalized RMSE)',
                xlabel='Measurement Sequence',
                ylabel='RMSE / |V∞|',
                size=50,
                alpha=0.7,
                tools=['pan', 'wheel_zoom', 'box_zoom', 'reset', 'save']
            )

            return plot

        except Exception as e:
            print(f"DEBUG: Error creating stability plot: {e}")
            return pn.pane.Markdown(f"**Error creating plot:** {str(e)}")

    def _kinetics_voltage_kinetics(self, data: Dict[str, Any]):
        """Create voltage-dependent kinetics plot (Time constants vs REST voltage)."""

        # Get backend data
        backend_data = data.get('data', data)
        individual_kinetics = backend_data.get('individual_kinetics', [])
        core_segments_data = backend_data.get('core_segment_data', [])
        
        if not individual_kinetics:
            return pn.pane.Markdown("**No kinetics data available for voltage kinetics analysis**")

        print(f"DEBUG: Voltage kinetics plot with {len(individual_kinetics)} measurements")

        try:
            # Extract time constant vs voltage data
            kinetics_data = []
            for measurement, segment_data in zip(individual_kinetics, core_segments_data):
                if isinstance(measurement, dict):
                    start_voltage = segment_data.get('start_potential_v')
                    if start_voltage is None:
                        continue
                    
                    # Get kinetics data from RelaxationKinetics structure
                    fit_type = measurement.get('fit_type', 'exponential')
                    variable_type = measurement.get('variable_type', 'voltage')
                    r_squared = measurement.get('r_squared', 0.0)
                    
                    # Only process voltage measurements
                    if variable_type == 'voltage':
                        if fit_type == 'exponential':
                            time_constant = measurement.get('time_constant')
                            if time_constant is not None:
                                kinetics_data.append({
                                    'voltage': start_voltage,
                                    'time_constant': time_constant,
                                    'fit_type': 'Exponential',
                                    'r_squared': r_squared
                                })
                        elif fit_type == 'sqrt':
                            amplitude = measurement.get('amplitude')
                            if amplitude is not None:
                                # Convert amplitude to pseudo-time constant (inverse relationship)
                                pseudo_tau = 1 / (abs(amplitude) + 1e-6)  # Avoid division by zero
                                kinetics_data.append({
                                    'voltage': start_voltage,
                                    'time_constant': pseudo_tau,
                                    'fit_type': 'sqrt(t)',
                                    'r_squared': r_squared
                                })

            if not kinetics_data:
                return pn.pane.Markdown("**No valid voltage kinetics data found**")

            # Create DataFrame and plot
            df = pd.DataFrame(kinetics_data)
            
            # Create scatter plot sized by fit quality
            plot = df.hvplot.scatter(
                x='voltage', 
                y='time_constant',
                by='fit_type',
                size='r_squared',
                title='Voltage-Dependent Kinetics',
                xlabel='REST Voltage (V)',
                ylabel='Time Constant / Kinetics Parameter',
                alpha=0.7,
                tools=['pan', 'wheel_zoom', 'box_zoom', 'reset', 'save']
            )

            return plot

        except Exception as e:
            print(f"DEBUG: Error creating voltage kinetics plot: {e}")
            return pn.pane.Markdown(f"**Error creating plot:** {str(e)}")

    def _kinetics_quality_comparison(self, data: Dict[str, Any]):
        """Create kinetics quality comparison (R² exponential vs sqrt(t))."""

        # Get backend data
        backend_data = data.get('data', data)
        individual_kinetics = backend_data.get('individual_kinetics', [])
        core_segments_data = backend_data.get('core_segment_data', [])
        
        if not individual_kinetics:
            return pn.pane.Markdown("**No kinetics data available for quality comparison**")

        print(f"DEBUG: Kinetics quality plot with {len(individual_kinetics)} measurements")

        try:
            # Extract R² values for comparison
            quality_data = []
            # Group measurements by segment_id to compare different fit types
            measurement_groups = {}
            for measurement, segment_data in zip(individual_kinetics, core_segments_data):
                if isinstance(measurement, dict):
                    segment_id = measurement.get('segment_id', 'unknown')
                    fit_type = measurement.get('fit_type', 'exponential')
                    r_squared = measurement.get('r_squared', 0.0)
                    
                    if segment_id not in measurement_groups:
                        measurement_groups[segment_id] = {}
                    measurement_groups[segment_id][fit_type] = r_squared
            
            # Extract paired R² values for comparison
            for segment_id, fits in measurement_groups.items():
                exp_r2 = fits.get('exponential')
                sqrt_r2 = fits.get('sqrt')
                
                # Only add if we have both fit types for comparison
                if exp_r2 is not None and sqrt_r2 is not None:
                    quality_data.append({
                        'exponential_r2': exp_r2,
                        'sqrt_r2': sqrt_r2,
                        'segment_id': segment_id
                    })

            if not quality_data:
                return pn.pane.Markdown("**No paired fit quality data found**")

            # Create DataFrame and plot
            df = pd.DataFrame(quality_data)
            
            # Create scatter plot comparing R² values
            plot = df.hvplot.scatter(
                x='exponential_r2', 
                y='sqrt_r2',
                title='Kinetics Fit Quality Comparison',
                xlabel='Exponential Fit R²',
                ylabel='sqrt(t) Fit R²',
                size=60,
                alpha=0.7,
                color='purple',
                tools=['pan', 'wheel_zoom', 'box_zoom', 'reset', 'save']
            )
            
            # Add diagonal reference line
            ref_line = pd.DataFrame({'x': [0, 1], 'y': [0, 1]})
            line_plot = ref_line.hvplot.line(
                x='x', y='y',
                color='red', 
                line_dash='dashed',
                alpha=0.5
            )
            
            combined_plot = plot * line_plot

            return combined_plot

        except Exception as e:
            print(f"DEBUG: Error creating quality comparison plot: {e}")
            return pn.pane.Markdown(f"**Error creating plot:** {str(e)}")

    def _legacy_create_dqdv_plot(self, data: Dict[str, Any], settings: Dict[str, Any]):
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
        """Update available plot types based on analysis type using registry."""
        
        try:
            # Get analysis configuration from registry
            analysis_config = self.registry.get_analysis(analysis_type)
            
            if analysis_config and hasattr(analysis_config, 'available_plots'):
                # Use registry-defined plot types
                registry_plots = analysis_config.available_plots
                options = [(plot.value.replace('_', ' ').title(), plot.value) for plot in registry_plots]
                
                if not options:
                    # Fallback to generic options
                    options = [("Default View", "default")]
                    
                print(f"✅ Using registry plot options for {analysis_type}: {[opt[1] for opt in options]}")
                
            else:
                # Fallback to predefined plot options
                plot_options = {
                    "basic_statistics": [
                        ("Technique Count", "technique_count"),
                        ("Duration Analysis", "duration_analysis")
                    ],
                    "resistance_analysis": [
                        ("Temporal Resistance", "temporal_resistance"),
                        ("Resistance vs Voltage", "resistance_voltage"),
                        ("Resistance Distribution", "resistance_distribution")
                    ],
                    "kinetics_analysis": [
                        ("Voltage Relaxation", "voltage_relaxation"),
                        ("Relaxation Stability", "relaxation_stability")
                    ],
                    "equilibrium_analysis": [
                        ("Equilibrium Evolution", "equilibrium_evolution"),
                        ("Stability Analysis", "stability_analysis")
                    ],
                    "current_decay_analysis": [
                        ("Decay Kinetics", "decay_kinetics"),
                        ("Decay Distribution", "decay_distribution")
                    ],
                    "dqdv_analysis": [
                        ("dQ/dV Curves", "dqdv_curves"),
                        ("Peak Analysis", "peak_analysis")
                    ]
                }
                
                options = plot_options.get(analysis_type, [("Default", "default")])
                print(f"⚠️ Using fallback plot options for {analysis_type}: {[opt[1] for opt in options]}")
            
            self.plot_type_select.options = options
            if options:
                self.plot_type_select.value = options[0][1]
                
        except Exception as e:
            print(f"❌ Error updating plot options for {analysis_type}: {e}")
            # Ultimate fallback
            self.plot_type_select.options = [("Default", "default")]
            self.plot_type_select.value = "default"

    def _on_plot_type_changed(self, event):
        """Handle plot type selector changes - regenerate plot with new type."""
        
        print(f"DEBUG: Plot type changed to: {event.new}")
        print(f"DEBUG: Current analysis type: {self.current_analysis_type}")
        print(f"DEBUG: Has current data: {self.current_data is not None}")
        
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