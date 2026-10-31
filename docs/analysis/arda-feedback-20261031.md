# Prof. Arda İnceoğlu's feedback on the Learner Notebook (31 Oct 2026, chat): analysis

Report he read: Track 3 Learner Notebook (https://claude.ai/artifact/1mxeAFQB7U9qhY5rk5eCVX), Part 1 (training vs
evaluation table) and Part 8 (variance). Checked against this repo and the live session branches at ~07:30 UTC. Labels:
[M] measured, [E] estimate, [I] inference, [H] hypothesis with its falsifier. No ground truth was read for this note,
and nothing was run or spent.

## 1. What he said (translated)
1. Part 8's variance table matters: rollouts of the same policy differ a lot.
2. Another table says training uses "none (no domain randomisation, no observation noise)". Look at that first.
3. Take one successful and one failed rollout of the same episode and compare them frame by frame, to see where the
   error starts. He expects no single failure point: different rollouts probably fail in different places. To save
   time, perturb several components at once.
4. Roughly two parts: (1) the reference trajectory from video, (2) RL learning the fine manipulation. If (1) is not
   good enough, (1) caps (2) however well (2) is trained.
5. Many research directions, few low-risk short-term ones. For example, each episode's RL is trained independently;
   some transfer learning could help.
6. "Tell Claude we never did domain randomisation; it will sort it out quickly."

## 2. Domain randomisation and the variance
**True as stated [M].** Training has no physics randomisation (object scale fixed at 1.0; no mass, friction or COM
randomisation) and no observation noise (`notes/01` §scene, `notes/26` §A; CHORD's own large runs also had observation
corruption off). Training is not deterministic, though:
- 4,096 worlds start at random frames, with finger openness U(0, 0.7);
- actions are sampled for exploration;
- the assist force changes the dynamics over the curriculum.

The evaluator runs one world from frame 0 with the deterministic mean action and no assist. Its run-to-run spread comes
from GPU physics non-determinism (MuJoCo-Warp contact solve order) and fp16 actor maths (`notes/14`). A determinism
option was merged upstream on 22 Oct, after the evaluator pin.

**Where the spread comes from, by episode** (H5, 10 official draws, sim_vs_ref [M]; cause from forensics [E]):

| Eval | sd | Cause | Fixed? |
|---|---|---|---|
| 30 | 0.255 | the sweeper starts inside our rack mesh (collision overlap) | no |
| 1 | 0.239 | the lid sits inside the pot's collision hulls | **yes, by a geometry carve: 0.924 ± 0.017 over 20 official draws** |
| 14 | 0.199 | our reference pushes the cup into the rack mesh; hand-over and flip (the oracle twin fails even with true motion) | no |
| 33 | 0.137 | two-handed hold | **yes, by a shorter curriculum (CURR_SCALE 0.4): 0.934 ± 0.008** |
| 25 | 0.099 | board 2 twists out after insertion (contact-sensitive) | no |
| 16 | 0.077 | the spoon flips on release (contact-sensitive) | no |
| 3 | 0.072 | the pot slips in two carries (contact-sensitive) | no |
| 32 | 0.068 | the cup tips in the grasp; two-handed hold | no |
| others | ≤ 0.043 | — | — |

**Reading:**
- The three largest spreads come with overlapping collision shapes [E]. There, which way the solver pushes the overlap
  apart is decided by noise. One of them (eval 1) was cured by removing the overlap [M], which domain randomisation
  would not do [I].
- The two measured cures so far are geometry (eval 1) and more training without the assist (eval 33). Domain
  randomisation is untested.
- The episodes where it is the natural remedy are the contact-sensitive ones (25, 16, 3, 32). Supporting evidence for
  that [M]:
  - a 2 mm random COM nudge changes a zero-action replay as much as a 1–2 cm correction (physics study);
  - the sampling solver's gain vanished under 0.5 mm target noise;
  - the training box gave 0/10 bad draws where the official evaluator gave 5/22.

  All three say that small numerical differences flip outcomes when a policy has no margin.

**[H-DR]:**
- Hypothesis: training-only robustness noise lowers the 10-draw spread on contact-sensitive episodes without lowering
  the mean. The noise is observation noise on the actor input, small random pushes on the objects, and optionally
  per-world mass, friction and COM within plausible ranges. Our masses are themselves uncertain (× 0.6–1.6 [E]).
- Falsified if, on the same reference as its control, the 10-draw sd does not fall by ≥ 40 % on at least 2 of 3
  episodes, or the mean falls by > 0.02.

**Integrity traps (must be checked in code before any training):**
- The evaluator rebuilds the environment from the checkpoint's resolved config. Randomisation set through config
  (object scale, action delay, and possibly an observation-corruption toggle) can replay into the scored rollout.
- So the noise must be a training-only patch, like the VOC and FDR patches (`ops/box/fc_v2d_*.py`), with a CPU check
  that an evaluation of the resulting checkpoint is unchanged.
- Per-world physics: the Newton model arrays plus `notify_model_changed` support it, but it is untested here
  (`grasp/flashchord-capabilities-for-grasp-search.md`).

**Board value:**
- Kaggle scores the uploaded rollouts as they are, so lower spread raises the board only where a fresh draw beats the
  banked packed draw.
- Its main value is an organiser re-run or validation (expected ≈ 0.78 instead of 0.81 today [E]) and the held-out
  evaluation.

## 3. Good vs failed draw, frame by frame
- Not possible from stored data: `ops/jobs/h5_reeval.sh` kept only per-draw scores and deleted the 200 rollout files.
  The forensics give where single rollouts fail (eval 25 f171, eval 30 from f56, eval 1 f150–200) but not where a good
  and a bad draw part ways.
- **Cheapest version (CPU, $0) [H-screen]:** CPU physics is deterministic, so draws can be emulated with controlled
  perturbations of one or several components:
  - start object pose ±0.5 mm;
  - observation noise;
  - mass ±5 %;
  - friction ±5 %;
  - COM ±2 mm.

  Use about 8 rollouts per setting of the packed checkpoints of evals 25, 16, 3 (contact-sensitive) and 30 (overlap),
  recording per-frame object error (`tools/trace_rollout.py`, STATE=1 on the determined-wright branch). Report which
  component flips outcomes, and the frame where the rollouts split.
  - Caveat: CPU physics is not the GPU evaluator, and a policy rollout on CPU has to be shown to work first.
- **Faithful version (GPU, ≈ $1.5–2 [E]):** 10 official draws of the same 4 episodes with the rollout files kept (one
  line in `h5_reeval.sh`), then the same CPU analysis.
- **Decision rule, tying his two points together:**
  - if the split frames cluster at a few events (grasp onset, release, insertion), fix those events (grasp margin,
    release rule, carve);
  - if they are spread out, as he expects, train robustness ([H-DR]).

## 4. The two-part view
- It matches our split. Policy loss is 0.083 [M] and reference loss ≈ 0.10 [E]. The oracle twins add the per-episode
  picture:
  - ep11 / eval 10 is reference-limited: true motion 0.940 vs ours 0.595 [M];
  - ep13 / eval 14 is learner-limited: 0.544 with either reference [M].
- One addition [M]: a bad reference does not only cap part 2, it also makes part 2 fail. On ep11 the robot tracks the
  true motion at sim_vs_ref 0.964 but ours at 0.518, because our reference nests the cup deeper than the shapes allow.

## 5. Transfer learning
- Today every policy starts from fresh weights. A shared pretrained tracker (ManipTrans and DexTrack style) is a
  multi-day project.
- Observation size differs with the object count, so one network for all episodes needs padding or per-object-set
  models.
- A short version is to warm-start an eval policy from its public twin's policy (same objects). Rule: CLAUDE.md
  allows no policy trained on mocap references (for example the ep11 oracle policy) in eval inference. Only
  perceived-reference twins qualify. Low priority before the freeze [I].

## 6. Recommendation
1. **$0 now:** [H-screen] on CPU, with the rule written before the run. It answers his frame-by-frame question and says
   which components need randomising.
2. **Code (CPU, hours):** a training-only robustness patch (observation noise + object pushes; per-world mass/friction
   only if quick), and a CPU proof that evaluation of a checkpoint is unchanged by it.
3. **GPU, owner go-ahead (≈ $8–12 [E]):** [H-DR] A/B on evals 25, 16 and 3. Same reference per arm (REUSE_REF), 10
   official draws per arm, rule as in §2. The top-variance episodes 30 and 14 go through geometry instead (carves, as
   eval 1).
4. Transfer learning: record as future work for the report.
