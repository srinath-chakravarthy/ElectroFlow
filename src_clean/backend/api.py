"""
Clean Backend API - Electrochemical Analysis Suite

Minimal, testable backend orchestration with atomic operations.

Key Principles:
- Single responsibility methods
- Atomic database operations
- Clean error handling
- Multi-interface support (Qt, CLI, Jupyter)
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import polars as pl
import pandas as pd

from src_clean.core import DatabaseManager, format_error_for_user, is_user_error
from src_clean.core.data_models import DataFile
from src_clean.core.config import get_config
from .data_migration import DataMigrationManager
from src_clean.core.exceptions import (
    ElectrochemicalAnalysisError, DatabaseError, ProcessingError,
    RecordNotFoundError
)
from src_clean.parsers import get_parser_factory, auto_parse_dual_files
from src_clean.analysis import FundamentalAnalytics
from src_clean.backend.lazy_data_service import get_lazy_data_service
from src_clean.analysis.registry import get_analysis_registry

logger = logging.getLogger(__name__)


class ProcessingResult:
    """Result of file processing operation."""
    
    def __init__(self, success: bool, file_id: str = "", message: str = "", 
                 error: str = "", data: Optional[pl.DataFrame] = None):
        self.success = success
        self.file_id = file_id
        self.message = message
        self.error = error
        self.data = data  # In-memory data for immediate use
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'success': self.success,
            'file_id': self.file_id,
            'message': self.message,
            'error': self.error,
            'has_data': self.data is not None
        }


class BackendAPI:
    """
    Clean backend API for electrochemical data analysis.
    
    Provides atomic operations for cell management, file processing,
    and data access with proper error handling.
    """
    
    def __init__(self, data_dir: Path = None, db_path: Path = None):
        """Initialize backend API with configuration support."""
        # Use configuration system if no explicit paths provided
        config = get_config()
        
        self.data_dir = Path(data_dir) if data_dir else config.data_dir
        self.db_path = Path(db_path) if db_path else config.db_path
        
        # Ensure all required directories exist using config
        config.ensure_directories()
        
        # Create legacy processed directory for backward compatibility
        (self.data_dir / "processed").mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.db = DatabaseManager(self.db_path)
        self.parser_factory = get_parser_factory()
        self.migration_manager = DataMigrationManager()
        self.analytics_engine = FundamentalAnalytics()
        self.lazy_data_service = get_lazy_data_service()
        self.analysis_registry = get_analysis_registry()
        
        logger.info(f"Backend API initialized - Data: {self.data_dir}, DB: {self.db_path}")
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Configuration: {config}")
    
    # =============================================================================
    # CELL MANAGEMENT
    # =============================================================================
    
    def create_cell(self, name: str, **kwargs) -> ProcessingResult:
        """
        Create new experimental cell.
        
        Args:
            name: Cell name (must be unique)
            **kwargs: Optional cell metadata (chemistry, capacity_ah, etc.)
            
        Returns:
            ProcessingResult with cell creation status
        """
        try:
            cell_id = self.db.create_cell(name=name, **kwargs)
            
            # Automatically create directory structure for new cell
            dir_result = self.ensure_cell_directory_structure(name)
            if not dir_result.success:
                logger.warning(f"Cell created but directory structure failed: {dir_result.error}")
                return ProcessingResult(
                    success=True,
                    file_id=str(cell_id),
                    message=f"Cell '{name}' created successfully (directory structure warning: {dir_result.error})"
                )
            
            return ProcessingResult(
                success=True,
                file_id=str(cell_id),
                message=f"Cell '{name}' created successfully with directory structure"
            )
            
        except Exception as e:
            error_info = format_error_for_user(e)
            return ProcessingResult(
                success=False,
                error=error_info['message']
            )
    
    def get_cells(self) -> List[Dict[str, Any]]:
        """Get all cells with metadata."""
        try:
            return self.db.get_all_cells()
        except Exception as e:
            logger.error(f"Failed to get cells: {e}")
            return []
    
    def get_cell_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get cell by name."""
        try:
            return self.db.get_cell_by_name(name)
        except Exception as e:
            logger.error(f"Failed to get cell '{name}': {e}")
            return None
    
    def delete_cell(self, cell_id: int) -> ProcessingResult:
        """Delete cell and all associated data (files + directories + database)."""
        try:
            # Get cell info first
            cell = self.db.get_cell_by_id(cell_id)
            if not cell:
                return ProcessingResult(
                    success=False,
                    error=f"Cell {cell_id} not found"
                )
            
            cell_name = cell['name']
            
            # Get all files for the cell to delete them properly
            files = self.db.get_cell_files(cell_id)
            
            deleted_file_count = 0
            failed_file_deletions = []
            
            # Delete each file (this handles raw files + parquet + triggers segment CASCADE)
            for file_info in files:
                file_id = file_info['file_id']
                result = self.delete_file(file_id)
                
                if result.success:
                    deleted_file_count += 1
                    logger.info(f"Successfully deleted file: {file_id}")
                else:
                    failed_file_deletions.append(f"{file_id}: {result.error}")
                    logger.error(f"Failed to delete file {file_id}: {result.error}")
            
            # Delete empty cell directory structure
            from src_clean.core.config import get_config
            config = get_config()
            cell_dir = config.get_cell_directory(cell_name)
            
            directory_deleted = False
            if cell_dir.exists():
                try:
                    # Remove entire cell directory tree
                    import shutil
                    shutil.rmtree(cell_dir)
                    directory_deleted = True
                    logger.info(f"Deleted cell directory: {cell_dir}")
                except Exception as e:
                    logger.warning(f"Failed to delete cell directory {cell_dir}: {e}")
            
            # Delete cell from database (CASCADE will handle remaining user_groups and user_group_segments)
            db_success = self.db.delete_cell(cell_id)
            
            if db_success:
                message_parts = [f"Deleted cell '{cell_name}' (ID: {cell_id})"]
                if deleted_file_count > 0:
                    message_parts.append(f"Removed {deleted_file_count} files")
                if directory_deleted:
                    message_parts.append("Removed cell directory")
                if failed_file_deletions:
                    message_parts.append(f"Had {len(failed_file_deletions)} file deletion errors")
                
                return ProcessingResult(
                    success=True,
                    file_id=str(cell_id),
                    message="; ".join(message_parts)
                )
            else:
                return ProcessingResult(
                    success=False,
                    error=f"Failed to delete cell {cell_id} from database"
                )
                
        except Exception as e:
            error_info = format_error_for_user(e)
            return ProcessingResult(
                success=False,
                error=f"Failed to delete cell {cell_id}: {error_info['message']}"
            )
    
    # =============================================================================
    # FILE PROCESSING
    # =============================================================================
    
    def process_dual_files(self, metadata_path: Path, data_path: Path, 
                          cell_name: str, **options) -> ProcessingResult:
        """
        Process dual files (.par + .par.csv) atomically.
        
        Args:
            metadata_path: Path to .par file
            data_path: Path to .par.csv file
            cell_name: Target cell name
            **options: Processing options (temperature_c, etc.)
            
        Returns:
            ProcessingResult with processed data
        """
        try:
            # Get or create cell
            cell = self.get_cell_by_name(cell_name)
            if not cell:
                create_result = self.create_cell(cell_name)
                if not create_result.success:
                    return create_result
                cell = self.get_cell_by_name(cell_name)
            
            # Ensure files are in the correct cell directory structure
            logger.info(f"Ensuring proper file storage for cell: {cell_name}")
            standardized_metadata_path, standardized_data_path = self.migration_manager.copy_raw_files_to_cell(
                cell_name, metadata_path, data_path
            )
            
            # Parse files using auto-detection with standardized paths
            data_file = auto_parse_dual_files(standardized_metadata_path, standardized_data_path)
            
            # Generate unique file ID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_id = f"{cell_name}_{metadata_path.stem}_{timestamp}"
            
            # Store processed data atomically
            self._store_data_file_atomic(data_file, file_id, cell, metadata_path, data_path, options)
            
            # Generate summary
            summary = self._generate_processing_summary(data_file)
            
            # Automatically refresh template groups for this cell after successful file processing
            try:
                cell = self.db.get_cell_by_name(cell_name)
                if cell:
                    created_count = self.db.refresh_template_groups(cell['id'])
                    logger.info(f"Auto-refreshed template groups for cell '{cell_name}': {created_count} groups updated")
            except Exception as e:
                logger.warning(f"Failed to auto-refresh template groups for cell '{cell_name}': {e}")
                # Don't fail the main operation if template refresh fails
            
            return ProcessingResult(
                success=True,
                file_id=file_id,
                message=summary,
                data=data_file.universal_data  # Return in-memory data
            )
            
        except Exception as e:
            error_info = format_error_for_user(e)
            return ProcessingResult(
                success=False,
                error=error_info['message']
            )
    
    def _store_data_file_atomic(self, data_file: DataFile, file_id: str, 
                               cell: Dict[str, Any], metadata_path: Path, 
                               data_path: Path, options: Dict[str, Any]):
        """Store DataFile atomically with database transaction."""
        # Use per-cell processed directory structure
        cell_name = cell['name']
        processed_dir = self.data_dir / "cells" / cell_name / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare file information  
        parquet_path = processed_dir / f"{file_id}.parquet"
        
        # Convert metadata to JSON-serializable format
        metadata_dict = {
            'original_filename': data_file.metadata.original_filename,
            'file_hash': data_file.metadata.file_hash,
            'file_size_bytes': data_file.metadata.file_size_bytes,
            'parser_version': data_file.metadata.parser_version,
            'acquisition_start': data_file.metadata.acquisition_start.isoformat(),
            'acquisition_duration_s': data_file.metadata.acquisition_duration_s,
            'instrument_model': data_file.metadata.instrument_model,
            'software_version': data_file.metadata.software_version,
            'total_points': data_file.metadata.total_points,
            'technique_count': data_file.metadata.technique_count,
            'actionid_mappings': data_file.metadata.actionid_mappings,
            'notes': data_file.metadata.notes,
            'temperature_c': data_file.metadata.temperature_c,
            'user_metadata': data_file.metadata.user_metadata or {}
        }
        
        file_info = {
            'file_id': file_id,
            'original_filename': metadata_path.name,
            'paired_filename': data_path.name,
            'file_hash': self._calculate_file_hash(metadata_path),
            'file_size_bytes': metadata_path.stat().st_size + data_path.stat().st_size,
            'instrument_model': data_file.metadata.instrument_model,
            'acquisition_start': data_file.metadata.acquisition_start,
            'acquisition_duration_s': data_file.metadata.acquisition_duration_s,
            'temperature_c': options.get('temperature_c', 25.0),
            'parquet_file_path': str(parquet_path),
            'metadata': metadata_dict
        }
        
        # Generate segments
        segments = self._generate_segments(data_file, file_id)
        
        # Atomic database transaction
        with self.db.get_connection() as conn:
            conn.execute("BEGIN")
            try:
                # Add file to database
                self.db.add_file(cell['id'], file_info)
                
                # Add segments
                self.db.add_segments(file_id, segments)
                
                # NEW: Update experiment accumulation for entire cell
                self._update_cell_experiment_accumulation(cell['id'])
                
                # Write parquet file
                data_file.universal_data.write_parquet(parquet_path)
                
                # Update processing status
                self.db.update_file_status(file_id, 'completed')
                
                conn.commit()
                logger.info(f"Successfully stored data file: {file_id}")
                
            except Exception as e:
                conn.rollback()
                # Clean up parquet file on failure
                if parquet_path.exists():
                    parquet_path.unlink()
                raise ProcessingError(f"Failed to store data file: {str(e)}")
    
    def _generate_segments(self, data_file: DataFile, file_id: str) -> List[Dict[str, Any]]:
        """Generate segment information from DataFile with analytics."""
        segments = []
        segment_boundaries = data_file.get_segment_boundaries()
        
        # Prepare segment info for analytics
        segments_info = []
        for i, boundary in enumerate(segment_boundaries):
            # Get technique mapping from new universal system
            raw_action_id = boundary.get('technique_id')
            universal_technique_id = None
            technique_name = "Unknown"
            fundamental_technique = "unknown"
            
            if raw_action_id is not None:
                # Look up in new technique mapping system
                technique_mapping = self.db.get_technique_mapping(raw_action_id)
                if technique_mapping:
                    universal_technique_id = technique_mapping['technique_id']
                    technique_name = technique_mapping['technique_name'] 
                    fundamental_technique = technique_mapping['technique_name'].lower()  # Use technique name as category
                else:
                    # Unknown ActionID - store as-is for later mapping
                    technique_name = f"ActionID_{raw_action_id}"
                    fundamental_technique = "unknown"
            
            segment_info = {
                'segment_index': boundary.get('segment_number', i),  # Use actual segment_number from instrument
                'technique_id': universal_technique_id or raw_action_id,  # Store universal ID if available
                'raw_action_id': raw_action_id,  # Keep raw ActionID for reference
                'technique_name': technique_name,
                'fundamental_technique': fundamental_technique,
                'start_row': boundary['start_row'],
                'end_row': boundary['end_row'],
                'start_time_s': boundary['start_time_s'],
                'end_time_s': boundary['end_time_s'],
                'point_count': boundary['point_count'],
                'segment_metadata': {}
            }
            segments_info.append(segment_info)
        
        # Perform analytics on all segments
        logger.info(f"Computing analytics for {len(segments_info)} segments")
        try:
            analytics_results = self.analytics_engine.analyze_all_segments(
                data_file.universal_data, segments_info
            )
            
            # Combine segment info with analytics results
            for segment_info, analytics in zip(segments_info, analytics_results):
                # Merge analytics results into segment info
                segment_info.update(analytics)
                segments.append(segment_info)
                
            logger.info(f"Analytics computation completed for {len(segments)} segments")
            
        except Exception as e:
            logger.error(f"Analytics computation failed: {e}")
            # Fallback: use segments without analytics
            for segment_info in segments_info:
                segment_info.update({
                    'analysis_status': 'failed',
                    'analysis_results': '{"error": "Analytics computation failed"}',
                    'duration_s': segment_info['end_time_s'] - segment_info['start_time_s']
                })
                segments.append(segment_info)
        
        return segments
    
    def _generate_processing_summary(self, data_file: DataFile) -> str:
        """Generate human-readable processing summary."""
        segments = data_file.get_segment_boundaries()
        techniques = []
        
        for segment in segments:
            raw_action_id = segment.get('technique_id')
            if raw_action_id is not None:
                # Look up using new technique mapping system
                technique_mapping = self.db.get_technique_mapping(raw_action_id)
                if technique_mapping:
                    techniques.append(technique_mapping['technique_name'].lower())
                else:
                    techniques.append(f"ActionID_{raw_action_id}")
        
        unique_techniques = list(set(techniques)) if techniques else ["Unknown"]
        
        return (f"Processed {len(segments)} segments, "
                f"{len(unique_techniques)} techniques: {', '.join(unique_techniques)}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        import hashlib
        
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception:
            return "unknown"
    
    def _update_cell_experiment_accumulation(self, cell_id: int):
        """
        Update experiment accumulation for all segments in cell.
        This is the core method that maintains cross-file accumulation.
        """
        try:
            # Get files ordered chronologically by acquisition timestamp
            files = self.db.get_cell_files_ordered_by_timestamp(cell_id)
            
            if not files:
                logger.debug(f"No files found for cell {cell_id}")
                return
            
            # Running offsets for experiment accumulation
            charge_offset = 0.0
            discharge_offset = 0.0
            energy_charge_offset = 0.0
            energy_discharge_offset = 0.0
            time_offset = 0.0
            
            logger.debug(f"Updating experiment accumulation for cell {cell_id} with {len(files)} files")
            
            for file_info in files:
                file_id = file_info['file_id']
                
                # Get final cumulative values from this file's last segment
                final_values = self.db.get_file_final_cumulative_values(file_id)
                
                # Update ALL segments in this file with current experiment offsets
                updated_count = self.db.update_segments_experiment_accumulation(
                    file_id,
                    charge_offset,
                    discharge_offset,
                    energy_charge_offset,
                    energy_discharge_offset,
                    time_offset
                )
                
                logger.debug(f"Updated {updated_count} segments in file {file_id} with offsets: "
                           f"charge={charge_offset:.3f}, discharge={discharge_offset:.3f}, "
                           f"time={time_offset:.1f}s")
                
                # Update offsets for next file (chronologically later)
                charge_offset += final_values['charge_cumulative_ah']
                discharge_offset += abs(final_values['discharge_cumulative_ah'])  # Convert to positive
                energy_charge_offset += final_values['energy_charge_cumulative_wh']
                energy_discharge_offset += abs(final_values['energy_discharge_cumulative_wh'])
                time_offset += final_values['total_duration_s']
            
            logger.info(f"Completed experiment accumulation update for cell {cell_id}")
            
        except Exception as e:
            logger.error(f"Failed to update experiment accumulation for cell {cell_id}: {e}")
            # Don't raise - let the main operation continue
    
    def recalculate_cell_experiment_accumulation(self, cell_name: str) -> ProcessingResult:
        """
        Recalculate experiment accumulation for all files in a cell.
        This is a database-only operation for maintenance/repair.
        """
        try:
            cell = self.get_cell_by_name(cell_name)
            if not cell:
                return ProcessingResult(
                    success=False,
                    error=f"Cell '{cell_name}' not found"
                )
            
            logger.info(f"Recalculating experiment accumulation for cell '{cell_name}'")
            self._update_cell_experiment_accumulation(cell['id'])
            
            return ProcessingResult(
                success=True,
                message=f"Recalculated experiment accumulation for cell '{cell_name}'"
            )
            
        except Exception as e:
            error_info = format_error_for_user(e)
            return ProcessingResult(
                success=False,
                error=f"Failed to recalculate accumulation for '{cell_name}': {error_info['message']}"
            )
    
    # =============================================================================
    # DATA ACCESS
    # =============================================================================
    
    def get_cell_files(self, cell_name: str) -> List[Dict[str, Any]]:
        """Get all files for a cell."""
        try:
            cell = self.get_cell_by_name(cell_name)
            if not cell:
                return []
            
            return self.db.get_cell_files(cell['id'])
            
        except Exception as e:
            logger.error(f"Failed to get files for cell '{cell_name}': {e}")
            return []
    
    def get_file_data(self, file_id: str) -> Optional[pl.DataFrame]:
        """Get processed data for a file."""
        try:
            file_info = self.db.get_file_by_id(file_id)
            if not file_info:
                return None
            
            parquet_path = Path(file_info['parquet_file_path'])
            if not parquet_path.exists():
                logger.error(f"Parquet file not found: {parquet_path}")
                return None
            
            return pl.read_parquet(parquet_path)
            
        except Exception as e:
            logger.error(f"Failed to get data for file '{file_id}': {e}")
            return None
    
    def get_file_segments(self, file_id: str) -> List[Dict[str, Any]]:
        """Get segments for a file."""
        try:
            return self.db.get_file_segments(file_id)
        except Exception as e:
            logger.error(f"Failed to get segments for file '{file_id}': {e}")
            return []
    
    def get_segments_by_technique(self, technique: str) -> List[Dict[str, Any]]:
        """Get all segments for a specific technique."""
        try:
            return self.db.get_segments_by_technique(technique)
        except Exception as e:
            logger.error(f"Failed to get segments for technique '{technique}': {e}")
            return []
    
    def delete_file(self, file_id: str) -> ProcessingResult:
        """Delete a file and all associated data (parquet + raw files)."""
        try:
            # Get file info first to access file paths
            file_info = self.db.get_file_by_id(file_id)
            if not file_info:
                return ProcessingResult(
                    success=False,
                    error=f"File {file_id} not found in database"
                )
            
            # Get cell info to construct raw file paths
            cell = self.db.get_cell_by_id(file_info['cell_id'])
            if not cell:
                return ProcessingResult(
                    success=False,
                    error=f"Cell not found for file {file_id}"
                )
            
            cell_name = cell['name']
            deleted_files = []
            deletion_errors = []
            
            # Delete raw files from cell directory structure
            from src_clean.core.config import get_config
            config = get_config()
            cell_raw_dir = config.get_cell_raw_directory(cell_name)
            
            # Delete original metadata file (.par)
            if file_info.get('original_filename'):
                original_path = cell_raw_dir / file_info['original_filename']
                if original_path.exists():
                    try:
                        original_path.unlink()
                        deleted_files.append(str(original_path))
                        logger.info(f"Deleted raw metadata file: {original_path}")
                    except Exception as e:
                        deletion_errors.append(f"metadata file {original_path}: {e}")
            
            # Delete paired data file (.par.csv)
            if file_info.get('paired_filename'):
                paired_path = cell_raw_dir / file_info['paired_filename']
                if paired_path.exists():
                    try:
                        paired_path.unlink()
                        deleted_files.append(str(paired_path))
                        logger.info(f"Deleted raw data file: {paired_path}")
                    except Exception as e:
                        deletion_errors.append(f"data file {paired_path}: {e}")
            
            # Delete parquet file
            parquet_path = file_info.get('parquet_file_path')
            if parquet_path and Path(parquet_path).exists():
                try:
                    Path(parquet_path).unlink()
                    deleted_files.append(str(parquet_path))
                    logger.info(f"Deleted parquet file: {parquet_path}")
                except Exception as e:
                    deletion_errors.append(f"parquet file {parquet_path}: {e}")
            
            # Delete from database (this will cascade to segments and group associations)
            db_success = self.db.delete_file(file_id)
            
            if db_success:
                # NEW: Update experiment accumulation for remaining files in cell
                self._update_cell_experiment_accumulation(file_info['cell_id'])
                
                message_parts = [f"Deleted file {file_id}"]
                if deleted_files:
                    message_parts.append(f"Removed {len(deleted_files)} files from disk")
                if deletion_errors:
                    message_parts.append(f"Had {len(deletion_errors)} file deletion errors")
                
                return ProcessingResult(
                    success=True,
                    file_id=file_id,
                    message="; ".join(message_parts)
                )
            else:
                return ProcessingResult(
                    success=False,
                    error=f"Failed to delete file {file_id} from database"
                )
                
        except Exception as e:
            error_info = format_error_for_user(e)
            return ProcessingResult(
                success=False,
                error=f"Failed to delete file {file_id}: {error_info['message']}"
            )
    
    def delete_cell_by_name(self, cell_name: str) -> ProcessingResult:
        """Delete a cell by name and all associated data."""
        try:
            # Get cell by name first
            cell = self.db.get_cell_by_name(cell_name)
            if not cell:
                return ProcessingResult(
                    success=False,
                    error=f"Cell '{cell_name}' not found"
                )
            
            # Delegate to the main delete_cell method using cell_id
            return self.delete_cell(cell['id'])
            
        except Exception as e:
            error_info = format_error_for_user(e)
            return ProcessingResult(
                success=False,
                error=f"Failed to delete cell '{cell_name}': {error_info['message']}"
            )
    
    # =============================================================================
    # ACTIONID MANAGEMENT
    # =============================================================================
    
    def get_technique_mappings(self) -> List[Dict[str, Any]]:
        """Get all technique mappings."""
        try:
            return self.db.get_all_technique_mappings()
        except Exception as e:
            logger.error(f"Failed to get technique mappings: {e}")
            return []
    
    def get_fundamental_techniques(self) -> List[Dict[str, Any]]:
        """Get all fundamental techniques."""
        try:
            return self.db.get_all_fundamental_techniques()
        except Exception as e:
            logger.error(f"Failed to get fundamental techniques: {e}")
            return []
    
    def add_technique_mapping(self, action_id: int, action_name: str, 
                             technique_id: int, description: str = "") -> ProcessingResult:
        """Add new VersaStudio ActionID mapping."""
        try:
            success = self.db.add_technique_mapping(
                action_id, action_name, technique_id, description
            )
            
            if success:
                return ProcessingResult(
                    success=True,
                    message=f"ActionID {action_id} mapped to technique {technique_id}"
                )
            else:
                return ProcessingResult(
                    success=False,
                    error=f"Failed to add ActionID {action_id} mapping"
                )
                
        except Exception as e:
            error_info = format_error_for_user(e)
            return ProcessingResult(
                success=False,
                error=error_info['message']
            )
    
    def discover_unknown_actionids(self, data: pl.DataFrame) -> List[int]:
        """Discover unknown ActionIDs in data."""
        try:
            if 'technique_id' not in data.columns:
                return []
            
            # Get unique ActionIDs from data
            data_actionids = set(data.get_column('technique_id').unique().drop_nulls().to_list())
            
            # Get known ActionIDs from new technique mapping system
            known_mappings = self.get_technique_mappings()
            known_actionids = {mapping['action_id'] for mapping in known_mappings}
            
            # Return unknown ActionIDs
            return list(data_actionids - known_actionids)
            
        except Exception as e:
            logger.error(f"Failed to discover unknown ActionIDs: {e}")
            return []
    
    # =============================================================================
    # VALIDATION
    # =============================================================================
    
    def validate_dual_files(self, metadata_path: Path, data_path: Path) -> ProcessingResult:
        """Validate dual file pair using the same parsing logic as processing."""
        try:
            # Use the SAME function that process_dual_files uses - unified path
            data_file = auto_parse_dual_files(metadata_path, data_path)
            
            # If parsing succeeds, files are valid
            segment_count = len(data_file.get_segment_boundaries())
            message = f"Files validated successfully: {data_file.metadata.instrument_model}, {segment_count} segments"
            
            return ProcessingResult(
                success=True,
                message=message,
                data={
                    'instrument': data_file.metadata.instrument_model,
                    'segment_count': segment_count,
                    'total_points': data_file.metadata.total_points,
                    'technique_count': data_file.metadata.technique_count
                }
            )
                
        except Exception as e:
            error_info = format_error_for_user(e)
            return ProcessingResult(
                success=False,
                error=f"File validation failed: {error_info['message']}"
            )
    
    # =============================================================================
    # STATISTICS AND UTILITIES
    # =============================================================================
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            stats = self.db.get_database_stats()
            
            # Add parser information
            parser_info = self.parser_factory.get_parser_info()
            stats['supported_instruments'] = list(parser_info.keys())
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {'error': str(e)}
    
    def cleanup_failed_processing(self) -> ProcessingResult:
        """Clean up failed processing attempts."""
        try:
            # Find files with 'pending' status older than 1 hour
            with self.db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT file_id, parquet_file_path FROM files 
                    WHERE processing_status = 'pending' 
                    AND created_at < datetime('now', '-1 hour')
                """)
                
                failed_files = cursor.fetchall()
                
                if not failed_files:
                    return ProcessingResult(
                        success=True,
                        message="No failed processing attempts found to clean up"
                    )
                
                cleaned = 0
                cleanup_errors = []
                
                for file_id, parquet_path in failed_files:
                    try:
                        # Use the new delete_file method for complete cleanup
                        result = self.delete_file(file_id)
                        if result.success:
                            cleaned += 1
                        else:
                            cleanup_errors.append(f"{file_id}: {result.error}")
                    except Exception as e:
                        cleanup_errors.append(f"{file_id}: {str(e)}")
                
                message_parts = [f"Cleaned up {cleaned} failed processing attempts"]
                if cleanup_errors:
                    message_parts.append(f"Had {len(cleanup_errors)} cleanup errors")
                
                return ProcessingResult(
                    success=True,
                    message="; ".join(message_parts)
                )
                
        except Exception as e:
            error_info = format_error_for_user(e)
            return ProcessingResult(
                success=False,
                error=f"Failed to cleanup failed processing: {error_info['message']}"
            )
    
    def reprocess_file(self, file_id: str) -> ProcessingResult:
        """
        Reprocess a file using its stored raw data files.
        
        Args:
            file_id: ID of the file to reprocess
            
        Returns:
            ProcessingResult with success/error information
        """
        try:
            # Get file info to access raw file paths
            file_info = self.db.get_file_by_id(file_id)
            if not file_info:
                return ProcessingResult(
                    success=False,
                    error=f"File {file_id} not found in database"
                )
            
            # Reconstruct raw file paths using config system
            cell = self.db.get_cell_by_id(file_info['cell_id'])
            cell_name = cell['name']
            
            # Use config to get standardized cell raw directory
            config = get_config()
            raw_dir = config.get_cell_raw_directory(cell_name)
            
            metadata_filename = file_info['original_filename']
            data_filename = file_info['paired_filename']
            
            metadata_path = raw_dir / metadata_filename
            data_path = raw_dir / data_filename
            
            if not metadata_path.exists():
                return ProcessingResult(
                    success=False,
                    error=f"Raw metadata file not found: {metadata_path}"
                )
            
            if not data_path.exists():
                return ProcessingResult(
                    success=False,
                    error=f"Raw data file not found: {data_path}"
                )
            
            # Cell info already retrieved above
            
            # Get original processing options
            options = {
                'temperature_c': file_info.get('temperature_c', 25.0)
            }
            
            # Delete existing processed data
            delete_success = self.delete_file(file_id)
            if not delete_success:
                logger.warning(f"Failed to delete existing data for {file_id}, continuing anyway")
            
            # Reprocess using the same raw files
            logger.info(f"Reprocessing file {file_id} from raw files")
            result = self.process_dual_files(
                metadata_path=metadata_path,
                data_path=data_path,
                cell_name=cell['name'],
                **options
            )
            
            if result.success:
                logger.info(f"Successfully reprocessed file: {file_id}")
                return ProcessingResult(
                    success=True,
                    file_id=result.file_id,
                    message=f"Successfully reprocessed {file_id}. New file ID: {result.file_id}"
                )
            else:
                return ProcessingResult(
                    success=False,
                    error=f"Failed to reprocess {file_id}: {result.error}"
                )
                
        except Exception as e:
            logger.error(f"Error reprocessing file {file_id}: {e}")
            return ProcessingResult(
                success=False,
                error=f"Reprocessing error: {str(e)}"
            )
    
    def reprocess_cell(self, cell_name: str) -> ProcessingResult:
        """
        Reprocess all files for a cell using stored raw data.
        
        Args:
            cell_name: Name of the cell to reprocess
            
        Returns:
            ProcessingResult with summary of reprocessing
        """
        try:
            # Get cell info
            cell = self.db.get_cell_by_name(cell_name)
            if not cell:
                return ProcessingResult(
                    success=False,
                    error=f"Cell '{cell_name}' not found"
                )
            
            # Get all files for the cell
            files = self.db.get_cell_files(cell['id'])
            if not files:
                return ProcessingResult(
                    success=True,
                    message=f"No files to reprocess for cell '{cell_name}'"
                )
            
            logger.info(f"Reprocessing {len(files)} files for cell '{cell_name}'")
            
            successful_count = 0
            failed_count = 0
            error_messages = []
            new_file_ids = []
            
            for file_info in files:
                file_id = file_info['file_id']
                logger.info(f"Reprocessing file: {file_id}")
                
                result = self.reprocess_file(file_id)
                
                if result.success:
                    successful_count += 1
                    new_file_ids.append(result.file_id)
                    logger.info(f"✅ Reprocessed: {file_id} → {result.file_id}")
                else:
                    failed_count += 1
                    error_messages.append(f"{file_id}: {result.error}")
                    logger.error(f"❌ Failed to reprocess: {file_id} - {result.error}")
            
            # Generate summary message
            summary_parts = [
                f"Cell '{cell_name}' reprocessing complete:",
                f"✅ Successful: {successful_count}",
                f"❌ Failed: {failed_count}"
            ]
            
            if failed_count > 0:
                summary_parts.append("Errors:")
                summary_parts.extend([f"  - {msg}" for msg in error_messages[:5]])  # Limit to first 5 errors
                if len(error_messages) > 5:
                    summary_parts.append(f"  - ... and {len(error_messages) - 5} more errors")
            
            summary = "\n".join(summary_parts)
            
            return ProcessingResult(
                success=failed_count == 0,
                message=summary,
                data={'successful_count': successful_count, 'failed_count': failed_count, 'new_file_ids': new_file_ids}
            )
            
        except Exception as e:
            logger.error(f"Error reprocessing cell {cell_name}: {e}")
            return ProcessingResult(
                success=False,
                error=f"Cell reprocessing error: {str(e)}"
            )
    
    def migrate_data_structure(self, dry_run: bool = True) -> ProcessingResult:
        """
        Migrate all raw files to standardized directory structure.
        
        Args:
            dry_run: If True, only report what would be done without making changes
            
        Returns:
            ProcessingResult with migration summary
        """
        try:
            logger.info(f"Starting data structure migration {'(dry run)' if dry_run else ''}")
            
            migration_summary = self.migration_manager.migrate_raw_files(dry_run=dry_run)
            
            if migration_summary['errors']:
                error_msg = f"Migration completed with errors: {len(migration_summary['errors'])} errors"
                logger.warning(error_msg)
                for error in migration_summary['errors'][:5]:  # Show first 5 errors
                    logger.warning(f"  - {error}")
                
                return ProcessingResult(
                    success=False,
                    message=error_msg,
                    data=migration_summary
                )
            else:
                success_msg = f"Migration {'planned' if dry_run else 'completed'} successfully"
                if not dry_run:
                    success_msg += f": {migration_summary['migration_items_executed']} items processed"
                
                logger.info(success_msg)
                return ProcessingResult(
                    success=True,
                    message=success_msg,
                    data=migration_summary
                )
                
        except Exception as e:
            logger.error(f"Data migration failed: {e}")
            return ProcessingResult(
                success=False,
                error=f"Migration error: {str(e)}"
            )
    
    def ensure_cell_directory_structure(self, cell_name: str) -> ProcessingResult:
        """
        Ensure complete directory structure exists for a cell.
        
        This creates the full directory structure including:
        - raw/ (for original files)  
        - processed/ (for parquet files)
        - analysis_results/ (for analytics JSON)
        - user_groups/ (for group definitions)
        """
        try:
            # Use config system to create standardized structure
            from src_clean.core.config import get_config
            config = get_config()
            
            cell_dir = config.get_cell_directory(cell_name)
            directories_created = []
            
            # Create all required subdirectories
            subdirs = ['raw', 'processed', 'analysis_results', 'user_groups']
            
            for subdir in subdirs:
                subdir_path = cell_dir / subdir
                if not subdir_path.exists():
                    subdir_path.mkdir(parents=True, exist_ok=True)
                    directories_created.append(str(subdir_path))
                    logger.debug(f"Created directory: {subdir_path}")
            
            # Create cell metadata file if it doesn't exist
            metadata_file = cell_dir / 'metadata.json'
            if not metadata_file.exists():
                import json
                metadata = {
                    "cell_name": cell_name,
                    "created_at": datetime.now().isoformat(),
                    "structure_version": "1.0"
                }
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
                directories_created.append(str(metadata_file))
                logger.debug(f"Created metadata file: {metadata_file}")
            
            if directories_created:
                message = f"Created directory structure for '{cell_name}': {len(directories_created)} items"
            else:
                message = f"Directory structure for '{cell_name}' already exists"
            
            return ProcessingResult(
                success=True,
                message=message
            )
            
        except Exception as e:
            error_info = format_error_for_user(e)
            return ProcessingResult(
                success=False,
                error=f"Failed to create directory structure for {cell_name}: {error_info['message']}"
            )
    
    # =============================================================================
    # ANALYTICS OPERATIONS
    # =============================================================================
    
    def reanalyze_segments(self, file_id: str, force_recompute: bool = False) -> ProcessingResult:
        """
        Reanalyze segments for a file using stored parquet data.
        
        Args:
            file_id: ID of the file to reanalyze
            force_recompute: If True, recompute even completed segments
            
        Returns:
            ProcessingResult with reanalysis status
        """
        try:
            # Get file information
            file_info = self.db.get_file_by_id(file_id)
            if not file_info:
                return ProcessingResult(
                    success=False,
                    error=f"File {file_id} not found in database"
                )
            
            # Load parquet data
            parquet_path = Path(file_info['parquet_file_path'])
            if not parquet_path.exists():
                return ProcessingResult(
                    success=False,
                    error=f"Parquet file not found: {parquet_path}"
                )
            
            data = pl.read_parquet(parquet_path)
            
            # Get current segments
            segments = self.db.get_file_segments(file_id)
            if not segments:
                return ProcessingResult(
                    success=False,
                    error=f"No segments found for file {file_id}"
                )
            
            logger.info(f"Reanalyzing {len(segments)} segments for file: {file_id}")
            
            updated_count = 0
            failed_count = 0
            
            # Reanalyze each segment
            for segment in segments:
                try:
                    # Skip if completed and not forcing recompute
                    if (segment.get('analysis_status') == 'completed' and 
                        not force_recompute):
                        continue
                    
                    # Perform analysis
                    analysis_result = self.analytics_engine.analyze_segment(
                        data, segment
                    )
                    
                    # Update database
                    success = self.db.update_segment_analysis(
                        file_id, segment['segment_index'], analysis_result
                    )
                    
                    if success:
                        updated_count += 1
                        logger.debug(f"Updated segment {segment['segment_index']}")
                    else:
                        failed_count += 1
                        logger.warning(f"Failed to update segment {segment['segment_index']}")
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error reanalyzing segment {segment['segment_index']}: {e}")
            
            # Generate summary message
            total_processed = updated_count + failed_count
            summary = f"Reanalyzed {file_id}: {updated_count} updated, {failed_count} failed"
            
            if failed_count == 0:
                return ProcessingResult(
                    success=True,
                    file_id=file_id,
                    message=summary
                )
            else:
                return ProcessingResult(
                    success=False,
                    file_id=file_id,
                    error=f"{summary} (partial failure)"
                )
                
        except Exception as e:
            logger.error(f"Error reanalyzing segments for {file_id}: {e}")
            return ProcessingResult(
                success=False,
                error=f"Reanalysis error: {str(e)}"
            )
    
    def get_analytics_summary(self, cell_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get analytics summary for all segments or for a specific cell.
        
        Args:
            cell_name: Optional cell name to filter results
            
        Returns:
            Summary of analytics status and metrics
        """
        try:
            with self.db.get_connection() as conn:
                # Base query
                if cell_name:
                    cursor = conn.execute("""
                        SELECT s.analysis_status, s.capacity_ah, s.energy_wh, s.duration_s,
                               s.analysis_results, s.fundamental_technique
                        FROM segments s
                        JOIN files f ON s.file_id = f.file_id
                        JOIN cells c ON f.cell_id = c.id
                        WHERE c.name = ?
                    """, (cell_name,))
                else:
                    cursor = conn.execute("""
                        SELECT s.analysis_status, s.capacity_ah, s.energy_wh, s.duration_s,
                               s.analysis_results, s.fundamental_technique
                        FROM segments s
                    """)
                
                segments_data = [dict(row) for row in cursor.fetchall()]
            
            if not segments_data:
                return {'total_segments': 0, 'message': 'No segments found'}
            
            # Use analytics engine to generate summary
            summary = self.analytics_engine.get_analysis_summary(segments_data)
            
            # Add database-specific information
            summary['cell_filter'] = cell_name
            summary['generated_at'] = datetime.now().isoformat()
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting analytics summary: {e}")
            return {'error': str(e)}
    
    def get_segments_by_analysis_status(self, status: str = 'failed') -> List[Dict[str, Any]]:
        """
        Get segments filtered by analysis status.
        
        Args:
            status: Analysis status to filter by ('pending', 'completed', 'failed', 'partial')
            
        Returns:
            List of segments with the specified status
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT s.*, f.file_id, f.parquet_file_path, c.name as cell_name
                    FROM segments s
                    JOIN files f ON s.file_id = f.file_id  
                    JOIN cells c ON f.cell_id = c.id
                    WHERE s.analysis_status = ?
                    ORDER BY c.name, f.acquisition_start, s.segment_index
                """, (status,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting segments by status '{status}': {e}")
            return []
    
    # =============================================================================
    # GROUP MANAGEMENT OPERATIONS
    # =============================================================================
    
    def create_group(self, cell_name: str, group_name: str, description: str = "", 
                     is_template: bool = False, template_type: str = None) -> ProcessingResult:
        """Create a new user group or template group for organizing segments."""
        try:
            # Get cell ID
            cell = self.db.get_cell_by_name(cell_name)
            if not cell:
                return ProcessingResult(
                    success=False,
                    error=f"Cell '{cell_name}' not found"
                )
            
            group_id = self.db.create_group(cell['id'], group_name, description, 
                                          is_template, template_type)
            
            group_type = "template" if is_template else "user"
            return ProcessingResult(
                success=True,
                file_id=str(group_id),  # Using file_id field for group_id
                message=f"Created {group_type} group '{group_name}' successfully"
            )
            
        except Exception as e:
            error_info = format_error_for_user(e)
            return ProcessingResult(
                success=False,
                error=error_info['message']
            )
    
    def get_groups(self, cell_name: str) -> List[Dict[str, Any]]:
        """Get all groups for a cell."""
        try:
            cell = self.db.get_cell_by_name(cell_name)
            if not cell:
                return []
            
            return self.db.get_cell_groups(cell['id'])
            
        except Exception as e:
            logger.error(f"Failed to get groups for cell '{cell_name}': {e}")
            return []
    
    def get_group_info(self, group_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a group."""
        try:
            return self.db.get_group_info(group_id)
        except Exception as e:
            logger.error(f"Failed to get group info for ID {group_id}: {e}")
            return None
    
    def delete_group(self, group_id: int) -> ProcessingResult:
        """Delete a group and all its segment associations."""
        try:
            # Get group info for the response message
            group_info = self.db.get_group_info(group_id)
            
            success = self.db.delete_group(group_id)
            
            if success:
                group_name = group_info['group_name'] if group_info else f"Group {group_id}"
                return ProcessingResult(
                    success=True,
                    message=f"Deleted group '{group_name}' successfully"
                )
            else:
                return ProcessingResult(
                    success=False,
                    error=f"Group {group_id} not found"
                )
                
        except Exception as e:
            error_info = format_error_for_user(e)
            return ProcessingResult(
                success=False,
                error=error_info['message']
            )
    
    def add_segments_to_group(self, group_id: int, segment_ids: List[str]) -> ProcessingResult:
        """Add segments to a group."""
        try:
            # Convert string segment IDs to integers
            int_segment_ids = [int(seg_id) for seg_id in segment_ids]
            added_count = self.db.add_segments_to_group(group_id, int_segment_ids)
            
            return ProcessingResult(
                success=True,
                message=f"Added {added_count} segments to group"
            )
            
        except Exception as e:
            error_info = format_error_for_user(e)
            return ProcessingResult(
                success=False,
                error=error_info['message']
            )
    
    def remove_segments_from_group(self, group_id: int, segment_ids: List[str]) -> ProcessingResult:
        """Remove segments from a group."""
        try:
            # Convert string segment IDs to integers
            int_segment_ids = [int(seg_id) for seg_id in segment_ids]
            removed_count = self.db.remove_segments_from_group(group_id, int_segment_ids)
            
            return ProcessingResult(
                success=True,
                message=f"Removed {removed_count} segments from group"
            )
            
        except Exception as e:
            error_info = format_error_for_user(e)
            return ProcessingResult(
                success=False,
                error=error_info['message']
            )
    
    def get_group_segments(self, group_id: int) -> List[Dict[str, Any]]:
        """Get all segments in a group."""
        try:
            return self.db.get_group_segments(group_id)
        except Exception as e:
            logger.error(f"Failed to get segments for group {group_id}: {e}")
            return []
    
    def get_cell_segments(self, cell_name: str) -> List[Dict[str, Any]]:
        """Get all segments for a cell with their group memberships."""
        try:
            cell = self.db.get_cell_by_name(cell_name)
            if not cell:
                return []
            segments =self.db.get_cell_segments_with_groups(cell['id'])
            print(f"API call {len(segments)} segments")
            if segments:
                print(f"First segment keys: {list(segments[0].keys())}")
            return segments
            
        except Exception as e:
            logger.error(f"Failed to get segments for cell '{cell_name}': {e}")
            return []
    
    def is_segment_in_group(self, segment_id: int, group_id: int) -> bool:
        """Check if a segment belongs to a group."""
        try:
            return self.db.is_segment_in_group(segment_id, group_id)
        except Exception as e:
            logger.error(f"Failed to check segment {segment_id} in group {group_id}: {e}")
            return False

    # =============================================================================
    # ANALYTICS METHODS - for Tab 3 Data Analysis
    # =============================================================================

    def get_group_base_statistics(self, group_ids: List[str]) -> Dict[str, Dict[str, float]]:
        """
        Get aggregated statistics for multiple groups using existing segment columns.
        
        Args:
            group_ids: List of group IDs to include in statistics
            
        Returns:
            Dictionary with metrics as keys and statistics as values:
            {
                "start_potential_v": {"mean": 3.75, "std": 0.02, "min": 3.70, "max": 3.80, "count": 45},
                "duration_s": {"mean": 120.5, "std": 15.2, "min": 90.0, "max": 180.0, "count": 45},
                ...
            }
        """
        try:
            int_group_ids = [int(gid) for gid in group_ids]
            return self.db.get_group_base_statistics(int_group_ids)
        except Exception as e:
            logger.error(f"Failed to get group statistics for groups {group_ids}: {e}")
            return {}

    def get_segment_subset_statistics(self, segment_ids: List[str]) -> Dict[str, Dict[str, float]]:
        """
        Get aggregated statistics for a specific subset of segments.
        
        Args:
            segment_ids: List of segment IDs to include in statistics
            
        Returns:
            Dictionary with metrics as keys and statistics as values (same format as get_group_base_statistics)
        """
        try:
            int_segment_ids = [int(sid) for sid in segment_ids]
            return self.db.get_segment_subset_statistics(int_segment_ids)
        except Exception as e:
            logger.error(f"Failed to get segment statistics for segments {segment_ids}: {e}")
            return {}

    def get_multi_group_segments(self, group_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get all segments from multiple groups with full segment data.
        
        Args:
            group_ids: List of group IDs to retrieve segments from
            
        Returns:
            List of segment dictionaries with full data for visualization and analysis
        """
        try:
            int_group_ids = [int(gid) for gid in group_ids]
            return self.db.get_multi_group_segments(int_group_ids)
        except Exception as e:
            logger.error(f"Failed to get segments for groups {group_ids}: {e}")
            return []

    # === Api to get schema columns and column name ==== #
    def get_segments_display_schema(self) -> Dict[str, Dict]:
        """Get display schema for segments table - simplified version."""
        try:
            with self.db.get_connection() as conn:
                # Get column information from SQLite
                cursor = conn.execute("PRAGMA table_info(segments)")
                columns_info = cursor.fetchall()

                schema = {}

                # Skip internal columns we don't want to display
                skip_columns = {
                    'created_at', 'updated_at', 'analysis_results', 'analysis_status'
                }

                for cid, name, type_name, notnull, dflt_value, pk in columns_info:
                    if name in skip_columns:
                        continue

                    schema[name] = {
                        'display_name': self._simple_display_name(name),
                        'sql_type': type_name,
                        'formatter': self._simple_formatter(name, type_name),
                        'width': 120  # Standard width for all columns
                    }

                return schema

        except Exception as e:
            print(f"Failed to get segments schema: {e}")
            return {}

    def _simple_display_name(self, column_name: str) -> str:
        """Simple display name generation - just replace underscores and title case."""
        return column_name.replace('_', ' ').title()

    def _simple_formatter(self, column_name: str, sql_type: str):
        """Simple formatter - just handle None values and basic types."""
        sql_type = sql_type.upper()

        if 'REAL' in sql_type or 'FLOAT' in sql_type:
            # Float values - show 3 decimal places
            return lambda x: f"{x:.3f}" if x is not None else "N/A"
        elif 'INT' in sql_type:
            # Integer values
            return lambda x: str(x) if x is not None else "N/A"
        else:
            # Everything else as string
            return lambda x: str(x) if x is not None else "N/A"

    def _get_group_content_columns(self) -> List[str]:
        """Get subset of segment columns for group contents display."""
        # Show fewer columns in the group contents for space
        key_columns = ['id', 'fundamental_technique', 'start_time_s', 'duration_s', 'start_potential_v',
                       'end_potential_v']

        # Filter the full schema to only include these columns
        return {col: config for col, config in self.segment_columns.items()
                if col in key_columns}

    def get_cell_groups_with_counts(self, cell_name: str) -> List[Dict[str, Any]]:
        """Get all groups for a cell with segment counts - needed for group management tab."""
        try:
            cell = self.db.get_cell_by_name(cell_name)
            if not cell:
                return []

            return self.db.get_cell_groups(cell['id'])

        except Exception as e:
            logger.error(f"Failed to get groups with counts for cell '{cell_name}': {e}")
            return []

    # =============================================================================
    # TEMPLATE GROUP OPERATIONS
    # =============================================================================

    def get_template_groups(self, cell_name: str) -> List[Dict[str, Any]]:
        """Get all template groups for a cell with segment counts."""
        try:
            cell = self.db.get_cell_by_name(cell_name)
            if not cell:
                return []

            return self.db.get_template_groups(cell['id'])

        except Exception as e:
            logger.error(f"Failed to get template groups for cell '{cell_name}': {e}")
            return []

    def get_user_groups(self, cell_name: str) -> List[Dict[str, Any]]:
        """Get all user groups (non-template) for a cell with segment counts."""
        try:
            cell = self.db.get_cell_by_name(cell_name)
            if not cell:
                return []

            return self.db.get_user_groups(cell['id'])

        except Exception as e:
            logger.error(f"Failed to get user groups for cell '{cell_name}': {e}")
            return []

    def refresh_template_groups(self, cell_name: str = None) -> ProcessingResult:
        """
        Refresh template groups for a specific cell or all cells.
        
        Args:
            cell_name: Cell name to refresh, or None to refresh all cells
            
        Returns:
            ProcessingResult with count of template groups created/updated
        """
        try:
            total_created = 0
            
            if cell_name:
                # Refresh specific cell
                print(f"DEBUG API: Refreshing template groups for specific cell '{cell_name}'")
                cell = self.db.get_cell_by_name(cell_name)
                if not cell:
                    return ProcessingResult(
                        success=False,
                        error=f"Cell '{cell_name}' not found"
                    )
                
                print(f"DEBUG API: Found cell {cell['name']} (ID: {cell['id']})")
                created_count = self.db.refresh_template_groups(cell['id'])
                total_created = created_count
                message = f"Refreshed template groups for cell '{cell_name}': {created_count} groups updated"
                
            else:
                # Refresh all cells
                print("DEBUG API: Refreshing template groups for ALL cells")
                cells = self.db.get_all_cells()
                print(f"DEBUG API: Found {len(cells)} cells to process")
                
                for cell in cells:
                    try:
                        print(f"DEBUG API: Processing cell '{cell['name']}' (ID: {cell['id']})")
                        
                        # Check if this cell has segments
                        segments = self.db.get_cell_segments_with_groups(cell['id'])
                        print(f"DEBUG API: Cell '{cell['name']}' has {len(segments)} segments")
                        
                        if segments:
                            # Show what techniques we have
                            techniques = set(seg.get('fundamental_technique', 'unknown') for seg in segments)
                            print(f"DEBUG API: Techniques found: {techniques}")
                        
                        created_count = self.db.refresh_template_groups(cell['id'])
                        print(f"DEBUG API: Created/updated {created_count} template groups for '{cell['name']}'")
                        total_created += created_count
                        
                    except Exception as e:
                        print(f"DEBUG API: Error with cell {cell['name']}: {e}")
                        logger.warning(f"Failed to refresh template groups for cell {cell['name']}: {e}")
                
                message = f"Refreshed template groups for all cells: {total_created} groups updated across {len(cells)} cells"
            
            print(f"DEBUG API: Total template groups created/updated: {total_created}")
            return ProcessingResult(
                success=True,
                file_id=str(total_created),  # Using file_id field for count
                message=message
            )
            
        except Exception as e:
            print(f"DEBUG API: Exception in refresh_template_groups: {e}")
            error_info = format_error_for_user(e)
            return ProcessingResult(
                success=False,
                error=error_info['message']
            )

    def copy_group(self, group_id: int, new_name: str = None) -> ProcessingResult:
        """
        Copy a group (template or user) to a new user group with smart naming.
        
        Args:
            group_id: Source group ID to copy
            new_name: Optional new name, or None for automatic naming
            
        Returns:
            ProcessingResult with new group ID and details
        """
        try:
            # Get source group info
            source_group = self.db.get_group_info(group_id)
            if not source_group:
                return ProcessingResult(
                    success=False,
                    error=f"Source group {group_id} not found"
                )
            
            # Generate new name if not provided
            if not new_name:
                new_name = self._generate_copy_name(source_group)
            
            # Ensure name is unique
            cell_id = source_group['cell_id']
            unique_name = self.db.generate_unique_group_name(cell_id, new_name)
            
            # Copy group as user group (never copy as template)
            new_group_id = self.db.copy_group(group_id, unique_name, copy_as_template=False)
            
            # Get source group type for message
            source_type = "template" if source_group.get('is_template') else "user"
            
            return ProcessingResult(
                success=True,
                file_id=str(new_group_id),
                message=f"Copied {source_type} group '{source_group['group_name']}' to user group '{unique_name}'"
            )
            
        except Exception as e:
            error_info = format_error_for_user(e)
            return ProcessingResult(
                success=False,
                error=error_info['message']
            )

    def _generate_copy_name(self, source_group: Dict[str, Any]) -> str:
        """
        Generate appropriate copy name based on source group type.
        
        Args:
            source_group: Source group info dictionary
            
        Returns:
            Suggested name for the copied group
        """
        source_name = source_group['group_name']
        is_template = source_group.get('is_template', False)
        
        if is_template:
            # For template groups: "Template_All_Rest" -> "User_Rest"
            if source_name.startswith("Template_All_"):
                technique = source_name.replace("Template_All_", "")
                return f"User_{technique}"
            else:
                # Fallback for non-standard template names
                return f"User_{source_name}"
        else:
            # For user groups: "My_Group" -> "Copy_My_Group"
            return f"Copy_{source_name}"

    def refresh_all_template_groups(self) -> ProcessingResult:
        """Convenience method to refresh template groups for all cells."""
        return self.refresh_template_groups(cell_name=None)

    # =============================================================================
    # ADVANCED GROUP ANALYTICS
    # =============================================================================

    def get_group_temporal_analytics(self, group_ids: List[str]) -> Dict[str, Any]:
        """
        Get temporal analytics for groups including cumulative calculations.
        
        Args:
            group_ids: List of group IDs to analyze
            
        Returns:
            Dictionary with time-series data and cumulative analytics
        """
        try:
            from src_clean.analysis.cumulative_calculator import get_cumulative_calculator
            from src_clean.analysis.analytics_config import get_config as get_analytics_config
            
            calculator = get_cumulative_calculator()
            config = get_analytics_config()
            
            # Get all segments for the groups
            all_segments = []
            group_files = []
            
            for group_id in group_ids:
                segments = self.get_group_segments(group_id)
                all_segments.extend(segments)
                
                # Collect unique file information
                for segment in segments:
                    file_info = {
                        'file_id': segment.get('file_id'),
                        'cell_name': self._get_cell_name_from_segment(segment),
                        'original_filename': segment.get('original_filename', segment.get('file_id'))
                    }
                    if file_info not in group_files:
                        group_files.append(file_info)
            
            if not all_segments:
                return {'error': 'No segments found for specified groups'}
            
            # Get cumulative context for the files
            context = calculator.get_group_cumulative_context(group_files)
            
            # Calculate temporal analytics
            temporal_data = {
                'segments': [],
                'time_series': {
                    'time_points': [],
                    'cumulative_capacity': [],
                    'cumulative_energy': [],
                    'individual_capacity': [],
                    'individual_energy': [],
                    'voltage_start': [],
                    'voltage_end': []
                },
                'summary': {
                    'total_duration_s': 0.0,
                    'total_capacity_ah': 0.0,
                    'total_energy_wh': 0.0,
                    'segment_count': len(all_segments),
                    'file_count': len(group_files)
                }
            }
            
            # Sort segments by start time for proper temporal order
            sorted_segments = sorted(all_segments, key=lambda s: s.get('start_time_s', 0))
            
            running_capacity = 0.0
            running_energy = 0.0
            
            for segment in sorted_segments:
                # Calculate cumulative values for this segment
                cumulative_values = calculator.calculate_segment_cumulative_values(segment, context)
                
                # Add to temporal data
                segment_capacity = segment.get('capacity_ah', 0.0)
                segment_energy = segment.get('energy_wh', 0.0)
                
                running_capacity += segment_capacity
                running_energy += segment_energy
                
                temporal_data['segments'].append({
                    **segment,
                    **cumulative_values
                })
                
                # Add to time series
                temporal_data['time_series']['time_points'].append(segment.get('start_time_s', 0))
                temporal_data['time_series']['cumulative_capacity'].append(running_capacity)
                temporal_data['time_series']['cumulative_energy'].append(running_energy)
                temporal_data['time_series']['individual_capacity'].append(segment_capacity)
                temporal_data['time_series']['individual_energy'].append(segment_energy)
                temporal_data['time_series']['voltage_start'].append(segment.get('start_potential_v', 0))
                temporal_data['time_series']['voltage_end'].append(segment.get('end_potential_v', 0))
            
            # Update summary
            if sorted_segments:
                temporal_data['summary'].update({
                    'total_duration_s': max(s.get('end_time_s', 0) for s in sorted_segments),
                    'total_capacity_ah': running_capacity,
                    'total_energy_wh': running_energy
                })
            
            return temporal_data
            
        except Exception as e:
            logger.error(f"Failed to get group temporal analytics: {e}")
            return {'error': str(e)}

    def get_group_fit_quality_statistics(self, group_ids: List[str]) -> Dict[str, Any]:
        """
        Get fitting quality statistics across group techniques.
        
        Args:
            group_ids: List of group IDs to analyze
            
        Returns:
            Dictionary with R² distributions and fit success rates
        """
        try:
            import json
            import numpy as np
            from collections import defaultdict
            
            # Get all segments for the groups
            all_segments = []
            for group_id in group_ids:
                segments = self.get_group_segments(group_id)
                all_segments.extend(segments)
            
            if not all_segments:
                return {'error': 'No segments found for specified groups'}
            
            # Collect fit quality data
            fit_quality = {
                'exponential_fits': defaultdict(list),
                'sqrt_fits': defaultdict(list),
                'overall_stats': {},
                'technique_breakdown': defaultdict(lambda: {
                    'total_segments': 0,
                    'successful_exp_fits': 0,
                    'successful_sqrt_fits': 0,
                    'exp_r2_values': [],
                    'sqrt_r2_values': []
                })
            }
            
            for segment in all_segments:
                technique = segment.get('fundamental_technique', 'Unknown')
                analysis_results = segment.get('analysis_results')
                
                fit_quality['technique_breakdown'][technique]['total_segments'] += 1
                
                if analysis_results:
                    try:
                        # Parse JSON if it's a string
                        if isinstance(analysis_results, str):
                            results = json.loads(analysis_results)
                        else:
                            results = analysis_results
                        
                        # Extract fitting results
                        all_coeffs = results.get('all_fit_coefficients', {})
                        
                        # Exponential fit data
                        exp_fits = all_coeffs.get('exponential_fits', {})
                        for variable, fit_data in exp_fits.items():
                            r2 = fit_data.get('r_squared', 0.0)
                            if r2 > 0:
                                fit_quality['exponential_fits'][variable].append(r2)
                                fit_quality['technique_breakdown'][technique]['exp_r2_values'].append(r2)
                                fit_quality['technique_breakdown'][technique]['successful_exp_fits'] += 1
                        
                        # sqrt(t) fit data
                        sqrt_fits = all_coeffs.get('sqrt_fits', {})
                        for variable, fit_data in sqrt_fits.items():
                            r2 = fit_data.get('r_squared', 0.0)
                            if r2 > 0:
                                fit_quality['sqrt_fits'][variable].append(r2)
                                fit_quality['technique_breakdown'][technique]['sqrt_r2_values'].append(r2)
                                fit_quality['technique_breakdown'][technique]['successful_sqrt_fits'] += 1
                                
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Failed to parse analysis results for segment {segment.get('id', 'unknown')}: {e}")
            
            # Calculate overall statistics
            all_exp_r2 = []
            all_sqrt_r2 = []
            
            for variable_r2_list in fit_quality['exponential_fits'].values():
                all_exp_r2.extend(variable_r2_list)
            
            for variable_r2_list in fit_quality['sqrt_fits'].values():
                all_sqrt_r2.extend(variable_r2_list)
            
            fit_quality['overall_stats'] = {
                'exponential_fits': {
                    'count': len(all_exp_r2),
                    'mean_r2': float(np.mean(all_exp_r2)) if all_exp_r2 else 0.0,
                    'std_r2': float(np.std(all_exp_r2)) if all_exp_r2 else 0.0,
                    'min_r2': float(np.min(all_exp_r2)) if all_exp_r2 else 0.0,
                    'max_r2': float(np.max(all_exp_r2)) if all_exp_r2 else 0.0
                },
                'sqrt_fits': {
                    'count': len(all_sqrt_r2),
                    'mean_r2': float(np.mean(all_sqrt_r2)) if all_sqrt_r2 else 0.0,
                    'std_r2': float(np.std(all_sqrt_r2)) if all_sqrt_r2 else 0.0,
                    'min_r2': float(np.min(all_sqrt_r2)) if all_sqrt_r2 else 0.0,
                    'max_r2': float(np.max(all_sqrt_r2)) if all_sqrt_r2 else 0.0
                },
                'total_segments': len(all_segments),
                'segments_with_fits': len([s for s in all_segments if s.get('analysis_results')])
            }
            
            # Convert defaultdicts to regular dicts for JSON serialization
            fit_quality['exponential_fits'] = dict(fit_quality['exponential_fits'])
            fit_quality['sqrt_fits'] = dict(fit_quality['sqrt_fits'])
            fit_quality['technique_breakdown'] = dict(fit_quality['technique_breakdown'])
            
            return fit_quality
            
        except Exception as e:
            logger.error(f"Failed to get group fit quality statistics: {e}")
            return {'error': str(e)}

    def get_group_voltage_correlation_analytics(self, group_ids: List[str]) -> Dict[str, Any]:
        """
        Get voltage correlation analytics for groups.
        
        Args:
            group_ids: List of group IDs to analyze
            
        Returns:
            Dictionary with correlation analysis between metrics and voltages
        """
        try:
            import numpy as np
            from scipy.stats import pearsonr, spearmanr
            
            # Get all segments for the groups
            all_segments = []
            for group_id in group_ids:
                segments = self.get_group_segments(group_id)
                all_segments.extend(segments)
            
            if not all_segments:
                return {'error': 'No segments found for specified groups'}
            
            # Extract relevant metrics
            metrics = {
                'start_voltage': [],
                'end_voltage': [],
                'capacity': [],
                'energy': [],
                'duration': [],
                'start_current': [],
                'end_current': []
            }
            
            for segment in all_segments:
                metrics['start_voltage'].append(segment.get('start_potential_v', 0.0))
                metrics['end_voltage'].append(segment.get('end_potential_v', 0.0))
                metrics['capacity'].append(segment.get('capacity_ah', 0.0))
                metrics['energy'].append(segment.get('energy_wh', 0.0))
                metrics['duration'].append(segment.get('duration_s', 0.0))
                metrics['start_current'].append(segment.get('start_current_a', 0.0))
                metrics['end_current'].append(segment.get('end_current_a', 0.0))
            
            # Calculate correlations
            correlations = {
                'vs_start_voltage': {},
                'vs_end_voltage': {},
                'summary': {
                    'segment_count': len(all_segments),
                    'voltage_range_start': [float(np.min(metrics['start_voltage'])), float(np.max(metrics['start_voltage']))],
                    'voltage_range_end': [float(np.min(metrics['end_voltage'])), float(np.max(metrics['end_voltage']))]
                }
            }
            
            # Correlations with start voltage
            for metric_name in ['capacity', 'energy', 'duration', 'end_voltage']:
                if len(metrics[metric_name]) > 2:  # Need at least 3 points for meaningful correlation
                    try:
                        pearson_r, pearson_p = pearsonr(metrics['start_voltage'], metrics[metric_name])
                        spearman_r, spearman_p = spearmanr(metrics['start_voltage'], metrics[metric_name])
                        
                        correlations['vs_start_voltage'][metric_name] = {
                            'pearson_r': float(pearson_r) if not np.isnan(pearson_r) else 0.0,
                            'pearson_p': float(pearson_p) if not np.isnan(pearson_p) else 1.0,
                            'spearman_r': float(spearman_r) if not np.isnan(spearman_r) else 0.0,
                            'spearman_p': float(spearman_p) if not np.isnan(spearman_p) else 1.0,
                            'data_points': len(metrics[metric_name])
                        }
                    except Exception as e:
                        logger.warning(f"Failed to calculate correlation for {metric_name} vs start_voltage: {e}")
                        correlations['vs_start_voltage'][metric_name] = {'error': str(e)}
            
            # Correlations with end voltage
            for metric_name in ['capacity', 'energy', 'duration', 'start_voltage']:
                if len(metrics[metric_name]) > 2:
                    try:
                        pearson_r, pearson_p = pearsonr(metrics['end_voltage'], metrics[metric_name])
                        spearman_r, spearman_p = spearmanr(metrics['end_voltage'], metrics[metric_name])
                        
                        correlations['vs_end_voltage'][metric_name] = {
                            'pearson_r': float(pearson_r) if not np.isnan(pearson_r) else 0.0,
                            'pearson_p': float(pearson_p) if not np.isnan(pearson_p) else 1.0,
                            'spearman_r': float(spearman_r) if not np.isnan(spearman_r) else 0.0,
                            'spearman_p': float(spearman_p) if not np.isnan(spearman_p) else 1.0,
                            'data_points': len(metrics[metric_name])
                        }
                    except Exception as e:
                        logger.warning(f"Failed to calculate correlation for {metric_name} vs end_voltage: {e}")
                        correlations['vs_end_voltage'][metric_name] = {'error': str(e)}
            
            return correlations
            
        except Exception as e:
            logger.error(f"Failed to get group voltage correlation analytics: {e}")
            return {'error': str(e)}

    def _get_cell_name_from_segment(self, segment: Dict[str, Any]) -> str:
        """Helper to get cell name from segment data."""
        # This would typically require a database lookup
        # For now, try to extract from existing data or return default
        return segment.get('cell_name', 'unknown')

    def get_cumulative_field_names(self) -> List[str]:
        """
        Get list of all cumulative field names from analytics config.
        
        Returns:
            List of field names that contain 'cumulative'
        """
        try:
            from src_clean.analysis.analytics_config import get_config as get_analytics_config
            
            config = get_analytics_config()
            cumulative_fields = list(config.get('segment_cumulative_fields', {}).keys())
            
            # Also check base fields for any with 'cumulative' in name
            base_fields = config.get('segment_base_fields', {})
            for field_name in base_fields.keys():
                if 'cumulative' in field_name.lower() and field_name not in cumulative_fields:
                    cumulative_fields.append(field_name)
            
            return cumulative_fields
            
        except Exception as e:
            logger.error(f"Failed to get cumulative field names: {e}")
            return []

    # =============================================================================
    # TAB 3 ANALYTICS - LAZY DATA & ELECTROCHEMICAL INSIGHTS
    # =============================================================================
    
    def create_lazy_data_query(self, file_infos: List[Dict[str, Any]]) -> str:
        """
        Create lazy data query for Tab 3 analysis.
        
        Args:
            file_infos: List of file info dictionaries
            
        Returns:
            Query ID for subsequent operations
        """
        try:
            return self.lazy_data_service.create_multi_file_lazy_query(file_infos)
        except Exception as e:
            logger.error(f"Failed to create lazy data query: {e}")
            raise
    
    def apply_data_filters(self, query_id: str, filters: Dict[str, Any]) -> str:
        """
        Apply filters to lazy data query.
        
        Args:
            query_id: Existing query ID
            filters: Filter conditions
            
        Returns:
            New query ID with filters applied
        """
        try:
            return self.lazy_data_service.apply_filters_to_query(query_id, filters)
        except Exception as e:
            logger.error(f"Failed to apply filters to query {query_id}: {e}")
            raise
    
    def materialize_data_for_visualization(self, query_id: str, 
                                         columns: Optional[List[str]] = None,
                                         limit: Optional[int] = None) -> pl.DataFrame:
        """
        Materialize lazy query data for visualization.
        
        Args:
            query_id: Query ID to materialize
            columns: Specific columns to load
            limit: Maximum rows to return
            
        Returns:
            Materialized Polars DataFrame
        """
        try:
            return self.lazy_data_service.materialize_query_for_viz(query_id, columns, limit)
        except Exception as e:
            logger.error(f"Failed to materialize query {query_id}: {e}")
            raise
    
    def get_electrochemical_rest_analysis(self, group_ids: List[str]) -> Dict[str, Any]:
        """
        Get electrochemical REST analysis for groups using unified pattern.
        
        Args:
            group_ids: List of group IDs to analyze
            
        Returns:
            REST relaxation kinetics analysis
        """
        try:
            # Get all segments for the groups
            all_segments = []
            for group_id in group_ids:
                segments = self.get_group_segments(group_id)
                all_segments.extend(segments)
            
            if not all_segments:
                return {'error': 'No segments found for specified groups'}
            
            # Extract relaxation kinetics using registry analysis
            kinetics_function = self.analysis_registry.get_analysis_function('kinetics_analysis')
            df_result = kinetics_function(all_segments, {})
            analysis_result = {'kinetics_data': df_result}
            
            # Add group context
            analysis_result['group_ids'] = group_ids
            analysis_result['analysis_timestamp'] = datetime.now().isoformat()
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in REST analysis for groups {group_ids}: {e}")
            return {'error': f'REST analysis error: {str(e)}'}
    
    def get_electrochemical_resistance_analysis(self, group_ids: List[str]) -> Dict[str, Any]:
        """
        Get electrochemical resistance analysis for GALVANOSTATIC groups.
        
        Args:
            group_ids: List of group IDs to analyze
            
        Returns:
            Instantaneous resistance analysis
        """
        try:
            # Get all segments for the groups
            all_segments = []
            for group_id in group_ids:
                segments = self.get_group_segments(group_id)
                all_segments.extend(segments)
            
            if not all_segments:
                return {'error': 'No segments found for specified groups'}
            
            # Calculate resistance using registry analysis
            resistance_function = self.analysis_registry.get_analysis_function('resistance_analysis')
            df_result = resistance_function(all_segments, {})
            analysis_result = {'resistance_data': df_result}
            
            # Add group context
            analysis_result['group_ids'] = group_ids
            analysis_result['analysis_timestamp'] = datetime.now().isoformat()
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in resistance analysis for groups {group_ids}: {e}")
            return {'error': f'Resistance analysis error: {str(e)}'}
    
    def get_electrochemical_equilibrium_analysis(self, group_ids: List[str]) -> Dict[str, Any]:
        """
        Get electrochemical equilibrium voltage analysis for groups.
        
        Args:
            group_ids: List of group IDs to analyze
            
        Returns:
            Equilibrium voltage tracking analysis
        """
        try:
            # Get all segments for the groups
            all_segments = []
            for group_id in group_ids:
                segments = self.get_group_segments(group_id)
                all_segments.extend(segments)
            
            if not all_segments:
                return {'error': 'No segments found for specified groups'}
            
            # Analyze equilibrium voltage using registry analysis
            equilibrium_function = self.analysis_registry.get_analysis_function('equilibrium_analysis')
            df_result = equilibrium_function(all_segments, {})
            analysis_result = {'equilibrium_data': df_result}
            
            # Add group context
            analysis_result['group_ids'] = group_ids
            analysis_result['analysis_timestamp'] = datetime.now().isoformat()
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in equilibrium analysis for groups {group_ids}: {e}")
            return {'error': f'Equilibrium analysis error: {str(e)}'}
    
    def get_electrochemical_current_decay_analysis(self, group_ids: List[str]) -> Dict[str, Any]:
        """
        Get electrochemical current decay analysis for POTENTIOSTATIC groups.
        
        Args:
            group_ids: List of group IDs to analyze
            
        Returns:
            Current decay kinetics analysis
        """
        try:
            # Get all segments for the groups
            all_segments = []
            for group_id in group_ids:
                segments = self.get_group_segments(group_id)
                all_segments.extend(segments)
            
            if not all_segments:
                return {'error': 'No segments found for specified groups'}
            
            # Analyze current decay using registry analysis
            decay_function = self.analysis_registry.get_analysis_function('current_decay_analysis')
            df_result = decay_function(all_segments, {})
            analysis_result = {'current_decay_data': df_result}
            
            # Add group context
            analysis_result['group_ids'] = group_ids
            analysis_result['analysis_timestamp'] = datetime.now().isoformat()
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in current decay analysis for groups {group_ids}: {e}")
            return {'error': f'Current decay analysis error: {str(e)}'}
    
    def get_unified_electrochemical_analysis(self, group_ids: List[str], 
                                           analysis_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get unified electrochemical analysis across all techniques.
        
        Args:
            group_ids: List of group IDs to analyze
            analysis_types: Optional list of specific analysis types to run
            
        Returns:
            Comprehensive electrochemical analysis
        """
        try:
            # Default to all analysis types if not specified
            if analysis_types is None:
                analysis_types = ['rest', 'resistance', 'equilibrium', 'current_decay']
            
            results = {
                'group_ids': group_ids,
                'analysis_timestamp': datetime.now().isoformat(),
                'analysis_types_requested': analysis_types,
                'results': {}
            }
            
            # Run each requested analysis type
            if 'rest' in analysis_types:
                results['results']['rest_relaxation'] = self.get_electrochemical_rest_analysis(group_ids)
            
            if 'resistance' in analysis_types:
                results['results']['instantaneous_resistance'] = self.get_electrochemical_resistance_analysis(group_ids)
            
            if 'equilibrium' in analysis_types:
                results['results']['equilibrium_voltage'] = self.get_electrochemical_equilibrium_analysis(group_ids)
            
            if 'current_decay' in analysis_types:
                results['results']['current_decay'] = self.get_electrochemical_current_decay_analysis(group_ids)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in unified electrochemical analysis for groups {group_ids}: {e}")
            return {'error': f'Unified analysis error: {str(e)}'}
    
    def get_lazy_query_info(self, query_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a cached lazy query."""
        try:
            return self.lazy_data_service.get_query_info(query_id)
        except Exception as e:
            logger.error(f"Failed to get query info for {query_id}: {e}")
            return None
    
    def cleanup_lazy_query(self, query_id: str) -> bool:
        """Remove specific lazy query from cache."""
        try:
            return self.lazy_data_service.cleanup_query(query_id)
        except Exception as e:
            logger.error(f"Failed to cleanup query {query_id}: {e}")
            return False

    # =============================================================================
    # ADVANCED RESEARCH TAB METHODS
    # =============================================================================

    def get_available_research_cells(self) -> List[str]:
        """Get list of cells available for advanced research analytics."""
        try:
            cells = self.get_cells()
            return [cell['name'] for cell in cells if cell['name']]
        except Exception as e:
            logger.error(f"Failed to get research cells: {e}")
            return []

    def get_clean_segment_data_for_perspective(self, cells: List[str] = None, 
                                             temperature: float = None) -> pl.DataFrame:
        """Get clean segment data without complex JSON fields for Perspective compatibility."""
        try:
            logger.info(f"Loading clean segment data for cells: {cells}, temperature: {temperature}")
            
            # Get segments data for all cells or filtered cells
            if cells:
                # Filter by specific cells
                segments_data = []
                for cell_name in cells:
                    cell_segments = self.get_cell_segments(cell_name)
                    if cell_segments:
                        segments_data.extend(cell_segments)
            else:
                # Get all cells
                all_cells = self.get_cells()
                segments_data = []
                for cell in all_cells:
                    cell_segments = self.get_cell_segments(cell['name'])
                    if cell_segments:
                        segments_data.extend(cell_segments)
            
            if not segments_data:
                logger.warning("No segments found for perspective dataset")
                return pl.DataFrame()
            
            # Remove complex JSON fields that cause Perspective issues
            clean_segments_data = []
            for segment in segments_data:
                clean_segment = {k: v for k, v in segment.items() 
                               if k not in ['segment_metadata', 'analysis_results', 'groups']}
                clean_segments_data.append(clean_segment)
            
            # Convert to Polars DataFrame
            df = pl.DataFrame(clean_segments_data)
            
            # Add computed columns for better research analysis
            df = df.with_columns([
                # Time-based columns
                (pl.col("duration_s") / 3600).alias("duration_hours"),
                
                # Power and efficiency calculations
                (pl.col("energy_wh") / pl.col("duration_s") * 3600).alias("avg_power_w"),
                pl.when(pl.col("capacity_ah") > 0)
                .then(pl.col("energy_wh") / pl.col("capacity_ah"))
                .otherwise(None)
                .alias("energy_density_wh_per_ah"),
                
                # Efficiency columns
                pl.when(pl.col("capacity_cumulative_ah") > 0)
                .then(pl.col("discharge_cumulative_ah") / pl.col("capacity_cumulative_ah") * 100)
                .otherwise(None)
                .alias("coulombic_efficiency_pct"),
            ])
            
            # Apply temperature filter if specified
            if temperature is not None and "temperature" in df.columns:
                df = df.filter(pl.col("temperature") == temperature)
            
            logger.info(f"Clean segment data loaded: {len(df)} segments")
            return df
            
        except Exception as e:
            logger.error(f"Failed to get clean segment data: {e}")
            return pl.DataFrame()

    def get_research_dataset_for_perspective(self, cells: List[str] = None, 
                                           temperature: float = None) -> pl.DataFrame:
        """Get comprehensive dataset with full analytics pipeline for Perspective analysis."""
        try:
            logger.info(f"Loading comprehensive research dataset for cells: {cells}, temperature: {temperature}")
            
            # Step 1: Get clean segment data (no JSON fields)
            clean_segments_df = self.get_clean_segment_data_for_perspective(cells, temperature)
            
            if clean_segments_df.is_empty():
                logger.warning("No clean segments found for comprehensive dataset")
                return clean_segments_df
            
            # Convert to pandas for analytics processing
            segments_data = []
            if cells:
                for cell_name in cells:
                    cell_segments = self.get_cell_segments(cell_name)
                    if cell_segments:
                        segments_data.extend(cell_segments)
            else:
                all_cells = self.get_cells()
                for cell in all_cells:
                    cell_segments = self.get_cell_segments(cell['name'])
                    if cell_segments:
                        segments_data.extend(cell_segments)
            
            if not segments_data:
                return clean_segments_df
            
            # Step 2: Run analytics pipeline
            analytics_results = self._run_comprehensive_analytics_pipeline(segments_data)
            
            # Step 3: Convert clean segments to pandas for joining
            pandas_clean_df = clean_segments_df.to_pandas()
            
            # Step 4: Join all analytics results
            final_df = pandas_clean_df.copy()
            
            # Simple merge using 'id' column (no more segment_id conflicts!)
            logger.info(f"Starting merge with {len(analytics_results)} analytics results")
            for analysis_name, analysis_df in analytics_results.items():
                if not analysis_df.empty:
                    logger.info(f"Merging {analysis_name}: {analysis_df.shape}")
                    logger.info(f"  Analysis has 'id': {'id' in analysis_df.columns}")
                    logger.info(f"  Base DataFrame has 'id': {'id' in final_df.columns}")
                    
                    # Check for overlapping columns (excluding 'id')
                    overlap_cols = [col for col in analysis_df.columns if col in final_df.columns and col != 'id']
                    if overlap_cols:
                        logger.warning(f"  Overlapping columns: {overlap_cols}")
                    
                    final_df = final_df.merge(
                        analysis_df,
                        on='id',  # Clean merge using matching id columns
                        how='left',
                        suffixes=('', f'_{analysis_name}')  # Add analysis name suffix for conflicts
                    )
                    
                    logger.info(f"After merge: {final_df.shape}")
            
            # Clean NaN values for Perspective compatibility - avoid Polars conversion issues
            logger.info(f"Cleaning NaN values from {len(final_df)} rows, {len(final_df.columns)} columns")
            
            # Instead of converting back to Polars, return pandas DataFrame directly
            # to avoid type conversion issues
            for col in final_df.columns:
                # if col.startswith('analytics_') and final_df[col].isnull().any():
                if final_df[col].isnull().any():

                    # Get the actual data type by examining non-null values
                    non_null_values = final_df[col].dropna()
                    
                    if len(non_null_values) == 0:
                        # All values are null, keep as float to avoid conversion issues
                        final_df[col] = final_df[col].fillna(0.0)
                        logger.debug(f"Column {col}: All null, filled with 0.0")
                        
                    elif non_null_values.dtype in ['float64', 'float32']:
                        # Numeric column - fill with 0.0
                        final_df[col] = final_df[col].fillna(0.0)
                        logger.debug(f"Column {col}: Float, filled with 0.0")
                        
                    elif non_null_values.dtype in ['int64', 'int32']:
                        # Integer column - fill with 0
                        final_df[col] = final_df[col].fillna(0)
                        logger.debug(f"Column {col}: Integer, filled with 0")
                        
                    elif non_null_values.dtype == 'bool' or 'is_high_quality' in col or col.endswith('_flag') or col.endswith('_bool'):
                        # Boolean column - fill with False, keep as bool
                        final_df[col] = final_df[col].fillna(False).astype('bool')
                        logger.debug(f"Column {col}: Boolean, filled with False")
                        
                    else:
                        # For string/object columns - keep as strings, Perspective handles them well
                        final_df[col] = final_df[col].astype('object').fillna('N/A')
                        logger.debug(f"Column {col}: String/Object type, filled with 'N/A'")
            
            # Return pandas DataFrame directly - convert to Polars later if needed
            logger.info(f"Analytics pipeline complete: {len(final_df)} rows × {len(final_df.columns)} columns")
            logger.info(f"Analytics columns: {len([c for c in final_df.columns if c.startswith('analytics_')])}")
            
            # Convert to Polars using from_pandas for better type inference
            try:
                result_df = pl.from_pandas(final_df)
            except Exception as conversion_error:
                logger.warning(f"Polars conversion failed: {conversion_error}, returning clean data only")
                # Fallback to clean data without analytics
                return clean_segments_df
            
            logger.info(f"Comprehensive dataset loaded: {len(result_df)} rows × {len(result_df.columns)} columns")
            return result_df
            
        except Exception as e:
            logger.error(f"Failed to get comprehensive research dataset: {e}")
            return pl.DataFrame()

    def _run_comprehensive_analytics_pipeline(self, segments_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run all registered analytics on segments and return results for joining."""
        try:
            from src_clean.analysis.registry import get_analysis_registry
            
            registry = get_analysis_registry()
            analytics_results = {}
            
            logger.info(f"Running comprehensive analytics on {len(segments_data)} segments")
            
            # Get all available analysis types from registry automatically  
            available_analysis = registry.get_analysis_options()
            analysis_types = [analysis_id for _, analysis_id in available_analysis if analysis_id != 'basic_statistics']
            
            # All analytics enabled with clean id-based merging!
            # analysis_types = ['kinetics_analysis']  # Debug mode - now working!
            
            logger.info(f"Running {len(analysis_types)} analytics from registry: {analysis_types}")
            
            for analysis_name in analysis_types:
                try:
                    logger.debug(f"Running {analysis_name}...")
                    
                    # # Execute analysis - call functions directly to use include_segment_data=False
                    # if analysis_name == 'kinetics_analysis':
                    #     from src_clean.analysis.kinetics_analysis import kinetics_analysis_function
                    #     df = kinetics_analysis_function(segments_data, {}, include_segment_data=False)
                    # elif analysis_name == 'current_decay_analysis':
                    #     from src_clean.analysis.current_decay_analysis import current_decay_analysis_function
                    #     df = current_decay_analysis_function(segments_data, {}, include_segment_data=False)
                    # elif analysis_name == 'resistance_analysis':
                    #     from src_clean.analysis.resistance_analysis import resistance_analysis_function
                    #     df = resistance_analysis_function(segments_data, {}, include_segment_data=False)
                    # elif analysis_name == 'equilibrium_analysis':
                    #     from src_clean.analysis.equilibrium_analysis import equilibrium_analysis_function
                    #     df = equilibrium_analysis_function(segments_data, {}, include_segment_data=False)
                    # else:
                    #     # For other analyses, use registry (will include full segment data)
                    df = registry.execute_analysis(analysis_name, segments_data, {}, include_segment_data=False)


                    # Store results if valid
                    if isinstance(df, pd.DataFrame) and not df.empty:
                        logger.info(f"✅ {analysis_name}: {len(df)} rows, {len(df.columns)} columns")
                        logger.debug(f"  Columns: {list(df.columns)[:10]}...")
                        logger.debug(f"  Has 'id' column: {'id' in df.columns}")
                        
                        # NOTE: Analysis functions now return pre-prefixed columns
                        # No need to rename columns here anymore!
                        analytics_results[analysis_name] = df
                    else:
                        logger.warning(f"⚠️  {analysis_name}: No results or invalid DataFrame")
                        
                except Exception as e:
                    logger.error(f"❌ {analysis_name} failed: {e}")
                    # Create error DataFrame
                    segment_ids = [seg.get('id') for seg in segments_data if seg.get('id')]
                    error_df = pd.DataFrame({
                        'segment_id': segment_ids,
                        f'analytics_{analysis_name}_error': [str(e)] * len(segment_ids)
                    })
                    analytics_results[analysis_name] = error_df
            
            logger.info(f"Analytics pipeline completed: {len(analytics_results)} analysis types")
            return analytics_results
            
        except Exception as e:
            logger.error(f"Analytics pipeline failed: {e}")
            return {}

    def get_research_data_summary(self, cells: List[str] = None) -> Dict[str, Any]:
        """Get summary statistics for dataset selection."""
        try:
            # Get basic counts
            if cells:
                total_segments = 0
                total_files = 0
                for cell_name in cells:
                    cell_segments = self.get_cell_segments(cell_name)
                    if cell_segments:
                        total_segments += len(cell_segments)
                        # Count unique files
                        unique_files = set()
                        for seg in cell_segments:
                            if seg.get('file_id'):
                                unique_files.add(seg['file_id'])
                        total_files += len(unique_files)
                
                cell_count = len(cells)
            else:
                all_cells = self.get_cells()
                cell_count = len(all_cells)
                
                total_segments = 0
                total_files = 0
                for cell in all_cells:
                    cell_segments = self.get_cell_segments(cell['name'])
                    if cell_segments:
                        total_segments += len(cell_segments)
                        unique_files = set()
                        for seg in cell_segments:
                            if seg.get('file_id'):
                                unique_files.add(seg['file_id'])
                        total_files += len(unique_files)
            
            # Get time range
            try:
                # Use LazyDataService for efficient time range query
                query_id = self.lazy_data_service.create_segments_query(
                    cell_filters=cells if cells else None
                )
                if query_id:
                    query_info = self.lazy_data_service.get_query_info(query_id)
                    # Note: This is a placeholder - LazyDataService would need enhancement 
                    # for time range calculation
                    time_range = "Available"
                else:
                    time_range = "Unknown"
            except Exception:
                time_range = "Unknown"
            
            # Get available techniques
            try:
                dataset = self.get_research_dataset_for_perspective(cells)
                if len(dataset) > 0 and "technique_name" in dataset.columns:
                    techniques = dataset.get_column("technique_name").unique().to_list()
                else:
                    techniques = []
            except Exception:
                techniques = []
            
            summary = {
                'cell_count': cell_count,
                'total_segments': total_segments,
                'total_files': total_files,
                'time_range': time_range,
                'techniques': techniques,
                'data_scale': 'Large' if total_segments > 1000 else 'Medium' if total_segments > 100 else 'Small',
                'estimated_rows': total_segments  # Each segment = 1 row in research view
            }
            
            logger.info(f"Research data summary: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get research data summary: {e}")
            return {
                'cell_count': 0,
                'total_segments': 0, 
                'total_files': 0,
                'time_range': 'Error',
                'techniques': [],
                'data_scale': 'Unknown',
                'estimated_rows': 0,
                'error': str(e)
            }

# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_backend_instance = None

def get_backend_api(data_dir: Path = None, db_path: Path = None) -> BackendAPI:
    """Get singleton backend API instance."""
    global _backend_instance
    if _backend_instance is None:
        _backend_instance = BackendAPI(data_dir, db_path)
    return _backend_instance