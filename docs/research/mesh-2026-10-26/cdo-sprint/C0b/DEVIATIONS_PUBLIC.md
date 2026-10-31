# C0b public stage: implementation deviations and interpretations (PREREG section 3.10, last bullet)

Written before any C0b candidate was built or scored, and extended only with build facts, never after scoring. Each
item is an implementation detail the PREREG left open or a change found necessary by a dry run; none changes a
pre-registered value, candidate set, pick rule or threshold.

| # | Where | What the PREREG says | What the code does | Why |
|---|---|---|---|---|
| D1 | `obs_points.py --roi_cube` | ROI = cube of half-side 0.30 m about the track origin | frames whose cube corners are not all in front of the camera (z < 5 cm) use the whole image as the pixel window; the 3-D cube test still bounds the points. The library-box path keeps the old rule (frame skipped) | [M] dry run 1 (ep11, stride 8): with the old skip rule every frame was skipped (a 0.6 m cube about an object 0.4-0.7 m away always has corners behind or beside the camera) and obs_points produced no points |
| D2 | pass B, single-object episodes (39, 40, 41-45) | pass B = the final file with co-object carving | pass B is a copy of pass A (no co-object exists; the command would be identical and obs_points is deterministic) | saves 7 identical runs |
| D3 | cube guard | "if more than 0.1 % of a file's kept points lie within 8 mm of a cube face, that file is rebuilt once at 0.45 m" | applied to every pass-A and pass-B file independently; the rebuilt file's guard is recorded, not acted on | a pass-A file feeds the co-object carving, so it gets the same guard |
| D4 | thickness chain, merged blue cup (ep21+22) | "per build for multi-episode builds" | the pooled per-episode thickness.py measurements of ep21 and ep22 (as the rack rule), not thickness.py on the concatenated points | the concatenated points are not aligned between episodes; a two-sided measurement across them would measure the misalignment |
| D5 | markers `T` and sigma frames | T = the track length; frames = range(0, T, stride) | T = min over `world_T_cam` and every slot object's `cam_T_*` (gmg `bundle.from_obs_all`'s definition); stride from the file's own args (2) | the gmg convention |
| D6 | `attach(mesh, balls, obs)` | obs = the observed points | the builder's own points (1.5 mm voxel-downsampled, first point per voxel); `attach` voxelizes on the same 1.5 mm grid, so its point set is the same | one load per build |
| D7 | M_sep(own) | keep extraction frame t iff < half of B lies within 12 mm of any Q_p | B and Q_p posed in the camera frame of t (cam_T_*; equivalent to the world frame); frames evaluated = range(0, T, 2); the >= 10 kept-frames test counts kept extraction frames (kept frames with points are reported) | T1's census used world poses over all frames |
| D8 | option names (3.10) | `--markers_json`, `--attach`, ... | `--attach` is implied by the variant (fit / thick: posts by the stem rule; nostem: bare; nomk: none); added `--markers_obj` (object key in the markers json), lathe `--tmax` (the 8 mm upper clamp of step 4); a thickness argument of -1 means "needed but t0_C0b not fittable" and the build fails only if it needs it | PREREG 3.10 allows renaming with the meaning kept |
| D9 | reported-only fidelities | C0 and library_v3 fidelity on the same points | computed on the box in a separate stage after `selection.json` is written (`report/`) | keeps the pick process free of library_v3 |
| D10 | rack sigma | APP_D unused in prim_rack under C0b | the rack run gets no sigma; sigma of each rack episode is computed for the marker detector only | as PREREG 3.5 |
