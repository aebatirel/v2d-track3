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

### Step 2 result (CPU zero-action, 30 Oct 09:45–10:20 UTC, code 299274e / fc75ac4) [M]
Machine: this cloud container (4 CPU), FlashCHORD at the evaluator pin, 1 world, CPU. Outputs: scratchpad
`phys/{S0,S1}/out/ep*/` (run.log, zero.npz, gl.log). Per-object detail: `tools/trace_objects.py`.

| episode | floor | S0 (0.3 kg) | S1 (plausible) | Δ |
|---|---|---|---|---|
| ep2 pot + lid | 0.506 | 0.179 | 0.141 | −0.038 |
| ep12 cup → rack | 0.605 | 0.551 | 0.600 | +0.049 |
| ep18 sweeper + dust pan | 0.619 | 0.214 | 0.279 | +0.065 |
| ep24 boards | 0.220 | 0.196 | 0.203 | +0.007 |

Mean Δ +0.021 → **neutral** by the pre-registered rule (signal needs ≥ +0.03; no episode ≤ −0.05, none ≤ −0.10).
Readings [M]:
- Every arm leaves the reference early (first object > 3 cm off at frames 11–61) and all but ep24 score below the
  do-nothing floor: grasp holds and contact geometry dominate, mass is second order at zero action.
- ep12: the copied human grip loses the cup ~1 cm into the lift (f37) at 128 g and at 300 g; S1's gain is the heavier
  rack (387 g) not being knocked by the dropped cup (S0: 12 cm at the end).
- ep2: pot and lid are off 13–17 cm / ~70° from f44–61, before the pot's hold starts (f105): the lid–pot collision
  shapes overlap (as the 30 Oct carve study found on our meshes), not a mass effect.
- ep24: S0 throws board 1 ≈ 80 cm (f137); S1 ≈ 23 cm.
No GPU decision depends on this (the GPU arms were approved regardless); it says the no-policy replay is limited by
contacts, so RL is where a mass effect could show.
