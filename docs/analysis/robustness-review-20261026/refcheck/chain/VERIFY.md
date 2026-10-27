# VERIFY: independent check of refcheck/chain (27 Oct 2026)

Check name: `verify_chain`. I tried to refute `chain/README.md`, `tables.md` and `results.json`.
- My scripts and outputs are in `../verify_chain/`; bulky scratch is in `$SP/work/verify_chain/`.
- I used my own code and did not re-run the chain's scripts.
- CPU only: 36 scorer runs (6 of them failed on an argparse error and were re-run), about 12 CPU-min, $0.
- Every command is in `../verify_chain/commands.log`.
- **[M]** = measured here. **[doc]** = taken from a file or a doc. **[H]** = hypothesis.

## Verdict: partly confirmed

- **Every chain number I re-derived reproduces exactly.** That is all 232 scene and per-object AUCs of the
  10-episode chain, the hybrids, the sweep registration costs, the v2/v3 sweeper effect and the ep0 lid.
- **These mechanisms hold:**
  - mkref only applies a constant per-object vertical shift;
  - rest settle changes the object path;
  - support fill and grasp lock do not change it;
  - the kit aligns the scene on slot 0 (translation) and on the first non-symmetric object (rotation).
- **The ep26 finding is the strongest one, and it holds physically.**
- **One causal claim does not survive: that the snap is "wrong on ep21" because of a "table-plane error".**
  - The ep21 score loss is real.
  - But by frame-independent bottoms, the ep21 snap is physically about right.
  - The loss comes from the kit's scoring frame:
    - the pitcher's frame-0 orientation (the rotation anchor) is 4° off;
    - with our meshes, the blue cup's slot-0 anchor offset adds about 1 cm.
- **Smaller corrections:**
  - the headline's "6 of 10 within 0.01" is really 5;
  - the per-object mkref mean is diluted by 10 structural zeros;
  - ep11 is scored with library_v3x, which was not adopted;
  - the magnitudes that depend on registration move by ±0.02–0.03 with the kit's registration seed.

## 1. What I ran (own code)

- **`verify_chain/myscore.py`: an independent registered ADD-AUC.** My own code does the following:
  - GT parquet reading (w-first quaternion → rotation matrix);
  - the npz, FlashCHORD reference parquet and raw evaluator parquet readers (it does not use `ref2npz.py` or the
    kit reader);
  - the host stand-in (area-weighted centroid, PCA axis);
  - the anchor conversion, the frame-0 alignment, the symmetric ADD and the AUC, all with rotation matrices.

  From the kit it uses only these official pieces, which I did not re-write:
  - `budget_mesh`;
  - `_register_object_body`;
  - `_sample_mesh_surface`, with the same seeds as `score_registered.py`.

  Options:
  - `--alt_points` swaps in trimesh's sampler with another count and seed;
  - `--seed_offset` perturbs the registration seed;
  - `--tshift` scores path[t+k] against mocap[t] after aligning the unshifted path.
- **`geom.py`: no scorer and no ground truth (part 1).** It forms `E_t inv(P_t)` per object (e2s against perception),
  then processed against e2s, then the evaluator reference against processed. Part 2 is diagnostic: frame-0 scan
  bottoms at the mocap poses for all 20 public episodes.
- **`tilt.py`: diagnostic.** At frame 0 it splits a relative height error in the kit-aligned frame into two parts:
  - the tilt of the alignment against mkref's own table normal;
  - the object bottoms against mkref's plane.
- **`lag.py`: diagnostic.** It cross-correlates the perceived and mocap speeds with no alignment at all.
  `shift.py` and `--tshift` are the frame-index test.
- **`compare.py`** compares my scores against `chain/results.json` and writes `compare.json`.

## 2. Re-derived numbers [M] (myscore.py unless noted)

| quantity | chain | mine | |
|---|---|---|---|
| 10-ep scene mean, lib: perc / e2s / ref / sim r1 | 0.915 / 0.899 / 0.902 / 0.722 | 0.9154 / 0.8992 / 0.9023 / 0.7216 | ok |
| same, scan: perc / e2s / ref | 0.934 / 0.932 / 0.935 | 0.9344 / 0.9324 / 0.9351 | ok |
| all scene + per-object AUCs, 10 eps × 8 links (232 values) | results.json | max abs diff 0.0001 | ok |
| mkref per object, lib (n=19): mean / min / max | −0.017 / −0.123 / +0.013 | −0.0171 / −0.1230 / +0.0132 | ok (see §5) |
| contact retarget per object, lib: mean / min / max | +0.004 / −0.007 / +0.056 | +0.0035 / −0.0072 / +0.0565 | ok |
| ep26 pot perc → e2s, lib / scan | −0.123 / −0.047 | 0.9474→0.8244 / 0.9130→0.8663 | ok |
| ep26 pot dz error, scan, all frames | +0.83 → −1.76 cm | +0.834 → −1.756 | ok |
| ep21 pitcher perc → e2s, lib / scan | −0.112 / −0.095 | 0.6915→0.5793 / 0.9187→0.8236 | ok |
| ep21 pitcher dz error, scan, all frames | +1.06 → +1.99 cm | +1.059 → +1.987 | ok |
| ep12 rack perc → e2s, lib / scan | −0.061 / +0.059 | 0.9997→0.9382 / 0.9392→0.9979 | ok |
| ep21 hybrid, pitcher perc (scans / cup ours / pitcher ours / all ours) | 0.919 / 0.810 / 0.798 / 0.692 | 0.9187 / 0.8098 / 0.7977 / 0.6915 | ok |
| ep31 hybrid, rack perc | 0.820 / 0.756 / 0.812 / 0.688 | 0.8203 / 0.7556 / 0.8125 / 0.6875 | ok |
| sweep pitcher registration cost ep21 / ep22 | −0.230 / −0.215 | 0.6835−0.9133 / 0.7497−0.9646 | ok |
| sweep ep31 rack registration cost | −0.144 | 0.6879−0.8319 = −0.144 | ok |
| ep18 sweep dust pan, library_v2 → v3 (only the sweeper differs: md5) | 0.881 → 0.933 | 0.8814 → 0.9333 | ok |
| guard ep0 lid, lib / scan | −0.060 | 0.9363 / 0.9955 | ok |
| ep2 r1 sim / reference (lib) | 0.4513 / 0.9798 | 0.4513 / 0.9798 | ok |
| blue cup registration anchor offset (eps 11, 12, 13, 21, 22) | 0.9–1.05 cm, mostly axial | 0.91–1.05 cm, of which 0.89–1.03 along the axis | ok |
| surface RMS radius, blue cup ours / scan | 6.08 / 6.94 cm | 6.08 / 6.93 | ok |
| pitcher surface centroid, ours vs scan | +2.0 cm up, 1.4 cm sideways | (−0.34, +1.40, +2.01) cm | ok |

**Scorer-free [M] (`geom.json`):**
- **mkref is a constant per-object shift in all 10 episodes, not only the 7 diagnosed.** `M_t = E_t inv(P_t)` is the
  same in every frame (< 0.001 mm, < 1e-5°) and has the same rotation for every object (< 1e-5°). The objects differ
  only in table-frame z:

  | ep | object | relative shift (mm) |
  |---|---|---|
  | 2 | lid | −1.64 |
  | 11 | beige cup | +3.15 |
  | 12 | rack | +9.96 |
  | 18 | dust pan | −3.20 |
  | 21 | pitcher | +9.30 |
  | 24 | board 2 | −1.92 |
  | 26 | pot | −25.94 |
  | 27 | pot | −1.46 |
  | 31 | rack | +10.33 |

  These equal `table_frame.npz` `object_z_shift` differences.
- **The scored perception is exactly mkref's input.** `world_T_cam · cam_T_obj` from `poses.npz` equals
  `poses_world_vo.npz` (0.0 mm, 0.0°) in all 10. The constancy of `M_t` also proves that each e2s was built from
  exactly that perception file.
- **The evaluator reference columns equal the processed parquet.** They differ by one rigid transform shared by all
  objects (≤ 1e-4 mm, ≤ 1e-5°) in all 10, so support fill and grasp lock leave the object path unchanged. This is a
  direct pose comparison, which is stronger than the chain's score equality.
- **Contact retarget changes the object path exactly where rest settle ran.**
  - With rest settle (2, 11, 18, 21, 26, 31, 39; `contact_retarget.json` has `rest_settle`): up to 33 mm / 6.3° on
    the ep2 pot, 32 mm / 12.9° on the ep18 dust pan and 19 mm / 6.7° on the ep26 pot.
  - Without it (12, 24, 27): 0.000 mm.
- **Mocap, ep26 at frame 0.**
  - The pot's lowest scan point is at 0.6184 m and the rack's at 0.5981 m: the pot is 2.04 cm above the rack bottom.
  - Across the public episodes, the median bottom of an on-table pot is 0.6010 m; the pot is 1.73 cm above that.
  - The pot's xy footprint overlaps the rack's.
  - In ep27, by contrast, the pot is beside the rack and on the table (0.6007 m).

## 3. Robustness of the key numbers [M]

- **Host point sampling (3000 trimesh points, another seed): no effect.**
  - ep26 pot mkref effect: −0.124 lib / −0.051 scan.
  - ep21 pitcher: −0.112 / −0.097.
  - All within 0.004 of the chain.
- **Registration seed: the magnitudes move. Treat every registration-dependent number as ±0.02–0.03.**
  - The kit's seed is `1_000_003·episode + 101·slot`, so the registration on an eval episode will differ.
  - ep21 at the kit seed and 4 other seeds:
    - perception scene AUC (lib): 0.833–0.857 (kit seed 0.837);
    - pitcher perception AUC (lib): 0.682–0.730, so the pitcher registration cost is −0.19 to −0.24;
    - pitcher mkref effect: −0.080 to −0.114.
  - ep26 at 3 seeds:
    - pot perception AUC (lib): 0.926–0.947, so "lib beats scan" for the pot is +0.013 to +0.034;
    - pot mkref effect: −0.095 to −0.123.
  - The signs never change.

## 4. Classic-error hunt

- **Quaternion order: no error.**
  - The GT `pose` is read as x, y, z, qw, qx, qy, qz, both in `score_registered.py` lines 86-88 and in my own reader.
  - Physical check: in all 20 public episodes the scan bottoms at the mocap poses sit at 0.5975–0.6053 m, a level
    table.
  - FlashCHORD `wxyz` is read correctly: a misread would make `M_t` vary over time, and it does not.
  - The evaluator parquet's metadata says `xyzw`.
- **Frame origins: no error, and "scan" scoring is not an upper bound.**
  - Our meshes are fused in the tracked body frame (`recon_mesh.py`), so the kit's registration to the scan is
    0.8–3.2° and ≤ 1.05 cm.
  - "Scan" scoring is therefore meaningful, but it means "registration = identity", not an upper bound. This agrees
    with the chain.
- **Wrong run or copy: none found.** The perception→e2s pairing (constancy of `M_t`) and the processed→evaluator
  pairing are confirmed in all 10 episodes.
- **Mesh library: two labelling caveats, no scoring error.**
  - library_v2 → v3 differs only in `mini_sweeper`, and v3 → v3x only in `beige_cup` (md5).
  - ep11 is scored with v3x, which `library_v3x/README.md` calls "NOT adopted". So "submitted meshes" is not literally
    true for ep11; it is the tracking mesh of that run.
  - ep18 and the sweep/guard runs of ep31 were tracked with the v2 sweeper and scored with v3. The flatten moved 121
    bottom vertices and left the frame unchanged, so this is acceptable.
- **Off-by-one: none found.**
  - Frame counts are equal for GT, perception, e2s, the processed parquet and the evaluator, and GT `frame_index` is
    0..N−1.
  - Timing test (`--tshift`, alignment fixed), on six episodes (39, 26, 18, 2, 42, 21):
    - k = −1 is always the worst (−0.012 to −0.045);
    - k = 0 is best or tied in five (ep21 lib and ep2 scan are ties with k = +1);
    - k = +1 is better only in ep26 (+0.008 lib / +0.011 scan).
  - The speed cross-correlation (`lag.json`) peaks at lag 0 or +1 for moving objects, never at 2 or more.
  - There is a hint of a sub-frame lag: HV2 below.
- **Averaging: labels correct, one presentation flaw.**
  - Scene AUC = the mean of per-object AUCs (kit `_add_auc`). The 10-episode mean = the mean of scene AUCs.
    Per-object tables = means over object-episodes.
  - However, 10 of the 19 per-object mkref deltas are exactly 0 by construction (slot 0 or a single object).
- **Symmetric objects: no error.**
  - Cups are order 360 about the PCA axis and the lid is order 2; reproduced.
  - The "130°" cup rotation is spin, as the chain says.
- **Selection: all episodes used, but small and mixed samples.**
  - The 10 canonical episodes are all the episodes that have a reference, so no easy-episode selection.
  - The recipes differ, though: only ep11 and ep21 use the current one.
  - The per-object reference means rest on n = 1–4 (the pitcher on n = 1).
- **Claims not backed by a measurement:**
  - "Lib beats scan because our mesh's registration offset cancels a tracking offset from the same mesh" is untested
    (label [H]).
  - "Matches forensics 'pot 29 mm too deep'" is [doc].
  - The ep21 "table-plane error" is contradicted (§5, P2).

## 5. Problem by problem

**P1. Snap moves objects not on the table (ep26): SURVIVES, strengthened.**
- The score effect is robust (§2, §3).
- It is physical in every frame:
  - mocap pot bottom: 2.04 cm above the rack bottom;
  - perceived (our mesh against mkref's plane): pot +1.54, rack −1.05, so +2.59 relative;
  - the snap set the relative height to 0, so the pot ends 2.04 cm too low relative to the rack.
- The current `pipeline/mkref.py` (lines 963-967) still snaps any object with |h| ≤ `snap_max` = 2 cm, so the problem
  recurs. Whether today's perception still gives h < 2 cm on ep26 was not run.

**P2. "The snap amplifies table-plane error" (ep21): the score loss SURVIVES, the cause is KILLED.**
- `tilt.py` at frame 0 [M] shows the following.
- **Scan mode (our frame taken as the scan frame):**
  - the kit takes the scene rotation from the pitcher's frame-0 orientation;
  - in that frame, mkref's table normal is tilted 4.05° from mocap vertical;
  - the blue cup's axis agrees with the table normal to 0.46° once the scene is levelled on that normal;
  - in the kit frame, the cup is 4.23° off;
  - so the pitcher's frame-0 orientation is the outlier, not the plane.
- **Size of the effect:** over the 33.2 cm between the cup and the pitcher, the 4.05° tilt alone raises the pitcher
  by +1.64 cm in the kit frame. Levelled, perception has the pitcher 1.09 cm too low, and the snap takes it to
  −0.16 cm.
- **Frame-independent bottoms** (`snapcheck.json` [chain M]; ep21 and ep26 re-derived here). This is the needed
  relative shift (from mocap bottoms) against the applied one, |residual| before → after the snap, in cm:

  | ep | before | after | effect of the snap |
  |---|---|---|---|
  | 11 | 0.47 | 0.16 | better |
  | 12 | 0.76 | 0.24 | better |
  | 18 | 0.51 | 0.19 | better |
  | 21 | 1.14 | 0.21 | better |
  | 24 | 0.13 | 0.32 | slightly worse |
  | 27 | 0.18 | 0.33 | slightly worse |
  | 31 | 0.35 | 0.69 | worse |
  | 2 (lid not snapped, by design) | 0.71 | 0.87 | worse |
  | 26 | 0.55 | 2.04 | much worse (stacked pot) |

  These residuals mix our-mesh bottoms with scan bottoms, which differ by up to about 0.6 cm in the mesh frame. So
  residuals under about 0.5 cm are within noise.
- **With our meshes (lib):** the blue cup's slot-0 registration raises the whole scene by about 0.9 cm. With only
  the cup ours, the ep12 rack dz goes −0.97 → −0.10. This makes the pitcher look too high before the snap.
- **Conclusion:** on ep21 the snap is physically about right, and the −0.112 / −0.095 are scoring-frame artifacts.
  - The chain's "plane 1.3 cm above the mocap table under the pitcher" includes the +1.64 cm alignment lever. Without
    it, the plane is consistent with the cup's plane to about 0.1–0.3 cm.
  - This favours H3's alternative (the rotation anchor) over H3 itself.
  - Turning the snap off for ep21 would leave the pitcher 0.9 cm inside mkref's table in the simulation, to buy back
    score through compensating errors that cannot be known without GT.

**P3. Contact retarget with rest settle changes the object path: SURVIVES.** See the scorer-free results in §2.
Support fill and grasp lock leave the path unchanged (rigid equality, ≤ 1e-4 mm).

**P4. The slot-0 registration error moves every object: SURVIVES.**
- The code reading is correct: translation from slot 0, rotation from the first object without an axis.
- The hybrids and the ep18 v2/v3 effect (+0.052) reproduce.
- Addition: the rotation anchor's frame-0 orientation error also moves the other objects. In ep21 (scan) that is
  4.05°, about 1.6 cm at 33 cm. In ep12 the rotation anchor is the rack; the plane is tilted 2.99° and the cup 4.49°.

**P5. Our meshes cost a lot at registration for the pitcher, rack (ep31), cups, lid, sweeper and pot (ep43):
SURVIVES with a caveat.**
- Reproduced: the pitcher (ep21, ep22), the rack, sweeper and blue cup in ep31 and ep12, and the lid in ep0.
- The beige cup and ep43 were not re-run.
- The pitcher cost is −0.19 to −0.24 across registration seeds.
- The cost also depends on the guessed host anchor and point count. That is the chain's caveat, and I did not test it.

**P6. Scan scoring is not an upper bound: SURVIVES** (measured: ep26 pot lib 0.947 > scan 0.913; +0.013 to +0.034
across seeds). The mechanism the chain gives is [H].

**P7. The box-recorded perception AUCs do not reproduce: SURVIVES, with a sharper reason.**
- `perc2.py` lines 511-525 score with the kit's unregistered metric:
  - `_warp_to_reference_start` (full slot-0 orientation, the cup's spin included);
  - 500 trimesh samples of the scan in the scan frame;
  - no symmetry and no registration.
- That is a different metric, not an older version of the registered one. For example, on ep21 it gives cup 1.000
  and pitcher 0.848 (`result.json` [doc]).

**P8. The hidden-loss model should use the reference, and the product is 0.04 pessimistic: PARTLY.**
- The arithmetic reproduces: 0.682 against 0.722.
- `sim_vs_ref` (box `summary.json`) comes from `qa.py`'s unregistered warp metric, while `ref lib` is registered. The
  product therefore mixes two metrics. Use it from r1 only, as indicative.
- The reference means rest on n = 1–4.

## 6. Corrected numbers

- **Headline count.** 5 of 10 are within ±0.01 (2, 18, 24, 27, 39); ep31 gains +0.024 from rest settle; 4 lose
  (11 −0.012, 12 −0.031, 21 −0.060, 26 −0.049). The headline said "6 of 10".
- **mkref per-object mean.** −0.017 over n = 19 includes 10 structural zeros. Over the 9 objects that mkref can move
  in the score it is −0.036.
- **ep26 pot height.** The pot is 2.04 cm above the rack's lowest point and 1.73 cm above the median on-table pot
  bottom (0.6010 m).
- **ep21 plane.** The plane offset under the pitcher relative to the cup is about +0.1–0.3 cm once the 4.05°
  alignment tilt is removed, not 1.3 cm. The pitcher's frame-0 orientation is off by 4.05° (scan) or 5.99° (lib)
  against the table normal.
- **Registration-dependent magnitudes are ±0.02–0.03 across registration seeds.**
  - pitcher perception (lib): 0.68–0.73;
  - ep21 mkref effect: −0.08 to −0.11;
  - ep26 mkref effect: −0.095 to −0.123.
- **ep11 meshes.** ep11 is scored with library_v3x, which was not adopted, not with the submitted library_v3.

## 7. New hypotheses (untested; [H])

- **HV1: the ep21 snap loss is a scoring-frame artifact, not an mkref error.** Its two sources are the pitcher's
  4–6° frame-0 orientation as the scene's rotation anchor, and, with our meshes, the blue cup's ~1 cm anchor offset.
  - Test (diagnostic): rescore perc and e2s with the scene rotation taken from mkref's table normal plus the
    pitcher's yaw.
  - Falsified if the pitcher's e2s − perc stays below −0.05.
  - GT-free variant: re-estimate the pitcher's frame-0 tilt against the table plane before tracking.
- **HV2: perception (and so the reference) lags mocap by about 0.3–0.7 frame.** Evidence: k = −1 always costs
  0.012–0.045 while k = +1 costs ≤ 0.009 or gains (ep26 +0.008).
  - Test: score with fractional (interpolated) shifts on all 20 episodes.
  - Falsified if the mean peak satisfies |k| < 0.2 frame.
- **Caution on the chain's H2.** Its "bottom > 0.5 cm above the lowest object" variant would also stop snapping
  objects that do rest on the table. The perceived bottoms scatter by about 1 cm (`snapcheck` mkref_h):
  - ep12 blue cup, 1.0 above the rack;
  - ep21 blue cup, 0.93 above the pitcher;
  - ep31 sweeper, 1.04 above the rack.
  The footprint-over-another-object rule changes only ep26.

## Files

- **Scripts** (`../verify_chain/`): `myscore.py`, `geom.py`, `tilt.py`, `lag.py`, `shift.py`, `compare.py`,
  `run_verify{,2,3,4}.sh`.
- **Outputs:** `scores/*.json`, `compare.json`, `geom.json`, `tilt_ep{11,12,21,26}_{scan,lib}.json`, `lag.json`,
  `commands.log`.
- **Scratch:** `$SP/work/verify_chain/` (logs, per-frame ADD npz, shifted npz).
- Nothing outside `refcheck/verify_chain/` and this file was written. No git commands.
