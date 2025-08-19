"""
Data Viewer Component

Handles data visualization using Bokeh plots through Panel.
"""

import panel as pn
import param
import numpy as np
import pandas as pd

class DataViewer(param.Parameterized):
    """
    Data visualization component with Bokeh plots.
    
    Provides:
    - Interactive Bokeh plots (reliable plotting!)
    - Multiple plot types (potential, current, power vs time)
    - DataFrame preview table
    - Technique-based color coding
    """
    
    status_message = param.String(default="", doc="Status message for main app")
    
    def __init__(self, api, **params):
        super().__init__(**params)
        self.api = api
        self.current_data = None
        self.current_file_id = None
        
        self._create_components()
    
    def _create_components(self):
        """Create the UI components."""
        self.header = pn.pane.HTML("""
        <h3 style='margin: 10px 0; color: #2E4057;'>
            📊 Data Visualization
        </h3>
        """)
        
        # Plot controls
        self.plot_potential_btn = pn.widgets.Button(
            name="Plot Potential vs Time",
            button_type="primary",
            width=200
        )
        self.plot_potential_btn.on_click(
            lambda event: self._plot_column('potential_v', 'Potential (V)')
        )
        
        self.plot_current_btn = pn.widgets.Button(
            name="Plot Current vs Time", 
            button_type="primary",
            width=200
        )
        self.plot_current_btn.on_click(
            lambda event: self._plot_column('current_a', 'Current (A)')
        )
        
        # Plot display
        self.plot_pane = pn.pane.HTML(
            "<p style='color: #666; text-align: center; padding: 100px;'>Select a file to view data</p>",
            min_height=400
        )
        
        # Data info
        self.data_info = pn.pane.HTML("")
    
    @property
    def panel(self):
        """Return the Panel layout."""
        return pn.Column(
            self.header,
            
            # Controls
            pn.Row(
                self.plot_potential_btn,
                self.plot_current_btn
            ),
            
            # Data info
            self.data_info,
            
            # Plot area
            self.plot_pane,
            
            margin=(10, 10)
        )
    
    def load_file_data(self, file_id: str):
        """Load file data for visualization."""
        self.current_file_id = file_id
        
        if not file_id:
            self.current_data = None
            self.plot_pane.object = "<p style='color: #666; text-align: center; padding: 100px;'>Select a file to view data</p>"
            self.data_info.object = ""
            return
        
        try:
            # Load data
            data = self.api.get_file_data(file_id)
            
            if data is None:
                self.data_info.object = f"<p style='color: red;'>❌ Could not load data for file: {file_id}</p>"
                return
            
            self.current_data = data.head(10000)  # Limit for performance
            
            # Show data info
            info_lines = [
                f"📄 <b>File:</b> {file_id}",
                f"📊 <b>Data Points:</b> {data.height:,} (showing first {min(10000, data.height):,})",
                f"📈 <b>Columns:</b> {data.width}",
                f"⏱️ <b>Time Range:</b> {data['time_s'].min():.1f} - {data['time_s'].max():.1f} seconds"
            ]
            
            self.data_info.object = f"""
            <div style='background: #f5f5f5; padding: 10px; border-radius: 5px; margin: 10px 0;'>
                {'<br>'.join(info_lines)}
            </div>
            """
            
            self.status_message = f"Loaded {data.height:,} data points"
            
        except Exception as e:
            self.data_info.object = f"<p style='color: red;'>❌ Error loading data: {str(e)}</p>"
            self.status_message = f"Error loading data: {str(e)}"
    
    def _plot_column(self, column: str, label: str):
        """Create Bokeh plot for specified column."""
        if self.current_data is None:
            return
        
        if column not in self.current_data.columns or 'time_s' not in self.current_data.columns:
            self.plot_pane.object = f"<p style='color: red;'>Column '{column}' or 'time_s' not found in data</p>"
            return
        
        try:
            # Convert to pandas for Bokeh (Bokeh works great with pandas)
            df = self.current_data.to_pandas()
            
            # Create Bokeh plot
            from bokeh.plotting import figure
            from bokeh.models import HoverTool
            
            p = figure(
                title=f"{label} vs Time - {self.current_file_id}",
                x_axis_label="Time (s)",
                y_axis_label=label,
                width=800,
                height=400,
                tools="pan,wheel_zoom,box_zoom,reset,save"
            )
            
            # Add hover tool
            hover = HoverTool(tooltips=[("Time", "@x{0.0} s"), (label, "@y{0.000}")])
            p.add_tools(hover)
            
            # Plot data with technique colors if available
            if 'technique_id' in df.columns:
                self._plot_with_techniques(p, df, column)
            else:
                # Simple single color plot
                p.line(df['time_s'], df[column], line_width=2, color='blue', alpha=0.8)
            
            # Update plot pane
            self.plot_pane.object = p
            self.status_message = f"Plotted {label} - {len(df):,} points"
            
        except Exception as e:
            self.plot_pane.object = f"<p style='color: red;'>❌ Error creating plot: {str(e)}</p>"
    
    def _plot_with_techniques(self, p, df, column):
        """Add technique-based coloring to plot."""
        try:
            # Get technique colors
            technique_colors = {
                8: '#2E8B57',   # Sea Green
                20: '#9932CC',  # Purple  
                23: '#FF6347',  # Tomato Red
            }
            
            # Plot each technique separately
            for technique_id in df['technique_id'].unique():
                if pd.isna(technique_id):
                    continue
                    
                mask = df['technique_id'] == technique_id
                technique_df = df[mask]
                
                color = technique_colors.get(int(technique_id), '#696969')
                
                p.line(
                    technique_df['time_s'], 
                    technique_df[column],
                    line_width=2,
                    color=color,
                    alpha=0.8,
                    legend_label=f"ActionID {int(technique_id)}"
                )
            
            p.legend.click_policy = "hide"
            
        except Exception as e:
            # Fallback to simple plot
            p.line(df['time_s'], df[column], line_width=2, color='blue', alpha=0.8)