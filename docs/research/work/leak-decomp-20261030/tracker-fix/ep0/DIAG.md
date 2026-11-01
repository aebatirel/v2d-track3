# ep0 diagnosis: why the scan-template track scores 0.078 (pot + lid; twin of eval 1)

30 Oct 2026, ~22:15–23:15 UTC. CPU only on this VM, $0; no GPU, no Kaggle, no commit. Public episode ep0 only.
Mocap and the public scans are read for diagnosis only; every fix below is GT-free and uses our meshes on eval.
Labels: [M] measured here, [E] estimate, [H] hypothesis. Code: working tree on a960523 plus the scripts in `scripts/`.

## Verdict
1. **The starting hypothesis is refuted.** The lid is not flipped, and the error does not persist through the episode.
   - In the scan-template arm (P_s), the **pot** is wrong at frame 0, not the lid. It is turned 179.3° about its
     horizontal axis across the handle, so it sits upside down with the handle reversed, 3.9 cm off [M].
   - The tracker carries that pose for 64 frames (f0–63). At f64 the lid lift makes the pose fall below the table,
     TRACK_GUARD fires, and the pot is re-acquired correctly. From then on its ADD has a median of 1.0 cm (95th
     percentile 1.7 cm, max 3.8 cm) vs mocap [M].
   - The P_s **lid** is correct in every frame under an independent world alignment: ADD 0.5–2.9 cm (95th percentile
     1.3 cm), rotation 0.9–5.1° [M].
2. **The scorer turns 64 bad frames into a total failure.**
   - The kit's frame-0 scene alignment (`_align_registered_scene`) takes the whole scene's rotation and translation
     from slot 0's frame-0 pose, and slot 0 is the pot.
   - So the flipped frame-0 pot rotates the scene by ~180° for all 373 frames. The pot after f64 and the lid
     throughout then score ~12–15 cm ADD at ~178°: pot 0.156, lid 0.001, scene 0.078 [M].
   - "Lid ~179°" (20 Oct) and "lid 0.001" (today) are this artefact.
   - The 20 Oct note also saw "the pot jumps ~10 cm at f75 when the lid is lifted". That matches today's mechanism,
     but the 20 Oct track is not here to re-score [H].
3. **Root cause: a frame-0 detection error that depends on the template's appearance.**
   - With the scan template, the pot is assigned SAM2 proposal 45, the whole round wooden table top (`Ps_masks_f0.jpg`).
   - The scan's gray render is darker than ours (mean intensity 152 vs 198), so the intensity term now favours the
     dark table (137) over the white pot (204).
   - The 0.40 m table passes the size gate, because the pot's handle makes its template 0.37–0.40 m long.
   - FoundationPose then registers the pot on the table mask upside down. The pose stays above the table, so the
     guard does not fire at frame 0.
4. **Our-mesh arm P_o (the eval pipeline) does not fail here, but only barely.**
   - P_o scores 0.962 lib and 0.948 \*.
   - The same table proposal loses to the right one by only **0.005** in score (0.384 vs 0.379). DINOv2 alone prefers
     the table (similarity 0.452 vs 0.403); the intensity term rescues the pot [M].
   - In 8 of the 9 public pot episodes (all but ep27) and both pitcher episodes, an eligible oversized "table" decoy
     competes with the correct proposal: margins 0.005–0.42 [M].
   - P_o's own residual is a constant lid offset of ~1.4–1.8 cm and 3–5° tilt, the same in every phase (rest on the
     pot, in the hand, on the table). That is a template/frame offset, not tracking (§5).
5. **Fixes, all GT-free (§6):**
   - F1, oversized-proposal gate at detection: CPU-validated on the 20 public frame-0 dumps. It bars 0 of 36 chosen
     proposals and all 21 eligible oversized decoys, the ep0 table tops included.
   - F2, backfill after a guard re-acquisition: CPU proxy on P_s ep0 0.078 → **0.995**. It does not fire on ep23 or on
     any other public P track.
   - F3, frame-0 anchor smoothing: tested here on all 20 public episodes and **rejected** by its pre-set rule (mean
     +0.0003 lib; 7 episodes up, 10 down). It only cuts the run-to-run spread 4×.

## 1. Inputs and method
- **Tracks, all on one depth cache with the same camera** (`camera_maxdiff 0.0`):
  - P_s = `runs/20261030-orcP1a-87fc869/results/leak_p1/ep0/perc2scan` (scan templates);
  - P_o = `…/perc2` (library_v3);
  - P_r = `refine/in/ep0` (25 Oct guard run, library_v2; refine input).
  - ep0 is not a REPEAT episode, so there is no P_o2.
  - Local copies: `scratchpad/leak/p1/oracle_roots/{Po,Ps_scan}/ep0`. Fetched for this step (single-file downloads):
    `perc_log_inference.txt`, `track_guard.json`, `masks_f0.jpg` of both arms, and P_s `poses.npz`, into
    `scratchpad/leak/diag_ep0/`.
- **\* convention.** Lib tracks are taken to scan frames by X\*_geom (`tierA/xstar_geom.json`) and scored with the
  scan. "lib" = library_v3 at X_kit, the leaderboard convention. The scorer is the kit chain of `tools/xstar_fit.py`.
  It reproduces p1_check exactly: P_s 0.0783, P_r \* 0.9612 = FRAMES.md [M].
- **Two error views per frame:**
  - **kit**: after the scorer's own frame-0 alignment. This is what the AUC sees.
  - **G**: one world transform, perception → mocap, fitted with a soft-L1 fit on P_o's pot over all 373 frames
    (median residual 0.31 cm). The same G is used for every arm, because the arms share `world_T_cam`. Each object's
    error is then independent of the other object's frame-0 pose.
  - Both views report symmetry-aware ADD (lid 180°), centre distance and rotation.
- **Phases come from mocap** (oracle): speed > 3 cm/s or > 15°/s means moving. Lid-on-pot = the lid within 1 cm of its
  frame-0 pose in the pot frame.
- **Hand proximity** = refine/in `hands_refined.npz` joints vs the mocap surface mapped by G⁻¹ (an occlusion proxy).
- fps 20.25. Per-frame arrays: `scratchpad/leak/diag_ep0/out/perframe.npz`.

Mocap timeline (ep0, 373 frames):

| phase | frames | what happens |
|---|---|---|
| A | 0–37 | rest; lid on pot; hands approach (35 → 3 cm) |
| B | 38–52 | pot handle grasped (hand ≤ 1.5 cm until f279), both static |
| C | 53–85 | lid lifted off and set on the table (lid ≤ 34 cm/s); pot held still |
| D | 86–107 | lid on table, pot held still |
| E | 108–206 | pot carried / waved (25–49 cm/s, ≤ 75°/s); lid nudged f132–144 |
| F | 207–239 | pot held still |
| G | 240–266 | lid put back on the pot (≤ 47 cm/s) |
| H | 267–372 | rest, lid on pot; hand leaves the pot ~f280 |

## 2. Errors per object and phase [M]
Mean over each phase. "kit ADD" is the scorer's view; G ADD and G rot are each object's own error (lid rotation modulo
its 180° symmetry). "share" is the mean per-frame contribution to the ADD-AUC (1 = every threshold met).

**white_pot**

| phase | P_s kit ADD | P_s G ADD | P_s G rot | P_s share | P_o kit ADD | P_o G ADD | P_o G rot | P_o share | P_r kit ADD | P_r G ADD | P_r share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A 0–37 | 0.8 | **14.5** | **178.8°** | 0.98 | 0.3 | 0.2 | 1.0° | 1.00 | 0.1 | 0.2 | 1.00 |
| B 38–52 | 2.3 | **14.5** | **175.6°** | 0.82 | 0.5 | 0.7 | 2.5° | 1.00 | 0.7 | 0.6 | 1.00 |
| C 53–85 | 10.7 | 5.5 | 59.6° (flip until f63) | 0.26 | 0.4 | 0.4 | 1.9° | 1.00 | 0.4 | 0.4 | 1.00 |
| D 86–107 | **14.6** | 0.9 | 1.2° | 0.00 | 0.4 | 0.2 | 1.3° | 1.00 | 0.2 | 0.3 | 1.00 |
| E 108–206 | **19.9** | 1.2 | 1.7° | 0.00 | 0.9 | 0.8 | 2.0° | 0.97 | 0.8 | 0.8 | 0.97 |
| F 207–239 | **14.5** | 0.9 | 1.1° | 0.00 | 0.3 | 0.2 | 0.6° | 1.00 | 0.2 | 0.2 | 1.00 |
| G 240–266 | **14.6** | 0.9 | 1.5° | 0.00 | 0.7 | 0.5 | 3.3° | 1.00 | 0.6 | 0.5 | 1.00 |
| H 267–372 | **14.6** | 1.1 | 2.1° | 0.00 | 0.5 | 0.3 | 1.0° | 1.00 | 0.3 | 0.3 | 1.00 |

**white_pot_lid**

| phase | P_s kit ADD | P_s G ADD | P_s G rot | P_s share | P_o kit ADD | P_o G ADD | P_o G rot | P_o share | P_r kit ADD | P_r G ADD | P_r share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A 0–37 | **12.8** | 0.9 | 3.3° | 0.00 | 1.8 | 1.7 | 4.7° | 0.94 | 1.7 | 1.7 | 0.94 |
| B 38–52 | **12.9** | 1.0 | 4.2° | 0.00 | 1.7 | 1.6 | 3.3° | 0.94 | 1.6 | 1.6 | 0.94 |
| C 53–85 | **14.6** | 1.1 | 3.6° | 0.01 | 1.9 | 1.7 | 3.8° | 0.88 | 1.8 | 1.7 | 0.91 |
| D 86–107 | **12.2** | 1.0 | 3.4° | 0.00 | 2.1 | 1.5 | 4.7° | 0.84 | 1.8 | 1.5 | 0.94 |
| E 108–206 | **12.3** | 0.9 | 1.8° | 0.00 | 1.9 | 1.4 | 2.5° | 0.91 | 1.7 | 1.4 | 0.93 |
| F 207–239 | **12.2** | 1.0 | 2.8° | 0.00 | 2.0 | 1.4 | 3.7° | 0.87 | 1.7 | 1.4 | 0.94 |
| G 240–266 | **15.9** | 1.3 | 3.3° | 0.00 | 2.0 | 1.6 | 4.1° | 0.89 | 1.8 | 1.6 | 0.90 |
| H 267–372 | **13.0** | 1.1 | 3.3° | 0.00 | 1.9 | 1.8 | 4.4° | 0.91 | 1.8 | 1.8 | 0.93 |

Scores [M]:

| arm | scene, kit | pot | lid |
|---|---|---|---|
| P_s, \* (= scan native) | 0.0783 | 0.1555 | 0.0010 |
| P_o, \* / lib | 0.9476 / 0.9620 | 0.9928 / 0.9904 | 0.9025 / 0.9335 |
| P_r, \* / lib | 0.9612 / 0.9641 | 0.9926 / 0.9918 | 0.9298 / 0.9363 |

Under the oracle G alignment (each object independent of slot 0):
- P_s: pot **0.800** (its 64 flipped frames), lid **0.972**.
- P_o: pot 0.993, lid 0.932.

## 3. Where the P_s error comes from (frame by frame) [M]
- **Frame 0, detection** (`Ps_masks_f0.jpg`; the P_o log lists the same 66 proposals):
  - P_s puts the pot on proposal 45, the whole round table top: 0.40 m, intensity 137, area 1531 cm².
  - P_s puts the lid on proposal 48, the pot + lid body: 0.17 m, intensity 205.
  - P_o puts the pot on proposal 1 (pot + lid + handle, 341 cm²) and the lid on 25 (the handle). The guard rejects
    that lid pose at frame 0 (−4.2 cm under the table) and re-registers the lid on proposal 48.
- **Pot scores, P_s:** 45 → 0.435, 53 (table) → 0.394, 1 (pot) → 0.385.
- **Pot scores, P_o:** 1 → 0.384, 45 → 0.379, 25 → 0.369.
- **Score decomposition, P_o dump** (`refine/in/ep0/det_f0.npz`, same proposals):
  - DINOv2 similarity to the pot templates is table **0.452** vs pot 0.403.
  - The intensity term (LAM_I 0.3 × |Δ|/255) moves the scores by −0.072 for the table and −0.007 for the pot, which
    rescues the pot.
  - With the scan template (mean intensity 152), the same term moves them by −0.018 (table) and −0.061 (pot). That
    flips the choice.
- **Frame 0, registration.**
  - On the table mask, FoundationPose places the pot **upside down with the handle reversed**: 179.3° about the body
    axis (−0.02, −0.98, 0.20), i.e. the pot's middle principal axis, horizontal and across the handle; 3.88 cm.
  - The pose stays above the table, so `plausible()` is true and there is no frame-0 retry.
  - `overlay_pot_flip_f0_f63_f64.png` shows it: the yellow P_s handle points away from the camera at f0 and f63, and
    lies on the cyan mocap handle at f64.
- **f0–63:** the flipped track wobbles by up to 3.2 cm and 20.8° in the world while the real pot is static (mocap
  ≤ 1.3 cm/s). The hand grasps the handle at f38.
- **f64:** the lid is 13 cm off the pot. The flipped pose falls below the table, and the guard re-detects and
  re-acquires the pot: a jump of 5.19 cm and 176.1°.
- **f64–372:** the P_s pot tracks the real one at a median 1.0 cm (G; phase means 0.9–1.2 cm). That includes the
  carry at 25–49 cm/s (f108–206), the lid replacement and the release.
- **Scoring.** Slot 0 (the pot) is both the translation and the rotation anchor of `_align_registered_scene` (it is
  also the first object without a symmetry axis). The 179° frame-0 pot pose therefore rotates every frame of both
  objects.
  - Kit view: P_s pot 0.8 cm at A (it is its own anchor), then 14.5–19.9 cm for every frame after f64. P_s lid
    12–16 cm at 175–180° in every phase.
  - Kit vs G is the signature: G small, kit large → scene-anchor error; G large → the object's own error.

## 4. Hypothesis check
| claim | verdict | evidence [M] |
|---|---|---|
| frame-0 initialisation error | **confirmed, but for the pot**, via a wrong mask (table top) | §3; G rot 178.8° at f0–37 |
| the lid (scan template) is flipped ~180° | **refuted** | P_s lid G ADD 0.9–1.3 cm, rot 1.8–4.2° (phase means, every phase); its 178° appears only in the kit view (anchor) |
| one-time error, then tracked consistently wrong | **refuted** | guard re-acquisition at f64; correct from then on (G median 1.0 cm) |
| drift, event jump, static object wandering | **not seen** | no growth of G error with time or speed. The only jump (f64) is the correction. The pot carry f108–206 is tracked at 1.2 cm G (P_s) / 0.8 cm (P_o) |
| identity swap | **no** | each object follows its own mocap body in G |

## 5. The our-mesh arm (P_o): what is left [M]
- **Pot:** 0.990 lib / 0.993 \*, at ≤ 1 cm in all phases. The carry costs 3 % of frames.
- **Lid:** 0.9335 lib / 0.9025 \*. A **constant** offset in the lid body frame, with near-equal means in every phase:
  - G view: along the lid normal −1.00 / −0.98 / −1.00 / −1.08 cm (on pot / moving / on table / on pot again);
    in-plane 0.9–1.4 cm; tilt 2.9–4.2°.
  - P_o lid relative to the P_s lid (same world): [−0.40, −0.24, +0.63] cm, sd ≤ 0.09 cm; 1.6° ± 0.65°.
  - So this is the template / frame relation of the lid (FRAMES.md H1, L2), not the tracker. It agrees with ep0's
    X\*_trk lid offset (3.30 cm, 3.4°) and T_trk − T\* = +0.035.
- **P_o vs P_r differ only by noise.**
  - Their pot frame 0 differs by 0.28 cm / 0.51°.
  - Because the pot anchors the scene, this moves the lid's \* AUC by 0.027 (0.9025 vs 0.9298). The lid's ADD sits
    near the 2 cm threshold, so small shifts flip many frames.
- **Lid-on-pot seat constraint (dropped).**
  - Oracle ceiling: the on-pot frames (169) were set to P_o pot ∘ mocap lid-in-pot. Lid lib went 0.9335 → 0.9365
    (+0.003); \* went 0.9025 → 0.9388.
  - In lib the lid floor is set by the pot's registration E (0.75–0.88 cm, 1.3–2.5°, FRAMES.md), not by the lid's
    seat.
  - A nest/seat constraint for eval 1 is therefore not worth building [M ceiling].
  - (A crude GT-free seat from our meshes was also built and was 6.6 cm off; not pursued.)

## 6. GT-free fixes, public tests that would falsify them, eval exposure, value

### F1. Oversized-proposal gate at detection (`pipeline/det_rules.py` + `perc2.py detect()`, also used by guard re-detection)
- **Rule.** Bar proposal j for object a when its metric silhouette area exceeds 1.5 × the template's largest silhouette
  area. Area = Σ over mask pixels of (z/f)²; template area = max over 162 view directions of the convex hull of the
  projected mesh (an upper bound).
  - Only our depth and our mesh are used, so the rule is template-agnostic: the table top measures 3.34× our pot and
    3.48× the scan pot.
  - [H] the threshold 1.5; the CPU replay below gives a 0.42 margin above the largest correct ratio (1.08).
- **CPU check done** [M]. 20 public frame-0 dumps (refine/in, our templates), `scripts/area_gate.py`,
  `decoy_margin.txt`:
  - Chosen proposals have ratios 0.16–1.08 (36 objects), so 0 are barred.
  - 21 eligible proposals are barred: table tops for the pot in eps 0, 2, 26, 41–45 and oversized masks for the pitcher
    in 21 and 22.
  - The ep0 table proposals 45, 53 and 0 measure 3.34 / 3.36 / 2.41×.
  - With them barred, P_s ep0's pot falls to proposal 1 (score 0.385), the P_o choice.
- **Falsifier** (pre-register before running):
  - (a) `tools/det_replay.py` + `det_score.py` on the 23 Oct public dumps (frames 0 and quarter points). F1 is
    rejected if any instance that R0 gets right turns wrong.
  - (b) GPU perception re-run with the gate (owner go-ahead; ≈ 1 box, < 1 h), P_s and P_o on ep0, and P_o on 2, 26,
    27, 41–45, 21, 22. F1 is rejected if P_s ep0 \* < 0.95, or if any P_o episode drops by more than 0.005 lib.
- **Eval exposure.** All pot evals: 1, 3, 5, 6 (pot = slot 0, it anchors the whole scene), 8 (the pot sets the
  scene rotation; the beige cup sets the translation) and 28 (pot = slot 1; the rack anchors). Also pitcher eval 20.
  - On public data the decoy margin is as low as 0.005 with our own templates (ep0).
  - GPU nondeterminism or a rerun can flip it, and sim_vs_ref cannot see it: the robot copies a flipped reference just
    as well.
  - **First step, GT-free and cheap:** read the 7 eval episodes' `det_f0.npz` from their perception runs and compute
    the chosen proposals' area ratios. Any ratio above 1.5 marks a suspect eval reference.
- **Value [E]:**
  - An affected eval episode loses ΔR ≈ 0.9 (P_s ep0: 0.078 vs 0.995). LB ≈ (c/20)·a·S·ΔR = (0.74–1.0)/20 × 1.025 ×
    ~0.9 × 0.9 ≈ **+0.031 to +0.041 LB per affected episode**.
  - If the screen flags none, the value now is 0, and F1 is insurance for any re-run of perception (protecting 7 evals).

### F2. Backfill after a guard re-acquisition (`perc2.py` tracking loop; CPU post-processing as a stop-gap)
- **Rule.**
  - **Trigger:** an object's first guard re-acquisition at frame k jumps by more than 5 cm or 30° from frame k−1.
  - **Quasi-static case:** if its perceived track over [0, k) stayed within 4 cm / 25° of frame 0, replace [0, k) by
    the world pose at k.
  - **Moving case:** the general version re-tracks backward from k to 0 with FoundationPose `track_one`. It accepts
    the backward track if every frame is plausible and its frame-0 render-and-compare agreement beats the forward one.
  - [H] thresholds. The 4 cm / 25° were set after seeing ep0's 3.2 cm / 20.8° wobble, so they are fitted to this case.
- **CPU proxy** [M] (`scripts/backfill_rule.py`, `backfill_rule.json`):
  - P_s ep0 fires at k = 64: 0.0783 → **0.9948** (pot 0.994, lid 0.996). Holding f70 instead gives 0.9950.
  - ep23 P (board 1 re-acquired at f155 after 16 cm / 39° of motion) does not fire; unchanged at 0.0418.
  - No other public P track (refine/in, 25 Oct) has a re-acquisition, so none changes.
- **Falsifier:**
  - (a) Pull the Phase-1 `track_guard.json` and guard log lines of all 20 episodes, both arms (40 small files). F2 is
    rejected if the rule fires on a P_o track and lowers it by more than 0.005 (lib or \*).
  - (b) GPU backward-track version on P_s ep0. F2 is rejected if it gives < 0.95 \*, or if it changes any P_o episode
    by more than 0.005 where the static rule does not fire.
- **Eval exposure.** Evals with guard re-acquisitions (work log, 25 Oct check): 8 (beige cup, slot 0: a frame-0 retry
  plus 2 re-acquisitions) and 14 (cup, slot 0: 1). 32 and 33 were expected from the plausibility flag. The rule acts
  only where the jump and quasi-static conditions hold; checking that on their logs and poses is GT-free.
- **Value [E]:** 0 if it fires nowhere on eval. Per firing on a wrong pre-segment of a slot-0 / anchor object,
  ≈ +0.03–0.04 LB, as for F1.

### F3. Frame-0 anchor smoothing (post-processing of `poses_world_vo.npz` before mkref, or in mkref)
- **Rule.** Each object's frame-0 pose := the mean pose over its initial window (≤ K = 20 frames) in which the
  perceived object stays within 1 cm / 3° of frame 0.
  - The scorer anchors the scene on single frame-0 poses: translation from slot 0, rotation from the first object
    without a symmetry axis. The robot starts from the reference's frame 0. One frame of registration noise therefore
    moves every object.
- **ep0** [M]:
  - P_o \* 0.9476 → 0.9616, lib 0.9620 → 0.9645.
  - P_r \* 0.9612 → 0.9614, lib 0.9641 → 0.9646.
  - The P_o–P_r gap closes (0.014 → 0.000 \*).
- **20-episode public test** (`scripts/f0smooth_all.py`; Phase-1 P_o, the P_o2 repeat on 10 eps, refine P;
  lib and \*): see the table below.
- **Pre-set reading** (PLAN §4 reference-level rule, here applied to perception tracks):
  - adopt if the mean ΔR ≥ +0.003 on lib with ≥ 12/20 episodes non-negative and no episode < −0.005, and if
    |P_o − P_o2| shrinks;
  - else drop. It is a ride-along (≤ 0.003 LB), never a retrain trigger.
- **Eval exposure:** all 20 evals (every reference has a frame 0). **Value [E]** before the test: ≤ +0.002 LB,
  mainly variance.

**F3 public test, run here** [M]. The reading above was written before this 20-episode run (`f0smooth_all_K20.log`;
Δ = smoothed − raw, 20 eps; P_o2 has 10):

| arm | lib mean Δ | lib min / max | \* mean Δ | \* min / max | eps up / down (lib) |
|---|---|---|---|---|---|
| P_o | +0.0003 | −0.0095 / +0.0204 | +0.0015 | −0.0071 / +0.0225 | 7 / 10 |
| P_o2 | +0.0019 | −0.0135 / +0.0204 | +0.0030 | −0.0056 / +0.0211 | 5 / 4 |
| P_r | +0.0006 | −0.0073 / +0.0204 | +0.0001 | −0.0117 / +0.0225 | 7 / 11 |

- Largest gains: ep39 +0.020 lib, ep21 +0.016, ep12 +0.006, ep0 +0.0025.
- Largest losses: ep26 −0.0095, ep45 −0.0073, ep2 −0.0076, ep40 −0.0063.
- Run-to-run spread |P_o − P_o2| (lib) falls from a mean of 0.0017 (max 0.0136) to 0.0004 (max 0.0027).

**Verdict: F3 fails its pre-set rule.** The mean is +0.0003 < +0.003, only 10/20 episodes are non-negative (7 up,
10 down by more than 0.0005, 3 unchanged), and 4 episodes are below −0.005. It is **not adopted** as an accuracy fix.
It does make the frame-0 anchor reproducible (4× less repeat spread) [M]. A variant may be worth a later look: average
only frames whose render-and-compare agreement is no worse than frame 0's [H]. Nothing is changed now.

### Order and cost
1. **F1 eval screen** (GT-free, CPU, ~7 single-file downloads of the eval `det_f0.npz`). If it flags an eval pot
   or pitcher episode, that eval's reference is suspect: ≈ +0.03–0.04 LB at stake [E].
2. **F1 CPU replay** with `det_replay` / `det_score` on the public dumps ($0).
3. **F2 GT-free check** of the eval re-acquisitions (8, 14, 32, 33: jump and pre-motion from their logs and poses;
   CPU) and of the 40 Phase-1 guard logs.
4. **Only then**, with the owner's go-ahead: one GPU perception box, ≈ $1–2 [E], for F1 + F2 on the public
   episodes in §6 (pass rules above), before any eval re-perception or retraining.

### Not proposed
- A lid-on-pot seat/nest constraint: the oracle ceiling is +0.003 lib on the lid (§5).
- Static-object freeze: the pot is held from f38, and P_o's static phases are already at 0.2–0.5 cm.

## 7. Consequences for the leak decomposition (PLAN §2, L2/L3)
- **Do not read L2 = R\*(P_s) − R\*(P_o) on ep0 from the raw P_s (0.078 vs 0.948).**
  - It is a detection artefact of the scan template's *appearance* (texture intensity), not of its shape or of the
    tracker.
  - Read ep0 on the backfilled P_s (0.995 \*, labelled "CPU backfill proxy"), or exclude ep0 from L2 and report it
    under detection.
  - On the backfilled P_s, L2 on ep0 is +0.047 for the scene (0.9948 vs 0.9476 \*): lid +0.093 (0.9958 vs 0.9025),
    pot +0.001. Under the oracle G alignment, the lid gains +0.040 (0.972 vs 0.932) [M].
- **Appearance confound.** The same intensity-term effect can change other P_s frame-0 choices.
  - Before attributing L2 on any episode, compare the P_o and P_s `assignment` lines of the 20 Phase-1 logs (GT-free,
    20 small downloads).
  - Episodes whose frame-0 assignment differs between the arms should be read separately [H].
- **L3 on ep0 (the tracker given a true template):** once frame 0 is right, the tracker loses ≈ 0.005. P_s
  backfilled 0.995; G ADD ≈ 1 cm through the carry at up to 49 cm/s [M].

## 8. Commands (this VM; `S=$scratchpad`, `PY=$S/map/scoring/venv/bin/python`; scripts copied to `scripts/`)
1. `$PY -I $S/leak/diag_scripts/ep0_diag.py 0`: per-frame kit/G errors, phases and hands →
   `$S/leak/diag_ep0/out/{perframe.npz,summary.json}` (7 s).
2. `$PY -I $S/leak/diag_scripts/ep0_print.py 0 1`: per-frame table. `ep0_phase_table.py` gives the phase tables in §2.
3. `$PY -I $S/leak/diag_scripts/ep0_cf.py`: P_s f0 error axis, backfill, G-aligned scores, F3 on ep0 →
   `counterfactuals.json` (15 s).
4. `$PY -I $S/leak/diag_scripts/ep0_lid.py`: lid offset structure (§5).
5. `$PY -I $S/leak/diag_scripts/ep0_seat.py`: seat ceiling → `seat.json` (2.5 min).
6. `$PY -I $S/leak/diag_scripts/area_gate.py`, `ext2_gate.py`, `decoy_margin.py`: F1 on the 20 public dumps → `decoy_margin.txt`.
7. `$PY -I $S/leak/diag_scripts/backfill_rule.py` → `backfill_rule.json`.
8. `K=20 $PY -I $S/leak/diag_scripts/f0smooth_all.py` → `$S/leak/diag_ep0/out/f0smooth_all_K20.{json,log}`.
9. `$PY -I $S/leak/diag_scripts/ep0_overlay.py $S/leak/diag_ep0/overlays 0,40,63,64,150,300` and
   `ep0_overlay_pot.py … 0,63,64`: projections into camera a (frame t+1) through `hands_refined.npz` `T_rect_a`/`Ka`/`Da`.
   - Colours: mocap blue (scan at G⁻¹·mocap), P_o green, P_s red.

Files here:
- `overlay_montage_f0_f40_f63_f64_f150_f300.png`;
- `overlay_pot_flip_f0_f63_f64.png`;
- `Ps_masks_f0.jpg` and `Po_masks_f0_before_guard.jpg` (perc2's own frame-0 mask images);
- `summary.json`, `counterfactuals.json`, `seat.json`, `backfill_rule.json`, `decoy_margin.txt`,
  `f0smooth_all_K20.{json,log}`;
- `scripts/`.

Store traffic: 7 single-file downloads (both arms' logs, guard JSONs and masks; P_s `poses.npz`), no listings.
