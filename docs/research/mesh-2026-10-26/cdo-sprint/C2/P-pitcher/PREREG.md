# C2 / Track P (water_pitcher): pre-registration

Written 2026-10-31, 18:20-18:33 UTC (commit 5982c31 at 18:33), before any candidate is built and before any scoring. No scan, mocap, parquet
pose or `*_align` file was read for this track. Step log: `NOTES.md`. Rules: the C2 brief (as C0b: GT-free
construction and choice, no scan-derived or unknown-origin constant, one scoring per picked mesh, C0's AUC guard).
`SCR` = `/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad`. Repo paths are
relative to `docs/research/mesh-2026-10-26/` unless they start with `docs/`, `meshes/` or `pipeline/`.
Labels: [M] measured without ground truth; [D] diagnostic scored against public ground truth; [E] estimate;
[H] hypothesis.

## 1. Hypothesis and prediction

**H-P [H] (from the brief):** an observed-point lathe body plus the observed appendages (handle, spout) that
`lathe_obs.py` splats from our ep21 / ep22 points reaches CD-O <= 0.6 cm on eval 20 with add_med <= library + 2 mm.

- **Falsified** unless the scored pick is a WIN (section 5) **and** its CD-O at the eval-20 seed is <= 0.60 cm.
- A WIN with CD-O in (0.60, 0.8742] does not save H-P, but the mesh can still be adopted (section 7).

**GT-free prediction, before any build [M]:** H-P is likely falsified.
- Our own ep22 RGB crop (`SCR/crops/ep22/water_pitcher_k174.png`, a public video frame) shows an elephant-shaped
  watering can: a narrow oval base, a long up-swept spout (about the body's height again), a handle loop whose lower end
  nearly reaches the table, and a slanted open top. It is not near-axial.
- Earlier GT-free notes say the same: "not a lathe (rotational consistency 8.85 mm)" (`gmg/evidence.md`); lathe gate
  failed (MAD 8.8 mm) (`ledger-of-past-mesh-work.md` 2a).
- So the lathe body can explain only the lower body. The spout and handle become appendage splats of the observed
  surface, and the unseen sides stay open.
- This prediction is not a gate.

## 2. Inputs (GT-free)

**Observed points:** the C0b pass-B points of the pitcher on public ep21 and ep22 (C0b PREREG 3.4, commit 8174998).
- Built here by `scripts/obs_c0b.sh EP`, which calls C0b's own `C0b/jobs/c0b_obs.sh`. These are exactly the
  commands the C0b box runs (stages obsA, obsB):
  - pass A: water_pitcher and blue_cup, `--roi_cube 0.30`, no co-object carving;
  - pass B: water_pitcher with `--others_pts blue_cup=<pass-A blue cup>`;
  - cube guard after each pass: if more than 0.1 % of the points lie within 8 mm of a face, rebuild once at 0.45 m.
- Code: `scripts/obs_points.py` at commit 00e8584, which holds the C0b options.
- **Tracks:** our sweep base tracks `SCR/data/sweep/ep21|22/poses.npz`:
  - sha256 `7e4dae9c...b8a8c` and `50acd616...4e4c`;
  - equal to the store run `20261025-sweep-a894083` LFS sha256 [M].
  - Tier P1 (library_v3-seeded tracks; flag F4, C0b AUDIT record 161: an owner / organiser question, not a constant).
- **Hands:** G1 MediaPipe `SCR/data/sweep/ep21|22/hands.npz`, sha256 `8143230b...` and `77b56f43...` (store
  `20261025-g1-022fece`).
- **Depth:** FoundationStereo `cache/depth/public/ep<N>/depths_fs0.5.npy` from the store.
  - ep21: full file, sha256 `f2aa07b7...53e6` = LFS.
  - ep22: the whole file was streamed and hashed (sha256 `927c2585...030b` = LFS). Because only ~1 GB of disk is
    free, only the frames obs_points reads were stored (t even, stride 2), in a sparse file of the full size.
    `obs_points.py` memory-maps the file and reads only `D[0]` and `D[t]` for t in `range(0, N, 2)`, so its inputs are
    byte-identical.
  - The downloader is `SCR/cdo_c2/P/dl_depth_sparse.py`.
- **Calibration:** `SCR/data/calib.json` (md5 56c32942...).
- **Frame.** The sweep tracks were made with library_v2's pitcher, which is identical to library_v3's (work log 25 Oct
  23:57: "v3 = v2 for the pitcher"). So the points, and every candidate, are in the library_v3 pitcher frame that eval
  20's rollouts use. No placement step is applied, and nothing is aligned to library_v3 (C0a diagnostic).

**Constants (every one cites C0b `AUDIT.json` / `REPLACEMENTS.json`):**

| Setting | Value | Audit id | C0b class / origin |
|---|---|---|---|
| obs ROI | cube of half-side 0.30 m about the track origin; guard 0.1 % within 8 mm -> 0.45 m | 133 | LIB (generic gmg A.6 crop) |
| co-object carving | 20,000 random pass-A blue-cup points (seed 0), within 12 mm | 134, 135 | LIB (own observation); KEEP |
| stride, margin, zmax, pix_stride | 2, 20 mm (unused in cube mode), 1.5 m, 1 | 136, 137, 139, 143 | G |
| edge filter | 20 mm | 138 | KEEP |
| table band | 8 mm | 140 | KEEP (U-suspect timing disclosed by C0b) |
| hand capsules | 30 / 45 / 150 mm | 141 | G |
| vote: vox, hit, free, min_hits, min_ratio | 4 mm, 4 mm, 10 mm, 3, 0.5 | 142 | A6 |
| per-frame table refit | 30 / 12 mm, 500, 20000, 10 deg | 145 | KEEP |
| table_plane | thr 6 mm; sampling; hmin / hmax; cone | 148-151 | KEEP / G / O |
| lathe DH, NSEC, min_pts, knn, vox_ds, axis subsample | 3 mm, 24, 8, 24, 1.5 mm, 60000 | 106, 108-110, 120, 124 | G |
| lathe IRLS, rot. consistency, axis candidates, smoothing, nseg | as coded | 111-115, 129 | G |
| lathe minsec, body extent, view split, open-end vote | 6; r < max r_out + 5 mm, P0.5 / P99.5; 0.3; 50 % | 123, 126, 125, 127 | O, O, G, G |
| axis tie | `--tie 1.0` (no tie-break) | 107 | GEN |
| floor | `--floor base_t` (floor top = base + t) | 131, 122 | GEN; NEVER `observed` |
| wall | measured (>= 3 two-wall bins); else `--t_fallback` = thickness chain (below) | 128 | TH |
| wall clamp | `--tmin 0.0015`, `--tmax 0.008` | 121 | A6 (sensor floor, two voxels) |
| appendage threshold | `--app_d` = 3 sigma | 117 | A6 (gmg A.6 grammar; sigma own) |
| appendage size, cap-in margin, splat | 400 points; 3 mm; 2 mm voxels, pad 3, dilation 1, closing 2, Gaussian 0.7, iso 0.5 | 118, 130, 132 | KEEP |
| solid, spheres | 0, 0 | 116, 119 | O, G |
| fidelity | trim 0.9; 300 k observed, 200 k mesh samples, seed 0; AABB gate | 152-154 | G |
| selector | lowest fidelity sum on ALL, pre-registered (this file) | 155 | RULE |

- **sigma** = gmg A.2 estimator `gmg/bundle.py _sigma` through `c0b_prep.py sigma OBS POSES water_pitcher
  blue_cup,water_pitcher OUT`, on the extraction frames `range(0, T, 2)`, clamped to [0.5, 3] mm (C0b 3.5). For the
  merged source: the median of the two episodes' sigma.
- **Thickness chain** (C0b 3.3 steps 2-4; `scripts/params_p.py`), used only when lathe_obs measures fewer than 3
  two-wall bins:
  1. gmg `thickness.py` median of the source's two-sided measurements (`c0b_prep.py thick`; merged: pooled), if
     there are at least 200;
  2. else t0_C0b from the C0b box (`results/t0_c0b.json` of store run `mesh-20261031-c0b-00e8584`), if fittable and
     already present when params are written;
  3. else -1, so lathe_obs fails if it needs the fallback (a failed build is no candidate);
  4. clamp to [1.5, 8] mm.
  - Never 3 mm, never thickness.py's 2.5 mm fallback.

## 3. Candidates (exactly six; `scripts/build_p.sh`)

| Label | Points | Variant |
|---|---|---|
| ep21_g1 / ep21_g0 | `pts/B/ep21_water_pitcher.npz` | appendages 1 / `--appendages 0` |
| ep22_g1 / ep22_g0 | `pts/B/ep22_water_pitcher.npz` | same |
| merged_g1 / merged_g0 | `pts/M/merged_water_pitcher.npz` (ep21 + ep22 pass-B points concatenated, `c0b_prep.py merge`, as C0b's merged blue cup) | same |

- Command per candidate: `lathe_obs.py OBS OUT.glb --tie 1.0 --floor base_t --t_fallback T --tmax 0.008 --tmin 0.0015
  --app_d 3sigma [--appendages 0]`. This is C0b's `lathe_args`, the blue-cup family.
- **Merged is safe in one frame:** both episodes are in the same library_v3 pitcher frame along our sweep tracks.
- `hybrid.py` is **not** used. Its second mesh would have to be library_v3 (an S-input, C0b AUDIT 134 / 46) or a
  generated mesh (not GT-free placed). `lathe_obs.py`'s own appendage splat already provides the observed handle and
  spout. No other family or setting is built for the pick.

## 4. The pick (GT-free; C0b PREREG section 5 applied to the pitcher; `scripts/pick_p.py`)

1. **Exclusions:**
   - raw mesh not watertight (trimesh, `process=True`);
   - kit `budget_mesh(path, 4096, 4096)` raises or leaves more than 4096 faces or vertices;
   - no fidelity value;
   - a failed build.
2. **Fidelity:** `obs_fidelity.py OBS_ep21,OBS_ep22 MESH` with defaults, one mesh per process, on the C0b pass-B
   points of both public episodes (set ALL).
3. **Pick:** the lowest `sum_mm`. Ties (equal to 3 decimals) go to fewer raw faces, then to the label in byte order.
4. **Commit before scoring:** the pick goes to `meshes/` (if <= 10 MB, else the HF store), with its sha256 and the
   fidelity table of all candidates. Committed and pushed before `score_p.py` runs.

**Reported only, never deciding:**
- fidelity on each episode alone;
- library_v3's fidelity on the same points;
- the GT-free diagnosis (`scripts/diag_pitcher.py`: coverage, axis, profile ovality, appendage groups);
- the rest check (section 8).

## 5. Scoring [D] (once; `scripts/score_p.py`)

```
cd /home/user/v2d-track3 && MESH_SCR=SCR SCR/venv/bin/python docs/research/mesh-2026-10-26/cdo-sprint/C2/P-pitcher/scripts/score_p.py \
    docs/research/mesh-2026-10-26/cdo-sprint/C2/P-pitcher/meshes/<pick>.glb \
    docs/research/mesh-2026-10-26/cdo-sprint/C2/P-pitcher/results/score_p.jsonl
```

- **One call:** `mesh_metric.evaluate()` on the kit-budgeted mesh and scan. It refuses a sha already in the output.
- **Seeds:**
  - eval seed 20000161 (eval 20, slot 1);
  - extra seeds 11, 22, 33, 44, 55 (the library baseline record's own extras);
  - then 1001-1026, for 32 seeds in total.
- **Baseline** (library_v3 [D], `results/baseline_library.jsonl`): L = 0.8942 cm at 20000161; A = add_med 7.97 mm over
  its 6 seeds (20000161, 11, 22, 33, 44, 55).
- **WIN:** all three must hold:
  - CD-O at 20000161 <= L - 0.02 = **0.8742**;
  - add_med over the same 6 seeds <= A + 2.0 = **9.97 mm**;
  - **0 flips** over all 32 seeds. The kit does not declare the pitcher symmetric, so a flip is any rotation error over
    90 deg.
- **H-P survives** iff WIN and CD-O at 20000161 <= 0.60.
- **Floats:** a value exactly at a threshold passes; seed values are mesh_metric's 4-decimal values.
- **Reported, not gating:** cdo_all, add_med over 32 seeds, ambiguity, ADD max, rot max.

## 6. AUC guard [D] (only if the pick is a WIN; C0's rule and runner)

- **Twins:** public ep21 and ep22. Both have blue_cup (slot 0) and water_pitcher (slot 1), the same objects in the
  same order as eval 20.
  - On eval 20 the kit takes the scene rotation from the first non-symmetric object, which is the pitcher. So this
    swap moves eval 20's rotation anchor.
  - The 26 Oct single-twin pitcher swap cost -0.0045 AUC on Kaggle.
- **Runs:**
  - `base` = C0's library_v3 dir `SCR/cdo_c0/base`;
  - `single` = that dir with `water_pitcher.glb` replaced by the pick, as built (`scripts/check_base_p.py` makes it
    and lists its sha256).
- **Runner:** `scripts/run_auc_guard_p.sh`, a copy of C0's `run_auc_guard.sh` that changes only the mesh dir, the
  output dir (`SCR/cdo_c2/P/auc/runs`) and the object list.
  - Command per run: `pipeline/score_registered.py <e> SCR/cdo_c0/tracks/ep<e>/poses_world_vo.npz --meshes <dir>
    --t3 SCR/cdo_c0/t3 --kit SCR/kit/v2d_submission_kit`.
  - Each run is executed once; a crash may be re-run unchanged.
- **Base reuse:** C0's `runs/base/ep21|22.json` are reused only if `check_base_p.py` passes C0b's checks:
  - base mesh shas;
  - track shas;
  - `score_registered.py` 6a4cd60a0d26e3f8;
  - kit `track3_pose.py` b4b99f698eb4893a;
  - the staged-input list.

  Otherwise both base runs are re-run.
- **Rule** (C0 PREREG section 5, `scripts/guard_eval_p.py`), with dX = X(single) - X(base) on the episode-level
  `perception` entry:
  - **PASS** iff mean dAUC >= -0.005, min dAUC >= -0.02, mean dMPPE <= +0.2 cm and mean dRPE <= +0.2 cm, with both
    twins present.
  - Deltas are compared unrounded.
- **In-sample caveat (stated now):** the candidates are built from these two twins' own points, so the guard is fully
  in-sample, as T1's beige guard was on ep11.

## 7. Adoption

- **ADOPTED** for pack 10 (eval 20, slot 1, replacing the packed library_v3 pitcher) iff WIN (section 5) **and** guard
  PASS (section 6). There is no other selection.
- If not adopted, library_v3 stays.
- **Joint test with the blue cup:** if C0b's blue cup is also adopted for pack 10, eval 20 would have both swapped.
  ep21 / ep22 then need a joint run (both swapped) before packing. This is reported here as a requirement; this track
  does not run it unless both are adopted.

## 8. Reported only (GT-free [M]; decides nothing)

- **Rest check** (`scripts/rest_check.py`): the pitcher's observed resting poses on ep21 / ep22, from our track and
  our depth's frame-0 table plane, using pipeline/support_fill.py's statics.
  - Statics: COM inside the support polygon, margin >= 3 mm, tip >= 3 deg, quasi-static rocking <= 3 deg.
  - COM = the mesh's volume centroid.
  - Applied to the pick, all candidates and library_v3. library_v3 is already measured: UNSTABLE at all 8 ep21 rest
    candidates, contact 1.0 x 0.4 cm, 2-9 mm into the table, which reproduces the 25 Oct finding.
  - The pack swaps only the scored mesh. The simulator copy (with its 25 Oct arc foot) is unchanged, so this is
    information for a later simulator decision.
- **Diagnosis** (`scripts/diag_pitcher.py`, before the builds where possible): which episode sees more, the axis and
  its consistency, ovality per height, and the appendage groups (spout, handle) with their extents.
- **Reproducibility:** the sha256 of our pass-B files against the C0b box's files for the same episodes, if its run
  pushes them.

## 9. Order, machine, cost

1. obs points (local);
2. diagnosis;
3. **this PREREG committed and pushed**;
4. sigma / thickness / params;
5. builds;
6. pick and commit;
7. one scoring;
8. AUC guard if WIN;
9. rest check;
10. RESULTS.

Everything runs on the shared local VM (4 cores, loaded; nice 5), CPU only, **$0**. No Vast box is planned. A box
(one, self-destroying, cap $4) would only be considered if the local obs or guard runs could not finish, and only after
a new ledger line and a dated NOTES entry.

## 10. Integrity

- Construction and choice read only our tracks, hands, depth, calibration and our own outputs.
- Ground truth is read only by `score_p.py` (once, public scan via mesh_metric) and, if WIN, by
  `score_registered.py` (ep21, ep22: mocap and public scans).
- library_v3 is read only for the reported-only fidelity and rest rows, and as the guard's base dir.
- Author's context, disclosed:
  - the brief quoted library_v3's [D] scores (0.894, 7.97 mm) and the generator range (0.38-0.77);
  - `ledger-of-past-mesh-work.md` quotes scan-scored numbers for the pitcher (wall 2.2 mm, extents). None of these
    enters a setting: every setting is a C0b value or a measured own-observation statistic.

## A1. Amendment (2026-10-31, 18:34-18:38 UTC, commit 07d2536 at 18:38; times corrected 18:40 from guessed values; before any candidate is built, smoke-tested or scored)

**What was seen [M].** A preview of `scripts/diag_pitcher.py` was run on the older `SCR/obs_all` pitcher points
(library_v3 ROI and carving). Those points are not used for any build; the C0b points were still being made.
- `lathe_obs.fit_axis` chooses a direction about 87 deg from the pitcher's resting up, roughly the object-frame x axis:
  ep21 (0.994, 0.091, 0.057), ep22 (0.995, 0.063, 0.077). Its rotational consistency is 9.2 / 9.0 mm.
- Only 17-24 % of the 24 sectors are seen per height bin.
- 66-77 % of the points lie outside that lathe.

A lathe about a near-horizontal axis cannot be the body H-P describes, whose axis is the vertical axis the can stands
on.

**GT-free axis prior.** A vessel stands on its base, so its body axis is the support normal at rest.
`scripts/rest_axis.py` measures that normal from our own data:
- inputs: our sweep track, our depth's frame-0 table plane (`table_plane_ep.py`), and support_fill's still windows,
  kept when the origin is within 10 mm of its lowest height;
- statistic: the mean of R_obj^T n over those frames.

| Source | axis_dir (object frame) | frames | spread max / median |
|---|---|---|---|
| ep21 | (0.0315, 0.6279, 0.7777) | 8 | 2.20 / 0.84 deg |
| ep22 | (0.0454, 0.6132, 0.7886) | 9 | 0.54 / 0.36 deg |
| merged | (0.0389, 0.6201, 0.7835) | 17 | 2.06 / 0.91 deg |

`REST_DH` = 10 mm (2.5 vote voxels) and support_fill's 3 mm / 2 deg / 10-frame still windows are its own constants
(support_fill, 23-25 Oct; not scan-derived). All rest candidates passed the 10 mm test in both episodes.

**Change.** Six candidates are added, so there are 12 in all.
- Each of the six in section 3 is rebuilt with the axis direction fixed to its source's rest-up (`ep21r_g1`,
  `ep21r_g0`, `ep22r_*`, `mergedr_*`).
- `scripts/lathe_axis.py` runs lathe_obs.py unchanged, except that `fit_axis` evaluates only that direction:
  - placement by `lathe_obs._place` (line-complex least squares with the direction fixed);
  - centre at the points' mean height;
  - rotational consistency reported.
- All other arguments are identical: the C0b lathe_args, sigma and t_fallback.
- The shared `lathe_obs.py` is not edited.

**Unchanged:**
- the pick rule (section 4, now over 12 candidates, lowest obs_fidelity sum on ALL);
- one scoring;
- the gates, guard and adoption rule;
- H-P's falsification test, which applies to whichever candidate is picked.

**Reason this is not tuning.** No candidate has been built and nothing has been scored. The prior is a physical
statement measured on our own observations. The original six candidates stay in the pool. The pick is still made by
the pre-registered GT-free rule.
