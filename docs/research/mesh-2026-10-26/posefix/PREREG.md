# posefix: physics rest projection of our tracked poses (pre-registration, public episodes only)

Written 1 Nov 2026 ~05:00 UTC, before any scoring step of this experiment ran and before any public parquet, mocap pose
or scan was opened for it. Committed and pushed before the first scorer run; the commit hash is in `README.md`.
Labels: [M] measured, [E] estimate, [H] hypothesis, [D] diagnostic (scored against public ground truth).

## 1. In plain words

At frames where no hand is near an object ("hands-off", H30), our tracked poses are often physically impossible: the
visual meshes of two objects cross each other, or an object sits in the table (INTERLOCK 21.15, precheck_H30). This
experiment moves an object, during each hands-off stretch, by the smallest rigid shift that removes the overlap, holds
that shift for the whole stretch and ramps it in and out over 3 frames. It is applied to our own public perception
tracks and scored with the same kit chain as the CD-O sprint AUC guard. If it helps on public data by the gate in
section 7, the pack lane may apply the same rule to the eval references; if not, it is not proposed for eval.

## 2. Inputs (all GT-free for the transform)

- **Episodes:** the 20 public episodes with perception tracks: 0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39,
  40, 41, 42, 43, 44, 45.
- **Tracks:** the stored converted tracks of the CD-O sprint AUC guard, copied to `<scratch>/posefix/tracks/ep<e>/`:
  `cdo_c0/tracks` (15 episodes), `cdo_c1/t2/auc/tracks` (18, 39, 40), `cdo_c1/t3/auc/tracks` (23, 24). Each one was
  checked [M] array-equal (max abs diff < 1e-12) to `world_T_cam @ cam_T_<obj>` of `data/sweep/ep<e>/poses.npz` (our
  inference output), with no non-finite frame. world_vo = camera frame 0 (`world_T_cam[0]` is the identity in all 20).
  sha256 (first 16 hex): 0 77b98d2e22b097eb, 2 129dce52d359a179, 11 c09ea1d089424b2f, 12 e538fb7633ca4d9d,
  13 3e1a00a4677b58ba, 18 b198d95f81100673, 21 3307012737ef10b9, 22 a8d876274d9dde8c, 23 df80ebd0e74efbaf,
  24 050c1e22487ea990, 26 e93274ded98f4743, 27 2578bdc58e6d5f30, 31 ba5996e431e8acb1, 39 2b06718eeaa9f2a7,
  40 dcdef66c15c16b60, 41 717b93d2ee3f413c, 42 cc65534b0bfa356c, 43 bb9658978c3bd62d, 44 c13ec6cb30854c3a,
  45 50ca4e70f7f472b3. Full hashes: `inputs.json` (committed copy of `<scratch>/posefix/inputs.json`).
- **Meshes: pack 9a+** (`<scratch>/posefix/mesh9a/<obj>.glb`), md5:
  - white_pot 0264da83fc0e396c652a43d282dbc0ea, white_pot_lid 35727a10bca407594f41d108b4dc03ab, plastic_dish_rack
    bbca8ec0c26e6e37baaa145cef4e48e5 (all `meshes/library_c0`);
  - beige_cup 8c8be2b0747d234706913a2360e90570 (C1 T1 `ep11_beige_cup_sep_g1.glb`);
  - mini_dust_pan 1976540525ecca181c9ed83ba953e165 (C1 T2 `mini_dust_pan_k297_s42_lib.glb`);
  - library_v3: blue_cup 7542631493e3a0564f6d74009de67d54, mini_sweeper c126a8ff33dcc8f4504b285e0b3cc5c2,
    water_pitcher fc824fc5b0a9325c91b630c19ba32677, wooden_piece_1 d152b2b5e6a9d9acdd5bd37e29e72b9d, wooden_piece_2
    825a7fe364d280603f36226595137f43.
  - These equal the mesh files of the stored 9a+ runs (C0 `c0` pot/lid/rack, C1 T1 beige, C1 T2 dust pan, library_v3
    elsewhere). Geometry for the transform = the kit's `budget_mesh(path, 4096, 4096)` of each, exactly as the scorer
    decimates candidates.
- **Hands (GT-free):** gmg M1 MediaPipe hands of the v6 clean run `gmg/runs/20261031-b4ext6-90c8cce/hands/public/
  ep<e>/hands.npz` (pipeline/hands_mp.py: cam_a video + our FoundationStereo depth + our VO; world = rectified-left
  camera at frame 0 = world_vo). Joints with `valid_<side>` true, 21 per hand. sha256 per episode in `inputs.json`.
- **Table (GT-free):** the v6 bundle `episode.json` `table` entry (`n`, `d`; frame-0 FoundationStereo depth,
  `recon_mesh.table_plane` RANSAC; camera frame 0 = world_vo). Height above the table h(x) = n.x + d (camera at h = d
  > 0). One plane per episode for all frames.
- **Scorer (for section 6 only):** `pipeline/score_registered.py` (sha256 6a4cd60a0d26e3f8..., last changed 46b8389),
  kit `<scratch>/kit/v2d_submission_kit` (`v2dlb/track3_pose.py` b4b99f698eb4893a, `mesh_budget.py` 8f29481d52a82c46),
  public scans as the hidden-scan stand-in (`cdo_c0/t3/mesh`), public parquets. Same chain, seeds and points as the
  CD-O sprint AUC guard (`cdo-sprint/C0/scripts/run_auc_guard.sh`).

## 3. Integrity

- The transform (`scripts/pf_transform.py`, `scripts/pf_lib.py`) opens only the files of section 2 except the scorer
  inputs. It never opens a parquet, a scan or a mocap pose. Object names and slot order come from our track files.
- Run order (`scripts/run_posefix.sh`): `transform` (all variants) -> sha256 of every written track and report
  (`out/<V>/tracks_sha256.txt`, committed) -> `stage0` (stages parquets and scans) -> `score` -> `diag`.
- One scored run per variant and episode. No constant below is changed after any score is seen. Variants B, C, D are
  report-only and cannot change the verdict.
- GT-free development before this text (no score involved): the measurement `scripts/pf_measure.py` on all 20 tracks
  (`gtfree_measure_summary.txt`) and dev transform runs of variant A on episodes 0, 2, 11, 12, 13, 24, 31, 41 (code
  versions before this commit; outputs in `<scratch>/posefix/dev`, not scored). They showed: the q90 success share
  overshoots on jittery segments (changed to the median frame, 4.4), the support case lid-on-pot needs inheritance
  (4.5) and the plain Gauss-Newton stalls on thin shells (lift search added, 4.6).

## 4. The rule (variant A; constants in `pf_transform.py` header)

4.1 **Hand-near (H30).** Object o is hand-near at frame t if any valid hand joint lies within 30 mm of o's mesh surface
(dense surface samples at 1 mm plus vertices, in o's frame at our pose) or inside o. Otherwise o is hands-off at t.

4.2 **Rest segments.** A rest segment of o is a maximal run of consecutive hands-off frames of length >= 5 (0.25 s at
20 fps). Shorter runs are left alone.

4.3 **Penetration** (visual meshes, our poses), per frame:
- signed distance grids of every mesh in its own frame: 1.5 mm spacing, 9 mm margin; inside = |median over the three
  axes of the signed-crossing winding number| >= 0.5 (handles open and inside-out shells); unsigned distance from
  surface samples (3 mm everywhere, 0.5 mm within 8 mm of the surface); trilinear interpolation; outside the grid =
  far outside;
- probes of each object = its 4,096 vertices plus up to 12,000 area-uniform surface samples (2 mm spacing; seed 7);
- object-table depth = max(0, -min over o's probes of h);
- object-object depth (o, p) = max over the two directions of max(0, -min sdf_p(o's probes)) and of p's probes in o;
- reported also: overlap volume = (inside nodes of the smaller-volume object that fall inside the other) x 1.5^3 mm^3.
- A constraint frame is clean when its maximum depth (table and every assigned pair) is <= 1.0 mm.

4.4 **Constraints of a segment.** For a rest segment of o: the table at every frame of the segment; pair (o, p) at the
frames where p is also in a rest segment and o is the mover of the pair (4.5). The segment is resolved when at least
50 % of its constraint frames are clean (the median frame: a constant shift corrects the offset of the typical frame,
not the frame-to-frame jitter). A segment that is already resolved is left unchanged.

4.5 **Mover and support.**
- Pair (a, b) at frame t, both at rest: the object whose current rest segment started later (released last) moves. Tie
  (both at rest since the same frame, e.g. since frame 0): the smaller mesh volume moves; then the later slot.
- Support exception: if that object is the lower of the two (lower lowest point above the table, original poses) and
  the other object's lowest point is >= 10 mm above the table (it does not stand on the table, so it rests on the
  mover), the other (upper) object moves instead. A support is never pushed into the table by its guest.
- The table never moves.
- Support inheritance: if a mover rests on a partner (on more than half of the pair frames its lowest point is >= 10 mm
  above the partner's and its probes come within 5 mm of the partner, original poses) and that partner has already been
  shifted at those frames, the mover's start shift is the partner's shift applied to the mover's centre (mean over the
  shifted pair frames). Its own shift is solved from there (a guest rides along with its support, then is corrected).

4.6 **Solver**, per segment, from the start shift (zero or inherited), about the object's volume centroid at the
segment's middle frame:
- Stage 1, translation: projected Gauss-Newton on the squared depths of all violating probes of all constraint frames
  (rows = signed-distance gradients; the table gradient = n); Levenberg damping 1e-9 x (number of violators); trust
  region 5 mm per iteration; stop at the first iterate that resolves the segment (success), when |t| > 30 mm, after 60
  iterations, or after 20 iterations without a better clean share (failure).
- Stage 1b (only if stage 1 fails), lift: the smallest lift along +n in 0.5 mm steps from the start shift that resolves
  the segment with |t| <= 30 mm.
- Stage 2 (only if 1 and 1b fail), small rotation: the same Gauss-Newton with translation and rotation (rotation vector
  about the centroid; 1 deg per iteration; bounded by projection to 5 deg); same stops.
- If all fail, the segment is "unresolved" and keeps its start shift (zero, or the inherited support shift).

4.7 **Order, hold, ramp.**
- Segments are processed in order of start frame (then larger volume first, then slot), against the partners' current
  (already shifted) poses, in two Gauss-Seidel sweeps; the second sweep's shifts are final.
- The shift of a segment is one rigid transform held constant over every frame of the segment.
- Ramp: over the 3 frames outside each end of a shifted segment the shift is scaled linearly (3/4, 2/4, 1/4 at
  distance 1, 2, 3 frames); if the gap to the same object's next rest segment is <= 6 frames, the shift is interpolated
  linearly between the two segments' shifts across the gap. Ramps stop at the episode ends.
- Output: one `poses_world_vo.npz` per episode (same keys), plus `posefix.json` (every segment, its constraints,
  status, shift and penetration before / after).

4.8 **Report-only variants** (same code, same constants):
- B: A, then drop each resolved rest segment whose median clearance (to the table and every object at rest in the same
  frame) is in (2, 15] mm along -n, by the largest distance (bisection, 12 steps) that keeps it resolved against all.
- C: A, but segments that contain frame 0 keep their tracked pose (they are still partners of later segments). It
  separates the kit's frame-0 scene alignment from the rest of the effect (section 8, H1).
- D: A with object-object constraints only (no table constraint).

## 5. What is reported (diagnostic, after the transform)

- Per episode, before (original tracks) and after (A; B, C, D report only), kit-chain perception scores from
  `score_registered.py`: AUC, MPPE (cm), RPE (cm), SP-SR, MP-SR, per-object AUC; plus mean symmetric ADD (cm) per
  object from `pf_diag.py` (the AUC's own per-frame error after the kit's alignment). Deltas = after - before; mean and
  min over the 20 episodes.
- **Before = stored check:** the before scores must equal the stored 9a+ runs where they exist: 0, 2, 26, 27, 31,
  41-45 = C0 `runs/c0`; 12, 13 = C0 `runs/single_plastic_dish_rack`; 21, 22 = C0 `runs/base`; 11 = C1 T1
  `runs/single_ep11.json`; 18, 39, 40 = C1 T2 `runs/single_mini_dust_pan`. 23 and 24 have no stored 9a+ run. Any
  mismatch is reported; deltas always use this experiment's own before runs.
- GT-free per segment: status, shift (mm, deg), penetration before / after.

## 6. Diagnostics that read ground truth (`pf_diag.py`; decide nothing about the transform)

- **Direction check.** For every segment with a nonzero shift: push = mean over its frames of the displacement of the
  object's scan anchor (the scorer's converted pose) after - before, both under the BEFORE run's scene alignment;
  correction = mean over the same frames of (mocap anchor - our aligned anchor, before). Cosine(push, correction).
  Note on sign: the brief wrote "(ours - mocap)"; a push that corrects the pose points along (mocap - ours), so the
  cosine is taken with the correction and "the push helps" means cos > 0. **Falsified if cos <= 0 on more than half of
  the shifted segments** (also reported split into segments with and without a pair constraint).
- **Mesh check.** At the frames where both objects of a pair are at rest (every second frame): overlap volume and max
  depth of OUR meshes placed at the MOCAP poses (mocap scan pose composed with the inverse of the kit's registration of
  our mesh to the scan), next to the same at OUR poses and the public scans at the mocap poses. Bottom check (mocap z
  taken as up): lowest point of our mesh at the mocap pose minus the scan's lowest point, at each object's rest frames.
  Reading: overlap at mocap poses close to the overlap at our poses = "meshes too fat / wrong shape"; near zero = "our
  poses wrong".
- The replicated AUC must equal the scorer's (check of the diagnostic code).

## 7. Gate (pre-registered, variant A only)

**Mean dAUC over the 20 episodes >= +0.002 and no episode with dAUC < -0.01.** Otherwise the fix is not proposed for
eval. MPPE and RPE deltas are reported next to it (no threshold). Episodes the rule leaves unchanged count with
dAUC = 0.

## 8. Predictions with falsifiers

- **P1 [H] (GT-free, checkable before scoring):** A changes at least one frame in >= 15 of the 20 episodes (rest-phase table penetration of
  >= 2 mm is in nearly every episode, `gtfree_measure_summary.txt`). Falsifier: fewer than 15 changed.
- **P2 [H]:** segments left unresolved by A include ep11 beige (end stack, ~93 cm3), ep13 blue cup (end, ~16 mm in
  the table plus the rack), ep31 rack (end), ep24 board 1 (end, slotted pair without slots) and ep0 lid (60 mm below
  the table: the known failed lid track). Seen in the dev runs; it holds unless the final code differs.
- **P3 [H] (frame-0 coupling):** the kit aligns the scene once at frame 0 (offset from object 0, rotation from the
  first object without a symmetry axis). A shift held over a frame-0 rest segment therefore moves every other frame of
  the episode in the aligned frame. If the table penetration is a bias common to the whole episode (table plane or
  mesh bottom), the alignment already cancels it and a rest-only lift adds error to the in-hand frames. Prediction: on
  the single-object pot episodes 41-45 mean dAUC(A) < 0. Falsifier: mean dAUC(A) on 41-45 >= 0.
- **P4 [H]:** the gate fails (mean dAUC < +0.002 or an episode < -0.01). About 60 % confidence; falsifier: it passes.
- **P5 [H] (direction):** cos > 0 on more than half of the shifted segments that carry a pair constraint (pair overlap
  is a pose error the alignment does not cancel). Falsifier: cos <= 0 on half or more of them.
- **P6 [H] (meshes):** our meshes still overlap at the mocap poses (median >= 1 cm3) for ep11 blue / beige, ep2 pot /
  lid and ep31 sweeper / rack, i.e. part of the overlap is mesh shape, not pose; the public scans at the mocap poses
  overlap < 1 cm3 except ep24 (our board meshes have no slot, the scans may). Falsifier: median overlap at the mocap
  poses < 1 cm3 for all three pairs.
- **P7 [H] (bottoms):** the C0 pot's lowest point at the mocap pose lies >= 3 mm below the scan's (marker balls or base
  below the real base), which would make the pot's table lift a mesh artefact. Falsifier: median difference > -3 mm.

## 9. Cost

This container, CPU only, no rental, $0. Expected wall time [E]: transform ~25 min (4 variants in parallel), scoring
100 runs ~30-40 min, diagnostics ~20 min.
