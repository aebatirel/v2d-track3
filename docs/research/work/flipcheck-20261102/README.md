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

## D1 no-flip gate on eval 25 (coordinator request, 20:24 UTC; `scripts/d1gate.py`, `results/d1gate_eval25.json`)
Setup: the kit's _register_object_body vs the public scan at the eval seed (1_000_003·25 + 101·slot) and 9 more seeds:
the kit seeds of eps 21, 22, 23, 24, 26 and 27 at the same slot, plus seeds 0, 1 and 2.
- rot = rotation in degrees.
- anchor = distance in mm between the registered candidate anchor and the scan surface centroid, which stands in for
  the hidden anchor. This assumes the scan frame is our body frame.

| Pack / slot | Mesh | Flips | Eval seed rot / anchor | Range over 10 seeds |
|---|---|---|---|---|
| 13f1 o1 | library_v3 wooden_piece_2 (= 12c) | **0/10** | 0.7° / 3.9 mm | rot ≤ 0.9°, anchor 2.3–4.9 mm |
| 13f o1 | Tier B occupancy plate | **2/10, incl. the eval seed** | **179.2°** / 3.5 mm | ep24 also 180.0° |
| 13f1 o0 = 13f o0 | Tier B wooden_piece_1 | **0/10** | 0.7° / 4.1 mm | rot ≤ 1.2°, anchor 3.7–6.7 mm |
| 12c o0 | library_v3 wooden_piece_1 | 0/10 | 0.3° / 1.1 mm | rot ≤ 1.7°, anchor 1.1–3.2 mm |

**Verdict:**
- **13f1 passes D1 on both eval-25 slots.** Slot 0 does not flip at its eval seed, so it stays as the Tier B mesh. Its
  anchor error is about 3 mm larger than library_v3's, a small pose cost [D].
- 13f's slot 1 fails D1.
- The C4 audit's 50-seed flip rates (34% for piece 2, 6% for piece 1) come from the coordinator's message; not re-measured here.

## Both reference modes (bold-albattani's reconciliation, 20:34 UTC)
Their sign-off check had put the public scan through budget_mesh(4096) before registering, and found 1.05° at the eval
seed. With the raw scan they get 179.18°, the same as here. The hidden reference's processing is unknown, so both modes
are now checked. The scripts take `REF_MODE=raw|budget`; raw is the default. In budget mode the scan goes through the
kit's budget_mesh(scan, 4096, 4096) before registering. The candidate is always the decoded packed payload.
- D1 with the budgeted reference (`results/d1gate_eval25_budgetref.json`):
  - **13f1 passes both slots: 0/10 flips each.** Slot 1 at the eval seed 0.7° / 3.4 mm; slot 0 at the eval seed
    0.5° / 3.3 mm.
  - 13f slot 1: 3/10 flips (ep22, ep23 and ep24 seeds, about 178–179°), but not at the eval seed (1.1°).
- So 13f's plate flips at the eval seed only against the raw scan. Either way it fails the ≥ 6-seed D1 rule; 13f1 passes
  in both modes.
- All pairs of 13f1 against budgeted scans (`results/flipall_13f1_budgetref.json`): no flips. The blue-cup rotations
  (95–166°) have tilt ≤ 4°, i.e. axial spin; everything else ≤ 5°.
- The scripts run standalone: `REF_MODE=raw|budget OUT=x.json python -I scripts/d1gate.py KIT SCANROOT LABEL=PACK ...`, and
  the same for flipall.py. They need the kit's v2dlb (budget_mesh needs fast_simplification 0.2.0, as at packing).
