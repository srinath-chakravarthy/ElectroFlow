#!/usr/bin/env python3
"""
Perspective Display Fix Test

Tests the hypothesis that complex object columns are preventing Perspective datagrid 
from displaying data properly. Attempts different data cleaning approaches.

Usage:
    python tests/test_perspective_fix.py
"""

import sys
from pathlib import Path
import pandas as pd
import polars as pl
import panel as pn
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src_clean"))

from src_clean.backend import get_backend_api
import logging

# Configure Panel extensions
pn.extension('perspective')

logger = logging.getLogger(__name__)

def clean_dataframe_for_perspective(df):
    """Clean DataFrame to make it compatible with Perspective."""
    cleaned_df = df.copy()
    
    print(f"🧹 Cleaning DataFrame for Perspective compatibility...")
    print(f"   Original shape: {df.shape}")
    
    problematic_columns = []
    
    for col in cleaned_df.columns:
        if cleaned_df[col].dtype == 'object':
            # Check if column contains complex objects
            sample_values = cleaned_df[col].dropna().head(3).tolist()
            
            # Check for dictionaries, lists, or other complex objects
            has_complex = any(
                isinstance(v, (dict, list)) or 
                (isinstance(v, str) and (v.startswith('{') or v.startswith('[')))
                for v in sample_values if v is not None
            )
            
            if has_complex:
                problematic_columns.append(col)
                print(f"   🔧 Converting complex column: {col}")
                
                # Convert complex objects to strings
                cleaned_df[col] = cleaned_df[col].astype(str)
    
    print(f"   Cleaned {len(problematic_columns)} complex columns: {problematic_columns}")
    print(f"   Final shape: {cleaned_df.shape}")
    
    return cleaned_df

def create_minimal_test_dataset(df):
    """Create a minimal dataset with only basic columns."""
    basic_columns = [
        'id', 'segment_index', 'technique_name', 'capacity_ah', 
        'energy_wh', 'duration_s', 'start_potential_v', 'end_potential_v'
    ]
    
    available_columns = [col for col in basic_columns if col in df.columns]
    minimal_df = df[available_columns].copy()
    
    print(f"📊 Created minimal dataset:")
    print(f"   Columns: {available_columns}")
    print(f"   Shape: {minimal_df.shape}")
    
    return minimal_df

def test_perspective_fixes():
    """Test different approaches to fix the Perspective datagrid display."""
    print("\n" + "="*70)
    print("🔧 TESTING PERSPECTIVE DATAGRID FIXES")
    print("="*70)
    
    try:
        # Get original dataset
        api = get_backend_api()
        available_cells = api.get_available_research_cells()
        
        if not available_cells:
            print("❌ No cells available")
            return
        
        dataset = api.get_research_dataset_for_perspective(cells=available_cells[:1])
        original_df = dataset.to_pandas()
        
        print(f"✅ Original dataset loaded: {original_df.shape}")
        
        # Test datasets
        test_datasets = []
        
        # 1. Original dataset (as is)
        test_datasets.append({
            'name': 'Original Dataset',
            'data': original_df.head(20),  # Limit to 20 rows for testing
            'description': 'Unmodified dataset from API'
        })
        
        # 2. Cleaned dataset (convert complex objects to strings)
        cleaned_df = clean_dataframe_for_perspective(original_df)
        test_datasets.append({
            'name': 'Cleaned Dataset',
            'data': cleaned_df.head(20),
            'description': 'Complex objects converted to strings'
        })
        
        # 3. Minimal dataset (basic columns only)
        minimal_df = create_minimal_test_dataset(original_df)
        test_datasets.append({
            'name': 'Minimal Dataset', 
            'data': minimal_df.head(20),
            'description': 'Only basic numeric/string columns'
        })
        
        # 4. Super simple test dataset
        simple_df = pd.DataFrame({
            'segment_id': range(1, 11),
            'technique': ['Rest', 'EIS', 'Charge', 'Discharge'] * 2 + ['Rest', 'EIS'],
            'capacity': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            'voltage': [3.0, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9]
        })
        test_datasets.append({
            'name': 'Simple Test Dataset',
            'data': simple_df,
            'description': 'Hand-crafted simple data'
        })
        
        # Create Perspective viewers for each dataset
        layout_items = ["# Perspective Datagrid Fix Testing"]
        
        for i, test_data in enumerate(test_datasets):
            print(f"\n🧪 Test {i+1}: {test_data['name']}")
            print(f"   Shape: {test_data['data'].shape}")
            print(f"   Description: {test_data['description']}")
            
            # Create viewer
            viewer = pn.pane.Perspective(
                object=test_data['data'],
                sizing_mode='stretch_width',
                min_height=300,
                margin=(10, 10)
            )
            
            # Add to layout
            layout_items.extend([
                pn.pane.HTML(f"<h2>Test {i+1}: {test_data['name']}</h2>"),
                pn.pane.HTML(f"<p><em>{test_data['description']}</em></p>"),
                pn.pane.HTML(f"<p><strong>Shape:</strong> {test_data['data'].shape[0]} rows × {test_data['data'].shape[1]} columns</p>"),
                viewer,
                pn.Spacer(height=30)
            ])
        
        # Create layout
        layout = pn.Column(*layout_items, sizing_mode='stretch_width')
        
        print(f"\n🚀 Starting test server on http://localhost:5010")
        print("📝 Check each Perspective viewer:")
        print("   - Look for data rows in the datagrid")
        print("   - Check if any datasets show data correctly")
        print("   - Compare behavior between different datasets")
        print("\n🛑 Press Ctrl+C to stop the server")
        
        # Serve the test
        layout.show(port=5010, autoreload=True, title="Perspective Datagrid Fix Testing")
        
    except Exception as e:
        print(f"❌ Fix testing failed: {e}")
        import traceback
        traceback.print_exc()

def test_perspective_api_direct():
    """Test Perspective with direct data loading."""
    print("\n" + "="*70) 
    print("🎯 TESTING PERSPECTIVE API DIRECTLY")
    print("="*70)
    
    try:
        # Create test data
        test_data = pd.DataFrame({
            'id': range(1, 21),
            'name': [f'Item_{i}' for i in range(1, 21)],
            'value': [i * 1.5 for i in range(1, 21)],
            'category': ['A', 'B', 'C', 'D'] * 5
        })
        
        print(f"✅ Test data created: {test_data.shape}")
        print(test_data.head())
        
        # Test different Perspective configurations
        viewers = []
        
        # Default configuration
        viewer1 = pn.pane.Perspective(
            test_data,
            sizing_mode='stretch_width',
            min_height=300
        )
        viewers.append(("Default Config", viewer1))
        
        # With explicit plugin
        viewer2 = pn.pane.Perspective(
            test_data,
            sizing_mode='stretch_width', 
            min_height=300,
            plugin='datagrid'
        )
        viewers.append(("Explicit Datagrid Plugin", viewer2))
        
        # Create layout
        layout_items = ["# Direct Perspective API Test"]
        
        for name, viewer in viewers:
            layout_items.extend([
                pn.pane.HTML(f"<h2>{name}</h2>"),
                viewer,
                pn.Spacer(height=20)
            ])
        
        layout = pn.Column(*layout_items, sizing_mode='stretch_width')
        
        print(f"\n🚀 Starting direct API test on http://localhost:5011")
        layout.show(port=5011, autoreload=True, title="Direct Perspective API Test")
        
    except Exception as e:
        print(f"❌ Direct API test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Perspective datagrid fixes')
    parser.add_argument('--mode', choices=['fixes', 'direct'], 
                       default='fixes', help='Test mode to run')
    
    args = parser.parse_args()
    
    if args.mode == 'direct':
        test_perspective_api_direct()
    else:
        test_perspective_fixes()