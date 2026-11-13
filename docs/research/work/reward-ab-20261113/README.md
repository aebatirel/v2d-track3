# Reward A/B: the Track 3 winner's metric-aligned object reward vs ours (public episodes), 2026-11-13

Status: **PREPARED, NOT LAUNCHED.** Waiting for the owner's go-ahead and credit. Credit $9.58 at 13 Nov.

## Question
- Does the winner's object reward make our policies follow their reference more closely, and score higher against
  mocap?
- Their reward: six keypoints on a 0.1 m lever around the object's centroid, exp(−d / 3 cm). They report public
  MPPE 0.851 → 0.666 cm and +0.023 hidden AUC.
- Ours: FDR point match, the mean of the 3 largest of 128 surface-point errors, exp(−e / 10 cm). It is flat across
  the 1–9 cm range the metric scores.

Hypothesis H-W2 (`docs/analysis/winner-richchentw-20261113/README.md`).

## Design
- **Episodes:** public ep12 (blue cup + rack), ep2 (pot + lid), ep40 (dust pan), ep23 (wooden pieces).
  - These are the four of test A's eight (`docs/research/work/gate-testA-20261113/`, branch
    `claude/gallant-franklin-8gvsv3`) where test A's standard learner followed its reference: one-draw sim_vs_ref
    0.89 / 0.97 / 0.96 / 0.94.
  - The other four (0.25–0.55) have infeasible 20 Oct references (wrist IK 62–171 mm), where a reward cannot show
    tracking precision.
  - Selection used only GT-free sim_vs_ref. That draw is not used below.
- **Control:** test A's own chosen checkpoint per episode (`runs/20261113-gA*-25cb421/results/perc2s/ep<N>-s42/
  selection.json`).
  - Recipe: standard FDR learner (FC_FDR_OBJ=1 top-k, FC_FDR_TIPS=1, FC_VOC_INERTIA=1, FC_IMMEDIATE_FIRST_FRAME=0.25,
    FDR_TRAIN_ARGS), 250M steps, seed 42, checkpoint sweep 0.4/0.6/0.8 + final chosen by sim_vs_ref.
- **Treatment:** the same reference file (sha256 checked against test A's input), seed, recipe, steps, assets and
  sweep, with one change: FC_FDR_OBJ_MODE=centroid, FC_FDR_OBJ_LEVER=0.1, FC_FDR_OBJ_SIGMA=0.03.
  - Code: `ops/box/fc_v2d_fdr.py`, CPU-tested by `tests/test_fdr_centroid.py`.
  - The training path otherwise equals test A's commit 25cb421. `git diff 25cb421 HEAD` touches only opt-in options
    (EVAL_TIMEOUT, DR/lift patches, physics, oracle) and this reward.
- **Measurement:** hard_ab.sh with BASE_EVAL=1 and NREP=5.
  - Both chosen checkpoints get 5 fresh official-evaluator draws on the same box.
  - Every draw is scored with `pipeline/score_registered.py`: registered AUC, MPPE and SP/MP vs mocap (scoring
    only), plus sim_vs_ref vs our reference.
  - Same evaluator conditions as test A (D3: the box's patched FlashCHORD).
- **Boxes:** 2 × RTX PRO 6000 (WS/S, on demand), 2 episodes each, trained one after the other.
  - rA1: ep12, ep2. rA2: ep40, ep23.
  - Jobs: `jobs/rA1.job`, `jobs/rA2.job` (sha256 in `jobs/SHA256SUMS`, built by `jobs/make_jobs.sh`).

## Pre-registered rule (fixed before any result)
For each episode, Δ = mean registered AUC of the treatment's 5 draws − mean of the control's 5 draws.
- **Promising** (then a seed-43 repeat on the same 4 episodes before any recipe change):
  - mean Δ over the 4 episodes ≥ +0.010;
  - no episode Δ < −0.030.
- **Falsified** for this reward on these references: mean Δ ≤ 0.
- **Otherwise inconclusive:** a second seed decides.

Secondary, reported but not deciding:
- MPPE (cm) vs mocap; the winner's direction is lower;
- sim_vs_ref;
- SP/MP-SR;
- failed draws (AUC < 0.5).

If only rA1 can run (budget), its two episodes are reported as descriptive, with no verdict.

## Cost
- Test A's boxes took 3.3–4.2 h for 2 trainings + sweeps + 1 draw.
- Here, 9 more draws per episode add ≈ 0.2 h.
- Estimate [E]: 3.5–4.4 h × $1.45–1.65/h ≈ $5–7 per box, so ≈ $11–14 for both. Cap $16.
- Boxes self-destroy after pushing to the store; the stall watchdog is on.

## Launch (after the go-ahead)
Same steps as `docs/research/work/gate-testA-20261113/JOBS.txt`:
1. check the pushed commit;
2. `(cd jobs && sha256sum -c SHA256SUMS)`;
3. `ops/vast.sh show` and credit;
4. pick offers (WS/S only, effective ≤ $1.75/h);
5. run `ops/vast.sh V2D_COMMIT=$SHA ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create $O <date>-rA<k>-<sha7>
   "$(cat jobs/rA<k>.job)"`, about 2 minutes apart, checking `show` after each.
