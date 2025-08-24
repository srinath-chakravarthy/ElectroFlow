"""
Universal Query Engine for Registry-Based Analytics System

Replaces 22+ specialized database methods with a single, flexible query system.
Handles all segment-related queries with standardized filtering, aggregation,
and result formatting.

This engine consolidates:
- get_group_base_statistics() (60 lines of SQL)
- get_segment_subset_statistics() (60 lines of IDENTICAL SQL) 
- get_multi_group_segments() 
- get_segments_by_technique()
- get_file_segments()
- get_cell_segments_with_groups()
- And 15+ other similar methods
"""

import sqlite3
import pandas as pd
from typing import List, Dict, Any, Optional, Union
from dataclasses import asdict
import json
from pathlib import Path

from .query_filters import QueryFilters, AggregationType, QueryScope
from .database import DatabaseManager
from .config import get_config


class QueryEngine:
    """
    Universal query engine that replaces specialized database methods.
    
    Single entry point for all segment-related data access with flexible
    filtering, aggregation, and formatting options.
    """
    
    def __init__(self, database_manager: DatabaseManager):
        """Initialize with database connection."""
        self.db = database_manager
        self.config = get_config()
    
    def execute_query(self, filters: QueryFilters) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Execute query with given filters and return formatted results.
        
        This single method replaces 22+ specialized database methods by
        handling different aggregation types and result formats.
        
        Args:
            filters: QueryFilters object specifying what data to retrieve
            
        Returns:
            - RAW: List of segment dictionaries  
            - STATISTICS: Dict with aggregated statistics
            - COUNT: Dict with count information
            - TEMPORAL: List with time-series data
        """
        
        if filters.aggregation == AggregationType.RAW:
            return self._execute_raw_query(filters)
        elif filters.aggregation == AggregationType.STATISTICS:
            return self._execute_statistics_query(filters)
        elif filters.aggregation == AggregationType.COUNT:
            return self._execute_count_query(filters)
        elif filters.aggregation == AggregationType.TEMPORAL:
            return self._execute_temporal_query(filters)
        else:
            raise ValueError(f"Unsupported aggregation type: {filters.aggregation}")
    
    def _execute_raw_query(self, filters: QueryFilters) -> List[Dict[str, Any]]:
        """
        Execute raw data query returning full segment information.
        
        Replaces methods like:
        - get_multi_group_segments()
        - get_segment_subset() 
        - get_file_segments()
        - get_segments_by_technique()
        """
        
        # Build SELECT clause based on scope
        select_columns = self._get_select_columns(filters.scope)
        joins = filters.get_joins()
        where_clause, parameters = filters.to_sql_conditions()
        order_clause = filters.get_order_clause() 
        limit_clause = filters.get_limit_clause()
        
        # Add GROUP BY for GROUP_CONCAT when using groups
        group_by_clause = ""
        if "GROUP_CONCAT" in select_columns:
            group_by_clause = "GROUP BY s.id"
        
        query = f"""
        SELECT DISTINCT {select_columns}
        {joins}
        WHERE {where_clause}
        {group_by_clause}
        {order_clause}
        {limit_clause}
        """
        
        with self.db.get_connection() as conn:
            cursor = conn.execute(query.strip(), parameters)
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
        
        # Convert to list of dictionaries
        results = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            
            # Parse JSON analysis_results if present
            if 'analysis_results' in row_dict and row_dict['analysis_results']:
                try:
                    row_dict['analysis_results'] = json.loads(row_dict['analysis_results'])
                except (json.JSONDecodeError, TypeError):
                    row_dict['analysis_results'] = {}
            else:
                row_dict['analysis_results'] = {}
                
            results.append(row_dict)
        
        return results
    
    def _execute_statistics_query(self, filters: QueryFilters) -> Dict[str, Dict[str, float]]:
        """
        Execute statistical aggregation query.
        
        Replaces methods like:
        - get_group_base_statistics() (60 lines of SQL)
        - get_segment_subset_statistics() (IDENTICAL 60 lines of SQL)
        
        Returns the same format as existing methods for compatibility.
        """
        
        joins = filters.get_joins()
        where_clause, parameters = filters.to_sql_conditions()
        
        # Statistical aggregation query (consolidated from 2 identical methods)
        query = f"""
        SELECT 
            -- Time statistics
            AVG(s.start_time_s) as avg_start_time,
            SQRT(MAX(0, AVG(s.start_time_s * s.start_time_s) - AVG(s.start_time_s) * AVG(s.start_time_s))) as std_start_time,
            MIN(s.start_time_s) as min_start_time,
            MAX(s.start_time_s) as max_start_time,
            
            AVG(s.duration_s) as avg_duration,
            SQRT(MAX(0, AVG(s.duration_s * s.duration_s) - AVG(s.duration_s) * AVG(s.duration_s))) as std_duration,
            MIN(s.duration_s) as min_duration,
            MAX(s.duration_s) as max_duration,
            
            -- Voltage statistics  
            AVG(s.start_potential_v) as avg_start_potential,
            SQRT(MAX(0, AVG(s.start_potential_v * s.start_potential_v) - AVG(s.start_potential_v) * AVG(s.start_potential_v))) as std_start_potential,
            MIN(s.start_potential_v) as min_start_potential,
            MAX(s.start_potential_v) as max_start_potential,
            
            AVG(s.end_potential_v) as avg_end_potential,
            SQRT(MAX(0, AVG(s.end_potential_v * s.end_potential_v) - AVG(s.end_potential_v) * AVG(s.end_potential_v))) as std_end_potential,
            MIN(s.end_potential_v) as min_end_potential,
            MAX(s.end_potential_v) as max_end_potential,
            
            -- Current statistics
            AVG(s.start_current_a) as avg_start_current,
            SQRT(MAX(0, AVG(s.start_current_a * s.start_current_a) - AVG(s.start_current_a) * AVG(s.start_current_a))) as std_start_current,
            MIN(s.start_current_a) as min_start_current,
            MAX(s.start_current_a) as max_start_current,
            
            AVG(s.end_current_a) as avg_end_current,
            SQRT(MAX(0, AVG(s.end_current_a * s.end_current_a) - AVG(s.end_current_a) * AVG(s.end_current_a))) as std_end_current,
            MIN(s.end_current_a) as min_end_current,
            MAX(s.end_current_a) as max_end_current,
            
            -- Energy/Capacity statistics
            AVG(s.capacity_ah) as avg_capacity,
            SQRT(MAX(0, AVG(s.capacity_ah * s.capacity_ah) - AVG(s.capacity_ah) * AVG(s.capacity_ah))) as std_capacity,
            MIN(s.capacity_ah) as min_capacity,
            MAX(s.capacity_ah) as max_capacity,
            
            AVG(s.energy_wh) as avg_energy,
            SQRT(MAX(0, AVG(s.energy_wh * s.energy_wh) - AVG(s.energy_wh) * AVG(s.energy_wh))) as std_energy,
            MIN(s.energy_wh) as min_energy,
            MAX(s.energy_wh) as max_energy,
            
            -- Point count statistics
            AVG(s.point_count) as avg_points,
            SQRT(MAX(0, AVG(s.point_count * s.point_count) - AVG(s.point_count) * AVG(s.point_count))) as std_points,
            MIN(s.point_count) as min_points,
            MAX(s.point_count) as max_points,
            
            COUNT(*) as total_count
        {joins}
        WHERE {where_clause}
        """
        
        with self.db.get_connection() as conn:
            cursor = conn.execute(query.strip(), parameters)
            row = cursor.fetchone()
        
        if not row or row[-1] == 0:  # total_count is 0
            return {}
        
        # Build statistics dictionary matching existing format
        stats = {
            "start_time_s": {
                "mean": row[0] or 0.0,
                "std": row[1] or 0.0,
                "min": row[2] or 0.0,
                "max": row[3] or 0.0,
                "count": int(row[-1])
            },
            "duration_s": {
                "mean": row[4] or 0.0,
                "std": row[5] or 0.0,
                "min": row[6] or 0.0,
                "max": row[7] or 0.0,
                "count": int(row[-1])
            },
            "start_potential_v": {
                "mean": row[8] or 0.0,
                "std": row[9] or 0.0,
                "min": row[10] or 0.0,
                "max": row[11] or 0.0,
                "count": int(row[-1])
            },
            "end_potential_v": {
                "mean": row[12] or 0.0,
                "std": row[13] or 0.0,
                "min": row[14] or 0.0,
                "max": row[15] or 0.0,
                "count": int(row[-1])
            },
            "start_current_a": {
                "mean": row[16] or 0.0,
                "std": row[17] or 0.0,
                "min": row[18] or 0.0,
                "max": row[19] or 0.0,
                "count": int(row[-1])
            },
            "end_current_a": {
                "mean": row[20] or 0.0,
                "std": row[21] or 0.0,
                "min": row[22] or 0.0,
                "max": row[23] or 0.0,
                "count": int(row[-1])
            },
            "capacity_ah": {
                "mean": row[24] or 0.0,
                "std": row[25] or 0.0,
                "min": row[26] or 0.0,
                "max": row[27] or 0.0,
                "count": int(row[-1])
            },
            "energy_wh": {
                "mean": row[28] or 0.0,
                "std": row[29] or 0.0,
                "min": row[30] or 0.0,
                "max": row[31] or 0.0,
                "count": int(row[-1])
            },
            "point_count": {
                "mean": row[32] or 0.0,
                "std": row[33] or 0.0,
                "min": row[34] or 0.0,
                "max": row[35] or 0.0,
                "count": int(row[-1])
            }
        }
        
        return stats
    
    def _execute_count_query(self, filters: QueryFilters) -> Dict[str, Any]:
        """Execute count query for quick statistics."""
        
        joins = filters.get_joins()
        where_clause, parameters = filters.to_sql_conditions()
        
        query = f"""
        SELECT 
            COUNT(*) as segment_count,
            COUNT(DISTINCT ugs.group_id) as group_count,
            COUNT(DISTINCT s.file_id) as file_count,
            COUNT(DISTINCT s.fundamental_technique) as technique_count
        {joins}  
        WHERE {where_clause}
        """
        
        with self.db.get_connection() as conn:
            cursor = conn.execute(query.strip(), parameters)
            row = cursor.fetchone()
        
        return {
            "segment_count": row[0] if row else 0,
            "group_count": row[1] if row else 0,
            "file_count": row[2] if row else 0,
            "technique_count": row[3] if row else 0
        }
    
    def _execute_temporal_query(self, filters: QueryFilters) -> List[Dict[str, Any]]:
        """
        Execute temporal query for time-series analysis.
        
        Returns data ordered by time with additional temporal context.
        """
        # Force temporal ordering
        filters.order_by = ['s.start_time_s', 's.id']
        
        # Get raw data 
        segments = self._execute_raw_query(filters)
        
        # Add temporal analysis fields
        for i, segment in enumerate(segments):
            segment['sequence_number'] = i + 1
            segment['time_from_start'] = (segment['start_time_s'] - segments[0]['start_time_s'] 
                                        if segments else 0)
        
        return segments
    
    def _get_select_columns(self, scope: QueryScope) -> str:
        """Get SELECT columns based on query scope."""
        
        # Base segment columns (always included) - matching existing database schema
        base_columns = [
            "s.id", "s.file_id", "s.segment_index", "s.technique_id",
            "s.start_row", "s.end_row", "s.start_time_s", "s.end_time_s", "s.duration_s", 
            "s.start_potential_v", "s.end_potential_v",
            "s.start_current_a", "s.end_current_a",
            "s.capacity_ah", "s.energy_wh", "s.point_count",
            "s.analysis_status", "s.analysis_results",
            "s.fundamental_technique"  # Available directly in segments table
        ]
        
        columns = base_columns.copy()
        
        if scope in [QueryScope.WITH_GROUPS, QueryScope.FULL]:
            columns.extend([
                "f.original_filename", "f.acquisition_start",
                "c.name as cell_name",
                "GROUP_CONCAT(ug.group_name, ', ') as group_names"
            ])
        
        if scope in [QueryScope.WITH_FILES, QueryScope.FULL]:
            columns.extend([
                "f.original_filename", "f.acquisition_start"
            ])
        
        if scope in [QueryScope.WITH_CELLS, QueryScope.FULL]:
            columns.extend([
                "c.name as cell_name"
            ])
        
        # fundamental_technique appears to be already available in the segments view
        # so we don't need to join to fundamental_techniques table
        
        return ", ".join(columns)


# === GLOBAL INSTANCE ===

_query_engine = None

def get_query_engine() -> QueryEngine:
    """Get global query engine instance."""
    global _query_engine
    if _query_engine is None:
        config = get_config()
        db_manager = DatabaseManager(config.db_path)
        _query_engine = QueryEngine(db_manager)
    return _query_engine


# === CONVENIENCE FUNCTIONS ===
# These replace the specialized database methods with simple function calls

def get_segments_data(filters: QueryFilters) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Universal segments data retrieval function.
    
    This single function replaces 22+ specialized database methods:
    - get_group_base_statistics() 
    - get_segment_subset_statistics()
    - get_multi_group_segments()
    - get_file_segments()
    - get_segments_by_technique() 
    - get_cell_segments_with_groups()
    - And 15+ others
    
    Usage:
        # Raw segment data (replaces get_multi_group_segments)
        segments = get_segments_data(group_filter([1, 2, 3]))
        
        # Statistics (replaces get_group_base_statistics) 
        stats = get_segments_data(statistics_filter([1, 2, 3]))
        
        # Technique filtering (replaces get_segments_by_technique)
        rest_segments = get_segments_data(technique_filter(['Rest']))
    """
    engine = get_query_engine()
    return engine.execute_query(filters)