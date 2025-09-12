#!/usr/bin/env python3
"""Debug Ns assignment in the raw parser."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser

# Test file path
mpr_file = Path("/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_Redo_formation_after_GITT_to_check_04_MB_C05.mpr")

if mpr_file.exists():
    parser = BiologicParser()
    
    print("=== DEBUGGING Ns ASSIGNMENT IN RAW PARSER ===\n")
    
    # Get raw data from MPRReader
    raw_df = parser.mpr_reader.parse_mpr_file(mpr_file)
    
    print(f"Raw data shape: {raw_df.shape}")
    print(f"Ns column type: {raw_df['Ns'].dtype}")
    
    # Check Ns values and their distribution
    ns_counts = raw_df.group_by('Ns').len().sort('Ns')
    print(f"\nNs value counts:")
    print(ns_counts)
    
    # Look at the first transition: Ns=0 → Ns=1
    print(f"\nFirst Ns transition analysis:")
    
    # Find where Ns changes from 0 to 1
    ns0_data = raw_df.filter(raw_df['Ns'] == 0)
    ns1_data = raw_df.filter(raw_df['Ns'] == 1)
    
    print(f"Ns=0: {len(ns0_data)} points")
    print(f"Ns=1: {len(ns1_data)} points")
    
    # Check boundary rows
    print(f"\nLast 5 rows of Ns=0:")
    print(ns0_data.select(['Ns', 'time', 'I', 'Ewe']).tail(5))
    
    print(f"\nFirst 5 rows of Ns=1:")  
    print(ns1_data.select(['Ns', 'time', 'I', 'Ewe']).head(5))
    
    # Check the raw data around the transition point
    print(f"\nRaw data around Ns transition (rows 8-15):")
    transition_data = raw_df.slice(8, 8).select(['Ns', 'time', 'I', 'Ewe'])
    print(transition_data)
    
    # Check if there are any time gaps or inconsistencies
    print(f"\nTime analysis for Ns=0:")
    ns0_times = ns0_data['time'].to_list()
    print(f"Time range: {min(ns0_times):.1f} - {max(ns0_times):.1f}s")
    print(f"Time gaps: {[ns0_times[i+1] - ns0_times[i] for i in range(min(4, len(ns0_times)-1))]}")
    
    print(f"\nTime analysis for first few Ns=1 points:")
    ns1_times = ns1_data['time'].head(5).to_list()
    print(f"First 5 times: {ns1_times}")
    
    # Check current values at boundaries
    print(f"\nCurrent analysis:")
    ns0_currents = ns0_data['I'].to_list()
    ns1_currents = ns1_data['I'].head(5).to_list()
    
    print(f"Last 5 Ns=0 currents: {ns0_currents[-5:]}")
    print(f"First 5 Ns=1 currents: {ns1_currents}")
    
    # Check if there's a discontinuity that suggests wrong assignment
    print(f"\nPotential boundary issue analysis:")
    print(f"Last Ns=0 current: {ns0_currents[-1]:.6f} mA")
    print(f"First Ns=1 current: {ns1_currents[0]:.6f} mA")
    
    if abs(ns0_currents[-1] - ns1_currents[0]) > 1.0:
        print("⚠️  LARGE CURRENT JUMP - possible boundary assignment error")
    else:
        print("✓ Smooth current transition")
        
else:
    print(f"❌ File not found: {mpr_file}")