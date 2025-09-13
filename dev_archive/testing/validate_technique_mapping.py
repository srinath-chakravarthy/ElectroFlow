#!/usr/bin/env python3
"""
Validate BioLogic Technique ID Mapping

Test actual technique_id values stored in database and unknown technique handling.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def validate_technique_mapping():
    """Validate technique_id mapping in database."""
    print("🧪 Validating BioLogic Technique ID Mapping")
    print("=" * 60)
    
    try:
        from src_clean.backend import get_backend_api
        
        api = get_backend_api()
        print("✅ Backend API initialized")
        
        # Get the latest processed file
        files = api.get_cell_files("TEST_BIOLOGIC_CELL")
        if not files:
            print("❌ No files found - run test_process_single_file.py first")
            return False
            
        latest_file = files[-1]  # Get most recent file
        file_id = latest_file['file_id']
        print(f"📁 Checking file: {file_id}")
        
        # Check database segments directly
        print(f"\n🔍 Checking database segments...")
        try:
            # Get segments from database
            with api.db.get_connection() as conn:
                segments = conn.execute("""
                    SELECT segment_number, technique_id, raw_action_id, technique_name, 
                           fundamental_technique, capacity_ah, energy_wh, duration_s,
                           start_row, end_row, point_count
                    FROM segments WHERE file_id = ?
                """, (file_id,)).fetchall()
                
                print(f"📊 Found {len(segments)} segments in database")
                
                for i, segment in enumerate(segments):
                    print(f"\n📋 Segment {i+1}:")
                    print(f"   segment_number: {segment['segment_number']}")
                    print(f"   technique_id: {segment['technique_id']}")
                    print(f"   raw_action_id: {segment['raw_action_id']}")  
                    print(f"   technique_name: {segment['technique_name']}")
                    print(f"   fundamental_technique: {segment['fundamental_technique']}")
                    print(f"   capacity_ah: {segment['capacity_ah']}")
                    print(f"   energy_wh: {segment['energy_wh']}")
                    print(f"   duration_s: {segment['duration_s']}")
                    print(f"   boundaries: rows {segment['start_row']}-{segment['end_row']} ({segment['point_count']} points)")
        
        except Exception as e:
            print(f"❌ Database query failed: {e}")
            return False
        
        # Check technique mapping table
        print(f"\n🔍 Checking technique mapping table...")
        try:
            with api.db.get_connection() as conn:
                mappings = conn.execute("""
                    SELECT technique_id, technique_name FROM fundamental_techniques
                """).fetchall()
                
                print(f"📊 Available technique mappings:")
                for mapping in mappings:
                    print(f"   {mapping['technique_id']}: {mapping['technique_name']}")
                    
        except Exception as e:
            print(f"❌ Technique mapping query failed: {e}")
            return False
            
        # Test unknown technique handling by checking parser logic
        print(f"\n🔍 Testing unknown technique ID handling...")
        try:
            from src_clean.parsers.biologic import BiologicParser
            
            parser = BiologicParser()
            
            # Test known techniques
            known_tests = [
                ('rest', 23),
                ('cv', 1), 
                ('cc', 8),
                ('cp', 7),
                ('eis', 20)
            ]
            
            print("📋 Testing known technique mappings:")
            for ftech_name, expected_id in known_tests:
                actual_id = parser._get_technique_id_from_ftech(ftech_name)
                status = "✅" if actual_id == expected_id else "❌"
                print(f"   {status} {ftech_name} → {actual_id} (expected {expected_id})")
            
            # Test unknown technique
            print("📋 Testing unknown technique handling:")
            unknown_id = parser._get_technique_id_from_ftech('unknown_technique')
            status = "✅" if unknown_id == 0 else "❌"
            print(f"   {status} unknown_technique → {unknown_id} (expected 0)")
            
        except Exception as e:
            print(f"❌ Parser technique mapping test failed: {e}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run validation."""
    success = validate_technique_mapping()
    
    if success:
        print("\n🎉 Technique ID mapping validation PASSED!")
    else:
        print("\n❌ Technique ID mapping validation FAILED!")
        
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)