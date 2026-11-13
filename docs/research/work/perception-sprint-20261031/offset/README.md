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

## 3. Results [M] (scored 31 Oct 09:41–09:49 UTC, after all 160 refine outputs existed; oracle arm 09:52–10:02)

### 3.0 Owner summary
1. **No variant passes; S11 is not adopted [M].** Every variant fails on both arms: the means are −0.006 to +0.0005 lib
   (bar +0.010), and every variant has episodes far below −0.010 (ep12 −0.064 to −0.067, ep39 −0.105 to −0.128, ep40
   −0.017 to −0.039, ep13 −0.055 for V1).
2. **[H-OFF] is falsified for all three variants [M].** The corrections are small (median 0.27–0.31 cm and 1.5–1.8°;
   largest 1.2 cm / 5.4°) and point nowhere in particular relative to the oracle constant offset: over the objects with an
   oracle offset ≥ 0.5 cm, the median recovered share is −0.01 to −0.045, and only 40–46 % of them move closer
   (`geo_share.json`). The oracle offsets on the same objects average 1.3–1.5 cm.
3. **Share of the constant-offset ceiling recovered: about none [M].** Main arms: −12 % to +1 % of R_trk − R_lib
   (0.050) in lib; +1 % to −17 % of R_trk − R\* (0.054–0.055) in \*. Against Phase 1's 0.025 (\*, without ep0 and
   ep23): V1 +0.0018 (+7 %), V2 −0.010 (−40 %), V3 −0.004 (−16 %).
4. **With the true shapes (oracle arm P_s), the depth re-fit still does not pay [M].** V1 −0.0021 \* (−9 % of the P_s
   ceiling 0.0222), V2 −0.0099, V3 −0.0059; geometrically V1 moves 13 of 17 objects slightly toward the oracle offset
   (median recovered +0.075), V2/V3 do not (−0.003). By the §2 rule: V2/V3 "the depth re-fit itself is uninformative";
   V1 inconclusive (a small geometric pull with no score gain). So the failure is not only our templates.
5. **What the constant offset is not [M/H].** It is not a disagreement between our mesh and our own depth that a robust
   re-fit can see: our tracks already sit within ~0.3 cm / ~1.5° of the depth optimum, while the oracle offsets are
   ~1.4 cm. A side reading: the adopted S2 already recovers 25 % of the P_s ceiling (+0.0056 of 0.0222; ep12 +0.062,
   ep45 +0.031, ep26 +0.014), because in P_s the frame-0 registration disagrees with the next tracked frames by up to
   7.8° (ep12 rack; later steps ≤ 0.3°, `f01_Ps.txt`). On our P_o tracks such 0→1 steps are smaller (≤ 4°, mostly
   ≤ 2°), and frame-0 smoothing was already tested and dropped (ep0 F3: +0.0003).
6. **Eval: nothing changes.** No variant passes, S11 stays opt-in (not in `DEFAULT_STEPS`), and no eval file was read.
   The one large public gain (ep31, V2/V3 +0.065 to +0.099 lib) is the known frame-0 anchor tilt (M2); the GT-free eval
   screen (`../../leak-decomp-20261030/tracker-fix/SCREEN.md`) found no eval with that mode (eval 30's anchor coverage
   0.855 vs 0.52 on ep31).
7. **Cost:** $0. CPU on this VM (shared with the heldpose experiment): 20 × 48 frames of our depth cache by HTTP range
   reads (≈ 6.1 GB read, 733 MB kept as half-resolution float16, ≈ 6 min, no 429); 240 refine runs ≈ 18 + 8 min;
   oracle scoring ≈ 8 + 3 min; diagnostics ≈ 5 min.

### 3.1 Verdicts (pre-registered rule; lib decisive) [M]

| variant | arm | mean ΔR lib | better / worse / 0 | worst (ep) | rule | mean ΔR \* | ΔR \* w/o ep0, ep23 | share of trk ceiling lib / \* | vs 0.025 |
|---|---|---|---|---|---|---|---|---|---|
| V1 mf/whole (primary) | Po | −0.0058 | 7 / 11 / 2 | −0.0640 (ep12) | **fail** | +0.0004 | +0.0018 | −12 % of 0.0505 / +1 % of 0.0550 | +7 % |
| V1 mf/whole (primary) | refineP | −0.0049 | 9 / 10 / 1 | −0.0637 (ep12) | **fail** | +0.0003 | +0.0018 | −10 % of 0.0507 / +1 % of 0.0536 | +7 % |
| V2 f0/whole | Po | −0.0014 | 11 / 7 / 2 | −0.1046 (ep39) | **fail** | −0.0085 | −0.0096 | −3 % / −15 % | −39 % |
| V2 f0/whole | refineP | −0.0030 | 11 / 8 / 1 | −0.1046 (ep39) | **fail** | −0.0092 | −0.0100 | −6 % / −17 % | −41 % |
| V3 f0/prefix | Po | +0.0005 | 12 / 7 / 1 | −0.1281 (ep39) | **fail** | −0.0031 | −0.0036 | +1 % / −6 % | −15 % |
| V3 f0/prefix | refineP | −0.0011 | 11 / 8 / 1 | −0.1281 (ep39) | **fail** | −0.0039 | −0.0040 | −2 % / −7 % | −16 % |

Baseline check: the S2 baseline re-run with the new code is byte-identical to T1's S2 outputs on 20/20 episodes in both
arms.

### 3.2 Per episode, ΔR = R(S11,S2) − R(S2), lib / \* [M] (`scores/off_tables.md`)

| ep | objects | Po S2 lib / \* | refineP S2 lib / \* | Po V1 | Po V2 | Po V3 | refineP V1 | refineP V2 | refineP V3 |
|---|---|---|---|---|---|---|---|---|---|
| 0 | white_pot + white_pot_lid | 0.9669 / 0.9629 | 0.9672 / 0.9657 | −0.0012 / −0.0250 | +0.0027 / +0.0036 | +0.0019 / +0.0028 | +0.0008 / −0.0274 | +0.0001 / −0.0042 | −0.0003 / −0.0045 |
| 2 | white_pot + white_pot_lid | 0.9911 / 0.9824 | 0.9871 / 0.9823 | +0.0048 / −0.0009 | −0.0172 / −0.0034 | −0.0184 / −0.0043 | +0.0075 / −0.0015 | −0.0080 / +0.0010 | −0.0095 / +0.0010 |
| 11 | blue_cup + beige_cup | 0.9012 / 0.8814 | 0.9012 / 0.8814 | −0.0084 / −0.0100 | +0.0016 / +0.0068 | +0.0032 / +0.0123 | −0.0084 / −0.0100 | +0.0016 / +0.0068 | +0.0032 / +0.0123 |
| 12 | blue_cup + plastic_dish_rack | 0.9763 / 0.9739 | 0.9760 / 0.9739 | **−0.0640** / −0.0045 | **−0.0671** / −0.0100 | **−0.0645** / −0.0053 | **−0.0637** / −0.0045 | **−0.0668** / −0.0107 | **−0.0641** / −0.0057 |
| 13 | blue_cup + plastic_dish_rack | 0.9623 / 0.9051 | 0.9648 / 0.9038 | **−0.0569** / +0.0238 | −0.0084 / −0.0299 | −0.0037 / −0.0189 | **−0.0554** / +0.0242 | −0.0095 / −0.0293 | −0.0046 / −0.0193 |
| 18 | mini_sweeper + mini_dust_pan | 0.9162 / 0.9217 | 0.9680 / 0.9718 | −0.0007 / −0.0048 | +0.0038 / −0.0032 | +0.0126 / −0.0013 | −0.0027 / −0.0042 | +0.0015 / −0.0045 | +0.0110 / −0.0027 |
| 21 | blue_cup + water_pitcher | 0.8389 / 0.8438 | 0.8389 / 0.8438 | +0.0040 / +0.0097 | +0.0383 / +0.0060 | +0.0630 / +0.0485 | +0.0040 / +0.0097 | +0.0383 / +0.0060 | +0.0630 / +0.0485 |
| 22 | blue_cup + water_pitcher | 0.8704 / 0.8618 | 0.8704 / 0.8598 | +0.0271 / +0.0330 | +0.0220 / +0.0071 | +0.0301 / +0.0145 | +0.0268 / +0.0350 | +0.0213 / +0.0078 | +0.0271 / +0.0159 |
| 23 | wooden_piece_1 + wooden_piece_2 | 0.0425 / 0.0429 | 0.0425 / 0.0429 | +0.0000 / +0.0000 | +0.0000 / +0.0000 | +0.0000 / +0.0000 | +0.0002 / +0.0000 | +0.0000 / +0.0000 | +0.0000 / +0.0000 |
| 24 | wooden_piece_1 + wooden_piece_2 | 0.8091 / 0.8069 | 0.8091 / 0.8069 | −0.0069 / −0.0072 | +0.0089 / +0.0098 | +0.0035 / +0.0054 | −0.0069 / −0.0072 | +0.0089 / +0.0098 | +0.0035 / +0.0054 |
| 26 | plastic_dish_rack + white_pot | 0.9717 / 0.9652 | 0.9678 / 0.9610 | +0.0160 / +0.0166 | +0.0085 / −0.0004 | +0.0022 / +0.0000 | +0.0186 / +0.0188 | +0.0081 / +0.0002 | +0.0010 / −0.0015 |
| 27 | plastic_dish_rack + white_pot | 0.9634 / 0.9362 | 0.9627 / 0.9339 | +0.0135 / +0.0157 | +0.0071 / +0.0049 | +0.0212 / +0.0167 | +0.0148 / +0.0176 | +0.0073 / +0.0077 | +0.0208 / +0.0187 |
| 31 | mini_sweeper + plastic_dish_rack | 0.8239 / 0.8673 | 0.8550 / 0.8723 | −0.0131 / +0.0054 | +0.0960 / +0.0518 | +0.0991 / +0.0434 | −0.0037 / +0.0026 | +0.0647 / +0.0471 | +0.0674 / +0.0398 |
| 39 | mini_dust_pan | 0.9759 / 0.9914 | 0.9759 / 0.9914 | +0.0000 / +0.0000 | **−0.1046** / −0.0866 | **−0.1281** / −0.1099 | +0.0000 / +0.0000 | **−0.1046** / −0.0866 | **−0.1281** / −0.1099 |
| 40 | mini_dust_pan | 0.9584 / 0.9784 | 0.9584 / 0.9784 | **−0.0394** / −0.0284 | **−0.0166** / −0.0149 | **−0.0380** / −0.0282 | **−0.0394** / −0.0284 | **−0.0166** / −0.0149 | **−0.0380** / −0.0282 |
| 41 | white_pot | 0.9927 / 0.9893 | 0.9927 / 0.9893 | +0.0023 / +0.0015 | +0.0010 / +0.0023 | +0.0029 / +0.0002 | +0.0023 / +0.0015 | +0.0010 / +0.0023 | +0.0029 / +0.0002 |
| 42 | white_pot | 0.9990 / 0.9708 | 0.9993 / 0.9784 | −0.0017 / −0.0073 | +0.0000 / −0.0131 | +0.0005 / −0.0131 | −0.0015 / −0.0086 | −0.0005 / −0.0219 | +0.0002 / −0.0224 |
| 43 | white_pot | 0.9486 / 0.9465 | 0.9479 / 0.9469 | +0.0132 / +0.0038 | +0.0094 / −0.0985 | +0.0363 / −0.0224 | +0.0130 / +0.0019 | +0.0072 / −0.0997 | +0.0362 / −0.0226 |
| 44 | white_pot | 0.9970 / 0.9995 | 0.9970 / 0.9995 | −0.0023 / −0.0003 | −0.0113 / −0.0003 | −0.0103 / −0.0003 | −0.0023 / −0.0003 | −0.0113 / −0.0003 | −0.0103 / −0.0003 |
| 45 | white_pot | 0.9823 / 0.9843 | 0.9823 / 0.9843 | −0.0028 / −0.0136 | −0.0017 / −0.0015 | −0.0030 / −0.0020 | −0.0028 / −0.0136 | −0.0017 / −0.0015 | −0.0030 / −0.0020 |

### 3.3 What S11 did, GT-free (`scores/s11_gtfree_summary.json`) [M]
| arm, variant | objects corrected | median change | largest | not corrected (reason) |
|---|---|---|---|---|
| Po V1 / refineP V1 | 28 / 33 each | 0.27 cm, 1.5° | 0.58 cm, 4.0° | 5: rotation spread > 3° (ep18, ep31 sweepers; ep26, ep27 pots; ep39 dust pan) |
| Po V2, V3 | 29 / 33 | 0.31 cm, 1.8° | 1.20 cm, 5.4° | 4: < 150 points (ep0 lid, ep23 board 1, ep24 board 2, ep26 rack) |
| refineP V2, V3 | 29 / 33 | 0.29 cm, 1.8° | 1.20 cm, 5.2° | 4: as Po |

- V1 consensus is tight: the racks take 48/48 frames with a rotation spread of ~1°, i.e. our rack mesh and our depth
  disagree consistently by 0.3–0.5 cm / 0.8–2.9° in every rack episode.
- The two arms give nearly the same corrections (V1: the magnitudes differ on 16 of 33 objects, by ≤ 0.06 cm and
  ≤ 0.35°), because the arms are near-replicate tracks on the same depth. They are not independent tests.
- Removing the occluders fixed what made F1 reject the pots under the lid: ep0/ep2 pot F1 7.8–8.3° / 2.5 cm (rejected),
  V2 0.85–1.4° / 0.1–0.2 cm (accepted). It did not make the corrections helpful (ep2 −0.008 to −0.018 lib).

### 3.4 Geometric share against the oracle constant offset (`scores/geo_share.json`; cups on their axis points) [M]

| variant | arm | objects (d0 ≥ 0.5 cm, corrected) | mean d0 → mean d1 (cm) | median recovered | closer | [H-OFF] |
|---|---|---|---|---|---|---|
| V1 | Po | 23 | 1.459 → 1.469 | −0.013 | 43 % | falsified |
| V1 | refineP | 24 | 1.480 → 1.501 | −0.021 | 42 % | falsified |
| V2 | Po | 24 | 1.303 → 1.372 | −0.010 | 46 % | falsified |
| V2 | refineP | 25 | 1.320 → 1.398 | −0.045 | 40 % | falsified |
| V3 | Po | 24 | 1.303 → 1.372 | −0.010 | 46 % | falsified |
| V3 | refineP | 25 | 1.320 → 1.398 | −0.045 | 40 % | falsified |

### 3.5 Oracle arm P_s, scan templates (`scores/oracle_ps_scores.json`; rule §2) [M]

| variant | mean ΔR\* (20) | w/o ep0, ep23 | better / worse | worst | share of P_s ceiling 0.0222 (0.0246) | geometric: n, median recovered, closer | §2 reading |
|---|---|---|---|---|---|---|---|
| V1 | −0.0021 | −0.0020 | 6 / 10 | −0.0337 (ep12) | −9 % (−8 %) | 17, +0.075, 77 % | inconclusive (small pull, no gain) |
| V2 | −0.0099 | −0.0110 | 3 / 15 | −0.0628 (ep18) | −44 % (−45 %) | 16, −0.003, 50 % | depth re-fit uninformative |
| V3 | −0.0059 | −0.0065 | 4 / 12 | −0.0501 (ep18) | −27 % (−27 %) | 16, −0.003, 50 % | depth re-fit uninformative |

- The S2 baseline on P_s vs the raw P_s track: +0.0056 \* mean (25 % of the 0.0222 ceiling; ep12 +0.0615, ep45 +0.0308,
  ep26 +0.0136, ep31 −0.0156, ep24 −0.0063). After S2 the P_s ceiling left is ≈ 0.0166 (trk of the raw track − S2).
- Per episode (ΔR\* V1 / V2 / V3): ep12 −0.034 / −0.019 / −0.000; ep18 −0.003 / −0.063 / −0.050; ep31 +0.022 / +0.028 /
  +0.029; ep45 −0.004 / −0.025 / −0.028; ep43 +0.002 / −0.032 / −0.018; ep22 −0.003 / −0.028 / −0.006; the rest within
  ±0.024 (`scores/oracle_ps_score.log`).

### 3.6 Mechanism readings [M unless marked]
- **Small anchor rotations are what the scorer punishes.** ep12's rack is the scene's rotation anchor (the cup in slot 0
  has an axis). All three variants turn it by 1.9–2.3° (V1: 48/48 frames, spread 1.1°), and ep12 loses 0.064–0.067 lib in
  both arms. F1's "every object" variant lost −0.085 there by the same route.
- **The table exclusion broke the thin dust pan (a design flaw found after scoring).** On ep39 the 0.8 cm table band
  removes 56 % of the dust pan's det-mask points (3,659 → 1,602), leaving mostly the handle; V2 turns it 5.2° (F1, without
  the band: 1.6°) and ep39 loses 0.105–0.128. V1 skips ep39 (rotation spread 3.2°). ep40 loses with all variants.
- **Where it helps, it helps through the frame-0 anchor, not through a truer pose.** ep31 (+0.065 to +0.099 lib, V2/V3)
  is the M2 frame-0 sweeper tilt (occluders removed: 663 of the 714 mask pixels kept, change 4.6°; F1 7.1°). ep21's
  pitcher gains +0.038 / +0.063 lib (V2 / V3) while moving away from the oracle offset (recovered −0.38): the pitcher is
  the rotation anchor there, so the gain is a different frame-0 scene rotation, not a better pose.
- **Does our depth prefer the oracle-corrected pose?** (`scripts/diag_depth_truth.py`, P_o; the scan mesh at our track vs
  at our track with the oracle body offset X_trk; median absolute depth residual over frame 0 and ≤ 12 rest frames):
  overall a tie (oracle better on 16 of 33 objects, ours on 15; medians 0.69 vs 0.66 cm). By class: racks 5/5 and the
  pitcher 2/2 prefer the oracle offset (rack 1.02 → 0.67 cm); cups prefer our track 5 of 6 (0.53 vs 1.22 cm); pots 6/5;
  thin objects 2/3. Caveat: X_trk is chosen to maximise the AUC under the kit's frame-0 alignment, so it is the
  scorer-optimal offset, not a geometric truth.
- [H] For racks and the pitcher the oracle offset is partly a shape (template) effect that depth can see with the true
  shape; for cups and pots the AUC-optimal offset is mostly a scene-alignment effect (slot-0 translation, anchor
  rotation at frame 0) that no per-object depth fit can see. Experiment that would falsify it: refit X_trk with the
  geometric LS fit only (`trk_ls`, no AUC step) and repeat the depth comparison; if cups then also prefer the oracle
  offset, the split is not alignment-driven.

### 3.7 What this leaves [E/H]
- Depth re-fitting of our own meshes is not a route to the constant-offset share: three forms, two arms, plus the true
  shapes, all ≈ 0 or negative. Together with F1 (`PREREG_f0icp.md`) and the depth audit (30 Oct, AUROC 0.600), this is
  the third negative result for depth-only pose correction on these data.
- The constant-offset ceiling on our tracks (0.050 lib) is not one mechanism. Its large parts are already attributed
  elsewhere: ep24 camera (T5, fixed on public, no eval target), ep31 frame-0 anchor tilt (M2, no eval target), ep21/22
  pitcher template (L2, eval 20), ep0/ep23 outliers. The template lever (L2: +0.012–0.017 LB [E], only if the improved
  mesh is also submitted, Phase 1 Reading 3) remains the larger perception lever.
- Not tried, and the only depth-free variant left [H]: a GT-free consistency fix between frame 0 and the first tracked
  frames for the scene anchor (P_s shows 0→1 steps up to 7.8°). It overlaps with S2 (which already takes 25 % of the P_s
  ceiling) and with the dropped F3; on P_o the steps are ≤ 4°. Expected value small [E].

## 4. Eval exposure
- **No eval episode changes.** No variant passed, so S11 was not run on eval and no eval file was opened. S11 stays
  opt-in and outside `DEFAULT_STEPS`; no build calls it.
- If a gated form were ever proposed for ep31-type anchors (M2), the eval screen already shows no eval with that mode.

## 5. Commands, inputs, code
Paths: `S` = the session scratchpad, `PY=$S/map/scoring/venv/bin/python`, `D` = this folder. Code: run from the working
tree on b74ef87; `pipeline/offsetfix.py` sha256 1610649f…, `pipeline/refine.py` 3b353b5f… (with the parallel heldpose
S10 hook; the same refine bytes in all 240 runs, checked from each `pose_opt.json`; `runs/code_sha256.txt`). Both files
are byte-identical in the WIP commit 2cca69d.
1. Depth grid (GT-free, our stereo depth): `$PY -I $D/scripts/fetch_depth.py $S/offset/depth <eps>` (two processes,
   10 episodes each). The full-resolution frame 0 read from the store is sha256-equal to `refine/in/ep<N>/depth0.npy`
   on 20/20 episodes; the kept half-resolution float16 copy is within 0.5 mm of it.
2. Inference: `bash $D/scripts/off_run.sh` (160 jobs in `runs/jobs.txt`, 4 at a time, `OMP_NUM_THREADS=1`; outputs
   `$S/offset/runs/<arm>/<variant>/ep<N>/`). No traceback, no FAIL.
3. GT-free summary: `$PY -I $D/scripts/off_gtfree_summary.py $S/offset/runs $D/scores/s11_gtfree_summary.json`.
4. Oracle scoring: `SPLIT=public OMP_NUM_THREADS=1 $PY -I $D/scripts/off_score.py $S/offset/off_scores.json` (copied to
   `scores/`), then `$PY -I $D/scripts/off_tables.py scores/off_scores.json > scores/off_tables.md`,
   `$PY -I $D/scripts/geo_share.py $S/offset/runs scores/geo_share.json`.
5. Diagnostics (oracle): `$PY -I $D/scripts/diag_depth_truth.py scores/diag_depth_truth.json`; GT-free
   `$PY -I $D/scripts/f01.py {Po,Ps} > scores/f01_{Po,Ps}.txt`; pre-registration-time `scripts/diag_dir.py Po`.
6. Oracle arm: `bash $D/scripts/oracle_ps_run.sh` (80 jobs, `runs/oracle_jobs.txt`; outputs `$S/offset/oracle/`), then
   `SPLIT=public $PY -I $D/scripts/oracle_ps_score.py scores/oracle_ps_scores.json`.
7. QA images (GT-free; `scripts/qa_pixels.py`): `qa/ep12_f0_blue.png` (used pixels green, other objects blue, hands
   red) and `qa/ep31_f0_sweeper_det_crop.png` (det mask minus the rendered rack).

Integrity: every refine input passed `refine.assert_inference_input` (depth grid, det_f0, hands, poses, meshes; the
oracle arm's scan links are an oracle input by design and are kept under `$S/offset/oracle/`). Mocap and the trk fits were
read only by `off_score.py`, `geo_share.py`, `diag_depth_truth.py`, `oracle_ps_score.py` and the pre-registration-time
`diag_dir.py`. Eval data were not read.

## 6. Caveats
- No fresh holdout: the 20 public episodes were also the F1 test set, and the two arms are near-replicates.
- The oracle "constant offset" (X_trk) is AUC-optimal under the kit's frame-0 alignment, not a geometric truth; the
  geometric shares and the depth comparison inherit that.
- The table-band flaw (§3.6) hurts thin flat objects; a variant without it was not run (it would still fail on ep12,
  whose loss is the rack's anchor rotation).
- S11 runs before S2; the prefix variant does not commute exactly with S2.
