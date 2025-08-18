#!/usr/bin/env python3
"""
Test script to isolate the parsing performance issue.
"""

import sys
import time
from pathlib import Path

# Add src_clean directory to path
sys.path.insert(0, '.')

from src_clean.parsers import VersaStudioParser
from src_clean.backend import get_backend_api

def test_parsing():
    """Test parsing with the actual files to see where the hang occurs."""
    print("🔍 Testing File Parsing Performance")
    print("=" * 50)
    
    # Use the actual test files
    par_file = Path("data/measurement_groups/GITT_EIS_Charge_cycle1_Channel 2.par")
    csv_file = Path("data/measurement_groups/GITT_EIS_Charge_cycle1_Channel 2.par.csv")
    
    if not par_file.exists() or not csv_file.exists():
        print(f"❌ Test files not found:")
        print(f"   PAR: {par_file} (exists: {par_file.exists()})")
        print(f"   CSV: {csv_file} (exists: {csv_file.exists()})")
        return
    
    print(f"📁 Found test files:")
    print(f"   PAR: {par_file.name} ({par_file.stat().st_size:,} bytes)")
    print(f"   CSV: {csv_file.name} ({csv_file.stat().st_size:,} bytes)")
    
    # Initialize parser
    print(f"\n🔧 Initializing parser...")
    parser = VersaStudioParser()
    print("✅ Parser initialized")
    
    # Test 1: Basic validation
    print(f"\n🔍 Step 1: Basic file validation...")
    start = time.time()
    try:
        par_valid = parser.validate_file(par_file)
        csv_valid = parser.validate_file(csv_file)
        elapsed = time.time() - start
        print(f"✅ Validation complete in {elapsed:.3f}s")
        print(f"   PAR valid: {par_valid}")
        print(f"   CSV valid: {csv_valid}")
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return
    
    # Test 2: Parse .par file only  
    print(f"\n📊 Step 2: Parse .par file only...")
    start = time.time()
    try:
        par_metadata = parser.parse_metadata(par_file)
        elapsed = time.time() - start
        print(f"✅ PAR parsing complete in {elapsed:.3f}s")
        print(f"   ActionID mappings: {len(par_metadata.actionid_mappings)}")
        print(f"   Techniques: {par_metadata.technique_count}")
    except Exception as e:
        print(f"❌ PAR parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 3: Parse CSV file only  
    print(f"\n📈 Step 3: Parse .csv file only...")
    start = time.time()
    try:
        csv_data = parser.parse_data(csv_file)
        elapsed = time.time() - start
        print(f"✅ CSV parsing complete in {elapsed:.3f}s")
        print(f"   Data rows: {csv_data.universal_data.height:,}")
        print(f"   Data cols: {csv_data.universal_data.width}")
    except Exception as e:
        print(f"❌ CSV parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 4: Backend API validation (what Qt actually calls)
    print(f"\n🔍 Step 4: Backend API validation...")
    start = time.time()
    try:
        api = get_backend_api()
        result = api.validate_dual_files(par_file, csv_file)
        elapsed = time.time() - start
        print(f"✅ Backend validation complete in {elapsed:.3f}s")
        print(f"   Success: {result['success']}")
        print(f"   Message: {result.get('message', 'N/A')}")
    except Exception as e:
        print(f"❌ Backend validation failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 5: Backend API processing (the heavy operation)
    print(f"\n⚙️ Step 5: Backend API processing...")
    start = time.time()
    try:
        result = api.process_dual_files(par_file, csv_file, "TEST_CELL")
        elapsed = time.time() - start
        print(f"✅ Backend processing complete in {elapsed:.3f}s")
        print(f"   Success: {result.success}")
        print(f"   Message: {result.message}")
        print(f"   File ID: {result.file_id}")
    except Exception as e:
        print(f"❌ Backend processing failed: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n" + "=" * 50)
    print("🏁 Full workflow test complete")

if __name__ == "__main__":
    test_parsing()