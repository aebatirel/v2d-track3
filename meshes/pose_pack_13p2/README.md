# Pose pack 13p2: eval-20 water_pitcher placed from depth (2 Nov 2026, tracking-perception session)

- **File:** `eval20_water_pitcher_placed.glb`, md5 fb2cb7eaac66699a33d2ec772732bafd. For eval 20, slot 1
  (water_pitcher) only.
- **What it is:** the pack-13p / 13f water_pitcher payload (decoded vertices / faces, 4096 faces, md5 of the decoded
  glb 49a173701c49b6295f3807e44fd1d4ca; payload zip 83276565…) with the transform Δ applied (mesh → tracker body
  frame, metres, row-major 4×4; also in `place_fit_ep20.json`):

      [[ 0.99879,   0.024607,  0.042591,  0.003503],
       [-0.024132,  0.999641, -0.011638,  0.002266],
       [-0.042862,  0.010596,  0.999025, -0.002092],
       [ 0,         0,         0,         1       ]]       (2.89°, 0.47 cm)

- **How it was produced (GT-free):** `docs/analysis/ptrk-20261102/scripts/place_fit.py` on eval 20.
  - Inputs:
    - the packed eval-20 reference body poses (packed_refs: run 20261025-evb1420-ee7ba8e,
      refs/glockt/ep20/.../ref_gl_ilc.parquet, mapped to the perception frame by inv(world_T_cam) · inv(T_table)), so
      Δ is relative to what the policy follows;
    - the eval-20 stereo depth cache (store cache/depth/eval/ep20);
    - SAM2 video masks from `ops/jobs/eval_vos.sh` (run 20261102-ptrkG-5f341eb; same frame-0 detection as the packed
      run).
  - Fit: rest segments, trimmed ICP; trimmed RMS 3.81 → 2.57 mm; guards passed.
- **Evidence:** public leave-one-episode-out CV of this procedure (PREREG_posemesh.md Part 2): held-out mean ΔAUC
  +0.106 (ep21 +0.133, ep22 +0.080), 10-seed means. Results in `docs/analysis/ptrk-20261102/results/cv_posemesh.json`.
- **D1 [M]:** kit registration to the public scan at eval-20 slot-1 seeds: 3.4° at the kit seed (3.4–4.2° over 10
  seeds) against 3.3° for the unplaced payload. No flip.
- **Disclosure:** the procedure was selected by public pose CV (mocap of public episodes, development). Nothing on eval
  was scored.
