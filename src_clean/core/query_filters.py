"""
Universal Query Filters for Registry-Based Analytics System

Standardized filtering system that replaces multiple specialized database methods
with a single, flexible query interface. Supports all filtering patterns found
in the existing 22+ database methods.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from enum import Enum


class AggregationType(Enum):
    """Statistical aggregation types for query results."""
    RAW = "raw"                    # Return raw segment data
    STATISTICS = "statistics"      # Return mean/std/min/max for numeric columns
    COUNT = "count"               # Return count only
    TEMPORAL = "temporal"         # Return time-series data
    CUSTOM = "custom"             # Custom aggregation function


class QueryScope(Enum):
    """Defines the scope of the query for performance optimization."""
    SEGMENTS_ONLY = "segments"     # Only segment table data
    WITH_GROUPS = "with_groups"    # Include group membership information  
    WITH_FILES = "with_files"      # Include file metadata
    WITH_CELLS = "with_cells"      # Include cell information
    FULL = "full"                  # All related data


@dataclass
class QueryFilters:
    """
    Universal filter specification that replaces specialized query methods.
    
    Combines all filtering patterns from existing database methods:
    - get_group_base_statistics() → group_ids + aggregation
    - get_segment_subset_statistics() → segment_ids + aggregation  
    - get_electrochemical_*_analysis() → group_ids + technique_filter
    - get_multi_group_segments() → group_ids + raw data
    - get_segments_by_technique() → technique_filter + raw data
    """
    
    # === PRIMARY FILTERS ===
    group_ids: Optional[List[Union[str, int]]] = None
    segment_ids: Optional[List[Union[str, int]]] = None
    cell_names: Optional[List[str]] = None
    file_ids: Optional[List[str]] = None
    
    # === TECHNIQUE FILTERS ===
    fundamental_techniques: Optional[List[str]] = None  # ['Rest', 'Galvanostatic', etc.]
    exclude_techniques: Optional[List[str]] = None
    
    # === TIME FILTERS ===
    start_time_min: Optional[float] = None
    start_time_max: Optional[float] = None  
    duration_min: Optional[float] = None
    duration_max: Optional[float] = None
    
    # === VOLTAGE/CURRENT FILTERS ===
    voltage_min: Optional[float] = None
    voltage_max: Optional[float] = None
    current_min: Optional[float] = None  
    current_max: Optional[float] = None
    
    # === ANALYSIS STATUS FILTERS ===
    analysis_status: Optional[List[str]] = None  # ['success', 'failed', 'pending']
    has_analysis_results: Optional[bool] = None  # Filter by JSON analysis presence
    
    # === RESULT FORMAT ===
    aggregation: AggregationType = AggregationType.RAW
    scope: QueryScope = QueryScope.SEGMENTS_ONLY
    
    # === PERFORMANCE OPTIONS ===
    limit: Optional[int] = None
    offset: Optional[int] = None
    order_by: Optional[List[str]] = None  # ['start_time_s', 'duration_s', etc.]
    
    # === CUSTOM FILTERS ===
    custom_where_clause: Optional[str] = None  # For advanced use cases
    custom_parameters: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate filter combinations and set defaults."""
        # Convert string IDs to proper types if needed
        if self.group_ids:
            self.group_ids = [int(gid) if isinstance(gid, str) and gid.isdigit() else gid 
                            for gid in self.group_ids]
        
        if self.segment_ids:
            self.segment_ids = [int(sid) if isinstance(sid, str) and sid.isdigit() else sid 
                              for sid in self.segment_ids]
        
        # Validate filter combinations
        if not any([self.group_ids, self.segment_ids, self.cell_names, 
                   self.file_ids, self.custom_where_clause]):
            raise ValueError("At least one primary filter must be specified")
        
        # Set scope based on filters if not explicitly set
        if self.scope == QueryScope.SEGMENTS_ONLY and self.group_ids:
            self.scope = QueryScope.WITH_GROUPS
    
    def to_sql_conditions(self) -> tuple[str, List[Any]]:
        """
        Convert filters to SQL WHERE clause and parameters.
        
        Returns:
            Tuple of (where_clause, parameters) for safe SQL execution
        """
        conditions = []
        parameters = []
        
        # Primary ID filters
        if self.group_ids:
            placeholders = ','.join('?' * len(self.group_ids))
            conditions.append(f"ugs.group_id IN ({placeholders})")
            parameters.extend(self.group_ids)
        
        if self.segment_ids:
            placeholders = ','.join('?' * len(self.segment_ids))
            conditions.append(f"s.id IN ({placeholders})")
            parameters.extend(self.segment_ids)
        
        if self.cell_names:
            placeholders = ','.join('?' * len(self.cell_names))
            conditions.append(f"c.name IN ({placeholders})")
            parameters.extend(self.cell_names)
        
        if self.file_ids:
            placeholders = ','.join('?' * len(self.file_ids))
            conditions.append(f"s.file_id IN ({placeholders})")
            parameters.extend(self.file_ids)
        
        # Technique filters (using direct column from segments table)
        if self.fundamental_techniques:
            placeholders = ','.join('?' * len(self.fundamental_techniques))
            conditions.append(f"s.fundamental_technique IN ({placeholders})")
            parameters.extend(self.fundamental_techniques)
        
        if self.exclude_techniques:
            placeholders = ','.join('?' * len(self.exclude_techniques))
            conditions.append(f"s.fundamental_technique NOT IN ({placeholders})")
            parameters.extend(self.exclude_techniques)
        
        # Time range filters
        if self.start_time_min is not None:
            conditions.append("s.start_time_s >= ?")
            parameters.append(self.start_time_min)
        
        if self.start_time_max is not None:
            conditions.append("s.start_time_s <= ?")
            parameters.append(self.start_time_max)
        
        if self.duration_min is not None:
            conditions.append("s.duration_s >= ?")
            parameters.append(self.duration_min)
        
        if self.duration_max is not None:
            conditions.append("s.duration_s <= ?")
            parameters.append(self.duration_max)
        
        # Voltage/current filters
        if self.voltage_min is not None:
            conditions.append("s.start_potential_v >= ?")
            parameters.append(self.voltage_min)
        
        if self.voltage_max is not None:
            conditions.append("s.end_potential_v <= ?")
            parameters.append(self.voltage_max)
        
        if self.current_min is not None:
            conditions.append("s.start_current_a >= ?")
            parameters.append(self.current_min)
        
        if self.current_max is not None:
            conditions.append("s.end_current_a <= ?")
            parameters.append(self.current_max)
        
        # Analysis status filters
        if self.analysis_status:
            placeholders = ','.join('?' * len(self.analysis_status))
            conditions.append(f"s.analysis_status IN ({placeholders})")
            parameters.extend(self.analysis_status)
        
        if self.has_analysis_results is not None:
            if self.has_analysis_results:
                conditions.append("s.analysis_results IS NOT NULL AND s.analysis_results != '{}'")
            else:
                conditions.append("(s.analysis_results IS NULL OR s.analysis_results = '{}')")
        
        # Custom filters
        if self.custom_where_clause:
            conditions.append(self.custom_where_clause)
            if self.custom_parameters:
                parameters.extend(self.custom_parameters.values())
        
        # Default filter - exclude null start times for statistics
        if self.aggregation == AggregationType.STATISTICS:
            conditions.append("s.start_time_s IS NOT NULL")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        return where_clause, parameters
    
    def get_joins(self) -> str:
        """Get required SQL JOINs based on query scope and filters - matching existing schema."""
        joins = []
        
        # Base segments table
        base_table = "segments s"
        
        # For group queries, use the same JOINs as existing get_multi_group_segments
        if self.scope in [QueryScope.WITH_GROUPS, QueryScope.FULL] or self.group_ids:
            joins.extend([
                "JOIN user_group_segments ugs ON s.id = ugs.segment_id",
                "JOIN user_groups ug ON ugs.group_id = ug.group_id",
                "LEFT JOIN files f ON s.file_id = f.file_id", 
                "LEFT JOIN cells c ON f.cell_id = c.id"
            ])
        elif self.scope in [QueryScope.WITH_FILES, QueryScope.WITH_CELLS, QueryScope.FULL]:
            joins.extend([
                "LEFT JOIN files f ON s.file_id = f.file_id",
                "LEFT JOIN cells c ON f.cell_id = c.id"
            ])
        
        if joins:
            return f"FROM {base_table} " + " ".join(joins)
        else:
            return f"FROM {base_table}"
    
    def get_order_clause(self) -> str:
        """Get SQL ORDER BY clause."""
        if self.order_by:
            return f"ORDER BY {', '.join(self.order_by)}"
        else:
            # Default ordering
            return "ORDER BY s.start_time_s ASC"
    
    def get_limit_clause(self) -> str:
        """Get SQL LIMIT/OFFSET clause."""
        clauses = []
        if self.limit:
            clauses.append(f"LIMIT {self.limit}")
        if self.offset:
            clauses.append(f"OFFSET {self.offset}")
        return " ".join(clauses)


# === CONVENIENCE CONSTRUCTORS ===

def group_filter(group_ids: List[Union[str, int]], 
                 aggregation: AggregationType = AggregationType.RAW) -> QueryFilters:
    """Create filter for group-based queries (replaces get_multi_group_segments)."""
    return QueryFilters(
        group_ids=group_ids,
        aggregation=aggregation,
        scope=QueryScope.WITH_GROUPS
    )

def segment_filter(segment_ids: List[Union[str, int]], 
                   aggregation: AggregationType = AggregationType.RAW) -> QueryFilters:
    """Create filter for segment subset queries (replaces get_segment_subset_statistics).""" 
    return QueryFilters(
        segment_ids=segment_ids,
        aggregation=aggregation
    )

def technique_filter(techniques: List[str], 
                     cell_names: Optional[List[str]] = None) -> QueryFilters:
    """Create filter for technique-based queries (replaces get_segments_by_technique)."""
    return QueryFilters(
        fundamental_techniques=techniques,
        cell_names=cell_names,
        scope=QueryScope.WITH_CELLS
    )

def statistics_filter(group_ids: List[Union[str, int]]) -> QueryFilters:
    """Create filter for statistical analysis (replaces get_group_base_statistics)."""
    return QueryFilters(
        group_ids=group_ids,
        aggregation=AggregationType.STATISTICS,
        scope=QueryScope.WITH_GROUPS
    )