#!/usr/bin/env python3
"""Debug script to test VersaStudio parser using the full integrated flow."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.versastudio import VersaStudioParser
from src_clean.parsers.configs.universal_schema import UNIVERSAL_SCHEMA
from src_clean.core.data_models import add_missing_universal_columns

# Test file paths
par_files = [
    Path("./data_clean/cells/test/raw/GITT_EIS_DisCharge_cycle1_Channel 2.par"),
    Path("./data_clean/cells/test/raw/GITT_EIS_Charge_cycle1_Channel 2.par")
]

# Find available file
test_file = None
for par_file in par_files:
    if par_file.exists():
        csv_file = par_file.with_suffix('.par.csv')
        if csv_file.exists():
            test_file = par_file
            break

if test_file:
    print(f"🧪 Testing VersaStudio parser INTEGRATED flow with: {test_file.name}")
    
    try:
        # Create parser
        parser = VersaStudioParser()
        
        # Test the parse_data method (which internally uses _map_to_universal_schema)
        result = parser.parse_data(test_file)
        
        if hasattr(result, 'universal_data'):
            universal_df = result.universal_data
        else:
            universal_df = result['universal_data']
        
        print(f"\n📊 VersaStudio universal DataFrame: {universal_df.shape}")
        
        # Compare with expected
        expected_columns = set(UNIVERSAL_SCHEMA.keys())
        actual_columns = set(universal_df.columns)
        
        print(f"📋 Expected columns: {len(expected_columns)}")
        print(f"📋 Actual columns: {len(actual_columns)}")
        
        # Check for discrepancies
        missing_columns = expected_columns - actual_columns
        extra_columns = actual_columns - expected_columns
        
        if missing_columns:
            print(f"\n❌ Missing columns ({len(missing_columns)}):")
            for col in sorted(missing_columns)[:10]:  # Show first 10
                print(f"   {col}")
            if len(missing_columns) > 10:
                print(f"   ... and {len(missing_columns) - 10} more")
        else:
            print(f"\n✅ All universal schema columns present!")
        
        if extra_columns:
            print(f"\n⚠️ Extra columns ({len(extra_columns)}):")
            for col in sorted(extra_columns):
                print(f"   {col}")
        
        # Show sample of actual columns with proper universal names
        print(f"\n📋 Sample universal columns:")
        key_columns = ["time_s", "current_a", "potential_v", "technique_id", "segment_number"]
        for col in key_columns:
            if col in universal_df.columns:
                non_null = universal_df[col].count()
                total = universal_df.height
                print(f"   ✅ {col}: {non_null}/{total} non-null ({100*non_null/total:.1f}%)")
            else:
                print(f"   ❌ {col}: MISSING")
        
        # Test result comparison
        if len(actual_columns) == len(expected_columns) and not missing_columns:
            print(f"\n🎉 VersaStudio parser returns correct 47-column universal schema!")
        else:
            print(f"\n⚠️ VersaStudio parser column count issue:")
            print(f"   Expected: {len(expected_columns)} columns")
            print(f"   Actual: {len(actual_columns)} columns")
            print(f"   Missing: {len(missing_columns)} columns")
        
    except Exception as e:
        print(f"❌ VersaStudio parser test failed: {e}")
        import traceback
        traceback.print_exc()

else:
    print("❌ No VersaStudio .par/.par.csv file pairs found for testing")
    print("Checked paths:")
    for par_file in par_files:
        csv_file = par_file.with_suffix('.par.csv')
        print(f"   {par_file} + {csv_file.name} ({'✅' if csv_file.exists() else '❌'})")