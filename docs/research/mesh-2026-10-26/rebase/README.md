# Collision-only re-base of the pot and the pitcher: result (1 Nov 2026)

**Verdict.**
- **No re-base is needed for any pot set.** On public ep2 (mass0) and on evals 1, 3, 5, 6 and 8, the pot the simulator
  loads already rests on our table at every hands-off rest frame. The median signed penetration is -0.14 to +0.05 mm;
  the worst frame is 1.26 mm into the table.
- **Eval 28 has no qualifying frame.** The pot touches the rack at every hands-off table frame.
- **No pot candidate was built**, as the pre-registered rule requires. So there is no ep2 re-base set to A/B.
- **One set is delivered, for the eval-20 pitcher** (`sets/ev20/water_pitcher`, 41 pieces). Its base is not in the
  table either. But the packed pitcher tips 6.4-7.5 deg in a hands-free settle: a CoACD corner sits 1.36 mm below
  its support foot. Amendment A1 (a foot-plane clip, written before building) passes every binding CPU gate.

Labels: [M] measured here, [R] read from another lane's files, [E] estimate, [H] hypothesis. Rules and gates:
`GATES.md`, pushed in 0b8291f before any candidate was measured; amendment A1 in ea025f3, before b1 was built.
Log: `NOTES.md`. CPU only, this container, no rental, **$0**.

## 1. In plain words

- **Why the pot base is not in the table.**
  - The simulator does not run the shipped C0 pot. Every packed eval asset and the mass0 ep2 asset use
    `library_v3/white_pot.glb` (b97d460a; make_assets copy b5541587).
  - In the shared library frame, the C0 pot's base sits 7.55 mm deeper than the v3 pot's base (-51.68 vs -44.13 mm
    along the rest-up axis) [M].
  - Placed at the same reference frames, the C0 mesh would be 7.3-7.6 mm into the table [M]. That is the posefix
    number. The E0b pot (pack-10 candidate) would be 20.7-20.9 mm into it: its marker balls hang below the base, owner
    decision B1.
  - The references are also built so that resting objects sit on the table: `contact_retarget.py rest_settle`
    (variant mck) shifts each resting object until its lowest collision point touches the table top.
  - Before that shift, our eval tracks put the v3 pot 1.3-4.1 mm above the table, not in it [R: the
    `contact_retarget.json` rest_settle stats].
- **What is wrong on ep2 is the lid, not the base** [M].
  - The packed CoACD hulls of the pot fill its mouth. At the 45 frames where the lid rests on the pot, the packed lid
    lies 53.0 cm3 (median; 56.2 max) inside the packed pot, at least 10 mm deep.
  - Hands-free settle in plain MuJoCo:
    - the pot alone stays within 0.3-0.5 mm / 0.2 deg;
    - with the lid present, the lid is thrown 188-448 mm and the pot is knocked 42-50 mm / 32-45 deg.
  - The pack's own FlashCHORD zero-action rest check of this reference [R] agrees: pot 202.9 mm / 39.1 deg, lid
    33.6 mm / 14.0 deg, both before a hand comes for them.
  - This is the eval-1 problem before the `ev01` carve (50 cm3 there).
- **For keen-heisenberg's hypothesis.** "A re-based pot cuts ep2's early lid failures" cannot be tested by a
  re-base: on this reference the re-base changes nothing, so the two arms would be identical.
  - The revised hypothesis [H] is the lid-in-pot hull fill.
  - Its matching piece set is a placement carve. focused-pascal's `P2mck` carve (`docs/research/work/carve-20261030/
    BUILD.md`, 30 Oct) has overlap 53.83 -> 0 cm3 and settle at f0 5.99 cm / 25.5 deg -> 0.94 cm / 2.0 deg [R].
  - It was built for ep2's perc2mck reference. That reference's object poses are identical to the mass0 reference's
    (ec1a2e78 vs e22747bf, largest difference 0) [M].
  - Falsifier, unchanged: an ep2 A/B (default vs carve) that still has >= 8 early lid onsets per 20 draws.
- **Eval-20 pitcher** [M].
  - At its rest frames f181-197, the lowest collision point is a corner of one CoACD hull. Four vertices lie within
    1 mm of it, the centre of mass sits 39 mm outside them, and the corner is 1.36 mm below the 8-sector arc foot
    that support_fill added.
  - In a hands-free settle the pitcher rocks off that corner onto the foot (6.4-7.5 deg). Without the foot it falls
    over.
  - b1 cuts that one hull at the foot's base level (0.03 cm3 removed). The pitcher then stands within 1.6 mm /
    0.6 deg.
  - At the start frame f0 (report only), the packed pitcher falls over in plain MuJoCo (195 mm / 94.6 deg); b1 moves
    8.5 mm / 3.2 deg. The pack's FlashCHORD rest check [R] has the packed pitcher 10.4 mm / 3.9 deg off by f8,
    before the hand arrives at f14 (it fails the check's 5 mm / 2 deg).

## 2. Numbers [M] (`results/tables.md`, `results/summary.json`)

**Penetration of the packed collision geometry into the support at T-rest frames** (H30, on the table, not held by a
receiver, static runs >= 5). Support = the reference's own `t3_epNNN_support.usda`, top z = 0.600 m in every set.

| Set | Object | Reference md5 | Packed pieces | T-rest frames [runs] | Signed median / min / max, mm | G1 (pen. median / max) | d, mm | Outcome | Report only: hands allowed | Report only: receiver contact allowed | Partner rest: frames, overlap median / max cm3, depth mm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ep2 mass0 | pot | e22747bf | 31 | 17 [2-6, 15-26] | -0.05 / -1.02 / 0.86 | 0.00 / 0.86 pass | -0.05 | not needed | 94 fr: 0.00 / 1.21 | 17: -0.05 / 0.86 | lid: 45, **53.0 / 56.2**, 10.1 |
| eval 1 | pot (ev01) | 7f230466 | 53 | 29 [0-12, 16-21, 309-318] | -0.06 / -0.85 / 0.90 | 0.00 / 0.90 pass | -0.06 | not needed | 75: -0.02 / 1.01 | 29: -0.06 / 0.90 | lid: 24, 0.0 / 0.0, 0 |
| eval 3 | pot | 732e44ea | 31 | 20 [12-16, 21-28, 30-36] | -0.05 / -1.20 / 1.26 | 0.00 / 1.26 pass | -0.05 | not needed | 33: -0.03 / 1.26 | 20: -0.05 / 1.26 | spoon: 0 |
| eval 5 | pot | aa2f4fc5 | 31 | 10 [274-278, 280-284] | 0.00 / -1.49 / 0.97 | 0.03 / 0.97 pass | 0.00 | not needed | 30: 0.06 / 0.97 | 10: 0.00 / 0.97 | spoon: 0 |
| eval 6 | pot | 50445bc3 | 31 | 10 [223-227, 229-233] | -0.14 / -1.00 / 0.74 | 0.00 / 0.74 pass | -0.14 | not needed | 34: -0.02 / 1.05 | 10: -0.14 / 0.74 | spoon: 0 |
| eval 8 | pot | 9424b5a1 | 31 | 10 [0-9] | 0.05 / -0.31 / 0.48 | 0.05 / 0.48 pass | 0.05 | not needed | 42: 0.03 / 0.81 | 10: 0.06 / 0.48 | beige cup: 0 |
| eval 28 | pot | 6f57deb2 | 31 | 0 | - | - | - | nothing measured | 0 | 5: -0.51 / 0.45 | - |
| eval 20 | pitcher | 4d06d8d4 | 41 (33 + 8 foot) | 16 [181-186, 188-197] | 0.01 / -0.60 / 0.53 | 0.01 / 0.53 pass | 0.01 | not needed; A1 | 16: 0.01 / 0.53 | 16: 0.01 / 0.53 | blue cup: 0 |

- **Rest-up axis.** Frames deviate from u by at most 0.54 deg in every set.
- **Pooled pot d.** The median of the six pot d values is -0.05 mm.
- **C0 / E0b at the same T-rest frames** (report only, `results/cond_meshes.json`): C0 median 7.33-7.58 mm, max
  7.9-8.7 mm; E0b median 20.7-20.9 mm.

**Hands-free settle, plain MuJoCo** (G3 at the gated frames; target displacement at 2 s; G4 = 16 jittered copies).

| Set | Pieces | Frame | Target mm / deg | Partner mm / deg | G4 max nefc / overflow copies |
|---|---|---|---|---|---|
| ep2 mass0 | packed | f4, f20 | **49.6 / 44.6**, **41.6 / 32.1** | lid 448 / 161, 188 / 173 | 440, 432 / 0 |
| eval 1 | packed (ev01) | f0, f6, f18, f313 | 0.25-0.53 / 0.19-0.51 | lid 4.2-6.6 / 0.8-1.7 | 256-392 / 0 |
| eval 3 | packed | f14, f24, f33 | 0.23-0.61 / 0.17-0.45 | spoon <= 1.2 / 0.4 | 236-272 / 0 |
| eval 5 | packed | f276, f282 | 0.39-0.62 / 0.24-0.34 | spoon <= 0.5 / 0.2 | 228-244 / 0 |
| eval 6 | packed | f225, f231 | 0.33-0.54 / 0.23-0.33 | spoon <= 0.4 / 0.3 | 232-236 / 0 |
| eval 8 | packed | f0, f4 | 0.25-0.58 / 0.29-0.34 | beige <= 1.9 / 1.0 | 292-296 / 0 |
| eval 28 | packed | f0 (diagnostic) | 0.86 / 0.47 | rack 1.2 / 1.2 | 208 / 0 |
| eval 20 | packed | f183, f192 | **3.21 / 6.39**, **3.32 / 7.54** | cup 0.4-0.6 / 0.2-0.3 | 188, 216 / 0 |
| eval 20 | **b1** | f183, f192 | **1.59 / 0.38**, **1.62 / 0.55** | same | 308, 316 / 0 |
| eval 20 | packed / b1 | f0 (report only) | **195.2 / 94.6** / 8.51 / 3.16 | cup 48.7 (held at f0) | 188 / 268 |
| eval 20 | packed / b1 | f152 (report only) | 3.62 / 2.59 / 0.97 / 0.38 | 0.8 | 304 / 312 |

- **Jittered copies at f183 / f192.**
  - Packed: median 3.8 / 4.1 mm and 8.9 / 5.1 deg. One f183 copy falls over (215 mm / 114 deg).
  - b1: at most 3.1 / 3.3 mm and 1.1 / 1.3 deg.

**Eval-20 b1 against every gate** (`results/ev20_a1/`).

| Gate | Packed | b1 | Verdict |
|---|---|---|---|
| G1 rest penetration, median / max | 0.01 / 0.53 mm | 0.00 / 0.00 mm | pass |
| G2 partner overlap | no partner-rest frame | same | pass (vacuous) |
| G3 settle at f183 / f192 (<= 4 mm, 5 deg) | 3.21 mm / 6.39 deg, 3.32 / 7.54 (fail) | 1.59 / 0.38, 1.62 / 0.55 | **pass** |
| G4 contacts (indicative) | max nefc 304 over all frames, 188 / 216 at f183 / f192 | 316; 308 / 316 (1.64x / 1.46x) | **flagged** (> 1.25x packed per frame); 0 overflow, far below 512 |
| G5 visual / inertial | glb adb315f3, URDF 6772f954 | glb adb315f3 unchanged; URDF 77b395a5 differs from packed in `<collision>` only (route A); make_assets route: glb, `<visual>` and `<inertial>` equal | pass |
| G6 pieces | 41 | 41 (40 untouched, 1 cut, 0 dropped) | pass |
| Convex / CoACD | - | every piece convex; coacd 1.0.11 returns one part each (volume ratio 0.9994-1.0000) | pass |

## 3. Per set: folder, reference, critical frames, what is needed

- **Public ep2, mass0** (the A/B set). **No re-base set**: not needed (d = -0.05 mm).
  - Reference: `runs/20261031-mass-2ed46ea/refs/mass0s42_glockt/ep2/.../ref_gl_ilc.parquet` e22747bf. The s43 copy is
    byte-identical.
    - Its source is `refs/glockt/ep2` ae4dbde8 (fingerprint af6b1110).
    - Its object poses equal the perc2mck reference's (ec1a2e78).
  - Assets: `refs/mass0_sf/ep2/assets`. Pot URDF d25b8a41, collision = visual glb b5541587 -> CoACD 31 hulls. Lid
    URDF 7b5dc76a, glb c9a07a18 -> 41 hulls.
  - Critical frames:
    - pot T-rest 2-6, 15-26 (a hand is within 30 mm of the pot from f36 to the end);
    - lid on the pot at rest: 0-21, 23-27, 29-33, 324-329, 336-342;
    - drawdiv's early lid onsets fall before f30, inside the first lid-rest run.
  - **focused-pascal:** a re-base A/B would compare identical arms, so there is nothing to run for it.
    - If the orchestrator wants the lid hypothesis tested, the treatment arm is a pot / lid placement carve on this
      reference (their P2mck, or ev01's tool rerun on e22747bf). The control is mass0. Same 2 seeds x 10 draws.
    - This lane can check a P2mck folder against G2 / G3 above if it is handed over (it lives in their scratch, not
      in git).
  - **determined-wright:** nothing.
- **Eval 1.** **No set**: not needed (d = -0.06 mm).
  - The packed `meshes/carve/ev01` pieces (focused-pascal 328139c; pot 53, lid 107) already rest on the table. They
    keep the lid 0.0 cm3 out of the pot at the 24 lid-rest frames.
  - Reference: perc2mck ep1 7f230466. Critical frames: T-rest 0-12, 16-21, 309-318; lid rest 0-23.
  - Keep `ev01`.
- **Evals 3, 5, 6, 8.** **No set**: not needed (d -0.05 / 0.00 / -0.14 / +0.05 mm).
  - Packed pot = CoACD of b5541587 (31 hulls); support_fill left the pot as is in all four.
  - References: glockt 732e44ea / aa2f4fc5 / 50445bc3 / 9424b5a1. T-rest runs are in the table above.
- **Eval 28.** **No set**: no frame qualifies (rule 3 excludes the pot while it touches the rack).
  - Report only, with rack contact allowed: 5 frames, signed median -0.51 mm, max 0.45 mm. So it is not in the table
    there either.
  - Reference: perc2mck ep28 6f57deb2, shared `/content/assets` (pot 31 hulls, rack 43).
- **Eval 20, pitcher.** **Delivered: `sets/ev20/water_pitcher/piece_00..40.obj`** (rule b1, amendment A1).
  - The folder hashes to fe9aeca0 (md5 of the sorted per-file md5 list).
  - Pieces 00-32 are the 33 CoACD hulls of glb adb315f3, one of them cut. Pieces 33-40 are the 8 arc-foot sectors,
    unchanged in geometry.
  - Reference: `runs/20261025-evb1420-ee7ba8e/refs/glockt/ep20/.../ref_gl_ilc.parquet` 4d06d8d4.
  - Assets: `refs/sf/ep20/assets`. Pitcher URDF 6772f954; blue cup with a 0.5 cm fill (d2be7e3d).
  - Critical frames: T-rest 181-186, 188-197 (G3 at f183 and f192); f0 start (report only); f152 foot certification
    (report only); the hand reaches the pitcher at f14 (FlashCHORD rest check).
  - **How to apply.** Run `pipeline/placement_carve.py assets <refs/sf/ep20/assets> sets/ev20 <out>`. Only the
    pitcher URDF changes (77b395a5, a copy is in `results/ev20_a1/`). The blue cup's fill, both visuals and both
    inertials are kept. Use SF=0 so support_fill does not rebuild the pitcher.
    - Do **not** use `make_assets.py --pieces` for eval 20: it would rebuild the blue cup from the library and drop
      its 0.5 cm fill.
  - **determined-wright:** `budget.py` at 32x60 on eval 20, b1 against packed. This is the binding contact check;
    plain MuJoCo flags +46-64 % rows per frame (max 316, no overflow).
  - **focused-pascal:** after budget.py passes, an eval-20 retrain with REUSE_REF on 4d06d8d4 and the b1 asset copy,
    if the owner approves the rental. The packed rest check (pitcher 10.4 mm / 3.9 deg before the hand comes) gives
    the after-number to compare.

## 4. Commands and run record

- **Machine and code.** This cloud container (4 shared cores), CPU, $0. Code: `scripts/` at this commit, built on
  GATES 0b8291f / A1 ea025f3. Python: the scratch venv (trimesh 5.2.0, MuJoCo 3.17.0, numpy, scipy). coacd 1.0.11 from
  a separate pip target (`<scratch>/coacd1011`), as FlashCHORD pins.
- **Inputs.**
  - `dl.py` of `gmg/build/I/results/collcarve2-evalcheck/scripts` was run on focused-pascal's `packed_refs.json`
    (a7ed39d6) for evals 1, 3, 5, 6, 8, 20 and 28. Every reference md5 matches the list. Evals 1 and 28 come from the
    byte source `refs/perc2mck`, as in the evalcheck.
  - The mass0 ep2 files came from `runs/20261031-mass-2ed46ea` (store `aebatirel/v2d-store`).
  - make_assets copies (focused-pascal's `pipeline/make_assets.py`) of library_v3: pot b5541587, lid c9a07a18,
    pitcher adb315f3, rack 99bc3983. The packed sf glbs are identical where they exist.
- **Packed decomposition.**
  - Run: `python -I collcarve2-evalcheck/scripts/packed_coacd.py <coacd1011> <out> name=glb ...`.
  - Results: pot 31 hulls / 890.63 cm3 (equal to ev01 `carve.json` `hulls_default` 31 / 890.6, FlashCHORD's own
    function), lid 41 / 325.71, pitcher 33 / 1554.84, rack 43, spoon 10 / 9, beige and blue cup
    (`results/packed_coacd*_report.json`).
- **Per set** (configs in `results/cfg/`; paths point to the scratch downloads):
  - `python -I scripts/rebase.py cfg/<set>.json out/<set>` (frames, packed penetration, rules, G1 / G2 / G6;
    86-309 s per set);
  - `python -I scripts/settle.py cfg/<set>.json out/<set> packed`; for eval 20 also `cfg/ev20_a1.json
    out/ev20_a1 b1 packed --extra 0,152`;
  - `python -I scripts/checks.py sets/ev20 refs/sf/ep20/assets meshes/library_v3 <fp pipeline> <coacd1011>
    checks.json` (G5, route A and route B, convexity, coacd);
  - `python -I scripts/cond_meshes.py <root> <sets>` (C0 / E0b, report only);
  - `python -I scripts/collect.py results <sets> > results/tables.md`.
- **Outputs.**
  - Per set, in `results/<set>/`: `rebase.json`, `frames.json` (per-frame penetration, hands, partner distances),
    `settle_*.json`.
  - For eval 20 also: `checks.json` and `water_pitcher_rigid.route_A.urdf`.
  - The pack's rest checks [R]: `results/rest_check_R/`.
- **Ground truth.** None read. Inputs: our references (object poses, robot hand frames), our support usda, our meshes
  and the packed pieces. No scan, mocap, parquet object pose or `*_align`. Nothing tuned on eval scores; none exist
  here.

## 5. Caveats

- **Engine.** Plain MuJoCo, not the evaluator's MuJoCo-Warp. Hands are absent, and the table is a plane at the usda
  top, not the 0.24-0.29 m cylinder. Default solref / solimp, 0.3 kg placeholders as in the packed URDFs. G3 / G4 are
  CPU stand-ins; budget.py and a GPU run decide.
- **Small T-rest sets** (10-29 frames). The grasp-lock references keep a hand within 30 mm of the pot for most of each
  episode. Both report-only sets (hands allowed: 16-94 frames; receiver contact allowed) agree with the gated ones to
  within 0.15 mm in the median.
- **A1 is post hoc.** It was written after the packed eval-20 settle failed, but before b1 existed. It applies to this
  one set and is labelled as an amendment. The contact flag (G4) is open until budget.py.
- **The eval-20 start (f0) is report only.** f0 is hands-off (31 mm), but its static run is too short for T-rest, so
  b1's 8.5 mm / 3.2 deg there is not a gate result.
- **C0 / E0b numbers are conditional.** They hold only if a future pack moves the simulator copy to those meshes on
  these references. In that case, rule (a) / (b) with d ~ 7.5 mm would apply to C0. E0b's 21 mm is beyond the 12 mm
  bound.
