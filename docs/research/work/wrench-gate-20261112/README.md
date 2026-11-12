# Wrench-feasibility gate: pre-registered public test (2026-11-12, note 29 idea 1)

**Status: NOT RUN. The data the pre-registered rule needs are not in the store. There is no verdict and no AUROC.**
- Official evaluator rollouts exist for only 11 of the 20 public episodes, spread over many recipes.
- No single recipe covers more than 6 public episodes (4 per results group).
- 9 public episodes have no rollout at all.

The gate is built and tested. The scoring script is ready and refuses to run until the data exist.

Labels: [M] measured here, [C] computed, [E] estimate, [H] hypothesis.

## 1. Rule (pre-registered, work log "2026-11-12 ~22:20 UTC … PRE-REGISTRATION", unchanged)

- **Score:** per reference frame in held phases, the residual of the task wrench (`pipeline/task_wrench.py`) after a
  non-negative fit in the cone of the contact wrenches. The friction cone has 8 edges plus the normal, as in exercise
  3's `contacts.py`. The residual is divided by the task-wrench norm. Inputs are only our reference.
- **Label:** per frame, the official evaluator rollout's object deviates more than 2 cm from our reference. This uses
  no ground truth.
- **Data:** the 20 public episodes.
- **Verdict:**
  - informative if the pooled AUROC is ≥ 0.75 and ≥ 8 episodes contribute positives;
  - falsified if AUROC < 0.65;
  - otherwise inconclusive.
- **CI:** 95%, by episode bootstrap.

## 2. Method: `pipeline/wrench_gate.py` (inference only, no ground truth)

- **Demand:** W = [F ; τ/r_c] in the world frame, about the centre of mass (COM).
  - F = m(a − g) and τ = I_w α + ω × I_w ω, from `task_wrench.wrench`: Savitzky-Golay derivatives of our object
    track (window 9, 20 fps).
  - `task_wrench` takes a diagonal inertia, so the object frame is turned onto the inertia's principal axes. This
    leaves the COM track, ω and R I Rᵀ unchanged.
- **Supply:** every active contact slot on the object, from both hands.
  - `mkref.py` writes 16 slots per hand in `CONTACT_SLOT_NAMES` order (= `PROBE_SITES` + palm). Each slot holds a
    world-frame point on the object surface and a unit normal pointing into the object. Its part id is the body index
    + 1.
  - A slot is active when its part id matches and |normal| > 10⁻³ (the `hold_phases.py` convention).
  - Each contact gives 8 unit edge rays plus the normal, with the Frisvad tangent basis, line for line as in exercise
    3's `contacts.py` and FlashCHORD's `objectives/wrench.py`.
  - Generator: [f ; ((p − c) × f)/r_c], with c the COM at that frame. Demand and supply share the world frame and the
    COM.
- **Score:** min over λ ≥ 0 of |Gλ − W| / |W| (scipy `nnls`).
  - 0 means the demand lies inside the contact wrench cone.
  - 1 means there are no contacts, or none can push in the needed direction.
  - A point contact carries no torsional friction. The simulator's condim-3 contacts have none either (note 24 §1).
- **Frames (object-event windows, as in `grasp_lock --events`):** for each hold of an object (`hold_phases.py`, both
  hands merged), the window runs from the object's lift-off (`object_events.hold_events`) to the frame after its last
  movement inside the hold. That end frame is `hold_events`' settle frame. I use it even when `hold_events` rejects it
  as a placement, so a still tail resting on a rack or a pot is left out.
  - The contact labels only assign events to holds. MANO labels are mistimed by up to ~24 frames, so they set no
    window edges.
  - Objects that are never lifted (slid, or never touched) get no window.
- **Parameters, with their sources:**

  | Parameter | Value | Source |
  |---|---|---|
  | μ | 1.0 | FlashCHORD scene. `configs/scene/{train,eval}.yaml` sets `contact_friction: 1.0`; `setup.py` then leaves shapes at Newton 1.2.0's `ShapeConfig.mu = 1.0` [V]. Measured as 1.0 in note 24 §1 [M]. |
  | m | 0.3 kg | URDF `<mass>`. All 10 kit URDFs of the public objects read 0.3 [M], as does `make_assets.py`. |
  | COM, inertia | URDF `<inertial>` | What the simulator uses. Fallbacks: a uniform solid of the object's mesh at mass m (convex hull if not watertight), then the body origin with a solid sphere of radius r_c. The fallback in use is reported per object. |
  | r_c | `object_mesh_radius` from the reference | FlashCHORD's own torque scale: the largest vertex distance from the vertex mean. |
  | infeasible | score > 0.5 | Pre-registered threshold for the secondary statistic. |

- **Self-test** (`score_gate.py selftest`, 21 checks, all pass) [M]:
  - antipodal pinch holds the weight: residual 0, also at μ 0.1;
  - one side contact at the COM: 1/√2;
  - support from below: 0; push from above only: 1; no contacts: 1;
  - cone half-angle 45° at μ = 1;
  - demand force m(a − g) exact on a constant-acceleration track;
  - ω × Iω about a non-principal axis within 10⁻¹⁷ N m of the analytic value (target 1.2 × 10⁻³ N m);
  - AUROC tie handling matches brute force; verdict thresholds.

## 3. Analysis plan (fixed before any label was computed; no label has been computed)

- **Unit:** one (object, frame) pair inside a held window.
- **Label:** |achieved − reference| object position > 0.02 m.
  - Rows: `environment_id` = min of the rollout parquet, matched by `reference_frame`.
  - A frame with no row, or with `environment_valid` false, counts as positive (object lost).
- **Rollouts:** exactly one official evaluator rollout per episode (the first official draw of the policy trained on
  that reference). All 20 episodes come from one recipe.
- **Provenance check:** every rollout must replay its reference, with max |`reference_position` − our
  `object_body_position`| < 1 mm. Otherwise the script refuses to run.
  - Tested on real data: the ev3 run's ep12 rollout replays `perc2mc/ep12` exactly (0.0 mm). The Oct 20 `perc2/ep12`
    reference differs by 10.4 mm, so a wrong pairing is caught [M].
  - Only the reference columns were read; no achieved position.
- **AUROC:** Mann-Whitney with mid-ranks. A higher score predicts deviation. Pooled over all units.
- **CI:** 2,000 episode-bootstrap resamples (seed 20261112), percentile 2.5 / 97.5. One-class resamples are skipped and
  counted.
- **Positive episodes:** episodes with at least one positive unit.
- **Secondary (descriptive only):** per episode, the share of units with score > 0.5 against the mean sim-vs-reference
  error over the held units, and over all rollout frames. Spearman ρ.
- **Window refinement:** the end-of-window rule above was set after inspecting window geometry only (no score-label
  pairing). Ending at the hold end when no placement is accepted would have kept static tails of up to 78 frames
  (ep2 lid on the pot).
- **End-to-end check:** the scoring path was exercised on synthetic rollouts built from three public references (no
  real outcome read). It returned AUROC 1.0 and "inconclusive" (3 < 8 positive episodes). A 5 mm reference shift
  triggers the provenance refusal [M].

## 4. Data: what exists and what is missing

**Store inventory** (`score_gate.py list` + `inventory`; private HF dataset `aebatirel/v2d-store`): recursive
listing of all 226 runs (267,746 files), 12 Nov 2026 [M]. Rollouts are `runs/<run>/results/<group>/…/episode_0000NN.parquet`
for public episode ids (`pipeline/run_public.sh`).

| Public episode | Runs holding an official evaluator rollout |
|---|---|
| 0, 22, 23, 40, 41, 42, 43, 44, 45 | **none** |
| 2 | 17 |
| 11 | 5 |
| 12 | 68 |
| 13 | 4 |
| 18 | 64 |
| 21 | 4 |
| 24 | 31 |
| 26 | 1 |
| 27 | 55 |
| 31 | 7 |
| 39 | 3 |

**Largest single-recipe coverage:**
- Largest results group: 4 public episodes (12, 18, 24, 27), e.g. `runs/20261022-r1a-65c5a52/results/final`.
- Largest run: `runs/20261024-ev3-2c1e4dd`, 6 episodes (2, 12, 18, 24, 27, 39) under mixed groups and reference
  recipes.
- The `pf*` runs (1–3 Nov) are almost all eval-episode retrains. Their public rollouts are ep13 (`pfA`, `pfE`) and
  ep31 (`pfH`).
- Git holds no public rollout parquet on any branch [M].

**References for the full public set:**
- Only `runs/20261020-refsweep-ea14fdf/refs/perc2`, with 19 of 20 episodes (ep26 missing). No policy was ever trained
  on all of them.
- The work logs of all branches record no policy training on all 20 public episodes. `refs_sweep.sh` was "no
  training".

**What is missing:** for one recipe (one code commit, one reference builder, one training recipe), a trained policy
and its first official evaluator rollout on each of the 20 public episodes.
- 9 episodes have no rollout at all.
- The other 11 have rollouts only from different, incompatible recipes.
- Nothing was substituted.

## 5. What was run (all CPU, this cloud container, 4 cores; $0)

- **Code version:** working tree of branch `claude/gallant-franklin-8gvsv3`. The parent session committed WIP copies:
  a9f71461, c134272b, 61c0b6ad. The final files are the ones in this folder and `pipeline/wrench_gate.py`; commit them
  before citing.
- **Python:** scratch venv with numpy 2.5.4, scipy 1.18.1, pyarrow 26.0.1, trimesh 5.2.1.
- **Downloads:** ≈ 25 MB in the session scratchpad (`wgate/store/`):
  - 19 public references (`runs/20261020-refsweep-ea14fdf/refs/perc2/ep*/processed/…`);
  - two `perc2mc` refs and one rollout from `runs/20261024-ev3-2c1e4dd`, used only for the provenance check;
  - kit URDFs for the 10 public objects (`nvidia/video_to_data_challenge`, `track_3/public/urdf/`).
- **Commands:**
  - `python -I -B score_gate.py selftest`: SELFTEST OK.
  - `python -I -B score_gate.py inventory TREES OUT`: inventory above.
  - `python -I -B pipeline/wrench_gate.py REF --assets KIT --json OUT --frames`: run on each of the 19 references,
    21 s in total.

## 6. Gate output on the 19 public references (inference only, no labels; NOT the test)

These are the Oct 20 `perc2` references with kit URDFs (all objects from URDF, 0.3 kg). They are not the references
any rollout above was trained on. They show only that the gate's output is not degenerate.
- Pooled: 3,167 (object, frame) units [M].
- 72% exactly feasible (score 0); 17.3% infeasible (> 0.5).
- Score percentiles 50 / 75 / 90 / 95: 0 / 0.15 / 0.92 / 1.0.

| ep | held units | infeasible share | no-contact share | rollouts in store |
|---|---|---|---|---|
| 0 | 48 | 0.02 | 0 | none |
| 2 | 128 | 0.20 | 0 | 17 runs |
| 11 | 104 | 0.46 | 0 | 5 |
| 12 | 88 | 0.00 | 0 | 68 |
| 13 | 120 | 0.40 | 0 | 4 |
| 18 | 236 | 0.06 | 0 | 64 |
| 21 | 194 | 0.30 | 0.28 (pitcher) | 4 |
| 22 | 176 | 0.30 | 0.28 (pitcher) | none |
| 23 | 240 | 0.02 | 0 | none |
| 24 | 249 | 0.27 | 0.25 | 31 |
| 26 | — (no reference in the set) | — | — | 1 |
| 27 | 117 | 0.13 | 0 | 55 |
| 31 | 213 | 0.64 (sweeper) | 0 | 7 |
| 39 | 213 | 0.17 | 0.15 | 3 |
| 40 | 159 | 0.00 | 0 | none |
| 41 | 195 | 0.01 | 0 | none |
| 42 | 158 | 0.01 | 0 | none |
| 43 | 236 | 0.05 | 0 | none |
| 44 | 115 | 0.17 | 0 | none |
| 45 | 178 | 0.05 | 0 | none |

"No-contact" means an object in the air with no contact slot on it in that frame: a reference defect the gate scores
as 1.

## 7. Verdict

**None. The test is blocked by missing data:** no one-recipe set of 20 public official evaluator rollouts exists. AUROC,
CI and the count of positive episodes were not computed.

## 8. Limitations (apply when the test is run)

- **Cone shape:** the gate's 8-edge cone is inscribed in the circular μ = 1 cone. Its weakest direction has effective
  μ = cos 22.5° ≈ 0.92. The simulator's pyramidal condim-3 cone is a diamond, with an effective μ of 0.71 on its
  diagonals (note 24 §1). So the gate is slightly more permissive than the simulator.
  - A μ = 1/√2 run would be a descriptive sensitivity check only.
- **Unbounded forces:** contact forces have no magnitude limit. A grasp is "feasible" if any force mix works, even
  one that needs more squeeze than the fingers can give (effort 10 N m, kp 1.7) or than the policy learns.
- **Reference contacts, not simulated ones:** contacts are the reference's own MANO-derived slots, gated and
  deflickered by `mkref`. The policy may grasp differently in simulation.
- **Approximate physics:** mass is the kit's placeholder 0.3 kg, and COM and inertia are a surface estimate.
  Accelerations come from a smoothed perceived track, so jitter adds demand.
- **Unscored frames:** frames outside object-event windows are not scored. That includes objects carried without a
  labelled hold, and the load phase before lift-off.
- **Correlated units:** frames are strongly autocorrelated within an episode. The episode bootstrap accounts for
  this; a per-frame pooled AUROC is dominated by long episodes.

## 9. What would unblock it (the owner decides; nothing was rented)

- **A. The pre-registered test as written.** One GPU batch: build references with one recipe for all 20 public
  episodes (perception + hands + mkref; the Oct 20 `perc2` set lacks ep26), train one policy each, and take one
  official evaluator draw each.
  - Training alone ≈ $1–2.5 per policy (note 27 [C]), so ≈ $20–50 for 20 [E], plus reference building.
  - Then run `score_gate.py score MANIFEST OUT` once.
- **B. A weaker amended test, pre-registered before any scoring.** Use the 11 episodes with some rollout, one per
  episode from mixed recipes, each paired with the reference that passes the provenance check.
  - Reaching "≥ 8 episodes with positives" would need 8 of 11.
  - This is a change of rule and needs a new work-log entry first.
- **C. A different label (note 29 test (a)), pre-registered first.** Use the drift of a zero-residual physics replay
  of each reference, on CPU at $0 [H].
  - Needs FlashCHORD running on CPU here. Not checked: exercise 3 ran Newton on CPU, but our scene and FlashCHORD's
    env were not tried.
  - It answers a different question: can the reference be carried open-loop, rather than does the trained policy
    leave it.
