"""
Cumulative Analytics Calculator

Provides on-demand file boundary data reading and cumulative calculations
for group-level analytics that span multiple files.
"""

import polars as pl
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import logging
from dataclasses import dataclass, field
from collections import defaultdict

from src_clean.core.config import get_config
from src_clean.analysis.analytics_config import get_config as get_analytics_config

logger = logging.getLogger(__name__)


@dataclass
class FileBoundaryData:
    """Data structure for file boundary information."""
    file_id: str
    file_path: Path
    last_row_data: Dict[str, Any]
    second_last_row_data: Dict[str, Any]
    total_rows: int
    acquisition_end_time: float
    
    # Cumulative values at file end
    cumulative_capacity_ah: float = 0.0
    cumulative_energy_wh: float = 0.0
    cumulative_duration_s: float = 0.0
    cumulative_abs_capacity_ah: float = 0.0


@dataclass
class CellCumulativeContext:
    """Context for cumulative calculations across a cell's files."""
    cell_name: str
    file_boundaries: List[FileBoundaryData] = field(default_factory=list)
    timeline_established: bool = False
    total_experiment_duration: float = 0.0


class CumulativeCalculator:
    """
    Calculator for cumulative analytics across file boundaries.
    
    Implements on-demand reading of file boundary data (last 2 rows) with
    in-memory caching for efficient group-level temporal analytics.
    """
    
    def __init__(self):
        self.config = get_config()
        self.analytics_config = get_analytics_config()
        self.logger = logger
        
        # In-memory cache for file boundary data
        self._cell_contexts: Dict[str, CellCumulativeContext] = {}
        self._cache_valid = True
    
    def get_group_cumulative_context(self, group_files: List[Dict[str, Any]]) -> CellCumulativeContext:
        """
        Get or build cumulative context for a group's files.
        
        Args:
            group_files: List of file dictionaries with file_id, file_path, cell_name
            
        Returns:
            CellCumulativeContext with file boundaries and cumulative data
        """
        if not group_files:
            return CellCumulativeContext(cell_name="unknown")
        
        # Assume all files belong to same cell (groups are per-cell)
        cell_name = group_files[0].get('cell_name', 'unknown')
        
        # Check cache
        if cell_name in self._cell_contexts and self._cache_valid:
            context = self._cell_contexts[cell_name]
            # Verify cache covers all requested files
            cached_file_ids = {fb.file_id for fb in context.file_boundaries}
            requested_file_ids = {f['file_id'] for f in group_files}
            
            if requested_file_ids.issubset(cached_file_ids):
                return context
        
        # Build new context
        context = self._build_cell_context(cell_name, group_files)
        self._cell_contexts[cell_name] = context
        
        return context
    
    def _build_cell_context(self, cell_name: str, group_files: List[Dict[str, Any]]) -> CellCumulativeContext:
        """
        Build cumulative context by reading file boundaries.
        
        Args:
            cell_name: Name of the cell
            group_files: List of file information dictionaries
            
        Returns:
            Complete CellCumulativeContext
        """
        context = CellCumulativeContext(cell_name=cell_name)
        
        try:
            # Sort files by acquisition time or file_id for proper chronological order
            sorted_files = sorted(group_files, key=lambda f: f.get('original_filename', f['file_id']))
            
            running_capacity = 0.0
            running_energy = 0.0
            running_duration = 0.0
            running_abs_capacity = 0.0
            
            for file_info in sorted_files:
                boundary_data = self._read_file_boundary(file_info)
                if boundary_data is None:
                    continue
                
                # Calculate cumulative values at end of this file
                file_capacity = boundary_data.last_row_data.get('cumulative_capacity_ah', 0.0)
                file_energy = boundary_data.last_row_data.get('cumulative_energy_wh', 0.0)
                file_duration = boundary_data.last_row_data.get('time_s', 0.0)
                
                # If file doesn't have cumulative values, use segment-based calculation
                if file_capacity == 0.0:
                    file_capacity = self._estimate_file_capacity(file_info)
                if file_energy == 0.0:
                    file_energy = self._estimate_file_energy(file_info)
                
                boundary_data.cumulative_capacity_ah = running_capacity + file_capacity
                boundary_data.cumulative_energy_wh = running_energy + file_energy
                boundary_data.cumulative_duration_s = running_duration + file_duration
                boundary_data.cumulative_abs_capacity_ah = running_abs_capacity + abs(file_capacity)
                
                context.file_boundaries.append(boundary_data)
                
                # Update running totals for next file
                running_capacity = boundary_data.cumulative_capacity_ah
                running_energy = boundary_data.cumulative_energy_wh
                running_duration = boundary_data.cumulative_duration_s
                running_abs_capacity = boundary_data.cumulative_abs_capacity_ah
            
            context.timeline_established = True
            context.total_experiment_duration = running_duration
            
        except Exception as e:
            self.logger.error(f"Failed to build cumulative context for cell {cell_name}: {e}")
            # Return empty context on failure
            context.timeline_established = False
        
        return context
    
    def _read_file_boundary(self, file_info: Dict[str, Any]) -> Optional[FileBoundaryData]:
        """
        Read last 2 rows of a file to extract boundary data.
        
        Args:
            file_info: File information dictionary
            
        Returns:
            FileBoundaryData or None if reading fails
        """
        try:
            file_path = Path(file_info.get('file_path', ''))
            if not file_path.exists():
                # Try to construct path from config
                cell_name = file_info.get('cell_name', '')
                file_id = file_info['file_id']
                file_path = self.config.data_dir / cell_name / 'processed' / f"{file_id}.parquet"
            
            if not file_path.exists():
                self.logger.warning(f"File not found: {file_path}")
                return None
            
            # Read only last 2 rows efficiently
            df = pl.read_parquet(file_path)
            total_rows = df.height
            
            if total_rows < 2:
                self.logger.warning(f"File {file_path} has insufficient rows: {total_rows}")
                return None
            
            # Get last 2 rows
            last_rows = df.tail(2)
            last_row = last_rows.row(-1, named=True)
            second_last_row = last_rows.row(-2, named=True)
            
            # Extract acquisition end time
            acquisition_end_time = last_row.get('time_s', 0.0)
            
            boundary_data = FileBoundaryData(
                file_id=file_info['file_id'],
                file_path=file_path,
                last_row_data=last_row,
                second_last_row_data=second_last_row,
                total_rows=total_rows,
                acquisition_end_time=acquisition_end_time
            )
            
            return boundary_data
            
        except Exception as e:
            self.logger.error(f"Failed to read boundary data for file {file_info.get('file_id', 'unknown')}: {e}")
            return None
    
    def _estimate_file_capacity(self, file_info: Dict[str, Any]) -> float:
        """
        Estimate total file capacity from segment data if raw cumulative not available.
        
        Args:
            file_info: File information dictionary
            
        Returns:
            Estimated total capacity for the file
        """
        # This would typically query the database for segments in this file
        # For now, return 0.0 as placeholder - would need database connection
        return 0.0
    
    def _estimate_file_energy(self, file_info: Dict[str, Any]) -> float:
        """
        Estimate total file energy from segment data if raw cumulative not available.
        
        Args:
            file_info: File information dictionary
            
        Returns:
            Estimated total energy for the file
        """
        # This would typically query the database for segments in this file
        # For now, return 0.0 as placeholder - would need database connection
        return 0.0
    
    def calculate_segment_cumulative_values(self, segment_data: Dict[str, Any], 
                                          context: CellCumulativeContext) -> Dict[str, Any]:
        """
        Calculate cumulative values for a specific segment within cell context.
        
        Args:
            segment_data: Segment data dictionary
            context: Cell cumulative context
            
        Returns:
            Dictionary with calculated cumulative values
        """
        cumulative_values = {}
        
        try:
            segment_file_id = segment_data.get('file_id', '')
            segment_start_time = segment_data.get('start_time_s', 0.0)
            
            # Find the file boundary data for this segment's file
            file_boundary = None
            for fb in context.file_boundaries:
                if fb.file_id == segment_file_id:
                    file_boundary = fb
                    break
            
            if file_boundary is None:
                self.logger.warning(f"No boundary data found for file {segment_file_id}")
                return {}
            
            # Calculate cumulative values based on segment position within file timeline
            segment_capacity = segment_data.get('capacity_ah', 0.0)
            segment_energy = segment_data.get('energy_wh', 0.0)
            segment_duration = segment_data.get('duration_s', 0.0)
            
            # Get cumulative offset from previous files
            file_index = context.file_boundaries.index(file_boundary)
            prev_cumulative_capacity = 0.0
            prev_cumulative_energy = 0.0
            prev_cumulative_duration = 0.0
            
            if file_index > 0:
                prev_boundary = context.file_boundaries[file_index - 1]
                prev_cumulative_capacity = prev_boundary.cumulative_capacity_ah
                prev_cumulative_energy = prev_boundary.cumulative_energy_wh
                prev_cumulative_duration = prev_boundary.cumulative_duration_s
            
            # Add segment position within file
            # This is simplified - would need more sophisticated calculation for exact positioning
            cumulative_values = {
                'cumulative_capacity_ah': prev_cumulative_capacity + segment_capacity,
                'cumulative_energy_wh': prev_cumulative_energy + segment_energy,
                'cumulative_duration_s': prev_cumulative_duration + segment_start_time,
                'cumulative_time_s': segment_start_time,  # This would need absolute timestamp calculation
                'cumulative_abs_capacity_ah': prev_cumulative_capacity + abs(segment_capacity)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate cumulative values for segment: {e}")
        
        return cumulative_values
    
    def get_cumulative_field_names(self) -> List[str]:
        """
        Get list of all cumulative field names from analytics config.
        
        Returns:
            List of cumulative field names
        """
        config = self.analytics_config
        cumulative_fields = list(config.get('segment_cumulative_fields', {}).keys())
        
        # Also check for any fields with 'cumulative' in the name
        base_fields = config.get('segment_base_fields', {})
        for field_name in base_fields.keys():
            if 'cumulative' in field_name.lower() and field_name not in cumulative_fields:
                cumulative_fields.append(field_name)
        
        return cumulative_fields
    
    def invalidate_cache(self, cell_name: Optional[str] = None):
        """
        Invalidate cumulative calculation cache.
        
        Args:
            cell_name: Specific cell to invalidate, or None for all cells
        """
        if cell_name:
            self._cell_contexts.pop(cell_name, None)
        else:
            self._cell_contexts.clear()
            self._cache_valid = False
        
        self.logger.debug(f"Cumulative cache invalidated for cell: {cell_name or 'all'}")


# Global instance
_calculator = CumulativeCalculator()

def get_cumulative_calculator() -> CumulativeCalculator:
    """Get global cumulative calculator instance."""
    return _calculator