# Eval-19 sweeper: support_fill step, rules and gates (written before the tool is run)

1 Nov 2026, ~07:10 UTC. This step was requested by the orchestrator (keen-heisenberg's decision at 06:57 UTC, under
the owner's 02:50 permission) and confirmed by focused-pascal at 06:55 UTC. It runs on the CPU in this container: no
rental, $0. GT-free.

Labels: [M] measured, [R] read from another lane, [H] hypothesis.

## Why [M] (`../f0_survey.md`)

- In the packed eval-19 simulator assets, the mini_sweeper falls over from the start frame in a hands-free plain-MuJoCo
  settle: 90.2 mm / 88.8 deg, 16 of 16 jittered copies. No hand is within 170 mm.
- It stands on its bristles. Its COM is 4.2 mm inside the band of collision points within 1 mm of its lowest point,
  63 mm above the table.
- Eval 19 is a std-mode reference, so `support_fill.py` never ran on it. That tool was written for public ep18's brush,
  which had this same failure.
- **[H]** support_fill's certified underside fill (or its arc foot) keeps the sweeper standing at f0.
- **Falsifier:** the gates below fail.
- **Prior from focused-pascal [R]:** on public ep18, with the "no fill below another resting pose" fix, the tool added no
  fill, and the brush stood (<= 0.9 deg) until a hand knocked it. So the tool may add nothing here. If it does, that is
  the outcome. No fill will be invented.

## Inputs (md5)

- **Reference.** The packed eval-19 reference: `runs/20261025-std1928-ee7ba8e/refs/perc2mcks/ep19/processed/
  sequence_id=t3_ep019/robot_name=sharpa_wave/afc53914ae7542d7b565119fc4892688-0.parquet`, md5 201f338a.
  - It is the one listed in focused-pascal's `packed_refs.json` (a7ed39d6).
  - Its stage is `refs/perc2mck/ep19/reconstructed_stage/t3_ep019_support.usda`, md5 8b41baf8. The perc2mcks copy
    keeps its stage in perc2mck.
- **Assets.** The reference names `/content/assets` (std mode, shared). They are rebuilt here with focused-pascal's
  `pipeline/make_assets.py` (6bbb52a) on `meshes/library_v3` with no pieces:
  - sweeper glb c32f43de (library c126a8ff, the same file in every library), URDF 68762128;
  - dust pan glb 9ac90016 (library c33fa411), URDF ad816644.
- **Code.** focused-pascal's `pipeline/support_fill.py` at 22fb399 (md5 9599101b; identical on this branch), with
  `pipeline/hold_phases.py` (md5 1e1b93c5). SF_ARC unset, so the default 1 applies.
- **Dependencies.** manifold3d 3.5.4, fast_simplification 0.2.0, trimesh 5.2.0, in this lane's venv.

## Build (exactly one run)

```
python -I support_fill.py <REF> <USDA> <scratch>/ev19/sf_assets <scratch>/ev19/ref_sf.parquet --asset_map /content/assets=<scratch>/shared/ep19
```

- Default `--fill 0`, so the smallest certifying fill of 0.5 / 1 / 1.5 / 2 cm is used. The settings are the same as the
  grasp-lock references (glock_public.sh SF=1).
- The tool processes every object in the reference. **Only the sweeper's output is used**; the dust pan stays as packed.
  Its result is reported, not used.
- **Candidate assets** = the packed assets with the sweeper's collision replaced by the tool's output for it:
  - the filled glb, if any, as a `<collision>` only;
  - its arc-foot sectors, if any, as extra `<collision>` elements.
- **Packaging.** support_fill writes the filled mesh over the URDF's shared visual / collision file. Here the sweeper
  URDF's `<visual>` keeps the packed glb (c32f43de), so the simulator's visual is unchanged too. The filled glb goes in
  as `mesh/mini_sweeper/mini_sweeper_sf.glb`, referenced only by `<collision>`. This packaging is the only deviation
  from the tool's own output. It changes no collision geometry.
- **Outcomes, fixed now:**
  - (i) The tool adds neither a fill nor an arc foot to the sweeper: "no fill". Nothing is delivered, and the gates are
    **moot** (no candidate). The packed sweeper's f0 fall stands, and the tool's per-pose statuses are reported.
  - (ii) It adds something: the gates below decide.

## Gates (candidate vs packed, same scene)

- **Scene.** As in `../scripts/settle.py` / `f0_survey.py`:
  - plain MuJoCo 3.17.0 with the sim=rl options (cfg sha256 checked), condim 3, friction 1;
  - URDF mass / COM / inertia; the sweeper's inertial is unchanged, because support_fill keeps it;
  - both objects free; table plane at the usda top; no hands; 2.0 s;
  - the exact pose plus 16 copies with both objects jittered 0.5 mm / 0.005 rad (seed 2).
- **Frames.**
  - f0 (start);
  - f2, the sweeper's first H30 rest frame: the first frame of its only run of >= 5 frames with no hand point within
    30 mm and < 2 mm per-frame motion, run [2, 8]. Found from the packed geometry before this file.

| Gate | Rule | Binding |
|---|---|---|
| E1 | The sweeper's rotation at 2 s < 5 deg in >= 15 of 16 jittered copies, at f0 and at f2 (exact copy reported) | yes |
| E2 | Visual mesh md5 unchanged: library c126a8ff, simulator `<visual>` glb c32f43de; submitted mesh untouched | yes |
| E3 | Collision piece count stated: FlashCHORD's CoACD (1.0.11, threshold 0.05) of the candidate collision glb, plus foot sectors (one each), against packed 19 | stated |
| E4 | Plain-MuJoCo contacts: max nefc / ncon and copies over 512 / 256, against packed | indicative; determined-wright's `budget.py` is binding |

- **Also reported:**
  - the fill volume (cm3) and which resting poses got a slab, with the tool's status per pose;
  - the dust pan's result (not used);
  - overlap of the sweeper's candidate pieces with the packed dust pan at f0 and f2;
  - whether the fill reaches below the sweeper's lowest point at its other rest frames (the tool forbids this).
- **Delivery if E1 and E2 pass:**
  - `ev19/sets/mini_sweeper/`: the URDF, plus the filled glb if it is small; otherwise it stays in scratch with its
    sha256;
  - `ev19/README.md`.
- **If E1 fails:** the candidate is kept in scratch with `DO_NOT_USE`, and the README reports it.
- Nothing is tuned after the run. A second build would be a new, dated amendment.
