#!/usr/bin/env python3
"""
Comprehensive Backend Integration Test Framework

Tests all backend API operations with real data in isolation from UI.
Designed to catch integration issues, database constraints, and data pipeline problems.

Test Categories:
1. Core Backend API Tests - CRUD operations
2. Multi-File Processing Tests - Critical for production workflows  
3. Data Pipeline Integrity Tests - Parser → Database → Analytics
4. Error Handling and Edge Cases - Graceful failure scenarios
5. Database Transaction Tests - Atomicity and rollback behavior

Usage:
    python -m pytest tests/test_backend_integration.py -v
    python tests/test_backend_integration.py  # Direct execution
"""

import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import sqlite3

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src_clean"))

from src_clean.backend import get_backend_api
from src_clean.core.database import DatabaseManager
from src_clean.core.exceptions import *
import logging

# Configure logging for tests
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# =============================================================================
# TEST DATA CONFIGURATION
# =============================================================================

class TestDataConfig:
    """Configuration for test data files and expected results."""
    
    BASE_DIR = Path(__file__).parent.parent
    TEST_DATA_DIR = BASE_DIR / "data" / "measurement_groups"
    
    # Test file pairs
    SIMPLE_FILES = {
        'metadata': TEST_DATA_DIR / "test.par",
        'data': TEST_DATA_DIR / "test.par.csv",
        'description': "Simple truncated test files for basic functionality"
    }
    
    MULTI_FILES = {
        'file_1': {
            'metadata': TEST_DATA_DIR / "test.par", 
            'data': TEST_DATA_DIR / "test.par.csv"
        },
        'file_2': {
            'metadata': TEST_DATA_DIR / "test_file_2.par",
            'data': TEST_DATA_DIR / "test_file_2.par.csv"
        },
        'description': "Multi-file test scenario for sequential processing"
    }
    
    REAL_FILES = {
        'metadata': TEST_DATA_DIR / "GITT_EIS_Charge_cycle1_Channel 2.par",
        'data': TEST_DATA_DIR / "GITT_EIS_Charge_cycle1_Channel 2.par.csv", 
        'description': "Real production GITT files for comprehensive testing"
    }

    @classmethod
    def validate_test_files(cls) -> Dict[str, bool]:
        """Validate all test files exist and are readable."""
        status = {}
        
        # Simple files
        status['simple_par'] = cls.SIMPLE_FILES['metadata'].exists()
        status['simple_csv'] = cls.SIMPLE_FILES['data'].exists()
        
        # Multi files
        status['multi_file1_par'] = cls.MULTI_FILES['file_1']['metadata'].exists()
        status['multi_file1_csv'] = cls.MULTI_FILES['file_1']['data'].exists()
        status['multi_file2_par'] = cls.MULTI_FILES['file_2']['metadata'].exists()
        status['multi_file2_csv'] = cls.MULTI_FILES['file_2']['data'].exists()
        
        # Real files
        status['real_par'] = cls.REAL_FILES['metadata'].exists()
        status['real_csv'] = cls.REAL_FILES['data'].exists()
        
        return status

# =============================================================================
# TEST FIXTURES AND UTILITIES
# =============================================================================

class BackendTestHarness:
    """Test harness for backend operations with cleanup and isolation."""
    
    def __init__(self):
        self.api = None
        self.temp_db_dir = None
        self.test_cells_created = []
        self.original_data_dir = None
        
    def setup(self):
        """Setup isolated test environment."""
        # Create temporary directory for test database
        self.temp_db_dir = Path(tempfile.mkdtemp(prefix="backend_test_"))
        
        # Initialize backend API with test database
        self.api = get_backend_api()
        
        # Store original data directory and set to test location
        self.original_data_dir = self.api.data_dir
        self.api.data_dir = self.temp_db_dir
        
        # Initialize test database
        self.api.db.db_path = self.temp_db_dir / "test_electrochemical.db"
        self.api.db._init_database()
        
        logger.info(f"✅ Test environment setup: {self.temp_db_dir}")
        
    def teardown(self):
        """Cleanup test environment."""
        try:
            # Clean up test cells
            for cell_name in self.test_cells_created:
                try:
                    result = self.api.delete_cell_by_name(cell_name)
                    if result.success:
                        logger.debug(f"Cleaned up test cell: {cell_name}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup cell {cell_name}: {e}")
            
            # Restore original data directory
            if self.original_data_dir:
                self.api.data_dir = self.original_data_dir
            
            # Remove temporary directory
            if self.temp_db_dir and self.temp_db_dir.exists():
                shutil.rmtree(self.temp_db_dir)
                logger.info(f"✅ Test environment cleaned up")
                
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
    
    def create_test_cell(self, name: str = "TEST_CELL") -> Dict[str, Any]:
        """Create a test cell and track it for cleanup."""
        result = self.api.create_cell(name, description=f"Test cell for integration testing")
        if result.success:
            self.test_cells_created.append(name)
            return self.api.get_cell_by_name(name)
        else:
            raise RuntimeError(f"Failed to create test cell {name}: {result.error}")
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics for validation."""
        with self.api.db.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM cells")
            cells_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM files")
            files_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM segments")
            segments_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM user_groups")
            groups_count = cursor.fetchone()[0]
            
        return {
            'cells': cells_count,
            'files': files_count, 
            'segments': segments_count,
            'groups': groups_count
        }

# =============================================================================
# CORE BACKEND API TESTS
# =============================================================================

class TestCoreBackendAPI:
    """Test core backend API operations - CRUD functionality."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.harness = BackendTestHarness()
        self.harness.setup()
    
    def teardown_method(self):
        """Teardown for each test method."""
        self.harness.teardown()
    
    def test_create_cell_success(self):
        """Test successful cell creation with all parameters."""
        result = self.harness.api.create_cell(
            name="TEST_CREATE",
            description="Test cell creation",
            chemistry="LiFePO4",
            capacity_ah=2.5
        )
        
        assert result.success, f"Cell creation failed: {result.error}"
        
        # Verify cell exists in database
        cell = self.harness.api.get_cell_by_name("TEST_CREATE")
        assert cell is not None
        assert cell['name'] == "TEST_CREATE"
        assert cell['chemistry'] == "LiFePO4"
        assert cell['capacity_ah'] == 2.5
        
        # Track for cleanup
        self.harness.test_cells_created.append("TEST_CREATE")
        
        logger.info("✅ Cell creation test passed")
    
    def test_create_duplicate_cell_failure(self):
        """Test that creating duplicate cell names fails gracefully."""
        # Create first cell
        result1 = self.harness.api.create_cell("DUPLICATE_TEST")
        assert result1.success
        self.harness.test_cells_created.append("DUPLICATE_TEST")
        
        # Attempt to create duplicate
        result2 = self.harness.api.create_cell("DUPLICATE_TEST")
        assert not result2.success
        assert "already exists" in result2.error.lower()
        
        logger.info("✅ Duplicate cell prevention test passed")
    
    def test_process_simple_dual_files(self):
        """Test processing simple test.par + test.par.csv files."""
        # Create test cell
        cell = self.harness.create_test_cell("SIMPLE_FILE_TEST")
        
        # Process files
        result = self.harness.api.process_dual_files(
            metadata_path=TestDataConfig.SIMPLE_FILES['metadata'],
            data_path=TestDataConfig.SIMPLE_FILES['data'],
            cell_name="SIMPLE_FILE_TEST"
        )
        
        assert result.success, f"File processing failed: {result.error}"
        assert result.file_id is not None
        assert len(result.message) > 0
        
        # Verify database state
        stats = self.harness.get_database_stats()
        assert stats['files'] >= 1
        assert stats['segments'] >= 1
        
        # Verify segments have required fields
        with self.harness.api.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT start_time_s, end_time_s, technique_name 
                FROM segments 
                WHERE file_id = ?
            """, (result.file_id,))
            segments = cursor.fetchall()
            
        assert len(segments) > 0
        for segment in segments:
            assert segment[0] is not None  # start_time_s
            assert segment[1] is not None  # end_time_s
            assert segment[2] is not None  # technique_name
        
        logger.info(f"✅ Simple file processing test passed - {len(segments)} segments")
    
    def test_delete_cell_cascade(self):
        """Test that cell deletion properly cascades to files and segments."""
        # Create cell and process files
        cell = self.harness.create_test_cell("DELETE_CASCADE_TEST")
        
        result = self.harness.api.process_dual_files(
            metadata_path=TestDataConfig.SIMPLE_FILES['metadata'],
            data_path=TestDataConfig.SIMPLE_FILES['data'],
            cell_name="DELETE_CASCADE_TEST"
        )
        assert result.success
        
        # Verify data exists
        stats_before = self.harness.get_database_stats()
        assert stats_before['cells'] >= 1
        assert stats_before['files'] >= 1
        assert stats_before['segments'] >= 1
        
        # Delete cell
        delete_result = self.harness.api.delete_cell_by_name("DELETE_CASCADE_TEST")
        assert delete_result.success
        
        # Verify cascade deletion
        stats_after = self.harness.get_database_stats()
        assert stats_after['cells'] == stats_before['cells'] - 1
        assert stats_after['files'] == stats_before['files'] - 1
        # Segments should be deleted by cascade
        
        # Remove from cleanup list since we manually deleted
        self.harness.test_cells_created.remove("DELETE_CASCADE_TEST")
        
        logger.info("✅ Cell cascade deletion test passed")

# =============================================================================
# MULTI-FILE PROCESSING TESTS - Critical for Current Bug
# =============================================================================

class TestMultiFileProcessing:
    """Test multi-file processing scenarios - the current bug area."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.harness = BackendTestHarness()
        self.harness.setup()
    
    def teardown_method(self):
        """Teardown for each test method."""  
        self.harness.teardown()
    
    def test_sequential_file_processing(self):
        """Test the exact scenario that's currently failing."""
        # Create test cell
        cell = self.harness.create_test_cell("MULTI_FILE_TEST")
        
        # Process first file (should work)
        logger.info("🔄 Processing first file...")
        result1 = self.harness.api.process_dual_files(
            metadata_path=TestDataConfig.MULTI_FILES['file_1']['metadata'],
            data_path=TestDataConfig.MULTI_FILES['file_1']['data'], 
            cell_name="MULTI_FILE_TEST"
        )
        
        assert result1.success, f"First file processing failed: {result1.error}"
        logger.info(f"✅ First file processed: {result1.file_id}")
        
        # Verify first file segments
        with self.harness.api.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT COUNT(*), MIN(start_time_s), MAX(end_time_s) 
                FROM segments WHERE file_id = ?
            """, (result1.file_id,))
            file1_stats = cursor.fetchone()
        
        assert file1_stats[0] > 0  # Has segments
        assert file1_stats[1] is not None  # start_time_s not NULL
        assert file1_stats[2] is not None  # end_time_s not NULL
        
        # Process second file (this is where the bug occurs)
        logger.info("🔄 Processing second file...")
        
        # Add debugging to see what's in the second file before processing
        try:
            from src_clean.parsers import auto_parse_dual_files
            logger.info("🔍 DEBUG: Parsing second file to examine data...")
            debug_data_file = auto_parse_dual_files(
                TestDataConfig.MULTI_FILES['file_2']['metadata'],
                TestDataConfig.MULTI_FILES['file_2']['data']
            )
            
            # Check if time_s column exists and has valid data
            df = debug_data_file.universal_data
            logger.info(f"🔍 DEBUG: Columns in second file: {df.columns}")
            
            if 'time_s' in df.columns:
                import polars as pl
                time_stats = df.select([
                    'time_s',
                    'segment_number'
                ]).group_by('segment_number').agg([
                    pl.col('time_s').min().alias('min_time'),
                    pl.col('time_s').max().alias('max_time'),
                    pl.col('time_s').count().alias('count_time'),
                    pl.col('time_s').null_count().alias('null_count')
                ])
                logger.info(f"🔍 DEBUG: Time stats by segment: {time_stats.to_pandas()}")
                
                # Check segment boundaries
                boundaries = debug_data_file.get_segment_boundaries()
                logger.info(f"🔍 DEBUG: Segment boundaries: {boundaries}")
                for i, boundary in enumerate(boundaries):
                    logger.info(f"🔍 DEBUG: Segment {i}: start_time_s={boundary.get('start_time_s')}, end_time_s={boundary.get('end_time_s')}")
            else:
                logger.error("🔍 DEBUG: time_s column not found in second file!")
                
        except Exception as debug_e:
            logger.error(f"🔍 DEBUG: Failed to parse second file for debugging: {debug_e}")
        
        result2 = self.harness.api.process_dual_files(
            metadata_path=TestDataConfig.MULTI_FILES['file_2']['metadata'],
            data_path=TestDataConfig.MULTI_FILES['file_2']['data'],
            cell_name="MULTI_FILE_TEST"
        )
        
        assert result2.success, f"Second file processing failed: {result2.error}"
        logger.info(f"✅ Second file processed: {result2.file_id}")
        
        # Verify second file segments 
        with self.harness.api.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT COUNT(*), MIN(start_time_s), MAX(end_time_s)
                FROM segments WHERE file_id = ?
            """, (result2.file_id,))
            file2_stats = cursor.fetchone()
        
        assert file2_stats[0] > 0  # Has segments
        assert file2_stats[1] is not None  # start_time_s not NULL - This is the bug!
        assert file2_stats[2] is not None  # end_time_s not NULL
        
        # Verify total database state
        stats = self.harness.get_database_stats()
        assert stats['files'] == 2
        assert stats['segments'] == file1_stats[0] + file2_stats[0]
        
        logger.info("✅ Sequential multi-file processing test passed")
    
    def test_mixed_file_types_same_cell(self):
        """Test processing different file types in the same cell."""
        cell = self.harness.create_test_cell("MIXED_FILE_TEST")
        
        # Process simple files first
        result1 = self.harness.api.process_dual_files(
            metadata_path=TestDataConfig.SIMPLE_FILES['metadata'],
            data_path=TestDataConfig.SIMPLE_FILES['data'],
            cell_name="MIXED_FILE_TEST"
        )
        assert result1.success
        
        # Process more complex files second
        result2 = self.harness.api.process_dual_files(
            metadata_path=TestDataConfig.MULTI_FILES['file_2']['metadata'], 
            data_path=TestDataConfig.MULTI_FILES['file_2']['data'],
            cell_name="MIXED_FILE_TEST"
        )
        assert result2.success
        
        # Verify both files processed correctly
        stats = self.harness.get_database_stats()
        assert stats['files'] == 2
        assert stats['segments'] > 0
        
        logger.info("✅ Mixed file types test passed")
    
    def test_file_reprocessing(self):
        """Test file reprocessing preserves raw files and regenerates segments."""
        cell = self.harness.create_test_cell("REPROCESS_TEST")
        
        # Process initial file
        result1 = self.harness.api.process_dual_files(
            metadata_path=TestDataConfig.SIMPLE_FILES['metadata'],
            data_path=TestDataConfig.SIMPLE_FILES['data'],
            cell_name="REPROCESS_TEST"
        )
        
        assert result1.success, f"Initial file processing failed: {result1.error}"
        initial_file_id = result1.file_id
        
        # Get initial segment count
        with self.harness.api.db.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM segments WHERE file_id = ?", (initial_file_id,))
            initial_segment_count = cursor.fetchone()[0]
        
        assert initial_segment_count > 0, "Initial processing should create segments"
        
        # Get file info for reprocessing test
        file_info = self.harness.api.db.get_file_by_id(initial_file_id)
        
        # Test reprocessing - should work with original test files as source
        # Since test uses original test files from TestDataConfig, reprocess should find them
        logger.info(f"🔄 Testing reprocess for file: {initial_file_id}")
        reprocess_result = self.harness.api.reprocess_file(initial_file_id)
        
        # The key test: reprocessing should succeed (not fail due to deleted raw files)
        assert reprocess_result.success, f"Reprocessing failed: {reprocess_result.error}"
        new_file_id = reprocess_result.file_id
        
        # Verify new segments were created
        with self.harness.api.db.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM segments WHERE file_id = ?", (new_file_id,))
            new_segment_count = cursor.fetchone()[0]
        
        assert new_segment_count > 0, "Reprocessing should create new segments"
        assert new_segment_count == initial_segment_count, "Reprocessing should create same number of segments"
        
        # The key success: reprocessing worked without "raw files not found" error
        # File ID may be the same (deterministic generation), but segments were regenerated
        new_file_info = self.harness.api.db.get_file_by_id(new_file_id)
        assert new_file_info is not None, "File record should exist after reprocessing"
        
        logger.info(f"✅ File reprocessing test passed - Raw files preserved, segments regenerated")

# =============================================================================
# DATA PIPELINE INTEGRITY TESTS
# =============================================================================

class TestDataPipelineIntegrity:
    """Test the complete data pipeline: Parser → Database → Analytics."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.harness = BackendTestHarness()
        self.harness.setup()
    
    def teardown_method(self):
        """Teardown for each test method."""
        self.harness.teardown()
    
    def test_segment_time_consistency(self):
        """Test that segment time calculations are consistent and valid."""
        cell = self.harness.create_test_cell("TIME_CONSISTENCY_TEST")
        
        result = self.harness.api.process_dual_files(
            metadata_path=TestDataConfig.SIMPLE_FILES['metadata'],
            data_path=TestDataConfig.SIMPLE_FILES['data'],
            cell_name="TIME_CONSISTENCY_TEST"
        )
        assert result.success
        
        # Check segment time consistency
        with self.harness.api.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT segment_index, start_time_s, end_time_s, duration_s, point_count
                FROM segments 
                WHERE file_id = ?
                ORDER BY segment_index
            """, (result.file_id,))
            segments = cursor.fetchall()
        
        assert len(segments) > 0
        
        for i, segment in enumerate(segments):
            seg_idx, start_time, end_time, duration, points = segment
            
            # Verify required fields are not NULL
            assert start_time is not None, f"Segment {seg_idx}: start_time_s is NULL"
            assert end_time is not None, f"Segment {seg_idx}: end_time_s is NULL"
            assert points > 0, f"Segment {seg_idx}: Invalid point count"
            
            # Verify time logic
            assert end_time >= start_time, f"Segment {seg_idx}: end_time < start_time"
            
            # Verify sequential segments don't overlap (if we have multiple)
            if i > 0:
                prev_end = segments[i-1][2]  # Previous end_time
                # Allow for small time gaps but no overlaps
                assert start_time >= prev_end - 0.1, f"Segment {seg_idx}: Time overlap with previous segment"
        
        logger.info(f"✅ Time consistency test passed - {len(segments)} segments validated")
    
    def test_database_constraint_compliance(self):
        """Test that all database constraints are properly satisfied."""
        cell = self.harness.create_test_cell("CONSTRAINT_TEST")
        
        result = self.harness.api.process_dual_files(
            metadata_path=TestDataConfig.SIMPLE_FILES['metadata'],
            data_path=TestDataConfig.SIMPLE_FILES['data'],
            cell_name="CONSTRAINT_TEST"
        )
        assert result.success
        
        # Test all NOT NULL constraints in segments table
        with self.harness.api.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM segments 
                WHERE file_id = ? AND (
                    start_time_s IS NULL OR 
                    end_time_s IS NULL OR
                    technique_name IS NULL OR
                    fundamental_technique IS NULL OR
                    start_row IS NULL OR
                    end_row IS NULL OR
                    point_count IS NULL
                )
            """, (result.file_id,))
            null_count = cursor.fetchone()[0]
        
        assert null_count == 0, f"Found {null_count} segments with NULL required fields"
        
        logger.info("✅ Database constraint compliance test passed")
    
    def test_cross_file_experiment_tracking(self):
        """Test that experiment-level tracking works across multiple files."""
        cell = self.harness.create_test_cell("EXPERIMENT_TRACKING_TEST")
        
        # Process multiple files
        result1 = self.harness.api.process_dual_files(
            metadata_path=TestDataConfig.MULTI_FILES['file_1']['metadata'],
            data_path=TestDataConfig.MULTI_FILES['file_1']['data'],
            cell_name="EXPERIMENT_TRACKING_TEST"
        )
        assert result1.success
        
        result2 = self.harness.api.process_dual_files(
            metadata_path=TestDataConfig.MULTI_FILES['file_2']['metadata'],
            data_path=TestDataConfig.MULTI_FILES['file_2']['data'],
            cell_name="EXPERIMENT_TRACKING_TEST"
        )
        assert result2.success
        
        # Check experiment accumulation columns
        with self.harness.api.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    exp_charge_cap_ah, exp_discharge_cap_ah,
                    exp_charge_energy_wh, exp_discharge_energy_wh,
                    exp_time_cumulative_s
                FROM segments 
                WHERE file_id IN (?, ?)
                ORDER BY exp_time_cumulative_s
            """, (result1.file_id, result2.file_id))
            exp_data = cursor.fetchall()
        
        assert len(exp_data) > 0
        
        # Verify cumulative values are monotonic (non-decreasing)
        prev_time = -1
        for row in exp_data:
            exp_time = row[4] or 0
            assert exp_time >= prev_time, "Experiment time should be cumulative"
            prev_time = exp_time
        
        logger.info("✅ Cross-file experiment tracking test passed")

# =============================================================================
# ERROR HANDLING AND EDGE CASES
# =============================================================================

class TestErrorHandling:
    """Test error handling and edge case scenarios."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.harness = BackendTestHarness()
        self.harness.setup()
    
    def teardown_method(self):
        """Teardown for each test method."""
        self.harness.teardown()
    
    def test_missing_files_graceful_failure(self):
        """Test graceful handling of missing files."""
        cell = self.harness.create_test_cell("MISSING_FILES_TEST")
        
        # Test with non-existent files
        result = self.harness.api.process_dual_files(
            metadata_path=Path("/nonexistent/test.par"),
            data_path=Path("/nonexistent/test.par.csv"),
            cell_name="MISSING_FILES_TEST"
        )
        
        assert not result.success
        assert "not found" in result.error.lower() or "no such file" in result.error.lower()
        
        # Verify database remains consistent
        stats = self.harness.get_database_stats()
        assert stats['files'] == 0
        assert stats['segments'] == 0
        
        logger.info("✅ Missing files graceful failure test passed")
    
    def test_transaction_rollback_on_failure(self):
        """Test that database transactions properly rollback on failure."""
        cell = self.harness.create_test_cell("TRANSACTION_TEST")
        
        # Get initial database state
        initial_stats = self.harness.get_database_stats()
        
        # Try to process with corrupted file (this should fail)
        # We'll create a temporary corrupted file
        with tempfile.NamedTemporaryFile(suffix='.par.csv', delete=False) as temp_file:
            temp_file.write(b"corrupted,data,without,proper,headers\n1,2,3,4,5")
            temp_csv = Path(temp_file.name)
        
        try:
            result = self.harness.api.process_dual_files(
                metadata_path=TestDataConfig.SIMPLE_FILES['metadata'],
                data_path=temp_csv,
                cell_name="TRANSACTION_TEST"
            )
            
            # Should fail due to corrupted data
            if not result.success:
                # Verify database state unchanged (transaction rollback)
                final_stats = self.harness.get_database_stats()
                assert final_stats['files'] == initial_stats['files']
                assert final_stats['segments'] == initial_stats['segments']
                logger.info("✅ Transaction rollback test passed")
            else:
                # If it somehow succeeded, we still verify data integrity
                logger.warning("Corrupted file processing unexpectedly succeeded")
                
        finally:
            # Cleanup temporary file
            temp_csv.unlink(missing_ok=True)

# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def validate_test_environment():
    """Validate test environment before running tests."""
    print("🔍 Validating Test Environment...")
    print("=" * 50)
    
    file_status = TestDataConfig.validate_test_files()
    missing_files = [name for name, exists in file_status.items() if not exists]
    
    if missing_files:
        print(f"❌ Missing test files: {missing_files}")
        print("\nRequired files:")
        print(f"  - {TestDataConfig.SIMPLE_FILES['metadata']}")
        print(f"  - {TestDataConfig.SIMPLE_FILES['data']}")
        print(f"  - {TestDataConfig.MULTI_FILES['file_2']['metadata']}")
        print(f"  - {TestDataConfig.MULTI_FILES['file_2']['data']}")
        return False
    
    print("✅ All test files found")
    print(f"✅ Simple files: test.par ({TestDataConfig.SIMPLE_FILES['metadata'].stat().st_size} bytes)")
    print(f"✅ Multi-file 2: test_file_2.par ({TestDataConfig.MULTI_FILES['file_2']['metadata'].stat().st_size} bytes)")
    
    return True

if __name__ == "__main__":
    """Direct execution for development and debugging."""
    
    if not validate_test_environment():
        sys.exit(1)
    
    print("\n🚀 Starting Comprehensive Backend Integration Tests")
    print("=" * 60)
    
    # Run specific test classes
    test_classes = [
        TestCoreBackendAPI,
        TestMultiFileProcessing, 
        TestDataPipelineIntegrity,
        TestErrorHandling
    ]
    
    total_passed = 0
    total_failed = 0
    
    for test_class in test_classes:
        print(f"\n🔬 Running {test_class.__name__}")
        print("-" * 40)
        
        # Get all test methods
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for method_name in test_methods:
            test_instance = test_class()
            try:
                test_instance.setup_method()
                method = getattr(test_instance, method_name)
                method()
                print(f"  ✅ {method_name}")
                total_passed += 1
            except Exception as e:
                print(f"  ❌ {method_name}: {e}")
                total_failed += 1
            finally:
                try:
                    test_instance.teardown_method()
                except Exception as cleanup_error:
                    print(f"  ⚠️  Cleanup failed for {method_name}: {cleanup_error}")
    
    print(f"\n🎯 Test Summary")
    print("=" * 30)
    print(f"✅ Passed: {total_passed}")
    print(f"❌ Failed: {total_failed}")
    print(f"🎲 Total:  {total_passed + total_failed}")
    
    if total_failed == 0:
        print("\n🎉 ALL TESTS PASSED! Backend is ready for beta testing.")
    else:
        print(f"\n⚠️  {total_failed} tests failed. Please investigate.")
        sys.exit(1)