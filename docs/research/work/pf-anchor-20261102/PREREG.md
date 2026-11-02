# Spoon-anchor re-evaluation — PRE-REGISTRATION (2 Nov 2026 ~20:45 UTC, before any draw)

Owner (via keen-heisenberg, 20:10 UTC): "do as much work as you can for tonight"; coordinator's task: spoon anchor on
evals 32 / 33 / 35 / 36 / 37 (docs/research/spoon-2026-10-25/README.md). GT-free; eval episodes only; no training.

## Why [M, from the spoon README]
The kit aligns the whole achieved scene on the anchor object's frame-0 orientation; the spoon anchors these five
episodes; a 10° frame-0 roll error costs 0.09–0.28 AUC there. A rollout's frame 0 is its reference's frame 0, so the
anchor orientation we submit is our reference's. Our reference's spoon frame 0 differs from the raw tracker's
rest-averaged orientation by 2.0 / 1.8 / 3.2 / 6.1 / 5.2° (32 / 33 / 35 / 36 / 37; tools/anchor_rest.py, refs/ep<N>.json).

## Change (CPU, done; refs/ep<N>.parquet, md5 refs/MD5SUMS; no_oracle pass)
R' = the board policy's own reference P (32: pack-12b bridged reference of run 20261101-pfD-f38b324; 33 / 35 / 36 / 37:
docs/research/work/masses-eval-20261031/packed_refs.json, md5-checked) with, for the spoon only:
- frames before its first > 1 cm motion (onset 49 / 55 / 27 / 33 / 33): orientation := W · chordal_mean(raw rest
  orientations, at most 30 frames), W = chordal mean over frames ≥ onset + 10 of R_ref R_raw⁻¹ (the estimator (b) of
  tools/anchor_f0_test.py); z shifted so the mesh's lowest point keeps its height (≤ 4 mm);
- the next 10 frames: the correction fades linearly to zero; every later frame, every other object and every robot
  column byte-unchanged (checked: changed spoon frames 0..onset+9 only).
No S2 (it needs a rebuild + retrain; out of scope tonight).

## Run (ops/jobs/pf_anchor.sh, one box)
Per episode the BOARD checkpoint (sha256-checked against the table; unchanged) is rolled out with R' placed at the path
its config names (the config stores the path and frame count only): 10 fresh official draws on the pristine evaluator
(kit run_policy_evaluation.py, clean worktree), scored by tools/dr_score.py vs P and R'.
Controls: the board policy's own draws on P — H5p7 (33 / 35 / 36 / 37), pack-12b confirmation draws (32); old = the
board's row (pack 6: 35 / 36 / 37; c33B submission: 33; pfD conf draw 1: 32; each checked equal to pack 13b's rows).

## Rule (tools/anchor_verdict.py), per episode — SWAP iff
- a: mean sim_vs_ref of the 10 draws vs R' ≥ the board policy's control mean vs P − 0.01;
- b: share of draws with RPE > 5 cm (vs R') ≤ the control's (vs P);
- s: draw 1 vs R' ≥ the board's row vs P − 0.05;
- every draw scored, own-reference-checked (R'), and carrying the board checkpoint.
SWAP → draw 1 replaces the episode's rows in the next pack (tools/pack_swap_rows.py; the checkpoint is the same, so the
tool's "differs from the base checkpoint" check is waived for these episodes only, and that is the only waived check).
One upload of the resulting pack; no iteration on the board; whatever the board says, this rule is not revisited.

## What this does NOT show [H]
sim_vs_ref vs R' only checks that the policy still tracks the shifted reference; it cannot say whether R' is closer to
the truth. That is a variance argument only: the public test of the same estimator on other anchors (A-f0) gave +0.001
(low power, 3 / 4 within 2°). On 36 / 37 our reference may sit on a real stable facet and the raw mean between facets;
eval 37's raw → reference mapping is weak (residual median 5.3° vs ~1° elsewhere). Board effect per episode [E]:
0 ± 0.03–0.15, sign unknown.
