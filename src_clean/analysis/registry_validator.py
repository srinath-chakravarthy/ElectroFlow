"""
Registry Validator Tool - Development Helper for Registry System

This tool provides validation and development helpers for the registry-driven
plotting system, making it easy to:
- Validate all plot configurations against actual DataFrame schemas
- Get available columns from analysis functions  
- Add/modify plot configurations programmatically
- Generate comprehensive configuration reports

Usage:
    from src_clean.analysis.registry_validator import RegistryValidator
    
    validator = RegistryValidator()
    validator.validate_all_configs()
    validator.generate_config_report()
"""

from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import pandas as pd
from dataclasses import dataclass

from .registry import get_analysis_registry, AnalysisRegistry


@dataclass
class ValidationResult:
    """Results of plot configuration validation."""
    analysis_id: str
    plot_name: str
    is_valid: bool
    missing_columns: List[str]
    available_columns: List[str]
    error_message: Optional[str] = None


class RegistryValidator:
    """
    Registry validation and development helper tool.
    
    Provides methods to validate plot configurations, discover available columns,
    and help with registry development workflow.
    """
    
    def __init__(self):
        self.registry = get_analysis_registry()
        self._sample_segments = self._create_sample_segments()
    
    def validate_all_configs(self) -> Dict[str, List[ValidationResult]]:
        """
        Validate all plot configurations against actual DataFrame schemas.
        
        Returns:
            Dict mapping analysis_id to list of validation results
        """
        print("🔍 Validating all registry plot configurations...")
        
        results = {}
        
        for analysis_id in self._get_all_analysis_ids():
            print(f"\n=== Validating {analysis_id} ===")
            analysis_results = []
            
            config = self.registry.get_analysis(analysis_id)
            if not config or not config.plot_config:
                print(f"  ⚠️ No plot configurations found")
                continue
            
            # Get available columns by running analysis
            available_columns = self.get_available_columns(analysis_id)
            
            # Validate each plot configuration
            for plot_name, plot_config in config.plot_config.items():
                result = self._validate_single_plot_config(
                    analysis_id, plot_name, plot_config, available_columns
                )
                analysis_results.append(result)
                
                if result.is_valid:
                    print(f"  ✅ {plot_name}: Valid")
                else:
                    print(f"  ❌ {plot_name}: Missing {result.missing_columns}")
            
            results[analysis_id] = analysis_results
        
        return results
    
    def get_available_columns(self, analysis_id: str) -> List[str]:
        """
        Get available DataFrame columns for an analysis by running it.
        
        Args:
            analysis_id: Analysis type to check
            
        Returns:
            List of column names available in the DataFrame
        """
        try:
            # Get appropriate sample segments for this analysis
            sample_segments = self._get_sample_segments_for_analysis(analysis_id)
            
            # Execute analysis to get actual DataFrame
            result = self.registry.execute_analysis(analysis_id, sample_segments, {})
            
            if isinstance(result, pd.DataFrame):
                columns = list(result.columns)
                print(f"  📊 {analysis_id}: Found {len(columns)} columns")
                return sorted(columns)
            else:
                print(f"  ❌ {analysis_id}: Analysis returned {type(result)}, not DataFrame")
                return []
                
        except Exception as e:
            print(f"  ❌ {analysis_id}: Error running analysis - {str(e)}")
            return []
    
    def validate_plot_columns(self, analysis_id: str, plot_name: str) -> ValidationResult:
        """
        Validate a specific plot configuration.
        
        Args:
            analysis_id: Analysis type
            plot_name: Name of plot to validate
            
        Returns:
            ValidationResult with details
        """
        config = self.registry.get_analysis(analysis_id)
        if not config or plot_name not in config.plot_config:
            return ValidationResult(
                analysis_id=analysis_id,
                plot_name=plot_name,
                is_valid=False,
                missing_columns=[],
                available_columns=[],
                error_message=f"Plot '{plot_name}' not found in {analysis_id}"
            )
        
        plot_config = config.plot_config[plot_name]
        available_columns = self.get_available_columns(analysis_id)
        
        return self._validate_single_plot_config(
            analysis_id, plot_name, plot_config, available_columns
        )
    
    def generate_config_report(self) -> str:
        """
        Generate comprehensive markdown report of all registry configurations.
        
        Returns:
            Markdown-formatted report string
        """
        print("📋 Generating registry configuration report...")
        
        validation_results = self.validate_all_configs()
        
        report_lines = [
            "# Registry Configuration Report",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            ""
        ]
        
        # Summary statistics
        total_analyses = len(validation_results)
        total_plots = sum(len(results) for results in validation_results.values())
        valid_plots = sum(1 for results in validation_results.values() 
                         for result in results if result.is_valid)
        
        report_lines.extend([
            f"- **Total Analyses**: {total_analyses}",
            f"- **Total Plots**: {total_plots}",
            f"- **Valid Plots**: {valid_plots}",
            f"- **Invalid Plots**: {total_plots - valid_plots}",
            ""
        ])
        
        # Detailed analysis reports
        for analysis_id, results in validation_results.items():
            report_lines.extend([
                f"## {analysis_id}",
                ""
            ])
            
            # Available columns
            available_columns = self.get_available_columns(analysis_id)
            if available_columns:
                report_lines.extend([
                    f"**Available Columns** ({len(available_columns)}):",
                    "```"
                ])
                for col in available_columns[:10]:  # Show first 10
                    report_lines.append(f"  {col}")
                if len(available_columns) > 10:
                    report_lines.append(f"  ... and {len(available_columns) - 10} more")
                report_lines.append("```")
                report_lines.append("")
            
            # Plot configurations
            report_lines.append("**Plot Configurations**:")
            report_lines.append("")
            
            for result in results:
                status = "✅" if result.is_valid else "❌"
                report_lines.append(f"- {status} **{result.plot_name}**")
                
                if not result.is_valid:
                    report_lines.append(f"  - Missing: {result.missing_columns}")
                    
                    # Suggest similar columns
                    suggestions = self._suggest_similar_columns(
                        result.missing_columns, result.available_columns
                    )
                    if suggestions:
                        report_lines.append(f"  - Suggestions: {suggestions}")
                
                report_lines.append("")
        
        return "\n".join(report_lines)
    
    def add_plot_config(self, analysis_id: str, plot_name: str, 
                       plot_type: str, x_column: str, y_column: Optional[str] = None,
                       title: Optional[str] = None, x_label: Optional[str] = None,
                       y_label: Optional[str] = None) -> bool:
        """
        Add new plot configuration to existing analysis.
        
        Args:
            analysis_id: Analysis to add plot to
            plot_name: Name for the new plot
            plot_type: Type of plot ('line', 'scatter', 'histogram')
            x_column: X-axis column name
            y_column: Y-axis column name (optional for histograms)
            title: Plot title (auto-generated if None)
            x_label: X-axis label (auto-generated if None)
            y_label: Y-axis label (auto-generated if None)
            
        Returns:
            True if successfully added, False otherwise
        """
        config = self.registry.get_analysis(analysis_id)
        if not config:
            print(f"❌ Analysis '{analysis_id}' not found")
            return False
        
        # Auto-generate missing labels
        if not title:
            title = f"{plot_name} - {analysis_id}"
        if not x_label:
            x_label = x_column.replace('_', ' ').title()
        if not y_label and y_column:
            y_label = y_column.replace('_', ' ').title()
        
        # Build plot config
        plot_config = {
            "plot_type": plot_type,
            "x_column": x_column,
            "title": title,
            "x_label": x_label
        }
        
        if y_column:
            plot_config["y_column"] = y_column
            plot_config["y_label"] = y_label
        elif not y_label:
            plot_config["y_label"] = "Count"  # Default for histograms
        else:
            plot_config["y_label"] = y_label
        
        # Add to configuration
        config.plot_config[plot_name] = plot_config
        
        # Validate the new configuration
        validation = self.validate_plot_columns(analysis_id, plot_name)
        if validation.is_valid:
            print(f"✅ Added plot '{plot_name}' to {analysis_id}")
            return True
        else:
            print(f"❌ Plot config invalid: Missing columns {validation.missing_columns}")
            # Remove the invalid config
            del config.plot_config[plot_name]
            return False
    
    def _get_all_analysis_ids(self) -> List[str]:
        """Get all registered analysis IDs."""
        return [analysis.analysis_id for analysis in self.registry.list_analyses()]
    
    def _validate_single_plot_config(self, analysis_id: str, plot_name: str, 
                                   plot_config: Dict[str, Any], 
                                   available_columns: List[str]) -> ValidationResult:
        """Validate a single plot configuration."""
        
        # Get required columns from plot config
        required_columns = []
        if 'x_column' in plot_config:
            required_columns.append(plot_config['x_column'])
        if 'y_column' in plot_config:
            required_columns.append(plot_config['y_column'])
        
        # Check which columns are missing
        missing_columns = [col for col in required_columns 
                          if col and col not in available_columns]
        
        return ValidationResult(
            analysis_id=analysis_id,
            plot_name=plot_name,
            is_valid=len(missing_columns) == 0,
            missing_columns=missing_columns,
            available_columns=available_columns
        )
    
    def _suggest_similar_columns(self, missing_columns: List[str], 
                               available_columns: List[str]) -> List[str]:
        """Suggest similar column names for missing columns."""
        suggestions = []
        
        for missing in missing_columns:
            # Simple similarity matching
            missing_lower = missing.lower()
            candidates = []
            
            for available in available_columns:
                available_lower = available.lower()
                
                # Check for partial matches
                if missing_lower in available_lower or available_lower in missing_lower:
                    candidates.append(available)
                # Check for common words
                elif any(word in available_lower for word in missing_lower.split('_')):
                    candidates.append(available)
            
            if candidates:
                suggestions.extend(candidates[:2])  # Top 2 suggestions
        
        return list(set(suggestions))  # Remove duplicates
    
    def _create_sample_segments(self) -> Dict[str, List[Dict]]:
        """Create sample segment data for testing different analysis types."""
        return {
            'basic': [
                {'id': 1, 'fundamental_technique': 'Rest', 'duration_s': 100, 
                 'start_potential_v': 3.5, 'end_potential_v': 3.4, 'start_time_s': 0}
            ],
            'galvanostatic': [
                {'id': 1, 'fundamental_technique': 'Galvanostatic', 
                 'analysis_results': {'ir_immediate': 0.02}, 'start_time_s': 0}
            ],
            'rest_with_analysis': [
                {'id': 1, 'fundamental_technique': 'Rest', 'duration_s': 100,
                 'analysis_results': {'v_eq': 3.4, 'tau': 50.0, 'r_squared': 0.95},
                 'start_time_s': 0}
            ],
            'potentiostatic': [
                {'id': 1, 'fundamental_technique': 'Potentiostatic',
                 'analysis_results': {'decay_constant': 50.0}, 'start_time_s': 0}
            ]
        }
    
    def _get_sample_segments_for_analysis(self, analysis_id: str) -> List[Dict]:
        """Get appropriate sample segments for a specific analysis type."""
        
        analysis_requirements = {
            'basic_statistics': 'basic',
            'resistance_analysis': 'galvanostatic', 
            'kinetics_analysis': 'rest_with_analysis',
            'equilibrium_analysis': 'basic',
            'current_decay_analysis': 'potentiostatic',
            'dqdv_analysis': 'basic'
        }
        
        sample_key = analysis_requirements.get(analysis_id, 'basic')
        return self._sample_segments.get(sample_key, self._sample_segments['basic'])


# ===== CONVENIENCE FUNCTIONS =====

def validate_all_configs() -> Dict[str, List[ValidationResult]]:
    """Convenience function to validate all configurations."""
    validator = RegistryValidator()
    return validator.validate_all_configs()

def generate_config_report() -> str:
    """Convenience function to generate configuration report."""
    validator = RegistryValidator()
    return validator.generate_config_report()

def get_available_columns(analysis_id: str) -> List[str]:
    """Convenience function to get available columns for an analysis."""
    validator = RegistryValidator()
    return validator.get_available_columns(analysis_id)

def add_plot_to_registry(analysis_id: str, plot_name: str, plot_type: str,
                        x_column: str, y_column: Optional[str] = None, **kwargs) -> bool:
    """Convenience function to add a plot configuration."""
    validator = RegistryValidator()
    return validator.add_plot_config(analysis_id, plot_name, plot_type, 
                                   x_column, y_column, **kwargs)