# C2 / Track P (water_pitcher): results

**Status (2026-10-31, ~20:30 UTC).** Done. CPU only, **$0**: no Vast box was rented and nothing was added to the
ledger.
- **Verdict:** H-P is **falsified**. The pick is **not a WIN**, so the AUC guard was not run (PREREG section 6), and
  the pick is **NOT ADOPTED**. library_v3 stays on eval 20.
- Pre-registration: `PREREG.md` (commit 5982c31, amendments A1 07d2536 and A2 cc63fc2 / 1230b6d), all pushed before
  the one scoring. Step log: `NOTES.md`.

Tags: [M] measured without ground truth; [D] diagnostic, scored once against the public scan; [E] estimate; [H]
hypothesis. `SCR` = `/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad`.

## 1. Answer

| | library_v3 [D] | C2/P pick [D] | WIN threshold |
|---|---|---|---|
| CD-O, eval 20 seed 20000161 (cm) | 0.8942 | **1.1600** | <= 0.8742 |
| add_med, 6 seeds (mm) | 7.97 | **11.165** | <= 9.97 |
| flips, 32 seeds | 0 / 6 | 0 / 32 | 0 |
| cdo_all, 32 seeds (cm) | 0.889 (6 seeds) | 1.155 (sd 0.012) | |
| add_max (mm); rot_max (deg) | 8.52; 2.77 | 13.49; 3.55 | |
| self-ambiguity amb (mm) | 14.25 | 12.26 | |

- **The scored pick:** `meshes/ep22_water_pitcher_g1_a2.glb`.
  - sha256 `fadf3e7b7c5104b2c68799a3d9da6af42a881624caea7f405d8529010ec6d1f6`; mesh_metric sha1[:16] `478b9fb3cc65c841`.
  - 145,164 faces, 2 bodies.
  - Built by lathe_obs on ep22 with appendages, after the A2 connectivity filter.
- **Record:** `results/score_p.jsonl`, `results/score_p.log` (958 s).
- **The gates:** CD-O fails (+0.27 cm against library), ADD fails (+3.2 mm), flips pass.
- **H-P** needed CD-O <= 0.60 and a WIN. Neither holds.
- **Board effect:** none. Eval 20 keeps library_v3, so pack 9a+'s 0.33234 is unchanged by this track. Had the pick
  shipped, the board would have moved by (1.160 - 0.894) / 36 = +0.0074 [E].

## 2. GT-free diagnosis (before the builds) [M]

- **The object is not near-axial.** Our own ep22 RGB crop (`SCR/crops/ep22/water_pitcher_k174.png`) shows an
  elephant-shaped watering can:
  - a narrow oval base;
  - a long up-swept spout;
  - a handle loop whose lower end nearly reaches the table;
  - a slanted open top.
- **One-sided views.** On our tracks the camera covers only 90 deg (ep21) and 60 deg (ep22) of azimuth around the
  body, at 34-59 deg elevation (`results/diag_c0b.json`).
  - ep21 covers more azimuth.
  - ep22 has more outer-wall points (48k against 30k) and more two-wall bins (6 against 1).
  - Neither sees the far side.
- **lathe_obs's own axis is near-horizontal.** It is about the object-frame x axis, 87-89 deg from the resting up.
  - Rotational consistency is 9.15 mm (ep21) and 12.29 mm (ep22); the two episodes' axes differ by 20 deg.
  - 80-85 % of the points lie more than 3 sigma (5.2 mm) outside that lathe, in one 412 x 264 x 140 mm group: spout,
    body and handle together.
- **The resting up is very stable** (`rest_axis.py`, our track plus our depth's table plane).
  - It is (0.039, 0.620, 0.784) in the object frame, i.e. about 38 deg from the frame's z axis, the same 38 deg as on
    25 Oct.
  - The spread is <= 2.2 deg over 17 rest frames. ep21 and ep22 differ by about 1 deg.
  - A lathe about this axis is less rotationally consistent (10.4-13.2 mm), but its base stands (section 4).
- **The 0.30 m C0b cube admitted clutter.** ep22's points hold a 7,896-point cluster 32-37 cm from the axis, and ep21
  a 365-point one. lathe_obs splatted the ep22 cluster into an 82 cm2 piece in four g1 candidates (amendment A2).
- **Reproducibility.** Our own pass-A build of the ep21 pitcher (`scripts/obs_c0b.sh`) is array-identical to the C0b
  box's file (store run `mesh-20261031-c0b-00e8584`): pts, cam, frame, vote grids. Only the path strings differ.
  The box's pass-B files for ep21 and ep22 were used, with input shas equal to ours.

## 3. Candidates and the GT-free pick (`results/pick_A1.json`, `results/pick_A2.json`)

Lathe arguments are C0b's: `--tie 1.0 --floor base_t --tmax 0.008 --tmin 0.0015`.
- `--app_d` = 3 sigma = 5.20-5.22 mm (gmg A.2 sigma 1.73-1.74 mm).
- `--t_fallback`: thickness.py, 5.99 mm (n = 877) for ep21 and merged; -1 for ep22 (n = 1, t0_C0b absent when the
  params were written).
- The ep22 builds measured their own wall (6 and 35 two-wall bins), so the -1 never bound.

| Candidate | Axis | Faces | Watertight | Fidelity sum on ALL, mm (A2) |
|---|---|---|---|---|
| **ep22_g1** | lathe_obs | 145,164 | yes | **6.732** (A1, with the clutter piece: 6.624) |
| ep21_g1 | lathe_obs | 156,572 | yes | 7.448 |
| merged_g1 | lathe_obs | 162,310 | **no** (excluded) | 8.095 |
| ep21r_g1 | rest-up (A1) | 114,276 | **no** (excluded) | 8.640 |
| ep22r_g1 | rest-up | 104,022 | yes | 9.050 |
| mergedr_g1 | rest-up | 119,406 | yes | 9.417 |
| ep21r_g0 / ep22r_g0 / mergedr_g0 | rest-up | 29-31 k | yes | 14.658 / 16.757 / 15.414 |
| ep22_g0 / merged_g0 / ep21_g0 | lathe_obs | 17 k | yes | 37.675 / 41.548 / 47.416 |
| library_v3 (reported only) | | 31,832 | yes | 6.166 |

- **Per-episode fidelity** (reported only): `results/fid_report.json`.
- **A2's change:** the connectivity filter dropped the same far piece (82-85 cm2 at (231, 227, -181) mm) from ep22_g1,
  ep22r_g1, merged_g1 and mergedr_g1. It did not change the ranking.

## 4. Rest (simulator) [M] (`results/rest_*.json`)

Method: support_fill.py's statics at every observed resting frame of ep21 (8) and ep22 (9), using our track and our
depth's table plane.

| Mesh | ep21 | ep22 | Contact patch | Notes |
|---|---|---|---|---|
| library_v3 | UNSTABLE at all 8 | UNSTABLE at all 9 | 1.0 x 0.4 cm, mesh 2-11 mm into the table | the 25 Oct finding, reproduced GT-free |
| **pick (ep22_g1_a2)** | UNSTABLE at all 8 | UNSTABLE at all 9 | 1.6 x 0.4-0.6 cm | lathe axis 87-89 deg from up; the splat's faces are inverted (signed volume -754 cm3), so trimesh's COM is unreliable |
| ep22r_g0 (rest-up lathe, not picked) | UNSTABLE at 7 of 8 | **STANDS** at all 9 | about 10 x 10 cm, margin about 50 mm | axis 0.2-2.7 deg from up |
| mergedr_g0 (not picked) | UNSTABLE at 5 of 8 | **STANDS** at all 9 | about 9 x 9.6 cm | |

- **The simulator is unaffected by any pack swap.** The pack swaps only the scored mesh. Eval 20's simulator copy is
  still library_v3 with the 25 Oct arc foot (8 convex sectors, r 3.44 cm, margin 23.1 mm at rest f152). The ep21 twin
  with the arc foot gave pitcher AUC 0.414 -> 0.591 (25 Oct, [D]).
- **Unchanged:** library_v3 does not stand by itself; the foot is what holds the pitcher up.
- **A possible later simulator option [H]:** a rest-up lathe body, which stands on our own base geometry. It was not
  tested in simulation here.

## 5. Why H-P failed (interpretation, labelled)

- **[M] The shape is outside the lathe family.** No axis makes the body a solid of revolution: rotational consistency
  is >= 9 mm on every axis tried. The "observed appendages" are most of the object.
- **[H] The fidelity selector favours one-sided splats.** `obs_fidelity` rewards meshes that hug the observed surface
  (obs -> mesh) and checks extra surface only inside the observed bounding box (mesh -> obs). So it prefers a splat of
  the seen side over a closed body. With 60-90 deg views, the splat is an open, one-sided sheet.
  - In the kit CD-O, the missing far side changes the surface centroid and radius (scale normalisation) and adds
    chamfer error.
  - ADD grows by about 3 mm, because the registration of a half-shell drifts.
  - The same bias was noted for the generator placements in C1/T2 ("biased, 17/20 meshes").
  - Falsifier: a pre-registered, closed, mirror-completed candidate (below) scoring a lower CD-O than an equally
    faithful one-sided splat.
- **[M] The lathe body is not the useful part.** The g0 lathe bodies alone explain the points poorly (14.7-47.4 mm).

## 6. Next step (proposal only; not run)

**H-P2 [H].** The can is bilaterally symmetric: the spout-handle plane is its plane of symmetry, as our own crop
shows.
- Method: mirror-complete the observed surface across a plane fitted to our points (gmg `structure.py` mirror
  hypothesis), then close it as a thin shell with walls from thickness.py (5.99 mm measured on ep21).
- This addresses the one-sided view directly.
- Falsified unless it is a WIN against 0.8742 / 9.97 mm / 0 flips, by one scoring of a candidate picked by a
  pre-registered GT-free rule that is not fidelity-only (fidelity plus a closure / visibility term), and passes the
  AUC guard on ep21 and ep22.
- Weight: 1 pair of 36, so at most -0.01 board [E] even for a large gain.
- Lower priority than the rack (5 pairs, 0.456).

## 7. Failures and incidents (all in `NOTES.md`)

- **Local obs build too slow.** The local C0b pass-A / pass-B build ran at about 25 % CPU per process under load 15-30,
  about 33 min for one ep21 file. ep22 was stopped, then ep21, and the C0b box's identical files were used.
- **Disk full.** Free disk fell to 159 MB (other writers plus my depth files). Both depth files were deleted. ep22 had
  been fetched by streaming the whole file through sha256 and storing only the even frames (sparse file;
  `SCR/cdo_c2/P/dl_depth_sparse.py`).
- **Clutter in the A1 pick.** The A1 pick carried a clutter piece. A2 (post hoc, GT-free, before scoring) removed it
  and disclosed it.
- **A2 commit text.** The A2 commit cc63fc2 had four backticked names emptied by an unquoted heredoc. They were
  restored in 1230b6d; the rule did not change.
- **Guessed times.** Times written into PREREG were guessed (~18:50); they were corrected to the commit times.

## 8. Files

- **Repository, this folder:**
  - `PREREG.md`, `NOTES.md`, `RESULTS.md`;
  - `meshes/` (the pick, its `.lathe.json` and `.keep.json`);
  - `results/`: score, picks, fidelity report, params, diag, rest axes, table planes, rest checks, build logs;
  - `scripts/`: obs_c0b.sh, diag_pitcher.py, table_plane_ep.py, rest_axis.py, rest_check.py, rest_all.sh,
    lathe_axis.py, keep_connected.py, build_p.sh, params_p.py, pick_p.py, score_p.py, and the guard runner
    (run_auc_guard_p.sh, check_base_p.py, guard_eval_p.py, unused).
- **Scratch (bulk, not in git):** `SCR/cdo_c2/P/`:
  - `box/` (C0b pass-B points);
  - `cand/`, `cand_a2/` (12 candidates each);
  - `pts/M` (merged points), `sigma/`, `thick/`, `diag/`, `logs/`.
