# T1 S6 static hold: public reference part (20 episodes) and S6 on eval 10 (31 Oct 2026, ~05:15 UTC)

Rule and thresholds: `../PLAN.md` §3 T1, frozen before the run and unchanged here. Labels: [M] measured, [E] estimate,
[H] hypothesis. CPU only on this VM, $0, no GPU, no Vast, no Kaggle, nothing committed by this step. Inference
(`pipeline/refine.py`) read no ground truth. Mocap was read only by `scripts/t1_score.py` and `scripts/t1_order_diag.py`,
on public episodes, after refine had written its outputs. Eval 10 has no ground truth, and no eval reference was changed.

## 0. Owner summary
1. **T1 reference part: the pre-registered rule fails on the P_o arm by 0.0003 [M].**
   - S6 freezes exactly the mocap-static objects on 20/20 episodes, in both arms.
   - The 25 Oct tracks (`refine/in`) pass: worst episode −0.0008 lib.
   - The Phase-1 P_o tracks fail: ep27 −0.0023 \* and −0.00203 lib, against the bar of −0.002.
   - Mean gain over the 20 episodes is +0.004 (lib and \*) in both arms. Almost all of it is ep11 (+0.068 lib, +0.071 \*).
2. **Why ep27 loses (post hoc) [M]:** the frozen rack is the kit's rotation anchor.
   - With S6 placed before S2 (the planned order), the rack keeps its raw frame-0 pose. Without S6 it takes S2's half-frame
     advanced pose.
   - The 0.09 cm / 0.18° difference moves the kit's frame-0 alignment of the whole scene.
   - Running S6 after S2 instead removes the ep27 loss but makes ep31 fail (−0.0022 lib). Neither order passes both arms.
   - The −0.002 margin is at the size of half-frame anchor jitter. This is a reading of the numbers, not a new rule.
3. **Eval 10: S6 freezes nothing [M].** Both cups move more than 2 cm sideways in our track.
   - The blue cup steps 4.4–4.9 cm sideways at f38–46, while the left hand grips it, and stays 4.1 cm away to the end.
   - A GT-free camera check confirms the move is the cup's own, not a VO error. The check passes its public controls (ep24
     camera step found; ep11 camera clean). On eval 10 the camera correction is ≤ 0.24 cm.
   - The overlay agrees: from f42 on, the frame-0 hold sits next to the cup, on the hand and table.
   - An independent depth-ICP background check in the parallel eval screen (`../screen/e10_vo_bg.txt`) agrees.
4. **Consequence [E]:** S6 as pre-registered gives about 0 on eval 10. The +0.007 LB (central) that ranked it first in
   `../PLAN.md` §4 does not exist for S6.
   - Do not spend on the T1 rollout ($2.6–5.2) or the eval-10 retrain ($2.6) for S6. **The owner decides.**
   - Eval 10's blue cup now belongs to the "container moves" group. The fix that still covers it is the masking
     re-track, T2 (`../PLAN.md` §2 M1 row 2, §4 item 4).
5. Eval 10's track still shows ep11's vertical pattern [M on the track, H that it is a tracker error]:
   - +3.1 to +3.7 cm while the beige cup is nested and the hands are on it (f100–117);
   - +1.8 to +2.1 cm held to f160.
   - S6 cannot remove it, because the cup moved sideways.

## 1. Code (committed in e50ec1e, reviewed here, unchanged)
- `pipeline/refine.py` S6, sha256 `8c54ec70…`. The same bytes ran every public and eval run below; each `pose_opt.json`
  records the hash.
- **Rule** (`../PLAN.md` §2 M1): an object freezes when the horizontal travel of its vertex centroid stays under 2 cm over
  the episode, measured in the world frame along our table plane.
  - Objects that are not axisymmetric must also rotate less than 10° from frame 0.
  - The cups skip the rotation test (`--s6_axisym`, default `blue_cup,beige_cup`, the only axisymmetric objects in the
    rosters).
  - A frozen object takes its frame-0 pose on every frame.
- **Plane:** `det_rules.table_plane` on our frame-0 depth, at half resolution with K/2, as perc2's TRACK_GUARD does.
  Without depth or K it falls back to refine's plane; with no plane at all it skips S6.
- **Opt-in:** S6 runs only when `--steps` names it; it is not in `DEFAULT_STEPS`.
- **Order:** `STEP_ORDER` is S0, S6, S1, S3, S4, S5, S2, so the adopted chain is S0, S6, S2. The planned S7 (before S6) and
  S9, S8 (after it) are not built.
- `pose_opt.json` records per object:
  - horizontal travel, vertical peak (value and frame), end height, rotation, the reason;
  - for a frozen object, where the other objects are at its peak.
- **Unit test** `tests/test_refine_s6.py`: 3/3 pass (`python tests/test_refine_s6.py`; pytest is not installed in the
  venv). It covers:
  - the rule (ep11-like lift frozen; an object moved 2.05 cm, one tilted 12° and one turned 25° kept);
  - that a wrong (camera-frame) normal changes the decision, and the no-plane skip;
  - end to end on a synthetic directory with a moving camera: the frozen object holds its frame-0 world pose, the other
    is untouched, and every input passes `assert_inference_input`.
- **Review notes [M]:**
  - The rule uses the maximum over all frames, so one tracker glitch over 2 cm blocks a freeze. That errs on the safe side.
  - `white_pot_lid` has a half-turn symmetry in the kit but keeps the rotation test. That is also on the safe side.
  - The thresholds were chosen after seeing these 20 episodes (`../ep11/DIAG.md`). No fresh holdout exists.

## 2. T1 reference part (public, 20 episodes)
**Commands** (this VM; `S` = the session scratchpad; scripts in `scripts/`):
1. `bash scripts/t1_run.sh`: inference, 80 refine runs, about 1–2 min. The commands are in `public/jobs.txt` and the hashes in
   `public/refine_sha256.txt`.
   - Code: the bytes later committed as e50ec1e. At run time the tree was HEAD 53be655 with `pipeline/refine.py`
     modified.
2. `$S/map/scoring/venv/bin/python -I scripts/t1_score.py public/t1_scores.json`: oracle scoring, 8 min 15 s. Log:
   `public/t1_score.log`.
3. `… -I scripts/t1_order_diag.py public/t1_order_diag.json`: post-hoc mechanism check; adopts nothing.

**Inputs:**
- `refineP`: the 25 Oct tracks in `$S/refine/in/ep<N>` (poses, hands, frame-0 depth), as in the refine study.
- `Po`: the Phase-1 P_o tracks (`runs/20261030-orcP1{a,b,c}-87fc869/results/leak_p1/ep<N>/perc2`), with refine/in's frame-0
  depth and hands.
- The two arms are near-replicates [M]. Object translations agree within 0.43 cm on 18/20 episodes (0 on 7). ep18 and
  ep23 differ by 15–17 cm (re-acquisition and identity events). On ep11 they are identical.
- The S6 plane source was `det_rules.table_plane` on the frame-0 depth in all 40 S6 runs.
- **Not run:** the P_s (scan-template) arm that `../PLAN.md` §3 also names. This task scoped T1 to refine/in and P_o. P_s
  is not eval-like, and for it S6 would need the scan meshes for the centroid.

**Scoring:**
- `tools/xstar_fit.py` `score_track`, the kit chain, ADD-AUC.
- \* = X\*_geom; lib = X_kit of library_v3.
- Mocap-static: the kit anchor point travels less than 1 cm over the episode (as in `../ep11/DIAG.md`).

**Verdict per arm [M]** (rule: frozen set = mocap-static set on 20/20, and no episode Δ < −0.002 in lib or \*):

| arm | frozen = static | worst Δ lib | worst Δ \* | mean Δ lib / \* | better / worse (lib; \*) | mean S2 → S6,S2 lib | rule |
|---|---|---|---|---|---|---|---|
| refineP | 20/20 | −0.0008 (ep27) | −0.0002 (ep27) | +0.0039 / +0.0042 | 4/2; 5/1 | 0.8982 → 0.9021 | **pass** |
| Po | 20/20 | −0.00203 (ep27) | **−0.0023 (ep27)** | +0.0043 / +0.0042 | 4/2; 4/2 | 0.8944 → 0.8987 | **fail** |

**Episodes with a frozen object [M].** In the other 14 episodes nothing is frozen, no object is mocap-static, and Δ = 0
exactly in both arms.

| ep | frozen = mocap-static | S6: horizontal / rotation (refineP; Po) | mocap travel | refineP Δ lib / \* | Po Δ lib / \* |
|---|---|---|---|---|---|
| 11 | blue_cup | 0.96 cm / 32.8° (cup, not tested); lift +5.39 cm at f67, +2.45 at the end | 0.49 cm | **+0.0676 / +0.0709** | **+0.0676 / +0.0709** |
| 12 | rack | 0.64; 0.67 cm / 3.3° | 0.41 cm | −0.0003 / +0.0073 | −0.0006 / +0.0073 |
| 13 | rack | 0.48; 0.52 cm / 1.8° | 0.09 cm | +0.0048 / +0.0003 | +0.0073 / −0.0010 |
| 26 | rack | 0.75 cm / 4.3° | 0.43 cm | +0.0053 / +0.0038 | +0.0069 / +0.0032 |
| 27 | rack | 0.42 cm / 1.8° | 0.28 cm | −0.0008 / −0.0002 | **−0.0020 / −0.0023** |
| 31 | rack | 0.65 cm / 3.7° | 0.15 cm | +0.0012 / +0.0026 | +0.0069 / +0.0057 |

**Margins [M]:**
- Frozen objects travel ≤ 0.96 cm horizontally in our tracks and turn ≤ 4.3° (racks).
- The smallest travel among kept objects is 4.32 cm (ep40 dust pan; then the ep44 pot 4.42, the ep45 pot 4.75). No object
  was kept for its rotation alone.
- Mocap: static objects ≤ 0.49 cm; the next smallest is 9.37 cm.
- So the decisions are far from both thresholds. The failing part of T1 is the no-harm margin, not the set.

**Post-hoc mechanism of the small losses** (`public/t1_order_diag.json`; adopts nothing) [M]:
- The kit pins the whole scene on frame 0. The rotation comes from the first object without a symmetry axis (the rack in
  ep12, 13, 26 and 27, the sweeper in ep31). The translation comes from slot 0.
- S6 runs before S2 (`../PLAN.md` §1 order), so a frozen anchor keeps the raw O(0), while the S2 arm's frame 0 is
  O(0.545).

| ep | arm | rotation anchor | anchor frame-0 shift S2 → S6,S2 | Δ lib: S6,S2 / S2-then-S6 | Δ \*: S6,S2 / S2-then-S6 |
|---|---|---|---|---|---|
| 27 | Po | rack (frozen) | 0.093 cm, 0.18° | −0.00203 / 0.0 | −0.00229 / 0.0 |
| 27 | refineP | rack (frozen) | 0.091 cm, 0.13° | −0.00076 / 0.0 | −0.00025 / 0.0 |
| 12 | Po | rack (frozen) | 0.035 cm, 0.24° | −0.00069 / 0.0 | +0.00725 / +0.00604 |
| 13 | Po | rack (frozen) | 0.117 cm, 0.26° | +0.00724 / +0.00691 | −0.00099 / 0.0 |
| 26 | Po | rack (frozen) | 0.117 cm, 0.48° | +0.00692 / +0.00158 | +0.00317 / +0.00158 |
| 31 | refineP | sweeper (not frozen) | 0 | +0.00129 / **−0.00216** | +0.00259 / +0.00259 |
| 31 | Po | sweeper (not frozen) | 0 | +0.00690 / +0.00539 | +0.00560 / +0.00560 |
| 11 | both | blue cup (slot 0, frozen) | 0.017 cm, 1.0° | +0.06752 / +0.06752 | +0.07094 / +0.06820 |

- In the "S2 then S6" order (freeze at the S2 output's frame 0), ep27 goes to 0. But ep31 refineP lib falls to −0.0022:
  the only change is which rack pose is held (O(0.545) instead of O(0)), and that 0.0034 swing alone crosses the bar.
- So no order passes every episode at −0.002 [M]. Choosing the order after this reading would tune on the test.
  Re-registering S6 needs the owner's call, and no fresh public holdout exists.

## 3. S6 on eval 10 (GT-free)
**Which track** [M]:
- The packed eval-10 policy is `20261026-gl10A2-5e0e100` (sha 76a12265…, pack 6/7/8).
- It trained on the evB reference (`20261024-evB-664e5fd` `refs/perc2mck/ep10`, built from its `perc2/ep10`; work log
  26 Oct ~11:10).
- The pack-6 copies have the same store sha256 as evB (one metadata call, no download):
  - `poses.npz` fb9103fa…
  - `det_f0.npz` 3f034015…
  - `hands_refined.npz` cdd52386…
  - `poses_world_vo.npz` 2f0d515a…
- The local files, already pulled by the eval screen, match these hashes.

**Command:** `bash scripts/t1_eval10.sh`, at HEAD 8f17f0a with `pipeline/refine.py` unchanged since e50ec1e.
- It runs `refine.py --steps S6,S2` with inputs `poses.npz`, `vo.json`, `hands_refined.npz` (KR) and `depth0.npy`.
- `depth0.npy` is perc2's own frame-0 depth: `det_f0.npz` 'depth' (half resolution) repeated 2×2. Refine's [::2, ::2] then
  sees exactly the TRACK_GUARD input.
- Cross-check: frame 0 of the 29 Oct recomputed eval depth.
- Outputs went only to `$S/leak/t1/eval10/`. Copies are in `eval10/`: `pose_opt_S6S2.json`,
  `pose_opt_S6S2_depth29oct.json`, `refine_S6S2.log`, `inputs_sha256.txt`.

**Frozen objects: none [M].**

| object | horizontal travel (max, frame; end) | vertical peak (frame); end | rotation | S6 |
|---|---|---|---|---|
| blue_cup | 4.91 cm (f52); 4.13 cm | +3.69 cm (f117); +1.78 cm | 34.2° (cup, not tested) | kept: horizontal ≥ 2 cm |
| beige_cup | 15.39 cm (f92) | +23.05 cm (f46); +2.90 cm | 36.4° | kept |

- With the 29 Oct depth: plane normal within 0.3°, blue 4.91 cm / +3.71 cm. Same decision [M].
- The eval screen's own S6 copy (`../screen/eval_screen.log`) gives the same numbers (4.91 / 3.69 / 34.2°).

**Blue cup, frame by frame** (our track; `../screen/e10_profile.txt`, `e10_hand_rerun.txt`) [M]:
- f0–35: still (≤ 0.16 cm). The left hand reaches it at f15–20 and holds it from about f20.
- f38–46: the cup steps 4.6 cm sideways. The left-hand centroid moves 4.0 cm in the same direction over the same frames,
  and its closest joint stays 4 cm from the cup centre.
- After f46: the step holds (4.1–4.6 cm to f160).
- The beige cup is lifted at f40, carried over and lowered in. It is nested from about f100, centre 1.4–2.7 cm above the
  blue cup's.
- The blue cup's height: −0.4 to +1.3 cm at f50–95; +3.1 to +3.7 cm at f100–117 (nesting, hands on); +1.6 to +2.1 cm from
  f130 (hands off).

**Is the 4.4 cm step a camera error? No [M].** `scripts/camcheck.py` (GT-free; our frames, our frame-0 depth, our
masks):
- It warps the frame-0 background into frame t and fits a 6-DoF camera correction.
- It then reports the cup's step after the correction. If the step is real, it survives; if the camera caused it, it
  vanishes.
- Controls were run first, on the public twins (mocap is used only to say what the controls should show).

| case | frame | tracked step h / v (cm) | the correction moves the object by | corrected step h / v | cost (0 → fit), NCC at 0 |
|---|---|---|---|---|---|
| ep24, positive control: board 2 is static (mocap), VO steps 2.4 cm at f33–51 | 30 | 0.08 / +0.08 | 0.26 cm | 0.24 / −0.13 | 0.877 → 0.867, 0.917 |
| | 60 | 1.33 / +1.53 | 1.15 cm | 1.66 / +0.57 (only the vertical part removed) | 1.553 → 1.471, 0.803 |
| | 100 | 1.32 / +1.96 | 2.40 cm | **0.08 / −0.06** (removed) | 1.400 → 1.003, 0.828 → 0.885 |
| ep11, negative control: blue cup is static (mocap); its lift is a tracker error | 30 | 0.19 / +0.03 | 0.13 cm | 0.14 / +0.13 | 0.669 → 0.640, 0.951 |
| | 67 | 0.50 / +5.39 | 0.26 cm | 0.51 / +5.50 (the lift stays) | 0.844 → 0.813, 0.927 |
| | 130 | 0.23 / +2.35 | 0.08 cm | 0.27 / +2.37 | 0.585 → 0.525, 0.962 |
| **eval 10, blue cup** | 30 | 0.12 / +0.05 | 0.05 cm | 0.09 / +0.04 | 0.409 → 0.403, 0.974 |
| | 46 | 4.58 / +1.86 | 0.12 cm | **4.49 / +1.88** | 0.568 → 0.526, 0.959 |
| | 60 | 4.42 / +0.76 | 0.24 cm | **4.29 / +0.65** | 0.628 → 0.548, 0.957 |
| | 100 | 4.33 / +3.12 | 0.08 cm | **4.27 / +3.09** | 0.608 → 0.569, 0.956 |
| | 150 | 4.15 / +2.08 | 0.12 cm | **4.10 / +1.99** | 0.516 → 0.474, 0.970 |

How to read it:
- The check finds ep24's camera error once the VO keyframe burst is over (f100), but only the vertical part in the middle
  of it (f60). It leaves ep11's tracker lift alone.
- On eval 10 the camera holds at every frame (corrections ≤ 0.24 cm), and the 4.1–4.5 cm step survives.
- **Failed first version [M]:** a translation-only fit failed the positive control (ep24 f100 corrected step 1.03 / 0.94 cm)
  and is not used for any reading. ep24's VO error includes a rotation (the 6-DoF fit at f100 gives about 1.3°).
- **Structural evidence [M]:**
  - Eval 10's VO has keyframes 0, 54 and 130. Every frame of the step (f38–46) is matched to keyframe 0 with 135–181
    inliers, and the camera moves ≤ 0.37 cm per frame over f30–56. ep24's steps sit exactly on its keyframe switches.
  - The parallel screen's depth-ICP background check (`../screen/e10_vo_bg.txt`) finds VO corrections ≤ 0.6 cm. When the
    background is shifted by the cup's step, that check recovers 4.41 and 4.64 cm.
  - With the camera confirmed, the screen's depth fit (`../screen/e10_depth.txt`) separates the two hypotheses. At f60 the
    cup's depth fits the tracked pose (median residual 1.27 cm), not the frame-0 position (5.55 cm).

**Overlay** `eval10/e10_s6_overlay.png` (`scripts/e10_overlay.py`): rectified cam-c frames f0, 35, 42, 46, 60, 100, 117 and
160.
- Colours: red = our blue-cup track, which S6 kept; cyan = the frame-0 hold S6 would write if it froze the cup; yellow =
  the beige track.
- At f0–35 red and cyan coincide on the cup. From f42 on, cyan sits beside the cup, over the fingers and table. Red stays
  on the cup through the grip, the nesting and the release.
- This is visual QA only; the reading above rests on the measurements.

**What this leaves for eval 10 [H]:**
- The vertical part of the track (+3.1–3.7 cm while nested, +1.8–2.1 cm held) has the shape of ep11's tracker lift, a jump
  at the nest and then a held offset. GT-free depth does not settle it:
  - At f150 the screen's fit with the blue cup at its frame-0 height leaves less free space behind the rendered cup than
    the track does (13.9 % vs 26.8 % of pixels) but more surface in front of it (9.8 % vs 1.1 %), at equal median
    residual (0.97 vs 0.96 cm).
- A "height hold" variant cannot be tested on public data. The only public nest (ep11) has a static outer cup, where it
  equals S6.
- The root-cause test is T2 (masking the other objects out of the tracker input; GPU perception box, `../PLAN.md` §3).
  - Falsified for ep11 if blue \* < 0.90.
  - If it passes, re-perceiving eval 10 with masking shows whether the vertical offset disappears.

## 4. Cost, downloads, failures, files
- **Cost:** $0 (this VM's CPU).
- **Downloads:**
  - 3 videos from the public competition dataset (`nvidia/video_to_data_challenge`, cam c): eval 10, plus public ep24 and
    ep11 for the controls. 6.3 MB in total.
  - One HF-store metadata call (`get_paths_info`, 8 paths, no file download).
  - Everything else was already local: the eval screen's pulls, the 29 Oct eval depth slice, refine/in, Phase 1.
  - The videos are hard-linked to `$S/leak/t1/v/ep<N>_c.mp4`, because `assert_inference_input` refuses any path containing
    "observation", as the pipeline's `/content/t3/eval/v` names do.
- **Failures:**
  - T1 P_o arm (rule, ep27).
  - The translation-only camera check (positive control).
  - The 6-DoF check is only partial in the middle of a VO burst (ep24 f60).
- **Not done:**
  - the P_s arm;
  - the T1 rollout and the eval-10 retrain (they need the owner's go-ahead and, after this result, have no eval-10 target);
  - S6 through refine on the other evals. The screen's own S6 copy freezes the rack on evals 14, 15, 16, 28 and 30. Their
    twins move by −0.002 to +0.007 (above), so the expected value is about 0 ± 0.001 LB [E].
- **Files:**
  - `public/`: `t1_scores.json`, `t1_score.log`, `t1_order_diag.json`, `jobs.txt`, `refine_sha256.txt`;
  - `eval10/`: `pose_opt_S6S2.json`, `pose_opt_S6S2_depth29oct.json`, `refine_S6S2.log`, `inputs_sha256.txt`,
    `e10_s6_overlay.png`;
  - `camcheck/`: `ep24.json`, `ep11.json`, `eval10.json`, `camcheck.log`;
  - `scripts/`: `t1_run.sh`, `t1_score.py`, `t1_order_diag.py`, `t1_eval10.sh`, `camcheck.py`, `e10_overlay.py`.
- **Commands for the camera check** (`PY=$S/map/scoring/venv/bin/python`, `CAL=$S/hfds/track_3/public/meta/camera_calibration.json`):
  - `$PY -I scripts/camcheck.py --poses <dir>/poses.npz --det <dir>/det_f0.npz --hands <dir>/hands_refined.npz --video
    $S/leak/t1/v/<ep>_c.mp4 --calib $CAL --meshes meshes/library_v3 --obj <blue_cup|wooden_piece_2> --frames … --label
    <ep> --out <ep>.json`
  - `<dir>` is `$S/refine/in/ep24`, `$S/refine/in/ep11`, or for eval 10 `$S/leak/t1/eval10/in` with the pack-6
    `det_f0.npz`.
  - Run time: about 35 s per frame.
- **Overlay:** `$PY -I scripts/e10_overlay.py $S/leak/t1/eval10/in/poses.npz $S/leak/t1/eval10/S6S2/pose_opt.json
  $S/leak/t1/v/eval10_c.mp4 $CAL meshes/library_v3 eval10/e10_s6_overlay.png`.
