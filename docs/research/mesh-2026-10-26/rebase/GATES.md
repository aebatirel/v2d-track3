# Collision-only re-base of the pot and the pitcher: rules and gates (written before any candidate is measured)

1 Nov 2026, ~06:05 UTC. CPU only, this container, no rental. Labels: [M] measured, [E] estimate, [H] hypothesis,
[R] read from another lane.

## 0. Why, and what is fixed

- **Problem [R].** posefix (`../posefix/README.md` section 5): at the true poses the shipped C0 pot reaches 6.9-8.3 mm
  below the real base (9 of 9 pot episodes), the library_v3 pitcher 7.3 / 10.7 mm. Lifting the POSE cost AUC (gate
  failed), so the geometry is fixed instead.
- **Scope (keen-heisenberg's approval).** Collision only. The submitted visual mesh (`object_mesh_b64`, the CD-O
  board) stays byte-identical, and so does the simulator's visual glb and the URDF `<inertial>`. Only `<collision>`
  changes. If any gate below can only pass by changing a visual mesh, the work stops and says so.
- **Hypothesis [H] (keen-heisenberg, drawdiv-20261031 at f58f638 / ed28734).** A re-based pot cuts ep2's early lid
  failures (8-9 lid onsets before f30 per 20 draws, mass0). Falsifier: focused-pascal's GPU A/B on ep2, not run here.
- **Ground truth.** None is read. Inputs: our own references (the packed ones, or the mass0 ep2 reference), our
  meshes, our table estimate. No scan, mocap, parquet object pose or `*_align`.
- **What was already known before this file** (so nothing below is chosen on it blind):
  - [R] posefix bottoms (above);
  - [R] collcarve2-evalcheck: on eval 1 the packed `ev01` pot reaches 2.28 mm below the table at most on H30 frames
    and 5.1 mm once (f55) on its hand-free frames;
  - [M] step 0 below (which geometry the pack uses, hull counts). No penetration of any packed or candidate geometry
    at any reference frame has been computed by this lane yet.

## 1. Packed collision geometry (step 0) [M / R]

| Set | Reference (md5) | Pot / pitcher collision in the pack | Partner collision |
|---|---|---|---|
| public ep2, mass0 | `refs/mass0s42_glockt/ep2/.../ref_gl_ilc.parquet` e22747bf (s43 copy identical; source `refs/glockt/ep2` ae4dbde8, fingerprint af6b1110), run `20261031-mass-2ed46ea` | URDF `refs/mass0_sf/ep2/assets` d25b8a41: collision = visual glb b5541587 (make_assets of library_v3 `white_pot.glb` b97d460a); FlashCHORD CoACD 1.0.11 at load: **31 hulls**, 890.63 cm3 | lid glb c9a07a18 -> 41 hulls |
| eval 1 | `refs/perc2mck/ep1/.../64333b0b...-0.parquet` 7f230466 | `meshes/carve/ev01/white_pot` (focused-pascal 328139c): **53 pieces** | `ev01/white_pot_lid` 107 pieces |
| evals 3, 5, 6 | glockt refs 732e44ea / aa2f4fc5 / 50445bc3 | `refs/sf/epN/assets`: support fill left the pot as is; collision = b5541587 -> 31 hulls | spoon |
| eval 8 | glockt 9424b5a1 (lib v3x; pot glb identical b5541587) | 31 hulls | beige cup (arc feet) |
| eval 28 | `refs/perc2mck/ep28/.../4327c2f4...-0.parquet` 6f57deb2 | shared `/content/assets`, no pieces -> 31 hulls | rack |
| eval 20 | glockt 4d06d8d4 | `refs/sf/ep20/assets`: pitcher glb adb315f3 (library_v3, not filled) -> **33 hulls** + 8 arc-foot pieces (support_fill, certified at f152) = 41 | blue cup (0.5 cm fill) |

- The CoACD call is FlashCHORD's (`fc_mesh.py`: threshold 0.05, max_convex_hull -1, preprocess auto) with coacd
  1.0.11, the evaluator's pin. It reproduces focused-pascal's `hulls_default` for the v3 pot and lid (31 / 890.6 and
  41 / 325.7 cm3, `meshes/carve/ev01/carve.json`).
- Pieces are passed by `pipeline/make_assets.py --pieces DIR` (`DIR/<obj>/piece_*.obj`, one `<collision>` per piece,
  visual = the library glb) or by `placement_carve.py assets` (an asset copy whose URDF lists the pieces; inertial
  unchanged). With pieces, FlashCHORD keeps each convex piece as one hull.

## 2. Measurement (GT-free)

- **Support.** The reference's own `reconstructed_stage/t3_epNNN_support.usda`: one cylinder, top z = translate z +
  height / 2 (0.600 m in every reference read so far). This is our table estimate, the one the simulator loads.
- **Hands.** Robot hand points = `robot_{left,right}_frames` without 'universe'.
- **Table-rest frames of object o** (T-rest), all four:
  1. H30: no hand point within 30 mm of o's visual mesh surface (2 mm samples);
  2. on the table: the lowest point of o's PACKED collision geometry within +-15 mm of the table top
     (support_fill's NEAR);
  3. not held by a receiver: if the partner ranks above o in rack > pot > blue cup, o's packed pieces are more than
     4 mm from the partner's packed pieces (eval 28: pot in the rack);
  4. static: o's packed vertices move < 2 mm between consecutive frames, in runs of >= 5 frames meeting 1-4.
  The set is fixed from the packed geometry before any candidate exists, and candidates are measured on the same
  frames.
- **Penetration.** p_f = table top - lowest world point of o's collision pieces (mm; > 0 = into the table). Convex
  pieces, so the minimum over vertices is exact.
- **Rest-up axis u.** The mean over T-rest frames of R_f^T e_z (world up in o's frame), normalised; the largest
  deviation of a frame's axis from u is reported.
- **Partner-rest frames** (for G2): frames where the partner q (lid, spoon, cup, rack) is H30, static relative to o
  (q's origin in o's frame moves < 2 mm per frame, runs >= 5), and q's packed pieces are within 4 mm of o's packed
  pieces.
- **Overlap.** Volume of q's packed solid (1.5 mm grid, cell centre inside a piece) inside o's piece union, cm3, with
  the deepest q grid point inside o's pieces (a lower bound on the penetration depth, mm). This is the "pot rim vs
  lid" number for both rules.

## 3. Candidate rules (fixed now)

Both use the same shift d = median over T-rest frames of the signed p_f.
- **Bound.** If d < 1.0 mm the packed set already meets G1's median: no candidate is built ("not needed"). If
  d > 12.0 mm, no candidate is built either (beyond the 7-11 mm mesh offset that motivates the work; it would be a
  pose problem, not the base).
- **(a) translate.** Every collision piece of o moves by d along u, in o's frame.
- **(b) base clip.** Every piece of o is intersected with the half-space u.x >= m + d, where m = min over all piece
  vertices of u.x (the base level along u). Pieces wholly above that plane stay byte-identical. Pieces wholly below
  are dropped. Cut pieces are re-hulled. A cut part smaller than 2e-8 m3 or thinner than a 0.2 mm inscribed ball is
  dropped (placement_carve's debris rule).
- **Convexity.** Translation and half-space intersection keep every piece convex. Checked for each piece: its vertex
  set equals its convex hull (volume within 1e-9 m3), and coacd 1.0.11 at FlashCHORD's settings returns one hull
  for it.
- **The trade.**
  - (a) keeps the base's shape, but it also raises the rim and the handles by d. A lid resting on the rim at the
    reference pose then meets a rim d higher (G2 measures this).
  - (b) leaves the rim, the handles, and any carve (ev01) exactly where they are. It flattens the bottom d above
    the lowest point and removes the slab that sat in the table, so the base footprint is the cut section.
- **Selection, per set.**
  - A candidate passes if G1, G2, G3, G5 and G6 pass (G4 is indicative).
  - If both pass, deliver (b): it changes only the base slab, keeping the lid / spoon interface and the handle the
    hands grasp.
  - If only one passes, deliver that one. If neither passes, deliver nothing for the set. The candidates are then
    kept in `rejected/` with `DO_NOT_USE.json`.
- **Per set.** d is measured per set, on the reference that set is paired with. A pooled pot median over the pot sets
  is reported for comparison only.

## 4. Gates

| Gate | Rule | Note |
|---|---|---|
| G1 | On T-rest frames: max(p_f, 0) median <= 1 mm and max <= 3 mm | binding |
| G2 | On partner-rest frames: overlap(q, candidate o) median and max each <= the packed value + 0.5 cm3 | binding; vacuous (pass, flagged) if there are no partner-rest frames |
| G3 | Hands-free settle (below): o stays within 4 mm and 5 deg of its reference pose at every test frame | binding |
| G4 | Contact counts in plain MuJoCo, same scene, 16 jittered copies: max nefc / ncon, copies over njmax 512 / nconmax 256 | indicative only; flagged if any copy overflows or max nefc > 1.25 x packed. The binding check is determined-wright's FlashCHORD `budget.py` at 32x60, which they run |
| G5 | Visual mesh and inertial unchanged | binding: the folder holds no visual mesh; `make_assets.py --pieces` writes `mesh/<o>/<o>.glb` with the packed md5; the URDF differs from the packed one only in `<collision>` lines; the library and submission glb md5s are unchanged |
| G6 | Piece count of o <= packed count (31, 53 on eval 1, 41 on eval 20) | binding |

**Settle scene (G3, G4).**
- Plain MuJoCo 3.17.0 with the sim=rl options of `docs/research/work/15-verify/cfg_sim_rl.yaml` (sha256 695536b7...;
  dt 0.01 s, Newton, implicitfast, pyramidal, impratio 20, 100 / 50 iterations, njmax 512, nconmax 256).
- Condim 3, friction 1.0, margin 0, MuJoCo default solref / solimp.
- Table = a plane at the support top.
- Every object of the episode is free, at its reference pose, at zero velocity, with the URDF's mass, COM and inertia
  (the packed ones, unchanged).
- o carries the set's pieces (packed or candidate); the partner carries its packed pieces. No hands. 2.0 s.
- Test frames: frame 0 if it is a T-rest frame (the simulator starts there), plus the middles of the up to 3 longest
  T-rest runs.
- Measured: o's origin displacement (mm) and rotation (deg) at 2.0 s against the reference pose at that frame, and the
  maxima over the 2 s. The partner's displacement is reported, not gated.
- G4 adds 16 copies with o jittered 0.5 mm / 0.005 rad (seed 2, as the evalcheck).
- Packed and candidate both run through the same scene, so every number has its packed twin.

## 5. Order, outputs, what is not done here

- Order:
  1. ep2 (the A/B set);
  2. evals 1, 3, 5, 6, 8, 28;
  3. eval 20 (pitcher).
- Each set gets its own folder `sets/<set>/` in the `make_assets.py --pieces` layout (`<obj>/piece_XX.obj`, no
  `inertia.json`, so make_assets keeps the packed COM / inertia), plus `rebase.json` with the numbers.
- README: a numbers table (packed vs candidate), the commands and md5s. Timestamped log: `NOTES.md`.
- **Not done here:** FlashCHORD / MuJoCo-Warp runs, `budget.py`, any training or GPU A/B, any change to a pack or a
  visual mesh. Nothing is tuned on eval scores: there are none in this work.
