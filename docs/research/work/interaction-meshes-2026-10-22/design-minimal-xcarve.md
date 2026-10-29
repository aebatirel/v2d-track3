# Minimal-carve design: XCarve, shaping the meshes from how the objects interact

## Summary

XCarve is a post-pass on the TSDF grids that `recon_mesh.py` already fuses, plus an automatic support rule. It turns two kinds of interaction into constraints on each object's shape:

1. **Mutual exclusion over time.** Two rigid objects never occupy the same space at the same time. When they appear to, the space goes to the object with real observations there. When both have observations there and the objects were pushed together (an insertion), the contested space is split across the direction of insertion.
2. **Support.** An object seen resting on the table with no hand near it must be able to stand there. If our mesh cannot, its base is flattened at that pose. This automates `flatten_base.py`.

Hands are deliberately left out (the measurement is under rule R5 below).

A scratch prototype of the whole design ran on CPU in this session, using only inference-legal inputs; scans were read afterwards, for diagnostics only. The headline results, all measured:

- **Real ep24, per-episode grids:**
  - Board slot fill went from 80% to 11% (wooden_piece_1) and from 52% to 0% (wooden_piece_2).
  - Assembled overlap with our tracks went from 2.86 to 0.0 cm³. Frames above 1 cm³ went from 50 to 0.
  - The overlap of the simulator's convex pieces (CoACD) at the assembled pose went from 4.9 to 0.56 cm³.
  - Real wood removed: 1.2 and 2.5 cm³. Excess removed: 5.5 and 3.3 cm³.
- **ep2, lid on pot:**
  - Lid excess went from 93.8 to 79.0 cm³; lid missing volume went from 51.1 to 52.2 cm³.
  - The pot is unchanged.
  - Overlap at the final frame went from 6.1 to 2.6 cm³.
- **ep18 (bristle contacts) negative control:** nothing is carved.
- **Support rule, found automatically:** it fixed exactly the two cases that were patched by hand before:
  - the sweeper underside: the up vector is within 2.2° of library_v3's, and the stability margin goes from −4.1 to +5.6 mm;
  - board 2 standing on its edge: within 1.1° of library_v4's, margin from −103 to +6.1 mm.
  
  It left the 5 already-stable cases untouched.

The design does **not** fix the bulk of our mesh error: over-thick walls, filled cup and pitcher interiors, and missing geometry. It removes only small parts of it (see the last section).

---

## 1. Algorithm

**Stage A — pass 0 (compliance fix).** Fuse each object from all its public episodes with `--others` set to nothing. This gives mesh0.

Today's library (v1, v2 and later) was built with `--others` set to the **public scans**. That is not inference-legal, so the library has to be rebuilt.

**Stage B — pass 1.** Fuse each object again with `--others` set to its partners' mesh0 (our own meshes), and save the grid. This gives grid1, holding `tsdf` and `wgt` in the object frame, all episodes fused.

**Stage C — XCarve, for each pair (A, B) over every public episode where both are tracked.**

- **C1 – Classify each voxel.**
  - Observed-inside: `w ≥ min_obs` and `tsdf < 0`.
  - Observed-outside: `w ≥ min_obs` and `tsdf ≥ 0`.
  - Unknown: everything else.
  
  The solid S0 comes from recon_mesh's own closing (fill/near/auto, as today). The evidence of a voxel is `e = w·clip(−tsdf, 0, 1)`. It is 0 for voxels that are solid only because the closing filled them.
- **C2 – Claims.** For each sampled frame (stride 2):
  - Map A's S0 voxel centres into B's grid with `T_BA = inv(cam_T_B[t]) @ cam_T_A[t]`.
  - Interpolate B's tsdf and weight trilinearly, over observed voxels only.
  - B **claims** a voxel x when B's interpolated `tsdf < 0` and `w ≥ min_obs` there. Space B holds only because of closing never claims.
  - Record the claim count n_B(x) and B's mean evidence ē_B(x). Do the same with A and B swapped.
  - Sum the claim counts over episodes.
- **C3 – Persistence.** A voxel is contested when B claims it in at least K = 5 sampled frames (10 raw frames).
- **C4 – Arbitration.** Evidences come from grid1 and are never updated by carving. The result therefore does not depend on which object goes first, and no alternation is needed.
  - **R1 – Closing loses.** A contested voxel whose own evidence is 0 loses to any observed claim. This is always safe.
  - **R2 – Insertion split.** First measure the pair's relative motion into its deepest contact:
    - *full* = the frame with the most claims;
    - *entry* = the frame, within the same unbroken run of claim frames, where B's origin is farthest from where it is at *full*. This also handles disassembly.
    - d = B's origin at *full* minus B's origin at *entry*, in A's frame. The motion counts as an insertion if this travel is more than 2 cm and its straightness (largest PCA singular value divided by the sum of all three) is more than 0.7.
    
    If it is an insertion, every voxel that both objects observed is split by the plane through the centroid of the contested region, normal to d:
    - A loses the entry side, `(x − c)·d < 0`;
    - B loses the far side.
  - **R3 – Evidence ratio.** If the motion is not an insertion (an object resting on, nested in or sliding along the other), the loser is the side whose evidence is at most half the other's (R = 2). Remaining ties are kept and reported to gate G4. As a last resort they can be split by the S2MDF two-object projection (`d₁ + d₂ ≥ 0`) at the end-state pose. Never use that projection as the main rule: it splits the slot column along the diagonal.
- **C5 – Apply.**
  - Set carved voxels to known-free (`tsdf = +1`, `w = min_obs`), so that `fill` cannot fill them again. The codemap measured that fill alone takes a 9 mm slot from 96% to 26% free.
  - Close again in the mode pass 1 chose.
  - After the Gaussian (σ 0.8 voxel), force the field to at least +0.25 at carved voxels. Otherwise a 1-voxel gap closes again (its centre value is −0.01).
  - Run marching cubes, then `budget_mesh` (≤ 4096 faces).
- **C6 – Optional pass 2.** Fuse again with the carved partners as `--others` and repeat C2–C5 once. Stop if the carved volume changes by less than 0.5 cm³. This step is untested.

**Stage D — support rule (`rest_support.py`), run on the final mesh.**

1. Find unassisted rests. All of these must hold:
   - the object's origin moves less than 2 mm per frame (5-frame median) for at least 15 frames;
   - the mesh's lowest point is within ±2 cm of our own frame-0 table plane;
   - in at least 80% of those frames, no MediaPipe joint is within 2 cm of the surface.
2. Cluster the rests by up vector (within 10°).
3. Check stability, snapping to the convex-hull facet within 5° of the observed up. Without the snap, a 1° tilt in the track makes a well-standing pot look unstable. With it, the results match the defects stable-pose table: board 2 lying flat gives a 2.2 mm margin in both.
4. If the object is unstable, apply `flatten_base.flatten(up, 8 mm)`. Accept the change only if the result is stable at that pose and every other observed rest stays stable.

**Stage E — automatic gates (Section 4), then the diagnostics (Section 5).**

## 2. Integration points

- **`pipeline/recon_mesh.py`:**
  - `main()` after line 241: add `--save_grid`.
  - Lines 242–277: move the closing and component selection into `solidify(..., free=None)`.
  - Lines 278–299: move the meshing into `mesh_from_solid(..., keep_open=None)`.
  - Line 89: use `svd(..., full_matrices=False)`. Today it allocates an N×N matrix: about 2 GB on real data, 45 GB on clean synthetic depth.
  - Lines 221 and 99–106: refuse any `--others` path under the public-scan directory (G0).
- **New `pipeline/xcarve.py`.** Port it from the prototype and add claim summing across episodes.
- **New `pipeline/rest_support.py`.** Port it from `auto_rest.py`. It reuses `flatten_base.flatten` (lines 16–22).
- **Library build.** It lives today only in the scratchpad (`recon_library2.sh`, `man2.txt`, `finalize_lib.sh`). Move it into the repo as `ops/build_library.sh`: passes 0 and 1, XCarve, support, gates, then `mesh_color.py`, written to `meshes/library_v5`. Each submission must reference the commit of the code that produced its meshes.
- **Consumers.** `make_assets.py` and CoACD in `flash_chord/assets/mesh.py` (threshold 0.05) stay unchanged. Set `LIB=meshes/library_v5`: `train_eval.sh` and `own_eval.sh` still default to **library_v1**.
- **Eval episodes.** Use the library only. Do not carve per eval episode: bad eval tracks would damage validated meshes, and the boards' slots already come from ep23/24. This also avoids any thresholds touched by eval data.

## 3. Prototype results

Everything here is measured. Scripts are in `/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/minimal/`, and all numbers are in `prototype_results.json` there.

- `fuse_grid.py` runs recon_mesh unchanged and saves its grid.
- `xcarve.py` with `--arb motion --split 1` is the proposed rule; `xcarve_v1.py` is the ratio-only version.

Inputs and provenance:
- Inputs: our loc/perc tracks, our FoundationStereo depth (ep24 pulled from the store), MediaPipe hands, and our library meshes as `--others`.
- Diagnostics only: the scan solids and the synthetic box model.
- The ep2 grids and the synthetic ideal depth were reused from the parallel "joint" run. Its inputs are byte-identical to mine.

| Case | Before | Ratio rule only | **Proposed (R1+R2+R3)** |
|---|---|---|---|
| Synthetic slotted boards, ideal depth, ep23 tracks: slot fill (board 1 / board 2) | 62% / 11% | 2.2% / 2.0% | **2.9% / 0%** |
| ↳ real material removed (cm³) | – | 1.9 / 1.4 | 2.3 / 3.8 |
| ↳ assembled overlap, 1 mm samples: max / final (cm³) | 4.35 / 3.40 | 0.88 / 0.20 | **0.21 / 0.02** |
| Real ep24: slot fill (scan slot box), board 1 / board 2 | 80% / 52% | **80% (fails)** / 6.6% | **11% / 0%** |
| ↳ excess removed / real material removed (cm³) | – | – | 5.5 / 1.2 and 3.3 / 2.5 |
| ↳ overlap with our tracks: max / final / frames > 1 cm³ | 3.0 / 2.86 / 50 | 0.89 / 0.45 | **0.15 / 0.0 / 0** |
| ↳ CoACD union overlap at the end state (cm³) | 4.89 | – | **0.56** |
| ep2 lid on pot (classed as no insertion: travel 1.7 cm): lid excess / missing (cm³) | 93.8 / 51.1 | – | 79.0 / 52.2 |
| ↳ pot excess / missing (cm³) | 347.5 / 228.4 | – | 346.8 / 228.6 |
| ↳ lid–pot overlap: max / final (cm³) | 12.3 / 6.1 | – | 8.0 / 2.6 |
| ep18 sweeper + dust pan (transient bristle contact) | – | – | 0 carved at K = 5 (with K = 1 and no glitch filter: 1.7 cm³, wrong) |

What the prototype showed:

- **Why the ratio rule alone fails on real data.** 93% of board 1's slot voxels read as observed-inside, with tsdf median −0.20, weight 64 and evidence 13.8. Board 2's real wood there scores only 9.1. Stereo fills the 3–6 px gap, and 12 mm truncation adds inside votes behind the faces. Evidence magnitude cannot separate a filled notch from wood, so R2 is needed.
- **Insertion detection on ep24:** entry at frame 166, full at frame 214. The census has the board fully inserted from frame 213. Travel is 11.3 cm, straightness 0.89, and d = (0.09, −0.99, −0.05) in board 1's frame, so board 2 slides along −y as the census says.
- **Stage time:** fusion takes 3–5.5 min per object and episode on a shared 4-core CPU. XCarve takes 1–3 s, the support rule 5–60 s, CoACD 7–30 s per mesh.

**Limits of the prototype:**
- The ep24 grids are per-episode, not library quality: the board 2 grid recovered only 95 of 259 cm³, and the board 1 grid contains a 5.9 cm-thick blob.
- The tracks were made with the public scans as FoundationPose templates (the "A-lite" caveat).
- There is only one real insertion example.
- The thresholds are not calibrated.

## 4. Automatic gates (CPU, no ground truth)

All thresholds are initial values. Calibrate them on public episodes only, then freeze them.

- **G0 – Compliance.** Hard fail if `--others` or any method input points at public scans or mocap.
- **G1 – Track consistency, per pair and episode.**
  - Drop static-segment frames whose relative pose is more than 5 mm from its 9-frame median.
  - Skip the pair-episode if the "strong" contested volume is more than 5% of the smaller solid or more than 10 cm³. Strong means both sides observed it more deeply than their own median evidence, which is physically impossible for two well-observed rigid solids.
  - Measured: ep24 and the synthetic boards 0.0 cm³; ep2 3.3 cm³ (1.5% of the lid), which passes. The prediction is that the ep0 flipped lid and the ep26 broken rack track fail. That is untested.
- **G2 – Carve budget.** Carved volume at most 10% of the object's solid; the number of components unchanged. Otherwise revert that pair.
- **G3 – Persistence.** K ≥ 5 sampled frames. This alone kept ep18 clean.
- **G4 – Outcome.**
  - At static co-located frames, the end-state overlap of the carved meshes is ≤ 1 cm³ or ≤ 25% of the base overlap.
  - The CoACD union overlap is ≤ 1 cm³.
  - The mesh is watertight and has ≤ 4096 faces.
- **G5 – Support.** Edit only at unassisted rests. Accept only if the result is stable there and no other rest of the object regresses.
- **G6 – Registration.** Registering the carved mesh to the uncarved one moves it by at most 2 mm and 2°. This protects ADD-AUC.
- **G7 – Tracking QA (GPU box, production).** Re-tracking (perc2m) with the new mesh must not lower any public episode's render-and-compare QA by more than 0.02.

## 5. Diagnostic-only validation (public episodes, after inference)

- **D1 – Mesh vs scan**, with the defects method:
  - every object loses more excess than real material;
  - both boards have slot fill below 20% in the scan slot box.
- **D2 – Overlap at the assembled or resting pose**, with our tracks and with mocap relative poses (census method):
  - ep23/24 end state ≤ 2 cm³ (scan-on-scan floor: 0.7–0.9 cm³ under mocap, 1.4 cm³ under our tracks);
  - ep2 ≤ 7.6 cm³ (the scan-on-scan overlap under mocap).
- **D3 – Stable-pose table (defects step 5).** Every scan pose with a tip angle of at least 2° has one of ours within 10° that is also stable.
- **D4 – Simulator drop test** (Newton or FlashCHORD on CPU). Dropped from 5 mm at the observed rest pose, each mesh settles within 5 mm and 5°.
- **D5 – End-to-end GPU A/B on ep24 and ep18, controls ep12 and ep27.** This needs the owner's go-ahead and about $8–10.
  - Compare registered AUC over 6 evaluations against library_v4/v3: today ep24 0.31 and ep18 0.715.
  - Check the ep24 reference: the assembled X currently floats with h_last 3.99 / 2.69 cm. The hypothesis is that this falls below 0.5 cm once the overlap is gone.

## 6. What it helps, by episode and object

| Pair or object (public → eval) | Problem (census/defects) | Rule | Expected effect |
|---|---|---|---|
| Boards ep23/24 → ep25 | Notches filled; 10.4–11 cm³ overlap with the library meshes | R1 + R2 | Slots open and overlap → ~0 (measured per episode) |
| Board 2 standing; sweeper underside → ep25, ep19, ep30 | Cannot stand | Support rule | Automatic equivalent of v4/v3 (measured); v3 gave ep18 0.345 → 0.715 end to end |
| Lid / pot ep2 → ep1 | Lid's lower ring inside the pot rim (23 cm³ with the library meshes) | R1 + R3 | Lid trimmed, pot keeps its rim (measured on ep2) |
| Cup in rack ep12/13 → ep14 | 1.5–3 cm³; the rack's slot filled | R1 + R3 | Small; estimate, untested |
| Nested cups ep11 → ep10 | 42.7 cm³ even under mocap; our tracks sink the inner cup 2.7 cm | R3 + G1/G2 | Uncertain, risky; test first (depth cache in the store, 0.88 GB) |
| Sweeper in rack ep31 → ep30 | Sliding contact plus a static rest | R1 + R3 + K | Expected ≤ 3 cm³ of closing-filled bristle tips. Risk to rack slats; untested (1.86 GB depth) |
| Sweeper + pan ep18 → ep19 | Transient bristle contact | G3 | No carving (measured) |
| Cup + pitcher ep21/22 → ep20; pot + rack ep27 → ep28 | No contact or no overlap | – | No change |

## 7. Failure modes on the 20 eval episodes

Eval-time use is library-only, so these are risks for the library's effect on these episodes, plus R2 weaknesses.

- **ep1 (pot + lid).** If an ep0-like flipped lid track were fused into the library, the lid would be carved by the pot. The defects measured 134 cm³ carved with 164 cm³ conflict. G1 must catch it; until then, exclude ep0 from the lid's claims.
- **ep3/5/6, 15/16, 32/33 (with the wooden spoon).** The spoon has no public scan, is thin and is tracked poorly. As a carver it could cut random channels into the cup's filled interior. Recommendation: the spoon does not carve unless its track passes QA. The likely gain is small.
- **ep8 (beige cup + pot).** No public analogue exists, and the beige cup mesh is half missing (IoU 0.13). XCarve cannot help.
- **ep10 (nested cups).** Tracking sink and over-thick walls; risk depends on G1/G2.
- **ep30 (sweeper + rack).** Sliding contact. K does not stop long static rests, so carving relies on the rack slats being well observed.
- **ep25 (boards).** R2 assumes cross-halving: the receiver keeps the far side. For a peg in a blind hole where both sides read as solid (stereo bridging), R2 would cut the peg tip. No such case exists in our data. R1 handles holes that are only closing-filled.
- **Single-object episodes ep35–38.** Only the support rule applies. The wooden spoon is not covered.
- **Rest detection misses** jittery tracks: the ep18 rest from frame 189 to 352 steps about 1.75 mm per frame against a 2 mm threshold. Board 1 in ep24 was never found unassisted.

## 8. What it cannot fix

- **Over-thick walls and plates.** These are 51% of all excess (1494 cm³, within 4 mm of the surface). Only contact faces get trimmed. A thickness prior or finer voxels and truncation are needed (a separate design).
- **Filled interiors.** The blue cup has 213 cm³ filled, the pitcher 664 cm³. Nothing but hands enters them, and hand carving is not usable (R5).
- **Missing geometry (867 cm³).** Examples: the beige cup base, rack slats, board edges, the 36.6 cm² hole in board 1. XCarve only removes material.
- **Width of the carved slot.** It equals the partner's reconstructed thickness. On synthetic ideal depth, 2.3–3.8 cm³ of real wood was lost per board.
- **Tracking errors.** These are gated, not fixed.
- **Table bias.** Scans placed by our tracks sit 0.3–1.4 cm below our plane; the rack sits at −1.36 cm in ep27. `--below_carve 0.004` therefore removes up to about 9 mm of real base on such objects once they are rebuilt. Carving below the plane needs a per-episode offset (the median lowest point at unassisted rests, capped at 15 mm). This is a hypothesis, untested.

**R5 – Hands are excluded (measured).**
- On ep2 with MediaPipe capsules (r = 7 mm, K = 5), restricted to voxels that are solid only by closing, hands carve 0.0 cm³ of the lid and 0.13 cm³ of the pot.
- 34.75 cm³ of pot voxels covered by hands were observed solid; these are hand–object pose errors.
- Unrestricted hand carving removes as much real material as excess (defects: pot 87 vs 96 cm³, blue cup 194 vs 90 cm³).
- The only A/B worth running is the blue-cup interior (ep12/13, closing-only restriction).

## 9. Effort, compute, rule risk

**Effort: about 2.5 days.**

| Time | Work |
|---|---|
| 0.5 day | recon_mesh refactor, guard and SVD fix |
| 0.5 day | `xcarve.py` and `rest_support.py` ported from the prototype, with gates and multi-episode claims |
| 0.5–1 day | Compliant library_v5 rebuild script in the repo, D1–D4 |
| 0.5 day | GPU A/B and write-up |

**Compute.**
- CPU: 2 passes × about 27 object-episode fusions × 3–5 min ≈ 2–4.5 CPU-hours, about 1 h on 4 cores. XCarve takes seconds.
- Depth caches are 0.9–2.4 GB each. With 4.4 GB free locally, process episodes one after another and delete each cache, or use a cheap CPU box.
- GPU A/B: about $8–10 (2 boxes × about 2.2 h at about $1.7/h). This needs the owner's go-ahead.

**Rule risk: low, on three conditions.**
1. `--others` uses only our own meshes. Today's library violates this.
2. Production tracks come from our own templates (perc2m).
3. Thresholds are frozen before any eval run.

Scans and mocap are used only in diagnostic scripts, after inference.

## 10. Experiment that would falsify the design

Rebuild the board library: fuse ep23 and ep24 together, use our own `--others`, two passes, then XCarve with R1–R3.

The design is **falsified** if any of these happens:
- **(a)** Either board's slot fill (scan slot box) is above 40%.
- **(b)** The ep23/24 end-state overlap with our tracks is above 2 cm³ (1 mm samples), or the CoACD union overlap is above 1 cm³.
- **(c)** Either board loses at least as much real material as excess.
- **(d)** Any object in ep2, ep12, ep13, ep27 or ep18 loses more real material than excess.

The end-to-end falsifier: ep24 registered AUC (6 evaluations) does not rise above 0.31. That would mean the slot was not the bottleneck; keep the mesh change only if (a)–(d) pass.

**Status today.** The ratio-only rule already fails (a) on real ep24: board 1 stays 80% filled. The proposed motion-split rule passes (a)–(c) on the per-episode ep24 grids, though narrowly for board 2 (3.3 cm³ excess removed against 2.5 cm³ of real material). The library-quality test and (d) are still open.