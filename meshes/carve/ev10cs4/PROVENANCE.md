# ev10cs4: provenance

- Byte copy of `docs/research/mesh-2026-10-26/gmg/build/I/results/ev10-cavsafe/ev10cs4/` at commit `fa2ec4160cf76d70d0e43ad7a9eaa8c74cb46d1d` (git tree `946b25714044e65f21dc029a132fe0b47dab3e05`), imported 2026-11-01 05:18 UTC by `tools/e10cs_pieces.py import`.
- 50 input files; `MD5SUMS` lists them (md5 of MD5SUMS `c745ebc8c3e86cadc5301a7b2351c5c1`); `FROZEN.md` is the source's own freeze, byte copy, and lists the same md5s (checked at import).
- Check: `python3 tools/e10cs_pieces.py check --dir meshes/carve/ev10cs4`.

## What it is (from the mesh lane, bold-albattani; [R] read from their README / GATES, [M] measured here)
- ev10 cavity-safe v4 (`GATES.md` amendment A4, commit `fedccf6`, written before the build): blue 24 pieces = 16 wall
  (8 sectors x 2 bands) + 1 floor plate (`blue_cup/piece_16.obj`, 6 mm, 22.67 cm3) + 7 of meshes/carve/ev10's base hulls
  clipped to h >= h_base; beige 21 = 16 wall + 1 centre + 4 rim. Built at `7e4bc6a`, frozen at `fa2ec41` (FROZEN.md).
  Tool: their `scripts/lathe_cavsafe.py` = this repo's `pipeline/lathe_collision.py` (blob 680cc2f9) + opt-in flags
  (without them it rebuilds meshes/carve/ev10 at Hausdorff 0.0 mm) [R].
- Use: `python pipeline/make_assets.py meshes/library_v3 OUT --pieces meshes/carve/ev10cs4` (the lane's command).
- Pieces are in the library_v3 mesh (= URDF link) frame, as meshes/carve/ev10. Paired visual meshes:
  `meshes/library_v3/blue_cup.glb` md5 7542631493e3a0564f6d74009de67d54, `beige_cup.glb` 6226281f120192c52bffec7680fa9d8f
  (equal to this repo's files [M]).

## Ground-truth freedom
- [R] README: "CPU on this container, no rental, $0. GT-free." and "Nothing read here is a scan, mocap, a dataset `pose`
  field or an `*_align` file." Inputs: lathe profiles fitted to our library_v3 meshes (`lathe_fit2.py`), meshes/carve/ev10's
  base hulls (ours), the packed eval-10 reference P (gl10A2, md5 1a5003d9..., GT-free: built from the eval video) for the
  gate frames only. No scan-derived value is named in carve.json's commands or inputs.
- [M] `tools/no_oracle.py meshes/carve/ev10cs4 (+ blue_cup/, beige_cup/)`: accepted (no BAD name; no .obj matches a
  public-scan / scan-template sha256 of ops/provenance/denylist.json).

## Layout vs meshes/carve/ev10 [M]
- The same layout: `<obj>/piece_NN.obj`, `<obj>/inertia.json`, `<obj>/lathe_collision.json`, `carve.json`. Both sets carry
  inertia.json, and `pipeline/make_assets.py` (since d9c3f7d) takes the URDF COM and inertia from it (uniform solid of the
  pieces, scaled to the 0.3 kg placeholder) whenever the folder has pieces. So the mass properties follow the pieces in
  both the packed set and this one; they are NOT the same values (second changed variable, below).
- make_assets.py library_v3 + this folder (CPU, 1 Nov): blue_cup_rigid.urdf md5 8511f0d3fdc154c6e2dba609aa195c4c
  (24 collisions), beige_cup_rigid.urdf 1a8cb9d813c7a8085b4759347a16a8ba (21). The same command on meshes/carve/ev10
  reproduces e10v's box URDFs exactly (82ff6cb8... / b994e584..., e10v arms.json).

| cup | quantity (0.3 kg) | meshes/carve/ev10 (packed) | ev10cs4 | change |
|---|---|---|---|---|
| blue | COM, mm | (0.73, 1.55, 2.99) | (0.54, 1.15, 15.77) | +12.8 mm along the axis (toward the base) |
| blue | ixx / iyy / izz, kg m2 | 9.849e-4 / 9.838e-4 / 4.405e-4 | 9.884e-4 / 9.879e-4 / 4.579e-4 | +0.4 / +0.4 / +4.0 % |
| beige | COM, mm | (1.52, 5.53, -4.17) | (1.54, 5.51, -5.57) | -1.4 mm along the axis |
| beige | ixx / iyy / izz, kg m2 | 8.904e-4 / 8.903e-4 / 2.990e-4 | 9.044e-4 / 9.043e-4 / 2.683e-4 | +1.6 / +1.6 / -10.3 % |

## Known trades (disclosed; the mesh lane's numbers, plain MuJoCo unless noted)
1. **Gate 4a "blue kept volume" FAILS: 0.384 against the lane's bar 0.80.** It fails for every cavity-safe set and for the
   packed ev10 too (0.381): the blue visual mesh fills its own cavity, so a set that keeps the cavity empty cannot keep
   80 % of the visual volume. Accepted on the owner side (orchestrator, 1 Nov) because the risk that gate guards (the
   collision body not standing for the cup) is tested directly by determined-wright's FlashCHORD drop / nest checks
   (`6e32856`: 32 x 60 contact budget 0 / 0 overflow lines, hold max 448; `4f5ff63`: nest test, beige tracks the
   reference nest 0.14 cm median vs packed 1.02 cm, no floor crossing). The lane's A4 rules: commit `fedccf6`.
2. **Blue cavity floor** is a 6 mm plate, 3 mm above the visual cavity bottom; it adds overlap at the in-hand insertion
   frame f109: 17.1 cm3 (9.5 cm3 with a 3 mm floor).
3. **Thin release margin:** in FlashCHORD the release impact reaches 5.49 of the 6 mm plate, then settles at ~1 mm. In
   plain-MuJoCo hands-free drops of 24-32 mm the beige crossed the floor in 2-8 of 16 copies; none crossed in FlashCHORD.
4. **Settles deeper:** in plain MuJoCo the beige settles 1.3-24.4 mm deeper into the blue than the reference puts it.
   [H] A policy may read this as tracking error. ([M] here: eval 10's V4p nest seat re-run with these pieces puts the
   beige 1.07 cm median, 1.82 cm max, away from V over the 45 hands-off frames; docs/research/work/eval10-cs4-20261101/
   cpu/out/seat_compare.json.)
5. **Shape and mass:** blue outer faces up to 3.3-3.9 mm outside the lathe profile; beige pieces 8 mm (plus up to 5.4 mm)
   inside its mesh; blue COM 12.8 mm toward the base.
6. **Pose floor (unchanged by any piece set):** the reference's visual meshes overlap 80.6 cm3 median at f124-f160; a free
   rest from f124 drifts 1.6 cm (packed 1.3 cm).
7. **Design history:** v2-v4 were designed after v1's numbers; each version's gates were committed before it was measured
   (GATES.md A1-A4).
