"""
Plot Templates for Battery Data Analyzer.

Provides templated plotting functions for different analysis types.
Supports manual plotting workflow with predefined plot templates.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
import polars as pl
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


class PlotTemplates:
    """
    Template-based plotting system for battery data analysis.
    
    Provides predefined plot templates for common analysis tasks:
    - Voltage vs Time
    - Current vs Time
    - Power vs Time
    - Voltage vs Current (I-V curves)
    - Capacity vs Voltage
    - Nyquist Plot (EIS)
    - Bode Plot (EIS)
    - Group Comparison plots
    """
    
    def __init__(self):
        """Initialize plot templates."""
        self.default_colors = px.colors.qualitative.Set1
        self.default_width = 800
        self.default_height = 500
    
    def create_voltage_time_plot(self, data: pl.DataFrame, title: str = "Voltage vs Time", 
                                group_by: Optional[str] = None) -> go.Figure:
        """
        Create voltage vs time plot.
        
        Args:
            data: DataFrame with time_s and potential_v columns
            title: Plot title
            group_by: Column to group traces by (e.g., 'technique_id')
            
        Returns:
            Plotly Figure object
        """
        try:
            fig = go.Figure()
            
            if group_by and group_by in data.columns:
                # Multiple traces grouped by specified column
                groups = data.get_column(group_by).unique().to_list()
                for i, group in enumerate(groups):
                    group_data = data.filter(pl.col(group_by) == group)
                    if not group_data.is_empty():
                        fig.add_trace(go.Scatter(
                            x=group_data.get_column('time_s').to_list(),
                            y=group_data.get_column('potential_v').to_list(),
                            mode='lines',
                            name=str(group),
                            line=dict(color=self.default_colors[i % len(self.default_colors)], width=2)
                        ))
            else:
                # Single trace
                fig.add_trace(go.Scatter(
                    x=data.get_column('time_s').to_list(),
                    y=data.get_column('potential_v').to_list(),
                    mode='lines',
                    name='Voltage',
                    line=dict(color='blue', width=2)
                ))
            
            fig.update_layout(
                title=title,
                xaxis_title="Time (s)",
                yaxis_title="Potential (V)",
                width=self.default_width,
                height=self.default_height,
                template='plotly_white'
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating voltage-time plot: {e}")
            return self._create_error_figure(f"Plot error: {str(e)}")
    
    def create_current_time_plot(self, data: pl.DataFrame, title: str = "Current vs Time",
                                group_by: Optional[str] = None) -> go.Figure:
        """
        Create current vs time plot.
        
        Args:
            data: DataFrame with time_s and current_a columns
            title: Plot title
            group_by: Column to group traces by
            
        Returns:
            Plotly Figure object
        """
        try:
            fig = go.Figure()
            
            if group_by and group_by in data.columns:
                # Multiple traces
                groups = data.get_column(group_by).unique().to_list()
                for i, group in enumerate(groups):
                    group_data = data.filter(pl.col(group_by) == group)
                    if not group_data.is_empty():
                        fig.add_trace(go.Scatter(
                            x=group_data.get_column('time_s').to_list(),
                            y=group_data.get_column('current_a').to_list(),
                            mode='lines',
                            name=str(group),
                            line=dict(color=self.default_colors[i % len(self.default_colors)], width=2)
                        ))
            else:
                # Single trace
                fig.add_trace(go.Scatter(
                    x=data.get_column('time_s').to_list(),
                    y=data.get_column('current_a').to_list(),
                    mode='lines',
                    name='Current',
                    line=dict(color='orange', width=2)
                ))
            
            fig.update_layout(
                title=title,
                xaxis_title="Time (s)",
                yaxis_title="Current (A)",
                width=self.default_width,
                height=self.default_height,
                template='plotly_white'
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating current-time plot: {e}")
            return self._create_error_figure(f"Plot error: {str(e)}")
    
    def create_power_time_plot(self, data: pl.DataFrame, title: str = "Power vs Time",
                              group_by: Optional[str] = None) -> go.Figure:
        """
        Create power vs time plot.
        
        Args:
            data: DataFrame with time_s and power_w columns
            title: Plot title
            group_by: Column to group traces by
            
        Returns:
            Plotly Figure object
        """
        try:
            # Calculate power if not available
            plot_data = data.clone()
            if 'power_w' not in data.columns:
                if 'potential_v' in data.columns and 'current_a' in data.columns:
                    plot_data = plot_data.with_columns([
                        (pl.col('potential_v') * pl.col('current_a')).alias('power_w')
                    ])
                else:
                    return self._create_error_figure("Cannot calculate power: missing voltage or current data")
            
            fig = go.Figure()
            
            if group_by and group_by in plot_data.columns:
                # Multiple traces
                groups = plot_data.get_column(group_by).unique().to_list()
                for i, group in enumerate(groups):
                    group_data = plot_data.filter(pl.col(group_by) == group)
                    if not group_data.is_empty():
                        fig.add_trace(go.Scatter(
                            x=group_data.get_column('time_s').to_list(),
                            y=group_data.get_column('power_w').to_list(),
                            mode='lines',
                            name=str(group),
                            line=dict(color=self.default_colors[i % len(self.default_colors)], width=2)
                        ))
            else:
                # Single trace
                fig.add_trace(go.Scatter(
                    x=plot_data.get_column('time_s').to_list(),
                    y=plot_data.get_column('power_w').to_list(),
                    mode='lines',
                    name='Power',
                    line=dict(color='red', width=2)
                ))
            
            fig.update_layout(
                title=title,
                xaxis_title="Time (s)",
                yaxis_title="Power (W)",
                width=self.default_width,
                height=self.default_height,
                template='plotly_white'
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating power-time plot: {e}")
            return self._create_error_figure(f"Plot error: {str(e)}")
    
    def create_iv_curve_plot(self, data: pl.DataFrame, title: str = "I-V Curve",
                            group_by: Optional[str] = None) -> go.Figure:
        """
        Create current vs voltage (I-V) curve plot.
        
        Args:
            data: DataFrame with potential_v and current_a columns
            title: Plot title
            group_by: Column to group traces by
            
        Returns:
            Plotly Figure object
        """
        try:
            fig = go.Figure()
            
            if group_by and group_by in data.columns:
                # Multiple traces
                groups = data.get_column(group_by).unique().to_list()
                for i, group in enumerate(groups):
                    group_data = data.filter(pl.col(group_by) == group)
                    if not group_data.is_empty():
                        fig.add_trace(go.Scatter(
                            x=group_data.get_column('potential_v').to_list(),
                            y=group_data.get_column('current_a').to_list(),
                            mode='markers',
                            name=str(group),
                            marker=dict(
                                color=self.default_colors[i % len(self.default_colors)],
                                size=4,
                                opacity=0.7
                            )
                        ))
            else:
                # Single trace
                fig.add_trace(go.Scatter(
                    x=data.get_column('potential_v').to_list(),
                    y=data.get_column('current_a').to_list(),
                    mode='markers',
                    name='I-V Curve',
                    marker=dict(color='blue', size=4, opacity=0.7)
                ))
            
            fig.update_layout(
                title=title,
                xaxis_title="Potential (V)",
                yaxis_title="Current (A)",
                width=self.default_width,
                height=self.default_height,
                template='plotly_white'
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating I-V curve plot: {e}")
            return self._create_error_figure(f"Plot error: {str(e)}")
    
    def create_capacity_voltage_plot(self, data: pl.DataFrame, title: str = "Capacity vs Voltage",
                                    group_by: Optional[str] = None) -> go.Figure:
        """
        Create capacity vs voltage plot.
        
        Args:
            data: DataFrame with potential_v and charge_capacity_ah columns
            title: Plot title
            group_by: Column to group traces by
            
        Returns:
            Plotly Figure object
        """
        try:
            if 'charge_capacity_ah' not in data.columns:
                return self._create_error_figure("No capacity data available")
            
            fig = go.Figure()
            
            if group_by and group_by in data.columns:
                # Multiple traces
                groups = data.get_column(group_by).unique().to_list()
                for i, group in enumerate(groups):
                    group_data = data.filter(pl.col(group_by) == group)
                    if not group_data.is_empty():
                        fig.add_trace(go.Scatter(
                            x=group_data.get_column('potential_v').to_list(),
                            y=group_data.get_column('charge_capacity_ah').to_list(),
                            mode='lines+markers',
                            name=str(group),
                            line=dict(color=self.default_colors[i % len(self.default_colors)], width=2),
                            marker=dict(size=4)
                        ))
            else:
                # Single trace
                fig.add_trace(go.Scatter(
                    x=data.get_column('potential_v').to_list(),
                    y=data.get_column('charge_capacity_ah').to_list(),
                    mode='lines+markers',
                    name='Capacity',
                    line=dict(color='green', width=2),
                    marker=dict(size=4)
                ))
            
            fig.update_layout(
                title=title,
                xaxis_title="Potential (V)",
                yaxis_title="Capacity (Ah)",
                width=self.default_width,
                height=self.default_height,
                template='plotly_white'
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating capacity-voltage plot: {e}")
            return self._create_error_figure(f"Plot error: {str(e)}")
    
    def create_nyquist_plot(self, data: pl.DataFrame, title: str = "Nyquist Plot",
                           group_by: Optional[str] = None) -> go.Figure:
        """
        Create Nyquist plot for EIS data.
        
        Args:
            data: DataFrame with impedance_real_ohm and impedance_imag_ohm columns
            title: Plot title
            group_by: Column to group traces by
            
        Returns:
            Plotly Figure object
        """
        try:
            # Filter EIS data
            eis_data = data.filter(
                (pl.col('impedance_real_ohm').is_not_null()) & 
                (pl.col('impedance_imag_ohm').is_not_null())
            )
            
            if eis_data.is_empty():
                return self._create_error_figure("No EIS data available")
            
            fig = go.Figure()
            
            if group_by and group_by in eis_data.columns:
                # Multiple traces
                groups = eis_data.get_column(group_by).unique().to_list()
                for i, group in enumerate(groups):
                    group_data = eis_data.filter(pl.col(group_by) == group)
                    if not group_data.is_empty():
                        fig.add_trace(go.Scatter(
                            x=group_data.get_column('impedance_real_ohm').to_list(),
                            y=(-group_data.get_column('impedance_imag_ohm')).to_list(),
                            mode='markers',
                            name=str(group),
                            marker=dict(
                                color=self.default_colors[i % len(self.default_colors)],
                                size=5
                            )
                        ))
            else:
                # Single trace
                fig.add_trace(go.Scatter(
                    x=eis_data.get_column('impedance_real_ohm').to_list(),
                    y=(-eis_data.get_column('impedance_imag_ohm')).to_list(),
                    mode='markers',
                    name='Nyquist',
                    marker=dict(color='blue', size=5)
                ))
            
            fig.update_layout(
                title=title,
                xaxis_title="Z' (Ω)",
                yaxis_title="-Z'' (Ω)",
                width=self.default_width,
                height=self.default_height,
                template='plotly_white',
                yaxis=dict(scaleanchor="x", scaleratio=1)  # Equal aspect ratio
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating Nyquist plot: {e}")
            return self._create_error_figure(f"Plot error: {str(e)}")
    
    def create_bode_plot(self, data: pl.DataFrame, title: str = "Bode Plot",
                        group_by: Optional[str] = None) -> go.Figure:
        """
        Create Bode plot for EIS data.
        
        Args:
            data: DataFrame with frequency_hz, impedance_mag_ohm, impedance_phase_deg columns
            title: Plot title
            group_by: Column to group traces by
            
        Returns:
            Plotly Figure object
        """
        try:
            # Filter EIS data
            eis_data = data.filter(
                (pl.col('frequency_hz').is_not_null()) & 
                (pl.col('frequency_hz') > 0)
            )
            
            if eis_data.is_empty():
                return self._create_error_figure("No EIS frequency data available")
            
            # Calculate magnitude if not available
            if 'impedance_mag_ohm' not in eis_data.columns:
                if 'impedance_real_ohm' in eis_data.columns and 'impedance_imag_ohm' in eis_data.columns:
                    eis_data = eis_data.with_columns([
                        ((pl.col('impedance_real_ohm')**2 + pl.col('impedance_imag_ohm')**2)**0.5).alias('impedance_mag_ohm')
                    ])
                else:
                    return self._create_error_figure("Cannot calculate impedance magnitude")
            
            # Calculate phase if not available
            if 'impedance_phase_deg' not in eis_data.columns:
                if 'impedance_real_ohm' in eis_data.columns and 'impedance_imag_ohm' in eis_data.columns:
                    eis_data = eis_data.with_columns([
                        (pl.col('impedance_imag_ohm').arctan2(pl.col('impedance_real_ohm')) * 180 / np.pi).alias('impedance_phase_deg')
                    ])
                else:
                    return self._create_error_figure("Cannot calculate impedance phase")
            
            # Create subplot
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Magnitude', 'Phase'),
                shared_xaxes=True,
                vertical_spacing=0.1
            )
            
            if group_by and group_by in eis_data.columns:
                # Multiple traces
                groups = eis_data.get_column(group_by).unique().to_list()
                for i, group in enumerate(groups):
                    group_data = eis_data.filter(pl.col(group_by) == group)
                    if not group_data.is_empty():
                        color = self.default_colors[i % len(self.default_colors)]
                        
                        # Magnitude
                        fig.add_trace(go.Scatter(
                            x=group_data.get_column('frequency_hz').to_list(),
                            y=group_data.get_column('impedance_mag_ohm').to_list(),
                            mode='markers',
                            name=f'{group} |Z|',
                            marker=dict(color=color, size=4),
                            showlegend=True
                        ), row=1, col=1)
                        
                        # Phase
                        fig.add_trace(go.Scatter(
                            x=group_data.get_column('frequency_hz').to_list(),
                            y=group_data.get_column('impedance_phase_deg').to_list(),
                            mode='markers',
                            name=f'{group} Phase',
                            marker=dict(color=color, size=4),
                            showlegend=False
                        ), row=2, col=1)
            else:
                # Single trace
                # Magnitude
                fig.add_trace(go.Scatter(
                    x=eis_data.get_column('frequency_hz').to_list(),
                    y=eis_data.get_column('impedance_mag_ohm').to_list(),
                    mode='markers',
                    name='|Z|',
                    marker=dict(color='blue', size=4)
                ), row=1, col=1)
                
                # Phase
                fig.add_trace(go.Scatter(
                    x=eis_data.get_column('frequency_hz').to_list(),
                    y=eis_data.get_column('impedance_phase_deg').to_list(),
                    mode='markers',
                    name='Phase',
                    marker=dict(color='red', size=4),
                    showlegend=False
                ), row=2, col=1)
            
            # Update layout
            fig.update_xaxes(type="log", title_text="Frequency (Hz)", row=2, col=1)
            fig.update_yaxes(type="log", title_text="|Z| (Ω)", row=1, col=1)
            fig.update_yaxes(title_text="Phase (°)", row=2, col=1)
            
            fig.update_layout(
                title=title,
                width=self.default_width,
                height=600,  # Taller for subplots
                template='plotly_white'
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating Bode plot: {e}")
            return self._create_error_figure(f"Plot error: {str(e)}")
    
    def create_group_comparison_plot(self, data: pl.DataFrame, plot_type: str, 
                                   title: str = "Group Comparison") -> go.Figure:
        """
        Create comparison plot for multiple groups.
        
        Args:
            data: DataFrame with group data
            plot_type: Type of comparison plot
            title: Plot title
            
        Returns:
            Plotly Figure object
        """
        try:
            if plot_type == "voltage_time":
                return self.create_voltage_time_plot(data, title, group_by='technique_id')
            elif plot_type == "current_time":
                return self.create_current_time_plot(data, title, group_by='technique_id')
            elif plot_type == "power_time":
                return self.create_power_time_plot(data, title, group_by='technique_id')
            elif plot_type == "iv_curve":
                return self.create_iv_curve_plot(data, title, group_by='technique_id')
            elif plot_type == "capacity_voltage":
                return self.create_capacity_voltage_plot(data, title, group_by='technique_id')
            elif plot_type == "nyquist":
                return self.create_nyquist_plot(data, title, group_by='technique_id')
            elif plot_type == "bode":
                return self.create_bode_plot(data, title, group_by='technique_id')
            else:
                return self._create_error_figure(f"Unknown plot type: {plot_type}")
                
        except Exception as e:
            logger.error(f"Error creating group comparison plot: {e}")
            return self._create_error_figure(f"Plot error: {str(e)}")
    
    def create_multi_panel_overview(self, data: pl.DataFrame, title: str = "Multi-Panel Overview") -> go.Figure:
        """
        Create multi-panel overview plot with key measurements.
        
        Args:
            data: DataFrame with measurement data
            title: Plot title
            
        Returns:
            Plotly Figure object with multiple subplots
        """
        try:
            # Create 2x2 subplot grid
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Voltage vs Time', 'Current vs Time', 'Power vs Time', 'I-V Curve'),
                vertical_spacing=0.1,
                horizontal_spacing=0.1
            )
            
            # Voltage vs Time
            if 'potential_v' in data.columns and 'time_s' in data.columns:
                fig.add_trace(go.Scatter(
                    x=data.get_column('time_s').to_list(),
                    y=data.get_column('potential_v').to_list(),
                    mode='lines',
                    name='Voltage',
                    line=dict(color='blue', width=1),
                    showlegend=False
                ), row=1, col=1)
            
            # Current vs Time
            if 'current_a' in data.columns and 'time_s' in data.columns:
                fig.add_trace(go.Scatter(
                    x=data.get_column('time_s').to_list(),
                    y=data.get_column('current_a').to_list(),
                    mode='lines',
                    name='Current',
                    line=dict(color='orange', width=1),
                    showlegend=False
                ), row=1, col=2)
            
            # Power vs Time
            if 'power_w' in data.columns and 'time_s' in data.columns:
                fig.add_trace(go.Scatter(
                    x=data.get_column('time_s').to_list(),
                    y=data.get_column('power_w').to_list(),
                    mode='lines',
                    name='Power',
                    line=dict(color='red', width=1),
                    showlegend=False
                ), row=2, col=1)
            elif 'potential_v' in data.columns and 'current_a' in data.columns:
                # Calculate power
                power = (data.get_column('potential_v') * data.get_column('current_a')).to_list()
                fig.add_trace(go.Scatter(
                    x=data.get_column('time_s').to_list(),
                    y=power,
                    mode='lines',
                    name='Power (calculated)',
                    line=dict(color='red', width=1),
                    showlegend=False
                ), row=2, col=1)
            
            # I-V Curve
            if 'potential_v' in data.columns and 'current_a' in data.columns:
                fig.add_trace(go.Scatter(
                    x=data.get_column('potential_v').to_list(),
                    y=data.get_column('current_a').to_list(),
                    mode='markers',
                    name='I-V',
                    marker=dict(color='green', size=2, opacity=0.6),
                    showlegend=False
                ), row=2, col=2)
            
            # Update axes labels
            fig.update_xaxes(title_text="Time (s)", row=1, col=1)
            fig.update_xaxes(title_text="Time (s)", row=1, col=2)
            fig.update_xaxes(title_text="Time (s)", row=2, col=1)
            fig.update_xaxes(title_text="Potential (V)", row=2, col=2)
            
            fig.update_yaxes(title_text="Potential (V)", row=1, col=1)
            fig.update_yaxes(title_text="Current (A)", row=1, col=2)
            fig.update_yaxes(title_text="Power (W)", row=2, col=1)
            fig.update_yaxes(title_text="Current (A)", row=2, col=2)
            
            fig.update_layout(
                title=title,
                width=900,
                height=600,
                template='plotly_white'
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating multi-panel overview: {e}")
            return self._create_error_figure(f"Plot error: {str(e)}")
    
    def _create_error_figure(self, error_message: str) -> go.Figure:
        """Create error figure with message."""
        fig = go.Figure()
        fig.add_annotation(
            text=error_message,
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(size=16, color="red")
        )
        fig.update_layout(
            title="Plot Error",
            width=self.default_width,
            height=self.default_height,
            template='plotly_white'
        )
        return fig