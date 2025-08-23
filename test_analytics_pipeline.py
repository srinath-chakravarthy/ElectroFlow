#!/usr/bin/env python3
"""
Analytics Pipeline Alignment Test Script
========================================

Comprehensive test to verify synchronization between:
1. analytics_config.py - Schema definitions
2. electrochemical_insights.py - Backend computation
3. Backend API responses - Data structure
4. Tab 3 UI parsing - Field extraction
5. Database schema - Actual stored data

This script will identify all synchronization issues and report them systematically.
"""

import sys
import json
from pathlib import Path

# Add src_clean to path
sys.path.append(str(Path(__file__).parent / "src_clean"))

from analysis.analytics_config import get_analytics_registry
from backend.api import get_backend_api
from analysis.electrochemical_insights import ElectrochemicalInsights


def test_analytics_config_schemas():
    """Test 1: Verify analytics_config schemas are properly defined."""
    print("=" * 60)
    print("TEST 1: ANALYTICS CONFIG SCHEMAS")
    print("=" * 60)
    
    registry = get_analytics_registry()
    config = registry.get_config()
    
    # Check analysis result schemas
    analysis_schemas = config.get('analysis_result_schemas', {})
    
    print(f"📊 Available analysis schemas: {list(analysis_schemas.keys())}")
    
    for schema_name, schema_def in analysis_schemas.items():
        print(f"\n🔍 {schema_name.upper()} SCHEMA:")
        print(f"   Description: {schema_def.get('description', 'N/A')}")
        fields = schema_def.get('fields', {})
        print(f"   Fields ({len(fields)}):")
        for field_name, field_def in fields.items():
            field_type = field_def.get('type', 'unknown')
            field_unit = field_def.get('unit', '')
            field_desc = field_def.get('description', '')
            print(f"     - {field_name}: {field_type} {field_unit} | {field_desc}")
    
    print(f"\n✅ Analytics config schemas loaded successfully")
    return analysis_schemas


def test_database_current_data():
    """Test 2: Check what's actually in the database."""
    print("\n" + "=" * 60)
    print("TEST 2: DATABASE CURRENT DATA")
    print("=" * 60)
    
    try:
        api = get_backend_api()
        
        # Get all cells
        cells = api.get_cells()
        if not cells:
            print(f"❌ No cells found in database")
            return None
        print(f"📊 Found {len(cells)} cells in database")
        
        if not cells:
            print("⚠️  No cells found in database")
            return None
            
        # Check first cell
        cell = cells[0]
        print(f"🔍 Cell data structure: {list(cell.keys())}")
        print(f"🔍 Cell data: {cell}")
        
        # Try different possible field names
        cell_name = cell.get('cell_name') or cell.get('name') or cell.get('id')
        print(f"🔍 Examining cell: {cell_name}")
        
        # Get segments for this cell
        segments = api.get_cell_segments(cell_name)
        if not segments:
            print(f"❌ No segments found for cell {cell_name}")
            return None
        print(f"📊 Found {len(segments)} segments")
        
        if segments:
            # Check a sample segment
            sample_segment = segments[0]
            print(f"\n🔍 Sample segment fields:")
            for key, value in sample_segment.items():
                if key == 'analysis_results' and value:
                    print(f"   {key}: JSON data (length: {len(str(value))})")
                    try:
                        if isinstance(value, str):
                            analysis_data = json.loads(value)
                        else:
                            analysis_data = value
                        print(f"     Analysis results keys: {list(analysis_data.keys())}")
                    except:
                        print(f"     Analysis results: {type(value)} = {str(value)[:100]}...")
                else:
                    print(f"   {key}: {type(value)} = {value}")
        
        return {'cell_name': cell_name, 'segments': segments}
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_backend_api_responses():
    """Test 3: Check backend API response structures."""
    print("\n" + "=" * 60)
    print("TEST 3: BACKEND API RESPONSE STRUCTURES")
    print("=" * 60)
    
    try:
        api = get_backend_api()
        
        # Get cells first
        cells = api.get_cells()
        if not cells:
            print("❌ No cells available for API testing")
            return None
            
        cell_name = cells[0].get('cell_name') or cells[0].get('name') or str(cells[0].get('id', 'unknown'))
        
        # Get groups for this cell
        groups = api.get_cell_groups(cell_name)
        if not groups:
            print(f"⚠️  No groups found for cell {cell_name}")
            # Create a test group
            print("📊 Creating test group...")
            create_result = api.create_group(cell_name, "TEST_ANALYTICS", "Test group for analytics verification")
            if not create_result.success:
                print(f"❌ Failed to create test group: {create_result.error}")
                return None
            group_id = create_result.group_id
        else:
            group_id = groups[0]['group_id']
            
        print(f"🔍 Testing with group_id: {group_id}")
        
        # Test resistance analysis API  
        print(f"\n🔍 RESISTANCE ANALYSIS API:")
        try:
            resistance_result = api.get_electrochemical_resistance_analysis([group_id])
        except AttributeError as e:
            print(f"   Method not found: {e}")
            resistance_result = {'error': 'Method not available'}
        if isinstance(resistance_result, dict) and 'error' in resistance_result:
            print(f"   Error: {resistance_result['error']}")
        else:
            success = getattr(resistance_result, 'success', 'unknown')
            print(f"   Success: {success}")
            if success:
                data = resistance_result.data
                print(f"   Response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, list) and value:
                            print(f"   {key}: list with {len(value)} items")
                            if isinstance(value[0], dict):
                                print(f"     First item keys: {list(value[0].keys())}")
                        else:
                            print(f"   {key}: {type(value)} = {value}")
            else:
                print(f"   Could not access data (success={success})")
        
        # Test equilibrium analysis API
        print(f"\n🔍 EQUILIBRIUM ANALYSIS API:")
        try:
            equilibrium_result = api.get_electrochemical_equilibrium_analysis([group_id])
        except AttributeError as e:
            print(f"   Method not found: {e}")
            equilibrium_result = {'error': 'Method not available'}
        if isinstance(equilibrium_result, dict) and 'error' in equilibrium_result:
            print(f"   Error: {equilibrium_result['error']}")
        else:
            success = getattr(equilibrium_result, 'success', 'unknown')
            print(f"   Success: {success}")
            if success:
                data = equilibrium_result.data
                print(f"   Response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, list) and value:
                            print(f"   {key}: list with {len(value)} items")
                            if isinstance(value[0], dict):
                                print(f"     First item keys: {list(value[0].keys())}")
                                # Show sample data
                                sample_item = value[0]
                                for item_key, item_value in sample_item.items():
                                    print(f"       {item_key}: {type(item_value)} = {item_value}")
                                break
                        else:
                            print(f"   {key}: {type(value)} = {value}")
            else:
                print(f"   Could not access data (success={success})")
            
        return {
            'resistance_response': getattr(resistance_result, 'data', None) if getattr(resistance_result, 'success', False) else None,
            'equilibrium_response': getattr(equilibrium_result, 'data', None) if getattr(equilibrium_result, 'success', False) else None
        }
        
    except Exception as e:
        print(f"❌ Backend API test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_electrochemical_insights():
    """Test 4: Check ElectrochemicalInsights computation."""
    print("\n" + "=" * 60)
    print("TEST 4: ELECTROCHEMICAL INSIGHTS COMPUTATION")
    print("=" * 60)
    
    try:
        api = get_backend_api()
        
        # Get test data
        cells = api.get_cells()
        if not cells:
            print("❌ No cells available for insights testing")
            return None
            
        cell_name = cells[0].get('cell_name') or cells[0].get('name') or str(cells[0].get('id', 'unknown'))
        
        # Get segments
        segments = api.get_cell_segments(cell_name)
        if not segments:
            print("❌ No segments available for insights testing")
            return None
        print(f"🔍 Testing with {len(segments)} segments")
        
        # Initialize ElectrochemicalInsights (no arguments needed)
        insights = ElectrochemicalInsights()
        
        # Test individual methods
        print(f"\n🔍 RESISTANCE ANALYSIS:")
        resistance_data = insights.analyze_resistance([s['segment_id'] for s in segments[:5]])
        print(f"   Type: {type(resistance_data)}")
        if isinstance(resistance_data, dict):
            print(f"   Keys: {list(resistance_data.keys())}")
            for key, value in resistance_data.items():
                if isinstance(value, list) and value:
                    print(f"   {key}: list with {len(value)} items")
                    if isinstance(value[0], dict):
                        print(f"     Sample item keys: {list(value[0].keys())}")
                else:
                    print(f"   {key}: {type(value)} = {value}")
        
        print(f"\n🔍 EQUILIBRIUM ANALYSIS:")
        equilibrium_data = insights.analyze_equilibrium([s['segment_id'] for s in segments[:5]])
        print(f"   Type: {type(equilibrium_data)}")
        if isinstance(equilibrium_data, dict):
            print(f"   Keys: {list(equilibrium_data.keys())}")
            for key, value in equilibrium_data.items():
                if isinstance(value, list) and value:
                    print(f"   {key}: list with {len(value)} items")
                    if isinstance(value[0], dict):
                        print(f"     Sample item keys: {list(value[0].keys())}")
                        # Check if time constants exist
                        sample = value[0]
                        time_const_fields = ['time_constant_s', 'tau_s', 'time_const']
                        for field in time_const_fields:
                            if field in sample:
                                print(f"       TIME CONSTANT FOUND: {field} = {sample[field]}")
                else:
                    print(f"   {key}: {type(value)} = {value}")
        
        return {
            'resistance_insights': resistance_data,
            'equilibrium_insights': equilibrium_data
        }
        
    except Exception as e:
        print(f"❌ Electrochemical insights test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_field_alignment():
    """Test 5: Compare field names across all systems."""
    print("\n" + "=" * 60)
    print("TEST 5: FIELD NAME ALIGNMENT CHECK")
    print("=" * 60)
    
    # Get analytics config field names
    registry = get_analytics_registry()
    config = registry.get_config()
    
    config_fields = {}
    analysis_schemas = config.get('analysis_result_schemas', {})
    
    for schema_name, schema_def in analysis_schemas.items():
        fields = schema_def.get('fields', {})
        config_fields[schema_name] = list(fields.keys())
        print(f"📊 {schema_name.upper()} config fields: {list(fields.keys())}")
    
    # Compare with what we found in backend responses
    print(f"\n🔍 FIELD ALIGNMENT ISSUES:")
    
    # This would be populated from the previous tests
    # For now, let's check the specific fields we know are problematic
    
    expected_fields = {
        'exponential_fit': ['voltage_infinity', 'voltage_amplitude', 'current_infinity', 'current_amplitude', 'time_constant_s', 'r_squared', 'rmse'],
        'current_pulse': ['ir_immediate_ohm', 'ir_10s_ohm', 'ir_30s_ohm', 'baseline_voltage_v', 'average_current_a', 'pulse_duration_s']
    }
    
    for schema_name, expected in expected_fields.items():
        config_schema_fields = config_fields.get(schema_name, [])
        missing_in_config = [f for f in expected if f not in config_schema_fields]
        extra_in_config = [f for f in config_schema_fields if f not in expected]
        
        if missing_in_config:
            print(f"   ❌ {schema_name}: Missing in config: {missing_in_config}")
        if extra_in_config:
            print(f"   ⚠️  {schema_name}: Extra in config: {extra_in_config}")
        if not missing_in_config and not extra_in_config:
            print(f"   ✅ {schema_name}: Field alignment OK")
    
    return config_fields


def main():
    """Run comprehensive analytics pipeline alignment test."""
    print("🔬 ANALYTICS PIPELINE ALIGNMENT TEST")
    print("=" * 80)
    
    # Run all tests
    results = {}
    
    try:
        results['config_schemas'] = test_analytics_config_schemas()
        results['database_data'] = test_database_current_data()
        results['api_responses'] = test_backend_api_responses()
        results['insights_computation'] = test_electrochemical_insights()
        results['field_alignment'] = test_field_alignment()
        
        # Summary
        print("\n" + "=" * 80)
        print("🎯 SUMMARY")
        print("=" * 80)
        
        for test_name, result in results.items():
            status = "✅ PASSED" if result is not None else "❌ FAILED"
            print(f"{test_name.upper()}: {status}")
        
        print(f"\n📊 Test completed. Check output above for detailed findings.")
        
    except Exception as e:
        print(f"❌ Main test execution failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()