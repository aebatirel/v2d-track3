# Pre-registration: stage 1b, joint shape + pose fit of rest segments (13 Nov 2026)

Written and pushed before any stage-1b track exists or is scored. Owner: "okay lets do those see if we get any
improvements" (plan `docs/research/work/plan-20261113/PLAN.md`, step 1).

## Why (evidence)
- **Stage 1** (`DESIGN_offline_joint.md` and `PREREG_stage1.md` in `docs/analysis/ptrk-20261102/`, branch
  `claude/perception-tracking-20261102`):
  - one pose per rest segment by depth-only trimmed ICP against the fixed library template;
  - **FAILED**, −0.0088, with rest-frame ADD lower on only 9/20 episodes.
  - Its own reading: it helps where tracker bias is large (pitcher, rack) and hurts where the tracker is already
    within the mesh's shape error (pot, cups). "The limit is mesh shape."
- **Rest-frame oracle:** +0.032 mean AUC (ep24 +0.118, ep31 +0.112, ep11 +0.088, ep21 +0.083).
- **The Track 3 winner** (`docs/analysis/winner-richchentw-20261113/`):
  - a silhouette + depth tracker, and meshes fitted to silhouettes and stereo points by differentiable rendering;
  - their first upload (0.902) used that tracker without FoundationPose.
- **Hypothesis H-B1:** fitting the object's shape jointly with its rest-segment poses, against silhouettes (SAM2
  masks) and stereo depth over many views, removes the template-shape bias that defeated stage 1.
  - Falsifier: rest-frame ADD is not lower than the tracker's on most episodes.

## Method (GT-free; `docs/research/work/joint-fit-20261113/stage1b.py`)
Never reads a parquet, scan or mocap; input paths are asserted like stage 1.
- **Inputs:** the same as stage 1.
  - Control tracks C (`runs/20261102-ptrkA-7fbc3215/results/ptrk/C/ep<N>`, ep23 from ptrkD Cr; poses.npz with
    world_T_cam, det_f0.npz K).
  - Depth cache (`cache/depth/public/ep<N>/depths_fs0.5.npy`).
  - SAM2 video masks (`runs/20261102-ptrkD-95cecd7/results/ptrk/MRr/ep<N>/vos_masks.npz`).
  - Tracking templates = the scoring meshes: library_v3 with the pack 9a+ overrides (c0_pack9a, c1_pack9aplus).
- **Rest segments:** stage 1's rule (centroid speed < 0.5 cm/frame and turn < 2°/frame, 3-frame means, ≥ 10 frames;
  2 frames dropped at each end).
- **Unknowns per object:**
  - one shape correction shared by all its segments: scale along the template's 3 principal axes about its surface
    centroid, bounded to [0.85, 1.15];
  - one world pose per segment.
- **Residuals, frames sampled evenly, ≤ 6 per segment:**
  - **Depth:** observed points (mask ∩ dilated projected silhouette, eroded, as stage 1, ≤ 400 per frame) → distance
    to the shape-corrected template surface. Robust soft-L1, scale 5 mm.
  - **Silhouette precision:** 400 fixed surface samples projected. Distance in pixels to the nearest pixel of the
    object's mask or of any other object's mask (occluders excused), × depth / focal → metres. Soft-L1, 5 mm.
  - **Silhouette recall:** ≤ 150 boundary pixels of the object's mask → distance to the nearest projected surface
    sample, converted to metres the same way. Soft-L1, 5 mm. Occlusion only shrinks the mask, so this term
    tolerates it.
  - **Priors:** segment pose vs the tracker's middle-frame pose (σ 2 cm, 5°); log-scale vs 0 (σ 0.05).
- **Solver:** scipy least_squares (trf, soft_l1, numerical Jacobian with the block sparsity of shape × segments),
  ≤ 60 iterations.
- **Guards (as stage 1):** a segment keeps its tracker poses when
  - it has < 2 usable frames or < 300 depth points, or
  - the fit moves its middle-frame pose by > 3 cm or > 10°.

  The whole object keeps tracker poses and template shape when the robust cost does not fall.
- **Output:**
  - `poses_world_vo.npz`: rest segments replaced, 5-frame ramps to the tracker, moving frames unchanged;
  - `meshes/<obj>.glb`: the template with the fitted scale; unchanged objects copied.

  Scored with these per-episode meshes, because mesh and pose are coupled in the registered scorer (winner's lesson
  3).

## Development vs verdict
- Development, scores visible, tuning allowed: **ep21, ep11, ep31** (three of the largest oracle gains: pitcher +
  cup, two cups, sweeper).
- Then the code is **frozen**. Its sha256 is recorded in the work log before the 20-episode run.
- The verdict uses the frozen code on all 20 public episodes. The 17 non-development episodes are reported separately;
  they are the honest estimate.

## Scoring (after inference; mocap read only here)
`pipeline/score_registered.py` (perception-tracking version, reproduced exactly here: control ep21 0.8375 [M]).
- Kit `v2d_submission_kit.zip` sha256 7e1fdd00…; public scans; per frame.
- Control C scored with the pack 9a+ meshes; stage 1b scored with its per-episode fitted meshes.
- Also reported: control scored with the fitted meshes but tracker poses, to split the mesh effect from the pose
  effect.

## Gate (stage 1's, unchanged), stage 1b vs C over the 20 public episodes
1. mean ΔAUC ≥ +0.005;
2. no episode below −0.01;
3. rest-frame ADD (frames the arm changed) lower on ≥ 14 of 20 episodes;
4. mean ΔMPPE ≤ 0 and mean ΔRPE ≤ 0.

The same four numbers are reported for the 17 non-development episodes.
**Falsifier:** rest-frame ADD not lower on most changed segments.

## Cost
CPU in this container, $0. Depth is about 1–2.4 GB per episode, pulled from the store, used and deleted.
