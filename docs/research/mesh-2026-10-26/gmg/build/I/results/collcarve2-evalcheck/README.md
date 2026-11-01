# Eval precheck of the collision carve, round 2: the packed references and the packed colliders

1 Nov 2026, 00:14-01:45 UTC. Diagnostic only: it decides nothing, nothing is tuned on it, and nothing is carved on any
eval episode. CPU on this container (4 shared cores, load 10-13), no rental, $0.
Rules: PREREG F-I5.15 (3) (the pose precheck) and F-I5.16 (3) (contact numbers).
Tags: [M] measured here, [R] read from another lane, [E] estimate, [H] hypothesis.

## In plain words

We took the references the packed eval policies were trained on and the collision shapes the simulator gives each
object, and asked four things at every frame where no hand touches either object:
1. Do the two objects overlap?
2. Does an object sink into the table?
3. Does an object float with nothing under it?
4. Does the collision shape fill a hollow, such as a cup or a rack slot, where the reference puts the other object?

We also counted the contacts the simulator would need for each pair under the training limits.

Findings:
- **Eval 10 (beige cup in blue cup).** The packed collision pieces of the two cups still overlap at the nested rest:
  12 cm3 in the median hands-off frame of f124-f160 (3.4-32.7 cm3). Dropped into the training simulator settings, this
  pair alone needs 656-1,296 constraint rows and 164-324 contacts, against limits of 512 and 256. Every copy is already
  over the 512-row limit at step 0 (129-320 contacts, 516-1,280 rows). That overflows in all 16 copies at all three test frames.
  No other eval pair overflows.
- **Evals 14 and 30 (rack).** The rack's packed collider (CoACD) fills part of the slot the reference puts the cup (14)
  or the sweeper (30) in, beyond what the rack mesh itself fills:
  - 10.5 cm3 and 10.4 cm3 at most beyond the mesh, in 60 and 190 frames;
  - collider overlap of 16 cm3 in the median overlapping hands-off frame, up to 38 cm3 (14) and 22 cm3 (30).
  - In eval 14 the cup also sits 16.6 mm inside the table at f42.
- **Eval 1 (lid on pot).** The packed carve pieces (`ev01`) do their job: at hands-off frames the packed pot and lid do
  not overlap. Their meshes do overlap, 29 cm3 in the median hands-off frame, so on faithful copies of the meshes every
  hands-off frame fails the overlap check.
- **Evals 15 and 16 (spoon and rack).** Nothing fills the rack's slots (at most 0.7-1.0 cm3). The spoon floats in
  19-23 hands-off frames, up to 44-61 mm from any support. Eval 15 does have a rack seat: the reference puts the spoon
  between the rack's plates in 58 hands-off frames, just as in eval 16.
- **Evals 32 and 33 (spoon in blue cup).** These reproduce the earlier spoon diagnostic (`cdo-sprint/spoon-diag`) to
  within 0.1 cm3:
  - The spoon is in the cup only while it is held.
  - What blocks it is the cup mesh itself: up to 9.8 cm3 and 19 mm deep at f155-161 of eval 33.
  - The packed pieces add at most 1.0 cm3 beyond the mesh.
  - In eval 32 the cup sits 19.5 mm inside the table at the hands-off frames f32-f33, and 35.6 mm at f20.

## Summary table (hands-off frames H0: no hand-contact label in the reference)

Faithful = the packed visual mesh's 2 mm cells. Packed = the simulator's convex pieces. "Frames failing" counts frames
where a mesh is more than 4 mm inside the table, an object floats more than 4 mm from any support, or the faithful
overlap is 1 cm3 or more. The (a / b / c) counts are per object, so they can add up to more than the frame count.
Contacts come from the pair scene under sim=rl, maxima over 3 frames x 16 copies.

| Eval | Receiver <- guest | Pieces R / G | H0 frames / all | Frames failing (a / b / c) | Max overlap, faithful / packed, cm3 | Max table penetration, mm | Max float, mm | Packed collider blocks a cavity the reference fills? | Pair-scene max nefc / ncon, overflow copies |
|---|---|---|---|---|---|---|---|---|---|
| 10 | blue cup <- beige cup | 53 / 49 (`ev10`) | 52 / 161 | 37 (0 / 0 / 37) | 88.5 / 32.7 | 1.5 | 1.5 | **yes**: packed-vs-packed 11.9 cm3 median at the hands-off nested rest f124-f160 (3.4-32.7); beige mesh in blue pieces beyond the blue mesh up to 11.3 cm3 (78 frames) | **1,296 / 324, 48 / 48 (overflow)** |
| 1 | pot <- lid | 53 / 107 (`ev01`) | 56 / 335 | 56 (0 / 0 / 56) | 34.9 / 0 | 2.4 | 0 | no (lid mesh in pot pieces <= 1.07 cm3; the mesh overlap is mesh-on-mesh) | 420 / 105, 0 / 48 |
| 14 | rack <- blue cup | 43 / 76 | 63 / 158 | 47 (5 / 1 / 46) | 24.9 / 38.2 | **16.6** (cup, f42) | 13.8 (cup, f39) | **yes**: beyond the rack mesh up to 10.5 cm3 (60 frames); packed overlap 16.4 cm3 median over the 46 overlapping hands-off frames | 312 / 78, 0 / 48 |
| 15 | rack <- spoon | 43 / 10 | 92 / 166 | 24 (1 / 23 / 0) | 0.34 / 0.73 | 5.1 (spoon, f30) | **61.0** (spoon, f62) | no (spoon in a rack seat in 58 hands-off frames; <= 0.73 cm3 in the pieces) | 184 / 46, 0 / 48 |
| 16 | rack <- spoon | 43 / 10 | 86 / 173 | 19 (0 / 19 / 0) | 0.11 / 0.71 | 2.5 (rack, f137) | **44.3** (spoon, f34) | no (<= 0.97 cm3 in the pieces, any frame) | 252 / 63, 0 / 48 |
| 30 | rack <- sweeper | 43 / 19 | 63 / 263 | 59 (1 / 1 / 58) | 11.1 / 22.1 | 4.7 (sweeper, f123) | 5.1 (sweeper, f191) | **yes**: beyond the rack mesh up to 10.4 cm3 (190 frames); packed overlap 15.5 cm3 median over the 58 overlapping hands-off frames | 324 / 81, 0 / 48 |
| 32 | blue cup <- spoon | 72 / 11 (sf) | 21 / 259 | 6 (6 / 0 / 0) | 0 / 0 | **19.5** (cup, f33) | 1.2 | no (spoon in the cup only in hand; beyond the mesh <= 0.68 cm3) | 356 / 89, 0 / 48 |
| 33 | blue cup <- spoon | 76 / 10 | 30 / 348 | 4 (0 / 7 / 0) | 0 / 0 | 1.7 | >= 100 (spoon, f70) | marginal: 1 frame at 1.01 cm3 beyond the mesh (f157); the mesh itself blocks 20 frames (<= 9.77 cm3, 19 mm deep) | 436 / 109, 0 / 48 |

All numbers are [M]. Frame numbers are reference frames at 20 fps. For eval 32, "sf" marks the support-filled cup and
spoon of `refs/sf/ep32/assets`. The full tables are in section 4: all frames, and the per-object hand-free frames.

**P103** (F-I5.16 (4)) says no eval pair's packed pieces overflow in the pair scene. It is **falsified on eval 10**
(16 / 16 copies at all three frames). Its second leg, budget.py reproducing eval 25 within 2 %, was not run (section 6).

## 1. Inputs (integrity)

- **References.** Taken from focused-pascal's `docs/research/work/masses-eval-20261031/packed_refs.json`
  (origin/claude/focused-pascal-2nz9s1 at c6fe323). Downloaded from the HF store `aebatirel/v2d-store` (37 MB, to
  `<scratch>/evck/dl`). All eight md5s match the list (`inputs/dl_report.json`, `inputs/cfg.json`).
  - Eval 1: the listed `refs/perc2mcks/ep1/...` copy is not in the store. Its byte source
    `refs/perc2mck/ep1/processed/.../64333b0b...-0.parquet` has the listed md5 `7f230466`, so that file was used.
- **What is read from the references.** These are our own perception (tier P1), GT-free.
  - Columns read: `object_body_names / _position / _wxyz`, `object_mesh_paths`, `object_urdf_paths`, `fps`,
    `robot_{left,right}_frames` (hand points; 'universe' dropped), `mano_{left,right}_object_contact_part_ids /
    _positions` (the reference's hand-contact labels) and `sequence_id`.
  - Not read: no scan, mocap, dataset parquet `pose` field or `*_align` file. No eval result was tuned on.
- **Table.** The reference's `reconstructed_stage/t3_epNNN_support.usda`: one cylinder each, top at z = 0.600 m,
  radius 0.24-0.34 m.
- **Collision source per object: the URDF the simulator loads (`object_urdf_paths`).**
  - Found [M]: `object_mesh_paths` says `/content/assets/mesh/...` for every object. But the URDFs of evals 14, 15, 16,
    32 and 33 point at `refs/sf/epN/assets`.
  - These are library_v3 vertex for vertex, except the eval-32 cup (405.0 cm3, 72 hulls) and spoon (99.7 cm3, 11 hulls),
    which are the support-filled variants (as in spoon-diag).
  - Shared `/content/assets` (evals 1, 10, 30) = `make_assets.py` on library_v3: visual = collision = the library glb.
    Where `--pieces` is set, there is one `<collision>` per carve piece:
    - `meshes/carve/ev10`: identical on both branches; blue 53 and beige 49 pieces.
    - `meshes/carve/ev01`: from focused-pascal; pot 53 and lid 107 pieces.
    - Each piece is kept as one hull ("FlashCHORD's CoACD keeps each convex piece as one hull", `make_assets.py`).
- **Packed decomposition** (`scripts/packed_coacd.py`, `inputs/packed_coacd_report.json`).
  - It is FlashCHORD's own call, `fc_mesh.py:62-90`: coacd **1.0.11** from a separate pip target, threshold 0.05,
    max_convex_hull -1, preprocess auto, with the mesh loaded by `trimesh.load(force='mesh')`.
  - It reproduces the 26 Oct hull census [M vs R]:

    | Object | Here | 26 Oct census |
    |---|---|---|
    | Spoon | 10 hulls / 97.51 cm3 | 10 / 97.5 |
    | Rack | 43 / 1,210.61 | 43 / 1,210.6 |
    | Cup | 76 / 449.91 | 75 / 450.4 |

    Also computed: sweeper 19 hulls, eval-32 cup 72 and eval-32 spoon 11.
- **Why the scripts are standalone.** The gmg guard refuses `.parquet` and `library_v3` paths. Both are this
  diagnostic's inputs: the pack's own references and simulator assets, which are measured here. They are never used as
  shape evidence for any mesh of ours. Library meshes enter only as the pack's colliders.

## 2. Method

**Colliders per object**, all in the object's link frame:
- **Visual:** the URDF's collision source mesh, i.e. the packed visual mesh, voxelised by exact vertical-ray parity on
  a 1 mm grid.
- **Faithful:** the same mesh's 2 mm cells, centre inside (F-I5.15 (3)). Exact parity at 2 mm, the same cells as
  `cavpieces.faithful_boxes`.
- **Packed:** the union of the convex pieces, centre-inside on a 1 mm grid.

**Per frame and pair** (receiver R by role: rack > pot > blue cup; guest G = the partner):
- Overlap volumes:
  - faithful: G's 2 mm cell centres inside R's cells, as `collcarve.precheck` (c);
  - packed: G's packed solid at 1.5 mm inside R's packed solid;
  - visual: G's mesh solid at 1.5 mm inside R's mesh solid.
- Table penetration: the lowest faithful corner, mesh vertex and piece vertex below z = 0.600.
- Float: the distance of each object to the table or to the partner. Faithful version: cube distance between the cell
  sets. Mesh version: surface samples at 2 mm. Distances are capped at 100 mm.
- Cavity question:
  - the guest's mesh solid inside R's convex hull but outside R's mesh solid (the guest is in R's cavity or slot
    region, counted at >= 1 cm3);
  - inside R's packed pieces;
  - inside the pieces but outside R's mesh (what the packed collider adds);
  - the deepest guest point in R's pieces (distance to the piece surfaces, a lower bound).

**Frame sets:**
- H0 (primary, "a hand is not in contact"): no contact label (`mano_*_object_contact_part_ids` > 0) in either hand.
  These labels are the episode's hands output.
- H30: no robot hand point within 30 mm of either object's mesh (F-I5.3 (2)).
- Per object: frames with no label point attributed to that object. A label point is attributed to the nearest object
  surface; label ids were not trusted, since they are ambiguous in eval 10.
- All frames, for reference.

**Fail flags.** Thresholds with origins:
- (a) table: more than s_max = 4 mm below the table (F-I5.15 (3), informed F-I1.14).
- (b) float: more than 4 mm from the table and from the partner (same origin).
- (c) faithful overlap of 1 cm3 or more. Informed: the spoon-diag frame threshold. Frames with overlap > 0 are counted
  in the JSON.
- F-I5.15 (3c) fails only when the overlap is also not carvable (an exact boolean, 1 mm topology, wall rays). That
  carvability sub-check was **not** run here: it needs the gmg carve machinery on library meshes, which the guard
  refuses. Overlap is reported as volume.

**Contact numbers** (`scripts/contacts.py`; F-I5.16 (3)(a), G1 pair scene):
- Scene: both objects free, 0.3 kg each, with COM and inertia from the pieces' union. Table plane at the support top.
- Engine: plain MuJoCo 3.17.0 with the sim=rl options read from `docs/research/work/15-verify/cfg_sim_rl.yaml`
  (sha256 `695536b7...4b66`, checked): dt 0.01 s, Newton, implicitfast, pyramidal, impratio 20, 100 / 50 iterations,
  njmax 512, nconmax 256. Condim 3, friction 1.0.
- Copies: 16, with the S jitter draws (seed 2: 0.5 mm / 0.005 rad on the guest), 2 s each.
- Overflow: ncon > 256, nefc > 512 or a CONTACTFULL / CNSTRFULL warning in any step.
- Frames: the middles of the 3 longest F-I1.1 static stretches (guest origin in the receiver frame moving < 2 mm per
  frame for >= 5 frames) in which the packed colliders are within 4 mm, hands-off (H30, then H0) first.
- **Post-hoc fallback (this step, not in F-I5.16):** most references jitter by 1-5 mm per frame even at rest (eval 10
  [M]), so few stretches qualify. Missing slots are filled with the middles of the longest H0 runs with the packed
  colliders within 4 mm (`not_static`), then of any such runs (`in_hand`). Evals 32 and 33 have no hands-off frame
  with the spoon near the cup, so all their frames are `in_hand`.

## 3. Findings by episode [M]

- **Eval 10.**
  - At the nested hands-off rest (f124-f160), the beige mesh lies 80.8 cm3 inside the blue mesh (median; visual and
    faithful agree). That is the blue mesh's solid fill (cavity 38.7 % solid, spoon-diag) plus the 3-5 mm off-axis pose.
  - The packed `ev10` pieces were built so that "the reference nest fits" (beige radius shrunk 8 mm, blue wall
    wedges). On this reference they still overlap at every one of those frames: 11.9 cm3 median, 3.4-32.7 cm3, at
    most 3.2 mm deep.
  - The beige pieces are 303 cm3, of which 275 cm3 lies outside the beige mesh (shrunk thick-wall lathe pieces).
  - That overlap is what overflows: 129-320 contacts (516-1,280 rows) already at step 0 of the copies, and 164-324
    contacts / 656-1,296 rows at the maxima, all guest-receiver.
  - Not flagged by (a) or (b) at hands-off frames.
- **Eval 1.**
  - The packed lid and pot pieces do not touch at hands-off frames: 0 cm3, median gap 3.6 mm.
  - The meshes overlap, 29 cm3 median: the `ev01` placement carve removed exactly that overlap (its README: 50 -> 0
    cm3).
  - The pot reaches 5.1 mm below the table once, at f55, in its hand-free frames.
  - Contact rows reach 420 (f288, in hand) with no overflow: the closest pair to the 512 limit after eval 10, together
    with eval 33 (436).
- **Eval 14.**
  - The cup in the rack: the faithful overlap reaches 24.9 cm3 and the packed overlap 38.2 cm3 at f42 (hands-off).
  - At the same frame the cup is 16.6 mm inside the table (5 hands-off frames over 4 mm).
  - The rack's CoACD pieces add up to 10.5 cm3 beyond the rack mesh in the cup's region (60 frames).
  - Focused-pascal's `ev14` placement carve (overlap 16.7 -> 0 cm3) is **not** in the packed config
    (`pieces: null`) [R].
- **Eval 30.**
  - The sweeper in the rack: packed overlap 15.5 cm3 median over the 58 overlapping hands-off frames, up to 22.1 cm3
    (34.5 cm3 in any frame).
  - Beyond the rack mesh up to 10.4 cm3, in 190 of 238 in-slot frames.
  - `ev30` ("the sweeper falls through the carved slot", do-not-use) is rightly not packed [R].
- **Evals 15 and 16.**
  - The spoon sits in the rack's slot region in 92 frames each (58 / 55 hands-off).
  - The packed rack never holds more than 0.97 cm3 of it, and it is free (<= 0.1 cm3) in 84 / 71 of those frames.
  - The spoon floats: 23 / 19 hands-off frames are more than 4 mm from the rack and the table, up to 61 / 44 mm. This
    confirms spoon-diag's eval-16 finding (1-8 mm off the rack, 16-26 mm above the table) and shows the same on eval 15.
- **Evals 32 and 33.** Against spoon-diag (coacd 1.0.14 there; 1.0.11 and our cavity definition here):

  | | Eval 33 here | Eval 33 spoon-diag | Eval 32 here | Eval 32 spoon-diag |
  |---|---|---|---|---|
  | Spoon in the cup mesh | 9.77 cm3 | 9.77 cm3 | 2.58 cm3 | 2.58 cm3 |
  | Spoon in the cup pieces | 10.73 cm3 | 10.71 cm3 | 3.25 cm3 | 3.20 cm3 |
  | Pieces only (beyond the mesh) | 1.01 cm3 | 1.01 cm3 | 0.68 cm3 | 0.63 cm3 |
  | Frames > 1 cm3 (mesh / pieces) | 20 / 22 | 20 / 22 | 3 / 5 | 3 / 5 |
  | Deepest point in the mesh | 19.0 mm | 19.0 mm | 6.0 mm | 6.0 mm |
  | Collider vs collider | 15.92 cm3 | 15.81 cm3 | 4.53 cm3 | 4.42 cm3 |

  - In-cavity frames: 64 here against 66 in spoon-diag (eval 33; 28 against 30 for eval 32). The difference is the
    cavity definition: the convex hull minus the solid here, a cylinder there.
  - No in-cavity frame is hands-off.
  - The eval-32 cup is 19.5 mm inside the table at hands-off f32-f33, and 35.6 mm at f20 (in hand; faithful
    boxes, 34.5 mm on the mesh).

## 4. Full tables [M]

Generated by `scripts/tables.py` from `evalcheck_summary.json`.

### Precheck, hands-off frames (H0)

| Eval | Receiver <- guest | Pieces R / G | Frames (H0) / all | Failing: any (a table / b float / c overlap >= 1 cm3) | Max overlap, faithful 2 mm boxes, cm3 | Max overlap, packed pieces, cm3 | Max table penetration, faithful, mm | Max float, faithful, mm |
|---|---|---|---|---|---|---|---|---|
| 10 | blue cup <- beige cup | 53 / 49 | 52 / 161 | 37 (0 / 0 / 37) | 88.5 (f143) | 32.67 (f124) | 1.45 (f8) beige cup | 1.47 (f3) blue cup |
| 1 | pot <- lid | 53 / 107 | 56 / 335 | 56 (0 / 0 / 56) | 34.86 (f326) | 0 (f0) | 2.41 (f28) pot | 0 (f0) pot |
| 14 | rack <- blue cup | 43 / 76 | 63 / 158 | 47 (5 / 1 / 46) | 24.94 (f42) | 38.18 (f42) | 16.59 (f42) blue cup | 13.77 (f39) blue cup |
| 15 | rack <- spoon | 43 / 10 | 92 / 166 | 24 (1 / 23 / 0) | 0.34 (f153) | 0.73 (f153) | 5.05 (f30) spoon | 61.02 (f62) spoon |
| 16 | rack <- spoon | 43 / 10 | 86 / 173 | 19 (0 / 19 / 0) | 0.11 (f116) | 0.71 (f166) | 2.46 (f137) rack | 44.27 (f34) spoon |
| 30 | rack <- sweeper | 43 / 19 | 63 / 263 | 59 (1 / 1 / 58) | 11.1 (f23) | 22.09 (f127) | 4.74 (f123) sweeper | 5.07 (f191) sweeper |
| 32 | blue cup <- spoon | 72 / 11 | 21 / 259 | 6 (6 / 0 / 0) | 0 (f26) | 0 (f26) | 19.52 (f33) blue cup | 1.17 (f26) spoon |
| 33 | blue cup <- spoon | 76 / 10 | 30 / 348 | 4 (0 / 7 / 0) | 0 (f0) | 0 (f0) | 1.68 (f342) spoon | >= 100 (f70) spoon |

### Precheck, all frames (hands included, report only)

| Eval | Receiver <- guest | Pieces R / G | Frames | Failing: any (a / b / c) | Max overlap, faithful, cm3 | Max overlap, packed, cm3 | Max table penetration, faithful, mm | Max float, faithful, mm |
|---|---|---|---|---|---|---|---|---|
| 10 | blue cup <- beige cup | 53 / 49 | 161 | 118 (6 / 41 / 87) | 93.12 (f108) | 36.2 (f105) | 11.38 (f94) blue cup | 87.11 (f40) beige cup |
| 1 | pot <- lid | 53 / 107 | 335 | 234 (8 / 114 / 113) | 36.91 (f298) | 1.15 (f267) | 6.99 (f248) lid | >= 100 (f149) pot |
| 14 | rack <- blue cup | 43 / 76 | 158 | 128 (6 / 66 / 62) | 24.94 (f42) | 38.18 (f42) | 16.59 (f42) blue cup | >= 100 (f33) blue cup |
| 15 | rack <- spoon | 43 / 10 | 166 | 80 (1 / 79 / 0) | 0.34 (f153) | 0.73 (f153) | 5.05 (f30) spoon | >= 100 (f57) spoon |
| 16 | rack <- spoon | 43 / 10 | 173 | 69 (0 / 69 / 0) | 0.74 (f87) | 0.97 (f87) | 3.66 (f100) spoon | >= 100 (f66) spoon |
| 30 | rack <- sweeper | 43 / 19 | 263 | 232 (15 / 46 / 186) | 19.02 (f226) | 34.53 (f226) | 5.65 (f115) sweeper | 60.93 (f177) sweeper |
| 32 | blue cup <- spoon | 72 / 11 | 259 | 170 (19 / 254 / 3) | 2.61 (f154) | 4.53 (f154) | 35.64 (f20) blue cup | >= 100 (f68) spoon |
| 33 | blue cup <- spoon | 76 / 10 | 348 | 253 (21 / 370 / 21) | 9.94 (f159) | 15.92 (f159) | 23.65 (f90) blue cup | >= 100 (f63) spoon |

In-hand frames float by construction (the hand holds the object up), so (b) is meaningful only on hands-off frames.

### Cavity question (all frames)

| Eval | Guest in receiver's cavity region (>= 1 cm3): frames, all / hands-off | Max guest mesh in receiver pieces, cm3 | ... in receiver mesh, cm3 | ... in the pieces beyond the mesh, cm3 (cavity frames >= 1 cm3) | Cavity frames with <= 0.1 cm3 in the pieces | Max depth into the pieces, mm (lower bound) | Packed collider adds a block? |
|---|---|---|---|---|---|---|---|
| 10 | 92 / 37 | 60.88 (f104) | 93.53 (f116) | 11.31 (f104) (78) | 5 / 92 | 3.2 (f146) | yes |
| 1 | 119 / 56 | 1.07 (f267) | 37.24 (f298) | 0.36 (f267) (0) | 115 / 119 | 5 (f267) | no |
| 14 | 71 / 47 | 35.55 (f42) | 25.02 (f42) | 10.52 (f42) (60) | 5 / 71 | 10.73 (f43) | yes |
| 15 | 92 / 58 | 0.73 (f153) | 0.34 (f153) | 0.54 (f110) (0) | 84 / 92 | 4.39 (f153) | no |
| 16 | 92 / 55 | 0.97 (f87) | 0.64 (f87) | 0.7 (f166) (0) | 71 / 92 | 6.26 (f123) | no |
| 30 | 238 / 63 | 29.29 (f226) | 19.21 (f225) | 10.43 (f221) (190) | 37 / 238 | 11.55 (f31) | yes |
| 32 | 28 / 0 | 3.25 (f154) | 2.58 (f154) | 0.68 (f154) (0) | 10 / 28 | 6.36 (f153) | no |
| 33 | 64 / 0 | 10.73 (f159) | 9.77 (f159) | 1.01 (f157) (1) | 31 / 64 | 8.07 (f160) | yes, 1 frame |

For eval 10 the guest's own collider is the shrunk beige pieces, so the packed-vs-packed overlap (precheck tables) is
the more relevant number there.

### Contact numbers (pair scene, sim=rl limits, 16 copies x 2 s) — `eval_contact_precheck.json`

| Eval | Pieces R + G | Frame (pick, hands) | Max ncon | Max nefc | Overflow copies | At the max-nefc step: guest-receiver / guest-table / receiver-table contacts |
|---|---|---|---|---|---|---|
| 10 | 53 + 49 | f111 (static, in_hand) | 313 | 1252 | **16 / 16** | 313 / 0 / 0 |
| 10 | 53 + 49 | f142 (not_static, H0) | 164 | 656 | **16 / 16** | 164 / 0 / 0 |
| 10 | 53 + 49 | f116 (not_static, in_hand) | 324 | 1296 | **16 / 16** | 324 / 0 / 0 |
| 1 | 53 + 107 | f10 (static, H30) | 60 | 240 | 0 / 16 | 55 / 0 / 5 |
| 1 | 53 + 107 | f288 (static, in_hand) | 105 | 420 | 0 / 16 | 75 / 0 / 30 |
| 1 | 53 + 107 | f40 (static, in_hand) | 64 | 256 | 0 / 16 | 47 / 0 / 17 |
| 14 | 43 + 76 | f149 (static, H30) | 75 | 300 | 0 / 16 | 15 / 0 / 60 |
| 14 | 43 + 76 | f135 (static, H0) | 65 | 260 | 0 / 16 | 28 / 0 / 37 |
| 14 | 43 + 76 | f137 (not_static, H0) | 78 | 312 | 0 / 16 | 15 / 0 / 63 |
| 15 | 43 + 10 | f120 (not_static, H0) | 46 | 184 | 0 / 16 | 4 / 4 / 38 |
| 15 | 43 + 10 | f157 (not_static, H0) | 45 | 180 | 0 / 16 | 2 / 0 / 43 |
| 15 | 43 + 10 | f138 (not_static, H0) | 42 | 168 | 0 / 16 | 4 / 0 / 38 |
| 16 | 43 + 10 | f155 (not_static, H0) | 63 | 252 | 0 / 16 | 4 / 4 / 55 |
| 16 | 43 + 10 | f120 (not_static, H0) | 26 | 104 | 0 / 16 | 2 / 1 / 23 |
| 16 | 43 + 10 | f132 (not_static, H0) | 41 | 164 | 0 / 16 | 4 / 4 / 33 |
| 30 | 43 + 19 | f257 (static, H30) | 76 | 304 | 0 / 16 | 4 / 0 / 72 |
| 30 | 43 + 19 | f249 (static, H30) | 66 | 264 | 0 / 16 | 17 / 0 / 49 |
| 30 | 43 + 19 | f17 (static, H0) | 81 | 324 | 0 / 16 | 11 / 0 / 70 |
| 32 | 72 + 11 | f151 (not_static, in_hand) | 58 | 232 | 0 / 16 | 18 / 2 / 38 |
| 32 | 72 + 11 | f82 (not_static, in_hand) | 52 | 208 | 0 / 16 | 0 / 0 / 52 |
| 32 | 72 + 11 | f90 (not_static, in_hand) | 89 | 356 | 0 / 16 | 35 / 27 / 27 |
| 33 | 76 + 10 | f219 (not_static, in_hand) | 64 | 256 | 0 / 16 | 24 / 8 / 32 |
| 33 | 76 + 10 | f158 (not_static, in_hand) | 63 | 252 | 0 / 16 | 63 / 0 / 0 |
| 33 | 76 + 10 | f93 (not_static, in_hand) | 109 | 436 | 0 / 16 | 42 / 23 / 44 |

- The rack alone on the table makes 23-72 contacts: its 43 hulls land on the plane, about 4 per hull.
- In the full scene, hands and support take about half of determined-wright's packed eval-25 budget (276 rows max)
  [R]. So pair-scene numbers of 420-436 (evals 1 and 33) suggest those episodes may approach the 512-row limit with
  both hands [H]. Falsifier: budget.py on their packed references stays <= 380 rows.

## 5. Limits

- **Plain MuJoCo, not the evaluator's MuJoCo-Warp.** The contact counts can differ (plane-mesh 3 against 4 points; the
  convex pipelines differ). The c1 validity check of F-I5.16 (ep24 r0 against determined-wright's measured overflow) has
  not run, because the ep24 v6 bundle is not on this machine.
- **The scene is reduced:** no hands, no ground, zero action, 0.3 kg placeholder masses. Objects that the reference
  holds in the air fall in this scene, so in-hand frames count settling contacts, not grasp contacts.
- **Overlap only, not carvability.** The faithful precheck's (c) is reported as overlap volume. F-I5.15's carvability
  sub-check (boolean, topology, wall rays) was not run.
- **Distances are approximate.** They are capped at 100 mm and come from 2 mm surface samples or cube distances, so
  they are good to about 1 mm. Packed depths are lower bounds.
- **Timing.** A first, slower run of evals 10 and 14 (unbounded nearest-neighbour queries; `<scratch>/evck/out/geo`)
  gives the same pair values as the reported run once those values are capped at 100 mm (0 differences in 161 + 158
  frames). Its partial evals 1 and 15 were stopped and rerun; they are not results.
- **Scope.** Eval 25, the boards, is not in this list; determined-wright measured its full scene. Other packed eval
  episodes with two objects (3, 5, 6, 8, 19, 20, 28, 35-38 in `packed_refs.json`) were not in the task.

## 6. Not run here, and hand-offs

- **F-I5.16 (3)(b), budget.py on the packed references** (full scene with both hands; the <= 380 bound). It cannot run
  here: there is no FlashCHORD tree, warp, newton or mujoco_warp in this container. Hand-off to determined-wright:
  - They can run it directly on the packed references listed in `packed_refs.json`; the assets are the pack's own
    (`/content/assets` with `--pieces meshes/carve/ev10` for eval 10 and `ev01` for eval 1).
  - Eval 10 first, since its pair scene alone overflows.
- **For the orchestrator to relay** (F-I5.16 (3) says "sent to focused-pascal and determined-wright"; this step did not
  message any session):
  - Eval 10's packed `ev10` pieces overflow under sim=rl.
  - Evals 14 and 30: the rack's CoACD pieces block the slot beyond the mesh.
  - Eval 32: the cup is 19.5 mm in the table at hands-off frames.
  - Evals 15 and 16: the spoon floats 44-61 mm at hands-off frames.

## 7. Reproduce

Python 3.13 venv (trimesh 4.x, numpy, scipy, pyarrow, mujoco 3.17.0, huggingface_hub); coacd 1.0.11 in a separate pip
target (`<scratch>/coacd1011`). Run from `<scratch>/evck`; S = this folder's `scripts/`.

```
python -I S/dl.py packed_refs.json dl 10,1,14,15,16,30,32,33                 # HF store: refs, stages, sf assets
python -I S/packed_coacd.py <scratch>/coacd1011 out/packed spoon_lib=meshes/library_v3/wooden_spoon.glb \
    spoon_ep32sf=<ep32 sf wooden_spoon.glb> sweeper_lib=meshes/library_v3/mini_sweeper.glb \
    cup_lib=meshes/library_v3/blue_cup.glb cup_ep32sf=<ep32 sf blue_cup.glb> rack_lib=meshes/library_v3/plastic_dish_rack.glb
python -I S/make_config.py packed_refs.json dl out/packed <ev01 checkout> out/cfg.json 10,1,14,15,16,30,32,33
python -I S/evalcheck.py out/cfg.json out/geo2 <eps>                          # per-frame records (84-1,622 s per episode under load)
python -I S/contacts.py out/cfg.json out/geo2 out/contacts2 <ep>              # contact numbers (2-6 s per frame, 16 copies)
python -I S/summarize.py out/cfg.json out/geo2 out/contacts2 evalcheck_summary.json
python -I S/tables.py evalcheck_summary.json
```

Code: the scripts in `scripts/` at the commit that adds this README. `packed_refs.json` is at focused-pascal c6fe323.
Outputs here:
- `evalcheck_summary.json`: per episode, the H0 / H30 / all / per-object precheck, the cavity measures and the
  contacts;
- `eval_contact_precheck.json`: per copy, overflows first;
- `per_frame/ep*_frames.json`: every frame's measures and flags;
- `inputs/`: config, download md5s, CoACD report;
- `logs/`.
