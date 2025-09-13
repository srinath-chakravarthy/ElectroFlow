#!/usr/bin/env python3
"""
Segment Inspector Implementation Validation Test

Tests the implementation structure and method signatures without requiring actual data.
Validates that all components are properly integrated and methods are callable.
"""

import sys
from pathlib import Path
import inspect
import polars as pl
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src_clean"))

def test_database_method_exists():
    """Test that database method exists with correct signature."""
    print("🔍 Testing Database Method Implementation")
    print("-" * 50)
    
    try:
        from src_clean.core.database import DatabaseManager
        from src_clean.core.config import get_config
        
        config = get_config()
        db_manager = DatabaseManager(config.db_path)
        
        # Check method exists
        if not hasattr(db_manager, 'get_segment_file_info'):
            print("❌ Method get_segment_file_info does not exist")
            return False
        
        # Check method signature
        method = getattr(db_manager, 'get_segment_file_info')
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        
        if 'segment_id' not in params:
            print("❌ Method signature missing segment_id parameter")
            return False
        
        print("✅ Database method exists with correct signature")
        print(f"   - Method: get_segment_file_info{sig}")
        
        # Test with non-existent ID (should return None gracefully)
        result = db_manager.get_segment_file_info(99999)
        if result is not None:
            print("⚠️  Non-existent segment should return None")
        else:
            print("✅ Correctly handles non-existent segment")
        
        return True
        
    except Exception as e:
        print(f"❌ Database method test failed: {e}")
        return False

def test_lazy_service_method_exists():
    """Test that LazyDataService method exists with correct signature."""
    print("\n⚡ Testing LazyDataService Method Implementation")
    print("-" * 50)
    
    try:
        from src_clean.backend.lazy_data_service import LazyDataService
        
        lazy_service = LazyDataService()
        
        # Check method exists
        if not hasattr(lazy_service, 'get_segment_raw_data'):
            print("❌ Method get_segment_raw_data does not exist")
            return False
        
        # Check method signature
        method = getattr(lazy_service, 'get_segment_raw_data')
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        
        if 'segment_id' not in params:
            print("❌ Method signature missing segment_id parameter")
            return False
        
        # Check return type annotation
        if sig.return_annotation != pl.DataFrame:
            print("⚠️  Return type should be pl.DataFrame")
        
        print("✅ LazyDataService method exists with correct signature")
        print(f"   - Method: get_segment_raw_data{sig}")
        
        # Test with non-existent ID (should return empty DataFrame gracefully)
        result = lazy_service.get_segment_raw_data(99999)
        if not isinstance(result, pl.DataFrame):
            print("❌ Method should return pl.DataFrame")
            return False
        
        print("✅ Method returns correct type (pl.DataFrame)")
        
        return True
        
    except Exception as e:
        print(f"❌ LazyDataService method test failed: {e}")
        return False

def test_api_method_exists():
    """Test that API method exists with correct signature."""
    print("\n🏹 Testing API Method Implementation")
    print("-" * 50)
    
    try:
        from src_clean.backend import get_backend_api
        
        api = get_backend_api()
        
        # Check method exists
        if not hasattr(api, 'get_segment_raw_data_for_perspective'):
            print("❌ Method get_segment_raw_data_for_perspective does not exist")
            return False
        
        # Check method signature
        method = getattr(api, 'get_segment_raw_data_for_perspective')
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        
        required_params = ['segment_id', 'analysis_context']
        missing_params = [p for p in required_params if p not in params]
        if missing_params:
            print(f"❌ Method signature missing parameters: {missing_params}")
            return False
        
        # Check return type annotation
        if sig.return_annotation != bytes:
            print("⚠️  Return type should be bytes (Arrow format)")
        
        print("✅ API method exists with correct signature")
        print(f"   - Method: get_segment_raw_data_for_perspective{sig}")
        
        # Test with non-existent ID (should return bytes gracefully)
        result = api.get_segment_raw_data_for_perspective(99999, {})
        if not isinstance(result, bytes):
            print("❌ Method should return bytes")
            return False
        
        print("✅ Method returns correct type (bytes)")
        
        return True
        
    except Exception as e:
        print(f"❌ API method test failed: {e}")
        return False

def test_data_cleaning_methods():
    """Test data cleaning helper methods exist."""
    print("\n✨ Testing Data Cleaning Methods")
    print("-" * 50)
    
    try:
        from src_clean.backend import get_backend_api
        
        api = get_backend_api()
        
        # Check helper methods exist
        helper_methods = [
            '_add_segment_metadata',
            '_clean_data_for_perspective',
            '_create_empty_arrow_table'
        ]
        
        missing_methods = []
        for method_name in helper_methods:
            if not hasattr(api, method_name):
                missing_methods.append(method_name)
        
        if missing_methods:
            print(f"❌ Missing helper methods: {missing_methods}")
            return False
        
        print("✅ All data cleaning helper methods exist")
        
        # Test empty arrow table creation
        empty_arrow = api._create_empty_arrow_table()
        if not isinstance(empty_arrow, bytes):
            print("❌ Empty arrow table should return bytes")
            return False
        
        print("✅ Empty arrow table creation works")
        
        return True
        
    except Exception as e:
        print(f"❌ Data cleaning methods test failed: {e}")
        return False

def test_ui_integration_methods():
    """Test that UI integration methods exist."""
    print("\n🖱️ Testing UI Integration Methods")
    print("-" * 50)
    
    try:
        from src_clean.panel_app.components.electrochemical_explorer_tab import CleanElectrochemicalExplorer
        from src_clean.backend import get_backend_api
        
        api = get_backend_api()
        explorer = CleanElectrochemicalExplorer(api)
        
        # Check UI methods exist
        ui_methods = [
            '_add_click_handling',
            '_handle_plot_click',
            '_find_closest_segment',
            '_open_segment_inspector_modal',
            '_extract_current_context'
        ]
        
        missing_methods = []
        for method_name in ui_methods:
            if not hasattr(explorer, method_name):
                missing_methods.append(method_name)
        
        if missing_methods:
            print(f"❌ Missing UI methods: {missing_methods}")
            return False
        
        print("✅ All UI integration methods exist")
        
        # Test context extraction
        context = explorer._extract_current_context()
        if not isinstance(context, dict):
            print("❌ Context extraction should return dict")
            return False
        
        expected_keys = ['selected_cells', 'include_fits', 'plot_type']
        missing_keys = [k for k in expected_keys if k not in context]
        if missing_keys:
            print(f"⚠️  Context missing expected keys: {missing_keys}")
        
        print("✅ Context extraction works")
        
        return True
        
    except Exception as e:
        print(f"❌ UI integration methods test failed: {e}")
        return False

def test_arrow_compatibility():
    """Test Arrow format compatibility."""
    print("\n🏹 Testing Arrow Format Compatibility")
    print("-" * 50)
    
    try:
        import pyarrow as pa
        
        # Test creating Arrow table from sample data
        sample_df = pl.DataFrame({
            'time_s': [0.0, 1.0, 2.0],
            'potential_v': [3.0, 3.1, 3.2],
            'current_a': [0.001, 0.002, 0.003],
            'segment_id': [1, 1, 1],
            'cell_name': ['TEST_CELL', 'TEST_CELL', 'TEST_CELL']
        })
        
        # Convert to Arrow bytes
        arrow_table = sample_df.to_arrow()
        
        # Serialize to bytes
        sink = pa.BufferOutputStream()
        writer = pa.ipc.new_stream(sink, arrow_table.schema)
        writer.write_table(arrow_table)
        writer.close()
        arrow_bytes = sink.getvalue().to_pybytes()
        
        print("✅ Arrow serialization works")
        print(f"   - Sample data shape: {sample_df.shape}")
        print(f"   - Arrow bytes size: {len(arrow_bytes)}")
        
        # Test deserialization
        reader = pa.ipc.open_stream(arrow_bytes)
        recovered_table = reader.read_all()
        recovered_df = recovered_table.to_pandas()
        
        print("✅ Arrow deserialization works")
        print(f"   - Recovered shape: {recovered_df.shape}")
        
        return True
        
    except Exception as e:
        print(f"❌ Arrow compatibility test failed: {e}")
        return False

if __name__ == "__main__":
    print("="*70)
    print("🧪 SEGMENT INSPECTOR IMPLEMENTATION VALIDATION")
    print("="*70)
    
    tests = [
        ("Database Method", test_database_method_exists),
        ("LazyDataService Method", test_lazy_service_method_exists),
        ("API Method", test_api_method_exists),
        ("Data Cleaning Methods", test_data_cleaning_methods),
        ("UI Integration Methods", test_ui_integration_methods),
        ("Arrow Compatibility", test_arrow_compatibility)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    print("\n" + "="*70)
    print("📋 IMPLEMENTATION VALIDATION SUMMARY")
    print("="*70)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL IMPLEMENTATION TESTS PASSED!")
        print("✅ Segment Inspector implementation is structurally complete")
        print("✅ Ready for integration testing with real data")
        sys.exit(0)
    else:
        print(f"\n❌ {total - passed} TESTS FAILED")
        print("❌ Implementation needs fixes before deployment")
        sys.exit(1)