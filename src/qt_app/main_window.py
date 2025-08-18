"""
Main Window for Battery Data Analyzer Qt Application

Implements the primary application window with:
- Single-cell focused workflow
- Docked widgets for flexible layout
- File management and data visualization
- Group creation and analysis
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QMenuBar, QStatusBar,
    QDockWidget, QLabel, QComboBox, QPushButton, QSplitter, QMessageBox
)
from PySide6.QtCore import Qt, QSettings, Signal, QTimer
from PySide6.QtGui import QAction, QKeySequence

# Import backend
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from ui.backend_api import BackendAPI
from qt_app.widgets.cell_selector import CellSelectorWidget
from qt_app.widgets.file_manager import FileManagerWidget
from qt_app.widgets.data_viewer import DataViewerWidget
from qt_app.widgets.group_manager import GroupManagerWidget


class MainWindow(QMainWindow):
    """Main application window with single-cell workflow."""
    
    # Signals
    active_cell_changed = Signal(int, str)  # cell_id, cell_name
    
    def __init__(self, data_dir: Path = None, debug: bool = False):
        super().__init__()
        
        self.data_dir = data_dir or Path("data")
        self.debug = debug
        self.active_cell_id = None
        self.active_cell_name = ""
        
        # Initialize backend
        self.setup_backend()
        
        # Setup UI
        self.setup_ui()
        self.setup_connections()
        self.restore_settings()
        
        # Initialize with first cell if available
        self.auto_select_first_cell()
    
    def setup_backend(self):
        """Initialize backend API."""
        try:
            self.api = BackendAPI(self.data_dir)
            if self.debug:
                print(f"Backend initialized with data_dir: {self.data_dir}")
        except Exception as e:
            QMessageBox.critical(self, "Backend Error", 
                               f"Failed to initialize backend: {str(e)}")
            sys.exit(1)
    
    def setup_ui(self):
        """Setup the main user interface."""
        self.setWindowTitle("Battery Data Analyzer")
        self.setMinimumSize(1200, 800)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create central widget (data viewer)
        self.data_viewer = DataViewerWidget(self.api)
        self.setCentralWidget(self.data_viewer)
        
        # Create docked widgets
        self.create_dock_widgets()
        
        # Create status bar
        self.create_status_bar()
        
        # Create toolbar
        self.create_toolbar()
    
    def create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        # New cell action
        new_cell_action = QAction("&New Cell...", self)
        new_cell_action.setShortcut(QKeySequence.New)
        new_cell_action.triggered.connect(self.new_cell)
        file_menu.addAction(new_cell_action)
        
        file_menu.addSeparator()
        
        # Upload files action
        upload_action = QAction("&Upload Files...", self)
        upload_action.setShortcut(QKeySequence("Ctrl+U"))
        upload_action.triggered.connect(self.upload_files)
        file_menu.addAction(upload_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        # Analysis menu
        analysis_menu = menubar.addMenu("&Analysis")
        
        # Create group action
        create_group_action = QAction("Create &Group...", self)
        create_group_action.setShortcut(QKeySequence("Ctrl+G"))
        create_group_action.triggered.connect(self.create_group)
        analysis_menu.addAction(create_group_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_dock_widgets(self):
        """Create dockable widgets for the interface."""
        
        # Cell selector dock (top)
        self.cell_dock = QDockWidget("Cell Selection", self)
        self.cell_selector = CellSelectorWidget(self.api)
        self.cell_dock.setWidget(self.cell_selector)
        self.cell_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable)
        self.addDockWidget(Qt.TopDockWidgetArea, self.cell_dock)
        
        # File manager dock (left)
        self.file_dock = QDockWidget("File Management", self)
        self.file_manager = FileManagerWidget(self.api)
        self.file_dock.setWidget(self.file_manager)
        self.file_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.file_dock)
        
        # Group manager dock (left, below file manager)
        self.group_dock = QDockWidget("Group Management", self)
        self.group_manager = GroupManagerWidget(self.api)
        self.group_dock.setWidget(self.group_manager)
        self.group_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.group_dock)
        
        # Split the left docks vertically
        self.splitDockWidget(self.file_dock, self.group_dock, Qt.Vertical)
    
    def create_status_bar(self):
        """Create the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Active cell label
        self.active_cell_label = QLabel("No cell selected")
        self.status_bar.addWidget(self.active_cell_label)
        
        # Status message
        self.status_bar.showMessage("Ready")
    
    def create_toolbar(self):
        """Create the main toolbar."""
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)
        
        # Quick cell selection
        toolbar.addWidget(QLabel("Active Cell:"))
        self.cell_combo = QComboBox()
        self.cell_combo.setMinimumWidth(200)
        self.cell_combo.currentTextChanged.connect(self.on_cell_combo_changed)
        toolbar.addWidget(self.cell_combo)
        
        toolbar.addSeparator()
        
        # Quick actions
        upload_btn = QPushButton("Upload Files")
        upload_btn.clicked.connect(self.upload_files)
        toolbar.addWidget(upload_btn)
        
        new_group_btn = QPushButton("New Group")
        new_group_btn.clicked.connect(self.create_group)
        toolbar.addWidget(new_group_btn)
    
    def setup_connections(self):
        \"\"\"Setup signal/slot connections between widgets.\"\"\"
        
        # Cell selection changes
        self.cell_selector.cell_selected.connect(self.set_active_cell)
        self.active_cell_changed.connect(self.file_manager.set_active_cell)
        self.active_cell_changed.connect(self.group_manager.set_active_cell)
        self.active_cell_changed.connect(self.data_viewer.set_active_cell)
        
        # File management events
        self.file_manager.files_uploaded.connect(self.on_files_uploaded)
        self.file_manager.file_selected.connect(self.data_viewer.show_file_data)
        
        # Group management events
        self.group_manager.group_selected.connect(self.data_viewer.show_group_analysis)
        
        # Data viewer events
        self.data_viewer.segments_selected.connect(self.group_manager.enable_group_creation)
    
    def auto_select_first_cell(self):
        \"\"\"Automatically select the first available cell.\"\"\"
        QTimer.singleShot(100, self._auto_select_first_cell)
    
    def _auto_select_first_cell(self):
        \"\"\"Internal method to select first cell after UI is ready.\"\"\"
        result = self.api.get_all_cells()
        if result['success'] and result['cells']:
            first_cell = result['cells'][0]
            self.set_active_cell(first_cell['id'], first_cell['cell_name'])
    
    def set_active_cell(self, cell_id: int, cell_name: str):
        \"\"\"Set the active cell and update all widgets.\"\"\"
        if cell_id != self.active_cell_id:
            self.active_cell_id = cell_id
            self.active_cell_name = cell_name
            
            # Update UI
            self.active_cell_label.setText(f"Active: {cell_name}")
            self.update_cell_combo()
            
            # Emit signal to update other widgets
            self.active_cell_changed.emit(cell_id, cell_name)
            
            self.status_bar.showMessage(f"Active cell changed to: {cell_name}")
    
    def update_cell_combo(self):
        \"\"\"Update the cell combo box.\"\"\"
        self.cell_combo.blockSignals(True)
        self.cell_combo.clear()
        
        result = self.api.get_all_cells()
        if result['success']:
            for cell in result['cells']:
                self.cell_combo.addItem(cell['cell_name'], cell['id'])
            
            # Set current cell
            if self.active_cell_name:
                index = self.cell_combo.findText(self.active_cell_name)
                if index >= 0:
                    self.cell_combo.setCurrentIndex(index)
        
        self.cell_combo.blockSignals(False)
    
    def on_cell_combo_changed(self, cell_name: str):
        \"\"\"Handle cell combo box changes.\"\"\"
        if cell_name and cell_name != self.active_cell_name:
            # Find cell ID
            result = self.api.get_all_cells()
            if result['success']:
                for cell in result['cells']:
                    if cell['cell_name'] == cell_name:
                        self.set_active_cell(cell['id'], cell_name)
                        break
    
    def on_files_uploaded(self, count: int):
        \"\"\"Handle successful file upload.\"\"\"
        self.status_bar.showMessage(f"Uploaded {count} files successfully", 3000)
    
    # Menu actions
    def new_cell(self):
        \"\"\"Create a new cell.\"\"\"
        self.cell_selector.create_new_cell()
    
    def upload_files(self):
        \"\"\"Upload files to active cell.\"\"\"
        if not self.active_cell_id:
            QMessageBox.warning(self, "No Cell Selected", 
                              "Please select a cell before uploading files.")
            return
        
        self.file_manager.upload_files()
    
    def create_group(self):
        \"\"\"Create a new group.\"\"\"
        if not self.active_cell_id:
            QMessageBox.warning(self, "No Cell Selected", 
                              "Please select a cell before creating groups.")
            return
        
        self.group_manager.create_new_group()
    
    def show_about(self):
        \"\"\"Show about dialog.\"\"\"
        QMessageBox.about(self, "About Battery Data Analyzer",
                         "Battery Data Analyzer 2.0\\n\\n"
                         "Qt-based desktop application for\\n"
                         "electrochemical battery data analysis.\\n\\n"
                         "Built with PySide6 and pyqtgraph.")
    
    # Settings management
    def save_settings(self):
        \"\"\"Save application settings.\"\"\"
        settings = QSettings()
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        if self.active_cell_id:
            settings.setValue("activeCell", self.active_cell_id)
    
    def restore_settings(self):
        \"\"\"Restore application settings.\"\"\"
        settings = QSettings()
        
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        window_state = settings.value("windowState")
        if window_state:
            self.restoreState(window_state)
    
    def closeEvent(self, event):
        \"\"\"Handle application close event.\"\"\"
        self.save_settings()
        event.accept()