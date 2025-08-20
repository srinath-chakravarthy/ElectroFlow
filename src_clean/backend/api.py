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
                'segment_index': i,
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
    
    def create_group(self, cell_name: str, group_name: str, description: str = "") -> ProcessingResult:
        """Create a new user group for organizing segments."""
        try:
            # Get cell ID
            cell = self.db.get_cell_by_name(cell_name)
            if not cell:
                return ProcessingResult(
                    success=False,
                    error=f"Cell '{cell_name}' not found"
                )
            
            group_id = self.db.create_group(cell['id'], group_name, description)
            
            return ProcessingResult(
                success=True,
                file_id=str(group_id),  # Using file_id field for group_id
                message=f"Created group '{group_name}' successfully"
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
            
            return self.db.get_cell_segments_with_groups(cell['id'])
            
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