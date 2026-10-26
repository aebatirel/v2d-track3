# Seed race: many seeds, keep the ones that start well (proposal, 26 Oct 2026; NOT adopted, nothing rented)

The owner asked whether we can train many seeds (10–20 or more) and keep the ones that progress most, since the good ones
seem to show early signs. Everything here is GT-free: every score is sim_vs_ref, our simulation against OUR reference.

## 1. Evidence: do early scores predict the final score? (`early_predict.py` → `early_predict.json`)

Data: 31 standard-learner curves (29 public-twin checkpoint sweeps of 22 Oct, evals 12/18/24/27/3, plus today's eval-25
carve seeds 42/43). One official rollout per checkpoint (noisy: eval-25 s42's five rollouts of one checkpoint span
0.62–0.90).

| Test | Result |
|---|---|
| Correlation, score at 40 % (100M steps) vs final (250M) | Pearson 0.89, rank 0.82 |
| Variance of the final explained by: the level at 40 % / its slope 40→60 % / both / the level at 60 % | 0.79 / 0.04 / 0.82 / 0.81 |
| Same episode, two runs more than 0.1 apart at 40 %: the leader also finishes ahead | 30 of 36 pairs |
| Same, more than 0.05 apart | 43 of 55 |
| Late jumps (final − 40 % > 0.25) | 2 of 31: public ep18 0.24 → 0.82; eval 25 s42 0.50 → 0.89 |

Today's eval 25: s42 led at 40 % (0.495 vs 0.442) and won (5-evaluation means 0.792 vs 0.474), but it dipped to 0.36
and 0.42 at 60 % and 80 %, where s43 led (0.50, 0.47).

Reading:
- The owner's intuition holds on average: the LEVEL at 40 % carries most of the signal.
- The slope ("progress") adds almost nothing. A slope is the difference of two noisy one-rollout scores.
- One cut at 40 % is safe enough. A second cut at 60–80 % would have killed eval 25's winner.
- About 1 in 31 runs blooms late from the bottom. Pruning will lose these.

## 2. Proposed design (asynchronous successive halving, "ASHA": Li et al. 2020, arXiv 1810.05934)

The same family as Hyperband (Li et al. 2018) and population-based training (Jaderberg et al. 2017). DexPBT (Petrenko
et al., RSS 2023) applies population-based training to dexterous hand-arm RL.

Per episode:
- **Lanes:** L single-GPU boxes. One training per GPU: two at once ran about 30 % slower in total (measured 21 Oct,
  `pipeline/pipeline_ep.sh`).
- **Each lane** runs up to S new seeds, one after another, with today's recipe (`carve_rerun.sh` / `hard_ab.sh`,
  STEPS 250M, same schedule).
- **Rung at 40 %:** when `policy_100003840` appears, 3 official evaluations (about 45 s, while training continues). The
  rung score is their mean, written to the HF store.
- **Promotion (η = 3):** the seed continues only if its rung score is in the top third of all rung scores of this race
  so far. The rule waits for at least 3 scores (up to 15 min). Otherwise the lane stops that training and starts its
  next seed.
- **Promoted seeds** run to 250M, then the usual sweep (0.6 / 0.8 / final) and 5 official evaluations of the chosen
  checkpoint.
- **Choice (pre-registered):** the highest 5-evaluation mean among the promoted seeds AND the currently submitted
  policy. The pack then plays one fresh official rollout, as now.
- **Winner's curse:** our own estimate for the chosen seed is inflated (the maximum of N noisy means). The leaderboard
  rollout is fresh, so it is not inflated; expect it below the winner's 5-evaluation mean.

## 3. Cost (measured 26 Oct: 250M took 1 h 37 min / 1 h 50 min on RTX PRO 6000 S / Max-Q, $1.27–1.55/h)

Per seed:
- up to the rung: about 0.67 GPU-h;
- a promoted seed: about 1.0 GPU-h more.

For N seeds at η = 3 that is about 1.0 × N GPU-h, against 1.75 × N for training every seed to the end. So the race
gives about 1.7× more seeds per dollar.

| Seeds per episode (lanes × seeds) | GPU-h | Cost (estimate) | Wall time |
|---|---|---|---|
| 8 (4 × 2) | ≈ 8.5 | ≈ $12–13 | ≈ 2–3.5 h |
| 12 (4 × 3) | ≈ 12.5 | ≈ $17–18 | ≈ 3–4.5 h |
| 16 (4 × 4) | ≈ 16.5 | ≈ $23 | ≈ 3.5–5 h |

## 4. What it can buy (estimates)

- Each episode is 1/20 of the AUC: +0.1 sim_vs_ref on one episode ≈ +0.005 Track 3.
- Score headroom (helper derivation, leaderboard ≈ 0.979 × sim_vs_ref − 0.075 hidden reference loss):
  - perfect policies with today's references: ≈ 0.90;
  - today's policies with a perfect reference: ≈ 0.865 (3rd is 0.865).
  - Top 3 needs about +0.077, i.e. two-thirds of all the policy headroom, or policy and reference gains together.
- Where seeds matter most: episodes with a large policy loss and a wide seed spread.
  - Standard learner: eval 10 (if today's carve works), eval 25.
  - Grasp lock: evals 33, 32, 16, 3. The early-sign rule does NOT hold there (section 5).
- **Hypothesis:** an 8-seed race lifts a high-spread episode by +0.05 to +0.15 sim_vs_ref. **Falsified if** the race
  winner's 5-evaluation mean does not beat the best of today's two seeds by more than its standard error.

## 5. Grasp-lock fine-tunes: early scores do not pick the better run (`glock_early.py` → `glock_early.json`)

Data: 66 checkpoint curves (70M steps, 30 episodes, the "curve" lines of the grasp-lock job logs of 23–26 Oct).

| Test | Grasp lock | Standard learner (section 1) |
|---|---|---|
| Correlation, 40 % vs final (best of the curve here) | 0.77 (rank 0.80) | 0.89 (rank 0.82) |
| Same episode, > 0.1 apart at 40 %: the leader ends better | **22 of 38 (58 %)** | 30 of 36 (83 %) |
| Mean change between neighbouring checkpoints | 0.10 | — |
| Where the best checkpoint sits (median) | 86 % of training (10 % of curves: at 14 %) | — |

Reading:
- Across episodes the correlation mostly reflects episode difficulty.
- Within one episode a 40 % lead is close to a coin flip. The curves jump by about 0.1 between checkpoints, and the
  best checkpoint can come early or late.
- For grasp-lock episodes, a race with an early cut is not supported. Extra seeds there should run to the end; the
  checkpoint curve already picks the best checkpoint. Measured cost today: eval 32 seed 43 took about 1.3 h on a
  $1.51/h box, setup included (about $2).

## 6. Cheaper options (owner, 26 Oct: "is there a cheaper way? maybe a seed race for the frozen or eval_both grasp?")

**Grasp-lock race on the pre-training score.**
- Frozen variant: the evolutionary grip search's best fitness. eval_both variant: the zero-action score after
  re-planning.
- 45 curves; same-episode pairs more than 0.03 apart before training: the leader ends better in **3 of 8** (frozen) and
  6 of 15 (both kinds).
- No support (few pairs). Grasp-lock seeds must run to the end.

**Interruptible machines (Vast bid).**
- Market check 10:10 UTC: PRO 6000 interruptible $0.67–0.71/h all-in, against $1.35–1.39/h on demand: about half.
- Training resume after a kill was verified on 20 Oct (`pipeline_ep.sh`, same box).
- Not tested: a paused box restarting. `onstart.sh` re-runs `run_job.sh` from the start, so the job must skip finished
  steps.
- Lost work per pause is unknown (guess +10–30 %).

**Small or no savings:**
- two trainings per GPU: about 30 % slower in total;
- RTX 5090: 32 GB, less than our 40.5 GB peak;
- A100: 0.16× the speed;
- 48 GB cards: little saving per policy;
- several seeds per box: saves only about 6 min of setup per box.
