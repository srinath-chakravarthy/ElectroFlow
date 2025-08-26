#!/usr/bin/env python3
"""
Comprehensive Analytics Pipeline Test

Tests the new comprehensive analytics pipeline that:
1. Gets clean segment data (no JSON fields)  
2. Runs all registry analytics with include_segment_data=False
3. Joins all results into one comprehensive DataFrame
4. Tests Perspective compatibility

Usage:
    python tests/test_comprehensive_analytics_pipeline.py
"""

import sys
from pathlib import Path
import pandas as pd
import polars as pl
import panel as pn

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src_clean"))

from src_clean.backend import get_backend_api
import logging

# Configure Panel extensions
pn.extension('perspective')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_clean_segment_data():
    """Test clean segment data extraction (no JSON fields)."""
    print("\n" + "="*70)
    print("🧹 TESTING CLEAN SEGMENT DATA EXTRACTION")
    print("="*70)
    
    try:
        api = get_backend_api()
        available_cells = api.get_available_research_cells()
        
        if not available_cells:
            print("❌ No cells available")
            return None
        
        print(f"✅ Available cells: {available_cells}")
        
        # Test clean segment data method
        clean_df = api.get_clean_segment_data_for_perspective(cells=available_cells[:1])
        
        if clean_df.is_empty():
            print("❌ No clean data returned")
            return None
        
        print(f"✅ Clean data shape: {clean_df.shape}")
        print(f"✅ Clean data columns: {len(clean_df.columns)}")
        
        # Check that problematic JSON fields are removed
        problematic_fields = ['segment_metadata', 'analysis_results', 'groups']
        has_problematic = any(field in clean_df.columns for field in problematic_fields)
        
        if has_problematic:
            found_fields = [f for f in problematic_fields if f in clean_df.columns]
            print(f"⚠️  Still contains JSON fields: {found_fields}")
        else:
            print(f"✅ All JSON fields successfully removed")
        
        # Convert to pandas and check data types
        pandas_df = clean_df.to_pandas()
        print(f"\n📋 Sample data types:")
        for col, dtype in pandas_df.dtypes.items():
            if pandas_df[col].dtype == 'object':
                sample_val = pandas_df[col].iloc[0] if len(pandas_df) > 0 else None
                print(f"   {col}: {dtype} (sample: {type(sample_val).__name__})")
                if isinstance(sample_val, (dict, list)):
                    print(f"      ⚠️  Complex object detected!")
            elif pandas_df.dtypes.name in ['int64', 'float64', 'bool']:
                print(f"   {col}: {dtype} ✅")
        
        return clean_df
        
    except Exception as e:
        print(f"❌ Clean segment data test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_analytics_pipeline():
    """Test the comprehensive analytics pipeline."""
    print("\n" + "="*70)
    print("⚙️  TESTING COMPREHENSIVE ANALYTICS PIPELINE")
    print("="*70)
    
    try:
        api = get_backend_api()
        available_cells = api.get_available_research_cells()
        
        if not available_cells:
            print("❌ No cells available")
            return None
        
        print(f"✅ Available cells: {available_cells}")
        
        # Test comprehensive dataset method
        comprehensive_df = api.get_research_dataset_for_perspective(cells=available_cells[:1])
        
        if comprehensive_df.is_empty():
            print("❌ No comprehensive data returned")
            return None
        
        print(f"✅ Comprehensive data shape: {comprehensive_df.shape}")
        print(f"✅ Total columns: {len(comprehensive_df.columns)}")
        
        # Analyze column composition
        columns = comprehensive_df.columns
        raw_columns = [col for col in columns if not col.startswith('analytics_')]
        analytics_columns = [col for col in columns if col.startswith('analytics_')]
        
        print(f"\n📊 Column Analysis:")
        print(f"   Raw segment columns: {len(raw_columns)}")
        print(f"   Analytics columns: {len(analytics_columns)}")
        
        # Show analytics columns by type
        analytics_by_type = {}
        for col in analytics_columns:
            parts = col.split('_')
            if len(parts) >= 3:
                analysis_type = parts[1] + '_' + parts[2]  # e.g., 'current_decay'
                if analysis_type not in analytics_by_type:
                    analytics_by_type[analysis_type] = []
                analytics_by_type[analysis_type].append(col)
        
        print(f"\n🔬 Analytics Results by Type:")
        for analysis_type, cols in analytics_by_type.items():
            print(f"   {analysis_type}: {len(cols)} columns")
            error_cols = [c for c in cols if 'error' in c]
            if error_cols:
                print(f"      Error columns: {len(error_cols)}")
        
        return comprehensive_df
        
    except Exception as e:
        print(f"❌ Analytics pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_perspective_compatibility():
    """Test Perspective compatibility with comprehensive dataset."""
    print("\n" + "="*70)
    print("🔬 TESTING PERSPECTIVE COMPATIBILITY")
    print("="*70)
    
    try:
        api = get_backend_api()
        available_cells = api.get_available_research_cells()
        
        if not available_cells:
            print("❌ No cells available")
            return False
        
        # Get comprehensive dataset
        comprehensive_df = api.get_research_dataset_for_perspective(cells=available_cells[:1])
        
        if comprehensive_df.is_empty():
            print("❌ No comprehensive data")
            return False
        
        # Convert to pandas for Perspective
        pandas_df = comprehensive_df.to_pandas()
        
        print(f"✅ Data for Perspective: {pandas_df.shape}")
        
        # Check for problematic data types
        problematic_columns = []
        for col, dtype in pandas_df.dtypes.items():
            if dtype == 'object':
                sample_values = pandas_df[col].dropna().head(3).tolist()
                has_complex = any(isinstance(v, (dict, list)) for v in sample_values if v is not None)
                if has_complex:
                    problematic_columns.append(col)
        
        if problematic_columns:
            print(f"⚠️  Problematic columns for Perspective: {problematic_columns}")
            for col in problematic_columns[:3]:  # Show first 3
                sample = pandas_df[col].dropna().iloc[0] if not pandas_df[col].dropna().empty else None
                print(f"   {col}: {type(sample)} - {sample}")
        else:
            print(f"✅ All columns Perspective-compatible")
        
        # Create Perspective viewer
        print(f"\n🔬 Creating Perspective viewer...")
        
        perspective_viewer = pn.pane.Perspective(
            object=pandas_df,
            sizing_mode='stretch_width',
            min_height=400,
            margin=(10, 10)
        )
        
        print(f"✅ Perspective viewer created successfully")
        
        # Create test layout
        layout = pn.Column(
            "## Comprehensive Analytics Pipeline - Perspective Test",
            pn.pane.HTML(f"<p><strong>Dataset:</strong> {pandas_df.shape[0]} rows × {pandas_df.shape[1]} columns</p>"),
            pn.pane.HTML(f"<p><strong>Raw columns:</strong> {len([c for c in pandas_df.columns if not c.startswith('analytics_')])}</p>"),
            pn.pane.HTML(f"<p><strong>Analytics columns:</strong> {len([c for c in pandas_df.columns if c.startswith('analytics_')])}</p>"),
            perspective_viewer,
            sizing_mode='stretch_width'
        )
        
        print(f"\n🚀 Starting Perspective test server on http://localhost:5012")
        print(f"📝 Check that:")
        print(f"   - Data rows are visible in the datagrid")
        print(f"   - Both raw and analytics columns are present")
        print(f"   - No JSON/complex object errors")
        print(f"   - Can filter by analytics_*_error columns")
        print(f"\n🛑 Press Ctrl+C to stop the server")
        
        # Serve the test
        layout.show(port=5012, autoreload=True, title="Comprehensive Analytics Pipeline Test")
        
        return True
        
    except Exception as e:
        print(f"❌ Perspective compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_comprehensive_pipeline_tests():
    """Run all comprehensive analytics pipeline tests."""
    print("🚀 Comprehensive Analytics Pipeline Test Suite")
    print("="*70)
    
    # Test 1: Clean segment data extraction
    clean_data = test_clean_segment_data()
    
    # Test 2: Analytics pipeline
    comprehensive_data = test_analytics_pipeline()
    
    # Test 3: Perspective compatibility
    perspective_ok = test_perspective_compatibility()
    
    # Final summary
    print("\n" + "="*70)
    print("📋 COMPREHENSIVE PIPELINE TEST SUMMARY")
    print("="*70)
    print(f"✅ Clean segment data: {'Success' if clean_data is not None else 'Failed'}")
    print(f"✅ Analytics pipeline: {'Success' if comprehensive_data is not None else 'Failed'}")
    print(f"✅ Perspective compatibility: {'Success' if perspective_ok else 'Failed'}")
    
    if all([clean_data is not None, comprehensive_data is not None, perspective_ok]):
        print(f"\n🎉 All pipeline tests passed! Comprehensive analytics with Perspective ready.")
    else:
        print(f"\n⚠️  Some pipeline tests failed. Check individual test results.")

if __name__ == "__main__":
    run_comprehensive_pipeline_tests()