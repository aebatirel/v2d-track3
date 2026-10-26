# Generative 3D for V2D Track 3: literature and open-source review

Date: 2026-10-26. Web-only review; nothing in the repo was touched or run.

Evidence labels used throughout:
- **[M]** a number measured and reported in the cited paper or repo (their protocol, not ours).
- **[C]** an author claim with no number behind it.
- **[I]** my inference or hypothesis, with no measurement behind it. Each comes with a falsification test.
- **[U]** stated by a secondary or third-party source, or not verified in a primary source.

---

## 0. Bottom line

1. **No paper reports pure image-to-3D generation at about 1% of object size on real objects.** The best single-image model on a real-image benchmark is SAM 3D: Chamfer 0.040 with objects normalised to [-1,1] and ICP-aligned, which is about 2% of object extent [M] ([SAM 3D paper, Table 2 and App. D.3.1](https://arxiv.org/html/2511.16624v2)). Methods that fuse several views reach 0.059 on OmniObject3D with 4 views [M] ([ReconViaGen](https://arxiv.org/html/2510.23306v1)).
2. **Pipelines that generate a shape and then fit it to observations do beat reconstruction-only pipelines on hand-held objects.**
   - AGILE (Hunyuan3D-2 mesh fitted to video) gets 0.27 cm² Chamfer on HO3D, against 1.11 for HOLD and 0.90 for MagicHOI [M] ([AGILE](https://arxiv.org/html/2602.04672)).
   - MagicHOI's novel-view prior helps only when combined with RGB evidence: CD 1.37 → 0.91 cm [M] ([MagicHOI](https://arxiv.org/html/2508.05506v1)).
3. **The most relevant new tool is Pixal3D's multi-view mode.** Released in Sep 2026, MIT licence, TRELLIS.2 backbone. It takes posed views and generates **in the given camera/world frame**, which removes the rotation-ambiguity and flip risk. On Toys4K with 4 views it reports CD 4.73e-4 against 18.35e-4 for TRELLIS [M] ([Pixal3D paper, Table 3](https://arxiv.org/html/2605.10922); [repo README](https://github.com/TencentARC/Pixal3D)).
4. **Conditioning a generator on a reconstructed point cloud measurably helps.** RecGen3D (VGGT point cloud fed into Hunyuan3D-Omni) cuts Chamfer by about 35–40% against ReconViaGen on GSO and Toys4K [M] ([RecGen3D](https://arxiv.org/html/2604.01479)). We already have a better point cloud: metric stereo depth plus poses.
5. **The organisers' SAM3D baseline aligns each per-frame SAM 3D mesh by silhouettes, with optional depth.** It runs Powell optimisation over up to 25 silhouettes. The baseline itself warns that "unseen geometry is generated rather than reconstructed" and that scale "can be less reliable" [M] ([v2d_hoi_object_reconstruction README](https://github.com/nvidia-isaac/video_to_data/blob/main/reconstruction/modules/v2d_hoi_object_reconstruction/README.md)).
6. **Recommended order:** (A) Pixal3D-MV with our poses, then (B) SAM 3D with our metric pointmap followed by an observation fit, then (C) point-conditioned completion with Hunyuan3D-Omni, or "keep what we observed, generate only what is missing". In every case the generated mesh is then fitted (Sim(3), then light non-rigid) to our observed outer surface, and kept only if it passes an observation-consistency gate. Details are in section 8.
7. **Time is short.** The leaderboard freezes on 2026-11-04 at 17:00 EST, and pretrained models are explicitly allowed. Winners must release their code under Apache-2.0 [M] ([challenge page](https://nvidia-isaac.github.io/video_to_data/v2d_challenge/); [FAQ PDF](https://nvidia-isaac.github.io/video_to_data/v2d_challenge/assets/v2d_challenge_2026_faqs.pdf)).

---

## 1. Rules and organiser baseline facts that matter here

**Challenge rules** ([FAQ PDF](https://nvidia-isaac.github.io/video_to_data/v2d_challenge/assets/v2d_challenge_2026_faqs.pdf), all [M]):
- "Pretrained models and external data are allowed for all tracks."
- "Winning submissions will be asked to release their code under an Apache 2.0 license."
- Track 3 requires our own reconstructed meshes for all 20 eval videos: "participants should reconstruct the objects ... and submit their own reconstructed meshes", even where a public scan exists.
- The final rank is the sum of per-metric ranks, so CD-O and each pose metric weigh equally.

**Dates** ([challenge page](https://nvidia-isaac.github.io/video_to_data/v2d_challenge/), [M]):
- Leaderboard freeze 2026-11-04; winners announced at CoRL on 2026-11-12.
- 5 submissions per week, unlimited in the last 3 days.

**Organiser baseline code** ([v2d_hoi_object_reconstruction README](https://github.com/nvidia-isaac/video_to_data/blob/main/reconstruction/modules/v2d_hoi_object_reconstruction/README.md)):
- The `nvidia-isaac/video_to_data` repo is Apache-2.0 for code and CC-BY-4.0 for docs [M] ([LICENSE](https://raw.githubusercontent.com/nvidia-isaac/video_to_data/main/LICENSE)). It contains `v2d_sam3d`, `v2d_hoi_object_reconstruction`, `v2d_bundlesdf`, `v2d_gsplat_refinement` and `v2d_cari4d` modules ([modules tree](https://github.com/nvidia-isaac/video_to_data/tree/main/reconstruction/modules)).
- The HOI object pipeline has two mesh modes [M]:
  - **BundleSDF:** "reconstructs observed geometry with metric scale"; thin or partly seen parts "can be missing or thickened".
  - **SAM3D:** selects frames every 60° of orbit (or 6 frames by view-direction diversity) and runs SAM 3D on each selected frame. An SRT (scale-rotation-translation) step then fits each per-frame mesh by silhouette optimisation (≤25 views, 60 Powell iterations), with optional FoundationStereo depth (`--sam3d_use_depth`). Candidates are ranked and `best/output_scaled.glb` is kept.
- Measured runtime on 2× RTX A6000 [M]: SAM3D mode took 69 min for 13 frames (14 min sequential SAM 3D inference, 37 min SRT). BundleSDF took about 100 min for 2,433 stereo pairs. At least 24 GB VRAM is needed, and Blackwell sm_120 is not supported.
- **Track 3 egocentric baseline** [U, a competitor's public repo]: HaMeR hands, a SAM3D mesh, scale fitted to MoGe depth on a single frame, and FoundationPose that re-registers from scratch when mask IoU < 0.3, which causes about 180° flips ([zjifan121-source/NVIDIA_V2D_Egocentric](https://github.com/zjifan121-source/NVIDIA_V2D_Egocentric)).
- **CARI4D**, the organisers' related CVPR 2026 HOI method, also uses generation then fitting [M] ([CARI4D](https://arxiv.org/html/2512.11988v1)):
  - It runs Hunyuan3D-2 on the first frame.
  - It fixes scale with a FoundationPose grid search over scales, ranked by one-sided Chamfer to the segmented depth points (UniDepth).
  - It does no shape refinement.
  - An oracle with the ground-truth mesh improves object CD only from 11.57 to 9.26 cm in their (much harder, monocular) setting.

---

## 2. What accuracy do generative methods reach? (Calibrating expectations)

| Evidence | Setting | Number | Label |
|---|---|---|---|
| SAM 3D vs others on SA-3DAO (real images, artist meshes) | single image, [-1,1]-normalised, ICP | CD: SAM 3D 0.040; TripoSG 0.084; HY3D-2.0 0.087; TRELLIS 0.090; Hi3DGen 0.094; Direct3D-S2 0.096; HY3D-2.1 0.113. F1@0.01: SAM 3D 0.234 vs ≤0.163 | [M] [paper](https://arxiv.org/html/2511.16624v2) |
| Cue3D on GSO / Toys4K (rendered) | single image | CD×1000 on GSO: TRELLIS 39.6, Hunyuan3D-2 41.8, InstantMesh 54.5, SF3D 61.6. Native 3D generators beat multi-view-diffusion + LRM pipelines | [M] [Cue3D](https://arxiv.org/html/2511.22121) |
| ReconViaGen (VGGT + TRELLIS), 4 unposed views | [-1,1]³, 100k points | OmniObject3D CD 0.059 vs TRELLIS-M 0.072, VGGT 0.091, HY3D-2mv 0.124. Dora-bench 8 views: 0.081 | [M] [paper](https://arxiv.org/html/2510.23306v1) |
| RecGen3D (VGGT point cloud → Hunyuan3D-Omni), 4 views | ICP-aligned, F@0.01 | GSO CD-L2 0.0192 vs ReconViaGen 0.0290, SAM 3D 0.0296, TRELLIS-M 0.0318 | [M] [paper](https://arxiv.org/html/2604.01479) |
| Pixal3D multi-view, posed | Toys4K | CD×1e-4 for 2/4/6 views: 5.27/4.73/4.16 vs TRELLIS 21.4/18.4/18.1. F 64.9/67.9/69.0 vs ≈44–46. Normalisation not stated | [M] [paper](https://arxiv.org/html/2605.10922) |
| AGILE: Hunyuan3D-2 mesh from VLM-chosen keyframes, then fitted | HO3D-v3, real hand-held | CD 0.27 cm² vs HOLD 1.11 and MagicHOI 0.90. F@5mm 86.6%. Baseline numbers are averaged over successful runs only | [M] [AGILE](https://arxiv.org/html/2602.04672) |
| GenPC: keep partial points, generate missing (TRELLIS.2 / InstantMesh) | Redwood real scans | CD×100 1.74 vs SDS-Complete 2.72, PoinTr 2.89 | [M] [GenPC](https://arxiv.org/html/2502.19896v1) |

**Inference [I]: converting these numbers to our metric.**
- SAM 3D's 0.040 on a [-1,1] object is about 2% of extent. For our 10–20 cm objects that is about 0.2–0.4 cm, which is no better than our TSDF's 0.40 cm on average.
- The gains therefore have to come from three places:
  - our objects being simple and common (cups, pitcher, pot);
  - conditioning on many posed views and metric points;
  - fitting the generated mesh to the observations.
- The leaders' 0.11–0.15 cm (about 1%) is at the level of the best multi-view-conditioned results above on synthetic data. Pure single-image generation is unlikely to get there on its own.
- Protocols differ (normalisation, squared or unsquared CD, sum or mean), so no number in this table converts exactly to CD-O.

---

## 3. Single- and multi-image-to-3D models

Licences were checked against each repo's LICENSE file via raw.githubusercontent.com unless marked otherwise.

| Model | Conditioning | Real-object geometry evidence | Thin / detail | Licence and weights | VRAM / time |
|---|---|---|---|---|---|
| **SAM 3D Objects** (Meta, Nov 2025) | Image + **object mask** + optional **pointmap** (sensor or monocular). Outputs shape and metric layout R, t, s in the camera frame. Pointmap "minimally affects shape" [M] ([paper](https://arxiv.org/html/2511.16624v2)) | Best on SA-3DAO (above). Trained for occlusion and clutter; its edge is largest under heavy occlusion [C]. Layout TTO (render-and-compare) raises ADT 2D IoU 0.514→0.649 and 3D IoU 0.484→0.526 [M] | 1.2B geometry model on a **64³** coarse grid. The paper's limitations say thin structures and fine detail are lost [M] | SAM License: royalty-free use, distribution and derivatives, with trade-control limits [M] ([LICENSE](https://raw.githubusercontent.com/facebookresearch/sam-3d-objects/main/LICENSE)). HF weights **gated**, approval needed [M] ([setup.md](https://raw.githubusercontent.com/facebookresearch/sam-3d-objects/main/doc/setup.md)) | ≥32 GB [M]. About 65 s per frame on A6000 in the V2D baseline [M]. Fast-SAM3D claims up to 2.67× speedup [C] ([arXiv](https://arxiv.org/abs/2602.05293)) |
| MV-SAM3D (community) | Several images plus a Depth-Anything-3 npz; entropy-weighted multi-view fusion | Qualitative only [M] ([repo](https://github.com/devinli123/MV-SAM3D)) | as SAM 3D | SAM License [M] | not stated |
| Scene-SAM3D (Jul 2026) | Calibrated multi-view; latent velocity fusion; 200-iteration rigid layout optimisation | Scene CD −43.8% on Replica, −30.9% on ScanNet++ [M]. Code "will be released" [M] ([arXiv](https://arxiv.org/abs/2607.16805)) | – | not released | – |
| **TRELLIS** (MSR) | Image. Multi-image is **tuning-free** and "may not give the best results" [M] ([README](https://raw.githubusercontent.com/microsoft/TRELLIS/main/README.md)) | See SA-3DAO, Cue3D and RecGen3D rows | 64³ structure | MIT [M] | ≥16 GB [M] |
| **TRELLIS.2** (Dec 2025, 4B) | Single image; also shape-conditioned texturing | No Chamfer-to-GT image-to-3D table; only CLIP/ULIP and user preference [M] ([paper](https://arxiv.org/html/2512.14692)) | O-Voxel up to 1536³; handles open and non-manifold surfaces [C] | MIT. nvdiffrast and nvdiffrec carry their own licences [M] ([README](https://raw.githubusercontent.com/microsoft/TRELLIS.2/main/README.md)) | ≥24 GB. H100: 3 s at 512³, 17 s at 1024³, 60 s at 1536³ [M] ([repo](https://github.com/microsoft/TRELLIS.2)) |
| **Pixal3D** (Tencent ARC / Tsinghua, SIGGRAPH 2026) | Pixel-aligned back-projection. Generates in the **input-camera frame**. `inference_mv.py` takes N views plus a NeRF-style `transforms.json` (camera-to-world, FOV, Z-up; first view must be the canonical front view). Alpha channel used as mask [M] ([README](https://github.com/TencentARC/Pixal3D)) | Toys4K multi-view table (above). Single view: normal-IoU 93.6 vs HY3D-2.1 83.3 [M] ([paper](https://arxiv.org/html/2605.10922)) | Default 1536 resolution. Paper limitation: "sensitivity to pixel-level noise, such as imperfect segmentation boundaries" [M] | MIT [M] ([HF card](https://huggingface.co/TencentARC/Pixal3D)) | TRELLIS.2 environment (≥24 GB); `--low_vram` mode; runtime not reported |
| ReconViaGen v0.2 / v0.5 | Unposed RGBA views → VGGT → TRELLIS (v0.5: TRELLIS.2). Six fusion strategies; `adaptive_guidance_weight` works best [C] | OmniObject3D 4-view (above) [M] | v0.5 at TRELLIS.2 resolution | Code MIT [M] ([LICENSE](https://raw.githubusercontent.com/GAP-LAB-CUHK-SZ/ReconViaGen/main/LICENSE)). VGGT weights are research-use per RecGen3D's notice [U] | 16 views: <18 GB, or <24 GB with refinement [M] ([README](https://raw.githubusercontent.com/GAP-LAB-CUHK-SZ/ReconViaGen/v0.5/README.md)) |
| Hunyuan3D 2.0 / 2mv / 2.1 | Image; 2mv takes front/left/back views [M] ([HF](https://huggingface.co/tencent/Hunyuan3D-2mv)) | SA-3DAO: 2.0 CD 0.087, 2.1 CD 0.113 [M] | octree ~380 | Tencent community licence; **not valid in the EU, UK or South Korea** [M] ([2.1 LICENSE](https://raw.githubusercontent.com/Tencent-Hunyuan/Hunyuan3D-2.1/main/LICENSE)) | 2.0 shape 6 GB; 2.1 shape 10 GB [M] |
| **Hunyuan3D-Omni** (Sep 2025, 3.3B) | Image plus **point cloud** (512–2048 points, partial or noisy, trained with random drop), voxel, bbox or skeleton [M] ([paper](https://arxiv.org/html/2509.21245v1)) | No numbers of its own [M]. RecGen3D's gains come on top of it [M] | as 2.1 | Same territory exclusion, **including outputs** ("must not use ... Output ... outside the Territory") [M] ([License.txt](https://raw.githubusercontent.com/Tencent-Hunyuan/Hunyuan3D-Omni/main/License.txt)) | 10 GB [M] ([repo](https://github.com/Tencent-Hunyuan/Hunyuan3D-Omni)). About 27 s per object on A6000 [M] (RecGen3D) |
| Hunyuan3D 2.5 / 3.0 | API | – | – | No open weights found [U] ([news](https://www.notebookcheck.net/Tencent-s-new-Hunyuan-3D-3-0-brings-realistic-AI-model-generation-to-developers-and-creators.1116964.0.html)) | – |
| RecGen3D (Sep 2026 weights) | Unposed views → canonical VGGT point cloud (4096 points) → Hunyuan3D-Omni plus LoRA | Table above [M] | – | LICENSE says research-only, vendoring VGGT and Hunyuan terms [M] ([LICENSE](https://raw.githubusercontent.com/zsh523/RecGen3D/main/LICENSE)) | 16 GB, 40 s on A6000 [M] |
| TripoSG (1.5B) / TripoSF | Image. TripoSF release is the VAE: point cloud in, 1024³ SparseFlex mesh out [M] ([README](https://raw.githubusercontent.com/VAST-AI-Research/TripoSF/main/README.md)) | SA-3DAO CD 0.084 [M] | TripoSF arbitrary topology at 1024³ [C] | MIT, both [M] | TripoSG ≥8 GB; TripoSF ≥12 GB [M] |
| Step1X-3D | Image | User preference only [M] (TRELLIS.2 Table 2) | – | **Apache-2.0** [M] ([LICENSE](https://raw.githubusercontent.com/stepfun-ai/Step1X-3D/main/LICENSE)) | 27 GB, 152 s with texture [M] |
| Direct3D-S2 | Image; sparse SDF at 1024³ | SA-3DAO CD 0.096 [M] | 1024³ | MIT [M] | 10 GB at 512³, about 24 GB at 1024³ [M] |
| SPAR3D / SF3D | Image → 512-point cloud diffusion → mesh. **The point cloud can be edited or replaced** [M] ([README](https://raw.githubusercontent.com/Stability-AI/stable-point-aware-3d/main/README.md)) | Cue3D GSO CD×1000: SF3D 61.6 [M] | low | Stability Community License [M] | 10.5 GB, 0.7 s [M] |
| Amodal3R (ICCV 2025) | Image plus visible/occluded mask (TRELLIS-based) | Synthetic occlusions on GSO and Toys4K [M] ([paper](https://arxiv.org/abs/2503.13439)) | – | **S-Lab non-commercial** [M] ([LICENSE](https://raw.githubusercontent.com/Sm0kyWu/Amodal3R/main/LICENSE.txt)) | – |
| InstantMesh | Zero123++ views → LRM | Cue3D GSO 54.5 [M] | low | Apache code [M]. Zero123++ weights CC-BY-NC [M] ([README](https://raw.githubusercontent.com/SUDO-AI-3D/zero123plus/main/README.md)) | – |
| CraftsMan3D / PartCrafter | Image (PartCrafter does parts, on TripoSG) | No real-object CD found | – | MIT, both [M] ([CraftsMan](https://raw.githubusercontent.com/wyysf-98/CraftsMan/main/README.md), [PartCrafter](https://raw.githubusercontent.com/wgsxm/PartCrafter/main/LICENSE)) | PartCrafter ≥8 GB [M] |
| **Hi3D v1.0** (formerly Sparc3D, open since **2026-10-23**) | **Coarse mesh plus reference image** → refined geometry at 512/1024/1536³. Accepts any existing mesh. Output is normalised (mean removed, radius 1); orientation is not stated to change [M] ([pipeline.md](https://raw.githubusercontent.com/hi3d-official/Hi3Dv1.0/main/docs/pipeline.md)) | Qualitative only. "Unseen surfaces are plausible completions" and "refinement may retain severe structural errors" [M] | Up to 1536³ | Custom Hi3D Open License; commercial use permitted with conditions [M] ([LICENSE](https://raw.githubusercontent.com/hi3d-official/Hi3Dv1.0/main/LICENSE)) | 1536³ validated **only on a 96 GB H20** [M] |

**Gaps.** I found no 2026 release beyond Pixal3D, Hi3D v1.0, RecGen3D and ReconViaGen v0.5 with real-object geometry numbers. SA-3DAO has a Hugging Face leaderboard, but I could not retrieve its rankings ([Meta SA-3DAO page](https://ai.meta.com/datasets/sa-3dao-sam-3d-artist-objects/)).

---

## 4. Video and novel-view generation used for 3D

**Model status:**
- **SV3D / SV4D 2.0** (Stability): SV4D 2.0 reports better LPIPS and FV4D for novel-view video [M] and is released under the Stability Community License [M] ([SV4D 2.0](https://arxiv.org/pdf/2503.16396); [announcement](https://stability.ai/news/stable-video-4d-20-new-upgrades-for-high-fidelity-novel-views-and-4d-generation-from-a-single-video)). SV3D GSO numbers (CD 0.024, IoU 0.614) come from a secondary review [U] ([review](https://liner.com/ko/review/sv3d-novel-multiview-synthesis-and-3d-generation-from-single-image-using-latent-video-diffusion)).
- **GEN3C** (NVIDIA): video generation conditioned on renders of a 3D cache [M] ([paper](https://arxiv.org/abs/2503.03751)). Code is Apache-2.0; weights are under the NVIDIA Open Model License; about 43 GB peak with offloading [M] ([README](https://raw.githubusercontent.com/nv-tlabs/GEN3C/main/README.md)). Evaluated on scene novel-view synthesis, with no object geometry metrics.
- **Other code licences** [M]: [ViewCrafter](https://raw.githubusercontent.com/Drexubery/ViewCrafter/main/LICENSE) Apache-2.0; [ReconX](https://raw.githubusercontent.com/liuff19/ReconX/main/LICENSE) MIT; [Wonder3D](https://raw.githubusercontent.com/xxlong0/Wonder3D/main/LICENSE) MIT; [MV-Adapter](https://raw.githubusercontent.com/huanngzh/MV-Adapter/main/LICENSE) Apache-2.0; [Era3D](https://raw.githubusercontent.com/pengHTYX/Era3D/main/README.md) AGPL-3.0; [pix2gestalt](https://raw.githubusercontent.com/cvlab-columbia/pix2gestalt/main/LICENSE) CC BY-NC 4.0.
- **CAT3D / CAT4D / See3D:** I found no public weights or licence file for any of them [U].
- **Difix3D+ (NVIDIA):** about 2× FID improvement on scene reconstructions [M] ([paper](https://arxiv.org/html/2503.01774v1)), under an NVIDIA licence [M] ([LICENSE](https://raw.githubusercontent.com/nv-tlabs/Difix3D/main/LICENSE.txt)). GenFusion and FlowR are also appearance-focused; I found no geometry numbers for them.

**Do these beat direct native-3D generation on real hand-held objects? The evidence:**
- **Native 3D wins on geometry** [M]: Cue3D (GSO and Toys4K) finds native 3D generators (TRELLIS, Hunyuan3D-2) beat multi-view-diffusion + LRM pipelines (InstantMesh, CRM, LGM) on CD ([Cue3D](https://arxiv.org/html/2511.22121)).
- **Views from a novel-view model only help alongside real observations** [M]: in MagicHOI's ablation, NVS alone gives 1.54 cm and RGB alone 1.37 cm, but RGB + NVS gives 0.91 cm ([MagicHOI](https://arxiv.org/html/2508.05506v1)).
- **Generated views can feed a native 3D generator** [M]: AGILE uses a closed image model (Gemini) to synthesise orthogonal views, rejects bad ones with a VLM critic, and gets the best HO3D result. That generation stage alone takes 16–24 min per object ([AGILE](https://arxiv.org/html/2602.04672)).
- **Verdict [I]:** we already have real posed views covering most of each object. Generated views add hallucination, and their consistency cannot be checked against metric depth. Use novel-view and video models only:
  - for hand removal or amodal fill in a *selected* conditioning frame (Qwen-Image-Edit is Apache-2.0 [M] ([HF card](https://huggingface.co/Qwen/Qwen-Image-Edit-2509)); GenPC and Pixal3D's scene pipeline both use it [M]);
  - as an SDS prior restricted to unseen regions.

---

## 5. Fusing generation with observations: what exists and what was measured

**(a) Condition the generator on observations**
- **Point clouds:** Hunyuan3D-Omni (partial/noisy points) [M], RecGen3D (gains above) [M], SPAR3D (editable or replaceable point cloud) [M], and CAST (occlusion-aware generation with point-cloud conditioning plus an alignment model) [C] ([CAST](https://arxiv.org/html/2502.12894v2)).
- **Posed pixels:** Pixal3D-MV [M].
- **Unposed latent fusion:** ReconViaGen [M], MV-SAM3D [C], Scene-SAM3D [M].
- **InstaScene** (ICCV 2025): "in-situ generation" conditioned on observations and partial geometry [C] ([paper](https://arxiv.org/html/2507.08416v1)).

**(b) Generate, then fit with a similarity or rigid transform**
- The NVIDIA SRT silhouette/depth fit [M] (section 1).
- SAM 3D layout TTO: kept only if mask IoU improves; 554 of 1,027 ADT instances accepted [M] ([paper](https://arxiv.org/html/2511.16624v2)).
- **Any6D** (InstantMesh mesh, metric RGB-D): per-axis size search over 0.6–1.4 plus render-and-compare. It does "not incorporate shape updating". The HO3D ablation lowers CD from 1.47 to 0.49 with alignment [M] ([Any6D](https://arxiv.org/html/2503.18673v2)).
- CARI4D scale grid search [M] (section 1).

**(c) Keep what was observed, generate only what is missing**
- GenPC keeps the input partial points, aligns the generated shape by scale sweep (0.8–1.2) plus ICP, and deletes generated points near the observations.
- Its optional SDS refinement optimises only the missing region. It improves Redwood CD from 1.98 to 1.74 (×100) [M] ([GenPC](https://arxiv.org/html/2502.19896v1)).
- Code is MIT and recommends TRELLIS.2 [M] ([repo](https://github.com/liannuaa/GenPC)).

**(d) SDS or diffusion prior plus observations**
- MagicHOI: visibility-weighted SDS on unseen regions only [M] (section 4).
- Counter-evidence: Photo3D found test-time optimisation on TRELLIS outputs *degraded* quality and took over 4 minutes, which it attributed to geometry/view mismatch [M] ([Photo3D](https://arxiv.org/pdf/2512.08535)).

**(e) Generative super-resolution of an existing mesh**
- Hi3D v1.0 can take **our TSDF mesh** as the coarse input [M] (section 3).
- Whether it thins our 12 mm walls or keeps them is untested [I]. Its docs warn that structural errors in the coarse mesh can survive.

**(f) Non-rigid or free-form fitting**
- Optimal-step non-rigid ICP ([Amberg et al. 2007](https://shapemodelling.cs.unibas.ch/gravis-literature/publications/2007/CVPR07_Amberg.pdf)) is implemented in trimesh (MIT) as `registration.nricp_amberg` [M] ([source](https://raw.githubusercontent.com/mikedh/trimesh/main/trimesh/registration.py)).
- I found **no paper measuring generate → non-rigid-fit gains on real hand-held objects**. Treat it as a hypothesis [I].

---

## 6. Similar challenges and what top teams used

- **HANDS ARCTIC track (ECCV 2024):** won with 3DGS plus mask and contact losses (CDh 38.69) [M] ([1st-place report](https://arxiv.org/pdf/2409.19215)). The 2025 winner, GHOST (DFKI), was also reconstruction-based [M] ([DFKI](https://av.dfki.de/?p=15257)).
- **BOP 2024 model-free:** the only model-free entry, GFreeDet, onboarded objects by fitting 3DGS to onboarding videos [M] ([BOP 2024 report](https://arxiv.org/html/2504.02812v2)). The 2025 award slides are linked from the [BOP site](https://bop.felk.cvut.cz/), but I could not read the winners' methods [U].
- **HO3D with 2026 methods:** the generation-then-fit pipeline (AGILE, Hunyuan3D-2) now leads reconstruction-only HOLD by about 4× in CD [M] (section 2).
- **V2D Discord and Kaggle discussions:** not public or not indexed. Nothing found.

---

## 7. Interactions with our scorer (all [I] unless cited)

- **CD-O is invariant to similarity transforms.** Our metric registers with Sim(3) after fixing scale by the area-weighted RMS-radius ratio. A generator's scale error therefore costs nothing on CD-O. Shape errors, extra inner shells and missing bottoms do cost, because they shift the RMS radius and hence the fixed scale.
- **Thick TSDF walls distort the fixed scale.** Our 12 mm walls add area on the inner shell, which biases the RMS radius. Generated cups and pitchers have closed thin walls, so this alone may give a CD-O gain.
- **A complete mesh should flip less.** Registration starts from PCA and our body frame comes from that registration. Missing undersides move the PCA axes, which is a likely cause of flips. A completed mesh should reduce flip risk, provided its own pose in *our* tracking frame is right. All generated meshes must therefore be registered into the frame of the mesh we tracked, and the trajectory kept as it is.
- **Decimation sets a floor.** Measure CD-O of the public scan decimated to ≤4096 faces against the original scan before chasing below about 0.1 cm.
- **Integrity.** Conditioning inputs (frames, masks, depth, our poses) are all available at eval time. Never use public scans as retrieval templates or conditioning for eval objects (FAQ, section 1).

---

## 8. Ranked recommendation for public-episode trials

**Shared front end for all candidates (no ground truth read):**
1. **Frame scoring.** Use FoundationPose object poses, SAM2 object masks, and our TSDF mesh projected at each pose.
   - Visibility = mask area / projected-silhouette area. Keep frames ≥0.9.
   - Sharpness = Laplacian variance. Prefer low object angular velocity, because the colour camera has a rolling shutter.
   - Coverage: greedy farthest-point selection of viewing directions on the object-frame sphere, 4–8 frames. Force-include the frames that show the underside while the object is lifted or rotated.
2. **Images.** Use the undistorted 2028×1520 colour frames.
   - SAM 3D: full image plus mask.
   - Pixal3D: a recentred virtual pinhole crop (rotation-only homography H = K′RK⁻¹, principal point at the centre, object about 80% of the frame). Its loader assumes FOV-only intrinsics and never crops [M] ([README](https://github.com/TencentARC/Pixal3D)).
3. **Masks.** Object-only masks (hands removed). Avoid frames where a hand cuts the outer silhouette. Inpainting with Qwen-Image-Edit is a fallback only.
4. **Observations for fitting and gating.**
   - The fused **outer-surface** depth points in the object frame: per-frame FoundationStereo points inside the object mask, minus hand pixels, minus points behind the TSDF front surface.
   - Silhouettes from about 25 frames not used for conditioning.
5. **Fit.**
   - Sim(3): multi-start ICP to the depth points (24 rotation starts), with silhouette IoU used to break symmetry ties.
   - Optional non-rigid step: `nricp_amberg` toward depth points within 1 cm (high stiffness, observed regions only).
   - Decimate to ≤4096 faces.
6. **Gate (works on eval data too).**
   - Median one-sided distance from observed points to the mesh must be ≤ the TSDF mesh's value plus 1 mm.
   - Mean held-out silhouette IoU must be ≥ the TSDF mesh's value.
   - Otherwise fall back to TSDF for that object.

### A. Pixal3D multi-view with our poses (try first)
- **Why:**
  - Output is in our object frame, so no canonical-frame guessing and no flip from the generator.
  - It uses all posed views; best multi-view numbers found (Toys4K) [M].
  - 1536³ output for fins and slots [C].
  - MIT licence on a TRELLIS.2 base.
- **Inputs:**
  - 4–6 recentred RGBA crops plus `transforms.json`, with camera-to-world from inverse object poses and a per-frame `camera_angle_x`.
  - Object frame rescaled to the unit cube using the TSDF bounding radius.
  - World rotated so view 0 is at (0,−d,0) looking at the origin with Z up (README requirement [M]).
- **Expected CD-O [I]:** 0.13–0.30 cm on cups, pot, pitcher, dust pan and boards; 0.25–0.5 cm on dish rack and brush.
  - The low end assumes Toys4K-like gains carry over to real crops. The high end allows for hand-cut silhouettes and rolling-shutter misalignment, since the paper itself lists sensitivity to mask noise [M].
- **Compute [I]:** A100-80GB or H100; runtime not published (TRELLIS.2 is 17–60 s per pass at 1024–1536 on H100 [M]). Budget about 2–5 min per object including the fit, plus 1–2 h of environment setup (flash-attn, natten, FlexGEMM).
- **Licence risk:** low. MIT; nvdiffrast is under its own NVIDIA licence [M], and we already depend on NVIDIA-licensed FoundationPose/Stereo.
- **Falsification:** on ≥10 public objects, with the same fit and gate as the TSDF baseline, the hypothesis fails if:
  - median CD-O is not at least 0.08 cm below the TSDF's 0.40 cm; or
  - adding views 5–6 does not reduce one-sided observed→mesh distance (that would mean occluded views hurt); or
  - the frame of any object ends up rotated by more than 20° from our tracked frame after Sim(3) to the scan.

### B. SAM 3D Objects with our metric pointmap, best-of-K plus observation fit
- **Why:**
  - Best measured real-image single-view accuracy (SA-3DAO) and occlusion-trained [M].
  - The organisers' module already wraps it: `v2d_sam3d`, Apache-2.0 [M].
  - Our pointmap gives a metric layout start [M].
- **Inputs:**
  - K = 6–8 frames (as in the front end) with full frame plus visible mask.
  - Pointmap from FoundationStereo depth reprojected into the colour camera (this needs the stereo-to-colour extrinsic). The paper states sensors may supply the pointmap [M]. Whether the released API takes it directly is unverified [U]; NVIDIA ships `inference_pipeline_modified.py` [M] ([lib](https://github.com/nvidia-isaac/video_to_data/tree/main/reconstruction/modules/v2d_sam3d/lib)).
  - Fixed seeds, 2 seeds per frame.
  - Pick the candidate that wins the gate. Do not average meshes.
- **Expected CD-O [I]:** 0.18–0.35 cm on closed simple objects. The 64³ limit should cost on the dish-rack fins, board slots and spoon [M limitation], so expect 0.3–0.6 cm there; keep TSDF or A for those.
- **Compute:** ≥32 GB (A100-40/80, L40S, A6000) [M]. About 1 min per frame [M], so 6–8 frames × 2 seeds ≈ 15 min plus a few minutes of fit per object [I].
- **Licence risk:** low, but the gated HF access must be **requested today**. Approval timing is unknown [M gating].
- **Falsification:** the hypothesis fails if best-of-K SAM 3D after fitting does not beat TSDF CD-O on ≥70% of the closed public objects, or if the gate cannot pick the best candidate. Test the gate by checking that the rank correlation between gate score and CD-O is above 0.5 on public episodes.

### C. Point-conditioned completion: Hunyuan3D-Omni (or GenPC-style keep-observed + generate-missing)
- **Why:** it directly uses our strongest signal, metric outer-surface points, and the RecGen3D measurement supports point conditioning [M]. It is cheap: 10 GB and about 30 s [M].
- **Inputs:**
  - 2048 farthest-point-sampled outer-surface points plus the best single crop.
  - Points normalised to the generator's [-1,1] box and rotated into that crop's camera-aligned canonical frame. This convention is my assumption [I]; test both aligned and object-frame orientations.
  - GenPC variant: keep observed points, use generated points only where the visibility map has no observations, then mesh.
- **Expected CD-O [I]:** 0.18–0.35 cm. Surfaces stay close to our depth, but the model may copy depth noise or thick walls if inner-wall points leak into the conditioning set.
- **Licence risk:** **high if the owner or team operates in the EU, UK or South Korea.** Hunyuan licences exclude these regions, including use of outputs [M]. GenPC itself is MIT [M].
- **Falsification:** the hypothesis fails if point-conditioned output does not cut one-sided observed→mesh distance by ≥30% compared with image-only Hunyuan3D-2.1 on the same crop (which would mean the conditioning is ignored), or if public CD-O is not below TSDF.

**Optional quick probe: Hi3D v1.0 refining our TSDF mesh.**
- Released 3 days ago; validated only on a 96 GB H20 [M]; qualitative evidence only.
- Run one cup and one dish rack at 1024³. Keep it only if wall thickness measured on the output is well below 12 mm *and* CD-O drops.

**Rough budget [I]:** setting up A and B and running them on about 14 public objects takes about 8–12 GPU-hours on one 80 GB card. Get the price from the Vast API before renting. Per CLAUDE.md, the plan and cost need the owner's go-ahead.

---

## 9. Main uncertainties

- **None of the cited CD numbers use our CD-O protocol.** Normalisation and squared versus unsquared distance differ by paper, so every expected range in section 8 is an estimate.
- **Pixal3D's multi-view inference** is new (Sep 2026). Its robustness to real masks, hand occlusion and rolling shutter is untested; the paper evaluates only Toys4K renders.
- **Two items are unverified** [U]: the Track 3 baseline description (from a competitor's repo), and VGGT's weight licence (from RecGen3D's LICENSE notice).
