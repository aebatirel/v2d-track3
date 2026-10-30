# Structured, primitive, parametric and retrieval reconstruction: literature and open-source review for V2D Track 3

Date: 2026-10-26. Web-only review; no repository changes. Written for the CD-O (Sim(3)-registered symmetric Chamfer) problem
described in the brief: our TSDF meshes score 0.40 cm, the leaders 0.11–0.15 cm, and a first in-house lathe scored 0.31–0.32 cm.

**Labels used throughout**
- **[M]** measured or stated in the cited paper, on its own data and with its own metric. These numbers are *not* CD-O.
- **[O]** our in-house measurement, as given in the brief. I did not re-verify these.
- **[I]** my inference. **[H]** a hypothesis; each one names a falsification test.
- When I write "≈ x % of size", that is my own conversion [I] under the paper's normalisation (a unit cube or a unit-diameter
  sphere). Chamfer definitions differ between papers (L1 or squared L2, sum or mean), so treat these conversions as order of
  magnitude only.
- Scale anchor [I]: the leaders' 0.11–0.15 cm is about 1 % of object size, so the objects are about 11–15 cm. On that scale our
  0.40 cm is about 3 %, and the lathe's 0.31 cm is about 2–2.5 %.

## 0. Bottom line

1. **Generic primitive abstraction is not accurate enough.** Superquadrics, neural CSG and convex parts are designed for
   compactness. The best published Chamfer-L1 is about 1.7–2.2 % of object size on ShapeNet [M: SuperDec
   https://arxiv.org/html/2504.00992v2, Marching-Primitives https://arxiv.org/html/2303.13190v2]. At our scale that is
   about 0.2–0.3 cm [I], roughly what our lathe already gets. These methods are useful for parts (the bristle block, a knob)
   and for initialisation, not as final meshes.
2. **Five of the eleven objects need one representation**: the two cups, the pot, the lid and the pitcher. It is a
   *closed-profile* surface of revolution: outer wall, rim, inner wall and base drawn as one closed 2-D curve, then revolved.
   Handles are added as swept tubes, and the pitcher's spout as a displacement field. The parts are well studied
   (axis estimation by line geometry, B-spline profiles, generalized-cylinder sweeps; §2), and none of it needs training. [I]
3. **The other objects map to small programs.** Boards are extrusions, the dish rack is an array program, the spoon and the
   brush handle are generalized cylinders fitted to silhouettes and stereo depth, and the dust pan is a shelled sheet
   template. Each has 10–40 parameters and can be fitted on CPU, by optimisation, to fused depth and SAM2 masks. [I]
4. **Learned CAD-code models are far from 1 % accuracy on real data.** CAD-Recode, cadrille and MeshCoder are trained on
   synthetic mechanical parts or Infinigen scenes. On the only real-scan benchmark (CC3D) the best of them reaches IoU 67.9 %
   [M: https://arxiv.org/html/2505.22914v3]. They can at most propose a structure; the numbers have to come from
   optimisation. [I]
5. **Learned symmetry completion helps little.** SymmCompletion improves CD on the PCN benchmark by about 4 %
   [M: https://arxiv.org/html/2503.18007v1]. Symmetry is more useful as a hard constraint built into the parametric model. [I]
6. **Retrieval plus deformation gets to category-level fidelity, and it carries a rules risk.** Deformation roughly halves
   Chamfer compared with retrieval alone on ShapeNet [M: https://arxiv.org/abs/2101.07889], which is still category-level. It
   is also unclear whether a retrieved, deformed mesh counts as our "own reconstruction". Do not ship it without written
   approval from the organisers, and never use the public-episode scans as templates (§5.4).
7. **Two metric effects matter for every structured model [I] (§7).** Missing or misplaced inner walls and undersides are
   penalised twice: by the area-weighted RMS-radius scale normalisation and by the Chamfer itself. And registration that
   starts from PCA is decided by the small asymmetric parts (handles, spout, slots, the concavity of the spoon bowl); if those
   parts are missing or the wrong size, registration rotates or flips.

## 1. Primitive decomposition and fitting

| Method | What it does | Accuracy as reported [M] | Code and licence |
|---|---|---|---|
| EMS, Liu et al., CVPR 2022 https://arxiv.org/abs/2111.14517 | Probabilistic superquadric fit. It infers an outlier posterior, refines with trust region, and uses a "switching" step to escape local minima between equivalent shapes. Can fit several superquadrics hierarchically. | Synthetic partial ratios down to 0.2, plus real KIT and BigBIRD scans. The text says it beats all baselines; the numbers are only in plots (https://arxiv.org/html/2111.14517v3) | https://github.com/bmlklwx/EMS-superquadric_fitting (MATLAB and Python; no licence shown) |
| Marching-Primitives, CVPR 2023 https://arxiv.org/abs/2303.13190 | Grows superquadrics from an SDF grid by voxel connectivity at several SDF levels | ShapeNet mean Chamfer-L1 0.022 (grid over [-0.5,0.5]³) and IoU 0.870, against 0.057 and 0.368 for Paschalidou's SQs. 6.7 s per object on CPU (https://arxiv.org/html/2303.13190v2) | https://github.com/ChirikjianLab/Marching-Primitives (MIT, MATLAB only) |
| SuperDec, ICCV 2025 https://arxiv.org/abs/2504.00992 | Feed-forward network that decomposes a point cloud into about 5 superquadrics | ShapeNet L1 1.70 (×10⁻²) with 5.8 primitives, against EMS 5.77 and SQ 3.67. ScanNet++ object instances: 1.70 against EMS 5.51 and CSA 2.91. Objects normalised to radius 0.5 (https://arxiv.org/html/2504.00992v2) | https://github.com/elisabettafedele/superdec (MIT; weights, including a "normalized" checkpoint for scene objects) |
| SQ, Paschalidou et al., CVPR 2019 https://arxiv.org/abs/1904.09970; cuboids, Tulsiani et al. https://arxiv.org/abs/1612.00404 | Learned unsupervised parsing into superquadrics or cuboids | See the SuperDec table above | |
| CSG-Stump, ICCV 2021 https://arxiv.org/abs/2108.11305 | Three-level CSG-like representation: intersection, then union, then primitives | ShapeNet CD-L2 (×10³, 2048 points): 1.505, against UCSG-Net 2.085, SQ 1.656 and VP 2.259 | |
| UCSG-Net, NeurIPS 2020 https://arxiv.org/abs/2006.09102 | Unsupervised CSG tree | A reviewer notes it "lacks detail… inferior… in the 3D task" (https://papers.nips.cc/paper/2020/file/63d5fb54a858dd033fe90e6e4a74b0f0-Review.html) | |
| D²CSG, NeurIPS 2023 https://arxiv.org/abs/2301.11497 | Quadric primitives, with a residual "complement" branch that is subtracted | Claims better quality and compactness on CAD shapes with complex or high genus | |
| CoACD, SIGGRAPH 2022 https://arxiv.org/abs/2205.02961 | Approximate convex decomposition with collision-aware concavity | Built for collision, not surface fidelity | https://github.com/SarahWeiii/CoACD (MIT, per the brew and PyPI listings) |
| Point2Cyl, CVPR 2022 https://arxiv.org/abs/2112.09329; SECAD-Net, CVPR 2023 https://arxiv.org/abs/2303.10613 | Extrusion cylinders (sketch and extrude) from point clouds | Best on Fusion Gallery and DeepCAD; synthetic CAD only | |
| SweepNet, ECCV 2024 https://arxiv.org/abs/2407.06305 | Sweep primitives: a superellipse profile along a B-spline axis, in as few as 14 floats | Unsupervised abstraction | Project page only |

**What this means for us [I]**
- At our scale, 1.7–2.2 % of size is about 0.2–0.3 cm, so superquadric and CSG abstractions (a few blobs fitted to a whole
  shape) are no better than our lathe. A superquadric cannot represent a cup's hollow interior; CSG needs a difference
  operation for it. Convex decompositions inflate thin walls and the rack's fins.
- Useful roles: (a) robust part segmentation and initialisation (EMS's outlier model and switching step are good ideas to
  copy); (b) final geometry for parts that really are blob-like: the bristle block (a rounded box is a superquadric with
  small ε), the pot-lid knob, the brush head. Marching-Primitives works directly on our TSDF grid; cheap to try, but needs MATLAB.

## 2. Surfaces of revolution (SOR) and generalized cylinders (GC)

### 2.1 Axis estimation
- **Line geometry.** Every surface normal of an SOR meets the axis. So one estimates normals, fits a *linear line complex*
  to the normal lines, and reads the axis from the fit. The fit is a generalised eigenvalue problem, and the same approach
  covers helical and spiral surfaces [M]. Sources: Pottmann and Randrup
  (https://orbit.dtu.dk/en/publications/rotational-and-helical-surface-approximation-for-reverse-engineer/), ECCV 2004
  (https://www.geometrie.tuwien.ac.at/ig/publications/oldpub/2005/hopsw_line_05/paper_docs/line.pdf) and the 2002 summary
  (https://miro.geometrie.tuwien.ac.at/geom/ig/peternell/cv2002.pdf). A basis-independent generalisation is Andrews and
  Séquin 2013 (https://doi.org/10.1016/j.cad.2012.10.047).
- **Robust variants.** Cao and Mumford fit the axis by least squares to estimated circle centres
  (https://www.dam.brown.edu/people/mumford/vision/papers/2002d--CaoPots-journal.pdf; the PDF was unreachable today, so this
  description comes from search excerpts). Willis et al. fit an axially symmetric implicit polynomial to points and normals,
  with a statistical error analysis (https://mlanthology.org/cvprw/2003/willis2003cvprw-accurately). RANSAC over normals in
  Plücker coordinates is reported to be robust to noise and outliers
  (https://jcad.cn/article/id/761dd0d0-8f63-4b47-b9dd-ac7331ead61a) [M, claims].
- **Hard case [M].** Mara and Sablatnig tested 35 real pottery *fragments*. About 50 % agreed across all three methods,
  30 % agreed within 20 mm in radius and 20° in orientation, and 20 % could not be processed
  (https://cvl.tuwien.ac.at/wp-content/uploads/2014/12/cvww05c1.pdf). Our fused whole-object clouds cover far more of the
  surface, so this is an easier problem [I].
- **Recommended pipeline [I].** (1) Initialise the axis with the line-complex eigen-solution on trimmed points with good
  normals. (2) Refine axis (4 DoF) and profile jointly by Gauss–Newton or LM on point-to-profile distance, with a Huber or
  trimmed loss; stereo normals are noisy, so point distances should drive the refinement. (3) Treat points with large
  residuals as handle or spout candidates, remove them and iterate. (4) Validate with a histogram of radial residuals per
  azimuth bin, which should be flat for a true SOR.

### 2.2 Profile curve
- Map the inlier points to the (r, z) half-plane and fit a least-squares B-spline. SciPy's `make_lsq_spline` takes
  user-chosen knots and per-point weights
  (https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.make_lsq_spline.html).
- Prior work [M]: KAIST maps rotational free-form point data to orthogonal coordinates and fits a single-valued B-spline,
  recovering the exact shape when the data is a true SOR (https://dspace.kaist.ac.kr/handle/10203/83369). Single-image
  celadon reconstruction runs contour, then axis, then B-spline profile, then multi-resolution meshes
  (https://www.mdpi.com/2076-3417/13/11/6848/html). DeepSpline learns spline profiles and notes that local optimisers need a
  close initialisation (https://ar5iv.labs.arxiv.org/html/1901.03781). Single-view SOR from silhouettes has a 2-parameter
  ambiguity (https://mi.eng.cam.ac.uk/reports/abstracts/kykwong_bmvc02.html); we avoid it because we have metric depth [I].
- **Sharp rims and base edges [I].** Use a polyline with explicit corner vertices and smooth segments in between, or give
  interior knots a multiplicity equal to the degree, which yields C⁰ corners. That is a standard B-spline property; the SciPy
  page only demonstrates repeated *boundary* knots [M]. Point2CAD gets sharp CAD edges by extending, intersecting and
  trimming fitted analytic surfaces (https://arxiv.org/abs/2312.04962) [M]. The 2-D analogue is to intersect the fitted wall
  line with the fitted rim and base segments.

### 2.3 Thin walls: inner and outer surfaces
- **Why TSDF walls come out thick.** Measurements of a thin wall from opposite sides cancel in a linear TSDF update, and
  structures thinner than a voxel cannot be represented at all. Directional TSDF fixes this by storing opposite surfaces
  separately (https://arxiv.org/abs/1908.05146) [M]. This matches our thick, rounded walls [I].
- **Pottery practice.** Archaeologists document a vessel as its *profile*, the intersection with a plane through the
  rotational axis (https://cvl.tuwien.ac.at/wp-content/uploads/2014/12/cvww05c1.pdf) [M]. By construction the profile holds
  both the outer and the inner outline, and so the wall thickness [I].
- **Recommended closed-profile model [I].** One closed curve runs outer wall(z), then rim (flat or round, radius ρ), then
  inner wall(z) = outer(z) − t(z), then inner floor, base underside, and back to the outer wall. Parameters: the outer-wall
  B-spline, t (constant or linear in z), ρ, base thickness, foot ring height. Fit the outer wall to outside views and the
  inner wall to interior points seen over the rim; where the interior is not seen, take t from the rim width, which top
  views measure. Revolve (our own lathe or CadQuery `revolve`, https://pypi.org/project/cadquery); the mesh is watertight
  by construction.
- **Estimate of the CD-O effect [I], with illustrative numbers.** Suppose the ground truth has an inner wall and ours is
  missing or offset by t. The inner wall is about 40 % of a cup's area, and its samples sit about t from our surface. With
  t ≈ 3 mm, that term alone adds roughly 0.05 cm to the symmetric mean, about half of a leader's total score. A missing
  surface also changes the area-weighted RMS radius, which rescales our whole mesh before the Chamfer.
  **Test:** on public episodes only, score lathe variants with outer-only, inner+outer and thick walls, and break the error
  down by GT region.

### 2.4 Handles, spouts and generalized cylinders
- **Generalized cylinders [M].** 3-Sweep: many man-made objects decompose into GCs and cuboids that snap to image outlines
  (https://cg.cs.tsinghua.edu.cn/3sweep/). GC decomposition uses an MDL cylindricity measure and a global exact-cover
  selection (https://www2.cs.sfu.ca/~haoz/pubs/zhou_siga15_gcd.pdf). Neural GC is an editable neural SDF defined around a
  centre curve (https://arxiv.org/abs/2410.03675).
- **Thin and tubular parts from video [M].** Vid2Curve models thin objects as connected GCs with radii from images, using
  RGB video (https://arxiv.org/abs/2005.03372). CurveFusion works from RGB-D sequences with L1-medial axes per frame
  bundle, and reports that voxel fusion largely fails on such structures (https://arxiv.org/abs/2107.05284). The L1-medial
  skeleton tolerates noise and missing data (https://www2.cs.sfu.ca/~haoz/pubs/huang_sig13_l1skel.pdf); a third-party C++
  implementation exists (https://github.com/jasonkena/L1-Skeleton), licence not checked.
- **Recommended handle pipeline [I].** (1) Cluster the SOR residual points. (2) Fit a plane; a mug or pitcher handle lies
  roughly in a plane that contains the axis. (3) Fit a 2-D centreline spline in that plane. (4) Give it a superellipse
  cross-section with radii a(s), b(s) and sweep it (CadQuery `sweep`). (5) Boolean-union it with the body (manifold3d,
  Apache-2.0, https://github.com/elalish/manifold). (6) Refine the centreline and radii against SAM2 masks with a
  silhouette loss.
- **Spout [I].** Model it as a displacement field on the SOR: r(θ, z) = r₀(z) + d(θ, z), where d is a smooth tensor B-spline
  that is non-zero only near the spout azimuth. The same field absorbs mild non-circularity. This is my proposal; I found no
  paper that does exactly this.

### 2.5 Primitive-detection tools
- Efficient RANSAC detects planes, spheres, cylinders, cones and tori
  (https://cg.cs.uni-bonn.de/backend/v1/files/publications/schnabel-2007-efficient.pdf). The authors' library is
  research-only (https://armarx.humanoids.kit.edu/d8/daf/ReadMe_8txt.html). CGAL reimplements it
  (https://doc.cgal.org/latest/Shape_detection/); CGAL packages are GPL, as the PSR doc shows
  (https://doc.cgal.org/5.6/Polygonal_surface_reconstruction/group__PkgPolygonalSurfaceReconstructionRef.html).
- pyransac3d covers planes, cylinders and cuboids under Apache-2.0 (https://pypi.org/project/pyransac3d/).

## 3. Symmetry priors

- **Classical detection [M].** Mitra, Guibas and Pauly 2006 find partial and approximate symmetries by voting in
  transformation space (https://graphics.stanford.edu/~niloy/research/approx_symmetry/approx_symm_sig_06.html). Pauly et al.
  2008 detect regular grids of repeated elements despite outliers and missing elements
  (https://www.cs.princeton.edu/courses/archive/spring11/cos598A/pdfs/Pauly08.pdf); directly relevant to the rack's fins.
- **Classical completion [M].** Thrun and Wegbreit 2005 detect probable symmetries in partial range data from an active
  stereo rig, use them to extend the model into occluded space, and segment the object into parts with separate symmetries
  (https://mlanthology.org/iccv/2005/thrun2005iccv-shape). I found no Chamfer numbers for it.
- **Learned detection [M].** NeRD (CVPR 2021) finds a reflection plane from a single image, more accurately than direct CNN
  regression (https://arxiv.org/abs/2105.03211; code https://github.com/zhou13/nerd). SymmetryNet (SIGGRAPH Asia 2020)
  predicts reflective *and* rotational symmetries from single-view RGB-D, together with per-point symmetric counterparts
  (https://arxiv.org/abs/2008.00485).
- **Learned completion: measured gains [M].** SymmCompletion (AAAI 2025) scores CD-L1 6.28 (×10⁻³) on PCN, against 6.54
  for SVDFormer, an improvement of about 4 %; removing its symmetry guidance gives 6.51; on real KITTI scans it is *not*
  best on FD or MMD (https://arxiv.org/html/2503.18007v1; code https://github.com/HongyuYann/SymmCompletion).
- **Pose ambiguity [M].** DiffusionNOCS reports that pose distributions for mugs are sharp when the handle is visible and
  spread out when it is hidden (https://arxiv.org/abs/2402.12647). The same mechanism causes our registration flips (§7).
- **What this means for us [I].** With about 260 views, unseen *azimuths* are rare; the gaps are mostly undersides and
  interiors. Reflection or rotation cannot recover a bottom, which differs from the top; that needs a prior such as a flat
  base plus wall thickness. So use symmetry as a hard constraint inside the parametric model: continuous rotation for an
  SOR, C₂ symmetry for the pot's handles, mirror planes for the boards, the dust pan and the rack. Learned completion nets
  give single-digit percent gains on synthetic benchmarks, which is irrelevant at the 2–3× we need.

## 4. CAD and program inference

- **CAD-Recode** (ICCV 2025): a point cloud goes in, CadQuery Python comes out (https://arxiv.org/abs/2412.14042). [M] It
  uses Qwen2-1.5B with a point projector, trained on 1 M procedurally generated sketch-extrude programs; it samples several
  candidates and keeps the one with minimum Chamfer to the input; it reports 10× lower mean CD than prior methods on DeepCAD
  and Fusion360. Weights: https://github.com/filaPro/cad-recode (the LICENSE file exists, but I did not read it).
- **cadrille** (ICLR 2026 oral; https://arxiv.org/html/2505.22914v3): point cloud, image or text input, CadQuery output.
  [M] On the real CC3D scans (which include revolve, chamfer and fillet operations, plus noise and missing parts), median CD
  (×10³, 8192 points, [-0.5,0.5]³) is 0.47 with IoU 67.9 % after RL. CAD-Recode scores 0.54 and 60.5 %. Ground truth
  resampled against itself scores 0.15. Code is Apache-2.0, with weights on Hugging Face (https://github.com/col14m/cadrille).
- **CADCrafter** (CVPR 2025): image to CAD, trained only on synthetic textureless renders, fine-tuned with DPO using an
  automatic code checker, and tested on a real multi-view set it collected (https://arxiv.org/abs/2504.04753) [M, qualitative].
- **Text2CAD** (https://arxiv.org/abs/2409.17106) and **CAD-MLLM** (Omni-CAD dataset, about 450 k instances,
  https://arxiv.org/abs/2411.04954) generate sketch-extrude sequences [M]. Their scope is mechanical CAD.
- **MeshCoder** (NeurIPS 2025; https://arxiv.org/abs/2508.14879; code https://github.com/ZhaoyangLyu/MeshCoder, MIT, weights
  on Hugging Face): a point cloud in [-1,1]³ goes in, Blender Python comes out. [M] Its API covers primitives, sweeps
  (including solids of revolution), bridge loops, 1-D and 2-D arrays, booleans and bevels, plus special "Spoon" and "Fork"
  types. It is trained on 41 Infinigen categories, including Cup, Bowl, Jar and Bottle, and scores CD 0.06 against PLAD 1.87,
  on synthetic data only. [I] It is the closest open model to our object set (arrays for the rack, a spoon type), but its
  output is still a *structure guess* that needs re-fitting.
- **Programs fitted to data [M].** GeoCode: hand-built procedural programs plus a network that recovers their parameters
  from point clouds, reported to generalise to noisy and real scans (https://ar5iv.labs.arxiv.org/html/2212.11715, code
  https://github.com/threedle/GeoCode). ShapeAssembly: a differentiable interpreter fits programs to point clouds
  (https://arxiv.org/abs/2009.08026).
- **LLMs and VLMs writing models [M].** ShapeLib: an LLM designs a library of shape functions; the authors note that LLMs
  "misinterpret or misattribute constraints" (https://arxiv.org/abs/2502.08884). LL3M: multi-agent LLMs write Blender code
  from text (https://arxiv.org/abs/2508.08228). CAD-Assistant: a VLM planner drives FreeCAD tools, including a 2-D
  cross-section tool (https://arxiv.org/abs/2412.13810).
- **What this means for us [I].** I found no paper that reports the exact loop of "VLM writes a parametric template, then an
  optimiser fits it to real depth" with Chamfer near 1 %; the pieces exist. With only about 11 objects, hand-writing about 6
  templates with typed bounds is cheaper and more controllable than an LLM, which pays off only beyond this object set. Fit
  each template with CMA-ES or Nelder–Mead on (trimmed Chamfer to fused depth) + λ·(1 − mask IoU), or with gradients
  through an analytic SDF. The learned CAD models are trained on sketch-extrude mechanical parts, a mismatch with our
  household objects.

## 5. Retrieval and deformation, category priors, and the rules

### 5.1 Retrieval embeddings [M]
- OpenShape: 46.8 % zero-shot top-1 on Objaverse-LVIS across 1156 categories (https://arxiv.org/abs/2305.10764). Uni3D:
  1 B parameters (https://arxiv.org/abs/2310.06773). DuoduoCLIP: multi-view, 87 M parameters, 14.3 h to train
  (https://arxiv.org/abs/2406.11579). These retrieve a *category*, not the instance. [I]

### 5.2 Alignment to images or scans [M]
- Scan2CAD aligns CAD models in RGB-D scans
  (https://openaccess.thecvf.com/content_CVPR_2019/papers/Avetisyan_Scan2CAD_Learning_CAD_Model_Alignment_in_RGB-D_Scans_CVPR_2019_paper.pdf).
  ROCA raises retrieval-aware alignment accuracy on ScanNet from 9.5 % to 17.6 % (https://arxiv.org/abs/2112.01988; code
  https://github.com/cangumeli/ROCA). DiffCAD beats the supervised state of the art on Scan2CAD by 5.9 % with 8 hypotheses
  (https://arxiv.org/abs/2311.18610). Zero-shot inexact alignment: https://arxiv.org/abs/2507.03292. [I] Success here is
  measured in coarse thresholds of pose and scale, far from 1 mm-level geometry.

### 5.3 Deformation and category priors [M]
- Neural Cages (https://arxiv.org/abs/1912.06395; code https://github.com/yifita/deep_cage, MIT). DeepMetaHandles, with
  biharmonic coordinates (https://arxiv.org/abs/2102.09105). ARAP (https://diglib.eg.org/handle/10.2312/SGP.SGP07.109-116);
  libigl's implementation is MPL-2.0 according to its header
  (https://git.inf-cv.uni-jena.de/3DFaces/libigl_Martin/raw/master/include/igl/ARAPEnergyType.h).
- Joint retrieval and deformation (Uy et al. 2021): chairs score Chamfer about 1.0 against 1.93 for retrieval only (×10⁻²,
  ShapeNet; the table extraction was partly garbled, so check the PDF) (https://arxiv.org/abs/2101.07889).
- DeepSDF fits a latent code to partial depth; its error grows roughly linearly with depth noise
  (https://arxiv.org/abs/1901.05103;
  https://openaccess.thecvf.com/content_CVPR_2019/supplemental/Park_DeepSDF_Learning_Continuous_CVPR_2019_supplemental.pdf).
- Category shape-prior deformation on real RGB-D: SPD scores CD 3.17 on REAL275 against 4.41 for the prior alone
  (https://arxiv.org/abs/2007.08454). A later method scores 1.12 (×10⁻³) on mugs (https://arxiv.org/abs/2309.01925).
- Generative image-to-3D: SAM 3D Objects wins at least 5:1 in human preference, but reports little metric-geometry evidence
  (https://arxiv.org/abs/2511.16624; https://github.com/facebookresearch/sam-3d-objects).
- [I] All of these are category-level. They help where we see too little of an object, and lose wherever we observe it well.

### 5.4 Rules risk [I]
As relayed in the brief, the FAQ says CD-O must use our own reconstructed meshes, not the public scans. The cases:
- **(a) Clearly prohibited:** using the organisers' public-episode scans as templates for the same physical objects in eval
  episodes. That also breaks our own rule in CLAUDE.md: no ground truth in inference.
- **(b) Grey zone:** an Objaverse or ShapeNet mesh, retrieved and deformed. Its topology and vertices come from a third
  party, so organisers could reasonably say it is not "own reconstruction". If we ever want this, ask them in writing first.
- **(c) Defensible:** a generic parametric template whose every number is fitted to our observations. The object name may
  choose the template, since names are allowed.
- Licences vary per Objaverse object, and some are NC (https://pypi.org/project/objaverse/0.0.4). Objaverse-XL is ODC-By at
  dataset level, with per-object licences and a Polycam subset that is NC on request
  (https://huggingface.co/datasets/allenai/objaverse-xl/blob/64b19a1a8784b156a33e5f1b778310c00de55fe0/README.md) [M].

## 6. Thin, elongated objects: the spoon and the brush handle

- **Volumetric fusion fails on them [M]** (https://arxiv.org/abs/1908.05146, https://arxiv.org/abs/2107.05284).
- **Curve-skeleton methods [M].** Wire art from 3 views
  (https://geometry.cs.ucl.ac.uk/projects/2017/wire-art-reconstruction/paper_docs/LiuEtAl_ImageBasedReconstructionOfWireArt_Siggraph17.pdf);
  a visual hull, then skeleton, then cubic splines, then image-guided refinement
  (https://cgv.cs.nthu.edu.tw/projects/recreational_graphics/MVWA); Vid2Curve's GCs (https://arxiv.org/abs/2005.03372).
- **Silhouette fitting [M].** SoftRas gives smooth silhouette gradients and a blur schedule for pose
  (https://vgl.ict.usc.edu/Software/SoftRasterizer). Differentiable Stereopsis notes that silhouettes cannot capture
  concavities (https://arxiv.org/abs/2110.05472). [I] So the *concavity* of the spoon bowl must come from stereo depth.
- **Renderers.** PyTorch3D is BSD (https://github.com/facebookresearch/pytorch3d). nvdiffrast is under the NVIDIA Source
  Code License (https://github.com/NVlabs/nvdiffrast) [M]; check its terms before using it in submitted code, as I recall it
  is non-commercial [I].
- **Proposed spoon model [I], about 20 parameters.** A centreline B-spline in a plane, with gentle bending allowed. Handle
  cross-section: a superellipse with width w(s) and thickness h(s). Bowl: a shell (thickness t) of a superellipsoid cap with
  depth d, blended into the handle. Initialise from the PCA of the fused points plus the mask visual hull. Fit with
  Σ_frames (1 − soft-mask IoU) plus a robust depth Chamfer, and break the front/back ambiguity with depth.
- **Brush handle [I].** The same GC model. For the bristle block, use a superquadric or rounded box (EMS-style robust fit).

## 7. Metric-specific pitfalls for structured models (all [I])

- **Scale normalisation.** The area-weighted RMS surface radius depends on *which surfaces exist*. If GT has an inner cup
  wall, or a pot interior and underside, and we omit it, our normalised scale shifts and every point moves. So structured
  models must reproduce the surface set that the GT scans actually contain. **Check on public GT (diagnostics only):** do
  the GT meshes for cups and the pot contain inner walls and undersides? How thick are the walls? Are the rack fins
  resolved, or blobbed by the scanner?
- **Registration flips.** For a near-SOR, the two transverse PCA eigenvalues are nearly equal. The in-plane axes are then
  set by the handle and spout mass, and trimmed ICP only refines from there. A missing or undersized handle makes our PCA
  frame disagree with GT's. CD-O is then barely hurt on the body, but the derived body frame rotates and the pose metrics
  fail. The same holds for a board's slots, which break its 180° symmetry, and for the bowl concavity of the spoon.
  **Test:** on public episodes, log the scorer's recovered rotation residual about the symmetry axis for each object and
  count flips by variant.
- **Model selection without GT.** For each object, pick among TSDF, lathe and template by self-consistency on *held-out
  frames*: depth residual plus mask IoU. That is legitimate at eval time. **Falsification:** on public episodes, the
  self-consistency ranking must agree with the GT CD-O ranking on at least about 80 % of objects; if not, the selector is
  invalid.

## 8. Ranked recommendations per object

"Expected" is a **[H] guess**, not a measurement. The only measured anchors are TSDF 0.52 → lathe 0.31 on the blue cup and
0.44 → 0.32 on the pot [O]. Every test below runs on public episodes only; GT is used only by the scorer.

| Object | Rank-1 representation | Fit to our data | Expected CD-O [H] | Main risks | Falsification test |
|---|---|---|---|---|---|
| Cups (beige, blue) | Closed-profile lathe with wall thickness t, a sharp or round rim, a flat base, plus a swept-tube handle if one is present | Axis by line complex, then joint LM. Profile by LSQ B-spline in (r, z). Handle from SOR residual clusters, refined by silhouette | 0.15–0.22 (lathe 0.31 [O]) | Handle missing or wrong azimuth (flip); inner wall not observed (t prior); handle detection on a handle-less cup | Ablate outer-only, +inner, +handle. If adding the handle does not lower CD-O *and* the flip count, the handle model is wrong |
| White pot | Closed-profile lathe plus 2 handles under C₂ symmetry | As for cups. Handles fitted jointly with the constraint | 0.15–0.22 (lathe 0.32 [O]) | Interior hidden by the lid; wrong handle shape (loops or lugs) | Per-region error map. If the handle regions still dominate the residual after adding handles, change the handle model |
| Pot lid | Lathe (dome, flange, rim) plus a coaxial knob (lathe or superquadric) | Same lathe pipeline. The knob is a separate profile segment | 0.12–0.20 | Up/down flip if the underside flange is wrong | Count flips on public episodes. If flips persist, the underside profile is under-constrained |
| Pitcher | Lathe body plus displacement field d(θ, z) for the spout, plus a swept handle | Lathe first, then fit d as a tensor B-spline on residuals, then the handle | 0.18–0.28 | Body not an SOR (oval); spout too thin for depth | Compare against lathe-only and against TSDF. If the d-field gain is under 10 %, drop it |
| Dust pan | Thin-sheet template: CadQuery sketch, extrude, `shell(t)`, plus a handle extrude or sweep. Alternative: piecewise-planar mid-surface offset by ±t/2 | CMA-ES on Chamfer plus mask IoU over about 12 parameters | 0.20–0.30 | Wrong fold topology; curved walls | If it is not better than TSDF on public episodes, keep TSDF |
| Mini sweeper or brush | Superquadric or rounded box (bristle block) plus a GC handle | EMS-style robust fit for the block; GC with silhouettes for the handle | 0.20–0.30 | GT bristles may be ragged; joint geometry | Per-part error. If the block error exceeds TSDF's, keep TSDF for the block and use the hybrid |
| Dish rack | Array program: base frame plus N fins (pitch p, thickness τ, height profile) | Periodicity from FFT or Pauly-style lattice detection on projected points; then fit N, p, τ to depth and masks | 0.15–0.40 (high variance) | Fin count off by one; GT scan may itself blob the fins | First inspect whether the GT shows fins. If not, model a solid envelope instead |
| Wooden boards | Extrusion: polygon outline with slot notches, thickness from two RANSAC planes | Outline from the projection of points and masks onto the board plane, via alpha shape and polygon simplification; slots as rectangles | 0.08–0.15 | Slot position or width errors cause in-plane flips | Flip count plus CD-O against TSDF. If slots are mislocated by more than 3 mm, refine with silhouettes |
| Wooden spoon | GC handle plus a shelled superellipsoid bowl (§6) | Silhouette IoU plus depth Chamfer; bowl concavity from depth | 0.15–0.25 | Bowl inverted (flip); stereo noise on a part only mm thick | Check the sign of bowl depth against held-out depth. If it is unstable, add a prior on bowl depth |

**Ordering by expected gain per effort [I]:** (1) finish the lathe for the cups, pot and lid (closed profile, inner wall,
sharp rim, then handles): 4 of 11 objects on a pipeline that already exists; (2) boards: simple, and likely the largest
relative gain; (3) spoon; (4) pitcher; (5) sweeper; (6) dust pan; (7) rack: riskiest, and it depends on what the GT contains.

**Hybrid fallback for every object [I].** Keep TSDF as a candidate and use the self-consistency selector (§7), or use the
structured mesh only for parts it models well, union it with the TSDF elsewhere, and remesh to 4096 or fewer faces.

## 9. Reusable open-source code and licences (as stated on repo or package pages; verify before vendoring)

| Purpose | Code | Licence |
|---|---|---|
| Superquadric fit (robust, multiple) | https://github.com/bmlklwx/EMS-superquadric_fitting | Not shown on the page |
| SQs from SDF | https://github.com/ChirikjianLab/Marching-Primitives | MIT (needs MATLAB) |
| Learned SQ decomposition | https://github.com/elisabettafedele/superdec | MIT, weights |
| Convex decomposition | https://github.com/SarahWeiii/CoACD | MIT |
| Primitive RANSAC | https://pypi.org/project/pyransac3d/; CGAL https://doc.cgal.org/latest/Shape_detection/ | Apache-2.0; GPL |
| Planar polygonal surfaces (boards) | PolyFit https://3d.bk.tudelft.nl/liangliang/publications/2017/polyfit/polyfit.html; CGAL PSR | Not verified; GPL |
| CAD kernel (revolve, sweep, shell) | CadQuery https://pypi.org/project/cadquery | Apache-2.0 |
| Mesh booleans | manifold3d https://github.com/elalish/manifold | Apache-2.0 |
| B-spline LSQ | SciPy `make_lsq_spline` (doc link in §2.2) | BSD (SciPy) |
| Differentiable rendering | PyTorch3D https://github.com/facebookresearch/pytorch3d; nvdiffrast https://github.com/NVlabs/nvdiffrast | BSD; NVIDIA Source Code License |
| Curve skeleton | https://github.com/jasonkena/L1-Skeleton (third party) | Not verified |
| CAD-code models | cadrille https://github.com/col14m/cadrille; CAD-Recode https://github.com/filaPro/cad-recode; MeshCoder https://github.com/ZhaoyangLyu/MeshCoder | Apache-2.0; not read; MIT |
| Freeform CAD fitting | Point2CAD https://github.com/YujiaLiu76/point2cad | Not verified |
| Deformation | Neural Cages https://github.com/yifita/deep_cage; libigl ARAP | MIT; MPL-2.0 |
| Symmetry | NeRD https://github.com/zhou13/nerd; SymmCompletion https://github.com/HongyuYann/SymmCompletion | Not verified |
| Retrieval and alignment | ROCA https://github.com/cangumeli/ROCA; procedural programs GeoCode https://github.com/threedle/GeoCode | Not verified |

## 10. Next experiments and cost

- **Everything in §8 is CPU work** [I]: axis and profile fitting, CadQuery and manifold, CMA-ES over about 20 parameters,
  and PyTorch3D silhouettes on a small GPU or on CPU at low resolution. No Vast rental is needed until we want a batch
  re-scoring run.
- **Order of experiments:** (E1) inspect the public GT surface set (inner walls, undersides, fins) as a diagnostic;
  (E2) closed-profile lathe with inner wall and sharp rim, on cups, pot and lid; (E3) add handles, logging flip counts;
  (E4) board extrusion; (E5) spoon GC; (E6) validate the self-consistency selector against public CD-O.
- **Kill criteria.** E2: if the closed-profile lathe does not beat the current lathe on *both* the cups and the pot, the
  thin-wall hypothesis (§2.3) is falsified; re-examine the GT surface set and the registration before adding more parts.
  E4: if structured boards do not beat TSDF on public episodes, the bottleneck is pose or registration, not representation.
