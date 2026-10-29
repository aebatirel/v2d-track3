**Adversarial review: plan for physically valid object meshes (2026-10-22)**

Checked against the repo: `pipeline/recon_mesh.py`, `make_assets.py`, `contact_retarget.py`, notes 01 and 19, the work log, and the kit scorer `v2dlb/track3_pose.py`.

**A. Failure modes the plan misses**

1. **Our own fusion corrupts the "observed" states that Stages C and D rely on.**
   - In `/home/user/v2d-track3/pipeline/recon_mesh.py`, depth samples flagged as table (within 15 mm), hand (3 cm bones, 4.5 cm forearm) or other object (within 12 mm) never vote for surface. They still carve free space (`keep = ~other | sdf > trunc`).
   - So near supports and contacts, voxels get only "free" votes. With a few mm of pose jitter, rays that hit the table carve into the true bottom.
   - The eroded underside is then labelled "observed empty", not "never observed". The sweeper library mesh reports `unknown_share 0.009`.
   - Result: Stage C calls it a pose error, and D1/D2 (unobserved voxels only) may not fill it.
   - Fix: keep separate vote counters per ray class (clean, table, hand, other). Treat free votes from flagged rays within about 5 mm of a support or contact as a fourth state: unreliable.
2. **The mesher itself rounds edges and quantises thickness. The table band and hole closing are not the only cause.**
   - `recon_mesh` meshes a ±1 binary solid blurred with σ = 0.8 voxel (3.2 mm) and discards the TSDF's sub-voxel values.
   - A 9 mm board is 2–3 voxels thick. The blur leaves no flat standing edge.
   - Walls come out at about 3 voxels, which is 12 mm: board 2 12 mm, dust pan 11–13 mm, lid 12–13 mm.
   - Add to X3: mesh from the TSDF zero level, no blur, 2 mm voxels.
3. **X3 also omits two settings that hide exactly the regions in question.**
   - `edge_thr`: depth is dropped wherever the 5×5 range exceeds 2 cm. That includes inside the 19 mm notches, between rack fins and at rims.
   - `--others`: surface votes are suppressed within 12 mm of the other object's own slot-less mesh. This is a circular dependency at the joint.
   - Stage A item 2 is already what the code does: the band tests the world height of the observed point, so a lifted underside already votes.
4. **The collision mesh is the decimated visual mesh.**
   - `make_assets.py` uses the 4096-face budgeted GLB as both visual and collision geometry.
   - Note 19 (B3) found that QEM or edge-collapse decimation fails CoACD's checks. That triggers a voxel remesh at L/100, about L/200 of inflation per surface (about 1.1 mm per board).
   - This is not yet checked for our meshes. If it holds, it feeds the floats, F7 and the board overlap. Run CoACD's manifold check, and if needed ship the welded `_full` mesh as collision geometry.
5. **Frame-0 alignment has high leverage, and the plan does not mention it.**
   - `_align_registered_scene` aligns the whole episode from frame 0 of the first object without a symmetry axis.
   - Any float, pop or settle on that anchor object at frame 0 offsets every object in every frame. Note 19 C19 puts this at about 0.125 AUC per persistent cm.
   - Stage F's 3° allowance on the anchor object is about 1.6 cm at a 30 cm lever arm.
6. **The ep12 cup tip is most likely collision inflation, not the rack's missing floor.**
   - Note 19 §1.7 measured a 24° tilt in 1 s for a cup on the rack, starting from mocap states with the scan's CoACD hulls. With welded input and the rack split into ≤120 mm parts it drops to 2–3°.
   - X5 should test the hull path first.
7. **The pose-versus-shape rule cannot work for floats.**
   - An egocentric, top-down camera almost never sees the 1–4 cm gap under a resting object. The rule would therefore add a fake bottom whenever the real cause is the table plane, VO drift or the track.
   - Use cross-segment consistency instead: a shape error repeats in the object frame in every rest on the same face; a pose error does not.
   - There are also two table estimates (`recon_mesh.table_plane` and `mkref.fit_table`). Unify them before measuring floats.
8. **Sending everything over 3 mm or 3° to shape repair is the wrong routing.**
   - It would grow geometry to justify a wrong track: the ep0 lid flip gives 156 cm³ of overlap, and the pitcher is 62° from a stable face.
   - Add a pose-hypothesis branch first: symmetry flips, up re-estimated over the whole rest segment, re-track.
9. **Gate thresholds sit below the noise floor.**
   - Even exact colliders drift 5–11 mm in a 1 s hands-free settle (2–4 mm after the asset fix plus the reference projection R4). The plan's drop-test gate is 3 mm and 3°.
   - The real sweeper scan has only a 5 mm centre-of-mass margin, and the real standing board has +0.4 mm. Our perceived ups are 4.2–6.2° off.
   - Calibrate every threshold by putting the public scans through the same check (diagnostic only). Tie the tilt tolerance to the measured up uncertainty: margin ≥ h_com · tan σ_up.
10. **The spoon is missing from the plan.** It appears in 10 of 20 eval episodes (35–37 contain only the spoon). It has no public twin, is a parametric template with a 0.3 kg placeholder mass, and has no experiment. Exact collision pieces (capsule chain plus ≤4 bowl pieces, note 19 R3) and the Stage B check on eval perception are the only checks available.
11. **Moving contacts are not covered.**
    - Board insertion (eval 25), cup nesting (10) and sweeping need clearance along the whole relative trajectory, not only at one assembled pose. Use a robust swept overlap across the contact frames.
    - ep24 also has non-mesh limits: the two hands snap onto one board, and the policy fails to learn the lift and stand-up. A mesh fix alone may not move ep24 above 0.36.
12. **Evaluation spread is larger than the decision thresholds.**
    - 6 evaluations give ±0.023–0.069 (ep12 0.740 ± 0.032; ep18 0.345 ± 0.046), all on one seed.
    - X8's 0.02 threshold and Stage G's 0.01 are inside that noise. Run X9's second seed paired with X8, not after the freeze.

**B. Claims not supported by the evidence**

13. **Labels that the fact-check does not back.**
    - PhyRecon (1a, Stage B), PhysComp (D2) and HoloScene's penetration energy (1b) are marked "checked". The fact-check only covered HoloScene's runtime and code, and did not check PhyRecon or PhysComp.
    - These numbers are not in the research input: PhyRecon "bulges", "12.56 A100-hours" and "5°/5 cm"; DSO "15–30% unstable"; SceneComplete 0.48 IoU; "plain TSDF thickens thin structures".
    - Cite the angle that contains them, or mark them unverified.
14. **ARM argues against D1, not for it.** ARM reports that stability reasoning beats the extrusion baseline by 25% task success. D1 (fill from the plane up to the observed surface inside the silhouette hull) is that extrusion baseline. Cite ARM for D2.
15. **"Other researchers use the same loop" is an overclaim.** SimuScene stretches the whole mesh or resamples it with SAM3D. HoloScene and SPARCS use generative priors for unseen regions. "Change the shape only where nobody saw it" is our own hypothesis.
16. **Section 1c contradicts the code** (`/home/user/v2d-track3/pipeline/contact_retarget.py:304`).
    - `rest_settle` has `max_tilt=15` and `gap_max=0.05`, and it skips any object whose low points are within 1 cm of another object.
    - So it would not tip the pitcher 62° or the beige cup 46°. It silently leaves them unstable.
    - It also does not lift the seated lid: the lid is skipped and sits more than 5 cm above the table. The real risk there is the reset pop (F10) and mkref's depenetration.
    - The ep12 case does fit the code: the cup falls through a rack with no floor, is not detected as resting on another object, and is lowered up to 5 cm.
17. **"CoACD refills slots" is overgeneralised.** Note 19 B26: the public board collision meshes, once welded, pass CoACD's manifold check and keep the real 1.6–3.2 mm clearance. Test a welded, watertight, undecimated mesh with a slot before building convex pieces.
18. **Stage E mixes up two kinds of piece.**
    - Note 19's ≤120 mm split parts are still decomposed by CoACD, with about 3 mm of tolerance. Only R3 exact convex pieces (≤64 vertices) come back unchanged.
    - The +0.5 / +1.0 mm figures were measured on public-scan assets, not on our meshes.
19. **Arithmetic and internal consistency.**
    - The plan says 6–7 CPU days. Its own per-stage estimates add up to about 11–14 days.
    - "12 of 20 eval episodes" does not match its own lists: 11 from the Section 0 objects, 13 with eval 19 and 25, 16 in the F-table.
    - X8 says 8 episodes but lists about 11, so the cost is about $35–45, not $30.
    - F9 is wrong: `make_assets` computes the centre of mass from a thin surface shell, so interior fill has no effect. Every surface repair (base cap, slot walls) does move it.

**C. Rule problems**

20. **Where the library meshes come from.** Per the work log (2026-10-21 13:20, "A-lite"), the public-video tracks used to fuse our library meshes came from FoundationPose with the public scans as templates. The FAQ says CD-O must use our own reconstructions, not public scans. This is not among the plan's organiser questions; add it.
21. **Choices guided by the scans.**
    - Stage G accepts or rejects changes by the score against the public scan.
    - D5 assigns shape families per object by hand.
    - Together these are the per-object manual edits that Section 0 forbids. Fit every family to every object and keep one by a criterion on our own data and the physics check. Use the scans only for one global accept or reject per pipeline version.
22. **Decisions on eval data.** X1 "decides which eval episodes get repair work" from eval QA output. That is a human decision on test records, against the Kaggle no-hand-labelling rule and our own "never tune on eval" rule. Run only the automatic gate on eval and look at aggregate counts.
23. **Stage H "hold still" is not available as described.**
    - FlashCHORD's actions are residuals on the retargeted reference (note 01). Zero action replays the reference hands into the objects.
    - A hands-off reference plus an untrained checkpoint amounts to submitting the static floor, which is a rule risk.
    - Instead, act on what exists: `qa.py`'s harmful verdict in the checkpoint sweep, plus another checkpoint, reference or seed.
24. **The plan overstates the rule risk of generative models.** Rules 7c and the FAQ allow pretrained models; the only open question is "own reconstruction" for CD-O. Licence and time are the real reasons to drop X10. Put the following in the same email as note 19 questions (a) and (b):
    - separate visual and collision geometry;
    - centre-of-mass changes that repairs cause;
    - the spoon template.

**D. Time and budget**

25. **Schedule.** 24–27 Oct holds about 9–11 days of the plan's own estimates. Cut D5 to the slab (boards). Build D3 only if X3 shows the notch is "seen inside". Merge C into F.
26. **No early submission.** Eval perception (task #6) and the first full submission (#7) are still pending, and the plan starts eval perception on 31 Oct. Packaging, digest or reproducibility failures found then cannot be fixed in time.
27. **Stage E costs are missing** (note 19 C14):
    - 0.1–1 TB of build RAM per split-rack episode at 4096 training worlds;
    - about 0.5 h of cold CoACD;
    - about 10× step cost in seated states;
    - debris screening on Linux;
    - R4 projection, which is needed in every case.
28. **D3 masks.** SAM2 already runs in `perc2.py`, so propagate masks inside the eval perception run instead of renting a separate box. Masks drawn from our own rendered mesh cannot show a slot the mesh lacks. With 3–5° of pose jitter, carving erodes thin parts, so restrict it to regions Stage B flags and to frames where hands do not cover the part.

**E. Cheaper or more robust alternatives**

29. **Separate physics from the scored mesh.**
    - URDF `<collision>` gets the repaired proxy. `<visual>` and the submitted mesh stay faithful to what we observed.
    - The kit registers our mesh by surface moments plus trimmed ICP, so added surfaces shift the registration. Keeping repairs out of the visual mesh removes that risk (F13).
    - Needs the organiser's answer.
30. **Support cap instead of voxel fill.** For a rigid body on a plane, stability depends only on the convex hull of the contact set. Per rest segment, add one closed convex piece: the hull of the observed points within ε of the plane, projected onto it. CoACD leaves it unchanged, and it needs no prior.
31. **Primitives for plates.** Make each board 3 boxes with a notch, sized from plane fits on our depth. It stands on edge by construction and keeps the slot through CoACD. For the spoon, use capsules plus bowl pieces. This is cheaper than D3 + D4 + D5 combined.
32. **Cups as surfaces of revolution.** The scorer already treats cups as symmetric under any spin about their axis (and the lid under 180°), which supports the revolution fit at low rule risk.
33. **A better up estimate.** Take the rest up as the median over the whole segment, fitted to the local table plane. That removes the 4–6° tilts behind the sweeper's F1 at almost no cost.

**Top 5 next actions**

1. **Extended X3 today (CPU, $0).** For all public objects, compare the current mesher with:
   - meshing from the TSDF zero level without blur;
   - 2 mm voxels with 5 mm truncation;
   - separate vote counters per ray class;
   - `edge_thr` off;
   - `--others` off;
   - plus a CoACD manifold check on the budgeted meshes.

   Measure footprint, standing on edge, thickness, notch and registered score (diagnostic only).
2. **Stage B as one automatic, ground-truth-free gate.** It checks the anchor object's frame-0 pop, centre-of-mass margin with the up uncertainty, a drop test, and swept overlap. Calibrate it by putting the public scans through it, then run it on eval perception and report counts only.
3. **Send the organiser email now.** Our own collision geometry and separate visual/collision meshes, inertial values, how the library meshes were built from scan-template tracks, the spoon template, and physics-constrained completion.
4. **Collision-proxy route plus one GPU batch.** Welded undecimated mesh, support caps, board boxes with notch, exact spoon pieces, rack and pot split per note 19 R2, plus R4 projection. Test on ep18, ep24, ep12, ep27, ep31 and ep0 with two paired seeds (about $40–50).
5. **Baseline eval submission by about 27 Oct.** Run eval perception and submit all 20 episodes with library_v3, contact retargeting, and the checkpoint sweep's harmful verdict acted on (about $70–80). The 31 Oct – 3 Nov run then repeats a path that already works.