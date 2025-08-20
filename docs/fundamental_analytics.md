# Fundamental Analytics Engine - Technical Documentation

## Overview

The Fundamental Analytics Engine is a comprehensive analysis system that automatically computes core metrics and advanced analytics for all electrochemical technique segments. It provides universal analysis capabilities that work across different instruments and technique types.

## Architecture

### Core Components

1. **`CoreMetricsCalculator`** - Universal metrics for all techniques
2. **`TechniqueAnalyzer`** - Advanced technique-specific analysis  
3. **`FundamentalAnalytics`** - Main orchestrator and coordinator
4. **Database Integration** - Enhanced schema with analytics storage

### Database Schema Extensions

New columns added to the `segments` table:

```sql
-- Core metrics (universal)
duration_s REAL NOT NULL,
start_potential_v REAL,
end_potential_v REAL, 
start_current_a REAL,
end_current_a REAL,
capacity_ah REAL,
energy_wh REAL,

-- Analysis management
analysis_status TEXT DEFAULT 'pending',
analysis_results TEXT DEFAULT '{}'
```

**Analysis Status Values:**
- `pending`: Not yet analyzed
- `completed`: Successfully analyzed (core + technique)
- `partial`: Core metrics only (technique analysis failed)
- `failed`: Analysis could not be completed

## Universal Core Metrics

Computed for **every segment** regardless of technique type:

### 1. Capacity Calculation
```python
capacity_ah = ∫I dt / 3600  # Trapezoidal integration, Ah
```
- Uses trapezoidal rule for numerical integration
- Handles NaN values gracefully
- Converts amp-seconds to amp-hours

### 2. Energy Calculation  
```python
energy_wh = ∫(V×I) dt / 3600  # Power integration, Wh
```
- Computes instantaneous power at each time point
- Integrates power over segment duration
- Converts watt-seconds to watt-hours

### 3. Duration and Boundary Values
- `duration_s`: Segment duration in seconds
- `start_potential_v`, `end_potential_v`: First and last voltage values
- `start_current_a`, `end_current_a`: First and last current values
- `point_count`: Number of data points in segment

## Technique-Specific Analysis

### Rest Phase Detection

Rest phases are identified using technique name keywords:
```python
REST_KEYWORDS = {
    'rest', 'relax', 'eis', 'open_circuit', 'ocp', 'ocv', 
    'impedance', 'pause', 'wait', 'delay'
}
```

### Context-Aware Decay Analysis

Rest phase analysis adapts based on the previous segment:

#### After Current Pulse → Voltage Decay Analysis
```python
# Exponential fitting: V(t) = V∞ + A·exp(-t/τ)
{
    "analysis_type": "voltage_decay",
    "voltage_infinity": 3.245,      # Equilibrium voltage (V)
    "voltage_amplitude": -0.089,    # Initial voltage drop (V)  
    "time_constant_s": 45.2,        # Time constant τ (s)
    "r_squared": 0.94,              # Fit quality
    "rmse": 0.002,                  # Root mean square error
    "param_errors": {...}           # Parameter uncertainties
}
```

#### After Voltage Pulse → Current Decay Analysis
```python
# Exponential fitting: I(t) = I∞ + A·exp(-t/τ)
{
    "analysis_type": "current_decay",
    "current_infinity": 0.000001,   # Final current (A)
    "current_amplitude": 0.050,     # Initial current step (A)
    "time_constant_s": 12.8,        # RC time constant (s)
    "r_squared": 0.97,
    "rmse": 0.000005
}
```

### Current Pulse Analysis

For active current application phases:

```python
{
    "analysis_type": "current_pulse",
    "ir_immediate_ohm": 0.045,      # Ohmic resistance (Ω)
    "ir_10s_ohm": 0.052,            # Kinetics + ohmic (Ω)
    "ir_30s_ohm": 0.058,            # Diffusion + kinetics + ohmic (Ω)
    "baseline_voltage_v": 3.24,     # Pre-pulse voltage (V)
    "average_current_a": 0.100,     # Applied current (A)
    "pulse_duration_s": 120.0       # Pulse duration (s)
}
```

**Resistance Calculation Points:**
- **IR Immediate**: ΔV at first data point (pure ohmic)
- **IR @ 10s**: ΔV after kinetics settling
- **IR @ 30s**: ΔV after diffusion effects

### General Technique Analysis

For techniques that don't match specific patterns:

```python
{
    "analysis_type": "general",
    "voltage_mean_v": 3.25,
    "voltage_std_v": 0.15,
    "voltage_range_v": 0.89,
    "current_mean_a": 0.001,
    "current_std_a": 0.025,
    "current_range_a": 0.195
}
```

## Curve Fitting Implementation

### Exponential Decay Fitting

Uses SciPy's `curve_fit` with bounded optimization:

```python
def exp_decay(t, y_inf, A, tau):
    return y_inf + A * np.exp(-t / max(tau, 1e-6))

# Bounds to ensure physical meaningful parameters
bounds = (
    [-np.inf, -np.inf, 1e-3],        # Lower bounds
    [np.inf, np.inf, t_max * 10]     # Upper bounds  
)
```

### Quality Metrics

**R² Coefficient of Determination:**
```python
r_squared = 1 - (SS_res / SS_tot)
```

**Root Mean Square Error:**
```python
rmse = √(mean((y_actual - y_fit)²))
```

**Parameter Uncertainties:**
- Extracted from covariance matrix diagonal
- Provides error estimates for fit parameters

## API Methods

### File Processing Integration

Analytics are automatically computed during file processing:

```python
# In _generate_segments()
analytics_results = self.analytics_engine.analyze_all_segments(
    data_file.universal_data, segments_info
)
```

### Reanalysis Operations

```python
# Reanalyze specific file
result = api.reanalyze_segments(file_id, force_recompute=True)

# Get analytics summary  
summary = api.get_analytics_summary(cell_name)

# Get segments by status
failed_segments = api.get_segments_by_analysis_status('failed')
```

### Analytics Summary

Provides comprehensive statistics:

```python
{
    "total_segments": 45,
    "success_rate": 0.89,
    "total_capacity_ah": 2.456,
    "total_energy_wh": 8.234,
    "total_duration_s": 125400,
    "status_distribution": {
        "completed": 40,
        "partial": 3, 
        "failed": 2
    },
    "technique_distribution": {
        "voltage_decay": 15,
        "current_pulse": 12,
        "current_decay": 8,
        "general": 10
    }
}
```

## Error Handling

### Graceful Degradation
- Core metrics always attempted, even if technique analysis fails
- Partial success states allow recovery from technique-specific errors
- Failed analysis stored with error messages for debugging

### Automatic Recovery
- Database migration handles schema updates automatically
- Missing columns added transparently to existing databases
- Reanalysis system allows updating with improved algorithms

## Performance Considerations

### Memory Efficiency
- Segment-based processing avoids loading entire files into memory
- Numpy operations used for numerical computations
- JSON storage for complex analysis results

### Processing Speed  
- Analytics computed once during file processing
- Reanalysis only processes segments with specific statuses
- Database indexing on analysis_status for efficient queries

### Quality Assurance
- Minimum data point requirements for curve fitting (10+ points)
- Physical bounds on fitting parameters
- Quality metrics stored with all analyses
- Error logging for failed computations

## Future Extensions

### Additional Techniques
- **CV Analysis**: Peak detection, scan rate effects, capacitance
- **EIS Analysis**: Basic validation, export preparation
- **Advanced Fitting**: Multi-exponential, Warburg diffusion models

### Machine Learning Integration
- Pattern recognition for technique classification
- Anomaly detection for data quality assessment
- Predictive modeling for battery health estimation

The Fundamental Analytics Engine provides a solid foundation for comprehensive electrochemical data analysis while maintaining flexibility for future enhancements and technique-specific extensions.