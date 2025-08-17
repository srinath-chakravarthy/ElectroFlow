#!/usr/bin/env python3
"""
Universal Battery Data Analysis Script - API Testing Tool

Tests the new universal battery data processing system with direct API calls.
Perfect for debugging, validation, and development testing.

Usage:
    python actual_file_tester.py file1.par [file2.par ...]
    python actual_file_tester.py file.par --no-plot --export-csv
    python actual_file_tester.py file.par --show-analytics
"""

import argparse
import sys
from pathlib import Path
import json

# Add src to Python path
script_dir = Path(__file__).parent.absolute()
project_root = script_dir.parent if script_dir.name == 'notebooks' else script_dir
src_path = project_root / 'src'
sys.path.insert(0, str(src_path))

import matplotlib.pyplot as plt
import seaborn as sns
import polars as pl

from typing import List, Optional, Dict, Any

# Import the new universal system modules
from core.data_models import DataFile, UNIVERSAL_COLUMNS, TECHNIQUE_MAPPING
from core.parsers import VersaStudioParser
from analysis.analytics import FundamentalAnalytics


def parse_single_file(file_path: Path, enable_debug_output: bool = False) -> DataFile:
    """Parse a single .par file using the universal system."""
    print(f"Parsing {file_path.name}...")
    
    # Use VersaStudio parser directly (with optional debug output)
    parser = VersaStudioParser(debug_structural_parsing=enable_debug_output)
    
    if not parser.validate_file(file_path):
        raise ValueError(f"File validation failed: {file_path}")
    
    data_file = parser.parse(file_path)

    print(f"✓ Success! {data_file.point_count:,} points, {data_file.duration_seconds:.1f}s")
    print(f"  Timestamp: {data_file.timestamp}")
    print(f"  Schema: {data_file.universal_data.shape[1]} columns (expected: {len(UNIVERSAL_COLUMNS)})")
    
    # Show techniques found
    techniques = data_file.universal_data.get_column('fundamental_technique').unique().to_list()
    print(f"  Techniques: {techniques}")
    
    # Show file hash for integrity
    print(f"  File hash: {data_file.file_hash[:12]}...")

    return data_file


def process_multiple_files(file_paths: List[Path]) -> List[DataFile]:
    """Parse multiple .par files individually (no merging in new system)."""
    print(f"Processing {len(file_paths)} files individually...")

    # Parse all files
    data_files = []
    total_points = 0
    total_duration = 0.0
    
    for file_path in file_paths:
        try:
            data_file = parse_single_file(file_path)
            data_files.append(data_file)
            total_points += data_file.point_count
            total_duration += data_file.duration_seconds
        except Exception as e:
            print(f"✗ Failed to parse {file_path.name}: {e}")

    if not data_files:
        raise ValueError("No files could be parsed")

    print(f"✓ Processing complete!")
    print(f"  Total files: {len(data_files)}")
    print(f"  Total points: {total_points:,}")
    print(f"  Total duration: {total_duration:.1f}s")
    
    # Show technique summary across all files
    all_techniques = set()
    for data_file in data_files:
        techniques = data_file.universal_data.get_column('fundamental_technique').unique().to_list()
        all_techniques.update(techniques)
    print(f"  All techniques: {sorted(all_techniques)}")

    return data_files


def plot_data(data, title: str, file_paths: List[Path], output_dir: Optional[Path] = None,
              show_plot: bool = True) -> None:
    """Create plots for the universal schema data."""
    # Get the dataframe
    if isinstance(data, DataFile):
        df = data.universal_data.to_pandas()
        subtitle = f"File: {data.file_path.name}"
        output_prefix = data.file_path.stem
    elif isinstance(data, list):  # List of DataFiles
        # Combine data from multiple files
        dfs = [df.universal_data.to_pandas() for df in data]
        df = pl.concat([pl.from_pandas(d) for d in dfs]).to_pandas()
        subtitle = f"Files: {', '.join([fp.name for fp in file_paths])}"
        output_prefix = "multiple_files"
    else:
        print("Unsupported data type for plotting")
        return

    if df.empty:
        print("No data to plot")
        return

    # Sample data if too large
    if len(df) > 50000:
        df = df.sample(n=50000).sort_values('time_s')
        print(f"Plotting sample of 50,000 points (total: {len(df):,})")

    # Set up the plotting style
    plt.style.use('default')
    sns.set_palette("husl")

    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle(f'{title}\n{subtitle}', fontsize=14)

    # Voltage vs Time (universal schema)
    if 'potential_v' in df.columns and 'time_s' in df.columns:
        axes[0, 0].plot(df['time_s'], df['potential_v'], alpha=0.7, linewidth=0.5)
        axes[0, 0].set_xlabel('Time (s)')
        axes[0, 0].set_ylabel('Potential (V)')
        axes[0, 0].set_title('Potential vs Time')
        axes[0, 0].grid(True, alpha=0.3)

    # Current vs Time (universal schema)
    if 'current_a' in df.columns and 'time_s' in df.columns:
        axes[0, 1].plot(df['time_s'], df['current_a'], alpha=0.7, linewidth=0.5, color='orange')
        axes[0, 1].set_xlabel('Time (s)')
        axes[0, 1].set_ylabel('Current (A)')
        axes[0, 1].set_title('Current vs Time')
        axes[0, 1].grid(True, alpha=0.3)

    # I-V Curve (universal schema)
    if 'potential_v' in df.columns and 'current_a' in df.columns:
        axes[1, 0].scatter(df['potential_v'], df['current_a'], alpha=0.5, s=0.5)
        axes[1, 0].set_xlabel('Potential (V)')
        axes[1, 0].set_ylabel('Current (A)')
        axes[1, 0].set_title('Current vs Potential')
        axes[1, 0].grid(True, alpha=0.3)

    # EIS or Power plot (universal schema)
    if 'frequency_hz' in df.columns and df['frequency_hz'].notna().any():
        # EIS data - Nyquist plot
        eis_data = df[df['frequency_hz'] > 0]
        if not eis_data.empty and 'impedance_real_ohm' in df.columns:
            axes[1, 1].scatter(eis_data['impedance_real_ohm'], -eis_data['impedance_imag_ohm'],
                             alpha=0.7, s=1)
            axes[1, 1].set_xlabel('Z Real (Ω)')
            axes[1, 1].set_ylabel('-Z Imag (Ω)')
            axes[1, 1].set_title('Nyquist Plot (EIS)')
            axes[1, 1].grid(True, alpha=0.3)
            axes[1, 1].axis('equal')
        else:
            axes[1, 1].text(0.5, 0.5, 'No EIS data found', ha='center', va='center')
            axes[1, 1].set_title('Nyquist Plot (EIS)')
    else:
        # Power plot for DC data (universal schema)
        if 'power_w' in df.columns and 'time_s' in df.columns:
            axes[1, 1].plot(df['time_s'], df['power_w'], alpha=0.7, linewidth=0.5, color='red')
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

    # Print data summary (universal schema)
    print(f"\n=== DATA SUMMARY ===")
    print(f"Data points: {len(df):,}")
    if 'time_s' in df.columns:
        print(f"Duration: {df['time_s'].max():.1f} seconds")
    if 'potential_v' in df.columns:
        print(f"Potential range: {df['potential_v'].min():.3f} to {df['potential_v'].max():.3f} V")
    if 'current_a' in df.columns:
        print(f"Current range: {df['current_a'].min():.6f} to {df['current_a'].max():.6f} A")
    if 'fundamental_technique' in df.columns:
        techniques = df['fundamental_technique'].value_counts()
        print(f"Techniques: {dict(techniques)}")


def export_data(data, output_dir: Path, export_format: str = 'parquet') -> None:
    """Export universal schema data to file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(data, DataFile):
        df = data.universal_data  # Export full universal schema
        output_prefix = data.file_path.stem
    elif isinstance(data, list):  # List of DataFiles
        # Combine universal data from multiple files
        dfs = [df.universal_data for df in data]
        df = pl.concat(dfs, how="vertical_relaxed")
        output_prefix = "multiple_files"
    else:
        raise ValueError("Unsupported data type for export")

    if export_format.lower() == 'csv':
        output_path = output_dir / f"{output_prefix}.csv"
        df.write_csv(output_path)
    elif export_format.lower() == 'parquet':
        output_path = output_dir / f"{output_prefix}.parquet"
        df.write_parquet(output_path)
    else:
        raise ValueError(f"Unsupported export format: {export_format}")

    print(f"✓ Data exported to: {output_path}")
    print(f"  Format: {export_format.upper()}")
    print(f"  Columns: {len(df.columns)} (universal schema)")
    print(f"  Rows: {df.height:,}")


def analyze_file_with_analytics(data_file: DataFile, show_details: bool = True) -> Dict[str, Any]:
    """Run analytics on a parsed file and display results."""
    print(f"\n=== ANALYTICS ANALYSIS ===")
    
    # Run analytics
    analytics = FundamentalAnalytics()
    results = analytics.analyze_datafile(data_file.universal_data)
    
    if not results:
        print("No analytics results generated")
        return {}
    
    print(f"Analyzed {len(results)} actions:")
    
    for action_id, analysis_result in results.items():
        technique = analysis_result.technique
        metrics = analysis_result.results
        quality = analysis_result.quality_metrics
        
        print(f"\nAction {action_id} ({technique}):")
        
        # Display technique-specific results
        if technique == 'CC':
            print(f"  Capacity: {metrics.get('capacity_ah', 0):.6f} Ah")
            print(f"  Energy: {metrics.get('energy_wh', 0):.6f} Wh")
            print(f"  Avg Potential: {metrics.get('avg_voltage_v', 0):.3f} V")
            print(f"  Current Stability: {quality.get('current_stability', 0):.3f}")
        
        elif technique == 'REST':
            print(f"  Equilibrium Potential: {metrics.get('v_equilibrium_v', 0):.3f} V")
            print(f"  Potential Drop: {metrics.get('v_drop_v', 0):.3f} V")
            print(f"  Time Constant: {metrics.get('time_constant_s', 0):.1f} s")
            print(f"  R²: {quality.get('r_squared', 0):.3f}")
            print(f"  Fit Type: {metrics.get('fitting_type', 'unknown')}")
        
        elif technique == 'PULSE':
            print(f"  Resistance: {metrics.get('resistance_ohm', 0):.6f} Ω")
            print(f"  Potential Drop: {metrics.get('voltage_drop_v', 0):.3f} V")
            print(f"  Duration: {metrics.get('pulse_duration_s', 0):.1f} s")
            print(f"  Current Uniformity: {quality.get('current_uniformity', 0):.3f}")
        
        elif technique == 'EIS':
            print(f"  Frequency Range: {metrics.get('frequency_min_hz', 0):.2e} - {metrics.get('frequency_max_hz', 0):.2e} Hz")
            print(f"  Series Resistance: {metrics.get('series_resistance_ohm', 0):.6f} Ω")
            print(f"  Charge Transfer R: {metrics.get('charge_transfer_resistance_ohm', 0):.6f} Ω")
            print(f"  Frequency Coverage: {quality.get('frequency_coverage', 0):.1f} decades")
        
        elif technique == 'CV':
            print(f"  Potential Range: {metrics.get('voltage_range_v', 0):.3f} V")
            print(f"  Current Range: {metrics.get('current_range_a', 0):.6f} A")
            print(f"  Scan Rate: {metrics.get('scan_rate_v_per_s', 0):.3f} V/s")
            print(f"  Capacitance: {metrics.get('capacitance_f', 0):.6f} F")
        
        print(f"  Data Quality: {quality.get('data_completeness', 0):.3f}")
        print(f"  Total Points: {metrics.get('total_points', 0)}")
    
    return results


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="Universal Battery Data Analysis - API Testing Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Single file analysis with analytics
    python actual_file_tester.py data.par --show-analytics

    # Multiple file processing (individual, not merged)
    python actual_file_tester.py file1.par file2.par file3.par

    # Export universal schema without plotting
    python actual_file_tester.py data.par --no-plot --export-csv --output results/

    # Full analysis with plots and analytics
    python actual_file_tester.py data.par --show-analytics --output analysis/
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

    # Analytics options
    parser.add_argument(
        '--show-analytics',
        action='store_true',
        help='Run and display fundamental analytics results'
    )

    # Export options
    parser.add_argument(
        '--export-csv',
        action='store_true',
        help='Export data as CSV file (universal schema)'
    )

    parser.add_argument(
        '--export-parquet',
        action='store_true',
        help='Export data as Parquet file (universal schema)'
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
        help='Verbose output with debug information'
    )

    return parser


def main(args):
    """Main script function."""
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
            # Enable debug output for scenarios 6 and 7
            enable_debug = hasattr(args, '_debug_scenario') and getattr(args, '_debug_scenario', 0) in [6, 7]
            data_file = parse_single_file(args.files[0], enable_debug_output=enable_debug)

            # Run analytics if requested
            if args.show_analytics:
                analytics_results = analyze_file_with_analytics(data_file)

            # Plot if requested
            if not args.no_plot:
                plot_data(
                    data_file,
                    "Single File Analysis - Universal Schema",
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
            # Multiple files - process individually (no merging)
            print("=== MULTI-FILE ANALYSIS ===")
            data_files = process_multiple_files(args.files)

            # Run analytics on all files if requested
            if args.show_analytics:
                for i, data_file in enumerate(data_files):
                    print(f"\n--- File {i+1}: {data_file.file_path.name} ---")
                    analytics_results = analyze_file_with_analytics(data_file)

            # Plot if requested (combine for visualization)
            if not args.no_plot:
                plot_data(
                    data_files,
                    "Multi-File Analysis - Universal Schema",
                    args.files,
                    output_dir=args.output,
                    show_plot=not args.output
                )

            # Export if requested
            if args.export_csv or args.export_parquet or args.output:
                if not args.output:
                    args.output = Path('.')

                if args.export_csv:
                    export_data(data_files, args.output, 'csv')
                else:
                    export_data(data_files, args.output, 'parquet')

    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    print("\n=== ANALYSIS COMPLETE ===")
    print(f"Universal Schema: {len(UNIVERSAL_COLUMNS)} columns")
    print(f"Supported Techniques: {list(TECHNIQUE_MAPPING.keys())}")
    print("Ready for production testing!")


if __name__ == "__main__":
    debug_mode = True  # Set to False for command line, True for API testing

    if debug_mode:
        # ============= DEBUG TEST SCENARIOS =============
        # Choose a test scenario by setting debug_scenario number
        debug_scenario = 7  # Change this number to test different scenarios
        
        debug_scenarios = {
            1: {
                'name': 'Nested Structure Parsing - Complex Hierarchy',
                'args': ['../test_nested_structure.par', '--no-plot', '--verbose'],
                'description': 'Test complex nested loops (Loop #3 inside Loop #2), structural filtering'
            },
            2: {
                'name': 'Real Data - GITT EIS Charge',
                'args': ['../data/measurement_groups/GITT_EIS_Charge_cycle1_Channel 2.par', '--no-plot'],
                'description': 'Test real data file with 948k points, segment mapping validation'
            },
            3: {
                'name': 'Real Data with Analytics',
                'args': ['../data/measurement_groups/GITT_EIS_Charge_cycle1_Channel 2.par', '--show-analytics', '--no-plot'],
                'description': 'Test real data with fundamental analytics engine'
            },
            4: {
                'name': 'Nested Structure with Plotting',
                'args': ['../test_nested_structure.par', '--verbose'],
                'description': 'Test nested structure with visualization (no data segments expected)'
            },
            5: {
                'name': 'Real Data with Export',
                'args': ['../data/measurement_groups/GITT_EIS_Charge_cycle1_Channel 2.par', '--export-parquet', '--no-plot', '--output', './debug_output'],
                'description': 'Test real data with parquet export to debug_output folder'
            },
            6: {
                'name': 'Nested Structure with Debug Output',
                'args': ['../test_nested_structure.par', '--no-plot', '--verbose'],
                'description': 'Test nested structure with detailed structural parsing debug output'
            },
            7: {
                'name': 'Real Data with Debug Output',
                'args': ['../data/measurement_groups/GITT_EIS_Charge_cycle1_Channel 2.par', '--no-plot', '--verbose'],
                'description': 'Test real data with structural parsing debug output (first 10 actions only)'
            }
        }
        
        # Display available scenarios
        print("=== DEBUG MODE - STRUCTURAL PARSING TESTING ===")
        print("Available test scenarios:")
        for num, scenario in debug_scenarios.items():
            marker = ">>> " if num == debug_scenario else "    "
            print(f"{marker}{num}. {scenario['name']}")
            print(f"       {scenario['description']}")
            print(f"       Args: {' '.join(scenario['args'])}")
            print()
        
        # Execute selected scenario
        if debug_scenario in debug_scenarios:
            selected = debug_scenarios[debug_scenario]
            print(f"=== EXECUTING SCENARIO {debug_scenario}: {selected['name']} ===")
            print(f"Description: {selected['description']}")
            print(f"Args: {' '.join(selected['args'])}")
            print()
            args = create_parser().parse_args(selected['args'])
            # Store debug scenario number for reference
            args._debug_scenario = debug_scenario
        else:
            print(f"❌ Invalid debug_scenario: {debug_scenario}")
            print(f"Available scenarios: {list(debug_scenarios.keys())}")
            exit(1)
            
        print("💡 PyCharm Debug Tips:")
        print("   - Set breakpoints in src/core/parsers.py:")
        print("     * _parse_action() (~line 181) - action filtering")
        print("     * _build_execution_sequence() (~line 414) - loop grouping") 
        print("     * _build_segment_mapping() (~line 450) - segment mapping")
        print("   - Watch variables: self.actions, self.experimental_action_counter")
        print("   - Check execution_sequence for proper loop hierarchy")
        print()
        
    else:
        args = create_parser().parse_args()

    main(args)