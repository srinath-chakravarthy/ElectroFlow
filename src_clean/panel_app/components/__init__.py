"""
Panel Application Components

Modular components for the electrochemical analysis interface:
- CellFileManagement: Unified cell & file management with modals (Tab 1)
- DataViewer: Data visualization and analysis
- StatusBar: Status messages and system information
- GroupManagementTab: Group management and organization
- DataAnalysisTabWrapper: Advanced data analysis and visualization (Tab 3)
- AdvancedResearchTabWrapper: Advanced research analytics with Perspective (Tab 4)
"""

from .cell_file_management import CellFileManagement
from .data_viewer import DataViewer
from .status_bar import StatusBar
from .group_management_tab import GroupManagementTab
from .data_analysis import DataAnalysisTabWrapper
from .advanced_research_tab import AdvancedResearchTabWrapper

__all__ = ['CellFileManagement', 'DataViewer', 'StatusBar', 'GroupManagementTab', 'DataAnalysisTabWrapper', 'AdvancedResearchTabWrapper']