# DataFrame Column Documentation - Registry Analysis Functions

**Date**: August 25, 2025  
**Status**: All analysis functions converted to return standardized DataFrames

## Analysis Function DataFrame Outputs

All analysis functions now return `pd.DataFrame` with consistent structure:
- **Core segment columns**: From query_engine (`segments` parameter)
- **Analysis-specific columns**: Unique calculations per analysis type
- **Standard columns**: Required by registry (`analysis_type`, `quality_score`)

---

## 1. resistance_analysis_function()

**Returns**: DataFrame with resistance analysis for galvanostatic segments

### Core Columns (from segments):
- `segment_id` (renamed from `id`)
- `start_time_s`, `duration_s`, `start_potential_v`, `end_potential_v`
- `start_current_a`, `end_current_a`, `capacity_ah`, `energy_wh`
- `fundamental_technique`, `point_count`, `analysis_results`

### Analysis-Specific Columns:
- `ir_immediate_ohm` - Immediate resistance
- `ir_10s_ohm` - 10-second resistance (if requested)
- `ir_30s_ohm` - 30-second resistance (if requested)
- `baseline_voltage_v` - Baseline voltage from analysis
- `average_current_a` - Average current during segment
- `calculation_quality` - 'good' or 'invalid'

### Standard Columns:
- `analysis_type` = 'resistance_analysis'
- `quality_score` - 1.0 for good, 0.0 for invalid

### Summary Columns:
- `ir_immediate_ohm_mean`, `ir_immediate_ohm_std` - Statistical summaries
- `insight_resistance_level`, `insight_average_resistance`, `insight_data_quality` - Electrochemical insights

---

## 2. kinetics_analysis_function()

**Returns**: DataFrame with relaxation kinetics for REST segments

### Core Columns: Same as above

### Analysis-Specific Columns:
- `v_equilibrium_v` - Equilibrium voltage (exponential fit)
- `tau_s` - Time constant (exponential fit)
- `v_infinity_v` - Infinite time voltage (sqrt(t) fit)
- `a_coefficient` - A coefficient (sqrt(t) fit)
- `r_squared` - Goodness of fit
- `fit_type` - 'exponential', 'sqrt_t', or determined by auto_best
- `voltage_recovery_v` - End voltage - start voltage
- `fit_quality` - 'good' or 'poor'

### Standard Columns:
- `analysis_type` = 'kinetics_analysis'
- `quality_score` - R² value

### Additional Columns:
- `fit_type_used` - Selected fit type
- `min_r_squared_threshold` - Quality threshold used
- `is_high_quality` - Boolean, meets R² threshold
- `summary_*` - Statistical summaries (total_segments, fit_success_rate, r_squared_stats, etc.)
- `insight_*` - Electrochemical insights (fit_quality, relaxation_speed, voltage_recovery, etc.)

---

## 3. basic_statistics_analysis()

**Returns**: DataFrame with statistical summary of all segments

### Core Columns: Same as above

### Analysis-Specific Columns (per metric):
For each metric in settings (default: duration_s, start_potential_v, end_potential_v):
- `{metric}_mean`, `{metric}_std`, `{metric}_min`, `{metric}_max`
- `{metric}_median`, `{metric}_count`

### Technique/Group Columns:
- `technique_count_{technique}` - Count per technique
- `group_count_{group}` - Count per group (if available)

### Time Analysis Columns:
- `time_range_hours` - Total time span
- `first_segment_time`, `last_segment_time` - Time boundaries

### Standard Columns:
- `analysis_type` = 'basic_statistics'
- `quality_score` = 1.0 (always succeeds)
- `total_segments_analyzed`, `metrics_analyzed`

---

## 4. equilibrium_analysis_function()

**Returns**: DataFrame with equilibrium voltage analysis

### Core Columns: Same as above

### Analysis-Specific Columns:
- `equilibrium_voltage_v` - Equilibrium voltage (from JSON or calculated)
- `is_stable` - Stability flag
- `drift_rate_mv_min` - Voltage drift rate
- `voltage_change_v` - End - start voltage
- `meets_duration_criteria`, `meets_drift_criteria` - Quality checks
- `equilibrium_quality` - 'good' or 'poor'

### Standard Columns:
- `analysis_type` = 'equilibrium_analysis'
- `quality_score` - 1.0 for good, 0.0 for poor

### Summary/Insight Columns:
- `summary_*` - Statistical summaries (quality_ratio, equilibrium_voltage_stats, drift_rate_stats, etc.)
- `insight_*` - Electrochemical insights (data_quality, voltage_stability, drift_assessment, etc.)

---

## 5. current_decay_analysis_function()

**Returns**: DataFrame with current decay kinetics for potentiostatic segments

### Core Columns: Same as above

### Analysis-Specific Columns:
- `initial_current_a` - Starting current
- `decay_constant_s` - Decay time constant
- `steady_state_current_a` - Final current
- `r_squared` - Decay fit quality
- `decay_quality` - 'good' or 'poor'

### Standard Columns:
- `analysis_type` = 'current_decay_analysis'
- `quality_score` - 1.0 for good, 0.0 for poor

### Summary/Insight Columns:
- `summary_*` - Statistical summaries (fit_success_rate, decay_constant_stats, etc.)
- `insight_*` - Electrochemical insights (fit_quality, decay_speed, current_stability, etc.)

---

## 6. dqdv_analysis (placeholder)

**Returns**: DataFrame with placeholder error message

### Columns:
- `segment_id` = None
- `error_message` = "dQ/dV analysis not implemented yet..."
- `analysis_type` = 'dqdv_analysis'
- `placeholder` = True

---

## Usage for Registry Plot Configurations

**Standard columns available for ALL analyses**:
- **Time**: `start_time_s` (for TIME_SERIES plots)
- **Identification**: `segment_id`, `fundamental_technique` (for coloring/grouping)
- **Quality**: `quality_score`, `analysis_type`
- **Core metrics**: `duration_s`, `start_potential_v`, `end_potential_v`, `capacity_ah`, `energy_wh`

**Analysis-specific columns**: Each analysis has unique calculated columns for specialized plots

**Registry plot configs can now reference these exact column names consistently across all analyses.**