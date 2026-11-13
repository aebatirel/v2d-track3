# Oracle twins: can the robot copy the TRUE object motion of the hard public twins? (design, 30 Oct 2026)

Owner, 30 Oct ~09:35 UTC: "maybe we can try the public episode real refs to see if we can really copy them.
intentionally go for the hard ones. go test in 3-4 ones that are similar to the hardest eval episodes."

Diagnostic on PUBLIC episodes only. Two arms per twin, same box, same commit, same seed, same learner:
- **P (perceived):** the current recipe on our perceived reference.
- **O (oracle):** the identical recipe on a reference whose object motion is mocap.

Both arms are scored the way the leaderboard scores: registered ADD-AUC of the official rollout vs mocap, with our
meshes. O − P separates perception/reference error from policy/physics limits on the task types of the hardest eval
episodes.

Labels: [M] measured (this design or the cited run), [E] estimate, [H] hypothesis. Nothing has been launched. No
Kaggle call. No eval data was read.

Design work dir (scratchpad, 30 Oct): `/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/oracle/`.
Copied into the repo 30 Oct ~12:30 UTC with the CPU-check scripts and outputs (`cpu/scripts`, `cpu/out`) and the
CPU mock (`cpu/mock`). The build differs from §4.1 in a few mechanics (one learner invocation per box, a 4th PAIRS
field instead of REFP/GLP/NS, `tools/no_oracle.py` as the leak guard): see PREREG.md §8. The readings are in PREREG.md.
- `scripts/g_check.py`: oracle alignment check.
- `scripts/twin_stats.py`: task shape from mocap.
- `scripts/frames_check.py`, `scripts/cup_axis.py`: mesh-frame offsets.
- `gcheck/ep*.out`, `g_check_summary.json`, `twin_stats.txt`, `frames_check_v3.txt`: outputs.

All four scripts ran on CPU with the scoring venv, `python -I`, at repo HEAD c608acb.

---------------------------------------------------------------------------------------------------------------------

## 1. Hardest eval episodes, their public twins, and the choice

Eval scores are sim_vs_ref (vs OUR reference): 10-draw H5 means of the packed policies
(`docs/analysis/h5-20261029/h5_summary.json`), plus the 30 Oct replacements in the work log. Object names and tasks
come from the public `meta/episodes_metadata.jsonl` and the parquet slot names (checked [M]) and from
`docs/research/notes/15-eval-video-survey.md`.

| Eval (H5 mean ± sd) | Objects, task | Packed policy (learner) | Public twin(s) | Twin task check [M] |
|---|---|---|---|---|
| **10** (0.450 ± 0.007) | blue + beige cup, stack beige into blue | gl10A2 (grasp-lock, `SF=0 REPLAN=1 EVOLVE=0`, carve pieces `meshes/carve/ev10`) | **ep11** Cup_Stack (137 f) | Beige travels 25 cm and ends +2.9 cm higher (nested [E]). Blue cup static (0.5 cm), held by the left hand. |
| **14** (0.615 ± 0.199) | blue cup + rack: left grasp, hand-over to right, flipped 180°, placed inverted in the rack | evb1420 (grasp-lock, `SF=1 REPLAN=1 EVOLVE=0`; no carve: the ev14 carve failed its rule) | ep12, **ep13** Cup_In_Dish_Rack | Both flip the cup (tilt 177° / 162°). **ep13:** left fingertips 3–7 cm from the cup f20–60, then right 8–12 cm from f70 = the eval-14 left→right hand-over. **ep12:** right hand only. |
| **30** (0.798 ± 0.255, bimodal) | sweeper + rack: sweeper taken from between the dividers, scrubs, put back | std30 (standard learner, 250M, `refs/perc2mcks`, no carve: the ev30 carve was dropped) | **ep31** Brush_Dishrack | Note 15: "nearly the same clip". Sweeper travels 15.6 cm, tilt up to 33°, right hand f22–266. Rack static. |
| 16 (0.813 ± 0.077) | rack + **spoon** into rack tower | seed43 (grasp-lock) | **none** | No public episode has a spoon (work log 21 Oct). |
| 32 (0.838 ± 0.068) | blue cup + **spoon**, stir | fr32s46b (grasp-lock) | **none** | Same. |
| **25** (0.850 ± 0.099) | two boards: slide, stand, slot together | c25s42 (standard learner + carve `ev25` + identity fix) | ep23, **ep24** Planter_Stand | ep24: both boards rotate ~100° and end +6.5 cm (assembled). ep23 has a frame-0 identity swap in perception (AUC 0.041), so ep24. |
| 20 (0.888 ± 0.043) | blue cup + pitcher, pour | evb1420 (grasp-lock, arc foot) | ep21, ep22 Water_Can_Blue_Cup | Pitcher tilts 91° (pour). Cup held by the left hand. |
| (1: 0.822 → 0.924 after the carve; 28: 0.931) | pot + lid; pot into rack | std | ep0/ep2; ep26/ep27 | No longer among the hardest. |

**Choice: 3 twins in this batch, 1 as an optional extension.**
1. **ep11** (eval 10, the hardest).
2. **ep13** (eval 14). ep13 is chosen over ep12 because it has eval 14's hand-over and flip [M]. ep12's arm P is
   already at its perception ceiling (§2), so ep12 has little to learn.
3. **ep31** (eval 30).
4. Optional, needs its own go-ahead: **ep24** (eval 25). It needs two more standard-learner trainings (§4.5).

Eval 20's twin is not needed: its arm P already answers the question [M]. ep21's policy copies our reference almost
perfectly (sim_vs_ref 0.983), and its AUC (0.772) equals our reference's own AUC vs mocap (0.778). So ep21 is
perception-limited (the pitcher, 0.575).

The chosen twins are the ones where the policy cannot even copy our perceived reference: sim_vs_ref 0.48 (ep11),
0.72 (ep31) and 0.27 (ep24). ep13 is untested, and its eval twin 14 reaches only 0.62–0.66. There, perception error
and robot limits are confounded, and the oracle separates them.

## 2. Arm P: best existing results of current recipes on our perceived reference

Columns: rollout AUC = registered ADD-AUC vs mocap with our meshes, over the official evaluations of the checkpoint
chosen by sim_vs_ref. ref-vs-mocap = the `reference` entry of `score_registered_ep<N>.json` (the reference that was
trained on).

Sources: local copies of each run's job.log, and three score files fetched from the store today (one call each). The
ep12 score files are local.

| Twin | Best existing P | Rollout AUC vs mocap | sim_vs_ref | ref-vs-mocap | Run (code) | Matches the eval twin's packed recipe? |
|---|---|---|---|---|---|---|
| ep11 | grasp-lock frozen recipe, library_v3x | **0.570 ± 0.001** (n 5), below the static floor 0.595 | 0.480 ± 0.004 | **0.884** (blue 0.864, beige 0.905) | `20261025-twin11v3x-0e8aebb` | **No.** It used `SF=1 REPLAN=0 EVOLVE=1`, onset anchor, v3x, and no ev10 pieces. The beige cup falls at the start (50 mm / 29°). Base v3: 0.525 (`-twin11v3-`). The eval-10 recipe (ev10 pieces, `SF=0 REPLAN=1`) was never run on ep11. |
| ep13 | **none.** Never trained. | – | – | perception 0.961 (cup 0.933, rack 0.988; refine baseline) | – | **Missing:** P must run. |
| ep12 (reference point only) | grasp-lock, recipe-arm control A | **0.912 ± 0.033** (n 5) | 0.926 ± 0.036 | **0.935** (cup 0.933, rack 0.938) | `20261029-rcA-34bf6ae`, policy_50003968, on the stored 24 Oct `mc` reference (`20261024-ev2-2c1e4dd`) | Partly. It used `REPLAN=0 EVOLVE=1`, eval 14 used `REPLAN=1 EVOLVE=0`. The rollouts sit at the reference ceiling. |
| ep31 | grasp-lock frozen recipe, gated re-proposal (the eval-30 box's twin slot) | **0.695 ± 0.122** (n 5; older grasp-lock E2 0.767 ± 0.016, `20261024-e2-e49e83d`) | 0.717 ± 0.078 | **0.823** (sweeper 0.912, rack 0.735) | `20261024-ev30rp-07eef1a` | **No.** Eval 30's packed policy is the standard learner. No standard-learner run on ep31 exists, so P must run. |
| ep24 (optional) | standard learner `mcs` (21 Oct recipe, before FDR/VOC); grasp-lock | 0.307 (std, `20261021-auto24-966eb96`); 0.241 ± 0.125 (grasp-lock, `20261024-ev3-2c1e4dd`) | 0.267 (grasp-lock) | perception 0.812 | as listed | **No.** No current standard-learner run, no ev25 pieces. |
| ep21 (not needed) | grasp-lock + arc foot = eval 20's recipe | 0.772 ± 0.009 | 0.983 ± 0.007 | 0.778 (pitcher 0.575, cup 0.980) | `20261025-twin21arc-ee7ba8e` | Yes. Already shows "perception-limited". |

So no twin in the chosen set has a current-recipe arm P at the current code. P is trained fresh beside O, on the same
box and commit, with the eval twin's packed recipe.

## 3. Oracle machinery: what exists, what is wrong with it, and the clean construction

### 3.1 What exists
- `pipeline/oracle_poses.py` (written 20 Oct, used once, on ep12 day 1):
  - takes perc2's `poses.npz` and keeps `world_T_cam`;
  - replaces every `cam_T_<obj>` with the mocap pose mapped by `G = W_C[0] · cam_T_slot0[0] · inv(mocap_slot0[0])`
    (anchor slot 0 at frame 0);
  - symlinks the depth;
  - refuses eval ids.
- `pipeline_ep.sh PERC=oracle` runs it when `/content/oracle/ep<N>/poses.npz` is missing. The pipeline then runs as
  usual, with refs at `/content/refs/oracle<VARIANT>/ep<N>`, runs at `runs/oracle<V>`, results at `results/oracle<V>`.
  The script refuses `PERC=oracle` with `SPLIT=eval`. `store.sh` push-run and pull-run already carry `/content/oracle`.
- The day-1 result: ep12 oracle 0.858 (registered 0.857) vs perc2 0.890. It used the old recipe, scan meshes and a
  slot-0 (cup) anchor. Given §3.2(b) it is not comparable; not used.

### 3.2 Three measured defects of `oracle_poses.py` as written (CPU check `g_check.py`, 6 public twins)

**(a) Mocap is in the SCAN body frame, the simulator uses OUR meshes.** The kit registration (the one
`score_registered.py --meshes` applies) puts library_v3 within 0.15–3.1° and 0.2–1.05 cm of the scans [M]. The beige
cup's 133° is a spin about its symmetry axis; only 3.7° of it is tilt [M].

Using scan-frame poses for our meshes therefore costs reference-vs-mocap before any other step:
- ep13 0.903, ep12 0.913, ep21 0.924;
- ep11 0.969, ep31 0.969;
- ep24 1.000.

**Fix:** our-mesh pose = mocap pose ∘ X, with X = [R, c − R·ca]. (R, ca) come from `T3._register_object_body`, with
score_registered's candidate (`budget_mesh` 4096) and seed `1_000_003·ep + 101·slot`. Converted, the raw oracle
track scores exactly 1.000 on all 6 twins [M].

**(b) Anchoring G on slot 0 at frame 0 is wrong when slot 0 is a cup.** Its spin about the axis is arbitrary in
perception, and G inherits that spin. The other object lands far from where the perceived hands and depth put it at
frame 0 [M]:
- ep13 rack 21.9 cm off;
- ep11 beige cup 16.2 cm off.

Even with the conversion, a slot-0 anchor on ep31 (sweeper) moved the ring so that mkref's table fit failed its
support check (bottoms +58–61 cm) [M]. A Kabsch fit over all objects' surface points instead tilts the scene 16.6° on
ep11 (two cylinders: ill-conditioned) [M].

**(c) Gravity.** Mocap z is gravity: frame-0 bottoms of the objects agree within 0.1–0.7 cm on all 6 twins, for
example ep12 cup 60.09 / rack 59.85 cm [M]. Any G taken from perceived object poses tilts mocap "up" 0.5–4.2°
(16.6° for the Kabsch fit on ep11) against mkref's depth-fitted table normal, which is the simulator's gravity [M].

**Construction to use: `convG`.**
1. Convert mocap to our-mesh frames, as in (a).
2. Rotation: map mocap +z onto the table normal that mkref's own `fit_table` finds (frame-0 depth, ring around
   perc2's frame-0 objects).
3. Yaw about that normal and translation: least squares on all objects' surface points at frame 0 (perc2 vs oracle).

Measured on the 6 twins, convG gives:
- up vs table normal 0.00–0.04°;
- frame-0 centres 0.3–1.3 cm from perception, i.e. where the perceived hands expect them;
- support check passes everywhere.

### 3.3 What mkref and the later steps change in the oracle reference (it should stay ≈ 0.97–1.0 vs mocap)

| Step | Effect on the object motion | Measured / where recorded |
|---|---|---|
| mkref table frame | Rigid; no change in registered AUC. | [M] |
| mkref `--snap per_object` (whole trajectory, \|h\| ≤ 2 cm) | With convG the snaps are small. Relative shifts between objects score 1:1 (AUC steps of 1/32 per object here). | Snaps −0.5…+1.5 cm. ref-vs-mocap after the snap: ep13 1.000, ep24 1.000, ep11 / ep12 / ep21 / ep31 0.969 [M]. The snaps come from our mesh bottoms vs the scans (mesh shape, not motion). Logged in `ref_summary.json` → table.shifts_cm. |
| mkref support fallback lift, `--start_overlap` | Fallback only if the support check fails (never with convG [M]). `start_overlap` is off by default. | `ref_summary.json` |
| contact_retarget `--rest_settle 1` (variant mck) | Per frame: a vertical shift, and a tilt of ≤ 15° onto a stable rest, for free resting objects. | Not measurable on CPU here (needs hands + SDFs). `contact_retarget.json` → rest_settle (max_shift_cm, max_turn_deg). |
| support_fill (SF=1, ep13) | Meshes only (underside fill); the fill can differ between arms. | `support_fill.json` per arm |
| grasp_lock / ILC / EVOLVE | Hands only. Without re-plan the object path is unchanged (0.0 m, 24 Oct [M]). | – |
| `REPLAN=1` (eval-10 / eval-14 recipes) | Can re-route an object that is off its reference before its grasp. Kept only if the zero-action replay improves. | glock log, `zero_score_r*.txt` |
| Final reference as trained | All of the above. | The `reference` AUC in every rollout's `score_registered_ep<N>.json`, for both arms, at no extra cost. Gate G0 (§4.3) checks it before training. |

Two residuals remain by construction [M]:
- **VO drift between perceived hands and true-world objects:** ≤ 0.5–1.2 cm p95. Static racks in the perceived world
  move 0.5 cm (ep12, ep13) and 1.0 cm (ep31) p95. Camera translation ≤ 2–9 cm. This is below contact_retarget's
  2.5 cm snap radius.
- **Hands are identical input, but the robot hand reference is not:** mkref's gap-fill ("attach"), depenetration,
  contacts and contact retargeting are conditioned on the object poses.

### 3.4 How the current recipes take a base reference, and the clean way to give them an oracle one

**grasp-lock, `ops/jobs/glock_public.sh`**
- `PAIRS="EP:RUN:BASE"`:
  - `RUN=new` builds the reference end to end: perc2 → hands → mkref `--wrist_cost 3.0` → contact_retarget
    `--rest_settle 1` → `refs/perc2mck`.
  - Otherwise the job pulls `runs/RUN` from the store.
- `R0=/content/refs/perc2$BASE/ep$EP`, with the prefix hard-coded. Then:
  1. SF → `refs/sf`, SETTLE;
  2. grasp_lock (GL_ARGS, `GL_WRIST_KP=400`) → `refs/glock`;
  3. wrist_ilc → `ref_gl_ilc`;
  4. EVOLVE;
  5. zero-action replay + rest check, REPLAN → `refs/glockt/ep/…/ref_gl_ilc.parquet`;
  6. 70M kp-400 FDR+VOC training → `runs/glock`;
  7. curve (CURVE_REP evaluations per checkpoint), choice by sim_vs_ref;
  8. NREP evaluations → `results/glock_public/ep/best`, each scored by qa.py and `score_registered.py --meshes LIB`.
- `REUSE_REF=1` skips the reference stages when `refs/glockt` and `rest_check.json` exist.
- All directory names and `/content/assets` are fixed, and `run=local` is not supported (it would try to pull "local").

**standard learner, `ops/jobs/hard_ab.sh`** (as wrapped by `std_learner.sh` / `eval_both.sh`)
- Settings: `FC_FDR_OBJ=1 FC_FDR_TIPS=1 FC_VOC_INERTIA=1 FC_IMMEDIATE_FIRST_FRAME=0.25 TRAIN_ARGS=$FDR_TRAIN_ARGS SUF=s CR=0 BASE_EVAL=0`.
- `R0=refs/perc2$BASE` is copied to `refs/perc2$BASE$SUF`. Then `pipeline_ep.sh VARIANT=$BASE$SUF PDIR=$PDIR_ROOT/ep`
  runs; stages are skipped. Training is 250M under the shared `TRAIN_LOCK`, with checkpoint sweep 0.4/0.6/0.8 and the
  floor guard.
- NREP evaluations go to `results/hard_ab/ep/$k-s$SEED`. `PERC=perc2` is exported and hard-coded.

**Cleanest oracle base, everything else identical to arm P.** Per twin, on the same box:
1. P reference, as for an eval episode:
   `PERC=perc2 VARIANT=mck MKREF_ARGS="--wrist_cost 3.0" CONTACT_RETARGET=1 CR_ARGS="--rest_settle 1" STOP_AFTER=reference SPLIT=public pipeline_ep.sh EP`
   This gives `/content/perc2/ep<N>` and `refs/perc2mck/ep<N>`.
2. O perception: `oracle_poses.py` v2 (`--meshes $LIB --align gravity`) on that same `/content/perc2/ep<N>`, giving
   `/content/oracle/ep<N>/poses.npz`. Same `world_T_cam`, same depth link.
3. Copy P's `hands.npz` and `hands_refined.npz` into `refs/oraclemck/ep<N>/`, so the hands stage is skipped and the
   hands are byte-identical.
4. `PERC=oracle` + the same VARIANT, MKREF_ARGS and CR args → `refs/oraclemck/ep<N>`.
5. The same learner, with the base prefix `oracle` and oracle-prefixed working directories:
   - grasp-lock: `refs/oracle_glock`, `refs/oracle_glockt`, `refs/oracle_sf`, `runs/oracle_glock`,
     `results/oracle_glock_public`;
   - standard learner: `refs/oraclemcks`, `runs/oraclemcks`, `results/oraclemcks`, `results/hard_ab_oracle`.

No oracle file ever lives under the names that eval packs pull (`perc2mck`, `perc2mcks`, `glockt`, `sf`). P keeps the
normal names, which is harmless: public episode numbers never collide with eval numbers, and packs pull by run id.

Identical in both arms:
- hands;
- mkref and contact-retargeting settings;
- meshes `library_v3`;
- carve pieces where the eval twin's policy used them (ev10 for ep11 only);
- SF setting, GL_ARGS, REPLAN, EVOLVE, CURVE_REP, NREP;
- seed, steps, embodiment, curriculum;
- checkpoint choice rule (sim_vs_ref against the arm's own reference).

Different by construction: the object motion, and everything conditioned on it (robot hand retarget and contacts, SF
fills, re-plans). O's checkpoint is chosen by sim_vs_ref against a reference that is ≈ mocap, a mild selection
advantage. §4.4 removes it in a secondary reading.

## 4. Job design

### 4.1 Code to build and check on CPU before any spend (next workflow step)

1. **`pipeline/oracle_poses.py` v2:**
   - `--meshes DIR` (mesh-frame conversion as in 3.2a);
   - `--align gravity` (default) and `--align anchor0` (old behaviour, only for reproducing 20 Oct);
   - needs `/content/kit/v2d_submission_kit`, `/content/t3/mesh`, `/content/t3/calib.json` and `mkref.fit_table`;
   - writes `oracle.json`: mesh offsets, G, up-vs-normal, frame-0 bottoms and expected snaps, frame-0 distance to
     perception, raw ref-vs-mocap;
   - keeps the eval-id refusal.
   - **Acceptance:** reproduces `g_check_summary.json` convG on the local inputs for eps 11, 13 and 31: raw 1.000;
     after the snap 0.969 / 1.000 / 0.969; up ≤ 0.1°; support OK.
2. **`pipeline_ep.sh`:** pass `ORACLE_ARGS` and `MESH_DIR` to oracle_poses.py.
3. **`glock_public.sh`**, with defaults that leave existing jobs byte-identical in behaviour:
   - `REFP` (default perc2) for R0;
   - `GLP` directory prefix (default empty);
   - `run=local` (no pull);
   - `ASSETS` override (default `/content/assets`; fix_assets links to `$ASSETS`);
   - `ENV_EP<N>` per-episode settings, as in hard_ab;
   - `SLOT_CLEAN=0` for a second concurrent invocation (otherwise its `rmdir /content/train_slot_*` frees slots held
     by the first);
   - `ref_auc` and `floor_auc` added to summary.json;
   - guard: `REFP` ≠ perc2 requires `SPLIT=public` and a non-empty GLP.
4. **`hard_ab.sh`:**
   - `REFP` for R0 / R1 / F / `chosen()` and the exported PERC;
   - `NS` suffix for `results/hard_ab$NS` and the logs;
   - skip `rm -f $TRAIN_LOCK.ep*` when NS is set;
   - same guard;
   - `ref_auc` in summary.json.
5. **`tools/ref_vs_mocap.py`:** registered AUC vs mocap of a reference parquet's object track (`object_body_position`
   / `object_body_wxyz`), with `score_registered.py`'s machinery. This is gate G0.
6. **`ops/jobs/oracle_twins.sh`:**
   - inputs: `LEARNER=glock|std`, `EPS`, `ENV_EP<N>`;
   - steps:
     1. `ensure_gdino`, pull-depth per episode, make_assets;
     2. P references, then O references (§3.4);
     3. G0;
     4. learners (P and O concurrently for grasp-lock under `TRAIN_SLOTS=2`; P then O for the standard learner,
        which shares the training lock);
     5. `results/oracle_twins/summary.json` and `RESULT` lines;
     6. push-run.
7. **Leak guards:**
   - `pack_eval.sh`, `h5_reeval.sh` and `submit_pack.sh` refuse any RUNS / PICK / KEEP_RESULTS / ASSET path that
     contains `oracle`, or a run id that contains `-orc`;
   - run ids `<date>-orcG-<sha>` and `<date>-orcS-<sha>`.
8. **Checks:**
   - `bash -n`;
   - a CPU mock of `oracle_twins.sh` with stub trainer and evaluator (as the e1v mock);
   - a diff showing unchanged commands for existing callers with REFP / GLP / NS unset.

### 4.2 Boxes (RTX PRO 6000, 96 GB, on demand ≤ $1.45/h, snapshot `pt2.11-cu130-py313-20261020`, self-destroy + stall watchdog)

**Box G, grasp-lock, run `…-orcG-<sha>`: eps 11 and 13, arms P and O = 4 trainings.**
- Common to all four: `TRAIN_SLOTS=2` (2 concurrent, 2 waves), `LIB=meshes/library_v3`, `REPLAN=1 EVOLVE=0 CURVE_REP=3 NREP=6 SEED=42 STEPS=70004736`.
- `GL_ARGS="--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15"`, as gl10A2 and evb1420 (copied from their job.log [M]).
- FDR + VOC via fc_patches; ILC_HOLD and CURR_SCALE unset.
- `ENV_EP11="SF=0 PIECES=meshes/carve/ev10 ASSETS=/content/assets_ev10"` (= gl10A2).
- `ENV_EP13="SF=1"` (= evb1420; SF_ARC default).
- Separate asset roots because ev10 replaces `blue_cup`, which ep13 also has.
- Fallback if per-episode ASSETS is not ready: two sequential phases (ep11 P+O, then ep13 P+O), ≈ +0.5 h.

**Box S, standard learner, run `…-orcS-<sha>`: ep31, arms P then O = 2 trainings.**
- = std30's recipe, with `SPLIT=public` so the rollouts are scored vs mocap.
- `FC_FDR_OBJ=1 FC_FDR_TIPS=1 FC_VOC_INERTIA=1 FC_IMMEDIATE_FIRST_FRAME=0.25 TRAIN_ARGS=$FDR_TRAIN_ARGS SUF=s CR=0 BASE_EVAL=0 NREP=6 SEED=42 STEPS=250003456`, CK_SWEEP 0.4/0.6/0.8, `LIB=meshes/library_v3`, no pieces.
- `PAIRS="31:local:mck"` with `REFP=perc2 PDIR_ROOT=/content/perc2`, then `REFP=oracle NS=_oracle PDIR_ROOT=/content/oracle`.

Seeds: one seed (42) per arm, both arms the same. NREP = 6 official evaluations of each arm's chosen checkpoint (≥ 5
as required). Each rollout is scored three ways:
- `pipeline/score_registered.py EP DIR --meshes LIB`: rollout AUC, `reference` AUC (= ref-vs-mocap), static floor;
- `pipeline/qa.py policy`: sim_vs_ref vs the arm's own reference;
- SP-SR and MP-SR from the same score file.

Time and cost [E]. Basis [M]:
- setup 16 min on a normal day, 43 min today under HF 429;
- evb1420: two grasp-lock episodes from raw on one box in 1.2 h;
- rcA: one grasp-lock training + curve + 5 evaluations in 0.68 h;
- std30 / c25s42: one standard-learner training + sweep + 5 evaluations in 1.65–1.68 h.

| Box | Setup | References + G0 | Training + evaluations | Total | $ at $1.40/h |
|---|---|---|---|---|---|
| G | 0.3–0.7 h | 0.25 h | 2 waves × ≈ 1.1 h | ≈ 2.8–3.2 h | **≈ $3.9–4.5** |
| S | 0.3–0.7 h | 0.2 h | 2 × ≈ 1.6 h | ≈ 3.7–4.1 h | **≈ $5.2–5.7** |
| **Total** | | | | wall ≈ 4–4.5 h (both in parallel) | **≈ $9.1–10.2** (ledger planned $10) |

Store traffic per box:
- the env restore;
- pull-depth for its episodes (about 1 GB each);
- the final push.

No pull-run of old runs (everything is built fresh), which keeps the 429-prone calls to a minimum.

### 4.3 Gates and pre-registered readings (write them into the work log before launch)

**G0, before any training (on the box, per twin).**
- Condition: O's final reference (after mkref + CR) has ref-vs-mocap ≥ 0.95, mkref's support check passed without the
  fallback, and frame-0 centres are within 3 cm of perception.
- Expected: 0.97–1.0.
- If it fails: O is not trained for that twin (logged, pushed); P still runs.
- P's ref-vs-mocap is recorded too. Expected [E/M]: ep11 ≈ 0.88, ep13 ≈ 0.93–0.96, ep31 ≈ 0.82.

**Primary metric:** mean registered AUC vs mocap over the 6 rollouts of each arm's checkpoint, chosen by sim_vs_ref
(the recipes' own rule). Also report sd, min, and the count of rollouts below 0.70 (eval 14 and 30 are bimodal).

**R1, can the recipe copy this task type at all?**
- O ≥ 0.90: yes.
- O ≤ 0.75: no, even from true motion (robot / simulator / mesh / grasp limit).
- Otherwise: partial.

**R2, perception's share.** Δ = O − P.
- Δ ≥ +0.12: our reference is the main loss on this twin.
- |Δ| ≤ 0.05: it is not.
- Otherwise: inconclusive at one seed.
- Why 0.12: above the measured one-seed spread of these recipes. Grasp-lock on ep12 ranged 0.854–0.912 over 7 runs and variants;
  the standard learner on ep18 gave 0.776 vs 0.889 on two seeds.

**Use of the result:** only to direct the next effort on that eval task type (perception/reference vs
learner/physics). No eval policy, pack or checkpoint is chosen or tuned from it. No second seed or extension without a
new go-ahead.

### 4.4 Secondary readings (CPU after the boxes, $0)
- Registered AUC of every curve checkpoint in both arms, with `score_registered.py` on the pushed curve rollouts. This
  removes the checkpoint-choice asymmetry and shows the learning curve vs truth.
- `score_registered.py --per_frame` on the best and worst rollouts per arm, to find where O fails: start, grasp,
  transport, placement or nest.

### 4.5 If a twin needs the standard learner (2–3 h), and the extension
- ep31 already uses the standard learner (Box S). If the owner wants to stay well under $10, the fallback is ep31 P+O
  with the grasp-lock learner as a third pair on Box G: +≈ 1.1 h ≈ +$1.5, total ≈ $5.5. It must be labelled "learner
  differs from eval 30's packed standard-learner policy".
- **ep24 extension (eval 25), separate go-ahead:**
  - recipe: standard learner + `PIECES=meshes/carve/ev25`, in both arms;
  - P+O ≈ 3.7–4.1 h ≈ $5.2–5.7;
  - O-only ≈ 2.0 h ≈ $2.8. O-only compares against the old P (0.24–0.31, other commits), which is still decisive if
    O ≥ 0.6 or O ≤ 0.35.
  - Caveat: the ev25 slot carve was cut from eval-25's perceived assembly. On ep24 it is an object-level collision
    copy in both arms, not tailored to ep24.

## 5. Risks and unknowns
- **ep11 with ev10 pieces** [H]:
  - the beige cup was shrunk 8 mm in radius to fit eval-10's perceived nest; at the true nest it may sink deeper than
    the real cup (3 cm rim offset, note 15);
  - G0 plus the per-frame error locate this;
  - a failed ep11 O with a clean reference reads as "mesh/physics", which is itself the answer for eval 10.
- **REPLAN in the O arm** may move the oracle object path. It is recorded through the `reference` AUC per rollout.
- **Concurrent grasp-lock invocations:**
  - slot cleanup, make_assets and fc_patches races. Start O ≥ 120 s after P, with `SLOT_CLEAN=0`. OOM retry exists
    (2×).
  - The CPU mock must cover this.
- **One seed:** the R2 band 0.05–0.12 is inconclusive by design.
- **Under HF 429**, setup can take 45 min (vid5 box today), which is included in the upper estimates. The stall
  watchdog (30 min without progress) protects the spend; no fixed time limit.

## 6. Integrity
- Mocap is read only:
  - by `oracle_poses.py` in the O arm, for public eps 11 / 13 / 31 (and 24 if extended);
  - by G0 / `tools/ref_vs_mocap.py`;
  - by `score_registered.py` (scoring);
  - by this design's CPU checks.
- Arm P reads no mocap. As always, perception's own log prints scores after inference.
- Nothing goes to eval inference:
  - oracle data stays under `oracle*` names in `-orcG-` / `-orcS-` runs;
  - the pack guards (4.1.7) refuse them;
  - `oracle_poses.py` refuses eval ids;
  - `pipeline_ep.sh` refuses `PERC=oracle` with `SPLIT=eval`.
- No Kaggle. No eval result is used. Public development and eval inference stay separate.
- Record per run: exact command, machine, output paths, commit and result, including failures (CLAUDE.md). A `planned`
  ledger line goes in before each launch, and an `actual` line after.
