# 03 — Perception literature / open-source survey for V2D Track 3

Status: COMPLETE research note (2026-10-04). Research only: nothing installed, no models downloaded,
no repo code edited, no SlamDunk code used. Sources: papers (arXiv HTML), author repos (GitHub API
licence + README), HF model cards (licence tags), BOP leaderboards, organiser repo and FAQ.
Scope: head-mounted video (2028x1520 colour + 1280x800 mono stereo, 75 mm baseline, factory
calibration, ~20 fps, ~13 s clips, hand occlusion, tabletop kitchen objects, unscanned wooden spoon)
-> metric gravity-aligned world-frame 6DoF object trajectories, own meshes (CD-O, Sim(3) Chamfer),
3D hands. Numbers are as reported by their authors unless marked; UNVERIFIED = not checked in a
primary source here.

## Executive summary
1. Use the stereo pair. HOT3D (head-mounted, closest public analogue) reports 3D lifting of
   in-hand objects recall@10 cm of 96.8 % with stereo matching vs 30.2 % with monocular depth; best
   metric mono depth (MoGe-2) still has ~8-16 % relative error. The organiser ego baseline is
   monocular (MoGe + DROID-SLAM + SAM3D scale estimation), so this is our main expected advantage.
2. Best-evidenced tracker for "own mesh + metric depth" remains FoundationPose (YCB-V ADD 96.0 AUC,
   YCBInEOAT 93.09, HO-Cap hand-object ADD 89.3 vs MegaPose 67.1). Newer trackers mainly add
   recovery/speed (Woven/Bonn 2026: same accuracy, 57.6 vs 41.3 FPS) or RGB-only (GoTrack).
3. Segmentation: SAM2.1 (Apache) is the clean default; SAM 3/3.1 is clearly better under occlusion
   (MOSEv2 60.3 vs 47.9 J&F) and adds text/exemplar prompts (useful for "wooden spoon"), under the
   custom SAM License.
4. Own meshes: BundleSDF (HO3D CD 0.57 cm) / 6DOPE-GS (0.41 cm) with depth are the measured
   video-based options; SAM3D / TRELLIS.2 / Hunyuan3D give complete but hallucinated shapes. Plan to
   combine generative completion with multi-view stereo constraints.
5. Licences are the main non-technical risk: FoundationPose, BundleSDF, FoundationStereo,
   Fast-FoundationStereo, nvdiffrast, 3DGS/2DGS reference code, GoTrack, FoundPose, Any6D, WiLoR,
   HaWoR, UniDepth, MASt3R-SLAM, Depth Pro and ARCTIC are non-commercial. MANO is research-only.
   OSI-clean alternatives exist for most stages (SAM2.1, Grounding DINO, OWLv2, MoGe-2, DROID-SLAM,
   DPVO, MegaPose, GigaPose, gsplat, TRELLIS(.2) minus nvdiffrast, MapAnything-apache, Pi3, MHR).
   Ask the organisers (Q12) before investing in a licence-clean variant.
6. Three proposed stacks: section 12 (S1 conservative organiser-aligned stereo, S2 accurate
   multi-view iterative, S3 cheap and cleanest licence). 13 falsifiable questions are in section 13.

Progress log:
- 21:05 skeleton created; licence sweep; 21:20 licence table saved; then per-area sections 1-9;
  ~22:10 addenda, fit analysis, stacks, open questions, executive summary. Complete.

---------------------------------------------------------------------------------------------
## 0. Licence rule we screen against (read this first)

Kaggle foundational rules (as summarised by the user, not re-read here): open-source *code* used in a
winning submission must be OSI-approved without commercial limits; pretrained *models* with
incompatible licences need not be released. Winners must also release their own code Apache-2.0.
Ambiguities (ASK ORGANISERS; record answer in handoff):
- A1. Many NVIDIA/Meta research repos ship code AND weights under one non-OSI licence (NVIDIA Source
  Code License = "research or evaluation purposes only"; SAM License; VGGT License; CC BY-NC).
  Calling such code at inference is "using OSS code" -> probably non-compliant even if weights are OK.
- A2. The official V2D ego-reconstruction baseline itself depends on FoundationPose, SAM3D, HaMeR,
  MANO etc. (non-OSI). Organisers presumably tolerate these; unconfirmed. If the baseline's stack is
  acceptable, the rule is weaker than its literal text.
- A3. MANO (hand model) is a research-only licence from MPI; every MANO-based hand method inherits it.
- A4. Custom licences that DO allow commercial use but are not OSI (SAM License, VGGT License,
  NVIDIA Community License for PyCuVSLAM, Tencent Hunyuan community licence with territory exclusions)
  are "no commercial limit" but still not OSI-approved.

Licence sweep (GitHub API + LICENSE text, 2026-10-04). OSI = OSI-approved, no commercial limit.
| Repo | Code licence (verified from LICENSE text) | Class |
|---|---|---|
| NVlabs/FoundationPose | NVIDIA Source Code License: "non-commercially ... research or evaluation purposes only" (code+weights) | NON-COMMERCIAL |
| NVlabs/BundleSDF | NVIDIA Source Code License (same family) | NON-COMMERCIAL |
| NVlabs/FoundationStereo | NVIDIA Source Code License, "research purposes only" | NON-COMMERCIAL |
| taeyeopl/Any6D | custom "academic and personal use only ... Commercial use is strictly prohibited" | NON-COMMERCIAL |
| facebookresearch/gotrack | CC BY-NC 4.0 | NON-COMMERCIAL |
| facebookresearch/foundpose | CC BY-NC 4.0 | NON-COMMERCIAL |
| JiehongLin/SAM-6D | no LICENSE file (all rights reserved by default) | UNLICENSED |
| nv-nguyen/gigapose | MIT | OSI |
| megapose6d/megapose6d | Apache-2.0 | OSI |
| facebookresearch/sam2 | Apache-2.0 (code + SAM2.1 weights) | OSI |
| facebookresearch/sam3 | SAM License (Nov 2025): royalty-free, permits derivative works/distribution, trade-control + AUP terms; grep of LICENSE found no non-commercial clause; HF weights manually gated | CUSTOM, commercial OK, not OSI |
| facebookresearch/sam-3d-objects, sam-3d-body | SAM License (same) | CUSTOM, commercial OK, not OSI |
| hkchengrex/Cutie | MIT | OSI |
| IDEA-Research/GroundingDINO | Apache-2.0 | OSI |
| google-research/scenic (OWLv2) | Apache-2.0 | OSI |
| microsoft/MoGe | MIT code; HF Ruicheng/moge-2-* and moge-vitl weights tagged MIT | OSI |
| lpiccinelli-eth/UniDepth | CC BY-NC 4.0 | NON-COMMERCIAL |
| ByteDance-Seed/Depth-Anything-3 | Apache-2.0 code; HF: DA3-GIANT/LARGE/NESTED CC BY-NC-4.0; DA3METRIC-LARGE, DA3-BASE, DA3-SMALL Apache-2.0 | OSI code / mixed weights |
| apple/ml-depth-pro | Apple custom code licence; HF apple/DepthPro weights tagged apple-amlr (Apple ML Research, research use) | NON-COMMERCIAL (weights) |
| UZ-SLAMLab/ORB_SLAM3 | GPL-3.0 | OSI (copyleft) |
| princeton-vl/DROID-SLAM | BSD-3-Clause | OSI |
| princeton-vl/DPVO | MIT | OSI |
| rmurai0610/MASt3R-SLAM | CC BY-NC-SA 4.0 (and MASt3R/DUSt3R weights CC BY-NC-SA) | NON-COMMERCIAL |
| mega-sam/mega-sam | Apache-2.0 (but bundles DepthAnything/UniDepth/RAFT deps with own licences) | OSI code |
| nv-tlabs/vipe | Apache-2.0 | OSI code (deps: check) |
| facebookresearch/vggt | VGGT License v1 (Jul 2025); HF VGGT-1B CC BY-NC-4.0; VGGT-1B-Commercial custom licence, gated form, commercial use except military | CUSTOM / NC |
| yyfz/Pi3 | BSD-3-Clause code; HF yyfz233/Pi3 BSD-2-Clause; Pi3X CC BY-NC-4.0 | OSI (Pi3) |
| facebookresearch/map-anything | Apache-2.0 code; HF facebook/map-anything CC BY-NC-4.0, facebook/map-anything-apache Apache-2.0 | OSI (apache weights) |
| NVlabs/PyCuVSLAM | NVIDIA Community License: commercially usable, but only on NVIDIA platforms; closed-source core | CUSTOM, not OSI |
| isaac_ros_visual_slam | Apache-2.0 wrapper around closed cuVSLAM binary | wrapper OSI, core closed |
| graphdeco-inria/gaussian-splatting, hbb1/2d-gaussian-splatting | Inria/MPII Gaussian-Splatting licence, research/evaluation only | NON-COMMERCIAL |
| nerfstudio-project/gsplat | Apache-2.0 (has 2DGS / 3DGS rasterisers) | OSI |
| microsoft/TRELLIS, TRELLIS.2 | MIT | OSI (weights: check deps) |
| Tencent-Hunyuan/Hunyuan3D-2, -2.1 | Tencent community licence; excludes EU, UK, South Korea territories | CUSTOM, territorial limit |
| geopavlakos/hamer | MIT code (but MANO + ViTPose deps research-only) | OSI code / MANO |
| rolpotamias/WiLoR | CC BY-NC-ND 4.0 | NON-COMMERCIAL |
| ThunderVVV/HaWoR | CC BY-NC-ND 4.0 (license.txt) | NON-COMMERCIAL |
| ZhengdiYu/Dyn-HaMR | MIT code (MANO + HaMeR deps) | OSI code / MANO |
| facebookresearch/hot3d | Apache-2.0 (toolkit; dataset own licence) | OSI |
| zc-alexfan/arctic | non-commercial scientific research | NON-COMMERCIAL |
| zc-alexfan/hold | MIT code (MANO deps) | OSI code / MANO |
| NVlabs/dex-ycb-toolkit | GPL-3.0 | OSI (copyleft) |
| nvidia-isaac/video_to_data | Apache-2.0 code + CC-BY-4.0 docs | OSI |
| NVlabs/Fast-FoundationStereo | NVIDIA Source Code License, research only | NON-COMMERCIAL |
| NGC TAO FoundationStereo | NVIDIA Open Model License, commercial use | model licence, not OSI |
| byran-wang/MagicHOI | Apache-2.0 (deps: Zero-1-to-3, MANO) | OSI code |
| facebookresearch/MHR | Apache-2.0 (hand+body rig) | OSI |
| nvidia-isaac/pyCuSFM | Apache-2.0 wrapper (cuVSLAM core closed) | wrapper OSI |
| HF microsoft/Florence-2-large, google/owlv2-*, IDEA-Research/grounding-dino-base | MIT / Apache-2.0 / Apache-2.0 | OSI |


---------------------------------------------------------------------------------------------
## 1. Organiser baseline and organiser-side building blocks (nvidia-isaac/video_to_data, main, read 2026-10-04)

Primary source: https://github.com/nvidia-isaac/video_to_data (Apache-2.0 code; modules wrap third-party
models with their own licences). Relevant because it fixes what the organisers consider "normal" and
gives us tested Docker wrappers.
- Ego baseline `reconstruction/modules/v2d_pipelines/run_ego_reconstruction.py` (skill doc
  `.codex/skills/run-ego-reconstruction-video/references/run-ego-reconstruction-video.md`): MONOCULAR
  RGB. Stages: frames -> MoGe depth+intrinsics -> WiLoR detection + HaMeR hands (or ViPE + Dyn-HaMR
  path) -> SAM2 masks from prompts -> object mesh (SAM3D) + scale estimation, or `--object_mesh` with
  `--skip_object_scale_estimation` -> FoundationPose poses -> pose smoothing -> optional DROID-SLAM
  camera poses -> GeoCalib gravity alignment -> optional gsplat refinement. Output `result.npz`, `mesh.obj`.
- `v2d_foundation_stereo` (stereo depth, TensorRT engine export), `v2d_cusfm` (stereo image list ->
  camera poses via PyCuSFM/cuVSLAM; not supported on sm_120 Blackwell), `v2d_bundlesdf` (SDF + texture
  from given poses/depth/masks; requires stereo calibration json), `v2d_hoi_object_reconstruction`
  (two-stage object scan -> BundleSDF mesh, or SAM3D meshes + silhouette scale; validated on A6000/L40S),
  `v2d_ego_hand_reconstruction` (ViPE + Dyn-HaMR via IsaacTeleop, MANO_RIGHT.pkl needed),
  `v2d_cari4d` (category-agnostic human-object 4D recon; MoGe-2 init + SAM 3D Body + FoundationPose +
  CoCoNet; checkpoint `nvidia/cari4d_commercial`), `v2d_geocalib` (single-image gravity), `v2d_unidepth`,
  `v2d_grounding_dino`, `v2d_sam2`, `v2d_sam3d`, `v2d_sam3d_body`.
- Take-away: the organisers' own stereo path (FoundationStereo + cuSFM + BundleSDF + FoundationPose) is
  the obvious "conservative" stereo stack; the ego baseline does NOT use the stereo pair.
- Gravity: no IMU in Track 3 data, so gravity must come from vision (GeoCalib, table-plane normal,
  vanishing lines, or the object's resting pose). Scorer aligns only the first pose of object slot 0
  with one rigid transform, so global gravity error is partially absorbed for metrics, but NOT for the
  physics simulation in which the policy must move the object (gravity tilt changes the sim task).

---------------------------------------------------------------------------------------------
## 2. 6DoF object pose estimation / tracking

### Benchmarks to read numbers against
- BOP 2024 report (arXiv 2504.02812, https://arxiv.org/abs/2504.02812): introduced BOP-H3 (HOT3D,
  HOPEv2, HANDAL) and model-free tasks (static and *dynamic* onboarding: object manipulated by hands,
  head-mounted camera). Best 2024 unseen-object 6D localisation on BOP-Classic-Core: FreeZeV2.1 82.1 AR
  at 24.9 s/img; Co-op 75.9 AR at 0.8 s/img; GenFlow (2023) 67.4 AR. BOP-H3 model-based 6D detection 2024
  best: GigaPose+GenFlow 31.2 AP (HOT3D 26.8) at 5.3 s/img.
- Live BOP-H3 leaderboards (fetched 2026-10-04; single-image detection, NOT video tracking):
  - Model-based 6D detection (https://bop.felk.cvut.cz/leaderboards/pose-detection-unseen-bop24/bop-h3/):
    SAM-FP 0.668 AP (2026-09-08, per-dataset not shown; method unpublished — name suggests SAM +
    FoundationPose, UNVERIFIED); 3PT-Pose (Nov 2025) 0.587 AP (HOT3D 0.553) at 16 s; Co-op (MUSE)
    0.464 (HOT3D 0.401) at 3.4 s; GigaPose+GenFlow 0.312.
  - Model-free 6D detection (https://bop.felk.cvut.cz/leaderboards/modelfree-pose-detection-unseen-bop24/bop-h3/):
    NOVASplat (CNOS25) 0.529 (2026-07-09); X0 0.508 (HOT3D 0.531) at 40.5 s; gfreedet2-6d 0.466 (HOT3D 0.489).
  - BOP 2025 awards PDF is a Google-Drive link (not read). HOT3D images are fisheye/greyscale Aria/Quest3,
    i.e. closer to our rig than YCB-V.

### FoundationPose (CVPR 2024, NVIDIA) — https://arxiv.org/abs/2312.08344 , https://github.com/NVlabs/FoundationPose
- Output: per-frame 6D pose of a rigid object given RGB-D + first-frame mask + mesh (model-based) or ~16
  reference RGB-D views (model-free, neural object field). Tracking mode refines from previous pose.
- Evidence: YCB-Video tracking model-based ADD-S 97.9 / ADD 96.0 AUC; model-free 97.5 / 93.7.
  YCBInEOAT (robot-held objects) model-based 96.42 / 93.09 (BundleSDF 93.77/86.95, se(3)-TrackNet
  89.18/78.28). Pose estimation ~1.3 s/object (252 hypotheses), tracking ~32 Hz on RTX 3090.
- DEPTH IS REQUIRED (paper: RGBD input; RGB-only methods are separate baselines). Our depth would come
  from FoundationStereo on the mono pair, reprojected into the colour camera (or run FP on the mono left
  camera directly — greyscale, needs testing).
- Limitations stated: texture-less + severe occlusion + weak edges -> orientation failures; relies on
  external 2D detection/mask; no re-detection logic of its own (tracking needs reinit after loss).
- Licence: NVIDIA Source Code License, research/evaluation only (code + weights). NON-COMMERCIAL.
  Used by the organiser baseline. TensorRT version exists in Isaac ROS Pose Estimation (Apache-2.0 ROS
  wrapper; model under NVIDIA model licence — verify).
- Fit: best-validated tracker for "known mesh + metric depth"; the 9 scanned objects can use it if the
  organisers allow public scans as priors (open question). For CD-O we must use our OWN meshes, which
  can then also be FP's mesh (consistency between tracked and submitted mesh).

### Robust tracking with built-in recovery (Woven by Toyota + Bonn, arXiv 2607.23468, Jul 2026)
- RGB-D + mesh tracker; vs FoundationPose: YCB-V ADD 95.0 vs 96.0, ADD-S 98.1 vs 97.9; YCBInEOAT ADD
  93.14 vs 93.09; Fast-YCB ADD-S 99.42 vs 99.15. 57.6 FPS vs FP 41.3 FPS on RTX 4090. Main claim is
  recovery after full occlusion / rapid motion (new dataset). Code/licence: only a dataset page
  github.com/Bazs/robust-6d-object-pose-tracking mentioned — UNVERIFIED release.
- Fit: idea worth copying (loss detection + re-registration), small accuracy delta vs FP.

### GoTrack (Meta Reality Labs, arXiv 2506.07155, 2025) — https://github.com/facebookresearch/gotrack
- RGB-only, CAD-based refinement + tracking; model-to-frame flow (DINOv2 transformer) + frame-to-frame
  RAFT flow. YCB-V tracking ADD 69.3 / ADD-S 83.6 (RGB-only, so not comparable to FP's RGB-D 96.0).
  HOT3D (train split, test GT unavailable): Aria 83.7 ADD / 90.7 ADD-S, Quest3 81.5 / 89.0 — works on
  greyscale. BOP refinement 60.6 AR with GigaPose 5 hyps. Model-to-frame 40 ms, f2f 6 ms (V100).
- Licence: CC BY-NC 4.0 -> NON-COMMERCIAL.
- Fit: useful if stereo depth on the object is poor (thin spoon); otherwise FP+depth should beat it.

### Any6D (CVPR 2025) — https://arxiv.org/abs/2503.18673 , https://github.com/taeyeopl/Any6D
- Model-free: single RGB-D anchor image -> InstantMesh shape -> metric scale by joint 2D-3D alignment
  with depth -> FoundationPose-style render-and-compare. HO3D ADD-S 98.7 / ADD 40.4 / AR 38.3;
  YCBInEOAT ADD-S 89.3 / ADD 45.6. Stated limitation: no shape update when the generated shape is wrong.
- Licence: custom, "Commercial use is strictly prohibited". NON-COMMERCIAL.
- Fit: design pattern (generate shape, fix metric scale with depth, then track) is exactly what the
  spoon needs, but low ADD shows generated-shape error dominates; prefer multi-view reconstruction.

### UA-Pose (arXiv 2506.07996, 2025) — https://minfenli.github.io/UA-Pose/
- RGB-D, partial references (few posed RGB-D views or one image) + uncertainty-aware online object
  completion; claims FP fails on HO3D with 2 reference images under strong rotation, UA-Pose succeeds.
  Numbers not extracted (UNVERIFIED magnitude). Code/licence not checked.

### SAM-6D (CVPR 2024) — https://github.com/JiehongLin/SAM-6D
- RGB-D zero-shot: SAM-based instance segmentation model (ISM) + point-matching pose model (PEM).
  NO LICENSE FILE (default all-rights-reserved) -> unusable for a compliant release.

### GigaPose (CVPR 2024) — https://github.com/nv-nguyen/gigapose (MIT)
- RGB-only coarse pose from one correspondence; 0.87 s/img; weak alone (BOP-H3 9.4 AP) but good as
  hypothesis generator (GigaPose+GenFlow 31.2 AP; + GoTrack 60.6 AR on BOP-Classic).
- Licence MIT -> OSI. Fit: OSI-clean coarse initialiser if FP is ruled out.

### MegaPose (CoRL 2022) — https://github.com/megapose6d/megapose6d (Apache-2.0)
- RGB or RGB-D coarse+refiner for novel objects with mesh; slower and less accurate than FP but
  Apache-2.0. The OSI-clean fallback for render-and-compare refinement.

### BundleSDF (CVPR 2023) — https://github.com/NVlabs/BundleSDF (NVIDIA Source Code License, NON-COMMERCIAL)
- Model-free joint pose tracking + neural SDF from RGB-D video of an unknown object (hand-held OK).
  See section 6 for reconstruction numbers. Slow (offline; pose graph + NeRF). The organisers ship
  `v2d_bundlesdf` (SDF+texture from given poses/depth/masks).

### Newer / to watch
- ProxyPose (arXiv 2607.06555, Jul 2026): video-to-video translation into a proxy polyhedron, no mesh,
  one clicked pixel; claims SOTA tracking (no numbers extracted; code UNKNOWN).
- BOP-H3 SAM-FP / NOVASplat / X0 / 3PT-Pose: leaderboard entries without checked papers.


---------------------------------------------------------------------------------------------
## 3. Video segmentation / open-vocabulary detection

Object names per episode are known from the kit object list, so detection is only an initialiser;
the hard parts are (a) masks through hand occlusion and re-appearance, (b) thin spoon masks,
(c) consistent identity for two similar objects (cups, cup+dish rack).

### SAM 2 / SAM 2.1 (Meta, 2024) — https://github.com/facebookresearch/sam2 (Apache-2.0 code AND weights)
- Promptable image+video segmentation with memory. SAM2.1 checkpoint table (README): hiera_large
  224.4M params, 39.5 FPS (A100), SA-V test 79.5 J&F, MOSE val 74.6, LVOS v2 80.6; tiny 38.9M 91.2 FPS
  76.5 SA-V. MOSEv2 (harder: disappearance/occlusion; arXiv 2508.05630) drops SAM2-L to ~50 J&F,
  occlusion-subset J&F_r 26.2 (SAMURAI-L 33.8, DAM4SAM-L 48.8 overall) -> long occlusion is the weak spot.
- Fit: OSI-clean default. Used by organiser baseline. Re-prompt after occlusion with detector boxes.

### SAM 3 / SAM 3.1 (Meta, Nov 2025; 3.1 Mar 2026) — https://github.com/facebookresearch/sam3 , arXiv 2511.16719
- Promptable Concept Segmentation: text phrase or image exemplar -> all instances, masks + identities,
  in images and video; 848M params; DETR detector + SAM2-style tracker sharing an encoder. SAM 3.1
  adds shared-memory joint multi-object tracking ("significantly faster", README).
- Evidence (paper tables): LVIS zero-shot box/mask AP 48.5/37.2 (OWLv2 35.2/20.1, DINO-X 38.5/21.3);
  SA-Co/Gold cgF1 54.1 (OWLv2 17.3, Gemini 2.5 13.0; human 72.8). VOS: SA-V test 84.4 vs SAM2.1-L 78.4;
  MOSEv2 val 60.3 vs 47.9; DAVIS17 92.2 vs 90.7. Image 30 ms with 100+ objects on H200; video near
  real-time for ~5 concurrent objects on H200.
- Requirements: Python 3.12+, PyTorch 2.7+, CUDA >= 12.6. HF weights manually gated.
- Licence: SAM License (custom; commercial use not prohibited in text grep; AUP + trade controls).
  NOT OSI. Pretrained-model exception may cover the weights; the code is under the same licence -> A1.
- Fit: best for "wooden spoon" / "hand" text prompts and re-detection after occlusion; biggest
  measured gain over SAM2 is exactly on occlusion-heavy MOSEv2 (+12.4 J&F).

### Cutie (CVPR 2024) — https://github.com/hkchengrex/Cutie (MIT)
- Object-level memory VOS, semi-supervised (first-frame mask). Strong on MOSE v1 in its paper; weak
  in MOSEv2 table as "Cutie+SAM" 17.3 J&F (setting differs; UNVERIFIED comparability).
- Fit: MIT fallback; SAM2/3 now stronger.

### Grounding DINO (ECCV 2024) — https://github.com/IDEA-Research/GroundingDINO (Apache-2.0)
- Text -> boxes. Organiser baseline uses it. Grounding DINO 1.5/1.6 and DINO-X are API-only (not
  usable offline for a reproducible release). Original paper zero-shot COCO ~52.5 AP for Swin-L (from
  memory, UNVERIFIED here).
### OWLv2 (NeurIPS 2023) — scenic (Apache-2.0); HF google/owlv2-* (Apache-2.0)
- Open-vocab boxes + image-conditioned (one-shot) detection: useful to find the spoon from a query
  crop. LVIS zero-shot box AP 35.2 in SAM3's table.
### Florence-2 (CVPR 2024) — HF microsoft/Florence-2-large (MIT weights)
- Generalist VLM-ish detector/grounding/captioning; 0.23B/0.77B. No numbers extracted here; usable as
  an OSI-clean phrase-grounding fallback.

Recommendation: SAM2.1 (Apache) as compliant core; SAM3 text/exemplar prompts as the accuracy option
if A1 resolves favourably; OWLv2/Grounding DINO for re-detection boxes. Hand masks: SAM3 "hand" prompt
or projected hand meshes (section 7) — the latter also gives occlusion ordering for the tracker.

---------------------------------------------------------------------------------------------
## 4. Stereo depth (ego_cam_b/c, 1280x800 mono, 75 mm baseline)

Geometry (from track3-requirements.md): fx ~562 px -> disparity ~84 px at 0.5 m; 0.25 px disparity
error -> ~1.5 mm depth error at 0.5 m, ~3 mm at 0.7 m. Stereo depth is in the mono-left frame and must
be reprojected into the 2028x1520 colour camera via factory extrinsics (occlusion holes, edge bleeding,
synchronisation offset between colour and mono — UNVERIFIED whether the OAK streams are hardware synced).

### FoundationStereo (CVPR 2025, NVIDIA) — arXiv 2501.09898, https://github.com/NVlabs/FoundationStereo
- Zero-shot disparity; ViT-L (23-51-11) and ViT-S (11-33-40) checkpoints; DepthAnythingV2 features +
  cost filtering; 1M synthetic pairs. Ranked 1st on Middlebury and ETH3D when released (README).
  Fast-FS paper table: Middlebury-H BP-2 2.49, ETH3D BP-1 1.10, KITTI-15 D1 2.80, 496 ms on RTX 3090.
  README: TensorRT FP16 ~6x faster on 3090.
- Licence: NVIDIA Source Code License, "research purposes only" (code + weights) -> NON-COMMERCIAL.
  BUT NGC "NVIDIA-TAO" FoundationStereo (ViT-small-derived, 63M params, frozen DAv2 + EdgeNeXt) is under
  the NVIDIA Open Model License, "ready for commercial use"; A100 latency ~199 ms at 320x736, ~437 ms at
  576x960 (https://catalog.ngc.nvidia.com/orgs/nvidia/tao/models/foundationstereo). Fixed input
  resolutions (320x736, 576x960) or dynamic via ONNX only -> 1280x800 needs resizing/tiling (accuracy cost).
  NVIDIA Open Model License is not OSI, but it is a *model* licence; inference code we would write.
- Organiser wrapper `v2d_foundation_stereo` exists (TensorRT engine export).

### Fast-FoundationStereo (CVPR 2026, NVIDIA) — arXiv 2512.11130, https://github.com/NVlabs/Fast-FoundationStereo
- Distilled 14.6M params; Middlebury-H BP-2 2.20, ETH3D BP-1 1.22, KITTI-15 D1 3.25; 49 ms (21 ms TRT)
  on 3090. Licence: NVIDIA Source Code License "research purposes only" -> NON-COMMERCIAL.
### DEFOM-Stereo (CVPR 2025) — https://github.com/Insta360-Research-Team/DEFOM-Stereo (MIT)
- DepthAnythingV2-initialised recurrent stereo. Fast-FS table: Middlebury-H BP-2 3.76, ETH3D BP-1 1.03,
  KITTI-15 D1 4.58, 371 ms (3090). Note DAv2 ViT-L backbone weights are CC BY-NC; ViT-S is Apache —
  check which DEFOM checkpoint embeds which (UNVERIFIED).
- Fit: best OSI-licensed (code) high-accuracy stereo option found.
### MonSter (CVPR 2025): Fast-FS table Middlebury-H BP-2 4.24, ETH3D BP-1 0.46, KITTI D1 3.41, 336 ms.
  Licence not checked.
### Stereo Anything (arXiv 2411.14053): mixed-data scaling; code in XiandaGuo/OpenStereo which has NO
  LICENSE file -> unusable for compliant release.
### Newer efficient: Lite Any Stereo V2 (arXiv 2606.24457), LiteMatch (arXiv 2606.31636, claims SOTA ETH3D
  over FoundationStereo) — not inspected; licences unknown.
- Classical fallback: OpenCV SGBM (Apache-2.0) — far worse on texture-poor tabletops; useful as a sanity
  check and as an OSI-clean baseline for the ablation.

Fit summary: object-scale depth (5-30 cm objects at 0.4-0.8 m) is where learned stereo shines over
mono depth (metric, no scale ambiguity). Thin spoon (~1-2 cm wide handle) is ~20-40 px wide in mono
1280 images at 0.5 m -> resolvable, but expect edge fattening; validate on public episodes' scanned
objects (Chamfer of stereo-fused cloud vs scan after rigid alignment with mocap GT).

---------------------------------------------------------------------------------------------
## 5. Metric monocular depth (colour camera)

Role: fallback/complement where stereo fails (colour FOV outside stereo overlap, specular/transparent),
and as a prior for SLAM scale; NOT the primary metric source given a calibrated stereo pair.
MoGe-2 paper Table 2 (arXiv 2507.02546, averaged over 7 datasets; metric point maps Rel / delta1):
MoGe-2 8.19 / 93.6; UniDepth V2 10.1 / 91.9; UniDepth V1 12.1 / 87.2; Depth Pro 13.7 / 81.9.
Metric depth without GT intrinsics: MoGe-2 15.7 / 76.8; UniDepth V2 21.3 / 75.3; Depth Pro 27.6 / 54.4;
DA V2 29.9 / 56.6. => ~8-16% relative error, i.e. 4-8 cm at 0.5 m: an order of magnitude worse than stereo.
| Model | Licence (weights) | Runtime | Note |
|---|---|---|---|
| MoGe-2 (Microsoft, 2025) https://github.com/microsoft/MoGe | MIT code, MIT weights (HF Ruicheng/moge-2-*) | 29 ms @484^2, 39 ms @700^2, A100 FP16; 326M | OSI-clean; organiser baseline uses it |
| UniDepth V2 (2025) https://github.com/lpiccinelli-eth/UniDepth | CC BY-NC 4.0 | — | NON-COMMERCIAL |
| Depth Anything 3 (ByteDance, Nov 2025) https://github.com/ByteDance-Seed/Depth-Anything-3 | code Apache-2.0; DA3-GIANT/LARGE/NESTED CC BY-NC; DA3METRIC-LARGE, DA3-BASE, DA3-SMALL, DA3MONO-LARGE Apache-2.0 | DA3-Streaming <12 GB | any-view depth + pose; metric only via METRIC/NESTED; numbers not extracted |
| Depth Pro (Apple, ICLR 2025) https://github.com/apple/ml-depth-pro | weights "apple-amlr" (Apple ML Research licence, research use) | 139 ms @1536^2 (A100, MoGe-2 table) | NON-COMMERCIAL; sharp boundaries |
Use case: MoGe-2 (MIT) on the colour image, scale-aligned per frame to stereo depth on static
background, gives dense colour-frame depth with stereo-metric scale and fewer reprojection holes.

---------------------------------------------------------------------------------------------
## 6. Ego-motion / SLAM (13 s, head-mounted, static tabletop + moving hands/objects)

Requirement: camera-to-world poses in a metric, gravity-aligned frame over ~262 frames; dynamic hands
and manipulated objects must be masked. Object-in-world error = camera pose error (+) object-in-camera
error, so camera drift adds directly to MPPE/RPE. A 13 s clip is short: drift should be mm-level with a
good stereo VO; failure modes are fast head rotation, motion blur, and hands filling the view.
| Method | Sensors | Accuracy evidence | Runtime | Licence | Fit |
|---|---|---|---|---|---|
| cuVSLAM / PyCuVSLAM (NVIDIA, arXiv 2506.04359) | mono, stereo, multi-stereo, +IMU, RGB-D | stereo EuRoC avgRTE 0.17%, RMSE APE 0.054 m; KITTI 0.27%; mono-depth TUM APE 0.065 m | stereo 0.4 ms/frame RTX 4090 | NVIDIA Community License (commercial OK, NVIDIA platforms only); closed core; paper CC BY-NC-ND | fast stereo baseline; used inside organiser cuSFM and ViPE; static-mask support needs checking; not OSI |
| ORB-SLAM3 (2021) https://github.com/UZ-SLAMLab/ORB_SLAM3 | mono/stereo/RGB-D(+IMU) | well-known EuRoC stereo cm-level | CPU real time | GPL-3.0 (OSI copyleft; our release is Apache-2.0 -> keep as separate process/tool, licence-compatibility question) | needs dynamic masks via code edits; 1280x800 greyscale fine |
| DROID-SLAM (NeurIPS 2021) https://github.com/princeton-vl/DROID-SLAM | mono, stereo, RGB-D | EuRoC mono avg ATE 0.022 m (MASt3R-SLAM table); TUM 0.038 m | ~ real time-ish, high VRAM | BSD-3 (weights trained on TartanAir) | stereo mode + per-pixel masks feasible via weight maps; organiser baseline uses mono DROID |
| DPVO / DPV-SLAM (2023-24) https://github.com/princeton-vl/DPVO | mono | EuRoC 0.023 m (DPV-SLAM++) | fast, low VRAM | MIT | mono only -> needs scale from stereo |
| MASt3R-SLAM (CVPR 2025) https://github.com/rmurai0610/MASt3R-SLAM | mono (calib or not) | TUM 0.030 m; EuRoC 0.041 m (worse than DROID 0.022) | 15 FPS RTX 4090 | CC BY-NC-SA 4.0 | NON-COMMERCIAL; no advantage here |
| MegaSaM (CVPR 2025) https://github.com/mega-sam/mega-sam | mono dynamic video | claims SOTA on Sintel/DyCheck (numbers NOT extracted) | offline | Apache-2.0 code; deps (DepthAnything, UniDepth CC BY-NC) | designed for dynamic monocular; stereo makes it unnecessary |
| ViPE (NVIDIA, arXiv 2508.10934) https://github.com/nv-tlabs/vipe | mono video (+ rig extension in paper) | TUM fr1 ATE 3.6 cm (MegaSaM 7.0, DROID 4.4); KITTI 9.2 m (MegaSaM 25.4, VGGT 23.8) | 3-5 FPS 640x480 RTX 5090 | Apache-2.0 code; metric prior choice Metric3Dv2 / UniDepthV2 (NC) / UniK3D; GroundingDINO+SAM+XMem dynamic masks | organiser hand path uses it; multi-camera rig support in released code UNVERIFIED |
| VGGT (CVPR 2025) https://github.com/facebookresearch/vggt | feed-forward multi-view | (not extracted) | ~1 s for tens of frames; hundreds of frames need >40 GB (UNVERIFIED) | VGGT-1B CC BY-NC; VGGT-1B-Commercial gated, custom licence | init / loop closure only |
| pi3 (2025) https://github.com/yyfz/Pi3 | feed-forward, permutation-equivariant | (not extracted) | — | code BSD-3; Pi3 weights BSD-2; Pi3X CC BY-NC | OSI-clean feed-forward option |
| MapAnything (Meta, 2025) https://github.com/facebookresearch/map-anything | feed-forward, accepts intrinsics/poses/depth as optional inputs, metric | (not extracted) | — | code Apache-2.0; `map-anything-apache` weights Apache-2.0; default weights CC BY-NC | can ingest stereo calibration + stereo depth; worth a test for robust init |
Recommendation: stereo VO on the mono pair with hand/object masks (cuVSLAM for speed, DROID-SLAM
stereo for robustness and OSI licence), refined by a short offline bundle adjustment with the colour
camera added via factory extrinsics. Gravity from table-plane normal (fit to stereo points on the
static support surface) cross-checked with GeoCalib; both need validation on public episodes.


Dependency licence traps (checked 2026-10-04 via GitHub API/LICENSE text):
- nvdiffrast (NVlabs): NVIDIA Source Code License, "research or evaluation purposes only" -> NON-COMMERCIAL.
  Used by FoundationPose, BundleSDF texture baking, TRELLIS/TRELLIS.2, many render-and-compare codes.
  An OSI replacement would be PyTorch3D rasteriser (BSD-3) or gsplat (Apache-2.0) for splats.
- tiny-cuda-nn: BSD-3 (OK). PyTorch3D: BSD (OK). DINOv2: Apache-2.0 (OK). DINOv3: custom "DINOv3 License".
- MANO: MPI research licence (non-commercial); manopth GPL-3.0; manotorch Apache-2.0 (code only, still
  needs the MANO .pkl).
- ultralytics (YOLO) AGPL-3.0 — OSI but copyleft-network; avoid in an Apache release.
- GeoCalib Apache-2.0; LightGlue Apache-2.0 (SuperPoint weights are non-commercial; ALIKED/DISK OK —
  verify per extractor); RAFT BSD-3.

---------------------------------------------------------------------------------------------
## 7. Object reconstruction (own meshes for CD-O; Chamfer after Sim(3) => shape only, scale free)

CD-O is scale/pose invariant (Sim(3) registration), so shape fidelity incl. UNSEEN sides is what
matters; but the SAME mesh at metric scale drives tracking and the physics sim, so scale still matters
for everything else. Two families: (a) multi-view fitting from the clip (accurate where observed, holes
where not: table-contact faces, inside of pots/cups), (b) single-image generative (complete but
hallucinated detail). Best expected: generative completion constrained by multi-view observations.

### BundleSDF (CVPR 2023) — https://arxiv.org/abs/2303.14158 (NVIDIA Source Code License, NON-COMMERCIAL)
- RGB-D video of an unknown rigid object, hand-held allowed -> object poses + neural SDF mesh+texture.
- HO3D: ADD-S 96.52 / ADD 92.62, object Chamfer 0.57 cm (DROID-SLAM baseline 30.84 cm); YCBInEOAT
  CD 1.16 cm; BEHAVE CD 4.66 cm. Online thread ~10.2 Hz + offline NeRF rounds ~6.7 s each, RTX 3090.
- Fails when severe occlusion + segmentation error + low texture + geometric ambiguity co-occur;
  requires depth; rigid only.
- Fit: the closest published match to our problem when fed stereo depth. Organisers ship v2d_bundlesdf.
  Licence is the blocker for a compliant release (code + nvdiffrast).

### SAM 3D Objects (Meta, Nov 2025; CVPR 2026) — arXiv 2511.16624, https://github.com/facebookresearch/sam-3d-objects
- Single image + mask -> mesh or Gaussian splat with texture AND pose/layout (scale is only an estimate).
  Human-preference win rate >= 5:1 vs prior work on real objects; SA-3DAO F1@0.01 0.2344, CD 0.04
  (normalised units; from search snippet, UNVERIFIED in paper table). Encoder weights released Jun 2026;
  SA-3DAO artist-object benchmark + HF leaderboard Jun 2026. Fast-SAM3D (arXiv 2602.05293) speeds it up.
- Licence: SAM License (custom, commercial not prohibited). HF repo manually gated, 13.3 GB.
- Organiser baseline and CARI4D use it with a separate scale step ("mesh autoscaling" known issue).
- Fit: strongest single-image prior for kitchen objects (pots, cups, brush, spoon); pick the least
  occluded frame (or several and select by multi-view silhouette/depth agreement).

### TRELLIS (CVPR 2025) / TRELLIS.2 (Microsoft, 2025) — https://github.com/microsoft/TRELLIS.2 (MIT)
- Image -> textured PBR mesh; TRELLIS.2 4B params, >= 24 GB VRAM, H100: 3 s @512^3, 17 s @1024^3, 60 s
  @1536^3. TRELLIS v1 supports multi-image conditioning (experimental). Code+weights MIT, but depends on
  nvdiffrast (NON-COMMERCIAL) and nvdiffrec.
- Fit: OSI-licensed generative alternative to SAM3D; compare both on public-episode objects.

### Hunyuan3D-2.1 (Tencent, Jun 2025) — https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1
- Image -> shape (10 GB VRAM) + PBR texture (21 GB), 29 GB combined. Shape metrics ULIP-T 0.0774 vs
  TRELLIS 0.0769 (self-reported, tiny margins). Hunyuan3D-2mv takes multi-view images.
- Licence: Tencent Hunyuan 3D community licence; does NOT apply in EU, UK, South Korea -> custom, territorial.

### 2DGS / 3DGS / gsplat
- Inria 3DGS and hbb1 2DGS reference code: research/evaluation-only licence (NON-COMMERCIAL).
- gsplat (nerfstudio) Apache-2.0 implements 3DGS and 2DGS rasterisation -> OSI-clean route to
  object-centric splatting: express each frame in the object frame (inverse of tracked object pose),
  mask to the object, fit 2DGS with stereo depth + normal supervision, extract mesh (TSDF of rendered
  depth). Organiser baseline already has a `--run_gsplat_refinement` stage.
- Fit: refine generative mesh/texture and object pose jointly; needs good masks and poses first.

### Hand-object video reconstruction (template-free)
- HOLD (CVPR 2024, MIT code, MANO) — monocular video, hand + object neural fields, no template; HO3D object
  CD 1.31 cm, MPJPE 30.79 mm in MagicHOI's table. Per-sequence optimisation, slow (hours; UNVERIFIED).
- MagicHOI (arXiv 2508.05506, code https://github.com/byran-wang/MagicHOI Apache-2.0; deps Zero-1-to-3
  (Stable-Diffusion-derived OpenRAIL) + MANO) — short monocular clips with limited view variation (our
  case); HO3D CD 0.87 cm vs HOLD 1.31; F10 92.15 vs 80.23; hand MPJPE 4.62 vs 30.79 mm (as reported;
  MPJPE gap looks like a different alignment protocol — UNVERIFIED). Runtime not reported.
- HORT (arXiv 2503.21313): single-image hand-held object point clouds (transformer), fast; not checked.
- Fit: these are monocular and fight scale ambiguity that our stereo removes; borrow ideas (diffusion
  prior for unseen sides, hand-contact constraints) rather than run as-is.

### Wooden spoon (no scan) — specific notes
- Thin (handle ~1-2 cm), elongated, near-symmetric about its long axis, wood texture weak, often
  partially occluded by the grasping hand. Problems: stereo edge fattening, SAM masks merging with
  hand, roll about long axis weakly observable, generative models may produce a generic spoon bowl.
- Options: (1) SAM3D/TRELLIS from best frame + metric scale from stereo length; (2) parametric spoon
  (bowl ellipsoid + tapered cylinder) fitted to stereo points and silhouettes across frames — a
  hypothesis, cheap and robust for CD-O since spoons are simple; (3) multi-view 2DGS in object frame.
  Evaluate shapes on any similar public objects (dust brush, dustpan handles) as proxies.


---------------------------------------------------------------------------------------------
## 8. 3D hands

Downstream constraint: the organiser retargeting script (robotic_grounding/scripts/retarget/
ego_recon_to_sharpa.py) needs a MANO .pkl, so MANO parameters are the de-facto interface; MANO itself
is research-licensed (A3). OSI-clean alternative rig: Meta MHR (Momentum Human Rig, Apache-2.0,
https://github.com/facebookresearch/MHR) used by SAM 3D Body (hands via optional hand decoder) — would
need our own MHR->Sharpa retarget. Hands matter for (a) occlusion masks/ordering for object tracking,
(b) contact priors, (c) the policy reference (retarget), not for any Kaggle metric directly.
| Method | Output | Evidence | Runtime | Licence | Fit |
|---|---|---|---|---|---|
| HaMeR (CVPR 2024) https://github.com/geopavlakos/hamer | per-frame MANO from crop (ViT-H) | FreiHAND PA-MPJPE 6.0 mm; HO3Dv2 7.7 mm; HO-Cap egocentric MPJPE 28.9 mm (absolute) | ~tens of ms/crop (UNVERIFIED) | MIT code; MANO + ViTPose/detectron2 deps | baseline default; camera-frame depth of hand is the weak axis |
| WiLoR (CVPR 2025) https://github.com/rolpotamias/WiLoR | detector (138-175 FPS) + MANO refiner | FreiHAND 5.5 mm, HO3Dv2 7.5 mm PA-MPJPE | real-time on RTX 4090 | CC BY-NC-ND 4.0 | NON-COMMERCIAL; organiser baseline uses its detector |
| HaWoR (CVPR 2025) https://github.com/ThunderVVV/HaWoR | world-space MANO from egocentric video; DROID-SLAM with hand masking + Metric3D scale; motion infiller for out-of-view hands | HOT3D W-MPJPE 33.20 mm, WA-MPJPE 11.27 mm (HMP-SLAM 119.41/39.46) | 40 ms/frame forward | CC BY-NC-ND 4.0 | NON-COMMERCIAL; idea (mask hands in SLAM, infill) transferable |
| Dyn-HaMR (CVPR 2025) https://github.com/ZhengdiYu/Dyn-HaMR | 4D two-hand MANO with dynamic camera (SLAM + HaMeR init + interacting-hand prior) | numbers not extracted | optimisation, minutes/clip (UNVERIFIED) | MIT code; MANO deps | organiser `v2d_ego_hand_reconstruction` (with ViPE) |
| SAM 3D Body (Meta, 2026) https://github.com/facebookresearch/sam-3d-body | full body MHR incl. hands, promptable (keypoints/masks) | lightweight hand decoder within 0.3 mm PA-MPJPE of full decoder on FreiHAND, 4.6x faster (Fast SAM 3D Body arXiv 2603.15603) | — | SAM License (weights gated) | egocentric view shows hands/forearms only; body model may be overkill |
| GeoHand (arXiv 2605.17354) | monocular MANO | FreiHAND PA-MPJPE 5.1 mm | — | not checked | newer SOTA claim |
| ECCV 2024 Multiview Egocentric Hand Tracking 1st place (arXiv 2409.19362, Jiiov) | multi-view MANO with extrinsics, neural smoothing | UmeTrack 13.92 mm, HOT3D 21.66 mm MPJPE | offline | code not found | multi-view + smoothing is the recipe that wins |
Stereo opportunity (our rig): HOT3D baseline (arXiv 2411.19167) two-view UmeTrack MPKE 10.9 vs
single-view 15.4 mm on HOT3D (-29%). Practical recipe: HaMeR/WiLoR-style per-view MANO on colour +
both mono views, then fit one MANO per frame to all views' 2D keypoints + stereo depth of the hand
surface, temporally smoothed (hypothesis: should beat single-view absolute depth by a large margin).

---------------------------------------------------------------------------------------------
## 9. Joint hand-object methods and benchmarks

### Benchmarks (what each tells us)
- HOT3D (Meta, CVPR 2025; arXiv 2411.19167; toolkit Apache-2.0 https://github.com/facebookresearch/hot3d):
  833+ min, 3.7M+ images, Aria + Quest 3, 33 rigid objects, optical mocap GT, 19 subjects. Closest public
  analogue to our data (head-mounted, greyscale stereo + RGB, tabletop/kitchen objects). Baselines:
  FoundPose 6DoF recall@(10 cm,10 deg) single vs multi-view Aria 41.7 -> 52.9, Quest3 46.6 -> 55.9;
  3D lifting of in-hand objects with GT masks recall@10 cm: StereoMatch 96.8 (Quest3, 2 views) /
  86.2 (Aria, 3 views) vs MonoDepth 30.2 (Aria). => STRONG evidence for stereo over mono depth for
  in-hand objects. Used by BOP-H3 and ECCV 2024 hand challenge.
- ARCTIC (CVPR 2023, https://github.com/zc-alexfan/arctic, non-commercial): bimanual articulated objects,
  egocentric + allocentric; HANDS@ICCV 2025 ARCTIC challenge 1st place "GHOST" (Gaussian hand-object
  surface reconstruction with geometric priors) — details UNVERIFIED.
- DexYCB (CVPR 2021, toolkit GPL-3.0): 8 static RGB-D views, YCB objects, grasping; standard for
  hand+object pose; static cameras (less like ours).
- HO-Cap (NVIDIA/UT Dallas 2024, arXiv 2406.06843, https://irvlutd.github.io/HOCap): 8 RealSense +
  Azure Kinect + HoloLens egocentric; 64 videos, 656K frames, 64 objects. Benchmarks on hand-object
  occlusion with real depth: FoundationPose ADD 89.3 / ADD-S 95.7 AUC vs MegaPose 67.1 / 83.0; HaMeR
  MPJPE 28.9 mm; GroundingDINO novel-object detection 17.0 mAP vs CNOS 25.3. Its annotation pipeline
  (BundleSDF recon -> FoundationPose tracking -> multi-view SDF optimisation of hand+object) is itself a
  template for our offline refinement.
### Methods
- HOLD (CVPR 2024, MIT, MANO): template-free monocular hand+object; HO3D object CD 1.31 cm.
- MagicHOI (2025, Apache-2.0 code, Zero-1-to-3 prior + MANO): HO3D CD 0.87 cm, F10 92.15.
- BundleSDF (above): object-only but robust to hand occlusion with depth; HO3D CD 0.57 cm.
- CARI4D (NVIDIA, organiser module v2d_cari4d; `nvidia/cari4d_commercial` checkpoint): human-object
  4D from monocular RGB + object mesh; MoGe-2 init, SAM 3D Body, FoundationPose, CoCoNet, contact-guided
  refinement (300 steps). Designed for full-body; licence of the commercial checkpoint not read.
- Common refinement ingredients (literature + our hypotheses): contact consistency (hand surface within
  ~5 mm of object where contact predicted; CARI4D uses 0.05 m activation), non-penetration with table
  and hand, object static when not contacted, temporal smoothness, gravity/support (object rests on
  table at start/end). These are cheap to add as a post-hoc factor graph over FP outputs.


---------------------------------------------------------------------------------------------
## 10. Addenda found late (keep with section 2/7)

- 6DOPE-GS (ICCV 2025, arXiv 2412.01543): model-free RGB-D pose tracking + incremental 2DGS object
  reconstruction; HO3D ADD-S 95.07 / ADD 84.33 / CD 0.41 cm (BundleSDF in same table 94.86 / 89.56 / 0.58);
  YCBInEOAT 93.79 / 87.82 / CD 0.15 cm (BundleSDF 92.82 / 84.28 / 0.53); 0.22 s/frame on RTX 4090, ~5x
  faster than BundleSDF (~2.1 s/frame). Requires RGB-D + per-frame masks. Only a project page repo
  (YufengJin/6dope-gs-page, MIT) found; implementation release UNVERIFIED. Shows the 2DGS-in-object-frame
  idea from section 7 is published and competitive with BundleSDF on reconstruction.
- MapAnything (Meta, 3DV 2026): feed-forward metric reconstruction from any mix of images, intrinsics,
  poses, depth; `facebook/map-anything-apache` weights Apache-2.0 (default weights CC BY-NC). Claims better
  memory/speed than VGGT/Pi3X for 2-1000 views (README graphs, numbers not extracted).
- VGGT: VGGT-1B (CC BY-NC); VGGT-1B-Commercial (Jul 2025, custom licence, gated form, Co3D AUC@30 90.37 vs
  89.98); VGGT-Omega released May 2026 (not inspected); May 2026 memory optimisation ~2-3x more frames.
- Challenge FAQ (docs/v2d_challenge/assets/v2d_challenge_2026_faqs.pdf, 2026-10-02, read via pdftotext):
  "Winning submissions will be asked to release their code under an Apache 2.0 license." and
  "Pretrained models and external data are allowed for all tracks." It says nothing about OSI status
  of third-party code -> the Kaggle foundational-rule constraint (A1) is the only stricter text; ask.
  Same FAQ: "participants should submit their own reconstructed meshes" (CD-O); Track 1 answers (not
  ours) say objects must be output continuously through occlusion — expect the same for Track 3.

---------------------------------------------------------------------------------------------
## 11. Fit analysis for our rig (hypotheses, to be tested — not measured)

H-fit-1 Stereo first. Evidence: HOT3D 3D lifting of in-hand objects recall@10 cm StereoMatch 96.8 vs
  MonoDepth 30.2; MoGe-2 metric Rel ~8-16 % (4-8 cm at 0.5 m) vs stereo ~1.5-3 mm per 0.25 px. The
  organiser ego baseline is monocular; this is the largest expected gain available to us.
H-fit-2 Track on the global-shutter mono-left camera, not (only) on colour. Depth is native there (no
  reprojection holes, no colour-mono sync/rolling-shutter error). The colour camera is probably rolling
  shutter (OAK 12 MP sensors usually are; UNVERIFIED for this rig) and is mounted rotated 180 deg.
  Use colour for segmentation/appearance/texture; run FoundationPose-style refinement on both views
  offline (multi-view render-and-compare) — HOT3D shows multi-view FoundPose +9-11 recall points.
H-fit-3 Object-in-world = camera pose (+) object-in-camera. Camera error from a masked stereo VO over
  13 s should be small compared with object tracking error; verify via objects that are static in
  mocap (any apparent motion = camera + tracker error).
H-fit-4 Occlusion handling dominates errors (hands grasp objects). Expect FP losses at grasp and
  re-appearance; SAM3 improves masks most under occlusion (MOSEv2 +12.4 J&F). During full occlusion
  the object most likely moves rigidly with the grasping hand -> hand-attached bridging.
H-fit-5 Mesh quality and canonical frame. CD-O ignores scale/pose, but tracking ADD and the simulated
  physics use the mesh at metric scale and in its own canonical frame. Reference poses are in the scan
  frame; a constant mesh-frame offset becomes a pose error (also for slot 0, by conjugation). For the 9
  scanned objects we can learn the convention; for the spoon we cannot (ask organisers).
H-fit-6 Thin spoon. Expect the worst masks, depth and roll observability; the cheapest robust shape
  may be a fitted parametric spoon; validate by silhouette IoU over all frames and both cameras.

---------------------------------------------------------------------------------------------
## 12. Recommended perception stacks (proposed; none tested)

Legend licence: [OSI] OSI-clean code+weights; [W] only weights non-OSI (pretrained-model exception may
apply); [NC] non-commercial code (A1 risk); [M] MANO-dependent.

### S1 Conservative — organiser-aligned stereo stack (fastest path to a working, defensible result)
1. Stereo rectification from factory calibration; FoundationStereo ViT-L (TensorRT) on ego_cam_b/c
   [NC], or NGC TAO FoundationStereo [W, NVIDIA Open Model License] -> metric depth on mono-left,
   reprojected to colour.
2. Object masks: Grounding DINO boxes with the known object names -> SAM2.1-L video propagation on
   colour (+ mono-left) [OSI]; re-prompt from detector when mask area/score collapses.
3. Camera: PyCuSFM/cuVSLAM stereo via organiser `v2d_cusfm` [custom, not OSI] or DROID-SLAM stereo
   [OSI], hands/objects masked; gravity from RANSAC table plane on stereo points (GeoCalib cross-check).
4. Mesh: organiser BundleSDF path (`v2d_bundlesdf`) on stereo depth + masks + tracked poses [NC];
   fallback SAM3D image-to-mesh + stereo metric scale [W].
5. Tracking: FoundationPose register + track with OUR mesh on RGB-D [NC]; re-register on low score.
6. Hands: organiser HaMeR / WiLoR path or ViPE + Dyn-HaMR [M, WiLoR NC]; anchor wrist depth with stereo.
7. Post: per-object smoothing + static-when-untouched + table support.
Compute (ESTIMATE): ~20-40 GPU-min per episode on one L40S/A6000-class GPU; fits 48 GB.
Risk: licence (FP, BundleSDF, FoundationStereo, nvdiffrast all NC); BundleSDF on short 13 s clips
with limited object rotation may leave unseen faces.

### S2 Accurate — offline, multi-view, iterate tracking and reconstruction
1. Depth: FoundationStereo ViT-L full-res + temporal median in static regions; MoGe-2 [OSI] on colour,
   per-frame scale/shift fitted to stereo on static background, to fill holes and the non-overlap FOV.
2. Masks: SAM3.1 text prompts per object name + "hand" [W/custom], exemplar prompt for the spoon,
   cross-checked with SAM2.1; masks on colour AND mono-left; identity consistency by 3D position.
3. Camera: stereo VO (cuVSLAM or DROID-SLAM stereo) then offline BA over colour + both mono cameras
   with fixed factory extrinsics, dynamic masks, table-plane prior; gravity = table normal.
4. Shape (iterate 2-3 rounds): (a) SAM3D and TRELLIS.2 candidates from 3-5 least-occluded frames,
   metric scale from stereo; (b) select/merge by multi-view silhouette + depth agreement over the
   clip; (c) object-centric 2DGS (gsplat [OSI]) or BundleSDF refinement on tracked poses; (d) re-track.
   Spoon: compare generative vs parametric fitted spoon by the same agreement score.
5. Tracking: FoundationPose multi-hypothesis registration + tracking on mono-left (native depth) and
   colour; offline multi-view render-and-compare refinement; loss detection + re-registration
   (Woven/Bonn tracker idea); hand-attached bridging through full occlusion.
6. Hands: per-view WiLoR/HaMeR -> multi-view MANO fit (colour + 2 mono) with stereo hand depth, temporal
   smoothing / infilling (HaWoR/Dyn-HaMR ideas).
7. Joint offline factor graph (gtsam, BSD): object poses, hand poses, camera poses; terms = FP
   residuals, contact (hand-object distance when grasped), non-penetration (hand, table), support
   (object on table at rest), static-when-untouched, smoothness (also helps the acceleration-style
   metrics), gravity.
Compute (ESTIMATE): 1-3 GPU-h per episode, >= 24 GB for TRELLIS.2, gated weights (SAM3, SAM3D).
Risk: most components NC or custom; complexity; needs a strong local validation harness.

### S3 Cheap — low compute, licence-cleanest available
1. Depth: DEFOM-Stereo [MIT code; check DAv2 backbone weight licence] or TAO FoundationStereo [W] at
   reduced resolution; OpenCV SGBM [OSI] as floor.
2. Masks: SAM2.1-S/B+ [OSI] prompted by OWLv2 [OSI] (image-conditioned query for the spoon).
3. Camera: DROID-SLAM stereo [OSI] (or DPVO [OSI] + stereo scale).
4. Mesh: TSDF fusion of masked stereo depth in the object frame (Open3D, MIT) + hole filling /
   symmetry completion; TRELLIS.2 [MIT; nvdiffrast NC dependency] only if fusion is too partial.
5. Tracking: depth-ICP + MegaPose refiner [OSI] (GigaPose [OSI] for (re)initialisation); PyTorch3D
   [BSD] rendering instead of nvdiffrast.
6. Hands: HaMeR [MIT, M] single-view + stereo wrist anchoring; or SAM 3D Body MHR hands [W, MHR Apache]
   if MANO is unacceptable (needs own retarget).
Compute (ESTIMATE): ~5-15 GPU-min per episode; runs on 24 GB.
Risk: MegaPose/ICP clearly weaker than FP under occlusion (HO-Cap: MegaPose ADD 67.1 vs FP 89.3).

---------------------------------------------------------------------------------------------
## 13. Specific open questions to test (each with a falsifiable measurement on the 20 public episodes)

Data/setup (no GT read at inference; evaluator-only use of mocap and scans):
Q1 Stereo depth on our rig: fuse masked stereo depth of each scanned object at mocap GT pose (evaluator
   side) and compute point-to-scan error vs distance; compare FoundationStereo L vs TAO vs DEFOM vs SGBM,
   full vs reduced resolution. Pass if median < 3 mm at 0.4-0.7 m.
Q2 Colour-mono time sync and extrinsics: edge-alignment residual of reprojected stereo depth on colour
   and temporal cross-correlation of motion; is a per-episode time offset needed? Is colour rolling shutter?
Q3 Tracker x depth source: FoundationPose with stereo depth vs MoGe-2 depth vs RGB-only (GoTrack /
   MegaPose) with scanned meshes (dev only) -> ADD AUC 1-9 cm, SP-SR, MP-SR per object. Expect stereo >>.
Q4 Tracking camera: colour vs mono-left vs both (offline multi-view refinement). Does greyscale hurt FP?
Q5 Own meshes: Sim(3) Chamfer to scans (the CD-O metric) for BundleSDF, SAM3D, TRELLIS.2, 2DGS fusion,
   TSDF fusion, and merged; plus tracking ADD with own mesh vs scan (how much does mesh error cost?).
Q6 Canonical frame: how far are our mesh frames from the scan frames, and what does the scorer do for
   the spoon? (organiser question + measurement on scanned objects).
Q7 Camera drift: apparent motion of mocap-static objects in our world frame over 13 s, hands masked vs not.
Q8 Gravity: angle between table-plane normal, GeoCalib, and the mocap world up-axis (if gravity-aligned).
Q9 Masks under occlusion: SAM2.1 vs SAM3.1 IoU against masks rendered from scans at GT poses
   (evaluator-side pseudo-GT), split by occlusion fraction.
Q10 Occlusion bridging: drop frames artificially; compare interpolation, constant velocity, and
   hand-attached rigid bridging.
Q11 Spoon shape: generative vs parametric vs fusion by silhouette/depth agreement on eval-free public
   proxies (thin parts of dust brush/dustpan) and self-consistency on spoon clips.
Q12 Licence: does the organisers' reading of the Kaggle OSS rule allow FoundationPose, BundleSDF,
   FoundationStereo, nvdiffrast, SAM License code, and MANO in a winning solution?
Q13 Hands: is there any hand GT in public episodes? If not, use cross-camera 2D keypoint reprojection
   error as the proxy for single- vs multi-view MANO fitting.

---------------------------------------------------------------------------------------------
## 14. Unverified / not extracted (do not cite as fact)
- SAM-FP (BOP-H3 0.668 AP), NOVASplat, X0, 3PT-Pose: no paper read.
- MegaSaM, VGGT, pi3, DA3, MapAnything numeric accuracy: not extracted.
- Dyn-HaMR numbers, HOLD runtime, SAM3D runtime/VRAM, BundleSDF wall-clock on 13 s clips.
- Grounding DINO COCO 52.5 AP (from memory). HaWoR camera ATE units unclear in extraction.
- DEFOM-Stereo backbone weight licence (DAv2 ViT-L is CC BY-NC; ViT-S Apache).
- Release status of the Woven/Bonn robust tracker, UA-Pose, ProxyPose, 6DOPE-GS code.
- Whether ViPE's released code supports a stereo/multi-camera rig (paper says the formulation extends).
- Colour camera shutter type and colour-mono hardware sync on this rig.
