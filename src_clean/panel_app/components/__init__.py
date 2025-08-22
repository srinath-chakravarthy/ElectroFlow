"""
Panel Application Components

Modular components for the electrochemical analysis interface:
- CellManager: Cell creation, selection, and management
- FileUploader: File upload, processing, and selection  
- DataViewer: Data visualization and analysis
- StatusBar: Status messages and system information
"""

from .cell_manager import CellManager
from .file_uploader import FileUploader  
from .data_viewer import DataViewer
from .status_bar import StatusBar
from .group_management_tab import GroupManagementTab

__all__ = ['CellManager', 'FileUploader', 'DataViewer', 'StatusBar', 'GroupManagementTab']