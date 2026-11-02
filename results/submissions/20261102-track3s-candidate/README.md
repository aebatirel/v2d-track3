# Track 3 pack 14 candidate, 2 Nov 2026 — pack 13f + eval 14 (Tier B collision retrain)

**NOT UPLOADED from this session.** keen-heisenberg verifies and uploads on the owner's word.

## Record — `build_14/`
- File: `build_14/track3_submission.parquet`, 9,120 rows, sha256
  `1dbc33c4968ce5f662f16ca66ad0309b34cef4efd621098d0271180110013638`; CD-O `f2f4a7e9…` (rows identical to 13f's).
- Base: **pack 13f** (claude/focused-pascal-2nz9s1, results/submissions/20261102-track3r-candidate/build_13f, sha256
  fa1e31f5…; = 13e + blue cup / dust pan; 13e = 13b's poses + 12e's meshes).
- Code commit on every row: https://github.com/aebatirel/v2d-track3/commit/cc191721a6e15a8530b366f31592d9625aad1b51.
- Built by tools/pack_swap_rows.py [M]: vs 13f only e000014 (316 rows, all pose rows changed) and its checkpoint
  (9da879d9… → 7f7a7c6a…) differ; mesh payloads identical; evaluator stamps match; kit offline validation pass; CD-O rows
  changed 0; no_oracle pass (rollout, reference, checkpoint). The board's eval-14 row (13f) = pfC conf draw 1 (checked).

## Eval 14
- Run `20261102-pfR2-c1a5471`, arm **p0m** seed 43, checkpoint
  `7f7a7c6a8fb989f2c6fc5a169ac059cc486fbea873a27c2227e588eeac73105e` (store
  `runs/20261102-pfR2-c1a5471/results/pfp0ms43_glock_public/ep14/best/policy.safetensors`), confirmation draw 1.
- Recipe: the board policy's own reference (pack 12b's bridged eval-14 reference, run 20261101-pfC-f38b324) reused byte
  for byte; the packed grasp-lock recipe (70,004,736 steps, stock limits); the collision MESH files of the blue cup (13f
  Tier B+ cup, decimated to 20k faces) and the dish rack (Tier B) replaced in the reference's asset copy.
- **GROUND-TRUTH FLAG:** those collision shapes were selected by CD-O against the organisers' public object scans, so this
  rollout depends on GT-selected geometry (owner's "permission for all", coordinator's task; docs/research/work/
  pf-mesh-20261102/PREREG.md). Everything else is GT-free.
- Zero-shot (board policy on the new collision, one draw): 0.878, no overflow. Box draws: s42 0.938 ± 0.010, s43
  0.946 ± 0.008.
- Verdict [M] (10 fresh official draws, pristine evaluator; docs/research/work/pf-mesh-20261102/results/verdict_ep14_p0m.json):
  sim_vs_ref **0.933** vs the board policy's 0.875; fails 0 vs 1 / 10; median RPE 1.97 vs 2.71 cm; draw 1 0.942 vs the
  board row 0.895; gain +0.058 → PASS + INCLUDE.
- Board expectation [E]: eval 14's stored draw 0.895 → 0.942 vs our reference (≈ +0.002 on the 20-episode mean); vs
  ground truth unknown.

## Pack 14p (2 Nov ~23:40 UTC) = pack 13p2 + eval 14 — `build_14p/` (THE ONE TO UPLOAD; pack 14 on 13f is superseded)
- Base: **pack 13p2** (claude/focused-pascal-2nz9s1, results/submissions/20261102-track3u-candidate/build_13p2, sha256
  19ac10e3…; = 13f1 + pose-CV meshes (TSDF pot, library_c0 rack) + eval-20 pitcher placement; AUC 0.88403). 13p2's poses
  and checkpoints equal 13f's (checked: 0 rows differ; mesh payloads differ on 12 episodes); its eval-14 row = pfC conf
  draw 1, the verdict's "old".
- File: `build_14p/track3_submission.parquet`, 9,120 rows, sha256
  `b6c6100d57d18dc2ae22ec7bda238d599e753e4344c417926b787595997d7d70`; CD-O `e3409f38…` (rows identical to 13p2's).
- Code commit on every row: https://github.com/aebatirel/v2d-track3/commit/cc191721a6e15a8530b366f31592d9625aad1b51.
- Checks [M]: vs 13p2 only e000014 (316 rows) poses + checkpoint (9da879d9… → 7f7a7c6a…); 13p2's mesh payloads kept
  everywhere; eval-14 poses identical to pack 14's; evaluator stamps match; kit offline validation pass; CD-O rows changed 0;
  no_oracle pass.
- **Note:** eval 14's SIMULATOR collision was the Tier B rack + 13f cup (meshes/tierB_collision), while 13p2's submitted
  eval-14 rack payload is library_c0 (pose CV). All share our template body frame, so the poses are consistent with
  either payload.
