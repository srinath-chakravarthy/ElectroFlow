#!/usr/bin/env python3
"""Debug script to test integrated BioLogic parser with full universal schema."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser
from src_clean.parsers.configs.universal_schema import UNIVERSAL_SCHEMA
from src_clean.core.data_models import add_missing_universal_columns

# Test file path
mpr_file = Path("/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_Redo_formation_after_GITT_to_check_04_MB_C05.mpr")

if mpr_file.exists():
    print(f"🧪 Testing INTEGRATED BioLogic parser with: {mpr_file.name}")
    
    # Create parser and test the full flow
    parser = BiologicParser()
    
    # Step 1: Raw parsing
    raw_df = parser.mpr_reader.parse_mpr_file(mpr_file)
    print(f"\n📊 Raw BioLogic DataFrame: {raw_df.shape}")
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
        print(f"\n❌ Still missing columns ({len(missing_columns)}):")
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
    key_columns = ["time_s", "current_a", "working_electrode_potential_v", "ce_potential_v", "potential_v"]
    for col in key_columns:
        if col in complete_df.columns:
            non_null = complete_df[col].count()
            total = complete_df.height
            print(f"   {col}: {non_null}/{total} non-null values ({100*non_null/total:.1f}%)")
        else:
            print(f"   {col}: MISSING")
    
    # Show final result structure
    print(f"\n📋 Final DataFrame columns ({len(complete_df.columns)}):")
    for i, col in enumerate(sorted(complete_df.columns)[:20]):
        col_type = complete_df[col].dtype
        non_null = complete_df[col].count()
        print(f"   {i+1:2d}. {col:<35} | {str(col_type):<12} | {non_null:>6} values")
    
    if len(complete_df.columns) > 20:
        print(f"   ... and {len(complete_df.columns) - 20} more columns")
        
else:
    print(f"❌ File not found: {mpr_file}")