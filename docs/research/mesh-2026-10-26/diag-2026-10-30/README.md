# Diagnosis 2026-10-30: SAM 3D placement and the mini sweeper

Workflow `wf_f944d682-4b3` (4 agents: two investigators, two adversarial verifiers), 02:53–09:06 UTC, CPU only.
Code version: repo HEAD 9513488 + scratchpad scripts copied here. Full agent returns: `workflow-result.json`.
Scan use: SAM placement 12 pre-registered mesh_metric scorings (`sam-placement/prereg.txt`), its verifier 0;
sweeper 5 full evaluations + 7 registration-only runs (`sweeper/scorings.log`), its verifier 8 runs
(`sweeper_verify/scorings.log`). No mesh was chosen for a submission from these numbers.

Labels: [D] measured against the public scan (diagnostic), [M] measured without the scan, [E] estimate, [H] hypothesis.

## SAM 3D: why the overlay looks off
- SAM 3D shapes are mostly fine; the page overlay is drawn correctly (scan display alignment <= 6.1 deg / 4.5 mm).
- The error is our placement step `gen/sim3_fit.py`: a scale-free trimmed Sim(3) ICP to one-sided partial observed
  points. Its objective is biased: our wrong placement scores lower than the scan-ideal one on 17/20 meshes [D].
  - Translation is the largest visible error: blue cup 32/21 mm along its axis (a local minimum: the ideal scores
    better), beige cup 21-23, pitcher 15-33, boards 24-30, rack 18 mm [D]. The verifier shows the exact numbers for
    pitcher, rack and lid depend on which registration defines "ideal" (pitcher 13-35 mm).
  - Size is within ±5 % on 18/20. Board 1's -15 % and 18 deg came from the broken ep23 board-1 track (identity swap,
    16 % coverage), not from the objective: refitting with ep24 points gives +4.5/+0.6 % and <= 1.7 deg [D].
  - Flips: boards and sweeper are near-symmetric under a 180-deg turn about their long axis; flip calls are coin
    tosses (scan-registration gap 0.004-0.017 mm). Cup roll is unobservable and costs nothing in the kit.
  - Lid and sweeper s42 "size" is SHAPE. **Correction (12:10 UTC, owner's point):** the lid's error is not a
    single-view stretch. SAM 3D was given ep2 k321, where the lid rests on the pot, and it generated a whole pot with
    a lid on top (render `white_pot_lid_s42.png` in the scratchpad diag folder). The pot body under the lid explains
    diameter x0.7 and thickness x1.6. Generation must know the pot and lid are separate objects (frame choice, joint
    masks, exclusion of the other object's observed space). The sweeper s42 stretch (edge-on crop) stands.
- SAM 3D's own layout (rotation/translation) was never saved (`with_layout_postprocess=False`); its saved scale is in
  MoGe-on-crop units (2.1-6.5x metric), unusable as metric scale.
- Fixes tried (GT-free in the sense that no scan is read at fit time):
  - `vis` (visibility-aware objective): worse, flips the lid upside down.
  - `lib` (Sim(3) of the raw SAM mesh onto our library_v3 surface): best. Kit-like ADD median 25.9 -> 14.3 mm
    (verifier's reimplementation, 3 seeds) [D]; blue cup 30 -> 5 mm. Still worse than library_v3's own pose on lid,
    pitcher, beige cup, boards, sweeper; better only on pot, blue cup, dust pan.
  - **Provenance caveat (verifier):** `meshes/library_v3/*` is on `ops/provenance/denylist.json` (fused along
    scan-templated tracks with scans as --others), and the obs_all points used it as --roi/--others. So `lib` is only
    as compliant as the current submission. A clean version would register to library_v5.
  - `lib` and `lib_gated` were chosen after seeing [D] numbers for six variants (post hoc). Only `lib_vis` was
    pre-registered and kit-scored.
- Pixal3D-MV (generated in our frame, no fit) places much better: median centroid offset 5.4 mm, 7/10 <= 10 mm.
  Hunyuan3D-2.1 fitted the same way fails like SAM, so the fault is our registration, not SAM.

## Mini sweeper
- Real object: ring + head + 11 cm bristle fan, 3 marker balls (two +x, one -x). Near-symmetric under 180 deg about
  its long axis (scan vs its turned self 0.93-1.15 mm mean); only the balls break it.
- The kit does not declare the sweeper symmetric, so registration must tell the two fits apart by the balls.
  library_v3's margin is -0.022 to 0.09 mm (scan itself 0.31-0.39) -> flips 3/30 seeds (~10 % of eval pairs [E]).
  Whether eval 30's own seed flips depends on how the reference scan is decimated (flips vs budgeted scan, not vs raw).
- Root cause (verifier control): library_v3 lost the ball bumps (its surface stops 6.6-8.7 mm short of the observed
  ball edges). C0 = symmetric body without balls flips 9/30; C1 = library_v3 + the two observed +x balls flips 0/30
  (min margin 0.017 mm); M2 (symmetric + balls) 0/30 (min 0.068); P1 part program 0/30 (min 0.092) [D].
- Generators were fed an edge-on crop (ep31 k270): fan width invisible -> "brush on a stick" (width/length 0.19-0.51
  vs 0.80). crops.py rejected the face-on frames because of the hand-on-object rule.
- ep18 observed points were built with `hands: null`: 25 % of points are a blob attached to the ring (a gripping hand
  [H]).
- Candidates [D] (CD-O / ADD median / flips): library_v3 0.317 / 5.2 / 3 of 30; M2 0.283 / 3.4 / 0; M2b 0.291 / 4.1 / 0
  (not watertight); P1 0.2225 / 3.3 / 0; P1v0 0.413 / 3.6 / 0.
  - **Leak:** P1's mid-plane and ring rules were changed after a scan comparison; the 7 mm ball radius and head band
    used in P1, P1v0 and M2 match scan dimensions computed before the builds (`sweeper/scan_parts.json`). So P1's
    0.2225 is optimistic and P1v0 is not a clean baseline. The flip result (balls fix flips) does not depend on it.
- Meshes in `sweeper/meshes/` are diagnostic, not submission candidates until rebuilt with frozen, scan-free rules.

## What follows (hypotheses with falsifiers)
- Register generated meshes onto a compliant reference surface (library_v5 or our own shells), not raw points.
  Falsified if cup/pitcher kit ADD does not fall below 10 mm on new episodes.
- Sweeper: library mesh + observed balls at a free-fit radius, body optionally symmetric. Falsified by any flip over
  30 seeds on both reference decimations.
- Face-on, hand-masked crop rule for generators: width/length >= 0.6 [H]; falsified if below on one GPU generation.
- Save SAM 3D layout rotation (GPU re-run, about $1 [E]); falsified if median error > 10 deg after mapping to our frame.
