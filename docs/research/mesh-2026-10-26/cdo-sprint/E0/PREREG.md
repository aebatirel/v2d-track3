# E0 pre-registration: C0's mesh methods rebuilt on the eval episodes (CD-O sprint)

Written 2026-10-31 ~16:05-16:20 UTC, before any eval candidate mesh exists. The only eval runs before this file was
committed are the local dry run of the job script on eval 14 at a coarse stride (section 9); its meshes are a code
test, are not candidates and are not used for anything.

Why: owner, 31 Oct: "if the method of mesh creation better just recreate the meshes in the eval and use that", then
"Is there a way that we can get these faster with vast machines?". C0 (`../C0/MANIFEST.json`) swaps pot, lid, rack
(kit-of-parts fits) and blue cup (observed-point lathe), all built from PUBLIC episodes. E0 runs the same methods with
the same frozen settings on each eval episode where the object appears, on one many-core Vast CPU box
(`jobs/e0_box.sh`). There is no eval ground truth: E0 cannot be scored. Everything below is GT-free.

## 1. Pairs and inputs (inventory: `jobs/e0_inventory.py` -> `inputs/plan.json`)

| Object | Eval episodes (pairs) | Other tracked objects in those episodes |
|---|---|---|
| white_pot | 1, 3, 5, 6, 8, 28 (6) | lid (1), spoon (3, 5, 6), beige cup (8), rack (28) |
| white_pot_lid | 1 (1) | pot |
| plastic_dish_rack | 14, 15, 16, 28, 30 (5) | blue cup (14), spoon (15, 16), pot (28), sweeper (30) |
| blue_cup | 10, 14, 20, 32, 33 (5) | beige cup (10), rack (14), pitcher (20), spoon (32, 33) |

17 pairs in 14 episodes. Every episode: depth frames = track frames; kit roster objects = track bodies.

Inputs (no scan, no mocap, no parquet pose, no `*_align` file; none is uploaded to the box):
- **Tracks**: our eval tracks `data/eval/ep<N>/poses.npz` + `result.json` (scratchpad) = HF store
  `runs/20261025-evperc-4f596df/results/evalperc/ep<N>/` (sha256 match checked for eval 8 and 14). These are the pack's
  poses (work log 25 Oct: "identical poses to the pack's"); perception seeded with `meshes/library_v3`, so
  `cam_T_<obj>` are poses of the library_v3 bodies and the observed points land in the library_v3 object frame (the
  frame check in section 4 tests this). Caveat: eval 8 is packed with library_v3x; its white pot file is
  byte-identical to library_v3, so the pot frame is the same.
- **Depth**: FoundationStereo `cache/depth/eval/ep<N>/depths_fs0.5.npy` in the HF store (run
  `mesh-20261029-evdepth-92f3d86`; 21.4 GB for the 14 episodes). Only the depth of that run is used, not its tracks.
- **Calibration**: the dataset camera calibration (`public/meta/camera_calibration.json`, linked as `T3/calib.json`
  by `pipeline/fetch_data.sh`; same file as the public runs' `data/calib.json`, md5 56c32942...).
- **Hands**: no eval hands exist in the store, so they are made on the box exactly as the public G1 refs
  `hands.npz` were made (`pipeline/pipeline_ep.sh` step 2: `hands_mp.py`, MediaPipe 0.10.14, raw output, no
  refinement) from the eval cam_a video `ep<N>_a.mp4`. If hands fail for an episode, obs_points runs without
  `--hands` there, as the public prep did where no hands were stored (public rack ep12).
- **ROI / other-object meshes**: `meshes/library_v3/<obj>.glb` (as `prep_obs.sh`).
- **Kit**: `v2dlb/mesh_budget.py` (sha256 8f29481d...) for the budget check.

## 2. Code and exact commands (frozen)

Code: `jobs/frozen/` = the files of commit **2971a10** (27 Oct clean-up round), sha1 in `jobs/frozen/SHA1SUMS`:
`obs_points.py` fd1fec99, `prim_potlid.py` **c2627630** (= `results/prim/clean/code_state.txt`; the working-tree
file has an unreviewed 29 Oct WIP edit, commit 14eaf37, which E0 does NOT use), `prim_rack.py` 18a923c3 (the
committed clean-round file; CUP_LEAN is passed explicitly), `lathe_obs.py` ca8add36 (the 26 Oct 16:49 file; its only
change after the 16:27 `ep21_blue_cup_g1` build adds flags whose defaults equal the old constants), `obs_fidelity.py`
53d90e5d, `pipeline/recon_mesh.py` b388084e, `pipeline/hands_mp.py` 433d5008. C0's `frame_check.py` from this repo
(`../C0/scripts/`). Python: main venv pinned to the local venv (`jobs/req_main.txt`), MediaPipe venv pinned to the
local mpvenv (`jobs/req_mp.txt`). The box runs `jobs/e0_box.sh`; its task lists come from `jobs/e0_tasks.py`.
`$S` = `jobs/frozen/docs/research/mesh-2026-10-26/scripts`, `$LIB` = `meshes/library_v3`.

1. Hands, per episode: `hands_mp.py --ep N --split eval --t3 IN --depth D/epN/depths_fs0.5.npy --poses
   IN/eval/epN/poses.npz --video_a IN/eval/epN_a.mp4 --out R/hands/epN` (all other flags default).
2. Observed points, per pair (the `prep_obs.sh` command; all other flags default: stride 2, vox 4 mm, ...):
   `obs_points.py --poses IN/eval/epN/poses.npz [--hands R/hands/epN/hands.npz] --depth D/epN/depths_fs0.5.npy
   --calib IN/calib.json --obj O --roi $LIB/O.glb [--others X=$LIB/X.glb,...] --out R/obs/epN_O.npz`
   (`--others` = the episode's other tracked objects).
3. Candidate builds (single-episode builds for every object and episode; joint builds where the public rule had one):
   - **white_pot**, per pot episode, variants fit, nostem, tsdf, thick (`results/prim/potlid/run_fit.sh`; fit first,
     it writes the episode's axis cache, the other three reuse it):
     `prim_potlid.py pot R/obs/epN_white_pot.npz R/cand/white_pot/white_pot_epN_V.glb --variant V
     --lib $LIB/white_pot.glb --axis_cache R/axis/epN_white_pot.json` -> **24 candidates**.
   - **white_pot_lid**, eval 1, variants fit and tsdf at the clean-up round's shipped thickness
     (`PRIM_T_LID=0.0025 prim_potlid.py lid R/obs/ep1_white_pot_lid.npz .../white_pot_lid_ep1_t2.5_V.glb --variant V
     --lib $LIB/white_pot_lid.glb`) -> **2 candidates**. T_LID 2.5 mm is the grid midpoint of the clean-up round
     (passed at 1.5 / 2.5 / 4.0 mm); FLAG: the value equals the one that leaked from scan measurements into the first
     brief; it is not chosen by any eval number. Our points cannot measure it (the lid is seen from above only).
   - **plastic_dish_rack**: the clean-up round's command for the shipped config over the rack's eval episodes:
     `PRIM_T_WALL=0.0025 PRIM_CUP_LEAN=1 prim_rack.py run --obs_dir R/obs --out R/cand/rack/t2.5_lean1
     --episodes 14,15,16,28,30` -> per-episode full and nomk (shared floor depth from all episodes, as the public
     run), plus the joint fit (episodes whose own full fit is within JOINT_TOL 1.25 of the best, rigidly aligned on
     their points, moved to the mean frame) joint and joint_nomk -> **12 candidates**. T_WALL 2.5 mm FLAG as for
     the lid (clean-up round passed at 1.5 / 2.5 / 4.0 mm; the never-seen floor thickness).
   - **blue_cup**, per cup episode: `lathe_obs.py R/obs/epN_blue_cup.npz .../epN_blue_cup_g1.glb` (all defaults:
     the C0 cup's `g1` = hollow lathe + observed appendages) and the body-only `g0` (`--appendages 0`); plus the
     merged-points g1 lathe (the public candidate set had `ep21+22`, points concatenated without alignment:
     `e0_merge.py` over all 5 eval cup episodes) -> **11 candidates**.
   49 candidates in total. A build that fails is recorded with its log and is not a candidate.

## 3. Fidelity (as the public selections computed it)

`obs_fidelity.py OBS_1,...,OBS_k MESH` (defaults: trim 0.9, observed points subsampled to 300 k with seed 0, 200 k
mesh samples with seed 0, no ICP): trimmed mean observed->mesh distance + trimmed mean mesh->observed distance inside
the observations' bounding box, `sum_mm`. One mesh per process (the per-mesh result does not depend on the other
meshes of a call). Point sets: **ALL** = the observed points of all eval episodes of the object (this chooses), and
each single eval episode (diagnostic only). Meshes: all candidates, C0's public mesh (`../C0/MANIFEST.json`) and
library_v3 (both diagnostics, never candidates).

## 4. Exclusions and the pick (per object; `jobs/e0_select.py`, run on the box and re-runnable locally)

Excluded before the pick:
- raw candidate mesh not watertight (trimesh, process=True; C0's `frame_check.py` `watertight_raw`);
- the kit `budget_mesh(path, 4096, 4096)` raises or leaves > 4096 faces or vertices;
- GT-free frame check vs `meshes/library_v3/<obj>.glb` (C0 `frame_check.py`, no registration) beyond 3x the C0 public
  mesh's value for that object (`inputs/thresholds.json`, from `../C0/frame_check.json`):

  | Object | centroid offset max mm | median symmetric surface distance max mm | PCA axis angle max deg (major, middle, minor) |
  |---|---|---|---|
  | white_pot | 16.31 | 8.19 | 9.04, 14.0, 13.8 |
  | white_pot_lid | 21.94 | 7.06 | not checked, not checked, 2.39 |
  | plastic_dish_rack | 34.39 | 10.28 | 7.34, 5.89, 9.37 |
  | blue_cup | 10.58 | 7.60 | 9.43, not checked, not checked |

  An axis is not checked when its library_v3 PCA eigenvalue is within a ratio >= 0.8 of a neighbour (lid major /
  middle 0.83, cup middle / minor 0.84): there the axis direction is set by noise (C0 frame_check's own note), its
  angle is reported only. The surface distance still covers those meshes.
- no fidelity on ALL.

**Pick**: among the remaining E0 candidates of the object, the lowest `sum_mm` on ALL; ties: fewer raw faces, then
label order. The pick is shipped for every eval pair of the object (one mesh per object, as C0).

## 5. Diagnostics (do NOT choose)
- C0's public mesh and library_v3: fidelity on ALL and on each episode; their frame checks (C0 vs library_v3 must
  reproduce `../C0/frame_check.json`).
- Per eval episode, the own-episode alternative: among that episode's own eligible single-episode builds, the lowest
  fidelity on that episode's points, beside the pick's, C0's and library_v3's fidelity on the same points.
- The rack's own `prim_rack.py run` selection (`cand/rack/t2.5_lean1/selection.json`) as a cross-check of the table.

## 6. Recommendation rule
- white_pot, white_pot_lid, plastic_dish_rack: **E0** unless C0's ALL fidelity < 0.85 x the E0 pick's (C0 better by
  more than 15 %); then FLAG the object for the owner and recommend C0 for it. No eligible E0 candidate: C0.
- blue_cup (C0 cup held back from pack 9a): **E0** unless library_v3's ALL fidelity < 0.85 x the E0 pick's; then
  library_v3. C0's cup fidelity is reported only (flag if it beats the pick by > 15 %). No eligible E0 candidate:
  library_v3.

## 7. Known biases and limits (stated before results)
- In-sample advantage: E0 candidates are fitted to the same eval points that score them; C0 and library_v3 are
  out-of-sample there. The 15 % margin is the only allowance. Per-episode fidelity shows how much of a pick's lead
  comes from its own episode.
- Fidelity is not CD-O: on public data its Spearman with CD-O was 0.85 over 32 pot candidates and 0.5 over 5 cup
  candidates; public single-episode builds also varied a lot by episode (cup 0.291 vs 0.364). Lid and rack
  thickness is a prior that fidelity cannot judge (the lid's unseen underside makes fidelity prefer thin sheets).
- Eval hands are new (no stored eval hands); public pot / lid / cup points used G1 refs hands. A hand-holding
  episode with failed hands keeps more hand points (the free-space vote removes most).
- Eval 10: the blue cup nests the beige cup with a ~5 mm track offset in nest frames (work log 31 Oct 13:55); no
  episode is excluded (no tuning); its per-episode fidelity is reported.
- Nothing is scored against any ground truth (none exists for eval). Nothing is tuned: every setting above is the
  public one; no setting is changed after any eval build.

## 8. Run plan (box)
One Vast box, >= 32 CPU cores, ~<= $0.8/h, `SETUP=none`, job `bash docs/research/mesh-2026-10-26/cdo-sprint/E0/jobs/e0_box.sh`,
run id `mesh-20261031-e0-<commit>`; inputs uploaded by the agent to the store `runs/<run id>/inputs/` before the launch
(`jobs/e0_stage_inputs.py`, SHA256SUMS checked on the box). Outputs: `results/e0/` (obs, hands, candidates, logs,
`fidelity.jsonl`, `check/`, `selection.json`, `selection.md`, `SHA256SUMS`) pushed to the store run folder; the box
self-destroys (run_job.sh), stall watchdog 30 min. Ledger planned / actual lines (session mesh-bold).

## 9. Dry run (local, before this file was committed)
See NOTES.md: `jobs/e0_box.sh` with `E0_LOCAL=1`, a local fake store, eval 14 only (blue cup + rack), obs_points
stride 8 (DRY; production stride 2), 3 workers. Purpose: catch bugs. Its outputs are not candidates.
