# ep11 rollout gate for the eval-10 cup-nest fix (S12 V4p): pre-registration

Written 2026-10-31, 14:05 UTC. At that time no box had run this gate, no CPU rebuild of its two tracks had been made,
and no reference or rollout number of this gate existed. The numbers quoted below come from earlier, committed work
(mask10, ev10w, orcB). The launch commit must contain this file unchanged; build notes go to `BUILD.md`, the job string
and cost to `JOBS.txt`. Labels: [M] measured, [E] estimate, [H] hypothesis.

## 1. Question and status of V4p
- **V4p is post hoc.** mask10 (`../mask10/README.md` §0) pre-registered V1 (hold) as primary and V1h/V1d/V2/V3/V3p.
  V4p (S12 `--s12_mode support`: the blue cup at its frame-0 support height with the tracked sideways motion, then the
  beige cup seated by MuJoCo, then S2) was designed after seeing eval 10's GT-free track, because on eval 10 the
  pre-registered V1/V3 hold the blue cup inside a real 4.5 cm slide. Its ep11 reference-level number (+0.0698 lib,
  0.9012 → 0.9710) was measured after it was designed, under no rule.
- **This gate is V4p's pre-registered test.** It applies mask10 §0 "Next gate" (the ep11 rollout gate: the packed
  eval-10 grasp-lock recipe, P_o bundle + refine + mkref, seeds 42 and 43, NREP 10, against the same recipe without
  S12; falsified if the seed-mean ADD-AUC vs mocap rises by less than +0.05) to V4p instead of V1.
- **H-gate [H]:** on ep11 (eval 10's public twin), training the packed eval-10 recipe on the V4p reference raises the
  rollout's registered ADD-AUC vs mocap by at least +0.05 over the same recipe on the control reference.
- **Evidence behind it [M, earlier work]:**
  - orcB (oracle twins, one seed): with the true cup motion the recipe stacks the cups (0.940 ± 0.034); with our
    perceived motion every draw sits at the static floor (0.595 ± 0.000). Our reference is only moderately off by AUC
    (0.896) but much harder to copy (sim_vs_ref 0.518 vs 0.964).
  - mask10: V4p fixes the blue cup's tracked lift on ep11 (blue lib 0.865 → 1.000) and seats the beige 3.32 cm over the
    blue (mocap 3.17).
  - ev10w: the eval-10 nest intrusion is a relative-pose error (beige ~5 mm off the blue axis), not a narrow cavity.
    V4p with the unchanged `meshes/carve/ev10` is near intrusion-free on the hands-off frames (f118–160 median
    0.01 cm³) but still intrudes 3–12 cm³ on the hands-on frames f100–117. So V4p alone may not make the nest copyable.

## 2. Design (fixed)
### 2.1 Inputs: identical for both arms (single-file store downloads; the md5s are the files mask10 used)
| input | store path | md5 |
|---|---|---|
| P_o track (perc2, library_v3 templates; Phase 1) | `runs/20261030-orcP1b-87fc869/results/leak_p1/ep11/perc2/poses.npz` | sha256 `900abb7e…` (refine's record) |
| its world poses | `…/leak_p1/ep11/perc2/poses_world_vo.npz` | sha256 `c140137a…` |
| hands (25 Oct; camera equal to P_o's within 0.08 cm, Phase-1 check) | `runs/20261025-g1-022fece/refs/perc2m/ep11/hands_refined.npz`, `hands.npz` | `d9c391de…`, `0c7652fd…` |
| frame-0 depth for refine | frame 0 of `cache/depth/public/ep11/depths_fs0.5.npy` (877 MB), saved as `depth0.npy` | `5b9fb362…` (sha256 of the frame's bytes `070547…`, `phase1/inputs.tsv`) |
| depth for mkref | the same cache file, linked as the perception folder's `depths_fs0.5.npy` (mkref reads frame 0) | as above |
| collision pieces | `meshes/carve/ev10` (unchanged) | repo |

Object names and slot order come from the track's `cam_T_` keys (blue_cup, beige_cup). Nothing reads `observation.*`
or mocap.

### 2.2 Arms: they differ only in the refined track (the `poses.npz` mkref reads)
| arm | name | refine chain (committed code; the exact mask10 commands) | mask10 output it must equal |
|---|---|---|---|
| **C** control | `e11c` | `refine.py --steps S2` (the S2 baseline arm P_o) | `runs/Po/S2/ep11/poses.npz` md5 `b32ab808e560f8a3ebbec3658701066c` (ref-level lib 0.9012) |
| **T** treatment | `e11t` | `refine.py --steps S12 --s12_mode support` → `tools/nest_physics.py --mode inner --pieces meshes/carve/ev10 --hands <hands_refined>` → `refine.py --steps S2 --hands <hands_refined> --depth <depth0>` | `runs/Po/V4p/ep11/poses.npz` md5 `25801979433d7265bfd5aef2ca868dcc` (ref-level lib 0.9710) |

**B0, rebuild check on the box (before any reference is built).** The box rebuilds both tracks from the downloaded
inputs and compares them with the CPU outputs whose md5 is committed in `expect.json` (the build writes it; it must
equal the mask10 md5s above, or `BUILD.md` says why not). Per arm, over every frame and object:
- **IDENTICAL**: same md5 → go on.
- **NUMERIC**: `world_T_cam` byte-identical and every object pose within 0.01 mm and 0.001° → go on (reported).
- **DIFFERS** (arm T only): within 5 mm and 2° → go on with the box's own V4p track, flagged in every summary. MuJoCo's
  settle (500 steps of contact dynamics) need not be bit-reproducible on another CPU; the box's track is the same
  algorithm on the same inputs.
- otherwise **MISMATCH** → the job stops before any reference is built (no training); the gate is not run.

### 2.3 Reference build: identical for both arms
- `pipeline/pipeline_ep.sh 11` with `PERC=perc2`, `PDIR` = the arm's refined track folder (holding `poses.npz` and the
  depth cache link), the stored hands copied into the arm's reference folder (so `hands_mp.py` and `hand_refine.py` are
  skipped), `MKREF_ARGS="--wrist_cost 3.0" CONTACT_RETARGET=1 CR_ARGS="--rest_settle 1"` (variant mck, as the packed
  eval-10 base reference `20261024-evB-664e5fd` refs/perc2mck/ep10), `ASSETS=/content/assets` built by
  `make_assets.py meshes/library_v3 --pieces meshes/carve/ev10`, `STOP_AFTER=reference`. Folder
  `refs/perc2e11{c,t}mck/ep11`.
- Then the grasp-lock reference stages once per arm (`glock_public.sh REF_ONLY=1 SEED=42`, both arms in one call):
  folders `refs/perc2e11{c,t}_glockt/ep11`. Both seeds of an arm train on that one file (byte copies per seed,
  `refs/perc2e11{c,t}s{42,43}_glockt/ep11`, with `REUSE_REF=1 REQUIRE_REUSE=1`), so a seed difference is RL noise only.

### 2.4 Recipe: the packed eval-10 policy's (run `20261026-gl10A2-5e0e100`, its job.log)
- `ops/jobs/glock_public.sh`; `LIB=meshes/library_v3`, `PIECES=meshes/carve/ev10`, `SF=0`, `SETTLE=0`, `REPLAN=1`,
  `EVOLVE=0`, ILC default (4 iterations, no `ILC_HOLD`), `CURVE_REP=3`, `STEPS=70004736`, `ES=0`, `CURR_SCALE` unset,
  `TRAIN_SLOTS=2`, FDR rewards + VOC fix and the default curriculum (`fc_patches`), the kp 400 embodiment, and
  `GL_ARGS="--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15"`.
- **Checkpoint choice (no ground truth):** the checkpoint with the best mean sim_vs_ref over 3 official evaluations
  per curve checkpoint (glock_public.sh's rule, as gl10A2).
- **Deviations from gl10A2, stated now:** `SPLIT=public` (ep11, scored vs mocap); `NREP=10` (gl10A2: 5); `PAR=2`;
  `EVAL_TIMEOUT=1200` (`timeout -k 60`, as mass_check); the reference stages run once per arm and are shared by both
  seeds (gl10A2 had one seed); the current commit (both arms the same); the base reference comes from the P_o track +
  refine instead of a fresh perc2 run on the box (both arms the same).
- **Seeds 42 and 43**, one box, one commit. Per seed the two arms train in the same wave (TRAIN_SLOTS 2): wave 1 =
  C s42 + T s42, wave 2 = C s43 + T s43.

### 2.5 Scoring
NREP 10 official evaluations (FlashCHORD `scripts/evaluate_policy.py`, 1 world) of each cell's chosen checkpoint,
each scored as registered ADD-AUC vs mocap (`pipeline/score_registered.py 11 --meshes library_v3`, the leaderboard's
metric with our meshes) and sim_vs_ref (`pipeline/qa.py policy`, against the arm's own reference).

### 2.6 Verification (`tools/e11g_verify.py`; any failure makes the run INVALID)
- B0 band of each arm (IDENTICAL / NUMERIC / DIFFERS), and each arm's mkref read the poses.npz with that arm's
  rebuilt-track md5; both arms' mkref read the same depth cache and the same hands (md5).
- Per cell, the chain the official evaluator loads: the chosen checkpoint's saved config `task.parquet` → the arm × seed
  reference copy, whose md5 equals the arm's finished grasp-lock reference → `object_urdf_paths` → the same URDF files
  (equal md5 across the arms, 0.3 kg).
- **Config diff:** per seed the two arms' saved configs differ only in `output_dir`, `task.parquet`,
  `reference.parquet`, or in values equal once each arm's name is replaced by a token (where its files live).
- `reset.seed` is the seed; `training.total_environment_steps` is 70,004,736; the evaluated rollouts name the chosen
  checkpoint's sha256.
- A cell without a chosen checkpoint is **missing** (INCOMPLETE), not a verify failure.

## 3. Rule (fixed; `tools/e11g_verdict.py` applies it)
- Cell = arm × seed. Cell mean = the mean registered AUC vs mocap of its scored rollouts (unrounded). Seed mean = the
  mean of an arm's two cell means. **Δ = seed mean(T) − seed mean(C)**. **Δ(s) = cell mean(T, s) − cell mean(C, s)**.
- **PASS iff Δ ≥ +0.05 and no Δ(s) < −0.05** (no seed of T more than 0.05 below its C seed).
- **FAIL** otherwise.
- **INCOMPLETE** if any of the 4 cells is missing or has fewer than 8 scored rollouts. No reading from partial
  results. Only the missing cells are re-run, on this run's stored references (same files, `REUSE_REF`), and the rule is
  then applied once to the completed set.
- **INVALID** if the verification (2.6) fails, in particular if the config diff shows the arms differing in anything
  but the reference/task parquet and output paths. No reading.
- **Reported with the verdict, not gating:** per-seed cell means, sd, min, n, the 10 AUCs and the chosen checkpoint;
  Δ(s); the SE of Δ from the rollout spread, sqrt(Σ sd²/n)/2, and the two-seed spread |Δ(42) − Δ(43)|/2; sim_vs_ref per
  cell and its Δ; per-object AUC (blue_cup, beige_cup) per cell; each arm's trained reference vs mocap (`ref_auc`) and
  the static floor; eval timeouts per cell (curve and best) printed right after the label; each arm's zero-action
  sim_vs_ref and rest check; the B0 band.

## 4. Noise and power (stated before any result)
- Measured cell spreads on ep11 [M]: orcB P 0.595 ± 0.000 (10/10 at the static floor), O 0.940 ± 0.034;
  twin11v3x 0.570 ± 0.001. Elsewhere with grasp lock: ep2 sd 0.27–0.29 (bimodal), ep12 sd 0.02–0.03; between seeds on one
  reference: ep2 0.552 / 0.581 and 0.633 / 0.814, eval 32 0.397 / 0.634 / 0.803.
- [E] Model: cell mean = μ + b_s + e, sd(e) = sd/√10, sd(b_s) = τ (seed-to-seed). With C at the floor (sd ≈ 0, as orcB P),
  SE(Δ) = √((τ² + sd_T²/10)/2):

| sd_T | τ | SE(Δ) | P(PASS \| true Δ = 0) | P(PASS \| +0.10) | P(PASS \| +0.15) | 80 % detectable (2.8 SE) |
|---|---|---|---|---|---|---|
| 0.03 | 0.05 | 0.036 | 0.08 | 0.92 | 1.00 | 0.10 |
| 0.10 | 0.05 | 0.042 | 0.12 | 0.88 | 0.99 | 0.12 |
| 0.20 | 0.05 | 0.057 | 0.19 | 0.81 | 0.96 | 0.16 |
| 0.30 | 0.05 | 0.076 | 0.25 | 0.75 | 0.91 | 0.21 |
| 0.30 | 0.15 | 0.125 | 0.35 | 0.65 | 0.79 | 0.35 |

  If both arms are noisy (same sd and τ), SE grows by √2: e.g. sd 0.2, τ 0.05 → SE 0.081, P(PASS | 0) 0.27.
  (The seed-drop condition lowers every P(PASS) somewhat; not modelled.)
- Reading: at sd ≈ 0.1–0.3 the gate reliably detects only Δ ≳ +0.15–0.2, and a true null passes 12–35 % of the time.
  The mask10 expectation (30–70 % of orcB's +0.345) is Δ ≈ +0.10 to +0.24 [E]. +0.05 is a decision bar, not a
  significance test; that is why PASS buys only a retrain that must itself beat the packed draw on several draws (§5).

## 5. What PASS buys, what FAIL leaves
- **PASS:** the eval-10 retrain on eval 10's V4p reference: rebuild only eval 10's reference with the same chain (its
  stored track → `refine.py --steps S12 --s12_mode support` → `nest_physics.py --mode inner` → `refine.py --steps S2` →
  mkref + contact retargeting, mck), the packed recipe (2.4, `SPLIT=eval`, `meshes/carve/ev10`), 2 seeds; then a 10-draw
  confirmation of the chosen policy. Each step needs the owner's go-ahead. The packed eval-10 policy is swapped only if
  the multi-draw mean sim_vs_ref ≥ the packed draw (0.456, pack 7/8). Nothing goes to Kaggle without the owner.
- **FAIL:** eval 10 stays as packed. V4p is not used on eval. Further nest work (e.g. H-coax, ev10w README §6) needs
  its own pre-registration.
- **INCOMPLETE / INVALID:** no reading; re-run only the missing cells / fix the defect and re-run.

## 6. Integrity
- Public ep11 only. No eval episode, no Kaggle, no pack. Nothing here is tuned on eval results (there are none).
- Inference (refine, nest_physics, mkref, contact retargeting, grasp lock, ILC, re-plan, training, checkpoint choice)
  reads no ground truth: no mocap, no `pose` field of `observation.objects` (mkref takes only object names from the
  episode parquet). Mocap is read only by `score_registered.py`, after each rollout.
- The run id carries `-e11g-` (the job refuses any other). Every folder carries the arm prefix `perc2e11c` / `perc2e11t`
  (`refs/perc2e11{c,t}mck`, `refs/perc2e11{c,t}*_glockt`, `runs/perc2e11{c,t}s*_glock`,
  `results/perc2e11{c,t}s*_glock_public`, `results/ep11_gate`). No eval job pulls these names (eval jobs pull named
  runs and eval-episode folders only), and no eval episode can use an ep11 policy.
- The P_o inputs come from a `-orc` run (Phase 1) because that run also held the scan-template arm. The files pulled
  here are only its perc2 (library_v3) arm's poses, which read no mocap; mocap scores of that run (`result.json`,
  `log.txt`) are never pulled.

## 7. Build amendments (31 Oct ~15:10 UTC; mechanics only, before any gate result)
Sections 1–6 are unchanged since 14:05 UTC (sha256 of the file then: `7e5194e7b4b14e66…`). No box has run; the only
numbers produced since are the CPU rebuild (identical to mask10), the stage-(a) preview and mock outputs (`BUILD.md`).
The question, arms, recipe, metric, rule and bars are unchanged. Added, all in the direction of stricter checks:
- **Arm identity by content** is part of the verification (INVALID on failure): each arm's pre-contact-retargeting mkref
  output must carry its own rebuilt track's blue cup over the S12 window (closer than to the other arm's track), and each
  trained reference must be nearest its own base reference. The two trained references' blue-cup distance is reported.
- **Pinned venvs for the rebuild** (refine: numpy 2.5.4, scipy 1.18.1, trimesh 5.2.0, rtree 1.4.1; physics: numpy 2.4.6,
  scipy 1.18.0, trimesh 4.12.2, mujoco 3.8.1): the box's main python has no rtree, so S12 cannot run there.
- **B0 angle measure:** small rotation differences from the skew part of R_a R_bᵀ (the trace's arccos reads ~0.02° for
  equal float32 matrices). Bands unchanged.
- **Ties:** Δ and Δ(s) are compared with the bars with a 1e-9 tolerance, so an exact +0.05 (or −0.05) counts as met, as
  the rule's ≥ (and "below by more than") say.
- **INCOMPLETE re-run mechanics:** `RERUN_FROM=<run> CELLS="<arm>:<seed> ..."` trains only those cells on the first run's
  stored references (the seed copies must equal its manifest), on the same commit; the other cells' summaries and chosen
  checkpoints are pulled for the config diff and the verdict; their eval timeouts come from the first run's verify.json.
