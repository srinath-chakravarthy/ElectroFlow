"""
Lazy Data Service for Tab 3 Analytics

Provides Polars lazy loading capabilities for efficient multi-file data analysis
without loading entire datasets into memory until visualization is needed.
"""

import polars as pl
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from uuid import uuid4
import time

from src_clean.core.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class LazyQuery:
    """Represents a lazy query with metadata."""
    query_id: str
    lazy_frame: pl.LazyFrame
    source_files: List[str] = field(default_factory=list)
    applied_filters: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)


class LazyDataService:
    """
    Service for managing lazy Polars queries for Tab 3 data analysis.
    
    Implements the lazy loading architecture pattern:
    1. Create lazy queries without loading data
    2. Chain filters dynamically 
    3. Materialize only when visualization is needed
    """
    
    def __init__(self):
        self.config = get_config()
        self.logger = logger
        
        # Query cache with TTL cleanup
        self._query_cache: Dict[str, LazyQuery] = {}
        self._max_cache_size = 50
        self._cache_ttl_seconds = 3600  # 1 hour
    
    def create_multi_file_lazy_query(self, file_infos: List[Dict[str, Any]]) -> str:
        """
        Create a lazy query spanning multiple files.
        
        Args:
            file_infos: List of file info dicts with file_id, file_path, cell_name
            
        Returns:
            Query ID for subsequent operations
        """
        try:
            # Clean up old queries first
            self._cleanup_expired_queries()
            
            # Build file paths
            file_paths = []
            source_files = []
            
            for file_info in file_infos:
                file_path = self._resolve_file_path(file_info)
                if file_path and file_path.exists():
                    file_paths.append(str(file_path))
                    source_files.append(file_info.get('file_id', str(file_path)))
                else:
                    self.logger.warning(f"File not found: {file_path}")
            
            if not file_paths:
                raise ValueError("No valid files found for lazy query")
            
            # Create lazy scans (no data loaded yet)
            if len(file_paths) == 1:
                lazy_frame = pl.scan_parquet(file_paths[0])
            else:
                # Multi-file concatenation
                lazy_scans = [pl.scan_parquet(path) for path in file_paths]
                lazy_frame = pl.concat(lazy_scans)
            
            # Generate query ID and store
            query_id = str(uuid4())
            query = LazyQuery(
                query_id=query_id,
                lazy_frame=lazy_frame,
                source_files=source_files
            )
            
            self._query_cache[query_id] = query
            
            self.logger.debug(f"Created lazy query {query_id} for {len(file_paths)} files")
            return query_id
            
        except Exception as e:
            self.logger.error(f"Failed to create lazy query: {e}")
            raise
    
    def apply_filters_to_query(self, query_id: str, filters: Dict[str, Any]) -> str:
        """
        Apply filters to existing lazy query, creating new query.
        
        Args:
            query_id: Existing query ID
            filters: Filter conditions to apply
            
        Returns:
            New query ID with filters applied
        """
        try:
            if query_id not in self._query_cache:
                raise ValueError(f"Query {query_id} not found in cache")
            
            base_query = self._query_cache[query_id]
            base_query.last_accessed = time.time()
            
            # Start with base lazy frame
            filtered_frame = base_query.lazy_frame
            
            # Apply technique filter
            if 'techniques' in filters and filters['techniques']:
                technique_list = filters['techniques']
                if isinstance(technique_list, str):
                    technique_list = [technique_list]
                filtered_frame = filtered_frame.filter(
                    pl.col("technique_id").is_in(technique_list)
                )
            
            # Apply time range filter
            if 'time_range' in filters and filters['time_range']:
                time_min, time_max = filters['time_range']
                filtered_frame = filtered_frame.filter(
                    pl.col("time_s").is_between(time_min, time_max)
                )
            
            # Apply voltage range filter
            if 'voltage_range' in filters and filters['voltage_range']:
                voltage_min, voltage_max = filters['voltage_range']
                filtered_frame = filtered_frame.filter(
                    pl.col("potential_v").is_between(voltage_min, voltage_max)
                )
            
            # Apply current range filter
            if 'current_range' in filters and filters['current_range']:
                current_min, current_max = filters['current_range']
                filtered_frame = filtered_frame.filter(
                    pl.col("current_a").is_between(current_min, current_max)
                )
            
            # Apply segment filter
            if 'segment_ids' in filters and filters['segment_ids']:
                segment_list = filters['segment_ids']
                if isinstance(segment_list, str):
                    segment_list = [segment_list]
                filtered_frame = filtered_frame.filter(
                    pl.col("segment_number").is_in(segment_list)
                )
            
            # Create new query with filters applied
            new_query_id = str(uuid4())
            combined_filters = {**base_query.applied_filters, **filters}
            
            filtered_query = LazyQuery(
                query_id=new_query_id,
                lazy_frame=filtered_frame,
                source_files=base_query.source_files.copy(),
                applied_filters=combined_filters
            )
            
            self._query_cache[new_query_id] = filtered_query
            
            self.logger.debug(f"Applied filters to query {query_id}, created {new_query_id}")
            return new_query_id
            
        except Exception as e:
            self.logger.error(f"Failed to apply filters to query {query_id}: {e}")
            raise
    
    def materialize_query_for_viz(self, query_id: str, 
                                columns: Optional[List[str]] = None,
                                limit: Optional[int] = None) -> pl.DataFrame:
        """
        Materialize lazy query data for visualization.
        
        Args:
            query_id: Query ID to materialize
            columns: Specific columns to load (optimization)
            limit: Maximum rows to return
            
        Returns:
            Materialized Polars DataFrame
        """
        try:
            if query_id not in self._query_cache:
                raise ValueError(f"Query {query_id} not found in cache")
            
            query = self._query_cache[query_id]
            query.last_accessed = time.time()
            
            # Start with lazy frame
            materialization_frame = query.lazy_frame
            
            # Select specific columns if requested
            if columns:
                # Validate columns exist by trying to select them
                materialization_frame = materialization_frame.select(columns)
            
            # Apply limit if specified
            if limit:
                materialization_frame = materialization_frame.limit(limit)
            
            # NOW materialize the data (this is where data is actually loaded)
            start_time = time.time()
            df = materialization_frame.collect()
            materialization_time = time.time() - start_time
            
            self.logger.debug(
                f"Materialized query {query_id}: {df.height} rows, "
                f"{df.width} columns in {materialization_time:.3f}s"
            )
            
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to materialize query {query_id}: {e}")
            raise
    
    def get_query_info(self, query_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a cached query."""
        if query_id not in self._query_cache:
            return None
        
        query = self._query_cache[query_id]
        return {
            'query_id': query.query_id,
            'source_files': query.source_files,
            'applied_filters': query.applied_filters,
            'created_at': query.created_at,
            'last_accessed': query.last_accessed
        }
    
    def cleanup_query(self, query_id: str) -> bool:
        """Remove specific query from cache."""
        if query_id in self._query_cache:
            del self._query_cache[query_id]
            self.logger.debug(f"Cleaned up query {query_id}")
            return True
        return False
    
    def get_cached_query_count(self) -> int:
        """Get number of cached queries."""
        return len(self._query_cache)
    
    def get_segment_raw_data(self, segment_id: str) -> pl.DataFrame:
        """
        Get raw data for specific segment ID.
        
        Args:
            segment_id: Target segment identifier
            
        Returns:
            Raw electrochemical data for the segment
        """
        try:
            from src_clean.core.database import DatabaseManager
            
            # Get segment file info from database
            db_manager = DatabaseManager(self.config.db_path)
            segment_info = db_manager.get_segment_file_info(segment_id)
            
            if not segment_info:
                self.logger.warning(f"No file info found for segment {segment_id}")
                return pl.DataFrame()
            
            # Get file path for the segment
            file_path = self._resolve_segment_file_path(segment_info)
            if not file_path:
                self.logger.warning(f"Could not resolve file path for segment {segment_id}")
                return pl.DataFrame()
            
            # Create lazy query for the specific file
            lazy_frame = pl.scan_parquet(str(file_path))
            
            # Filter for the specific segment using row range
            start_row = segment_info.get('start_row', 0)
            end_row = segment_info.get('end_row', 0)
            
            if start_row >= 0 and end_row > start_row:
                # Use slice for row-based filtering (Polars uses 0-based indexing)
                segment_data = lazy_frame.slice(start_row, end_row - start_row).collect()
            else:
                self.logger.warning(f"Invalid row range for segment {segment_id}: {start_row}-{end_row}")
                return pl.DataFrame()
            
            self.logger.debug(f"Loaded segment {segment_id} data: {segment_data.shape}")
            return segment_data
            
        except Exception as e:
            self.logger.error(f"Failed to get segment raw data: {e}")
            return pl.DataFrame()
    
    def _resolve_segment_file_path(self, segment_info: Dict[str, Any]) -> Optional[Path]:
        """Resolve file path from segment file info."""
        try:
            cell_name = segment_info.get('cell_name', '')
            file_id = segment_info.get('file_id', '')
            
            if not cell_name or not file_id:
                return None
            
            # Use standard processed file path
            file_path = (
                self.config.data_dir / cell_name / 'processed' / f"{file_id}.parquet"
            )
            
            if file_path.exists():
                return file_path
            
            # Try legacy path structure
            legacy_path = self.config.data_dir / "processed" / f"{file_id}.parquet"
            if legacy_path.exists():
                return legacy_path
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to resolve segment file path: {e}")
            return None
    
    def _resolve_file_path(self, file_info: Dict[str, Any]) -> Optional[Path]:
        """Resolve file path from file info."""
        # Try direct path first
        if 'file_path' in file_info:
            file_path = Path(file_info['file_path'])
            if file_path.exists():
                return file_path
        
        # Construct path from config
        cell_name = file_info.get('cell_name', '')
        file_id = file_info.get('file_id', '')
        
        if cell_name and file_id:
            constructed_path = (
                self.config.data_dir / cell_name / 'processed' / f"{file_id}.parquet"
            )
            if constructed_path.exists():
                return constructed_path
        
        return None
    
    def _cleanup_expired_queries(self):
        """Remove expired queries from cache."""
        current_time = time.time()
        expired_queries = []
        
        for query_id, query in self._query_cache.items():
            if current_time - query.last_accessed > self._cache_ttl_seconds:
                expired_queries.append(query_id)
        
        for query_id in expired_queries:
            del self._query_cache[query_id]
        
        if expired_queries:
            self.logger.debug(f"Cleaned up {len(expired_queries)} expired queries")
        
        # Also enforce max cache size
        if len(self._query_cache) > self._max_cache_size:
            # Remove oldest queries
            sorted_queries = sorted(
                self._query_cache.items(),
                key=lambda x: x[1].last_accessed
            )
            
            queries_to_remove = len(self._query_cache) - self._max_cache_size
            for i in range(queries_to_remove):
                query_id = sorted_queries[i][0]
                del self._query_cache[query_id]
            
            self.logger.debug(f"Cleaned up {queries_to_remove} queries due to cache size limit")


# Global instance
_lazy_data_service = LazyDataService()

def get_lazy_data_service() -> LazyDataService:
    """Get global lazy data service instance."""
    return _lazy_data_service