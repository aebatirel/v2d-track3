# Hand-aware tracking: literature and code review (3 Nov 2026)

Primary sources: arXiv papers, project pages, and the repos' own LICENSE files. Items marked [unverified] could not be
checked against a primary source in this session.

## Methods
| Method | Citation | Code / licence | Inputs | Outputs | Cost | Fit for us |
|---|---|---|---|---|---|---|
| HOLD | Fan et al., CVPR 2024, arXiv 2311.18448 | zc-alexfan/hold, MIT; **needs MANO (non-commercial)** | monocular RGB, **no template**; SAM-Track masks, HLoc SfM object init, MANO regressor | MANO hand + object SDF + per-frame pose (camera frame, scale from MANO) | per-sequence optimisation; initial stage ≈ 10 h on an A100 | low: it solves shape we already have, ignores our metric depth, hours per episode; SfM init fails on thin / textureless objects (boards, sweeper) |
| MagicHOI | Wang, …, Fan, Song, ICCV 2025, arXiv 2508.05506 | byran-wang/MagicHOI, Apache-2.0 (built on HOLD, so MANO applies) | short monocular RGB clip, template-free | hand + object shape and pose | HOLD-like, not stated | low: a diffusion prior for unseen *shape*; we know the shape. Transfers: **visible-fingertip contact** (only fingertips visible in the hand mask, ray-cast to the object) |
| HaMeR | Pavlakos et al., CVPR 2024, arXiv 2312.05251 | geopavlakos/hamer, MIT; MANO non-commercial | single RGB crop | MANO in camera frame, translation from an assumed focal [unverified detail], not metric | ViT-H, heavy | optional upgrade to MediaPipe for a dense hand surface |
| WiLoR | Potamias et al., CVPR 2025, arXiv 2409.12259 | rolpotamias/WiLoR, **code and weights CC-BY-NC-ND 4.0**; MANO; Ultralytics (AGPL) [unverified] | RGB images / video | detection + MANO, camera frame | detector > 130 fps on an RTX 4090 | as HaMeR; per frame |
| HaWoR | Zhang et al., CVPR 2025, arXiv 2501.02973 | ThunderVVV/HaWoR, **CC-BY-NC-ND**; MANO, DROID-SLAM, Metric3D | monocular egocentric RGB video | world-space MANO + camera trajectory, infills occluded frames | not stated | low: we already have metric stereo depth and a camera track (drift 2–9 mm) |
| **HOnnotate** | Hampali et al., CVPR 2020, arXiv 1907.01481 | shreyashampali/HOnnotate, GPL-3.0; MANO | 1–5 calibrated **RGB-D** cameras, **known meshes**, hand / object segmentation | MANO + 6-D object pose, multi-frame | offline batch | **closest precedent** (known meshes + metric depth) |
| ContactOpt | Grady et al., CVPR 2021, arXiv 2104.07267 | facebookresearch/contactopt, MIT; MANO | hand mesh + known object mesh and pose | refines the **hand** only | 62 ms per pair | loss shapes only (asymmetric contact, 2 mm penetration dead zone) |
| HOISDF | Qi et al., CVPR 2024, arXiv 2402.17062 | amathislab/HOISDF, no LICENSE found | single RGB, trained per object set | MANO + object pose | 31 fps | no (trained on YCB objects) |
| BundleSDF | Wen et al., CVPR 2023, arXiv 2303.14158 | NVlabs, NVIDIA source code licence (non-commercial) | RGB-D + first-frame mask, model-free | pose + neural shape | ≈ 10 Hz | no: changes shape; occluded parts never seen |
| Any6D | Lee et al., CVPR 2025, arXiv 2503.18673 | licence unverified | one RGB-D anchor + generated shape | pose + size | not stated | no |
| FoundationPose (ours) | Wen et al., CVPR 2024, arXiv 2312.08344 | NVlabs, NVIDIA source code licence (non-commercial) | RGB-D + mesh | pose | — | current tracker |

HOnnotate's energy (Eq. 1–2): mask (silhouette) + depth residual in the segmented regions + 2-D hand joints + optional
3-D point-cloud term + joint limits + penetration (hand vertices pushed out along the object normal) + a zeroth- and
first-order motion model on hand and object. Ablations: mask or depth alone gives poor poses, together fewer local
minima; penetration does not improve accuracy (more natural grasps only); multi-frame joint optimisation ≈ 15 % better
than single-frame. Its single-camera mode **assumes the grasp varies only marginally over the sequence** (rigid in grasp)
and reaches 0.45 cm object error against the multi-camera annotation.

Accuracy reference (protocols differ, rough guides): HO3D RGB-D tracking AUC (0–10 cm) BundleSDF ADD-S 96.5 / ADD 92.6,
BundleTrack 92.4 / 66.0 (Apache-2.0). With a known mesh and metric RGB-D, ≈ 1 cm is reachable in the literature.

MANO: registration-gated (mano.is.tue.mpg.de), MPI non-commercial research licence, no redistribution. Never commit the
.pkl files.

## Verdict: what transfers
1. **Adopt HOnnotate's objective for the object only, with the hands fixed from our MediaPipe fit** (we have the meshes
   and metric depth, so no shape or scale needs solving): hand-masked depth residual, hand-masked silhouette,
   penetration of hand points into the object, visible-fingertip contact with a dead zone, and a motion prior. Optimise
   over windows, not per frame.
2. **Rigid-in-grasp as a soft prior**: T_hand→object nearly constant across a stable grasp, allowing slips and
   regrasps.
3. **Skip HOLD, MagicHOI and HaWoR**: template-free, monocular, hours per sequence, and they solve shape and scale
   that we already have. HOLD's SfM init also fails on thin, textureless objects.
4. **WiLoR / HaMeR (MANO)** only if MediaPipe's hand proves to be the bottleneck. Non-commercial licences would apply.
5. Licence flags: FoundationPose and BundleSDF NVIDIA non-commercial; WiLoR and HaWoR CC-BY-NC-ND; HOnnotate GPL-3.0
   (ideas only, no code copied); MANO non-commercial.
