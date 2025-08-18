"""
Cell Creation Dialog

Modal dialog for creating new cells with material metadata.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, 
    QTextEdit, QDoubleSpinBox, QComboBox, QPushButton, QLabel,
    QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from typing import Optional, Dict, Any


class CellCreationDialog(QDialog):
    """Dialog for creating new battery cells with material metadata."""
    
    def __init__(self, backend_api, parent=None):
        super().__init__(parent)
        self.api = backend_api
        self.cell_data = None
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Create New Cell")
        self.setModal(True)
        self.setMinimumWidth(450)
        self.setMaximumHeight(600)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Create New Battery Cell")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Basic info group
        basic_group = QGroupBox("Basic Information")
        basic_layout = QFormLayout(basic_group)
        
        self.cell_name_edit = QLineEdit()
        self.cell_name_edit.setPlaceholderText("e.g., CELL_001, Battery_A1")
        basic_layout.addRow("Cell Name*:", self.cell_name_edit)
        
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Brief description of the cell")
        basic_layout.addRow("Description:", self.description_edit)
        
        self.chemistry_combo = QComboBox()
        self.chemistry_combo.addItems([
            "Li_metal", "Li-ion", "LFP", "NMC", "LCO", "LMO", 
            "NCA", "LTO", "Na-ion", "Custom"
        ])
        basic_layout.addRow("Chemistry:", self.chemistry_combo)
        
        self.capacity_spinbox = QDoubleSpinBox()
        self.capacity_spinbox.setRange(0.0, 1000.0)
        self.capacity_spinbox.setDecimals(3)
        self.capacity_spinbox.setSuffix(" Ah")
        self.capacity_spinbox.setSpecialValueText("Not specified")
        basic_layout.addRow("Capacity:", self.capacity_spinbox)
        
        layout.addWidget(basic_group)
        
        # Material info group
        materials_group = QGroupBox("Active Material Information")
        materials_layout = QFormLayout(materials_group)
        
        # Cathode
        cathode_label = QLabel("Cathode Material")
        cathode_label.setFont(QFont("Arial", 10, QFont.Bold))
        materials_layout.addRow(cathode_label)
        
        self.cathode_material_edit = QLineEdit()
        self.cathode_material_edit.setPlaceholderText("e.g., LiFePO4, NMC811, LCO")
        materials_layout.addRow("Material:", self.cathode_material_edit)
        
        self.cathode_mass_spinbox = QDoubleSpinBox()
        self.cathode_mass_spinbox.setRange(0.0, 10000.0)
        self.cathode_mass_spinbox.setDecimals(2)
        self.cathode_mass_spinbox.setSuffix(" mg")
        self.cathode_mass_spinbox.setSpecialValueText("Not specified")
        materials_layout.addRow("Active Mass:", self.cathode_mass_spinbox)
        
        # Anode  
        anode_label = QLabel("Anode Material")
        anode_label.setFont(QFont("Arial", 10, QFont.Bold))
        materials_layout.addRow(anode_label)
        
        self.anode_material_edit = QLineEdit()
        self.anode_material_edit.setPlaceholderText("e.g., Li metal, Graphite, Silicon")
        materials_layout.addRow("Material:", self.anode_material_edit)
        
        self.anode_mass_spinbox = QDoubleSpinBox()
        self.anode_mass_spinbox.setRange(0.0, 10000.0)
        self.anode_mass_spinbox.setDecimals(2)
        self.anode_mass_spinbox.setSuffix(" mg")
        self.anode_mass_spinbox.setSpecialValueText("Not specified")
        materials_layout.addRow("Active Mass:", self.anode_mass_spinbox)
        
        layout.addWidget(materials_group)
        
        # Notes
        notes_group = QGroupBox("Additional Notes")
        notes_layout = QVBoxLayout(notes_group)
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.setPlaceholderText("Optional: Assembly notes, conditions, references...")
        notes_layout.addWidget(self.notes_edit)
        
        layout.addWidget(notes_group)
        
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
    
    def setup_connections(self):
        """Setup signal connections."""
        self.cell_name_edit.textChanged.connect(self.validate_input)
        self.validate_input()
    
    def validate_input(self):
        """Validate user input and enable/disable create button."""
        cell_name = self.cell_name_edit.text().strip()
        valid = bool(cell_name and len(cell_name) >= 3)
        self.create_btn.setEnabled(valid)
    
    def create_cell(self):
        """Create the cell via backend API."""
        try:
            # Collect data
            cell_data = {
                'cell_name': self.cell_name_edit.text().strip(),
                'description': self.description_edit.text().strip(),
                'chemistry': self.chemistry_combo.currentText(),
                'notes': self.notes_edit.toPlainText().strip()
            }
            
            # Add capacity if specified
            if self.capacity_spinbox.value() > 0:
                cell_data['capacity_ah'] = self.capacity_spinbox.value()
            
            # Add cathode material if specified
            if self.cathode_material_edit.text().strip():
                cell_data['cathode_material'] = self.cathode_material_edit.text().strip()
            if self.cathode_mass_spinbox.value() > 0:
                cell_data['cathode_mass_mg'] = self.cathode_mass_spinbox.value()
                
            # Add anode material if specified
            if self.anode_material_edit.text().strip():
                cell_data['anode_material'] = self.anode_material_edit.text().strip()
            if self.anode_mass_spinbox.value() > 0:
                cell_data['anode_mass_mg'] = self.anode_mass_spinbox.value()
            
            # Create cell via backend
            result = self.api.create_cell(**cell_data)
            
            if result['success']:
                self.cell_data = result['cell_data']
                QMessageBox.information(
                    self, "Success", 
                    f"Cell '{cell_data['cell_name']}' created successfully!"
                )
                self.accept()
            else:
                QMessageBox.warning(
                    self, "Creation Failed", 
                    f"Failed to create cell: {result.get('error', 'Unknown error')}"
                )
                
        except Exception as e:
            QMessageBox.critical(
                self, "Error", 
                f"Unexpected error creating cell: {str(e)}"
            )
    
    def get_cell_data(self) -> Optional[Dict[str, Any]]:
        """Get the created cell data."""
        return self.cell_data