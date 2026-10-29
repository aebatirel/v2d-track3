# Approach 2 pre-registration (written before any lathe/box mesh was scored against a public scan)

Inputs: our library meshes only (meshes/library_v3/*.glb; beige cup also library_v3x). No scan, no mocap.
Seen before writing: GT-free profiles/sections/thickness maps of OUR meshes (out/look.txt, sections_out.png,
out/boards_thick.png). Also seen (caveat): the public scans' bounding boxes and face counts (probe.py), not used below.

## L1 lathe rule (blue_cup, beige_cup v3 + v3x, white_pot, white_pot_lid, water_pitcher)
A axis: candidates = 3 PCA axes + 400 Fibonacci hemisphere directions; per 5 mm slab along the candidate, Kasa circle fit
  (all slab points, then outward-facing points n.r > 0.3, IRLS 3 its); slab valid if >= 50 % of 36 angle bins covered;
  score = median over valid slabs of median|res|/r; valid slabs must span >= 30 % of the extent. Best score wins, then
  refine_axis (slab circle centres -> weighted line, 4 its; kept only if within 15 deg of the start).
B gate: best score > 0.05 -> "not a lathe", no fit.
C profile: 2 mm bins along the axis, 10 deg angle bins; R(h,th) = max r of outward-facing samples; r_out(h) = median over
  angle bins with data; bins with angular coverage < 0.25 dropped; running median of 5 bins. Body = longest contiguous
  run of kept bins with r_out >= 0.5 max r_out.
D ends: an end is capped if >= 50 % of the disc within 0.8 r_out (end ring) holds samples with |n.d| > 0.7 within 15 mm of
  that end. Base = the capped end; if both or neither are capped, base = the end with the smaller r_out (mean of the
  10 mm next to the end). Base plane = the outermost body bin at the base end (flat cut there).
E hollow: if the mouth end is not capped and the object is not a disc (smallest PCA eigenvalue >= 0.1 x middle):
  t = median over body bins within 10 mm of the mouth with inner coverage >= 0.5 of median_th(R_out - R_in), clipped to
  [2, 8] mm; inner profile r_out - t; flat inner floor at base + t. Otherwise solid of revolution.
F appendages: faces of our mesh whose centroid lies > 5 mm outside the lathe body (r > r_out(h) + 5 mm, or > 5 mm
  beyond the body's axial range) are kept and concatenated (scoring mesh); simulator copy = lathe + CoACD of those faces.
G mesh: 64 angle segments, profile at 2 mm. Watertight shell of revolution.
[M] residuals: symmetric mean distance ours<->lathe (no registration, same frame), p90 ours->lathe.
[D] acceptance for the SUBMITTED mesh (same rule as metric-summary.md): eval-pair-weighted dCD-O <= 0 AND dADD <= 0
  AND no new flip, vs library_v3 (beige cup also vs v3x). Otherwise the lathe is usable only as simulator geometry.

## B1 box-with-slot rule (wooden_piece_1, wooden_piece_2)
1 PCA frame of our mesh; T = median ray-cast thickness over the footprint (2 mm grid); mid-plane = median ray mid-point.
2 plate = box: length/width = 0.5-99.5 percentile extents of footprint cells (interior holes treated as recon holes).
3 appendages: faces with centroid > 2 mm outside the slab |s - mid| > T/2 + 2 mm are kept (feet, pegs, markers).
4 slot: from OUR public ep24 reference, last frame (boards crossed): in each board's frame, the part of its plate inside
  the other board's plate (other plate expanded by 0.5 mm) = intersection column; halving prior: the board that moved
  down relative to the other in the last 60 frames loses the lower half of the column (slot opens down), the other
  board the upper half; each slot extends from the column middle to that board's edge.
[M] overlap volume of the two boards at OUR eval-25 reference's last frame (independent of ep24), library vs B1.
[D] same acceptance rule as L1.

## Physical checks (GT-free, our own references only; no parameter is set from them)
P1 beige cup stands at eval-10 frame 0 / blue cup at ep21 frame 0: COM (uniform solid) inside the support polygon
   (points within 1 mm of the table), margin and tip angle.
P2 nest: beige-in-blue penetration at the last frame of our eval-10 reference (samples of beige inside blue).
P3 lid-in-pot penetration at frame 0 of our ep2 and eval-1 references, library vs lathe.

## Revision v2 (2026-10-25 ~09:00 UTC; before ANY scan/mocap diagnostic was run; v1 outputs kept in out/lathe/)
Reason (GT-free only): v1's axis search picked axes 18-20 deg off the cup axis for blue_cup and beige_cup_v3 (refine
rejected by the 15 deg guard); our-mesh circularity MAD about the fitted axis 8.5 mm (blue) and 14.2 mm (pitcher) vs
0.9-1.5 mm where the axis was right. Lid failed gate B (score 0.070).
R2a axis: candidates = 3 PCA axes + best v1 Fibonacci direction + Pottmann-Randrup line-complex axis (normals of a
  surface of revolution meet its axis; IRLS-Huber, 5 its); each refined (refine_axis, 15 deg guard); choose the
  candidate with the smallest body circularity MAD / rmax of the C-step profile. Gate B unchanged (v1 slab score of
  the chosen axis <= 0.05) plus gate B2: body circularity MAD <= 3 mm.
R2b wall t fallback: no mouth bin within 10 mm with inner coverage >= 0.5 -> bins within 20 mm with inner coverage
  >= 0.25 -> else 4 mm.
Everything else as v1. v2 outputs in out/lathe2/.

## Ablation declared before the diagnostic (information only; never a selectable variant)
A1: the v2 lathe forced solid (no hollowing) for blue_cup, beige_cup_v3x, white_pot: separates the interior effect.
A2: B1 box without slot (out/boards/*_box.glb) next to box-with-slot.
