# E0 verify_0: adversarial verification, integrity lens

- **When / where.** 2026-10-31, ~17:00-17:30 UTC, cloud VM (4 shared cores, loaded), CPU only, $0. I did not build E0.
- **Scope.** Ground-truth reads in every E0 script and in the box job; contents of the store inputs folder; PREREG
  timing against the dry-run, box and git/store times; settings against the public frozen ones; the pick, recomputed
  from the box's raw tables; ledger lines; whether the box is gone. Also: which scan-derived or unexplained constants
  actually bind in the four picks (the C0b constants audit, pushed 40 s before the E0 package commit, was not
  available to the packager).
- **Labels.** [M] measured here. [E] estimate. [D] quoted from an earlier document, not re-measured. [H] hypothesis.
- **Ground truth.** None read. I opened no scan, mocap, parquet or `*_align` file. The only public data I used are
  the public observed points `scratchpad/obs_all/ep{12,13,26,27,31}_plastic_dish_rack.npz` (our own stereo), to
  re-run the public rack build.

## Verdict

- **Blocking: 1 (B1).** It is a ship gate for pot, lid and rack, not a defect in the run. The blue cup is not affected.
- **Non-blocking: 9 (N1-N9).**
- **Confirmed: 9 (C1-C9).** No ground truth was read. The store inputs hold no ground truth. PREREG was pushed
  before any eval candidate existed and did not change afterwards. Settings equal the public ones, except N1. The pick
  and recommendation recompute exactly. The ledger is complete, and the box is gone.

## Blocking

### B1. The scan-derived marker-ball prior shapes the E0 pot, lid and rack picks, and no owner decision covers E0

- **The rule.** The task's integrity rule says no parameter may come from scan measurements. Thickness (the 2.5 mm
  grid midpoint, flagged) is the only stated exception.
- **The prior.** `prim_potlid.py` (frozen sha1 c2627630) has `MK_R0 = 7 mm` and the free-fit window 5-9.5 mm. Both
  are S-value: measured on public scans (C0b `AUDIT.md` ids 12 and 13; C0 verify_0 B1). `prim_rack.py` uses the same
  `markers_from`.
- **Where it binds, from the E0 build records [M]:**

  | Pick | Ball | Free-fit radius | Shipped radius |
  |---|---|---|---|
  | pot/ep3/fit | 1 | 7.34 mm | 7 mm (prior) |
  | pot/ep3/fit | 2 (with a stem) | **32.52 mm** | 7 mm (prior) |
  | lid/ep1/t2.5_fit | 1 | 7.74 mm | 7.74 mm (free fit, accepted only because it is inside the scan window) |
  | lid/ep1/t2.5_fit | 2 | 12.07 mm | 7 mm (prior) |
  | rack/joint/joint | 1 | 6.52 mm | 7 mm (prior) |
  | rack/joint/joint | 2 | 6.24 mm | 7 mm (prior) |

  In the rack, the `in_basin` rule rejected 4 more clusters, one of them a free 8.16 mm ball. `in_basin` is
  U-suspect: it was added after the first rack scan scores (C0b id 101).
- **What the owner decided.** "Ship 9a, flagged" (C0 README, ~16:55 UTC). That decision covers the C0 meshes in
  pack 9a. The stated plan for pack 10 is the GT-free rebuilds C0b/E0b ("ball radius from our own marker detector …
  or no balls"). No decision covers the E0 meshes.
- **The gap.** MANIFEST flags the prior on every pot, lid and rack pair. But README and `selection_final.json` say
  "E0 for all four objects with no rule flags", and that reads as ship-ready.
- **Needed.** Before E0's pot, lid or rack ships in any pack, either an explicit owner decision for E0 (as for 9a), or
  E0b (the same pipeline with the GT-free marker path). The blue cup is a lathe with no marker path, so it is not
  affected.

## Non-blocking

### N1. Rack code: the frozen `prim_rack.py` is not the file the public clean-up round ran, and my public re-run is not byte-identical

- **The mismatch [M].**
  - `results/prim/clean/code_state.txt` records `prim_rack.py` sha1 **7a7fa102** for the clean-up-round runs, which
    built the C0 rack.
  - E0 froze **18a923c3**, the file committed in 2971a10 (27 Oct 07:08:41).
  - No commit contains 7a7fa102. The two git versions are ca2aea0d (104ae2a) and 18a923c3 (2971a10).
  - PREREG section 2 calls 18a923c3 "the committed clean-round file" and does not mention the mismatch. The prep
    reproduced the pot, lid and cup byte-identically, but not the rack.
- **Evidence for equivalence [M].** `scratchpad/prim/clean/rack/default/` (27 Oct 07:08:24, 17 s before the commit;
  `default.check` = `DEFAULT-SAME`) holds a default-settings re-run.
  - All 12 meshes are byte-identical to `t2.5_lean1/`.
  - Its `joint_joint.glb` md5 is bbca8ec0…, the C0 rack.
  - This fits the diff 104ae2a→2971a10: the defaults now equal T_WALL 2.5 / CUP_LEAN 1, plus comments. But nothing
    records which file that re-run executed.
- **My re-run [M].** Command: `PRIM_T_WALL=0.0025 PRIM_CUP_LEAN=1 venv/bin/python -I -W ignore
  E0/jobs/frozen/.../prim_rack.py run --obs_dir scratchpad/obs_all --out scratchpad/cdo_e0/verify0/rack_pub`, local
  pinned venv (same versions as the box `freeze_main.txt`).
  - With `OMP_NUM_THREADS=1`: 12/12 meshes differ from the public run.
  - Structure is identical: H_r, cup top, pegs and markers per episode.
  - Faces differ by ≤ 4. Fidelity differs by ≤ 0.004 mm. The joint is 5.938 vs 5.935 mm, with 2354 vs 2356 faces.
  - With default threads: RACK_THR_RESULT.
- **Effect.** This sits far inside the 15 % rule margin. The rack rec does not depend on it (C0/pick 0.973).
- **Needed.** Record in PREREG/BOX that the rack's public run used 7a7fa102, and cite the DEFAULT-SAME evidence. Do
  not claim a byte-identical rack reproduction.

### N2. library_v3 is a scan-tier input on the project's own deny-list, and E0 does not disclose this

- **Where E0 reads `meshes/library_v3` [M]:**
  - `obs_points --roi` (crop box) and `--others` (co-object carving), both binding.
  - `prim_potlid --lib` in the `tsdf` variants. All 7 tsdf candidates were excluded as not watertight, so this does
    not bind.
  - The PREREG section 4 frame-check exclusion. It does not bind: the only exclusions were 7 "not watertight".
  - The eval tracks are seeded with library_v3: the evperc-4f596df `job.log` says "LIB …/meshes/library_v3".
- **Why it matters.** `ops/provenance/denylist.json` lists `meshes/library_v3/*` as scan-derived, and C0b `AUDIT.md`
  section 2.1 classes it S-input.
- **The gap.** E0 MANIFEST/README name library_v3 as an input, but they do not state its provenance tier. C0's F4
  covers only the tracks.
- **Needed.** Add one line to the MANIFEST flags.

### N3. Unexplained constants bind in the E0 picks, including one that did not bind in C0

- **New binding: the pot handle [M].** In the E0 pot pick the handle thickness is `T_src: "prior"`: `BAR_T0` = 5 mm
  (prim_potlid:76). That constant has no recorded derivation. In C0 the handle was measured from the side (5.8 mm), and
  the audit lists `BAR_T0` as non-binding.
- **Inherited, as in C0 [M/D]:**
  - lid arch T = 3.0 mm, the clip floor;
  - `APP_D`, `MK_DIAG`, `table_band` (U-suspect);
  - `in_basin`, see B1.
- **Needed.** The MANIFEST "METHOD QUALIFIER" is generic. It should cite C0b `AUDIT.md` and name `BAR_T0` for the pot.

### N4. The cup floor comes from a rule set in response to a scan diagnostic

- **What it is.** The lathe floor rule (lower 40 %, > 200 pts, < 10 mm layer) is S-dev (C0b id 131).
- **What happened [M].** In all 5 eval g1 builds it found no observed floor: `hfloor_mm` = `t_mm`, i.e. the floor is
  at base + t. The pick's t is 3.32 mm.
- **Not affected [M].** The scan-valued wall fallbacks do not bind:
  - the cup's 3 mm fallback: t was measured in every cup build, 2.88-6.57 mm;
  - the pot's 4 mm fallback: 12 two-wall bins, t 3.51 mm.
- **Needed.** Disclose the floor rule next to the cup's flags.

### N5. Eval depth is checked by byte size only

`e0_fetch.py` sha256-checks the 45 input files, but it checks the 14 depth caches (21.4 GB) only against
`plan.json` sizes. A same-size corruption would pass. This is low risk, and it is not a ground-truth path.

### N6. PREREG wording and how it was committed

- **[M].** PREREG.md is byte-identical (sha256 bfb85697…) to its first commit, 705652a (16:08:17, pushed 16:08:20).
- **The wording.** Its header says "Written … ~16:05-16:20 UTC", but nothing was added after 16:08.
- **How it was committed.** It went in with a shared "WIP snapshot" commit, not an E0 commit.
- **Effect.** Timing is unaffected (C3). The header should say "committed 16:08:17 (705652a)".

### N7. "The pack's poses" is asserted, not verified for each episode

- **Verified [M]:**
  - All 14 `data/eval/ep<N>/poses.npz` match the store `runs/20261025-evperc-4f596df/results/evalperc/` byte for byte.
  - That run tracked library_v3 bodies.
  - pot, lid, rack and cup are byte-identical in library_v3 and library_v3x, so the body frame is the same in both
    libraries.
- **Not checked.** Whether each pack episode's poses equal these tracks. Per the 25 Oct work log, evals 8, 14, 32 and
  33 had references rebuilt. The frame argument does not depend on this [H]: any track of a library_v3 body
  estimates the same body frame.

### N8. The ledger actual is a clock estimate

- **Recorded.** Actual $0.13: 15.2 min × $0.486/h plus ~22 GB at $0.29/TB. It is labelled an estimate. No Vast
  invoice figure was read.
- **Plausibility [E].** Recomputed: 16:25:29→16:40:39 = 15.2 min, about $0.12 plus < $0.01.

### N9. The recommendation stays in-sample, and on the rack the out-of-sample reference wins

This is not an integrity defect; it is already disclosed.
- **Rack [M].** library_v3 scores 5.881 mm against the pick's 6.419 on ALL; library_v3/pick = 0.916. The rack rule
  compares only against C0.
- **Pot [M].** C0/pick = 0.997.
- Both pick E0 only through the 15 % margin, which the prereg intended as the in-sample allowance. Read together with
  B1.

## Confirmed

### C1. No ground-truth read in any E0 code path [M]

- **Grep.** I searched `jobs/*.{py,sh}`, `jobs/frozen/**`, `scripts/e0_package.py` and `C0/scripts/frame_check.py`
  for scan/mocap/parquet/align/ground. Hits are comments, flag text, and `prim_rack.icp_align` (a function name).
- **Every file read in the frozen scripts:**
  - `obs_points`: poses, depth, hands, calib, ROI/others meshes;
  - `prim_potlid`: obs npz, axis cache, `--lib`;
  - `prim_rack`: obs npz, plus a subprocess of `obs_fidelity`;
  - `lathe_obs`: obs npz;
  - `obs_fidelity`: obs npz and meshes;
  - `hands_mp`: `T3/calib.json`, `world_T_cam`, depth, video;
  - `e0_select`, `e0_package`, `frame_check`: result JSONs, meshes, C0 MANIFEST/roster.
- **Data setup on the box.** It ran `SETUP=none`, so neither `pipeline/setup.sh` nor `fetch_data.sh` ran; no dataset
  download (`run_job.log`).

### C2. The store inputs contain no ground truth [M]

`runs/mesh-20261031-e0-b05f001/inputs/` holds 46 files (listed with `list_repo_tree`):
- `SHA256SUMS`, `plan.json` and `calib.json`. calib.json is the OAK factory calibration: keys source, units, devices,
  cameras, stereo_pairs, skew. md5 56c32942…, the same file the public runs used.
- `kit/v2dlb/mesh_budget.py`.
- For each of the 14 eval episodes:
  - `poses.npz`, with keys only `world_T_cam` and `cam_T_<roster objects>`;
  - `result.json`, which holds detection statistics;
  - `ep<N>_a.mp4`.
- The box's `inputs_SHA256SUMS` equals the local files.
- No name or content is a scan, mocap, parquet or `_align` file.
- Depth comes from `cache/depth/eval/` (FoundationStereo inference) and nothing else.

### C3. PREREG existed on origin before any eval candidate, and nothing changed after [M]

| Event | UTC |
|---|---|
| Dry run starts (eval 14 hands, then obs; no candidate) | 16:04:46 |
| PREREG.md + jobs committed (705652a) | 16:08:17 |
| … pushed (remote-tracking reflog) | 16:08:20 |
| First dry-run build (code test, stride 8; not a candidate) | 16:11:10 |
| First dry-run fidelity line | 16:12:55 |
| b05f001 (NOTES only) pushed; the box code | 16:19:16 |
| Inputs uploaded to the store (single "E0 inputs" commit) | 16:19:38 |
| Ledger planned line (store commit) | 16:25:13 |
| Instance created | 16:25:29 |
| First production build | 16:37:05 |
| Box job done, pushed | 16:40:22 |
| Instance gone | 16:40:39 |
| Ledger actual line (store commit) | 16:41:03 |

- `git diff 705652a b05f001` and `git diff 705652a HEAD` over `PREREG.md`, `jobs/` and `inputs/` are both empty.
- The box ran b05f001 with `dirty=0`, and its frozen code passed the sha1 check.
- The dry run's eval-14 numbers came after the PREREG push, and no rule or code changed afterwards.

### C4. Frozen code equals commit 2971a10 [M]

- All 7 files under `jobs/frozen` have the same sha1 as `git show 2971a10:<path>`.
- `prim_potlid.py` c2627630 equals `code_state.txt`. The working-tree file (9032a68b, 14eaf37 WIP) is correctly not
  used.
- Exception: `prim_rack.py`, see N1.

### C5. The settings equal the public ones [M]

- **obs_points.** The `args` of all 17 eval obs npz equal the public obs npz files (ep21 cup; pot eps 0, 2, 26, 27,
  41-45; lid eps 0, 2; rack eps 12, 13, 26, 27, 31) in every non-path key: stride 2, vox/hit 4 mm, free 10 mm,
  other_r 12 mm, edge_thr 20 mm, zmax 1.5, table_band 8 mm, hand/arm radii, min_hits 3, min_ratio 0.5, margin 20 mm.
  - All 17 used `--hands`.
  - `--others` equals each episode's other tracked bodies.
- **Hands.** The public `hands.npz` (G1 refs perc2m, `pipeline_ep.sh` step 2, no `HANDS_ARGS`, raw output) was made
  by the same `hands_mp.py` as E0's (no diff 022fece→2971a10).
- **Builds** (box `commands/build.txt` against `run_fit.sh`, `run_rack.sh` and the clean-round lid command):
  - pot `--variant V --lib library_v3 --axis_cache`, fit first; all 24 inner rc=0;
  - lid `PRIM_T_LID=0.0025 … --variant fit|tsdf --lib`;
  - rack `PRIM_T_WALL=0.0025 PRIM_CUP_LEAN=1 … run` (plus `--episodes` for eval);
  - cup `lathe_obs.py` defaults (g1) and `--appendages 0` (g0).
- **Venv.** Box `freeze_main.txt` pins equal `req_main.txt` and the local venv.

### C6. The pick follows PREREG sections 4 and 6 [M]

- **My implementation.** A third one, written without reading `e0_select.py` or `e0_package.py`:
  `scratchpad/cdo_e0/verify0/recompute.py`, run with `python -I` on the box's raw `fid/*/*.jsonl`, `check/*/*.json`,
  `candidates.json` and the committed `inputs/thresholds.json`.
- **Result.** It agrees with the box and the packager on every pick, eligible set, exclusion, ratio and
  recommendation:

  | Object | Pick | Eligible | Excluded | sum_mm ALL | C0/pick | lib/pick | Rec |
  |---|---|---|---|---|---|---|---|
  | white_pot | pot/ep3/fit (tie with nostem, same sha; label order) | 18/24 | 6 tsdf, not watertight | 2.922 | 0.9973 | 1.3282 | E0 |
  | white_pot_lid | lid/ep1/t2.5_fit | 1/2 | t2.5_tsdf, not watertight | 1.675 | 1.0579 | 3.0961 | E0 |
  | plastic_dish_rack | rack/joint/joint | 12/12 | - | 6.419 | 0.9729 | 0.9162 | E0 |
  | blue_cup | cup/ep32/g1 | 11/11 | - | 2.646 | 1.0291 | 1.0983 | E0 |

### C7. The packaged files are the picks [M]

- In `library_e0` and `library_e0x` the four swapped files have the sha256 of the picks (af321725…, e3dd5861…,
  fc67c59b…, e6c18b2a…). Those equal the box `SHA256SUMS` and the `E0/meshes/` copies.
- Every other `.glb`/`.json` file equals library_v3 (or library_v3x for e0x).
- The `*.recon.json` files are absent, as in library_c0.
- The largest committed E0 file is 638 KB.
- No secrets were found by a pattern scan.

### C8. The ledger has both lines, in order [M]

`ledger.py show` (session mesh-bold) lists both lines for `mesh-20261031-e0-b05f001`:
- planned $1.00 at 16:25Z, before the create;
- actual $0.13 at 16:40Z, after the destroy.

Store commit times are in C3.

### C9. The box is gone [M]

`ops/vast.sh show` at ~17:12 UTC lists 7 instances of other sessions. Instance 58555214 is not among them.

## Re-run

- `python -I scratchpad/cdo_e0/verify0/recompute.py <box results/e0> E0/inputs/thresholds.json` (output
  `scratchpad/cdo_e0/verify0/recompute_out.json`).
- Rack: the commands in N1 (output `scratchpad/cdo_e0/verify0/rack_pub*`).
