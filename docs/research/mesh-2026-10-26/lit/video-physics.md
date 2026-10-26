# Accurate object meshes from egocentric RGB-D video, with physics and interaction priors: literature and open-source review

Date: 2026-10-26. Web-only review; no repository files were read or changed.
Tags: **[M]** = a number measured in the cited paper under that paper's own protocol. **[I]** = my inference or
back-of-envelope estimate. **[G]** = a guess that needs an experiment before anyone relies on it.
Our numbers (CD-O 0.40 cm; leaders 0.11–0.15 cm) come from the task brief, not from this review.

## 0. Bottom line

1. **Hand-object methods that use only RGB will not get us to about 1 mm.** The best template-free video methods on
   HO3D report object Chamfer distances around 0.9–1.3 cm on short clips (MagicHOI, HOLD), and 0.4 cm² on full
   sequences after Sim(3) ICP (HOLD). Single-image methods are worse still. RGB-D trackers that reconstruct as they go
   (BundleSDF, 6DOPE-GS) report 0.15–0.58 cm, but only over faces that were visible, in the ground-truth frame. That is
   the same range as our 0.40 cm. **[M]**, sources in §1.
2. **The gap to the leaders is most likely a fusion problem**: walls blurred by occupancy, poses smeared, and missing
   bottoms. It is not a shortage of priors. **[I]** The literature has cheap, measured fixes for each:
   - Weighting that drops off behind the surface, as in Voxblox and Bylow et al.
   - A directional TSDF (Splietker & Behnke). It reduced thin-structure RMSE by 2–3× against a standard hashed TSDF.
     **[M]**
   - Jointly refining poses and shape. In Azinović et al. the F-score rose from 0.868 to 0.924 and rotation error fell
     from 0.571° to 0.144°. **[M]**
   - Envelope-constrained screened Poisson (Kazhdan et al. 2020) to fill regions with no data.
3. **Physics priors (PhysComp, Atlas3D, DSO, PhysPart) mostly raise *stability* rates, not geometric accuracy.**
   Measured accuracy gains appear only where contact implies a hidden surface:
   - Vysics: Chamfer distance 2.98 → 1.45 cm against BundleSDF on occluded objects. **[M]**
   - Co-Section: completeness 42–71% better, but accuracy mixed. **[M]**
   - Contact-guided generation: Chamfer distance 14–19% lower. **[M]**
   - PhyRecon: object Chamfer distance 4.08 → 3.28 cm at scene scale. **[M]**
   For us that means table-contact and hand-collision constraints, not stability simulation.
4. **Fusing the same object across episodes is well established and cheap.** Examples: multi-session object
   modelling (Prankl et al. 2015), object libraries (Fusion++), and certifiable registration (TEASER++, MIT
   licence). The main risk is choosing the wrong symmetric or PCA alignment. PCA has 24 possible alignments
   (Li et al. ICCV 2021). §4.

## 1. Hand-held and egocentric object reconstruction from video

| Method | Input | Benchmark result | Runtime | Code / licence |
|---|---|---|---|---|
| BundleSDF (CVPR'23) [arXiv](https://arxiv.org/abs/2303.14158) | RGB-D, first-frame mask | HO3D Chamfer distance 0.57 cm; next best was BundleTrack at 52.05 cm **[M]** ([CVPR](https://openaccess.thecvf.com/content/CVPR2023/papers/Wen_BundleSDF_Neural_6-DoF_Tracking_and_3D_Reconstruction_of_Unknown_Objects_CVPR_2023_paper.pdf)) | Tracking about 10 Hz; neural field training about 6.7 s per round on an RTX 3090 **[M]** ([ar5iv](https://ar5iv.labs.arxiv.org/html/2303.14158)) | [NVlabs/BundleSDF](https://github.com/NVlabs/BundleSDF), NVIDIA licence, research and evaluation only ([LICENSE](https://raw.githubusercontent.com/NVlabs/BundleSDF/master/LICENSE.txt)) |
| 6DOPE-GS (ICCV'25) [arXiv](https://arxiv.org/html/2412.01543v2) | RGB-D, incremental 2DGS plus joint pose refinement | YCBInEOAT Chamfer distance 0.15 cm (BundleSDF 0.53). HO3D 0.41 cm (BundleSDF 0.58) **[M]** | About 0.22–0.24 s per frame, about 4 Hz, on an RTX 4090 **[M]** | No code link in the paper |
| HOLD (CVPR'24) [arXiv](https://arxiv.org/html/2311.18448) | Monocular RGB plus MANO hand | HO3D Chamfer distance 0.4 cm² and F10 96.5%. iHOI 3.8 cm², DiffHOI 4.3 cm². Evaluated after ICP with scale **[M]** | About 10 h per sequence for the first stage on an A100 **[M]** | [zc-alexfan/hold](https://github.com/zc-alexfan/hold), MIT |
| MagicHOI (ICCV'25) [arXiv](https://arxiv.org/html/2508.05506v1) | RGB 30-frame clips, Zero-1-to-3 prior via SDS | HO3D-v3 Chamfer distance 0.87 cm. HOLD 1.31, EasyHOI 1.86, DiffHOI 2.30, iHOI 2.37 cm **[M]** | Not reported | Project page only |
| G-HOP (CVPR'24) [arXiv](https://arxiv.org/html/2404.12383v1) | RGB clip plus hand-object diffusion prior | HOI4D Chamfer distance 0.4 (units not stated) and F@5mm 0.76. DiffHOI 0.8 / 0.62 **[M]** | About 1 h per clip **[M]** | Not stated |
| DiffHOI (ICCV'23) [arXiv](https://arxiv.org/abs/2309.05663v1) | RGB clip plus category-conditioned diffusion prior | See the rows above | Slower than G-HOP **[M]** ([G-HOP](https://arxiv.org/html/2404.12383v1)) | [project](https://judyye.github.io/diffhoi-www) |
| iHOI (CVPR'22) [arXiv](https://arxiv.org/abs/2204.07153v1) | Single RGB image | HO3D Chamfer distance 15.3 cm² as reported in HORT's table **[M]** | Feed-forward | [JudyYe/ihoi](https://github.com/JudyYe/ihoi) |
| HORT (ICCV'25) [arXiv](https://arxiv.org/html/2503.21313v1) | Single RGB image, point cloud output | HO3D Chamfer distance 2.6 cm² and FS@5mm 0.45. DexYCB 1.1 cm² **[M]** | 16.9 fps on an A100; 4.8 fps when meshing **[M]** | [project](https://zerchen.github.io/projects/hort.html) |
| MOHO (CVPR'24) [CVF](https://openaccess.thecvf.com/content/CVPR2024/html/Zhang_MOHO_Learning_Single-view_Hand-held_Object_Reconstruction_with_Multi-view_Occlusion-Aware_Supervision_CVPR_2024_paper.html) | Single RGB image, trained on 2D supervision only | Chamfer distance 40.5% lower than iHOI on HO3D **[M]** | Feed-forward | — |
| HOISDF (CVPR'24) [arXiv](https://arxiv.org/abs/2402.17062v1) | Single RGB image | A hand/object *pose* estimator, not a shape method | — | [amathislab/HOISDF](https://github.com/amathislab/HOISDF) |
| In-hand RGB video (arXiv'23) [arXiv](https://arxiv.org/html/2312.16425) | RGB video, NeuS plus amodal masks plus contact | HO3D Chamfer distance 1.094 → 0.448 with amodal masks → 0.333 with contact → 0.282 (units not stated) **[M]** | — | — |
| GHOST (2026) [arXiv](https://arxiv.org/abs/2603.18912) / GraG (2026) [arXiv](https://arxiv.org/abs/2604.12929) | RGB video, 2DGS or a SAM3D-based prior | Claim state-of-the-art and a 4.4–38.9× speed-up. Numbers not checked **[M, claim only]** | Faster | [GHOST code](https://github.com/ATAboukhadra/GHOST) |
| EgoGrasp (2026) [arXiv](https://arxiv.org/abs/2601.01050v2) | Egocentric RGB, world-space hand-object interaction | Evaluated on H2O and HOI4D. Targets pose, not mesh accuracy **[M]** | — | — |
| HOSt3R (ICCVW'25) [arXiv](https://arxiv.org/html/2508.16465v2) | RGB, DUSt3R-style pointmaps, no keypoints | State of the art on SHOWMe **[M, claim]** | — | — |
| FoundationPose model-free (CVPR'24) [arXiv](https://arxiv.org/html/2312.08344v2) | About 16 reference RGB-D views and a neural SDF | No shape-accuracy numbers. The SDF exists to support rendering for pose estimation **[M]** | Training takes seconds | NVIDIA licence |
| Any6D (CVPR'25) [arXiv](https://arxiv.org/abs/2503.18673) | One RGB-D anchor image | Pose and size only, on HO3D and YCBInEOAT **[M]** | — | — |
| GraspSplats (CoRL) [arXiv](https://arxiv.org/pdf/2409.02084) | Posed RGB-D, feature Gaussians | Robot grasping; no surface metrics. Builds a scene in under 60 s **[M]** | — | — |

**Protocol caveats that matter when comparing these numbers with our CD-O:**
- BundleSDF computes Chamfer distance in the ground-truth frame of the first image. It samples at 5 mm and removes
  ground-truth faces that were never visible. **[M]** ([ar5iv App. C](https://ar5iv.labs.arxiv.org/html/2303.14158))
  Its numbers therefore leave out unseen undersides entirely. Our metric penalises them.
- HOLD reports squared Chamfer distance in cm², after ICP with scale. **[M]** ([HOLD](https://arxiv.org/html/2311.18448))
- BundleSDF's neural object field truncates at 1 cm and starts from an octree with 2 cm voxels. **[M]**
  ([ar5iv](https://ar5iv.labs.arxiv.org/html/2303.14158)) That is coarse compared with the 1–2 mm walls we need, so
  BundleSDF is not obviously sharper than a well-tuned TSDF. **[I]**
- Taken together, RGB-D methods reach 0.15–0.6 cm on visible surfaces. Without accurate depth, priors leave errors at
  1 cm or more. **[I]** Hand priors help us mainly with masks, occlusion reasoning and collision carving, not with
  shape.

## 2. Surface reconstruction from posed RGB(-D)

### 2.1 TSDF best practice for thin walls
- **Why walls get thick.** The truncation band from one side spreads behind the surface and corrupts the field seen
  from the other side. The surface shrinks, overlaps or grows gaps. "Reducing truncation helps only up to a point."
  **[M, qualitative]** ([Sensors 2020 thin-surface paper](https://api.crossref.org/works/10.3390%2FS20020534);
  [DTSDF](https://arxiv.org/pdf/1908.05146)) A TSDF cannot represent anything thinner than one voxel.
  ([DTSDF](https://ar5iv.labs.arxiv.org/html/1908.05146))
- **Directional TSDF** ([Splietker & Behnke IROS'19](https://ar5iv.labs.arxiv.org/html/1908.05146)):
  - Keeps six volumes, one per ±axis direction.
  - Each measurement is fused into every direction whose weight ⟨n, v_D⟩ exceeds sin(π/8) ≈ 0.38, so into at most
    three directions.
  - Fusion is by ray casting along the normal. Truncation was 4 voxels.
  - At 10 mm voxels, RMSE fell from 3.67 to 1.74 mm (Armadillo), 3.82 to 1.23 mm (Bunny) and 7.11 to 2.87 mm (Asian
    Dragon), against the MeshHashing TSDF. **[M]**
  - A follow-up adds depth rendering, so the DTSDF can replace a standard TSDF in trackers.
    ([ECMR'21](https://arxiv.org/pdf/2108.08115))
- **Behind-surface drop-off** (Voxblox code, BSD-3) ([tsdf_integrator.cc](https://raw.githubusercontent.com/ethz-asl/voxblox/master/voxblox/src/integrator/tsdf_integrator.cc)):
  - Voxels in front of the surface and up to one voxel behind it get full weight.
  - From there the weight falls linearly to 0 at sdf = −truncation.
  - The per-ray weight is 1/z². The defaults also enable voxel carving ([header](https://raw.githubusercontent.com/ethz-asl/voxblox/master/voxblox/include/voxblox/integrator/tsdf_integrator.h)).
  - The paper reports that 1/z² weighting reduces RMSE slightly in every setting (for example KITTI 0.6701 → 0.5906 m
    at 0.5 m voxels). The effect is "bigger for thin surfaces seen from multiple viewpoints." **[M]**
    ([ar5iv](https://ar5iv.labs.arxiv.org/html/1611.03631))
  - Bylow et al. studied distance and weighting functions in the same framework.
    ([RSS'13](https://cvai.in.tum.de/_media/spezial/bib/bylow_etal_rss2013.pdf))
- **Weighted signed distance and least-squares isosurfaces** come from Curless & Levoy. Their method also fills holes
  at the boundary between space seen as empty and space never seen.
  ([SIGGRAPH'96](https://graphics.stanford.edu/papers/volrange/))
- **Open3D warns** that smaller voxels make the result "susceptible to depth noise". Its example uses 7.8 mm voxels and
  4 cm truncation, which is far too coarse for us.
  ([Open3D](https://www.open3d.org/docs/release/tutorial/pipelines/rgbd_integration.html))
- **Depth edges.** Window-based stereo "fattens" foreground objects at depth discontinuities.
  ([MIT multi-frame stereo](https://people.csail.mit.edu/tfxue/project/multiview-stereo)) So depth pixels near mask
  boundaries are biased toward the foreground. **[I]** Erode masks before fusing.
- **Multi-view consistency filtering** is the MVS-style alternative to plain averaging. The COLMAP fusion defaults are a
  2 px reprojection error, 1% depth error, 10° normal error and at least 5 pixels; these come from an unofficial wiki.
  ([colmap-parameters wiki](https://github.com/mwtarnowski/colmap-parameters/wiki/StereoFusion))
- **Noise model for our rig [I].** Stereo depth error is σ_z = z²·σ_d/(f·B), the Intel RealSense tuning formula.
  ([Intel BKM](https://forums.intel.com/cipcp26785/attachments/cipcp26785/feeditem_no_topic/6363/1/BKM-For-Tuning-D435-and-D415-Cameras-Webinar_Rev3.pdf))
  Here B = 75 mm. Assumptions **[G]**: f ≈ 350 px at half resolution (replace with our calibration), σ_d ≈ 0.15 px,
  z = 0.5 m.
  - Result: σ_z ≈ 1.4 mm at half resolution and about 0.7 mm at full resolution, if σ_d in pixels stays the same.
  - FoundationStereo supports full-resolution output with `--hiera 1`. It also has a commercial-use TAO model.
    ([repo](https://github.com/NVlabs/FoundationStereo))
  - Implications: voxel size v ≈ 1.5 mm; truncation μ ≈ 3v ≈ 3σ_z ≈ 4.5 mm.
  - μ is larger than our 2–4 mm walls, so we need either the drop-off (ε = v) or a directional or side-aware TSDF.

### 2.2 Poisson / screened Poisson
- **PoissonRecon** is MIT-licensed.
  ([mkazhdan/PoissonRecon](https://github.com/mkazhdan/PoissonRecon)) Relevant options:
  - `--envelope` takes a watertight PLY.
  - `--bType` 1 = free, 2 = Dirichlet, 3 = Neumann (default).
  - `--pointWeight` (default 2 × degree), `--samplesPerNode` (1.5), `--density` for trimming.
- **Envelope constraints** ([Kazhdan, Chuang, Rusinkiewicz, Hoppe, SGP'20](https://hhoppe.com/proj/envelope/)):
  - Dirichlet conditions force the implicit function to zero (the "outside" value) beyond the envelope. The envelope
    can be a visual hull or a depth hull taken from RGB-D.
  - This gives "substantially improved surface reconstructions in regions of missing data". That claim is
    qualitative on the project page **[M, qualitative]**.
  - It matches our problem with unseen undersides: the envelope is the visual hull, intersected with the free space
    seen by stereo, intersected with the half-space above the table. **[I]**
- **Gaussian surfels** finish with screened Poisson at tree depth 10 on fused rendered depth. They first cut away
  voxels on a 512³ grid whose opacity is below 1. **[M]** ([arXiv](https://arxiv.org/html/2404.17774v2))

### 2.3 Neural SDF
- **Neural RGB-D Surface Reconstruction** (Azinović et al.) is the closest controlled comparison with TSDF fusion on
  noisy depth. Over 10 synthetic scenes it reports **[M]**
  ([ar5iv](https://ar5iv.labs.arxiv.org/html/2104.04532)):
  - Chamfer-ℓ1: 0.062 for BundleFusion TSDF, 0.049 for the neural SDF without pose refinement, and 0.044 with pose
    refinement.
  - F-score: 0.805 → 0.868 → 0.924.
  - Pose refinement contributes a large share of the gain.
- **DTU Chamfer distances** (mm, 49–64 calibrated views, masks) **[M]**:
  - NeuS 0.84 and Neuralangelo 0.61, with more than 128 h of training
    ([PGSR table](https://arxiv.org/html/2406.06521)).
  - NeuS2 0.70 in 3.3 min ([surfels table](https://arxiv.org/html/2404.17774v2);
    [repo](https://github.com/19reborn/NeuS2)).
- **MonoSDF** ([arXiv](https://arxiv.org/abs/2206.00665)) and **BakedSDF** ([arXiv](https://arxiv.org/abs/2302.14859))
  target room- and scene-scale reconstruction with monocular priors or real-time rendering. They are not aimed at
  millimetre object walls. **[I]**

### 2.4 Gaussian surfaces
- **DTU mean Chamfer distance (mm) and training time [M]:**
  - PGSR 0.52 (0.5 h). ([PGSR](https://arxiv.org/html/2406.06521))
  - MILo 0.68 (25 min), RaDe-GS 0.68 (8 min), GOF 0.74, 2DGS 0.80 (9 min), SuGaR 1.33, 3DGS 1.96.
    ([MILo](https://arxiv.org/html/2506.24096v2))
  - Gaussian surfels 0.88. ([surfels](https://arxiv.org/html/2404.17774v2))
- **Mesh size:** MILo produces meshes with about 10× fewer vertices **[M]**. Its depth supervision uses only built-in
  Depth-Anything ordering, with no input for external depth ([repo](https://github.com/Anttwo/MILo)).
- **DN-Splatter** adds depth and normal priors for indoor scenes. In its MuSHRoom/ScanNet++ mesh table, classical
  Poisson scores Chamfer-ℓ1 .0306 and MonoSDF with sensor depth .0250 **[M]**. Only the snippet was read, so check
  which table this row comes from. ([arXiv](https://arxiv.org/abs/2403.17822v1))
- **Licences:**
  - 2DGS, GOF, MILo and similar code inherits the Inria/MPII Gaussian-Splatting licence (non-commercial)
    ([2DGS LICENSE](https://raw.githubusercontent.com/hbb1/2d-gaussian-splatting/main/LICENSE.md)).
  - gsplat is Apache-2.0. It provides `rasterization_2dgs` with normals, distortion and median depth.
    ([gsplat](https://github.com/nerfstudio-project/gsplat), [docs](https://docs.gsplat.studio/main/apis/rasterization.html))
- **Caveat [I]:** DTU numbers use calibrated, static captures. Our accuracy is limited by object-pose error and by
  rolling shutter on the colour camera, not by the renderer. Gaussian methods pay off only after poses are refined.

### 2.5 Refining the mesh with differentiable rendering
- **Neural deferred shading** ([ar5iv](https://ar5iv.labs.arxiv.org/html/2212.04386)):
  - Losses: L1 shading, L1 silhouette (weight 2), Laplacian (40), normal consistency (0.1).
  - Initialised from a 32³ visual hull and remeshed three times.
  - DTU 1.95 mm, against COLMAP 0.64 and IDR 0.92 **[M]**.
  - So a mesh optimised from RGB and masks alone is fast but *not* more accurate. Its value for us is as a final
    refinement on a good initial mesh, with depth terms added. **[I]**
- **Tools:**
  - Large Steps uses Laplacian reparameterisation for stable mesh optimisation (BSD-3).
    ([large-steps-pytorch](https://github.com/rgl-epfl/large-steps-pytorch))
  - Continuous Remeshing (MIT). ([Profactor](https://github.com/Profactor/continuous-remeshing))
  - PyTorch3D (BSD). ([repo](https://github.com/facebookresearch/pytorch3d))
  - nvdiffrast uses the NVIDIA Source Code License ([repo](https://github.com/NVlabs/nvdiffrast)).

### 2.6 Visual hull and space carving
- The visual hull is the largest volume consistent with all silhouettes, so it cannot recover concavities.
  ([Wikipedia](https://en.wikipedia.org/wiki/Visual_hull); [Laurentini, polito](https://cgvg.polito.it/vhull.html))
  Cup interiors therefore need depth. Silhouettes, by contrast, hold the fins and the spoon well. **[I]**
- **Mask quality:**
  - SAM-family masks lose thin structures. On ThinObject5K, SAM ViT-H scores 0.591 mBIoU and HQ-SAM 0.759 **[M]**.
    ([Talk2SAM](https://arxiv.org/pdf/2506.05396); [HQ-SAM](https://arxiv.org/pdf/2306.01567))
  - Carving should therefore use dilated masks, or vote over views instead of requiring every view to agree. **[I]**
- **Rolling shutter:** modelling rolling shutter and motion blur in the renderer improves reconstruction from handheld
  video. ([Seiskari et al. ECCV'24](https://arxiv.org/abs/2403.13327v3))
  - Example **[G]**: an object moving at 0.3 m/s during a 20–30 ms readout shifts 6–9 mm across the frame. Colour-camera
    silhouettes need a tolerance band, or should be projected into the stereo camera, which is probably global
    shutter (check the rig).

### 2.7 Joint pose-and-shape refinement
- **BundleSDF** alternates a pose graph with the neural field. It drops point-to-plane correspondences beyond 1 cm or
  20° and uses up to 10 memory frames plus the current one **[M]**.
  ([ar5iv](https://ar5iv.labs.arxiv.org/html/2303.14158))
- **6DOPE-GS** refines all keyframe poses through the 2DGS renderer using RGB, depth and normals **[M]**.
  ([arXiv](https://arxiv.org/html/2412.01543v2))
- **Azinović et al.:** with pose refinement, rotation error fell from 0.571° to 0.144° and F-score rose by 5.6
  points **[M]**. ([ar5iv](https://ar5iv.labs.arxiv.org/html/2104.04532))
- **Scale of the effect [I]:** a 0.5° rotation error at 6 cm radius smears the surface by about 0.5 mm. Translation
  jitter of 1–2 mm smears it by the same amount. Both widen walls directly, so pose refinement and thin-wall fusion
  compound.

## 3. Physics and interaction priors in mesh reconstruction

| Work | Physics used | Measured effect on accuracy |
|---|---|---|
| PhysComp (NeurIPS'24) [arXiv](https://arxiv.org/html/2405.20510v1) | Rest-shape optimisation with static equilibrium as a hard constraint, from a single image | Stability goes from 7–33% to 72–92% across 5 generators. Image loss improves slightly. **No Chamfer distance reported [M]** |
| Atlas3D (NeurIPS'24) [arXiv](https://arxiv.org/abs/2405.18515) | Differentiable-simulation loss for text-to-3D that stands up by itself | Stable in simulation and when printed. Textures change slightly. No geometric accuracy reported **[M]** |
| DSO (ICCV'25) [arXiv](https://arxiv.org/abs/2503.22677) | Simulator feedback used for DPO/DRO fine-tuning of TRELLIS | Stability goes up and it is faster than test-time optimisation. No accuracy against scans **[M]** |
| PhysPart (ICRA'25) [arXiv](https://arxiv.org/abs/2408.13724v2) | Diffusion part completion with stability and mobility losses | Motion-success metric only **[M]** |
| PhyRecon (NeurIPS'24) [arXiv](https://arxiv.org/html/2404.16666v1) | Differentiable particle simulation with SDF-to-points (SP-MC). Contact-point displacement loss | ScanNet++ object Chamfer distance 4.08 → 3.28 cm. Stability 25% → 78%. The physics loss alone gives 4.13 → 3.97 cm **[M]** |
| Co-Section (CVPR'20) [ar5iv](https://ar5iv.labs.arxiv.org/html/2004.04630) | Hull term (observed free space) plus a non-penetration term between object SDFs | Completeness 42–71% better than TSDF. Accuracy *worse* on 2 of 3 objects because unseen regions are filled in **[M]** |
| Vysics (RSS'25) [arXiv](https://arxiv.org/html/2504.18719v1) | Contact dynamics infer hidden geometry. Losses for support points and a hyperplane lower bound (SDF ≥ distance to support plane) are added to BundleSDF | Mean Chamfer distance 1.45 cm, against BundleSDF 2.98 and the best completion baseline 2.47 **[M]** |
| Contact-guided generation (2025) [arXiv](https://arxiv.org/html/2512.05079v1) | Contact points steer Amodal3R/TRELLIS | GSO Chamfer distance −19%. Real data 1.61 → 1.39 cm **[M]** |
| In-hand RGB video [arXiv](https://arxiv.org/html/2312.16425) | Hand attraction and penetration losses | Chamfer distance 0.448 → 0.333. Penetration loss alone does worse than attraction **[M]** |
| NeuralFeels (Sci. Robotics'24) [arXiv](https://arxiv.org/abs/2312.13469v1) | Touch as surface samples in a neural SDF | F-score 81%. Pose drift 4.7 mm. Up to 94% better tracking under occlusion than vision alone **[M]** |
| Schiebener et al. 2016 [PDF](https://h2t.iar.kit.edu/pdf/Schiebener2016.pdf) | Symmetry plus support plane to fill in the bottom | Heuristic completion **[M, qualitative]** |
| trimesh `compute_stable_poses` [docs](https://trimesh.org/trimesh.poses.html) | Stable rest poses and their probabilities | A tool for checking whether a mesh rests correctly on the table **[I]** |

**Takeaways [I]:**
- Stability and equilibrium priors keep shapes from tipping over, but no paper reports a gain in accuracy against a
  scan. Low priority.
- The constraints with measured geometric gains are:
  - Free space (hull or envelope).
  - Non-penetration (table, hand, other objects).
  - Support or contact points treated as samples on the surface.
- Co-Section and PhyRecon show that filling unseen regions can *cost* accuracy if it is unconstrained. Fill only inside
  the envelope, and prefer planar caps where the object meets the table.

## 4. Fusing the same object across sequences, and canonicalisation
- **Prankl et al. (IROS'15)** merge partial models captured in separate sessions, with the object in different poses,
  by multi-session registration. The aim is to reveal occluded sides.
  ([PDF](https://www.acin.tuwien.ac.at/fileadmin/acin/v4r/v4r/IROS15_IROS2015_ObjectModellingfinal.pdf);
  [arXiv long version](https://arxiv.org/pdf/1505.05643))
- **Fusion++** keeps a persistent library of TSDFs, one per object, in a 6-DoF pose graph. Objects are reused when
  revisited. ([Imperial](https://spiral.imperial.ac.uk/entities/publication/00c14136-ff56-4b11-8f93-97e59b267cdc))
- **Panoptic Multi-TSDFs** keep one submap per object, with change detection over time.
  ([arXiv](https://arxiv.org/abs/2109.10165v2))
- **SDF-2-SDF** registers SDFs to each other directly.
  ([ECCV'16](https://www.campar.in.tum.de/pub/slavcheva2016eccv/slavcheva2016eccv.pdf))
- **Global registration:**
  - TEASER++ stays accurate with more than 99% outlier correspondences, runs in milliseconds, and is MIT-licensed.
    ([arXiv](https://arxiv.org/abs/2001.07715); [repo](https://github.com/MIT-SPARK/TEASER-plusplus))
  - Open3D FPFH+RANSAC recipe, as multiples of the voxel size v: normal radius 2v, FPFH radius 5v, RANSAC threshold
    1.5v, ICP threshold 0.4v.
    ([Open3D](https://www.open3d.org/docs/release/tutorial/pipelines/global_registration.html))
- **Canonicalising with PCA** is ambiguous in 4 sign × 6 axis-order = 24 ways. A pose selector is needed.
  ([Li et al. ICCV'21 suppl.](https://openaccess.thecvf.com/content/ICCV2021/supplemental/Li_A_Closer_Look_ICCV_2021_supplemental.pdf))
  The scorer starts from PCA, so on near-symmetric objects (cups, pot, boards) an episode-specific mesh that differs
  only slightly can flip the registration. Fusing across episodes makes the meshes *identical* up to a rigid
  transform, so episodes stay consistent. **[I]**
- **Generative completion:** SAM 3D Objects reconstructs shape from a single image, including unseen parts. Its
  evidence is human preference wins, not Chamfer distance against scans.
  ([arXiv](https://arxiv.org/pdf/2511.16624); [HF](https://huggingface.co/facebook/sam-3d-objects/blob/refs%2Fpr%2F6/README.md))
  Use it at most as a fallback for areas that were never seen. **[I]**

## 5. Error budget for our meshes [I unless marked]
- **Cup wall.** Example cup: outer radius 4 cm, height 9 cm, wall 3 mm.
  - Inner surfaces are about 45% of the total area (inside wall about 200 cm² of about 520 cm²).
  - A 12 mm reconstructed wall puts the inner surface about 9 mm off.
  - That alone contributes roughly 0.4 cm to symmetric Chamfer distance. So **wall thickness can explain our whole
    0.40 cm on hollow objects** (cups, pot, pitcher, dust pan).
- **Thick flat objects.** For boards about 1.5 cm thick with no underside, the underside's ground-truth points lie
  about 1–1.5 cm from our mesh, over roughly 45% of the area.
- **Decimation is cheap.**
  - 4096 faces on about 500 cm² gives edges of about 5.5 mm.
  - The chord error on a 4 cm radius is l²/8r ≈ 0.1 mm. Not a bottleneck.
  - Quadric decimation should keep that budget off the flat regions.
- **Scale normalisation interacts with shape errors.** The scorer normalises by area-weighted RMS radius. Missing or
  extra (inner or thick) surfaces shift that radius and so bias the scale. Completeness therefore matters twice.
- **The noise floor allows the leaders' numbers.** With σ_z ≈ 0.7–1.4 mm per frame (§2.1) and tens of views per
  surface point, 1–1.5 mm Chamfer distance is reachable if poses are about 0.2° / 1 mm accurate.

## 5b. Cheap diagnostics to run first (public episodes only; CPU; minutes) [I]
These decide which of R1–R4 matters most per object, before any new reconstruction code is written.
1. **Split the Chamfer distance by direction.**
   - Report the GT→pred and pred→GT halves of CD-O separately, for each object.
   - A large GT→pred with a small pred→GT means missing surface: undersides or interiors (R3/R4).
   - Both large means smear or offset (R1/R2).
2. **Wall thickness.** In the GT-registered frame, cast rays along the scan normals through hollow objects and take the
   median distance between our two surface crossings. Compare with the scan's thickness. This sets R1's payoff.
3. **Error by height.** Bin GT→pred error by height above the table. A peak in the bottom 1 cm means R3/R4 matter.
4. **Pose consistency.** Compute the depth-to-mesh point-to-plane residual per frame along our tracks. Plot it against
   time and against hand-occlusion fraction. A high median (> 2 mm) or spikes means R2 comes before R1.
5. **Stereo noise.** Take frames where the object rests on the table. Fit a plane to the table depth near the object
   and measure the RMS. Do this at half and at full stereo resolution. This replaces the assumed σ_z in §2.1.

### Parameter cheat-sheet (provenance in the last column)
| Parameter | Value to try | Provenance |
|---|---|---|
| TSDF voxel v | 1.5 mm (2 mm fallback) | [I] from σ_z ≈ 0.7–1.4 mm (§2.1); Open3D notes small voxels are noise-sensitive ([doc](https://www.open3d.org/docs/release/tutorial/pipelines/rgbd_integration.html)) |
| Truncation μ | 3–4 v (4.5–6 mm) | DTSDF used 4v ([DTSDF](https://ar5iv.labs.arxiv.org/html/1908.05146)); BundleSDF 1 cm is too coarse ([ar5iv](https://ar5iv.labs.arxiv.org/html/2303.14158)) |
| Behind-surface drop-off | Full weight to −v, linear to 0 at −μ | Voxblox code ([cc](https://raw.githubusercontent.com/ethz-asl/voxblox/master/voxblox/src/integrator/tsdf_integrator.cc)) |
| Ray weight | 1/σ_z² ∝ 1/z⁴ (stereo); Voxblox uses 1/z² | Voxblox ([ar5iv](https://ar5iv.labs.arxiv.org/html/1611.03631)); stereo σ_z ∝ z² ([Intel](https://forums.intel.com/cipcp26785/attachments/cipcp26785/feeditem_no_topic/6363/1/BKM-For-Tuning-D435-and-D415-Cameras-Webinar_Rev3.pdf)) [I] |
| Direction bins | 6 (±xyz), threshold sin(π/8) ≈ 0.38 | DTSDF ([ar5iv](https://ar5iv.labs.arxiv.org/html/1908.05146)) |
| Mask and depth-edge erosion | 3 px at half resolution; drop depth steps > 5 mm | [I] from foreground fattening ([MIT](https://people.csail.mit.edu/tfxue/project/multiview-stereo)) |
| ICP gates | 1 cm / 20°, 5 iterations | BundleSDF ([ar5iv](https://ar5iv.labs.arxiv.org/html/2303.14158)) |
| Poisson | depth 10, `--bType 2`, `--envelope`, pointWeight 4 | Surfels used depth 10 ([arXiv](https://arxiv.org/html/2404.17774v2)); options ([repo](https://github.com/mkazhdan/PoissonRecon)) |
| Global registration | FPFH 5v, RANSAC 1.5v, ICP 0.4v at v = 3 mm | Open3D ([doc](https://www.open3d.org/docs/release/tutorial/pipelines/global_registration.html)) |
| PCA hypotheses | 24 | Li et al. ([suppl.](https://openaccess.thecvf.com/content/ICCV2021/supplemental/Li_A_Closer_Look_ICCV_2021_supplemental.pdf)) |
| Decimation | Quadric to ≤ 4096 faces, preserving boundaries | [I]: chord error ≈ 0.1 mm (§5) |

## 6. Ranked recommendations for tests on public episodes
Every item uses only video-derived inputs: stereo depth, SAM2 masks, our tracks, the table plane estimated from depth,
and object names. Ground truth is used only for scoring.
Parameter values are **[I]** unless a citation is attached. All expected gains are **[G]**: no paper measures our
setup.
The order follows the expected gain per unit of effort. R1–R4 run on CPU. R5 needs a GPU rental and the owner's go-ahead.

### R1 — Thin-wall fusion (replaces occupancy blur). CPU, about 1–3 min per object-episode. BSD/MIT code or our own.
- **Grid:** voxel v = 1.5 mm (2 mm if memory-bound). Truncation μ = 3v = 4.5 mm.
- **Weights:**
  - w = cos θ_view / σ_z², with σ_z from the formula in §2.1. Cap at W_max.
  - Behind-surface drop-off as in Voxblox: full weight down to sdf = −v, linear to 0 at −μ.
    ([code](https://raw.githubusercontent.com/ethz-asl/voxblox/master/voxblox/src/integrator/tsdf_integrator.cc))
- **Discard:**
  - Pixels within 3 px (half resolution) of the SAM2 boundary or of a depth step greater than 5 mm (stereo
    fattening).
  - Hand-mask pixels.
  - Rays with θ > 75°.
- **Two variants:**
  - (a) Plain TSDF with the drop-off.
  - (b) Directional TSDF: six bins, threshold sin(π/8), each bin fused separately.
    ([DTSDF](https://ar5iv.labs.arxiv.org/html/1908.05146)) Merge by meshing each bin and taking the union of the
    zero-crossings. The simpler alternative is to sample points with normals from each bin, then run R3's Poisson.
- **Optional:** full-resolution FoundationStereo (`--hiera 1`) for frames where the object is within 0.6 m.
- **Expected:** walls go from about 12 mm to 3–6 mm. CD-O goes from 0.40 to 0.25–0.30 cm on hollow objects **[G]**.
  The DTSDF paper measured 2–3× lower RMSE on thin geometry **[M]**.
- **Falsification:**
  - Pass if median wall thickness on cups and pot (rays through the wall in the GT-registered mesh) drops below 6 mm
    and per-object CD-O improves by at least 0.04 cm on at least 70% of hollow objects.
  - Variant (b) must beat (a) by at least 0.01 cm, or we keep (a).
  - If walls thin but CD-O does not drop, the bottleneck is pose smear. Go to R2.

### R2 — Alternate pose refinement and re-fusion. CPU (Open3D ICP); optional GPU silhouette term. About 5–10 min per episode.
- **Per frame:** point-to-plane ICP of the masked, eroded stereo points against the current R1 mesh.
  - 5 iterations. Correspondence gates 1 cm and 20° (the BundleSDF values,
    [ar5iv](https://ar5iv.labs.arxiv.org/html/2303.14158)). Huber δ = 2 mm.
  - Optionally add a silhouette IoU term with the mesh rendered in PyTorch3D (BSD).
- **Then:** sliding-window pose-graph smoothing (constant-velocity prior). Re-fuse with R1. Run 2–3 rounds.
- **Evidence:** pose refinement improved F-score from 0.868 to 0.924 and rotation error from 0.571° to 0.144°
  ([Azinović](https://ar5iv.labs.arxiv.org/html/2104.04532)) **[M]**. BundleSDF and 6DOPE-GS both rely on the same
  idea.
- **Expected:** a further 10–25% CD-O reduction **[G]**. Pose metrics should improve as well.
- **Falsification:**
  - Median ICP residual must fall by at least 20% from round 0 to round 2.
  - CD-O must improve by at least 0.02 cm.
  - Pose ADD must not degrade.
  - If residuals fall but CD-O rises, the refinement is fitting the mesh to its own errors (self-confirmation). Freeze
    the mesh while refining poses, or hold out 20% of frames to measure the residual.

### R3 — Envelope-constrained screened Poisson plus table-contact samples (replaces the support-fill, flatten-base and below-table heuristics). CPU, seconds. MIT.
- **Points:** oriented points from the R1/R2 zero-crossings, with normals from the TSDF gradient.
- **Envelope (watertight):** the intersection of
  - the visual hull from SAM2 masks, dilated by about 4 px and taking a vote of at least 90% of views,
  - the depth hull (voxels seen as free space at least 3σ_z in front of measured depth),
  - the half-space above the table plane.
- **Contact samples** in frames where the object rests on the table (track speed < 2 mm/frame): points on the table
  plane inside the object's footprint, with normal −n_table. This follows Vysics's support-point and hyperplane idea
  ([Vysics](https://arxiv.org/html/2504.18719v1)).
- **Command:**
  `PoissonRecon --in pts.ply --envelope env.ply --bType 2 --depth 10 --pointWeight 4 --samplesPerNode 2 --density`.
  Trim the lowest-density 2–5% of vertices outside the envelope band
  ([PoissonRecon](https://github.com/mkazhdan/PoissonRecon); [envelope](https://hhoppe.com/proj/envelope/)).
- **Expected:** closes undersides and open shells. Largest gain on boards, dust pan, pot and pitcher: 0.03–0.10 cm per
  object **[G]**. Co-Section's +42–71% completeness is the closest measured analogue **[M]**.
- **Falsification:** score the GT→pred and pred→GT halves of the Chamfer distance separately.
  - GT→pred must fall by at least 20% on objects with unseen bottoms.
  - pred→GT must not rise by more than 0.01 cm. If it does, the fill creates bulges (Co-Section's accuracy loss); fall
    back to planar caps.
  - Poisson can merge thin double-sided walls. Check that cup wall thickness from R1 is preserved within 1 mm, or use
    a finer depth.

### R4 — Cross-episode object fusion. CPU, about 1 min per object.
- **Register** per object name, for every pair of episodes:
  - Sample 20k points from the R3 meshes at v = 3 mm.
  - FPFH+RANSAC (normal radius 6 mm, FPFH 15 mm, RANSAC threshold 4.5 mm), or TEASER++.
  - Also try all 24 PCA hypotheses, then trimmed point-to-plane ICP (threshold 1.2 mm).
  - Accept only if trimmed RMS < 1.5 mm, overlap > 60%, and the second-best hypothesis is at least 30% worse.
    Otherwise do not fuse that episode.
- **Fuse:** integrate *raw depth* from all accepted episodes into one R1 grid in the canonical frame, composing poses
  with the inter-episode transform. Run R3 once. Map the result back into each episode's object frame.
- **Evidence:** multi-session completion ([Prankl'15](https://www.acin.tuwien.ac.at/fileadmin/acin/v4r/v4r/IROS15_IROS2015_ObjectModellingfinal.pdf));
  robust registration ([TEASER++](https://arxiv.org/abs/2001.07715)) **[M]**.
- **Expected:** undersides become *observed* rather than inferred, and noise averages down. 0.03–0.08 cm on top of
  R1–R3 **[G]**. It also gives one consistent mesh per object, which reduces flips between episodes **[I]**.
- **Falsification:** leave one episode out on the public set. The fused mesh built *without* episode k, scored on
  episode k's scan, must beat episode k's own R3 mesh on at least 70% of objects.
  - Also count failed or ambiguous registrations. If more than 20%, the fusion is unsafe for eval.
  - Selecting fusion parameters on eval results is forbidden.

### R5 (only if R1–R4 stall above 0.2 cm) — Final GPU refinement against depth, masks and photometry
- **Method:** start a 2DGS model (gsplat, Apache-2.0) or a mesh model (PyTorch3D with Large Steps) from the R4 mesh.
  - Losses: L1 depth (weight 1), mask BCE (weight 0.5), photometric loss on the colour camera with a rolling-shutter
    tolerance, normal consistency.
  - Jointly optimise keyframe poses, as in 6DOPE-GS.
- **Evidence:** 6DOPE-GS reaches 0.15 cm on YCBInEOAT (visible-surface protocol) **[M]**. DTU-level Gaussian methods
  reach 0.5–0.8 mm when poses are perfect **[M]**.
- **Cost:** about 10–30 min per object-episode on a 4090, from DTU timings of 8–50 min **[M→I]**. Rental needs
  owner approval.
- **Falsification:** CD-O must improve by at least 0.02 cm over R4 on at least 70% of objects. Thin-fin coverage
  (dish rack) must not regress.

**Not recommended now [I]:**
- RGB-only hand-object priors (HOLD, MagicHOI, G-HOP, HORT): they reach 1 cm or worse.
- Stability and equilibrium losses (PhysComp, Atlas3D, DSO): no accuracy gains measured against scans.
- Generative completion (SAM 3D, TRELLIS): no millimetre accuracy evidence. Keep it as a fallback for areas never seen.
- The hand prior is still worth using as *free space* (hand voxels cannot be object) and as weak contact samples. The
  measured gain is mostly from attraction-type contact: 0.448 → 0.333 Chamfer distance
  ([in-hand](https://arxiv.org/html/2312.16425)) **[M]**.

## 7. What was not verified (to avoid overclaiming)
- **Not read in full, so their numbers are not quoted:**
  - GHOST and GraG tables ([GHOST](https://arxiv.org/abs/2603.18912), [GraG](https://arxiv.org/abs/2604.12929)).
  - MOHO's absolute Chamfer distance ([CVF](https://openaccess.thecvf.com/content/CVPR2024/html/Zhang_MOHO_Learning_Single-view_Hand-held_Object_Reconstruction_with_Multi-view_Occlusion-Aware_Supervision_CVPR_2024_paper.html)).
  - HOISDF's HO3D results ([arXiv](https://arxiv.org/abs/2402.17062v1)).
  - SAM 3D's SA-3DAO metrics ([arXiv](https://arxiv.org/pdf/2511.16624)).
  - Atlas3D's and DSO's quantitative tables ([Atlas3D](https://arxiv.org/abs/2405.18515), [DSO](https://arxiv.org/abs/2503.22677)).
- **No 2025–26 successor to BundleSDF reports better accuracy than 6DOPE-GS.**
  - GTR ([arXiv](https://arxiv.org/abs/2505.11905)) compares with BundleSDF, but I did not read its numbers.
  - The 2026 hand-object interaction survey ([arXiv](https://arxiv.org/abs/2607.28394)) has a taxonomy but no HO3D
    Chamfer table on its abstract page.
- **Licences not confirmed from the LICENSE file:**
  - PGSR ([repo](https://github.com/zju3dv/PGSR)), NeuS2 ([repo](https://github.com/19reborn/NeuS2)) and
    FoundationStereo's research model ([repo](https://github.com/NVlabs/FoundationStereo)). The repos link LICENSE files
    I did not open.
  - Open3D is assumed MIT ([repo](https://github.com/isl-org/Open3D)).
- **The COLMAP fusion defaults** come from an unofficial wiki
  ([wiki](https://github.com/mwtarnowski/colmap-parameters/wiki/StereoFusion)). Check them with
  `colmap stereo_fusion -h`.
- **Rig specifics** (focal length, and whether the stereo pair is global shutter) were assumed. Check them against our
  calibration before using §2.1 and §5.
- **No public write-up of the V2D Track 3 leaders' methods turned up in a web search** (2026-10-26).
