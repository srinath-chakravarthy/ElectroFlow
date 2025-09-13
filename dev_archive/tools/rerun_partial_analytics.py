#!/usr/bin/env python3
"""
Re-run analytics on the 31 partial segments to complete the dataset
"""

import sys
from pathlib import Path

# Add src_clean to path
sys.path.append(str(Path(__file__).parent / "src_clean"))

from backend.api import get_backend_api
from analysis.fundamental_analytics import FundamentalAnalytics

def main():
    api = get_backend_api()
    
    # Get all segments
    cells = api.get_cells()
    cell_name = cells[0]['name']
    segments = api.get_cell_segments(cell_name)
    
    # Find partial segments
    partial_segments = [s for s in segments if s['analysis_status'] == 'partial']
    
    print(f"Found {len(partial_segments)} partial segments to re-analyze")
    
    if not partial_segments:
        print("No partial segments found - all analytics complete!")
        return
    
    # Initialize fundamental analytics
    analytics = FundamentalAnalytics()
    
    # Process partial segments
    completed_count = 0
    failed_count = 0
    
    for segment in partial_segments:
        segment_id = segment['id']
        technique = segment['technique_name']
        
        print(f"Re-analyzing segment {segment_id} ({technique})...")
        
        try:
            # Run analytics on this segment
            result = analytics.analyze_segment_comprehensive(segment_id)
            
            if result and result.get('success', False):
                completed_count += 1
                print(f"  ✅ Completed {segment_id}")
            else:
                failed_count += 1
                print(f"  ❌ Failed {segment_id}: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            failed_count += 1
            print(f"  ❌ Exception {segment_id}: {e}")
    
    print(f"\n📊 REANALYSIS SUMMARY:")
    print(f"Completed: {completed_count}")
    print(f"Failed: {failed_count}")
    print(f"Total processed: {len(partial_segments)}")

if __name__ == "__main__":
    main()