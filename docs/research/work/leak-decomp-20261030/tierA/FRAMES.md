# Frames for the leak decomposition: X\*_geom, X\*_trk, lib ↔ scan conversion, tests (a) and (b)

30 Oct 2026, 17:15–17:45 UTC. Plan items B1 and B2, CPU tests (a) and (b) of `../PLAN.md` §7. CPU only, on this VM
(4 cores, shared with the Phase-1 build step), $0. Labels: [M] measured, [E] estimate, [H] hypothesis.

**Oracle side.** These steps read mocap and the public scans, on public episodes only. Nothing here feeds eval
inference, and no X from here is a default anywhere: `frame_xform.py` and `oracle_poses.py --xform` take X only from an
explicit file. X\*_trk is fitted to mocap and is a diagnostic only.

## Verdict
All rules pass on all 20 public episodes [M]. Details are in `frames_check.json`.

- **(a) passes.**
  - Mocap through the kit's own packer and the unmodified official `AUC.py` scores 1.0000 on 20/20 episodes, both with
    the scan submitted (a1) and with library_v3 submitted at X_kit (a2).
  - lib → scan → lib round trip through `frame_xform.py`:
    - `poses.npz`: max 6.0e-8. That is float32 rounding, because `poses.npz` stores float32.
    - `poses_world_vo.npz`: 3.3e-16 (float64).
    - `world_T_cam`: byte-identical.
    - The same holds through X\*_trk.
- **(b) passes.**
  - T\* computed two ways (converted file vs X\*_geom in process) agrees to 0.0000 per episode and object (rule ≤ 0.002).
  - Cup spin: X\*_geom spun by 45–180° changes T\* by at most 0.0018 (ep11 beige cup; rule ≤ 0.002). The cause is
    the scorer's own 1° symmetric metric on 1000 host points, which are not exactly axisymmetric.
  - T_trk two ways: 0.0000, and equal to the value recorded in `xstar_trk.json`.
  - `score_registered.py` vs the in-process lib chain: 0.0000.
  - (a3) official vs in process: 0.0000.
- **Beside the rules (no rule).** Submitting the exact scan, budgeted to 4096 faces, moves T\* by up to 0.025 per object
  (pitcher, ep21; mean −0.0002). That is the kit's own registration noise for a perfect-shape mesh.
- **Ambiguous fits resolved by the data.** Every rival minimum of the 5 ambiguous surface fits scores worse on our
  tracks in every episode except ep23 (identity swap):
  - sweeper −0.55 / −0.73;
  - lid −0.16 / −0.23;
  - pot −0.007 to −0.133 (9/9 episodes);
  - pieces −0.57 to −0.85 on ep24.

  So the best surface fit, which X\*_geom keeps on surface grounds alone, is also the one our tracks agree with.

## Commands (this VM; code = working tree on e03cb91 plus this step's edits, committed by the orchestrator)
`S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad`, `PY=$S/map/scoring/venv/bin/python`,
`KIT=$S/map/scoring/kit/v2d_submission_kit`, `T3=$S/map/scoring/t3` (public parquets; `mesh/` → `$S/hfds/track_3/public/mesh`),
`D=docs/research/work/leak-decomp-20261030/tierA`. Run from the repo root.
1. X\*_geom (3 min 48 s):
   `$PY -I tools/xstar_fit.py geom --lib meshes/library_v3 --t3 $T3 --kit $KIT --out $S/leak/xstar_geom_v2.json`, then copied to
   `$D/xstar_geom.json` (md5 919ea341…). Log: `$D/xstar_geom.log`.
   - It is bit-identical to the WIP fit committed in 6468f65, except that each listed minimum now also carries its X.
2. X\*_trk on the `refine/in` tracks (6 min 6 s, 3 processes):
   `$PY -I tools/xstar_fit.py trk --perc $S/refine/in --geom $D/xstar_geom.json --lib meshes/library_v3 --t3 $T3 --kit $KIT --out $D/xstar_trk.json --jobs 3`
   (md5 bd8432f1…). Log: `$D/xstar_trk.log`.
3. Tests (a) and (b): `$PY -I $D/frames_check.py --xgeom $D/xstar_geom.json --xtrk $D/xstar_trk.json --perc $S/refine/in --lib meshes/library_v3 --t3 $T3 --kit $KIT --work $S/leak/oracle_frames_v2 --out $D/frames_check.json --jobs 3`
   (11 min 32 s). Log: `$S/leak/logs/frames_check_v2.log`.
4. The `oracle_poses.py --xform` path on ep11, ep13 and ep31, kit X vs X\*_geom:
   `$PY -I pipeline/oracle_poses.py EP $S/refine/in/epEP $S/leak/oracle_poses_xform/epEP_{kit,geom} --meshes meshes/library_v3 [--xform $D/xstar_geom.json] --t3 $S/oracle/verify2/t3 --kit $KIT --depth $S/refine/in/epEP/depth0.npy`.
   - ep11 ran in the earlier attempt with the same code.
   - Outputs: `$D/oracle_poses_xform/*.oracle.json`.
5. Tables below: `python3 -I $D/frames_tables.py`.

Inputs:
- `refine/in` is the 20-episode perception set of the refine study: tracks from `runs/20261025-guard-fe3f407`, hands
  from the g1/auto18 runs, depth frame 0.
- Its templates were library_v2. That equals library_v3 except `mini_sweeper.glb`, whose underside v3 flattened
  in place (121 vertices, same body frame), so X\*_geom of the v3 sweeper applies [M, `meshes/library_v3/README.md`].

## B1 X\*_geom: rigid fit of library_v3 to the public scan (scans only, no mocap)
Method (`tools/xstar_fit.py`, docstring):
- Unscaled trimmed ICP (90 %), lib onto scan, from 85 starts: identity, the kit's 24 PCA mappings, 48 seeded random
  rotations, plus 12 axis spins (cups) or the 180° flip (lid).
- The best start is picked by the kit's symmetric mean surface distance on fresh samples.
- Reported: distinct minima (symmetry-aware), the reseed stability, and per (episode, slot) the kit's own registration
  X_kit, with E = X\*_geom X_kit⁻¹.

| object | symmetry | rot / shift vs lib frame | sym. surface distance mm (trim 90 %) | p90 lib→scan / scan→lib mm | RMS ratio scan/lib | 2nd minimum: residual ratio, rot, ADD | reseed ADD cm | E = X\*_geom X_kit⁻¹ over eps: ADD cm, rot ° |
|---|---|---|---|---|---|---|---|---|
| beige_cup | cup axis | 90.10° / 1.81 cm | 8.02 (6.22) | 9.1 / 27.9 | 1.122 | 1.367, 25°, 2.49 cm | 0.141 | 1.48–1.48, 2.0–2.0 (tilt) |
| blue_cup | cup axis | 0.54° / 0.18 cm | 3.74 (2.71) | 9.5 / 5.9 | 1.142 | 1.988, 178°, 11.97 cm | 0.071 | 0.76–0.89, 0.4–1.1 (tilt) |
| mini_dust_pan | none | 0.88° / 0.56 cm | 3.11 (2.64) | 6.6 / 5.2 | 1.078 | 1.146, 6°, 0.59 cm | 0.051 | 0.21–0.25, 1.6–1.6 |
| mini_sweeper | none | 1.98° / 0.17 cm | 3.21 (2.63) | 5.7 / 6.0 | 0.951 | 1.015, 180°, 4.48 cm **ambiguous** | 0.030 | 0.30–0.32, 1.5–1.6 |
| plastic_dish_rack | none | 0.44° / 1.36 cm | 6.41 (5.33) | 10.3 / 15.8 | 0.973 | 1.757, 178°, 9.48 cm | 0.084 | 1.13–1.39, 0.8–1.4 |
| water_pitcher | none | 0.61° / 2.28 cm | 9.51 (7.33) | 18.0 / 23.2 | 1.031 | 1.360, 168°, 13.00 cm | 0.119 | 1.71–1.75, 2.1–2.6 |
| white_pot | none | 0.93° / 0.87 cm | 5.52 (4.49) | 10.4 / 10.1 | 0.964 | 1.080, 7°, 0.84 cm **ambiguous** | 0.169 | 0.75–0.88, 1.3–2.5 |
| white_pot_lid | lid 180 deg | 0.40° / 0.86 cm | 3.99 (3.55) | 7.1 / 5.9 | 1.034 | 1.062, 157°, 2.52 cm **ambiguous** | 0.023 | 0.24–0.26, 0.9–1.5 |
| wooden_piece_1 | none | 0.35° / 0.08 cm | 2.17 (1.69) | 3.4 / 5.1 | 1.033 | 1.079, 180°, 6.47 cm **ambiguous** | 0.018 | 0.14–0.21, 0.3–0.7 |
| wooden_piece_2 | none | 0.82° / 0.32 cm | 2.09 (1.88) | 3.0 / 3.1 | 1.009 | 1.038, 180°, 14.63 cm **ambiguous** | 0.011 | 0.09–0.16, 0.4–0.7 |

beige_cup: spin profile (residual vs spin about the scan axis, 10° steps, no refit) 7.99–9.00 mm, argmin 10°

blue_cup: spin profile (residual vs spin about the scan axis, 10° steps, no refit) 3.74–4.31 mm, argmin 0°

white_pot_lid: residual after the 180° flip about the normal 4.05 mm (best 3.99)

Reading [M]:
- Our cups are 12–14 % smaller than the scans in RMS radius (beige 1.122, blue 1.142). Every other object is within 8 %.
  - So a rigid fit keeps a shape residual: beige cup 8.0 mm, pitcher 9.5 mm, rack 6.4 mm.
  - The kit's registration rescales by this ratio before its ICP and matches centroids, so X_kit ≠ X\*_geom.
- X\*_geom vs X_kit (E) puts 0.1–1.8 cm of symmetry-aware ADD on a perfect track.
  - Pieces, sweeper, dust pan and lid: 0.1–0.3 cm. Pot and cups: 0.75–0.9 cm. Rack and pitcher: 1.1–1.75 cm.
  - Beige cup: 1.48 cm.
  - Test (a3) below shows what E costs a perfect motion under the leaderboard convention.
- **Ambiguity.** 5 of 10 fits have a distinct second minimum within 10 % of the best residual:
  - mini_sweeper: 1.015 ×, 180°, 4.5 cm;
  - wooden_piece_2: 1.038 ×, 180°, 14.6 cm;
  - white_pot_lid: 1.062 ×, 157°, 2.5 cm (beyond its 180° symmetry);
  - wooden_piece_1: 1.079 ×, 180°, 6.5 cm;
  - white_pot: 1.08 ×, 7.4°, 0.84 cm.

  The surface alone therefore cannot settle these objects. Test (b3) scores every such rival on our tracks (below).
  X\*_geom keeps the best surface fit whatever the tracks say. If a rival were picked from mocap-scored tracks, X\*_geom
  would become mocap-fitted.
- **Cup spin.** The kit scores cups modulo spin, so only the tilt and centre of X matter to the score.
  - The residual changes little with spin: beige 7.99–9.00 mm over 36 spins, blue 3.74–4.31 mm.
  - So the spin in X\*_geom is set weakly: beige is 90° from our lib frame, versus 145° under X_kit (E: 125° of spin,
    2.0° of tilt).
  - Our beige cup is less axisymmetric about the scan axis than the scan itself. Self-distance under spin is 2.6–12.8 mm
    for ours vs 1.7–3.6 mm for the scan (8000 samples, `$S/leak/scripts/cup_selfsym.py`).
  - So the spin matters for the cells that simulate our meshes (c2, c3), though it never matters to the score (b2).

## B1 X\*_trk: constant body offset per (episode, object), fitted to mocap (ORACLE DIAGNOSTIC)
Method (docstring):
- A robust least-squares fit (soft-L1, 2 cm, ≤ 200 frames, with one free world transform per episode).
- Then Powell on a smoothed AUC under the kit's own conversion and frame-0 alignment.
- X\*_trk is the best exact AUC among {X\*_geom, LS, the two refits}, each within 5 cm (symmetry-aware ADD) of X\*_geom.
  So T_trk ≥ T\* by construction: T_trk is an upper bound on what one constant offset per episode and object can
  recover. T_trk_ls, the plain geometric fit, is reported beside it.
- Cups use 3 axis points, so their spin stays X\*_geom's. The lid's flip is chosen per frame.

| ep | picked | rejected (> 5 cm) | per object: trk vs geom ADD cm, rot ° [track rot span °] |
|---|---|---|---|
| 0 | opt_from_geom | – | white_pot 2.54, 2.1 [15]; white_pot_lid 3.30, 3.4 [16] |
| 2 | opt_from_ls | – | white_pot 1.75, 2.5 [12]; white_pot_lid 2.58, 4.2 [30] |
| 11 | opt_from_geom | – | blue_cup 1.69, 10.0 [33]; beige_cup 0.85, 14.2 [22] |
| 12 | opt_from_geom | – | blue_cup 0.54, 25.4 [180]; plastic_dish_rack 1.48, 1.6 [3] |
| 13 | opt_from_ls | – | blue_cup 1.10, 5.0 [177]; plastic_dish_rack 1.35, 2.7 [2] |
| 18 | opt_from_ls | – | mini_sweeper 0.87, 4.1 [50]; mini_dust_pan 0.43, 1.6 [63] |
| 21 | opt_from_ls | – | blue_cup 0.52, 13.1 [38]; water_pitcher 1.87, 4.8 [91] |
| 22 | opt_from_ls | – | blue_cup 1.01, 8.1 [29]; water_pitcher 2.21, 4.4 [92] |
| 23 | geom | ls, opt_from_ls, opt_from_geom | wooden_piece_1 0.00, 0.0 [114]; wooden_piece_2 0.00, 0.0 [102] |
| 24 | opt_from_ls | – | wooden_piece_1 1.81, 0.5 [107]; wooden_piece_2 1.32, 1.6 [102] |
| 26 | opt_from_ls | – | plastic_dish_rack 1.23, 4.5 [4]; white_pot 0.96, 2.3 [180] |
| 27 | opt_from_ls | – | plastic_dish_rack 1.01, 3.7 [2]; white_pot 0.60, 1.8 [177] |
| 31 | opt_from_geom | – | mini_sweeper 0.84, 9.5 [35]; plastic_dish_rack 1.41, 3.2 [4] |
| 39 | opt_from_ls | – | mini_dust_pan 0.41, 2.2 [110] |
| 40 | ls | – | mini_dust_pan 1.07, 1.8 [75] |
| 41 | opt_from_ls | – | white_pot 0.99, 1.9 [69] |
| 42 | opt_from_ls | – | white_pot 1.11, 1.8 [98] |
| 43 | opt_from_ls | – | white_pot 0.91, 1.6 [180] |
| 44 | opt_from_ls | – | white_pot 1.77, 1.6 [25] |
| 45 | opt_from_ls | – | white_pot 0.74, 1.7 [94] |

Reading [M]:
- The 5 cm cap is needed: in ep23 the tracker swapped the two pieces. Uncapped, the fit moved wooden_piece_1 by 260 cm
  [M, earlier attempt, `$S/leak/xstar_trk_v0_nocap.json`]. All three refits are rejected there, so T_trk = T\*.
- X\*_trk is 1.30 cm (mean, ep23 excluded) from X\*_geom and 1.24 cm from X_kit, while X\*_geom and X_kit are 0.80 cm
  apart. The trk offset is nearer X_kit in 17 of 31 (episode, object) pairs.
  - So the constant offset of our tracks is not one of the two registrations: it is track bias.
  - Exceptions: the pitcher (2/2) and the rack (3/5) sit nearer X_kit. Source: `$S/leak/scripts/trk_vs_kit.py`.
- For an object that barely moves (rack: 2–4° track rotation span), a constant body offset absorbs any static pose
  error, including frame-0 error held over the rest. T_trk − T\* is then "constant error", not only registration.
  Each object's rotation span is in `xstar_trk.json` (`fit.track_rot_span_deg`).

## B2 frame conversion
`pipeline/frame_xform.py EP PERC_DIR OUT_DIR --xform xstar_{geom,trk}.json --to scan|lib`:
- Conventions:
  - scan pose = lib pose · X⁻¹; lib pose = scan pose · X.
  - `poses.npz` `cam_T_<obj>` keeps its dtype (float32); `world_T_cam` is copied.
  - `poses_world_vo.npz` stays float64.
  - The other perception files are linked unchanged: depth, hands, detections and VO hold no body-frame pose; checked
    on ep11's keys.
  - `xform.json` records X, the direction and the input md5s.
- Guard checks [M]:
  - It refuses an eval episode, `SPLIT≠public`, an output path without "oracle", a missing `--xform`, and a trk file
    without the episode (rc 1 or 2).
  - Fixed in this step: a refusal now writes nothing. X is resolved before the output folder is made.
  - The new file gives byte-identical output on all 20 episodes: 40/40 converted files (geom and trk, 20 episodes) array- and dtype-identical to the files the test run wrote.
- `oracle_poses.py --xform FILE` (opt-in, needs `--meshes`):
  - It takes X from the file instead of the kit registration.
  - It adds `*_star` scores, which take the tracks to scan frames by the same X.

`oracle_poses.py` [M]:

| ep | X | raw vs mocap, lib / \* | after mkref snap, lib / \* | expected snap cm | frame-0 centre vs perception cm |
|---|---|---|---|---|---|
| 11 | X_kit | 1.000 / – | 0.9688 / – | blue −0.49, beige +0.78 | 1.30, 0.95 |
| 11 | X\*_geom | 0.9973 / **1.000** | 0.9688 / 0.9688 | blue −0.75, beige +1.05 | 0.81, 1.02 |
| 13 | X_kit | 1.000 / – | 1.000 / – | blue −0.30, rack +0.67 | 0.50, 0.58 |
| 13 | X\*_geom | 0.9061 / **1.000** | 0.9061 / 1.000 | blue +0.06, rack +0.37 | 0.68, 0.76 |
| 31 | X_kit | 1.000 / – | 0.9688 / – | sweeper −0.38, rack +0.66 | 0.31, 0.34 |
| 31 | X\*_geom | 0.9688 / **1.000** | 0.9688 / 1.000 | sweeper −0.29, rack +0.56 | 0.65, 0.65 |

- Mocap taken to lib frames by X\*_geom scores 1.000 in the \* convention.
- In the lib convention it reproduces (a3) exactly: 0.9973 / 0.9061 / 0.9688.
- Up vs the table normal stays ≤ 0.04°, and the support check passes.
- The ep31 snap cost (0.031, known from the oracle-twin PREREG) disappears under X\*_geom. It is threshold
  quantisation, not a large error: the relative snap of sweeper and rack is 1.04 cm under X_kit and 0.85 cm under
  X\*_geom, against the scorer's first ADD threshold of 1 cm. Snap readings near 1 cm are therefore fragile [M].

## Tests (a) and (b) on all 20 public episodes
- (a1) mocap with the scan as the submitted mesh, through the kit's own `pack_object_meshes` and the unmodified
  official `metric_code/track_3/AUC.py score()`.
  - The host solution is built from mocap + scan, as `score_registered.py` builds it.
  - The decode limit is raised only for this full-resolution stand-in, as `refcheck/scorer/kit_e2e.py` does.
- (a2) mocap · X_kit with library_v3 submitted.
- (a3) mocap · X\*_geom with library_v3 submitted: the leaderboard score of a perfect physical motion of our mesh.
  It is also recomputed in process.
- (a4) lib → scan → lib round trip through `frame_xform.py`, on both files, by X\*_geom and by X\*_trk.
- (b1) T\* two ways, on the refine/in tracks:
  - (i) `frame_xform.py --to scan`, scored by the kit chain with the full-resolution scan as the candidate. The kit's
    `_register_object_body` then returns the identity, checked to ≤ 6e-16.
  - (ii) in process, with X\*_geom as the registration.
  - Rule: ≤ 0.002 per episode and object.
  - Beside it, no rule: (i′) the same file through `score_registered.py`, whose candidate is the 4096-face budgeted
    scan, so it includes the kit's scan→scan registration noise.
  - (b0) also checks `score_registered.py --meshes library_v3` against the in-process lib chain.
- (b2) X\*_geom spun by 45/90/145/180° about the scan axis: |ΔT\*| ≤ 0.002.
- (b3) rivals, no rule.
- (b4) T_trk two ways, and against the value recorded in `xstar_trk.json`.

| ep | objects | (a1) | (a2) | (a3) official / in process | round trip f32 / f64 | (b1) T\* file / in process / budget scan | lib file / in process | (b2) spin max abs Δ | T_lib | T\* | T_trk (pick) | T_trk_ls | L1 = T_lib − T\* | bias = T_trk − T\* |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | white_pot + white_pot_lid | 1.0000 | 1.0000 | 0.9858 / 0.9858 | 6e-08 / 2e-16 | 0.9612 / 0.9612 / 0.9603 | 0.9641 / 0.9641 | – | 0.9641 | 0.9612 | 0.9959 (opt_from_geom) | 0.9951 | +0.0029 | +0.0347 |
| 2 | white_pot + white_pot_lid | 1.0000 | 1.0000 | 1.0000 / 1.0000 | 6e-08 / 3e-16 | 0.9792 / 0.9792 / 0.9785 | 0.9823 / 0.9823 | – | 0.9823 | 0.9792 | 0.9955 (opt_from_ls) | 0.9941 | +0.0031 | +0.0163 |
| 11 | blue_cup + beige_cup | 1.0000 | 1.0000 | 0.9973 / 0.9973 | 6e-08 / 3e-16 | 0.8739 / 0.8739 / 0.8723 | 0.8978 / 0.8978 | 0.0018 | 0.8978 | 0.8739 | 0.9302 (opt_from_geom) | 0.8891 | +0.0239 | +0.0563 |
| 12 | blue_cup + plastic_dish_rack | 1.0000 | 1.0000 | 0.9477 / 0.9477 | 6e-08 / 3e-16 | 0.9738 / 0.9738 / 0.9741 | 0.9662 / 0.9662 | 0.0003 | 0.9662 | 0.9738 | 0.9991 (opt_from_geom) | 0.9974 | -0.0076 | +0.0253 |
| 13 | blue_cup + plastic_dish_rack | 1.0000 | 1.0000 | 0.9061 / 0.9061 | 6e-08 / 3e-16 | 0.9036 / 0.9036 / 0.9097 | 0.9605 / 0.9605 | 0.0009 | 0.9605 | 0.9036 | 0.9748 (opt_from_ls) | 0.9722 | +0.0569 | +0.0712 |
| 18 | mini_sweeper + mini_dust_pan | 1.0000 | 1.0000 | 1.0000 / 1.0000 | 6e-08 / 3e-16 | 0.9680 / 0.9680 / 0.9672 | 0.9642 / 0.9642 | – | 0.9642 | 0.9680 | 0.9971 (opt_from_ls) | 0.9944 | -0.0038 | +0.0291 |
| 21 | blue_cup + water_pitcher | 1.0000 | 1.0000 | 0.9708 / 0.9708 | 6e-08 / 3e-16 | 0.8313 / 0.8313 / 0.8184 | 0.8325 / 0.8325 | 0.0003 | 0.8325 | 0.8313 | 0.9945 (opt_from_ls) | 0.9677 | +0.0012 | +0.1632 |
| 22 | blue_cup + water_pitcher | 1.0000 | 1.0000 | 0.9592 / 0.9592 | 6e-08 / 3e-16 | 0.8710 / 0.8710 / 0.8707 | 0.8710 / 0.8710 | 0.0000 | 0.8710 | 0.8710 | 0.9950 (opt_from_ls) | 0.9940 | +0.0000 | +0.1240 |
| 23 | wooden_piece_1 + wooden_piece_2 | 1.0000 | 1.0000 | 1.0000 / 1.0000 | 6e-08 / 2e-16 | 0.0418 / 0.0418 / 0.0418 | 0.0414 / 0.0414 | – | 0.0414 | 0.0418 | 0.0418 (geom) | 0.0428 | -0.0004 | +0.0000 |
| 24 | wooden_piece_1 + wooden_piece_2 | 1.0000 | 1.0000 | 1.0000 / 1.0000 | 6e-08 / 3e-16 | 0.8105 / 0.8105 / 0.8089 | 0.8117 / 0.8117 | – | 0.8117 | 0.8105 | 0.9859 (opt_from_ls) | 0.9659 | +0.0012 | +0.1754 |
| 26 | plastic_dish_rack + white_pot | 1.0000 | 1.0000 | 0.9877 / 0.9877 | 6e-08 / 2e-16 | 0.9565 / 0.9565 / 0.9573 | 0.9652 / 0.9652 | – | 0.9652 | 0.9565 | 0.9947 (opt_from_ls) | 0.9933 | +0.0087 | +0.0382 |
| 27 | plastic_dish_rack + white_pot | 1.0000 | 1.0000 | 0.9789 / 0.9789 | 6e-08 / 2e-16 | 0.9376 / 0.9376 / 0.9421 | 0.9611 / 0.9611 | – | 0.9611 | 0.9376 | 0.9971 (opt_from_ls) | 0.9964 | +0.0235 | +0.0595 |
| 31 | mini_sweeper + plastic_dish_rack | 1.0000 | 1.0000 | 0.9688 / 0.9688 | 6e-08 / 3e-16 | 0.8391 / 0.8391 / 0.8426 | 0.7999 / 0.7999 | – | 0.7999 | 0.8391 | 0.9976 (opt_from_geom) | 0.9579 | -0.0392 | +0.1585 |
| 39 | mini_dust_pan | 1.0000 | 1.0000 | 1.0000 / 1.0000 | 6e-08 / 2e-16 | 0.9804 / 0.9804 / 0.9767 | 0.9602 / 0.9602 | – | 0.9602 | 0.9804 | 0.9961 (opt_from_ls) | 0.9931 | -0.0202 | +0.0157 |
| 40 | mini_dust_pan | 1.0000 | 1.0000 | 1.0000 / 1.0000 | 6e-08 / 3e-16 | 0.9740 / 0.9740 / 0.9738 | 0.9570 / 0.9570 | – | 0.9570 | 0.9740 | 0.9853 (ls) | 0.9853 | -0.0170 | +0.0113 |
| 41 | white_pot | 1.0000 | 1.0000 | 0.9967 / 0.9967 | 6e-08 / 2e-16 | 0.9881 / 0.9881 / 0.9881 | 0.9910 / 0.9910 | – | 0.9910 | 0.9881 | 0.9941 (opt_from_ls) | 0.9933 | +0.0029 | +0.0060 |
| 42 | white_pot | 1.0000 | 1.0000 | 0.9550 / 0.9550 | 6e-08 / 3e-16 | 0.9740 / 0.9740 / 0.9759 | 0.9915 / 0.9915 | – | 0.9915 | 0.9740 | 0.9966 (opt_from_ls) | 0.9912 | +0.0175 | +0.0226 |
| 43 | white_pot | 1.0000 | 1.0000 | 0.9503 / 0.9503 | 6e-08 / 3e-16 | 0.9429 / 0.9429 / 0.9446 | 0.9482 / 0.9482 | – | 0.9482 | 0.9429 | 0.9952 (opt_from_ls) | 0.9881 | +0.0053 | +0.0523 |
| 44 | white_pot | 1.0000 | 1.0000 | 1.0000 / 1.0000 | 3e-08 / 2e-16 | 0.9982 / 0.9982 / 0.9982 | 0.9967 / 0.9967 | – | 0.9967 | 0.9982 | 0.9987 (opt_from_ls) | 0.9982 | -0.0015 | +0.0005 |
| 45 | white_pot | 1.0000 | 1.0000 | 0.9858 / 0.9858 | 6e-08 / 3e-16 | 0.9789 / 0.9789 / 0.9787 | 0.9795 / 0.9795 | – | 0.9795 | 0.9789 | 0.9903 (opt_from_ls) | 0.9897 | +0.0006 | +0.0114 |

Means over 20 eps: T_lib 0.8921, T\* 0.8892, T_trk 0.9428, T_trk_ls 0.9350; L1 +0.0029 (12 eps > 0, 7 < 0); bias +0.0536.
Without ep23 (identity swap): T_lib 0.9369, T\* 0.9338, T_trk 0.9902, T_trk_ls 0.9819; L1 +0.0031; bias +0.0564.
(a3) perfect motion under the lib convention: mean 0.9795, min 0.9061, 13/20 eps < 1.

(b3) rivals (per-object ΔAUC on the tracks; ep23's tracks have the two pieces swapped):

| rival | residual ratio | rot from best | ADD from best | eps | mean Δ | min | max |
|---|---|---|---|---|---|---|---|
| white_pot#1 | 1.080 | 7° | 0.84 cm | 9 | -0.0545 | -0.1326 | -0.0067 |
| white_pot_lid#1 | 1.062 | 157° | 2.52 cm | 2 | -0.1928 | -0.2286 | -0.1571 |
| mini_sweeper#1 | 1.015 | 180° | 4.48 cm | 2 | -0.6389 | -0.7323 | -0.5455 |
| wooden_piece_1#1 | 1.079 | 180° | 6.47 cm | 2 | -0.3655 | -0.7272 | -0.0039 |
| wooden_piece_2#1 | 1.038 | 180° | 14.63 cm | 2 | -0.3787 | -0.8473 | +0.0900 |
| wooden_piece_2#2 | 1.068 | 180° | 12.30 cm | 2 | -0.4159 | -0.8473 | +0.0156 |
| wooden_piece_2#3 | 1.068 | 180° | 6.50 cm | 2 | -0.2867 | -0.5734 | +0.0000 |

L1 per object (by-product for A1):

| object | eps | mean | min | max | eps with \|L1\| ≥ 0.03 |
|---|---|---|---|---|---|
| beige_cup | 1 | +0.0475 | +0.0475 | +0.0475 | 11 (+0.047) |
| blue_cup | 5 | -0.0026 | -0.0583 | +0.0632 | 12 (-0.058), 13 (+0.063) |
| mini_dust_pan | 3 | -0.0147 | -0.0202 | -0.0070 | – |
| mini_sweeper | 2 | -0.0066 | -0.0129 | -0.0004 | – |
| plastic_dish_rack | 5 | +0.0055 | -0.0655 | +0.0507 | 12 (+0.043), 13 (+0.051), 31 (-0.066) |
| water_pitcher | 2 | +0.0104 | +0.0073 | +0.0135 | – |
| white_pot | 9 | +0.0098 | -0.0015 | +0.0470 | 27 (+0.047) |
| white_pot_lid | 2 | +0.0066 | +0.0065 | +0.0067 | – |
| wooden_piece_1 | 2 | +0.0010 | -0.0008 | +0.0028 | – |
| wooden_piece_2 | 2 | -0.0002 | -0.0003 | +0.0000 | – |

```
{
 "a1_min": 1.0,
 "a2_min": 1.0,
 "a3_mean": 0.9795,
 "a3_min": 0.906086,
 "a4_round_trip_max_abs": 5.960464477539063e-08,
 "a4_world_T_cam_identical": true,
 "b1_max_abs_delta": 0.0,
 "b1_full_scan_self_registration_max_abs": 8.881784197001252e-16,
 "b1b_budget_scan_max_abs_delta": 0.0248,
 "b1b_budget_scan_mean_delta": -0.0002,
 "b0_max_abs_delta": 0.0,
 "b2_max_abs_delta": 0.0018,
 "a3_inprocess_max_abs_delta": 0.0,
 "means": {
  "lib": 0.8921,
  "star": 0.8892,
  "star_budget_scan": 0.889
 },
 "pass": {
  "a1": true,
  "a2": true,
  "a4": true,
  "a3_inprocess": true,
  "b1": true,
  "b2": true,
  "b0": true,
  "b4": true,
  "a4_trk": true
 },
 "b4_max_abs_delta": 0.0,
 "b4_max_abs_delta_recorded": 0.0,
 "b4_round_trip_max_abs": 5.960464477539063e-08
}
```

## What this hands to Tier A (A1) and the cells
- **Use X\*_geom** (`xstar_geom.json`, md5 919ea341…) for every lib ↔ scan conversion in cells c2–c6. X_kit is used
  only for the lib score (PLAN risk 1).
- **The lib column of O references.**
  - Mocap taken to lib frames by X\*_geom scores, in the leaderboard (lib) convention, (a3): mean 0.9795, min 0.9061
    (ep13), with 13/20 episodes below 1.
  - orcB's O arm used X_kit, so it scores 1.000 in lib by construction. c3's lib column and orcB's O therefore differ
    by design.
  - Read stage leaks on \*, as the plan says.
- **A1 by-products on refine/in [M]** (the A1 verdict still needs B3's 50-perturbation flip rate):

  | | T_lib | T\* | T_trk | T_trk_ls |
  |---|---|---|---|---|
  | 20 eps | 0.8921 | 0.8892 | 0.9428 | 0.9350 |
  | ep23 excluded | 0.9369 | 0.9338 | 0.9902 | 0.9819 |

  - L1 = T_lib − T\* averages +0.0029 (12 episodes positive, 7 negative). That is inside the plan's reference-level
    "no leak" band |ΔR| < 0.005.
  - Per object it swings from −0.066 (rack, ep31) to +0.063 (blue cup, ep13).
  - No object loses ≥ 0.03 in ≥ 2 episodes: the only losses ≥ 0.03 are rack ep31 (−0.066) and blue cup ep12 (−0.058).
  - The budget-scan check shows the kit's own registration noise reaches 0.025 per object, so per-object L1 below
    that is not distinguishable from the kit's registration noise.
- **Constant bias [M, upper bound].** T_trk − T\* = +0.054 over 20 episodes, +0.056 without ep23.
  - One constant offset per (episode, object) would close 85 % of the remaining 1 − T\* gap (73 % with the plain LS
    fit). The gap is 0.066 without ep23.
  - Largest: ep24 +0.175, ep21 +0.163, ep31 +0.159, ep22 +0.124.
  - This is the input for A2 (phase split) and A5 (frame-0 re-anchor).
- **Physics cells.** For ep11, the beige cup's spin under X\*_geom is 90° from our lib frame, against 145° under X_kit
  (oracle_poses `mesh_frame_offset`).
  - Our beige mesh is not axisymmetric about the scan axis.
  - c2/c3 physics on ep11, which simulates our mesh, therefore depends on a spin that the surface fit sets only
    weakly (8.0 vs 9.0 mm). c4–c6 simulate the scan and are unaffected. The spin does not matter to any score (b2).
- **Guard (B8).** `tools/no_oracle.py` matches `oracle|<date>-orc` only, so a path naming `xstar_trk.json` would pass
  it. B8 should add `xstar` to its pattern. `frame_xform.py` outputs already need "oracle" in their path.

## Hypotheses and the experiments that would falsify them
- [H1] X\*_geom, the unscaled minimum-surface-distance fit, is the frame relation our tracker realises.
  - For: every rival minimum loses on the tracks.
  - Against: X\*_trk sits as far from X\*_geom as from X_kit (1.30 vs 1.24 cm).
  - Falsifier: the Phase-1 P_o vs P_s tracks on the same depth cache. If, over rest frames, the median constant offset
    P_o⁻¹·P_s differs from X\*_geom⁻¹ by more than 0.5 cm and more than 2× the P_o-repeat noise, for one object in
    ≥ 12/20 episodes, then X\*_geom is not the tracker's relation for that object, and stage leaks read on \* would
    book that offset as tracking error.
- [H2] The cups' 12–14 % size deficit causes most of the cup L1 and part of the cup L2.
  - Falsifier: Phase-1 L2 on the cup episodes. If R\*(P_s) − R\*(P_o) < 0.01, size is not a material cause.
- [H3] Most of T_trk − T\* is frame-0 initialisation error held over rest periods, not a template body-frame bias.
  - Falsifier: A5, re-anchoring at the mocap frame-0 pose. If it recovers less than half of T_trk − T\* on the
    objects that move more than 30°, the offset is a template bias, not an init error.
- [H, thresholds]
  - AMBIG = 1.10 (rival residual ratio) and DISTINCT_CM = 0.5 only decide what is reported.
  - TRK_MAX_CM = 5 cm binds only on ep23 [M]. Every other X\*_trk is ≤ 3.3 cm from X\*_geom (lid, ep0).

## Files
- `tools/xstar_fit.py`: B1. Changed in this step: each minimum also stores its X.
- `pipeline/frame_xform.py`: B2. Changed in this step: a refusal writes nothing.
- `pipeline/oracle_poses.py --xform`: unchanged in this step; the review kept it.
- `docs/research/work/leak-decomp-20261030/tierA/`:
  - `xstar_geom.json` + `.log`;
  - `xstar_trk.json` + `.log`;
  - `frames_check.py`: tests. Added in this step: (a3) in process, (b3), (b4), `--xtrk`;
  - `frames_check.json`;
  - `frames_tables.py`;
  - `oracle_poses_xform/*.oracle.json`;
  - this file.
- Scratch (not in git):
  - `$S/leak/oracle_frames_v2/ep*`: converted tracks, kit mesh roots, `score_registered` outputs;
  - `$S/leak/oracle_poses_xform/`;
  - `$S/leak/logs/`;
  - `$S/leak/scripts/{cup_selfsym,trk_vs_kit}.py`;
  - earlier attempt: `$S/leak/*_try.json`, `xstar_trk_v0_nocap.json`.
