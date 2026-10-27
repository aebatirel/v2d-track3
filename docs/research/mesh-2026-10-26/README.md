# Object meshes: how to make them accurate (research round, 2026-10-26)

Owner's request: "work on 3D mesh generation and make it accurate, test it on the public data, think about everything
we tried (video generation, primitive generation, physics-based meshes, …) and find out how to increase mesh
accuracy; do detailed research on methods."

Labels:
- **[M]** measured here, without ground truth;
- **[D]** diagnostic against the public scans, after inference (the public scan stands in for the hidden one);
- **[L]** from the literature (the `lit/` reports cite each source);
- **[E]** estimate; **[H]** hypothesis, with the test that would falsify it.

Everything here ran on the cloud VM's CPU ($0). No GPU was rented, no submission was made and no existing pipeline
file was changed.

## Answer in brief

1. **Meshes count twice.** CD-O is its own board, but the kit also registers our mesh to the hidden scan to define the
   body frame used by AUC, SP-SR, MP-SR, RPE and MPPE. A registration error of θ rotates the whole trajectory by θ, and
   a flip ruins the episode.
   - Ours: CD-O **0.402 cm**. Leaders: 0.154 (richchentw, also first on AUC), 0.112 (Panav Raaj) [M, leaderboard JSON].
   - The spoon is 10 of the 36 CD-O pairs. Our current spoon is a parametric template (≈ 0.18 cm, inferred).
2. **The information is in our depth; our mesher throws it away.**
   - Our stereo points, moved into the object frame along our own tracks, lie a median **0.9 mm** (blue cup) and
     **1.9 mm** (pot) from the scan [D].
   - The submitted TSDF meshes average 4–9 mm. The mesher binarises a 4 mm TSDF and blurs it, so 3 mm walls become
     12–20 mm slabs.
3. **What the scorer rewards (new findings) [D]:**
   - The scans are thin double-walled shells (cup walls 2.4–3.2 mm, pot 3.9, lid 1.8, pitcher 2.2, rack fins ≈ 2.5).
   - They are also **partial**: the blue-cup scan has no inner wall in its lower half, because the scanner never saw
     it.
   - CD-O's scale fix (the ratio of area-weighted RMS radii) punishes a wrong *distribution of surface area*, not
     only a wrong shape.
     - Example: a thin-walled lathe of the blue cup scores 0.382 cm as scored, but 0.316 cm at its true metric scale.
     - Missing or extra surfaces (inner walls, base, markers) shift the scale.
4. **A thin-walled lathe fitted directly to observations helps the cup** [D], without ground truth in the method:
   - blue cup 0.523 → **0.291 cm** with ep21 (0.364 with ep22);
   - registration offset 10.0 → 4.1 mm;
   - 0 flips out of 7 seeds;
   - recovered wall 2.0–3.5 mm against 3.2 mm in the scan.
   - A GT-free fidelity score picked the better episode.

   The same method does not yet beat our pot mesh: 0.437 → 0.413–0.468 cm. The handle comes out inflated, and
   without its handle the pot body flips in registration. The earlier library-based lathe (approach 2) remains
   better on the pot (0.319).
5. **Screened Poisson on the raw points fails** (0.96–1.11 cm) [D]. Noise creates crumpled, multi-layer surfaces
   with 1.6× the true area. Any point-based surface needs denoising or a structural prior first.
6. **The leaders' level (≈ 1 % of object size) has, in the literature, been reached only by "generate, then fit to
   observations"** [L]:
   - image-to-3D alone reaches about 2 % of size on real images;
   - pipelines that fit a generated mesh to video or depth (AGILE, MagicHOI, RecGen3D, GenPC) report 30–75 % lower
     Chamfer than either part alone.

   We have never run a generative model. A GPU probe is ready to go (crops and fit code written). It is blocked on
   two owner decisions, listed under "Owner actions".
7. **Recommended plan** (details and costs below):
   - CPU: finish the observation-first family fits (lathe for cups, pot and lid; extrusions for boards).
   - GPU, ≈ $4–8: generative probe on the 9 public objects, scored against the scans.
   - Then generate-and-fit for every object, with a GT-free selector that picks per object between TSDF, family fit
     and generative fit.

## 1. What the scorer does with a mesh (kit `metric_code/track_3/CD-O.py`, `AUC.py`, read 26 Oct)
- **CD-O:**
  - rescale our mesh about its surface centroid by the ratio of the two meshes' area-weighted RMS radii;
  - sample 10,000 points on each surface;
  - 25 PCA-start trimmed ICPs;
  - symmetric mean nearest-neighbour distance, in cm at the scan's scale;
  - the board is the flat mean over 36 (episode, object) pairs.
- **Pose boards:**
  - the same scale fix and ICP give a rotation and anchor that convert every pose of that object into the scan's body
    frame;
  - one rigid world transform from frame 0 then aligns the scene.
  - So a mesh that registers rotated by θ rotates the whole trajectory by θ. The 21 Oct sensitivity study [D]: 5 mm
    inflation gave AUC 0.608 against 0.987 clean, with flips on the boards and sweeper.
- **The scans are surface soups, not solids:**

  | Object | Wall (median) | Extents (cm) | Area (cm²) | RMS radius (cm) |
  |---|---|---|---|---|
  | blue cup | 3.2 mm | 10.3 × 10.0 × 17.2 | 711 | 6.94 |
  | beige cup | 2.4 mm | 10.4 × 11.1 × 16.9 | 759 | 6.79 |
  | white pot | 3.9 mm | 13.2 × 18.9 × 35.7 | 1231 | 9.81 |
  | lid | 1.8 mm | 4.7 × 18.8 × 19.0 | 784 | 6.74 |
  | pitcher | 2.2 mm | 14.1 × 27.2 × 41.5 | 2236 | 11.08 |
  | dust pan | 2.7 mm | 4.5 × 17.0 × 17.8 | 491 | 6.37 |
  | rack | 2.5 mm | 11.7 × 17.5 × 51.0 | 3435 | 15.69 |
  | sweeper | 13 mm | 4.8 × 11.4 × 14.2 | 264 | 4.77 |
  | board 1 | 7.5 mm | 2.7 × 13.9 × 22.7 | 608 | 7.89 |
  | board 2 | 9.1 mm | 2.6 × 13.9 × 22.7 | 628 | 7.86 |

  Wall = distance from a surface point inward to the next surface along the normal (`scripts/scan_stats.py`) [D].
  Mocap markers (grey spheres on stems) are part of every scan.
- **Partial scans** (`scripts/area_prof.py`, blue cup): about 50 cm² of surface per cm of height near the rim (inner
  and outer wall), but only about 25 cm² per cm in the lower half (outer wall only), plus about 146 cm² at the base
  (a recessed foot) [D].

## 2. What was tried before (full ledger: `ledger-of-past-mesh-work.md`)
| Family | What was done | Best result [D] | Status |
|---|---|---|---|
| TSDF fusion (v0–v3) | 4 mm voxels, 12 mm truncation, binary solid + blur, table/hand/other carving, closing, `below_carve`, `flatten_base`, multi-episode | weighted 0.491 (v2 = v3) | **submitted** (mostly 21 Oct v1 files) |
| Observation-first v5 / Design O | 2 mm, 4/6/12 mm truncation cascade, continuous marching cubes | dust pan 0.251, lid 0.37, board 1 0.19, but pot 0.73, rack 0.82 | only the beige cup used (0.730) |
| Interaction carving (submitted mesh) | slots, min-cut, nests | neutral or worse; new flips | rejected; carving in the **collision copy only** helps the simulator |
| Primitives (approach 2) | lathe fitted to library mesh; box-with-slot boards | cup 0.307, pot 0.319, beige 0.292; board 1 0.177 (board 2: 2/6 flips) | **parked** (organiser question), never submitted |
| Physics-based | support fill, arc foot, stability certificate, sim-only carves | simulator gains (eval 20 0.29 → 0.89, eval 25 0.71 → 0.79) | adopted for the **simulator copy**; CD-O unchanged |
| Spoon | parametric template from stereo measurements | ≈ 0.18 inferred (no scan) | submitted |
| Generative (SAM 3D, TRELLIS, Hunyuan3D), video generation, 2DGS, BundleSDF | literature notes only | — | **never run** |

Lessons carried forward:
- judge CD-O **and** registration (ADD, flips) together;
- per-object choices tuned on the public scans leak the scans into the eval meshes;
- one good single episode beat multi-episode fusion on 6/6 objects;
- tracks templated on the scans make meshes non-compliant (library v1–v4).

## 3. Literature map (full reports with sources: `lit/`)
| Family | Accuracy evidence | Fit for our data | Licence / compute |
|---|---|---|---|
| Image-to-3D (SAM 3D Objects, TRELLIS(.2), Hunyuan3D 2.x, TripoSG, Step1X-3D) | SA-3DAO real images: SAM 3D 0.040, TripoSG 0.084, Hunyuan3D-2.0 0.087, TRELLIS 0.090 (normalised Chamfer ≈ 2–4 % of size) [L] | complete, thin-walled, handles and slots; unseen parts invented; scale and frame arbitrary | SAM licence (gated); MIT (TRELLIS, TripoSG); Apache (Step1X); Tencent community licence (excludes EU/UK/KR); 24–40 GB GPU |
| Multi-view / pose-conditioned generation (Pixal3D, MV-SAM3D, Hunyuan3D-2mv) | Toys4K, 4 views: Pixal3D CD 4.7e-4 vs TRELLIS 18.4e-4 [L] | can take our posed crops, so output lands in our frame | MIT (Pixal3D); ≥ 24 GB |
| Generate then fit (AGILE, MagicHOI, RecGen3D, GenPC) | HO3D: AGILE 0.27 cm² vs HOLD 1.11 [L]; GenPC real Redwood 1.74 vs 2.72 [L] | the direct route to ≈ 1 %: keep observed geometry, generate the rest | mostly MIT or research-only; we can write the fit ourselves (Sim(3) + non-rigid ICP to `obs_points`) |
| Video / novel-view generation (SV3D, SV4D, GEN3C, ViewCrafter, Zero123++) | no evidence it beats native 3-D generators on geometry; Cue3D ranks native ahead [L] | at most hand removal or extra views | several are non-commercial |
| HOI video reconstruction (BundleSDF, HOLD, MagicHOI, 6DOPE-GS) | RGB-D: BundleSDF 0.57 cm, 6DOPE-GS 0.41 cm on HO3D, but visible faces only [L] | close to our setup; scored differently | BundleSDF NVIDIA non-commercial; GPU |
| Better fusion (directional TSDF, Voxblox weights, pose refinement, envelope Poisson) | directional TSDF cuts thin-structure RMSE 2–3× [L]; joint pose refinement F-score 0.868 → 0.924 [L] | fixes our thick walls at the source; CPU | permissive |
| Gaussian / neural surfaces (2DGS, PGSR, GOF, MILo, NeuS2) | DTU 0.5–0.8 mm on static, calibrated scenes [L] | need many clean views; hands and motion hurt | gsplat Apache; most others non-commercial |
| Primitives and CAD (superquadrics, SuperDec, CAD-Recode, cadrille, MeshCoder) | 1.7–2.2 % of size on ShapeNet; CAD models IoU ≈ 68 % on real scans [L] | too coarse alone; useful per family (lathe, extrusion, generalized cylinder) | MIT / Apache |
| Retrieval + deformation (Objaverse, neural cages) | about half the Chamfer of retrieval alone [L] | category-level only; rules grey zone ("own reconstruction") | per-asset licences |
| Physics priors (PhysComp, Atlas3D, Vysics, contact) | stability up, accuracy gains only where contact implies hidden geometry (Vysics 2.98 → 1.45 cm) [L] | table contact fixes unseen undersides | permissive |

## 4. Measured today (CPU) [D]
Benchmark: `scripts/mesh_metric.py`, the 22 Oct metric. It runs the kit's CD-O at the scorer's eval seeds and the
kit's registration (ADD offset, flips) on ≥ 6 seeds. Library_v3 reproduces the earlier numbers exactly.

Observed points (`scripts/obs_points.py` → `scripts/obs_diag.py`; perc2m own-mesh tracks, FoundationStereo depth):

| Object | Episode | Points kept | Median / p90 distance to scan | Scan surface within 3 mm / 6 mm of an observation |
|---|---|---|---|---|
| lid | 2 | 1.49 M | **0.85** / 2.6 mm | 83 % / 96 % |
| blue cup | 22 | 1.11 M | **0.89** / 3.4 mm | 59 % / 67 % |
| blue cup | 21 | 1.20 M | 0.96 / 4.6 mm | 64 % / 72 % |
| blue cup | 21 + 22 | 2.31 M | 0.92 / 3.9 mm | 64 % / 71 % (no coverage gain) |
| dust pan | 39 | 1.96 M | 1.07 / 3.3 mm | **90 %** / 97 % |
| board 2 | 23 | 0.77 M | 1.29 / 4.9 mm | 84 % / 91 % |
| pitcher | 22 | 5.64 M | 1.30 / 6.1 mm | 61 % / 68 % |
| sweeper | 31 | 0.50 M | 1.37 / 3.9 mm | 68 % / 82 % |
| board 1 | 23 | 0.04 M | 1.71 / 4.6 mm | 16 % / 30 % (ep23 track has the known board-identity problem) |
| rack | 26 | 0.98 M | 1.88 / 6.5 mm | **28 %** / 38 % (static, fins hide each other) |
| pot | 41 | 4.56 M | 1.89 / 6.6 mm | 88 % / 95 % |

Read: for most objects our own observations already cover 60–90 % of the scan at about 1 mm median. The rack and
board 1 (track problem) are the exceptions. The beige cup was skipped: the ep11 track is wrong at frame 0 (known G1
failure).

Thin-walled lathe from observed points (`scripts/lathe_obs.py`). CD-O at eval seeds; ADD = static registration offset:

| Mesh | Blue cup CD-O / ADD / flips | Pot CD-O / ADD / flips |
|---|---|---|
| library_v3 (submitted) | 0.523 / 10.0 mm / 0 of 7 | 0.437 / 6.7 / 0 of 8 |
| approach-2 lathe on library mesh (25 Oct) | 0.307 / 9.1 / 0 | 0.319 / 4.7 / 0 |
| obs lathe, solid (no cavity) | 0.493 / 4.0 / 0 | – |
| obs lathe, hollow, body only | **0.392** / 7.3 / 0 | 1.168 / 81 / **2 of 8** (symmetric body flips) |
| obs lathe, hollow + observed appendages (voxel splat), ep22 | 0.364 / 4.7 / 0 | 0.468 / 5.4 / 0 |
| same, **ep21** | **0.291** / **4.1** / 0 | – |
| same, ep21 + ep22 points merged | 0.396 / 5.2 / 0 | – |
| obs lathe, hollow + library appendages | 0.420 / 7.8 / 0 | **0.413** / 4.7 / 0 |
| screened Poisson on oriented points (trim 3–10 mm) | 0.96–1.11 | – |

**Episode choice dominates, and fusion hurts again** [D]: one episode gives 0.291, the other 0.364, and merged 0.396.
This matches the 22 Oct finding (single episode beat fusion on 6/6 objects).

**A GT-free selector works here** (`scripts/obs_fidelity.py`) [M score, D check]. Each candidate mesh is scored by
how well it explains *all* observed points: trimmed mean observed→mesh distance plus mesh→observed distance inside
the observed region.
- ranking: ep21 lathe 4.08 mm < merged 4.23 < ep22 lathe 5.79 < library_v3 5.86 < ep22 lathe without markers 6.63;
- it picks the CD-O winner (0.291);
- Spearman with CD-O is 0.5 on these 5 candidates (small sample).

Axis estimation needed three ideas. All are GT-free and kept in the code:
- the line-complex fit alone locks onto the pot's long handle;
- a bowl fits every axis through its centre;
- so candidates from the line complex, PCA and the opening direction are scored by rotational self-consistency.

## 5. Where our 0.40 cm comes from (diagnosis)
1. **Thick walls** (12–20 mm vs 2–4 mm): inner surfaces sit 5–15 mm off. The mesher's binary threshold plus blur is
   the cause [D, ledger].
2. **Unobserved regions closed wrongly:** slabs, cones, and filled cavities (blue cup lower 37 % solid).
3. **Area distribution versus a partial scan:** extra deep inner walls, missing feet and missing markers shift the
   scorer's RMS-radius scale. That alone is worth ≈ 0.07 cm on the blue-cup lathe [D].
4. **Thin structures** (rack fins, slots, handles) are lost or inflated at 4 mm.
5. **The spoon** (10/36 pairs): a template with unmeasured real-shape error.

## 6. Plan, ranked (owner's go-ahead needed for every GPU item)
| # | Step | Where / cost | Expected | Falsified if |
|---|---|---|---|---|
| P1 | **Generative probe**: SAM 3D Objects, TRELLIS.2 and Hunyuan3D-2.1 on our 9 public crops (2 crops × 2 seeds each), scored raw (CD-O is similarity-invariant) | 1 GPU (A100 80 GB ≈ $0.8/h or PRO 6000 ≈ $1.7/h), ≈ 3–4 h, **≈ $4–8**, ceiling $12 | the best model ≤ 0.35 cm on ≥ 5 of 9 objects [E] | median over objects not better than library_v3 |
| P2 | **Generate-then-fit**: Sim(3) multi-start ICP of the generated mesh to `obs_points` (outer surfaces), then non-rigid ICP (trimesh `nricp_amberg`), observed regions pulled to the points, unseen regions kept from the generator | CPU | 0.15–0.25 cm on cups, pot, lid, dust pan, boards [E] | no gain over P1 raw, or more flips |
| P3 | **GT-free selector** per object among {TSDF, family fit, generative fit}: one-sided observed→mesh distance, silhouette IoU on held-out frames, registration self-ambiguity (`mesh_gates.py`) | CPU | picks the best or second-best candidate on ≥ 7 of 9 public objects | Spearman with CD-O < 0.5 |
| P4 | **Observation-first family fits** (no GPU): lathe per episode (cups, pot, lid) with the episode chosen by `obs_fidelity.py` (not merged), handle as a swept tube, board extrusion with slot | CPU, ≈ 1 day | cup ≈ 0.29 (measured on one cup), pot ≤ 0.32, boards ≤ 0.18 [E] | not better than the approach-2 lathe on ≥ 2 of 3 lathe objects |
| P5 | **Thin-wall fusion** for everything else (rack, sweeper, pitcher): directional TSDF (6 view bins), 1.5–2 mm voxels, 4–5 mm truncation, sub-voxel marching cubes, table-contact base | CPU | rack 0.55 → ≤ 0.40 [E] | walls stay ≥ 6 mm |
| P6 | **Spoon**: generative fit from eval crops (spoon has no scan; check against our stereo points and silhouettes only), or a generalized-cylinder fit to masks + depth | P1/P2 infrastructure | registration stable (0 flips over 40 seeds) and observed→mesh p90 ≤ 3 mm | flips or residual worse than template |
| P7 | Re-track public episodes with the new meshes (perception AUC must not drop), then rebuild the eval meshes and the 20 eval policies' packs | GPU, part of the normal pack cost | CD-O board ≈ 0.40 → 0.20–0.28 cm [E]; AUC +0.00–0.02 from smaller registration offsets [E] | perception AUC on public twins drops > 0.01 |

What not to do, from the evidence:
- carve the **submitted** mesh for interactions; keep carving in the collision copy;
- use raw Poisson;
- tune per object on the public scans;
- rely on video or novel-view generation for geometry.

## 7. Owner actions
1. **Permission to run third-party model code** (Hunyuan3D-2, TRELLIS.2, SAM 3D Objects) in this cloud session or on a
   Vast box. The cloud sandbox blocked `gen_hy3d.py` ("code from external").
2. **SAM 3D Objects access.** Request access at https://huggingface.co/facebook/sam-3d-objects and let the
   fine-grained HF token read gated repos (the token gets HTTP 403 now).
3. **Go-ahead and budget for P1**: ≈ $4–8, ceiling $12. Another session is running eval-10 boxes now, so the two
   should not share a box.
4. **Licence choice:** Hunyuan3D's Tencent community licence excludes the EU, UK and South Korea. TRELLIS.2 and
   TripoSG are MIT, Step1X-3D is Apache-2.0, and SAM 3D uses the SAM licence. Winners must release code under Apache-2.0
   (models may keep their own licence).
5. **Rules question, still unsent** (`docs/organiser-email-draft-2026-10-22.md`): are generated or fitted meshes "our
   own reconstruction" for CD-O? The FAQ only forbids the public scans.

## Files
- `ledger-of-past-mesh-work.md`: every earlier mesh experiment with numbers and sources.
- `lit/generative.md`, `lit/video-physics.md`, `lit/primitives-cad.md`: the three literature reviews.
- `scripts/`:
  - `mesh_metric.py`: kit CD-O + registration at eval seeds, eval weights (`MESH_SCR` sets the data root).
  - `cdo_decomp.py`: CD-O split into directions, plus metric-scale CD.
  - `obs_points.py`: observed object-frame points.
  - `obs_fidelity.py`: GT-free mesh score against the observations (selector).
  - `obs_diag.py`, `area_prof.py`, `scan_stats.py`, `prof_plot2.py`: [D] diagnostics.
  - `lathe_obs.py`: thin-walled lathe from observations.
  - `hybrid.py`: lathe + appendages.
  - `poisson_obs.py`: negative result.
  - `crops.py`: GT-free colour crops for generators.
  - `gen_hy3d.py`: Hunyuan3D-2mini runner, blocked here.
- `results/`: JSONL scores, manifests, crop choices. Paths inside point at the session scratchpad.
- `figures/`: crop montage, profile plot, pot axis candidates.

## 8. The eval meshes (added 26 Oct, ~18:30 UTC)
Interactive page: https://claude.ai/artifact/TSEF4dCCSRdErBcfCPR2Ex (private to the owner). Source: `eval-view/`. It
shows:
- a 3-D viewer of every submitted eval mesh after the kit's own 4096-face decimation (what Kaggle receives), with a
  section cut;
- the new-method meshes on public episodes beside the scan;
- one eval colour frame per (episode, object) with our mesh projected by our eval track;
- a review panel's verdicts.

**New-method meshes for eval cannot be built yet** [M]:
- The store has no eval depth cache, only `cache/depth/public` (work log line 3913).
- Only frame 0 survives, in `det_f0.npz`. A lathe from frame 0 alone was tested on public data first (`obs_f0.py`)
  [D]:
  - points are accurate (median 0.7–1.5 mm) but cover only 24–30 % of a cup or pot;
  - the lathes fail: CD-O 1.1–1.3 cm, 7/7 flips on both cups.
  - So it was not run on eval.
- The fix is `ops/jobs/eval_perc.sh` on one GPU: it pushes eval depth to the store, ≈ 4 min per episode, ≈ $2–4 for
  the 11 episodes with a cup, pot or lid, or all 20. After that, `obs_points.py` → `lathe_obs.py` → `obs_fidelity.py`
  run on CPU.

**Defects found in the submitted eval meshes** (GT-free unless marked):
- **Open base on the white pot** (6 eval pairs):
  - the mesh is a closed thick ring with a hole ≈ 4–5 cm across in the middle of its base;
  - 6 of 9 rays through its centre along its axis hit nothing, while the scan has 0 of 9 [D];
  - figure: `figures/pot_profile_lib_vs_scan.png`.
  - Likely from the below-table carving or closing of the never-seen underside (hypothesis). It may also affect the
    simulator copy; not checked.
- **Beige cup, eval 10 (library_v3):** the base is entirely open (9 of 9 rays). The ledger already calls it an open
  shell. Eval 8 uses the v3x rebuild, which is closed.
- **Water pitcher** (eval 20): see-through holes (3 of 9 rays along one axis; scan 0), matching the "twisted shell" in
  the forensics.
- Thick walls on pot, lid, dust pan and cups, as measured before.

Review panel (workflow `wf_c69f9d10-f06`):
- one reviewer per eval pair compares the raw frame, the projected mesh and the 3-D renders;
- a skeptic re-checks every flagged issue;
- a final step writes per-object verdicts.

Results: `results/eval_review.json` (68 agents, 0 errors). Shown on the page as notes under each image and a priority
table.
- **Tracking is good:** all 36 meshes land on the right object, place and size. Possible small pose offsets only on
  eval 10 and 32 (blue cup) and eval 30 (sweeper).
- **Meshes, in priority order** (visual, GT-free):

  | # | Object | Pairs | Verdict | Main issues |
  |---|---|---|---|---|
  | 1 | blue cup | 5 | poor | side-wall hole near the open end; not round |
  | 2 | white pot | 6 | usable with defects | floor mostly missing; wall hole near the rim; filled handle hole |
  | 3 | dish rack | 5 | poor | tray floor mostly missing; fused pegs |
  | 4 | beige cup | 2 | poor | both versions broken: two pieces, no opening |
  | 5 | pitcher | 1 | usable with defects | wall holes |
  | 6 | dust pan | 2 | usable with defects | terraced scoop |
  | 7 | sweeper | 2 | usable with defects | lumpy, uneven ring handle |
  | 8 | board 1 | 1 | usable with defects | spurious hole; no slot |
  | 9 | lid | 1 | usable with defects | rim notch; plate hole |
  | 10 | board 2 | 1 | usable with defects | no slot |
  | 11 | spoon | 10 | good | small neck taper only |
- The order matches the measured lathe gain (cups first). The lathe's effect on the pot, rack and beige cup is still
  a hypothesis until measured on public episodes.

## 9. Kit-of-parts (primitive-assembly) meshes (added 27 Oct)
Owner: "Okay do that" (build meshes from primitives fitted to our own points). CPU only, $0. Rules were pre-registered
in the work log before any result.

**Method** [M]. Each object is a small assembly of parametric parts, fitted to our observed stereo points
(`obs_points.py`, on our own tracks; no GT). Parts are unioned with manifold3d into one watertight mesh.
- `scripts/prim_potlid.py`:
  - pot: thin-walled lathe with a closed floor, wall thickness measured from inner and outer points; flat bar handle;
    marker balls;
  - lid: domed sheet, swept arch strap and marker balls.
- `scripts/prim_boards.py`: board = extruded occupancy outline, thickness from points, marker balls.
- `scripts/prim_rack.py`:
  - tray = rounded-rectangle block minus a sloped basin;
  - cup-holder tube;
  - 2 × 6 cone pegs;
  - marker balls;
  - optional joint fit of the consistent episodes.

Selection is GT-free, by the lowest `obs_fidelity.py` over all of the object's episodes. Each selected mesh was then
scored once against the public scan [D].

| Object (eval pairs) | Selected mesh | CD-O cm, library_v3 → new | ADD mm, lib → new | Flips | Verdict |
|---|---|---|---|---|---|
| white pot (6) | ep41 fit | 0.437 → **0.342** | 6.7 → 3.05 | 0/8 | PASS |
| pot lid (1) | ep2 fit, T_LID 2.5 | 0.421 → **0.220** | 8.1 → 4.46 | 0/6 | PASS at all thicknesses |
| dish rack (5) | joint 12/13/27, lean, T_WALL 2.5 | 0.555 → **0.456** | 6.0 → 5.37 | 0/7 | PASS at all thicknesses |
| board 1 (1) | ep24 occ_d2 | 0.222 → 0.189 | 2.4 → 3.31 | 1/6 | FAIL (flip) |
| board 2 (1) | ep23 occ_d2 | 0.216 → 0.229 | 3.6 → 78.7 | 3/6 | FAIL (wrong board's track) |

**Integrity.**
- The first run's lid and rack wall thicknesses (2.5 mm) and the rack's upright cup holder were informed by scan
  measurements that my workflow brief passed to the builders. An auditor found this.
- A pre-registered clean-up round re-ran both over a generic range of thickness (1.5 / 2.5 / 4.0 mm) and both cup-lean
  settings.
- Our points cannot measure these thicknesses: the lid is seen only from above and the rack floor never. So the rule
  was "pass at every grid value".
- Both passed everywhere:
  - lid worst case 0.224 / 5.06;
  - rack worst case 0.458 / 6.23.
- The GT-free fidelity preferred the original leaning cup holder at every thickness. That choice also scores better
  on ADD.
- Scan scorings: pot 32, lid 4 + 6, rack 12 + 6, boards 16, plus 6 dev bug checks, all logged.
- Independent audits re-ran selection and scoring and matched exactly (`results/prim/workflow-result.json`).

**Known defects** (visual, GT-free):
- pot: one spurious ball mid-handle, no handle hole (not seen in our occupancy), 4 of 5 balls float;
- lid: one ball floats;
- rack: straight-walled cup holder, no right-end ribs or marker stems;
- boards: no slot, notches or correct marker side.

The boards need identity-safe tracks (the ep23 board 2 track looks like board 1 rotated 180°) and a slot detector.
Both are hypotheses to test before another board round.

**What it would change for eval** [E]:
- The submitted eval meshes are `library_v3`, which is built from **public** episodes and reused for eval. These
  meshes are built the same way and lie in the same object frame (median 2–4 mm from the library meshes, without
  registration).
- So they **do not need eval depth**.
- If the hidden scans match the public ones, swapping pot, lid and rack (12 of 36 CD-O pairs) moves our CD-O from
  0.402 to about **0.367 cm** [E].
- The AUC effect through the better registration (lower ADD) is unmeasured.
- Open question for the owner: `ops/jobs/submit_pack.sh` packs the file the simulator built its bodies from.
  Swapping only the packed mesh (frames match) is a $0 pack change. Swapping the simulator copy too means
  re-running the affected eval episodes on GPU.

Files: `results/prim/` (candidates, fidelity, scores, selections, meshes, `clean/` for the clean-up round),
`scripts/prim_*.py`, `scripts/tmeas_lid.py` (the failed GT-free thickness measurement).
