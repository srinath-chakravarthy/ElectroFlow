# Registry Configuration Report
**Generated**: 2025-08-25 06:15:53

## Summary

- **Total Analyses**: 6
- **Total Plots**: 12
- **Valid Plots**: 8
- **Invalid Plots**: 4

## basic_statistics

**Available Columns** (32):
```
  analysis_type
  duration_s
  duration_s_count
  duration_s_max
  duration_s_mean
  duration_s_median
  duration_s_min
  duration_s_std
  end_potential_v
  end_potential_v_count
  ... and 22 more
```

**Plot Configurations**:

- ✅ **Duration Distribution**

- ✅ **Voltage Range**

## resistance_analysis

**Available Columns** (15):
```
  analysis_results
  analysis_type
  average_current_a
  baseline_voltage_v
  calculation_quality
  duration_s
  fundamental_technique
  insight_data_quality
  ir_10s_ohm
  ir_immediate_ohm
  ... and 5 more
```

**Plot Configurations**:

- ✅ **Resistance vs Time**

- ✅ **Resistance Distribution**

## kinetics_analysis

**Available Columns** (29):
```
  analysis_results
  analysis_type
  duration_s
  duration_s_analysis
  end_voltage_v
  fit_quality
  fit_type
  fit_type_used
  fundamental_technique
  insight_average_time_constant
  ... and 19 more
```

**Plot Configurations**:

- ✅ **Voltage Recovery vs Time**

- ✅ **Fit Quality Distribution**

## equilibrium_analysis

**Available Columns** (2):
```
  error_message
  segment_id
```

**Plot Configurations**:

- ❌ **Equilibrium Voltage vs Time**
  - Missing: ['start_time_s', 'equilibrium_voltage_v']
  - Suggestions: ['error_message', 'segment_id']

- ❌ **Drift Rate Distribution**
  - Missing: ['drift_rate_mv_min']

## current_decay_analysis

**Available Columns** (3):
```
  analysis_type
  error_message
  segment_id
```

**Plot Configurations**:

- ❌ **Decay Constant vs Time**
  - Missing: ['start_time_s', 'decay_constant_s']
  - Suggestions: ['analysis_type', 'error_message']

- ❌ **Current Drop Distribution**
  - Missing: ['current_decay_percent']

## dqdv_analysis

**Available Columns** (4):
```
  analysis_type
  error_message
  placeholder
  segment_id
```

**Plot Configurations**:

- ✅ **Placeholder Plot 1**

- ✅ **Placeholder Plot 2**
