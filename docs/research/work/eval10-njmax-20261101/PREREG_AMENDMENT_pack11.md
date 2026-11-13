# PREREG amendment, 1 Nov 2026 ~11:10 UTC: pack 11 (the njmax-1024-trained eval-10 policy, evaluated at stock limits)

Written and committed BEFORE the pack-11 scoring and verdict below are computed. It amends
`PREREG.md` (086de63) of this folder, which said "DIAGNOSTIC ONLY, NEVER PACKED".

## Why the amendment
- The owner gave the go directly in keen-heisenberg's chat: "I give give you go" (09:11 UTC). Relayed to this session at
  09:12 UTC; it reached this session at 11:04 UTC.
- The proposal it answered: pack the njmax-1024-trained eval-10 policy, scored at stock limits.
- The owner's reading: the rule protects the evaluation setting, and the training buffer is a training choice, like
  FDR / VOC / D.
- The go replaces the "never packed" condition for **this one policy only**: the 512-config copy
  `results/ev10_nj/ck512/policy.safetensors` of run 20261101-e10nj-451b82d.

## Disclosure: this is NOT a blind test
- The 512-readout values of this checkpoint were already seen: n 10, mean 0.9034 vs V, 0.873 vs P (work log 05:45 UTC).
- The rule below is the standing pack-9b / pack-10 rule. It is applied to already-seen draws, so it is a standing rule,
  not a blind pre-registered test.

## Policy, draws and evaluation setting
- **Candidate:** the ck512 copy of the seed-43 checkpoint trained with `sim.njmax=1024 sim.nconmax=512`. Its stored
  resolved config (the `user.resolved_config_json` metadata inside the single .safetensors file) carries njmax 512 /
  nconmax 256 in both `sim` and `env.sim`. checkpoint_sha256 covers that whole file: weights and the stored config.
- **Draws:** the 10 "conf512" official draws of run 20261101-e10nj-451b82d, reused. They ran on the pristine kit
  evaluator (/content/v2d_clean, one run_policy_evaluation.py call per draw) loading exactly that file. Draw 1 is taken
  by position; n = 10.
- **Required checks, else INVALID:**
  - (1) the stored config of the file whose sha256 the rollouts name reads 512 / 256 in both blocks;
  - (2) the evaluator built SolverMuJoCo at njmax 512 / naconmax 256 for this file (the box's solver_check on the
    pristine tree, plus the per-draw evaluator logs where stored);
  - (3) 0 "nefc overflow" / "broadphase overflow" lines in every scored draw;
  - (4) all 10 draws scored, each naming the ck512 checkpoint_sha256.

## Rule (the standing pack-9b rule a / b / c / s, on V and on P, exactly as tools/e10v_verdict.py computes it)
- **References:**
  - V = e10v's stored V4p reference (refs/perc2e10v_glockt/ep10 of run 20261031-e10v-caf38fb);
  - P = the packed eval-10 reference, md5 1a5003d9….
- **Packed side** = the policy now in pack 10 for eval 10: the 10 official confirmation draws of run
  20261101-e10cs-50c2d90, seed 43, checkpoint ca7c4e3a….
- **Old packed draw** = pack 10's eval-10 rollout: that run's confirmation draw 1.
- **Clauses**, the same tolerances as e10v_verdict:
  - (a) new mean ≥ packed mean;
  - (b) new fail rate (RPE > 5 cm) ≤ packed fail rate;
  - (c) new median RPE ≤ packed median RPE;
  - (s) new draw 1 ≥ old packed draw − 0.05.
- **Binding pack-inclusion bar:** (new mean − packed mean) ≥ +0.02 on BOTH V and P.
- **Scoring:** both sides are re-scored together on CPU with tools/e10v_score.py, the same code and the same two
  reference files.
- **Labels:** SWAP-ELIGIBLE (every clause on both references), NO-SWAP, or INVALID. INCLUDE only if SWAP-ELIGIBLE and
  the bar holds.

## Pack 11, if INCLUDE
- Pack 11 = pack 10 (results/submissions/20261101-track3k-candidate/build_10, sha256 e1bef1e5…) with ONLY eval 10's
  rollout replaced by the conf512 draw-1 rollout. Byte diff vs pack 10: only e000010's rows, checkpoint_sha256 and
  code_commit_url; meshes identical.
- **Guard:** tools/no_oracle.py keeps refusing every non-stock-limit checkpoint and the diagnostic run names, except
  inputs tied to this one checkpoint sha256. That exception is an explicit allowlist entry citing this amendment.
- **README disclosure:** "trained with njmax 1024 / nconmax 512 (training-only); evaluated at stock 512 / 256".
- **Cost:** $0 GPU; CPU only, reusing stored draws. A fresh confirmation box (~$2) only if a required check above fails
  for a reason a re-run would fix.
