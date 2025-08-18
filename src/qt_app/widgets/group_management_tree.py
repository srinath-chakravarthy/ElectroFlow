"""
Group Management Tree Widget

Hierarchical tree for managing user-defined groups of technique segments.
Supports drag-and-drop, group nesting, and group operations.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QMenu, QMessageBox, QInputDialog, QLineEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QBrush, QColor, QDrag, QPixmap
from typing import Dict, List, Any, Optional


class GroupManagementTreeWidget(QWidget):
    """Tree widget for hierarchical group management."""
    
    # Signals
    group_selected = Signal(int)  # group_id
    group_analysis_requested = Signal(int)  # group_id
    group_plotting_requested = Signal(int)  # group_id
    
    def __init__(self, backend_api, parent=None):
        super().__init__(parent)
        self.api = backend_api
        self.current_cell_id = None
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Groups Management")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_groups)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Group Name", "Type", "Count", "Description"])
        self.tree.setRootIsDecorated(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setDragDropMode(QTreeWidget.InternalMove)
        
        # Enable context menu
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.tree)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.new_group_btn = QPushButton("New Group")
        self.new_group_btn.clicked.connect(self.create_new_group)
        self.new_group_btn.setEnabled(False)
        button_layout.addWidget(self.new_group_btn)
        
        self.rename_group_btn = QPushButton("Rename")
        self.rename_group_btn.clicked.connect(self.rename_selected_group)
        self.rename_group_btn.setEnabled(False)
        button_layout.addWidget(self.rename_group_btn)
        
        button_layout.addStretch()
        
        self.analyze_btn = QPushButton("Analyze")
        self.analyze_btn.clicked.connect(self.analyze_selected_group)
        self.analyze_btn.setEnabled(False)
        button_layout.addWidget(self.analyze_btn)
        
        layout.addLayout(button_layout)
        
        # Instructions
        instructions = QLabel(
            "Drag segments or groups to reorganize | Right-click for options | "
            "Double-click to analyze"
        )
        instructions.setStyleSheet("color: gray; font-size: 10px;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
    
    def setup_connections(self):
        """Setup signal connections."""
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree.currentItemChanged.connect(self.on_current_item_changed)
    
    def set_active_cell(self, cell_id: int):
        """Set the active cell and refresh groups."""
        self.current_cell_id = cell_id
        self.new_group_btn.setEnabled(True)
        self.refresh_groups()
    
    def refresh_groups(self):
        """Refresh the groups tree for current cell."""
        self.tree.clear()
        
        if not self.current_cell_id:
            self.new_group_btn.setEnabled(False)
            return
        
        try:
            # Get all groups for current cell
            result = self.api.get_group_analytics_summary(self.current_cell_id)
            
            if not result['success']:
                self._show_error(f"Failed to load groups: {result['error']}")
                return
            
            groups = result.get('groups_summary', [])
            
            if not groups:
                # Show placeholder
                placeholder_item = QTreeWidgetItem([
                    "No groups created",
                    "Create groups from selected segments",
                    "",
                    ""
                ])
                placeholder_item.setForeground(0, QBrush(QColor(150, 150, 150)))
                self.tree.addTopLevelItem(placeholder_item)
                return
            
            # Create group tree (simplified - no hierarchical structure yet)
            for group_data in groups:
                group_item = self._create_group_item(group_data)
                self.tree.addTopLevelItem(group_item)
            
            # Expand all groups
            self.tree.expandAll()
            
            # Resize columns
            for i in range(4):
                self.tree.resizeColumnToContents(i)
                
        except Exception as e:
            self._show_error(f"Error loading groups: {str(e)}")
    
    def _create_group_item(self, group_data: Dict) -> QTreeWidgetItem:
        """Create tree item for group."""
        
        group_name = group_data.get('group_name', 'Unknown')
        group_type = group_data.get('group_type', 'Custom')
        technique_count = group_data.get('technique_count', 0)
        description = f"{technique_count} techniques"
        
        # Add quality indicator if available
        quality = group_data.get('overall_quality')
        if quality is not None:
            description += f" (Q: {quality:.2f})"
        
        group_item = QTreeWidgetItem([
            group_name,
            group_type,
            str(technique_count),
            description
        ])
        
        # Set group icon color based on type
        type_colors = {
            'OCV': QColor(100, 150, 100),
            'CC': QColor(150, 100, 100),  
            'GEIS': QColor(100, 100, 150),
            'Custom': QColor(150, 150, 100)
        }
        color = type_colors.get(group_type, QColor(100, 100, 100))
        group_item.setForeground(1, QBrush(color))
        
        # Make group name bold
        font = QFont()
        font.setBold(True)
        group_item.setFont(0, font)
        
        # Store group data
        group_item.setData(0, Qt.UserRole, {
            'type': 'group',
            'group_id': group_data.get('group_id'),
            'group_name': group_name,
            'group_type': group_type,
            'data': group_data
        })
        
        # TODO: Add technique items as children
        # For now, just show count
        
        return group_item
    
    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item click."""
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        
        if data['type'] == 'group':
            group_id = data.get('group_id')
            if group_id:
                self.group_selected.emit(group_id)
        
        self.update_button_states(item)
    
    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item double-click."""
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        
        if data['type'] == 'group':
            group_id = data.get('group_id')
            if group_id:
                self.group_analysis_requested.emit(group_id)
    
    def on_current_item_changed(self, current: QTreeWidgetItem, previous: QTreeWidgetItem):
        """Handle current item change."""
        self.update_button_states(current)
    
    def update_button_states(self, current_item: QTreeWidgetItem):
        """Update button enabled states based on selection."""
        if not current_item:
            self.rename_group_btn.setEnabled(False)
            self.analyze_btn.setEnabled(False)
            return
        
        data = current_item.data(0, Qt.UserRole)
        if data and data['type'] == 'group':
            self.rename_group_btn.setEnabled(True)
            self.analyze_btn.setEnabled(True)
        else:
            self.rename_group_btn.setEnabled(False)
            self.analyze_btn.setEnabled(False)
    
    def add_segments_to_group(self, segment_ids: List[str], suggested_name: str):
        """Add segments to a new or existing group."""
        if not segment_ids:
            return
        
        # Ask user for group name
        group_name, ok = QInputDialog.getText(
            self, "Create Group", 
            f"Enter group name:", 
            QLineEdit.Normal, 
            suggested_name
        )
        
        if not ok or not group_name.strip():
            return
        
        group_name = group_name.strip()
        
        try:
            # Create new group via backend API
            # TODO: Implement group creation in backend API
            # For now, show placeholder
            QMessageBox.information(
                self, "Create Group",
                f"Group '{group_name}' would be created with {len(segment_ids)} segments.\n"
                "Group creation not yet fully implemented."
            )
            
            # Refresh groups after creation
            self.refresh_groups()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create group: {str(e)}")
    
    def create_new_group(self):
        """Create new empty group."""
        group_name, ok = QInputDialog.getText(
            self, "New Group", 
            "Enter group name:", 
            QLineEdit.Normal, 
            "New_Group"
        )
        
        if not ok or not group_name.strip():
            return
        
        # TODO: Create empty group via backend API
        QMessageBox.information(
            self, "New Group",
            f"Empty group '{group_name}' creation not yet implemented."
        )
    
    def rename_selected_group(self):
        """Rename the currently selected group."""
        current_item = self.tree.currentItem()
        if not current_item:
            return
        
        data = current_item.data(0, Qt.UserRole)
        if not data or data['type'] != 'group':
            return
        
        current_name = data['group_name']
        new_name, ok = QInputDialog.getText(
            self, "Rename Group",
            "Enter new name:",
            QLineEdit.Normal,
            current_name
        )
        
        if not ok or not new_name.strip() or new_name.strip() == current_name:
            return
        
        # TODO: Rename group via backend API
        QMessageBox.information(
            self, "Rename Group",
            f"Renaming '{current_name}' to '{new_name}' not yet implemented."
        )
    
    def analyze_selected_group(self):
        """Analyze the currently selected group."""
        current_item = self.tree.currentItem()
        if not current_item:
            return
        
        data = current_item.data(0, Qt.UserRole)
        if not data or data['type'] != 'group':
            return
        
        group_id = data.get('group_id')
        if group_id:
            self.group_analysis_requested.emit(group_id)
    
    def show_context_menu(self, position):
        """Show context menu for tree items."""
        item = self.tree.itemAt(position)
        if not item:
            return
        
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        
        menu = QMenu(self)
        
        if data['type'] == 'group':
            # Group context menu
            analyze_action = menu.addAction("Analyze Group")
            analyze_action.triggered.connect(self.analyze_selected_group)
            
            plot_action = menu.addAction("Plot Group")
            plot_action.triggered.connect(lambda: self._plot_group(data.get('group_id')))
            
            menu.addSeparator()
            
            rename_action = menu.addAction("Rename")
            rename_action.triggered.connect(self.rename_selected_group)
            
            duplicate_action = menu.addAction("Duplicate")
            # TODO: Connect to duplication
            
            menu.addSeparator()
            
            remove_action = menu.addAction("Remove Group")
            remove_action.triggered.connect(lambda: self._remove_group(item))
        
        menu.exec(self.tree.mapToGlobal(position))
    
    def _plot_group(self, group_id: int):
        """Request plotting for group."""
        if group_id:
            self.group_plotting_requested.emit(group_id)
    
    def _remove_group(self, item: QTreeWidgetItem):
        """Remove group after confirmation."""
        data = item.data(0, Qt.UserRole)
        group_name = data['group_name']
        
        reply = QMessageBox.question(
            self, "Remove Group",
            f"Are you sure you want to remove group '{group_name}'?\\n\\n"
            "This will not delete the underlying data, only the group definition.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # TODO: Remove group via backend API
            QMessageBox.information(
                self, "Remove Group",
                f"Group '{group_name}' removal not yet implemented."
            )
    
    def _show_error(self, message: str):
        """Show error message in tree."""
        self.tree.clear()
        error_item = QTreeWidgetItem([message, "", "", ""])
        error_item.setForeground(0, QBrush(QColor(200, 50, 50)))
        self.tree.addTopLevelItem(error_item)
    
    def get_selected_group_id(self) -> Optional[int]:
        """Get currently selected group ID."""
        current_item = self.tree.currentItem()
        if not current_item:
            return None
        
        data = current_item.data(0, Qt.UserRole)
        if data and data['type'] == 'group':
            return data.get('group_id')
        
        return None