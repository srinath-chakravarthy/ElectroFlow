"""
Actions/Segments Tree Widget

Displays technique actions and segments for multi-selection and grouping.
Supports Shift/Ctrl-click for multi-selection and drag-to-group operations.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QMenu, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QBrush, QColor
from typing import Dict, List, Any, Optional, Set


class ActionsSegmentsTreeWidget(QWidget):
    """Tree widget for actions and segments with multi-selection."""
    
    # Signals
    segments_selected = Signal(list)  # List of selected segment IDs
    create_group_requested = Signal(list, str)  # segments, suggested_name
    
    def __init__(self, backend_api, parent=None):
        super().__init__(parent)
        self.api = backend_api
        self.current_file_id = None
        self.current_cell_id = None
        self.selected_segments = set()
        
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Actions & Segments")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Selection info
        self.selection_label = QLabel("0 segments selected")
        self.selection_label.setStyleSheet("color: gray; font-style: italic;")
        header_layout.addWidget(self.selection_label)
        
        layout.addLayout(header_layout)
        
        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Action/Segment", "Technique", "Duration", "Points"])
        self.tree.setRootIsDecorated(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        
        # Enable context menu
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.tree)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all_segments)
        self.select_all_btn.setEnabled(False)
        button_layout.addWidget(self.select_all_btn)
        
        self.clear_selection_btn = QPushButton("Clear Selection")
        self.clear_selection_btn.clicked.connect(self.clear_selection)
        self.clear_selection_btn.setEnabled(False)
        button_layout.addWidget(self.clear_selection_btn)
        
        button_layout.addStretch()
        
        self.create_group_btn = QPushButton("Create Group")
        self.create_group_btn.clicked.connect(self.create_group_from_selection)
        self.create_group_btn.setEnabled(False)
        button_layout.addWidget(self.create_group_btn)
        
        layout.addLayout(button_layout)
        
        # Instructions
        instructions = QLabel(
            "Ctrl+Click: Multi-select segments | Shift+Click: Range select | "
            "Right-click: Context menu"
        )
        instructions.setStyleSheet("color: gray; font-size: 10px;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
    
    def setup_connections(self):
        """Setup signal connections."""
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.itemSelectionChanged.connect(self.on_selection_changed)
    
    def set_file_data(self, cell_id: int, file_id: str):
        """Set the current file and load its segments."""
        self.current_cell_id = cell_id
        self.current_file_id = file_id
        self.selected_segments.clear()
        self.refresh_segments()
    
    def refresh_segments(self):
        """Refresh the segments tree for current file."""
        self.tree.clear()
        
        if not self.current_file_id:
            self.select_all_btn.setEnabled(False)
            return
        
        try:
            # Get file data with analysis results
            result = self.api.get_file_analysis_results(self.current_file_id)
            
            if not result['success']:
                self._show_error(f"Failed to load analysis: {result['error']}")
                return
            
            analysis_data = result.get('analysis_results', {})
            
            # Get file preview for basic info
            preview_result = self.api.get_file_data_preview(self.current_file_id, n_rows=100)
            if not preview_result['success']:
                self._show_error(f"Failed to load file data: {preview_result['error']}")
                return
            
            stats = preview_result.get('stats', {})
            techniques = stats.get('techniques', [])
            
            # Create action items (simplified - using placeholder data)
            for i, technique in enumerate(techniques):
                action_item = self._create_action_item(i, technique, analysis_data)
                self.tree.addTopLevelItem(action_item)
            
            # If no techniques found, create placeholder
            if not techniques:
                placeholder_item = QTreeWidgetItem([
                    "No segments found",
                    "Unknown",
                    "N/A",
                    "N/A"
                ])
                placeholder_item.setForeground(0, QBrush(QColor(150, 150, 150)))
                self.tree.addTopLevelItem(placeholder_item)
            
            # Expand all actions
            self.tree.expandAll()
            
            # Resize columns
            for i in range(4):
                self.tree.resizeColumnToContents(i)
            
            self.select_all_btn.setEnabled(len(techniques) > 0)
            
        except Exception as e:
            self._show_error(f"Error loading segments: {str(e)}")
    
    def _create_action_item(self, action_index: int, technique: str, 
                           analysis_data: Dict) -> QTreeWidgetItem:
        """Create tree item for action with segments."""
        
        # Action-level item
        action_name = f"Action {action_index + 1}"
        action_item = QTreeWidgetItem([
            action_name,
            technique,
            "Multi-segment",
            "N/A"
        ])
        
        # Make action item bold
        font = QFont()
        font.setBold(True)
        action_item.setFont(0, font)
        
        # Store action data
        action_item.setData(0, Qt.UserRole, {
            'type': 'action',
            'action_index': action_index,
            'technique': technique
        })
        
        # Create segment items (simplified - using placeholder data)
        num_segments = 3  # Placeholder
        for seg_index in range(num_segments):
            segment_item = self._create_segment_item(action_index, seg_index, technique)
            action_item.addChild(segment_item)
        
        return action_item
    
    def _create_segment_item(self, action_index: int, segment_index: int, 
                            technique: str) -> QTreeWidgetItem:
        """Create tree item for individual segment."""
        
        segment_id = f"{self.current_file_id}_action{action_index}_seg{segment_index}"
        segment_name = f"Segment {segment_index + 1}"
        
        # Placeholder data
        duration = f"{(segment_index + 1) * 100:.1f}s"
        points = f"{(segment_index + 1) * 1000}"
        
        segment_item = QTreeWidgetItem([
            segment_name,
            technique,
            duration,
            points
        ])
        
        # Store segment data
        segment_item.setData(0, Qt.UserRole, {
            'type': 'segment',
            'segment_id': segment_id,
            'action_index': action_index,
            'segment_index': segment_index,
            'technique': technique,
            'file_id': self.current_file_id
        })
        
        return segment_item
    
    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item click for selection."""
        data = item.data(0, Qt.UserRole)
        if not data or data['type'] != 'segment':
            return
        
        segment_id = data['segment_id']
        
        # Handle multi-selection
        modifiers = self.tree.keyboardModifiers()
        
        if modifiers & Qt.ControlModifier:
            # Ctrl+Click: Toggle selection
            if segment_id in self.selected_segments:
                self.selected_segments.remove(segment_id)
                self._set_item_selected(item, False)
            else:
                self.selected_segments.add(segment_id)
                self._set_item_selected(item, True)
        else:
            # Regular click: Clear selection and select this item
            self.clear_selection()
            self.selected_segments.add(segment_id)
            self._set_item_selected(item, True)
        
        self.update_selection_display()
    
    def on_selection_changed(self):
        """Handle selection change."""
        # Update selected segments based on Qt selection
        selected_items = self.tree.selectedItems()
        self.selected_segments.clear()
        
        for item in selected_items:
            data = item.data(0, Qt.UserRole)
            if data and data['type'] == 'segment':
                self.selected_segments.add(data['segment_id'])
        
        self.update_selection_display()
    
    def update_selection_display(self):
        """Update selection display and button states."""
        count = len(self.selected_segments)
        
        if count == 0:
            self.selection_label.setText("0 segments selected")
            self.create_group_btn.setEnabled(False)
            self.clear_selection_btn.setEnabled(False)
        elif count == 1:
            self.selection_label.setText("1 segment selected")
            self.create_group_btn.setEnabled(True)
            self.clear_selection_btn.setEnabled(True)
        else:
            self.selection_label.setText(f"{count} segments selected")
            self.create_group_btn.setEnabled(True)
            self.clear_selection_btn.setEnabled(True)
        
        # Emit selection signal
        segment_list = list(self.selected_segments)
        self.segments_selected.emit(segment_list)
    
    def _set_item_selected(self, item: QTreeWidgetItem, selected: bool):
        """Set visual selection state for item."""
        if selected:
            item.setBackground(0, QBrush(QColor(200, 220, 255)))
        else:
            item.setBackground(0, QBrush())
    
    def select_all_segments(self):
        """Select all segments."""
        self.selected_segments.clear()
        
        for i in range(self.tree.topLevelItemCount()):
            action_item = self.tree.topLevelItem(i)
            for j in range(action_item.childCount()):
                segment_item = action_item.child(j)
                data = segment_item.data(0, Qt.UserRole)
                if data and data['type'] == 'segment':
                    self.selected_segments.add(data['segment_id'])
                    self._set_item_selected(segment_item, True)
        
        self.update_selection_display()
    
    def clear_selection(self):
        """Clear all selection."""
        self.selected_segments.clear()
        
        # Clear visual selection
        for i in range(self.tree.topLevelItemCount()):
            action_item = self.tree.topLevelItem(i)
            for j in range(action_item.childCount()):
                segment_item = action_item.child(j)
                self._set_item_selected(segment_item, False)
        
        self.tree.clearSelection()
        self.update_selection_display()
    
    def create_group_from_selection(self):
        """Create group from selected segments."""
        if not self.selected_segments:
            return
        
        # Suggest group name based on selected techniques
        techniques = set()
        for segment_id in self.selected_segments:
            # Extract technique from segment (simplified)
            techniques.add("OCV")  # Placeholder
        
        if len(techniques) == 1:
            suggested_name = list(techniques)[0] + "_Group"
        else:
            suggested_name = "Mixed_Techniques_Group"
        
        self.create_group_requested.emit(list(self.selected_segments), suggested_name)
    
    def show_context_menu(self, position):
        """Show context menu."""
        item = self.tree.itemAt(position)
        if not item:
            return
        
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        
        menu = QMenu(self)
        
        if data['type'] == 'action':
            # Action context menu
            select_all_action = menu.addAction("Select All Segments")
            select_all_action.triggered.connect(lambda: self._select_action_segments(item))
            
        elif data['type'] == 'segment':
            # Segment context menu
            if data['segment_id'] not in self.selected_segments:
                select_action = menu.addAction("Select Segment")
                select_action.triggered.connect(lambda: self._select_single_segment(item))
            else:
                deselect_action = menu.addAction("Deselect Segment")
                deselect_action.triggered.connect(lambda: self._deselect_single_segment(item))
            
            menu.addSeparator()
            
            view_action = menu.addAction("View Segment Data")
            # TODO: Connect to segment data viewer
        
        menu.exec(self.tree.mapToGlobal(position))
    
    def _select_action_segments(self, action_item: QTreeWidgetItem):
        """Select all segments under an action."""
        for i in range(action_item.childCount()):
            segment_item = action_item.child(i)
            data = segment_item.data(0, Qt.UserRole)
            if data and data['type'] == 'segment':
                self.selected_segments.add(data['segment_id'])
                self._set_item_selected(segment_item, True)
        
        self.update_selection_display()
    
    def _select_single_segment(self, segment_item: QTreeWidgetItem):
        """Select a single segment."""
        data = segment_item.data(0, Qt.UserRole)
        if data and data['type'] == 'segment':
            self.selected_segments.add(data['segment_id'])
            self._set_item_selected(segment_item, True)
            self.update_selection_display()
    
    def _deselect_single_segment(self, segment_item: QTreeWidgetItem):
        """Deselect a single segment."""
        data = segment_item.data(0, Qt.UserRole)
        if data and data['type'] == 'segment':
            self.selected_segments.discard(data['segment_id'])
            self._set_item_selected(segment_item, False)
            self.update_selection_display()
    
    def _show_error(self, message: str):
        """Show error message in tree."""
        self.tree.clear()
        error_item = QTreeWidgetItem([message, "", "", ""])
        error_item.setForeground(0, QBrush(QColor(200, 50, 50)))
        self.tree.addTopLevelItem(error_item)
        self.select_all_btn.setEnabled(False)
    
    def get_selected_segments(self) -> List[str]:
        """Get list of selected segment IDs."""
        return list(self.selected_segments)