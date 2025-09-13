#!/usr/bin/env python3
"""
Panel Web App - PyCharm Compatible Entry Point

This file provides a PyCharm-friendly way to run the Panel web application.
It handles path setup and proper Panel serving for IDE environments.
"""

import os
import sys
from pathlib import Path

# Ensure we're in the project directory
project_root = Path(__file__).parent
os.chdir(project_root)

# Add paths for imports
sys.path.insert(0, str(project_root / "src_clean"))
sys.path.insert(0, str(project_root))

def main():
    """PyCharm-compatible Panel app launcher."""
    
    # Import after path setup
    import panel as pn
    from src_clean.panel_app.main_app import ElectrochemicalApp
    
    print("🔬 Starting Panel Web Application...")
    print(f"📁 Project root: {project_root}")
    print(f"🐍 Python version: {sys.version.split()[0]}")
    
    # Configure Panel
    pn.extension('bokeh')
    
    # Create app
    app = ElectrochemicalApp()
    print("✅ Application initialized successfully")
    
    # Serve with PyCharm-compatible settings
    print("🌐 Starting Panel server on http://localhost:5006")
    print("💡 This version is optimized for PyCharm IDE")
    print("🔄 Server will start - use Ctrl+C to stop")
    print("=" * 50)
    
    try:
        # Use pn.serve which works better in PyCharm
        pn.serve(
            app.servable(),
            port=5006,
            show=True,  # Open browser
            autoreload=False,  # Disable for PyCharm stability
            title="Electrochemical Analysis Suite"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        print("💡 Try running 'python echem_web.py' instead")

def test_imports():
    """Test that all imports work correctly."""
    try:
        import panel as pn
        from src_clean.panel_app.main_app import ElectrochemicalApp
        print("✅ All imports successful")
        
        app = ElectrochemicalApp() 
        print("✅ App created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Import/creation error: {e}")
        return False

if __name__ == "__main__":
    # Quick test before starting server
    if test_imports():
        main()
    else:
        print("❌ Cannot start - import test failed")
        sys.exit(1)