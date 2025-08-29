# Segment Inspector Modal - Implementation Plan

## Overview
Implement point-and-click segment inspection in Explorer Tab that opens a Perspective modal with raw data + analytical metadata. Uses existing LazyDataService infrastructure with zero-copy Arrow format for optimal performance.

## Implementation Steps

### 1. Backend API Enhancement

**File: `src_clean/backend/api.py`**

Add new method to existing API class:

```python
def get_segment_data_for_perspective(self, segment_id: str, analysis_context: dict = None) -> bytes:
    """
    Get raw data + analytical metadata for segment inspection modal.
    
    Args:
        segment_id: Target segment ID from Explorer click
        analysis_context: Current Explorer state (technique, temperature, etc.)
        
    Returns:
        Arrow table bytes (zero-copy ready for Perspective)
    """
    try:
        # 1. Query LazyFrame for raw data (use existing LazyDataService)
        raw_data_df = self._query_segment_raw_data(segment_id)
        
        if raw_data_df.is_empty():
            logger.warning(f"No raw data found for segment {segment_id}")
            return self._create_empty_arrow_table()
        
        # 2. Add segment metadata (analytical results)
        enhanced_df = self._add_segment_metadata(raw_data_df, segment_id, analysis_context)
        
        # 3. Add analytical fits if requested
        if analysis_context and analysis_context.get('include_fits', True):
            enhanced_df = self._add_analytical_fits(enhanced_df, segment_id)
        
        # 4. Convert to Arrow for zero-copy transfer
        arrow_table = enhanced_df.to_arrow()
        
        logger.debug(f"Generated segment inspection data: {len(enhanced_df)} points, {len(enhanced_df.columns)} columns")
        return arrow_table
        
    except Exception as e:
        logger.error(f"Failed to get segment data for perspective: {e}")
        return self._create_empty_arrow_table()

def _query_segment_raw_data(self, segment_id: str) -> pl.DataFrame:
    """Query raw data for specific segment using existing LazyDataService."""
    # TODO: Implement using existing LazyDataService patterns
    # Reference: get_comprehensive_research_dataset_for_perspective method
    # Filter LazyFrame for specific segment_id and materialize
    pass

def _add_segment_metadata(self, raw_data_df: pl.DataFrame, segment_id: str, context: dict) -> pl.DataFrame:
    """Add analytical metadata as constant columns."""
    try:
        # Get segment analytics using existing registry system
        analytics = self._get_segment_analytics_summary(segment_id)
        
        # Add metadata as literal columns (efficient broadcast)
        enhanced_df = raw_data_df.with_columns([
            pl.lit(analytics.get('resistance_ohm', None)).alias('computed_resistance_ohm'),
            pl.lit(analytics.get('time_constant_s', None)).alias('computed_time_constant_s'),
            pl.lit(analytics.get('r_squared', None)).alias('fit_r_squared'),
            pl.lit(analytics.get('analysis_method', 'unknown')).alias('analysis_method'),
            pl.lit(analytics.get('cell_name', 'unknown')).alias('cell_name'),
            pl.lit(analytics.get('technique_name', 'unknown')).alias('technique_name'),
            pl.lit(segment_id).alias('segment_id'),
        ])
        
        # Add context-specific metadata if available
        if context:
            enhanced_df = enhanced_df.with_columns([
                pl.lit(context.get('temperature_c', None)).alias('temperature_c'),
                pl.lit(context.get('current_technique', 'All')).alias('explorer_technique_filter'),
            ])
        
        return enhanced_df
        
    except Exception as e:
        logger.warning(f"Failed to add segment metadata: {e}")
        return raw_data_df

def _add_analytical_fits(self, enhanced_df: pl.DataFrame, segment_id: str) -> pl.DataFrame:
    """Add analytical fit curves to raw data."""
    try:
        # Get fit parameters from analytics
        analytics = self._get_segment_analytics_summary(segment_id)
        fit_params = analytics.get('fit_parameters', {})
        fit_method = analytics.get('analysis_method', 'unknown')
        
        if not fit_params or fit_method == 'unknown':
            logger.debug(f"No fit parameters available for segment {segment_id}")
            return enhanced_df
        
        # Generate fit curve using existing patterns
        time_points = enhanced_df['time_s'].to_numpy()
        fit_curve = self._generate_fit_curve(time_points, fit_params, fit_method)
        
        if fit_curve is not None:
            # Add fit curve and residuals
            enhanced_df = enhanced_df.with_columns([
                pl.Series('fit_voltage_v', fit_curve),
                pl.Series('residual_voltage_v', enhanced_df['potential_v'] - fit_curve),
            ])
        
        return enhanced_df
        
    except Exception as e:
        logger.warning(f"Failed to add analytical fits: {e}")
        return enhanced_df

def _generate_fit_curve(self, time_points: np.ndarray, fit_params: dict, fit_method: str) -> np.ndarray:
    """Generate analytical fit curve based on stored parameters."""
    # TODO: Implement fit curve generation
    # Reference: existing analytics functions for fit parameter usage
    # Support: exponential_decay, linear, sqrt_diffusion, etc.
    pass

def _get_segment_analytics_summary(self, segment_id: str) -> dict:
    """Get analytical summary for segment using existing systems."""
    # TODO: Integrate with existing registry/analytics system
    # Reference: get_segment_analytics or similar existing methods
    # Return: dict with resistance, time_constant, r_squared, etc.
    pass

def _create_empty_arrow_table(self) -> bytes:
    """Create empty Arrow table for error cases."""
    empty_df = pl.DataFrame({
        'time_s': [],
        'potential_v': [],
        'error_message': ['No data available']
    })
    return empty_df.to_arrow()
```

### 2. Explorer Tab UI Enhancement

**File: `src_clean/panel_app/components/electrochemical_explorer_tab.py`**

Add click handling to existing Explorer tab:

```python
# Add to existing ElectrochemicalExplorerTab class

def _setup_plot_interactions(self):
    """Setup click handling for segment inspection."""
    # TODO: Implement click detection on existing plots
    # Reference: existing plot creation methods in this file
    # Add click handlers to hvplot scatter plots
    pass

def handle_segment_click(self, segment_id: str):
    """Handle click on segment point for raw data inspection."""
    try:
        # Extract current Explorer context
        analysis_context = self._extract_current_context()
        
        # Show loading indicator
        self._update_status("Loading segment data...", "info")
        
        # Call API for segment data
        arrow_data = self.api.get_segment_data_for_perspective(segment_id, analysis_context)
        
        # Open Perspective modal
        self._open_segment_inspector_modal(arrow_data, segment_id)
        
        self._update_status(f"Opened inspector for segment {segment_id}", "success")
        
    except Exception as e:
        logger.error(f"Failed to handle segment click: {e}")
        self._update_status(f"Error opening segment inspector: {str(e)}", "error")

def _extract_current_context(self) -> dict:
    """Extract current Explorer tab state for API context."""
    return {
        'selected_cells': self.selected_cells,
        'current_technique': self.current_technique,
        'temperature_c': getattr(self, 'current_temperature', None),
        'include_fits': True,  # Default to include analytical fits
        'plot_type': getattr(self, 'current_plot_type', 'scatter'),
        'explorer_tab': 'electrochemical_explorer'
    }

def _open_segment_inspector_modal(self, arrow_data: bytes, segment_id: str):
    """Open Perspective modal with segment data."""
    try:
        # Create Perspective pane with Arrow data (zero-copy)
        perspective_pane = pn.pane.Perspective(
            arrow_data,  # Direct Arrow bytes - zero copy!
            plugin="d3_xy_scatter",  # Start with scatter plot
            columns=["time_s", "potential_v"],  # X, Y axes
            settings=True,  # Allow user configuration
            width=1000,
            height=700,
            theme='pro'  # Professional theme
        )
        
        # Create modal content
        modal_content = pn.Column(
            pn.pane.HTML(f"<h3>🔬 Segment {segment_id} Inspector</h3>"),
            pn.pane.HTML("<p>Hover over points to see raw data + analytical metadata</p>"),
            perspective_pane,
            pn.Row(
                pn.widgets.Button(name="Export Data", button_type="primary"),
                pn.widgets.Button(name="Close", button_type="light"),
                sizing_mode='stretch_width'
            ),
            sizing_mode='stretch_width'
        )
        
        # Show modal using existing modal system
        self._show_modal(modal_content)
        
    except Exception as e:
        logger.error(f"Failed to open segment inspector modal: {e}")
        self._update_status("Error creating segment inspector", "error")

def _show_modal(self, content):
    """Show modal using existing UI patterns."""
    # TODO: Integrate with existing modal system in this file
    # Reference: existing modal patterns in ElectrochemicalExplorerTab
    pass
```

### 3. LazyDataService Integration

**File: `src_clean/backend/lazy_data_service.py`**

Add segment-specific query method:

```python
# Add to existing LazyDataService class

def get_segment_raw_data(self, segment_id: str) -> pl.DataFrame:
    """
    Get raw data for specific segment ID.
    
    Args:
        segment_id: Target segment identifier
        
    Returns:
        Raw electrochemical data for the segment
    """
    try:
        # TODO: Implement using existing query patterns
        # Reference: existing materialize_query_for_viz method
        # Filter for specific segment_id and return materialized data
        
        # Expected approach:
        # 1. Use existing query cache or create new query
        # 2. Apply segment_id filter
        # 3. Materialize and return DataFrame
        
        pass
        
    except Exception as e:
        self.logger.error(f"Failed to get segment raw data: {e}")
        raise
```

### 4. Testing and Integration Points

**Files to Reference for Existing Patterns:**

1. **API Patterns**: 
   - `src_clean/backend/api.py` - `get_comprehensive_research_dataset_for_perspective`
   - Follow existing error handling and logging patterns

2. **LazyFrame Usage**:
   - `src_clean/backend/lazy_data_service.py` - Existing query and materialization patterns
   - Use existing `with_columns` and filtering approaches

3. **Explorer UI Patterns**:
   - `src_clean/panel_app/components/electrochemical_explorer_tab.py` - Existing plot creation and interaction patterns
   - Follow existing status update and error handling patterns

4. **Perspective Integration**:
   - **PLACEHOLDER**: Reference existing Perspective modal implementation
   - Follow existing Arrow data handling patterns
   - Use existing modal UI patterns

5. **Analytics Integration**:
   - `src_clean/analysis/registry.py` - Existing analytics retrieval patterns
   - Follow existing segment analytics access methods

## Performance Considerations

### Zero-Copy Arrow Transfer
- **API Side**: Convert Polars DataFrame to Arrow bytes before return
- **UI Side**: Pass Arrow bytes directly to Perspective (no conversion)
- **Memory**: Single data structure from LazyFrame → Arrow → Perspective

### Query Optimization
- **Point-Based**: Single segment queries are inherently fast
- **LazyFrame**: Leverage existing caching and materialization strategies
- **Metadata**: Literal column addition is O(1) operation

### Error Handling
- **Graceful Degradation**: Empty Arrow table for missing data
- **User Feedback**: Clear status messages for loading and errors
- **Logging**: Comprehensive error tracking for debugging

## Implementation Order

1. **Backend API Method** - Core segment data retrieval
2. **LazyDataService Integration** - Raw data querying  
3. **Analytics Integration** - Metadata and fit curve addition
4. **Explorer UI Click Handling** - User interaction layer
5. **Perspective Modal** - Final display integration
6. **Testing and Polish** - Error cases and performance validation

## Success Criteria

- **Fast Response**: Segment data loads in <2 seconds
- **Rich Tooltips**: Hover shows raw data + analytical metadata
- **Zero-Copy Performance**: Efficient memory usage via Arrow
- **Scientific Accuracy**: Analytical metadata correctly associated with raw data
- **User Experience**: Intuitive click-to-inspect workflow