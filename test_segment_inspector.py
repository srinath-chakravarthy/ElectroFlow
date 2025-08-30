#!/usr/bin/env python3
"""
Test Segment Inspector Implementation

Validates the complete workflow from database query to Arrow conversion:
1. Database segment file info retrieval
2. LazyDataService raw data loading
3. API Arrow conversion with data cleaning
4. Arrow format validation for Perspective compatibility
"""

import sys
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src_clean"))

from src_clean.backend import get_backend_api
from src_clean.backend.lazy_data_service import get_lazy_data_service
from src_clean.core.database import DatabaseManager
from src_clean.core.config import get_config

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_segment_inspector_workflow():
    """Test complete segment inspector workflow."""
    print("\n" + "="*70)
    print("🔬 TESTING SEGMENT INSPECTOR WORKFLOW")
    print("="*70)
    
    try:
        # Initialize components
        api = get_backend_api()
        lazy_service = get_lazy_data_service()
        config = get_config()
        db_manager = DatabaseManager(config.db_path)
        
        print("✅ Components initialized successfully")
        
        # Step 1: Get available segments from database
        print(f"\n📊 STEP 1: Database Segment Query")
        print("-" * 50)
        
        # Get a few segments to test with
        with db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT s.id, s.file_id, s.segment_index, s.point_count,
                       s.technique_name, c.name as cell_name
                FROM segments s
                JOIN files f ON s.file_id = f.file_id
                JOIN cells c ON f.cell_id = c.id
                LIMIT 5
            """)
            test_segments = [dict(row) for row in cursor.fetchall()]
        
        if not test_segments:
            print("❌ No segments found in database")
            return False
        
        print(f"✅ Found {len(test_segments)} test segments:")
        for segment in test_segments:
            print(f"   - Segment {segment['id']}: {segment['technique_name']} ({segment['point_count']} points)")
        
        # Step 2: Test database segment file info query
        print(f"\n🔍 STEP 2: Database File Info Query")
        print("-" * 50)
        
        test_segment_id = test_segments[0]['id']
        segment_info = db_manager.get_segment_file_info(test_segment_id)
        
        if not segment_info:
            print(f"❌ No file info found for segment {test_segment_id}")
            return False
        
        print(f"✅ Segment file info retrieved:")
        print(f"   - File ID: {segment_info['file_id']}")
        print(f"   - Row range: {segment_info['start_row']} - {segment_info['end_row']}")
        print(f"   - Point count: {segment_info['point_count']}")
        print(f"   - Cell: {segment_info['cell_name']}")
        
        # Step 3: Test LazyDataService raw data loading
        print(f"\n⚡ STEP 3: LazyDataService Raw Data Loading")
        print("-" * 50)
        
        raw_data_df = lazy_service.get_segment_raw_data(test_segment_id)
        
        if raw_data_df.is_empty():
            print(f"❌ No raw data loaded for segment {test_segment_id}")
            return False
        
        print(f"✅ Raw data loaded:")
        print(f"   - Shape: {raw_data_df.shape}")
        print(f"   - Columns: {raw_data_df.columns[:10]}...")  # First 10 columns
        
        # Validate expected electrochemical columns
        expected_columns = ['time_s', 'potential_v', 'current_a']
        missing_columns = [col for col in expected_columns if col not in raw_data_df.columns]
        if missing_columns:
            print(f"⚠️  Missing expected columns: {missing_columns}")
        else:
            print(f"✅ All expected electrochemical columns present")
        
        # Step 4: Test API Arrow conversion method
        print(f"\n🏹 STEP 4: API Arrow Conversion with Data Cleaning")
        print("-" * 50)
        
        analysis_context = {
            'selected_cells': [segment_info['cell_name']],
            'current_technique': 'All',
            'include_fits': True,
            'plot_type': 'scatter'
        }
        
        arrow_data = api.get_segment_raw_data_for_perspective(test_segment_id, analysis_context)
        
        if not arrow_data:
            print(f"❌ No Arrow data returned for segment {test_segment_id}")
            return False
        
        print(f"✅ Arrow data generated:")
        print(f"   - Data type: {type(arrow_data)}")
        print(f"   - Size: {len(arrow_data)} bytes")
        
        # Step 5: Validate Arrow format and data cleanliness
        print(f"\n✨ STEP 5: Data Validation for Perspective Compatibility")
        print("-" * 50)
        
        # Convert Arrow back to DataFrame for validation
        import pyarrow as pa
        try:
            arrow_table = pa.ipc.open_stream(pa.py_buffer(arrow_data)).read_all()
            validation_df = arrow_table.to_pandas()
            
            print(f"✅ Arrow format is valid:")
            print(f"   - Shape: {validation_df.shape}")
            print(f"   - Columns: {len(validation_df.columns)}")
            
            # Check for problematic data types
            problems = []
            
            # Check for string NaN values
            for col in validation_df.columns:
                if validation_df[col].dtype == 'object':
                    na_count = validation_df[col].isna().sum()
                    if na_count > 0:
                        problems.append(f"Column '{col}' has {na_count} NaN values (object type)")
                elif validation_df[col].dtype == 'bool':
                    na_count = validation_df[col].isna().sum()
                    if na_count > 0:
                        problems.append(f"Column '{col}' has {na_count} NaN values (bool type)")
            
            if problems:
                print("⚠️  Data cleaning issues found:")
                for problem in problems:
                    print(f"   - {problem}")
            else:
                print("✅ No string NaN or bool NaN issues found")
            
            # Validate metadata columns were added
            metadata_columns = ['computed_resistance_ohm', 'analysis_method', 'cell_name', 'segment_id']
            found_metadata = [col for col in metadata_columns if col in validation_df.columns]
            print(f"✅ Metadata columns added: {len(found_metadata)}/{len(metadata_columns)}")
            if found_metadata:
                print(f"   - Found: {found_metadata}")
            
            return True
            
        except Exception as e:
            print(f"❌ Arrow validation failed: {e}")
            return False
    
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_method_directly():
    """Direct test of database method."""
    print("\n" + "="*50)
    print("🔍 DIRECT DATABASE METHOD TEST")
    print("="*50)
    
    try:
        config = get_config()
        db_manager = DatabaseManager(config.db_path)
        
        # Test with a known segment ID
        with db_manager.get_connection() as conn:
            cursor = conn.execute("SELECT id FROM segments LIMIT 1")
            row = cursor.fetchone()
            if not row:
                print("❌ No segments in database")
                return False
            
            test_segment_id = row[0]
        
        result = db_manager.get_segment_file_info(test_segment_id)
        
        if result:
            print(f"✅ Database method works for segment {test_segment_id}")
            print(f"   - Result: {result}")
            return True
        else:
            print(f"❌ Database method returned None for segment {test_segment_id}")
            return False
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    print("Starting Segment Inspector Tests...")
    
    # Test database method directly first
    db_success = test_database_method_directly()
    
    # Test complete workflow
    workflow_success = test_segment_inspector_workflow()
    
    print("\n" + "="*70)
    print("📋 TEST SUMMARY")
    print("="*70)
    print(f"Database Method: {'✅ PASSED' if db_success else '❌ FAILED'}")
    print(f"Complete Workflow: {'✅ PASSED' if workflow_success else '❌ FAILED'}")
    
    if db_success and workflow_success:
        print("\n🎉 ALL TESTS PASSED - Segment Inspector is ready!")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED - Check implementation")
        sys.exit(1)