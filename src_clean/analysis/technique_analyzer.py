"""
Technique Analyzer - Advanced Analytics

Technique-specific analysis including:
- Rest phase analysis with context-aware decay fitting
- Current pulse resistance calculations
- Advanced curve fitting with quality metrics
"""

import numpy as np
import polars as pl
from scipy import optimize
from typing import Dict, Any, Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)


class TechniqueAnalyzer:
    """
    Advanced technique-specific analytics with curve fitting.
    
    Performs context-aware analysis based on technique identification
    and previous segment context.
    """
    
    # Rest phase identification keywords
    REST_KEYWORDS = {
        'rest', 'relax', 'eis', 'open_circuit', 'ocp', 'ocv', 
        'impedance', 'pause', 'wait', 'delay'
    }
    
    def __init__(self):
        self.logger = logger
    
    def analyze_segment(self, data: pl.DataFrame, start_row: int, end_row: int,
                       technique_name: str, fundamental_technique: str,
                       previous_segment_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform technique-specific analysis on a segment.
        
        Args:
            data: Full DataFrame with universal schema
            start_row: Starting row index (inclusive)  
            end_row: Ending row index (exclusive)
            technique_name: Name of the technique
            fundamental_technique: Fundamental technique category
            previous_segment_info: Information about the previous segment
            
        Returns:
            Dictionary with analysis results and quality metrics
        """
        try:
            # Extract segment data
            segment_data = data.slice(start_row, end_row - start_row + 1)
            
            if segment_data.height == 0:
                return {'analysis_type': 'empty', 'success': False}
            
            analysis_results = {'analysis_type': 'unknown', 'success': True}
            
            # Determine analysis type
            if self._is_rest_phase(technique_name, fundamental_technique):
                analysis_results = self._analyze_rest_phase(
                    segment_data, previous_segment_info
                )
            elif self._is_current_pulse(segment_data):
                analysis_results = self._analyze_current_pulse(segment_data)
            else:
                # General technique analysis
                analysis_results = self._analyze_general_technique(segment_data)
            
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Error in technique analysis: {e}")
            return {'analysis_type': 'error', 'success': False, 'error': str(e)}
    
    def _is_rest_phase(self, technique_name: str, fundamental_technique: str) -> bool:
        """
        Determine if this is a rest phase based on technique identification.
        
        Args:
            technique_name: Name of the technique
            fundamental_technique: Fundamental technique category
            
        Returns:
            True if this is identified as a rest phase
        """
        # Check technique names for rest keywords
        name_lower = technique_name.lower()
        fundamental_lower = fundamental_technique.lower()
        
        return (any(keyword in name_lower for keyword in self.REST_KEYWORDS) or
                any(keyword in fundamental_lower for keyword in self.REST_KEYWORDS))
    
    def _analyze_rest_phase(self, segment_data: pl.DataFrame, 
                           previous_segment_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze rest phase with comprehensive dual decay fitting.
        
        Always attempts both voltage and current decay analysis with both exponential
        and sqrt(t) fitting models, returning the best fit or indicating insufficient data.
        
        Args:
            segment_data: Segment DataFrame
            previous_segment_info: Information about previous segment
            
        Returns:
            Analysis results with fit parameters and quality metrics
        """
        try:
            time_values = segment_data.get_column('time_s').to_numpy()
            voltage_values = segment_data.get_column('potential_v').to_numpy()
            current_values = segment_data.get_column('current_a').to_numpy()
            
            # Always attempt both voltage and current decay analysis with both models
            voltage_exp_result = self._analyze_voltage_decay(time_values, voltage_values)
            current_exp_result = self._analyze_current_decay(time_values, current_values)
            voltage_sqrt_result = self._analyze_voltage_sqrt_decay(time_values, voltage_values)
            current_sqrt_result = self._analyze_current_sqrt_decay(time_values, current_values)
            
            # Collect all successful results
            results = []
            for result in [voltage_exp_result, current_exp_result, voltage_sqrt_result, current_sqrt_result]:
                if result.get('success', False):
                    results.append(result)
            
            if not results:
                # All fitting attempts failed
                return {
                    'analysis_type': 'rest_insufficient_data', 
                    'success': False,
                    'voltage_exp_error': voltage_exp_result.get('error', 'Unknown'),
                    'current_exp_error': current_exp_result.get('error', 'Unknown'),
                    'voltage_sqrt_error': voltage_sqrt_result.get('error', 'Unknown'),
                    'current_sqrt_error': current_sqrt_result.get('error', 'Unknown')
                }
            
            # Return the best fit based on R² value
            best_result = max(results, key=lambda x: x.get('r_squared', 0))
            
            # Store all fit coefficients in the result for replotting capability
            fit_coefficients = {
                'exponential_fits': {},
                'sqrt_fits': {}
            }
            
            if voltage_exp_result.get('success'):
                fit_coefficients['exponential_fits']['voltage'] = self._extract_fit_coefficients(voltage_exp_result)
            if current_exp_result.get('success'):
                fit_coefficients['exponential_fits']['current'] = self._extract_fit_coefficients(current_exp_result)
            if voltage_sqrt_result.get('success'):
                fit_coefficients['sqrt_fits']['voltage'] = self._extract_fit_coefficients(voltage_sqrt_result)
            if current_sqrt_result.get('success'):
                fit_coefficients['sqrt_fits']['current'] = self._extract_fit_coefficients(current_sqrt_result)
            
            # Add fit coefficients to the best result
            best_result['all_fit_coefficients'] = fit_coefficients
            
            return best_result
                    
        except Exception as e:
            self.logger.debug(f"Rest phase analysis failed: {e}")
            return {'analysis_type': 'rest_failed', 'success': False, 'error': str(e)}
    
    def _analyze_voltage_decay(self, time_values: np.ndarray, 
                             voltage_values: np.ndarray) -> Dict[str, Any]:
        """
        Analyze voltage decay with exponential fitting: V(t) = V∞ + A·exp(-t/τ).
        
        Args:
            time_values: Time points in seconds
            voltage_values: Voltage values in volts
            
        Returns:
            Fit parameters and quality metrics
        """
        try:
            # Remove NaN and normalize time to start at 0
            valid_mask = ~(np.isnan(time_values) | np.isnan(voltage_values))
            if not np.any(valid_mask) or np.sum(valid_mask) < 10:
                return {'analysis_type': 'voltage_decay_insufficient_data', 'success': False}
            
            t_clean = time_values[valid_mask] - time_values[valid_mask][0]
            v_clean = voltage_values[valid_mask]
            
            # Exponential decay fitting
            result = self._fit_exponential_decay(t_clean, v_clean, 'voltage')
            result['analysis_type'] = 'voltage_decay'
            
            return result
            
        except Exception as e:
            return {'analysis_type': 'voltage_decay_failed', 'success': False, 'error': str(e)}
    
    def _analyze_current_decay(self, time_values: np.ndarray,
                             current_values: np.ndarray) -> Dict[str, Any]:
        """
        Analyze current decay with exponential fitting: I(t) = I∞ + A·exp(-t/τ).
        
        Args:
            time_values: Time points in seconds
            current_values: Current values in amperes
            
        Returns:
            Fit parameters and quality metrics
        """
        try:
            # Remove NaN and normalize time to start at 0
            valid_mask = ~(np.isnan(time_values) | np.isnan(current_values))
            if not np.any(valid_mask) or np.sum(valid_mask) < 10:
                return {'analysis_type': 'current_decay_insufficient_data', 'success': False}
            
            t_clean = time_values[valid_mask] - time_values[valid_mask][0]
            i_clean = current_values[valid_mask]
            
            # Exponential decay fitting
            result = self._fit_exponential_decay(t_clean, i_clean, 'current')
            result['analysis_type'] = 'current_decay'
            
            return result
            
        except Exception as e:
            return {'analysis_type': 'current_decay_failed', 'success': False, 'error': str(e)}
    
    def _analyze_voltage_sqrt_decay(self, time_values: np.ndarray, 
                                  voltage_values: np.ndarray) -> Dict[str, Any]:
        """
        Analyze voltage decay with sqrt(t) fitting: V(t) = V∞ + A·√t.
        
        Args:
            time_values: Time points in seconds
            voltage_values: Voltage values in volts
            
        Returns:
            Fit parameters and quality metrics
        """
        try:
            # Remove NaN and normalize time to start at 0
            valid_mask = ~(np.isnan(time_values) | np.isnan(voltage_values))
            if not np.any(valid_mask) or np.sum(valid_mask) < 10:
                return {'analysis_type': 'voltage_sqrt_insufficient_data', 'success': False}
            
            t_clean = time_values[valid_mask] - time_values[valid_mask][0]
            v_clean = voltage_values[valid_mask]
            
            # sqrt(t) fitting
            result = self._fit_sqrt_decay(t_clean, v_clean, 'voltage')
            result['analysis_type'] = 'voltage_sqrt_decay'
            
            return result
            
        except Exception as e:
            return {'analysis_type': 'voltage_sqrt_failed', 'success': False, 'error': str(e)}
    
    def _analyze_current_sqrt_decay(self, time_values: np.ndarray,
                                  current_values: np.ndarray) -> Dict[str, Any]:
        """
        Analyze current decay with sqrt(t) fitting: I(t) = I∞ + A·√t.
        
        Args:
            time_values: Time points in seconds
            current_values: Current values in amperes
            
        Returns:
            Fit parameters and quality metrics
        """
        try:
            # Remove NaN and normalize time to start at 0
            valid_mask = ~(np.isnan(time_values) | np.isnan(current_values))
            if not np.any(valid_mask) or np.sum(valid_mask) < 10:
                return {'analysis_type': 'current_sqrt_insufficient_data', 'success': False}
            
            t_clean = time_values[valid_mask] - time_values[valid_mask][0]
            i_clean = current_values[valid_mask]
            
            # sqrt(t) fitting
            result = self._fit_sqrt_decay(t_clean, i_clean, 'current')
            result['analysis_type'] = 'current_sqrt_decay'
            
            return result
            
        except Exception as e:
            return {'analysis_type': 'current_sqrt_failed', 'success': False, 'error': str(e)}
    
    def _fit_exponential_decay(self, t: np.ndarray, y: np.ndarray, 
                             variable_type: str) -> Dict[str, Any]:
        """
        Fit exponential decay: y(t) = y∞ + A·exp(-t/τ).
        
        Args:
            t: Time values (normalized to start at 0)
            y: Signal values (voltage or current)
            variable_type: 'voltage' or 'current' for proper naming
            
        Returns:
            Fit parameters and quality metrics
        """
        try:
            if len(t) < 10:
                return {'success': False, 'error': 'Insufficient data points'}
            
            # Initial parameter estimates
            y_initial = y[0]
            y_final = y[-1]
            y_infinity_guess = y_final
            A_guess = y_initial - y_final
            tau_guess = np.max(t) / 3.0  # Rough estimate
            
            # Define exponential decay function
            def exp_decay(t_vals, y_inf, A, tau):
                return y_inf + A * np.exp(-t_vals / max(tau, 1e-6))
            
            # Perform curve fitting with bounds
            bounds = (
                [-np.inf, -np.inf, 1e-3],  # Lower bounds
                [np.inf, np.inf, np.max(t) * 10]   # Upper bounds
            )
            
            popt, pcov = optimize.curve_fit(
                exp_decay, t, y,
                p0=[y_infinity_guess, A_guess, tau_guess],
                bounds=bounds,
                maxfev=1000
            )
            
            y_infinity, A, tau = popt
            
            # Calculate fit quality
            y_fit = exp_decay(t, *popt)
            r_squared = self._calculate_r_squared(y, y_fit)
            rmse = np.sqrt(np.mean((y - y_fit)**2))
            
            # Parameter uncertainties
            param_errors = np.sqrt(np.diag(pcov)) if pcov is not None else [0, 0, 0]
            
            prefix = variable_type  # 'voltage' or 'current'
            
            result = {
                'success': True,
                'fit_type': 'exponential_decay',
                f'{prefix}_infinity': float(y_infinity),
                f'{prefix}_amplitude': float(A),
                'time_constant_s': float(tau),
                'r_squared': float(r_squared),
                'rmse': float(rmse),
                'param_errors': {
                    f'{prefix}_infinity_error': float(param_errors[0]),
                    f'{prefix}_amplitude_error': float(param_errors[1]),
                    'time_constant_error': float(param_errors[2])
                },
                'data_points': len(t)
            }
            
            return result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _fit_sqrt_decay(self, t: np.ndarray, y: np.ndarray, 
                       variable_type: str) -> Dict[str, Any]:
        """
        Fit sqrt(t) decay: y(t) = y∞ + A·√t.
        
        Args:
            t: Time values (normalized to start at 0)
            y: Signal values (voltage or current)
            variable_type: 'voltage' or 'current' for proper naming
            
        Returns:
            Fit parameters and quality metrics
        """
        try:
            if len(t) < 10:
                return {'success': False, 'error': 'Insufficient data points'}
            
            # Avoid sqrt(0) by adding small offset to time
            t_offset = t + 1e-6
            sqrt_t = np.sqrt(t_offset)
            
            # Initial parameter estimates
            y_initial = y[0]
            y_final = y[-1]
            y_infinity_guess = y_final
            A_guess = (y_initial - y_final) / np.sqrt(np.max(t_offset))
            
            # Define sqrt(t) decay function
            def sqrt_decay(t_vals, y_inf, A):
                return y_inf + A * np.sqrt(t_vals + 1e-6)
            
            # Perform curve fitting
            popt, pcov = optimize.curve_fit(
                sqrt_decay, t, y,
                p0=[y_infinity_guess, A_guess],
                maxfev=1000
            )
            
            y_infinity, A = popt
            
            # Calculate fit quality
            y_fit = sqrt_decay(t, *popt)
            r_squared = self._calculate_r_squared(y, y_fit)
            rmse = np.sqrt(np.mean((y - y_fit)**2))
            
            # Parameter uncertainties
            param_errors = np.sqrt(np.diag(pcov)) if pcov is not None else [0, 0]
            
            prefix = variable_type  # 'voltage' or 'current'
            
            result = {
                'success': True,
                'fit_type': 'sqrt_decay',
                f'{prefix}_infinity': float(y_infinity),
                f'{prefix}_sqrt_amplitude': float(A),
                'r_squared': float(r_squared),
                'rmse': float(rmse),
                'param_errors': {
                    f'{prefix}_infinity_error': float(param_errors[0]),
                    f'{prefix}_sqrt_amplitude_error': float(param_errors[1])
                },
                'data_points': len(t)
            }
            
            return result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _extract_fit_coefficients(self, fit_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract fit coefficients from analysis result for storage and replotting.
        
        Args:
            fit_result: Result dictionary from fitting analysis
            
        Returns:
            Dictionary with essential coefficients for replotting
        """
        coefficients = {
            'fit_type': fit_result.get('fit_type', 'unknown'),
            'r_squared': fit_result.get('r_squared', 0.0),
            'rmse': fit_result.get('rmse', 0.0),
            'data_points': fit_result.get('data_points', 0)
        }
        
        # Extract coefficients based on fit type
        if fit_result.get('fit_type') == 'exponential_decay':
            # Exponential: y = y∞ + A·exp(-t/τ)
            for key in ['voltage_infinity', 'current_infinity', 'voltage_amplitude', 
                       'current_amplitude', 'time_constant_s']:
                if key in fit_result:
                    coefficients[key] = fit_result[key]
                    
        elif fit_result.get('fit_type') == 'sqrt_decay':
            # sqrt(t): y = y∞ + A·√t
            for key in ['voltage_infinity', 'current_infinity', 'voltage_sqrt_amplitude',
                       'current_sqrt_amplitude']:
                if key in fit_result:
                    coefficients[key] = fit_result[key]
        
        return coefficients
    
    def _is_current_pulse(self, segment_data: pl.DataFrame) -> bool:
        """
        Determine if this segment represents a current pulse.
        
        Args:
            segment_data: Segment DataFrame
            
        Returns:
            True if this appears to be a current pulse
        """
        try:
            current_values = segment_data.get_column('current_a').to_numpy()
            valid_current = current_values[~np.isnan(current_values)]
            
            if len(valid_current) < 10:
                return False
            
            # Check for significant current and relatively stable current
            current_mean = np.abs(np.mean(valid_current))
            current_std = np.std(valid_current)
            
            # Criteria: significant current (>1µA) and relatively stable (CV < 50%)
            return (current_mean > 1e-6 and 
                   (current_std / current_mean < 0.5 if current_mean > 0 else False))
            
        except Exception:
            return False
    
    def _analyze_current_pulse(self, segment_data: pl.DataFrame) -> Dict[str, Any]:
        """
        Analyze current pulse with resistance calculations.
        
        Args:
            segment_data: Segment DataFrame
            
        Returns:
            Resistance analysis results
        """
        try:
            time_values = segment_data.get_column('time_s').to_numpy()
            voltage_values = segment_data.get_column('potential_v').to_numpy()
            current_values = segment_data.get_column('current_a').to_numpy()
            
            # Remove NaN values
            valid_mask = ~(np.isnan(time_values) | np.isnan(voltage_values) | np.isnan(current_values))
            if not np.any(valid_mask) or np.sum(valid_mask) < 10:
                return {'analysis_type': 'current_pulse_insufficient_data', 'success': False}
            
            t_clean = time_values[valid_mask]
            v_clean = voltage_values[valid_mask]
            i_clean = current_values[valid_mask]
            
            # Calculate resistance at different time points
            resistances = self._calculate_pulse_resistances(t_clean, v_clean, i_clean)
            
            result = {
                'analysis_type': 'current_pulse',
                'success': True,
                **resistances
            }
            
            return result
            
        except Exception as e:
            return {'analysis_type': 'current_pulse_failed', 'success': False, 'error': str(e)}
    
    def _calculate_pulse_resistances(self, time_values: np.ndarray,
                                   voltage_values: np.ndarray, 
                                   current_values: np.ndarray) -> Dict[str, Any]:
        """
        Calculate IR resistance at different time intervals.
        
        Args:
            time_values: Time points in seconds
            voltage_values: Voltage values in volts
            current_values: Current values in amperes
            
        Returns:
            Resistance calculations at different time points
        """
        try:
            # Normalize time to start at 0
            t_rel = time_values - time_values[0]
            
            # Calculate baseline (average of first few points)
            baseline_points = min(5, len(voltage_values) // 10)
            v_baseline = np.mean(voltage_values[:baseline_points])
            i_average = np.mean(current_values)
            
            resistances = {}
            
            # IR immediate (first data point after baseline)
            if len(voltage_values) > baseline_points:
                v_immediate = voltage_values[baseline_points]
                dv_immediate = v_immediate - v_baseline
                if abs(i_average) > 1e-9:
                    resistances['ir_immediate_ohm'] = float(dv_immediate / i_average)
            
            # IR at 10s
            idx_10s = np.argmin(np.abs(t_rel - 10.0))
            if idx_10s < len(voltage_values) and t_rel[idx_10s] >= 5.0:  # At least 5s in
                v_10s = voltage_values[idx_10s]
                dv_10s = v_10s - v_baseline
                if abs(i_average) > 1e-9:
                    resistances['ir_10s_ohm'] = float(dv_10s / i_average)
            
            # IR at 30s
            idx_30s = np.argmin(np.abs(t_rel - 30.0))
            if idx_30s < len(voltage_values) and t_rel[idx_30s] >= 20.0:  # At least 20s in
                v_30s = voltage_values[idx_30s]
                dv_30s = v_30s - v_baseline
                if abs(i_average) > 1e-9:
                    resistances['ir_30s_ohm'] = float(dv_30s / i_average)
            
            resistances.update({
                'baseline_voltage_v': float(v_baseline),
                'average_current_a': float(i_average),
                'pulse_duration_s': float(t_rel[-1])
            })
            
            return resistances
            
        except Exception as e:
            self.logger.debug(f"Resistance calculation failed: {e}")
            return {'error': str(e)}
    
    def _analyze_general_technique(self, segment_data: pl.DataFrame) -> Dict[str, Any]:
        """
        General analysis for techniques that don't fit specific patterns.
        
        Args:
            segment_data: Segment DataFrame
            
        Returns:
            Basic statistical analysis
        """
        try:
            voltage_values = segment_data.get_column('potential_v').to_numpy()
            current_values = segment_data.get_column('current_a').to_numpy()
            
            # Remove NaN values
            v_clean = voltage_values[~np.isnan(voltage_values)]
            i_clean = current_values[~np.isnan(current_values)]
            
            result = {
                'analysis_type': 'general',
                'success': True
            }
            
            if len(v_clean) > 0:
                result.update({
                    'voltage_mean_v': float(np.mean(v_clean)),
                    'voltage_std_v': float(np.std(v_clean)),
                    'voltage_range_v': float(np.max(v_clean) - np.min(v_clean))
                })
            
            if len(i_clean) > 0:
                result.update({
                    'current_mean_a': float(np.mean(i_clean)),
                    'current_std_a': float(np.std(i_clean)),
                    'current_range_a': float(np.max(i_clean) - np.min(i_clean))
                })
            
            return result
            
        except Exception as e:
            return {'analysis_type': 'general_failed', 'success': False, 'error': str(e)}
    
    def _calculate_r_squared(self, y_actual: np.ndarray, y_predicted: np.ndarray) -> float:
        """Calculate R² coefficient of determination."""
        try:
            ss_res = np.sum((y_actual - y_predicted) ** 2)
            ss_tot = np.sum((y_actual - np.mean(y_actual)) ** 2)
            
            if ss_tot == 0:
                return 1.0 if ss_res == 0 else 0.0
            
            r_squared = 1 - (ss_res / ss_tot)
            return max(0.0, min(1.0, r_squared))  # Clamp between 0 and 1
            
        except Exception:
            return 0.0