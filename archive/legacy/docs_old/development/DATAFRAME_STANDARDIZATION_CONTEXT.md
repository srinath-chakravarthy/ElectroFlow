# DataFrame Standardization Context - Registry Plot Fix

**Date**: August 25, 2025  
**Issue**: Registry-based plotting system needs complete plot configurations  
**Status**: Implementing DataFrame standardization as prerequisite for plot configs

## Core Problem Context

**Registry Architecture**: 
- ✅ Analysis functions exist and return DataFrames
- ✅ Registry lists available plot types (`TIME_SERIES`, `XY_PLOT`, etc.)  
- ❌ Registry plot configurations are EMPTY (`plot_config={}` for all analyses)
- ❌ plotting.py can't be purely config-driven without plot configs

**Plot Configuration Requirements**:
```python
# plotting.py needs from registry:
plot_config = {
    "time_series": {
        "plot_name": "Resistance vs Time",
        "x": "start_time_s", 
        "y": "ir_immediate_ohm",
        "color": "technique"
    }
}
```

**Current DataFrame Problem**: Analysis functions return inconsistent columns
- **resistance_analysis**: Returns `segment_id`, `ir_immediate_ohm`, etc. (missing `start_time_s` for TIME_SERIES plots)
- **kinetics_analysis**: Returns `segment_id`, `tau_s`, etc. (missing core columns)
- **basic_statistics**: Returns segments as dict (not DataFrame format)

## Solution: DataFrame Standardization

**Objective**: Every analysis function returns DataFrame with:
- **Core segment columns**: `segment_id`, `start_time_s`, `duration_s`, `start_potential_v`, `end_potential_v`, `technique`, `capacity_ah`, `energy_wh`, `point_count` (same for all analyses)
- **Analysis-specific columns**: `ir_immediate_ohm`, `tau_s`, `r_squared`, etc. (unique per analysis)

**Implementation Strategy**: 
1. **Use existing infrastructure**: query_engine already provides ALL core columns in `segments` parameter
2. **Merge approach**: `pd.merge(pd.DataFrame(segments), pd.DataFrame(analysis_data), on='segment_id')`
3. **Benefits**: Future-proof, maintainable, no hardcoded column lists

**Change per analysis function**:
```python
# Current:
df = pd.DataFrame(analysis_specific_data)  # Missing core columns

# New:  
core_df = pd.DataFrame(segments)  # All core columns from query_engine
analysis_df = pd.DataFrame(analysis_specific_data)  # Analysis columns
df = pd.merge(core_df, analysis_df, on='segment_id')  # Combined DataFrame
return df
```

## Analysis Functions to Update

1. **resistance_analysis_function** (HIGH PRIORITY - fix first)
2. **kinetics_analysis_function**
3. **basic_statistics_analysis**  
4. **equilibrium_analysis_function**
5. **current_decay_analysis_function**
6. **dqdv_analysis** (placeholder)

## Next Steps After DataFrame Standardization

1. **Document standardized DataFrame columns** for each analysis type
2. **Create complete registry plot configurations** referencing standardized columns
3. **Verify plotting.py** uses only registry configs (no hardcoded analysis logic)

## Success Criteria

- ✅ Every analysis returns DataFrame with consistent core columns
- ✅ Registry plot configs reference actual DataFrame columns  
- ✅ plotting.py is purely config-driven from registry
- ✅ Adding new analysis = update registry config only (no UI changes)

**Context Preservation**: This standardization enables the registry-driven plotting system to work properly by ensuring consistent DataFrame column access across all analysis types.