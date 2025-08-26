#!/usr/bin/env python3
"""
Advanced Research Tab API Testing

Reusable test script for validating the Advanced Research Tab backend API methods.
Tests all three new API methods with real data.

Usage:
    python tests/test_advanced_research_api.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src_clean"))

from src_clean.backend import get_backend_api
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_get_available_research_cells():
    """Test get_available_research_cells API method."""
    print("\n" + "="*60)
    print("🧪 Testing get_available_research_cells()")
    print("="*60)
    
    api = get_backend_api()
    
    try:
        cells = api.get_available_research_cells()
        
        print(f"✅ Method executed successfully")
        print(f"📊 Found {len(cells)} research cells:")
        for i, cell in enumerate(cells, 1):
            print(f"  {i}. {cell}")
        
        if len(cells) == 0:
            print("⚠️  No cells found - may need to create test data")
        
        return cells
        
    except Exception as e:
        print(f"❌ Error testing get_available_research_cells: {e}")
        return []

def test_get_research_data_summary(test_cells):
    """Test get_research_data_summary API method."""
    print("\n" + "="*60)
    print("🧪 Testing get_research_data_summary()")
    print("="*60)
    
    api = get_backend_api()
    
    # Test 1: All cells
    try:
        print("\n📈 Test 1: Summary for all cells")
        summary_all = api.get_research_data_summary()
        
        print(f"✅ All cells summary:")
        for key, value in summary_all.items():
            print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"❌ Error testing all cells summary: {e}")
        summary_all = {}
    
    # Test 2: Specific cells (if available)
    if test_cells:
        try:
            print(f"\n📈 Test 2: Summary for specific cells: {test_cells[:2]}")
            summary_specific = api.get_research_data_summary(test_cells[:2])
            
            print(f"✅ Specific cells summary:")
            for key, value in summary_specific.items():
                print(f"  {key}: {value}")
            
        except Exception as e:
            print(f"❌ Error testing specific cells summary: {e}")
            summary_specific = {}
    
    return summary_all

def test_get_research_dataset_for_perspective(test_cells):
    """Test get_research_dataset_for_perspective API method."""
    print("\n" + "="*60)
    print("🧪 Testing get_research_dataset_for_perspective()")
    print("="*60)
    
    api = get_backend_api()
    
    # Test 1: All cells dataset
    try:
        print("\n📊 Test 1: Dataset for all cells")
        df_all = api.get_research_dataset_for_perspective()
        
        print(f"✅ All cells dataset:")
        print(f"  Shape: {df_all.shape}")
        print(f"  Columns: {df_all.columns}")
        
        if len(df_all) > 0:
            print(f"  Sample data types:")
            for col in df_all.columns[:5]:  # Show first 5 columns
                dtype = df_all[col].dtype
                print(f"    {col}: {dtype}")
        else:
            print("⚠️  Empty dataset returned")
        
    except Exception as e:
        print(f"❌ Error testing all cells dataset: {e}")
        df_all = None
    
    # Test 2: Specific cells dataset (if available)
    if test_cells:
        try:
            print(f"\n📊 Test 2: Dataset for specific cells: {test_cells[:1]}")
            df_specific = api.get_research_dataset_for_perspective(test_cells[:1])
            
            print(f"✅ Specific cells dataset:")
            print(f"  Shape: {df_specific.shape}")
            
            if len(df_specific) > 0:
                print(f"  Computed columns present:")
                computed_cols = ['duration_hours', 'avg_power_w', 'energy_density_wh_per_ah', 'coulombic_efficiency_pct']
                for col in computed_cols:
                    if col in df_specific.columns:
                        print(f"    ✅ {col}")
                    else:
                        print(f"    ❌ {col} missing")
            
        except Exception as e:
            print(f"❌ Error testing specific cells dataset: {e}")
            df_specific = None
    
    return df_all

def test_perspective_integration(df):
    """Test Arrow conversion for Perspective integration."""
    print("\n" + "="*60)
    print("🧪 Testing Perspective Integration (Polars → Arrow)")
    print("="*60)
    
    if df is None or len(df) == 0:
        print("⚠️  No dataset available for Perspective testing")
        return False
    
    try:
        # Test Arrow conversion
        arrow_table = df.to_arrow()
        
        print(f"✅ Polars → Arrow conversion successful:")
        print(f"  Arrow table shape: {arrow_table.shape}")
        print(f"  Arrow schema: {arrow_table.schema}")
        
        # Test basic Arrow operations
        print(f"  First row preview: {arrow_table.take([0]).to_pandas().to_dict('records')[0] if len(arrow_table) > 0 else 'Empty'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing Arrow conversion: {e}")
        return False

def run_all_tests():
    """Run complete Advanced Research API test suite."""
    print("🚀 Advanced Research Tab API Test Suite")
    print("="*60)
    
    # Test 1: Available cells
    test_cells = test_get_available_research_cells()
    
    # Test 2: Data summary
    summary = test_get_research_data_summary(test_cells)
    
    # Test 3: Research dataset
    dataset = test_get_research_dataset_for_perspective(test_cells)
    
    # Test 4: Perspective integration
    perspective_ready = test_perspective_integration(dataset)
    
    # Final summary
    print("\n" + "="*60)
    print("📋 TEST SUMMARY")
    print("="*60)
    print(f"✅ Available cells: {len(test_cells)} found")
    print(f"✅ Data summary: {'Success' if summary else 'Failed'}")
    print(f"✅ Research dataset: {'Success' if dataset is not None else 'Failed'}")
    print(f"✅ Perspective ready: {'Success' if perspective_ready else 'Failed'}")
    
    if test_cells and dataset is not None and len(dataset) > 0 and perspective_ready:
        print("\n🎉 All API tests passed! Advanced Research Tab backend ready.")
    else:
        print("\n⚠️  Some tests failed or returned empty data. Check data availability.")

if __name__ == "__main__":
    run_all_tests()