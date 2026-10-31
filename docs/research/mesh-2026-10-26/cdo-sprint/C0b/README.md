# C0b / E0b: the C0 mesh methods rebuilt without scan-derived constants (report)

2026-10-31, closing report of the CD-O sprint C0b / E0b step, for pack 10 (built 1 Nov ~14:00 UTC).
Labels: [M] measured without ground truth; [D] scored against the public scans / mocap (stand-ins for the hidden ones);
[E] estimate; [H] hypothesis.

**Why.** Pack 9a ships the C0 pot, lid and rack "flagged": their marker balls use the scan-measured 7 mm radius and a
5-9.5 mm fit window, and the lid / rack walls use the scan-leaked 2.5 mm. C0b rebuilds the same methods with no
scan-derived constant, validates them the same way on public episodes (one scoring per mesh plus C0's AUC guard), and
E0b rebuilds the adopted objects on the eval episodes.

**Sequence of records.**
- Audit 9451062: `AUDIT.md` / `AUDIT.json`, 163 constants. 16 are scan-derived and 71 of unknown origin, 16 of those
  suspect.
- PREREG 8174998 (`PREREG.md`, `REPLACEMENTS.md` / `.json`), pushed before any build.
- Public deviations ade3608 (`DEVIATIONS_PUBLIC.md`, D1-D10).
- Picks 9f99ae0, committed before any scoring.
- Public results and adoption d84bc87 (`PUBLIC_RESULTS.md` / `.json`).
- E0b deviations (`../E0b/DEVIATIONS_E0B.md`, X1-X15), written before any eval candidate.
- E0b results 94742e4 (`../E0b/README.md`, `MANIFEST_E0b.json`).
- Verifiers: `verify_0.md` 04748dc (integrity) and `verify_1.md` 64542d7 (frame, kit, bytes).
- This report and the disclosure flags. Step log: `NOTES.md`.

## 1. What pack 10 gets

**Adopted (PREREG 8: WIN and AUC-guard pass): white_pot and beige_cup.** On their eval pairs each ships its eval-built
E0b pick (PREREG 9 (e)). **Not adopted: white_pot_lid, plastic_dish_rack, blue_cup.** For those, C0's flagged mesh (as in
pack 9a) or library_v3 stays, by the owner's choice; C0b recommends neither.

| Object | Public pick: CD-O [D] (WIN threshold; C0, library_v3) | AUC guard [D] (mean / min dAUC) | Adopted | Ships on eval (md5) |
|---|---|---|---|---|
| white_pot | `pot/ep43/fit` 0.3924 (<= 0.4171; C0 0.3417, v3 0.4371) | pass, +0.0009 / -0.0107 | **yes** | E0b `pot/ep3/thick` on evals 1, 3, 5, 6, 8, 28: **073872f4d0bdd0935a27fa985ae0063d**, flag B1 |
| beige_cup | `beige/ep11/g1` 0.3007 eval 10 / 0.2983 eval 8 (<= 0.8363 / 0.7100; C1/T1 0.2475 / 0.2549) | pass, +0.0139 (twin 11) | **yes** | E0b `beige/ep8/g1` on evals 8, 10: **0d926da1b444f4982de50ceb0e90ade7**, flag B2 |
| white_pot_lid | none (16/16 public builds failed) | no data | no | C0 or library_v3 (owner) |
| plastic_dish_rack | `rack/ep13/full` 1.632 (<= 0.5351) | fail, -0.1325 / -0.3043 | no | C0 or library_v3 (owner) |
| blue_cup | `cup/ep21/g1` 1.677 (<= 0.5033) | fail, -0.5462 / -0.6273 | no | C0 or library_v3 (owner) |

- **Folders.** `meshes/library_e0b` is library_v3 with only `white_pot.glb` and `beige_cup.glb` replaced (every eval
  pair except eval 8). `meshes/library_e0bx` is library_v3x with the same two files (eval 8).
- **Merge one by one.** Neither folder is a drop-in for pack 9a+. Pack 9a+ carries the C0 pot, lid and rack and the C1
  beige and dust pan; packing a folder whole reverts those pairs.
- **Manifest.** `MANIFEST_E0b.json` lists 36 pairs, 8 of them swapped. It was amended on 2026-10-31 with flags only
  (see `amendments`; prior sha256 `4ebbe5bc...`, commit 94742e4).
- **E0b rule (e) [M]** (obs_fidelity sum_mm on all eval points of the object):
  - pot: E0b pick 3.275 against the C0b public pick's 3.602, ratio 1.100;
  - beige: 3.322 against 3.277, ratio 0.986.

  Both ratios are >= 0.85, so the E0b pick ships in both cases.
- **Accuracy against what pack 9a+ already ships.** Both adopted objects are less accurate than the meshes in pack 9a+.
  - Pot, public [D]: 0.392 against C0's 0.342.
  - Beige, public [D]: 0.30 against C1/T1's 0.25.
  - On the eval points [M]: C0's pot 3.072 and E0's pot 3.059 fit better than the shipped 3.275; library_v3x's beige 3.066
    fits better than the shipped 3.322.

  Adoption follows PREREG 8, which has no other gate. Pack 10 trades accuracy for compliance; that weighing is the
  owner's.

## 2. What replaced which constant

All replacements are options; with old defaults the scripts rebuild C0 byte-identically (lid ep2, pot ep2 with its axis
file, cup ep21, rack run 12/12; re-checked by verify_0 with HEAD code). Full table: `REPLACEMENTS.md` (87 records).

| Old (origin) | Replacement (origin) |
|---|---|
| MK_R0 7 mm, MK_RMIN/RMAX 5-9.5 mm, and the rest of the marker path: MK_DIAG, MK_FREE_R, free-fit acceptance, stem rule, in_basin (S / U-suspect) | gmg `markers.py` `detect_episode` with the frozen A.6 settings (sha 488ac3b6), no radius prior; variants fit / thick / nostem / nomk. One setting, the seed count, is gmg-informed (verify_0 N1) |
| T_LID 2.5 mm, T_WALL 2.5 mm, the pot wall fallback 4 mm, the lathe fallback 3 mm, T_MIN/T_MAX 2-6 mm, BAR_T0 5 mm, the 1.5 / 2.5 / 4.0 grid (S / U) | Own-observation thickness chain. First the method's own wall measurement, then the `thickness.py` median (>= 200 measurements), then **t0_C0b = 4.559 mm**: the A.1 median of 9 public per-object medians, fittable, frozen for E0b. Clipped to [1.5, 8] mm. The grid is retired |
| library_v3 box as ROI, library_v3 surfaces for co-object carving, the `--lib` tsdf variant (library input) | ±0.30 m cube about the track origin, rebuilt at 0.45 m when more than 0.1 % of points lie within 8 mm of a face; two-pass carving from our own pass-A points; tsdf dropped (nomk takes its slot) |
| APP_D 8 mm, lathe `--app_d` 4 mm (U-suspect) | 3 sigma (gmg A.2 sigma of the observations) |
| hO 0.6, handle reach rmax + 60 mm, lid arch > 50 mm, lid flange band ±6 mm (U-suspect) | hO 0.5; reach > 1.5 x rmax; arch extent > 0.5 x r_edge; ±3 sigma |
| Lid dome 15-35 mm and flange 40-80 mm windows (U-suspect) | gmg A.6b extents, x1 (`a6b1`) and x2 (`a6b2`); the A.6b table is also "informed" (verify_0 N2) |
| Lathe TIE 1.25, floor-density rule (U-suspect / S) | TIE 1.0; `--floor base_t` |
| Blue-cup selector written after scoring (S) | Pre-registered GT-free fidelity pick (PREREG 5, 9 (d)) |
| 40 other U values | KEPT, declared generic post hoc (disclosed). One is U-suspect: obs_points `table_band` 8 mm |

**Correct wording for pack 10 (verify_0 N1).** "No scan-derived value reaches the shipped meshes; the ball detector
carries one gmg-informed setting; 40 constants of unknown origin are kept." Do not write "no scan-derived or unknown
constant". The tracks remain library_v3-seeded (audit F4, an owner question). The imported gmg and autokit modules were
taken on gmg's labels and not re-audited (verify_0).

## 3. Open owner decisions (blocking for contact / simulator use; not PREREG violations)

The pick followed the written rules. No PREREG rule covers either finding, so nothing was re-run or swapped. Both are
now flagged in `MANIFEST_E0b.json` and `../E0b/README.md`. I re-measured them GT-free [M]
(scratch `c0b_report/quick.py`, `potlow.py`).

- **B1, shipped pot (md5 073872f4...) [M].** 17 of its 32 marker balls hang below the pot's own base.
  - The lowest point is -60.2 mm on the build axis. The same ep3 build without balls (`nomk`) ends at -43.3 mm, and
    library_v3 at -39.3 mm.
  - 7.2 % of the surface lies below -44 mm, and the balls add about 192 cm3 to a 207 cm3 body.
  - [H] These are fingers or clutter, not markers. In SR, contact_retarget or the collision carve, the pot would rest on
    12-mm balls 17-21 mm inside the table.
  - Options, all post hoc: ship it flagged "not for contact use"; ship `pot/ep3/nomk` (fidelity 3.377 vs 3.275 mm); or
    keep C0's pot or library_v3.
- **B2, shipped beige (md5 0d926da1...) [M].** It has three inside-out appendage shells (-30.5, -29.3 and -15.9 cm3).
  - Its net signed volume is 23.5 cm3 (main body 99.1), against 157.8 for library_v3.
  - After the kit budget it is 16 bodies and not watertight.
  - The same defect runs through the whole lathe g1 family, including T1 in pack 9a+ and C0's blue cup.
  - Options, both post hoc: re-orient the three shells (surface unchanged, so [H] fidelity and CD-O unchanged); or ship
    the same build's `g0` (one watertight body, fidelity 4.343, 4th of 5).
- **Not-adopted objects.** For the lid, rack and blue cup the choice is C0 (flagged, scan-derived constants) or
  library_v3.

## 4. Caveats for the pack builder

- **No AUC guard on these meshes.** The guard ran on the public C0b picks; the eval-built meshes have neither a guard
  nor a score, and their pick is in-sample. Fidelity is not CD-O.
- **Cube-ROI clutter [M].** The cube guard fired on 16 + 11 public files and 8 + 3 eval files. Clutter caused all three
  public failures: the lid's flange window, the rack bounds, and the blue cup's 5 blobs. ALL-set fidelity is partly a
  clutter score.
- **Marker balls [M].** The frozen detector returns 20-69 balls per object-episode, with radii at the 12.5 mm top of
  its window. Most are probably false [H] (B7 dev crops; not checked on these files).
- **Eval 8 frame.** One beige mesh ships on eval 8 and eval 10. Whether eval 8 is in the v3 or the v3x frame stays open
  (PREREG 10). It is bounded at about 8 deg about the near-symmetric axis and 3.4 mm [M] (verify_1 N2).
- **Frame [M].** Both shipped meshes are in the library_v3 object frame with no flip: pot 1.7 deg / 3.4 mm, beige
  7.8 deg / 3.4 mm, by ICP from identity, best of 24 starts. They ship as fitted, with no alignment (C0a-diag).
- **Kit budget.** "OK" covers face and vertex counts only: 4096 faces each, 2050 / 2043 vertices. After the budget the
  pot is 6 bodies, as library_v3 is.
- **Sidecars.** The library folders drop the `*.recon.json` sidecars and the vertex colours, as library_c0 / e0 do.

## 5. Verification and corrections

- **verify_0 (integrity): no blocking item.** These reproduce:
  - timing, with the PREREG pushed before every build and the picks before every scoring;
  - both sets of picks, recomputed from the raw rows;
  - one scoring per mesh;
  - the guard, from the 15 base runs (byte-identical to C0's);
  - no alignment anywhere;
  - the old-default rebuilds.
- **verify_0 corrections:**
  - N1: the detector seed count is "informed" (above).
  - N2: the A.6b table is "informed"; only the lid uses it.
  - N3: the single-scoring check was split over two streams; no duplicate scoring happened.
  - N4: the E0b dry-run outputs were *not* deleted (scratch `e0b/dry`, 244 files). They were not used.
  - N5: the ep11 beige and ep21 blue cup picks also feed PUBOWN's mocap-scored re-track test. That result must not
    revise this adoption without a new PREREG.
  - N6: the E0b rack ran prim_rack blob 27e778e (provenance only).
  - N7: the beige WIN compares one seed against the library mean; the verdict holds either way.
- **verify_1 (frame, kit, bytes): two blocking items, B1 and B2 (section 3).** Its other checks hold: the manifest
  matches the files byte for byte (36/36), the libraries differ from their bases only in the two files, the glTF
  structure is plain, and the balls equal the `markers.py` detections. Non-blocking items:
  - N4: `markers.attach` `gap_mm` cannot tell embedded balls from floating ones.
  - N5: the C0b public pot pick, the PREREG 9 (e) fallback, has one free-floating ball.
  - N8: the not-adopted rack and blue cup are shape failures, not frame shifts.
- **Code defects, not fixed:**
  - prim_potlid `build_lid` raises LinAlgError on an empty flange selection;
  - prim_rack `lip_tops` raises IndexError on an empty quantile (the E0b rack crash);
  - obs_fidelity ignores `--trim` / `--icp`;
  - lathe_obs `--spheres` is unused;
  - the prim_* docstrings still call 7 mm "our own stereo".

## 6. Cost and runs

| Run | Box | Code | Time | Cost |
|---|---|---|---|---|
| C0b public `mesh-20261031-c0b-00e8584` | Vast 58564958, self-destroyed, confirmed gone 19:33:35Z | 00e8584 | 66 min | $0.68 (ledger actual; planned $1.50) |
| E0b eval `mesh-20261031-e0b-c8f1c33` | Vast 58580656, self-destroyed, confirmed gone 22:15:10Z | c8f1c33 | 39 min | $0.49 [E] (planned $1.50) |
| Scoring, guard, verifiers, this report | shared cloud VM, CPU | d84bc87 .. this commit | - | $0 |

Total about **$1.17**. Bulk observed points are in the HF store runs. Here: `meshes/`, `results/`, `jobs/`, `scripts/`
(C0b) and `../E0b/{meshes,results,jobs,scripts}`.
