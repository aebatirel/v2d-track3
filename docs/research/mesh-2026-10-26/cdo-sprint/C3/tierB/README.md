# C3 Tier B: CD-O-only mesh swaps chosen with public ground truth (2 Nov 2026)

## How ground truth entered the selection (read this first)
- **Every mesh in this set was chosen because it scored best against the public object scans.** The public scans are
  ground-truth geometry of the same physical objects that appear in the eval episodes. For each object we built or
  generated many candidate meshes from public-episode video. We then kept the one with the lowest CD-O against that
  object's public scan. Our scorer is `scripts/mesh_metric.py`, which wraps the kit's own registration and CD-O.
  - So the selection used ground truth.
  - No mesh was built from a scan, and no scan geometry was copied into any mesh.
  - Eval episodes were never scored or used for tuning.
  - The sweeper part program P1 is one step further: two of its construction rules were changed after we compared
    earlier versions with the scan (`../../../diag-2026-10-30/sweeper/README.md` section 6). Ground truth therefore
    influenced its design as well as its selection.
- **This is why it is a separate tier.** Our earlier shipped meshes were chosen by rules fixed in advance, from
  ground-truth-free signals. The exception is the 12c blue cup, which carries the same qualifier as this tier.
- **Approval.** The owner approved this tier explicitly ("Okay I give you permission for all"). keen-heisenberg relayed
  it at 19:00 UTC on 2 Nov, after explaining that this is a GT-informed selection by public-scan score.
- **Kind of submission.** It is a CD-O-only variant. Each leaderboard keeps our best submission, so the pose boards
  stay with the earlier packs.

Labels: [D] diagnostic, scored against the public scan after inference; [M] measured without ground truth;
[E] estimate. Repo paths are relative to `docs/research/mesh-2026-10-26/` unless they start with `meshes/`.

## The set (pack 12e = pack 12d + these payload swaps; transform none for all)
All paths are under `cdo-sprint/C3/tierB/meshes/`. "Shipped" means the mesh in pack 12d that this file replaces. CD-O is
per eval pair, in cm [D]. Frame is a rigid ICP onto the shipped mesh [M]. "Anchor" is the kit-registration error at the
scan anchor [D], per eval seed; it is a pose-risk indicator, not a frame error.

| Object | File (md5) | Replaces (md5) | Eval (slot) | CD-O before -> after [D] | Faces in file | Frame vs shipped [M] | Anchor before -> after [D] | Selection (how GT entered) |
|---|---|---|---|---|---|---|---|---|
| water_pitcher | `water_pitcher_hy21_ep22_k174_s42_lib.glb` (e59c15a3e4a442ebc52e7cd72ab73124) | 12d T3 fit `water_pitcher_t3fit.glb` (61503a91...) | 20 (1) | 0.7226 -> **0.3722** | 400,000 (the kit's `budget_mesh` cuts it to 4090 at packing, as for 12b's dust pan) | ICP 6.89 mm / 1.88 deg; centroid 21.9 mm | 29.4 -> 14.5 mm | Hunyuan3D-2.1 mesh generated from public ep22 frames, seed 42. Chosen as the best of the generator outputs by public-scan CD-O (seed 7: 0.570; SAM 3D: 0.650; T2 pick: 0.771). Placed GT-free; scored once (31 seeds, 0 flips). |
| mini_sweeper | `mini_sweeper_P1_partprog.glb` (55fe1682f09721ca5d4e98477bfef150) | library_v3 (c126a8ff...) | 19 (0), 30 (0) | 0.3171 / 0.3168 -> **0.2212 / 0.2239** | 8,514 (budget at packing; scored at 4096) | ICP 2.17 mm / 1.97 deg; centroid 4.9 mm | 5.2 / 4.8 -> 4.0 / 3.3 mm (ADD) | Part program built from our ep18 observed points. Two of its rules were changed after comparing earlier versions with the scan. Lowest sweeper CD-O of all candidates. |
| plastic_dish_rack | `plastic_dish_rack_dev1_ep31_full.glb` (1176443c748ece893ffdb64a1cc82c9a) | C0 joint rack (bbca8ec0...) | 14 (1), 15 (0), 16 (0), 28 (0), 30 (1) | 0.4537 / 0.4525 / 0.4595 / 0.4619 / 0.4526 -> **0.4203 / 0.4174 / 0.4181 / 0.4194 / 0.4188** | 2,624 | ICP 3.38 mm / 0.60 deg; centroid 5.9 mm | 1.5-3.8 -> 8.1-9.7 mm | Primitive rack fit to public ep31 points (dev build). Lowest rack CD-O of the primitive fits. |
| wooden_piece_1 | `wooden_piece_1_ep24_occ_d2.glb` (015aaae3183760cd8a48d82b5599d32c) | library_v3 (d152b2b5...) | 25 (0) | 0.2219 -> **0.1893** | 4,438 (budget at packing; scored at 4096) | ICP 1.73 mm / 0.85 deg; centroid 2.6 mm | 2.4 -> 3.3 mm (ADD) | Occupancy plate fit to public ep24 points. Lowest occupancy variant by CD-O. 1 flip in 6 seeds (an extra seed, not the eval seed). |
| wooden_piece_2 (**see correction below**) | `wooden_piece_2_ep24_occ.glb` (bf82e385cac24a586168b4f14bf5b245) | library_v3 (825a7fe3...) | 25 (1) | 0.2158 -> **0.1642** | 1,256 | ICP 0.73 mm / 0.59 deg; centroid 4.7 mm | 3.4 -> 4.1 mm (ADD) | Same as wooden_piece_1. 1 flip in 6 seeds (an extra seed). |

- **Not scan copies.** No file is a byte copy of a public scan; md5 was checked against all 10 scan files.
  - Every file was built from our own video-derived points (sweeper, rack, boards) or generated from video frames
    (pitcher).
  - Their CD-O to the scan is 0.16-0.42 cm, far from the near-0 of a scan template.
- **Pose boards.** On the anchor error, the pitcher (29 -> 15 mm) and the sweeper improve on 12d. The boards are slightly
  worse (+0.7-0.9 mm). The rack is clearly worse (about 9 mm vs about 3 mm), so the rack pairs' pose scores will
  probably drop. Each board keeps our best
  submission.

## Expected board effect
Board model: the pair-weighted mean over 36 eval pairs. The public scans stand in for the hidden ones, so the
model is [D] -> [E]; it predicted 12c within about 0.001.
- Measured 12c: 0.30008.
- 12d (tier A) [E]: 0.2902 (-0.0099).
- Tier B [E]: pitcher -0.0097, sweeper -0.0052, rack -0.0052, wooden_piece_2 -0.0014, wooden_piece_1 -0.0009; total
  **-0.0225**.
- **Pack 12e [E]: about 0.268.**
- The spoon (10 pairs) has no public scan and stays as it is.

## Files and commands
- Meshes: `cdo-sprint/C3/tierB/meshes/`. The pitcher is also in the HF store `aebatirel/v2d-store`, under
  `runs/cdo-c3-tierB-20261102/`.
- Pitcher placement. This step is ground-truth free and reads only the generated mesh and our library_v3 pitcher. It
  is the same procedure as the C1 T2 dust pan in pack 12b:
  `python -I cdo-sprint/C1/T2-probe-picks/scripts/place.py water_pitcher <gen>/hy21_sim3/water_pitcher_k174_s42.ply
  meshes/library_v3/water_pitcher.glb <out>`. Output: `results/place_water_pitcher.json`.
- Pitcher scoring, one run [D]: `MESH_SCR=<scratch> python -I cdo-sprint/C3/tierB/scripts/score_once.py water_pitcher
  <placed.glb> C3B/hy21_ep22_water_pitcher_k174_s42_lib cdo-sprint/C3/tierB/results/score_tierB.jsonl`.
- The other four meshes were scored earlier; nothing was re-scored. Records:
  - sweeper: `diag-2026-10-30/sweeper/scores_diag.jsonl`;
  - rack: `results/prim/rack/summary.json` (dev1/ep31_full);
  - boards: `results/prim/boards/scores.jsonl`.
- Frame checks [M]: rigid ICP of 20k surface samples onto the replaced mesh (trimesh), as for 12c and 12d.

## Added for pack 13f (B+; coordinator 19:22 UTC, under the same owner approval)
Pack 13f = pack 13e (13b's poses + 12e's meshes) + these two payload swaps.
- **Why they are now included.** At 19:12 UTC they were held because they would not change a CD-O rank. The coordinator
  reversed the hold at 19:22 UTC. The reason given: meshes also drive the pose boards through registered scoring. Both
  pass C3's pre-set rule (beat the shipped mesh by >= 0.02 cm public-scan CD-O). No leaderboard result was used to
  choose between mesh variants.
- **How ground truth entered.** The same way as for the rest of this tier. Each mesh is the best generator output, chosen
  by its public-scan CD-O. Each was then placed in the library_v3 frame without ground truth (C1/T2 `place.py`) and
  scored once [D] (`results/score_tierBplus.jsonl`). Neither is a byte copy of the public scan (md5 checked) or a scan
  template; both were generated from public-episode video frames.

| Object | File (md5) | Replaces (md5) | Eval (slot) | CD-O before -> after [D] | Faces in file | Frame vs shipped [M] | Anchor before -> after [D] | Selection |
|---|---|---|---|---|---|---|---|---|
| blue_cup | `blue_cup_sam3d_ep22_k156_s7_lib.glb` (672c4048e11afe9b2b9a7eafebbefe58) | C0 obs-lathe cup (9e3a74fd...) | 10, 14, 20, 32, 33 (0) | 0.2900 / 0.2894 / 0.2894 / 0.2930 / 0.2910 -> **0.2595 / 0.2647 / 0.2674 / 0.2683 / 0.2664** | 400,000 (budget at packing) | ICP 1.45 mm / 0.91 deg; axis 0.78 deg; closed end +z like C0 and library_v3 (no flip); extents 100x120x181 vs 93x104x167 mm | 2.1-3.6 -> 4.5-7.3 mm | SAM 3D on public ep22 frames, seed 7. Lowest blue-cup CD-O of the generator outputs. Placement: start pca02, residual 2.99 mm, scale 1.0004. 0/35 flips. |
| mini_dust_pan | `mini_dust_pan_hy21_ep39_k297_s42_lib.glb` (1530b1d3be77507730b00e1c5047cad1) | C1 T2 SAM 3D pick (1976540...) | 19 (1), 38 (0) | 0.2587 / 0.2601 -> **0.2294 / 0.2311** | 400,000 (budget at packing) | ICP 1.61 mm / 0.47 deg; centroid 7.3 mm | 4.7 / 6.0 -> 6.0 / 5.8 mm | Hunyuan3D-2.1 on public ep39 frames, seed 42. Lowest dust-pan CD-O of the generator outputs. Placement: identity start, residual 2.52 mm, scale 1.04. 0/32 flips. |

- **Board effect [E].** Blue cup -0.0035, dust pan -0.0016. Measured 12e was 0.26775, so 13f should be about **0.2627**.
- **Pose.** The blue cup's kit anchor error roughly doubles (2-4 -> 5-7 mm), so the blue-cup pairs may score lower on the
  pose boards than with the C0 cup. The dust pan is about unchanged. Each board keeps our best submission.

## Correction (2026-11-02 ~20:30 UTC): wooden_piece_2 flips at the eval seed under a raw-scan reference
Earlier statements here and in the work log said "the eval seed does not flip". That holds only with mesh_metric's
default, budgeted (4096) reference. With the raw public scan as reference, the eval-25 slot-1 seed 25000176 registers
this plate at 179.18 deg, a flip. This matches the perception lane's 179.2 deg [D].

The C4 50-seed audit gives this plate a 34% flip rate (budget reference). The eval-seed outcome is therefore not robust.
Pack 13f2 restores the library_v3 board 2 on eval 25 slot 1. See `../C4-audit/PREREG.md` sections 8-9.
