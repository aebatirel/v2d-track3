# Mesh library v3 (2026-10-22)

`library_v2` plus one change: `mini_sweeper.glb` with its underside flattened by `pipeline/flatten_base.py`
(`--from_ref <ep18 reference> --object mini_sweeper --depth 0.008`: vertices within 8 mm of the lowest point along the
world up of our own ep18 frame-0 pose moved onto one plane 4 mm above it; 121 vertices; `mini_sweeper.flatten.json`).
Reason: our reconstruction's underside was rounded (the table hides it), 0.3 cm^2 footprint at the perceived resting
pose with the centre of mass 3 cm outside, so with the object assist off (official evaluation) the sweeper fell over in
4-5 steps while mocap has it standing. After flattening: 9.7 cm^2 footprint, centre of mass 4 mm inside; with
`contact_retarget --rest_settle 1` the sweeper stays within 0.7 deg for 9 steps (assist off, CPU), was 17.6 deg by
step 4. Experimental: validate on GPU (ep18) before using it for submissions.
