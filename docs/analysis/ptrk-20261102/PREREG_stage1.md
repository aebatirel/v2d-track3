# Pre-registration: Stage 1 of DESIGN_offline_joint.md: one pose per object per rest segment (2 Nov 2026)

Owner's word via keen-heisenberg (17:05 UTC): build and run Stage 1, public only; ≤ $4 GPU (separate from ptrkE);
stop if credit < $10. Written and pushed before any transformed track exists or is scored.

## Method (GT-free; `scripts/stage1.py`)
- **Base tracks:** the control C of the first batch (eval defaults; runs/20261102-ptrkA/B-7fbc3215 results/ptrk/C;
  ep23 from runs/20261102-ptrkD-95cecd7 Cr), with its own world_T_cam (VO camera arm).
- **Rest segments** (per object, from our track only):
  - centroid speed < 0.5 cm / frame and turn < 2° / frame (3-frame means; refine.py / object_events thresholds);
  - runs of ≥ 10 frames;
  - the first and last 2 frames of each run are dropped from the fit and kept as ramp frames.
- **Observations per segment frame t:**
  - stereo depth (store cache/depth/public, the same depth the tracker used);
  - pixels inside the object's SAM2 video mask (store runs/20261102-ptrkD-95cecd7 MRr vos_masks.npz, propagated from
    the same frame-0 detection), intersected with the 2-pixel-dilated projected silhouette of the tracked pose (drops
    mask failures), eroded 1 px at the mask resolution (400 × 250);
  - back-projected and moved to the world with world_T_cam[t];
  - every 2nd frame of the segment, at most 1500 points per frame.
- **Fit:** one world pose per segment, initialised at the tracked pose of the segment's middle frame. Trimmed ICP:
  - observed point to nearest mesh-surface point (library_v3 tracking template, 20 000 samples);
  - keep the 70 % smallest residuals each iteration;
  - point-to-point Kabsch update;
  - 40 iterations or until the update is < 0.1 mm / 0.01°.

  No Huber / Cauchy loss (coordinator: trimming).
- **Guards (fixed now):** a segment keeps its tracker poses when
  - fewer than 300 points are collected, or
  - the fit moves the middle-frame pose by > 3 cm or > 10°, or
  - the trimmed RMS residual after the fit is not lower than before it.
- **Output:** frames inside the segment get the fitted world pose. Over 5 frames on each side the pose blends linearly
  (position, slerp rotation) back to the tracker's. Moving frames are unchanged.
  `poses_world_vo.npz` is written per episode, and its sha256 is pushed before scoring.

## Arms
- **VO** (now): the cameras above.
- **MAP** (later, only if room-map's leave-episode-out fold cameras are ready): the same with those cameras, its own
  sha256 push before scoring.

## Gate (owner / coordinator, fixed now), each arm vs C, 20 public episodes
1. mean ΔAUC ≥ +0.005;
2. no episode below −0.01;
3. rest-frame ADD (mean symmetric ADD over the frames the arm changed, diagnostic) lower on ≥ 14 of 20 episodes
   (an episode with no changed frame counts as not lower);
4. mean ΔMPPE ≤ 0 and mean ΔRPE ≤ 0.

**Falsifier:** rest-frame ADD not lower on most changed segments.
Reference ceiling: the rest-frame oracle, +0.032 [D].

## Cost
CPU in this container, $0 (depth ≈ 2.2 GB per episode pulled from the store, processed, deleted). No GPU planned
unless CPU proves too slow.
