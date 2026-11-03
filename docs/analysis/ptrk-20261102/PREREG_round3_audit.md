# Pre-registration: round-3 pose CV and the eval gross-failure audit (3 Nov 2026, 06:55 UTC)

Owner's word via keen-heisenberg (06:30 UTC): "go in all". Written and pushed before any score of either task.

## (1) Round 3 pose-board mesh CV ($0, CPU)
Same as PREREG_round2.md (a), with these changes:
- **Baseline:** pack 14p's meshes, decoded from its submission parquet. For the public scoring, 14p's eval-20-only
  pitcher placement does not apply to public episodes; the pitcher stays the 13p payload.
- **Candidates:** the coordinator's G3 list (board 1 hy21 ep24 s123; dust pan Pixal3D-MV ep39 s2025; board 2 sam3d
  ep24 #43; G3 pot trellis2 ep45), plus near-misses from bold-albattani's manifest.
- **Rule:** nested leave-one-episode-out, 10-seed means, held-out mean ≥ +0.005, no held-out episode below −0.01, D1
  (both modes via focused-pascal before packing).

## (2) Eval gross-failure audit (GT-free; GPU ≤ $6 for SAM2 masks)
- **Inputs per eval episode:**
  - the PACKED reference's object poses (per perfect-following's packed_refs for 14p), mapped to the camera frame by
    inv(world_T_cam) · inv(T_table);
  - the eval stereo depth cache;
  - SAM2 video masks from `ops/jobs/eval_vos.sh` (same perception defaults, frame-0 detection of that run);
  - the reference's hand joints for the hand mask.
- **Per object and frame** (`scripts/eval_audit.py`), with the object rendered at the reference pose (library_v3
  template, projected silhouette, surface-point depths):
  - IoU(silhouette, own mask) over the unoccluded part (hand pixels removed);
  - best IoU with any other object's mask (swap check);
  - robust depth residual (median |z_obs − z_point| over visible points, cm);
  - lowest surface point below the table plane (cm);
  - visible fraction.
- **Flags (fixed now):**
  - LOST: IoU < 0.2 while the mask has ≥ 300 px, or depth residual > 3 cm, for ≥ 5 consecutive frames;
  - SWAP: the IoU with another object's mask exceeds the own IoU by 0.3 for ≥ 5 frames;
  - BELOW: lowest point < −2 cm for ≥ 5 frames;
  - FLIP: the reference rotation jumps > 60° within 3 frames while the mask IoU drops;
  - WRIST (spoon only): the reference within 2 cm of the wrist, with IoU < 0.2.
- **Severity:** frames flagged × object weight (all objects count equally) per episode; ranked table, overlays for the
  top flags.
- **Report only;** no fix is applied. The coordinator chooses targets for re-tracking (option C). Thresholds are not
  tuned after seeing eval data. Any change to them is logged as an addendum with its reason, and both versions are
  reported.

## Addendum 1 (08:35 UTC, before scoring this candidate)
**Source-episode rule (coordinator, 08:20 UTC):** a candidate's generation-source episodes are excluded from its
held-out scoring, in this and all future CV rounds.

**Board 2 outer shell of G3 #43** (bold-albattani, `C4-audit/meshes_outer/wooden_piece_2_outer.glb` @ da10a423, md5
34152d97…; source ep24):
- the only non-source public episode is ep23, so no candidate selection takes place;
- **pass** if the gain vs 14p on ep23 is ≥ +0.005 (10-seed mean);
- ep24 is scored and reported as in-sample only.

One-episode evidence is weak, and the verdict says so.
