# PUBOWN box run: one own-video mesh per public (episode, object) pair

Run id `mesh-20261031-pubown-ed7171c`, code commit `ed7171caf6c87b792e1da9d8c38e560a18855475`. The builders ran from a
code tree extracted at C0b's box commit `00e858434419...` (`jobs/pubown_freeze.sh`; tree hashes equal to the staged
plan, checked on the box). Job `bash docs/research/mesh-2026-10-26/cdo-sprint/PUBOWN/jobs/pubown_box.sh`. Plan:
`PLAN.md`. Step log: `NOTES.md`. Per-pair index: `MANIFEST.json`.

Labels: [M] measured, [E] estimate, [H] hypothesis. Public development only. No scan, mocap, parquet pose, `*_align`
file or scan-derived constant went to the box. **Nothing here is scored against ground truth.** The perception
re-track test (perc2 with these meshes as templates, scored against mocap by focused-pascal) is the out-of-sample check.

## Result in one line

**PUBOWN-DONE rc=0 [M].** All 22 pairs ran: 20 got a PUBOWN mesh, and the 2 lids keep library_v3 (0 of 16 lid builds,
the same failure as C0b's). The box lived about 21 min, the job took 17 min, and it cost about **$0.15** [E]. The prep
estimate was 25-40 min and $0.2-0.4.

**But the GT-free frame check below finds 7 of the 20 picks broken [M]:**
- all 5 racks (metre-scale extents on ep12, 26 and 31);
- blue cup g1 on ep12, 13, 21 and 22 (stray "appendage" bodies up to 286 mm from the cup);
- pot ep27 (main body 526 mm tall against library_v3's 362).

The PUBOWN rule (C0b section 5) has no frame gate, so it still picked them. `MANIFEST.json` therefore carries a second,
report-only set per pair, `alt_e0_gated`: E0's pre-registered frame gate applied first, then the same pick rule.

## Box

| | |
|---|---|
| Offer | 36762812: Thailand, AMD EPYC 7713, 64 of 64 cores effective, 71 GB RAM (70 GB seen), 596 Mbps down, reliability 0.998, RTX 4090 (unused), $0.410/h, download $2.67/TB |
| Why | Custom Vast bundles query: verified, on-demand, >= 64 effective cores, >= 64 GB RAM, >= 40 GB disk, reliability >= 0.97, >= 300 Mbps, CUDA >= 13.2 (default py313 image). It was the cheapest Zen 3 offer whose effective cores equal its total cores. C0b's box peaked at 28 GB of memory, so 71 GB was enough; fidelity workers = RAM / 8 GB = 8 |
| Instance | 58572720, image `vastai/pytorch:2.11.0-cu130-cuda-13.2-mini-py313-2026-10-16`, `SETUP=none DISK=40` |
| Create | `ops/vast.sh SETUP=none DISK=40 V2D_COMMIT=ed7171caf6c87b792e1da9d8c38e560a18855475 create 36762812 mesh-20261031-pubown-ed7171c 'bash docs/research/mesh-2026-10-26/cdo-sprint/PUBOWN/jobs/pubown_box.sh'` |
| Ledger (session mesh-bold) | planned $0.40 at 19:58Z (cap $2; approval: the owner's standing go-ahead of 2026-10-30 12:20 UTC); actual **$0.15** at 20:20Z, estimated from the instance clock as about 21 min x $0.410/h plus 1-2 GB downloaded |
| End | The box pushed to the store and self-destroyed. It was gone from `ops/vast.sh show` at 20:19:48Z [M] |

## Timeline (UTC, 31 Oct) [M]

| Step | Time | Duration |
|---|---|---|
| create -> running (image pull) | 19:58:30-20:01:24 | 2.9 min |
| run_job start; code tree at 00e8584 (135 files, tree hashes = plan); venv; gmg markers settings sha256 `488ac3b6...` | 20:01:39-20:01:51 | 12 s |
| inputs (18 files sha256 OK) + 97 reused C0b files (724.9 MB, sha256 = C0b `SHA256SUMS`, `sha_bad` empty) | 20:01:51-20:02:22 | 31 s (reuse fetch 23.7 s) |
| sigma: pot ep0 and blue cup ep11/12/13 (4/4 OK) | 20:02:22-20:03:08 | 46 s |
| build_a: 33 tasks that need no new marker file | 20:03:08-20:05:04 | 1.9 min |
| markers ep0 over {pot, lid}, in parallel with build_a (1/1 OK) | 20:03:08-20:15:27 | 737.7 s (prep estimate 15-20 min) |
| build_b: 9 pot and lid ep0 tasks | 20:15:27-20:17:01 | 1.6 min |
| check (58/58 OK), fidelity (58/58 OK, 8 workers), select | 20:17:02-20:17:44 | 42 s |
| SHA256SUMS (514 files, 39 MB), store push, second push, self-destroy | 20:17:44-20:19:48 | 2.1 min |

## What ran [M]

- **sigma** (gmg A.2; recomputed only where C0b had none):
  - pot ep0 1.308 mm;
  - blue cup ep11 0.764 mm, ep12 1.131 mm (the same as dry run 2), ep13 1.096 mm.
- **Markers ep0** over pot + lid: 29 pot balls, 0 lid balls, consensus radius 11.04 mm. C0b's lid-only ep0
  detection found 0 balls.
- **Thickness chain** (C0b PREREG 3.3, own measurements only; t0_C0b = 4.559 mm):
  - pot: thickness.py on ep2, 26, 27, 41, 42, 43 and 45 (ep45 7.50 mm, ep2 clamped to 1.50 mm); t0_C0b on ep0 and 44;
  - blue cup: thickness.py on ep12, 13 and 21; t0_C0b on ep11 and 22;
  - beige, lid and all 5 racks: t0_C0b.
- **Builds: 25 OK, 17 FAIL.**
  - **Lid ep0 and ep2: 16/16 FAIL.** `prim_potlid.py build_lid` raises `LinAlgError: Eigenvalues did not converge`.
    The flange window is empty, so the covariance is NaN. This is the same failure as C0b's 16/16, which PLAN.md
    expected. Both lids keep library_v3.
  - **rack/ep31: status FAIL, but its candidates exist.** `build()` finished and wrote `ep31_full.glb`,
    `ep31_nomk.glb` and `ep31.json`, plus their in-run fidelity. Then prim_rack's own joint step, run over that single
    episode, raised `IndexError` in `lip_tops` (an empty lip-top selection). Joint variants are not PUBOWN candidates,
    and the candidate stage lists the files that exist. So ep31 full and nomk still went through check and fidelity.
- **58 candidates:** pot 36, blue cup 10, beige 2, rack 10. All 58 passed check: raw mesh watertight, and the kit
  budget leaves at most 4096 faces and 4096 vertices. All 58 got fidelity on their own points.

## Picks (PUBOWN rule = C0b s5 on the pair's own points; in-sample) and the GT-free frame check

The fidelity column is `obs_fidelity` sum_mm on the pair's own pass-B points. Frame columns are measured against
`meshes/library_v3/<object>.glb` at identity, then by trimmed ICP (`checks/frame_kit.json`). The E0 gate is E0
PREREG s4: 3x the C0 public mesh's value (`../E0/inputs/thresholds.json`), applied here as a reading only
(`checks/e0_gate_alt.json`).

| Episode | Object | Pick | own fid mm (runner-up) | sha256 | kit faces / verts / watertight | identity: centroid mm, median mm | ICP rot deg (axis tilt) / centroid motion mm | extent mm (library_v3) | E0 gate | alt (E0-gated) |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | white_pot | nomk | 4.217 (nostem 4.341) | a1b0f9ea | 4096 / 2050 / yes | 8.1, 2.90 | 0.88 / 2.4 | 136 x 182 x 354 (131 x 190 x 362) | PASS | same |
| 0 | white_pot_lid | library_v3 | - | cf899059 | - | - | - | - | - | library_v3 (0 candidates) |
| 2 | white_pot | nostem | 4.995 (fit 5.161) | da20383e | 4096 / 2056 / no | 9.3, 2.69 | 1.10 / 1.9 | 136 x 189 x 412 | PASS | same |
| 2 | white_pot_lid | library_v3 | - | cf899059 | - | - | - | - | - | library_v3 (0 candidates) |
| 11 | blue_cup | g1 | 5.171 (g0 5.741) | 78969bb9 | 4096 / 2052 / no | 5.2, 2.30 | 1.71 (1.63) / 9.0 | 93 x 95 x 157 (95 x 96 x 167) | PASS | same |
| 11 | beige_cup | g1 | 3.910 (g0 5.167) | 5c39b656 | 4096 / 2043 / no | 10.5, 2.60 | 8.27 (5.93) / 2.3 | 101 x 105 x 176 (99 x 110 x 174) | n/a | same |
| 12 | blue_cup | g1 | 3.407 (g0 9.571) | e3c75bf8 | 4096 / 2052 / no | 52.4, 2.83 | 65.06 (64.66) / 54.9 | 362 x 290 x 184 | FAIL | g0 (9.571) |
| 12 | plastic_dish_rack | full | 49.289 (nomk 76.204) | c845d4f9 | 4096 / 2063 / no | 6475.5, 52.82 | 120.53 / 6365.5 | 16342 x 719 x 2290 (109 x 159 x 496) | FAIL | library_v3 |
| 13 | blue_cup | g1 | 2.882 (g0 3.136) | eaf11af1 | 4096 / 2044 / no | 12.5, 2.25 | 2.59 (2.01) / 4.0 | 100 x 94 x 183 | FAIL | g0 (3.136) |
| 13 | plastic_dish_rack | full | 21.634 (nomk 25.936) | 6c996a0a | 4096 / 2062 / no | 48.0, 4.97 | 8.44 / 32.0 | 126 x 265 x 487 | FAIL | library_v3 |
| 21 | blue_cup | g1 | 3.375 (g0 11.225) | 27957f76 | 4096 / 2055 / no | 29.6, 2.97 | 23.31 (23.24) / 23.4 | 137 x 326 x 168 | FAIL | g0 (11.225) |
| 21 | water_pitcher | library_v3 | - | 9f16ed2a | - | - | - | - | - | library_v3 (no PUBOWN method) |
| 22 | blue_cup | g1 | 4.814 (g0 9.628) | 3275ecce | 4096 / 2058 / no | 24.1, 2.84 | 7.56 (7.55) / 9.6 | 168 x 316 x 178 | FAIL | g0 (9.628) |
| 22 | water_pitcher | library_v3 | - | 9f16ed2a | - | - | - | - | - | library_v3 (no PUBOWN method) |
| 26 | plastic_dish_rack | full | 49.712 (nomk 66.875) | 803a2851 | 4096 / 2092 / yes | 2923.9, 32.56 | 14.38 / 3208.6 | 644 x 653 x 5858 | FAIL | library_v3 |
| 26 | white_pot | fit | 4.171 (nostem 4.172) | 10c147c6 | 4096 / 2050 / no | 8.7, 2.98 | 2.84 / 4.5 | 147 x 192 x 321 | PASS | same |
| 27 | plastic_dish_rack | full | 44.138 (nomk 62.930) | 04ae6f1b | 4096 / 2072 / no | 73.1, 13.01 | 29.48 / 28.1 | 412 x 654 x 826 | FAIL | library_v3 |
| 27 | white_pot | fit | 6.059 (nostem 6.068) | f4a298a2 | 4096 / 2064 / no | 40.4, 4.47 | 5.10 / 11.6 | 205 x 200 x 526 | FAIL | library_v3 (4/4 fail) |
| 31 | mini_sweeper | library_v3 | - | 66f6dc93 | - | - | - | - | - | library_v3 (no PUBOWN method) |
| 31 | plastic_dish_rack | full | 48.092 (nomk 82.766) | 56153ee5 | 4096 / 2076 / no | 2502.9, 47.08 | 89.32 / 2250.1 | 6094 x 853 x 4246 | FAIL | library_v3 |
| 41 | white_pot | nomk | 3.683 (fit 3.692) | 1368cb42 | 4096 / 2050 / yes | 6.3, 2.76 | 1.86 / 1.4 | 138 x 182 x 345 | PASS | same |
| 42 | white_pot | nomk | 3.270 (fit 3.519) | dff67c4c | 4096 / 2050 / yes | 8.0, 2.80 | 1.68 / 2.9 | 138 x 183 x 354 | PASS | same |
| 43 | white_pot | nomk | 3.001 (fit 3.054) | 3dea9a78 | 4096 / 2050 / yes | 5.8, 2.64 | 3.17 / 2.8 | 135 x 185 x 356 | PASS | same |
| 44 | white_pot | nostem | 5.459 (thick 5.997) | e82688ff | 4096 / 2063 / no | 8.0, 3.10 | 1.19 / 3.6 | 187 x 366 x 469 | PASS | same |
| 45 | white_pot | fit | 4.806 (nostem 4.806, tie, fewer faces equal -> label) | 9647bf5b | 4096 / 2054 / no | 15.3, 2.79 | 3.31 / 8.9 | 167 x 190 x 364 | PASS | same |

No pick has a kit quality flag. Each budgets to 4096 faces and 2043-2092 vertices, and the archive decodes to the same
arrays. Only 5 of the 20 are watertight after budgeting (pots ep0, 41, 42, 43 and rack ep26). At library_v3's own budget the pot, blue cup and rack are not
watertight either. No pair had ties except ep45 (fit = nostem, the same mesh size).

### Reading the frame check [M unless marked]

- **Pots ep0, 2, 26, 41-45 are in frame.** ICP moves them by 0.9-3.3 deg and 1.4-8.9 mm, the same order as the C0
  and E0 pots that ship (E0 verify_1: 0.90-0.93 deg, 2.6-3.8 mm).
- **Stray marker balls.** The ~22-25 mm bodies far from the pot are marker balls detected away from the surface:
  - ep2 (nostem): 2 balls at ~230 mm;
  - ep44 (nostem): 3 balls at ~335-340 mm;
  - ep27 (fit): 7 balls.
  - They pass the E0 gate, which looks at centroid and median, but they inflate the extents (ep44 187 x 366 x 469 mm).
  - [H] They could pull a template registration. The `nomk` variants have none.
- **Pot ep27 fails.** Its main body is 205 x 200 x 526 mm. All 4 ep27 candidates fail the gate, so the alternative
  set keeps library_v3 there.
- **Blue cup g1 on ep12, 13, 21 and 22 fails.** g1 keeps "appendages" (`lathe_obs.py` default; g0 = `--appendages
  0`). On these episodes the appendages are extra bodies of 90-180 mm, up to 286 mm from the cup:
  - ep12 and ep13: the cup sits in the rack;
  - ep21 and ep22: the cup is with the pitcher.
  - [H] The appendages are co-object or clutter points that survived the carving. This is PLAN section 6's known
    mutual-carving risk.
  - Each g0 passes the gate. Their own fidelity is worse (ep12 9.57, ep21 11.23, ep22 9.63 mm), because the own-point
    fidelity rewards the stray bodies that cover clutter points.
  - ep21 g1 is byte-identical to C0b's cross-episode blue-cup pick. That pick failed C0b's public AUC guard
    (mean -0.546) [D, C0b NOTES 20:30 UTC].
- **All 10 rack candidates fail.** The extents are 16.3 m (ep12), 5.9 m (ep26), 6.1 m (ep31) and 0.41 x 0.65 x 0.83 m
  (ep27). ep13 is closest: centroid 48 mm off and axes 12 deg off. The ep12 fit record shows a degenerate lip plane:
  5 segments, slope_y 252.8, residual 1e-12, a plane fitted through too few points. Own fidelity is 21.6-49.7 mm.
  - C0b's rack points hold clutter. C2/R's amendment A1 (945baa5) addresses this; PUBOWN follows C0b unchanged.
  - C0b's rack failed its AUC guard too (mean -0.133) [D, C0b NOTES].
- **Beige ep11 g1** is C0b's beige mesh (byte-identical). It is not the C1-adopted T1 beige (sha 60e398b0). E0 has no
  beige threshold, so it is not gated. ICP gives a 5.9 deg axis tilt, and the mesh has 4 bodies (largest 174 mm,
  all within 54 mm; [H] inner shells).

### Reproducibility [M]

- **Pot, blue cup and beige are reproducible.** All 32 candidates PUBOWN shares with C0b's box are byte-identical to
  C0b's: pot ep2, 26, 27 and 41-45; cup ep21 and 22; beige ep11. The blue cup ep12 g0/g1 builds are byte-identical
  to the local dry run 2.
- **The rack is not reproducible across machines.** The same frozen code, C0b points and marker file gave different
  ep12 meshes:
  - dry run 2 (local): 201 x 328 x 647 mm, own fidelity 23.606 mm;
  - box: 16.3 m, own fidelity 49.289 mm.
  - The fits agree on H_r to 1e-16. They diverge at the lip plane (4 against 5 segments) and the outline (69 against
    2 lip points).
  - Package versions are equal (numpy 2.5.4, scipy 1.18.1, trimesh 5.2.0, manifold3d 3.5.4).
  - [H] CPU-dependent floating-point paths flip an early threshold in an ill-conditioned fit. Falsifier: rerun ep12
    twice on one machine (identical expected), then on a second CPU type.
  - Both ep12 results are broken anyway.

## For the re-track consumer

- Index: `MANIFEST.json` -> `episodes.ep<N>.<object>`:
  - `store_path` (dataset `aebatirel/v2d-store`), `sha256`, `md5`, `method` and `build.command` (flags; box paths made
    relative);
  - `params` (thickness and sigma), own fidelity, the frame / kit readings and `alt_e0_gated`.
  - library_v3 rows give the repo path and the reason.
- **Set A (PUBOWN rule, as pre-registered in PLAN.md): 20 PUBOWN meshes + 5 library_v3 rows.** It contains the 7
  broken meshes above. Racks in particular are not usable as templates [M, frame].
- **Set B (report-only `alt_e0_gated`):**
  - 14 PUBOWN meshes: 8 pots (all but ep27); blue cup ep11 g1 and ep12/13/21/22 g0; beige ep11 g1;
  - library_v3 for the 5 racks, pot ep27, both lids, the pitchers and the sweeper.
  - The gate is E0's fixed pre-registered rule, not tuned here. Choosing between A and B is the consumer's call, made
    before the re-track scores are seen.
- Frames: the meshes are in the object frame of the library_v3-seeded sweep track, as fitted, with no alignment. The
  ICP numbers above are the GT-free frame reading. Any residual offset should be read from the re-track, not from
  here.
- The pick is in-sample: the same points build each mesh and judge it.

## Store and files

- Store: `aebatirel/v2d-store` `runs/mesh-20261031-pubown-ed7171c/`:
  - `results/pubown/meshes/ep<N>/<object>.glb` (the 20 picks);
  - `cand/` (all 58 candidates);
  - `manifest.tsv`, `selection.json`, `params.json`, `plan.json`, `commands/`, `logs/`, `status/`, `fid/`, `check/`;
  - `SHA256SUMS` (514 files, 39 MB). The local re-check gave 514/514 OK.
  - Reused C0b files were symlinks on the box and were not re-pushed; they stay in `runs/mesh-20261031-c0b-00e8584/`.
- Repo:
  - `MANIFEST.json`;
  - `checks/frame_kit.json` (the 20 picks: identity + ICP + kit path; library_v3 kit rows);
  - `checks/e0_gate_alt.json` (all 58 candidates: identity, bodies, gate; per-pair alternative);
  - scripts `scripts/pubown_frame_kit.py`, `scripts/pubown_gate_alt.py`, `scripts/pubown_manifest.py`.
- Commands (local, 4 shared cores, `nice 10`, `OMP_NUM_THREADS=1`, scratchpad venv, `python -I`):
  - `pubown_frame_kit.py REPO KIT RESULTS OUT [pairs]`, as two parallel halves merged into `checks/frame_kit.json`.
    KIT = the submission kit `v2dlb` (`budget_mesh`, `_encode_archive`, `_decode_object_mesh`,
    `mesh_quality_flags`). About 10 min. It was tested first on `meshes/library_c0/white_pot_lid.glb` and reproduced
    E0 verify_1's C0->v3 lid ICP (1.32 deg, 2.33 mm, tilt 1.24).
  - `pubown_gate_alt.py REPO RESULTS ../E0/inputs/thresholds.json OUT`: 100 k samples per mesh, about 4 min.
  - `pubown_manifest.py REPO RESULTS mesh-20261031-pubown-ed7171c MANIFEST.json checks/frame_kit.json checks/e0_gate_alt.json`.
    It asserts that each pick's sha256 matches across `selection.json`, `manifest.tsv` and `SHA256SUMS`.
