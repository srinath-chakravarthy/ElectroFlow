"""
Cell and Experiment Tree Widget

Displays cells and their experiments in a collapsible tree structure.
Supports single-click for data loading and double-click for review modal.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QMenu, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QBrush, QColor
from typing import Dict, List, Any, Optional


class CellExperimentTreeWidget(QWidget):
    """Tree widget for cell and experiment management."""
    
    # Signals
    experiment_selected = Signal(int, str, str)  # cell_id, cell_name, file_id
    cell_selected = Signal(int, str)  # cell_id, cell_name
    experiment_double_clicked = Signal(int, str, str)  # cell_id, cell_name, file_id
    upload_files_requested = Signal(str)  # cell_name
    
    def __init__(self, backend_api, parent=None):
        super().__init__(parent)
        self.api = backend_api
        self.setup_ui()
        self.setup_connections()
        self.refresh_tree()
    
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Cells & Experiments")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_tree)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Status", "Info"])
        self.tree.setRootIsDecorated(True)
        self.tree.setAlternatingRowColors(True)
        
        # Enable context menu
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.tree)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.new_cell_btn = QPushButton("New Cell")
        self.new_cell_btn.clicked.connect(self.create_new_cell)
        button_layout.addWidget(self.new_cell_btn)
        
        self.upload_files_btn = QPushButton("Upload Files")
        self.upload_files_btn.clicked.connect(self.upload_files)
        self.upload_files_btn.setEnabled(False)
        button_layout.addWidget(self.upload_files_btn)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
    
    def setup_connections(self):
        """Setup signal connections."""
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree.currentItemChanged.connect(self.on_current_item_changed)
    
    def refresh_tree(self):
        """Refresh the tree with current data."""
        self.tree.clear()
        
        # Get all cells
        result = self.api.get_all_cells()
        if not result['success']:
            return
        
        cells = result['cells']
        
        for cell in cells:
            # Create cell item
            cell_item = QTreeWidgetItem([
                cell['cell_name'],
                f"{cell.get('file_count', 0)} experiments",
                f"{cell.get('chemistry', 'Unknown')} chemistry"
            ])
            
            # Store cell data
            cell_item.setData(0, Qt.UserRole, {
                'type': 'cell',
                'cell_id': cell['id'],
                'cell_name': cell['cell_name'],
                'data': cell
            })
            
            # Set cell icon and font
            font = QFont()
            font.setBold(True)
            cell_item.setFont(0, font)
            
            # Get files for this cell
            files_result = self.api.get_cell_files(cell['id'])
            if files_result['success']:
                files = files_result['files']
                
                # Group files by experiment (assume dual files have similar names)
                experiments = self._group_files_into_experiments(files)
                
                for exp_name, exp_files in experiments.items():
                    exp_item = self._create_experiment_item(exp_name, exp_files)
                    cell_item.addChild(exp_item)
            
            self.tree.addTopLevelItem(cell_item)
        
        # Expand all cells by default
        self.tree.expandAll()
        
        # Resize columns to content
        for i in range(3):
            self.tree.resizeColumnToContents(i)
    
    def _group_files_into_experiments(self, files: List[Dict]) -> Dict[str, List[Dict]]:
        """Group files into experiments based on naming patterns."""
        experiments = {}
        
        # Group by base filename (remove .par and .csv extensions)
        for file_info in files:
            original_name = file_info['original_filename']
            
            # Extract base name
            if original_name.endswith('.par.csv'):
                base_name = original_name[:-8]  # Remove .par.csv
            elif original_name.endswith('.par'):
                base_name = original_name[:-4]  # Remove .par
            elif original_name.endswith('.csv'):
                base_name = original_name[:-4]  # Remove .csv
            else:
                base_name = original_name
            
            if base_name not in experiments:
                experiments[base_name] = []
            experiments[base_name].append(file_info)
        
        return experiments
    
    def _create_experiment_item(self, exp_name: str, files: List[Dict]) -> QTreeWidgetItem:
        """Create tree item for experiment."""
        
        # Determine experiment status
        statuses = [f['processing_status'] for f in files]
        if any(status == 'failed' for status in statuses):
            status = 'failed'
            status_color = QColor(200, 50, 50)  # Red
        elif any(status == 'processing' for status in statuses):
            status = 'processing'
            status_color = QColor(50, 150, 200)  # Blue
        elif all(status == 'completed' for status in statuses):
            status = 'completed'
            status_color = QColor(50, 150, 50)  # Green
        else:
            status = 'uploaded'
            status_color = QColor(150, 150, 50)  # Yellow
        
        # Create experiment info
        file_types = []
        temperatures = []
        for file_info in files:
            # Determine file type from filename since 'file_type' field doesn't exist
            filename = file_info.get('original_filename', '')
            if filename.endswith('.par'):
                file_types.append('PAR')
            elif filename.endswith('.par.csv'):
                file_types.append('CSV')
            elif filename.endswith('.csv'):
                file_types.append('CSV')
            else:
                file_types.append('DATA')
                
            if file_info.get('temperature_c'):
                temperatures.append(file_info['temperature_c'])
        
        temp_info = f", {temperatures[0]:.1f}°C" if temperatures else ""
        info = f"{'+'.join(sorted(set(file_types)))}{temp_info}"
        
        # Create item
        exp_item = QTreeWidgetItem([exp_name, status.title(), info])
        
        # Set status color
        exp_item.setForeground(1, QBrush(status_color))
        
        # Store experiment data
        exp_item.setData(0, Qt.UserRole, {
            'type': 'experiment',
            'experiment_name': exp_name,
            'files': files,
            'status': status,
            'primary_file_id': files[0]['file_id'] if files else None
        })
        
        return exp_item
    
    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item click."""
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        
        if data['type'] == 'cell':
            # Cell clicked - enable upload button
            self.upload_files_btn.setEnabled(True)
            self.cell_selected.emit(data['cell_id'], data['cell_name'])
            
        elif data['type'] == 'experiment':
            # Experiment clicked - load data
            parent_data = item.parent().data(0, Qt.UserRole)
            if parent_data and data['primary_file_id']:
                self.experiment_selected.emit(
                    parent_data['cell_id'],
                    parent_data['cell_name'], 
                    data['primary_file_id']
                )
    
    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item double-click."""
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        
        if data['type'] == 'experiment':
            # Experiment double-clicked - open review modal
            parent_data = item.parent().data(0, Qt.UserRole)
            if parent_data and data['primary_file_id']:
                self.experiment_double_clicked.emit(
                    parent_data['cell_id'],
                    parent_data['cell_name'],
                    data['primary_file_id']
                )
    
    def on_current_item_changed(self, current: QTreeWidgetItem, previous: QTreeWidgetItem):
        """Handle current item change."""
        if not current:
            self.upload_files_btn.setEnabled(False)
    
    def show_context_menu(self, position):
        """Show context menu for tree items."""
        item = self.tree.itemAt(position)
        if not item:
            return
        
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        
        menu = QMenu(self)
        
        if data['type'] == 'cell':
            # Cell context menu
            upload_action = menu.addAction("Upload Files")
            upload_action.triggered.connect(lambda: self.upload_files_requested.emit(data['cell_name']))
            
            menu.addSeparator()
            edit_action = menu.addAction("Edit Cell")
            # TODO: Connect to cell editing dialog
            
        elif data['type'] == 'experiment':
            # Experiment context menu
            review_action = menu.addAction("Review/Edit")
            parent_data = item.parent().data(0, Qt.UserRole)
            review_action.triggered.connect(lambda: self.experiment_double_clicked.emit(
                parent_data['cell_id'], parent_data['cell_name'], data['primary_file_id']
            ))
            
            menu.addSeparator()
            
            remove_action = menu.addAction("Remove")
            remove_action.triggered.connect(lambda: self.remove_experiment(item))
            
            if data['status'] == 'failed':
                reprocess_action = menu.addAction("Reprocess")
                # TODO: Connect to reprocessing
        
        menu.exec(self.tree.mapToGlobal(position))
    
    def remove_experiment(self, item: QTreeWidgetItem):
        """Remove experiment after confirmation."""
        data = item.data(0, Qt.UserRole)
        parent_data = item.parent().data(0, Qt.UserRole)
        
        reply = QMessageBox.question(
            self, "Remove Experiment",
            f"Are you sure you want to remove experiment '{data['experiment_name']}'?\\n\\n"
            "This will delete all associated files and data.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # TODO: Implement file removal via backend API
            QMessageBox.information(self, "Remove Experiment", "Experiment removal not yet implemented")
    
    def create_new_cell(self):
        """Create new cell using creation dialog."""
        from qt_app.dialogs.cell_creation_dialog import CellCreationDialog
        
        dialog = CellCreationDialog(self.api, self)
        if dialog.exec() == QDialog.Accepted:
            # Refresh tree to show new cell
            self.refresh_tree()
    
    def upload_files(self):
        """Upload files for selected cell."""
        current_item = self.tree.currentItem()
        if not current_item:
            return
        
        # Find the cell item
        cell_item = current_item
        while cell_item.parent():
            cell_item = cell_item.parent()
        
        cell_data = cell_item.data(0, Qt.UserRole)
        if cell_data and cell_data['type'] == 'cell':
            self.upload_files_requested.emit(cell_data['cell_name'])
    
    def get_selected_cell(self) -> Optional[Dict[str, Any]]:
        """Get currently selected cell data."""
        current_item = self.tree.currentItem()
        if not current_item:
            return None
        
        # Find the cell item
        cell_item = current_item
        while cell_item.parent():
            cell_item = cell_item.parent()
        
        cell_data = cell_item.data(0, Qt.UserRole)
        if cell_data and cell_data['type'] == 'cell':
            return cell_data
        
        return None