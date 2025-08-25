#!/usr/bin/env python3
"""
Quick check of segment analysis_results to understand current state
"""

import sys
import json
from pathlib import Path

# Add src_clean to path
sys.path.append(str(Path(__file__).parent / "src_clean"))

from backend.api import get_backend_api

def main():
    api = get_backend_api()
    
    # Get cell and segments
    cells = api.get_cells()
    if not cells:
        print("No cells found")
        return
        
    cell_name = cells[0]['name']
    segments = api.get_cell_segments(cell_name)
    
    print(f"Examining analysis_results for cell: {cell_name}")
    print(f"Total segments: {len(segments)}")
    
    # Check first 5 segments
    for i, segment in enumerate(segments[:5]):
        segment_id = segment['id']
        technique = segment['technique_name']
        analysis_status = segment['analysis_status']
        analysis_results = segment['analysis_results']
        
        print(f"\n--- SEGMENT {i+1} ---")
        print(f"ID: {segment_id}")
        print(f"Technique: {technique}")
        print(f"Analysis Status: {analysis_status}")
        
        if analysis_results:
            if isinstance(analysis_results, str):
                try:
                    parsed_results = json.loads(analysis_results)
                    print(f"Analysis Results Keys: {list(parsed_results.keys())}")
                    print(f"Analysis Results: {parsed_results}")
                except json.JSONDecodeError as e:
                    print(f"Failed to parse JSON: {e}")
                    print(f"Raw analysis_results: {analysis_results}")
            else:
                print(f"Analysis Results: {analysis_results}")
        else:
            print("Analysis Results: None")
    
    # Check technique distribution
    techniques = {}
    analysis_statuses = {}
    
    for segment in segments:
        tech = segment['technique_name']
        status = segment['analysis_status']
        
        techniques[tech] = techniques.get(tech, 0) + 1
        analysis_statuses[status] = analysis_statuses.get(status, 0) + 1
    
    print(f"\n--- SUMMARY ---")
    print(f"Technique distribution: {techniques}")
    print(f"Analysis status distribution: {analysis_statuses}")

if __name__ == "__main__":
    main()