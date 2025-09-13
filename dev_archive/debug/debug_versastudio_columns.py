#!/usr/bin/env python3
"""Debug script to test VersaStudio parser column output."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.versastudio import VersaStudioParser
from src_clean.parsers.configs.universal_schema import UNIVERSAL_SCHEMA
from src_clean.core.data_models import add_missing_universal_columns

# Test file paths
par_files = [
    Path("./data_clean/cells/test/raw/GITT_EIS_DisCharge_cycle1_Channel 2.par"),
    Path("./data_clean/cells/test/raw/GITT_EIS_Charge_cycle1_Channel 2.par"),
    Path("./data/cells/AR-3161/raw/GITT_EIS_Charge_cycle1_Channel 2.par")
]

# Find available file
test_file = None
for par_file in par_files:
    if par_file.exists():
        test_file = par_file
        break

if test_file:
    print(f"🧪 Testing VersaStudio parser with: {test_file.name}")
    
    # Create parser and test the full flow
    parser = VersaStudioParser()
    
    # Check if CSV file exists (VersaStudio needs both .par and .par.csv)
    csv_file = test_file.with_suffix('.par.csv')
    if not csv_file.exists():
        print(f"❌ CSV file not found: {csv_file}")
        print("VersaStudio parser requires both .par (metadata) and .par.csv (data) files")
        exit()
    
    print(f"✅ Found both files: {test_file.name} and {csv_file.name}")
    
    # Step 1: Test direct mapping method
    try:
        # Load CSV data
        import polars as pl
        raw_df = pl.read_csv(csv_file, separator=',')
        print(f"\n📊 Raw VersaStudio CSV: {raw_df.shape}")
        print(f"📋 Raw columns sample: {list(raw_df.columns[:10])}")
        
        # Step 2: Map to universal schema (only mapped columns)
        mapped_df = parser._map_to_universal_schema(raw_df)
        print(f"\n📊 Mapped DataFrame: {mapped_df.shape}")
        print(f"📋 Mapped columns: {sorted(mapped_df.columns)}")
        
        # Step 3: Add missing universal columns
        complete_df = add_missing_universal_columns(mapped_df)
        print(f"\n📊 Complete universal DataFrame: {complete_df.shape}")
        
        # Compare with expected
        expected_columns = set(UNIVERSAL_SCHEMA.keys())
        actual_columns = set(complete_df.columns)
        
        print(f"📋 Expected columns: {len(expected_columns)}")
        print(f"📋 Actual columns: {len(actual_columns)}")
        
        # Check for discrepancies
        missing_columns = expected_columns - actual_columns
        extra_columns = actual_columns - expected_columns
        
        if missing_columns:
            print(f"\n❌ Missing columns ({len(missing_columns)}):")
            for col in sorted(missing_columns):
                print(f"   {col}")
        else:
            print(f"\n✅ All universal schema columns present!")
        
        if extra_columns:
            print(f"\n⚠️ Extra columns ({len(extra_columns)}):")
            for col in sorted(extra_columns):
                print(f"   {col}")
        
        # Test data mapping quality
        print(f"\n🔍 Data quality check:")
        key_columns = ["time_s", "current_a", "potential_v", "technique_id", "segment_number"]
        for col in key_columns:
            if col in complete_df.columns:
                non_null = complete_df[col].count()
                total = complete_df.height
                print(f"   {col}: {non_null}/{total} non-null values ({100*non_null/total:.1f}%)")
            else:
                print(f"   {col}: MISSING")
        
        print(f"\n✅ VersaStudio parser test completed successfully!")
        
    except Exception as e:
        print(f"❌ VersaStudio parser test failed: {e}")
        import traceback
        traceback.print_exc()

else:
    print("❌ No VersaStudio .par files found for testing")
    print("Checked paths:")
    for par_file in par_files:
        print(f"   {par_file}")