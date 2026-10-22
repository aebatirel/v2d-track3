# 23 — The 250M-step training budget: what it buys and whether we need it (2026-10-22)

Sources: FlashCHORD at the evaluator pin `8c778f90` (read in a fresh clone, nothing executed; upstream main `7eb9721` of
2026-10-22 has identical training configs and training code), our Colab run (work log, 2026-10-12), and a focused
literature review (section 5). Paths below are relative to `robotic_grounding/flash_chord/` (FCR) or
`FCR/src/flash_chord/` (FC). [M] measured, [V] verified in code or docs, [E] estimate, [H] hypothesis.

## 1. Bottom line
- **Nobody has shown that 250M steps are needed for our episodes.** NVIDIA calls the schedule "validated"
  (FCR/docs/configuration.md:13,31), meaning it works on their demos, not that it is the minimum. They ship no learning
  curve or ablation. [V]
- **Our setting is harder than the one it was validated on**, so the answer can go either way: our references play at
  twice NVIDIA's speed (section 3). [V/H]
- **As the scripts stand, day 1 cannot answer the question.** Training runs with `logging.mode=disabled`, so no training
  metric is recorded, and `ops/box/store.sh push-run` keeps only the newest policy. [V]
- **You cannot stop a run early to save steps.** The assist force is scheduled by step count, so a shorter run needs
  the whole schedule rescaled. A half-length schedule composes correctly as a Hydra override (section 4). [V]
- Proposed: measure the learning curve on day 1 for about +1 GPU-h, then A/B a 125M schedule against 250M on three
  public episodes with two seeds each (18 GPU-h, about $9–29). If it holds, each 20-policy cycle drops from about 40 to
  about 20 GPU-h, and the saving can buy a second seed per episode. [E]

## 2. What the 250M steps are [V]
- `FC/configs/experiment/sharpa_flash_sac.yaml` overrides the training defaults (`configs/training/reference_flash_sac.yaml`):
  - total steps 50,000,896 → **250,003,456** (61,036 collections of 4,096 worlds);
  - updates per collection 2 → **8**, so 488,288 optimizer updates, batch 2,048;
  - checkpoint every **10,000,384** steps (the 5,000,000 default is overridden; STATUS and the runbook said 5M), so 25
    policy checkpoints per run, 4.9 MB each [M, Colab].
- The learning rate decays by cosine from 3e-4 to 1.5e-4 over all optimizer updates. The horizon is derived from the
  total step count (`FC/training/flash_sac/config.py:363-373`), so a shorter run compresses the decay automatically.
- The curriculum (`FC/configs/curriculum/tracking_250m_mixed_reset.yaml`) changes only the assist (VOC) scale and the
  share of resets to frame 0, never the reward weights. Wall clock below is at our measured 45,300 env steps/s [M],
  before JIT compile and any later-phase slowdown:

| Phase | Steps | Share | VOC scale | P(reset to frame 0) | Wall clock |
|---|---|---|---|---|---|
| Assisted: VOC annealed in 8 stages | 0–122.9M | 49% | 1 → .75 → .5 → .25 → .1 → .05 → .025 → .01 | 0.1 once VOC < 0.1 (from 78.6M) | 45 min |
| Unassisted | 122.9–200.0M | 31% | 0 | 0.1 | 28 min |
| Unassisted, eval-like starts | 200.0–250.0M | 20% | 0 | **0.5** | 18 min |
| Total | 250.0M | | | | **92 min** (1.5–2 h with overhead) |

- The official evaluator removes the assist (`FC/evaluation/harness.py:265-272`) and starts once from frame 0. The
  phases that train that condition are the last ~127M steps, and mostly the last 50M.
- The G1 body recipe uses 350M steps; the generic training default is 50M with a quarter of the updates per step.

## 3. Evidence on whether 250M is needed
- **Our one data point is weak** [M]: the tissue-box demo policy at 20M steps scored evaluator AUC 0.918 against its own
  reference. That policy had trained almost entirely at full assist (the first VOC drop is at 19.66M). We do not know
  how far the box moves in that demo; an object that barely moves scores high with almost any policy.
- **Our references play twice as fast as NVIDIA's validated ones** [V]: the recipe uses `motion_speed: 0.5` on ego
  demos registered at 30 fps (note 01 A.0, B.2); our timing rule (note 06) needs `motion_speed=1.0` at 20 fps. Each clip
  therefore has half as many control steps, each with twice the data, but the soft wrist controller (kp 25 N/m, 45 N)
  must follow motion twice as fast. [H] This could need more steps, not fewer. Two-object episodes, the spoon and
  the lid are also harder than the tissue box.
- **Training metrics are discarded** [V]. Rewards, termination causes, tracking errors, reference progress and the
  stage index exist (`FC/training/flash_sac/runner.py:230-302`), but only a W&B logger records them, and
  `scripts/train_flash_sac.py:89` creates it only when `logging.mode != disabled`. NVIDIA's README and our
  `pipeline/pipeline_ep.sh` both use `disabled`, so a run leaves only its 1 % progress lines. The evaluator drops the
  `logging` block from the checkpoint config (`FC/training/checkpoint_metadata.py:375`), so enabling logging cannot
  change evaluation.
- **Intermediate policies are thrown away** [V]: `store.sh push-run` keeps only the newest `policy_` and `state_` per
  run, and nothing evaluates the earlier ones before the box self-destroys.
- **Literature**: section 5.

## 4. Why not just stop early, and what a shorter run looks like [V]
- A checkpoint at 100M was trained with assist 0.025 and has seen few frame-0 starts; the evaluator gives it no assist.
  Its score says little about a run that was *planned* to end at 100M.
- A shorter run rescales every threshold. Half schedule (all thresholds × 0.5, all multiples of 4,096):

```
curriculum.thresholds=[9830400,17203200,24576000,31948800,39321600,46694400,54067200,61440000,68812800,100003840,125001728] training.total_environment_steps=125001728
```

- Checked with Hydra's compose API against the pinned configs (config only; nothing instantiated or trained):
  `training.curriculum` resolves to the overridden thresholds, total updates become 244,144, and checkpoints stay at
  every 10,000,384 steps.
- The evaluator accepts such a checkpoint: the saved curriculum only sets training stages, and evaluation forces VOC 0
  (`FC/training/checkpoint_metadata.py:420-439`, `FC/evaluation/harness.py:265-272`).

## 5. Literature
Pending (review running 2026-10-22).

## 6. Proposed experiments
Integrity: public episodes only; mocap is read only by `score_sim.py`. On eval episodes, any choice of checkpoint, seed
or schedule uses the evaluator's metrics against our own reference, never mocap.

**H1 [H]:** under the standard schedule, the official evaluator's score on Track 3 episodes stops rising well before
250M (for example ≥ 95 % of its final AUC by 160M). Falsified if the gain from 200M to 250M, or from 140M to 200M,
exceeds the seed-to-seed spread.

**H2 [H]:** a schedule compressed to 125M reaches the same final AUC as 250M. Falsified if, over 3 episodes × 2
seeds, mean AUC against mocap drops by more than the seed-to-seed spread, or any episode drops by more than 0.05.

- **Stage A, added to day 1** (episode 12 already trains twice to 250M, on perc2 and on oracle references):
  - record training metrics locally;
  - keep all 25 policy checkpoints (about 125 MB per run in the HF store);
  - evaluate the checkpoints at 50, 100, 140, 160, 180, 200, 220 and 250M with the official evaluator (AUC against
    our reference, GT-free) and `score_sim.py` (AUC against mocap);
  - cost about +0.5–1.5 GPU-h [E]; evaluator time per checkpoint is unmeasured.
- **Stage B, on boxes 2–3** (already in the runbook) plus episode 12: {250M, 125M} × seeds {42, 7} on episodes 12, 22
  and 27, whose tracking is clean (perception AUC 0.94–0.998), so robot error dominates. 12 runs, 6 × 2 h + 6 × 1 h =
  **18 GPU-h, about $9–29** [E], fewer boxes if two trainings per GPU work on day 1. Apply the H2 rule above.

## 7. What it is worth [E]
- Per policy: 250M ≈ 1.5–2 h; 125M ≈ 0.8–1 h.
- Per 20-policy cycle: about 40 → 20 GPU-h, saving about $10 at interruptible prices or $30 on demand, and each wave
  finishes about 45 min sooner.
- The larger value is what the saving buys: a second seed per episode, chosen by the GT-free evaluator metric, or a
  third submission cycle before the freeze.
- If the curve is still rising at 250M (plausible given the faster playback), the result instead says to train the
  hard episodes longer. That is worth knowing too.

## 8. Changes needed before day 1 (not made yet)
1. A local metrics logger: a small wrapper that replaces `flash_chord.training.flash_sac.runner.WandbLogger` with a
   JSONL writer before running `scripts/train_flash_sac.py` (the script imports the class by name, line 31), or W&B
   offline mode with `logging.upload_checkpoints=false`. FlashCHORD itself stays unchanged.
2. `store.sh push-run`: keep every policy checkpoint for experiment runs.
3. A checkpoint-sweep script: evaluator plus `score_sim.py` per checkpoint, writing one table per run.
4. `pipeline_ep.sh`: a `SCHEDULE=half` option that adds the override above; the run directory must name it.
5. Correct the checkpoint cadence in STATUS and the runbook: 10,000,384 steps (about 3.7 min), not 5M.

Aside: `immediate_first_frame_probability` (`FC/lifecycle/reset.py:620-675`) trains starts that match deployment
exactly; the G1 recipe uses it (0.25, then 0.5) and the Sharpa recipe does not. It is a quality lever, not a cost lever,
and a candidate for a later A/B on the same harness.
