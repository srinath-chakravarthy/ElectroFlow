# Universal Capacity & Energy Integration - Parsing and Database Design

## Overview

Complete design for implementing physics-based capacity and energy integration at the file parsing level with standardized segment database storage. Uses scipy trapezoidal integration for accurate results with variable time intervals, providing both segment-level metrics and experimental timeline context.

## Timestamp Integration Foundation

### Problem Solved
**Multi-file experiments lose temporal continuity:**
- File 1: `elapsed_time_s` goes 0s → 3600s
- File 2: `elapsed_time_s` resets to 0s → 1800s (loses experimental timeline!)

### Solution
- **Universal Schema**: Add `timestamp` column (absolute time for each data point)
- **Segments Table**: Add `start_timestamp` column (enables cross-file temporal analysis)
- **Extraction Sources**:
  - VersaStudio: `DateAcquired` + `TimeAcquired` + `elapsed_time_s`
  - BioLogic: `acquisition_start` + `elapsed_time_s`

### Benefits
- Temporal aggregation: "All segments from 9:00-11:00 AM across multiple files"
- Discontinuous experiments: Pause overnight, resume next day with continuity
- Cross-experiment correlation: Compare experiments from different time periods

## Universal Schema Extensions

### Core Integration Columns (29-Column Schema)
```python
INTEGRATION_COLUMNS = [
    # Timestamp foundation
    'start_timestamp',                    # Absolute time for each data point (ISO format)
    
    # Segment-level integration (scipy trapz)
    'capacity_ah',                  # Cumulative capacity within segment (starts at 0)
    'energy_wh',                    # Cumulative energy within segment (starts at 0)
    
    # File-level experimental context
    'capacity_cumulative_ah',       # Running total across all segments in file
    'energy_cumulative_wh',         # Running total across all segments in file
    
    # Directional tracking (charge/discharge separation)
    'charge_cumulative_ah',         # Running total of positive segments only
    'discharge_cumulative_ah',      # Running total of negative segments only
    'energy_charge_cumulative_wh',  # Running total of positive energy segments
    'energy_discharge_cumulative_wh', # Running total of negative energy segments
    
    # Absolute activity tracking
    'capacity_absolute_cumulative_ah', # Sum of |segment_capacity| (total activity)
    'energy_absolute_cumulative_wh'    # Sum of |segment_energy| (total activity)
]
```

## Parsing Implementation

### Enhanced add_computed_columns Method
```python
def add_computed_columns(self, df: pl.DataFrame) -> pl.DataFrame:
    """Add physics-based capacity and energy integration."""
    try:
        computed_exprs = []
        
        # Timestamp calculation (absolute time)
        if self.acquisition_datetime and 'time_s' in df.columns:
            computed_exprs.append(
                (pl.lit(self.acquisition_datetime) + pl.duration(seconds=pl.col('time_s')))
                .alias('timestamp')
            )
        
        # Power calculation (for energy integration)
        if 'potential_v' in df.columns and 'current_a' in df.columns:
            computed_exprs.append(
                (pl.col('potential_v') * pl.col('current_a')).alias('power_w')
            )
        
        # Impedance calculations (existing)
        if 'impedance_real_ohm' in df.columns and 'impedance_imag_ohm' in df.columns:
            computed_exprs.append(
                (pl.col('impedance_real_ohm').pow(2) + pl.col('impedance_imag_ohm').pow(2))
                .sqrt().alias('impedance_mag_ohm')
            )
            computed_exprs.append(
                (pl.arctan2(pl.col('impedance_imag_ohm'), pl.col('impedance_real_ohm')) * 180 / 3.14159265359)
                .alias('impedance_phase_deg')
            )
        
        # Apply basic computations
        if computed_exprs:
            df = df.with_columns(computed_exprs)
        
        # Physics-based integration (requires segment grouping)
        if all(col in df.columns for col in ['time_s', 'current_a', 'segment_number']):
            df = self._add_integration_columns(df)
        
        return df
        
    except Exception as e:
        print(f"Error in add_computed_columns: {e}")
        return df

def _add_integration_columns(self, df: pl.DataFrame) -> pl.DataFrame:
    """Add segment-based integration using scipy trapz."""
    
    def integrate_segment_capacity(segment_df):
        """Integrate capacity for one segment using scipy trapezoidal rule."""
        time_vals = segment_df['time_s'].to_numpy()
        current_vals = segment_df['current_a'].to_numpy()
        
        if len(time_vals) < 2:
            return segment_df.with_columns([
                pl.lit(0.0).alias('capacity_ah')
            ])
        
        # Scipy trapezoidal integration - cumulative within segment
        cumulative_capacity = scipy.integrate.cumtrapz(
            current_vals, time_vals, initial=0
        ) / 3600.0  # Convert As to Ah
        
        return segment_df.with_columns([
            pl.Series('capacity_ah', cumulative_capacity)
        ])
    
    def integrate_segment_energy(segment_df):
        """Integrate energy for one segment using scipy trapezoidal rule."""
        if 'power_w' not in segment_df.columns:
            return segment_df.with_columns([pl.lit(0.0).alias('energy_wh')])
            
        time_vals = segment_df['time_s'].to_numpy()
        power_vals = segment_df['power_w'].to_numpy()
        
        if len(time_vals) < 2:
            return segment_df.with_columns([
                pl.lit(0.0).alias('energy_wh')
            ])
        
        # Scipy trapezoidal integration - cumulative within segment
        cumulative_energy = scipy.integrate.cumtrapz(
            power_vals, time_vals, initial=0
        ) / 3600.0  # Convert Ws to Wh
        
        return segment_df.with_columns([
            pl.Series('energy_wh', cumulative_energy)
        ])
    
    # Apply segment-based integration
    df = df.group_by('segment_number', maintain_order=True).map_groups(integrate_segment_capacity)
    
    if 'power_w' in df.columns:
        df = df.group_by('segment_number', maintain_order=True).map_groups(integrate_segment_energy)
    
    # Add file-level cumulative tracking
    df = self._add_cumulative_tracking(df)
    
    return df

def _add_cumulative_tracking(self, df: pl.DataFrame) -> pl.DataFrame:
    """Add file-level cumulative capacity and energy tracking."""
    
    # Get final values from each segment for cumulative tracking
    segment_totals = df.group_by('segment_number').agg([
        pl.col('capacity_ah').max().alias('segment_capacity_final'),
        pl.col('energy_wh').max().alias('segment_energy_final') if 'energy_wh' in df.columns else pl.lit(0.0).alias('segment_energy_final')
    ]).sort('segment_number')
    
    # Calculate cumulative values
    segment_totals = segment_totals.with_columns([
        # Net cumulative
        pl.col('segment_capacity_final').cumsum().alias('capacity_cumulative_segment'),
        pl.col('segment_energy_final').cumsum().alias('energy_cumulative_segment'),
        
        # Charge cumulative (positive only)
        pl.col('segment_capacity_final').clip(lower_bound=0).cumsum().alias('charge_cumulative_segment'),
        pl.col('segment_energy_final').clip(lower_bound=0).cumsum().alias('energy_charge_cumulative_segment'),
        
        # Discharge cumulative (negative only)
        pl.col('segment_capacity_final').clip(upper_bound=0).cumsum().alias('discharge_cumulative_segment'),
        pl.col('segment_energy_final').clip(upper_bound=0).cumsum().alias('energy_discharge_cumulative_segment'),
        
        # Absolute cumulative
        pl.col('segment_capacity_final').abs().cumsum().alias('capacity_absolute_cumulative_segment'),
        pl.col('segment_energy_final').abs().cumsum().alias('energy_absolute_cumulative_segment')
    ])
    
    # Join back to main dataframe
    df = df.join(segment_totals, on='segment_number', how='left')
    
    # Convert to point-level cumulative (interpolate within segments)
    df = df.with_columns([
        # File-level cumulative = previous segments + current segment progress
        (pl.col('capacity_cumulative_segment') - pl.col('segment_capacity_final') + pl.col('capacity_ah')).alias('capacity_cumulative_ah'),
        (pl.col('energy_cumulative_segment') - pl.col('segment_energy_final') + pl.col('energy_wh')).alias('energy_cumulative_wh'),
        
        # Charge/discharge tracking
        (pl.col('charge_cumulative_segment') + pl.col('capacity_ah').clip(lower_bound=0)).alias('charge_cumulative_ah'),
        (pl.col('discharge_cumulative_segment') + pl.col('capacity_ah').clip(upper_bound=0)).alias('discharge_cumulative_ah'),
        
        # Energy equivalents
        (pl.col('energy_charge_cumulative_segment') + pl.col('energy_wh').clip(lower_bound=0)).alias('energy_charge_cumulative_wh'),
        (pl.col('energy_discharge_cumulative_segment') + pl.col('energy_wh').clip(upper_bound=0)).alias('energy_discharge_cumulative_wh'),
        
        # Absolute tracking
        (pl.col('capacity_absolute_cumulative_segment') + pl.col('capacity_ah').abs()).alias('capacity_absolute_cumulative_ah'),
        (pl.col('energy_absolute_cumulative_segment') + pl.col('energy_wh').abs()).alias('energy_absolute_cumulative_wh')
    ])
    
    # Clean up temporary columns
    df = df.drop([col for col in df.columns if col.endswith('_segment')])
    
    return df
```

## Database Schema Extensions

### Segments Table - Universal Columns
```sql
-- Temporal foundation
ALTER TABLE segments ADD COLUMN start_timestamp TEXT; -- ISO format timestamp

-- Segment totals (final values from integration)
ALTER TABLE segments ADD COLUMN segment_capacity_ah REAL DEFAULT 0.0;
ALTER TABLE segments ADD COLUMN segment_energy_wh REAL DEFAULT 0.0;

-- Experimental context (cumulative boundaries)
ALTER TABLE segments ADD COLUMN start_capacity_cumulative_ah REAL DEFAULT 0.0;
ALTER TABLE segments ADD COLUMN end_capacity_cumulative_ah REAL DEFAULT 0.0;
ALTER TABLE segments ADD COLUMN start_energy_cumulative_wh REAL DEFAULT 0.0;
ALTER TABLE segments ADD COLUMN end_energy_cumulative_wh REAL DEFAULT 0.0;

-- Directional tracking (charge/discharge context)
ALTER TABLE segments ADD COLUMN start_charge_cumulative_ah REAL DEFAULT 0.0;
ALTER TABLE segments ADD COLUMN end_charge_cumulative_ah REAL DEFAULT 0.0;
ALTER TABLE segments ADD COLUMN start_discharge_cumulative_ah REAL DEFAULT 0.0;
ALTER TABLE segments ADD COLUMN end_discharge_cumulative_ah REAL DEFAULT 0.0;

-- Energy directional tracking
ALTER TABLE segments ADD COLUMN start_energy_charge_cumulative_wh REAL DEFAULT 0.0;
ALTER TABLE segments ADD COLUMN end_energy_charge_cumulative_wh REAL DEFAULT 0.0;
ALTER TABLE segments ADD COLUMN start_energy_discharge_cumulative_wh REAL DEFAULT 0.0;
ALTER TABLE segments ADD COLUMN end_energy_discharge_cumulative_wh REAL DEFAULT 0.0;

-- Absolute activity tracking
ALTER TABLE segments ADD COLUMN start_capacity_absolute_cumulative_ah REAL DEFAULT 0.0;
ALTER TABLE segments ADD COLUMN end_capacity_absolute_cumulative_ah REAL DEFAULT 0.0;
ALTER TABLE segments ADD COLUMN start_energy_absolute_cumulative_wh REAL DEFAULT 0.0;
ALTER TABLE segments ADD COLUMN end_energy_absolute_cumulative_wh REAL DEFAULT 0.0;
```

### Segment Extraction Logic
```python
def extract_segment_universal_metrics(segment_df: pl.DataFrame) -> dict:
    """Extract universal metrics for segment database storage."""
    
    # Basic segment metrics
    segment_capacity = segment_df['capacity_ah'].max()  # Final capacity value
    segment_energy = segment_df['energy_wh'].max() if 'energy_wh' in segment_df.columns else 0.0
    
    # Timestamp boundaries
    start_timestamp = segment_df['timestamp'].min()  # First timestamp in segment
    
    # Cumulative boundaries (experimental context)
    start_capacity_cumulative = segment_df['capacity_cumulative_ah'].min()
    end_capacity_cumulative = segment_df['capacity_cumulative_ah'].max()
    start_energy_cumulative = segment_df['energy_cumulative_wh'].min()
    end_energy_cumulative = segment_df['energy_cumulative_wh'].max()
    
    # Charge/discharge boundaries
    start_charge_cumulative = segment_df['charge_cumulative_ah'].min()
    end_charge_cumulative = segment_df['charge_cumulative_ah'].max()
    start_discharge_cumulative = segment_df['discharge_cumulative_ah'].min()
    end_discharge_cumulative = segment_df['discharge_cumulative_ah'].max()
    
    return {
        # Core segment metrics
        'start_timestamp': start_timestamp.isoformat(),
        'segment_capacity_ah': segment_capacity,
        'segment_energy_wh': segment_energy,
        
        # Experimental context
        'start_capacity_cumulative_ah': start_capacity_cumulative,
        'end_capacity_cumulative_ah': end_capacity_cumulative,
        'start_energy_cumulative_wh': start_energy_cumulative,
        'end_energy_cumulative_wh': end_energy_cumulative,
        
        # Directional context
        'start_charge_cumulative_ah': start_charge_cumulative,
        'end_charge_cumulative_ah': end_charge_cumulative,
        'start_discharge_cumulative_ah': start_discharge_cumulative,
        'end_discharge_cumulative_ah': end_discharge_cumulative,
        
        # Energy directional context
        'start_energy_charge_cumulative_wh': segment_df['energy_charge_cumulative_wh'].min(),
        'end_energy_charge_cumulative_wh': segment_df['energy_charge_cumulative_wh'].max(),
        'start_energy_discharge_cumulative_wh': segment_df['energy_discharge_cumulative_wh'].min(),
        'end_energy_discharge_cumulative_wh': segment_df['energy_discharge_cumulative_wh'].max(),
        
        # Absolute activity context
        'start_capacity_absolute_cumulative_ah': segment_df['capacity_absolute_cumulative_ah'].min(),
        'end_capacity_absolute_cumulative_ah': segment_df['capacity_absolute_cumulative_ah'].max(),
        'start_energy_absolute_cumulative_wh': segment_df['energy_absolute_cumulative_wh'].min(),
        'end_energy_absolute_cumulative_wh': segment_df['energy_absolute_cumulative_wh'].max()
    }
```

## Multi-File Experimental Continuity

### File-Level Independence
Each file processes independently with its own cumulative tracking:

**File 1 (charge.par):**
```
Segment 1: capacity_ah = 0.000 → 0.050, cumulative = 0.000 → 0.050
Segment 2: capacity_ah = 0.000 → 0.030, cumulative = 0.050 → 0.080
```

**File 2 (discharge.par):**
```
Segment 3: capacity_ah = 0.000 → -0.045, cumulative = 0.000 → -0.045
Segment 4: capacity_ah = 0.000 → -0.025, cumulative = -0.045 → -0.070
```

### Cross-File Analysis
Group-level analysis uses `start_timestamp` for experimental timeline:

```python
# Query segments by actual experimental time
segments = query_segments_by_timestamp("2025-08-20T09:00:00", "2025-08-20T11:00:00")

# Results span multiple files but maintain temporal order:
[
    {"file": "charge.par", "start_timestamp": "09:00:00", "segment_capacity_ah": 0.050},
    {"file": "charge.par", "start_timestamp": "09:30:00", "segment_capacity_ah": 0.030},
    {"file": "discharge.par", "start_timestamp": "10:00:00", "segment_capacity_ah": -0.045},
    {"file": "discharge.par", "start_timestamp": "10:30:00", "segment_capacity_ah": -0.025}
]

# Analysis: net_capacity = 0.050 + 0.030 - 0.045 - 0.025 = 0.010 Ah
# Analysis: efficiency = |discharge| / charge = 0.070 / 0.080 = 87.5%
```

## Benefits and Applications

### Technical Advantages
1. **Physics-Based Integration**: Scipy trapezoidal rule handles variable time intervals accurately
2. **Segment Isolation**: Each segment starts from zero, enabling independent analysis
3. **Experimental Context**: Cumulative tracking maintains experimental timeline
4. **Multi-File Continuity**: Timestamp-based analysis across fragmented experiments
5. **Performance**: Integration done once during parsing, stored in parquet and database

### Analysis Capabilities

#### Efficiency Studies
```python
# Coulombic efficiency per segment
efficiency = abs(segment_capacity_discharge) / segment_capacity_charge

# Energy efficiency
energy_efficiency = abs(segment_energy_discharge) / segment_energy_charge
```

#### Aging Analysis
```python
# Capacity fade over time using timestamps
capacity_trend = segments.group_by(timestamp.date()).agg(
    pl.col('segment_capacity_ah').sum()
)
```

#### Cross-Experiment Correlation
```python
# Compare multiple cells tested at same time
temperature_effect = segments.filter(
    pl.col('start_timestamp').is_between("09:00", "11:00")
).group_by('cell_id').agg(pl.col('segment_capacity_ah').mean())
```

#### Activity Analysis
```python
# Total electrochemical activity regardless of direction
total_activity = segments['end_capacity_absolute_cumulative_ah'].max()

# Activity rate (how hard was the electrode worked)
activity_rate = total_activity / experiment_duration_hours
```

### Future Extensions
1. **State-of-Charge Tracking**: Use cumulative capacity for SOC calculations
2. **Degradation Mechanisms**: Correlate absolute activity with aging
3. **Temperature Compensation**: Timestamp-based temperature correlation
4. **DOE Analysis**: Statistical analysis of capacity vs experimental conditions
5. **Real-time Monitoring**: Live cumulative tracking for ongoing experiments

## Implementation Priority

### Phase 1: Core Integration (IMMEDIATE)
1. Update universal schema with integration columns
2. Implement segment-based scipy integration in `add_computed_columns`
3. Add cumulative tracking logic
4. Test with single VersaStudio files

### Phase 2: Database Storage (NEXT)
1. Extend segments table schema with universal columns
2. Update segment extraction logic
3. Test database storage and retrieval
4. Validate cumulative boundary calculations

### Phase 3: Multi-File Testing (FOLLOWING)
1. Test with fragmented GITT experiments
2. Validate timestamp continuity across files
3. Test cross-file temporal queries
4. Performance optimization for large datasets

### Phase 4: Analysis Integration (FINAL)
1. Update group analytics to use new columns
2. Implement efficiency and aging analysis functions
3. Add timestamp-based filtering to UI
4. Create analysis templates for common calculations