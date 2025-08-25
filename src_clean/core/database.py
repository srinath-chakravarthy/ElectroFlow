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
                duration_s REAL NOT NULL,
                start_potential_v REAL,
                end_potential_v REAL,
                start_current_a REAL,
                end_current_a REAL,
                capacity_ah REAL,
                energy_wh REAL,
                start_timestamp TEXT,
                capacity_cumulative_ah REAL DEFAULT 0.0,
                energy_cumulative_wh REAL DEFAULT 0.0,
                charge_cumulative_ah REAL DEFAULT 0.0,
                discharge_cumulative_ah REAL DEFAULT 0.0,
                energy_charge_cumulative_wh REAL DEFAULT 0.0,
                energy_discharge_cumulative_wh REAL DEFAULT 0.0,
                capacity_absolute_cumulative_ah REAL DEFAULT 0.0,
                energy_absolute_cumulative_wh REAL DEFAULT 0.0,
                analysis_status TEXT DEFAULT 'pending',
                analysis_results TEXT DEFAULT '{}',
                segment_metadata TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE CASCADE,
                UNIQUE(file_id, segment_index)
            )
        """)
        
        # Check if we need to migrate existing segments table
        self._migrate_segments_table(conn)
        
        # User groups table - for group management functionality
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_groups (
                group_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cell_id INTEGER NOT NULL,
                group_name VARCHAR(255) NOT NULL,
                description TEXT,
                is_template BOOLEAN DEFAULT FALSE,
                template_type VARCHAR(100) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cell_id) REFERENCES cells(id) ON DELETE CASCADE,
                UNIQUE(cell_id, group_name)
            )
        """)
        
        # User group segments junction table - many-to-many relationship
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_group_segments (
                group_id INTEGER NOT NULL,
                segment_id INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (group_id, segment_id),
                FOREIGN KEY (group_id) REFERENCES user_groups(group_id) ON DELETE CASCADE,
                FOREIGN KEY (segment_id) REFERENCES segments(id) ON DELETE CASCADE
            )
        """)
        
        # Fundamental techniques - battery-focused universal techniques
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fundamental_techniques (
                technique_id INTEGER PRIMARY KEY,
                technique_name TEXT UNIQUE NOT NULL,
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Instrument-specific ActionID mappings to fundamental techniques
        conn.execute("""
            CREATE TABLE IF NOT EXISTS instrument_actionid_mappings (
                action_id INTEGER PRIMARY KEY,
                action_name TEXT NOT NULL,
                technique_id INTEGER NOT NULL,
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (technique_id) REFERENCES fundamental_techniques(technique_id)
            )
        """)
    
    def _create_indices(self, conn: sqlite3.Connection):
        """Create database indices for performance."""
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_files_cell_id ON files(cell_id)",
            "CREATE INDEX IF NOT EXISTS idx_files_file_id ON files(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_segments_file_id ON segments(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_segments_technique ON segments(fundamental_technique)",
            "CREATE INDEX IF NOT EXISTS idx_user_groups_cell_id ON user_groups(cell_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_group_segments_group_id ON user_group_segments(group_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_group_segments_segment_id ON user_group_segments(segment_id)",
            # Fundamental techniques indices
            "CREATE INDEX IF NOT EXISTS idx_fundamental_techniques_name ON fundamental_techniques(technique_name)",
            "CREATE INDEX IF NOT EXISTS idx_instrument_mappings_technique ON instrument_actionid_mappings(technique_id)"
        ]
        
        for index_sql in indices:
            conn.execute(index_sql)
    
    def _migrate_segments_table(self, conn: sqlite3.Connection):
        """Migrate existing segments table to include analytics columns."""
        try:
            # Check if analytics columns exist
            cursor = conn.execute("PRAGMA table_info(segments)")
            columns = {row[1] for row in cursor.fetchall()}
            
            required_columns = {
                'duration_s', 'start_potential_v', 'end_potential_v',
                'start_current_a', 'end_current_a', 'capacity_ah', 
                'energy_wh', 'start_timestamp', 'capacity_cumulative_ah', 
                'energy_cumulative_wh', 'charge_cumulative_ah', 'discharge_cumulative_ah',
                'energy_charge_cumulative_wh', 'energy_discharge_cumulative_wh',
                'capacity_absolute_cumulative_ah', 'energy_absolute_cumulative_wh',
                'exp_charge_cap_ah', 'exp_discharge_cap_ah', 
                'exp_charge_energy_wh', 'exp_discharge_energy_wh', 'exp_time_cumulative_s',
                'analysis_status', 'analysis_results'
            }
            
            missing_columns = required_columns - columns
            
            if missing_columns:
                logger.info(f"Migrating segments table - adding columns: {missing_columns}")
                
                # Add missing columns with appropriate defaults
                column_definitions = {
                    'duration_s': 'REAL NOT NULL DEFAULT 0.0',
                    'start_potential_v': 'REAL',
                    'end_potential_v': 'REAL',
                    'start_current_a': 'REAL',
                    'end_current_a': 'REAL',
                    'capacity_ah': 'REAL',
                    'energy_wh': 'REAL',
                    'start_timestamp': 'TEXT',
                    'capacity_cumulative_ah': 'REAL DEFAULT 0.0',
                    'energy_cumulative_wh': 'REAL DEFAULT 0.0',
                    'charge_cumulative_ah': 'REAL DEFAULT 0.0',
                    'discharge_cumulative_ah': 'REAL DEFAULT 0.0',
                    'energy_charge_cumulative_wh': 'REAL DEFAULT 0.0',
                    'energy_discharge_cumulative_wh': 'REAL DEFAULT 0.0',
                    'capacity_absolute_cumulative_ah': 'REAL DEFAULT 0.0',
                    'energy_absolute_cumulative_wh': 'REAL DEFAULT 0.0',
                    'exp_charge_cap_ah': 'REAL DEFAULT 0.0',
                    'exp_discharge_cap_ah': 'REAL DEFAULT 0.0',
                    'exp_charge_energy_wh': 'REAL DEFAULT 0.0',
                    'exp_discharge_energy_wh': 'REAL DEFAULT 0.0',
                    'exp_time_cumulative_s': 'REAL DEFAULT 0.0',
                    'analysis_status': 'TEXT DEFAULT "pending"',
                    'analysis_results': 'TEXT DEFAULT "{}"'
                }
                
                for column in missing_columns:
                    if column in column_definitions:
                        sql = f"ALTER TABLE segments ADD COLUMN {column} {column_definitions[column]}"
                        conn.execute(sql)
                        logger.debug(f"Added column: {column}")
                
                # Update duration for existing segments
                conn.execute("""
                    UPDATE segments 
                    SET duration_s = end_time_s - start_time_s 
                    WHERE duration_s = 0.0
                """)
                
                logger.info("Segments table migration completed successfully")
            
        except Exception as e:
            logger.error(f"Error migrating segments table: {e}")
            # Don't raise - let the application continue with existing schema
    
    def _insert_default_data(self, conn: sqlite3.Connection):
        """Insert default fundamental techniques and VersaStudio mappings."""
        
        # Insert 5 fundamental techniques (battery-focused)
        fundamental_techniques = [
            (1, 'Rest', 'Open circuit potential measurement'),
            (2, 'Galvanostatic', 'Constant current technique'),
            (3, 'Potentiostatic', 'Constant potential technique'),
            (4, 'EIS', 'Electrochemical impedance spectroscopy'),
            (5, 'Cyclic Voltammetry', 'Voltage sweep technique')
        ]
        
        for technique_id, name, description in fundamental_techniques:
            conn.execute("""
                INSERT OR IGNORE INTO fundamental_techniques 
                (technique_id, technique_name, description)
                VALUES (?, ?, ?)
            """, (technique_id, name, description))
        
        # Insert VersaStudio ActionID mappings (only 3 known ones)
        versastudio_mappings = [
            # (action_id, action_name, technique_id, description)
            (23, 'Energy Open Circuit', 1, 'VersaStudio rest technique'),
            (20, 'Galvanostatic EIS', 4, 'VersaStudio EIS technique'),
            (8, 'Constant Current', 2, 'VersaStudio galvanostatic technique')
        ]
        
        for action_id, action_name, technique_id, description in versastudio_mappings:
            conn.execute("""
                INSERT OR IGNORE INTO instrument_actionid_mappings 
                (action_id, action_name, technique_id, description)
                VALUES (?, ?, ?, ?)
            """, (action_id, action_name, technique_id, description))
    
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
    
    def get_file_final_cumulative_values(self, file_id: str) -> Dict[str, float]:
        """Get final cumulative values from the last segment of a file."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT charge_cumulative_ah, discharge_cumulative_ah,
                       energy_charge_cumulative_wh, energy_discharge_cumulative_wh,
                       end_time_s, start_time_s
                FROM segments 
                WHERE file_id = ?
                ORDER BY end_time_s DESC, segment_index DESC
                LIMIT 1
            """, (file_id,))
            
            row = cursor.fetchone()
            if row:
                start_time = cursor.execute("""
                    SELECT start_time_s FROM segments 
                    WHERE file_id = ? 
                    ORDER BY start_time_s ASC, segment_index ASC 
                    LIMIT 1
                """, (file_id,)).fetchone()
                
                return {
                    'charge_cumulative_ah': float(row[0] or 0),
                    'discharge_cumulative_ah': float(row[1] or 0),
                    'energy_charge_cumulative_wh': float(row[2] or 0),
                    'energy_discharge_cumulative_wh': float(row[3] or 0),
                    'total_duration_s': float(row[4] or 0) - float(start_time[0] or 0) if start_time else 0.0
                }
            return {
                'charge_cumulative_ah': 0.0,
                'discharge_cumulative_ah': 0.0,
                'energy_charge_cumulative_wh': 0.0,
                'energy_discharge_cumulative_wh': 0.0,
                'total_duration_s': 0.0
            }
    
    def update_segments_experiment_accumulation(self, file_id: str, 
                                              charge_offset: float, discharge_offset: float,
                                              energy_charge_offset: float, energy_discharge_offset: float,
                                              time_offset: float):
        """Update experiment accumulation for all segments in a file."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                UPDATE segments SET
                    exp_charge_cap_ah = charge_cumulative_ah + ?,
                    exp_discharge_cap_ah = ABS(discharge_cumulative_ah) + ?,
                    exp_charge_energy_wh = energy_charge_cumulative_wh + ?,
                    exp_discharge_energy_wh = ABS(energy_discharge_cumulative_wh) + ?,
                    exp_time_cumulative_s = start_time_s + ?
                WHERE file_id = ?
            """, (charge_offset, discharge_offset, energy_charge_offset, energy_discharge_offset, time_offset, file_id))
            
            updated_count = cursor.rowcount
            conn.commit()  # Explicit commit to ensure changes are persisted
            logger.debug(f"Updated {updated_count} segments with experiment accumulation for file {file_id}")
            return updated_count
    
    def get_cell_files_ordered_by_timestamp(self, cell_id: int) -> List[Dict[str, Any]]:
        """Get cell files ordered chronologically by acquisition timestamp."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT file_id, acquisition_start, original_filename
                FROM files 
                WHERE cell_id = ?
                ORDER BY acquisition_start ASC, created_at ASC
            """, (cell_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
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
                    analysis_results_json = json.dumps(segment.get('analysis_results', {})) if isinstance(segment.get('analysis_results'), dict) else segment.get('analysis_results', '{}')
                    
                    conn.execute("""
                        INSERT INTO segments 
                        (file_id, segment_index, technique_id, technique_name, 
                         fundamental_technique, start_row, end_row, start_time_s, 
                         end_time_s, point_count, duration_s, start_potential_v, 
                         end_potential_v, start_current_a, end_current_a, capacity_ah, 
                         energy_wh, start_timestamp, capacity_cumulative_ah, energy_cumulative_wh,
                         charge_cumulative_ah, discharge_cumulative_ah, energy_charge_cumulative_wh,
                         energy_discharge_cumulative_wh, capacity_absolute_cumulative_ah, 
                         energy_absolute_cumulative_wh, analysis_status, analysis_results, segment_metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        file_id, segment['segment_index'], segment.get('technique_id'),
                        segment['technique_name'], segment['fundamental_technique'],
                        segment['start_row'], segment['end_row'], segment['start_time_s'],
                        segment['end_time_s'], segment['point_count'], 
                        segment.get('duration_s'), segment.get('start_potential_v'),
                        segment.get('end_potential_v'), segment.get('start_current_a'),
                        segment.get('end_current_a'), segment.get('capacity_ah'),
                        segment.get('energy_wh'), segment.get('start_timestamp'),
                        segment.get('capacity_cumulative_ah'), segment.get('energy_cumulative_wh'),
                        segment.get('charge_cumulative_ah'), segment.get('discharge_cumulative_ah'),
                        segment.get('energy_charge_cumulative_wh'), segment.get('energy_discharge_cumulative_wh'),
                        segment.get('capacity_absolute_cumulative_ah'), segment.get('energy_absolute_cumulative_wh'),
                        segment.get('analysis_status', 'pending'), analysis_results_json, metadata_json
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
    
    def update_segment_analysis(self, file_id: str, segment_index: int, analysis_data: Dict[str, Any]) -> bool:
        """Update segment analysis results."""
        with self.get_connection() as conn:
            try:
                # Prepare analysis_results JSON
                analysis_results_json = analysis_data.get('analysis_results', '{}')
                if isinstance(analysis_results_json, dict):
                    analysis_results_json = json.dumps(analysis_results_json)
                
                cursor = conn.execute("""
                    UPDATE segments SET 
                        duration_s = ?, start_potential_v = ?, end_potential_v = ?,
                        start_current_a = ?, end_current_a = ?, capacity_ah = ?,
                        energy_wh = ?, analysis_status = ?, analysis_results = ?
                    WHERE file_id = ? AND segment_index = ?
                """, (
                    analysis_data.get('duration_s'),
                    analysis_data.get('start_potential_v'),
                    analysis_data.get('end_potential_v'),
                    analysis_data.get('start_current_a'),
                    analysis_data.get('end_current_a'),
                    analysis_data.get('capacity_ah'),
                    analysis_data.get('energy_wh'),
                    analysis_data.get('analysis_status', 'pending'),
                    analysis_results_json,
                    file_id, segment_index
                ))
                
                updated = cursor.rowcount > 0
                if updated:
                    logger.debug(f"Updated analysis for segment {file_id}:{segment_index}")
                return updated
                
            except Exception as e:
                logger.error(f"Failed to update segment analysis: {e}")
                raise TransactionError("update_segment_analysis", str(e))
    
    def get_segments_pending_analysis(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get segments that need analysis (status = 'pending' or 'failed')."""
        with self.get_connection() as conn:
            sql = """
                SELECT s.*, f.file_id, f.parquet_file_path
                FROM segments s
                JOIN files f ON s.file_id = f.file_id
                WHERE s.analysis_status IN ('pending', 'failed')
                ORDER BY f.acquisition_start, s.segment_index
            """
            
            params = []
            if limit:
                sql += " LIMIT ?"
                params.append(limit)
            
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
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
    # TECHNIQUE MAPPING OPERATIONS
    # =============================================================================
    
    def get_technique_mapping(self, action_id: int) -> Optional[Dict[str, Any]]:
        """Get technique mapping for VersaStudio ActionID."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    iam.action_id,
                    iam.action_name,
                    ft.technique_id,
                    ft.technique_name,
                    ft.description as technique_description,
                    iam.description as mapping_description
                FROM instrument_actionid_mappings iam
                JOIN fundamental_techniques ft ON iam.technique_id = ft.technique_id
                WHERE iam.action_id = ?
            """, (action_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_fundamental_techniques(self) -> List[Dict[str, Any]]:
        """Get all fundamental techniques."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM fundamental_techniques ORDER BY technique_id
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_technique_mappings(self) -> List[Dict[str, Any]]:
        """Get all VersaStudio ActionID mappings with technique details."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    iam.action_id,
                    iam.action_name,
                    ft.technique_id,
                    ft.technique_name,
                    ft.description as technique_description,
                    iam.description as mapping_description,
                    iam.created_at
                FROM instrument_actionid_mappings iam
                JOIN fundamental_techniques ft ON iam.technique_id = ft.technique_id
                ORDER BY iam.action_id
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def add_technique_mapping(self, action_id: int, action_name: str, 
                             technique_id: int, description: str = "") -> bool:
        """Add new VersaStudio ActionID mapping to fundamental technique."""
        with self.get_connection() as conn:
            conn.execute("BEGIN")
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO instrument_actionid_mappings 
                    (action_id, action_name, technique_id, description)
                    VALUES (?, ?, ?, ?)
                """, (action_id, action_name, technique_id, description))
                
                conn.commit()
                logger.info(f"Added technique mapping: ActionID {action_id} -> {technique_id}")
                return True
                
            except Exception as e:
                conn.rollback()
                raise TransactionError("add_technique_mapping", str(e))
    
    # =============================================================================
    # GROUP MANAGEMENT OPERATIONS
    # =============================================================================
    
    def create_group(self, cell_id: int, group_name: str, description: str = "", 
                     is_template: bool = False, template_type: str = None) -> int:
        """Create a new user group or template group."""
        with self.get_connection() as conn:
            conn.execute("BEGIN")
            try:
                cursor = conn.execute("""
                    INSERT INTO user_groups (cell_id, group_name, description, is_template, template_type)
                    VALUES (?, ?, ?, ?, ?)
                """, (cell_id, group_name, description, is_template, template_type))
                
                group_id = cursor.lastrowid
                conn.commit()
                group_type = "template" if is_template else "user"
                logger.info(f"Created {group_type} group: {group_name} (ID: {group_id})")
                return group_id
                
            except sqlite3.IntegrityError as e:
                conn.rollback()
                if "UNIQUE constraint failed" in str(e):
                    raise DatabaseIntegrityError(f"Group name '{group_name}' already exists for this cell", "create_group")
                else:
                    raise DatabaseIntegrityError(str(e), "create_group")
            except Exception as e:
                conn.rollback()
                raise TransactionError("create_group", str(e))
    
    def get_cell_groups(self, cell_id: int) -> List[Dict[str, Any]]:
        """Get all groups for a cell with segment counts."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT ug.group_id, ug.group_name, ug.description, ug.is_template, 
                       ug.template_type, ug.created_at, ug.updated_at,
                       COUNT(ugs.segment_id) as segment_count
                FROM user_groups ug
                LEFT JOIN user_group_segments ugs ON ug.group_id = ugs.group_id
                WHERE ug.cell_id = ?
                GROUP BY ug.group_id
                ORDER BY ug.created_at DESC
            """, (cell_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_group_info(self, group_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed group information."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT ug.group_id, ug.cell_id, ug.group_name, ug.description, 
                       ug.is_template, ug.template_type, ug.created_at, ug.updated_at,
                       COUNT(ugs.segment_id) as segment_count
                FROM user_groups ug
                LEFT JOIN user_group_segments ugs ON ug.group_id = ugs.group_id
                WHERE ug.group_id = ?
                GROUP BY ug.group_id
            """, (group_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def delete_group(self, group_id: int) -> bool:
        """Delete a group and all its segment associations."""
        with self.get_connection() as conn:
            conn.execute("BEGIN")
            try:
                # Get group info for logging
                group_info = self.get_group_info(group_id)
                
                # Delete group (CASCADE will handle user_group_segments)
                cursor = conn.execute("DELETE FROM user_groups WHERE group_id = ?", (group_id,))
                deleted = cursor.rowcount > 0
                
                conn.commit()
                
                if deleted and group_info:
                    logger.info(f"Deleted group: {group_info['group_name']} (ID: {group_id})")
                
                return deleted
                
            except Exception as e:
                conn.rollback()
                raise TransactionError("delete_group", str(e))
    
    def add_segments_to_group(self, group_id: int, segment_ids: List[int]) -> int:
        """Add segments to a group. Returns count of successfully added segments."""
        with self.get_connection() as conn:
            conn.execute("BEGIN")
            try:
                added_count = 0
                
                for segment_id in segment_ids:
                    try:
                        conn.execute("""
                            INSERT OR IGNORE INTO user_group_segments (group_id, segment_id)
                            VALUES (?, ?)
                        """, (group_id, segment_id))
                        
                        if conn.total_changes > 0:
                            added_count += 1
                            
                    except Exception as e:
                        logger.debug(f"Skipped segment {segment_id}: {e}")
                        continue
                
                conn.commit()
                logger.info(f"Added {added_count} segments to group ID: {group_id}")
                return added_count
                
            except Exception as e:
                conn.rollback()
                raise TransactionError("add_segments_to_group", str(e))
    
    def remove_segments_from_group(self, group_id: int, segment_ids: List[int]) -> int:
        """Remove segments from a group. Returns count of successfully removed segments."""
        with self.get_connection() as conn:
            conn.execute("BEGIN")
            try:
                removed_count = 0
                
                for segment_id in segment_ids:
                    cursor = conn.execute("""
                        DELETE FROM user_group_segments 
                        WHERE group_id = ? AND segment_id = ?
                    """, (group_id, segment_id))
                    
                    if cursor.rowcount > 0:
                        removed_count += 1
                
                conn.commit()
                logger.info(f"Removed {removed_count} segments from group ID: {group_id}")
                return removed_count
                
            except Exception as e:
                conn.rollback()
                raise TransactionError("remove_segments_from_group", str(e))
    
    def get_group_segments(self, group_id: int) -> List[Dict[str, Any]]:
        """Get all segments in a group with full segment information."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT s.*, f.original_filename, ugs.added_at
                FROM user_group_segments ugs
                JOIN segments s ON ugs.segment_id = s.id
                JOIN files f ON s.file_id = f.file_id
                WHERE ugs.group_id = ?
                ORDER BY s.start_time_s
            """, (group_id,))
            
            segments = []
            for row in cursor.fetchall():
                segment_data = dict(row)
                if segment_data.get('segment_metadata'):
                    segment_data['segment_metadata'] = json.loads(segment_data['segment_metadata'])
                if segment_data.get('analysis_results'):
                    segment_data['analysis_results'] = json.loads(segment_data['analysis_results'])
                segments.append(segment_data)
            
            return segments
    
    def get_cell_segments_with_groups(self, cell_id: int) -> List[Dict[str, Any]]:
        """Get all segments for a cell with their group memberships."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT s.*, f.original_filename,
                       GROUP_CONCAT(ug.group_name, ', ') as group_names,
                       GROUP_CONCAT(ug.group_id, ', ') as group_ids
                FROM segments s
                JOIN files f ON s.file_id = f.file_id
                LEFT JOIN user_group_segments ugs ON s.id = ugs.segment_id
                LEFT JOIN user_groups ug ON ugs.group_id = ug.group_id
                WHERE f.cell_id = ?
                GROUP BY s.id
                ORDER BY s.start_time_s
            """, (cell_id,))
            
            segments = []
            for row in cursor.fetchall():
                segment_data = dict(row)
                if segment_data.get('segment_metadata'):
                    segment_data['segment_metadata'] = json.loads(segment_data['segment_metadata'])
                if segment_data.get('analysis_results'):
                    segment_data['analysis_results'] = json.loads(segment_data['analysis_results'])
                    
                # Parse group information
                if segment_data['group_names']:
                    segment_data['groups'] = list(zip(
                        segment_data['group_ids'].split(', '),
                        segment_data['group_names'].split(', ')
                    ))
                else:
                    segment_data['groups'] = []
                
                segments.append(segment_data)
            
            return segments
    
    def is_segment_in_group(self, segment_id: int, group_id: int) -> bool:
        """Check if a segment belongs to a group."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 1 FROM user_group_segments 
                WHERE group_id = ? AND segment_id = ?
            """, (group_id, segment_id))
            
            return cursor.fetchone() is not None

    # =============================================================================
    # TEMPLATE GROUP OPERATIONS
    # =============================================================================

    def get_template_groups(self, cell_id: int) -> List[Dict[str, Any]]:
        """Get all template groups for a cell with segment counts."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT ug.group_id, ug.group_name, ug.description, ug.template_type,
                       ug.created_at, ug.updated_at,
                       COUNT(ugs.segment_id) as segment_count
                FROM user_groups ug
                LEFT JOIN user_group_segments ugs ON ug.group_id = ugs.group_id
                WHERE ug.cell_id = ? AND ug.is_template = 1
                GROUP BY ug.group_id
                ORDER BY ug.template_type, ug.created_at DESC
            """, (cell_id,))
            
            return [dict(row) for row in cursor.fetchall()]

    def get_user_groups(self, cell_id: int) -> List[Dict[str, Any]]:
        """Get all user groups (non-template) for a cell with segment counts."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT ug.group_id, ug.group_name, ug.description, ug.is_template, 
                       ug.template_type, ug.created_at, ug.updated_at,
                       COUNT(ugs.segment_id) as segment_count
                FROM user_groups ug
                LEFT JOIN user_group_segments ugs ON ug.group_id = ugs.group_id
                WHERE ug.cell_id = ? AND (ug.is_template = 0 OR ug.is_template IS NULL)
                GROUP BY ug.group_id
                ORDER BY ug.created_at DESC
            """, (cell_id,))
            
            return [dict(row) for row in cursor.fetchall()]

    def refresh_template_groups(self, cell_id: int) -> int:
        """
        Refresh template groups for a cell by creating template groups for all fundamental 
        techniques that have segments in the cell.
        
        Returns the number of template groups created/updated.
        """
        with self.get_connection() as conn:
            conn.execute("BEGIN")
            try:
                print(f"DEBUG DB: Starting refresh_template_groups for cell_id {cell_id}")
                
                # Get all unique fundamental techniques for this cell's segments
                # Use case-insensitive comparison since segments have lowercase fundamental_technique
                # but fundamental_techniques table has proper case technique_name
                cursor = conn.execute("""
                    SELECT DISTINCT s.fundamental_technique, ft.technique_name
                    FROM segments s
                    JOIN files f ON s.file_id = f.file_id
                    JOIN fundamental_techniques ft ON LOWER(s.fundamental_technique) = LOWER(ft.technique_name)
                    WHERE f.cell_id = ?
                    ORDER BY s.fundamental_technique
                """, (cell_id,))
                
                techniques = cursor.fetchall()
                print(f"DEBUG DB: Query returned {len(techniques)} technique mappings:")
                for technique_row in techniques:
                    print(f"  - {technique_row[0]} → {technique_row[1]}")
                
                print(f"DEBUG DB: Processing {len(techniques)} matched techniques")
                created_count = 0
                
                for technique_row in techniques:
                    fundamental_technique = technique_row[0]
                    technique_name = technique_row[1]
                    
                    template_name = f"Template_All_{fundamental_technique}"
                    description = f"Auto-generated template group for all {technique_name} segments"
                    
                    # Check if template group already exists
                    check_cursor = conn.execute("""
                        SELECT group_id FROM user_groups 
                        WHERE cell_id = ? AND group_name = ? AND is_template = 1
                    """, (cell_id, template_name))
                    
                    existing_group = check_cursor.fetchone()
                    
                    if not existing_group:
                        # Create new template group
                        insert_cursor = conn.execute("""
                            INSERT INTO user_groups (cell_id, group_name, description, is_template, template_type)
                            VALUES (?, ?, ?, 1, ?)
                        """, (cell_id, template_name, description, fundamental_technique))
                        
                        template_group_id = insert_cursor.lastrowid
                        created_count += 1
                        
                        logger.info(f"Created template group: {template_name} (ID: {template_group_id})")
                    else:
                        template_group_id = existing_group[0]
                        logger.debug(f"Template group already exists: {template_name} (ID: {template_group_id})")
                    
                    # Get all segments for this technique and add them to the template group
                    segments_cursor = conn.execute("""
                        SELECT s.id
                        FROM segments s
                        JOIN files f ON s.file_id = f.file_id
                        WHERE f.cell_id = ? AND s.fundamental_technique = ?
                    """, (cell_id, fundamental_technique))
                    
                    segment_ids = [row[0] for row in segments_cursor.fetchall()]
                    
                    if segment_ids:
                        # Clear existing associations and add all segments
                        conn.execute("""
                            DELETE FROM user_group_segments WHERE group_id = ?
                        """, (template_group_id,))
                        
                        for segment_id in segment_ids:
                            conn.execute("""
                                INSERT OR IGNORE INTO user_group_segments (group_id, segment_id)
                                VALUES (?, ?)
                            """, (template_group_id, segment_id))
                        
                        logger.debug(f"Added {len(segment_ids)} segments to template group {template_name}")
                
                conn.commit()
                logger.info(f"Template group refresh completed for cell {cell_id}: {created_count} groups created")
                return created_count
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to refresh template groups for cell {cell_id}: {e}")
                raise TransactionError("refresh_template_groups", str(e))

    def copy_group(self, source_group_id: int, new_group_name: str, 
                   copy_as_template: bool = False) -> int:
        """
        Copy a group (template or user) to a new group with all its segment associations.
        
        Returns the new group ID.
        """
        with self.get_connection() as conn:
            conn.execute("BEGIN")
            try:
                # Get source group info
                cursor = conn.execute("""
                    SELECT cell_id, group_name, description, is_template, template_type
                    FROM user_groups WHERE group_id = ?
                """, (source_group_id,))
                
                source_group = cursor.fetchone()
                if not source_group:
                    raise RecordNotFoundError(f"Source group {source_group_id} not found")
                
                cell_id, old_name, old_description, is_template, template_type = source_group
                
                # Create description for the copied group
                source_type = "template" if is_template else "user"
                new_description = f"Copied from {source_type} group '{old_name}'"
                if old_description:
                    new_description += f" - {old_description}"
                
                # Create new group
                new_template_type = template_type if copy_as_template else None
                insert_cursor = conn.execute("""
                    INSERT INTO user_groups (cell_id, group_name, description, is_template, template_type)
                    VALUES (?, ?, ?, ?, ?)
                """, (cell_id, new_group_name, new_description, copy_as_template, new_template_type))
                
                new_group_id = insert_cursor.lastrowid
                
                # Copy all segment associations
                conn.execute("""
                    INSERT INTO user_group_segments (group_id, segment_id)
                    SELECT ?, segment_id
                    FROM user_group_segments
                    WHERE group_id = ?
                """, (new_group_id, source_group_id))
                
                # Get count of copied segments
                count_cursor = conn.execute("""
                    SELECT COUNT(*) FROM user_group_segments WHERE group_id = ?
                """, (new_group_id,))
                segment_count = count_cursor.fetchone()[0]
                
                conn.commit()
                
                new_type = "template" if copy_as_template else "user"
                logger.info(f"Copied group '{old_name}' to new {new_type} group '{new_group_name}' "
                           f"(ID: {new_group_id}) with {segment_count} segments")
                
                return new_group_id
                
            except Exception as e:
                conn.rollback()
                raise TransactionError("copy_group", str(e))

    def generate_unique_group_name(self, cell_id: int, base_name: str) -> str:
        """
        Generate a unique group name by appending numbers if conflicts exist.
        
        Args:
            cell_id: Cell ID to check for conflicts
            base_name: Base name to make unique
            
        Returns:
            Unique group name (base_name, base_name_1, base_name_2, etc.)
        """
        with self.get_connection() as conn:
            # Check if base name exists
            cursor = conn.execute("""
                SELECT 1 FROM user_groups WHERE cell_id = ? AND group_name = ?
            """, (cell_id, base_name))
            
            if not cursor.fetchone():
                return base_name
            
            # Find the next available number
            counter = 1
            while True:
                candidate_name = f"{base_name}_{counter}"
                cursor = conn.execute("""
                    SELECT 1 FROM user_groups WHERE cell_id = ? AND group_name = ?
                """, (cell_id, candidate_name))
                
                if not cursor.fetchone():
                    return candidate_name
                
                counter += 1
                # Safety limit to prevent infinite loops
                if counter > 1000:
                    raise DatabaseError(f"Could not generate unique name for '{base_name}' after 1000 attempts")

    # =============================================================================
    # ANALYTICS OPERATIONS
    # =============================================================================

    def get_group_base_statistics(self, group_ids: List[int]) -> Dict[str, Dict[str, float]]:
        """
        Get aggregated statistics for multiple groups using existing segment columns.
        
        Returns statistics for 9 key metrics from the segments table.
        """
        if not group_ids:
            return {}
        
        placeholders = ','.join('?' * len(group_ids))
        
        with self.get_connection() as conn:
            cursor = conn.execute(f"""
                SELECT 
                    -- Basic statistics for each numeric column
                    AVG(start_time_s) as avg_start_time,
                    SQRT(MAX(0, AVG(start_time_s * start_time_s) - AVG(start_time_s) * AVG(start_time_s))) as std_start_time,
                    MIN(start_time_s) as min_start_time,
                    MAX(start_time_s) as max_start_time,
                    
                    AVG(duration_s) as avg_duration,
                    SQRT(MAX(0, AVG(duration_s * duration_s) - AVG(duration_s) * AVG(duration_s))) as std_duration,
                    MIN(duration_s) as min_duration,
                    MAX(duration_s) as max_duration,
                    
                    AVG(start_potential_v) as avg_start_potential,
                    SQRT(MAX(0, AVG(start_potential_v * start_potential_v) - AVG(start_potential_v) * AVG(start_potential_v))) as std_start_potential,
                    MIN(start_potential_v) as min_start_potential,
                    MAX(start_potential_v) as max_start_potential,
                    
                    AVG(end_potential_v) as avg_end_potential,
                    SQRT(MAX(0, AVG(end_potential_v * end_potential_v) - AVG(end_potential_v) * AVG(end_potential_v))) as std_end_potential,
                    MIN(end_potential_v) as min_end_potential,
                    MAX(end_potential_v) as max_end_potential,
                    
                    AVG(start_current_a) as avg_start_current,
                    SQRT(MAX(0, AVG(start_current_a * start_current_a) - AVG(start_current_a) * AVG(start_current_a))) as std_start_current,
                    MIN(start_current_a) as min_start_current,
                    MAX(start_current_a) as max_start_current,
                    
                    AVG(end_current_a) as avg_end_current,
                    SQRT(MAX(0, AVG(end_current_a * end_current_a) - AVG(end_current_a) * AVG(end_current_a))) as std_end_current,
                    MIN(end_current_a) as min_end_current,
                    MAX(end_current_a) as max_end_current,
                    
                    AVG(capacity_ah) as avg_capacity,
                    SQRT(MAX(0, AVG(capacity_ah * capacity_ah) - AVG(capacity_ah) * AVG(capacity_ah))) as std_capacity,
                    MIN(capacity_ah) as min_capacity,
                    MAX(capacity_ah) as max_capacity,
                    
                    AVG(energy_wh) as avg_energy,
                    SQRT(MAX(0, AVG(energy_wh * energy_wh) - AVG(energy_wh) * AVG(energy_wh))) as std_energy,
                    MIN(energy_wh) as min_energy,
                    MAX(energy_wh) as max_energy,
                    
                    AVG(point_count) as avg_points,
                    SQRT(MAX(0, AVG(point_count * point_count) - AVG(point_count) * AVG(point_count))) as std_points,
                    MIN(point_count) as min_points,
                    MAX(point_count) as max_points,
                    
                    COUNT(*) as total_count
                FROM segments s
                JOIN user_group_segments ugs ON s.id = ugs.segment_id
                WHERE ugs.group_id IN ({placeholders})
                AND s.start_time_s IS NOT NULL
            """, group_ids)
            
            row = cursor.fetchone()
            
            if not row or row[-1] == 0:  # total_count is 0
                return {}
            
            # Build the statistics dictionary
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

    def get_segment_subset_statistics(self, segment_ids: List[int]) -> Dict[str, Dict[str, float]]:
        """
        Get aggregated statistics for a specific subset of segments.
        """
        if not segment_ids:
            return {}
        
        placeholders = ','.join('?' * len(segment_ids))
        
        with self.get_connection() as conn:
            cursor = conn.execute(f"""
                SELECT 
                    -- Basic statistics for each numeric column
                    AVG(start_time_s) as avg_start_time,
                    SQRT(MAX(0, AVG(start_time_s * start_time_s) - AVG(start_time_s) * AVG(start_time_s))) as std_start_time,
                    MIN(start_time_s) as min_start_time,
                    MAX(start_time_s) as max_start_time,
                    
                    AVG(duration_s) as avg_duration,
                    SQRT(MAX(0, AVG(duration_s * duration_s) - AVG(duration_s) * AVG(duration_s))) as std_duration,
                    MIN(duration_s) as min_duration,
                    MAX(duration_s) as max_duration,
                    
                    AVG(start_potential_v) as avg_start_potential,
                    SQRT(MAX(0, AVG(start_potential_v * start_potential_v) - AVG(start_potential_v) * AVG(start_potential_v))) as std_start_potential,
                    MIN(start_potential_v) as min_start_potential,
                    MAX(start_potential_v) as max_start_potential,
                    
                    AVG(end_potential_v) as avg_end_potential,
                    SQRT(MAX(0, AVG(end_potential_v * end_potential_v) - AVG(end_potential_v) * AVG(end_potential_v))) as std_end_potential,
                    MIN(end_potential_v) as min_end_potential,
                    MAX(end_potential_v) as max_end_potential,
                    
                    AVG(start_current_a) as avg_start_current,
                    SQRT(MAX(0, AVG(start_current_a * start_current_a) - AVG(start_current_a) * AVG(start_current_a))) as std_start_current,
                    MIN(start_current_a) as min_start_current,
                    MAX(start_current_a) as max_start_current,
                    
                    AVG(end_current_a) as avg_end_current,
                    SQRT(MAX(0, AVG(end_current_a * end_current_a) - AVG(end_current_a) * AVG(end_current_a))) as std_end_current,
                    MIN(end_current_a) as min_end_current,
                    MAX(end_current_a) as max_end_current,
                    
                    AVG(capacity_ah) as avg_capacity,
                    SQRT(MAX(0, AVG(capacity_ah * capacity_ah) - AVG(capacity_ah) * AVG(capacity_ah))) as std_capacity,
                    MIN(capacity_ah) as min_capacity,
                    MAX(capacity_ah) as max_capacity,
                    
                    AVG(energy_wh) as avg_energy,
                    SQRT(MAX(0, AVG(energy_wh * energy_wh) - AVG(energy_wh) * AVG(energy_wh))) as std_energy,
                    MIN(energy_wh) as min_energy,
                    MAX(energy_wh) as max_energy,
                    
                    AVG(point_count) as avg_points,
                    SQRT(MAX(0, AVG(point_count * point_count) - AVG(point_count) * AVG(point_count))) as std_points,
                    MIN(point_count) as min_points,
                    MAX(point_count) as max_points,
                    
                    COUNT(*) as total_count
                FROM segments s
                WHERE s.id IN ({placeholders})
                AND s.start_time_s IS NOT NULL
            """, segment_ids)
            
            row = cursor.fetchone()
            
            if not row or row[-1] == 0:  # total_count is 0
                return {}
            
            # Build the statistics dictionary (same format as get_group_base_statistics)
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

    def get_multi_group_segments(self, group_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Get all segments from multiple groups with full segment data.
        """
        if not group_ids:
            return []
        
        placeholders = ','.join('?' * len(group_ids))
        
        with self.get_connection() as conn:
            cursor = conn.execute(f"""
                SELECT DISTINCT s.id, s.file_id, s.segment_index, s.technique_id,
                       s.start_row, s.end_row, s.start_time_s, s.end_time_s, s.duration_s,
                       s.start_potential_v, s.end_potential_v, s.start_current_a, s.end_current_a,
                       s.capacity_ah, s.energy_wh, s.point_count,
                       s.analysis_status, s.analysis_results,
                       f.original_filename, f.acquisition_start,
                       s.fundamental_technique,
                       c.name as cell_name,
                       GROUP_CONCAT(ug.group_name, ', ') as group_names
                FROM segments s
                JOIN user_group_segments ugs ON s.id = ugs.segment_id
                JOIN user_groups ug ON ugs.group_id = ug.group_id
                LEFT JOIN files f ON s.file_id = f.file_id
                LEFT JOIN cells c ON f.cell_id = c.id
                WHERE ugs.group_id IN ({placeholders})
                GROUP BY s.id
                ORDER BY s.start_time_s
            """, group_ids)
            
            segments = []
            for row in cursor.fetchall():
                segment_data = {
                    'id': row[0],
                    'file_id': row[1],
                    'segment_index': row[2],
                    'technique_id': row[3],
                    'start_row': row[4],
                    'end_row': row[5],
                    'start_time_s': row[6],
                    'end_time_s': row[7],
                    'duration_s': row[8],
                    'start_potential_v': row[9],
                    'end_potential_v': row[10],
                    'start_current_a': row[11],
                    'end_current_a': row[12],
                    'capacity_ah': row[13],
                    'energy_wh': row[14],
                    'point_count': row[15],
                    'analysis_status': row[16],
                    'analysis_results': row[17],
                    'original_filename': row[18],
                    'acquisition_start': row[19],
                    'fundamental_technique': row[20],
                    'cell_name': row[21],
                    'group_names': row[22] or ''
                }
                
                # Parse group names into list
                if segment_data['group_names']:
                    segment_data['groups'] = list(filter(None, 
                        segment_data['group_names'].split(', ')
                    ))
                else:
                    segment_data['groups'] = []
                
                segments.append(segment_data)
            
            return segments

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