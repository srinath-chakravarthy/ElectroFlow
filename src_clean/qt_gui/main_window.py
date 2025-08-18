"""
Clean Qt Main Window - Electrochemical Analysis Suite

Minimal, clean Qt interface with proper separation from backend.

Key Principles:
- No direct database access (use backend API only)
- Clean error handling with user-friendly messages
- Minimal interface focused on core workflow
- Proper threading for file operations
"""

import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
    QWidget, QSplitter, QGroupBox, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QMessageBox, QProgressBar, QTextEdit,
    QMenuBar, QStatusBar, QFileDialog, QTabWidget
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QFont, QAction

# Import pyqtgraph for plotting
try:
    import pyqtgraph as pg
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src_clean.backend import get_backend_api, ProcessingResult
from src_clean.core.exceptions import format_error_for_user

logger = logging.getLogger(__name__)


class FileProcessingThread(QThread):
    """Background thread for file processing."""
    
    processing_completed = Signal(dict)  # Processing results
    progress_updated = Signal(str)  # Status message
    
    def __init__(self, api, metadata_path: Path, data_path: Path, cell_name: str):
        super().__init__()
        self.api = api
        self.metadata_path = metadata_path
        self.data_path = data_path
        self.cell_name = cell_name
    
    def run(self):
        """Process files in background."""
        try:
            self.progress_updated.emit("Processing files...")
            
            result = self.api.process_dual_files(
                self.metadata_path, 
                self.data_path, 
                self.cell_name,
                temperature_c=25.0
            )
            
            self.processing_completed.emit({
                'success': result.success,
                'message': result.message,
                'error': result.error,
                'file_id': result.file_id
            })
            
        except Exception as e:
            error_info = format_error_for_user(e)
            self.processing_completed.emit({
                'success': False,
                'error': error_info['message'],
                'message': '',
                'file_id': ''
            })


class CellSelectionWidget(QWidget):
    """Widget for cell selection and creation."""
    
    cell_selected = Signal(str)  # cell_name
    
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.setup_ui()
        self.refresh_cells()
    
    def setup_ui(self):
        """Setup the cell selection UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Experimental Cells")
        header.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(header)
        
        # Cell list
        self.cell_list = QListWidget()
        self.cell_list.itemClicked.connect(self.on_cell_selected)
        layout.addWidget(self.cell_list)
        
        # Cell operations buttons
        button_layout = QHBoxLayout()
        
        self.new_cell_btn = QPushButton("New Cell")
        self.new_cell_btn.clicked.connect(self.create_new_cell)
        button_layout.addWidget(self.new_cell_btn)
        
        self.delete_cell_btn = QPushButton("Delete Cell")
        self.delete_cell_btn.clicked.connect(self.delete_selected_cell)
        self.delete_cell_btn.setEnabled(False)
        self.delete_cell_btn.setStyleSheet("QPushButton { color: red; }")
        button_layout.addWidget(self.delete_cell_btn)
        
        layout.addLayout(button_layout)
        
        # Utility buttons
        util_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_cells)
        util_layout.addWidget(self.refresh_btn)
        
        util_layout.addStretch()
        
        layout.addLayout(util_layout)
    
    def refresh_cells(self):
        """Refresh the cell list."""
        try:
            self.cell_list.clear()
            cells = self.api.get_cells()
            
            for cell in cells:
                item_text = f"{cell['name']} ({cell['file_count']} files)"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, cell['name'])
                self.cell_list.addItem(item)
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load cells: {str(e)}")
    
    def on_cell_selected(self, item: QListWidgetItem):
        """Handle cell selection."""
        cell_name = item.data(Qt.UserRole)
        if cell_name:
            self.cell_selected.emit(cell_name)
            # Enable delete button when cell is selected
            self.delete_cell_btn.setEnabled(True)
        else:
            self.delete_cell_btn.setEnabled(False)
    
    def create_new_cell(self):
        """Create new cell with simple dialog."""
        from PySide6.QtWidgets import QInputDialog
        
        cell_name, ok = QInputDialog.getText(
            self, "New Cell", "Enter cell name:"
        )
        
        if ok and cell_name.strip():
            try:
                result = self.api.create_cell(cell_name.strip())
                if result.success:
                    self.refresh_cells()
                    QMessageBox.information(self, "Success", result.message)
                else:
                    QMessageBox.warning(self, "Error", result.error)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create cell: {str(e)}")
    
    def delete_selected_cell(self):
        """Delete the currently selected cell."""
        current_item = self.cell_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a cell to delete.")
            return
        
        cell_name = current_item.data(Qt.UserRole)
        if not cell_name:
            return
        
        # Confirmation dialog with detailed warning
        reply = QMessageBox.question(
            self, "Confirm Cell Deletion",
            f"Are you sure you want to delete cell '{cell_name}'?\n\n"
            f"⚠️  This will permanently remove:\n"
            f"• All files associated with this cell\n"
            f"• All processed data and parquet files\n"
            f"• All experimental segments and analysis\n"
            f"• All metadata and notes\n\n"
            f"🚨 THIS ACTION CANNOT BE UNDONE!\n\n"
            f"Type the cell name to confirm deletion:",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Additional confirmation - require typing cell name
            from PySide6.QtWidgets import QInputDialog
            
            confirmation_name, ok = QInputDialog.getText(
                self, "Final Confirmation",
                f"Type '{cell_name}' exactly to confirm deletion:"
            )
            
            if ok and confirmation_name == cell_name:
                try:
                    # Delete cell through API (should implement cascade delete)
                    success = self.api.delete_cell(cell_name)
                    if success:
                        QMessageBox.information(
                            self, "Success", 
                            f"Cell '{cell_name}' and all associated data has been deleted."
                        )
                        # Refresh the cell list
                        self.refresh_cells()
                        # Disable delete button
                        self.delete_cell_btn.setEnabled(False)
                        # Emit empty cell selection to clear other widgets
                        self.cell_selected.emit("")
                    else:
                        QMessageBox.warning(self, "Error", f"Failed to delete cell '{cell_name}'.")
                        
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Error deleting cell: {str(e)}")
            elif ok:
                QMessageBox.information(
                    self, "Cancelled", 
                    "Cell name did not match. Deletion cancelled for safety."
                )


class FileUploadWidget(QWidget):
    """Widget for file upload and processing."""
    
    file_processed = Signal(str)  # file_id
    
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.current_cell = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the file upload UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("File Processing")
        header.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(header)
        
        # Cell info
        self.cell_info = QLabel("No cell selected")
        layout.addWidget(self.cell_info)
        
        # File selection
        file_group = QGroupBox("Select Files")
        file_layout = QVBoxLayout(file_group)
        
        # PAR file
        par_layout = QHBoxLayout()
        self.par_label = QLabel("No .par file selected")
        self.par_btn = QPushButton("Browse .par")
        self.par_btn.clicked.connect(self.browse_par_file)
        par_layout.addWidget(self.par_label)
        par_layout.addWidget(self.par_btn)
        file_layout.addLayout(par_layout)
        
        # CSV file
        csv_layout = QHBoxLayout()
        self.csv_label = QLabel("No .par.csv file selected")
        self.csv_btn = QPushButton("Browse .par.csv")
        self.csv_btn.clicked.connect(self.browse_csv_file)
        csv_layout.addWidget(self.csv_label)
        csv_layout.addWidget(self.csv_btn)
        file_layout.addLayout(csv_layout)
        
        layout.addWidget(file_group)
        
        # Process button
        self.process_btn = QPushButton("Process Files")
        self.process_btn.clicked.connect(self.process_files)
        self.process_btn.setEnabled(False)
        layout.addWidget(self.process_btn)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Initialize paths
        self.par_path = None
        self.csv_path = None
    
    def set_current_cell(self, cell_name: str):
        """Set the current cell for processing."""
        self.current_cell = cell_name
        self.cell_info.setText(f"Current cell: {cell_name}")
        self.update_process_button()
    
    def browse_par_file(self):
        """Browse for .par file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select .par file", "", "PAR files (*.par);;All files (*)"
        )
        
        if file_path:
            self.par_path = Path(file_path)
            self.par_label.setText(f"Selected: {self.par_path.name}")
            self.update_process_button()
    
    def browse_csv_file(self):
        """Browse for .par.csv file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select .par.csv file", "", "CSV files (*.csv *.par.csv);;All files (*)"
        )
        
        if file_path:
            self.csv_path = Path(file_path)
            self.csv_label.setText(f"Selected: {self.csv_path.name}")
            self.update_process_button()
    
    def update_process_button(self):
        """Update process button state."""
        enabled = (self.current_cell is not None and 
                  self.par_path is not None and 
                  self.csv_path is not None)
        self.process_btn.setEnabled(enabled)
    
    def process_files(self):
        """Process selected files."""
        if not all([self.current_cell, self.par_path, self.csv_path]):
            QMessageBox.warning(self, "Error", "Please select cell and files first")
            return
        
        # Validate files exist
        if not self.par_path.exists():
            QMessageBox.warning(self, "Error", f"PAR file not found: {self.par_path}")
            return
        
        if not self.csv_path.exists():
            QMessageBox.warning(self, "Error", f"CSV file not found: {self.csv_path}")
            return
        
        # Start processing in background
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.process_btn.setEnabled(False)
        self.status_label.setText("Processing...")
        
        self.processing_thread = FileProcessingThread(
            self.api, self.par_path, self.csv_path, self.current_cell
        )
        self.processing_thread.processing_completed.connect(self.on_processing_completed)
        self.processing_thread.progress_updated.connect(self.status_label.setText)
        self.processing_thread.start()
    
    def on_processing_completed(self, result: Dict[str, Any]):
        """Handle processing completion."""
        self.progress_bar.setVisible(False)
        self.process_btn.setEnabled(True)
        
        if result['success']:
            self.status_label.setText("✅ Processing complete")
            QMessageBox.information(
                self, "Success", 
                f"Files processed successfully!\n\n{result['message']}"
            )
            self.file_processed.emit(result['file_id'])
            
            # Clear selections for next upload
            self.par_path = None
            self.csv_path = None
            self.par_label.setText("No .par file selected")
            self.csv_label.setText("No .par.csv file selected")
            self.update_process_button()
        else:
            self.status_label.setText("❌ Processing failed")
            QMessageBox.critical(
                self, "Processing Failed", 
                f"Error: {result['error']}"
            )


class DataPreviewWidget(QWidget):
    """Widget for data preview with basic plotting."""
    
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.current_data = None
        self.current_file_id = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the data preview UI."""
        layout = QVBoxLayout(self)
        
        # Header with plot button
        header_layout = QHBoxLayout()
        header = QLabel("Data Preview")
        header.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.plot_btn = QPushButton("Plot Data")
        self.plot_btn.clicked.connect(self.plot_data)
        self.plot_btn.setEnabled(False)
        header_layout.addWidget(self.plot_btn)
        
        layout.addLayout(header_layout)
        
        # Data info
        self.data_info = QTextEdit()
        self.data_info.setMaximumHeight(120)
        self.data_info.setReadOnly(True)
        self.data_info.setPlaceholderText("Select a file to preview data...")
        layout.addWidget(self.data_info)
        
        # Plot area
        if PYQTGRAPH_AVAILABLE:
            # Create plot widget
            self.plot_widget = pg.PlotWidget()
            self.plot_widget.setLabel('left', 'Value')
            self.plot_widget.setLabel('bottom', 'Time (s)')
            self.plot_widget.setTitle('Data Preview')
            self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
            self.plot_widget.setMinimumHeight(300)
            layout.addWidget(self.plot_widget)
            
            # Plot controls
            plot_controls = QHBoxLayout()
            
            self.plot_potential_btn = QPushButton("Potential vs Time")
            self.plot_potential_btn.clicked.connect(lambda: self.plot_column('potential_v', 'Potential (V)'))
            self.plot_potential_btn.setEnabled(False)
            plot_controls.addWidget(self.plot_potential_btn)
            
            self.plot_current_btn = QPushButton("Current vs Time")
            self.plot_current_btn.clicked.connect(lambda: self.plot_column('current_a', 'Current (A)'))
            self.plot_current_btn.setEnabled(False)
            plot_controls.addWidget(self.plot_current_btn)
            
            self.plot_power_btn = QPushButton("Power vs Time")
            self.plot_power_btn.clicked.connect(lambda: self.plot_column('power_w', 'Power (W)'))
            self.plot_power_btn.setEnabled(False)
            plot_controls.addWidget(self.plot_power_btn)
            
            plot_controls.addStretch()
            
            self.clear_plot_btn = QPushButton("Clear Plot")
            self.clear_plot_btn.clicked.connect(self.clear_plot)
            self.clear_plot_btn.setEnabled(False)
            plot_controls.addWidget(self.clear_plot_btn)
            
            layout.addLayout(plot_controls)
        else:
            # Fallback if pyqtgraph not available
            no_plot_label = QLabel("PyQtGraph not available - install for plotting functionality")
            no_plot_label.setStyleSheet("color: orange; font-style: italic;")
            layout.addWidget(no_plot_label)
    
    def set_file_for_preview(self, file_id: str):
        """Set file for data preview."""
        self.current_file_id = file_id
        if file_id:  # Only load if file_id is not empty
            self.load_data_preview()
        else:
            # Clear preview when file_id is empty (e.g., after deletion)
            self.clear_preview()
    
    def load_data_preview(self):
        """Load data preview for current file."""
        if not self.current_file_id:
            return
        
        try:
            # Get file data (limited to first 10000 rows for preview)
            data = self.api.get_file_data(self.current_file_id)
            
            if data is None:
                self.data_info.setText(f"❌ Could not load data for file: {self.current_file_id}")
                self.current_data = None
                self.update_button_states()
                return
            
            # Store data and show info
            self.current_data = data.head(10000)  # Limit for performance
            
            # Generate summary
            summary_lines = [
                f"📄 File ID: {self.current_file_id}",
                f"📊 Data Points: {data.height:,} (showing first {min(10000, data.height):,})",
                f"📈 Columns: {data.width}",
                f"⏱️ Time Range: {data['time_s'].min():.1f} - {data['time_s'].max():.1f} seconds",
                ""
            ]
            
            # Check available columns
            available_cols = []
            if 'potential_v' in data.columns:
                potential_range = f"{data['potential_v'].min():.3f} to {data['potential_v'].max():.3f} V"
                available_cols.append(f"• Potential: {potential_range}")
            
            if 'current_a' in data.columns:
                current_range = f"{data['current_a'].min():.6f} to {data['current_a'].max():.6f} A"
                available_cols.append(f"• Current: {current_range}")
            
            if 'power_w' in data.columns:
                power_range = f"{data['power_w'].min():.6f} to {data['power_w'].max():.6f} W"
                available_cols.append(f"• Power: {power_range}")
            
            if 'technique_id' in data.columns:
                techniques = data['technique_id'].unique().drop_nulls().to_list()
                available_cols.append(f"• Techniques: {len(techniques)} unique ActionIDs")
            
            summary_lines.extend(available_cols)
            self.data_info.setText("\n".join(summary_lines))
            
            self.update_button_states()
            
        except Exception as e:
            self.data_info.setText(f"❌ Error loading data: {str(e)}")
            self.current_data = None
            self.update_button_states()
    
    def update_button_states(self):
        """Update button states based on available data."""
        has_data = self.current_data is not None
        
        self.plot_btn.setEnabled(has_data)
        
        if PYQTGRAPH_AVAILABLE and has_data:
            columns = self.current_data.columns
            self.plot_potential_btn.setEnabled('potential_v' in columns)
            self.plot_current_btn.setEnabled('current_a' in columns)
            self.plot_power_btn.setEnabled('power_w' in columns)
            self.clear_plot_btn.setEnabled(True)
        elif PYQTGRAPH_AVAILABLE:
            self.plot_potential_btn.setEnabled(False)
            self.plot_current_btn.setEnabled(False)
            self.plot_power_btn.setEnabled(False)
            self.clear_plot_btn.setEnabled(False)
    
    def clear_preview(self):
        """Clear the data preview."""
        self.current_data = None
        self.current_file_id = None
        self.data_info.clear()
        self.data_info.setPlaceholderText("Select a file to preview data...")
        self.update_button_states()
        if PYQTGRAPH_AVAILABLE:
            self.clear_plot()
    
    def plot_data(self):
        """Plot basic overview of data."""
        if not PYQTGRAPH_AVAILABLE or self.current_data is None:
            return
        
        # Default to potential vs time if available
        if 'potential_v' in self.current_data.columns:
            self.plot_column('potential_v', 'Potential (V)')
        elif 'current_a' in self.current_data.columns:
            self.plot_column('current_a', 'Current (A)')
        else:
            QMessageBox.information(self, "Info", "No suitable columns found for plotting")
    
    def plot_column(self, column: str, label: str):
        """Plot specific column vs time."""
        if not PYQTGRAPH_AVAILABLE or self.current_data is None:
            return
        
        if column not in self.current_data.columns or 'time_s' not in self.current_data.columns:
            QMessageBox.warning(self, "Error", f"Column '{column}' or 'time_s' not found in data")
            return
        
        try:
            # Convert to pandas for plotting
            df = self.current_data.to_pandas()
            
            # Clear previous plot
            self.plot_widget.clear()
            
            # Plot data
            time_data = df['time_s'].values
            y_data = df[column].values
            
            # Use different colors for different plots
            colors = {'potential_v': 'b', 'current_a': 'r', 'power_w': 'm'}
            color = colors.get(column, 'g')
            
            self.plot_widget.plot(time_data, y_data, pen=pg.mkPen(color, width=1))
            self.plot_widget.setLabel('left', label)
            self.plot_widget.setLabel('bottom', 'Time (s)')
            self.plot_widget.setTitle(f'{label} vs Time - {self.current_file_id}')
            
        except Exception as e:
            QMessageBox.critical(self, "Plot Error", f"Failed to plot data: {str(e)}")
    
    def clear_plot(self):
        """Clear the plot."""
        if PYQTGRAPH_AVAILABLE:
            self.plot_widget.clear()
            self.plot_widget.setTitle('Data Preview')


class FileListWidget(QWidget):
    """Widget to display files for current cell."""
    
    file_selected = Signal(str)  # file_id
    
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.current_cell = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the file list UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Cell Files")
        header.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(header)
        
        # File list
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.on_file_selected)
        layout.addWidget(self.file_list)
        
        # File operations buttons
        file_ops_layout = QHBoxLayout()
        
        self.delete_file_btn = QPushButton("Delete File")
        self.delete_file_btn.clicked.connect(self.delete_selected_file)
        self.delete_file_btn.setEnabled(False)
        self.delete_file_btn.setStyleSheet("QPushButton { color: red; }")
        file_ops_layout.addWidget(self.delete_file_btn)
        
        file_ops_layout.addStretch()
        
        self.refresh_files_btn = QPushButton("Refresh")
        self.refresh_files_btn.clicked.connect(self.refresh_files)
        file_ops_layout.addWidget(self.refresh_files_btn)
        
        layout.addLayout(file_ops_layout)
        
        # File info
        self.file_info = QTextEdit()
        self.file_info.setMaximumHeight(100)
        self.file_info.setReadOnly(True)
        layout.addWidget(self.file_info)
    
    def on_file_selected(self, item: QListWidgetItem):
        """Handle file selection."""
        file_info = item.data(Qt.UserRole)
        if file_info:
            file_id = file_info['file_id']
            self.file_selected.emit(file_id)
            # Enable delete button when file is selected
            self.delete_file_btn.setEnabled(True)
        else:
            self.delete_file_btn.setEnabled(False)
    
    def delete_selected_file(self):
        """Delete the currently selected file."""
        current_item = self.file_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a file to delete.")
            return
        
        file_info = current_item.data(Qt.UserRole)
        if not file_info:
            return
        
        file_id = file_info['file_id']
        filename = file_info['original_filename']
        
        # Confirmation dialog
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete '{filename}'?\n\n"
            f"This will permanently remove:\n"
            f"• File data and metadata\n"
            f"• All associated segments\n"
            f"• Any analysis results\n\n"
            f"This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Delete file through API
                success = self.api.delete_file(file_id)
                if success:
                    QMessageBox.information(self, "Success", f"File '{filename}' has been deleted.")
                    # Refresh the file list
                    self.refresh_files()
                    # Disable delete button
                    self.delete_file_btn.setEnabled(False)
                    # Clear data preview if this file was selected
                    self.file_selected.emit("")  # Emit empty to clear preview
                else:
                    QMessageBox.warning(self, "Error", f"Failed to delete file '{filename}'.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error deleting file: {str(e)}")
    
    def set_current_cell(self, cell_name: str):
        """Set current cell and refresh file list."""
        self.current_cell = cell_name
        self.refresh_files()
    
    def refresh_files(self):
        """Refresh file list for current cell."""
        self.file_list.clear()
        self.file_info.clear()
        
        if not self.current_cell:
            return
        
        try:
            files = self.api.get_cell_files(self.current_cell)
            
            for file_info in files:
                item_text = f"{file_info['original_filename']} ({file_info['segment_count']} segments)"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, file_info)
                self.file_list.addItem(item)
            
            if files:
                self.file_info.setText(f"Total files: {len(files)}")
            else:
                self.file_info.setText("No files found for this cell")
                
        except Exception as e:
            self.file_info.setText(f"Error loading files: {str(e)}")


class ElectrochemicalMainWindow(QMainWindow):
    """Clean main window for electrochemical analysis."""
    
    def __init__(self):
        super().__init__()
        self.api = get_backend_api()
        self.setup_ui()
        self.setup_connections()
        
        # Set window properties
        self.setWindowTitle("Electrochemical Analysis Suite")
        self.resize(1400, 900)  # Larger window for data preview
    
    def setup_ui(self):
        """Setup the main UI."""
        # Central widget with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QHBoxLayout(central_widget)
        main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(main_splitter)
        
        # Left panel - Cell selection
        self.cell_widget = CellSelectionWidget(self.api)
        self.cell_widget.setMaximumWidth(300)
        main_splitter.addWidget(self.cell_widget)
        
        # Middle panel - File upload
        self.upload_widget = FileUploadWidget(self.api)
        self.upload_widget.setMaximumWidth(400)
        main_splitter.addWidget(self.upload_widget)
        
        # Right panel - Combined file list and data preview
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Create right-side splitter (vertical)
        right_splitter = QSplitter(Qt.Vertical)
        right_layout.addWidget(right_splitter)
        
        # File list (top half)
        self.file_list_widget = FileListWidget(self.api)
        right_splitter.addWidget(self.file_list_widget)
        
        # Data preview (bottom half)
        self.data_preview_widget = DataPreviewWidget(self.api)
        right_splitter.addWidget(self.data_preview_widget)
        
        # Set right splitter proportions (file list smaller, preview larger)
        right_splitter.setSizes([200, 600])
        
        main_splitter.addWidget(right_widget)
        
        # Set main splitter proportions
        main_splitter.setSizes([250, 350, 800])
        
        # Menu bar
        self.create_menu_bar()
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def create_menu_bar(self):
        """Create menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        # Database stats action
        stats_action = QAction("Database Statistics", self)
        stats_action.triggered.connect(self.show_database_stats)
        file_menu.addAction(stats_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_connections(self):
        """Setup signal connections."""
        self.cell_widget.cell_selected.connect(self.on_cell_selected)
        self.upload_widget.file_processed.connect(self.on_file_processed)
        self.file_list_widget.file_selected.connect(self.on_file_selected)
    
    def on_cell_selected(self, cell_name: str):
        """Handle cell selection."""
        self.upload_widget.set_current_cell(cell_name)
        self.file_list_widget.set_current_cell(cell_name)
        # Clear data preview when switching cells
        self.data_preview_widget.current_data = None
        self.data_preview_widget.current_file_id = None
        self.data_preview_widget.data_info.clear()
        self.data_preview_widget.update_button_states()
        if PYQTGRAPH_AVAILABLE:
            self.data_preview_widget.clear_plot()
        self.status_bar.showMessage(f"Selected cell: {cell_name}")
    
    def on_file_processed(self, file_id: str):
        """Handle file processing completion."""
        # Refresh file list
        self.file_list_widget.refresh_files()
        self.status_bar.showMessage(f"File processed: {file_id}")
    
    def on_file_selected(self, file_id: str):
        """Handle file selection for data preview."""
        self.data_preview_widget.set_file_for_preview(file_id)
        self.status_bar.showMessage(f"Previewing data: {file_id}")
    
    def show_database_stats(self):
        """Show database statistics."""
        try:
            stats = self.api.get_database_stats()
            
            stats_text = f"""Database Statistics:

• Cells: {stats['cell_count']}
• Files: {stats['file_count']}
• Segments: {stats['segment_count']}
• User Mappings: {stats['user_mappings_count']}
• Database Size: {stats['database_size_mb']:.2f} MB
• Supported Instruments: {', '.join(stats['supported_instruments'])}

Database Location: {stats['database_path']}"""
            
            QMessageBox.information(self, "Database Statistics", stats_text)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to get statistics: {str(e)}")
    
    def show_about(self):
        """Show about dialog."""
        about_text = """Electrochemical Analysis Suite v2.0

Clean implementation with universal data processing for:
• VersaStudio (.par + .par.csv files)
• Universal 29-column schema
• Atomic database operations
• Multi-interface support (Qt, CLI, Python)

Built with Python, PySide6, Polars, and SQLite."""

        QMessageBox.about(self, "About", about_text)


def main():
    """Main entry point for Qt application."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Electrochemical Analysis Suite")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("Research Lab")
    
    # Create and show main window
    window = ElectrochemicalMainWindow()
    window.show()
    
    return app.exec()


if __name__ == '__main__':
    main()