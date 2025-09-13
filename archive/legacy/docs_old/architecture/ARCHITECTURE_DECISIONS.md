# Architecture Decisions Log

**Project:** Registry-Based Analytics System Refactor  
**Branch:** `dev-clean-registry`

## Decision Format
Each decision includes: **Context** → **Decision** → **Rationale** → **Consequences**

---

## ADR-001: Registry-Based Analytics Architecture
**Date:** August 24, 2025  
**Status:** Accepted

**Context:**
Current system has 15+ specialized API methods (get_electrochemical_resistance_analysis, get_electrochemical_rest_analysis, etc.) with different return formats, causing 2+ days of UI debugging per new analysis type.

**Decision:**
Replace specialized methods with unified registry-driven system where:
- Registry maps analysis types to calculation methods
- All analytics return standard DataFrame format
- UI routing uses registry lookups instead of if/elif chains

**Rationale:**
- Recent Tab 3 debugging took 1.5 days due to data structure inconsistencies
- Registry eliminates routing duplication across 5+ UI files
- Standard DataFrame format prevents format mismatches
- Focus shifts to electrochemical algorithms vs software plumbing

**Consequences:**
- **Positive**: 30-minute new analysis development, unified data flow, maintainable codebase
- **Negative**: Major refactor required, potential short-term instability
- **Mitigation**: Phased implementation keeping old methods during transition

---

## ADR-002: DataFrame-First Data Flow
**Date:** August 24, 2025  
**Status:** Accepted

**Context:**
Current system uses inefficient dict → dataclass → dict → DataFrame transformations that caused recent synchronization bugs (62 vs 56 array lengths).

**Decision:**
Implement DataFrame-first approach:
- Database queries use `pd.read_sql()` directly
- Calculations operate on DataFrames
- UI consumes DataFrames without transformation
- Standard columns: `time_s | value | group_id | segment_id | analysis_type | quality_score | technique | unit`

**Rationale:**
- Eliminates data transformation overhead
- Prevents array synchronization issues we just debugged
- Leverages pandas ecosystem for analytics
- Simpler debugging and data inspection

**Consequences:**
- **Positive**: Fewer bugs, better performance, easier debugging
- **Negative**: Some complex nested data may need flattening
- **Mitigation**: Custom methods can still return complex structures when needed

---

## ADR-003: Smart Registry Router Pattern
**Date:** August 24, 2025  
**Status:** Accepted

**Context:**
Need to support both generic analytics AND custom/specialized analysis methods within unified system.

**Decision:**
Registry acts as intelligent router that can dispatch to:
- Generic DataFrame-based methods for standard analytics
- Custom specialized methods for complex analysis
- Registry configuration determines which method to call

**Rationale:**
- Flexibility to handle both simple and complex analytics
- Gradual migration path from specialized to generic methods
- Custom electrochemical analysis can use specialized approaches when needed

**Consequences:**
- **Positive**: Best of both worlds - automation + flexibility
- **Negative**: Registry becomes critical infrastructure
- **Mitigation**: Comprehensive testing and clear documentation

---

## ADR-004: Preserve UI Patterns, Replace Routing Logic
**Date:** August 24, 2025  
**Status:** Accepted

**Context:**
Existing Panel UI patterns work well (widgets, layouts, styling), but routing logic (if/elif chains) is duplicated and error-prone.

**Decision:**
During refactor:
- **PRESERVE**: Panel widgets, layouts, event handlers, styling, status updates
- **REPLACE**: if/elif routing chains with registry lookups
- **PRESERVE**: Helper methods and UI patterns that work
- **REPLACE**: Dictionary navigation with DataFrame operations

**Rationale:**
- UI investment should be preserved
- Routing logic is the actual source of bugs and maintenance issues
- Panel patterns are mature and functional

**Consequences:**
- **Positive**: Faster refactor, preserved UI quality, reduced risk
- **Negative**: Some UI code may look inconsistent initially
- **Mitigation**: Gradual cleanup of preserved patterns where beneficial

---

## Pending Decisions

### PD-001: LazyDataService Integration Strategy
**Context:** How should registry-based analytics integrate with existing LazyDataService?
**Options:** 
- Registry calls LazyDataService for raw data access
- Separate paths for segment-level vs raw data analytics
- Unified approach through registry

**Decision:** TBD during Phase 1 implementation

### PD-002: Error Handling and Propagation
**Context:** How should errors flow from calculation → registry → UI?
**Options:**
- Standard exceptions with registry handling
- Error columns in DataFrame returns
- Mixed approach based on error type

**Decision:** TBD during Phase 2 implementation

### PD-003: Custom Analysis Integration Pattern
**Context:** How should complex custom analyses integrate with registry?
**Options:**
- Registry calls specialized methods, converts results to DataFrame
- Custom methods implement DataFrame interface directly
- Hybrid approach with metadata columns

**Decision:** TBD when first custom analysis is implemented