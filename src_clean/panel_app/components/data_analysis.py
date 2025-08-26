"""
Data Analysis Tab - Main Entry Point

Simple wrapper that integrates Tab 3 with the main Panel application.
Provides clean interface consistent with other tabs.

Phase 1: Basic integration with static layout
Phases 2-4: Progressive enhancement with full functionality
"""

from .data_analysis_tab import DataAnalysisTab


class DataAnalysisTabWrapper:
    """
    Wrapper class for integration with main Panel app.
    Provides clean interface consistent with other tabs.
    
    This follows the same pattern as other tabs (CellFileManagement, etc.)
    """
    
    def __init__(self, api):
        """Initialize with backend API."""
        self.api = api
        
        # Create the main Tab 3 component
        self.tab = DataAnalysisTab(api)
    
    @property
    def panel(self):
        """Return the main panel for integration with tab system."""
        return self.tab.panel
    
    def cleanup(self):
        """Cleanup method for tab switching."""
        self.tab.cleanup()
    
    def get_current_state(self):
        """Get current state (for debugging/monitoring)."""
        return self.tab.get_current_state()
    
    def refresh_data(self):
        """Refresh data when tab becomes active.""" 
        # Phase 2: Add refresh logic when switching to Tab 3
        pass