[← Index](README.md) · [Summary](00-summary.md)

# V2D Challenge Track 3 — entry requirements (research note, 2026-10-01)

Status: PROPOSED. Nothing installed, built, registered or submitted. Read-only research.

## Sources read
- Challenge page: https://nvidia-isaac.github.io/video_to_data/v2d_challenge/
- Submission kit: https://nvidia-isaac.github.io/video_to_data/v2d_challenge/assets/v2d_submission_kit.zip
  (unpacked copy was in the session scratchpad only; re-download to inspect)
- Kaggle rules: https://www.kaggle.com/competitions/v2d-challenge-track3-auc/rules
- Dataset: https://huggingface.co/datasets/nvidia/video_to_data_challenge/tree/main/track_3 (CC BY 4.0)
- Repo nvidia-isaac/video_to_data: release/0.2.0 ("starter toolkit"); official evaluator pin
  main@aee95f25ae0943f335d8bb42fa95b6a9acfa266f (robotic_grounding/flash_chord)
- Live leaderboard JSON: https://raw.githubusercontent.com/MVerghese/v2d-leaderboard-data/main/leaderboard.json

## What Track 3 scores
Egocentric video -> reconstruct objects/hands -> train one RL policy per episode in FlashCHORD
-> run the official evaluator -> submit the *simulated* object trajectories.
- Pose CSV (9,120 rows, 20 eval episodes 1,3,5,6,8,10,14,15,16,19,20,25,28,30,32,33,35,36,37,38)
  goes to 5 Kaggle competitions: AUC (ADD 1-9 cm, higher), SP-SR (<=10 cm & <=0.5 rad, higher),
  MP-SR (<3 cm & <30 deg per object, higher), RPE (cm, lower), MPPE (cm, lower).
- Mesh Parquet (one mesh per episode-object) goes to CD-O (Sim(3)-registered Chamfer, cm, lower).
- Scorer aligns only the first pose of object slot 0 with one rigid transform per episode;
  metric scale is NOT corrected. Reference poses use the scanned-mesh frame.
- Scorer code: kit `metric_code/track_3/*.py`. Kaggle `private_fraction` = 0 (all public), but the
  sponsor runs a further held-out evaluation after close on undistributed data.
- How the 6 metrics combine into "track winner" is NOT defined anywhere found -> ask organizers.

## Data facts (track_3, ~1.47 GB)
- 20 public episodes WITH mocap object poses (local validation set) + 20 eval episodes video-only.
- 3 ego streams: ego_cam_a 2028x1520 colour (mounted rotation_deg=180); ego_cam_b/c 1280x800 mono
  stereo pair, 75 mm baseline. ~20.25 fps, ~262 frames/episode. OAK factory calibration with
  inter-camera extrinsics; no camera-to-mocap extrinsic. No IMU stream released.
- Scanned meshes + URDFs for 10 objects; `wooden_spoon` appears in 10 of 20 eval episodes
  (3,5,6,15,16,32,33,35,36,37) but has no public mesh. 36 episode-object pairs in total.

## Rules that matter (Kaggle Track 3 rules)
- Team <= 10; 5 submissions/week per competition, unlimited in final 3 days; 2 final picks.
- Must also register on the challenge site form (separate from Kaggle).
- Every row: evaluator digests + per-episode checkpoint digest + GitHub /commit/<sha> URL in a repo
  shared with the V2D organisers' account.
- External data and pretrained models allowed (publicly accessible, reasonable cost).
- Kaggle foundational rule: no hand labeling / human prediction on test records.
- Winners: Apache-2.0 public code release, technical report, reproducible single command.
- Leaderboard freeze 2026-11-04 17:00 EST; winners at CoRL tutorial 2026-11-12.
- Leaderboard state 2026-10-01: Track 3 has zero submissions on all six boards.

## Runtime requirements (from repo docs)
- FlashCHORD (policy train/eval): Linux, NVIDIA driver >= 580, Docker + NVIDIA Container Toolkit,
  Git LFS. Full training needs a 48 GiB GPU with >= 46,000 MiB free. Stack: Newton 1.2.0,
  MuJoCo/MuJoCo-Warp 3.8.1, Warp 1.14.0, JAX[cuda13] 0.10.2, Python 3.11. Base image
  nvidia/cuda:13.0.2-devel-ubuntu24.04 (4.0 GB compressed). Sharpa FlashSAC recipe =
  250,003,456 env steps per policy; wall-clock not documented.
- Ego reconstruction baseline: Docker + NVIDIA Container Toolkit; repo states 9 images,
  ~30 min build, ~135 GB; ~10-15 min per segment. Mostly pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel
  base (7.4 GB compressed). Monocular pipeline (HaMeR/DynHaMR, Grounding DINO, SAM2, SAM3D,
  FoundationPose, MoGe, DROID-SLAM, gravity alignment, gsplat); supports `--object_mesh` override.
- Retarget ego reconstruction -> Sharpa: robotic_grounding/scripts/retarget/ego_recon_to_sharpa.py,
  run inside the robotic_grounding (Isaac Lab) container; needs MANO .pkl (registration).
- Gated/licensed downloads: facebook/sam-3d-objects (13.3 GB repo storage, manual gate),
  facebook/sam-3d-body-dinov3 (manual gate), MANO, FoundationPose (NVIDIA model EULA flag),
  FoundationStereo (NGC).
- Weights (HF usedStorage / HTTP sizes): SAM3D objects 13.3 GB, HaMeR demo tar 6.0 GB,
  MoGe-2 ViT-L 2.65 GB, SAM2.1 large 2.69 GB, plus smaller models. Estimate 25-35 GB total.

## Disk estimate for one Linux GPU host (estimates marked)
| Item | Size |
|---|---|
| Reconstruction images | ~135 GB (repo's figure) |
| Model weights | ~25-35 GB (estimate) |
| FlashCHORD image | ~15-20 GB (estimate) |
| Isaac Lab robotic_grounding image | tens of GB (not measured) |
| Repo + LFS + track_3 data | ~2-3 GB |
| Per-episode intermediates and checkpoints, 40 episodes | tens of GB (not measured) |
| Plan | >= 300 GB used; provision 500 GB-1 TB |

The local Mac (M4 Max, arm64, no NVIDIA GPU, ~100 GiB free on 2026-10-01) cannot run the
reconstruction containers or FlashCHORD. It can inspect data, score locally, pack and upload.

## Hypotheses for ranking (untested)
1. Use the stereo pair for metric depth/scale and stereo ego-motion (SlamDunk overlap) instead of
   the monocular baseline's scale estimation; scale error is scored directly.
2. Track objects with the provided scanned meshes so the pose frame matches the reference frame
   (README: poses are in the scan's frame). Ask organizers whether public meshes may be used
   for eval episodes and, separately, for the CD-O submission.
3. Build a local validation harness on the 20 public episodes using the kit's scorer code
   (sample 500 object-frame points from public meshes for AUC) before spending submissions.
4. Policy tracking quality bounds the score: the evaluated trajectory is the simulated object.

## Compute options (checked 2026-10-01)
- Challenge page, kit and Kaggle rules: no compute credits or VMs offered. The CoRL tutorial page
  offers laptop-only / optional GPU / precomputed-artifact paths, so organizers know GPUs are a barrier.
- Asking organizers for compute is unconfirmed; draft request given to user in chat (not sent).
- NVIDIA Academic Grant Program: closed to new applications; full-time faculty only
  (https://www.nvidia.com/en-us/industries/higher-education-research/academic-grant-program/).
- NVIDIA Inception: credits via partners per third-party guides (unverified); requires an
  incorporated company and business email.
- Fallback: rent a >= 48 GB Linux GPU host by the hour.

## GPU cost estimate (2026-10-01, estimates)
- Anchor: CHORD paper (arXiv 2607.00033, same NVIDIA team): "FlashSAC with 2,048 environments,
  training each per-sequence policy on a single L40S GPU in ~2 hours". Current FlashCHORD Sharpa
  recipe uses 4,096 worlds / 250M steps and asks for >= 46,000 MiB free; L40S is borderline, so
  either run 2,048 worlds or use a 49 GB / 80 GB card. Per-policy time for the current recipe is
  unmeasured; assume 2-4 GPU-h.
- Reconstruction baseline: ~10-15 min per segment (repo README).
- Rental prices seen in third-party comparisons (verify at rental time): L40S ~$0.72-1.30/h,
  A100 80GB ~$0.80-2.20/h, H100 ~$1.89-4/h on-demand from smaller providers.
- Scenario A, first full Track 3 submission with the baseline: ~70-130 GPU-h -> ~$60-170 on L40S.
- Scenario B, competitive five-week effort (3-5 retrain cycles of 20 policies, local validation on
  public episodes, development time): ~350-650 GPU-h -> ~$300-850 on L40S-class.
- CD-O mesh-only entry: a few GPU-h.
- Reconstruction launches Docker containers with GPU access, so the host must be a VM/bare metal
  with Docker + NVIDIA Container Toolkit, not a container-only pod.

## What is fixed vs free (checked 2026-10-01)
- Fixed: scored trajectories must be FlashCHORD rollouts from the official evaluator. The
  `eval_code_sha256` digest covers only `flash_chord/evaluation/{__init__,harness,metrics,rollout}.py`
  (harness.py `_EVALUATION_CODE_MODULES`). Evaluation removes training assistance (virtual object
  controller force/torque set to 0, failure terminations off, reset to first frame), so the policy
  must move the object physically. Supported learners: FlashSAC and PPO checkpoints.
- Free: reconstruction method, hand/object estimation, retargeting, reward/curriculum/network and
  training budget; a different checkpoint per episode is allowed. Pretrained models/VLAs permitted
  by rules 7c, but a VLA would still need to end in a FlashCHORD checkpoint (ask organizers).
- Changing simulator physics or evaluation behaviour would count as manipulating the evaluation.

## Approach hypotheses (untested)
- Score = simulated object trajectory vs mocap, so error = reconstruction error + policy tracking
  error. Reconstruction error can be measured on the 20 public episodes without training policies.
- Stereo-metric pipeline: depth from ego_cam_b/c (75 mm baseline; ~1.5-3 mm per 0.25 px disparity
  error at 0.5-0.7 m, computed from fx ~562 px), metric stereo camera trajectory with hands/objects
  masked, FoundationPose with scanned meshes on colour + registered stereo depth, offline
  smoothing with table-plane/gravity, static-when-untouched and non-penetration priors.
- Policy: reward/curriculum tuning for object fidelity; physically consistent references; several
  seeds per episode chosen by tracking error against our own reference (no GT).
- Hard case: wooden_spoon has no scan (10/20 eval episodes); thin, near-symmetric object.

## Public vs evaluation coverage (computed 2026-10-01 from public parquets + kit object list)
- Public: 20 episodes, 10 tasks (Pan_Solo 5; Pot_with_lid, Cup_In_Dish_Rack, Water_Can_Blue_Cup,
  Planter_Stand, Pan_In_Dishrack, Dustpan_Solo 2 each; Cup_Stack, Dust_Brush, Brush_Dishrack 1 each),
  137-373 frames, object motion extent ~11-43 cm (static objects < 1 cm).
- Eval episodes with an object set seen in public data: 9/20 (1,10,14,19,20,25,28,30,38).
- Eval episodes with no public analogue: 11/20 — ten with wooden_spoon (3,5,6,15,16,32,33,35,36,37;
  35-37 spoon only) and ep 8 (beige_cup + white_pot). wooden_spoon has no mesh and no GT anywhere.
- Episode indices interleave (public 0-45, eval 1-38): same rig, room and capture sessions.

## Ranking mechanics and legitimate metric optimisation
- Six independent Kaggle boards; 100% public (no private split), so the public score on the 20 eval
  episodes is the standing. Winner = "first on the track leaderboard"; cross-metric aggregation
  unpublished (Track 1/2 text mentions points/weights; Track 3 none). Positions provisional until
  reproducibility verification. Separate panel-judged Industry Innovation Award.
- Evaluator is deterministic (deterministic: true, seed 42, 1 world per episode).
- Scorer trusts the frame-0 pose of object slot 0 completely; an orientation error of theta there
  rotates the whole episode (5 deg at 30 cm lever arm ~ 2.6 cm, near the MP-SR 3 cm threshold).
- RPE: single-object episodes (35, 36, 37, 38) score 0 for everyone.
- Unlimited submissions in the final 3 days: selecting among genuine pipeline runs by score is
  allowed; crafting files to probe the hidden reference or altering evaluator/physics is not.

## Tooling timeline (why boards were empty on 2026-10-02)
- FlashCHORD trajectory export for the leaderboard: main commit #181, 2026-09-28 23:18 UTC
  (= evaluator pin aee95f25). Kit first published #182, 2026-09-29.
- Kit refreshed #188 "Clarify challenge submission workflow and refresh participant kit",
  2026-10-01 19:40 UTC — AFTER the copy summarised above. Re-download and diff before use.

## 2026-10-04 updates
- Kit refreshed (#188, #190): evaluator pin now main@8c778f905cb35f76f8e6cd6e2ea486da4fb9e0ef
  (only flash_chord/scene/support.py changed vs aee95f25); private repos must invite GitHub
  account Nvidia-V2D-Challenge; uploader has --wait and receipts.
- FAQ (docs/v2d_challenge/assets/v2d_challenge_2026_faqs.pdf, 2026-10-02): CD-O must use own
  reconstructed meshes, not public scans; Sharpa Wave default embodiment, others welcome (floating
  hands, fixed-base arm+hand); GPU credits "under review", reply to requesting participants;
  pretrained models/external data allowed; 5 submissions/week per track and tier; Discord exists.
  Metric aggregation still unstated. Using public scans as tracking priors not addressed.
- User decisions: goal = leaderboard + Industry Innovation; rent GPUs when needed (no fixed
  budget); 4+ people; challenge code in a clean-room new repo with no SlamDunk code.
- Research plan v0 proposed to user (candidate architectures A-G, five research streams); awaiting
  approval before the deep-research workflow. No downloads needed beyond ~1 MB public pose files.

## Next actions (proposed, need user decision)
- Register team (form) and accept the six Kaggle rule pages (user only; no API).
- Email v2d_challenge@nvidia.com: metric aggregation; use of public meshes for tracking and CD-O.
- Rent or provision Linux GPU host (>= 48 GB VRAM, driver >= 580, >= 500 GB disk).
- Reproduce the baseline on one public episode end-to-end, then measure policy training time.
