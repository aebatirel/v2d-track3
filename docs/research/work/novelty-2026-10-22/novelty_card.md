# How innovative is our Track 3 approach? (2026-10-22)

Labels: **[M]** measured in this repo. **[L]** verified literature (authors' claims, not reproduced by us). **[G]** guess or estimate.

Corrections to the brief, from reading the code and repo:
- The detector is not OWLv2. It was dropped on 2026-10-13, and the `perc2.py` docstring is stale.
- The hand lift fits MediaPipe's 3-D hand shape (rotation, translation, scale) to the stereo depth. It does not look up depth per keypoint.
- We have no eval-set (leaderboard) score yet: tasks "eval perception" and "first full submission" are still pending. Every comparison with the leaders below sets 4 public validation episodes against their 20 hidden eval episodes, so it is indicative only.

## 1. Verdict

**Score: about 2 on a 5-point scale.** The scale runs: 1 = integration of off-the-shelf parts; 2 = well-engineered integration with measured adaptations; 3 = new combination validated by score; 4 = new method component; 5 = novel method.

**Every built stage has close prior art** that I verified, often covering the whole stage:
- **Perception:** EgoXperience's EgoX-Engine (Oct 2026) has essentially our architecture. It also adds tracking verification and stereo hand triangulation, which we lack.
- **Contact retargeting:** EgoCPT (Oct 2026) does the same step in the same setting (egocentric video, FoundationPose, Sharpa hand) and adds force allocation.
- **Rest settling:** DexForge already combines a ground-contact QP, rest detection and smoothing.
- **Meshes:** our TSDF fusion follows Curless–Levoy and BundleSDF, and the organisers ship a BundleSDF module that does the same job.
- **Policy:** the organisers' FlashCHORD recipe, run unchanged.

**Our adaptations are careful and measured**, but none would count as a method contribution:
- the co-location detection prior (+0.049 on the 20-episode perception mean);
- the simulator's own collision check inside retargeting;
- marking hands, table and other objects as occluders in 3-D rather than with 2-D masks;
- choosing variants without ground truth, with that proxy checked against the true score.

**What is genuinely ours is a diagnosis.** On hard episodes the bottleneck is whether the reconstructed scene is physically valid with the evaluator's object assist off, not perception accuracy. On ep18 our reference scores 0.98 against mocap, yet the policy scored 0.345, because our sweeper could not stand. A sweeper that stands raised it to 0.715.

**The only candidate for novelty is stage 8** (interaction-aware meshes). It is a new combination of known ingredients, and it is not built or scored.

**Two caveats on what counts as "ours":**
- The library meshes were fused along tracks that FoundationPose produced with the public scans as templates, and the build also used the scans to remove space occupied by other objects (the owner's "A-lite" decision). So we have not solved joint tracking plus reconstruction ourselves.
- Stereo, the fixed room and the visible mocap markers are dataset-specific. The professor flagged them as "slightly cheating-leaning", which matters for the Innovation award.

## 2. Scorecard

| Stage | What we do | Closest prior art [L] | Rating | What is ours |
|---|---|---|---|---|
| 1 Depth | FoundationStereo on the rectified mono pair, used unchanged | FoundationStereo; HOT3D (stereo 96.8 % vs mono 30.2 % recall@10 cm); EgoX-Engine | off-the-shelf | Choosing stereo over the organiser baseline's mono MoGe |
| 1 Detection | SAM2 proposals scored by DINOv2 against 42 grey renders, a 3-D size gate from stereo, a joint co-location prior | CNOS; SAM-6D ISM | adapted | Grey templates, size gate, episode-level prior: 20-episode mean 0.883 → 0.932 [M] |
| 1 Tracking | FoundationPose registration on frame 0, then tracking with our meshes; no verification or recovery | FoundationPose; EgoX-Engine and HO-Cap (both add verification) | off-the-shelf | Nothing; weaker than EgoX-Engine and HO-Cap |
| 1 Camera, table | Keyframe SIFT + stereo PnP; RANSAC plane closest under the objects | ORB-SLAM2 tracking thread; PCL tabletop | standard | The support-plane rule (a heuristic) |
| 2 Hands | MediaPipe on the colour camera; MediaPipe's 3-D shape fitted to stereo depth; greedy linking; bone-length lifting along camera rays | AnyTeleop; HO-Cap and EgoXperience (triangulation); KITRO | off-the-shelf / adapted | No MANO needed (licence); episode bone template (bone-length CV 0.24 → 0.07 [M], effect on score never isolated) |
| 3 Meshes | TSDF in the object frame along our tracks. Hands, table and other objects carve free space but never add surface. Also: carving below the table, fill/near hole closing, multi-episode fusion, colours from video | Curless–Levoy; Co-Fusion/MaskFusion; BundleSDF free space; organisers' v2d_bundlesdf | standard / adapted | Occluders found in 3-D instead of 2-D masks; CPU-only and licence-free |
| 3 Flat bases, assets | Underside flattened by hand along one perceived resting pose; colourless simulator copies | Make It Stand; Atlas3D; DSO; NVIDIA mesh_to_usd (drop test) | standard (manual) | Found that Newton splits a coloured mesh into one shape per colour (174 pieces → 1) |
| 4 E2S retargeting | Organiser's IK unchanged, fed MediaPipe joints | DexPilot; AnyTeleop | off-the-shelf | Plumbing only |
| 4 Pre-cleaning | Lead-in, 4 cm hand separation, joint-centre depenetration | ContactOpt; Do as I Do warm-up | standard | ep24 0.080 → 0.232 (single rollouts) [M] |
| 4 Contact retargeting + MjPen | Fingertips near a surface become targets. Wrist bounded to ±6 cm and solved with the finger joints by LM. Penetration comes from the evaluator's own MuJoCo scene | EgoCPT; DexForge; C2Dex; mink; SPIDER | adapted | Collision check identical to the evaluator's; bounded-wrist rule |
| 4 Rest settling | Detects resting objects, turns them onto stable hull faces, smooths over time | DexForge; PhysPose; trimesh stable poses | adapted | Applied per rest segment, gated by hand proximity, with an object-on-object exclusion |
| 5 Policy | FlashCHORD/FlashSAC unchanged, 250M steps, one seed. Two opt-in patches: keypoint scale, deployment-exact start | CHORD; DexMachina assist curriculum; FlashDexRetarget point reward; NVIDIA ReconBody resets | off-the-shelf | Neither patch moved the score beyond noise [M] |
| 6 Selection, QA | sim_vs_ref chooses checkpoints and variants; 6 repeat evaluations; drop test with assist off | SPIDER and OmniHOI rollout scoring; mesh_to_usd drop test | standard | Proxy checked against the true score (§3) |
| 7 Ops | Self-destroying Vast boxes, stall watchdog, HF store, HTTPS exec, one-command episode run | – | engineering | About $2–2.5 per policy; full run records ($49.76 for 13 boxes overnight [M]) |
| 8 Interaction-aware meshes | Census only (overlaps, defects) | Picasso; φ-Scene; PhyRecon; HOLD; NeuralFeels; Neural Shape Mating | new combination (hypothesis) | Constraints taken from a whole manipulation video, aimed at simulator validity: non-penetration, swept volumes, support, fingertip contact |

## 3. What is genuinely ours and worth defending or writing up

1. **The physical-validity diagnosis and its fix** [M]. This is the strongest item.
   - **ep18:** our reference scores 0.982 against mocap, but the policy scored 0.345. With the assist off, our sweeper tips over by frame 5 with no hand near it: its footprint is 0.3 cm² and its centre of mass sits 3 cm outside it. After flattening its base and settling it into a stable pose: 0.715 ± 0.240, with 5 of 6 rollouts at 0.79–0.84 and SP/MP success (one seed). The same setup with the rounded sweeper scored 0.368.
   - **ep24:** the boards have the same flaw (no stable standing pose).
   - **Gate:** the assist-off drop test flagged objects that fall or drop with no hand near them on 3 of 4 references.
   - The general idea is known (Atlas3D, PhyRecon, mesh_to_usd). Our contribution is the measured link to the score of a tracking policy built from video.
2. **The metric insight: mesh quality decides all five pose metrics under registered scoring** [M]. Damaged-scan test: clean 0.987, convex hull 0.947, bottom missing 0.904, 3 mm noise 0.825, 5 mm thicker 0.608 (flat objects register flipped); scale errors cost nothing. Useful for the organisers' post-challenge report.
3. **Choosing variants without ground truth, checked and with its noise measured** [M].
   - Spearman between sim_vs_ref and the true score: 0.98 on ep18 (9 policies), 0.86 on ep24 (7 policies, all within 0.04), 1.0 on ep12 and ep27 (3 each). Per rollout: 0.73–0.95.
   - Noise: ±0.01–0.10 between evaluations of one policy, about 0.04 between seeds. The single-rollout checkpoint sweep is optimistic by +0.026 on average (17 runs).
   - This is honest evaluation methodology, not a new method.
4. **Collision checks identical to the evaluator's** (MjPen) [M].
   - Penetration p95: ep24 20.1 → 6.0 mm, ep18 16 → 2.7 mm.
   - Rollout spread shrinks (ep12 ±0.067 → ±0.023).
   - The 4-episode mean barely moved (0.577 → 0.587). Defend it as engineering that makes rollouts reproducible, not as a score gain.
5. **A cheap, licence-light stack** (MediaPipe, stereo lift, CPU TSDF; about $2–2.5 per policy). This is an Industry Innovation angle, not a research one. MediaPipe is weaker than HaMeR or WiLoR.
6. **Stage 8, if built and scored.** It is the only item that could reach "new combination validated by score".

## 4. Where we are conventional, and what it costs us

| Episode | Ours (best variant, 6 evaluations) [M] | Share of the mean gap to ~0.84 | Conventional part behind the loss |
|---|---|---|---|
| ep24 boards | 0.318 (every variant 0.306–0.318); reference vs mocap 0.816 | **~0.13** | Unmodified RL recipe on a reference that is only kinematically cleaned; boards with no slots and no standing edges (13.5 cm³ overlap at the assembled pose); hand lift squashed into the board. Rollouts fail at the stand-up (board 1 at f102, board 2 at f117) |
| ep18 sweeper | 0.715 ± 0.240 (one seed, one dropped rollout); base 0.345 | ~0.03 | Flat base patched by hand; no second seed |
| ep12 cup + rack | 0.790 ± 0.023 | ~0.01 | Final cup placement (cup AUC 0.53 vs rack 1.0 in kr) |
| ep27 pot + rack | 0.942 ± 0.017 (base) | −0.03 | – |

The mean of the best variant per episode is **0.69**. That is optimistic, since the variants were picked with ground truth; the leaders are at 0.83–0.85. **Hard manipulation accounts for almost the whole gap.** Zihao Guo's SP 0.95 means 19 of 20 eval episodes succeed, so the leaders very likely handle the hard twins (eval 19, 25, 30, 38) that our recipe fails [G]. The literature agrees that cleaning a reference without physics is not enough (SPIDER, OmniHOI, EgoCPT) [L].

Other conventional choices that cost score on the eval set:
- **Mesh thickness.** Preliminary diagnostics [M]: walls 8–15 mm thick vs 2–7 mm in the scans; lid volume 3.5× and pitcher 4.2× the scan. Registered AUC with our mesh vs the scan: ep31 0.801 vs 0.876, ep21 0.917 vs 0.975, ep11 0.857 vs 0.914, ep39 0.953 vs 0.997, ep42 0.958 vs 0.986. CD-O is 0.22–1.15 cm vs the leaders' 0.065 and 0.313 cm (different episodes).
- **A tracker with no verification or recovery.** ep0 0.18 (lid 179° off by symmetry). The pot is in 6 eval episodes and the lid also appears.
- **Camera from chained keyframes, no room map.** Note 18 modelled +0.06–0.10 from a map [G, not run end to end, and possibly for a different VO]. The gain is bounded, because public perception already scores 0.932.
- **One seed per variant**, plus the optimistic single-rollout sweep (+0.026).
- **The spoon** (in 10 of 20 eval episodes, no scan): a near coin-flip on its frame convention. This is a convention risk rather than an innovation question, but it is large.

## 5. Most promising out-of-the-box directions, ranked by expected gain per cost (about 13 days left)

**Prerequisite, conventional but certain.** Run eval perception and train 20 eval policies × 2–3 reference variants, chosen by sim_vs_ref over ≥ 3 evaluations each. Cost: about $80–120 at $2 per training [G]. Without this we have no score at all.

1. **Automatic standing faces from every perceived rest segment** (a general version of flatten_base, gated by the assist-off stand test).
   - Every rest segment, in any episode including eval, gives a support plane in the object frame: the mesh is cut and filled to it. This replaces the hand patches, which do not scale to 20 eval episodes.
   - Seat floating references first; they float 1–4 cm [M].
   - **Cost:** CPU 1–2 days; GPU A/B about $8. **Expected gain** [G]: up to +0.3 on each episode with an object that cannot stand (ep18 measured with the manual version). On the eval mean it depends on how many such objects exist; counting them with the free CPU drop test is step 1.
   - **Falsified if:** objects do not stand within 2° and 3 mm for 20 assist-off steps at every rest segment of public episodes 12/18/23/24/27, or registered AUC drops by more than 0.01, or ep18 with the automatic mesh scores below 0.65 (2 seeds × 6 evaluations).
2. **Thin-shell meshing.**
   - First mesh the TSDF zero crossing instead of the blurred binary occupancy (hours). Then use a 1.5–2 mm sparse grid with 3–4 mm truncation and depth/angle weights, keeping open shells where a surface is seen from both sides.
   - **Cost:** CPU 1–2 days, plus about $2–4 for one public perception box to re-track with the new meshes. **Expected gain** [G]: +0.01–0.03 on the mean, bounded by the measured mesh-vs-scan gap of 0.03–0.075 per affected episode; plus CD-O and fewer nesting overlaps.
   - **Falsified if:** median thickness in the scans' thin regions stays above 6 mm, or registered AUC or the 8-seed flip rate on ep2/11/21/39/41 does not beat library_v2 by more than about 0.01.
3. **Carving at mating and nesting poses** (the minimum version of the owner's stage 8, and our only novelty story).
   - Where two tracked objects stay rigidly together, voxels where they overlap beyond the tracking-error floor go to the object with the weaker occupancy evidence. This carves slots and cavities: ep24 and its eval twin ep25, the nested cups in ep11, the lid on the pot.
   - **Cost:** CPU 1–2 days on top of the census; GPU A/B on ep24 about $8. **Expected gain** [G]: small on its own (ep24 also needs #4), but a precondition for #4.
   - **Falsified if:** overlap at assembled frames does not fall to the scan floor (3–4 cm³; ours is 9.0 vs 4.0 cm³ for the scans at the same tracks [M]), or the diagnostic CD worsens, or ep24's stand-up segment does not change.
4. **Physics-in-the-loop refinement of the hard windows.**
   - SPIDER / Do as I Do style sampling of wrist and finger keyframe offsets in FlashCHORD's Newton scene with the assist off, then RL on the reference the robot actually executes. Start with ep24 f95–135 and ep18's sweep strokes.
   - **Cost:** 2–4 days of code; GPU about $2–5 per episode for the search, plus $8 per RL A/B. **Expected gain** [G]: the largest potential, but uncertain; ep24-type episodes hold about 0.13 of the mean gap. Start it in parallel with #1–3 because of its lead time.
   - **Falsified if:** no sample keeps board 2 within 2 cm and 15° of our reference for ≥ 30 frames open loop (then it is infeasible with this geometry), or, if that passes, RL on the refined reference fails to beat k by ≥ 0.05 (2 seeds × 6 evaluations).
5. **Object-centric reward port from FlashDexRetarget** (released code for the same hand and the same RL algorithm).
   - Three changes: object reward from the top-3 surface-point errors, in ADD units; a one-sided fingertip-distance reward; weaker tracking of the human finger joints. Our keypoint-scale patch was a partial step: ep18 0.381 ± 0.012, the tightest result but within noise [M]. The paper reports 86 % vs 50 % for CHORD on Sharpa Wave [L].
   - **Cost:** about 1 day; GPU about $12 (ep18 and ep24 × 2 seeds, plus an ep12 control).
   - **Falsified if:** neither hard episode gains ≥ 0.03, or ep12 loses more than 0.03.
6. **Grip preload.**
   - In consolidated contact segments, place pad targets 2–4 mm inside the surface instead of 1 mm outside, so that position tracking produces a squeezing force. Hypothesis: this is why penetration fell 3–4× while the mean barely moved.
   - **Cost:** hours; a free CPU replay first, then a GPU A/B at $8.
   - **Falsified if:** in a CPU stiff-wrist replay, the carried object does not follow for clearly more frames on the ep12 and ep24 carry segments.
7. **Rest prior plus forward-backward tracking with depth-agreement verification.**
   - Freeze an object while no hand is near it; also track backward from the last frame; flag frames where the two directions disagree. `verify()` already exists in perc.py.
   - **Cost:** CPU about 1 day for the rest prior; about 1 day plus minutes of GPU for the backward pass. **Targets:** ep0 lid and pot, the pot and lid in eval episodes.
   - **Falsified if:** the 20-episode perception AUC vs mocap gains less than 0.005, or ep0 does not rise, or the disagreement flag's precision is below 0.5.
8. **Persistent room map** (note 18 prototype: a 21.5-minute CPU map that relocalises all 20 eval clips to about 2 mm).
   - **Cost:** CPU 1–2 days. **Expected gain** [G]: bounded, since public perception is already at 0.932.
   - **Falsified if:** with maps that leave out each test episode's frames, swapping in the relocalised camera poses gains less than 0.01 and the pot-only episodes 41–45 do not improve.

**Not ranked for this freeze:**
- Generative completion (Hunyuan3D-Omni, SAM 3D, TRELLIS.2): licence conflicts with the Apache-2.0 release rule, and hallucination risk.
- Triangulated hand keypoints: 2–3 days, and the matching quality on mono images is unknown.
- Learned hand-object priors: depend on MANO, whose licence we do not have.

Files I drew on:
- /home/user/v2d-track3/docs/overnight-2026-10-22.md
- /home/user/v2d-track3/STATUS.md
- /home/user/v2d-track3/docs/research/competitors-2026-10-21.md
- /home/user/v2d-track3/docs/work-log.md
- /home/user/v2d-track3/ops/box/patch_flashchord.py
- /home/user/v2d-track3/pipeline/auto_ep.sh
- /home/user/v2d-track3/results/e2e/overnight_20261022/

The stage 5–6 input review arrived cut off, so I completed that part from these files.