# Design J: rebuild interacting objects together, using one min-cut over the voxels they both claim

The owner's idea is to build each mesh from how the pieces interact. This design turns that into one optimisation per group of objects that touch each other. Each object keeps its own TSDF evidence. Wherever two tracked objects occupy the same space in any frame, a voxel is taken away from exactly one of them, the one whose depth evidence for that voxel is weaker. I prototyped it today on CPU, with scratch code only; the repo is unchanged.

**Result.** It removes the impossible end states (the board joint, the lid on the pot) and takes material from the right object.
- On real ep2 data, about 90% of what it removed from the lid was excess when checked against the scan.
- On a synthetic version of the slotted boards, both slots open fully.
- It does not fix most of the shape error. The defects study found 2,940 cm³ of excess across the library. Only about 100 cm³ of it (roughly 3%) ever sits inside another tracked object.

Labels used below: [M] measured today, [E] estimate, [H] hypothesis.

## 1. Prototype evidence [M]

Scripts and outputs are in `/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/joint/`; all key numbers are in `results.json` there.
- `recon_mesh.py` runs unchanged. `fuse_save.py` only saves the fused grid and works around the SVD memory bug inside its own process.
- Settings: voxel 4 mm, truncation 12 mm, `lam_x` 50, `lam_s` 0.3, `beta` 0.1, `cap` 2, `n_min` 2, `n_req` 4.

**A. Synthetic slotted boards** (`synth_render2.py`). The boards are 9 mm thick with 9 mm slots, posed by our ep23 tracks over our ep23 table plane. Here the truth is the box model, not a scan. "Bleed" depth fills every far gap narrower than 15 px with the near depth, which is the worst case of stereo interpolating across a slot.

| Case | Slot free in mesh (wp1 / wp2) | End-state overlap (cm³) | Real material removed (cm³) | Board split? |
|---|---|---|---|---|
| ideal, independent | 0.26 / 0.97 | 3.4 median, 4.2 max | – | – |
| ideal, joint, halving prior 1.0 | 1.00 / 1.00 | 0.0 (max 0.11) | 2.2 / 2.0 (from the 4 mm grid) | no |
| ideal, carve from both (Co-Section-like) | – | 0 | – | **yes, 111 / 124 cm³ cut off** |
| bleed, independent | 0.26 / 0.14 | 6.3 | – | – |
| bleed, joint, no prior | 0.26 / 1.00 | 0.0 | 0 / **7.7** | **wp2 cut in two (125 cm³)** |
| bleed, joint, halving prior 1.0 | 0.95 / 1.00 | 0.0 | 1.8 / 2.9 | no |

**The simulator's convex decomposition keeps the slots** (CoACD with FlashCHORD's parameters, threshold 0.05).
- Bleed, independent boards: the hulls overlap 10.3–11.0 cm³ at the assembled pose and the slots are 0–2% free. This matches the real ep23/ep24 census (10.9–11.0 cm³), so the testbed reproduces the real defect.
- Bleed, joint: 0.00–0.04 cm³ overlap; slots 92% / 100% free inside the hulls.
- Ideal, joint: 0.45–1.16 cm³ residual hull overlap, which is why there is a hull gate (G5).

**B. Real ep2, pot and lid.** Inputs are our FoundationStereo depth and our tracks. Both objects were rebuilt from ep2 with the current code, using the library_v2 partner (our mesh) as `--others`. All are meshed the same way. Scan numbers are diagnostic only.

| | Lid (scan 81 cm³) | Pot (scan 357 cm³) | Lid-on-pot overlap, our tracks / mocap (cm³) |
|---|---|---|---|
| independent | 128 cm³; excess 96, missing 50, IoU 0.178 | 478; excess 346 | 6.3–6.7 / 10.5–11.7 (penetration about 7 mm) |
| joint, no prior | −35.2 (31.7 excess, 3.5 real), IoU 0.194 | −2.1 (0.7 real) | **0.0 / 0.0** |
| joint, halving prior 1.0 | −32.8 (28.5 excess, 4.3 real) | −5.9 (1.0 real) | max 0.5 / 0.0 |
| carve from both | about the same as joint | −28.8 (5.7 real) | 0 |

Side findings:
- Rebuilding the lid with the current code (with `--below_carve`, our pot as `--others`) already shrinks it from 288 to 128 cm³ (library_v2 → this rebuild). IoU barely changes (0.179 vs 0.178) because more of it is now missing.
- With no prior, the cut separates 22 cm³ more of the lid from its main component; with the prior that drops to 0.6 cm³.

**C. Gate test with a wrong track.** I applied ep0's tracks, where the lid is flipped 179° and posed inside the pot, to the ep2 grids. Without gates, the pot loses 25–29 cm³, of which 16–17 cm³ is real material. Two GT-free statistics separate this case from all five good ones:
- Owner-side observed carve (smaller of the two objects' carved observed-solid volume divided by its observed-solid volume): ep0 3.7–6.4%; good cases 0.26–1.45%.
- Contested share of the lid: 0.37 against at most 0.17 in the good cases.

**Solver.** PyMaxflow (GPL) and SciPy's `maximum_flow` with Dinic (BSD) give the same labels (100% agreement, flow 359.34 vs 359.35). Each pair solves in 0.7–2.7 s. Fusion costs 2.7–5.3 min per object per episode on 4 shared cores.

## 2. Model

**Variables.** One label per voxel of each object's independent solid S_o, which is the current `recon_mesh` closing plus main-component rule. The cut only removes voxels. Adding material is a separate support term (S5).

**Energy:**
- **Data term.** `carve_o(v) = β + min(ev(v)/median_ev_o, cap)`, where `ev = weight · max(0, −tsdf)` over observed voxels. A voxel that was never observed and was only filled by closing costs β. A well-observed solid voxel costs about 1 to 2.
- **Smoothness.** A Potts term with `λ_s` on the 6-neighbourhood inside S_o, so the cut prefers compact carves.
- **Exclusion.** Voxel a of A and voxel b of B are co-located at frame t when one's centre falls into the other's voxel under `T_BA = inv(cam_T_B[t]) · cam_T_A[t]`, mapped in both directions. The penalty for keeping both is `λ_x · min(1, frames/n_req)`. Pairs seen in fewer than `n_min` frames are dropped.
- **Approach-side prior.** Each object yields on the side its partner came from. This is the halving prior; it is explained in section 4.

**Exactness.** Flipping the labels of one object makes every term submodular, so a single s-t min cut finds the global optimum. This is the exclusion construction of Delong and Boykov (ICCV 2009), as described in the Nosrati and Hamarneh survey. For more than two objects, the trick works whenever the graph of interacting objects is bipartite. Our public-episode contact graph is a forest, so the whole library can be solved in one cut:
- edges: pot–lid, blue cup–beige cup, blue cup–rack, rack–pot, rack–sweeper, sweeper–pan, board 1–board 2;
- a triangle of three mutually touching objects would break this; then use QPBO or fix one object.

## 3. Algorithm

**S1. Fuse each object** across all its public episodes with the current `recon_mesh`. Requirements:
- tracks from `perc2m` (made with our own meshes);
- `--others` set to our own meshes, never scans;
- save the grids.

**S2. Build the candidate solid and costs** (the S_o and carve costs from section 2).

**S3. Find co-located pairs** for every episode pair at stride 2. Only use frames that pass the track check (G1).

**S4. Approach direction**, from our tracks only:
- If the partner travels at least 2 cm while in contact (a sliding insertion), use that travel.
- Otherwise use the move in the frame just before contact and just after it.

Then bias the carve cost of each contested voxel by `−halve · clip(s, −1, 1)`, where s is the voxel's position along the approach direction, relative to the contested set's centre and in units of its half-extent.

**S5. Support term (adds material).** [H, not yet tested] This replaces the hand-picked `flatten_base`.
- A rest window is one where the object is static for at least 10 frames and its lowest voxel is within 3 cm of the per-frame table plane.
- Over each rest window, add chain constraints on never-observed voxels in the object's footprint below it, down to the plane: if a voxel is solid, the one below must be solid too.
- Add a unary "solid" preference at plane height. Both terms are submodular, so they go into the same cut.

**S6. Solve** with SciPy Dinic.

**S7. Gates** (section 8). If an interaction fails a gate, drop it and re-solve.

**S8. Mesh and recheck.** Apply the Gaussian and marching cubes as now, then `budget_mesh` and CoACD. Recheck overlap on the hulls. If it exceeds 0.5 cm³, re-carve with the partner dilated by one voxel.

**S9 (optional).** Run S1 once more with the new meshes as `--others`.

Optionally, run the contested region on a 2 mm grid by trilinear resampling. The 4 mm grid costs about 2 cm³ of real material per board [M].

## 4. How ownership is decided without ground truth

Non-penetration plus the observed motion do **not** decide who owns the contested space at an interlocking joint. If board A keeps its slot over [a, H/2] along the insertion axis and board B over [−H/2, a] (in A's frame), the assembly works at every insertion depth for any a. The bleed run shows the degenerate end of that family: one board is cut through.

The cut therefore decides, in this order:
1. **Depth evidence.** Material that closing invented costs about 0.1 to carve; material the cameras saw costs 1 to 2. This decided ep2: the pot's rim keeps its material and the lid's weakly observed lower ring yields.
2. **Persistence.** Exclusion weight grows with the number of frames that support it, so transient bristle contacts drop out.
3. **Smoothness.** It prefers whole slot columns over scattered voxels.
4. **Approach-side halving prior.** It splits a tie at the middle of the contested set, across the approach axis. This is right for cross-halving joints. It is wrong by the size of the asymmetry for joints with unequal notches, which still assemble but have the wrong shape.
5. **Refusal.** If the gates say both objects would lose well-observed material, the interaction is treated as a track error (ep0) and dropped.

The S2MDF bisector split (equal signed distances) cuts the contested column diagonally, so it is used only as the final safety projection.

## 5. Where in our code

- **`pipeline/recon_mesh.py`**
  - Lines 241–277 (known/inside, closing, component keep): move into `solidify()`.
  - Lines 278–299 (Gaussian, marching cubes, parts filter, budget): move into `mesh_out()`.
  - Add `--save_grid` after line 240.
  - Line 89: use `svd(..., full_matrices=False)`. The full SVD needs 2 GB on real data and 45 GB on a clean synthetic table.
  - Lines 177–183 (the `--others` rule) stay as they are. They only throw away evidence; the joint step adds the missing rule that space another object occupies is free.
- **New `pipeline/recon_joint.py`**, from the prototype `joint_cut.py` (about 300 lines). It takes the interaction manifest, the saved grids and the episodes' `poses.npz`, and writes the meshes plus a gate report in JSON.
- **Library build.** The scratchpad `recon_library2.sh` and `man2.txt` should become a repo script under `ops/jobs/` that runs S1, then `recon_joint`, then `mesh_color` + `finalize`, into `meshes/library_v5`. `make_assets.py` then consumes it as usual, and `ops/jobs/own_eval.sh:12` uses `LIB=meshes/library_v5`.
- **Downstream.** `flatten_base.py` is replaced by S5. `contact_retarget.py:277` (`stable_ups`) and `:304` (`rest_settle`) use the new stable facets.

## 6. Expected effect per episode (from the census and defects studies)

| Episode / object | Measured defect | Prediction |
|---|---|---|
| ep23/24 boards | 10.5–11 cm³ column; slots 56% / 63% filled | overlap ~0 and slots open, if real stereo behaves somewhere between the ideal and bleed runs [H, test F1] |
| ep2 lid | 24 cm³ closed overlap with library meshes | measured on real data: overlap 0, about 30 cm³ of lid excess removed |
| ep0 | lid track flipped | rejected by gates G2 and G3 (shown by proxy) |
| ep12/13 cup and rack | overlap cores 1.5–3 cm³; 57% of the cup's and 100% of the rack's overlap core lies off the scan | small correct carves, ≤5 cm³ [E] |
| ep11 nested cups | our tracks sink the inner cup 2.7 cm; defects: our meshes conflict 106 cm³ | expected rejected, or net harm if the gates miss it [H] |
| ep31 sweeper in rack | bristle tips persistent (overlap core 2.6 cm³); the rack contact slides (114 cm³ union) | bristle tips carved, likely correct (ours 13 mm thick vs about 2 mm real); risk of shaving the rack top [H] |
| ep18, ep21/22, ep27 | transient contact or none | no change |
| ep26 | rack track broken | excluded by G1 |
| ep18 sweeper, ep24 board edges (cannot stand) | not an exclusion problem | only S5 helps; untested |

## 7. What it cannot fix

- **Wall thickening.** 51% of the excess lies within 4 mm of the scan surface. Better fixes: 2 mm voxels with 4 mm truncation (the synthetic fine9 run left 94.5% of the slot free) or a directional TSDF.
- **Cavities no tracked object ever enters.** The pitcher's interior (664 cm³) and the blue cup's interior (214 cm³; only hands go inside, and hand carving conflicts 90 cm³).
- **Missing geometry.** 867 cm³ in total, including the beige cup's base.
- **Track errors.** It can only refuse them.
- **Objects floating above the table** in our references. That is a pose problem, not a mesh problem.

## 8. Failure modes on the 20 eval episodes, and the gates

**Failure modes:**
- **Track flips and sinks** (as in ep0 and ep11) cause wrong carves.
- **Compliant contacts** (bristles, sponge) and **sliding contacts** over the passive object can carve real material.
- **Thin contested regions** smaller than about 2 voxels get over-carved.
- **CoACD can leave residual overlap** (ideal case 0.5–1.2 cm³).
- **A three-object contact** makes the graph non-bipartite.
- **Fragmentation.** A carve can split a mesh into pieces.

Eval episodes use the frozen library, so by default the joint pass runs on public episodes only and an eval episode cannot be harmed. A per-eval-episode joint pass would be a separate, opt-in step, with the parameters frozen from public episodes.

**Automatic gates (CPU, no ground truth).** Thresholds are hypotheses fitted on only 5 good cases and 1 bad one.
- **G1 Track quality.** Relative-pose jitter below 3 mm median, no relative rotation jump above 20° between consecutive frames, and a plausible object path.
- **G2 Contested share** of each object's candidate solid ≤ 0.30. ep0 lid 0.37 fails; good cases 0.04–0.17.
- **G3 Owner-side observed carve** ≤ 2%. ep0 3.7–6.4% fails; good cases ≤ 1.45%. The margin is thin.
- **G4 No new fragments.** No more than 2 cm³ newly separated. The no-prior bleed run (125 cm³) and ep2 without the prior (22 cm³) fail; with the prior, 0.6 cm³ passes.
- **G5 Hull overlap.** CoACD hull overlap in static co-located windows ≤ 0.5 cm³, otherwise re-carve with a one-voxel margin.
- **G6 Stability.** At each rest window, the observed up direction must be within 10° of a stable facet with a tip angle of at least 2°.
- **G7 Registration sanity.** The carve moves the mesh's centroid less than 5 mm.

## 9. Validation on public episodes only (diagnostics, after inference)

- **D1** Excess and missing against the scan, and the precision of what was removed. Target ≥ 80% of removed volume being excess; ep2 measured 87–90%.
- **D2** Overlap at the end state under the mocap relative pose should be about 0 (ep2 measured 0.0).
- **D3** How much of each board's real slot region is filled (now 56% / 63%; target < 25%).
- **D4** Stable poses compared with the scan's.
- **D5** Simulator drop and settle test (CPU): place the objects at the mocap end-state pose; the joint should stay assembled within 5 mm.
- **D6** Registered AUC of tracks made with the new meshes (needs a GPU).

## 10. Effort, compute, rule risk

- **Effort [E]:** about 2–2.5 agent days.
  - 0.5 d: refactor `recon_mesh`, build `recon_joint` on SciPy, write the interaction manifest.
  - 0.5 d: get the ep23/ep24 depth caches (from the HF store if they were pushed; otherwise a FoundationStereo GPU run, about $1–2) and run F1.
  - 0.5 d: the S5 support term and the stability gate on ep18 and ep24.
  - 0.5 d: rebuild the library with the current code, our meshes as `--others` and `perc2m` tracks, then run D1–D5.
- **GPU:** an ep24 A/B through `hard_ab.sh` costs about $8–10 [E]. Per the rules, I need the go-ahead before renting.
- **CPU [E from M]:** about 25 object-episode fusions at 3–5 min each, so 1.5–2 h; the joint solve takes seconds; CoACD takes 5–10 s per mesh.
- **Rule risk:** none in the method; it uses only our depth, tracks and meshes.
  - Existing compliance flag: the current library used the public scans as `--others` and was fused along scan-templated tracks. Both are replaced in S1.
  - Today's prototype also used those scan-templated loc/perc tracks.
  - Avoid PyMaxflow's GPL by using SciPy, which gives an identical cut.

## 11. Experiments that would falsify the design

**F1 (CPU, decides whether it works on real data).** Fuse both boards from the real ep23 and ep24 depth (all `recon_mesh` defaults, grids saved) and run the joint pass with the frozen parameters above (halving prior 1.0). Predictions:
1. CoACD hull overlap at the assembled pose with our tracks ≤ 1 cm³ (now about 10.9).
2. Diagnostic: at least 70% of the carved volume lies outside the real scan material, and each slot region is ≤ 25% filled.
3. Neither board splits, and the gates pass.

The design is falsified if the gates pass but prediction 2 fails, meaning ownership goes wrong on real stereo. It also fails if the gates reject both ep23 and ep24.

**F2 (GPU, effect on score).** ep24 with library_v4 versus the joint boards plus S5, 6 repeat evaluations each. Falsified for score purposes if the mean registered AUC does not beat the base (0.30–0.31) by more than the spread between repeats. The overnight report found that ep24 is limited by learning the lift and stand-up, so a pass on F1 with no gain on F2 would mean the slot fix is necessary but not enough.

## Sources
- Co-Section (CVPR 2020): https://arxiv.org/abs/2004.04630
- S2MDF (2026): https://arxiv.org/abs/2605.29761
- Delong and Boykov, ICCV 2009: https://mlanthology.org/iccv/2009/delong2009iccv-globally
- The flip trick for exclusion, as described in the Nosrati and Hamarneh survey: https://arxiv.org/pdf/1607.01092
- Directional TSDF: https://arxiv.org/abs/1908.05146
- ShapeGrasp, on the risk of carving with hand volumes: https://arxiv.org/abs/2605.02347
- PhyRecon: https://arxiv.org/abs/2404.16666

Everything is in `/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/joint/`:
- `joint_cut.py`
- `fuse_save.py`
- `synth_render2.py`
- `eval_pair.py`
- `eval_scan.py`
- `eval_synth.py`
- `coacd_check.py`
- `diag_mocap/mk_mocap_poses.py`
- `results.json`

I deleted the 2 GB of synthetic depth because the disk was down to 3.4 GB free; `synth_render2.py 9 15` regenerates it in about 7 min.