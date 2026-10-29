# VERIFY: independent check of refcheck/systematics

27 Oct 2026, CPU only, in this cloud container. Check name: `verify_systematics`. I tried to refute the systematics
measurement (`README.md`, `systematics_all.json`, `lagdrift.json`, `fixed_shift*.json` in this directory).

I did not re-run the other agent's scripts. I wrote my own code in
`docs/analysis/robustness-review-20261026/refcheck/verify_systematics/` (`vload.py`, `v0`-`v10`), with outputs next to it. The code shares only one thing with theirs: the kit's
own functions (`v2dlb.track3_pose`: registration, body conversion, frame-0 alignment, ADD-AUC), called with the
seeds and mesh budget of `pipeline/score_registered.py`, because the kit defines the scored body point.

Mocap was read only for these diagnostics, after inference, on public episodes.

Every number below is **MEASURED** here, unless it is marked *(their)* or *(doc)*.

**Verdict: partly confirmed.**
- The main claims hold:
  - no metric-scale error;
  - exact frame bookkeeping;
  - a constant lag of about half a frame;
  - the scene tilt from the kit's frame-0 alignment;
  - the centimetre-level rest-height errors (ep26 pot, ep24 boards, cup, lid, racks);
  - mkref's snap costing -0.016 on average.
- Four details do not hold, and two of their quantities are understated (listed below).

## Commands
```
source <rc>/venv/bin/activate; D=docs/analysis/robustness-review-20261026/refcheck/verify_systematics; W=<rc>/work/verify_systematics
python -I $D/v0_adhoc.py $D/v0_adhoc.json             # capture_time jitter, rollout bookkeeping, box-stored scores, mocap lows
python -I $D/v1_consistency.py $D/v1_consistency.json # frame counts; pre == T_tab @ perception + z shift
python -I $D/v2_scale_lag_tilt.py $D/v2_scale_lag_tilt.json
python -I $D/v3_drift.py $D/v3_drift.json
python -I $D/v4_make_npz.py $W/npz; bash $D/v4_score.sh $W/npz $W/scores   # 20 paths through pipeline/score_registered.py
python -I $D/v5_rest_height.py $D/v5_rest_height.json
python -I $D/v6_inproc.py $D/v6_shifts.json           # parity with score_registered.py, then time shifts on all paths
python -I $D/v7_tilt_anchor.py $D/v7_tilt_anchor.json
python -I $D/v8_rest_tilt.py $D/v8_rest_tilt.json
python -I $D/v9_snap.py $D/v9_snap.json
python -I $D/v10_frame0.py $D/v10_frame0.json
```
`<rc>` = `/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck`.
The score_registered.py outputs are copied to `$D/scores_registered/`. Code base: the working tree at e2f0a6b.

## Inputs and plumbing
| check | result |
|---|---|
| Is the canonical reference built from the canonical perception? | Yes, in all 10 episodes. The e2s parquet equals `T_table_from_world @ poses_world_vo` plus `object_z_shift`: 0.000 mm, at most 0.08 deg (float32 rounding). |
| Quaternion order | The parquet pose is read as x y z qw qx qy qz and `object_body_wxyz` as wxyz. Two pieces of evidence: the perception and reference identity above holds exactly, and the AUCs match the box-stored ones. |
| Frame counts | Mocap rows = perception = e2s = final reference in all 20 episodes. `frame_index` runs 0..T-1. |
| Stored rollouts (ep2, 21, 24, 26, 39; 45 object tracks) | `step == reference_frame` and 0..T-1, `start_frame` 0, 20 fps, `step_count` = T. **The rollout reference columns equal the canonical reference parquet: 0.00 mm, 0.00 deg.** So support fill and grasp lock leave the object path unchanged. |
| Box-stored `score_registered` reference AUC | ep2 0.9798, ep21 0.7776, ep24 0.8163, ep26 0.9229, ep39 0.9559. These equal my `pipeline/score_registered.py` runs on my own npz files. My in-process copy (v6) equals `score_registered.py` on 20 of 20 paths. |
| Mesh libraries | Only three objects differ between libraries: the sweeper (v2 vs v3), the beige cup (v3x) and the boards (v4). The simulator asset meshes in the store have the same vertices as the library meshes (ep21, ep2, ep11 blue cup). The canonical mesh assignment checks out. |

## Their key numbers, re-derived
| claim *(their)* | mine | status |
|---|---|---|
| s median 1.004 (0.971-1.020), 19 perception tracks | 1.0037 (0.9712-1.0204), the same anchors with my own Umeyama code. Registration-free fit (my own; the body point is solved jointly): 1.0055 (0.982-1.053) | confirmed. The range is wider without the kit registration (ep13 1.053, ep24 1.040). Nowhere near 0.65-0.85. |
| s, 10 references: 1.006 (0.977-1.022) | 1.0057 (0.9774-1.0219); registration-free 1.0046 (0.976-1.044) | confirmed |
| lag +0.48 frames (IQR 0.33-0.57), above 0 for 23 of 25 objects; ep27 -0.43 | I used two estimators different from theirs: velocity regression, and cubic-resampled RMSE. Perception: +0.51 / +0.53 (IQR 0.40-0.59), **25 of 25 positive**. References: +0.41 / +0.43, 14 of 14 positive. **ep27 pot +0.09 / +0.10**; ep0 pot +0.35 (theirs -0.07). | lag confirmed. **"ep27 is the exception (-0.43)" is an artefact of their speed cross-correlation**: their own RMSE-minimising shift also gave +0.25. |
| drift -0.11 +- 0.03 frames per 100 frames (prediction +1.27) | Linear-lag model per episode: median +0.07, mean +0.14 +- 0.15 (SE over 19 episodes, ep23 excluded). Per episode -0.86 to +1.96. With mocap resampled from `timestamp` onto `capture_time`, the drift becomes +1.34. | H-drift is falsified (confirmed). **Their SE is understated**: they treated 254 windows that overlap by 75 % as independent. |
| `capture_time` | Mean step 0.0500 s against 0.049373 s for `timestamp`. Jitter around a uniform grid: std 0.015-0.06 frames; single outliers up to 0.85 frames (ep41, ep13, ep22). | Not a lag source (new; measured). |
| kit scene tilt: median 2.4 refs / 2.5 perception; ep21 6.0, ep22 6.2, ep31 4.6 | Identical on the 27 source-episodes I computed: ep21 5.99, ep22 6.19, ep31 4.59, ep43 4.14, ep27 3.68. Median 2.43 refs, 2.60 perception. I did not compute ep11, which has no fixed object (axis + direction alignment). | confirmed |
| pitcher 30-41 mm too high after alignment (ep21), 22-23 mm (ep22) | ep21 ref: +29.9 mm at frame 0, +40.4 mm over the last 20 frames. ep22 perception: +23.3 / +23.0. | confirmed |
| rest tilt median 2.8 deg (IQR 2.2-3.7); 4.1 deg between objects | 2.71 (IQR 1.70-3.45, n=31), using my own rest blocks (speed < 1 mm and < 0.5 deg per frame, at least 10 frames). 4.31 between objects (n=12). ep13 cup 19.2, ep11 beige cup 7.65. | confirmed |
| ep26 pot: centre -29 / lowest -20 mm (ref); perception -14; snap -15.4 mm | -29.6 / -18.3; perception -14.2; `object_z_shift` -15.4. Mocap: the pot's lowest point is 19.8 mm above the table, in the rack. | confirmed |
| ep24 boards at the final rest: b1 +38 lowest / +33 centre, b2 +23 / +24 | b1 +40.5 / +36.2, b2 +26.1 / +26.6 with my table estimate of 0.6008. Theirs uses 0.5979, which accounts for the 2.9 mm difference. | confirmed (about 3 mm table-height uncertainty) |
| "board 2 also starts +9 / +17 mm high" | At the real start (frames 2-23): lowest +0.6, centre +5.3 (+3.5 / +8.2 with their table height). Their +17 is the median over frames 0-109, after a small nudge. | **partly**: the start is only a few mm high |
| blue cup -8 to -12; lid -6/-7 (lowest -7 to -9); snapped racks +8/+10 | cup -8.0 to -12.6 in all 5 episodes; lid -5.7 to -6.7 (lowest -7.9 to -9.1); ep12 rack +9.3/+9.9, ep27 rack +7.0/+8.0 | confirmed |
| "sweeper -9 mm (v2), -3 mm (flattened v3)" | ep31 is tracked and scored **with library_v3** and shows -8.4 to -11.0 mm. The ep18 reference's -1 to -3 mm comes from mkref's +9.7 mm snap of the sweeper, not from the flattening (ep18 perception with v2: -8 to -9). | **attribution wrong**: the flattened v3 sweeper is still about 9 mm low |
| mocap table 0.598-0.602 m | 0.598-0.602 (my estimate). In the episodes with a rack, the rack's lowest scan point is 2-3 mm below the cups and pots: ep12, 26, 27, 31 give 0.5975-0.5990, against 0.6002-0.6012 for the cups and pots. | confirmed. The spread depends on the object, so all rest-height numbers carry about +-2 mm. |
| Is mocap z the table normal? (implicit) | Pairs of objects resting at the start, about 30 cm apart: their lowest points differ by at most 4 mm (ep31 sweeper 7 mm). That is under about 0.5-0.8 deg. | holds. The 2-6 deg tilts are not a mocap-frame artefact. |
| blue cup mesh radius ratio 0.876 | 0.8756 (RMS surface radius). **Bounding-box extents are only 3-7 % smaller** (9.5 x 9.6 x 16.7 against 10.0 x 10.3 x 17.2 cm). | number confirmed. **"Our cup mesh is 12 % small" over-reads it**: the RMS radius also reflects shape (inner wall). |
| snap (pre minus perception, same mesh): mean -0.016; ep26 -0.062, ep21 -0.056, ep12 -0.031, ... ep18 +0.007 | Identical in all 10 episodes, mean -0.0162 (in-process). ep21 -0.0561 and ep26 -0.0615 also come out the same through `score_registered.py`. ep39 is exactly 0: with one object, the kit's alignment absorbs a constant z shift. | confirmed |
| contact retarget (ref minus pre): mean +0.003 (ep31 +0.028, ep26 +0.012, ep18 -0.005) | +0.0032; ep31 +0.0283, ep26 +0.0121, ep18 -0.0052 | confirmed |
| anchor sensitivity, ep18 perception with v2 vs v3: 0.938 vs 0.964 | 0.9380 vs 0.9642 | confirmed |

## Time shift, re-scored (in-process, parity-checked; all public paths, ep23 excluded)
| variant | refs (n=10) mean dAUC (episodes better) | perception (n=19) |
|---|---|---|
| +0.5 frame, linear + slerp (their method) | +0.0069 (9) | +0.0052 (16) |
| +0.5 frame, cubic + slerp | +0.0059 (8) | +0.0051 (14) |
| **+0.5 frame with frame 0 kept as is** | **+0.0039 (10 of 10)** | **+0.0033 (19 of 19)** |
| -0.5 frame, linear | -0.0050 (0) | -0.0072 (0) |
| +1 frame, integer (no interpolation) | +0.0058 (6) | +0.0043 (7) |
| -1 frame, integer | -0.0147 (0) | -0.0188 (0) |

The lag is real. The integer shifts are an interpolation-free control: -1 frame costs 2.5 to 4.4 times what +1 frame gains, which a late path predicts and a smoothing effect does not.

About 40 % of the headline +0.5 gain comes from moving frame 0. The kit aligns the whole scene on frame 0, so any change to frame 0 moves the score.
- A pure 1-frame perturbation of frame 0 (frame 0 replaced by frame 1, `v10`) changes the AUC by -0.011 to +0.065 per episode, with no consistent sign: 9 of 19 perception paths better, 8 of 10 refs.
- So the large per-episode +0.5 gains are mostly this frame-0 effect: ep31 perception +0.018 (frame 0 kept: +0.002), ep39 ref +0.014 (+0.004), ep18 perception +0.021 (+0.003).
- The same mechanism makes the per-episode sign depend on the interpolation: ep26 ref +0.0015 linear, -0.0046 cubic.

## Tilt oracle, my variant
I removed only the anchor object's frame-0 tilt, as a constant body-frame swing taking our anchor's up axis (relative to our table) to mocap's (`v7`, oracle).
- refs: +0.0293 mean (median +0.020, 7 of 10 better);
- perception: +0.0232 (median +0.007, 15 of 19);
- ep21 ref 0.7776 -> **0.9575** (+0.180), against their tilt-only result of 0.8878 and their all-corrections result of 0.9519. Also checked through `score_registered.py`.
- ep22 perception 0.871 -> 0.9663 (+0.095, the same as theirs).
- Negative on ep12 (-0.009 ref) and ep26 ref (-0.0145). This agrees with their remark that errors cancel.

**So their oracle deltas are not upper bounds** (the README says "upper bound"). They are the gains of one particular correction; a different oracle gains more. Their "+0.016 tilt" and "+0.048 all" therefore understate what the frame-0 anchor orientation costs.

## Their problems_found, judged
1. **Half-frame lag, no drift; +0.5 gives +0.007 / +0.005.** Survives, with three corrections:
   - The lag is positive for 25 of 25 objects with my estimators. ep27 is about 0, not -0.43.
   - The pure time effect is +0.004 / +0.003. The rest is frame-0 alignment sensitivity.
   - The drift SE is about 0.15, not 0.03.
2. **Scene tilt from the kit's frame-0 alignment.** Survives and is strengthened: the anchor-only oracle gives +0.18 on ep21, and +0.03 / +0.02 on average.
3. **mkref's per-object snap costs -0.016 (ep26 -0.062, ep21 -0.056, ep12 -0.031).** Survives (identical values).
4. **ep26 pot 29 mm too deep; perception -14; the snap doubles it.** Survives.
5. **ep24 boards float.** Survives at the final rest (b1 +33 to +36 centre, +38 to +40 lowest; b2 +24 to +27). Board 2 "starts +9 / +17": only partly. At the actual start it is +1 to +8 mm, depending on the table estimate.
6. **Recurring resting-centre errors.**
   - The cup, lid and rack values survive.
   - The sweeper attribution does not: the v3 sweeper is still about 9 mm low (ep31). ep18's -3 mm comes from the snap.
   - "Cup 12 % small" over-reads the RMS-radius ratio: the extents are 3-7 % smaller.
7. **ep11 blue cup tracked up while stacked.** Survives: +15.7 mm centre and +23 mm lowest point at the last rest, in perception and reference alike.
8. **Rest orientation 2-4 deg, object-specific.** Survives.
9. **The single oracle corrections interact.** Plausible. I did not re-run their per-object tilt oracle. My anchor-only oracle is also negative on ep12 and ep26.
10. **Depth-scale bias falsified.** Survives: s = 1.00 +- 0.02 with two methods.
    - Minor misquote: the work log ('Hand scale check') says the fit is 0.839 with widened bounds, so it is not pinned at the 0.85 clamp *(doc)*.
    - The doc's version of the hypothesis is an additive 7 cm depth offset at 0.45 m. That would also give objects s of about 0.84, so it is falsified too.
    - "The hand error is in the hand pipeline" is an inference, not a measurement.
11. **H-drift falsified.** Survives.

Classic errors I hunted and did not find:
- quaternion order;
- frame origins (kit anchor conversion; the perception and reference identity is exact);
- a wrong run or copy (the canonical perception reproduces the canonical reference; the rollout reference columns equal it; the box scores match);
- a mesh mismatch (handled; ep18 rescored on the same mesh);
- off-by-one (counts are equal; the integer-shift asymmetry is a lag, not an index error);
- selection bias (all 20 public episodes used; only ep23 is excluded, for its identity swap).

The per-object vs per-episode statistics are labelled correctly.

## New hypotheses from this check (not tested here)
- **H-frame0-noise.** The kit's frame-0 alignment makes a single-frame change of frame 0 move the AUC by up to 0.065.
  - So per-episode deltas below about 0.01 are not interpretable without a frame-0-invariant control (frame 0 kept, or the rollout's own frame 0).
  - Falsifier: score each candidate with frames 0 and 1 swapped. Measured here: 3-frame averaging of frame 0 gives +0.0003 (perception) and +0.003 (refs), so naive frame-0 smoothing is not a fix.
- **H-shift-deploy, revised.** Expect about +0.003 to +0.004 from a +0.5-frame advance in rollouts, not +0.007.
  - Falsifier: their retrain experiment, scored also with frame 0 held fixed.
