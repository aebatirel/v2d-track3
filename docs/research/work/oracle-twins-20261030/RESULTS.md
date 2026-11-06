# Oracle twins, option B: results (30 Oct 2026, read under PREREG §4 + §10)

Box 58408407 `20261030-orcB-38234d1` (RTX PRO 6000 Max-Q, California, $1.467/h), commit 38234d1, ~13:39–18:57 UTC,
ledger actual ≈ $7.80 (estimate). Grasp-lock learner, seed 42, 70M steps, NREP 10 official evaluations per arm, scored
as registered ADD-AUC vs mocap with our meshes (library_v3). Store: `runs/20261030-orcB-38234d1/results/oracle_twins/`.
Public episodes only; P = our perceived reference, O = the same pipeline with mocap object motion.

| Twin → eval | G0 ref vs mocap P / O | P rollout AUC | O rollout AUC | Δ = O − P (SE) | Class (pre-registered) |
|---|---|---|---|---|---|
| ep11 → eval 10 (cup stacking) | 0.896 / 0.969 | 0.595 ± 0.000 (10/10 < 0.70) | **0.940 ± 0.034** (min 0.872) | **+0.345 (0.011)** | **C2 perception-limited** |
| ep13 → eval 14 (hand-over, flip, rack) | 0.940 / 0.964 | 0.543 ± 0.001 | 0.544 ± 0.002 | +0.001 (0.001) | **C1 physics/learner-limited** |
| ep31 → eval 30 (sweeper, rack) | 0.822 / 0.993 | 0.783 ± 0.044 | 0.869 ± 0.047 | +0.086 (0.020) | **C5 inconclusive** (one seed) |

Secondary (R3, how copyable each reference is; sim_vs_ref against its own reference): ep11 P 0.518 vs O 0.964
(our perceived reference is far harder to track); ep13 0.556 vs 0.573 (equal); ep31 0.758 vs 0.883 (inconclusive).

## Readings
- **Eval 10 (ep11): perception-limited.** With the true cup motion, the same recipe stacks the cups (0.940); with our
  perceived motion it fails every draw (0.595, at the static floor). Our reference is only moderately off by AUC
  (0.896), but it is physically much harder to copy (R3). Consistent with the 26 Oct forensics: our reference nests the
  beige cup deeper than the cup shapes allow [M then]. Lever: make eval 10's reference physically consistent (nest
  height / interpenetration-free placement, GT-free), validated first on ep11. Upper bound of the gain if it transfers:
  Δ/20 ≈ +0.017 LB [E].
- **Eval 14 (ep13): not perception.** Even the true motion is not copied (0.544, identical to P): the left→right
  hand-over and flip are a robot/learner limit of this recipe. No reference spend for eval 14; levers are learner /
  embodiment (hand-over) only.
- **Eval 30 (ep31): inconclusive.** Δ +0.086 is inside the 0.05–0.12 band at one seed (and the learner differs from eval
  30's packed standard learner, as labelled in PREREG §5). A second seed or the standard learner would decide it.
- Priors (PREREG §4) vs results: ep11 was expected C1 → falsified (it is C2); ep13 expected C3 → it is C1; ep31 expected
  C2 or C4 → inconclusive.
