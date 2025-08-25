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
        self.last_options_analysis_type = None  # Track last analysis type for plot options

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

            # Update plot options when analysis type changes
            self.update_plot_options(analysis_type)

            # Handle errors (DataFrame-first architecture compatible)
            if isinstance(data, pd.DataFrame):
                # Check for error in DataFrame format
                if 'error_message' in data.columns and not data['error_message'].isna().all():
                    error_msg = data['error_message'].iloc[0]
                    return pn.pane.Markdown(f"**Error:** {error_msg}")
            elif isinstance(data, dict) and data.get("error"):
                return pn.pane.Markdown(f"**Error:** {data['error']}")

            # Get current plot type from selector  
            plot_type = self.plot_type_select.value
            
            print(f"✅ Creating registry-driven plot: {analysis_type}, plot_type: {plot_type}")
            
            # Use registry-driven generic plotting
            return self._create_registry_driven_plot(analysis_type, data, settings, plot_type)

        except Exception as e:
            print(f"❌ Plot creation error: {e}")
            return pn.pane.Markdown(f"**Plot Error:** {str(e)}")

    def _create_registry_driven_plot(self, analysis_type: str, data: Dict[str, Any], settings: Dict[str, Any], plot_type: str):
        """Create plot using registry-driven configuration."""
        
        try:
            # Get analysis configuration from registry
            analysis_config = self.registry.get_analysis(analysis_type)
            if not analysis_config:
                return pn.pane.Markdown(f"**Unknown analysis type:** {analysis_type}")
            
            # Get plot config from registry
            plot_config = analysis_config.plot_config.get(plot_type)
            if not plot_config:
                return pn.pane.Markdown(f"**Unknown plot type {plot_type} for analysis {analysis_type}**")
            
            # Extract DataFrame from analysis results (expecting DataFrame-first architecture)
            plot_df = self._extract_dataframe_from_results(data)
            if plot_df is None or plot_df.empty:
                return pn.pane.Markdown(f"**No data available for plotting {plot_type}**")
            
            # Create plot using registry plot configuration
            plot = self._create_plot_from_config(plot_df, plot_config)
            
            print(f"✅ Created registry-driven plot for {analysis_type}: {plot_type}")
            return plot
            
        except Exception as e:
            print(f"❌ Registry-driven plot creation failed: {e}")
            return pn.pane.Markdown(f"**Plot creation error:** {str(e)}")
    
    def _extract_dataframe_from_results(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Extract DataFrame from analysis results (DataFrame-first architecture)."""
        
        try:
            # DataFrame-first architecture - analysis functions return DataFrames directly
            if isinstance(data, pd.DataFrame):
                print(f"✅ Analysis result is already a DataFrame")
                return data
            
            # Handle wrapped DataFrame results
            if 'dataframe' in data:
                df = data['dataframe']
                if isinstance(df, pd.DataFrame) and not df.empty:
                    print(f"✅ Found DataFrame in results")
                    return df
            
            # Handle 'data' key containing DataFrame
            if 'data' in data:
                df_data = data['data']
                if isinstance(df_data, pd.DataFrame) and not df_data.empty:
                    print(f"✅ Found DataFrame in 'data' key")
                    return df_data
            
            print(f"⚠️ No DataFrame found in analysis results")
            return None
                
        except Exception as e:
            print(f"❌ DataFrame extraction error: {e}")
            return None

    def _create_plot_from_config(self, df: pd.DataFrame, plot_config: Dict[str, Any]) -> pn.pane.HoloViews:
        """Create plot using registry plot configuration with multi-series support."""
        
        try:
            plot_type = plot_config.get("plot_type", "line")
            x_column = plot_config.get("x_column")
            y_column = plot_config.get("y_column") 
            by_column = plot_config.get("by")  # Group by column for series
            title = plot_config.get("title", "Analysis Plot")
            x_label = plot_config.get("x_label", "X")
            y_label = plot_config.get("y_label", "Y")
            
            # Validate required columns exist
            missing_cols = []
            if x_column and x_column not in df.columns:
                missing_cols.append(x_column)
                
            # Handle y_column as string or list (multi-y-column support)
            if y_column:
                if isinstance(y_column, list):
                    # Multi-y-column: check all columns exist
                    missing_y = [col for col in y_column if col not in df.columns]
                    missing_cols.extend(missing_y)
                else:
                    # Single y-column: check exists
                    if y_column not in df.columns:
                        missing_cols.append(y_column)
            
            # Validate by column exists
            if by_column and by_column not in df.columns:
                missing_cols.append(by_column)
            
            if missing_cols:
                return pn.pane.Markdown(f"**Missing columns:** {missing_cols}")
            
            # Build plot parameters
            plot_params = {
                'title': title,
                'xlabel': x_label, 
                'ylabel': y_label,
                'width': 700, 
                'height': 400
            }
            
            # Add x column
            if x_column:
                plot_params['x'] = x_column
                
            # Add y column(s) and filter out null values
            if y_column:
                plot_params['y'] = y_column  # Works for both string and list
                
                # Filter DataFrame to remove null values in y_column(s)
                if isinstance(y_column, list):
                    # Multiple y columns - keep rows where at least one y column has data
                    mask = df[y_column].notna().any(axis=1)
                else:
                    # Single y column - keep rows where y column has data
                    mask = df[y_column].notna()
                
                # Apply filter if there are null values
                if not mask.all():
                    df = df[mask].copy()
                    print(f"✅ Filtered DataFrame: {mask.sum()} rows with non-null {y_column} data out of {len(mask)} total")
                    
                # Check if we have any data left after filtering
                if df.empty:
                    return pn.pane.Markdown(f"**No non-null data available for {y_column}**")
                
            # Add grouping column
            if by_column:
                plot_params['by'] = by_column
            
            # Create plot based on type
            if plot_type == "line":
                if not y_column:
                    return pn.pane.Markdown("**Error:** Line plot requires y_column")
                plot = df.hvplot.line(**plot_params)
                
            elif plot_type == "scatter":
                if not y_column:
                    return pn.pane.Markdown("**Error:** Scatter plot requires y_column")
                plot = df.hvplot.scatter(**plot_params)
                
            elif plot_type == "histogram":
                # For histogram, use x_column as the data column
                hist_params = plot_params.copy()
                hist_params['y'] = x_column  # Histogram data column
                if 'x' in hist_params:
                    del hist_params['x']  # Remove x for histogram
                hist_params['bins'] = 20
                plot = df.hvplot.hist(**hist_params)
                
            else:
                return pn.pane.Markdown(f"**Unsupported plot type:** {plot_type}")
            
            print(f"✅ Created plot: {plot_type}, y_columns: {y_column}, grouping: {by_column or 'None'}")
            return pn.pane.HoloViews(plot, sizing_mode='stretch_width')
            
        except Exception as e:
            print(f"❌ Plot creation from config failed: {e}")
            return pn.pane.Markdown(f"**Plot configuration error:** {str(e)}")
    
    def update_plot_options(self, analysis_type: str):
        """Update plot type selector options from registry."""
        
        try:
            # Check if analysis type has actually changed
            analysis_type_changed = (self.last_options_analysis_type != analysis_type)
            
            analysis_config = self.registry.get_analysis(analysis_type)
            if not analysis_config or not analysis_config.plot_config:
                self.plot_type_select.options = ["Default"]
                self.last_options_analysis_type = analysis_type
                return
            
            # Get plot names from registry plot_config
            plot_options = list(analysis_config.plot_config.keys())
            if plot_options:
                # Always update options
                self.plot_type_select.options = plot_options
                
                # Only reset value if analysis type changed or current value is invalid
                if analysis_type_changed or self.plot_type_select.value not in plot_options:
                    self.plot_type_select.value = plot_options[0]  # Select first option
                    print(f"✅ Updated plot options for {analysis_type}: {plot_options} (reset to first)")
                else:
                    print(f"✅ Updated plot options for {analysis_type}: {plot_options} (kept current selection: {self.plot_type_select.value})")
            else:
                self.plot_type_select.options = ["Default"]
            
            # Update tracking variable
            self.last_options_analysis_type = analysis_type
                
        except Exception as e:
            print(f"❌ Error updating plot options: {e}")
            self.plot_type_select.options = ["Default"]
            self.last_options_analysis_type = analysis_type
    # ========================================
    # HARDCODED ANALYSIS LOGIC REMOVED 
    # ========================================
    # DataFrame-first architecture: Analysis functions return DataFrames directly
    # Registry plot configs specify exact column names for plotting
    # No more data conversion methods needed

    def _resolve_auto_detect_columns(self, df: pd.DataFrame, config: Dict[str, Any], 
                                   analysis_type: str, plot_type: str) -> Dict[str, Any]:
        """Resolve auto_detect_* placeholders with actual DataFrame columns."""
        
        resolved_config = config.copy()
        available_columns = list(df.columns)
        
        # Define column preference mappings based on analysis type and common patterns
        column_preferences = {
            # Time-related columns (for x-axis in time series)
            "time": ["time", "time_s", "elapsed_time", "sequence", "measurement_number", "index"],
            
            # Value columns (for y-axis in various plots)  
            "value": ["resistance", "voltage", "potential_v", "current_a", "capacity_ah", "energy_wh", 
                     "equilibrium_voltage", "duration_s", "mean", "std", "count", "value"],
            
            # Category columns (for grouping/coloring)
            "category": ["resistance_type", "technique", "fundamental_technique", "fit_type", 
                        "measurement_type", "metric", "analysis_type"],
            
            # Count columns (for bar charts)
            "count": ["count", "frequency", "occurrence", "number"]
        }
        
        # Resolve auto-detect placeholders
        for key, value in config.items():
            if isinstance(value, str) and value.startswith("auto_detect_"):
                placeholder_type = value.replace("auto_detect_", "")
                
                # Find best matching column
                if placeholder_type in column_preferences:
                    for preferred_col in column_preferences[placeholder_type]:
                        if preferred_col in available_columns:
                            resolved_config[key] = preferred_col
                            print(f"✅ Auto-detected {placeholder_type}: {preferred_col} for {plot_type}")
                            break
                    else:
                        # Fallback: use first available column or remove the key
                        if placeholder_type == "category" and available_columns:
                            # For category, try to find a non-numeric column
                            categorical_cols = [col for col in available_columns 
                                              if df[col].dtype == 'object' or col in ['technique', 'type', 'method']]
                            if categorical_cols:
                                resolved_config[key] = categorical_cols[0]
                                print(f"⚠️ Auto-detected fallback category: {categorical_cols[0]} for {plot_type}")
                            else:
                                # Remove by parameter for non-categorical plots if no category column found
                                if key == "by":
                                    del resolved_config[key]
                                    print(f"⚠️ Removed category grouping for {plot_type} (no categorical columns)")
                        elif available_columns:
                            # For other types, use first available numeric-like column
                            numeric_cols = [col for col in available_columns 
                                          if col not in ['id', 'index'] and 
                                          (df[col].dtype in ['float64', 'int64'] or 'time' in col.lower())]
                            if numeric_cols:
                                resolved_config[key] = numeric_cols[0]
                                print(f"⚠️ Auto-detected fallback {placeholder_type}: {numeric_cols[0]} for {plot_type}")
        
        return resolved_config

    # All plotting is now registry-driven via _create_plot_from_config()

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

    

    def _on_plot_type_changed(self, event):
        """Handle plot type selector changes - regenerate plot with new type."""
        
        print(f"DEBUG: Plot type changed to: {event.new}")
        print(f"DEBUG: Current analysis type: {self.current_analysis_type}")
        print(f"DEBUG: Has current data: {self.current_data is not None}")
        print(f"DEBUG: Current data type: {type(self.current_data)}")
        print(f"DEBUG: Current settings: {self.current_settings is not None}")
        
        # Regenerate plot with current data if available (DataFrame-first compatible)
        has_data = (isinstance(self.current_data, pd.DataFrame) and not self.current_data.empty) or \
                   (isinstance(self.current_data, dict) and bool(self.current_data))
        
        if (self.current_analysis_type and has_data and self.current_settings):
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
    
