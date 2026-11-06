# ep31 tracker diagnosis: the scene anchor's frame-0 tilt, not the rack (30 Oct 2026, ~23:35 UTC)

ep31 is the public twin of eval 30: a mini sweeper stands between the fins of a dish rack, is lifted, scrubs along the
fins and is put back. This is a public-episode oracle diagnostic. Mocap and the public scans are read only to score and
diagnose, after inference. Every proposed fix is GT-free and uses our meshes. CPU only on this VM, $0; no GPU, no Kaggle,
no commit. Labels: [M] measured, [E] estimate, [H] hypothesis.

## Verdict
1. **The starting hypothesis is refuted for the rack and moved to frame 0 for the sweeper [M].**
   - The rack is not thin wire. It is solid white plastic with fins, and its depth is good: at frame 0 the observed depth
     sits 0.36 cm (median) from the true rack surface on 100 % of 21.6k rack pixels. Our rack mask matches the true
     visible rack at IoU 0.93.
   - The rack does not drift. In mocap it moves ≤ 0.15 cm. Our tracks wander ≤ 0.65–0.68 cm horizontally and 2.4–3.6° over
     290 frames. Under one oracle world alignment the rack's median error is 0.42 cm / 1.1° (P_s) and 0.86 cm / 1.5°
     (P_o): rack AUC 1.000 and 0.987.
   - The sweeper *is* hidden by the fins, but what costs score is its pose at frame 0, not drift or loss later on.
2. **One number explains ep31: the sweeper's frame-0 orientation is off by ~9° [M].**
   - The error is 9.1° in P_o, 9.1° in the repeat P_o2 and 8.9° in P_s. The position error is only 0.2–0.7 cm.
   - The sweeper is slot 0 and has no symmetry axis, so the scorer takes the whole scene's rotation from its frame-0 pose
     (`_align_registered_scene`).
   - That 9° turns the correctly tracked rack into a constant 2.7–2.8 cm ADD error in every frame of every phase
     (table §1): rack AUC 0.74 (P_o, \*), 0.69 (P_o, lib), 0.80 (P_s).
   - It also adds about 1 cm to the sweeper's error during the held phases.
3. **Counterfactual (oracle) [M].** Replacing only the sweeper's frame-0 pose with the truth raises P_o from 0.7998 to
   **0.985 lib** and from 0.8351 to **0.963 \***.
   - That is nearly the whole ep31 deficit in lib (1 − 0.7998 = 0.200).
   - For scale: P_o under an oracle world alignment scores 0.980 \*, and P_s 0.995.
4. **Mechanism [M]: the frame-0 input is contaminated, and the tilted pose fits it better than the truth does.** At
   frame 0 the sweeper is a white object among white fins, seen edge-on (its 4.8 cm side faces the camera), and its head
   is behind the front fins. A fit that uses all of the input lands on the tilt; trimming the outliers (F1) recovers most
   of the truth.
   - Our sweeper mask covers only **51 %** of the sweeper's predicted visible silhouette (GT-free number) and 47 % IoU
     of the true visible silhouette. 12 % of the mask is fin edges whose depth lies **4.3 cm in front** of the sweeper.
   - Stereo depth on the true sweeper pixels outside our mask lies **2.6 cm behind** the true surface (it bleeds to the
     background). Inside the mask it is good (+0.35 cm).
   - The tilted perceived pose explains these inputs better than the truth does:
     - depth residual on the visible silhouette 0.36 cm vs 0.76 cm;
     - mask IoU 0.51–0.53 vs 0.47.
   - The same tilt returns when the sweeper is put back among the fins: 8.7–10.6° over f246–289, against 3.0–5.6° while
     it is held and its head is visible.
   - The error is systematic. It appears in P_o, P_o2 and P_s, and in the 25 Oct refine track (lib 0.7999).
5. **What it is not [M].**
   - Not drift: the rack error is flat in every phase.
   - Not a static object wandering: rule F1 of the ep11 diagnosis, which freezes the rack, gives lib +0.000.
   - Not an identity swap, and not a jump at grasp, occlusion or release.
   - Not an upright/stable-pose problem: the true sweeper leans on a fin. Our mesh's nearest stable face is 6.8° from
     the true resting direction, more than P_o's own tilt error of 4.3°.
   - Not a penetration problem: the tilted P_s pose penetrates the rack less than the truth does (2.4 vs 3.4 mm).
6. **Fix F1 (frame-0 depth-ICP polish), CPU proxy on ep31 [M].**
   - Rule: point-to-plane ICP of our sweeper mesh onto our own mask's depth, keeping the best 80 % of pairs, starting
     from the tracker's pose.
   - Result: frame-0 tilt **9.2° → 3.7°**; P_o **lib 0.7998 → 0.9514**, \* 0.8351 → 0.9199.
   - **As a general rule F1 is falsified** by its pre-registered 20-episode test (`PREREG_f0icp.md`, written before the
     run). The mean passes (lib +0.011), but the harm guard fails: slot-0 polish costs ep12 −0.015 and ep40 −0.011, and
     polishing every object costs ep12 −0.085.
   - A post-hoc gate [H] would touch only ep31 and ep18 on public data, so the public evidence for it is n = 1. It
     applies the polish only to a rotation anchor whose mask covers < 70 % of its predicted visible silhouette, a
     GT-free number. It needs the rollout gate (§4).
7. **Side finding (L1, mesh session) [M, Tier A a1.json].** The kit's registration of our library_v3 sweeper flips 180°
   in 25 of 50 host-scan perturbations at ep31's seed. Whenever it flips, ep31 scores lib 0.094–0.096 (unflipped
   0.80–0.85), because the sweeper is the anchor.
   - With the clean public scan, eval 30's seed does not flip: 0.7–0.9° (work log, 25 Oct entry).
   - Eval 30 is therefore exposed only if the host's scan differs from the public one. A registration-safe sweeper
     (PLAN §4: 0/50 flips) is the remedy.

## Inputs and commands (this VM, repo a960523 + the scripts in `scripts/`)
- Tracks, all from `runs/20261030-orcP1b-87fc869/results/leak_p1/ep31/`, already in `$S/leak/p1/runs/...` (`S` = the
  session scratchpad), so nothing was downloaded:
  - `perc2/poses_world_vo.npz` (P_o, md5 8a632780…);
  - `perc2rep/poses_world_vo.npz` (P_o2, ebea46ce…);
  - `perc2scan/poses_world_vo.npz` (P_s, b2a7df07…).
  - P_o and P_o2: the sweeper is bit-identical; the rack differs by ≤ 0.21 cm / 0.58°.
- Frame-0 inputs from the 25 Oct refine run (`$S/refine/in/ep31`): `depth0.npy`, `det_f0.npz` (chosen proposals 78 =
  sweeper, 3 = rack), `hands_refined.npz` (hands, used only as an occlusion and contact proxy), `poses.npz`.
- X\*_geom: `../../tierA/xstar_geom.json`. Mocap: `$S/map/scoring/t3/ep31.parquet`. Video: cam a
  `$S/hfds/.../episode_000031.mp4`.
- Scoring: the kit chain of `tools/xstar_fit.py`. "\*" = scan frames by X\*_geom; "lib" = library_v3 at X_kit.
  - Neither object has a symmetry axis, so ADD is plain.
  - Reproduced: P_o 0.8351 \* / 0.7998 lib, P_o2 0.8336, P_s 0.8685, as in `phase1/RESULTS.md`.
- Three world alignments per track:
  - **kit**: the scorer's own; the rotation comes from the sweeper's frame-0 pose. This is what the AUC sees.
  - **rack0**: the same rule anchored on the rack (diagnostic).
  - **bw**: one rigid transform fitted over all frames and both objects (oracle). It removes the scene-alignment error.
- Commands (`PY=$S/map/scoring/venv/bin/python`, run from `$S/leak/diag_31`, `OMP_NUM_THREADS=2 SPLIT=public`):
  1. `$PY -I scripts/diag31.py diag31.json`: per-frame errors in the three alignments, mocap phases, hands, contact;
  2. `$PY -I scripts/phase_table.py`: §1 table;
  3. `$PY -I scripts/rotbody.py SCRIPTS`, `errdir.py SCRIPTS`, `relpose.py SCRIPTS`: error direction in body, camera and
     rack frames;
  4. `$PY -I scripts/f0render.py SCRIPTS f0render.json`: z-buffered render of truth / P_s / P_o vs our mask and depth;
  5. `$PY -I scripts/stable_check.py SCRIPTS` and `penetration.py SCRIPTS`: the two physical priors;
  6. `$PY -I scripts/f0icp.py SCRIPTS f0icp.json`: F1 on ep31 plus the oracle counterfactuals;
  7. `$PY -I scripts/f0icp_all.py {Pr,Po} f0icp_all_{Pr,Po}.json`: the pre-registered 20-episode test
     (logs `f0icp_all_{Pr,Po}.log`);
  8. `$PY -I scripts/coverage_all.py coverage_all.json`: GT-free mask coverage per object, 20 episodes;
  9. `$PY -I scripts/f0crop.py OUT.png`, `f0crop_icp.py SCRIPTS OUT.png` and `overlay31.py SCRIPTS OUT.png`: the figures.
- Copies of the scripts and the JSON outputs (`diag31.json`, `phase_table.json`, `f0render.json`, `f0icp.json`,
  `f0icp_all_*.json`, `coverage_all.json`) are in this folder.

## 1. Error per object and phase [M]
Phases come from mocap and the audit (`docs/research/grasp/audit-boards-ep24-sweeper-rack-ep31.md` §3.1). The mocap
segmenter marks the sweeper at rest over f0–26, moving over f27–235 with short pauses, and at rest from f246 on. The rack
is at rest throughout.

Hand = median distance from the nearest refined hand joint to the object's surface (cm), as an occlusion and contact
proxy. Gap = the mocap sweeper–rack surface gap. Bbox = fraction of sweeper samples inside the rack's box.

Cells give median ADD (cm) / median rotation error (°) / AUC of that phase. **kit** = what the scorer sees; **bw** =
after the oracle world fit. The P_o2 values equal P_o to within 0.03 cm, so they are left out (`phase_table.json`).

| phase (frames) | hand sw / rack | gap, bbox | sweeper P_o kit | sweeper P_o bw | sweeper P_s bw | rack P_o kit | rack P_s kit | rack P_o bw | rack P_s bw |
|---|---|---|---|---|---|---|---|---|---|
| A rest in the fins, hands off the sweeper (0–19) | 15.7 / 4.9 | 0.03, 0.74 | 0.15 / 1.6 / 1.000 | 0.85 / 9.1 / 1.000 | 0.76 / 9.9 / 1.000 | **2.84 / 9.9 / 0.794** | **2.72 / 9.0 / 0.812** | 0.79 / 2.1 / 0.988 | 0.41 / 0.8 / 1.000 |
| B rest, hands arrive; left hand steadies the rack (20–26) | 1.6 / 2.0 | 0.03, 0.74 | 0.90 / 8.3 / 0.982 | 1.28 / 11.2 / 0.955 | 1.31 / 14.4 / 0.946 | 3.00 / 10.3 / 0.759 | 2.81 / 9.3 / 0.812 | 0.80 / 2.3 / 0.991 | 0.31 / 1.0 / 1.000 |
| C pinch closes, ≤ 0.5 cm motion (27–44) | 0.6 / 1.9 | 0.02, 0.74 | 0.75 / 9.6 / 0.990 | 1.32 / 3.3 / 0.938 | 1.06 / 13.5 / 0.944 | 3.02 / 9.9 / 0.701 | 2.89 / 9.3 / 0.812 | 0.86 / 1.4 / 1.000 | 0.43 / 0.9 / 1.000 |
| D lift (45–61) | 0.9 / 1.9 | 1.41, 0.17 | 0.94 / 5.9 / 0.982 | 1.28 / 4.9 / 0.941 | 0.77 / 4.7 / 0.989 | 3.08 / 10.0 / 0.688 | 2.90 / 9.5 / 0.812 | 1.04 / 1.7 / 0.967 | 0.51 / 1.1 / 1.000 |
| E scrub strokes among the fins (62–184) | 0.8 / 1.9 | 0.03, 0.66 | 1.73 / 6.5 / 0.904 | 0.67 / 4.5 / 0.994 | 0.45 / 3.5 / 0.999 | 3.04 / 9.7 / 0.713 | 2.90 / 9.5 / 0.790 | 0.95 / 1.2 / 0.979 | 0.47 / 1.1 / 1.000 |
| F second lift and carry (185–234) | 0.8 / 1.8 | 1.55, 0.28 | 1.56 / 4.9 / 0.930 | 0.97 / 5.6 / 0.973 | 0.45 / 4.0 / 0.993 | 2.98 / 9.9 / 0.760 | 2.80 / 9.2 / 0.812 | 0.76 / 1.5 / 0.995 | 0.25 / 1.1 / 1.000 |
| G put back standing (235–245) | 0.7 / 1.8 | 0.02, 0.77 | 1.76 / 7.7 / 0.938 | 1.37 / 4.9 / 0.938 | 0.69 / 3.0 / 1.000 | 2.92 / 9.8 / 0.812 | 2.71 / 9.3 / 0.812 | 0.76 / 1.5 / 1.000 | 0.24 / 1.5 / 1.000 |
| H end rest in the fins (246–289) | 5.0 / 2.7 | 0.02, 0.77 | 1.56 / 4.4 / 0.889 | 1.39 / 10.6 / 0.935 | 0.86 / 8.7 / 0.980 | 2.91 / 10.0 / 0.812 | 2.60 / 8.7 / 0.812 | 0.78 / 2.2 / 1.000 | 0.39 / 1.0 / 1.000 |
| **whole episode** | | | AUC 0.926 | 0.972 | 0.990 | **0.744** | **0.803** | 0.987 | **1.000** |

Episode AUC [M]:

| track | kit (\*) | lib | rack-anchored | bw (oracle) |
|---|---|---|---|---|
| P_o | 0.8351 | 0.7998 | 0.9633 | 0.9797 |
| P_o2 | 0.8336 | – | 0.9635 | 0.9792 |
| P_s | 0.8685 | – | 0.9904 | 0.9950 |

How the scorer's alignment differs from bw: 9.08° (P_o), 9.10° (P_o2), 8.89° (P_s). That is the sweeper's frame-0
rotation error.

Where the error comes from, by the task's categories:
- **Frame-0 initialisation of the rotation anchor: yes, and it dominates.**
  - The kit-chain rack error is 2.7–2.8 cm at f0 and stays within 2.6–3.1 cm in every phase.
  - The sweeper's own kit error is ~0 at f0 by construction, and its bw rotation error at f0 is 9°.
- **Gradual drift: no.** The rack's bw error is flat at 0.25–1.04 cm. The sweeper's error falls while it is held
  (better visibility) and rises again when it is back in the fins.
- **Jump at an event: no score-relevant one.** The sweeper's rotation error peaks at 13–14° while the pinch closes
  (C, P_s; the hand covers the handle). It costs little: 18 frames at phase AUC 0.94–0.99.
- **Static object wandering: small, and not the loss.** Rack track wander is ≤ 0.65 cm horizontal, ≤ 0.99 cm vertical
  and ≤ 3.6° (P_o). Freezing the rack (ep11 F1) gives P_o \* +0.034 but lib +0.000.
- **Identity swap or flip: none** in tracking. The registration flip under host-scan perturbation is the L1 side
  finding.

## 2. The frame-0 error in detail [M]
- **Direction.**
  - P_o's 9.0° is almost purely a rotation about the camera's viewing axis, i.e. a lean in the image: out-of-plane
    1.2°. The handle top sits 1.4 cm left of the truth, the bristle end 0.2 cm.
  - P_s: 6.6° about the view axis plus 6.0° out of plane.
  - In the rack's frame, the truth leans 8.7° from the rack's vertical (it rests against a fin); P_o leans 15.5° and
    P_s 16.5°.
  - The error is mostly about the rack's across axis and its vertical: a sideways lean toward the next fin, plus yaw.
- **Inputs at frame 0** (`f0render.json`, z-buffered render with the rack as occluder; mocap placed in the camera by
  a fit of the P_s rack track to the mocap rack over all frames, residual 0.29 cm median):

  | pose of the sweeper | visible px | mask IoU | depth residual on visible px (median / MAD / within 1 cm) |
  |---|---|---|---|
  | truth | 1260 | 0.468 | +0.76 / 1.35 cm / 42 % |
  | P_s | 1185 | 0.508 | +0.36 / 0.54 cm / 66 % |
  | P_o (scan mesh at X\*_geom) | 1185 | 0.530 | +0.61 / 0.72 cm / 60 % |

  - The 714 px mask contains 88 % sweeper, 9 % rack and 3 % background.
  - True visible pixels inside the mask: depth +0.35 cm. Outside the mask: +2.61 cm (bleeds to the background).
  - Mask pixels that are not the true sweeper: −4.29 cm (fin edges in front).
- **Viewpoints.** The rectified camera and cam a are only 3.8 cm apart, and the head moves ≤ 1.4 cm / 2.3° over the
  rest (f0–26). The rig therefore gives no second view of the occluded part.
- **Physical priors, tested on the truth [M].**
  - Stable faces (convex-hull facets holding the centre of mass; surface centroid for the open scan) of our library_v3
    sweeper: the truth's down direction is 6.8° from the nearest one, and 70° from the scan's. The sweeper is not
    free-standing; it leans on a fin.
  - Signed penetration into the rack scan at f0, as maximum depth: truth 3.4 mm, P_s 2.4 mm, P_o 7.1 mm.
  - Neither prior pins the true lean.
- **Figures** (in this folder):
  - `ep31_f0_sweeper_mask_silhouettes.png`: rectified half-res f0 crop. Our sweeper mask is yellow and the rack mask
    cyan. The visible silhouettes are truth green, P_s magenta, P_o red. The mask misses the head between the fins and
    the right edge of the handle; both tracks lean left at the top.
  - `ep31_f0_F1_icp_vs_tracker.png`: the same crop with our library_v3 sweeper at the tracker pose (red) and at the
    F1 polished pose (cyan) against the truth (green).
  - `ep31_overlay_f0_f20_f100_f260.png`: cam a at f0, f20, f100 and f260, with each frame's kit ADD. Truth is green,
    P_s magenta, P_o red. The rack agrees in every frame; the sweeper's top leans left at the rests (f0, f20, f260) and
    agrees while it is held (f100).

## 3. The hypothesis, against the evidence
- *"The thin-wire rack gives poor depth"*: **refuted.**
  - The rack's f0 depth is within 0.36 cm of the truth, with 100 % valid pixels and mask IoU 0.93.
  - The kit-chain rack error (2.7–3.1 cm) is a rotation of the whole scene. Under any world fit that is not taken
    from the sweeper's frame 0, the rack is at 0.25–1.04 cm (bw), or at AUC 0.998–1.000 (rack0).
- *"So the static rack drifts"*: **refuted.** The rack's error is flat across phases, and its wander is ≤ 0.7 cm.
- *"The sweeper is occluded between the dividers"*: **confirmed, with a different consequence.**
  - The occlusion biases the sweeper's frame-0 pose by 9°, through an incomplete mask, fin-edge depth in the mask and
    background-biased depth on the head.
  - Because the sweeper is the scorer's rotation anchor, that one pose costs the rack 0.20–0.31 AUC (0.69–0.80 vs
    0.987–1.000 under bw).
  - Mid-episode occlusion during the strokes costs little: P_s bw sweeper 0.45 cm, AUC 0.999.
- **Mechanism status.** The tilt fits the inputs better than the truth does [M]. That it *causes* the tracker's tilt is
  [H] until F2's GPU test.

## 4. Fixes (GT-free), tests that would falsify them, eval exposure, value

### F1 — frame-0 depth-ICP polish (post-processing; CPU) [M: helps ep31, falsified as a general rule]
**Rule** (inference side; inputs are our depth0, our frame-0 masks `det_f0.npz`, library_v3 and our tracks):
- For each object at f0, back-project the valid depth inside its chosen mask.
- Run point-to-plane ICP of our mesh's camera-facing surface samples onto those points, starting from the tracker's
  pose: keep the 80 % closest pairs, ≤ 60 iterations.
- Accept only if ≥ 200 points, the change is ≤ 15° and ≤ 3 cm, and the trimmed residual drops.
- Apply the accepted change as a constant body correction to the frames before the object's own perceived onset
  (> 1 cm or > 5° from f0).
- The trimming is what removes the fin-edge pixels.
- A completed mask (adding depth-consistent pixels around the predicted silhouette) makes it worse: 7.5°. The depth
  outside the mask is biased (§2).

**Where:**
- `pipeline/refine.py` as a new step run before S2, with the polished objects logged in `pose_opt.json`.
- Or at the end of perc2's registration, so the tracker starts from the polished pose.
- perc2 already writes the frame-0 detection dump (`det_f0.npz`) and the depth cache per episode. Check that both
  exist for the eval perception runs before use.

**ep31 [M]** (`f0icp.json`; P_o track, 25 Oct masks):

| sweeper f0 pose | rotation error | anchor error | ep31 \* | ep31 lib |
|---|---|---|---|---|
| P_o (tracker) | 9.20° | 0.17 cm | 0.8351 | 0.7998 |
| F1, our mask | **3.74°** | 0.64 cm | **0.9199** | **0.9514** |
| F1, depth-completed mask | 7.46° | 0.29 cm | 0.8861 | 0.8822 |
| ORACLE: true f0 pose | 0 | 0 | 0.9628 | 0.9850 |

**20-episode public test (pre-registered in `PREREG_f0icp.md`, 23:00 UTC, before the run) [M]:**

Rows show the slot-0 object, its GT-free mask coverage, and F1's change to it (° / cm, accepted or rejected). Δ is the
reference AUC change vs mocap; A = slot 0 only, B = every object. P_r = refine-input tracks with their own masks
(primary); P_o = Phase-1 tracks with the same 25 Oct masks (beside).

| ep | slot 0 | coverage | F1 change | A lib P_r | A \* P_r | A lib P_o | B lib P_r | B \* P_r | B lib P_o |
|---|---|---|---|---|---|---|---|---|---|
| 0 | white_pot | 0.96 | 7.8 / 2.6, rej | 0 | 0 | 0 | 0 | 0 | 0 |
| 2 | white_pot | 0.90 | 8.3 / 2.5, rej | 0 | 0 | 0 | +0.0014 | 0 | +0.0030 |
| 11 | blue_cup | 0.94 | 6.4 / 0.2, acc | +0.0039 | +0.0187 | +0.0039 | +0.0037 | +0.0187 | +0.0037 |
| 12 | blue_cup | 0.97 | 9.0 / 0.3, acc | **−0.0154** | +0.0031 | −0.0163 | **−0.0852** | −0.0183 | −0.0848 |
| 13 | blue_cup | 0.94 | 18.1 / 0.7, rej | 0 | 0 | 0 | **−0.0255** | +0.0219 | −0.0245 |
| 18 | mini_sweeper | **0.51** | 4.5 / 0.3, acc | +0.0006 | −0.0070 | +0.0025 | +0.0006 | −0.0070 | +0.0025 |
| 21 | blue_cup | 0.94 | 6.1 / 0.2, acc | −0.0064 | −0.0109 | −0.0064 | +0.0623 | +0.0560 | +0.0623 |
| 22 | blue_cup | 0.92 | 5.4 / 0.4, acc | +0.0098 | +0.0172 | +0.0093 | +0.0389 | +0.0085 | +0.0389 |
| 23 | wooden_piece_1 | 0.94 | 2.8 / 0.6, acc | −0.0007 | −0.0009 | −0.0007 | −0.0007 | −0.0009 | −0.0007 |
| 24 | wooden_piece_1 | 0.99 | 1.1 / 0.2, acc | +0.0152 | +0.0128 | +0.0152 | +0.0151 | +0.0126 | +0.0151 |
| 26 | plastic_dish_rack | **0.00** | diverged, rej | 0 | 0 | 0 | +0.0028 | −0.0004 | +0.0056 |
| 27 | plastic_dish_rack | 0.97 | 2.5 / 0.3, acc | +0.0271 | +0.0253 | +0.0277 | +0.0270 | +0.0243 | +0.0276 |
| **31** | mini_sweeper | **0.52** | 7.1 / 0.5, acc | **+0.1474** | +0.0813 | **+0.1516** | +0.1472 | +0.0836 | +0.1510 |
| 39 | mini_dust_pan | 0.96 | 1.6 / 0.3, acc | +0.0151 | +0.0094 | +0.0151 | +0.0151 | +0.0094 | +0.0151 |
| 40 | mini_dust_pan | 0.96 | 2.2 / 0.3, acc | **−0.0108** | −0.0214 | −0.0108 | −0.0108 | −0.0214 | −0.0108 |
| 41 | white_pot | 0.97 | 0.8 / 0.3, acc | +0.0029 | +0.0010 | +0.0029 | +0.0029 | +0.0010 | +0.0029 |
| 42 | white_pot | 0.94 | 1.2 / 0.4, acc | −0.0044 | −0.0270 | −0.0037 | −0.0044 | −0.0270 | −0.0037 |
| 43 | white_pot | 0.94 | 4.3 / 0.7, acc | +0.0338 | −0.0211 | +0.0341 | +0.0338 | −0.0211 | +0.0341 |
| 44 | white_pot | 0.97 | 1.8 / 0.2, acc | −0.0017 | −0.0010 | −0.0017 | −0.0017 | −0.0010 | −0.0017 |
| 45 | white_pot | 0.98 | 0.3 / 0.1, acc | −0.0015 | +0.0045 | −0.0015 | −0.0015 | +0.0045 | −0.0015 |

| variant (P_r, lib) | mean Δ | w/o ep31 | non-negative | min | ep31 | pre-set reading |
|---|---|---|---|---|---|---|
| A slot 0 | +0.0107 | +0.0036 | 13/20 | −0.0154 (ep12) | +0.1474 | **FALSIFIED**: harm guard (ep12, ep40 < −0.010) |
| B every object | +0.0110 | +0.0039 | 13/20 | −0.0852 (ep12) | +0.1472 | **FALSIFIED**: harm guard (ep12, ep13) |

The \* readings lead to the same verdict: A \* mean +0.0042, w/o ep31 +0.0001, min −0.0270. On P_o the lib Δ agree with
P_r to ≤ 0.006 per episode.

Reading [M]:
- Trimmed ICP to the mask's depth is not a safe general frame-0 refiner. It turns well-observed objects by 1–9° and
  helps or hurts about equally outside ep31. ep12's blue cup is the clearest case: turned 9°, it costs −0.015, and
  with its rack also polished −0.085.
- On ep31 the gain is large, because there the tracker's input is contaminated (§2) and the scene anchor carries the
  error.

**Post-hoc variant F1g [H] (written after reading the table, so not validated).** Polish only the scorer's rotation
anchor (the first object without a symmetry axis), and only when its GT-free mask coverage is < 0.70 (`coverage_all.json`).
- On the 20 public episodes the gate opens on 3 rotation anchors:
  - ep31 sweeper 0.52: lib +0.147;
  - ep18 sweeper 0.51: lib +0.0006, \* −0.007;
  - ep26 rack 0.00: rejected by F1's own guard (divergence).
  - Every other rotation anchor has coverage ≥ 0.90. That includes the racks of ep12/13, whose ungated polish
    (variant B) did harm.
- So the public evidence for F1g is one helped episode and one neutral one: mean lib +0.0074 over 20, no episode
  worse than −0.001 lib (ep18 \* −0.007).
- **By-product:** coverage ≈ 0 flags a frame-0 mask/pose mismatch on ep0's lid and ep26's rack in the 25 Oct tracks.
  That is a GT-free screen worth handing to the ep0 diagnosis and to the eval-reference QA [H].

**Tests that would falsify F1g** (needs the owner's go-ahead; pre-register before running):
- **Reference level, fresh data.** The only fresh data is a re-run. Re-track the 20 public episodes once with a
  different seed or code and apply F1g unchanged (thresholds frozen here: coverage < 0.70, trim 80 %, ≤ 15°, ≤ 3 cm).
  - Pass: the gate opens on ep31 again with lib ≥ +0.05, and no opened episode loses more than 0.005 lib.
  - This is weak, because it re-uses the same scenes.
- **Rollout gate (decisive):** the Phase-2 cell c1 recipe for ep31 with and without F1g, seeds 42 and 43, NREP 10.
  - Falsified if the seed-mean rollout AUC vs mocap rises by less than +0.03.
  - Reference values: orcB P 0.783 ± 0.044 vs O 0.869 ± 0.047 (one seed, grasp-lock learner).
  - Also run eval 30's packed standard learner (std30 recipe) on ep31, because the packed learner differs.

### F2 — occlusion-aware registration and tracking in perc2 (`pipeline/perc2.py`) [H]: the general fix that F1 is not
- **What:**
  1. Register the confident, large objects first. Order by mask area × Grounding DINO agreement; here the rack (21.5k
     px) before the sweeper (714 px).
  2. Before registering or tracking object k, render the already-posed objects with nvdiffrast (already loaded). Set
     depth to 0 and grey out RGB wherever another object lies in front of k's predicted surface.
  3. Drop mask pixels whose depth lies > 2 cm in front of k's predicted surface.
- This is the same code change as ep11's Fix 2 (mask the other objects out of the tracker's input), so one GPU test
  covers both.
- **Why it replaces F1 as the general fix:**
  - F1 polishes frame 0 with depth alone and failed its 20-episode guard. F2 removes the contamination at the input.
  - F2 also fixes the end rest (f246–289, 8.7–10.6°): it matters to the reference, though not to the scorer's anchor.
  - It covers FoundationPose's RGB term, which F1 ignores.
- **Public test that would falsify it** (the same box as ep11 F2; ≈ $1 [E]):
  - Re-track all 20 public episodes, F1 off, P_o templates.
  - Pass if ep31 sweeper f0 rotation error ≤ 4°, ep31 lib ≥ 0.93, ep11 blue cup \* ≥ 0.95, no episode drops by more than
    0.01, and the repeat is identical.
  - Falsified if ep31's f0 error stays ≥ 7°. The tilt would then come from the incomplete mask or the background-biased
    head depth, not from the fin pixels. F2 would be dropped, and F1g (or a re-segmentation of the anchor) remains.

### F3 — start-consistent simulation geometry for the anchor (companion; mkref / FlashCHORD assets) [H, from the audit]
- **Why it belongs here:** even with a perfect reference (mocap, 0.993), the ep31 rollout loses 0.124 (orcB O 0.869).
  - The audit measured the cause: a first-step ejection of the sweeper from the rack's CoACD hulls, 11.3° / 1.07 cm
    in all 5 rollouts.
  - It acts through the same scorer anchor; fixing that one frame was worth +0.074 there.
  - F1g/F2 and F3 are two halves of one problem: the anchor's orientation at the evaluator's frame 0.
- **What:** split the rack's hulls (note 19, S120: sweeper-in-rack overlap 2.4–3.1 mm instead of 10.4–15.3 mm), or
  depenetrate the reference sweeper from the hulls by its smallest motion.
- **Falsifying test:** the audit's H31-1. Falsified if ep31's first-step sweeper rotation stays ≥ 3° or the 5-evaluation
  mean stays < 0.82.

### Tested here and dropped [M]
- F1 as a general frame-0 refiner (all objects, or slot 0 without a gate): fails its pre-registered harm guard
  (ep12 −0.015 / −0.085, ep40 −0.011, ep13 −0.026).
- Static hold of the rack (ep11 F1): lib +0.000 on ep31.
- Upright / stable-face snap: the truth is 6.8° from our mesh's nearest stable face, against P_o's 4.3° tilt error, so
  the snap would add error.
- Depenetration from the rack: P_s already penetrates less than the truth.
- Depth-completed mask: 7.5°, worse than our own mask.
- Frame-0 smoothing (ep0 F3): on ep31 lib −0.0014, because the error is constant across the rest.

### Eval exposure
The scorer takes translation from slot 0 and rotation from the first object without a symmetry axis, using the kit's
symmetry table (cups have an axis, the lid a half-turn). So any frame-0 orientation error of that object rotates the
whole scene. Rotation anchor per eval (kit roster):

| rotation anchor at frame 0 | evals | exposure to this failure |
|---|---|---|
| sweeper standing between the rack fins (rack in slot 1) | **30** | exact twin (ep31) |
| sweeper, with a dust pan | 19 | twin ep18: its sweeper mask coverage is also low (0.51), but F1 changes it by only 4.5° and ±0.007, and ep18 scores 0.91–0.96 lib: low |
| spoon (thin; the cup in slot 0 has an axis) | **32, 33** (and 35–37, spoon alone) | same mechanism class (thin anchor, partly hidden) [H]; no public spoon twin; P_gf proxies only |
| board 1 (edge-on plate) | 25 | twin ep24 (separate diagnosis) |
| dust pan alone | 38 | twin ep39/40, AUC 0.97–0.98: low |
| rack | 14, 15, 16, 28 | rack anchors are well tracked (rack bw ≤ 1 cm, 1–2°): low |
| pot / pitcher | 1, 3, 5, 6, 8, 20 | large, well-seen anchors; pot frame-0 detection decoys are ep0's F1 |
| cups only (axis + direction rule) | 10 | ep11 (separate diagnosis) |

- Note: `13-spoon.md` says the spoon's frame-0 pose sets the alignment only in evals 35–37. By the kit's code it also
  sets the scene rotation in 32 and 33, because the blue cup in slot 0 has a symmetry axis.

### Leaderboard value [E]
- **Eval 30, F1g (or F2) fixing the anchor's frame-0 tilt.**
  - The twin reference goes 0.800 → 0.951 lib (proxy), toward the oracle frame-0 ceiling of 0.985.
  - All of P → O was +0.086 in the rollout (orcB, one seed). The fix recovers ≈ 80 % of the reference gap, so
    ≈ +0.05–0.07 on the twin rollout if proportional, while F3's start transient remains.
  - LB = (0.74–1.0)/20 × (0.04–0.086) = **+0.0015 to +0.004, central ≈ +0.003**.
  - It is 0 if eval 30's reference does not carry the tilt. Check (GT-free, after the public gates): eval 30's
    sweeper mask coverage, and its frame-0 lean against its own rack.
  - Confidence is low: n = 1 public episode for F1g, and no GPU run for F2.
- **F1g/F2 + F3 together on eval 30:** up to ≈ +0.15 on the twin rollout, so **≤ +0.0075 LB** (upper bound).
- **Spoon-anchored evals 32, 33, 35–37:** unknown. Same class, no public twin [E-analogy; not added to any total].
- **The L1 side finding (registration flip of the sweeper anchor):** 0 if the host scan equals the public scan. Up to
  ≈ 0.5 × 0.7 / 20 ≈ 0.017 LB at a 50 % flip rate if it does not. Mesh session; PLAN §4 rule.

## 5. Caveats
- The F1 numbers are a CPU proxy (trimmed ICP with our meshes). The real pipeline's FoundationPose run from the
  polished pose may differ.
- F1g's gate was chosen after the 20-episode table. Its public support is ep31 alone.
- The F1 rule was developed on ep31 and then tested on 20 episodes under a pre-set rule. No fresh public holdout
  exists.
- The masks are from the 25 Oct refine run, and the Phase-1 P_o track comes from the 30 Oct code. For ep31 the
  frame-0 detection is the same proposal type (the re-proposed sweeper), but the masks were not re-dumped by Phase 1.
- The truth is placed in the camera through the rack, which is tracked to 0.3 cm. That mapping, not the sweeper,
  limits the render checks.
- The rollout values lean on one orcB seed with the grasp-lock learner, while eval 30 is packed with the standard
  learner (std30).
- Eval data were not read.
