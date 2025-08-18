"""
Data Viewer Widget

Central widget for displaying:
- File data tables
- Interactive plots (pyqtgraph)
- Analysis results
- Group comparisons
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableView, 
    QLabel, QPushButton, QSplitter, QTextEdit, QScrollArea, QGroupBox,
    QFormLayout, QTreeWidget, QTreeWidgetItem
)
from PySide6.QtCore import Qt, Signal, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QFont
import pyqtgraph as pg
import pandas as pd
import numpy as np


class DataFrameModel(QAbstractTableModel):
    """Table model for displaying Pandas DataFrames efficiently."""
    
    def __init__(self, df=None):
        super().__init__()
        self._df = df if df is not None else pd.DataFrame()
        
    def rowCount(self, parent=QModelIndex()):
        return len(self._df)
    
    def columnCount(self, parent=QModelIndex()):
        return len(self._df.columns)
    
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._df)):
            return None
            
        if role == Qt.DisplayRole:
            value = self._df.iloc[index.row(), index.column()]
            if pd.isna(value):
                return ""
            return str(value)
        
        return None
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._df.columns[section])
            else:
                return str(section)
        return None
    
    def setDataFrame(self, df):
        """Update the model with new DataFrame."""
        self.beginResetModel()
        self._df = df if df is not None else pd.DataFrame()
        self.endResetModel()


class DataViewerWidget(QWidget):
    """Central widget for data visualization and analysis."""
    
    # Signals
    segments_selected = Signal(list)  # List of segment IDs for grouping
    
    def __init__(self, backend_api, parent=None):
        super().__init__(parent)
        self.api = backend_api
        self.active_cell_id = None
        self.active_cell_name = ""
        self.current_file_id = None
        self.current_data = None
        
        # Table model for data display
        self.table_model = DataFrameModel()
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Create tab widget for different views
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Tab 1: File Overview
        self.setup_file_overview_tab()
        
        # Tab 2: Data Table
        self.setup_data_table_tab()
        
        # Tab 3: Plots
        self.setup_plots_tab()
        
        # Tab 4: Analysis
        self.setup_analysis_tab()
    
    def setup_file_overview_tab(self):
        """Setup the file overview tab with comprehensive file information."""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        
        # Scrollable area for file info
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # File metadata group
        metadata_group = QGroupBox("File Metadata")
        metadata_layout = QFormLayout(metadata_group)
        
        self.file_name_label = QLabel("No file selected")
        self.file_type_label = QLabel("-")
        self.upload_time_label = QLabel("-")
        self.processing_status_label = QLabel("-")
        self.temperature_label = QLabel("-")
        
        metadata_layout.addRow("File Name:", self.file_name_label)
        metadata_layout.addRow("File Type:", self.file_type_label)
        metadata_layout.addRow("Upload Time:", self.upload_time_label)
        metadata_layout.addRow("Processing Status:", self.processing_status_label)
        metadata_layout.addRow("Temperature:", self.temperature_label)
        
        scroll_layout.addWidget(metadata_group)
        
        # Data statistics group
        stats_group = QGroupBox("Data Statistics")
        stats_layout = QFormLayout(stats_group)
        
        self.total_rows_label = QLabel("-")
        self.total_columns_label = QLabel("-")
        self.time_range_label = QLabel("-")
        self.data_size_label = QLabel("-")
        
        stats_layout.addRow("Total Rows:", self.total_rows_label)
        stats_layout.addRow("Total Columns:", self.total_columns_label)
        stats_layout.addRow("Time Range:", self.time_range_label)
        stats_layout.addRow("Data Size:", self.data_size_label)
        
        scroll_layout.addWidget(stats_group)
        
        # Techniques overview group
        techniques_group = QGroupBox("Techniques Overview")
        techniques_layout = QVBoxLayout(techniques_group)
        
        self.techniques_tree = QTreeWidget()
        self.techniques_tree.setHeaderLabels(["Technique", "Action ID", "Duration (s)", "Points"])
        techniques_layout.addWidget(self.techniques_tree)
        
        scroll_layout.addWidget(techniques_group)
        
        # Column information group
        columns_group = QGroupBox("Column Information")
        columns_layout = QVBoxLayout(columns_group)
        
        self.columns_tree = QTreeWidget()
        self.columns_tree.setHeaderLabels(["Column", "Data Type", "Min", "Max", "Units"])
        columns_layout.addWidget(self.columns_tree)
        
        scroll_layout.addWidget(columns_group)
        
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        
        layout.addWidget(scroll_area)
        
        self.tabs.addTab(tab_widget, "File Overview")
    
    def setup_data_table_tab(self):
        """Setup the data table tab."""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        
        # Table controls
        controls_layout = QHBoxLayout()
        
        self.rows_label = QLabel("Showing 0 rows")
        controls_layout.addWidget(self.rows_label)
        
        controls_layout.addStretch()
        
        self.export_btn = QPushButton("Export Data")
        self.export_btn.setEnabled(False)
        controls_layout.addWidget(self.export_btn)
        
        layout.addLayout(controls_layout)
        
        # Table view with model
        self.data_table = QTableView()
        self.data_table.setModel(self.table_model)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSortingEnabled(True)
        layout.addWidget(self.data_table)
        
        # Status
        self.data_status = QLabel("No data loaded")
        self.data_status.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.data_status)
        
        self.tabs.addTab(tab_widget, "Data Table")
    
    def setup_plots_tab(self):
        """Setup the plots tab with pyqtgraph."""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        
        # Plot controls
        controls_layout = QHBoxLayout()
        
        self.x_axis_combo = pg.ComboBox()
        self.x_axis_combo.setItems(['time_s', 'potential_v', 'segment_number'])
        controls_layout.addWidget(QLabel("X-Axis:"))
        controls_layout.addWidget(self.x_axis_combo)
        
        self.y_axis_combo = pg.ComboBox()
        self.y_axis_combo.setItems(['current_a', 'potential_v', 'impedance_real_ohm', 'impedance_imag_ohm'])
        controls_layout.addWidget(QLabel("Y-Axis:"))
        controls_layout.addWidget(self.y_axis_combo)
        
        controls_layout.addStretch()
        
        self.plot_btn = QPushButton("Generate Plot")
        self.plot_btn.clicked.connect(self.generate_plot)
        self.plot_btn.setEnabled(False)
        controls_layout.addWidget(self.plot_btn)
        
        self.clear_plot_btn = QPushButton("Clear")
        self.clear_plot_btn.clicked.connect(self.clear_plot)
        controls_layout.addWidget(self.clear_plot_btn)
        
        layout.addLayout(controls_layout)
        
        # Plot widget with improved settings
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Y Axis')
        self.plot_widget.setLabel('bottom', 'X Axis')
        self.plot_widget.showGrid(x=True, y=True)
        
        # Enable zooming and panning
        self.plot_widget.setMouseEnabled(x=True, y=True)
        self.plot_widget.enableAutoRange()
        
        # Add crosshair
        vLine = pg.InfiniteLine(angle=90, movable=False)
        hLine = pg.InfiniteLine(angle=0, movable=False)
        self.plot_widget.addItem(vLine, ignoreBounds=True)
        self.plot_widget.addItem(hLine, ignoreBounds=True)
        
        def mouseMoved(evt):
            pos = evt[0]
            if self.plot_widget.sceneBoundingRect().contains(pos):
                mousePoint = self.plot_widget.plotItem.vb.mapSceneToView(pos)
                vLine.setPos(mousePoint.x())
                hLine.setPos(mousePoint.y())
        
        self.plot_widget.scene().sigMouseMoved.connect(mouseMoved)
        
        layout.addWidget(self.plot_widget)
        
        # Plot info
        self.plot_info = QLabel("No plot generated")
        self.plot_info.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.plot_info)
        
        self.tabs.addTab(tab_widget, "Plots")
    
    def setup_analysis_tab(self):
        """Setup the analysis results tab."""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        
        # Analysis results
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setPlainText("No analysis results available.")
        layout.addWidget(self.analysis_text)
        
        self.tabs.addTab(tab_widget, "Analysis")
    
    def set_active_cell(self, cell_id, cell_name):
        """Set the active cell and refresh data."""
        self.active_cell_id = cell_id
        self.active_cell_name = cell_name
        
        self.data_status.setText(f"Active cell: {cell_name}")
        
        # Clear all displays when cell changes
        self.clear_file_display()
        self.analysis_text.clear()
    
    def show_file_data(self, file_id):
        """Display comprehensive data for a specific file."""
        if not file_id:
            return
        
        self.current_file_id = file_id
        
        # Get file preview data
        result = self.api.get_file_data_preview(file_id, n_rows=1000)
        
        if result['success']:
            preview_df = result['preview_data']
            stats = result['stats']
            self.current_data = preview_df
            
            # Update file overview tab
            self.update_file_overview(file_id, stats)
            
            # Update data table
            self.table_model.setDataFrame(preview_df)
            self.rows_label.setText(f"Showing {len(preview_df):,} of {stats['total_rows']:,} rows")
            self.export_btn.setEnabled(True)
            self.plot_btn.setEnabled(True)
            
            # Update data status
            self.data_status.setText(
                f"File data: {stats['total_rows']:,} rows, "
                f"{stats['total_columns']} columns, "
                f"Time: {stats['time_range']['min']:.1f}-{stats['time_range']['max']:.1f}s"
            )
            
            # Update plot axis options based on available columns
            self.update_plot_options(stats['columns'])
            
            # Switch to file overview tab
            self.tabs.setCurrentIndex(0)
        else:
            self.data_status.setText(f"Error loading file data: {result['error']}")
            self.clear_file_display()
    
    def update_file_overview(self, file_id, stats):
        """Update the file overview tab with comprehensive information."""
        # Get file metadata from database
        # For now, use placeholder data
        
        # File metadata
        self.file_name_label.setText(f"File ID: {file_id}")
        self.file_type_label.setText("Battery Data (.par/.csv)")
        self.upload_time_label.setText("Recent")
        self.processing_status_label.setText("Completed")
        self.temperature_label.setText("25°C")
        
        # Data statistics
        self.total_rows_label.setText(f"{stats['total_rows']:,}")
        self.total_columns_label.setText(f"{stats['total_columns']}")
        
        time_range = stats.get('time_range', {})
        if time_range.get('min') is not None and time_range.get('max') is not None:
            duration = time_range['max'] - time_range['min']
            self.time_range_label.setText(f"{time_range['min']:.1f} - {time_range['max']:.1f}s ({duration:.1f}s duration)")
        else:
            self.time_range_label.setText("N/A")
        
        # Estimate data size (rough calculation)
        estimated_size = stats['total_rows'] * stats['total_columns'] * 8  # 8 bytes per float
        if estimated_size > 1024*1024:
            size_str = f"{estimated_size / (1024*1024):.1f} MB"
        elif estimated_size > 1024:
            size_str = f"{estimated_size / 1024:.1f} KB"
        else:
            size_str = f"{estimated_size} bytes"
        self.data_size_label.setText(size_str)
        
        # Update techniques tree
        self.techniques_tree.clear()
        techniques = stats.get('techniques', [])
        if techniques:
            for technique in techniques:
                item = QTreeWidgetItem([technique, "N/A", "N/A", "N/A"])
                self.techniques_tree.addTopLevelItem(item)
        else:
            item = QTreeWidgetItem(["No technique information available", "", "", ""])
            self.techniques_tree.addTopLevelItem(item)
        
        # Update columns tree
        self.columns_tree.clear()
        columns = stats.get('columns', [])
        data_types = stats.get('data_types', {})
        
        for col in columns:
            dtype = data_types.get(col, "Unknown")
            # For now, show placeholder min/max values
            item = QTreeWidgetItem([col, dtype, "N/A", "N/A", self.get_column_units(col)])
            self.columns_tree.addTopLevelItem(item)
    
    def get_column_units(self, column_name):
        """Get units for column based on name."""
        unit_map = {
            'time_s': 's',
            'potential_v': 'V',
            'current_a': 'A',
            'frequency_hz': 'Hz',
            'impedance_real_ohm': 'Ω',
            'impedance_imag_ohm': 'Ω',
            'impedance_mag_ohm': 'Ω',
            'impedance_phase_deg': '°',
            'temperature_c': '°C',
            'power_w': 'W',
            'charge_capacity_ah': 'Ah',
            'energy_wh': 'Wh'
        }
        return unit_map.get(column_name, '')
    
    def update_plot_options(self, available_columns):
        """Update plot axis options based on available columns."""
        # Filter common columns for plotting
        x_options = [col for col in ['time_s', 'potential_v', 'segment_number', 'point_number'] if col in available_columns]
        y_options = [col for col in ['current_a', 'potential_v', 'impedance_real_ohm', 'impedance_imag_ohm', 'power_w'] if col in available_columns]
        
        if x_options:
            self.x_axis_combo.setItems(x_options)
        if y_options:
            self.y_axis_combo.setItems(y_options)
    
    def clear_file_display(self):
        """Clear all file-related displays."""
        self.current_file_id = None
        self.current_data = None
        
        # Clear overview
        self.file_name_label.setText("No file selected")
        self.file_type_label.setText("-")
        self.upload_time_label.setText("-")
        self.processing_status_label.setText("-")
        self.temperature_label.setText("-")
        
        self.total_rows_label.setText("-")
        self.total_columns_label.setText("-")
        self.time_range_label.setText("-")
        self.data_size_label.setText("-")
        
        self.techniques_tree.clear()
        self.columns_tree.clear()
        
        # Clear table
        self.table_model.setDataFrame(pd.DataFrame())
        self.rows_label.setText("Showing 0 rows")
        self.export_btn.setEnabled(False)
        self.plot_btn.setEnabled(False)
        
        # Clear plot
        self.plot_widget.clear()
        self.plot_info.setText("No plot generated")
    
    def show_group_analysis(self, group_id):
        """Display analysis results for a group."""
        # TODO: Implement group analysis display
        self.analysis_text.setPlainText(f"Group analysis for group ID: {group_id}")
        self.tabs.setCurrentIndex(2)  # Switch to analysis tab
    
    def generate_plot(self):
        """Generate a plot based on current data and axis selection."""
        if self.current_data is None or self.current_data.empty:
            self.plot_info.setText("No data available for plotting")
            return
        
        try:
            # Get selected axes
            x_col = self.x_axis_combo.value()
            y_col = self.y_axis_combo.value()
            
            if x_col not in self.current_data.columns or y_col not in self.current_data.columns:
                self.plot_info.setText(f"Selected columns not available: {x_col}, {y_col}")
                return
            
            # Get data for plotting
            x_data = self.current_data[x_col].dropna()
            y_data = self.current_data[y_col].dropna()
            
            # Ensure same length
            min_len = min(len(x_data), len(y_data))
            x_data = x_data.iloc[:min_len]
            y_data = y_data.iloc[:min_len]
            
            if len(x_data) == 0:
                self.plot_info.setText("No valid data points for plotting")
                return
            
            # Clear previous plot
            self.plot_widget.clear()
            
            # Create plot
            pen = pg.mkPen(color='b', width=1)
            
            # For large datasets, use downsampling
            if len(x_data) > 10000:
                # Downsample to 10000 points
                step = len(x_data) // 10000
                x_data = x_data.iloc[::step]
                y_data = y_data.iloc[::step]
                pen = pg.mkPen(color='b', width=1)
                symbol = None
            else:
                symbol = 'o' if len(x_data) < 1000 else None
            
            # Plot data
            self.plot_widget.plot(
                x_data.values, y_data.values, 
                pen=pen, symbol=symbol, symbolSize=2
            )
            
            # Set labels with units
            x_units = self.get_column_units(x_col)
            y_units = self.get_column_units(y_col)
            
            self.plot_widget.setLabel('bottom', f"{x_col} ({x_units})" if x_units else x_col)
            self.plot_widget.setLabel('left', f"{y_col} ({y_units})" if y_units else y_col)
            self.plot_widget.setTitle(f"{y_col} vs {x_col}")
            
            # Update plot info
            self.plot_info.setText(f"Plotted {len(x_data):,} points: {y_col} vs {x_col}")
            
            # Switch to plots tab
            self.tabs.setCurrentIndex(2)
            
        except Exception as e:
            self.plot_info.setText(f"Error generating plot: {str(e)}")
    
    def clear_plot(self):
        """Clear the current plot."""
        self.plot_widget.clear()
        self.plot_info.setText("Plot cleared")