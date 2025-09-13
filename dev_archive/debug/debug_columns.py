#!/usr/bin/env python3
"""Quick debug script to see actual vs expected column names."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser
from src_clean.parsers.configs.universal_schema import UNIVERSAL_SCHEMA

# Test file path
mpr_file = Path("/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_Redo_formation_after_GITT_to_check_04_MB_C05.mpr")

if mpr_file.exists():
    print(f"🧪 Testing with: {mpr_file.name}")
    
    # Create parser and parse data
    parser = BiologicParser()
    result = parser.parse_data(mpr_file)
    
    if hasattr(result, 'universal_data'):
        universal_df = result.universal_data
    else:
        universal_df = result['universal_data']
    
    # Get actual columns
    actual_columns = set(universal_df.columns)
    expected_columns = set(UNIVERSAL_SCHEMA.keys())
    
    print(f"\n📊 DataFrame shape: {universal_df.shape}")
    print(f"📋 Expected columns in universal schema: {len(expected_columns)}")
    print(f"📋 Actual columns in DataFrame: {len(actual_columns)}")
    
    # Missing columns
    missing_columns = expected_columns - actual_columns
    if missing_columns:
        print(f"\n❌ Missing columns ({len(missing_columns)}):")
        for col in sorted(missing_columns):
            print(f"   {col}")
    
    # Extra columns (shouldn't happen)
    extra_columns = actual_columns - expected_columns
    if extra_columns:
        print(f"\n⚠️ Extra columns ({len(extra_columns)}):")
        for col in sorted(extra_columns):
            print(f"   {col}")
    
    # Sample of actual column names
    print(f"\n📋 Sample of actual column names:")
    for i, col in enumerate(sorted(actual_columns)[:15]):
        print(f"   {i+1:2d}. {col}")
    if len(actual_columns) > 15:
        print(f"   ... and {len(actual_columns) - 15} more columns")
    
    print(f"\n🔍 First 5 expected universal schema columns:")
    for i, col in enumerate(sorted(expected_columns)[:5]):
        units = UNIVERSAL_SCHEMA[col]['units']
        desc = UNIVERSAL_SCHEMA[col]['description']
        print(f"   {i+1:2d}. {col} [{units}] - {desc}")
        
else:
    print(f"❌ File not found: {mpr_file}")