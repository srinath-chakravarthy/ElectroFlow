#!/usr/bin/env python3
"""
Test the new simplified backend API.
"""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, 'src')

from backend_api import BackendAPI

def test_backend_api():
    """Test the new backend API functionality."""
    print("🔧 Testing New Simplified Backend API")
    print("=" * 50)
    
    # Initialize API
    api = BackendAPI()
    print("✅ Backend API initialized")
    
    # Test file validation
    par_path = Path("data/measurement_groups/GITT_EIS_Charge_cycle1_Channel 2.par")
    csv_path = Path("data/measurement_groups/GITT_EIS_Charge_cycle1_Channel 2.par.csv")
    
    if not par_path.exists() or not csv_path.exists():
        print("❌ Test files not found")
        return
    
    print(f"\n📁 Testing file validation...")
    validation_result = api.validate_files([par_path, csv_path])
    
    print(f"✅ Validation result:")
    print(f"   Success: {validation_result.success}")
    print(f"   Message: {validation_result.message}")
    print(f"   Valid files: {validation_result.details.get('total_valid', 0)}")
    print(f"   Dual pairs: {validation_result.details.get('has_dual_pairs', False)}")
    
    # Test cell creation
    print(f"\n👤 Testing cell creation...")
    create_result = api.create_cell(
        cell_name="TEST_CELL_API",
        description="Test cell for new API",
        chemistry="Li_metal"
    )
    
    print(f"✅ Cell creation result:")
    print(f"   Success: {create_result.success}")
    print(f"   Message: {create_result.message}")
    if create_result.error:
        print(f"   Error: {create_result.error}")
    
    # Test getting cells
    print(f"\n📊 Testing cell retrieval...")
    cells = api.get_cells()
    print(f"✅ Found {len(cells)} cells in database")
    
    # Test ActionID mappings
    print(f"\n🔧 Testing ActionID mappings...")
    mappings = api.get_actionid_mappings()
    print(f"✅ Found {len(mappings)} ActionID mappings")
    
    print(f"\n" + "=" * 50)
    print("🏁 Backend API test complete")

if __name__ == "__main__":
    test_backend_api()