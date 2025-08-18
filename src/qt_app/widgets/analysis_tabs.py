"""
Analysis Tabs Widget

Tabbed panel with data view, analysis, and plotting capabilities.
Supports re-running analysis on individual techniques, groups, or combinations.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableView,
    QTextEdit, QPushButton, QLabel, QComboBox, QGroupBox, QFormLayout,
    QSpinBox, QCheckBox, QSplitter, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QAbstractTableModel, QModelIndex, QThread
from PySide6.QtGui import QFont
import pyqtgraph as pg

# Add src directory to path for imports
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


class AnalysisDataModel(QAbstractTableModel):
    """Table model for analysis data display."""
    
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


class AnalysisThread(QThread):
    """Background thread for running analysis."""
    
    analysis_completed = Signal(dict)  # results
    progress_updated = Signal(str)  # status message
    
    def __init__(self, analysis_type: str, data_ids: List[str], api):
        super().__init__()
        self.analysis_type = analysis_type
        self.data_ids = data_ids
        self.api = api
    
    def run(self):
        """Run analysis in background."""
        try:
            self.progress_updated.emit(f"Running {self.analysis_type} analysis...")
            
            # TODO: Implement actual analysis via backend API
            # For now, return placeholder results
            results = {
                'success': True,
                'analysis_type': self.analysis_type,
                'data_ids': self.data_ids,
                'results': {
                    'summary': f"Analysis completed for {len(self.data_ids)} items",
                    'metrics': {
                        'average_value': 42.0,
                        'standard_deviation': 3.14,
                        'quality_score': 0.95
                    }
                }
            }
            
            self.analysis_completed.emit(results)
            
        except Exception as e:
            self.analysis_completed.emit({
                'success': False,
                'error': str(e)
            })


class DataViewTab(QWidget):
    """Tab for displaying selected data."""
    
    def __init__(self, backend_api, parent=None):
        super().__init__(parent)
        self.api = backend_api
        self.data_model = AnalysisDataModel()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the data view tab."""
        layout = QVBoxLayout(self)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.data_info_label = QLabel("No data selected")
        self.data_info_label.setFont(QFont("Arial", 10, QFont.Bold))
        controls_layout.addWidget(self.data_info_label)
        
        controls_layout.addStretch()
        
        self.export_btn = QPushButton("Export Data")
        self.export_btn.setEnabled(False)
        controls_layout.addWidget(self.export_btn)
        
        layout.addLayout(controls_layout)
        
        # Data table
        self.data_table = QTableView()
        self.data_table.setModel(self.data_model)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSortingEnabled(True)
        layout.addWidget(self.data_table)
        
        # Statistics panel
        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(100)
        self.stats_text.setReadOnly(True)
        self.stats_text.setPlaceholderText("Data statistics will appear here...")
        layout.addWidget(self.stats_text)
    
    def update_data(self, data_ids: List[str], data_type: str):
        """Update displayed data."""
        if not data_ids:
            self.clear_data()
            return
        
        self.data_info_label.setText(f"{data_type}: {len(data_ids)} items selected")
        
        # TODO: Load actual data from backend
        # For now, show placeholder
        placeholder_data = pd.DataFrame({
            'ID': data_ids[:10],  # Limit for display
            'Value': np.random.randn(min(10, len(data_ids))),
            'Status': ['OK'] * min(10, len(data_ids))
        })
        
        self.data_model.setDataFrame(placeholder_data)
        self.export_btn.setEnabled(True)
        
        # Update statistics
        stats_text = f"""
Data Summary:
- Items: {len(data_ids)}
- Type: {data_type}
- Preview rows: {len(placeholder_data)}
        """.strip()
        self.stats_text.setPlainText(stats_text)
    
    def clear_data(self):
        """Clear displayed data."""
        self.data_info_label.setText("No data selected")
        self.data_model.setDataFrame(pd.DataFrame())
        self.export_btn.setEnabled(False)
        self.stats_text.clear()


class AnalysisTab(QWidget):
    """Tab for running analysis on selected data."""
    
    def __init__(self, backend_api, parent=None):
        super().__init__(parent)
        self.api = backend_api
        self.current_data_ids = []
        self.current_data_type = ""
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the analysis tab."""
        layout = QVBoxLayout(self)
        
        # Analysis controls
        controls_group = QGroupBox("Analysis Configuration")
        controls_layout = QFormLayout(controls_group)
        
        # Analysis type selection
        self.analysis_type_combo = QComboBox()
        self.analysis_type_combo.addItems([
            "Fundamental Analysis",
            "Custom Analysis", 
            "Curve Fitting",
            "Statistical Analysis",
            "Comparative Analysis"
        ])
        controls_layout.addRow("Analysis Type:", self.analysis_type_combo)
        
        # Analysis options
        self.recompute_checkbox = QCheckBox("Recompute existing results")
        controls_layout.addRow("Options:", self.recompute_checkbox)
        
        # Run analysis button
        self.run_analysis_btn = QPushButton("Run Analysis")
        self.run_analysis_btn.clicked.connect(self.run_analysis)
        self.run_analysis_btn.setEnabled(False)
        controls_layout.addRow(self.run_analysis_btn)
        
        layout.addWidget(controls_group)
        
        # Progress and status
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Results display
        results_group = QGroupBox("Analysis Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setPlaceholderText("Analysis results will appear here...")
        results_layout.addWidget(self.results_text)
        
        layout.addWidget(results_group)
    
    def update_data(self, data_ids: List[str], data_type: str):
        """Update data for analysis."""
        self.current_data_ids = data_ids
        self.current_data_type = data_type
        
        if data_ids:
            self.run_analysis_btn.setEnabled(True)
            self.status_label.setText(f"Ready to analyze {len(data_ids)} {data_type} items")
        else:
            self.run_analysis_btn.setEnabled(False)
            self.status_label.setText("No data selected for analysis")
            self.results_text.clear()
    
    def run_analysis(self):
        """Run analysis on current data."""
        if not self.current_data_ids:
            return
        
        analysis_type = self.analysis_type_combo.currentText()
        
        self.run_analysis_btn.setEnabled(False)
        self.status_label.setText("Running analysis...")
        
        # Start analysis in background
        self.analysis_thread = AnalysisThread(
            analysis_type, self.current_data_ids, self.api
        )
        self.analysis_thread.analysis_completed.connect(self.on_analysis_completed)
        self.analysis_thread.progress_updated.connect(self.status_label.setText)
        self.analysis_thread.start()
    
    def on_analysis_completed(self, results: Dict[str, Any]):
        """Handle analysis completion."""
        self.run_analysis_btn.setEnabled(True)
        
        if results['success']:
            self.status_label.setText("Analysis completed successfully")
            
            # Display results
            analysis_results = results.get('results', {})
            summary = analysis_results.get('summary', 'No summary available')
            metrics = analysis_results.get('metrics', {})
            
            results_text = f"""
Analysis Type: {results['analysis_type']}
Data Items: {len(results['data_ids'])}

Summary:
{summary}

Metrics:
"""
            
            for key, value in metrics.items():
                results_text += f"- {key}: {value}\\n"
            
            self.results_text.setPlainText(results_text)
            
        else:
            error_msg = results.get('error', 'Unknown error')
            self.status_label.setText(f"Analysis failed: {error_msg}")
            self.results_text.setPlainText(f"Error: {error_msg}")


class PlottingTab(QWidget):
    """Tab for plotting selected data."""
    
    def __init__(self, backend_api, parent=None):
        super().__init__(parent)
        self.api = backend_api
        self.current_data_ids = []
        self.current_data_type = ""
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the plotting tab."""
        # Create splitter for controls and plot
        splitter = QSplitter(Qt.Vertical)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(splitter)
        
        # Plot controls
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        
        # Plot configuration
        config_group = QGroupBox("Plot Configuration")
        config_layout = QFormLayout(config_group)
        
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems([
            "Time Series",
            "Scatter Plot",
            "Histogram", 
            "Box Plot",
            "Comparison Plot"
        ])
        self.plot_type_combo.currentTextChanged.connect(self.update_plot)
        config_layout.addRow("Plot Type:", self.plot_type_combo)
        
        self.x_axis_combo = QComboBox()
        self.y_axis_combo = QComboBox()
        config_layout.addRow("X-Axis:", self.x_axis_combo)
        config_layout.addRow("Y-Axis:", self.y_axis_combo)
        
        # Plot options
        self.show_legend_checkbox = QCheckBox("Show Legend")
        self.show_legend_checkbox.setChecked(True)
        config_layout.addRow("Options:", self.show_legend_checkbox)
        
        # Generate plot button
        self.generate_plot_btn = QPushButton("Generate Plot")
        self.generate_plot_btn.clicked.connect(self.update_plot)
        self.generate_plot_btn.setEnabled(False)
        config_layout.addRow(self.generate_plot_btn)
        
        controls_layout.addWidget(config_group)
        controls_layout.addStretch()
        
        controls_widget.setMaximumHeight(200)
        splitter.addWidget(controls_widget)
        
        # Plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Y Axis')
        self.plot_widget.setLabel('bottom', 'X Axis')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setMouseEnabled(x=True, y=True)
        self.plot_widget.enableAutoRange()
        
        splitter.addWidget(self.plot_widget)
        
        # Set splitter proportions
        splitter.setSizes([200, 400])
    
    def update_data(self, data_ids: List[str], data_type: str):
        """Update data for plotting."""
        self.current_data_ids = data_ids
        self.current_data_type = data_type
        
        if data_ids:
            self.generate_plot_btn.setEnabled(True)
            
            # Update axis options (placeholder)
            self.x_axis_combo.clear()
            self.y_axis_combo.clear()
            
            axes = ['time_s', 'potential_v', 'current_a', 'frequency_hz']
            self.x_axis_combo.addItems(axes)
            self.y_axis_combo.addItems(axes)
            
            self.update_plot()
        else:
            self.generate_plot_btn.setEnabled(False)
            self.plot_widget.clear()
    
    def update_plot(self):
        """Update the plot with current data."""
        if not self.current_data_ids:
            return
        
        try:
            self.plot_widget.clear()
            
            # Generate sample data for plotting
            n_points = len(self.current_data_ids) * 100
            x_data = np.linspace(0, 10, n_points)
            y_data = np.sin(x_data) + np.random.normal(0, 0.1, n_points)
            
            # Plot data
            pen = pg.mkPen(color='b', width=1)
            self.plot_widget.plot(x_data, y_data, pen=pen, name=self.current_data_type)
            
            # Set labels
            x_label = self.x_axis_combo.currentText()
            y_label = self.y_axis_combo.currentText()
            self.plot_widget.setLabel('bottom', x_label)
            self.plot_widget.setLabel('left', y_label)
            
            # Set title
            plot_type = self.plot_type_combo.currentText()
            self.plot_widget.setTitle(f"{plot_type}: {len(self.current_data_ids)} items")
            
        except Exception as e:
            print(f"Error updating plot: {e}")


class AnalysisTabsWidget(QWidget):
    """Main widget with tabbed analysis interface."""
    
    def __init__(self, backend_api, parent=None):
        super().__init__(parent)
        self.api = backend_api
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the tabbed interface."""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Create tabs
        self.data_view_tab = DataViewTab(self.api)
        self.analysis_tab = AnalysisTab(self.api)
        self.plotting_tab = PlottingTab(self.api)
        
        # Add tabs
        self.tabs.addTab(self.data_view_tab, "Data View")
        self.tabs.addTab(self.analysis_tab, "Analysis")
        self.tabs.addTab(self.plotting_tab, "Plotting")
        
        layout.addWidget(self.tabs)
    
    def update_selected_data(self, data_ids: List[str], data_type: str = "segments"):
        """Update all tabs with selected data."""
        self.data_view_tab.update_data(data_ids, data_type)
        self.analysis_tab.update_data(data_ids, data_type)
        self.plotting_tab.update_data(data_ids, data_type)
    
    def update_selected_group(self, group_id: int):
        """Update tabs with selected group data."""
        # TODO: Load group data and update tabs
        self.update_selected_data([f"group_{group_id}"], "group")
    
    def clear_data(self):
        """Clear all tabs."""
        self.update_selected_data([], "none")