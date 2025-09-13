#!/usr/bin/env python3
"""
Battery Data Analyzer CLI
Command-line interface for processing battery electrochemical data.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional
import polars as pl

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from io_utils.storage import StorageManager
from core.parsers import VersaStudioParser
from analysis.analytics import FundamentalAnalytics


def upload_command(args):
    """Handle file upload command."""
    storage = StorageManager(Path(args.data_dir))
    
    # Handle multiple files
    file_paths = [Path(f) for f in args.files]
    
    for file_path in file_paths:
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            continue
        
        print(f"Uploading {file_path.name} to cell {args.cell_id}...")
        
        try:
            file_id, status = storage.upload_file(
                file_path, 
                args.cell_id, 
                user_choice=args.duplicate_action
            )
            
            if status == "uploaded":
                print(f"  ✓ Successfully uploaded as {file_id}")
            elif status == "replaced":
                print(f"  ✓ Successfully replaced existing file as {file_id}")
            elif status == "skipped":
                print(f"  - Skipped (file already exists)")
            
        except Exception as e:
            print(f"  ✗ Error uploading {file_path.name}: {e}")


def list_command(args):
    """Handle list command."""
    storage = StorageManager(Path(args.data_dir))
    
    if args.cell_id:
        # List files for specific cell
        files = storage.get_cell_files(args.cell_id)
        if not files:
            print(f"No files found for cell {args.cell_id}")
            return
        
        print(f"Files for cell {args.cell_id}:")
        print("-" * 80)
        for file_info in files:
            print(f"  {file_info['file_id']}")
            print(f"    Original: {file_info['original_filename']}")
            print(f"    Date: {file_info['timestamp']}")
            print(f"    Duration: {file_info['duration_seconds']:.1f}s")
            print(f"    Points: {file_info['point_count']}")
            print(f"    Techniques: {', '.join(file_info['techniques'])}")
            print()
    else:
        # List all cells
        cells = storage.list_cells()
        if not cells:
            print("No cells found")
            return
        
        print("Available cells:")
        print("-" * 40)
        for cell_id in sorted(cells):
            summary = storage.get_cell_summary(cell_id)
            if summary:
                files_count = summary['summary']['total_files']
                duration_hours = summary['summary']['total_duration_hours']
                print(f"  {cell_id}: {files_count} files, {duration_hours:.1f} hours total")


def analyze_command(args):
    """Handle analyze command."""
    storage = StorageManager(Path(args.data_dir))
    
    # Load file data
    data = storage.load_processed_file(args.cell_id, args.file_id)
    analysis = storage.load_analysis_results(args.cell_id, args.file_id)
    
    if data is None:
        print(f"Error: File {args.file_id} not found for cell {args.cell_id}")
        return
    
    if analysis is None:
        print(f"Error: Analysis results not found for {args.file_id}")
        return
    
    print(f"Analysis Results for {args.file_id}")
    print("=" * 60)
    
    # File summary
    file_meta = analysis['file_metadata']
    data_summary = analysis['data_summary']
    
    print(f"Original File: {file_meta['original_file']}")
    print(f"Timestamp: {file_meta['timestamp']}")
    print(f"Total Points: {data_summary['total_points']}")
    print(f"Duration: {data_summary['duration_seconds']:.1f} seconds")
    print(f"Techniques: {', '.join(data_summary['techniques'])}")
    print()
    
    # Analysis results by action
    results = analysis['analysis_results']
    if not results:
        print("No analysis results available")
        return
    
    print("Action Analysis:")
    print("-" * 40)
    
    for action_id, action_results in results.items():
        technique = action_results['technique']
        metrics = action_results['results']
        quality = action_results['quality_metrics']
        
        print(f"Action {action_id} ({technique}):")
        
        # Display relevant metrics based on technique
        if technique == 'CC':
            print(f"  Capacity: {metrics.get('capacity_ah', 0):.6f} Ah")
            print(f"  Energy: {metrics.get('energy_wh', 0):.6f} Wh")
            print(f"  Avg Voltage: {metrics.get('avg_voltage_v', 0):.3f} V")
            print(f"  Current Stability: {quality.get('current_stability', 0):.3f}")
        
        elif technique == 'REST':
            print(f"  Equilibrium Voltage: {metrics.get('v_equilibrium_v', 0):.3f} V")
            print(f"  Voltage Drop: {metrics.get('v_drop_v', 0):.3f} V")
            print(f"  Time Constant: {metrics.get('time_constant_s', 0):.1f} s")
            print(f"  R²: {quality.get('r_squared', 0):.3f}")
        
        elif technique == 'PULSE':
            print(f"  Resistance: {metrics.get('resistance_ohm', 0):.6f} Ω")
            print(f"  Voltage Drop: {metrics.get('voltage_drop_v', 0):.3f} V")
            print(f"  Duration: {metrics.get('pulse_duration_s', 0):.1f} s")
        
        elif technique == 'EIS':
            print(f"  Frequency Range: {metrics.get('frequency_min_hz', 0):.2e} - {metrics.get('frequency_max_hz', 0):.2e} Hz")
            print(f"  Series Resistance: {metrics.get('series_resistance_ohm', 0):.6f} Ω")
            print(f"  Charge Transfer R: {metrics.get('charge_transfer_resistance_ohm', 0):.6f} Ω")
        
        print(f"  Data Quality: {quality.get('data_completeness', 0):.3f}")
        print()


def info_command(args):
    """Handle info command."""
    storage = StorageManager(Path(args.data_dir))
    
    summary = storage.get_cell_summary(args.cell_id)
    if not summary:
        print(f"Cell {args.cell_id} not found")
        return
    
    print(f"Cell Information: {args.cell_id}")
    print("=" * 50)
    
    # Basic info
    print(f"Created: {summary.get('created_timestamp', 'Unknown')}")
    print(f"Last Updated: {summary.get('last_updated', 'Unknown')}")
    print()
    
    # Summary statistics
    stats = summary['summary']
    print("Summary:")
    print(f"  Total Files: {stats['total_files']}")
    print(f"  Total Data Points: {stats['total_points']:,}")
    print(f"  Total Duration: {stats['total_duration_hours']:.1f} hours")
    print(f"  Techniques Used: {', '.join(stats['techniques_used'])}")
    
    if stats['date_range']:
        print(f"  Date Range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
    
    # User metadata
    user_meta = summary.get('user_metadata', {})
    if user_meta:
        print()
        print("User Metadata:")
        for key, value in user_meta.items():
            print(f"  {key}: {value}")


def export_command(args):
    """Handle export command."""
    storage = StorageManager(Path(args.data_dir))
    
    # Load processed data
    data = storage.load_processed_file(args.cell_id, args.file_id)
    if data is None:
        print(f"Error: File {args.file_id} not found")
        return
    
    output_path = Path(args.output)
    
    if args.format == 'csv':
        # Export as CSV
        data.write_csv(output_path)
        print(f"Exported to {output_path}")
    
    elif args.format == 'parquet':
        # Copy parquet file
        source_path = storage.cells_dir / args.cell_id / "processed" / f"{args.file_id}.parquet"
        if output_path.is_dir():
            output_path = output_path / f"{args.file_id}.parquet"
        
        import shutil
        shutil.copy2(source_path, output_path)
        print(f"Exported to {output_path}")
    
    elif args.format == 'eis_csv':
        # Export EIS data only
        eis_data = data.filter(
            (pl.col('fundamental_technique') == 'GEIS') |
            (pl.col('fundamental_technique') == 'PEIS')
        )
        
        if eis_data.is_empty():
            print("No EIS data found in file")
            return
        
        # Export Relaxis-compatible format
        eis_export = eis_data.select([
            'frequency_hz',
            'impedance_real_ohm',
            'impedance_imag_ohm'
        ]).rename({
            'frequency_hz': 'Frequency(Hz)',
            'impedance_real_ohm': 'Z_Real(Ohm)',
            'impedance_imag_ohm': 'Z_Imag(Ohm)'
        })
        
        eis_export.write_csv(output_path)
        print(f"EIS data exported to {output_path}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Battery Data Analyzer - Universal electrochemical data processing"
    )
    
    parser.add_argument(
        '--data-dir', 
        default='data',
        help='Base directory for data storage (default: data)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Upload command
    upload_parser = subparsers.add_parser('upload', help='Upload data files')
    upload_parser.add_argument('cell_id', help='Cell ID for the files')
    upload_parser.add_argument('files', nargs='+', help='Files to upload')
    upload_parser.add_argument(
        '--duplicate-action', 
        choices=['replace', 'keep_both', 'skip', 'ask'],
        default='ask',
        help='Action for duplicate files (default: ask)'
    )
    
    # List command
    list_parser = subparsers.add_parser('list', help='List cells or files')
    list_parser.add_argument('cell_id', nargs='?', help='Cell ID (optional, lists all cells if omitted)')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Show analysis results')
    analyze_parser.add_argument('cell_id', help='Cell ID')
    analyze_parser.add_argument('file_id', help='File ID')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show cell information')
    info_parser.add_argument('cell_id', help='Cell ID')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export data')
    export_parser.add_argument('cell_id', help='Cell ID')
    export_parser.add_argument('file_id', help='File ID')
    export_parser.add_argument('output', help='Output file path')
    export_parser.add_argument(
        '--format',
        choices=['csv', 'parquet', 'eis_csv'],
        default='parquet',
        help='Export format (default: csv)'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    try:
        if args.command == 'upload':
            upload_command(args)
        elif args.command == 'list':
            list_command(args)
        elif args.command == 'analyze':
            analyze_command(args)
        elif args.command == 'info':
            info_command(args)
        elif args.command == 'export':
            export_command(args)
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())