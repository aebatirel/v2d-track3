# Oracle twins: pre-registration (30 Oct 2026, written before any GPU result)

Owner, 30 Oct ~09:35 UTC: "maybe we can try the public episode real refs to see if we can really copy them.
intentionally go for the hard ones. go test in 3-4 ones that are similar to the hardest eval episodes."

Question: on the public twins of the hardest eval episodes, can our current recipe make the simulated robot copy the
**true** (mocap) object motion? Comparing that with the same recipe on our **perceived** reference separates
perception/reference error from robot, physics and learner limits.

Labels: [M] measured, [E] estimate, [H] hypothesis. Nothing has been launched. No GPU result exists. No eval data was
read. No Kaggle call. Design: `DESIGN.md` (this folder). CPU checks: `cpu/`.

## 1. Twins, arms and recipes

| Twin | Eval episode (H5 10-draw mean ± sd, sim_vs_ref) | Task | Learner and recipe (= the eval episode's packed policy) |
|---|---|---|---|
| ep11 | 10 (0.450 ± 0.007) | Stack the beige cup into the blue cup | grasp-lock as gl10A2: `SF=0 REPLAN=1 EVOLVE=0`, collision pieces `meshes/carve/ev10` |
| ep13 | 14 (0.615 ± 0.199) | Left grasp, hand-over to the right, flip 180°, cup into the rack | grasp-lock as evb1420: `SF=1 REPLAN=1 EVOLVE=0` |
| ep31 | 30 (0.798 ± 0.255) | Sweeper out of the rack, scrub, put back | Option A: standard learner as std30 (250M, FDR + VOC + starts 0.25, sweep). Option B: grasp-lock `SF=1 REPLAN=1 EVOLVE=0` (**learner differs from eval 30's packed standard-learner policy**) |

Common to all grasp-lock arms: `LIB=meshes/library_v3`, `GL_ARGS="--single_hand 1 --mcp_first 1 --close 10
--palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15"`, kp-400 wrist, FDR + VOC, 70,004,736 steps,
`CURVE_REP=3`, checkpoint chosen by sim_vs_ref against the arm's own reference, `NREP=6`, seed 42.

Two arms per twin, on the same box, at the same commit and seed, with the same learner:
- **P (perceived):** the reference built as for an eval episode: perc2 (library_v3) → hands → mkref `--wrist_cost 3.0` →
  contact retargeting `--rest_settle 1` (`refs/perc2mck/ep<N>`).
- **O (oracle):** `pipeline/oracle_poses.py` v2 on P's perception (same camera trajectory, same depth). Mocap is converted
  to library_v3's mesh body frames with the scorer's own registration and aligned to the perceived table by gravity.
  P's hands are copied byte for byte. Then the same mkref and contact retargeting are run (`refs/oraclemck/ep<N>`), and
  the learner runs with every folder under `oracle` names.

Each rollout is scored three ways:
- registered ADD-AUC vs mocap with library_v3 (`score_registered.py`, as the leaderboard scores);
- the rollout's own reference vs mocap, and the static floor, from the same file;
- sim_vs_ref against the arm's own reference (`qa.py`).

## 2. What is already measured (CPU, $0) [M]

### 2.1 oracle_poses.py v2 on the local public inputs

Inputs: the 25 Oct perception poses and frame-0 depth in `refine/in`, our meshes, the kit registration. Code: WIP
commit be2b2a9, re-run at 12:20 UTC and identical to the 10:15 run. Files: `cpu/out/oracle_ep*.json`.

| Twin | Mesh-frame offset (rot / shift) | Up vs perceived table normal | Frame-0 centres vs perception | Expected mkref snap | Perception vs mocap | Oracle raw | Oracle after snap |
|---|---|---|---|---|---|---|---|
| ep11 | blue 1.86° / 0.98 cm; beige 145.3° (spin about its axis) / 0.59 cm | 0.036° | 1.30 / 0.95 cm | −0.49 / +0.78 cm | 0.898 (blue 0.862, beige 0.933) | **1.000** | **0.969** (beige 0.938) |
| ep13 | cup 1.47° / 1.04 cm; rack 1.77° / 0.54 cm | 0.022° | 0.50 / 0.58 cm | −0.30 / +0.67 cm | 0.961 (cup 0.933, rack 0.988) | **1.000** | **1.000** |
| ep31 | sweeper 3.04° / 0.43 cm; rack 1.56° / 0.67 cm | 0.006° | 0.31 / 0.34 cm | −0.38 / +0.66 cm | 0.800 (sweeper 0.912, rack 0.688) | **1.000** | **0.969** (rack 0.938) |

The support check passes on all three. The 20 Oct anchor rule (`--align anchor0`) puts ep11's beige cup 16.2 cm from
where perception has it, and ep13's rack 21.9 cm away. That is why gravity alignment is the default.

### 2.2 mkref stage (a) on the same inputs

mkref's own `fit_table` / `table_frame` and per-object snap. Stages b–f need the GPU box: hands, E2S IK, contacts,
contact retargeting. Files: `cpu/out/stage_a_*`.

| Twin | O ref vs mocap | P ref vs mocap | P snaps |
|---|---|---|---|
| ep11 | 0.969 | 0.896 (blue 0.862, beige 0.931) | −0.04 / +0.04 cm |
| ep13 | 1.000 | 0.896 (cup 0.933, rack 0.859) | 0.00 / +1.27 cm (rack) |
| ep31 | 0.969 | 0.793 (sweeper 0.912, rack 0.675) | −0.14 / +0.95 cm |

For comparison, the stored grasp-lock training references vs mocap are:
- ep11 0.884 (twin11v3x, library_v3x);
- ep31 0.823 (ev30rp).

### 2.3 Arm P's existing rollouts

From the runs' job logs. These are the numbers the new P arm is checked against; they are not part of the readings.

| Twin | Run | Recipe difference vs this test | Rollout AUC vs mocap (n 5, mean ± pop. sd, min) | sim_vs_ref | Its reference vs mocap |
|---|---|---|---|---|---|
| ep11 | 20261025-twin11v3x-0e8aebb | library_v3x, `SF=1 REPLAN=0 EVOLVE=1`, onset anchor, no ev10 pieces | 0.570 ± 0.001 (0.567); static floor 0.595 | 0.480 | 0.884 |
| ep13 | none | – | – | – | – |
| ep31 | 20261024-ev30rp-07eef1a | grasp-lock `SF=1 REPLAN=0 EVOLVE=1`, older GL_ARGS | 0.695 ± 0.122 (0.453) | 0.717 | 0.823 |
| ep12 (reference point, not in this test) | 20261029-rcA-34bf6ae | grasp-lock control | 0.912 ± 0.033 (0.867) | 0.926 | 0.935 |

The new P arm is a fresh measurement at the current code with the eval twin's recipe. Only it is compared with O.

### 2.4 Machinery

- **CPU mock of the whole job:** `cpu/mock/`. It uses stub perception, IK, trainer and evaluator, and the real
  `oracle_poses.py`, `ref_vs_mocap.py` and `score_registered.py`. Results are in §9.
- **Leak guard:** `tools/no_oracle.py`. It refused:
  - an `-orc` run id;
  - an `oracle` path;
  - a renamed checkpoint whose stored training config names `refs/oracle_glockt`.

  It passed all 20 pack-7 checkpoints.

## 3. Gate G0 (on the box, per twin, before any training)

**G0 passes when all three hold:**
- O's finished reference (after mkref and contact retargeting) scores ≥ **0.95** vs mocap (`tools/ref_vs_mocap.py`);
- mkref's support check passed without the fallback lift;
- the frame-0 centres are within 3 cm of perception.

Expected: 0.97–1.00 (§2.2). If G0 fails for a twin, O is not trained for it, the failure is logged and pushed, and P
still trains. P's reference vs mocap is recorded beside it. Expected [E]: ep11 ≈ 0.90, ep13 ≈ 0.90, ep31 ≈ 0.79–0.82.

Also recorded, but not part of the gate: the reference each arm was finally trained on, after support fill, grasp
lock, ILC and re-plan. It is scored vs mocap as `trained_ref_vs_mocap` in `summary.json` and as `ref_auc` per rollout.

## 4. Primary metric and readings (fixed now)

**Primary metric** per arm: the mean registered ADD-AUC vs mocap over the 6 official evaluations of the arm's chosen
checkpoint. Also reported: sd (ddof 1), min, and the number of rollouts below 0.70 (evals 14 and 30 are bimodal).

Notation: O and P are those means; Δ = O − P.

**R1. Can the recipe copy this task's true motion?**
- O ≥ 0.90: **yes**.
- O ≤ 0.75: **no**. The limit is robot, physics, mesh or learner, not perception.
- Otherwise: **partial**.

**R2. Perception's share.**
- Δ ≥ +0.12: our reference is **the main loss** on this twin.
- |Δ| ≤ 0.05: **not the reference**.
- 0.05 < Δ < 0.12: **inconclusive** at one seed.
- Δ ≤ −0.05: **oracle worse than perception.** This is read as a construction or selection problem: check
  `trained_ref_vs_mocap`, the re-plan log and the curve. It says nothing about perception.

The bands are not "Δ ≥ +0.05 means perception-limited" because measured one-seed spreads of these recipes exceed 0.05:
- grasp-lock on ep12 ranged 0.854–0.912 over 7 runs and variants;
- the standard learner on ep18 gave 0.776 and 0.889 on two seeds.

**Combined class per twin.** The first matching row wins:

| Class | Condition | Meaning |
|---|---|---|
| **C1 physics/learner-limited** | O ≤ 0.75 | Even the true motion is not copied: the robot cannot copy the task. |
| **C2 perception-limited** | Δ ≥ +0.12 and O ≥ 0.90 | The recipe copies the truth and loses mainly through our reference. |
| **C3 both** | Δ ≥ +0.12 and 0.75 < O < 0.90 | The reference is the main loss, and the copy also caps. |
| **C4 not the reference** | \|Δ\| ≤ 0.05 and O > 0.75 | Reference work does not pay at this recipe. P sits near the copy ceiling. |
| **C5 inconclusive** | anything else | No decision at one seed. |

**Secondary readings.** These are reported, but no decision rests on them alone:
- **R3, how copyable each reference is:** sim_vs_ref(O) − sim_vs_ref(P), each against its own reference.
  - ≥ +0.15: our perceived reference is physically harder to track, for example because of inconsistent contacts or
    interpenetration.
  - |·| ≤ 0.05: both are equally trackable.
- **Copy gap per arm:** trained reference vs mocap minus rollout AUC.
- **Checkpoint asymmetry (CPU after the box, $0):** the registered AUC of every curve checkpoint in both arms. This
  removes the advantage O has from being selected against a reference that is ≈ mocap.
- **Failure phase:** `score_registered.py --per_frame` on the best and worst rollouts per arm (start, grasp,
  transport, placement or nest).

Priors [H], which do not change the readings:
- ep11 is C1 (the nest is a mesh/physics limit: the carve shrank the beige cup 8 mm to fit eval 10's perceived nest).
- ep13 is C3 (rack placement after the flip).
- ep31 is C2 or C4 (the rack is the main perception loss: 0.675–0.735 per object, while the sweeper is at 0.912).

Each prior is falsified by its twin's class.

## 5. How each reading maps to eval spend (direction only)

The leaderboard AUC is the mean over the 20 submitted eval episodes. So raising one eval episode by x moves the board by
x / 20 [E, assuming the twin's gap transfers to its eval episode; that transfer is itself a hypothesis]. For scale:
- eval 10 at 0.45 → 0.90 would add +0.0225;
- 5th place needs about +0.046.

| Twin → eval | C2 / C3 (reference is the main loss) | C1 (cannot copy the truth) | C4 (not the reference) | C5 |
|---|---|---|---|---|
| ep11 → **eval 10** | Spend on eval 10's reference: nest heights and the beige cup track (perception repair, nest-aware placement). Expected gain ≤ Δ/20. | No reference spend on eval 10. Levers: the cup collision copy (carve / pieces at the true nest depth), grasp and learner, tested first on ep11's O arm (it isolates the robot side). | Same as C1. P shows how far eval 10's policy is from its copy ceiling. | None. A second seed needs a go-ahead (≈ $1.5–2). |
| ep13 → **eval 14** | Spend on eval 14's reference: cup pose after the flip, rack placement. | Hand-over and flip are a robot limit. Levers: learner (hand-over), embodiment, rack collision copy; no eval-14 reference spend. | As C1. | None. |
| ep31 → **eval 30** | Spend on eval 30's reference: rack pose (the per-object AUC shows the rack, not the sweeper, is off). | Scrubbing in the rack is a robot limit. Levers: learner and collision. | As C1. | None. |

Rules for using the result:
- It only directs the next effort for these eval task types.
- No eval policy, pack or checkpoint is chosen or tuned from it.
- No eval result feeds back into it.
- Option B's ep31 readings are for the task type under the grasp-lock learner. Because eval 30's packed policy is the
  standard learner, they say nothing direct about that policy.

## 6. Integrity

- **Who reads mocap:**
  - `oracle_poses.py` (arm O, public eps 11 / 13 / 31 only; it refuses eval ids and `SPLIT=eval`);
  - `tools/ref_vs_mocap.py` (G0, summary);
  - `score_registered.py` (scoring);
  - the CPU checks in `cpu/`.

  Arm P reads no mocap.
- **Where O's files live:** only under oracle names (`/content/oracle`, `refs/oraclemck`, `refs/oracle_*`,
  `runs/oracle_glock`, `refs/oraclemcks`, `runs/oraclemcks`, `results/oracle*`, `results/hard_ab/ep31/oracle_*`), in runs
  named `<date>-orc<X>-<sha>`. The job refuses a run id without `-orc`.
- **Packs refuse them:**
  - `pack_eval.sh`, `h5_reeval.sh` and `submit_pack.sh` call `tools/no_oracle.py` on their inputs;
  - it also reads each submitted checkpoint's stored training config.
- **Eval data and Kaggle:** no eval data and no Kaggle. Public development and eval inference stay separate.

## 7. Launch options and cost [E]

Basis [M], from the runs' job logs:
- **One grasp-lock wave of 2 concurrent trainings** (reference stages, training, curve, 5 evaluations):
  - 66 min (evb1420);
  - 80 min (fr1420);
  - 82 min (ev30rp).
- **One grasp-lock training alone:** 60 min (twin21arc); 72 min (gl10A2, with the eval-10 carve pieces).
- **References from raw:** 7–12 min for two episodes at once; 24 min for one public episode when the depth is computed
  on the box.
- **One standard-learner training + sweep + 5 evaluations:** 1.4–1.5 h.
- **Setup:** 2–8 min plus boot on a normal day; 43 min today under HF 429.

The price is RTX PRO 6000 on demand at $1.30–1.45/h. The job strings are in `JOBS.txt` (this folder; the same file is
in the scratchpad `oracle/JOBS.txt`).

| Option | Boxes | Trainings | Wall time | Cost |
|---|---|---|---|---|
| **A (full design)** | G: grasp-lock eps 11 + 13, P + O; S: standard learner ep31, P then O | 4 + 2 | G 2.8–4.1 h; S 3.3–4.2 h (in parallel) | **≈ $7.9–12.0** (central ≈ $9.8) |
| **B (single box)** | one: grasp-lock eps 11 + 13 + 31, P + O (ep31 labelled "learner differs from eval 30's packed standard learner") | 6 (3 waves of 2) | 4.0–5.5 h | **≈ $5.2–8.0** (central ≈ $6.3) |
| (A's box G alone, if ep31 is dropped) | grasp-lock eps 11 + 13, P + O | 4 | 2.8–4.1 h | ≈ $3.6–5.9 (central ≈ $4.6) |

This session has about $9 left of its cap:
- option A likely exceeds it;
- option B fits.

The owner chooses. There is no second seed and no ep24 extension without a new go-ahead.

## 8. Build notes: differences from DESIGN.md §4.1 (mechanics only, same arms)

- **One learner invocation per box.** Both arms are entries of the same `PAIRS` with a 4th field `EP:RUN:BASE:PERC`
  (`11:local:mck` and `11:local:mck:oracle`). There are no concurrent `glock_public.sh` runs, so there are no slot
  cleanup or `make_assets` races, and `SLOT_CLEAN` is not needed.
  - **glock_public.sh:** PERC ≠ perc2 prefixes every folder with `<PERC>_` (`refs/oracle_glock`, `refs/oracle_glockt`,
    `refs/oracle_sf`, `runs/oracle_glock`, `results/oracle_glock_public`).
  - **hard_ab.sh:** PERC ≠ perc2 uses `/content/oracle`, `refs/oraclemcks`, `runs/oraclemcks`, `results/oraclemcks`,
    and `results/hard_ab/ep<N>/oracle_mcks-s42`.
  - Both refuse PERC ≠ perc2 unless `SPLIT=public` and `RUN=local`. Entries without the 4th field behave exactly as
    before.
- **`RUN=local`** in `glock_public.sh`: a reference built on this box, nothing pulled.
- **`ENV_EP<N>`** in `glock_public.sh`: per-episode settings, as in `hard_ab.sh`.
- **Per-episode collision pieces.** `oracle_twins.sh` builds both of ep11's references against
  `/content/assets_ev10` (`ENV_EP11 PIECES=meshes/carve/ev10`). The references name those assets, so ep13's blue cup
  never sees the eval-10 carve. This replaces the design's `ASSETS` override.
- **Summaries.** `ref_auc` and `floor_auc` are added to each rollout row and to the aggregates of the
  `glock_public.sh` and `hard_ab.sh` summaries. These are additive keys only.
- **Leak guard.** `tools/no_oracle.py` replaces per-script pattern checks, and also checks checkpoint configs.
- **Run ids.** `<date>-orcG-<sha>` and `<date>-orcS-<sha>` (option A), `<date>-orcB-<sha>` (option B).

## 9. CPU mock results (before launch) [M for the mechanics; the policy numbers are stubs]

`cpu/mock/` reruns the exact job strings of `JOBS.txt`, with `/content` mapped to a mock root.
- **Stubbed** (GPU or IK): perception (it serves the 25 Oct perception of the refine inputs), hands, mkref (stage (a)
  with mkref's own functions), contact retargeting, support fill, grasp lock, ILC, training, evaluation, qa, and
  rollout scoring.
- **Real:** `oracle_poses.py`, `ref_vs_mocap.py` and `score_registered.py`.

All three mocks finished with rc 0.
- **Option B** (glock, eps 11 / 13 / 31) and **box G** (eps 11 / 13): G0 passed with
  - O 0.969 / 1.000 / 0.969;
  - P 0.896 / 0.896 / 0.793 (as in §2.2).

  Six (four for box G) learner entries ran. Checks:
  - P trained on `refs/glockt` and O on `refs/oracle_glockt`, with identical training arguments, seed and embodiment
    within each episode.
  - ep11's references (both arms) name `/content/assets_ev10`; ep13 and ep31's name `/content/assets`.
  - The hands are md5-identical between the arms.
  - The O arm's mkref read `/content/oracle/ep<N>/poses.npz`, P's read `/content/perc2/ep<N>/poses.npz`.
  - No file under `perc2mck`, `glockt`, `glock`, `sf`, `glock_public` or `runs/glock` mentions an oracle folder.
  - The summary and the RESULT lines carry R1, R2, the class and R3.
- **Box S** (std, ep31): G0 passed with O 0.969 and P 0.793.
  - P trained on `refs/perc2mcks`, then O on `refs/oraclemcks`, after the lock was released, with identical arguments.
  - There were 10 evaluations per arm: final, sweep and NREP 6.
  - Results are in `results/hard_ab/ep31/{mcks-s42,oracle_mcks-s42}`.
  - The first std mock run caught a bug, fixed before this record: `PAIRS` was not passed to `hard_ab.sh`, which would
    have trained its default ep24 / ep18 pairs.
- **Existing callers** (3-field PAIRS, no PERC field): `cpu/mock/equiv.sh` ran `glock_public.sh` and `hard_ab.sh`
  from be2b2a9 (before these hooks) and from the working tree, in the same mock (grasp-lock eps 11 + 13; standard
  learner ep11).
  - Identical: every reference-stage, training and evaluation call (arguments and paths), every file written, and
    every job-log line.
  - The one exception: the final summary line, which gains the additive `ref_auc` / `floor_auc` keys.
