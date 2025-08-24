"""
Test Script for Universal Query Engine

Tests the new query engine against existing data to ensure compatibility
with current database and verify it can replace the 22+ redundant methods.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src_clean.core.query_engine import get_segments_data, get_query_engine
from src_clean.core.query_filters import (
    group_filter, segment_filter, technique_filter, statistics_filter,
    AggregationType, QueryScope
)
from src_clean.backend.api import get_backend_api


def test_query_engine_vs_existing():
    """Test query engine against existing API methods for compatibility."""
    
    print("🧪 Testing Universal Query Engine vs Existing Methods")
    print("=" * 60)
    
    # Initialize
    api = get_backend_api()
    
    # Test 1: Compare group statistics
    print("\n1. Testing Group Statistics Query:")
    
    # Get available cells first
    cells = api.get_cells()
    if not cells:
        print("❌ No cells found in database")
        return
    
    print(f"   Found {len(cells)} cells: {[c['name'] for c in cells[:3]]}")
    
    # Get groups for first cell
    cell_name = cells[0]['name']
    groups = api.get_user_groups(cell_name)
    if not groups:
        print(f"❌ No groups found for cell {cell_name}")
        return
    
    print(f"   Found {len(groups)} groups in {cell_name}")
    
    # Test with first 2 groups
    test_group_ids = [str(g['group_id']) for g in groups[:2]]
    print(f"   Testing with groups: {test_group_ids}")
    
    try:
        # OLD METHOD: get_group_base_statistics
        old_stats = api.get_group_base_statistics(test_group_ids)
        print(f"   ✅ Old method returned {len(old_stats)} metrics")
        
        # NEW METHOD: Universal query engine
        filters = statistics_filter(test_group_ids)
        new_stats = get_segments_data(filters)
        print(f"   ✅ New method returned {len(new_stats)} metrics")
        
        # Compare results
        if old_stats and new_stats:
            # Check if both have duration_s statistics
            if 'duration_s' in old_stats and 'duration_s' in new_stats:
                old_mean = old_stats['duration_s']['mean']
                new_mean = new_stats['duration_s']['mean']
                diff = abs(old_mean - new_mean) if old_mean and new_mean else 0
                print(f"   📊 Duration mean: old={old_mean:.3f}s, new={new_mean:.3f}s, diff={diff:.6f}s")
                
                if diff < 0.001:  # 1ms tolerance
                    print("   ✅ Statistics match within tolerance")
                else:
                    print(f"   ⚠️  Statistics differ by {diff:.6f}s")
        
    except Exception as e:
        print(f"   ❌ Error testing group statistics: {e}")
    
    # Test 2: Compare raw segment data
    print("\n2. Testing Raw Segment Data Query:")
    
    try:
        # OLD METHOD: get_multi_group_segments  
        old_segments = api.get_multi_group_segments(test_group_ids)
        print(f"   ✅ Old method returned {len(old_segments)} segments")
        
        # NEW METHOD: Universal query engine
        from src_clean.core.query_filters import AggregationType
        filters = group_filter(test_group_ids, AggregationType.RAW)
        new_segments = get_segments_data(filters)
        print(f"   ✅ New method returned {len(new_segments)} segments")
        
        # Compare segment counts
        if len(old_segments) == len(new_segments):
            print("   ✅ Segment counts match")
        else:
            print(f"   ⚠️  Segment counts differ: old={len(old_segments)}, new={len(new_segments)}")
        
        # Compare first segment data if available
        if old_segments and new_segments:
            old_seg = old_segments[0]
            new_seg = new_segments[0]
            
            # Compare a few key fields
            key_fields = ['id', 'start_time_s', 'duration_s', 'start_potential_v']
            matches = 0
            for field in key_fields:
                if field in old_seg and field in new_seg:
                    if old_seg[field] == new_seg[field]:
                        matches += 1
            
            print(f"   📊 Key fields matching: {matches}/{len(key_fields)}")
            
            if matches == len(key_fields):
                print("   ✅ Segment data matches")
            else:
                print("   ⚠️  Some segment fields differ")
        
    except Exception as e:
        print(f"   ❌ Error testing raw segments: {e}")
    
    # Test 3: Test technique filtering
    print("\n3. Testing Technique Filtering:")
    
    try:
        # NEW METHOD: Technique filtering (replaces get_segments_by_technique)
        filters = technique_filter(['Rest'], [cell_name])
        rest_segments = get_segments_data(filters)
        print(f"   ✅ Found {len(rest_segments)} REST segments")
        
        if rest_segments:
            techniques = set(seg.get('fundamental_technique', 'Unknown') for seg in rest_segments)
            print(f"   📊 Techniques found: {techniques}")
        
    except Exception as e:
        print(f"   ❌ Error testing technique filtering: {e}")
    
    # Test 4: Test count queries
    print("\n4. Testing Count Queries:")
    
    try:
        from src_clean.core.query_filters import QueryFilters, AggregationType
        
        filters = QueryFilters(
            group_ids=test_group_ids,
            aggregation=AggregationType.COUNT
        )
        counts = get_segments_data(filters)
        print(f"   ✅ Count query returned: {counts}")
        
    except Exception as e:
        print(f"   ❌ Error testing count query: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Query Engine Testing Complete")


def test_analysis_registry():
    """Test the analysis registry system."""
    
    print("\n🧪 Testing Analysis Registry System")
    print("=" * 60)
    
    try:
        from src_clean.analysis.registry import get_analysis_registry, execute_analysis
        
        # Get registry
        registry = get_analysis_registry()
        print(f"✅ Registry initialized")
        
        # List available analyses
        analyses = registry.list_analyses()
        print(f"✅ Found {len(analyses)} registered analyses:")
        for analysis in analyses:
            print(f"   - {analysis.analysis_id}: {analysis.name}")
        
        # Test analysis options for UI
        options = registry.get_analysis_options()
        print(f"✅ UI options: {options}")
        
        # Test with dummy data
        dummy_segments = [
            {
                'id': 1,
                'fundamental_technique': 'Rest',
                'start_time_s': 0.0,
                'duration_s': 300.0,
                'start_potential_v': 3.7,
                'end_potential_v': 3.75,
                'analysis_results': {}
            },
            {
                'id': 2, 
                'fundamental_technique': 'Rest',
                'start_time_s': 300.0,
                'duration_s': 295.0,
                'start_potential_v': 3.72,
                'end_potential_v': 3.78,
                'analysis_results': {}
            }
        ]
        
        # Test basic statistics analysis
        result = execute_analysis('basic_statistics', dummy_segments, {'metrics': ['duration_s']})
        if 'error' not in result:
            print(f"✅ Basic statistics analysis successful")
            print(f"   Total segments: {result.get('total_segments')}")
            print(f"   Statistics keys: {list(result.get('statistics', {}).keys())}")
        else:
            print(f"❌ Basic statistics failed: {result['error']}")
        
    except Exception as e:
        print(f"❌ Error testing analysis registry: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_query_engine_vs_existing()
    test_analysis_registry()