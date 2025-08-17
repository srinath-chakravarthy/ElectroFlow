"""
Group Analytics for Battery Data Analyzer.

Provides analytics for user-defined groups of techniques across files.
Supports specialized analysis for different group types: OCV, Rate, EIS, GITT, etc.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import polars as pl
import numpy as np
from dataclasses import dataclass
from pathlib import Path
import sys

# Add src directory to path for imports
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from core.database import DatabaseManager
from io_utils.storage_v2 import DatabaseStorageManager

logger = logging.getLogger(__name__)


@dataclass
class GroupAnalyticsResult:
    """Result of group analytics analysis."""
    group_id: int
    group_name: str
    group_type: str
    technique_count: int
    total_points: int
    time_span_hours: float
    analysis_results: Dict[str, Any]
    quality_metrics: Dict[str, float]
    computed_at: str


class GroupAnalytics:
    """
    Analytics engine for user-defined technique groups.
    
    Provides specialized analysis based on group type:
    - OCV Analysis: Voltage equilibration, time constants, stability
    - Rate Analysis: C-rate effects, capacity retention, efficiency  
    - EIS Analysis: Impedance spectra, resistance evolution, fitting
    - GITT Analysis: Diffusion coefficients, overpotentials, kinetics
    - Cycle Comparison: Degradation trends, capacity fade, resistance growth
    - Custom: General statistics and data quality metrics
    """
    
    def __init__(self, storage_manager: DatabaseStorageManager):
        """
        Initialize group analytics engine.
        
        Args:
            storage_manager: Database storage manager instance
        """
        self.storage = storage_manager
        self.db = storage_manager.db
        
    def analyze_group(self, group_id: int) -> Optional[GroupAnalyticsResult]:
        """
        Analyze a technique group and return comprehensive results.
        
        Args:
            group_id: Database ID of the group to analyze
            
        Returns:
            GroupAnalyticsResult with specialized analysis or None if group not found
        """
        # Get group metadata
        group = self.db.get_user_group_by_id(group_id)
        if not group:
            logger.error(f"Group {group_id} not found")
            return None
        
        try:
            # Load data for all techniques in group
            group_data = self._load_group_data(group)
            if group_data.is_empty():
                logger.warning(f"No data found for group {group_id}")
                return None
            
            # Perform group-type specific analysis
            analysis_results = self._perform_group_analysis(group, group_data)
            
            # Compute quality metrics
            quality_metrics = self._compute_quality_metrics(group_data)
            
            # Create result
            result = GroupAnalyticsResult(
                group_id=group_id,
                group_name=group['group_name'],
                group_type=group['group_type'],
                technique_count=len(group['techniques']),
                total_points=group_data.height,
                time_span_hours=(group_data.get_column('time_s').max() - group_data.get_column('time_s').min()) / 3600,
                analysis_results=analysis_results,
                quality_metrics=quality_metrics,
                computed_at=datetime.now().isoformat()
            )
            
            logger.info(f"Completed analysis for group {group_id} ({group['group_type']})")
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze group {group_id}: {e}")
            return None
    
    def _load_group_data(self, group: Dict[str, Any]) -> pl.DataFrame:
        """
        Load and combine data for all techniques in group.
        
        Args:
            group: Group metadata dictionary
            
        Returns:
            Combined DataFrame with all technique data
        """
        group_data = []
        
        for technique_ref in group['techniques']:
            file_id = technique_ref['file_id']
            segment_number = technique_ref['segment_number']
            
            # Load processed file data
            data = self.storage.load_processed_file(file_id)
            if data is None:
                logger.warning(f"Could not load data for file {file_id}")
                continue
            
            # Filter to specific segment
            segment_data = data.filter(pl.col('segment_number') == segment_number)
            if segment_data.is_empty():
                logger.warning(f"No data for segment {segment_number} in file {file_id}")
                continue
            
            # Add group metadata
            segment_data = segment_data.with_columns([
                pl.lit(file_id).alias('source_file_id'),
                pl.lit(segment_number).alias('source_segment'),
                pl.lit(f"{file_id}_seg{segment_number}").alias('technique_id')
            ])
            
            group_data.append(segment_data)
        
        if group_data:
            return pl.concat(group_data, how="vertical_relaxed")
        else:
            return pl.DataFrame()
    
    def _perform_group_analysis(self, group: Dict[str, Any], data: pl.DataFrame) -> Dict[str, Any]:
        """
        Perform group-type specific analysis.
        
        Args:
            group: Group metadata
            data: Combined group data
            
        Returns:
            Analysis results dictionary
        """
        group_type = group['group_type']
        
        if group_type == "OCV Analysis":
            return self._analyze_ocv_group(data)
        elif group_type == "Rate Analysis":
            return self._analyze_rate_group(data)
        elif group_type == "EIS Analysis":
            return self._analyze_eis_group(data)
        elif group_type == "GITT Analysis":
            return self._analyze_gitt_group(data)
        elif group_type == "Cycle Comparison":
            return self._analyze_cycle_group(data)
        else:  # Custom or unknown
            return self._analyze_custom_group(data)
    
    def _analyze_ocv_group(self, data: pl.DataFrame) -> Dict[str, Any]:
        """Analyze OCV (Open Circuit Voltage) group."""
        results = {
            "analysis_type": "OCV Analysis",
            "techniques_analyzed": data.get_column('technique_id').unique().to_list()
        }
        
        try:
            # Voltage statistics by technique
            voltage_stats = (
                data.group_by('technique_id')
                .agg([
                    pl.col('potential_v').mean().alias('avg_voltage_v'),
                    pl.col('potential_v').std().alias('voltage_stability_v'),
                    pl.col('potential_v').min().alias('min_voltage_v'),
                    pl.col('potential_v').max().alias('max_voltage_v'),
                    pl.col('time_s').max().alias('duration_s'),
                    pl.len().alias('point_count')
                ])
            )
            
            # Convert to list of dictionaries for easy access
            results['voltage_by_technique'] = voltage_stats.to_dicts()
            
            # Overall voltage evolution
            if 'time_s' in data.columns and 'potential_v' in data.columns:
                # Group voltage evolution (time vs technique)
                results['voltage_evolution'] = {
                    'time_points': data.get_column('time_s').to_list(),
                    'voltage_points': data.get_column('potential_v').to_list(),
                    'technique_labels': data.get_column('technique_id').to_list()
                }
                
                # Overall statistics
                results['overall_stats'] = {
                    'average_voltage_v': float(data.get_column('potential_v').mean()),
                    'voltage_range_v': float(data.get_column('potential_v').max() - data.get_column('potential_v').min()),
                    'total_duration_hours': float((data.get_column('time_s').max() - data.get_column('time_s').min()) / 3600),
                    'equilibration_quality': float(1.0 - data.get_column('potential_v').std() / data.get_column('potential_v').mean())
                }
            
        except Exception as e:
            logger.error(f"Error in OCV analysis: {e}")
            results['error'] = str(e)
        
        return results
    
    def _analyze_rate_group(self, data: pl.DataFrame) -> Dict[str, Any]:
        """Analyze Rate (C-rate) group."""
        results = {
            "analysis_type": "Rate Analysis",
            "techniques_analyzed": data.get_column('technique_id').unique().to_list()
        }
        
        try:
            # Current statistics by technique (proxy for C-rate)
            current_stats = (
                data.group_by('technique_id')
                .agg([
                    pl.col('current_a').mean().alias('avg_current_a'),
                    pl.col('current_a').abs().mean().alias('avg_abs_current_a'),
                    pl.col('current_a').std().alias('current_stability_a'),
                    pl.col('potential_v').mean().alias('avg_voltage_v'),
                    pl.col('time_s').max().alias('duration_s'),
                    pl.len().alias('point_count')
                ])
            )
            
            results['current_by_technique'] = current_stats.to_dicts()
            
            # Capacity and energy calculations (if available)
            if 'charge_capacity_ah' in data.columns:
                capacity_stats = (
                    data.group_by('technique_id')
                    .agg([
                        pl.col('charge_capacity_ah').max().alias('capacity_ah'),
                        pl.col('energy_wh').max().alias('energy_wh') if 'energy_wh' in data.columns else pl.lit(0).alias('energy_wh')
                    ])
                )
                results['capacity_by_technique'] = capacity_stats.to_dicts()
            
            # Rate analysis summary
            current_levels = [abs(float(row['avg_current_a'])) for row in results['current_by_technique']]
            if current_levels:
                results['rate_summary'] = {
                    'min_current_a': min(current_levels),
                    'max_current_a': max(current_levels),
                    'current_range_ratio': max(current_levels) / min(current_levels) if min(current_levels) > 0 else 1.0,
                    'technique_count': len(current_levels)
                }
            
        except Exception as e:
            logger.error(f"Error in rate analysis: {e}")
            results['error'] = str(e)
        
        return results
    
    def _analyze_eis_group(self, data: pl.DataFrame) -> Dict[str, Any]:
        """Analyze EIS (Electrochemical Impedance Spectroscopy) group."""
        results = {
            "analysis_type": "EIS Analysis",
            "techniques_analyzed": data.get_column('technique_id').unique().to_list()
        }
        
        try:
            # Filter EIS data (non-null impedance values)
            eis_data = data.filter(
                (pl.col('impedance_real_ohm').is_not_null()) & 
                (pl.col('impedance_imag_ohm').is_not_null()) &
                (pl.col('frequency_hz').is_not_null()) &
                (pl.col('frequency_hz') > 0)
            )
            
            if eis_data.is_empty():
                results['error'] = "No valid EIS data found in group"
                return results
            
            # EIS statistics by technique
            eis_stats = (
                eis_data.group_by('technique_id')
                .agg([
                    pl.col('frequency_hz').min().alias('freq_min_hz'),
                    pl.col('frequency_hz').max().alias('freq_max_hz'),
                    pl.col('impedance_real_ohm').min().alias('z_real_min_ohm'),
                    pl.col('impedance_real_ohm').max().alias('z_real_max_ohm'),
                    pl.col('impedance_imag_ohm').min().alias('z_imag_min_ohm'),
                    pl.col('impedance_imag_ohm').max().alias('z_imag_max_ohm'),
                    pl.len().alias('frequency_points')
                ])
            )
            
            results['eis_by_technique'] = eis_stats.to_dicts()
            
            # Simple resistance estimates (high frequency intercept)
            resistance_estimates = []
            for technique_id in eis_data.get_column('technique_id').unique():
                tech_data = eis_data.filter(pl.col('technique_id') == technique_id)
                
                # Find high frequency point (approximate series resistance)
                high_freq_data = tech_data.filter(
                    pl.col('frequency_hz') == pl.col('frequency_hz').max()
                )
                
                if not high_freq_data.is_empty():
                    series_r = float(high_freq_data.get_column('impedance_real_ohm').mean())
                    resistance_estimates.append({
                        'technique_id': technique_id,
                        'series_resistance_ohm': series_r
                    })
            
            results['resistance_estimates'] = resistance_estimates
            
            # Overall EIS summary
            results['eis_summary'] = {
                'total_spectra': len(eis_data.get_column('technique_id').unique()),
                'frequency_range_decades': float(np.log10(eis_data.get_column('frequency_hz').max() / eis_data.get_column('frequency_hz').min())),
                'impedance_magnitude_range_ohm': float(eis_data.get_column('impedance_real_ohm').max() - eis_data.get_column('impedance_real_ohm').min()),
                'total_eis_points': eis_data.height
            }
            
        except Exception as e:
            logger.error(f"Error in EIS analysis: {e}")
            results['error'] = str(e)
        
        return results
    
    def _analyze_gitt_group(self, data: pl.DataFrame) -> Dict[str, Any]:
        """Analyze GITT (Galvanostatic Intermittent Titration Technique) group."""
        results = {
            "analysis_type": "GITT Analysis",
            "techniques_analyzed": data.get_column('technique_id').unique().to_list()
        }
        
        try:
            # GITT typically involves pulse-rest sequences
            # Analyze voltage responses and time constants
            
            gitt_stats = (
                data.group_by('technique_id')
                .agg([
                    pl.col('potential_v').mean().alias('avg_voltage_v'),
                    pl.col('potential_v').max().alias('max_voltage_v'),
                    pl.col('potential_v').min().alias('min_voltage_v'),
                    pl.col('current_a').mean().alias('avg_current_a'),
                    pl.col('time_s').max().alias('duration_s'),
                    pl.len().alias('point_count')
                ])
            )
            
            results['gitt_by_technique'] = gitt_stats.to_dicts()
            
            # Voltage relaxation analysis (simplified)
            voltage_responses = []
            for technique_id in data.get_column('technique_id').unique():
                tech_data = data.filter(pl.col('technique_id') == technique_id)
                
                if tech_data.height > 10:  # Need sufficient points
                    voltage_change = float(tech_data.get_column('potential_v').max() - tech_data.get_column('potential_v').min())
                    time_span = float(tech_data.get_column('time_s').max() - tech_data.get_column('time_s').min())
                    
                    voltage_responses.append({
                        'technique_id': technique_id,
                        'voltage_change_v': voltage_change,
                        'time_span_s': time_span,
                        'voltage_rate_v_per_s': voltage_change / time_span if time_span > 0 else 0
                    })
            
            results['voltage_responses'] = voltage_responses
            
            # GITT summary
            if voltage_responses:
                avg_voltage_change = sum(r['voltage_change_v'] for r in voltage_responses) / len(voltage_responses)
                avg_time_span = sum(r['time_span_s'] for r in voltage_responses) / len(voltage_responses)
                
                results['gitt_summary'] = {
                    'pulse_count': len(voltage_responses),
                    'avg_voltage_change_v': avg_voltage_change,
                    'avg_pulse_duration_s': avg_time_span,
                    'total_experiment_hours': float((data.get_column('time_s').max() - data.get_column('time_s').min()) / 3600)
                }
            
        except Exception as e:
            logger.error(f"Error in GITT analysis: {e}")
            results['error'] = str(e)
        
        return results
    
    def _analyze_cycle_group(self, data: pl.DataFrame) -> Dict[str, Any]:
        """Analyze Cycle Comparison group."""
        results = {
            "analysis_type": "Cycle Comparison",
            "techniques_analyzed": data.get_column('technique_id').unique().to_list()
        }
        
        try:
            # Cycle-by-cycle comparison
            cycle_stats = (
                data.group_by('technique_id')
                .agg([
                    pl.col('potential_v').mean().alias('avg_voltage_v'),
                    pl.col('current_a').mean().alias('avg_current_a'),
                    pl.col('charge_capacity_ah').max().alias('capacity_ah') if 'charge_capacity_ah' in data.columns else pl.lit(0).alias('capacity_ah'),
                    pl.col('energy_wh').max().alias('energy_wh') if 'energy_wh' in data.columns else pl.lit(0).alias('energy_wh'),
                    pl.col('time_s').max().alias('duration_s'),
                    pl.len().alias('point_count')
                ])
                .sort('technique_id')
            )
            
            results['cycle_by_technique'] = cycle_stats.to_dicts()
            
            # Degradation analysis (if capacity data available)
            if 'charge_capacity_ah' in data.columns:
                capacities = [row['capacity_ah'] for row in results['cycle_by_technique']]
                if len(capacities) > 1 and max(capacities) > 0:
                    initial_capacity = max(capacities)
                    final_capacity = capacities[-1] if capacities else 0
                    
                    results['degradation_analysis'] = {
                        'initial_capacity_ah': initial_capacity,
                        'final_capacity_ah': final_capacity,
                        'capacity_retention_percent': (final_capacity / initial_capacity * 100) if initial_capacity > 0 else 0,
                        'capacity_fade_percent': ((initial_capacity - final_capacity) / initial_capacity * 100) if initial_capacity > 0 else 0,
                        'cycle_count': len(capacities)
                    }
            
            # Cycle comparison summary
            voltages = [row['avg_voltage_v'] for row in results['cycle_by_technique']]
            currents = [row['avg_current_a'] for row in results['cycle_by_technique']]
            
            results['comparison_summary'] = {
                'cycle_count': len(results['cycle_by_technique']),
                'voltage_consistency_v': float(np.std(voltages)) if voltages else 0,
                'current_consistency_a': float(np.std(currents)) if currents else 0,
                'total_experiment_hours': float((data.get_column('time_s').max() - data.get_column('time_s').min()) / 3600)
            }
            
        except Exception as e:
            logger.error(f"Error in cycle analysis: {e}")
            results['error'] = str(e)
        
        return results
    
    def _analyze_custom_group(self, data: pl.DataFrame) -> Dict[str, Any]:
        """Analyze Custom group with general statistics."""
        results = {
            "analysis_type": "Custom Analysis",
            "techniques_analyzed": data.get_column('technique_id').unique().to_list()
        }
        
        try:
            # General statistics by technique
            general_stats = (
                data.group_by('technique_id')
                .agg([
                    pl.col('potential_v').mean().alias('avg_voltage_v'),
                    pl.col('potential_v').std().alias('voltage_std_v'),
                    pl.col('current_a').mean().alias('avg_current_a'),
                    pl.col('current_a').std().alias('current_std_a'),
                    pl.col('time_s').min().alias('start_time_s'),
                    pl.col('time_s').max().alias('end_time_s'),
                    pl.len().alias('point_count')
                ])
            )
            
            results['stats_by_technique'] = general_stats.to_dicts()
            
            # Overall group statistics
            results['overall_stats'] = {
                'total_techniques': len(data.get_column('technique_id').unique()),
                'total_points': data.height,
                'time_span_hours': float((data.get_column('time_s').max() - data.get_column('time_s').min()) / 3600),
                'voltage_range_v': float(data.get_column('potential_v').max() - data.get_column('potential_v').min()),
                'current_range_a': float(data.get_column('current_a').max() - data.get_column('current_a').min()),
                'data_completeness': float(1.0 - (data.null_count().sum_horizontal() / (data.height * data.width)).item())
            }
            
        except Exception as e:
            logger.error(f"Error in custom analysis: {e}")
            results['error'] = str(e)
        
        return results
    
    def _compute_quality_metrics(self, data: pl.DataFrame) -> Dict[str, float]:
        """Compute data quality metrics for the group."""
        try:
            metrics = {}
            
            # Data completeness
            total_cells = data.height * data.width
            null_cells = data.null_count().sum_horizontal().item()
            metrics['data_completeness'] = 1.0 - (null_cells / total_cells) if total_cells > 0 else 0.0
            
            # Time continuity
            if 'time_s' in data.columns:
                time_diffs = data.get_column('time_s').diff().drop_nulls()
                if time_diffs.len() > 0:
                    time_consistency = 1.0 - (time_diffs.std() / time_diffs.mean()) if time_diffs.mean() > 0 else 0.0
                    metrics['time_continuity'] = max(0.0, min(1.0, time_consistency))
            
            # Signal stability (voltage)
            if 'potential_v' in data.columns:
                voltage_data = data.get_column('potential_v').drop_nulls()
                if voltage_data.len() > 0:
                    cv = voltage_data.std() / abs(voltage_data.mean()) if voltage_data.mean() != 0 else float('inf')
                    metrics['voltage_stability'] = max(0.0, 1.0 - min(cv, 1.0))
            
            # Current stability
            if 'current_a' in data.columns:
                current_data = data.get_column('current_a').drop_nulls()
                if current_data.len() > 0:
                    current_cv = current_data.std() / abs(current_data.mean()) if current_data.mean() != 0 else float('inf')
                    metrics['current_stability'] = max(0.0, 1.0 - min(current_cv, 1.0))
            
            # Overall quality score
            quality_scores = [v for v in metrics.values() if 0 <= v <= 1]
            metrics['overall_quality'] = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error computing quality metrics: {e}")
            return {'overall_quality': 0.0, 'error': str(e)}
    
    def get_group_comparison(self, group_ids: List[int]) -> Dict[str, Any]:
        """
        Compare multiple groups of the same type.
        
        Args:
            group_ids: List of group IDs to compare
            
        Returns:
            Comparison results dictionary
        """
        comparison_results = {
            'group_count': len(group_ids),
            'individual_results': [],
            'comparison_metrics': {},
            'computed_at': datetime.now().isoformat()
        }
        
        # Analyze each group individually
        group_results = []
        for group_id in group_ids:
            result = self.analyze_group(group_id)
            if result:
                group_results.append(result)
                comparison_results['individual_results'].append({
                    'group_id': group_id,
                    'group_name': result.group_name,
                    'group_type': result.group_type,
                    'technique_count': result.technique_count,
                    'total_points': result.total_points,
                    'time_span_hours': result.time_span_hours,
                    'overall_quality': result.quality_metrics.get('overall_quality', 0.0)
                })
        
        # Cross-group comparison metrics
        if len(group_results) > 1:
            # Check if all groups are the same type
            group_types = [r.group_type for r in group_results]
            if len(set(group_types)) == 1:
                comparison_results['comparison_metrics'] = self._compare_same_type_groups(group_results)
            else:
                comparison_results['comparison_metrics'] = {'error': 'Cannot compare groups of different types'}
        
        return comparison_results
    
    def _compare_same_type_groups(self, group_results: List[GroupAnalyticsResult]) -> Dict[str, Any]:
        """Compare groups of the same type."""
        try:
            metrics = {}
            
            # Basic comparison metrics
            technique_counts = [r.technique_count for r in group_results]
            point_counts = [r.total_points for r in group_results]
            time_spans = [r.time_span_hours for r in group_results]
            quality_scores = [r.quality_metrics.get('overall_quality', 0.0) for r in group_results]
            
            metrics['technique_count_stats'] = {
                'mean': float(np.mean(technique_counts)),
                'std': float(np.std(technique_counts)),
                'min': int(min(technique_counts)),
                'max': int(max(technique_counts))
            }
            
            metrics['data_volume_stats'] = {
                'mean_points': float(np.mean(point_counts)),
                'total_points': sum(point_counts),
                'mean_duration_hours': float(np.mean(time_spans)),
                'total_duration_hours': sum(time_spans)
            }
            
            metrics['quality_comparison'] = {
                'mean_quality': float(np.mean(quality_scores)),
                'quality_std': float(np.std(quality_scores)),
                'best_group_id': group_results[np.argmax(quality_scores)].group_id,
                'worst_group_id': group_results[np.argmin(quality_scores)].group_id
            }
            
            return metrics
            
        except Exception as e:
            return {'error': f"Comparison failed: {str(e)}"}