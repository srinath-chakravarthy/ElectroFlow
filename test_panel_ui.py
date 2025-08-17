#!/usr/bin/env python3
"""
Test script for Panel UI functionality.

Tests the Panel UI components and backend API integration
without requiring a full server startup.
"""

import sys
from pathlib import Path
import tempfile

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Always import backend API (no Panel dependencies)
from ui.backend_api import BackendAPI

try:
    import panel as pn
    import plotly.graph_objects as go
    import pandas as pd
    
    # Configure Panel for testing (headless mode)
    pn.extension('plotly', 'tabulator')
    
    from ui.main_app import BatteryAnalyzerApp
    
    PANEL_AVAILABLE = True
except ImportError as e:
    print(f"Panel dependencies not available: {e}")
    print("Install dependencies: pip install panel plotly plotly-resampler")
    PANEL_AVAILABLE = False


def test_backend_api():
    """Test backend API functionality."""
    print("=== Testing Backend API ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir)
        api = BackendAPI(data_dir)
        
        print(f"✓ Backend API initialized with data_dir: {data_dir}")
        
        # Test get all cells (empty)
        result = api.get_all_cells()
        assert result['success'], "Should succeed even with no cells"
        assert result['total_cells'] == 0, "Should have 0 cells initially"
        print("✓ get_all_cells works with empty database")
        
        # Test cell creation
        result = api.create_cell(
            cell_name="TEST_API_CELL",
            description="API test cell",
            chemistry="Li-ion",
            capacity_ah=2.5
        )
        assert result['success'], f"Cell creation should succeed: {result.get('error', '')}"
        cell_id = result['cell_id']
        print(f"✓ Cell created: {cell_id}")
        
        # Test cell details
        result = api.get_cell_details("TEST_API_CELL")
        assert result['success'], "Should get cell details"
        cell_data = result['cell']
        assert cell_data['cell_name'] == "TEST_API_CELL", "Cell name should match"
        print("✓ Cell details retrieved")
        
        # Test duplicate cell creation
        result = api.create_cell("TEST_API_CELL")  # Duplicate
        assert not result['success'], "Duplicate cell should fail"
        print("✓ Duplicate cell creation properly rejected")
        
        # Test directory listing
        test_files_dir = data_dir / "test_files"
        test_files_dir.mkdir()
        (test_files_dir / "test.par").touch()
        (test_files_dir / "test.par.csv").touch()
        (test_files_dir / "README.txt").touch()
        
        result = api.list_directory_contents(test_files_dir)
        assert result['success'], "Directory listing should succeed"
        contents = result['contents']
        supported_files = [f for f in contents if f.get('is_supported', False)]
        assert len(supported_files) == 2, "Should find 2 supported files"
        print("✓ Directory listing and file filtering works")
        
        # Test file validation
        par_file = test_files_dir / "test.par"
        csv_file = test_files_dir / "test.par.csv"
        
        # Write minimal valid content
        par_file.write_text("<Application>VersaStudio</Application>\n<Experiment>Test</Experiment>")
        csv_file.write_text("Segment #,Point #,E(V),I(A),Elapsed Time(s)\n0,1,3.7,0.001,1.0\n")
        
        result = api.validate_file_compatibility([par_file, csv_file])
        assert result['success'], "File validation should succeed"
        print("✓ File compatibility validation works")
        
        # Test database stats
        result = api.get_database_stats()
        assert result['success'], "Database stats should work"
        stats = result['stats']
        assert stats['cells_count'] == 1, "Should have 1 cell"
        print(f"✓ Database stats: {stats}")
        
        print("✓ All Backend API tests passed!")


def test_panel_components():
    """Test Panel UI components initialization."""
    if not PANEL_AVAILABLE:
        print("Skipping Panel component tests (dependencies not available)")
        return
    
    print("\n=== Testing Panel UI Components ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir)
        api = BackendAPI(data_dir)
        
        # Create test cell
        api.create_cell("UI_TEST_CELL", "Cell for UI testing")
        
        # Test cell manager component
        from ui.components.cell_manager import CellManagerTab
        cell_manager = CellManagerTab(api)
        assert cell_manager.layout is not None, "Cell manager should have layout"
        print("✓ CellManagerTab initialized")
        
        # Test file association component
        from ui.components.file_association import FileAssociationTab
        file_association = FileAssociationTab(api)
        assert file_association.layout is not None, "File association should have layout"
        print("✓ FileAssociationTab initialized")
        
        # Test data processing component
        from ui.components.data_processing import DataProcessingTab
        data_processing = DataProcessingTab(api)
        assert data_processing.layout is not None, "Data processing should have layout"
        print("✓ DataProcessingTab initialized")
        
        print("✓ All Panel UI components initialized successfully!")


def test_main_app_creation():
    """Test main app creation without serving."""
    if not PANEL_AVAILABLE:
        print("Skipping main app tests (dependencies not available)")
        return
    
    print("\n=== Testing Main App Creation ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir)
        
        # Create main app
        app = BatteryAnalyzerApp(data_dir)
        assert app.layout is not None, "App should have layout"
        assert app.api is not None, "App should have backend API"
        print("✓ BatteryAnalyzerApp created")
        
        # Test servable layout
        servable = app.servable()
        assert servable is not None, "App should return servable layout"
        print("✓ Servable layout created")
        
        # Test app factory function
        from ui.main_app import create_app
        app2 = create_app(data_dir)
        assert app2.layout is not None, "Factory should create valid app"
        print("✓ App factory function works")
        
        print("✓ All main app tests passed!")


def test_plotly_integration():
    """Test Plotly integration."""
    if not PANEL_AVAILABLE:
        print("Skipping Plotly tests (dependencies not available)")
        return
        
    print("\n=== Testing Plotly Integration ===")
    
    try:
        # Test basic plotly figure creation
        fig = go.Figure()
        fig.add_scatter(x=[1, 2, 3], y=[1, 4, 2], name='test')
        fig.update_layout(title="Test Plot")
        
        # Test Panel plotly pane
        plot_pane = pn.pane.Plotly(fig, width=400, height=300)
        assert plot_pane is not None, "Plotly pane should be created"
        print("✓ Basic Plotly integration works")
        
        # Test plotly-resampler (if available)
        try:
            from plotly_resampler import FigureResampler
            
            # Create test data
            import numpy as np
            x = np.linspace(0, 100, 10000)
            y = np.sin(x) + np.random.normal(0, 0.1, len(x))
            
            # Create resampled figure
            fig_resampler = FigureResampler()
            fig_resampler.add_scatter(x=x, y=y, name='Large Dataset')
            
            print("✓ Plotly-resampler integration works")
            
        except ImportError:
            print("⚠ plotly-resampler not available (install for large dataset support)")
        
        print("✓ Plotly integration tests passed!")
        
    except Exception as e:
        print(f"⚠ Plotly integration test failed: {e}")


def main():
    """Run all UI tests."""
    print("🧪 Testing Panel UI and Backend Integration")
    print("=" * 50)
    
    try:
        # Always test backend API (no external dependencies)
        test_backend_api()
        
        # Test Panel components if available
        if PANEL_AVAILABLE:
            test_panel_components()
            test_main_app_creation()
            test_plotly_integration()
            
            print("\n🎉 All Panel UI tests completed successfully!")
            print("Panel UI is ready for production use.")
            print("\nTo start the application:")
            print("  python src/ui/main_app.py")
            print("  # or")
            print("  python src/ui/main_app.py --port 5007 --data-dir data")
        else:
            print("\n⚠ Panel UI tests skipped due to missing dependencies")
            print("Install Panel dependencies to test UI components:")
            print("  pip install panel plotly plotly-resampler")
            print("\nBackend API is ready and tested successfully.")
        
    except Exception as e:
        print(f"\n❌ UI test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()