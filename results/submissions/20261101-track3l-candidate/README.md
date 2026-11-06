# Track 3 pack-11 candidate, 1 Nov 2026 — pack 10 with the njmax-1024-trained eval-10 policy, evaluated at stock limits

**NOT UPLOADED from this session.** The owner decides the upload; it happens in the session where the owner gives the
word (keen-heisenberg), or on the owner's own word in this session. Pack 10 stays on the boards as the fallback.

**Disclosure: the eval-10 policy was trained with njmax 1024 / nconmax 512 (training-only); it is evaluated at stock
512 / 256.**

## Record
- File: `build_11/track3_submission.parquet`, 9,120 rows, 1,315,317 bytes.
  sha256 `3c428350ec8a3558ec39d8f2072236704e4c52d0538c80ebef125fcb26c055ec`.
- CD-O file derived by the uploader's own offline step: `build_11/track3_submission.cd-o.parquet`, 294,912 rows,
  sha256 `ca3c2875dcfef0db…`. Its xyz rows are identical to pack 10's, because meshes are unchanged.
- Code: https://github.com/aebatirel/v2d-track3/commit/503123196934174ec91901331af79273881e8573 (on every row).
- Built on CPU by `tools/pack_swap_rollouts.py`. Inputs are pack 10's own packer inputs; the base is
  `results/submissions/20261101-track3k-candidate/build_10/track3_submission.parquet` (e1bef1e5…).

## Content
- 19 of 20 episodes are byte-identical to pack 10 in every column except code_commit_url. That includes every mesh
  payload and the eval, packer and uploader hashes.
- **Eval 10:** draw 1 (by position) of the 10 "conf512" official draws of run `20261101-e10nj-451b82d`.
  - Policy: `results/ev10_nj/ck512/policy.safetensors`, sha256
    `aaa077ebae863650c926d13550d368704889d445bcfc96ef9e4773f17c04d55f`.
  - It is the seed-43 eval-10 grasp-lock policy trained with the packed recipe on e10v's stored V4p reference, with
    the packed `meshes/carve/ev10` pieces, and with the training overrides `sim.njmax=1024 sim.nconmax=512`.
  - ck512 is that checkpoint with its stored config set back to stock. The weights buffer is byte-identical to the
    trained checkpoint (3c75ca1d…); only the 4 keys sim / env.sim njmax / nconmax differ (ck512.json of that run).
  - checkpoint_sha256 covers the whole .safetensors file: the tensors and the header, including the stored config
    (`user.resolved_config_json`). Weights and config are one file.
- **Stock evaluation, from the saved config alone** [M]:
  - the file's stored config is 512 / 256 in both `sim` and `env.sim`;
  - FlashCHORD's evaluation path on the pristine evaluator tree (cuda:0) built SolverMuJoCo at njmax 512 / naconmax 256
    for this exact file (`results/ev10_nj/solver_build.json` of that run; the 1024 file builds 1024 / 512);
  - all 10 scored draws ran on the pristine kit evaluator (/content/v2d_clean, one run_policy_evaluation.py call each),
    rc 0, with 0 "nefc overflow" / "broadphase overflow" lines in every evaluator log.
  So both our evaluator and the organisers' container rebuild stock physics from the checkpoint, with no override.
- It replaces pack 10's eval-10 rollout (the ev10cs5 retrain, checkpoint ca7c4e3a…).

## Why: the standing rule, applied to already-seen draws
- Amendment `docs/research/work/eval10-njmax-20261101/PREREG_AMENDMENT_pack11.md` (998385b0), committed before the
  pack-11 scoring.
- **Not a blind test:** the 512-readout values had been seen at 05:45 UTC.
- Verdict: `docs/research/work/eval10-njmax-20261101/results/pack11/p11_verdict.txt`, from `tools/p11_verdict.py`
  (b8bc0aa7; it applies e10v_verdict unchanged).
- Scoring is GT-free sim_vs_ref, re-scored together on CPU with tools/e10v_score.py against V (V4p, md5 5d22fc57…)
  and P (packed eval-10 reference, md5 1a5003d9…).

| ref | new mean (n 10) | pack 10's eval-10 mean (n 10) | gain (bar +0.02) | fail rate new / packed | median RPE margin |
|---|---|---|---|---|---|
| V | 0.9034 | 0.5322 | +0.3712 | 0 / 10 vs 10 / 10 | 11.9 cm |
| P | 0.8730 | 0.5116 | +0.3614 | 0 / 10 vs 10 / 10 | 11.3 cm |

- All clauses a / b / c / s hold on both references, so the verdict is SWAP-ELIGIBLE and INCLUDE.
- Draw 1: vs V 0.9175 (RPE 1.89 cm); vs P 0.8816 (RPE 2.37 cm). Pack 10's rollout: 0.5120 / RPE 13.25 cm.

## Guard
- `tools/no_oracle.py` has ONE owner-approved exception, `ALLOW_CKPT = {aaa077eb…}`. The owner gave it in this session,
  ~11:40 UTC.
- An input is accepted under it only when its own content names that sha256. Every other non-stock-limit checkpoint and
  every e10nj / ev10_nj name stays refused: tests 17/17 in
  `docs/research/work/eval10-njmax-20261101/cpu/out/allow_ckpt_test.json`.

## Expected effect [estimate]
- Eval 10 on the GT-free proxy, draw 1 vs pack 10's rollout: +0.41 (V) / +0.38 (P). That is ≈ +0.02 AUC over 20
  episodes if the board follows.
- RPE / MPPE on eval 10 are much lower: 1.9 vs 13.3 cm vs V.
- [H] SP-SR may regain eval 10, since the draws pass the 5 cm RPE bar where pack 10's fail.
- Cost: $0 GPU for the pack (the stored draws were reused). The diagnostic run behind it cost $2.06.
