CREATE TABLE cells (
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
            );
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE files (
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
                channel_id INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cell_id) REFERENCES cells(id) ON DELETE CASCADE
            );
CREATE TABLE segments (
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
                cell_id INTEGER,
                cell_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, exp_discharge_energy_wh REAL DEFAULT 0.0, exp_discharge_cap_ah REAL DEFAULT 0.0, exp_charge_cap_ah REAL DEFAULT 0.0, exp_time_cumulative_s REAL DEFAULT 0.0, exp_charge_energy_wh REAL DEFAULT 0.0, start_we_potential_v REAL, end_we_potential_v REAL, start_ce_potential_v REAL, end_ce_potential_v REAL,
                FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE CASCADE,
                FOREIGN KEY (cell_id) REFERENCES cells(id) ON DELETE CASCADE,
                UNIQUE(file_id, segment_index)
            );
CREATE TABLE user_groups (
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
            );
CREATE TABLE user_group_segments (
                group_id INTEGER NOT NULL,
                segment_id INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (group_id, segment_id),
                FOREIGN KEY (group_id) REFERENCES user_groups(group_id) ON DELETE CASCADE,
                FOREIGN KEY (segment_id) REFERENCES segments(id) ON DELETE CASCADE
            );
CREATE TABLE fundamental_techniques (
                technique_id INTEGER PRIMARY KEY,
                technique_name TEXT UNIQUE NOT NULL,
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
CREATE TABLE instrument_actionid_mappings (
                action_id INTEGER PRIMARY KEY,
                action_name TEXT NOT NULL,
                technique_id INTEGER NOT NULL,
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (technique_id) REFERENCES fundamental_techniques(technique_id)
            );
CREATE INDEX idx_files_cell_id ON files(cell_id);
CREATE INDEX idx_files_file_id ON files(file_id);
CREATE INDEX idx_segments_file_id ON segments(file_id);
CREATE INDEX idx_segments_technique ON segments(fundamental_technique);
CREATE INDEX idx_user_groups_cell_id ON user_groups(cell_id);
CREATE INDEX idx_user_group_segments_group_id ON user_group_segments(group_id);
CREATE INDEX idx_user_group_segments_segment_id ON user_group_segments(segment_id);
CREATE INDEX idx_fundamental_techniques_name ON fundamental_techniques(technique_name);
CREATE INDEX idx_instrument_mappings_technique ON instrument_actionid_mappings(technique_id);
