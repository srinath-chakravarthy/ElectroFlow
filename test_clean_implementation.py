#!/usr/bin/env python3
"""
Quick Test - Clean Implementation

Test all major components of the clean implementation.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_backend_api():
    """Test backend API functionality."""
    print("🔧 Testing Backend API...")
    
    try:
        from src_clean.backend import get_backend_api
        api = get_backend_api()
        
        # Test database stats
        stats = api.get_database_stats()
        print(f"  ✅ Database stats: {stats['cell_count']} cells, {stats['file_count']} files")
        
        # Test cell creation
        result = api.create_cell("TEST_CELL_CLEAN", chemistry="Li_metal", notes="Test from clean implementation")
        if result.success:
            print(f"  ✅ Cell creation: {result.message}")
        else:
            print(f"  ℹ️ Cell creation: {result.error} (may already exist)")
        
        # Test cell listing
        cells = api.get_cells()
        print(f"  ✅ Cell listing: {len(cells)} cells found")
        
        # Test ActionID mappings
        mappings = api.get_actionid_mappings()
        print(f"  ✅ ActionID mappings: {len(mappings)} mappings loaded")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Backend API test failed: {e}")
        return False


def test_cli():
    """Test CLI interface."""
    print("\n💻 Testing CLI Interface...")
    
    try:
        import subprocess
        
        # Test CLI help
        result = subprocess.run(
            [sys.executable, "echem_cli.py", "--help"], 
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0 and "Electrochemical Analysis Suite CLI" in result.stdout:
            print("  ✅ CLI help working")
        else:
            print("  ❌ CLI help failed")
            return False
        
        # Test CLI stats command
        result = subprocess.run(
            [sys.executable, "echem_cli.py", "stats"], 
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0 and "cell_count" in result.stdout:
            print("  ✅ CLI stats command working")
        else:
            print("  ❌ CLI stats command failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ CLI test failed: {e}")
        return False


def test_parsers():
    """Test parser factory."""
    print("\n🔍 Testing Parser Factory...")
    
    try:
        from src_clean.parsers import get_parser_factory
        factory = get_parser_factory()
        
        # Test parser info
        parser_info = factory.get_parser_info()
        print(f"  ✅ Parser info: {list(parser_info.keys())} instruments supported")
        
        # Test VersaStudio parser creation
        versastudio_parser = factory.create_parser("VersaStudio")
        print(f"  ✅ VersaStudio parser: {versastudio_parser.get_instrument_name()}")
        
        # Test supported extensions
        extensions = factory.get_supported_extensions()
        print(f"  ✅ Supported extensions: {extensions}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Parser test failed: {e}")
        return False


def test_database():
    """Test database functionality."""
    print("\n🗄️ Testing Database...")
    
    try:
        from src_clean.core import DatabaseManager
        
        # Test database initialization
        db = DatabaseManager(Path("data_clean/test_db.db"))
        print("  ✅ Database initialization successful")
        
        # Test cell creation
        cell_id = db.create_cell("TEST_DB_CELL", chemistry="Li_ion")
        print(f"  ✅ Cell creation: ID {cell_id}")
        
        # Test cell retrieval
        cell = db.get_cell_by_id(cell_id)
        if cell:
            print(f"  ✅ Cell retrieval: {cell['name']}")
        
        # Test stats
        stats = db.get_database_stats()
        print(f"  ✅ Database stats: {stats['cell_count']} cells")
        
        # Cleanup test database
        Path("data_clean/test_db.db").unlink(missing_ok=True)
        
        return True
        
    except Exception as e:
        print(f"  ❌ Database test failed: {e}")
        return False


def test_data_models():
    """Test data models."""
    print("\n📊 Testing Data Models...")
    
    try:
        from src_clean.core.data_models import (
            UNIVERSAL_SCHEMA, VERSASTUDIO_CSV_SCHEMA, 
            create_empty_universal_dataframe
        )
        
        # Test schemas
        print(f"  ✅ Universal schema: {len(UNIVERSAL_SCHEMA)} columns")
        print(f"  ✅ VersaStudio CSV schema: {len(VERSASTUDIO_CSV_SCHEMA)} columns")
        
        # Test empty dataframe creation
        df = create_empty_universal_dataframe()
        print(f"  ✅ Empty universal dataframe: {df.width} columns")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Data models test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Testing Clean Implementation")
    print("=" * 50)
    
    tests = [
        test_data_models,
        test_database,
        test_parsers,
        test_backend_api,
        test_cli
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! Clean implementation is working correctly.")
        print("\n🚀 Ready to use:")
        print("• CLI: python echem_cli.py --help")
        print("• Qt GUI: python echem_gui.py")
        print("• Jupyter: examples/jupyter_example.ipynb")
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())