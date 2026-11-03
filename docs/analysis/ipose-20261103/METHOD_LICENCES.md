# Method choice and licences (instance-pose lane, 3 Nov 2026)

## Candidates [L; checked on the repositories, 3 Nov]
| Method | Code licence | Weights | Fit for this task |
|---|---|---|---|
| GDRNPP (BOP 2022 winner; github shanice-l/gdrnpp_bop2022) | Apache-2.0 | BOP-dataset weights; licence not stated; not usable for our pot anyway | Needs a detectron2-from-source + CUDA 10/11 + C++-extension stack and a YOLOX detector; it does not match our torch 2.11 / cu130 image, so porting costs hours |
| SurfEmb (github rasmushaugaard/surfemb) | MIT | per BOP dataset | Long training per object, CosyPose detections, conda environment |
| ZebraPose (github suyz526/ZebraPose) | MIT | per BOP object | Tested on torch 1.10 / CUDA 11.1; long schedules (100k+ iterations); Progressive-X dependency |
| FoundationPose refiner / scorer fine-tune | NVIDIA Source Code License (non-commercial); already in our pipeline | released | Training code not released, so fine-tuning means re-implementing its losses and data |

## Chosen
A GDRN-style geometry-guided correspondence regressor, our own code (`pipeline/ipose/`), after GDR-Net (Wang et
al., CVPR 2021) and GDRNPP:
- crop → visible / amodal masks + dense object coordinates;
- pose by RANSAC Kabsch against our stereo depth (instead of GDRN's Patch-PnP head);
- depth makes the 3-D–3-D fit well posed.

It trains in tens of minutes on one 24 GB GPU and runs on our existing image.

## Components and licences
| Component | Licence | Note |
|---|---|---|
| `pipeline/ipose/*` (renderer, generator, net, solver) | ours | own point-splat renderer: no nvdiffrast (NVIDIA non-commercial) and no OpenGL |
| torchvision ResNet-34 | BSD-3-Clause | ImageNet-1k weights (torchvision); ImageNet terms are research-oriented, **flag for commercial use** |
| PyTorch, OpenCV, trimesh, SciPy, NumPy | BSD / Apache-2.0 / MIT | |
| Stereo depth from FoundationStereo (existing cache) | NVIDIA Source Code License, **non-commercial; flagged** | already part of perc2 |
| Control track (FoundationPose) | NVIDIA Source Code License, **non-commercial; flagged** | already part of perc2 |
| BlenderProc (not used) | GPL-3.0 | considered for renders; ours is enough here |
