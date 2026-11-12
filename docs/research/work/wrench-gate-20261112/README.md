# Wrench-feasibility gate: pre-registered public test (2026-11-12, note 29 idea 1)

**Status: NOT RUN. The data the pre-registered rule needs are not in the store. There is no verdict and no AUROC.**
- Official evaluator rollouts exist for only 11 of the 20 public episodes, spread over many recipes.
- No single recipe covers more than 6 public episodes (4 per results group).
- 9 public episodes have no rollout at all.

The gate is built and tested. The scoring script is ready and refuses to run until the data exist.

**Test C was run (section 10; label = zero-residual replay drift, CPU, $0): INCONCLUSIVE by the pre-registered
positive-share rule.** 99.6% of held frames are positive, because the replay lifts almost no object. Pooled AUROC 0.41,
95% CI [0.06, 0.59].

**Test C2 was run (section 11; label = grasp-locked replay): INCONCLUSIVE by the same rule.** 98.6% of held frames
are positive. Pooled AUROC 0.53, 95% CI [0.33, 0.66]. The blob tree on the same rows is also inconclusive.

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

## 10. Test C: zero-residual replay label (run 2026-11-12, CPU, $0)

**Verdict: INCONCLUSIVE.** The pre-registered positive-share rule decides it: 99.6% of held frames are positive
(3,155 of 3,167), above the 90% bar.
- Pooled AUROC 0.41, 95% episode-bootstrap CI [0.06, 0.59] (2,000 resamples, seed 20261112; 1 one-class resample
  skipped).
- All 19 episodes contribute positives.
- The AUROC rests on only 12 negative units in 6 episodes, so it carries no information [M].

### 10.1 Rule (work log "2026-11-12 ~22:55 UTC — PRE-REGISTRATION, idea 1 test C", unchanged)

- **Gate:** `pipeline/wrench_gate.py` as committed in 61c0b6ad. `score_C.py` refuses to run if `git diff 61c0b6ad`
  of that file is not empty.
- **Data:** the 19 references `runs/20261020-refsweep-ea14fdf/refs/perc2/ep*/processed/…` (ep26 is missing).
- **Label:** a FlashCHORD zero-residual replay on CPU (VOC 0, zero policy action, `tools/trace_rollout.py zero`, the
  recipe's controller settings).
  - Per (object, frame) in the gate's held windows: positive if the simulated object is more than 2 cm from the
    reference.
  - A missing or non-finite row counts as positive.
- **Verdict:**
  - informative if AUROC ≥ 0.75 and ≥ 8 episodes contribute positives;
  - falsified if AUROC < 0.65;
  - otherwise inconclusive, and also inconclusive if under 10% or over 90% of held frames are positive.
- **Order of rules:** `score_C.py` applies the share rule before the AUROC bars. A share outside [0.10, 0.90] is
  inconclusive whatever the AUROC. That is my reading of "also inconclusive".

### 10.2 Setup and exact commands

- **FlashCHORD at the evaluator pin.** The version is `nvidia-isaac/video_to_data` 8c778f905cb35f76f8e6cd6e2ea486da4fb9e0ef,
  the pin in `pipeline/setup.sh` that our training and evaluation boxes use. I did not use the shallow clone at
  `/home/user/nvidia-isaac/video_to_data` (main 1e862a8): it is a newer version, and its LFS meshes are pointer stubs.
  - In the scratchpad `wgate/fc/`:

        git init -q v2d && cd v2d && git remote add origin https://github.com/nvidia-isaac/video_to_data.git
        GIT_LFS_SKIP_SMUDGE=1 git fetch -q --depth 1 origin 8c778f905cb35f76f8e6cd6e2ea486da4fb9e0ef
        GIT_LFS_SKIP_SMUDGE=1 git checkout -q FETCH_HEAD

  - The session's git proxy refuses `git lfs pull` for this repository: it is not attached, and attaching does not
    serve LFS on the anonymous lane.
  - The 346 LFS files under `flash_chord/src/flash_chord/assets/meshes/sharpawave` (212 MB) came from
    `https://media.githubusercontent.com/media/nvidia-isaac/video_to_data/<pin>/<path>`.
    `wgate/fc/lfs_media.py` verified each one against the sha256 and size in its pointer: 346 of 346.
  - Venv:

        cd v2d/robotic_grounding/flash_chord && uv venv --python /usr/bin/python3.11 .venv && uv sync --frozen

    No `train` extra, so no JAX. It gives Python 3.11.18, flash_chord 0.4.0, Newton 1.2.0, Warp 1.14.0, MuJoCo 3.8.1,
    mujoco-warp 3.8.1, CoACD 1.0.11 and numpy 2.4.6.
- **References and assets.** The references name their objects as `/content/t3/{urdf,mesh}/…`, the kit's public scans.
  - Fetched from `nvidia/video_to_data_challenge`: `track_3/public/urdf/*_rigid.urdf` and `track_3/public/mesh/**`
    (10 objects, 89 MB).
  - The support stages came from the store, `refs/perc2/ep*/reconstructed_stage/t3_ep0NN_support.usda`.
  - `wgate/scripts/stage_refs.py` writes a replay copy of each reference. Only `object_mesh_paths` and
    `object_urdf_paths` are rewritten to the local kit files. Every other column was checked to be identical.
  - The gate and the labels read the original downloaded files.
- **Replay** (`wgate/scripts/run_zero.sh EP`), from the flash_chord directory, with N = the reference's frame count:

      DEV=cpu OMP_NUM_THREADS=1 .venv/bin/python -B /home/user/v2d-track3/tools/trace_rollout.py zero OUT/epEP.npz REF N

  - ep12 ran first, alone. The other 18 then ran with `xargs -P 3`.
  - Settings, all from `trace_rollout.py` and the stock configs:
    - controller: `experiment=sharpa_flash_sac` with its default embodiment `sharpa_hands`, the standard learner's
      controller; action `residual_hand_pose` (wrist kp 25, wrist τ_max 45, EMA 0.3);
    - sim `rl`: 20 fps × 5 substeps, pyramidal cone, impratio 20, njmax 512;
    - `voc_scale=0`, `env.step(None)` (zero residual), auto-reset off, terminations off, motion speed 1.0, one world;
    - support on, CoACD collision decomposition on.
  - Our FDR, VOC-inertia and start patches are training-only, or act only at VOC > 0, and were not applied.
  - `EMB=sharpa_hands_mid` (the kp 400 wrist) belongs to the grasp-lock recipe, not to these references, and was not
    used.
- **Scoring** (scratch venv with numpy 2.5.4, scipy 1.18.1, pyarrow 26.0.1, trimesh 5.2.1):

      python -I -B docs/research/work/wrench-gate-20261112/score_C.py MANIFEST.json OUT_DIR

  The manifest holds, per episode, the store-copy reference and its `zero.npz`, with `assets` = the kit folder.
- **Timings** [M]:
  - ep12 alone: 262 s for 181 frames, including the Warp kernel builds.
  - The other 18 with 3 in parallel: 24–190 s each, 230 s wall.
  - Scoring: under a minute.
  - All 19 replays exit 0. Each trace has one row per reference frame (0 … T−1). The frame-0 object offset is 0.0 mm
    in all 19.
- **Outputs:**
  - `results_C.json`: statistics, per-episode table, settings, timings, descriptive label diagnostics.
  - `labels_C.csv`: `episode,object,frame,label`, exactly the gate's 3,167 held-window rows. Its key set was checked
    equal to the gate output.
  - The traces (`wgate/replayC/out/ep*.npz`, 5.7 MB) stay in the session scratchpad.

### 10.3 Per-episode table

Columns: positives out of held units; the gate's share of frames scoring > 0.5; mean sim-vs-reference error over the
held units; median height rise of the object above its frame-0 height in the held frames, simulated vs reference.

| ep | positives / held | gate infeasible | mean err held (cm) | rise sim / ref (cm, median) |
|---|---|---|---|---|
| 0 | 48 / 48 | 0.02 | 15.3 | lid −1.0 / 1.8 |
| 2 | 127 / 128 | 0.20 | 9.7 | pot −0.2 / 6.2; lid 1.1 / 2.7 |
| 11 | 103 / 104 | 0.46 | 13.7 | blue cup 0.0 / 3.7; beige cup 0.0 / 7.9 |
| 12 | 88 / 88 | 0.00 | 15.9 | 0.0 / 11.8 |
| 13 | 120 / 120 | 0.40 | 25.2 | −4.5 / 8.9 |
| 18 | 236 / 236 | 0.06 | 7.0 | sweeper −4.1 / 1.2; dust pan −0.1 / 2.0 |
| 21 | 188 / 194 | 0.30 | 18.5 | cup 0.0 / 6.4; pitcher −7.8 / 15.5 |
| 22 | 176 / 176 | 0.30 | 18.9 | cup 0.0 / 5.3; pitcher −7.0 / 9.3 |
| 23 | 240 / 240 | 0.02 | 15.7 | piece 1 −0.4 / 6.6; piece 2 0.0 / 14.9 |
| 24 | 247 / 249 | 0.27 | 14.3 | piece 1 10.2 / 19.6; piece 2 −0.2 / 9.1 |
| 27 | 117 / 117 | 0.13 | 29.2 | 0.1 / 24.5 |
| 31 | 212 / 213 | 0.64 | 10.1 | 0.4 / 0.9 |
| 39 | 213 / 213 | 0.17 | 21.7 | 0.0 / 15.0 |
| 40 | 159 / 159 | 0.00 | 20.3 | −0.1 / 21.6 |
| 41 | 194 / 195 | 0.01 | 11.8 | 4.7 / 14.2 |
| 42 | 158 / 158 | 0.01 | 9.0 | −0.2 / 4.7 |
| 43 | 236 / 236 | 0.05 | 12.1 | 0.1 / 9.4 |
| 44 | 115 / 115 | 0.17 | 14.4 | −0.1 / 18.9 |
| 45 | 178 / 178 | 0.05 | 20.4 | −0.3 / 20.8 |

- **Negatives:** the 12 negatives are in ep2 (1), ep11 (1), ep21 (6), ep24 (2), ep31 (1) and ep41 (1).
  Within-episode AUROCs (in `results_C.json`) rest on 1–6 negatives and mean nothing.
- **Secondary, descriptive only:** Spearman ρ between the gate's infeasible share and the mean error is 0.05 over held
  units and 0.05 over all frames.

### 10.4 What the label measured [M] and why it cannot test the gate [H]

- **Before lift-off the replay follows the reference.** The median object error before the first lift-off is 0.1–1.6
  cm. The exception is ep24 piece 1 at 10.1 cm: it already leaves the reference in the replay before its reference
  lift-off.
- **After lift-off the object stays down.** In the held windows the simulated object mostly stays at table height
  (median rise −7.8 to +10.2 cm; within ±1.1 cm for 20 of 26 objects) while the reference rises 1–25 cm.
- **So the replay lifts almost nothing.** The reference hands are PD-tracked with no squeeze and no policy, and do not
  grip. This matches note 24 (zero-action holds need a designed squeeze) and exercise 3 (the zero-residual replay
  loses the flask).
- **Reading [H]:** the label is close to a constant "no open-loop grip". It does not separate the frames the gate
  separates, so these references cannot answer the question.
- **A new test would need a new pre-registration.** One option: replay grasp-locked references (`grasp_lock.py` +
  `wrist_ilc.py`, kp-400 wrist), where zero replays sometimes hold. It is informative only if its positive share
  falls inside 10–90%; otherwise it is inconclusive in the same way.
- **Test A** (official policy rollouts) stays blocked by data (section 4).

### 10.5 Limitations

- **Old references:** these are the Oct 20 references; current references (grasp lock, refine stage) were not tested.
- **Stock replay settings:** njmax 512 is the stock sim config; some later recipes used 1024. Too small a buffer can
  drop contacts in crowded frames, which was not checked.
- **Assets:** objects are the kit's public scans, which is what these references name.

## 11. Test C2: grasp-locked replay label (run 2026-11-12/13, CPU, $0)

**Verdict: INCONCLUSIVE**, again by the pre-registered positive-share rule: 98.6% of held frames are positive (3,122 of
3,167), over the 90% bar.
- Pooled AUROC 0.53, 95% episode-bootstrap CI [0.33, 0.66] (2,000 resamples, seed 20261112; 8 one-class resamples
  skipped).
- All 19 episodes contribute positives.
- No episode failed grasp lock or ILC (0 of 19 against the limit of 5).
- **Blob tree on the same rows** (`tools/blob_tree.py`, rule of 12 Nov ~23:05 UTC): also inconclusive by the share
  rule. The tree's out-of-fold AUROC is 0.35 against the gate's 0.53, a difference of −0.18 with 95% CI [−0.23, 0.09]
  (`docs/research/work/blob-tree-20261112/results_tree_C2.json`) [M].

### 11.1 Rule (work log "2026-11-13 ~00:50 UTC — owner: okay go crazy … PRE-REGISTRATION of tests C2, G-A and G-B")

- **Gate and blob features:** unchanged. The gate is frozen at 61c0b6ad and runs on the 19 original refsweep perc2
  references. `score_C2.py` refuses to run if the gate file differs.
- **Label:** the grasp-locked physics replay of each reference, on CPU, using the `tools/cpu_glock_zero.sh` chain:
  `grasp_lock.py` with default args, then `wrist_ilc.py` at kp 400 for 4 iterations, then a zero-action replay with
  `sharpa_hands_mid`.
  - Positive if the object is more than 2 cm from the replayed reference's object pose.
  - A missing or non-finite row counts as positive.
- **Exclusions:** episodes where grasp lock or ILC fails are excluded. More than 5 of 19 failures makes the test
  inconclusive.
- **Bars:** the same verdict bars and 10–90% share rule as test C.
- **Object trajectory:** grasp lock and ILC leave it unchanged on all 19 episodes: the largest change between
  `ref_gl_ilc.parquet` and the original is 0.0 mm and 0.0° [M]. The label uses the replayed reference's own object
  pose, which here is identical to the original.

### 11.2 Commands and settings

- **Runner:** `wgate/scripts/run_glock.sh EP` in the session scratchpad follows `tools/cpu_glock_zero.sh` step by step
  with the same settings and environment, and with local paths. Input: the staged reference copy of test C (only the
  asset paths rewritten). It runs from the 8c778f9 flash_chord directory with `OMP_NUM_THREADS=1`:

      FC=$FCD GL_WRIST_KP=400 $PY -B pipeline/grasp_lock.py $D/ref_in.parquet $D/ref_gl.parquet
      EMB=sharpa_hands_mid $PY -B pipeline/wrist_ilc.py $D/ref_gl.parquet $D/ref_gl_ilc.parquet --iters 4 --device cpu
      EMB=sharpa_hands_mid DEV=cpu $PY -B tools/trace_rollout.py zero $ARM/zero.npz $D/ref_gl_ilc.parquet N

  - `flashchord_conf/embodiment/sharpa_hands_mid.yaml` (wrist xyz kp 400, kd 20, 150 N) was copied into the scratch
    FlashCHORD configs, as `ops/jobs/glock_public.sh` does on the boxes.
  - The script's last step, `trace_score.py` (the kit's sim-vs-reference score), was not run: it is not part of the
    label.
- **Code and environment:** repository HEAD 983bd272 for all 19 runs. `grasp_lock.py`, `wrist_ilc.py`,
  `trace_rollout.py` and `wrench_gate.py` are unmodified. The FlashCHORD venv is the one from test C.
- **Scoring and tree:**

      python -I -B docs/research/work/wrench-gate-20261112/score_C2.py MANIFEST_C2.json OUT_DIR
      mlvenv/bin/python -I -B tools/blob_tree.py blob/features.csv labels_C2.csv results_tree_C2.json

  - The scorer used the scratch venv. The tree used `mlvenv`: scikit-learn 1.9.1, numpy 2.5.3.
  - `features.csv` md5 is e484aa85…; it was used unchanged. All 3,167 rows join, since no episode was excluded.
- **Timings** [M]:
  - ep12 alone: 222 s for 181 frames. That is grasp lock 96 s, ILC 67 s (5 replays), then the final replay.
  - The other 18 ran 3 in parallel on 4 cores shared with two other agents: 175–527 s each, 1,532 s wall.
  - Scoring: under a minute. The tree: 6 s.
- **Checks:**
  - All 19 chains exit 0, with no ILC divergence.
  - Every trace has one row per reference frame.
  - The frame-0 object offset is 0.0 mm in all 19.
  - `labels_C2.csv` holds exactly the gate's 3,167 rows.

### 11.3 Per-episode table

| ep | positives / held | gate infeasible | mean err held (cm) | rise sim / ref (cm, median) | held frames lifted ≥ half the ref rise |
|---|---|---|---|---|---|
| 0 | 48 / 48 | 0.02 | 13.0 | lid −0.9 / 1.8 | 0.38 |
| 2 | 128 / 128 | 0.20 | 14.7 | pot 3.1 / 6.2; lid 1.2 / 2.7 | 0.45; 0.41 |
| 11 | 104 / 104 | 0.46 | 16.0 | blue −3.9 / 3.7; beige −4.7 / 7.9 | 0; 0.11 |
| 12 | 87 / 88 | 0.00 | 13.4 | 2.4 / 11.8 | 0.15 |
| 13 | 120 / 120 | 0.40 | 14.9 | 0.6 / 8.9 | 0.43 |
| 18 | 236 / 236 | 0.06 | 10.3 | sweeper −4.2 / 1.2; pan 2.2 / 2.0 | 0; 0.68 |
| 21 | 194 / 194 | 0.30 | 25.2 | cup 0.0 / 6.4; pitcher −0.4 / 15.5 | 0; 0 |
| 22 | 176 / 176 | 0.30 | 13.4 | cup 1.2 / 5.3; pitcher 0.1 / 9.3 | 0.29; 0.09 |
| 23 | 240 / 240 | 0.02 | 25.5 | piece 1 0.0 / 6.6; piece 2 −0.3 / 14.9 | 0.01; 0 |
| 24 | 248 / 249 | 0.27 | 12.2 | piece 1 21.4 / 19.6; piece 2 −0.4 / 9.1 | 1.0; 0 |
| 27 | 117 / 117 | 0.13 | 30.6 | 0.1 / 24.5 | 0 |
| 31 | 213 / 213 | 0.64 | 8.3 | 0.6 / 0.9 | 0.67 |
| 39 | 213 / 213 | 0.17 | 23.8 | 0.0 / 15.0 | 0.01 |
| 40 | 157 / 159 | 0.00 | 20.2 | −0.1 / 21.6 | 0 |
| 41 | 195 / 195 | 0.01 | 11.7 | 5.4 / 14.2 | 0.20 |
| 42 | 158 / 158 | 0.01 | 23.7 | 9.2 / 4.7 | 0.88 |
| 43 | 196 / 236 | 0.05 | 4.4 | 4.7 / 9.4 | 0.78 |
| 44 | 115 / 115 | 0.17 | 29.0 | −0.1 / 18.9 | 0.01 |
| 45 | 177 / 178 | 0.05 | 20.2 | −0.3 / 20.8 | 0.01 |

- **Negatives:** the 45 negatives are in ep43 (40), ep12, ep24, ep45 (1 each) and ep40 (2). The within-episode AUROCs
  in `results_C2.json` rest on 1–40 negatives.
- **Secondary, descriptive only:** Spearman ρ between the gate's infeasible share and the mean error is −0.04 over held
  units and 0.02 over all frames.

### 11.4 Reading [M] and hypotheses [H]

- **Grasp lock changes what happens, but not the outcome.** It now lifts some objects at least half-way for most of
  their held frames: ep24 piece 1, ep42 and ep43 (pot), ep18 (dust pan), ep31 (sweeper).
- **Lifted objects still leave the reference.** For these five, median held errors are still 4–24 cm. Most objects still stay on the
  table. Only ep43 (pot, mean error 4.4 cm) gives a block of frames within 2 cm.
- **So the label is again near-constant [H].** Both open-loop replays, raw (C) and grasp-locked (C2), fail on almost
  every held frame of these Oct 20 references. Their failure is not the per-frame wrench shortfall that the gate and
  the blob features measure.
- **A physics-replay label cannot test the gate on these references** under the pre-registered share rule. Test A
  (trained-policy rollouts) is still blocked by data (section 4).
- **A test that can discriminate needs a label that varies across frames.** Trained-policy rollouts (test A) are one
  such label: they need a GPU and a new owner go-ahead.

### 11.5 Limitations

- **Same reference set as C:** the Oct 20 references with kit assets.
- **Grasp-lock options:** only the default arguments, as pre-registered. Later recipe options (`--events`,
  `--force_design`, `--sim_trace` re-planning) were not used.
- **No kit score:** `trace_score.py` was skipped. The label does not depend on it.
