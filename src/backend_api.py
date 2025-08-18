"""
Clean, simplified backend API for battery data analysis.

Reflects the actual workflow:
1. Validate files → Check format compatibility
2. Extract metadata → Get ActionID mappings from .par files  
3. Process data → Parse .par.csv with proper schema
4. Store in database → Cell + files + ActionID mappings
5. Query data → Retrieve processed data for analysis

This API is UI-agnostic and works with Qt, Panel, CLI, and web interfaces.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
import polars as pl
import pandas as pd

from core.database import DatabaseManager
from core.parsers import VersaStudioParser
from io_utils.storage_v2 import DatabaseStorageManager

logger = logging.getLogger(__name__)


class ValidationResult:
    """Simple validation result."""
    def __init__(self, success: bool, message: str = "", details: Dict = None):
        self.success = success
        self.message = message
        self.details = details or {}


class ProcessingResult:
    """File processing result."""
    def __init__(self, success: bool, file_id: str = "", message: str = "", error: str = ""):
        self.success = success
        self.file_id = file_id
        self.message = message
        self.error = error


class UnknownActionID:
    """Unknown ActionID that needs user mapping."""
    def __init__(self, action_id: int, technique_name: str, occurrences: int):
        self.action_id = action_id
        self.technique_name = technique_name
        self.occurrences = occurrences


class BackendAPI:
    """
    Clean, workflow-focused backend API.
    
    Provides simple methods that match our actual data processing workflow.
    Each method does one clear thing with minimal complexity.
    """

    def __init__(self, data_dir: Path = None, db_path: Path = None):
        """Initialize backend API with database and storage."""
        self.data_dir = data_dir or Path("data")
        self.db_path = db_path or (self.data_dir / "battery_data.db")
        
        # Core components
        self.db = DatabaseManager(self.db_path)
        self.storage = DatabaseStorageManager(self.data_dir, self.db_path)
        self.parser = VersaStudioParser()
        
        logger.info(f"Backend API initialized with data_dir: {self.data_dir}")

    # =============================================================================
    # FILE VALIDATION (Simple & Fast)
    # =============================================================================

    def validate_files(self, file_paths: List[Path]) -> ValidationResult:
        """
        Lightweight file format validation only.
        
        Args:
            file_paths: List of file paths to validate
            
        Returns:
            ValidationResult with success status and details
        """
        try:
            par_files = []
            csv_files = []
            invalid_files = []
            
            # Simple format validation only
            for file_path in file_paths:
                if not file_path.exists():
                    invalid_files.append(f"File not found: {file_path.name}")
                    continue
                    
                if file_path.suffix.lower() == '.par':
                    if self.parser.validate_file(file_path):
                        par_files.append(file_path)
                    else:
                        invalid_files.append(f"Invalid .par format: {file_path.name}")
                        
                elif str(file_path).lower().endswith('.par.csv'):
                    # Basic CSV header check only
                    if self._validate_csv_headers(file_path):
                        csv_files.append(file_path)
                    else:
                        invalid_files.append(f"Invalid CSV format: {file_path.name}")
                else:
                    invalid_files.append(f"Unsupported file type: {file_path.name}")
            
            # Check for dual file pairs
            dual_pairs = []
            for par_file in par_files:
                csv_name = par_file.name + '.csv'
                for csv_file in csv_files:
                    if csv_file.name == csv_name:
                        dual_pairs.append((par_file, csv_file))
                        break
            
            success = len(invalid_files) == 0 and len(dual_pairs) > 0
            
            details = {
                'par_files': [str(f) for f in par_files],
                'csv_files': [str(f) for f in csv_files], 
                'dual_pairs': [(str(p), str(c)) for p, c in dual_pairs],
                'invalid_files': invalid_files,
                'total_valid': len(par_files) + len(csv_files),
                'has_dual_pairs': len(dual_pairs) > 0
            }
            
            if success:
                message = f"Validated {len(dual_pairs)} file pairs successfully"
            else:
                message = f"Validation failed: {invalid_files}"
            
            return ValidationResult(success, message, details)
            
        except Exception as e:
            logger.error(f"File validation error: {e}")
            return ValidationResult(False, f"Validation error: {str(e)}")

    def _validate_csv_headers(self, csv_path: Path) -> bool:
        """Fast CSV header validation only."""
        try:
            with open(csv_path, 'r') as f:
                header = f.readline().strip()
                # Check for key VersaStudio CSV columns
                required = ['Potential (V)', 'Current (A)', 'Elapsed Time (s)']
                return all(col in header for col in required)
        except:
            return False

    # =============================================================================
    # FILE PROCESSING (Core Workflow)
    # =============================================================================

    def upload_par_file(self, par_path: Path, cell_name: str) -> ProcessingResult:
        """
        Upload .par file and extract ActionID mappings (metadata only).
        
        Args:
            par_path: Path to .par file
            cell_name: Target cell name
            
        Returns:
            ProcessingResult with ActionID mappings extracted
        """
        try:
            file_id, status = self.storage.upload_file(par_path, cell_name, "par")
            
            if status == "skipped":
                return ProcessingResult(False, "", "Upload skipped by user")
            
            message = f"PAR file processed: {file_id} (metadata and ActionID mappings extracted)"
            return ProcessingResult(True, file_id, message)
            
        except Exception as e:
            logger.error(f"PAR file upload failed: {e}")
            return ProcessingResult(False, "", "", str(e))

    def upload_csv_file(self, csv_path: Path, cell_name: str) -> ProcessingResult:
        """
        Upload .par.csv file and process calibrated data.
        
        Args:
            csv_path: Path to .par.csv file
            cell_name: Target cell name
            
        Returns:
            ProcessingResult with calibrated data processed
        """
        try:
            file_id, status = self.storage.upload_file(csv_path, cell_name, "par_csv")
            
            if status == "skipped":
                return ProcessingResult(False, "", "Upload skipped by user")
                
            message = f"CSV file processed: {file_id} (calibrated data ready for analysis)"
            return ProcessingResult(True, file_id, message)
            
        except Exception as e:
            logger.error(f"CSV file upload failed: {e}")
            return ProcessingResult(False, "", "", str(e))

    def process_dual_files(self, par_path: Path, csv_path: Path, cell_name: str, 
                          upload_options: Dict[str, Any] = None) -> Tuple[ProcessingResult, Optional[pl.DataFrame]]:
        """
        Clean processing pipeline using parser's dual file processing.
        
        Args:
            par_path: Path to .par file (metadata source)
            csv_path: Path to .par.csv file (data source) 
            cell_name: Target cell name
            upload_options: Processing options (temperature, etc.)
            
        Returns:
            Tuple[ProcessingResult, Optional[pl.DataFrame]]: Result and universal schema data
        """
        try:
            upload_options = upload_options or {}
            logger.info(f"Processing dual files: {par_path.name} + {csv_path.name}")
            
            # Use parser's dual file processing - returns universal schema
            data_file = self.parser.parse_dual_files(par_path, csv_path)
            
            # Commit to database atomically
            file_id = self._commit_data_file(data_file, cell_name, par_path, csv_path, upload_options)
            
            # Generate summary from universal schema data
            summary = self._get_data_file_summary(data_file)
            techniques = ', '.join(summary['techniques_detected'])
            
            message = f"Processed {summary['segment_count']} segments, {len(summary['techniques_detected'])} techniques: {techniques}"
            
            return (
                ProcessingResult(True, file_id, message),
                data_file.universal_data  # Return universal schema DataFrame
            )
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            return (
                ProcessingResult(False, "", "", str(e)),
                None
            )

    def _commit_data_file(self, data_file, cell_name: str, par_path: Path, csv_path: Path, 
                         upload_options: Dict[str, Any]) -> str:
        """Commit DataFile to database and storage atomically."""
        # Generate unique file_id
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_id = f"{cell_name}_{par_path.stem}_{timestamp}"
        
        # Get or create cell
        cell = self.db.get_cell_by_name(cell_name)
        if not cell:
            cell_id = self.db.create_cell(cell_name)
        else:
            cell_id = cell['id']
        
        # Write parquet file to storage
        parquet_path = self.data_dir / "processed" / f"{file_id}.parquet"
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        data_file.universal_data.write_parquet(parquet_path)
        
        # Prepare file info for database
        file_info = {
            'file_id': file_id,
            'original_filename': par_path.name,
            'paired_filename': csv_path.name,
            'file_hash': self._calculate_file_hash(par_path),
            'raw_file_path': str(par_path),
            'parquet_file_path': str(parquet_path),
            'acquisition_start': data_file.metadata.get('acquisition_start'),
            'temperature_c': upload_options.get('temperature_c', 25.0),
            'metadata': data_file.metadata
        }
        
        # Generate segments from universal data
        segments = self._generate_segments_from_universal_data(data_file, file_id)
        
        # Atomic database transaction
        with self.db.get_connection() as conn:
            conn.execute("BEGIN")
            try:
                # Add file to database
                self.db.add_file_to_cell(cell_id, file_info)
                
                # Add segments to database
                self.db.add_segments_to_file(file_id, cell_name, segments)
                
                # Update file status to completed
                self.db.update_file_processing_status(file_id, 'completed')
                
                conn.commit()
                logger.info(f"Successfully committed data file: {file_id}")
                
            except Exception as e:
                conn.rollback()
                # Clean up parquet file on database failure
                if parquet_path.exists():
                    parquet_path.unlink()
                raise e
        
        return file_id

    def _generate_segments_from_universal_data(self, data_file, file_id: str) -> List[Dict[str, Any]]:
        """Generate segments from universal schema data."""
        df = data_file.universal_data
        segments = []
        
        # Use universal schema column names
        if 'technique_id' not in df.columns:
            # Single segment if no technique_id column
            time_min = float(df.get_column('time_s').min()) if 'time_s' in df.columns else 0.0
            time_max = float(df.get_column('time_s').max()) if 'time_s' in df.columns else 0.0
            
            return [{
                'segment_index': 0,
                'action_id': None,
                'technique_name': 'Unknown',
                'fundamental_technique': 'Unknown',
                'start_row': 0,
                'end_row': df.height - 1,
                'start_time_s': time_min,
                'end_time_s': time_max,
                'point_count': df.height
            }]
        
        # Group by technique_id to create segments
        action_groups = df.group_by('technique_id').agg([
            pl.col('time_s').min().alias('start_time'),
            pl.col('time_s').max().alias('end_time'),
            pl.len().alias('point_count')
        ])
        
        for i, group in enumerate(action_groups.iter_rows(named=True)):
            action_id = group['technique_id']
            
            # Get technique mapping from database
            mapping = self.db.get_actionid_mapping(action_id)
            if mapping:
                technique_name = mapping['technique_name']
                fundamental_technique = mapping['fundamental_technique']
            else:
                technique_name = f'ActionID_{action_id}'
                fundamental_technique = 'Unknown'
            
            segments.append({
                'segment_index': i,
                'action_id': action_id,
                'technique_name': technique_name,
                'fundamental_technique': fundamental_technique,
                'start_row': 0,  # Would need row mapping for actual start/end rows
                'end_row': int(group['point_count']) - 1,
                'start_time_s': float(group['start_time']),
                'end_time_s': float(group['end_time']),
                'point_count': int(group['point_count'])
            })
        
        return segments

    def _get_data_file_summary(self, data_file) -> Dict[str, Any]:
        """Get summary from DataFile with universal schema."""
        df = data_file.universal_data
        techniques = []
        
        if 'technique_id' in df.columns:
            unique_actions = df.get_column('technique_id').unique().to_list()
            for action_id in unique_actions:
                if action_id is not None:
                    mapping = self.db.get_actionid_mapping(action_id)
                    if mapping:
                        techniques.append(mapping['fundamental_technique'])
                    else:
                        techniques.append(f'ActionID_{action_id}')
        
        return {
            'file_count': 1,
            'techniques_detected': list(set(techniques)) if techniques else ['Unknown'],
            'segment_count': len(set(techniques)) if techniques else 1,
            'actionid_mappings': {}
        }


    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        import hashlib
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _get_in_memory_summary(self, analyzed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary from in-memory analyzed data."""
        segments = analyzed_data['segments']
        techniques = list(set(seg['fundamental_technique'] for seg in segments))
        
        return {
            'file_count': 1,
            'techniques_detected': techniques,
            'segment_count': len(segments),
            'actionid_mappings': analyzed_data.get('actionid_mappings', {})
        }

    def _get_processing_summary(self, file_ids: List[str]) -> Dict[str, Any]:
        """Get processing summary for uploaded files."""
        try:
            summary = {
                'file_count': len(file_ids),
                'techniques_detected': [],
                'segment_count': 0,
                'actionid_mappings': {}
            }
            
            for file_id in file_ids:
                file_data = self.get_file_data(file_id)
                if file_data and 'fundamental_technique' in file_data.columns:
                    techniques = file_data.get_column('fundamental_technique').unique().to_list()
                    summary['techniques_detected'].extend(techniques)
                    summary['segment_count'] += len(techniques)
            
            summary['techniques_detected'] = list(set(summary['techniques_detected']))
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get processing summary: {e}")
            return {'file_count': len(file_ids), 'techniques_detected': [], 'segment_count': 0}

    # =============================================================================
    # CELL MANAGEMENT (Database Operations)
    # =============================================================================

    def create_cell(self, cell_name: str, description: str = "", chemistry: str = "Li_metal",
                   capacity_ah: Optional[float] = None, cathode_material: str = "",
                   cathode_mass_mg: Optional[float] = None, anode_material: str = "",
                   anode_mass_mg: Optional[float] = None, notes: str = "") -> ProcessingResult:
        """Create a new cell with material metadata."""
        try:
            if not cell_name or not cell_name.strip():
                return ProcessingResult(False, "", "", "Cell name cannot be empty")
            
            cell_name = cell_name.strip()
            
            # Check if exists
            existing_cell = self.db.get_cell_by_name(cell_name)
            if existing_cell:
                return ProcessingResult(False, "", "", f"Cell '{cell_name}' already exists")
            
            # Create cell
            cell_id = self.db.create_cell(
                cell_name=cell_name,
                description=description,
                chemistry=chemistry,
                capacity_ah=capacity_ah,
                cathode_material=cathode_material,
                cathode_mass_mg=cathode_mass_mg,
                anode_material=anode_material,
                anode_mass_mg=anode_mass_mg,
                notes=notes
            )
            
            return ProcessingResult(True, str(cell_id), f"Cell '{cell_name}' created successfully")
            
        except Exception as e:
            logger.error(f"Cell creation failed: {e}")
            return ProcessingResult(False, "", "", str(e))

    def get_cells(self) -> List[Dict[str, Any]]:
        """Get all cells with metadata and file counts."""
        try:
            return self.db.get_all_cells()
        except Exception as e:
            logger.error(f"Failed to get cells: {e}")
            return []

    def get_cell_files(self, cell_name_or_id: Union[str, int]) -> Dict[str, Any]:
        """Get all files for a cell (compatibility method for Qt widgets)."""
        try:
            # Handle both cell_name (string) and cell_id (integer)
            if isinstance(cell_name_or_id, str):
                cell = self.db.get_cell_by_name(cell_name_or_id)
                if not cell:
                    return {
                        'success': False,
                        'error': f"Cell '{cell_name_or_id}' not found",
                        'files': []
                    }
                cell_id = cell['id']
            else:
                cell_id = cell_name_or_id
            
            files = self.db.get_cell_files(cell_id)
            return {
                'success': True,
                'files': files,
                'total_files': len(files)
            }
        except Exception as e:
            logger.error(f"Failed to get cell files: {e}")
            return {
                'success': False,
                'error': str(e),
                'files': []
            }

    # =============================================================================
    # ACTIONID MANAGEMENT (Database-Driven Technique Mapping)
    # =============================================================================

    def get_actionid_mappings(self) -> List[Dict[str, Any]]:
        """Get all ActionID → technique mappings from database."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT action_id, technique_name, fundamental_technique, user_defined
                    FROM actionid_mappings
                    ORDER BY action_id
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get ActionID mappings: {e}")
            return []

    def add_actionid_mapping(self, action_id: int, technique_name: str, 
                           fundamental_technique: str) -> ProcessingResult:
        """Add new ActionID → technique mapping to database."""
        try:
            success = self.db.add_actionid_mapping(
                action_id, technique_name, fundamental_technique, user_defined=True
            )
            
            if success:
                message = f"ActionID {action_id} mapped to {fundamental_technique}"
                return ProcessingResult(True, str(action_id), message)
            else:
                return ProcessingResult(False, "", "", f"Failed to add ActionID {action_id} mapping")
                
        except Exception as e:
            logger.error(f"Failed to add ActionID mapping: {e}")
            return ProcessingResult(False, "", "", str(e))

    def discover_unknown_actionids(self, file_data: pl.DataFrame) -> List[UnknownActionID]:
        """Discover ActionIDs in data that are not yet mapped in database."""
        try:
            unknown_actionids = []
            
            if 'technique_id' not in file_data.columns:
                return unknown_actionids
            
            # Get unique ActionIDs from data
            data_actionids = file_data.get_column('technique_id').unique().to_list()
            
            # Get known ActionIDs from database
            known_mappings = self.get_actionid_mappings()
            known_actionids = {mapping['action_id'] for mapping in known_mappings}
            
            # Find unknown ActionIDs
            for action_id in data_actionids:
                if action_id is not None and action_id not in known_actionids:
                    occurrences = file_data.filter(pl.col('technique_id') == action_id).height
                    unknown_actionids.append(UnknownActionID(action_id, f"ActionID_{action_id}", occurrences))
            
            return unknown_actionids
            
        except Exception as e:
            logger.error(f"Failed to discover unknown ActionIDs: {e}")
            return []

    # =============================================================================
    # DATA ACCESS (Simple Queries)
    # =============================================================================

    def get_file_data(self, file_id: str) -> Optional[pl.DataFrame]:
        """Get processed data for a file."""
        try:
            return self.storage.load_processed_file(file_id)
        except Exception as e:
            logger.error(f"Failed to get file data: {e}")
            return None

    def get_cell_summary(self, cell_name: str) -> Optional[Dict[str, Any]]:
        """Get cell summary with statistics."""
        try:
            return self.storage.get_cell_summary(cell_name)
        except Exception as e:
            logger.error(f"Failed to get cell summary: {e}")
            return None

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            return self.storage.get_database_stats()
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {'error': str(e)}

    # =============================================================================
    # COMPATIBILITY METHODS (For Qt Widgets)
    # =============================================================================

    def get_all_cells(self) -> Dict[str, Any]:
        """Compatibility method for Qt widgets - returns cells with success wrapper."""
        try:
            cells = self.get_cells()
            return {
                'success': True,
                'cells': cells,
                'total_cells': len(cells)
            }
        except Exception as e:
            logger.error(f"Failed to get all cells: {e}")
            return {
                'success': False,
                'error': str(e),
                'cells': []
            }

    def get_file_data_preview(self, file_id: str, n_rows: int = 1000) -> Dict[str, Any]:
        """Get preview of file data for Qt widgets."""
        try:
            data = self.get_file_data(file_id)
            if data is None:
                return {
                    'success': False,
                    'error': f"File {file_id} not found or no processed data available"
                }
            
            # Get preview data
            preview_data = data.head(n_rows) if data.height > n_rows else data
            
            # Convert to pandas for Qt consumption
            preview_df = preview_data.to_pandas()
            
            # Get basic statistics
            stats = {
                'total_rows': data.height,
                'total_columns': data.width,
                'preview_rows': preview_df.shape[0],
                'columns': list(data.columns),
                'time_range': {
                    'min': float(data.get_column('time_s').min()) if 'time_s' in data.columns else None,
                    'max': float(data.get_column('time_s').max()) if 'time_s' in data.columns else None
                },
                'techniques': data.get_column('fundamental_technique').unique().to_list() if 'fundamental_technique' in data.columns else []
            }
            
            return {
                'success': True,
                'preview_data': preview_df,
                'stats': stats,
                'file_id': file_id
            }
            
        except Exception as e:
            logger.error(f"Failed to get file preview {file_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'preview_data': pd.DataFrame(),
                'stats': {}
            }

    def add_dual_files_to_cell(self, cell_name: str, par_path: Path, csv_path: Path, 
                              upload_options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Qt compatibility method for clean in-memory processing."""
        try:
            result, processed_data = self.process_dual_files(par_path, csv_path, cell_name, upload_options)
            
            if result.success:
                return {
                    'success': True,
                    'file_ids': [result.file_id],
                    'message': result.message,
                    'processed_data': processed_data  # In-memory DataFrame for immediate use
                }
            else:
                return {
                    'success': False,
                    'error': result.error or result.message,
                    'file_ids': [],
                    'processed_data': None
                }
                
        except Exception as e:
            logger.error(f"Qt processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_ids': [],
                'processed_data': None
            }


# =============================================================================
# GLOBAL INSTANCE (Singleton Pattern)
# =============================================================================

_backend_instance = None

def get_backend_api(data_dir: Path = None, db_path: Path = None) -> BackendAPI:
    """Get singleton backend API instance."""
    global _backend_instance
    if _backend_instance is None:
        _backend_instance = BackendAPI(data_dir, db_path)
    return _backend_instance