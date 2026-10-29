# Contact-anchored retargeting for V2D Track 3: literature review (2023–2026) and a concrete algorithm

Date: 2026-10-21. Read-only research; nothing in the repository was changed or run.

**Labels.** **[F]** = fact from a primary source (paper text, author code or config), with the arXiv id or file.
**[M]** = measured in this repository (from `STATUS.md` or `docs/work-log.md`). **[I]** = my inference or hypothesis.
Each hypothesis names the experiment that would falsify it. All paper numbers are on *their* datasets (mostly mocap
DexYCB, OakInk2, ARCTIC, TACO, GRAB). None of them is a measurement on our episodes.

**Sources read in full text** (arXiv HTML): 2609.24093, 2609.28660, 2610.26762, 2608.07045, 2610.17572, 2610.15769,
2606.19333, 2610.06331, 2607.00033, 2610.01849, 2610.14379, 2511.09484, 2509.26633, 2402.04820, 2610.10855,
2610.18822, 2606.16272, 2607.11874, 2610.24392, 2609.01938, 2506.09384, 2505.24853, 2503.21860, 2503.23120.
Abstracts only for the rest.
**Code opened** (shallow clones in scratchpad `repos/`): DexForge (`wmz1226/DexForge`), Do as I Do
(`malik-group/do-as-i-do`), SPIDER (`facebookresearch/spider`), PyRoki (`chungmin99/pyroki`), mink
(`kevinzakka/mink`), REGRIND (`yunhaif/regrind`). Three repos hold only a README: real2sim2real, morphometric and
C2Dex_code.
**Robot geometry:** taken from the local `video_to_data` checkout (Sharpa primitive URDF and MJCF).

---

## 0. Executive summary

1. **[F] Contact-structure transfer is now the dominant recipe.** It works better than fingertip-position or
   joint-angle transfer, and the evidence is consistent across groups:
   - Morphometric Imitation (2609.28660) uses the same Sharpa hand. Contact- and morphology-aware references raised
     residual-RL success from 56.5 % to 91.8 % against the best baseline reference.
   - DexOAK (2610.26762) uses the same ADD-AUC metric as our scorer. On ARCTIC with DexMachina RL, object-aware
     references raised ADD-AUC from 83.4 to 88.9 (optimizer alone) and to 91.3 (with the learned, contact-loss
     fine-tuned network).
   - C2Dex (2608.07045): removing cross-frame contact consolidation dropped end-to-end success from 57.8 % to 17.8 %.
   - Gen2Dex (2610.24392): resetting RL to raw (penetrating) reference poses solved 0 of 10 tasks; physically
     validated reset states solved 9 of 10.
2. **[F] Kinematic contact snapping is necessary but not sufficient.** Four results show it:
   - EgoCPT (2610.17572, Sharpa, noisy egocentric hands): contact and pose refinement *without* force allocation did
     not beat vanilla retargeting (1/10 vs 2/10 after RL). The full method with wrench-feasibility checks got 10/10.
   - OmniHOI (2610.10855): in open-loop replay, contact refinement *lowered* apparent success. Most of the lost
     successes were false: fingers had passed through the object and dragged it along. Physics-in-the-loop
     refinement then raised success from 9–29 % to 85–89 % (Sharpa 89 %).
   - Open-loop replays of contact-anchored kinematic references stay weak:
     - 2609.24093: 0.5–50 % success by hand, vs 76.5–82.5 % after residual RL;
     - SPIDER: kinematic replay scores ADD-AUC 11–24, vs 49–58 after physics refinement.
   - OATH (2610.14379) states it directly: tracking the kinematic reference position alone does not induce contact
     forces.
3. **[F] Noise is the main hazard for video inputs.**
   - Laplacian/interaction-mesh retargeters keep human "virtual contacts" (fingers that hover near the surface) as
     gaps. TopoRetarget lists this as its limitation.
   - CHORD's contact-wrench reward collapses at about 25 mm / 25° contact noise. Its force-closure fallback stays
     flat.
   - Methods built for video therefore aggregate contacts in the object frame over stable segments (C2Dex, DexForge,
     Hand2Robot, EgoMatrix). They also filter short or drifting contacts (SPIDER) and use one-sided distance rewards
     (FlashDexRetarget).
4. **[I] Recommended algorithm** (details in §7), segment-wise contact-anchored grasp retargeting:
   - Detect human contacts with phalanx capsules against our object SDFs.
   - Consolidate them in the object frame per stable segment, then check that the contact set (both hands plus table)
     can supply the object wrench the tracked trajectory demands.
   - Solve one collision-free Sharpa grasp per segment on robot geometry: pads on faces, correct side, palm and wrist
     free, primitive capsule radii.
   - Carry it rigidly with the object, interpolate transitions with collision checks, and recompute the FlashCHORD
     contact labels from the robot.
   - Verify on CPU: the per-frame pop map, a pinned-object "settle", then stiff-wrist no-policy replays with and
     without a 2–4 mm grip preload, checking for interlock.
   - Only then spend GPU on RL.

---

## 1. Contact estimation from video

### 1.1 Classic hand-object (HOI) refinement with contact and penetration terms

| Method | What it does | Relevance to us |
|---|---|---|
| ContactOpt, CVPR 2021, arXiv 2104.07267 | [F] A network (DeepContact) predicts target contact maps on hand and object meshes; a differentiable contact model optimizes the MANO pose to reach them. "Our contact model encourages mesh interpenetration to approximate deformable soft tissue." | [I] A useful reminder that some interpenetration is physically meaningful (it stands in for grip force). Needs a MANO mesh, which we do not have. |
| GraspTTA, ICCV 2021, arXiv 2104.03304 | [F] Hand–object contact consistency (hand contact points near the surface, common object contact regions touched), plus self-supervised test-time adaptation. | Static grasps only. |
| TOCH, ECCV 2022, arXiv 2205.07982 | [F] Object-centric spatio-temporal correspondence fields; a temporal denoising autoencoder corrects noisy RGB/RGB-D HOI sequences, including before and after contact. | [I] The right idea (object-frame, temporal) but needs a trained prior on MANO. |
| HOLD, CVPR 2024, arXiv 2311.18448, code `zc-alexfan/hold` | [F] Category-agnostic implicit reconstruction of hand plus object from monocular video, with hand–object constraints. | Monocular reconstruction; we already have better geometry (stereo TSDF, AUC about 0.9). |
| DiffHOI, ICCV 2023, arXiv 2309.05663 | [F] Per-video neural optimization with a diffusion prior on object renderings conditioned on the hand. | Same remark. |
| G-HOP, CVPR 2024, arXiv 2404.12383 | [F] A diffusion hand–object prior (skeletal distance field plus object SDF) used for reconstruction and grasp synthesis. | [I] Could act as a plausibility prior; heavy. |
| HORT, ICCV 2025, arXiv 2503.21313 | [F] A transformer reconstructs hand-held object point clouds from one image. | Not needed: we have meshes. |

### 1.2 2025–2026 video-to-robot pipelines that estimate contact

- **C2Dex** (arXiv 2608.07045, submitted to RA-L).
  - [F] Pipeline: Dyn-HaMR hands, SAM 3D object, ProxyPose tracking.
  - [F] Contact candidates: silhouette overlap of hand and object, ray-cast onto the object, filtered by
    opposite-normal compatibility $-n_h^\top n_o>\gamma_n$.
  - [F] Consolidation: points are mapped to the canonical object frame and the sequence is split into segments where
    articulation and the relative pose change little. Each hand vertex's points are clustered with DBSCAN, and the
    medoid of the dominant cluster is the stable contact.
  - [F] The stable contacts drive both the human HOI optimization ($\lambda_c=8$, $\lambda_{sdf}=0.01$,
    $\lambda_{reg}=10$) and robot retargeting (Laplacian 500, contact $2\times10^4$, penetration $10^5$, smooth 1;
    Adam, 3000 iterations, lr 0.02), followed by ManipTrans residual RL.
  - [F] Ablation: removing cross-frame contact consistency drops end-to-end success from 57.8 % to 17.8 % (DexYCB) and
    from 26.7 % to 10.0 % (TACO).
- **EgoCPT** (arXiv 2610.17572).
  - [F] Inputs: egocentric RGB plus metric 3D hand skeletons (EgoDex/Vision Pro, i.e. keypoints, much like our
    MediaPipe joints lifted with stereo). Robot: Sharpa.
  - [F] Object via FoundationPose.
  - [F] Treats human contacts as *uncertain* and object motion as the goal. It samples contact candidates near the
    robot finger endpoints, refines pose to reach them under joint limits and penetration $d\ge-\epsilon$, smooths
    with bounded corrections, then runs force allocation, $\min_\lambda\|G\lambda-w^{req}\|^2+\rho\|\lambda\|^2$,
    $\lambda\ge0$, $\|f_i\|\le f^{max}$.
  - [F] $G$ includes a support disk under the object for table contact; $w^{req}$ comes from Newton–Euler on the
    reference object motion. Candidates are kept only if the wrench residual is below a threshold.
  - [F] Results: EgoDex 67.3 % (CHORD 55.8 %, Do as I Do 46.2 %, SPIDER 15.4 %); "sweep dustpan" 54.5 %. TACO 92 %.
  - [F] With 0/1/2 cm hand offset the reference penetration stays 0.05–0.08 mm (vanilla 4.4–5.3 mm). Success after RL
    falls to 100 / 87 / 73 %.
- **Hand2Robot** (arXiv 2610.15769).
  - [F] Object-centric 4D hand refinement: staged 2D alignment, ray-based contacts, SDF penetration.
  - [F] Temporal contact stabilization in the object frame: a stop-gradient anchor (mean of adjacent ray hits) with a
    Charbonnier loss. Then GeoRT retargeting.
- **EgoMatrix** (arXiv 2610.18822).
  - [F] Contact frames from HACO vertex probabilities fused with mask proximity, $s=(0.65H+0.35P)P$. Median filter
    5 frames, thresholds 0.38 / 0.68, at least 3 confident frames per interval, gaps up to 8 frames merged.
  - [F] Contacts are stabilized in the canonical object frame as in C2Dex, and opposition contacts (pad/palm/side, from
    the GRASP taxonomy) are added when the stable patches give no opposing support.
  - [F] End-to-end 54.8 % vs 14.5 % for the best baseline.
- **OmniHOI** (arXiv 2610.10855).
  - [F] Occlusion-order loss on rendered hand/object depth.
  - [F] Contact–penetration loss: palmar samples attracted with $\frac{d}{\sigma_c}\log(1+\frac{d}{\sigma_c})$,
    full-surface samples repelled; $\lambda_c=66$, $\lambda_p=7\times10^5$, $d_0=0.001\ell$, $\sigma=0.5\ell$, where
    $\ell$ is the distal phalanx length.
  - [F] **Finger-crossing repair for thin objects**: "signed distance saturates on thin objects". Crossings are
    detected by parity along each finger polyline, with 2 mm clearance.
- **Do as I Do** (arXiv 2606.19333, code released, Sharpa).
  - [F] HaWoR/WiLoR hands plus MoGe depth, then mink IK (fingers 10, wrist position 0.3, wrist orientation 3.0), then
    MPPI-style annealed sampling in MuJoCo Warp.
  - [F] The noted failure: in Do as I Do as evaluated, a grasp is declared whenever the hand–object distance is below
    10 cm (EgoCPT's analysis).
- **DexForge** (arXiv 2610.06331, code released).
  - [F] Stable contacts from MANO distal-pad vertices: within ±10 mm of the surface, runs of at least 8 frames at
    30 Hz, intervals where at least 80 % of projected points lie within 8 mm of their medoid; the medoid is the anchor.
  - [F] The released `contactaware.yaml` repeats these values, plus `contact_run_max_gap: 3` and
    `contact_switch_penalty_frames: 7`.

### 1.3 Dense contact and force estimators (2025–2026)

All entries here are [F] from abstracts, except the final note.
- HACO (NeurIPS 2025, arXiv 2505.11152): dense hand contact on MANO vertices; used by EgoMatrix.
- ContactPrompt (2605.05886): training-free, uses a multimodal LLM.
- EgoPHI (ECCV 2026, 2608.13014): dense contact plus 3D force on hand and object meshes from egocentric RGB.
- HOPE (2608.06192): per-vertex pressure from video.
- RLHND (2610.09455): Cosmos-based tracker with tactile head.
- EPIC-Contact / HOPformer (ECCV 2026, 2606.30598).
- EgoPressure (2409.02224).
- **[I]** All of these need a MANO mesh (HaMeR/WiLoR fit). For us they are second-line evidence; our own stereo depth is
  a more direct cue (§1.5).

### 1.4 Temporal consolidation: the common recipe

[F] The rules used across papers:

| Rule | Value | Source |
|---|---|---|
| Contact gate | 4.5 mm | MMO, mocap GRAB |
| Contact gate | 10 mm | DexMachina, DexForge |
| Contact gate | 15 mm | DexOAK (5–25 mm made "little effect") |
| Contact gate | 18 mm | FlashCHORD `contact_labels.py` (min run 2 frames, object-motion gate; per `docs/research/notes/22`) |
| Minimum duration | 8 frames at 30 Hz | DexForge |
| Minimum duration / drift | $t_{c,min}$ / $d_{c,max}$ | SPIDER (values not printed) |
| Anchor | medoid per stable segment in the object frame | C2Dex, DexForge |
| Anchor | stop-gradient average of adjacent hits | Hand2Robot |
| Gap merge | ≤ 3 frames | DexForge code |
| Gap merge | ≤ 8 frames | EgoMatrix |
| Normal check | opposite-normal test | C2Dex; DexForge (contact-normal residual weight 100α) |

### 1.5 What applies to our perception [I]

We have stereo depth, good object tracks and 21 MediaPipe joints per hand (1–2 cm error). The cheapest
contact evidence, from best to worst:
- (a) Geometric: distances from human phalanx capsules (MCP–PIP, PIP–DIP, DIP–tip, thumb chain, palm quad) to our
  object SDFs, in each object's frame.
- (b) Temporal consolidation per §1.4.
- (c) Image evidence from our own stereo depth: inside the hand mask near the object, compare measured hand depth with
  the object depth rendered from our mesh and track. A gap under about 1 cm along the ray is direct contact evidence that
  does not depend on MediaPipe lifting.
- (d) Physical plausibility: EgoCPT-style wrench feasibility with table support.
- (e) Optionally HACO / EgoPHI after a WiLoR MANO fit.

Our measured human fingertip gaps (0.6–1.8 cm, never inside [M]) mean the gate must be about 15–20 mm, which makes
(b) and (d) essential to reject hovering fingers.

---

## 2. Contact representations for transfer

| Representation | Papers | Strengths / weaknesses | For us |
|---|---|---|---|
| Fingertip positions / vectors | DexPilot (ICRA 2020, 1910.03135), AnyTeleop / dex-retargeting (RSS 2023, 2307.04577), DexMV (ECCV 2022, 2108.05877), E2S | [F] Fast (Position: 1082 frames/s in 2609.24093 Table 5). Hand-only; scaling drives hands into objects. OmniRetarget (2509.26633): "scaling human hand keypoints to the robot's size often drives the robot's hands inside the object". Contact completeness 0.3–5.8 % on OakInk Allegro (DexOAK Table I). | This is our failure mode [M]: 1.2× scaling about the wrist, heavy wrist cost, robot 16–20 mm inside objects. |
| Contact points with normals on the object, per finger region | 2609.24093 (DexGEM, code "coming soon"), DexForge, C2Dex, OATH, DexMachina, CHORD/FlashCHORD (16 slots per MANO link) | [F] 2609.24093: a region name maps to robot surface points; each contact picks "the surface point whose direction from the link center best matches the direction of the corresponding MANO contact"; hinge loss with 1 cm tolerance. Fidelity 14.7 mm, 3.2 % joint-limit violations, jitter 0.53 rad/s, 5.5 frames/s. | Closest to the owner's idea. Needs a contact→robot-region map and normals. |
| Dense contact maps (object or hand surface), part maps, direction maps | GenDexGrasp (ICRA 2023, 2210.00722), ContactGen (ICCV 2023, 2310.03740), CAMS (CVPR 2023), GeoMatch (CoRL 2023, 2312.03864), D(R,O) (ICRA 2025, 2410.01702), Lakshmipathy (ACM TOG 2025, arXiv 2402.04820) | [F] Hand-agnostic. Lakshmipathy transfers contact *areas* by an atlas of local log-map charts (non-isometric shape matching). CPU 4–22 h per result (finite differences). | [I] Too heavy for 21 joints; the region idea survives as "pad patch". |
| Morphology-matched MANO (scaled MANO) | Morphometric Imitation (2609.28660; code "soon") | [F] Scale palm and fingers to the robot (6 ratios), re-pose to recover human contact vertices (τ = 4.5 mm), linear-blend retarget to the robot skeleton, PyRoki IK with JAX surface-sampled hand–table collision. Sharpa: patch distance 9.7 mm, F1 37.2 % (best baseline 10.7 mm / 26.7 %); downstream SR 91.8 % vs 56.5 %. | [I] Needs MANO; the takeaway is "match morphology, then re-solve contacts". |
| Interaction graph / Laplacian | OmniRetarget (2509.26633), DexOAK (2610.26762), TopoRetarget (2606.16272), REGRIND (2607.11874, code), C2Dex | [F] Delaunay tetrahedralization over hand keypoints plus object anchors; matches Laplacian coordinates. DexOAK: 64 anchors, SLSQP, margins 5 mm robot–object (2 mm in the appendix table) and 8 mm self-collision; $v_{max}$ 12 rad/s; no human-to-robot scaling ("retain true scale relative to the object"); 15.5 Hz. Without object anchors, contact completeness drops to 2.8 % and tip error rises to 41.5 mm. TopoRetarget: $\lambda_{IM}=500$, κ = 30, soft penetration τ = 1 mm, hard backstop 3 cm, slack weight $10^5$. **Limitation [F]: "less effective for virtual contacts, where the source finger is intended to interact with the object but does not actually touch".** | [I] Preserves our hovering gaps. Use only as a regularizer beside explicit contact attraction (DexOAK fine-tuning: surface 5, part 10, direction 1, collision 10). |
| Wrench space | CHORD (2607.00033), EgoCPT, DexForge (force-closure term) | [F] Compares the *capability* of contacts to move the object. Robust to contact-location differences, sensitive to normal noise. | Already our reward (FlashCHORD contact-wrench support, CWS); the normals of our contact labels matter. |

---

## 3. Optimization formulations

### 3.1 Terms and defaults reported (all [F])

| Term | Form | Values seen |
|---|---|---|
| Contact attraction | $\sum_i[\max(\|c_i(u)-p_i\|-\delta,0)]^2$ (2609.24093); $\|P_i(q)-T_{obj}\hat a_i\|^2$ (DexForge); $d(r_i)^2$ to the surface, plus $\|r_i-o(k_i)\|^2$ to the part (DexOAK) | δ = 1 cm (2609.24093). DexForge contact weight $100(1+99\alpha)$; anchor guidance 100. PyRoki example: joint-to-contact with 1 cm margin, weight 5. |
| Contact direction / sidedness | DexOAK $\mathcal L_{dir}=1-\cos\theta$ ("separates opposite faces of thin geometry"); DexForge normal residual $r_i(n_{robot}+n_{object})$, weight $100\alpha$ | 2506.09384: a fingertip orientation term (DIP→tip) is needed for correct contact normals |
| Non-penetration (object) | hinge $\max(0,m-\phi)^2$ or hard constraint (SQP) | margins 1 mm (TopoRetarget τ), 2–5 mm (DexOAK), 0 plus 5 mm pre-contact (DexForge); hard 3 cm backstop |
| Self and hand–hand collision | capsule distances | 8 mm (DexOAK); DexForge: finger capsules |
| Table | $\max(0,z_{table}-z_v)^2$ over hand vertices (MMO); hand–table termination in RL | MMO: JAX surface sampling, because "capsule approximations ... proved insufficient for hand-table interactions" |
| Joint limits | bounds or sigmoid reparametrization (DexOAK) | |
| Temporal | $\|q_t-q_{t-1}\|^2$ plus SE(3) terms (DexOAK); $\tau^2\int\|\dot z\|_W^2+\tau^4\int\|\ddot z\|_{WM}^2$ (DexForge) | DexForge: τ = 0.1 s; W = 100 (palm translation), 1 (rotation, joints); M = 32 (palm), 16 (joints) |
| Wrist / palm prior | track the human palm pose | DexForge: palm position 10, rotation 1, **scaled by $(1-0.99\,c_k)$ during contact**, so the wrist is nearly free when anchors are active |
| Force closure / wrench | net-wrench residual of friction-cone edges; SOCP margin | DexForge μ = 0.2, $F_{max}$ = 20, β ∈ [1, 21]; FlashCHORD force-closure term (disabled): 512 directions, 8 edges, μ = 0.1 (`notes/14`) |

[F] 2506.09384 ran real-world ablations of retargeting objectives:
- letting the wrist adjust (instead of copying the human wrist) improves fingertip accuracy;
- a pinch term with rescaled distances matters for pinches;
- a fingertip orientation term matters for contact normals.

### 3.2 Choosing which robot link touches which contact

- [F] Fixed anatomical map, tip to tip (E2S, DexOAK nodes, C2Dex fingers).
- [F] Nearest robot link to each object contact point (DexMachina: γ = 1 cm, $N_c$ = 50, assigned to the nearest
  link centre, averaged).
- [F] Region to surface point by direction (2609.24093) or by a descriptor cost (DexForge "terminal pad": axial
  ∈ [0, 0.5], palmar cosine ≥ 0.75, axial cost 4, azimuth cost 1).
- [F] Sampling validated by wrench feasibility (EgoCPT).
- [F] Learned maps (GeoMatch, D(R,O)).
- [I] For a 21-joint skeleton: map each human phalanx segment to the matching Sharpa link (DP, MP, PP, thumb chain,
  palm). Inside the link, choose the *pad region* (palmar face, distal half). Pick the point whose outward normal is
  most anti-parallel to the object normal at the anchor.

**Sharpa numbers [F]** (`right_sharpa_wave_primitive.urdf` and `right_sharpawave.xml` in the `video_to_data` checkout):

| Link | Collision primitive radius |
|---|---|
| DP capsule | 7.26 mm (thumb DP 8.26) |
| MP | 8.56 mm |
| PP | 9.34 mm |
| Palm capsules | 20.9 mm |

- The MJCF `*_tip_site` sits 26.0 mm along the DP link, on its axis. With the DP capsule centred at 12.9 mm and half
  length 5.6 mm, the site sits at the distal end cap, about 7 mm distal of the pad centre. (Same link frames assumed
  in the URDF and MJCF.)
- **[I] Placing the tip site on the surface makes a fingertip contact, not a pad contact.** For pressing a board flat,
  the pad's closest point should reach the surface instead (§7).

### 3.3 Solvers and runtime

| Solver | Notes |
|---|---|
| pink / pinocchio (E2S) | [F] daqp; 100 iterations per frame |
| mink (MuJoCo differential IK; `kevinzakka/mink`, v1.1.0) | [F] FrameTask, PostureTask; `CollisionAvoidanceLimit` between any geom pair (defaults: minimum distance 5 mm, detection 5 cm). Used by SPIDER and Do as I Do (fingers 10, wrist position 0.3, wrist orientation 3.0). |
| PyRoki / jaxls (IROS 2025, 2505.03728) | [F] Sparse Levenberg–Marquardt on CPU, GPU or TPU; whole-trajectory problems (examples `09/11_hand_retargeting*.py`); 1.4–1.7× faster than cuRobo IK. MMO: 180 frames/s on an RTX 4090 without the IK step. |
| cuRobo (2310.17274) | [F] Collision-free IK > 7000 queries/s on GPU (sphere robots) |
| SLSQP per frame (DexOAK) | [F] 15.5 Hz; the amortized network runs at 108.9 Hz |
| SQP with trust region and collision line search (DexForge, `contactaware`) | [F] Trust 4 mm, 0.05 rad, 0.08 rad per step; ≤ 40 Gauss–Newton SQP iterations; collision checks at 16 substeps between frames |
| Adam (C2Dex) | [F] 3000 iterations |
| 2609.24093 | [F] 5.5 frames/s (3000 iterations) |
| Lakshmipathy | [F] 4–22 h CPU |
| Our draft `pipeline/contact_retarget.py` | [M, code read] scipy TRF with finite differences, ≤ 40 evaluations per frame, Newton FK on CPU, 30 samples per collision shape, trilinear SDF on a ≤ 64³ grid. Untracked and not yet run per `git status`. |

---

## 4. Physics-in-the-loop refinement after kinematic retargeting

| Method | Inputs | Mechanism | Reported gain [F] |
|---|---|---|---|
| SPIDER (2511.09484, `facebookresearch/spider`; Sharpa data released) | Kinematic reference (mink IK), object trajectory and convex-decomposed mesh; contacts from MuJoCo collision detection on kinematic data | Annealed MPPI/CEM: 1024 samples, 32 iterations, horizon 1.6–2 s, knots every 0.1–0.4 s. **Virtual contact guidance**: a constraint $c_k\|{}^{r}p^{o}_k-{}^{r}p^{o,ref}_k\|^2\le\eta_i$ relaxed over iterations (decay 0.5–0.8). A **contact filter** disables contacts shorter than $t_{c,min}$ or drifting more than $d_{c,max}$. A stability check rejects objects that drift > 5 mm in 0.5 s at start. | Kinematic ADD-AUC 11.0 → 48.8 → 56.9 with guidance (OakInk); 24.1 → 56.9 → 57.7 (GigaHands). 6.1 frames/s, 0.4 frames/s with guidance (L40S). |
| Do as I Do (2606.19333, code; Sharpa; MuJoCo Warp) | Noisy reconstructed refs, mink IK | SPIDER-style sampling plus **warmup**: 3 s with the object welded while the hand settles. Also random force perturbations, a transition penalty (missing floor contact at rest / hand contact in hand), penetration penalty 3000 with 5 mm margin, objects dilated 2 mm, a base plate for odd poses. | Success 25 % → 71 % on reconstructions (warmup gives most of it: 66 %); 72 % → 81 % on OakInk2 |
| DexForge (2610.06331, code) | Stable anchors, collision-free kinematic reference | Gradient MPC through a differentiable sim (ComFree-GS), anchor alignment, system identification | "≈35–53 pp" success over "the baseline" (the abstract; Table 3 compares against IK+SPIDER) across 7 hands. Swapping its contact-aware IK into SPIDER also helps. |
| OmniHOI (2610.10855) | Contact-retargeted keyframes | CMA-ES on per-keyframe offsets in MuJoCo, rolling horizon; cost: object pose, contact gap, antagonistic-pair force shortfall, penetration, prior, terminal | Sharpa 89 % (SPIDER 19 %, OmniRetarget 20 %); 19 min per trajectory on an RTX 4090 |
| Grasp-and-Lift (2601.18121) | DexYCB/HO3D | CMA-ES over spline keyframes in a black-box sim | Better replay than ManipTrans (abstract) |
| DexMachina (2505.24853) | Collision-aware kinematic reference ("fixate the object, set joints as PD targets, let the sim resolve collisions, record achieved joints") | RL with decaying virtual object controllers (VOC), contact and motion rewards | [F, via DexOAK/CHORD] ARCTIC ADD-AUC 83.4 (Allegro) |
| 2609.24093 / Morphometric / C2Dex / DexOAK / EgoCPT / Gen2Dex / OATH / REGRIND | Contact-anchored references | Residual RL | See §5 |

**[I] What this means for us.** The simplest physics step is DexMachina's "pinned object settle". It is free on our
CPU FlashCHORD pins and turns a kinematic reference into one the simulator accepts. Do as I Do's warmup addresses our
measured frame-0 problem; the evaluation itself cannot weld objects, so the warmup idea has to live in the reference
lead-in. The sampling refiners (SPIDER, OmniHOI) are the next step if the replays fail.

---

## 5. RL with contact objectives

| Method | How contact enters | Result [F] |
|---|---|---|
| CHORD (2607.00033), which FlashCHORD implements | Object-frame contact points and normals → friction-cone primitive wrenches → support function over sampled directions; reward $\exp(-\|\max(0,(1-\beta)\sigma_h-\sigma_r)\|^2/v-\|\max(0,\sigma_r-(1+\beta)\sigma_h)\|^2/v)$; penalties for missed and unintended contact. Observations: contact positions and force directions in the wrist frame. Residual actions 0.05 m / 0.15 rad; VOC. **Force-closure fallback for video**: $r_{fc}=\frac1B\sum_b\mathbb 1[\sigma_{r,b}>\epsilon]$. | 60 tasks: CWS AUC 0.918, Position-only 0.862, no contact 0.774. Noise study: CWS falls at about 25 mm / 25° contact noise; force closure stays flat (about 0.50–0.57) but "reduces dexterity". |
| FlashDexRetarget (2610.01849; Sharpa; FlashSAC) | **One-sided fingertip distance**: $\epsilon=\max(0,d_{robot}-d^{ref}_{unsigned})$, $r=\frac15\sum\exp(-\epsilon/0.01)$. Unsigned reference distances avoid copying penetrations; the robot may close gaps. Observations: SDF distances plus normals of fingertips and wrist in the wrist frame (128³ grid over a 60 cm cube); 128-point object cloud; 10-frame future encoding; per-hand actor-critic. | Sharpa SR (SPIDER criterion) 86 % vs Do as I Do 64 %, CHORD 50 %; 44 vs 62 vs 3314 GPU-h. Ablation: removing the interaction reward and observations slows learning and lowers success. |
| OATH (2610.14379) | **Per-body contact-error vector** $e_{k,i}=[p_o+R_o\bar g_{k,i}]-[p_i+R_i\bar h_{k,i}]$ (object-frame anchor minus body-frame witness) plus an active mask, as observations | Removing them: Table III shows 89→69 / 53→31 / 46→38 % (train / test / unseen), i.e. −20 / −22 / −8 pp. The text says 21 / 27 / 16; the two disagree. |
| Morphometric (2609.28660) | Reward $r=r_{obj}\cdot r_{contact}$ with $r_{contact}=1-\|N_{goal}-N_{obs}\|/N_{max}$ (contacting-finger count); contact state in observations; termination on table collision | Sharpa: SR 91.8 % with contact; 76.6 % without contact; 54.3 % without object pose |
| DexMachina | Per-link contact positions with validity masks, $\exp(-\beta D)$ | — |
| ManipTrans (2503.21860) | Contact-force reward when mocap hand–object distance < threshold; termination if no fingertip force when there should be | — |
| DexTrack (ICLR 2025, 2502.09614, `Meowuu7/DexTrack`) | Tracking controller with data flywheel; no explicit contact reward | — |
| REGRIND (2607.11874, code) | No contact reward; contact prior carried by the interaction-mesh reference | Sim near 100 % on scissors/screwdriver vs Mink-IK+RL much lower; DexMachina transferred poorly to hardware |
| Gen2Dex (2610.24392) | Physically valid reset-state cache (contact plus SDF optimization, then sim validation) and a backward curriculum | 9/10 tasks vs 5/10 (random valid frames) vs 0/10 (raw resets) vs 2/10 (start only) |

---

## 6. Noisy egocentric inputs and special cases

- **Noise.**
  - [F] EgoCPT: fixed 1–2 cm hand offsets. Kinematic quality survives; RL success drops to 87 % and 73 %.
  - [F] CHORD: contact noise ≥ 25 mm / 25° breaks wrench guidance.
  - [F] FlashDexRetarget: fixed binary thresholds mislabel contacts when reconstruction gaps exceed them; continuous
    one-sided distances avoid this.
  - [I] With 1–2 cm hand–object relative error on the hard episodes [M], use segment-level consolidation, a wrench
    check and, if needed, CHORD's force-closure reward.
- **Thin and flat objects (the board).**
  - [F] DexOAK's direction term targets "opposite faces of thin geometry". OmniHOI's parity-based crossing repair
    exists because SDF gradients vanish once a finger has passed through a plate.
  - [F] ExDex (2503.23120) learns "relocating objects from table centers to edges for direct grasping" with staged
    rewards (motion → pre-grasp → grasp).
  - [F] Zhou & Held (CoRL 2022, 2211.01500): pushing against a wall emerges with RL.
  - [F] HACMan (CoRL 2023, 2305.03942): object-centric contact-location-plus-motion actions.
  - [F] CORN (ICLR 2024, 2403.10760): contact-based object representation for thin, ungraspable objects.
  - [M] Our board meshes cost about 0.05 AUC in tracking; a mesh 5 mm too thick made flat objects register flipped.
  - [I] Our draft's SDF grid is capped at 64 cells per axis, about 1 cm voxels on a long board. That is too coarse for a
    1–2 cm thick board: expect crossings and wrong-face snaps. Use exact mesh queries (signed by winding number) or
    ≤ 2 mm voxels.
- **Non-prehensile phases (slide to the edge).**
  - [I] During sliding, the human pads press the top face, and the table supports the board. The contact set is
    one-sided, so a single hand cannot resist wrench in all directions. EgoCPT's grasp matrix with a support disk is
    exactly the tool to check that "pads on top plus table friction" can produce the observed acceleration.
  - [I] The lift needs the thumb pad on the *underside* of the overhang (sidedness).
- **Two hands.**
  - [F] EgoCPT solves both hands jointly (56 DoF) with shared force allocation; FlashDexRetarget uses per-hand critics
    on the full state; DexOAK pools all objects into one graph.
  - [M] Our ep24 had overlapping robot hands at reset, now separated by `--hand_sep`.
- **Tool use (sweeper and dustpan).**
  - [F] CHORD adds a relative object-pose reward, masked to demonstrated object–object interaction phases.
  - [F] EgoCPT reports "sweep dustpan" 54.5 % on EgoDex; C2Dex and OmniHOI show sweeping on real robots.
  - [I] Tool grasps are stable power grasps over long segments, ideal for the segment-wise rigid-grasp idea in §7.

---

## 7. Synthesis: recommended algorithm for us

### 7.0 Principle [I]

- Trust the object, not the human hand. Our object tracks are good, while the hand–object relative pose is off by
  1–2 cm.
- Inside a stable contact segment, the human grasp relative to the object is constant (carry, slide, sweep stroke).
  So estimate **one robot grasp per segment, in the object frame**, rather than one per frame.
- This (i) averages hand noise over N frames, (ii) makes every in-segment frame a valid reset, and (iii) hands RL
  clean, consistent contact labels.
- It is DexForge's keyframe idea (DexYCB keyframes reuse one seed) combined with C2Dex/EgoMatrix stable contacts and
  EgoCPT's wrench check. It also matches the segments `tools/manip_segments.py` already finds [M].

### 7.1 Algorithm: segment-wise contact-anchored grasp retargeting (SCAR)

Inputs: object meshes $M_j$, tracks $T_j(t)$, table plane, MediaPipe joints $K_h(t)$ per hand, the E2S solution
$(W^{E2S}_h(t),q^{E2S}_h(t))$, segments from `manip_segments.py`, and the FlashCHORD scene (Newton FK, Sharpa
primitives). Never mocap or ground-truth poses.

**Step 1: human contact evidence (object frame).**
- For each hand $h$, segment $s\in$ {thumb MCP–IP–tip, four fingers × (MCP–PIP, PIP–DIP, DIP–tip), palm quad (wrist,
  index MCP, pinky MCP)} and object $j$, build a capsule of human radius $r^H_s$ (about 8 / 9 / 10 mm distal → proximal;
  palm half-thickness about 12 mm) [I anthropometric].
- Compute $d_{s,j}(t)=\min_{y\in\text{axis}_s}\phi_j(T_j^{-1}y)-r^H_s$, the closest object point $p$ and the outward
  normal $n=\nabla\phi$.
- Candidate if $d<\tau_{on}$ with $\tau_{on}=15$ mm (DexOAK; try 10 and 20).
- Optionally add stereo-depth evidence: median (measured hand depth − rendered object depth) over hand-mask pixels within
  1 cm of the object silhouette.

**Step 2: consolidation.**
- Per (hand, segment, object), runs of candidates within one manipulation segment. Merge gaps ≤ 3 frames; drop runs
  < 8 frames at 30 Hz (scale to our fps).
- Map points to the object frame. Split a run where < 80 % of points lie within 8 mm of the medoid (DexForge values).
- Anchor $a$ = medoid, normal $n_a=\nabla\phi(a)$, face id = the normal cluster.
- **Sidedness**: $\sigma=\mathrm{sign}((k-a)\cdot n_a)$ over the run must be +1 for ≥ 80 % of frames, else reject.

**Step 3: wrench feasibility (EgoCPT/DexForge).**
- Per frame, $w^{req}=[m(\ddot x-g);\ I\dot\omega+\omega\times I\omega]$ from our *smoothed* object track. m = 0.3 kg
  is the kit placeholder; the uncertainty in m is stated, not hidden.
- Grasp matrix $G$: all active anchors on object $j$ (both hands), 4–8 friction-cone edges, μ = 0.5 [I; DexForge
  0.2, FlashCHORD force-closure 0.1]. Add support contacts: table under the object while its lowest point is within
  5 mm of the plane; the other object for tool use.
- Solve $\min_{\lambda\ge0}\|G\lambda-w^{req}\|^2+\rho\|\lambda\|^2$ with $\|f_i\|\le20$ N.
- **Flag** frames with residual > 20 % of $\|w^{req}\|$, or a missing opposition during lift.
- Repair by promoting weaker candidates ($\tau_{on}$ up to 25 mm) or adding the thumb–finger opposition from the
  GRASP-taxonomy prior (EgoMatrix). If still infeasible, mark the segment "primitive needed" (forensics idea C).

**Step 4: robot contact points.**
- Human segment → Sharpa link (thumb DP→`thumb_DP`, finger DP→`*_DP`, DIP–PIP→`*_MP`, MCP–PIP→`*_PP`,
  palm→`hand_C_MC`).
- For a pad contact the robot point is $c_i(q)=\arg\min_{y\in\mathcal P_i(q)}\phi_j(y)$ over the **pad region**
  $\mathcal P_i$ (palmar half, distal half of the link surface; DexForge: palmar cosine ≥ 0.75, axial ≤ 0.5).
- With primitives, $\phi_j(c_i)=\phi_j(\text{axis point})-r_i$ with $r_i$ = 7.26 / 8.26 / 8.56 / 9.34 / 20.9 mm.

**Step 5: per-segment grasp solve** (one static problem per segment $k$; DexForge keyframes).
- Variables: the wrist pose in the object frame $^oW_h$ and finger joints $q_h$ (both hands jointly if they share an
  object). Minimize:
$$
\begin{aligned}
E_k=\;&w_g\sum_i \big(\phi(c_i)-\delta\big)^2 &&\text{gap: pad on the face, }\delta=0.5\text{ mm}\\
+\;&w_t\sum_i \big[\max(0,\|\Pi_{n_i}(c_i-a_i)\|-\rho_t)\big]^2 &&\text{stay in the human patch, }\rho_t=10\text{ mm (2609.24093 tolerance)}\\
+\;&w_n\sum_i r_i^2\,(1+\hat n_{pad,i}\cdot n_i)^2 &&\text{pad faces the surface (DexForge, weight }100\alpha)\\
+\;&w_p\sum_{y\in\text{hand}}\max(0,m-\phi(y))^2 + w_p\sum \max(0,m-z_{tab}(y))^2 + w_p\sum_{hh}\max(0,m_{hh}-d_{hh})^2 &&m=1\text{ mm}, m_{hh}=5\text{ mm}\\
+\;&w_s\sum_i \max(0,-(x_i^{axis}-a_i)\cdot n_i)^2 &&\text{same side (sidedness)}\\
+\;&w_W\,(1-0.99\,c)\,d_{SE3}\big(W,\ \mathrm{med}_t\,W^{E2S}\big)^2 + w_q\|q-\mathrm{med}_t\,q^{E2S}\|^2 &&\text{wrist free in contact}
\end{aligned}
$$
- Joint limits are bounds. Scale residuals as the draft does: gap/5 mm, penetration/1 mm, wrist/2 cm, joints/0.5 rad.
  Prefer the *gap* formulation over point equality, because our anchors are uncertain by about 1 cm.
- Multi-start: 3–5 seeds (E2S median, ± palm roll, open-hand start) [F: DexForge first-frame candidates 3; Do as I Do
  multiple kinematic starts]. Keep the best feasible one.
- Non-contact fingers keep E2S-relative curl but must satisfy penetration.
- **Grip preload variant** (for replay and RL bias): commanded finger targets flexed so that $\phi(c_i)$ would be −2 to
  −4 mm; the collision geometry stops them and the PD error produces normal force [I; motivated by ContactOpt's
  soft-tissue interpenetration and OATH's "position tracking alone does not induce force"].

**Step 6: trajectory assembly.**
- In-segment frames: $W_h(t)=T_j(t)\,{}^oW_h$, constant $q_h$. The object track is pre-smoothed in SE(3), so its jitter
  does not shake the hand.
- Transitions (approach, release, regrasp, rest): blend from E2S toward the segment grasp over 0.2–0.3 s with
  pre-contact clearance 5 mm (DexForge). Use PCHIP for joints and SLERP/SE(3) splines for the wrist (OmniHOI).
- Then a trajectory-level smoothing QP or LM with the DexForge temporal operator (τ = 0.1 s; W = 100/1/1; M = 32/16)
  under the same penetration constraints, checked at 4–16 substeps between frames.
- Hand-hand: solve jointly when the hands come within 2 cm.

**Step 7: contact labels for FlashCHORD.**
- Recompute `mano_{s}_object_contact_positions/normals/part_ids` *from the robot reference*. Pad points within 3 mm of
  a surface are in contact, with normals into the object, 16 slots, stable runs only.
- The same function as E2S post-processing (`contact_labels.py`, 18 mm, min run 2) is acceptable as a fallback.
- [F] All-zero contacts load but penalize grasping (`notes/22`), so never ship empty labels on a contact episode.

**Step 8: physics checks (CPU, FlashCHORD pins; ordered from cheapest to most expensive).**
- **8a. Static audit.** Penetration p95, % frames > 2 mm, pad gap distribution for active contacts, wrong-side count,
  hand-hand overlap, joint-limit hits, jerk.
- **8b. Pop map** (`tools/frame_quality_probe.py`): reset to each frame, one step, worst object jump.
- **8c. Pinned-object settle** (DexMachina post-processing): object welded to the reference, hands PD-driven to the
  reference for about 20 steps; record the achieved q and write it back.
- **8d. No-policy replays**, four variants: {stiff wrist, real soft wrist} × {no preload, 2–4 mm preload}. Objects
  free, from frame 0 and from each segment start.
  - Metrics: `sim_vs_ref` ADD-AUC per segment, frames survived, contact retention.
  - **Interlock flag**: any finger capsule axis inside the object, or penetration > 3 mm while the object follows. Per
    OmniHOI such "successes" are false.
- **8e. Only if 8d fails on a lift segment**: local sampling refinement over that window. Either CMA-ES on per-keyframe
  offsets (OmniHOI; rolling horizon, 1 s windows) or SPIDER-style sampling with virtual contact guidance and Do-as-I-Do
  perturbations. Run on CPU MuJoCo for short windows, or on GPU.

**Step 9: training.**
- Same FlashCHORD recipe, with resets only on frames passing 8b (Gen2Dex: valid resets matter).
- A/B the contact objective: CWS with the new labels vs the force-closure override (`objective.force_closure.enabled`,
  no code change per `notes/14`).
- Optional code additions with evidence:
  - OATH contact-error observations (−8 to −22 pp when removed, per its Table III);
  - FlashDexRetarget's one-sided fingertip distance reward (σ = 1 cm).

### 7.2 Comparison with the draft `pipeline/contact_retarget.py` [M code read; I suggestions]

The draft already does per-frame least squares on Newton FK with object/table penetration, continuity and relaxation
to E2S. Suggested changes, in order of expected impact:
1. **Tip site vs pad.** The target places the MJCF tip site, the end cap on the finger axis, at "surface + depth under
   pad". That gives a *fingertip* contact and fights the penetration term when the finger lies flat (board pressing). Use
   the pad-region closest point (Step 4) and a normal term.
2. **Per-frame snap vs per-segment anchors.** A window-5 smoothing of per-frame snapped points still follows 1–2 cm hand
   noise. Medoid anchors per stable run (or one grasp per segment) remove it.
3. **Snap gate.** 25 mm with run ≥ 3 frames is permissive. Use 15 mm, ≥ 8 frames, the 80 % / 8 mm consistency test,
   sidedness, and the wrench check.
4. **SDF resolution.** The grid cap of 64 cells per axis gives about 1 cm voxels on long boards. Use exact mesh distance
   with winding-number sign (e.g. Warp `mesh_query_point_sign_winding_number`) or 2 mm voxels near contacts, plus a
   crossing check (OmniHOI parity).
5. **Missing terms.** Hand–hand collision (ep24 overlap history), palm and proximal-link contacts (board and pan
   handles), and a wrist weight that drops during contact ($1-0.99c$).
6. **Speed.** Finite differences × 40 evaluations × FK per frame is acceptable for about 300 frames on CPU. A
   trajectory-level solve wants analytic Jacobians: PyRoki/jaxls with the Sharpa *primitive* URDF (capsules and
   spheres, natively supported) or mink with the Do-as-I-Do Sharpa MJCF and `CollisionAvoidanceLimit`.

### 7.3 What to borrow from where

| Need | Borrow from | Concrete artefact |
|---|---|---|
| Stable anchors | DexForge (code), C2Dex | `contactaware.yaml` `contact_extraction` values; DBSCAN medoid per segment |
| Pad region and normal term | DexForge, 2609.24093 | `contact/mapping.py` terminal-pad mask; direction-matching surface point |
| Wrist freedom in contact | DexForge; 2506.09384 | palm weights × $(1-0.99c)$ |
| Thin-object safety | DexOAK $\mathcal L_{dir}$; OmniHOI crossing repair | sidedness hinge; parity test |
| Wrench check with table support | EgoCPT; DexForge force closure | NNLS on the grasp matrix with a support disk |
| Interaction regularizer (optional) | DexOAK / TopoRetarget | Laplacian with 64 object anchors, λ = 500, κ = 30 (only *with* contact attraction) |
| Physics projection | DexMachina post-processing; Do as I Do warmup | pinned-object settle; lead-in |
| Physics refinement if needed | OmniHOI CMA-ES; SPIDER / Do as I Do (Sharpa MJCF + mink + MJWarp code) | keyframe offsets; virtual contact guidance with contact filter |
| RL signals | OATH; FlashDexRetarget; CHORD force closure | contact-error observations; one-sided tip reward; force-closure override |
| Valid resets | Gen2Dex | reset only on frames that pass the pop gate |

### 7.4 Expected gains (evidence and honest uncertainty)

- [F] **Reference quality → RL success**, other datasets:
  - Sharpa +35 pp SR (Morphometric);
  - +27.6 pp SR on OakInk Allegro and +5.5 / +7.9 ADD-AUC on ARCTIC (DexOAK);
  - +40 pp end-to-end (C2Dex contact consolidation);
  - 0/10 → 9/10 tasks from valid resets (Gen2Dex);
  - 1/10 → 10/10 with force allocation (EgoCPT, n = 10).
- [F] **Kinematic metrics to expect from good contact-aware IK:**
  - pad/patch error about 10–15 mm (MMO Sharpa 9.7 mm; 2609.24093 14.7 mm; C2Dex 11.9 mm);
  - maximum penetration about 1–5 mm (TopoRetarget 1.07 mm; C2Dex 4.0–5.4 mm; EgoCPT 0.05–0.08 mm mean).
  - [M] Ours today: p95 16–20 mm inside, 63–88 % of frames > 2 mm, 63–89 % of start frames pop.
- [I] **Guess** (not a measurement): if 8b/8d pass, ep24 could leave its floor (0.23) only once the lift is learned.
  Plausible range 0.3–0.6. ep18 might reach its floor (0.64) or above if the sweeper stops falling. Both depend on RL
  as much as on the reference; rollout noise (0.13–0.41 for one policy [M]) means any A/B needs ≥ 2 seeds and several
  rollouts.

### 7.5 Risks

1. False contacts from hovering or occluded fingers, made worse by a wide gate. Mitigation: consolidation plus the
   wrench check. CHORD shows contact noise ≥ 25 mm collapses wrench guidance.
2. Wrong-face snaps and crossings on the thin board; mesh thickness error (5 mm made flips [M]).
3. Kinematically clean but dynamically useless references (EgoCPT, OmniHOI). Mitigation: preload, 8d, 8e.
4. Rigid per-segment grasp hides real finger gaiting (sweeping wrist motion). Mitigation: allow small per-frame
   residuals inside a segment (w = 0.1 × the segment-solve weights).
5. Object-track jitter transfers to the hands. Mitigation: smooth the object in SE(3) before composition, but keep the
   scored object reference untouched.
6. FlashCHORD terminates if the palm is > 15 cm from the reference wrist. Not an issue, since the new reference *is* the
   wrist, but it is an issue if the policy needs a larger regrasp.
7. Evaluation starts at frame 0 with no settling, so frame 0 must pass 8b.
8. Over-constrained contacts at switches cause jitter. Mitigation: switch penalty about 7 frames (DexForge) and blends.

### 7.6 Cheapest falsification tests (CPU, no GPU)

| ID | Hypothesis [I] | Test | Falsified if |
|---|---|---|---|
| H1 | Segment anchors from our perception are consistent | Per run: fraction of points within 8 mm of the medoid; sidedness; overlay on frames (`track_overlay.py`) | < 60 % of the contact-frames of ep24/ep18 fall in consistent runs, or a thumb lands on the wrong board face |
| H2 | The consolidated contact set can produce the tracked object motion | Step 3 NNLS residual per frame (m = 0.3 kg; also 0.15 / 0.6) | Residual > 20 % on most lift frames of ep24 even after promotions. Then the evidence does not support a two-hand lift; go to primitives or force closure |
| H3 | SCAR removes reset pops | 8a + 8b on ep24, ep18, ep12, ep27 | Dirty start frames not below 20 % (from 89 / 73 / 63 / 69 % [M]), or frame-0 pop > 1° |
| H4 | The object follows a stiff-wrist replay through grasp/carry when pads preload | 8d, 4 variants | All lift segments lose the object within 10 frames in every variant, or success occurs only with interlock flags. That would point to 8e (sampling refinement) rather than more IK |
| H5 | Better references improve learned policies | One GPU batch: ep24 + ep18 × {current, SCAR} × 2 seeds, same budget; select by `sim_vs_ref` | SCAR does not beat the current reference by ≥ 0.1 `sim_vs_ref` on either episode |

H1–H4 cost CPU minutes. H5 is the first paid step; the batch plan and expected cost need the owner's go-ahead per
`CLAUDE.md`.

---

## 8. References

arXiv ids, venues as given in the arXiv record, the paper, or memory where marked. Code links were checked on project
pages and by cloning on 2026-10-21.

**Contact-anchored, contact-aware and interaction-preserving retargeting**
- 2609.24093: Contact-Anchored Retargeting + Residual Policy Learning (DexGEM Lab), tech report. `github.com/DexGEM-Lab/real2sim2real` (README and videos only; "Code release coming soon").
- 2609.28660: Morphometric Imitation (Berkeley). `github.com/tsadja/morphometric` ("Code will be released soon").
- 2610.26762: DexOAK (ETH/Inria). Project page `fspinola.github.io/dexoak`; no code link found.
- 2608.07045: C2Dex, submitted to RA-L. `github.com/K-Jie/C2Dex_code` (README only).
- 2610.06331: DexForge. **Code:** `github.com/wmz1226/DexForge` (contactaware + forceaware; has a `sharpa` hand spec).
- 2610.17572: EgoCPT (Sharpa; EgoDex/TACO). No code link in the arXiv record.
- 2610.15769: Hand2Robot. Project page; no code link found.
- 2610.10855: OmniHOI. Project page; no code link found.
- 2610.18822: EgoMatrix.
- 2606.16272: TopoRetarget. No code link found.
- 2607.03828: ObjRetarget.
- 2505.01083: DexFlow.
- 2610.17789: DexStitch.
- 2506.09384: Analyzing Key Objectives in Human-to-Robot Retargeting.
- 2509.26633: OmniRetarget.
- 2402.04820: Lakshmipathy, Hodgins, Pollard, ACM TOG 2025.
- 1910.03135 DexPilot (ICRA 2020); 2307.04577 AnyTeleop (RSS 2023, dex-retargeting); 2108.05877 DexMV (ECCV 2022);
  2312.03864 GeoMatch (CoRL 2023); 2210.00722 GenDexGrasp (ICRA 2023, `tengyu-liu/GenDexGrasp`); 2410.01702 D(R,O)
  Grasp (ICRA 2025); 2310.03740 ContactGen (ICCV 2023); 2303.15469 CAMS (CVPR 2023); 2503.07541 GeoRT.

**Physics-in-the-loop and RL**
- 2511.09484 SPIDER. **Code:** `github.com/facebookresearch/spider` (Sharpa data released).
- 2606.19333 Do as I Do. **Code:** `github.com/malik-group/do-as-i-do` (Sharpa MJCF, mink IK, MJWarp sampling, warmup).
- 2505.24853 DexMachina.
- 2503.21860 ManipTrans (CVPR 2025).
- 2502.09614 DexTrack (ICLR 2025; `Meowuu7/DexTrack`).
- 2607.00033 CHORD (FlashCHORD port).
- 2610.01849 FlashDexRetarget.
- 2610.14379 OATH.
- 2607.11874 REGRIND. **Code:** `github.com/yunhaif/regrind`.
- 2610.24392 Gen2Dex.
- 2601.18121 Grasp-and-Lift.
- 2609.01938 DemoMimic.
- 2605.05925 DexSynRefine.
- 2504.12609 Human2Sim2Robot.
- 2411.04005 ObjDex.
- 2610.12440 Generative Neural Retargeting.
- 2608.15560 ReForce.
- 2603.12185 ComFree-Sim.

**Contact estimation and HOI reconstruction**
- 2104.07267 ContactOpt (CVPR 2021); 2104.03304 GraspTTA (ICCV 2021); 2205.07982 TOCH (ECCV 2022, venue from memory);
  2311.18448 HOLD (CVPR 2024, `zc-alexfan/hold`); 2309.05663 DiffHOI (ICCV 2023); 2404.12383 G-HOP (CVPR 2024);
  2503.21313 HORT (ICCV 2025).
- 2505.11152 HACO (NeurIPS 2025); 2605.05886 ContactPrompt; 2608.13014 EgoPHI (ECCV 2026); 2608.06192 HOPE;
  2610.09455 RLHND; 2606.30598 EPIC-Contact / HOPformer (ECCV 2026); 2409.02224 EgoPressure; 2501.02973 HaWoR.

**Non-prehensile and extrinsic dexterity**
- 2211.01500 (CoRL 2022); 2305.03942 HACMan (CoRL 2023); 2403.10760 CORN (ICLR 2024); 2503.23120 ExDex; 2603.09882
  DAPL (RSS 2026).

**Solvers**
- 2505.03728 PyRoki (IROS 2025; `chungmin99/pyroki`, examples 09/11 hand retargeting with a contact cost of margin 1 cm,
  weight 5); mink (`kevinzakka/mink` v1.1.0, `CollisionAvoidanceLimit`); 2310.17274 cuRobo.

**Repository facts used**
- `STATUS.md`, `docs/work-log.md` (2026-10-21 entries), `docs/forensics-2026-10-21.md`,
  `docs/research/notes/14-policy-tracking-error.md`, `docs/research/notes/22-hand-reference-contract.md`,
  `pipeline/contact_retarget.py` (untracked draft), `pipeline/robot_clearance.py`.
- Sharpa primitive URDF and MJCF from the local `video_to_data` checkout.
