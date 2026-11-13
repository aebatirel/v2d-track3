# C0b / E0b verify_1: frame, kit and bytes

- **When and where.** 2026-10-31, 22:29-23:40 UTC, on the shared cloud VM (4 cores, load 3-14 from other jobs; my
  jobs at nice 19, one thread each). CPU only, $0.
- **Lens.** FRAME, KIT, BYTES:
  - frame of every shipped E0b mesh and every C0b pick against library_v3, with no registration and with rigid ICP;
  - the kit's `budget_mesh` result (faces, vertices, watertight, bodies) for the same meshes;
  - byte identity of `meshes/library_e0b` and `meshes/library_e0bx` against `MANIFEST_E0b.json`;
  - marker-ball radii measured on the shipped files against the `markers.py` detections;
  - whether library_e0b differs from library_v3 only in the adopted objects.
- **Inputs.** The repo at `9d644e4` (E0b final) and the pulled E0b box tree
  `SCR/e0b/box/dl/runs/mesh-20261031-e0b-c8f1c33` (only for the non-shipped variants of the same builds: ep3 `nomk` /
  `fit` pot, the ep8 / ep10 / merged beige builds). `SCR` = the session scratchpad.
- **Ground truth.** I opened no scan, mocap, parquet or `*_align` file and scored nothing. Every number here is [M],
  read from mesh files and our own JSON records. library_v3 / v3x, C0 and T1 meshes are used only as references for the
  frame comparison.
- **My scripts** (scratchpad `v1c0b/`): `manifest_check.py` (bytes), `glbhdr.py` (glTF structure), `frame_kit.py`
  (raw stats, kit budget, frame), `kitlib.py` and `rawonly.py` (same stats for the references and the sibling builds),
  `beige_frames.py` (beige per-episode frames), `balls.py`, `balls3.py`, `balls4.py`, `balls5.py`, `bottom.py`
  (ball radii and placement). Outputs: `frame_kit.json` / `frame_kit_copy.log`, `kitlib.json`, `rawonly.json`,
  `beige_frames.json`, `balls.json`, `balls3.json`.
- **Method notes.**
  - Kit: `v2dlb/mesh_budget.py` (sha256 8f29481d..., the staged kit) `budget_mesh(path, 4096, 4096)`; padding rows
    (faces `[0,0,0]`) are dropped before the watertight and body counts.
  - Frame, no registration: area-weighted centroid and PCA axes from 200,000 surface samples; median symmetric surface
    distance from 20,000 samples of each mesh to a 200,000-sample KD-tree of the other. This is an approximation of C0's
    exact `frame_check.py`; it reproduces the committed exact numbers to about 0.1-0.5 mm (C0b pot vs library_v3:
    centroid 7.15 vs 7.07 mm, symmetric median 2.57 vs 2.52 mm).
  - Rigid ICP: point-to-point, 90 % trimmed, 20,000 samples, started from identity; then a 24-start check (the 24 cube
    rotations about the centroids) to see whether the identity basin is the best one. "rel" below is the angle between
    the identity-started and the best multi-start solution.
- **Labels.** [M] measured here without ground truth; [D] an existing scan-scored record, quoted, not recomputed;
  [H] hypothesis.

## Verdict

**Two blocking items, both about what the shipped meshes would do in any contact or simulator use; neither breaks a
PREREG rule.** Bytes, kit counts and frames hold: both shipped E0b meshes are byte-identical to the MANIFEST and to the
box candidates, inside the kit budget, and in the library_v3 object frame to within the episode-to-episode spread of our
own builds.

- **B1 [M].** In the shipped E0b pot (`pot/ep3/thick`, md5 073872f4...), 17 of the 32 marker balls hang below the
  pot's own bottom. The lowest point is 16.8 mm below the pot body and 21 mm below library_v3's bottom along the same
  axis, and the balls nearly double the solid volume of the body they sit on.
- **B2 [M].** The shipped E0b beige cup (`beige/ep8/g1`, md5 0d926da1...) has three inside-out appendage shells. Its
  net signed volume is 23.5 cm3 (library_v3 157.8, T1 66.4). Neither the E0b README nor MANIFEST_E0b says so.

## 1. Bytes [M]

| Check | Result |
|---|---|
| MANIFEST_E0b.json itself | sha256 `4ebbe5bc61e7c810...` (as reported) |
| 36 pairs: `sha256`, `md5`, `bytes` vs the file at `mesh`, and the file at `source` | 36/36 equal, 0 mismatches |
| swapped pairs | 8: white_pot on evals 1, 3, 5, 6, 8, 28; beige_cup on evals 8, 10 (as reported) |
| library per pair | eval 8 -> `library_e0bx`, every other pair -> `library_e0b`, no exception |
| `libraries.*.files` (12 per library) vs disk | every file listed exists and matches sha256 / md5 / bytes / `same_as_base`; nothing on disk is unlisted |
| `library_e0b` vs `library_v3` | only `white_pot.glb` and `beige_cup.glb` differ. The 10 `*.recon.json` sidecars are not copied |
| `library_e0bx` vs `library_v3x` | only the same two files differ. The 9 `*.recon.json` and v3x's `beige_cup.v5.json` are not copied; v5.json described the replaced v3x beige |
| shipped files vs E0b box candidates | white_pot = `cand/white_pot/white_pot_ep3_thick.glb` (265ab341...), beige = `cand/beige_cup/ep8_beige_cup_sep_g1.glb` (aa3d8799...), in the box SHA256SUMS |
| `E0b/meshes/SHA256SUMS`, `C0b/meshes/SHA256SUMS` | all entries equal the files |
| C0b scored and guarded meshes | `score_c0b.jsonl` sha1[:16] and `guard_inputs_c0b.json` sha256 equal the four committed picks |
| glTF structure (both shipped, the four C0b picks, library_v3 / v3x, C0, T1) | one node, no node transform, one primitive, no material. library_v3's pot and beige also carry `COLOR_0`; ours, C0's and v3x's beige do not |

library_e0b and library_e0bx differ from their bases only in the two adopted objects, as claimed. The sidecars are
dropped exactly as in `library_c0` / `library_e0`. [H] Harmless if the kit reads only geometry; nothing here reads the
sidecars or the vertex colours.

## 2. Kit budget [M]

Raw = trimesh with `process=True`. Budget = the kit's `budget_mesh(path, 4096, 4096)` output without padding.

| Mesh | Raw faces / verts | Raw watertight / bodies | Signed volume, cm3 (bodies < 0) | Budget faces / verts | Budget watertight / bodies / volume |
|---|---|---|---|---|---|
| **E0b pot ep3/thick (shipped)** | 28650 / 14327 | yes / 1 | 563.7 (0) | 4096 / 2050 | no / 6 / 545.9 |
| library_v3 pot | 23734 / 11859 | yes / 1 | 624.6 (0) | 4096 / 2042 | no / 6 / 616.9 |
| C0b pot ep43/fit (public pick) | 25922 / 12965 | yes / 2 | 631.8 (0) | 4096 / 2052 | no / 4 / 620.8 |
| **E0b beige ep8/g1 (shipped)** | 46426 / 23201 | yes / 4 | **23.5** (3: -30.5, -29.3, -15.9; main 99.1) | 4096 / 2043 | no / **16** / 25.1 |
| E0b beige ep8/g0 (same build, no appendages) | - / - | yes / 1 | 99.1 (0) | 4096 / 2050 | **yes / 1** / 98.4 |
| library_v3 beige | 7526 / 3767 | yes / 2 | 157.8 (0) | 4096 / 2052 | yes / 2 / 157.3 |
| library_v3x beige | 4096 / 1998 | yes / 2 | 163.4 (0) | 4096 / 1998 | yes / 2 / 163.4 |
| T1 beige (pack 9a+) | - | yes / 2 | 66.4 (1: -67.0) | 4096 / 2052 | no / 4 / 63.7 |
| C0b beige ep11/g1 (public pick) | 43778 / 21883 | yes / 4 | 7.0 (3) | 4096 / 2043 | no / 25 / 8.3 |
| E0b beige ep10/g1, merged g1 (not shipped) | - | yes / 6, 9 | -56.2, -30.5 | 4096 / 2061, 2051 | no / 13, 23 / -56.0, -24.5 |
| C0 blue cup (pack 9a) | - | yes / 5 | 75.9 (4) | 4096 / 2059 | no / 11 / 76.5 |
| E0b blue cup merged g1 (info) | - | yes / 5 | -87.7 (3) | 4096 / 2052 | no / 17 / -81.1 |

- **Counts.** Every mesh is within 4096 faces and 4096 vertices after the budget, and `budget_mesh` never raised. This
  confirms the "budget OK" claims of PUBLIC_RESULTS and the E0b check stage (48/48).
- **Watertight and bodies.** After the budget the meshes are not watertight and are split into more bodies. For the pot
  this matches library_v3 (6 bodies). For the beige it does not: 16 bodies against 2 for v3 / v3x, which stay watertight.
- **"Budget OK" covers counts only.** It does not cover orientation, volume or fragmentation; see B2.

## 3. Frame [M]

### 3.1 Shipped E0b meshes and C0b picks of the adopted objects

| New -> reference | Centroid offset, mm | PCA axis angles, deg | Sym. median / p90, mm (no registration) | ICP from identity: rot deg / trans mm | Sym. median after ICP, mm | Multi-start rel, deg |
|---|---|---|---|---|---|---|
| **E0b pot -> library_v3** | 9.5 | 3.9 / 4.5 / 6.0 | 2.64 / 8.19 | **1.7 / 3.4** | 2.49 | 0.08 |
| E0b pot -> C0 pot (pack 9a) | 5.9 | 3.0 / 2.4 / 2.0 | 1.55 / 4.71 | 1.2 / 1.7 | 1.36 | 0.13 |
| E0b pot -> C0b pot pick | 9.3 | 2.3 / 4.1 / 3.8 | 2.24 / 6.12 | 1.8 / 3.2 | 1.70 | 0.25 |
| C0b pot pick -> library_v3 | 7.2 | 5.6 / 2.5 / 5.3 | 2.57 / 7.54 | 2.9 / 3.0 | 2.40 | 0.03 |
| C0b pot pick -> C0 pot | 5.5 | 5.4 / 5.2 / 4.3 | 1.89 / 4.83 | 2.1 / 2.4 | 1.74 | 0.49 |
| **E0b beige -> library_v3** | 9.6 | 25.7 / 26.2 / 5.4 (near-lathe pair) | 2.68 / 14.59 | **7.8 / 3.4** (mostly -6.4 deg about the cup axis) | 2.84 | 0.20 |
| E0b beige -> library_v3x | 11.1 | 18.6 / 20.4 / 8.7 | 2.02 / 9.28 | 2.7 / 0.6 | 1.99 | 1.09 |
| E0b beige -> T1 (pack 9a+) | 8.0 | 4.4 / 13.2 / 13.2 | 1.70 / 6.81 | 1.5 / 3.5 | 1.68 | 0.17 |
| E0b beige -> C0b beige pick | 3.0 | 1.4 / 19.4 / 19.4 | 0.95 / 2.96 | 0.8 / 2.1 | 0.72 | 0.30 |
| C0b beige pick -> library_v3 | 10.7 | 24.4 / 33.7 / 23.4 | 2.57 / 15.05 | 4.6 / 2.9 | 3.02 | 0.15 |
| C0b beige pick -> library_v3x | 11.9 | 17.3 / 19.7 / 9.5 | 2.10 / 8.88 | 7.1 / 1.2 (+6.8 deg about the axis) | 2.06 | 2.18 |
| C0b beige pick -> T1 | 6.7 | 5.3 / 7.1 / 5.7 | 1.42 / 6.21 | 3.5 / 2.1 | 1.37 | 0.13 |
| library_v3x beige -> library_v3 beige | 2.0 | - | 1.56 / 5.84 | 7.0 / 2.8 (-6.9 deg about the axis) | 0.93 | 0.05 |
| E0b beige ep8/g1 -> E0b ep10/g1 (not shipped) | 12.5 | - | 1.70 / 9.53 | 1.8 / 1.6 | 1.72 | 0.21 |
| E0b ep10/g1 -> library_v3 / v3x | 15.5 / 17.5 | - | 3.26 / 3.00 | 13.2 / 5.7 and 7.7 / 3.1 | 4.78 / 3.33 | 0.05 / 0.91 |

My approximate numbers agree with the committed exact ones: the box frame row gives 9.53 mm / 2.17 mm for E0b pot ->
C0b pick (mine 9.3 / 2.24), and 2.92 mm / 0.83 mm for E0b beige -> C0b beige (mine 3.0 / 0.95).

What the frame numbers say:
- **No flip, no frame error.** For every pair the best of 24 ICP starts is the identity basin (rel <= 2.2 deg). The
  centroid offsets of 6-12 mm are mostly shape (balls, handle, appendages): after ICP the residual translation is
  0.6-3.5 mm.
- **Pot.** The shipped pot is 1.7 deg / 3.4 mm from library_v3 and 1.2 deg / 1.7 mm from the C0 pot that pack 9a ships.
  That is the same spread as the guarded public pick (2.9 / 3.0 and 2.1 / 2.4). Shipping it "as fitted" (C0a-diag) is
  consistent with the frame.
- **Beige, rotation about the cup axis is ill-conditioned.** The ICP angles about the axis do not compose:
  - E0b -> C0b pick is 0.8 deg, and C0b pick -> v3 is 4.6 deg (about the axis -1.4 deg);
  - E0b -> v3 is 7.8 deg (about the axis -6.4 deg).

  Only the handle and the appendage splats fix that angle, so it is uncertain to a few degrees. Tilt and translation
  are well defined.
- **The eval 8 v3 / v3x question cannot be settled from meshes, and it is small.**
  - library_v3x's beige sits 7.0 deg (about the axis) / 2.8 mm from v3's.
  - The E0b beige is closer to v3x (2.7 deg / 0.6 mm) than to v3 (7.8 / 3.4), but so is the public C0b beige
    (translation 1.2 vs 2.9 mm), and that one was built on v3-seeded public tracks. The resemblance is shape, not
    evidence about eval 8's track frame.
  - The ep8 and ep10 builds agree to 1.8 deg / 1.6 mm, so the two eval pairs that share this one mesh see the same
    object frame to that precision.
  - Bound [M]: whichever frame the eval 8 poses are in, the shipped beige differs from that frame's library mesh by at
    most about 8 deg about the near-symmetric axis and 3.4 mm.

### 3.2 Not-adopted objects (information only; nothing here ships)
| New -> reference | Centroid, mm | Axes, deg | Sym. median / p90, mm | ICP from identity: rot / trans | Sym. median after ICP | Multi-start |
|---|---|---|---|---|---|---|
| C0b rack ep13/full -> library_v3 | 37.2 | 12.1 / 12.1 / 0.9 | 6.88 / 52.67 | 13.9 deg / 33.6 mm | 11.03 | identity basin (rel 0.47 deg) |
| C0b rack ep13/full -> C0 rack (pack 9a) | 29.1 | 12.7 / 12.5 / 3.7 | 8.61 / 47.24 | 7.7 deg / 21.7 mm | 9.43 | identity basin (rel 0.01 deg) |
| C0b blue cup ep21/g1 -> library_v3 | 29.5 | 73.7 / 73.4 / 6.4 | 2.99 / 13.90 | 24.0 deg / 18.4 mm | 7.33 | **best start 116 deg away** (trimmed mean 10.2 vs 11.3 mm) |

- **Rack.** The rack pick is a different shape, not a moved rack: 2659 cm3 against library_v3's 866 cm3, 487 x 265 x 151 mm,
  and 11 mm median distance even after ICP. This agrees with its CD-O of 1.63 [D].
- **Blue cup.** The clutter blobs (PUBLIC_RESULTS) make even rigid registration ambiguous, which agrees with the kit's
  registration failure behind add_med 120 mm [D].
- **Not finished.** The remaining comparisons (blue cup vs C0, the E0b lid and blue-cup info picks, and the C0 / T1
  controls against library_v3) were still running when this file was committed. They are not needed for any verdict
  above. If they finish, they are in `SCR/v1c0b/frame_kit_copy.log`.

## 4. Marker balls on the shipped files [M]

### 4.1 Radii and counts
For each detected ball (centre c, radius r from `results/box/markers/ep<e>.json`), I took the mesh vertices at
distance r from c (tolerance 0.02 mm), fitted a sphere to them, and compared.

| Mesh | Detected (markers json) | In build record | Exposed on the file (>= 8 vertices on the sphere) | Max \|r_file - r_det\| | Radii, mm | Stems | Separate ball bodies |
|---|---|---|---|---|---|---|---|
| **E0b pot ep3/thick (shipped)** | 32 (pass 1: 12, pass 2: 20) | 32, same centres | 32 | 0.001 mm | 10.42-12.48, median 12.06; 19 >= 12.0 | 0 | 0 (1 body) |
| C0b pot ep43/fit (public pick) | 26 (18 + 8) | 26 | 26 | 0.001 mm | 7.47-12.43, median 11.69 | 0 | 1 (r 11.41) |
| C0b rack ep13/full (public pick, not adopted) | 45 (22 + 23); markers json = build record exactly | 45 | 45 | 0.008 mm | 6.74-12.49, median 11.25 | 1 | 5 |

- **Radii.** The balls on the files are exactly the `markers.py` detections, as `attach` unions them. Every frozen
  setting is respected (settings sha256 488ac3b6... in both the markers json and the build record).
- **Pass 2.** It adds 20 of the 32 pot balls inside the consensus window. On ep3 that window is [10.81, 12.5] mm: the
  upper end is the A.6 window top, not the +10 % of the 12.01 mm consensus, so pass 2 can only add balls of 10.8-12.5 mm.
- **Exposure.** On the E0b pot, 113-146 of a full sphere's 146 vertices remain on each ball, so every ball is 77-100 %
  outside the body.
- **Report wart (non-blocking, gmg code).** `markers.attach` writes `gap_mm = (L - r) * (-1 if inside else 1)`, with L
  the distance from the centre to the surface. A protruding ball whose centre is inside the body and a floating ball
  outside both get a positive gap, so the sign of `gap_mm` in the build records does not tell embedded from floating.
  The counts above come from the files.

### 4.2 Where the shipped pot's balls are (B1)
Reference frame: the pot axis and centre of the build record (`axis` [0.980, 0.033, 0.195], i.e. about +x, open end
towards +axis). Axial rays from inside the cavity hit the floor at -40.0 mm (inside) and -42.6 mm (outside), and
nothing towards +axis, so the opening is up and the bottom is at about -43 mm.

| Mesh (same axis) | Lowest vertex, axial mm | 0.5 % / 2 % surface quantile, mm | Surface share below -44 mm |
|---|---|---|---|
| E0b ep3 `nomk` (same build, no balls; box) | -43.4 | -43.2 / -43.0 | 0.00 % |
| **E0b ep3 `thick` (shipped)** | **-60.2** | -56.2 / -51.8 | **7.19 %** |
| C0b ep43 `fit` (public pick, guarded) | -55.7 | -49.6 / -44.9 | 3.80 % |
| C0 pot (pack 9a) | -46.9 | -46.3 / -44.9 | 2.68 % |
| library_v3 pot | -39.3 | -38.6 / -38.1 | 0.00 % |

- **Under the bottom.** 17 of the 32 balls reach below the body's outer bottom (lowest ball point -60.3 mm). The ball
  centres sit at axial -48 to -27 mm and radial 10-88 mm, under and around the base.
- **Elsewhere.** 4 balls are on the handle (radial 116-223 mm, axial +50 mm). The rest are on the outer wall, from the
  base fillet up to near the rim.
- **Volume.** The same ep3 build without balls (`nomk`) is 206.6 cm3, with balls (`fit`) 398.7 cm3, and the 32 balls
  add up to 230.7 cm3 of sphere volume. The shipped `thick` body with balls is 563.7 cm3.
- **[H] What they are.** A real marker under a pot's base would not be seen by the cameras. The radii (10-12.5 mm) and
  the place are those of fingers lifting the pot, or of table clutter beside the base. B7 saw hands and rims on its dev
  crops. Falsified if crop images at these centres (the B7 crop check) show ball markers.
- **[H] Consequence.**
  - Any contact use puts the pot on a bed of 12-mm balls, up to 17 mm above its own base: the simulator for SR,
    `contact_retarget`, the collision carve.
  - At the tracked resting poses, those balls are 17-21 mm inside the table, the kind of contact overflow the gmg I
    round met under sim=rl.
  - The public guard accepted the C0b pick, which has the same defect at about half the size, so the pose metrics may
    tolerate it. A contact metric was never tested.

## 5. Findings

### Blocking (decide before pack 10 ships these meshes; neither is a PREREG violation)
- **B1, E0b pot balls under the base [M], consequence [H].** Section 4.2.
  - PREREG 8 and 9 have no geometric gate, so the ship rule was followed.
  - The README and MANIFEST describe the 32 balls only as "[H] most are false, not checked on these files". They do not
    say that half of them lie under the base, or that the lowest 17 mm of the mesh is balls.
  - **Owner decision.** Options, all labelled post hoc (no score may choose between them):
    - ship as is, flagged "not for contact / simulator use";
    - ship `pot/ep3/nomk`, the same body without balls (fidelity 3.377 against 3.275 [M]), as a disclosed deviation;
    - keep C0's flagged pot or library_v3 for the pot.
  - Whichever is chosen, pack 10's README should carry the measured numbers above.
- **B2, E0b beige inside-out shells [M], consequence [H].** Section 2.
  - The shipped beige's three appendage shells are oriented inward, which brings its net volume to 23.5 cm3 (main body
    99.1). After the budget it is 16 bodies.
  - [H] Any use that derives mass, inertia or inside / outside from the mesh will be wrong or refused.
  - The issue is known for the whole lathe g1 family: STATUS 31 Oct ~22:00 says to hand it to "the C0b / E0b owners
    before any COM or simulator use". T1 in pack 9a+ and C0's blue cup in pack 9a have it too.
  - Not fixed and not flagged: E0b ships a g1 mesh, and neither `E0b/README.md` nor `MANIFEST_E0b.json` mentions it.
  - **Minimum.** Add the flag to the MANIFEST and README before the hand-off.
  - **Owner options.**
    - Re-orient the three shells (trimesh `fix_normals` per body). This keeps every surface point, so fidelity and CD-O
      cannot change [H, by construction], but it is a new file.
    - Ship the same build's `g0`: one body, 99.1 cm3, watertight after the budget. Its ALL-eval fidelity is 4.343,
      4th of 5, against 3.322 for the pick [M].
  - Each is a disclosed post-hoc deviation.

### Non-blocking
- **N1.** "Budget OK" in PUBLIC_RESULTS and the E0b check covers face and vertex counts only. The budgeted beige meshes
  are non-watertight and fragmented (E0b 16 bodies, C0b pick 25), against 2 watertight bodies for library_v3 / v3x.
  The pot matches library_v3 (6 bodies).
- **N2.** The eval 8 frame caveat (PREREG 10) cannot be resolved GT-free from the meshes. It is bounded at about 8 deg
  about the beige axis and 3.4 mm, and the ep8 and ep10 builds agree to 1.8 deg / 1.6 mm (section 3.1). The E0b
  beige's closeness to v3x is shape, not frame: the public C0b beige shows it too.
- **N3.** The shipped pot body without balls is already lower than library_v3's: nomk bottom -43.4 mm against -39.3 mm
  on the same axis, so 4.1 mm. This is within the reconstruction spread (ICP 3.4 mm), not a frame shift.
- **N4.** `markers.attach` `gap_mm` sign convention (section 4.1): embedded-protruding and floating balls both
  report positive gaps.
- **N5.** The C0b public pot pick carries one free-floating ball (a separate 5.98 cm3 body) and the rack pick five.
  They are not shipped, but the C0b pot is PREREG 9 (e)'s fallback.
- **N6.** The library folders drop the `*.recon.json` sidecars and the vertex colours, as library_c0 / e0 do (section 1).
- **N7.** The frame-check thresholds for the pot are wide (centroid 108.6 mm, symmetric median 12.9 mm; E0b X4 / X15).
  The shipped pot passes them by a factor of about 6 to 11. The independent check against library_v3 above is the
  stronger statement.
- **N8 (my process).** A first copy of my `frame_kit.py` (pid 10090) was not dead, as I had thought, and a second copy
  ran beside it. I was not permitted to stop my own first copy. It runs at nice 19 on one thread and ends by itself.
  Both write the same log and json; I read the results from an append-only copy (`frame_kit_copy.log`) of the second
  copy's lines.

### Confirmed
- MANIFEST_E0b: 36/36 pairs byte-identical (sha256, md5, bytes) to the files and their sources; 8 swaps; eval 8 only
  from library_e0bx.
- library_e0b = library_v3 except `white_pot.glb` (073872f4...) and `beige_cup.glb` (0d926da1...); library_e0bx =
  library_v3x except the same two files.
- Shipped files = the E0b box candidates (sha256 in the box SHA256SUMS). The C0b scored and guarded meshes = the
  committed picks.
- glTF: one node and no transform in every file checked (section 1 list). Nothing re-poses the mesh on load.
- Kit budget: within 4096 / 4096 for every mesh checked; `budget_mesh` never raised.
- Frame: both shipped meshes and all C0b picks of the adopted objects are in the library_v3 object frame. There is no
  flip, ICP from identity gives 0.8-7.8 deg and 0.6-3.5 mm, and the identity basin is the best of 24 starts.
- Ball radii and counts on the shipped pot equal the frozen detector's output (<= 0.001 mm); on the rack pick to
  0.008 mm.

## Progress log
- 22:29Z start; read NOTES tail, STATUS head, PREREG 1-13.
- 22:33Z [M] MANIFEST and library byte checks; ball radii vs detections.
- 22:47Z [M] scored / guarded sha = picks; glTF headers; kit on library_v3.
- 23:05Z-23:30Z [M] pot balls under the base (balls3-5, bottom.py); beige inside-out shells; frames of the adopted
  objects; beige per-episode frames.
- 23:40Z wrote this file (pushed e62a3ff).
- 23:50Z [M] section 3.2: rack and blue-cup picks vs library_v3 / C0; remaining info comparisons not waited for.
