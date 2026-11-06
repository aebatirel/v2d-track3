# Track 3 pack-10 candidate, 1 Nov 2026 — pack 9a+ with a fresh official eval-10 rollout (cavity-safe pieces)

**NOT UPLOADED from this session.** The upload is the owner's decision. It happens in the session where the owner gave
the word (keen-heisenberg / score-status), or on the owner's own word in this session.

## Record
- File: `build_10/track3_submission.parquet`, 9,120 rows, 1,314,925 bytes.
  sha256 `e1bef1e5d7df3513ff9b0ddba19429c5933fe7baa4f05ea8807e245615fd0e2a`.
- CD-O file derived by the uploader's own offline step: `build_10/track3_submission.cd-o.parquet`, 294,912 rows,
  sha256 `2993df019d83c80a…`. Its xyz rows are identical to the ones derived from 9a+, because meshes are unchanged.
- Code: https://github.com/aebatirel/v2d-track3/commit/a187a8c9f9e948e1bfecd91d3fcb9a5495fc0b15 (on every row).
- Built on CPU by `tools/pack_swap_rollouts.py`:
  - Inputs are 9a+'s own packer inputs.
  - Base = `results/submissions/20261031-track3i-candidate/build_9aplus/track3_submission.parquet` (e02736ea…), our best
    upload. 9b is not the base: its eval-33 swap gained +0.012 on the proxy, below the binding pack-10 inclusion bar of
    +0.02.

## Content
- 19 of 20 episodes are byte-identical to 9a+ in every column except code_commit_url. That includes every mesh payload
  (9a+'s C0 / C1 meshes, as flagged and disclosed there) and the eval, packer and uploader hashes.
- **Eval 10:** the draw-1 rollout (by position) of the confirmation draws in run `20261101-e10cs-50c2d90`.
  - Policy: seed 43, `results/perc2e10css43_glock_public/ep10/best/policy.safetensors`, sha256
    `ca7c4e3a162ab11ecda1b8a040ad151763c2e57dcd1e97a1334c6623c2906131`.
  - It was trained with the packed eval-10 grasp-lock recipe at **stock contact limits (njmax 512 / nconmax 256)**, on
    the stored V4p reference of run 20261031-e10v-caf38fb. Its collision pieces are the cavity-safe
    **ev10cs5** (meshes/carve/ev10cs5, MD5SUMS 045d8921…). Training uses the ev10cs5 pieces in place of the packed
    `meshes/carve/ev10`.
  - The collision pieces are the changed variable, along with their piece-derived inertia: blue COM +16.1 mm.
  - The mesh lane's "blue kept volume" gate fails (0.402 vs 0.80); this is disclosed in the PREREG and PROVENANCE.md.
  - It replaces pack 7's eval-10 rollout (gl10A2, checkpoint 76a12265…).
  - It is NOT the njmax-1024 diagnostic policy: tools/no_oracle.py refuses that one, and it accepted this one.
- **Checks against 9a+:**
  - only eval 10's 322 pose rows and its checkpoint_sha256 differ;
  - object_mesh_b64 and the eval / packer / uploader hashes are identical on every row;
  - the uploader's offline validate_submission passes;
  - no_oracle passes, including the swap's reference path.

## Why: the pre-registered swap rule plus the pack-10 inclusion bar
- PREREG: `docs/research/work/eval10-cs4-20261101/PREREG.md` (13c4133, before any result). Verdict:
  `docs/research/work/eval10-cs4-20261101/results/verdict.txt`.
- Scoring is GT-free sim_vs_ref vs our references V (V4p) and P (packed). The comparison is 10 official draws of the
  new policy against 10 fresh draws of the packed policy (run 20261031-h5p7-1a7cdff).

| ref | new mean | packed mean | gain (bar +0.02) | median RPE new / packed | fail rate new / packed |
|---|---|---|---|---|---|
| V | 0.5322 | 0.4632 | +0.069 | 13.94 / 16.05 cm | 10 / 10 |
| P | 0.5116 | 0.4525 | +0.059 | 13.79 / 15.85 cm | 10 / 10 |

- All clauses (a / b / c / s) hold on both references, so the verdict is SWAP-ELIGIBLE and INCLUDE.
- Equal floor: both policies still fail the 5 cm RPE bar on every draw. The cup nest is not completed.
- Draw 1 (the packed rollout) against the replaced 9a+ rollout:
  - vs V: sim_vs_ref 0.512 vs 0.472; RPE 13.25 vs 15.96 cm; MPPE 7.92 vs 8.47 cm;
  - vs P: 0.497 vs 0.456; RPE 12.85 vs 15.76 cm;
  - the beige cup now moves 10.4 cm (reference 25.4, packed 0.7).

## Expected effect [estimate]
- About +0.04 on eval 10's GT-free proxy for draw 1, roughly +0.002 AUC over 20 episodes if the board follows. Pack 9b
  showed the proxy can disagree with mocap by about 0.016 on one episode, which is under this gain.
- RPE / MPPE on eval 10 are lower for draw 1 than for the packed rollout. Across all 10 draws the RPE mean is higher
  (21.1 cm, one draw at 76.9 cm). Each board keeps its best submission.
- Cost of this retrain: $2.85 measured. The njmax diagnostic behind it cost $2.06.
