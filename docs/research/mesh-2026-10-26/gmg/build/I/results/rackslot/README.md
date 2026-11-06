# Rack slot pieces for evals 30 and 14: measured candidates, none passes its gates

1 Nov 2026, 02:53-04:25 UTC. CPU on this container, no rental, $0. Owner go 02:50 UTC (relayed). The gates were
written before any candidate was measured (`GATES.md`, with amendments 1 and 2).
Tags: [M] measured here, [R] read from another lane, [E] estimate, [H] hypothesis.
Nothing here reads ground truth or eval scores. The inputs are the packed references (our own perception), the packed
meshes and FlashCHORD's packed hulls.

## In plain words

**The aim.** The packed simulator gives the dish rack 43 convex pieces, made by CoACD at load. In both episodes they
fill part of the slot where the packed reference rests the guest (the mini sweeper in eval 30, the blue cup in eval
14), beyond what the rack's own mesh fills. We built rack piece sets that keep every bit of the rack mesh but empty
that slot.

**The root cause is the pose, so no rack piece set can fix it.** At every hands-off rest frame the guest's own mesh
already sits inside the rack's mesh [M]:
- eval 30: 22 of 22 rest frames, 6.2 cm3 median, up to 8.4 cm3;
- eval 14: 18 of 18 rest frames, 9.2 cm3 median, up to 10.8 cm3.

That overlap is in the reference pose. Emptying the slot cannot remove it, so the simulator still pushes the guest
out. The fix belongs to the pose lanes.

**What the candidates do** [M]. They remove almost all of the fill beyond the mesh:
- What remains sits in a band within 0.87 mm of the mesh surface. Beyond that band, 0.3-0.8 cm3 is left, from
  4.3-7.6 cm3.
- The collider overlap at the rest frames falls from 14.2 to 9.8 cm3 median on eval 30, and from 15.7 to 12.8 cm3 on
  eval 14. That is close to the floor the guest's pieces have inside the rack mesh (8.1 and 11.7 cm3).

**What it costs, and what it buys**, measured in the hands-free pair scene where both objects are free [M]:

| Eval | Candidate | Contact rows per world (plain MuJoCo, indicative; limit 512) | How far the guest is thrown |
|---|---|---|---|
| 14 | c1-ev14 | 552-612 (packed 300-336); 10-16 of 16 copies over 512 | about 42 % less (median 79 mm against 136 mm) |
| 14 | c2-ev14 (merged down to 54 pieces) | still over at 2 of 3 frames | median 77 mm, but 202 mm at f149 |
| 30 | c1-ev30 | 544 at f257 (1 of 16 copies over); 324 and 344 at f249 and f1 | farther: 41 mm median against 25 mm |
| 30 | c2-ev30 | 308-392: under the limit | farther: 43 mm median against 25 mm |

- The new pieces near the guest multiply the contacts: guest-to-rack contacts rise from 4-21 to 34-60 at the busiest
  step.
- With the rack held fixed (the S settle test), every candidate throws the guest 2-9 times less far than the packed
  rack does. It is still thrown, by 23-214 mm, so the settle gate fails everywhere, the packed rack included.

**Gate verdicts.** None of the five candidates passes its gates (table below):
- G2b (the slot is empty beyond the band) and G5 (kept volume) pass for all.
- G1 fails on the pose floor for all.
- G1x fails on its median for all: 1.1-2.0 cm3 against 1.0. The excess left is the sub-millimetre band along the
  mesh.
- G4 fails for all, as it does for the packed rack.
- C1 fails for all: the sets have 54-86 pieces against 43. Each touched CoACD hull holds 91-100 % of its share of
  the slot inside the hull of its own mesh part [M], so it has to be split. No merge can bring the count back without
  re-filling the slot.
- G3 fails for every set except c2-ev30.

**Recommendation.**
- **Eval 30: do not use any of these sets.** They throw the free sweeper farther than the packed rack does.
- **Eval 14: c1-ev14 is the only set with a possible value.** It cuts the throw by about 42 %, but it may overflow the
  512-row budget. Use it only if determined-wright's `budget.py`, the binding contact check, keeps it within budget,
  and only if the owner accepts the gates it fails: G1 (floor), G1x median, G4 (floor), C1 (62 pieces) and C3 as
  written (numerical slivers, below).
- **c1-both: do not use.** It serves both episodes with the same per-episode geometry, but it has 86 pieces and
  overflows on eval 14 at 616-688 rows (14-16 of 16 copies).

## Numbers: candidates against the packed rack (all [M])

- **Frames.** R is the hands-off rest frames:
  - H30 (no robot hand point within 30 mm of either object), guest in the slot region, no table or float flag;
  - eval 30: f0-2, f4, f244-245, f247-262 (22 frames); eval 14: f140-157 (18).
- **G1 / G1x / G2** are over R. Volumes are in cm3, as median / max over R.
- **Floors.** V_vv is the guest mesh inside the rack mesh (the pose floor). V_pm is the guest's packed pieces inside
  the rack mesh (the floor for any rack set).
- **G3 / G4 / G6** are at the gate frames, the median over 16 jittered copies:
  - eval 30: f257, f249, f1;
  - eval 14: f149, f144, f153.
- **G6, pair scene:** both objects free, sim=rl options, 2 s, plain MuJoCo. **G4 and S:** rack fixed, 2 s at 2 ms.

### Eval 30 (rack <- mini sweeper)

| | packed | c1-ev30 | c2-ev30 |
|---|---|---|---|
| Pieces (C1: <= 43) | 43 | 67 (FAIL) | 57 (FAIL) |
| G1 V_pp median / max (<= 1.0 / 3.0) | 14.2 / 18.7 | 9.8 / 12.3, FAIL (pose floor) | 10.1 / 12.7, FAIL (pose floor) |
| Floors V_vv; V_pm | 6.2 / 8.4; 8.1 / 10.4 | same | same |
| G1x = V_pp - V_pm, median / max (<= 1.0 / 3.0) | 6.15 / 8.29 | 1.69 / 2.03, FAIL (median) | 1.97 / 2.32, FAIL (median) |
| G2 swept beyond mesh, as written (<= 1.0) | 10.76 | 2.90, FAIL | 3.49, FAIL |
| **G2b** beyond the 0.87 mm band (<= 1.0, judged) | 7.62 | **0.37, pass** | **0.80, pass** |
| Per-frame max beyond mesh (guest pieces / guest mesh) | 8.29 / 6.78 | 2.03 / 1.57 | 2.32 / 1.83 |
| G3 max nefc / ncon, plain MuJoCo, indicative (<= 512 / 256, no overflow) | 304 / 76, 264 / 66, 288 / 72 (pass) | 544 / 136 (1 / 16 over), 324 / 81, 344 / 86, FAIL | **392 / 98, 348 / 87, 308 / 77, pass** |
| G4 S mean displacement / tilt (<= 4 mm / 5 deg, no fall) | 133 / 156, 230 / 139, 144 / 124, FAIL | 62 / 112, 46 / 76, 27 / 46, FAIL | 56 / 62, 42 / 37, 28 / 39, FAIL |
| G5 kept volume (>= 0.90) | 1.000 | 0.999, pass | 0.999, pass |
| G6 pair-scene guest throw, mm (median per frame; report) | 38, 23, 25 (25) | 49, 41, 40 (41): worse | 56, 41, 43 (43): worse |
| G6 S guest throw, mm (report) | 138, 217, 134 | 55, 44, 23 | 52, 43, 23 |
| C2 mesh not cut (cells lost; farthest sample) | - | 0.0 cm3; 0.09 mm, pass | 0.001 cm3; 0.08 mm, pass |
| C3 one convex hull per piece | pass | FAIL as written (4 pieces flagged by trimesh is_convex; coacd 1.0.11: 1 part each) | pass |

### Eval 14 (rack <- blue cup)

| | packed | c1-ev14 | c2-ev14 |
|---|---|---|---|
| Pieces (C1: <= 43) | 43 | 62 (FAIL) | 54 (FAIL) |
| G1 V_pp median / max | 15.7 / 17.6 | 12.8 / 14.6, FAIL (pose floor) | 13.2 / 15.0, FAIL (pose floor) |
| Floors V_vv; V_pm | 9.2 / 10.8; 11.7 / 13.4 | same | same |
| G1x median / max | 4.01 / 4.43 | 1.14 / 1.37, FAIL (median) | 1.45 / 1.73, FAIL (median) |
| G2 swept as written | 6.88 | 2.31, FAIL | 2.90, FAIL |
| **G2b** (judged) | 4.30 | **0.29, pass** | **0.69, pass** |
| Per-frame max beyond mesh (guest pieces / mesh) | 4.43 / 3.73 | 1.37 / 1.12 | 1.73 / 1.43 |
| G3 max nefc / ncon (indicative) | 300 / 75, 336 / 84, 320 / 80 (pass) | 584 / 146 (10 / 16), 612 / 153 (16 / 16), 552 / 138 (11 / 16), FAIL | 488 / 122, 580 / 145 (11 / 16), 536 / 134 (1 / 16), FAIL |
| G4 S mean displacement / tilt | 692 / 99, 799 / 130, 381 / 146, FAIL | 83 / 85, 108 / 75, 101 / 86, FAIL | 60 / 80, 144 / 92, 211 / 122, FAIL |
| G5 kept volume | 1.000 | 0.999, pass | 0.999, pass |
| **G6 pair-scene guest throw, mm** | 140, 136, 134 (136) | **79, 76, 81 (79): 42 % less** | 202, 76, 77 (77): worse at f149 |
| G6 S guest throw, mm | 689, 780, 432 | 77, 91, 87 | 51, 94, 214 |
| C2 | - | 0.0 cm3; 0.06 mm, pass | 0.0 cm3; 0.09 mm, pass |
| C3 | pass | FAIL as written (7 flagged; coacd 1 part each) | pass |

**c1-both (86 pieces), both episodes.** The two slots touch disjoint hulls:
- eval 30: hulls 24, 29, 36, 41, 42;
- eval 14: hulls 3, 13, 21, 28, 40.

So c1-both's G1, G1x, G2 and G2b equal c1-ev30's on eval 30 and c1-ev14's on eval 14. Its contacts are worse:
- eval 30: 636 / 432 / 404 rows, 1 copy over;
- eval 14: 644 / 688 / 616 rows, 15, 16 and 14 copies over.

The guest throw is the same as the per-episode sets. G5 is 0.994 / 0.991. C3 fails as written.

**About the C3 flags on the c1 sets.** These are numerical artefacts:
- Each flagged piece has vertices 4-12 um apart.
- Every vertex lies on the convex hull, and the mesh volume equals the hull volume to within 1e-6.
- coacd 1.0.11, run with FlashCHORD's settings, returns one part for every piece of every set.

The c2 sets snap hull vertices to 10 um and pass C3.

**Where the excess beyond the floor sits (G1x).** It lies in the band where 1 mm cells straddle the rack-mesh surface.
For c1-ev30, 2.90 cm3 is left in the pieces as written, but only 0.37 cm3 of it lies more than 0.87 mm from the
surface. G1x was not amended for the band, so its median fails as measured.

## Deliverables in the pack's layout (`pipeline/make_assets.py --pieces DIR`)

- `pieces/<set>/plastic_dish_rack/piece_XX.obj`: one convex piece each.
- `pieces/<set>/carve.json`: provenance, the inputs with md5, every piece's md5, the rest frames and the gate frames.
- `make_assets.py` (focused-pascal 6bbb52a) on library_v3 with `--pieces pieces/c1-ev14` gives the rack 62
  `<collision>` elements. The guest keeps its one default collision [M].
- There is no `inertia.json`, so the rack's mass, COM and inertia stay as they are now [M].

| Set | Pairs with the packed reference (md5) | Critical frames | Pieces folder |
|---|---|---|---|
| c1-ev14 (the only one with a possible value) | eval 14: `runs/20261025-evb1420-ee7ba8e/refs/glockt/ep14/processed/sequence_id=t3_ep014/robot_name=sharpa_wave/ref_gl_ilc.parquet`, md5 10d5f3ba6b7368ed30dad9d0c9c30df1. Asset root `/content/refs/sf/ep14/assets` | rest f140-157 (H30, cup in the rack); gate frames f149, f144, f153 | `pieces/c1-ev14` (62) |
| c2-ev14 | same | same | `pieces/c2-ev14` (54) |
| c1-ev30, c2-ev30 (not recommended) | eval 30: `runs/20261025-std30-ee7ba8e/refs/perc2mcks/ep30/processed/sequence_id=t3_ep030/robot_name=sharpa_wave/a2eb7d276dd84fe6bed9251b46e93770-0.parquet`, md5 dd464c96184e84400e62ffcfa17a6ac4. Shared `/content/assets` | rest f0-2, f4, f244-245, f247-262; gate frames f257, f249, f1 | `pieces/c1-ev30` (67), `pieces/c2-ev30` (57) |
| c1-both (not recommended) | both of the above | both | `pieces/c1-both` (86) |

**Eval 14's sf asset root.** `make_assets.py` with no pieces on library_v3 reproduces the sf/ep14 rack and cup URDF
inertials exactly [M], and the sf rack and cup meshes are library_v3 vertex for vertex. Either of these gives eval 14
the same assets as now plus the rack pieces:
- `make_assets.py <library_v3> OUT --pieces pieces/c1-ev14`;
- adding the 62 `<collision>` lines to the sf rack URDF.

## What the other lanes would run next

- **determined-wright, `budget.py` (binding).**
  - c1-ev14 and c2-ev14 with eval 14's packed reference (md5 10d5f3ba...), at the rest frames f140-157 and the gate
    frames.
  - If c1-ev14 stays at or below 512 rows per world with hands (packed: 385 [R], determined-wright 02:56), it is the only set worth a retrain.
  - Eval 30: nothing to run, unless the orchestrator wants c2-ev30's counts on record. It fits in plain MuJoCo, but it
    throws the sweeper farther.
- **focused-pascal, retrain under the swap rule.** Only after budget.py passes on c1-ev14 and the owner accepts its
  failed gates (G1 floor, G1x median, G4 floor, C1 62 pieces, C3 as written).
  - The assets are eval 14's with `--pieces pieces/c1-ev14`.
  - Keep `pieces: null` for eval 30.

## Flagged reference issues (for the pose lanes)

- **Evals 30 and 14: the guest sits inside the rack mesh at every hands-off rest frame.** Eval 30 22 / 22 frames
  (V_vv 6.2 median, 8.4 max); eval 14 18 / 18 (9.2 / 10.8). This is the root cause, and no collider change removes
  it.
- **Eval 14, f41-45 (16.6 mm into the table at f42), restated.** Under H30 these frames are not hands-off: a hand is
  within 30 mm, and 3 mm away at f42. It is a reference pose problem while the cup is held, not a rest problem. It
  enters no gate here. Over the H30 frames, eval 14's largest table penetration is 3.9 mm, by the rack at f157.
- **Eval 30, f123-128.** The sweeper sits inside the rack's far end wall: visual overlap 7.3-10.3 cm3, no
  hand-contact label, but a hand within 30 mm. It is a transit pose. It entered only the superseded H0 rest set.

## Method (GATES.md has the full rules)

1. **Rest volume RV.** The union over R of the guest's packed pieces, each hull plane pushed out by 1.0 mm. It is
   evaluated on the 1 mm cells of the packed rack. F = RV minus the rack mesh. F' = F beyond the 0.87 mm surface
   band, where a 1 mm cell straddles the mesh surface.
2. **Cut** (`build.py`, [H]). Every packed hull holding more than 20 F' cells is cut into convex cells:
   - clip planes keep every rack-mesh point (0.3 mm surface samples plus the 1 mm mesh cells inside the hull) and cut
     away F' cells (at most 6 planes per cell);
   - where F' lies inside the hull of the cell's own mesh points, a BSP split through F' is chosen from 126
     directions x 5 offsets to leave the fewest F' points trapped (depth <= 5);
   - every leaf is the hull intersected with half-spaces, so it is convex, lies inside the hull and keeps the mesh.
3. **Merges** (`build.py`, then `merge2.py` for c2).
   - c1: a merge must add no F' cell. No such merge existed.
   - c2: merges cheapest in added F' cells, at most 0.5 cm3 in total (half of G2b's allowance), at most 2 cm3 of new
     fill outside the packed union per merge and none where the guest goes at any frame. Hull vertices are snapped to
     10 um.
4. **Measure** (`measure.py`, `phys.py`). The packed rack and the candidates run through the same code:
   - G3 is the precheck's `contacts.py`, unchanged;
   - G4 is `gmg.simphys.sink_test`, as collcarve calls it.

**Development record.**
- Builds:
  - the H0 c1-ev30 build was stopped at 03:25, before Amendment 1;
  - try1 (depth 3, 70 pieces, 2.42 cm3 of F left) and try2 (depth 5; 107 / 102 pieces, 1.32 / 1.04 cm3 left) were
    never measured;
  - their logs are in `build/dev-*` and `c1-ev30-h0-stopped.log`.
- The packed baseline under H0 is in `meas_h0/` (superseded). It reproduced the precheck's contact rows exactly.

## Commands, code, inputs

The code is `scripts/` in this folder. It ran from `<scratch>/rackslot/scripts` with the scratch venv: Python 3, numpy,
scipy, trimesh 5.2.0, mujoco 3.17.0. coacd 1.0.11 was installed in a separate pip target (`<scratch>/coacd1011`).

```
python make_grid.py ../grid_base.npz              # rack mesh + packed union occupancy, 1 mm (md5 be3ccbf6...)
python build.py 30 ../c1-ev30; python build.py 14 ../c1-ev14; python build.py both ../c1-both     # code 8fd2c00
python merge2.py 30 ../c1-ev30 ../c2-ev30; python merge2.py 14 ../c1-ev14 ../c2-ev14
python measure.py packed ../meas/packed_geo.json 30,14
python phys.py packed ../meas/packed_phys30.json 30; python phys.py packed ../meas/packed_phys14.json 14
python measure.py ../<set> ../meas/<set>_geo.json <eps>; python phys.py ../<set> ../meas/<set>_phys<ep>.json <ep>
python package.py ../<set> <this folder>/pieces/<set> <set>
python tables.py ../meas packed,c1-ev30,c2-ev30,c1-ev14,c2-ev14,c1-both > meas/tables.md
```

**Inputs (md5).** `carve.json` in each pieces folder has the full list.

| Input | md5 | Note |
|---|---|---|
| `meshes/library_v3/plastic_dish_rack.glb` | e6835614... | eval 14's sf copy 99bc3983... is the same geometry (sha1 c9ee8c559c02) |
| packed rack hulls `rack_lib.npz` | c0742888... | coacd 1.0.11, threshold 0.05, 43 hulls; reproduces the 26 Oct census |
| `mini_sweeper.glb` | c126a8ff... | packed hulls `sweeper_lib.npz` a10021e7... (19) |
| sf ep14 `blue_cup.glb` | 0435d5d2... | packed hulls `cup_lib.npz` fb2a675f... (76) |
| precheck `per_frame/ep30_frames.json` | 3da81b24... | |
| precheck `per_frame/ep14_frames.json` | 30f3022a... | |
| pose npz (from the packed references) ep30 / ep14 | b42c291a... / fe12f95b... | |
| `packed_refs.json` (focused-pascal) | a7ed39d6... | |
| `cfg_sim_rl.yaml` | sha256 695536b7... | checked by `contacts.py` |

**Outputs.**
- `meas/*.json`: per set and episode, every gate with per-frame rows and per-copy rows.
- `meas/tables.md`: the generated tables.
- `build/<set>/build.json`, `build.log`.
- `pieces/<set>/`.

## Limits

- **G3 and G6 are plain MuJoCo**, not the evaluator's MuJoCo-Warp. They are indicative only, and plain MuJoCo
  over-counts against Warp (the round-2 c1 check). The scene has no hands and 0.3 kg placeholder masses.
- **All volumes are on 1 mm cells** (guest points at 1.5 mm), so a band of about 1 mm along every surface is
  ambiguous. G2b handles this for G2. G1x was not amended.
- **The S test holds the rack fixed.** The pair scene leaves it free, and the two measures disagree on eval 30.
- **Only three gate frames per episode were run** for G3, G4 and G6.
