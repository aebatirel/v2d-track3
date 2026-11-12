# 29 — NVIDIA's tutorial exercise 3, and where LLMs and decision models fit our pipeline (2026-11-12)

Status: READING + one CPU run of the exercise (§1.3). Every improvement in §3 is a hypothesis with a test; nothing in
our pipeline was changed. Builds on notes 27 (LLM weight editing) and 28 (Gemini Decisions API).

Owner's question: "look at these links go for exercise 3 and see how we can improve the pipeline with llms and
decision models based on the research in this session" (https://nvidia-isaac.github.io/video_to_data/v2d_corl_tutorial/exercises/).

Labels: [V] read in the source, [M] measured here, [C] computed, [E] estimate, [H] hypothesis.

## 1. What exercise 3 is

### 1.1 Contents [V]
- Source: `docs/v2d_corl_tutorial/exercises/exercise_3.zip` in nvidia-isaac/video_to_data (main 1e862a8, 12 Nov 2026).
  Exercise 1's ZIP is a Git LFS pointer and was not downloaded. Exercises 2, 4 and 5 are not published yet. The
  schedule lists exercise 3 as "dexterous skill training" and exercise 5 as "agentic orchestration".
- One notebook, CPU only: two Tianji arms with Sharpa hands hand over a flask (sequence P0003_cbee62a7_seg013,
  1,023 reference frames at 20 fps). Its five cells:
  1. **Kinematic replay:** the retargeted reference is written straight into the joints, with no physics.
  2. **Dynamics replay:** the same reference played in Newton physics with PD control and zero policy residual.
     The point: a kinematically right reference can still fail physically.
  3. **Contact wrench support:** each annotated contact point gets a friction cone (8 edge rays plus the normal,
     μ = 0.1). Each ray becomes a 6-D wrench [f, (p×f)/r] with r = 0.168 m. Support is
     h(u) = max(0, maxᵢ uᵀwᵢ) over 512 fixed 6-D directions. A direction with zero support is one the grasp cannot
     push in; the notebook points at frame 250 for this.
  4. **Training:** only prints the FlashCHORD Hydra command (FlashSAC, 250M steps, 32 worlds).
  5. **Evaluation:** a bundled trained policy, numpy inference plus Newton on CPU. It stops on object error > 0.10 m,
     object rotation > 0.5 rad or wrist error > 0.15 m.
- Two built-in knobs make it a test bed: `Simulation(delay_steps=0…12)` adds 0–60 ms of control delay; physics
  parameters sit in `assets/model/calibration.npz`.

### 1.2 Same policy architecture as ours [V, M]
- The bundled actor (`policy.py`, 332 inputs, 58 outputs) has exactly the structure of our checkpoints (722 inputs,
  56 outputs): batch norm, a 256-wide embedding, two residual blocks of 1,024 wide units, RMS norm, a gained mean head
  and a final tanh.
- Our `tools/actor_np.py` gives identical actions to NVIDIA's `policy.py` on two of our checkpoints (ep12 public
  250M and the 504-input spoon fine-tune): maximum difference 0.0 on 256 sampled inputs [M]. This confirms our name
  mapping. A check against JAX itself is still not done.

### 1.3 CPU run here [M]
Machine: this cloud container (4 CPU cores, no GPU), Python 3.12 venv with the exercise's pinned packages (Newton
1.2.0, Warp 1.14.0, MuJoCo 3.8.1). Runner: headless, no viewer, the exercise's own `simulation.py` and `policy.py`.

| Run | Result | Compute |
|---|---|---|
| Zero-residual replay (cell 2), full 1,023 frames | flask lost: max object error 0.81 m, 757 frames over 0.10 m | 12.0 s |
| Bundled trained policy (cell 5), delay 0 | **fails at 17.6 s (frame 353 of 1,023)**: object error 0.101 m against the 0.10 m limit. Median error before that 1.3 cm; error at frames 300 / 340 / 352 = 0.9 / 7.2 / 10.1 cm, so a sudden slip | 6.0 s for 353 frames |
| Same policy run again | identical rollout (max difference 0.0): deterministic | 6.0 s |

So the notebook's "fully trained" policy does not complete on this x86 Linux CPU. NVIDIA tested it on Apple M4 /
macOS; a platform difference in CPU physics is the likely cause, not checked. Either way it gives a reproducible
failing policy at no cost, and a full-length rollout costs about 17 s here.

## 2. Lessons from the exercise for our pipeline

1. **Check a reference in physics before training.** Cell 2 is our `tools/trace_rollout.py zero` plus
   `tools/trace_score.py`: the reference with zero residual, scored against itself. Note 23 §E proposed it as a
   screen before training on 22 Oct, and grasp-lock work uses it. I found no record that it became a gate for every
   episode.
2. **Check grasp capability per frame.** Cell 3 measures what the hand contacts can push. We have only the demand
   side: `pipeline/task_wrench.py` computes the wrench the object's motion needs, m(a − g) and Iα + ω×Iω. Putting
   the two together asks whether the grasp can produce the wrench the motion needs. We have never computed that.
3. **The policy loop can run on a CPU.** Cell 5 runs the same kind of policy closed loop without a GPU. That gives a
   free test bed for weight editing (note 27 §9), where the LLM has to repair because retraining is impossible on a
   CPU. That is exactly the blog post's setting.

## 3. Improvements, ranked [H]

| # | Stage | Kind | What | Test (public only, pre-registered before results) | Cost |
|---|---|---|---|---|---|
| 1 | reference, before training | analytic decision model | **Wrench-feasibility gate.** For each frame and hold, is the task wrench (`task_wrench.py`) inside the cone spanned by the contact wrenches (exercise 3's generators on our MANO contacts)? Solved as non-negative least squares; the residual is the score. Flags holds the reference cannot physically carry, and routes them to `grasp_lock`, contact retargeting or a grip choice. | Does the infeasible-frame share predict (a) the zero-residual replay's object drift and (b) the final policy's sim-vs-reference loss on the 20 public episodes? Informative if AUROC ≥ 0.75 for frames with drift > 2 cm, falsified if < 0.65 (the depth audit's bars). | CPU, $0 |
| 2 | policy | LLM weight editing (note 27) | **Pilot on exercise 3 first.** The bundled policy already fails here, deterministically, at 17.6 s (§1.3). The LLM repairs it by editing weights, with a 17 s CPU rollout as its test tool, a budget of 25 rollouts and the post's rules (no gradients, no fitting, no automated search). Then 20 perturbed starts (start frames 0–40, delay 0–4 steps) check the repair is not a one-rollout fit. Baselines: unedited, and an edit of the same size in a random direction. | Repair counts if the edited policy completes the reference and completes ≥ 10 more of the 20 perturbed starts than the unedited one, without failing a start the unedited one completes. If it fails here, skip the GPU pilot on our episodes. | CPU, $0 (Claude usage only) |
| 3 | between stages | small decision model | **Route each episode's fix** (keep, reseed, grasp-lock fine-tune, placement carve, grip change), with a tiny decision tree on GT-free features: zero-residual replay score, wrench-feasibility share, hold count, object size, draw-to-draw spread. Today these are separate hand rules (`tools/choose_learner.py`, `tools/grip_choose.py`, H5 carve rule). | Leave-one-episode-out on public episodes: the tree's choice beats the current rules' choice in mean AUC. With about 20 episodes, keep it to depth 2 or plain rules. | CPU, $0 |
| 4 | after rollouts | LLM triage | **Failure labels and a fix proposal per episode.** An LLM reads `tools/rollout_forensics.py` output, contact traces and hold phases, labels the failure (drop at lift, slip in carry, collision, placement offset, never grasps) and proposes a fix family. A fixed rule, not the LLM, decides what runs. | The LLM's label agrees with a human label (owner, on public overlays only) on ≥ 80% of failed public episodes. | Claude usage only |
| 5 | after rollouts | visual decision model | **Gemini Decisions API judge** (note 28, ideas 1 and 6): rollout render against the source video. | As in note 28 §5. | ≈ $1 API, needs a key |

**Ranking reasons.**
- Idea 1 comes first: it targets the error source the evidence points at (the reference side), it is pure physics with
  no model to trust, and every input already exists.
- Idea 2 is the cheapest honest test of note 27's method; it moves the GPU decision from a guess to a measurement.
- Ideas 3–5 depend on 1 and 2 producing features or labels worth routing on.

## 4. What does not transfer

- **The exercise scene is not ours.** Fixed Tianji arms, not floating hands; 332 inputs, not 722; one flask. Results
  of idea 2 show whether the method works on this kind of policy, not on our episodes.
- **Different contact source.** Exercise 3's contacts come from the reconstruction ("in-house"). Ours would come from
  MANO contact labels, which are 24 frames early to 22 late (`pipeline/object_events.py`); idea 1 must use the
  object-event windows, not the raw labels.
- **Missing inputs for idea 1.** The cone test needs friction μ and object mass. The exercise uses μ = 0.1 for
  display; the simulator's real friction values must be read from the FlashCHORD scene.

## 5. Open
- Whether submissions or checkpoint re-runs are still possible; this decides whether any gain matters on the board.
- Exercise 5 (agentic orchestration) is not published yet; it may show NVIDIA's own LLM workflow.
