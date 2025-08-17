"""
Data Processing Tab for Panel UI.

Provides interface for viewing processed data, monitoring processing status,
and displaying analysis results with plotly visualizations.
"""

import panel as pn
import param
import plotly.graph_objects as go
import plotly.express as px
from plotly_resampler import FigureResampler
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional


class DataProcessingTab(param.Parameterized):
    """
    Data preview and processing interface.
    
    Features:
    - File data preview with plotly-resample for large datasets
    - Processing status monitoring
    - Analysis results display
    - Interactive visualizations
    """
    
    # Parameters for reactive UI
    selected_cell = param.String(default="", doc="Currently selected cell")
    selected_file = param.String(default="", doc="Currently selected file")
    refresh_trigger = param.Number(default=0, doc="Trigger for refreshing data")
    
    def __init__(self, backend_api, **params):
        super().__init__(**params)
        self.api = backend_api
        self.layout = None
        self.cell_file_selector = None
        self.data_preview_pane = None
        self.analysis_results_pane = None
        self.plot_pane = None
        self.setup_layout()
    
    def setup_layout(self):
        """Setup the complete data processing layout."""
        
        # Cell and file selector
        self.cell_file_selector = self._create_cell_file_selector()
        
        # Data preview section
        data_preview_section = self._create_data_preview_section()
        
        # Analysis results section  
        analysis_section = self._create_analysis_section()
        
        # Visualization section
        visualization_section = self._create_visualization_section()
        
        # Main layout
        self.layout = pn.Column(
            "## Data Processing & Analysis",
            "View processed data, analysis results, and interactive visualizations",
            self.cell_file_selector,
            pn.Tabs(
                ("Data Preview", data_preview_section),
                ("Analysis Results", analysis_section),
                ("Visualizations", visualization_section)
            ),
            width=1200
        )
    
    def _create_cell_file_selector(self):
        """Create cell and file selection controls."""
        
        # Cell selector
        cell_selector = self._create_cell_dropdown()
        
        # File selector (depends on selected cell)
        file_selector = pn.widgets.Select(
            name="File",
            options=[],
            width=300
        )
        
        # Processing status indicator
        status_indicator = pn.pane.HTML("", width=400)
        
        # Refresh button
        refresh_btn = pn.widgets.Button(name="Refresh", width=100)
        
        def on_cell_change(event):
            if event.new:
                self.selected_cell = event.new
                self._update_file_selector(file_selector, event.new)
                self.selected_file = ""  # Clear file selection
                self._clear_data_displays()
        
        def on_file_change(event):
            if event.new:
                self.selected_file = event.new
                self._update_status_indicator(status_indicator, event.new)
                self._update_data_displays(event.new)
        
        def refresh_data(event):
            self.refresh_trigger += 1
            if self.selected_cell:
                self._update_file_selector(file_selector, self.selected_cell)
            if self.selected_file:
                self._update_data_displays(self.selected_file)
        
        cell_selector.param.watch(on_cell_change, 'value')
        file_selector.param.watch(on_file_change, 'value')
        refresh_btn.on_click(refresh_data)
        
        return pn.Row(
            cell_selector,
            file_selector,
            refresh_btn,
            status_indicator
        )
    
    def _create_cell_dropdown(self):
        """Create cell selection dropdown."""
        result = self.api.get_all_cells()
        
        if result['success']:
            cells = result['cells']
            if cells:
                cell_options = [cell['cell_name'] for cell in cells]
                return pn.widgets.Select(
                    name="Cell",
                    options=cell_options,
                    width=200
                )
            else:
                return pn.pane.HTML('<p style="color: orange;">No cells available</p>')
        else:
            return pn.pane.HTML(f'<p style="color: red;">Error loading cells: {result["error"]}</p>')
    
    def _update_file_selector(self, file_selector, cell_name):
        """Update file selector options based on selected cell."""
        result = self.api.get_cell_details(cell_name)
        
        if result['success']:
            files = result['cell'].get('files', [])
            if files:
                # Only show processed files
                processed_files = [f for f in files if f['processing_status'] == 'completed']
                file_options = [(f['original_filename'], f['file_id']) for f in processed_files]
                file_selector.options = file_options
            else:
                file_selector.options = []
        else:
            file_selector.options = []
    
    def _update_status_indicator(self, status_indicator, file_id):
        """Update processing status indicator."""
        result = self.api.get_processing_status([file_id])
        
        if result['success'] and result['status_info']:
            status_info = result['status_info'][0]
            status = status_info['status']
            
            if status == 'completed':
                color = 'green'
                icon = '✓'
            elif status == 'processing':
                color = 'orange'
                icon = '⟳'
            elif status == 'failed':
                color = 'red'
                icon = '✗'
            else:
                color = 'gray'
                icon = '?'
            
            html = f"""
            <p style="color: {color};">
                {icon} Status: {status.title()}
                <br>File: {status_info['filename']}
                <br>Upload: {status_info['upload_time']}
            </p>
            """
            
            if status_info.get('error_message'):
                html += f'<p style="color: red;">Error: {status_info["error_message"]}</p>'
            
            status_indicator.object = html
        else:
            status_indicator.object = '<p style="color: gray;">No status information</p>'
    
    def _create_data_preview_section(self):
        """Create data preview section."""
        
        self.data_preview_pane = pn.pane.HTML(
            "<p>Select a cell and file to view data preview</p>",
            width=1150, height=400
        )
        
        return pn.Column(
            "### Data Preview",
            "First 1000 rows of processed data",
            self.data_preview_pane
        )
    
    def _create_analysis_section(self):
        """Create analysis results section."""
        
        self.analysis_results_pane = pn.pane.HTML(
            "<p>Select a cell and file to view analysis results</p>",
            width=1150, height=500
        )
        
        return pn.Column(
            "### Analysis Results",
            "Fundamental analytics results for the selected file",
            self.analysis_results_pane
        )
    
    def _create_visualization_section(self):
        """Create visualization section."""
        
        self.plot_pane = pn.pane.Plotly(
            go.Figure().add_annotation(text="Select a file to view plots", x=0.5, y=0.5),
            width=1150, height=600
        )
        
        # Plot type selector
        plot_selector = pn.widgets.Select(
            name="Plot Type",
            options=[
                "Time Series Overview",
                "Potential vs Time",
                "Current vs Time", 
                "I-V Curve",
                "Nyquist Plot (EIS)",
                "Bode Plot (EIS)",
                "Power vs Time"
            ],
            width=200
        )
        
        def on_plot_change(event):
            if self.selected_file and event.new:
                self._update_plot(event.new)
        
        plot_selector.param.watch(on_plot_change, 'value')
        
        return pn.Column(
            "### Interactive Visualizations",
            plot_selector,
            self.plot_pane
        )
    
    def _update_data_displays(self, file_id):
        """Update all data displays for selected file."""
        self._update_data_preview(file_id)
        self._update_analysis_results(file_id)
        self._update_plot("Time Series Overview")  # Default plot
    
    def _clear_data_displays(self):
        """Clear all data displays."""
        self.data_preview_pane.object = "<p>Select a file to view data preview</p>"
        self.analysis_results_pane.object = "<p>Select a file to view analysis results</p>"
        self.plot_pane.object = go.Figure().add_annotation(text="Select a file to view plots", x=0.5, y=0.5)
    
    def _update_data_preview(self, file_id):
        """Update data preview table."""
        result = self.api.get_file_data_preview(file_id, n_rows=1000)
        
        if result['success']:
            preview_df = result['preview_data']
            stats = result['stats']
            
            # Create preview table
            table_html = f"""
            <div>
                <h4>Data Statistics</h4>
                <p><strong>Total Rows:</strong> {stats['total_rows']:,}</p>
                <p><strong>Total Columns:</strong> {stats['total_columns']}</p>
                <p><strong>Preview Rows:</strong> {stats['preview_rows']}</p>
                <p><strong>Time Range:</strong> {stats['time_range']['min']:.1f} - {stats['time_range']['max']:.1f} seconds</p>
                <p><strong>Techniques:</strong> {', '.join(t for t in stats['techniques'] if t)}</p>
                
                <h4>Data Preview (First {stats['preview_rows']} rows)</h4>
            </div>
            """
            
            # Convert DataFrame to HTML table
            table_html += preview_df.head(50).to_html(
                classes='table table-striped',
                table_id='data-preview-table',
                escape=False,
                float_format=lambda x: f'{x:.6f}' if abs(x) < 1 else f'{x:.3f}'
            )
            
            self.data_preview_pane.object = table_html
        else:
            self.data_preview_pane.object = f'<p style="color: red;">Error loading data preview: {result["error"]}</p>'
    
    def _update_analysis_results(self, file_id):
        """Update analysis results display."""
        result = self.api.get_file_analysis_results(file_id)
        
        if result['success']:
            analysis_results = result['analysis_results']
            
            if analysis_results:
                html = "<h4>Analysis Results by Action</h4>"
                
                for action_id, action_results in analysis_results.items():
                    if hasattr(action_results, 'technique'):
                        technique = action_results.technique
                        results = action_results.results
                        quality = action_results.quality_metrics
                        
                        html += f"""
                        <div style="border: 1px solid #ddd; margin: 10px 0; padding: 10px;">
                            <h5>Action {action_id} - {technique}</h5>
                        """
                        
                        # Display technique-specific results
                        if technique == 'CC':
                            html += f"""
                            <p><strong>Capacity:</strong> {results.get('capacity_ah', 0):.6f} Ah</p>
                            <p><strong>Energy:</strong> {results.get('energy_wh', 0):.6f} Wh</p>
                            <p><strong>Average Voltage:</strong> {results.get('avg_voltage_v', 0):.3f} V</p>
                            <p><strong>Current Stability:</strong> {quality.get('current_stability', 0):.3f}</p>
                            """
                        elif technique == 'REST':
                            html += f"""
                            <p><strong>Equilibrium Voltage:</strong> {results.get('v_equilibrium_v', 0):.3f} V</p>
                            <p><strong>Voltage Drop:</strong> {results.get('v_drop_v', 0):.3f} V</p>
                            <p><strong>Time Constant:</strong> {results.get('time_constant_s', 0):.1f} s</p>
                            <p><strong>R²:</strong> {quality.get('r_squared', 0):.3f}</p>
                            <p><strong>Fit Type:</strong> {results.get('fitting_type', 'unknown')}</p>
                            """
                        elif technique == 'PULSE':
                            html += f"""
                            <p><strong>Resistance:</strong> {results.get('resistance_ohm', 0):.6f} Ω</p>
                            <p><strong>Voltage Drop:</strong> {results.get('voltage_drop_v', 0):.3f} V</p>
                            <p><strong>Duration:</strong> {results.get('pulse_duration_s', 0):.1f} s</p>
                            """
                        elif technique == 'EIS':
                            html += f"""
                            <p><strong>Frequency Range:</strong> {results.get('frequency_min_hz', 0):.2e} - {results.get('frequency_max_hz', 0):.2e} Hz</p>
                            <p><strong>Series Resistance:</strong> {results.get('series_resistance_ohm', 0):.6f} Ω</p>
                            <p><strong>Charge Transfer Resistance:</strong> {results.get('charge_transfer_resistance_ohm', 0):.6f} Ω</p>
                            """
                        
                        html += f"""
                            <p><strong>Data Quality:</strong> {quality.get('data_completeness', 0):.3f}</p>
                            <p><strong>Total Points:</strong> {results.get('total_points', 0)}</p>
                        </div>
                        """
                
                self.analysis_results_pane.object = html
            else:
                self.analysis_results_pane.object = "<p>No analysis results available for this file</p>"
        else:
            self.analysis_results_pane.object = f'<p style="color: red;">Error loading analysis results: {result["error"]}</p>'
    
    def _update_plot(self, plot_type):
        """Update plot based on selected type."""
        if not self.selected_file:
            return
        
        result = self.api.get_file_data_preview(self.selected_file, n_rows=10000)  # More data for plots
        
        if not result['success']:
            self.plot_pane.object = go.Figure().add_annotation(
                text=f"Error loading data: {result['error']}", x=0.5, y=0.5
            )
            return
        
        df = result['preview_data']
        
        try:
            if plot_type == "Time Series Overview":
                fig = self._create_time_series_overview(df)
            elif plot_type == "Potential vs Time":
                fig = self._create_potential_time_plot(df)
            elif plot_type == "Current vs Time":
                fig = self._create_current_time_plot(df)
            elif plot_type == "I-V Curve":
                fig = self._create_iv_curve_plot(df)
            elif plot_type == "Nyquist Plot (EIS)":
                fig = self._create_nyquist_plot(df)
            elif plot_type == "Bode Plot (EIS)":
                fig = self._create_bode_plot(df)
            elif plot_type == "Power vs Time":
                fig = self._create_power_time_plot(df)
            else:
                fig = go.Figure().add_annotation(text="Plot type not implemented", x=0.5, y=0.5)
            
            self.plot_pane.object = fig
            
        except Exception as e:
            self.plot_pane.object = go.Figure().add_annotation(
                text=f"Plot error: {str(e)}", x=0.5, y=0.5
            )
    
    def _create_time_series_overview(self, df):
        """Create time series overview with subplots."""
        from plotly.subplots import make_subplots
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Potential vs Time', 'Current vs Time', 'Power vs Time', 'Impedance'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Potential vs Time
        if 'potential_v' in df.columns and 'time_s' in df.columns:
            fig.add_scatter(x=df['time_s'], y=df['potential_v'], name='Potential',
                          line=dict(width=1), row=1, col=1)
        
        # Current vs Time
        if 'current_a' in df.columns and 'time_s' in df.columns:
            fig.add_scatter(x=df['time_s'], y=df['current_a'], name='Current',
                          line=dict(width=1, color='orange'), row=1, col=2)
        
        # Power vs Time
        if 'power_w' in df.columns and 'time_s' in df.columns:
            fig.add_scatter(x=df['time_s'], y=df['power_w'], name='Power',
                          line=dict(width=1, color='red'), row=2, col=1)
        
        # Impedance (if EIS data present)
        if 'impedance_real_ohm' in df.columns and 'impedance_imag_ohm' in df.columns:
            eis_data = df[(df['impedance_real_ohm'].notna()) & (df['impedance_imag_ohm'].notna())]
            if not eis_data.empty:
                fig.add_scatter(x=eis_data['impedance_real_ohm'], y=-eis_data['impedance_imag_ohm'],
                              mode='markers', name='Nyquist', marker=dict(size=3), row=2, col=2)
        
        fig.update_layout(height=600, title_text="Time Series Overview")
        return fig
    
    def _create_potential_time_plot(self, df):
        """Create potential vs time plot."""
        if 'potential_v' not in df.columns or 'time_s' not in df.columns:
            return go.Figure().add_annotation(text="No potential data available", x=0.5, y=0.5)
        
        # Use FigureResampler for large datasets
        fig = FigureResampler()
        fig.add_scatter(x=df['time_s'], y=df['potential_v'], name='Potential (V)')
        fig.update_layout(
            title="Potential vs Time",
            xaxis_title="Time (s)",
            yaxis_title="Potential (V)"
        )
        return fig
    
    def _create_current_time_plot(self, df):
        """Create current vs time plot."""
        if 'current_a' not in df.columns or 'time_s' not in df.columns:
            return go.Figure().add_annotation(text="No current data available", x=0.5, y=0.5)
        
        fig = FigureResampler()
        fig.add_scatter(x=df['time_s'], y=df['current_a'], name='Current (A)', line=dict(color='orange'))
        fig.update_layout(
            title="Current vs Time",
            xaxis_title="Time (s)",
            yaxis_title="Current (A)"
        )
        return fig
    
    def _create_iv_curve_plot(self, df):
        """Create I-V curve plot."""
        if 'potential_v' not in df.columns or 'current_a' not in df.columns:
            return go.Figure().add_annotation(text="No I-V data available", x=0.5, y=0.5)
        
        fig = go.Figure()
        fig.add_scatter(x=df['potential_v'], y=df['current_a'], mode='markers',
                       marker=dict(size=2, opacity=0.6), name='I-V Curve')
        fig.update_layout(
            title="Current vs Potential (I-V Curve)",
            xaxis_title="Potential (V)",
            yaxis_title="Current (A)"
        )
        return fig
    
    def _create_nyquist_plot(self, df):
        """Create Nyquist plot for EIS data."""
        if 'impedance_real_ohm' not in df.columns or 'impedance_imag_ohm' not in df.columns:
            return go.Figure().add_annotation(text="No EIS data available", x=0.5, y=0.5)
        
        # Filter EIS data
        eis_data = df[(df['impedance_real_ohm'].notna()) & (df['impedance_imag_ohm'].notna())]
        if eis_data.empty:
            return go.Figure().add_annotation(text="No valid EIS data found", x=0.5, y=0.5)
        
        fig = go.Figure()
        fig.add_scatter(x=eis_data['impedance_real_ohm'], y=-eis_data['impedance_imag_ohm'],
                       mode='markers', marker=dict(size=4), name='Nyquist')
        fig.update_layout(
            title="Nyquist Plot",
            xaxis_title="Z' (Ω)",
            yaxis_title="-Z'' (Ω)",
            yaxis=dict(scaleanchor="x", scaleratio=1)
        )
        return fig
    
    def _create_bode_plot(self, df):
        """Create Bode plot for EIS data."""
        if 'frequency_hz' not in df.columns or 'impedance_mag_ohm' not in df.columns:
            return go.Figure().add_annotation(text="No EIS data available", x=0.5, y=0.5)
        
        # Filter EIS data
        eis_data = df[(df['frequency_hz'].notna()) & (df['frequency_hz'] > 0)]
        if eis_data.empty:
            return go.Figure().add_annotation(text="No valid EIS data found", x=0.5, y=0.5)
        
        from plotly.subplots import make_subplots
        
        fig = make_subplots(rows=2, cols=1,
                           subplot_titles=('Magnitude', 'Phase'),
                           shared_xaxes=True)
        
        # Magnitude plot
        fig.add_scatter(x=eis_data['frequency_hz'], y=eis_data['impedance_mag_ohm'],
                       name='|Z|', row=1, col=1)
        
        # Phase plot
        if 'impedance_phase_deg' in df.columns:
            fig.add_scatter(x=eis_data['frequency_hz'], y=eis_data['impedance_phase_deg'],
                           name='Phase', row=2, col=1)
        
        fig.update_xaxes(type="log", title_text="Frequency (Hz)", row=2, col=1)
        fig.update_yaxes(type="log", title_text="|Z| (Ω)", row=1, col=1)
        fig.update_yaxes(title_text="Phase (°)", row=2, col=1)
        fig.update_layout(height=600, title_text="Bode Plot")
        
        return fig
    
    def _create_power_time_plot(self, df):
        """Create power vs time plot."""
        if 'power_w' not in df.columns or 'time_s' not in df.columns:
            return go.Figure().add_annotation(text="No power data available", x=0.5, y=0.5)
        
        fig = FigureResampler()
        fig.add_scatter(x=df['time_s'], y=df['power_w'], name='Power (W)', line=dict(color='red'))
        fig.update_layout(
            title="Power vs Time",
            xaxis_title="Time (s)",
            yaxis_title="Power (W)"
        )
        return fig