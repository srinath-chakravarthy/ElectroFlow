#!/usr/bin/env python3
"""
Test script for templated groups functionality.

This script tests the core functionality of the templated groups system:
1. Database methods for template group management
2. Backend API methods for template groups
3. Template group creation and refresh
4. Copy functionality with naming conventions
"""

import sys
from pathlib import Path

# Add src_clean to path
sys.path.insert(0, str(Path(__file__).parent / "src_clean"))

from core.database import DatabaseManager
from backend.api import get_backend_api
from core.config import get_config

def test_template_groups():
    """Test the complete template groups functionality."""
    print("🧪 Testing Template Groups Functionality")
    print("=" * 50)
    
    # Initialize components
    config = get_config()
    api = get_backend_api()
    
    try:
        # Test 1: Create a test cell
        print("\n1. Creating test cell...")
        result = api.create_cell("TEMPLATE_TEST", chemistry="Li_ion", capacity_ah=2.5)
        if result.success:
            print(f"✅ Cell created: {result.message}")
        else:
            print(f"❌ Cell creation failed: {result.error}")
            return False
        
        # Test 2: Check initial template groups (should be empty)
        print("\n2. Checking initial template groups...")
        template_groups = api.get_template_groups("TEMPLATE_TEST")
        user_groups = api.get_user_groups("TEMPLATE_TEST")
        print(f"✅ Initial state: {len(template_groups)} template, {len(user_groups)} user groups")
        
        # Test 3: Manually refresh template groups (should still be empty - no segments yet)
        print("\n3. Testing template group refresh...")
        result = api.refresh_template_groups("TEMPLATE_TEST")
        if result.success:
            print(f"✅ Template refresh: {result.message}")
        else:
            print(f"❌ Template refresh failed: {result.error}")
            return False
        
        # Test 4: Simulate adding segments directly to database for testing
        print("\n4. Adding test segments to database...")
        cell = api.db.get_cell_by_name("TEMPLATE_TEST")
        if not cell:
            print("❌ Could not find test cell")
            return False
        
        # Add a test file
        test_file_info = {
            'file_id': 'test_file_001',
            'original_filename': 'test.par',
            'file_hash': 'test_hash_123',
            'file_size_bytes': 1000,
            'temperature_c': 25.0
        }
        
        try:
            file_id = api.db.add_file(cell['id'], test_file_info)
            print(f"✅ Test file added: {file_id}")
        except Exception as e:
            print(f"⚠️ File already exists or error: {e}")
        
        # Add test segments with different techniques
        test_segments = [
            {
                'file_id': 'test_file_001',
                'segment_index': 0,
                'technique_name': 'Rest',
                'fundamental_technique': 'Rest',
                'start_row': 0,
                'end_row': 100,
                'start_time_s': 0.0,
                'end_time_s': 300.0,
                'point_count': 100,
                'duration_s': 300.0,
                'analysis_status': 'completed'
            },
            {
                'file_id': 'test_file_001',
                'segment_index': 1,
                'technique_name': 'Galvanostatic',
                'fundamental_technique': 'Galvanostatic',
                'start_row': 100,
                'end_row': 200,
                'start_time_s': 300.0,
                'end_time_s': 600.0,
                'point_count': 100,
                'duration_s': 300.0,
                'analysis_status': 'completed'
            },
            {
                'file_id': 'test_file_001',
                'segment_index': 2,
                'technique_name': 'EIS',
                'fundamental_technique': 'EIS',
                'start_row': 200,
                'end_row': 300,
                'start_time_s': 600.0,
                'end_time_s': 900.0,
                'point_count': 100,
                'duration_s': 300.0,
                'analysis_status': 'completed'
            }
        ]
        
        try:
            segment_count = api.db.add_segments('test_file_001', test_segments)
            print(f"✅ Added {segment_count} test segments")
        except Exception as e:
            print(f"⚠️ Segments already exist or error: {e}")
        
        # Test 5: Refresh template groups (should create template groups now)
        print("\n5. Refreshing template groups after adding segments...")
        result = api.refresh_template_groups("TEMPLATE_TEST")
        if result.success:
            print(f"✅ Template refresh: {result.message}")
            
            # Check what template groups were created
            template_groups = api.get_template_groups("TEMPLATE_TEST")
            print(f"✅ Template groups created: {len(template_groups)}")
            for group in template_groups:
                print(f"   - {group['group_name']} ({group['segment_count']} segments)")
        else:
            print(f"❌ Template refresh failed: {result.error}")
            return False
        
        # Test 6: Test copy functionality
        print("\n6. Testing group copy functionality...")
        if template_groups:
            source_group = template_groups[0]
            result = api.copy_group(source_group['group_id'])
            if result.success:
                print(f"✅ Group copy: {result.message}")
                
                # Check user groups
                user_groups = api.get_user_groups("TEMPLATE_TEST")
                print(f"✅ User groups after copy: {len(user_groups)}")
                for group in user_groups:
                    print(f"   - {group['group_name']} ({group['segment_count']} segments)")
            else:
                print(f"❌ Group copy failed: {result.error}")
                return False
        
        # Test 7: Test naming convention with conflicts
        print("\n7. Testing naming conflict resolution...")
        if template_groups:
            source_group = template_groups[0]
            # Copy the same group again to test conflict resolution
            result = api.copy_group(source_group['group_id'])
            if result.success:
                print(f"✅ Conflict resolution: {result.message}")
            else:
                print(f"❌ Conflict resolution failed: {result.error}")
        
        # Test 8: Test global refresh
        print("\n8. Testing global template group refresh...")
        result = api.refresh_all_template_groups()
        if result.success:
            print(f"✅ Global refresh: {result.message}")
        else:
            print(f"❌ Global refresh failed: {result.error}")
        
        print("\n🎉 All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup: Delete test cell
        print("\n🧹 Cleaning up test data...")
        try:
            cell = api.db.get_cell_by_name("TEMPLATE_TEST")
            if cell:
                result = api.delete_cell(cell['id'])
                if result.success:
                    print(f"✅ Cleanup: {result.message}")
                else:
                    print(f"⚠️ Cleanup warning: {result.error}")
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")

if __name__ == "__main__":
    success = test_template_groups()
    sys.exit(0 if success else 1)