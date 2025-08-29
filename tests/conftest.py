"""
Pytest Configuration for Backend Integration Tests

Provides shared fixtures, configuration, and utilities for all tests.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import logging
import sys

# Add project root to path for all tests
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src_clean"))

from src_clean.backend import get_backend_api


# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Reduce noise from some loggers during testing
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)


@pytest.fixture(scope="session")
def test_data_config():
    """Configuration for test data files."""
    from tests.test_backend_integration import TestDataConfig
    return TestDataConfig


@pytest.fixture(scope="function") 
def backend_harness():
    """Isolated backend test harness with automatic cleanup."""
    from tests.test_backend_integration import BackendTestHarness
    
    harness = BackendTestHarness()
    harness.setup()
    
    yield harness
    
    harness.teardown()


@pytest.fixture(scope="function")
def test_cell(backend_harness):
    """Create a test cell and return it."""
    return backend_harness.create_test_cell("PYTEST_TEST_CELL")


@pytest.fixture(scope="session", autouse=True)
def validate_test_files():
    """Automatically validate test files exist before running any tests."""
    from tests.test_backend_integration import TestDataConfig
    
    file_status = TestDataConfig.validate_test_files()
    missing_files = [name for name, exists in file_status.items() if not exists]
    
    if missing_files:
        pytest.fail(
            f"Missing required test files: {missing_files}\n"
            f"Please ensure test data files exist in {TestDataConfig.TEST_DATA_DIR}"
        )


def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (may take several seconds)"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "database: marks tests that require database operations"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Mark all tests as integration tests
        item.add_marker(pytest.mark.integration)
        
        # Mark database-related tests
        if "database" in item.name.lower() or "segment" in item.name.lower():
            item.add_marker(pytest.mark.database)
        
        # Mark potentially slow tests
        if any(keyword in item.name.lower() for keyword in ["multi", "real", "large"]):
            item.add_marker(pytest.mark.slow)


@pytest.fixture(scope="function")
def temp_directory():
    """Provide a temporary directory for tests."""
    temp_dir = Path(tempfile.mkdtemp(prefix="test_temp_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestDataValidator:
    """Utility class for validating test data."""
    
    @staticmethod
    def validate_segment_data(segments, file_id):
        """Validate segment data integrity."""
        assert len(segments) > 0, f"No segments found for file {file_id}"
        
        for i, segment in enumerate(segments):
            # Check required fields are not None
            assert segment.get('start_time_s') is not None, f"Segment {i}: start_time_s is None"
            assert segment.get('end_time_s') is not None, f"Segment {i}: end_time_s is None"
            assert segment.get('technique_name') is not None, f"Segment {i}: technique_name is None"
            
            # Check time logic
            start_time = segment['start_time_s']
            end_time = segment['end_time_s'] 
            assert end_time >= start_time, f"Segment {i}: end_time < start_time"
    
    @staticmethod
    def validate_database_consistency(api):
        """Validate overall database consistency."""
        with api.db.get_connection() as conn:
            # Check foreign key consistency
            cursor = conn.execute("""
                SELECT COUNT(*) FROM segments s 
                LEFT JOIN files f ON s.file_id = f.file_id 
                WHERE f.file_id IS NULL
            """)
            orphaned_segments = cursor.fetchone()[0]
            assert orphaned_segments == 0, f"Found {orphaned_segments} orphaned segments"


@pytest.fixture(scope="function")
def data_validator():
    """Provide data validation utilities."""
    return TestDataValidator()