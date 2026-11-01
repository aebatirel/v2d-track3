# ev20b1: provenance (import header; details below it)

- Byte copy of `docs/research/mesh-2026-10-26/rebase/sets/ev20/` at commit `83d18d09d358aa4cf6121d9c546125b885434f2c` (git tree `5bcb77bd7833b19ff859b0f5f26f03d64a90fba5`), imported 2026-11-01 06:55 UTC by `tools/e20b1.py import`.
- 41 input files; `MD5SUMS` lists them (md5 of MD5SUMS `fe9aeca079fdcc7524a06f46fcd0a7ae`); `FROZEN.md` is the source's own freeze, byte copy, and lists the same md5s (checked at import).
- The 41 input files are byte-identical at commit `9c0bc0c9a1c9092cd363ab1d257768b5baebb0a8`: True.
- Check: `python3 tools/e20b1.py pieces --dir meshes/carve/ev20b1 --out /tmp/p.json`.

## Source and freeze
- Mesh lane: bold-albattani, `origin/claude/bold-albattani-6qmxsv`, `docs/research/mesh-2026-10-26/rebase/` (README.md, GATES.md
  with amendment A1 at ea025f3, NOTES.md). Result commit `9c0bc0c` ("Eval-20 pitcher b1 foot-plane clip (amendment A1) passes
  G1/G2/G3/G5/G6, G4 flagged; delivered sets/ev20"); freeze commit `83d18d0` (FROZEN.md, "frozen 2026-11-01 ~06:40 UTC at
  keen-heisenberg's request ... Apply with placement_carve.py assets on refs/sf/ep20/assets with SF=0 (not make_assets
  --pieces). Do not edit; any change is a new folder.").
- MD5SUMS md5 `fe9aeca079fdcc7524a06f46fcd0a7ae` equals the lane's "the folder hashes to fe9aeca0 (md5 of the sorted per-file
  md5 list)".

## What the pieces are
- `water_pitcher/piece_00..32.obj`: the 33 CoACD hulls (coacd 1.0.11, FlashCHORD's settings) of the pitcher glb adb315f3 (the
  make_assets copy of library_v3 `water_pitcher.glb` in the packed `refs/sf/ep20/assets`), one of them cut by the b1 plane.
- `water_pitcher/piece_33..40.obj`: the 8 arc-foot sectors support_fill added at f152 (geometry unchanged).
- Rule b1 (GATES.md A1): every piece clipped to the half-space u.x >= m_foot, u = the T-rest axis [0.043013, 0.620115,
  0.783331] measured on the packed reference P (md5 4d06d8d4), m_foot = the lowest foot-piece vertex along u. 0.03 cm3 removed.
- No inertia.json: the carve's `assets` mode keeps the packed URDF inertial (COM and inertia unchanged).

## GT-freedom (the lane's statements [R]; checked here [M])
- README: "Ground truth. None read. Inputs: our references (object poses, robot hand frames), our support usda, our meshes and
  the packed pieces. No scan, mocap, parquet object pose or `*_align`. Nothing tuned on eval scores; none exist here."
- GATES.md section 0: "Ground truth. None is read."
- The lane's motivation was posefix's public-episode mocap finding (pot / pitcher base offsets). On eval 20 it measured the
  base shift d = +0.01 mm ("not needed"); no offset from that finding enters b1.
- `tools/no_oracle.py meshes/carve/ev20b1 meshes/carve/ev20b1/water_pitcher`: accepted (no BAD name, no denylisted sha256).

## Gates and trades
- Pass: G1 (rest penetration 0.00 / 0.00 mm), G2 (vacuous), G3 (plain-MuJoCo settle at f183 / f192: 1.59 mm / 0.38 deg,
  1.62 / 0.55; packed 3.21 / 6.39, 3.32 / 7.54 fail), G5 (visual / inertial unchanged; route-A URDF 77b395a5), G6 (41 pieces),
  convexity (coacd returns one part per piece).
- Flagged: G4 (plain MuJoCo contact rows +46-64 % per frame, max 316, no overflow). FlashCHORD 32 x 60 budget (determined-wright
  f59c897): 0 / 0 overflow lines, sampled max 342 (packed 348), explicit 321 (packed 317).
- A1 is post hoc (after the packed settle failed, before b1 existed).
- FlashCHORD settle (determined-wright 85e8ef8): at the hands-off frame f192 the pitcher falls over in both sets, b1 more
  (12.0 cm / 50 deg vs packed 6.8 cm / 28 deg); the blue cup is better under b1 at f152 / f183 / f192.

## How it is applied (ops/jobs/ev20_b1.sh)
- `pipeline/placement_carve.py assets refs/sf/ep20/assets meshes/carve/ev20b1 OUT`, OUT replaces refs/sf/ep20/assets; SF=0.
- [M, CPU on the real packed files] only `urdf/water_pitcher_rigid.urdf` changes (6772f954, 9 collisions -> 77b395a5, 41
  collisions); 41 col_NN.obj byte copies added; blue cup URDF 31cd001d / glb d2be7e3d (0.5 cm fill) unchanged.
