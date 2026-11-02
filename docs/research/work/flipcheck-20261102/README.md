# Registration flip check of packed mesh payloads (2 Nov 2026) — diagnostic, public scans as stand-ins

**Why.** tracking-perception (20:23 UTC) reported that pack 13f's (and 12e's) wooden_piece_2 payload registers to the
public scan flipped 180° at eval 25's kit seed, which would score eval 25's piece-2 poses upside down. The mesh lane's
earlier check had said the eval seed does not flip.

**Method.** The kit's v2dlb.track3_pose._register_object_body(decoded payload, scan, anchor, seed) at the kit's own seed
1_000_003·episode + 101·slot (metric_code/track_3/AUC.py). Its rotation does not depend on the anchor. The public scans
(track_3/public/mesh) stand in for the hidden ones, so every value is [D]. Ground truth is read here only as a diagnostic,
after inference; nothing from this check enters a pack. Scripts: `scripts/flipall.py` (every eval pair with a public
scan) and `scripts/flipchk.py` (eval 25 and public eps 23–25).

**Result** (`results/flipall_12c_13f.json`):
- rot = full rotation angle in degrees; tilt = angle between the registered z axis and the scan's z axis.
- **wooden_piece_2, eval 25 slot 1: 13f rot 179.2°, tilt 179.1° (upside down).** 12c (library_v3) gives 0.7°.
  - The same payload flips at public ep24 slot 1 (180.0°) but not at ep23 slot 1 or ep25 slot 0 (about 1°).
  - library_v3 stays ≤ 0.8° at every seed tried.
- Blue cup (13f, generated cup): rot 26–144° on evals 14 / 20 / 32 / 33, with tilt ≤ 4°. These are spins about the cup
  axis. The kit treats blue_cup as axially symmetric (config/tracks.json), so they are not pose errors; 12c's C0 cup
  also spins 177° on eval 32.
- Every other pair, 12c and 13f: rot ≤ 4.7°.
- pack_swap_meshes' kit proxy (base mesh standing in for the scan) had flagged the same piece-2 flip (179.9°) at
  packing. The flag was signed off on the claim that the eval seed did not flip. That claim was wrong for the packed
  payload.

**Fix.** A payload-only revert of eval 25 slot 1 to library_v3 wooden_piece_2 (825a7fe3). No retrain is needed.
- Cost: CD-O for that pair goes 0.1642 → 0.2158 [D], i.e. board CD-O about +0.0014 [E].
- Gain, if the hidden scan behaves like the public one: eval-25 piece-2 pose no longer upside down. tracking-perception
  measured public ep24 piece-2 AUC 0.862 → 0.000 with the flipped mesh, and estimates about −0.02 board AUC [E].
- **Hypothesis:** the board's pose scores will rise when the revert is uploaded. It is falsified if AUC does not rise vs
  13f, other things equal.
