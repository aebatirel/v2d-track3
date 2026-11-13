# ep11 rollout gate (control vs S12 V4p): build notes (31 Oct 2026, CPU only, nothing launched)

**Question.** Before any eval-10 retrain on the cup-nest fix, does V4p (S12 `--s12_mode support` + MuJoCo seat of the
beige cup + S2) make ep11's reference copyable by the packed eval-10 recipe? Rule, noise and what PASS / FAIL buy:
`PREREG.md` (written 14:05 UTC, before any build output; sha256 `7e5194e7…` at writing; §7 added ~15:10 UTC lists the
build amendments, mechanics only, sections 1–6 byte-unchanged). Launch string and cost:
`JOBS.txt`. Labels: [M] measured here, [E] estimate, [H] hypothesis. Machine: this Claude cloud VM (4 CPU), ~14:00–15:30
UTC, $0; no GPU, Vast or Kaggle; nothing committed by this step.

**Job.** `ops/jobs/ep11_gate.sh` (run id `<date>-e11g-<sha7>`), one RTX PRO 6000 box: arms C (`e11c`, P_o + S2) and T
(`e11t`, P_o + V4p) × seeds 42, 43 = 4 trainings in 2 waves, NREP 10, verdict PASS / FAIL / INCOMPLETE / INVALID.
Expected ~$4.2–7.9, central ~$5.4 [E] (JOBS.txt table).

## 1. Where the ep11 perception inputs live (the P_o bundle) [M]
All six were fetched here with one `hf_hub_download` each (no listing; `scratchpad/ep11gate/dl`), and every md5 equals
the file mask10 used (`scratchpad/leak/t1/in_Po/ep11`, T1's links):

| file | store path | md5 | made by |
|---|---|---|---|
| P_o track | `runs/20261030-orcP1b-87fc869/results/leak_p1/ep11/perc2/poses.npz` | `2f4800ff…` | Phase-1 box b (`ops/jobs/perc_leak.sh`, arm o = perc2 with `MESH_DIR=library_v3`, KF_MIN 120) |
| its world poses | `…/leak_p1/ep11/perc2/poses_world_vo.npz` | `6e2c2ff5…` | same |
| frame-0 depth | `…/leak_p1/ep11/depth0.npy` | `5b9fb362…` | `tools/leak_p1.py inputs` = frame 0 of the cache (its `inputs.json` records frame0 sha256 `070547…` = `phase1/inputs.tsv`) |
| depth cache (mkref) | `cache/depth/public/ep11/depths_fs0.5.npy` | 876,800,128 B | stereo cache of the refine study |
| hands | `runs/20261025-g1-022fece/refs/perc2m/ep11/hands_refined.npz`, `hands.npz` | `d9c391de…`, `0c7652fd…` | 25 Oct g1 box; Phase 1 checked P_o's camera = the refine camera (max abs 1e-16 on ep11, `phase1/scores/p1_check.json`) |

The P_o run id carries `-orc` because the same box also tracked with the organiser scans (P_s, `perc2scan/`); the job
pulls only the `perc2/` (library_v3) arm and `depth0.npy`, never `perc2scan`, `result.json` or `log.txt` (perc2's mocap
scores). `tools/no_oracle.py` refuses that source path (as intended for packs) and accepts every gate name
(`cpu/out/no_oracle_names.txt`): the gate's references are GT-free, and an ep11 policy cannot serve an eval episode.

## 2. The two refined tracks, rebuilt on CPU from the stored inputs [M]
`tools/e11g_tracks.sh IN OUT PY FPY` runs the exact mask10 commands (`m10_run.sh` S2; the V4p logs in
`runs/Po/posthoc_ep11`). On the downloaded inputs, with the committed code (refine.py `aae1fb41…`, nest.py `7e063b94…`,
nest_physics.py `e9500036…`, the mask10 final hashes):

| arm | output md5 | mask10 file | stages |
|---|---|---|---|
| C (S2) | `b32ab808e560f8a3ebbec3658701066c` | `runs/Po/S2/ep11/poses.npz`: **identical** | — |
| T (V4p) | `25801979433d7265bfd5aef2ca868dcc` | `runs/Po/V4p/ep11/poses.npz`: **identical** | S12 `1b5f84c6…`, physics `74c04533…` (both = mask10's pre4 / pre4_phys); window [42, 137), 36 frames settled, beige dz median −1.07 cm |

These two files and their md5 are committed in `expect/` (`expect.json`, `C_poses.npz`, `T_poses.npz`, 45–53 KB each;
`.gitignore` gets a one-folder exception). The box does **not** use them as inputs: it rebuilds both tracks itself
and B0 (`tools/e11g_verify.py b0`) compares. They are in git only because the NUMERIC / DIFFERS bands need the expected
poses, not just their md5.

**Environment sensitivity (why the box uses two pinned venvs)** (`cpu/out/track_rebuilds.json`):

| refine python | physics python | C | T |
|---|---|---|---|
| scoring venv (py3.13, numpy 2.5.4, scipy 1.18.1, trimesh 5.2.0, rtree 1.4.1) = mask10 | fcvenv (py3.12, FlashCHORD lock: numpy 2.4.6, scipy 1.18.0, trimesh 4.12.2, mujoco 3.8.1) = mask10 | identical | identical |
| **copy of the box main env** (snapshot pip freeze: trimesh 5.1.1, **no rtree**) | fcvenv | identical | **S12 crashes**: `ModuleNotFoundError: rtree` (trimesh proximity in `pipeline/nest.py`) |
| box main env + rtree 1.4.1 | fcvenv | identical | identical |
| minimal py3.13 venv numpy 2.5.4 / scipy 1.18.1 / trimesh 5.2.0 / rtree 1.4.1 (**the job's refine venv**) | fcvenv | identical | identical |
| box main + rtree | py3.13 venv pinned to the FlashCHORD lock (**the job's physics venv**) | identical | identical |
| the job's two venvs, numpy AVX-512 dispatch off (`NPY_DISABLE_CPU_FEATURES=X86_V4`) | same | identical | identical |
| refine venv + mujoco 3.8.1 for both | same | identical | **differs**: beige on 42 settled frames, max 0.37 mm / 0.34° (B0 band DIFFERS) |

- So the job builds `/content/e11g_vr` (numpy 2.5.4, scipy 1.18.1, trimesh 5.2.0, rtree 1.4.1) and `/content/e11g_vp`
  (numpy 2.4.6, scipy 1.18.0, trimesh 4.12.2, mujoco 3.8.1) with `python -m venv` + pip, falling back to `uv` (uv 0.13.4
  is in the box env). The physics settle depends on the numpy/trimesh versions at the sub-mm level, not on numpy's SIMD
  dispatch. A box CPU can differ [M, review: T is IDENTICAL on SkylakeX/Cooperlake OpenBLAS kernels and DIFFERS by ≤ 0.78 mm / 0.65° on Haswell/Zen and 6 others, so expect DIFFERS on many boxes]; the DIFFERS band (≤ 5 mm, ≤ 2°, T only) lets the gate go on with the box's
  own V4p track, flagged. C (pure numpy) must be IDENTICAL or NUMERIC (≤ 0.01 mm, ≤ 0.001°, camera byte-identical).
- **Finding for any later V4p use on a box (eval-10 retrain):** the box's main python cannot run S12 (no rtree). The
  retrain must rebuild eval 10's V4p track the same way (pinned venvs) or on CPU.
- B0 on the variants and on synthetic fixtures (`cpu/mock/b0_fixtures.py`, `cpu/out/b0_runs.txt`): every real rebuild
  GO (IDENTICAL, or T DIFFERS for the one-venv variant); C moved 0.005 mm → NUMERIC (go); C moved 1 mm → STOP (C has no
  DIFFERS band); T moved 3 mm → DIFFERS (go); T moved 6 mm, T = C's track, or a camera changed by 1e-9 m → STOP.
- B0's small-angle measure is the skew part of R_a R_bᵀ: the arccos of the trace reads ~0.02° for two *equal* float32
  matrices (they are not exactly orthonormal), which would have broken the 0.001° band; fixed before use.

## 3. Reference build, the part that runs on CPU (mkref stage a) [M]
mkref's own `fit_table` / `table_frame` / per-object snap on each arm's rebuilt track and frame-0 depth
(`oracle-twins-20261030/cpu/scripts/mkref_a_emul.py`; `cpu/out/stage_a/`):

| arm | support check | table inlier frac | bottoms (blue / beige) | snap |
|---|---|---|---|---|
| C | ok | 0.575 | +0.04 / −0.03 cm | −0.04 / +0.03 cm |
| T | ok | 0.575 | +0.04 / −0.03 cm | −0.04 / +0.03 cm |

Both arms get the same table frame and snaps (frame 0 is the same in both; S12 never changes frame 0). Oracle-side
preview (public mocap, after inference, diagnostic only; `tools/ref_vs_mocap.py`): stage-(a) reference vs mocap
**C 0.9012** (blue 0.865, beige 0.9375), **T 0.9722** (blue 1.000, beige 0.944), consistent with mask10's track-level
0.9012 / 0.9710. Not runnable on CPU here: hands → E2S IK, contacts, contact retargeting (rest settle), grasp lock, ILC,
re-plan, training, evaluation.

## 4. How the arms differ in exactly one input
- **Folders.** `glock_public.sh`'s PERC field (oracle twins, mass check) gives every arm × seed its own folders:
  base `refs/perc2e11{c,t}mck/ep11` (pipeline_ep.sh `PERC=perc2 VARIANT=e11{c,t}mck`), grasp-lock reference
  `refs/perc2e11{c,t}_glockt/ep11` (built once per arm, `REF_ONLY=1 SEED=42`), per-seed byte copies
  `refs/perc2e11{c,t}s{42,43}_glockt/ep11` + base links `refs/perc2e11{c,t}s{42,43}mck/ep11` + `rest_check.json`
  (`tools/e11g_verify.py arms`, mass_arm.py's layout without the asset copy), runs `runs/perc2e11{c,t}s*_glock`, results
  `results/perc2e11{c,t}s*_glock_public`. Training: `REUSE_REF=1 REQUIRE_REUSE=1` (exit, rebuilding nothing, if a copy is
  not a finished reference).
- **Same everything else.** One job-wide recipe (unset/overwritten environment, nothing overridable from the job
  string), one asset root `/content/assets` (library_v3 + ev10 pieces, 0.3 kg), the same depth cache, the same stored
  hands (copied into each arm's reference folder so hands_mp / hand_refine are skipped), the same mkref / CR arguments,
  the same seeds and box.
- **Checked after training** (`tools/e11g_verify.py verify`, INVALID on any failure; PREREG 2.6): B0 bands; mkref read
  the arm's own rebuilt track (md5 before = after = B0's) and both arms the same cache and hands; **arm identity by
  content** (each arm's pre-CR mkref output `e2s_reference.parquet` carries its own track's blue cup in the window —
  mock: 0.04 cm to its own vs 2.4 cm to the other — and each trained reference is nearest its own base); the
  evaluator's chain per cell (checkpoint config → its arm × seed copy, md5 = the arm's reference → the same URDF files
  in all cells, 0.3 kg); per seed the two saved configs differ only in `output_dir`, `task.parquet`,
  `reference.parquet` (mass_verify's `pair_diff` with arm-name normalisation); seed, steps, evaluated checkpoint sha256;
  eval timeouts counted. Reported: how far apart the two trained references' blue cups are (window and hands-off f101–136):
  if contact retargeting's rest settle had already lowered C's lifted blue cup, the treatment would be smaller than the
  track contrast [H; the mock's CR stub copies, so this is untested].

## 5. Recipe: the packed eval-10 policy's (from `runs/20261026-gl10A2-5e0e100/job.log`) [M]
`glock_public.sh` at 5e0e100 with `SPLIT=eval SF=0 CURVE_REP=3 NREP=5 SEED=42 LIB=library_v3 PIECES=meshes/carve/ev10
REPLAN=1 EVOLVE=0`, `GL_ARGS="--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1
--approach_cm 15"`, steps 70,004,736, ES 0, CURR_SCALE 1, SETTLE 0, no ILC_HOLD (4 ILC iterations), FDR rewards + VOC fix
and the default curriculum (`tracking_250m_mixed_reset_v2d`), base reference `20261024-evB-664e5fd` refs/perc2mck/ep10
(variant mck: mkref `--wrist_cost 3.0`, contact retargeting `--rest_settle 1`). Chosen 60M by sim_vs_ref, 5-draw mean
0.4539. The gate keeps all of it; deviations (PREREG 2.4): SPLIT public, NREP 10, PAR 2, EVAL_TIMEOUT 1200, reference
stages once per arm shared by both seeds, current commit, base reference from P_o + refine instead of a fresh perc2.

## 6. Changes
| file | change |
|---|---|
| `ops/jobs/ep11_gate.sh` | new: the gate job (inputs + md5, pinned venvs, tracks + B0, references, grasp-lock stages, seed copies, 2 waves, verify, verdict, push; `RERUN_FROM` + `CELLS` for an INCOMPLETE re-run of only the missing cells on the stored references) |
| `tools/e11g_tracks.sh` | new: the two refined tracks from one input folder (the mask10 commands), `tracks.json` with md5s and package versions |
| `tools/e11g_verify.py` | new: `b0`, `arms`, `verify` (imports mass_verify / mass_arm helpers unchanged) |
| `tools/e11g_verdict.py` | new: the PREREG rule (imports mass_verdict's `stats` / `r4` unchanged); ties at exactly +0.05 / −0.05 count as met (1e-9) |
| `.gitignore` | one exception: `docs/research/work/perception-sprint-20261031/ep11gate/expect/*.npz` |
| `docs/research/work/perception-sprint-20261031/ep11gate/` | PREREG.md, JOBS.txt, BUILD.md, expect/ (B0 comparison files), cpu/mock/ (setup.sh, run_mock.sh, run_all.sh, check_all.sh, stub.py, hf_stub.py, check.py, verdict_tests.py, b0_fixtures.py), cpu/out/ (evidence) |

Not changed: `pipeline/refine.py`, `pipeline/nest.py`, `tools/nest_physics.py`, `pipeline/pipeline_ep.sh`,
`ops/jobs/glock_public.sh`, `tools/mass_*.py`, `tools/no_oracle.py`, any eval job. `bash -n` clean on every new script.

## 7. CPU mock of the whole job (`cpu/mock/`, outputs `cpu/out/`)
A repo copy with `/content` → the mock root; stubbed GPU / IK steps (mkref's stage (a) is real, then a minimal parquet;
contact retargeting, grasp lock, ILC copy; trainer and evaluator load references the way FlashCHORD does and write /
read safetensors configs; mock scores give T +MOCK_EFFECT when the loaded reference holds the blue cup down); REAL
e11g_tracks.sh / refine.py / nest_physics.py (in the local pinned venvs the job's `python -m venv` is mapped onto),
make_assets.py, pipeline_ep.sh, glock_public.sh, ckpt_curve.sh, store.sh, e11g_verify.py, e11g_verdict.py; a stub `hf`
that serves single files and refuses listings, and whose uploads land in a fake store (so a re-run box can pull them).

`run_all.sh` runs eight scenarios, `check_all.sh` runs `check.py` on each (`cpu/out/mock_checks.txt`,
`mock_check_<n>.txt`, and each scenario's own summary / verify / verdict text in `mock_<n>/`). Mock numbers are NOT
evidence about V4p.

| scenario | injected | outcome | checks |
|---|---|---|---|
| pass | mock effect +0.12 on references that hold the blue cup | **PASS** (C 0.595, T 0.715, Δ +0.120, seeds +0.119 / +0.121) | 49/49 |
| fail | effect +0.02 | **FAIL** (Δ +0.020 < +0.05) | 49/49 |
| seeddrop | effect +0.20, T seed 43 lowered 0.27 | **FAIL** by the seed clause (Δ +0.065 ≥ +0.05, seed 43 −0.069) | 49/49 |
| invalid | one extra config key in T s42's training | **INVALID** (config diff `training.mock_extra_setting`) | 49/49 |
| incomplete | T s43's training exits 1 | **INCOMPLETE** (`e11t/s43` missing; everything else VERIFIED) | 41/41 |
| rerun | a new box: `RERUN_FROM=<incomplete's run> CELLS="e11t:43"` | **PASS** over all four cells; only e11t s43 trained; seed copies equal the first manifest | 16/16 |
| b0stop | the committed T expectation replaced by C's | **STOP** at B0 (MISMATCH): no reference, no training; reason pushed | 9/9 |
| badinput | a corrupted P_o `poses.npz` served by the store | **STOP** at the input md5 check, before anything is built | 9/9 |

What the checks assert in the verdict scenarios: no store listing (6 single-file downloads; the re-run 43) and exactly
one upload; hands_mp / hand_refine / perc2 never ran; the two pinned venvs got their exact pins; B0 IDENTICAL on both
arms (the real refine + physics ran on the downloaded inputs); mkref ran once per arm on that arm's rebuilt track
(md5 `b32ab808…` / `25801979…`), the ep11 depth cache, the stored hands (`d9c391de…`), `--wrist_cost 3.0`,
`/content/assets`, SPLIT public; contact retargeting `--rest_settle 1` once per arm; grasp lock only in the reference
stages (2 arms × plan + re-plan) with gl10A2's GL_ARGS and kp 400; each cell trained once, on its own copy, with its
seed and 70,004,736 steps, loading the same 0.3 kg URDFs under `/content/assets` in all cells; the arm's reference
holds the blue cup (T, lift < 1 cm) or not (C, +2.42 cm); 10 best + 21 curve evaluations per cell, each on the
checkpoint's own task; every mocap scoring call of a cell after that cell's training finished; wave order (both s42
trainings done before any s43 starts); both arms of a seed with identical training arguments; the verdict and the
re-run file list in the push; no depth cache in the push; arm identity (pre-CR mkref output: 0.04 cm to its own track,
2.4 cm to the other).

A first re-run attempt read INVALID: the mock trees of the two boxes had different roots, so the earlier cells'
checkpoint configs named files under the first tree (a mock artefact; on Vast both boxes use `/content`). The verify
check that caught it is the intended one (a cell must train on its own copy). The mock now runs the re-run at the first
tree's path; `cpu/out/mock_rerun/` is that run.

`verdict_tests.py` (synthetic cells): 14/14 (`cpu/out/verdict_tests.json`): PASS at Δ = +0.105 and at exactly +0.05; FAIL at +0.03 and +0.0499; FAIL on a seed at −0.07 with Δ +0.065; PASS with a seed at exactly −0.05 and Δ +0.05; INCOMPLETE with 7 scored rollouts in a cell (PASS with 8), with a missing summary, and with a cell verify lists as missing; INVALID when verify failed (also with a missing cell) or verify.json is absent; per-object deltas omitted when the per-rollout score files are absent.

## 8. Integrity
- Public ep11 only; no eval episode, pack, Kaggle or GPU. Nothing eval-side changed.
- Inference (refine, physics, mkref, CR, grasp lock, ILC, re-plan, training, checkpoint choice) reads no ground truth;
  mkref takes only object names from the episode parquet. Mocap is read by `score_registered.py` after each rollout and,
  here on CPU, by the stage-(a) preview (diagnostic, after inference, public). The mock checks that every mocap scoring
  call of a cell comes after that cell's training finished.
- Run ids `-e11g-`; folders `perc2e11{c,t}*`, `results/ep11_gate`; eval jobs pull named runs and eval-episode folders only.

## 9. Risks and open items
1. **Box reproducibility of T** [H]: pinned venvs reproduce mask10 byte for byte here, also with AVX-512 dispatch off;
   another CPU could still move the settle at the sub-mm level → DIFFERS (go, flagged); > 5 mm / 2° → the job stops
   after setup (~$1.2–2.2 with run_job.sh's 30-min FAIL_HOLD; review F3).
2. **pip / uv on the box**: the venvs need PyPI (other jobs `pip install` there). If both methods fail the job stops at
   setup.
3. **Contact retargeting's rest settle** may partly fix C's lifted blue cup on the hands-off frames, shrinking the arm
   contrast; reported (`arms_apart_blue_cm`), not gating. It is part of the packed recipe, so it belongs in both arms.
4. **Power** (PREREG §4): +0.05 is a decision bar. At cell sd 0.1–0.3 a true null passes 12–35 % of the time; only
   Δ ≳ +0.15–0.2 is reliably seen. PASS buys only a retrain that must beat the packed draw on several draws.
5. **What ep11 cannot test**: V4p differs from V1 where eval 10 has a slide before the nest (mask10 §4); ep11 has none.
   The hands-on nest frames f100–117 still intrude 3–12 cm³ with V4p + ev10 (ev10w README).
6. **C is not the packed eval-10 base path exactly** (packed: fresh perc2 without refine): the gate isolates S12 V4p
   given S2; an eval-10 retrain on V4p would carry S2 as well.
7. **INCOMPLETE re-run**: the other cells' per-object AUCs are not pulled (summary + checkpoint only), so per-object
   deltas are missing in a merged verdict; the rule does not use them.
8. `glock_public.sh` logs `glock_public summary: {}` for PERC-prefixed pairs (its job-level summary globs the unprefixed
   folder; also in mass_check). Cosmetic; `results/ep11_gate/summary.json` is the gate's summary.

## 10. Exact commands (this VM, 31 Oct ~14:05–15:30 UTC; HEAD ed45786 + the uncommitted files above)
`S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad`, `W=$S/ep11gate`,
`PY=$S/map/scoring/venv/bin/python`, `G=docs/research/work/perception-sprint-20261031/ep11gate`.
1. Inputs: `$PY -I $G/cpu/scripts/dl.py $W/dl <the 5 store paths of section 1> runs/20261030-orcP1b-87fc869/results/leak_p1/ep11/inputs.json`
   (one `hf_hub_download` each); copies into `$W/cpu/in/ep11`.
2. Tracks: `bash tools/e11g_tracks.sh $W/cpu/in/ep11 $W/cpu/tracks_a $PY $S/carve/fcvenv/bin/python` (11 s), and the
   variants of section 2 with the venvs `$W/boxmain_venv`, `$W/e11g_venv`, `$W/phys_venv` (uv, py3.13; pins as listed),
   `NPY_DISABLE_CPU_FEATURES=X86_V4` for the dispatch test. Expectation: `expect/` written from `tracks_a`.
3. B0: `$PY -I tools/e11g_verify.py b0 --tracks <tracks> --expect $G/expect --out ...` on every variant and on
   `$PY -I $G/cpu/mock/b0_fixtures.py $W/cpu/tracks_a <out>` (`cpu/out/b0_runs.txt`, `cpu/out/b0/`).
4. Stage (a): `$PY -I docs/research/work/oracle-twins-20261030/cpu/scripts/mkref_a_emul.py <repo> <tracks>/{C,T}/ep11/poses.npz
   $W/cpu/in/ep11/depth0.npy $S/hfds/track_3/public/meta/camera_calibration.json meshes/library_v3 11 $S/map/scoring/t3 <out>.parquet`,
   then (oracle side) `$PY -I tools/ref_vs_mocap.py 11 <out>.parquet --meshes meshes/library_v3 --t3 $S/map/scoring/t3
   --kit $S/map/scoring/kit/v2d_submission_kit` (`cpu/out/stage_a/`).
5. Mock: `bash $G/cpu/mock/run_all.sh` (eight scenarios, ~4.5 min each, trees in `$W/mock/<n>`), `bash $G/cpu/mock/check_all.sh`;
   `$PY -I $G/cpu/mock/verdict_tests.py <repo> $W/vt $G/cpu/out/verdict_tests.json`.
6. Guard: `$PY -I tools/no_oracle.py <name>` for each gate name and the P_o source path (`cpu/out/no_oracle_names.txt`).
