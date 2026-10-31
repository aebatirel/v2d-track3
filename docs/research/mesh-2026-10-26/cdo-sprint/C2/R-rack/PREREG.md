# C2 track R (plastic_dish_rack): pre-registration

Written 2026-10-31, 18:40-19:10 UTC, before any C2/R candidate is built and before any scoring. Step log: `NOTES.md`.

**What was read to write this file.** No scan, mocap, parquet pose or `*_align` file, and no CD-O or ADD record other
than the four baseline numbers quoted in section 6 (library_v3 and C0 rack records, already in the C0 / C0b documents).
Read: C0 README / PREREG / verify_0, C0b AUDIT / PREREG / REPLACEMENTS / DEVIATIONS_PUBLIC / NOTES, `prim_rack.py`,
`obs_fidelity.py`, `mesh_metric.py` (header), the kit's CD-O definition, C0's guard runner and verdict script.
New GT-free diagnostics (section 2) used only our observed points (`SCR/obs_all`) and the C0 rack mesh / build record.

Labels: [M] measured without ground truth; [D] diagnostic scored against public ground truth; [E] estimate;
[H] hypothesis. Repo paths are relative to `docs/research/mesh-2026-10-26/` unless they start with `docs/` or
`pipeline/`. `SCR` = `/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad`.

## 1. Question and hypothesis

- **Object.** plastic_dish_rack: 5 eval pairs (eval 14, 15, 16, 28, 30); public episodes 12, 13, 26, 27, 31.
  Shipped now (pack 9a): the C0 prim rack `results/prim/meshes/plastic_dish_rack_joint_v2.glb`, CD-O 0.45604 cm,
  ADD med 5.63 mm, flips 0/7 [D]; library_v3 0.55506 cm, ADD med 5.79 mm [D].
- **H-R [H].** The C0 prim rack misses structure that our observations show. Adding parts (or part degrees of freedom)
  supported by our points lowers CD-O to <= 0.40 cm. **Falsified** if the picked mesh is not <= 0.436 cm
  (C0 - 0.02), or if the AUC guard fails. It is also falsified GT-free (no scoring) if no candidate with a new part
  explains our points better than the same build without it (section 5).

## 2. GT-free diagnosis (done before this file; scripts in `scripts/`, outputs `SCR/cdo_c2r/diag/`)

Inputs: `SCR/obs_all/ep{12,13,27,26,31}_plastic_dish_rack.npz` (C0's observed points; built with the library_v3 ROI
and library_v3 co-object carving, AUDIT ids 133 / 134, S-input; used here for diagnosis only, never for a build or a
pick) and the C0 rack mesh with its build record (`SCR/prim/clean/rack/t2.5_lean1/plastic_dish_rack/joint.json`, frame
only).

| Script | What it measures [M] |
|---|---|
| `resid_diag.py` | distance of every observed point (1.5 mm voxels) to the mesh, side, 4 mm-voxel clusters of points > 6 mm out, per episode |
| `free_diag.py` | for mesh surface samples: the obs_points vote grid (hits / free per 4 mm voxel): seen, seen-empty (free >= 3, hits 0), unseen |
| `vis_diag.py` | shadow test: is the segment from a residual point to the camera that saw it blocked by the mesh solid (then the point is a depth-edge / smear sample or the mesh is wrong there) |
| `rmap.py` | raster maps (top, front, side) |

Findings [M]:
1. **Overall the C0 mesh explains the points near the noise level:** obs->mesh trimmed mean 2.49 mm. Residual share
   by region: cup holder 27 %, pegs / basin 26 %, back wall 23.5 %, front wall 17 %, right end 4 %.
2. **The largest outside cluster is not structure:** 11,233 points 7-14 mm behind the back wall (y 71-78 mm,
   h 4-20 mm, all 5 episodes) are in the mesh's own shadow (camera elevation ~53-59 deg; the strip is the depth-edge
   smear behind the back lip). Same for 3,919 points behind the cup holder's back wall.
3. **Pegs are not round [M].**
   - free-space: the C0 round pegs' +-x sides lie in seen-empty voxels in >= 3 of 5 episodes for 7-57 % (most
     17-37 %) of their samples at h 10-40 mm; their +-y faces for 0-8 %.
   - directly seen front faces sit 12.6 / 11.2 / 9.4 / 7.0 mm in front of the fitted centre at h 4-10 / 16-22 / 22-28
     / 28-34 mm, while the x half-width of the same points is 8.4 / 6.4 / 6.1 / 5.7 mm (front row, medians over pegs).
   - so the section is deeper along y than wide along x (aspect > 1); the round prior (PEG_KAPPA = 1) forces a
     compromise radius that is too wide in x.
   - The y extent behind the peg centre also contains depth-edge smear along the viewing rays (shadow region), so
     the back half is not direct evidence.
4. **The right end's inner face is sloped [M]:** in the x-h section (y -40..40 mm) it runs from x ~257 mm at
   h ~0 to x ~268 mm at h ~28 mm (seen head-on by the camera; red residuals up to ~15 mm in the basin at the
   bottom). The single outline draft s1 converged to its bound 0 in 4 of 5 episodes and the joint (ep31: 0.24): the
   long back wall's inner face (seen at a grazing angle, smeared into the wall) dominates s1.
5. **Cup holder:** visible residual clusters at its back-left interior (7,435 points, 5 episodes), its front (4,745,
   5 episodes) and its tray-side face at low h (2,571, 5 episodes, x ~ -117 mm vs face -125 mm); per side, the
   residual changes with height (left wall median -1.6 / -2.6 mm at h 0-20 mm, +0.2..+0.9 mm above 30 mm; tray-side
   face outside by up to ~8 mm at h < 35 mm). A tube whose half extents are linear in h cannot follow this.
6. **Not found:** no visible, multi-episode cluster at the right end other than one compact bump (x ~285,
   y ~-32 mm; C0 has a 5.2 mm ball there); no front-wall foot (front outer face median -67 mm vs model -66 mm at
   h 0-8 mm; the P2 tail is noise); the tray floor is unseen (86 % of the model floor area has no vote). The C0
   README's "right-end ribs" and "tray floor" items have no support in our points beyond item 4, and marker stems
   are C0b's `markers.attach` stem rule.

## 3. Candidate parts (options of `scripts/prim_rack.py`; unset = byte-identical old behaviour)

| Option | Part / degree of freedom | Evidence (section 2) | New constants and their origin |
|---|---|---|---|
| `--end_draft` (E) | the right end's inner face gets its own draft s1e: inset s_e(h) = s0 + s1e (H_r - h) at the right end, s(h) elsewhere; one more outline LSQ parameter; the basin is the hull of the per-side inset outlines | item 4 | bounds [0, 1.5] and init 0.3 = the existing s1 bounds and init (AUDIT ids 84, 87: KEEP in C0b, "s1 >= 0 kept, moulding draft") |
| `--peg_kappa_free` (K) | per peg row the section aspect kappa (b = kappa a) is an LSQ parameter instead of the fixed 1 | item 3 | bounds [0.5, 3.0]: new generic search bounds (aspect 1:2 to 3:1), no prior value, not derived from any scan figure; init 1.0 = PEG_KAPPA (AUDIT id 69, KEEP) |
| `--cup_quad` (Q) | cup-holder half extents ex(h), ey(h) get a quadratic term gx h^2, gy h^2; tube and cavity become unions of 8 stacked frusta | item 5 | bound |g| <= 2.5 /m = the existing lean / draft bound 0.25 (AUDIT id 89, KEEP) spread over 0.1 m, the order of our own cup-top height (C0: 105 mm [M]); init 0; 8 frusta = tessellation (generic) |

- **Disclosed contamination risk.** The project's documents record that a scan-informed brief once described the
  rack's pegs as "fins ~2.5 mm" (C0b AUDIT section 3). Option K was motivated by finding 3 [M]; it fits kappa freely
  within generic bounds and carries no thickness or aspect value from that brief.
- **Everything else is C0b's scan-free build** (C0b PREREG 3.2-3.4 and REPLACEMENTS.json): wall / floor T from the C0b
  thickness chain (id 62, TH), `--s0_min_t` (id 87, TH), gmg markers with `attach` (ids 71-73, 99, 101: MK), the C0b
  observed points (cube ROI, own co-object points: ids 133, 134: LIB), `PRIM_CUP_LEAN=1` (id 76 O; id 77 NEVER),
  JOINT_TOL 1.25 (id 78, KEEP), and every other prim_rack value as KEEP in REPLACEMENTS.
- **Regression (before any build):** with no new option, the modified script gives byte-identical output to the
  unmodified one (`prim_rack.py joint` on the C0 inputs, C0 settings, same thread count). If it differs, nothing is
  built until it is fixed. **Done, passed [M]** (18:46 UTC): joint_joint.glb md5 8fdf2444 and joint_joint_nomk.glb
  md5 5bfa2509 from both scripts; joint.json identical apart from its output path (`SCR/cdo_c2r/regress`).
- **Smoke test (dev, outputs discarded, disclosed):** all three options together on the dev `obs_all` points 12/13/27
  (T 5 mm, no markers) ran and gave a watertight mesh (3212 faces). Fitted there: s1e 0.122, kappa 1.42 / 1.58, cup
  gx +0.48 /m, gy -1.07 /m. The predictions in section 9 were written before this result and are not changed.

## 4. Inputs and builds

- **Inputs** (C0b public box run `mesh-20261031-c0b-00e8584`, HF store `runs/<run>/results/c0b/`, sha256 recorded on
  staging; never a scan, mocap, parquet pose, `*_align` file or library_v3 mesh):
  - C0b pass-B observed points `pts/B/ep{12,13,26,27,31}_plastic_dish_rack.npz`;
  - `params.json` target `rack/run`: `t_wall_m` (the C0b T);
  - `markers/ep{12,13,26,27,31}.json` (gmg balls, frozen settings sha256 `488ac3b6...`);
  - the kit (`inputs/kit`) for the budget check.
  - If C0b's rack inputs are missing or its T is not fittable, this track builds nothing and reports it.
- **Builds:** 8 runs of C0b's rack command, one per option set S in {base, E, K, Q, EK, EQ, KQ, EKQ}:
  ```
  PRIM_CUP_LEAN=1 python prim_rack.py run --obs_dir pts/B --out cand/<S> --episodes 12,13,26,27,31 \
      --t_wall <T> --s0_min_t --markers_dir markers [--end_draft] [--peg_kappa_free] [--cup_quad]
  ```
  Each run gives C0b's 12-mesh family (per episode `full`, `nomk`; `joint`, `joint_nomk` of the episodes within
  JOINT_TOL), so 96 meshes. Every run is executed once; a crash is re-run unchanged; a failed run is recorded and
  gives no candidate.
- **Machine:** one self-destroying Vast CPU box (>= 32 cores, >= 64 GB RAM, `SETUP=none`, C0b's pinned venv
  `c0b_setup.sh`), stall watchdog 30 min, cap $4, ledger session `mesh-bold` (planned / actual). Estimate ~1 h,
  ~$0.5 [E]. If no box is available, the same commands run locally at nice 10.

## 5. The pick (GT-free)

1. **Exclusions** (C0b's `c0b_check.py`): raw mesh not watertight (trimesh, process=True); kit
   `budget_mesh(path, 4096, 4096)` raises or leaves more than 4096 faces or vertices; no fidelity value.
2. **Fidelity:** `obs_fidelity.py OBS_12,...,OBS_31 MESH` (defaults: trim 0.9, 300 k observed points, 200 k mesh
   samples, seed 0, no ICP; one mesh per process) on the C0b pass-B points of all 5 episodes. This is C0's and C0b's
   formula.
3. **Pick:** the lowest `sum_mm` over all eligible meshes of the 8 runs, base included. Ties (equal at the printed 3
   decimals) go to fewer raw faces, then to the label in byte order.
4. **Gate:** if the pick comes from the base run, no new part explains our points better: **H-R is falsified
   GT-free**, nothing is scored and no guard runs. Otherwise the pick is the **C2/R rack**. Before any scoring it is
   committed to `C2/R-rack/meshes/` (<= 10 MB) with its sha256, the fidelity table of all 96 meshes, and the fitted
   option values.

Reported only, never deciding: per-episode fidelity, the base run's own pick, C0's mesh and C0b's rack pick on the
same points, each run's internal selection, the fitted s1e / kappa / gx, gy.

## 6. Scoring [D] (once)

- **One** `mesh_metric.py run` of the pick, default seeds (the rack's 5 eval seeds plus extra seeds to >= 6),
  results to `C2/R-rack/results/score.jsonl`. Not run if the pick's sha1[:16] already has a record in
  `results/**/*.jsonl` or `cdo-sprint/**/*.jsonl` (then that record is used).
- **WIN** iff all hold (floats as written, 4 decimals; a value exactly at a threshold passes):
  - `cdo_eval` <= 0.45604 - 0.02 = **0.43604** (C0 baseline, record `clean/rack/t2.5_lean1/all_joint`);
  - `add_med` <= 5.79 + 2.0 = **7.79 mm** (library_v3, `results/baseline_library.jsonl`);
  - `flips_all` = 0 (the rack is not kit-symmetric).
- Also reported: cdo_all, ADD eval / max, ambiguity, the difference to C0 and to C0b's rack pick (if C0b has scored
  it), and whether H-R's strong claim (<= 0.40) holds.

## 7. AUC guard [D] (C0's rule and runner)

- **Rule** (C0 PREREG section 5, frozen): over the twins 12, 13, 26, 27, 31, single swap minus base library_v3:
  mean dAUC >= -0.005, min dAUC >= -0.02, mean dMPPE <= +0.2 cm, mean dRPE <= +0.2 cm (`perception` entry;
  4-decimal inputs, deltas unrounded, 1e-9 tolerance; missing data fails).
- **Runs:** 5 `score_registered.py` runs, `single/plastic_dish_rack` = C0's `SCR/cdo_c0/base` (library_v3) with the
  rack replaced by the pick as built; `scripts/run_auc_guard_c2r.sh` is C0's runner with only the mesh dir, output
  dir (`SCR/cdo_c2r/runs`) and object list changed; `scripts/guard_eval_c2r.py` is C0's verdict for the rack only.
- **Base runs** reused from `SCR/cdo_c0/runs/base/ep<e>.json` only if C0b's reuse conditions hold (base mesh sha256,
  track sha256, `score_registered.py` 6a4cd60a0d26e3f8, kit `track3_pose.py` b4b99f698eb4893a, staged inputs);
  otherwise the 5 base runs are re-run unchanged.
- The guard runs for the pick whether or not it is a WIN (reported); a crash may be re-run unchanged.

## 8. Adoption

- **Adopted** iff WIN (section 6) **and** guard PASS (section 7). No other selection.
- An adopted mesh is a public-built candidate for the rack's 5 eval pairs, offered to the orchestrator for pack 10
  next to C0b's / E0b's rack; this file does not decide between them.

## 9. Predictions and known limits

- **[H] Fitted values:** E: s1e >= 0.2 on the joint (falsified if < 0.1); K: kappa > 1.2 on both rows (falsified if
  <= 1.0 on either); Q: |gx| or |gy| > 0.5 /m. Reported only.
- **[H] Fidelity:** the pick improves `sum_mm` over the base run's pick by >= 0.05 mm. Reported only.
- **[H] CD-O:** pick <= 0.40 cm (H-R); falsified above 0.436 cm.
- **Limits:**
  - fidelity is not CD-O (across rack episodes it did not track CD-O; C0b PREREG 12);
  - the y depth of a peg behind its centre is not observed (shadow); kappa trades the seen front face against smear;
  - the diagnosis used points with the library_v3 ROI / carving (S-input); builds and the pick do not;
  - every candidate is built on its own AUC twins (in-sample);
  - the C0b T (expected ~5 mm, t0_C0b) differs from C0's 2.5 mm, so a C2/R vs C0 difference mixes the C0b
    replacements and the new parts; the base run separates them on fidelity, and C0b's own rack score (if any)
    separates them on CD-O.

## 10. Integrity

- Construction and every choice in sections 3-5 read no scan, mocap, parquet pose, `*_align` file or library_v3
  mesh. Scans and mocap are read only by `mesh_metric.py` (section 6) and `score_registered.py` (section 7), after
  the pick is committed and pushed.
- One scoring. No option, bound, candidate set, threshold or twin set changes after this commit. Failures are
  reported, not retried with changed settings. Deviations found in implementation go to `RESULTS.md` before scoring.

## 11. Amendment A1 (2026-10-31 ~19:55 UTC; before any C2/R candidate output was seen, before any scoring)

**Why [M].** C0b's public run finished at 19:33 UTC. Its own rack candidates (C0b `cand/rack/candidates.jsonl`,
GT-free) show that the C0b observed points break `prim_rack.py`: cup-holder tops of 82-320 mm (C0: 105 mm), lip
heights up to 47.9 mm, 0-8 pegs instead of 13, 39-76 gmg balls per build, and obs_fidelity sums of 33-115 mm (C0's
mesh on the obs_all points: ~6 mm). Measured here on the five C0b pass-B rack files (our points only; the box is the
C0 rack frame, a diagnostic): 1.7 / 0.8 / 21.3 / 36.9 / 19.3 % of the voxel-downsampled points of episodes
12 / 13 / 26 / 27 / 31 lie outside a rack-sized box, mostly 150-400 mm in front of the rack. This is the static clutter
that C0b PREREG 3.4 named as a risk of the +-0.30 m cube ROI. With > 10 % clutter in the fidelity set, the trimmed
fidelity measures clutter, not the rack, so the section 5 pick would not test H-R.

**Change (inputs only).** Every C0b pass-B rack file is cleaned by `scripts/clean_pts.py` before the builds and the
fidelity: points linked within 12 mm (obs_points `other_r`, AUDIT id 135, KEEP) on 4 mm voxels (the obs_points vote
voxel, AUDIT id 142, A6) form connected components; keep the largest component and every component whose centroid lies
inside its convex hull (rack parts that the removed table band disconnects, such as pegs on the unseen floor); drop the
rest. Nothing else changes: options, candidate family, T, markers (C0b's per-episode gmg balls, unchanged), exclusions,
fidelity formula, pick, gate, scoring, guard and adoption are sections 3-8 as written.
- Measured effect of the rule [M]: kept 98.8 / 99.6 / 63.8 / 51.0 / 65.4 % of the points of 12 / 13 / 26 / 27 / 31;
  afterwards >= 99.96 % of the kept points of 12, 13, 27, 31 and 88.0 % of ep26 lie in the rack-sized box (ep26
  keeps an attached cluster ~136 mm high above the cup holder).
- **Runs.** The box started at 19:35 UTC (`mesh-20261031-c2r-18e63eb`, uncleaned inputs) is reported only; nothing is
  picked from it. The section 4 runs are repeated on the cleaned points, locally at nice 10 (`c2r_build.sh` with the
  cleaned input dir; one box per track is already used). Its `selection.json` is the section 5 pick.
- **Reported only:** C0b's own rack pick (ep13 full, fidelity 33.32 mm on uncleaned points) is not comparable on
  fidelity; the C0 mesh and the C0b base run are reported on the cleaned points.
