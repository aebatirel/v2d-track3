# Lift-window training starts (contact-moment training), pre-registered 2 Nov 2026 ~07:15 UTC (10:15 TRT), before any result

## Evidence [M] (GT-free, H5p7 onsets vs our reference's hold starts)
The remaining deterministic losses start ~10 frames after a grasp begins: eval 25 pieces f41 / f173 (holds from f31 /
f163), eval 30 sweeper f36–52 (hold from f42), eval 3 pot f66–68 (from f57), eval 14 after the bridge repair f27–31
(from f18). Post-release growth exists only on 14 / 16 / 32, already replaced in pack 12b, so hold-freeze does not apply
to 25 / 30 / 1 / 3 (checked 07:20 UTC, message to keen-heisenberg).

## Hypothesis [H-lift] and change
FlashCHORD draws training reset frames uniformly, so a ~20-frame grasp / lift window gets ~20 / T of the starts. Drawing a
share P = 0.3 of the sampled training resets uniformly from the windows [hold start − 5, hold start + 15] of our reference
(tools/lift_windows.py; ops/box/patch_flashchord_lift.py, training-only, inert unless FC_LIFT_WINDOWS is set; explicit
resets / every evaluation untouched; CPU-checked: unset = upstream sampling exactly) lowers the lift loss.
Falsified on the public twin if the rule below fails.

## Step 1, public test (box pfH): public ep31 (eval 30's twin), base = run 20261030-orcB-38234d1's perceived reference
Arms on one box, one commit, the grasp-lock recipe (pf-hands PREREG §2), seeds 42 / 43:
- `s`  = single-hand lock (the packed construction), stock training;
- `lw` = the same reference construction + lift-window starts (windows 20–40 on ep31, P 0.3).
Metric: registered AUC vs mocap (public evaluation only), NREP 10 of the sim_vs_ref-chosen checkpoint.
**Rule:** lw passes if the mean over seeds of the paired ΔAUC (lw − s) ≥ +0.02 and no seed's Δ < −0.03.
Reported: sim_vs_ref plain / symmetric, error onsets around the lift.

## Step 2 (only if step 1 passes; a new PREREG addendum before launch)
Eval 3 and eval 14 (grasp-lock, the packed / pack-12b reference reused, arm `plw`), and evals 25 / 30 (standard learner)
if the job supports them, 2 seeds, swap rule + ≥ +0.02 bar, 10 fresh draws.

## Cost [E]
Step 1: 2 pairs per seed wave ≈ 3 h ≈ $4–4.5. Step 2 ≈ $10–15. Budget left ≈ $70 of $102.

## Addendum A (2 Nov ~10:15 UTC, written after pfH seed 42 only — lw 0.730 vs s 0.589 — and before seed 43; the step-1
## rule above is unchanged and still decides whether step 2 runs)
Step 2 box pfI (launched only if step 1 PASSES): evals **3, 14, 32**, arm `plw` = the policy's own current reference
reused byte for byte + lift-window starts (windows from tools/lift_windows.py on the base: eval 3 30–50,52–72; eval 14
13–50,73–93; eval 32 from its base), P 0.3, current recipe, stock limits, seeds 42 / 43.
- References: eval 3 = packed_refs.json's; evals 14 / 32 = pack 12b's (docs/research/work/pf-lift-20261102/packed_refs_12b.json,
  runs 20261101-pfC-f38b324 / pfD-f38b324, refs/pfss43_glockt).
- Control = the policy on the board: eval 3 the H5p7 draws (packed); evals 14 / 32 the pack-12b policies' own 10
  confirmation draws (PACKED_DRAWS_EP14/32), old draw = pack 12b's row (conf draw 1).
- Per episode: seed choice, training-box gate (> the control mean), 10 fresh official draws, pack-9b swap rule vs the
  control on the episode's own reference, inclusion bar ≥ +0.02. Not adopted on any episode if step 1 fails.
Evals 25 / 30 (standard learner) are not in this box (the job supports grasp-lock episodes only).
Cost [E]: 3 pairs per seed (waves 2 + 1) ≈ 5 h + confirmations ≈ $7–8.

## Addendum B (2 Nov ~12:55 UTC; owner via keen-heisenberg: scale the lift windows to every episode losing at a
## lift / grasp; written before any eval lift result — pfI has not started training yet)
Same rule as addendum A (seed choice, training-box gate > the board policy's mean, 10 fresh official draws, pack-9b swap
rule on the episode's own reference vs the board policy's draws, inclusion bar ≥ +0.02). Order by expected gain = gap ×
share of H5p7 draws whose onset is at a lift (≤ 15 frames after a hold start) [M, step-2 timelines]:
eval 25 (0.122 × 10/10), 30 (0.103 × 6/10), 28 (0.081 × ~5/10), 20 (0.107 × ~3/10), 1 (0.088, mid-carry; lowest
confidence), 15 (0.094 × 2/10). Eval 33 is out (its loss is the f91 guard re-acquisition, not a lift).
- Box pfJ (grasp lock, arm plw on the packed reference, packed_refs.json): evals 20 and 15, seeds 42 / 43.
- Standard-learner episodes (25, 30, 28, 1): the same lift-window starts in the std recipe (hard_ab.sh path, packed base
  reference byte copy), 2 seeds each, run after this job path is built and CPU/mock-checked; a further addendum names the
  exact job before launch.
- Packs go on top of pack 12c (sha 3542f8e5…, the board's best pose pack; not 12d).
