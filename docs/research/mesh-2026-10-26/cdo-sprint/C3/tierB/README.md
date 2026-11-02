# C3 Tier B: CD-O-only mesh swaps chosen with public ground truth (2 Nov 2026) — DRAFT, pitcher scoring running

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
PITCHER_TABLE_PLACEHOLDER

## Expected board effect
BOARD_PLACEHOLDER

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
