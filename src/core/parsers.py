"""
Fixed VersaStudio .par file parser with performance improvements.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import polars as pl

from .data_models import (
    DataFile, ActionDefinition, SegmentData,
    create_universal_dataframe, UNIVERSAL_COLUMNS, UNIVERSAL_SCHEMA,
    VERSASTUDIO_COLUMNS, VERSASTUDIO_SCHEMA, VERSASTUDIO_CSV_SCHEMA, TECHNIQUE_MAPPING,
    map_technique_name, map_actionid_to_technique, is_structural_action, 
    calculate_file_hash, prune_empty_columns
)


class ParserError(Exception):
    """Base exception for all parser errors."""
    pass


class VersaStudioParseError(ParserError):
    """Raised when VersaStudio .par file parsing fails."""
    pass


class BaseParser:
    """Abstract base class for all instrument parsers."""

    def parse(self, file_path: Path) -> DataFile:
        """Parse an instrument data file into a DataFile object."""
        raise NotImplementedError("Subclasses must implement parse method")

    def validate_file(self, file_path: Path) -> bool:
        """Validate that the file can be parsed by this parser."""
        raise NotImplementedError("Subclasses must implement validate_file method")


class VersaStudioParser(BaseParser):
    """
    Parser for VersaStudio .par files.

    Uses line-by-line parsing for metadata and Polars for data sections.
    """

    def __init__(self, debug_structural_parsing=False):
        super().__init__()
        self.debug_structural_parsing = debug_structural_parsing
        self.sections = {}
        self.actions = {}  # Will store experimental actions with continuous indexing
        self.segments = {}
        self.experimental_action_counter = 0  # Counter for continuous indexing
        self.original_action_mapping = {}  # Track original ActionX -> continuous index
        self.loop_iterations = {}  # Store loop iteration counts: {loop_name: iterations}

    def validate_file(self, file_path: Path) -> bool:
        """Validate that this is a VersaStudio .par file."""
        if not file_path.exists() or file_path.suffix.lower() != '.par':
            return False

        # Quick check for VersaStudio format markers
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_chunk = f.read(1000)
                return '<Application>' in first_chunk or '<Experiment>' in first_chunk
        except:
            return False

    def parse(self, file_path: Path) -> DataFile:
        """
        Parse a .par file for METADATA ONLY - no segment data parsing.
        
        For dual file processing, use parse_dual_files() which gets metadata from .par 
        and data from .par.csv files.

        Args:
            file_path: Path to the .par file

        Returns:
            DataFile object with metadata and empty universal_data DataFrame

        Raises:
            VersaStudioParseError: If parsing fails
        """
        try:
            # Line-by-line parsing for metadata and ActionID mappings only
            self._parse_file_structure(file_path)

            # Skip all segment data parsing - metadata only approach
            # Data will come from .par.csv files in dual file processing

            # Create DataFile object with metadata only
            data_file = self._create_metadata_only_data_file(file_path)

            return data_file

        except Exception as e:
            raise VersaStudioParseError(f"Failed to parse {file_path}: {str(e)}") from e

    def _parse_file_structure(self, file_path: Path) -> None:
        """Parse file structure line by line for METADATA ONLY - skip segment data."""
        self.sections = {}
        self.actions = {}
        # Note: No segment_boundaries tracking - we skip all segment data

        current_section = None
        current_section_content = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f):
                    line = line.strip()

                    # Skip empty lines
                    if not line:
                        continue

                    # Section start
                    if line.startswith('<') and line.endswith('>') and not line.startswith('</'):
                        # Save previous section
                        if current_section:
                            self._process_section(current_section, current_section_content)

                        # Start new section
                        current_section = line[1:-1]  # Remove < >
                        current_section_content = []

                        # Skip segment sections entirely - metadata-only parsing
                        if current_section.startswith('Segment'):
                            current_section = None  # Ignore segment sections completely

                    # Section end
                    elif line.startswith('</') and line.endswith('>'):
                        # Save current section
                        if current_section:
                            self._process_section(current_section, current_section_content)
                            current_section = None
                            current_section_content = []

                        # Skip segment end tracking - metadata-only parsing
                        # No segment boundary tracking needed

                    # Section content
                    elif current_section:
                        current_section_content.append((line_num, line))

                # Process final section
                if current_section:
                    self._process_section(current_section, current_section_content)

        except UnicodeDecodeError:
            # Try with latin-1 encoding as backup
            with open(file_path, 'r', encoding='latin-1') as f:
                # Repeat the same logic...
                pass

    def _process_section(self, section_name: str, content: List[Tuple[int, str]]) -> None:
        """Process a parsed section - metadata only, skip segments entirely."""
        if section_name.startswith('Action'):
            action = self._parse_action(section_name, content)
            if action:  # Only experimental actions (structural ones filtered out)
                # Store with continuous indexing instead of original action_id
                self.actions[self.experimental_action_counter] = action
                # Track mapping from original ActionX to continuous index
                self.original_action_mapping[action.action_id] = self.experimental_action_counter
                self.experimental_action_counter += 1
        elif section_name.startswith('Segment'):
            # SKIP ALL SEGMENT PROCESSING - metadata-only approach
            pass  # Completely ignore segment sections
        else:
            # Regular section
            section_dict = {}
            for line_num, line in content:
                if '=' in line:
                    key, value = line.split('=', 1)
                    section_dict[key.strip()] = value.strip()
            self.sections[section_name] = section_dict

    def _parse_action(self, section_name: str, content: List[Tuple[int, str]]) -> Optional[ActionDefinition]:
        """Parse an action section, filtering out structural actions."""
        action_match = re.match(r'Action(\d+)', section_name)
        if not action_match:
            return None

        action_id = int(action_match.group(1))

        # Parse action parameters
        parameters = {}
        for line_num, line in content:
            if '=' in line:
                key, value = line.split('=', 1)
                parameters[key.strip()] = value.strip()

        # Extract action name
        name = parameters.get('Name', f'Action{action_id}')

        # FILTER OUT STRUCTURAL ACTIONS AT PARSE TIME
        if is_structural_action(name):
            # Don't store structural actions - they won't be in self.actions
            # But capture loop iteration info before filtering
            if 'Loop #' in name and 'Number of Iterations' in parameters:
                try:
                    iterations = int(parameters['Number of Iterations'])
                    self.loop_iterations[name] = iterations
                    if self.debug_structural_parsing:
                        print(f"🔄 Captured loop: {name} → {iterations} iterations")
                except ValueError:
                    pass
                    
            if self.debug_structural_parsing:
                print(f"🚫 Filtered structural: Action{action_id} ({name})")
            return None

        # Extract parent action if specified
        parent_id = None
        parent_loop_name = None
        if 'ParentNode' in parameters:
            parent_node = parameters['ParentNode']
            parent_match = re.search(r'Action(\d+)', parent_node)
            if parent_match:
                parent_id = int(parent_match.group(1))
            # Handle string parent nodes like "Common", "Loop #2"
            elif parent_node == 'Common':
                parent_id = None  # Top-level action
            elif 'Loop #' in parent_node:
                # Store loop name for later resolution
                parent_loop_name = parent_node
                parent_id = None  # Will be resolved in execution sequence building


        # Store parent loop name in parameters for execution sequence building
        if parent_loop_name:
            parameters['_parent_loop'] = parent_loop_name

        if self.debug_structural_parsing:
            print(f"✅ Stored experimental: Action{action_id} ({name}) → continuous_index {self.experimental_action_counter}, parent_loop={parent_loop_name}")

        return ActionDefinition(
            action_id=action_id,
            name=name,
            parameters=parameters,
            parent_action_id=parent_id
        )

    def _parse_segment_metadata(self, segment_id: int, content: List[Tuple[int, str]]) -> None:
        """Parse segment metadata and find data boundaries."""
        segment_type = None
        version = None
        definition = None
        data_start_line = None

        for line_num, line in content:
            if line.startswith('Type='):
                segment_type = int(line.split('=')[1])
            elif line.startswith('Version='):
                version = int(line.split('=')[1])
            elif line.startswith('Definition='):
                definition = line.split('=', 1)[1]
                data_start_line = line_num + 1
                break

        if segment_id in self.segment_boundaries:
            self.segment_boundaries[segment_id].update({
                'segment_type': segment_type,
                'version': version,
                'definition': definition,
                'data_start_line': data_start_line
            })

    def _parse_data_with_polars(self, file_path: Path) -> None:
        """Use Polars to parse data sections efficiently."""
        self.segments = {}

        for segment_id, boundaries in self.segment_boundaries.items():
            try:
                # Extract boundary info
                data_start = boundaries.get('data_start_line')
                data_end = boundaries.get('end_line')
                definition = boundaries.get('definition', '')

                if data_start is None or data_end is None:
                    continue

                # Parse column names from definition
                available_columns = self._parse_column_definition(definition)

                # Calculate number of data rows
                n_rows = data_end - data_start -1

                if n_rows <= 0:
                    # Empty segment
                    df = pl.DataFrame(schema=VERSASTUDIO_SCHEMA)
                else:
                    # Read data with Polars
                    df = pl.read_csv(
                        file_path,
                        skip_rows=data_start,
                        n_rows=n_rows,
                        has_header=False,
                        separator=',',
                        schema=self._create_segment_schema(available_columns),
                        ignore_errors=True
                    )

                    # Standardize to full schema
                    df = self._standardize_dataframe(df, available_columns)

                # Create segment data object
                segment_data = SegmentData(
                    segment_id=segment_id,
                    segment_type=boundaries.get('segment_type', 0),
                    version=boundaries.get('version', 0),
                    column_definition=definition,
                    data=df
                )

                self.segments[segment_id] = segment_data

            except Exception as e:
                print(f"Warning: Failed to parse segment {segment_id}: {e}")
                continue

    def _parse_column_definition(self, definition: str) -> List[str]:
        """Parse column definition string."""
        if not definition:
            return []

        # Split by comma and clean up column names
        columns = []
        for col in definition.split(','):
            col = col.strip()
            if col and col != '0':  # Skip empty and trailing '0'
                columns.append(col)

        return columns

    def _create_segment_schema(self, available_columns: List[str]) -> Dict[str, pl.DataType]:
        """Create Polars schema for available columns."""
        schema = {}
        for col in available_columns:
            if col in VERSASTUDIO_SCHEMA:
                schema[col] = VERSASTUDIO_SCHEMA[col]
            else:
                # Default to float for unknown columns
                schema[col] = pl.Float64
        return schema

    def _standardize_dataframe(self, df: pl.DataFrame, available_columns: List[str]) -> pl.DataFrame:
        """Convert DataFrame to standardized schema."""
        # Start with current data
        result_data = {}

        for col in VERSASTUDIO_COLUMNS:
            if col in available_columns and col in df.columns:
                result_data[col] = df.get_column(col)
            else:
                # Create null column with correct type
                null_series = pl.Series([None] * df.height, dtype=VERSASTUDIO_SCHEMA[col])
                result_data[col] = null_series

        return pl.DataFrame(result_data, schema=VERSASTUDIO_SCHEMA)

    def _extract_timestamp(self) -> datetime:
        """Extract experiment timestamp from metadata."""
        if 'Experiment' not in self.sections:
            raise VersaStudioParseError("No Experiment section found")

        exp_section = self.sections['Experiment']

        # Get date and time
        date_str = exp_section.get('DateAcquired', '')
        time_str = exp_section.get('TimeAcquired', '')

        if not date_str or not time_str:
            raise VersaStudioParseError("Missing DateAcquired or TimeAcquired")

        # Parse timestamp
        try:
            datetime_str = f"{date_str} {time_str}"

            # Try different formats
            formats = [
                "%A, %B %d, %Y %I:%M:%S %p",
                "%A, %B %d, %Y %H:%M:%S",
                "%m/%d/%Y %I:%M:%S %p",
                "%m/%d/%Y %H:%M:%S",
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(datetime_str, fmt)
                except ValueError:
                    continue

            raise ValueError(f"Could not parse timestamp: {datetime_str}")

        except Exception as e:
            raise VersaStudioParseError(f"Invalid timestamp format: {e}")

    def _combine_segments(self) -> pl.DataFrame:
        """Combine all segments into single dataframe with technique mapping."""
        if not self.segments:
            return pl.DataFrame(schema=VERSASTUDIO_SCHEMA)

        # Collect all segment dataframes
        segment_dfs = []
        for segment in self.segments.values():
            if not segment.data.is_empty():
                segment_dfs.append(segment.data)

        if not segment_dfs:
            return pl.DataFrame(schema=VERSASTUDIO_SCHEMA)

        # Combine segments
        combined = pl.concat(segment_dfs, how="vertical_relaxed")

        # Add technique mapping using efficient Polars operations
        combined = self._add_technique_mapping(combined)

        return combined
    
    def _build_execution_sequence(self) -> List[Tuple[int, ActionDefinition, str, int]]:
        """Build execution sequence from ParentNode relationships."""
        if not self.actions:
            return []
        
        # Group actions by parent type
        top_level_actions = []    # parent_id = None (Common) 
        loop_groups = {}          # grouped by loop name
        
        for continuous_index, action in self.actions.items():
            parent_loop = action.parameters.get('_parent_loop')
            
            if parent_loop:
                # Action belongs to a loop
                if parent_loop not in loop_groups:
                    loop_groups[parent_loop] = []
                loop_groups[parent_loop].append((continuous_index, action))
            else:
                # Top-level action (Common parent or no parent)
                top_level_actions.append((continuous_index, action))
        
        # Sort within each group by original action_id to maintain VersaStudio order
        top_level_actions.sort(key=lambda x: x[1].action_id)
        for loop_name in loop_groups:
            loop_groups[loop_name].sort(key=lambda x: x[1].action_id)
        
        # Build execution sequence: top-level first, then expanded loops
        execution_sequence = []
        
        # Add top-level actions (execute once)
        for continuous_index, action in top_level_actions:
            execution_sequence.append((continuous_index, action, 'top_level', 1))
        
        # Add loop actions (expand based on iterations)
        for loop_name in sorted(loop_groups.keys()):
            loop_iterations = self.loop_iterations.get(loop_name, 1)  # Default to 1 if not found
            loop_actions = loop_groups[loop_name]
            
            # Repeat the loop actions for each iteration
            for iteration in range(loop_iterations):
                for continuous_index, action in loop_actions:
                    execution_sequence.append((continuous_index, action, f'loop_{loop_name}', iteration + 1))
        
        if self.debug_structural_parsing:
            print(f"\n🔄 Execution Sequence Built:")
            print(f"   Top-level actions: {len(top_level_actions)}")
            print(f"   Loop groups: {list(loop_groups.keys())}")
            print(f"   Loop iterations: {self.loop_iterations}")
            print(f"   Total expanded segments: {len(execution_sequence)}")
            for continuous_index, action, group_type, iteration in execution_sequence:
                print(f"   {group_type}: Action{action.action_id} ({action.name}) → iteration {iteration}")
        
        return execution_sequence
    
    def _build_segment_mapping(self) -> pl.DataFrame:
        """Build segment-to-action mapping using execution sequence."""
        execution_sequence = self._build_execution_sequence()
        
        if not execution_sequence:
            return pl.DataFrame({
                'segment_number': [],
                'technique_name': [],
                'fundamental_technique': []
            })
        
        # Build mapping based on execution sequence
        mapping_data = {
            'segment_number': [],
            'technique_name': [],
            'fundamental_technique': []
        }
        
        segment_counter = 0
        
        # Process expanded execution sequence
        for continuous_index, action, group_type, iteration in execution_sequence:
            mapping_data['segment_number'].append(segment_counter)
            mapping_data['technique_name'].append(action.name)
            mapping_data['fundamental_technique'].append(map_technique_name(action.name))
            segment_counter += 1
        
        # Create mapping DataFrame
        mapping_df = pl.DataFrame(mapping_data)
        
        
        return mapping_df
    
    def _add_technique_mapping(self, df: pl.DataFrame) -> pl.DataFrame:
        """Add technique names using both ActionId and execution sequence mapping."""
        if df.is_empty():
            return df
        
        # Method 1: ActionId-based mapping (simple, direct, partial coverage)
        df_with_actionid = self._add_actionid_technique_mapping(df)
        
        # Method 2: Execution sequence mapping (complete, complex)
        df_with_hierarchy = self._add_hierarchy_technique_mapping(df_with_actionid)
        
        return df_with_hierarchy
    
    def _add_actionid_technique_mapping(self, df: pl.DataFrame) -> pl.DataFrame:
        """Add ActionId-based technique mapping (simple, direct method)."""
        if 'ActionId' not in df.columns:
            # Add default columns if ActionId not available
            df = df.with_columns([
                pl.lit('Unknown').alias('technique_name_actionid'),
                pl.lit('UNKNOWN').alias('fundamental_technique_actionid')
            ])
            return df
        
        # Create ActionId → technique mapping using Polars
        df = df.with_columns([
            # Direct ActionId mapping
            pl.col('ActionId').map_elements(
                lambda x: map_actionid_to_technique(x) if x is not None else 'UNKNOWN',
                return_dtype=pl.Utf8
            ).alias('fundamental_technique_actionid'),
            
            # Keep ActionId as technique name for now (can be enhanced later)
            pl.format('ActionId_{}', pl.col('ActionId')).alias('technique_name_actionid')
        ])
        
        return df
    
    def _add_hierarchy_technique_mapping(self, df: pl.DataFrame) -> pl.DataFrame:
        """Add hierarchy-based technique mapping (complex, complete method)."""
        # Build segment mapping from execution sequence
        mapping_df = self._build_segment_mapping()
        
        if mapping_df.is_empty():
            # No actions available - add default columns
            df = df.with_columns([
                pl.lit('Unknown').alias('technique_name'),
                pl.lit('UNKNOWN').alias('fundamental_technique')
            ])
            return df
        
        # Join data with mapping
        df = df.join(
            mapping_df,
            left_on='Segment #',
            right_on='segment_number',
            how='left'
        )
        
        # Fill missing values for unmapped segments
        df = df.with_columns([
            pl.col('technique_name').fill_null('Unknown'),
            pl.col('fundamental_technique').fill_null('UNKNOWN')
        ])
        
        # Prefer ActionId mapping when available, fall back to hierarchy mapping
        if 'fundamental_technique_actionid' in df.columns:
            df = df.with_columns([
                pl.when(pl.col('fundamental_technique_actionid') != 'UNKNOWN')
                .then(pl.col('fundamental_technique_actionid'))
                .otherwise(pl.col('fundamental_technique'))
                .alias('fundamental_technique_final')
            ])
        
        return df
    
    def _validate_technique_mapping(self, df: pl.DataFrame) -> Dict[str, Any]:
        """Validate that ActionId → Fundamental Technique mapping is consistent."""
        if df.is_empty() or 'ActionId' not in df.columns:
            return {'validation_passed': True, 'message': 'No ActionId data to validate'}
            
        # Group by ActionId and check consistency
        validation_stats = df.group_by('ActionId').agg([
            pl.col('fundamental_technique').n_unique().alias('unique_techniques'),
            pl.col('fundamental_technique').first().alias('primary_technique'),
            pl.col('Segment #').n_unique().alias('segments_spanned'),
            pl.col('ActionId').count().alias('total_points')
        ])
        
        # Find inconsistent mappings (ActionId maps to multiple techniques)
        inconsistent = validation_stats.filter(pl.col('unique_techniques') > 1)
        
        # Find unknown mappings
        unknown = validation_stats.filter(pl.col('primary_technique') == 'UNKNOWN')
        
        # Create ActionId → Technique mapping for database building
        actionid_to_technique = validation_stats.select(['ActionId', 'primary_technique']).to_dicts()
        
        validation_passed = inconsistent.is_empty() and unknown.is_empty()
        
        return {
            'validation_passed': validation_passed,
            'inconsistent_actionids': inconsistent.to_dicts() if not inconsistent.is_empty() else [],
            'unknown_actionids': unknown.to_dicts() if not unknown.is_empty() else [],
            'actionid_to_technique_mapping': actionid_to_technique,
            'total_actionids': validation_stats.height,
            'validation_summary': validation_stats.to_dicts()
        }

    def _add_absolute_timestamps(self, df: pl.DataFrame, start_time: datetime) -> pl.DataFrame:
        """Legacy function - timestamps now handled in universal schema conversion."""
        return df

    def _create_data_file(self, file_path: Path) -> DataFile:
        """Create DataFile object from parsed data."""
        # Extract timestamp
        timestamp = self._extract_timestamp()

        # Debug: Show execution sequence if debug mode enabled
        if self.debug_structural_parsing:
            self._build_execution_sequence()  # This will print debug output

        # Combine all segment data with technique mapping (VersaStudio format)
        # NOTE: Technique mapping now happens inside _combine_segments()
        combined_data = self._combine_segments()
        
        # Validate ActionId consistency using internal validation
        validation_results = self._validate_technique_mapping(combined_data)
        
        # Log warnings for inconsistencies
        if not validation_results['validation_passed']:
            print(f"Warning: Technique mapping inconsistencies detected in {file_path.name}")
            if validation_results['inconsistent_actionids']:
                print(f"  Inconsistent ActionIds: {validation_results['inconsistent_actionids']}")
            if validation_results['unknown_actionids']:
                print(f"  Unknown ActionIds: {validation_results['unknown_actionids']}")

        # Convert to universal schema (now much simpler - just column translation)
        universal_data = create_universal_dataframe(combined_data, timestamp)

        # Extract enhanced metadata
        metadata = self._extract_metadata()
        # Add validation results and ActionId mapping for database building
        metadata['mapping_validation'] = validation_results
        metadata['actionid_to_technique_database'] = validation_results.get('actionid_to_technique_mapping', [])

        return DataFile(
            file_path=file_path,
            timestamp=timestamp,
            universal_data=universal_data,
            actions=self.actions,
            segments=self.segments,
            metadata=metadata,
            file_hash=calculate_file_hash(file_path)
        )

    def _create_metadata_only_data_file(self, file_path: Path) -> DataFile:
        """Create DataFile object with metadata only - no segment data."""
        # Extract timestamp
        timestamp = self._extract_timestamp()

        # Create empty universal schema DataFrame - no data from .par file
        from .data_models import UNIVERSAL_SCHEMA
        universal_data = pl.DataFrame(schema=UNIVERSAL_SCHEMA)

        # Extract metadata (same as regular parsing)
        metadata = self._extract_metadata()
        
        # Add ActionID to technique mapping for database building
        actionid_mappings = []
        for action in self.actions.values():
            if action:  # Only valid actions
                actionid_mappings.append({
                    'ActionId': action.action_id,
                    'technique_name': action.name,
                    'primary_technique': action.technique.value if hasattr(action, 'technique') else 'UNKNOWN'
                })
        
        metadata['actionid_to_technique_database'] = actionid_mappings
        metadata['parsing_mode'] = 'metadata_only'

        return DataFile(
            file_path=file_path,
            timestamp=timestamp,
            universal_data=universal_data,  # Empty DataFrame
            actions=self.actions,
            segments={},  # No segments in metadata-only mode
            metadata=metadata,
            file_hash=calculate_file_hash(file_path)
        )

    def _extract_metadata(self) -> Dict[str, Any]:
        """Extract relevant metadata from all sections."""
        metadata = {}

        # Copy all sections
        for section_name, section_data in self.sections.items():
            metadata[section_name] = section_data.copy()

        # Add action summary
        metadata['actions_summary'] = {
            'total_actions': len(self.actions),
            'action_names': [action.name for action in self.actions.values()],
            'techniques': list(set(action.technique.value for action in self.actions.values()))
        }

        # Add segment summary
        metadata['segments_summary'] = {
            'total_segments': len(self.segments),
            'total_points': sum(segment.row_count for segment in self.segments.values())
        }

        return metadata

    # Dual file processing methods for Panel UI integration
    def parse_dual_files(self, par_path: Path, csv_path: Path) -> DataFile:
        """
        Parse both .par and .par.csv files for complete data processing.
        
        This method combines technique sequence mapping from .par files with
        calibrated measurement data from .par.csv files exported by VersaStudio.
        
        Args:
            par_path: Path to .par file (technique sequence and ActionId mapping)
            csv_path: Path to .par.csv file (calibrated measurement data)
            
        Returns:
            DataFile with combined technique mapping and calibrated data
            
        Raises:
            VersaStudioParseError: If files are incompatible or parsing fails
        """
        if not self.validate_dual_files(par_path, csv_path):
            raise VersaStudioParseError(f"Incompatible file pair: {par_path.name} and {csv_path.name}")
        
        try:
            # Parse .par file for technique sequence only (no data segments)
            structure_data = self.parse_structure_only(par_path)
            
            # Parse .par.csv file for calibrated measurement data
            calibrated_data = self.parse_calibrated_csv(csv_path)
            
            # Merge technique mapping with calibrated data
            merged_data = self.merge_dual_file_data(structure_data, calibrated_data, par_path)
            
            return merged_data
            
        except Exception as e:
            raise VersaStudioParseError(f"Dual file parsing failed: {str(e)}") from e
    
    def parse_structure_only(self, par_path: Path) -> Dict[str, Any]:
        """
        Parse .par file for technique sequence and ActionId mapping only.
        
        Extracts action hierarchy, technique names, and ActionId mapping
        without processing large data segments.
        
        Args:
            par_path: Path to .par file
            
        Returns:
            Dictionary with technique mapping and metadata
        """
        # Parse file structure (actions and metadata only)
        self._parse_file_structure(par_path)
        
        # Build execution sequence for technique mapping
        execution_sequence = self._build_execution_sequence()
        segment_mapping = self._build_segment_mapping()
        
        # Create technique mapping table from DataFrame
        technique_mapping = []
        if not segment_mapping.is_empty():
            for row in segment_mapping.iter_rows(named=True):
                segment_number = row['segment_number']
                technique_name = row['technique_name']
                fundamental_technique = row['fundamental_technique']
                
                # Find corresponding action_id (simplified for now)
                action_id = None
                for action in self.actions.values():
                    if action.name == technique_name:
                        action_id = action.action_id
                        break
                
                mapping_entry = {
                    'segment_number': segment_number,
                    'action_id': action_id,
                    'technique_name': technique_name,
                    'fundamental_technique': fundamental_technique
                }
                technique_mapping.append(mapping_entry)
        
        return {
            'technique_mapping': technique_mapping,
            'actions': {k: {'name': v.name, 'technique': v.technique.value} for k, v in self.actions.items()},
            'metadata': self._extract_metadata(),
            'timestamp': self._extract_timestamp()
        }
    
    def parse_calibrated_csv(self, csv_path: Path) -> pl.DataFrame:
        """
        Parse VersaStudio exported .par.csv file for calibrated measurement data.
        
        VersaStudio CSV exports contain calibrated data that should be used
        for EIS measurements and other calibrated analyses.
        
        Args:
            csv_path: Path to .par.csv file
            
        Returns:
            Polars DataFrame with calibrated measurement data
            
        Raises:
            VersaStudioParseError: If CSV parsing fails
        """
        try:
            # First, try to read with VersaStudio CSV schema for proper type detection
            df = pl.read_csv(
                csv_path,
                has_header=True,
                schema=VERSASTUDIO_CSV_SCHEMA,
                ignore_errors=False
            )
            
            # Validate that this is a VersaStudio CSV export
            if not self._validate_versastudio_csv(df):
                raise VersaStudioParseError(f"Not a valid VersaStudio CSV export: {csv_path.name}")
            
            # Apply VersaStudio CSV column mapping
            df = self._map_csv_columns_to_universal(df)
            
            # Add computed columns for universal schema compatibility
            df = self._add_csv_computed_columns(df)
            
            return df
            
        except Exception as e:
            raise VersaStudioParseError(f"Failed to parse CSV file {csv_path.name}: {str(e)}") from e
    
    def _validate_versastudio_csv(self, df: pl.DataFrame) -> bool:
        """
        Validate that DataFrame is a VersaStudio CSV export.
        
        Args:
            df: Polars DataFrame from CSV
            
        Returns:
            True if valid VersaStudio CSV format
        """
        # Check for .par.csv export column names (based on actual CSV structure)
        required_columns = ['Segment', 'Point', 'ActionId', 'Potential (V)', 'Current (A)', 'Elapsed Time (s)']
        return all(col in df.columns for col in required_columns)
    
    def _map_csv_columns_to_universal(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Map VersaStudio CSV columns to universal schema.
        
        Args:
            df: Raw CSV DataFrame from .par.csv export
            
        Returns:
            DataFrame with universal schema columns
        """
        # Use VersaStudio CSV mapping for calibrated data
        from .data_models import VERSASTUDIO_CSV_MAPPING
        
        # Create mapping for available columns
        column_mapping = {}
        for vs_col, universal_col in VERSASTUDIO_CSV_MAPPING.items():
            if vs_col in df.columns:
                column_mapping[vs_col] = universal_col
        
        # Rename columns
        df = df.rename(column_mapping)
        
        # Add missing universal schema columns with null values
        for col in UNIVERSAL_COLUMNS:
            if col not in df.columns:
                df = df.with_columns(pl.lit(None).alias(col))
        
        return df.select(UNIVERSAL_COLUMNS)
    
    def _add_csv_computed_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Add computed columns to CSV data for universal schema compatibility.
        
        Args:
            df: DataFrame with mapped columns
            
        Returns:
            DataFrame with computed columns added
        """
        df = df.with_columns([
            # Power calculation
            (pl.col('potential_v') * pl.col('current_a')).alias('power_w'),
            
            # Convert charge from Coulombs to Ah (1 Ah = 3600 C)
            (pl.col('charge_capacity_ah') / 3600.0).alias('charge_capacity_ah'),
            
            # Energy calculation (power integrated over time, approximated)
            (pl.col('potential_v') * pl.col('current_a') * pl.col('time_s') / 3600.0).alias('energy_wh')
        ])
        
        return df
    
    def merge_dual_file_data(self, structure_data: Dict[str, Any], 
                           calibrated_data: pl.DataFrame, par_path: Path) -> DataFile:
        """
        Merge technique mapping from .par with calibrated data from .par.csv.
        
        Args:
            structure_data: Technique mapping and metadata from .par file
            calibrated_data: Calibrated measurement data from .par.csv file
            par_path: Original .par file path for DataFile creation
            
        Returns:
            DataFile with combined data
        """
        # Create technique mapping lookup
        technique_lookup = {}
        for mapping in structure_data['technique_mapping']:
            segment_num = mapping['segment_number']
            technique_lookup[segment_num] = {
                'action_id': mapping['action_id'],
                'technique_name': mapping['technique_name'],
                'fundamental_technique': mapping['fundamental_technique']
            }
        
        # Add technique columns to calibrated data
        calibrated_data = calibrated_data.with_columns([
            # Map segment numbers to techniques
            pl.col('segment_number').map_elements(
                lambda seg: technique_lookup.get(seg, {}).get('action_id'),
                return_dtype=pl.Int64
            ).alias('technique_id'),
            
            pl.col('segment_number').map_elements(
                lambda seg: technique_lookup.get(seg, {}).get('technique_name'),
                return_dtype=pl.Utf8
            ).alias('technique_name'),
            
            pl.col('segment_number').map_elements(
                lambda seg: technique_lookup.get(seg, {}).get('fundamental_technique'),
                return_dtype=pl.Utf8
            ).alias('fundamental_technique')
        ])
        
        # Add absolute timestamps
        start_timestamp = structure_data['timestamp']
        calibrated_data = calibrated_data.with_columns([
            (pl.lit(start_timestamp) + 
             pl.duration(seconds=pl.col('time_s'))).alias('timestamp')
        ])
        
        # Create DataFile object
        return DataFile(
            file_path=par_path,
            timestamp=start_timestamp,
            universal_data=calibrated_data,
            actions=structure_data['actions'],
            segments={},  # Segments not needed for dual file processing
            metadata={
                **structure_data['metadata'],
                'processing_type': 'dual_file',
                'calibrated_data_source': 'par_csv_export',
                'data_quality': 'calibrated'
            },
            file_hash=calculate_file_hash(par_path)
        )
    
    def validate_dual_files(self, par_path: Path, csv_path: Path) -> bool:
        """
        Validate that .par and .par.csv files are compatible for dual processing.
        
        Args:
            par_path: Path to .par file
            csv_path: Path to .par.csv file
            
        Returns:
            True if files are compatible for dual processing
        """
        try:
            # Basic file existence and extension checks
            if not (par_path.exists() and csv_path.exists()):
                return False
            
            if par_path.suffix.lower() != '.par':
                return False
                
            if not csv_path.name.lower().endswith('.par.csv'):
                return False
            
            # Check if CSV file is readable with correct schema
            try:
                test_df = pl.read_csv(csv_path, has_header=True, n_rows=5, schema=VERSASTUDIO_CSV_SCHEMA)
                if not self._validate_versastudio_csv(test_df):
                    return False
            except Exception as e:
                # Log schema validation error for debugging
                print(f"CSV validation failed for {csv_path.name}: {e}")
                return False
            
            # Check file timestamps (CSV should be newer or same time as PAR)
            par_time = par_path.stat().st_mtime
            csv_time = csv_path.stat().st_mtime
            
            # Allow CSV to be up to 1 hour older (manual export timing)
            time_diff = par_time - csv_time
            if time_diff > 3600:  # 1 hour in seconds
                return False
            
            return True
            
        except Exception:
            return False
    
    def _map_action_to_fundamental_technique(self, action_id: Optional[int], action_name: Optional[str]) -> str:
        """
        Map action to fundamental technique using dual approach.
        
        Args:
            action_id: VersaStudio ActionId
            action_name: Action name from hierarchy
            
        Returns:
            Fundamental technique name
        """
        # Priority 1: ActionId-based mapping
        if action_id is not None:
            technique = map_actionid_to_technique(action_id)
            if technique != 'UNKNOWN':
                return technique
        
        # Priority 2: Hierarchy-based mapping
        if action_name:
            return map_technique_name(action_name)
        
        return 'UNKNOWN'


# Convenience function
def parse_par_file(file_path: Path) -> DataFile:
    """Parse a VersaStudio .par file."""
    parser = VersaStudioParser()
    return parser.parse(file_path)