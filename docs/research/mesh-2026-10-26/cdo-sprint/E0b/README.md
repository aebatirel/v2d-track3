# E0b: the C0b scan-free mesh methods rebuilt on the eval episodes

Pre-registration: `../C0b/PREREG.md` sections 9-10 (commit 8174998). Public stage and adoption: `../C0b/PUBLIC_RESULTS.md`
(d84bc87): **white_pot and beige_cup adopted**; lid, rack and blue cup not adopted. Interpretations and code details:
`DEVIATIONS_E0B.md` (X1-X15, written before any eval candidate existed). Step log: `../C0b/NOTES.md`. Labels: [M] measured
without ground truth, [E] estimate, [H] hypothesis. No eval ground truth exists, so nothing here is scored.

## Result
- **Box run [M].** Run `mesh-20261031-e0b-c8f1c33`, code c8f1c33. Vast instance 58580656 (Belgium, EPYC 7662, 64 cores).
  The job took 39 min and finished with rc=0. The box destroyed itself and was confirmed gone at 22:15:10Z.
  Cost about **$0.49** [E] (ledger: planned $1.50, actual $0.49).
- **Stages [M].** Everything passed except one build:
  - obsA 28/28, obsB 19/19, derive 4/4, measure 38/38, markers 10/10;
  - builds 30/31: the one `prim_rack.py run` crashed (below);
  - check 48/48, frame 40/40, fid 287/287, report 72/72.
- **Pick re-applied locally.** `scripts/e0b_package.py` re-applied PREREG 9 (c)-(e) from the box's raw rows and recomputed
  the frame thresholds. It agrees with the box's `selection.json` for every object.

### What ships (PREREG 9 (e), adopted objects only)
| Object | E0b pick | fid ALL-eval, mm (pick / C0b public pick) | public / pick | Rule (e) | Shipped mesh, md5 |
|---|---|---|---|---|---|
| white_pot | `pot/ep3/thick` (24/24 eligible) | 3.275 / 3.602 | 1.100 (>= 0.85) | E0b pick | `meshes/library_e0b/white_pot.glb` (and e0bx) md5 **073872f4d0bdd0935a27fa985ae0063d** |
| beige_cup | `beige/ep8/g1` (5/5 eligible) | 3.322 / 3.277 | 0.986 (>= 0.85) | E0b pick | `meshes/library_e0b/beige_cup.glb` (and e0bx) md5 **0d926da1b444f4982de50ceb0e90ade7** |

- **Libraries.**
  - `meshes/library_e0b` = `meshes/library_v3` with only these two files replaced;
  - `meshes/library_e0bx` = `meshes/library_v3x` with the same two files (eval 8);
  - each keeps the `.glb` files and `mini_sweeper.flatten.json`, as `library_c0` and `library_e0` do.
- **Manifest.** `../C0b/MANIFEST_E0b.json` lists all 36 pairs: mesh, sha256, md5, source, fidelity and flags. 8 pairs
  are swapped: white_pot on evals 1, 3, 5, 6, 8 and 28; beige_cup on evals 8 and 10.
- **Not a drop-in for pack 9a+.** Pack 9a+ ships the C0 pot, lid and rack, the C1 beige lathe and the C1 dust pan. Merge
  the objects one by one.

### Flags added after verification (2026-10-31 ~23:55 UTC; disclosure only, meshes unchanged)
Verifiers: `../C0b/verify_0.md` (integrity) and `../C0b/verify_1.md` (frame, kit, bytes). Both shipped meshes need an
owner decision before any contact, mass or simulator use. No PREREG rule covers this, so nothing was re-run or swapped.
The same flags are in `../C0b/MANIFEST_E0b.json` (pairs and `objects.<o>.flags`; the change is recorded under
`amendments`; prior sha256 `4ebbe5bc...`, commit 94742e4).
- **white_pot (B1) [M].** 17 of the 32 marker balls lie below the pot's own base.
  - On the build axis the lowest point is -60.2 mm. The same ep3 build without balls (`nomk`) ends at -43.3 mm, and
    library_v3 at -39.3 mm.
  - 7.2 % of the surface lies below -44 mm.
  - The balls add about 192 cm3 to a 207 cm3 body.
  - [H] These are fingers or table clutter, not markers.
  - **Not for contact or simulator use** (SR, contact_retarget, collision carve) until the owner decides. The options,
    all post hoc: ship it flagged; ship `pot/ep3/nomk` (fidelity 3.377 vs 3.275 mm); or keep C0's pot or library_v3.
- **beige_cup (B2) [M].** The mesh has three inside-out appendage shells (-30.5, -29.3 and -15.9 cm3; main body
  +99.1 cm3).
  - Its net signed volume is 23.5 cm3, against 157.8 for library_v3 and 66.4 for T1.
  - After the kit budget it is 16 bodies and not watertight. library_v3 and v3x stay 2 watertight bodies.
  - **Not for mass, inertia, inside/outside or simulator use** until the owner decides. The options, both post hoc:
    re-orient the three shells (the surface does not change); or ship the same build's `g0` (one body, watertight after
    the budget, fidelity 4.343 vs 3.322 mm).
- **Constant origins (verify_0 N1).** No scan-derived value reaches either mesh. But the frozen gmg ball detector has
  one gmg-informed setting: its seed count was raised from 5,000 to 15,000 after a first run, by agents who knew the
  scan catalogue. 40 KEEP constants of unknown origin also remain. Describe the pack as "no scan-derived value; the
  ball detector carries one gmg-informed setting".
- **"Kit budget OK"** covers face and vertex counts only (verify_1 N1).

### Picks of the non-adopted objects (information only; library_v3 stays)
| Object | E0b pick | fid ALL mm | Note |
|---|---|---|---|
| white_pot_lid | `lid/ep1/a6b2_nomk` (8/8 built and eligible) | 2.976 | The eval lid builds worked, where all 16 public ones failed. There is no frame check, because no public lid pick exists |
| plastic_dish_rack | none | - | `prim_rack.py run` crashed in `lip_tops` (numpy quantile of an empty array, IndexError; `results/box/logs/build/rack__run.log`). Not retried (PREREG 13) |
| blue_cup | `cup/merged/g1` (9/11 eligible) | 5.033 | The frame check excluded ep20 g1 and g0 (median distance 7.28 and 16.61 mm, over the 5.41 mm limit) |

## Diagnostics (reported only; fidelity sum_mm on the C0b eval points, ALL set) [M]
| Object | E0b pick | C0b public pick | C0 mesh | library_v3 | E0 pick | other |
|---|---|---|---|---|---|---|
| white_pot | 3.275 | 3.602 | 3.072 | 4.075 | 3.059 | |
| white_pot_lid | 2.976 | - | 1.861 | 5.254 | 1.674 | |
| plastic_dish_rack | - | 19.067 | 10.814 | 10.878 | 11.058 | |
| blue_cup | 5.033 | 5.181 | 13.968 | 14.058 | 13.838 | |
| beige_cup | 3.322 | 3.277 | 4.569 (C1/T1, pack 9a+'s beige) | 3.417 | - | library_v3x 3.066 |

Per-episode values, rankings, the observed-point table, M_sep, thickness, markers and frame thresholds are in
`results/RESULTS_TABLES.md` and `results/results_digest.json`.

## Read before shipping
- **The pick is in-sample.**
  - The E0b candidates are fitted to the same eval points that rank them. The C0b public pick, C0, E0 and library_v3 are
    out of sample there.
  - Fidelity is not CD-O. On public data the C0b pot pick was 0.392 [D] against C0's 0.342.
- **C0 and E0 explain the eval points better on the pot [M].** C0's pot scores 3.072 and E0's 3.059, against 3.275 for the
  E0b pick. Rule 9 (e) compares the pick only with the C0b public pick, so it ships the E0b pick.
  - The same pattern held on public data: C0's pot beat every C0b candidate.
- **Beige [M].**
  - library_v3x's beige (3.066) beats the E0b pick (3.322), and so does library_v3's on eval 8 alone.
  - The C1/T1 beige that pack 9a+ ships scores worst on these points (4.569).
  - Public [D]: the C0b beige pick scored 0.30 against T1's 0.25. The E0b beige pick has no score.
- **Cube-ROI clutter [M].**
  - The cube guard fired on 8 of 28 pass-A files and 3 of 19 pass-B files. Two pass-A files (cup eval 20, rack eval 28)
    were still over the limit after the 0.45 m rebuild. Some files hold far more points than E0's: rack eval 30 1.39x,
    cup eval 20 1.35x.
  - Every mesh scores badly on some episodes: pot eval 8 10-12 mm, cup eval 20 13-86 mm. On rack eval 30, C0, library_v3
    and E0 all score about 41 mm (the C0b public rack 25 mm).
  - So ALL-set fidelity is partly a clutter score. [H] The blue cup's merged pick ranks first because it explains the
    eval 20 clutter: 13.45 mm, against 84.6 for C0. Falsified if that ranking changes once eval 20 is left out.
- **Marker balls [M].** The frozen gmg detector found 20-59 balls per object-episode, with radii up to the 12.5 mm top of
  its window.
  - The shipped pot carries 32 balls and no stems. [H] Most are false (B7 dev crop check). This was not checked on these
    files.
  - The beige cup is a lathe and has no ball path.
- **Frame-check thresholds [M].**
  - Pot: centroid 108.6 mm, median distance 12.9 mm, axes 42 / 27 / 36 deg.
  - Rack: metres wide (X15), so they exclude nothing.
  - Beige: reported only. The shipped beige is 2.9 mm and 1.3 / 18.5 / 18.5 deg from the C0b beige pick; the 18.5 deg
    axes are a near-degenerate pair.
- **Pose boards.** The packed mesh also drives AUC, MPPE, RPE and SR. The AUC guard ran on the public C0b picks, not on
  these eval-built meshes.
- **Eval 8 frame.** One beige mesh ships on both eval pairs. Whether eval 8 is in the v3 or the v3x frame is still open
  (PREREG 10 caveat).

## Files
- `jobs/`: the box job (`e0b_box.sh`), staging (`e0b_stage.py`), task lists (`e0b_tasks.py`), helpers (`e0b_prep.py`),
  the pick (`e0b_select.py`) and the chunked frame check (`frame_check_b.py`).
- `scripts/`: `e0b_pull.py`, `e0b_package.py` (re-check and packaging) and `e0b_results.py` (tables).
- `meshes/`: the E0b pick of every object that has one, with build records and `SHA256SUMS`.
- `results/selection_final.json`, `results/RESULTS_TABLES.md`, `results/results_digest.json`.
- `results/box/`: the box's selection, plan, params, frame thresholds, logs, markers, guard, sigma, thickness rows, and the
  check, frame, fidelity and report rows gathered into jsonl files, plus `SHA256SUMS`.
- Bulk observed points: HF store `runs/mesh-20261031-e0b-c8f1c33/results/e0b/pts/`.
