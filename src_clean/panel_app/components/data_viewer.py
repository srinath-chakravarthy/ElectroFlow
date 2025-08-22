"""
Professional Data Viewer Component - Dashboard Style with AC Data Detection

Clean visualization interface with intelligent plot type detection and professional styling.
"""

import panel as pn
import param
import numpy as np
import pandas as pd
import hvplot.pandas
import holoviews as hv
from holoviews.operation import decimate

class DataViewer(param.Parameterized):
    """
    Professional data visualization component with dashboard design.

    Features:
    - Dashboard-style layout
    - Intelligent AC data detection for Nyquist plots
    - Professional plot styling
    - Clean data preview
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
        """Create professional UI components."""

        # File info display
        self.file_info_display = pn.pane.HTML(
            """<div style='background: #F8F9FA; padding: 15px; border-radius: 4px; 
                          text-align: center; color: #666;'>
               <span style='font-size: 16px;'>📊</span><br>
               <strong>Select a file to view data</strong><br>
               <small>Choose a processed file from the File Operations panel</small>
               </div>""",
            margin=(10, 5)
        )

        # Plot controls
        self.plot_type_select = pn.widgets.Select(
            name="Visualization Type",
            options=["Select a file first..."],
            value="Select a file first...",
            width=200,
            margin=(5, 5)
        )
        self.plot_type_select.param.watch(self._on_plot_type_selected, 'value')

        # View controls
        self.show_data_btn = pn.widgets.Button(
            name="📋 Data Preview",
            button_type="light",
            width=130,
            margin=(5, 5)
        )
        self.show_data_btn.on_click(self._toggle_data_preview)

        self.export_btn = pn.widgets.Button(
            name="💾 Export CSV",
            button_type="light",
            width=130,
            disabled=True,
            margin=(5, 5)
        )

        # Plot area
        self.plot_pane = pn.pane.HoloViews(
            None,
            min_height=450,
            sizing_mode='stretch_width',
            margin=(10, 5)
        )

        # Welcome message
        self.plot_message = pn.pane.HTML(
            """<div style='text-align: center; padding: 80px 20px; color: #999;'>
               <span style='font-size: 48px; opacity: 0.3;'>📈</span><br><br>
               <strong style='font-size: 18px;'>Interactive Visualization</strong><br>
               <span style='font-size: 14px;'>Process a file to see voltage, current, and impedance plots</span>
               </div>""",
            visible=True,
            margin=(10, 5)
        )

        # Initially hide plot pane
        self.plot_pane.visible = False

        # Data preview table (initially hidden)
        self.data_preview = pn.pane.DataFrame(
            pd.DataFrame(),
            visible=False,
            height=300,
            width=800,
            margin=(10, 5)
        )

        # Data preview state
        self.data_preview_visible = False

    @property
    def panel(self):
        """Return professional dashboard layout."""

        # Header with icon
        header = pn.pane.HTML("""
        <div style='background: linear-gradient(135deg, #2E4057 0%, #1976D2 100%); color: white; 
                    padding: 15px; border-radius: 8px 8px 0 0; margin: 0;'>
            <h2 style='margin: 0; font-size: 18px; font-weight: 600;'>
                📊 Data Visualization
            </h2>
        </div>
        """, margin=(0, 0))

        # File info section
        info_section = pn.Column(
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 14px; font-weight: 600; margin: 15px 5px 10px 5px;'>
                Current File
            </div>
            """),
            self.file_info_display,
            margin=(10, 10)
        )

        # Controls section
        controls_section = pn.Column(
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 20px 5px 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                Visualization Controls
            </div>
            """),

            pn.Row(
                pn.Column(
                    pn.pane.HTML("<label style='font-weight: 500; color: #555; font-size: 14px;'>Plot Type:</label>"),
                    self.plot_type_select,
                    width=220
                ),
                pn.Column(
                    pn.pane.HTML("<label style='font-weight: 500; color: #555; font-size: 14px;'>Actions:</label>"),
                    pn.Row(
                        self.show_data_btn,
                        self.export_btn,
                        margin=(0, 0)
                    ),
                    width=280
                ),
                margin=(5, 5)
            ),
            margin=(10, 10)
        )

        # Visualization section
        viz_section = pn.Column(
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 20px 5px 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                Interactive Plot
            </div>
            """),

            # Plot area with conditional display
            pn.Column(
                self.plot_message,
                self.plot_pane,
                min_height=470,
                styles={'background': '#FAFAFA', 'border-radius': '4px', 'padding': '10px'}
            ),
            margin=(10, 10)
        )

        # Data preview section (conditional)
        preview_section = pn.Column(
            self.data_preview,
            margin=(10, 10)
        )

        # Complete card
        card_content = pn.Column(
            info_section,
            controls_section,
            viz_section,
            preview_section,
            styles={'background': 'white', 'border-radius': '0 0 8px 8px',
                   'box-shadow': '0 2px 8px rgba(0,0,0,0.1)', 'margin': '0'}
        )

        return pn.Column(
            header,
            card_content,
            margin=(10, 10),
            styles={'border-radius': '8px', 'overflow': 'hidden'}
        )

    def load_file_data(self, file_id: str):
        """Load file data with professional feedback."""
        self.current_file_id = file_id

        if not file_id:
            self.current_data = None
            self.plot_pane.object = None
            self.plot_message.visible = True
            self.plot_pane.visible = False
            self.export_btn.disabled = True

            # Reset to welcome state
            self.file_info_display.object = """
            <div style='background: #F8F9FA; padding: 15px; border-radius: 4px; 
                        text-align: center; color: #666;'>
                <span style='font-size: 16px;'>📊</span><br>
                <strong>Select a file to view data</strong><br>
                <small>Choose a processed file from the File Operations panel</small>
            </div>
            """
            self.plot_type_select.options = ["Select a file first..."]
            return

        try:
            # Load data
            data = self.api.get_file_data(file_id)

            if data is None:
                self._show_error_state(f"Could not load data for file: {file_id}")
                return

            self.current_data = data
            self.export_btn.disabled = False

            # Update file info display
            self._update_file_info_display(file_id, data)

            # Update available plot types
            self._update_plot_options(data)

            self.status_message = f"Loaded {data.height:,} data points"

        except Exception as e:
            self._show_error_state(f"Error loading data: {str(e)}")
            self.status_message = f"Error loading data: {str(e)}"

    def _update_file_info_display(self, file_id: str, data):
        """Update file info with data statistics."""
        try:
            time_range = data['time_s'].max() - data['time_s'].min()
            hours = int(time_range // 3600)
            minutes = int((time_range % 3600) // 60)

            # Check for different data types
            has_voltage = 'potential_v' in data.columns
            has_current = 'current_a' in data.columns
            has_impedance = self._has_impedance_data(data)

            data_types = []
            if has_voltage:
                data_types.append("Voltage")
            if has_current:
                data_types.append("Current")
            if has_impedance:
                data_types.append("Impedance")

            self.file_info_display.object = f"""
            <div style='background: #E8F5E8; padding: 15px; border-radius: 4px; 
                        border-left: 4px solid #2E7D32;'>
                <div style='font-weight: 600; color: #2E7D32; margin-bottom: 8px; font-size: 16px;'>
                    📄 {file_id}
                </div>
                <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 14px; color: #1B5E20;'>
                    <div><strong>Data Points:</strong> {data.height:,}</div>
                    <div><strong>Duration:</strong> {hours}h {minutes}m</div>
                    <div><strong>Columns:</strong> {data.width}</div>
                    <div><strong>Data Types:</strong> {', '.join(data_types)}</div>
                </div>
            </div>
            """

        except Exception:
            self.file_info_display.object = f"""
            <div style='background: #E8F5E8; padding: 15px; border-radius: 4px; 
                        border-left: 4px solid #2E7D32; text-align: center;'>
                <strong style='color: #2E7D32;'>📄 {file_id}</strong><br>
                <span style='color: #666; font-size: 14px;'>Data loaded successfully</span>
            </div>
            """

    def _update_plot_options(self, data):
        """Update plot options based on available data."""
        options = self._get_available_plot_types(data)
        self.plot_type_select.options = options

        # Set intelligent default
        if "Voltage vs Time" in options:
            self.plot_type_select.value = "Voltage vs Time"
        elif len(options) > 0:
            self.plot_type_select.value = options[0]

    def _get_available_plot_types(self, data):
        """Determine available plot types based on data columns."""
        options = []

        # Always available (basic overview)
        if 'potential_v' in data.columns:
            options.append("Voltage vs Time")

        if 'current_a' in data.columns:
            options.append("Current vs Time")

        # Check for impedance data (AC techniques)
        if self._has_impedance_data(data):
            options.append("Nyquist Plot")

        # Computed plots
        # if 'potential_v' in data.columns and 'current_a' in data.columns:
        #     options.append("Power vs Time")

        if not options:
            options = ["No plottable data available"]

        return options

    def _has_impedance_data(self, data):
        """Check if data contains valid AC impedance measurements."""
        required_cols = ['impedance_real_ohm', 'impedance_imag_ohm']

        if not all(col in data.columns for col in required_cols):
            return False

        # Check for non-null impedance data
        real_data = data.get_column('impedance_real_ohm').drop_nulls()
        imag_data = data.get_column('impedance_imag_ohm').drop_nulls()

        return len(real_data) > 0 and len(imag_data) > 0

    def _show_error_state(self, error_message):
        """Show error state in the interface."""
        self.file_info_display.object = f"""
        <div style='background: #FFEBEE; padding: 15px; border-radius: 4px; 
                    border-left: 4px solid #D32F2F; text-align: center;'>
            <strong style='color: #D32F2F;'>❌ Error</strong><br>
            <span style='color: #666; font-size: 14px;'>{error_message}</span>
        </div>
        """
        self.plot_message.visible = True
        self.plot_pane.visible = False
        self.plot_type_select.options = ["Error loading data"]
        self.export_btn.disabled = True

    def _on_plot_type_selected(self, event):
        """Handle plot type selection."""
        plot_type = event.new
        
        # Handle tuple case from Select widget (display_name, actual_value)
        if isinstance(plot_type, tuple):
            plot_type = plot_type[1] if len(plot_type) > 1 else plot_type[0]
        elif not isinstance(plot_type, str):
            plot_type = str(plot_type) if plot_type is not None else ""

        if plot_type in ["Select a file first...", "No plottable data available", "Error loading data"]:
            return

        if self.current_data is None:
            return

        try:
            if plot_type == "Voltage vs Time":
                self._create_time_series_plot('time_s', 'potential_v', 'Voltage vs Time', 'Time (s)', 'Voltage (V)')
            elif plot_type == "Current vs Time":
                self._create_time_series_plot('time_s', 'current_a', 'Current vs Time', 'Time (s)', 'Current (A)')
            # elif plot_type == "Power vs Time":
            #     self._create_power_plot()
            elif plot_type == "Nyquist Plot":
                self._create_nyquist_plot()

        except Exception as e:
            self._show_plot_error(f"Error creating {plot_type}: {str(e)}")

    # def _create_time_series_plot(self, x_col, y_col, title, x_label, y_label):
    #     """Create time series plot with technique coloring."""
    #     df = self.current_data.to_pandas()
    #
    #     if x_col not in df.columns or y_col not in df.columns:
    #         self._show_plot_error(f"Missing required columns: {x_col} or {y_col}")
    #         return
    #
    #     try:
    #         # Create plot with technique-based coloring if available
    #         if 'segment_number' in df.columns and df['segment_number'].nunique() > 1:
    #             # Group by segment for different colors
    #             curves = []
    #             colors = ['#2E8B57', '#9932CC', '#FF6347', '#1E90FF', '#FFD700', '#FF69B4']
    #
    #             for i, (segment_num, segment_data) in enumerate(df.groupby('segment_number')):
    #                 if len(segment_data) == 0:
    #                     continue
    #
    #                 color = colors[i % len(colors)]
    #
    #                 # Create curve with decimation for large datasets
    #                 curve = hv.Curve(segment_data, kdims=[x_col], vdims=[y_col],
    #                                label=f'Segment {int(segment_num)}')
    #
    #                 if len(segment_data) > 1000:
    #                     curve = decimate(curve, max_samples=1000, dynamic=True)
    #
    #                 curves.append(curve.opts(color=color, line_width=2, alpha=0.8))
    #
    #             if curves:
    #                 plot = curves[0]
    #                 for curve in curves[1:]:
    #                     plot = plot * curve
    #             else:
    #                 # Fallback to single curve
    #                 plot = self._create_single_curve(df, x_col, y_col)
    #         else:
    #             # Single curve
    #             plot = self._create_single_curve(df, x_col, y_col)
    #
    #         # Apply styling
    #         plot = plot.opts(
    #             title=f"{title} - {self.current_file_id}",
    #             xlabel=x_label,
    #             ylabel=y_label,
    #             width=700,
    #             height=400,
    #             # tools=['pan', 'wheel_zoom', 'box_zoom', 'reset', 'save'],
    #             active_tools=['pan', 'wheel_zoom']
    #         )
    #
    #         # Update display
    #         self.plot_pane.object = plot
    #         self.plot_pane.visible = True
    #         self.plot_message.visible = False
    #         self.status_message = f"Plotted {title} - {len(df):,} points"
    #
    #     except Exception as e:
    #         self._show_plot_error(f"Error creating time series plot: {str(e)}")

    def _create_time_series_plot(self, x_col, y_col, title, x_label, y_label):
        """Create simplified single-curve time series plot with dynamic decimation."""
        df = self.current_data.to_pandas()

        if x_col not in df.columns or y_col not in df.columns:
            self._show_plot_error(f"Missing required columns: {x_col} or {y_col}")
            return

        try:
            # Simple single curve approach - no overlays or complex coloring
            curve = hv.Curve(df, kdims=[x_col], vdims=[y_col])

            # Apply dynamic decimation for large datasets (>10,000 points)
            if len(df) > 10000:
                curve = decimate(curve, max_samples=10000, dynamic=True)
                print(f"Applied dynamic decimation: {len(df):,} points -> max 10,000 points")

            # Professional single-color styling
            plot = curve.opts(
                color='#1976D2',  # Professional blue
                line_width=2,
                alpha=0.8,
                title=f"{title} - {self.current_file_id}",
                xlabel=x_label,
                ylabel=y_label,
                width=700,
                height=400,
                tools=['pan', 'wheel_zoom', 'box_zoom', 'reset', 'save'],
                active_tools=['pan', 'wheel_zoom']
            )

            # Update display
            self.plot_pane.object = plot
            self.plot_pane.visible = True
            self.plot_message.visible = False

            # Simple status message
            self.status_message = f"Plotted {title} - {len(df):,} points"

        except Exception as e:
            self._show_plot_error(f"Error creating time series plot: {str(e)}")
            print(f"Plot creation error: {str(e)}")  # Debug print

    def _create_single_curve(self, df, x_col, y_col):
        """Create a single curve with decimation."""
        curve = hv.Curve(df, kdims=[x_col], vdims=[y_col])

        if len(df) > 1000:
            curve = decimate(curve, max_samples=1000, dynamic=False)

        return curve.opts(color='#1976D2', line_width=2, alpha=0.8)

    # def _create_power_plot(self):
    #     """Create power vs time plot."""
    #     df = self.current_data.to_pandas()
    #
    #     # Calculate power if not present
    #     if 'power_w' not in df.columns:
    #         if 'potential_v' in df.columns and 'current_a' in df.columns:
    #             df['power_w'] = df['potential_v'] * df['current_a']
    #         else:
    #             self._show_plot_error("Cannot calculate power: missing voltage or current data")
    #             return
    #
    #     self._create_time_series_plot('time_s', 'power_w', 'Power vs Time', 'Time (s)', 'Power (W)')

    # def _create_nyquist_plot(self):
    #     """Create Nyquist plot for impedance data."""
    #     df = self.current_data.to_pandas()
    #
    #     real_col = 'impedance_real_ohm'
    #     imag_col = 'impedance_imag_ohm'
    #
    #     if real_col not in df.columns or imag_col not in df.columns:
    #         self._show_plot_error("Missing impedance data for Nyquist plot")
    #         return
    #
    #     # Filter out NaN values
    #     impedance_data = df.dropna(subset=[real_col, imag_col])
    #
    #     if len(impedance_data) == 0:
    #         self._show_plot_error("No valid impedance data found")
    #         return
    #
    #     try:
    #         # Create points plot
    #         points = hv.Points(impedance_data, kdims=[real_col], vdims=[imag_col])
    #
    #         # Apply decimation for large datasets
    #         if len(impedance_data) > 1000:
    #             points = decimate(points, max_samples=1000, dynamic=False)
    #
    #         # Style the plot
    #         plot = points.opts(
    #             color='#1976D2',
    #             size=6,
    #             alpha=0.7,
    #             title=f"Nyquist Plot - {self.current_file_id}",
    #             xlabel="Real Impedance (Ω)",
    #             ylabel="Imaginary Impedance (Ω)",
    #             width=600,
    #             height=600,
    #             tools=['pan', 'wheel_zoom', 'box_zoom', 'reset', 'save'],
    #             active_tools=['pan', 'wheel_zoom'],
    #             aspect='equal'
    #         )
    #
    #         # Update display
    #         self.plot_pane.object = plot
    #         self.plot_pane.visible = True
    #         self.plot_message.visible = False
    #         self.status_message = f"Plotted Nyquist - {len(impedance_data):,} points"
    #
    #     except Exception as e:
    #         self._show_plot_error(f"Error creating Nyquist plot: {str(e)}")

    def _create_nyquist_plot(self):
        """Create Nyquist plot for impedance data with segment-based coloring."""
        df = self.current_data.to_pandas()

        real_col = 'impedance_real_ohm'
        imag_col = 'impedance_imag_ohm'

        if real_col not in df.columns or imag_col not in df.columns:
            self._show_plot_error("Missing impedance data for Nyquist plot")
            return

        # Filter out NaN values
        impedance_data = df.dropna(subset=[real_col, imag_col])
        impedance_data = df[impedance_data[imag_col] <= -0.01]

        if len(impedance_data) == 0:
            self._show_plot_error("No valid impedance data found")
            return
        xlims = None
        ylims = None

        try:
            print(f"Nyquist plot: {len(impedance_data)} impedance points")

            # Create segment-colored plots if segment data is available
            if 'segment_number' in impedance_data.columns and impedance_data['segment_number'].nunique() > 1:
                # Color by segment - each EIS measurement gets its own color
                curves = []
                colors = ['#1976D2', '#2E8B57', '#9932CC', '#FF6347', '#FFD700',
                          '#FF69B4', '#708090', '#20B2AA', '#32CD32', '#DC143C']

                print(f"Found {impedance_data['segment_number'].nunique()} EIS segments")

                for i, (segment_num, segment_data) in enumerate(impedance_data.groupby('segment_number')):
                    if len(segment_data) == 0:
                        continue

                    color = colors[i % len(colors)]

                    # Change to -Z_imag for consistency
                    segment_data[imag_col] = -segment_data[imag_col]

                    # Create points for this segment
                    points = hv.Points(segment_data, kdims=[real_col, imag_col], vdims=[],
                                       label=f'EIS Segment {int(segment_num)} ({len(segment_data)} pts)')

                    curves.append(points.opts(
                        color=color,
                        size=8,
                        alpha=0.8
                    ))

                    print(f"  - Segment {int(segment_num)}: {len(segment_data)} points -> {color}")
                    xlims = (min(segment_data[real_col]), max(segment_data[real_col]))
                    ylims = (0, max(segment_data[imag_col]))

                if curves:
                    plot = hv.Overlay(curves)
                    print(f"Created overlay with {len(curves)} EIS segments")
                else:
                    # Fallback to single curve
                    plot = hv.Points(impedance_data, kdims=[real_col], vdims=[imag_col])
                    plot = plot.opts(color='#1976D2', size=8, alpha=0.8)
            else:
                # Single color if no segments or only one segment
                plot = hv.Points(impedance_data, kdims=[real_col], vdims=[imag_col])
                plot = plot.opts(color='#1976D2', size=8, alpha=0.8)
                print("Single EIS measurement or no segment data")

            # Apply professional EIS styling
            plot = plot.opts(
                title=f"Nyquist Plot - {self.current_file_id}",
                xlabel="Real Impedance (Ω)",
                ylabel="-Imaginary Impedance (Ω)",  # Standard EIS convention
                width=600,
                height=600,
                tools=['pan', 'wheel_zoom', 'box_zoom', 'reset', 'save', 'hover'],
                active_tools=['pan', 'wheel_zoom'],
                xlim = xlims,
                ylim = ylims,
                # aspect='equal',  # Critical for proper semicircle visualization
                legend_position='right',
                legend_opts={'click_policy': 'hide'}
            )

            # Update display
            self.plot_pane.object = plot
            self.plot_pane.visible = True
            self.plot_message.visible = False
            self.status_message = f"Plotted Nyquist - {len(impedance_data):,} impedance points"

        except Exception as e:
            self._show_plot_error(f"Error creating Nyquist plot: {str(e)}")
            print(f"Nyquist plot error: {str(e)}")

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

    def _toggle_data_preview(self, event):
        """Toggle data preview table visibility."""
        self.data_preview_visible = not self.data_preview_visible
        self.data_preview.visible = self.data_preview_visible

        if self.data_preview_visible:
            self.show_data_btn.name = "📋 Hide Preview"
            if self.current_data is not None:
                # Show first 1000 rows
                preview_data = self.current_data.head(1000).to_pandas()
                self.data_preview.object = preview_data
        else:
            self.show_data_btn.name = "📋 Data Preview"