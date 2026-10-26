# Status (2026-10-26)

Also read `docs/context-and-decisions.md` for the owner's goals, preferences and earlier answers.

## Goal and constraints
- **Goal:** top of the NVIDIA V2D Challenge Track 3 leaderboard (ranked by AUC), plus the Industry Innovation award.
  Freeze 2026-11-04 17:00 EST. The owner said "anything goes" for the leaderboard, within the rules.
- **Budget:** the professor considered $1,000–1,500 reasonable. The plan below needs about $110–200 of GPU time.
- **Owner-only actions:** Vast.ai account and credit, challenge registration, accepting the Kaggle Track 3 rules,
  sharing a repo with the organisers (this one or a cleaned copy), uploading submissions. The agent cannot sign up,
  sign in or pay.

## How Track 3 is scored (verified from the kit)
- Submitted rows must be **FlashCHORD rollouts from the official evaluator** of a trained policy per eval episode, with
  evaluator code digests, a checkpoint digest and a GitHub commit URL on every row. Perception output alone cannot be
  submitted. The packer is `tools/pack_submission.py` in the kit.
- 20 eval episodes: 1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38. Their objects are in the
  kit's `data/track_3_evaluation_objects.json`. **Wooden spoon in 10** (3, 5, 6, 15, 16, 32, 33, 35, 36, 37; slot 0 and
  alone in 35–37). **White pot in 6** (1, 3, 5, 6, 8, 28).
- Metrics: one rigid warp from slot 0 at frame 0, no scale fix. AUC = ADD swept over 1–9 cm (trapezoid; ranking metric);
  SP-SR (≤ 10 cm and ≤ 0.5 rad); MP-SR (< 3 cm and < 30° for every object); RPE; MPPE (6 points at 5 cm).
- Leaderboard on 2026-10-12: SoySauceChicken AUC 0.765 / SP 0.80 / MP 0.50 / MPPE 3.0 / CD-O 0.583. Other teams
  0.23–0.37. Leaving every object at its frame-0 pose scores about 0.446.

## What works (measured)
- **Simulator and evaluator on Colab G4** (RTX PRO 6000 96 GB):
  - FlashCHORD at the evaluator pin (`8c778f90`); jax 0.10.2, warp 1.14, newton 1.2, mujoco 3.8.1.
  - Sharpa FlashSAC trains at about 45,300 env steps/s with a 40.5 GB peak (`XLA_PYTHON_CLIENT_PREALLOCATE=false`),
    so a 250M-step policy takes about 1.5–2 h.
  - The official evaluator (1 world, trajectory export) works. A 20M-step tissue-box policy scored AUC 0.918 against
    its own reference.
- **Perception** (`pipeline/perc2.py`) on the 20 public episodes, scored with the kit's metric functions against mocap:
  **mean AUC 0.809, SP 0.90, MP 0.85, MPPE 4.76 cm**. Per episode:
  - 0.986–0.998: 12, 13, 23, 27, 40.
  - 0.935–0.962: 18, 22. Episode 2 ≈ 0.98, inferred from the mean.
  - 0.795–0.887: 11, 21, 24, 31, 41, 42, 43, 44, 45.
  - Failures: 39 at 0.550 (dustpan offset about 5 cm once moving); 0 at 0.179 (lid 180° symmetric, so its rotation
    is wrong from frame 0); 26 at 0.031 (white pot inside the white rack; wrong detections).
- **Hands:** MediaPipe 0.10.14 on the **colour** camera finds two hands in 173/181 (ep 12) and 338/373 (ep 0) frames.
  On the mono cameras it finds almost none.
- **Retargeting without MANO is feasible.** NVIDIA's `ego_recon_to_sharpa.py` reads only 21 joint positions plus
  orientations, in MediaPipe order. See `docs/research/notes/22-hand-reference-contract.md`.

## Staging for Vast (2026-10-20): see `docs/runbook-vast.md`
- **Ready off the clock.** Scripts are written but not yet run on Vast (only `ops/vast.sh offers` was tested on the
  live market):
  - `ops/vast.sh`: launch, list, logs, label and destroy through the API with curl;
  - `ops/box/`: on-start, bootstrap, HF store, stall watchdog, self-destroy;
  - `ops/jobs/smoke.sh` (box 0) and `ops/jobs/day1.sh` (box 1);
  - `pipeline/fetch_data.sh`: the whole 1.47 GB dataset;
  - `pipeline/oracle_poses.py`: the evaluation-only mocap oracle.
- **Changed in the pipeline:**
  - `setup.sh` now also installs CUDA dev headers, both hand venvs and the MediaPipe model, and can pull weights from
    the HF mirror.
  - `pipeline_ep.sh` now defaults to the validated **perc2** (it ran the unvalidated perc4 before), keeps one output
    folder per variant and seed, supports `PERC=oracle`, and resumes training from the newest `state_` checkpoint.
- **Found today:**
  - FlashCHORD resumes (`training.resume=true training.checkpoint_path=<state file>`) and checkpoints every 5M steps;
    the replay buffer is not saved by default.
  - The Vast image `vastai/pytorch:2.11.0-cu130-cuda-13.2-mini-py313-2026-10-16` matches Colab's torch, CUDA and
    Python.
  - PRO 6000 WS on demand costs $1.45–1.65/h all-in (market on 2026-10-20 afternoon); interruptible from $0.54/h.
- **Storage:** a private HF dataset repo (`HF_STORE` in `ops/config.env`) holds the weight mirror, environment
  snapshots, depth caches and run outputs. Git holds code and summaries. Boxes never push to git.
- **Keys:**
  - Vast key and HF read token → network secrets in the Claude cloud environment.
  - HF write token and GitHub read-only token → Vast account env vars (narrow scope, expiring).
  - Owner checklist: runbook §3.

## Policy-stage research (2026-10-26, note 23; nothing run in the simulator yet)
- **Wrist control is the biggest policy lever, and it is config-only [computed, hypothesis for effect].**
  - The default floating wrist is a soft spring (kp 25 N/m). At real speed it spends its 0.2 m residual range on object
    weight (11.8 cm sag) and damping lag (0.24 s × speed), and saturates on 23 of 27 public moving tracks.
  - kp ≥ 100 removes saturation in every sensitivity rerun; kp 50 is marginal.
  - The ball wrist is over-damped (ζ ≈ 4–5.5); kd 1.5–3 removes rotation saturation.
  - The verified Hydra recipe and its traps are in note 23 §B: list all five joint_overrides; set effort_limit,
    `action.wrist_kp` and `action.wrist_tau_max`.
- **The hand already feels contact.** Live contact points and force directions are observed, and the PD error acts as a
  weight sensor. Force magnitude needs code (not for submission). The critic sees object velocity but the actor does not:
  `observation.object_body_velocity.enabled=true` is a config-only slip signal.
- **Kalman filtering belongs in the reference.** perc2 object poses are unsmoothed. Plan a robust offline smoother with
  rest snap and hand-object attachment during carries.
- **Reference contact labels can penalise carrying.** If the reference hand is more than 18 mm from the object, the −10
  unintended-contact penalty fires on the grip.
- **Train/eval start mismatch.** Training resets hold 1 s with full assist; the evaluator starts unassisted at frame 0.
- **Physics knobs (cone, impratio, friction, object scale, delay) replay unchecked** into the scored rollout:
  off-limits. The sim uses pyramidal cone + impratio 20, which MuJoCo advises against.
- **Plan (note 23 §E):**
  - CPU reference audit first;
  - smoother test on regenerated perc2 poses;
  - then GPU batch G1 on public eps 11, 23, 13, 42 (+27): wrist-gain arms, ball damping, a policy bundle and reference
    feed-forward. Full G1 is 30 runs, ≈ $75–100 on demand; a first slice is 16 runs, ≈ $40–55. Needs the owner's
    go-ahead after day 1.

## Written, not run yet (first things to test)
- `hands_mp.py` → `mkref.py` → `pipeline_ep.sh` → `score_sim.py`. `README_ref.md` lists the checks to do first:
  - pinocchio frame/finger/task counts should be 67/22/11;
  - `daqp` must be available;
  - hand overlay alignment and handedness;
  - URDF warnings;
  - contact fractions;
  - FlashCHORD `load_reference` validation;
  - Hydra quoting of a path containing `=`.
- `perc.py` (perc4): render-and-compare detection check plus reworked VO. Episode 0 with `KF_MIN=250` scored worse
  (0.087): masking leaves fewer features, so a keyframe was added nearly every frame. A rerun with `KF_MIN=120` was
  interrupted. Validate it against perc2 per episode before adopting it.

## Key facts and gotchas
- **Cameras:**
  - Videos are stored upright; do not rotate them.
  - The mono stereo pair is left = `ego_cam_c`, right = `ego_cam_b`, about 75 mm apart. Rectified focal length
    ≈ 600.2 px, baseline 0.0755 m.
  - `ego_cam_a`'s `extrinsics_to_stereo_left` maps cam_a to **cam_b**: X_b = R X_a + t.
  - Stereo frame k pairs with cam_a frame k+1, with a few clips at k+2. cam_a is rolling shutter (31.6 ms per height).
- **Timing rule (note 06):** write `fps=20.0` and exactly N frames, train with `task.motion_speed=1.0` and `sim=rl`
  (20 fps). The default `motion_speed` of 0.5 silently breaks the frame mapping.
- **Quaternions:** the public parquet `pose` is `[x, y, z, qw, qx, qy, qz]`. The kit and evaluator export use xyzw.
- **Detection:**
  - OWLv2 text prompts fail on mono images.
  - FoundationPose's register score is not comparable across masks (a rack fragment scored 143, the true cup 73).
  - Use the scan-matching detector: SAM2 proposals × DINOv2 against 42 grey renders, a 3-D size gate and an
    intensity term.
- **Symmetric objects** (lid, cups, pot body) need spin disambiguation. Note 17 found marker-based correction works
  (marker-only lid AUC 0.977).
- **Room map (note 18):** a public-frames SfM map relocalises all eval clips with about 1–2 mm accuracy, worth about
  +0.06–0.07 AUC over our VO. Not yet integrated.
- **Spoon:** the parametric model is in `spoon/`. The scan-frame rule gives **frame A by a near-tie**
  (P(B) ≈ 0.40–0.45; ≈ 0.17 if the organisers' scan lacks markers). This contradicts note 13's "commit to B". Decide
  from evidence (owner's choice); the owner can check overlays visually on request.
- **Setup gotchas:**
  - Background jobs started from an interactive terminal must use `setsid nohup … < /dev/null`, or apt gets
    SIGTTIN-stopped.
  - FoundationStereo's top-level `Utils` module shadows FoundationPose's; purge it from `sys.modules`.
  - The FoundationStereo cfg needs `vit_size`. New transformers renamed OWLv2's post-processing function.
  - `warp-lang` is required by FoundationPose.
  - Two GPU jobs sharing a card can OOM.
- MediaPipe ≥ 1.x dropped `mp.solutions`; pin 0.10.14. pin 4.1 (pinocchio) has `buildModelFromMJCF`.
- CoACD collision hulls differ by platform; build and evaluate on Linux x86_64.

## GPU plan (from `docs/gpu-rental/report.md`)
- **Vast.ai RTX PRO 6000 96 GB**, about $1.0–1.2/h on demand or $0.5–0.6 interruptible, billed per second.
  - Filters: `cuda_vers>=13.0 cpu_cores_effective>=16 cpu_ram>=65536 reliability>=0.98`, 200 GB disk.
  - Check each host's storage and bandwidth prices.
  - Destroy instances instead of stopping them.
- Fallbacks: RunPod Community $1.69/h, Nebius $1.80/h, RunPod Secure $2.49/h.
- Costs: first public end-to-end test $4–12; first submission (20 policies on 5–10 parallel machines) $35–50;
  campaign about $110.
- To verify on the first host (under $5): throughput (and Max-Q variants), two jobs on one GPU, whether training can
  resume from a checkpoint (needed before using interruptible machines), and restore time.
- **Remote access:** an agent working from a cloud session needs its own SSH key added to the owner's Vast account, and
  the cloud environment needs outbound network access to the rented host. Never commit private keys.

## Running from a Claude Code cloud session (checked against the docs, 2026-10-20)
- **Cost:** included in the owner's Claude plan; usage counts toward the plan's limits; no charge for the cloud VM.
  The VM is small (about 4 vCPU, 16 GB RAM, 30 GB disk, no GPU), which is enough to orchestrate. All GPU work runs on
  Vast.
- **SSH out may not work.** Cloud traffic goes through an HTTP/HTTPS proxy, and raw SSH to arbitrary hosts or ports
  is not documented. **First action in a new cloud session:** with network access set to Full, run
  `ssh -o BatchMode=yes -p <port> root@<host> true` against a Vast box and record the result here.
- **If SSH is blocked**, drive Vast over HTTPS only:
  - create instances through the API with an on-start script that clones this repo and runs the job on its own;
  - push results to git or object storage over HTTPS;
  - read logs through the Vast API;
  - self-destroy at the end.

  Interactive debugging then needs another route, such as Jupyter over HTTPS on the box or the owner opening a
  session on the box.
- **Vast API key:** store it as a *network secret* on the environment (allowed host `console.vast.ai`), never as an
  environment variable or file. The proxy adds the header outside the VM. Vast's v0 API takes
  `Authorization: Bearer <key>`; this header format has not been verified.
- **Idle pauses:** the VM pauses after a few idle minutes. The conversation survives, but background shell commands
  and loops do not. Long jobs must therefore run on the GPU box by themselves (nohup + self-destroy + stall watchdog) and
  must never depend on the cloud session staying awake.
- Each session starts from a fresh clone, so commit and push everything. Private repos need the Claude GitHub App
  installed on the repo, or `/web-setup` from a terminal.

## Next actions, in order
1. Owner checklist in `docs/runbook-vast.md` §3:
   - new Vast key and credit;
   - HF store repo and the two tokens;
   - the GitHub read-only PAT and the Claude GitHub App;
   - cloud environment network secrets;
   - go-ahead for the day-1 batch (about $14–16, ceiling $25).
2. Box 0 smoke test (`ops/jobs/smoke.sh`). It checks SSH from the cloud session, env injection, HF write, the label
   and self-destroy. Record each result here.
3. Box 1 `ops/jobs/day1.sh`:
   - setup and environment snapshot;
   - perc2 on ep 12;
   - resume test;
   - ep 12 trained twice at once, on perception objects and on the evaluation-only mocap oracle, which separates
     tracking error from robot error;
   - evaluate and `score_sim`.

   Then ep 22 and 27 from the snapshot.
4. Policy-stage levers (note 23 §E): CPU reference feasibility and contact-label audit; then batch G1 (wrist gains,
   ball damping, actor object velocity, start alignment) on public episodes after the owner's go-ahead.
5. Perception fixes, validated on public episodes:
   - detection check (perc4 verify);
   - marker spin for lid and cups;
   - VO drift (room map or loop closure);
   - track recovery (re-registration, bidirectional tracking, full-resolution depth);
   - rest snap and table snap;
   - robust offline object smoothing (note 23).
6. Spoon: fit the template to the eval videos (`spoon/fit_spoon.py` skeleton), track it, decide the frame from
   evidence; ask the owner for visual checks of overlays.
7. Eval run: perception on the 20 eval videos → references → 20 trainings in parallel → evaluator → kit
   `pack_submission.py` → owner uploads. Commit the exact code first (provenance).
8. Iterate: up to 5 submissions a week, unlimited in the final 3 days. Train several seeds per episode and keep the
   best.

## Expected score (estimates, not measurements)
- Tracking on eval videos: about 0.72–0.81, depending on the spoon.
- First submission after the robot's losses: about 0.60–0.75.
- After fixes: about 0.75–0.85.
- The first public end-to-end test replaces these guesses.
