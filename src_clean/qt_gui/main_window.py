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
    QMenuBar, QStatusBar, QFileDialog
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QFont, QAction

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
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.new_cell_btn = QPushButton("New Cell")
        self.new_cell_btn.clicked.connect(self.create_new_cell)
        button_layout.addWidget(self.new_cell_btn)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_cells)
        button_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(button_layout)
    
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
        self.cell_selected.emit(cell_name)
    
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


class FileListWidget(QWidget):
    """Widget to display files for current cell."""
    
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
        layout.addWidget(self.file_list)
        
        # File info
        self.file_info = QTextEdit()
        self.file_info.setMaximumHeight(100)
        self.file_info.setReadOnly(True)
        layout.addWidget(self.file_info)
    
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
        self.resize(1200, 800)
    
    def setup_ui(self):
        """Setup the main UI."""
        # Central widget with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QHBoxLayout(central_widget)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # Left panel - Cell selection
        self.cell_widget = CellSelectionWidget(self.api)
        self.cell_widget.setMaximumWidth(300)
        splitter.addWidget(self.cell_widget)
        
        # Middle panel - File upload
        self.upload_widget = FileUploadWidget(self.api)
        self.upload_widget.setMaximumWidth(400)
        splitter.addWidget(self.upload_widget)
        
        # Right panel - File list
        self.file_list_widget = FileListWidget(self.api)
        splitter.addWidget(self.file_list_widget)
        
        # Set splitter proportions
        splitter.setSizes([250, 350, 400])
        
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
    
    def on_cell_selected(self, cell_name: str):
        """Handle cell selection."""
        self.upload_widget.set_current_cell(cell_name)
        self.file_list_widget.set_current_cell(cell_name)
        self.status_bar.showMessage(f"Selected cell: {cell_name}")
    
    def on_file_processed(self, file_id: str):
        """Handle file processing completion."""
        # Refresh file list
        self.file_list_widget.refresh_files()
        self.status_bar.showMessage(f"File processed: {file_id}")
    
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