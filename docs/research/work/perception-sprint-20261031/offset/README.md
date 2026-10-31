# offset: GT-free correction of the constant per-object pose offset (refine step S11), 31 Oct 2026

Perception sprint, experiment "offset". Labels: [M] measured, [E] estimate, [H] hypothesis. CPU only on this VM, $0;
no GPU, Vast or Kaggle; nothing committed by this step (the orchestrator commits). The step number is S11 because the
parallel experiment "heldpose" already uses S10 in `pipeline/refine.py`.

## 0. Pre-registration (written before any mocap was read for this experiment; not changed after scoring)

**Hypothesis [H-OFF].** Our frame-0 and rest-phase object poses carry a constant bias, because FoundationPose registers
on contaminated or partial masks and depth. A robust re-fit of our mesh to our own stereo depth, with the occluders
removed, measures that bias, and one constant body-frame correction per object removes it.

**Evidence it builds on [M, earlier work].**
- Phase 1 (`../../leak-decomp-20261030/phase1/RESULTS.md`): with true templates the tracker loses 0.033 (\*, without ep0
  and ep23), of which 0.025 is one constant body offset per (episode, object) (the oracle `trk` refit).
- On our own tracks the constant-offset ceiling is larger: R_trk − R_lib(P_o) = 0.9403 − 0.8899 = +0.050 (20 episodes).
- F1 (`../../leak-decomp-20261030/tracker-fix/ep31/DIAG.md` §4; `PREREG_f0icp.md`) was frame-0 trimmed ICP onto the
  det_f0 mask's depth, without removing occluders, applied to the rest prefix only. It was falsified by its harm guard
  (ep12 −0.015, ep40 −0.011, ep13 −0.026 for every object), with a mean of +0.011 lib driven by ep31 (+0.147).

**What was looked at before this section was frozen.**
- The F1 results above. They are on the same 20 public episodes, so there is no fresh holdout (as for F1, S6, T5).
- An oracle diagnostic of the direction of the Phase-1 trk offsets (`scripts/diag_dir.py`, reads the mocap-fitted
  `xstar_trk_Po.json`): at frame 0 the P_o offsets are 0.2–2.4 cm lateral and −1.5 to +1.5 cm along the viewing ray
  with mixed signs, rotations 1.5–4° on non-cups. No parameter below was set from it.
- GT-free smoke runs of the new code on ep31 (refine/in): S11 f0 changes the sweeper by 0.33 cm / 4.6° and the rack by
  0.23 cm / 2.9° (F1 changed the sweeper 7.1°). No score was computed for them.

**Method (`pipeline/offsetfix.py`, called by `pipeline/refine.py --steps S11,S2`; opt-in, not in DEFAULT_STEPS).**
Inputs: our track, `world_T_cam`, our stereo depth (frame-0 `depth0.npy`; for mode mf a fixed grid of 48 frames of
our depth cache `cache/depth/public/ep<N>/depths_fs0.5.npy`, fetched by HTTP range reads, `scripts/fetch_depth.py`),
our frame-0 masks (`det_f0.npz`), our hands (`hands_refined.npz`), our meshes (library_v3). Every path passes
`refine.assert_inference_input`. Per object j and used frame t, at half resolution (K/2):
1. Render every roster object at its tracked pose (z-buffered splats of ~1 sample per 1.5 mm² of our mesh).
2. Occluders out: pixels whose front-most rendered object is another object; our hands (valid joints: hull of the 21
   projected joints plus a 25 cm forearm strip, dilated by 2 cm at the hand's depth); points within 0.8 cm above our
   frame-0 table plane (`det_rules.table_plane`, as S6).
3. Pixels: mode **f0** = the chosen det_f0 mask minus occluders; mode **mf** = our predicted visible silhouette of j,
   dilated 2 px, minus occluders. Valid depth only. Points farther than 2 cm from our posed mesh are dropped.
4. Point-to-plane ICP of our mesh's camera-facing samples onto the points, from the tracked pose, keeping the 80 %
   closest pairs per iteration, ≤ 30 iterations. Cups (`--s6_axisym`) get no update about their own axis.
5. Accept a frame if ≥ 150 points, the trimmed residual drops, and the change is ≤ 3 cm (centroid) and ≤ 10°.
   C_t = inv(T_t) T_icp, a body-frame correction.
6. f0: C = C_0. mf: over the accepted frames among the object's non-moving frames (refine's labels) of the grid:
   chordal-mean rotation (members > max(2°, 2.5 × median deviation) dropped) and per-axis median centroid shift;
   needs ≥ 5 frames, shift spread (median deviation) ≤ 1 cm, rotation spread ≤ 3°, result ≤ 3 cm / 10°.
7. Apply: **whole** O'(t) = O(t) C on every frame (the form the trk ceiling measures); **prefix** only before the
   object's perceived onset (> 1 cm or > 5° from frame 0; F1's form).

**Variants (declared now).**
- **V1 (primary) S11 mf/whole:** `--steps S11,S2 --s11_mode mf --s11_apply whole --s11_depth <grid npz>`.
- **V2 S11 f0/whole:** `--steps S11,S2 --s11_mode f0 --s11_apply whole`.
- **V3 S11 f0/prefix:** `--steps S11,S2 --s11_mode f0 --s11_apply prefix` (F1 with the occluders removed).

**Arms.** `Po` = Phase-1 P_o tracks (library_v3 templates, the eval-like arm) with refine/in's frame-0 depth, hands and
det_f0 masks (the 25 Oct masks; as F1 and T1); `refineP` = the 25 Oct tracks (`refine/in`) with their own files.
Baseline = `--steps S2` (the adopted chain), re-run with the new code and checked byte-identical against T1's S2 outputs.

**Scoring.** `tools/xstar_fit.py score_track` (the kit chain, ADD-AUC). lib = library_v3 at X_kit (leaderboard
convention, decisive); \* = X\*_geom (beside). ΔR = R(S11,S2) − R(S2). Mocap is read only by `scripts/off_score.py`,
after every refine output exists.

**Pass rule (fixed by the sprint task; per variant and arm, lib).** Mean ΔR_lib over the 20 public episodes ≥ +0.010;
≥ 12/20 episodes better (ΔR_lib ≥ +0.0001, strictly positive at the scorer's 4-decimal rounding); no episode
ΔR_lib < −0.010. **Adopt only if both arms pass.** If several variants pass, V1 is adopted when it passes, otherwise the
passing variant with the higher two-arm mean, flagged as chosen among 3.

**Ceiling readings (oracle, after inference; reported, not decisive).**
- Score share: mean ΔR / mean (R_trk − R) of the same arm's input track (Phase-1 `xstar_trk_Po.json` for Po,
  `tierA/xstar_trk.json` for refineP), in lib and \*; and mean ΔR\* without ep0, ep23 against the 0.025 of Phase 1.
- Geometric share per (episode, object): the oracle constant body correction C_or = inv(X_trk) X\*_geom against our C,
  as mean displacement of our mesh's vertices: d0 = |C_or − I|, d1 = |C_or − C|; recovered = 1 − d1 / d0.
- **[H-OFF] is falsified for a variant** if, over the objects with d0 ≥ 0.5 cm that the variant corrected, the median
  recovered share is ≤ 0 (the depth re-fit does not move the poses toward the oracle's constant offset).

**Eval.** Only a variant that passes is run on eval (GT-free, stored perception; no tuning). Otherwise no eval file is
read and no eval reference changes.

## 1. Amendments before scoring (GT-free reasons only)
- 31 Oct, before any score: for speed only, each ICP association uses a strided subsample of ≤ ~60k camera-facing
  model samples, and the 2 cm band test ≤ ~100k samples (the rack's 400k made one mf run take 3 min). On ep31 refineP
  the mf result was unchanged by the first of these (sweeper kept, spread 3.7°; rack 0.49 cm / 2.86°, 48/48 frames).
  Per-frame render and hand mask are computed once per frame (same values).

## 2. Oracle arm P_s, added after the main scoring (diagnostic only; reading rule written before it ran)
Written 31 Oct ~09:58 UTC, after the main arms were scored (§3: all three variants fail) and before this arm ran.
- **Why:** the main arms cannot tell whether the depth re-fit fails because of our templates or because of the depth
  re-fit itself. Phase 1's 0.025 constant-offset share was measured on P_s (the organiser scans as tracking templates).
  Running the same S11 on P_s with the scan meshes measures how much of that 0.025 the method recovers when the shape
  is right.
- **What:** the Phase-1 P_s tracks (`perc2scan/poses_world_vo.npz`, scan frames) with P_o's `world_T_cam` (cameras agree
  within ≤ 0.08 cm, `phase1/RESULTS.md`), refine/in's depth, hands and det_f0, and `--meshes` a folder of links to the
  public scans. Same commands and parameters as V1–V3 and the S2 baseline. ORACLE: scan meshes are never an inference
  input on eval; nothing here is adoptable.
- **Scoring:** \* (scan frames = identity registration, via X\*_geom to lib frames and back, as Phase 1). Ceiling =
  R_trk(P_s) − R\*(P_s) from `phase1/scores/xstar_trk_Ps.json` (mean 0.0222; 0.0246 without ep0, ep23).
- **Reading rule:** template-limited [H-TPL] is supported if a variant recovers ≥ 25 % of the P_s ceiling (mean ΔR\* ≥
  +0.0056 over 20 episodes) with median recovered geometric share > 0; the depth re-fit itself is uninformative if the
  mean ΔR\* ≤ 0 and the median geometric share ≤ 0; anything else is inconclusive.
