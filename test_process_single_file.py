#!/usr/bin/env python3
"""
Test process_single_file API method with BioLogic .mpr file

Simple test to verify the complete end-to-end workflow.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Test file path - same as debug script
MPR_FILE_PATH = Path(r"/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_GITT_EIS_1st_charge_interlayer_05_GCPL_C05.mpr")

def test_process_single_file():
    """Test the complete process_single_file workflow."""
    print("🧪 Testing process_single_file() API Method")
    print("=" * 50)
    
    if not MPR_FILE_PATH.exists():
        print(f"❌ File not found: {MPR_FILE_PATH}")
        return
    
    print(f"📁 Using file: {MPR_FILE_PATH.name}")
    
    try:
        # Import backend API
        from src_clean.backend import get_backend_api
        
        api = get_backend_api()
        print("✅ Backend API initialized")
        
        # Test process single file
        print("\n🔄 Testing process_single_file...")
        result = api.process_single_file(
            file_path=MPR_FILE_PATH,
            cell_name="TEST_BIOLOGIC_CELL",
            temperature_c=25.0
        )
        
        if result.success:
            print(f"✅ Processing successful!")
            print(f"📊 File ID: {result.file_id}")
            print(f"📊 Data shape: {result.data.shape if result.data is not None else 'No data'}")
            print(f"📝 Message: {result.message}")
            
            # Check database segments
            print(f"\n🔍 Checking database segments...")
            file_data = api.get_file_data(result.file_id)
            if file_data is not None:
                print(f"📊 Retrieved data shape: {file_data.shape}")
            
            # Check cell files
            cell_files = api.get_cell_files("TEST_BIOLOGIC_CELL")
            print(f"📋 Cell files count: {len(cell_files)}")
            
            return True
            
        else:
            print(f"❌ Processing failed: {result.error}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the test."""
    success = test_process_single_file()
    
    if success:
        print("\n🎉 End-to-end BioLogic integration test PASSED!")
        print("✅ process_single_file() method working correctly")
    else:
        print("\n❌ End-to-end BioLogic integration test FAILED!")
        print("🔧 Check errors above for debugging")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)