#!/usr/bin/env python3
"""
Electrochemical Analysis Suite - Panel Web Interface

Launch the Panel web application for electrochemical data analysis.
Modern, reliable web interface with Bokeh plotting.

Usage:
  Command Line: python echem_web.py
  PyCharm IDE:  Run this file directly or use run_panel_app.py
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
    
    # Import config system
    from src_clean.core.config import get_config, get_web_config
    
    # Parse command line arguments for port
    import argparse
    parser = argparse.ArgumentParser(description='Launch Panel web application')
    
    # Get default port from config
    _, default_port, _ = get_web_config()
    parser.add_argument('--port', type=int, default=default_port, help=f'Port to run server on (default: {default_port})')
    args = parser.parse_args()
    
    port = args.port

    # Configure Panel
    pn.extension('tabulator', 'modal', 'filedropper')
    
    # Create the application
    app = ElectrochemicalApp()

    print("🔬 Electrochemical Analysis Suite - Panel Web Interface")
    print("=" * 60)
    print("Starting Panel web server...")
    print()
    print("Features:")
    print("  ✅ Cell management (create, select, delete)")
    print("  ✅ File upload and processing (.par + .par.csv)")
    print("  ✅ HoloViews plotting with proper decimate")
    print("  ✅ Interactive data preview tables")
    print("  ✅ Real-time status updates")
    print()
    print(f"Access the web interface at: http://localhost:{port}")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)

    # Serve the application with correct parameters
    try:
        # Method 1: Using pn.serve for PyCharm compatibility
        pn.serve(
            app.servable(),
            port=port,
            show=True,
            autoreload=True,
            title="Electrochemical Analysis Suite"
        )
    except Exception as e:
        print(f"Error starting server with pn.serve: {e}")
        print("Trying alternative method...")

        # Method 2: Alternative approach
        app.servable().show(port=port)

def run_in_jupyter():
    """Alternative entry point for Jupyter/PyCharm environments."""
    pn.extension('tabulator', 'modal', 'filedropper')
    app = ElectrochemicalApp()
    return app.servable()

if __name__ == "__main__":
    main()