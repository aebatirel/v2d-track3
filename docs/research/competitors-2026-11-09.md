# V2D Track 3 after the freeze: what the teams above us did, and what we could have done differently

Research date: 2026-11-09 (winners are announced on 12 Nov; no team has published a write-up yet). Read-only
research: nothing in the pipeline or a submission changed, no GPU rented ($0). Third-party repositories were read,
never executed.

Labels: **[F]** fact from a primary source (link or file given). **[M]** number measured in a source (Kaggle API,
the organisers' leaderboard feed, our own reports). **[I]** inference. **[H]** hypothesis, with the experiment
that would falsify it.

Sources:
- Kaggle API, six Track 3 boards, read 2026-11-09 (`/api/v1/competitions/v2d-challenge-track3-*/leaderboard/view`).
- Organisers' feed: https://github.com/MVerghese/v2d-leaderboard-data (`leaderboard.json` generated 5 Nov 01:43 UTC;
  `submission_history.jsonl`, 524 Track 3 snapshots).
- Public competitor repositories (all found by GitHub search on 9 Nov):
  - https://github.com/cringeyburger/purple-v2d-track3 (Team Purple / Barry Allen, AUC 0.933; one commit, 4 Nov)
  - https://github.com/kyounginbaik/SRL_V2D (SRL, AUC 0.923, CD-O 1st; one visible commit, 16 Oct)
  - https://github.com/zjifan121-source/NVIDIA_V2D_Egocentric (Gravity Aligned, 0.780)
  - https://github.com/the-simsons/ego2sim-nvidia-v2d and https://github.com/shrinidik18/v2d_track3 (The Simsons, 0.651)
  - https://github.com/civicW/v2d-challenge-asap (ASAP_Team, 0.652)
  - https://github.com/yuchenzema/v2d-track3 (ycchen99, invalidated)
  - https://github.com/Att100/Nvidia-V2D-Challenge-Submission (HOI2Policy, 0.453), https://github.com/tianny0078/v2d-track3,
    https://github.com/Swaguto/NVIDIA-V2D-Challenge, https://github.com/BAp3r/v2d-track3-submission
  - https://github.com/hobbit04/ObsidianVault (`Project/V2D/`, notes that appear to come from an rlwrld member; weak)
- Ours: the Track 3 Journey Report (https://claude.ai/artifact/6pNjoK3xEqi8ry4ceA6jLS) and the case study
  (https://claude.ai/artifact/XyF2LbdbMZT5tgE9Qufz1b).

No public code exists for richchentw, DDD, Zihao Guo or egocube. Everything about them is inferred from board
timelines.

---

## 1. Final boards [M]

| Rank sum | Team | AUC | SP-SR | MP-SR | RPE cm | MPPE cm | CD-O cm | Uploads |
|---|---|---|---|---|---|---|---|---|
| 7 | richchentw | 0.985 | 1.00 | 1.00 | 0.63 | 0.60 | 0.212 | 84 |
| 15 | DDD | 0.953 | 1.00 | 1.00 | 0.93 | 0.93 | 0.232 | 22 |
| 23 | rlwrld | 0.934 | 1.00 | 1.00 | 1.05 | 1.23 | 0.246 | 82 |
| 24 | Zihao Guo | 0.935 | 1.00 | 1.00 | 1.26 | 1.17 | 0.247 | 29 |
| 33 | egocube | 0.928 | 1.00 | 1.00 | 1.24 | 1.24 | 0.236 | 34 |
| 37 | SRL | 0.923 | 1.00 | 1.00 | 1.50 | 1.39 | 0.207 | 60 |
| 46 | Barry Allen | 0.933 | 1.00 | 1.00 | 1.42 | 1.25 | 0.295 | 16 |
| 47 | Purple | 0.933 | 1.00 | 1.00 | 1.39 | 1.25 | 0.295 | 84 |
| **56** | **Imitation.Tech** | 0.886 | 0.90 | 0.80 | 2.21 | 1.80 | 0.239 | 26 |
| 61 | DSAIL | 0.878 | 0.90 | 0.85 | 1.99 | 1.86 | 0.267 | 57 |

- We are 9th by rank sum. Barry Allen and Purple are one solution on two accounts (identical AUC, MPPE and CD-O;
  the Purple repository belongs to Barry Allen's Kaggle user), so 8th if the organisers merge them. The feed's own
  `rank` column orders by AUC.
- Every team above us has SP-SR 1.00 and MP-SR 1.00: no failed episode. We have 2 and 4.
- Six teams sit in a tight cluster at AUC 0.92–0.935 and MPPE 1.17–1.39 cm. DDD is one step better. richchentw is
  alone at 0.60 cm.
- Kaggle allowed 25 uploads per day (`maxDailySubmissions: 25`, competition API) [F]. Our October note recorded
  "5 submissions/week" from the FAQ.

## 2. What the teams above us did

### 2.1 Stock RL; the poses did the work [F for three teams]
- **Purple** (verified in code): stock FlashCHORD runtime, floating Sharpa hands, soft stock wrist (`wrist_kp: 25`),
  250M steps, 4,096 worlds, seed 42, "one policy per episode, fixed world 0". Two retrains (E14, and E16 continued
  25M steps with `object_keypoints: 40`). No designed grasps, no stiff wrist, no seed race.
- **SRL** (verified in code, state of 16 Oct): FlashSAC, 100.7M steps, 2,048 worlds, three seeds, wrist kp 100,
  `motion_speed 1.0`, fixed frame-0 resets, a performance-gated assist curriculum, hand-set masses (pot 0.2 kg,
  lid and spoon 0.1 kg), checkpoint chosen by a local copy of the six metrics against their own reference.
- **rlwrld** (notes, weak): stock FlashCHORD at 250M steps; the notes trace failed clips to pose quality.
- None of the three built grasps by hand. Our grasp-lock, wrist-ILC, evolutionary grasp search and lift-window
  work has no counterpart in their code.

### 2.2 Half-speed playback, with the rollout resampled to video time [F for Purple]
- `postprocess/bridge_export.py` maps simulator steps to dataset frames with `step(f) = f (S-1)/(N-1)` and
  interpolates; it calls the kit packer's unconverted mode "a TRAP". Their training config keeps NVIDIA's
  `motion_speed: 0.5`.
- We found the same timing bug (it caps public AUC at 0.415) and fixed it on the other side: we trained at real
  speed. Our own CPU model says the stock wrist is out of range on 23 of 27 moving public tracks at real speed and
  on 0 of 27 at half speed (builder session, 26 Oct). Real speed is what led us to the kp 400 wrist.
- **[H]** Half-speed training with a resampled export would have given us easier following and less run-to-run
  spread with the stock recipe. Falsifier: three public episodes (12, 18, 27), stock recipe at 0.5 with a
  resampled export against our packed recipe, 10 fresh draws each; falsified if the registered AUC is not higher
  or the spread not lower. It is not necessary for 0.92: SRL trained at speed 1.0 with kp 100.

### 2.3 Collision geometry built by hand for the cavity cases [F for Purple]
- Cups: 192 convex sector pieces, "no global hull over mouth". Dish rack: ten boxes, five for the tray and five
  for a utensil pocket whose depth is `max(q95 visible depth, deepest spoon reference + 2mm)`.
- These are the nested-cup and spoon- or sweeper-in-rack cases (our evals 10, 14, 30) that kept our MP-SR at 0.80.
  We carved two episodes late (pack 4, +0.022) and then found that policies are tied to the shapes they trained
  on (1 of 7 retrains passed).

### 2.4 Perception front end [F for Purple and Gravity Aligned]
- SAM 3 text-prompted masks per object, plus a `hand` mask, on all three cameras. We used SAM2 proposals scored by
  DINOv2 with hand-written rules, and lost objects to the wearer's wrist and watch on five evals.
- A SLAM world frame (cuVSLAM for Purple, DROID-SLAM for Gravity Aligned and the stock kit). Ours was keyframe
  SIFT / stereo PnP; our measured drift was already 2–9 mm, so this is probably not the difference [I].
- Fast-FoundationStereo depth and FoundationPose, as ours.
- Not found in any top-team source: marker tracking, a learned pose corrector, global trajectory optimisation.

### 2.5 Public scans as tracking templates: a grey zone [F for SRL in development, I beyond that]
- SRL's development baseline tracked with `mesh='provided'` (the public scans) and then moved the poses onto the
  submission mesh by a rigid transform (`old_from_submission`; mean surface distance 2.3 mm pot, 2.9 mm lid).
- Purple's default FoundationPose output is named `T_A_from_scan`; a later variant is "fresh own-model FP ... no
  stale public-frame rebase"; and the spoon path, the one object with no public scan, is called "scan-free pose".
  This suggests an earlier scan-templated pass. The final lineage sits in their verification container and cannot
  be checked [I].
- Our own measurement [M]: with exact scans as templates 16 of 20 public episodes score 0.96–1.00 in perception
  (30 Oct); with our own meshes the same stack scored 0.868 (25 Oct) to 0.945 (2 Nov).
- The organisers removed submissions whose *submitted* meshes were scan-like: CD-O 0.06–0.11 disappeared on
  23 Oct, 27 Oct and 2 Nov (SoySauceChicken 0.902 AUC -> 0.765; ycchen99 all 29 uploads; richchentw lost four and
  its CD-O went 0.154 -> 0.213 while its AUC moved only 0.9330 -> 0.9316) [M]. Tracking with a scan while
  submitting an own mesh is invisible in the file.
- We chose route A (own meshes everywhere) on 21 Oct. The organiser email that asked this exact question was
  drafted on 22 Oct and never sent.

### 2.6 Edits aimed at the scorer [F for Purple]
- E20: one submitted row is changed. The pitcher's frame-0 orientation is rotated toward the mean of reference
  frames 0–10, which shifts the scorer's one-time scene alignment for every frame.
- E25: each board's body frame is flipped 180 degrees with the scorer's own mesh helpers, to counter the
  registration ambiguity of flat boards.
- We knew both effects (frame-0 "lottery", 26–27 Oct; registration, 21 Oct and 2 Nov) and used mesh choice as the
  lever (+0.046 AUC). We did not edit rollout rows.

### 2.7 The board as a measuring instrument [F for the mechanism, H for who used it]
- Episode scores add up exactly (Gravity Aligned measured a maximum gap of 0.00002), so a file with one episode
  masked reveals that episode's true score. The Simsons' code builds 20 such probe files
  (`probe/make_probe_packages.py`).
- Upload counts: richchentw 84, Purple 84, rlwrld 82, EIG 71, SRL 60, DSAIL 57; ours 26.
- richchentw: 0.945 / 1.09 cm after 16 uploads (30 Oct), then 0.985 / 0.60 cm after 65 more in four days.
- **[H]** The last step from about 1.1 cm to 0.6 cm came from per-episode selection or tuning against the board.
  It cannot be confirmed from outside. It is not needed for 0.93–0.95: DDD reached 0.931 on its 4th upload and
  0.953 on its 20th.
- Our rules forbid tuning on eval results, and we refused it (one disclosed exception, pack 6).
- All standings are provisional until the organisers' container reproduces each counted file (PR #215), and a
  held-out evaluation follows.

## 3. What we could have done better

Ordered by my estimate of the score at stake.

1. **Put the effort where the loss was.** The cluster above us tracks at about 1.2 cm; we ended at 1.8 cm.
   richchentw's second-ever upload (22 Oct) already had 1.46 cm. From 24 Oct to 1 Nov most of our GPU money and
   sessions went to the robot side (grasp design, seeds, swaps, carving), while our own split on 30 Oct read
   policy 0.083 against reference about 0.10. The perception push came in the last four days as about 20 small
   GT-free patches, and all failed. The bigger options were listed and never run: joint shape and pose
   (item 8 of our open list, "days of work and $100+") and a SAM 3 front end with a hand mask.
2. **Settle the rule questions in week one.** One reply from the organisers on scan templates, on collision
   shapes that differ from the submitted mesh, and on the stiffer wrist would have fixed three strategy branches
   on 22 Oct. We were strict where it was expensive (own templates for tracking) and later relaxed where it was
   cheap (GT-informed choice among generated meshes, 2 Nov).
3. **Read the scorer and the ranking rule before building.** Already in our own lessons: the rank-sum rule was
   found on 31 Oct and the registration effect was understood on 2 Nov; mesh-only changes then gave +0.046 AUC in
   about 36 hours. Purple's two row-level fixes come from the same reading.
4. **No failed episodes first.** One SP-SR episode was worth about four rank points. Analytic collision geometry
   for cups, rack and boards, built before training, is how Purple cleared the cases that we were still failing.
5. **Fix the timing on the export side** (section 2.2, hypothesis).
6. **Gates that were too strict for single ideas.** "Mean +0.005 and no episode below −0.01" on 20 noisy public
   episodes rejects many true small gains; the closest misses were 0.00002 and 0.007. Ideas were also tested one
   at a time against a tracker that is fragile to single changes [I]. The gates did protect us from false wins.
7. **We stopped 36 hours before the freeze.** Last upload 3 Nov 10:30; freeze 4 Nov 22:00. In that window Zihao Guo
   went 0.921 -> 0.935, SRL 0.903 -> 0.923, Purple 0.920 -> 0.933, DDD 0.939 -> 0.953, and three of them cleared
   their last MP-SR failures. CD-O third place was 0.006 cm away, about one more mesh round.

## 4. What we did well by comparison
- CD-O 5th with own meshes, ahead of rlwrld, Zihao Guo and Purple.
- A complete audit trail and pre-registered tests; no invalidated uploads. Several teams lost their best scores to
  invalidation.
- Gravity Aligned, with a similar stack (FoundationStereo, SAM 3, SAM 3D meshes, FoundationPose, 371 runs),
  ended at 0.780.

## 5. Open
- Winners' talks on 12 Nov (CoRL tutorial) should show what richchentw and DDD did. Re-read this note then.
- Whether the container reproduction accepts scan-templated tracks, row edits and board-selected files.

## 6. Addendum (9 Nov, owner's follow-up): efficiency, and how they handled perception

### 6.1 Efficiency
| Measure | Teams above us | Us |
|---|---|---|
| Policy trainings | Purple: about 22 visible (20 episodes + 2 retrains, 250M steps each) [F]; SRL: 3 seeds x 20 episodes at 100M steps [F, 16 Oct] | at least 158 trainings, 246 GPU-hours, 135 machines by 30 Oct [M] |
| Uploads | DDD 22, Zihao Guo 29, egocube 34; SRL 60, rlwrld 82, richchentw 84, Purple 84 (+16 on the second account) [M] | 26 |
| Days from first upload to best | richchentw 0.903 on day 1; DDD 0.931 on day 6 (4th upload); rlwrld 0.934 in 7 days; Purple 0.933 in 9 days [M] | 0.886 in 10 days |
| Cost | not stated anywhere; SRL and Gravity Aligned use university clusters | about $556 GPU [E] |

- Robot side: they were more efficient, because near-stock RL was enough for them and needed few experiments.
- Board use: three of the top teams were far heavier users than we were.
- Total cost cannot be compared. The public repositories are final snapshots (one commit each) and hide failed
  experiments. Gravity Aligned shows the other direction: 371 runs for 0.780.

### 6.2 Perception
- Same building blocks as ours in every repository read: stereo depth (Fast-FoundationStereo) and FoundationPose.
  No top-team source contains a new tracker, marker tracking, a learned corrector or a global optimiser.
- What differs in Purple's code [F]:
  - SAM 3 text masks per object and a `hand` mask on all three cameras; hand pixels are dilated and removed before
    depth is used.
  - A SLAM world frame (cuVSLAM, hands and objects masked).
  - An explicit timing model: colour camera A "one frame late", with a per-frame lag. We measured the same pairing
    and a half-frame lateness; our half-frame advance (S2, +0.006 public) was never in a packed reference.
  - The spoon is not tracked with FoundationPose. A masked stereo cloud is registered to a spoon model by trimmed
    ICP (previous pose + 8 PCA starts), scored by distance plus silhouette overlap; the model is fused from all 10
    eval spoon episodes. We tracked a parametric template per episode and never resolved its frame.
  - Meshes are corrected against stereo points (at most 3 mm, held-out frame blocks).
  - Per-episode repairs at the end: fresh tracking for E8, retrains for E14 and E16, the frame-0 fix for E20, the
    board flip for E25.
- Board timelines [M]: one large step, then a slow per-episode grind. MPPE in one upload: Purple 4.42 -> 1.95 cm
  (28 Oct), DDD 2.31 -> 1.24 (29 Oct), SRL 3.11 -> 1.95 (29 Oct), rlwrld 3.16 -> 1.81 (29 Oct). Purple then needed
  about 80 uploads to go from 1.95 to 1.25 cm.
- **[I]** The cluster's advantage may be the absence of bad episodes more than a better tracker. Our RPE/MPPE
  ratio was 1.35 against 0.88-1.03 for the top six (31 Oct), which points to a few large per-episode errors; our
  proxy could not show which eval references were wrong, while a masked upload shows it directly.
  Falsifier: per-episode board scores of our counted file (the organisers' reproduction report, if it lists them);
  falsified if our loss is spread evenly over the 20 episodes.

### 6.3 Computation cost (owner's clarification, 9 Nov)
Compute for every team is almost all RL training. Perception is minutes per episode for everyone (ours: 94 s per
episode on GPU; The Simsons: hand tracking for 20 episodes in about 35 min on two RTX 4090).

| Team (final AUC) | Steps per policy | Time per policy | Policies trained | GPU-hours |
|---|---|---|---|---|
| Purple (0.933) | 250M, 4,096 worlds, stock [F] | about 1.5-1.8 h at our measured 45k steps/s [E] | 22 visible in the final snapshot [F]; earlier rounds unknown | at least about 35 [E] |
| rlwrld (0.934) | 250M stock [F, notes of 15-19 Oct]; the notes plan 125M, early stopping and warm starts per object | as Purple | unknown | unknown |
| SRL (0.923) | 100.7M, 2,048 worlds, 3 seeds [F, 16 Oct] | not stated | 60 per full pass | unknown |
| Gravity Aligned (0.780) | 100M, thresholds x0.4 of the 250M schedule [F] | "~40-55 min on L40S/A100/H100" [F] | 371 runs [F] | about 250-340 [E] |
| **Us (0.886)** | 250M standard, 70M grasp-lock fine-tunes | 1.5-1.8 h [M] | at least 158 by 30 Oct [M] | 246 billed by 30 Oct [M]; about 360 in all [E, from $556 at $1.53 per GPU-hour] |

- One complete submission needs 20 policies: about $50 at our prices [M, our "full 20-episode rerun with packing"].
  We spent about 11 times that. Most of it was experiments, second learners and seeds, repeat draws, retrains and
  side lanes, not final policies.
- Per policy, the 100M-step teams pay about 40 % of what we paid. SRL reached SP-SR and MP-SR 1.00 with that
  family of recipe (its final config is not public). Gravity Aligned reports its best checkpoint at 90-100M
  (median 95M) in 371 runs. We never tested a shorter schedule (open question 6 of the Journey Report).
- Gravity Aligned fits a 100M run in about 22 GB (njmax 1024, 1M float16 replay), so 24 GB cards work for them.
  We rented 96 GB cards and ran two trainings on each.
- No team states a total, and the snapshots hide earlier rounds. So "Purple used a tenth of our compute" is a lower
  bound on their side, not a measurement.

### 6.4 Purple's upload history: where its lead came from (owner's question, 9 Nov)
From `submission_history.jsonl` [M]; "n" is the upload count on the AUC board.

| Date | n | AUC | MPPE cm | RPE cm | SP-SR | MP-SR |
|---|---|---|---|---|---|---|
| 26 Oct | 2 | 0.696 | 4.42 | 5.09 | 0.60 | 0.45 |
| 28 Oct | 3 | 0.862 | 1.95 | 1.88 | 0.80 | 0.65 |
| 29 Oct | 4 | 0.870 | 1.89 | 1.68 | 0.80 | 0.70 |
| 30 Oct | 5 | 0.907 | 1.63 | 1.53 | 0.85 | 0.80 |
| 1 Nov | 25 | 0.916 | 1.44 | 1.42 | 0.95 | 0.85 |
| 2 Nov | 45 | 0.919 | 1.41 | 1.39 | 0.95 | 0.85 |
| 3 Nov | 64 | 0.921 | 1.35 | 1.39 | 1.00 | 0.95 |
| 4 Nov | 84 | 0.933 | 1.25 | 1.39 | 1.00 | 1.00 |

- Purple was above our final AUC (0.886) on its 5th upload, with MP-SR 0.80 like ours and SP-SR 0.85 below ours.
  So about 0.021 of the 0.047 gap existed at an equal number of failed episodes, and about 0.026 came with clearing
  them. This corrects the inference in 6.2, which put the weight on bad episodes alone: it is about half each.
- The code has no selection among policies or rollouts: one seed, one policy per episode, world 0 [F].
- The last 79 uploads gave +0.026 AUC, with MP-SR rising one episode at a time and RPE unchanged after upload 45.
  **[H]** These were per-episode fixes tried against the board and kept when they scored better; the build script
  names four (E14 and E16 retrains, the E20 frame-0 rotation, the E25 board flip). What else was tried is not in
  the repository.

### 6.5 Purple's perception in detail (second read of the code, 9 Nov)
Read from `reconstruction/tools/*.py`, `reconstruction/refine/*.py` and `postprocess/build_submission.py` (about
700 lines). The FoundationPose driver, the mask generation and the reference "bridge" are not in the repository, so
the cause of the 4.42 -> 1.95 cm step on 28 Oct is not visible.

| Step | Purple [F] | Ours |
|---|---|---|
| Object points | A stereo point is kept only if it lies in the object's SAM 3 mask in camera C **and** projects into the object's mask in camera B, and is outside the dilated `hand` mask in both (`sfp_common.frame_points_world`) | SAM2 masks, cut by hands; objects latched onto the wrist and watch on five evals; the hand-aware ray correction failed its gate (-0.0042) |
| World frame | cuVSLAM camera track with hands and objects masked; object points of all frames are pooled in that frame "no object pose involved" | keyframe SIFT / stereo PnP; points pooled along FoundationPose tracks |
| Spoon (32.5 % of eval object weight) | no FoundationPose: trimmed point-to-plane ICP of the clean cloud to a spoon model, starts = previous pose + 8 PCA starts, score = mean distance (mm) + 20 x (1 - silhouette IoU); a frame continues the track only at < 3 mm and IoU > 0.6; the model is fused from all 10 eval spoon episodes; fitted on camera C only, cameras A and B "stay held out" | FoundationPose on a parametric template, per episode; frame sign never resolved; "the spoon was never measurable" |
| Cups (17.5 %) | parametric frustum from a stereo-silhouette fit, 1.4 mm walls; a world-frame "cup" track next to the hands | FoundationPose on TSDF / lathe meshes; the tracker spins resting cups (140 degrees by frame 30) |
| Other objects | FoundationPose on colour camera A, with A modelled one frame late plus a per-frame lag | FoundationPose; half-frame lateness measured, correction never packed |
| Mesh | least-squares correction along normals to stereo points, capped at 3 mm, vertices need >= 10 points from >= 5 frames; alternating 20-frame dev / held-out blocks | TSDF, lathe, generated pools chosen by Chamfer to public scans |
| Frame 0 | E20: frame-0 pitcher orientation replaced by a rotation toward the mean of reference frames 0-10 | frame 0 known as our noisiest frame (1.07 degrees median against about 0.5 later); no correction shipped |

- **[I]** The pattern is "clean the points, then use a geometry-specific fit where FoundationPose is weak" (thin
  spoon, symmetric cups), not a better general tracker. Spoon and cups are half of the eval object weight.
- **[I]** Held-out cameras and held-out frame blocks give them a GT-free check on eval episodes that can see a
  wrong pose or shape (silhouette overlap in a camera the fit never used). Our GT-free proxy (sim_vs_ref) could not.
- **[H]** For us: spoon and cup poses from clean two-view-masked stereo points with a model-to-cloud ICP would beat
  our FoundationPose tracks on those objects. Falsifier: public cup episodes (11, 12, 21, 22) scored against mocap
  with the registered scorer, pre-registered gain of at least +0.02 on the cup objects and no episode worse by 0.01;
  the spoon has no public truth, so only the held-out-camera silhouette check is available there.

### 6.6 Colour versus grey (owner's question, 9 Nov)
- Purple did not drop stereo [F]: every point cloud, the spoon fit, the cup fit and the mesh correction use
  Fast-FoundationStereo depth from the grey pair (cameras C and B).
- The difference is which image the tracker sees. Purple's FoundationPose output is `T_A_from_scan` "at B/C time f
  (A image = A(f+1))" (`mesh_common.py`), so it ran on **colour camera A**, one frame shifted [I, strong; the driver
  is not public]. SAM 3 masks exist for A, B and C.
- Ours ran FoundationPose on **grey camera C** with grey-textured meshes (`pipeline/perc2.py`: "gray textures: the
  ego stereo cameras are monochrome"; `pipeline/mesh_color.py`). Colour camera A was used only for MediaPipe hands.
- Our own records show colour matters for detection: Grounding DINO 10/10 objects in colour against 7/10 in grey;
  OWLv2 4/10 in grey and swapped the twin cups; SAM2 masks failed on the beige cup and the white board.
- **[H]** FoundationPose on colour camera A (colour-textured meshes, stereo depth reprojected into A, the a[k+1]-b[k]
  pairing) tracks better than our grey camera-C run. Falsifier: the 20 public episodes, registered AUC against mocap,
  same meshes; pre-registered pass at mean +0.01, no episode worse by 0.01. About 30 GPU-minutes [E].
