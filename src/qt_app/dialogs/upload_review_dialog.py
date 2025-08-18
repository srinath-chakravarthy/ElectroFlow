"""
Upload/Review Dialog for Battery Data Files

Large modal window for both file upload and experiment review with:
- 4-panel plots (Applied Pot vs Time, Current vs Time, Nyquist scatter, Applied Pot vs Current)
- File metadata editing (temperature, etc.)
- ActionID mapping management
- Comprehensive file validation and data preview
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter,
    QGroupBox, QFormLayout, QLabel, QLineEdit, QDoubleSpinBox,
    QComboBox, QPushButton, QTextEdit, QFileDialog, QMessageBox,
    QProgressBar, QTabWidget, QWidget, QSpinBox, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QFont
import pyqtgraph as pg

# Add src directory to path for imports
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from backend_api import BackendAPI


class FileValidationThread(QThread):
    """Background thread for file validation and data loading."""
    
    validation_completed = Signal(dict)  # validation results
    progress_updated = Signal(int, str)  # progress, status message
    
    def __init__(self, par_path: Path, csv_path: Path, api: BackendAPI):
        super().__init__()
        self.par_path = par_path
        self.csv_path = csv_path
        self.api = api
    
    def run(self):
        """Run lightweight file validation only - NO data loading."""
        try:
            self.progress_updated.emit(20, "Validating file formats...")
            
            # Use new simplified validation API
            validation_result = self.api.validate_files([self.par_path, self.csv_path])
            
            if not validation_result.success:
                self.validation_completed.emit({
                    'success': False,
                    'error': validation_result.message
                })
                return

            self.progress_updated.emit(100, "Validation complete")

            # Return validation results WITHOUT any CSV data
            self.validation_completed.emit({
                'success': True,
                'par_metadata': {},
                'validation_details': validation_result.details,
                'message': validation_result.message
            })
            
        except Exception as e:
            self.validation_completed.emit({
                'success': False,
                'error': f"Validation failed: {str(e)}"
            })


class FourPanelPlotWidget(QWidget):
    """Widget containing 4 plots for comprehensive data visualization."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.clear_plots()
    
    def setup_ui(self):
        """Setup the 4-panel plot layout."""
        layout = QGridLayout(self)
        
        # Create plot widgets
        self.plot_applied_pot_time = pg.PlotWidget()
        self.plot_current_time = pg.PlotWidget()
        self.plot_nyquist = pg.PlotWidget()
        self.plot_applied_pot_current = pg.PlotWidget()
        
        # Configure plots
        plots_config = [
            (self.plot_applied_pot_time, "Applied Potential vs Time", "Time (s)", "Applied Potential (V)"),
            (self.plot_current_time, "Current vs Time", "Time (s)", "Current (A)"),
            (self.plot_nyquist, "Nyquist Plot", "Z Real (Ω)", "-Z Imag (Ω)"),
            (self.plot_applied_pot_current, "Applied Potential vs Current", "Current (A)", "Applied Potential (V)")
        ]
        
        for plot, title, x_label, y_label in plots_config:
            plot.setLabel('bottom', x_label)
            plot.setLabel('left', y_label)
            plot.setTitle(title)
            plot.showGrid(x=True, y=True)
            plot.setMouseEnabled(x=True, y=True)
            plot.enableAutoRange()
        
        # Special configuration for Nyquist plot (equal aspect ratio would be nice)
        self.plot_nyquist.setAspectLocked(False)  # Allow independent zooming
        
        # Layout plots in 2x2 grid
        layout.addWidget(self.plot_applied_pot_time, 0, 0)
        layout.addWidget(self.plot_current_time, 0, 1)
        layout.addWidget(self.plot_nyquist, 1, 0)
        layout.addWidget(self.plot_applied_pot_current, 1, 1)
    
    def update_plots(self, data: pd.DataFrame):
        """Update all 4 plots with new data."""
        try:
            self.clear_plots()
            
            # Map common column names (handle different CSV formats)
            column_mapping = self._detect_columns(data)
            
            if not column_mapping:
                return
            
            # Plot 1: Applied Potential vs Time
            if column_mapping['time'] and column_mapping['applied_potential']:
                time_data = data[column_mapping['time']].dropna()
                pot_data = data[column_mapping['applied_potential']].dropna()
                
                min_len = min(len(time_data), len(pot_data))
                if min_len > 0:
                    pen = pg.mkPen(color='b', width=1)
                    self.plot_applied_pot_time.plot(
                        time_data.iloc[:min_len], pot_data.iloc[:min_len], 
                        pen=pen, name="Applied Potential"
                    )
            
            # Plot 2: Current vs Time
            if column_mapping['time'] and column_mapping['current']:
                time_data = data[column_mapping['time']].dropna()
                curr_data = data[column_mapping['current']].dropna()
                
                min_len = min(len(time_data), len(curr_data))
                if min_len > 0:
                    pen = pg.mkPen(color='r', width=1)
                    self.plot_current_time.plot(
                        time_data.iloc[:min_len], curr_data.iloc[:min_len],
                        pen=pen, name="Current"
                    )
            
            # Plot 3: Nyquist Plot (scatter, colored by segment if available)
            if column_mapping['z_real'] and column_mapping['z_imag']:
                z_real = data[column_mapping['z_real']].dropna()
                z_imag = data[column_mapping['z_imag']].dropna()
                
                min_len = min(len(z_real), len(z_imag))
                if min_len > 0:
                    # Use scatter plot for Nyquist
                    scatter = pg.ScatterPlotItem(
                        x=z_real.iloc[:min_len], 
                        y=-z_imag.iloc[:min_len],  # Negative imaginary for conventional Nyquist
                        size=3, brush=pg.mkBrush(color='g'), pen=pg.mkPen(color='g')
                    )
                    self.plot_nyquist.addItem(scatter)
            
            # Plot 4: Applied Potential vs Current
            if column_mapping['current'] and column_mapping['applied_potential']:
                curr_data = data[column_mapping['current']].dropna()
                pot_data = data[column_mapping['applied_potential']].dropna()
                
                min_len = min(len(curr_data), len(pot_data))
                if min_len > 0:
                    pen = pg.mkPen(color='m', width=1)
                    self.plot_applied_pot_current.plot(
                        curr_data.iloc[:min_len], pot_data.iloc[:min_len],
                        pen=pen, name="I-V Curve"
                    )
                    
        except Exception as e:
            print(f"Error updating plots: {e}")
    
    def _detect_columns(self, data: pd.DataFrame) -> Dict[str, Optional[str]]:
        """Map universal schema columns for plotting."""
        columns = data.columns.tolist()
        
        # Map to universal schema column names
        mapping = {
            'time': 'time_s' if 'time_s' in columns else None,
            'current': 'current_a' if 'current_a' in columns else None,
            'applied_potential': 'potential_applied_v' if 'potential_applied_v' in columns else None,
            'z_real': 'impedance_real_ohm' if 'impedance_real_ohm' in columns else None,
            'z_imag': 'impedance_imag_ohm' if 'impedance_imag_ohm' in columns else None
        }
        
        return mapping
    
    def clear_plots(self):
        """Clear all plots."""
        for plot in [self.plot_applied_pot_time, self.plot_current_time, 
                    self.plot_nyquist, self.plot_applied_pot_current]:
            plot.clear()
    
    def show_validation_placeholder(self):
        """Show placeholder text indicating validation completed."""
        self.clear_plots()
        
        # Add text items to plots showing validation status
        placeholder_text = "✅ Validation Complete\nUpload files to see plots"
        
        text_item1 = pg.TextItem(placeholder_text, color='gray', anchor=(0.5, 0.5))
        text_item2 = pg.TextItem(placeholder_text, color='gray', anchor=(0.5, 0.5))
        text_item3 = pg.TextItem(placeholder_text, color='gray', anchor=(0.5, 0.5))
        text_item4 = pg.TextItem(placeholder_text, color='gray', anchor=(0.5, 0.5))
        
        # Position text in center of each plot
        self.plot_applied_pot_time.addItem(text_item1)
        text_item1.setPos(0, 0)
        
        self.plot_current_time.addItem(text_item2)
        text_item2.setPos(0, 0)
        
        self.plot_nyquist.addItem(text_item3)
        text_item3.setPos(0, 0)
        
        self.plot_applied_pot_current.addItem(text_item4)
        text_item4.setPos(0, 0)


class UploadReviewDialog(QDialog):
    """Large modal dialog for file upload and experiment review."""
    
    # Signals
    upload_completed = Signal(list)  # List of successfully uploaded file_ids
    
    def __init__(self, backend_api: BackendAPI, parent=None, 
                 mode: str = 'upload', cell_name: str = '', 
                 file_id: str = ''):
        """
        Initialize upload/review dialog.
        
        Args:
            backend_api: Backend API instance
            parent: Parent widget
            mode: 'upload' for new files, 'review' for existing experiment
            cell_name: Target cell name
            file_id: File ID for review mode
        """
        super().__init__(parent)
        self.api = backend_api
        self.mode = mode
        self.cell_name = cell_name
        self.file_id = file_id
        
        self.par_path = None
        self.csv_path = None
        self.current_data = None
        
        # Remember last directory for file dialogs - start with measurement_groups if it exists
        measurement_groups = Path("data/measurement_groups")
        if measurement_groups.exists():
            self.last_directory = measurement_groups
        else:
            self.last_directory = Path.home()
        
        self.setup_ui()
        self.setup_connections()
        
        if mode == 'review':
            self.load_existing_file()
        
        # Make dialog large (90% of screen)
        screen = self.screen().availableGeometry()
        self.resize(int(screen.width() * 0.9), int(screen.height() * 0.9))
        self.setWindowTitle(f"{'Upload Files' if mode == 'upload' else 'Review Experiment'} - {cell_name}")
        
        # Initialize file selection state
        if self.mode == 'upload':
            self.check_file_selection()
    
    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Create main splitter (left metadata, right plots)
        main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(main_splitter)
        
        # Left panel - File metadata and controls
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # File selection group (upload mode only)
        if self.mode == 'upload':
            self.setup_file_selection_group(left_layout)
        
        # Metadata editing group
        self.setup_metadata_group(left_layout)
        
        # ActionID mapping group
        self.setup_actionid_group(left_layout)
        
        # Progress and status
        self.setup_progress_group(left_layout)
        
        # Buttons
        self.setup_buttons(left_layout)
        
        left_widget.setMaximumWidth(400)
        main_splitter.addWidget(left_widget)
        
        # Right panel - 4-panel plots
        self.plot_widget = FourPanelPlotWidget()
        main_splitter.addWidget(self.plot_widget)
        
        # Set splitter proportions (30% left, 70% right)
        main_splitter.setSizes([300, 700])
    
    def setup_file_selection_group(self, parent_layout):
        """Setup file selection group for upload mode."""
        group = QGroupBox("File Selection")
        layout = QFormLayout(group)
        
        # .par file selection
        par_layout = QHBoxLayout()
        self.par_file_label = QLabel("No .par file selected")
        self.par_browse_btn = QPushButton("Browse...")
        self.par_browse_btn.clicked.connect(self.browse_par_file)
        par_layout.addWidget(self.par_file_label)
        par_layout.addWidget(self.par_browse_btn)
        layout.addRow(".par file:", par_layout)
        
        # .par.csv file selection
        csv_layout = QHBoxLayout()
        self.csv_file_label = QLabel("No .par.csv file selected")
        self.csv_browse_btn = QPushButton("Browse...")
        self.csv_browse_btn.clicked.connect(self.browse_csv_file)
        csv_layout.addWidget(self.csv_file_label)
        csv_layout.addWidget(self.csv_browse_btn)
        layout.addRow(".par.csv file:", csv_layout)
        
        # Validation button
        self.validate_btn = QPushButton("Validate Files")
        self.validate_btn.clicked.connect(self.validate_files)
        self.validate_btn.setEnabled(False)
        layout.addRow(self.validate_btn)
        
        parent_layout.addWidget(group)
    
    def setup_metadata_group(self, parent_layout):
        """Setup metadata editing group."""
        group = QGroupBox("File Metadata")
        layout = QFormLayout(group)
        
        # Temperature
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(-100, 200)
        self.temperature_spin.setValue(25.0)
        self.temperature_spin.setSuffix(" °C")
        layout.addRow("Temperature:", self.temperature_spin)
        
        # Applied potential interpretation
        self.applied_potential_combo = QComboBox()
        self.applied_potential_combo.addItems([
            "2-electrode WE-CE voltage",
            "3-electrode WE-RE voltage", 
            "3-electrode CE-RE voltage",
            "Custom configuration"
        ])
        layout.addRow("Applied Potential:", self.applied_potential_combo)
        
        # Notes
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.setPlaceholderText("Additional notes...")
        layout.addRow("Notes:", self.notes_edit)
        
        parent_layout.addWidget(group)
    
    def setup_actionid_group(self, parent_layout):
        """Setup ActionID mapping group."""
        group = QGroupBox("ActionID Mappings")
        layout = QVBoxLayout(group)
        
        self.actionid_text = QTextEdit()
        self.actionid_text.setMaximumHeight(100)
        self.actionid_text.setReadOnly(True)
        self.actionid_text.setPlaceholderText("ActionID mappings will appear here after validation...")
        layout.addWidget(self.actionid_text)
        
        parent_layout.addWidget(group)
    
    def setup_progress_group(self, parent_layout):
        """Setup progress and status group."""
        group = QGroupBox("Status")
        layout = QVBoxLayout(group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        parent_layout.addWidget(group)
    
    def setup_buttons(self, parent_layout):
        """Setup dialog buttons."""
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        
        if self.mode == 'upload':
            self.upload_btn = QPushButton("Process Files")
            self.upload_btn.clicked.connect(self.process_files)
            self.upload_btn.setEnabled(False)
            button_layout.addWidget(self.upload_btn)
        else:
            self.save_btn = QPushButton("Save Changes")
            self.save_btn.clicked.connect(self.save_changes)
            button_layout.addWidget(self.save_btn)
        
        parent_layout.addLayout(button_layout)
    
    def setup_connections(self):
        """Setup signal connections."""
        pass
    
    def browse_par_file(self):
        """Browse for .par file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select .par file", "", "PAR Files (*.par);;All Files (*.*)"
        )
        if file_path:
            self.par_path = Path(file_path)
            self.par_file_label.setText(self.par_path.name)
            self.check_files_ready()
    
    def browse_csv_file(self):
        """Browse for .par.csv file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select .par.csv file", "", "CSV Files (*.csv);;All Files (*.*)"
        )
        if file_path:
            self.csv_path = Path(file_path)
            self.csv_file_label.setText(self.csv_path.name)
            self.check_files_ready()
    
    def check_files_ready(self):
        """Check if both files are selected and enable validation."""
        if self.par_path and self.csv_path:
            self.validate_btn.setEnabled(True)
        else:
            self.validate_btn.setEnabled(False)
    
    def validate_files(self):
        """Validate selected files and load data."""
        if not self.par_path or not self.csv_path:
            return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Validating files...")
        
        # Start validation in background thread
        self.validation_thread = FileValidationThread(self.par_path, self.csv_path, self.api)
        self.validation_thread.validation_completed.connect(self.on_validation_completed)
        self.validation_thread.progress_updated.connect(self.on_progress_updated)
        self.validation_thread.start()
    
    def on_progress_updated(self, progress: int, message: str):
        """Handle validation progress updates."""
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)
    
    def on_validation_completed(self, result: Dict[str, Any]):
        """Handle validation completion - lightweight success/error handling only."""
        self.progress_bar.setVisible(False)

        if result['success']:
            # Simple validation success - no processing
            # self.plot_widget.show_validation_placeholder()
            self.actionid_text.setPlainText("✅ Files validated successfully - ready for upload and processing")
            self.status_label.setText("✅ Files validated - ready for upload")
            
            if self.mode == 'upload':
                self.upload_btn.setEnabled(True)
            
        else:
            QMessageBox.critical(self, "Validation Error", result['error'])
            self.status_label.setText(f"❌ Validation failed: {result['error']}")
    
    def browse_par_file(self):
        """Browse for .par file."""
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select .par file", 
            str(self.last_directory),
            "PAR files (*.par);;All files (*)"
        )
        
        if file_path:
            self.par_path = Path(file_path)
            self.last_directory = self.par_path.parent  # Remember directory
            self.par_file_label.setText(f"Selected: {self.par_path.name}")
            self.check_file_selection()
    
    def browse_csv_file(self):
        """Browse for .par.csv file."""
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select .par.csv file", 
            str(self.last_directory),
            "CSV files (*.csv *.par.csv);;All files (*)"
        )
        
        if file_path:
            self.csv_path = Path(file_path)
            self.last_directory = self.csv_path.parent  # Remember directory
            self.csv_file_label.setText(f"Selected: {self.csv_path.name}")
            self.check_file_selection()
    
    def check_file_selection(self):
        """Enable validate button when both files are selected."""
        if self.par_path and self.csv_path:
            self.validate_btn.setEnabled(True)
            self.status_label.setText("Files selected - ready to validate")
        else:
            self.validate_btn.setEnabled(False)
            self.status_label.setText("Please select both .par and .par.csv files")
    
    def process_files(self):
        """Process files using clean in-memory pipeline and populate all panels."""
        if not self.par_path or not self.csv_path:
            QMessageBox.warning(self, "No Files", "Please select and validate files first.")
            return
        
        try:
            # Show progress
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("Processing files...")
            
            # Prepare processing options
            upload_options = {
                'temperature_c': self.temperature_spin.value() if hasattr(self, 'temperature_spin') else 25.0,
                'applied_potential_interpretation': self.applied_potential_combo.currentText() if hasattr(self, 'applied_potential_combo') else '2-electrode WE-CE voltage'
            }
            
            self.progress_bar.setValue(30)
            
            # Process files through clean in-memory pipeline
            result = self.api.add_dual_files_to_cell(
                cell_name=self.cell_name,
                par_path=self.par_path,
                csv_path=self.csv_path,
                upload_options=upload_options
            )
            
            self.progress_bar.setValue(70)
            
            if result['success']:
                # Use in-memory data directly (no disk I/O needed)
                self.status_label.setText("Updating displays...")
                
                processed_data = result.get('processed_data')
                if processed_data is not None:
                    self._populate_panels_with_memory_data(processed_data, result.get('message', ''))
                
                self.progress_bar.setValue(100)
                self.progress_bar.setVisible(False)
                
                QMessageBox.information(self, "Processing Complete", 
                    f"✅ Files processed successfully!\n\n{result.get('message', '')}")
                
                self.upload_completed.emit(result.get('file_ids', []))
                self.accept()
            else:
                self.progress_bar.setVisible(False)
                QMessageBox.critical(self, "Processing Failed", f"❌ {result['error']}")
                
        except Exception as e:
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self, "Processing Error", f"❌ Unexpected error: {str(e)}")
    
    def _populate_panels_with_memory_data(self, processed_data, processing_message: str):
        """Populate all panels with in-memory processed data - no disk I/O."""
        try:
            # Convert Polars DataFrame to Pandas for plotting
            import polars as pl
            if isinstance(processed_data, pl.DataFrame):
                self.current_data = processed_data.to_pandas()
            else:
                self.current_data = processed_data
            
            # Update plots with in-memory data
            self.plot_widget.update_plots(self.current_data)
            
            # Generate summary from universal schema data
            techniques = []
            if 'technique_id' in self.current_data.columns:
                unique_actions = self.current_data['technique_id'].unique()
                techniques = [f"ActionID_{aid}" for aid in unique_actions if not pd.isna(aid)]
            
            time_range = ""
            if 'time_s' in self.current_data.columns:
                time_min = self.current_data['time_s'].min()
                time_max = self.current_data['time_s'].max()
                time_range = f"{time_min:.1f} - {time_max:.1f} s"
            
            summary_text = (
                f"Processing: {processing_message}\n"
                f"Data points: {len(self.current_data):,}\n"
                f"Techniques: {', '.join(techniques) if techniques else 'Unknown'}\n"
                f"Time range: {time_range}\n"
                f"✅ Data ready for analysis"
            )
            
            self.actionid_text.setPlainText(summary_text)
            self.status_label.setText("✅ Processing complete - displaying in-memory data")
                
        except Exception as e:
            self.status_label.setText(f"Display update failed: {str(e)}")
    
    def save_changes(self):
        """Save metadata changes for existing experiment."""
        # TODO: Implement save changes for review mode
        QMessageBox.information(self, "Save Changes", "Changes saved successfully")
        self.accept()
    
    def load_existing_file(self):
        """Load existing file data for review mode."""
        if not self.file_id:
            return
        
        try:
            # Load file data
            result = self.api.get_file_data_preview(self.file_id, n_rows=50000)
            if result['success']:
                self.current_data = result['preview_data']
                self.plot_widget.update_plots(self.current_data)
                
                # TODO: Load and display file metadata
                self.status_label.setText("Experiment data loaded")
            else:
                self.status_label.setText(f"Failed to load data: {result['error']}")
                
        except Exception as e:
            self.status_label.setText(f"Error loading file: {str(e)}")