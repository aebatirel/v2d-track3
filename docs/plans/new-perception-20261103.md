# A new perception method: make the submitted mesh agree with our own trajectory (3 Nov 2026)

Owner: "ideate on a genuinely new perception method, do your research and go the distance".
Labels: [M] measured, [D] measured on public data vs mocap, [E] estimate, [H] hypothesis, [I] inference.

## What tonight's measurements say
1. **The board scores sim rollouts, not perception output.** Changing the poses therefore needs new references and
   retrains. Those cost ≈ $6–8 per episode, and only 1 of the 7 mesh-collision retrains passed tonight.
2. **Payload-only changes reach the board directly.** The kit registers our submitted mesh to the scan
   (`_register_object_body`, scale-normalised trimmed ICP) and converts our poses through that registration. So the
   mesh's shape *and its placement in our tracker's body frame* act like a pose correction on every frame [M, code].
   - Proof [M]: 12e (+0.029 AUC), 13p (+0.010), 13p2 (+0.0015) changed only mesh rows.
3. Our tracker's errors are mostly **systematic biases**, not noise [D]:
   - Kalman / RTS smoothing gives −0.0001.
   - The rest-frame oracle is worth +0.032: ep24 +0.118, ep31 +0.112, ep11 +0.088, ep21 +0.083.
   - Constant per-episode offsets are worth +0.030, mostly along the camera ray (physperc D4 oracle).
   - The pitcher tilts 5–6° because its template base is incomplete.
4. GT-free fixes of that bias have failed or been mixed:
   - placement from depth: mean +0.0026; the pitcher gains +0.1, but thin / compliant objects lose (sweeper −0.14);
   - the stage-1 rest fit: −0.0088;
   - depth-ICP offsets recovered nothing.

   **Depth fitting cannot tell our template error apart from our tracker error.**

## Literature (checked 3 Nov)
- Joint shape-and-pose from RGB-D video: **BundleSDF** (Wen et al., CVPR 2023, NVlabs) and the model-free mode of
  FoundationPose. **Any6D** (Lee, Wen et al., CVPR 2025, github taeyeopl/Any6D): single RGB-D anchor, joint pose +
  size via render-and-compare, evaluated with hand occlusion (HO3D, YCBInEOAT).
- Hand-object video reconstruction: **HOLD** (Fan et al., CVPR 2024) and **MagicHOI** (ICCV 2025, a diffusion prior
  for hand-occluded regions).
- All of these change the trajectory and so would need retrains here. Tonight's test B (re-tracking with better
  templates, −0.043, objects lost) shows how fragile that path is.
- None addresses the thing our scorer rewards: **consistency between the submitted mesh and the submitted trajectory**.

## Proposed method: learn the tracker's systematic body-frame bias per object, apply it as mesh placement
[H1] For each object and template, our tracker's pose is T_track(t) ≈ T_true(t) · B⁻¹ with B roughly constant in the
body frame. B comes from the template's shape error and the tracker's response to it.
- Placing the submitted mesh at B in the tracker frame makes the kit's conversion return T_true. This is payload-only,
  so **no retrains**.
- B is measurable on the 20 public episodes (mocap = training labels) and can be applied to eval episodes of the same
  object.
- **Integrity: this uses public mocap to calibrate an inference constant, so it is GT-informed (like Tier B).** Eval
  application needs the owner's explicit yes. The public test itself is a diagnostic.

Variants, all pre-registered before scoring:
- **H1a:** constant body-frame B per object (rotation + translation; rotation about the symmetry axis excluded for
  symmetric objects), estimated by a robust mean over rest frames of other episodes.
- **H1b:** H1a restricted to the parts with a physical cause: B's tilt only (axis error), translation only.
- **H1c:** a GT-free counterpart. Per episode, choose among candidate meshes and placements by the depth / silhouette
  residual along our trajectory, but only when the residual drops by a pre-registered margin (gated M1). This tests
  whether a GT-free signal can find what H1a learns.

**Falsifier and gate.** Leave-one-episode-out on the public episodes, with the 10-seed registered scorer:
- B is estimated without the held-out episode and scored on it;
- adopt per object only if the held-out mean is ≥ +0.005 and no held-out episode is below −0.01, plus D1;
- report B's dispersion across episodes. Large dispersion falsifies "systematic"; then B is view- or episode-specific
  and H1a fails.

Expected size [E]: up to the systematic part of the +0.030–0.032 oracles on public. For bias-dominated objects
(pitcher, rack, boards, cups) perhaps +0.01–0.02 public, ≈ +0.005–0.015 board AUC. RPE / MPPE fall too. The spoon is
not covered (no public spoon GT).

## Not chosen tonight (and why)
- BundleSDF / Any6D / HOLD re-tracking: the trajectory changes, so references and retrains are needed (days and
  ≈ $100+), and test B showed losses. Revisit only if H1 proves the bias is the main loss and payload-only fixes run
  out.
- Spoon anchor roll: no public spoon GT; expected value ≈ 0 by the facet argument.

## Plan
1. perception-tracking: PREREG, then the H1a / H1b / H1c public LOO on CPU ($0).
2. Owner decision on H1 eval use (GT-informed).
3. If yes and the gate passes: a pose pack on 14p (payload-only). focused-pascal builds; keen-heisenberg verifies and
   uploads.
