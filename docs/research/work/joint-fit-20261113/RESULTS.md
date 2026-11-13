# Stage 1b results (13 Nov 2026): FALSIFIED by the pre-registered gate

Code frozen at `FROZEN.sha256` (stage1b.py 87a674c5…), run on CPU in this container ($0).
Scored with the registered scorer against mocap (scoring only). Controls reproduce their recorded values exactly (e.g.
ep21 0.8375, ep11 0.8999, ep31 0.8647).

| Arm | Mean ΔAUC (20 eps) | Mean ΔAUC (17 non-dev) | Worse / better | Min ΔAUC | Rest-frame ADD lower | ΔMPPE | ΔRPE | Gate |
|---|---|---|---|---|---|---|---|---|
| P (poses only, silhouette + depth; primary) | −0.0254 | −0.0329 | 16 / 3 | −0.157 (ep2) | 4 / 20 | +0.25 cm | +0.21 cm | **FAIL** (all 4 clauses) |
| JS (shape + pose + table support; secondary) | −0.0211 | −0.0273 | 16 / 3 | −0.075 (ep2) | 3 / 20 | +0.23 cm | +0.21 cm | **FAIL** (all 4 clauses) |

Per-episode rows: `results/gate1b_P.json`, `results/gate1b_JS.json`. Per-episode fit logs: `results/<arm>/ep<N>.stage1b.json`.

## Why it failed [D, with readings marked I]
- **Only the development episodes improved.** ep21 +0.028, ep31 +0.026, plus ep22 +0.019.
  - Elsewhere, most episodes lost 0.01–0.05, including near-perfect controls (ep44 0.998 → 0.973, ep42 0.993 →
    0.962).
  - The falsifier fired: rest-frame ADD rose on 16/20.
  - [I] The fit is noisier than the tracker it corrects. Masks at 400 × 250 (1 px ≈ 4 mm on the table) and a
    robust-loss fit with loose priors move good poses by millimetres in random directions.
- **Pot episodes collapsed** (ep0 −0.141, ep2 −0.157 in P).
  - The pot is the scorer's alignment anchor. The fit rotated its frame-0 segment by 6.5°, which tilts every object
    in every frame.
  - The lid fell 0.97 → 0.74 although its own pose barely moved.
  - The winner's lesson 4 ("one anchor amplifies small errors") was not protected here.
- **Shape scale is not identifiable from these views** for the rack and sweeper; it runs to the ±15 % bound.
- **Same conclusion as stage 1 (depth-only ICP, −0.0088, 9/20):** post-hoc whole-segment refits on top of our
  FoundationPose tracks do not find the remaining bias with our masks and meshes.
  - The winner's tracker differs in kind: full-resolution rendering, per-episode fitted meshes, anchor levelling.
  - It was not tested here.

## What is not tested
- A full render-and-compare tracker (GPU, nvdiffrast, full-resolution masks), replacing FoundationPose rather than
  touching it up.
- Anchor-protected variants (frame-0 anchor pose held fixed). This idea came only after seeing the non-development
  episodes, so any test of it needs a fresh pre-registration and is exploratory.
