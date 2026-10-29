# Design O: build meshes from what the cameras saw, and use interactions only for what they never saw

Labels: **[M]** measured today; **[D]** diagnostic only (public scans or mocap, read after the meshes were built, never a method input); **[E]** estimate; **[H]** hypothesis.

I prototyped this today on CPU in about 1.5 h of wall time, all under `scratchpad/interact/obs/`, and did not touch the repo. Inputs were all allowed at inference: our loc/perc tracks, our FoundationStereo depth, our MediaPipe hands, the raw ego_cam_c video, and our own library meshes (used for the region of interest, for labelling the other objects, and for sampling object colour). The ep23/ep24 depth came from our HF store, every 2nd frame.

## 0. Verdict

- **Where the error is.** Most of our excess is not in places interactions can reach.
  - 51% of the 2,940 cm³ excess lies within 4 mm of the scan surface (thickened walls), and about 590 cm³ bulges outside the scan hulls.
  - Interaction carving reaches about 3–10% of the excess (Design J measured about 100 cm³).
  - Building meshes from the observations acts on every object. That includes the wooden spoon, which appears in 10 of the 20 eval episodes, has no public scan, and has no partner object in eval episodes 35–37.
- **Prototype results [M][D], library mesh → Design O default.**
  - **Lid:** excess 231.8 → 70.6 cm³; 95th-percentile-ish (p90) distance from our surface to the scan 9.6 → 4.3 mm.
  - **Lid on pot (ep2):** closed-state overlap 23.5 → 1.4–4.1 cm³, without any interaction step.
  - **Dust pan:** excess 117.4 → 39.6 cm³; bulge outside the scan hull 37.2 → 7.6 cm³; volumetric IoU 0.22 → 0.33.
  - **Boards:**
    - Stereo depth never sees the board-1 slot: inside the real slot the depth evidence looks exactly like solid wood.
    - The RGB silhouette does see it: 89% of slot voxels against 1% of solid-wood voxels.
    - With silhouette carving plus a small interaction step, slot fill goes from 0.97 / 1.0 to 0.00 / 0.05.
    - Overlap at the assembled pose goes from 10.6 to 0.9–1.0 cm³. Even the public scans, placed at our tracked poses, overlap 1.4 cm³.
- **The white pot fails.** The fine (4 mm) truncation leaves holes:
  - 27% of the scan surface is more than 8 mm from our surface, against 11% for the library mesh; IoU drops 0.27 → 0.17.
  - Two causes I tested today were ruled out: the 15 mm table band and the below-table carve.
  - A ground-truth-free gate catches it: 23–25% of our own depth evidence is left unexplained, against at most 2.4% on the other objects.
  - Taking the coarse solid only where the fine one misses evidence ("local fallback") improves both surface-distance directions. But the pot's upright tip angle drops 49.8° → 16.8°, so for v1 the pot keeps its current mesh.
- **Two things it cannot fix:**
  - **Thickness seen from one side only.** 58% of board 2's solid was never observed at the fine truncation, and its 55 cm³ underside dome remains.
  - **The simulator's convex decomposition.** CoACD refills the slot: overlap at the assembled pose is 17.0 cm³ for both the old (v4) and the new boards. Lowering its threshold to 0.02 or 0.01 still leaves 8.8 / 8.7 cm³.
- **Recommendation.** Build library_v5 in this order:
  1. Observation-first fusion.
  2. Silhouette carving.
  3. Interaction exclusion, limited to voxels with weak evidence.
  4. Ground-truth-free gates, falling back to the current mesh per object.

  Separately, fix the decomposition step, because no mesh change alone survives CoACD.

## 1. Why the current fusion goes wrong (mechanisms, measured)

| # | Mechanism in `pipeline/recon_mesh.py` | Evidence | Fix in Design O |
|---|---|---|---|
| 1 | 12 mm truncation, 4 mm voxels, and a blurred binary solid (Gaussian, lines 278–279) set a thickness floor of about 12 mm | [D] Thin parts are 1.4–2.6 mm in the scans but 9.9–16.5 mm in ours. [M] On the same 2 mm grid, today's rules give a 160 cm³ lid; a 4 mm truncation gives 91 cm³ (scan 81) | 4 mm truncation, 2 mm voxels inside a region of interest, marching cubes on the continuous TSDF |
| 2 | `fill` (lines 249–252) closes every unknown pocket that does not touch the grid border, including gaps that were seen around | Codemap synthetic test: a 9 mm slot is 96% free → 26% free | "adj" closing: fill an unknown pocket only if at least 50% of its boundary touches observed-inside voxels; never fill voxels seen as free |
| 3 | Half-resolution stereo smears a slot only 4 px wide | [M][D] Board-1 slot vs solid wood: free-space count median 3 vs 3 (of ~200 views); inside at 4 mm truncation 0.66 vs 0.71 | Silhouette free space from the RGB colour model |
| 4 | Depth samples less than 15 mm above the table never vote for a surface (line 156): no votes for the lowest 15 mm of a resting object, or for a lying board's top face | [M] Not applying the band inside the object's own silhouette changed the pot only slightly (missing 277 → 272 cm³) | Optional; not the main lever |
| 5 | `below_carve` (lines 158–164) casts one free vote per frame 4 mm under a plane whose position is uncertain by several mm | [M] Single-frame plane offset varies 0.518–0.546 m. [D] The scan, posed by our tracks while lying flat, sits −15.6 to +5.1 mm from our plane. [M] Solid wood in board 2 reads TSDF mean +0.9 (free) with below-carve, −0.7 without | Make below-table a separate counter that only blocks closing, with a margin of at least the measured plane spread [H] |
| 6 | A surface seen from one side only has unobservable thickness; the 12 mm truncation silently invents about 12 mm | [M] Solid present only at the coarse truncation: board 2 207 of 358 cm³, board 1 16 cm³, lid 25 cm³ | Flag it, fill with the coarse field, and resolve with more views, support or interaction |

## 2. Algorithm

**Step 0, first pass (exists).** The current `recon_mesh` at 4 mm gives each object's region of interest and the other objects' meshes used for labelling. Its other objects must be our own meshes, not the public scans; current library builds pass the scans (the codemap's compliance flag).

**Step 1, evidence fusion.** One pass per object and episode, run in parallel; episode grids add together. Grid: 2 mm voxels over the first-pass mesh bounds plus 4 cm. Per voxel:
- Running TSDF sums and weights at truncations 4 and 12 mm (6 mm optional), using today's per-sample rules for table, hand and other-object samples.
- `NF3`: samples of any label (own, hand, table, other) whose depth is more than 3 mm behind the voxel. `NV`: number of views.
- Surface-sample moments, giving an effective noise σ_eff.
- `NB`: below-table hits, kept as a counter. It is not a TSDF vote.
- Silhouette counters `NMF` / `NMV`, as in `maskfuse.py`:
  - Each frame, build an object colour model (Lab median and spread) from our own first-pass mesh's visible surface samples. Visible means depth agrees within 5 mm.
  - A voxel is tested when the depth at its pixel is not more than 3 mm in front of it, so a hand or another object in front blocks the test.
  - It votes free when the pixel colour is more than 4 standard deviations from the object colour.
  - A partner of the same colour never votes free, so the rule is conservative.

**Step 2, classification:**
1. **Cascade.** Use the 4 mm truncation where it has at least 3 votes, otherwise the 12 mm one. Voxels decided only by the 12 mm field are labelled "thickness unobserved".
2. **Silhouette carve.** `NMF ≥ 3` and `NMF ≥ 0.5·NMV` → free. This overrides depth saying "inside", because stereo bleeds across narrow gaps.
3. **Closing.** Use the "adj" rule from table row 2. Voxels seen free by depth (`NF3 ≥ 2`), by the silhouette, or below the table never fill.
4. **Main component.** Keep the component nearest the origin, joining pieces within 8 mm (as today).

**Step 3, mesh.** Marching cubes on the clipped continuous TSDF, then a decimation that keeps the mesh watertight (see gate G8), then the kit budget of 4096 faces.

**Step 4, local fallback.** Where our own 12 mm zero-crossing evidence lies more than 8 mm from the fine solid, take today's solid within 8 mm of that evidence (`localfb.py`).

**Step 5, interaction exclusion, only for objects that share space.**
- At contact or assembly frames, find voxels both objects claim (each object's solid mapped into the other's grid by our tracks, claimed in at least 30% of frames).
- A claim is strong when it was observed inside at 4 mm and not seen free by the silhouette.
- The voxel is removed from the side whose claim is weak. If both are strong, nothing is carved and the conflict is reported as a pose or depth error (`resid.py`).
- Design J's min-cut or XCarve's insertion split can be used here, restricted to weak voxels.

**Step 6, support.** For observed rest segments, run the existing XCarve `auto_rest` flattening, but only inside weak or unknown voxels.

**Step 7, gates (section 7).** Any object that fails falls back to its current library mesh.

## 3. Integration points (exact)

In `pipeline/recon_mesh.py`:
- **Line 89 (`table_plane`):** call `np.linalg.svd(Q - q0, full_matrices=False)`. Without it this allocates an N×N matrix (45.6 GB crash on a clean synthetic table).
- **Lines 196–198 and 229–230:** add `--roi MESH` and `--voxel 0.002`. A 0.6 m cube at 2 mm would be 27 M voxels; a region of interest is 0.9–3.2 M.
- **Line 136:** keep samples with `sdf > -max(taus)`.
- **Lines 184–187:** one accumulator per truncation, using the rule `(sdf > -tau) & (~other | sdf > tau)`.
- **After line 183:** count `NF3` and `NV` over all labels.
- **Lines 158–164:** below-table becomes the counter `NB`, not a TSDF vote.
- **Line 156 (optional):** apply the table band only outside the object's eroded silhouette (`obsfuse3.py`).
- **New arguments:**
  - `--video` for the silhouette counters (`maskfuse.py`).
  - `--save_grid` for an npz of all accumulators, needed by step 5 and by Design J / XCarve.
- **Lines 241–279:** replace with `classify()` (cascade, gates, adj closing, main component, continuous meshing) plus the local fallback. Lines 288–307 stay.

New files:
- `pipeline/interact_resid.py` (from `resid.py`).
- `pipeline/mesh_gates.py` (G1–G9, using `gate_ev.py`, `axisrest.py`, `core.py`, `pairovl.py`, `coacd_thr.py`).

Library and eval:
- Library builds (scratchpad `recon_library2.sh` / `man2.txt` → `meshes/library_v5`) use our own meshes as the other objects.
- Eval: re-fuse per eval episode (task #13) by adding the eval episode's depth and video grids. The colour model is fitted per frame.

Downstream, in FlashCHORD:
- `scene/objects.py:159–178` decomposes each colliding mesh shape separately, using `assets/mesh.py:62–90` with threshold 0.05.
- Pre-splitting slotted or thin objects into several collision meshes might preserve slots. That depends on what the official evaluator imports [H; check `make_assets.py` and the kit].

## 4. Resolving ambiguity (priority order)

1. **Silhouette free beats depth "inside".** Bleeding stereo fills gaps; colour does not. Measured on real wood: 1% false-free on board 1, 0% on board 2.
2. **Fine observation (4 mm, at least 3 votes) places the surface.** Free-space counts alone never override it: on board 1, 85% of solid-wood voxels have at least one free sample, from pose and depth noise. A free-space-priority variant changed volumes by under 2%.
3. **Coarse-only solid is "thickness unobserved".** It is kept but flagged, and step 5 or 6 may change it.
4. **Unknown pockets fill only when they are hidden behind the object's own surface.** That is, at least 50% of the boundary is observed-inside, and the pocket was never seen free, silhouette-free or below the table.
5. **Contested voxels go to the side with fine evidence.** When both sides are strong, nothing is carved and the track is flagged. On board 1, 5.4 cm³ was strong on both sides.

## 5. Prototype results [M; scan columns D]

Default variant: `4c12_adj_g2[m]_f0_cont`. "Today@2mm" means today's rules (12 mm, fill, binary) on the same grid.

| Object (episodes) | Mesh | Excess / missing cm³ | IoU | ours→scan med/p90 mm | scan→ours med/p90 mm | Other |
|---|---|---|---|---|---|---|
| Lid (2) | library_v2 | 231.8 / 25.2 | 0.179 | 3.3 / 9.6 | 2.8 / 5.9 | Closed overlap 23.5 cm³; rim tip 68.1° |
| | today@2mm | 113.3 / 34.2 | 0.242 | 1.8 / 5.9 | 2.2 / 21.9 | Overlap 8.6 |
| | O default | 70.6 / 41.9 | 0.259 | 1.4 / 4.3 | 1.9 / 16.5 | Overlap 4.1 with the O pot |
| | O, 4 mm only | 56.7 / 47.0 | 0.248 | 1.2 / 3.6 | 1.9 / 16.2 | Overlap 1.4–2.7; rim tip 83.1° (scan 75.9°) |
| Dust pan (39, 40, 18) | library_v2 | 117.4 / 24.4 | 0.221 | 2.5 / 7.4 | 2.6 / 6.2 | Outside hull 37.2; scoop 38% filled; tips 67.9 / 42.4° |
| | O default | 39.6 / 29.8 | 0.334 | 1.2 / 2.8 | 1.8 / 6.7 | Outside hull 7.6; scoop 10%; tips 68.2 / 62.7° (scan 68.3 / 56.6) |
| Board 1 (23, 24) | library_v4 | 50.4 / 38.7 | 0.638 | 0.8 / 3.3 | 1.3 / 5.1 | Slot 0.97 filled |
| | O + silhouette + step 5 | 4.6 / 53.4 | 0.711 | 0.9 / 2.5 | 1.3 / 2.8 | Slot 0.00; 6 mm thick vs 8 |
| Board 2 | library_v4 | 74.1 / 9.2 | 0.750 | 1.4 / 3.2 | 1.7 / 3.3 | Slot 1.0; lying face unstable (−1.9 mm margin) |
| | O + silhouette + step 5 | 62.4 / 18.9 | 0.747 | 1.1 / 4.0 | 1.5 / 4.1 | Slot 0.05; dome 55 cm³; lying face 64° |
| Boards, assembled | v4 → O + silhouette + step 5 | — | — | — | — | Overlap 10.6 → 1.02 (ep24), 10.9 → 0.90 (ep23); without silhouette 8.7; CoACD 16.9 → 17.0 |
| Pot (41, 44, 2, 27) | library_v2 | 412.9 / 146.4 | 0.274 | 2.6 / 9.9 | 2.5 / 8.7 | Upright tip 49.8° |
| | O default | 125.6 / 277.2 | 0.166 | 1.5 / 4.9 | 2.6 / 25.1 | Holes; evidence gate fails (0.234) |
| | O + local fallback | 245.4 / 199.3 | 0.262 | 1.8 / 6.9 | 2.2 / 6.6 | Upright tip 16.8° → stability gate fails |

Notes on the table:
- **Pot holes.** I ran two tests and both failed to explain them:
  - Not applying the table band inside the pot's silhouette: missing 277 → 272 cm³ only.
  - Turning off the below-table carve: holes stay, and an under-table skirt appears (extent 15.0 vs 13.2 cm).

  Single-episode grids also have the holes, so cross-episode misalignment is not the cause either.
- **Lid at 2 mm.** Scan→ours p90 is 16–22 mm in every 2 mm variant, including today's rules at 2 mm, against 5.9 at 4 mm. So something is lost at 2 mm itself [H: the component filter drops a thin part].

## 6. What it helps (census and defect numbers; eval roster)

- **Every object**, through thinner walls and fewer bulges. This drives the CD-O metric and registered ADD-AUC.
- **Spoon** (10 eval episodes, thin, no scan) [H]: the main eval beneficiary, since no interaction method can reach it in episodes 35–37.
- **Lid on pot (eval ep1):** closed overlap falls to 1.4–4.1 cm³. Under mocap the scans themselves overlap 6–7.6, so we may now be slightly under-filled (lid missing went 25 → 42 cm³).
- **Boards (eval ep25):** the slot opens through the silhouette (the depth cannot do it), and the residual overlap is resolved by step 5.
- **Dust pan (eval 19, 38):** see the table.
- **Untested here (no local depth):**
  - Cups (eval 10, 14, 20, 32, 33): walls 8–8.8 mm vs 2.1–2.5 mm in the scans.
  - Rack (eval 14, 15, 16, 28, 30): slats 13.6 mm vs 2.1 mm; gaps of 12–20 mm are 41–72% filled.
  - Pitcher (eval 20): walls 16.5 mm vs 2.1 mm; 664 cm³ of interior filled.
  - Sweeper.

## 7. Automatic acceptance gates (no ground truth, CPU)

Thresholds were chosen after looking at diagnostics on these 5 objects. They must be frozen and confirmed on the other 6 objects before eval.

| Gate | Check | Measured |
|---|---|---|
| G1 | Solid voxels seen free by most views (`NF3 ≥ 2` and at least 50% of views) ≤ 0.5 cm³ | O: 0.00–0.02; today@2mm: 0.76–8.76 |
| G2 | Unexplained evidence: share of our own 12 mm zero crossings more than 8 mm from the final surface ≤ 0.05 | O: lid 0.012, dust pan 0.024, board 1 0.015; pot 0.234–0.254 (fails) → local fallback |
| G3 | Silhouette false-free on fine-observed solid ≤ 5%, else the silhouette is off for that object | Boards: 1% / 0% |
| G4 | Colour separability: object vs local background at least 4σ in at least 50% of frames | Not yet measured; this is the risk for the white pot and lid |
| G5 | Coarse-only share of the solid: report, and above 30% mark "thickness unobserved" | Board 2 58%, lid 17%, board 1 7% |
| G6 | At every observed rest segment (static, no hand within 3 cm, at least 15 frames): a stable support within 10° of up, margin ≥ 2 mm, tip angle at least 50% of the first pass | Catches the pot fallback (16.8° vs 49.8°) |
| G7 | At contact frames: mesh–mesh overlap ≤ 1.5 cm³, and after CoACD with the simulator's parameters ≤ 2 cm³ | Boards pass the first (0.9–1.0) and fail the second (17.0) |
| G8 | At most 4096 faces and watertight after the budget | Fails today: the kit's `budget_mesh` returned non-watertight meshes from 25–45k-face 2 mm meshes in 5 of 5 cases |
| G9 | Volume within 0.3–1.1× and extents within 1 cm of the first pass | Catches the pot's under-table skirt (15.0 vs 13.2 cm) |

## 8. Failure modes on the 20 eval episodes

- **Low colour contrast** (white pot and lid on a light table, shadows): the silhouette either does nothing or erodes. G3 and G4 switch it off.
- **Holes on large thin-walled bodies** (pot in eval 1, 3, 5, 6, 8, 28): the cause is unknown. Handled by G2, the local fallback and G6, falling back to v2.
- **One-sided thickness** (objects lying flat, beige cup base): G5 flags it and the coarse field stays.
- **Few views** (beige cup: only ep11, plus eval 8 and 10): more unknown voxels. Per-eval re-fusion adds views.
- **Pose error from the production tracks:** today's loc/perc tracks used scan templates, so pose quality may be optimistic. A thin shell needs σ_eff below about 1.5 mm. Watch G2 and σ_eff.
- **Hands in front:** excluded by the depth test. Skin seldom differs from the wood colour by more than 4σ, so it does not carve.

## 9. Validation on public episodes (diagnostic only)

- Compare each mesh with its scan (`evalscan2.py`): excess, missing, IoU, both surface-distance directions, outside-hull volume, concavity fill, slot fill, thickness.
- Closed or assembled overlap compared with the scan floors (1.4 at our poses; 0.68–0.88 under mocap for the boards; 6–7.6 for lid on pot). Too little overlap means real material was removed.
- Stable poses compared with the scan.
- **Not run:** a FlashCHORD drop test (`stand_check.py`, drop logs). Planned: drop each object 1 cm onto its observed rest pose and measure displacement and tilt after 2 s [E: 0.5 day].
- **Decisive test:** a GPU A/B (section 11).

## 10. Effort, compute, rule risk

**Effort, about 3.5–4.5 days in total, before the 11-04 freeze:**
- Day 1: port into `recon_mesh` behind flags and reproduce today's numbers.
- Day 2: silhouette pass; fetch every-2nd-frame depth for episodes 11, 12, 13, 21, 22 and 31; rebuild the remaining objects and the spoon.
- Day 3: step 5, rest stability, watertight decimation, CoACD gate; build library_v5.
- 0.5–1 day for diagnostics and the A/B, plus 0.5 day on the pot holes.

**Compute [M], single thread:**

| Step | Time |
|---|---|
| Fusion, per object and episode | 1.5–2.5 min (boards and dust pan, 0.9 M voxels), 3.7 min (lid), 5–13 min (pot, 3.2 M voxels) |
| Today's `recon_mesh`, for comparison | 8–10 min per board episode, 38 min for the 3-episode dust pan |
| Silhouette | about 2 min per object and episode |
| Post-pass and step 5 | seconds |
| CoACD | 16–158 s per mesh |

Library about 2–3 h on 4 cores [E]; 20 eval episodes about 4–6 h of CPU [E]. No GPU is needed. SAM2 video masks are an optional upgrade, about 1 min per episode on the perception box [E].

**Rule risk: none as designed.** Two caveats:
- Production must use tracks made with our own meshes (perc2m), not the scan-templated tracks used here.
- Parameters were chosen on public diagnostics. Freeze them before eval and never retune on eval results.

## 11. Experiment that would falsify it

- **CPU, before any GPU spend.** Rebuild cups, rack, pitcher and sweeper with the frozen defaults and gates.
  - **Prediction:** every accepted object gets lower ours→scan p90; scan→ours p90 rises by no more than 2 mm; excess falls by at least 30%.
  - **Falsified if** 2 or more accepted objects worsen scan→ours p90 by more than 2 mm, or a gate accepts a mesh whose scan→ours p90 exceeds 15 mm. Then only the silhouette carve and step 5 survive.
- **GPU, needs your go-ahead, about $10–15 [E].** Registered ADD-AUC, mean of 6 evaluations, v5 vs v4 on ep24, ep18, ep2, ep12 and ep27.
  - **Falsified if** v5 is not better on at least 3 of the 5, or loses more than 0.02 on any.
- **Silhouette-specific.** Falsified if the false-free rate on real material exceeds 5% on any object. Check the white pot and lid first.

## 12. Compared with interaction carving

| | Interaction carving | Observation-first (Design O) |
|---|---|---|
| Reach | Only voxels another object occupies: Design J ≈ 100 cm³ (3%). Census: conflict ≈ coverage (pot 164 covered / 172 conflict; lid 145 / 56) because the partner meshes are themselves bloated | Every excess class on every object |
| Lid result | J: 96.2 → about 64.5 cm³ | 113 → 71 on the same grid; 232 → 57–71 vs v2 |
| Boards, assembled overlap | XCarve 2.86 → 0.0 per episode | 10.6 → 4.9–8.7 alone; → 0.9–1.0 with silhouette and step 5 |
| Main fragility | Relative pose at contact: ep0's flipped lid gives 134 cm³ carved against 164 cm³ of real material | Per-object depth and pose noise, and colour contrast. Failures are local and caught by G1/G2 (as on the pot) |
| Cost | Same fusion pass, plus seconds | Same fusion pass, plus seconds |

Order matters: building from observation first shrinks the partner meshes, which cuts the conflict any later interaction step would have.

## 13. What it cannot fix

- **One-sided thickness:** board 2's dome and its 12 mm vs 9–10 mm plate. Fixing it needs a support plane we can trust (multi-frame, with object pixels masked out) or a planar-face prior [H].
- **Never-seen parts:** the beige cup's base and half its wall (88 cm³ missing); rack slats at about one voxel (2.1 mm).
- **Pot holes** at the fine truncation; cause unknown.
- **Decomposition:** CoACD refills slots in the simulator. For board 1 the union of convex pieces is 300 cm³ against 164 cm³ of mesh.
- **Track errors and compliance:** ep0's flipped lid, ep26's broken rack, and compliant bristles.
- **Not tested:** cups, rack, pitcher, sweeper, spoon, the silhouette on white objects, and transparency.

## Files

Everything is in `/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/obs/`:
- `results_obs.json` (all numbers above)
- Fusion and post-pass: `obsfuse2.py`, `obsfuse3.py`, `maskfuse.py`, `obspost2.py`, `resid.py`, `localfb.py`
- Gates and checks: `gate_ev.py`, `axisrest.py`, `core.py`, `coacd_thr.py`, `pairovl.py`
- Diagnostics: `evalscan2.py`, `slotgrid.py`, `slotmask.py`, `sinkdiag.py`, `planediag.py`
- Data: `grids2/` (evidence grids), `out2/` (meshes and logs)