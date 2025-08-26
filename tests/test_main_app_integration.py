#!/usr/bin/env python3
"""
Main App Integration Testing

Validates that Tab 4 (Advanced Research) integrates correctly with the main application.
Tests app initialization, tab creation, and basic functionality.

Usage:
    python tests/test_main_app_integration.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src_clean"))

from src_clean.panel_app.main_app import ElectrochemicalApp
from src_clean.backend import get_backend_api
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_app_initialization():
    """Test main app initialization with Tab 4."""
    print("\n" + "="*60)
    print("🧪 Testing Main App Initialization with Tab 4")
    print("="*60)
    
    try:
        # Initialize app
        app = ElectrochemicalApp()
        print("✅ ElectrochemicalApp initialized successfully")
        
        # Check that all tabs exist
        tabs = app.layout[1]  # tabs is the second element (after header)
        tab_count = len(tabs.objects)
        expected_tabs = 4
        
        assert tab_count == expected_tabs, f"Expected {expected_tabs} tabs, got {tab_count}"
        print(f"✅ Found {tab_count} tabs as expected")
        
        # Check tab names
        tab_names = [tab[0] for tab in tabs.objects]
        expected_names = [
            "🔋 Cell & File Management",
            "🔗 Group Management", 
            "📊 Data Analysis",
            "🔬 Advanced Research"
        ]
        
        for i, (actual, expected) in enumerate(zip(tab_names, expected_names)):
            assert actual == expected, f"Tab {i}: expected '{expected}', got '{actual}'"
        print("✅ All tab names correct")
        
        # Check that advanced research tab exists
        assert hasattr(app, 'advanced_research_tab'), "Missing advanced_research_tab attribute"
        print("✅ Advanced research tab component present")
        
        # Check tab content accessibility
        tab4_content = tabs.objects[3][1]  # 4th tab content
        assert tab4_content is not None, "Tab 4 content is None"
        print("✅ Tab 4 content accessible")
        
        return app
        
    except Exception as e:
        print(f"❌ App initialization failed: {e}")
        return None

def test_advanced_research_tab_functionality():
    """Test advanced research tab basic functionality."""
    print("\n" + "="*60)
    print("🧪 Testing Advanced Research Tab Functionality")
    print("="*60)
    
    try:
        # Initialize app
        app = ElectrochemicalApp()
        print("✅ App initialized for tab testing")
        
        # Get advanced research tab
        research_tab = app.advanced_research_tab
        
        # Check wrapper methods
        assert hasattr(research_tab, 'panel'), "Missing panel property"
        assert hasattr(research_tab, 'cleanup'), "Missing cleanup method"
        assert hasattr(research_tab, 'get_current_state'), "Missing get_current_state method"
        print("✅ Advanced research tab wrapper methods present")
        
        # Test current state method
        state = research_tab.get_current_state()
        assert isinstance(state, dict), "get_current_state should return dict"
        expected_keys = ['selected_cells', 'dataset_loaded', 'perspective_ready', 'status']
        for key in expected_keys:
            assert key in state, f"Missing key in state: {key}"
        print("✅ Current state method working")
        print(f"   Initial state: {state}")
        
        # Check component integration
        actual_tab = research_tab.tab
        assert hasattr(actual_tab, 'cell_tabulator'), "Missing cell_tabulator"
        assert hasattr(actual_tab, 'perspective_viewer'), "Missing perspective_viewer"
        assert hasattr(actual_tab, 'load_dataset_btn'), "Missing load_dataset_btn"
        print("✅ Component integration working")
        
        return True
        
    except Exception as e:
        print(f"❌ Advanced research tab functionality failed: {e}")
        return False

def test_tab_switching():
    """Test basic tab switching functionality."""
    print("\n" + "="*60)
    print("🧪 Testing Tab Switching")
    print("="*60)
    
    try:
        # Initialize app
        app = ElectrochemicalApp()
        print("✅ App initialized for tab switching test")
        
        # Get tabs component
        tabs = app.layout[1]
        
        # Test switching to each tab
        for i in range(len(tabs.objects)):
            tabs.active = i
            assert tabs.active == i, f"Failed to switch to tab {i}"
            print(f"✅ Successfully switched to tab {i}: {tabs.objects[i][0]}")
        
        # Test switching specifically to Advanced Research tab
        tabs.active = 3  # Tab 4 (0-indexed)
        assert tabs.active == 3, "Failed to switch to Advanced Research tab"
        print("✅ Advanced Research tab switching working")
        
        return True
        
    except Exception as e:
        print(f"❌ Tab switching failed: {e}")
        return False

def test_backend_integration():
    """Test backend API integration with Tab 4."""
    print("\n" + "="*60)
    print("🧪 Testing Backend Integration with Tab 4")
    print("="*60)
    
    try:
        # Initialize app
        app = ElectrochemicalApp()
        print("✅ App initialized for backend testing")
        
        # Check that advanced research tab has API access
        research_tab = app.advanced_research_tab.tab
        assert hasattr(research_tab, 'api'), "Advanced research tab missing API"
        print("✅ Advanced research tab has API access")
        
        # Test API methods are available
        api = research_tab.api
        required_methods = [
            'get_available_research_cells',
            'get_research_dataset_for_perspective', 
            'get_research_data_summary'
        ]
        
        for method_name in required_methods:
            assert hasattr(api, method_name), f"Missing API method: {method_name}"
            method = getattr(api, method_name)
            assert callable(method), f"Method {method_name} is not callable"
            print(f"✅ API method {method_name} available")
        
        print("✅ Backend integration working")
        return True
        
    except Exception as e:
        print(f"❌ Backend integration failed: {e}")
        return False

def run_all_integration_tests():
    """Run complete main app integration test suite."""
    print("🚀 Main App Integration Test Suite - Tab 4")
    print("="*60)
    
    # Test 1: App initialization
    app = test_app_initialization()
    
    # Test 2: Advanced research tab functionality
    tab_functionality_ok = test_advanced_research_tab_functionality()
    
    # Test 3: Tab switching
    tab_switching_ok = test_tab_switching()
    
    # Test 4: Backend integration
    backend_integration_ok = test_backend_integration()
    
    # Final summary
    print("\n" + "="*60)
    print("📋 INTEGRATION TEST SUMMARY")
    print("="*60)
    print(f"✅ App initialization: {'Success' if app else 'Failed'}")
    print(f"✅ Tab functionality: {'Success' if tab_functionality_ok else 'Failed'}")
    print(f"✅ Tab switching: {'Success' if tab_switching_ok else 'Failed'}")
    print(f"✅ Backend integration: {'Success' if backend_integration_ok else 'Failed'}")
    
    if all([app, tab_functionality_ok, tab_switching_ok, backend_integration_ok]):
        print("\n🎉 All integration tests passed! Tab 4 successfully integrated.")
    else:
        print("\n⚠️  Some integration tests failed. Check individual test results.")

if __name__ == "__main__":
    run_all_integration_tests()