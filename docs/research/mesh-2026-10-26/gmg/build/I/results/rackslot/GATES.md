# Gates for the rack slot pieces (evals 30 and 14)

Written 1 Nov 2026, 03:06 UTC (first pushed in f352c79, a WIP snapshot), and pushed **before any candidate was built or measured**. Owner go 02:50 UTC (relayed by
the orchestrator). They apply to every candidate in this folder. Thresholds come from the owner's task unless stated.
Tags: [M] measured, [E] estimate, [H] hypothesis.

Measured before this file, on the packed rack only (no candidate) [M]:
- the rest frames;
- the swept rest volume;
- the pose floor from the precheck (`../collcarve2-evalcheck/per_frame`).

## Amendment 1 (1 Nov 2026, 03:27 UTC), before any candidate was measured

**What prompted it.** The orchestrator relayed the collision-carve round-2 verifiers and report (INTERLOCK 21.15,
commit 2d9bfc5; `../collcarve2-eval/`). The rule's hands-off set is H30, not H0.

**State when it was written.**
- No candidate had been measured.
- One build, c1-ev30 under the H0 rest set, was started at 03:13 and stopped at 03:25 before it finished. It was never
  measured. Its partial log is kept as `c1-ev30-h0-stopped.log`.
- The packed rack had been measured under H0, as a baseline: `meas_h0/`. That run reproduced the precheck's contact
  rows exactly.

**What it supersedes.** Where this section and the text below disagree, this section holds.

1. **Rest frames R.** These are frames that pass all three tests below. There is no run-length condition (H30 already
   drops the in-hand transit frames that the run rule was meant to remove).
   - H30: no robot hand point within 30 mm of either object (the precheck's H30; F-I5.3 (b), F-I5.16 (3)(a)).
   - The guest is in the slot region: at least 1 cm3 of its mesh inside the rack's convex hull and outside the rack
     mesh.
   - No (a) table or (b) float flag.

   | Eval | R | Frames | Left out |
   |---|---|---|---|
   | 30 | f0-2, f4, f244-245, f247-262 | 22 | none: every H30 frame is in the slot, and none is flagged |
   | 14 | f140-157 | 18 | 11 H30 frames, where the cup is not in the slot region |

2. **Gate frames for G3 / G4 / G6** (`rs_lib.gate_frames`, rule fixed here):
   - first, the precheck's contact frames that lie in R;
   - then the middle frame of each other run of R, longest run first;
   - then the R frames at 25 %, 75 % and 50 % of R, until there are 3.

   | Eval | Frames | Why |
   |---|---|---|
   | 30 | f257, f249, f1 | f1: the episode starts with the sweeper resting in the slot |
   | 14 | f149, f144, f153 | |

   The precheck's f17 (eval 30) and f135 / f137 (eval 14) are hands-off under H0 only, so they drop out.
3. **G3 label.** G3 is **plain MuJoCo, indicative only**: validity check c1 failed, because plain MuJoCo over-counts
   against MuJoCo-Warp. determined-wright's FlashCHORD `budget.py` is the binding contact check. G3's thresholds are
   unchanged.
4. **New G6 (reported, no threshold): how far the guest is thrown.** This is the candidate's possible value when the
   pose floor blocks G1 and G4. Two measures, each the median over the 16 copies at each gate frame, for the candidate
   and the packed rack:
   - pair scene (G3; both objects free, sim=rl, 2 s): the guest's displacement, contacts.py's `disp_mm_receiver_guest`
     (the measure behind the round-2 verifiers' "thrown 23-140 mm");
   - S scene (G4; rack fixed): the guest's displacement.

   "Reduces the throw" means the candidate's median over the three gate frames is below the packed rack's. The size of
   the reduction is reported. It is not a pass / fail gate.
5. **Plain statement required in the README.** The precheck shows the visual meshes overlapping at every H30 rest
   frame. In the slot this is a faithful overlap of 1 cm3 or more: eval 30 22 / 22, up to 8.4 cm3; eval 14 18 / 18,
   up to 10.7 cm3 (`../collcarve2-eval/precheck_H30_tables.md`). Wherever that holds, the README states plainly that a
   rack piece set cannot fix the root cause, which is the pose (pose lanes). G1 and G4 are then expected to fail on the
   pose floor, and G6 is reported as the candidate's possible value.
6. **Eval 14's "cup 16.6 mm in the table at f42" is restated.** Under H30, f41-45 are not hands-off: a hand is within
   30 mm, and 3 mm at f42. This is a reference pose problem while the cup is held, not a hands-off rest problem. It
   enters no gate. Over the H30 frames, eval 14's largest table penetration is 3.9 mm, by the rack at f157.

The H0-based R table and frames in "Definitions" and "G3" below are kept for the record. They are superseded by items
1-2.

## Amendment 2 (1 Nov 2026, 03:52 UTC), before any candidate was measured

**What prompted it.** Two development builds, try1 and try2, were made under Amendment 1. They are not candidates and
were never run through `measure.py` or `phys.py`. A construction diagnostic on them (`scripts/diag_left.py`) showed
[M]:
- **Most forbidden cells left inside the pieces touch the mesh surface.** These are cells of F (RV minus the rack
  mesh) whose centre is within 1.0 mm of the rack-mesh surface.

  | Build | Pieces | F left in pieces, cm3 | ... of which within 1.0 mm of the mesh surface, cm3 |
  |---|---|---|---|
  | try2, eval 30 (BSP depth 5) | 107 | 1.32 | 1.20 |
  | try2, eval 14 | 102 | 1.04 | 0.98 |
  | try1, eval 30 (BSP depth 3) | 70 | 2.42 | 1.95 |

- **Such a cell straddles the mesh surface.** At 1 mm resolution it cannot be called "beyond the mesh". A convex piece
  that keeps the mesh cannot drop it without being split at the scale of single cells.
- **Chasing those cells is what drives the piece count up.** Of all F, 2.2 cm3 (eval 30) and 1.9 cm3 (eval 14) lie
  within 0.6 mm of the mesh surface.

**Change.**
- **G2 is judged on G2b.** G2b is the same swept measure (RV inside the candidate pieces, outside the rack mesh, 1 mm
  cells), counting only cells whose centre lies more than b = 0.87 mm from the rack-mesh surface. 0.87 mm is half the
  diagonal of a 1 mm cell (generic, grid resolution). The surface is sampled at 0.3 mm (seed 3). Pass: G2b <= 1.0 cm3.
- **G2 as written (all cells) stays in every table with its own verdict.** The packed rack's G2 is 10.76 cm3 on eval
  30 and 6.88 cm3 on eval 14.
- **The build targets F' = F minus the band.** Merges may add band cells but never an F' cell. Every other gate is
  unchanged.
- **Naming.** The first sets measured are named c1-ev30, c1-ev14 and c1-both, as planned. try1 and try2 stay in the
  record as unmeasured development builds: the log and `build.json` in the scratch folder, and their piece counts and
  leftovers in the table above.

## Definitions

- **Frame of work.** Everything is measured in the rack's link frame. The guest is placed there by the packed
  reference's guest-in-rack relative pose at each frame, read from the precheck's pose npz, which was built from the
  packed references:
  - eval 30: `refs/perc2mcks/ep30/.../a2eb7d27...-0.parquet`, md5 dd464c96..., run 20261025-std30-ee7ba8e;
  - eval 14: `refs/glockt/ep14/.../ref_gl_ilc.parquet`, md5 10d5f3ba..., run 20261025-evb1420-ee7ba8e.
- **Packed rack.** FlashCHORD's CoACD of the library_v3 rack at load: coacd 1.0.11, threshold 0.05, 43 hulls,
  1,210.6 cm3 (`<scratch>/evck/out/packed/rack_lib.npz`, md5 c0742888...). Eval 14's sf rack is the same mesh vertex
  for vertex.
- **Guest collider.** The guest's packed pieces, unchanged: the sweeper's 19 hulls, the cup's 76 (coacd 1.0.11 of the
  packed visual mesh).
- **Rest frames R.** Frames in maximal runs of at least 5 consecutive frames (informed: F-I1.1 run length) that meet all
  of these:
  - hands-off: no contact label in either hand (the precheck's H0);
  - the guest's mesh lies at least 1 cm3 inside the rack's convex hull and outside the rack mesh (the guest is in the
    slot region);
  - no (a) table flag (more than 4 mm in the table) and no (b) float flag. A pose that fails those is impossible, and
    no collider change fixes it.

  | Eval | R | Frames | Hands-off slot frames left out |
  |---|---|---|---|
  | 30 | f0-29, f124-128, f241-262 | 57 | f123 (a), f191 (b), f192-195 (a run of 4) |
  | 14 | f118-157 | 40 | f39 (b), f40 (a run of 1), f41-45 (a: the cup is 11.6-15.7 mm inside the table) |

  Eval 14's f41-45 are the flagged reference problem. They are reported, and the table is not carved.
- **Rest volume RV.** The union over R of the guest's packed pieces, with every hull plane pushed out by a clearance
  c = 1.0 mm (informed: F-I5.10 c_0 1.0 mm, the F-I1.14 clearance). It is evaluated on the 1 mm cells of the packed
  rack.
- **Grids.**
  - Rack occupancy: 1 mm cell centres. The rack mesh uses exact vertical-ray parity; pieces use centre-inside
    (the precheck's method).
  - Guest points: 1.5 mm cell centres of the guest's packed union (or of its mesh), as in the precheck.
  - Volumes are cell counts times cell volume.
- **Floors** (they do not depend on the candidate):
  - V_vv(f): the guest mesh inside the rack mesh. This is the precheck's V_visual, the pose floor.
  - V_pm(f): the guest's packed pieces inside the rack mesh. This is the floor for any rack set that keeps the rack
    mesh and the guest's pieces.

## Gates

| Gate | Measure | Pass |
|---|---|---|
| **G1** (the owner's gate as written) | V_pp(f): the guest's packed pieces inside the candidate rack pieces (the precheck's V_packed) over R. V_vv and V_pm are reported beside it | median <= 1.0 cm3 and max <= 3.0 cm3 |
| **G1x** (the rack's share of G1) | E(f) = V_pp(f) - V_pm(f) over R | median <= 1.0 cm3 and max <= 3.0 cm3 |
| **G2** | Volume of RV inside the candidate pieces but outside the rack mesh (1 mm cells). Also reported: the per-frame maximum over R of the same, with the guest's packed pieces and with its mesh. The mesh version is the precheck's "beyond the mesh" number (packed: 10.4 cm3 on eval 30, 10.5 on eval 14, maxima over all frames) | <= 1.0 cm3 |
| **G3** | Contacts in the pair scene: the precheck's `contacts.py` unchanged. Plain MuJoCo 3.17.0 with the sim=rl options from `cfg_sim_rl.yaml` (sha256 checked); both objects free, 0.3 kg; table plane; 16 copies with the S jitter (seed 2); 2 s. Frames: the precheck's three (eval 30: f257, f249, f17; eval 14: f149, f135, f137; all in R) | no overflow copy; max nefc <= 512; max ncon <= 256 |
| **G4** | Hands-off settle: collcarve's S, `gmg.simphys.sink_test` called as collcarve calls it. The rack is fixed at its tracked pose; the guest starts free at its tracked pose composed with the jitter; 16 copies, seed 2; table plane; 2 s at 2 ms; guest mass 0.3 kg, COM and inertia from `simpieces.props` of its pieces. Same three frames as G3 | the S rule (mean displacement <= 4 mm, mean tilt <= 5 deg, no NaN copy, no copy below the rack's lowest point) and no fall-through (no copy whose guest COM drops more than 4 mm along gravity; informed: the 4 mm s_max sink bound), at all three frames |
| **G5** | Kept volume: (candidate ∩ packed ∖ RV) / (packed ∖ RV), on 1 mm cells | >= 0.90 |

How G1 and G1x are judged:
- The candidate keeps the rack mesh and the guest's pieces, so V_pp(f) >= V_pm(f) >= V_vv(f), up to discretisation.
- The precheck already shows V_vv at R of 5.1-10.9 cm3 on eval 30 and 7.2-12.3 cm3 on eval 14 [M]. G1 as written
  therefore cannot pass for any rack set that keeps the rack mesh.
- It is still reported. Where V_pm alone exceeds the threshold, the verdict reads "FAIL (pose floor)".
- The candidate is judged on G1x: the same thresholds, applied to the overlap the rack pieces add beyond that floor.
- Whether a candidate that fails G1 only on the floor is used is the owner's or orchestrator's call.

The packed rack is measured on every gate as the baseline, in the same run and with the same code. Its G3 numbers are
also a reproduction check against the precheck.

## Construction checks (required)

- **C1.** At most 43 pieces, the packed count, unless a reason is written in the README before delivery.
- **C2.** The rack mesh is not cut:
  - rack-mesh 1 mm cells covered by the packed pieces but not by the candidate: <= 0.1 cm3 (generic: 1 mm
    discretisation);
  - the farthest rack-mesh surface sample (0.25 mm spacing, seed 7, a different draw from the one used in the build)
    inside the packed pieces but outside the candidate: <= 0.5 mm.
- **C3.** Each piece is one convex hull. Each piece file must:
  - be a watertight convex mesh with positive volume;
  - come back from coacd 1.0.11 with FlashCHORD's settings (threshold 0.05, max_convex_hull -1, preprocess auto) as
    one part, whose hull volume is within 1 % of the piece's.

## Candidates, order and delivery rule

- **Order.** Candidates are built and measured in this order:
  1. `c1-ev30` (cut against eval 30's RV);
  2. `c1-ev14` (against eval 14's RV);
  3. `c1-both` (against the union of both RVs, measured on both episodes).
- **No in-place fixes.** A candidate is never changed after it is measured. A fix is a new candidate (`c2-...`), and
  every candidate and its numbers stay in this folder.
- **Delivery, per episode.** The first candidate in build order that passes G1x, G2, G3, G4, G5 and C1-C3 for that
  episode is delivered as a CANDIDATE (G1 is reported as above). One set serves both episodes only if it passes both
  episodes' gates.
- **No eval scores.** Nothing here is tuned on eval results (scores). The gates use our own packed references and
  meshes only.
- **Final contact gate.** It is determined-wright's FlashCHORD `budget.py` on each delivered set. The pair scene here
  (G3) is the first gate only.
