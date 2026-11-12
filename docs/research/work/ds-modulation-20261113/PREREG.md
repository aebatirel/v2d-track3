# Pre-registration: DS obstacle modulation of reference wrist paths (phase 2 rules)

Written 2026-11-13, in phase 1, before any phase-2 run. CPU only, $0. Nothing in this folder has been run on a real
episode. Code: `pipeline/ds_modulate.py` (default off), `tests/test_ds_modulate.py`, `eval_ds.py` and `run_phase2.sh`
(this folder). The code is uncommitted on top of `d0e26727`. Phase 2 may start only after this file and the code are
committed; `run_phase2.sh` logs the commit and the number of dirty files.

Markers: [M] measured, [E] estimate, [H] hypothesis, [C] checked in code or docs.

## 0. Recommendation (phase 1 result)

**Do not run phase 2 as a fix for evals 1, 14, 30 and 10.** The recorded evidence shows that their "reference collision
causes" are not hand-path collisions with other objects (section 2):
- Evals 1, 14 and 30 have object–object overlaps between the manipulated object and the object it rests on or in. These
  sit at frame 0 or at the placed pose. They come from our perceived poses and from the convex-hull fill of the collision
  copy.
- Eval 10's rim hit is a misalignment inside the simulation, while the reference path itself is clear (≤ 2.4 mm).

DS modulation keeps the start and the attractor by construction, so it cannot move a start or placed pose. The paper also
requires the goal to lie outside every obstacle, yet here the obstacle is the receptacle the goal sits in.

If the owner wants the general hypothesis tested anyway, phase 2 below is about 0.5–1.5 h of one CPU core [E]. Its
first gate (section 6.1) stops it at once if our references have no hand–non-target collisions to remove.

## 1. Hypothesis [H]

Modulating a reference's wrist path around non-target objects removes more reference collisions, with less distortion,
than the existing tools. The modulation follows Khansari-Zadeh & Billard 2012 ("KZB"): normal eigenvalue 1 − 1/Γ,
tangent eigenvalue 1 + 1/Γ, attractor and timing kept.
- Collisions counted: the robot hand inside an object that is not this hand's target or held object.
- Comparator: `pipeline/robot_clearance.py`, the existing hand-side clearance tool.
- The placement and interaction carves change object collision geometry, not the hand path (section 5.2).

**What would falsify it:** on the public twins, DS removes less than 20 % of the hand–non-target collision frame-hand
pairs. It is also falsified if robot_clearance both removes more and distorts less (section 6).

## 2. Where the cited collisions come from (phase-1 findings; recorded evidence, nothing new measured)

| Eval (public twin) | Recorded collision | How it was measured | Kind | Can DS reach it? |
|---|---|---|---|---|
| 1 (ep2: pot + lid) | Lid inside the pot's hulls, up to 51 cm³; 44–50 cm³ at frame 0 and at the placed frame (f305; twin f334) | `tools/hull_census.py` (forensics 26 Oct, `docs/analysis/forensics-20261026/hull_census/ep1.json`); `placement_carve.py` overlap grid (carve BUILD 30 Oct §3) | Object–object rest overlap at both ends. Our lid pose plus hull fill; on the twin the lid-in-pot error against mocap is 6.83 cm with default hulls and 1.71 cm with the carve | No. Start and goal are fixed points of DS, and the overlap is at both of them |
| 14 (ep12 = the repo's twin; ep13 = the brief's twin; both cup + rack) | Cup inside our rack mesh (54 cm³) and hulls (72 cm³) from f42; 32.9 cm³ in motion at f44 (cup in hand during the insertion); 16.7 cm³ at the placed frame | Hull census; carve BUILD §3–4 | Held object vs its destination during insertion and at rest. The 54 cm³ in the exact mesh means our cup pose overlaps our rack: a pose or mesh error | No. The obstacle is the goal's receptacle, and KZB needs the attractor outside obstacles. After the carve removed the rest overlap, the eval-14 retrain still failed its rule (30 Oct), so the bad mode may be the task, not geometry [H] |
| 30 (ep31: sweeper + rack) | Sweeper starts inside our rack mesh (≈ 6–10 cm³ for 192 frames; 29 cm³ hulls) | Hull census; carve v1/v2 | Object–object overlap from frame 0 (perception) | No: frame 0 is DS's initial condition |
| 10 (ep11: blue + beige cup) | Beige cup hits the blue cup's rim (up to 9.65 kN), wrist 14 cm behind, cup flung | CPU replay with contact forces (`docs/analysis/ev10-stack-20261026/README.md`) | Misalignment in simulation: 3–6 cm in-hand slip plus 2–5 cm blue-cup offset. The reference's kinematic overlap with the carved pieces is ≤ 2.4 mm (`nest_pen.py`) | No. The reference path is already clear |

The robot hand hitting another object along its path is not documented anywhere for these evals. The related records:
- On 21 Oct (`robot_clearance.py`, `tools/contact_breakdown.py`; ep12, ep18, ep24, ep27), 63–88 % of frames had the robot
  hand more than 2 mm inside something. That census did not split target from non-target, and its remaining cases were
  fingers wrapped through the grasped object.
- ep18: the reference hand knocked the brush it was about to grasp (its target) at f24–28. This was fixed with
  `grasp_lock --approach_cm 15`.
- ep18: the dust pan was nudged in a soft-wrist replay (a tracking effect).
- ep35: the withdrawing hand knocked its own released spoon.

**Structural point [C]:** each of the five twins has exactly two objects (`object_body_names`: ep2 pot, lid; ep11 blue,
beige cup; ep12 and ep13 blue cup, rack; ep31 sweeper, rack). So a hand's only possible non-target object is the
receptacle its object starts in or goes into. The hand meets that receptacle in the grasp and placement zones. KZB's own
precondition, and the brief ("not the grasp itself"), exclude those zones from modulation.

## 3. Design (as built; `pipeline/ds_modulate.py` docstring has the details)

**Phases, per hand.** They are computed once, from the input reference: `pipeline/hold_phases.py` (MANO contact labels
plus our object track), the hand's collision samples, and our object surfaces.
- **APPROACH frames:** no hold, and the hand body is at least `d_pre` from the object of its next hold and from the
  object of its previous hold (grasp and release zones). This covers approach and retreat. The target, excluded from the
  obstacles, is the next hold's object, or after the last hold the object last held.
- **TRANSPORT frames:** a one-hand hold whose object is at least `d_pre` from both its origin support and its destination
  support. A support is the other object or the table, whichever is nearest at the start or end of the hold.
- **Never modulated:** grasp, release, lift-off and placement zones, and two-handed holds.

**What is moved.** Wrist translation only. The wrist and all 67 robot frames shift by the same vector, so the fingers
follow rigidly. In TRANSPORT the held object and this hand's MANO contact points shift with it. Rotation and finger
joints are unchanged.

**Moving body.** The robot's own collision meshes (FlashCHORD `{side}_sharpawave.urdf`, convex STLs, 6 mm samples), posed
by the reference's link frames, plus the held object's surface in TRANSPORT. Format check [M], on ep12's hand columns
only (no objects, no modulation, no metric): the wrist equals the `hand_C_MC` frame (0.0 mm), and all 22 URDF joint
origins agree with the frames' quaternions to 0.0 mm.

**Obstacles.**
- Every non-target object at its reference pose (convex pieces of OUR library_v3 mesh, as FlashCHORD decomposes it,
  sampled at 3 mm). A carried obstacle moves with its reference velocity (KZB's moving-obstacle form).
- The table (top of our support USDA cylinder), for held-object samples only: FlashCHORD has `robot_support_collision:
  false` in its training and manipulation collision configs [C].
- The other hand is not an obstacle; hand–hand contact is a guard.

**DS.**
- Nominal tracking DS: f = ṗ(t) + K (p(t) − x).
- Modulated: ẋ = M̄ (f − v_o) + v_o, with M_k = E diag(λn, λt, λt) Eᵀ, λn = 1 − w_k / Γ_k^(1/ρ) and
  λt = 1 + w_k / Γ_k^(1/ρ). w_k are KZB's multi-obstacle weights; the closest obstacle is applied last.
- Integration starts from x(a) = p(a), on the original frame clock (timing kept), with sub-steps of at most 1 mm.
- The deviation fades to 0 over the last 3 frames, so each window ends exactly on the original (goal kept).

**Γ.**
- The C-space distance of the translating body is d_k = min over body samples of the signed distance to obstacle k.
- Γ_k = ((d_k + R_k) / (m + R_k))²: KZB's sphere Γ (p = 1) with safety factor η = (R_k + m) / R_k. R_k is the obstacle's
  bounding radius. Γ = 1 at d = m.
- Signed distance: nearest oriented surface sample (KD tree). Point-to-plane within 2 spacings, Euclidean beyond 4.

**Documented deviations from KZB:**
1. A locality cutoff: 1/Γ is renormalised to reach exactly 0 at d = `d_inf`, so M = I beyond it.
2. Huber, Slotine & Billard's (2022) smooth tail negligence, in place of a hard switch, which keeps the velocity
   continuous.
3. A stall guard. If more than the margin is left to fade, and the fade would move the wrist faster than the reference's
   own fastest frame step in that window, the window is left unchanged and reported as stalled. These are KZB saddle
   points: a body sent head-on into an obstacle stops on its boundary.

## 4. Parameters (fixed here from geometry and the paper; the DEFAULTS dict of `ds_modulate.py`)

| Parameter | Value | Reason |
|---|---|---|
| margin m | 1.0 cm | About 2× the summed geometric error: obstacle sampling (≤ 1.3 mm distance error on a sampled sphere, unit test [M]), body sampling (6 mm spacing), our CoACD call vs the scene's (same function and defaults, possibly different vertex order), and robot_clearance's own 1 mm clearance |
| d_inf | 8 cm | The reference hand approaches at up to ≈ 2.5 cm per frame (work log 24 Oct, ep18), so modulation starts ≥ 3 frames (0.15 s at 20 fps) before contact |
| d_pre | 8 cm (= d_inf) | Grasp and placement zones: closer than this, the target or support would sit inside the influence radius; KZB needs the attractor outside obstacles |
| ρ | 1 | KZB's default reactivity |
| K | 5 s⁻¹ | τ = 0.2 s, close to the 0.16 s it takes to cross d_inf at 0.5 m/s: the deviation decays on the time scale at which modulation engages |
| fade | 3 frames | 0.15 s, about τ |
| λn, λt clips | [−1, 2] | λt = 2 is KZB's maximum, at Γ = 1; λn ≥ −1 pushes out no faster than the nominal speed |
| sub-step | ≤ 1 mm nominal travel, ≥ 4 per frame | ≤ 10 % of the margin |
| spacing | obstacles 3 mm, body 6 mm | Speed / accuracy (benchmark below) |
| geometry | `--geom fc_hulls` on `$ASSETS/mesh` (make_assets copy of `meshes/library_v3`) | What the simulator collides with, from OUR meshes |
| penetration event | > 2 mm | The threshold of the 21 Oct robot-geometry census |

## 5. Phase-2 protocol (`run_phase2.sh`)

### 5.1 Episodes, references, assets
- **Public twins only:** ep2 (eval 1), ep11 (eval 10), ep12 and ep13 (eval 14; ep12 is the repo's twin, ep13 the brief's),
  ep31 (eval 30). Eval episodes are not used. Nothing is tuned.
- **References:** the 20 Oct refsweep perc2 set, store
  `runs/20261020-refsweep-ea14fdf/refs/perc2/ep{2,11,12,13,31}/processed/...` (paths in
  `wgate/work/refsweep_perc2_paths.txt`). This is the only complete public set; 1,141 frames in all at 20 fps
  (343 / 137 / 181 / 190 / 290).
- **Staging:** `eval_ds.py stage` rewrites only `object_mesh_paths` and `object_urdf_paths` to `pipeline/make_assets.py
  meshes/library_v3` output (our meshes) and checks every other column byte-identical.
- **Ground truth:** mocap and the episode parquets' `observation.objects` pose are never read.

### 5.2 Arms
- **orig:** the staged reference.
- **clear:** `pipeline/robot_clearance.py orig out` with its defaults (3 rounds, 1 mm margin, λ 4): the existing
  hand-side tool.
- **ds:** `pipeline/ds_modulate.py` with the DEFAULTS above. It also writes `phases.json`, the labels every arm is scored
  with.
- **Placement / interaction carve: not an arm.**
  - They edit object collision copies for object–object rest overlaps and never move the hand, so their wrist distortion
    is 0 by construction and they do not act on the primary metric.
  - No carved pieces exist for these refsweep references. Building them, like the 30 Oct carve study, is out of scope.

### 5.3 Primary metric
- For every frame t and hand s, the scene is put at the reference state: `env.reset(frame_id=t)`, then CPU MuJoCo
  `mj_kinematics` and `mj_collision` on the scene's own `mj_model`, with geom margin 0 and no physics step. This is the
  simulator's own convex pieces and link meshes, a different geometry from DS's samples.
- NT(t, s) is the deepest penetration of any geom of hand s into any object other than this hand's phase target or held
  object, taken from `phases.json` of the original.
- **P_arm** = the number of (t, s) pairs with NT > 2 mm, all frames, pooled over the five episodes.
- **Distortion D95** = the 95th percentile of the wrist deviation from orig over all frame-hand pairs, in cm, pooled.

### 5.4 Secondary (reported, never change the verdict)
- P inside the DS windows only.
- Depth-weighted P (mm·frames).
- Maximum wrist deviation.
- Object-path deviation (p95 and max, cm): DS moves held objects in TRANSPORT, and that is the scored quantity.
- Stalled and total windows.
- Optional, `REPLAY=1`: zero-action physics replays (`tools/trace_rollout.py zero`) and per-object bystander displacement
  before the first hold. Descriptive only: soft-wrist zero-action replays drift on almost all frames (test C, 12 Nov).

### 5.5 Guards (DS arm)
- **TG:** hand–target pairs > 2 mm.
- **HH:** hand–hand pairs > 2 mm.
- **OOX:** held object vs another object > 2 mm in TRANSPORT frames.
- Each of TG, HH and OOX may exceed orig by at most max(5, 10 % of orig).
- Frames outside the windows, and each window's first and last frame, must be bit-identical to orig.

## 6. Decision rules (exactly `eval_ds.py verdict`, fixed now)

Let R_arm = 1 − P_arm / P_orig.
1. **NOT APPLICABLE** if P_orig < 10: our references have nothing for DS to remove. Close the idea.
2. **FAIL (falsified)** if any of these holds:
   - R_ds < 0.20;
   - R_ds < R_clear and D95_ds ≥ D95_clear (dominated);
   - any guard fails.
3. **PASS** if all of these hold:
   - R_ds ≥ 0.50;
   - D95_ds < D95_clear;
   - R_ds ≥ R_clear − 0.10.
4. **INCONCLUSIVE** otherwise.

A PASS would only justify a phase 3: a public-twin replay or a GPU retrain test with its own pre-registration. It would
not justify changing any eval reference.

## 7. Predictions (written before any run) [H]

- **Most likely, FAIL with R_ds < 0.20.**
  - P_orig is likely ≥ 10: the robot hand is larger than the human's and touches the receptacle while grasping an object
    that rests in or on it (lid on pot, sweeper in rack).
  - Those frames lie in the grasp and placement zones that DS does not modulate.
- **Second most likely, NOT APPLICABLE.**
- robot_clearance will remove more, but with larger D95: it also moves the wrist at grasp frames.

## 8. Limitations and threats to validity

- **No guarantees.**
  - KZB's guarantees hold for a point and convex obstacles; the later work extends them to star-shaped obstacles (Huber,
    Slotine & Billard 2023, arXiv 2306.16160: "the convergence guarantees are presently limited to star-shaped
    obstacles").
  - Our C-space obstacle (a non-convex rack or pot, minus a rigid hand) is not star-shaped. The unit test
    `test_concave_cspace_obstacle_documented_limitation` shows the body entering the margin at a concave waist.
- **Saddle points.** A head-on approach stalls; the stall guard then leaves the window unchanged, so DS fixes only
  grazing contacts. Tests: centre-line and head-on end-to-end.
- **Timing.** The tangential stretch (λt up to 2) moves the path up to about 1–2 cm along its direction near obstacles,
  so timing is kept at window ends but not frame by frame (tests: gap and transport). In TRANSPORT this changes the
  scored object path.
- **Window boundaries.** Phases come from MANO contact labels, which time holds 24 frames early to 22 late (note in
  `pipeline/object_events.py`). Labels are fixed from the original and shared by all arms.
- **Geometry.** DS's obstacle geometry (our CoACD call on the make_assets mesh) may differ slightly from the scene's
  pieces (Newton's loader). The metric uses the scene's own, which is conservative for DS.
- **Representativeness.** The refsweep references (20 Oct) are older than the eval references packed later (mck / gl
  variants).

## 9. Literature and code review (phase 1)

- **KZB 2012** (Auton. Robots 32:433–454).
  - I could not open the full text: EPFL Infoscience returned HTTP 429 and Springer is paywalled.
  - The forms used come from three sources: the brief; the restatement in Huber, Slotine & Billard 2022 (RA-L, arXiv
    2205.04928, §II-B: M = E D E⁻¹, E = [r, e1, …], E orthonormal for a sphere, Γ = 1 on the boundary, tail negligence
    eq. 14), which cites KZB as [19]; and the drone repository.
  - λ = 1 ∓ 1/Γ^(1/ρ) and the weights w_k are as I recall KZB, and they agree with the brief and the restatement. They
    are not verified against the PDF.
- **romanklis/ann2snn-pychromo-drone** (`a2aac4a`).
  - `field.py modulate_ds` is a planar "Billard-inspired" variant: it removes w·(v·n)n whatever the direction and adds a
    0.8 tangential stretch.
  - `control.py` uses Γ = (d/d_dead)², λr = 1 − 1/max(Γ, 0.05) and λt = 1 + 0.8/max(Γ, 0.05), with a sin² weight
    between d_dead and r_infl.
  - Its own docs state that this is not a formal guarantee, and that a global A* planner owns the route in the arms
    that reach the goal.
  - We follow KZB, not this variant.
- **Huber et al. 2023** (arXiv 2306.16160): each smooth modulated obstacle has at least one saddle point on its surface,
  and DS modulation assumes straight dynamics toward an attractor. Both match what the unit tests show.

## 10. Phase-1 test results [M] (synthetic only; `python tests/test_ds_modulate.py`, 24 of 24 pass)

| Case | Result |
|---|---|
| Point on a straight line 1 cm off a 5 cm ball's centre (original 4 cm deep) | Keeps ≥ 0.97 cm clearance with a 1 cm margin. Start and goal exact, same frame count. Detour ≤ 5.8 cm, no position jump |
| Lines 2 cm beyond d_inf, straight and curved | Bit-identical (no active sub-step) |
| Grazing at 3 cm | Bent < 1 cm |
| Head-on | Stall guard, window unchanged |
| Two-point body | Clears via the side point |
| Concave C-space waist | Margin violated (documented) |
| Moving ball past a resting point | Pushed, keeps > 0.5 margin |
| 5 cm gap between two balls | No sideways push (< 5 mm), ≤ 2 cm along the path |
| End to end on synthetic parquets (palm link, sampled meshes, support USDA, MANO contacts) | Approach: palm 1.5 cm deep → 1.08 cm clear (wrist moved ≤ 3.0 cm), grasp zone and pre-grasp frame unchanged. Head-on: unchanged. Carry: held box 1.5 cm deep → 1.0 cm clear, box and contacts moved exactly with the wrist, bystander and other hand untouched |
| Phase labels: lift-off, carry, two-handed hold, release zone between two holds | As specified |
| `eval_ds` verdict rules, target / non-target classification, ends-unchanged guard | As specified |

Runtime [M]: 30 s for one hand over a 400-frame window with three library meshes active on 80 % of sub-steps. This is
the real Sharpa sample count (4,783), at nice 10 on the shared CPU.

## 11. Expected phase-2 cost [E]

| Step | Estimate | Basis |
|---|---|---|
| DS, five episodes | ≈ 3–6 min | The benchmark above |
| CoACD of six library meshes (first call, own cache) | 1–10 min | Not measured |
| robot_clearance | ≈ 5–25 min | 4 passes × 1,141 frames of reset and step |
| Metric | ≈ 10–25 min | 15 scene builds, 3 × 1,141 resets and collision calls |
| Optional replays | 10–25 min | 24–190 s per episode measured on this container, 12 Nov |

- Total: about 0.5–1 h, or ≤ 1.5 h with replays, single-threaded, run under `nice`. $0, no GPU.
- `FLASH_CHORD_CACHE_DIR` must be set to our own scratch, because the default cache lives inside the shared FlashCHORD
  checkout.
