# Track 3 pack-12 candidate, 2 Nov 2026 — pack 11 with evals 14 and 32 retrained on guard-bridged references

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

## Pack 12b (added 2 Nov ~06:35 UTC) = pack 12 + eval 16 — `build_12b/`
- File: `build_12b/track3_submission.parquet`, 9,120 rows, sha256
  `bde0ae84ccdaf442459308f0f806365cc79105e2f4af0b676c05103c14b0a0e1`; CD-O `985db0dd…` (rows identical to pack 11's).
- Code commit on every row: https://github.com/aebatirel/v2d-track3/commit/fa129a110aa4fd33bcdab199bcaa2c0c7fd3f9cd.
- Built by tools/pack_swap_rows.py on pack 12; checks as above [M]: vs pack 11 only e000014 (316), e000016 (346; 345 pose
  rows changed) and e000032 (518) pose rows + checkpoints differ; evaluator stamps match; kit offline validation pass;
  CD-O rows changed 0; no_oracle pass (rollout, reference path, checkpoint).
- **Eval 16:** run `20261102-pfG-86cfc19`, arm pz seed 43, checkpoint
  `ed25dc5f8312b861b8ec3be6d96fdafecb3c939e89a29fef8e4a8b56b4966882` (store
  `runs/20261102-pfG-86cfc19/results/pfpzs43_glock_public/ep16/best/policy.safetensors`), confirmation draw 1.
  - Reference: the PACKED eval-16 reference with the right hand's wrist / fingers / frames held at f106 from f107 to the
    end (tools/hold_freeze.py): the robot hand keeps holding the spoon where our reference keeps it still, instead of
    letting it fall in the simulator. Object poses unchanged (the packed reference P is the yardstick). Current packed
    recipe, stock limits. Pre-registered: docs/research/work/pf-release-20261102/PREREG_B.md.
  - Verdict [M] (10 fresh official draws, pristine evaluator): sim_vs_ref **0.974** vs packed H5p7 0.850; fails 0 / 0;
    median RPE 1.18 vs 1.79 cm; draw 1 0.974 vs the board's old eval-16 draw 0.908; inclusion gain +0.124 → PASS + INCLUDE.
  - Same-box control (packed reference, no freeze): 0.769 / 0.787, NO-SWAP.
- Board expectation [E]: eval 16's stored draw rises 0.908 → 0.974 vs our reference; evals 14 / 32 as above.

## Pack 13 (added 2 Nov ~17:40 UTC) = pack 12c + eval 20 — `build_13/`
- Base: **pack 12c** (sha256 3542f8e5…, the board's best pose pack: 12b + the C0 blue-cup mesh payloads in evals
  10 / 14 / 20 / 32 / 33; from claude/focused-pascal-2nz9s1). The blue-cup meshes carry over unchanged.
- File: `build_13/track3_submission.parquet`, 9,120 rows, sha256
  `791c3922fffd15f3d63657c3a34bf5e0ee971ec6158f5d2b5e5db2580defb094`; CD-O `d55cc9f6…` (rows identical to 12c's).
- Code commit on every row: https://github.com/aebatirel/v2d-track3/commit/b45b377bae18d7dc2b0710355ea9dde435169275.
- Built by tools/pack_swap_rows.py on 12c [M]: only e000020 (404 rows; 403 pose rows changed) + its checkpoint differ;
  evaluator stamps match the base rows; kit offline validation pass; CD-O rows changed 0; no_oracle pass. Self-test: a
  no-swap repack of 12c is byte-identical to 12c.
- **Eval 20:** run `20261102-pfJ-cf8cc34`, arm plw seed 43, checkpoint
  `1e08b92ff96d076d48fe58ea02d5006aa4ebed4a3767b82fc60f3a99f0763c66` (store
  `runs/20261102-pfJ-cf8cc34/results/pfplws43_glock_public/ep20/best/policy.safetensors`), confirmation draw 1.
  - Recipe: the packed grasp-lock recipe (70,004,736 steps, stock limits) on the PACKED eval-20 reference reused byte for
    byte, with lift-window training starts (frames 1–35, share 0.3; ops/box/patch_flashchord_lift.py). GT-free.
    Pre-registered: docs/research/work/pf-lift-20261102/PREREG.md (addenda A / B); public test pfH PASS.
  - Verdict [M] (10 fresh official draws, pristine evaluator; docs/research/work/pf-lift-20261102/results/verdict_ep20_plw.json):
    sim_vs_ref **0.926** vs board policy (H5p7) 0.893; fails 0 / 0; median RPE 1.38 vs 1.67 cm; draw 1 0.938 vs the
    board's old draw 0.895; gain +0.033 ≥ +0.02 → PASS + INCLUDE. Seed 42 collapsed (0.297 box); the seed rule chose 43
    (box 0.921).
- Not included (same batch): eval 15 NO-SWAP on clause c only (mean 0.958 vs 0.906, fails 0 vs 1/10, but median RPE
  1.346 vs 1.299 cm); eval 14 NO-SWAP (fresh 0.826 vs 0.875 after box 0.923); evals 3 / 25 / 28 / 30 / 32 fail the gate.
- Board expectation [E]: eval 20's stored draw 0.895 → 0.938 vs our reference (one episode of 20: ≈ +0.002 on the
  sim_vs_ref mean); vs ground truth unknown.
