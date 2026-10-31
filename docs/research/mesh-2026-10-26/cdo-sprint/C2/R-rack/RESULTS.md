# C2 track R (plastic_dish_rack): results

Stage 1 (sections 1-4) written 2026-10-31 ~21:25 UTC, after the GT-free pick and **before any scoring** (pushed in `8d53a60`); sections 5-9 added after the scoring and the guard. Pre-registration:
`PREREG.md` (commit `01c25d2`, amendment A1 in `945baa5`). Step log: `NOTES.md`.

Labels: [M] measured without ground truth; [D] diagnostic scored against public ground truth; [E] estimate;
[H] hypothesis. `SCR` = `/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad`.

## 1. Runs (CPU, local, $0; one Vast box created and destroyed unused, ~$0.02)

| What | Command / machine | Output | Code |
|---|---|---|---|
| inputs | C0b store run `mesh-20261031-c0b-00e8584` pass-B rack points, markers, params (T = t0_C0b 4.559 mm); cleaned by `scripts/clean_pts.py` (A1) | `SCR/cdo_c2r/inA1` (sha256 in `results/inputs_STAGED.json`) | 945baa5 |
| builds + fidelity + checks + pick | `bash scripts/c2r_build.sh SCR/cdo_c2r/inA1 SCR/cdo_c2r/runA1 SCR/kit/v2d_submission_kit 2`, this VM, nice 10, 19:55-21:20 UTC | `SCR/cdo_c2r/runA1`; copies in `results/` | 945baa5 |

- 8 runs OK (base, E, K, Q, EK, EQ, KQ, EKQ), 96 meshes, 96 fidelity values, 96 checks.
- Exclusions: 2 raw meshes not watertight (`EKQ/joint_joint`, `Q/ep31_full`); no budget failure; 94 eligible.
- Every run put episodes 12, 13, 27 into its joint (JOINT_TOL), as C0 did.

## 2. The pick [M]

| Option set | best mesh | fidelity sum (mm) | its joint_nomk |
|---|---|---|---|
| base | ep12_nomk | 5.533 | 5.620 |
| E | ep12_nomk | 5.538 | 5.617 |
| **K** | **ep12_nomk** | **5.483** | 5.559 |
| Q | ep12_nomk | 5.560 | 5.565 |
| EK | ep12_nomk | 5.485 | 5.560 |
| EQ | joint_joint_nomk | 5.556 | 5.556 |
| KQ | joint_joint_nomk | 5.488 | 5.488 |
| EKQ | joint_joint_nomk | 5.485 | 5.485 |

- **Pick: `K/ep12_nomk`** (peg section aspect fitted; per-episode ep12 fit; no marker balls): fidelity 5.483 mm
  (obs->mesh 1.949, mesh->obs 3.534), 1836 faces raw, watertight, kit budget unchanged (1836 faces).
- **Gate: pass** (the pick has a new part). Best base mesh: `base/ep12_nomk` 5.533 mm, so the pick improves fidelity
  by 0.050 mm.
- **Committed mesh:** `meshes/plastic_dish_rack_c2r_K_ep12_nomk.glb`, sha256
  `92d9fed04f938f1859f4bcbf488babee0dd4582ee71d8e08aa1c9ecb53703966`, sha1[:16] `7f4eab701769d264`; build record
  `meshes/plastic_dish_rack_c2r_K_ep12.build.json`. Full table: `results/fidelity_table.jsonl`, `results/selection.json`.
- Fitted values of the pick: peg rows kappa 0.956 (front row) and 1.606 (back row); outline s1 = 0; cup holder linear
  (no Q); T 4.559 mm (C0b chain); s0 = T.

## 3. GT-free predictions (section 9)

| Prediction | Result [M] | Verdict |
|---|---|---|
| E: s1e >= 0.2 on the joint (falsified if < 0.1) | joint s1e 0.082 (ep12 0.144, ep13 0.120, ep26 0.000) | falsified |
| K: kappa > 1.2 on both rows (falsified if <= 1.0 on either) | joint 1.43 / 1.57; pick (ep12) 0.956 / 1.606 | holds on the joint; falsified for the picked ep12 fit (front row 0.956) |
| Q: abs(gx) or abs(gy) > 0.5 /m | joint gx 0.44, gy -0.77 | holds |
| pick improves fidelity over the base pick by >= 0.05 mm | 5.533 -> 5.483 (0.050) | holds (at the threshold) |

## 4. Deviations and failures (before scoring)

1. **A1 (dated amendment, inputs):** C0b's pass-B rack points carried 1-37 % static clutter; they were cleaned by
   `clean_pts.py` before the builds (PREREG section 11). Without A1, C0b's own rack builds had cup tops of 82-320 mm
   and fidelity 33-115 mm.
2. **Machine:** the box created at 19:35 UTC for the uncleaned inputs (Vast 58571056) never started (status
   created/stopped, empty log); it was destroyed at ~19:56 UTC and is gone from `vast show`. Ledger: planned $0.50,
   actual $0.02 [E]. All builds ran locally, as A1 states.
3. **Dry-run overrides** `C2R_EPS` / `C2R_SETS` were added to `c2r_build.sh` (unused in the real run; its log has no
   DRY line). A local dry run on `obs_all` was refused by the gmg guard (refused folder) and was not circumvented.
4. `resid_diag.py`: the matplotlib map block was removed (the venv has none); `rmap.py` draws the maps.
5. The diagnosis (PREREG section 2) used `obs_all` (library_v3 ROI / carving); builds and the pick used only the
   cleaned C0b points.

## 5. Scoring [D] (once, 21:21 UTC, after the pick was pushed in `8d53a60`)

`scripts/score_c2r.py meshes/plastic_dish_rack_c2r_K_ep12_nomk.glb c2r/rack/K_ep12_nomk results/score.jsonl`
(one `mesh_metric.py run`, 7 seeds, 68 s; no earlier record of sha1 `7f4eab701769d264` existed).

| Mesh | CD-O eval (cm) | CD-O all | ADD med (mm) | ADD eval / max | flips | amb (mm) |
|---|---|---|---|---|---|---|
| library_v3 [D, earlier record] | 0.55506 | 0.5551 | 5.79 | 5.99 / 6.62 | 0/7 | |
| C0 prim joint (pack 9a) [D, earlier record] | 0.45604 | 0.4550 | 5.63 | 5.37 / 6.08 | 0/7 | |
| C0b rack pick (C0b PUBLIC_RESULTS, uncleaned points) | 1.6324 | | 31.24 | | 0 | |
| **C2/R pick K/ep12_nomk** | **0.4413** | 0.4430 | **6.56** | 6.65 / 7.64 | **0/7** | 11.8 |

- **WIN: no.** CD-O 0.4413 > 0.43604 (C0 - 0.02). ADD med 6.56 <= 7.79 passes; flips 0 passes.
- vs C0: -0.0147 cm; vs library_v3: -0.1138 cm. Board effect if it shipped on the 5 rack pairs [E]: 5 x -0.0147 / 36 =
  -0.0020 cm (not shipped: no WIN).
- **H-R: falsified** (not <= 0.436; the strong claim <= 0.40 fails too).
- What the number mixes: the C0b replacements (T 4.56 mm, s0 >= T, no balls in the pick), the A1 point cleaning and the
  K option. Only fidelity separates them (K vs base 5.483 vs 5.533 mm; C0's mesh on the same cleaned points 5.536 mm).
  The C2/R base mesh was not scored (one scoring per track).

## 6. AUC guard [D] (C0's rule; 5 single runs, 21:22-21:24 UTC; base runs reused, all reuse checks passed)

`scripts/check_base_c2r.py` (reuse checks: base meshes, tracks, score_registered 6a4cd60a0d26e3f8, kit track3_pose,
staged inputs, base JSONs: all true), `scripts/run_auc_guard_c2r.sh`, `scripts/guard_eval_c2r.py` ->
`results/guard_result_c2r.json`; run JSONs in `results/auc/`.

| Twin | dAUC | dMPPE cm | dRPE cm | rack AUC base -> swap |
|---|---|---|---|---|
| 12 | -0.0076 | +0.152 | +0.122 | 0.9997 -> 0.9665 |
| 13 | +0.0078 | -0.308 | -0.141 | 0.9882 -> 1.0000 |
| 26 | -0.0048 | +0.146 | +0.259 | 0.9937 -> 0.9937 |
| 27 | +0.0169 | -0.173 | -0.129 | 1.0 -> 1.0 |
| 31 | +0.0612 | -0.243 | -0.301 | 0.6879 -> 0.8103 |
| **mean / min** | **+0.0147 / -0.0076** | **-0.086** | **-0.038** | |

- **Guard: PASS** (mean dAUC >= -0.005, min >= -0.02, mean dMPPE and dRPE <= +0.2 cm). dSP-SR and dMP-SR 0.
  For comparison C0's rack: +0.0158 / -0.0092 [D].

## 7. Adoption

**Not adopted** (PREREG section 8 needs WIN and guard PASS; WIN fails on CD-O). Pack 9a keeps the C0 rack.

## 8. GT-free post-pick diagnostic (reported only)

`scripts/free_diag.py` on the cleaned points, pick vs the base run's best (both ep12 nomk) [M]: model peg / basin
surface in seen-empty voxels in a majority of episodes 6.2 % -> 2.7 % (any episode 25.8 % -> 22.1 %); other regions
unchanged within 0.5 %. Files: `results/free_pick_K_ep12_nomk.json`, `results/free_base_ep12_nomk.json`.

## 9. Cost

$0.02 [E] (one Vast instance created and destroyed unused); everything else local CPU, $0. Scorings: 1. Guard runs: 5
(+ 5 reused base runs).
