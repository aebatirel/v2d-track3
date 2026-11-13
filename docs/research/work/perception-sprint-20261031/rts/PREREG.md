# rts: zero-lag position smoother after S2 (refine step S13): pre-registration

Written 2026-10-31 21:17 UTC (cloud container, session focused-pascal), **before any score of S13 and before any
S13 output existed**. Nothing in this file is changed after the first score; deviations go to `README.md`, dated.
Labels: [M] measured, [E] estimate, [H] hypothesis, [guess].

## 1. Hypothesis and what was seen before

**[H-RTS].** An offline Rauch-Tung-Striebel smoother on each object's world-frame POSITION (constant-velocity model,
process noise raised while one of our hands is near the object), applied to the adopted public chain's output (S2,
the 0.545-frame advance), raises the registered ADD-AUC of the refined track vs mocap on the 20 public episodes.

**Prior evidence (session keen-heisenberg, `docs/analysis/roman-ep2-20261031/` at 4fc29ef; diagnostic, mocap-tuned).**
- Metric there: mean ADD (cm) on a 5 cm sphere after a mocap world fit and one constant body offset per object; both
  position AND rotation (sign-continuous quaternions) filtered.
- `rtssweep.py`: best of 96 cells −5.1 % ADD with the advance vs −4.4 % for the advance alone (upper bound, tuned).
- `cvsmooth.py` (two-fold over alternate public episodes): held-out gain on top of the advance −1.2 % and −0.5 % ADD.
  The chosen cells in `cvsmooth.json` are (σ 16 mm, q 4.0, still ×0.01) for train-A and (8 mm, 4.0, ×0.01) for
  train-B (the README there says both chose 8 mm; the JSON says otherwise). The task fixes 8 mm.
- **Not independent:** the parameters below were chosen on these same 20 episodes with mocap, on another metric and
  with rotations also smoothed. This gate tests whether a positions-only form transfers to the kit-chain AUC; it is
  not a holdout test of generalisation.
- This session has read no mocap and no score for this experiment.

## 2. Method (`pipeline/rts.py`, called by `pipeline/refine.py --steps ...,S13`; opt-in, not in DEFAULT_STEPS)

- **Order:** S13 runs after S2, on S2's output (STEP_ORDER gains S13 after S2; whether S10 or S13 comes first does
  not matter here, S10 is not used).
- **Frame:** refine's world frame (O = world_T_cam @ cam_T_obj, the frame every other step uses). The filter acts on
  each axis independently with identical parameters, so it commutes with any world rotation.
- **Position:** the translation of the world pose O(t)[:3, 3] (our library_v3 mesh-frame origin; within 2.5 cm of the
  mesh vertex centroid for every library_v3 object [M]). Rotation O(t)[:3, :3] is not changed (byte-identical in the
  step's output).
- **Filter, per object, per axis x, y, z:** state [p, v]; dt = 1/20 s; F = [[1, dt], [0, 1]]; H = [1, 0];
  Q = q [[dt³/3, dt²/2], [dt²/2, dt]] with q in m²/s³; R = σ², σ = 0.008 m; q = 4.0 on frames where a hand is near,
  0.04 otherwise (q of frame t is used in the prediction from t−1 to t, as the reference `all20.kf`).
  x0 = [p(0), 0], P0 = diag(σ², 1.0). Forward Kalman pass over all frames, then the standard RTS backward pass
  t = T−2 … 0; output p = smoothed position. Numerically the reference `kf(..., smooth=True)` of all20.py (unit test).
- **Hand gate (GT-free, inference-side hands only):** our library_v3 mesh's vertices (as `trimesh.load(...,
  force='mesh')`), every len(V)//300-th, posed by S13's input track (= S2's output) on each frame; keypoints = all 21
  joints of each hand from refine's hands file (`hands_refined.npz`; `joints_<side>`, world frame), only on frames
  where `valid_<side>` is true; near(t) = min keypoint-to-posed-vertex distance < 0.035 m for either hand.
  (The reference posed the vertices with the pre-advance track; the 0.545-frame difference is declared here.)
  No hands file: no frame is near (q = 0.04 everywhere), recorded in pose_opt.json.
- Frame 0 is not held (as S2, which also moves frame 0). Fewer than 2 frames: S13 skips.

## 3. Arms, inputs, metric

- **Treatment vs control:** control = `refine.py --steps S2` (the adopted public chain); treatment =
  `refine.py --steps S2,S13`. Everything else default.
- **Perception arms (the sprint's two, inputs as heldpose / mask10):** **Po** (primary) = Phase-1 P_o tracks,
  library_v3 templates, the eval-like arm (`$S/leak/t1/in_Po/ep<N>`); **refineP** (secondary) = 25 Oct tracks
  (`$S/refine/in/ep<N>`); both with refine/in's hands and frame-0 depth. S = the session scratchpad.
- **Episodes:** the 20 public episodes 0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45.
- **Metric (the sprint's, as `heldpose/scripts/hp_score.py`):** R_lib = registered ADD-AUC of the refined track
  (`poses_world_vo.npz`) vs public mocap through the kit chain, `tools/xstar_fit.py score_track` with the kit's
  registration of library_v3 (X_kit, leaderboard convention). RPE_lib = the kit's `rpe_cm` (pairwise relative
  position error, cm; 0 on single-object episodes) on the same converted and scene-aligned arrays. Readings beside
  them: R_* and RPE_* (X*_geom registration), per-object ΔAUC, frames changed, max position change, near-frame share.
- ΔR = R(S2,S13) − R(S2) and ΔRPE = RPE(S2,S13) − RPE(S2), per episode. Mocap is read only by the scoring script,
  after all 80 refine outputs exist.

## 4. Rule

- **PASS iff, on the Po arm, mean over the 20 episodes of ΔR_lib ≥ +0.005 AND no episode has ΔR_lib < −0.02.**
  Otherwise FAIL.
- **Second arm (refineP):** a replication reading. The same rule is evaluated on it and reported with the verdict:
  "PASS, replicated" (both arms pass), "PASS, not replicated" (Po passes, refineP fails: the adoption question then goes
  to the orchestrator and the owner with that flag), or FAIL (Po fails, whatever refineP shows).
- **RPE:** reported, not gating. Mean ΔRPE_lib over the multi-object episodes is stated beside the verdict, and any
  episode with ΔRPE_lib > +0.5 cm is flagged.
- **INCOMPLETE** (no verdict; re-run only the missing pieces with the same code): any of the 40 Po refine runs
  (control or treatment) fails, or any Po R_lib is missing or non-finite. refineP missing: the Po verdict stands,
  replication "not available".
- **INVALID** (no verdict; fix and re-run everything): (a) the control `--steps S2` outputs (array bytes of
  `poses.npz` and `poses_world_vo.npz`) differ on any (arm, episode) from the S2 baseline run before the code change
  (HEAD fef059b) on the same inputs, i.e. the change was not opt-in; (b) any inference input fails
  `refine.assert_inference_input`, or inference reads mocap, a parquet or anything derived from them; (c) S13's
  written rotations differ from the control's by more than 1e-4 deg on any frame (a bug: rotations must be untouched);
  (d) the parameters that ran differ from §2; (e) refine.py or rts.py changes between the first score and the verdict
  (sha256 recorded before scoring).

## 5. What PASS buys, what FAIL leaves

- **PASS:** an opt-in refine step S13 that can be added to eval references that are rebuilt anyway (S2 is applied on
  rebuilt references per the pack-10 plan). Nothing changes in any pack, reference or job without the orchestrator and
  the owner; no rebuild is triggered by this result alone.
- **FAIL:** S13 stays in the code as an opt-in, unused step (default behaviour is byte-identical either way); the
  positions-only zero-lag smoother is closed at kit-chain level on public data; S2 stays the only adopted temporal fix.
  A fresh pre-registration would be needed for any other form (rotation smoothing, other σ / q).

## 6. Expectation [guess], cost [E]

- [guess] Po mean ΔR_lib in [−0.002, +0.003], central ≈ +0.0005; P(PASS) ≈ 0.1. Reason: the kit's ADD-AUC steps at
  1–9 cm, our fast noise is ≈ 0.15 cm median [M, keen-heisenberg], and the held-out diagnostic gain was 0.5–1.2 % of a
  ≈ 0.5–1.6 cm mean ADD (≈ 0.003–0.02 cm). S13 also moves frame 0, which shifts the kit's frame-0 scene alignment.
- Cost: CPU in this container, $0; ≈ 10–20 min inference (80 refine runs), ≈ 20–40 min scoring.

## Amendment 1 (2026-10-31 21:26 UTC; append-only; BEFORE any score, after GT-free bookkeeping only)

- **What was found (GT-free, `scripts/rts_bytecheck.py` on the 80 refine outputs; no mocap read, no score computed):**
  the written S13 rotation blocks are byte-identical to the control's on 16918 of 16984 object-frames. The other 66
  are the LAST frame of every object: S2 holds that frame (its input bytes are written unchanged), S13 moves its
  position, so refine's shared writer re-orthonormalises its rotation (the SVD it applies to every changed frame, for
  every step). There the treatment rotation equals the orthonormal projection of the control's rotation to
  ≤ 2.3e-6 deg; the chordal distance to the control's raw rotation is ≤ 1.27e-4 deg, which is the float32 input's own
  non-orthonormality (|RᵀR − I| ≤ 6.1e-6), not a rotation. By the letter, (c)'s 1e-4 deg bound fires on 1 of 66 frames.
- **Amended INVALID (c):** S13's written rotation differs by more than 1e-4 deg from the control's rotation, or, on a
  frame the control writes unchanged and S13 changes, from the orthonormal projection of the control's rotation.
- Original text above unchanged (sha256 809a4acd… recorded in `results/PREREG_sha256_before_any_run.txt`; also in
  commit dc4be79). Nothing else changes. Disclosed in README.md.
