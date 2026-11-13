# Tier A of the leak decomposition: reference-level audits on the 20 public episodes (P_o = `refine/in`)

30 Oct 2026, 17:15–22:50 UTC (two sessions, split by a usage limit). Plan items A1–A7 of `../PLAN.md` §3, read by the
§4 reference-level rule. CPU only, on this VM (4 cores, shared with other agents), $0. Labels: [M] measured,
[E] estimate, [H] hypothesis. LB = leaderboard AUC.

**Oracle side.** Every number here reads mocap and the public scans, on public episodes only. Nothing feeds eval
inference. No registration correction, re-anchor or settle variant from here becomes a default anywhere. Outputs
carry `oracle` / `leak-decomp` in their paths, and `tools/leak_tierA.py` refuses eval episodes and `SPLIT≠public`.

Track = P_o, the `refine/in` perception set (tracks from `runs/20261025-guard-fe3f407`, hands from the g1/auto18 runs,
depth frame 0; library_v2 templates = library_v3 except the sweeper's flattened underside, FRAMES.md). The Phase-1
tracks (P_o, P_s, P_o repeat; `20261030-orcP1{a,b,c}-87fc869`) are not used here. The plan's re-run of A2/A5 on them,
and the L2/L3 split through P_s, is the next step.

## Verdicts

PLAN §4 reference-level rule, on all 20 episodes: mean ΔR ≥ 0.01 and ≥ 12/20 episodes positive → leaks; the same
negative → truth worse; |mean ΔR| < 0.005 → no leak; else inconclusive. ΔR is what the true version of the stage gains,
so ΔR > 0 is a leak. L_LB = (c/20)·Σ_e 1.025·S_e·ΔR(twin(e)) over the 7 evals with S_e ≥ 0.8 (1, 8, 19, 20, 25, 28,
38), c 0.74–1.0 [E] (PLAN §2). Without ep23 (identity swap) only where it changes the reading.

| Leak | Tier A quantity [M] | mean ΔR (20 eps) | eps + / − | verdict | L_LB [E] | PLAN §4 consequence |
|---|---|---|---|---|---|---|
| L1 registration | T\* − T_lib, public scan, each episode's own seed | −0.0029 | 7 / 12 | no leak | −0.0002 | no object loses ≥ 0.03 in ≥ 2 episodes → no registration-safe swap from this |
| L1 registration | seed only, full-resolution public scan as host: T_lib own seed − mean over 50 seeds | +0.0012 | 9 / 11 | no leak | +0.001 | only the sweeper flips (2/50); a full-resolution host is ruled out by the 16 MB limit (26 Oct review) |
| L1 registration | host-scan perturbation, welded (30 % decimation, 1 mm, 10 % holes) [H model] | running | | | | a1_v2 started 23:11 UTC |
| (L1 beside) | constant body bias T_trk − T\* (oracle upper bound, not a fix) | +0.0536 | 19 / 0 | leaks | +0.017 to +0.023 | read with A5 |
| L2 + L3 | tracking loss of P_o on \*, 1 − R\* | +0.1108 (+0.0662 without ep23) | 20 / 0 | leaks | +0.018 to +0.024 | P_s (Phase 1) splits template from tracker |
| L3 phase | frame 0 | +0.0002 | 12 / 0 | no leak | 0.0000 | – |
| L3 phase | untouched rest | +0.0277 (+0.0189) | 13 / 0 | leaks | +0.002 to +0.003 | – |
| L3 phase | held-moving | +0.0330 (+0.0272) | 20 / 0 | leaks | +0.008 to +0.011 | – |
| L3 phase | post-release | +0.0498 (+0.0199) | 15 / 0 | leaks | +0.008 to +0.011 | – |
| L3 occlusion | loss in hand-occluded frames [proxy H] | +0.0182 (+0.0113) | 12 / 0 | leaks (inconclusive without ep23) | +0.002 to +0.003 | occluded frames: 14 % of object-frames, about 17 % of the loss |
| L3 init (A5) | frame-0 re-anchor gain, body form | +0.0504 | 19 / 0 | leaks | +0.014 to +0.019 | 77 % of 1 − R\* without ep23; ≈ T_trk − T\* |
| L3 drift (A5) | loss left after the re-anchor | +0.0604 (+0.0155) | 20 / 0 | leaks | +0.004 to +0.006 | – |
| L4 on O | whole chain raw → S2 + a + rest settle | +0.0272 | 20 / 0 | leaks | (+0.007 to +0.010, bound only) | action rule met: stage a on 4 objects, rest settle on 6 (≥ 0.02 each) |
| L4 on O | stage a (table + snap) / rest settle / S2 | +0.0156 / +0.0084 / +0.0031 | 4/0, 16/1, 19/1 | inconclusive / inconclusive / no leak | – | – |
| L4 on P | whole chain | +0.0024 | 8 / 12 | no leak | −0.002 | no amplification on P |
| L4 on P | stage a / rest settle / S2 | +0.0093 / −0.0030 / −0.0039 | 9/3, 9/11, 3/17 | inconclusive / no leak / no leak | +0.002 / −0.003 / −0.001 | snap costs, settle and S2 gain |
| L6 hands | arrival / leave vs the true motion; fingertip gap | −14 / +34 frames; 0.26 cm | – | no rule (input to H_t) | – | c7/c8 gate not evaluated (B6 not built) |
| A6 | scorer sanity, frame invariance | all pass | – | – | – | FRAMES.md |
| A7 gate | 2 s hands-free settle of mocap rest configurations, scan collision | pass on 3 of 10 twins | – | gate | – | c4–c6 valid only on ep21, ep27, ep39 by the pre-registered gate |

## What this means for Phase 2 and the eval pipeline (decisions for the owner)
1. **A7 gate: scan geometry fails on 7 of 10 twins [M].**
   - The pre-registered gate is every object ≤ 1 cm and ≤ 5° after 2 s, on hand-free configurations. It passes only on
     ep21, ep27 and ep39. It fails on ep2, 11, 12, 13, 18, 24 and 31.
   - Three of those fails are marginal: ep11 (0.73 cm / 5.3°), ep18 (0.52 cm / 6.4°) and ep13 (1.11 cm / 6.7°).
   - The other four are not: ep2 (lid slides 1.9 cm on the pot), ep12 (cup in the rack 3.0 cm / 21°), ep24 (board 1.6
     cm / 17°) and ep31 (sweeper 14° at frame 0).
   - In the failing hand-free scan cases, the jolt after one control frame is 0.08–0.63 cm, against final drifts of
     0.5–3.0 cm or 5–21°. So the objects slide or topple over 1–2 s. That is not an initial-penetration artefact.
   - By the plan, cells c4–c6 run only on ep21, ep27 and ep39, unless the owner changes the gate. Changing a gate after
     seeing the data must be logged as a deviation.
   - The lib geometry fails worse: 8 of 10 twins.
     - At the true frame-0 pose, our beige cup (ep11), sweeper (ep18) and pitcher (ep21) stand on 0.9–3.3 cm²
       footprints with the centre of mass outside them. The pitcher also sits 2.5 cm into the table.
     - The scans stand on 8–52 cm² footprints, centre of mass inside (`scripts/a7_support_check.py`).
     - For these three, the cause is the base of our meshes, not the simulator.
     - So c3 (mocap on our meshes) needs mkref's snap and rest settle to be physical at all. It then moves away from the
       truth, which the A3 O-arm numbers below measure.
   - **ep11 detail [M].** The beige cup's spin is free for the score (FRAMES b2) but not for the physics.
     - At X\*_geom's spin (90°) it topples at frame 0 with or without the ev10 carve pieces (88° / 91°).
     - At X_kit's spin (145°, orcB's O arm) it topples in plain lib (91°) but holds with the ev10 pieces (0.86 cm / 3.8°
       at 2 s). That is orcB's configuration, and it is consistent with orcB's O arm reaching 0.940.
     - c2/c3 on ep11 should therefore keep X_kit's cup spin, which needs no mocap, and the ev10 pieces. Otherwise c3 is
       not comparable with orcB.
2. **Registration (L1).**
   - On the public scan at each public episode's own seed, there is no leak (−0.003). No object loses ≥ 0.03 in two
     episodes.
   - The risk is a flip. The sweeper and board-1 registrations have a 180° second minimum within 1.5 % / 8 % of the best
     residual (FRAMES). Each is its scene's anchor (the first object without a symmetry axis), and the kit aligns the
     whole scene on the anchor's frame-0 pose. So a flip moves every object: ep18 0.96 → 0.22, ep31 0.80 → 0.10.
   - **Seed only** (`a1seed`, full-resolution public scan as host, 50 pseudo-episode seeds):
     - Only the sweeper flips: 2 of 50 (4 %, 95 % CI 0.5–14 %). Board 1 is 0/50, and so is every other object.
     - The mean scene change is +0.001: no leak.
     - This reproduces the 26 Oct robustness review: 4 of 40 random seeds,
       `docs/analysis/robustness-review-20261026/refcheck/scorer/README.md` §2b–2d.
   - **The hidden host is not the full-resolution scan.**
     - One 16 MB decode limit covers all objects, and the public scans need 94.5 MB [M, 26 Oct].
     - That review registered our meshes at Kaggle's own eval seeds, GT-free, over 11 host resolutions. The sweeper
       flips at 1 of 11 on eval 19 and on eval 30. The boards flip at none.
     - A flip costs ≈ 0.7 episode AUC, ≈ 0.035 LB per flipped eval. Expected ≈ 2 × (1/11) × 0.035 ≈ 0.006 LB [E] if
       every host resolution is equally likely; the realised loss is 0, 0.035 or 0.07.
   - **Host-scan perturbation (corrected).**
     - The earlier attempt decimated the public scans unwelded. They are triangle soups (3 vertices per face), so the
       copies' centroids moved 7–13 mm and their radii ×1.11–1.27. That is the invalid procedure of the 26 Oct review.
     - Its flip rates (sweeper 52/100, board 1 51/100) are artefacts. That run is kept as `a1.json` and superseded by
       `a1_v2.json`, which welds first, as the kit's `budget_mesh` does.
     - The corrected run (a1_v2) is still running; this line is filled when it ends.
   - Tier A adds no new registration action: the PLAN §4 rule (a loss ≥ 0.03 on one object in ≥ 2 episodes) is not
     met. The sweeper flip stays the one registration item. A flip-safe sweeper must show 0/50 flips here and none
     across host resolutions at the eval seeds.
3. **Tracking (L2 + L3) is the largest reference-level loss: 0.066 without ep23 [M], 0.018–0.024 LB [E].**
   - About three quarters of it is one constant body-frame offset per object, already present at frame 0 (A5 body
     re-anchor 0.051 ≈ the constant-offset bound T_trk − T\* 0.056). That offset persists through the motion:
     post-release loss falls from 0.020 to 0.003 after the frame-0 re-anchor.
   - Drift is 0.016. Hand occlusion is not the driver: 1.27× the loss per frame on 14 % of the frames, by an [H] proxy.
   - By the §4 table this points at "frame-0 init" over "held span", "static freeze" or "occlusion".
   - But a frame-0 re-anchor cannot tell an init error from a template body-frame bias: both are constant in the body
     frame. Phase-1 P_s, the same init with the scan template, decides between them. Note that FRAMES' H3 falsifier
     (ratio 0.867 ≥ 0.5, not falsified) has the same blind spot.
   - The 5 largest object losses: pitcher ep21/22 (0.33 / 0.26, ≈ all a constant offset), rack ep31 (0.25, an untouched
     object, all constant), board 1 / 2 ep24 (0.23 / 0.15; board 2's offset changes after frame 0, re-anchor +0.010 of
     +0.139), blue cup ep11 (0.14, an untouched cup drifting while still: re-anchor +0.001; the known static-freeze case).
4. **Construction (L4).**
   - On mocap the chain costs 0.027 (20/20 episodes) and meets the §4 action rule for the snap (4 objects) and the rest
     settle (6 objects).
   - On P it costs nothing on average (+0.002). The snap costs 0.009, while the settle (−0.003) and S2 (−0.004) gain.
   - The stage that matters on eval is P, so the action is a GT-free fix gated on P, not on O.
   - The clearest candidate [H] is the rest settle's turn onto the nearest stable pose for the white pot. On P it costs
     0.046 / 0.020 / 0.016 on the single-pot ep43 / 45 / 42. On O it costs 0.026–0.031 on ep27 / 42 / 43. On P it gains
     0.017–0.051 on the multi-object scenes ep12 / 13 / 24 / 27 / 31.
   - On mocap the snap moves an object by ≥ 1 cm, the scorer's first ADD threshold, only where our mesh's lowest point
     under the true pose is ≥ 1 cm off the table: pitcher 1.8–1.9 cm, pot 1.6 cm and rack 1.1 cm on ep26, beige cup
     1.05 cm. That is the same base mismatch as in A7.
5. **Hands (L6, timing only).**
   - Our hands reach within 2 cm of the true surface 14 frames (0.7 s) before the object starts to move, and stay within
     2 cm for 34–36 frames (≥ 1.7 s) after it stops. These are first / last segment medians. The leave lag is a lower
     bound: 28 of 62 segments are still near at the edge of a ±120-frame window.
   - Our object tracks start and stop moving within 0–1 frame of the truth.
   - During true motion, the measured fingertips are 0.26 cm (median) from the true surface.
   - Exception: in the pitcher pours (ep21, ep22) the pouring hand is measured in only 18–22 % of the pour.
   - These are the inputs to H_t (B6, not built). The c7/c8 gate (PLAN test (c)) is therefore not evaluated.
6. **LB size [E].** Reference-level conversion over the 7 evals with S ≥ 0.8:
   - tracking 0.018–0.024, of which frame-0 init / constant offset 0.014–0.019;
   - construction on P ≈ 0 (−0.002 to −0.003);
   - registration ≈ 0 at the public seeds and +0.001 seed-only; the sweeper flip risk ≈ 0.006 expected (26 Oct review).
   - Evals 10, 14 and 30 (S < 0.8) and the 10 spoon evals carry no [M] row.

## Review of the earlier attempt (17:15–19:45 UTC, cut by the usage limit)
Every Tier A output was already computed. This session reviewed the code, the inputs and the readings, re-checked
reproducibility, fixed two bugs (one in the A1 perturbation code, one in the reading) and added the checks below.
- **Code versions.**
  - a1, a3prep, a3 and a7 ran with the current `leak_tierA.py` (md5 896e0cfb, commit 20e3461).
  - a2 and a4 ran with 0f46a310 (87fc869). Its diff to the current file touches only a3prep (the optional joint
    depenetration) and a7 reading (hand gaps), so a2 and a4 are what the current code computes.
  - a7prep ran from an uncommitted working tree (md5 5b25b81d). Recomputing every rest configuration with the committed
    code gives identical frames and config arrays, max difference 0 (`scripts/a7prep_repro.py`).
- **Bug fixed in `tools/leak_tierA.py` (A1).**
  - `perturb_scan` decimated the public scans as loaded. They are triangle soups (V/F = 3.00), so the stand-in host
    copies were distorted: centroid 7–13 mm, radius ×1.11–1.27, against ≤ 0.46 mm and 0.997–1.002 when welded first.
  - The 26 Oct review had already flagged this procedure as invalid (`sens2_INVALID_unwelded_decimation`).
  - It now welds first, as the kit's `budget_mesh` does. A1 was re-run as `a1_v2.json`; `a1.json` is kept, and only
    its perturbation columns are superseded.
- **Bug fixed in `results_tables.py`.**
  - The A3 verdicts used ΔR = R(after) − R(before). A costly stage was therefore labelled "truth worse".
  - Under PLAN §2 the leak is R(before) − R(after). The O chain now reads "leaks" (20/0), as the earlier snap-on-mocap
    finding (PLAN §5: 0.031 on ep11 / 31) predicts.
  - The verdicts also now use all 20 episodes, as pre-registered, with ep23 shown separately.
  - Also corrected: a note claimed every first hand arrival is at frame ≥ 10. On ep24 a fingertip is already 2.2 cm from
    board 1 at frame 0. The hand-free test reads the measured gaps, so it already excluded that frame.
- **Checked and kept.**
  - The per-frame loss split reproduces `score_track` to ≤ 1e-4 (asserted).
  - Mocap enters the perception world by X\*_trk's robust whole-track fit G. This is only used for occlusion and hand
    gaps.
  - The mocap frame-0 pose of a cup / lid is taken modulo its symmetry before the re-anchor (fixed in 87fc869).
  - The mkref stage-(a) emulation reproduces FRAMES' oracle_poses snap numbers: ep11 0.9688, ep13 / 31 1.000 on \*.
  - E2S + contacts leave object poses unchanged (stored runs: 0.0 cm). The grasp-lock ILC reference has the same object
    poses as its processed reference (5/5 stored runs).
  - Skipping mkref's 6 mm joint depenetration leaves the rest-settled poses unchanged (ep0, ep2: max difference 0.0 cm;
    `a3_depen_check.json`).
- **Added.**
  - `a1seed` (seed-only registration test).
  - `--a4_window` (A4 at ±120 frames).
  - Side checks: pitcher hands per side; ep11 lib at X_kit spin in A7; support footprints in A7.

## Hypotheses and the experiments that would falsify them
- [H-A5] The constant per-object body offset (77 % of the tracking loss without ep23) is mostly a template body-frame
  bias (our meshes differ from the scans: cups 12–14 % small, pitcher / rack residual 6–10 mm), not a frame-0 init error.
  - Falsifier: Phase-1 P_s (the same depth cache and init, with the scan as the template). Run A2/A5 on P_s. If P_s's
    body re-anchor gain is ≥ half of P_o's on the same objects (≥ 12/20 episodes), the offset is init, not template.
  - First sign from the Phase-1 job logs [M, unregistered, not scored here]: P_s ≥ 0.96 vs mocap on 16 episodes. That
    includes ep21 / 22, where P_o's pitcher carries a 0.25–0.32 constant offset.
- [H-A3] On the white pot, the rest settle's turn onto the nearest stable resting pose (≤ 15°) is what costs. On P:
  ep43 / 45 / 42 −0.046 / −0.020 / −0.016. On O: ep27 / 42 / 43 −0.026 to −0.031.
  - Falsifier: re-run A3's rest settle with the turn off (`max_tilt=0`, shift only) on all 20 episodes. If the pot
    losses stay ≥ 0.01, the turn is not the cause. If the multi-object gains (ep12 / 13 / 24 / 27 / 31, +0.017 to
    +0.051) fall below +0.01, the turn is needed there, and any fix must be per object.
  - Not run here: it is a construction fix, gated on P by the refine gate (PLAN §4).
- [H-A7] The scan-geometry settle failures come from the simulator's collision approximations (CoACD hulls of the scans,
  0.3 kg, default friction), not from the scans' shapes.
  - Falsifier: settle the same hand-free configurations with a finer decomposition (or the scan's own mesh as one
    collision body) and measured-order friction. If ≥ 4 of the 7 failing twins still fail, the approximations are not
    the cause.
  - Until then, the pre-registered gate stands.
- [H-A1] The sweeper's flip comes from its 180° near-tie: our mesh's two minima are within 1.5 % in residual, so the
  sampling of 3000 points decides. No object without a near-tie (≥ 8 %) flips at any seed.
  - Falsifier: a sweeper mesh whose second minimum is ≥ 10 % worse (e.g. the handle made asymmetric) still flipping in
    ≥ 1 of 50 seeds or 11 host resolutions.
- [H-A2] The occlusion proxy (≥ 20 % of the surface samples behind 1 cm hand capsules) is coarse. The 1.27× per-frame
  ratio could hide a larger effect on the frames where the hand truly covers the object.
  - Falsifier: the same split with 10 % / 40 % coverage and 0.5 / 2 cm capsules. If the occluded share of the loss stays
    ≤ 25 % at every setting, occlusion is not a main driver of L3 on P_o.

## Commands (this VM, 4 cores shared with other agents; code as noted per output)
`S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad`, `PY=$S/map/scoring/venv/bin/python`,
`D=docs/research/work/leak-decomp-20261030/tierA`, `W=$S/leak/oracle_tierA`. Common arguments `C="--perc $S/refine/in
--xgeom $D/xstar_geom.json --xtrk $D/xstar_trk.json --lib meshes/library_v3 --t3 $S/map/scoring/t3 --kit
$S/map/scoring/kit/v2d_submission_kit --work $W"`. Run from the repo root. Logs: `$D/logs/` (warp / newton
chatter removed).

| step | command | code (commit, leak_tierA md5) | wall time | output |
|---|---|---|---|---|
| A1 (superseded: unwelded perturbations) | `$PY -I tools/leak_tierA.py a1 $C --out $W/a1.json --jobs 4 --n_perturb 50` | 20e3461, 896e0cfb | 99.6 min | `a1.json` (its L1 and bias columns are valid) |
| A1 v2 | `$PY -I tools/leak_tierA.py a1 $C --out $W/a1_v2.json --episodes 11,13,21,12,22,18,0,2,31,26,27,24,23,40,41,39,42,43,45,44 --jobs 4 --n_perturb 50` | this step (welded), a7e57867 | running | `a1_v2.json` |
| A1 seed | `$PY -I tools/leak_tierA.py a1seed $C --out $W/a1seed.json --n_seed 50 --jobs 4` | a960523, 2ad44d29 | 58 min (registrations 29 min) | `a1seed.json` |
| A2 / A5 | `$PY -I tools/leak_tierA.py a2 $C --out $W/a2.json --jobs 2` | 87fc869, 0f46a310 (a2 code = current) | 9.8 min | `a2.json` |
| A3 prep | `$PY -I tools/leak_tierA.py a3prep $C --out $W/a3prep.json --oracle_t3 $S/oracle/verify2/t3 --jobs 2` | 20e3461, 896e0cfb | 6.6 min | `a3prep.json`, `$W/a3/ep*/{P,O}_{base,S2}.npz` |
| A3 rest settle | `bash $D/scripts/run_rest.sh $W/logs/a3_rest_{1,2}.log EP...` (fcvenv, `tools/leak_settle.py rest`, 2 processes) | 20e3461, leak_settle 91edce14 | ≈ 20 min | `$W/a3/ep*/*_settle.npz` |
| A3 | `$PY -I tools/leak_tierA.py a3 $C --out $W/a3.json --stored $W/stored.json --jobs 3` | 20e3461, 896e0cfb | 17.1 min | `a3.json` |
| A3 depen check | `$PY -I $D/scripts/a3_depen_score.py $S` (inputs: `run_rest` on `*_depen.npz`, ep0 / 2) | this step | 1 min | `a3_depen_check.json` |
| A4 | `$PY -I tools/leak_tierA.py a4 $C --out $W/a4.json --jobs 2`; `... --out $W/a4_w120.json --a4_window 120 --jobs 2` | d51372e (a4 code = current); a960523 | 2.1 / 2.0 min | `a4.json`, `a4_w120.json` |
| A4 pitcher hands | `$PY -I $D/scripts/a4_pitcher_hands.py $S` | this step | < 1 min | printed (RESULTS §A4) |
| A6 | `$PY -I tools/leak_tierA.py a6 $C --out $W/a6.json --frames_check $D/frames_check.json` | d51372e | 0 s | `a6.json` |
| A7 prep | `$PY -I tools/leak_tierA.py a7prep $C --out $W/a7prep.json --jobs 1` | uncommitted 5b25b81d; reproduced bit-identically by `$D/scripts/a7prep_repro.py` on the committed code | 2.9 min | `a7prep.json`, `$W/a7/ep*/{lib,lib_carve,scan}.npz`, `$W/a7/assets/` |
| A7 settle | `bash $D/scripts/run_fc.sh settle $W/logs/a7_{lib,scan}.log $W/a7/ep*/{lib,lib_carve,scan}.npz` (fcvenv, `tools/leak_settle.py settle`, 40 control frames) | working tree of 18:19 (≈ 87fc869; `settle` unchanged since) | lib + lib + carve 11 min, scan 31 min, in parallel | `$W/a7/ep*/*_settle.json` |
| A7 | `$PY -I tools/leak_tierA.py a7 $C --out $W/a7.json --jobs 2` | 2cc6883, 896e0cfb | 2.2 min | `a7.json` |
| A7 ep11 X_kit | `$PY -I $D/scripts/a7_ep11_xkit_prep.py $S`; `bash $D/scripts/run_fc.sh settle $W/logs/a7_ep11_xkit.log $W/a7/ep11/{lib,lib_carve}_xkit.npz` | this step | 3 min | `$W/a7/ep11/*_xkit_settle.json` (numbers in §A7) |
| A7 footprints | `$PY -I $D/scripts/a7_support_check.py $W` | this step | < 1 min | printed (§A7) |
| tables | `python3 -I $D/results_tables.py $D` | this step | – | the appendix below |

## Files
- `tools/leak_tierA.py`. Changed in this step: the `a1seed` mode, `--n_seed`, `--a4_window`, and `perturb_scan` now welds
  the scan before decimating. Unchanged otherwise.
- `tools/leak_settle.py`: unchanged.
- `docs/research/work/leak-decomp-20261030/tierA/`:
  - `RESULTS.md` (this file);
  - `results_tables.py`: v2, with the A3 sign fixed, 20-episode verdicts and the new tables;
  - outputs: `a1.json` (superseded perturbation columns), `a1_v2.json`, `a1seed.json`, `a2.json`, `a3prep.json`, `a3.json`, `a3_depen_check.json`, `a4.json`, `a4_w120.json`,
    `a6.json`, `a7prep.json`, `a7.json`, `stored.json`, `a7_ep11_xkit_settle.json`;
  - `scripts/`: the side checks and the fcvenv runners;
  - `logs/`.
- Scratch (not in git; regenerable with the commands above):
  - `$W/a3/ep*` (stage npz, settle trees);
  - `$W/a7/` (assets, configuration npz, settle json);
  - `$W/a2_v0_worldspin.json` (the pre-87fc869 A2, superseded);
  - `$W/*_test.json`.

## Appendix: generated tables
`python3 -I docs/research/work/leak-decomp-20261030/tierA/results_tables.py` over the outputs in this folder: per-episode values, means, sign counts and verdicts; LB terms [E].

## Verdicts (PLAN §4 reference-level rule on the 20 public episodes: mean ΔR ≥ 0.01 and ≥ 12/20 episodes positive → leaks; the same negative → truth worse; |mean ΔR| < 0.005 → no leak; else inconclusive)

ΔR = what the true version gains (positive = a leak). L_LB = (c/20)·Σ_e a·S_e·ΔR(twin(e)) over the 7 evals with S_e ≥ 0.8 (1, 8, 19, 20, 25, 28, 38), a = 1.025, c 0.74–1.0 [E].

| quantity (ΔR per episode) | mean 20 eps | eps > 0 / < 0 | verdict (rule) | mean without ep23 | verdict without ep23 | L_LB [E] | note |
|---|---|---|---|---|---|---|---|
| A1 L1 registration, public scan, own seed: T\* − T_lib | -0.0029 | 7 / 12 | no leak | -0.0031 | no leak | -0.0002 to -0.0002 | [M] |
| A1 constant body bias T_trk − T\* (upper bound) | +0.0536 | 19 / 0 | **leaks** | +0.0564 | **leaks** | +0.0168 to +0.0226 | [M], oracle fit, not a fix |
| A1 seed only (public scan as host): T_lib own seed − mean over 50 seeds | +0.0012 | 9 / 11 | no leak | +0.0013 | no leak | +0.0011 to +0.0015 | [M] given host scan = public scan |
| A1 host-scan perturbation (UNWELDED soups: invalid, 30 % decimation, 1 mm, 10 % holes; a1.json): T\* − T_lib, mean of 50 | +0.0665 | 12 / 8 | **leaks** | +0.0704 | **leaks** | +0.0333 to +0.0450 | [M] under a perturbation model [H] |
| A2 tracking loss of P_o on \*: 1 − R\* (L2 + L3) | +0.1108 | 20 / 0 | **leaks** | +0.0662 | **leaks** | +0.0180 to +0.0243 | [M]; P_s splits L2 / L3 (Phase 1) |
| A2 phase f0 (frame 0) | +0.0002 | 12 / 0 | no leak | +0.0002 | no leak | +0.0000 to +0.0000 | [M] |
| A2 phase untouched rest (before the first true motion) | +0.0277 | 13 / 0 | **leaks** | +0.0189 | **leaks** | +0.0020 to +0.0027 | [M] |
| A2 phase held-moving (true motion ± 2 frames, and still between motions) | +0.0330 | 20 / 0 | **leaks** | +0.0272 | **leaks** | +0.0081 to +0.0109 | [M] |
| A2 phase post-release (after the last true motion) | +0.0498 | 15 / 0 | **leaks** | +0.0199 | **leaks** | +0.0079 to +0.0107 | [M] |
| A2 loss in hand-occluded frames (all phases) | +0.0182 | 12 / 0 | **leaks** | +0.0113 | inconclusive | +0.0024 to +0.0032 | [M]; occlusion proxy [H] |
| A5 init: frame-0 re-anchor gain, body form | +0.0504 | 19 / 0 | **leaks** | +0.0507 | **leaks** | +0.0137 to +0.0186 | [M], oracle |
| A5 drift: loss left after the body re-anchor, 1 − R\*_re | +0.0604 | 20 / 0 | **leaks** | +0.0155 | **leaks** | +0.0043 to +0.0058 | [M], oracle |
| A5 frame-0 re-anchor gain, world form | +0.0274 | 11 / 1 | inconclusive | +0.0265 | inconclusive | +0.0063 to +0.0085 | [M], oracle |
| A3 O (mocap), stage a: table + snap: R before − R after | +0.0156 | 4 / 0 | inconclusive | +0.0165 | inconclusive | +0.0032 to +0.0043 | [M], IK + contacts: 0 by construction (checked), LB upper bound only: O is not available on eval |
| A3 O (mocap), contact retarget: rest settle: R before − R after | +0.0084 | 16 / 1 | inconclusive | +0.0083 | inconclusive | +0.0029 to +0.0039 | [M], LB upper bound only: O is not available on eval |
| A3 O (mocap), S2 0.545-frame advance: R before − R after | +0.0031 | 19 / 1 | no leak | +0.0032 | no leak | +0.0011 to +0.0014 | [M], LB upper bound only: O is not available on eval |
| A3 O (mocap), whole chain raw → S2 + a + settle: R before − R after | +0.0272 | 20 / 0 | **leaks** | +0.0280 | **leaks** | +0.0071 to +0.0096 | [M], LB upper bound only: O is not available on eval |
| A3 P (P_o), stage a: table + snap: R before − R after | +0.0093 | 9 / 3 | inconclusive | +0.0098 | inconclusive | +0.0016 to +0.0022 | [M], IK + contacts: 0 by construction (checked) |
| A3 P (P_o), contact retarget: rest settle: R before − R after | -0.0030 | 9 / 11 | no leak | -0.0032 | no leak | -0.0037 to -0.0027 | [M] |
| A3 P (P_o), S2 0.545-frame advance: R before − R after | -0.0039 | 3 / 17 | no leak | -0.0040 | no leak | -0.0010 to -0.0007 | [M] |
| A3 P (P_o), whole chain raw → S2 + a + settle: R before − R after | +0.0024 | 8 / 12 | no leak | +0.0026 | no leak | -0.0025 to -0.0018 | [M] |

## A1 registration (L1) per episode and object [M] (source: a1.json)

| ep | object | T_lib | T\* | T_trk | L1 = T_lib − T\* | bias T_trk − T\* | E = X\*_geom X_kit⁻¹ ADD cm | perturbation: flips /50 | T_lib drops ≥ 0.03 /50 | perturbed L1 mean ± sd | seed only: flips /50 | seed only: T_lib drops ≥ 0.03 /50 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | pot | 0.9918 | 0.9926 | 0.9955 | -0.0008 | +0.0029 | 0.77 | 0 | 0 | -0.0022 ± 0.0012 | 0 | 0 |
| 0 | lid | 0.9363 | 0.9298 | 0.9963 | +0.0065 | +0.0665 | 0.26 | 0 | 5 | +0.0024 ± 0.0242 | 0 | 0 |
| 2 | pot | 0.9923 | 0.9929 | 0.9938 | -0.0006 | +0.0009 | 0.75 | 0 | 0 | -0.0015 ± 0.0010 | 0 | 0 |
| 2 | lid | 0.9723 | 0.9656 | 0.9973 | +0.0067 | +0.0317 | 0.24 | 0 | 12 | -0.0079 ± 0.0179 | 0 | 3 |
| 11 | blue | 0.8622 | 0.8618 | 0.8636 | +0.0004 | +0.0018 | 0.82 | 0 | 0 | -0.0003 ± 0.0018 | 0 | 0 |
| 11 | beige | 0.9334 | 0.8859 | 0.9968 | +0.0475 | +0.1109 | 1.48 | 0 | 20 | +0.0195 ± 0.0282 | 0 | 0 |
| 12 | blue | 0.9327 | 0.9910 | 0.9983 | -0.0583 | +0.0073 | 0.76 | 0 | 29 | -0.0912 ± 0.0296 | 0 | 12 |
| 12 | rack | 0.9997 | 0.9565 | 1.0000 | +0.0432 | +0.0435 | 1.39 | 0 | 16 | +0.0250 ± 0.0206 | 0 | 2 |
| 13 | blue | 0.9329 | 0.8697 | 0.9497 | +0.0632 | +0.0800 | 0.88 | 0 | 1 | +0.0626 ± 0.0083 | 0 | 0 |
| 13 | rack | 0.9882 | 0.9375 | 1.0000 | +0.0507 | +0.0625 | 1.13 | 0 | 12 | +0.0413 ± 0.0213 | 0 | 2 |
| 18 | sweeper | 0.9952 | 0.9956 | 0.9965 | -0.0004 | +0.0009 | 0.30 | 27 | 27 | -0.3118 ± 0.2905 | 2 | 2 |
| 18 | pan | 0.9333 | 0.9403 | 0.9977 | -0.0070 | +0.0574 | 0.21 | 0 | 27 | -0.5071 ± 0.4738 | 0 | 8 |
| 21 | blue | 0.9815 | 0.9926 | 1.0000 | -0.0111 | +0.0074 | 0.89 | 0 | 7 | -0.0222 ± 0.0173 | 0 | 0 |
| 21 | pitcher | 0.6835 | 0.6700 | 0.9889 | +0.0135 | +0.3189 | 1.75 | 0 | 21 | -0.0371 ± 0.1410 | 0 | 12 |
| 22 | blue | 0.9924 | 0.9997 | 1.0000 | -0.0073 | +0.0003 | 0.85 | 0 | 2 | -0.0102 ± 0.0123 | 0 | 0 |
| 22 | pitcher | 0.7497 | 0.7424 | 0.9901 | +0.0073 | +0.2477 | 1.71 | 0 | 14 | +0.0168 ± 0.0972 | 0 | 4 |
| 23 | board1 | 0.0829 | 0.0837 | 0.0837 | -0.0008 | +0.0000 | 0.14 | 20 | 0 | +0.0113 ± 0.0561 | 0 | 0 |
| 23 | board2 | 0.0000 | 0.0000 | 0.0000 | +0.0000 | +0.0000 | 0.09 | 7 | 0 | +0.0012 ± 0.0088 | 0 | 0 |
| 24 | board1 | 0.7764 | 0.7736 | 0.9857 | +0.0028 | +0.2121 | 0.21 | 31 | 35 | -0.4548 ± 0.3431 | 0 | 0 |
| 24 | board2 | 0.8470 | 0.8473 | 0.9861 | -0.0003 | +0.1388 | 0.16 | 5 | 48 | -0.5822 ± 0.3584 | 0 | 1 |
| 26 | rack | 0.9937 | 0.9945 | 0.9941 | -0.0008 | -0.0004 | 1.23 | 0 | 0 | -0.0030 ± 0.0006 | 0 | 0 |
| 26 | pot | 0.9367 | 0.9185 | 0.9953 | +0.0182 | +0.0768 | 0.82 | 0 | 23 | -0.0162 ± 0.0365 | 0 | 0 |
| 27 | rack | 1.0000 | 1.0000 | 1.0000 | +0.0000 | +0.0000 | 1.26 | 0 | 0 | +0.0000 ± 0.0000 | 0 | 0 |
| 27 | pot | 0.9223 | 0.8753 | 0.9942 | +0.0470 | +0.1189 | 0.79 | 0 | 29 | +0.0053 ± 0.0295 | 0 | 2 |
| 31 | sweeper | 0.9119 | 0.9248 | 0.9953 | -0.0129 | +0.0705 | 0.32 | 25 | 25 | -0.3710 ± 0.3692 | 2 | 2 |
| 31 | rack | 0.6879 | 0.7534 | 1.0000 | -0.0655 | +0.2466 | 1.39 | 0 | 25 | -0.3419 ± 0.3493 | 0 | 2 |
| 39 | pan | 0.9602 | 0.9804 | 0.9961 | -0.0202 | +0.0157 | 0.22 | 0 | 3 | -0.0224 ± 0.0125 | 0 | 0 |
| 40 | pan | 0.9570 | 0.9740 | 0.9853 | -0.0170 | +0.0113 | 0.25 | 0 | 0 | -0.0121 ± 0.0076 | 0 | 0 |
| 41 | pot | 0.9910 | 0.9881 | 0.9941 | +0.0029 | +0.0060 | 0.81 | 0 | 0 | +0.0011 ± 0.0045 | 0 | 0 |
| 42 | pot | 0.9915 | 0.9740 | 0.9966 | +0.0175 | +0.0226 | 0.80 | 0 | 2 | +0.0145 ± 0.0082 | 0 | 0 |
| 43 | pot | 0.9482 | 0.9429 | 0.9952 | +0.0053 | +0.0523 | 0.84 | 0 | 3 | -0.0098 ± 0.0264 | 0 | 0 |
| 44 | pot | 0.9967 | 0.9982 | 0.9987 | -0.0015 | +0.0005 | 0.79 | 0 | 0 | -0.0077 ± 0.0048 | 0 | 0 |
| 45 | pot | 0.9795 | 0.9789 | 0.9903 | +0.0006 | +0.0114 | 0.88 | 0 | 1 | -0.0066 ± 0.0070 | 0 | 0 |

Per object over episodes (L1 = T_lib − T\*; the PLAN §4 action needs a LOSS T\* − T_lib ≥ 0.03 on one object in ≥ 2 episodes):

| object | eps | L1 mean | eps with loss ≥ 0.03 (L1 ≤ −0.03) | eps with L1 ≥ +0.03 | perturbation flips / draws | bias mean | seed-only flips / draws (slot) |
|---|---|---|---|---|---|---|---|
| beige | 1 | +0.0475 | – | [11] | 0 / 50 | +0.1109 | 0 / 50 (slot 1) |
| blue | 5 | -0.0026 | [12] | [13] | 0 / 250 | +0.0194 | 0 / 50 (slot 0) |
| pan | 3 | -0.0147 | – | – | 0 / 150 | +0.0281 | 0 / 50 (slot 0), 0 / 50 (slot 1) |
| sweeper | 2 | -0.0066 | – | – | 52 / 100 | +0.0357 | 2 / 50 (slot 0) |
| rack | 5 | +0.0055 | [31] | [12, 13] | 0 / 250 | +0.0704 | 0 / 50 (slot 0), 0 / 50 (slot 1) |
| pitcher | 2 | +0.0104 | – | – | 0 / 100 | +0.2833 | 0 / 50 (slot 1) |
| pot | 9 | +0.0098 | – | [27] | 0 / 450 | +0.0325 | 0 / 50 (slot 0), 0 / 50 (slot 1) |
| lid | 2 | +0.0066 | – | – | 0 / 100 | +0.0491 | 0 / 50 (slot 1) |
| board1 | 2 | +0.0010 | – | – | 51 / 100 | +0.1061 | 0 / 50 (slot 0) |
| board2 | 2 | -0.0001 | – | – | 12 / 100 | +0.0694 | 0 / 50 (slot 1) |

Scene level (the kit aligns the whole scene on the first non-symmetric object at frame 0, so a flip of that object moves every other object too):

| ep | objects (anchor first) | T_lib own seed | perturbation: scene T_lib mean (min), drops ≥ 0.03 /50 | seed only: scene T_lib mean (min), drops ≥ 0.03 /50 |
|---|---|---|---|---|
| 0 | pot, lid | 0.9641 | 0.9618 (0.9171), 3 | 0.9658 (0.9585), 0 |
| 2 | pot, lid | 0.9823 | 0.9745 (0.9366), 1 | 0.9797 (0.9637), 0 |
| 11 | blue, beige | 0.8978 | 0.8835 (0.8469), 10 | 0.9006 (0.8930), 0 |
| 12 | blue, rack | 0.9662 | 0.9406 (0.8916), 18 | 0.9581 (0.9123), 3 |
| 13 | blue, rack | 0.9605 | 0.9526 (0.9257), 1 | 0.9628 (0.9378), 0 |
| 18 | sweeper, pan | 0.9642 | 0.5585 (0.2050), 27 | 0.9269 (0.2239), 7 |
| 21 | blue, pitcher | 0.8325 | 0.7995 (0.4787), 20 | 0.8267 (0.7327), 11 |
| 22 | blue, pitcher | 0.8710 | 0.8723 (0.6796), 9 | 0.8866 (0.8014), 2 |
| 23 | board1, board2 | 0.0414 | 0.0473 (0.0380), 0 | 0.0418 (0.0407), 0 |
| 24 | board1, board2 | 0.8117 | 0.2905 (0.0232), 48 | 0.8187 (0.7865), 0 |
| 26 | rack, pot | 0.9652 | 0.9449 (0.8997), 10 | 0.9636 (0.9506), 0 |
| 27 | rack, pot | 0.9611 | 0.9436 (0.8910), 6 | 0.9642 (0.9433), 0 |
| 31 | sweeper, rack | 0.7999 | 0.4502 (0.0942), 25 | 0.7930 (0.0957), 2 |
| 39 | pan | 0.9602 | 0.9559 (0.9107), 3 | 0.9613 (0.9428), 0 |
| 40 | pan | 0.9570 | 0.9623 (0.9281), 0 | 0.9590 (0.9488), 0 |
| 41 | pot | 0.9910 | 0.9892 (0.9697), 0 | 0.9918 (0.9902), 0 |
| 42 | pot | 0.9915 | 0.9896 (0.9540), 2 | 0.9912 (0.9881), 0 |
| 43 | pot | 0.9482 | 0.9345 (0.8215), 3 | 0.9514 (0.9438), 0 |
| 44 | pot | 0.9967 | 0.9905 (0.9777), 0 | 0.9962 (0.9927), 0 |
| 45 | pot | 0.9795 | 0.9744 (0.9470), 1 | 0.9790 (0.9690), 0 |

## A2 phase split of the tracking loss on \* (P_o = refine/in tracks) [M]; occlusion proxy [H]

Loss = contribution to 1 − R\* (mean over the scene's objects, then over episodes); the phases add up to 1 − R\* exactly. Plan phases: frame-0 = f0; untouched rest = rest_pre; held-moving = moving + held_still; post-release = post.

| set | 1 − R\* | f0 | untouched rest | held-moving | post-release | in occluded frames | occluded share of object-frames |
|---|---|---|---|---|---|---|---|
| all (20 eps), track | 0.1108 | 0.0002 | 0.0277 (25%) | 0.0330 (30%) | 0.0498 (45%) | 0.0182 (16%) | 14% |
| all (20 eps), body re-anchor | 0.0604 | 0.0000 | 0.0126 (21%) | 0.0145 (24%) | 0.0334 (55%) | 0.0111 (18%) | 14% |
| no_ep23 (19 eps), track | 0.0662 | 0.0002 | 0.0189 (29%) | 0.0272 (41%) | 0.0199 (30%) | 0.0113 (17%) | 14% |
| no_ep23 (19 eps), body re-anchor | 0.0155 | 0.0000 | 0.0050 (33%) | 0.0077 (50%) | 0.0027 (18%) | 0.0039 (25%) | 14% |

Per episode (scene means; init = body re-anchor gain, drift = 1 − R\* after it):

| ep | 1 − R\* | f0 | untouched rest | held-moving | post-release | init (A5) | drift (A5) | T_trk − T\* |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.0388 | 0.0001 | 0.0047 | 0.0237 | 0.0103 | +0.0343 | 0.0045 | +0.0347 |
| 2 | 0.0208 | 0.0001 | 0.0052 | 0.0087 | 0.0067 | +0.0160 | 0.0048 | +0.0163 |
| 11 | 0.1261 | 0.0007 | 0.0782 | 0.0217 | 0.0255 | +0.0501 | 0.0760 | +0.0563 |
| 12 | 0.0262 | 0.0002 | 0.0216 | 0.0045 | 0.0000 | +0.0243 | 0.0019 | +0.0253 |
| 13 | 0.0964 | 0.0002 | 0.0311 | 0.0426 | 0.0225 | +0.0702 | 0.0262 | +0.0712 |
| 18 | 0.0320 | 0.0001 | 0.0014 | 0.0132 | 0.0174 | +0.0288 | 0.0032 | +0.0291 |
| 21 | 0.1687 | 0.0005 | 0.0274 | 0.0714 | 0.0694 | +0.1628 | 0.0059 | +0.1632 |
| 22 | 0.1290 | 0.0008 | 0.0278 | 0.0565 | 0.0438 | +0.1237 | 0.0053 | +0.1240 |
| 23 | 0.9582 | 0.0015 | 0.1957 | 0.1440 | 0.6169 | +0.0436 | 0.9146 | +0.0000 |
| 24 | 0.1895 | 0.0000 | 0.0228 | 0.0505 | 0.1162 | +0.0940 | 0.0955 | +0.1754 |
| 26 | 0.0435 | 0.0002 | 0.0127 | 0.0166 | 0.0140 | +0.0308 | 0.0127 | +0.0382 |
| 27 | 0.0624 | 0.0001 | 0.0028 | 0.0434 | 0.0160 | +0.0526 | 0.0098 | +0.0595 |
| 31 | 0.1609 | 0.0003 | 0.1235 | 0.0254 | 0.0116 | +0.1568 | 0.0041 | +0.1585 |
| 39 | 0.0196 | 0.0000 | 0.0000 | 0.0174 | 0.0022 | +0.0159 | 0.0037 | +0.0157 |
| 40 | 0.0260 | 0.0000 | 0.0000 | 0.0260 | 0.0000 | +0.0111 | 0.0149 | +0.0113 |
| 41 | 0.0119 | 0.0000 | 0.0000 | 0.0119 | 0.0000 | +0.0056 | 0.0063 | +0.0060 |
| 42 | 0.0260 | 0.0000 | 0.0000 | 0.0192 | 0.0068 | +0.0224 | 0.0036 | +0.0226 |
| 43 | 0.0571 | 0.0000 | 0.0000 | 0.0408 | 0.0163 | +0.0527 | 0.0044 | +0.0523 |
| 44 | 0.0018 | 0.0000 | 0.0000 | 0.0018 | 0.0000 | +0.0000 | 0.0018 | +0.0005 |
| 45 | 0.0211 | 0.0000 | 0.0000 | 0.0211 | 0.0000 | +0.0114 | 0.0097 | +0.0114 |

Per object (loss = contribution to the object's 1 − AUC; frames in brackets):

| ep | object | R\* | true rot span ° / travel cm | f0 ADD cm | untouched rest | held-moving | post | occluded frames | body re-anchor R\* | T_trk |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | pot | 0.9926 | 14 / 17 | 0.00 | 0.0003 (110) | 0.0067 (91) | 0.0003 (171) | 0 | 0.9946 | 0.9955 |
| 0 | lid | 0.9298 | 14 / 23 | 1.70 | 0.0091 (54) | 0.0407 (203) | 0.0203 (115) | 99 | 0.9963 | 0.9963 |
| 2 | pot | 0.9929 | 12 / 13 | 0.00 | 0.0000 (114) | 0.0069 (85) | 0.0002 (143) | 27 | 0.9931 | 0.9938 |
| 2 | lid | 0.9656 | 31 / 27 | 1.54 | 0.0104 (57) | 0.0106 (212) | 0.0133 (73) | 68 | 0.9973 | 0.9973 |
| 11 | blue | 0.8618 | 5 / 0 | 0.02 | 0.1382 (136) | 0.0000 (0) | 0.0000 (0) | 44 | 0.8627 | 0.8636 |
| 11 | beige | 0.8859 | 26 / 25 | 2.05 | 0.0182 (24) | 0.0433 (42) | 0.0511 (70) | 57 | 0.9854 | 0.9968 |
| 12 | blue | 0.9910 | 180 / 22 | 0.39 | 0.0000 (33) | 0.0090 (72) | 0.0000 (75) | 6 | 0.9962 | 0.9983 |
| 12 | rack | 0.9565 | 2 / 0 | 1.12 | 0.0432 (180) | 0.0000 (0) | 0.0000 (0) | 6 | 1.0000 | 1.0000 |
| 13 | blue | 0.8697 | 179 / 28 | 0.55 | 0.0000 (21) | 0.0852 (123) | 0.0451 (45) | 43 | 0.9477 | 0.9497 |
| 13 | rack | 0.9375 | 0 / 0 | 1.43 | 0.0622 (189) | 0.0000 (0) | 0.0000 (0) | 8 | 1.0000 | 1.0000 |
| 18 | sweeper | 0.9956 | 46 / 14 | 0.00 | 0.0000 (37) | 0.0044 (259) | 0.0000 (56) | 223 | 0.9965 | 0.9965 |
| 18 | pan | 0.9403 | 66 / 20 | 1.49 | 0.0028 (16) | 0.0220 (140) | 0.0347 (196) | 1 | 0.9972 | 0.9977 |
| 21 | blue | 0.9926 | 39 / 10 | 0.46 | 0.0000 (34) | 0.0074 (102) | 0.0000 (49) | 52 | 1.0000 | 1.0000 |
| 21 | pitcher | 0.6700 | 91 / 32 | 2.94 | 0.0548 (39) | 0.1354 (69) | 0.1388 (77) | 0 | 0.9882 | 0.9889 |
| 22 | blue | 0.9997 | 29 / 9 | 0.35 | 0.0000 (43) | 0.0003 (70) | 0.0000 (75) | 43 | 0.9997 | 1.0000 |
| 22 | pitcher | 0.7424 | 92 / 32 | 3.11 | 0.0556 (40) | 0.1128 (67) | 0.0876 (81) | 0 | 0.9897 | 0.9901 |
| 23 | board1 | 0.0837 | 101 / 16 | 0.00 | 0.0037 (19) | 0.1773 (66) | 0.7354 (239) | 0 | 0.0892 | 0.0837 |
| 23 | board2 | 0.0000 | 105 / 23 | 14.40 | 0.3877 (126) | 0.1108 (36) | 0.4985 (162) | 97 | 0.0815 | 0.0000 |
| 24 | board1 | 0.7736 | 105 / 24 | 0.00 | 0.0000 (10) | 0.0357 (75) | 0.1907 (189) | 123 | 0.9516 | 0.9857 |
| 24 | board2 | 0.8473 | 101 / 27 | 0.30 | 0.0457 (113) | 0.0652 (99) | 0.0418 (62) | 26 | 0.8575 | 0.9861 |
| 26 | rack | 0.9945 | 1 / 0 | 0.00 | 0.0055 (157) | 0.0000 (0) | 0.0000 (0) | 4 | 0.9941 | 0.9941 |
| 26 | pot | 0.9185 | 180 / 20 | 1.95 | 0.0198 (50) | 0.0332 (36) | 0.0281 (71) | 0 | 0.9806 | 0.9953 |
| 27 | rack | 1.0000 | 1 / 0 | 0.00 | 0.0000 (245) | 0.0000 (0) | 0.0000 (0) | 0 | 1.0000 | 1.0000 |
| 27 | pot | 0.8753 | 180 / 39 | 1.49 | 0.0056 (22) | 0.0869 (135) | 0.0320 (88) | 0 | 0.9804 | 0.9942 |
| 31 | sweeper | 0.9248 | 34 / 16 | 0.00 | 0.0011 (47) | 0.0509 (170) | 0.0233 (72) | 137 | 0.9940 | 0.9953 |
| 31 | rack | 0.7534 | 1 / 0 | 2.81 | 0.2459 (289) | 0.0000 (0) | 0.0000 (0) | 25 | 0.9978 | 1.0000 |
| 39 | pan | 0.9804 | 109 / 39 | 0.00 | 0.0000 (48) | 0.0174 (217) | 0.0022 (53) | 0 | 0.9963 | 0.9961 |
| 40 | pan | 0.9740 | 89 / 27 | 0.00 | 0.0000 (40) | 0.0260 (158) | 0.0000 (61) | 8 | 0.9851 | 0.9853 |
| 41 | pot | 0.9881 | 72 / 20 | 0.00 | 0.0000 (31) | 0.0119 (197) | 0.0000 (70) | 0 | 0.9937 | 0.9941 |
| 42 | pot | 0.9740 | 98 / 18 | 0.00 | 0.0000 (37) | 0.0192 (145) | 0.0068 (74) | 0 | 0.9964 | 0.9966 |
| 43 | pot | 0.9429 | 180 / 24 | 0.00 | 0.0000 (27) | 0.0408 (215) | 0.0163 (83) | 0 | 0.9956 | 0.9952 |
| 44 | pot | 0.9982 | 24 / 22 | 0.00 | 0.0000 (75) | 0.0018 (93) | 0.0000 (80) | 0 | 0.9982 | 0.9987 |
| 45 | pot | 0.9789 | 94 / 29 | 0.00 | 0.0000 (50) | 0.0211 (178) | 0.0000 (61) | 132 | 0.9903 | 0.9903 |

FRAMES H3 falsifier (objects whose true rotation span > 30°, ep23 excluded): 19 objects; body re-anchor gain +1.2893 vs constant-offset bound +1.4877 (ratio 0.867); falsified if < 0.5.

## A3 reference construction stages (L4) on \*, O and P [M]

| arm | raw | a: table + snap | IK + contacts | rest settle | with S2 (raw / a / settle) | lib column: raw / settle / S2 settle |
|---|---|---|---|---|---|---|
| O | 1.0000 | 0.9844 | 0.9844 | 0.9759 | 0.9977 / 0.9818 / 0.9728 | 0.9795 / 0.9567 / 0.9537 |
| P | 0.8892 | 0.8799 | 0.8799 | 0.8829 | 0.8934 / 0.8832 / 0.8868 | 0.8921 / 0.8815 / 0.8861 |

PLAN §4 L4 action rule (a stage costs ≥ 0.02 per object on O in ≥ 3 episodes): a: 4 (ep11 beige, ep21 pitcher, ep22 pitcher, ep26 pot); settle: 6 (ep11 beige, ep22 blue, ep18 pan, ep27 pot, ep42 pot, ep43 pot); S2: 0 (none)

On P, objects where a stage costs ≥ 0.02: a: 4 (ep21 pitcher, ep22 pitcher, ep26 pot, ep31 rack); settle: 4 (ep22 blue, ep26 rack, ep43 pot, ep45 pot); S2: 0 (none)

On P, objects where a stage gains ≥ 0.02: a: 0 (none); settle: 7 (ep12 rack, ep13 blue, ep24 board1, ep24 board2, ep26 pot, ep27 pot, ep31 rack); S2: 1 (ep26 rack)

| ep | O raw | O a | O settle | O S2 settle | P raw | P a | P settle | P S2 settle | O snap cm | P snap cm | P support fallback |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1.0000 | 1.0000 | 0.9995 | 0.9945 | 0.9612 | 0.9631 | 0.9657 | 0.9672 | [0.38, 0.0] | [-0.17, 0.0] | False |
| 2 | 1.0000 | 1.0000 | 0.9971 | 0.9924 | 0.9792 | 0.9785 | 0.9753 | 0.9774 | [0.43, 0.0] | [0.18, 0.0] | False |
| 11 | 1.0000 | 0.9688 | 0.9510 | 0.9464 | 0.8739 | 0.8670 | 0.8755 | 0.8816 | [-0.75, 1.05] | [-0.04, 0.04] | False |
| 12 | 1.0000 | 1.0000 | 1.0000 | 0.9993 | 0.9738 | 0.9663 | 0.9831 | 0.9845 | [0.17, 0.62] | [0.34, 1.34] | False |
| 13 | 1.0000 | 1.0000 | 0.9970 | 0.9942 | 0.9036 | 0.8990 | 0.9178 | 0.9176 | [0.06, 0.37] | [-0.0, 1.27] | False |
| 18 | 1.0000 | 1.0000 | 0.9788 | 0.9718 | 0.9680 | 0.9652 | 0.9694 | 0.9724 | [0.73, 0.63] | [0.57, 0.65] | False |
| 21 | 1.0000 | 0.9062 | 0.9000 | 0.9004 | 0.8313 | 0.7806 | 0.7816 | 0.7903 | [-0.64, 1.8] | [-0.0, 0.93] | False |
| 22 | 1.0000 | 0.9062 | 0.8907 | 0.8905 | 0.8710 | 0.8373 | 0.8251 | 0.8246 | [-0.59, 1.89] | [0.35, 0.79] | False |
| 23 | 1.0000 | 1.0000 | 0.9892 | 0.9878 | 0.0418 | 0.0418 | 0.0411 | 0.0427 | [1.48, 0.79] | [1.15, 1.59] | False |
| 24 | 1.0000 | 1.0000 | 0.9943 | 0.9891 | 0.8105 | 0.8151 | 0.8657 | 0.8674 | [1.51, 0.81] | [1.29, 1.1] | False |
| 26 | 1.0000 | 0.9062 | 0.9252 | 0.9197 | 0.9565 | 0.9035 | 0.8975 | 0.9140 | [1.13, -1.58] | [1.39, -1.54] | False |
| 27 | 1.0000 | 1.0000 | 0.9689 | 0.9642 | 0.9376 | 0.9385 | 0.9572 | 0.9560 | [0.63, 0.4] | [1.03, 0.89] | False |
| 31 | 1.0000 | 1.0000 | 1.0000 | 0.9997 | 0.8391 | 0.8059 | 0.8471 | 0.8547 | [-0.29, 0.56] | [-0.14, 0.95] | False |
| 39 | 1.0000 | 1.0000 | 1.0000 | 0.9955 | 0.9804 | 0.9804 | 0.9808 | 0.9859 | [0.39] | [0.44] | False |
| 40 | 1.0000 | 1.0000 | 0.9993 | 0.9978 | 0.9740 | 0.9740 | 0.9805 | 0.9829 | [0.29] | [0.28] | False |
| 41 | 1.0000 | 1.0000 | 0.9973 | 0.9956 | 0.9881 | 0.9881 | 0.9870 | 0.9889 | [-0.1] | [-0.04] | False |
| 42 | 1.0000 | 1.0000 | 0.9745 | 0.9664 | 0.9740 | 0.9740 | 0.9577 | 0.9650 | [0.1] | [0.15] | False |
| 43 | 1.0000 | 1.0000 | 0.9703 | 0.9684 | 0.9429 | 0.9429 | 0.8967 | 0.9016 | [0.41] | [0.62] | False |
| 44 | 1.0000 | 1.0000 | 0.9975 | 0.9960 | 0.9982 | 0.9982 | 0.9942 | 0.9955 | [0.09] | [0.19] | False |
| 45 | 1.0000 | 1.0000 | 0.9879 | 0.9860 | 0.9789 | 0.9789 | 0.9588 | 0.9651 | [0.01] | [0.11] | False |

Stored real references (older perception and code; P only) on \* (lib in brackets):

| ep | run | loaded (a + b) | E2S + contacts | processed (contact retarget) | grasp-lock trained (ref_gl_ilc) | loaded vs E2S max cm | loaded vs processed max cm |
|---|---|---|---|---|---|---|---|
| 2 | 20261024-e3-e49e83d | 0.9794 (0.9749) | 0.9794 (0.9749) | 0.9759 (0.9798) | 0.9759 (0.9798) | 0.0 | 3.3079 |
| 12 | 20261024-ev2-2c1e4dd | 0.9660 (0.9354) | – | 0.9660 (0.9354) | 0.9660 (0.9354) | – | 0.0 |
| 26 | 20261024-w1-37cc551 | 0.9090 (0.9108) | 0.9090 (0.9108) | 0.9197 (0.9229) | 0.9197 (0.9229) | 0.0 | 1.9454 |
| 27 | 20261023-sf1227-bfb973a | 0.9372 (0.9621) | – | 0.9372 (0.9621) | 0.9372 (0.9621) | – | 0.0 |
| 31 | 20261025-std30-ee7ba8e | 0.8065 (0.7950) | 0.8065 (0.7950) | 0.8489 (0.8233) | 0.8489 (0.8233) | 0.0 | 1.5341 |
| 31 | 20261024-ev30rp-07eef1a | – | – | – | 0.8489 (0.8233) | – | – |

Joint depenetration check (mkref's 6 mm joint depenetration, skipped in the 20-episode run): rest-settled R\* without / with it: ep0 P 0.9657 / 0.9657 (max position difference 0.0 cm); ep0 O 0.9995 / 0.9995 (max position difference 0.0 cm); ep2 P 0.9753 / 0.9753 (max position difference 0.0 cm); ep2 O 0.9971 / 0.9971 (max position difference 0.0 cm)

## A4 hands vs the mocap object motion [M] (ep23 excluded)

Window ±40 frames (as pre-built):

| quantity (frames at 20 fps; median [IQR]) | first handling segment | last segment | all segments |
|---|---|---|---|
| hand arrival (fingertip ≤ 2 cm of the true surface) − true onset | -14 [-27, -9] (n 25) | | -13 [-25, -11] (n 62) |
| hand leave − true end | | +34 [+29, +40] (n 25) | +22 [+12, +37] (n 62) |
| our track's onset − true onset | +0 [+0, +1] (n 25) | | +0 [-12, +0] (n 62) |
| our track's end − true end | | +0 [+0, +1] (n 25) | +1 [+0, +2] (n 62) |

Fingertip-to-surface gap during true motion (median over objects of the per-object median, nearest measured fingertip of either hand): true surface 0.26 cm [0.22, 0.72], our track's surface 0.24 cm. Segments without a hand within 2 cm: 0 of 62; leave still near at the window edge (a lower bound): 35 of 62.

Window ±120 frames (sensitivity; neighbouring segments still bound each window):

| quantity (frames at 20 fps; median [IQR]) | first handling segment | last segment | all segments |
|---|---|---|---|
| hand arrival (fingertip ≤ 2 cm of the true surface) − true onset | -14 [-27, -9] (n 25) | | -13 [-25, -11] (n 62) |
| hand leave − true end | | +36 [+30, +48] (n 25) | +24 [+12, +38] (n 62) |
| our track's onset − true onset | +0 [+0, +1] (n 25) | | -0 [-13, +0] (n 62) |
| our track's end − true end | | +1 [+0, +2] (n 25) | +1 [+0, +3] (n 62) |

Fingertip-to-surface gap during true motion (median over objects of the per-object median, nearest measured fingertip of either hand): true surface 0.26 cm [0.22, 0.72], our track's surface 0.24 cm. Segments without a hand within 2 cm: 0 of 62; leave still near at the window edge (a lower bound): 28 of 62.

| ep | object | segments (true onset–end: arrival, leave, our onset, our end lags; ±40) | gap true / ours cm | gap > 3 cm frac | hand measured in motion |
|---|---|---|---|---|---|
| 0 | pot | 111–202: -40, 40, 1, 0 | 0.39 / 0.24 | 0.211 | 90/91 |
| 0 | lid | 55–76: -8, 28, 1, 1; 242–258: -12, 19, 0, 1 | 1.24 / 0.17 | 0.027 | 37/37 |
| 2 | pot | 115–200: -40, 34, 0, -8 | 0.23 / 0.21 | 0.0 | 80/80 |
| 2 | lid | 58–81: -5, -4, 1, 0; 249–270: -13, 37, 1, 0 | 1.2 / 0.75 | 0.209 | 43/44 |
| 11 | blue | – | None / None | None | 0/0 |
| 11 | beige | 25–67: -11, 34, -8, -1 | 0.19 / 0.16 | 0.135 | 37/37 |
| 12 | blue | 34–68: -13, 10, -7, 3; 79–106: -11, 36, -11, 39 | 0.18 / 0.24 | 0.118 | 51/55 |
| 12 | rack | – | None / None | None | 0/0 |
| 13 | blue | 22–45: -5, 11, -19, 11; 56–95: -11, 40, -11, 40; 135–145: -40, 0, -40, 25 | 0.75 / 0.62 | 0.097 | 72/72 |
| 13 | rack | – | None / None | None | 0/0 |
| 18 | sweeper | 38–123: -10, 30, 1, 1; 175–185: -29, 40, 0, 0; 235–238: -40, 14, 0, 1; 252–255: -14, 37, -14, 1; 292–297: -37, 40, -37, 1 | 0.27 / 0.29 | 0.009 | 106/106 |
| 18 | pan | 17–25: -7, 14, 0, 1; 39–45: -14, 40, -14, 0; 115–157: -40, 32, -25, 12 | 0.16 / 0.18 | 0.037 | 54/56 |
| 21 | blue | 35–55: -6, 26, -3, 1; 81–85: -26, 10, -26, 2; 95–98: -10, 10, -10, -11; 132–137: -34, 20, 1, 2 | 0.49 / 0.3 | 0.0 | 25/27 |
| 21 | pitcher | 40–69: -32, -27, 1, 0; 81–109: 17, 40, 0, 0 | 16.95 / 16.3 | 0.825 | 57/57 |
| 22 | blue | 44–56: -35, 40, 1, 25; 111–114: -40, 32, -33, -33 | 0.72 / 0.22 | 0.0 | 15/15 |
| 22 | pitcher | 41–108: -14, 38, 0, -2 | 14.95 / 15.35 | 0.776 | 67/67 |
| 23 | board1 | 20–28: None, None, None, None; 45–69: None, None, None, None; 79–86: None, None, 26, 22 | 20.71 / 16.24 | 1.0 | 39/39 |
| 23 | board2 | 127–163: 27, 15, -40, 34 | 7.0 / 1.47 | 0.75 | 36/36 |
| 24 | board1 | 11–37: -10, 13, 0, 0; 50–86: -13, 14, 2, 2 | 0.22 / 0.24 | 0.17 | 47/54 |
| 24 | board2 | 114–151: -9, 40, -38, 28; 208–213: -40, 29, -32, 0 | 0.93 / 0.9 | 0.077 | 39/39 |
| 26 | rack | – | None / None | None | 0/0 |
| 26 | pot | 51–87: -14, 30, 1, 0 | 0.23 / 0.23 | 0.0 | 31/36 |
| 27 | rack | – | None / None | None | 0/0 |
| 27 | pot | 23–36: 12, 12, 0, 2; 48–158: -11, 40, -12, 1 | 0.21 / 0.24 | 0.194 | 108/108 |
| 31 | sweeper | 48–74: -27, 22, -27, 1; 96–218: -22, 40, -22, 40 | 0.22 / 0.28 | 0.046 | 109/109 |
| 31 | rack | – | None / None | None | 0/0 |
| 39 | pan | 49–266: -15, 26, 1, 1 | 0.69 / 0.74 | 0.308 | 169/172 |
| 40 | pan | 41–54: -23, 21, 0, 2; 75–199: -21, 29, -21, 1 | 0.34 / 0.72 | 0.0 | 107/109 |
| 41 | pot | 32–72: -15, 15, 0, -10; 87–142: -15, 11, 0, 1; 153–165: -11, 13, -11, 0; 178–184: -13, 15, 0, 15; 199–208: -15, 14, -15, 0; 226–229: -7, 31, 0, 0 | 0.22 / 0.19 | 0.024 | 84/97 |
| 42 | pot | 38–45: -19, 19, 1, 19; 64–84: -19, 11, -1, 0; 95–183: -11, 40, 1, 1 | 0.24 / 0.23 | 0.0 | 111/112 |
| 43 | pot | 28–33: -13, 19, 1, 0; 52–140: -19, 9, 0, 10; 150–218: -4, 12, -1, 3; 230–243: -12, 40, -12, -1 | 0.25 / 0.23 | 0.0 | 144/154 |
| 44 | pot | 76–93: -40, 12, 1, 1; 105–110: -12, 12, -12, 0; 122–130: -12, 13, 0, 2; 143–169: -13, 38, -13, 0 | 0.21 / 0.24 | 0.0 | 52/52 |
| 45 | pot | 51–98: -34, 11, 0, 2; 109–132: -11, 10, -11, 2; 142–192: -10, 9, -10, 10; 202–229: -5, 35, -10, 0 | 0.26 / 0.35 | 0.015 | 135/135 |

## A6 scorer sanity and frame invariance [M] (from frames_check.json)

All pass flags: True (a1 True, a2 True, a4 True, a3_inprocess True, b1 True, b2 True, b0 True, b4 True, a4_trk True). Mocap through the kit path: 1.0000 (scan) / 1.0000 (lib at X_kit); T\* two ways max |Δ| 0.0000; cup spin max |Δ| 0.0018 (rule ≤ 0.002); budgeted-scan registration noise max 0.0248.

## A7 2 s hands-free settle of the mocap rest configurations [M] (gate: every object ≤ 1 cm and ≤ 5° at 2 s)

| ep | rest frames (dropped: held in the air) | lib | lib + carve | scan |
|---|---|---|---|---|
| 0 | [0, 93, 221, 315] (–) | FAIL 2/4 (hand-free 0/2); worst 1.23 cm / 5.9° (lid f0, hand 36.44 cm) | – | FAIL 2/4 (hand-free 0/2); worst 1.82 cm / 1.7° (lid f315, hand 26.14 cm) |
| 2 | [0, 97, 224, 309] (–) | FAIL 2/4 (hand-free 0/1); worst 1.39 cm / 5.2° (lid f309, hand None cm) | FAIL 2/4 (hand-free 0/1); worst 1.01 cm / 7.5° (lid f309, hand None cm) | FAIL 2/4 (hand-free 0/1); worst 1.87 cm / 2.9° (lid f0, hand None cm) |
| 11 | [0, 101] (–) | FAIL 0/2 (hand-free 0/2); worst 10.17 cm / 88.4° (beige f0, hand 33.62 cm) | FAIL 0/2 (hand-free 0/2); worst 14.77 cm / 90.8° (beige f0, hand 33.62 cm) | FAIL 1/2 (hand-free 1/2); worst 0.73 cm / 5.3° (beige f101, hand 23.93 cm) |
| 12 | [0, 153] ([73]) | FAIL 1/2 (hand-free 1/2); worst 1.09 cm / 17.0° (blue f153, hand 19.17 cm) | FAIL 0/2 (hand-free 0/2); worst 2.18 cm / 4.3° (blue f153, hand 19.17 cm) | FAIL 0/2 (hand-free 0/2); worst 3.00 cm / 21.2° (blue f153, hand 19.17 cm) |
| 13 | [0, 114, 167] ([50]) | FAIL 1/3 (hand-free 1/2); worst 6.39 cm / 47.4° (blue f114, hand 1.54 cm) | FAIL 1/3 (hand-free 1/2); worst 21.97 cm / 177.4° (blue f114, hand 1.54 cm) | FAIL 1/3 (hand-free 1/2); worst 3.67 cm / 45.8° (blue f114, hand 1.54 cm) |
| 18 | [0, 31, 209, 244, 262, 281, 324] ([165]) | FAIL 0/7 (hand-free 0/1); worst 14.57 cm / 112.6° (sweeper f0, hand 16.72 cm) | – | FAIL 3/7 (hand-free 0/1); worst 3.39 cm / 3.3° (sweeper f262, hand 0.24 cm) |
| 21 | [0, 17, 161] ([74, 120]) | FAIL 0/3 (hand-free 0/2); worst 83.91 cm / 95.0° (pitcher f161, hand 11.92 cm) | – | PASS 3/3 (hand-free 2/2); worst 0.86 cm / 1.9° (pitcher f17, hand 0.75 cm) |
| 22 | [0, 151] (–) | FAIL 0/2 (hand-free 0/2); worst 18.17 cm / 97.6° (pitcher f0, hand 12.09 cm) | – | PASS 2/2 (hand-free 2/2); worst 0.74 cm / 0.4° (pitcher f0, hand 12.09 cm) |
| 23 | [0, 39, 73, 106, 288] ([178, 205, 228]) | FAIL 1/5 (hand-free 1/4); worst 10.45 cm / 83.9° (board1 f73, hand 20.96 cm) | – | FAIL 1/5 (hand-free 1/4); worst 21.71 cm / 85.4° (board1 f106, hand 15.96 cm) |
| 24 | [0, 99, 243] ([43, 163, 192]) | FAIL 1/3 (hand-free 0/1); worst 10.68 cm / 91.1° (board1 f99, hand 1.62 cm) | FAIL 1/3 (hand-free 0/1); worst 10.56 cm / 84.9° (board1 f99, hand 1.62 cm) | FAIL 0/3 (hand-free 0/1); worst 26.22 cm / 46.9° (board1 f99, hand 1.62 cm) |
| 26 | [0, 122] (–) | FAIL 1/2 (hand-free 1/2); worst 16.01 cm / 73.4° (pot f0, hand 11.71 cm) | – | FAIL 0/2 (hand-free 0/2); worst 2.72 cm / 19.9° (rack f122, hand 11.12 cm) |
| 27 | [0, 41] ([204]) | PASS 2/2 (hand-free 1/1); worst 0.62 cm / 2.0° (pot f0, hand 8.98 cm) | PASS 2/2 (hand-free 1/1); worst 0.87 cm / 3.5° (pot f41, hand 0.35 cm) | PASS 2/2 (hand-free 1/1); worst 0.38 cm / 1.3° (rack f0, hand 12.12 cm) |
| 31 | [0, 39, 84, 253] (–) | FAIL 0/4 (hand-free 0/1); worst 6.62 cm / 60.7° (sweeper f0, hand 23.71 cm) | FAIL 0/4 (hand-free 0/1); worst 5.74 cm / 56.9° (sweeper f253, hand 0.25 cm) | FAIL 0/4 (hand-free 0/1); worst 3.96 cm / 117.9° (sweeper f84, hand 0.1 cm) |
| 39 | [0, 292] (–) | PASS 2/2 (hand-free 2/2); worst 0.19 cm / 2.1° (pan f0, hand 29.81 cm) | – | PASS 2/2 (hand-free 2/2); worst 0.38 cm / 0.9° (pan f292, hand 3.32 cm) |
| 40 | [0, 229] ([59]) | PASS 2/2 (hand-free 2/2); worst 0.14 cm / 2.8° (pan f229, hand 3.17 cm) | – | PASS 2/2 (hand-free 2/2); worst 0.18 cm / 0.9° (pan f229, hand 3.17 cm) |
| 41 | [0, 216, 263] ([79, 147, 171, 191]) | FAIL 2/3 (hand-free 2/2); worst 3.99 cm / 21.1° (pot f216, hand None cm) | – | FAIL 2/3 (hand-free 2/2); worst 3.69 cm / 19.7° (pot f216, hand None cm) |
| 42 | [0, 54, 219] ([89]) | FAIL 2/3 (hand-free 1/1); worst 2.15 cm / 11.5° (pot f54, hand 0.79 cm) | – | FAIL 2/3 (hand-free 1/1); worst 1.76 cm / 10.4° (pot f54, hand 0.79 cm) |
| 43 | [0, 42, 284] ([144, 223]) | FAIL 2/3 (hand-free 1/1); worst 4.88 cm / 21.4° (pot f42, hand 0.31 cm) | – | FAIL 2/3 (hand-free 1/1); worst 4.32 cm / 20.3° (pot f42, hand 0.31 cm) |
| 44 | [0, 208] ([98, 115, 136]) | PASS 2/2 (hand-free 2/2); worst 0.37 cm / 3.9° (pot f208, hand 5.17 cm) | – | PASS 2/2 (hand-free 2/2); worst 0.12 cm / 1.0° (pot f208, hand 5.17 cm) |
| 45 | [0, 259] ([103, 136, 196]) | PASS 2/2 (hand-free 1/1); worst 0.24 cm / 2.8° (pot f259, hand 1.21 cm) | – | PASS 2/2 (hand-free 1/1); worst 0.14 cm / 1.1° (pot f259, hand 1.21 cm) |

All configurations: lib: pass 5 / 20 eps; lib_carve: pass 1 / 7 eps; scan: pass 7 / 20 eps

"Hand-free" = every measured fingertip > 3 cm from every object's true surface at that frame. A frame with no measured hand counts as unknown (not hand-free), except frame 0. Gate on hand-free configurations only:

- lib: pass [27, 39, 40, 41, 42, 43, 44, 45]; fail [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 31]; no hand-free configuration []
- lib_carve: pass [27]; fail [2, 11, 12, 13, 24, 31]; no hand-free configuration []
- scan: pass [21, 22, 27, 39, 40, 41, 42, 43, 44, 45]; fail [0, 2, 11, 12, 13, 18, 23, 24, 26, 31]; no hand-free configuration []

Per Phase-2 twin (PLAN §3 gate for c4–c6 = scan geometry; lib shown for c1–c3, which the plan does not gate):

| twin | eval | scan: hand-free gate | scan: worst hand-free drift | lib: hand-free gate | lib: worst hand-free drift | lib + carve: hand-free gate |
|---|---|---|---|---|---|---|
| ep2 | 1 | FAIL (1) | 1.87 cm / 2.9° (lid f0) | FAIL (1) | 1.39 cm / 3.7° (lid f0) | FAIL (1) |
| ep11 | 10 | FAIL (2) | 0.73 cm / 5.3° (beige f101) | FAIL (2) | 10.17 cm / 88.4° (beige f0) | FAIL (2) |
| ep12 | 14 | FAIL (2) | 3.00 cm / 21.2° (blue f153) | FAIL (2) | 1.09 cm / 17.0° (blue f153) | FAIL (2) |
| ep13 | 14 | FAIL (2) | 1.11 cm / 6.7° (blue f167) | FAIL (2) | 5.96 cm / 54.7° (blue f167) | FAIL (2) |
| ep18 | 19 | FAIL (1) | 0.52 cm / 6.4° (sweeper f0) | FAIL (1) | 14.57 cm / 112.6° (sweeper f0) | – |
| ep21 | 20 | PASS (2) | 0.38 cm / 0.6° (blue f0) | FAIL (2) | 83.91 cm / 95.0° (pitcher f161) | – |
| ep24 | 25 | FAIL (1) | 1.56 cm / 16.8° (board1 f243) | FAIL (1) | 2.31 cm / 10.1° (board2 f243) | FAIL (1) |
| ep27 | 8, 28 | PASS (1) | 0.38 cm / 1.3° (rack f0) | PASS (1) | 0.62 cm / 2.0° (pot f0) | PASS (1) |
| ep31 | 30 | FAIL (1) | 1.54 cm / 14.3° (sweeper f0) | FAIL (1) | 6.62 cm / 60.7° (sweeper f0) | FAIL (1) |
| ep39 | 8, 38 | PASS (2) | 0.38 cm / 0.9° (pan f292) | PASS (2) | 0.19 cm / 2.1° (pan f0) | – |
