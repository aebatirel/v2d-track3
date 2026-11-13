# C0b audit: where every constant of the C0 mesh methods comes from

- **When and where.** 2026-10-31, ~16:37-17:10 UTC, on the cloud VM (4 shared cores, loaded). CPU only, $0.
- **What.** Every numeric constant, prior, window, threshold and default in `prim_potlid.py`, `prim_rack.py`,
  `lathe_obs.py`, `obs_points.py`, `obs_fidelity.py`, the `pipeline/recon_mesh.py` helpers that `obs_points.py` imports
  (`rectified_K`, `hand_segments`, `table_plane`), and the command lines and inputs that built the four C0 meshes (pot,
  lid, rack, blue cup).
- **Why.** C0b and E0b rebuild these meshes with no scan-derived constant. This file lists what must change, and what
  can stay.
- **Files.**
  - `AUDIT.json`: 163 records. Each record gives name, value, file:line, what the value controls, origin, evidence,
    whether it changed the C0 mesh, and the C0b action.
  - `scripts/audit_gen.py`: holds the records and writes `AUDIT.json` and the tables in section 5.
  - `scripts/floorcheck.py`, `scripts/tiecheck.py`: two binding checks. They read only our observed points.
- **Code version.** Line numbers refer to HEAD. In `prim_potlid.py`, HEAD is `14eaf37`; its code equals `2971a10`
  and E0's `jobs/frozen` copy, apart from the comment on line 67. The other four scripts and `recon_mesh.py` equal
  E0's frozen copies.
- **Labels.**
  - [M]: measured here, without ground truth (our points, build records, transcripts, git).
  - [D]: an existing scan diagnostic, quoted here, not recomputed.
  - [E]: estimate. [H]: hypothesis.
- **Ground truth.** None was read. No scan, mocap, parquet or `*_align` file was opened, and nothing was scored.

## 1. Origin classes

| Code | Meaning |
|---|---|
| **G** generic | Physics, units, numerics: bin sizes, iteration counts, robust-statistics factors, sample sizes and seeds, tessellation, sensor range. |
| **O** own-observation | Measured or decided on our own stereo or video, with a record. |
| **S** scan-derived | **S-value**: a number measured on a public scan, directly or through a brief or document that quoted scan measurements.<br>**S-dev**: a value or rule set in direct response to a scan diagnostic or a scan score.<br>**S-input**: an input file that the project's own deny-list marks as scan-derived (`meshes/library_v3`). |
| **U** unknown | No recorded derivation. **U-suspect**: the value also matches a scan number the author had in context, or was set in a development loop that read scans. "Unknown" is not "generic". |

"Binds" means the value changed the C0 mesh, judged from the build records (`*.json` next to each candidate) [M].
Where a check was needed, it is in `scripts/`.

## 2. Summary

**Counts** (`AUDIT.json` `meta`). Of 163 records: G 62, O 14, S 16, U 71.
- S splits into S-value 8, S-dev 4 and S-input 4. Two S-value records are the C0 lid and rack command lines that set
  `T_LID` and `T_WALL`; one S-input record is the obs_points command lines that pass `--roi` and `--others`.
- 16 of the U records are U-suspect.

The `id` columns below are the record ids in `AUDIT.json` and section 5. Some rows group several values; for
example, "LSQ subsamples" is one row with three values.

### 2.1 Scan-derived items (S)

| id | Item | file:line | Value | Class | Binds in C0 [M] |
|---|---|---|---|---|---|
| 12 | `MK_R0`, the fixed marker-ball radius | prim_potlid:67 (also used by prim_rack) | 7.0 mm | S-value | **yes**: pot 4 of 5 balls, lid 2 of 3, rack 1 of 2 |
| 13 | `MK_RMIN`, `MK_RMAX`, the free-fit radius window | prim_potlid:68 | 5.0-9.5 mm | S-value | **yes**: decides free radius vs 7 mm on every ball |
| 18 | `T_LID`, the lid sheet thickness | prim_potlid:75 (`PRIM_T_LID`) | 2.5 mm | S-value | **yes**: the lid underside |
| 62 | `T_WALL`, the rack wall and floor thickness | prim_rack:64 (`PRIM_T_WALL`) | 2.5 mm | S-value | **yes**: floor plate, floor depth, cup-holder wall, cavity |
| 17 | Pot wall fallback, used when < 3 two-wall bins | prim_potlid:405 | 4.0 mm | S-value | no: C0 pot had 24 two-wall bins, t 4.77 mm |
| 128 | Lathe wall fallback, used when < 3 two-wall bins | lathe_obs:244 | 3.0 mm | S-value | no: C0 cup had 33 two-wall bins, t 1.965 mm |
| 131 | Lathe floor rule: lower 40 %, > 200 pts, < 10 mm layer | lathe_obs:252-259 | rule | S-dev | **yes in structure**: the old rule gives a floor 106.9 mm higher. The numbers do not bind (section 3.3). |
| 155 | Blue-cup selector, `obs_fidelity.py` used as the pick | obs_fidelity (whole) | rule | S-dev | **yes**: written after the cup lathes were scored on the scan (C0 flag F3) |
| 77 | `cup_upright()`, the `CUP_LEAN=False` path | prim_rack:324-357 | estimator | S-dev | no: C0 uses lean = True |
| 122 | `--floor observed` option | lathe_obs:201-203 | option | S-dev | no: the default is `base` |
| 133 | `--roi` = library_v3 mesh bounds | obs_points:32, 56 | file | S-input | yes: crops the samples to that box |
| 134 | `--others` = library_v3 co-object meshes | obs_points:33, 50-55 | files | S-input | yes: lid ep2 (pot), rack ep12/13 (cup), rack ep27 (pot), cup ep21 (pitcher) |
| 46 | `--lib` = library_v3 in the `tsdf` variant | prim_potlid:597-606 | file | S-input | not in the picks, but the variant is in the pot and lid candidate pools |
| 157, 158 | C0 lid and rack command lines (`PRIM_T_LID`, `PRIM_T_WALL` = 0.0025) | results/prim/clean | env | S-value | yes (= ids 18 and 62) |
| 160 | C0 obs_points command lines (`--roi`, `--others`) | prep_obs.sh, npz args | files | S-input | yes (= ids 133 and 134) |

**Why library_v3 counts as scan-derived.** `ops/provenance/denylist.json` (mesh pipeline v5 spec 3.2) lists
`meshes/library_v3/*`. The ledger (sections 1 and 6) says library v1-v4 were fused along tracks templated on the
public scans, with the scans as `--others`. Yet C0 and E0 read it in four places:
- `obs_points --roi`;
- `obs_points --others`;
- `prim_potlid --lib`, in the `tsdf` variant;
- E0's frame-check exclusion (E0 PREREG section 4).

Earlier C0 documents report this only as the provenance tier of the tracks (flag F4). Using library_v3 as a direct
input file is new here.

### 2.2 Unknown items (U)

**U-suspect (16 records; APP_D has one per file).** Each also matches a scan number the author had in context, or was set in a loop that read scans.

| id | Item | file:line | Value | Binds in C0 [M] | Why suspect |
|---|---|---|---|---|---|
| 6, 71 | `APP_D`, the residual threshold for handle, arch and markers | prim_potlid:61, prim_rack:74 | 8 mm | yes (every residual set) | "stereo noise 5-10 mm": the only noise figures on record then were obs-vs-scan percentiles [D] (pot p90 6.6, p95 8.7 mm) |
| 9 | `MK_DIAG`, the marker cluster size window | prim_potlid:64 | 6-35 mm | yes (size rejections) | sized around the scan-derived 7 mm ball |
| 72 | `MK_FREE_R`, the cap radius window | prim_rack:75 | 4-12 mm | yes (with `MK_SPREAD`) | window around the 7 mm prior |
| 99 | `marker_parts` acceptance | prim_rack:573-582 | `MK_FREE_R` and res ≤ 1.2 mm, or spread | yes | as item 3 |
| 16 | `T_MIN`, `T_MAX`, the clip of the measured pot wall | prim_potlid:71 | 2-6 mm | no (4.77) | brackets the scan pot wall 3.9 mm that the builder had just read |
| 19 | `T_LID` grid | clean-up round | 1.5 / 2.5 / 4.0 mm | n.a. (verdict rule) | centred on the leaked 2.5 |
| 33 | `hO`, the polar profile origin | prim_potlid:379 | 0.6 × height | yes | the builder viewed the scan-profile figure before writing it |
| 45 | Handle reach | prim_potlid:577 | rmax + 60 mm | yes (insensitive) | the brief gave the handle as ~17 cm, a scan bounding-box number |
| 47 | Lid dome window | prim_potlid:615-624 | r 15-35 mm | yes | lid-specific absolute window; the brief carried the scan lid size |
| 50 | Lid flange window | prim_potlid:652-654 | r 40-80 mm, ±6 mm | yes | same as item 9 |
| 55 | Arch detector | prim_potlid:728-735 | ≥ 100 pts, extent > 50 mm | yes | same as item 9 |
| 101 | `in_basin` marker rule | prim_rack:675-682 | rule | **yes: 9 candidate balls rejected** | added 06:03, after the first rack scan scores (05:51) and the [D] region printout (05:52-05:53) |
| 107 | `TIE`, the axis near-tie factor | lathe_obs:28 | 1.25 | **no** [M]: TIE 1.1, 1.5 and 2.0 give the same axis | set inside the scan-scored lathe loop |
| 121 | `--tmin`, the lathe wall floor | lathe_obs:200 | 1.5 mm | no for t (1.965) | written after scan_stats showed walls of 1.8-3.9 mm |
| 140 | `--table_band` | obs_points:36 | 8 mm | yes (cut height) | written 8 min after scan_stats.py; recon_mesh uses 15 mm; 8 is not derived |

**Other U items that bind in C0.** No recorded derivation, though not otherwise suspect:
- **Bounds the C0 fit stopped on:**
  - prim_rack `S0_MIN`, 4 mm: s0 = 4.000 mm. The 7-9 mm lip observation it cites is O; the 4 mm margin itself is
    not derived.
  - prim_rack outline bounds (279-280): s1 = 0, so the sloped inner face is not identified.
  - prim_potlid arch thickness clip, 3-8 mm (770-775): C0 strap T = 3.0 mm, the clip floor.
  - prim_rack cup inner floor, ≥ 50 points (382-383): 43 points, so the cup-holder floor falls back to the tray floor.
- **Shape priors:**
  - `PEG_KAPPA` = 1: round pegs.
  - `JOINT_TOL` = 1.25: chooses episodes 12, 13 and 27. In the first run, ep26 missed the cut by 0.04 mm of fidelity.
  - `MK_SPREAD`: keeps the rack's 9.51 mm ball.
- **Rack-specific windows:** peg detection and fit, lip sampling, outline and cup point classes, cup region and top,
  tray x-offsets, lower-plane percentiles.
- **Marker gates:** `MK_MIN`, `MK_RES`, `MK_GAP`, free-fit acceptance (res < 1.2 mm, spread > 0.08), `STEM_*`, the
  re-cluster height.
- **Pot heuristics:** rim window, body extent, rim height, bar width and ends, handle hole, handle cluster size.
- **Lid windows:** tilt, `SURF_D`, residual radius, arch sampling.
- **Lathe:** `--app_d` 4 mm, `--app_min` 400, cap-in margin, appendage splat morphology.
- **obs_points:** `--other_r` 12 mm, `--edge_thr` 20 mm, the free-space vote (4 / 4 / 10 mm, 3, 0.5), the per-frame
  table refit (30 / 12 mm, 10 deg).
- **recon_mesh:** `table_plane` thr 6 mm.
- `F_SCALE` 2 mm; the track provenance (P1).

**Non-binding U items:** `BAR_T0` 5 mm, `STEM_R`, `STEM_MIN`, the arch width clip, the bar thickness clip, cup bounds.

### 2.3 What changes the C0b plan

1. **Marker balls (ids 12, 13) and every marker gate.** Replacing `MK_R0` and the window is not enough.
   - `MK_DIAG`, `MK_RES`, `MK_GAP`, the free-fit acceptance, `MK_FREE_R`, `MK_SPREAD` and `in_basin` all decide which
     balls exist. None has a recorded origin, and three are U-suspect.
   - Use gmg `markers.py` (settings frozen in PREREG A.6) as one replacement for the whole marker path, or build
     without balls.
2. **Thickness (ids 17, 18, 62, 128).** `T_LID` and `T_WALL` bind; the 4 mm and 3 mm fallbacks would bind on any eval episode
   with too few two-wall bins.
   - Take the thickness from our own observations (gmg `thickness.py`).
   - Where it cannot be measured (lid underside, rack floor), use a generic grid declared without reference to 2.5,
     with "pass at every value". Or fail the build instead of falling back.
3. **library_v3 as input (ids 46, 133, 134).** The ROI box and the co-object carving need GT-free replacements:
   - ROI: a fixed cube around the track origin. `recon_mesh` uses ±30 cm, and the `obs_points` docstring says any box
     works.
   - Co-objects: our own points or meshes, e.g. gmg `extract_joint` ownership.
   - Drop the `tsdf` variant.

   The tracks themselves stay P1. That is an owner and organiser question (F4), not a constant.
4. **Blue cup (ids 131, 155).**
   - The floor rule's numbers do not bind on ep21. Its structure does: dense floor evidence or base + t. Pre-register
     it with a GT-free reason (a cup's floor is about one wall thick; sparse cap points are not a floor) and record its
     S-dev origin.
   - Pre-register the selection, as the brief says.
   - `--app_d` 4 mm and `--app_min` 400 shape the cup's appendages. Neither has an origin.
5. **APP_D (U-suspect, binds everywhere).** Replace with an own-observation value as an option: a high percentile of
   the observed-point distance to the fitted body, per episode. Or pre-register a generic value and test a second one.
6. **The bounds the fits stopped on** (`S0_MIN`, outline s1 ≥ 0, arch T ≥ 3 mm, cup floor ≥ 50 points) set geometry in
   C0 without evidence. Any C0b PREREG should name them.
7. **E0's eval observed points** (`cdo_e0`, run `mesh-20261031-e0-b05f001`) used exactly the C0 `obs_points` defaults,
   with `--roi` and `--others` from library_v3.
   - `obs_points.py` contains no S-value constant.
   - Its S items are the two library_v3 inputs, and `table_band` is U-suspect.
   - **Reuse them only if C0b accepts library_v3 as ROI and carving input. Otherwise rebuild them with an own box and
     own co-object carving.** Hands (MediaPipe) and the depth are fine.
   - E0's selection also excludes candidates by a frame check against library_v3, at 3× C0's values. C0b needs its own
     GT-free frame check.

## 3. Evidence

### 3.1 The primitive-round brief carried scan numbers to the builders (27 Oct, workflow `wf_b8fd112f-f1f`)

The brief shared by all builders (agent transcripts, first task message) said:
- "the scans are thin double-walled shells (pot wall ~4 mm, lid ~2 mm, rack fins ~2.5 mm, boards 7.5/9.1 mm thick)";
- "a prior of ~7 mm radius measured earlier from our own stereo is allowed".

The family briefs said:
- pot: "~19 cm across, ~13 cm tall incl. rim, thin wall (~4 mm), ... handle (~17 cm)";
- lid: "~19 cm across, ~2 mm thick sheet ... a ~2-3 mm prior measured from our points";
- rack: "~51 x 18 x 12 cm ... fins (~2.5 mm thick)".

All of these are the [D] scan statistics of README section 1:
- pot: 3.9 mm wall, bounding box 13.2 × 18.9 × 35.7 cm (35.7 - 18.9 ≈ 17 cm of handle);
- lid: 1.8 mm, 18.8 × 19.0 cm;
- rack: 2.5 mm, 51.0 × 17.5 × 11.7 cm.

The 7 mm prior is scan-derived (section 3.2). "Measured from our points" for the lid was false: the clean-up PREREG
found the lid thickness not measurable from our points.

**What the builders read before writing code** (transcripts):
- The pot/lid builder (agent `ae0d680a6cb0fc08a`):
  - read README lines 29 (scan walls) and 81-82 (scan pot and lid rows);
  - opened `figures/pot_profile_lib_vs_scan.png` at 04:08;
  - then wrote `prim_potlid.py` at 04:19.
- The rack builder (agent `ab2ac4c72910cc6f8`):
  - wrote `prim_rack.py` at 05:22;
  - scored two dev meshes on the scan at 05:51;
  - ran `diag_regions.py` [D] at 05:52-05:53, which printed the scan floor height and cup-holder extents;
  - then made `CUP_LEAN=False` + `cup_upright` (05:54-05:57) and `in_basin` (06:03).
  - `MK_FREE_R`, `MK_SPREAD`, `PEG_KAPPA`, `PEG_LEAN`, `JOINT_TOL` and `S0_MIN` date from 05:30-05:48, before any scan
    score.

### 3.2 The marker radius

- `spoon/spoon_template.py:71`: `marker_radius 0.0072`, "note 17: one physical size, fitted r 6.6-7.8 mm".
- `docs/research/notes/17-marker-tracking.md` §A1 is titled "Marker sphere catalogue from the scans [V]".
- The stage-1 audit (work log 27 Oct ~17:20 UTC, blocker 1) tied `MK_R0` and the 5-9.5 mm window to it.
- The 27 Oct 13:20 critic's "R0 = 7 mm came from eval-episode spoon stereo" is superseded by that audit.

### 3.3 lathe_obs.py was developed against the scans (26 Oct, main transcript)

| UTC | Step | Label |
|---|---|---|
| 15:33 | `scan_stats.py` measures the scan walls | [D] |
| 15:41 | `obs_points.py` written | |
| 15:49 | `obs_diag.py`: observed points vs scan | [D] |
| 15:51 | `lathe_obs.py` written. Its docstring cites the [D] diagnostic and "3 mm walls"; it holds the 3 mm wall fallback and `--tmin` 1.5 mm. | |
| 15:54 | a0/a1 scored on the scan | |
| 15:55:44 | `prof_plot2.py` draws the scan section over the a0 lathe | [D] |
| 15:56:38 | the floor rule is replaced | |
| 15:56 | b0/b1 scored | |
| 16:00:27 | `area_prof.py` on the scan, and `--floor observed` added | [D] |
| 16:08:59 | the axis tie-break (`TIE`) | |
| 16:10:24 | scan points rendered along the pot axis candidates (`pot_axes.png`) | [D] |
| 16:11:31 | `MINSEC` 3 → 6, after a sector-count table of our own pot points (16:10:55) | |
| 16:12 | g versions scored. g1 (all defaults) is the C0 cup's method. | |

**Binding checks** [M]:
- **Floor rule** (`scripts/floorcheck.py`, our ep21 points only):
  - 267 cap-in points, of which 2 lie in the lower 40 % of the height. So the floor = base + t (1.965 mm).
  - The pre-15:56 rule ("> 50 cap points → their 5th-percentile height") would put the floor 106.9 mm above the base.
  - With the fraction at 0.3, 0.5 or 0.6, 2 points qualify; at 0.8, 43 points (spread 21.7 mm). All are below 200, so
    the numbers do not bind; the structure does.
- **TIE** (`scripts/tiecheck.py`): 14 candidates. The pick is the best rotational-consistency axis (2.196 mm), for
  TIE 1.1, 1.25, 1.5 and 2.0.

### 3.4 Thickness

- Work log 27 Oct, "Leak, found by the rack auditor": `T_WALL` 2.5 mm equals the scan rack wall median; `T_LID` 2.5
  came from the same brief (scan lid 1.8).
- The clean-up round kept 2.5 as the midpoint of 1.5 / 2.5 / 4.0 and passed at all three [D].
- GT-free fidelity prefers the thinnest lid sheet, because the underside is unseen.
- The rack auditor [D]: "the floor top lands within about 0.2 mm of the scan".

### 3.5 Build records [M] (scratchpad)

- **Pot** (`prim/potlid/cand/white_pot_ep41_fit.json`):
  - t_meas 4.77 mm, with 24 two-wall bins;
  - handle: T 5.8 mm from side-seen points, no hole;
  - 5 accepted balls: 4 in prior mode (free 11.96 / 27.88 / 3.67 / 387 mm) and 1 free (6.94 mm).
- **Lid** (`prim/clean/lid/t2.5_fit.json`):
  - t 2.5 mm;
  - arch: T 3.0 mm from side-seen points, which is the clip floor; width 14.5 mm;
  - balls: free 7.35 mm, plus two prior 7.0 mm (free fits 8.99 and 322 mm).
- **Rack** (`prim/clean/rack/t2.5_lean1/plastic_dish_rack/joint.json`):
  - joint of episodes 12, 13 and 27;
  - s0 = 4.000 mm and s1 ≈ 0, both at their bounds;
  - cup holder: n_floor 43 (< 50), so h_cf = h_ft;
  - floor depth 33.2 mm;
  - balls kept: a 7.0 mm prior (free 9.51 mm, kept through spread 0.237) and a free 5.22 mm; 9 rejected by `in_basin`.
- **Cup:** `cdo_e0/prep/repro/cup.log` gives t 1.965 mm, open_top false, hfloor = t, 4 appendages. The
  `obs/ep21_blue_cup.npz` args show obs_points defaults with library_v3 ROI and pitcher others.
- **obs_all args:** all obs_points defaults, `--roi` library_v3, `--others` library_v3. Hands are absent for rack
  episodes 12 and 27.

### 3.6 Earlier audits used

- `results/autokit-stage1/research-workflow-result.json`: the "hand_constants" inventory. It lists values, but not
  their origins.
- `results/autokit-stage1/workflow-result.json`: blocker 1 (marker prior).
- `tasks/wsdspgfn2.output`: the primitive-round audits (potlid "soft priors"; rack "two scan-informed choices" and
  timeline).
- C0 `verify_0.md` B1, C0 `README.md` F1-F5, E0 `PREREG.md`.

## 4. Defects found in passing (not constants)

- `obs_fidelity.py`: the docstring advertises `--trim` and `--icp 1`. The code ignores both: trim is hard-coded to
  0.9, and there is no ICP.
- `lathe_obs.py`: `--spheres` is documented but never read.
- The `prim_rack.py` docstring still says markers use "the 7 mm prior from our own stereo" (lines 29-30). The
  `prim_potlid.py` docstring (lines 31-33) says the same; only line 67's comment was corrected.

## 5. All records

Generated by `scripts/audit_gen.py`, which also writes `AUDIT.json`. Columns: origin class, evidence, whether the
value changed the C0 mesh [M], and the action proposed for C0b. The actions are proposals for the C0b PREREG, not
decisions.

<!-- AUTO:TABLES -->
### prim_potlid.py

| # | file:line | name | value | controls | origin | evidence | binds in C0 [M] | C0b action |
|---|---|---|---|---|---|---|---|---|
| 1 | prim_potlid.py:56 | VOX | 1.5 mm | voxel downsample of observed points | G | sampling resolution, same in lathe_obs/prim_rack | yes (all) | keep |
| 2 | prim_potlid.py:57 | NSEC | 24 | azimuth sectors (profile, rim, lid tilt) | G | angular binning | yes | keep |
| 3 | prim_potlid.py:58 | MINSEC | 6 of 24 | sectors needed for a profile bin to count as body of revolution | O | set in lathe_obs 26 Oct 16:11 after printing per-height sector counts of OUR ep41 pot points (16:10:55); "a handle or a marker fills 1-3 of 24 sectors". the same loop also read scans (section 3.3), but the stated basis is our own points | yes | keep (flag loop) |
| 4 | prim_potlid.py:59 | MIN_PTS | 8 | points per (bin, sector) cell | G | minimum sample count | yes | keep |
| 5 | prim_potlid.py:60 | DPHI | 2 deg | polar-angle bin of the pot profile | G | binning | yes | keep |
| 6 | prim_potlid.py:61 | APP_D | 8 mm | residual threshold: points farther than this outside the body are handle/arch/marker candidates; also tsdf variant face cut, bar/arch exclusion band | U (U-suspect) | comment "stereo noise reaches 5-10 mm". The only noise figures on record before 27 Oct 04:19 are [D] obs-vs-scan percentiles (obs_diag: pot ep41 p90 6.6 / p95 8.7 mm; cup p95 4.9-7.3 mm, README sec. 4). No own-observation noise measurement predates it (the [M] handle-plane spread 5.6-9.3 mm is from 27 Oct 13:20, later) | yes (defines every residual set) | replace by an own-observation value (e.g. a high percentile of /obs-to-fitted-body/ distance on the episode) as an OPTION; or pre-register as a generic prior and test 2 values |
| 7 | prim_potlid.py:62 | CL_VOX | 3 mm | residual clustering voxel | G | connectivity resolution | yes | keep |
| 8 | prim_potlid.py:63 | MK_MIN | 60 points | minimum residual points for marker processing / cluster size | U | no derivation recorded | yes (gating) | superseded if gmg markers.py replaces markers_from; else flag |
| 9 | prim_potlid.py:64 | MK_DIAG | 6-35 mm (3-97 % bbox diagonal) | size window for a marker cluster | U (U-suspect) | no derivation; written in the same block as MK_R0 = 7 mm (scan-derived) and the brief's "~7 mm"; a 7 mm ball cap is 14-20 mm across | yes (many size rejections in pot/lid/rack records) | replace with gmg markers.py (PREREG A.6) or a declared generic window |
| 10 | prim_potlid.py:65 | MK_RES | 2 mm | sphere-fit median residual acceptance | U | no derivation recorded | yes (pot cluster rejected at 2.13 mm) | as MK_DIAG |
| 11 | prim_potlid.py:66 | MK_GAP | -3..+20 mm | ball surface to body/handle surface window (markers on short stems); also forces the prior radius when the free fit violates it | U | no derivation; stage-1 audit (27 Oct 17:20) asked to re-check its provenance (not done). Spoon template mount height 10.9 mm is scan-derived but is not this window | yes (gating + prior switch) | as MK_DIAG |
| 12 | prim_potlid.py:67 | MK_R0 | 7.0 mm | fixed ball radius used whenever the free sphere fit is rejected | S (S-value) | spoon/spoon_template.py:71 marker_radius 7.2 mm "note 17: fitted r 6.6-7.8 mm" = docs/research/notes/17 sec. A1 "Marker sphere catalogue from the scans"; stage-1 audit blocker 1 (work log 27 Oct ~17:20); comment fixed in 14eaf37; the brief called it "our own stereo" (false) | YES: pot 4 of 5 accepted balls at 7.00 (free fits 11.96, 27.88, 3.67, 387 mm replaced; verify_0 sees 3 as separate 7.00 mm bodies), lid 2 of 3 at 7.00 (one is the floating body), rack 1 of 2 at 7.00 (free fit 9.51 mm) | REPLACE (gmg markers.py free radius, or no balls) |
| 13 | prim_potlid.py:68 | MK_RMIN, MK_RMAX | 5.0-9.5 mm | free-fit radius acceptance window | S (S-value) | window around the scan catalogue 6.6-7.8 mm; stage-1 audit blocker 1 ("MK_R0 = 7 mm (and the 5-9.5 mm free-fit window) traces to the scans") | YES: free radii kept: pot 6.94, lid 7.35, rack 5.22 mm; free radii replaced by MK_R0: pot 11.96 / 27.88 / 3.67 / 387, lid 8.99 (gap) / 322, rack 9.51 mm | REPLACE (with MK_R0) |
| 14 | prim_potlid.py:69 | STEM_MIN | 15 points | points in the ball-to-surface gap needed for a stem | U | no derivation | gating only (no accepted C0 ball got a stem) | flag |
| 15 | prim_potlid.py:70 | STEM_R | 3.5 mm | stem cylinder radius; stem point count window STEM_R + 1.5 mm | U | no derivation; stage-1 audit asked to re-check (not done). Spoon template stem foot 5.5 mm (scan) differs | no geometry in C0 (no stems) | flag |
| 16 | prim_potlid.py:71 | T_MIN, T_MAX | 2-6 mm | clip of the measured pot wall thickness | U (U-suspect) | the potlid builder read the scan wall / bbox rows of README and the scan-profile figure before writing the code (section 3.1); brackets the scan pot wall 3.9 mm / brief "~4 mm"; potlid auditor noted it | no (C0 pot t_meas 4.77 mm, inside) | flag; replace by gmg thickness.py bounds or drop the clip as an OPTION |
| 17 | prim_potlid.py:405 | pot wall fallback | 4.0 mm | pot wall when < 3 profile bins see both walls | S (S-value) | equals the brief's "thin wall (~4 mm)" = scan pot wall 3.9 mm (README sec. 1); the potlid builder read the scan wall / bbox rows of README and the scan-profile figure before writing the code (section 3.1) | no (C0 pot: 24 two-wall bins) | REPLACE for eval builds (own thickness, gmg thickness.py) or fail the build instead of falling back |
| 18 | prim_potlid.py:72-75 | T_LID | 2.5 mm (env PRIM_T_LID) | lid sheet thickness: underside = top surface - T_LID (underside never observed) | S (S-value) | leak: first brief quoted scan walls (work log 27 Oct "Leak"; scan lid 1.8 mm); clean-up round kept 2.5 as grid midpoint of 1.5/2.5/4.0 (passed at all three [D]); GT-free fidelity prefers 1.5 (1.436 < 1.686 < 2.259 mm) because the underside is unseen | YES (C0 lid t_mm 2.5) | REPLACE (own-observation thickness, gmg thickness.py; or a pre-registered generic grid that must pass at every value) |
| 19 | prim_potlid.py:74 (comment), clean round | T_LID grid | 1.5 / 2.5 / 4.0 mm | sensitivity grid of the clean-up round | U (U-suspect) | declared "generic thin-moulding range not taken from any scan" (work log), but centred on the leaked 2.5 | n.a. (defines the verdict rule) | if reused, re-derive the grid without reference to 2.5 |
| 20 | prim_potlid.py:76 | BAR_T0 | 5 mm | handle / arch strap thickness when < 50 / 30 side-seen points | U | no derivation | no (pot T_src side 5.8 mm, lid T_src side) | flag |
| 21 | prim_potlid.py:77 | NSEG | 64 | revolve segments | G | tessellation | yes | keep |
| 22 | prim_potlid.py:124,145,169 | q=50; fill_smooth med 5 / avg 3; poly_dist step 0.5 mm | see value | per-cell median, gap fill + smoothing windows, polyline sampling | G | robust statistics / numerics | yes | keep |
| 23 | prim_potlid.py:186-199 | clusters() | 2-voxel pad, 1 dilation, 26-connectivity | residual clustering | G | numerics | yes | keep |
| 24 | prim_potlid.py:214,230 | sphere fit iterations | 10 GN (free), 15 (prior); prior start behind the cap | sphere fitting | G | numerics | yes | keep |
| 25 | prim_potlid.py:224 | free-fit acceptance | median res < 1.2 mm and spread > 0.08 | whether the free radius is kept | U | no derivation | yes (with MK_RMIN/MAX decides free vs prior) | replace with gmg markers.py rule |
| 26 | prim_potlid.py:257 | re-cluster height | APP_D + 4 mm (= 12 mm), level 0 only | splits oversize clusters into points standing high above the body | U | no derivation | yes (level-1 clusters in pot record) | flag |
| 27 | prim_potlid.py:275-288 | stem rule | gap > 3 mm; query 0.5 L + 5 mm; tp > r + 0.5 mm, < L - 3 mm; control offset 20 mm; n_stem >= 2 n_ctl; stem 2 mm into surface | stem evidence and geometry | U | no derivation (the 2 mm overlap is a union numeric, G) | gating only | flag |
| 28 | prim_potlid.py:303,311-317,336-352 | pot_axis search | 600 hemisphere directions; 20000 / 6000 subsamples (seed 0); top 3; local grids +-6 deg step 2, +-2 deg step 0.7 | pot axis search | G | numerics; design reason recorded as own observation ("fit_axis gave axes 5-36 deg apart on three episodes of the same pot; the rim term agreed") | yes | keep |
| 29 | prim_potlid.py:325,370-371 | open-end test | points with r < 0.4 R in the end 25 % of the height | which end is open (floor only at the closed end) | U | geometric heuristic, no derivation | yes (C0 pot axial counts 21897 vs 0: not close) | keep (insensitive here) |
| 30 | prim_potlid.py:329-331 | rim window | r in [0.6 R, R + 20 mm]; P98 per sector; >= 10 pts; >= 12 of 24 sectors | rim-flatness term of the axis score | U | no derivation; 20 mm absolute | yes (axis score) | flag |
| 31 | prim_potlid.py:363 | rot_consistency subsample | 20000, seed 1 | axis cost report | G | numerics | report only | keep |
| 32 | prim_potlid.py:367-369 | body extent | r < P60(r) + 20 mm; h P0.5/P99.5; Rb = P90(r) | pot body points for the extent / open-end test | U | no derivation; 20 mm absolute | yes | flag |
| 33 | prim_potlid.py:379 | hO | 0.6 x height | interior origin of the polar profile parameterization | U (U-suspect) | no derivation; the potlid builder read the scan wall / bbox rows of README and the scan-profile figure before writing the code (section 3.1) (the scan-profile figure was viewed before this design) | yes (profile geometry) | flag; insensitivity test is cheap (0.5 / 0.7) |
| 34 | prim_potlid.py:383,409 | view split; normal floor | /s/ > 0.3; cos floor 0.3 | outer- vs inner-seen classification; mid-surface offset guard | G | same 0.3 as lathe_obs; numerics | yes | keep |
| 35 | prim_potlid.py:390 | min profile bins | 10 | abort if fewer bins | G | sanity check | no | keep |
| 36 | prim_potlid.py:417-424 | rim height | points within 8 mm of the mid curve, r > 0.5 rmax, > 30 pts per sector, P99, median over sectors | pot rim cap height | U | no derivation (8 mm = APP_D) | yes (h_top 118.4 mm) | flag |
| 37 | prim_potlid.py:434,438 | resample; radius floor | 3 mm; 0.1 mm | profile resampling | G | numerics | yes | keep |
| 38 | prim_potlid.py:474-481 | bar top plane | top-seen view > 0.3 (else all if <= 50); 4 trimmed refits at 2.5 x 1.4826 MAD | handle top plane | G | robust statistics | yes | keep |
| 39 | prim_potlid.py:487-493 | bar width | 5 mm bins, >= 15 pts, P3-P97 lateral extent, P1-P99 length range, line fit if >= 4 bins | handle width and centre line | U | no derivation | yes (width 29.1 mm) | flag |
| 40 | prim_potlid.py:498-504 | bar thickness | side-seen /v.w/ > 0.5, > 50 pts; T = clip(2 x median depth, 3, 8 mm) | handle thickness | U | no derivation for the 3-8 mm clip | no (T 5.8 mm, inside) | flag |
| 41 | prim_potlid.py:505-512 | bar ends | tip P99.5; inner search from P0.5 - 60 mm, 400 steps; inner end where axis point radius < rmax - 2 t | handle length / attachment | U | no derivation | yes (length 172.3 mm) | flag |
| 42 | prim_potlid.py:519-541 | handle hole | > 200 top pts; 2 mm grid; 1 closing; area >= 40 mm^2; within 60 mm of the tip; /a/ < half width / 2 | whether a hole is cut | U | no derivation | yes (decided "no hole") | flag |
| 43 | prim_potlid.py:562 | thick variant | x 2.0 | variant "thick" (selection pool only) | G | sensitivity variant | no (fit selected) | keep |
| 44 | prim_potlid.py:571 | handle cluster size | >= 200 points | candidate handle clusters | U | no derivation | yes | flag |
| 45 | prim_potlid.py:577 | handle reach | P99 radius > rmax + 60 mm | which residual cluster is the handle | U (U-suspect) | no derivation; the brief gave the handle as ~17 cm (scan bbox 35.7 - 18.9 cm; section 3.1) | yes (picks the handle cluster; insensitive if the handle reaches ~170 mm) | flag; insensitivity test (40 / 80 mm) |
| 46 | prim_potlid.py:597-606, 818 | --lib (tsdf variant) | meshes/library_v3/<obj>.glb | tsdf variant appends library_v3 faces outside the body | S (S-input) | ops/provenance/denylist.json (mesh pipeline v5 spec 3.2) lists meshes/library_v3/*; ledger sec. 1 and 6 | no (fit selected), but tsdf candidates were in the pot (8) and lid (1 per T) selection pools | drop the tsdf variant in C0b (or document) |
| 47 | prim_potlid.py:615-624 | lid dome | dr 2 mm; quadratic h = a + b r^2 fitted on r 15-35 mm, used for r < 15 mm, >= 4 bins | lid top profile under the arch | U (U-suspect) | lid-specific absolute window; no derivation; brief carried scan lid size ("~19 cm across"); potlid auditor judged it "chosen from our own points" (judgement, no record) | yes (dome 4.4 mm) | flag; express relative to r_edge as an OPTION |
| 48 | prim_potlid.py:632-634 | lid up direction | smallest PCA axis, sign towards the cameras | lid normal | O | underside never seen (clean-up PREREG: median /view.axis/ = 0.78 at the edge) | yes | keep |
| 49 | prim_potlid.py:637-649 | lid centre | 36 sectors; > 50 pts; P98 radius; 3 mm band; 3 circle-fit iterations | lid centre | G | robust geometry | yes | keep |
| 50 | prim_potlid.py:652-654 | lid flange window | r 40-80 mm; /h - median/ < 6 mm | points used to re-fit the disc normal | U (U-suspect) | lid-specific absolute window (r_edge 91 mm); brief carried scan lid size; no derivation | yes (axis) | flag; relative-to-r_edge OPTION |
| 51 | prim_potlid.py:663-683 | lid tilt refinement | r bins 2 mm / 4 mm; surface +-4 mm; R_hi = P98 - 2 mm; r > 20 mm; >= MIN_PTS; 3 iterations | lid axis tilt | U | no derivation for the absolute 20 mm / 4 mm values | yes (final tilt 0.023 deg) | flag |
| 52 | prim_potlid.py:689-697 | lid top surface | SURF_D 4 mm (two passes); fill_smooth(3, 3); r_edge = median per-sector P99.5 (> 30 pts) | top surface and edge radius | U | SURF_D no derivation; rest robust statistics | yes (r_edge 91.0 mm) | flag |
| 53 | prim_potlid.py:702 | lid resample | 3 mm | profile resampling | G | numerics | yes | keep |
| 54 | prim_potlid.py:718 | lid residual radius | r < r_edge + 15 mm | residual region (arch, markers) | U | no derivation | yes | flag |
| 55 | prim_potlid.py:728-735 | arch detector | cluster >= 100 pts; in-plane extent > 50 mm | which residual cluster is the arch | U (U-suspect) | lid-specific; no derivation | yes (arch span 99 mm) | flag |
| 56 | prim_potlid.py:755-764 | arch sampling | top > 0.3, side > 0.5; 3 mm bins; >= 8 top pts; P75 height; P3-P97 width | arch top curve and width | U | no derivation (P75 choice) | yes | flag |
| 57 | prim_potlid.py:766 | arch width clip | 8-30 mm | strap width | U | no derivation | no (14.5 mm) | flag |
| 58 | prim_potlid.py:770-775 | arch thickness | hi part > P50(H); > 30 side pts; T = clip(2 x median depth, 3, 8 mm); else BAR_T0 | strap thickness | U | no derivation for the 3-8 mm clip | YES: C0 lid arch T = 3.0 mm = the lower clip | flag: the clip floor decides the strap thickness; measure unclipped value or pre-register the bound |
| 59 | prim_potlid.py:776-784 | arch smoothing / ends | median 3 + mean 3; ends extended 4 mm and run to the sheet mid-surface; resample 2 mm; 4000 samples for the exclusion tree | strap geometry | G | numerics; the mid-surface attachment is geometric (clean-up bug fix) | yes | keep |
| 60 | prim_potlid.py:817 | --variant default | fit | variant | G | default | yes | keep |

### prim_rack.py

| # | file:line | name | value | controls | origin | evidence | binds in C0 [M] | C0b action |
|---|---|---|---|---|---|---|---|---|
| 61 | prim_rack.py:63 | VOX | 1.5 mm | voxel downsample | G | numerics | yes | keep |
| 62 | prim_rack.py:64 | T_WALL | 2.5 mm (env PRIM_T_WALL) | floor plate thickness; cup-holder wall (inner/rim targets -T, -T/2); xa = xl - T; floor depth = max lip-above-cut + band - T; cavity inset | S (S-value) | equals the scan rack wall median (README sec. 1 "rack 2.5 mm" [D], scripts/scan_stats.py) passed in the brief ("fins ~2.5 mm thick"); rack auditor: "the floor top lands within about 0.2 mm of the scan"; clean-up kept 2.5 as grid midpoint (passed 1.5 / 2.5 / 4.0 [D]) | YES (h_tab, h_ft, cup wall, cavity) | REPLACE (own-observation thickness; floor never seen -> pre-registered generic grid or gmg thickness.py) |
| 63 | prim_rack.py:65 | CELL | 10 mm | lower-envelope cell for the table-cut plane | G | numerics | yes | keep |
| 64 | prim_rack.py:66 | VR | 0.25 | in-plane view component deciding outer- vs inner-seen | G | view-geometry threshold (0.3 in lathe_obs) | yes | keep |
| 65 | prim_rack.py:67 | F_SCALE | 2 mm | soft_l1 robust loss scale | U | audit note "about stereo noise"; no own measurement recorded | yes (all LSQ fits) | flag |
| 66 | prim_rack.py:68 | PEG_SLICE | 12-35 mm above the cut | peg detection slice | U | rack-specific; written 05:22 before any scan score; no derivation | yes (2 rows, 7 + 6 pegs) | flag |
| 67 | prim_rack.py:69 | PEG_R | 14 mm | peg point radius around a centre | U | as PEG_SLICE | yes | flag |
| 68 | prim_rack.py:70 | PEG_H0 | 2 mm | lowest peg knot | G | numerics | yes | keep |
| 69 | prim_rack.py:71 | PEG_KAPPA | 1.0 (round) | peg depth/width ratio; back of a peg never seen | U | shape prior; set 05:43 before any scan score; "a free depth/width ratio ... was unstable across episodes" (own observation of instability, not of the value) | YES (round pegs) | flag (prior on unseen shape) |
| 70 | prim_rack.py:72 | PEG_LEAN | False (upright) | peg lean | O | "a free lean came out 0.04-0.4 (2-22 deg) between episodes and rows (stereo smear)" - own points, 05:46, before any scan score | YES (lean 0) | keep |
| 71 | prim_rack.py:74 | APP_D | 8 mm | marker residual | U (U-suspect) | copy of prim_potlid APP_D (see there) | yes | as prim_potlid APP_D |
| 72 | prim_rack.py:75 | MK_FREE_R | 4-12 mm | free-fit radius that counts as a ball cap (marker_parts) | U (U-suspect) | added 05:30 (pre-scan-score); window around the 7 mm prior the brief supplied; no derivation | yes (with MK_SPREAD) | replace with gmg markers.py |
| 73 | prim_rack.py:76 | MK_SPREAD | 0.05 | or a cap this curved | U | no derivation | YES: the 9.51 mm ball (free_res 1.55 > 1.2) is kept only through spread 0.237 >= 0.05 | replace with gmg markers.py |
| 74 | prim_rack.py:77 | SEG | 6 | segments per rounded corner | G | tessellation | yes | keep |
| 75 | prim_rack.py:78 | S0_MIN | 4 mm | lower bound of the lip width s0 | O | comment: "the lip tops seen from above span ~7-9 mm" (own points, 05:48, before any scan score); the 4 mm itself is an unexplained margin below that | YES: C0 s0 = 4.000 mm (at the bound) | flag: the bound decides the lip width |
| 76 | prim_rack.py:79-82 | CUP_LEAN | True (env PRIM_CUP_LEAN=1) | cup-holder lean and draft free (linear in h) | O | clean-up round: GT-free fidelity preferred lean at every T_WALL (6.044/5.935/5.921 vs 6.242/6.116/6.138 mm); the alternative False was S-dev (set after diag_regions [D], the rack builder saw scan scores at 05:51 and a scan cup-holder / floor printout at 05:52-05:53 (section 3.1)) | yes (ux -0.052, uy 0.157) | keep |
| 77 | prim_rack.py:324-357 | cup_upright() | band H_r + 5 mm .. top - 5 mm; /n/ > 0.8; >30 pts; r search 4 mm step 2 mm; error cap 4 mm, window 12 mm | upright cup estimator (only when CUP_LEAN False) | S (S-dev) | written 05:54-05:57 right after the scan cup-holder extents were printed (the rack builder saw scan scores at 05:51 and a scan cup-holder / floor printout at 05:52-05:53 (section 3.1)) | no (C0 uses lean) | leave unused; never select it |
| 78 | prim_rack.py:83 | JOINT_TOL | 1.25 | episodes enter the joint fit if own full-fit fidelity <= 1.25 x best | U | set 05:46 before any scan score; no derivation | YES (joint = eps 12, 13, 27; first run ep26 7.802 vs cut 7.759) | flag; sensitivity is real (ep26 near the cut) |
| 79 | prim_rack.py:91 | band fallback | 8 mm | table band if the npz has no args | G | mirrors the obs_points default | no (args present) | keep |
| 80 | prim_rack.py:98-120 | lower_plane | P2 per cell; >= 20 pts/cell; lowest 30 % + 3 mm; 10 refits; 4 iterations | table-cut plane | U | robust-estimation choices; 30 % / 3 mm no derivation | yes | flag (low risk) |
| 81 | prim_rack.py:136-137 | joint offset | P2 per cell, P15 of the cell lows | cut offset under a fixed normal (joint fit) | U | no derivation | yes (joint) | flag (low risk) |
| 82 | prim_rack.py:197-201 | find_cup | tall = h > 0.65 x P99.8; P1/P99; P0.5/P99.5 | which end holds the cup holder | U | rack-specific; no derivation | yes (insensitive: cup holder is the only tall part) | keep |
| 83 | prim_rack.py:204-238 | lip sampling | 12 mm edge bands; 10 mm segments; >= 50 / >= 30 pts; P98 height; plane: 5 iterations, 3 mm inliers | lip-top samples and lip plane | U | no derivation | yes (78 segments, sd 1.0 mm) | flag |
| 84 | prim_rack.py:247-249 | outline init | x > x0 + 30 mm; init rc 15 mm, s0 8 mm, s1 0.3 | tray outline start values | U | init only; s0 8 mm matches the own-observed 7-9 mm lip | init only | keep |
| 85 | prim_rack.py:264-267 | outline point classes | near band -35..+15 mm; outer h 3 mm..H_r - 6 mm, /res/ < 8 mm; inner h > 6 mm; lip H_r - 3..+4 mm, sd -20..+6 mm | which points enter the outline LSQ | U | no derivation | yes (21701 / 25541 / 9789 points) | flag |
| 86 | prim_rack.py:271,309,453 | LSQ subsamples | 60000 / 60000 / 40000, seeds it / it / 0 | subsampling | G | numerics | yes | keep |
| 87 | prim_rack.py:279-280 | outline bounds | theta +-0.2 rad; so1 -0.3..1; hy 30-150 mm; rc 2-60 mm; s0 S0_MIN..30 mm; s1 0..1.5 | tray outline parameter bounds | U | rack-size bounds, no derivation; brief carried the scan rack size (51 x 18 x 12 cm) | YES: s0 at 4 mm and s1 at 0 (bounds); others interior | flag (s1 = 0 means the sloped inner face is not identified) |
| 88 | prim_rack.py:297-306 | cup point classes | /sd/ < 12 mm; h < top + 4 mm; upper h > H_r + 4 mm; /n.up/ < 0.7; outer sd > -6 mm; inner sd < 3 mm; below-lip inner from iteration 2: h > h_ft + 4 mm, -T_WALL - 8 mm < sd < -T_WALL + 3 mm; rim h >= top - 3 mm | cup-holder LSQ classes | U | no derivation; inner class tied to T_WALL | yes (32754 points) | flag; T_WALL part replaced with T_WALL |
| 89 | prim_rack.py:316-318 | cup bounds | lean/draft +-0.25; ex 10-80 mm; ey 10-120 mm; r 4-50 mm | cup-holder parameter bounds | U | rack-size bounds, no derivation | no (C0 values interior) | flag |
| 90 | prim_rack.py:363-370 | cup region / top | x < xr + 12 mm; top = median over 2 cm y-bands of P99 (> 30 pts above H_r); tall h > H_r + 10 mm; init r 20 mm | cup-holder region and top | U | no derivation | yes (top 105.1 mm) | flag |
| 91 | prim_rack.py:382-383 | cup inner floor | sd < -T_WALL - 4 mm; n.up > 0.85; h_ft < h < H_r; >= 50 pts else tray floor h_ft | cup-holder inner floor | U | no derivation | YES: n_floor 43 < 50 -> h_cf = h_ft (tray floor, which depends on T_WALL) | flag |
| 92 | prim_rack.py:391-418 | detect_pegs | 2 mm grid; >= 3 pts/cell; closing; blobs 10-150 cells; >= 100 slice pts; rows dy < 12 mm; >= 3 pegs | peg centres and rows | U | rack-specific; no derivation | yes | flag |
| 93 | prim_rack.py:421-475 | fit_peg_row | knots every 6 mm; query PEG_R + 4 / + 30 mm; >= 200 pts; P99 tops (> 30 pts); init a 6 mm; a 1-20 mm (floor 0.8 mm); centres +-8 mm; 2 rounds | peg template | U | no derivation | yes (a 9.4 -> 3.4 mm, H_p 51 / 48 mm) | flag |
| 94 | prim_rack.py:607 | normals k | 24 | PCA normals | G | numerics | yes | keep |
| 95 | prim_rack.py:608-613 | tray x0 offsets | H_r and lip plane from x > xh + 15 mm; outline from x > xh + 10 mm (+30 mm inside fit_outline) | where the tray starts | U | no derivation | yes | flag |
| 96 | prim_rack.py:626-627, 803 | floor placement | h_ft = H_r - depth; depth = max over episodes of lip-above-cut + band - T_WALL; h_tab = h_ft - T_WALL | never-seen floor | O | geometric: no floor point is ever seen, the floor lies under the deepest cut (band = obs_points table_band); the T_WALL terms are S-value (see T_WALL) | YES (depth 33.2 mm) | keep rule; replace T_WALL |
| 97 | prim_rack.py:636-642 | peg gates | inside: sd < -(s(h) + 10 mm) and x > cup face + 6 mm; ok: inside or h > H_r + 2 mm; row kept only if H_p > H_r + 8 mm | which blobs are pegs | U | no derivation | yes | flag |
| 98 | prim_rack.py:505-538 | build_body | so1 floor -0.2; basin top H_r + 10 mm; inset radius floor 2 mm; cavity top + 10 mm; peg base h_ft - 1 mm; peg ring 16 segments, radius floor 0.8 mm | solid construction | G | construction numerics (overlaps for the union) | yes | keep |
| 99 | prim_rack.py:573-582 | marker_parts | free_r in MK_FREE_R and free_res <= 1.2 mm, or spread >= MK_SPREAD; sphere 20 segments | cap evidence for accepted balls | U (U-suspect) | see MK_FREE_R | yes | replace with gmg markers.py |
| 100 | prim_rack.py:666-669 | rack residual | 200000 surface samples (seed 0); outside and d > APP_D | marker residual set | G | numerics (APP_D see above) | yes | keep |
| 101 | prim_rack.py:675-682 | in_basin rule | reject a ball whose centre is inside the inner face (sd < -s0) and right of the cup face | markers over the basin are treated as residuals | U (U-suspect) | added 06:03 after the first scan scores (05:51) and the [D] region diagnostic (05:52-05:53); stated reason GT-free ("after seeing 8 balls"); rack auditor: GT-free fidelity preferred the version without it (6.089 vs 6.116 mm), [D] it traded ADD 5.9 -> 6.4 for CD-O 0.463 -> 0.454 | YES: 9 candidate balls rejected in the C0 joint record (2 kept) | flag; decide in the C0b PREREG with a GT-free reason, or test both by fidelity |
| 102 | prim_rack.py:703-721 | icp_align | 30 iterations; trim P80; stop /t/ < 1e-6 m | joint episode alignment | G | numerics | yes (12/13/27 aligned, <= 0.6 deg) | keep |
| 103 | prim_rack.py:748-751 | joint reference | episode with most points; 60000 subsamples (seed 0); up = mean of aligned cut normals | joint fit frame | G | numerics / geometry | yes | keep |
| 104 | prim_rack.py:841 | rack selection | min fid_sum over 12 candidates | GT-free pick (pre-registered 27 Oct) | O | obs_fidelity on our points | yes (joint) | keep |
| 105 | prim_rack.py:865 | --episodes default | 12,13,26,27,31 | public rack episodes | G | all public rack episodes | yes | eval list for E0b |

### lathe_obs.py

| # | file:line | name | value | controls | origin | evidence | binds in C0 [M] | C0b action |
|---|---|---|---|---|---|---|---|---|
| 106 | lathe_obs.py:27, 205 | DH (--dh) | 3 mm | height bin | G | binning | yes | keep |
| 107 | lathe_obs.py:28, 150-153 | TIE | 1.25 | axis candidates within 1.25 x best rotational consistency are near-ties; the one closest to the opening direction wins | U (U-suspect) | set 16:08:59 inside the scan-scored loop (lathe_obs scan-scored development loop, 26 Oct 15:51-16:12 (section 3.3)); no derivation | no [M]: for the C0 cup the pick is the best-consistency axis itself (2.196 mm); TIE 1.1 / 1.5 / 2.0 give the same axis (scripts/tiecheck.py) | keep (shown not binding); flag |
| 108 | lathe_obs.py:29 | NSEC | 24 | sectors | G | binning | yes | keep |
| 109 | lathe_obs.py:46, 206 | sector_stat q / --min_pts | 50 / 8 | per-cell median, min points | G | statistics | yes | keep |
| 110 | lathe_obs.py:60, 207 | normals k (--knn) | 24 | PCA normals | G | numerics | yes | keep |
| 111 | lathe_obs.py:82-95 | IRLS | Cauchy scale 1.5 x median /res/ (over w > 5 % of max), floor 0.1 mm; 8 / 6 iterations | line-complex axis fit | G | robust statistics (Pottmann & Randrup line complex) | yes | keep |
| 112 | lathe_obs.py:99 | rot_consistency | angles 45/90/135 deg; trim 0.8 | axis score | G | numerics | yes | keep |
| 113 | lathe_obs.py:114-141 | fit_axis candidates | 6 k-means clusters (seed 0), > 500 pts; inside-facing > 100 pts; 20000 subsample (seed 1) | axis candidate set | G | numerics | yes (14 candidates) | keep |
| 114 | lathe_obs.py:157 | smooth_fill win | 5 bins | profile gap fill + median | G | numerics | yes | keep |
| 115 | lathe_obs.py:166 | revolve nseg | 96 | tessellation | G | numerics | yes | keep |
| 116 | lathe_obs.py:197 | --solid | 0 | hollow lathe | O | thin walls seen from both sides (inner/outer classes) | yes | keep |
| 117 | lathe_obs.py:198, 290-293 | --app_d | 4 mm | points beyond the profile by > 4 mm are appendage points | U | no derivation; differs from prim_potlid APP_D 8 mm | YES (3372 appendage points -> 4 parts) | flag; own-noise-based OPTION as for APP_D |
| 118 | lathe_obs.py:199, 306 | --app_min | 400 points | minimum appendage group | U | no derivation | yes | flag |
| 119 | lathe_obs.py:199 | --spheres | 0 | documented "fit markers as spheres" option; never read by the code (dead flag) | G | code defect, no effect | no | note |
| 120 | lathe_obs.py:200, 212 | --vox_ds | 1.5 mm | voxel downsample | G | numerics | yes | keep |
| 121 | lathe_obs.py:200, 245, 249 | --tmin | 1.5 mm | lower bound of the wall t; inner radius <= outer - tmin | U (U-suspect) | written 15:51 after scan_stats.py (15:33) showed scan walls 1.8-3.9 mm; no derivation | no for t (C0 t_meas 1.965 mm); the ri <= ro - tmin clamp not measured | flag; own-noise-based lower bound OPTION |
| 122 | lathe_obs.py:201-203 | --floor / --gap | base / 3 | "observed" mode: cavity only as deep as the inner wall was seen ("a scanner sees about as far in") | S (S-dev) | added 16:00:27 together with area_prof.py [D] on the scan; default stays base | no (default base) | never select "observed" in C0b |
| 123 | lathe_obs.py:204, 229-230 | --minsec | 6 | sectors needed per height bin | O | see prim_potlid MINSEC (same 16:11 edit, own sector counts) | yes | keep (flag loop) |
| 124 | lathe_obs.py:215 | axis subsample | 60000 (seed 0) | points for fit_axis | G | numerics | yes | keep |
| 125 | lathe_obs.py:222 | view split | /vr/ > 0.3 | outer/inner/cap classes | G | view geometry | yes | keep |
| 126 | lathe_obs.py:236-237 | body extent | r < max r_out + 5 mm; P0.5 / P99.5 of h | axial extent excluding the handle | O | same 16:11 edit, motivated by own pot sector table; 5 mm margin no derivation | yes (height 163.6 mm) | keep (flag) |
| 127 | lathe_obs.py:240 | open-end vote | >= 50 % of inner-wall bins above mid-height | which end is open | G | majority vote | yes (open_top false -> flipped) | keep |
| 128 | lathe_obs.py:244 | wall fallback | 3 mm when < 3 two-wall bins | wall thickness without evidence | S (S-value) | docstring of the same 15:51 write: "the TSDF mesher turns the 3 mm walls into 12-20 mm slabs" - the 3 mm walls are the scan walls measured 15:33 (cups 2.4-3.2 mm, README sec. 1) | no (C0 cup: 33 two-wall bins, t 1.965 mm) | REPLACE for eval builds (own thickness or fail) |
| 129 | lathe_obs.py:246-249 | profile smoothing | smooth_fill on outer / inner; ri = min(.., ro - tmin) | profiles | G | numerics | yes | keep |
| 130 | lathe_obs.py:251 | cap-in margin | r < ri - 3 mm | cap points inside the cavity (floor evidence) | U | no derivation | yes (267 points) | flag |
| 131 | lathe_obs.py:252-259 | floor rule | floor raised only by a dense (> 200 pts) thin (q90 - q10 < 10 mm) layer in the lower 40 % of the height; else floor = base + t | cavity depth | S (S-dev) | introduced 15:56:38, 54 s after a [D] plot of the scan section over the a0 lathe (prof_plot2.py 15:55:44) and after a0/a1 scan scores (15:54); replaced "any > 50 cap points -> P5 height" (lathe_obs scan-scored development loop, 26 Oct 15:51-16:12 (section 3.3)) | YES in structure [M, scripts/floorcheck.py]: C0 cup floor = base + t; the pre-15:56 rule would put the floor 106.9 mm above the base. The numbers do not bind: fractions 0.3-0.6 keep 2 points, 0.8 keeps 43, all < 200 | decide in the C0b PREREG: keep the rule with a GT-free reason (a cup has a floor ~t thick; sparse cap points are not a floor) and record its S-dev origin; or flag the cup |
| 132 | lathe_obs.py:296-310 | appendage splat | 2 mm voxels; pad 3; dilation 1; closing 2; Gaussian 0.7 voxel; iso 0.5 | appendage meshes | U | no derivation for the morphology | YES (4 appendage bodies) | flag |

### obs_points.py

| # | file:line | name | value | controls | origin | evidence | binds in C0 [M] | C0b action |
|---|---|---|---|---|---|---|---|---|
| 133 | obs_points.py:32, 56 | --roi | meshes/library_v3/<obj>.glb (bounds + margin) | box that crops the depth samples | S (S-input) | ops/provenance/denylist.json (mesh pipeline v5 spec 3.2) lists meshes/library_v3/*; ledger sec. 1 and 6; docstring: "any mesh of ours or a box size works" | yes (box only; cuts nothing of the object if the library mesh is about the right size - not measured) | REPLACE: a fixed box around the track origin (recon_mesh uses +-30 cm) or a box from our own detection |
| 134 | obs_points.py:33, 50-55, 106-110 | --others | meshes/library_v3/<other>.glb posed by our tracks | drops samples within other_r of a co-object | S (S-input) | ops/provenance/denylist.json (mesh pipeline v5 spec 3.2) lists meshes/library_v3/*; ledger sec. 1 and 6 | yes: lid ep2 (pot), rack ep12/13 (blue cup), rack ep27 (pot), cup ep21 (pitcher); pot ep41 none | REPLACE: co-objects from our own points (gmg extract_joint ownership) or C0b meshes; or drop |
| 135 | obs_points.py:33 | --other_r | 12 mm | co-object exclusion radius | U | recon_mesh v1 (21 Oct, f9e04f2) default; v1 posed the SCANS as others; value never derived | yes (lid next to pot) | flag |
| 136 | obs_points.py:34 | --stride | 2 | frame stride | G | compute | yes | keep |
| 137 | obs_points.py:34, 56 | --margin | 20 mm | ROI margin | G | box padding | yes | keep (with a new ROI) |
| 138 | obs_points.py:35, 64, 70 | --edge_thr | 20 mm (5 x 5 max - min) | depth-edge (flying pixel) filter | U | recon_mesh v4 (21 Oct): value set once; switching it on/off was judged by registered AUC with the scans [D] ("mixed") | yes | flag (low risk) |
| 139 | obs_points.py:35, 84 | --zmax; depth > 5 cm | 1.5 m; 0.05 m | valid depth range | G | sensor range | yes | keep |
| 140 | obs_points.py:36, 99, 129 | --table_band | 8 mm | samples within 8 mm above the table plane are dropped (bottom 8 mm of a resting object is never seen) | U (U-suspect) | obs_points written 26 Oct 15:41, 8 min after scan_stats.py; recon_mesh uses 15 mm; no derivation for 8. prim_rack places the table at -band (exact whatever the value); lathe_obs / prim_potlid bases sit at the lowest observed point | yes (cut height of resting objects; rack floor depth includes it) | flag; pre-register; test 2 values |
| 141 | obs_points.py:37-38 | --hand_r, --arm_r, --arm_len | 30 mm, 45 mm, 150 mm | hand-bone and forearm capsules that drop samples | G | body-scale priors (recon_mesh v0, 21 Oct); the scans contain no hands, so no scan origin is possible | yes (where hands exist; rack ep12/27 have none) | keep |
| 142 | obs_points.py:39-41 | --vox, --hit, --free, --min_hits, --min_ratio | 4 mm, 4 mm, 10 mm, 3, 0.5 | free-space vote: keep samples whose voxel was hit >= 3 times and >= 50 % of hits+free | U | no derivation (4 mm mirrors the TSDF voxel; 10 mm ~ the 12 mm truncation) | yes (cup kept 93 %) | flag (low risk) |
| 143 | obs_points.py:42 | --pix_stride | 1 | pixel stride | G | compute | yes | keep |
| 144 | obs_points.py:75 | ROI near camera | skip frame if a box corner is < 5 cm in front of the camera | projection guard | G | numerics | rare | keep |
| 145 | obs_points.py:87-96 | per-frame table refit | inliers within 30 mm then 12 mm; >= 500 samples; subsample to 20000; accept if within 10 deg | table plane per frame | U | recon_mesh v2 (21 Oct) fix for the ep39 dust pan, developed in a loop scored by registered AUC with the scans [D]; values set once | yes | flag (low risk) |

### pipeline/recon_mesh.py (helpers used by obs_points.py)

| # | file:line | name | value | controls | origin | evidence | binds in C0 [M] | C0b action |
|---|---|---|---|---|---|---|---|---|
| 146 | recon_mesh.py:20-30 | rectified_K | input 1280 x 800; output 1600 x 1000; alpha 0; CALIB_ZERO_DISPARITY; ego_cam_c / ego_cam_b | rectified intrinsics matching the depth cache | G | dataset calibration + rectification convention of the depth cache | yes | keep |
| 147 | recon_mesh.py:33-56 | hand_segments | MediaPipe 21-joint bones; forearm from the wrist away from the middle knuckle (J0 - J9) | hand capsule geometry | G | hand model topology | yes | keep |
| 148 | recon_mesh.py:58-67 | table_plane sampling | every 4th pixel; depth 0.2-1.5 m; 1500 RANSAC iterations; seed 0; least-squares refit | frame-0 support plane | G | numerics / sensor range | yes | keep |
| 149 | recon_mesh.py:58 | table_plane thr | 6 mm | RANSAC inlier distance | U | recon_mesh v0 (85fbda1) default; no derivation | yes | flag (low risk) |
| 150 | recon_mesh.py:58 | table_plane hmin, hmax | -5 cm .. +30 cm under the object origin | which plane may be the table | O | docstring: the floor (~1 m down) was otherwise picked (2026-10-20 mkref bug) | yes | keep |
| 151 | recon_mesh.py:58 | table_plane cone | 65 deg from camera up | admissible table normals | O | 45 -> 65 on 21 Oct (3946ba2): "the table normal is 48-50 deg from camera up in ep39/ep40" (own measurement; the failure was found through scan scoring) | yes | keep |

### obs_fidelity.py

| # | file:line | name | value | controls | origin | evidence | binds in C0 [M] | C0b action |
|---|---|---|---|---|---|---|---|---|
| 152 | obs_fidelity.py:11 | trim | 0.9 (hard-coded; --trim ignored) | trimmed mean in both directions | G | robust statistic; set once (26 Oct 16:28) | yes (every selection) | keep; fix docstring (--trim, --icp are not implemented) |
| 153 | obs_fidelity.py:13, 19 | samples | 300 k observed points (seed 0); 200 k mesh samples (seed 0) | fidelity sampling | G | numerics | yes | keep |
| 154 | obs_fidelity.py:14, 21 | AABB gate | mesh samples inside the observations' bounding box | mesh->obs counts only where we looked | G | design | yes | keep |
| 155 | obs_fidelity.py:whole file | selector design (blue cup) | sum of the two trimmed means; lowest wins | blue-cup episode / variant pick | S (S-dev) | written 26 Oct 16:28, after the five blue-cup lathes were scored on the scan; it picks the CD-O winner (README sec. 4; C0 flag F3). For pot, lid, rack the same selector was pre-registered on 27 Oct before their scorings | yes (picked ep21 g1) | C0b: pre-register the selection (as the brief says) |

### C0 command lines and inputs

| # | file:line | name | value | controls | origin | evidence | binds in C0 [M] | C0b action |
|---|---|---|---|---|---|---|---|---|
| 156 | run_fit.sh, select.py:- | pot build + pick | prim_potlid.py pot obs_all/ep41_white_pot.npz --variant fit --lib library_v3/white_pot.glb --axis_cache ...; pick = min obs_fidelity sum over 32 candidates (8 episodes x fit/nostem/tsdf/thick) on all 8 episodes' points | C0 pot | O | pre-registered 27 Oct (work log); ep41 fit 3.035 vs ep41 tsdf 3.044 mm (margin 0.009 mm) | yes | C0b: same rule, without the tsdf variant if library_v3 is dropped |
| 157 | clean (work log 27 Oct):- | lid build + pick | PRIM_T_LID=0.0025 prim_potlid.py lid obs_all/ep2_white_pot_lid.npz --variant fit --lib library_v3/white_pot_lid.glb; fit vs tsdf by fidelity (1.686 vs 1.913 mm) | C0 lid | S (S-value) | the env value is T_LID (see there); variant pick is O | yes | REPLACE T_LID |
| 158 | run_rack.sh:- | rack build + pick | PRIM_T_WALL=0.0025 PRIM_CUP_LEAN=1 prim_rack.py run --obs_dir obs_all --out ... (episodes 12,13,26,27,31); pick = joint (fid 5.935 mm); lean chosen by fidelity | C0 rack | S (S-value) | the env value is T_WALL (see there); lean and variant picks are O | yes | REPLACE T_WALL |
| 159 | NOTES.md 15:27; E0 NOTES 16:24:- | blue-cup build | lathe_obs.py obs/ep21_blue_cup.npz (all defaults = g1), byte-identical rebuild [M] | C0 cup | O | defaults audited above | yes | see lathe_obs rows |
| 160 | prep_obs.sh; obs npz args:- | obs_points command lines | all obs_points defaults (stride 2, vox 4 mm, hit 4 mm, free 10 mm, table_band 8 mm, other_r 12 mm, edge 20 mm, hands 30/45/150 mm, margin 20 mm); --roi/--others library_v3 | C0 observed points | S (S-input) | npz "args" of obs_all/ep41_white_pot, ep2_white_pot_lid, ep12/13/27_plastic_dish_rack and obs/ep21_blue_cup [M] | yes | see obs_points rows |
| 161 | ep21 args:- | tracks (--poses) | pot/lid/rack: store run 20261025-sweep-a894083 base tracks; cup: data/store/ep21 perc2m own-mesh tracks; eval (E0): 20261025-evperc-4f596df | object frame of the observed points | U | perception seeded with our library meshes (library_v2/v3 = tier P1, ledger sec. 1); not a scan read, but the library itself was fused along scan-templated tracks (C0 flag F4, open organiser question). Needed: the pack poses are these tracks | yes (frame) | owner/organiser question F4; not a constant |
| 162 | prep_obs.sh:- | hands | G1 refs (store 20261025-g1-022fece) MediaPipe hands.npz where stored; none for rack ep12/27 | hand capsules | G | MediaPipe on our video | yes | keep |
| 163 | mesh_budget.py:- | budget_mesh | 4096 faces, 4096 vertices (fast_simplification 0.2.0) | packing decimation | G | organiser kit | yes (packing) | keep |
<!-- /AUTO:TABLES -->

## 6. Limits

- **"Binds" was checked only on the C0 build records.** Eval builds (E0/E0b) can hit fallbacks and bounds that C0 did
  not hit, e.g. the 4 mm and 3 mm wall fallbacks, or the `T_MIN`/`T_MAX` clip.
- **Not re-run:**
  - the ROI box's effect: whether library_v3 bounds + 20 mm crop any object point;
  - the `ri ≤ ro - tmin` clamp on the cup;
  - the insensitivity tests suggested for `hO`, handle reach and `APP_D`.

  Each is a cheap, GT-free run.
- **`mesh_metric.py`** reads the scans by design. It is scoring, not construction, so its constants are outside this
  audit.
- **Out of scope:** gmg `markers.py` and `thickness.py`, the proposed replacements, have their own origin column in
  gmg PREREG A.6 and B7/B2 notes, and were not re-audited here.
