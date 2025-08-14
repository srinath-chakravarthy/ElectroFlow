#!/usr/bin/env python3
"""
Quick 1-hour battery data analysis script.

Usage:
    python battery_script.py single_file.par
    python battery_script.py file1.par file2.par file3.par
"""

import sys
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import List

# Import the fixed modules
from src.core.data_models import DataFile, DataFileGroup, TechniqueType, SignalType
from src.core.parsers import parse_par_file


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


def plot_data(data, title: str, file_paths: List[Path]) -> None:
    """Create plots for the data."""
    # Get the dataframe
    if isinstance(data, DataFile):
        df = data.full_data.to_pandas()
        subtitle = f"File: {data.file_path.name}"
    else:  # DataFileGroup
        df = data.get_combined_data().to_pandas()
        subtitle = f"Files: {', '.join([fp.name for fp in file_paths])}"

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
    plt.show()

    # Print data summary
    print(f"\n=== DATA SUMMARY ===")
    print(f"Data points: {len(df):,}")
    if 'Elapsed Time(s)' in df.columns:
        print(f"Duration: {df['Elapsed Time(s)'].max():.1f} seconds")
    if 'E(V)' in df.columns:
        print(f"Voltage range: {df['E(V)'].min():.3f} to {df['E(V)'].max():.3f} V")
    if 'I(A)' in df.columns:
        print(f"Current range: {df['I(A)'].min():.6f} to {df['I(A)'].max():.6f} A")


def main():
    """Main script function."""
    if len(sys.argv) < 2:
        print("Usage: python battery_script.py file1.par [file2.par ...]")
        sys.exit(1)

    # Get file paths
    file_paths = [Path(arg) for arg in sys.argv[1:]]

    # Validate files exist
    for file_path in file_paths:
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            sys.exit(1)
        if file_path.suffix.lower() != '.par':
            print(f"Error: Not a .par file: {file_path}")
            sys.exit(1)

    try:
        if len(file_paths) == 1:
            # Single file
            print("=== SINGLE FILE ANALYSIS ===")
            data_file = parse_single_file(file_paths[0])
            plot_data(data_file, "Single File Analysis", file_paths)

        else:
            # Multiple files - merge them
            print("=== MULTI-FILE ANALYSIS ===")
            file_group = merge_files(file_paths)
            plot_data(file_group, "Merged Files Analysis", file_paths)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n=== ANALYSIS COMPLETE ===")


if __name__ == "__main__":
    main()