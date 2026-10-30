# Object physics study (30 Oct 2026): public scans first

Owner's goal: understand the physics of the episodes before choosing a robot embodiment. Keep the simulator's own world
(solver, contact model, global friction 1.0); give each object plausible physical properties instead of NVIDIA's
placeholder ("Track 3 supplies no measured physical properties. 0.3 kg is a placeholder mass", public URDF comment).
Owner, 30 Oct: "first try it with the public given meshes, later we go to the generated meshes"; centre of gravity first.

Markers: [M] measured here, [E] estimate, [H] hypothesis with its falsification test. No ground truth is read except by
the final scoring of public rollouts against mocap (registered AUC), after inference.

## Rules we keep (owner accepted 30 Oct)
- One value set per object, shared by every episode; physically plausible; never fitted to mocap or to eval results;
  declared in the technical report.
- Only object properties change (mass, centre of mass, inertia). Global friction (`scene.contact_friction` 1.0), object
  damping (0) and every `sim` setting stay at the recipe defaults.

## Step 1: mass properties [M/E]
`pipeline/object_physics.py` on the meshes the simulator uses (`scanlib2`: NVIDIA's public scans; the boards and the
sweeper use NVIDIA's `_collision.glb`, as their public URDFs do). Material model per object:
`materials_public_scans.json` (materials from the public videos; masses are estimates, plausibly ×0.6–×1.6).
Output: `props_public_scans.json`. Asset build: `pipeline/make_assets.py LIB OUT --physics props_public_scans.json`.

## Step 2: CPU zero-action test (pre-registered 30 Oct ~10:20 UTC, before any result)
- Episodes (public; stored base references of the 24 Oct recipe validation): ep2 pot + lid (`20261024-ev3-2c1e4dd`
  perc2mck), ep12 cup into rack (`20261024-ev2-2c1e4dd` perc2mc), ep18 sweeper + dust pan (ev3 perc2mc), ep24 boards
  (ev3 perc2mc).
- Arms: **S0** = scans with the placeholder (0.3 kg, shell inertia) — the control; **S1** = scans with
  `props_public_scans.json`. Everything else identical.
- Per arm and episode, on this container's CPU (FlashCHORD at the evaluator pin, 1 world): `grasp_lock.py` (frozen
  GL_ARGS of the recipe arms) → `wrist_ilc.py` (4 iterations, kp 400 embodiment) → zero-action replay
  (`trace_rollout.py zero`) → `trace_score.py` (sim_vs_ref, our reference, no ground truth) and `rest_check.py`.
  No evolutionary refinement (GPU only).
- Reading, fixed now: Δ = S1 − S0 zero-action sim_vs_ref per episode.
  - **signal:** mean Δ ≥ +0.03 and no episode Δ ≤ −0.05;
  - **harm:** mean Δ ≤ −0.03 or any episode Δ ≤ −0.10;
  - otherwise **neutral**.
  CPU physics is deterministic, so one replay per arm. This is a no-policy test: it says whether the hand reference
  holds and moves lighter / heavier objects better, not what RL makes of it.

## Step 3: GPU retrain (owner approved 30 Oct; pre-registered 09:50 UTC, before any result)
- Job `ops/jobs/physics_arms.sh` (commit 6a814df): the frozen grasp-lock recipe of the 29 Oct recipe arms (GL_ARGS,
  EVOLVE=1, kp 400 wrist, FDR + VOC fix, 70M steps, seed 42, CURVE_REP 3, NREP 5) with REUSE_REF off (grasp lock, ILC
  and the evolutionary refinement are rebuilt under each arm's physics) and SF=0 (scans), on ep2, ep12, ep18, ep24.
- Boxes: S0 `20261030-physS0-6a814df` (instance 58386066, RTX PRO 6000 S, UK, $1.348/h); S1
  `20261030-physS1-6a814df` (58386069, RTX PRO 6000 WS, KR, $1.177/h). Ledger: $6.50 planned each [E].
- Reading, fixed now (registered AUC vs mocap of the chosen checkpoint, mean of 5 official evaluations; the checkpoint is
  chosen by sim_vs_ref only): Δ = S1 − S0 per episode.
  - **signal:** mean Δ ≥ +0.03 and no episode Δ ≤ −0.05;
  - **harm:** mean Δ ≤ −0.03 or any episode Δ ≤ −0.10;
  - otherwise **inconclusive**.
  One seed per arm and a rollout sd up to ~0.12 (ep24) make this weak: a signal buys a second seed, not adoption.
- Understanding readouts (no decision attached): zero-action sim_vs_ref and rest check per arm (with EVOLVE), the
  per-checkpoint curves, which objects slip or drop, and where.

## Results
(below, appended as they come; nothing above is edited after a result)
