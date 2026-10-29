# refcheck / systematics: systematic geometric errors of our object paths vs mocap (public episodes)

26 Oct 2026, CPU only, robustness review (`docs/analysis/robustness-review-20261026.md`). Mocap is read only here, after
inference, as a diagnostic on the 20 public episodes. Nothing here feeds inference.

Inputs: the canonical references and perception tracks picked in `../resolve/canonical_refs.json`.
- `ref`: the final reference parquet (10 episodes).
- `pre`: its `e2s_reference.parquet`, the mkref output before contact retarget.
- `perc`: the canonical perception `poses_world_vo.npz` (all 20 episodes).

Code: uncommitted scripts in this directory, run on the working tree at `8724a24`. Every number below was MEASURED here
with the commands listed, unless it is marked as coming from a doc.

## Bottom line

| check | result (measured) | AUC if corrected (oracle; mean over 10 refs / 20 percs) |
|---|---|---|
| 1 metric scale | **No scale bias.** Similarity fit s = our length / true length: median 1.004 (0.971 to 1.020) over 19 perception tracks, 1.006 (0.977 to 1.022) over the 10 references. Per object: 1.005 (IQR 0.996 to 1.013). Displacement ratio where mocap moved more than 2 cm: 1.015 (IQR 1.005 to 1.026). | +0.003 / +0.001 |
| 2 time | Frame bookkeeping is exact in every episode. Mocap rows = video frames = perception = reference = rollout steps; `reference_frame == step`; `start_frame` 0; 20 fps; motion_speed 1.0. There is one **constant lag: our path is late by about half a frame** (+0.48 frames, IQR +0.33 to +0.57, about 24 ms). It is positive for 23 of 25 moving objects, in perception and in the reference alike, so mkref does not cause it. **No drift** along the episode. | per-episode lag removed: +0.006 / +0.005. **Fixed +0.5-frame advance: +0.0070 (9 of 10 refs better) / +0.0050 (17 of 20)**. The opposite shift is the control: -0.0050 / -0.0068. |
| 3 up axis | The kit aligns the whole scene on the anchor object's frame-0 orientation, so that object's orientation error becomes a **scene tilt**. Our table normal ends up 0.8 to 6.2 deg from mocap z (median 2.4 refs / 2.5 percs). Worst: ep21 and ep22 at 6.0 and 6.2 deg (the pitcher, our mesh lacks half its base), ep31 4.6, ep43 4.1, ep27 3.7. | included in tilt |
| 4 resting height | Mocap table top 0.598 to 0.602 m in all 20 episodes. **ep24 boards float (confirmed):** at the final rest the lowest point is board 1 +38 mm, board 2 +23 mm (centre +33 / +24 mm). **ep26 pot too deep (confirmed):** centre -29 mm, lowest point -20 mm. Half of that comes from mkref's per-object snap (perception -14 mm). Other recurring errors are listed below. | +0.022 / +0.017 |
| 5 rotation bias | At rest, an object's tilt relative to our table, compared with mocap: median 2.8 deg (IQR 2.2 to 3.7). It is **not shared** by the objects of one episode (median 4.1 deg between their implied up axes), so it is an object-orientation error, not a table-plane error. | +0.016 / +0.016 |
| all corrections together | | **+0.048 / +0.032** (they are not additive) |
| extra: mkref per-object z snap | Relative to the unsnapped perception (same mesh) the snap costs **-0.016 AUC** on average. ep26 -0.062, ep21 -0.056, ep12 -0.031, ep2 -0.012, ep11 -0.011; ep18 +0.007, ep24 +0.005, ep27 +0.003. | |

Answer to the owner's question for this check:
- The reference has no scale error and no frame-indexing error.
- It does carry three systematics that its AUC does not show.
  1. A half-frame lag.
  2. Resting-height errors, centimetre-level for specific objects: snapped racks and pots, the lid on the pot, small cups, floating boards.
  3. Few-degree orientation errors at rest. These matter most on the anchor object, because the kit's frame-0 alignment turns them into a scene tilt.

The largest single case is ep21: the reference AUC is 0.778 and the oracle correction of all three gives 0.952. The pitcher's 5.7 deg tilt at frame 0 rotates the scene and puts the pitcher 30 to 41 mm too high in the aligned frame. Its own height above our table is only 5 mm off.

## Method (`systematics.py`)
- **Comparable centres.** The kit's own registration (`track3_pose._register_object_body`) of our mesh to the public scan is used, with the same seeds and the same 4096-face budget as `pipeline/score_registered.py`. It gives the body point of our mesh that matches the scan's surface centroid (the "kit anchor") and the body rotation B.
  - Our poses are converted with the kit's `_convert_object_body`, so ours and mocap are compared in the scan's body convention.
  - As a cross-check, s is also fitted on the plain surface centroids (our mesh vs scan). That gives a median of 1.00 (perception 0.9995, reference 0.998). The rack episodes are lower: 0.94 to 0.97 on ep12, ep26 and ep31. On our meshes, the surface centroid and the kit anchor are 10 to 13 mm apart for the rack and 19 mm for the pitcher. The kit anchor is what is scored.
- **Rest frames** come from mocap: before an object's first motion and after its last. Motion means more than 5 mm or 3 deg from the first (last) pose, with a 3-frame margin.
- **1 Scale.** Umeyama similarity fit mocap -> ours, joint over all objects and frames and per object. It is reported only where the mocap spread exceeds 2 cm. Fitting gt -> ours keeps our tracking noise out of the scale. The inverse fit gives the same values to within 0.003.
  - Also measured: the inter-object distance at rest, and the |displacement from frame 0| ratio where mocap moved more than 2 cm.
- **2 Time.**
  - `timecheck.py`: frame counts and clocks.
  - Lag: cross-correlation of centre-speed profiles (Gaussian sigma 1 frame on both, parabolic sub-frame peak). Cross-checked by the shift that minimises the rigid-fit RMSE.
  - `lagdrift.py`: windowed lags (60-frame windows) with a pooled within-episode slope.
- **3 Up axis.** Three estimates:
  - (a) the kit's alignment rotation (`_align_registered_scene`) applied to our table normal;
  - (b) the best rigid fit of all centres (poorly conditioned: the smallest mocap extent is 0 to 4 cm);
  - (c) per object at rest, R_gt R_ours^T z.
- **4 Height.**
  - Our object: the lowest convex-hull vertex of our (visual = simulator) mesh above OUR table plane (table frame z = 0.60).
  - Mocap object: the lowest scan hull vertex above the mocap table.
  - Mocap table = the median lowest point of the lowest resting object.
  - Also measured: the centre-height error (the scored quantity), the relative centre height of the two objects, and the vertical error after the kit alignment.
- **5 Rotation bias.** The swing taking mocap's up axis to our table's up axis, in the scan body frame, as a mean signed rotation vector per rest segment. Also the kit-aligned residual rotation: spin about the axis is dropped for cups, 0/180 deg is allowed for the lid.
- **AUC cost.** Each systematic is removed from our path with mocap knowledge (an oracle), and the path is re-scored with the kit's registered AUC and our meshes. That gives an upper bound on what the systematic costs.
  - scale: centres scaled by 1/s;
  - time: shifted by the episode lag;
  - height: rest-segment centre heights set to the truth, relative to the table;
  - tilt: a constant body-frame tilt removed;
  - all: the four together.
- **Scorer parity (measured).**
  - The in-process scorer reproduces the box-stored `score_registered.py` reference AUC of all 10 results dirs exactly, and the box perception AUCs of the 10 perception-only episodes.
  - Four corrected paths re-scored with `pipeline/score_registered.py` itself give identical values (`verify/`): ep21 all 0.9519, ep21 tilt 0.8878, ep26 height 0.9581, ep2 time 0.9835.

## Commands (machine: this cloud container, CPU)
```
source <scratchpad>/refcheck/venv/bin/activate; D=docs/analysis/robustness-review-20261026/refcheck/systematics
python -I $D/systematics.py <work>/systematics_all.json --save_npz       # ~20 min on 1 core; npz of base/corrected paths in <work>/npz
python -I $D/timecheck.py $D/timecheck.json
python -I $D/lagdrift.py <work>/lagdrift_auto.json
python -I $D/fixed_shift.py <work>/fixed_shift.json; SHIFTS=-0.5 python -I $D/fixed_shift.py <work>/fixed_shift_neg.json
python -I pipeline/score_registered.py 21 <work>/npz/ep21_ref_all.npz --meshes meshes/library_v3 --t3 <rc>/t3 --kit <rc>/kit/v2d_submission_kit --out $D/verify/ep21_ref_all.json   # and 3 more
python -I $D/summarize.py <work>/systematics_all.json <work>/lagdrift_auto.json <work>/fixed_shift.json > $D/tables.md
```
`<work>` = `/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck/work/systematics`
(holds the npz paths; not kept). Outputs in this directory:
- `systematics_all.json`: everything per episode and source;
- `tables.md`: all tables;
- `timecheck.json`, `lagdrift.json`, `fixed_shift.json`, `fixed_shift_control_minus05.json`, `verify/`.

## Per-episode summary (main source: the final reference where one exists, else perception)
Columns:
- `d ...`: AUC change from each oracle correction;
- `fixed +0.5`: the deployable constant time advance;
- `snap`: mkref's per-object z snap (pre AUC minus perception AUC).

| ep | objects | src | s | lag fr | kit up deg | max rest tilt deg | worst rest centre-height err mm | AUC | d time | d height | d tilt | d all | fixed +0.5 | snap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | pot+lid | perc | 1.010 | +0.26 | 2.3 | 3.9 lid | -6 lid | 0.9641 | +0.002 | +0.027 | -0.001 | +0.017 | +0.003 | - |
| 2 | pot+lid | ref | 1.014 | +0.59 | 2.2 | 2.8 lid | -7 lid | 0.9798 | +0.004 | +0.009 | +0.007 | +0.013 | +0.004 | -0.012 |
| 11 | bcup+gcup | ref | 1.004 | +0.49 | 0.9 | 7.6 gcup | +16 bcup (tracked 24 mm up after the stack) | 0.8844 | +0.012 | +0.060 | -0.001 | +0.071 | +0.013 | -0.011 |
| 12 | bcup+rack | ref | 0.994 | +0.45 | 3.1 | 3.5 rack | +10 rack (snapped) | 0.9354 | +0.010 | +0.048 | -0.048 | +0.062 | +0.010 | -0.031 |
| 13 | bcup+rack | perc | 1.004 | +0.60 | 2.9 | 20.8 bcup (in rack) | -10 bcup | 0.9605 | +0.003 | +0.000 | -0.028 | -0.029 | +0.004 | - |
| 18 | swp+pan | ref | 1.010 | +0.64 | 2.4 | 3.6 swp | -3 swp | 0.9657 | +0.003 | +0.003 | +0.023 | +0.026 | +0.003 | +0.007 (same mesh) |
| 21 | bcup+pitch | ref | 1.022 | +0.56 | 6.0 | 5.7 pitch | -9 bcup; pitcher -cup +14 | 0.7776 | +0.003 | +0.081 | +0.110 | +0.174 | +0.004 | -0.056 |
| 22 | bcup+pitch | perc | 1.018 | +0.56 | 6.2 | 6.1 pitch | -12 bcup | 0.8710 | -0.001 | +0.044 | +0.095 | +0.108 | -0.001 | - |
| 23 | b1+b2 | perc | (0.68) | - | (177) | swapped | swapped | 0.0414 | identity swap: numbers meaningless | | | | | - |
| 24 | b1+b2 | ref | 1.011 | +0.56 | 1.6 | 3.2 b2 | +33 b1 final rest | 0.8163 | -0.003 | +0.002 | -0.010 | -0.003 | -0.003 | +0.005 |
| 26 | rack+pot | ref | 0.977 | +0.47 | 2.4 | 4.9 pot | -29 pot (in rack) | 0.9229 | +0.002 | +0.035 | -0.003 | +0.035 | +0.002 | -0.062 |
| 27 | rack+pot | ref | 1.006 | -0.43 | 3.7 | 3.1 pot | +8 rack (snapped) | 0.9621 | -0.001 | -0.022 | +0.027 | +0.025 | +0.002 | +0.003 |
| 31 | swp+rack | ref | 0.987 | +0.53 | 4.6 | 4.1 swp | -9 swp | 0.8233 | +0.021 | +0.006 | +0.038 | +0.058 | +0.021 | -0.005 |
| 39 | pan | ref | 1.005 | +0.33 | 1.0 | 2.2 pan | -1 pan | 0.9559 | +0.010 | +0.000 | +0.019 | +0.024 | +0.014 | 0 |
| 40 | pan | perc | 0.996 | +0.42 | 2.1 | 2.7 pan | -3 pan | 0.9570 | +0.000 | -0.000 | +0.026 | +0.027 | +0.001 | - |
| 41 | pot | perc | 0.977 | +0.35 | 2.0 | 3.1 pot | +4 pot | 0.9910 | +0.002 | +0.002 | -0.000 | +0.003 | +0.002 | - |
| 42 | pot | perc | 0.992 | +0.40 | 1.1 | 2.2 pot | +5 pot | 0.9915 | +0.008 | -0.004 | -0.002 | -0.001 | +0.008 | - |
| 43 | pot | perc | 0.987 | +0.48 | 4.1 | 4.7 pot | -8 pot | 0.9482 | -0.000 | +0.016 | +0.016 | +0.046 | -0.000 | - |
| 44 | pot | perc | 0.999 | +0.51 | 1.7 | 2.3 pot | +3 pot | 0.9967 | +0.001 | +0.002 | +0.001 | +0.003 | +0.001 | - |
| 45 | pot | perc | 0.971 | +0.50 | 2.5 | 3.7 pot | +6 pot | 0.9795 | +0.003 | +0.001 | -0.011 | -0.010 | +0.003 | - |

Full tables (both sources, all objects, pre/post segments, lowest points, kit-aligned vertical errors): `tables.md`.

## Findings in more detail
- **Scale vs the hand-scale question.** The depth-bias hypothesis (from the work log, 'Hand scale check': fit scale at its 0.85 clamp, wrist to middle tip 12 cm vs about 18.5 cm) predicts s of about 0.65 to 0.85 for objects in the same stereo depth. Measured: s of about 1.00 (worst 0.971).
  - So **H-depth-bias is falsified** for the 0.45 to 0.6 m object range.
  - The small hand therefore comes from the hand pipeline (MediaPipe landmark scale or the fit), not from depth. Note it for the hand-side work.
  - Our meshes do differ in size from the scans: radius ratio blue cup 0.876, pot 1.037, pitcher 0.970, board 1 0.968. Those are shape errors; the kit rescales shape before registration but does not correct the pose.
- **Time.**
  - The pooled within-episode lag slope is -0.11 +- 0.03 frames per 100 frames. If mocap rows sat on the parquet's uniform `timestamp` grid (20.254 Hz) while video frames sit on `capture_time` (20.0 Hz), the slope would be +1.27. So **H-drift is falsified**.
  - A constant 0.5-frame offset remains. It is a real time shift, not smoothing: +0.5 helps and -0.5 hurts with the same interpolation.
  - ep27 is the one episode with a negative lag (-0.43, pot).
- **Rest heights, recurring errors (centre height relative to the table).**
  - Lid on pot: centre -6 to -7 mm (ep0, ep2); the lid's lowest point is 7 to 9 mm too deep, so the lid sinks into our pot.
  - Blue cup: -8 to -12 mm in every episode (ep11, 12, 13, 21, 22). Our cup mesh is 12 % small, so its anchor sits lower when it rests on the table.
  - Snapped racks: +8 to +10 mm (ep12, ep27). The snap puts our rack's lowest vertex on the table, which lifts the centre too high. Perception had the racks 7 to 13 mm into the table instead.
  - Sweeper: -9 mm (ep31; library_v2 in perception ep18 too). The flattened v3 sweeper in the ep18 reference: -3 mm.
  - ep11: our blue cup is tracked 24 to 41 mm UP while the beige cup is stacked into it, and stays 24 mm high (mocap: it does not move). This is perception (same in `perc`).
  - ep26 pot: perception has the pot 14 mm too deep in the rack. The snap then lowers it another 15.4 mm towards the table (`object_z_shift` -0.0154 in `table_frame.npz`), although the pot rests 21 mm above the table, in the rack.
- **The snap rule** makes the lowest point of OUR mesh touch the table. The kit scores the registered anchor, so every bottom-shape error of our mesh, and every object that rests on another object, moves the scored centre. Perception, which is fitted to the observed surface, places the anchor better on average (`snap` column).
- **Contact retarget with rest settle** (ref minus pre): mean +0.003. ep31 +0.028, ep26 +0.012, ep2 +0.005; ep18 -0.005, ep39 -0.004, ep21 -0.004.
- **Anchor sensitivity.** On ep18, the same perception poses scored with library_v2 and with library_v3 (only the sweeper differs) give 0.938 and 0.964. The dust pan's AUC changes by +0.05 because the sweeper is the kit's alignment anchor.
- **The single corrections interact.** On ep12, removing the rack's tilt reduces the scene tilt from 3.2 to 1.2 deg but uncovers the +19 mm relative height error (snapped rack, small cup) that the tilt had partly hidden, so tilt alone is -0.048 while all corrections together give +0.062. Read `all` for the total cost.

## Hypotheses (not tested here) and the experiments that would falsify them
- **H-lag-tracker vs H-lag-sync.** Either FoundationPose tracking (initialised from the previous frame) lags motion by about half a frame, or the ego video and mocap have a fixed 20 to 25 ms sync offset.
  - Falsifier: track the time-reversed video of 3 public episodes. Tracker latency flips sign in forward time; a sync offset does not.
  - Either way the +0.5-frame advance is inference-legal: it is one constant chosen on public data. It gives +0.005 to +0.007 on reference and perception. Not yet tested through training and rollouts: retrain one public twin on the advanced reference and compare sim AUC.
- **H-snap.** Gating the per-object snap would recover most of the snap's -0.016 mean without making the simulator start worse. The gate would exclude objects whose bottom lies above another object (pot in rack, lid on pot) and keep the perceived height of objects within a few mm of the table.
  - Falsifier: rebuild the object path of the 10 public references with the gate and score it. The object path is cheap on CPU and E2S is not needed for it. Then run one sim start check (CPU `tools/sim_settle.py`) for ep21 and ep26. H-snap is false if the AUC does not rise or the start becomes unstable.
- **H-anchor.** The scene-tilt cost (up to 6 deg, +0.10 on ep21/22) comes mainly from the anchor object's frame-0 orientation.
  - Ways to reduce it: averaging that orientation over the initial rest frames, or choosing the anchor's stable resting pose on our table plane nearest to the perceived one. Better anchor meshes reduce it too; the lathe pitcher, per STATUS.md (from doc), improved twin ep21 from 0.776 to 0.874.
  - Falsifier: apply the stable-pose snap to frame-0 anchor orientations of the 20 perception tracks and score. H-anchor is false if the mean AUC does not improve.

## Caveats
- The corrections are oracles (they use mocap). They bound the cost of each systematic; only the constant time shift is deployable as is.
- ep23: frame-0 identity swap of the two boards (perception AUC 0.041). Its scale, lag and tilt values are meaningless and are excluded from all medians.
- 'Lowest point' uses our visual mesh, which is also the simulator mesh from `make_assets.py`. Runs that use carved collision pieces collide differently.
- The mocap table height is estimated from the lowest resting object (0.598 to 0.602 m), not measured directly.
- A rest-height or tilt value covers only the frames the 5 mm / 3 deg rule calls rest. Mid-episode holds (e.g. ep24 board 1 standing, frames 96 to 211) are not rest by this rule.
- Box-recorded numbers quoted for context come from docs (STATUS.md, the work log, canonical_refs.json recipe notes); everything else is measured here.
