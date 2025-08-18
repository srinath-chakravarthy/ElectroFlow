"""
Cell Selector Widget

Provides interface for:
- Viewing all available cells
- Selecting active cell
- Creating new cells
- Editing cell metadata
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QPushButton, 
    QHeaderView, QAbstractItemView, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, Signal, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QStandardItemModel, QStandardItem

from qt_app.dialogs.create_cell import CreateCellDialog


class CellTableModel(QAbstractTableModel):
    """Table model for displaying cell data."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cells = []
        self.headers = ['Name', 'Description', 'Chemistry', 'Capacity (Ah)', 'Files', 'Created']
    
    def rowCount(self, parent=QModelIndex()):
        return len(self.cells)
    
    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)
    
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self.cells):
            return None
        
        cell = self.cells[index.row()]
        column = index.column()
        
        if role == Qt.DisplayRole:
            if column == 0:
                return cell.get('cell_name', '')
            elif column == 1:
                return cell.get('description', '')
            elif column == 2:
                return cell.get('chemistry', '')
            elif column == 3:
                capacity = cell.get('capacity_ah')
                return f"{capacity:.3f}" if capacity else ""
            elif column == 4:
                return str(cell.get('file_count', 0))
            elif column == 5:
                return cell.get('created_at', '')[:10] if cell.get('created_at') else ""
        
        elif role == Qt.UserRole:
            return cell.get('id')
        
        return None
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None
    
    def update_cells(self, cells):
        """Update the cell data."""
        self.beginResetModel()
        self.cells = cells
        self.endResetModel()


class CellSelectorWidget(QWidget):
    """Widget for cell selection and management."""
    
    # Signals
    cell_selected = Signal(int, str)  # cell_id, cell_name
    
    def __init__(self, backend_api, parent=None):
        super().__init__(parent)
        self.api = backend_api
        self.setup_ui()
        self.refresh_cells()
    
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Cell table
        self.cell_model = CellTableModel()
        self.cell_table = QTableView()
        self.cell_table.setModel(self.cell_model)
        self.cell_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.cell_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.cell_table.selectionModel().currentRowChanged.connect(self.on_cell_selection_changed)
        
        # Configure table
        header = self.cell_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Name
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Description
        
        layout.addWidget(self.cell_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.new_cell_btn = QPushButton("New Cell")
        self.new_cell_btn.clicked.connect(self.create_new_cell)
        button_layout.addWidget(self.new_cell_btn)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_cells)
        button_layout.addWidget(self.refresh_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
    
    def refresh_cells(self):
        """Refresh the cell list from the backend."""
        result = self.api.get_all_cells()
        
        if result['success']:
            self.cell_model.update_cells(result['cells'])
            if result['cells']:
                # Select first cell by default
                first_index = self.cell_model.index(0, 0)
                self.cell_table.setCurrentIndex(first_index)
        else:
            QMessageBox.warning(self, "Error", f"Failed to load cells: {result['error']}")
    
    def on_cell_selection_changed(self, current, previous):
        """Handle cell selection changes."""
        if current.isValid():
            cell_id = self.cell_model.data(current, Qt.UserRole)
            cell_name = self.cell_model.data(current, Qt.DisplayRole)
            
            if cell_id and cell_name:
                self.cell_selected.emit(cell_id, cell_name)
    
    def create_new_cell(self):
        """Show dialog to create a new cell."""
        dialog = CreateCellDialog(self.api, self)
        
        if dialog.exec() == QDialog.Accepted:
            self.refresh_cells()
            # Select the newly created cell
            cell_name = dialog.get_cell_name()
            self.select_cell_by_name(cell_name)
    
    def select_cell_by_name(self, cell_name):
        """Select a cell by name in the table."""
        for row in range(self.cell_model.rowCount()):
            index = self.cell_model.index(row, 0)
            if self.cell_model.data(index, Qt.DisplayRole) == cell_name:
                self.cell_table.setCurrentIndex(index)
                break