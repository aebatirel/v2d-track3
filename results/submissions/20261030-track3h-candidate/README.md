# Track 3 pack-8 candidate, 30 Oct 2026 — pack 7 + a fresh official eval-1 rollout

**NOT UPLOADED. Uploading is the owner's decision.**

- `track3_submission.parquet`: 9,120 rows, 1388405 bytes, sha256 `f2bf0441e05711df42ee333ac7b3b8c1c826d9a161844376fa6e453076b0aa48`, 0 mesh warnings.
- Built on box `20261030-e1conf2-d41382e` (58370419, RTX PRO 6000 WS Ontario) by `ops/jobs/h5_reeval.sh` →
  `pack_eval.sh` → `submit_pack.sh`, code https://github.com/aebatirel/v2d-track3/commit/d41382e8b5fe8982ba06173231ddee29ae7059ba.
- **Content:** pack 7's 19 rollouts kept by checkpoint sha256 (18 from pack 6, eval 33 from c33B draw 1) plus ONE
  fresh official rollout of eval 1 (draw 1, chosen by position) from the carved seed-43 policy
  (`runs/20261030-c01s43-328139c/runs/perc2mcks/ep1-s43/policy_250003456.safetensors`, sha256 5625b86a…).
  - Eval 1 was trained and evaluated with the ev01 placement carve (white_pot / lid collision copies, 53 / 107 pieces;
    `results/final_eval/assets_md5.txt` on the box). Only eval 1 was evaluated on this box (EVAL_ONLY guard), so the
    carved pot reached no other episode. Submitted meshes are unchanged (library_v3, v3x for eval 8).
- **Checked (CPU, against pack 7):** pose rows differ only for eval 1 (670 rows) and its checkpoint hash; the commit URL
  differs on all rows; `object_mesh_b64` and the eval script / eval code / packer / uploader hashes are identical.

## Why (pre-registered rule, work log 30 Oct 06:20)
- 20 fresh official draws of the carved s43 policy: **0.9241 ± 0.017** (min 0.884, p20 0.920; 0 of 20 below 0.70),
  vs the packed std0116 policy's H5 0.822 ± 0.239 (min 0.150). Rule: mean ≥ 0.8519, sd ≤ 0.2387, ≤ 1/20 below 0.70:
  **passes**. Mean ≥ 0.9196 (pack 6's packed eval-1 draw), so it counts as a leaderboard gain in expectation.
- Training box vs official evaluator: 0.931 ± 0.006 (10 draws) vs 0.924 ± 0.017 (20 draws): consistent, so the
  falsifier "the training box does not stand in for the official evaluator" (mean < 0.90 or ≥ 2/20 < 0.70) did not fire.
- Packed eval-1 rollout: sim_vs_ref 0.9232 (pack 7's: 0.9196).

## Expected effect [estimate]
- On the leaderboard as scored (submitted trajectories): +0.0036 sim_vs_ref on one of 20 episodes ≈ **+0.0002 AUC**,
  within noise. Its value is robustness: eval 1's bad mode (H5 min 0.150) is gone, which matters only if the
  organisers re-run checkpoints at validation.
