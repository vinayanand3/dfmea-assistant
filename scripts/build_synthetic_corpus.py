"""Build the synthetic knowledge-base corpus used to seed the local RAG store.

All content is synthetic demo data written in the style of prior-program BIW
engineering records. No confidential program data. Run from the repo root:

    python scripts/build_synthetic_corpus.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "data" / "knowledge_base"
OUT.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------- Historical DFMEA
DFMEA_ROWS = [
    # component, function, failure mode, effect, cause, prevention, detection, S, O, D, category, action
    ("P1 Front Rail Reinforcement", "Support front crash load path", "Crash load-path deformation or instability",
     "Occupant safety impact and unstable axial crush", "Insufficient section stiffness at rail-to-shotgun joint",
     "Crash CAE load-path review", "Frontal crash physical validation", 10, 3, 4, "Crash / Safety",
     "Added internal reinforcement bulkhead and increased weld density at node"),
    ("P1 Front Rail Reinforcement", "Maintain durability of welded joints", "Spot weld fatigue at rail flange",
     "Load transfer loss and durability degradation", "Weld pitch too coarse for cyclic torsional loads",
     "Weld layout review per weld standard", "Durability rig test with teardown", 8, 4, 4, "Joining / Durability",
     "Reduced weld pitch from 55 mm to 40 mm at high-strain zone"),
    ("P1 Rear Floor Crossmember", "Transfer rear impact and durability loads", "Fatigue crack at formed radius",
     "Crack propagation into floor panel", "3.5 mm radius created stress concentration above material limit",
     "CAE durability screening", "Physical durability test and dye-penetrant teardown", 8, 4, 5, "Durability",
     "Opened radius to 6 mm and added stiffening bead alongside"),
    ("P1 Rear Floor Crossmember", "Prevent corrosion at overlap joints", "Corrosion at flange overlap",
     "Perforation risk and long-term durability loss", "Water trap between flange layers with no drain path",
     "Drainage and sealer design review", "96-cycle corrosion test with sectioning", 7, 4, 5, "Corrosion",
     "Added 8 mm drain holes and revised sealer bead path"),
    ("P2 Shock Tower Reinforcement", "React suspension strut loads", "Fatigue crack at strut mounting holes",
     "Strut attachment stiffness loss, NVH degradation", "High local stress from undersized load-spread washer plate",
     "CAE fatigue review of attachment", "Road load durability test", 8, 4, 4, "Durability",
     "Enlarged washer plate and upgauged local reinforcement 1.6 to 2.0 mm"),
    ("P2 Shock Tower Reinforcement", "Maintain dimensional accuracy of strut mount", "Dimensional variation of strut tower position",
     "Wheel alignment drift and handling complaint", "Fixture locating scheme allowed tower lean during framing",
     "GD&T and locating strategy review", "Body build dimensional study (30 builds)", 6, 5, 4, "Dimensional",
     "Added net locating hole and revised framing sequence"),
    ("P2 B-Pillar Reinforcement", "Support side impact load path", "Side crash intrusion above target",
     "Occupant protection degraded in side impact", "Soft zone transition placed too low on pillar",
     "Crash CAE with hot-stamp soft zone modeling", "Side impact physical crash test", 10, 3, 4, "Crash / Safety",
     "Moved soft zone transition up 40 mm; verified by CAE correlation"),
    ("P2 B-Pillar Reinforcement", "Maintain weld integrity in UHSS", "Weld nugget cracking in ultra-high-strength steel",
     "Joint strength below spec, rework at plant", "Excessive electrode force and hold time for 1500 MPa PHS",
     "Weld schedule development per UHSS weld standard", "Peel test and nugget micrograph audit", 7, 4, 3, "Manufacturing Quality",
     "Adopted pulsed weld schedule; nugget size restored to 5.5 mm min"),
    ("P1 Rocker Reinforcement", "Absorb pole impact energy", "Rocker section collapse under pole load",
     "Battery protection margin reduced", "Foam-filled section replaced by empty section for cost",
     "Pole impact CAE study", "Pole impact sled test", 10, 2, 4, "Crash / Safety",
     "Reinstated aluminum extrusion insert at battery zone"),
    ("P1 Rocker Reinforcement", "Prevent corrosion in closed section", "Poor e-coat coverage inside rocker cavity",
     "Inner panel corrosion in service", "No vent path; e-coat drained before cure",
     "E-coat flow simulation", "E-coat coverage teardown study", 7, 3, 6, "Corrosion",
     "Added two 12 mm vent holes per e-coat standard EC-BIW-002"),
    ("P2 Battery Tray Crossmember", "Support battery pack mass and crash loads", "Bracket pull-out under vertical shock load",
     "Battery mount loosening, noise, durability risk", "Insufficient edge distance at fastener holes",
     "Attachment design review per fastener standard", "Pull-out test and shaker durability", 8, 3, 4, "Attachment / Durability",
     "Increased edge distance to 2.5x hole diameter and added emboss"),
    ("P2 Battery Tray Crossmember", "Seal battery compartment from road splash", "Water leak path at crossmember joint",
     "Battery compartment moisture ingress", "Sealer gap at three-layer joint intersection",
     "Sealer path design review", "Water test with UV dye trace", 9, 3, 5, "Corrosion",
     "Added butyl patch at T-joint and revised sealer robot path"),
    ("P1 Roof Rail Reinforcement", "Support roof crush load path", "Roof crush resistance below internal target",
     "Roof strength margin reduced", "Gauge reduction during weight program went too far",
     "Roof crush CAE gateway check", "Roof crush physical test", 9, 2, 4, "Crash / Safety",
     "Restored 1.4 mm gauge locally with tailor-rolled blank"),
    ("P1 Roof Rail Reinforcement", "Maintain roof ditch dimensional quality", "Roof ditch wrinkle during forming",
     "Visible surface defect, rework cost", "Insufficient blank holder pressure in ditch radius area",
     "Forming simulation of ditch area", "Tryout surface audit with highlight oil", 5, 5, 3, "Stamping / Formability",
     "Revised addendum geometry and blank holder pressure profile"),
    ("P1 Underbody Bracket", "Mount exhaust hanger to underbody", "Bracket fatigue crack at weld toe",
     "Exhaust system drop risk, warranty claim", "Weld toe stress riser combined with thermal cycling",
     "Weld fatigue review with hot-spot stress method", "Component durability rig with thermal cycle", 7, 5, 4, "Attachment / Durability",
     "Changed to wrap-around weld and increased bracket radius"),
    ("P2 Dash Panel Crossmember", "Support steering column and IP loads", "NVH boom from dash crossmember resonance",
     "Steering wheel shake complaint at idle", "First mode at 28 Hz coupled with engine idle order",
     "Modal CAE target check (>32 Hz)", "Vehicle modal test and subjective evaluation", 6, 4, 4, "NVH",
     "Added tuned brace to shift mode to 34 Hz"),
]

dfmea_df = pd.DataFrame(
    [
        {
            "Component": r[0], "Function": r[1], "Failure Mode": r[2], "Effect": r[3],
            "Cause": r[4], "Prevention Control": r[5], "Detection Control": r[6],
            "Severity": r[7], "Occurrence": r[8], "Detection": r[9],
            "RPN": r[7] * r[8] * r[9], "Risk Category": r[10], "Recommended Action": r[11],
            "Failure Mode ID": f"P-FM-{i+1:03d}", "Requirement ID": "REQ-" + r[10].split(" /")[0].split()[0].upper()[:5] + "-001",
            "Program": r[0].split()[0], "Source": "Synthetic prior-program record",
        }
        for i, r in enumerate(DFMEA_ROWS)
    ]
)
dfmea_df.to_excel(OUT / "historical_dfmea_biw.xlsx", sheet_name="DFMEA", index=False)

# --------------------------------------------------------------- Historical DVP&R
DVPR_ROWS = [
    ("P-FM-001", "Crash load-path deformation or instability", "P-TEST-001", "Frontal crash CAE correlation and physical barrier test",
     "CAE + Physical", "Vehicle", "Confirm axial crush mode and intrusion targets", "Crash pulse, intrusion, and deformation mode within targets",
     "BIW / Safety / CAE", "CR-BIW-001"),
    ("P-FM-002", "Spot weld fatigue at rail flange", "P-TEST-002", "Rail assembly durability rig with weld teardown",
     "Physical", "Subsystem", "Confirm weld fatigue life meets program durability target", "No weld failure before 100% target cycles",
     "BIW / Validation", "TS-DUR-BIW-014"),
    ("P-FM-003", "Fatigue crack at formed radius", "P-TEST-003", "Component durability test with strain-gauged radius",
     "CAE + Physical", "Component", "Confirm radius strain below fatigue limit", "No crack at 100% cycles; strain within CAE prediction +/-15%",
     "BIW / CAE / Validation", "TS-DUR-BIW-014"),
    ("P-FM-004", "Corrosion at flange overlap", "P-TEST-004", "96-cycle cyclic corrosion test with teardown sectioning",
     "Environmental", "Component", "Confirm no red rust at flange interfaces", "No perforation; cosmetic corrosion within limit after 96 cycles",
     "Materials / Corrosion", "TS-COR-021"),
    ("P-FM-005", "Fatigue crack at strut mounting holes", "P-TEST-005", "Road load data durability test on strut tower",
     "Physical", "Subsystem", "Confirm strut attachment survives RLD spectrum", "No crack initiation at 100% RLD cycles",
     "BIW / Validation", "TS-DUR-BIW-014"),
    ("P-FM-006", "Dimensional variation of strut tower position", "P-TEST-006", "30-build body dimensional capability study",
     "Manufacturing validation", "Subsystem", "Confirm strut tower position Cp/Cpk", "Cpk >= 1.33 on tower net points",
     "Dimensional Engineering", "DIM-BUILD-007"),
    ("P-FM-007", "Side crash intrusion above target", "P-TEST-007", "Side impact CAE correlation and physical crash test",
     "CAE + Physical", "Vehicle", "Confirm B-pillar intrusion and velocity targets", "Intrusion and door velocity within targets",
     "BIW / Safety / CAE", "CR-BIW-002"),
    ("P-FM-008", "Weld nugget cracking in ultra-high-strength steel", "P-TEST-008", "UHSS weld schedule qualification (peel + micrograph)",
     "Physical", "Coupon", "Qualify pulsed weld schedule for 1500 MPa PHS", "Nugget >= 5.5 mm, no cracks in 30-coupon sample",
     "Manufacturing / Quality", "WS-JOIN-003"),
    ("P-FM-009", "Rocker section collapse under pole load", "P-TEST-009", "Pole impact sled test with battery surrogate",
     "Physical", "Subsystem", "Confirm rocker intrusion protects battery zone", "Intrusion below battery clearance limit",
     "BIW / Safety", "CR-BIW-003"),
    ("P-FM-010", "Poor e-coat coverage inside rocker cavity", "P-TEST-010", "E-coat coverage teardown and film-build audit",
     "Environmental", "Component", "Confirm coverage in closed section", "Film build >= 10 um on 95% of internal surface",
     "Materials / Corrosion", "EC-BIW-002"),
    ("P-FM-011", "Bracket pull-out under vertical shock load", "P-TEST-011", "Fastener pull-out and shaker durability test",
     "Physical", "Component", "Confirm attachment strength under shock spectrum", "Pull-out force >= 1.5x max service load",
     "BIW / Validation", "FAST-BIW-005"),
    ("P-FM-012", "Water leak path at crossmember joint", "P-TEST-012", "Water test with UV dye and teardown",
     "Environmental", "Vehicle", "Confirm no moisture ingress to battery zone", "Zero dye trace inside compartment after 30 min spray",
     "BIW / Quality", "TS-SEAL-009"),
    ("P-FM-013", "Roof crush resistance below internal target", "P-TEST-013", "Roof crush quasi-static test",
     "Physical", "Vehicle", "Confirm strength-to-weight ratio target", "SWR >= internal target with margin",
     "BIW / Safety", "CR-BIW-004"),
    ("P-FM-014", "Roof ditch wrinkle during forming", "P-TEST-014", "Die tryout surface audit with highlight",
     "Manufacturing validation", "Component", "Confirm class-A adjacent surface quality", "No visible wrinkle under highlight oil audit",
     "Stamping / Quality", "FORM-TRY-002"),
    ("P-FM-015", "Bracket fatigue crack at weld toe", "P-TEST-015", "Component durability rig with thermal cycling",
     "Physical", "Component", "Confirm weld toe fatigue life with heat exposure", "No crack at 100% cycles incl. thermal soak blocks",
     "BIW / Validation", "TS-DUR-BIW-014"),
    ("P-FM-016", "NVH boom from dash crossmember resonance", "P-TEST-016", "Body modal test and idle NVH evaluation",
     "Physical", "Vehicle", "Confirm first mode above 32 Hz decoupled from idle", "Mode >= 32 Hz; subjective idle rating >= 7",
     "NVH", "NVH-MOD-005"),
]

dvpr_df = pd.DataFrame(
    [
        {
            "Linked Failure Mode ID": r[0], "Linked Failure Mode": r[1], "Test ID": r[2],
            "Recommended Validation Test": r[3], "Validation Type": r[4], "Validation Level": r[5],
            "Test Objective": r[6], "Acceptance Criteria": r[7], "Responsible Team": r[8],
            "Standard Reference": r[9], "Source": "Synthetic prior-program record",
        }
        for r in DVPR_ROWS
    ]
)
dvpr_df.to_excel(OUT / "historical_dvpr_biw.xlsx", sheet_name="DVPR", index=False)

# --------------------------------------------------------------- Lessons learned
LESSONS = [
    ("Front rail weld pitch", "Joining / Durability", "P1 front rail developed weld fatigue at 60% durability cycles.",
     "Weld pitch selected for static strength, not cyclic load", "Set weld pitch from fatigue CAE, not static margin; re-check after any load path change."),
    ("Formed radius fatigue", "Durability", "Rear crossmember cracked at 3.5 mm formed radius in P1 durability test.",
     "Radius below formability guideline for HSS at that gauge", "Keep formed radii >= 4t for HSS structural members; verify strain with forming simulation."),
    ("Flange drain path", "Corrosion", "P1 underbody flanges showed red rust at 40 cycles in corrosion test.",
     "Overlap flange trapped water with no drain", "Every horizontal overlap flange needs a drain path or full sealer coverage; review with corrosion team before data release."),
    ("E-coat venting", "Corrosion", "P1 rocker inner showed bare metal after e-coat.",
     "Closed section had no vent, coating drained before cure", "Apply e-coat standard EC-BIW-002 vent/drain hole pattern to all closed sections."),
    ("Soft zone location", "Crash / Safety", "P2 B-pillar intrusion exceeded target in first side crash test.",
     "Hot-stamp soft zone transition placed too low", "Lock soft zone location with crash CAE before die release; physical correlation mandatory."),
    ("UHSS weld schedule", "Manufacturing Quality", "P2 launch delayed by weld nugget cracks in 1500 MPa PHS.",
     "Standard weld schedule used for UHSS grade", "Qualify pulsed weld schedules per WS-JOIN-003 for any grade above 980 MPa before PV build."),
    ("Strut tower locating", "Dimensional", "P2 strut tower position drifted during framing, causing alignment complaints.",
     "Locating scheme allowed tower lean", "Use net locating hole on strut tower and audit with 30-build capability study."),
    ("Battery bracket edge distance", "Attachment / Durability", "P2 battery bracket pulled out in shaker test.",
     "Fastener edge distance only 1.6x hole diameter", "Maintain >= 2.5x hole diameter edge distance on battery attachments; add emboss for load spread."),
    ("Sealer three-layer joint", "Corrosion", "Water traced into P2 battery compartment at three-layer joint.",
     "Robot sealer path skipped T-joint intersection", "Add manual butyl patch at all three-layer T-joints; verify with UV dye water test."),
    ("Roof gauge weight program", "Crash / Safety", "P1 roof crush margin eroded by late gauge reduction.",
     "Weight action taken without re-running roof crush CAE", "Any gauge change on crash-relevant parts requires CAE gateway re-check before release."),
    ("Exhaust bracket weld toe", "Attachment / Durability", "P1 exhaust hanger bracket cracked at weld toe in service fleet.",
     "Weld toe stress riser plus thermal cycling", "Use wrap-around welds on hanger brackets; include thermal blocks in durability schedule."),
    ("Dash crossmember mode", "NVH", "P2 idle boom traced to dash crossmember first mode at 28 Hz.",
     "Modal target not checked after mass change", "Hold first mode >= 32 Hz on steering-support structure; re-check after any added mass."),
]

lessons_df = pd.DataFrame(
    [
        {
            "Lesson ID": f"LL-{i+1:03d}", "Title": r[0], "Risk Category": r[1],
            "Prior Issue": r[2], "Cause": r[3], "Lesson Learned": r[4],
            "Source": "Synthetic prior-program record",
        }
        for i, r in enumerate(LESSONS)
    ]
)
lessons_df.to_excel(OUT / "lessons_learned_biw.xlsx", sheet_name="Lessons", index=False)

# --------------------------------------------------------------- Standards excerpts
(OUT / "biw_weld_standard_ws_join_003.md").write_text("""# WS-JOIN-003 BIW Resistance Spot Weld Standard (Synthetic Excerpt)

Weld pitch for structural joints shall be derived from fatigue analysis, not static
strength alone. Minimum nugget diameter is 4 * sqrt(t) where t is the governing sheet
thickness. For steels above 980 MPa tensile strength, a pulsed weld schedule shall be
qualified by peel test and micrograph before PV build. Weld gun access shall be
verified in digital buyoff before die release. Flange width shall provide minimum
14 mm bearing for a 6 mm nugget class. Shunting through adjacent welds shall be
assessed when pitch is below 25 mm. Teardown audit frequency during launch is one
body side per shift minimum.
""")

(OUT / "biw_corrosion_standard_ts_cor_021.md").write_text("""# TS-COR-021 BIW Corrosion Protection Standard (Synthetic Excerpt)

All overlap flanges exposed to underbody splash shall have either a continuous sealer
bead or a defined drain path. Closed sections require vent and drain holes per e-coat
standard EC-BIW-002 (minimum two 12 mm holes positioned for full drainage in body
position). Cyclic corrosion validation is 96 cycles for underbody structural parts
with teardown sectioning at flange interfaces. Galvanic pairs (aluminum bracket on
steel structure) require isolation per materials guideline. No red rust is permitted
on structural sections before 60 cycles; perforation is not permitted at any point
in the test.
""")

(OUT / "biw_dimensional_standard_dim_build_007.md").write_text("""# DIM-BUILD-007 Body Dimensional Validation Standard (Synthetic Excerpt)

Structural net points require Cpk >= 1.33 demonstrated over a 30-build capability
study before PV signoff. Locating schemes shall follow 3-2-1 principle with net holes
on the primary load-carrying member. Framing sequence changes require a new capability
study. Strut towers, engine cradle mounts, and suspension attachment points are
classified as critical dimensional characteristics and require 100% in-line
measurement during launch ramp.
""")

(OUT / "launch_issue_reports_biw.md").write_text("""# BIW Launch Issue Summaries (Synthetic Excerpts)

Issue LI-2201: During P2 launch, spot weld splash at rocker-to-floor joint caused
sealer skips; corrosion audit flagged the joint. Resolution: weld schedule tuning
and sealer robot re-path. Lesson: audit sealer coverage after any weld parameter change.

Issue LI-2214: P1 front rail bulkhead missing in 3% of bodies due to feeder jam;
crash-relevant part. Resolution: added poka-yoke presence sensor and torque trace.
Lesson: crash-relevant internal reinforcements need error-proofed verification.

Issue LI-2230: P2 battery tray fastener torque failures traced to paint on weld nuts.
Resolution: masking added before e-coat. Lesson: verify fastener interfaces are
paint-free by design, not by process discipline.
""")

print(f"Corpus written to {OUT}")
for f in sorted(OUT.iterdir()):
    print(" -", f.name)
