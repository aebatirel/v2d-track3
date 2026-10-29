# How robots grasp thin / flat objects and tools from a table, and how human demonstrations reach dexterous hands — mapped to our grasp-lock recipe

2026-10-24. CPU only, no rentals, no commits. Workflow `wf_cdd41283-528`, step "robot thin-object and tool grasping" of the
owner's option 2 (one recipe, grasp-lock, with designed grasps). This report is the robot-literature companion of the
root-cause audits in this folder (`audit-plates-ep18-ep39.md`, `audit-boards-ep24-sweeper-rack-ep31.md`,
`audit-starts-ep21-ep2-ep26.md`), `rl-discovered-grasps.md`, `human-hand-biomechanics.md` and
`evolution-of-human-grasping.md`. It does not repeat their measurements; it cites them.

Evidence labels:
- **[L]** literature, full text opened (PDF or HTML) at the URL in §9;
- **[L-abs]** only the abstract or landing page opened;
- **[L-2nd]** a statement about a paper found inside another opened paper (the cited paper itself was not opened);
- **[C]** checked by me in code or config (FlashCHORD source, submission kit);
- **[M]** measured by me in this step (script in `docs/research/grasp/robot-thin-grasp-scripts/`), our meshes only, no
  ground truth;
- **[M-a]** measured by a sibling audit (file named), some of it with ground truth, which they label;
- **[I]** my inference; **[H]** hypothesis, with the experiment that would falsify it (§7).

No ground truth (mocap, `observation.objects.pose`) was read in this step.

---

## 0. Answer

1. **The central difficulty of the thin-object literature does not exist in our simulator.** That difficulty is getting a finger
   under an object lying on a hard surface. All the published solutions exist to solve it: slide-to-edge, flip-and-pinch, tilt-and-pivot,
   scooping nails, wall pivots and emergent extrinsic dexterity.
   - In FlashCHORD the robot hands do not collide with the table, in training or in the evaluator. The collision preset
     `training` sets `robot_support_collision: false` [C].
   - So fingers can be placed under a board or a dust-pan blade anywhere. None of those manoeuvres is needed to *reach*
     the underside.
   - They are also not free in our metric. Any object motion that is not in the human reference costs ADD [M]:
     - a 15° tilt of a board about its short edge is 2.9–3.0 cm ADD, frame score 0.69–0.81;
     - a 45° in-plane yaw is 5.4 cm (0.44);
     - a 10 cm slide to a table edge is ≥ 9 cm (0).
   - Use them only where the human did them. The reference then already contains the motion.

2. **What does transfer is the physics behind those methods: a reaction force must hold the object while the other
   contacts are made.** Babin, St-Onge and Gosselin's insertion condition, Eppner's surface-constrained grasps and
   Seo's fixture arm all express it [L]. In our simulator it becomes two hard rules [I, from [C] parameters]:
   - **Net force into the table before lift-off.** Take one finger under a 0.3 kg plate, commanded 0.4 rad past contact
     (kp 1.7 N·m/rad, lever 2–6 cm). It pushes up with 11–34 N against a 2.94 N weight. Any bottom contact that is not
     opposed throws the plate.
     - This matches the measured ep18 dust-pan flick: 63–80 mm / 17–22° before the reference had moved 1 cm, in 4 of 4
       variants [M-a audit-plates].
     - The successful RL policy closes its thumb (top) and index (bottom) in the same frame, and the pan moves ≤ 2.9 mm
       [M-a rl-discovered-grasps].
     - To keep the net vertical force below m g, the top and bottom squeeze targets must match to within about 0.07 rad
       (4°) at a 4 cm lever.
   - **No dragging by friction on top only.** Every colliding shape gets the same μ = 1.0 ([C] `scene/builder.py`).
     - A hand that presses only on the top face can never drag a board, because μN < μ(N + m g).
     - A clamp through the table (thumb on top, fingers under) cancels its own normal forces, so the table friction stays
       μ m g = 2.94 N. It drags once the clamp force exceeds 1.47 N per side.
     - Caveat: the cones are pyramidal (effective μ 0.71–1.0), so with misaligned tangent axes a top press above
       ≈ 7 N might still drag.

3. **Tools with handles: three points the literature agrees on, all with measured support.**
   - **Grasp the functional region, not the geometric centre.** BiDexHD has the exact TACO task (dust, brush, pan).
     Replacing the human-derived grasp centre with the geometric centre lowered the tracking rate from 78.2% to 66.4%
     (train) and from 59.9% to 52.1% (unseen combinations). The authors single out objects "thin, flat, or equipped with
     handles" [L].
   - **A postural prior plus RL beats hard-coded pinches on handles.** DexFunc, LEAP hand, real robot: saucepan 0.9 vs
     0.3, hammer 0.8–0.9 vs 0.0–0.3. The hard-coded pinch failed "since the fingers push the object behind", the same
     failure as our knocks [L].
   - **Contact-target terms make RL produce stable multi-contact grips.** Lid twisting with two Allegro hands: the
     keypoint contact reward was "crucial", and replaying a successful trajectory let the bottle roll off the fingers
     [L].

4. **Copying human hand kinematics rarely works; keeping the human's object path, wrist and contact timing and finding
   the fingers by physics does.**
   - Kinematic replay success [L]:
     - ManipTrans: 4.6% single-hand, 0.0% bimanual;
     - ObjDex (fingertip mapping): 4–39% per object;
     - SPIDER: kinematic ADD-AUC 11.0 (OakInk) and 24.1 (GigaHands), against 48.8–57.7 after physics-based
       retargeting.
   - A PPO policy trained on the kinematic reference reached 0.07 ± 0.11 task progress, against 0.99 ± 0.01 on the
     physics-corrected reference (SPIDER, 7 seeds) [L].
   - ObjDex: adding a human finger-tracking reward *lowered* performance [L].
   - This supports the owner's choice of designed grasps over copied ones, with two qualifications:
     - the *when* and *where* of contact should still come from the human (BiDexHD's grasp centre, ManipTrans's contact
       termination);
     - a designed grasp must be validated physically over the whole hold, not only at closure. DexGraspNet tests six
       gravity directions; SPIDER scores rollouts; King et al. optimise pre-grasp and transport jointly.

5. **Our fine-tune degradation (ep18: 0.446 at 10M → 0.060 at 70M) has a published analogue.** DexMachina re-implemented
   ManipTrans's physics curriculum and found it "initially achieves high task reward, but performance drops as the
   curriculum progresses and cannot recover". Their decaying virtual object controller did not do this. They also found
   that restrictive wrist bounds give the best results [L].
   - ObjDex limits the residual wrist action to ±4 cm / ±0.5 rad. FlashCHORD's Sharpa recipe allows ±20 cm / ±1 rad
     (STATUS).
   - [H] Restricting the wrist residual during holds, plus contact-level training guidance, are two cheap levers (H5–H7).

6. **For the design step, sampling and evolutionary optimisers are the field's standard tool; RL is the standard tool
   for the closed loop.**
   - Design step:
     - DFC: Metropolis-adjusted Langevin;
     - DexGraspNet: the same family, with Metropolis–Hastings acceptance;
     - SPIDER: annealed sampling with contact guidance. It matched or beat RL baselines on ADD-AUC (43.6 vs 41.0 for
       DexMachina, 22.3 vs 19.4 for ManipTrans) and was 10× or more faster [L].
   - Closed loop: RL.
   - FlashCHORD's objectives and VOC curriculum are written for "both the RL reward … and the MPPI cost" ([C]
     `objectives/__init__.py`, `lifecycle/curriculum.py`). This checkout ships only the PPO and FlashSAC trainers; I found
     no MPPI driver [C]. See the evolutionary-algorithms report for the full EA-vs-RL question.

How this maps to the audited failures (the root causes are the audits'; the literature column is this report's):

| episode | first thing that goes wrong [M-a] | literature principle | design consequence |
|---|---|---|---|
| ep18 pan | no opposition (thumb 20 mm off); closing from below flicks it | reaction force first (Babin; Eppner); simultaneous opposition (RL policy) | top-first or simultaneous closure, net force into the table (H1); hook through the ring for the lift (H2) |
| ep18 sweeper | hold starts at f61, but the brush moves from f38 (0 MANO contacts until f60) | stage-1 alignment before tracking (BiDexHD: removing it drops r1 98.7% → 25.0%); contact timing as a constraint (ManipTrans) | start holds at the object's motion onset (H8) |
| ep39 pan | carrier merge deletes the left-hand pick-up | same as above: the hand must be on the object before the object moves | a reference-building fix, not a grasp fix |
| ep24 boards | locked drag grasp never opposes (thumb 2.2–4.8 cm off) | slide needs a normal contact or a clamp; one grasp cannot serve drag and lift (Bimbo's two strategies; King's joint optimisation) | through-table edge clamp, locked from the slide (H3); grasp change inside a hold |
| ep21 pitcher | base missing in our mesh; falls before the grasp | none (a support problem); a "dynamic catch" is possible (ExDex catches mid-air; one ep21 rollout caught the pitcher: 0.665) | support-consistent mesh first, then a handle wrap |
| ep2 lid | flicked out at lift onset, whatever the start | balanced opposing contacts; no squeeze before lift; contact reward (lid twisting) | lid knob grasp with opposition (§4.5, H1/H6) |
| ep26 / ep31 | ejected from hull overlaps at the start | none in the grasp literature | geometry consistency, not grasp design |

---

## 1. Our setting differs from the literature's in ways that decide what transfers

| property | typical paper | ours | source |
|---|---|---|---|
| hand–table collision | physical; fingers cannot go below the support | **off** in training and in the evaluator (`training.yaml`: `robot_support_collision: false`; `physical.yaml` would turn it on) | [C] `flash_chord/configs/collision/*.yaml`, `configs/experiment/sharpa_flash_sac.yaml` → `override /collision: training` |
| friction | measured per material (ABS on steel 0.4 in Babin) | **μ = 1.0 on every colliding shape, the table included**; pyramidal cone (worst case 0.71) | [C] `scene/builder.py` L266–269 and L507; notes 24 §1 |
| torsional friction | soft-finger models common | **none** (condim 3) | notes 24 §1 |
| fingers | under-actuated / compliant (Yale T42, RBO, Pisa/IIT SoftHand, Babin's passive thumb) or stiff position control | **fully actuated, 22 joints, PD kp 1.7 N·m/rad, effort 10 N·m**: compliant by gain, not by mechanism | notes 24 §1 |
| wrist | arm-mounted, position or OSC control | virtual 6-DoF drive, kp 25 or **kp 400 (`sharpa_hands_mid`)** | STATUS 23 Oct |
| object mass | real (0.1–2 kg) | kit placeholder **0.3 kg** (weight 2.94 N) | notes 24; the ep24 audit's moments imply the same |
| hand size | robot hands are typically ~1–1.5× human | Sharpa index digit 10.45 cm vs our perceived MANO hand 6.25 / 6.45 cm (**1.62–1.67×**); thumb 13.3 vs 8.6 cm (1.55×); palm width 6.2 vs 5.0–5.2 cm (1.2×) | [M-a] `evolution-scripts/out/sharpa_opposition.json` |
| goal | lift or relocate | **reproduce a given object path** (6-DoF per frame) | task |
| score | binary success at thresholds | **ADD-AUC**, thresholds 1–9 cm, per object, mean over frames. The kit also computes SPIDER-style (10 cm / 0.5 rad) and ManipTrans-style (3 cm / 30°) success rates, matched to FlashCHORD's `evaluation/metrics.py` | [C] `v2dlb/object_pose.py` L25–29, L96–102 |
| start | object settled, robot pre-positioned | **frame 0, no object assist (VOC 0), one world**; stochastic across the 5 evaluations (e.g. ep39 standard 0.802 ± 0.280) | STATUS |

Two consequences [I]:
- The organisers' simulator descends from the human-to-robot transfer line (SPIDER and ManipTrans metrics in the
  evaluator code, a DexMachina-style VOC in the runtime). Results from that line are the most transferable evidence.
- The two physical facts that differ most from the thin-object literature are the pass-through table and the equal
  friction. Both reshape the flat-object problem (§1.2).

### 1.1 What pre-grasp object motion costs in our metric [M]

`robot-thin-grasp-scripts/pregrasp_add_cost.py` applies the kit's per-frame rule f(ADD) = trapezoid over
[ADD < t, t = 1…9 cm] to 6,000 surface samples of our library_v3 meshes. f is a step function, roughly (9 − ADD[cm])/8
in 1 cm steps: f = 1.0 below 1 cm, 0.94 for 1–2 cm, 0.81 for 2–3 cm, 0.69 for 3–4 cm, 0.56 for 4–5 cm and 0 from 9 cm.

"Long edge" means a hinge along the object's longest axis; "short edge", a hinge along its middle axis (the longer
lever). Cells give ADD in cm with the frame score in brackets.

| object (PCA extent, cm) | tilt 10° long edge | tilt 15° long edge | tilt 30° long edge | tilt 15° short edge | yaw 20° about centroid | yaw 45° about centroid |
|---|---|---|---|---|---|---|
| wooden_piece_1 (22.8 × 13.3 × 3.0) | 1.21 (0.94) | 1.82 (0.94) | 3.60 (0.69) | 2.90 (0.81) | 2.43 (0.81) | 5.35 (0.44) |
| wooden_piece_2 (22.8 × 13.8 × 2.6) | 1.23 (0.94) | 1.84 (0.94) | 3.65 (0.69) | 3.02 (0.69) | 2.49 (0.81) | 5.48 (0.44) |
| mini_dust_pan (17.3 × 15.8 × 3.7) | 1.36 (0.94) | 2.04 (0.81) | 4.05 (0.56) | 1.93 (0.94) | 1.86 (0.94) | 4.10 (0.56) |
| mini_sweeper (14.5 × 11.0 × 3.3) | 1.03 (0.94) | 1.54 (0.94) | 3.05 (0.69) | 1.77 (0.94) | 1.58 (0.94) | 3.48 (0.69) |
| white_pot_lid (18.5 × 17.0 × 5.2) | 1.55 (0.94) | 2.32 (0.81) | 4.60 (0.56) | 2.47 (0.81) | 2.10 (0.81) | 4.63 (0.56) |

Reading [I]:
- A brief tilt of ≤ 15° (Odhner's flip start, Seo's tilt, a pivot) costs 0.06–0.31 of one object's frame score while
  it lasts. Over 20 frames of a 300-frame episode that is ≤ 0.02 of that object's AUC.
- A slide to a table edge (≥ 10 cm) or a large yaw (Chang's pre-grasp rotation) costs the whole frame score while the
  object is off its path.
- Losing the object costs up to 1.0 per frame for the rest of the episode.
- So small transient tilts are affordable if they buy a secure grasp, and translations or rotations that are not in the
  human reference are not.

### 1.2 Force balance at closure in this simulator [I, parameters from [C] and notes 24]

**Flick.**
- A finger joint commanded Δq = 0.4 rad past contact (the grasp-lock squeeze) produces τ = 1.7 × 0.4 = 0.68 N·m; the
  10 N·m effort limit does not bind.
- At a contact 2–6 cm from that joint (Sharpa index DP 2.6 cm, MP 3.15 cm, PP 4.7 cm) this is F = τ/r ≈ 11–34 N.
- The weight is 2.94 N. A contact from below that is not opposed therefore pushes with 4–12× the weight, and the support
  can only push.
- To keep |F_up − F_down| < m g at r = 4 cm, the top and bottom torques must agree within 0.12 N·m, i.e. the squeeze
  targets within ≈ 0.07 rad (4°).
- Rule: **before lift-off, the net hand force must point into the table.** Let the top contacts carry the preload;
  bring the bottom contacts only to touch (small Δq) until the lift frame, then raise their share with the load
  (Johansson–Westling coupling, notes 24 §5).

**Drag (board slide).**
- With μ_hand = μ_table = 1.0, a hand pressing only on the top face can supply at most μN of tangential force. The table
  resists with up to μ(N + m g), so the board cannot be dragged by friction alone.
- What works:
  - a **normal contact on the trailing edge** (the human hooks or pushes the edge);
  - a **clamp through the table**: equal top and bottom normal forces N cancel, so the table normal stays m g and its
    friction μ m g = 2.94 N; the hand supplies up to 2μN. This drags once N > 1.47 N per side.
- Caveat: pyramidal cones give an effective μ of 0.71–1.0 depending on direction and on each contact frame's tangent axes.
  In the worst alignment a top press above ≈ 7 N (N > 0.71(N + m g)/1.0) could drag. It is fragile either way.

**Moments without torsional friction.** A two-point pinch whose contacts lie along the plate normal cannot resist a
moment about the line joining them (no torsion at condim 3). This matches the ep24 audit's rejection of the lateral
pinch for the carry. Either three non-collinear contacts, or a cage or hook through a hole, is needed.

---

## 2. Literature by family: what was shown, with which hand, how well, why it works, and what it means for us

### 2.1 Environment constraints and extrinsic dexterity

| work | hand / platform | sim / real | measured result | principle | maps to us |
|---|---|---|---|---|---|
| Chavan-Dafle, Rodriguez et al. 2014, "Extrinsic dexterity" [L-abs] | simple industrial gripper (ABB) | real | 12 open-loop, hand-scripted regrasp actions; > 1,200 trials on 3 objects (per-action rates not opened: the MIT PDF returned HTTP 429) | gravity, external contacts and fast arm motions as resources for regrasps | The grasp *change* inside a hold (needed for ep24 drag → lift, ep39 hand switch) can use the table as the third hand. |
| Eppner, Deimel, Álvarez-Ruiz, Maertens, Brock 2015, IJRR [L] | **human study**: 5 adults, 10 objects (button, salt shaker, tape, matchbox, marker, sunglasses, comb, screw, toy, chestnut), 100 trials each, control vs blurring goggles; robots: Barrett BH-262, RBO Hands 1 and 2 | real | Humans with impaired vision made more support contacts, longer contact duration and travel, and larger forces, and took longer. One participant slid the button to the edge in 10 of 10 trials; another flipped it by anchoring one finger and pulling with another. Barrett: small cylinders were grasped only with force-compliant closing that keeps the fingertips on the table; slide-to-edge was reliable for all blocks, force-compliant closing only for flat ones. RBO Hand 1: surface-constrained grasp needs cylinders ≥ 16–22 mm, edge grasp needs an edge within ~100 mm, objects > 75 mm too big (108 / 90 trials). | "grasping becomes a process of successive exploitation of environmental constraints"; contact with the support offsets state uncertainty | Our perception has 1.5–3.3 cm hand–object gaps (STATUS 23 Oct). The human answer to uncertainty is *more* use of the support. Ours: let fingers slide along (here: through) the table surface into place rather than close in the air. |
| Bimbo, Turco, Ghazaei Ardakani et al. 2019, Front. Robot. AI [L] | Pisa/IIT SoftHand on KUKA iiwa7 | real | 320 trials, 16 objects. Continuous Slide-and-Grasp suits small flat objects (credit card), Pivot-and-Re-Grasp larger ones. Validation 10 trials each: toolcase 90% vs 80%, rubber plate 60% vs 80%. | soft-hand compliance plus the table edge | One strategy does not fit all flat objects. Human strategies cited: flip or slide-to-edge (Puhlmann et al. 2016 [L-2nd]). |
| Zhou & Held 2022, CoRL [L] | Franka Panda, parallel gripper; robosuite / MuJoCo; SAC | sim → real zero-shot | An emergent push against a wall rotates the object, then it is grasped. **Without walls: 0%.** Real: 78% with ADR vs 33% without. Low-gain (compliant) OSC beat high-gain OSC; joint torque and joint position control were worse. | the wall supplies the reaction force; compliance keeps contact through the rotation | Supports "reaction force first". Contrast: our spoon needed a *stiff* kp 400 wrist for tracking (STATUS). [H] Compliance may help the approach and closure and stiffness the carry (H9). |
| Tang, Chen, Yang et al. 2025, ExDex [L] | Inspire hand on UR5e; Isaac Gym RL; teacher–student | sim → real | Learns to relocate flat-based objects (16–25 cm, 4–7.5 cm thick) to a table edge or a wall, then grasp. Real: 8/10 to 10/10 per object ("exceeding 80% for most"). Arm-only and heuristic baselines fail the wall task; removing the motion reward gives "near zero" success. The learned policy lifts and "dynamically catch[es] the object mid-air". | a dexterous hand turns the pivot into a catch | Dexterous-hand evidence that a catch inside a manipulation is learnable. Our one ep21 rollout that caught the falling pitcher scored 0.665 [M-a]. |
| Sun, Luo, Pfister et al. 2020 [L-abs] | robot arm with RL, sim → real | real | push the object against a support and pivot to lift one side, then grasp; no numbers in the abstract | pivot against a support | Same principle as tilt-and-pivot. |
| Ding et al. 2024, PreAfford [L-abs] | two-finger gripper, ShapeNet-v2 | sim and real | pre-grasping raises grasp success by 69% (52.9% + 16.4% closed loop) | point-level affordance for pre-grasp moves | Pre-grasp object motion is costly in our metric (§1.1), so this is of limited use. |

### 2.2 Pre-grasp manipulation planning

| work | platform | sim / real | result | principle | maps to us |
|---|---|---|---|---|---|
| King, Klingensmith, Dellin, Dogar, Velagapudi, Pollard, Srinivasa 2013, RSS [L] | two bimanual platforms; book slid to the table edge, then shelved | planning (sim) with demos | 9 scenes × 14 seeds = 126 cases per planner; **joint optimisation of pre-grasp and transport: +29% success** (feasible collision-free plan), 12% lower cost than sequential | the grasp choice and the transport are one problem | [I] Our grasp-lock picks a grasp at one frame (closure) and then locks it. **Choose each hold's grasp by its performance over the whole hold** (wrench along the carry, reachability, release), the analogue of King's joint cost (H4). |
| Chang, Zeglin, Pollard 2008; Chang, Srinivasa, Pollard 2010 [L-2nd, L-abs] | human motion capture (handled objects, heavy pans) and an anthropomorphic arm | real | Eppner [L]: Chang et al. "rotate pan handles into a specific orientation prior to grasping by exploiting the pan's friction and remote center of mass". The workshop abstract (KIT, ICRA 2010) says pre-grasp interaction "can extend the effective workspace of a well-tuned grasping action". The 2010 ICRA PDF could not be opened (host gone). | rotate the object, not the hand | Humans rotate handled objects before lifting them. If our human did, the reference has it. We must not add rotations (a 45° yaw costs 0.44–0.69 per frame, §1.1). |
| Hang, Morgan, Dollar 2019, RA-L [L] | Yale T42 under-actuated hand on a WAM; Gazebo and real | sim planning; real demos qualitative | 1,000 simulated planning problems. With the passive-reconfiguration allowance ΔZ* = 2 cm: > 90% planned within 20 s, 99% at 60 s. ΔZ* = 0.5 cm: 90% at 53 s. **ΔZ* = 0: 2%.** Real executions shown, not counted. | finger compliance lets the hand press "into" the surface by up to 2 cm, so contact survives position error | [I] Our PD fingers (kp 1.7) are compliant by gain. Commanding them past the surface is our ΔZ. Hang's result says this allowance is essential; §1.2 says it must be force-balanced (H1). |

### 2.3 Picking flat objects off hard surfaces: mechanisms and strategies

| work | platform | result | principle | maps to us |
|---|---|---|---|---|
| Babin, St-Onge, Gosselin 2019, RCIM [L] (the same group's IJRR 2018 "picking, grasping, or scooping" paper was not opened: the publisher returned 403) | Kinova Jaco, one finger replaced by a passive-joint thumb | "100% success rate of the method with the objects chosen" (continuous sequence; heaviest 0.167 kg) | A quasi-static model of thumb insertion under a plate (their Eq. 2 and Eq. 5): insertion is only possible if the line of the thumb force stays inside the friction cone (slope a < μ_f), and **the fingers must press on the top face** with a minimum force that grows with m g. "A spatula-like device … cannot be inserted under objects solely by moving towards them: it is necessary to have a reaction force". Low PD gains; slow approach near contact. | The reaction-force rule in its cleanest form. Here it inverts: insertion is free (hands pass through the table), but the *top* contact must still come first or together. |
| Odhner, Ma, Dollar 2012 (ICRA) / 2013 (T-ASE) [L] | planar two-finger under-actuated hand, open-loop | flip-and-pinch of coins and thin parts; **≥ 80% success under ±20° orientation and ±10 mm hand-height error** | a fingertip presses near one edge; the table constraint makes the flip a repeatable quasi-static motion into a pinch | A flip adds a tilt to the object path (§1.1). Not needed with a pass-through table. Lesson: let the table shape the motion. |
| Tong, He, Kim, Ng, Xu, Seo 2020 (ICRA), extended by Seo 2025 (Sensors) [L] | dual UR arms: Robotiq gripper plus a fixture arm as the tilting axis; vision and F/T | real: 215/250 = **86%** (flat fingertip), > 80% (curved tips), 80% at ≈ 4 s per pick; bin picking 203/274 = 74%, 47/60 = 78% with better singulation | **tilt** the plate up with one finger against a fixed axis, **pivot** the gripper about that contact without relative sliding, insert the other finger, pinch | A two-hand version of the reaction-force rule: the other hand is the fixture. For ep18 (two hands on two plates) not needed. |
| Tong, Ng, Kim, He, Seo 2021, "Dig-grasping", RA-L [L-2nd] | asymmetric fingers digging under the object | not opened (no open copy) | — | — |

### 2.4 Dexterous grasp synthesis

| work | hand | how | validation and numbers | maps to us |
|---|---|---|---|---|
| Liu et al. 2021, DFC [L] | arbitrary (MANO, others) | differentiable force-closure energy plus penetration and distance terms, optimised with a **Metropolis-adjusted Langevin algorithm** (stochastic, gradient plus accept/reject) | PyBullet drop test (object drop < 0.3 m after 1,000 steps): 76.98% (σ < 1.5 mm) and 85.0% (σ < 0.5 mm), against 72.53% (Unions of Balls) and 85.0% (Visuo-Haptic). Hard shapes are slow: bottles gave 5 valid grasps of 512 after 10⁴ steps. | A static force-closure check is necessary, not sufficient. Our condim-3 pyramid (μ_d 0.47, notes 24) must be the cone used. |
| Wang et al. 2023, DexGraspNet [L] | ShadowHand (also Allegro, MANO) | DFC accelerated. Initialisation: **fingers open, palm facing the object**, jittered. "Reverse penetration energy" (object points against the hand mesh) so thin meshes work. | 1.32M grasps on 5,355 objects. **Kept only if contact survives 100 steps under each of 6 gravity directions and penetration ≤ 1 mm** (Isaac Gym). 18% valid (3% with the original method); 950 A100-hours. | Our thin meshes (boards 0.8–1.2 cm, pan 1.5 cm local thickness [M-a]) need the reverse-penetration form. **Adopt the 6-direction hold test as a CPU gate** for designed grasps, but on *our* load: the reference's wrench over the hold. |
| Xu et al. 2023, UniDexGrasp [L-abs + text]; Wan et al. 2023, UniDexGrasp++ [L-abs] | ShadowHand, table-top, point cloud | grasp proposals + goal-conditioned RL; curricula; generalist–specialist distillation | > 60% average success on thousands of objects; ++: 85.4% train / 78.2% test. **Grasps that penetrate the table are rejected** (table-penetration penalty in synthesis). | Table-top synthesisers forbid exactly the under-plate placements our simulator allows. Drop the table term for our designs, but keep the force balance (§1.2). |
| Zhu et al. 2021, ICCV "Toward human-like grasp" [L] | dexterous hand, simulated | per functional part a 16-bit "touch code" (which hand parts touch); 18 categories, 129 objects | synthetic only | Our MANO contact labels per link [M-a census] are a touch code. Use them as *which* hand parts touch *which* object part, not as joint angles. |
| Agarwal, Uppal, Shaw, Pathak 2023, "Dexterous Functional Grasping" (DexFunc) [L] | LEAP hand on xArm6 | affordance matching for the pre-grasp; RL in a **9-D eigengrasp space** (PCA of a small set of human hand poses) | sim success: hammer 1.00 vs 0.60 (full 16-D actions), drill 0.23 vs 0.09, screwdriver 0.95 vs 0.46. Real (10 trials): saucepan 0.9, hammer 0.8–0.9, drill 0.5–0.8, stapler 1.0, screwdriver 0.7. **Hard-coded pinch 0.0–0.3: "the fingers push the object behind".** | Two points. (a) A postural subspace makes RL find firm handle grasps reliably across seeds. (b) Pushing the object away on approach is the generic failure of scripted closures; it is our sweeper and brush knock. |
| Huang et al. 2024, FunGrasp [L] | LEAP, Allegro, Inspire | one RGB-D human grasp → retargeting with **penetration + force-closure + contact-position losses** → RL with privileged learning, system identification, domain randomisation, gravity compensation | real one-shot functional grasps: **74%** average success on unseen objects | The closest published analogue of "a designed grasp from a human example, then RL". Their retargeting loss set is a ready template for ours. |
| Zhang et al. 2023, "FunctionalGrasp", RA-L [not opened] | — | — | — | Not opened (publisher, not open access). |

### 2.5 From human hand–object demonstrations to dexterous robot hands

| work | data → robot | sim / real | measured result | key mechanism | maps to us |
|---|---|---|---|---|---|
| Qin et al. 2022, DexMV [L] | human videos (3-D hand + object pose) → Adroit 30-DoF hand in MuJoCo | sim | Relocate: pure RL 0.06 (mustard) and **0.00 (sugar box)**; DAPG with demonstrations 0.93 and 0.00, SOIL 0.33 and 0.67. Fingertip-only retargeting "loses the bending information … leading to penetrating the object"; adding palm-to-middle-phalanx vectors and a smoothness term helped. | demonstrations as RL priors | Flat-faced objects are hard for RL alone ("tall and thin with a flat surface. Once it drops … hard to grasp again"). Fingertip-only matching penetrates. |
| Handa et al. 2020, DexPilot [L]; Qin et al. 2023, AnyTeleop [L] | human hand keypoints → Allegro and others | real teleoperation | DexPilot: pinch "projection" closes thumb–finger gaps below a threshold (η₁ = 1e-4 m) "particularly useful in the presence of visual finger tracking inaccuracies"; release with projection "can be unpredictable". AnyTeleop: vector retargeting with a scale factor α; "this module only considers the robot hand". | object-agnostic keypoint matching | Kinematic retargeting knows nothing about the object, so contacts are opened or closed only by heuristics (§3). |
| Chen, Wang et al. 2024, ObjDex [L] | ARCTIC → two Shadow Hands on UR10e | sim + real | Per-object completion: fingertip mapping 4–39%, vanilla RL 4–44%, **ObjDex 39–100%** (one policy per object). **Adding a human fingertip-matching reward lowers performance.** Residual wrist ±4 cm / ±0.5 rad around a generated human-like wrist. | human wrist, robot fingers | Keep the human *wrist* path and object path; do not reward human finger *joints*. |
| Li et al. 2025, ManipTrans [L] | OakInk-V2 and others → Inspire (12-DoF in sim), Shadow, Allegro, MANO; Isaac Gym | sim + real replay | Success rate single / bimanual: **retarget-only 4.6 / 0.0**, RL-only 34.3 / 12.1, retarget + residual 47.8 / 13.9, **ManipTrans 58.1 / 39.5**. "The Retargeting method often causes collisions in contact-rich scenarios, resulting in instability during residual policy training." Curriculum: gravity 0 and high friction early, restored later; object thresholds 90°/6 cm → 30°/2 cm; **contact termination: when the MoCap shows a firm grasp, contact force must be non-zero**. | pre-trained hand imitator + residual RL + physics relaxation | Our perceived human contact labels (allowed; not ground truth) can drive the same contact termination or penalty (H6). Their success thresholds are in our evaluator. |
| Mandi et al. 2025, DexMachina [L] | ARCTIC (long-horizon, articulated) → Inspire, Allegro, XHand, Schunk, Ability, DexRobot; Genesis | sim | Beats kinematics-only, ObjDex-style task reward, no-curriculum and ManipTrans-curriculum baselines on all hands (Fig. 3, 5 seeds × 20 episodes, ADD-AUC). **The ManipTrans curriculum "initially achieves high task reward, but performance drops as the curriculum progresses and cannot recover."** Restrictive wrist bounds performed best. Larger fully actuated hands do better; small hands "need different strategies". | virtual object controllers (6 + 1 PD joints per object) with gains decayed by learning progress; contact and motion rewards | FlashCHORD's VOC is this mechanism ([C] `runtime/object_control.py`). Our ep18 fine-tune collapse (0.446 → 0.060) resembles the ManipTrans curve. Two levers: decay tied to learning progress, and tighter wrist bounds (H5). |
| Liu et al. 2024, QuasiSim [L-abs]; Liu et al. 2025, DexTrack [L-abs] | human HOI → Shadow / Allegro | sim (DexTrack also real) | + 11% (QuasiSim) and + 10% (DexTrack) success over the best baselines | curriculum over relaxed ("quasi-physical") simulators; data flywheel with homotopy optimisation | Our pass-through table is itself a relaxed physics, but one that the evaluator also uses. |
| Pan et al. 2025, SPIDER [L] | 6 datasets, 9 embodiments, 3 simulators (Isaac Gym, Genesis, **MuJoCo Warp**) | sim + real | ADD-AUC (0–10 cm): ManipTrans 19.4 → SPIDER 22.3 (Inspire, OakInk); DexMachina 41.0 → SPIDER 43.6 (Inspire, ARCTIC); **kinematic 11.0 → SPIDER 48.8 → SPIDER+C 56.9** (OakInk, 5 hands); GigaHands 24.1 → 56.9 → 57.7. Over 10× faster than RL. A PPO policy on a SPIDER reference: **0.99 ± 0.01** task progress vs **0.07 ± 0.11** on the kinematic reference (7 seeds). Failure modes: upstream perception errors, occlusion gaps, **open-loop sensitivity** to the initial state, **contact-mode ambiguity** (fixed by contact guidance). | sampling-based optimisation with an annealed kernel over the control sequence in a parallel simulator; **virtual contact constraints** "sticking" intended hand–object contact pairs, relaxed in a curriculum | The strongest single piece of evidence for our design: make the reference physically feasible first, then train RL on it. Its contact guidance is a per-contact VOC (H7). Its open-loop limit is why we still need the RL fine-tune (5 stochastic evaluations). |
| Zhou et al. 2024, BiDexHD [L] (data: TACO, Liu et al. 2024 [L]) | TACO bimanual tool use, **including (dust, brush, pan) and (dust, brush, bowl)** → two LEAP hands, Isaac Gym, teacher–student | sim | Tracking rate r2 (train / unseen combinations / new objects): IPPO 78.2 / 59.9 / 21.3; **without the alignment stage 17.5 / 18.1 / 8.5** (r1 98.7 → 25.0); **without the functional grasp centre 66.4 / 52.1 / 22.6**; BC 0. The grasp centre is computed from the human wrist and fingertip positions at the reference timestep. | stage 1: approach the grasp centre and align the object to the first reference pose; stage 2: track | The only published RL result on our exact tool pair. Two lessons: (a) **get the hand on the tool before tracking starts**: our ep18 sweeper and ep39 failures are exactly a missing stage 1 [M-a]; (b) the grasp region must come from the human. |
| Lin et al. 2024, "Twisting lids off with two hands" [L] | two Allegro hands; sim → real | real | Their policy beats all baselines on 5 bottles; **replay of a successful trajectory fails** ("the bottle will directly roll on the fingers and then drop"); the keypoint-based finger contact reward is "crucial"; a larger network overfits. | contact-point targets as reward | Lid-type objects need contact targets, not trajectories. |

### 2.6 RL for dexterous manipulation (tool use, reorientation)

| work | platform | result | relevant to us |
|---|---|---|---|
| Petrenko et al. 2023, DexPBT [L] | Kuka + Allegro, one or two arms, Isaac Gym | Decentralised **population-based training**: 8 agents; every iteration the top 30% continue, the middle 40% mutate their hyperparameters and reward coefficients, the bottom 30% are replaced by mutated copies of the top. 5 × 10⁹ transitions (30–40 h). Two-arm reorientation reaches ≈ 40 of 50 consecutive successes. "Significantly outperforms regular end-to-end learning." | An *evolutionary outer loop* around RL, not a replacement for it. It suits our per-episode fine-tune (choose reward weights and VOC schedule per episode), but costs 8× compute. |
| Chen et al. 2023, Visual Dexterity (Science Robotics) [L] | D'Claw-type 3- and 4-finger hand, **downward-facing**, real | Reorientation in the air is much harder than with a hand below the object: with table support, train objects within 0.4 rad 81% of the time and OOD objects 45%; the duck was dropped in 56% of in-air trials. | The 0.889 RL policy carried the pan **palm-up** under the ring [M-a]. Palm-down carries of plates are the harder regime. |

---

## 3. How kinematic retargeting fails, with our instances

| failure mode | evidence in the literature | our instance |
|---|---|---|
| **Object-agnostic matching**: fingertips land inside or short of the object | AnyTeleop: "only considers the robot hand"; DexMV: fingertip-only matching penetrates; DexPilot needs a projection to close pinches [L] | the reference brings the fingers 1.5–3.3 cm from the spoon (STATUS 23 Oct); the ep24 thumb stops 2.2–4.8 cm short of the board face; the ep18 thumb is 20 mm off the pan [M-a] |
| **Scale and morphology gap** | DexMachina: hand size and DoF decide whether human strategies are usable; ObjDex: human finger reward hurts [L] | Sharpa fingers are 1.6× our perceived human fingers [M-a]. Copying fingertip positions forces extra curl and different contacts. |
| **Contact timing lost** | ManipTrans adds contact termination; BiDexHD adds an alignment stage [L] | ep18 brush: the object moves from f38, but MANO contacts are zero until f60 [M-a]. ep39: the carrier merge removed the pick-up [M-a]. |
| **Kinematic replay does not hold the object** | ManipTrans retarget-only 4.6% / 0%; ObjDex fingertip mapping 4–39%; SPIDER kinematic ADD-AUC 11–24 and a policy on it 0.07 [L] | the zero-action grasp-lock replays: ep39 0.1755 (floor 0.1763); ep24 board 1 never lifted [M-a] |
| **Contacts that collide destabilise residual RL** | ManipTrans: retargeting "often causes collisions … instability during residual policy training" [L] | approach knocks of the standing brush (ep18, f24–27 with a 6 cm approach) [M-a] |
| **Contact-mode ambiguity** | SPIDER: without contact guidance the optimiser may converge to another valid grasp [L] | the 0.889 policy took the sweeper's neck, not the ring handle the human used [M-a] (a valid alternative; not a failure for the score) |
| **Open-loop sensitivity** | SPIDER limitation (3) [L] | 5 evaluations vary (ep39 standard sd 0.28), so a designed open-loop reference must be robust or be closed by RL |

---

## 4. Object by object: brush and dust-pan handles, plates lying flat, boards, pitcher handle, lid knob

Dimensions [M-a] `evolution-scripts/out/mesh_dims.json` and `feature_dims.json`; human behaviour [M-a]
`hand-biomech-out/census_ep*.txt` and the audits.

### 4.1 Hand brush (`mini_sweeper`, 14.4 × 11.0 × 3.4 cm, local thickness p50 1.46 cm; ep18 lying, ep31 standing in the rack)
- What happened [M-a]:
  - ep18: the hold started 23 frames after the brush began to move. The fingertips clipped it and it fell flat. The designed
    clamp (thumb on one face, three fingers on the other) was the right type but was never tested.
  - ep31: the start ejection, not the grasp.
  - The RL policy clamps the neck and head with 10–13 links.
- Literature:
  - BiDexHD (dust, brush, pan): the grasp centre comes from the human's wrist and fingertips; without it, policies "struggle
    to find proper poses for using the brush" [L].
  - DexFunc: firm power grasps on handles come from RL in a postural subspace; scripted pinches push the tool away [L].
- Design:
  - Keep the human's clamp type and region.
  - Anchor the hold to the object's motion onset in the reference (H8).
  - Approach slowly over the last 2 cm along the plate normal (H9).
  - Validate the clamp over the whole hold (H4).

### 4.2 Dust pan (`mini_dust_pan`, 17.3 × 15.8 × 3.7 cm, blade lying flat, ring handle raised 20–24 mm; ep18 left hand, ep39 carried with tilts of 90–109°)
- What happened [M-a]:
  - The snapped grasp had no opposition, and closing from below flicked the pan.
  - The 0.889 RL policy used a palm-up key pinch: thumb on the band top, index under it, both touching at the same frame
    (f16).
  - For the 19 cm lift it switched to a hook through the ring.
- Literature: Babin's reaction force; Eppner's surface-constrained closure; Visual Dexterity on palm-down holds [L].
- Design:
  - (a) **Net force into the table until lift** (§1.2, H1).
  - (b) For the lift and the large tilts, a **cage or hook through the ring hole (≈ 3 × 3.5 cm)**. Under condim 3,
    friction-only pinches cannot hold moments about the pinch axis, while a hook carries gravity as a normal force (H2).
  - (c) Palm-up under the ring is the easier regime.
  - (d) Do not add a tilt or flip; the pass-through table gives access to the underside.

### 4.3 Boards (`wooden_piece_1/2`, 22.9 × 13.2–13.8 × 2.7–3.1 cm, local thickness p50 0.8 / 1.2 cm; ep24)
- What happened [M-a]:
  - The human slides one board and lifts both.
  - Neither board is acquired or carried by the locked grasp.
  - The counterfactual "sim follows the reference from the lift and the slide" gives 0.803.
- Literature:
  - slide-to-edge (Eppner, Hang, King, Bimbo, ExDex), flip-and-pinch (Odhner) and tilt-and-pivot (Tong/Seo) all exist to
    get under a board [L];
  - Bimbo shows that the best strategy depends on object size;
  - King shows that the pre-grasp and transport choice should be one optimisation [L].
- Design:
  - (a) Do not require an overhang. Keep the human's slide in the reference and use its end as the grasp-change frame (the
    audit's recommendation).
  - (b) **Drive the slide with a through-table clamp or a trailing-edge contact**, never a top-only press: with μ equal on
    hand and table, a top press cannot drag (§1.2, H3).
  - (c) The carry needs a moment couple from contacts spread 3–5 cm along the edge, or three non-collinear contacts. No
    torsional friction is available.

### 4.4 Pitcher handle (`water_pitcher`, 42.5 × 27.7 × 15.0 cm; ep21: lifted 29.6 cm, tilted 91° to pour)
- What happened [M-a]:
  - Our mesh lacks half its base, so the pitcher falls before any grasp. This is a support problem.
  - With a standing pitcher the copied grasp still tips it.
  - The human uses a thumb-dominant wrap (thumb links in 54–81% of held frames).
- Literature:
  - pouring with a handle grasp: DexMV mug, SPIDER cup [L];
  - firm handle grasps: DexFunc saucepan, 0.9 real [L];
  - humans pre-rotate handled objects (Chang et al. [L-2nd]); our reference fixes the path, so no added rotation.
- Design:
  - after the base fix, a **wrap around the handle with the loop caged by the fingers**: index–ring through the loop, thumb
    over the top. A 91° pour then loads the cage, not friction.
  - The VOC is training-only; the evaluator has none.
  - [I] The 0.3 kg placeholder mass makes the pour moment small (m g × lever). The risk is the closure tipping the pitcher
    (H1 applies to tall objects too: the net closure force must not push the pitcher over its support edge). Today its
    COM lies 2.8–4.1 cm *outside* the support of our mesh [M-a], so the base fix comes first; its new margin must then be
    certified (support_fill criterion: ≥ 3 mm and ≥ 3°).

### 4.5 Pot lid knob (`white_pot_lid`, 18.5 × 17.0 × 5.2 cm; knob top 15 mm spans 3.95 × 7.56 cm; ep2)
- What happened [M-a]:
  - In all 5 zero-action variants the lid is flicked out of the hand at lift onset (f59–63).
  - It starts 9.6 mm inside the pot's hulls.
  - The human uses a palm-on-top power grasp on the knob (palm in 76–80% of held frames).
- Literature:
  - lid twisting: contact targets are crucial and replay fails [L];
  - ManipTrans: lid-like tasks (pen capping, bottle unscrewing) need contact-force guidance [L].
- Design:
  - opposing contacts across the 3.95 cm knob width (thumb against index + middle), with the palm on the top;
  - **zero net squeeze before the lift**, the grip rising with the load (H1);
  - a hull-consistent seat (audit-starts).
  - The flick at lift onset suggests the lift starts before the opposing contacts are loaded. [H] Delay the lift by a few
    frames after the closure, within ADD tolerance (H1 variant).

---

## 5. Design implications for grasp-lock (designed grasp written into the reference, RL fine-tune, frame-0 evaluator)

1. **Do not add pre-grasp object motion.** Use only motions that are in the human reference (slides, tilts). The table is
   pass-through, so slide-to-edge, flips, pivots and scoops are unnecessary for access (§1.1).
2. **Force balance at closure.** Before lift-off the net designed hand force on the object must point into the support.
   Top contacts carry the preload; bottom contacts reach touch only, and their share rises with the load at the lift
   frame (Johansson–Westling). Squeeze targets come from statics (notes 24 rule 4) *including gravity and the support
   reaction*, not a uniform 0.4 rad.
3. **Drags need a normal contact or a clamp.** Top-only friction cannot drag a board when μ_hand = μ_table.
4. **Moments need spread contacts or cages.** No torsional friction: use three or more non-collinear contacts, contacts
   spread along the edge, or hooks and cages through holes (dust-pan ring, pitcher handle loop).
5. **The hand must be on the object before the object moves** (BiDexHD stage 1; ManipTrans contact timing). Anchor holds
   to the reference object's motion onset, not to perceived MANO contact.
6. **Take *where* and *when* from the human; *how* from physics.** Use the human contact region (touch code), the timing and
   the wrist path; synthesise the finger posture for the Sharpa hand with DFC/FunGrasp-style losses (penetration, force
   closure on our pyramidal cone, contact position) and a postural prior (DexFunc eigengrasps). Do not reward human finger
   joints (ObjDex).
7. **Validate each designed grasp over the whole hold in the simulator before RL** (DexGraspNet's 6-direction test, but
   with the reference's own wrench and a time-scaled, noisy replay as notes 24 rule 7). Choose among sampled variants by
   that replay (King's joint cost; SPIDER's sampling). This is the step where an evolutionary or sampling optimiser has
   a published edge over RL.
8. **In the fine-tune, guide contacts and restrict the wrist.** Training-only contact guidance (perceived-contact
   termination or reward; per-contact virtual constraints decayed with learning progress) and tighter wrist residual
   bounds during holds. Both target the degradation-with-training pattern that DexMachina reports for physics-only
   curricula.
9. **Approach slowly and from the open side.** The final 1–2 cm along the contact normal, slowly (Babin, Zhou & Held), so
   standing objects (brush in the rack, upright brush) are not knocked.

---

## 6. Where the literature does not help, and caveats

- No paper studies grasping with a table that the hand passes through but the object does not. The force-balance rules
  in §1.2 are my derivation from the simulator's parameters [I]. They ignore soft-contact compliance, the solver's
  impedance and the 5-substep integration. They are order-of-magnitude statements to be tested (H1, H3).
- Most thin-object results are on real under-actuated or soft hands (T42, RBO, Pisa/IIT, passive thumbs). Their
  robustness comes from mechanical compliance. Ours can only come from PD gains (kp 1.7 per finger joint) and reference
  design.
- Several numbers are planning success (Hang, King), not execution success. Hang's real executions are not counted.
- Per-action success rates for Chavan-Dafle 2014, the IJRR 2018 scooping paper, dig-grasping, Chang 2010 and
  FunctionalGrasp were not opened (blocked hosts or paywalls). Statements about them are labelled.
- Success definitions differ across papers (ManipTrans 3 cm / 30°; ObjDex 5 cm; BiDexHD 0.1 threshold units; DexMachina
  and SPIDER ADD-AUC to 10 cm vs our 9 cm). Cross-paper numbers are indicative only.
- The literature's transfer results are mostly on mocap-grade references (ARCTIC, OakInk, TACO). Our references come from
  egocentric perception with cm-level errors, closer to SPIDER's in-the-wild setting, where perception errors are its
  first-listed failure mode.

---

## 7. Hypotheses and the experiments that would falsify them

The CPU tests use FlashCHORD on Warp CPU at the evaluator pin, zero action, as in the audits (≈ minutes per replay
[M-a audit-starts]). GPU costs are estimates from the work log: one grasp-lock episode end to end (reference, 70M
fine-tune, evaluations) ≈ 1.1 h at ≈ $1.5/h ≈ **$1.7**; standard 250M ≈ $2.7.

| id | hypothesis [H] | falsifying experiment | gate (falsified if …) | cost |
|---|---|---|---|---|
| H1 | **Top-first (or exactly simultaneous) closure with the net force into the table** removes the plate flick. Variant for the lid: start the lift only after the opposing contacts are loaded. | ep18 pan and ep2 lid zero-action replays: current closure vs (a) bottom contacts at Δq ≤ 0.05 rad past touch until the lift frame, top contacts at the statics preload; (b) the same plus a 3-frame lift delay | pan displacement before the reference moves 1 cm ≥ 20 mm or ≥ 5° in ≥ 3 of 4 variants; lid still leaves the hand at lift onset in ≥ 4 of 5 variants | CPU |
| H2 | For ring handles under condim 3, a **hook or cage through the hole** holds through large tilts better than a friction pinch | ep39 carry window (after the carrier-merge fix) and the ep18 pan lift: key pinch vs index-through-ring + thumb on the band | in-hand drift of the hook ≥ that of the pinch, or hook drift > 1 cm / 5° over the carry | CPU |
| H3 | With μ equal on hand and table, **top-only presses cannot drive the human's board slide; a through-table clamp (N ≈ 2–3 N per side) or a trailing-edge contact can** | ep24 board-2 slide window, zero action: top press (N up to 10 N) vs clamp vs edge push | the top press tracks the reference slide within 1 cm, or the clamp fails to | CPU |
| H4 | **Selecting each hold's grasp by a whole-hold replay** (best of N sampled variants: contact offsets ± 1 cm, closure order, squeeze split) beats the single heuristic design | ep18, ep24, ep2: N = 32 variants per hold, zero-action sim_vs_ref over the hold; compare the best with the current design | best-of-32 improves zero-action sim_vs_ref by < 0.05 on ≥ 2 of 3 episodes | CPU hours, or ≈ $1–2 GPU batched (estimate) |
| H5 | **A restricted wrist residual during holds** (e.g. ±4 cm / ±0.3 rad, ObjDex/DexMachina) stops the fine-tune from degrading with training | ep18 fine-tune, same reference and seed, current bounds vs restricted; checkpoints 10/30/50/70M, 3 evaluations each. First check in code that the bound is part of the checkpoint config the evaluator honours, as the kp 400 embodiment is | 70M ≤ 10M again, or no gain ≥ 0.05 at the best checkpoint | ≈ $1.7 per run |
| H6 | **Perceived-contact guidance** (ManipTrans contact termination / BiDexHD grasp-centre approach / lid-twisting contact reward; from our perceived MANO labels, training only) improves the fine-tune on contact-critical objects | ep2 (lid) and ep18 A/B at equal steps, 3 evaluations per checkpoint | registered AUC gain < 0.05 on both | ≈ $1.7 per episode-run |
| H7 | **Per-contact virtual constraints decayed with learning progress** (SPIDER+C contact guidance; DexMachina progress-based decay), training only, avoid early learned contact avoidance | FlashCHORD training patch; ep18 and ep24 fine-tune A/B vs the current whole-object VOC | no improvement ≥ 0.05, or the same degradation with training | ≈ $1.7 per episode-run plus development |
| H8 | **Anchoring the hold at the reference object's motion onset** (not at perceived contact) fixes the sweeper timing failure | ep18 sweeper zero action with onset-anchored holds (task #30 in progress) | sweeper displaced > 5 mm / 2° before closure, or not lifted ≥ 5 cm | CPU |
| H9 | **A slow, normal-direction final approach** (last 2 cm over ≥ 5 frames) reduces knocks of standing objects | ep18 brush and ep31 rack-standing sweeper: approach-speed sweep at zero action | knock displacement unchanged (± 20%) across speeds | CPU |
| H10 | **Physics-synthesised finger postures on the human's contact regions** (DFC/FunGrasp losses on our pyramidal cone) beat copied postures on the lid and the pitcher | ep2 lid; ep21 pitcher after the base fix: zero-action sim_vs_ref, copied vs synthesised | gain < 0.05 on both | CPU (synthesis) + CPU replays |

---

## 8. Reproduction

- Literature: PDFs fetched through the session proxy with `curl` and converted with `pdftotext`, into
  `scratchpad/grasp_work/robot-thin-grasp/pdf/` (not in git).
- Pre-grasp ADD cost table [M]:
  `scratchpad/venv/bin/python -I docs/research/grasp/robot-thin-grasp-scripts/pregrasp_add_cost.py meshes/library_v3 docs/research/grasp/robot-thin-grasp-scripts/out/pregrasp_add_cost.json`
  (our meshes only; 6,000 surface samples, seed 0).
- Code facts [C]:
  - `flash_chord/configs/collision/training.yaml` and `configs/experiment/sharpa_flash_sac.yaml` (`override /collision:
    training`);
  - `flash_chord/scene/builder.py` L266–269, L507 (one μ for all shapes and the ground);
  - `flash_chord/runtime/object_control.py` (VOC);
  - `flash_chord/objectives/__init__.py` and `lifecycle/curriculum.py` (RL and MPPI consumers);
  - kit `v2dlb/object_pose.py` L25–29, L96–102 (ADD-AUC; SPIDER and ManipTrans success rules).

---

## 9. Sources (what was opened)

Full text opened [L]:
- Eppner, Deimel, Álvarez-Ruiz, Maertens, Brock (2015). Exploitation of environmental constraints in human and robotic grasping. IJRR 34(7). https://depositonce.tu-berlin.de//bitstream/11303/6844/1/0278364914559753.pdf
- Bimbo, Turco, Ghazaei Ardakani, Pozzi, Salvietti, Bo, Prattichizzo, Malvezzi (2019). Exploiting robot hand compliance and environmental constraints for edge grasps. Front. Robot. AI 6:135. https://www.frontiersin.org/articles/10.3389/frobt.2019.00135/pdf
- Hang, Morgan, Dollar (2019). Pre-grasp sliding manipulation of thin objects using soft, compliant, or underactuated hands. RA-L 4(2). https://www.eng.yale.edu/grablab/pubs/Hang_RAL2019.pdf
- King, Klingensmith, Dellin, Dogar, Velagapudi, Pollard, Srinivasa (2013). Pregrasp manipulation as trajectory optimization. RSS IX. https://www.roboticsproceedings.org/rss09/p15.pdf
- Babin, St-Onge, Gosselin (2019). Stable and repeatable grasping of flat objects on hard surfaces using passive and epicyclic mechanisms. RCIM 55 (accepted manuscript). https://espace2.etsmtl.ca/id/eprint/18899/1/St-Onge%20D%202018%2018899.pdf
- Odhner, Ma, Dollar (2012). Precision grasping and manipulation of small objects from flat surfaces using underactuated fingers. ICRA. https://www.eng.yale.edu/grablab/pubs/Odhner_ICRA2012.pdf
- Odhner, Ma, Dollar (2013). Open-loop precision grasping with underactuated hands inspired by a human manipulation strategy. T-ASE. https://www.eng.yale.edu/grablab/pubs/Odhner_TASE2013.pdf
- Seo (2025). A dexterous reorientation strategy for precision picking of large thin objects (extended version of Tong et al., ICRA 2020, tilt-and-pivot). Sensors 25(20):6496. https://pmc.ncbi.nlm.nih.gov/articles/PMC12567684/
- Zhou & Held (2022). Learning to grasp the ungraspable with emergent extrinsic dexterity. CoRL. https://arxiv.org/abs/2211.01500
- Tang et al. (2025). ExDex: Dexterous non-prehensile manipulation for ungraspable object via extrinsic dexterity. https://arxiv.org/abs/2503.23120
- Liu et al. (2021). Synthesizing diverse and physically stable grasps with arbitrary hand structures using differentiable force closure estimator (DFC). https://arxiv.org/abs/2104.09194
- Wang et al. (2023). DexGraspNet. ICRA. https://arxiv.org/abs/2210.02697
- Zhu et al. (2021). Toward human-like grasp: dexterous grasping via semantic representation of object-hand. ICCV. https://openaccess.thecvf.com/content/ICCV2021/papers/Zhu_Toward_Human-Like_Grasp_Dexterous_Grasping_via_Semantic_Representation_of_Object-Hand_ICCV_2021_paper.pdf
- Agarwal, Uppal, Shaw, Pathak (2023). Dexterous functional grasping. CoRL. https://arxiv.org/abs/2312.02975
- Huang et al. (2024). FunGrasp: functional grasping for diverse dexterous hands. https://arxiv.org/abs/2411.16755
- Qin et al. (2022). DexMV: imitation learning for dexterous manipulation from human videos. ECCV. https://arxiv.org/abs/2108.05877
- Handa et al. (2020). DexPilot. ICRA. https://arxiv.org/abs/1910.03135
- Qin et al. (2023). AnyTeleop. RSS. https://arxiv.org/abs/2307.04577
- Chen et al. (2024). Object-centric dexterous manipulation from human motion data (ObjDex). CoRL. https://arxiv.org/abs/2411.04005
- Li et al. (2025). ManipTrans: efficient dexterous bimanual manipulation transfer via residual learning. CVPR. https://arxiv.org/abs/2503.21860
- Mandi et al. (2025). DexMachina: functional retargeting for bimanual dexterous manipulation. https://arxiv.org/abs/2505.24853
- Pan et al. (2025). SPIDER: scalable physics-informed dexterous retargeting. https://arxiv.org/abs/2511.09484
- Zhou et al. (2024). Learning diverse bimanual dexterous manipulation skills from human demonstrations (BiDexHD). https://arxiv.org/abs/2410.02477
- Liu et al. (2024). TACO: benchmarking generalizable bimanual tool-action-object understanding. CVPR. https://arxiv.org/abs/2401.08399
- Lin et al. (2024). Twisting lids off with two hands. CoRL. https://arxiv.org/abs/2403.02338
- Petrenko et al. (2023). DexPBT: scaling up dexterous manipulation for hand-arm systems with population based training. RSS. https://arxiv.org/abs/2305.12127
- Chen et al. (2023). Visual dexterity: in-hand reorientation of novel and complex object shapes. Science Robotics. https://arxiv.org/abs/2211.11744

Abstract or landing page only [L-abs]:
- Chavan-Dafle, Rodriguez et al. (2014). Extrinsic dexterity: in-hand manipulation with external forces. ICRA. https://dspace.mit.edu/handle/1721.1/109430 (PDF download returned HTTP 429)
- Sun et al. (2020). Learning pregrasp manipulation of objects from ungraspable poses. ICRA. https://arxiv.org/abs/2002.06344 (PDF fetched; only the abstract used)
- Ding et al. (2024). PreAfford. https://arxiv.org/abs/2404.03634 (PDF fetched; abstract and summary numbers used)
- Xu et al. (2023). UniDexGrasp. CVPR. https://arxiv.org/abs/2303.00938; Wan et al. (2023). UniDexGrasp++. ICCV. https://arxiv.org/abs/2304.00464
- Liu et al. (2024). QuasiSim. ECCV. https://arxiv.org/abs/2404.07988; Liu et al. (2025). DexTrack. ICLR. https://arxiv.org/abs/2502.09614
- Chang & Pollard. Human-inspired manipulation using pre-grasp object interaction (ICRA 2010 workshop abstract). https://archive.iar.kit.edu/workshops/icra2010/pdf/11.pdf

Secondary only or not opened:
- Chang, Zeglin, Pollard (2008), Humanoids: through Eppner 2015 [L-2nd].
- Chang, Srinivasa, Pollard (2010), ICRA, "Planning pre-grasp manipulation for transport tasks": host 404.
- Babin & Gosselin (2018), IJRR 37(12), doi 10.1177/0278364918802346: publisher 403.
- Tong et al. (2021), "Dig-grasping", RA-L, doi 10.1109/LRA.2021.3062250: not found open.
- Zhang et al. (2023), "FunctionalGrasp", RA-L, doi 10.1109/LRA.2023.3264760: not open access.
- Puhlmann et al. (2016) human flat-object grasping: through Bimbo 2019 [L-2nd].
