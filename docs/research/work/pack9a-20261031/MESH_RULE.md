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
