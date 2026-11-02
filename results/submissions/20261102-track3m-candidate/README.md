# Track 3 pack-12 candidate, 2 Nov 2026 — pack 11 with evals 14 and 32 retrained on guard-bridged references (KURSAD)

**NOT UPLOADED from this session.** The uploader session (keen-heisenberg) uploads on the owner's word. Pack 11 stays on
the boards as the fallback. `build_12a_ep14only/` is the earlier eval-14-only build (superseded, kept).

## Record
- File: `build_12/track3_submission.parquet`, 9,120 rows,
  sha256 `7b0cd7df57cffb9623602329f5ad825a36819a759efc67b0e295770684ef072a`.
- CD-O file: `build_12/track3_submission.cd-o.parquet` (kit offline derivation; rows identical to pack 11's: meshes
  unchanged), sha256 `ab733205a34d…`.
- Code commit on every row: https://github.com/aebatirel/v2d-track3/commit/ab444c0033dc60733e64bfbc67b3d8b62d5f1417
  (branch claude/perfect-following-20261101; holds tools/guard_bridge.py, ops/jobs/pf_arms.sh, tools/pf_verdict.py,
  tools/pack_swap_rows.py).
- Built on CPU by `tools/pack_swap_rows.py` (exact row-level swap). Checks [M]:
  - only e000014 (316 rows) and e000032 (518 rows) pose columns + checkpoint_sha256 differ from pack 11;
    code_commit_url changes on every row; mesh payloads and evaluator / packer / uploader hashes identical;
  - each rollout's flash_chord stamps (checkpoint, eval_code b1b3ebe3…, eval_script 160d24f5…) match pack 11's rows;
  - kit offline validation pass; CD-O rows changed 0;
  - no_oracle pass on both rollouts, their reference paths and both checkpoints (stock sim limits 512 / 256).
- Self-test of the tool: a pure repack with pack 11's commit URL equals pack 11 in content (pandas `equals`).

## Content (18 episodes identical in content to pack 11)
| eval | run / seed | checkpoint sha256 | rollout = confirmation draw 1 | draw 1 sim_vs_ref vs P / own ref |
|---|---|---|---|---|
| 14 | 20261101-pfC-f38b324, s43 | 9da879d9c0e8ecdeb6dd08c69b901ac34262f8770db142defcc4e45de21493e8 | results/pf_arms/conf_ep14_s/r1 | 0.882 / 0.895 |
| 32 | 20261101-pfD-f38b324, s43 | 9a2c2f7ccf422b1890a77df461fd804049c6cbcf3fa5a34640baf4b8ed1f87ce | results/pf_arms/conf_ep32_s/r1 | 0.876 / 0.900 |
Policies in the store at `runs/<run>/results/pfss43_glock_public/ep<N>/best/policy.safetensors`: the packed grasp-lock
recipe (70,004,736 steps) and single-hand construction, trained on each episode's own perceived reference with the
perception's TRACK_GUARD drift bridged (tools/guard_bridge.py; eval 14 f37–45, eval 32 f21–33 where the cup had flipped
upside down). GT-free; pre-registered in docs/research/work/pf-bridge-20261101/PREREG.md.

## Why (the standing swap rule + inclusion bar) [M]
docs/research/work/pf-bridge-20261101/results/verdict_ep{14,32}_s_cpu.json (10 fresh official draws each, pristine evaluator,
rc 0, 0 overflow lines; scored with tools/dr_score.py against both the packed reference P and the bridged reference B).
| eval | mean vs B: cand / packed | mean vs P: cand / packed | fails (RPE > 5 cm, vs B) | inclusion gain (B) |
|---|---|---|---|---|
| 14 | **0.875** / 0.706 | **0.861** / 0.727 | 1 / 10 vs 4 / 10 | +0.169 |
| 32 | **0.890** / 0.851 | **0.867** / 0.852 | 0 / 10 vs 4 / 10 | +0.040 |
Also passed but not included: eval 33 (gain +0.0196 < +0.02). NO-SWAP: evals 14 / 16 two-hand, eval 15 two-hand (clause c).

## Board expectation [E]
The board scores the submitted trajectories as they are. Pack 11's eval-14 rollout is pack 6's lucky good-mode draw
(0.909 vs P) and its eval-32 rollout 0.866 vs P; the new draws 1 score 0.882 and 0.876 vs P. So on the stored-trajectory
board the change is small and may be slightly negative for eval 14 (one draw each; vs ground truth unknown). The expected
gain is real on re-runs (+0.13 / +0.015 mean on P). The owner decides.
