# Approach 2: primitive meshes, then physical refinement (2026-10-25)

The owner's idea: build the mesh as we do now, re-create it from primitives, then edit it using the motion and what is
physically possible (interlocking). Example: the boards.

Labels:
- **[M]** measured here without ground truth.
- **[D]** diagnostic against the public scans, run after every rule was frozen.
- **[L]** primary source read in full; **[L-abs]** abstract or record only.
- **[I]** inference; **[H]** hypothesis, with the experiment that would falsify it.

Scope: CPU only, $0, no commits, no existing repo file changed. Scripts and the frozen rules are in
`approach2-scripts/` (`RULES.md` holds the pre-registration and its one revision). Outputs are in the scratchpad,
`approach2/out/`.

## Answer

**What works.**
- **A lathe fitted to our own library mesh**, under a rule written before any scan was looked at:
  - Surface of revolution, flat base at the last observed ring, hollow with the wall thickness of the observed rim,
    appendages kept from our mesh.
  - Blue cup: CD-O **0.523 → 0.307 cm**, ADD 10.0 → 9.1 mm [D].
  - Pot: CD-O **0.437 → 0.319 cm**, ADD 6.7 → 4.7 mm [D].
  - Beige cup: CD-O **0.730 → 0.292 cm** (v3x as base), but ADD 5.4 → 8.2 mm [D].
  - No registration flips on any seed.
  - As a package the three pass the project's existing acceptance rule from `metric-summary.md`: eval-pair-weighted
    dCD-O −0.103 cm and dADD −0.41 mm over the 26 known pairs [D].
  - On the 36-pair board this is **0.405 → ≈ 0.331 cm**, about 8th instead of 10th [I]. That assumes the public scan
    stands in for the hidden scan.
- **Physics, measured on our own references:**
  - The beige lathe has a real base. At eval 10's frame 0 it settles after a 3.1° rock with the centre of mass
    32.6 mm inside the base. The v3x mesh's centre of mass is 26–28 mm outside its support [M].
  - The blue cup's cavity goes from **35.4 % solid to 0.2 %** [M].
  - Box-with-slot boards remove the assembled overlap at ep24: 10.7 → 0.05 cm³ [M].
- **Boards:** box-with-slot improves board 1 (0.222 → 0.177 cm) [D].

**What does not work.**
- **Our meshes are too broken for some primitive fits.** The pitcher fails the lathe gate (circularity MAD 8.8 mm),
  and so do the lid, rack and sweeper [M]. Board 2's box gains **2 registration flips** (ADD 157 mm on 2 of 6
  seeds) [D].
  - Primitives raise symmetry, and symmetry is what flips the registration.
- **Primitives do not by themselves make the interactions possible:**
  - Beige in blue at eval 10's stacked pose: 69 % of beige points still lie outside the blue cavity radius, by a
    median of 2.9 mm and a p95 of 10.8 mm [M].
  - The lid still overlaps the lathe pot (22.9 cm³, 3.6 mm deep); it needs a 26 mm lift to clear [M].
  - The slot derived at ep24 removes only 4.7 of 10.7 cm³ at eval 25's pose. Approach 1 found eval 25's board 2
    flipped by 178°.
- **The fit gates do not classify objects without names.** The dust pan and the spoon handle also pass them [M].

**Recommended version.**
1. **Simulator copy, now:**
   - Lathe cups and pot, built as exact primitive or convex pieces.
   - Boards as 3 `<box>` elements each.
   - Plus stage 3 rules: a nest shrink for stacked cups, the lid resting on the rim, and the slot taken from each
     episode's own assembled pose after the board flip is fixed.
2. **Submitted mesh:** blue cup and pot lathes, possibly the beige cup. Do this only after:
   - a CPU rescoring of the stored public rollouts;
   - the owner's decision on the organiser question (§4).
3. **Skip:** pitcher, lid, rack, sweeper and dust pan.

**Expected gain.**
- CD-O −0.05 to −0.075 cm [D→I].
- AUC +0.01 to +0.03 on the 20-episode mean [I]. Most of it comes from eval 10, and only if the nest rule works.
  Evals 1, 20 and 25 stay limited by grasps or the pitcher mesh.

**Cost.**
- ≈ 2 CPU days to build.
- ≈ $3 per arm for the cheapest GPU checks.
- ≈ $80–105 for the strongest A/B (§6.3).

## 1. Primitive family per object

| object (eval pairs) | family | evidence | resists? |
|---|---|---|---|
| wooden_spoon (10) | parametric loft: generalised cylinder with a shell bowl. **Already a hand-made template** (`spoon/`) | handle round: lathe gate passes, MAD 0.29 mm; bowl not | no; compliance risk (§4) |
| white_pot (6) | hollow lathe + handle (kept, or a capsule sweep) | MAD 1.45 mm; capped base, open mouth | no |
| blue_cup (5), beige_cup (2) | hollow lathe with a flat base. **The kit declares both axially symmetric** | MAD 0.99 / 0.88 mm | no |
| plastic_dish_rack (5) | dozens of thin plates and fins; boxes per fin from RANSAC planes | lathe gate fails (MAD 6.8 mm); comb sections | **yes**: wires and fins, CoACD splitting is better |
| mini_sweeper (2), mini_dust_pan (2) | 2.5-D extrusion of the silhouette, plate pieces | sections are flat outlines with a hole | partly: box-like shapes increase flip risk (the sweeper already flips) |
| white_pot_lid (1) | disc or dome lathe + bar knob. **Kit: half-turn symmetric** | axis found (MAD 2.6 mm) but gate B fails (slab score 0.134) | no in principle; our gate is unsuited to a 1.3 cm disc |
| water_pitcher (1) | lathe body + handle + spout (CSG) | gate fails, MAD 8.8 mm: our mesh is a twisted shell | **yes from our mesh**; a lathe would need refitting to depth or masks |
| wooden_piece_1/2 (1 each) | CSG box − slot + kept pegs and feet | §2 | no, but flips (board 2) |

## 2. Measurements

### 2.1 Rules

`RULES.md` was frozen at 08:46 UTC, before any scan comparison.

**L1 lathe rule** (blue cup, beige cup v3 and v3x, pot, lid, pitcher):
- **Axis:** best of 403 directions by slab circle fits.
- **Gate:** slab score ≤ 0.05.
- **Profile:** median over angle of the outward-facing maximum radius, in 2 mm bins.
- **Base:** the capped end; if neither end is capped, the narrower end. Cut flat at the last ring with ≥ 25 % angular
  coverage.
- **Hollow** when the mouth is uncapped. Wall t = median of (outer − inner radius) within 10 mm of the mouth, clipped
  to 2–8 mm.
- **Appendages:** faces more than 5 mm outside the lathe are kept.

**Revision v2 at about 09:00 UTC**, still before any [D] run, for a GT-free reason:
- The v1 search picked axes 18–20° off for both cups, and our own mesh's circularity MAD about that axis was 8.5 mm.
- v2 adds the PCA axes and the Pottmann–Randrup line-complex axis (normals of a surface of revolution meet the axis)
  as candidates.
- v2 chooses the axis by the resulting profile's circularity MAD, and adds gate B2: MAD ≤ 3 mm.
- v1 outputs are kept.

**B1 board rule:**
- Thickness T = median ray-cast thickness of our mesh.
- Box = the 0.5–99.5 % footprint extents.
- Pegs and feet kept.
- Slot = the part of the box inside the other board's box at the last frame of **our** ep24 reference, halved: the
  board that moved down relative to the other loses the lower half.

**Acceptance for the submitted mesh:** the existing project rule (dCD-O ≤ 0, dADD ≤ 0, no new flip).

**Ablations, declared before the diagnostic:** solid lathe; box without slot.

### 2.2 Fit results, GT-free [M]

| input | axis | circ. MAD (mm) | base | wall t (mm) | our surface within 3 mm of the lathe body | ours ↔ fit, sym. mean (mm) |
|---|---|---|---|---|---|---|
| blue_cup v3 | PCA, refined | 0.99 | capped end | 4.9 | 0.76 | 2.92 |
| beige_cup v3x | line complex | 0.88 | narrow end (no cap) | 5.9 | 0.89 | 5.90 |
| beige_cup v3 | line complex | 0.83 | narrow end | 7.4 | – | 7.13 |
| white_pot v3 | PCA, refined | 1.45 | capped end | 7.2 | 0.64 | 3.56 |
| lid / pitcher / rack / sweeper / boards | – | 2.6 / 8.8 / 6.8 / 3.1 / 9.3–21 | gate fails | – | – | – |
| dust pan / spoon (false passes) | – | 1.70 / 0.29 | pass | – | **0.17 / 0.54** | – |

**Boards** [M]:
- T = 7.8 / 12.0 mm; our board 2 is the one the 24 Oct audit found 3 mm too thick.
- Ours ↔ fit: 1.75 / 1.46 mm.
- Slot volume 7.9 / 10.2 cm³.
- Board 2 is the inserted board: it moved 5.4 mm down relative to board 1 in the last 60 frames, which matches the
  audit's narrative.

**Answer to the brief's question.** Yes: the lathe removes the beige cup's open, coned bottom and replaces it with a
flat base of r = 37 mm. It also empties the blue cup: cavity solid share 35.4 % → 0.2 % (pot 9.3 % → 0.1 %).

[H] A name-free family gate needs coverage as well as circularity. The proposed gate is "≥ 0.6 of our surface within
3 mm of the body", which separates the cups and pot (0.64–0.89) from the dust pan and spoon (0.17–0.54). This was set
after seeing these numbers. It is falsified if any object of another family passes on a new library build.

### 2.3 Against the public scans [D]

Measured with `mesh_metric.py`: the kit's CD-O and registration, the packer's budget, eval seeds plus extra seeds.

| object (w) | base | CD-O base → fit (cm) | ADD base → fit (mm) | flips | ablation |
|---|---|---|---|---|---|
| blue_cup (5) | v3 | 0.523 → **0.307** | 10.0 → 9.1 | 0/7 | solid: 0.344 / 6.0 |
| beige_cup (2) | v3x | 0.730 → **0.292** | 5.4 → **8.2** | 0/6 | solid: 0.351 / 7.2 |
| beige_cup (2) | v3 | 0.856 → 0.347 | 6.5 → 7.2 | 0/6 | – |
| white_pot (6) | v3 | 0.437 → **0.319** | 6.7 → 4.7 | 0/8 | solid: **0.545** / 4.8 |
| wooden_piece_1 (1) | v3 | 0.222 → 0.177 | 2.4 → 2.2 | 0/6 | no slot: 0.178 / 4.5 |
| wooden_piece_2 (1) | v3 | 0.216 → 0.230 | 3.6 → 2.3 (max **157**) | **2/6 new** | no slot: 0.227 / 157 |

**Verdicts under the pre-registered rule:**
- **L1 family accepted** (CD-O −0.103 cm, ADD −0.41 mm, 26 pairs).
- Per object, the beige cup alone would fail on ADD.
- **B1 rejected** (new flips on board 2).

**Reading:**
- The hollow interior matters: a solid pot lathe is worse than the library.
- Part of the gain is the clean, symmetric outer surface: even the solid cup lathes beat the library.
- Every gain here comes from our own geometry under a fixed rule. The scans chose nothing.

### 2.4 Physical checks on our own references [M]

| check | library | primitive fit |
|---|---|---|
| beige cup, eval 10 frame 0: static stand | v3x: centre of mass 26–28 mm outside its 0.3–0.6 cm² support (falls; GPU twin: 50 mm / 29°) | base tilted 3.1°; after rocking, centre of mass 4.7 mm off-centre in a 37 mm base, **margin 32.6 mm** |
| blue cup, frame 0 (eval 10 / ep21) | stands (support-band margin 23.7 mm) | stands (support-band margin 15.9 mm; after rocking 29.7 / 30.6 mm) |
| beige in blue, eval 10 last frame (stacked) | 66.9 cm³, beige up to 7.9 mm inside the filled interior | 73.3 cm³ of wall-on-wall overlap, ≤ 2.4 mm deep; 69 % of beige points beyond the blue inner radius (median 2.9, p95 10.8 mm) |
| lid vs pot, frame 0, eval 1 / ep2 | 26.6 / 31.4 cm³, 7.2 / 7.3 mm deep | 22.9 / 22.7 cm³, 3.6 / 3.5 mm deep |
| lid lift to clear the pot, eval 1 / ep2 | 22.7 / 22.6 mm | 25.9 / 26.2 mm |
| boards, last 40 frames, ep24 (in-sample) | 10.5–10.7 cm³ | 0.05–0.42 cm³ |
| boards, last 40 frames, eval 25 (out-of-sample) | 10.7 cm³ | 5.8–7.0 cm³ |

## 3. Literature and open source

GitHub was blocked in this session, so repository pages were not opened. arXiv was reached through curl.

| method | label | what it needs | relevance in 10 days |
|---|---|---|---|
| EMS superquadrics (Liu et al., CVPR 2022, arXiv 2111.14517) | [L] | point cloud; robust to outliers and partial data (Gaussian–uniform mixture, switching) | The authors: "hard to well capture the shape of a thin-walled non-convex object such as a cup". Usable only for solid parts (pot handle, sweeper head) as collision geometry. |
| Marching-Primitives (CVPR 2023, 2303.13190) | [L] | SDF grid of a watertight shape; 2.5–6.7 s per object | Cannot extract parts thinner than the voxel interval; our 4 mm TSDF against 5–8 mm walls and boards fails. Collision copy at best. |
| Efficient RANSAC (Schnabel et al., CGF 2007); CGAL Shape Detection | [L] CGAL docs; paper [L-abs] (the Bonn PDF link served HTML) | points with normals; detects planes, spheres, cylinders, cones and tori | Planes for board faces, rack fins and dust-pan plates. pyransac3d 0.7.0 on PyPI [L-abs]. |
| Pottmann–Randrup, rotational surface approximation | [L-abs] DTU record | points and normals; the axis comes from a linear line complex fitted to the normals | Used in our v2 axis rule. |
| Point2CAD (CVPR 2024, 2312.04962) | [L] | a segmented CAD-like point cloud (ParSeNet/HPNet backbones, ABC) | No: clean CAD data. |
| CAPRI-Net (CVPR 2022, 2104.05652) | [L] | ≈ 9 GPU-h pre-training plus per-shape fine-tuning | No. |
| CSGNet (CVPR 2018, 1712.08290) | [L-abs] | trained on synthetic CSG programs | No. |
| Thrun & Wegbreit, Shape from Symmetry (ICCV 2005) | [L-abs] | partial range data | The principle behind the lathe completion. |
| Schiebener et al., IROS 2016 | [L] | a partial point cloud plus the support plane | Mirrors about symmetry planes and closes the bottom at the support plane. This is our flat-base rule. |
| MuJoCo docs, Computation › Collision | [L] | – | Meshes collide as convex hulls, so non-convex objects must be decomposed. Box–box has an analytic collider with ≤ 8 contacts; general CCD gives 1 contact unless multiccd is on. Quote: decomposing the geometry "pays off at runtime and yields both faster and more stable simulation". |
| Isaac Lab performance guide | [L] | – | "Simpler collision geometries such as primitive shapes … better performance than complex meshes." |

What fits our 10 days:
- our own lathe and box rules (done here);
- RANSAC planes for the plate objects;
- analytic `<box>`/`<cylinder>` colliders, which FlashCHORD never decomposes (note 19, A3/A15).

Learned CAD or CSG reverse engineering does not fit.

## 4. Compliance and integrity

**Are fitted primitives "own reconstructed meshes"?** Probably yes [I].
- Every parameter comes from our reconstruction under a fixed rule: axis, profile, base plane, wall thickness, board
  thickness, slot.
- The kit expects such meshes. Its packer flags "box-like or sphere-like primitive surface" and says "coarse or
  primitive-shaped reconstructions can be intentional; warnings are advisory" (`tracks/track_3/README.md`, check in
  `v2dlb/mesh_quality.py`) [L].
- The FAQ allows pretrained models and external data [L].
- Our box-with-slot plus pegs does not trip the box flag; a bare box would.

**Is choosing the family by name a per-object hand decision?**
- Object names are an allowed input.
- The organisers' own list declares the cups axially symmetric, so a lathe for the cups is defensible.
- The pot, lid and pitcher are not on that list, so choosing a family for them is a human prior.
- Mitigation: run the rule on every object and let the gates decide. Done here: the lid, pitcher, rack, sweeper and
  boards were rejected. The dust pan and spoon passed falsely, which needs the coverage gate [H].

**Risks:**
1. A hand-designed template (CAD of a watering can, fixed spoon dimensions) is knowledge not taken from the video.
   The spoon template is already that.
2. Inherited: the library was fused along tracks bootstrapped with the public scans (email draft, Q3).
3. Integrity: the scans chose nothing. v1 → v2 was revised on GT-free evidence before any [D] run. The beige
   per-object ADD failure is reported, not hidden.
4. Swapping the submitted mesh without re-simulating means the collision geometry differs from the scored mesh.

**For the owner to ask the organisers.** The unsent draft `docs/organiser-email-draft-2026-10-22.md` already asks Q1
(collision geometry separate from the submitted mesh) and Q2 ("a slab for a board or a surface of revolution for a
cup"). Two more questions are worth adding:
- "May the submitted CD-O mesh be a primitive fitted to our own reconstruction, when the packer flags it?"
- "May URDF collisions use analytic `<box>`/`<cylinder>` primitives?"

## 5. Two uses

| use | safe? | helps? |
|---|---|---|
| **Simulator collision copy only** (submitted mesh unchanged) | Safe for CD-O: nothing scored changes. Same question as the arc foot (organiser Q1). | Helps only where the physics fails: eval 10 (beige base and empty blue), possibly 25 and 1 with stage 3. Needs re-running the affected policies. |
| **Also the submitted mesh** | Same body frame, so poses stay valid. Risks are flips (seen on board 2) and an ADD change (beige +2.9 mm) [D]; both are checked by the existing rule. | CD-O −0.05 to −0.075 cm [D→I]. ADD changes are ≤ 3 mm against cm-scale pose errors, so the pose metrics barely move [I]. |

Best order: the collision copy first (it fixes eval 10's mechanism), then the submitted-mesh swap after the CPU
rescoring in §6.3. Using the lathe for both keeps the scored and simulated geometry identical.

## 6. The three-stage pipeline

### 6.1 Assessment

**Stage 2 (primitive re-creation)** is sound where the object really is a primitive and our mesh observes enough of
it: cups, pot body, board 1. It fails where our mesh is too broken (pitcher) or the shape is many thin parts (rack).
It turns harmful when it removes the asymmetric details that anchor the registration (board 2).

**Stage 3 (physical refinement)** is the part that turns fixes into task success. The measurements show stage 2 alone
leaves:
- the nest impossible (median 2.9 mm violation);
- the lid wedged (26 mm to clear);
- eval 25 inconsistent, because of the board flip.

Stage 3 must act on the **simulator copy**. Approach 1 measured that carving the submitted mesh hurts CD-O.

### 6.2 Concrete version

**S1, lathe and box fits (this report's rules).** Author the simulator copies as:
- **Lathe:** a base `<cylinder>` plus K×24 tilted boxes along the wall. The faceting error is r(1 − cos 7.5°)
  ≈ 0.4 mm. Alternatively closed convex wedges of ≤ 64 vertices, which pass CoACD unchanged (note 19, A14).
- **Boards:** 3 boxes each, plus the pegs as convex pieces.
- [H] The contact count stays acceptable for training. Falsified if the build time or steps/s drop by more than 30 %.

**S2, stage 3 rules on our own reference.** Each fixed before running.
- **Nest:** shrink both cups' simulator radii uniformly by δ = ½ × p95 violation over the stacked frames (≈ 5 mm here),
  capped at the wall thickness.
- **Lid on rim:** the lid's frame-0 pose is lifted along the pot axis until the overlap is 0 (a pose fix, not a mesh
  fix).
- **Slot:** from each episode's own assembled frames, after the board-2 flip check (approach 1).

**Submitted-mesh swap:** blue cup, pot and beige cup (the L1 package), gated by §6.3.

**Per-episode effect** [I unless marked]:

| eval (now) | mechanism fixed | expected |
|---|---|---|
| 10 (0.342) | Beige stands [M]; blue cavity open [M]; the nest needs S2 | +0.15 to +0.35 on the episode if the nest works; +0.05 without it |
| 20 (0.336) | Nothing: the pitcher fails the gate; the arc foot is the existing fix | ≈ 0 |
| 25 (0.232) | Slot overlap 10.7 → 0.05 cm³ at ep24 [M]; eval 25 needs the flip fix; grasps are the primary loss (24 Oct audit) | ≈ 0 without the clamp grasp; up to +0.1 with it |
| 1 (0.205) | Lid overlap depth halved [M], but the lid stays wedged without S2; the lid grasp remains | 0 to +0.1 |
| CD-O | L1 package | 0.405 → ≈ 0.33 cm [D→I] |

Total: about +0.01 to +0.03 on the 20-episode AUC [I].

**Build cost:** ≈ 2 CPU days.

### 6.3 Pre-registered tests per family

Box price $1.4–1.9 per hour; one training ≈ 2.5 h; one evaluation ≈ 12 s.

| family | cheapest falsifying test | strongest test (GPU) | rule fixed now | decides |
|---|---|---|---|---|
| **Submitted-mesh swap** (L1 package) | CPU, $0: re-score the stored public rollouts with the lathe as the submitted mesh (kit registered scorer, public scans as hidden), on every stored episode with these objects (ep2, 11, 12, 21, 27, …) | – (no simulation changes) | Pass if the mean registered AUC per object ≥ base − 0.005 and no flip | the CD-O upload |
| **Cups** (ep11 twin of eval 10; ep21) | CPU: ep11 zero-action replay, hands parked, lathe copies plus the S2 nest. Pass: beige within 1 cm / 5° for 30 frames, and stacked-frame overlap ≤ 1 cm³ | ep11, 3 arms (v3x / lathe / lathe+nest) × 2 seeds × 5 evaluations, grasp-lock plus standard learner, registered against mocap: ≈ 15 box-h, **$21–29** | lathe+nest ≥ v3x + 0.05 mean AUC; beige AUC ≥ v3x's in both seeds; no seed < v3x − 0.02 | the simulator copy for evals 10 and 8 |
| **Pot + lid** (ep2 twin of eval 1; ep27 as control) | CPU: ep2 replay of frames 0–40, hands parked, lathe pot plus lid-on-rim pose. Pass: lid within 5 mm / 3° for 10 frames | ep2 and ep27 × {library, lathe+rim} × 2 seeds × 5 evaluations: ≈ 20 box-h, **$28–38** | ep2 ≥ base + 0.05 and ep27 ≥ base − 0.02 | eval 1 (and 28) rerun |
| **Boards** (ep24 twin of eval 25) | CPU MuJoCo proxy (approach 1's tool): weld-driven insertion with B1 `<box>` colliders. Pass: within 1 cm / 5°. Plus the eval-25 overlap ≤ 1 cm³ after the flip fix | 2×2 {CoACD library, B1 boxes} × {current grasp, designed clamp} × 2 seeds × 5 evaluations: ≈ 20 box-h, **$28–38** | B1+clamp ≥ clamp-only + 0.05 | whether eval 25 is rerun with B1 |

Strongest tests together: ≈ 55 box-h, ≈ $80–105. They run in parallel on 3–4 boxes in about 6 h of wall time.

## 7. Reproduce

All commands run from the scratchpad `approach2/`, with `PY=…/scratchpad/venv/bin/python`.

```
$PY lathe_fit2.py blue_cup meshes/library_v3/blue_cup.glb out/lathe2/blue_cup   # also run_lathe2.sh
$PY board_look.py && $PY board_fit.py && $PY board_check.py
$PY docs/research/work/mesh-v5-evidence-2026-10-22/mesh_metric.py run --out out/metric/res.jsonl --workers 4 \
    --manifest metric_manifest.tsv          # [D], after RULES.md was frozen
$PY phys_checks.py; $PY phys_checks2.py; $PY cavity.py; $PY explained.py
```

The code version is commit c4cc38e (branch main-bsky37), on the CPU session container.
