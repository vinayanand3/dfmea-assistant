# BIW Launch Issue Summaries (Synthetic Excerpts)

Issue LI-2201: During P2 launch, spot weld splash at rocker-to-floor joint caused
sealer skips; corrosion audit flagged the joint. Resolution: weld schedule tuning
and sealer robot re-path. Lesson: audit sealer coverage after any weld parameter change.

Issue LI-2214: P1 front rail bulkhead missing in 3% of bodies due to feeder jam;
crash-relevant part. Resolution: added poka-yoke presence sensor and torque trace.
Lesson: crash-relevant internal reinforcements need error-proofed verification.

Issue LI-2230: P2 battery tray fastener torque failures traced to paint on weld nuts.
Resolution: masking added before e-coat. Lesson: verify fastener interfaces are
paint-free by design, not by process discipline.
