# Eval-19 sweeper, support_fill step: result (1 Nov 2026)

**Verdict: the binding gates E1 and E2 pass, so the candidate is delivered.**
- support_fill certified the sweeper's start pose with a 0.5 cm underside fill (slab 4.2 cm3).
- In the hands-free settle the sweeper now stands. At f0 it moves 0.01 mm / 0.01 deg, against 90.2 mm / 88.8 deg
  falling over packed. At f2 it moves 1.70 mm / 1.53 deg, against 92.4 mm / 90.1 deg packed.
- All 16 jittered copies stay under 5 deg at both frames: max 0.86 and 2.03 deg. With packed, 16 of 16 fall at both.
- Visual mesh unchanged. Collision pieces 23 (packed 19). Plain-MuJoCo rows are lower than packed (max 160 vs 196).
- `budget.py` (determined-wright) is the binding contact check, and a retrain needs the owner's go.

Rules: `GATES.md`, pushed in a0ffceb before the tool ran. CPU, this container, no rental, $0. GT-free.
Labels: [M] measured here, [R] read from another lane.

## Build (one run, as pre-registered)

- **Code.** focused-pascal's `pipeline/support_fill.py` at 22fb399 (md5 9599101b) with `hold_phases.py` (md5 1e1b93c5).
  Default settings: `--fill 0` (auto) and SF_ARC = 1. Dependencies: manifold3d 3.5.4, fast_simplification 0.2.0,
  trimesh 5.2.0.
- **Command** (06:59:01-06:59:03 UTC, rc 0, stderr empty):
  ```
  python -I support_fill.py <runs/20261025-std1928-ee7ba8e/refs/perc2mcks/ep19/.../afc53914...-0.parquet, md5 201f338a>
    <refs/perc2mck/ep19/reconstructed_stage/t3_ep019_support.usda, md5 8b41baf8> <scratch>/ev19/sf_assets
    <scratch>/ev19/ref_sf.parquet --asset_map /content/assets=<scratch>/f0work/shared/ep19
  ```
  `<scratch>/f0work/shared/ep19` = make_assets.py (focused-pascal) on `meshes/library_v3` with no pieces: sweeper glb
  c32f43de, URDF 68762128; dust pan glb 9ac90016, URDF ad816644.
- **Tool output** (`results/ref_sf_support_fill.json`, `results/support_fill.stdout`). It ran without error on the
  std-mode reference.
  - **Sweeper.** Rest frames 0, 1, 11; they are near-identical poses and were processed once, at f0.
    - As is: lowest point 0.2 mm above the table, inside but margin 1.4 mm and tip 1.3 deg, so not certified.
    - **CERTIFIED BY FILL**: fill 0.5 cm, patch 10.7 x 1.3 cm, margin 5.5 mm, tip 5.0 deg, **slab 4.2 cm3**, manifold
      union.
    - Mesh volume 115.8 -> 117.9 cm3. No arc foot.
    - Only the f0 rest pose got a slab, and the tool listed no other rest pose for the sweeper. It is held from about
      f10 on.
  - **Dust pan.** STABLE AS IS at frames 0 and 196 (rest frames 0, 196, 206, 216, 234); not filled. Its file is
    unchanged (9ac90016). Not used.
- **Packaging** (GATES; the only deviation from the tool's own output, and no geometry changes). The tool wrote the
  filled mesh over `mesh/mini_sweeper/mini_sweeper.glb`. Here it is `mini_sweeper_sf.glb` (f27eb335) and is named only
  by `<collision>`. `<visual>` keeps c32f43de; mass, COM and inertia are unchanged.
- **Scratch only** (sha256):
  - the tool's `ref_sf.parquet` 1760d7a8...;
  - its overwritten glb b2bf0f9d... (byte source of f27eb335).

## Gates [M] (`results/ev19_settle.json`)

The scene is that of `../scripts/ev10x_settle.py` (the f0-survey method): plain MuJoCo with the sim=rl options, both
objects free, no hands, table plane at 0.600 m, 2.0 s. Each frame gets the exact pose plus 16 copies with both objects
jittered 0.5 mm / 0.005 rad (seed 2). The sweeper's only H30 rest run is f2-f8; the hands are 159-170 mm away at f0 and
f2.

| Gate | Packed | Candidate | Verdict |
|---|---|---|---|
| E1 at f0: rotation < 5 deg in >= 15 of 16 copies | exact 90.21 mm / 88.79 deg; copies 88.8 deg median, 89.4 max; **0/16 below 5 deg** (16 fall) | exact **0.01 mm / 0.01 deg**; copies 0.50 deg median, **0.86 max**; **16/16**; translation max 1.26 mm | **pass** |
| E1 at f2 (first H30 rest) | exact 92.35 / 90.13; copies 90.2 / 90.8; 0/16 (16 fall) | exact **1.70 / 1.53**; copies 1.72 / **2.03 max**; **16/16**; translation max 2.27 mm | **pass** |
| E2 visual md5 | `<visual>` c32f43de, library c126a8ff | `<visual>` c32f43de, library c126a8ff unchanged; submitted mesh untouched | **pass** |
| E3 collision pieces | 19 (CoACD of c32f43de), 150.4 cm3 | **23** (FlashCHORD CoACD 1.0.11 of f27eb335), 133.7 cm3 | stated |
| E4 contacts (indicative) | max nefc 196 (exact and copies) | max nefc 80 / 160 at f0, 72 / 144 at f2 | lower; no overflow (<= 512 rows) |

- **Contacts (ncon).** Not recorded by this script. nefc <= 196 means <= 49 contacts under the condim-3 pyramidal cone
  (4 rows each), far below 256.
- **Dust pan.** It is unchanged in both: 0.84-0.90 mm / 2.2-2.3 deg. Its hand is 9-10 mm away at f0 / f2, but it rests
  on the table.
- **Overlap.** The candidate sweeper's pieces do not overlap the packed dust pan at f0 or f2 (0 cm3, as packed).
- **Table penetration of the lowest piece.** f0: 0.00 mm (packed 0.58). f2: 0.87 mm (packed 0.61).
- **Report only, at the dust pan's first H30 rest frame (f201).** The sweeper is held there (hand 3.6 mm), so it drops
  65-66 mm in both variants. Expected.

## Deliverable and how to use it

- **Files** (`sets/`, an overlay on the eval-19 asset tree):
  - `sets/urdf/mini_sweeper_rigid.urdf` (90df047a);
  - `sets/mesh/mini_sweeper/mini_sweeper_sf.glb` (f27eb335, 81 KB).
  - Put them over the make_assets.py output of `meshes/library_v3` (std mode, `/content/assets`). Everything else stays
    as packed.
- **Shared-asset caution.** Eval 30 also uses `mini_sweeper` from the shared `/content/assets`. The fill is certified
  for eval 19's start pose only, and on eval 30 the sweeper sits in the rack. Train eval 19 on its own asset copy (the
  reference's `object_urdf_paths` pointing there), not in a box shared with eval 30.
- **determined-wright:** `budget.py` at 32x60 on eval 19 with this overlay against packed. It is the binding contact
  check; plain MuJoCo shows fewer rows.
- **focused-pascal:** the std-mode recipe of the packed eval-19 run (20261025-std1928-ee7ba8e, 250M) on the same
  reference, with the overlay. This needs the owner's go for a rental.
  - [H] The sweeper no longer falls at the start.
  - Falsifier: a zero-action FlashCHORD replay that still has the sweeper off by more than 5 mm / 2 deg before a hand
    comes.
  - focused-pascal's ep18 note applies: a hand can still knock it later, and std mode has no approach control.

## Caveats

- Plain MuJoCo, not MuJoCo-Warp. No hands. A plane instead of the usda cylinder.
- The certificate and the settle both concern the f0 / f2 pose only. The tool found no other sweeper rest pose to
  protect.
