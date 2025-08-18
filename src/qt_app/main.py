#!/usr/bin/env python3
"""
Battery Data Analyzer - Qt Desktop Application

Main entry point for the Qt-based desktop application.
Provides reliable, native UI for battery data analysis.
"""

import sys
import argparse
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QIcon

# Add src directory to path for imports
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from qt_app.main_window import MainWindow


def setup_application():
    """Setup QApplication with proper configuration."""
    app = QApplication(sys.argv)
    
    # Application metadata
    app.setApplicationName("Battery Data Analyzer")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("Battery Research")
    app.setOrganizationDomain("battery-analyzer.local")
    
    # Enable high DPI support
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    return app


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(description="Battery Data Analyzer - Qt Application")
    parser.add_argument("--data-dir", type=Path, default="data",
                       help="Data directory (default: data)")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Setup Qt application
    app = setup_application()
    
    # Create main window
    main_window = MainWindow(data_dir=args.data_dir, debug=args.debug)
    main_window.show()
    
    # Start event loop
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())