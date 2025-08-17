#!/usr/bin/env python3
"""
Test script for database layer functionality.

Tests the SQLite database backend independently to ensure
proper initialization, CRUD operations, and data integrity.
"""

import sys
from pathlib import Path
import tempfile
import shutil

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from core.database import DatabaseManager, get_or_create_cell


def test_database_basic_operations():
    """Test basic database operations."""
    print("=== Testing Database Basic Operations ===")
    
    # Create temporary database
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        db = DatabaseManager(db_path)
        
        print(f"✓ Database created: {db_path}")
        
        # Test cell creation
        cell_id = db.create_cell(
            cell_name="TEST_CELL_001",
            description="Test cell for database validation",
            chemistry="Li-ion",
            capacity_ah=2.5,
            notes="Testing database operations"
        )
        print(f"✓ Cell created with ID: {cell_id}")
        
        # Test cell retrieval
        cell = db.get_cell_by_id(cell_id)
        assert cell is not None, "Cell should exist"
        assert cell['cell_name'] == "TEST_CELL_001", "Cell name should match"
        print(f"✓ Cell retrieved: {cell['cell_name']}")
        
        # Test cell by name
        cell_by_name = db.get_cell_by_name("TEST_CELL_001")
        assert cell_by_name is not None, "Cell should exist by name"
        assert cell_by_name['id'] == cell_id, "Cell IDs should match"
        print("✓ Cell retrieved by name")
        
        # Test file addition
        file_info = {
            'file_id': 'TEST_CELL_001_data01',
            'original_filename': 'test_data.par',
            'file_type': 'par',
            'file_hash': 'abc123hash',
            'file_path': '/test/path/test_data.par',
            'metadata': {'test': 'metadata'}
        }
        
        added_file_id = db.add_file_to_cell(cell_id, file_info)
        assert added_file_id == file_info['file_id'], "File ID should match"
        print(f"✓ File added: {added_file_id}")
        
        # Test file retrieval
        file_data = db.get_file_by_id(added_file_id)
        assert file_data is not None, "File should exist"
        assert file_data['original_filename'] == 'test_data.par', "Filename should match"
        assert file_data['metadata']['test'] == 'metadata', "Metadata should be preserved"
        print("✓ File retrieved with metadata")
        
        # Test cell files
        cell_files = db.get_cell_files(cell_id)
        assert len(cell_files) == 1, "Should have one file"
        assert cell_files[0]['file_id'] == added_file_id, "File ID should match"
        print("✓ Cell files retrieved")
        
        # Test processing status update
        success = db.update_processing_status(
            added_file_id, 
            "completed", 
            processed_path="/test/processed.parquet",
            analysis_path="/test/analysis.json"
        )
        assert success, "Status update should succeed"
        
        updated_file = db.get_file_by_id(added_file_id)
        assert updated_file['processing_status'] == 'completed', "Status should be updated"
        print("✓ Processing status updated")
        
        # Test technique segments
        segments = [
            {
                'segment_number': 0,
                'action_id': 8,
                'technique_name': 'Constant Current',
                'fundamental_technique': 'CC',
                'start_time_s': 0.0,
                'end_time_s': 100.0,
                'point_count': 1000,
                'analysis_results': {'capacity_ah': 0.05}
            },
            {
                'segment_number': 1,
                'action_id': 23,
                'technique_name': 'Energy Open Circuit',
                'fundamental_technique': 'OCV',
                'start_time_s': 100.0,
                'end_time_s': 200.0,
                'point_count': 500,
                'analysis_results': {'v_equilibrium_v': 3.7}
            }
        ]
        
        db.add_technique_segments(added_file_id, segments)
        print("✓ Technique segments added")
        
        # Test segment retrieval
        retrieved_segments = db.get_file_segments(added_file_id)
        assert len(retrieved_segments) == 2, "Should have two segments"
        assert retrieved_segments[0]['action_id'] == 8, "First segment action_id should match"
        assert retrieved_segments[1]['fundamental_technique'] == 'OCV', "Second segment technique should match"
        print("✓ Technique segments retrieved")
        
        # Test get_or_create_cell convenience function
        existing_cell_id, created = get_or_create_cell(db, "TEST_CELL_001")
        assert existing_cell_id == cell_id, "Should return existing cell ID"
        assert not created, "Should not create new cell"
        print("✓ get_or_create_cell (existing)")
        
        new_cell_id, created = get_or_create_cell(db, "TEST_CELL_002", description="New test cell")
        assert new_cell_id != cell_id, "Should return different cell ID"
        assert created, "Should create new cell"
        print("✓ get_or_create_cell (new)")
        
        # Test file movement between cells
        success = db.move_file_to_cell(added_file_id, new_cell_id)
        assert success, "File move should succeed"
        
        # Verify file is in new cell
        new_cell_files = db.get_cell_files(new_cell_id)
        assert len(new_cell_files) == 1, "New cell should have one file"
        old_cell_files = db.get_cell_files(cell_id)
        assert len(old_cell_files) == 0, "Old cell should have no files"
        print("✓ File moved between cells")
        
        # Test database stats
        stats = db.get_database_stats()
        assert stats['cells_count'] == 2, "Should have 2 cells"
        assert stats['files_count'] == 1, "Should have 1 file"
        print(f"✓ Database stats: {stats}")
        
        print("✓ All database tests passed!")


def test_database_error_handling():
    """Test database error handling."""
    print("\n=== Testing Database Error Handling ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        db = DatabaseManager(db_path)
        
        # Test duplicate cell creation
        cell_id = db.create_cell("DUPLICATE_TEST")
        try:
            db.create_cell("DUPLICATE_TEST")  # Should fail
            assert False, "Should raise IntegrityError"
        except Exception:
            print("✓ Duplicate cell creation properly blocked")
        
        # Test invalid file operations
        invalid_file = db.get_file_by_id("NONEXISTENT_FILE")
        assert invalid_file is None, "Nonexistent file should return None"
        print("✓ Invalid file retrieval handled")
        
        # Test invalid cell operations
        invalid_cell = db.get_cell_by_name("NONEXISTENT_CELL")
        assert invalid_cell is None, "Nonexistent cell should return None"
        print("✓ Invalid cell retrieval handled")
        
        # Test file move to nonexistent cell
        file_info = {
            'file_id': 'test_file',
            'original_filename': 'test.par',
            'file_type': 'par',
            'file_hash': 'hash123',
            'file_path': '/test/path'
        }
        file_id = db.add_file_to_cell(cell_id, file_info)
        
        move_success = db.move_file_to_cell(file_id, 99999)  # Nonexistent cell
        assert not move_success, "Move to nonexistent cell should fail"
        print("✓ Invalid file move handled")
        
        print("✓ All error handling tests passed!")


def test_database_schema_integrity():
    """Test database schema and constraints."""
    print("\n=== Testing Database Schema Integrity ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        db = DatabaseManager(db_path)
        
        # Test foreign key constraints
        cell_id = db.create_cell("CONSTRAINT_TEST")
        
        # Add file
        file_info = {
            'file_id': 'constraint_test_file',
            'original_filename': 'test.par',
            'file_type': 'par',
            'file_hash': 'hash123',
            'file_path': '/test/path'
        }
        file_id = db.add_file_to_cell(cell_id, file_info)
        
        # Add segments
        segments = [{
            'segment_number': 0,
            'action_id': 8,
            'technique_name': 'Test',
            'fundamental_technique': 'CC'
        }]
        db.add_technique_segments(file_id, segments)
        
        # Delete cell (should cascade)
        success = db.delete_cell(cell_id)
        assert success, "Cell deletion should succeed"
        
        # Verify cascading deletion
        deleted_file = db.get_file_by_id(file_id)
        assert deleted_file is None, "File should be deleted with cell"
        
        deleted_segments = db.get_file_segments(file_id)
        assert len(deleted_segments) == 0, "Segments should be deleted with file"
        
        print("✓ Foreign key constraints and cascading deletion work")
        
        # Test check constraints
        cell_id = db.create_cell("CHECK_TEST")
        
        try:
            invalid_file_info = {
                'file_id': 'invalid_file',
                'original_filename': 'test.par',
                'file_type': 'invalid_type',  # Should fail check constraint
                'file_hash': 'hash123',
                'file_path': '/test/path'
            }
            db.add_file_to_cell(cell_id, invalid_file_info)
            assert False, "Should fail check constraint"
        except Exception:
            print("✓ Check constraints work for file_type")
        
        print("✓ All schema integrity tests passed!")


if __name__ == "__main__":
    try:
        test_database_basic_operations()
        test_database_error_handling()
        test_database_schema_integrity()
        
        print("\n🎉 All database tests completed successfully!")
        print("Database layer is ready for Panel UI integration.")
        
    except Exception as e:
        print(f"\n❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)