ActionId and Segment Mapping - System Summary
The Problem
VersaStudio .par files contain two key identifiers that need to be understood for proper data analysis:

ActionId: Internal execution counter that increments with every action execution
Segment #: Maps to the original Action definitions in the experiment

The Discovery
From analyzing the experiment structure and plotting ActionId vs Segment data:
ActionId Behavior

Increments sequentially for every executed action step
When loops run, each iteration gets new ActionId values
Creates clusters in the data corresponding to different experimental phases
Not easily decodable without parsing the full experiment structure

Segment # Behavior

Direct mapping to Action definitions (Action1 → Segment 1, Action2 → Segment 2, etc.)
Consistent across loop iterations (Action4 in Loop #1 iteration 1,2,3... all have Segment 4)
Skips loop container actions (Action3 and Action8 are loop containers, not executed actions)

The Mapping Logic
Segment → Technique Mapping (Stable)
Segment 1  → Action1  → Initial OCV measurement
Segment 2  → Action2  → Initial EIS characterization  
Segment 4  → Action4  → Discharge pulse (in Loop #1)
Segment 5  → Action5  → Rest recovery (in Loop #1)
Segment 6  → Action6  → EIS characterization (in Loop #1)
Segment 7  → Action7  → Short rest (in Loop #1)
Segment 9  → Action9  → Long discharge (in Loop #2)
Segment 10 → Action10 → Long rest (in Loop #2)
Segment 11 → Action11 → EIS characterization (in Loop #2)
Segment 12 → Action12 → Short rest (in Loop #2)
Segment 13 → Action13 → Final OCV measurement
ActionId → Iteration Tracking (Dynamic)

ActionId sequence within each Segment # indicates iteration number
Example: Segment 4 might have ActionId values [32, 72, 112, 152...] representing iterations 1, 2, 3, 4... of the discharge pulse

Implementation Strategy
Two-Level Data Organization

Primary grouping by Segment # → Identifies technique type (universal across experiments)
Secondary grouping by ActionId sequence → Identifies iteration number within that technique

Data Processing Pipeline

Parse Segment # to identify technique type using stable mapping
Use ActionId sequence within each Segment # to determine iteration numbers
Create derived columns: technique_type, iteration_number
Enable analysis like: "Compare iteration 5 rest recovery between Loop #1 and Loop #2"