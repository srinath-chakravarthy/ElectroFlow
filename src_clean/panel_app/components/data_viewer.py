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
        
        self.plot_power_btn = pn.widgets.Button(
            name="Plot Power vs Time",
            button_type="primary", 
            width=200
        )
        self.plot_power_btn.on_click(
            lambda event: self._plot_power()
        )
        
        # Data preview toggle
        self.show_data_btn = pn.widgets.Button(
            name="Show Data Preview",
            button_type="light",
            width=150
        )
        self.show_data_btn.on_click(self._toggle_data_preview)
        
        # Plot display - use Bokeh pane for proper plot rendering
        self.plot_pane = pn.pane.Bokeh(
            None,
            min_height=400,
            sizing_mode='stretch_width'
        )
        
        # Initial message pane
        self.plot_message = pn.pane.HTML(
            "<p style='color: #666; text-align: center; padding: 100px;'>Select a file to view data</p>",
            visible=True
        )
        
        # Initially hide plot pane
        self.plot_pane.visible = False
        
        # Data preview table (initially hidden)
        self.data_preview = pn.pane.DataFrame(
            pd.DataFrame(), 
            visible=False,
            height=300,
            width=800
        )
        
        # Data info
        self.data_info = pn.pane.HTML("")
        
        self.data_preview_visible = False
    
    @property
    def panel(self):
        """Return the Panel layout."""
        return pn.Column(
            self.header,
            
            # Plot controls
            pn.Row(
                self.plot_potential_btn,
                self.plot_current_btn,
                self.plot_power_btn
            ),
            
            # Data preview control
            pn.Row(
                self.show_data_btn
            ),
            
            # Data info
            self.data_info,
            
            # Plot area - conditionally show plot or message
            pn.pane.HTML("<b>Visualization:</b>"),
            pn.Column(
                self.plot_message,
                self.plot_pane,
                min_height=400
            ),
            
            # Data preview (conditional)
            self.data_preview,
            
            margin=(10, 10)
        )
    
    def load_file_data(self, file_id: str):
        """Load file data for visualization."""
        self.current_file_id = file_id
        
        if not file_id:
            self.current_data = None
            self.plot_pane.object = None
            self.plot_message.visible = True
            self.plot_pane.visible = False
            self.data_info.object = ""
            return
        
        try:
            # Load data
            data = self.api.get_file_data(file_id)
            
            if data is None:
                self.data_info.object = f"<p style='color: red;'>❌ Could not load data for file: {file_id}</p>"
                self.plot_message.visible = True
                self.plot_pane.visible = False
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
            self.plot_message.object = f"<p style='color: red;'>Column '{column}' or 'time_s' not found in data</p>"
            self.plot_message.visible = True
            self.plot_pane.visible = False
            return
        
        try:
            # Convert to pandas and create plot
            df = self.current_data.to_pandas()
            self._create_bokeh_plot(df, column, label)
            
        except Exception as e:
            self.plot_message.object = f"<p style='color: red;'>❌ Error creating plot: {str(e)}</p>"
            self.plot_message.visible = True
            self.plot_pane.visible = False
            self.status_message = f"Plot error: {str(e)}"
    
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
    
    def _plot_power(self):
        """Create power vs time plot."""
        if self.current_data is None:
            return
            
        try:
            # Calculate power if not present
            df = self.current_data.to_pandas()
            
            if 'power_w' not in df.columns:
                # Calculate power from V * I
                if 'potential_v' in df.columns and 'current_a' in df.columns:
                    df['power_w'] = df['potential_v'] * df['current_a']
                else:
                    self.plot_message.object = "<p style='color: red;'>Cannot calculate power: missing potential or current data</p>"
                    self.plot_message.visible = True
                    self.plot_pane.visible = False
                    return
            
            self._create_bokeh_plot(df, 'power_w', 'Power (W)')
            
        except Exception as e:
            self.plot_message.object = f"<p style='color: red;'>❌ Error creating power plot: {str(e)}</p>"
            self.plot_message.visible = True
            self.plot_pane.visible = False
    
    def _create_bokeh_plot(self, df, column, label):
        """Create a Bokeh plot for the specified column."""
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
        self.plot_pane.visible = True
        self.plot_message.visible = False
        self.status_message = f"Plotted {label} - {len(df):,} points"
    
    def _toggle_data_preview(self, event):
        """Toggle data preview table visibility."""
        self.data_preview_visible = not self.data_preview_visible
        self.data_preview.visible = self.data_preview_visible
        
        if self.data_preview_visible:
            self.show_data_btn.name = "Hide Data Preview"
            if self.current_data is not None:
                self.data_preview.object = self.current_data.to_pandas()
        else:
            self.show_data_btn.name = "Show Data Preview"