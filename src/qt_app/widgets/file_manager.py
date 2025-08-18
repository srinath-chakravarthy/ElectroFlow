"""
File Manager Widget

Provides interface for:
- Uploading files to active cell
- Viewing uploaded files
- File processing status
- Drag & drop support
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, 
    QLabel, QProgressBar, QFileDialog, QListWidgetItem, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QThread
from pathlib import Path


class FileUploadThread(QThread):
    """Background thread for file upload processing."""
    
    progress_updated = Signal(int)  # Progress percentage
    file_processed = Signal(str, bool)  # filename, success
    upload_completed = Signal(int)  # successful_count
    
    def __init__(self, api, cell_name, file_paths):
        super().__init__()
        self.api = api
        self.cell_name = cell_name
        self.file_paths = file_paths
    
    def run(self):
        """Run the file upload process."""
        successful_count = 0
        total_files = len(self.file_paths)
        
        for i, file_path in enumerate(self.file_paths):
            try:
                # Update progress
                progress = int((i / total_files) * 100)
                self.progress_updated.emit(progress)
                
                # Upload single file
                result = self.api.add_files_to_cell(
                    cell_name=self.cell_name,
                    file_paths=[file_path],
                    upload_options={'duplicate_handling': 'replace'}
                )
                
                if result['success'] and result['summary']['successful_uploads'] > 0:
                    successful_count += 1
                    self.file_processed.emit(file_path.name, True)
                else:
                    self.file_processed.emit(file_path.name, False)
                
            except Exception as e:
                self.file_processed.emit(file_path.name, False)
        
        self.progress_updated.emit(100)
        self.upload_completed.emit(successful_count)


class DualFileUploadThread(QThread):
    """Background thread for dual file upload processing."""
    
    progress_updated = Signal(int)  # Progress percentage
    file_processed = Signal(str, bool)  # filename, success
    upload_completed = Signal(int)  # successful_count
    
    def __init__(self, api, cell_name, dual_pairs):
        super().__init__()
        self.api = api
        self.cell_name = cell_name
        self.dual_pairs = dual_pairs
    
    def run(self):
        """Run the dual file upload process."""
        successful_count = 0
        total_pairs = len(self.dual_pairs)
        
        for i, pair in enumerate(self.dual_pairs):
            try:
                # Update progress
                progress = int((i / total_pairs) * 100)
                self.progress_updated.emit(progress)
                
                # Upload dual file pair
                par_path = Path(pair['par_file'])
                csv_path = Path(pair['csv_file'])
                
                result = self.api.add_dual_files_to_cell(
                    cell_name=self.cell_name,
                    par_path=par_path,
                    csv_path=csv_path,
                    upload_options={'duplicate_handling': 'replace'}
                )
                
                if result['success']:
                    successful_count += 1
                    self.file_processed.emit(f"{par_path.name} + {csv_path.name}", True)
                else:
                    self.file_processed.emit(f"{par_path.name} + {csv_path.name}", False)
                
            except Exception as e:
                self.file_processed.emit(f"Pair {i+1}", False)
        
        self.progress_updated.emit(100)
        self.upload_completed.emit(successful_count)


class FileManagerWidget(QWidget):
    """Widget for file management operations."""
    
    # Signals
    files_uploaded = Signal(int)  # successful_count
    file_selected = Signal(int)  # file_id
    
    def __init__(self, backend_api, parent=None):
        super().__init__(parent)
        self.api = backend_api
        self.active_cell_id = None
        self.active_cell_name = ""
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("File Management")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)
        
        # Upload section
        upload_layout = QHBoxLayout()
        
        self.upload_btn = QPushButton("Upload Files")
        self.upload_btn.clicked.connect(self.upload_files)
        self.upload_btn.setEnabled(False)  # Disabled until cell selected
        upload_layout.addWidget(self.upload_btn)
        
        upload_layout.addStretch()
        layout.addLayout(upload_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # File list
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.on_file_selected)
        layout.addWidget(self.file_list)
        
        # Status label
        self.status_label = QLabel("No cell selected")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.status_label)
    
    def set_active_cell(self, cell_id, cell_name):
        """Set the active cell and refresh file list."""
        self.active_cell_id = cell_id
        self.active_cell_name = cell_name
        
        self.upload_btn.setEnabled(True)
        self.status_label.setText(f"Active: {cell_name}")
        
        self.refresh_file_list()
    
    def refresh_file_list(self):
        """Refresh the file list from the backend."""
        if not self.active_cell_id:
            return
        
        self.file_list.clear()
        
        result = self.api.get_cell_files(self.active_cell_id)
        
        if result['success']:
            files = result['files']
            for file_info in files:
                item_text = f"{file_info['original_filename']} ({file_info['processing_status']})"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, file_info['id'])
                
                # Color code by status
                if file_info['processing_status'] == 'completed':
                    item.setForeground(Qt.darkGreen)
                elif file_info['processing_status'] == 'failed':
                    item.setForeground(Qt.red)
                else:
                    item.setForeground(Qt.blue)
                
                self.file_list.addItem(item)
        else:
            self.status_label.setText(f"Error loading files: {result['error']}")
    
    def upload_files(self):
        """Show file dialog and upload selected files."""
        if not self.active_cell_id:
            QMessageBox.warning(self, "No Cell Selected", 
                              "Please select a cell before uploading files.")
            return
        
        # File dialog for dual file support
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 
            "Select Battery Data Files (.par and .par.csv)",
            "",
            "Battery Data Files (*.par *.par.csv);;PAR Files (*.par);;PAR CSV Files (*.par.csv);;All Files (*.*)"
        )
        
        if file_paths:
            # Convert to Path objects
            path_objects = [Path(p) for p in file_paths]
            
            # Check for dual file pairs and validate
            self.validate_and_upload(path_objects)
    
    def validate_and_upload(self, file_paths):
        """Validate files and determine upload strategy."""
        # Validate files through backend API
        validation_result = self.api.validate_file_compatibility(file_paths)
        
        if not validation_result['success']:
            QMessageBox.critical(self, "Validation Error", 
                               f"File validation failed: {validation_result['error']}")
            return
        
        dual_pairs = validation_result.get('dual_pairs', [])
        individual_files = validation_result.get('individual_files', [])
        
        # If we have dual pairs, prioritize dual processing
        if dual_pairs:
            self.show_dual_file_dialog(dual_pairs, file_paths)
        else:
            # Process individual files
            valid_files = [Path(f['file']) for f in individual_files if f['valid']]
            if valid_files:
                self.start_upload(valid_files)
            else:
                QMessageBox.warning(self, "No Valid Files", 
                                  "No valid battery data files found.")
    
    def show_dual_file_dialog(self, dual_pairs, all_files):
        """Show dialog for dual file processing options."""
        message = "Detected .par and .par.csv file pairs:\n\n"
        for pair in dual_pairs:
            message += f"• {Path(pair['par_file']).name} + {Path(pair['csv_file']).name}\n"
        
        message += "\nFor calibrated data processing, use dual file mode (.par for technique metadata, .par.csv for calibrated data)."
        
        reply = QMessageBox.question(
            self, "Dual File Processing", 
            message + "\n\nUse dual file processing mode?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
        )
        
        if reply == QMessageBox.Yes:
            # Process as dual files
            self.start_dual_upload(dual_pairs)
        elif reply == QMessageBox.No:
            # Process as individual files
            self.start_upload(all_files)
        # Cancel does nothing
    
    def start_dual_upload(self, dual_pairs):
        """Start dual file upload processing."""
        self.upload_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Create and start dual upload thread
        self.upload_thread = DualFileUploadThread(self.api, self.active_cell_name, dual_pairs)
        self.upload_thread.progress_updated.connect(self.progress_bar.setValue)
        self.upload_thread.file_processed.connect(self.on_file_processed)
        self.upload_thread.upload_completed.connect(self.on_upload_completed)
        self.upload_thread.start()
    
    def start_upload(self, file_paths):
        """Start file upload in background thread."""
        self.upload_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Create and start upload thread
        self.upload_thread = FileUploadThread(self.api, self.active_cell_name, file_paths)
        self.upload_thread.progress_updated.connect(self.progress_bar.setValue)
        self.upload_thread.file_processed.connect(self.on_file_processed)
        self.upload_thread.upload_completed.connect(self.on_upload_completed)
        self.upload_thread.start()
    
    def on_file_processed(self, filename, success):
        """Handle individual file processing completion."""
        status = "✓" if success else "✗"
        self.status_label.setText(f"{status} {filename}")
    
    def on_upload_completed(self, successful_count):
        """Handle upload completion."""
        self.upload_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        self.status_label.setText(f"Upload completed: {successful_count} files")
        self.files_uploaded.emit(successful_count)
        
        # Refresh file list
        self.refresh_file_list()
    
    def on_file_selected(self, item):
        """Handle file selection."""
        file_id = item.data(Qt.UserRole)
        if file_id:
            self.file_selected.emit(file_id)