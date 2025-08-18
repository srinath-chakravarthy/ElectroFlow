#!/usr/bin/env python3
"""
Test script to isolate the parsing performance issue.
"""

import sys
import time
from pathlib import Path

# Add src directory to path
sys.path.insert(0, 'src')

from core.parsers import VersaStudioParser

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
        csv_valid = parser.validate_dual_files(par_file, csv_file)
        elapsed = time.time() - start
        print(f"✅ Validation complete in {elapsed:.3f}s")
        print(f"   PAR valid: {par_valid}")
        print(f"   Dual valid: {csv_valid}")
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return
    
    # Test 2: Parse .par file only
    print(f"\n📊 Step 2: Parse .par file only...")
    start = time.time()
    try:
        par_data = parser.parse(par_file)
        elapsed = time.time() - start
        print(f"✅ PAR parsing complete in {elapsed:.3f}s")
        print(f"   Data rows: {par_data.universal_data.height:,}")
        print(f"   Data cols: {par_data.universal_data.width}")
    except Exception as e:
        print(f"❌ PAR parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 3: Parse CSV file only  
    print(f"\n📈 Step 3: Parse .csv file only...")
    start = time.time()
    try:
        csv_data = parser.parse_calibrated_csv(csv_file)
        elapsed = time.time() - start
        print(f"✅ CSV parsing complete in {elapsed:.3f}s")
        print(f"   Data rows: {csv_data.height:,}")
        print(f"   Data cols: {csv_data.width}")
    except Exception as e:
        print(f"❌ CSV parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 4: Parse dual files (this is where it likely hangs)
    print(f"\n🔄 Step 4: Parse dual files together...")
    start = time.time()
    try:
        # Set a timeout for this test
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Dual file parsing timed out")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)  # 30 second timeout
        
        dual_data = parser.parse_dual_files(par_file, csv_file)
        signal.alarm(0)  # Cancel timeout
        
        elapsed = time.time() - start
        print(f"✅ Dual parsing complete in {elapsed:.3f}s")
        print(f"   Data rows: {dual_data.universal_data.height:,}")
        print(f"   Data cols: {dual_data.universal_data.width}")
        
    except TimeoutError:
        print(f"❌ Dual parsing TIMED OUT after 30 seconds - this is the issue!")
    except Exception as e:
        print(f"❌ Dual parsing failed: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n" + "=" * 50)
    print("🏁 Parsing test complete")

if __name__ == "__main__":
    test_parsing()