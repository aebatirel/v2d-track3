[← Index](../README.md) · [Summary](../00-summary.md) · [← 08](08-architectures-accuracy.md) · [10 →](10-synthesis.md)

# 09 — Resourceful + innovation architectures for V2D Track 3 (design + adversarial review)

Status: COMPLETE v1 (2026-10-04). Research/design only: nothing installed, run on a GPU,
downloaded or edited outside this file; no SlamDunk code read or reused.
Inputs: [track3-requirements.md](../track3-requirements.md), `research/01-baseline-dissection.md`, [02-error-budget.md](02-error-budget.md),
[03-lit-perception.md](03-lit-perception.md), [04-lit-transfer.md](04-lit-transfer.md), [05-alternatives.md](05-alternatives.md) (cited as 01..05 + section).
Also read (read-only) in the session scratchpad: participant kit v2 (`kit_v2/`), and two in-progress
analyses by other agents (`analysis_timing_map.py`, `meshframe/`), cited as [other-agent, U].

Lens: leaderboard score per GPU-dollar and per engineering week, plus the Industry Innovation
criteria (economic viability, data flywheel, challenging an assumption, complexity reduction / less
capture effort), with licence-clean components where possible.

Legend: [V] verified in a primary source (here or in 01-05, which are cited); [U] unverified;
[H] our hypothesis (untested); [E] estimate (arithmetic on stated assumptions).

---------------------------------------------------------------------------------------------------
## 0. TL;DR

1. Three architectures. Each ends in one FlashCHORD checkpoint per episode, run by the pinned
   official evaluator. All three share one licence-clean stereo "spine" (section 2):
   - **R1 Hands-Free.** Object-first. Robot-native Sharpa grasps are synthesised in the evaluator's
     own physics. No 3D human hands and no MANO.
   - **R2 Sim-Verified and Distilled.** The evaluator's physics acts as the estimator for occluded
     or implausible spans. It samples an executed trajectory, distils it into the actor, then runs
     a short RL fine-tune instead of 250M steps from scratch.
   - **R3 Room Memory.** Cross-episode amortisation: an object identity library (CD-O meshes and
     the spoon), room priors, a tracker fine-tuned in-domain on public GT, warm-started policies,
     and incremental resubmission.
2. Ranking as standalone designs: **R1 > R3 > R2**. Recommended build:
   - weeks 1-2: spine + R1 + R3's object library (needed anyway for CD-O and the unscanned spoon);
   - R3 warm starts only if K3b passes;
   - R2 only in its "repair failing windows" form, and only if K2a-c pass (section 7).
3. Three cross-cutting gates surfaced while writing this note. Resolve them **before any RL GPU-hour**:
   - **G1 timing.** The kit packer numbers rows by `reference_frame = step + start_frame` [V kit
     `tools/pack_submission.py`], and the export's `reference_frame` indexes the *resampled*
     reference [V 01 C.10]. With the default `motion_speed: 0.5`, the resampled reference has
     about 2N steps. The scored rows f = 0..N-1 would then be sim steps that replay roughly source
     frames 0..N/2 [U: consequence computed by another agent's in-progress script]. Writing the
     measured 20.00 fps (02 §1) with `motion_speed: 1` would make the mapping exact [U, same
     script], but needs organiser confirmation. Real-speed playback is harder to track.
   - **G2 cup anchor.** In 6 of 20 eval episodes (8, 10, 14, 20, 32, 33), object slot 0 is a cup
     [V kit `track_3_evaluation_objects.json`: order = object_slot]. The cups are near-rotationally
     symmetric (principal moments within 1%, 02 §1).
     - Their azimuth about the symmetry axis is not observable from shape.
     - The scorer turns an azimuth error into a rotation of the whole scene about the cup
       (02: 10° → AUC 0.71 / MP-SR 0.40; 30° → MP-SR 0).
     - Unless an appearance cue fixes the azimuth (print, seam, possibly mocap markers), this is a
       lottery for every team.
     - Ask the organisers, look for cues at zero GPU cost, and do not sink weeks into it.
   - **G3 own-mesh frame convention.** The skew-sign rule hypothesised in 02 is not universal:
     wooden_piece_2 has negative x-skew [other-agent, U]. This decides the spoon's frame in 10/20
     eval episodes.
4. Cost [E] (central ≈ $1 per GPU-hour on L40S/A100-class; range $0.7-2.2):

   | | Full 20-episode submission |
   |---|---|
   | Baseline-style | ≈ 65 GPU-h |
   | R1 | ≈ 70 GPU-h |
   | R2 | ≈ 30-50 GPU-h if distillation works, ≈ 90 if not |
   | R3 | ≈ 30 GPU-h once its warm-start pool exists, ≈ 70 the first time |

   - A 4-week program costs 300-500 GPU-h, about $300-1,100.
   - RL dominates the cost. Perception iterations against mocap cost only 3-7 GPU-h per 20-episode
     pass. The main resourceful levers are therefore:
     - iterate perception without RL;
     - gate references with frame-0 settle and VOC-0 replay checks;
     - rank variants with short-RL proxies, validated by rank correlation;
     - retrain only changed episodes;
     - use spot instances with FlashSAC resume.
5. Licence. An OSI-code / permissive-weights configuration exists for R1 and R2:
   - stereo: RAFT-Stereo or IGEV (MIT), or CREStereo (Apache-2.0);
   - masks and detection: SAM2.1, OWLv2 / Grounding DINO;
   - hands: MediaPipe;
   - geometry and optimisation: Open3D, PyTorch3D, gtsam;
   - simulation and training: MuJoCo-Warp / Newton, FlashCHORD.

   Its accuracy cost against FoundationPose / FoundationStereo (both NC) is unmeasured. Keep the NC
   parts behind flags and measure the "cost of compliance" on public episodes.

---------------------------------------------------------------------------------------------------
## 1. Facts the designs rest on

### 1.1 What is scored and how errors propagate (02 §0, §4; 01 C.10)
- Score = **simulated object trajectory** from the official evaluator vs mocap, per episode, then
  averaged. Evaluation conditions [V 01 C.10]:
  - reset to exact reference frame 0;
  - VOC 0;
  - deterministic actions;
  - 1 world;
  - physics taken from the checkpoint config.
- Error model [H, 04 §10, 05 §0]: err(sim, mocap) ≈ err(ref, mocap) ⊕ err(sim, ref).
  - err(ref, mocap) is measurable on the 20 public episodes with **no RL**.
  - err(sim, ref) is partly predictable with **no RL** via physical replay at VOC 0 (05 §1, [V]
    config exists).
- Budget priorities (02 §4):
  1. Never lose a manipulated object. Freezing at onset costs 0.45-0.55 AUC and gives MP-SR ≈ 0.
  2. One consistent world frame. Drift was the largest leave-one-out gain; 5 cm drift = −0.20 AUC.
  3. Slot-0 frame-0 pose. 3 cm → MP-SR 0.63; 10° → 0.68. Average it over the static prefix
     (13-117 frames, median 39).
  4. Noise ≤ 0.5 cm/axis and ≤ 2°, smoothed zero-phase. Lag costs ~1 AUC point per frame at
     1 frame and 6.7 at 3 frames.

  Cheap (do not over-invest): scale ≤ 5%; non-anchor orientation ≤ 15°; ADD < 1 cm (AUC dead
  zone). Policy tracking error spends the same 3 cm / 30° budget.
- Body-frame offsets: our mesh frame vs the organisers' scan frame.
  - For slots > 0, the error is constant on every frame.
  - For slot 0, the frame-0 alignment conjugates the error into later motion: a rotation offset θ
    gives 2·sin(θ/2)·|d| on a displacement d [H, 05 §1].

  The frame convention is as important as tracking (G2, G3).

### 1.2 Fixed vs free (requirements; 01 C.10, F.3; 05 §0)
- Fixed:
  - learner type (FlashSAC/PPO);
  - the 4 digested evaluation files;
  - evaluation overrides;
  - physics, which we keep at recipe defaults;
  - the evaluator pin `8c778f90`.
- Free (ours):
  - reference parquet: object poses, robot-space hand reference, contacts, fps;
  - object meshes/URDFs (mass/inertia honest);
  - support USDA, generated from video evidence;
  - training config: rewards, curriculum, resets, world count, budget, warm start;
  - per-episode checkpoints.
- FlashCHORD never reads MANO fields [V 05 §1]. A robot-space hand reference synthesised directly
  is valid input.
- Kit facts used here [V kit v2]:
  - `track_3_evaluation_objects.json` gives object names per eval episode **in slot order**.
  - CD-O meshes are named `<episode>/<object_name>.glb`.
  - The packer matches rows by (world, frame, object) using the evaluator's `reference_frame`.

### 1.3 Cross-cutting gates (block RL spend until resolved)
| Gate | Evidence | Why it blocks GPU money | Cheapest resolution |
|---|---|---|---|
| G1 timing / row mapping | kit packer note [V]; 01 C.10 [V]; consequence [other-agent, U] | Every policy trained at the wrong speed/mapping is wasted. Real-speed playback (if required) changes RL difficulty for all designs. | Organiser email. Then 1 public episode: evaluator export → packer → check frame alignment against mocap with a GT-reference policy (Exp 0, 05 §2) |
| G2 symmetric-cup slot 0 (6/20 eval eps) | kit slot order [V]; 02 cup moments [V]; 02 spin table [V] | Effort on cup-anchor accuracy may be unrecoverable. Potentially ≈ −0.15 to −0.2 mean AUC for everyone [E: 6/20 eps × ~0.5-0.6 AUC loss] | Zero-GPU: inspect public cup scans/videos for azimuth cues. Ask whether the scorer could use a non-symmetric anchor or ADD-S for cups |
| G3 frame convention of own meshes | 02 §0 [V for 2 meshes]; sign rule not universal [other-agent, U] | Spoon frame in 10/20 eval episodes. A wrong sign is a constant offset of several cm (slot 1) or a conjugated error (slot 0, eps 35-37) | Finish the 10-scan census (owner: mesh-frame agent); ask organisers for the spoon convention |
| G4 rules | requirements, 03 Q12, 05 §4 | Licence and pooling decide which variants are submittable | Organiser email (section 9) |
| G5 RL wall-clock / VRAM | 01 C.9: unmeasured; ≥ 46,000 MiB free for 4,096 worlds | Every GPU-h estimate below scales with it | 10M-step timing on 2-3 GPU types (Rung 1) |

### 1.4 Cost anchors and model [E unless marked]
- Anchors:
  - CHORD: ~2 h per sequence on one L40S at 2,048 envs [V 04 §1].
  - FlashCHORD recipe: 4,096 worlds, 250M steps, ≥ 46,000 MiB free [V 01 C.1, requirements].
    An L40S is borderline at 4,096 worlds.
  - Baseline reconstruction: 10-15 min per segment [V requirements].
  - Rental prices (third-party, verify at rental): L40S $0.72-1.30/h; A100-80GB $0.80-2.20/h;
    H100 $1.89-4/h [U requirements].
- Model: P_RL = 3 GPU-h per full-budget policy (range 2-4); $1/GPU-h central; evaluator plus
  packing ≈ 0.05 GPU-h per episode.
- Iteration tiers, per variant tested:

| Tier | What | GPU-h | Turnaround |
|---|---|---|---|
| I0 | perception only, 20 public eps, kit scorer on err(ref, mocap) | 3-7 | hours |
| I1 | I0 + reference build + frame-0 settle + VOC-0 replay on 20 public eps | +1-4 | hours |
| I2 | short-RL proxy: 6 dev eps × 50M steps × 1 seed | 2.4-4.8 | ~half day if parallel |
| I3 | full RL on dev: 6 eps × 2 seeds | 24-48 | 1 day on 2-4 GPUs |
| I4 | full public validation: 20 eps × 1 seed | 40-80 | 1-2 days |
| S | eval submission: 20 eps (architecture-specific, section 6) | 20-100 | 1-2 days |

- Resourceful levers common to all designs:
  - **(a) Iterate perception at I0.** The reference error is a floor no policy can beat.
  - **(b) Gate every reference at I1 before RL.** This catches frame-0 penetration, missing
    supports, and objects that fall at reset.
  - **(c) Use I2 only after its rank correlation with I3 is shown** (Spearman ≥ 0.6 on ≥ 8
    variant-episode pairs). Otherwise I2 is noise.
  - **(d) Content-hash each episode's parquet, assets and training config.** Retrain only changed
    episodes; checkpoint digests stay valid for unchanged ones.
  - **(e) Spot/preemptible GPUs.** FlashSAC `state_*.safetensors` is resumable [V 05 §0]; set
    checkpoint cadence to ~10M steps (recipe default 10,000,384 [V 01 C.1]).
  - **(f) Benchmark env-steps per dollar on L40S (2,048 worlds), A100-80 and H100 (4,096) before
    renting in bulk.** World count is a training choice, not physics [H; keep it out of the
    evaluation composition].
  - **(g) Adaptive seeds.** Spend a second seed only where the GT-free in-sim err(sim, ref) or the
    replay gate flags failure, not uniformly.

### 1.5 Licence screen used here
- Winners must release their own code under Apache-2.0 [V FAQ via 03 §10]. Pretrained models and
  external data are allowed [V FAQ].
- Kaggle requires that software needed to generate the solution be under an OSI-approved licence
  that does not prohibit commercial use [U: standard Kaggle wording per secondary sources; the
  track rules page is JS-rendered and was not re-read].
- Classes used below:
  - **[OSI]** code and weights OSI/permissive;
  - **[W]** only weights non-OSI but commercial-OK (model licence);
  - **[NC]** non-commercial code (rule risk A1 in 03 §0);
  - **[M]** MANO-dependent.
- New checks this session (GitHub API LICENSE, 2026-10-04):
  - OSI/permissive: RAFT-Stereo MIT; IGEV MIT; CREStereo Apache-2.0; DEFOM-Stereo MIT code;
    MediaPipe Apache-2.0 (hand-landmarker weights Apache-2.0 per a third-party model zoo, [U]);
    gtsam BSD; Open3D MIT; PyTorch3D BSD; CoACD MIT; mujoco_warp Apache-2.0; newton Apache-2.0;
    TAPIP3D Apache-2.0.
  - Not usable: **BODex** ships an "NVIDIA License" (NC family, [U] exact terms); **DexGraspNet** has
    no LICENSE file. Grasp synthesis must be our own code.

### 1.6 Innovation criteria and panel
- Criteria: economic viability, data flywheel, challenging an assumption the field treats as
  fixed, and complexity reduction / less capture effort [V 05 §1].
- Panel: Hao Su, Yunzhu Li, Louis Lian, Changliu Liu, Yuting Ye, Kaifeng Zhang (Sharpa), Javier
  Romero [V 05 §1].
- Note: the panel includes hand-model and hand-tracking researchers (Romero, Ye). A "no 3D human
  hands" pitch must be framed as complementary and evidence-based (precedents: DexImit, CHORD's
  own force-closure fallback), not dismissive.
- Baseline reference points for "complexity" claims:
  - Ego path: 9 Docker images, ~135 GB, ~30 min build [V requirements].
  - About 11 learned models: AnyCalib/GeoCalib, MoGe-2, DROID-SLAM, WiLoR, HaMeR/HaWoR, Grounding
    DINO, SAM2, SAM3D, FoundationPose, gsplat refinement, plus MANO [V 01 A.1].
  - NVIDIA's own demo needed manual scaling and an 8.4° levelling correction [V 01 A.2].
  - NVIDIA's HOI object reconstruction expects a dedicated object scan orbit of ≥ 600° [V 01 E].

---------------------------------------------------------------------------------------------------
## 2. Shared spine (used by R1, R2 and R3; dissected once here)

Design rule:
- One clip = one offline batch problem in a metric, table-anchored world.
- Every component has an [OSI] default and an optional "accurate" flag for an [NC] or [W]
  alternative, so the cost of compliance is measured rather than guessed.

| # | Step | Inputs → outputs | Method (default) | Alternatives | vs baseline: ADD / CUT | Licence |
|---|---|---|---|---|---|---|
| S0 | Ingest + rig model | 3 MP4s, calibration JSON, per-frame `capture_time` → frame-indexed colour (rotated 180°, K' with cx'=W−1−cx, cy'=H−1−cy), undistorted; rectified mono pair; per-frame times; rig extrinsics | OpenCV rational-model undistort + `stereoRectify` from factory calibration; associate by `frame_index` (02 §1) | `v2d_mv_preprocess` (EDEX R,P; 8 vs 14 distortion coefficients, 01 E) | ADD rotation fix, factory K, measured 20.00 fps. CUT AnyCalib, GeoCalib intrinsics, MoGe intrinsics, median-stabilised K | [OSI] |
| S1 | Stereo depth | rectified pair → metric depth + left-right-consistency confidence on mono-left; depth reprojected to colour; static-background cloud | RAFT-Stereo or IGEV [OSI]; object ROIs at full resolution, background at half resolution | TAO FoundationStereo [W]; FoundationStereo ViT-L / Fast-FS [NC]; SGBM floor [OSI]; MoGe-2 [OSI] scale-aligned to stereo only as hole filler | ADD the whole stereo path (03 H-fit-1: HOT3D in-hand lifting recall@10 cm 96.8 stereo vs 30.2 mono). CUT MoGe as the metric source | [OSI] default |
| S2 | Masks + identity | rotated colour (+ mono-left), kit object list (names, slot order) → per-object masks, visibility, hand masks, occlusion order (hand in front) | OWLv2 / Grounding DINO boxes → SAM2.1 video propagation; re-prompt when mask area or score collapses; identity check by 3D position from S1; hand prompts from MediaPipe palm boxes | SAM 3.1 text/exemplar prompts [custom SAM License; MOSEv2 +12.4 J&F, 03 §3]; Cutie [OSI] | ADD multi-object ids, re-prompting, hand-occlusion labels. CUT one-frame top-1 DINO box, WiLoR-silhouette prompts [NC] | [OSI] default |
| S3 | Camera, table, gravity | S1 depth + S2 masks + mono frames → camera_to_world (metric, per frame), table plane (height, normal), gravity = −normal, static background model | [H] "Table-anchored registration": masked features (ALIKED/DISK + LightGlue [OSI]; avoid SuperPoint weights [NC]) → stereo PnP-RANSAC to keyframes → small BA (gtsam [OSI]); RANSAC table plane on static stereo points | DROID-SLAM stereo with mask weights [OSI]; cuVSLAM/PyCuSFM [custom, not OSI]; ORB-SLAM3 [GPL: keep out of Apache release]; GeoCalib [OSI] as a gravity cross-check on the upright colour image | ADD metric stereo camera, dynamic masks, table-plane gravity. CUT monocular DROID with MoGe-ratio scale, thinnest-PCA "up" heuristic, manual levelling | [OSI] |
| S4 | Whole-clip object estimator | S0-S3 + object mesh (S5 or R3 library) → per-object world SE(3) trajectory + per-frame covariance + state label (rest/moving) + slot-0 anchor | Per-frame init: depth-ICP + silhouette render-and-compare (PyTorch3D [OSI]). Then a batch factor graph: **rest segments = one constant pose**; moving segments = SE(3) spline with confidence-weighted measurements; resting on the table at rest; no inter-object penetration; spin about a detected symmetry axis held constant (not measurement-driven); slot-0 anchor = robust mean over the static prefix | FoundationPose per-frame [NC] (best evidence: HO-Cap ADD 89.3 vs MegaPose 67.1, 03 §9) as the accurate flag; MegaPose refiner [OSI]; BundleSDF [NC]; 6DOPE-GS (code unreleased) | ADD batch world-frame estimate, priors, multi-object, anchor averaging. CUT camera-frame ESKF, occlusion-blind IoU re-registration, gsplat joint refinement | [OSI] default |
| S5 | Own mesh per episode (CD-O + sim asset) | masks, depth, S3 cameras, S4 poses → watertight mesh in canonical frame; URDF (mass = volume × density class); CoACD-friendly collision mesh | [H] **Static-prefix bootstrap**: while objects rest (median 39 frames), head motion gives multi-view stereo of each object in the world frame → partial TSDF (Open3D [OSI]); then object-frame fusion while held, using S4 poses (S4↔S5, 2 rounds); completion by **surface-of-revolution fit** for cups/lid/pot body [H]; parametric spoon (bowl + tapered handle) [H, 03 §7]; generative only for unseen non-symmetric parts | SAM 3D Objects [custom SAM License, gated]; TRELLIS.2 [MIT code, nvdiffrast NC dependency]; BundleSDF [NC] | ADD multi-view, metric, canonicalised, mass from volume. CUT single-view SAM3D + one-frame MoGe scale search, fixed 0.3 kg / 0.001 inertia | [OSI] default |
| S6 | Reference writer + gates | object trajectories, assets, table plane, **hand reference (architecture-specific)** → ManoSharpaData parquet (B bodies, measured fps, contacts), URDFs, support USDA; gate report | Write fields per 01 C.11. Support = horizontal disks at the measured table height under rest poses (prim rotation ignored, 01 C.8). Gates: g1 schema; **g2 frame-0 settle** (1 s sim at VOC 0, hands at reference: object moves < 3 mm, no penetration); **g3 VOC-0 physical replay** (`replay.py replay=physical`, 05 §1); g4 resolved-config diff vs recipe physics | baseline loader + `support_recon.py` still-run disks (fail under jitter, 01 B.5) | ADD gates, true fps, B > 1, video-justified supports. CUT 30 fps constant, thinnest-PCA ground alignment | [OSI] |
| S7 | Train → official eval → pack | parquet + assets → FlashSAC checkpoint per episode → pinned evaluator → `pack_submission.py` / `pack_reconstruction.py` | Recipe defaults for physics. Training-only changes (01 F.3; 04 §10): earlier frame-0 resets, `voc_decay_steps` 0 late, size-scaled object keypoints [H], resumable checkpoints, content-hash incremental retrain | PPO learner (also accepted) | ADD multi-body, eval-matched resets, compliance diff. CUT nothing in evaluation | [OSI] |
| S8 | Harness + monitors | runs → decomposition table per episode: err(ref, mocap), err(sim, ref), err(sim, mocap), gate stats, GPU-h, wall-clock | kit `metric_code/track_3` (02 already reproduced it, bit-identical); GT read only by evaluator scripts | — | ADD everything (the baseline has no local validation loop) | [OSI] |

**Boundary notes (ideas at each interface; [H] unless marked):**
- S0→S1:
  - Carry a per-episode colour↔mono time offset and a rolling-shutter flag (03 Q2). A
    0.15-frame skew is harmless; 1 frame is a 1-AUC-point lag.
- S1→S3/S4:
  - Pass disparity *confidence*, not just depth.
  - Edge fattening on the white pot and the thin spoon is the main systematic bias (02 §3), so
    down-weight pixels within ~3 px of mask edges.
- S2→S4:
  - Pass the occlusion order (hand-in-front masks). The estimator then treats "occluded" as
    missing data, not as evidence of a pose change. This fixes the baseline's IoU-triggered
    re-registration (01 A.4.3).
- S3→S4:
  - Static mocap objects (dish rack: < 0.5 cm motion, 02 §1) are a free GT-free drift monitor in
    our own world frame. If they appear to move, the camera, not the object, is wrong.
- S4→S6 (R1/R2):
  - Pass rest/moving labels and onset frames.
  - Grasp timing (R1), MPC windows (R2) and support disks (S6) all key off them.
- S5→S6:
  - Pass a mesh *confidence* map (observed vs completed surface). Grasps (R1) should prefer
    observed surface.
- S6→S7:
  - The gate report is the RL admission ticket: no gate pass, no GPU-hours.
  - Log the gate metrics, because they are candidate GT-free predictors of final score
    (validate the correlation at I3).
- S7→S8:
  - Store per-episode in-sim metrics against our own reference (01 C.10). These are the GT-free
    proxy for adaptive seeding.

**Spine cost [E]:**
- GPU-h per episode:
  - S1 ~1-2 GPU-min;
  - S2 ~2-4;
  - S3 ~1-3 (mostly CPU);
  - S4 ~3-8;
  - S5 ~3-6.
- Total ≈ 10-20 GPU-min per episode, i.e. **3-7 GPU-h per 20 episodes**, comparable to the
  baseline's 10-15 min per segment.
- Engineering ≈ 4-5 person-weeks (S0-S3 ~2, S4 ~1.5, S5 ~1, S6/S8 ~1).

**Spine red flags:**
- The OSI tracker (ICP + silhouette) may be far below FoundationPose under hand occlusion (HO-Cap
  MegaPose vs FP gap of 22 ADD points). This is the single biggest unknown cost of compliance.
  Measure it at I0 on public episodes (03 Q3) before deciding.
- The static-prefix bootstrap needs head motion during the prefix. Its magnitude is unknown (no
  camera pose in public GT); measure it from S3 at I0.

---------------------------------------------------------------------------------------------------
## 3. R1 "Hands-Free": object-first references with robot-native grasps

**Assumption challenged:** "Video-to-robot transfer needs the human hand reconstructed in 3D
(MANO) and retargeted."

**Thesis [H]:**
- The scored quantity is the object.
- FlashCHORD needs *a* physically consistent Sharpa reference that can produce the observed object
  motion. It never reads MANO fields [V 05 §1].
- Reference physical consistency is the largest published transfer lever (04 §9.1):
  - Regrind: interaction-mesh retargeting ~99% vs IK+RL 0-3%;
  - V2P-Manip: 0% → 79% with geometric constraints;
  - C2Dex: 18% → 58%.
- Synthesising the hand in robot space gives that consistency by construction:
  - no frame-0 penetration (the baseline's MANO fingers often start inside the object, 01 B.1);
  - exact contact labels for the CWS reward. CHORD reports +0.14 AUC / +0.28 MP-SR from contact
    guidance with clean contacts [V 04 §1].
- Split of roles: **"the object tells when, the hand tells where."**
- R1 is *not* object-only. It keeps dense contact guidance, so CHORD's evidence against object-only
  rewards (H2S2R 0.730 vs 0.918 AUC) does not apply directly.

### 3.1 Steps
| # | Step | Inputs → outputs | Method | Alternatives | vs baseline: ADD / CUT | Licence |
|---|---|---|---|---|---|---|
| R1.0 | Spine | S0-S5 | section 2 | — | — | [OSI] default |
| R1.1 | 2D/stereo hand cues | upright colour + mono views → per side, per frame: palm centre (3D, triangulated), palm normal, handedness, confidence | MediaPipe 21 landmarks per view; triangulate over colour + mono pair (baselines 3.74 / 7.5 cm). [E] With 3 px landmark noise, mono-pair depth error ≈ 0.5²·3/42.2 ≈ 1.8 cm at 0.5 m: enough for "where", not for fingers | SAM2 hand masks + mask centroids with stereo depth; WiLoR detector [NC]; Qwen2.5-VL keyframe script [U licence] | ADD stereo-triangulated hand cues. CUT WiLoR, HaMeR/HaWoR, Dyn-HaMR, ViPE, MANO, `align_hands` depth shift, MANO contact labels | [OSI]; weights [U] |
| R1.2 | Interaction segmentation | S4 rest/moving labels + onsets, R1.1 palm-object distance → per object: segments {rest, held-L, held-R, held-both, push/tool}; regrasp and handover events | Object kinematics decide *when* (onset/offset with hysteresis on the smoothed trajectory); the nearest confident palm within ~8 cm of the object surface decides *which side*; minimum segment length | VLM schedule (DexImit uses Qwen3-VL [V 05]); hand-object contact detectors (licences unchecked) | ADD explicit interaction schedule (baseline has none) | [OSI] |
| R1.3 | Grasp synthesis per held segment | object mesh + confidence map (S5), segment trajectory T_obj(t), side, palm prior, table plane, other objects → top-k Sharpa grasps G (wrist pose in object frame, 22 finger joints, contact points / normals / part ids) + scores | Our own batched sampler inside FlashCHORD's Newton/MuJoCo-Warp scene (Sharpa model, recipe physics):<br>(i) wrist samples on an approach cone around the palm prior;<br>(ii) scripted finger synergy closes to contact;<br>(iii) score with FlashCHORD's own wrench-support code (`objectives/wrench.py`, 01 C.2) against the segment's required wrench (gravity + m·a from T_obj);<br>(iv) collision check of wrist(t) = T_obj(t)·G against the table and other objects over the whole segment, including placement;<br>(v) **carry test**: hand driven along wrist(t), object free at VOC 0, slip < 5 mm / 5° | DexGraspNet (no LICENSE ✗); BODex (NVIDIA License ✗); ManiDext trajectory-conditioned diffusion [U]; force-closure optimisation as in DexImit (code not stated) | ADD whole stage | [OSI] (own code; FlashCHORD Apache) |
| R1.4 | Robot reference composition | segments + chosen grasps → robot_{L,R} wrist pose (T,7), finger joints (T,22), FK frames, contact fields | Hold: wrist(t) = T_obj(t)·G. Pre-grasp pose reached by onset − 10 frames; fingers close over ~8 frames, ending at onset − 2. Release after the object rests: open, then retreat. Idle hand parked ≥ 15 cm from objects. Min-jerk collision-checked transit. **Frame 0: hands open and contact-free.** Synthesised contacts written into `mano_{side}_object_contact_*` | Hybrid: per-segment fallback to repaired human-hand reference (R3.4 or baseline) | ADD robot-space synthesis. CUT `ego_recon_to_sharpa.py` IK, `mano_to_robot_scale`, opt-in de-penetration flags | [OSI] |
| R1.5 | Gates + re-selection | parquet → g1-g4 report; on carry/replay failure, try the next grasp, then split the segment, then fall back to the hybrid | S6 gates, applied per segment | — | ADD | [OSI] |
| R1.6 | Train, eval, pack | S7 | Recipe physics. CWS weight 10 kept (contacts now exact). Hand-imitation weight may be raised, since the reference is feasible [H]. Size-scaled object keypoints [H] | `force_closure` reward (unneeded with exact contacts) | — | [OSI] |

### 3.2 Boundary brainstorm [H]
- **R1.1→R1.2:**
  - Do not trust 2D-hand timing. Grasp onset is better measured from the object (it starts
    moving). The hand supplies only side and approach direction.
  - This makes R1 robust to the heavy finger occlusion that breaks MANO fitting.
- **R1.2→R1.3:**
  - Pass the segment's wrench and clearance envelope: peak acceleration, rotation rate, placement
    target, nearby objects. The grasp is then task-aware (e.g. a cup going into a rack slot must
    be held away from the slot side).
- **R1.3→R1.4:**
  - If no grasp survives a whole segment, the human probably regrasped. Split at the largest
    wrist-infeasibility point.
  - If splitting fails, use the hybrid fallback only for that segment. Log the event (flywheel
    signal).
- **R1.4→R1.5:**
  - The residual action envelope (wrist position clip 0.2 m, orientation 1 rad, fingers 1 rad;
    01 C.1) means the reference only has to sit near a feasible solution.
  - Use the replay gate as a feasibility check, not a requirement of perfect open-loop tracking.
    With a soft wrist (kp 25 N/m), open-loop replay is expected to drift.
- **R1.5→R1.6:**
  - Per-segment replay survival suggests a per-segment reset curriculum: more resets inside hard
    segments.
- **New:**
  - Bimanual episodes (pot + lid ep 1; sweeper + dust pan eps 19/30) are synthesised hand by hand,
    then jointly collision-checked.
  - Spoon: prefer a power grasp on the observed handle region. A pinch on a hull that CoACD may
    wrap poorly is fragile (01 C.12).

### 3.3 Error-budget mapping
| Budget item (02 §4) | R1 mechanism | Expected effect [H] |
|---|---|---|
| Lost / dropped object (−0.45 to −0.55 AUC) | carry test; exact contacts; no frame-0 penetration | fewer sim drops and ejections at grasp |
| Static object knocked (MP-SR needs *every* object < 3 cm) | idle hand parked; collision-checked approach | protects dish-rack episodes (14, 15, 16, 28, 30) |
| Policy lag | fingers closed before object onset | removes the "catch-up" lag (3 frames = −0.067 AUC) |
| Drift, anchor, scale, jitter | spine only (S3, S4) | unchanged vs other designs |
| Non-anchor orientation ≤ 15° (cheap) | do not chase. Size-scaled keypoints stop the 1 m-lever reward over-weighting rotation (04 §8) | small |

### 3.4 Cost [E]
- **Engineering:** R1.1 0.5 pw, R1.2 0.5, R1.3 1.5, R1.4 0.5; about 3 person-weeks beyond the spine.
  - Saves: repairing the human-hand stack (multi-view MANO fit, contact relabelling,
    de-penetration, retargeter fixes; 04 ideas 1, 2, 4, 9; ~2-3 pw).
  - Saves: the reconstruction containers (~135 GB) for hands.
- **GPU per episode:** R1.1 ~1-2 min; R1.3 ~3-10 min; gates ~2 min. About 2-5 GPU-h per 20 episodes.
- **Full 20-episode submission:**
  - spine 5 + R1 3.5 + RL 60 (40-80) + eval 1 ≈ **70 GPU-h (48-90) ≈ $50-200**;
  - with an adaptive second seed on ~30% of episodes, ≈ 88.
- **Per iteration of the R1 module:** I1 on 20 public ≈ 3-5 GPU-h; I2 3-5; I3 24-48.

### 3.5 Data flywheel
- **Grasp library.** Keyed by object identity and segment type, with sim-verified success
  statistics. The next video of the same object starts synthesis from the library: cheaper and
  better each time.
- **Robot-native demos.** Every processed video yields object trajectory + Sharpa hand trajectory
  + contacts + replay metrics, without any human hand model. This is training data for a
  generalist tracker (05 F) and works even where the hand is barely visible.
- **Failure mining.** Segments with no carry-stable grasp are auto-flagged. The cause is either
  physically implausible object motion (a perception error, which goes back to S4) or a missing
  skill (non-prehensile, which goes to R2 repair).
- **Capture effort.** One head-mounted stereo camera; no gloves, hand mocap or MANO calibration.

### 3.6 Red team
Failure modes, most likely first:
1. **Non-prehensile, tool or in-hand phases:**
   - sweeping (eps 19, 30: mini_sweeper + dust pan);
   - lid handling (1);
   - cup into rack slot (14);
   - planter assembly / insertion (25);
   - pouring (20).

   A rigid grasp plus a free SO(3) wrist covers carry, pour, flip and place. It does **not** cover
   in-hand reorientation, regrasps without release, sliding or pushing. Mitigation: per-segment
   hybrid fallback, triggered automatically by carry-test failure.
2. **The grasp blocks placement** (robot fingers hit the rack or the other object). Mitigation:
   the carry test spans placement with all scene objects; rank grasps by clearance.
3. **Onset misestimated** (S4 noise): the reference moves the object before the fingers close.
   Mitigation: hysteresis; close early; the replay gate catches it.
4. **Thin spoon** (10/20 eval eps): handle ~1-2 cm; CoACD 0.05 hull quality; roll unobservable.
   Mitigation: power grasp; make our own collision mesh watertight so CoACD decomposes it well
   (honest geometry, no thickening).
5. **Bimanual collisions** between two independently synthesised hands. Mitigation: joint check.
6. **Pitch risk with a hand-centric panel** (1.6). The score does not care, but the innovation
   award might.

Evidence against R1:
- CHORD's object-only comparator lost 0.19 AUC on clean mocap [V 04]. Mitigated because R1 keeps
  exact contact guidance.
- DexImit-style synthesised grasps reached 52-100% sim success over three tasks. Multi-object
  stacking was weakest (52%) [V 05].

**Cheapest killing experiments:**
- **K1a** (no RL; ≈ 3-5 GPU-h after ~1 pw of R1 code).
  - Setup: 6 public dev episodes, one per family (Pan_Solo, Pot_with_lid, Cup_In_Dish_Rack,
    Water_Can_Blue_Cup, Dust_Brush, Planter_Stand), same object reference for both arms.
  - Arms: (a) baseline retargeted hands with the official de-penetration/smoothing flags on;
    (b) R1 synthesised grasps.
  - A diagnostic third object source, the mocap object reference, is labelled "oracle, never
    submitted".
  - Measures: g2 frame-0 settle displacement; g3 replay time-to-failure; ADD vs reference.
  - **Kill R1** if (b) fails the carry test on more than 1/3 of held segments, or is worse than (a)
    on replay survival in ≥ 4/6 episodes.
- **K1b** (I2 7 GPU-h if the proxy is validated, else I3 ≈ 72 GPU-h).
  - Equal-budget RL, (a) vs (b), 6 episodes × 2 seeds.
  - **Kill** if (b) has lower mean AUC vs mocap on ≥ 4/6 episodes and no MP-SR gain.

**Licence exposure: lowest of the three.**
- No MANO, no WiLoR/HaMeR.
- MediaPipe [OSI; weight licence U].
- Own grasp code plus FlashCHORD wrench code (Apache).
- Remaining exposure sits only in spine flags (FoundationPose/FoundationStereo if enabled).

**Rule risks: low to medium.**
- The hand reference is not derived from 3D human hands. Hand estimation and retargeting are
  explicitly free [V requirements], but confirm that a synthesised robot hand counts as a
  reconstruction-derived reference.
- Simulator use is training-side only; physics unchanged.
- Contact fields are reference inputs we own [V 04 §1].
- Fully automatic, so no hand labelling.

---------------------------------------------------------------------------------------------------
## 4. R2 "Sim-Verified and Distilled": physics as the estimator, sample-then-distill

**Assumptions challenged:**
1. "The reconstruction is the reference."
2. "Each video needs ~250M steps of RL from scratch."

**Thesis [H]:**
- The reference should be the trajectory that the **evaluator's own physics can execute** and that
  best explains the video. Confidence-weighted observations decide where the video is trusted and
  where physics fills in (occlusion, implausible spans).
- Evaluation is a single deterministic rollout from exact frame 0 at VOC 0 [V 01 C.10]. A policy
  therefore only has to be robust in a tube around one executed solution.
- Find that solution by sampling, distil it, then fine-tune briefly.
- Precedents:
  - SPIDER: kinematic success 0.13 → 0.85 with annealed sampling + contact guidance [V 04 §4].
  - Grasp-and-Lift: 0.67 cm / 2.97° at ~557 s per sequence on CPU [V 05].
  - EgoEngine: on noisy ego data, MPC alone 0.20 vs RL 0.90, so use MPC as the reference and
    initialiser, not the final controller [V 04 §7].

### 4.1 Steps
| # | Step | Inputs → outputs | Method | Alternatives | vs baseline: ADD / CUT | Licence |
|---|---|---|---|---|---|---|
| R2.0 | Spine with uncertainty | S0-S5; S4 emits **measurements + calibrated covariances + visibility**, not only the smoothed trajectory | section 2; covariances calibrated on public GT (z-score check) | — | ADD calibrated uncertainty | [OSI] |
| R2.1 | Seed hand reference | R1 grasps (default) or baseline hands → parquet v0 | R1.1-R1.4 | baseline retarget [M] | — | [OSI] |
| R2.2 | Physics-in-the-loop optimisation | parquet v0 + measurements → **executed** trajectory from frame 0 at VOC 0: actions (FlashCHORD `residual_hand_pose` space), sim states, sim object poses, realised contacts | Our own annealed-covariance sampling MPC (DIAL-MPC / SPIDER idea, re-implemented). Worlds = samples (1,024-4,096); ~1.2 s receding windows; 16 annealing iterations; VOC annealed 1 → 0 across iterations (virtual contact guidance analogue); cost = Σ_t (1/σ_t²)·ADD-like distance(sim object, measurement) + contact consistency + action smoothness + termination penalty. Actions live in the policy's own action space, so the solution is directly imitable | SPIDER code [NC ✗]; CMA-ES keyframes (Grasp-and-Lift); gradient through MuJoCo-Warp (unstable with contacts) | ADD whole stage | [OSI] (own code; Newton / MuJoCo-Warp Apache) |
| R2.3 | Reference update | executed + observed → parquet v1 | Hand reference := executed wrist/finger targets. Contacts := realised sim contacts (filtered). Object reference: two variants, **E-gap** (executed only where σ_t is large) and **E-full** (executed everywhere). Pick by K2b | keep observed object, repair only the hand | ADD | [OSI] |
| R2.4 | Distillation | executed (obs, action) + perturbed rollouts → FlashSAC checkpoint initialiser | (i) Actor behaviour cloning on the executed trajectory plus noise-perturbed starts relabelled by short MPC replans (DAgger-lite, 10-50 starts). (ii) Or preload replay via `checkpoint.load_replay_path` and turn on `behavior_cloning_coefficient` (knobs exist [V 04 §8]; replay format compatibility [U]). Then (iii) a **genuine FlashSAC fine-tune** at VOC 0, frame-0 resets p ≈ 0.5, 25-50M steps, which writes the checkpoint | full 250M-step RL (fallback); PPO | ADD | [OSI] |
| R2.5 | Official eval + pack | S7 | — | — | — | [OSI] |
| R2.6 | Optional EM | rollout rendered into the 3 cameras vs masks / stereo depth → windows to re-optimise | 05 H render-and-compare scoring | skip | ADD | [OSI] |

### 4.2 Boundary brainstorm [H]
- **S4→R2.2:**
  - The whole design depends on honest covariances.
  - If S4 is over-confident in occluded frames, physics cannot fill.
  - If S4 is under-confident in visible frames, physics bias leaks in.
  - Calibrate z-scores per state (rest / held / occluded) on public GT.
- **R2.2→R2.3:**
  - Run a per-episode **physics-bias check**: mean executed-vs-observed distance on high-confidence
    frames.
  - Above ~1 cm, physics disagrees with evidence: the mass/inertia, the mesh or the support is
    wrong. Keep the observed reference and flag the episode for S5/R3 asset repair.
  - This turns the simulator into an **automatic perception and asset debugger**.
- **R2.3→R2.4:**
  - Size the perturbation noise for distillation to cross-GPU nondeterminism (K2a). The tube must
    be wider than what the organisers' reproduction hardware can introduce.
- **New: "MPC as curriculum."**
  - Store transitions from every annealing iteration (VOC 1 → 0) in the preloaded replay.
  - This mirrors FlashCHORD's VOC curriculum, but with good actions instead of exploration.
- **New: "physics as labeler."**
  - Frames where no executed motion can match high-confidence observations within 1 cm are
    automatic negatives (e.g. a "static" rack that moves means camera drift).
  - These label R3's tracker and confidence model for free.
- **New: G1 diagnostic.**
  - If G1 forces `motion_speed: 1`, peak speeds of 26-75 cm/s and 50-450°/s (02 §1) must be
    executed with a soft wrist (kp 25 N/m, 45 N).
  - R2.2 tells within minutes whether that is physically feasible. That is valuable to every
    design.

### 4.3 Error-budget mapping
| Budget item | R2 mechanism | Expected effect / risk [H] |
|---|---|---|
| Lost object through occlusion | physics carries the object with the hand instead of interpolating | fewer catastrophic gaps; risk of a confident wrong fill |
| Policy tracking share | the reference is executable by construction; distillation starts on-solution | err(sim, ref) → small; the main R2 gain |
| Static object knocked | contact and termination costs in the MPC | protects MP-SR |
| Systematic offset | **risk**: physics bias (friction 1.0, our mass, soft contacts) | 1 cm bias above the AUC dead zone ≈ −12.5 AUC points; the K2b gate exists for this |
| Drift, anchor, scale | spine only | unchanged |

### 4.4 Cost [E]
- **Engineering:**
  - MPC inside the FlashCHORD environment: 1.5-2.5 pw.
  - Distillation and FlashSAC initialiser: 1-1.5 pw.
  - EM: 0.5 pw, optional.
  - Total ≈ **3-4.5 pw** beyond spine + seed (R1).
  - [U] Whether FlashCHORD supports resetting worlds to arbitrary saved sim states is unverified.
    If not, every window replays from frame 0, which multiplies cost by about the number of
    windows.
- **GPU per episode:**
  - MPC: SPIDER reports 1.5-2.5 "FPS" [V 04 §4, its hardware; reading it as trajectory frames per
    second of wall-clock is U], i.e.
    ≈ 2-6 min for 262-524 frames. Allow 0.05-0.5 GPU-h.
  - BC: minutes.
  - Fine-tune at 10-20% of budget: 0.3-0.8 GPU-h.
- **Full submission:**
  - spine 5 + seed 3 + MPC 1-10 + BC 1 + RL 6-16 + eval 1 ≈ **17-36, call it 25-50 GPU-h with
    failures**, if distillation works;
  - **≈ 75-100 if it fails** (fallback to full RL with the repaired reference).
- **Per iteration:** MPC-only check on 20 public episodes = 1-10 GPU-h with no RL. Distillation
  variants at I2.

### 4.5 Data flywheel
- **Executable demos.** Every video becomes a physics-verified (state, action) trajectory in the
  official simulator. This is directly trainable data for a generalist tracker or BC prior (05 F;
  DexTrack's flywheel and OmniTrack's physics-consistent references are precedents [U]).
- **Warm-started MPC.** Episodes with the same object set reuse mean action sequences as the
  sampling prior, so later episodes get cheaper.
- **Perception and asset error labels.** Physics-disagreement maps label them for free (feeds R3).
- **Economics.** If K2c passes, the per-episode policy cost falls from 250M steps to ~25-50M plus
  minutes of MPC. That is the strongest "economic viability" number of the three designs.

### 4.6 Red team
Failure modes:
1. **Sim-vs-real bias.** Fixed friction 1.0, soft contacts (ke 1e3, 01 C.8) and our URDF mass make
   the executed motion deviate from the observed one. This is likeliest when lifting heavy items
   (pitcher, pot) with the soft wrist.
2. **Cross-GPU nondeterminism plus chaotic contact.** A narrowly distilled policy may diverge on
   the organisers' reproduction hardware, failing the reproducibility check (positions are
   provisional until reproduced [V requirements]). This applies to every design, but distillation
   narrows the robustness tube.
3. **Engineering overrun.** Own MPC + BC initialiser + replay format in 4 weeks, plus the
   arbitrary-state reset unknown.
4. **Local minima at grasp acquisition** (contact discontinuity). R2 needs a good seed (R1).
5. **BC compounding error and fine-tune unlearning.** FlashSAC's BN/RMSNorm and reward-normalisation
   statistics [V 04 §5] must be initialised consistently with a BC-initialised actor [U].
6. **Perception of "fitting the deterministic evaluator".** The final artefact is still a
   closed-loop FlashSAC policy produced by FlashSAC training. Disclose the method openly.

**Cheapest killing experiments:**
- **K2a** (≤ 1 GPU-h, no new code).
  - Run the official evaluator twice on one GPU and once on a second GPU type with one checkpoint;
    diff the trajectories.
  - **Kill the distillation route** if a baseline policy diverges by more than 1 cm within an
    episode across GPU types. MPC then survives only as reference repair. (This result is also
    vital for everyone's reproducibility.)
- **K2b** (2-5 GPU-h, after ~1.5 pw of MPC prototype).
  - On 3 public episodes, compare err(executed, mocap) with err(spine ref, mocap).
  - **Kill E-full** if executed is worse by more than 0.5 cm on ≥ 2/3. **Kill E-gap** if it does
    not improve the occluded windows.
- **K2c** (≈ 2 GPU-h + initialiser code).
  - Evaluate a BC-only initialised checkpoint through the official evaluator on 1 public episode.
  - **Kill distillation** if in-sim AUC vs our reference is below 0.5. Above 0.8, R2's economics
    are confirmed.

**Licence exposure: low.**
- Own code on Apache-2.0 stacks.
- **Do not vendor SPIDER** (CC BY-NC 4.0 [V 04 §4]).
- The DIAL-MPC repo licence was not checked; reimplement from the paper.

**Rule risks: medium.**
- Training-side use of the evaluator's physics is allowed: physics unchanged, VOC is a training
  assist that the recipe already uses.
- The submitted checkpoint must come from a real FlashSAC training run. Never submit a
  hand-assembled checkpoint.
- The "single command" reproduction must include the MPC stage and its seeds.

---------------------------------------------------------------------------------------------------
## 5. R3 "Room Memory": cross-episode amortisation

**Assumptions challenged:**
1. "Each video is an independent reconstruction + RL problem." The baseline builds a new
   single-view mesh, scale, gravity/level and a 250M-step policy for every clip.
2. "Objects need CAD/scans, or else single-view hallucinated meshes."

**Thesis [H]:**
- All 40 episodes share the rig, room, table and 11 objects [V requirements: interleaved indices,
  same sessions].
- Object recurrence (counts from the public parquets and the kit eval list) [V]:

  | Object | Public eps | Eval eps | Total |
  |---|---|---|---|
  | white_pot | 9 | 6 | 15 |
  | blue_cup | 5 | 5 | 10 |
  | plastic_dish_rack | 5 | 5 | 10 |
  | wooden_spoon | 0 | 10 | 10 |

- Treat the challenge as a deployment: build persistent memory once and amortise it. That memory
  is an object library, a room prior, an in-domain tracker, and a policy pool.
- R3 keeps a **human-derived** hand reference, so it is the low-variance counterpart to R1, using a
  licence-clean keypoint path by default.

### 5.1 Steps
| # | Step | Inputs → outputs | Method | Alternatives | vs baseline: ADD / CUT | Licence |
|---|---|---|---|---|---|---|
| R3.0 | Spine | S0-S4 | section 2 | — | — | [OSI] |
| R3.1 | Room prior | per-episode S3 tables / gravity → session-level table height, normal and uncertainty; stable rest poses per object | Robust pooling across episodes. Used as a soft prior in S3/S4 and for support-disk height. If pooling eval videos is disallowed, use public videos only (same room) | none (baseline levels per clip, manually for its demo) | ADD | [OSI] |
| R3.2 | Object identity library | per-episode partial models (S5) for every episode in which the identity appears → one fused, completed, canonicalised, CoACD-checked mesh + URDF per identity; versioned | Association by kit name [V] (colour separates blue/beige cups in ep 10). FPFH + ICP registration at metric scale (Open3D). Fused TSDF; revolution fit / generative completion only for unseen regions; canonicalise (G3); mass = volume × density class. **Emitted for CD-O on all 36 episode-object pairs** | per-episode meshes (S5); SAM3D per clip (baseline) | ADD whole stage. CUT per-clip SAM3D + scale search | [OSI] |
| R3.3 | In-domain tracker + confidence model | public videos + public mocap (training only) → fine-tuned refiner + per-frame error predictor feeding S4 weights | Labels: GT poses mapped into our camera frames through a per-episode alignment of our static-object estimates to GT (training time only, never at inference). Fine-tune a MegaPose refiner [OSI] or a small DINOv2-feature [OSI] correspondence head; train an error regressor. Leave-one-task-out validation | FoundationPose fine-tune [NC]; no fine-tune | ADD in-domain supervision (05 E) | [OSI] |
| R3.4 | Human-derived hands (licence-clean) | MediaPipe landmarks in colour + mono views → triangulated 21 keypoints → Sharpa joints, de-penetrated against the library mesh; contact labels | Own keypoint IK (FlashCHORD's `run_frame_ik` solves on joint positions [V 01 B.3]; adapting it to keypoints is [U]). SDF push-out against the library mesh. Contacts from fingertip-to-mesh distance + object-motion gate + minimum duration (contact_labels.py / SPIDER-filter style [V 04]). `force_closure` blend where contact confidence is low | HaMeR/WiLoR → MANO → NVIDIA retargeter with `--surface_project --smooth_reference` [M; WiLoR NC]; R1 grasps (composite) | ADD stereo hands, repair, robust contacts. CUT monocular depth shift, 1 cm raw proximity labels | [OSI]; weights [U] |
| R3.5 | Policy pool + warm starts | public-episode policies from I4 validation (trained on *our* reconstructed public references) → per eval episode, a parent with the same body count B (observation layout must match [V 05 §0]) and the nearest object set/task → resume for 25-50% budget | `training.resume`, `checkpoint_path` [V 05 §0]. Eval-internal chains for spoon groups: {spoon} 35→36→37; {pot, spoon} 3→5→6; {rack, spoon} 15→16; {cup, spoon} 32→33. Each root starts from the closest public parent | scratch training (baseline) | ADD | [OSI] |
| R3.6 | Incremental resubmission | content hashes of parquet / assets / config → retrain list | Retrain only episodes whose reference changed beyond a tolerance (e.g. Δ mean ADD > 3 mm); keep checkpoints and digests for the rest | full retrain each time | ADD | [OSI] |

### 5.2 Boundary brainstorm [H]
- **R3.1→S3:**
  - A per-episode gravity estimate more than ~1° from the session prior flags a bad camera
    solution before it reaches the policy.
  - Gravity tilt changes the sim task (03 §1), even though the scorer partly absorbs it.
- **R3.2→S4:**
  - Every new library version re-tracks all 40 episodes at I0 cost (3-7 GPU-h).
  - R3.6 then sends to RL only those episodes whose reference actually changed.
- **R3.2 for CD-O:**
  - CD-O is Sim(3)-registered Chamfer, so one excellent mesh per identity scores well on every
    pair it is emitted for.
  - Effort concentrates on 11 meshes instead of 36.
- **Rest-pose statistics** (R3.1): the white pot always rests upright, so only its yaw is free in
  the static prefix. This makes the slot-0 anchor a 4-DoF estimate for non-symmetric objects.
  - It does not help G2: cup yaw is unobservable.
- **R3.3 self-training:** high-confidence eval-episode frames as pseudo-labels.
  - Automated, so it is not hand labelling.
  - Risk of confirmation bias. Gate it by R2's physics-labeler negatives if R2 exists.
- **R3.5:** choose the parent by a GT-free similarity of object set and motion statistics.
  - Layout match (same B, same contact K) is the hard constraint.
  - Object identity is not part of the layout [U: verify on the checkpoint input description].

### 5.3 Error-budget mapping
| Budget item | R3 mechanism | Expected effect [H] |
|---|---|---|
| Body-frame offsets, mesh error (G3, 1.1) | library meshes from many views, one canonicalisation per identity | consistent frames across episodes; better ADD and CD-O |
| Slot-0 anchor | rest-pose prior + better mesh | tighter anchor for pot, rack, dust pan, sweeper, wooden pieces |
| Lost object, jitter | in-domain tracker + calibrated confidence | fewer losses under hand occlusion |
| Drift, gravity | room prior | fewer frame-0 settle failures; less sim-task tilt |
| Policy tracking share | warm starts (more effective training per GPU-h); repaired human hands | moderate; human-hand noise persists (04 §9.2) |
| G2 cup anchor | none | unchanged lottery |

### 5.4 Cost [E]
- **Engineering:**

  | Component | Person-weeks |
  |---|---|
  | Library + canonicaliser | 1-1.5 |
  | Tracker fine-tune + error model | 1-1.5 |
  | Keypoint hands (IK, de-penetration, contacts) | 1-1.5 |
  | Warm starts + hashing | 0.5 |
  | **Total beyond spine** | **3.5-5** |

- **GPU, one-time:** library 2-4 GPU-h; tracker fine-tune 5-20. The parent policies are the I4
  validation run (40-80), which is needed anyway.
- **Full submission:**
  - first time ≈ 5 + 3 + 60 + 1 ≈ **70**;
  - after the pool exists ≈ 5 + 3 + 20 × (0.25-0.5) × 3 + 1 ≈ **25-40 GPU-h**;
  - resubmits after small changes, via R3.6: often < 15.
- **Per iteration:** library or tracker change → I0 + I1 (4-11 GPU-h); RL only for changed
  episodes.

### 5.5 Data flywheel (most literal of the three)
- **Each new video adds:**
  - views to the object library;
  - statistics to the room prior;
  - (pseudo-)labels to the tracker;
  - a policy to the warm-start pool.

  Marginal error and cost per episode fall with use.
- **Industry framing:** instrument a kitchen once and every later demonstration is cheaper and
  better.
- **Capture:** no object-scanning pass. Meshes come from the manipulation videos themselves,
  whereas NVIDIA's HOI reconstruction expects a ≥ 600° scan orbit (01 E).

### 5.6 Red team
Failure modes:
1. **Rules on pooling** (05 Q2). Can one episode's inference use other episodes' videos, including
   other eval videos?
   - If not: a public-only library for the 9 scanned identities, which is legal as training data.
   - The spoon then falls back to per-episode meshes, losing R3's best CD-O and spoon lever.
2. **CD-O "own reconstructed meshes"** [V FAQ]. A pooled mesh is our reconstruction, but confirm
   that a shared mesh across episodes is acceptable.
3. **Identity drift.** Same name but a different physical instance across sessions [U]. Guard: a
   per-episode Chamfer check against the library (an outlier means use the per-episode mesh).
4. **Tracker overfit.** 9 objects / 20 episodes, and the spoon is unseen. Little gain exactly where
   it is most needed (10/20 eval eps).
5. **Warm-start negative transfer** from a different task; observation-layout mismatch.
6. **Label noise** from the camera↔mocap alignment used for fine-tuning labels.
7. **Human-hand noise.** MediaPipe on close egocentric hands under object occlusion; greyscale mono
   views [U]. Requires contact repair (04 idea 2), so R3 keeps part of the hand-stack burden that
   R1 removes.

**Cheapest killing experiments:**
- **K3a** (≤ 1 GPU-h, needs S5).
  - For white_pot (9 public eps) and blue_cup (5), compare Chamfer(scan, single-episode mesh) with
    Chamfer(scan, fused library mesh). Evaluator-side use of public scans only.
  - **Kill the library** if the gain is under 20% (05 I).
- **K3b** (≈ 5-8 GPU-h).
  - Warm start Pan_Solo ep 41 → ep 44 at 25% budget vs scratch at 100%, 2 seeds each.
  - Then a cross-task parent: Pot_with_lid → Pan_In_Dishrack.
  - **Kill warm starts** if final AUC vs mocap is worse by more than the seed standard deviation.
- **K3c** (≈ 5-10 GPU-h).
  - Tracker fine-tune, leave-one-task-out on 2 held-out tasks, vs off-the-shelf.
  - **Kill** if err(ref, mocap) improves by less than 2 AUC points.

**Licence exposure: low to medium.**
- Defaults are [OSI]: Open3D, PyTorch3D, CoACD, MegaPose, DINOv2, MediaPipe (weights [U]).
- The HaMeR alternative brings MANO [M]. A FoundationPose fine-tune would be [NC].

**Rule risks: medium.**
- Pooling across episodes and transductive self-training on eval inputs. Both are automated, so
  not hand labelling, but unusual. Ask before relying on them.

---------------------------------------------------------------------------------------------------
## 6. Comparison and ranking (all entries [E]/[H] unless marked)

| Dimension | R1 Hands-Free | R2 Sim-Verified + Distilled | R3 Room Memory |
|---|---|---|---|
| Assumption challenged | 3D human hands needed | reference = reconstruction; RL from scratch per video | each clip independent; scans or hallucinated meshes |
| Main boards moved | SP-SR, MP-SR, AUC via fewer drops and knocks | SP-SR, MP-SR via executable refs; cost | all pose boards via mesh/anchor/tracker; **CD-O**; cost |
| Score lever given the spine / variance | medium-high / **high** (task-dependent) | medium / **high** (physics bias) | medium-high / low-medium |
| Eng. person-weeks beyond spine | ~3 (and removes ~2-3 pw of hand repair) | 3-4.5 (needs R1 or baseline as seed) | 3.5-5 |
| GPU-h, full submission (first → steady) | ~70 → ~70 (≈ 35 with R3.6 incremental) | 25-50 if K2c passes; 75-100 if not | ~70 → 25-40 |
| GPU-h per module iteration | I1 3-5; I2 3-5 | MPC-only 1-10; I2 for distillation | I0 + I1 4-11 |
| 4-week program GPU-h (incl. shared rungs) | ~320-480 | ~330-550 | ~290-430 |
| $ at $1/GPU-h (range at $0.7-2.2) | ~$320-480 ($220-1,060) | ~$330-550 ($230-1,210) | ~$290-430 ($200-950) |
| Licence exposure (defaults) | lowest: no MANO, all [OSI] code | low: own code; never vendor SPIDER | low-medium: [OSI] defaults; HaMeR alternative [M] |
| Rule risk | low-medium (synthetic hand ref) | medium (distillation perception, determinism) | medium (cross-episode pooling, self-training) |
| Innovation, 1-5 (econ / flywheel / assumption / complexity) | 3 / 4 / 5 / 5 = **17** | 5 / 4 / 5 / 2 = **16** | 4 / 5 / 3 / 3 = **15** |
| Cheapest kill | K1a (no RL, ~3-5 GPU-h) | K2a (≤ 1 GPU-h) | K3a (≤ 1 GPU-h) |

**Weighted ranking.** Weights: expected score × confidence 35%; GPU-$ efficiency 15%; eng-week
efficiency 15%; innovation 20%; licence + rule safety 15%. Scores are 1-5 judgements.

| Design | Score × conf | GPU-$ | Eng-week | Innovation | Licence + rule | Weighted |
|---|---|---|---|---|---|---|
| R1 | 3.5 | 3 | 4 | 4.25 | 4.5 | **3.80** |
| R3 | 3.5 | 4.5 | 3 | 3.75 | 3.5 | **3.63** |
| R2 | 2.5 | 3.5 | 2 | 4 | 3.5 | **3.03** |

**Ranking: R1 > R3 > R2.**
- R1 vs R3 is close and is decided by K1a/K1b, not by this table.
- Weighting confidence above 45% flips it to R3 > R1.

**Recommended build: "R1 ⊕ R3", with R2-lite.**
- Shared spine.
- R3.2 library: needed for CD-O and the spoon regardless of the hand path.
- R1 grasps as the primary hand reference; R3.4 keypoint hands as the per-segment hybrid fallback.
- R3.5/R3.6 warm starts and incremental retraining, if K3b passes.
- R2.2 MPC used only to "repair failing windows" flagged by the R1 gates or the in-sim
  err(sim, ref), if K2a/K2b pass.

**Innovation pitch the composite could earn (only if measured):**
- "Hands-free, scan-free, physics-gated video-to-policy": one head-mounted stereo camera, no
  object scans, no mocap, no 3D human hand model, no manual levelling.
- Every reference is verified in the evaluator's own physics before any RL GPU-hour.
- Report GPU-h and $ per episode next to the baseline (~3 GPU-h RL + 10-15 min reconstruction).
- Show each additional video improving the object library and grasp pool.

---------------------------------------------------------------------------------------------------
## 7. Experiment ladder (gated, cheapest first; GT read only by evaluator-side scripts)

Integrity rule (AGENTS.md):
- "Oracle" arms that feed mocap as the object reference are **diagnostics only**. They are labelled
  as such and never used in a submission pipeline.
- Public scans are used only evaluator-side unless the organisers allow them as priors.

| Rung | When | GPU-h [E] | Experiments | Decision / kill rule |
|---|---|---|---|---|
| 0 | days 1-3 | 0 | G1 timing (read kit + resampling; organiser email; owner: timing agent). G2 cup-cue census (public cup scans + video crops of eps 11-13, 21-22: any visible azimuth cue?). G3 10-scan frame census (owner: mesh-frame agent). S8 harness from 02 scripts. Static-fraction and occlusion-share analysis on public GT (05 B/C falsifiers). Organiser email (section 9) | Set `motion_speed`/fps policy. Invest in the cup anchor only if a cue exists. Freeze the canonicalisation rule. Value of the batch priors and of physics fills |
| 1 | days 3-6 | 15-25 | Host bring-up. G5: 10M-step timing + VRAM on L40S (2,048 worlds), A100-80 and H100 (4,096). **K2a determinism**. **Exp 0** (05 §2): oracle-reference policies on 3 public eps (policy-only error ceiling; also the end-to-end G1 mapping check). VOC-0 replay calibration on the same eps | GPU type and P_RL (rescale every estimate here). Whether policy error or reference error dominates (staffing tilt). Distillation route alive? |
| 2 | weeks 1-2 | 20-40 (I0 × ~6) | Spine on 20 public eps: stereo Q1; tracker [OSI] vs FoundationPose flag (cost of compliance, 03 Q3); drift Q7; S5 meshes; **K3a** library | OSI vs NC per component (with organiser answer). Library go/no-go |
| 3 | week 2 | 5-10 | **K1a** (R1 vs baseline hands: settle, replay). R3.4 keypoint-hand prototype as a third arm if ready | Hand path shortlist |
| 4 | week 2 | 40-80 | **K1b** equal-budget RL, 6 dev eps × 2 seeds × 2 arms. Use the same runs to measure **I2-vs-I3 rank correlation**. **K3b** warm start | Hand path (R1 / R3.4 / hybrid). Short-RL proxy usable (ρ ≥ 0.6)? Warm starts on/off |
| 5 | weeks 2-3 (stretch) | 5-10 | **K2b**, **K2c**, only if K2a passed and a person is free | R2-lite on/off |
| 6 | week 3 | 40-80 | **I4**: chosen pipeline on all 20 public eps, 1 seed, kit scorer + decomposition. Produces the R3.5 parent pool | Go to submission; list weakest episode families |
| 7 | weeks 3-4 | 25-70 per submission | Eval submission S1 (target ~Oct 21-23); incremental resubmits (R3.6) on fixed families; adaptive second seeds; final 3 days: choose among genuine runs only | Final 2 picks by 2026-11-04 17:00 EST |

**Ladder total:** ≈ 300-480 GPU-h ≈ $300-500 at $1/GPU-h (up to ~$1,050 at $2.2), comparable to
requirements Scenario B (350-650 GPU-h).
- Rungs 0-3 cost < 75 GPU-h.
- Their purpose is to kill wrong bets before the expensive rungs.

---------------------------------------------------------------------------------------------------
## 8. Team split (4 core people + optional 5th; ~4 weeks to the 2026-11-04 freeze)

File ownership is disjoint; P3 owns the GPU queue (heavy runs serialised per host).

| Person | Owns | W1 (Oct 5-11) | W2 (Oct 12-18) | W3 (Oct 19-25) | W4 (Oct 26-Nov 1) + buffer |
|---|---|---|---|---|---|
| P1 Perception | `perception/` S0-S4 | S0-S3 on public eps; stereo Q1; drift Q7 | S4 batch estimator; anchor; OSI-vs-FP measurement | fixes from I4 decomposition; spoon tracking | failure-family fixes; freeze |
| P2 Transfer | `transfer/`, training configs; S6-S7 | Exp 0 + replay calibration (with P3); R1.2-R1.3 prototype | R1 complete; K1a, K1b; reward/reset tweaks | I4 training configs; adaptive seeds; R2-lite (if K2) | resubmits; ablations for the report |
| P3 Infra / eval / econ | `infra/`, `eval/`, `submit/`; S8 | host, queue, spot resume; G5 timing; K2a; S8 harness; compliance diff | content hashing (R3.6); proxy correlation; packing dry run on public | I4 + S1 submission | incremental resubmits; single-command repro; GPU-h ledger |
| P4 Assets / CD-O / innovation | `assets/`, `docs/`; S5, R3.2, G3 | G3 census; S5 static-prefix bootstrap; organiser liaison; licence register | K3a; library v1; spoon mesh; URDF mass | CD-O submissions; library v2 | technical report, innovation narrative, Apache release prep |
| P5 (optional) | `hands/` or `mpc/` | R3.4 keypoint hands | K1 third arm; R3.3 tracker fine-tune (K3c) | R2.2 MPC prototype (K2b) or tracker v2 | support |

Checkpointing: per AGENTS.md, update `HANDOFF.md` and run `scripts/checkpoint.py` after each rung
decision. The challenge repo is a separate clean-room repo (requirements 2026-10-04).

---------------------------------------------------------------------------------------------------
## 9. Organiser questions (additions to 05 §4 and the requirements note)
1. **G1.** The packer numbers rows by `reference_frame = step + start_frame` and the recipe uses
   `motion_speed: 0.5`. Is that intended? May we set `motion_speed: 1` with fps = the measured
   capture rate (20.00 fps) so steps map 1:1 to frames?
2. **G2.** Slot 0 is a near-symmetric cup in eval episodes 8, 10, 14, 20, 32, 33. Will the scorer
   use a symmetry-aware metric or a different anchor? If not, may public scans be used as frame
   priors for the pose boards?
3. **G3.** What frame convention (origin, axes, sign) does the hidden wooden-spoon scan use?
4. **R1.** Is a robot-hand reference synthesised in simulation acceptable as "reconstruction-
   derived", given that the object trajectories come from the video?
5. **R2.** Is it acceptable to initialise FlashSAC from our own sampling-MPC/BC data, provided the
   submitted checkpoint is produced by a FlashSAC training run?
6. **R3.** May one episode's pipeline use other episodes' videos (public and eval) for meshes,
   priors and automated self-training?
7. What GPU/driver will reproduction use, and what trajectory tolerance applies (determinism)?
8. Does the Kaggle OSI rule apply to third-party code invoked at inference (FoundationPose,
   FoundationStereo, SAM-License code, MANO)?
9. GPU credits (FAQ: "under review").

---------------------------------------------------------------------------------------------------
## 10. What would change the ranking
- **K1a/K1b fail** (synthesised grasps worse or infeasible on > 1/3 of segments): R3 first, with
  repaired human hands. R1 survives only as the per-segment fallback for frame-0 / static-object
  safety.
- **Exp 0 shows policy error ≪ reference error:** de-prioritise the transfer bets (R1, R2) and move
  people to the spine and R3.3.
- **K2a passes and K2c > 0.8:** R2 rises to first on economics and is worth a person in W3.
- **Organisers forbid cross-episode pooling:** R3 loses the spoon and CD-O library lever and falls
  near R2.
- **G1 forces real-speed playback and the soft wrist cannot follow** (seen in Exp 0 or R2.2):
  physically consistent references become decisive. R1 and R2-lite rise; R3's human-hand path
  falls.
- **The OSI tracker gap vs FoundationPose is large and NC is allowed:** swap the S4 flag. The
  ranking among R1-R3 is unchanged.

---------------------------------------------------------------------------------------------------
## 11. Verification log and limitations

Checks performed this session:
- **GitHub API** `repos/<r>` and `repos/<r>/license`:
  - RAFT-Stereo MIT; IGEV MIT; CREStereo Apache-2.0; DEFOM-Stereo MIT; MediaPipe Apache-2.0;
    CoACD MIT; mujoco_warp Apache-2.0; newton Apache-2.0; TAPIP3D Apache-2.0.
  - gtsam: simplified BSD (LICENSE text); Open3D: MIT (text); PyTorch3D: BSD (text).
  - BODex: "NVIDIA License" (header only read; NC family assumed [U]).
  - DexGraspNet: no LICENSE (404).
- **Kit v2** (session scratchpad, read-only):
  - `data/track_3_evaluation_objects.json` gives slot order per eval episode.
  - `tools/pack_submission.py` contains the `reference_frame = step + start_frame` note.
  - A grep of the kit for `motion_speed` / `source_frame_playback` found nothing.
- **Other agents' in-progress outputs** (cited [U], not re-derived): `analysis_timing_map.py`
  output (G1 consequences); `meshframe/analyze_meshes.log` (wooden_piece_2 negative skew).
- **Kaggle Track 3 rules page:** WebFetch returned only the title (JS-rendered). The OSI wording is
  from secondary search results [U].
- **MediaPipe hand-landmarker weight licence:** Apache-2.0 per a third-party model zoo (Luxonis)
  via search [U].

Limitations:
- Nothing was run on a GPU. Every GPU-h figure scales with the unmeasured P_RL (G5).
- Person-week figures are judgements.
- Innovation scores and ranking weights are subjective. They are stated so that others can
  re-weight.
- The G1/G2 consequences need organiser confirmation and an end-to-end check (Exp 0) before they
  drive spending.

## Progress log
- 2026-10-04 start: read 01-05 + requirements; licence checks via GitHub API; kit eval object list
  and packer note read; gates G1-G3 identified. Sections 0-1 saved.
- +~25 min: section 2 (shared spine) saved.
- +~40 min: section 3 (R1) saved.
- +~50 min: section 4 (R2) saved.
- +~60 min: section 5 (R3) saved.
- +~75 min: sections 6-11 (comparison, ranking, ladder, team split, questions, verification) saved.
  Status COMPLETE v1.


---
[← Index](../README.md) · [Summary](../00-summary.md) · [← 08](08-architectures-accuracy.md) · [10 →](10-synthesis.md)
