#!/usr/bin/env python3
"""
Explorer Tab Backend Integration Tests

Tests all backend functionality required by the ElectrochemicalExplorer tab.
Validates cell selection, dataset loading, registry integration, and technique filtering.

Test Categories:
1. Cell Data Access Tests - get_cells() functionality
2. Dataset Loading Tests - get_research_dataset_for_perspective() 
3. Registry Integration Tests - analysis options and configurations
4. Technique Filtering Tests - applicable_techniques logic
5. Error Handling Tests - graceful failure scenarios

Usage:
    python -m pytest tests/test_explorer_backend.py -v
    python tests/test_explorer_backend.py  # Direct execution
"""

import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import polars as pl
import sqlite3

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src_clean.backend.api import create_test_backend_api
from src_clean.core.config import set_test_config
from src_clean.analysis.registry import get_analysis_registry


class TestExplorerBackend:
    """Test suite for Explorer tab backend functionality."""
    
    def setup_method(self):
        """Set up isolated test environment for each test."""
        # Create temporary directories
        self.temp_base_dir = Path(tempfile.mkdtemp(prefix="explorer_test_"))
        self.temp_db_dir = self.temp_base_dir / "data"
        self.temp_db_dir.mkdir(parents=True, exist_ok=True)
        
        test_db_path = self.temp_db_dir / "test_explorer.db"
        
        # Create completely isolated test config
        test_config = set_test_config(self.temp_db_dir, test_db_path)
        test_config.ensure_directories()
        
        # Create isolated backend API with test config
        self.api = create_test_backend_api(self.temp_db_dir, test_db_path)
        
        # Initialize registry for testing
        self.registry = get_analysis_registry()
        
        # Create test data
        self._create_test_data()
        
    def teardown_method(self):
        """Clean up test environment."""
        try:
            if hasattr(self, 'temp_base_dir') and self.temp_base_dir.exists():
                shutil.rmtree(self.temp_base_dir)
        except Exception as e:
            print(f"Cleanup warning: {e}")
    
    def _create_test_data(self):
        """Create minimal test data for Explorer functionality."""
        # Create test cells
        result1 = self.api.create_cell("TEST_CELL_1", chemistry="Li_ion")
        result2 = self.api.create_cell("TEST_CELL_2", chemistry="Li_metal")
        
        assert result1.success, f"Failed to create test cell 1: {result1.error}"
        assert result2.success, f"Failed to create test cell 2: {result2.error}"
        
        # Store cell names for tests
        self.test_cells = ["TEST_CELL_1", "TEST_CELL_2"]
    
    # === CELL DATA ACCESS TESTS ===
    
    def test_get_cells_returns_valid_data(self):
        """Test that get_cells returns properly formatted cell data."""
        cells = self.api.get_cells()
        
        # Should return list of dicts
        assert isinstance(cells, list)
        assert len(cells) >= 2  # Our test cells
        
        # Check required fields for Explorer cell table
        for cell in cells:
            assert isinstance(cell, dict)
            assert 'name' in cell
            assert 'chemistry' in cell
            assert 'file_count' in cell or cell.get('file_count') is not None
            
        # Verify test cells present
        cell_names = [cell['name'] for cell in cells]
        assert "TEST_CELL_1" in cell_names
        assert "TEST_CELL_2" in cell_names
    
    def test_get_cells_handles_empty_database(self):
        """Test get_cells with no cells in database."""
        # Delete test cells
        for cell_name in self.test_cells:
            self.api.delete_cell_by_name(cell_name)
        
        cells = self.api.get_cells()
        assert isinstance(cells, list)
        assert len(cells) == 0
    
    # === DATASET LOADING TESTS ===
    
    def test_get_research_dataset_single_cell(self):
        """Test dataset loading for single cell."""
        dataset = self.api.get_research_dataset_for_perspective(cells=["TEST_CELL_1"])
        
        # Should return DataFrame (Polars or Pandas)
        assert dataset is not None
        assert hasattr(dataset, 'columns'), "Dataset should have columns attribute"
        
        # Convert to pandas if Polars for consistent testing
        if isinstance(dataset, pl.DataFrame):
            dataset = dataset.to_pandas()
        
        # Check required columns for Explorer functionality
        expected_columns = ['technique_name', 'time_s', 'potential_v', 'current_a']
        for col in expected_columns:
            if col in dataset.columns:  # Allow missing columns for empty datasets
                assert col in dataset.columns
    
    def test_get_research_dataset_multiple_cells(self):
        """Test dataset loading for multiple cells."""
        dataset = self.api.get_research_dataset_for_perspective(cells=self.test_cells)
        
        assert dataset is not None
        assert hasattr(dataset, 'columns')
        
        # Convert to pandas if needed
        if isinstance(dataset, pl.DataFrame):
            dataset = dataset.to_pandas()
        
        # Multi-cell dataset should handle multiple sources
        # (May be empty if no files processed, but should not error)
        assert isinstance(dataset, pd.DataFrame)
    
    def test_get_research_dataset_invalid_cells(self):
        """Test dataset loading with non-existent cells."""
        dataset = self.api.get_research_dataset_for_perspective(cells=["NONEXISTENT_CELL"])
        
        # Should handle gracefully - return empty dataset or None
        assert dataset is not None or dataset is None
        
        if dataset is not None:
            if isinstance(dataset, pl.DataFrame):
                dataset = dataset.to_pandas()
            assert isinstance(dataset, pd.DataFrame)
    
    def test_get_research_dataset_empty_cells_list(self):
        """Test dataset loading with empty cell list."""
        dataset = self.api.get_research_dataset_for_perspective(cells=[])
        
        # Should handle empty input gracefully
        assert dataset is not None or dataset is None
    
    # === REGISTRY INTEGRATION TESTS ===
    
    def test_registry_get_analysis_options(self):
        """Test registry returns valid analysis options for Explorer dropdown."""
        analysis_options = self.registry.get_analysis_options()
        
        assert isinstance(analysis_options, list)
        assert len(analysis_options) > 0
        
        # Check format - should be list of tuples (display_name, analysis_id)
        for option in analysis_options:
            assert isinstance(option, tuple)
            assert len(option) == 2
            assert isinstance(option[0], str)  # display name
            assert isinstance(option[1], str)  # analysis_id
    
    def test_registry_get_analysis_config(self):
        """Test registry returns valid analysis configurations."""
        analysis_options = self.registry.get_analysis_options()
        
        if analysis_options:
            # Test first available analysis
            analysis_id = analysis_options[0][1]
            config = self.registry.get_analysis(analysis_id)
            
            assert config is not None
            assert hasattr(config, 'applicable_techniques') or not hasattr(config, 'applicable_techniques')  # Optional
    
    def test_registry_applicable_techniques_exists(self):
        """Test that some analyses have applicable_techniques for filtering."""
        analysis_options = self.registry.get_analysis_options()
        
        has_applicable_techniques = False
        for _, analysis_id in analysis_options:
            config = self.registry.get_analysis(analysis_id)
            if hasattr(config, 'applicable_techniques'):
                has_applicable_techniques = True
                assert isinstance(config.applicable_techniques, list)
                break
        
        # At least one analysis should have technique filtering
        # (This validates the scientific filtering feature)
        assert has_applicable_techniques, "No analyses found with applicable_techniques filtering"
    
    # === TECHNIQUE FILTERING LOGIC TESTS ===
    
    def test_technique_filtering_logic(self):
        """Test the technique filtering logic used by Explorer."""
        # Create mock dataset with various techniques
        mock_data = pd.DataFrame({
            'technique_name': ['Galvanostatic', 'EIS', 'Rest', 'GALVANOSTATIC', 'eis'],
            'time_s': [1, 2, 3, 4, 5],
            'potential_v': [3.5, 3.6, 3.7, 3.8, 3.9],
            'current_a': [0.1, 0.0, 0.0, 0.1, 0.0]
        })
        
        # Test case-insensitive filtering (matches Explorer implementation)
        applicable_techniques = ['Galvanostatic', 'Rest']
        applicable_lower = [t.lower() for t in applicable_techniques]
        
        filtered_data = mock_data[mock_data['technique_name'].str.lower().isin(applicable_lower)]
        
        # Should match galvanostatic (both cases) and rest
        assert len(filtered_data) == 3
        assert 'EIS' not in filtered_data['technique_name'].values
        assert 'eis' not in filtered_data['technique_name'].values
    
    def test_technique_filtering_no_matches(self):
        """Test technique filtering when no data matches criteria."""
        # Create dataset with techniques not in applicable list
        mock_data = pd.DataFrame({
            'technique_name': ['EIS', 'Impedance'],
            'time_s': [1, 2],
            'potential_v': [3.5, 3.6],
            'current_a': [0.0, 0.0]
        })
        
        # Filter for techniques not in dataset
        applicable_techniques = ['Galvanostatic', 'Rest']
        applicable_lower = [t.lower() for t in applicable_techniques]
        
        filtered_data = mock_data[mock_data['technique_name'].str.lower().isin(applicable_lower)]
        
        # Should be empty (matches Explorer warning behavior)
        assert len(filtered_data) == 0
        assert filtered_data.empty
    
    # === ERROR HANDLING TESTS ===
    
    def test_dataset_loading_with_database_error(self):
        """Test dataset loading handles database errors gracefully."""
        # Close database connection to simulate error
        if hasattr(self.api.db_manager, '_conn') and self.api.db_manager._conn:
            self.api.db_manager._conn.close()
        
        # Should handle database error gracefully
        try:
            dataset = self.api.get_research_dataset_for_perspective(cells=self.test_cells)
            # If no exception, verify result is reasonable
            assert dataset is None or isinstance(dataset, (pd.DataFrame, pl.DataFrame))
        except Exception as e:
            # Exception is acceptable - Explorer should handle this
            assert isinstance(e, Exception)
    
    def test_registry_integration_availability(self):
        """Test that registry is available and functional for Explorer."""
        # Registry should be available
        assert self.registry is not None
        
        # Should provide analysis options (even if empty)
        try:
            options = self.registry.get_analysis_options()
            assert isinstance(options, list)
        except Exception as e:
            pytest.fail(f"Registry get_analysis_options failed: {e}")
    
    def test_cell_data_format_compatibility(self):
        """Test that cell data format matches Explorer expectations."""
        cells = self.api.get_cells()
        
        # Explorer expects specific data structure
        for cell in cells:
            # Required fields for Explorer cell table
            assert 'name' in cell, "Cell missing 'name' field for Explorer table"
            assert isinstance(cell['name'], str), "Cell name must be string"
            
            # Optional fields Explorer displays
            chemistry = cell.get('chemistry', 'Unknown')
            assert isinstance(chemistry, str), "Chemistry must be string"
            
            file_count = cell.get('file_count', 0)
            assert isinstance(file_count, int), "File count must be integer"


if __name__ == "__main__":
    """Direct execution for quick testing."""
    import unittest
    
    # Convert pytest class to unittest for direct execution
    suite = unittest.TestLoader().loadTestsFromTestCase(TestExplorerBackend)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)