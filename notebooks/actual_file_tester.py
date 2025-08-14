#!/usr/bin/env python3
"""
Quick 1-hour battery data analysis script.

Usage:
    python battery_script.py file1.par [file2.par ...]
    python battery_script.py --files file1.par file2.par --output results/
    python battery_script.py file.par --no-plot --export-csv
"""

import argparse
import sys
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import List, Optional

# Import the fixed modules
from data_models import DataFile, DataFileGroup, TechniqueType, SignalType
from parsers import parse_par_file


def parse_single_file(file_path: Path) -> DataFile:
    """Parse a single .par file."""
    print(f"Parsing {file_path.name}...")
    data_file = parse_par_file(file_path)

    print(f"✓ Success! {data_file.point_count:,} points, {data_file.duration_seconds:.1f}s")
    print(f"  Technique: {data_file.primary_technique.value}")
    print(f"  Signal: {data_file.signal_type.value}")

    return data_file


def merge_files(file_paths: List[Path]) -> DataFileGroup:
    """Parse and merge multiple .par files."""
    print(f"Parsing and merging {len(file_paths)} files...")

    # Parse all files
    data_files = []
    for file_path in file_paths:
        try:
            data_file = parse_single_file(file_path)
            data_files.append(data_file)
        except Exception as e:
            print(f"✗ Failed to parse {file_path.name}: {e}")

    if not data_files:
        raise ValueError("No files could be parsed")

    # Create file group
    group = DataFileGroup(
        group_id="merged_experiment",
        description=f"Merged data from {len(data_files)} files"
    )

    for data_file in data_files:
        group.add_data_file(data_file)

    print(f"✓ Merged successfully!")
    print(f"  Total files: {group.file_count}")
    print(f"  Total points: {group.total_points:,}")
    print(f"  Total duration: {group.total_duration:.1f}s")
    print(f"  Primary technique: {group.primary_technique.value}")

    return group


def plot_data(data, title: str, file_paths: List[Path], output_dir: Optional[Path] = None,
              show_plot: bool = True) -> None:
    """Create plots for the data."""
    # Get the dataframe
    if isinstance(data, DataFile):
        df = data.full_data.to_pandas()
        subtitle = f"File: {data.file_path.name}"
        output_prefix = data.file_path.stem
    else:  # DataFileGroup
        df = data.get_combined_data().to_pandas()
        subtitle = f"Files: {', '.join([fp.name for fp in file_paths])}"
        output_prefix = "merged_data"

    if df.empty:
        print("No data to plot")
        return

    # Sample data if too large
    if len(df) > 50000:
        df = df.sample(n=50000).sort_values('Elapsed Time(s)')
        print(f"Plotting sample of 50,000 points (total: {len(df):,})")

    # Set up the plotting style
    plt.style.use('default')
    sns.set_palette("husl")

    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle(f'{title}\n{subtitle}', fontsize=14)

    # Voltage vs Time
    if 'E(V)' in df.columns and 'Elapsed Time(s)' in df.columns:
        axes[0, 0].plot(df['Elapsed Time(s)'], df['E(V)'], alpha=0.7, linewidth=0.5)
        axes[0, 0].set_xlabel('Time (s)')
        axes[0, 0].set_ylabel('Voltage (V)')
        axes[0, 0].set_title('Voltage vs Time')
        axes[0, 0].grid(True, alpha=0.3)

    # Current vs Time
    if 'I(A)' in df.columns and 'Elapsed Time(s)' in df.columns:
        axes[0, 1].plot(df['Elapsed Time(s)'], df['I(A)'], alpha=0.7, linewidth=0.5, color='orange')
        axes[0, 1].set_xlabel('Time (s)')
        axes[0, 1].set_ylabel('Current (A)')
        axes[0, 1].set_title('Current vs Time')
        axes[0, 1].grid(True, alpha=0.3)

    # I-V Curve
    if 'E(V)' in df.columns and 'I(A)' in df.columns:
        axes[1, 0].scatter(df['E(V)'], df['I(A)'], alpha=0.5, s=0.5)
        axes[1, 0].set_xlabel('Voltage (V)')
        axes[1, 0].set_ylabel('Current (A)')
        axes[1, 0].set_title('Current vs Voltage')
        axes[1, 0].grid(True, alpha=0.3)

    # Frequency or Power plot
    if 'Frequency(Hz)' in df.columns and df['Frequency(Hz)'].notna().any():
        # EIS data - frequency plot
        freq_data = df[df['Frequency(Hz)'] > 0]
        if not freq_data.empty:
            axes[1, 1].semilogx(freq_data['Frequency(Hz)'], freq_data['Z Real'],
                                alpha=0.7, marker='o', markersize=1, linewidth=0.5)
            axes[1, 1].set_xlabel('Frequency (Hz)')
            axes[1, 1].set_ylabel('Z Real (Ω)')
            axes[1, 1].set_title('Impedance vs Frequency')
            axes[1, 1].grid(True, alpha=0.3)
        else:
            axes[1, 1].text(0.5, 0.5, 'No AC data found', ha='center', va='center')
            axes[1, 1].set_title('Impedance vs Frequency')
    else:
        # Power calculation for DC data
        if 'E(V)' in df.columns and 'I(A)' in df.columns:
            power = df['E(V)'] * df['I(A)']
            axes[1, 1].plot(df['Elapsed Time(s)'], power, alpha=0.7, linewidth=0.5, color='red')
            axes[1, 1].set_xlabel('Time (s)')
            axes[1, 1].set_ylabel('Power (W)')
            axes[1, 1].set_title('Power vs Time')
            axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()

    # Save plot if output directory specified
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        plot_path = output_dir / f"{output_prefix}_analysis.png"
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"✓ Plot saved to: {plot_path}")

    # Show plot if requested
    if show_plot:
        plt.show()
    else:
        plt.close()

    # Print data summary
    print(f"\n=== DATA SUMMARY ===")
    print(f"Data points: {len(df):,}")
    if 'Elapsed Time(s)' in df.columns:
        print(f"Duration: {df['Elapsed Time(s)'].max():.1f} seconds")
    if 'E(V)' in df.columns:
        print(f"Voltage range: {df['E(V)'].min():.3f} to {df['E(V)'].max():.3f} V")
    if 'I(A)' in df.columns:
        print(f"Current range: {df['I(A)'].min():.6f} to {df['I(A)'].max():.6f} A")


def export_data(data, output_dir: Path, export_format: str = 'parquet') -> None:
    """Export data to file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(data, DataFile):
        df = data.pruned_data  # Use pruned for storage
        output_prefix = data.file_path.stem
    else:  # DataFileGroup
        df = data.get_combined_data()
        # Prune empty columns for storage
        from data_models import prune_empty_columns
        df = prune_empty_columns(df)
        output_prefix = "merged_data"

    if export_format.lower() == 'csv':
        output_path = output_dir / f"{output_prefix}.csv"
        df.write_csv(output_path)
    elif export_format.lower() == 'parquet':
        output_path = output_dir / f"{output_prefix}.parquet"
        df.write_parquet(output_path)
    else:
        raise ValueError(f"Unsupported export format: {export_format}")

    print(f"✓ Data exported to: {output_path}")


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="Parse and analyze VersaStudio .par files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Single file analysis
    python battery_script.py data.par

    # Multiple file merge and analysis  
    python battery_script.py file1.par file2.par file3.par

    # Export data without plotting
    python battery_script.py data.par --no-plot --export-csv --output results/

    # Batch processing with custom output
    python battery_script.py *.par --output analysis/ --export-parquet
        """
    )

    # Positional arguments
    parser.add_argument(
        'files',
        nargs='+',
        type=Path,
        help='One or more .par files to analyze'
    )

    # Output options
    parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Output directory for plots and exported data'
    )

    # Plot options
    parser.add_argument(
        '--no-plot',
        action='store_true',
        help='Skip plotting (useful for batch processing)'
    )

    # Export options
    parser.add_argument(
        '--export-csv',
        action='store_true',
        help='Export data as CSV file'
    )

    parser.add_argument(
        '--export-parquet',
        action='store_true',
        help='Export data as Parquet file (default if --export used)'
    )

    # Analysis options
    parser.add_argument(
        '--sample-size',
        type=int,
        default=50000,
        help='Maximum number of points to plot (default: 50000)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )

    return parser


def main():
    """Main script function."""
    parser = create_parser()
    args = parser.parse_args()

    # Validate files exist and are .par files
    for file_path in args.files:
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            sys.exit(1)
        if file_path.suffix.lower() != '.par':
            print(f"Error: Not a .par file: {file_path}")
            sys.exit(1)

    try:
        if len(args.files) == 1:
            # Single file analysis
            print("=== SINGLE FILE ANALYSIS ===")
            data_file = parse_single_file(args.files[0])

            # Plot if requested
            if not args.no_plot:
                plot_data(
                    data_file,
                    "Single File Analysis",
                    args.files,
                    output_dir=args.output,
                    show_plot=not args.output  # Don't show if saving to file
                )

            # Export if requested
            if args.export_csv or args.export_parquet or args.output:
                if not args.output:
                    args.output = Path('.')

                if args.export_csv:
                    export_data(data_file, args.output, 'csv')
                else:
                    export_data(data_file, args.output, 'parquet')

        else:
            # Multiple files - merge them
            print("=== MULTI-FILE ANALYSIS ===")
            file_group = merge_files(args.files)

            # Plot if requested
            if not args.no_plot:
                plot_data(
                    file_group,
                    "Merged Files Analysis",
                    args.files,
                    output_dir=args.output,
                    show_plot=not args.output
                )

            # Export if requested
            if args.export_csv or args.export_parquet or args.output:
                if not args.output:
                    args.output = Path('.')

                if args.export_csv:
                    export_data(file_group, args.output, 'csv')
                else:
                    export_data(file_group, args.output, 'parquet')

    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    print("\n=== ANALYSIS COMPLETE ===")


if __name__ == "__main__":
    main()