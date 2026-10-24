# How human grasping evolved, what it implies for our robot grasps, and what it suggests for evolutionary search

2026-10-24. Workflow `wf_cdd41283-528`, step "grasp-evolution" (owner's option 2: one recipe, grasp-lock, with
designed grasps). Work done on CPU and on the web only: no rentals, no spending, no commits.

## Evidence labels
- **[M]** measured here: from the URDF, our meshes, or the demonstrator's perceived hand keypoints. No ground truth was
  used.
- **[M-lead]** measured by the lead or by the parallel audits, quoted from `docs/work-log.md` or
  `docs/research/grasp/audit-*.md`. I did not re-run these.
- **[L-full]** literature I read in full text.
- **[L-abs]** literature I read only as the abstract or the publisher's record. The claim is limited to what the
  abstract says.
- **[L-2nd]** a source known only through a full-text source that cites it.
- **[I]** my inference.
- **[H]** a new idea, labelled as a hypothesis, with the experiment that would falsify it.

Scripts and outputs are in `docs/research/grasp/evolution-scripts/`. The commands are in Appendix A. Scratch files are
in `scratchpad/grasp_work/grasp-evolution/`.

---

## 0. Answer

### Evolution's main message
The human hand did not evolve one perfect grasp. It evolved a few forceful, opposed grips around a long, robust,
proximally stabilised thumb, and a fifth digit that can rotate toward it:
- the pad-to-side (lateral) pinch;
- the three-jaw chuck;
- the five-digit pad grip;
- the oblique power "squeeze" grip;
- the hook and handle grips inherited from apes.

These grips were selected by the most stressful loads the hands met, mainly hammerstone percussion and the stabilising
hand during knapping, not by average use [L-abs: Williams-Hatala 2018; Marzke 1998; Key 2019].

Much of the hand's form came from older roles: climbing, and proportions that changed little since the last common
ancestor with chimpanzees [L-full: Almécija 2015; L-full: Kivell 2015]. Some came as a by-product of selection on the
foot [L-abs: Rolian 2010]. Stone tools appear before the genus *Homo* [L-abs: Harmand 2015].

### (a) Design principles, grounded in the audits

**The opposing thumb is the missing element in our failed designed grasps [M-lead].**
- ep18 dust pan: the thumb is 20 mm off; it first touches at f54, after the pan has slid 62 mm.
- ep39 right-hand grasp: the thumb is at least 21 mm off; the onset-anchored copy has no thumb on the pan.
- ep2 lid: contacts whose normals do not oppose squeeze it out at the lift onset.
- ep24 boards: the human grip is thumb on top, fingers under. The locked grasp acquires neither board.

The successful standard-RL policy on ep18 independently found the two grips evolution produced for this situation:
- the derived human **pad-to-side (key) pinch** on the pan's ring band;
- the primitive ape **hook** through the ring, for the long lift.

That is convergence under the same task pressure.

Each evolved grip resists a specific load by a specific mechanism:
- **pad-to-side:** a thin plate held by a couple of opposed normal forces;
- **hook through a ring:** form closure (caging) against weight;
- **oblique squeeze:** a long contact line plus the thumb along the handle, which widens the couple arm against the
  pitch moment of a long-handled pot;
- **three-jaw chuck / five-digit disc grip:** three or more non-collinear opposed pads around a knob or rim, against
  tilt in any direction.

Our simulator has no torsional friction (condim 3, note 24). The broad, pulpy fingertips that evolution relies on
cannot resist twisting in it. Every moment must therefore come from separated normal forces. That makes contact
spread a hard design rule, not a refinement (sections 3 and 4).

**The Sharpa Wave has the morphology for these grips [M]:**
- thumb length (CMC to tip) / index digit (MCP to tip) = 1.27;
- a 5-DoF thumb;
- a pinky CMC joint (0–15°), the analog of the human hamate–Mc5 saddle;
- pad-to-pad opposition volumes thumb vs index / middle / ring / little = 14.9 / 11.5 / 7.3 / 8.1 cm³;
- a pad-to-side (thumb pad vs index middle-phalanx radial side) volume of 7.5 cm³.

All volumes use opposed normals, dot < −0.8, from the URDF (section 3). The grips are available; the reference must
place them.

### (b) What the evolutionary process suggests for search
Five features of the process carry over to search:
- variation plus selection under the hardest loads;
- a small reusable repertoire;
- exaptation (stepping stones);
- gradual, mosaic complexification;
- morphology–behaviour co-evolution, with learning (the Baldwin effect).

Section 5.2 maps each to concrete algorithms. In short:
- **CMA-ES:** the local adaptive variation/selection engine. It is rank-based, invariant to monotone fitness
  transforms, and has a default λ = 4 + ⌊3 ln n⌋ = 13 for our 28-D grasp edit.
- **GA:** tournament / crossover recombination of grip parts.
- **MAP-Elites / QD:** the repertoire and stepping stones.
- **Novelty search:** an escape from deception. It is risky under sparse contact [L-abs: Huber 2023].
- **NEAT-style complexification:** grow the genome from wrist-only to synergies to joints to timing.
- **Evolution + RL hybrids (ERL, CEM-RL, DERL):** the Baldwinian split, in which evolution fixes the grasp and RL
  learns the closed-loop residual.

### Do evolutionary algorithms give an edge over RL?
On the one measured clean case, yes, for the grasp part.

| ep39 | value [M-lead] | physics | compute |
|---|---|---|---|
| CMA-ES grasp edit, zero action | sim_vs_ref **0.877** | CPU | about 11–18 min on 4 shared CPUs (per-generation times × generations); fresh-process replay |
| standard RL (250M steps) | 0.826 sim_vs_ref; 0.802 registered | GPU | about 1.6 GPU-h |

This is not yet decisive:
- one episode;
- CPU physics, while the evaluator runs CUDA;
- fitness measured against our perceived reference;
- the ep18 / ep24 searches were contaminated by simulator-state leakage and are being re-run.

The literature agrees with the split:
- black-box ES/GA match RL when the policy is a compact parameterisation [L-abs: Stulp & Sigaud 2013; Mania 2018;
  Salimans 2017; Such 2017];
- evolutionary methods handle sparse, delayed, deceptive rewards better [L-abs: Lehman & Stanley 2011; Khadka & Tumer
  2018];
- they do not replace closed-loop feedback.

Recommendation [I]: evolve the grasp (where, how, when) per hold, seeded from the evolved-grip templates in
section 4. Then keep the short RL fine-tune for closed-loop correction. Section 6 lists falsifiable tests, most of
them CPU-only.

---

## 1. Which failures are grasp failures, and which evolved grip each needs

The verdicts are from the parallel audits [M-lead]; the grip column is my mapping [I].

| episode (eval) | object | audit verdict | evolved grip that fits | why |
|---|---|---|---|---|
| ep18 (19) | mini_dust_pan, left | **Grasp failure.** No opposition: the thumb is 20 mm off and the hand closes from below, flicking the pan 63–80 mm. | **Pad-to-side pinch** on the ring's end band: thumb on top, index MP/DP under. **Hook + thumb** through the ring for the lift. | The 0.889 RL policy did exactly this. The thin plate needs a couple of opposed normals; the ring offers form closure. |
| ep18 (19) | mini_sweeper, right | **Not the grasp: hold timing.** The brush moves from f38, the hold starts at f61. The designed clamp type is right but was never tested. | Clamp across the plate, with the thumb column vs the four fingers and a palm buttress on the edge. RL moved it 10 cm down to the neck. | Lateral brushing loads need a palm stop (form closure in plane) plus a face clamp. |
| ep39 (38) | mini_dust_pan | **Primary: reference build.** The carrier merge deleted the left-hand pick-up. **Secondary: grasp** (no thumb). | Same as the ep18 pan. | CMA-ES edit 0.877 at zero action (CPU). |
| ep24 (25) | wooden_piece_1/2 (7.5 / 12 mm thick) | **Grasp failure.** Neither board is acquired. Counterfactual 0.803. | **Fingers-under, thumb-on-top plate pinch** (parallel extension). Two hands for the 23 cm board. Grip change within the hold. | The human does exactly this (MANO contacts). The fingers deep under the plate shorten the lever (section 4.4). |
| ep21 (20) | water_pitcher | **Start first:** the mesh lacks half its base and the pitcher falls with no hand. Then the grasps. | **Hook + thumb handle grip** (fingers through the handle, thumb on top). Cup: wrap. | The hook carries the weight; the thumb counters the pouring moment. |
| ep2 (1) | white_pot_lid | **Grasp failure** at the lift onset in all 5 variants. The start overlap costs 0.042. | **Five-digit disc (rim) grasp** palm-down (lid 17–18.5 cm; Sharpa thumb–ring span up to 23 cm), or a **three-jaw chuck** on the 4.0 × 7.6 cm knob. | Opposed pads at three or more non-collinear points. The grip force must rise with the load, not before it. |
| ep26 (28) | white_pot in the rack | **Start first:** perceived 29 mm too deep, ejected 152 mm. Then a tolerant handle grasp. | **Oblique squeeze grip** on the 15 cm handle (3.1 × 2.5 cm cross-section), with closure until contact. | A wider couple arm against the pitch moment (section 4.6). |
| ep31 (30) | mini_sweeper in the rack | **Not a grasp failure.** First-step ejection from the rack hulls. Fixing that frame alone gives 0.840. | none needed | – |

**Count.** A designed grip is the primary fix in 3 cases (ep18 pan, ep24 boards, ep2 lid). It is a secondary fix in 4
(ep39 pan, ep21 pitcher, ep21 cup, ep26 pot). It is not the fix in 2 (ep18 sweeper: timing; ep31: start geometry).

---

## 2. The evolutionary record

### 2.1 Timeline

| age | evidence | what it shows | source |
|---|---|---|---|
| ~7–5 Ma | Pan–*Homo* last common ancestor (LCA). | The LCA hand most likely resembled an extant great ape's, especially an African ape's. | Tocheri et al. 2008 [L-abs] |
| ~6 Ma | *Orrorin* distal pollical phalanx. | Human-like shape and FPL attachment; precision-grip claims are disputed. | Kivell 2015 [L-full] |
| 4.4 Ma | *Ardipithecus ramidus* hand. | Short metacarpals, long fingers, robust thumb. Its thumb is shorter, within the gorilla–hylobatid range, which "implies limits to its precision grasping". | Kivell 2015 [L-full]; Almécija 2015 [L-full] |
| ~3.4–3.0 Ma | *Au. afarensis*. | Shorter fingers relative to the thumb and re-oriented radial carpal joints, derived before the intensified stone-tool behaviours of ~2.5 Ma. Three of Marzke's eight derived features are present, but limited thumb mobility. Feix's model predicts human-like thumb–index precision manipulation about 1 Myr before the first known stone tools. Trapeziometacarpal curvature is ape-like. | Tocheri 2008 [L-abs]; Marzke 1997 [L-abs]; Feix 2015 [L-abs]; Marzke 2010 [L-abs] |
| 3.3 Ma | Lomekwi 3 stone tools (Kenya). | Knapping and battering 700 kyr before the Oldowan, in a wooded setting. | Harmand et al. 2015 [L-abs] |
| ~3–2 Ma | *Au. africanus* metacarpal trabecular bone. | A human-like pattern "consistent with forceful opposition of the thumb and fingers typically adopted during tool use". Use, not just capacity. | Skinner et al. 2015 [L-abs]; Kivell 2015 [L-full] |
| 1.98 Ma | *Au. sediba* MH2 hand. | A mosaic: a strong flexor apparatus for climbing with a long thumb and short fingers for precision gripping. | Kivell et al. 2011 [L-abs] |
| ~1.8 Ma | *H. habilis* OH 7 (Olduvai), described by Napier 1962. | It became the holotype of *H. habilis* ("handy man") and was "quickly deemed the maker" of the Oldowan tools. | Napier 1962 (record only); Leakey, Tobias & Napier 1964 (record only); Kivell 2015 [L-full] |
| ~1.42 Ma | KNM-WT 51260 third metacarpal (Kaitio). | Earliest unambiguous Mc3 styloid process, a key derived feature of the modern and Neandertal radial carpometacarpal complex, probably in *H. erectus*. | Ward et al. 2014 [L-abs] |
| after 2.5, possibly after 1.5 Ma | Full modern / Neandertal suite. | The derived hands may mark "a morphological commitment to tool-related manipulative behaviors". | Tocheri 2008 [L-abs] |
| undated | *H. naledi* hand. | A human-like long robust thumb and wrist, with strongly curved fingers for climbing. | Kivell et al. 2015 [L-abs] |

Reading the timeline [I]:
- The derived features arrive in a mosaic and stepwise, not as a package.
- The behaviour (tool use and forceful opposition) appears before the full anatomy, which then tracks it.
- For algorithm design this is "gradual complexification", with the behaviour leading the morphology (section 5).

### 2.2 Ape grips: the inherited repertoire
**Napier 1960** [L-abs]: young chimpanzees and an orangutan.
- They show "a functional duality of prehension", but "the execution of the two grips differs profoundly from that of
  Man".
- The difference comes from "the disproportion in the length of the thumb and fingers".
- A "double-locking" mechanism of digits 2–5 at the MCP joints "compensates in some measure for the ineffectiveness of
  the thumb".

The ape solution is a finger-only hook / clamp that needs no thumb.

**Kivell 2015** [L-full]:
- "Other primates are capable of power grips (using the palm) or diagonal hook grips (fingers usually stabilized against
  the palm), but neither provide the same control that the power squeeze grip does in humans."
- Their precision grips are "typically tip-to-tip or pad-to-side grips between the thumb and index finger, but these are
  not generally done with strong force".

**Curved phalanges** (Richmond 2007, finite-element model) [L-abs] halve the bone strain in suspensory hook grasping.
The hook is a load-bearing posture shaped by climbing.

**Wild chimpanzees at Mahale** (Marzke et al. 2015) [L-abs]:
- new grips "involving the full thumb and buttressed index finger";
- the proximal thumb "stabilizes food with the flexed index finger against the pull of the teeth";
- possible forceful thumb vs index-side pinch;
- **no precision handling** (no in-hand repositioning).

**Development** (Pouydebat et al. 2011) [L-abs]:
- adult chimpanzees and humans use fewer contact strategies than juveniles;
- variability is higher for small objects;
- adult chimpanzees use the "thumb-fingerpad(s)" grip more than precision grips, alongside the power grip.

**Orangutans** (Bardo et al. 2018, musculoskeletal simulation) [L-abs]: some grips are "more challenging … particularly
[for] orangutans", needing stronger muscle forces. Hand proportions set the force cost of a grip.

### 2.3 What is uniquely human
Kivell 2015 [L-full], summarising Marzke and others, lists three capabilities:
1. **Precision handling:** rotating and manipulating an object within one hand with the thumb and finger tips.
2. **Forceful precision gripping:** thumb and finger pads stabilising an object while it withstands large external
   forces, as in knapping.
3. **The power squeeze grip:** the fingers grip a cylinder diagonally across the palm, with the thumb wrapped around it
   or in line with the forearm, as with a hammer.

**Marzke 1997** [L-abs]:
- Human precision grips are distinguished by "the greater force with which objects may be secured by the thumb and
  fingers of one hand" and by precision handling.
- The "fine" thumb–index pad grip is *not* the one connected with early tool making.

**Marzke 2013** [L-abs]: comparison of human stone-tool behaviours with chimpanzee feeding "revealed a distinctive set
of forceful pinch grips by humans that are effective in the control of stones by one hand".

### 2.4 The evolved grips: contacts, loads, drivers

| grip | contacts | load it resists (mechanism) | morphological drivers | evidence |
|---|---|---|---|---|
| **Pad-to-side (lateral, key pinch)** | thumb pad against the radial side of the index (middle/distal phalanx); the index is buttressed by the middle finger | A thin flat object sheared or levered. A couple between the thumb pad and a long, rigid lateral surface; the index's lateral rigidity carries the reaction. | Long robust thumb; thumb intrinsic muscles with large moment arms; first dorsal interosseous and opponens attachments; buttressed index | Marzke & Shackley 1986 (cutting with a small flake: "between the pollical distal phalanx and the lateral side of the second digit") [L-2nd via Williams-Hatala 2018]; *Au. afarensis* capable of it (Marzke) [L-2nd via Kivell 2015]; chimpanzees possibly [L-abs: Marzke 2015] |
| **Three-jaw chuck** | thumb, index and middle pads around a roundish object | Moments in every direction and impact. Three non-collinear opposed pads. | Thumb able to oppose two fingers at once (proportions plus a flatter trapeziometacarpal joint); FPL; broad apical tufts | Used "exclusively … during Oldowan tool production and nut-cracking with small hammerstones" (Marzke & Shackley 1986) [L-2nd via WH18]; *Au. afarensis* capable (Marzke) [L-2nd via Kivell 2015] |
| **Five-digit pad grip** ("five-jaw chuck" in Kivell 2015, fig. 1b; the task's "five-jaw cradle") | all five pads around a larger object | Large moments, with the contact polygon spanning the object | Thumb opposition reaching digits 4–5; the 5th CMC saddle rotating digit 5 toward the thumb | Kivell 2015 fig. 1 [L-full] |
| **Power squeeze grip, oblique** | handle diagonal across the palm from the hypothenar to the index base; fingers wrapped; thumb wrapped or along the handle | Forceful use of a cylinder "as an extension of the forearm": large axial and bending loads and impact | Robust 5th metacarpal and hypothenar muscles; FPL "particularly active during power squeeze grips"; Mc3 styloid; flat trapezium–Mc1 | Marzke, Wullstein & Viegas 1992 [L-abs]; Kivell 2015 [L-full]; Young 2003 (clubbing grip = Napier's power grip; throwing grip = precision grip) [L-abs] |
| **Hook / handle grip** (ape heritage) | flexed fingers 2–5 around a bar or through a ring; the thumb not needed | Weight in suspension by form closure (fingers around the bar); no squeeze needed | Long curved fingers; strong flexor sheath; MCP "double locking" | Napier 1960 [L-abs]; Richmond 2007 [L-abs]; Kivell 2015 [L-full] |
| **Precision handling** (in-hand reorientation) | fingertip gaits | – (a manipulation, not a hold) | Joint mobility plus thumb–finger proportions together | Feix 2015 [L-abs]; Marzke 1997 [L-abs]; absent in wild chimpanzees [L-abs: Marzke 2015] |

### 2.5 Morphological drivers and their robot analogues

| human feature | function (source) | Sharpa Wave analogue [M] | consequence for us [I] |
|---|---|---|---|
| Long, robust thumb relative to the fingers (intrinsic hand proportions, IHP) | Proxy for opposability and pad-to-pad grasping; the human range is above all apes. The human/australopith ratio "required little change since the LCA" and arose convergently in capuchins and geladas (Almécija 2015 [L-full]). Longer digits need less muscle force and see lower joint stress in tool use (Rolian 2011 [L-abs]). | Thumb CMC→tip 13.3 cm vs index MCP→tip 10.5 cm: ratio 1.27. The demonstrator's perceived keypoints give 1.34–1.37 (a keypoint proxy, not bone lengths). | The thumb can reach every finger pad. Opposition is a placement problem, not a morphology limit. |
| Thumb musculature: opponens and adductor pollicis with larger cross-section; most thumb muscles with larger moment arms than *Pan* | Leverage and fatigue resistance when opposing the thumb (Kivell 2015 [L-full]); larger moment arms of the intrinsic muscles that stabilise the proximal thumb joints (Marzke 1997 [L-abs]) | All 22 finger joints PD kp 1.7 N m/rad, effort 10 N m (note 24). The thumb barely closed in the ep35 wrap (2.5 %). | Robot thumb force comes only from the PD target past contact. The thumb target must be designed (pressed), not left at the copied pose. |
| **FPL** (flexor pollicis longus) | Flexes and stabilises the thumb tip. Active in power squeeze grips rather than precision pinch; not strongly active in experienced knappers' precision pinch (Kivell 2015 [L-full]). EPB and FPL make human thumb myology special, found otherwise only in hylobatids (Diogo 2012 [L-abs]). | Thumb IP joint 0–100°. | Pressing with the thumb distal phalanx along the handle is the robot analogue of the FPL squeeze. |
| **Broad apical tufts** | Support an expanded digital pulp; tuft width correlates with pulp width (Mittra 2007 [L-abs]). Listed among the features for "better manipulative control" (Kivell 2015, fig. 1 [L-full]). | Elastomer pad width 14.3 mm (thumb), 11.6 mm (fingers); pad area 2.9 / 2.1 cm². FlashCHORD folds the pads into the distal link (audits). | In our simulator a broad pad gives **no torsional friction** (condim 3, note 24). The pulp's evolved benefit does not transfer. Spread separate contacts instead (rule R2). |
| **Trapeziometacarpal (CMC) joint shape** | Humans have significantly lower curvature than *Pan*; *H. habilis* is flatter still. "Contributes to the distinctive human morphology that facilitates forceful precision and power gripping" (Marzke 2010 [L-abs]). A flatter trapezium–Mc1 joint spreads thumb loads across the wrist and palm (Kivell 2015 [L-full]). | Thumb CMC: FE −10…110°, AA ±20° (2 DoF). | Range is adequate. Load spreading has no analogue: the robot's base is rigid. |
| **Mc3 styloid** | Stabilises the carpal–metacarpal joints against thumb and palm loads (Kivell 2015 fig. 1 [L-full]); ~1.42 Ma (Ward 2014 [L-abs]). | None. But the **wrist stiffness** we control (kp 25 → 400) proved decisive [M-lead: spoon ep3 0.23–0.42 → 0.968]. | **Proximal stabilisation first** (rule R5): stiff proximal joints, compliant fingers. This is the same lesson as the styloid and the large proximal moment arms. |
| **Fifth ray**: the most robust of Mc2–5, a saddle hamate–Mc5 joint that rotates digit 5 toward the thumb | Anchors the hand in the squeeze grip (Kivell 2015 [L-full]). The fifth-finger intrinsics are recruited at high force in hammerstone and core control (Marzke 1998 EMG [L-abs]). In the non-dominant (holding) hand, digit 5 is recruited as often as, and with pressures equal to or greater than, the thumb (Key, Dunmore & Marzke 2019 [L-abs]). | Pinky CMC 0–15°. Thumb–pinky pad-to-pad volume 8.1 cm³ (dot < −0.8). | The **stabilising hand** of two-handed tasks should use thumb + digit 5 cradles (ep18 pan holder, ep2 pot holder, ep21 cup holder). |

### 2.6 What selected these grips
**Williams-Hatala et al. 2018** [L-full], 39 subjects, Pliance pressure sensors:
- Pressure distributions vary significantly by behaviour.
- **Marrow acquisition and flake production with a hammerstone** "consistently placed the greatest loads on the digits
  collectively, on each digit and on each phalanx". They are therefore the behaviours most likely to have shaped the
  hand.
- The distal phalanges carry the highest peak pressures; the thumb is highly loaded in every behaviour; digit V carries
  the lowest (20.7–75.8 kPa).
- Forceful tasks "require specialization", while low-force tasks (nut-cracking) allow "a generic hand-tool posture".

**Williams et al. 2012** [L-abs], Oldowan chopper production: peak thumb loads are lower than those on digits 2 and/or
3 in every subject. Thumb robusticity is therefore not explained by knapping loads alone.

**Rolian et al. 2011** [L-abs]: longer, more robust radial digits lower the muscle force and joint stress in tool use.
*Pan*- or australopith-like thumbs "present serious performance challenges to habitual tool use".

**Key & Lycett** [L-abs / L-full]:
- Tool-user biometrics influence handaxe loading "up to a factor of 10" more than tool form (Archaeometry 2019,
  online 2018).
- Hand size best predicts handaxe efficiency; manipulative strength best predicts flake efficiency. The Acheulean may
  have *required* near-modern hand dimensions (AAS 2018).
- Tool form has wide "free play" zones without performance effect until thresholds are crossed (JASs 2017).

**Young 2003** [L-abs]: Napier's two grips are a throwing grip (precision) and a clubbing grip (power), an alternative
selection pressure.

**Marzke et al. 2015** [L-abs]: feeding on large fruits and meat is another pressure on the thumb.

My synthesis [I]: selection acted on (i) the highest loads, (ii) the hand that stabilises, and (iii) the fit between
the hand and the object. Within performance thresholds the form drifted freely.

### 2.7 What evolution did not do
- It did not redesign proportions from scratch. Human hand proportions are largely primitive. The high thumb-to-digit
  ratio needed little change since the LCA; chimpanzees and orangutans changed instead, by convergent digital
  elongation (Almécija 2015 [L-full]).
- It reused structure built for other roles (exaptation; Gould & Vrba 1982 [L-abs]):
  - climbing grips persist in *Au. sediba* and *H. naledi* (curved phalanges, strong flexors) alongside manipulative
    features [L-abs: Kivell 2011, 2015];
  - human finger and toe proportions co-evolved through shared development, so selection on the toes for bipedalism
    "likely led to parallel phenotypic changes in the hands" that may have helped the emergence of stone tools
    [L-abs: Rolian 2010].
- No single skeletal feature reliably marks human-like precision gripping (Marzke 1997 [L-abs]). It is the
  *combination* of features that is unique, as it is for the muscles (Diogo 2012 [L-abs]).

---

## 3. Our robot hand through the evolutionary lens [M]

Source: `evolution-scripts/sharpa_opposition.py` on `right_sharpawave.urdf` plus the elastomer and MP collision meshes.

Method:
- Joints sampled uniformly within the URDF limits: thumb 60k, each finger 30k.
- Pad centre and normal from the elastomer faces that face the flexion direction (area-weighted).
- The index's radial side is the MP collision-mesh faces facing the thumb.
- 5 mm voxels.
- "Opposed" means a thumb-pad sample and a finger-surface sample share a voxel with normal dot below the threshold.
- No self-collision check, so these volumes are upper bounds.

This is in the spirit of Feix et al. 2015's thumb–index workspace overlap, not their exact metric; I could not open
their full text.

| quantity | value |
|---|---|
| thumb CMC→MCP / PP / DP to tip | 6.61 / 3.90 / 2.76 cm (total 13.27) |
| index PP / MP / DP to tip | 4.70 / 3.15 / 2.60 cm (total 10.45) |
| ratio thumb total / index digit | **1.27** (demonstrator's perceived keypoints: 1.37 R, 1.34 L; these keypoints are not bone lengths) |
| thumb CMC to index MCP; index MCP to pinky MCP (palm width) | 7.5 cm; 6.2 cm |
| thumb DoF | CMC FE −10…110°, CMC AA ±20°, MCP FE −30…80°, MCP AA ±20°, IP 0…100° |
| fifth-ray rotation | pinky CMC 0…15° (no ring CMC) |
| pad-to-pad opposition volume, dot < −0.8 (−0.7): thumb vs index / middle / ring / little | **14.9** (21.9) / 11.5 (18.3) / 7.3 (13.9) / 8.1 (12.5) cm³ |
| pad-to-side volume (thumb pad vs index MP radial side), dot < −0.8 (−0.7) | **7.5** (15.5) cm³; best dot −0.94 |
| closest opposed thumb-tip–finger-tip approach | ≤ 0.8 mm for every finger (all four can be reached) |
| maximum pad span (not necessarily opposed): thumb to index / middle / ring / little | 20.5 / 22.1 / 23.2 / 24.4 cm |
| pad width / area: thumb, finger | 14.3 mm / 2.9 cm²; 11.6 mm / 2.1 cm² |

Reading [I]:
1. The hand has a human-like thumb-to-finger proportion and full thumb opposition to all four fingers. Opposition
   shrinks from index to ring, as in humans; the volumes rank index > middle > little ≈ ring.
2. The key pinch is kinematically available but tighter than pad-to-pad, about half the volume. A key-pinch template
   should use the thumb pad against the index MP / DP side, as RL did, not the PP.
3. The lid's 17–18.5 cm rim is within the 22–23 cm thumb–middle/ring span, so a palm-down disc grasp is feasible.
4. What the robot lacks in sim is the evolved *load-sharing* anatomy: no pulp torsion, a rigid palm with no
   carpometacarpal load spreading, and weak fingers (kp 1.7 N m/rad). So the designed grasp must create the couples
   with geometry: separated contacts, buttresses, cages. It cannot rely on contact area or squeeze.

---

## 4. Design principles (a)

### 4.1 Rules (literature, then their mapping)

- **R1. Pick the grip from the geometry of the grasped part. Grasp the smallest dimension [L-abs: Feix 2014].** Across
  about 10,000 human grasps, the smallest major dimension was grasped 94 % of the time, and 96 % of grasp widths were
  ≤ 7 cm. Mapping [I]:

  | part | example | grip |
  |---|---|---|
  | thin plate (≤ 2.5 cm) | pan ring band 1.3 cm, boards 0.75–1.2 cm | pad-to-side or fingers-under / thumb-on-top |
  | ring or hole ≥ 2 cm | pan hole 2.9–3.3 cm | hook + thumb |
  | long handle with a 2–4 cm section | pot handle 15 cm × 3.1 × 2.5 cm; spoon 2.7 cm | oblique squeeze / wrap |
  | knob or disc | lid knob 4 × 7.6 cm; lid 17–18.5 cm | three-jaw chuck or five-digit disc |

- **R2. Resist every moment with separated, opposed normal forces.**
  - Evolved grips do this with long lateral surfaces (pad-to-side), three or more non-collinear pads (chucks), or a long
    palm diagonal (oblique squeeze). Humans also add pulp torsion.
  - In our simulator torsional friction is absent (condim 3; note 24, Newton source) and the pyramidal cone's worst-case
    μ is μ/√2 (note 24). Contact separation along the lever is therefore the only lever.
  - Required couple force F ≈ m g d / s, where d is the lever to the centre of mass and s is the contact separation.
- **R3. Put the thumb on the object, opposed, and pressed.**
  - Forceful thumb opposition is the core of the human hand (Marzke 1997, 2013; Skinner 2015).
  - Its absence is the common feature of our failing designed grasps (section 0).
  - The thumb target needs its own press past contact. The ape solution is the finger-only hook or double-lock, which is
    acceptable only for pure suspension.
- **R4. Separate the roles of the two hands.**
  - The non-dominant (stabilising) hand in knapping uses digit 5 and the thumb heavily (Key 2019; Marzke 1998).
  - Stabilising hands are: the ep18 pan holder, the ep2 pot holder, the ep21 cup holder, and the ep24 board-1 holder
    during insertion. They need cradles and clamps that resist the *other* hand's loads (brushing push, lid lift,
    pouring).
  - Tool hands are the sweeper, lid and pitcher. They need squeeze or handle grips.
- **R5. Stabilise proximally, comply distally.**
  - Evolution added proximal stabilisers: larger moment arms of the proximal thumb stabilisers (Marzke 1997), the Mc3
    styloid and the CMC joint shapes (Kivell 2015).
  - Our measured analogue is the stiff kp 400 wrist [M-lead].
- **R6. Grip force follows the load; specialise only where the load is high.**
  - Low-load tasks allow "a generic hand-tool posture"; high-load tasks need specialised grips (Williams-Hatala 2018).
  - Grip-force/load coupling is covered in note 24 (Johansson & Westling; Flanagan).
  - The lid is lost within ±4 frames of the lift onset in every variant [M-lead]. So evaluate and specialise grasps
    around load changes, not over average frames.
- **R7. Use form closure where the object offers it.** The ring hole (pan, sweeper) and the pitcher handle allow
  fingers *through* the part: caging that holds weight with no squeeze. That is the ape hook. RL used it for the long
  lift.

### 4.2 Mini dust pan (ep18 left, ep39)

Geometry [M-lead]: plate 17.3 × 15.8 cm; ring handle hole Ø 2.9 cm (3.0 × 3.8); end band 2.0 cm wide × 1.3 cm thick
(our mesh; the real sheet is 4–8 mm).

**Grip: pad-to-side across the end band (as RL found).**
- Thumb pad and PP on the top face at axis1 −8.5…−9 cm.
- Index MP radial side and DP pad under the band, 2–2.5 cm closer to the pan; index tip in the ring hole as a
  locating peg.
- Palm up, approaching low and sideways *above* the table plane. Closing from below flicked the pan by 63–80 mm.

**Mechanics [I, estimate].** If the pan has the 0.3 kg placeholder mass measured for the spoon and pot:
- the horizontal lever from the band to the centre of mass is about 8.75 cm, so M ≈ 0.26 N m;
- with s ≈ 2.25 cm, the couple needs about 11 N per side;
- one finger joint at kp 1.7 N m/rad with the 0.4 rad squeeze gives 0.68 N m, about 14 N at a 5 cm lever. This is
  enough, *if* both sides touch. With the thumb 20 mm off the couple is zero and the pan pivots, as observed.

Note: in 70 % of its held frames the RL policy kept the pan's far lip on the table [M-lead]. It used the table as a
third contact to carry this moment until the lift.

**Lift: hook + thumb.** The middle and ring fingers go through the hole (two 11.6 mm pads in a 29–33 mm hole) and carry
the weight by caging. The thumb on top supplies the counter-moment, otherwise the pan swings to hang with its centre of
mass below the hook. This is a grip change within the hold, which the grasp lock must allow (the boards audit asks for
the same).

### 4.3 Mini sweeper / hand brush (ep18 right; ep31)

Geometry [M-lead]: plate 14.4 × 11.0 × 3.35 cm; bristle head 12–17 mm; ring hole Ø 2.0 cm; band 1.8 × 2.5 cm.

**Grip.** The loss was timing, so the type matters less. Two candidates:
- the human ring clamp: thumb on one face, three fingers on the other;
- RL's neck clamp: the thumb column on one face, four fingers flat on the other, palm against the near edge.

RL's version is a palm-buttressed clamp. The palm provides form closure against the in-plane brushing push, and the
face clamp provides friction [I]. Evolution's analogue is the squeeze grip's use of the palm as a stop. Prefer the neck
clamp: it is 10 cm closer to the centre of mass, so the lever and the couple force are smaller.

**ep31:** no grasp change (start geometry).

### 4.4 Flat boards (ep24, wooden_piece_1 / 2)

Geometry [M-lead]: 22.9 × 13.2–13.8 cm; solid thickness 7.5 / 12.0 mm (ours; scan 9.1 mm for board 2); cross-lap slot.

**Grip: fingers-under, thumb-on-top plate pinch**, the human's (MANO contacts: board 2 at f128 has the thumb 2.0 cm
above, middle / ring / pinky 2.0–3.8 cm below, inside the footprint) [M-lead]. In this simulator the fingers may go
through the table to get under [M-lead: `robot_support_collision: false`].

**Mechanics [I, estimate].**
- Fingers under at x_f from the edge, thumb on top near the edge at separation s, centre-of-mass lever d from the
  fingers.
- Then F_thumb = m g d / s and F_fingers = m g (1 + d / s).
- Gripping the long edge (centre of mass 6.6 cm in), with fingers 4 cm in and s = 3 cm: d = 2.6 cm, so F_thumb ≈ 0.87
  mg ≈ 2.6 N and F_fingers ≈ 5.5 N at 0.3 kg.
- The deep fingers make this the cheapest plate grip. That is why it is the human default for plates.

For the long axis (lever 11.4 cm) use two hands, as the human did for board 1 (two-hand phase f40–60).

### 4.5 Water pitcher (ep21)
**Start first:** support-consistent base (audit). Then the **hook + thumb handle grip**: fingers through the handle
carry the weight; the thumb on top of the handle counters the pouring moment (R7 + R3). The human contacts are pinky3
0.92, thumb2 0.86, ring2 0.72, palm 0.33 [M-lead], a handle grip with the thumb.

### 4.6 White pot (ep26, ep27) and its lid (ep2)

**Pot geometry [M]:** our white_pot mesh has one long handle, protruding 15.2 cm beyond the body (cross-section 3.1 ×
2.5 cm), on a 19.1 cm body.

**Pot grip: oblique squeeze** with the handle diagonal across the palm and the thumb along the handle. Close until
contact (audit: tolerate 2 cm / 10°).

**Pot mechanics [I, estimate].**
- At 0.3 kg with the grip at mid-handle (lever about 17 cm to the body centre), the pitch moment is M ≈ 0.50 N m.
- A transverse four-finger wrap spreads contacts over about 6.2 cm (the palm width), so F ≈ 8 N.
- An oblique crossing of about 25–30° lengthens the palm contact to about 7 cm. The thumb pad along the far side adds
  about 3 cm, giving s ≈ 9–10 cm and F ≈ 5 N: about a 35–40 % lower couple force.
- This is the mechanical reason the squeeze grip makes a cylinder "an extension of the forearm" (Marzke 1992).
- Test it as H3. Note 24 already exposes `--oblique_deg` (its H2 is untested).

**Lid geometry [M]:** 18.5 × 16.9 × 5.2 cm; knob 4.0 × 7.6 cm (top 15 mm).

**Lid grip.** Two options:
- the human's palm-down rim grasp (palm over the knob, fingers and thumb on opposite sides of the rim; span 17–18.5 cm,
  within the Sharpa's 22–23 cm thumb–middle/ring span);
- a three-jaw chuck across the 4 cm knob, with the index and middle pads spread along its 7.6 cm length.

In either case the contact normals must oppose (R2/R3). The grip force must ramp *with* the lift (R6), not as a
pre-lift squeeze; the audit's mechanism is that the squeeze on non-opposed contacts expels the lid.

### 4.7 What the grasp lock cannot copy from evolution
- Precision handling (in-hand reorientation) is uniquely human and absent in wild chimpanzees (Marzke 2015).
- A locked grasp cannot reorient an object in the hand. ep35's 140° spoon turn is one such case [M-lead].
- Either change grips between holds (re-grasp), or leave the reorientation to the RL fine-tune.

---

## 5. What the evolutionary process suggests for search (b)

### 5.1 Process features and the algorithm that embodies each

| feature of hand evolution (evidence) | algorithmic counterpart | EA variant that embodies it | concrete use in our grasp search |
|---|---|---|---|
| **Variation + selection under task pressure** (WH18; Rolian 2011; Key & Lycett 2018/19) | Population, mutation, recombination, selection on fitness | Every EA. CMA-ES (μ/μ_w, λ): weighted recombination of the best μ, adaptive covariance (Hansen & Ostermeier 2001; Hansen 2016 [L-full]). GA: tournament, crossover, mutation (as in DexEvolve [L-abs]). | Fitness = kit ADD-AUC of the object vs **our** reference over the hold window, as `tools/grasp_evolve.py` already does. |
| **Selection by the most stressful loads, not the average** (marrow and flake percussion load the digits most, WH18; the lid lost at the lift onset) | Multi-objective or worst-case fitness; robust, noisy evaluation | NSGA-II / lexicase / CMOEA over per-phase objectives (Huizinga & Clune 2018 [L-abs]); re-evaluation under perturbation | Objectives per phase: no knock on approach, acquisition, **lift-onset ± 10 frames**, carry, release. Score each candidate as the minimum over the note-24 perturbation set (wrist ±5 mm / ±2.5°, fingers ±0.05 rad, ×1.25 time). |
| **A small reusable repertoire** (Napier's two patterns cover all prehension [L-abs]; 33 grasp types reduce to 17 [L-full: Feix 2009]; adults use fewer strategies than juveniles [L-abs: Pouydebat 2011]) | An archive of diverse high performers, indexed by behaviour descriptors, reused for adaptation | **MAP-Elites / quality diversity** (Mouret & Clune 2015); CVT-MAP-Elites for many descriptors (Vassiliades 2016); a repertoire plus fast adaptation, "adapt … in less than two minutes" (Cully 2015) [all L-abs] | An archive per object class. Descriptors: grip type (pad-to-side, hook, squeeze, chuck, plate pinch) × contact site along the part × approach direction. Seed each new hold, and each eval twin (public ep39 → eval 38), from the archive; adapt with CMA-ES. Fitness uses our perception only, so this is legitimate at inference. |
| **Exaptation and stepping stones** (features built for one role co-opted for another, Gould & Vrba 1982; climbing grips retained, Kivell 2011/2015; hand change as a by-product of foot selection, Rolian 2010; tool use before the full anatomy, Harmand 2015, Skinner 2015) | Solutions to one subtask become seeds for another; goal switching | **Novelty search / NSLC** (Lehman & Stanley 2011 [L-abs; NSLC known only through the publisher record and S2 TLDR]); MAP-Elites (cells seed each other); POET's transfer between environments, "fortuitous stepping stones" (Wang 2019 [L-abs]); CMOEA (all subtask combinations) | Cross-object seeding: RL's ep18 key pinch → the ep39 / eval-38 pan; the hook through the pan ring → the pitcher handle; the spoon wrap → the pot handle. Keep elites of sub-goals (acquired / lifted / carried) as stepping stones, not just the full-hold best. |
| **Gradual, mosaic complexification** (derived features arrive stepwise from ~3.4 Ma to < 1.5 Ma, Tocheri 2008; Mc3 styloid 1.42 Ma, Ward 2014; *Au. sediba* mosaic) | Start from a minimal genome; add structure; protect new structure while it is tuned | **NEAT**: "incrementally growing from minimal structure" and "protecting structural innovation using speciation" (Stanley & Miikkulainen 2002 [L-abs]); IPOP restarts with increasing population (cited in Hansen 2016) | Staged genome: (1) wrist 6-DoF offset only; (2) + 3–5 finger synergy amplitudes (close, thumb press, spread); (3) + 22 joint offsets; (4) + timing (closure frame, ramp). Keep a stage's newcomers for a few generations before culling (Cheney's protection). |
| **Morphology–behaviour co-evolution** (hand dimensions gate tool efficiency, Key & Lycett 2018; biometrics matter up to 10× more than tool form, Key & Lycett 2019) | Optimise body and controller together; protect morphological change | Co-optimisation with "morphological innovation protection" (Cheney et al. 2017 [L-abs]); Sims 1994 [L-abs]; developmental change speeds robust behaviour (Bongard 2011 [L-abs]) | Our "morphology" is what we can change around the fixed hand: the reference (the grasp design), the embodiment gains (wrist kp 400 was decisive), and the collision meshes (support fill). Search grasp and embodiment parameters together; give a new grip type a grace period. |
| **Learning guides evolution (Baldwin effect)** | Evolution selects what learning can finish; learning smooths the landscape | Hinton & Nowlan 1987 [L-abs]; DERL: "evolution rapidly selects morphologies that learn faster", which are more stable and easier to learn with (Gupta 2021 [L-abs]); ERL (Khadka & Tumer 2018), CEM-RL (Pourchot & Sigaud 2018), PBT (Jaderberg 2017) [L-abs] | The split: evolve the grasp-lock reference, then the RL fine-tune learns the closed-loop residual. Select edits by *robust* zero-action fitness as a proxy for learnability (H6). |
| **Convergence** (the human thumb ratio arose convergently in other dexterous anthropoids, Almécija 2015; our RL found the human key pinch) | Similar pressures lead to similar solutions, so human grips are valid priors | Seeded search; edit one demonstration (DemoGrasp [L-abs]) | Seed with the copied human grasp, the evolved-grip templates of §4 and the RL-discovered grasps. |
| **Free play and thresholds** (tool form varies freely until performance thresholds, Key & Lycett 2017 [L-full]) | Neutral plateaus in fitness | QD illuminates plateaus (Mouret & Clune 2015). CMA-ES is rank-based and invariant to monotone fitness transforms (Hansen 2016 [L-full]), but it drifts on flat plateaus. | Break ties with margins (worst case over perturbations) and with secondary objectives (contact count, thumb on object, slip). |
| **Juvenile exploration, then narrowing** (Pouydebat 2011) | Broad exploration, then exploitation | CMA-ES step-size adaptation (σ shrinks by itself); MAP-Elites illumination, then CMA-ME emitters (Fontaine 2019 [L-abs]) | Broad σ at generation 0 (wrist 2 cm / 0.15 rad / fingers 0.15 rad, the tool's defaults), then let CMA shrink it. |
| **Deception and sparse interaction** (RL grasp-lock fine-tunes learn contact avoidance: ep18 0.446 at 10M → 0.060 at 70M [M-lead]) | The objective misleads; most samples never touch the object | Novelty search beats the objective on deceptive tasks (Lehman & Stanley 2011). But for grasping, "sparse interaction can lead to deceptive novelty" and success-prioritised MAP-Elites wins (Huber 2023 [L-abs]); QD with priors speeds grasp sampling (Huber 2024 [L-abs]). | Do **not** run pure novelty search. Seed near contact (human copy and templates); use success-prioritised QD selection. |

### 5.2 One line per algorithm family

| family | embodies | fit for our problem [I] |
|---|---|---|
| **CMA-ES** | Variation/selection with an adaptive mutation distribution; rank-based; derandomised. A speed-up of orders of magnitude on badly scaled, non-separable problems (Hansen & Ostermeier 2001). | **Primary local optimiser** for the 28-D edit: default λ = 13, run as 16 worlds per batch, 8–12 generations. Already implemented (`tools/grasp_evolve.py`). |
| **GA** (tournament, uniform crossover, Gaussian mutation, elitist archive) | Recombination of building blocks, e.g. a thumb placement from one parent and the finger closure from another | Useful when the archive holds different grip types. Crossover of joint vectors across types is mostly destructive [I]; crossover within a type is sensible. Implemented as `--algo ga`. |
| **MAP-Elites / QD** (CVT, CMA-ME) | Repertoire, stepping stones, illumination of plateaus | **Repertoire layer** across holds and episodes. Use success-prioritised selection (Huber 2023). |
| **Novelty search / NSLC** | Escape from deception; open-ended discovery | Only as a minor emitter inside QD, because of the sparse-interaction deception. |
| **NEAT-style complexification** | Minimal start, growth, protection of innovation | Apply to the **genome layout** (staged parameters), not to neural topology. |
| **ES as an RL alternative** (OpenAI-ES, ARS, deep GA) | Black-box policy search; invariant to action frequency and delayed rewards; long horizons; scalable (Salimans 2017; Mania 2018; Such 2017 [L-abs]) | Not for the 22+6-D closed-loop policy here: RL already works. Keep for low-dimensional open-loop parts. |
| **EA + RL hybrids** (ERL, CEM-RL, PBT, DERL) | Baldwinian division of labour | **Recipe shape**: evolve the reference grasp, RL-fine-tune. PBT-style selection among fine-tune checkpoints is what we do with 3–5 evaluations per checkpoint. |

### 5.3 Do evolutionary algorithms give an edge over RL here?

**Measured [M-lead], from the work log of 24 Oct:**

| episode | method | result | cost | caveat |
|---|---|---|---|---|
| ep39 | CMA-ES grasp edit (round 1: pop 16 × 8 generations, window f22–122; round 2: 8 worlds × 12 generations, f22–312), baked, zero action, full episode | sim_vs_ref **0.877** (onset anchor alone 0.164; old grasp lock 0.176 = floor) | round 1: 16–21 s × 8 generations; round 2: 45–75 s × 12 generations; about 11–18 min on 4 shared CPUs | CPU physics. Fitness vs our reference. One episode. Fresh-process replay, so not affected by the leakage bug. |
| ep39 | standard FDR RL, 250M steps | sim_vs_ref 0.826; registered AUC 0.802 ± 0.280 (4 of 5 rollouts 0.94) | about 1.6 GPU-h | GPU, official evaluator |
| ep18, ep24 | CMA-ES | pan 0.211 → 0.404 in search, 0.354 replay; sweeper search did not reproduce (0.584 in search, 0.374 fresh) | – | **Contaminated**: simulator state leaked across generations (`bbe57e6`, `72d60cb`). Rerun pending; no conclusion yet. |

**Literature [L-abs]:**
- With a compact policy parameterisation (dynamic movement primitives), the black-box (μ_W, λ)-ES "empirically
  outperforms" the RL algorithm PI² and shares its core (Stulp & Sigaud 2013).
- Random search on linear policies matches RL sample efficiency on MuJoCo and is at least 15× more compute-efficient
  (Mania 2018).
- ES and GAs are competitive on deep RL benchmarks (Salimans 2017; Such 2017).
- EAs suffer "high sample complexity" with many parameters (Khadka & Tumer 2018).
- Novelty search can solve deceptive problems that reward maximisers fail (Lehman & Stanley 2011; Such 2017).

**Assessment [I]:**
- *Where evolution has the edge:* the discrete, structural decision of where, how and when to grasp. It is a small
  parameter space (6–30 numbers) with a deceptive, sparse reward (contact or not, lift or not), evaluated by
  deterministic batched rollouts (one candidate per world). RL fine-tunes from a grasp that does not acquire the object
  learn avoidance (ep18 0.446 → 0.060), the classic deception that population search sidesteps. The one clean
  measurement (ep39) shows a CPU-minutes search beating 1.6 GPU-h of RL at zero action.
- *Where RL keeps the edge:* closed-loop correction during the whole episode. The evaluator runs the policy from frame
  0 with no assist, and the evolved edit is open-loop. The kp-400 fine-tunes on the spoon (0.968–0.978) show what the
  RL stage adds once the grasp is right.
- *So:* hand evolution itself split the work, with selection fixing the repertoire and anatomy and the individual
  learning the skill (Baldwin). The recipe should do the same, with grasp search plus a short RL fine-tune. Whether the
  fine-tune is still needed after a good evolved grasp is testable (H7).
- If the owner wants to submit an evolved reference with a zero-output policy, check first that the organisers' rules
  accept it (open question).

### 5.4 A concrete search design for the recipe [I]

**1. Seeds (convergence and exaptation):**
- the copied human grasp;
- the §4 template for the part type (key pinch / hook / squeeze / plate pinch / chuck);
- RL-discovered grasps from other episodes, mapped by the part type.

**2. Genome (complexification):** staged as in §5.1. Each stage runs CMA-ES with λ = 4 + ⌊3 ln n⌋ (n = 6 → 9, n = 11 →
11, n = 28 → 13), rounded up to the batch width (16).

**3. Fitness (selection by the hardest loads).** Each candidate is scored in two parts:
- a hold-window AUC that weights the lift onset ± 10 frames and the release;
- the minimum over a small perturbation set (3–5 worlds per candidate).

Use secondary tie-breaks: thumb in contact, number of opposed contacts, slip in the palm frame.

**4. Repertoire (QD).** Keep the elites per grip-type × site cell across holds. Re-use them for the eval twin.

**5. Hand-off (Baldwin).** Bake the best robust edit and run the existing 70M fine-tune. Choose checkpoints by 3–5
repeated sim_vs_ref evaluations, as now.

**6. Hygiene [M-lead].** Use a fresh environment per generation; clear the warm start. Confirm every search best by a
fresh-process replay of the baked reference, and on the GPU before training.

---

## 6. Hypotheses and the experiments that would falsify them

Each hypothesis is followed by its test and its cost; a hypothesis is falsified by the result named in its test.

**H1. A pad-to-side (key pinch) seed beats the copied-clamp seed.** It reaches a higher hold-window AUC on the ep18 pan
than the clamp-seeded CMA-ES at equal budget (8 worlds × 12 generations), and lifts the pan at zero action.
- Test: falsified if the key-pinch-seeded best is not ≥ 0.05 higher than the rerun clamp-seeded best (fresh-process
  replays both), or the pan is not lifted ≥ 10 cm at zero action.
- Cost: CPU, about 2 × 15–25 min.

**H2. The R1 geometry rule picks the grip that humans or RL used.** The rule (thin plate → pad-to-side / plate pinch;
ring → hook + thumb; long handle → squeeze; knob/disc → chuck/disc) matches the MANO or RL contact pattern.
- Test: across the holds of the 7 failed + 3 successful public episodes (about 14 holds), falsified if the rule
  disagrees with the human MANO contact pattern in > 2 holds (with the RL-discovered grip where available).
- Cost: CPU, < 1 h, no simulation.

**H3. An oblique squeeze grip on the pot handle cuts in-hand pot rotation by ≥ 30 % vs the transverse wrap.** Run at
`--oblique_deg` 25–30 on the ep27 and ep26 (GT-relative start) holds.
- Test: zero-action CPU replay; falsified if the in-palm rotation over the carry is not reduced by ≥ 30 %, or the lift
  height falls.
- Cost: CPU, about 1 h.

**H4. Repertoire transfer halves the search.** A MAP-Elites archive seeded on public ep39 (pan) reaches the same window
AUC on eval 38's pan hold in ≤ 1/3 of the cold-start generations.
- Test: falsified if the warm start needs > 1/2 of the cold-start generations to reach the cold-start best.
- Cost: CPU about 1 h, or GPU about $1 (owner's approval needed for GPU). Fitness uses our perception only, so this is
  inference-legal.

**H5. Staged complexification beats the flat 28-D CMA-ES.** The sequence wrist → synergies → joints → timing gets a
better best fitness at equal evaluation budget.
- Test: on 3 holds (ep39 pan, ep18 pan, ep24 board 1), falsified if staged ≤ flat on 2 of 3 holds at an equal budget of
  about 200 evaluations each.
- Cost: CPU, about 2–3 h total.

**H6. Robust fitness predicts learnability (Baldwin).** The worst-case zero-action fitness over perturbations predicts
the 70M fine-tune's final sim_vs_ref better than the nominal fitness.
- Test: falsified if the Spearman ρ over ≥ 6 (episode, edit) pairs is not higher for the robust fitness.
- Cost: about 6 fine-tunes, roughly $8–12 GPU (estimate; owner's go-ahead needed).

**H7. After a good evolved grasp, the RL fine-tune adds little.** It adds ≤ 0.03 registered AUC.
- Test: on ep39, compare the evolved reference at zero action (GPU, official evaluator) with the same plus the 70M
  fine-tune, 5 evaluations each. Falsified if the fine-tune adds > 0.03.
- Cost: about $2–3 GPU (estimate).

**H8. Pure novelty search under sparse contact finds fewer lifting edits than CMA-ES at equal budget** (Huber 2023's
deceptive novelty).
- Test: on ep39 pan, novelty only (descriptor = final object pose) vs CMA-ES, 200 evaluations each. Falsified if
  novelty finds ≥ as many edits with lift ≥ 10 cm.
- Cost: CPU, about 1 h. Low priority.

**H9. Contact separation, not contact count, decides plate holds.** Under the no-torsion simulator, the hold-window AUC
of plate grips correlates with the opposed-contact separation along the lever (s in F = mgd/s) more than with the
number of contacts.
- Test: over the CMA-ES population logs of the plate holds, falsified if the partial correlation of AUC with s is not
  > that with the contact count.
- Cost: CPU, minutes (log analysis), once contact logging is on.

---

## 7. Open questions
- Napier 1956 and 1962 (Nature), Marzke & Wullstein 1996, Marzke & Shackley 1986 and Feix et al. 2015 could not be
  opened in full from this environment (paywalls or captcha). Their specific numbers are therefore not used. For
  example, Feix's opposition volumes for humans would let us normalise our §3 volumes against the human hand.
- Is the placeholder mass 0.3 kg for every object, or only for the spoon and pot? The §4 force estimates scale
  linearly with it.
- Is an evolved reference with a zero-output policy an acceptable submission under the challenge rules? Owner or
  organisers.
- Is the human's dust-pan grip in ep18 the same key pinch as RL's? The plate audit says the human used a thumb–fingers
  clamp with palm contact 0–13 %. A finer MANO contact-face analysis would tell whether evolution's prediction (key
  pinch) holds for this demonstrator.
- Self-collision is not checked in §3. A collision-filtered version of the volumes would tighten the key-pinch number.

## 8. Caveats
- The §4 forces are statics estimates with an assumed mass and assumed contact positions. They show orders of
  magnitude and directions, not tested values.
- The §3 volumes are kinematic upper bounds from uniform joint sampling. They are not task-feasible grasp sets.
- The demonstrator's hand proportions come from perceived keypoints (`hands.npz`, ep39, our perception). They are not
  bone lengths and not ground truth.
- [M-lead] numbers come from the work log and the parallel audits. Where those runs had bugs (the ep18 / ep24 search
  leakage) I say so; I did not re-run them.

---

## 9. References

"Read" gives what I opened. Most PubMed records were retrieved through NCBI E-utilities; the PubMed URL is given.

### Hand evolution and primate grips

| reference | source | read |
|---|---|---|
| Napier JR 1956. The prehensile movements of the human hand. J Bone Joint Surg Br 38-B:902–913. | https://boneandjoint.org.uk/Article/10.1302/0301-620X.38B4.902 ; https://pubmed.ncbi.nlm.nih.gov/13376678/ | abstract |
| Napier JR 1960. Studies of the hands of living primates. Proc Zool Soc Lond 134:647–657. | https://doi.org/10.1111/j.1469-7998.1960.tb05606.x (abstract via the OpenAlex record) | abstract |
| Napier J 1962. Fossil hand bones from Olduvai Gorge. Nature 196:409–411. | https://www.nature.com/articles/196409a0 | record only |
| Napier J 1962. The evolution of the hand. Sci Am 207:56–62. | https://pubmed.ncbi.nlm.nih.gov/13937573/ | record only |
| Leakey LSB, Tobias PV, Napier JR 1964. Nature 202:7–9. | https://pubmed.ncbi.nlm.nih.gov/14166722/ | record only |
| Marzke MW 1997. Precision grips, hand morphology, and tools. Am J Phys Anthropol 102:91–110. | https://pubmed.ncbi.nlm.nih.gov/9034041/ | abstract |
| Marzke MW 2013. Tool making, hand morphology and fossil hominins. Phil Trans R Soc B 368:20120414. | https://pubmed.ncbi.nlm.nih.gov/24101624/ (PMC4027422) | abstract |
| Marzke MW, Wullstein KL 1996. Chimpanzee and human grips: a new classification with a focus on evolutionary morphology. Int J Primatol 17:117–139. | https://doi.org/10.1007/BF02696162 | record + Semantic Scholar TLDR only |
| Marzke MW, Wullstein KL, Viegas SF 1992. Evolution of the power ("squeeze") grip and its morphological correlates in hominids. Am J Phys Anthropol 89:283–298. | https://pubmed.ncbi.nlm.nih.gov/1485637/ | abstract |
| Marzke MW et al. 1998. EMG study of hand muscle recruitment during hard hammer percussion manufacture of Oldowan tools. Am J Phys Anthropol 105:315–332. | https://pubmed.ncbi.nlm.nih.gov/9545075/ | abstract |
| Marzke MW et al. 2010. Trapeziometacarpal joint surface curvatures. Am J Phys Anthropol 141:38–51. | https://pubmed.ncbi.nlm.nih.gov/19544574/ | abstract |
| Marzke MW et al. 2015. Grips and hand movements of chimpanzees during feeding in Mahale Mountains National Park. Am J Phys Anthropol 156:317–326. | https://pubmed.ncbi.nlm.nih.gov/25363236/ | abstract |
| Marzke MW, Shackley MS 1986. J Hum Evol 15:439–460. | https://doi.org/10.1016/S0047-2484(86)80027-6 | secondary, via Williams-Hatala 2018 |
| Susman RL 1994. Fossil evidence for early hominid tool use. Science 265:1570–1573. | https://pubmed.ncbi.nlm.nih.gov/8079169/ | abstract |
| Tocheri MW, Orr CM, Jacofsky MC, Marzke MW 2008. J Anat 212:544–562. | https://pubmed.ncbi.nlm.nih.gov/18380869/ (PMC2409097) | abstract |
| Kivell TL 2015. Evidence in hand: recent discoveries and the early evolution of human manual manipulation. Phil Trans R Soc B 370:20150105. | https://kar.kent.ac.uk/56810/1/RSTB20150105p.pdf | full text |
| Skinner MM et al. 2015. Human-like hand use in *Australopithecus africanus*. Science 347:395–399. | https://pubmed.ncbi.nlm.nih.gov/25613885/ | abstract |
| Almécija S, Smaers JB, Jungers WL 2015. The evolution of human and ape hand proportions. Nat Commun 6:7717. | https://pubmed.ncbi.nlm.nih.gov/26171589/ (PMC4510966, full text via E-utilities) | full text |
| Feix T, Kivell TL, Pouydebat E, Dollar AM 2015. Estimating thumb–index finger precision grip and manipulation potential in extant and fossil primates. J R Soc Interface 12:20150176. | https://pubmed.ncbi.nlm.nih.gov/25878134/ | abstract |
| Williams-Hatala EM et al. 2018. The manual pressures of stone tool behaviors and their implications for the evolution of the human hand. J Hum Evol 119:14–26. | https://kar.kent.ac.uk/66573/1/Williams-Hatala%20et%20al.%252c%202018_accepted_complete.pdf ; https://pubmed.ncbi.nlm.nih.gov/29685751/ | full text (accepted manuscript) |
| Williams EM, Gordon AD, Richmond BG 2012. Hand pressure distribution during Oldowan stone tool production. J Hum Evol 62:520–532. | https://pubmed.ncbi.nlm.nih.gov/22446065/ | abstract |
| Key AJM, Lycett SJ 2011. Technology based evolution? J Archaeol Sci 38:1663–1670. | https://doi.org/10.1016/j.jas.2011.02.032 | record + TLDR only |
| Key AJM, Lycett SJ 2017. Form and function in the Lower Palaeolithic. J Anthropol Sci 95:67–108. | https://kar.kent.ac.uk/62490/1/Key%20and%20Lycett%20In%20Press.pdf | full text |
| Key AJM, Lycett SJ 2018. Investigating interrelationships between Lower Palaeolithic stone tool effectiveness and tool user biometric variation. Archaeol Anthropol Sci 10:989–1006. | https://kar.kent.ac.uk/58392/3/REVISED%20Key%20Lycett%20OCTOBER%2024_2016.pdf | abstract |
| Key AJM, Lycett SJ 2019. Biometric variables predict stone tool functional performance more effectively than tool-form attributes. Archaeometry 61:539–555 (online 2018). | https://doi.org/10.1111/arcm.12439 (abstract via Crossref) | abstract |
| Key AJM, Dunmore CJ, Marzke MW 2019. The unexpected importance of the fifth digit during stone tool production. Sci Rep 9:16724. | https://pubmed.ncbi.nlm.nih.gov/31723201/ | abstract |
| Young RW 2003. Evolution of the human hand: the role of throwing and clubbing. J Anat 202:165–174. | https://pubmed.ncbi.nlm.nih.gov/12587931/ | abstract |
| Ward CV et al. 2014. Early Pleistocene third metacarpal from Kenya. PNAS 111:121–124. | https://pubmed.ncbi.nlm.nih.gov/24344276/ | abstract |
| Rolian C, Lieberman DE, Zermeno JP 2011. Hand biomechanics during simulated stone tool use. J Hum Evol 61:26–41. | https://pubmed.ncbi.nlm.nih.gov/21420144/ | abstract |
| Rolian C, Lieberman DE, Hallgrímsson B 2010. The coevolution of human hands and feet. Evolution 64:1558–1568. | https://pubmed.ncbi.nlm.nih.gov/20624181/ | abstract |
| Mittra ES, Smith HF, Lemelin P, Jungers WL 2007. Comparative morphometrics of the primate apical tuft. Am J Phys Anthropol 134:449–459. | https://pubmed.ncbi.nlm.nih.gov/17657781/ | abstract |
| Diogo R, Richmond BG, Wood B 2012. J Hum Evol 63:64–78. | https://pubmed.ncbi.nlm.nih.gov/22640954/ | abstract |
| Harmand S et al. 2015. 3.3-million-year-old stone tools from Lomekwi 3. Nature 521:310–315. | https://pubmed.ncbi.nlm.nih.gov/25993961/ | abstract |
| Pouydebat E et al. 2011. Diversity of grip in adults and young humans and chimpanzees. Behav Brain Res 218:21–28. | https://pubmed.ncbi.nlm.nih.gov/21074572/ | abstract |
| Kivell TL et al. 2011. *Australopithecus sediba* hand. Science 333:1411–1417. | https://pubmed.ncbi.nlm.nih.gov/21903806/ | abstract |
| Kivell TL et al. 2015. The hand of *Homo naledi*. Nat Commun 6:8431. | https://pubmed.ncbi.nlm.nih.gov/26441219/ | abstract |
| Bardo A et al. 2018. The impact of hand proportions on tool grip abilities. J Hum Evol 125:106–121. | https://pubmed.ncbi.nlm.nih.gov/30502891/ | abstract |
| Richmond BG 2007. Biomechanics of phalangeal curvature. J Hum Evol 53:678–690. | https://pubmed.ncbi.nlm.nih.gov/17761213/ | abstract |
| Feix T, Bullock IM, Dollar AM 2014. Analysis of human grasping behavior: object characteristics and grasp type. IEEE Trans Haptics 7:311–323. | https://pubmed.ncbi.nlm.nih.gov/25248214/ | abstract |
| Feix T, Pawlik R, Schmiedmayer H-B, Romero J, Kragić D 2009. A comprehensive grasp taxonomy. | https://www.csc.kth.se/grasp/taxonomyGRASP.pdf | full text (2 pages) |
| Gould SJ, Vrba ES 1982. Exaptation—a missing term in the science of form. Paleobiology 8:4–15. | https://doi.org/10.1017/S0094837300004310 (Cambridge abstract) | abstract |

### Evolutionary computation and its relation to RL

| reference | source | read |
|---|---|---|
| Hansen N, Ostermeier A 2001. Completely derandomized self-adaptation in evolution strategies. Evol Comput 9:159–195. | https://pubmed.ncbi.nlm.nih.gov/11382355/ | abstract |
| Hansen N 2016. The CMA evolution strategy: a tutorial. | https://arxiv.org/abs/1604.00772 | full text (λ default, invariances) |
| Salimans T et al. 2017. Evolution strategies as a scalable alternative to RL. | https://arxiv.org/abs/1703.03864 | abstract |
| Such FP et al. 2017. Deep neuroevolution: GAs are a competitive alternative. | https://arxiv.org/abs/1712.06567 | abstract |
| Mania H, Guy A, Recht B 2018. Simple random search. | https://arxiv.org/abs/1803.07055 | abstract |
| Mouret J-B, Clune J 2015. Illuminating search spaces by mapping elites. | https://arxiv.org/abs/1504.04909 | abstract |
| Vassiliades V et al. 2016. CVT-MAP-Elites. | https://arxiv.org/abs/1610.05729 | abstract |
| Fontaine MC et al. 2019. CMA-ME. | https://arxiv.org/abs/1912.02400 | abstract |
| Cully A, Clune J, Tarapore D, Mouret J-B 2015. Robots that can adapt like animals. | https://arxiv.org/abs/1407.3501 | abstract |
| Lehman J, Stanley KO 2011. Abandoning objectives: evolution through the search for novelty alone. Evol Comput 19:189–223. | https://pubmed.ncbi.nlm.nih.gov/20868264/ | abstract |
| Lehman J, Stanley KO 2011. Novelty search and local competition. GECCO. | https://doi.org/10.1145/2001576.2001606 | record + TLDR only |
| Stanley KO, Miikkulainen R 2002. NEAT. Evol Comput 10:99–127. | https://nn.cs.utexas.edu/downloads/papers/stanley.ec02.pdf | abstract |
| Sims K 1994. Evolving virtual creatures. SIGGRAPH. | https://www.karlsims.com/papers/siggraph94.pdf | abstract and intro |
| Cheney N, Bongard J, SunSpiral V, Lipson H 2017. Scalable co-optimization of morphology and control. | https://arxiv.org/abs/1706.06133 | abstract |
| Bongard J 2011. Morphological change in machines accelerates the evolution of robust behavior. PNAS 108:1234–1239. | https://pubmed.ncbi.nlm.nih.gov/21220304/ | abstract |
| Gupta A et al. 2021. Embodied intelligence via learning and evolution (DERL). | https://arxiv.org/abs/2102.02202 | abstract |
| Hinton GE, Nowlan SJ 1987. How learning can guide evolution. Complex Systems 1:495–502. | https://www.complex-systems.com/abstracts/v01_i03_a06/ | abstract |
| Huizinga J, Clune J 2018. CMOEA. | https://arxiv.org/abs/1807.03392 | abstract |
| Wang R et al. 2019. POET. | https://arxiv.org/abs/1901.01753 | abstract |
| Khadka S, Tumer K 2018. Evolution-guided policy gradient (ERL). | https://arxiv.org/abs/1805.07917 | abstract |
| Pourchot A, Sigaud O 2018. CEM-RL. | https://arxiv.org/abs/1810.01222 | abstract |
| Jaderberg M et al. 2017. Population based training. | https://arxiv.org/abs/1711.09846 | abstract |
| Stulp F, Sigaud O 2013. Robot skill learning: from RL to evolution strategies. Paladyn 4:49–61. | https://doi.org/10.2478/pjbr-2013-0003 (abstract via Semantic Scholar) | abstract |
| Gaier A, Asteroth A, Mouret J-B 2018. SAIL. | https://arxiv.org/abs/1806.05865 | abstract |
| Huber J et al. 2023. Quality diversity under sparse reward and sparse interaction: grasping. | https://arxiv.org/abs/2308.05483 | abstract |
| Huber J et al. 2024. Speeding up 6-DoF grasp sampling with quality-diversity. | https://arxiv.org/abs/2403.06173 | abstract |
| Zurbrügg R, Cramariuc A, Hutter M 2026. DexEvolve. | https://arxiv.org/abs/2602.15201 | abstract (details in `learned-grasp-models.md`) |
| Yuan H et al. 2025. DemoGrasp. | https://arxiv.org/abs/2509.22149 | abstract |

### Repository sources
- `docs/work-log.md` (24 Oct entries, lines ~2700–2787);
- `docs/research/grasp/audit-plates-ep18-ep39.md`, `audit-boards-ep24-sweeper-rack-ep31.md`,
  `audit-starts-ep21-ep2-ep26.md`, `rl-discovered-grasps.md`, `learned-grasp-models.md`;
- `docs/research/notes/24-physics-aware-grasp-design.md`;
- `tools/grasp_evolve.py`.

---

## Appendix A. Reproduction

`S` is the session scratchpad (`/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad`).
The scripts are in `docs/research/grasp/evolution-scripts/` (copies of the ones run from
`$S/grasp_work/grasp-evolution/scripts/`). All runs are CPU, single process, under 2 min each.

- Robot morphology and opposition (§3):
  `$S/venv/bin/python -I sharpa_opposition.py $S/src/video_to_data/robotic_grounding/flash_chord/src/flash_chord/assets/urdfs/sharpawave/right_sharpawave.urdf <hands.npz> out/sharpa_opposition.json`.
  - `hands.npz` is `runs/20261020-refsweep-ea14fdf/refs/dev_ha00/ep39/hands.npz` from the HF store (our perception;
    used only for the keypoint proportions).
  - Random seed 0.
- Hand span (§3): an inline run over the same FK; the result is in `out/sharpa_span.json`.
- Object dimensions (§1, §4): `mesh_dims.py meshes/library_v3` gives `out/mesh_dims.json`; `feature_dims.py
  meshes/library_v3` gives `out/feature_dims.json` (lid knob, pot handle).
- Literature retrieval: `pm.py` (PubMed E-utilities: esearch, esummary, efetch) and `pmc.py` (PMC full text via
  efetch). The other pages were fetched with curl through the session proxy; downloads are in
  `$S/grasp_work/grasp-evolution/dl/`.
