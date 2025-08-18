"""
Clean Database Layer - Electrochemical Analysis Suite

Minimal, atomic database operations for cells, files, and experimental segments.

Key Principles:
- Atomic operations (all-or-nothing commits)
- Clean schema with foreign key constraints
- Precise row boundaries for efficient data slicing
- Segment-centric design for flexible analysis
"""

import sqlite3
import json
import logging
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from .exceptions import (
    DatabaseError, DatabaseConnectionError, DatabaseIntegrityError,
    TransactionError, RecordNotFoundError
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Clean database manager with atomic operations."""
    
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Enable foreign keys and WAL mode for better concurrency
        self._init_database()
        logger.info(f"Database initialized: {self.db_path}")
    
    def _init_database(self):
        """Initialize database with clean schema."""
        try:
            with self.get_connection() as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("PRAGMA journal_mode = WAL")
                self._create_tables(conn)
                self._create_indices(conn)
                self._insert_default_data(conn)
                conn.commit()
        except Exception as e:
            raise DatabaseConnectionError(str(self.db_path), str(e))
    
    def _create_tables(self, conn: sqlite3.Connection):
        """Create database tables with clean schema."""
        
        # Cells table - experimental cells/batteries
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cells (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT DEFAULT '',
                chemistry TEXT DEFAULT 'Li_metal',
                capacity_ah REAL,
                cathode_material TEXT DEFAULT '',
                cathode_mass_mg REAL,
                anode_material TEXT DEFAULT '',
                anode_mass_mg REAL,
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Files table - individual data files
        conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT UNIQUE NOT NULL,
                cell_id INTEGER NOT NULL,
                original_filename TEXT NOT NULL,
                paired_filename TEXT,
                file_hash TEXT NOT NULL,
                file_size_bytes INTEGER DEFAULT 0,
                instrument_model TEXT DEFAULT 'VersaStudio',
                acquisition_start TIMESTAMP,
                acquisition_duration_s REAL DEFAULT 0.0,
                temperature_c REAL DEFAULT 25.0,
                processing_status TEXT DEFAULT 'pending',
                parquet_file_path TEXT,
                metadata_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cell_id) REFERENCES cells(id) ON DELETE CASCADE
            )
        """)
        
        # Segments table - experimental segments within files
        conn.execute("""
            CREATE TABLE IF NOT EXISTS segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT NOT NULL,
                segment_index INTEGER NOT NULL,
                technique_id INTEGER,
                technique_name TEXT NOT NULL,
                fundamental_technique TEXT NOT NULL,
                start_row INTEGER NOT NULL,
                end_row INTEGER NOT NULL,
                start_time_s REAL NOT NULL,
                end_time_s REAL NOT NULL,
                point_count INTEGER NOT NULL,
                segment_metadata TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE CASCADE,
                UNIQUE(file_id, segment_index)
            )
        """)
        
        # ActionID mappings - technique identification
        conn.execute("""
            CREATE TABLE IF NOT EXISTS actionid_mappings (
                action_id INTEGER PRIMARY KEY,
                technique_name TEXT NOT NULL,
                fundamental_technique TEXT NOT NULL,
                user_defined BOOLEAN DEFAULT FALSE,
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    def _create_indices(self, conn: sqlite3.Connection):
        """Create database indices for performance."""
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_files_cell_id ON files(cell_id)",
            "CREATE INDEX IF NOT EXISTS idx_files_file_id ON files(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_segments_file_id ON segments(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_segments_technique ON segments(fundamental_technique)",
            "CREATE INDEX IF NOT EXISTS idx_actionid_mappings_technique ON actionid_mappings(fundamental_technique)"
        ]
        
        for index_sql in indices:
            conn.execute(index_sql)
    
    def _insert_default_data(self, conn: sqlite3.Connection):
        """Insert default ActionID mappings."""
        default_mappings = [
            (1, 'Rest', 'rest', False, 'Open circuit potential measurement'),
            (2, 'Potentiostatic', 'cp', False, 'Constant potential technique'),
            (3, 'Galvanostatic', 'cc', False, 'Constant current technique'),
            (4, 'Linear Sweep', 'cv', False, 'Linear sweep voltammetry'),
            (5, 'Cyclic Voltammetry', 'cv', False, 'Cyclic voltammetry'),
            (10, 'EIS', 'eis', False, 'Electrochemical impedance spectroscopy'),
            (15, 'Current Interrupt', 'pulse', False, 'Current interrupt technique'),
            (20, 'GITT', 'pulse', False, 'Galvanostatic intermittent titration')
        ]
        
        for action_id, technique_name, fundamental_technique, user_defined, description in default_mappings:
            conn.execute("""
                INSERT OR IGNORE INTO actionid_mappings 
                (action_id, technique_name, fundamental_technique, user_defined, description)
                VALUES (?, ?, ?, ?, ?)
            """, (action_id, technique_name, fundamental_technique, user_defined, description))
    
    @contextmanager
    def get_connection(self):
        """Get database connection with proper error handling."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            raise DatabaseError(f"Database operation failed: {str(e)}")
        finally:
            if conn:
                conn.close()
    
    # =============================================================================
    # CELL OPERATIONS
    # =============================================================================
    
    def create_cell(self, name: str, description: str = "", chemistry: str = "Li_metal",
                   capacity_ah: Optional[float] = None, cathode_material: str = "",
                   cathode_mass_mg: Optional[float] = None, anode_material: str = "",
                   anode_mass_mg: Optional[float] = None, notes: str = "") -> int:
        """Create new cell with atomic transaction."""
        with self.get_connection() as conn:
            conn.execute("BEGIN")
            try:
                cursor = conn.execute("""
                    INSERT INTO cells 
                    (name, description, chemistry, capacity_ah, cathode_material, 
                     cathode_mass_mg, anode_material, anode_mass_mg, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, description, chemistry, capacity_ah, cathode_material,
                      cathode_mass_mg, anode_material, anode_mass_mg, notes))
                
                cell_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Created cell: {name} (ID: {cell_id})")
                return cell_id
                
            except sqlite3.IntegrityError as e:
                conn.rollback()
                if "UNIQUE constraint failed" in str(e):
                    raise DatabaseIntegrityError(f"Cell name '{name}' already exists", "create_cell")
                else:
                    raise DatabaseIntegrityError(str(e), "create_cell")
            except Exception as e:
                conn.rollback()
                raise TransactionError("create_cell", str(e))
    
    def get_cell_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get cell by name."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM cells WHERE name = ?", (name,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_cell_by_id(self, cell_id: int) -> Optional[Dict[str, Any]]:
        """Get cell by ID."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM cells WHERE id = ?", (cell_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_cells(self) -> List[Dict[str, Any]]:
        """Get all cells with file counts."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT c.*, COUNT(f.id) as file_count
                FROM cells c
                LEFT JOIN files f ON c.id = f.cell_id
                GROUP BY c.id
                ORDER BY c.created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_cell(self, cell_id: int) -> bool:
        """Delete cell and all associated data."""
        with self.get_connection() as conn:
            conn.execute("BEGIN")
            try:
                cursor = conn.execute("DELETE FROM cells WHERE id = ?", (cell_id,))
                deleted = cursor.rowcount > 0
                conn.commit()
                
                if deleted:
                    logger.info(f"Deleted cell ID: {cell_id}")
                
                return deleted
                
            except Exception as e:
                conn.rollback()
                raise TransactionError("delete_cell", str(e))
    
    # =============================================================================
    # FILE OPERATIONS
    # =============================================================================
    
    def add_file(self, cell_id: int, file_info: Dict[str, Any]) -> str:
        """Add file to database with atomic transaction."""
        with self.get_connection() as conn:
            conn.execute("BEGIN")
            try:
                # Prepare file data
                metadata_json = json.dumps(file_info.get('metadata', {}))
                
                conn.execute("""
                    INSERT INTO files 
                    (file_id, cell_id, original_filename, paired_filename, file_hash,
                     file_size_bytes, instrument_model, acquisition_start, 
                     acquisition_duration_s, temperature_c, parquet_file_path, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_info['file_id'], cell_id, file_info['original_filename'],
                    file_info.get('paired_filename'), file_info['file_hash'],
                    file_info.get('file_size_bytes', 0), 
                    file_info.get('instrument_model', 'VersaStudio'),
                    file_info.get('acquisition_start'), 
                    file_info.get('acquisition_duration_s', 0.0),
                    file_info.get('temperature_c', 25.0),
                    file_info.get('parquet_file_path'), metadata_json
                ))
                
                conn.commit()
                logger.info(f"Added file: {file_info['file_id']}")
                return file_info['file_id']
                
            except sqlite3.IntegrityError as e:
                conn.rollback()
                if "UNIQUE constraint failed" in str(e):
                    raise DatabaseIntegrityError(f"File ID '{file_info['file_id']}' already exists", "add_file")
                else:
                    raise DatabaseIntegrityError(str(e), "add_file")
            except Exception as e:
                conn.rollback()
                raise TransactionError("add_file", str(e))
    
    def get_file_by_id(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file by ID."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM files WHERE file_id = ?", (file_id,))
            row = cursor.fetchone()
            
            if row:
                file_data = dict(row)
                # Parse metadata JSON
                file_data['metadata'] = json.loads(file_data['metadata_json'])
                return file_data
            
            return None
    
    def get_cell_files(self, cell_id: int) -> List[Dict[str, Any]]:
        """Get all files for a cell."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT f.*, COUNT(s.id) as segment_count
                FROM files f
                LEFT JOIN segments s ON f.file_id = s.file_id
                WHERE f.cell_id = ?
                GROUP BY f.id
                ORDER BY f.acquisition_start DESC, f.created_at DESC
            """, (cell_id,))
            
            files = []
            for row in cursor.fetchall():
                file_data = dict(row)
                file_data['metadata'] = json.loads(file_data['metadata_json'])
                files.append(file_data)
            
            return files
    
    def update_file_status(self, file_id: str, status: str) -> bool:
        """Update file processing status."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                UPDATE files SET processing_status = ? 
                WHERE file_id = ?
            """, (status, file_id))
            return cursor.rowcount > 0
    
    def delete_file(self, file_id: str) -> bool:
        """Delete file and all associated segments."""
        with self.get_connection() as conn:
            conn.execute("BEGIN")
            try:
                # Delete segments first (foreign key constraint)
                conn.execute("DELETE FROM segments WHERE file_id = ?", (file_id,))
                
                # Delete file
                cursor = conn.execute("DELETE FROM files WHERE file_id = ?", (file_id,))
                deleted = cursor.rowcount > 0
                
                conn.commit()
                
                if deleted:
                    logger.info(f"Deleted file: {file_id}")
                
                return deleted
                
            except Exception as e:
                conn.rollback()
                raise TransactionError("delete_file", str(e))
    
    # =============================================================================
    # SEGMENT OPERATIONS
    # =============================================================================
    
    def add_segments(self, file_id: str, segments: List[Dict[str, Any]]) -> int:
        """Add segments for a file with atomic transaction."""
        with self.get_connection() as conn:
            conn.execute("BEGIN")
            try:
                for segment in segments:
                    metadata_json = json.dumps(segment.get('segment_metadata', {}))
                    
                    conn.execute("""
                        INSERT INTO segments 
                        (file_id, segment_index, technique_id, technique_name, 
                         fundamental_technique, start_row, end_row, start_time_s, 
                         end_time_s, point_count, segment_metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        file_id, segment['segment_index'], segment.get('technique_id'),
                        segment['technique_name'], segment['fundamental_technique'],
                        segment['start_row'], segment['end_row'], segment['start_time_s'],
                        segment['end_time_s'], segment['point_count'], metadata_json
                    ))
                
                conn.commit()
                logger.info(f"Added {len(segments)} segments for file: {file_id}")
                return len(segments)
                
            except Exception as e:
                conn.rollback()
                raise TransactionError("add_segments", str(e))
    
    def get_file_segments(self, file_id: str) -> List[Dict[str, Any]]:
        """Get all segments for a file."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM segments 
                WHERE file_id = ? 
                ORDER BY segment_index
            """, (file_id,))
            
            segments = []
            for row in cursor.fetchall():
                segment_data = dict(row)
                segment_data['segment_metadata'] = json.loads(segment_data['segment_metadata'])
                segments.append(segment_data)
            
            return segments
    
    def get_segments_by_technique(self, fundamental_technique: str) -> List[Dict[str, Any]]:
        """Get all segments for a specific technique across all files."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT s.*, f.cell_id, c.name as cell_name
                FROM segments s
                JOIN files f ON s.file_id = f.file_id
                JOIN cells c ON f.cell_id = c.id
                WHERE s.fundamental_technique = ?
                ORDER BY c.name, f.acquisition_start, s.segment_index
            """, (fundamental_technique,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # =============================================================================
    # ACTIONID MAPPING OPERATIONS
    # =============================================================================
    
    def get_actionid_mapping(self, action_id: int) -> Optional[Dict[str, Any]]:
        """Get ActionID mapping."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM actionid_mappings WHERE action_id = ?
            """, (action_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_actionid_mappings(self) -> List[Dict[str, Any]]:
        """Get all ActionID mappings."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM actionid_mappings ORDER BY action_id
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def add_actionid_mapping(self, action_id: int, technique_name: str, 
                           fundamental_technique: str, user_defined: bool = True,
                           description: str = "") -> bool:
        """Add or update ActionID mapping."""
        with self.get_connection() as conn:
            conn.execute("BEGIN")
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO actionid_mappings 
                    (action_id, technique_name, fundamental_technique, user_defined, description)
                    VALUES (?, ?, ?, ?, ?)
                """, (action_id, technique_name, fundamental_technique, user_defined, description))
                
                conn.commit()
                logger.info(f"Added ActionID mapping: {action_id} -> {fundamental_technique}")
                return True
                
            except Exception as e:
                conn.rollback()
                raise TransactionError("add_actionid_mapping", str(e))
    
    # =============================================================================
    # UTILITY OPERATIONS
    # =============================================================================
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM cells) as cell_count,
                    (SELECT COUNT(*) FROM files) as file_count,
                    (SELECT COUNT(*) FROM segments) as segment_count,
                    (SELECT COUNT(*) FROM actionid_mappings WHERE user_defined = 1) as user_mappings_count
            """)
            row = cursor.fetchone()
            
            return {
                'cell_count': row[0],
                'file_count': row[1], 
                'segment_count': row[2],
                'user_mappings_count': row[3],
                'database_path': str(self.db_path),
                'database_size_mb': self.db_path.stat().st_size / (1024 * 1024)
            }
    
    def vacuum_database(self) -> bool:
        """Vacuum database to reclaim space."""
        try:
            with self.get_connection() as conn:
                conn.execute("VACUUM")
                logger.info("Database vacuumed successfully")
                return True
        except Exception as e:
            logger.error(f"Database vacuum failed: {e}")
            return False
    
    def backup_database(self, backup_path: Path) -> bool:
        """Create database backup."""
        try:
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            with self.get_connection() as source:
                with sqlite3.connect(backup_path) as backup:
                    source.backup(backup)
            
            logger.info(f"Database backed up to: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return False