"""
Create Cell Dialog

Dialog for creating new battery cells with metadata input.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, 
    QComboBox, QDoubleSpinBox, QTextEdit, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt


class CreateCellDialog(QDialog):
    """Dialog for creating new cells."""
    
    def __init__(self, backend_api, parent=None):
        super().__init__(parent)
        self.api = backend_api
        self.cell_name = ""
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Create New Cell")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Form layout
        form_layout = QFormLayout()
        
        # Cell name (required)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., CELL_001, TestCell_A")
        form_layout.addRow("Cell Name*:", self.name_edit)
        
        # Description
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Brief description of the cell")
        form_layout.addRow("Description:", self.description_edit)
        
        # Chemistry
        self.chemistry_combo = QComboBox()
        self.chemistry_combo.addItems(["Li-ion", "LFP", "NMC", "LCO", "NCA", "Other"])
        self.chemistry_combo.setCurrentText("Li-ion")
        form_layout.addRow("Chemistry:", self.chemistry_combo)
        
        # Capacity
        self.capacity_spin = QDoubleSpinBox()
        self.capacity_spin.setSuffix(" Ah")
        self.capacity_spin.setDecimals(3)
        self.capacity_spin.setRange(0.001, 1000.0)
        self.capacity_spin.setValue(1.0)
        self.capacity_spin.setSpecialValueText("Not specified")
        self.capacity_spin.setMinimum(0.0)
        form_layout.addRow("Capacity:", self.capacity_spin)
        
        # Notes
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.setPlaceholderText("Additional notes about the cell")
        form_layout.addRow("Notes:", self.notes_edit)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        
        self.create_btn = QPushButton("Create Cell")
        self.create_btn.setDefault(True)
        self.create_btn.clicked.connect(self.create_cell)
        button_layout.addWidget(self.create_btn)
        
        layout.addLayout(button_layout)
        
        # Set focus to name field
        self.name_edit.setFocus()
    
    def create_cell(self):
        """Create the cell using the backend API."""
        # Validate input
        cell_name = self.name_edit.text().strip()
        if not cell_name:
            QMessageBox.warning(self, "Validation Error", "Cell name is required.")
            self.name_edit.setFocus()
            return
        
        # Collect data
        description = self.description_edit.text().strip()
        chemistry = self.chemistry_combo.currentText()
        capacity = self.capacity_spin.value() if self.capacity_spin.value() > 0 else None
        notes = self.notes_edit.toPlainText().strip()
        
        # Create cell via API
        result = self.api.create_cell(
            cell_name=cell_name,
            description=description,
            chemistry=chemistry,
            capacity_ah=capacity,
            notes=notes
        )
        
        if result['success']:
            self.cell_name = cell_name
            QMessageBox.information(self, "Success", result['message'])
            self.accept()
        else:
            QMessageBox.critical(self, "Error", f"Failed to create cell: {result['error']}")
    
    def get_cell_name(self):
        """Get the name of the created cell."""
        return self.cell_name