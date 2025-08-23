"""
Tab 3 Data Analysis - Plotting & Visualization Management  

Handles all plotting functionality and plot controls.
Generates analysis-specific visualizations.

Architecture: Plot generation dispatcher with analysis-specific methods.
"""

import panel as pn
import holoviews as hv
import pandas as pd
from typing import Dict, List, Any, Optional


class PlottingManager:
    """
    Handles all plotting functionality and plot controls.
    Generates analysis-specific visualizations.
    
    Phase 1: Basic plot area placeholder and simple controls
    Phase 2: Basic plotting with backend data
    Phase 3: Analysis-specific plot generation
    Phase 4: Advanced plot controls and export
    """
    
    def __init__(self, api):
        self.api = api
        
        # Create plot controls and area
        self._create_plot_area()
        self._create_plot_controls()
        
        # Current state
        self.current_plot = None
        self.current_analysis = "basic_statistics"
        self.available_plot_types = ["summary_table"]
    
    def _create_plot_area(self):
        """Create main plot area."""
        
        # Initialize with placeholder
        self.plot_area = pn.pane.HTML(
            """
            <div style='border: 2px dashed #E0E0E0; border-radius: 8px; 
                        padding: 40px; text-align: center; color: #666;
                        background: #FAFAFA; min-height: 300px;
                        display: flex; align-items: center; justify-content: center;'>
                <div>
                    <div style='font-size: 48px; margin-bottom: 10px;'>📊</div>
                    <div style='font-size: 18px; margin-bottom: 5px;'>Ready for Analysis</div>
                    <div style='font-size: 14px;'>Select groups and click "Analyze" to generate plots</div>
                </div>
            </div>
            """,
            height=500,
            width=700
        )
        
    def get_plot_area(self):
        """Return the main plot area."""
        return self.plot_area
    
    def _create_plot_controls(self):
        """Create plot controls interface."""
        
        # Basic plot controls (always visible)
        self.plot_type_selector = pn.widgets.Select(
            name="Plot Type",
            options=[("Summary Table", "summary_table")],
            value="summary_table",
            width=200
        )
        
        self.export_plot_btn = pn.widgets.Button(
            name="💾 Export Plot",
            button_type="default",
            width=120,
            disabled=True  # Disabled until plot is generated
        )
        
        self.plot_settings_btn = pn.widgets.Button(
            name="⚙️ Settings",
            button_type="default",
            width=80,
            disabled=True  # Phase 1: disabled
        )
        
        # Basic controls row
        self.basic_controls = pn.Row(
            self.plot_type_selector,
            pn.Spacer(width=20),
            self.export_plot_btn,
            self.plot_settings_btn,
            margin=(10, 0)
        )
        
        # Advanced controls (placeholder for future phases)
        self.advanced_controls = pn.Column(
            pn.pane.HTML("""
            <div style='color: #666; font-style: italic; padding: 10px;'>
                Advanced plot controls will be available in future phases...
            </div>
            """),
            visible=False    # Hidden in Phase 1
        )
        
        # Complete plot controls
        self.plot_controls = pn.Column(
            self.basic_controls,
            self.advanced_controls,
            width=500
        )
    
    def get_plot_controls(self):
        """Return the plot controls panel."""
        return self.plot_controls
    
    # ===== PLOT GENERATION =====
    
    def create_plot(self, analysis_type: str, data: Dict[str, Any], settings: Dict[str, Any]) -> Any:
        """Main plot generation dispatcher."""
        
        try:
            # CRITICAL FIX: Update available plot types for this analysis
            self.update_available_plots(analysis_type)
            print(f"Updated plot types for {analysis_type}: {self.plot_type_selector.options}")
            print(f"Selected plot type: {self.plot_type_selector.value}")
            
            if analysis_type == "basic_statistics":
                return self._create_basic_statistics_plot(data, settings)
            elif analysis_type == "resistance_analysis":
                return self._create_resistance_plot(data, settings)
            elif analysis_type == "kinetics_analysis":
                return self._create_kinetics_plot(data, settings)
            elif analysis_type == "dqdv_analysis":
                return self._create_dqdv_plot(data, settings)
            else:
                return self._create_empty_plot(f"Unknown analysis type: {analysis_type}")
                
        except Exception as e:
            print(f"Plot creation error for {analysis_type}: {e}")
            import traceback
            traceback.print_exc()
            return self._create_empty_plot(f"Error creating plot: {str(e)}")
    
    def _create_basic_statistics_plot(self, data: Dict[str, Any], settings: Dict[str, Any]):
        """Create basic statistics visualization - Phase 3: Enhanced with real data."""
        
        if not data:
            return self._create_empty_plot("No data available for basic statistics")
        
        # Phase 3: Enhanced visualization with real backend data
        
        # Get current plot type
        plot_type = self.plot_type_selector.value
        
        if plot_type == "summary_table":
            return self._create_statistics_table(data)
        elif plot_type == "histogram":
            return self._create_statistics_histogram(data)  
        elif plot_type == "box_plot":
            return self._create_statistics_boxplot(data)
        else:
            return self._create_statistics_table(data)  # Default
    
    def _create_statistics_table(self, data: Dict[str, Any]):
        """Create interactive bar chart with error bars for statistics."""
        
        # Extract real values with fallback
        duration_mean = data.get('duration_mean', 0)
        duration_std = data.get('duration_std', 0) 
        voltage_mean = data.get('voltage_mean', 0)
        voltage_std = data.get('voltage_std', 0)
        capacity_mean = data.get('capacity_mean', 0)
        capacity_std = data.get('capacity_std', 0)
        total_segments = data.get('total_segments', 0)
        total_groups = data.get('total_groups', 0)
        
        # Check if we have real data or fallback
        has_real_data = 'backend_results' in data
        data_source = "Real electrochemical analysis" if has_real_data else "Simulated data"
        
        # Prepare data for hvplot bar chart with error bars
        metrics_data = {
            'Metric': ['Duration', 'Start Voltage', 'Capacity'],
            'Mean': [duration_mean, voltage_mean, capacity_mean],
            'Std': [duration_std, voltage_std, capacity_std],
            'Units': ['seconds', 'V', 'Ah'],
            'Error_Lower': [duration_mean - duration_std, voltage_mean - voltage_std, capacity_mean - capacity_std],
            'Error_Upper': [duration_mean + duration_std, voltage_mean + voltage_std, capacity_mean + capacity_std]
        }
        
        df = pd.DataFrame(metrics_data)
        
        # Create separate plots for each metric (they have different scales)
        try:
            # Duration plot
            duration_plot = df[df.Metric == 'Duration'].hvplot.bar(
                x='Metric', y='Mean', 
                title="Duration Statistics",
                ylabel="Time (seconds)",
                color='#2E4057',
                width=200, height=200,
                toolbar=False
            ).opts(
                show_legend=False,
                fontsize={'title': 12, 'labels': 10}
            )
            
            # Voltage plot  
            voltage_plot = df[df.Metric == 'Start Voltage'].hvplot.bar(
                x='Metric', y='Mean',
                title="Start Voltage Statistics", 
                ylabel="Voltage (V)",
                color='#1976D2',
                width=200, height=200,
                toolbar=False
            ).opts(
                show_legend=False,
                fontsize={'title': 12, 'labels': 10}
            )
            
            # Capacity plot
            capacity_plot = df[df.Metric == 'Capacity'].hvplot.bar(
                x='Metric', y='Mean',
                title="Capacity Statistics",
                ylabel="Capacity (Ah)", 
                color='#388E3C',
                width=200, height=200,
                toolbar=False
            ).opts(
                show_legend=False,
                fontsize={'title': 12, 'labels': 10}
            )
            
            # Combine plots horizontally
            combined_plot = (duration_plot + voltage_plot + capacity_plot).opts(
                shared_axes=False
            )
            
            # Add summary info panel
            summary_info = pn.pane.HTML(f"""
            <div style='background: #E3F2FD; padding: 12px; border-radius: 6px; border-left: 4px solid #1976D2; margin-bottom: 10px;'>
                <strong style='color: #1976D2;'>📊 Basic Statistics Summary</strong><br>
                <div style='color: #666; font-size: 12px; margin-top: 5px;'>
                    {total_groups} groups • {total_segments} segments • <em>{data_source}</em><br>
                    Analysis timestamp: {data.get('analysis_timestamp', 'Current session')}<br>
                    {f"Error: {data['error']}" if 'error' in data else "✓ Analysis completed successfully"}
                </div>
            </div>
            """, width=650, height=80)
            
            # Return combined visualization
            return pn.Column(summary_info, pn.pane.HoloViews(combined_plot), sizing_mode='stretch_width')
            
        except Exception as e:
            # Fallback to simple display on error
            error_msg = f"Error creating interactive plot: {str(e)}"
            print(f"Statistics plot error: {error_msg}")
            
            return pn.pane.HTML(f"""
            <div style='background: #FFEBEE; padding: 15px; border-radius: 6px; border: 1px solid #D32F2F;'>
                <strong style='color: #D32F2F;'>Plot Error</strong><br>
                <div style='color: #666; margin-top: 8px;'>
                    Duration: {duration_mean:.1f} ± {duration_std:.1f} s<br>
                    Voltage: {voltage_mean:.3f} ± {voltage_std:.3f} V<br>
                    Capacity: {capacity_mean:.4f} ± {capacity_std:.4f} Ah<br>
                    <small>{error_msg}</small>
                </div>
            </div>
            """, width=650)
    
    def _create_statistics_histogram(self, data: Dict[str, Any]):
        """Create histogram visualization for per-technique statistics with real electrochemical data."""
        
        technique_breakdown = data.get('technique_breakdown', {})
        techniques_found = data.get('techniques_found', [])
        total_segments = data.get('total_segments', 0)
        
        if not technique_breakdown:
            return self._create_empty_plot("No statistical data available for histogram")
        
        # Extract data for histogram visualization
        metrics_data = []
        backend_results = technique_breakdown.get('backend_results', data.get('backend_results', {}))
        
        for metric_name, metric_stats in backend_results.items():
            if isinstance(metric_stats, dict) and 'count' in metric_stats:
                count = metric_stats.get('count', 0)
                mean = metric_stats.get('mean', 0)
                std = metric_stats.get('std', 0)
                
                # Create distribution info for display
                metrics_data.append({
                    'metric': metric_name.replace('_', ' ').title(),
                    'mean': mean,
                    'std': std,
                    'count': count,
                    'min': metric_stats.get('min', 0),
                    'max': metric_stats.get('max', 0)
                })
        
        if not metrics_data:
            return self._create_empty_plot("No statistical distributions available")
        
        # Create histogram visualization with distribution data
        histogram_html = f"""
        <div style='padding: 20px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;'>
                <h3 style='color: #2E4057; margin: 0;'>📊 Statistical Distributions - Histogram View</h3>
                <div style='color: #666; font-size: 12px;'>
                    {len(metrics_data)} metrics analyzed<br>
                    <em>Distribution analysis from backend</em>
                </div>
            </div>
            
            <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;'>
        """
        
        # Create distribution cards for each metric
        for i, metric in enumerate(metrics_data[:6]):  # Show first 6 metrics
            # Calculate distribution range for visual representation
            range_val = metric['max'] - metric['min']
            normalized_std = (metric['std'] / range_val * 100) if range_val > 0 else 0
            
            # Color scheme for different metrics
            colors = ['#1976D2', '#388E3C', '#F57C00', '#7B1FA2', '#C62828', '#00796B']
            color = colors[i % len(colors)]
            
            histogram_html += f"""
                <div style='background: white; border-radius: 8px; padding: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 4px solid {color};'>
                    <h4 style='color: {color}; margin: 0 0 12px 0; font-size: 16px;'>{metric['metric']}</h4>
                    
                    <!-- Distribution visualization -->
                    <div style='background: #F5F5F5; height: 80px; border-radius: 4px; margin-bottom: 12px; position: relative; overflow: hidden;'>
                        <div style='position: absolute; bottom: 0; left: 50%; transform: translateX(-50%); 
                                    width: {min(normalized_std + 20, 90)}%; height: 60%; background: {color}; 
                                    border-radius: 4px 4px 0 0; opacity: 0.3;'></div>
                        <div style='position: absolute; bottom: 0; left: 50%; transform: translateX(-50%); 
                                    width: 8px; height: 80%; background: {color}; border-radius: 2px;'></div>
                        <div style='position: absolute; top: 8px; right: 8px; font-size: 10px; color: #666;'>n={metric['count']}</div>
                    </div>
                    
                    <!-- Statistics -->
                    <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px;'>
                        <div><strong>Mean:</strong> {metric['mean']:.3f}</div>
                        <div><strong>Std:</strong> {metric['std']:.3f}</div>
                        <div><strong>Min:</strong> {metric['min']:.3f}</div>
                        <div><strong>Max:</strong> {metric['max']:.3f}</div>
                    </div>
                </div>
            """
        
        histogram_html += """
            </div>
            
            <div style='margin-top: 20px; padding: 12px; background: #E3F2FD; border-radius: 6px; border-left: 4px solid #1976D2;'>
                <strong style='color: #1976D2;'>Distribution Analysis:</strong><br>
                <div style='color: #666; font-size: 14px; margin-top: 5px;'>
                    Visual representation shows mean (dark bar) and standard deviation (light area)<br>
                    Each metric's distribution characteristics displayed with sample count<br>
                    Data sourced from electrochemical analysis backend
                </div>
            </div>
        </div>
        """
        
        return pn.pane.HTML(histogram_html)
    
    def _create_statistics_boxplot(self, data: Dict[str, Any]):
        """Create box plot visualization for statistics with real electrochemical data."""
        
        backend_results = data.get('backend_results', {})
        
        if not backend_results:
            return self._create_empty_plot("No statistical data available for box plots")
        
        # Extract data for box plot visualization
        metrics_data = []
        for metric_name, metric_stats in backend_results.items():
            if isinstance(metric_stats, dict) and all(k in metric_stats for k in ['min', 'max', 'mean']):
                metrics_data.append({
                    'metric': metric_name.replace('_', ' ').title(),
                    'min': metric_stats.get('min', 0),
                    'q1': metric_stats.get('mean', 0) - metric_stats.get('std', 0) * 0.5,  # Approx Q1
                    'median': metric_stats.get('mean', 0),  # Use mean as median approximation
                    'q3': metric_stats.get('mean', 0) + metric_stats.get('std', 0) * 0.5,  # Approx Q3
                    'max': metric_stats.get('max', 0),
                    'mean': metric_stats.get('mean', 0),
                    'std': metric_stats.get('std', 0),
                    'count': metric_stats.get('count', 0)
                })
        
        if not metrics_data:
            return self._create_empty_plot("No statistical distributions available for box plots")
        
        # Create box plot visualization
        boxplot_html = f"""
        <div style='padding: 20px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;'>
                <h3 style='color: #2E4057; margin: 0;'>📦 Statistical Distributions - Box Plot View</h3>
                <div style='color: #666; font-size: 12px;'>
                    {len(metrics_data)} metrics analyzed<br>
                    <em>Five-number summary from backend</em>
                </div>
            </div>
            
            <div style='display: flex; flex-direction: column; gap: 20px;'>
        """
        
        # Create box plot for each metric
        for i, metric in enumerate(metrics_data[:8]):  # Show first 8 metrics
            # Normalize values for visual representation (0-100 scale)
            value_range = metric['max'] - metric['min']
            if value_range == 0:
                continue
                
            # Calculate positions as percentages
            q1_pos = ((metric['q1'] - metric['min']) / value_range) * 80 + 10
            median_pos = ((metric['median'] - metric['min']) / value_range) * 80 + 10  
            q3_pos = ((metric['q3'] - metric['min']) / value_range) * 80 + 10
            mean_pos = ((metric['mean'] - metric['min']) / value_range) * 80 + 10
            
            # Color scheme for different metrics
            colors = ['#1976D2', '#388E3C', '#F57C00', '#7B1FA2', '#C62828', '#00796B', '#795548', '#607D8B']
            color = colors[i % len(colors)]
            
            boxplot_html += f"""
                <div style='background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 4px solid {color};'>
                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;'>
                        <h4 style='color: {color}; margin: 0; font-size: 16px;'>{metric['metric']}</h4>
                        <span style='color: #666; font-size: 12px;'>n = {metric['count']}</span>
                    </div>
                    
                    <!-- Box plot visualization -->
                    <div style='position: relative; height: 60px; background: #F8F9FA; border-radius: 6px; margin-bottom: 15px;'>
                        <!-- Whisker line (min to max) -->
                        <div style='position: absolute; top: 50%; left: 10%; right: 10%; height: 2px; background: {color}; transform: translateY(-50%);'></div>
                        
                        <!-- Box (Q1 to Q3) -->
                        <div style='position: absolute; top: 25%; left: {q1_pos}%; width: {q3_pos - q1_pos}%; height: 50%; 
                                    background: {color}; opacity: 0.3; border-radius: 3px;'></div>
                        <div style='position: absolute; top: 25%; left: {q1_pos}%; width: {q3_pos - q1_pos}%; height: 50%; 
                                    border: 2px solid {color}; border-radius: 3px;'></div>
                        
                        <!-- Median line -->
                        <div style='position: absolute; top: 20%; left: {median_pos}%; width: 2px; height: 60%; background: {color};'></div>
                        
                        <!-- Mean marker (diamond) -->
                        <div style='position: absolute; top: 50%; left: {mean_pos}%; width: 8px; height: 8px; 
                                    background: {color}; transform: translate(-50%, -50%) rotate(45deg); border: 1px solid white;'></div>
                        
                        <!-- Min/Max markers -->
                        <div style='position: absolute; top: 35%; left: 10%; width: 2px; height: 30%; background: {color};'></div>
                        <div style='position: absolute; top: 35%; right: 10%; width: 2px; height: 30%; background: {color};'></div>
                        
                        <!-- Value labels -->
                        <div style='position: absolute; top: -15px; left: 10%; font-size: 10px; color: #666; transform: translateX(-50%);'>{metric['min']:.3f}</div>
                        <div style='position: absolute; top: -15px; right: 10%; font-size: 10px; color: #666; transform: translateX(50%);'>{metric['max']:.3f}</div>
                        <div style='position: absolute; bottom: -15px; left: {median_pos}%; font-size: 10px; color: {color}; transform: translateX(-50%);'>{metric['median']:.3f}</div>
                    </div>
                    
                    <!-- Statistics summary -->
                    <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; font-size: 11px; text-align: center;'>
                        <div style='padding: 4px; background: #F5F5F5; border-radius: 3px;'>
                            <div style='font-weight: bold; color: {color};'>Q1</div>
                            <div>{metric['q1']:.3f}</div>
                        </div>
                        <div style='padding: 4px; background: #F5F5F5; border-radius: 3px;'>
                            <div style='font-weight: bold; color: {color};'>Median</div>
                            <div>{metric['median']:.3f}</div>
                        </div>
                        <div style='padding: 4px; background: #F5F5F5; border-radius: 3px;'>
                            <div style='font-weight: bold; color: {color};'>Q3</div>
                            <div>{metric['q3']:.3f}</div>
                        </div>
                        <div style='padding: 4px; background: #F5F5F5; border-radius: 3px;'>
                            <div style='font-weight: bold; color: {color};'>Mean</div>
                            <div>{metric['mean']:.3f}</div>
                        </div>
                    </div>
                </div>
            """
        
        boxplot_html += """
            </div>
            
            <div style='margin-top: 20px; padding: 12px; background: #E8F5E8; border-radius: 6px; border-left: 4px solid #388E3C;'>
                <strong style='color: #388E3C;'>Box Plot Legend:</strong><br>
                <div style='color: #666; font-size: 14px; margin-top: 5px;'>
                    📦 <strong>Box:</strong> Q1 to Q3 (interquartile range) • 
                    <strong>Line in box:</strong> Median • 
                    <strong>Diamond:</strong> Mean • 
                    <strong>Whiskers:</strong> Min to Max range<br>
                    Statistical quartiles approximated from mean and standard deviation
                </div>
            </div>
        </div>
        """
        
        return pn.pane.HTML(boxplot_html)
    
    # ===== RESISTANCE ANALYSIS METHODS =====
    
    def _create_resistance_plot(self, data: Dict[str, Any], settings: Dict[str, Any]):
        """Create resistance analysis plot with real electrochemical resistance data."""
        
        if not data or 'resistance_analysis' not in data:
            return self._create_empty_plot("No resistance analysis data available")
        
        # Get current plot type
        plot_type = self.plot_type_selector.value
        
        if plot_type == "resistance_time":
            return self._create_resistance_time_plot(data)
        elif plot_type == "resistance_distribution":
            return self._create_resistance_distribution_plot(data)
        elif plot_type == "resistance_summary":
            return self._create_resistance_summary_plot(data)
        else:
            return self._create_resistance_time_plot(data)  # Default
    
    def _create_resistance_time_plot(self, data: Dict[str, Any]):
        """Create resistance vs time plot with real IR resistance data using hvplot."""
        
        resistance_analysis = data.get('resistance_analysis', {})
        
        # Check if we have any data structure to work with
        if not resistance_analysis:
            return self._create_empty_plot("No resistance analysis data available")
        
        # Handle case where we have measurements but no valid resistance values
        valid_measurements = resistance_analysis.get('valid_measurements', 0)
        total_measurements = resistance_analysis.get('total_measurements', 0)
        null_measurements = resistance_analysis.get('null_measurements', 0)
        invalid_measurements = resistance_analysis.get('invalid_measurements', 0)
        
        if total_measurements == 0:
            return self._create_empty_plot("No resistance measurements found in backend data")
        
        if valid_measurements == 0:
            # We have measurements but they're all null/invalid - show diagnostic info
            diagnostic_html = f"""
            <div style='padding: 20px;'>
                <div style='background: #FFF3CD; border: 1px solid #F0AD4E; border-radius: 8px; padding: 20px;'>
                    <h3 style='color: #8A6D3B; margin: 0 0 15px 0;'>📊 Resistance Analysis Diagnostic</h3>
                    <div style='color: #8A6D3B; font-size: 14px; line-height: 1.5;'>
                        <strong>Data Status:</strong><br>
                        • Total measurements found: {total_measurements}<br>
                        • Valid measurements: {valid_measurements}<br>
                        • Null measurements: {null_measurements}<br>
                        • Invalid measurements: {invalid_measurements}<br><br>
                        
                        <strong>Possible causes:</strong><br>
                        • Insufficient current pulse data for resistance calculation<br>
                        • Data quality issues in source files<br>
                        • Calculation algorithm unable to determine valid IR values<br><br>
                        
                        <em>Try selecting different groups with current pulse segments or check data quality in the original files.</em>
                    </div>
                </div>
            </div>
            """
            return pn.pane.HTML(diagnostic_html)
        
        # We have valid measurements, proceed with hvplot visualization
        resistance_values = resistance_analysis.get('resistance_values_ohm', [])
        time_points = resistance_analysis.get('time_points_s', [])
        measurement_types = resistance_analysis.get('measurement_types', set())
        
        if not resistance_values:
            return self._create_empty_plot("No valid resistance values available for time plot")
        
        if len(resistance_values) != len(time_points):
            return self._create_empty_plot("Resistance and time data length mismatch")
        
        # Create DataFrame for hvplot
        try:
            df = pd.DataFrame({
                'Time_Point': time_points,
                'Resistance': resistance_values,
                'Measurement_Index': range(len(resistance_values))
            })
            
            # Create scatter plot: Resistance vs Time Point
            resistance_plot = df.hvplot.scatter(
                x='Time_Point', y='Resistance',
                title="IR Resistance vs Time",
                xlabel="Time Point (s)", ylabel="Resistance (Ω)",
                color='#F57C00', size=60, alpha=0.8,
                width=500, height=300,
                toolbar=False
            ).opts(
                fontsize={'title': 14, 'labels': 12},
                show_legend=False
            )
            
            # Add line plot to show trend if we have multiple time points
            if len(set(time_points)) > 1:
                # Sort by time for line plot
                df_sorted = df.sort_values('Time_Point')
                line_plot = df_sorted.hvplot.line(
                    x='Time_Point', y='Resistance',
                    color='#F57C00', line_width=2, alpha=0.6
                ).opts(show_legend=False)
                
                combined_plot = (resistance_plot * line_plot)
            else:
                combined_plot = resistance_plot
            
            # Summary info
            avg_resistance = resistance_analysis.get('average_resistance_ohm', 0.0)
            std_resistance = resistance_analysis.get('resistance_std_ohm', 0.0)
            
            summary_info = pn.pane.HTML(f"""
            <div style='background: #FFF3E0; padding: 12px; border-radius: 6px; border-left: 4px solid #F57C00; margin-bottom: 10px;'>
                <strong style='color: #F57C00;'>⚡ Resistance vs Time Analysis</strong><br>
                <div style='color: #666; font-size: 12px; margin-top: 5px;'>
                    {len(resistance_values)} measurements • Avg: {avg_resistance:.4f} Ω • Std: {std_resistance:.4f} Ω<br>
                    <em>IR resistance evolution • Types: {', '.join(sorted(measurement_types))}</em>
                </div>
            </div>
            """, width=650, height=60)
            
            return pn.Column(summary_info, pn.pane.HoloViews(combined_plot), sizing_mode='stretch_width')
            
        except Exception as e:
            # Fallback on error
            error_msg = f"Error creating resistance plot: {str(e)}"
            print(f"Resistance plot error: {error_msg}")
            
            return pn.pane.HTML(f"""
            <div style='background: #FFEBEE; padding: 15px; border-radius: 6px; border: 1px solid #D32F2F;'>
                <strong style='color: #D32F2F;'>Resistance Plot Error</strong><br>
                <div style='color: #666; margin-top: 8px;'>
                    {len(resistance_values)} measurements found<br>
                    Time points: {len(time_points)}<br>
                    <small>{error_msg}</small>
                </div>
            </div>
            """, width=650)
    
    def _create_resistance_distribution_plot(self, data: Dict[str, Any]):
        """Create resistance distribution analysis plot with statistical breakdown using hvplot."""
        
        resistance_analysis = data.get('resistance_analysis', {})
        
        # Check if we have any data structure to work with
        if not resistance_analysis:
            return self._create_empty_plot("No resistance analysis data available")
        
        # Handle case where we have measurements but no valid resistance values
        valid_measurements = resistance_analysis.get('valid_measurements', 0)
        total_measurements = resistance_analysis.get('total_measurements', 0)
        
        if total_measurements == 0:
            return self._create_empty_plot("No resistance measurements found in backend data")
        
        if valid_measurements == 0:
            null_measurements = resistance_analysis.get('null_measurements', 0)
            invalid_measurements = resistance_analysis.get('invalid_measurements', 0)
            
            diagnostic_html = f"""
            <div style='padding: 20px;'>
                <div style='background: #FFF3CD; border: 1px solid #F0AD4E; border-radius: 8px; padding: 20px;'>
                    <h3 style='color: #8A6D3B; margin: 0 0 15px 0;'>📊 Resistance Distribution Diagnostic</h3>
                    <div style='color: #8A6D3B; font-size: 14px; line-height: 1.5;'>
                        <strong>Data Status:</strong><br>
                        • Total measurements: {total_measurements}<br>
                        • Valid measurements: {valid_measurements}<br>
                        • Null measurements: {null_measurements}<br>
                        • Invalid measurements: {invalid_measurements}<br><br>
                        
                        <em>No valid resistance values available for distribution analysis. See time plot for detailed diagnostic information.</em>
                    </div>
                </div>
            </div>
            """
            return pn.pane.HTML(diagnostic_html)
        
        # We have valid measurements, proceed with hvplot visualization
        resistance_values = resistance_analysis.get('resistance_values_ohm', [])
        time_points = resistance_analysis.get('time_points_s', [])
        measurement_types = resistance_analysis.get('measurement_types', set())
        
        if not resistance_values:
            return self._create_empty_plot("No valid resistance values available for distribution plot")
        
        # Create DataFrame for hvplot
        try:
            df = pd.DataFrame({
                'Resistance': resistance_values,
                'Time_Point': time_points,
                'Time_Label': [f"{t}s" for t in time_points],
                'Measurement_Index': range(len(resistance_values))
            })
            
            plots = []
            
            # Plot 1: Overall resistance histogram
            hist_plot = df.hvplot.hist(
                y='Resistance', bins=15,
                title="Resistance Distribution",
                xlabel="Resistance (Ω)", ylabel="Count",
                color='#2196F3', alpha=0.7,
                width=300, height=250,
                toolbar=False
            ).opts(
                fontsize={'title': 12, 'labels': 10},
                show_legend=False
            )
            plots.append(hist_plot)
            
            # Plot 2: Box plot by time point (if multiple time points)
            if len(set(time_points)) > 1:
                box_plot = df.hvplot.box(
                    y='Resistance', by='Time_Label',
                    title="Resistance by Time Point",
                    xlabel="Time Point", ylabel="Resistance (Ω)",
                    width=300, height=250,
                    toolbar=False
                ).opts(
                    fontsize={'title': 12, 'labels': 10},
                    show_legend=False
                )
                plots.append(box_plot)
            
            # Plot 3: Statistics scatter plot
            # Group by time point and calculate stats
            time_stats = []
            for time_point in sorted(set(time_points)):
                subset = df[df.Time_Point == time_point]
                time_stats.append({
                    'Time_Point': time_point,
                    'Mean_Resistance': subset['Resistance'].mean(),
                    'Std_Resistance': subset['Resistance'].std(),
                    'Count': len(subset)
                })
            
            stats_df = pd.DataFrame(time_stats)
            if len(stats_df) > 1:
                stats_plot = stats_df.hvplot.scatter(
                    x='Time_Point', y='Mean_Resistance', size='Count',
                    title="Mean Resistance vs Time",
                    xlabel="Time Point (s)", ylabel="Mean Resistance (Ω)",
                    color='#4CAF50', alpha=0.8,
                    width=300, height=250,
                    toolbar=False
                ).opts(
                    fontsize={'title': 12, 'labels': 10},
                    show_legend=False
                )
                plots.append(stats_plot)
            
            # Combine plots
            if len(plots) >= 3:
                plot_layout = (plots[0] + plots[1] + plots[2]).cols(2).opts(shared_axes=False)
            elif len(plots) == 2:
                plot_layout = (plots[0] + plots[1]).opts(shared_axes=False)
            else:
                plot_layout = plots[0]
            
            # Summary info
            overall_mean = resistance_analysis.get('average_resistance_ohm', 0.0)
            overall_std = resistance_analysis.get('resistance_std_ohm', 0.0)
            cv_percent = (overall_std / overall_mean * 100) if overall_mean > 0 else 0
            
            summary_info = pn.pane.HTML(f"""
            <div style='background: #E3F2FD; padding: 12px; border-radius: 6px; border-left: 4px solid #2196F3; margin-bottom: 10px;'>
                <strong style='color: #2196F3;'>📊 Resistance Distribution Analysis</strong><br>
                <div style='color: #666; font-size: 12px; margin-top: 5px;'>
                    {len(resistance_values)} measurements • Mean: {overall_mean:.4f} ± {overall_std:.4f} Ω • CV: {cv_percent:.1f}%<br>
                    <em>Statistical breakdown by measurement time points • Interactive visualization</em>
                </div>
            </div>
            """, width=650, height=60)
            
            return pn.Column(summary_info, pn.pane.HoloViews(plot_layout), sizing_mode='stretch_width')
            
        except Exception as e:
            # Fallback on error
            error_msg = f"Error creating distribution plots: {str(e)}"
            print(f"Resistance distribution plot error: {error_msg}")
            
            return pn.pane.HTML(f"""
            <div style='background: #FFEBEE; padding: 15px; border-radius: 6px; border: 1px solid #D32F2F;'>
                <strong style='color: #D32F2F;'>Distribution Plot Error</strong><br>
                <div style='color: #666; margin-top: 8px;'>
                    {len(resistance_values)} measurements found<br>
                    Time points: {len(set(time_points))} unique<br>
                    <small>{error_msg}</small>
                </div>
            </div>
            """, width=650)
    
    def _create_resistance_summary_plot(self, data: Dict[str, Any]):
        """Create comprehensive IR resistance analysis summary plot using hvplot."""
        
        resistance_analysis = data.get('resistance_analysis', {})
        
        if not resistance_analysis:
            return self._create_empty_plot("No resistance analysis data available for summary")
        
        # Extract comprehensive data including quality metrics
        total_measurements = resistance_analysis.get('total_measurements', 0)
        valid_measurements = resistance_analysis.get('valid_measurements', 0)
        null_measurements = resistance_analysis.get('null_measurements', 0)
        invalid_measurements = resistance_analysis.get('invalid_measurements', 0)
        
        avg_resistance = resistance_analysis.get('average_resistance_ohm', 0)
        resistance_std = resistance_analysis.get('resistance_std_ohm', 0)
        measurement_types = resistance_analysis.get('measurement_types', set())
        calculation_quality = resistance_analysis.get('calculation_quality', [])
        
        resistance_values = resistance_analysis.get('resistance_values_ohm', [])
        time_points = resistance_analysis.get('time_points_s', [])
        
        # Handle case where we have no valid measurements but show diagnostic info
        if valid_measurements == 0 and total_measurements > 0:
            summary_info = pn.pane.Markdown(f"""
            ### 🔍 Resistance Analysis Diagnostic
            
            **Data Status:**
            - Total measurements processed: **{total_measurements}**
            - Valid resistance values: **{valid_measurements}**
            - Null measurements: **{null_measurements}**  
            - Invalid measurements: **{invalid_measurements}**
            
            **Quality Indicators:** {', '.join(set(calculation_quality)) if calculation_quality else 'None available'}
            
            **Measurement Types:** {', '.join(measurement_types) if measurement_types else 'None detected'}
            
            **Recommendations:**
            - Verify current pulse segments are present in selected groups
            - Check data quality and ensure sufficient sampling rate
            - Consider using groups with galvanostatic charge/discharge segments
            """, margin=(10, 20))
            
            return summary_info
        
        # Calculate additional statistics for valid measurements
        min_resistance = min(resistance_values) if resistance_values else 0
        max_resistance = max(resistance_values) if resistance_values else 0
        resistance_range = max_resistance - min_resistance
        cv_percent = (resistance_std / avg_resistance * 100) if avg_resistance > 0 else 0
        
        # Quality assessment
        quality_score = 0
        if total_measurements >= 10: quality_score += 25
        if cv_percent <= 15: quality_score += 25
        elif cv_percent <= 30: quality_score += 15
        if len(measurement_types) >= 2: quality_score += 25
        if avg_resistance > 0: quality_score += 25
        
        quality_label = ("Excellent" if quality_score >= 90 else 
                        "Good" if quality_score >= 70 else 
                        "Moderate" if quality_score >= 50 else "Poor")
        
        # Create summary text information
        summary_info = pn.pane.Markdown(f"""
        ### 📋 IR Resistance Analysis Summary
        
        **Key Metrics:**
        - Average Resistance: **{avg_resistance:.4f} ± {resistance_std:.4f} Ω**
        - Coefficient of Variation: **{cv_percent:.1f}%**
        - Range: **{min_resistance:.4f} - {max_resistance:.4f} Ω** (Δ{resistance_range:.4f} Ω)
        - Quality Score: **{quality_label}** ({quality_score}/100 points)
        
        **Analysis Details:**
        - Total measurements: {total_measurements} ({valid_measurements} valid)
        - Measurement types: {len(measurement_types)} timepoints
        - Time distribution: {', '.join([f"{t}s" for t in sorted(set(time_points))])}
        """, margin=(10, 20))
        
        try:
            # Create DataFrame for visualization
            import pandas as pd
            
            # Create metrics comparison plot
            metrics_data = pd.DataFrame({
                'Metric': ['Average', 'Std Dev', 'Min', 'Max', 'CV%'],
                'Value': [avg_resistance, resistance_std, min_resistance, max_resistance, cv_percent/10],  # Scale CV for visibility
                'Unit': ['Ω', 'Ω', 'Ω', 'Ω', '% (÷10)']
            })
            
            # Bar chart of key metrics
            metrics_plot = metrics_data.hvplot.bar(
                x='Metric', y='Value',
                title="Resistance Analysis Key Metrics",
                xlabel="Statistical Measure", ylabel="Value",
                color='#FF5722', alpha=0.8,
                width=400, height=250,
                toolbar=False
            ).opts(
                fontsize={'title': 12, 'labels': 10},
                show_legend=False
            )
            
            # Create quality assessment gauge-style plot
            quality_data = pd.DataFrame({
                'Category': ['Measurements', 'Variability', 'Coverage', 'Validity'],
                'Score': [
                    25 if total_measurements >= 10 else 0,
                    25 if cv_percent <= 15 else 15 if cv_percent <= 30 else 0,
                    25 if len(measurement_types) >= 2 else 0,
                    25 if avg_resistance > 0 else 0
                ]
            })
            
            quality_plot = quality_data.hvplot.bar(
                x='Category', y='Score',
                title=f"Quality Assessment - {quality_label}",
                xlabel="Quality Dimension", ylabel="Score (0-25)",
                color=['#4CAF50' if score >= 20 else '#FF9800' if score >= 10 else '#F44336' 
                       for score in quality_data['Score']],
                alpha=0.8, width=400, height=250,
                toolbar=False
            ).opts(
                fontsize={'title': 12, 'labels': 10},
                show_legend=False
            )
            
            # Combine the plots
            combined_plot = (metrics_plot + quality_plot).cols(2)
            
            return pn.Column(
                summary_info,
                pn.pane.HoloViews(combined_plot),
                sizing_mode='stretch_width'
            )
            
        except Exception as e:
            print(f"Error creating resistance summary plots: {e}")
            
            # Fallback: return just the summary info
            return pn.Column(
                summary_info,
                pn.pane.Markdown(f"""
                **Resistance Summary Stats:**
                - {avg_resistance:.4f} Ω ± {resistance_std:.4f} Ω  
                - CV: {cv_percent:.1f}% | Quality: {quality_label}
                - {total_measurements} measurements ({len(measurement_types)} timepoints)
                """, margin=(10, 20)),
                sizing_mode='stretch_width'
            )
    
    def _create_dqdv_plot(self, data: Dict[str, Any], settings: Dict[str, Any]):
        """Create dQ/dV analysis plot with real electrochemical insights data."""
        
        if not data or 'electrochemical_insights' not in data:
            return self._create_empty_plot("No dQ/dV analysis data available")
        
        # Get current plot type
        plot_type = self.plot_type_selector.value
        
        if plot_type == "dqdv_voltage":
            return self._create_dqdv_voltage_table(data)
        elif plot_type == "peak_analysis":
            return self._create_dqdv_peak_analysis(data)  
        elif plot_type == "overlay_comparison":
            return self._create_dqdv_overlay_comparison(data)
        else:
            return self._create_dqdv_voltage_table(data)  # Default
    
    def _create_kinetics_plot(self, data: Dict[str, Any], settings: Dict[str, Any]):
        """Create kinetics analysis plot with real electrochemical data."""
        
        if not data or 'kinetics_analysis' not in data:
            return self._create_empty_plot("No kinetics analysis data available")
        
        # Get current plot type
        plot_type = self.plot_type_selector.value
        
        if plot_type == "voltage_time":
            return self._create_kinetics_voltage_table(data)
        elif plot_type == "kinetics_fit":
            return self._create_kinetics_fit_summary(data)
        elif plot_type == "fit_quality":
            return self._create_kinetics_quality_table(data)
        else:
            return self._create_kinetics_voltage_table(data)  # Default
    
    # ===== dQ/dV VISUALIZATION METHODS =====
    
    def _create_dqdv_voltage_table(self, data: Dict[str, Any]):
        """Create dQ/dV voltage relaxation analysis table."""
        
        insights = data.get('electrochemical_insights', {})
        rest_analysis = insights.get('rest_analysis', {})
        
        # Extract voltage relaxation data
        rest_data = []
        for segment_id, segment_data in rest_analysis.items():
            if segment_data and 'voltage_relaxation' in segment_data:
                relaxation = segment_data['voltage_relaxation']
                rest_data.append({
                    'segment_id': segment_id,
                    'initial_v': relaxation.get('initial_voltage_v', 0.0),
                    'equilibrium_v': relaxation.get('equilibrium_voltage_v', 0.0), 
                    'time_constant_s': relaxation.get('time_constant_s', 0.0),
                    'r_squared': relaxation.get('r_squared', 0.0),
                    'voltage_drop_mv': relaxation.get('voltage_drop_mv', 0.0)
                })
        
        if not rest_data:
            return self._create_empty_plot("No voltage relaxation data available for dQ/dV analysis")
        
        # Create summary table
        total_segments = len(rest_data)
        avg_time_constant = sum(d['time_constant_s'] for d in rest_data) / total_segments
        avg_voltage_drop = sum(d['voltage_drop_mv'] for d in rest_data) / total_segments
        
        # Convert to DataFrame for hvplot
        # Truncate segment IDs for display
        for d in rest_data:
            d['segment_id'] = d['segment_id'][:12]
        
        df = pd.DataFrame(rest_data)
        
        try:
            # Create scatter plot: Time constant vs R² (with voltage drop as size)
            scatter_plot = df.hvplot.scatter(
                x='time_constant_s', y='r_squared', size='voltage_drop_mv',
                title="Relaxation Analysis Quality",
                xlabel="Time Constant τ (s)", ylabel="Fit Quality R²",
                color='#1976D2', alpha=0.7, 
                width=300, height=250,
                toolbar=False
            ).opts(
                fontsize={'title': 12, 'labels': 10},
                show_legend=False
            )
            
            # Create voltage comparison plot: Initial vs Equilibrium
            voltage_plot = df.hvplot.scatter(
                x='initial_v', y='equilibrium_v',
                title="Voltage Comparison", 
                xlabel="Initial Voltage (V)", ylabel="Equilibrium Voltage (V)",
                color='#2E4057', alpha=0.7,
                width=300, height=250,
                toolbar=False
            ).opts(
                fontsize={'title': 12, 'labels': 10},
                show_legend=False
            )
            
            # Create distribution plot: Time constants histogram
            time_hist = df.hvplot.hist(
                y='time_constant_s', bins=10,
                title="Time Constant Distribution",
                xlabel="Count", ylabel="Time Constant τ (s)",
                color='#388E3C', alpha=0.7,
                width=300, height=250,
                toolbar=False
            ).opts(
                fontsize={'title': 12, 'labels': 10},
                show_legend=False
            )
            
            # Combine plots in a layout
            plot_layout = (scatter_plot + voltage_plot + time_hist).cols(2).opts(
                shared_axes=False
            )
            
            # Add summary info
            summary_info = pn.pane.HTML(f"""
            <div style='background: #E3F2FD; padding: 12px; border-radius: 6px; border-left: 4px solid #1976D2; margin-bottom: 10px;'>
                <strong style='color: #1976D2;'>⚡ dQ/dV Voltage Relaxation Analysis</strong><br>
                <div style='color: #666; font-size: 12px; margin-top: 5px;'>
                    {total_segments} rest segments analyzed • Avg τ: {avg_time_constant:.1f} s • Avg ΔV: {avg_voltage_drop:.1f} mV<br>
                    <em>Electrochemical insights backend • Interactive visualization</em>
                </div>
            </div>
            """, width=650, height=60)
            
            return pn.Column(summary_info, pn.pane.HoloViews(plot_layout), sizing_mode='stretch_width')
            
        except Exception as e:
            # Fallback to summary on error  
            error_msg = f"Error creating voltage relaxation plots: {str(e)}"
            print(f"dQ/dV plot error: {error_msg}")
            
            # Show simple summary instead
            return pn.pane.HTML(f"""
            <div style='background: #FFEBEE; padding: 15px; border-radius: 6px; border: 1px solid #D32F2F;'>
                <strong style='color: #D32F2F;'>dQ/dV Analysis Error</strong><br>
                <div style='color: #666; margin-top: 8px;'>
                    {total_segments} segments analyzed<br>
                    Avg time constant: {avg_time_constant:.1f} s<br>
                    Avg voltage drop: {avg_voltage_drop:.1f} mV<br>
                    <small>{error_msg}</small>
                </div>
            </div>
            """, width=650)
    
    def _create_dqdv_peak_analysis(self, data: Dict[str, Any]):
        """Create dQ/dV peak analysis placeholder."""
        return self._create_empty_plot("dQ/dV peak analysis visualization will be enhanced in future phases")
    
    def _create_dqdv_overlay_comparison(self, data: Dict[str, Any]):
        """Create dQ/dV overlay comparison placeholder."""
        return self._create_empty_plot("dQ/dV overlay comparison will be enhanced in future phases")
    
    # ===== KINETICS VISUALIZATION METHODS =====
    
    def _create_kinetics_voltage_table(self, data: Dict[str, Any]):
        """Create kinetics voltage analysis table - Phase 2.2: Voltage vs time kinetics plots."""
        
        kinetics_data = data.get('kinetics_analysis', {})
        
        # Check if we have any data structure to work with
        if not kinetics_data:
            return self._create_empty_plot("No kinetics analysis data available")
        
        # Handle case where we have measurements but no valid kinetics values
        valid_measurements = kinetics_data.get('valid_measurements', 0)
        total_measurements = kinetics_data.get('total_measurements', 0)
        null_measurements = kinetics_data.get('null_measurements', 0)
        invalid_measurements = kinetics_data.get('invalid_measurements', 0)
        
        if total_measurements == 0:
            return self._create_empty_plot("No kinetics measurements found in backend data")
        
        if valid_measurements == 0:
            # We have measurements but they're all null/invalid - show diagnostic info
            diagnostic_html = f"""
            <div style='padding: 20px;'>
                <div style='background: #FFF3CD; border: 1px solid #F0AD4E; border-radius: 8px; padding: 20px;'>
                    <h3 style='color: #8A6D3B; margin: 0 0 15px 0;'>⚗️ Kinetics Analysis Diagnostic</h3>
                    <div style='color: #8A6D3B; font-size: 14px; line-height: 1.5;'>
                        <strong>Data Status:</strong><br>
                        • Total measurements found: {total_measurements}<br>
                        • Valid measurements: {valid_measurements}<br>
                        • Null measurements: {null_measurements}<br>
                        • Invalid measurements: {invalid_measurements}<br><br>
                        
                        <strong>Possible causes:</strong><br>
                        • No equilibrium segments available for kinetics analysis<br>
                        • Voltage relaxation data quality insufficient for curve fitting<br>
                        • Equilibrium calculation algorithm unable to determine valid parameters<br><br>
                        
                        <em>Try selecting groups with rest/relaxation segments or check data quality in the original files.</em>
                    </div>
                </div>
            </div>
            """
            return pn.pane.HTML(diagnostic_html)
        
        # Extract kinetics data with proper handling of None values
        raw_time_constants = kinetics_data.get('time_constants', [])
        raw_diffusion_coeffs = kinetics_data.get('diffusion_coefficients', [])
        raw_equilibrium_voltages = kinetics_data.get('equilibrium_voltages', [])
        calculation_quality = kinetics_data.get('calculation_quality', [])
        
        # Filter out None values and convert to proper numeric data
        time_constants = [tc for tc in raw_time_constants if tc is not None and isinstance(tc, (int, float))]
        diffusion_coeffs = [dc for dc in raw_diffusion_coeffs if dc is not None and isinstance(dc, (int, float))]
        equilibrium_voltages = [ev for ev in raw_equilibrium_voltages if ev is not None and isinstance(ev, (int, float))]
        
        print(f"DEBUG: Filtered data - {len(equilibrium_voltages)} valid equilibrium voltages, {len(time_constants)} valid time constants, {len(diffusion_coeffs)} valid diffusion coeffs")
        
        # Show meaningful diagnostic only if we have no data at all
        if not time_constants and not diffusion_coeffs and not equilibrium_voltages:
            return self._create_empty_plot("No valid kinetics parameters (time constants, diffusion coefficients, or equilibrium voltages) available")
            
        # Show info about what data we have
        print(f"DEBUG: Creating kinetics plots with {len(equilibrium_voltages)} equilibrium voltages, {len(time_constants)} time constants, {len(diffusion_coeffs)} diffusion coefficients")
        
        # Create interactive plots for kinetics data
        try:
            plots = []
            
            # Plot 1: Equilibrium Voltages Line Plot
            if equilibrium_voltages:
                eq_df = pd.DataFrame({
                    'Index': range(1, len(equilibrium_voltages) + 1),
                    'Equilibrium_Voltage': equilibrium_voltages,
                    'Label': [f'V_eq{i+1}' for i in range(len(equilibrium_voltages))]
                })
                
                eq_plot = eq_df.hvplot.line(
                    x='Index', y='Equilibrium_Voltage',
                    title="Equilibrium Voltages",
                    xlabel="Measurement #", ylabel="Voltage (V)",
                    color='#2E4057', line_width=2,
                    width=300, height=200,
                    toolbar=False
                ).opts(
                    fontsize={'title': 11, 'labels': 9},
                    show_legend=False
                )
                plots.append(eq_plot)
            
            # Plot 2: Time Constants Bar Plot
            if time_constants:
                tc_df = pd.DataFrame({
                    'Index': range(1, len(time_constants) + 1),
                    'Time_Constant': time_constants,
                    'Label': [f'τ{i+1}' for i in range(len(time_constants))]
                })
                
                tc_plot = tc_df.hvplot.bar(
                    x='Index', y='Time_Constant',
                    title="Time Constants",
                    xlabel="Measurement #", ylabel="τ (seconds)",
                    color='#1976D2', alpha=0.8,
                    width=300, height=200,
                    toolbar=False
                ).opts(
                    fontsize={'title': 11, 'labels': 9},
                    show_legend=False
                )
                plots.append(tc_plot)
            
            # Plot 3: Diffusion Coefficients Scatter Plot
            if diffusion_coeffs:
                dc_df = pd.DataFrame({
                    'Index': range(1, len(diffusion_coeffs) + 1),
                    'Diffusion_Coefficient': diffusion_coeffs,
                    'Label': [f'D{i+1}' for i in range(len(diffusion_coeffs))]
                })
                
                dc_plot = dc_df.hvplot.scatter(
                    x='Index', y='Diffusion_Coefficient',
                    title="Diffusion Coefficients",
                    xlabel="Measurement #", ylabel="D (cm²/s)",
                    color='#388E3C', size=60, alpha=0.8,
                    width=300, height=200,
                    toolbar=False
                ).opts(
                    fontsize={'title': 11, 'labels': 9},
                    show_legend=False
                )
                plots.append(dc_plot)
            
            # Plot 4: Quality Distribution (if quality data available)
            if calculation_quality:
                quality_stats = {}
                for quality in calculation_quality:
                    quality_stats[quality] = quality_stats.get(quality, 0) + 1
                
                quality_df = pd.DataFrame({
                    'Quality': list(quality_stats.keys()),
                    'Count': list(quality_stats.values())
                })
                
                quality_plot = quality_df.hvplot.bar(
                    x='Quality', y='Count',
                    title="Calculation Quality",
                    xlabel="Quality Level", ylabel="Count",
                    color='#4CAF50', alpha=0.8,
                    width=300, height=200,
                    toolbar=False
                ).opts(
                    fontsize={'title': 11, 'labels': 9},
                    show_legend=False,
                    xrotation=45
                )
                plots.append(quality_plot)
            
            # Combine plots in a layout
            print(f"DEBUG: Created {len(plots)} individual plots")
            
            if len(plots) >= 3:
                plot_layout = (plots[0] + plots[1] + plots[2]).cols(2).opts(shared_axes=False)
                if len(plots) > 3:
                    plot_layout = (plots[0] + plots[1] + plots[2] + plots[3]).cols(2).opts(shared_axes=False)
                print(f"DEBUG: Created combined layout with {len(plots)} plots")
            elif len(plots) == 2:
                plot_layout = (plots[0] + plots[1]).opts(shared_axes=False)
                print(f"DEBUG: Created 2-plot layout")
            elif len(plots) == 1:
                plot_layout = plots[0]
                print(f"DEBUG: Using single plot layout")
            else:
                plot_layout = None
                print(f"DEBUG: No plots created, returning empty")
            
            if not plot_layout:
                return self._create_empty_plot("No kinetics data available for plotting")
                
        except Exception as e:
            # Fallback to summary on error
            error_msg = f"Error creating kinetics plots: {str(e)}"
            print(f"Kinetics plot error: {error_msg}")
            plot_layout = None
        
        # Create summary info and return interactive visualization
        if plot_layout:
            # Summary info panel using Markdown
            summary_info = pn.pane.Markdown(f"""
            ### ⚗️ Kinetics Analysis - Interactive Plots
            
            **Data Summary:**
            - {len(equilibrium_voltages)} equilibrium voltages
            - {len(time_constants)} time constants  
            - {len(diffusion_coeffs)} diffusion coefficients
            
            *Electrochemical equilibrium backend • Interactive hvplot visualization*
            """, margin=(10, 20))
            
            result_column = pn.Column(summary_info, pn.pane.HoloViews(plot_layout), sizing_mode='stretch_width')
            print(f"DEBUG: Returning Column with {len(result_column)} components: {[type(comp).__name__ for comp in result_column]}")
            return result_column
        
        else:
            # Fallback error display using Markdown
            return pn.pane.Markdown(f"""
            ### ❌ Kinetics Analysis Error
            
            **Data Found:**
            - {len(equilibrium_voltages)} equilibrium voltages
            - {len(time_constants)} time constants
            - {len(diffusion_coeffs)} diffusion coefficients
            
            *Unable to create interactive plots - check data quality*
            """, margin=(10, 20))
    
    def _create_kinetics_fit_summary(self, data: Dict[str, Any]):
        """Create kinetics fit quality summary - Phase 2.3: Equilibrium voltage analysis plots."""
        
        kinetics_data = data.get('kinetics_analysis', {})
        
        # Check if we have any data structure to work with
        if not kinetics_data:
            return self._create_empty_plot("No kinetics analysis data available")
        
        # Handle case where we have measurements but no valid kinetics values
        valid_measurements = kinetics_data.get('valid_measurements', 0)
        total_measurements = kinetics_data.get('total_measurements', 0)
        
        if total_measurements == 0:
            return self._create_empty_plot("No kinetics measurements found in backend data")
        
        if valid_measurements == 0:
            return self._create_empty_plot("No valid equilibrium measurements available for fit analysis")
        
        # Extract kinetics data
        equilibrium_voltages = kinetics_data.get('equilibrium_voltages', [])
        calculation_quality = kinetics_data.get('calculation_quality', [])
        time_constants = kinetics_data.get('time_constants', [])
        diffusion_coeffs = kinetics_data.get('diffusion_coefficients', [])
        
        if not equilibrium_voltages:
            return self._create_empty_plot("No equilibrium voltage data available for fit summary")
        
        # Summary statistics
        avg_voltage = sum(equilibrium_voltages) / len(equilibrium_voltages)
        voltage_std = (sum((v - avg_voltage)**2 for v in equilibrium_voltages) / len(equilibrium_voltages))**0.5 if len(equilibrium_voltages) > 1 else 0.0
        
        # Quality statistics
        quality_stats = {}
        for quality in calculation_quality:
            quality_stats[quality] = quality_stats.get(quality, 0) + 1
        
        valid_count = quality_stats.get('valid', 0)
        invalid_count = quality_stats.get('invalid', 0)
        quality_percentage = (valid_count / len(calculation_quality) * 100) if calculation_quality else 0
        
        fit_html = f"""
        <div style='padding: 20px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;'>
                <h3 style='color: #2E4057; margin: 0;'>🎯 Kinetics Fit - Equilibrium Analysis</h3>
                <div style='color: #666; font-size: 12px;'>
                    {len(equilibrium_voltages)} equilibrium points<br>
                    <em>Quality: {quality_percentage:.0f}% valid</em>
                </div>
            </div>
            
            <div style='display: grid; grid-template-columns: 2fr 1fr; gap: 20px;'>
                <div style='padding: 20px; background: #F8F9FA; border-radius: 8px; border-left: 4px solid #4CAF50;'>
                    <h4 style='color: #4CAF50; margin-top: 0;'>Equilibrium Voltage Summary</h4>
                    <div style='margin-bottom: 15px;'>
                        <div style='font-size: 18px; font-weight: 600; color: #2E4057;'>{avg_voltage:.4f} ± {voltage_std:.4f} V</div>
                        <div style='color: #666; font-size: 14px;'>Mean equilibrium voltage</div>
                    </div>
                    <div style='margin-bottom: 15px;'>
                        <div style='font-size: 16px; font-weight: 600; color: #2E4057;'>{valid_count}/{total_measurements}</div>
                        <div style='color: #666; font-size: 14px;'>Valid measurements</div>
                    </div>
                    <div>
                        <div style='font-size: 16px; font-weight: 600; color: #2E4057;'>{len(time_constants + diffusion_coeffs)}</div>
                        <div style='color: #666; font-size: 14px;'>Kinetic parameters</div>
                    </div>
                </div>
                
                <div style='padding: 20px; background: #E8F5E8; border-radius: 8px;'>
                    <h4 style='color: #4CAF50; margin-top: 0;'>Data Quality</h4>
                    <div style='text-align: center;'>
                        <div style='font-size: 36px; color: #4CAF50; margin: 10px 0;'>
                            {"✓" if quality_percentage > 80 else "⚠" if quality_percentage > 60 else "✗"}
                        </div>
                        <div style='font-weight: 600; color: #2E4057;'>
                            {"Excellent" if quality_percentage > 80 else "Good" if quality_percentage > 60 else "Poor"} Quality
                        </div>
                        <div style='color: #666; font-size: 12px; margin-top: 5px;'>
                            {quality_percentage:.0f}% valid calculations
                        </div>
                    </div>
                </div>
            </div>
            
            <div style='margin-top: 20px; padding: 12px; background: #E3F2FD; border-radius: 6px; border-left: 4px solid #1976D2;'>
                <strong style='color: #1976D2;'>Kinetics Analysis Notes:</strong><br>
                <div style='color: #666; font-size: 14px; margin-top: 5px;'>
                    Equilibrium voltages extracted from electrochemical equilibrium analysis<br>
                    High quality indicates stable measurements suitable for kinetics modeling<br>
                    Voltage variation: {(voltage_std/avg_voltage*100 if avg_voltage > 0 else 0):.2f}% coefficient of variation
                </div>
            </div>
        </div>
        """
        
        return pn.pane.HTML(fit_html)
    
    def _create_kinetics_quality_table(self, data: Dict[str, Any]):
        """Create kinetics fit quality assessment table."""
        return self._create_empty_plot("Kinetics fit quality table will be enhanced in future phases")
    
    def _create_empty_plot(self, message: str = "No data to display"):
        """Create empty plot with message."""
        
        return pn.pane.HTML(f"""
        <div style='border: 2px dashed #E0E0E0; border-radius: 8px; 
                    padding: 40px; text-align: center; color: #666;
                    background: #FAFAFA; min-height: 200px;
                    display: flex; align-items: center; justify-content: center;'>
            <div>
                <div style='font-size: 36px; margin-bottom: 10px;'>📈</div>
                <div style='font-size: 16px;'>{message}</div>
            </div>
        </div>
        """)
    
    # ===== PLOT MANAGEMENT =====
    
    def update_plot_area(self, plot_object):
        """Update the plot area with new plot."""
        
        self.current_plot = plot_object
        
        # Handle Panel HTML objects vs strings
        if plot_object is None:
            self.plot_area.object = ""
        elif hasattr(plot_object, 'object'):
            # If it's a Panel HTML pane, extract the HTML content
            self.plot_area.object = plot_object.object
        elif isinstance(plot_object, str):
            # If it's already a string, use it directly
            self.plot_area.object = plot_object
        else:
            # Convert to string as fallback
            self.plot_area.object = str(plot_object)
        
        # Enable export button when plot is available
        self.export_plot_btn.disabled = (plot_object is None)
    
    def update_available_plots(self, analysis_type: str):
        """Update available plot types for analysis."""
        
        self.current_analysis = analysis_type
        
        # Update available plot types based on analysis
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
        
        # Update selector options
        self.plot_type_selector.options = plot_options
        self.plot_type_selector.value = plot_options[0][1]  # Select first option
    
    # ===== STYLING AND UTILITIES =====
    
    def _apply_electrochemical_styling(self, plot):
        """Apply professional electrochemical styling to plots."""
        # Phase 3: Add professional styling
        return plot
    
    def _create_publication_plot(self, plot, settings: Dict[str, Any]):
        """Create publication-ready version of plot."""
        # Phase 4: Add publication formatting
        return plot
    
    # ===== EXPORT FUNCTIONALITY =====
    
    def export_current_plot(self, format: str = "png", **kwargs):
        """Export current plot to specified format.""" 
        
        if self.current_plot is None:
            return False
        
        # Phase 1: Placeholder
        print(f"Plot export functionality will be implemented in Phase 4")
        print(f"Requested format: {format}")
        return True