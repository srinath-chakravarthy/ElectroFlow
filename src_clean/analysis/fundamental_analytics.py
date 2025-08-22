"""
Fundamental Analytics Engine - Main Orchestrator

Coordinates core metrics calculation and technique-specific analysis
for all electrochemical segments with database integration.
"""

import json
import logging
from typing import Dict, Any, List, Optional
import polars as pl

from .core_metrics import CoreMetricsCalculator  
from .technique_analyzer import TechniqueAnalyzer

logger = logging.getLogger(__name__)


class FundamentalAnalytics:
    """
    Main analytics engine that orchestrates core metrics and technique analysis.
    
    Processes segment data to compute:
    - Universal core metrics (stored in database columns)
    - Technique-specific analysis (stored in JSON field)
    """
    
    def __init__(self):
        self.core_calculator = CoreMetricsCalculator()
        self.technique_analyzer = TechniqueAnalyzer()
        self.logger = logger
    
    def analyze_segment(self, data: pl.DataFrame, segment_info: Dict[str, Any],
                       previous_segment_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform complete analysis on a segment.
        
        Args:
            data: Full DataFrame with universal schema
            segment_info: Dictionary with segment metadata (start_row, end_row, etc.)
            previous_segment_info: Information about the previous segment for context
            
        Returns:
            Complete analysis results ready for database storage
        """
        try:
            start_row = segment_info['start_row']
            end_row = segment_info['end_row']
            technique_name = segment_info.get('technique_name', 'Unknown')
            fundamental_technique = segment_info.get('fundamental_technique', 'unknown')
            
            self.logger.debug(f"Analyzing segment {segment_info.get('segment_index', '?')}: "
                            f"{technique_name} ({start_row}-{end_row})")
            
            # Calculate core metrics (database columns)
            core_metrics = self.core_calculator.calculate_core_metrics(
                data, start_row, end_row
            )
            
            # Perform technique-specific analysis (JSON field)
            technique_analysis = self.technique_analyzer.analyze_segment(
                data, start_row, end_row, technique_name, fundamental_technique,
                previous_segment_info
            )
            
            # Determine overall analysis status
            core_success = all(core_metrics.get(key) is not None 
                             for key in ['duration_s', 'start_time_s', 'end_time_s'])
            technique_success = technique_analysis.get('success', False)
            
            if core_success and technique_success:
                analysis_status = 'completed'
            elif core_success:
                analysis_status = 'partial'  # Core metrics OK, technique analysis failed
            else:
                analysis_status = 'failed'
            
            # Prepare results for database storage
            result = {
                # Core metrics (database columns)
                **core_metrics,
                
                # Analysis status and results
                'analysis_status': analysis_status,
                'analysis_results': json.dumps(technique_analysis, indent=None),
                
                # Success indicators for logging
                '_core_success': core_success,
                '_technique_success': technique_success
            }
            
            self.logger.info(f"Segment analysis complete: {analysis_status} "
                           f"(core: {'✓' if core_success else '✗'}, "
                           f"technique: {'✓' if technique_success else '✗'})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in fundamental analysis: {e}")
            return self._failed_analysis_result(str(e))
    
    def analyze_all_segments(self, data: pl.DataFrame, 
                           segments_info: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze all segments in a file with context sharing.
        
        Args:
            data: Full DataFrame with universal schema
            segments_info: List of segment information dictionaries
            
        Returns:
            List of analysis results for each segment
        """
        try:
            results = []
            previous_segment = None
            
            for i, segment_info in enumerate(segments_info):
                self.logger.debug(f"Processing segment {i+1}/{len(segments_info)}")
                
                # Analyze current segment with context from previous
                result = self.analyze_segment(data, segment_info, previous_segment)
                results.append(result)
                
                # Update previous segment info for context
                if result.get('_core_success', False):
                    previous_segment = {
                        'end_potential_v': result.get('end_potential_v'),
                        'end_current_a': result.get('end_current_a'),
                        'technique_name': segment_info.get('technique_name'),
                        'fundamental_technique': segment_info.get('fundamental_technique')
                    }
            
            # Log summary
            completed = sum(1 for r in results if r.get('analysis_status') == 'completed')
            partial = sum(1 for r in results if r.get('analysis_status') == 'partial')
            failed = sum(1 for r in results if r.get('analysis_status') == 'failed')
            
            self.logger.info(f"File analysis complete: {completed} completed, "
                           f"{partial} partial, {failed} failed out of {len(results)} segments")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error analyzing all segments: {e}")
            return [self._failed_analysis_result(str(e)) for _ in segments_info]
    
    def reanalyze_segment(self, data: pl.DataFrame, segment_info: Dict[str, Any],
                         force_recompute: bool = False) -> Dict[str, Any]:
        """
        Reanalyze a single segment, optionally forcing recomputation.
        
        Args:
            data: Full DataFrame with universal schema
            segment_info: Segment information including current analysis status
            force_recompute: If True, recompute even if status is 'completed'
            
        Returns:
            Updated analysis results
        """
        try:
            current_status = segment_info.get('analysis_status', 'pending')
            
            # Skip if already completed and not forcing recompute
            if current_status == 'completed' and not force_recompute:
                self.logger.debug(f"Skipping segment {segment_info.get('segment_index', '?')}: "
                                f"already completed")
                return segment_info
            
            self.logger.info(f"Reanalyzing segment {segment_info.get('segment_index', '?')}: "
                           f"current status {current_status}")
            
            # Perform fresh analysis
            return self.analyze_segment(data, segment_info)
            
        except Exception as e:
            self.logger.error(f"Error in segment reanalysis: {e}")
            return self._failed_analysis_result(str(e))
    
    def get_analysis_summary(self, analysis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary statistics for a set of analysis results.
        
        Args:
            analysis_results: List of analysis result dictionaries
            
        Returns:
            Summary statistics and quality metrics
        """
        try:
            if not analysis_results:
                return {'total_segments': 0}
            
            # Count analysis outcomes
            status_counts = {}
            for result in analysis_results:
                status = result.get('analysis_status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Calculate total metrics
            total_capacity = sum(r.get('capacity_ah', 0) or 0 for r in analysis_results)
            total_energy = sum(r.get('energy_wh', 0) or 0 for r in analysis_results)
            total_duration = sum(r.get('duration_s', 0) or 0 for r in analysis_results)
            
            # Technique distribution
            technique_counts = {}
            for result in analysis_results:
                # Extract technique from analysis_results JSON
                try:
                    analysis_json = json.loads(result.get('analysis_results', '{}'))
                    technique = analysis_json.get('analysis_type', 'unknown')
                    technique_counts[technique] = technique_counts.get(technique, 0) + 1
                except (json.JSONDecodeError, TypeError):
                    technique_counts['parse_error'] = technique_counts.get('parse_error', 0) + 1
            
            summary = {
                'total_segments': len(analysis_results),
                'status_distribution': status_counts,
                'technique_distribution': technique_counts,
                'total_capacity_ah': total_capacity,
                'total_energy_wh': total_energy,
                'total_duration_s': total_duration,
                'success_rate': status_counts.get('completed', 0) / len(analysis_results),
                'partial_rate': status_counts.get('partial', 0) / len(analysis_results),
                'failure_rate': status_counts.get('failed', 0) / len(analysis_results)
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating analysis summary: {e}")
            return {'error': str(e)}
    
    def _failed_analysis_result(self, error_message: str) -> Dict[str, Any]:
        """Generate a failed analysis result structure."""
        return {
            'start_time_s': None,
            'end_time_s': None,
            'duration_s': None,
            'start_potential_v': None,
            'end_potential_v': None,
            'start_current_a': None,
            'end_current_a': None,
            'capacity_ah': None,
            'energy_wh': None,
            'point_count': 0,
            'analysis_status': 'failed',
            'analysis_results': json.dumps({
                'analysis_type': 'failed',
                'success': False,
                'error': error_message
            }),
            '_core_success': False,
            '_technique_success': False
        }