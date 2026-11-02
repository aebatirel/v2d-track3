# Tier B collision retrains + eval-1 reseed — PRE-REGISTRATION (2 Nov 2026 ~20:21 UTC, before any box)

Owner (via keen-heisenberg, 20:13 UTC, after the top-up to $127.97): "go crazy, let's win this"; this lane ≤ $45, stop if
credit < $15. Coordinator's task: retrain evals 20 / 28 / 30 / 1 with the 13f meshes as collision meshes where the shape
changed (pitcher 20, rack 28 / 30, sweeper 30), contact budget first, 2 seeds, usual swap rule + ≥ +0.02 on 10 fresh draws;
passing → pack 14 on 13f (fa1e31f5…).

## GROUND-TRUTH FLAG
The Tier B shapes were selected by CD-O against the organisers' public object scans (meshes/tierB_collision/README.md).
In arms pm / sm they are collision geometry in training AND rollouts, so those trajectories depend on GT-selected
geometry. Covered by the owner's approval of the tier ("Okay I give you permission for all", 19:00 UTC) and the
coordinator's explicit task; labelled here so no one mistakes these rollouts for GT-free ones. Arm s0 (eval 1) is GT-free.

## Geometry [M, CPU]
Tier B vs library_v3, in our template frame (transform none): pitcher centroid −14 mm (z), Chamfer mean 8 mm / p95 25 mm;
rack centroid ~13 mm, mean 5–7 mm / p95 16 mm; sweeper 3 mm / p95 8 mm. Pitcher decimated 400k → 20k faces for
collision (vs source Chamfer mean 1.4 mm). Grasp references were built on the old shapes; the policy must adapt.

## Arms (ops/jobs/pf_arms.sh at the launch commit; seeds 42 / 43 unless stated)
| box | eval | arm | what changes vs the board recipe | control (board policy's own draws) / old draw |
|---|---|---|---|---|
| pfN | 20 | pm | grasp lock on the packed reference + lift windows (= the pack-13 recipe, plw) with the pitcher's collision MESH file replaced in the reference's asset copy (URDF inertia and support feet kept) | pfJ conf draws (1e08b92f…) / pfJ conf draw 1 |
| pfO | 28 | sm | standard learner (std recipe, packed base byte copy, no lift) with /content/assets built from library_v3 + Tier B rack | H5p7 / pack 6 draw |
| pfP | 30 | sm | the same with Tier B sweeper + rack | H5p7 / pack 6 draw |
| pfQ | 1 | s0 | plain reseed (seeds 44 / 45) of the board std recipe with ev01 pieces | h5e1 draws (5625b86a…) / e1conf2 draw 1 |
Table: docs/research/work/pf-mesh-20261102/packed_refs_13f.json (= packed_refs.json with the 13f board policies of evals
1 and 20). Board rows checked equal to the old draws above (pose max |diff| 0.0) [M].

## Contact budget (before any training; pm / sm)
One official draw of the BOARD checkpoint with the new collision (pristine evaluator). The episode is REFUSED (no
training) if its eval log has any "overflow - please" line or the draw gives no rollout. Its sim_vs_ref is logged
(zero-shot effect of the collision change; information only).

## Rule (unchanged pack-9b rule as in pf-lift addendum A; tools/pf_verdict.py)
Seed choice (higher box mean; within 0.005 the lower sd), training-box gate (chosen mean > the control mean), 10 fresh
official draws on the pristine evaluator, swap iff a (mean ≥ control) / b (fails ≤) / c (median RPE ≤) / s (draw 1 ≥ old
− 0.05), included iff gain ≥ +0.02. Passing episodes → pack 14 on 13f; one upload by keen-heisenberg.

## Not in this batch
S2 (needs references rebuilt from perception; rebuilt references lost to packed ones today, eval 16: 0.72–0.79 vs 0.85);
the 13f blue cup / dust pan as collision (not asked); the spoon anchor (planned, not run).
Cost [E]: 4 boxes × ~4–4.5 h × ~$1.4/h ≈ $24.

## Addendum 1 (2 Nov 20:28 UTC, before any result; coordinator's message of 20:18 crossed the launch)
- **Eval 1 dropped** ("skip eval 1": plain reseed, low value): pfQ destroyed in setup at ~20:24 UTC (no result).
- **Eval 14 added**, arm **p0m** (ops/jobs/pf_arms.sh): the board policy's own reference (pack 12b / 13f: run
  20261101-pfC-f38b324, bridged reference refs/pfss43_glockt, table docs/research/work/pf-lift-20261102/packed_refs_12b.json)
  reused byte for byte, grasp-lock recipe as the board's (single-hand construction already in the reference; no lift
  windows: lift failed eval 14's fresh draws today), with the collision MESH files of blue_cup (13f Tier B+ cup, decimated
  400k → 20k faces, Chamfer 0.9 mm to source) and plastic_dish_rack (Tier B) replaced in its asset copy refs/sf/ep14/assets.
  Control = pfC's 10 confirmation draws (9da879d9…, 0.875 vs P); old = pfC conf draw 1 (= the 13f row, checked). Same
  zero-shot contact check, rule and bar. Box pfR.
