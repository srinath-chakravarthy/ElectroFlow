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

from ..core import DatabaseManager, format_error_for_user, is_user_error
from ..core.data_models import DataFile
from ..core.exceptions import (
    ElectrochemicalAnalysisError, DatabaseError, ProcessingError,
    RecordNotFoundError
)
from ..parsers import get_parser_factory, auto_parse_dual_files

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
        """Initialize backend API."""
        self.data_dir = Path(data_dir) if data_dir else Path("data_clean")
        self.db_path = Path(db_path) if db_path else (self.data_dir / "electrochemical.db")
        
        # Create directories
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "processed").mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.db = DatabaseManager(self.db_path)
        self.parser_factory = get_parser_factory()
        
        logger.info(f"Backend API initialized - Data: {self.data_dir}, DB: {self.db_path}")
    
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
            
            return ProcessingResult(
                success=True,
                file_id=str(cell_id),
                message=f"Cell '{name}' created successfully"
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
        """Delete cell and all associated data."""
        try:
            success = self.db.delete_cell(cell_id)
            
            if success:
                return ProcessingResult(
                    success=True,
                    message=f"Cell {cell_id} deleted successfully"
                )
            else:
                return ProcessingResult(
                    success=False,
                    error=f"Cell {cell_id} not found"
                )
                
        except Exception as e:
            error_info = format_error_for_user(e)
            return ProcessingResult(
                success=False,
                error=error_info['message']
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
            
            # Parse files using auto-detection
            data_file = auto_parse_dual_files(metadata_path, data_path)
            
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
        # Prepare file information
        parquet_path = self.data_dir / "processed" / f"{file_id}.parquet"
        
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
        """Generate segment information from DataFile."""
        segments = []
        segment_boundaries = data_file.get_segment_boundaries()
        
        for i, boundary in enumerate(segment_boundaries):
            # Get technique mapping from database
            technique_id = boundary.get('technique_id')
            if technique_id is not None:
                mapping = self.db.get_actionid_mapping(technique_id)
                if mapping:
                    technique_name = mapping['technique_name']
                    fundamental_technique = mapping['fundamental_technique']
                else:
                    technique_name = f"ActionID_{technique_id}"
                    fundamental_technique = "unknown"
            else:
                technique_name = "Unknown"
                fundamental_technique = "unknown"
            
            segments.append({
                'segment_index': i,
                'technique_id': technique_id,
                'technique_name': technique_name,
                'fundamental_technique': fundamental_technique,
                'start_row': boundary['start_row'],
                'end_row': boundary['end_row'],
                'start_time_s': boundary['start_time_s'],
                'end_time_s': boundary['end_time_s'],
                'point_count': boundary['point_count'],
                'segment_metadata': {}
            })
        
        return segments
    
    def _generate_processing_summary(self, data_file: DataFile) -> str:
        """Generate human-readable processing summary."""
        segments = data_file.get_segment_boundaries()
        techniques = []
        
        for segment in segments:
            technique_id = segment.get('technique_id')
            if technique_id is not None:
                mapping = self.db.get_actionid_mapping(technique_id)
                if mapping:
                    techniques.append(mapping['fundamental_technique'])
                else:
                    techniques.append(f"ActionID_{technique_id}")
        
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
    
    def delete_file(self, file_id: str) -> bool:
        """Delete a file and all associated data."""
        try:
            # Get file info first to access parquet file path
            file_info = self.db.get_file_by_id(file_id)
            if not file_info:
                logger.warning(f"File {file_id} not found in database")
                return False
            
            # Delete from database (this will cascade to segments)
            success = self.db.delete_file(file_id)
            
            if success:
                # Delete parquet file if it exists
                parquet_path = file_info.get('parquet_file_path')
                if parquet_path and Path(parquet_path).exists():
                    try:
                        Path(parquet_path).unlink()
                        logger.info(f"Deleted parquet file: {parquet_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete parquet file {parquet_path}: {e}")
                
                logger.info(f"Successfully deleted file: {file_id}")
                return True
            else:
                logger.error(f"Failed to delete file {file_id} from database")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete file '{file_id}': {e}")
            return False
    
    def delete_cell(self, cell_name: str) -> bool:
        """Delete a cell and all associated data (cascade delete)."""
        try:
            # Get cell info first
            cell = self.db.get_cell_by_name(cell_name)
            if not cell:
                logger.warning(f"Cell '{cell_name}' not found")
                return False
            
            cell_id = cell['id']
            
            # Get all files for the cell to delete parquet files
            files = self.db.get_cell_files(cell_id)
            
            # Delete all parquet files first
            deleted_parquet_count = 0
            for file_info in files:
                parquet_path = file_info.get('parquet_file_path')
                if parquet_path and Path(parquet_path).exists():
                    try:
                        Path(parquet_path).unlink()
                        deleted_parquet_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete parquet file {parquet_path}: {e}")
            
            # Delete cell from database (this will cascade to files and segments)
            success = self.db.delete_cell(cell_id)
            
            if success:
                logger.info(f"Successfully deleted cell '{cell_name}' with {deleted_parquet_count} parquet files")
                return True
            else:
                logger.error(f"Failed to delete cell '{cell_name}' from database")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete cell '{cell_name}': {e}")
            return False
    
    # =============================================================================
    # ACTIONID MANAGEMENT
    # =============================================================================
    
    def get_actionid_mappings(self) -> List[Dict[str, Any]]:
        """Get all ActionID mappings."""
        try:
            return self.db.get_all_actionid_mappings()
        except Exception as e:
            logger.error(f"Failed to get ActionID mappings: {e}")
            return []
    
    def add_actionid_mapping(self, action_id: int, technique_name: str, 
                           fundamental_technique: str) -> ProcessingResult:
        """Add new ActionID mapping."""
        try:
            success = self.db.add_actionid_mapping(
                action_id, technique_name, fundamental_technique
            )
            
            if success:
                return ProcessingResult(
                    success=True,
                    message=f"ActionID {action_id} mapped to {fundamental_technique}"
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
            
            # Get known ActionIDs from database
            known_mappings = self.get_actionid_mappings()
            known_actionids = {mapping['action_id'] for mapping in known_mappings}
            
            # Return unknown ActionIDs
            return list(data_actionids - known_actionids)
            
        except Exception as e:
            logger.error(f"Failed to discover unknown ActionIDs: {e}")
            return []
    
    # =============================================================================
    # VALIDATION
    # =============================================================================
    
    def validate_dual_files(self, metadata_path: Path, data_path: Path) -> Dict[str, Any]:
        """Validate dual file pair."""
        try:
            # Use parser factory for validation
            parser = self.parser_factory.auto_detect_parser(metadata_path)
            
            if hasattr(parser, 'validate_dual_files'):
                valid = parser.validate_dual_files(metadata_path, data_path)
                
                if valid:
                    return {
                        'success': True,
                        'message': 'Files validated successfully',
                        'instrument': parser.get_instrument_name()
                    }
                else:
                    return {
                        'success': False,
                        'error': 'File validation failed'
                    }
            else:
                return {
                    'success': False,
                    'error': 'Single file parser detected, expected dual files'
                }
                
        except Exception as e:
            error_info = format_error_for_user(e)
            return {
                'success': False,
                'error': error_info['message']
            }
    
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
    
    def cleanup_failed_processing(self) -> int:
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
                
                cleaned = 0
                for file_id, parquet_path in failed_files:
                    # Delete database record
                    if self.db.delete_file(file_id):
                        cleaned += 1
                        
                    # Delete parquet file if exists
                    if parquet_path and Path(parquet_path).exists():
                        Path(parquet_path).unlink()
                
                logger.info(f"Cleaned up {cleaned} failed processing attempts")
                return cleaned
                
        except Exception as e:
            logger.error(f"Failed to cleanup failed processing: {e}")
            return 0


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