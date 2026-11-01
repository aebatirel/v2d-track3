# Human hand models for the physics study: what to simulate, and how

2026-10-30. Literature and open-source review, plus CPU measurements on third-party model files. No rentals, $0.
Purpose: before moving to a robot hand, replay each recorded episode with a simulated **human** hand driven by our
perceived hand motion, in FlashCHORD's physics, and see where the objects do or do not follow the video. This note
chooses the hand representation:
- (a) a MANO-derived articulated hand;
- (b) our own human-proportioned capsule hand;
- (c) an existing open-source human hand (MyoHand).

Labels:
- **[L]** literature, repository or documentation opened today (URL in §7);
- **[L-abs]** abstract only;
- **[L-sec]** a table reproduced in a secondary source I opened (named);
- **[M]** measured by me on model files or the installed kit (commands in §8);
- **[I]** inference;
- **[H]** hypothesis, with the experiment that would falsify it.

Facts given by the caller and not re-derived:
- our perception (MediaPipe 21 keypoints, stereo-lifted, MANO betas = 0);
- the simulator settings;
- the MANO licence reading;
- the ManipTrans, V2P-Manip, DexMachina and SPIDER headline results.

## 0. Answer

**Build (b): our own capsule hand, with the MediaPipe 21-keypoint topology and Arti-MANO's 22 finger DoF.** Size it
from robust (episode-median) bone lengths that pass an anthropometric gate. Use human torque limits and graded PD
gains. Release it under Apache-2.0. Use MyoHand (Apache-2.0) and the literature only as sources for numbers: capsule
radii, joint ranges, torque capacity. Do not use a MANO mesh. Reasons:

1. **Nobody simulates the MANO surface as such.** The leading works use one of two hands:
   - per-bone meshes or convex pieces of the *mean* MANO shape (D-Grasp, ArtiGrasp, DeepSimHO);
   - capsules (HUG, HOIC, PhysHOI).

   HUG builds both a mesh and a capsule version from MANO and simulates with the capsule hand, "as its smooth normals
   give more stable contacts" [L].

   With betas = 0 we would get the mean shape, not our demonstrator's. A per-bone MANO mesh also adds no surface
   fidelity a capsule lacks [I], because:
   - MuJoCo collides meshes as convex pieces;
   - FlashCHORD generates one contact per geom pair (§2.2) [M].
2. **What made Arti-MANO win in V2P-Manip is skeleton match, not the mesh.** The authors write: "its link proportions and
   joint hierarchies closely align with the human MANO model used in our trajectory optimization" [L]. Our trajectories
   come from MediaPipe keypoints, so the matching skeleton is one built from those keypoints [I]. DexMachina's
   "DoF matters more than size" points the same way (given).
3. **Licence.** MANO-derived URDF or meshes cannot ship with an Apache-2.0 release; only a builder script could [L].
   MyoHand is Apache-2.0, but it does not fit as the study hand (§2):
   - Newton's MJCF importer skips its `<muscle>` actuators [M];
   - its size is fixed (MoBL-derived) [L];
   - its thumb MCP has 1 DoF [M];
   - its oblique anatomical axes make the 21-keypoint IK harder [I].
4. **Perception is the bigger risk, and the representation must not hide it.** Our perceived fingers are about
   25–40 % too short for the perceived palm (§3.5) [M+I]. A hand built from raw per-frame keypoints would then
   under-reach, so the bone lengths need an anthropometric gate. This also has to be reported as a perception finding.

**Primary falsification test:** §6.9.

## 1. How physics-based human hand–object works represent the hand

| work (sim) | geometry | DoF and limits | actuation | contact / friction | label |
|---|---|---|---|---|---|
| **D-Grasp** CVPR'22 (RaiSim) | MANO **mean shape**. Per-bone meshes, vertices assigned by argmax skinning weight. Repo URDF `rsc/mano/mano_mean_meshcoll.urdf`: 16 OBJ collision meshes, hand mass 0.135 kg. Paper: primitives gave "an order of magnitude increase in training speed". | 45 finger DoF (3 revolute per joint) + 6 global. Limits "data-driven" from DexYCB + slack. URDF: MCP flex 0…90°, abd ±46°, twist ±14°; PIP −29…90°; DIP 0…90°. | PD on residual targets. Repo: fingers kp 50 N m/rad, kd 0.2. Effort 1000, i.e. unbounded. dt 2.22 ms × 13. | μ 0.8 (finger–object, finger–finger), restitution 0 (repo `Environment.hpp` l.120–122) | [L] + [M] |
| **ArtiGrasp** 3DV'24 (RaiSim) | MANO mean shape "following [D-Grasp]" | 51 DoF (45 + 6) | PD targets; dt 2.5 ms × 4 | not stated | [L] |
| **ManipTrans** CVPR'25 "Arti-MANO" (Isaac Gym, dt 1/60) | D-Grasp's articulated MANO, "fixing the hand collision meshes" | **22 DoF** (repo `artimano.py`): finger MCP 2 + PIP 1 + DIP 1; thumb CMC 3, MCP 2, IP 1. Follows CPF/A-MANO constraints. URDF `assets/mano_urdf/` not distributed (MANO licence) [M]. | residual RL. Optional PID wrist (kp_pos 10, kp_rot 0.3). | Friction set "slightly higher than the real-world value" to compensate for the missing skin deformation. Curriculum: zero gravity and high μ first. Objects 200 kg/m³. | [L] + [M] |
| **V2P-Manip** (Isaac Gym) | Arti-MANO, one of four hands | n/a | n/a | Success: Arti-MANO 82.4 > Inspire 78.8 > Shadow 61.6 > Allegro 52.0 %, attributed to skeleton match (§0) | [L] |
| **PhysHOI** (Isaac Gym, PD 60 Hz, policy 30 Hz) | SMPL-X humanoid; "bodies are simplified as simple geometries like capsules or boxes" | hands 30 × 3 DoF (spherical) | PD on target rotations | contact inferred from forces | [L] |
| **Omnigrasp** (Isaac) | SMPL-X humanoid, mean shape, 52 joints (as restated by its follow-up arXiv 2505.12278) | all 3-DoF spherical, PD | PD | n/a | [L-abs] |
| **QuasiSim** ECCV'24 | The human (MANO) hand is a **point set** (kinematic, relaxed); the final transfer is to a Shadow hand in Bullet / Isaac Gym. | n/a | joint forces; PD in the target sims | Spring–damper penalty contact, "soft" at first, then tightened (curriculum) | [L] |
| **HOIC** 2024 / Hu 2022 (MuJoCo 450 Hz) | **Own 26-DoF capsule + box hand, not MANO**. Repo XML: capsules r 6–13 mm, 4 palm boxes 4 × 4 × 2.7 cm. | 20 finger DoF: MCP flex+abd, PIP, DIP; thumb CMC 2, MCP 1, IP 1. MCP −74…92°, PIP/DIP −6…115°. | PD + a policy force on the object. The "residual force" (not explained by contacts) is minimised. Input: RGB-D kinematic tracking. | Friction "1 0.005 0.001" with condim 3 (torsion unused), margin 0.5 mm. Physically plausible frames 91 % vs 60 % kinematic (Box sequence). | [L] + [M] |
| **DeepSimHO** (MuJoCo) | MANO "convexly decomposed by MANO blending weights"; hand static | none | none | stability = object displacement in 200 ms | [L] |
| **Garcia-Hernando** IROS'20 (MuJoCo) | Adroit (Shadow-based) robot hand | 24 + 6 DoF | IK from **21 estimated keypoints** + residual RL | "simple pose retargeting functions fail due to the domain gap, contact physics, pose prediction errors and noise" | [L] |
| **HUG** 2026 (MuJoCo) | MANO fixed β; **capsule per phalanx, convex-mesh palm**; mass 0.4 kg by hull volume | every finger joint a ball joint; 6-DoF wrist | critically damped position actuators | **palm softer and higher priority** ("a stiff palm would eject the object") | [L] |
| **SPIDER** (MuJoCo-Warp / Genesis) | robot hands only; MANO is input (fingertips + wrist IK) | n/a | n/a | kinematic 11.0 → physics 48.8 ADD-AUC (given) | [L] |
| **DexMachina** (Genesis) | robot hands | n/a | n/a | DoF matters more than size (given) | [L-abs] |
| **MyoHand / MyoDex** (MuJoCo) | MoBL + 2nd-Hand bones. Collision: capsules per phalanx (r 6–10 mm) plus a **flat ellipsoid pad** on each distal phalanx (5 × 8 × 2 mm). | 23 DoF | 39 muscle–tendon units | condim 3, margin 1 mm, finger joint damping 0.05, armature 1e-4 | [M] / [L-abs] |

Pattern [I]:
- no physics work uses an individually fitted MANO shape;
- every work that simulates a full human hand uses either mean-MANO per-bone pieces or capsules;
- every successful *tracking* system adds a correction layer: residual RL, object compensation forces, or a physics
  curriculum. Pure kinematic replay fails (SPIDER 11.0; Garcia-Hernando).

## 2. Simulation-ready human hand models, and what our simulator accepts

### 2.1 Candidates

| model | format / DoF | geometry | licence | fit to our demonstrator's bones? | drive from 21 keypoints? |
|---|---|---|---|---|---|
| **MyoHand** (myo-sim 0.2.3) | MJCF; 23 DoF + forearm and wrist | capsules + DP pads | **Apache-2.0** (LICENSE and file headers) [L][M] | Hard. Fixed MoBL proportions [L]; scaling means editing body offsets, geoms and **39 tendon paths** | Moderate to hard. Oblique axes; thumb MCP 1 DoF; finger MCP abd ±15° [M] |
| D-Grasp MANO URDF | URDF (RaiSim); 45 + 6 | mean-MANO per-bone meshes | MANO-derived meshes (MANO licence); repo LICENSE is RaiSim's | No (mean shape) | Easy (3 hinges per joint) |
| ManipTrans Arti-MANO | URDF, 22 DoF | MANO meshes | code GPL-3.0; URDF not distributed | No | n/a |
| HUG capsule MANO | MJCF built from MANO | capsules + convex palm | code MIT; needs MANO files | Fixed β | Easy (ball joints) |
| manotorch | MANO layer + anatomical twist/spread/bend axes | mesh | Apache-2.0 code; MANO data under MANO licence | via betas (needs a fit) | Fitting step |
| SMPLSim | MJCF generator for SMPL/-H/-X humanoids | n/a | BSD-3; SMPL-X model licence | via betas | n/a |
| HOIC hand | MJCF, 26 DoF | capsules / boxes | GPL-3.0 | Fixed | via their own tracker |
| Adroit (Shadow) | MJCF, 24 DoF | robot hand | Apache-2.0 | n/a (robot) | IK |
| **Ours (proposed)** | URDF with Newton `<capsule>`, 22 DoF | capsules + pads | **Apache-2.0** | **By construction** | **Analytic** (§6.7) |

No public, licence-free MANO-to-MJCF/URDF converter that ships a sized hand was found [I, after search]. The MANO
builders above all need the MANO model files.

### 2.2 What FlashCHORD (Newton 1.2.0 + MuJoCo-Warp 3.8.1) accepts [M]

- **Capsules in URDF.** Newton's URDF importer reads `<capsule radius height>`. The capsule axis follows the importer's
  `up_axis` (default Z) (`import_urdf.py` l.462).
- **No muscles.** The MJCF importer handles `position`, `velocity`, `motor` and `general` actuators only and warns
  "Unknown actuator type" otherwise (l.2523–2700). It does parse spatial tendons. MyoHand's muscles are `general` with
  muscle parameters, so they *might* import. That is unverified, and they would replace the PD drive our study needs.
- **Multi-DoF joints.** The kit's floating hand is 3 prismatic joints plus a ball wrist, with URDF fingers below. It
  uses dummy links of 1e-4 kg (`sharpa_hands.py` l.96–140). A 2-DoF MCP can use the same idiom.
- **Kit defaults.** Fingers kp 1.7 N m/rad, kd 0.1, **armature 0.01 kg m²**, effort 10 N m. Wrist kp 25 N/m, or the
  `stiff_tracking` variant at kp 6000. Physics at 100 Hz (20 fps × 5). nconmax 256.
- **One contact per geom pair.** `SolverMuJoCo(enable_multiccd=False)` is the default and FlashCHORD does not change
  it (`runtime/sim.py`), so every convex pair yields **one contact point**. Margin > 0 also forces a single contact.
  A fingertip pad needs 2–3 geoms to yield a contact patch (§5).
- **Torsional friction is available but unused.** Per-shape `condim` and `mu_torsional` exist (`import_mjcf.py`
  l.625, 656; `solver_mujoco.py` l.4784). MuJoCo-Warp sizes its constraint rows for condim up to 6 (`io.py` l.229–233).

## 3. Human numbers for the sim hand

### 3.1 Maximum forces

| quantity | value | source |
|---|---|---|
| Index fingertip maximum, posture MCP 45° / PIP 45° / DIP 10° | palmar **27.9 ± 4.1 N**; distal 24.3; medial 22.9; lateral 14.7; dorsal 7.5 N (8 subjects) | Valero-Cuevas 1998 [L] |
| Grip (Jamar), dominant hand, age 20–39 | men 48.9–54.4 kgf (480–534 N); women 28.5–29.7 kgf (280–291 N) | Mohammadian 2014, n = 1008 [L] |
| Tip pinch, dominant | men 9.1–9.6 kgf (89–94 N); women 5.7–6.1 kgf (56–60 N) | same [L] |
| Key (lateral) pinch, dominant | men 11.1–11.5 kgf (109–113 N); women 7.7–7.8 kgf (76 N) | same [L] |
| Palmar (3-jaw) pinch, dominant | men 11.2–12.9 kgf; women 7.2–7.6 kgf | same [L] |
| Mathiowetz 1985 (US norms; 638 adults) | pinch stable from 20 to 59 years; grip peaks at 25–39 years | [L-abs] |
| Multi-finger maximum | individual finger forces are smaller in multi-finger MVC than alone ("force deficit") | Li 1998 [L-abs] |

### 3.2 Joint torques

| joint | torque at the max palmar index force [I from L] | MyoHand muscle capacity, neutral / MCP45-PIP45-DIP10 [M] | proposed **effort limit** | proposed **kp** (N m/rad) | needed for 3–8 N at the tip [I] |
|---|---|---|---|---|---|
| index MCP flex | **1.85** | 3.65 / 4.85 | 2.5 | 2.0 | 0.20–0.53 |
| index PIP | **1.16** | 2.12 / 2.74 | 1.5 | 1.2 | 0.12–0.33 |
| index DIP | **0.47** | 0.85 / 0.89 | 0.6 | 0.5 | 0.05–0.13 |
| middle MCP / PIP / DIP | n/a | 5.14 / 3.40 / 0.57 ; 7.43 / 4.61 / 0.62 | 3.0 / 2.0 / 0.6 | 2.0 / 1.2 / 0.5 | n/a |
| ring MCP / PIP / DIP | n/a | 1.89 / 1.38 / 0.40 ; 2.70 / 1.69 / 0.48 | 1.8 / 1.1 / 0.45 | 1.5 / 0.9 / 0.35 | n/a |
| little MCP / PIP / DIP | n/a | 1.30 / 0.72 / 0.25 ; 1.49 / 0.95 / 0.17 | 1.2 / 0.7 / 0.25 | 1.0 / 0.6 / 0.25 | n/a |
| MCP abduction (index, little) | n/a | 0.4–1.0 | 0.8 | 1.0 | n/a |
| thumb CMC, 2 axes | n/a | 3.17 / 1.08 (flexion axis, ±); 0.76 / 0.42 (abduction axis) | 2.5 / 0.8 | 2.0 / 1.0 | n/a |
| thumb MCP | n/a | 1.42 / 1.12 | 1.2 | 1.2 | n/a |
| thumb IP | tip pinch 56–94 N × 1.5–2 cm ≈ 0.8–1.9 | 1.76 (flexion) | 1.5 | 0.8 | n/a |

How the columns were made:
- **Valero-Cuevas column** [I]: 27.9 N perpendicular to the distal phalanx at the paper's posture, lever arms from
  MyoHand's index lengths (PP 42.6, MP 25.1 mm, pad 17 mm from the DIP). This is the torque set a person
  *simultaneously* produces at maximal effort.
- **MyoHand column** [M]: every agonist at full activation with force–length at that posture, one joint at a time. It
  is an upper bound: no force deficit, no enslaving.
- **Proposed columns** [I]: effort limits at about 1.3× the voluntary set, scaled across digits by MyoHand's ratios.
  The kp values are graded MCP : PIP : DIP ≈ 1 : 0.6 : 0.25, the same split as the voluntary torques. Our earlier
  uniform squeeze curled the DIP at 4× the MCP force (`grasp/human-hand-biomechanics.md` §0.2).

Finger stiffness rises linearly with activation (Hajian & Howe 1997) and depends on posture and direction (Milner &
Franklin 1998) [L-abs]. I have no opened stiffness numbers. With the kp above, the index fingertip stiffness is
≈ 1 / Σ(r_j² / kp_j) ≈ 230 N/m [I]. So 1–3.5 cm of target "squeeze" (penetration of the reference finger into the
object) gives 2–8 N, which is why the kp scale is swept in §6.8.

### 3.3 Typical grip force on light household objects [I from L]

The static safety margin is **40–50 % of grip force** for objects ≥ 100 g (Hiramatsu 2015) [L]. For two-digit pinch
holds of an upright object, GF = m·g / (2μ) / (1 − 0.45):

| mass | μ 0.5 (dry skin) | μ 0.71 (sim pyramid worst case) | μ 1.0 (sim nominal) |
|---|---|---|---|
| 0.1 kg | 1.8 N | 1.3 N | 0.9 N |
| 0.3 kg (kit placeholder) | 5.4 N | 3.8 N | 2.7 N |
| 0.8 kg | 14.3 N | 10.0 N | 7.1 N |

Context:
- Measured skin–object friction at 200 g: sandpaper μ 1.32, rayon 0.71 [L].
- Grip force tracks load and adapts to friction within about 0.1 s; slip corrections take 60–80 ms (Johansson &
  Westling 1984) [L-abs].
- The index finger carries 42 % of static five-digit grip (Kinoshita 1995) [L-abs].
- Torque-dominated holds need far more: our LP found 1.4–21 N per contact for these objects at 0.3 kg
  (`grasp/human-hand-biomechanics.md` §0.1).
- Rule of thumb [I]: **contact forces above about 30 N per contact in a light-object replay are penetration
  artefacts, not human grip.**

### 3.4 Segment lengths, widths, ranges, mass

| quantity | value | source |
|---|---|---|
| Phalanx bone lengths (X-ray, 66 adults), PP / MP / DP mm | index 39.8 / 22.4 / 15.8; middle 44.6 / 26.3 / 17.4; ring 41.4 / 25.7 / 17.3; little 32.7 / 18.1 / 16.0 | Buryanov & Kotiuk 2010, via arXiv 2003.11598 Table 2.1 [L-sec] |
| MyoHand joint-centre lengths (MoBL adult), PP / MP / DIP→tip mm | index 42.6 / 25.1 / 27.1; middle 44.7 / 29.1 / 27.3; ring 40.4 / 24.9 / 27.6; little 36.1 / 21.0 / 24.7; thumb PP 31.1, IP→tip 31.5 | [M] |
| MCP joint spacing, index→little | 45.2 mm (17.5 / 15.8 / 15.5) | MyoHand [M] |
| Capsule radii, PP / MP / DP | MyoHand: index and middle 9 / 8 / 7, ring 8.5 / 7.5 / 6.8, little 8 / 7 / 6, thumb MC / PP / DP 9.5 / 8.5 / 6.5 mm; MC "skin" capsules 9.5–10 mm. HOIC: 10 / 9 / 8.5 (little 8 / 7 / 6; thumb 13 / 11 / 9) | [M] |
| Kinematic segment lengths from external hand length | models explain 49–99 % of variance; joint centres within 1.4 mm (Reuleaux) | Buchholz 1992 [L-abs] (coefficients not opened) |
| Active flexion ROM, MCP / PIP / DIP | 71–86° / 99–107° / 61–74° | Becker & Thakor, via arXiv 2003.11598 Table 2.3 [L-sec] |
| Joint ranges in models | MyoHand: finger MCP 0…90°, abd ±15°, PIP 0…90°, DIP 0…90°; thumb CMC flexion −45…40°, abduction −29…45°, MCP −45…40°, IP −75…25° | [M] |
| Hand mass | MyoHand carpals + MC + phalanges 0.44 kg [M]; HUG 0.40 kg [L]; D-Grasp 0.135 kg [M] | n/a |
| Finger pulp | compliant below about 1 N, stiffens rapidly above; viscoelastic | Serina 1997 [L-abs] |

### 3.5 Our perceived hand against these numbers [M + I]

Earlier notes give, from our perceived keypoints (`grasp/robot-thin-object-and-tool-grasping.md`, `evolution-scripts`):
- index digit (MCP→tip) 6.25 / 6.45 cm;
- thumb 8.6 cm;
- palm (index MCP → pinky MCP) 5.0–5.2 cm.

The ratio digit / palm is **1.2–1.3**. Expected values:
- MyoHand: 94.8 / 45.2 = 2.10 [M];
- bone-only lower bound: Buryanov index 78 mm / 45 mm ≈ 1.7 [I].

So the perceived palm is adult-sized but the fingers are 25–40 % short. This fits the work-log observations:
- the hand changes shape per frame (wrist→middle MCP 5.6–9.0 cm);
- stereo depth at hand pixels "hits the board the hand is holding" (work log, 21 Oct).

**[H-size]:** perception shortens fingers. Two ways to falsify it:
- in each public episode's 10 best frames (fingers extended, unoccluded, valid depth on all 4 finger points), median
  index MCP→tip is still < 7.5 cm;
- the anthropometric-length variant of §6.9 does no better than the perceived-length one.

## 4. Evidence: MANO-based vs simplified hands

- **No head-to-head study** of a MANO-mesh hand against a capsule hand on tracking success or contact realism was
  found [I].
- Closest evidence:
  - HUG built both from MANO and chose capsules for contact stability [L];
  - D-Grasp: primitives are 10× faster to train [L];
  - capsule/box hands drive successful physics HOI reconstruction (HOIC, from RGB-D tracking) and imitation (PhysHOI) [L];
  - V2P-Manip's Arti-MANO gain is attributed to skeleton and proportion match [L];
  - DexMachina: DoF over size (given).
- **[I]** For our study the surface model is second-order. The first-order factors are:
  - skeleton match to the source keypoints;
  - DoF;
  - bone lengths;
  - force limits;
  - contact count per pad.

  §6.9 makes the MANO question directly testable on our data.

## 5. Soft skin and torsion in a rigid simulator

| approach | used by | what we can do (study only, unless noted) |
|---|---|---|
| Raise μ to stand in for skin deformation | ManipTrans [L] | not available: μ is a global 1.0 in FlashCHORD |
| Allow penetration / soft contact | ContactOpt (interpenetration "to approximate deformable soft tissue", via our `contact-retargeting-2026-10-21.md`); QuasiSim spring–damper curriculum; HUG softer palm [L] | Per-shape solref → `ke/kd` exists in Newton [M]. Pad / palm `timeconst` 0.02–0.04 s, at least 2× the 10 ms physics step (MuJoCo docs) [L]. **Ablation only.** |
| Patch instead of point | MyoHand flat DP pads [M]; HOIC expands each contact into 4 points 2.5 mm apart (for its compensation force) [L] | **Allowed in the scored setting too (hand geometry):** 2–3 pad geoms per distal phalanx, since each geom pair gives one contact (§2.2). |
| Torsional friction (condim 4) | MuJoCo: "useful for modeling soft fingers, and can substantially improve the stability of simulated grasping"; coefficient in length units = "diameter of the surface contact patch". Equal priority → max of the two condims [L] | Hand shapes condim 4 with torsional ≈ 0.006 m: patch area 26–41 mm² at 5 N (Ciocarlie 2007, via our biomech note) → d ≈ 6–7 mm [I]. **Ablation only** (needs a harness change; not the scored contact model). |

## 6. Recommendation and build spec

### 6.1 Choice

**(b) Our own human-proportioned capsule hand, Apache-2.0**, in two size variants:
- **P**: perceived episode-median bone lengths;
- **A**: anthropometric template scaled by perceived palm size.

Variant A is the baseline if [H-size] holds. No MANO files are needed, so nothing is restricted by licence. MyoHand
and the papers supply numbers only, not files.

### 6.2 Kinematic tree (MediaPipe 21 = MANO 16 joints + 5 tips)

| body | parent joint (DoF) | from → to keypoints (MediaPipe index) |
|---|---|---|
| palm | wrist: kit floating base (3 prismatic + ball) | 0 → {1, 5, 9, 13, 17} fixed in the palm frame |
| finger PP (×4) | MCP: flex + abd (2) | 5→6, 9→10, 13→14, 17→18 |
| finger MP (×4) | PIP: flex (1) | 6→7, … |
| finger DP (×4) | DIP: flex (1) | 7→8, … (8, 12, 16, 20 are skin tips) |
| thumb MC | CMC: flex + abd + axial (3) | 1→2 |
| thumb PP | MCP: flex + abd (2) | 2→3 |
| thumb DP | IP: flex (1) | 3→4 |

Notes:
- 22 finger DoF, as Arti-MANO [M].
- Multi-DoF joints use dummy links of 1e-4 kg (kit idiom).
- Joint axes come from the anatomical frames that `pipeline/mkref.py` already builds from 21 MediaPipe joints (l.232).
- The palm frame is fixed at the episode-median MCP and CMC positions.

### 6.3 Segment shapes

- **Phalanges:** one capsule joint-to-joint. The DP capsule ends one radius short of the tip keypoint, so its cap lands
  on the tip. Radii in mm (MyoHand / HOIC, scaled by palm width / 45 mm):

  | | PP | MP | DP |
  |---|---|---|---|
  | index, middle | 9 | 8 | 7.5 |
  | ring | 8.5 | 7.5 | 7 |
  | little | 8 | 7 | 6 |
  | thumb | 9.5 (MC 11) | 8.5 | 7 |

- **Pads:** 2 extra spheres of r ≈ 4 mm on the volar side of each DP, 6 mm apart across the pad, offset so they sit
  flush with the DP capsule. Same for the thumb. This gives 2–3 contacts per pad.
- **Palm:**
  - 4 metacarpal capsules, r 10 mm, from base points about 4 cm proximal of each MCP keypoint along the
    wrist→MCP direction;
  - a thenar capsule (thumb MC);
  - one flat box under them (about 2.5 cm thick, HOIC 2.7 cm) to close the palm surface.
- **Mass:** about 0.4 kg total, split by volume (HUG / MyoHand). Gravity compensation on (kit default).

### 6.4 Limits (deg)

Start values:
- finger MCP flexion −30…90, abduction ±15 (index and little ±20);
- PIP 0…105; DIP −10…80;
- thumb CMC flexion −45…40, abduction −30…45, axial ±15; thumb MCP flexion −45…40, abduction ±10; IP −75…25 in
  MyoHand's sign convention.

Sources: MyoHand, Becker & Thakor, HOIC.

Then widen data-driven, as D-Grasp did: the [p0.5 − 10°, p99.5 + 10°] range of the angles our keypoints produce on the
public episodes, capped at the anatomical maximum.

### 6.5 Actuation

- Joint PD position targets with the kp and effort limits of §3.2.
- kd at 0.3–0.7 of critical, 2√(kp·I). The kit's 0.1 gives ζ ≈ 0.4 at kp 1.7, I 0.01 [I].
- Armature 0.01 kg m² (kit default; stable at 100 Hz). Also test 1e-3: stability needs I ≳ kp·dt² / 4 ≈ 4e-5 [I].
- Wrist: the kit's `stiff_tracking` gains (6000 N/m), so the hand goes where the video shows. Compare against the
  default 25 N/m.
- Exclude self-contacts between adjacent links, and between fingers at first: perceived poses interpenetrate.
- Hand–table contact off in the first pass (kit setting), on in a second pass.

### 6.6 Contact settings

- **Baseline:** the scored-run model unchanged (μ 1.0, condim 3, pyramidal cone, impratio 20).
- **Ablations, labelled as non-scored:**
  - soft pads (solref timeconst 0.03);
  - hand condim 4, torsional 0.006;
  - pads removed.

### 6.7 Driving from keypoints

1. Per frame, compute joint angles analytically from the keypoint anatomical frames:
   - flexion = bone-to-bone angle about the joint's flex axis;
   - MCP abduction = deviation of the PP from the metacarpal direction in the palm plane;
   - thumb CMC from the MC direction in the palm frame.
2. Refine with a damped least-squares fit of the five tips and the wrist pose (SPIDER-style: fingertips + 0.1 ×
   wrist rotation [L]).
3. Clip to the limits; low-pass at 10 Hz.

No IK basins arise: the hand *is* the keypoint skeleton.

### 6.8 Build and validation steps (CPU first)

1. `tools/human_hand/build_hand.py`: keypoints → median bone lengths → gate → URDF (Newton `<capsule>`). Variants P
   and A.
2. A `human_hands` embodiment copying `sharpa_hands._add_hand`, with per-joint `joint_overrides` from §3.2.
3. Static checks:
   - a flat hand on the table;
   - each joint driven to its limits;
   - a 0.3 kg box pinch-hold for 5 s at kp scale {0.5, 1, 2, 4}.

   Log per-contact normal forces against §3.3.
4. Replay on public episodes:
   - log the object-follow metric of §6.9 against the **perceived** object track;
   - log per-link contact forces;
   - log frames with forces above 30 N.

   GT is used only afterwards, as a diagnostic.
5. Record every run per CLAUDE.md.

### 6.9 Primary falsification test

**[H-rep]:** for object-follow physics, our capsule hand is not worse than a MANO-derived hand.

Setup:
- Both hands are run on our machines only, never shipped.
- Same 22 DoF, limits, gains, wrist drive and object URDFs.
- MANO hand: per-bone convex pieces from MANO's skinning, betas fitted to the same median bone lengths, driven by IK
  to the same 21 keypoints.
- 10 public episodes, fixed in advance.

Metric: the fraction of human-hold frames in which the simulated object stays within 2 cm and 15° of the perceived
object pose.

**Falsified if** the MANO hand's median is ≥ 10 points higher **and** it wins ≥ 7 of 10 episodes. In that case switch
to (a) for the study and keep its files local.

The same harness runs the secondary tests:
- **[H-size]:** variant A vs P; falsified if A ≤ P on the median.
- **[H-pad]:** 2-sphere pads reduce object rotation about the grip normal in torque-dominated holds (pot, boards) by
  ≥ 20 %; falsified otherwise.

## 7. Sources

- D-Grasp: https://arxiv.org/abs/2112.03028 (via ar5iv); repo https://github.com/christsa/dgrasp (`rsc/mano/mano_mean_meshcoll.urdf`, `raisimGymTorch/raisimGymTorch/env/envs/dgrasp/Environment.hpp`)
- ArtiGrasp: https://arxiv.org/abs/2309.03891
- ManipTrans: https://arxiv.org/abs/2503.21860 (PDF, suppl. D.1, D.3); repo https://github.com/ManipTrans/ManipTrans (`maniptrans_envs/lib/envs/dexhands/artimano.py`)
- V2P-Manip: https://arxiv.org/abs/2606.16436
- PhysHOI: https://arxiv.org/abs/2312.04393 · Omnigrasp: https://arxiv.org/abs/2407.11385 [L-abs]
- QuasiSim: https://arxiv.org/abs/2404.07988
- HOIC: https://arxiv.org/abs/2405.02676; repo https://github.com/hu-hy17/HOIC (`eval_model_tmp.xml`) · Hu 2022: https://arxiv.org/abs/2209.10833 [L-abs]
- DeepSimHO: https://arxiv.org/abs/2310.07206
- Garcia-Hernando 2020: https://arxiv.org/abs/2008.03285
- HUG: https://arxiv.org/abs/2606.17054 (App. E.1); repo https://github.com/KevinyWu/hug (MIT)
- SPIDER: https://arxiv.org/abs/2511.09484 · DexMachina: https://arxiv.org/abs/2505.24853 [L-abs]
- MyoSuite: https://myosuite.readthedocs.io/en/latest/suite.html; myo_sim https://github.com/MyoHub/myo_sim (README, LICENSE, `models/arm/README_hand.md`; files from PyPI myo-sim 0.2.3) · MyoDex: https://arxiv.org/abs/2309.03130 [L-abs]
- manotorch https://github.com/lixiny/manotorch · SMPLSim https://github.com/ZhengyiLuo/SMPLSim · Adroit https://github.com/vikashplus/Adroit · MANO licence https://mano.is.tue.mpg.de/license.html
- MuJoCo docs: https://mujoco.readthedocs.io/en/stable/computation/index.html (condim, torsional units, margin); https://mujoco.readthedocs.io/en/stable/modeling.html (parameter combination, timeconst ≥ 2·dt)
- MediaPipe Hand Landmarker (21 keypoints): https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker
- Valero-Cuevas, Zajac, Burgar 1998, J Biomech 31:693: https://valerolab.org/Papers/Valero-CuevasJOB1998.pdf
- Mohammadian et al. 2014, Iran J Public Health (PMID 25927041, PMC4411908), via Europe PMC full text
- Hiramatsu et al. 2015, PLoS One (PMID 26376484, PMC4574045), via Europe PMC full text
- [L-abs] PubMed: Mathiowetz 1985 (3970660); Buchholz 1992 (1572336); Westling & Johansson 1984 (6705863); Johansson & Westling 1984 (6499981); Kinoshita 1995 (7758447); Li 1998 (9551828); Serina 1997 (9391870); Hajian & Howe 1997 (9083857); Milner & Franklin 1998 (9805835)
- [L-sec] Buryanov & Kotiuk 2010 and Becker & Thakor 1988, tables in https://arxiv.org/abs/2003.11598

## 8. Reproduction of the [M] numbers

- Machine: this cloud session's container (CPU).
- MuJoCo 3.8.1 from the FlashCHORD venv.
- myo-sim 0.2.3 wheel from PyPI (sha256 prefix 259eb2bb9bbd7a48).
- Command: `docs/research/physics-2026-10-30/human-hand-scripts/run.sh <workdir> <python>`. `<python>` needs mujoco 3.8.1; the download uses the system `python3 -m pip`. Re-run on 2026-10-30: outputs identical to `out/`.
- It downloads myo-sim, D-Grasp's URDF and HOIC's XML as data, builds a hand-only MyoArm (39 hand muscles and their
  tendons), and runs:
  - `myohand_measure.py` (lengths, radii, mass);
  - `myohand_torque.py` (per-joint capacity at two postures);
  - `probe_dgrasp_hoic.py`.
- Outputs are in `human-hand-scripts/out/`.
- Kit facts (§2.2) were read from the installed `newton` 1.2.0 and `mujoco_warp` 3.8.1 sources and from the kit's
  `flash_chord` source. Line numbers are as cited.
