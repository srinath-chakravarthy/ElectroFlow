#!/usr/bin/env python3
"""
Simple startup script for Battery Data Analyzer Panel UI.

This script starts the Panel application and confirms it's working.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    print("🔋 Starting Battery Data Analyzer Panel UI...")
    print("=" * 50)
    
    try:
        from ui.main_app import create_app
        
        # Create app instance
        print("📊 Initializing application...")
        app = create_app()
        print("✓ Application initialized successfully")
        
        # Print startup info
        print("\n🚀 Starting Panel server...")
        print("📍 URL: http://localhost:5007")
        print("🗂️  Data directory: data/")
        print("💾 Database: data/battery_analyzer.db")
        print("\n📋 Available tabs:")
        print("   1. Cell Management - Create and manage battery cells")
        print("   2. File Association - Upload .par and .par.csv files") 
        print("   3. Data Processing - View data, analysis results, and plots")
        print("\n🔧 Default file browser directory: /Users/srinathchakravarthy/")
        print("\n⚡ Features:")
        print("   • SQLite database backend")
        print("   • Dual file processing (.par + .par.csv)")
        print("   • Interactive Plotly visualizations")
        print("   • Real-time processing status")
        print("   • Cell-based data organization")
        
        print("\n" + "=" * 50)
        print("🌐 Opening browser and starting server...")
        print("💡 Press Ctrl+C to stop the server")
        print("=" * 50)
        
        # Start server
        app.serve(port=5007, show=True)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()