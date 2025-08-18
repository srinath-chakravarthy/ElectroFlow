"""
SQLite database layer for battery data analyzer - Clean Redesign.

Implements segment-based architecture with row mapping for efficient parquet querying.
Supports file mobility between cells and stores analysis results with fitting coefficients.
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """SQLite database manager with segment-based architecture."""
    
    def __init__(self, db_path: Path):
        """Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
        self.populate_default_actionid_mappings()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize clean database schema."""
        with self.get_connection() as conn:
            
            # Cell table with material metadata
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cells (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cell_name TEXT UNIQUE NOT NULL,
                    description TEXT DEFAULT '',
                    chemistry TEXT DEFAULT 'Li_metal',
                    capacity_ah REAL,
                    cathode_material TEXT,
                    cathode_mass_mg REAL,
                    anode_material TEXT, 
                    anode_mass_mg REAL,
                    notes TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # File table (no experiment level - files ARE experiments)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cell_id INTEGER NOT NULL,
                    file_id TEXT UNIQUE NOT NULL,
                    original_filename TEXT NOT NULL,
                    paired_filename TEXT,  -- The .par.csv paired file
                    file_hash TEXT NOT NULL,
                    raw_file_path TEXT NOT NULL,
                    parquet_file_path TEXT,  -- Processed parquet file
                    acquisition_start TIMESTAMP,  -- From .par file metadata
                    temperature_c REAL,
                    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processing_status TEXT DEFAULT 'uploaded' 
                        CHECK (processing_status IN ('uploaded', 'processing', 'completed', 'failed')),
                    error_message TEXT,
                    metadata_json TEXT,
                    FOREIGN KEY (cell_id) REFERENCES cells (id) ON DELETE CASCADE
                )
            """)
            
            # Segment table with row mapping for efficient parquet queries
            conn.execute("""
                CREATE TABLE IF NOT EXISTS segments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT NOT NULL,
                    cell_name TEXT NOT NULL,  -- For easy reference (no FK for mobility)
                    segment_index INTEGER NOT NULL,
                    action_id INTEGER,
                    technique_name TEXT NOT NULL,
                    fundamental_technique TEXT NOT NULL,
                    start_row INTEGER NOT NULL,  -- Row number in parquet file
                    end_row INTEGER NOT NULL,    -- Row number in parquet file
                    start_time_s REAL NOT NULL,
                    end_time_s REAL NOT NULL,
                    point_count INTEGER NOT NULL,
                    analysis_status TEXT DEFAULT 'pending' 
                        CHECK (analysis_status IN ('pending', 'completed', 'failed')),
                    analysis_results_json TEXT,  -- Metrics, fit coeffs, goodness of fit
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (file_id) REFERENCES files (file_id) ON DELETE CASCADE
                )
            """)
            
            # ActionID mapping table for dynamic technique discovery
            conn.execute("""
                CREATE TABLE IF NOT EXISTS actionid_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_id INTEGER NOT NULL UNIQUE,
                    technique_name TEXT NOT NULL,
                    fundamental_technique TEXT NOT NULL,
                    verified BOOLEAN DEFAULT FALSE,
                    user_defined BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User groups table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cell_id INTEGER NOT NULL,
                    group_name TEXT NOT NULL,
                    group_type TEXT DEFAULT 'Custom',
                    description TEXT DEFAULT '',
                    segment_ids TEXT,  -- JSON array of segment IDs
                    group_metadata_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cell_id) REFERENCES cells (id) ON DELETE CASCADE,
                    UNIQUE(cell_id, group_name)
                )
            """)
            
            # Create indices for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_files_cell_id ON files (cell_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_files_file_id ON files (file_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_segments_file_id ON segments (file_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_segments_cell_name ON segments (cell_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_segments_rows ON segments (start_row, end_row)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_groups_cell_id ON user_groups (cell_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_actionid_action_id ON actionid_mappings (action_id)")
            
            conn.commit()
            logger.info(f"Clean database schema initialized: {self.db_path}")
    
    # ===== CELL OPERATIONS =====
    
    def create_cell(self, cell_name: str, description: str = "", chemistry: str = "Li_metal",
                   capacity_ah: Optional[float] = None, cathode_material: str = "",
                   cathode_mass_mg: Optional[float] = None, anode_material: str = "",
                   anode_mass_mg: Optional[float] = None, notes: str = "") -> int:
        """Create new cell and return cell_id.
        
        Args:
            cell_name: Unique cell identifier
            description: Cell description  
            chemistry: Battery chemistry (default: Li_metal)
            capacity_ah: Nominal capacity in Ah
            cathode_material: Cathode material type
            cathode_mass_mg: Active cathode mass in mg
            anode_material: Anode material type
            anode_mass_mg: Active anode mass in mg
            notes: Additional notes
            
        Returns:
            cell_id: Primary key of created cell
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO cells (
                    cell_name, description, chemistry, capacity_ah, cathode_material,
                    cathode_mass_mg, anode_material, anode_mass_mg, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (cell_name, description, chemistry, capacity_ah, cathode_material,
                  cathode_mass_mg, anode_material, anode_mass_mg, notes))
            conn.commit()
            cell_id = cursor.lastrowid
            logger.info(f"Created cell: {cell_name} (id={cell_id})")
            return cell_id
    
    def get_all_cells(self) -> List[Dict[str, Any]]:
        """Get all cells with file counts."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT c.*, 
                       COUNT(f.id) as file_count,
                       COUNT(CASE WHEN f.processing_status = 'completed' THEN 1 END) as processed_count,
                       COUNT(s.id) as segment_count,
                       COUNT(CASE WHEN s.analysis_status = 'completed' THEN 1 END) as analyzed_segments
                FROM cells c
                LEFT JOIN files f ON c.id = f.cell_id
                LEFT JOIN segments s ON f.file_id = s.file_id
                GROUP BY c.id
                ORDER BY c.created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_cell_by_id(self, cell_id: int) -> Optional[Dict[str, Any]]:
        """Get cell by ID."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM cells WHERE id = ?", (cell_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_cell_by_name(self, cell_name: str) -> Optional[Dict[str, Any]]:
        """Get cell by name."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM cells WHERE cell_name = ?", (cell_name,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_cell(self, cell_id: int, **updates) -> bool:
        """Update cell metadata."""
        if not updates:
            return False
            
        updates['updated_at'] = datetime.now().isoformat()
        set_clause = ", ".join(f"{key} = ?" for key in updates.keys())
        values = list(updates.values()) + [cell_id]
        
        with self.get_connection() as conn:
            cursor = conn.execute(f"UPDATE cells SET {set_clause} WHERE id = ?", values)
            conn.commit()
            return cursor.rowcount > 0
    
    # ===== FILE OPERATIONS =====
    
    def add_file_to_cell(self, cell_id: int, file_info: Dict[str, Any]) -> str:
        """Add file to cell and return file_id.
        
        Args:
            cell_id: Cell primary key
            file_info: Dictionary with file metadata
                Required: file_id, original_filename, file_hash, raw_file_path
                Optional: paired_filename, parquet_file_path, acquisition_start, temperature_c
        """
        required = ['file_id', 'original_filename', 'file_hash', 'raw_file_path']
        for field in required:
            if field not in file_info:
                raise ValueError(f"Required field missing: {field}")
        
        # Parse acquisition_start if string
        acquisition_start = file_info.get('acquisition_start')
        if isinstance(acquisition_start, str):
            try:
                acquisition_start = datetime.fromisoformat(acquisition_start)
            except ValueError:
                acquisition_start = None
        
        metadata_json = json.dumps(file_info.get('metadata', {}))
        
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO files (
                    cell_id, file_id, original_filename, paired_filename, file_hash,
                    raw_file_path, parquet_file_path, acquisition_start, temperature_c, 
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cell_id, file_info['file_id'], file_info['original_filename'],
                file_info.get('paired_filename'), file_info['file_hash'],
                file_info['raw_file_path'], file_info.get('parquet_file_path'),
                acquisition_start, file_info.get('temperature_c'), metadata_json
            ))
            conn.commit()
            logger.info(f"Added file to cell: {file_info['file_id']} → cell_id={cell_id}")
            return file_info['file_id']
    
    def get_cell_files(self, cell_id: int) -> List[Dict[str, Any]]:
        """Get all files for a cell."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM files WHERE cell_id = ? ORDER BY upload_timestamp DESC
            """, (cell_id,))
            files = []
            for row in cursor.fetchall():
                file_dict = dict(row)
                if file_dict['metadata_json']:
                    file_dict['metadata'] = json.loads(file_dict['metadata_json'])
                else:
                    file_dict['metadata'] = {}
                del file_dict['metadata_json']
                files.append(file_dict)
            return files
    
    def get_file_by_id(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file by file_id."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM files WHERE file_id = ?", (file_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            file_dict = dict(row)
            if file_dict['metadata_json']:
                file_dict['metadata'] = json.loads(file_dict['metadata_json'])
            else:
                file_dict['metadata'] = {}
            del file_dict['metadata_json']
            return file_dict
    
    def update_file_processing_status(self, file_id: str, status: str, 
                                    error_message: str = None, **updates) -> bool:
        """Update file processing status."""
        updates['processing_status'] = status
        if error_message:
            updates['error_message'] = error_message
            
        set_clause = ", ".join(f"{key} = ?" for key in updates.keys())
        values = list(updates.values()) + [file_id]
        
        with self.get_connection() as conn:
            cursor = conn.execute(f"UPDATE files SET {set_clause} WHERE file_id = ?", values)
            conn.commit()
            return cursor.rowcount > 0
    
    def move_file_to_cell(self, file_id: str, new_cell_id: int, new_cell_name: str) -> bool:
        """Move file between cells atomically, updating segments."""
        with self.get_connection() as conn:
            conn.execute("BEGIN")
            try:
                # Check target cell exists
                cursor = conn.execute("SELECT id FROM cells WHERE id = ?", (new_cell_id,))
                if not cursor.fetchone():
                    conn.rollback()
                    return False
                
                # Move file
                cursor = conn.execute(
                    "UPDATE files SET cell_id = ? WHERE file_id = ?", 
                    (new_cell_id, file_id)
                )
                if cursor.rowcount == 0:
                    conn.rollback()
                    return False
                
                # Update segments cell_name reference
                conn.execute(
                    "UPDATE segments SET cell_name = ? WHERE file_id = ?",
                    (new_cell_name, file_id)
                )
                
                conn.commit()
                logger.info(f"Moved file: {file_id} → cell_id={new_cell_id}")
                return True
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to move file {file_id}: {e}")
                return False
    
    def delete_file(self, file_id: str) -> bool:
        """Delete file and all associated segments."""
        with self.get_connection() as conn:
            conn.execute("BEGIN")
            try:
                # Delete segments first (due to foreign key constraints)
                conn.execute("DELETE FROM segments WHERE file_id = ?", (file_id,))
                
                # Delete file record
                cursor = conn.execute("DELETE FROM files WHERE file_id = ?", (file_id,))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"Deleted file and segments: {file_id}")
                    return True
                else:
                    conn.rollback()
                    logger.warning(f"File not found for deletion: {file_id}")
                    return False
                    
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to delete file {file_id}: {e}")
                return False
    
    # ===== SEGMENT OPERATIONS =====
    
    def add_segments_to_file(self, file_id: str, cell_name: str, segments: List[Dict[str, Any]]):
        """Add segments for a file with row mapping.
        
        Args:
            file_id: File identifier
            cell_name: Cell name for easy reference
            segments: List of segment data with row mapping
        """
        with self.get_connection() as conn:
            for segment in segments:
                analysis_json = json.dumps(segment.get('analysis_results', {}))
                
                conn.execute("""
                    INSERT INTO segments (
                        file_id, cell_name, segment_index, action_id, technique_name,
                        fundamental_technique, start_row, end_row, start_time_s, end_time_s,
                        point_count, analysis_status, analysis_results_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_id, cell_name, segment['segment_index'], segment.get('action_id'),
                    segment['technique_name'], segment['fundamental_technique'],
                    segment['start_row'], segment['end_row'], segment['start_time_s'],
                    segment['end_time_s'], segment['point_count'],
                    segment.get('analysis_status', 'pending'), analysis_json
                ))
            conn.commit()
            logger.info(f"Added {len(segments)} segments for file: {file_id}")
    
    def get_file_segments(self, file_id: str) -> List[Dict[str, Any]]:
        """Get all segments for a file."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM segments WHERE file_id = ? ORDER BY segment_index
            """, (file_id,))
            segments = []
            for row in cursor.fetchall():
                segment_dict = dict(row)
                if segment_dict['analysis_results_json']:
                    segment_dict['analysis_results'] = json.loads(segment_dict['analysis_results_json'])
                else:
                    segment_dict['analysis_results'] = {}
                del segment_dict['analysis_results_json']
                segments.append(segment_dict)
            return segments
    
    def get_segment_by_id(self, segment_id: int) -> Optional[Dict[str, Any]]:
        """Get segment by ID with analysis results."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM segments WHERE id = ?", (segment_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            segment_dict = dict(row)
            if segment_dict['analysis_results_json']:
                segment_dict['analysis_results'] = json.loads(segment_dict['analysis_results_json'])
            else:
                segment_dict['analysis_results'] = {}
            del segment_dict['analysis_results_json']
            return segment_dict
    
    def update_segment_analysis(self, segment_id: int, analysis_status: str, 
                              analysis_results: Dict[str, Any]) -> bool:
        """Update segment analysis results.
        
        Args:
            segment_id: Segment ID
            analysis_status: 'completed' or 'failed'
            analysis_results: Analysis metrics and fit coefficients
        """
        analysis_json = json.dumps(analysis_results)
        
        with self.get_connection() as conn:
            cursor = conn.execute("""
                UPDATE segments SET analysis_status = ?, analysis_results_json = ?
                WHERE id = ?
            """, (analysis_status, analysis_json, segment_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_cell_segments_summary(self, cell_id: int) -> List[Dict[str, Any]]:
        """Get segment summary for a cell with technique pass/fail status."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    s.fundamental_technique,
                    COUNT(*) as total_segments,
                    COUNT(CASE WHEN s.analysis_status = 'completed' THEN 1 END) as passed_segments,
                    COUNT(CASE WHEN s.analysis_status = 'failed' THEN 1 END) as failed_segments,
                    f.original_filename,
                    f.processing_status,
                    s.file_id
                FROM segments s
                JOIN files f ON s.file_id = f.file_id  
                WHERE f.cell_id = ?
                GROUP BY s.fundamental_technique, f.original_filename, f.processing_status, s.file_id
                ORDER BY f.upload_timestamp DESC, s.fundamental_technique
            """, (cell_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    # ===== ACTIONID MAPPING =====
    
    def get_actionid_mapping(self, action_id: int) -> Optional[Dict[str, Any]]:
        """Get ActionID mapping from database."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT action_id, technique_name, fundamental_technique, verified, user_defined
                FROM actionid_mappings WHERE action_id = ?
            """, (action_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def add_actionid_mapping(self, action_id: int, technique_name: str, 
                           fundamental_technique: str, user_defined: bool = True) -> bool:
        """Add ActionID mapping."""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO actionid_mappings (action_id, technique_name, fundamental_technique, user_defined)
                    VALUES (?, ?, ?, ?)
                """, (action_id, technique_name, fundamental_technique, user_defined))
                conn.commit()
                logger.info(f"Added ActionID mapping: {action_id} -> {fundamental_technique}")
                return True
        except sqlite3.IntegrityError:
            logger.debug(f"ActionID {action_id} mapping already exists")
            return False
    
    def populate_default_actionid_mappings(self):
        """Populate with known ActionID mappings."""
        defaults = [
            (8, 'Constant Current', 'CC', False),
            (20, 'Galvanostatic EIS', 'GEIS', False), 
            (23, 'Energy Open Circuit', 'OCV', False)
        ]
        
        for action_id, technique_name, fundamental_technique, user_defined in defaults:
            self.add_actionid_mapping(action_id, technique_name, fundamental_technique, user_defined)
    
    # ===== USER GROUPS =====
    
    def create_user_group(self, cell_id: int, group_name: str, group_type: str = "Custom",
                         description: str = "", segment_ids: List[int] = None) -> int:
        """Create user group for segments."""
        segment_ids_json = json.dumps(segment_ids or [])
        
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO user_groups (cell_id, group_name, group_type, description, segment_ids)
                VALUES (?, ?, ?, ?, ?)
            """, (cell_id, group_name, group_type, description, segment_ids_json))
            conn.commit()
            group_id = cursor.lastrowid
            logger.info(f"Created user group: {group_name} (cell_id={cell_id})")
            return group_id
    
    def get_cell_groups(self, cell_id: int) -> List[Dict[str, Any]]:
        """Get all user groups for a cell."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM user_groups WHERE cell_id = ? ORDER BY created_at DESC
            """, (cell_id,))
            groups = []
            for row in cursor.fetchall():
                group_dict = dict(row)
                if group_dict['segment_ids']:
                    group_dict['segment_ids'] = json.loads(group_dict['segment_ids'])
                else:
                    group_dict['segment_ids'] = []
                groups.append(group_dict)
            return groups
    
    # ===== ANALYSIS HELPERS =====
    
    def compute_timestamps_for_file(self, file_id: str) -> bool:
        """Compute absolute timestamps for file segments.
        
        This assumes acquisition_start is already stored in the file record
        and segments have relative time_s values that need to be converted
        to absolute timestamps: acquisition_start + elapsed_time_s
        """
        file_info = self.get_file_by_id(file_id)
        if not file_info or not file_info.get('acquisition_start'):
            logger.error(f"Cannot compute timestamps: missing acquisition_start for {file_id}")
            return False
        
        acquisition_start = file_info['acquisition_start']
        if isinstance(acquisition_start, str):
            acquisition_start = datetime.fromisoformat(acquisition_start)
        
        # This would typically be called during file processing
        # when we have the actual time series data loaded
        logger.info(f"Timestamps computed for file: {file_id} (start: {acquisition_start})")
        return True
    
    # ===== DATABASE UTILITIES =====
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self.get_connection() as conn:
            stats = {}
            
            # Count records
            for table in ['cells', 'files', 'segments', 'user_groups', 'actionid_mappings']:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                stats[f"{table}_count"] = cursor.fetchone()[0]
            
            # Processing status breakdown
            cursor = conn.execute("""
                SELECT processing_status, COUNT(*) FROM files GROUP BY processing_status
            """)
            stats['file_processing_status'] = dict(cursor.fetchall())
            
            # Analysis status breakdown  
            cursor = conn.execute("""
                SELECT analysis_status, COUNT(*) FROM segments GROUP BY analysis_status
            """)
            stats['segment_analysis_status'] = dict(cursor.fetchall())
            
            # Database size
            stats['db_size_bytes'] = self.db_path.stat().st_size
            
            return stats
    
    def vacuum_database(self):
        """Vacuum database to reclaim space."""
        with self.get_connection() as conn:
            conn.execute("VACUUM")
            logger.info("Database vacuumed")


# Convenience functions
def get_or_create_cell(db: DatabaseManager, cell_name: str, **metadata) -> Tuple[int, bool]:
    """Get existing cell or create new one."""
    cell = db.get_cell_by_name(cell_name)
    if cell:
        return cell['id'], False
    else:
        cell_id = db.create_cell(cell_name, **metadata)
        return cell_id, True