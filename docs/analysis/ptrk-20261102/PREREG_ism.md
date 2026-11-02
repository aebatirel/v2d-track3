# Pre-registration: SAM-6D-style detector scoring at frame 0 and at re-detection (2 Nov 2026)

Owner's go-ahead via keen-heisenberg (14:55 UTC); GPU cap $6. Written before any run of this test. Labels as in
PREREG.md.

## Hypothesis [H]
Our detector (SAM2 proposals scored by DINOv2 CLS similarity to grey renders of our meshes, plus our rules) misses the
two extra scores of SAM-6D's Instance Segmentation Model:
- an appearance score from masked patch-to-patch matching against the best template;
- a geometric score: IoU of the proposal box with the projected box of the best template's view placed at the
  proposal's depth, weighted by the visible ratio.

These scores make the choice of mask more reliable at frame 0 and at the track guard's re-detections. Today's public
evidence on detection [M]:
- frame-0 assignments are already right on all 20 public episodes (ep0's lid after the guard's frame-0 retry);
- guard re-detections happen on ep18 (sweeper f155 / f165, the chaotic track) and ep23 (piece 1, 4×, after both boards
  froze from f21: a joint tracking loss, not an identity swap).

So the public test is mostly a no-harm test plus these re-detections. The eval-side motivation (evals 14 / 32 / 33
re-acquisition snaps, eval 8 beige-cup frame 0) cannot be scored and is not used.

## Variants (pipeline/perc2.py DET_ISM, pipeline/ism_score.py; one PRO 6000 box, same code, cached depth)
Same templates, same proposals, eval tracking defaults (library_v3, TRACK_GUARD).
- **Ci**: control (DET_ISM off).
- **ISMr**: `DET_ISM=replace`. ISM final score = (semantic + appearance + geometric × visible) / (2 + visible),
  proposals with semantic ≤ 0.2 barred, plain Hungarian assignment, none of our rules (size / reach / grounding /
  on-table / re-proposal gate / compact prior).
- **ISMa**: `DET_ISM=add`. The ISM final score replaces the CLS similarity inside our rules; everything else unchanged.

Deviations from SAM-6D: our SAM2 proposals (not SAM ViT-H); our 42 icosphere grey nvdiffrast templates (not 42
BlenderProc colour renders); object points centred on the mesh box centre. FoundationPose stays for pose and tracking.

## Scoring and gate (fixed now)
`score_registered.py`, 9a+ meshes, 20 public episodes, each variant vs Ci on the same box. For each variant:
1. mean ΔAUC ≥ +0.005;
2. no episode below −0.02;
3. mean ΔMPPE ≤ 0 and mean ΔRPE ≤ 0;
4. frames with position error > 3 cm not more than Ci's.

A variant passes only if all four hold. If both pass, the one with the higher mean is the candidate.

Also reported:
- frame-0 assignments that differ from Ci (from the logs), each judged right / wrong by its track's frame-0 error vs
  mocap (diagnostic);
- every guard re-acquisition, judged by whether the error after the jump is lower than before it.

**Falsifier:** mean ΔAUC ≤ 0 for both variants.
A pass goes to perfect-following as a candidate, with the per-episode list of eval references that would change.

## Cost
One RTX PRO 6000 (≈ $1.07–1.4/h), 60 runs, ≈ 3–3.5 h: ≈ $3.5–5 [E], within the $6 cap. If credit would fall below
$15 while perfect-following's boxes run, the box is destroyed after saving and the result is reported as incomplete.
