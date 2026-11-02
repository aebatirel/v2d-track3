# Track 3 pack-12 candidate, 2 Nov 2026 — pack 11 with eval 14 retrained on the guard-bridged reference

**NOT UPLOADED from this session.** The uploader session (keen-heisenberg) uploads on the owner's word. Pack 11 stays on
the boards as the fallback.

## Record
- File: `build_12/track3_submission.parquet`, 9,120 rows, sha256 `66fc37c348c310d24e640e4f0bf598c5d7d7c87398cc3b7f64d2b9c64a65bcc1`.
- CD-O file: `build_12/track3_submission.cd-o.parquet` (derived by the kit's offline step; rows identical to pack 11's:
  meshes unchanged), sha256 `7925706f…`.
- Code commit on every row: https://github.com/aebatirel/v2d-track3/commit/6cb5ea3fe7cd612832da3a8b9e241c3dc0b015b1.
- Built on CPU by `tools/pack_swap_rows.py` (exact row-level swap; self-test: a pure repack equals pack 11 in content;
  the swapped rows are the rollout's achieved poses, as for every earlier pack [M on pack 11's eval 10]). Checks [M]:
  only e000014's 316 pose rows + checkpoint_sha256 differ from pack 11 (05b13510… → 9da879d9…); code_commit_url changes
  on every row; mesh payloads and evaluator / packer / uploader hashes identical; the rollout's flash_chord stamps
  (checkpoint, eval_code b1b3ebe3…, eval_script 160d24f5…) match; kit offline validation pass; CD-O rows changed 0;
  no_oracle pass on the rollout, its reference path and the checkpoint (stock sim limits 512 / 256 in its stored config).

## Content
- 19 episodes byte-identical in content to pack 11.
- **Eval 14:** draw 1 (by position) of the 10 fresh official confirmation draws of run `20261101-pfC-f38b324`
  (pristine kit evaluator, rc 0, 0 overflow lines). sim_vs_ref of this draw: 0.882 vs the packed reference P, 0.895 vs B.
  - Policy: store `runs/20261101-pfC-f38b324/results/pfss43_glock_public/ep14/best/policy.safetensors`, sha256
    `9da879d9c0e8ecdeb6dd08c69b901ac34262f8770db142defcc4e45de21493e8` (seed 43, 70,004,736 steps, the packed grasp-lock
    recipe and single-hand construction).
  - Reference B: eval 14's own perceived base reference with the TRACK_GUARD drift bridged (tools/guard_bridge.py: the
    cup's f37–45, which had drifted 3–14 cm out of the perceived hand before the guard re-found it at f46, interpolated
    between f36 and f46). GT-free; pre-registered in docs/research/work/pf-bridge-20261101/PREREG.md.

## Why (the standing rule) [M]
docs/research/work/pf-bridge-20261101/results/verdict_ep14_s_cpu.json: PASS + INCLUDE.
| | candidate (10 draws) | packed (H5p7, 10 draws) |
|---|---|---|
| sim_vs_ref vs B (own reference) | **0.875** | 0.706 |
| sim_vs_ref vs P (packed reference) | **0.861** | 0.727 |
| draws with RPE > 5 cm (vs B) | 1 / 10 | 4 / 10 |
| median RPE vs B | 2.71 cm | 4.38 cm |
Draw-1 clause: 0.895 vs the old packed draw 0.890 (B). Inclusion gain on B +0.169 (bar +0.02).
Board effect [E]: unknown; the packed eval-14 rollout on the board is pack 6's lucky draw (0.909 vs P), better than
this draw 1 (0.882 vs P). On re-runs the expected gain is large (+0.13 mean on P); on the stored-trajectory board the
swap can even cost a little (draw 1 vs the lucky packed draw) [E].
