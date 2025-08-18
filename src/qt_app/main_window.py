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
from qt_app.widgets.cell_experiment_tree import CellExperimentTreeWidget
from qt_app.widgets.data_viewer import DataViewerWidget
from qt_app.widgets.actions_segments_tree import ActionsSegmentsTreeWidget
from qt_app.widgets.group_management_tree import GroupManagementTreeWidget
from qt_app.widgets.analysis_tabs import AnalysisTabsWidget
from qt_app.dialogs.upload_review_dialog import UploadReviewDialog


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
        """Setup the main user interface with 3-panel layout."""
        self.setWindowTitle("Battery Data Analyzer - Qt Application")
        self.setMinimumSize(1400, 900)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create main splitter layout
        self.create_main_layout()
        
        # Create status bar
        self.create_status_bar()
    
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
    
    def create_main_layout(self):
        """Create the main 3-panel layout."""
        # Create central widget with splitters
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create main horizontal splitter (top area)
        top_splitter = QSplitter(Qt.Horizontal)
        
        # Left: Cell/Experiment Tree
        self.cell_tree = CellExperimentTreeWidget(self.api)
        self.cell_tree.setMaximumWidth(300)
        top_splitter.addWidget(self.cell_tree)
        
        # Right: Data Viewer
        self.data_viewer = DataViewerWidget(self.api)
        top_splitter.addWidget(self.data_viewer)
        
        # Set proportions for top splitter (25% left, 75% right)
        top_splitter.setSizes([300, 900])
        
        # Create bottom horizontal splitter (bottom area)
        bottom_splitter = QSplitter(Qt.Horizontal)
        
        # Bottom Left: Actions/Segments Tree
        self.actions_tree = ActionsSegmentsTreeWidget(self.api)
        bottom_splitter.addWidget(self.actions_tree)
        
        # Bottom Center: Group Management Tree
        self.group_tree = GroupManagementTreeWidget(self.api)
        bottom_splitter.addWidget(self.group_tree)
        
        # Bottom Right: Analysis Tabs
        self.analysis_tabs = AnalysisTabsWidget(self.api)
        bottom_splitter.addWidget(self.analysis_tabs)
        
        # Set proportions for bottom splitter (33% each)
        bottom_splitter.setSizes([400, 400, 400])
        
        # Create main vertical splitter
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(bottom_splitter)
        
        # Set proportions (60% top, 40% bottom)
        main_splitter.setSizes([540, 360])
        
        main_layout.addWidget(main_splitter)
    
    def create_status_bar(self):
        """Create the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Active cell label
        self.active_cell_label = QLabel("No cell selected")
        self.status_bar.addWidget(self.active_cell_label)
        
        # Status message
        self.status_bar.showMessage("Ready")
    
    
    def setup_connections(self):
        """Setup signal/slot connections between widgets."""
        
        # Cell/Experiment Tree connections
        self.cell_tree.cell_selected.connect(self.set_active_cell)
        self.cell_tree.experiment_selected.connect(self.on_experiment_selected)
        self.cell_tree.experiment_double_clicked.connect(self.on_experiment_double_clicked)
        self.cell_tree.upload_files_requested.connect(self.on_upload_files_requested)
        
        # Actions/Segments Tree connections
        self.actions_tree.segments_selected.connect(self.on_segments_selected)
        self.actions_tree.create_group_requested.connect(self.group_tree.add_segments_to_group)
        
        # Group Management Tree connections
        self.group_tree.group_selected.connect(self.on_group_selected)
        self.group_tree.group_analysis_requested.connect(self.on_group_analysis_requested)
        self.group_tree.group_plotting_requested.connect(self.on_group_plotting_requested)
        
        # Active cell changes - update all widgets
        self.active_cell_changed.connect(lambda cell_id, cell_name: self.group_tree.set_active_cell(cell_id))
        self.active_cell_changed.connect(self.data_viewer.set_active_cell)
        self.active_cell_changed.connect(self.analysis_tabs.clear_data)
    
    def auto_select_first_cell(self):
        """Automatically select the first available cell."""
        QTimer.singleShot(100, self._auto_select_first_cell)
    
    def _auto_select_first_cell(self):
        """Internal method to select first cell after UI is ready."""
        result = self.api.get_all_cells()
        if result['success'] and result['cells']:
            first_cell = result['cells'][0]
            self.set_active_cell(first_cell['id'], first_cell['cell_name'])
    
    def set_active_cell(self, cell_id: int, cell_name: str):
        """Set the active cell and update all widgets."""
        if cell_id != self.active_cell_id:
            self.active_cell_id = cell_id
            self.active_cell_name = cell_name
            
            # Update UI
            self.active_cell_label.setText(f"Active: {cell_name}")
            
            # Emit signal to update other widgets
            self.active_cell_changed.emit(cell_id, cell_name)
            
            self.status_bar.showMessage(f"Active cell changed to: {cell_name}")
    
    
    def on_experiment_selected(self, cell_id: int, cell_name: str, file_id: str):
        """Handle experiment selection - load data in other widgets."""
        if cell_id != self.active_cell_id:
            self.set_active_cell(cell_id, cell_name)
        
        # Load experiment data in actions tree and data viewer
        self.actions_tree.set_file_data(cell_id, file_id)
        self.data_viewer.show_file_data(file_id)
        
        self.status_bar.showMessage(f"Loaded experiment: {file_id}")
    
    def on_experiment_double_clicked(self, cell_id: int, cell_name: str, file_id: str):
        """Handle experiment double-click - open upload/review modal."""
        from qt_app.dialogs.upload_review_dialog import UploadReviewDialog
        
        dialog = UploadReviewDialog(self.api, cell_id, cell_name, self)
        dialog.load_existing_experiment(file_id)
        dialog.exec()
        
        # Refresh tree after modal closes
        self.cell_tree.refresh_tree()
    
    def on_upload_files_requested(self, cell_name: str):
        """Handle upload files request from tree."""
        # Find cell ID
        result = self.api.get_all_cells()
        if result['success']:
            for cell in result['cells']:
                if cell['cell_name'] == cell_name:
                    self.upload_files_for_cell(cell['id'], cell_name)
                    break
    
    def on_segments_selected(self, segment_ids: list):
        """Handle segment selection - update analysis tabs."""
        self.analysis_tabs.update_selected_data(segment_ids, "segments")
        
        if segment_ids:
            self.status_bar.showMessage(f"Selected {len(segment_ids)} segments")
        else:
            self.status_bar.showMessage("No segments selected")
    
    def on_group_selected(self, group_id: int):
        """Handle group selection - update analysis tabs."""
        self.analysis_tabs.update_selected_group(group_id)
        self.status_bar.showMessage(f"Selected group: {group_id}")
    
    def on_group_analysis_requested(self, group_id: int):
        """Handle group analysis request - switch to analysis tab."""
        self.analysis_tabs.update_selected_group(group_id)
        self.analysis_tabs.tabs.setCurrentIndex(1)  # Switch to Analysis tab
        self.status_bar.showMessage(f"Analyzing group: {group_id}")
    
    def on_group_plotting_requested(self, group_id: int):
        """Handle group plotting request - switch to plotting tab."""
        self.analysis_tabs.update_selected_group(group_id)
        self.analysis_tabs.tabs.setCurrentIndex(2)  # Switch to Plotting tab
        self.status_bar.showMessage(f"Plotting group: {group_id}")
    
    def on_files_uploaded(self, count: int):
        """Handle successful file upload."""
        self.status_bar.showMessage(f"Uploaded {count} files successfully", 3000)
    
    # Menu actions
    def new_cell(self):
        """Create a new cell."""
        self.cell_tree.create_new_cell()
    
    def upload_files(self):
        """Upload files to active cell."""
        if not self.active_cell_id:
            QMessageBox.warning(self, "No Cell Selected", 
                              "Please select a cell before uploading files.")
            return
        
        self.upload_files_for_cell(self.active_cell_id, self.active_cell_name)
    
    def upload_files_for_cell(self, cell_id: int, cell_name: str):
        """Upload files for specific cell using modal dialog."""
        from qt_app.dialogs.upload_review_dialog import UploadReviewDialog
        
        dialog = UploadReviewDialog(self.api, cell_id, cell_name, self)
        if dialog.exec() == dialog.Accepted:
            # Refresh tree after successful upload
            self.cell_tree.refresh_tree()
    
    def create_group(self):
        """Create a new group."""
        if not self.active_cell_id:
            QMessageBox.warning(self, "No Cell Selected", 
                              "Please select a cell before creating groups.")
            return
        
        self.group_tree.create_new_group()
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(self, "About Battery Data Analyzer",
                         "Battery Data Analyzer 2.0\\n\\n"
                         "Qt-based desktop application for\\n"
                         "electrochemical battery data analysis.\\n\\n"
                         "Built with PySide6 and pyqtgraph.")
    
    # Settings management
    def save_settings(self):
        """Save application settings."""
        settings = QSettings()
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        if self.active_cell_id:
            settings.setValue("activeCell", self.active_cell_id)
    
    def restore_settings(self):
        """Restore application settings."""
        settings = QSettings()
        
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        window_state = settings.value("windowState")
        if window_state:
            self.restoreState(window_state)
    
    def closeEvent(self, event):
        """Handle application close event."""
        self.save_settings()
        event.accept()