#!/usr/bin/env python3
"""
Advanced Research Tab Component Testing

Reusable test script for validating the Advanced Research Tab UI component.
Tests component initialization, layout, and basic interactions.

Usage:
    python tests/test_advanced_research_component.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src_clean"))

from src_clean.backend import get_backend_api
from src_clean.panel_app.components.advanced_research_tab import AdvancedResearchTab, AdvancedResearchTabWrapper
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_component_initialization():
    """Test AdvancedResearchTab component initialization."""
    print("\n" + "="*60)
    print("🧪 Testing AdvancedResearchTab Initialization")
    print("="*60)
    
    try:
        # Initialize backend API
        api = get_backend_api()
        print("✅ Backend API initialized")
        
        # Create component
        tab = AdvancedResearchTab(api=api)
        print("✅ AdvancedResearchTab component created")
        
        # Check basic attributes
        assert hasattr(tab, 'selected_cells'), "Missing selected_cells attribute"
        assert hasattr(tab, 'dataset_loaded'), "Missing dataset_loaded attribute"
        assert hasattr(tab, 'perspective_ready'), "Missing perspective_ready attribute"
        print("✅ Component attributes present")
        
        # Check UI components
        assert hasattr(tab, 'cell_tabulator'), "Missing cell_tabulator component"
        assert hasattr(tab, 'load_dataset_btn'), "Missing load_dataset_btn component"
        assert hasattr(tab, 'perspective_viewer'), "Missing perspective_viewer component"
        print("✅ UI components created")
        
        # Check layout
        panel = tab.panel
        assert panel is not None, "Panel property returns None"
        print("✅ Panel layout accessible")
        
        return tab
        
    except Exception as e:
        print(f"❌ Component initialization failed: {e}")
        return None

def test_wrapper_class():
    """Test AdvancedResearchTabWrapper integration class."""
    print("\n" + "="*60)
    print("🧪 Testing AdvancedResearchTabWrapper")
    print("="*60)
    
    try:
        # Initialize backend API
        api = get_backend_api()
        print("✅ Backend API initialized")
        
        # Create wrapper
        wrapper = AdvancedResearchTabWrapper(api=api)
        print("✅ AdvancedResearchTabWrapper created")
        
        # Check wrapper methods
        assert hasattr(wrapper, 'panel'), "Missing panel property"
        assert hasattr(wrapper, 'cleanup'), "Missing cleanup method"
        assert hasattr(wrapper, 'get_current_state'), "Missing get_current_state method"
        print("✅ Wrapper methods present")
        
        # Test panel property
        panel = wrapper.panel
        assert panel is not None, "Wrapper panel property returns None"
        print("✅ Wrapper panel accessible")
        
        # Test state method
        state = wrapper.get_current_state()
        assert isinstance(state, dict), "get_current_state should return dict"
        expected_keys = ['selected_cells', 'dataset_loaded', 'perspective_ready', 'status']
        for key in expected_keys:
            assert key in state, f"Missing key in state: {key}"
        print("✅ Current state method working")
        print(f"   Initial state: {state}")
        
        return wrapper
        
    except Exception as e:
        print(f"❌ Wrapper class testing failed: {e}")
        return None

def test_component_structure():
    """Test component internal structure and UI elements."""
    print("\n" + "="*60)
    print("🧪 Testing Component Structure")
    print("="*60)
    
    try:
        # Initialize component
        api = get_backend_api()
        tab = AdvancedResearchTab(api=api)
        print("✅ Component initialized for structure testing")
        
        # Test Data Selection Panel components
        print("\n📊 Data Selection Panel:")
        assert hasattr(tab, 'cell_tabulator'), "Missing cell_tabulator"
        assert hasattr(tab, 'temperature_filter'), "Missing temperature_filter"
        assert hasattr(tab, 'data_info_display'), "Missing data_info_display"
        print("   ✅ All data selection components present")
        
        # Test Quick Actions Panel components
        print("\n⚡ Quick Actions Panel:")
        assert hasattr(tab, 'load_dataset_btn'), "Missing load_dataset_btn"
        assert hasattr(tab, 'refresh_cells_btn'), "Missing refresh_cells_btn"
        assert hasattr(tab, 'dataset_info_btn'), "Missing dataset_info_btn"
        assert hasattr(tab, 'status_indicator'), "Missing status_indicator"
        print("   ✅ All quick action components present")
        
        # Test Perspective Workspace components
        print("\n🔬 Perspective Workspace:")
        assert hasattr(tab, 'perspective_viewer'), "Missing perspective_viewer"
        assert hasattr(tab, 'perspective_status'), "Missing perspective_status"
        print("   ✅ All perspective components present")
        
        # Test component configuration
        print("\n⚙️ Component Configuration:")
        
        # Check cell tabulator configuration
        assert tab.cell_tabulator.height == 300, "Cell tabulator height not set correctly"
        assert tab.cell_tabulator.selectable == 'checkbox', "Cell tabulator should allow checkbox selection"
        print("   ✅ Cell tabulator configured correctly")
        
        # Check button states
        assert tab.load_dataset_btn.disabled == True, "Load dataset button should start disabled"
        assert tab.dataset_info_btn.disabled == True, "Dataset info button should start disabled"
        print("   ✅ Button states correctly initialized")
        
        # Check perspective viewer
        assert tab.perspective_viewer.min_height == 600, "Perspective viewer min_height not set correctly"
        print("   ✅ Perspective viewer configured correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Component structure testing failed: {e}")
        return False

def test_status_updates():
    """Test status update functionality."""
    print("\n" + "="*60)
    print("🧪 Testing Status Update System")
    print("="*60)
    
    try:
        # Initialize component
        api = get_backend_api()
        tab = AdvancedResearchTab(api=api)
        print("✅ Component initialized for status testing")
        
        # Test different status types
        status_types = [
            ("Test info status", "info"),
            ("Test success status", "success"),
            ("Test warning status", "warning"),
            ("Test error status", "error"),
            ("Test loading status", "loading")
        ]
        
        for message, status_type in status_types:
            tab._update_status(message, status_type)
            assert tab.status_message == message, f"Status message not updated for {status_type}"
            print(f"   ✅ {status_type.capitalize()} status working")
        
        # Test data info update
        tab._update_data_info("Test data info message")
        print("   ✅ Data info update working")
        
        return True
        
    except Exception as e:
        print(f"❌ Status update testing failed: {e}")
        return False

def test_callback_setup():
    """Test that callbacks are properly setup."""
    print("\n" + "="*60)
    print("🧪 Testing Callback Setup")
    print("="*60)
    
    try:
        # Initialize component
        api = get_backend_api()
        tab = AdvancedResearchTab(api=api)
        print("✅ Component initialized for callback testing")
        
        # Check that callback methods exist
        callback_methods = [
            '_on_load_dataset',
            '_on_refresh_cells', 
            '_on_show_dataset_info',
            '_on_cell_selection_changed',
            '_on_temperature_filter_changed'
        ]
        
        for method_name in callback_methods:
            assert hasattr(tab, method_name), f"Missing callback method: {method_name}"
            method = getattr(tab, method_name)
            assert callable(method), f"Method {method_name} is not callable"
            print(f"   ✅ {method_name} callback present and callable")
        
        return True
        
    except Exception as e:
        print(f"❌ Callback setup testing failed: {e}")
        return False

def run_all_tests():
    """Run complete Advanced Research Component test suite."""
    print("🚀 Advanced Research Tab Component Test Suite")
    print("="*60)
    
    # Test 1: Component initialization
    component = test_component_initialization()
    
    # Test 2: Wrapper class
    wrapper = test_wrapper_class()
    
    # Test 3: Component structure
    structure_ok = test_component_structure()
    
    # Test 4: Status updates
    status_ok = test_status_updates()
    
    # Test 5: Callback setup
    callbacks_ok = test_callback_setup()
    
    # Final summary
    print("\n" + "="*60)
    print("📋 TEST SUMMARY")
    print("="*60)
    print(f"✅ Component initialization: {'Success' if component else 'Failed'}")
    print(f"✅ Wrapper class: {'Success' if wrapper else 'Failed'}")
    print(f"✅ Component structure: {'Success' if structure_ok else 'Failed'}")
    print(f"✅ Status updates: {'Success' if status_ok else 'Failed'}")
    print(f"✅ Callback setup: {'Success' if callbacks_ok else 'Failed'}")
    
    if all([component, wrapper, structure_ok, status_ok, callbacks_ok]):
        print("\n🎉 All component tests passed! Advanced Research Tab UI ready.")
    else:
        print("\n⚠️  Some component tests failed. Check individual test results.")

if __name__ == "__main__":
    run_all_tests()