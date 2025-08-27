#!/usr/bin/env python3
"""
Perspective Datagrid Debug Script

Investigates the issue where Perspective viewer shows columns but no data rows.
Tests the Polars → Pandas → Perspective pipeline step by step.

Usage:
    python tests/debug_perspective_datagrid.py
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

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Configure Panel extensions
pn.extension('perspective')

def test_data_pipeline_step_by_step():
    """Test each step of the data pipeline to identify the issue."""
    print("\n" + "="*70)
    print("🔍 DEBUGGING PERSPECTIVE DATAGRID DISPLAY ISSUE")
    print("="*70)
    
    try:
        # Step 1: Initialize backend and get data
        print("\n📡 STEP 1: Backend Data Retrieval")
        print("-" * 50)
        
        api = get_backend_api()
        print("✅ Backend API initialized")
        
        # Get available cells
        available_cells = api.get_available_research_cells()
        print(f"✅ Available cells: {available_cells}")
        
        if not available_cells:
            print("❌ No cells available - cannot test")
            return
        
        # Step 2: Get Polars dataset
        print("\n📊 STEP 2: Polars Dataset Generation")
        print("-" * 50)
        
        dataset = api.get_research_dataset_for_perspective(cells=available_cells[:1])
        print(f"✅ Polars dataset shape: {dataset.shape}")
        print(f"✅ Polars columns: {dataset.columns}")
        
        # Check if dataset is empty
        if dataset.is_empty():
            print("❌ Polars dataset is empty!")
            return
        
        # Show first few rows of Polars data
        print(f"\n📋 First 3 rows of Polars data:")
        print(dataset.head(3))
        
        # Step 3: Convert to Pandas
        print("\n🐼 STEP 3: Polars → Pandas Conversion")
        print("-" * 50)
        
        pandas_df = dataset.to_pandas()
        print(f"✅ Pandas DataFrame shape: {pandas_df.shape}")
        print(f"✅ Pandas columns: {list(pandas_df.columns)}")
        print(f"✅ Pandas dtypes:\n{pandas_df.dtypes}")
        
        # Check for any issues with Pandas conversion
        print(f"\n📋 First 3 rows of Pandas data:")
        print(pandas_df.head(3))
        
        # Check for NaN or problematic values
        nan_counts = pandas_df.isnull().sum()
        if nan_counts.sum() > 0:
            print(f"\n⚠️  NaN values found:")
            print(nan_counts[nan_counts > 0])
        
        # Step 4: Test Perspective directly
        print("\n🔬 STEP 4: Perspective Integration Test")
        print("-" * 50)
        
        # Create simple test DataFrame
        simple_df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['test1', 'test2', 'test3'],
            'value': [10.5, 20.5, 30.5]
        })
        
        print("Testing with simple DataFrame:")
        print(simple_df)
        
        # Test Perspective with simple data
        perspective_simple = pn.pane.Perspective(
            object=simple_df,
            sizing_mode='stretch_width',
            min_height=300
        )
        print("✅ Simple Perspective viewer created")
        
        # Test Perspective with our research data
        perspective_research = pn.pane.Perspective(
            object=pandas_df,
            sizing_mode='stretch_width', 
            min_height=300
        )
        print("✅ Research Perspective viewer created")
        
        # Step 5: Data type analysis
        print("\n🔎 STEP 5: Data Type Analysis")
        print("-" * 50)
        
        # Check for any problematic data types
        problematic_types = []
        for col, dtype in pandas_df.dtypes.items():
            if dtype == 'object':
                # Check if object columns contain complex data
                sample_values = pandas_df[col].dropna().head(3).tolist()
                print(f"Column '{col}' (object): {sample_values}")
                if any(isinstance(v, (dict, list)) for v in sample_values):
                    problematic_types.append(col)
        
        if problematic_types:
            print(f"⚠️  Columns with complex data: {problematic_types}")
        
        # Step 6: Create test app
        print("\n🖥️  STEP 6: Test Application")
        print("-" * 50)
        
        # Create comparison layout
        layout = pn.Column(
            "## Perspective Datagrid Debug Test",
            
            pn.pane.HTML("<h3>Simple Test Data</h3>"),
            perspective_simple,
            
            pn.pane.HTML("<h3>Research Data</h3>"),
            pn.pane.HTML(f"<p>Shape: {pandas_df.shape[0]} rows × {pandas_df.shape[1]} columns</p>"),
            perspective_research,
            
            sizing_mode='stretch_width'
        )
        
        print("✅ Test layout created")
        print("\n🚀 Starting test server...")
        print("📝 Check both Perspective viewers:")
        print("   1. Simple test data should show 3 rows")
        print("   2. Research data should show your electrochemical data")
        print("\n🛑 Press Ctrl+C to stop the server")
        
        # Serve the test app
        layout.show(port=5008, autoreload=True)
        
    except Exception as e:
        print(f"❌ Debug test failed: {e}")
        import traceback
        traceback.print_exc()

def test_perspective_configuration():
    """Test different Perspective configurations to find working setup."""
    print("\n" + "="*70)
    print("⚙️  TESTING PERSPECTIVE CONFIGURATIONS")
    print("="*70)
    
    try:
        # Get test data
        api = get_backend_api()
        available_cells = api.get_available_research_cells()
        
        if not available_cells:
            print("❌ No cells available")
            return
        
        dataset = api.get_research_dataset_for_perspective(cells=available_cells[:1])
        pandas_df = dataset.to_pandas()
        
        # Test different configurations
        configs = [
            {
                'name': 'Default Configuration',
                'config': {}
            },
            {
                'name': 'Explicit Plugin Configuration', 
                'config': {'plugin': 'datagrid'}
            },
            {
                'name': 'With Columns Configuration',
                'config': {
                    'plugin': 'datagrid',
                    'columns': list(pandas_df.columns[:10])  # First 10 columns
                }
            },
            {
                'name': 'Minimal Data Test',
                'config': {},
                'data': pandas_df[['cell_name', 'technique_name', 'capacity_ah', 'energy_wh']].head(10)
            }
        ]
        
        # Create test viewers
        viewers = []
        for i, config in enumerate(configs):
            test_data = config.get('data', pandas_df)
            
            print(f"\n🧪 Configuration {i+1}: {config['name']}")
            print(f"   Data shape: {test_data.shape}")
            
            viewer = pn.pane.Perspective(
                object=test_data,
                sizing_mode='stretch_width',
                min_height=250,
                **config['config']
            )
            
            viewers.append((config['name'], viewer))
        
        # Create comparison layout
        layout_items = ["## Perspective Configuration Comparison"]
        
        for name, viewer in viewers:
            layout_items.extend([
                pn.pane.HTML(f"<h3>{name}</h3>"),
                viewer,
                pn.Spacer(height=20)
            ])
        
        layout = pn.Column(*layout_items, sizing_mode='stretch_width')
        
        print("\n🚀 Starting configuration test server...")
        layout.show(port=5009, autoreload=True)
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()

def quick_data_inspection():
    """Quick inspection of the data without UI."""
    print("\n" + "="*70)
    print("🔍 QUICK DATA INSPECTION")
    print("="*70)
    
    try:
        api = get_backend_api()
        available_cells = api.get_available_research_cells()
        
        if not available_cells:
            print("❌ No cells available")
            return
        
        print(f"✅ Available cells: {available_cells}")
        
        # Get dataset
        dataset = api.get_research_dataset_for_perspective(cells=available_cells[:1])
        pandas_df = dataset.to_pandas()
        
        print(f"\n📊 Dataset Summary:")
        print(f"   Shape: {pandas_df.shape}")
        print(f"   Columns: {len(pandas_df.columns)}")
        print(f"   Memory usage: {pandas_df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
        
        print(f"\n📋 Column Info:")
        for i, (col, dtype) in enumerate(pandas_df.dtypes.items()):
            non_null = pandas_df[col].count()
            print(f"   {i+1:2d}. {col:<30} | {str(dtype):<15} | {non_null:>6} non-null")
            if i >= 20:  # Limit output
                print(f"   ... and {len(pandas_df.columns)-21} more columns")
                break
        
        print(f"\n🔍 Sample Data (first 2 rows):")
        print(pandas_df.head(2).to_string())
        
        print(f"\n✅ Data inspection complete - data looks good!")
        
    except Exception as e:
        print(f"❌ Data inspection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Debug Perspective datagrid display issue')
    parser.add_argument('--mode', choices=['pipeline', 'config', 'inspect'], 
                       default='inspect', help='Debug mode to run')
    
    args = parser.parse_args()
    
    if args.mode == 'pipeline':
        test_data_pipeline_step_by_step()
    elif args.mode == 'config':
        test_perspective_configuration()
    else:  # inspect
        quick_data_inspection()