# T-I17 c1: is the plain-MuJoCo contact gate G1 a valid stand-in for MuJoCo-Warp? No (run 1 Nov 2026, 03:04 UTC)

Rule: PREREG F-I5.16 (1)(h). Run in the collision-carve round-2 Eval-carves step to fix verify_cc2_0 B1 (c1 had been
skipped, on the false premise that the ep24 bundle was not on this machine). [M] unless marked.

## In plain words

Our contact gate G1 counts contacts and solver rows in plain MuJoCo with the training simulator's limits (512 rows,
256 contacts per world). c1 checks it on the one case where the evaluator's own engine (MuJoCo-Warp, run by
determined-wright) has given an answer: the round-2 ep24 board pieces. MuJoCo-Warp says the carved boards overflow
(16 of 16 copies) and the default boards do not (0 of 16, 416-425 rows). Plain MuJoCo says both overflow: the
carved boards in 12 of 16 copies, the default boards in 16 of 16 (688 rows at most). So **c1 fails**. G1 flags a
piece set that the evaluator's engine handles. Plain-MuJoCo row counts in this round are therefore labelled
"plain MuJoCo only". No F-I5 delivery may be called usable until G1 has run in MuJoCo-Warp.

## Verdict

| | carved r0 (57 / 77 pieces) | default r0/_default (50 / 71) | c1 needs | MuJoCo-Warp, determined-wright [R] |
|---|---|---|---|---|
| copies over 512 rows or 256 contacts | **12 / 16** | **16 / 16** | carved >= 15, default 0 | 16 / 16 vs 0 / 16 |
| max nefc (median of the copy maxima) | 2,948 (614) | 688 (632) | ratio >= 3 | 2,027 vs 416-425 |
| max ncon | 737 | 172 | | 500-670 asked (carved) |
| ratio carved / default | **4.29** (holds) | | | about 4.9 |
| **c1** | | | | **FAIL** (2 of 3 legs) |

- Carved copies reach their maximum at step 0 or 8-9. At step 0 the jittered start overlaps the tight slot
  (guest-receiver contacts only). At steps 8-9 the boards land on the table.
- Default copies peak at step 8, the landing: 64-86 guest-table plus 71-84 guest-receiver contacts. At rest they use
  256-392 rows.
- Nominal (unjittered) pose: carved 476 rows (no overflow), default 628 (overflow).

## Scene (what c1 prescribes) and identity with determined-wright's run

- **Engine and options:** `gmg/contactgate5.py` (unchanged since 88f49df): plain MuJoCo 3.17.0, sim=rl from
  `docs/research/work/15-verify/cfg_sim_rl.yaml` (sha256 695536b7...4b66, checked). Options: dt 0.01 s, Newton,
  implicitfast, pyramidal, impratio 20, 100 / 50 iterations, njmax 512, nconmax 256. Mesh geoms with condim 3 and
  friction 1.0; uniform-solid props at 0.3 kg (`simpieces.props`). The limits are applied to the counts.
- **Pieces:** `build/I/results/slot2-ep24/fi4o/r0`, read only. Carved `wooden_piece_{1,2}/piece_*.obj`; default
  `_default/...`.
- **Settle scene:** both boards free, host wooden_piece_1, guest wooden_piece_2. Table plane z = 0.600 m, gravity -z.
  2 s = 200 steps.
- **Poses:** our ep24 FlashCHORD reference at f246, i.e. our P_sel plus their constant z shifts.
  - Source: `runs/20261030-physS1-6a814df/refs/glockt/ep24/.../ref_gl_ilc.parquet` from the HF store, md5
    699fe4266a0a965aaf4472a1bfcc8828 (= their RESULT section 2).
  - Support stage md5 debb7ad950590b91738f141a7f73310b; table top 0.600 m.
  - Only the columns object_body_names, object_body_position and object_body_wxyz were read, by
    `scripts/ref24_pose.py`. It runs outside the gmg guard, which refuses `.parquet` paths. Output:
    `c1_pose_f246.json`.
- **Draws:** `default_rng(0).normal((16, 2, 6))`, positions x 0.0005 m, rotation vectors x 0.005 rad, applied as
  R_j R about the mesh origin in the world frame, on both objects. This is their `settle_p1.py` (3c7fd32) exactly.
- **Identity checks:**
  - Nominal lowest vertices are 35.19 / 30.85 mm above the table; theirs are 35.0 / 30.7 mm.
  - Over 2 s the boards drop: carved host 34.9-36.7 mm, guest 30.5-32.1 mm (theirs 3.71 / 3.23 cm mean).
  - Default host 27.6-34.3 mm, guest 30.5-33.3 mm (theirs 3.18 / 3.20 cm).
- **Why P125 (F-I4.17) could not be cited:** F-I5.16 (1)(h) allows citing it only if the scene, options and draws are
  identical. Its S1 scene differs:
  - it used our P_sel without the z shifts (the boards 1.92 mm closer along z);
  - it used our bundle's table plane;
  - it used `simphys.jitters` seed 1 on the guest only.
  P125's numbers (carved 868 rows, 3 / 16 over; default 880, 1 / 16 over) point the same way as this run.

## Consequences (rule text, F-I5.16 (1)(h))

- G1 in plain MuJoCo is recorded as weaker than MuJoCo-Warp. No F-I5 delivery is called usable before G1 has run in
  MuJoCo-Warp (FlashCHORD's environment on a box, or determined-wright). There is no F-I5 delivery in round 2, so no
  verdict changes.
- Every contact number of round 2 is plain MuJoCo only: public G1, the eval precheck's pair scenes, and eval 10's
  656-1,296 rows. Eval 10's overflow itself is established by determined-wright's and focused-pascal's FlashCHORD
  measurements (work log, 1 Nov 02:50 UTC [R]), not by ours.
- [H] Plain MuJoCo makes more contacts than MuJoCo-Warp when convex pieces land on a plane. Here that happens because
  the reference holds the boards about 3 cm up. Falsifier: rerun c1 with the pair lowered 1 mm above the table
  (their snap1 pose). If the default still overflows in plain MuJoCo at rest, the cause is not the landing.

## Files

- `c1_ep24.json`: every value; per copy the maxima, steps, contact classes, the start and end counts, and the
  end displacement.
- `c1_ep24.log`, `c1_pose_f246.json`, `launch.sha256` (two runs: the first lacked the end-state fields and gave the
  same counts).
- `scripts/`: the download script and the pose extractor.
- The driver is `build/I/fi516_c1_ep24.py`. Command:
  `GMG_MODE=dev nice -n 10 <venv>/python docs/research/mesh-2026-10-26/gmg/build/I/fi516_c1_ep24.py --pose
  <scratch>/cc2eval/c1_pose_f246.npz --out <scratch>/cc2eval/c1_ep24.json`.
- Machine: this container, 4 shared cores, 41 s. No rental, $0. No ground truth read.
