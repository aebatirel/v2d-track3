# Evaluator-gap test — PRE-REGISTRATION (3 Nov 2026 ~00:40 UTC, before any draw)

Coordinator (keen-heisenberg, 00:35 UTC): GO for the ≈ $1 test; it decides whether training-box gates can be trusted.

## Evidence [M]
Box mean → fresh official mean (pristine evaluator): eval 14 plw s42 0.923 → 0.826 and eval 30 sm s42 0.938 → 0.768
(gaps); eval 20 plw s43 0.921 → 0.926 and eval 14 p0m s43 0.946 → 0.933 (no gap). Box draws run in the patched training
tree (ops/box/patch_flashchord*.py; the job's FC_* env exported in the evaluating process) with the repo's
scripts/evaluate_policy.py; fresh draws run the kit's examples/run_policy_evaluation.py on a clean worktree.
Checkpoint VOC scale (metadata): eval 30 sm 0.0; the three grasp-lock checkpoints 0.1 → VOC alone does not separate gap
from no gap.

## Run (ops/jobs/pf_evalgap.sh, one box)
Checkpoints: K30 = eval 30 sm s42 (run 20261102-pfP2-b0b4a31, Tier B sweeper + rack collision, as trained); K14 = eval 14
plw s42 (run 20261102-pfI-6c80007; library_v3 collision). Each with its own reference (the table's, md5-checked) and asset
copy at the paths its config names, as during its box draws. Per checkpoint, 10 rounds, each round one draw of:
- A = the training-box path exactly: patched tree (patch_flashchord.py, _fdr, _voc, _lift), repo scripts/evaluate_policy.py,
  env as in that job's evaluating process (K30: FC_FDR_OBJ=1 FC_FDR_TIPS=1 FC_VOC_INERTIA=1 FC_IMMEDIATE_FIRST_FRAME=0.25;
  K14: FC_FDR_OBJ=1 FC_FDR_TIPS=1 FC_VOC_INERTIA=1);
- B = the pristine path (kit run_policy_evaluation.py, clean worktree), as the confirmations;
- C = the patched tree and repo script with every switch off (FC_VOC_INERTIA=0, no other FC_* set).
Scored by pipeline/qa.py (sim_vs_ref vs the rollout's own reference). The job also logs the diff between the kit's and the
repo's evaluate_policy.py and `git status` of both trees.

## Reading rule
Per checkpoint: gap = mean(A) − mean(B).
- REPRODUCED iff gap ≥ 0.05 and Welch t ≥ 2; then: C − B < 0.02 → the env-switched patches cause it; A − C < 0.02 and
  C − B ≥ 0.05 → the tree / script (code present regardless of env) causes it; otherwise mixed.
- NOT REPRODUCED iff |gap| < 0.02 (then the earlier gaps are draw-to-draw / host variance [H]).
Box gates are called trustworthy iff neither checkpoint reproduces a gap. Whatever the outcome, fresh-draw confirmation
stays mandatory for any swap.
Cost [E]: ≈ 60 draws + setup ≈ 45 min ≈ $1.2.

## RESULT (3 Nov 01:21 UTC, box 20261103-pfgA-85c1626, rc 0, 43 min) [M]
| checkpoint | A box path | B pristine | C patched, switches off | gap A − B | reading |
|---|---|---|---|---|---|
| K30 eval 30 sm s42 | 0.935 ± 0.011 | 0.926 ± 0.041 (min 0.811) | 0.930 ± 0.025 | +0.009 (t 0.7) | NOT REPRODUCED |
| K14 eval 14 plw s42 | 0.925 ± 0.034 (min 0.844) | 0.937 ± 0.011 | 0.938 ± 0.011 | −0.012 (t −1.1) | NOT REPRODUCED |
Kit and repo evaluate_policy.py are identical (0 diff lines). By the rule: box gates are trustworthy (no evaluator effect).
**Beyond the rule:** the same pristine evaluator gives these checkpoints 0.926 / 0.937 here, while their confirmations on
their own training boxes gave 0.768 (pfP2, India WS) / 0.826 (pfI, Croatia Max-Q). So the earlier low fresh means are
specific to those boxes / runs, not to the evaluator code. [H] host- or run-dependent simulation outcomes (GPU / driver /
state), unexplained. The pre-registered NO-SWAP verdicts for eval 30 sm and eval 14 plw STAND (a re-test chosen after a
failure would be a forking path); a future protocol could pre-register confirmation on a second host.
