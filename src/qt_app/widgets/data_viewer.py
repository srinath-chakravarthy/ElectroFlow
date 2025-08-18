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
    QLabel, QPushButton, QSplitter, QTextEdit
)
from PySide6.QtCore import Qt, Signal
import pyqtgraph as pg
import pandas as pd


class DataViewerWidget(QWidget):
    """Central widget for data visualization and analysis."""
    
    # Signals
    segments_selected = Signal(list)  # List of segment IDs for grouping
    
    def __init__(self, backend_api, parent=None):
        super().__init__(parent)
        self.api = backend_api
        self.active_cell_id = None
        self.active_cell_name = ""
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Create tab widget for different views
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Tab 1: Data Table
        self.setup_data_table_tab()
        
        # Tab 2: Plots
        self.setup_plots_tab()
        
        # Tab 3: Analysis
        self.setup_analysis_tab()
    
    def setup_data_table_tab(self):
        """Setup the data table tab."""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        
        # Table view
        self.data_table = QTableView()
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
        
        self.plot_type_combo = pg.ComboBox()
        self.plot_type_combo.setItems(['Time Series', 'IV Curve', 'Nyquist Plot'])
        controls_layout.addWidget(QLabel("Plot Type:"))
        controls_layout.addWidget(self.plot_type_combo)
        
        controls_layout.addStretch()
        
        self.plot_btn = QPushButton("Generate Plot")
        self.plot_btn.clicked.connect(self.generate_plot)
        controls_layout.addWidget(self.plot_btn)
        
        layout.addLayout(controls_layout)
        
        # Plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Y Axis')
        self.plot_widget.setLabel('bottom', 'X Axis')
        self.plot_widget.showGrid(x=True, y=True)
        layout.addWidget(self.plot_widget)
        
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
        
        # Clear current data
        self.plot_widget.clear()
        self.analysis_text.clear()
    
    def show_file_data(self, file_id):
        """Display data for a specific file."""
        if not file_id:
            return
        
        # Get file preview data
        result = self.api.get_file_data_preview(file_id, n_rows=1000)
        
        if result['success']:
            preview_df = result['preview_data']
            stats = result['stats']
            
            # Update data status
            self.data_status.setText(
                f"File data: {stats['total_rows']:,} rows, "
                f"{stats['total_columns']} columns, "
                f"Time: {stats['time_range']['min']:.1f}-{stats['time_range']['max']:.1f}s"
            )
            
            # TODO: Implement proper table model for large data
            # For now, just show basic info
            self.analysis_text.setPlainText(f"File Statistics:\n{str(stats)}")
            
            # Switch to data table tab
            self.tabs.setCurrentIndex(0)
        else:
            self.data_status.setText(f"Error loading file data: {result['error']}")
    
    def show_group_analysis(self, group_id):
        """Display analysis results for a group."""
        # TODO: Implement group analysis display
        self.analysis_text.setPlainText(f"Group analysis for group ID: {group_id}")
        self.tabs.setCurrentIndex(2)  # Switch to analysis tab
    
    def generate_plot(self):
        """Generate a plot based on current selection."""
        if not self.active_cell_id:
            return
        
        # TODO: Implement actual plotting based on data
        # For now, create a sample plot
        import numpy as np
        
        x = np.linspace(0, 10, 100)
        y = np.sin(x) + np.random.normal(0, 0.1, 100)
        
        self.plot_widget.clear()
        self.plot_widget.plot(x, y, pen='b', symbol='o', symbolSize=3)
        self.plot_widget.setLabel('left', 'Current (A)')
        self.plot_widget.setLabel('bottom', 'Time (s)')
        self.plot_widget.setTitle('Sample Data Plot')
        
        # Switch to plots tab
        self.tabs.setCurrentIndex(1)