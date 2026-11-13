# Plan after the winners' talks (13 Nov 2026): what would make our algorithm better

Context:
- The boards froze on 4 Nov. We finished 9th by rank sum (Imitation.Tech: AUC 0.886, SP-SR 0.90, MP-SR 0.80, RPE
  2.21 cm, MPPE 1.80 cm, CD-O 0.239, 5th on CD-O; Kaggle API, 13 Nov).
- Improvements now serve the report, the award, a next round or the held-out evaluation, not this ranking.
- Vast credit $9.58, 0 boxes (gallant-franklin, 13 Nov).

Sources:
- The two talks: `docs/analysis/winner-richchentw-20261113/`, `docs/analysis/egocube-cmu-20261113/`.
- The competitor study `docs/research/competitors-2026-11-09.md` (branch `claude/jolly-turing-yqxcxn`).
- STATUS on the session branches of 1–13 Nov.

Labels: [M] measured, [E] estimate, [H] hypothesis.

## Where our loss is
- **Reference vs truth, not the policy.** By 3 Nov our packed rollouts all pass SP/MP-SR against our own references
  (perfect-following audit). The board losses are reference errors of about 2–3 cm, mostly in held phases [M].
  - The 30 Oct split (policy 0.083) is out of date.
  - The winner says the same of their pipeline: policy vs reference 0.10 cm, reference vs Vicon 0.60 cm.
- **Template quality is the gap inside perception** (same stack on 20 public episodes):
  - exact scans as tracking templates: 16 of 20 episodes at 0.96–1.00;
  - our own meshes: 0.945 (2 Nov) [M].
- **Failed episodes cost rank points.** Every team above us has SP-SR and MP-SR at 1.00; we have 2 and 4 failed
  episodes [M]. The failures are the cavity and contact cases (evals 10, 14, 30, the spoon in the holder).
- **Cheap patches are exhausted.**
  - About 20 GT-free perception patches failed (31 Oct – 3 Nov).
  - The 12–13 Nov ideas failed: LLM weight repair, wrench gate, Gemini judge, blob tree.

## What the top teams did that we did not
1. **A render-and-compare tracker on per-frame masks and stereo depth**, with FoundationPose only as a refiner.
   - The winner's first upload (0.902) used this tracker alone.
   - Adding FoundationPose gained +0.038.
   - Masks: GDINO + SAM 2 (winner) or SAM 3 with a hand mask (Purple, egoCUBE).
2. **Meshes fitted to the episode's own video**: parametric shapes by nvdiffrast against silhouettes and stereo
   (winner), or MV-SAM3D + stereo size fit + agent-written parts (egoCUBE, CD-O 0.269). This also removes the
   public-data dependency the organisers ruled out (compliance note, 10 Nov).
3. **Symmetric objects fixed with the visible markers** (egoCUBE). Our note 17 did this (marker-only lid AUC 0.977);
   it was never integrated.
4. **A physically consistent reference**, all from the winner:
   - rest phases level on their support;
   - the frame-0 anchor levelled (3.7° tilt → MP-SR 0.95; levelled → 1.00);
   - the release held longer where it would drop the object.
5. **Collision shapes fixed before training**, analytically (Purple: cup sectors, rack pocket) or by an agent
   (egoCUBE). We carved late, and policies trained on old shapes did not transfer (1 of 7 retrains passed).
6. **A reward weighted like the metric**: 0.1 m centroid keypoints, σ = 3 cm, reward centering (winner +0.023 AUC).
   We removed the 1 m lever but kept σ = 10 cm.
7. **Selection over many rollouts** against the team's own reference (winner: best of up to 320).

## Recommended order

Stop all further work on: the grasp-lock / ILC / evolutionary-grasp line, seed races, variance studies, LLM weight
repair and visual judges. All of it is tested, with negative or no-value results.

### Step 1: reference v2, joint shape and pose (CPU plus one small GPU box; biggest lever)
- Per-frame masks: SAM 3 text prompts per object plus a hand mask (watch and forearm as distractors).
- Per episode, fit the object meshes jointly with their poses:
  - parametric / part programs (we have the autokit DSL from the mesh session);
  - nvdiffrast silhouette loss + stereo point loss over many frames;
  - initialised from our current tracks.
- Then track with the fitted mesh as the template, render-and-compare first and FoundationPose as the refiner.
- Marker-based spin for the pot, lid, cups and rack (note 17 code).
- Every mesh comes from the episode's own video: no public templates in the pipeline.
- **Test (public episodes, GT only in scoring):**
  - reference vs mocap, registered scorer, 20 public episodes;
  - baseline 0.945 / current MPPE;
  - target ≥ 0.96 mean, with no episode dropping by more than 0.02.
  - Falsified if the mean gain is < +0.01.
- Cost: mostly CPU; SAM 3 masks and depth on one RTX PRO 6000 box ≈ $3–6 [E].
- Work: several days of agent sessions. This is item 8 of our old open list, never run.

### Step 2: physical consistency of the reference and of the collision shapes (CPU, $0)
- Support-aware rest snap and frame-0 anchor levelling, judged on SP-SR/MP-SR as well as AUC. Our 30 Oct S3 test
  measured AUC only.
- Release-hold extension: delay a release until the object is supported in a zero-action physics replay.
- Collision proxies built before any training, separate from the scored mesh:
  - cup sectors, rack pocket depth, spoon holder, pot/lid scale;
  - each checked by a replay where the reference must not drop or fling an object.
- **Test:** CPU replays of all 20 public references.
  - Count drops and penetrations before and after.
  - Falsified if the drop/fling count does not fall.

### Step 3: learner with the metric-aligned reward (GPU, needs a top-up)
- Object reward: keypoints at 0.1 m around the centroid, Laplacian σ = 3 cm, reward centering.
- One simple recipe on the step-1/2 references.
- **Test:**
  - 5 public episodes (12, 18, 22, 27 and a spoon twin), current vs new reward, 2 seeds, 5 official draws each;
  - pre-registered rule: mean registered AUC +0.01, no episode −0.03.
- Cost ≈ 20 policies × $2.5–3.3 ≈ $50–65 [E].

### Step 4: selection over many rollouts (GPU, small)
- Run N = 32–64 official rollouts per policy and keep the best against our own reference (GT-free).
- Report the mean as well, so the method stays honest about simulator noise.
- Cost ≈ $5–10 per full 20-episode pass [E].

## Order of spend
Steps 1 and 2 are CPU-first and decide whether step 3 is worth money. Nothing is rented without the owner's
go-ahead.
