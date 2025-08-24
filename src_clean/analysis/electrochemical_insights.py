"""
Electrochemical Insights Extraction

Extracts electrochemical insights from existing JSON fit coefficients and segment data.
Focuses on physics-based analysis rather than generic statistical metrics.
"""

import polars as pl
import numpy as np
from typing import Dict, List, Any, Optional, Union
import logging
from dataclasses import dataclass
import json

from src_clean.core.config import get_config
from src_clean.analysis.analytics_config import get_config as get_analytics_config

logger = logging.getLogger(__name__)


@dataclass
class RelaxationKinetics:
    """Results from voltage/current relaxation analysis."""
    technique: str
    variable_type: str  # 'voltage' or 'current'
    fit_type: str       # 'exponential' or 'sqrt'
    
    # Fit parameters
    equilibrium_value: float
    amplitude: float
    time_constant: Optional[float] = None  # For exponential fits
    sqrt_coefficient: Optional[float] = None  # For sqrt fits
    
    # Quality metrics
    r_squared: float = 0.0
    rmse: float = 0.0
    data_points: int = 0
    
    # Physical interpretation
    relaxation_quality: str = "unknown"  # good, fair, poor
    diffusion_regime: str = "unknown"    # fast, slow, mixed


@dataclass
class ResistanceAnalysis:
    """Results from instantaneous resistance analysis."""
    segment_id: str
    technique: str
    
    # Resistance calculations (using analytics_config current_pulse schema)
    ir_immediate_ohm: Optional[float] = None
    ir_10s_ohm: Optional[float] = None
    ir_30s_ohm: Optional[float] = None
    
    # Context data
    current_pulse_a: Optional[float] = None
    voltage_change_v: Optional[float] = None
    pulse_duration_s: Optional[float] = None
    
    # Quality assessment
    calculation_quality: str = "unknown"  # good, fair, poor, invalid


@dataclass
class EquilibriumAnalysis:
    """Results from equilibrium voltage analysis."""
    segment_id: str
    technique: str
    
    # Equilibrium tracking (using analytics_config exponential_fit schema)
    start_voltage_v: float  # Keep for context
    end_voltage_v: float    # Keep for context
    voltage_infinity: Optional[float] = None  # Analytics config field name
    
    # Kinetics metrics (analytics_config exponential_fit schema)
    time_constant_s: Optional[float] = None
    voltage_amplitude: Optional[float] = None  # Decay amplitude
    r_squared: Optional[float] = None  # Fit quality
    
    # Additional stability metrics (can be kept as supplementary)
    voltage_drift_mv_min: Optional[float] = None
    stability_achieved: bool = False
    stability_time_s: Optional[float] = None


class ElectrochemicalInsights:
    """
    Extracts electrochemical insights from existing JSON fit coefficients.
    
    Implements the unified analytics pattern where single methods handle
    both single-group and multi-group analysis automatically.
    """
    
    def __init__(self):
        self.config = get_config()
        self.analytics_config = get_analytics_config()
        self.logger = logger
    
    def get_rest_relaxation_kinetics(self, segment_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract voltage and current relaxation kinetics from REST segments.
        
        Args:
            segment_data: List of segment dictionaries with analysis_results JSON
            
        Returns:
            Dictionary with relaxation kinetics analysis for all REST segments
        """
        try:
            kinetics_results = []
            core_segment_data = []
            
            for segment in segment_data:
                if segment.get('technique_name', '').upper() != 'REST':
                    continue
                
                segment_id = segment.get('id', 'unknown')


                analysis_results = segment.get('analysis_results', {})
                
                if isinstance(analysis_results, str):
                    try:
                        analysis_results = json.loads(analysis_results)
                    except json.JSONDecodeError:
                        continue
                
                # Extract relaxation kinetics from stored fit coefficients
                kinetics = self._extract_relaxation_from_json(segment_id, analysis_results)
                kinetics_results.extend(kinetics)

                # Add core segment data for plotting fix - This is temporary so that plots work.
                if kinetics:
                    core_segment_data.append(segment)

            # Aggregate results
            summary = self._summarize_relaxation_kinetics(kinetics_results)
            
            return {
                'analysis_type': 'rest_relaxation_kinetics',
                'segment_count': len([s for s in segment_data if s.get('technique_name', '').upper() == 'REST']),
                'core_segment_data': core_segment_data,
                'individual_kinetics': [self._kinetics_to_dict(k) for k in kinetics_results],
                'summary_statistics': summary,
                'electrochemical_insights': self._interpret_relaxation_kinetics(kinetics_results)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze REST relaxation kinetics: {e}")
            return {'analysis_type': 'rest_relaxation_kinetics', 'error': str(e)}
    
    def get_instantaneous_resistance_analysis(self, segment_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate instantaneous resistance from GALVANOSTATIC segments.
        
        Args:
            segment_data: List of segment dictionaries
            
        Returns:
            Dictionary with resistance analysis for galvanostatic segments
        """
        try:
            resistance_results = []
            core_segment_data = []
            for segment in segment_data:
                technique = segment.get('technique_name', '').upper()
                if technique != 'GALVANOSTATIC':
                    continue
                
                segment_id = segment.get('id', 'unknown')



                # Calculate instantaneous resistance from segment boundaries
                resistance_analysis = self._calculate_instantaneous_resistance(segment)
                if resistance_analysis:
                    resistance_analysis.segment_id = segment_id
                    resistance_analysis.technique = technique
                    resistance_results.append(resistance_analysis)

                    # Add core segment data for plotting fix - This is temporary so that plots work.
                    core_segment_data.append(segment)
            # Summary statistics
            summary = self._summarize_resistance_analysis(resistance_results)
            
            return {
                'analysis_type': 'instantaneous_resistance_analysis',
                'segment_count': len([s for s in segment_data if s.get('technique_name', '').upper() == 'GALVANOSTATIC']),
                'core_segment_data': core_segment_data,
                'individual_resistances': [self._resistance_to_dict(r) for r in resistance_results],
                'summary_statistics': summary,
                'electrochemical_insights': self._interpret_resistance_analysis(resistance_results)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze instantaneous resistance: {e}")
            return {'analysis_type': 'instantaneous_resistance_analysis', 'error': str(e)}
    
    def get_equilibrium_voltage_analysis(self, segment_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze equilibrium voltage tracking across REST segments.
        
        Args:
            segment_data: List of segment dictionaries
            
        Returns:
            Dictionary with equilibrium voltage analysis
        """
        try:
            equilibrium_results = []
            
            for segment in segment_data:
                if segment.get('technique_name', '').upper() != 'REST':
                    continue
                
                segment_id = segment.get('id', 'unknown')
                
                # Extract equilibrium analysis
                equilibrium_analysis = self._analyze_equilibrium_voltage(segment)
                if equilibrium_analysis:
                    equilibrium_analysis.segment_id = segment_id
                    equilibrium_analysis.technique = 'REST'
                    equilibrium_results.append(equilibrium_analysis)
            
            # Track equilibrium evolution
            evolution = self._track_equilibrium_evolution(equilibrium_results)
            
            # Calculate diffusion coefficients from time constants
            diffusion_coefficients = self._calculate_diffusion_coefficients(equilibrium_results)
            
            return {
                'analysis_type': 'equilibrium_voltage_analysis',
                'segment_count': len([s for s in segment_data if s.get('technique_name', '').upper() == 'REST']),
                'individual_equilibrium': [self._equilibrium_to_dict(e, diffusion_coefficients.get(e.segment_id)) for e in equilibrium_results],
                'diffusion_coefficients': diffusion_coefficients,
                'equilibrium_evolution': evolution,
                'electrochemical_insights': self._interpret_equilibrium_analysis(equilibrium_results)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze equilibrium voltage: {e}")
            return {'analysis_type': 'equilibrium_voltage_analysis', 'error': str(e)}
    
    def get_current_decay_kinetics(self, segment_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract current decay kinetics from POTENTIOSTATIC segments.
        
        Args:
            segment_data: List of segment dictionaries
            
        Returns:
            Dictionary with current decay analysis
        """
        try:
            decay_results = []
            
            for segment in segment_data:
                if segment.get('technique_name', '').upper() != 'POTENTIOSTATIC':
                    continue
                
                segment_id = segment.get('id', 'unknown')
                analysis_results = segment.get('analysis_results', {})
                
                if isinstance(analysis_results, str):
                    try:
                        analysis_results = json.loads(analysis_results)
                    except json.JSONDecodeError:
                        continue
                
                # Extract current decay from fit coefficients
                decay_kinetics = self._extract_current_decay_from_json(segment_id, analysis_results)
                decay_results.extend(decay_kinetics)
            
            # Aggregate results
            summary = self._summarize_current_decay(decay_results)
            
            return {
                'analysis_type': 'current_decay_kinetics',
                'segment_count': len([s for s in segment_data if s.get('technique_name', '').upper() == 'POTENTIOSTATIC']),
                'individual_decays': decay_results,
                'summary_statistics': summary,
                'electrochemical_insights': self._interpret_current_decay(decay_results)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze current decay kinetics: {e}")
            return {'analysis_type': 'current_decay_kinetics', 'error': str(e)}
    
    def _extract_relaxation_from_json(self, segment_id: str, analysis_results: Dict) -> List[RelaxationKinetics]:
        """Extract relaxation kinetics from stored JSON coefficients."""
        kinetics = []
        
        # HACKY FIX: Handle actual JSON structure from database
        if analysis_results.get('success') and analysis_results.get('analysis_type') == 'voltage_decay':
            # Direct coefficients at root level for successful voltage decay analysis
            if analysis_results.get('r_squared', 0) > 0.1:  # Lower threshold for testing
                kinetic = RelaxationKinetics(
                    technique='REST',
                    variable_type='voltage',
                    fit_type='exponential',
                    equilibrium_value=analysis_results.get('voltage_infinity', 0.0),
                    amplitude=analysis_results.get('voltage_amplitude', 0.0),
                    time_constant=analysis_results.get('time_constant_s', 0.0),
                    r_squared=analysis_results.get('r_squared', 0.0),
                    rmse=analysis_results.get('rmse', 0.0),
                    data_points=analysis_results.get('data_points', 0)
                )
                kinetic.relaxation_quality = self._assess_fit_quality(kinetic.r_squared)
                kinetic.diffusion_regime = self._assess_diffusion_regime(kinetic.time_constant)
                kinetics.append(kinetic)
        elif not analysis_results.get('success'):
            # Map failed analysis as poor quality
            kinetic = RelaxationKinetics(
                technique='REST',
                variable_type='voltage',
                fit_type='exponential',
                equilibrium_value=0.0,
                amplitude=0.0,
                time_constant=0.0,
                r_squared=0.0,
                rmse=999.0,
                data_points=0
            )
            kinetic.relaxation_quality = "failed"
            kinetic.diffusion_regime = "unknown"
            kinetics.append(kinetic)
        
        return kinetics
    
    def _calculate_instantaneous_resistance(self, segment: Dict[str, Any]) -> Optional[ResistanceAnalysis]:
        """Extract resistance analysis from segment analysis_results (already calculated)."""
        try:
            # Extract resistance analysis from analysis_results (direct fields, not calculated)
            analysis_results = segment.get('analysis_results', {})
            if isinstance(analysis_results, str):
                try:
                    analysis_results = json.loads(analysis_results)
                except json.JSONDecodeError:
                    analysis_results = {}
            
            # Check if this is a current_pulse analysis with resistance data
            if not (analysis_results.get('success') and analysis_results.get('analysis_type') == 'current_pulse'):
                return None
            
            resistance_analysis = ResistanceAnalysis(
                segment_id="",  # Will be set by caller
                technique="GALVANOSTATIC",
                current_pulse_a=segment.get('end_current_a', 0.0),
                voltage_change_v=segment.get('end_potential_v', 0.0) - segment.get('start_potential_v', 0.0),
                pulse_duration_s=segment.get('duration_s', 0.0)
            )
            
            # Extract resistance values using analytics_config current_pulse schema field names
            resistance_analysis.ir_immediate_ohm = analysis_results.get('ir_immediate_ohm')
            resistance_analysis.ir_10s_ohm = analysis_results.get('ir_10s_ohm') 
            resistance_analysis.ir_30s_ohm = analysis_results.get('ir_30s_ohm')
            resistance_analysis.baseline_voltage_v = analysis_results.get('baseline_voltage_v')
            resistance_analysis.average_current_a = analysis_results.get('average_current_a')
            
            # Set quality based on data availability
            if resistance_analysis.ir_immediate_ohm is not None:
                resistance_analysis.calculation_quality = "good"  # Data already validated during analysis
            else:
                resistance_analysis.calculation_quality = "invalid"
            
            return resistance_analysis
            
        except Exception as e:
            self.logger.error(f"Failed to extract resistance analysis: {e}")
            return None
    
    def _analyze_equilibrium_voltage(self, segment: Dict[str, Any]) -> Optional[EquilibriumAnalysis]:
        """Analyze equilibrium voltage from REST segment."""
        try:
            start_voltage = segment.get('start_potential_v', 0.0)
            end_voltage = segment.get('end_potential_v', 0.0)
            duration = segment.get('duration_s', 0.0)
            
            # Extract equilibrium voltage from analysis results if available
            analysis_results = segment.get('analysis_results', {})
            if isinstance(analysis_results, str):
                try:
                    analysis_results = json.loads(analysis_results)
                except json.JSONDecodeError:
                    analysis_results = {}
            
            equilibrium_analysis = EquilibriumAnalysis(
                segment_id="",  # Will be set by caller
                technique="REST",
                start_voltage_v=start_voltage,
                end_voltage_v=end_voltage
            )
            
            # Get equilibrium voltage from analysis_results (direct fields, not nested)
            # Fields match analytics_config exponential_fit schema: voltage_infinity, time_constant_s, etc.
            if analysis_results.get('success'):
                # Use analytics_config field names directly
                equilibrium_analysis.voltage_infinity = analysis_results.get('voltage_infinity', end_voltage)
                equilibrium_analysis.time_constant_s = analysis_results.get('time_constant_s')
                equilibrium_analysis.voltage_amplitude = analysis_results.get('voltage_amplitude')
                equilibrium_analysis.r_squared = analysis_results.get('r_squared')
            else:
                equilibrium_analysis.voltage_infinity = end_voltage
            
            # Calculate drift rate
            if duration > 0:
                voltage_drift = abs(end_voltage - start_voltage)
                equilibrium_analysis.voltage_drift_mv_min = (voltage_drift * 1000 * 60) / duration
                
                # Assess stability
                if equilibrium_analysis.voltage_drift_mv_min < 0.1:  # <0.1 mV/min
                    equilibrium_analysis.stability_achieved = True
                    equilibrium_analysis.equilibrium_quality = "stable"
                elif equilibrium_analysis.voltage_drift_mv_min < 1.0:  # <1 mV/min
                    equilibrium_analysis.equilibrium_quality = "drifting"
                else:
                    equilibrium_analysis.equilibrium_quality = "unstable"
            
            return equilibrium_analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze equilibrium voltage: {e}")
            return None
    
    def _extract_current_decay_from_json(self, segment_id: str, analysis_results: Dict) -> List[Dict[str, Any]]:
        """Extract current decay kinetics from JSON coefficients."""
        decay_results = []
        
        all_fits = analysis_results.get('all_fit_coefficients', {})
        
        # Current exponential fits
        current_exp = all_fits.get('exponential_fits', {}).get('current', {})
        if current_exp.get('r_squared', 0) > 0.5:
            decay_results.append({
                'segment_id': segment_id,
                'fit_type': 'exponential',
                'equilibrium_current_a': current_exp.get('current_infinity', 0.0),
                'decay_amplitude': current_exp.get('current_amplitude', 0.0),
                'time_constant_s': current_exp.get('time_constant_s', 0.0),
                'r_squared': current_exp.get('r_squared', 0.0),
                'decay_quality': self._assess_fit_quality(current_exp.get('r_squared', 0.0))
            })
        
        return decay_results
    
    def _calculate_diffusion_coefficients(self, equilibrium_results: List[EquilibriumAnalysis]) -> Dict[str, float]:
        """
        Calculate diffusion coefficients from time constants using Cottrell equation.
        
        Args:
            equilibrium_results: List of equilibrium analysis results with time constants
            
        Returns:
            Dictionary mapping segment_id to diffusion coefficient in cm²/s
        """
        diffusion_coefficients = {}
        
        # Typical electrode dimensions for Li-ion cells
        # These should ideally be extracted from cell metadata
        characteristic_length_cm = 0.01  # 100 μm typical electrode thickness
        
        for equilibrium in equilibrium_results:
            if equilibrium.time_constant_s is not None and equilibrium.time_constant_s > 0:
                # Cottrell equation: D = L² / (π² * τ)
                # Where: D = diffusion coefficient, L = characteristic length, τ = time constant
                diffusion_coeff = (characteristic_length_cm ** 2) / (np.pi ** 2 * equilibrium.time_constant_s)
                diffusion_coefficients[equilibrium.segment_id] = diffusion_coeff
                
                self.logger.debug(f"Calculated diffusion coefficient for segment {equilibrium.segment_id}: "
                                f"{diffusion_coeff:.2e} cm²/s (τ = {equilibrium.time_constant_s:.1f} s)")
        
        return diffusion_coefficients
    
    def _assess_fit_quality(self, r_squared: float) -> str:
        """Assess fit quality based on R² value."""
        if r_squared >= 0.95:
            return "excellent"
        elif r_squared >= 0.90:
            return "good"
        elif r_squared >= 0.80:
            return "fair"
        else:
            return "poor"
    
    def _assess_diffusion_regime(self, time_constant: Optional[float]) -> str:
        """Assess diffusion regime based on time constant."""
        if time_constant is None or time_constant <= 0:
            return "unknown"
        
        if time_constant < 10:
            return "fast_kinetics"
        elif time_constant < 100:
            return "mixed_control"
        else:
            return "diffusion_limited"
    
    def _assess_resistance_quality(self, resistance: float, current_change: float) -> str:
        """Assess resistance calculation quality."""
        if abs(current_change) < 1e-6:
            return "invalid"
        elif abs(resistance) > 1000:  # > 1kΩ seems unrealistic for battery
            return "poor"
        elif abs(resistance) < 0.001:  # < 1mΩ seems too low
            return "poor"
        else:
            return "good"
    
    def _summarize_relaxation_kinetics(self, kinetics: List[RelaxationKinetics]) -> Dict[str, Any]:
        """Summarize relaxation kinetics results."""
        if not kinetics:
            return {}
        
        voltage_kinetics = [k for k in kinetics if k.variable_type == 'voltage']
        current_kinetics = [k for k in kinetics if k.variable_type == 'current']
        
        summary = {
            'total_fits': len(kinetics),
            'voltage_fits': len(voltage_kinetics),
            'current_fits': len(current_kinetics),
            'average_r_squared': np.mean([k.r_squared for k in kinetics]) if kinetics else 0.0
        }
        
        if voltage_kinetics:
            summary['voltage_time_constants'] = [k.time_constant for k in voltage_kinetics if k.time_constant]
            summary['voltage_equilibrium_range'] = [
                min(k.equilibrium_value for k in voltage_kinetics),
                max(k.equilibrium_value for k in voltage_kinetics)
            ]
        
        return summary
    
    def _summarize_resistance_analysis(self, resistances: List[ResistanceAnalysis]) -> Dict[str, Any]:
        """Summarize resistance analysis results."""
        if not resistances:
            return {}
        
        valid_resistances = [r for r in resistances if r.ir_immediate_ohm is not None]
        if not valid_resistances:
            return {'valid_calculations': 0}
        
        resistance_values = [r.ir_immediate_ohm for r in valid_resistances]
        
        return {
            'valid_calculations': len(valid_resistances),
            'total_segments': len(resistances),
            'resistance_range_ohm': [min(resistance_values), max(resistance_values)],
            'mean_resistance_ohm': np.mean(resistance_values),
            'std_resistance_ohm': np.std(resistance_values)
        }
    
    def _track_equilibrium_evolution(self, equilibrium_results: List[EquilibriumAnalysis]) -> Dict[str, Any]:
        """Track equilibrium voltage evolution over time."""
        if not equilibrium_results:
            return {}
        
        equilibrium_voltages = [e.voltage_infinity for e in equilibrium_results if e.voltage_infinity]
        drift_rates = [e.voltage_drift_mv_min for e in equilibrium_results if e.voltage_drift_mv_min]
        
        evolution = {}
        if equilibrium_voltages:
            evolution['voltage_evolution'] = {
                'initial_v': equilibrium_voltages[0],
                'final_v': equilibrium_voltages[-1],
                'range_v': [min(equilibrium_voltages), max(equilibrium_voltages)],
                'trend': 'increasing' if equilibrium_voltages[-1] > equilibrium_voltages[0] else 'decreasing'
            }
        
        if drift_rates:
            evolution['stability_metrics'] = {
                'mean_drift_mv_min': np.mean(drift_rates),
                'max_drift_mv_min': max(drift_rates),
                'stable_segments': len([e for e in equilibrium_results if e.stability_achieved])
            }
        
        return evolution
    
    def _interpret_relaxation_kinetics(self, kinetics: List[RelaxationKinetics]) -> Dict[str, str]:
        """Provide electrochemical interpretation of relaxation kinetics."""
        if not kinetics:
            return {'interpretation': 'No relaxation data available'}
        
        interpretations = {}
        
        # Count diffusion regimes
        regimes = [k.diffusion_regime for k in kinetics]
        regime_counts = {regime: regimes.count(regime) for regime in set(regimes)}
        
        if regime_counts.get('diffusion_limited', 0) > len(kinetics) * 0.5:
            interpretations['dominant_process'] = 'Diffusion-limited relaxation dominates'
        elif regime_counts.get('fast_kinetics', 0) > len(kinetics) * 0.5:
            interpretations['dominant_process'] = 'Fast charge transfer kinetics'
        else:
            interpretations['dominant_process'] = 'Mixed kinetic and diffusion control'
        
        # Quality assessment
        good_fits = len([k for k in kinetics if k.relaxation_quality in ['excellent', 'good']])
        if good_fits > len(kinetics) * 0.7:
            interpretations['data_quality'] = 'High quality relaxation data suitable for analysis'
        else:
            interpretations['data_quality'] = 'Moderate quality data, interpret with caution'
        
        return interpretations
    
    def _interpret_resistance_analysis(self, resistances: List[ResistanceAnalysis]) -> Dict[str, str]:
        """Provide electrochemical interpretation of resistance analysis."""
        if not resistances:
            return {'interpretation': 'No resistance data available'}
        
        valid_resistances = [r for r in resistances if r.calculation_quality == 'good']
        if not valid_resistances:
            return {'interpretation': 'No reliable resistance calculations'}
        
        resistance_values = [r.ir_immediate_ohm for r in valid_resistances]
        mean_resistance = np.mean(resistance_values)
        
        interpretations = {}
        
        if mean_resistance < 0.01:  # < 10mΩ
            interpretations['resistance_level'] = 'Low resistance - good ionic conductivity'
        elif mean_resistance < 0.1:   # < 100mΩ
            interpretations['resistance_level'] = 'Moderate resistance - typical for battery systems'
        else:
            interpretations['resistance_level'] = 'High resistance - may indicate aging or poor contact'
        
        # Consistency check
        resistance_std = np.std(resistance_values)
        if resistance_std / mean_resistance < 0.1:  # CV < 10%
            interpretations['consistency'] = 'Consistent resistance values across measurements'
        else:
            interpretations['consistency'] = 'Variable resistance - check measurement conditions'
        
        return interpretations
    
    def _interpret_equilibrium_analysis(self, equilibrium_results: List[EquilibriumAnalysis]) -> Dict[str, str]:
        """Provide electrochemical interpretation of equilibrium analysis."""
        if not equilibrium_results:
            return {'interpretation': 'No equilibrium data available'}
        
        stable_count = len([e for e in equilibrium_results if e.stability_achieved])
        total_count = len(equilibrium_results)
        
        interpretations = {}
        
        if stable_count > total_count * 0.8:
            interpretations['stability_assessment'] = 'Good equilibrium stability achieved'
        elif stable_count > total_count * 0.5:
            interpretations['stability_assessment'] = 'Moderate equilibrium stability'
        else:
            interpretations['stability_assessment'] = 'Poor equilibrium stability - consider longer rest times'
        
        # Voltage evolution
        equilibrium_voltages = [e.voltage_infinity for e in equilibrium_results if e.voltage_infinity]
        if len(equilibrium_voltages) > 1:
            voltage_change = abs(equilibrium_voltages[-1] - equilibrium_voltages[0])
            if voltage_change > 0.1:  # > 100mV change
                interpretations['voltage_evolution'] = 'Significant equilibrium voltage changes - indicates state evolution'
            else:
                interpretations['voltage_evolution'] = 'Stable equilibrium voltage - consistent electrochemical state'
        
        return interpretations
    
    def _summarize_current_decay(self, decay_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize current decay analysis."""
        if not decay_results:
            return {}
        
        time_constants = [d['time_constant_s'] for d in decay_results if d.get('time_constant_s', 0) > 0]
        r_squared_values = [d['r_squared'] for d in decay_results]
        
        summary = {
            'total_decays': len(decay_results),
            'average_r_squared': np.mean(r_squared_values) if r_squared_values else 0.0
        }
        
        if time_constants:
            summary['time_constant_range_s'] = [min(time_constants), max(time_constants)]
            summary['mean_time_constant_s'] = np.mean(time_constants)
        
        return summary
    
    def _interpret_current_decay(self, decay_results: List[Dict[str, Any]]) -> Dict[str, str]:
        """Interpret current decay kinetics."""
        if not decay_results:
            return {'interpretation': 'No current decay data available'}
        
        interpretations = {}
        
        time_constants = [d['time_constant_s'] for d in decay_results if d.get('time_constant_s', 0) > 0]
        if time_constants:
            mean_tau = np.mean(time_constants)
            if mean_tau < 10:
                interpretations['decay_kinetics'] = 'Fast current decay - charge transfer limited'
            elif mean_tau < 100:
                interpretations['decay_kinetics'] = 'Moderate current decay - mixed processes'
            else:
                interpretations['decay_kinetics'] = 'Slow current decay - diffusion limited'
        
        good_fits = len([d for d in decay_results if d.get('decay_quality') in ['excellent', 'good']])
        if good_fits > len(decay_results) * 0.7:
            interpretations['fit_quality'] = 'Good exponential fits - reliable kinetic analysis'
        else:
            interpretations['fit_quality'] = 'Variable fit quality - interpret kinetics cautiously'
        
        return interpretations
    
    def _resistance_to_dict(self, resistance: ResistanceAnalysis) -> Dict[str, Any]:
        """Convert ResistanceAnalysis to dictionary using analytics_config field names."""
        return {
            'segment_id': resistance.segment_id,
            'technique': resistance.technique,
            'ir_immediate_ohm': resistance.ir_immediate_ohm,
            'ir_10s_ohm': resistance.ir_10s_ohm,
            'ir_30s_ohm': resistance.ir_30s_ohm,
            'current_pulse_a': resistance.current_pulse_a,
            'voltage_change_v': resistance.voltage_change_v,
            'pulse_duration_s': resistance.pulse_duration_s,
            'calculation_quality': resistance.calculation_quality
        }
    
    def _kinetics_to_dict(self, kinetics: RelaxationKinetics) -> Dict[str, Any]:
        """Convert RelaxationKinetics to dictionary for consistent API output."""
        return {
            'segment_id': getattr(kinetics, 'segment_id', 'unknown'),
            'technique': kinetics.technique,
            'variable_type': kinetics.variable_type,
            'fit_type': kinetics.fit_type,
            'equilibrium_value': kinetics.equilibrium_value,
            'amplitude': kinetics.amplitude,
            'time_constant': kinetics.time_constant,
            'sqrt_coefficient': kinetics.sqrt_coefficient,
            'r_squared': kinetics.r_squared,
            'rmse': kinetics.rmse,
            'data_points': kinetics.data_points,
            'relaxation_quality': kinetics.relaxation_quality,
            'diffusion_regime': kinetics.diffusion_regime
        }

    def _equilibrium_to_dict(self, equilibrium: EquilibriumAnalysis, diffusion_coeff: Optional[float] = None) -> Dict[str, Any]:
        """Convert EquilibriumAnalysis to dictionary using analytics_config exponential_fit schema."""
        return {
            'segment_id': equilibrium.segment_id,
            'technique': equilibrium.technique,
            'start_voltage_v': equilibrium.start_voltage_v,  # Context
            'end_voltage_v': equilibrium.end_voltage_v,      # Context
            'voltage_infinity': equilibrium.voltage_infinity,         # Analytics config
            'time_constant_s': equilibrium.time_constant_s,           # Analytics config
            'voltage_amplitude': equilibrium.voltage_amplitude,       # Analytics config
            'r_squared': equilibrium.r_squared,                       # Analytics config
            'voltage_drift_mv_min': equilibrium.voltage_drift_mv_min, # Supplementary
            'stability_achieved': equilibrium.stability_achieved,     # Supplementary
            'stability_time_s': equilibrium.stability_time_s,         # Supplementary
            'diffusion_coefficient_cm2_s': diffusion_coeff            # Calculated on-the-fly
        }


# Global instance
_electrochemical_insights = ElectrochemicalInsights()

def get_electrochemical_insights() -> ElectrochemicalInsights:
    """Get global electrochemical insights instance."""
    return _electrochemical_insights