"""
Fundamental analytics engine for battery data analysis.
Implements CC, pulse, rest, CV, and basic EIS analysis.
"""

from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import polars as pl
from scipy.optimize import curve_fit
from scipy.stats import linregress
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore', category=RuntimeWarning)


@dataclass
class AnalysisResult:
    """Container for analysis results."""
    technique: str
    action_id: int
    results: Dict[str, Any]
    quality_metrics: Dict[str, float]
    fitted_data: Optional[Dict[str, List[float]]] = None


class FundamentalAnalytics:
    """
    Fundamental analytics engine for electrochemical data.
    
    Implements technique-specific analysis:
    - CC: Capacity, energy, efficiency
    - Pulse: Resistance, voltage drop
    - Rest: Exponential curve fitting
    - CV: Peak detection, capacitance
    - EIS: Basic impedance analysis
    """

    def __init__(self):
        self.min_points_for_fitting = 10
        self.pulse_max_duration = 60.0  # seconds
        self.rest_min_duration = 5.0   # seconds

    def analyze_datafile(self, universal_data: pl.DataFrame) -> Dict[str, AnalysisResult]:
        """
        Analyze all techniques in a universal schema DataFrame.
        
        Args:
            universal_data: DataFrame with universal 31-column schema
            
        Returns:
            Dictionary of ActionId -> AnalysisResult
        """
        results = {}
        
        if universal_data.is_empty():
            return results
            
        # Group by technique_id (ActionId) for individual analysis
        for action_id in universal_data.get_column('technique_id').unique():
            if action_id is None:
                continue
                
            action_data = universal_data.filter(pl.col('technique_id') == action_id)
            if action_data.is_empty():
                continue
                
            # Get technique type
            fundamental_technique = action_data.get_column('fundamental_technique')[0]
            
            # Perform technique-specific analysis
            analysis_result = self._analyze_action(action_data, action_id, fundamental_technique)
            
            if analysis_result:
                results[str(action_id)] = analysis_result
                
        return results

    def _analyze_action(self, data: pl.DataFrame, action_id: int, 
                       technique: str) -> Optional[AnalysisResult]:
        """Analyze single action based on technique type."""
        if data.height < self.min_points_for_fitting:
            return None
            
        try:
            if technique == 'CC':
                return self._analyze_cc(data, action_id)
            elif technique == 'OCV':
                return self._analyze_rest(data, action_id)
            elif technique == 'CV':
                return self._analyze_cv(data, action_id)
            elif technique in ['GEIS', 'PEIS']:
                return self._analyze_eis(data, action_id)
            else:
                # Default to pulse/rest analysis based on duration
                duration = data.get_column('time_s').max() - data.get_column('time_s').min()
                if duration <= self.pulse_max_duration:
                    return self._analyze_pulse(data, action_id)
                else:
                    return self._analyze_rest(data, action_id)
                    
        except Exception as e:
            print(f"Warning: Analysis failed for action {action_id}: {e}")
            return None

    def _analyze_cc(self, data: pl.DataFrame, action_id: int) -> AnalysisResult:
        """Analyze constant current data."""
        time = data.get_column('time_s').to_numpy()
        voltage = data.get_column('potential_v').to_numpy()
        current = data.get_column('current_a').to_numpy()
        
        # Remove null values
        valid_mask = ~(np.isnan(time) | np.isnan(voltage) | np.isnan(current))
        time = time[valid_mask]
        voltage = voltage[valid_mask]
        current = current[valid_mask]
        
        if len(time) < 2:
            return AnalysisResult('CC', action_id, {}, {})
        
        # Calculate capacity (integrate current over time)
        dt = np.diff(time)
        current_avg = (current[1:] + current[:-1]) / 2
        capacity_c = np.sum(current_avg * dt)  # Coulombs
        capacity_ah = abs(capacity_c) / 3600  # Amp-hours
        
        # Calculate energy (integrate power over time)
        power = voltage * current
        power_avg = (power[1:] + power[:-1]) / 2
        energy_j = np.sum(power_avg * dt)  # Joules
        energy_wh = abs(energy_j) / 3600  # Watt-hours
        
        # Basic statistics
        avg_voltage = np.mean(voltage)
        avg_current = np.mean(current)
        avg_power = np.mean(power)
        
        # Current stability (coefficient of variation)
        current_stability = np.std(current) / abs(np.mean(current)) if np.mean(current) != 0 else 1.0
        
        results = {
            'capacity_ah': capacity_ah,
            'capacity_c': abs(capacity_c),
            'energy_wh': energy_wh,
            'energy_j': abs(energy_j),
            'avg_voltage_v': avg_voltage,
            'avg_current_a': avg_current,
            'avg_power_w': avg_power,
            'duration_s': time[-1] - time[0],
            'total_points': len(time)
        }
        
        quality_metrics = {
            'current_stability': current_stability,
            'data_completeness': len(time) / len(data)
        }
        
        return AnalysisResult('CC', action_id, results, quality_metrics)

    def _analyze_pulse(self, data: pl.DataFrame, action_id: int) -> AnalysisResult:
        """Analyze pulse data for resistance calculation."""
        time = data.get_column('time_s').to_numpy()
        voltage = data.get_column('potential_v').to_numpy()
        current = data.get_column('current_a').to_numpy()
        
        # Remove null values
        valid_mask = ~(np.isnan(time) | np.isnan(voltage) | np.isnan(current))
        time = time[valid_mask]
        voltage = voltage[valid_mask]
        current = current[valid_mask]
        
        if len(time) < 3:
            return AnalysisResult('PULSE', action_id, {}, {})
        
        # Find current step (largest current change)
        current_diff = np.abs(np.diff(current))
        if len(current_diff) == 0:
            return AnalysisResult('PULSE', action_id, {}, {})
            
        step_idx = np.argmax(current_diff)
        
        # Calculate resistance (ΔV/ΔI)
        if step_idx > 0 and step_idx < len(current) - 1:
            delta_i = current[step_idx + 1] - current[step_idx]
            delta_v = voltage[step_idx + 1] - voltage[step_idx]
            
            resistance = abs(delta_v / delta_i) if abs(delta_i) > 1e-9 else np.inf
            voltage_drop = abs(delta_v)
        else:
            resistance = np.inf
            voltage_drop = 0.0
        
        # Pulse duration and uniformity
        pulse_duration = time[-1] - time[0]
        current_uniformity = 1.0 - (np.std(current) / abs(np.mean(current))) if np.mean(current) != 0 else 0.0
        
        results = {
            'resistance_ohm': resistance,
            'voltage_drop_v': voltage_drop,
            'pulse_duration_s': pulse_duration,
            'current_change_a': abs(delta_i) if 'delta_i' in locals() else 0.0,
            'avg_current_a': np.mean(current),
            'total_points': len(time)
        }
        
        quality_metrics = {
            'current_uniformity': max(0.0, current_uniformity),
            'resistance_validity': 1.0 if resistance < 1000 else 0.0,
            'data_completeness': len(time) / len(data)
        }
        
        return AnalysisResult('PULSE', action_id, results, quality_metrics)

    def _analyze_rest(self, data: pl.DataFrame, action_id: int) -> AnalysisResult:
        """Analyze rest phase with exponential curve fitting."""
        time = data.get_column('time_s').to_numpy()
        voltage = data.get_column('potential_v').to_numpy()
        
        # Remove null values and sort by time
        valid_mask = ~(np.isnan(time) | np.isnan(voltage))
        time = time[valid_mask]
        voltage = voltage[valid_mask]
        
        if len(time) < self.min_points_for_fitting:
            return AnalysisResult('REST', action_id, {}, {})
        
        # Sort by time
        sort_idx = np.argsort(time)
        time = time[sort_idx]
        voltage = voltage[sort_idx]
        
        # Normalize time to start at 0
        time_norm = time - time[0]
        
        # Exponential decay fitting: V(t) = V_eq + V_drop * exp(-t/tau)
        def exponential_decay(t, v_eq, v_drop, tau):
            return v_eq + v_drop * np.exp(-t / tau)
        
        try:
            # Initial guess
            v_eq_guess = voltage[-1]  # Final voltage as equilibrium
            v_drop_guess = voltage[0] - voltage[-1]  # Initial drop
            tau_guess = time_norm[-1] / 3  # Time constant guess
            
            # Fit curve
            popt, pcov = curve_fit(
                exponential_decay, 
                time_norm, 
                voltage,
                p0=[v_eq_guess, v_drop_guess, tau_guess],
                maxfev=2000
            )
            
            v_eq, v_drop, tau = popt
            
            # Calculate R-squared
            fitted_values = exponential_decay(time_norm, *popt)
            ss_res = np.sum((voltage - fitted_values) ** 2)
            ss_tot = np.sum((voltage - np.mean(voltage)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
            
            # RMSE
            rmse = np.sqrt(np.mean((voltage - fitted_values) ** 2))
            
            # Store fitted curve for plotting
            fitted_data = {
                'time_s': time_norm.tolist(),
                'voltage_fitted_v': fitted_values.tolist(),
                'voltage_measured_v': voltage.tolist(),
                'residuals_v': (voltage - fitted_values).tolist()
            }
            
            fit_success = True
            
        except Exception as e:
            # Fallback to linear fit if exponential fails
            if len(time_norm) >= 2:
                slope, intercept, r_value, _, _ = linregress(time_norm, voltage)
                v_eq = intercept + slope * time_norm[-1]
                v_drop = voltage[0] - v_eq
                tau = time_norm[-1] / 2  # Rough estimate
                r_squared = r_value ** 2
                rmse = np.sqrt(np.mean((voltage - (intercept + slope * time_norm)) ** 2))
                fitted_data = None
            else:
                v_eq = np.mean(voltage)
                v_drop = 0.0
                tau = 0.0
                r_squared = 0.0
                rmse = np.std(voltage)
                fitted_data = None
            
            fit_success = False
        
        results = {
            'v_equilibrium_v': v_eq,
            'v_drop_v': abs(v_drop),
            'time_constant_s': abs(tau),
            'duration_s': time_norm[-1],
            'voltage_range_v': voltage.max() - voltage.min(),
            'fitting_type': 'exponential' if fit_success else 'linear',
            'total_points': len(time)
        }
        
        quality_metrics = {
            'r_squared': max(0.0, r_squared),
            'fit_error_rmse': rmse,
            'fit_success': 1.0 if fit_success else 0.0,
            'data_completeness': len(time) / len(data)
        }
        
        return AnalysisResult('REST', action_id, results, quality_metrics, fitted_data)

    def _analyze_cv(self, data: pl.DataFrame, action_id: int) -> AnalysisResult:
        """Analyze cyclic voltammetry data."""
        voltage = data.get_column('potential_v').to_numpy()
        current = data.get_column('current_a').to_numpy()
        
        # Remove null values
        valid_mask = ~(np.isnan(voltage) | np.isnan(current))
        voltage = voltage[valid_mask]
        current = current[valid_mask]
        
        if len(voltage) < 10:
            return AnalysisResult('CV', action_id, {}, {})
        
        # Basic CV analysis
        voltage_range = voltage.max() - voltage.min()
        current_range = current.max() - current.min()
        
        # Simple peak detection (find local maxima/minima)
        try:
            from scipy.signal import find_peaks
        except ImportError:
            # Fallback if scipy not available
            def find_peaks(data, **kwargs):
                return [], {}
        
        # Find anodic peaks (positive current)
        anodic_peaks, _ = find_peaks(current, height=np.mean(current) + np.std(current))
        # Find cathodic peaks (negative current)
        cathodic_peaks, _ = find_peaks(-current, height=-np.mean(current) + np.std(current))
        
        # Estimate capacitance from scan rate and current
        if len(voltage) > 1:
            scan_rate = np.mean(np.abs(np.diff(voltage))) / np.mean(np.diff(data.get_column('time_s').to_numpy()[:len(voltage)]))
            capacitance = current_range / (2 * scan_rate) if scan_rate > 0 else 0.0
        else:
            scan_rate = 0.0
            capacitance = 0.0
        
        results = {
            'voltage_range_v': voltage_range,
            'current_range_a': current_range,
            'scan_rate_v_per_s': scan_rate,
            'capacitance_f': capacitance,
            'anodic_peaks': len(anodic_peaks),
            'cathodic_peaks': len(cathodic_peaks),
            'total_points': len(voltage)
        }
        
        quality_metrics = {
            'peak_symmetry': abs(len(anodic_peaks) - len(cathodic_peaks)) / max(1, len(anodic_peaks) + len(cathodic_peaks)),
            'data_completeness': len(voltage) / len(data)
        }
        
        return AnalysisResult('CV', action_id, results, quality_metrics)

    def _analyze_eis(self, data: pl.DataFrame, action_id: int) -> AnalysisResult:
        """Analyze EIS data for basic impedance characteristics."""
        frequency = data.get_column('frequency_hz').to_numpy()
        z_real = data.get_column('impedance_real_ohm').to_numpy()
        z_imag = data.get_column('impedance_imag_ohm').to_numpy()
        
        # Remove null values
        valid_mask = ~(np.isnan(frequency) | np.isnan(z_real) | np.isnan(z_imag))
        frequency = frequency[valid_mask]
        z_real = z_real[valid_mask]
        z_imag = z_imag[valid_mask]
        
        if len(frequency) < 3:
            return AnalysisResult('EIS', action_id, {}, {})
        
        # Calculate impedance magnitude and phase
        z_mag = np.sqrt(z_real**2 + z_imag**2)
        z_phase = np.degrees(np.arctan2(z_imag, z_real))
        
        # Basic EIS metrics
        freq_range = frequency.max() - frequency.min()
        z_mag_range = z_mag.max() - z_mag.min()
        
        # Estimate series resistance (high frequency limit)
        high_freq_idx = np.argmax(frequency)
        series_resistance = z_real[high_freq_idx] if len(z_real) > 0 else 0.0
        
        # Estimate charge transfer resistance (low frequency limit)
        low_freq_idx = np.argmin(frequency)
        charge_transfer_resistance = z_real[low_freq_idx] - series_resistance
        
        results = {
            'frequency_range_hz': freq_range,
            'frequency_min_hz': frequency.min(),
            'frequency_max_hz': frequency.max(),
            'impedance_mag_range_ohm': z_mag_range,
            'series_resistance_ohm': series_resistance,
            'charge_transfer_resistance_ohm': max(0.0, charge_transfer_resistance),
            'total_points': len(frequency)
        }
        
        quality_metrics = {
            'frequency_coverage': np.log10(frequency.max() / frequency.min()) if frequency.min() > 0 else 0.0,
            'data_quality': 1.0 - np.mean(np.isnan(z_real) | np.isnan(z_imag)),
            'data_completeness': len(frequency) / len(data)
        }
        
        return AnalysisResult('EIS', action_id, results, quality_metrics)