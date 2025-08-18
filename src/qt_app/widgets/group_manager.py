"""
Group Manager Widget

Provides interface for:
- Creating data groups
- Managing group membership
- Viewing group analysis
- Drag & drop group creation
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, 
    QLabel, QListWidgetItem, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt, Signal


class GroupManagerWidget(QWidget):
    """Widget for managing data groups."""
    
    # Signals
    group_selected = Signal(int)  # group_id
    
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
        title_label = QLabel("Group Management")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)
        
        # Group list
        self.group_list = QListWidget()
        self.group_list.itemClicked.connect(self.on_group_selected)
        layout.addWidget(self.group_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.new_group_btn = QPushButton("New Group")
        self.new_group_btn.clicked.connect(self.create_new_group)
        self.new_group_btn.setEnabled(False)  # Disabled until cell selected
        button_layout.addWidget(self.new_group_btn)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_groups)
        button_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(button_layout)
        
        # Status
        self.status_label = QLabel("No cell selected")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.status_label)
    
    def set_active_cell(self, cell_id, cell_name):
        """Set the active cell and refresh groups."""
        self.active_cell_id = cell_id
        self.active_cell_name = cell_name
        
        self.new_group_btn.setEnabled(True)
        self.status_label.setText(f"Active: {cell_name}")
        
        self.refresh_groups()
    
    def refresh_groups(self):
        """Refresh the group list from the backend."""
        self.group_list.clear()
        
        if not self.active_cell_id:
            return
        
        # TODO: Implement group listing in backend API
        # For now, show placeholder groups
        placeholder_groups = [
            {"id": 1, "name": "Formation Cycles", "description": "Initial formation data"},
            {"id": 2, "name": "Rest Phases", "description": "OCV rest measurements"},
            {"id": 3, "name": "Pulse Tests", "description": "Current pulse experiments"}
        ]
        
        for group in placeholder_groups:
            item_text = f"{group['name']} - {group['description']}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, group['id'])
            self.group_list.addItem(item)
    
    def create_new_group(self):
        """Create a new group."""
        if not self.active_cell_id:
            QMessageBox.warning(self, "No Cell Selected", 
                              "Please select a cell before creating groups.")
            return
        
        # Get group name from user
        group_name, ok = QInputDialog.getText(
            self, 
            "Create New Group", 
            "Enter group name:",
            text="New Group"
        )
        
        if ok and group_name.strip():
            # TODO: Implement group creation in backend API
            QMessageBox.information(self, "Group Created", 
                                  f"Group '{group_name}' created successfully.")
            self.refresh_groups()
    
    def on_group_selected(self, item):
        """Handle group selection."""
        group_id = item.data(Qt.UserRole)
        if group_id:
            self.group_selected.emit(group_id)
    
    def enable_group_creation(self, segment_ids):
        """Enable group creation when segments are selected."""
        # TODO: Implement automatic group creation from selected segments
        if segment_ids:
            self.status_label.setText(f"{len(segment_ids)} segments selected for grouping")
        else:
            self.status_label.setText(f"Active: {self.active_cell_name}")