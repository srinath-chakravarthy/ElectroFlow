#!/usr/bin/env python3
"""
Electrochemical Analysis Suite - Panel Web Interface

Launch the Panel web application for electrochemical data analysis.
Modern, reliable web interface with Bokeh plotting.
"""

import panel as pn
import sys
from pathlib import Path

# Add src_clean to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src_clean"))

# Add project root for proper module resolution
sys.path.insert(0, str(Path(__file__).parent))

# Import with absolute imports now working
from src_clean.panel_app.main_app import ElectrochemicalApp

def main():
    """Launch the Panel web application."""
    
    # Configure Panel
    pn.extension('bokeh', template='material', theme='dark')
    
    # Create and serve the application
    app = ElectrochemicalApp()
    
    print("🔬 Electrochemical Analysis Suite - Panel Web Interface")
    print("=" * 60)
    print("Starting Panel web server...")
    print()
    print("Features:")
    print("  ✅ Cell management (create, select, delete)")
    print("  ✅ File upload and processing (.par + .par.csv)")
    print("  ✅ Reliable Bokeh plotting with technique colors")
    print("  ✅ Interactive data preview tables")
    print("  ✅ Real-time status updates")
    print()
    print("Access the web interface at: http://localhost:5006")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    # Serve the application
    app.servable().show(port=5006, autoreload=True, show=True)

if __name__ == "__main__":
    main()