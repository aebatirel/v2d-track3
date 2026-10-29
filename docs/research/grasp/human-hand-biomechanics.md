# Human hand anatomy, biomechanics and grasp mechanics, applied to designed grasps for our failing objects

2026-10-24. CPU only (no rentals, no spending, no commits). Workflow `wf_cdd41283-528`, step "hand-biomech" of the owner's
option 2 ("one recipe, grasp-lock, with designed grasps; make sure the failures really are grasp failures"). Companion
reports in this folder: `audit-plates-ep18-ep39.md`, `audit-boards-ep24-sweeper-rack-ep31.md`, `rl-discovered-grasps.md`,
`learned-grasp-models.md`.

Labels:
- **[M]** measured by me from our references, meshes and simulator parameters (no ground truth);
- **[GT]** diagnostic that reads the organisers' public scan geometry, used only to describe the real object, never as an
  input to a design;
- **[L]** literature I opened (URL in §15; PubMed records were read through NCBI E-utilities because the PubMed web page
  sits behind a browser check here);
- **[I]** inference;
- **[H]** hypothesis, with the experiment that would falsify it (§14).

Every force number below uses the simulator's mass of **0.3 kg for every object** (kit placeholder in all URDFs [M]), a
safety factor 1.5 on the load, and friction 0.5 / 0.71 / 1.0. Required forces scale linearly with mass: a 0.15 kg board
needs half.

## 0. Answer

> **Correction, 2026-10-25 [M].** The "human grasp" column below and §9.2 read our 16 contact slots in MANO link order
> (palm, thumb1 … pinky3, the reference's `mano_link_names`). `pipeline/mkref.py` fills them in its probe order: five
> tips, five DPs, thumb MCP and finger MPs, then the palm. So "palm" was the thumb tip, "thumb1–3" were the index,
> middle and ring tips, and "pinky3" was the palm (`approach3-grasp-taxonomy.md` §9). Corrected census:
> `hand-biomech-out/slotfix-20261025/`; corrected table under §9.2. The text below is kept as written. Changes to the
> column:
> - **white_pot_lid:** palm **0.00**, not 76–80 % (that was the thumb tip). Thumb 0.80–0.89 with the middle, ring and
>   pinky tips and DPs: a thumb-and-fingers grip on the strap, reaching the rim.
> - **white_pot:** the palm sits near the handle end (−18 to −21 cm, share 0.61–0.94) and the thumb nearer the pot
>   (−11 to −15 cm). This is the reverse of "thumb near the end, palm near the base".
> - **mini_dust_pan:** thumb 0.19 (ep18), 0.51 / 0.31 (ep39 pick-up / carry); palm 0.02, 0.00 / 0.73.
> - **mini_sweeper:** thumb 0.14 (ep18) and 0.03 (ep31); the middle and ring tips and DPs hold it; palm 0.00.
> - **wooden boards:** in the f60–243 holds thumb 0.15 / 0.35 and palm 0.00 / 0.08; the f0–55 drag has palm 0.61.
> - **water_pitcher:** palm 0.93 (not 39 %), every digit 0.70–0.93: still a power grasp of the handle.
>
> Unaffected: the forces (§10, geometry and our object track), the tolerances, the failure verdicts, and the load
> columns of §9.2. The robot grasps stay hypotheses. Their human basis changes for the pot wrap (the palm, not the
> thumb, is at the far end) and for the lid (no palm in the human grip).

### 0.1 Per object

Columns:
- **human grasp** comes from our perceived MANO contacts [M], §9;
- **forces** are the minimal maximum normal force per contact over the whole human hold, from a friction LP
  along our reference motion [M], §10;
- **tolerance** is the hand-to-object position error the grasp can absorb at closure [M, geometry], §11.

| object (episodes) | human grasp [M] | robot grasp to build [H] | forces, N per contact (μ 0.5 / 0.71 / 1.0) | tolerance at closure | current failure a grasp failure? |
|---|---|---|---|---|---|
| **mini_dust_pan** (ep18 left, ep39; eval 19, 38) | Thumb vs middle/index clamp on the **ring handle**. Palm 13–44 %. Grip 5.9–7.5 cm from the COM. Tilts 56–88°, lifts 16–27 cm. | **Cage, then clamp:** index **through the ring hole** under the inner band; thumb pad (+PP) on top of the end band; middle under the end band. | **5.0–7.8** (single pinch: infeasible; key pinch across the band: 30–60) | ±0.7 cm along the handle (2.8 cm hole vs 1.4 cm finger), ±1.35 cm across | **ep18: yes** (no opposition; the fingers flick the pan from below). **ep39: no** (carrier merge deletes the pick-up), then yes (the designed grasp touches nothing). From the audits. |
| **mini_sweeper** (ep18 right, ep31; eval 19, 30) | Thumb (all segments) vs the middle finger's PP/MP across the ring's side band. Palm ≤ 7 %. Grip 6–7 cm. Tilts 30–58°, lifts 8–10.5 cm. | **Neck/head clamp spread over about 6 × 5 cm**: thumb column on one face, four fingers flat on the other (the grasp the successful RL found). Band clamp as second choice. | neck clamp **1.4–3.7**; band clamp 6.2–16.4; single pinch infeasible | ±1.2 cm normal, ±2–3 cm in the plane | **No** for both. ep18: hold timing and approach knocks. ep31: the brush is ejected from the rack hulls at step 1. |
| **wooden boards** (ep24; eval 25) | Drag with the palm on top. Then thumb on top, fingers under. Grip 4.6–10.8 cm from the COM. Tilts 28–100°. | **Pad opposition plus edge contact**: thumb DP directly opposite the index/middle/ring pads 3 cm in from the edge; thumb PP at the edge; fingers spread 4 cm. | **3.0–9.5** (single pinch: infeasible; thumb-at-edge-only cantilever infeasible once tilted) | ±1.4–1.6 cm normal, ±1.5 cm inward, ±5 cm along the edge | **Yes.** The clamp is never acquired: wrist lag 3–11 cm and fingers 2–5 cm off at closure. From the audit. |
| **water_pitcher** (ep21; eval 20) | Power grasp of the handle (palm 39 %, all digits). Grip 10.4 cm from the COM. Pour tilt 91°, lift 30 cm. | **Handle wrap** (medium wrap, thumb over the top). | **3.3–5.3** (hook alone: infeasible; one-station pinch: infeasible) | ±1.5 cm (handle 4–5 cm thick in our mesh) | **No.** The pitcher falls at f20, before any grasp (no flat bottom). The designed grasp would also fail: thumb-to-finger normal angle 38°, palm 81 mm off. |
| **white_pot_lid** (ep2; eval 1) | Palm over the **strap (bridge) handle** (76–80 %); fingers around the strap reaching the rim. Lift 4–6 cm, tilt 30–36°. | **Strap side pinch**: thumb on one side face, index + middle on the other, 2.4 cm apart. **Not** fingers under the strap in our mesh, whose gap is 1.5 cm vs a 1.4 cm robot distal phalanx. | side pinch **6.2–15.2**; hook under strap 1.9–4.0 (gap too tight); rim pinch 25–48 | side pinch ±1.3 cm across, ±2 cm along, ±0.7 cm in height; under-strap hook ±0.05 cm (ours) / ±0.4 cm (real lid, [GT]) | **No.** The lid starts 8 mm inside the pot's hulls and jumps 31 mm / 27°. The designed grasp is also weak: 52°, palm 95 mm. |
| **white_pot** (ep2, ep26; eval 1, 28) | Power grasp of the **16 cm stick handle**, thumb on top near the end (−18 cm), palm near the base (−12 cm). Grip torque 0.45–0.61 N m. ep26 flips the pot 180°. | **Medium wrap of the handle** between −13 and −21 cm: fingers under and around, palm on the side, thumb plus palm heel on top. Use the existing `wrap_grasp` on the handle. | wrap **4.0–10.2**; wrap only at the far end 9.6–21; end pinch infeasible | ±2 cm across, ±3.5 cm along | **No.** ep26: the pot is flung 117 mm by a start overlap. ep2: lid. The designed grasp is weak anyway: ep2 95°, palm 67 mm; ep26 no thumb. The wrap rule never fired: the whole-pot hull PCA ratio is 1.63, the rule needs ≥ 3. |

### 0.2 General findings

> **Correction, 2026-10-25 [M].** These findings come from the designed (robot-site) grasps (§9.3), the LP (§10) and
> the audits, not from the perceived contact labels, so they stand. The human claim that falls is §9.2's "thumb-vs-finger
> opposition in every hold": with the slot labels corrected (§0 note), the perceived thumb share on the plates, boards
> and sweepers is 0.03–0.35 in the §9.2 holds; the exception is the ep39 pick-up at 0.51. Across the approach-3 hold
> set it is 0.03–0.36 in 9 of 14 such holds (`approach3-scripts/out/digit_shares.txt`). The opposition may be there in
> the video; our perception does not show it.

- **Opposition separates success from failure** [M]. The designed (grasp-lock) holds that work have the thumb opposing
  the fingers: ep27 pot 160°, ep12 cup 124°. In 7–8 of the 9 failing holds the thumb is missing or the angle between the
  thumb and finger surface normals is below 100°. The range is 7–8 because the hull-based plates audit disputes the
  coarse site check on the ep18 sweeper. The clear exception is ep24 board 1 at 126°, which fails on acquisition.
  Method and caveats: §9.3.
- **The simulator has no torsional friction** (condim 3, pyramidal cone; [M] notes 24). Two consequences [M, LP, §10]:
  - a single opposing pair (thumb pad vs one finger pad) is infeasible for **every** observed hold of these objects:
    100 % of frames, at every μ;
  - moments must come from contacts spread by at least 2–4 cm, or from form closure (a finger through a hole, a wrap).

  Human hands do not have this limit: soft finger pads transmit tangential torques up to tens of N·mm, with grip force
  scaled to the torque (Kinoshita 1997 [L]).
- **The hand can supply these forces, but the uniform 0.4 rad squeeze cannot** [M]:
  - finger PD gain kp is 1.7 N m/rad;
  - 5–8 N at a fingertip needs Δq_MCP : Δq_PIP : Δq_DIP ≈ 0.31–0.49 : 0.17–0.27 : 0.08–0.12 rad;
  - a uniform 0.4 rad squeeze implies 26 N at the DIP against 6.5 N at the MCP, so the fingertip curls. That is why the
    thumb lifted 20 mm off the dust pan (audit).
- **Acquisition precision is the bottleneck** [M + audits]:
  - capture tolerances are 0.05–2 cm;
  - measured hand-to-object errors at closure with the soft wrist (kp 25) are 2–11 cm (ep24) and 5–8 cm (ep18 sweeper
    phantom);
  - so a designed grasp only works with the stiff wrist (kp 400) plus wrist ILC plus a slow, surface-normal final
    approach, and a gate on the closure error.
- **Literature corrections to our earlier notes** [L]:
  - The "Muzykewicz 2013, IP-first roll-up" citation in notes 24 could not be found; the only PubMed author of that name
    published in paediatric orthopaedics.
  - The MCP-first closing order is still supported, by a different paper. Braido & Zhang 2004 found a proximal-to-distal
    flexion sequence in 87 % of all trials, with 28 subjects doing cylinder grasps and single-finger flexion.
  - Somia et al. 1998 found the opposite for unrestricted simultaneous flexion: the DIP initiates flexion in the index,
    middle and ring fingers, and the most frequent sequence is DIP-PIP-MP.
  - The two studies disagree, so the closing order is not a settled anatomical fact. MCP-first remains an engineering
    rule supported by Braido & Zhang and by our own measurement (ep35 zero action 0.27 → 0.52, notes 24).
- **Is every failure a grasp failure? No** (§12). Only the ep18 dust pan and the ep24 boards fail primarily on the
  grasp. ep39, the ep18 sweeper, ep31, ep21, ep2 and ep26 fail first on reference construction or start-state physics.
  In ep39, ep21, ep2 and ep26 the designed grasp is also weak or empty, so it would become the next failure once the
  primary cause is fixed.

## 1. What our simulator and robot hand impose [M]

| quantity | value | source |
|---|---|---|
| contact friction | μ 1.0. Pyramidal cone: worst-case effective μ/√2 ≈ 0.71 for diagonal loads. condim 3, so no torsional or rolling resistance. | notes 24 (`tools/sim_physics_inventory.py`) |
| finger joints | PD kp 1.7 N m/rad, kd 0.1, effort 10 N m (the URDF's own efforts are smaller: MCP 1.86, PIP 0.64, DIP 0.19, thumb CMC 3.3 N m) | notes 24; `right_sharpawave.urdf` |
| hand kinematics (Sharpa Wave) | 22 DoF. Thumb: CMC FE −10…110°, CMC AA ±20°, MCP FE −30…80°, MCP AA ±20°, IP 0…100°. Fingers: MCP FE −10…90°, AA ±20°, PIP 0…100°, DIP 0…80°; pinky CMC 0…15°. | URDF |
| finger segments | index PP 4.7 cm, MP 3.15 cm, DP to tip 2.6 cm (lever MCP→tip 10.45 cm). Thumb CMC→MCP 6.5, MCP→IP 3.9, IP→tip 2.76 cm (13.2 cm). Link boxes: index DP 2.7 × 1.4 × 1.5 cm, MP 3.6 × 1.9 × 1.7, PP 4.5 × 1.9 × 2.2; palm 8.4 × 8.6 cm. Hand mass 1.24 kg, gravity-compensated. | URDF; plates audit |
| wrist | default kp 25 N/m (a 3 N load sags it 12 cm); `sharpa_hands_mid` kp 400 N/m (0.7 cm) | notes 24; embodiment yaml |
| hands vs table | **no collision** (`robot_support_collision: false`): fingers can pass under an object lying on the table | boards audit |
| object mass | 0.3 kg for every object (weight 2.94 N). Inertia from our mesh. | `make_assets.py`, all URDFs |

## 2. Hand anatomy that matters for grasping [L]

**Thumb CMC (trapeziometacarpal) saddle joint and opposition.**
- Its two rotation axes are fixed, **non-orthogonal and non-intersecting**: flexion-extension in the trapezium,
  abduction-adduction in the metacarpal (Hollister 1992, 7 cadaver thumbs; confirmed in vivo by CT in 44 subjects,
  Crisco 2015).
- Flexion is coupled with internal rotation (pronation) and ulnar translation, "a potential stabilizing screw-home
  mechanism" (Crisco 2015). That coupling is what turns the thumb pad to face the finger pads in opposition.
- The joint carries large loads (Cooney & Chao 1977):
  - with 1 kg applied at the thumb tip in simple pinch, joint compression averages 3.0 kgf at the IP, 5.4 at the MCP
    and 12.0 at the CMC;
  - tendons carry up to 10 kgf (extrinsic) and 30 kgf (intrinsic) in a pinch that produces 5 kgf at the tip, and up to
    50 kgf in grasp;
  - CMC compression can reach 120 kgf in a strong grasp.
- Ladd et al. 2013 stress the joint's micromotion and ligament stabilisers.
- Napier described the CMC's form and function in 1955 (J Anat 89:362–369; record only, I did not open the full text).

*Robot [M, I]:*
- The Sharpa thumb has a CMC FE of 120° but only ±20° of CMC abduction, and no pronation axis.
- Opposition therefore comes mostly from CMC FE plus the MCP AA (±20°).
- Grasps should be designed around the directions this thumb can oppose, not copied from the human thumb pose.

**Palmar arches.**
- The palm is a hollow formed by transverse, longitudinal and oblique arches; thenar and hypothenar motion shapes it
  during pre-shaping and contact (Sangole & Levin 2008, J Biomech).
- Palmar-arch modulation begins with arm transport (47 % of the change for a sphere, 64 % for a cylinder). In 60 % of
  trials it precedes MCP motion of the index and middle fingers (Sangole & Levin 2008, Exp Brain Res).

*Robot [I]:* the Sharpa palm is flat, except for the pinky CMC (0–15°), so a palm "cupping" a handle is not available.
Wraps must close with the fingers and the thumb.

**Finger pad (pulp) compliance and friction.**
- The pulp is viscoelastic and **compliant below about 1 N**, then stiffens rapidly; the loading angle matters
  (Serina, Mote & Rempel 1997, 20 subjects).
- The pressure distribution under a flat probe is an inverted paraboloid, with exponential stiffness and relaxation
  (Pawluk & Howe 1999).
- Pads behave like rubber, not like hard solids: **the friction coefficient falls as normal force rises**, and friction
  rises with contact area (Warman & Ennos 2009).
- Consequence for humans: the contact patch transmits a **frictional torque** about the contact normal, and grip force is
  scaled to it (§5).

*Robot [M]:* the simulator models the elastomer pads as rigid convex pieces with soft-constraint contacts and no
torsion.

**Tendons, muscle synergies and finger independence.**
- **Enslaving** (involuntary force in non-instructed fingers) is large: up to 67.5 % of a finger's own maximum, larger
  for neighbouring fingers (Zatsiorsky, Li & Latash 2000).
- Middle and ring fingers are the least individuated (Häger-Ross & Schieber 2000). Causes: multi-tendoned flexors
  (FDP, FDS), passive inter-digit links, distributed neural control.
- Postural synergies: when shaping the hand for a large number of familiar objects, **the first two principal
  components of 15 joint angles explain > 80 % of the variance**. Higher components still carry object-specific detail. Posture appears to be
  controlled separately from contact forces (Santello, Flanders & Soechting 1998). Santello et al. 2016 review the
  robotics use of synergies (I read the authors' reply, PMID 27344306).

*Robot [I]:*
- A grasp search can work in a 2–3-D synergy space plus a few contact-placement parameters (relevant to the
  evolutionary-search step).
- Force must be designed separately from posture: the squeeze of §10 and §11.

## 3. Grasp taxonomies [L]

- **Napier 1956.** Two patterns: precision grip (object pinched between the flexor surfaces of the fingers and the
  opposing thumb) and power grip (object clamped between the flexed fingers and the palm, the thumb counter-pressing).
  The purpose of the action decides the form. Napier's dichotomy is restated in the opened abstract of Young 2003 (the
  1956 paper itself: record only).
- **Kamakura 1980.** 7 subjects × 98 objects, photographed from 5 directions. 14 static prehension patterns: 5 power,
  4 intermediate, 4 precision, 1 other. 86 % of grips fit one pattern; 67 of 98 objects were grasped in 2 or more
  patterns.
- **Cutkosky 1989** (IEEE TRA 5:269–279; not opened, paywalled). Taxonomy from observing machinists. Feix 2016 includes
  it among the 22 taxonomies it merges.
- **Feix et al. 2016, GRASP taxonomy** (opened):
  - 22 taxonomies merged into **33 grasp types**, reducible to **17** when only hand shape matters;
  - arranged by opposition type: **pad** (force parallel to the palm), **palm** (perpendicular to the palm), **side**
    (along the transverse axis);
  - also by virtual-finger assignment, power / intermediate / precision, and thumb **abducted** (opposes the finger
    pads) or **adducted** (presses on the side of the fingers, or is out of the way);
  - gravity-dependent grasps (**hook**, flat hand, platform) are excluded from the definition. **Fixed hook (#15) is
    included.**
  - Most consistently named type across authors: the **lateral grasp (#16)**, classified as power by some authors and
    intermediate or precision by others.
  - Frequencies in housekeepers and machinists: medium wrap #3 12.7 %, lateral #16 8.9 %, tripod #14 8.4 %, precision
    disk #12 7.1 %, lateral tripod #25 10.4 %, parallel extension #22 2.0 %, fixed hook #15 0.4 %.
- **Feix, Bullock & Dollar 2014a** (about 10,000 grasp instances):
  - 92 % of objects weigh ≤ 500 g;
  - 96 % of grasp locations are ≤ 7 cm wide;
  - in 94 % of instances the **smallest dimension is grasped**;
  - the most versatile grasps are the **medium wrap** (median object 400 g, grasp size 4.5 cm), then the **lateral
    pinch** (median 150 g, 2 cm), then the thumb-2-finger grasp (105 g, 1 cm).
- **Feix 2014b:**
  - grasp type is predicted at only 47 % from object size, task constraints and mass;
  - even objects < 2 cm and < 20 g get precision grasps only 61 % of the time;
  - in about 60 % of instances the grip force is set by the object's weight;
  - the optimal handle diameter is **22–32 mm** (Tilley, quoted there).
- **Bullock, Ma & Dollar 2013.** A hand-centric manipulation classification: contact / no contact, prehensile /
  non-prehensile, motion / no motion, within-hand / not, motion at contact or not.
  - The board drag in ep24 (palm on top, sliding) is a **non-prehensile, motion-at-contact** action.
  - Every hold of a grasp-lock reference is **prehensile, no within-hand motion**.
  - This is a type change the locked grasp cannot represent (the human changes grasp 3–4 times on board 1; boards
    audit).

**Mapping to our objects** [M + L]:

| object | human grasp observed (§9) | nearest GRASP type(s) |
|---|---|---|
| dust pan, sweeper (ring handles) | thumb vs middle/index across the handle band | lateral #16 / prismatic-2-finger #8 (pad or side opposition) |
| boards | palm-on-top drag, then thumb on top + fingers under | non-prehensile drag, then parallel extension #22 or pad opposition |
| pitcher handle | all digits around the handle, thumb over | medium wrap #3 (fixed hook #15 when the thumb is off) |
| pot stick handle | handle across the palm, thumb on top near the end | medium wrap #3 / adducted thumb #4 |
| lid strap | palm over the strap, fingers around | power grasp of a strap (closest: fixed hook #15 / prismatic 4-finger #6). **Not** the precision disk #12 on the rim. |

## 4. Reach-to-grasp kinematics and closure order [L]

- **Transport and grip.** Transport has a fast phase, then a low-velocity phase that starts at about **75 % of movement
  time**. The fingers first open, then begin to close in anticipation of contact. **Closure onset correlates with the
  start of the low-velocity phase** (Jeannerod 1984, 7 subjects).
  - Both object size and distance affect both components.
  - Without visual feedback, hands open wider but still scale with size: a strategy for tolerating errors (Jakobson &
    Goodale 1991).
- **Digits move to chosen contact points and approach the surface roughly orthogonally** (Smeets & Brenner 1999,
  minimum-jerk model).
  - Model slope of maximum grip aperture vs object size: **0.81** (0.88 with a velocity constraint).
  - Maximum opening for small objects occurs at 60–67 % of the movement (Smeets & Brenner 1999 response).
  - Re-examined favourably in 2009 (Smeets, Brenner & Martin).
- **Finger paths.** Fingertip trajectories during reach-to-grasp follow a **logarithmic spiral** per subject (error 0.23
  ± 0.25 cm, > 98 % of variance). Different object sizes use different portions of the same path. The thumb path
  depends more on the object (Kamper, Cruz & Siegel 2003).
- **Joint order:**
  - cylinder grasping plus single-finger flexion (28 subjects): **proximal-to-distal flexion in 87 % of all trials**;
    two PCs explain ≥ 98 % of joint variance (Braido & Zhang 2004);
  - unrestricted simultaneous flexion: motion starts in a single joint in 83 % of cycles; the DIP initiates in index,
    middle and ring (most frequent DIP-PIP-MP), the PIP in the little finger (Somia et al. 1998);
  - the two disagree, and neither measured closure onto a free object lying on a table;
  - Landsmeer 1963 is the classic analysis of finger-joint coordination (record only).

*Design rules* [I]:
- (a) Start closing at the end of the approach, not during transport.
- (b) Pre-open to the grasped thickness plus twice the tolerance of §11. Humans scale aperture about 0.8 × size, plus a
  margin that grows with uncertainty.
- (c) Final approach along the contact normals.
- (d) MCP-led closure for wraps and hooks (the Braido & Zhang grasping order). Simultaneous thumb and finger contact for
  pinches (§6.4 of the plates audit; RL-found grasp: thumb and index in the same frame).

## 5. Grip–load coupling, safety margins and slip [L]

- **Grip force follows load force in parallel** and is **adapted to friction**: the more slippery the surface, the higher
  the grip force at a given load. The ratio is set within about **0.1 s** of contact from cutaneous input. Small slips
  trigger corrective increases **60–80 ms** later, and the new ratio is remembered (Johansson & Westling 1984).
- The **safety margin** (applied grip minus the minimal non-slip grip) is small but individual. It depends on weight,
  friction and the previous trial's friction (Westling & Johansson 1984).
- Force rates are **programmed from the expected weight** (previous lift). Wrong expectations are corrected by
  somatosensory events at lift-off; unloading after replacement is also triggered by contact (Johansson & Westling
  1988).
- **Anticipation (feed-forward).** During arm movements with inertial, viscous and elastic loads, **grip force is
  modulated in parallel with, and anticipates, load force** under every load (Flanagan & Wing 1997). This holds for all
  grips, including two-handed, inverted and whole-body jumping (Flanagan & Tresilian 1994).
- **Torques.** Tangential torques (0–50 N·mm) raise the minimal slip force in proportion, with a slope set by friction.
  Torque and force effects are roughly additive, and the safety margin stays constant (Kinoshita, Bäckström, Flanagan &
  Johansson 1997).
  - When tilting objects (65° about the grip axis), grip force rises linearly with tangential torque. The slope grows
    with surface curvature (concave r 20 mm to convex r 5 mm) and keeps an adequate margin against rotational slip
    (Goodwin, Jenmalm & Johansson 1998).
- **Friction scaling.** The background grip, and both fast and slow responses to pulling loads, scale with **inverse
  friction**; friction is read on contact (Cole & Johansson 1993).
  - In three-digit lifts each digit's normal:tangential ratio is set to its **local** friction. Load distribution
    follows the geometry of the COM relative to the contacts (Burstedt, Flanagan & Johansson 1999).
  - In multi-finger prehension the static grip shares are index 42.0 %, middle 27.4 %, ring 17.6 %, little 12.9 %,
    constant across 200–800 g (Kinoshita, Kawai & Ikuta 1995).
  - In maximal cylinder grasps the shares are 30 / 30 / 22 / 18 % (Amis 1987).
- **Feedback dependence.** With digital anaesthesia the static safety margin rises, but grip decays over 20–30 s.
  Objects were dropped in 36 % of trials and slipped in a further 12 %, against 0 % with sensation (Augurelle et al.
  2003).
- **Margins are statistical.** The safety margin scales with the expected **variability** of the load, like a fixed
  statistical risk of slip; the authors' framing is 2–3 SD (Hadjiosif & Smith 2015).

*Design rules for a zero-action reference* [I]:
1. The squeeze is **feed-forward and scheduled with the load** derived from our reference (as `grasp_force.py` does).
   Ramp it up **before** each acceleration peak or tilt (lead of at least 2 frames = 100 ms, at least the human slip
   latency), and keep it high during tilts.
2. A zero-action reference has **no slip reflex**. The margin must cover the evaluator's variability. Our replays vary
   by 0.13–0.41 AUC between evaluations of one policy (STATUS), so a 1.5–2 × factor on the LP minimum is a floor, not
   a ceiling. The RL fine-tune can add a learned reflex (20 Hz policy = 50 ms per step, close to human reflex latency).
3. **Torque-dominated holds need much more grip than weight-dominated ones** (Kinoshita 1997). Without torsional friction
   in the simulator, torque must be carried by spread contacts (§7), never by "more squeeze" on one pair.

## 6. Skin friction and soft-finger contact [L] vs the simulator [M]

- Skin friction depends on probe material, geometry and smoothness, hydration and anatomical site. More water or
  moisturiser raises it; dryness and alcohol lower it (Sivamani et al. 2003).
- Dry skin: **μ > 0.2, typically about 0.5**, independent of pressure. Moist or wet skin: **typically > 1**, rising as
  contact pressure falls. The adhesion friction model bounds most data (Derler & Gerhardt 2012, review).
- Hydration also changes the stick-to-slip transition: the stuck fraction of the contact falls linearly from 1 to 0 as
  tangential force rises. Dry skin is less stable, which explains exaggerated grip forces (André et al. 2011).
- **Soft-finger contact.** A finite patch supports a frictional moment about the normal. The force-torque coupling is a
  friction ellipsoid f_t² + τ_n²/e_n² ≤ μ²P². For 5 N per contact, elastic-foundation patches of 26–41 mm² give the
  thumb about 30 % more torque capacity than the ring finger (Ciocarlie, Lackner & Allen 2007).
- Modern Robotics (Lynch & Park 2017) defines the **soft contact** as a point contact with friction plus no relative
  spin about the normal.

**In our simulator** [M]:
- μ = 1.0 sits inside the human range for moist skin, but the 4-edge pyramid gives an effective 0.71 for diagonal loads;
- there is **no torsion** (condim 3), so every contact is a hard point contact with friction;
- I therefore report forces for μ 0.5 (dry human), 0.71 (simulator worst case) and 1.0 (simulator nominal).

## 7. Grasp mechanics [L]

- **Force closure.** A grasp is force-closure iff arbitrary force and moment can be exerted through the contacts.
  Equivalently, the object cannot break contact without non-zero external work (Nguyen 1985, MIT AI memo; constructive
  algorithms for independent contact regions; the IJRR 1988 paper was not opened).
- **Form closure.** At least **4** point contacts for a planar body and **7** for a spatial body. Surfaces of revolution
  are "exceptional" and can never be form-closed (Lynch & Park 2017, Theorem 12.6).
  - **Two frictional point contacts cannot give force closure in 3-D: no moment about the line joining them.** Three
    non-collinear frictional contacts can (Lynch & Park 2017, §12.2).
  - This is the mechanical reason our single-pair pinches are LP-infeasible (§10).
- **Grasp quality** (Ferrari & Canny 1992): the radius of the largest ball, centred at the origin, inside the convex hull
  of the contact wrenches. L∞ (bounded maximum finger force) or L1 (bounded total force); friction cones approximated
  by pyramids. My LP is the per-frame version: the minimal maximum normal force to resist the task wrench.
- **Caging** bounds an object's mobility without immobilising it. For two-fingered hands every cage is a
  "pregrasping cage": squeezing or stretching reaches a grasp without breaking the cage. This does not hold for three
  or more fingers (Rodriguez, Mason & Ferry 2011).
  - For our ring handles and loops, a finger through the hole plus the thumb is a two-finger cage. Closing it cannot
    lose the object, so the grasp tolerates position and force errors.
- **Wrap and capstan.** For a flexible band, the capstan law F_L = F_0·e^{μφ} (φ = wrap angle) explains why wrapping
  multiplies holding capacity, though it is "not adequately ratified by experiments" for real rods (Singh 2022).
  - For rigid segmented fingers the right model is the multi-contact LP over contacts spread around the handle (§10):
    capacity grows with the number and angular spread of contacts, not exponentially [I].
- **Handle size and power-grip forces:**
  - maximal grip force vector magnitude rises 34.8 N from 2.54 to 3.81 cm diameter, then falls 103.8 N up to 7.62 cm
    (61 participants; Edgren, Radwin & Irwin 2004);
  - total normal force on the handle is **2.3 ×** the split-cylinder grip force for 38–83 mm handles (Seo & Armstrong
    2008);
  - normal forces decrease with diameter, and distal phalanges carry the largest share (Amis 1987).
  - Our pot handle (3.0 × 2.5 cm) is within the optimal 22–32 mm. Our pitcher handle (4–5 cm, thickened by the
    reconstruction) is not [M].

## 8. Picking up and holding flat or thin objects and tool handles [L], and what differs in our simulator [M]

**Flat objects lying on a table:**
- Humans exploit the environment: the fingers make **support contact** with the table, slide the object to an edge and
  grasp the overhang, or **flip** it by anchoring one finger and pulling with another. One participant slid a button to
  the edge in all 10 trials; another flipped it (Eppner et al. 2015).
- Robots: slide-to-edge succeeded for all block sizes, while compliant closing worked only on flat blocks (Barrett
  hand).
- "Several objects cannot be grasped from the top when lying on a hard surface, e.g., flat or small objects … we
  typically grasp them with a flip or a slide-to-edge grasp" (Bimbo et al. 2019, citing Puhlmann et al. 2016).
  Strategies:
  - **Continuous Slide-and-Grasp** (palm on the object, slide to the edge, close the fingers under it) suits small
    flats;
  - **Pivot-and-Re-grasp** suits larger ones;
  - 320 trials, 16 objects; success ≥ 60 % per object with the better strategy (toolcase 90 / 80 %, rubber plate
    60 / 80 %).
- Planning the pre-grasp slide in configuration space with a compliant underactuated hand: Hang, Morgan & Dollar 2019.
- For small objects, contact with the support surface is critical. A force-compliant "landing" of the fingers on the
  table, then compliant closing, is robust to localisation error (Kazemi et al. 2012).
- What the human did in ep24 (boards audit): drag palm-on-top → slide past the table edge → fingers under the
  overhang, thumb on top → turn the board vertical (a second grasp) → stand it on its edge. No flip, no lateral pinch.

**Tool handles:**
- Grasp choice depends on the end goal: the placement of individual digits changes with object shape and with the goal
  (pour vs move), even for the same bottle (Sartori, Straulino & Castiello 2011).
- A **pitcher** is therefore held in a power grasp of the handle with the thumb over it. A pure hook (thumb off) is only
  for carrying upright [I + §9].
- A **lid with a strap handle** is lifted by the strap (our ep2 human: palm over the strap).
- A **pan** with a stick handle is held in a power grasp, the handle across the palm, the thumb on top [M §9].

**What differs in our simulator** [M]:
- **The hands do not collide with the table.** Fingers can be placed directly under a board or plate lying on the table,
  so the slide-to-edge is **not physically needed for the robot hand**.
  - The object, however, collides with the table. If fingers below a free object close before anything holds it from
    above, they **scoop or flick it** (dust pan: 63–80 mm / 17–22° at closure in 4 of 4 replays; plates audit).
  - The scored object path still contains the human's drag and slide (we track the object, not the hand). A board
    clamped where it lies can follow the drag with the hand, against table friction μ_t·m·g ≈ 2.9 N [I].
- **Our meshes are thicker than the real objects** [GT]:
  - plates 1.2–2.5 cm vs 0.4–0.8 cm;
  - the lid disk is 1.8 cm against 1.1 cm in the scan, and the gap under its strap is **1.5 cm against 2.2 cm**;
  - the sweeper's ring hole is 1.7–3.0 cm against 3.9 cm.

  Grasps that thread fingers through holes or gaps must be designed on our meshes, not on the real objects.

## 9. How the human holds our failing objects (measured from our references) [M]

### 9.1 Method

`hand-biomech-scripts/human_grasp_census.py` runs on our perceived references (`refs/perc2mck*`, MANO hands + perceived
object poses; no ground truth). For each run of frames with MANO contacts on an object, it reports:
- the per-link contact share;
- where the thumb, fingers and palm touch, in the object's PCA frame with the COM at the origin, plus the side of the
  thin axis;
- the task load along our object track (Savitzky–Golay derivatives, 0.3 kg): |F| = |m(a − g)|, p95 acceleration, the
  torque about the human contact centroid ("grip torque"), the tilt from the start of the hold, and the lift.

Contact plots (`contact_plot.py`) are in `hand-biomech-out/ct_*.png`.

Caveats:
- the perceived hand is noisy to about ±1–2 cm;
- MANO contact labels can start late (ep18 sweeper: 22 frames late, plates audit);
- in ep24 our reference names the boards opposite to the boards audit's naming (twin pieces).

### 9.2 Results

> **Correction, 2026-10-25 [M].** The "link shares" and "where" columns and the last reading below use MANO link
> labels, which do not describe our slots (§0 note). They are kept as written; the corrected table follows the readings.

| episode, hand, object | frames | link shares (≥ 0.5) | where | max load force N | acc p95 m/s² | grip torque med / max N m | tilt max ° | lift cm |
|---|---|---|---|---|---|---|---|---|
| ep18 L dust pan | 9–186 | thumb2/3 0.69/0.75, index1 0.83, middle1-3 0.69–0.92; palm 0.13 | ring region (pca1 −5 to −10 cm); thumb and fingers on opposite faces (thumb contact normals 72 % toward −thin, fingers 67 % toward +thin) | 3.46 | 1.60 | 0.16 / 0.20 | 66 | 16.1 |
| ep39 L dust pan (pick-up) | 35–102 | thumb1/2 0.85/0.94, middle1-3 0.60–0.79; palm 0.44 | ring (pca1 −4 to −9) | 3.47 | 1.28 | 0.21 / 0.23 | 56 | 20.7 |
| ep39 R dust pan (carry) | 104–292 | thumb2/3 0.71/0.87, index1 0.65, middle1 0.55, pinky3 0.73; palm 0.26 | ring | 3.31 | 1.19 | 0.21 / 0.24 | 88 | 27.0 |
| ep18 R sweeper | 60–225 | thumb2/3 0.85/0.86, middle1/2 0.86/0.78; palm 0.07 | ring and neck (pca1 −3 to −8) | 3.45 | 2.43 | 0.07 / 0.15 | 58 | 8.4 |
| ep31 R sweeper | 25–264 | thumb1-3 0.70–1.00, middle2 0.66 | ring (pca1 −5 to −8) | 3.22 | 0.89 | 0.08 / 0.11 | 30 | 10.5 |
| ep24 board (left hand) | 60–201 | thumb1/3 0.82/0.84, index3 0.90, middle1/2 0.89/0.94, ring3 0.85, pinky1 0.77 | short edge, 10–11 cm from the COM; thumb on one face (92 %), fingers on the other | 3.19 | 0.72 | 0.30 / 0.33 | 66 | 23.4 |
| ep24 board (right hand) | 102–243 | thumb1-3 0.75–0.77, middle1/2 0.78/0.73; palm 0.25 | corner region, 8–9 cm from the COM | 3.57 | 1.69 | 0.24 / 0.32 | 101 | 25.4 |
| ep21 R pitcher | 13–134 | all digits 0.25–0.93, pinky3 0.93, thumb2 0.81; palm 0.39 | handle (`ct_ep21_pitcher.png`) | 3.46 | 1.53 | 0.30 / 0.36 | 91 | 29.6 |
| ep2 R lid | 45–135, 234–303 | palm 0.76–0.80, thumb3 0.79–0.90, index1 0.69–0.90, middle1/2 0.73–0.97 | palm over the strap; fingers around the strap and over to the rim (`ct_ep2_lid.png`) | 3.22–3.44 | 1.45–1.54 | 0.11–0.14 / 0.13–0.15 | 30–36 | 3.6–5.7 |
| ep2 L pot | 36–233 | palm 0.58, thumb2/3 0.57/0.54, index2 0.69, ring2 0.62, pinky3 0.94 | stick handle: thumb on top at −18 cm, palm at −12 cm, fingers −12 to −21 cm (`ct_ep2_pot.png`) | 3.28 | 2.17 | 0.46 / 0.53 | 12 | 10.8 |
| ep26 R pot | 36–118 | palm 0.60, index1 0.63, pinky3 0.61 | handle −13 to −24 cm, thumb at −20 cm (`ct_ep26_pot.png`) | 3.49 | 1.80 | 0.52 / 0.61 | 180 | 19.1 |

Readings [M]:
- All loads are small: |F| ≤ 3.6 N, about 1.2 × weight.
- What differs is the **lever**:
  - pot 16–18 cm → 0.45–0.61 N m;
  - pitcher 10 cm → 0.30–0.36 N m;
  - boards 9–11 cm → 0.24–0.33 N m;
  - pan 6–7.5 cm → 0.16–0.24 N m;
  - sweeper and lid → ≤ 0.15 N m.
- And the **tilt**: 30–180°, which turns gravity into the plane of plates and along handles. Both demand
  moment-resisting, multi-contact layouts.
- Humans use **thumb-vs-finger opposition in every hold**. The palm is used heavily only for handles (pot 0.58–0.60,
  lid strap 0.76–0.80, pitcher 0.39) and rarely for plates (0.07–0.44).

**Corrected table, 2026-10-25 [M].** Same references, holds and code, with slots labelled in mkref's probe order
(`human_grasp_census.py` after the fix; `hand-biomech-out/slotfix-20261025/census_ep*.txt`, plots `ct_*.png` there).
Digit share = fraction of the hold's frames in which any slot of that digit touches the object. The load columns
(force, acceleration, grip torque, tilt, lift) are identical in all 24 holds and are not repeated.

| episode, hand, object | frames | digit shares: thumb / index / middle / ring / pinky / palm | slots ≥ 0.5 | where (group means, object PCA frame) |
|---|---|---|---|---|
| ep18 L dust pan | 9–186 | 0.19 / 0.39 / 0.89 / 0.92 / 0.94 / 0.02 | pinky DP 0.92, pinky tip 0.83, ring tip 0.75, middle DP 0.72, middle tip 0.69, ring DP 0.69 | fingers at the ring (pca1 −5.6 cm). Thumb only 49 contacts. Thumb and finger normals point to the same side (76 % / 56 % toward +thin): no opposite-face clamp |
| ep39 L dust pan (pick-up) | 35–102 | 0.51 / 0.93 / 0.99 / 0.93 / 0.65 / 0.00 | middle tip 0.94, index tip 0.85, ring DP 0.79, middle DP 0.69, pinky DP 0.60 | ring; thumb at the ring end (pca1 −9.7), fingers −6.6 |
| ep39 R dust pan (carry) | 104–292 | 0.31 / 0.54 / 0.89 / 0.90 / 0.69 / **0.73** | ring tip 0.87, palm 0.73, middle tip 0.71, pinky tip 0.65, middle DP 0.55 | palm at the ring end (−9.9), fingers −7.1, thumb −6.1 |
| ep18 R sweeper | 60–225 | 0.14 / 0.40 / 0.93 / 0.92 / 0.45 / 0.00 | ring tip 0.86, middle DP 0.86, middle tip 0.85, ring DP 0.78 | ring and neck (fingers −5.9); thumb 29 contacts |
| ep31 R sweeper | 25–264 | 0.03 / 0.70 / 1.00 / 0.98 / 0.04 / 0.00 | middle tip 1.00, ring tip 0.97, index tip 0.70, ring DP 0.66 | ring (−7.0); thumb 7 contacts |
| ep24 board (left hand) | 60–201 | 0.15 / 0.92 / 0.95 / 0.96 / 0.13 / 0.00 | ring DP 0.94, index DP 0.90, middle DP 0.89, middle MP 0.85, ring tip 0.84, index tip 0.82, ring MP 0.77, index MP 0.63 | short edge, 10.2 cm from the COM; thumb 27 contacts, no face split (44 % / 53 % +thin) |
| ep24 board (right hand) | 102–243 | 0.35 / 0.85 / 0.84 / 0.78 / 0.05 / 0.08 | middle DP 0.78, index / middle / ring tips 0.75–0.77, ring DP 0.73 | corner region, fingers 8.0 cm from the COM, thumb 6.4 |
| ep21 R pitcher | 13–134 | 0.70 / 0.75 / 0.93 / 0.84 / 0.80 / **0.93** | palm 0.93, middle tip 0.81, index MP / tip / DP 0.61–0.66, middle MP 0.60, middle DP 0.57, ring MP 0.57, ring tip 0.54 | handle; palm at pca1 −13.3, thumb −7.9 |
| ep2 R lid | 45–135, 234–303 | **0.89 / 0.80** thumb; index 0.48 / 0.44; middle 0.82 / 0.94; ring 0.82 / 0.99; pinky 0.71 / 1.00; **palm 0.00 / 0.00** | thumb tip 0.76 / 0.80, ring tip 0.79 / 0.90, ring DP 0.78 / 0.97, middle DP 0.73 / 0.94, pinky tip 0.69 / 0.90 | thumb on top of the strap, fingers around the strap and over to the rim (`slotfix-20261025/ct_ep2_lid.png`) |
| ep2 L pot | 36–233 | 0.80 / 0.72 / 0.61 / 0.57 / 0.47 / **0.94** | palm 0.94, thumb DP 0.69, index MP 0.62, thumb tip 0.58, middle tip 0.57, ring tip 0.54 | stick handle: **palm at −18.4 cm (near the end), thumb at −12.9 cm**, fingers −16.7 cm |
| ep26 R pot | 36–118 | 0.60 / 0.64 / 0.63 / 0.52 / 0.63 / 0.61 | pinky tip 0.63, palm 0.61, thumb tip 0.60 | handle: palm at −20.6 cm, thumb at −11.2 cm, fingers −19.2 cm |

Corrected readings [M]:
- The loads and levers above stand.
- **No measured thumb-vs-finger opposition.** The perceived thumb share on the plates, boards and sweepers is 0.03–0.35
  (ep39 pick-up 0.51). The pan and board holds show no thumb-vs-finger face split. Thin features (0.8–2.3 cm) are at or
  below our hand error (±1–2 cm), so the thumb may be there in the video and missed by our perception
  (`approach3-grasp-taxonomy.md` §2).
- **Palm:** heavy on the handles of the pot (0.61–0.94) and the pitcher (0.93), and in the ep39 carry (0.73). It is
  absent on the lid strap (0.00), the sweepers (0.00) and the ep18 pan (0.02).

### 9.3 The designed (grasp-lock) grasps vs. the human ones [M]

`designed_grasp_check.py`:
- **Method:** tip, DP, MP sites and the palm frame of the grasp-lock reference (`ref_gl.parquet`: the PD targets,
  including the squeeze) against our mesh, at closure and mid-hold.
- **Opposition angle:** the angle between the mean surface normals under the thumb sites and under the finger sites
  (180° = fully opposed).
- **Coarse check:** site points only. Where it differs from the hull-based audits, the audits take precedence: for the
  ep18 sweeper the plates audit finds middle/ring/little MP on the −face, which site points miss.

| hold | outcome | thumb sites / finger sites within 12 mm | opposition angle | palm frame to surface |
|---|---|---|---|---|
| ep27 R pot | success (0.957–0.972) | 2 / 3 | **160°** | 38 mm |
| ep12 R blue cup | success (0.854–0.910) | 1 / 4 | **124°** | 85 mm |
| ep18 L dust pan | fail | 0 / 0 | – | 133 mm |
| ep18 R sweeper | fail | 2 / 0 | – (audit: clamp type, never reached) | 122 mm |
| ep39 R dust pan | fail | 0 / 0 | – | 124 mm |
| ep24 L board | fail | 1 / 5 | 126° | 55 mm |
| ep24 R board | fail | 1 / 6 | 72° | 84 mm |
| ep31 R sweeper | partial (RL fixes the grasp) | 1 / 2 | 18° | 103 mm |
| ep21 R pitcher | fail | 2 / 8 | 38° | 81 mm |
| ep2 L pot | fail | 2 / 8 | 95° | 67 mm |
| ep2 R lid | fail | 2 / 2 | 52° | 95 mm |
| ep26 R pot | fail | 0 / 7 | – | 76 mm |

- The copied ("snapped") human grasps on handles and plates come out without opposition, because the human's
  perceived fingers sit 1–2 cm off and the snap moves fingers, not the thumb's opposition direction [I].
- The **wrap rule never fires on the pot**: `wrap` is null in ep2, ep26 and ep27.
  - `grasp_lock.py` line 197 requires the singular-value ratio σ1/σ2 of the **whole object's** hull vertices to be ≥ 3.
  - The convex-hull ratio of our pot is 1.63; the other failing objects are lower still (pitcher 1.31, lid 1.13, dust pan
    1.55, sweeper 1.94, board 2.11).
  - Yet the held part of the pot is a 16 cm × 3 cm stick handle, the same shape class as the spoon handle on which the
    wrap recipe reached 0.97 [M].

## 10. Required contact forces for candidate grasps (LP) [M]

**Method** (`grasp_lp.py`):
- **Frames:** every frame of each human hold of §9.
- **Required wrench:** the contacts must supply SF·[m(a − g), 0] in the object's PCA frame (COM origin), with SF 1.5
  and 0.3 kg.
- **Contacts:** idealised contact layouts placed on our meshes' measured geometry (§11). Point contacts with a 4-edge
  friction pyramid, evaluated at 0° and 45° tangent orientation, worst case kept; no torsion.
- **LP:** minimise the largest normal force (Ferrari–Canny L∞ style). A frame is **infeasible** when no force
  distribution exists.
- **Reported:** the worst frame over the hold. Totals are not minimised.

| object, hold | layout | μ 0.5 | μ 0.71 | μ 1.0 |
|---|---|---|---|---|
| dust pan ep18 L / ep39 L / ep39 R | P1 single pinch at the ring end | infeasible 100 % | infeasible 100 % | infeasible 100 % |
| | P2 key pinch across the end band, 3 cm spread along the band | 57–60 N | 41–43 N | 30–32 N |
| | **P3 index through the hole under the inner band + thumb on the end band + middle under the end band** | **7.5–7.8 N** | **6.7–7.1 N** | **5.9–6.2 N** |
| | P4 = P3 + thumb PP + ring under the end band | 6.8–7.2 N | 5.9–6.2 N | 5.0–5.3 N |
| sweeper ep18 / ep31 | S3 single pinch on the ring end | infeasible 100 % | infeasible | infeasible |
| | S1 band clamp, 2 cm spread | 14.6–16.4 N | 8.8–9.3 N | 6.2–6.7 N |
| | **S2 neck/head clamp, 6 × 5 cm spread (RL-found)** | **3.4–3.7 N** | **1.9–2.0 N** | **1.4 N** |
| board, ep24 left-hand hold (f60–201; f0–55) | B1 one-point edge pinch | infeasible 100 % | infeasible | infeasible |
| | B2 thumb at the edge only, fingertips 4 cm in (cantilever) | infeasible 126/142 frames | infeasible 125/142 | 28.6 N |
| | B3 short-edge cantilever | infeasible 138/142 | infeasible 131/142 | 143 N |
| | **B4 thumb DP opposite the fingertips 3 cm in + thumb PP at the edge, fingers spread 4 cm** | **3.5 N (4.6)** | **3.3 N (4.3)** | **3.0 N (3.9)** |
| | B5 two pad pairs 6 cm apart | 4.9 N (6.3) | 4.4 N (5.7) | 3.9 N (5.1) |
| board, ep24 right-hand hold (f102–243, tilt 101°) | B2 / B3 | infeasible 100 % | infeasible 100 % | 241 / 352 N |
| | **B4** | **9.5 N** | **9.0 N** | **8.5 N** |
| | B5 | 27.9 N | 20.4 N | 15.3 N |
| pot ep2 / ep26 | T1 handle-end pinch | infeasible 100 % | infeasible | infeasible |
| | **T2 medium wrap −13…−21 cm** | **5.6 / 10.2 N** | **4.9 / 8.0 N** | **4.0 / 6.1 N** |
| | T3 wrap far out (−19…−25 cm) | 13.3 / 21.2 N | 11.3 / 17.3 N | 9.6 / 13.1 N |
| lid ep2 (two holds) | **L1 strap side pinch, 2.4 cm spread** | **12.0–15.2 N** | **8.6–10.9 N** | **6.2–8.0 N** |
| | L2 two fingers under the strap + thumb on top | 3.2–4.0 N | 2.5–3.0 N | 1.9–2.3 N |
| | L3 rim pinch at one side | 45.7–47.6 N | 33.5–35.0 N | 24.5–25.7 N |
| pitcher ep21 | **W1 handle wrap, 3 stations × 4 sides** | **5.3 N** | **4.2 N** | **3.3 N** |
| | W2 hook (one inner side only) | infeasible 100 % | infeasible | infeasible |
| | W3 one-station thumb–index pinch | infeasible 100 % | infeasible | infeasible |

**Readings** [M, I]:
1. Every single-pair pinch (P1, S3, B1, T1, W3) and the pure hook (W2) is infeasible through the observed tilts. This
   follows from the missing torsional friction and the two-contact theorem (§7).
2. The robust layouts all have a **long lever between opposing normal forces**:
   - hole-hook to end band: 4.5 cm;
   - thumb DP vs fingertips plus the edge contact: 3 cm;
   - wrap stations: 6–8 cm along the handle;
   - neck clamp: 6 cm.
3. Spreading contacts along a direction that is not the moment's lever does not help. P2 spreads along the band, but
   the pitch moment's lever is only the band thickness, so it needs 30–60 N per contact.
4. Achievability [M]:
   - the robot fingertip force per finger is about F ≈ kp·Δq_MCP / 0.1045 m = 16.3 N per rad;
   - 5–8 N needs Δq_MCP ≈ 0.31–0.49 rad within the MCP's remaining range;
   - forces up to about 10 N per contact are realistic; 25–60 N are not.
   - So the recommended layouts (≤ 10 N) are feasible, and P2, L3 and T3 are not.

**Analytic cross-checks** (static, horizontal, SF 1, μ irrelevant):
- **Pan P3:** fingers up 6.2 N, thumb down 3.3 N.
- **Board held at a long edge:** thumb at 1 cm, fingers under at 3 cm → 8.3 / 5.4 N; fingers at 5 cm → 4.2 / 1.2 N.
- **Board held at a short edge:** fingers at 3 cm → 15.4 / 12.4 N; fingers at 5 cm → 7.7 / 4.7 N.
- **Pot:** up and down contacts 7 cm apart, COM 12 cm beyond → 8.0 / 5.0 N.
- **Vertical plate held by a two-sided friction pinch:** N per side ≥ SF·mg / (2μ) = 4.4 / 3.1 / 2.2 N.

## 11. Per-object design specifications

Geometry is from our meshes (library_v3, PCA frame, COM origin; `slices.py`) [M], with the scan only to describe the
real object [GT].

Squeeze by joint, to produce a fingertip normal force F with kp 1.7 N m/rad [M]:
- straight index finger: Δq_MCP = 0.061·F, Δq_PIP = 0.034·F, Δq_DIP = 0.015·F rad per N;
- thumb: Δq_CMC = 0.078·F, Δq_MCP = 0.039·F, Δq_IP = 0.016·F.

This is Jᵀf/kp for a tip force normal to a straight finger. Bent postures change the levers; use the full Jacobian
(`grasp_force.py`).

### 11.1 mini_dust_pan (sim 0.3 kg; real mass unknown, a light plastic pan)

**Geometry (ours):**
- 17.3 × 15.8 × 3.7 cm, plate 1.2–2.3 cm thick (real 0.4–0.8 cm [GT]);
- ring handle: end band at pca1 −10.6…−8.2 cm, hole −8.2…−5.4 cm (2.8 × 4.2 cm), inner band at about −5.2 cm;
- COM to ring end 10.3 cm;
- collision-piece hole ≈ 3.0 × 3.5 cm (plates audit).

**Human:** thumb–middle/index clamp on the ring. In the ep39 carry the hand turns the pan up to 88–109°. The pick-up is
done by the left hand (f35–102), then handed over.

**Robot (P3/P4) [H]:**
1. Approach from **above, along the plate normal**, hand pre-shaped:
   - index extended and aligned with the hole;
   - thumb abducted above the end band;
   - middle and ring curled, ready to come under the end band.
2. **Cage:** lower the index distal and middle phalanges through the hole (insertion tolerance ±0.7 cm along the handle,
   ±1.35 cm across). Nothing touches the pan yet.
3. **Close:**
   - the thumb pad lands on the end band's top face;
   - in the same 1–2 frames, the index curls under the inner band (MCP-led) and the middle comes up under the end band;
   - net force on the free pan during closure stays at about 0;
   - **no finger may rise from below before the thumb is on top** (the current scoop and flick).
4. **Squeeze:** about 6 N per contact (thumb CMC 0.47 rad, index MCP 0.37 rad) scheduled with the load. Keep at least
   3 contacts on both sides of the plate through the tilts.
5. **Handover (ep39):** keep the human's pick-up hand until the object's first hold and hand over only where the human
   does (plates audit), or carry with one hand from the first hold.

### 11.2 mini_sweeper

**Geometry (ours):**
- 14.4 × 11.0 × 3.3 cm; bristle head 1.2–1.7 cm thick (real 0.6–0.8 cm);
- ring end at pca1 −7.2 cm, hole 1.7–3.0 × 2.2 cm (too small to hook; real 3.9 cm [GT]);
- COM to ring end 7.2–8.0 cm.

**Human:** thumb (all segments) against the middle finger's PP/MP across the ring band. A lateral-pinch-family grasp
with little palm.

**Robot (S2) [H]:**
- **Neck/head clamp**:
  - thumb column (metacarpal, PP, DP) along one face;
  - four fingers flat across the other face, reaching the far edge;
  - palm or index knuckle against the near lateral edge.
- 1.4–3.7 N per contact suffices; tolerance ±1.2 cm normal (aperture about 5 cm on a 2.2–2.7 cm head), ±2–3 cm in the
  plane.
- This is what the 0.889 RL policy did (rl-discovered-grasps), against the human's ring clamp (S1: 6–16 N).

**Must also** [plates and boards audits]:
- start the hold at the **object's motion onset** (f28 in ep18), not at the MANO contact onset;
- approach horizontally along the plate normal (the brush stands on a 3.2° stance margin);
- close thumb and fingers simultaneously;
- comply where the human pressed the bristles 0.4–0.9 cm into the table (the rigid brush cannot);
- ep31: fix the start overlap with the rack first.

### 11.3 Wooden boards

**Geometry (ours):** 22.9 × 13.3–13.8 cm; solid 7.8 mm (board 1) and 12.0 mm (board 2, 3 mm thicker than the scan
[GT]).

**Human:** palm-on-top drag → slide past the edge → fingers under, thumb on top → turn vertical (88–101°) → stand on edge.

**Robot (B4) [H]:**
1. Since the fingers may pass through the table, **clamp the board where it lies, at the start of the drag**:
   - thumb DP on top, 3 cm in from the edge, directly opposite the index/middle/ring pads below;
   - thumb PP (or palm heel) on top at the edge;
   - fingertips spread 4 cm along the edge.
2. Close thumb first (on top), then the fingers from below, with equal and opposite forces, so the board is pinched in
   place rather than scooped.
3. Then follow the human object path (drag, lift, turn). B4 works in both the flat (cantilever) and the vertical
   (in-plane) phases at 3–9.5 N per contact. The current edge-only cantilever (B2) is infeasible once the board tilts.
4. Tolerance ±1.4–1.6 cm normal, ±1.5 cm inward, ±5 cm along the edge.
5. **Precondition:** at closure, the hand must be within these tolerances of the simulated board. Today the wrist lags
   3–11 cm and the fingertips are 2–5 cm off (boards audit), so the kp 400 wrist + ILC and a gate on the closure error
   are prerequisites.
6. Alternatives: allow a **grasp change inside a hold** (the human regrasps 3–4 times), or a second hand for the turn as
   the human did (f37–78).

### 11.4 water_pitcher

**Geometry (ours):**
- 15 × 26 × 41.5 cm, a rough reconstruction;
- the handle loop is thickened to 4–5 cm (pca1 −8…−14 cm, pca2 +2…+11 cm);
- no flat bottom (the support certificate fails; the pitcher falls by f20).

**Human:** power grasp of the handle. The hand rotates the pitcher 91° to pour and lifts it 30 cm.

**Robot (W1) [H]:**
- **Medium wrap of the handle**:
  - fingers through the loop around the handle, MCP-led;
  - thumb over the top of the handle (thumb abducted, opposing the fingers through the loop);
  - palm on the outer side.
- 3.3–5.3 N per contact. A hook alone (thumb off) or a pinch cannot follow the pour (infeasible).
- Tolerance about ±1.5 cm.
- Prerequisite: a supportable mesh (flat underside) so the pitcher stands until the grasp.

### 11.5 white_pot_lid

**Geometry:**
- ours: disk 18.5 cm, 1.8 cm thick; bridge strap about 6–7 cm long across the centre, cross-section 1.4 × 1.4 cm at
  2.5–3.9 cm above the disk centre plane; **gap under the strap 1.5 cm**;
- scan [GT]: disk 1.1 cm, strap 1.5 × 1.2 cm, gap 2.1–2.2 cm.

**Human:** palm over the strap, fingers wrapping the strap, the thumb on its side. Lifted 4–6 cm, tilted 30–36°.

**Robot (L1) [H]:**
- **Strap side pinch**: thumb pad on one side face of the strap; index and middle pads on the other, 2.4 cm apart along
  the strap (the spread carries the moment).
- 6–15 N per contact (μ 1.0 → 0.5).
- Tolerance ±1.3 cm across, ±2 cm along, **±0.7 cm in height**: the pads must sit on the 1.4 cm-tall strap above the
  disk.
- **Do not** design fingers under the strap on our mesh: a 1.4 cm distal phalanx in a 1.5 cm gap gives ±0.5 mm. If a
  later mesh restores the real 2.2 cm gap, the hook-plus-thumb layout (L2, 2–4 N) becomes the robust choice (cage
  first).
- Prerequisite: separate the lid from the pot's hulls at frame 0 (start audit).

### 11.6 white_pot (stick-handle saucepan; the task brief's "side handles" do not exist in our mesh or the scan [M, GT])

**Geometry (ours):**
- body Ø 19 × 13 cm;
- one stick handle from pca1 −9 to −25.5 cm, cross-section 3.0 × 2.5 cm (2.8 × 1.7 cm at the tip);
- COM to the human grip 16–18 cm.

**Human:** power grasp, handle across the palm, thumb on top near the end. ep26 turns the pot 180° (mouth down into the
rack).

**Robot (T2) [H]:**
- Run **`wrap_grasp` on the handle**: selected by the local geometry around the human contacts (local PCA of the held
  part), not the whole-object PCA.
- 4 fingers under and around the handle at −13…−19 cm, MCP-led; palm on the side; thumb plus palm heel on top at
  −15 and −21 cm.
- 4–10 N per contact. Gripping only near the end (−19…−25 cm) doubles the force (10–21 N): grip near the middle of the
  handle, not where the human thumb sat.
- Tolerance ±2 cm across, ±3.5 cm along.
- Prerequisite in ep26: remove the frame-0 hull overlap with the rack.

## 12. Are the failures really grasp failures? (combined verdict)

| episode (eval twin) | primary cause (first thing that goes wrong) | evidence | grasp failure? | after the primary fix, would the current grasp hold? |
|---|---|---|---|---|
| ep18 dust pan (19) | designed grasp has no opposition; fingers rise from below and flick the pan (63–80 mm / 17–22° at closure, 4 of 4 replays) | plates audit [M] | **yes** | – (is the primary) |
| ep18 sweeper (19) | hold starts 23 frames after the object moves; the approach follows a phantom and knocks the brush (3.2° stance) | plates audit | no | uncertain: the audit finds a human-type band clamp that was never exercised (the site check sees the thumb only); a band clamp needs 6–16 N (§10), the RL neck clamp 1.4–3.7 N |
| ep39 dust pan (38) | `--single_hand` merge deletes the left-hand pick-up; no hand on the pan while it rises | plates audit | no | no: the right-hand designed grasp touches nothing (§9.3) |
| ep24 boards (25) | clamp never acquired: wrist lag 3–11 cm, fingers 2–5 cm off; the edge-only cantilever is infeasible once tilted | boards audit + §10 | **yes** | – |
| ep31 sweeper (30) | sweeper ejected from the rack hulls at step 1 (11.3° / 1.07 cm) | boards audit | no | the RL fine-tune already carries it 5 of 5 |
| ep21 pitcher (20) | pitcher falls 134 mm / 73° by f20: no flat bottom | work log, start audit | no | no: 38° opposition, palm 81 mm, 5 joints at limit |
| ep2 lid + pot (1) | lid starts 8 mm inside the pot's hulls, jumps 31 mm / 27°; pot shifts 71 mm | work log | no | lid: no (52°, palm 95 mm). pot: weak (95°, no wrap) |
| ep26 pot in rack (28) | hull overlap 9.8 mm flings the pot 117 mm / 52° before any hand | work log | no | no: no thumb on the pot; a 180° flip needs a wrap |

Bottom line [I]:
- Only **2 of 8** failures are primarily grasp failures (ep18 dust pan, ep24 boards).
- **4 more** have a grasp that would fail next (ep39, ep21, ep2, ep26), and the ep18 sweeper probably would too.
- The designed grasps of §11 are needed for 7 of 8, but they will not show any gain until reference timing and carrier
  rules (ep18 sweeper, ep39) and frame-0 collision consistency (ep2, ep21, ep26, ep31) are fixed.

## 13. Evolution of the human grip (brief; context for "what the hand is built for") [L]

- **Two grips.** Napier's power grip and precision grip have been read as a **clubbing grip and a throwing grip**.
  On this reading, millions of years of selection for throwing and clubbing remodelled the hand (Young 2003; a
  hypothesis in palaeoanthropology).
- **What is distinctive in humans** (Marzke 1997):
  - **forceful precision grips**: securing objects firmly between the thumb and fingers of one hand ("precision
    pinching");
  - reorienting objects by distal joint motion ("precision handling");
  - eight derived features, among them substantially **larger moment arms of the intrinsic muscles that stabilise the
    proximal thumb joints**;
  - tool-making studies link human grips to stone tool making; the fine pad-to-pad grip is *not* the critical one.
- Humans have "a distinctive set of **forceful pinch grips** … effective in the control of stones by one hand", backed
  by a unique pattern of muscle architecture and joint surfaces (Marzke 2013).
- Fossil evidence now supports advanced manipulation in pre-*Homo* hominins, balanced against arboreal demands (Kivell
  2015).

Design reading [I]:
- What the human hand evolved to do best is **thumb-against-finger(s) clamping with large, stable thumb forces**: pad
  opposition, lateral or key pinch, three-jaw chuck. That is what our humans used on every failing object (§9).
- The Sharpa thumb has a large CMC FE range but little abduction and no pronation (§1). The clamp must be built from
  CMC FE + MCP AA, with the fingers moved to meet the thumb.
- Where the robot cannot reach the human's thumb force or orientation, the mechanical substitutes are **form closure**
  (hook through a hole, wrap) and **spread contacts** (§10).
- The evolutionary-algorithm question has its own report (workflow step "EA vs RL"). For this report the relevant
  facts are:
  - the grasp design space is small and structured: contact roles, a 2–3-D postural synergy space (Santello 1998),
    approach direction, closure order, per-joint squeeze;
  - its fitness can be evaluated by a zero-action replay plus the LP of §10;
  - so population search fits a **design** step, while RL stays for closed-loop tracking (notes 24: zero action
    0.41–0.66 → fine-tune 0.96–0.98).

## 14. Hypotheses and the experiments that would falsify them

| # | hypothesis [H] | experiment (CPU build; one zero-action GPU replay each, about $0.1) | falsified if |
|---|---|---|---|
| H1 | Opposition is necessary: a designed hold with a thumb-to-finger normal angle < 100° (or no thumb) loses the object during tilts > 30°. | Re-snap ep2 pot, ep2 lid, ep21 pitcher and ep24 board 2 with the thumb forced onto the face opposite the finger pads (angle ≥ 150°); zero-action replay after the start fixes. | in-hand slip does not drop (≥ 2 cm or ≥ 10° in both versions), or the < 100° versions already hold within 1 cm / 5° |
| H2 | In this simulator, single-pair pinches cannot hold our objects through the observed tilts (no torsional friction). | CPU FlashCHORD: the dust pan (0.3 kg) held by one thumb–index pair at the ring end, rotated 0 → 60° about the handle axis at 20 fps. | the pan rotates < 5° in the hand (then the simulator has torsional friction and §10 is too pessimistic) |
| H3 | Dust pan P3 (cage through the hole, thumb on the band, closed together, about 6 N) removes the closure flick and holds through ep39's 88° carry. | Build P3 in `grasp_lock.py` (with the onset-anchored hold of the plates audit); zero action on ep18 and ep39. | displacement at closure > 10 mm or > 5° (now 63–80 mm / 17–22°), or slip > 2 cm during f20–150 (ep18) |
| H4 | Board B4 (thumb DP opposite the fingertips + thumb PP at the edge) holds through the 66–101° turns where the edge-only clamp cannot. | ep24 with B4, kp 400 wrist + ILC, closure-error gate ≤ 1 cm. | B4 board lift < 5 cm at the human lift frames, or board-in-hand slip > 2 cm |
| H5 | Wrapping the pot's stick handle (local-PCA wrap rule) beats the snapped grasp once the start overlap is fixed. | ep2 / ep26 with the start fix, wrap vs snap, zero action + 3 evaluations of a 40M fine-tune. | the wrap does not raise zero-action sim_vs_ref by ≥ 0.05, or the fine-tune does not beat the snap version |
| H6 | A force-proportional squeeze (Δq = Jᵀf/kp, about 0.06 rad per N at the MCP) keeps contacts that the uniform 0.4 rad squeeze curls away from on thin plates. | ep18 dust-pan grasp target with both squeezes: distance of thumb and finger pads to the plate after the squeeze (CPU FK, then zero action). | the uniform squeeze keeps the thumb within 3 mm of the plate (now 20 mm) or the proportional one does not |
| H7 | On our lid mesh, fingers cannot be threaded under the strap without moving the lid; the side pinch (L1) can be acquired. | CPU: insert the index DP under the strap along the strap normal at 5 mm/step, measure lid displacement; then the L1 closure. | the index passes under the strap with < 3 mm lid motion |
| H8 | The capture tolerances (0.7–2 cm) are what limits acquisition: with the closure-error gate passed (hand within the tolerance of §11 at the closure frame), every designed grasp acquires its object at zero action. | Log hand-to-object error at closure in all zero-action replays; correlate with acquisition (object lifted ≥ 3 cm at the human lift frames). | acquisition fails in ≥ 2 of 5 holds whose closure error is within tolerance (then the contact layout, not the precision, is wrong) |

## 15. Sources (opened unless marked)

**Anatomy and biomechanics:**
- Hollister et al. 1992, axes of the thumb CMC joint, J Orthop Res 10:454 — https://pubmed.ncbi.nlm.nih.gov/1569508/
- Crisco et al. 2015, in vivo TMC kinematics, J Hand Surg Am 40:289 — https://pubmed.ncbi.nlm.nih.gov/25542440/
- Cooney & Chao 1977, static forces in the thumb, JBJS Am 59:27 — https://pubmed.ncbi.nlm.nih.gov/833171/
- Ladd et al. 2013, thumb CMC anatomy, hormones and biomechanics, Instr Course Lect 62:165 — https://pubmed.ncbi.nlm.nih.gov/23395023/
- Napier 1955, thumb CMC form and function, J Anat 89:362 (record only, not read) — https://pubmed.ncbi.nlm.nih.gov/13251966/
- Sangole & Levin 2008, arches of the hand, J Biomech 41:829 — https://pubmed.ncbi.nlm.nih.gov/18076888/
- Sangole & Levin 2008, palmar arch dynamics, Exp Brain Res 190:443 — https://pubmed.ncbi.nlm.nih.gov/18641977/
- Serina, Mote & Rempel 1997, fingertip pulp, J Biomech 30:1035 — https://pubmed.ncbi.nlm.nih.gov/9391870/
- Pawluk & Howe 1999, fingerpad dynamic contact, J Biomech Eng 121:605 — https://pubmed.ncbi.nlm.nih.gov/10633260/
- Warman & Ennos 2009, fingerprints and friction, J Exp Biol 212:2016 — https://pubmed.ncbi.nlm.nih.gov/19525427/
- Zatsiorsky, Li & Latash 2000, enslaving, Exp Brain Res 131:187 — https://pubmed.ncbi.nlm.nih.gov/10766271/
- Häger-Ross & Schieber 2000, finger independence, J Neurosci 20:8542 — https://pubmed.ncbi.nlm.nih.gov/11069962/
- Santello, Flanders & Soechting 1998, postural synergies, J Neurosci 18:10105 (abstract via Europe PMC) — https://doi.org/10.1523/JNEUROSCI.18-23-10105.1998
- Santello et al. 2016, synergies reply, Phys Life Rev 17:54 — https://pubmed.ncbi.nlm.nih.gov/27344306/

**Taxonomies:**
- Napier 1956, JBJS Br 38-B:902 (record only; content as restated by Young 2003 and Feix 2016) — https://pubmed.ncbi.nlm.nih.gov/13376678/
- Kamakura et al. 1980, AJOT 34:437 — https://pubmed.ncbi.nlm.nih.gov/6446851/
- Cutkosky 1989, IEEE TRA 5:269 (not opened) — https://doi.org/10.1109/70.34763
- Feix et al. 2016, GRASP taxonomy — https://www.eng.yale.edu/grablab/pubs/Feix_THMS2016.pdf
- Feix, Bullock & Dollar 2014, object characteristics — https://www.eng.yale.edu/grablab/pubs/Feix_TOH2014_1.pdf
- Feix, Bullock & Dollar 2014, tasks, objects and grasps — https://www.eng.yale.edu/grablab/pubs/Feix_TOH2014_2.pdf
- Bullock, Ma & Dollar 2013, hand-centric manipulation classification — https://www.eng.yale.edu/grablab/pubs/Bullock_TOH2013_1.pdf

**Reach-to-grasp and closure order:**
- Jeannerod 1984, J Mot Behav 16:235 — https://pubmed.ncbi.nlm.nih.gov/15151851/
- Jakobson & Goodale 1991, Exp Brain Res 86:199 — https://pubmed.ncbi.nlm.nih.gov/1756790/
- Smeets & Brenner 1999, A new view on grasping, Motor Control 3:237 (abstract) — https://research.vu.nl/en/publications/a-new-view-on-grasping/
- Smeets & Brenner 1999, response, Motor Control 3:316 — https://personal.fbw.vu.nl/~jsmeets/1999/Emergent_grip-MC99.pdf
- Smeets, Brenner & Martin 2009, Grasping Occam's razor — https://pubmed.ncbi.nlm.nih.gov/19227518/
- Kamper, Cruz & Siegel 2003, J Neurophysiol 90:3702 — https://pubmed.ncbi.nlm.nih.gov/12954607/
- Braido & Zhang 2004, Hum Mov Sci 22:661 — https://pubmed.ncbi.nlm.nih.gov/15063047/
- Somia et al. 1998, J Hand Surg Br 23:792 — https://pubmed.ncbi.nlm.nih.gov/9888684/
- Landsmeer 1963, JBJS Am 45:1654 (record only) — https://pubmed.ncbi.nlm.nih.gov/14083140/

**Grip force:**
- Johansson & Westling 1984, Exp Brain Res 56:550 — https://pubmed.ncbi.nlm.nih.gov/6499981/
- Westling & Johansson 1984, Exp Brain Res 53:277 — https://pubmed.ncbi.nlm.nih.gov/6705863/
- Johansson & Westling 1988, Exp Brain Res 71:59 — https://pubmed.ncbi.nlm.nih.gov/3416958/
- Flanagan & Wing 1997, J Neurosci 17:1519 — https://pubmed.ncbi.nlm.nih.gov/9006993/
- Flanagan & Tresilian 1994, JEP:HPP 20:944 — https://pubmed.ncbi.nlm.nih.gov/7964530/
- Kinoshita et al. 1997, J Neurophysiol 78:1619 — https://pubmed.ncbi.nlm.nih.gov/9310447/
- Goodwin, Jenmalm & Johansson 1998, J Neurosci 18:10724 — https://pubmed.ncbi.nlm.nih.gov/9852607/
- Cole & Johansson 1993, Exp Brain Res 95:523 — https://pubmed.ncbi.nlm.nih.gov/8224079/
- Burstedt, Flanagan & Johansson 1999, J Neurophysiol 82:2393 — https://pubmed.ncbi.nlm.nih.gov/10561413/
- Kinoshita, Kawai & Ikuta 1995, Ergonomics 38:1212 — https://pubmed.ncbi.nlm.nih.gov/7758447/
- Augurelle et al. 2003, J Neurophysiol 89:665 — https://pubmed.ncbi.nlm.nih.gov/12574444/
- Johansson & Flanagan 2009, Nat Rev Neurosci 10:345 (abstract only) — https://pubmed.ncbi.nlm.nih.gov/19352402/
- Hadjiosif & Smith 2015, J Neurosci 35:9106 — https://groups.seas.harvard.edu/motorlab/Reprints/Hadjiosif_Smith_J_Neurosci_2015.pdf

**Friction:**
- Sivamani et al. 2003, Skin Res Technol 9:227 — https://pubmed.ncbi.nlm.nih.gov/12877683/
- Derler & Gerhardt 2012, Tribol Lett 45:1 (abstract) — https://research.tue.nl/en/publications/tribology-of-skin-review-and-analysis-of-experimental-results-for/
- André et al. 2011, J R Soc Interface 8:1574 — https://pubmed.ncbi.nlm.nih.gov/21490002/
- Han, Shimada & Kawamura 1996 (ICRA): not opened

**Mechanics:**
- Nguyen 1985, Synthesis of force-closure grasps, MIT AI memo — https://dspace.mit.edu/handle/1721.1/6430
- Lynch & Park 2017, Modern Robotics, ch. 12 — https://hades.mech.northwestern.edu/images/7/7f/MR.pdf
- Ferrari & Canny 1992, ICRA — https://www.research.unipd.it/bitstream/11577/2532028/1/PlanningOptimal.pdf
- Ciocarlie, Lackner & Allen 2007, WHC — https://roam.me.columbia.edu/sites/default/files/content/papers/haptics07_contact.pdf
- Rodriguez, Mason & Ferry 2011, RSS — https://roboticsproceedings.org/rss07/p37.pdf
- Singh 2022, capstan — https://arxiv.org/pdf/2205.04348
- Edgren, Radwin & Irwin 2004, Hum Factors 46:244 — https://pubmed.ncbi.nlm.nih.gov/15359674/
- Seo & Armstrong 2008, Hum Factors 50:734 — https://pubmed.ncbi.nlm.nih.gov/19110833/
- Amis 1987, J Biomed Eng 9:313 — https://pubmed.ncbi.nlm.nih.gov/3682795/
- Bicchi 1995 / Bicchi & Kumar 2000: not opened (the host reset the connection); not cited for content

**Flat objects and tools:**
- Eppner et al. 2015, IJRR 34:1021 — https://depositonce.tu-berlin.de/bitstream/11303/6844/1/0278364914559753.pdf
- Bimbo et al. 2019, Front Robot AI 6:135 — https://www.frontiersin.org/articles/10.3389/frobt.2019.00135/pdf
- Hang, Morgan & Dollar 2019, RA-L 4:662 — https://www.eng.yale.edu/grablab/pubs/Hang_RAL2019.pdf
- Kazemi et al. 2012, RSS — https://www.roboticsproceedings.org/rss08/p23.pdf
- Sartori, Straulino & Castiello 2011, PLoS One 6:e25203 — https://pubmed.ncbi.nlm.nih.gov/21980396/

**Evolution:**
- Young 2003, J Anat 202:165 — https://pubmed.ncbi.nlm.nih.gov/12587931/
- Marzke 1997, Am J Phys Anthropol 102:91 — https://pubmed.ncbi.nlm.nih.gov/9034041/
- Marzke 2013, Phil Trans R Soc B 368:20120414 — https://pubmed.ncbi.nlm.nih.gov/24101624/
- Kivell 2015, Phil Trans R Soc B 370:20150105 — https://pubmed.ncbi.nlm.nih.gov/26483538/

## 16. Reproduction

**Environment:**
- machine: Claude cloud VM (4 CPU), `OMP_NUM_THREADS=1`;
- code: repo at the current head plus the scripts in `docs/research/grasp/hand-biomech-scripts/`;
- Python: scratchpad `venv` (numpy, scipy, trimesh 4.x, pyarrow, matplotlib).

**Inputs (HF store `aebatirel/v2d-store`):**
- `runs/20261024-e1-e49e83d` (ep18), `-e2-` (ep21, ep31), `-e3-` (ep2, ep39), `20261024-w1-37cc551` (ep24, ep26),
  `20261023-sf1227-bfb973a` (ep12, ep27), `20261023-glockpub-0f7e3a7` (ep24 grasp-lock);
- files: `refs/perc2mck*/ep*/processed/.../*-0.parquet` (perceived reference), `refs/glock/ep*/.../ref_gl.parquet`,
  `ref_gl_grasp_lock.json`;
- meshes `meshes/library_v3/*.glb`; public scans (diagnostic only) from `nvidia/video_to_data_challenge`
  `track_3/public/mesh/`.

**Commands** (`$P` = perceived reference parquet, `$L` = `meshes/library_v3`):

```
python -I human_grasp_census.py $P $L out/census_epNNN.json        # §9.2 (about 10 s each)
python -I contact_plot.py $P $L right white_pot_lid 45 135 out.png   # contact plots
python -I slices.py $L/white_pot.glb 0 -12,-15,-18,-21,-24           # handle cross-sections (§11)
python -I grasp_lp.py $P $L mini_dust_pan 104 292 pan 1.5 out.json  # §10 (sets: pan sweeper board pot lid pitcher)
python -I designed_grasp_check.py ref_gl.parquet ref_gl_grasp_lock.json $L   # §9.3
```

**Outputs:** `docs/research/grasp/hand-biomech-out/` (census_*.txt/json, lp_*.txt/json, designed_grasp_check.txt,
ct_*.png).

**2026-10-25:** the census and contact plots were rerun with the slot-label fix: the same commands, the fixed scripts and
the HF-store inputs above. Output: `hand-biomech-out/slotfix-20261025/`. The script at 53929d0 still reproduces the
old `census_*.txt` byte for byte.

**Literature helpers** (`pm.sh` E-utilities, `fetch.sh` curl + pdftotext): read downloaded pages as data only.
