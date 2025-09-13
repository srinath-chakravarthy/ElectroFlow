#!/usr/bin/env python3
"""
Battery Data Analyzer - Command Line Interface

Simple CLI for managing cells, uploading files, and querying data without the web UI.
"""

import sys
import argparse
from pathlib import Path
import pandas as pd
import json
from typing import List, Optional, Dict, Any

# Add src directory to path for imports
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from ui.backend_api import BackendAPI
from core.database import DatabaseManager


class BatteryCLI:
    """Command line interface for battery data analyzer."""
    
    def __init__(self, data_dir: Path = None, db_path: Path = None):
        """Initialize CLI with data directory and database."""
        self.data_dir = data_dir or Path("data")
        self.db_path = db_path or (self.data_dir / "battery_analyzer.db")
        
        # Initialize backend
        self.api = BackendAPI(self.data_dir, self.db_path)
        self.db = DatabaseManager(self.db_path)
        
        print(f"🔋 Battery Data Analyzer CLI")
        print(f"📁 Data Directory: {self.data_dir}")
        print(f"💾 Database: {self.db_path}")
        print("=" * 50)
    
    def list_cells(self) -> List[Dict[str, Any]]:
        """List all cells in the database."""
        print("\n📋 Available Cells:")
        result = self.api.get_all_cells()
        
        if not result['success']:
            print(f"❌ Error: {result['error']}")
            return []
        
        cells = result['cells']
        if not cells:
            print("   No cells found. Create one with 'create-cell' command.")
            return []
        
        # Display cells in a table format
        df = pd.DataFrame(cells)
        display_columns = ['id', 'cell_name', 'description', 'chemistry', 'capacity_ah', 'file_count']
        available_columns = [col for col in display_columns if col in df.columns]
        
        print(df[available_columns].to_string(index=False))
        print(f"\n📊 Total cells: {len(cells)}")
        return cells
    
    def create_cell(self, cell_name: str, description: str = "", chemistry: str = "Li-ion", 
                   capacity_ah: Optional[float] = None, notes: str = "") -> Optional[int]:
        """Create a new cell."""
        print(f"\n🔧 Creating cell: {cell_name}")
        
        result = self.api.create_cell(
            cell_name=cell_name,
            description=description,
            chemistry=chemistry,
            capacity_ah=capacity_ah,
            notes=notes
        )
        
        if result['success']:
            print(f"✅ {result['message']}")
            print(f"   Cell ID: {result['cell_id']}")
            return result['cell_id']
        else:
            print(f"❌ Error: {result['error']}")
            return None
    
    def get_cell_by_index(self, index: int) -> Optional[Dict[str, Any]]:
        """Get cell by index (0-based)."""
        cells = self.list_cells()
        if 0 <= index < len(cells):
            return cells[index]
        else:
            print(f"❌ Invalid cell index: {index}. Available: 0-{len(cells)-1}")
            return None
    
    def upload_files(self, cell_index: int, file_paths: List[str], 
                    duplicate_handling: str = "ask") -> bool:
        """Upload files to a cell specified by index."""
        print(f"\n📤 Uploading files to cell index {cell_index}")
        
        # Get cell by index
        cell = self.get_cell_by_index(cell_index)
        if not cell:
            return False
        
        cell_name = cell['cell_name']
        print(f"   Target cell: {cell_name}")
        
        # Convert string paths to Path objects and validate
        valid_paths = []
        for file_path_str in file_paths:
            file_path = Path(file_path_str)
            if file_path.exists():
                if file_path.suffix.lower() == '.par' or str(file_path).lower().endswith('.par.csv'):
                    valid_paths.append(file_path)
                    print(f"   ✓ Valid file: {file_path.name}")
                else:
                    print(f"   ⚠️  Invalid file type: {file_path.name} (only .par and .par.csv supported)")
            else:
                print(f"   ❌ File not found: {file_path}")
        
        if not valid_paths:
            print("   No valid files to upload.")
            return False
        
        # Upload files
        print(f"\n   Uploading {len(valid_paths)} files...")
        result = self.api.add_files_to_cell(
            cell_name=cell_name,
            file_paths=valid_paths,
            upload_options={'duplicate_handling': duplicate_handling}
        )
        
        if result['success']:
            summary = result['summary']
            print(f"   ✅ Upload complete!")
            print(f"      Successful: {summary['successful_uploads']}")
            print(f"      Failed: {summary['failed_uploads']}")
            
            # Show detailed results
            if 'results' in result:
                for file_result in result['results']:
                    status = "✅" if file_result['success'] else "❌"
                    file_name = Path(file_result['file']).name
                    print(f"      {status} {file_name}")
            
            return summary['successful_uploads'] > 0
        else:
            print(f"   ❌ Upload failed: {result['error']}")
            return False
    
    def validate_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """Validate files for compatibility."""
        print(f"\n🔍 Validating {len(file_paths)} files...")
        
        # Convert to Path objects
        path_objects = [Path(p) for p in file_paths]
        
        result = self.api.validate_file_compatibility(path_objects)
        
        if result['success']:
            print("   ✅ Validation complete!")
            
            # Show individual file results
            if result['individual_files']:
                print("\n   📄 Individual Files:")
                for file_result in result['individual_files']:
                    status = "✅" if file_result['valid'] else "❌"
                    file_name = Path(file_result['file']).name
                    file_type = file_result['type']
                    print(f"      {status} {file_name} ({file_type})")
                    if not file_result['valid'] and file_result.get('error'):
                        print(f"         Error: {file_result['error']}")
            
            # Show dual file pairs
            if result['dual_pairs']:
                print("\n   🔗 Dual File Pairs:")
                for pair in result['dual_pairs']:
                    status = "✅" if pair['valid'] else "❌"
                    par_name = Path(pair['par_file']).name
                    csv_name = Path(pair['csv_file']).name
                    print(f"      {status} {par_name} + {csv_name}")
                    if pair.get('recommended'):
                        print("         (Recommended for calibrated data)")
            
            return result
        else:
            print(f"   ❌ Validation failed: {result['error']}")
            return {}
    
    def get_cell_files(self, cell_index: int) -> List[Dict[str, Any]]:
        """Get all files for a cell by index."""
        print(f"\n📁 Files for cell index {cell_index}:")
        
        # Get cell by index
        cell = self.get_cell_by_index(cell_index)
        if not cell:
            return []
        
        cell_id = cell['id']
        cell_name = cell['cell_name']
        print(f"   Cell: {cell_name}")
        
        result = self.api.get_cell_files(cell_id)
        
        if result['success']:
            files = result['files']
            if files:
                df = pd.DataFrame(files)
                display_columns = ['original_filename', 'file_type', 'processing_status', 'upload_timestamp']
                available_columns = [col for col in display_columns if col in df.columns]
                print(df[available_columns].to_string(index=False))
                print(f"\n   📊 Total files: {len(files)}")
            else:
                print("   No files found for this cell.")
            return files
        else:
            print(f"   ❌ Error: {result['error']}")
            return []
    
    def get_file_preview(self, cell_index: int, file_index: int = 0, n_rows: int = 10) -> Optional[pd.DataFrame]:
        """Get preview of processed file data."""
        print(f"\n🔍 Data preview for cell {cell_index}, file {file_index}:")
        
        # Get cell files
        files = self.get_cell_files(cell_index)
        if not files or file_index >= len(files):
            print(f"   ❌ Invalid file index: {file_index}. Available: 0-{len(files)-1}")
            return None
        
        file_info = files[file_index]
        file_id = file_info['id']
        filename = file_info['original_filename']
        
        print(f"   File: {filename}")
        
        result = self.api.get_file_data_preview(file_id, n_rows)
        
        if result['success']:
            preview_df = result['preview_data']
            stats = result['stats']
            
            print(f"\n   📊 Data Statistics:")
            print(f"      Total rows: {stats['total_rows']:,}")
            print(f"      Total columns: {stats['total_columns']}")
            print(f"      Preview rows: {stats['preview_rows']}")
            
            if stats['time_range']['min'] is not None:
                print(f"      Time range: {stats['time_range']['min']:.2f} - {stats['time_range']['max']:.2f} seconds")
            
            if stats['techniques']:
                print(f"      Techniques: {', '.join(stats['techniques'])}")
            
            print(f"\n   📋 Data Preview:")
            print(preview_df.to_string(index=False))
            
            return preview_df
        else:
            print(f"   ❌ Error: {result['error']}")
            return None
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        print("\n📊 Database Statistics:")
        
        result = self.api.get_database_stats()
        
        if result['success']:
            stats = result['stats']
            print(f"   Cells: {stats.get('cells_count', 0)}")
            print(f"   Files: {stats.get('files_count', 0)}")
            print(f"   Database size: {stats.get('db_size_bytes', 0) / 1024:.1f} KB")
            return stats
        else:
            print(f"   ❌ Error: {result['error']}")
            return {}


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Battery Data Analyzer CLI")
    parser.add_argument("--data-dir", type=Path, default="data", 
                       help="Data directory (default: data)")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List cells command
    subparsers.add_parser('list-cells', help='List all cells')
    
    # Create cell command
    create_parser = subparsers.add_parser('create-cell', help='Create a new cell')
    create_parser.add_argument('name', help='Cell name')
    create_parser.add_argument('--description', default='', help='Cell description')
    create_parser.add_argument('--chemistry', default='Li-ion', help='Battery chemistry')
    create_parser.add_argument('--capacity', type=float, help='Capacity in Ah')
    create_parser.add_argument('--notes', default='', help='Additional notes')
    
    # Upload files command
    upload_parser = subparsers.add_parser('upload', help='Upload files to a cell')
    upload_parser.add_argument('cell_index', type=int, help='Cell index (0-based)')
    upload_parser.add_argument('files', nargs='+', help='File paths to upload')
    upload_parser.add_argument('--duplicate-handling', default='ask', 
                              choices=['ask', 'replace', 'skip'],
                              help='How to handle duplicate files')
    
    # Validate files command
    validate_parser = subparsers.add_parser('validate', help='Validate files')
    validate_parser.add_argument('files', nargs='+', help='File paths to validate')
    
    # List files command
    files_parser = subparsers.add_parser('list-files', help='List files for a cell')
    files_parser.add_argument('cell_index', type=int, help='Cell index (0-based)')
    
    # Preview data command
    preview_parser = subparsers.add_parser('preview', help='Preview file data')
    preview_parser.add_argument('cell_index', type=int, help='Cell index (0-based)')
    preview_parser.add_argument('--file-index', type=int, default=0, help='File index (default: 0)')
    preview_parser.add_argument('--rows', type=int, default=10, help='Number of rows to preview')
    
    # Database stats command
    subparsers.add_parser('stats', help='Show database statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize CLI
    cli = BatteryCLI(data_dir=args.data_dir)
    
    # Execute commands
    try:
        if args.command == 'list-cells':
            cli.list_cells()
        
        elif args.command == 'create-cell':
            cli.create_cell(
                cell_name=args.name,
                description=args.description,
                chemistry=args.chemistry,
                capacity_ah=args.capacity,
                notes=args.notes
            )
        
        elif args.command == 'upload':
            cli.upload_files(
                cell_index=args.cell_index,
                file_paths=args.files,
                duplicate_handling=args.duplicate_handling
            )
        
        elif args.command == 'validate':
            cli.validate_files(args.files)
        
        elif args.command == 'list-files':
            cli.get_cell_files(args.cell_index)
        
        elif args.command == 'preview':
            cli.get_file_preview(
                cell_index=args.cell_index,
                file_index=args.file_index,
                n_rows=args.rows
            )
        
        elif args.command == 'stats':
            cli.get_database_stats()
    
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()