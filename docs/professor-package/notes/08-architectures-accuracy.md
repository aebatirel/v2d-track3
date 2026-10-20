[← Index](../README.md) · [Summary](../00-summary.md) · [← 07](07-mesh-frame-convention.md) · [09 →](09-architectures-resourceful.md)

# 08 — Track 3 candidate architectures: maximum-accuracy lens (design + adversarial review)

Status: COMPLETE v1 (2026-10-04, 21:43-21:55 +03). Research/design only. Nothing installed, run,
downloaded or edited outside this file; no SlamDunk code read or used.

Lens (from the user): maximise the V2D Track 3 leaderboard: AUC, SP-SR, MP-SR, RPE and MPPE on
simulated object trajectories, plus CD-O on our own meshes. Constraints: team of 4+ people, about 4 weeks
to the 2026-11-04 17:00 EST freeze, GPUs rented as needed, Apache-2.0 release for winners, and the Kaggle
licence constraint (OSI code with no commercial limit; pretrained models with incompatible licences
exempt, wording ambiguous). FAQ: CD-O must use our own meshes. Using public scans for tracking is
unconfirmed.

Inputs read in full: `../[track3-requirements.md](../track3-requirements.md), [01-baseline-dissection.md](01-baseline-dissection.md), [02-error-budget.md](02-error-budget.md),
[03-lit-perception.md](03-lit-perception.md), [04-lit-transfer.md](04-lit-transfer.md), [05-alternatives.md](05-alternatives.md). Sibling round-2 notes not yet
available when this was written: `06` (timing audit: suspected frame-mapping bug between evaluator rows
and source frames under `motion_speed: 0.5`) and `07` (mesh frame convention). This note treats both as
P0 open risks and designs every architecture so that their outcome is a parameter, not a rewrite.

Legend:
- [V] verified in a sibling note from primary source or code (citation in that note).
- [M] measured in `02` (perturbations of public mocap, scored with the official scorer functions).
- [U] unverified: secondary source, search snippet or inference.
- [E] our estimate (planning number, not a prediction).
- [H] our hypothesis: an untested idea, including every new idea in this note.

Web checks made for this note (load-bearing only):
- The Kaggle rules page is JS-rendered, and WebFetch returned only the title.
- A search for the standard Kaggle template clause returned this wording [U, search snippet; this
  competition's own text not read]: a submission "will be ineligible to win a prize if it was developed
  using code containing or depending on software licensed under an open source license other than an
  Open Source Initiative-approved license ... or an open source license that prohibits commercial use".
  Pretrained models with incompatible licences are exempt from the licence grant (as the user states).
- NGC `nvidia/isaac/models/foundationpose`: the page says use is "covered by the Model EULA"; the EULA
  terms were not read [U]. So a FoundationPose weight path outside the NVlabs research licence may
  exist, but whether it allows commercial use is unknown.

## TL;DR

1. **Score physics.** Scored error ≈ reference error ⊕ policy tracking error ⊕ slot-0 anchor error ⊕
   body-frame offset ⊕ timing. Log the first two separately on every run; both are measurable with GT
   used only in the scorer.
   - The MP-SR cliff (3 cm / 30 deg per object, time-mean) is shared by perception and policy.
   - CHORD's clean-reference policy error (~1-2 cm ADD [E from V 04]) means perception must stay near
     1 cm or the total goes over the cliff.
2. **Six P0 risks hit every architecture alike; settle them first** (§0.3):
   - timing row mapping (06);
   - frame convention, especially the unscanned wooden spoon in 10/20 eval episodes (07);
   - **new [H]:** unobservable spin of symmetric objects (cups as slot 0, the lid), which a scorer
     anchored on slot-0 frame-0 turns into a whole-scene rotation. Probably fixable only with public
     scans + visible texture, so the organisers' answer on scans is worth tenths of AUC on those
     episodes;
   - catastrophic loss or fling;
   - unknown policy error;
   - multi-object plumbing.
3. **Candidates:**
   - **Arch-1 SMH:** stereo-modular perception (FoundationStereo, FoundationPose on stereo depth with
     multi-hypothesis output, world-frame gtsam smoother with static/support/hand-attachment factors,
     static-prefix and support-constrained anchor) + repaired human-hand reference + training-side
     FlashCHORD changes.
   - **Arch-2 OFP:** Arch-1's object branch + grasps synthesised in Sharpa space and verified or
     optimised in the evaluator's own physics (own sampling-MPC; SPIDER code is NC). No 3-D human hands
     or MANO.
   - **Arch-3 JCE:** whole-clip multi-camera analysis-by-synthesis with discrete mode search + a
     cross-episode object library + closed-loop rollout-vs-video selection/repair.
   - **Arch-F BL+:** the organiser pipeline + 7 decisive fixes, as control and safety net.
4. **Ranking (risk-adjusted accuracy):**
   1. Arch-1 as the base.
   2. Arch-2's transfer half as the leading upgrade. One ~1-3 GPU-h experiment, R4 (physical replay at
      VOC 0, repaired human vs synthesised grasps), can promote it.
   3. Arch-3: harvest its components (library for CD-O and the spoon; flip/spin mode search; rollout
      selection only if a GT-free proxy reaches Spearman ≥ 0.5). Do not build the full joint optimiser
      unless ambiguous windows hold ≥ 25 % of reference error.
   - Arch-F is built first regardless.
5. **Experiment ladder** (§7), ordered by information per GPU-h:
   - R0-R4 together cost < ~25 GPU-h: timing/frame/compliance → spin and rig reconnaissance → stereo
     benchmark → reference-only scoring with error-window diagnosis → hand-source physical replay;
   - R5 sizes the policy error, wall-clock and determinism;
   - only then the large RL sweeps (R7, R8, R12).
   - Total ≈ 330-650 GPU-h (~$0.35-1.6k) [E].
6. **Team** (§8): P1 perception-geometry, P2 objects/frames/meshes/CD-O/spoon, P3 transfer/RL, P4
   infra/evaluation/compliance/submissions (+ Arch-F). Optional P5 hands or MPC (per R4), P6 Arch-3
   components.
   - First pose and CD-O submissions in week 2; recipe frozen Oct 25.
   - Two final picks: best local dev + holdout, and best genuine LB variant.
   - No per-episode leaderboard probing.
7. **Licence:** Arch-1 and Arch-F are high exposure (FoundationPose, nvdiffrast, MANO, NVlabs
   FoundationStereo); Arch-2 is medium. An all-OSI-code path exists at a measurable accuracy cost.
   Build it only if the organisers reject the baseline's own non-commercial stack.

## Progress log
- 21:43 skeleton; all six inputs read; two licence web checks done (above).
- 21:45 §0 premises + §1 spine + §2 Arch-1 saved.
- 21:46 §3 Arch-2, §4 Arch-3, §5 Arch-F saved.
- 21:48-21:50 §6 ranking/matrices, §7 ladder, §8 team/calendar, §9 questions, §10 hypotheses, §11
  limitations saved. 21:55 TL;DR; COMPLETE v1.

---------------------------------------------------------------------------------------------------

## 0. What the score physically rewards (design premises)

### 0.1 Error decomposition every architecture is judged by

Scored trajectory = FlashCHORD rollout of our policy, tracking our reference with our assets, from exact
frame 0, unassisted [V 01 C.10]. After the scorer's single rigid alignment on slot-0 frame-0 [V 02]:

    e_score(t, obj) ~= e_ref(t, obj)     reference vs mocap: perception, mesh frame, scale, timing
                     (+) e_track(t, obj)  rollout vs our reference: policy and physics, GT-free measurable
                     (+) e_anchor(t, obj) slot-0 frame-0 error broadcast to every object and frame
                     (+) e_frame(obj)     constant body-frame offset vs the organiser scan frame
                     (+) e_time(t)        any row/frame mis-mapping (06)

What to measure, and where GT is allowed:
- `e_ref`: score our reference with the kit scorer as if it were a rollout. GT is used only in the scorer.
- `e_track`: FlashCHORD's built-in metrics against our reference [V 04 §8]. Needs no GT at all.
- `e_score`: the kit scorer on the official evaluator export. GT is used only in the scorer.
- Log all three for every run [V idea from 04 §10]. Do not log only `e_score`, because it cannot say
  which half of the system to fix.

The combination rule matters [H]. Independent random errors add roughly in quadrature in 3-D. Lag-type
errors add roughly linearly, because both a smoothed reference and a lagging policy fall behind the
motion in the same direction. Do not budget on quadrature until the R5 rung measures the correlation.

### 0.2 Budget allocation (targets that keep MP-SR alive and AUC high)

MP-SR needs every object's time-mean error below 3 cm and below 30 deg [V 02]. That margin is shared by
`e_ref` and `e_track`. CHORD on clean mocap references reaches AUC 0.918 and MP-SR 0.894 against its
reference [V 04]. That implies a typical policy-only ADD of about 1-2 cm [E], even with a perfect
reference. Perception therefore has to stay near 1 cm, or the policy pushes the total over the cliff.

| Term | Target [E/H] | Why (02 [M] unless marked) |
|---|---|---|
| Common world drift | ≤ 1 cm end-point, ≤ 1 deg | 1 cm costs 0.000 AUC; 3 cm costs −0.084; 5 deg camera rotational drift → MP 0.92, 8 deg → 0.22 |
| Slot-0 anchor (asymmetric object) | ≤ 0.5 cm, ≤ 2 deg | 2 deg → AUC 0.997; 1 cm → 0.966; 3 cm → MP 0.63; 10 deg → MP 0.68 |
| Slot-0 spin (symmetric object) | ≤ 5 deg, else catastrophic | cup-anchor spin 10 deg → AUC 0.714, MP 0.40; 90 deg → AUC 0.195, MP 0 (on those episodes) |
| Per-frame noise after smoothing | ≤ 0.5 cm/axis, ≤ 2 deg | 0.5 cm/axis with anchor exact → AUC 0.984; 1 cm/axis with anchor exact → 0.914 |
| Lag | 0 frames (zero-phase) | 1 frame → −0.010 AUC; 3 frames → −0.067 |
| Scale | ≤ 2-3 % | 3 % → −0.002; 10 % → −0.077 and MP 0.90 |
| Non-anchor body rotation | ≤ 10-15 deg | 15 deg → −0.039 AUC (all episodes) / −0.060 (multi-object only); 30 deg is a hard MP cliff |
| Lost or frozen frames | none for the moving object | drop at onset ≈ static predictor (AUC 0.55, MP 0.05) |
| Policy `e_track` | ≤ 1-1.5 cm mean, no flings | unknown on our data; it is the largest unmeasured term (R5) |
| Reference total (`e_ref`) | ≈ 02's combined "careful stereo" case | AUC 0.889, SP 1.00, MP 0.97, RPE 0.98, MPPE 1.71 [M] |

Static predictor for scale: AUC 0.446, SP 0.45, MP 0.00, RPE 10.87, MPPE 9.31 [M]. A policy that flings
the object scores worse than this. "Do no harm" is therefore a real objective.

### 0.3 P0 risks: settle these before choosing between architectures

Ordered by expected score swing × probability [E/H]. None of them distinguishes the architectures; all
of them can sink every architecture.

1. **Timing contract (06).** If evaluator rows are mapped to source frames wrongly (for example 2× time
   under `motion_speed 0.5`), the lag is up to half an episode on every board. GT-free test: synthesise
   an evaluator-format export from public GT resampled exactly as FlashCHORD would. Pack it with the kit
   and score it; it must give AUC 1, SP 1, MP 1, RPE 0, MPPE 0. CPU only.
2. **Object frame convention (07), above all for the wooden spoon** (in 10/20 eval episodes, no public
   scan) [V 02/track3]. A constant body-frame offset O:
   - for slot 0, scores every later displacement d with error 2 sin(θ_O/2)|d| [H 05];
   - for slots > 0, adds a constant ||O x − x|| on every frame [H 05].

   Spoon-only episodes 35-37 have the spoon as slot 0. The public URDFs and GLBs point to a canonical
   frame: centroid origin, principal axes in ascending variance [V 02, inference].
   - Signs: right-handedness fixes y once x and z are fixed. x (thickness, bowl concavity) and z (long
     axis, bowl end vs handle) have strong third moments for a spoon [H]. So a rule "sign = positive
     surface skew" (02 saw positive skew on pot +z/+x and lid +x) would make the spoon frame inferable.
   - This must be confirmed on all 10 public scans (07) and asked of the organisers. A wrong z sign
     (180 deg flip) zeroes AUC and MP for that object.
3. **Unobservable spin of rotationally symmetric objects.**
   - Cups are slot 0 in 5/20 public episodes, and their principal moments differ by < 1 % about the long
     axis [V 02]. The scan frame's x/y axes are then set by tiny asymmetries in the organisers' scan.
   - Implication [H]: without the scan, or without visible texture registered to it, the frame-0 spin of
     a symmetric anchor is a lottery for every team. It rotates the whole scene about the cup axis.
   - The lid has the same problem as a non-anchor: a 90 deg spin gives MP 0 on episodes 0 and 2 [M].
   - So the answer to "may public scans be used for tracking?" is worth tenths of AUC on cup-anchor and
     lid episodes, *if* the cups and lid carry visible texture or features [H]. Measure first (R1).
4. **Catastrophic loss or fling** (perception loses the object, or the policy drops or throws it). This
   is the largest single-term swing in 02 (−0.45 AUC on the episode). Robust re-acquisition and
   no-fling training beat sub-centimetre refinement.
5. **Policy tracking error of unknown size.** It shares the MP-SR margin. One calibration rung (R5)
   measures it before the team splits effort between perception and transfer.
6. **Multi-object support.** The baseline ego path is single-object end to end [V 01 A.0, B.2]. A missing
   slot-1 object is not a degradation: the submission is incomplete.

### 0.4 Unknowns about the target itself

- How the six boards combine into "track winner" is unpublished [V track3]. Optimise a balanced profile.
  - MP-SR is the most discriminating board (hard per-object cliffs).
  - SP-SR saturates easily (static predictor 0.45; any decent tracker 0.9-1.0).
  - RPE is 0 for everyone on the four single-object eval episodes (35-38).
  - MPPE is linear and has no dead zone.
  - CD-O is a separate, cheap sub-pipeline and a plausible early first place.
- The sponsor runs a further held-out evaluation after close [V track3]. Choosing final picks by public
  leaderboard (LB) score overfits 20 episodes, so one of the two final picks should be the
  best-on-local-validation pipeline (§8).

### 0.5 GT policy for this note (user constraint + AGENTS integrity rules)

- Public mocap is used only by the scorer and evaluator-side diagnostics, after inference. No pipeline
  stage reads GT, and no parameter is fitted to GT except through choosing between whole configurations
  by validation score.
- Two GT uses are *not* "scoring only" and are marked as user decisions: (a) the oracle run "policy
  trained on the GT object reference" (R6); (b) any supervised fine-tune on public GT (Arch-3 option).
  Both consume the validation set and need leave-task-out folds.
- Validation hygiene [H]: split the 20 public episodes into dev (14) and a frozen holdout (6), stratified
  by task family (for example one each of Pan_Solo, Pot_with_lid, Cup_In_Dish_Rack, Water_Can,
  Planter_Stand, Dust_Brush). The holdout is scored only for final-pick decisions.

---------------------------------------------------------------------------------------------------

## 1. Shared spine: built once, used by every architecture, never a candidate on its own

| ID | Module | In -> Out | Why it is shared |
|---|---|---|---|
| S0 | Data contract and timing | Raw videos, `capture_time`, calibration -> frames keyed by `frame_index`, measured fps, colour rotated 180 deg with K transformed, rectification maps for the mono pair, colour↔mono time-offset estimate | Associate frames by `frame_index`, never by nominal time [V 02]. Use measured fps, not 30 [V 01 B.2]. The timing round-trip test of §0.3-1 becomes a regression test. |
| S1 | Local evaluation harness | References and evaluator exports -> kit-scorer metrics per episode, object and window, plus `e_ref` / `e_track` / `e_score` and a failure taxonomy (lost, flipped, flung, drifted, lagged, frame offset) | GT is read only in the scorer process (separate directory and permissions). Every ablation reports the five pose metrics, CD-O, GPU-h and failures together. |
| S2 | Object frame and asset module | Mesh -> canonical frame (07 rule), watertight collision mesh, URDF mass from volume × density class, symmetry descriptor (continuous axis or discrete order), CoACD preview (hull/mesh volume ratio, slot/opening fill check) | The same canonical mesh feeds tracking, sim and CD-O. Frame offsets are e_frame, the most dangerous constant error (§0.3-2). |
| S3 | Compliance and reproducibility | Checkpoint config -> diff against the recipe for every physics field (scene, sim, collision, embodiment, `motion_speed`), licence register, digests, pinned upstreams, content-hash cache | Only training-side config and our assets may differ [V 04 §8, 05 §0]. Replaces the baseline's cache-by-existence `_step`, which silently reuses stale outputs [V 01 A.0]. |
| S4 | GPU fleet and job queue | Containers, rented hosts -> serialized heavy jobs, run manifests | FlashCHORD needs ≥ 46 GB free at 4,096 worlds and driver ≥ 580 [V track3]. cuSFM rejects Blackwell [V 01 E]. Pick Ada/Hopper/Ampere 48-80 GB. |
| S5 | Multi-object plumbing (B ≤ 2) | Per-object masks, tracks, meshes -> multi-body parquet and URDF list | The FlashCHORD format supports B > 1; the ego loader and bundle do not [V 01 C.11, B.2]. |

Physics freeze (all architectures) [V 04 §8, H compliance]. Never change:
- friction, damping, object-scale range, substeps, solver settings, collision policy, CoACD parameters;
- `motion_speed` (default 0.5);
- the stiff embodiment, unless the organisers approve it in writing.

We change only these:
- the reference parquet;
- our assets (meshes, URDF inertials, support USDA from the reconstructed table);
- training-side config and code (objectives, curriculum, reset, termination, learner);
- per-episode seeds and checkpoint selection.

---------------------------------------------------------------------------------------------------

## 2. Arch-1 "SMH": Stereo-Modular perception + repaired-Human reference + tuned FlashCHORD

**Bet:** `e_ref` is the dominant fixable term. A careful modular stereo stack plus a world-frame batch
smoother drives it to the "careful stereo" level of 02. The human-hand reference can be repaired enough
(de-penetration, contact relabelling) for FlashCHORD to track it. Closest to the organiser stack: lowest
conceptual risk, broadest integration effort.

### 2.1 Step dissection

Columns: "Add / Cut" is relative to the NVIDIA ego baseline (01). "Moves" lists the boards affected.
"Residual" is the expected error left after the step [E].

| # | Step | In -> Out | Chosen method (alternatives) | Add / Cut vs baseline | Moves | Residual |
|---|---|---|---|---|---|---|
| 1.1 | Rig conditioning | Raw streams -> rotated colour; rectified mono pair; fixed K; blur score per frame | Factory calibration incl. rational distortion. Rectification FOV chosen to keep the tabletop. Time offset from motion cross-correlation (Q2 in 03). | **Add:** rotation, factory K, sync check. **Cut:** AnyCalib, GeoCalib intrinsics, MoGe per-frame K and its median "stabilisation" [V 01 A.1] | Everything through scale and K | Removes focal-length and per-frame K inconsistency |
| 1.2 | Stereo depth | Rectified pair -> metric depth on mono-left + confidence + edge-band mask; reprojected to colour with hole mask | FoundationStereo. TAO weights [W] at 576×960 or tiled; NVlabs ViT-L [NC] if allowed. Alternatives: DEFOM-Stereo (MIT code; weight licence U), SGBM as sanity floor. MoGe-2 per-frame scale/shift fitted to stereo on static background, used only as a dense hole filler on colour. | **Add:** the stereo pair, never used by the baseline [V 01 A.2]. **Cut:** MoGe as the metric source | Scale, translation, anchor, camera translation | Scale ≤ 1-2 %. 1.5-6 mm per-pixel noise at 0.5-1 m [V 02 §3]. Systematic bias on the white pot/lid and on spoon edges: unmeasured (R2) |
| 1.3 | Segmentation and identity | Colour (+ mono-left) + object names -> per-object visible masks, score, identity confidence; hand masks | Grounding DINO / OWLv2 boxes on several frames (not just frame 0) -> SAM2.1-L video propagation forward and backward. Re-prompt when mask area/score collapses or the 3-D centroid jumps. SAM3.1 text/exemplar prompts if A1 licence resolves (MOSEv2 60.3 vs 47.9 J&F [V 03]). | **Add:** multi-object, multi-frame prompting, re-prompting, 3-D identity check. **Cut:** single DINO box at frame 0 [V 01 A.0] | Loss and identity swaps (all boards) | Identity swaps ~0 with 3-D gating [H]. Mask loss concentrated in grasp windows |
| 1.4 | Camera ego-motion + world | Mono pair + dynamic masks -> T_wc(t) with covariance, static background model, table plane, gravity = table normal | DROID-SLAM stereo [BSD] with mask-dilated weights, or cuVSLAM [custom]. Offline BA that adds the colour camera through factory extrinsics. RANSAC table plane; GeoCalib on rotated colour as a cross-check. World origin on the table under the slot-0 frame-0 position. | **Add:** stereo metric VO, masking, table-plane world. **Cut:** mono DROID with an unmasked MoGe ratio for scale [V 01 A.1]; thinnest-PCA "up" in the loader [V 01 B.2] | Common drift (AUC, MPPE, MP via rotational drift); sim gravity and support | ≤ 1 cm, ≤ 1 deg over 13 s [E]. Gravity tilt ≤ 1 deg if the table is level [H] |
| 1.5 | Object models | Masks, depth, poses -> per-object canonical mesh (S2) for tracking, sim and CD-O | Scans allowed: scans for tracking and sim, own meshes for CD-O. Scans not allowed: object-frame fusion of masked stereo depth along tracked poses (TSDF, or 2DGS via gsplat [Apache]) + generative completion (SAM3D [custom], TRELLIS.2 [MIT; nvdiffrast NC]) registered by Sim(3) to the fused partial. Metric scale from stereo. Two tracking↔mesh rounds. Spoon: pick generative vs parametric vs fused by multi-view silhouette + depth agreement. | **Add:** multi-view fusion, canonicalisation, completion selection. **Cut:** single-view SAM3D on frame 0 with a scale grid search against one MoGe frame [V 01 A.1 8a/8b] | CD-O directly; pose boards via e_frame and tracking quality; sim contact geometry | Scanned objects: e_frame ≈ 0. Own meshes: e_frame = canonicalisation noise (07) |
| 1.6 | 6-DoF tracking | RGB + depth + masks + mesh -> per-frame pose, 6×6 covariance, render score, K hypotheses | FoundationPose [NC]. Multi-frame, multi-hypothesis registration over the static prefix. Bidirectional tracking from several anchors. Colour view plus mono-left view (native depth). Occlusion-aware re-registration: IoU computed on the visible region minus hand masks, seeded by the smoother's prediction. Spin covariance inflated for symmetric objects. Alternatives: MegaPose [Apache] / GigaPose [MIT] (OSI path; HO-Cap ADD 67.1 vs FP 89.3 [V 03]); GoTrack [NC, RGB-only]; depth-ICP. | **Add:** prefix registration, bidirectional, second view, occlusion-aware IoU, covariance output. **Cut:** frame-0 one-shot registration; full-silhouette IoU<0.3 re-registration that fires during grasps [V 01 A.4-3]; camera-frame EKF; gsplat refinement that bypasses the smoother [V 01 A.1 8d] | Per-frame noise (AUC, MPPE, MP), loss, non-anchor orientation | 0.3-0.7 cm/axis, 1-3 deg raw [E]. Flips on the white pot/lid under grasp: unmeasured (R3) |
| 1.7 | 3-D hands | Colour + mono L/R + depth -> MANO per frame with confidence; grasp segments; hand-object contact sets | HaMeR [MIT + MANO] per view, then a multi-view MANO fit to 2-D keypoints and stereo hand-surface depth, then temporal smoothing/infilling. Contact optimisation against the object SDF (penetration ≤ 3 mm [V 04 V2P]; object-frame contact aggregation, C2Dex [V 04]). WiLoR [NC] only if licence allows. | **Add:** multi-view + stereo hand depth (HOT3D two-view −29 % MPKE [V 03]), contact optimisation. **Cut:** single-view translation-only depth shift to MoGe [V 01 A.1 9-14] | Indirect: e_track (action prior, contacts) and occlusion bridging | Wrist ~1-2 cm, contacts noisy [E] |
| 1.8 | **World-frame batch smoother (keystone)** | Tracker poses + covariances + camera + hands + table -> object trajectories in world with per-frame confidence, segment labels and rest poses | Factor graph (gtsam [BSD]) with these factors: robust FP measurements (Cauchy/Huber, anisotropic); static-when-untouched segments with one pose variable each (exactly constant); support factor (rest pose on the table plane, snapped to one of the mesh's stable poses, i.e. yaw + discrete pose); SE(3) smoothness while held; hand-attachment factor in low-visibility grasp windows; soft inter-object non-penetration. Batch solve, so zero lag. Slot-0 frame-0 anchor = static-prefix segment estimate. Segment detection gated by hand proximity and motion, iterated. | **Add:** everything in this row. **Cut:** camera-frame EKF/RTS [V 01 A.1 8d] | AUC (noise, exact statics), MP (bias, bridging), RPE (inter-object consistency), MPPE, anchor | Anchor 0.3-0.5 cm / 1-2 deg (asymmetric objects) [E]. Static objects ~0 error. Noise ≤ 0.5 cm/axis |
| 1.9 | Reference assembly | Object trajectories + hands -> FlashCHORD parquet (B ≤ 2, true fps), URDFs, support USDA | Official IK retargeter with `--smooth_reference --surface_project --adaptive_offset` on and tuned [V 01 B.3]. Object-anchored hand during grasp segments (robust median relative grasp [H 04 idea 4]). Contact relabel: object-frame aggregation, motion gate, minimum duration, SPIDER-style drift filter [V 04]. Support prims from the table plane (horizontal) instead of still-run disks. Frame-0 validity: objects on support, no penetration, fingers outside objects. | **Add:** all repair flags on, relabel, table support, frame-0 validity. **Cut:** 30 fps constant, single body, still-run supports, 0.3 kg for every object [V 01 B.2-B.5] | e_track (penetration, contacts, supports), t=0 behaviour | Penetration ≤ 3-5 mm; contact precision unknown |
| 1.10 | Reference QA (GT-free gates) | Parquet + assets -> pass/fail per window + repair requests | Physical replay at VOC 0 (`replay=physical`) [V 05]. Settle test of rest poses (object alone, 1 s). Penetration and contact statistics. CoACD preview. Failing windows go back to 1.8/1.9. | **Add:** all (baseline has no QA) | Catastrophes before RL is paid for | n/a |
| 1.11 | Policy training | Parquet + assets -> FlashSAC checkpoints (2-3 seeds/episode) | FlashCHORD Sharpa FlashSAC recipe plus training-side changes [V allowed: only `evaluation/{__init__,harness,metrics,rollout}.py` are digested]: (a) evaluation-matched resets (frame 0 earlier, finger openness → 1, VOC decay 0 in late stages); (b) object keypoints scaled to object size instead of ±1 m, with the rotation term about a detected symmetry axis down-weighted [H 04 idea 3]; (c) contact robustness (CWS β 0.1→0.3, force-closure blend when label confidence is low) [H 04 idea 2]; (d) relaxed-termination tail so the policy learns to recover, since evaluation has no terminations [H]; (e) replay flush when VOC reaches 0 [H 04]. | **Add:** (a)-(e), seeds. **Cut:** nothing in eval/physics | e_track: AUC, MP, SP | Unknown (R5) |
| 1.12 | Selection + packing | Checkpoints -> official evaluator exports -> packed CSV + digests | GT-free choice among seeds by in-sim metrics against our reference, kept only if validated (R9 Spearman ≥ 0.5). S3 compliance diff before packing. | **Add:** selection, compliance gate | All | — |
| 1.13 | CD-O export | Canonical meshes -> mesh Parquet | From 1.5 (own meshes only, per the FAQ) | **Cut:** single-view SAM3D | CD-O | Unknown; validate against public scans with the kit CD-O code (R0d) |

### 2.2 Step boundaries: what must cross, consistency checks, feedback loops

Information and uncertainty that must flow across each boundary (the baseline passes only point
estimates):
- **1.1→1.2/1.3:** valid-FOV mask, colour↔mono time offset, and per-frame blur/exposure score. Blurred
  frames get lower weight in every later residual.
- **1.2→all:** depth plus per-pixel confidence (left-right consistency, cost entropy) and an *edge band*
  (2-3 px fattening zone at object boundaries). Trackers and fusion ignore the edge band; this is the
  thin-spoon failure mode [H 03 §4]. Reprojected holes are flagged, never zero-filled.
- **1.3→1.6/1.8:** visible mask, mask score, identity confidence and *occlusion fraction* (visible ÷
  amodal; the amodal mask is rendered from the tracked pose, which forms loop L2).
- **1.4→1.8/1.5:** T_wc with covariance, a per-frame static-scene residual (frames with a high residual
  are marked unreliable), and the table plane with its uncertainty.
- **1.5→1.6/sim/CD-O:** mesh in the canonical frame, scale uncertainty, symmetry descriptor, CoACD preview
  metrics.
- **1.6→1.8:**
  - pose with an *anisotropic* covariance: depth axis and spin about a symmetry axis are inflated;
  - render score;
  - up to K pose hypotheses when the score landscape is multi-modal (flips);
  - re-registration events.

  A unimodal smoother cannot repair a confident flip. It must see the alternatives [H].
- **1.7↔1.8:** grasp segments (which hand holds which object, when), relative hand-object pose, and
  confidence. These feed the smoother's hand-attachment and segment gating.
- **1.8→1.9/1.11:** trajectory, per-frame confidence, segment labels and stable rest poses.
  - Proposed new interface [H]: pass per-frame confidence into the reward, down-weighting the object term
    in low-confidence windows (bridged occlusions, symmetric spin), so the policy does not chase
    reference noise.

GT-free consistency checks:
- **C1 drift meter:** objects that are untouched (hands far) must be static in the world frame. Their
  apparent motion equals camera error plus tracker error, measured without GT. 03 Q7 makes the same
  observation; here it becomes a gate.
- **C2 size consistency:** mesh extents vs stereo extents in every frame where the object is ≥ 50 %
  visible. The same identity must have the same size across episodes.
- **C3 forward/backward and colour/mono-left tracking agreement:** disagreement marks ambiguous windows.
- **C4 gravity:** table normal vs GeoCalib vs the stable rest poses of untouched objects.
- **C5 contact causality:** an object may move only while a hand is within ~2 cm of it. This catches
  phantom motion (tracker noise) and missed grasps.
- **C6 physics:** settle test, physical replay at VOC 0, penetration depth.
- **C7 timing round-trip** (S0) and per-episode row counts.

Feedback loops (each bounded to 2-3 iterations):
- **L1 mesh ↔ tracker** (BundleSDF-style alternation).
- **L2 smoother → tracker:** re-initialise on lost frames from the smoother's prediction; amodal mask
  for occlusion fraction.
- **L3 smoother ↔ hands:** grasp segments gate attachment; object poses refine hand contacts.
- **L4 reference QA → smoother/assembly:** failing replay windows trigger repair.
- **L5 seeds → selection:** only if the proxy is validated.

### 2.3 Error-budget mapping (Arch-1 expected profile)

| Error term | Owning steps | Expected residual [E] | Cost on the boards (02 [M]) |
|---|---|---|---|
| Scale | 1.2 | ≤ 2 % | ≤ 0.002 AUC. For comparison, the baseline's MoGe error is 8-16 % [V 03]; 10 % alone costs −0.077 AUC and MP 0.90 [M] |
| Common drift | 1.4, 1.8 | ≤ 1 cm | ~0 |
| Anchor, asymmetric slot 0 | 1.6, 1.8 | 0.3-0.5 cm, 1-2 deg | ≤ 0.01-0.03 AUC |
| Anchor, symmetric slot 0 (cups) | 1.5, 1.6 | Bimodal: ~0 with scan + texture; uniform without | 0 vs ~0.5-0.8 AUC and MP→0 on those episodes |
| Per-frame noise | 1.2, 1.6, 1.8 | ≤ 0.5 cm/axis, ≤ 2 deg | ~0.02 AUC |
| Lost/flipped windows | 1.3, 1.6, 1.8 | ≤ 2-5 % of moving frames | 0.01-0.05 AUC; MP risk where loss exceeds ~30 % of an episode |
| Non-anchor orientation | 1.6 | ≤ 10 deg | ≤ 0.02 AUC |
| **Reference total `e_ref`** | | ≈ 02 combined case A | AUC ~0.85-0.9, MP ~0.9 (excluding symmetric-spin episodes) |
| Policy `e_track` | 1.9-1.11 | Unknown; CHORD clean-reference level is ~1-2 cm | Plausibly −0.05 to −0.2 AUC, −0.1 to −0.5 MP-SR [E]; widest uncertainty |

End-to-end planning range [E, not a prediction]: AUC 0.70-0.85, SP-SR 0.85-1.0, MP-SR 0.3-0.75,
RPE 1.5-3 cm, MPPE 2-4 cm. CD-O depends on whether scans can serve as tracking priors; CD-O itself is
always from our own meshes.

### 2.4 Red team: Arch-1

Top failure modes:
1. **The hand branch is the weak link.** Ego MANO under grasp occlusion gives penetrating or misplaced
   fingers and wrong contact labels. The CWS reward (weight 10) then teaches the wrong contacts, which
   leads to drops: catastrophic on MP and AUC. Published evidence that reference consistency decides
   success:
   - Regrind: IK+RL 0-3 % vs interaction-mesh retargeting ~99 % [V 04];
   - V2P-Manip: 0 % without geometric constraints [V 04].

   Our repair flags are lighter than either fix.
2. **Multi-modal tracker errors on the white pot/lid** (textureless, symmetric lid) during grasps. If
   the tracker hands over only one hypothesis, the smoother averages a flip into a wrong pose.
3. **Symmetric spin of cups as slot 0** is unfixable without scans plus texture. This is common to all
   architectures, but Arch-1 has no physics or whole-clip mechanism to disambiguate it.
4. **Domain shifts on unusual inputs.** FoundationPose and FoundationStereo on greyscale, strongly
   distorted, rectified inputs: FoundationStereo is trained on RGB [V 01 E.1], and greyscale FP is
   untested [U]. The colour/mono sync is also unverified [U 03].
5. **Over-eager static clamp.** If segment detection labels a slowly moving held object "static", it
   freezes it, which equals a drop. The clamp must be conservative: hands far *and* motion small.
6. **Integration breadth.** About 12 models in 6+ containers, each needing tuning. Calendar slip is the
   most likely way this architecture loses.

Single experiment that would kill it as the *leading* architecture:
- The hand-source A/B, rungs R4 (physical replay at VOC 0) + R7 (equal-budget RL).
- Arch-1's repaired human reference vs Arch-2's synthesised grasps, with the *same* object reference, on
  6 public episodes spanning task families.
- If Arch-2 wins `e_track` / `e_score` on ≥ 4/6, Arch-1's transfer half is dead (its perception
  survives).
- Separately, if R3 shows Arch-1 `e_ref` AUC < 0.8 on asymmetric scanned objects, the perception thesis
  itself is in trouble.

Licence exposure: **HIGH.**
- Non-commercial: FoundationPose code (weights under NGC Model EULA, unread [U]); NVlabs
  FoundationStereo (or TAO weights [W]); nvdiffrast (inside FP, BundleSDF, TRELLIS); WiLoR (avoid);
  MANO (required by the official retargeter [V 01 B]); BundleSDF if used for meshes.
- OSI swap ladder, each step with an accuracy cost to measure in R3: MegaPose/own PyTorch3D
  render-and-compare; DEFOM/SGBM; gsplat fusion; HaMeR+MANO still needs MANO.
- The organisers' own baseline uses FP + MANO + SAM3D [V 01], which suggests they tolerate these.
  Unconfirmed: ask (Q-L1).

Compute and calendar [E]:
- Reconstruction 0.5-1.5 GPU-h per episode × 40 episodes × 3-4 iterations ≈ 60-240 GPU-h.
- Policies 2-4 GPU-h × 2-3 seeds × (20 eval + 8-20 public) × 3-4 cycles ≈ 300-900 GPU-h.
- At $1-2.5/GPU-h: ~$0.4-3k.
- Person-time: ~10-12 person-weeks. Perception v1 by the end of week 2, first full eval submission in
  week 3.

Unconfirmed-rule dependencies:
- Scans as tracking priors (high: spin, frame convention, sizes).
- URDF mass (medium).
- Non-OSI code (high).
- Regenerating support USDA from our table plane (low-medium; it is a reconstruction output in the
  baseline too).

---------------------------------------------------------------------------------------------------

## 3. Arch-2 "OFP": Object-First perception + Physics-verified robot reference (no 3-D human hands)

**Bet:** once perception is stereo-grade, `e_track` dominates. The cheapest way to cut it is to hand
FlashCHORD a robot reference that is executable *by construction*:
- grasps synthesised in Sharpa space on our mesh;
- contacts exact;
- every held window checked or optimised in the evaluator's own physics before RL.

The object reference stays the perceived trajectory. Physics is never allowed to overwrite well-observed
object motion.

Facts this relies on [V 05 §0]:
- FlashCHORD never reads MANO fields, so a robot-space hand reference is valid input.
- The hand reference acts only as action prior plus contact source and is never scored.
- Physical replay at VOC 0 is a near-free probe.
- FlashSAC has a BC term and replay preloading (`behavior_cloning_coefficient`, `load_replay_path`)
  [V 04 §8; replay format U].

### 3.1 Step dissection

Steps 2.1-2.6 reuse Arch-1 steps 1.1-1.6 and 1.8 (object branch, smoother, anchor) unchanged. The
person-time saved by dropping 1.7 (3-D hands) goes to 2.8-2.11.

| # | Step | In -> Out | Chosen method (alternatives) | Add / Cut vs baseline | Moves | Residual |
|---|---|---|---|---|---|---|
| 2.1-2.6 | Object branch | As Arch-1 1.1-1.6 + 1.8 | As Arch-1 | As Arch-1 | `e_ref` | As Arch-1 |
| 2.7 | 2-D hand cues | Colour + masks -> hand masks/boxes, handedness, 2-D wrist keypoints, optional stereo wrist depth | Lightweight detector + SAM2 hand masks; 2-D keypoints from an OSI model if available. No MANO. | **Cut:** WiLoR/HaMeR/Dyn-HaMR/ViPE 3-D hands, MANO, align_hands [V 01 A.1] | Segmentation accuracy only | — |
| 2.8 | Interaction segmentation | Object trajectories + hand cues -> per-object segments {rest, held-L, held-R, bimanual, tool-contact, pushed} with confidence and timing | Rules on object kinematics (leaves support, speed), hand-mask adjacency, stereo hand-object depth gap. Optional VLM script (DexImit uses Qwen3-VL [V 05]). | **Add:** all | e_track through timing (late grasp = lag/drop) | Segment-boundary error ≤ 2-3 frames [E] |
| 2.9 | Grasp synthesis | Mesh + held segment + approach side -> ranked Sharpa grasps G per segment | GPU-batched sampling in Newton: wrist poses around surface normals on the observed hand side, finger closure to contact. Each candidate is tested *in the evaluator scene config* at VOC 0 against the segment's own accelerations and rotations (e.g. the 180 deg pot flips in episodes 26/27/43). Rank by hold success, then by similarity to a 3-D human hand if one exists (DexImit ranking [V 05]). Alternatives: force-closure optimisation (DexGraspNet-style; licence U); learned grasp generators. | **Add:** all | e_track, catastrophes (drops) | Hold success per segment: measure in R4 |
| 2.10 | Robot reference synthesis | T_obj(t), G, segments -> wrist(t), fingers(t) for both hands, exact contacts (points, normals, part ids), parked idle hand | Wrist(t) = T_obj(t)·G during holds; min-jerk approach/retreat; finger closure ramps aligned with segment boundaries; idle hand parked away from static objects (protects MP-SR on the rack/rest object). | **Cut:** IK retargeting of MANO (kept only as fallback), MANO-proximity contact labels [V 01 B.2] | e_track: CWS reward becomes reliable | Zero penetration by construction |
| 2.11 | Physics-in-the-loop repair | Robot reference + perceived object + confidence -> executed robot trajectory + executed contacts + per-window feasibility | Sampling MPC with annealed covariance and virtual contact guidance (SPIDER/DIAL-MPC idea [V 04]). **Own Apache-2.0 re-implementation**, because SPIDER is CC BY-NC [V 04]. Runs in Newton/MuJoCo-Warp with the frozen scene config and 0.5× playback timing. Cost = confidence-weighted perceived-object error + contact stickiness early + effort. Only low-confidence (occluded) windows may take the executed object instead of the perceived one, and only if the gain is gated (C-lite of 05). | **Add:** all | e_track (feasibility), occlusion fill | Infeasible windows found before RL |
| 2.12 | RL | Executed reference -> checkpoints | FlashCHORD with residuals around the executed robot reference. CWS kept at weight 10, since contacts are exact. Score-aligned keypoints, evaluation-matched resets, relaxed-termination tail (as Arch-1 1.11). Optional BC warm start from the executed rollout through the BC term and replay preload, then a shorter budget. | **Add:** BC warm start | e_track; GPU-h | Unknown (R7) |
| 2.13 | Selection, packing, CD-O | As Arch-1 1.12-1.13 | | | | |

### 3.2 Step boundaries

New information that has to cross:
- **2.8→2.9:** segment *hypotheses*, not one segmentation. The hand that grasps and the grasp onset frame
  are the most error-prone cues, so 2.9 receives 1-3 alternatives scored by confidence and keeps the
  one whose replay works.
- **2.9→2.6 (new feedback into perception) [H]:** "No grasp can produce this perceived rotation sequence"
  is evidence that the perceived rotation is wrong (a flip or symmetric-spin hypothesis). Physics becomes
  a perception consistency check (loop L6). Example: a pot "rotating" 180 deg while no hand touches it is
  impossible.
- **2.11→2.12:** per-window feasibility and MPC residual. Windows the MPC cannot execute get lower
  object-reward weight or a widened tolerance, so RL does not spend budget chasing the impossible.
- **2.11→2.6:** executed-object fills only in windows where visibility is < 50 % and the smoother's
  covariance is large. Every fill is logged, and its share of `e_ref` is scored separately on public
  episodes.

GT-free checks:
- hold success at VOC 0 per segment;
- slip distance in the object frame during holds;
- contact-set stability;
- the MPC residual distribution;
- the share of the episode covered by synthesised grasps vs fallback IK.

### 3.3 Error-budget mapping

- `e_ref`: identical to Arch-1 (same object branch).
- `e_track` [H]: expected lower than Arch-1 on prehensile segments, because there is no penetration, no
  missing contacts and no wrong handedness. CHORD reports force-closure-style guidance outperforming
  corrupted wrench guidance [V 04/05], and the reference-repair literature shows large swings (Regrind,
  V2P, C2Dex [V 04]). Expected equal or worse on tool-contact and placement segments (sweeping,
  lid-on-pot, rack insertion, planter assembly), where a fixed grasp may not generate the needed wrench.
- Catastrophes: 2.9's hold test filters drop-prone grasps before training, which most protects MP-SR
  and SP-SR [H].
- Planning range [E]: as Arch-1 for `e_ref`. If R7 confirms the bet, MP-SR could gain +0.1 to +0.3
  over Arch-1 on prehensile tasks. Coverage risk could lose that on tool tasks.

### 3.4 Red team: Arch-2

Top failure modes:
1. **Coverage of non-prehensile and tool phases.** The public task families include Dust_Brush,
   Brush_Dishrack, Dustpan_Solo (sweeping), Pot_with_lid (lid placement), Cup_In_Dish_Rack (slot
   insertion), Cup_Stack and Planter_Stand (assembly). Eval spoon tasks are unknown (stirring or
   scooping would be prehensile and fine). A per-segment static grasp cannot regrasp or slide in-hand;
   the MPC must discover those, which is the expensive, unreliable part.
2. **Grasp-induced bias.** A robot grasp unlike the human's can make the perceived object orientation
   unreachable or collision-bound (cup into rack). The hold test at VOC 0 catches some cases, not all.
3. **Segmentation errors.** A late grasp onset makes the object lag behind the reference until the hand
   arrives (lag: 3 frames costs −0.067 AUC [M]). A wrong hand means an awkward reach.
4. **Engineering and calendar.** GPU-batched grasp sampling plus a sampling MPC in Newton is about 2-3
   person-weeks of new code; the SPIDER code cannot be vendored (NC). EgoEngine: MPC alone 0.20 vs RL
   0.90 on noisy ego data [V 04]. That is why the MPC is a reference generator here, never the final
   controller.
5. **Physics-biased fills.** Sim friction (1.0) and our URDF masses can make "feasible" differ from
   "what happened". Fills must be gated and scored separately.
6. **No gain on `e_ref`.** If perception is the bottleneck (R3), Arch-2 changes nothing on the boards.

Single experiment that would kill it:
- R4 + R7 on 6 public episodes: Pan_Solo, Pot_with_lid, Cup_In_Dish_Rack, Water_Can_Blue_Cup,
  Planter_Stand, Dust_Brush.
- Arch-2 is killed as primary if it is not ≥ Arch-1 on `e_track` and `e_score` on ≥ 4/6, or if its hold
  test fails on > 50 % of held segments outside tool tasks.
- If it wins only on prehensile families, keep it as a per-family option. The family is chosen by a
  GT-free rule, for example "all segments pass the hold test", decided once on dev episodes.

Licence exposure: **MEDIUM.**
- Removes MANO, WiLoR/HaMeR and the IK retargeter dependency on MANO.
- The MPC is our own code; Newton and MuJoCo-Warp are Apache [V 01 C].
- Remaining non-OSI parts are in perception only (FP, FS weights, nvdiffrast, SAM3 if used).
- This is the shortest route to an all-OSI-plus-weights stack if perception switches to
  MegaPose/own render-and-compare.

Compute and calendar [E]:
- Grasp search + MPC ≈ 0.1-0.5 GPU-h per episode. RL similar to Arch-1, possibly −30-50 % with a BC
  warm start (unverified).
- Person-time ≈ Arch-1 minus 3-D hands (−2 person-weeks) plus grasp/MPC (+3 person-weeks).
- Earliest decision point is R4, end of week 1 to mid week 2, if a 2-task grasp prototype exists.

Unconfirmed-rule dependencies:
- URDF mass/inertia and collision authoring (high: grasp and MPC results depend on them).
- Whether a synthesised, non-human hand reference is in the spirit of Track 3. It is not a scoring
  rule; FAQ says other embodiments are welcome [V track3]. Ask anyway for the Innovation narrative.
- Scans as tracking priors (as Arch-1).

---------------------------------------------------------------------------------------------------

## 4. Arch-3 "JCE": Joint whole-Clip estimation + cross-episode object library + Closed-loop EM

**Bet:** per-frame tracking plus late smoothing (Arch-1) leaves the expensive errors in place. The
expensive errors are:
- grasp occlusion windows;
- flips and symmetric ambiguity;
- mesh and frame errors that are consistent within an episode.

These need whole-clip, pixel-level evidence plus physics and cross-episode identity. Closing the loop
on the *rollout* (render the simulated object into the video, select or repair) attacks `e_score`
directly instead of `e_ref` and `e_track` separately. This is the highest theoretical ceiling and the
worst calendar fit.

### 4.1 Step dissection

| # | Step | In -> Out | Chosen method (alternatives) | Add / Cut vs baseline | Moves | Residual |
|---|---|---|---|---|---|---|
| 3.1 | Rig, depth, masks, camera | As Arch-1 1.1-1.4 | | | | |
| 3.2 | Cross-episode object library | All episodes (public + eval videos; no GT) containing an identity -> one canonical mesh per identity, with metric size, symmetry descriptor and mass | Per-episode object-frame partials (Arch-1 1.5) -> cross-episode Sim(3) registration + fusion -> generative completion only for never-observed regions -> canonicalised (S2). The spoon is built from 10 eval episodes instead of one view [H 05 I]. | **Add:** all. **Cut:** per-episode single-view meshes | CD-O (large for the spoon), e_frame, sim geometry, tracking ADD | Chamfer gain vs single-episode: measure (R10) |
| 3.3 | Initialisation | As Arch-1 1.6 (FP per frame), plus 3-D point tracks on the spoon where the mesh is weak (TAPIP3D [Apache, U] / Any4D [Apache]) [H 05 D] | | | | |
| 3.4 | **Joint whole-clip analysis-by-synthesis** | Images (3 cams), depth, masks, camera init, library meshes, hand cues -> camera refinement + per-object SE(3) splines + (optional) hand poses with posterior uncertainty | Differentiable render-and-compare over all frames and cameras: silhouettes with occlusion ordering from depth and hands, robust stereo-depth residual, dense feature/flow consistency (model-to-frame + frame-to-frame; GoTrack idea, own implementation, since GoTrack is NC [V 03]), contact in grasp segments, non-penetration (hand/object/table), support and stable rest, static-when-untouched, smoothness. A discrete mode search (particles or branches) over flips and symmetric spin, scored by whole-clip residual. Renderer PyTorch3D [BSD] or gsplat [Apache], not nvdiffrast [NC]. | **Add:** all. **Cut:** per-frame FP output as the final answer; camera-frame EKF; gsplat "simple" refinement in the camera-at-reference world [V 01 A.1 15] | Everything in `e_ref`, especially occlusion windows, flips, anchor | Gain over Arch-1 concentrated in ambiguous windows (R3-diag) |
| 3.5 | Physics-feasibility factor | Candidate trajectories -> per-window feasibility from replay/MPC (Arch-2 2.11 machinery) -> soft factor back into 3.4 | Impossible motions (object moving without contact, floating, interpenetrating) are pulled toward feasible ones unless the image evidence is strong | **Add** | `e_ref` catastrophes | — |
| 3.6 | Reference + transfer | Arch-1 (repaired human) or Arch-2 (object-first), whichever R7 picks | | | | |
| 3.7 | Policy variants | N per episode: seeds × reference variants (e.g. spin/flip modes the estimator could not resolve) | FlashCHORD as Arch-1 1.11 | **Add:** variants | e_track, catastrophes | — |
| 3.8 | **Closed-loop selection and repair (EM)** | Evaluator rollouts -> render the simulated object into the 3 cameras with our camera poses -> video-consistency score (masks, stereo depth, features) -> pick a variant per episode. Windows where all variants fail are split into *reference wrong* (rollout ≈ reference ≠ video) and *policy failed* (rollout ≠ reference), then 3.4 re-optimises the window or a short fine-tune runs. 1-2 iterations. | Selection is legal: a GT-free choice among genuine variants [V 05 H]. It is *not* leaderboard probing. | **Add:** all | `e_score` directly, all boards | Valid only if R9 Spearman ≥ 0.5 |
| 3.9 | CD-O | Library mesh per episode-object | | | CD-O | |

Optional, requires a user decision (conflicts with "GT only for scoring", and leaks validation): an
in-domain refiner fine-tune or a learned confidence model trained on public mocap under
leave-task-out folds [H 05 E].

### 4.2 Step boundaries

- **3.2↔3.4 (identity-level loop):** the library feeds the joint estimator a better mesh. The estimator's
  poses on every episode feed back better partials. Size and symmetry descriptors are shared across
  episodes; an identity whose size disagrees across episodes flags an association or scale error.
- **3.4 posterior → 3.7 variants:** unresolved discrete modes (spin, flip) are not collapsed; they
  become policy variants that 3.8 adjudicates against the video.
- **3.8 → 3.4 / 3.7:** the window-level diagnosis (reference wrong vs policy failed) is the key new
  signal. It tells the team which half to fix per episode without GT.
- Consistency checks: C1-C7 from Arch-1, plus
  - **C8** cross-camera reprojection consistency of the final trajectory;
  - **C9** cross-episode identity consistency (size, shape);
  - **C10** rollout-vs-video consistency.

### 4.3 Error-budget mapping

- `e_ref`: gains over Arch-1 only in windows where per-frame tracking is wrong *and* whole-clip context
  can fix it: occlusion, flips, spin made observable by features. From 02, losing the most-moving object
  after its first motion costs AUC 0.943 → about −0.06 [M]; a full flip window costs more. Upper bound
  of the gain over Arch-1 [E]: +0.02 to +0.1 AUC and up to +0.2 MP-SR, *if* R3-diag finds ≥ 25 % of
  Arch-1's `e_ref` in such windows.
- e_frame and CD-O: library meshes should cut CD-O most on the spoon and on objects with hidden faces.
  They cut the spoon's sim-geometry error too [H].
- `e_score`: closed-loop selection protects against catastrophic seeds and mode errors *if* the proxy
  correlates. Prior workspace experience with GT-free proxies was weak (rho ≤ 0.47 in an unrelated SLAM
  project [V 05 H]), so plan for it to fail.

### 4.4 Red team: Arch-3

Top failure modes:
1. **Calendar.** A multi-camera differentiable joint optimiser with discrete mode search, contact and
   physics factors is a research project. With ≤ 2 people and ≤ 3 weeks it is unlikely to beat a tuned
   FP + factor-graph smoother except in ambiguous windows.
2. **Little multi-view leverage.** The mono cameras sit ±37.5 mm from the colour camera (occluder at
   0.4 m, object at 0.55 m → ~14 px relative shift [H 05 B]). Extra cameras add little occlusion
   diversity; most gain must come from whole-clip priors, which Arch-1's smoother partly has.
3. **Proxy failure.** Video consistency suffers from camera error, mask error and the slot-0 alignment
   the scorer applies but the video does not see. If rho < 0.5, 3.8 is just extra GPU-h.
4. **Local minima and confident wrong modes.** Joint optimisation can converge to a self-consistent but
   wrong flip.
5. **EM cost.** Policy variants × iterations multiply RL GPU-h by 2-4×.
6. **Rule exposure.** Pooling other episodes' videos for an episode's mesh (library) is unconfirmed [H 05 Q2].

Single experiment that would kill it:
- **R3-diag**, on Arch-1 references for the dev episodes:
  - compute the share of `e_ref` (sum of ADD over frames) that sits in windows where per-frame tracking
    is wrong (> 3 cm or > 30 deg) *and* visibility < 50 % or a flip occurred;
  - if < 25 %, the joint estimator's ceiling is small, so kill 3.4.
- **R9:** Spearman(video consistency, mocap AUC) over ≥ 10 checkpoints. If < 0.5, kill 3.8.
- The library (3.2) is separable and survives either way if R10 shows ≥ 20 % Chamfer gain.

Licence exposure: **MEDIUM-HIGH.**
- Own renderer (PyTorch3D/gsplat) avoids nvdiffrast. Perception initialisation still uses FP and FS.
- 3-D point trackers vary: TAPIP3D Apache [U], SpatialTrackerV2/CoTracker custom [U 05].

Compute and calendar [E]:
- Joint optimisation 0.5-2 GPU-h per episode × iterations; EM policies 2-4× Arch-1.
- About +4-6 person-weeks over the shared spine. Probably not complete by 2026-11-04; harvest components.

Unconfirmed-rule dependencies:
- Cross-episode pooling (high for 3.2).
- Public-GT supervision (only if that option is chosen).
- Scans as priors (lower: the library partly substitutes, but not for the spin of textureless symmetric
  objects).

---------------------------------------------------------------------------------------------------

## 5. Arch-F (fallback) "BL+": organiser pipeline + minimum decisive fixes

Purpose: a guaranteed, legal, multi-object submission by the end of week 2, and the *control* for every
ablation. Not a contender for first place.

| # | Fix to the organiser HaMeR/WiLoR ego pipeline | Why (01) |
|---|---|---|
| F1 | Rotate colour 180 deg, factory K. MoGe receives only an FOV prior and assumes a centred principal point, so crop or pad to a centred principal point. | [V 01 D] |
| F2 | Stereo depth pre-filled into `<out>/depth/*.png` (16-bit inverse depth, rotated colour frame) and `intrinsics_stable.json`, so DROID scale, the FP scale search, FP tracking and hand alignment consume metric depth via cache-by-existence. | [H 01 E, "practical shortcut"]; verify the format on one episode |
| F3 | `--object_mesh` (scans if allowed, else SAM3D + stereo scale) + `--skip_object_scale_estimation` | [V 01 A.1 8b] |
| F4 | Object branch run once per object (separate SAM2 ids / runs); bundles merged; small loader patch for B = 2 | [V 01 A.0, B.2] |
| F5 | True fps in the loader/registry instead of 30 | [V 01 B.2] |
| F6 | Retargeter repair flags on; table-plane support instead of still-runs; `--no_ground_align` with a table-plane level | [V 01 B.1-B.5] |
| F7 | Default FlashCHORD recipe, 1 seed; only change: frame-0 resets earlier | [V 01 C.7] |

Compute: ~70-130 GPU-h for a first full submission [E track3]. Person-time ~1.5 person-weeks (P4 + P1
part-time).

Red team:
- The F2 shortcut may fail on format details.
- The camera-frame EKF and frame-0 one-shot registration remain.
- MANO hands stay noisy.
- The spoon stays a single-view hallucination.
- If F scores near the static predictor on public episodes, that is the signal to prioritise catastrophe
  fixes (loss, flings) before accuracy.

Licence: the same as the organiser baseline.

---------------------------------------------------------------------------------------------------

## 6. Comparison and ranking

### 6.1 Side by side

| | Arch-F BL+ | Arch-1 SMH | Arch-2 OFP | Arch-3 JCE |
|---|---|---|---|---|
| Error term it attacks | Gross bugs (scale, fps, single object) | `e_ref` (stagewise robustness) | `e_track` (executable reference) | `e_ref` ambiguity windows + `e_score` via closed loop |
| New code (person-weeks) [E] | ~1.5 | ~10-12 (incl. spine) | spine + ~3 (grasp/MPC), −2 (no 3-D hands) | spine + ~4-6 |
| GPU-h, dev + final [E] | 70-130 (one submission) | 400-1100 | 350-1000 (BC warm start may cut RL) | 700-2000 |
| P(complete and validated by 2026-11-04) [E] | 0.9 | 0.7 | 0.5 (as Arch-1 perception + OFP transfer) | 0.2 (full); 0.6 (library + selection only) |
| Licence exposure | High (baseline stack) | High | Medium | Medium-high |
| Worst rule dependency | Scans for tracking | Scans; NC code | URDF/physics assets | Cross-episode pooling |
| Planning profile [E] AUC / SP / MP / RPE cm / MPPE cm | 0.45-0.65 / 0.5-0.85 / 0-0.2 / 3-8 / 4-8 | 0.70-0.85 / 0.85-1.0 / 0.3-0.75 / 1.5-3 / 2-4 | Arch-1 ±: MP +0.1-0.3 on prehensile tasks if R7 confirms; possible loss on tool tasks | Arch-1 + 0.02-0.1 AUC if R3-diag ≥ 25 % |
| Kill experiment | — (control) | R4+R7 hand A/B (transfer half); R3 (perception) | R4+R7 on 6 task families | R3-diag (< 25 %), R9 (rho < 0.5) |

The profile row is for planning only. It comes from 02's idealised perturbations [M] combined with
CHORD's clean-reference policy numbers [V 04]. None of it was run on our data.

### 6.2 Ranking (maximum leaderboard accuracy, risk-adjusted)

1. **Arch-1 SMH is the base. It ranks first on expected value.**
   - Every one of its stages can be validated on public GT *without RL* (R2/R3, cheap).
   - It carries the spine all other architectures need.
   - Its main weakness (the human-hand reference) has a drop-in replacement (Arch-2's transfer half)
     that shares the object branch.
2. **Arch-2 OFP is the leading upgrade. It has the highest upside on MP-SR / SP-SR and the lowest licence
   exposure.**
   - It ranks second only because its value depends on one unmeasured fact (R5/R7: is `e_track` the
     dominant term on our data?) and it carries a task-coverage risk.
   - Expected final form: Arch-1 perception + Arch-2 transfer on task families that pass the GT-free hold
     test, with Arch-1 repaired hands elsewhere.
3. **Arch-3 JCE is not finishable as a whole. Harvest its components:**
   - the cross-episode library (3.2) for CD-O and the spoon, if pooling is allowed;
   - the discrete mode search for flips and spin;
   - rollout-vs-video selection (3.8) only if R9 passes.

   Do not staff the full joint optimiser unless R3-diag says ambiguity windows hold ≥ 25 % of `e_ref`.
- **Arch-F BL+ is built first regardless.** It is the control, packer test and safety net.

Why not rank Arch-2 first? The literature evidence for reference repair is strong (Regrind, V2P, C2Dex
[V 04]). But none of those studies had an *ego-stereo object reference* plus FlashCHORD's CWS reward, and
Arch-1 already includes the cheap part of reference repair (flags on, relabelling, frame-0 validity). The
marginal gain of synthesised grasps over *repaired* human hands is the unmeasured quantity. One
experiment (R4, ~1-3 GPU-h) can flip the ranking.

### 6.3 Licence exposure matrix (components that drive prize eligibility)

[V 03] unless marked. Under the template clause in the header, non-OSI *code* is the risk; non-OSI
*weights* are exempt from the licence grant [U].

| Component | Licence | F | 1 | 2 | 3 | OSI substitute (accuracy cost to measure) |
|---|---|---|---|---|---|---|
| FoundationPose code (+ NGC weights: Model EULA, unread [U]) | NVIDIA Source Code License, NC | ● | ● | ● | ○ init | MegaPose [Apache] / GigaPose [MIT] / own PyTorch3D render-and-compare (HO-Cap ADD 89.3 → 67.1 for MegaPose) |
| nvdiffrast (inside FP, BundleSDF, TRELLIS) | NC | ● | ● | ● | ✕ (own renderer) | PyTorch3D [BSD], gsplat [Apache] |
| FoundationStereo NVlabs / TAO | NC / NVIDIA Open Model License (weights) | TAO | TAO or NC | TAO | TAO | DEFOM [MIT code; weights U], SGBM |
| MANO (needed by the official retargeter) | MPI research-only | ● | ● | ✕ | optional | MHR [Apache] + own retarget; or Arch-2 (no human hand model) |
| WiLoR / HaWoR | CC BY-NC-ND | ● (baseline detector) | ✕ (use HaMeR) | ✕ | ✕ | HaMeR [MIT + MANO] |
| SAM2.1 | Apache | ● | ● | ● | ● | — |
| SAM3/3.1, SAM3D | SAM License (custom; commercial OK, not OSI) | SAM3D | optional | optional | optional | SAM2.1, TRELLIS.2 [MIT] |
| DROID-SLAM / cuVSLAM | BSD / NVIDIA Community (closed core) | DROID mono | DROID stereo or cuVSLAM | same | same | DROID stereo |
| SPIDER code | CC BY-NC | — | — | re-implement | re-implement | own code |
| gtsam, gsplat, PyTorch3D, Newton, MuJoCo-Warp, FlashCHORD | OSI | | ● | ● | ● | — |

Implication [H]: an all-OSI-code stack is possible, at a measurable accuracy cost:
- Arch-2 transfer (no MANO);
- MegaPose or own render-and-compare instead of FoundationPose;
- TAO FoundationStereo weights + own inference code (the weights may be exempt);
- SAM2.1;
- DROID stereo;
- gsplat/PyTorch3D.

Build the OSI path only if the organisers reject the baseline's own NC stack (Q-L1). Until then, record
an OSI substitute and its measured cost for every NC stage (the R3 ablations).

### 6.4 Unconfirmed-rule dependency matrix

| Rule question | F | 1 | 2 | 3 | What is at stake |
|---|---|---|---|---|---|
| Public scans as tracking priors and sim assets (pose boards) | H | H | H | M | Symmetric spin (cup-anchor and lid episodes), exact frame, exact size, collision geometry |
| Spoon scan frame convention | H | H | H | H | 10/20 eval episodes; a wrong sign zeroes the spoon |
| Kit timing mapping under `motion_speed 0.5` (06) | H | H | H | H | Every board |
| NC code acceptable (FP, FS, nvdiffrast, MANO, SAM License) | H | H | M | M | Prize eligibility |
| URDF inertials, convex-part collision authoring, support USDA from our table | M | M | H | M | Sim trackability, insertion tasks |
| Cross-episode pooling of eval/public *videos* | — | L | L | H | Library meshes, spoon |
| Public GT as training supervision (user rule + organisers) | — | — | — | optional | In-domain fine-tune |
| Non-default shipped configs (stiff wrist etc.) | — | opt | opt | opt | Not planned; keep defaults |
| Metric aggregation for "track winner" | all | all | all | all | Which board to trade off |

H/M/L = high/medium/low dependence.

---------------------------------------------------------------------------------------------------

## 7. Experiment ladder (ordered by information per GPU-hour)

Rules for every rung:
- Public mocap is read only by the scorer or evaluator-side diagnostics, after inference.
- Development uses the 14 dev episodes. The 6 holdout episodes are scored only at R12.
- Each RL comparison uses ≥ 2 seeds and reports seed spread. A "win" must exceed the spread.
- Every row reports AUC, SP-SR, MP-SR, RPE, MPPE (+ CD-O where relevant), `e_ref` / `e_track` /
  `e_score`, GPU-h, wall-clock and failure counts together.

| Rung | Question it answers | Method | GPU-h [E] | GT use | Decision / kill rule | Owner | Earliest |
|---|---|---|---|---|---|---|---|
| **R0** | Are the plumbing assumptions right? | (a) Timing contract: synthesise evaluator-format exports from public GT with FlashCHORD's 0.5× resampling, pack with the kit, score: must be 1/1/1/0/0; adopt 06's audit. (b) Frame-convention rule on all 10 scans (07); spoon sign rule. (c) Read the kit CD-O code: Sim(3) registration initialisation and point counts. (d) Config-diff compliance tool. (e) Read the kit object list: which slot holds the spoon/cup in each eval episode. | 0 (CPU) | Scorer only | Any failure blocks all RL until fixed | P4 (a, d, e), P2 (b, c) | Day 1-3 |
| **R1** | Is symmetric spin observable? What does the rig see? | Inspect frames: texture/logos on blue/beige cup and lid; visible mocap markers; camera-object distance distribution from stereo; colour shutter; colour↔mono offset (Q2 of 03) | ~0-1 | None | Spin unobservable → accept the loss on those episodes and ask organisers Q1. Observable only with the scan → Q1 is top priority. | P2, P1 | Day 2-4 |
| **R2** | Which stereo depth, at what resolution? | Fuse masked stereo depth of scanned objects; compare with scans placed at the mocap pose (evaluator side). FS-TAO vs FS-L vs DEFOM vs SGBM, full vs reduced resolution, edge band on/off. | 2-4 | Scorer-side placement only | Pass: median < 3 mm at 0.4-0.7 m and no bias > 5 mm on the white pot. Pick the best licence-admissible model. | P1 | Wk 1 |
| **R3** | How large is `e_ref`, and where does it live? | Kit-score *references* on dev episodes. Variants: F vs Arch-1 perception; stereo vs MoGe depth; scans vs own meshes; smoother on/off; anchor from frame 0 vs static prefix vs support-constrained; FP vs MegaPose (OSI cost). **R3-diag:** split ADD mass into windows (occluded/flip/static/held). | 5-15 | Scorer only | Arch-1 perception must beat F by ≥ 0.1 reference-AUC, else rethink. R3-diag < 25 % in ambiguous windows → drop the Arch-3 joint optimiser. | P1 (+P2 meshes) | Wk 1-2 |
| **R4** | Which hand reference is trackable? (cheapest discriminator between Arch-1 and Arch-2 transfer) | Physical replay at VOC 0 on 6 dev episodes (6 families), same object reference: F hands, Arch-1 repaired hands, Arch-2 synthesised grasps (prototype on ≥ 3 prehensile families). Metrics: object error vs reference, survival time, ejections. | 1-3 | None (vs our reference) | Arch-2 replay error ≤ 0.5× Arch-1 on ≥ 4/6 → fund Arch-2 transfer for R7. Otherwise keep it as a per-family option. | P3 | Wk 1-2 |
| **R5** | How large is `e_track`, how long does a policy take, and is evaluation deterministic? | Default recipe (+ frame-0 resets) on 4 dev episodes × 2 seeds with the best available reference. Wall-clock per policy on the rented GPU type; training-mode vs evaluator gap; seed spread. Evaluate one checkpoint twice on two GPU models and diff the trajectories. | 10-20 | Scorer only | Sets the fleet size and seeds per episode. If `e_track` ≫ `e_ref`, shift a person to transfer. Non-determinism → fix the GPU type for reproduction. | P3 (P4 fleet) | Wk 1-2 |
| R6 (optional, user decision) | Policy-only floor | Train on the mocap GT object reference (oracle) for the R5 episodes | ~8 | **GT as training input:** diagnostic only, never a candidate | Gap between R5 and oracle = reference-induced tracking loss | P3 | Wk 2 |
| **R10** | Spoon: mesh, frame, tracking (10/20 eval episodes, no GT anywhere) | Proxies: treat elongated scanned objects (mini_sweeper, mini_dust_pan handle) as unscanned and run the spoon pipeline vs mocap. On spoon eval clips, GT-free checks only: cross-episode size consistency, multi-view silhouette IoU, settle test. Library vs single-episode Chamfer on scanned objects. | 5-20 | Scorer on proxies only | Choose generative vs parametric vs fused spoon. Library kept if ≥ 20 % Chamfer gain. | P2 | Wk 2-3 |
| **R7** | Final training recipe and hand branch | 6-8 dev episodes × 2 seeds, one factor at a time vs control: (a) score-aligned keypoints, (b) evaluation-matched resets, (c) contact relabel / force-closure blend, (d) relaxed-termination tail, (e) Arch-2 hands (if R4 funded), (f) confidence-weighted object reward. Then the best combination. | 50-100 | Scorer only | Keep a factor if the mean gain > seed spread and no board regresses beyond spread. Per-family hand branch rule fixed here. | P3 (+P5) | Wk 2-3 |
| **R9** | Can we select seeds/variants without GT? | Reuse R5/R7/R8 checkpoints (≥ 10 per family): Spearman of (in-sim tracking vs reference) and of (rollout-vs-video consistency, if built) against mocap AUC | ~0 (+ rendering) | Scorer only | rho ≥ 0.5 → use for selection; else pick a fixed seed count and no selection | P4/P6 | Wk 3 |
| **R8** | Full pipeline v1 | All 14 dev episodes, then all 20 eval episodes, 1-2 seeds; first pose submissions (and CD-O as soon as meshes exist, likely week 2) | 60-120 | Scorer only (dev) | Sets the leaderboard calibration; failure mining list | P4 | Wk 3 |
| R11 (conditional) | Is whole-clip estimation worth it? | Arch-3 3.4 on the worst 5 dev episodes from R3-diag; mode search for flips/spin | 20-60 | Scorer only | Keep if `e_ref` AUC improves by ≥ 0.03 on those episodes without regressions | P6 | Wk 3-4 |
| **R12** | Final runs | 20 eval episodes × 3 seeds with the final recipe; holdout scored once; reproducibility single-command test on a clean host | 150-300 | Scorer only (holdout) | Final picks (§8.3) | All | Wk 4 |

Total ≈ 330-650 GPU-h, plus R6/R11 if run. This is consistent with scenario B in the requirements note
(350-650 GPU-h). Cost at $1-2.5/GPU-h: ~$0.35-1.6k [E].

Information-per-GPU-h logic:
- R0-R4 cost under ~25 GPU-h together. They decide the P0 risks, the perception thesis and the transfer
  branch.
- R5 is the single most valuable RL experiment: it sizes `e_track`, the fleet and determinism.
- Large RL sweeps (R7, R8, R12) come only after the cheap rungs have removed dead branches.

---------------------------------------------------------------------------------------------------

## 8. Team split, calendar and submission strategy

### 8.1 Roles (4 core, 2 optional). File ownership is by module, so nobody edits another's stage.

| Person | Owns (modules) | Rungs | Architecture role |
|---|---|---|---|
| P1 Perception-geometry | S0 rig, 1.2 stereo, 1.4 camera/world/table, 1.6 tracking, 1.8 smoother | R1 (sync), R2, R3 | Arch-1 perception (shared by Arch-2 and Arch-3) |
| P2 Objects, frames, meshes | S2 canonical frame (with 07), 1.5 meshes, CD-O, spoon, symmetric-spin study, URDF/CoACD assets, library | R0b-c, R1, R10 | CD-O board owner; Arch-3 3.2 |
| P3 Transfer/RL | 1.9-1.11 reference repair and FlashCHORD training changes, physical replay, Arch-2 2.8-2.12 grasp/MPC prototype | R4, R5, R6, R7 | Decides the transfer half |
| P4 Infra, evaluation, compliance, submissions | S1 harness, S3 compliance, S4 fleet/queue, packer, digests, repo shared with organisers, single-command reproduction, licence register, organiser liaison, Arch-F | R0a/d/e, R8, R9, R12 | Owns Arch-F and every submission |
| P5 (optional) | Arch-1 1.7 multi-view hands + contacts, **or** the Arch-2 MPC executor (whichever R4 favours) | R7 | Second transfer person |
| P6 (optional) | Arch-3 components: mode search, rollout rendering/selection | R9, R11 | Harvests Arch-3 |

Coordination:
- Serialize heavy GPU jobs through P4's queue.
- Every run writes a manifest: code SHA, config diff, inputs, digests.
- Integrate weekly (Friday) into one pipeline command.

### 8.2 Calendar (today Sun 2026-10-04; freeze Wed 2026-11-04 17:00 EST = 22:00 UTC = Thu 2026-11-05 01:00 +03)

| Week | Goals | Exit criteria |
|---|---|---|
| Wk 1 (Oct 5-11) | Organiser email sent Monday (§9). Fleet up. Kit harness + R0. FlashCHORD trains one policy on Arch-F's reference (R5 starts). Stereo R2. Spin and spoon convention R1/R0b. Arch-2 grasp prototype on 2 prehensile families. | Timing contract green; policy wall-clock known; stereo choice made |
| Wk 2 (Oct 12-18) | Arch-1 perception v1 → R3 on dev. R4 hand A/B. R5 done. Arch-F end-to-end on 20 eval → **first pose submissions** (validate packer and leaderboard behaviour). **First CD-O submission** from own meshes. | Perception thesis confirmed or revised; transfer branch funded |
| Wk 3 (Oct 19-25) | R7 transfer ablations. R10 spoon. R8 full Arch-1 (+ Arch-2 families) dev + eval run v1 → submissions. R9 proxy check. | Final recipe frozen by Oct 25 |
| Wk 4 (Oct 26-Nov 1) | R11 if justified. R12 final eval runs (3 seeds). Holdout check. Clean-host single-command reproduction. Technical report draft. | Two final candidates ready by Nov 1 |
| Final (Nov 1-4) | Unlimited submissions in the last 3 days [V track3]: submit genuine full-pipeline variants (seed sets, finished recipe variants) | Picks made by Nov 4 12:00 EST |

### 8.3 Submission strategy and red lines

- The 5/week per-board budget goes on learning, not hill-climbing:
  - week 2: 1-2 submissions (packer, LB sanity);
  - week 3: 2-3 (v1);
  - week 4: 3-5.
- Final two picks [H]:
  1. the pipeline best on local dev + frozen holdout (hedges the sponsor's further held-out evaluation);
  2. the best public-LB score among *genuine full-pipeline* variants.
- Red lines:
  - no files crafted to probe the hidden reference, including per-episode variant swaps whose purpose is
    to read one episode's score;
  - no evaluator, physics or `motion_speed` changes;
  - no GT at inference;
  - no manual correction of eval episodes (Kaggle: no hand labelling) [V track3];
  - every correction automatic and identical across episodes, unlike the organisers' hand-levelled demo
    [V 01 D].

---------------------------------------------------------------------------------------------------

## 9. Organiser questions, ranked by score impact (merge into the single email)

1. **Q-S1** May public scanned meshes and URDFs be used as tracking priors and sim assets for the five
   pose boards (CD-O already excluded)? This decides symmetric-object spin, frame convention and sizes
   on most episodes.
2. **Q-S2** Does the hidden wooden-spoon scan follow the public scans' frame convention (centroid,
   principal axes ascending variance, sign rule)? Which slot holds the spoon in each eval episode?
3. **Q-T1** (if 06 finds ambiguity) How does the kit map evaluator rows (`reference_frame`, `time_s`) to
   mocap frames when `motion_speed = 0.5`?
4. **Q-L1** Are the organiser baseline's non-OSI dependencies (FoundationPose, FoundationStereo,
   nvdiffrast, MANO, SAM License code) acceptable in a prize-eligible solution, given the Kaggle
   open-source clause?
5. **Q-A1** Are URDF inertials, multi-geometry convex collision authoring and support USDA generated
   from our reconstructed table participant-controlled assets, or "physics"?
6. **Q-P1** May an episode's pipeline use other episodes' *videos* (no GT) for meshes and priors?
7. **Q-M1** How do the six boards combine into "track winner"?
8. **Q-R1** Will reproduction re-run the evaluator on different GPU models (determinism)?

---------------------------------------------------------------------------------------------------

## 10. Register of new hypotheses in this note (all [H], untested)

| ID | Hypothesis | Cheapest falsifier |
|---|---|---|
| H08-1 | Symmetric slot-0 objects (cups) and the lid carry an unobservable spin unless the scan + visible texture are used. Worth tenths of AUC on those episodes. Visible mocap markers could break the symmetry, but must not be relied on: marker-free held-out data would not have them. | R1 visual inspection; R3 spin error on cup episodes with scan vs own mesh |
| H08-2 | The spoon's scan frame is inferable: centroid + PCA ascending variance + skew-sign on x and z + right-handed y. | R0b: the rule reproduces all 10 public scan frames |
| H08-3 | Support-constrained anchor: a resting slot-0 object = table plane + stable pose + yaw (3 DoF). This cuts anchor rotation error to yaw only. | R3 anchor variants |
| H08-4 | Trackers must pass anisotropic covariances and K hypotheses; a unimodal smoother averages flips into wrong poses. | R3: smoother with vs without hypotheses on flip windows |
| H08-5 | Confidence-weighted object reward (down-weight bridged windows and symmetric spin) reduces chasing of reference noise. | R7 factor (f) |
| H08-6 | Relaxed-termination tail in training teaches recovery and reduces flings, because evaluation runs without failure terminations. | R7 factor (d): count of flung objects |
| H08-7 | Physical infeasibility of a perceived motion (no grasp can produce it) is a GT-free perception error detector. | R4: infeasible windows vs `e_ref` error windows overlap |
| H08-8 | Stereo edge-band masking is required for thin objects (spoon, brush handles). | R2/R10 with vs without edge band |
| H08-9 | Untouched objects' apparent world motion is a GT-free drift meter, usable as a gate. | R3: correlation with true common drift |
| H08-10 | Per-episode choice among genuine policy variants by in-sim error vs our reference avoids catastrophic seeds. | R9 Spearman |
| H08-11 | Pre-decomposed convex collision parts in our URDF avoid CoACD filling rack slots on insertion tasks. Rule question Q-A1. | CoACD preview on own rack mesh; replay of the cup-in-rack segment |
| H08-12 | Rollout-vs-video window diagnosis separates "reference wrong" from "policy failed" without GT. | R9/R11 against `e_ref`/`e_track` decomposition |
| H08-13 | Canonicalising CD-O meshes to the scan convention helps the scorer's Sim(3) registration converge. Depends on its initialisation. | R0c (read code); then scan-vs-own Chamfer with and without canonicalisation |
| H08-14 | Planning-profile figures in §2.3 and §6.1 hold within their ranges. | R8 |

---------------------------------------------------------------------------------------------------

## 11. Limitations of this note

- Nothing was run. All expected errors and profiles are planning estimates [E] derived from 02's
  idealised perturbations [M] (linear drift, iid noise, constant offsets). Real errors are correlated and
  heavy-tailed.
- 06 (timing) and 07 (frame convention) were not available. §0.3 items 1-2 may change the ranking of
  effort but not the architecture choice, since every architecture takes them as parameters.
- CHORD's clean-reference policy numbers [V 04] come from other datasets (ARCTIC etc., long bimanual
  sequences). They bound order of magnitude only.
- Licence text:
  - the Kaggle clause is the standard template wording from a search snippet, not this competition's
    page [U];
  - the NGC FoundationPose Model EULA was not read [U].
- The eval task names for the spoon episodes are unknown. Arch-2's coverage risk on those episodes
  cannot be assessed.
- Effort estimates in person-weeks are guesses for a team with no FlashCHORD experience yet.

Sources added by this note (web, 2026-10-04):
- Kaggle standard open-source clause (search snippet, DrivenData/Kaggle forum results):
  https://community.drivendata.org/t/official-pre-trained-models-external-data-thread/4003
- NGC FoundationPose model page ("Model EULA"):
  https://catalog.ngc.nvidia.com/orgs/nvidia/isaac/models/foundationpose
- Kaggle Track 3 rules page (JS-rendered, not readable by fetch):
  https://www.kaggle.com/competitions/v2d-challenge-track3-auc/rules


---
[← Index](../README.md) · [Summary](../00-summary.md) · [← 07](07-mesh-frame-convention.md) · [09 →](09-architectures-resourceful.md)
