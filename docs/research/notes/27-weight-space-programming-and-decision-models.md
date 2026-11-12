# 27 — LLM weight-space repair of robot policies, and replacing the LLM with a decision model (2026-11-12)

Status: COMPLETE as a reading and design note. Nothing was run; every claim about a non-LLM replacement is a
hypothesis until the experiments in §7 measure it.

Owner's question: read the post, see how they use the LLM, and think how decision models could replace the LLM and
how efficient and how much better that would be.

Labels: [V] read in the primary text, [C] computed here, [E] estimate, [H] hypothesis.

Sources (all read in full or scanned on 2026-11-12):
- Stranghöner, Hartmann, Störck, Hammer, Neumann. *Repairing Robot Policies with Weight Space Programming.* Blog,
  2026-11-11. https://jstranghoener.github.io/blog/robotic-weight-space-programming/ (read in full)
- Takehi, Teoh, Zhang, Khattab. *Sparks of Weight-Space Programming.* Blog, 2026.
  https://rikiyat.github.io/blog/weight-space-programming (scanned for rules and baselines)
- Zhang, Wang, Lin. *Can LLMs Debug Robots by Editing Their Weights?* arXiv:2611.09376 (abstract only)
- Gong et al. *We Asked Opus-5.5 to Edit π0.5's Weights.* Blog, 2026.
  https://cuzyoung.github.io/robotics-weight-editing/en (scanned for cost and baselines)

Later the same day the owner pointed to the Gemini Decisions API as the product meant; see note 28 §6.
"Decision model" is read broadly here: any small trained or algorithmic model that makes the repair decisions
(which failure, which fix, which numbers) in place of the LLM. The Decision Transformer reading is design C in §4.

## 1. What the post does

- **Task [V]:** simulated cube pick-and-place into a tray (OCBench-based). The policy is behaviour cloning: three
  cameras, each through a ResNet to 256 features, plus arm readings, into an MLP head of three 256-unit ReLU layers,
  7 outputs. Head: 335,111 parameters. Trained on 8,426 noisy-expert (DART) demonstrations: 95.8% success.
- **Breakages [V]:** tray moved once; tray random per episode; cube colour changed; a forbidden zone; a human-like
  (non-Markov) teacher. Each drops success to 0–5%.
- **Result [V]:** best edit without a success-check exploit, on 500 unseen episodes:

| Experiment | Before | After | Model | Weights written |
|---|---|---|---|---|
| 1 tray moved 21 cm | 0.2% | 94.6% (0.0% at a second unseen position) | Opus 5.5 | 4,674 (1.4%) |
| 2 tray random | 5.0% | 33.2% | Opus 5.5 | 2,522 (0.75%) |
| 3 green cube | 0.0% | 71.6% | Fable 5.2 | 60,378 (18.0%) |
| 4 forbidden zone | 1.6% | 68.0% (zone entry 50.0% → 7.8%) | Fable 5.2 | 43,031 (12.8%) |
| 5 human-like teacher | 0.4% | 84.6% | Fable 5.2 | 2,731 (0.81%) |

  Other models were lower (e.g. experiment 1: Fable 5.1 93.0, Sonnet 5.5 91.2, Astra 54.4). In experiment 2, three
  models scored 46–99% only by exploiting a gap in the success check.

## 2. How the LLM is used

- **Offline, not in the control loop [V].** The LLM is a repair engineer. Its only deliverable is an edited set of
  head weights. The robot then runs the same small network with no LLM.
- **Loop [V]:** one agent run per model and experiment, reasoning effort high, 320–341 turns.
  1. It gets the weights in a Python sandbox, 200 training demonstrations, and the traces of every test it has run.
     The sandbox has no simulator. It is told what changed, not where the tray or wall is.
  2. It diagnoses. Its two main tools are swapping one input block (a camera, the arm readings) between a failing
     frame and a demonstration frame, and difference-of-means directions in the 256 camera features.
  3. It writes numpy code that sets weights, mostly in ReLU units the trained network never activates.
  4. It spends one of 25 test rounds. A round runs the current edit on the same 100 practice episodes.
  5. It reads the traces, then keeps, adjusts or drops the edit.
- **Budgets [V]:** 25 test rounds, 60 camera views, 300 code runs, one submission; chat memory resets every 40 turns.
- **Forbidden [V]:** gradients, optimizers, fitting weights to data, automated search, new demonstrations.

This rule exists because the post asks a research question: can an LLM reason in weight space? It does not claim the
LLM is the cheapest repair method, and it runs no non-LLM baseline [V].

## 3. What the LLM contributes, job by job

The LLM does four separate jobs. Only one of them needs open-ended reasoning.

| Job | What it is in the post | Needs an LLM? |
|---|---|---|
| Diagnose | which phase fails (hover, empty grasp, never touches, zone entry, tilt drift); which input block causes it | partly: the phase labels and the block swap are fixed procedures |
| Choose a fix structure | "a gated proportional controller on the base angle", "a retry reflex" | yes for new mechanisms; no for the repeating ones |
| Compile into weights | helper code such as `set_unit`, `lin_unit`, `prim`, `raw_unit` | no: deterministic |
| Tune and select | gains, thresholds, keep or drop, over 25 scored rounds | no: this is black-box optimisation |

**The fixes repeat [C].** I classified the 23 key edits the post walks through. They fall into six families, plus
two recalibrations of output weights (experiment 3 edit 4, part of experiment 4 edit 4):

| Family | What it does | Experiments (of 5) |
|---|---|---|
| T1 gated proportional controller | drives a joint or the gripper position to a fixed setpoint while a gate holds (cube held, height above a threshold) | 5 |
| T2 gated motion primitive | rise, lower, close or push by a constant while a gate holds | 4 |
| T3 empty-grasp retry reflex | closed on nothing: lift, reopen, try again; uses pose as the memory | 4 |
| T4 input correction | shift, gain or rank-one change on one camera block or the arm readings, sometimes gated | 4 |
| T5 difference-of-means detector | one unit reads a camera block along a mean-difference direction and drives T1 or T2 | 2 |
| T6 silence the trained network | a gate switches the learned units off so a hand-built controller has sole authority | 2 (plus the Fable 5.1 exploit) |

The LLM also spends many rounds on plain number tuning [V]: experiment 2 sat at 24–27% from rounds 12 to 15, and
experiment 4's rounds 21–25 only moved the edges of the guard strip.

**What does not repeat [V]:** the discoveries behind the structure. Examples: the policy only moves the arm when the
wrist camera already shows moving fingers (experiment 5); the wall shrinks camera features toward one fixed pattern
(experiment 4); shoulder and elbow follow 0.17–0.19 of a command per step but the wrist 0.33, so the retry rise
tilted the tool (experiment 3). A fixed library does not find these.

## 4. Replacement designs

**A. Repair compiler plus tuner (no learning).**
- A fixed diagnosis script: phase labels from traces, the block-swap test, a census of idle units.
- A library of the six families, each compiled into idle units.
- A decision table or tree from failure label to family.
- Bayesian optimisation or CMA-ES over each instance's 3–10 numbers, scored on practice episodes.

**B. Learned selector.** Generate many synthetic breakages (moved goals, recolouring, zones, changed dynamics). Run
design A on each and log failure signature → best family and numbers. Train a small classifier or regressor
(boosted trees or a small MLP) to pick the family and warm-start the numbers. This cuts the rollouts per repair.

**C. Sequence decision model (Decision Transformer or similar).** Treat one repair as an episode: state = failure
statistics plus the edits applied so far; action = next family and numbers; return = success. Train on design B's
logs. It helps over B only where fixes interact, which the post shows they do: the camera correction in experiment 4
added a yaw offset that later broke grasps [V]. It needs thousands of logged repairs, and each repair is thousands of
simulated episodes, so the cost moves up front and pays back only at volume.

**D. Hybrid (recommended).** The LLM proposes structure in a few calls and writes new families into the library.
The tuner does every number. Related evidence: in Zhang et al., a mechanical "full replacement" rule built from the
LLM's own finding recovered much of the gain (difference from the LLM's edit not significant at 0.05), while matched
random-direction edits did not help [V, abstract]. So structure matters and blind search is not enough, but once the
structure is known a mechanical procedure gets most of the way. Gong et al. already allowed closed-form fitting and
gradient-free search alongside the LLM [V].

Not a decision model, but the obvious competitor wherever a simulator and a reward exist: retrain or fine-tune with
RL. The post excludes it by rule and does not measure it.

## 5. Efficiency

**LLM, per repair run.**
- 320–341 turns and 2,500 practice episodes (25 × 100) [V]. Tokens, dollars and time are not reported [V].
- Anchor from Gong et al. [V]: one Opus 5.5 weight-editing run of 187 API requests took 1 h 51 min and used
  184,614 output tokens, 433,426 cache-write tokens and 36,783,281 cache-read tokens.
- At list prices (Opus 5.5 $20/M output, $0.20/M cache read; Fable 5.2 $40/M output, $0.20/M cache read; cache
  write assumed 1.25 × input) that run is about $13 on Opus 5.5 and about $19 on Fable 5.2 [C].
- Scaled to 330 turns: **about $20–40 and 3–4 hours per repair [E]**. The 40-turn memory reset would lower this and
  high effort would raise it.

**Design A, per repair run.**
- $0 of LLM. More rollouts: perhaps 50–200 rounds, so 5,000–20,000 episodes [E, a guess].
- The post gives no simulator speed. If one 100-episode round takes 1–3 minutes on one GPU [E, a guess], that is
  1–10 GPU-hours, so roughly $1–10 at our Vast prices, and it parallelises.

**Reading.**
- Per repair, the dollar saving is modest: perhaps 3–20× [E], and both are cheap next to collecting demonstrations.
- The real gains would be: no 25-round ceiling on number tuning; a deterministic, repeatable result; no frontier
  model needed at repair time; and cost per repair that falls with volume (designs B and C).
- The real loss is coverage: a library only finds fixes it already contains.
- Both can exploit a loose success check. The LLM reported its exploits in its final report [V]; a tuner would not.

## 6. Expected accuracy [H]

| Experiment | LLM best | Design A expectation | Why |
|---|---|---|---|
| 1 tray moved | 94.6% | about equal | every key edit is T1, T2, T3 or T4 with fixed targets |
| 5 human-like teacher | 84.6% | about equal, if a generic per-block shift is in the library | T1, T3 and T5 cover four of five edits; the "moving fingers" shift is a T4 instance the tuner could find without understanding it |
| 3 green cube | 71.6% | somewhat lower | T4 rank-one correction, T1 and T3 are covered; the joint-tracking fix is not |
| 4 forbidden zone | 68.0% | lower | needs the wall's geometry; a box-shaped guard region with tuned edges may recover part |
| 2 tray random | 33.2% | possibly higher, if fitting is allowed | the cap was the tray readout (5–7 cm scatter per coordinate [V]); a fitted linear readout should beat a mean difference |

Design D should be at least as good as the LLM alone, because it gives the LLM's structure more tuning rounds.

## 7. Experiments that would falsify these

- **F1 (design A matches on fixed-target repairs).** Rebuild experiment 1 on OCBench, implement T1–T4 and a tuner
  with the same 2,500 practice episodes. Falsified if unseen success is more than 5 points below 94.6% and stays
  below at 10,000 episodes.
- **F2 (tuning is the LLM's waste).** Freeze an LLM edit's structure at round 10; let a tuner use the remaining 15
  rounds. Falsified if it does not beat the LLM's own final score in at least 3 of 5 experiments.
- **F3 (fitting lifts experiment 2).** Replace the mean-difference tray readout with a ridge readout fitted on
  practice traces. Falsified if readout error does not fall below 3 cm or success stays within 5 points of 33.2%.
- **F4 (selector works).** On held-out synthetic breakages, the design B selector picks a family that reaches at
  least 80% of design A's exhaustive result. Falsified below that.

None of these is planned or costed. Each needs the OCBench setup, which we do not have.

## 8. Relevance to Track 3 [H unless marked]

- The post's constraint does not bind us: we have a simulator and a reward and may use gradients.
- Retraining one of our policies is cheaper than an LLM repair: 250M steps ≈ 1.5–2 h per policy (note 23), so
  about $1–2.5 at $0.55–1.18/h [C], against about $20–40 [E].
- What may transfer:
  - the diagnosis routine (phase labels per rollout, then an input-block swap) as a CPU script for the
    high-variance evals 1, 14, 25, 30, 33;
  - hand-written gated reflexes such as the empty-grasp retry. We can add those in the reference or controller. They
    need to live inside the weights only if a checkpoint must carry all behaviour, for example if the organisers
    re-run checkpoints. Not checked against our checkpoint format or the kit rules.
- No change to the submission or the plan follows from this note.

## 9. Testing it on our own policies (added 2026-11-12, owner: "can we see if the llm method helps with better policies")

### 9.1 What the checkpoints allow (checked on CPU, $0)

- **Network [V].** Read from FlashCHORD's `training/flash_sac/network.py` (NVIDIA `video_to_data` main, 1e862a8,
  12 Nov 2026) and our checkpoint metadata. Batch norm on 722 inputs → linear to 256 → two residual blocks
  (256 → 1024 → ReLU → 256 → ReLU, batch norm on each, plus the skip) → RMS norm → 56 action residuals.
  1.28M stored numbers. Eval mode uses the stored batch-norm statistics, so the forward pass is fixed and editable.
- **Inputs are physical quantities [V].** Wrist and finger state, object pose, the reference command relative to the
  hands and object, the previous action, and per-slot contact positions and force directions. This is easier to
  write controllers on than the post's camera features.
- **Outputs are bounded corrections to our reference [V].** Wrist position scale 0.05, clip 0.2; wrist
  orientation scale 0.15, clip 1.0; fingers scale 0.15, clip 1.0; smoothing 0.3. An edit can only nudge the
  reference, not replace it.
- **Idle units [C, rough].** Estimated from batch-norm bias and scale, assuming normalised Gaussian inputs
  (`tools/actor_np.py census`):
  - first block's 1024 wide units: 14–225 idle per checkpoint across the 10 public 250M/150M checkpoints;
  - second block's: 1–142 idle;
  - the two short fine-tuned spoon checkpoints: none idle;
  - the 256-wide layers: none idle.
  So there is room for small circuits, but every write passes through a 256-wide layer that is always in use, then
  a whole-vector RMS norm. That is harder than the post's plain network. Real counts need recorded observations.
- **Not done:** the numpy forward (`tools/actor_np.py`) is not yet checked against JAX.

### 9.2 Where it could help, and where not [H]

- **The post's main lever is missing.** Its policies failed under a distribution shift and retraining was banned. Ours
  are trained with RL in the same simulator and on the same reference that the evaluator uses.
- **The plausible lever is rare failures.** Several packed policies vary widely between evaluator draws (evals 1, 14,
  25, 30, 33; sd up to 0.24, H5, 29 Oct). A reflex such as a grip tighten or retry when the object slips could cut
  that spread.
- **Unlikely to help** where the reference is wrong (2–3 cm perception errors, collisions written into the
  reference), because the edit can only nudge the reference.
- **Bar to beat:** a reseed or retrain costs about $1–2.5 per policy.

### 9.3 Pilot plan (not started; needs the owner's go-ahead)

Public episodes only; ground truth is read only after the loop ends.

1. **Stage 0, CPU, $0:** check the numpy forward against JAX on CPU. Write a fixed rule that picks 3 public
   episodes (policy-side failures or high draw spread; public twins of the high-variance evals where they exist).
2. **Stage 1, one GPU box, about 1 h, about $1–2 [E]:** 10 evaluator draws per episode with the current policy.
   Record observations, actions, contacts and body poses (`tools/trace_rollout.py` needs an observation and action
   recorder added).
3. **Stage 2, CPU, $0 of GPU:** the agent reads weights and traces, states a mechanism and a predicted effect, and
   writes at most 2 edits per episode per round. Shapes stay unchanged, so the evaluator loads edited checkpoints.
4. **Stage 3, GPU, up to 6 rounds:** each round runs every edit for 10 draws. The loop sees only the GT-free score
   (`pipeline/qa.py policy`: simulation against our reference).
5. **Baseline:** one reseeded retrain per episode at the packed recipe, with 10 draws.

**Cost [E].** About 2.5 min per evaluator draw (work log, 15 min for 6 evaluations) at $0.55–1.18/h. GPU about
$10–20 for the whole pilot, plus the agent's Claude usage (hundreds of turns; not a Vast cost).

**Rule, fixed now.** After the loop, 10 fresh draws per arm are scored against ground truth with the kit scorer.
- **Helps:** the final edit raises mean AUC by ≥ 0.02 over the original, without a larger sd, on at least 2 of 3
  episodes, and is not below the reseed baseline on those episodes.
- **Falsified:** the gain is < 0.005 on all 3 episodes, or the edit is below the reseed baseline on at least 2.
- **Otherwise:** inconclusive.

**Open before any submission use.**
- Whether the competition allows a hand-edited checkpoint.
- The leaderboard scores the submitted rollouts as they are, so an edit counts only through new rollouts, which the
  owner uploads.
