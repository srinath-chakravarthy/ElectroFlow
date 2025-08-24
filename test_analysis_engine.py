"""
Test Script for Analysis Engine Integration

Tests the new analysis engine against existing API methods to verify compatibility
and that it can replace the 35+ redundant API methods.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src_clean.backend.analysis_engine import get_analysis_engine, get_basic_statistics, get_electrochemical_analysis
from src_clean.backend.api import get_backend_api
from src_clean.core.query_filters import group_filter, AggregationType


def test_analysis_engine_vs_api():
    """Test analysis engine against existing API methods."""
    
    print("🧪 Testing Analysis Engine vs Existing API Methods")
    print("=" * 70)
    
    # Initialize
    api = get_backend_api()
    engine = get_analysis_engine()
    
    # Get test data
    cells = api.get_cells()
    if not cells:
        print("❌ No cells found in database")
        return
    
    cell_name = cells[0]['name'] 
    groups = api.get_user_groups(cell_name)
    if len(groups) < 2:
        print(f"❌ Need at least 2 groups, found {len(groups)}")
        return
    
    test_group_ids = [str(g['group_id']) for g in groups[:2]]
    print(f"Testing with groups: {test_group_ids} from cell: {cell_name}")
    
    # Test 1: Basic Statistics Analysis
    print("\n1. Testing Basic Statistics Analysis:")
    
    try:
        # OLD METHOD: API get_group_base_statistics
        old_stats = api.get_group_base_statistics(test_group_ids)
        print(f"   ✅ Old API method: {len(old_stats)} metrics")
        
        # NEW METHOD: Analysis Engine
        new_stats = get_basic_statistics(test_group_ids)
        
        if "error" not in new_stats:
            print(f"   ✅ New analysis engine: working")
            # Check compatibility
            if isinstance(new_stats, dict) and "statistics" in new_stats:
                engine_stats = new_stats["statistics"]
                if "duration_s" in old_stats and "duration_s" in engine_stats:
                    old_mean = old_stats["duration_s"]["mean"]
                    new_mean = engine_stats["duration_s"]["mean"]
                    print(f"   📊 Duration comparison: old={old_mean:.3f}s, new={new_mean:.3f}s")
                    
                    if abs(old_mean - new_mean) < 0.01:
                        print("   ✅ Statistics are compatible")
                    else:
                        print("   ⚠️  Statistics differ")
        else:
            print(f"   ❌ New engine error: {new_stats.get('error')}")
            
    except Exception as e:
        print(f"   ❌ Basic statistics test error: {e}")
    
    # Test 2: Resistance Analysis
    print("\n2. Testing Resistance Analysis:")
    
    try:
        # OLD METHOD: API get_electrochemical_resistance_analysis  
        old_resistance = api.get_electrochemical_resistance_analysis(test_group_ids)
        print(f"   ✅ Old API method: {type(old_resistance)}")
        
        # NEW METHOD: Analysis Engine
        new_resistance = get_electrochemical_analysis("resistance_analysis", test_group_ids)
        
        if "error" not in new_resistance:
            print(f"   ✅ New analysis engine: working")
            print(f"   📊 New engine fields: {list(new_resistance.keys())}")
        else:
            print(f"   ❌ New engine error: {new_resistance.get('error')}")
            
    except Exception as e:
        print(f"   ❌ Resistance analysis test error: {e}")
    
    # Test 3: Kinetics Analysis
    print("\n3. Testing Kinetics Analysis:")
    
    try:
        # OLD METHOD: API get_electrochemical_rest_analysis
        old_kinetics = api.get_electrochemical_rest_analysis(test_group_ids)
        print(f"   ✅ Old API method: {type(old_kinetics)}")
        
        # NEW METHOD: Analysis Engine
        new_kinetics = get_electrochemical_analysis("kinetics_analysis", test_group_ids)
        
        if "error" not in new_kinetics:
            print(f"   ✅ New analysis engine: working")
            print(f"   📊 New engine fields: {list(new_kinetics.keys())}")
        else:
            print(f"   ❌ New engine error: {new_kinetics.get('error')}")
            
    except Exception as e:
        print(f"   ❌ Kinetics analysis test error: {e}")
    
    # Test 4: Registry Functionality
    print("\n4. Testing Analysis Registry:")
    
    try:
        # Get available analyses
        available = engine.get_available_analyses()
        print(f"   ✅ Registry has {len(available)} analyses:")
        for analysis in available:
            print(f"      - {analysis['id']}: {analysis['name']}")
        
        # Test unified analysis 
        unified = engine.get_unified_analysis(test_group_ids, ["basic_statistics", "resistance_analysis"])
        if "error" not in unified:
            print(f"   ✅ Unified analysis working: {len(unified.get('results', {}))} results")
        else:
            print(f"   ❌ Unified analysis error: {unified.get('error')}")
            
    except Exception as e:
        print(f"   ❌ Registry test error: {e}")
    
    print("\n" + "=" * 70)
    print("🎉 Analysis Engine Testing Complete")


if __name__ == "__main__":
    test_analysis_engine_vs_api()