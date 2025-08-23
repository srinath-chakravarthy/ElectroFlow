"""
Command Line Interface - Electrochemical Analysis Suite

Comprehensive CLI for all backend operations supporting scripting and automation.

Key Features:
- Cell management (create, list, delete)
- File processing (upload, validate)
- Data queries (files, segments, techniques)
- ActionID mapping management
- Database utilities
- Scriptable with JSON output
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src_clean.backend import get_backend_api
from src_clean.core.exceptions import format_error_for_user


def format_output(data: Any, format_type: str = 'table') -> str:
    """Format output for display."""
    if format_type == 'json':
        return json.dumps(data, indent=2, default=str)
    
    elif format_type == 'table':
        if isinstance(data, list) and data:
            if isinstance(data[0], dict):
                return format_table(data)
        elif isinstance(data, dict):
            return format_dict(data)
    
    return str(data)


def format_table(data: List[Dict[str, Any]]) -> str:
    """Format list of dictionaries as table."""
    if not data:
        return "No data"
    
    # Get column headers
    headers = list(data[0].keys())
    
    # Calculate column widths
    widths = {header: len(header) for header in headers}
    for row in data:
        for header in headers:
            value = str(row.get(header, ''))
            widths[header] = max(widths[header], len(value))
    
    # Format table
    lines = []
    
    # Header
    header_line = " | ".join(header.ljust(widths[header]) for header in headers)
    lines.append(header_line)
    lines.append("-" * len(header_line))
    
    # Rows
    for row in data:
        row_line = " | ".join(str(row.get(header, '')).ljust(widths[header]) for header in headers)
        lines.append(row_line)
    
    return "\n".join(lines)


def format_dict(data: Dict[str, Any]) -> str:
    """Format dictionary as key-value pairs."""
    lines = []
    for key, value in data.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


class ElectrochemicalCLI:
    """Main CLI application."""
    
    def __init__(self):
        self.api = None
        self.args = None
    
    def run(self):
        """Main entry point."""
        parser = self.create_parser()
        self.args = parser.parse_args()
        
        # Initialize backend API
        data_dir = Path(self.args.data_dir) if self.args.data_dir else None
        self.api = get_backend_api(data_dir)
        
        # Execute command
        try:
            result = self.execute_command()
            
            # Format and display output
            if result is not None:
                output = format_output(result, self.args.format)
                print(output)
                
        except Exception as e:
            error_info = format_error_for_user(e)
            if self.args.format == 'json':
                print(json.dumps({'error': error_info['message']}, indent=2))
            else:
                print(f"Error: {error_info['message']}")
            sys.exit(1)
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser."""
        parser = argparse.ArgumentParser(
            description="Electrochemical Analysis Suite CLI",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # Global options
        parser.add_argument('--data-dir', type=str, 
                          help='Data directory path (default: data_clean)')
        parser.add_argument('--format', choices=['table', 'json'], default='table',
                          help='Output format (default: table)')
        
        # Subcommands
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Cell management
        self.add_cell_commands(subparsers)
        
        # File processing
        self.add_file_commands(subparsers)
        
        # Data queries
        self.add_query_commands(subparsers)
        
        # ActionID management
        self.add_actionid_commands(subparsers)
        
        # Utilities
        self.add_utility_commands(subparsers)
        
        # Advanced analytics
        self.add_analytics_commands(subparsers)
        
        return parser
    
    def add_cell_commands(self, subparsers):
        """Add cell management commands."""
        # Create cell
        create_cell = subparsers.add_parser('create-cell', help='Create new cell')
        create_cell.add_argument('name', help='Cell name')
        create_cell.add_argument('--chemistry', default='Li_metal', help='Cell chemistry')
        create_cell.add_argument('--capacity', type=float, help='Capacity in Ah')
        create_cell.add_argument('--cathode-material', help='Cathode material')
        create_cell.add_argument('--cathode-mass', type=float, help='Cathode mass in mg')
        create_cell.add_argument('--anode-material', help='Anode material')
        create_cell.add_argument('--anode-mass', type=float, help='Anode mass in mg')
        create_cell.add_argument('--notes', help='Cell notes')
        
        # List cells
        subparsers.add_parser('list-cells', help='List all cells')
        
        # Delete cell
        delete_cell = subparsers.add_parser('delete-cell', help='Delete cell')
        delete_cell.add_argument('cell_id', type=int, help='Cell ID to delete')
        delete_cell.add_argument('--confirm', action='store_true', 
                               help='Confirm deletion (required)')
    
    def add_file_commands(self, subparsers):
        """Add file processing commands."""
        # Process dual files
        process_files = subparsers.add_parser('process-files', 
                                            help='Process VersaStudio dual files')
        process_files.add_argument('metadata_file', help='Path to .par file')
        process_files.add_argument('data_file', help='Path to .par.csv file')
        process_files.add_argument('cell_name', help='Target cell name')
        process_files.add_argument('--temperature', type=float, default=25.0,
                                 help='Temperature in Celsius (default: 25.0)')
        
        # Validate files
        validate_files = subparsers.add_parser('validate-files',
                                             help='Validate dual files')
        validate_files.add_argument('metadata_file', help='Path to .par file')
        validate_files.add_argument('data_file', help='Path to .par.csv file')
        
        # List files
        list_files = subparsers.add_parser('list-files', help='List files for cell')
        list_files.add_argument('cell_name', help='Cell name')
    
    def add_query_commands(self, subparsers):
        """Add data query commands."""
        # Get file data
        get_data = subparsers.add_parser('get-data', help='Get file data')
        get_data.add_argument('file_id', help='File ID')
        get_data.add_argument('--limit', type=int, default=10,
                            help='Number of rows to display (default: 10)')
        
        # Get segments
        get_segments = subparsers.add_parser('get-segments', help='Get file segments')
        get_segments.add_argument('file_id', help='File ID')
        
        # Query by technique
        query_technique = subparsers.add_parser('query-technique',
                                              help='Query segments by technique')
        query_technique.add_argument('technique', help='Fundamental technique name')
    
    def add_actionid_commands(self, subparsers):
        """Add ActionID management commands."""
        # List mappings
        subparsers.add_parser('list-actionids', help='List ActionID mappings')
        
        # Add mapping
        add_mapping = subparsers.add_parser('add-actionid', help='Add ActionID mapping')
        add_mapping.add_argument('action_id', type=int, help='ActionID number')
        add_mapping.add_argument('technique_name', help='Technique name')
        add_mapping.add_argument('fundamental_technique', help='Fundamental technique')
        
        # Discover unknown ActionIDs
        discover = subparsers.add_parser('discover-actionids',
                                       help='Discover unknown ActionIDs in file')
        discover.add_argument('file_id', help='File ID to analyze')
    
    def add_utility_commands(self, subparsers):
        """Add utility commands."""
        # Database stats
        subparsers.add_parser('stats', help='Show database statistics')
        
        # Cleanup
        subparsers.add_parser('cleanup', help='Clean up failed processing attempts')
        
        # Export data
        export = subparsers.add_parser('export', help='Export file data')
        export.add_argument('file_id', help='File ID')
        export.add_argument('output_file', help='Output file path')
        export.add_argument('--format', choices=['csv', 'parquet'], default='csv',
                          help='Export format (default: csv)')
    
    def add_analytics_commands(self, subparsers):
        """Add advanced analytics commands."""
        # Group temporal analytics
        temporal = subparsers.add_parser('group-temporal', 
                                       help='Get temporal analytics for groups')
        temporal.add_argument('group_ids', nargs='+', help='Group IDs to analyze')
        temporal.add_argument('--plot-types', nargs='*', 
                            choices=['capacity_vs_time', 'energy_vs_time', 
                                   'cumulative_capacity', 'cumulative_energy',
                                   'voltage_evolution'],
                            help='Types of plots to generate')
        temporal.add_argument('--save-plots', help='Directory to save plots')
        
        # Group fit quality statistics
        fit_quality = subparsers.add_parser('group-fit-quality',
                                          help='Get fitting quality statistics for groups')
        fit_quality.add_argument('group_ids', nargs='+', help='Group IDs to analyze')
        fit_quality.add_argument('--technique-filter', help='Filter by specific technique')
        
        # Group voltage correlation analytics
        voltage_corr = subparsers.add_parser('group-voltage-correlation',
                                           help='Get voltage correlation analytics for groups')
        voltage_corr.add_argument('group_ids', nargs='+', help='Group IDs to analyze')
        voltage_corr.add_argument('--correlation-type', choices=['pearson', 'spearman', 'both'],
                                default='both', help='Type of correlation to compute')
        
        # Analytics config operations
        config_gen = subparsers.add_parser('generate-analytics-config',
                                         help='Generate analytics configuration file')
        config_gen.add_argument('--output-path', help='Path to save config file')
        
        # List cumulative fields
        subparsers.add_parser('list-cumulative-fields',
                            help='List all cumulative field names')
        
        # Test sqrt(t) fitting
        test_sqrt = subparsers.add_parser('test-sqrt-fitting',
                                        help='Test sqrt(t) fitting on segments')
        test_sqrt.add_argument('segment_ids', nargs='+', help='Segment IDs to test')
        test_sqrt.add_argument('--compare-exponential', action='store_true',
                             help='Compare with exponential fitting results')
        
        # Group comparison analytics
        group_compare = subparsers.add_parser('compare-groups',
                                            help='Compare analytics between groups')
        group_compare.add_argument('group_ids', nargs='+', help='Group IDs to compare')
        group_compare.add_argument('--metrics', nargs='*',
                                 choices=['capacity', 'energy', 'duration', 'voltage',
                                        'fit_quality', 'correlation'],
                                 default=['capacity', 'energy', 'fit_quality'],
                                 help='Metrics to compare between groups')
    
    def execute_command(self) -> Any:
        """Execute the parsed command."""
        command = self.args.command
        
        if command == 'create-cell':
            return self.create_cell()
        elif command == 'list-cells':
            return self.list_cells()
        elif command == 'delete-cell':
            return self.delete_cell()
        elif command == 'process-files':
            return self.process_files()
        elif command == 'validate-files':
            return self.validate_files()
        elif command == 'list-files':
            return self.list_files()
        elif command == 'get-data':
            return self.get_data()
        elif command == 'get-segments':
            return self.get_segments()
        elif command == 'query-technique':
            return self.query_technique()
        elif command == 'list-actionids':
            return self.list_actionids()
        elif command == 'add-actionid':
            return self.add_actionid()
        elif command == 'discover-actionids':
            return self.discover_actionids()
        elif command == 'stats':
            return self.get_stats()
        elif command == 'cleanup':
            return self.cleanup()
        elif command == 'export':
            return self.export_data()
        elif command == 'group-temporal':
            return self.group_temporal_analytics()
        elif command == 'group-fit-quality':
            return self.group_fit_quality_analytics()
        elif command == 'group-voltage-correlation':
            return self.group_voltage_correlation_analytics()
        elif command == 'generate-analytics-config':
            return self.generate_analytics_config()
        elif command == 'list-cumulative-fields':
            return self.list_cumulative_fields()
        elif command == 'test-sqrt-fitting':
            return self.test_sqrt_fitting()
        elif command == 'compare-groups':
            return self.compare_groups()
        else:
            raise ValueError(f"Unknown command: {command}")
    
    # =============================================================================
    # CELL COMMANDS
    # =============================================================================
    
    def create_cell(self) -> Dict[str, Any]:
        """Create new cell."""
        kwargs = {
            'chemistry': self.args.chemistry,
            'notes': self.args.notes or ''
        }
        
        if self.args.capacity:
            kwargs['capacity_ah'] = self.args.capacity
        if self.args.cathode_material:
            kwargs['cathode_material'] = self.args.cathode_material
        if self.args.cathode_mass:
            kwargs['cathode_mass_mg'] = self.args.cathode_mass
        if self.args.anode_material:
            kwargs['anode_material'] = self.args.anode_material
        if self.args.anode_mass:
            kwargs['anode_mass_mg'] = self.args.anode_mass
        
        result = self.api.create_cell(self.args.name, **kwargs)
        return result.to_dict()
    
    def list_cells(self) -> List[Dict[str, Any]]:
        """List all cells."""
        return self.api.get_cells()
    
    def delete_cell(self) -> Dict[str, Any]:
        """Delete cell."""
        if not self.args.confirm:
            raise ValueError("--confirm flag required for deletion")
        
        result = self.api.delete_cell(self.args.cell_id)
        return result.to_dict()
    
    # =============================================================================
    # FILE COMMANDS
    # =============================================================================
    
    def process_files(self) -> Dict[str, Any]:
        """Process dual files."""
        metadata_path = Path(self.args.metadata_file)
        data_path = Path(self.args.data_file)
        
        if not metadata_path.exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
        if not data_path.exists():
            raise FileNotFoundError(f"Data file not found: {data_path}")
        
        options = {'temperature_c': self.args.temperature}
        
        result = self.api.process_dual_files(
            metadata_path, data_path, self.args.cell_name, **options
        )
        
        return result.to_dict()
    
    def validate_files(self) -> Dict[str, Any]:
        """Validate dual files."""
        metadata_path = Path(self.args.metadata_file)
        data_path = Path(self.args.data_file)
        
        return self.api.validate_dual_files(metadata_path, data_path)
    
    def list_files(self) -> List[Dict[str, Any]]:
        """List files for cell."""
        return self.api.get_cell_files(self.args.cell_name)
    
    # =============================================================================
    # QUERY COMMANDS
    # =============================================================================
    
    def get_data(self) -> Dict[str, Any]:
        """Get file data."""
        data = self.api.get_file_data(self.args.file_id)
        
        if data is None:
            return {'error': f'File {self.args.file_id} not found'}
        
        # Convert to pandas for display
        df = data.head(self.args.limit).to_pandas()
        
        return {
            'file_id': self.args.file_id,
            'total_rows': data.height,
            'displayed_rows': len(df),
            'columns': list(data.columns),
            'data': df.to_dict('records')
        }
    
    def get_segments(self) -> List[Dict[str, Any]]:
        """Get file segments."""
        return self.api.get_file_segments(self.args.file_id)
    
    def query_technique(self) -> List[Dict[str, Any]]:
        """Query segments by technique."""
        return self.api.get_segments_by_technique(self.args.technique)
    
    # =============================================================================
    # ACTIONID COMMANDS
    # =============================================================================
    
    def list_actionids(self) -> List[Dict[str, Any]]:
        """List ActionID mappings."""
        return self.api.get_actionid_mappings()
    
    def add_actionid(self) -> Dict[str, Any]:
        """Add ActionID mapping."""
        result = self.api.add_actionid_mapping(
            self.args.action_id,
            self.args.technique_name,
            self.args.fundamental_technique
        )
        return result.to_dict()
    
    def discover_actionids(self) -> Dict[str, Any]:
        """Discover unknown ActionIDs."""
        data = self.api.get_file_data(self.args.file_id)
        
        if data is None:
            return {'error': f'File {self.args.file_id} not found'}
        
        unknown_actionids = self.api.discover_unknown_actionids(data)
        
        return {
            'file_id': self.args.file_id,
            'unknown_actionids': unknown_actionids,
            'count': len(unknown_actionids)
        }
    
    # =============================================================================
    # UTILITY COMMANDS
    # =============================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        return self.api.get_database_stats()
    
    def cleanup(self) -> Dict[str, Any]:
        """Clean up failed processing attempts."""
        result = self.api.cleanup_failed_processing()
        return result.to_dict()
    
    def export_data(self) -> Dict[str, Any]:
        """Export file data."""
        data = self.api.get_file_data(self.args.file_id)
        
        if data is None:
            return {'error': f'File {self.args.file_id} not found'}
        
        output_path = Path(self.args.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.args.format == 'csv':
            data.write_csv(output_path)
        elif self.args.format == 'parquet':
            data.write_parquet(output_path)
        
        return {
            'file_id': self.args.file_id,
            'output_file': str(output_path),
            'format': self.args.format,
            'rows_exported': data.height
        }
    
    # =============================================================================
    # ANALYTICS COMMANDS
    # =============================================================================
    
    def group_temporal_analytics(self) -> Dict[str, Any]:
        """Get temporal analytics for groups."""
        group_ids = [str(gid) for gid in self.args.group_ids]
        
        analytics_data = self.api.get_group_temporal_analytics(group_ids)
        
        if 'error' in analytics_data:
            return {'error': analytics_data['error']}
        
        result = {
            'group_ids': group_ids,
            'analytics': analytics_data,
            'summary': {
                'segments_analyzed': analytics_data.get('summary', {}).get('segment_count', 0),
                'files_analyzed': analytics_data.get('summary', {}).get('file_count', 0),
                'total_capacity_ah': analytics_data.get('summary', {}).get('total_capacity_ah', 0.0),
                'total_energy_wh': analytics_data.get('summary', {}).get('total_energy_wh', 0.0)
            }
        }
        
        # Generate plots if requested
        if hasattr(self.args, 'save_plots') and self.args.save_plots:
            plot_dir = Path(self.args.save_plots)
            plot_dir.mkdir(parents=True, exist_ok=True)
            
            time_series = analytics_data.get('time_series', {})
            if time_series and hasattr(self.args, 'plot_types') and self.args.plot_types:
                saved_plots = []
                for plot_type in self.args.plot_types:
                    plot_path = self._generate_temporal_plot(plot_type, time_series, plot_dir)
                    if plot_path:
                        saved_plots.append(str(plot_path))
                
                result['saved_plots'] = saved_plots
        
        return result
    
    def group_fit_quality_analytics(self) -> Dict[str, Any]:
        """Get fitting quality statistics for groups."""
        group_ids = [str(gid) for gid in self.args.group_ids]
        
        fit_quality = self.api.get_group_fit_quality_statistics(group_ids)
        
        if 'error' in fit_quality:
            return {'error': fit_quality['error']}
        
        result = {
            'group_ids': group_ids,
            'fit_quality': fit_quality
        }
        
        # Apply technique filter if specified
        if hasattr(self.args, 'technique_filter') and self.args.technique_filter:
            technique = self.args.technique_filter
            technique_data = fit_quality.get('technique_breakdown', {}).get(technique)
            if technique_data:
                result['filtered_technique'] = {technique: technique_data}
            else:
                result['warning'] = f"No data found for technique: {technique}"
        
        return result
    
    def group_voltage_correlation_analytics(self) -> Dict[str, Any]:
        """Get voltage correlation analytics for groups."""
        group_ids = [str(gid) for gid in self.args.group_ids]
        
        correlations = self.api.get_group_voltage_correlation_analytics(group_ids)
        
        if 'error' in correlations:
            return {'error': correlations['error']}
        
        result = {
            'group_ids': group_ids,
            'correlations': correlations
        }
        
        # Filter correlation type if specified
        if hasattr(self.args, 'correlation_type') and self.args.correlation_type != 'both':
            corr_type = self.args.correlation_type
            filtered_correlations = {}
            
            for voltage_ref, metrics in correlations.items():
                if voltage_ref not in ['vs_start_voltage', 'vs_end_voltage']:
                    continue
                
                filtered_metrics = {}
                for metric, corr_data in metrics.items():
                    if isinstance(corr_data, dict):
                        if corr_type == 'pearson':
                            filtered_metrics[metric] = {
                                'r': corr_data.get('pearson_r', 0.0),
                                'p': corr_data.get('pearson_p', 1.0),
                                'data_points': corr_data.get('data_points', 0)
                            }
                        elif corr_type == 'spearman':
                            filtered_metrics[metric] = {
                                'r': corr_data.get('spearman_r', 0.0),
                                'p': corr_data.get('spearman_p', 1.0),
                                'data_points': corr_data.get('data_points', 0)
                            }
                    else:
                        filtered_metrics[metric] = corr_data
                
                filtered_correlations[voltage_ref] = filtered_metrics
            
            result['filtered_correlations'] = filtered_correlations
        
        return result
    
    def generate_analytics_config(self) -> Dict[str, Any]:
        """Generate analytics configuration file."""
        from src_clean.analysis.analytics_config import get_analytics_registry
        
        registry = get_analytics_registry()
        config = registry.generate_config()
        
        # Save to file
        output_path = None
        if hasattr(self.args, 'output_path') and self.args.output_path:
            output_path = Path(self.args.output_path)
        
        config_file = registry.save_config_file(output_path)
        
        return {
            'config_generated': True,
            'config_file': str(config_file),
            'config_version': config['version'],
            'timestamp': config['generated_timestamp'],
            'field_counts': {
                'base_fields': len(config['segment_base_fields']),
                'cumulative_fields': len(config['segment_cumulative_fields']),
                'analysis_schemas': len(config['analysis_result_schemas']),
                'analytics_methods': len(config['analytics_methods']),
                'group_methods': len(config['group_analytics_methods'])
            }
        }
    
    def list_cumulative_fields(self) -> Dict[str, Any]:
        """List all cumulative field names."""
        field_names = self.api.get_cumulative_field_names()
        
        return {
            'cumulative_fields': field_names,
            'count': len(field_names)
        }
    
    def test_sqrt_fitting(self) -> Dict[str, Any]:
        """Test sqrt(t) fitting on segments."""
        segment_ids = [str(sid) for sid in self.args.segment_ids]
        
        results = []
        for segment_id in segment_ids:
            # Get segment data
            segments = self.api.get_segments_for_file(segment_id)  # This might need adjustment
            if not segments:
                results.append({
                    'segment_id': segment_id,
                    'error': 'Segment not found'
                })
                continue
            
            # For now, return placeholder - would need to implement segment-level fitting test
            results.append({
                'segment_id': segment_id,
                'sqrt_fitting': 'Test would require raw data access',
                'exponential_fitting': 'Test would require raw data access'
            })
        
        return {
            'tested_segments': segment_ids,
            'results': results,
            'compare_exponential': getattr(self.args, 'compare_exponential', False)
        }
    
    def compare_groups(self) -> Dict[str, Any]:
        """Compare analytics between groups."""
        group_ids = [str(gid) for gid in self.args.group_ids]
        metrics = getattr(self.args, 'metrics', ['capacity', 'energy', 'fit_quality'])
        
        comparison = {
            'group_ids': group_ids,
            'metrics_compared': metrics,
            'comparison_results': {}
        }
        
        # Get base statistics for all groups
        if any(metric in metrics for metric in ['capacity', 'energy', 'duration', 'voltage']):
            base_stats = self.api.get_group_base_statistics(group_ids)
            comparison['comparison_results']['base_statistics'] = base_stats
        
        # Get fit quality if requested
        if 'fit_quality' in metrics:
            fit_quality = self.api.get_group_fit_quality_statistics(group_ids)
            comparison['comparison_results']['fit_quality'] = fit_quality
        
        # Get correlation analysis if requested
        if 'correlation' in metrics:
            correlations = self.api.get_group_voltage_correlation_analytics(group_ids)
            comparison['comparison_results']['voltage_correlations'] = correlations
        
        return comparison
    
    def _generate_temporal_plot(self, plot_type: str, time_series: Dict[str, Any], 
                               plot_dir: Path) -> Optional[Path]:
        """Generate temporal plot and save to file."""
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            
            time_points = time_series.get('time_points', [])
            if not time_points:
                return None
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            if plot_type == 'capacity_vs_time':
                capacity = time_series.get('individual_capacity', [])
                ax.plot(time_points, capacity, 'b-o', markersize=3)
                ax.set_ylabel('Capacity (Ah)')
                ax.set_title('Capacity vs Time')
                
            elif plot_type == 'energy_vs_time':
                energy = time_series.get('individual_energy', [])
                ax.plot(time_points, energy, 'r-o', markersize=3)
                ax.set_ylabel('Energy (Wh)')
                ax.set_title('Energy vs Time')
                
            elif plot_type == 'cumulative_capacity':
                cum_capacity = time_series.get('cumulative_capacity', [])
                ax.plot(time_points, cum_capacity, 'g-o', markersize=3)
                ax.set_ylabel('Cumulative Capacity (Ah)')
                ax.set_title('Cumulative Capacity vs Time')
                
            elif plot_type == 'cumulative_energy':
                cum_energy = time_series.get('cumulative_energy', [])
                ax.plot(time_points, cum_energy, 'm-o', markersize=3)
                ax.set_ylabel('Cumulative Energy (Wh)')
                ax.set_title('Cumulative Energy vs Time')
                
            elif plot_type == 'voltage_evolution':
                voltage_start = time_series.get('voltage_start', [])
                voltage_end = time_series.get('voltage_end', [])
                ax.plot(time_points, voltage_start, 'b-o', label='Start Voltage', markersize=3)
                ax.plot(time_points, voltage_end, 'r-o', label='End Voltage', markersize=3)
                ax.set_ylabel('Voltage (V)')
                ax.set_title('Voltage Evolution vs Time')
                ax.legend()
            
            ax.set_xlabel('Time (s)')
            ax.grid(True, alpha=0.3)
            
            plot_path = plot_dir / f"{plot_type}.png"
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return plot_path
            
        except ImportError:
            print("Warning: matplotlib not available for plotting")
            return None
        except Exception as e:
            print(f"Warning: Failed to generate plot {plot_type}: {e}")
            return None


def main():
    """Main entry point."""
    cli = ElectrochemicalCLI()
    cli.run()


if __name__ == '__main__':
    main()