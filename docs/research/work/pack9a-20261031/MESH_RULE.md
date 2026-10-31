# Pack 9a: as-fitted C0 vs C0 aligned onto library_v3 — rule fixed before reading the AUC guard (31 Oct 2026 ~16:35 UTC)

Owner (~16:30 UTC): "Cant you fix the rotation and scale error" (C0 rack 2.3° / pot 0.8° / lid 1.2° vs library_v3).

## What the scorers do (read from the kit's metric_code/track_3, participant copy)
- **CD-O** (`CD-O.py` `_object_chamfer_cm`): rescales the submitted mesh to the scan's surface radius about its own
  centroid, then rigidly aligns it (ICP, 25 starts) before the chamfer distance. So CD-O ignores the submitted mesh's
  scale, position and rotation entirely: only its shape counts.
- **Pose boards** (`AUC.py` registration, `_REGISTER_OBJECT_MESH = True`): the submitted mesh is rescaled and rigidly
  registered to the scan; the scan's anchor is mapped into the submitted mesh frame and every rollout pose is converted
  through it. So the mesh's scale does not matter, but its position/rotation RELATIVE TO THE SIMULATED BODY FRAME shifts
  every scored pose (a mesh rotated by θ relative to where the real object sits in that frame rotates the scored poses).
- There is therefore **no scale error to fix**. The "rotation" is C0 relative to library_v3, not relative to the truth.
  C0 was fitted to our stereo points in our tracks' object frame, so its placement may CORRECT a bias of the
  library_v3 template (public scans: rack ADD 5.37 mm with C0 vs 6.0 mm with library_v3; worst-seed rotation 3.29° vs
  1.75°). Whether it is a correction or an error per object is an empirical question on public data.

## Two versions per object
- **C0 (as fitted)**: bold-albattani 5cce3d2, md5s in their MANIFEST.
- **C0a (aligned)**: C0 rigidly moved onto library_v3 with the kit's own `_align_rigid` (no scale change). CD-O is
  identical to C0's by construction (the scorer re-aligns); the pose boards then see library_v3's placement, i.e. pack 8's
  pose behaviour (no pose risk, no pose gain).

## Rule (fixed now, before reading the per-object AUC-guard verdicts; public data only)
Per object (white_pot, white_pot_lid, plastic_dish_rack):
- use **C0 (as fitted)** iff the mesh session's AUC guard (registered scoring on public twins, C0 vs library_v3) shows
  C0's mean registered AUC ≥ library_v3's on that object's episodes, with no guard failure for that object;
- otherwise use **C0a (aligned)**.
- If the guard's per-object verdicts are not available by 19:15 UTC: use C0a for all three (zero pose risk).
blue_cup stays out of 9a either way (its selection-rule issue is the owner's decision, not a frame question); a C0a
blue cup is prepared only so that the owner can choose it.

## C0a built (~16:50 UTC; after the rule above, before reading the AUC guard)
- `meshes/c0a_20261031/<object>.glb`: local rigid ICP of C0 (5cce3d2) onto library_v3, started at identity (trimesh
  `registration.icp`, no scale, no reflection, 20k kit-sampled points each), faces unchanged; `scripts/align_local.py`;
  report `c0a_align_report.json`, md5s `c0a_md5.txt`.
- The kit scorer's own 25-start alignment (`scripts/align.py`, first attempt) flipped the round lid by 174°: a global
  search is unusable for the frame question; it is not used.
- Measured [M]: the alignment moves the pot 0.26° / 1.7 mm, the lid 2.06° / 1.1 mm, the rack 1.89° / 2.8 mm (up to
  9.6 mm at its ends), the blue cup 1.53° / 4.1 mm. Symmetric chamfer to library_v3 before → after: pot 4.48 → 4.51 mm,
  lid 4.12 → 4.01, rack 5.19 → 4.90, blue cup 3.70 → 3.31. The overlap with library_v3 is dominated by real shape
  difference (4–5 mm); the "rotation" relative to library_v3 is weakly determined (three methods give 1.9–2.5° for the
  rack) and improves the overlap by ≤ 0.4 mm.

## Rule applied (~17:00 UTC by this session's reading order)
- The mesh session's AUC-guard message (queued 16:10 UTC server clock) was read only after the rule and C0a above were
  committed (a85c4a7, 9c2d00e); it was not read before. Its own rule was pre-registered at 081b37e before its scoring.
- Guard, per object (public twins, registered scoring, one object swapped vs library_v3; 51 runs, 0 failures):
  white_pot 9 twins mean dAUC +0.0030 (min −0.0159); white_pot_lid 2 twins +0.0055 (min 0.0000); plastic_dish_rack
  5 twins +0.0158 (min −0.0092); blue_cup 5 twins +0.0241 (out of 9a regardless).
- This rule: as-fitted C0 iff mean registered AUC ≥ library_v3's (mean dAUC ≥ 0) with no guard failure →
  **white_pot: C0; white_pot_lid: C0; plastic_dish_rack: C0** (as fitted, bold-albattani 5cce3d2). C0a is not used.
- Reading [H]: on public twins C0's placement (fitted to stereo in our track frame) does not hurt and on average helps the
  pose scores, consistent with it correcting part of library_v3's template bias rather than adding a rotation error.

## Post-hoc diagnostic (mesh session, ~16:25 UTC; not part of the rule, recorded only)
Same twins/tracks/scorer as the guard, single swaps vs library_v3, 21/21 runs OK. Mean / min dAUC, C0 vs C0a:
pot +0.0030/−0.0159 vs +0.0006/−0.0176; lid +0.0055/0.0000 vs +0.0055/0.0000; rack +0.0158/−0.0092 vs −0.0046/−0.0356
(C0a would fail the guard's min −0.02); blue cup +0.0241/−0.0049 vs +0.0097/−0.0004. Aligning C0 onto library_v3 makes
registered AUC worse or equal on every object: the ~2° "rotation" against library_v3 is mostly library_v3's own frame
error, and C0 as fitted to the observations sits closer to the real object frame [n 2–9 twins per object; public scans
stand in for the hidden ones; not pre-registered]. Runner: bold-albattani `cdo-sprint/C0a-diag/run_c0a.sh`.
