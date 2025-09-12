#!/usr/bin/env python3
"""Debug where segment expansion from 25 Ns values to 90 segments happens."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser
import polars as pl

# Test file path
mpr_file = Path("/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_Redo_formation_after_GITT_to_check_04_MB_C05.mpr")

if mpr_file.exists():
    parser = BiologicParser()
    
    # Step 1: Raw data
    print("=== STEP 1: Raw MPR Data ===")
    raw_df = parser.mpr_reader.parse_mpr_file(mpr_file)
    ns_values = raw_df["Ns"].unique().sort()
    print(f"Raw Ns values: {len(ns_values)} ({ns_values.to_list()[:10]}...)")
    
    # Step 2: After segment number assignment
    print("\n=== STEP 2: After _add_segment_numbers_to_raw_data ===")
    df_with_segments = parser._add_segment_numbers_to_raw_data(raw_df)
    segment_numbers = df_with_segments["segment_number"].unique().sort()
    print(f"Segment numbers: {len(segment_numbers)} ({segment_numbers.to_list()[:10]}...)")
    
    # Check if segment_number matches Ns values
    for i, ns_val in enumerate(ns_values.to_list()[:5]):
        rows_with_ns = df_with_segments.filter(pl.col("Ns") == ns_val)
        unique_segments = rows_with_ns["segment_number"].unique().to_list()
        print(f"  Ns={ns_val} -> segment_number: {unique_segments}")
    
    # Step 3: After technique ID assignment  
    print("\n=== STEP 3: After _add_technique_ids_to_raw_data ===")
    df_with_techniques = parser._add_technique_ids_to_raw_data(df_with_segments)
    technique_ids = df_with_techniques["technique_id"].unique().sort()
    print(f"Technique IDs: {len(technique_ids)} ({technique_ids.to_list()})")
    print(f"Still {len(df_with_techniques['segment_number'].unique())} segments")
    
    # Step 4: After universal schema conversion
    print("\n=== STEP 4: After _map_to_universal_schema ===")
    universal_df = parser._map_to_universal_schema(df_with_techniques)
    if 'segment_number' in universal_df.columns:
        final_segments = universal_df["segment_number"].unique().sort()
        print(f"Final segments: {len(final_segments)} ({final_segments.to_list()[:10]}...)")
    else:
        print("No segment_number column in universal schema!")
    
    # Step 5: Check boundary issue
    print("\n=== STEP 5: Boundary Analysis ===")
    # Find the boundary between Ns=0 and Ns=1
    ns0_data = df_with_techniques.filter(pl.col("Ns") == 0)
    ns1_data = df_with_techniques.filter(pl.col("Ns") == 1) 
    
    print(f"Ns=0: {len(ns0_data)} points, segment_number range: {ns0_data['segment_number'].unique().to_list()}")
    print(f"Ns=1: {len(ns1_data)} points, segment_number range: {ns1_data['segment_number'].unique().to_list()}")
    
    # Check last few rows of Ns=0 and first few rows of Ns=1
    print("\nLast 3 rows of Ns=0:")
    print(ns0_data.select(['Ns', 'segment_number', 'I']).tail(3))
    print("\nFirst 3 rows of Ns=1:")
    print(ns1_data.select(['Ns', 'segment_number', 'I']).head(3))
    
else:
    print(f"❌ File not found: {mpr_file}")