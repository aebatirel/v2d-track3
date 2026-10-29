# refcheck/chain: where our object path loses accuracy against public mocap (26 Oct 2026)

Answers part of the owner's question "can't we first make sure our calculation of the reference is correct with
public data?". It scores every link of the chain perception -> mkref -> contact retarget -> evaluator reference (and
rollout r1) against the public mocap, twice: with our submitted meshes and with the public scans. It also re-scores
the 20-episode perception sweep and the 8-episode track-guard arm with the submitted meshes.

Everything here was run on CPU in this session: no GPU, no Vast, no Kaggle. All 188 scorer and diagnostic calls
returned 0 (`commands.log`). Ground truth was read only by scoring and diagnostics.

**[M]** marks a number measured here; the command is in `commands.log`, and the scripts are listed under Files.
**[doc]** marks a number taken from a doc or a box record. **[H]** marks a hypothesis.

## Method

- **Scorer.** `pipeline/score_registered.py` is the kit's registered Track 3 scoring. The public scan stands in for
  the hidden one; the anchor is the scan's surface centroid, scored with 1000 points.
  - **lib**: `--meshes meshes/library_v3`, the submitted meshes. ep11 uses `library_v3x`, because its run tracked
    the v5 beige cup.
  - **scan**: no `--meshes`. The poses are taken as poses of the scan frame.
  - Check: the results-dir score reproduces the box's `score_registered_ep2.json` exactly (sim 0.4513, reference
    0.9798) **[M]**.
- **Chain, per canonical episode with a reference** (2, 11, 12, 18, 21, 24, 26, 27, 31, 39;
  `../resolve/canonical_refs.json`). Each link is scored in both modes:
  - perc: the perception `poses_world_vo.npz` that fed the reference;
  - e2s: `e2s_reference.parquet`, mkref's output before contact retarget;
  - ref: the final reference;
  - sim: rollout r1 of the results dir. Its reference columns give ref.
- **Converting parquets.** `ref2npz.py` converts a reference parquet's `object_body_position` / `object_body_wxyz`
  (table frame, tracking-mesh body frame) into an npz in the poses_world_vo layout.
  - The converted final parquet scores identically to the evaluator's reference columns in all 10 episodes
    (0 conversion mismatches) **[M]**.
  - The table frame is one rigid transform of the perception world. The kit's frame-0 scene alignment removes that
    transform.
  - The alignment does **not** remove per-object shifts. It takes the scene **translation from object slot 0's
    frame-0 position** and the **rotation from the first object without a symmetry axis**
    (`v2dlb/track3_pose.py::_align_registered_scene`).
- **Re-scoring.** Sweep base (20 episodes) and the guard arm (8) are scored lib and scan. The stale 20 Oct refsweep
  pairs (perception templated on the public scans) are scored with the scans only.
- **Frame-level diagnosis (`diag.py`).** It reproduces the scorer exactly and splits an AUC difference between two
  paths by frame. The per-frame share of the ADD AUC is the trapezoid over the 1-9 cm thresholds, so
  AUC = the mean of the per-frame shares. For each case it reports:
  - frame 0 against later frames, and segments;
  - a translation-only / rotation-only split (hybrids);
  - the vertical error against mocap.
  It was run on every flagged link (`diag/*.json`).
- **Registration split by object (`hyb_jobs.py`).** One object is scored with our mesh and the other with its scan.
- **Frame-0 bottoms (`bottoms.py`, `snapcheck.py`).** These compare the object bottoms at frame 0 (mocap scan, our
  mesh) with mkref's measured heights above its fitted table.

## Commands (CPU; `SP=/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck`)

```
python -I run_jobs.py --workers 2      # 146 scoring jobs -> $SP/work/chain/{scores,pf,npz}
python -I diag_jobs.py                 # 22 frame-level diagnoses -> $SP/work/chain/diag
python -I hyb_jobs.py                  # 16 mixed-mesh scorings
python -I diag.py 43|22|0 ...          # 3 extra registration diagnoses (sweep ep43/ep22, guard ep0; commands.log)
python -I bottoms.py $SP/t3 $SP/kit/v2d_submission_kit meshes/library_v3 bottoms_v3.json
python -I snapcheck.py $SP/t3 $SP/kit/v2d_submission_kit $SP/store $SP/work/canonical_refs.json snapcheck.json
python -I compile.py $SP/work/chain/scores OUTDIR        # -> results.json, tables.md (all tables)
```

Each call takes 7-161 s on one core. 1.5 CPU-h in total (measured, `commands.log`; the 3 extra diag calls have no timing); $0.

## Results

### 1. Chain: perception -> mkref -> contact retarget -> reference (scene AUC; per object in `tables.md`) [M]

| ep | perc lib | e2s lib | ref lib | ref - perc lib | perc scan | ref scan | sim r1 lib |
|---|---|---|---|---|---|---|---|
| 2 | 0.987 | 0.975 | 0.980 | -0.007 | 0.989 | 0.984 | 0.451 |
| 11 | 0.896 | 0.885 | 0.884 | **-0.012** | 0.916 | 0.921 | 0.567 |
| 12 | 0.966 | 0.935 | 0.935 | **-0.031** | 0.964 | 0.993 | 0.921 |
| 18 | 0.964 | 0.971 | 0.966 | +0.002 | 0.971 | 0.970 | 0.960 |
| 21 | 0.837 | 0.781 | 0.778 | **-0.060** | 0.958 | 0.908 | 0.790 |
| 24 | 0.812 | 0.816 | 0.816 | +0.005 | 0.790 | 0.796 | 0.308 |
| 26 | 0.972 | 0.911 | 0.923 | **-0.049** | 0.955 | 0.931 | 0.537 |
| 27 | 0.959 | 0.962 | 0.962 | +0.003 | 0.939 | 0.943 | 0.954 |
| 31 | 0.800 | 0.795 | 0.823 | +0.024 | 0.885 | 0.924 | 0.770 |
| 39 | 0.960 | 0.960 | 0.956 | -0.004 | 0.977 | 0.980 | 0.958 |
| **mean** | **0.915** | **0.899** | **0.902** | **-0.013** | 0.934 | 0.935 | 0.722 |

**mkref changes the object path in one way only: a constant vertical shift of each object** (the per-object table
snap, plus overlap lifts).
- In all 7 diagnosed episodes the change is a pure translation, identical in every frame, with 0.00° of rotation **[M]**.
- After the frame-0 alignment, only the shift *relative to object slot 0* matters. Single-object episodes are
  therefore immune.
- Over 19 object-episodes, lib **[M]**:
  - mkref: −0.017 mean, −0.123 to +0.013;
  - contact retarget (rest settle): +0.004 mean, −0.007 to +0.056.

Support fill / grasp lock leave the path unchanged: the evaluator's reference columns equal the parquet
(`../resolve`).

Frame-level causes of the flagged links (`diag/mkref_*`, `diag/cr_*`, `snapcheck.json`, `bottoms_v3.json`):

| ep / object | link: relative shift | lib dAUC | scan dAUC | cause |
|---|---|---|---|---|
| 26 pot | mkref: pot −2.59 cm vs rack, all frames | **−0.123** | −0.047 | **Snap-rule error.** The pot rests in the rack: the mocap scan bottom is 2.04 cm above the table. mkref measured it 1.54 cm above its plane (≤ the 2 cm `snap_max`) and pushed it onto the table, while lifting the rack 1.05 cm. Vertical error (scan frame) went +0.83 → −1.76 cm. Rest settle then recovers +0.031 (f96-157). This matches the "pot 29 mm too deep in the rack" seen in forensics. |
| 21 pitcher | mkref: pitcher +0.93 cm vs cup, f0-185 | **−0.112** | **−0.095** | **Snap made it worse in both frames.** Perception already had the pitcher 1.06 cm too high (scan frame); after the snap it is 1.99 cm too high. At frame 0, mkref's plane sits 1.3 cm above the mocap table under the pitcher but 0.2 cm below it under the cup (plane offset or tilt). This figure includes the pitcher's frame-0 orientation, which sets the scene rotation. |
| 12 rack | mkref: rack +1.0 cm vs cup, f0-180 | **−0.061** | +0.059 | **Snap is physically right; the lib loss comes from the cup's registration.** Scan frame: perception had the rack 0.97 cm too low, and the snap took it to +0.03 cm. With our meshes, the blue cup (slot 0) registers 0.89 cm off along its axis, which shifts the whole scene; that shift had cancelled the rack's perception error. |
| 11 beige cup | mkref: +0.31 cm vs blue cup, mainly f41-80 | −0.023 | +0.012 | Same pattern: scan-frame vertical error −0.30 → +0.02 cm; lib is hurt by the cups' registration offsets. |
| 2 lid | mkref: pot +0.16 cm (lid not snapped) | −0.024 | +0.008 | **Threshold effect.** The lid's ADD sits at ≈ 1.0 cm, so 1.6 mm moves 128 frames across the 1 cm threshold. Rest settle then gives +0.017. |
| 31 rack | contact retarget: rack −0.81 cm, ≈ 1.7° | **+0.057** | +0.088 | Rest settle improves the rack (f17-80, f186-252). |
| 18 pan | contact retarget: ≤ 13° turns in f69-105 | −0.007 | −0.012 | Rest-settle tilt onto a stable pose while the pan is moving. Small. |

### 2. What our submitted meshes cost at registration (lib − scan, same path) [M]

Sweep base, 33 object-episodes: mean −0.016, median 0.000. The losses are concentrated:

| object (episodes) | lib − scan | mechanism (diag / hybrid split) |
|---|---|---|
| pitcher (21, 22) | **−0.230, −0.215** | Two parts, about half each (ep21 perception: scan 0.919; only the cup ours 0.810; only the pitcher ours 0.798; both 0.692): (a) the blue cup is slot 0 and registers about 1 cm off along its axis, which shifts the whole scene; (b) the pitcher's own registration is off by 2.65–3.19° and 0.65 cm. The error is present from frame 0 (dz +1.4–1.6 cm). |
| rack (31) | **−0.144** (ref −0.165) | The sweeper is slot 0 and also the rotation anchor; its 3.0° registration rotation turns the whole scene. Only the sweeper ours: rack −0.064; only the rack ours: −0.008. All 290 frames. |
| beige cup v3 / v5 (11) | −0.059 / −0.042 (ref −0.074) | The beige cup's own registration (axis tilt about 4°, anchor +1.3 cm) plus the blue cup's slot-0 offset. |
| blue cup (12) | −0.053 | Its own 0.9 cm axial offset grows to about 2 cm once the cup is turned over (f78-180). |
| blue cup (21, 22) | −0.014, −0.007 | Small. |
| lid (0, guard arm) | −0.060 | The lid registers 0.7 cm lower relative to the pot (offsets in opposite directions); its ADD goes 0.68 → 1.33 cm in all frames. |
| sweeper (31) | −0.038 | Its own 3.0° registration. |
| pot (43) | −0.033 | Single object, 1.9° registration; the error grows while the pot is turned (f105-325). |
| pot (26, 27), boards (24), cup + rack (13) | **+0.02 to +0.07** | Lib beats scan: our meshes' registration offset cancels a perception offset that the tracker took on from our mesh's shape. **The scan score is therefore not an upper bound for paths tracked with our meshes.** |

Mesh-level evidence, frame 0, kit-registered placement (`bottoms_v3.json`, surface moments) **[M]**:
- **Blue cup:** our bottom sits 0.74–0.89 cm above the scan's in every episode. Surface RMS radius: 6.08 cm (ours)
  vs 6.94 cm (scan).
- **Water pitcher:** our surface centroid is 2.0 cm higher and 1.4 cm sideways from the scan's.

### 3. Per-object accuracy table for the hidden-loss model (mean over public episodes) [M]

| object | review midpoint [doc] | newest perception, lib (n) | newest perception, scan | canonical reference, lib (n) | reference, scan |
|---|---|---|---|---|---|
| pot | 0.97 | 0.972 (9) | 0.967 | **0.922** (3) | 0.915 |
| lid | 0.965 | 0.954 (2) | 0.980 | 0.974 (1) | 0.980 |
| blue cup | 0.95 | 0.940 (5) | 0.942 | 0.925 (3) | 0.948 |
| beige cup | 0.93 | 0.933 (1) | 0.992 | 0.905 (1) | 0.980 |
| rack | 0.95 | 0.934 (5) | 0.940 | 0.916 (4) | 0.972 |
| sweeper | 0.96 | 0.954 (2) | 0.973 | 0.952 (2) | 0.971 |
| dust pan | 0.95 | 0.950 (3) | 0.967 | 0.948 (2) | 0.964 |
| pitcher | 0.66 | 0.717 (2) | 0.939 | **0.575** (1) | 0.823 |
| boards | 0.82 | 0.427 (4); 0.812 without the ep23 swap | 0.416 / 0.790 | 0.816 (2) | 0.796 |

- **Newest perception** is the guard arm for 0, 11, 12, 18, 21, 23, 24 and 31, and the sweep base elsewhere. With
  library_v3 the sweep scores match the box-stored library_v2 scores, except in the sweeper episodes:
  - ep18 dust pan 0.881 → 0.933: only the sweeper changed (it is slot 0);
  - ep31 0.805 → 0.800.
- **The hidden-loss model should use the reference column, not perception.** The policy tracks the reference.
  - The midpoints are close for most objects.
  - They are optimistic for the pot (0.922 because of the ep26 snap) and the rack (0.916).
  - The pitcher's reference is 0.575 vs the 0.66 midpoint, though n = 1.
- **Multiplicative check on the public twins (rollout r1).** Measured sim vs mocap (lib) averages 0.722; the model
  `sim_vs_ref [doc, box r1] × ref lib` predicts 0.682.
  - The model is pessimistic by 0.04 on average and by 0.15 in ep11 and ep31.
  - In ep2, 11 and 26 the static floor beats the rollout.

### 4. Stale refsweep (20 Oct, perception templated on the public scans, scored with the scans) [M]

- Perception scores 0.966–1.000 in 9 of 10 episodes. ep0 fails at frame 0: 0.184.
- mkref changes the path by at most 0.007 (ep22 pitcher), with snaps of at most 0.8 cm.
- Today's own-mesh perception on the same episodes, scored with our meshes (sweep base):
  - ep13 0.961, ep22 0.871, ep40 0.957, ep43 0.948;
  - for comparison, the stale scan-templated runs score 0.998, 0.994, 0.997 and 0.993.
- Read with care: the code versions differ, and scan templates are an oracle that eval episodes do not have.
  Still, with an exact template the tracker reaches about 0.99. Most of the remaining gap is the template mesh and
  its registration, not the tracker.

## Problems found

1. **mkref's per-object snap moves objects that are not on the table.** On ep26 the pot is in the rack; it moved
   −2.59 cm relative, costing −0.123 on the pot. The rule only checks `|h| ≤ 2 cm`.
2. **The snap amplifies table-plane error.** ep21: pitcher +0.93 cm, −0.112 lib / −0.095 scan. It is the largest
   reference-side loss together with item 1.
3. **"Hand-side stages do not change the object path" is false for contact retarget with rest settle.** Measured
   effect: +0.004 mean, from −0.007 to +0.057.
4. **The registration error of slot 0 propagates to every object in the scene** through the kit's alignment. It
   explains:
   - the pitcher's −0.11 of −0.23;
   - the ep31 rack's −0.064;
   - the ep12 rack's sign flips;
   - the ep18 pan's +0.052 between v2 and v3.
5. **Our pitcher, cups, sweeper and lid meshes cost real AUC at registration** (table 2). The pitcher's low
   accuracy is mostly registration, not tracking (scan 0.91–0.96).
6. **Box-recorded perception AUCs in the canonical notes do not reproduce with library_v3.**
   - ep21 0.924 vs 0.837 **[M]**, ep31 0.881 vs 0.800, ep39 0.982 vs 0.960, ep2 0.994 vs 0.987.
   - They sit closer to the scan-scored values (0.958, 0.885, 0.977, 0.989). They are probably an older or
     scan-based score.

## Hypotheses (new, untested) and the experiment that would falsify each

- **H1 [H].** The blue cup's ≈ 0.9 cm axial registration offset comes from the kit's scale normalisation (RMS
  radius 6.08 vs 6.94 cm), because our closed reconstruction lacks the open cup's inner wall.
  - Test: score ep12 / ep21 perception with an open-shell blue cup (inner wall added).
  - Falsified if `anchor_shift_cm` stays ≥ 0.6 or the blue cup's lib AUC does not move toward scan (0.988 / 0.996).
- **H2 [H].** Restricting the snap to objects resting on the table recovers the ep26 pot: for example, skip an
  object whose frame-0 footprint lies over another object, or one whose bottom is more than 0.5 cm above the lowest
  object's.
  - Test: rebuild ep26 e2s (CPU, mkref only) and re-score.
  - Falsified if the pot's e2s lib AUC stays < 0.93 (perception 0.947).
- **H3 [H].** ep21's pitcher lift is a table-fit error: the plane under the pitcher is ≈ 1.5 cm off relative to
  the plane under the cup, rather than a perception error.
  - Test (GT-free): fit planes on frame-0 depth in rings around each object separately and compare them under the
    pitcher and under the cup.
  - Falsified if they agree to < 0.3 cm. Then the frame-0 pitcher orientation (the scene rotation anchor) is the
    cause.

## Caveats

- **Hidden scans are assumed equal to the public scans.** The anchor (surface centroid) and the point count are
  the scorer's guesses.
- **Sim numbers are rollout r1 only.** sim_vs_ref comes from the box summaries.
- **The 10 canonical references were built with different recipes and dates.** Only ep11 and ep21 use the current
  recipe (`../resolve`). Ten episodes have no own-mesh reference.
- **The hybrid translation/rotation splits are not additive.** The ADD thresholds are nonlinear.
- **`snapcheck`'s plane error includes the alignment's rotation-anchor error.**
- **Raw quaternion differences of cups include free spin about the axis.** For example, the "130°" in reg ep11 is
  spin only.

## Files

- **Scripts:**
  - `run_jobs.py`, `diag_jobs.py`, `hyb_jobs.py`: job lists;
  - `ref2npz.py`: parquet → npz;
  - `diag.py`: frame attribution;
  - `bottoms.py`, `snapcheck.py`: frame-0 bottoms and snap check;
  - `compile.py`: tables;
  - `show_diag.py`: prints a diag JSON.
- **Outputs:**
  - `tables.md`: all tables, including the per-object chain, the sweep / guard table, the hybrid split, the diag
    table and every flag;
  - `results.json`;
  - `diag/*.json`, `snapcheck.json`, `bottoms_v3.json`;
  - `commands.log`: every command, return code and seconds.
- **Bulky scratch, not in git:** `$SP/work/chain/{scores,pf,npz,diag/*.npz,logs}`. It holds the per-frame
  position / ADD arrays from `--per_frame` and diag.
