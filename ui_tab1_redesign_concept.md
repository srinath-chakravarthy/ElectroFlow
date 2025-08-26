Original Problem

Cell manager tab felt clunky with cell info not being primary
Complex nested UI with expandable rows was confusing
File management was disconnected from cell context

Final Design Solution
We landed on a clean 2-panel unified approach:
┌─────────────────────────────────────────────┐ ┌─────────────────────────┐
│ CELLS & FILES (Perspective - Left Panel)   │ │ Data Preview Panel  │
│ ┌─────────────────────────────────────────┐ │ │ ┌─────────────────────┐ │
│ │[▼]CELL_001│Li-ion│2.5Ah│12 files│NMC811│ │ │ │ Plots         │ │
│ └─────────────────────────────────────────┘ │ │ └─────────────────────┘ │
├─────────────────────────────────────────────┤ └─────────────────────────┘
│ 📝 CREATE CELL     📁 ADD FILES           │
│ [Collapsible]      [Drop Zone]             │
└─────────────────────────────────────────────┘
Key Design Principles

Cell metadata is prominent - Perspective table as the star
Hierarchical tree view - cells with nested files in one interface
Cell-centric workflow - select cell → see files & segments
Single drop zone - dedicated file upload area
Side creation card - compact cell creation form
Clean 2-level hierarchy - no complex nested expandables