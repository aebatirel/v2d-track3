# Contact-blob decision tree (2026-11-12; owner: "use the physical contact blob from exercise 3 … through the decision tree")

Labels: [M] measured, [H] hypothesis. Rule pre-registered in `docs/work-log.md` (~23:05 UTC) before any physics label
existed.

## 1. What it is
- **The blob:** exercise 3's 6-D contact-wrench support, h(u) = max(0, maxᵢ uᵀwᵢ). It measures how hard the hands'
  contacts can push the object in each force/torque direction.
- **Features:** `tools/blob_features.py` turns it into 8 features per held frame of our references, reusing
  `pipeline/wrench_gate.py`'s contact wrench generators:
  - the gate score;
  - push along the needed wrench;
  - push straight up;
  - share of 512 directions with no push;
  - contacts;
  - hands;
  - force and torque needed.
- **Tree:** `tools/blob_tree.py` trains a small decision tree (depth 3) leave-one-episode-out and compares it with the
  gate score alone.
- **Status:** both scripts are frozen in git (314515e9) before any label. Checked on synthetic labels only: a planted
  signal gives 0.815 vs the gate's 0.692 ("adds value"), and random labels give 0.496 vs 0.502 ("no added value").
- **The real test** waits for test C's physics labels (zero-residual replay drift on the 19 public references); the
  gate agent is producing them.

## 2. Exercise 3, descriptive only (one episode, no verdict) [M]
- **Inputs:**
  - the flask's reference pose and its annotated contacts (`trajectory_contacts.npz`; the exercise labels a contact
    by "reference proximity ≤ 10 mm");
  - flask mass 1.0 kg and inertia from `flask_newton.xml`;
  - torque scale 0.168 m as in the exercise.
- **Friction:**
  - The exercise's simulator uses μ = 1.0 on every geom (`calibration.npz` `geom_friction`). That is the physical
    case: `ex3_blob_timeline_mu1.0.png`.
  - The exercise's display uses μ = 0.1: `ex3_blob_timeline_mu0.1.png`.

| | μ 1.0 (simulator) | μ 0.1 (display) |
|---|---|---|
| frames scored infeasible (> 0.5), all 1,023 | 5.0% | 40.3% |
| right hand only (120 frames) | 15% | 100% |
| both hands (248) | 0% | 72% |
| left hand only (655) | 5% | 17% |

- **Physics:**
  - the zero-residual replay leaves the reference by 2 cm at frame 54 (2.7 s) and by 10 cm at frame 93 (4.7 s);
  - the trained policy stays within about 2 cm until 15.5 s, then fails at 17.6 s, at the handover, as the right
    hand lets go.
- **Reading [H]:**
  - At the simulator's friction, the reference's contacts say the grasp can hold the flask almost all the time, yet
    physics loses it within 3 s with no policy. The policy then fails at a handover that the reference's contacts
    call strong (score 0, push up ≈ 0.99).
  - So the blob of the reference's kinematic contacts did not foresee either failure here. These contacts are
    proximity labels, and a PD-tracked hand does not reproduce them in physics: the exercise's own cell-2 lesson.
  - At μ 0.1 the early phase looks infeasible and "matches" the replay's drop. That match is spurious, because the
    simulator does not use μ 0.1.
- **Consequence for the pre-registered test:** one episode cannot falsify it, but it lowers the prior for both the
  gate and the tree. If test C fails too, the next feature set should come from contacts the simulator actually
  makes (replay or rollout contact readout, `tools/trace_rollout.py CONTACTS=1`), not from the reference's labels.
  That is a different, post-physics question.

## Files
- `ex3_blob.py`, `zero_err.py`: the descriptive run (exercise 3 venv for the replay, then plain numpy/scipy).
- `ex3_blob_timeline_mu1.0.png`, `ex3_blob_timeline_mu0.1.png`.

## 3. Result on test C's labels (2026-11-12 ~23:55 UTC) [M]
- **Verdict: inconclusive** (pre-registered share rule): 99.6% of the 3,167 rows are positive, because the
  zero-residual replay never grips.
- Out-of-fold AUROC 0.58 vs the gate's 0.41; difference 0.17, CI [−0.14, 0.79]; 12 negative rows. Not interpreted.
  Full output: `results_tree.json`.

