# Approach 3: grasp taxonomies, and the phase-structured manipulation model

2026-10-25. CPU and web only (no rentals, no commits). Scripts and outputs: `approach3-scripts/` (commands in §10).
Downloads: `scratchpad/approach3/<one dir per download>` (untrusted data, text extracted with pdftotext).

Labels: **[M]** measured by me without ground truth; **[D]** diagnostic that reads mocap (public episodes only, after
inference); **[L]** primary source opened in full; **[L-abs]** abstract or record only; **[L-2nd]** known only through a
source that cites it; **[I]** inference; **[H]** hypothesis with the experiment that would falsify it.

## Answer

**What does not work.**
- **A grasp-type classifier on our perceived hands.** I wrote a rule-based GRASP-taxonomy classifier (opposition type,
  virtual fingers, palm contact) and ran it on 44 holds from 6 public twins and 8 eval episodes [M].
  - It never finds pad or side opposition, the classes that matter for plates, boards and the lid.
  - Thumb-vs-finger opposition (≥ 110°) shows in at least half the frames of only 5 of 40 holds. The median angle is
    86°, and on the ep12 cup, a grasp that certainly opposes, opposition shows in 16 % of frames.
  - The perceived thumb touches the object in only 3–36 % of the frames of 9 of the 14 plate, board and sweeper holds.
  - Adding 2 cm of correlated hand noise keeps only 36 % of the per-frame labels and flips half the per-hold labels.
  - Even trained human raters reach only κ = 0.54 on grasp type from head-mounted video [L, Bullock 2015].
- **A correct type label as the grasp seed.** The one test already run is negative [M, work log 24 Oct]:
  - setup: ep39 dust pan, seeded with the lateral key pinch (Feix #16) that the successful RL policy used;
  - zero action: 0.243;
  - the best CMA-ES result from that seed: 0.373;
  - the best CMA-ES result from the copied human grasp: 0.81–0.865 (0.958 vs mocap after the fine-tune).
- **Is the type even the bottleneck?** Of the six grasp-related eval failures, the type is the problem in none [I, §4].
  The failures sit in opposition and force, acquisition precision, staging, mesh geometry and phase boundaries.

**What works.** The taxonomy's mechanical content does: opposition, virtual fingers, spread contacts and wraps. It is
already in our designs (biomechanics report §10–11) and needs no classifier. Two type-light pieces are worth doing:
- the wrap rule fired by local geometry plus palm contact, for pot handles;
- the B4 parallel-extension clamp (Feix #22) for boards.

**The owner's phase model is better supported than the type route.**
- 14 of 17 grasp-related failure instances sit at phase boundaries [I from the audits, §6a]:
  - frame 0;
  - grasp onset and lift-off (lid, pan, boards);
  - hand changes;
  - release and placement (evals 16, 28).
- Object-track events are sharp (lift-off within 1 frame of mocap for 5 of 6 objects [D]). Contact-label hold starts
  are 24 frames early to 22 frames late, and hold ends are 26–116 frames after the final placement [D].
- Waiting K frames at an event costs little if the policy then catches up [M]:
  - waiting 2 frames at lift-off costs at most 0.004 episode AUC, against a median of 0.026 if the delay persists;
  - waiting 5 frames costs at most 0.019;
  - waiting at release costs at most 0.003.

**Recommended version (cheapest; no type classifier).** "Event-anchored grasp-lock":
- closure and load are complete by the object's lift-off;
- the hold ends at the object's final placement, plus a 2-frame unload, followed by the existing staged release;
- hand changes only while the object is slow or resting;
- type-light templates: a local wrap for handles, the B4 clamp for boards;
- training-only resets concentrated near the lift-off and placement events.

**Expected gain and cost.**
- About +0.01 to +0.03 on the 20-episode AUC [I]; the eval analysis bounded all grasp fixes at about +0.03 to +0.05.
  The classifier itself adds about 0.
- About 1.5–2 days of CPU work.
- A strong public-twin GPU test costs about $11–15 (§8.3).

**Owner's follow-up: try every feasible grip type and keep the most stable (§11).**
- Worth doing as a portfolio of 3–6 constructed types plus the human copy per hold, with no classifier.
- It needs a new selection fitness:
  - run from frame 0 through the release, all objects;
  - score the 25 % worst disturbed trials (CVaR);
  - re-score the finalists in fresh processes;
  - the copy wins ties.
- Cost: about 3.5 engineering days and about $12–19 of search for the 20 eval episodes.
- Expected gain: about +0.01 to +0.03, overlapping §6.

## 1. Sources: covered, failed, fetched now

| source | before today | today | what matters for us |
|---|---|---|---|
| Feix et al. 2016, GRASP taxonomy, THMS | opened (biomech §3) | re-fetched, Yale PDF, read [L] | See the note below the table. |
| Feix et al. 2009 (KTH, 2 pages) | full (evolution report) | re-fetched [L] | The figure; text extraction is garbled. |
| Bullock, Feix & Dollar 2015, IJRR, Yale dataset | not opened | fetched [L] | See the note below the table. |
| Feix, Bullock & Dollar 2014 (TOH) | opened (biomech §3) | re-fetched [L] | Already summarised: 94 % of instances grasp the smallest dimension; type is predicted at 47 % from object and task. |
| Cutkosky 1989, IEEE TRA | not opened | **failed** (IEEE blocked; Harvard copy 404 / DNS) [L-2nd] | Per Feix 2016: 15 grasps, split mainly by object shape and size, populating only 7 GRASP cells. Per Stival: a tree by the task's adaptability needs. |
| Puhlmann et al. 2016, IROS | through Bimbo 2019 | **failed** (TU Berlin host does not resolve; Wayback reset; IEEE blocked). DOI 10.1109/IROS.2016.7759308 [L-2nd] | Bimbo (opened earlier): humans grasp flat objects with a flip or a slide-to-edge. Heinemann 2015 is the companion taxonomy "suitable for transfer to robotic hands"; record only. |
| Stival et al. 2019, JNER | not opened | fetched [L] | See the note below the table. |
| Key & Lycett 2017–19 | evolution report | not re-fetched | Analogy only [I]: user biometrics predict tool performance more than tool form does. The hand matters more than the human's type label. |
| Johansson & Westling 1984, 1988; Westling & Johansson 1984; Kinoshita 1997 | abstracts (biomech §5) | re-fetched, PubMed [L-abs] | Grip force rises in parallel with load, set to friction within 0.1 s, with a small safety margin. Slip corrections come 60–80 ms later. Load force rates are programmed from the expected weight. **Lift-off and touchdown are signalled by somatosensory events** (1988). |
| Johansson & Flanagan 2009, Nat Rev Neurosci | abstract | [L-abs] | The brain "selects and implements action-phase controllers"; contact events monitor and update them. |
| Romano et al. 2011, T-RO | – | record + secondary summary (MPI page fails TLS) [L-2nd] | PR2 gripper with six tactile-event-triggered states: Close, Load, Lift-and-Hold, Replace, Unload, Open. |
| HOGraspNet, ECCV 2024 | – | fetched [L] | §2 |
| GUN-71 (Rogez et al., ICCV 2015) | – | fetched [L] | §2 |
| Cai, Kitani & Sato, THMS 2017 | – | [L-abs] | §2 |
| Dexonomy, RSS 2025 | named (competitors) | paper + README fetched [L] | §3 |
| GenDexGrasp, FunGrasp, DexTOG | FunGrasp in the robot-thin report | [L-abs] | §3 |

Notes on the three sources marked "see below":
- **Feix 2016.**
  - 33 types, reducible to 17, arranged by opposition (pad / palm / side), virtual fingers, power / intermediate /
    precision, and an abducted or adducted thumb.
  - "Classification … depends not only on the hand pose, but also the type of contact": a glove "that measures only
    the joint angles might not be sufficient".
  - Inter-rater confusions: tripod #14 ↔ lateral #16 69.7 % / 41.8 %; prismatic-2 #8 → #9 27.1 % and → #16 26.7 %.
- **Bullock 2015.**
  - 27.7 h of head-mounted video, 18,210 instances, two trained raters.
  - **Cohen's κ = 0.54 for grasp type.**
  - Transitions shorter than 1 s are not recorded.
  - The CSV is CC BY 4.0.
- **Stival 2019.**
  - Data: 40 subjects × 20 grasps, CyberGlove and sEMG.
  - The data-driven trees give 5 groups: flat, distal, cylindrical, spherical, ring.
  - Power / precision and thumb abduction are **not** supported. Opposition is partly supported, the virtual-finger
    assignment well.
  - "The shape of the object influences the positioning of the fingers … more than the usefulness for power or
    precision tasks and opposition type."

Blocked once and not retried: ieeexplore, robotics.tu-berlin.de, biorobotics.harvard.edu, is.mpg.de (TLS),
web.archive.org (reset), Semantic Scholar / OpenAlex (rate limit), GitHub API outside the session scope.

## 2. Can we recognise the grasp type? Literature and our measurement

**Literature** [L unless marked]:

| method / dataset | input | classes | accuracy | caveat |
|---|---|---|---|---|
| HOGraspNet (Cho et al., ECCV 2024) | GT-fitted MANO mesh + per-vertex contact (multi-view RGB-D) | 28 (merged from Feix 33) | **0.88** on the seen-subject split | Labels are by instruction (3 types per object); the input is mocap-grade. Only the in-distribution split is reported for classification. HO3D and DexYCB cover only 15 and 14 of the 33 types. |
| GUN-71 (Rogez et al., 2015) | one egocentric RGB-D image | 71 / 33 / 17 | **18 % / 20.5 % / 20.5 %** (deep features, cross-scene) | 85 % once the same subject and scene appear in train and test, i.e. overfitting. |
| Cai, Kitani & Sato (THMS 2017) [L-abs] | egocentric RGB, hand features | 17 (Cutkosky-based) | 92 % lab, **59 % real world** | |
| Yale dataset (Bullock 2015) | human raters on video | 33 | κ = 0.54 | Human ceiling on egocentric video. |
| ContactPose, OakInk / OakInk2, DexYCB, ARCTIC | MANO + object pose | intent, primitive or no grasp-type labels | – | No Feix labels (HOGraspNet Table 1). |

**Our classifier** [M] (`grasp_type_rules.py`):
- Input: the holds of `pipeline/hold_phases.py`.
- Two feature sources:
  - R: the reference's 16 robot-site contact slots;
  - H: the perceived MediaPipe joints against our mesh, contact within 1.5 cm, palm within 2.5 cm.
- Rules after Feix's opposition definitions: power, side, pad2/3/45, under (platform or hook), top (push / drag),
  one-sided.
- Noise test: AR(1) rigid hand offset (σ 1 or 2 cm, τ 5 frames) plus 0.5 cm per joint, 4 seeds.

| result over 44 holds (≥ 15 frames; 6 public twins, ep27 grasp-lock reference, 8 eval refs) | value |
|---|---|
| labels, R | one-sided 21, top 14, under 7, power 1, none 1. **pad / side: 0** |
| labels, H | power 12 (pot handles, spoon), one-sided 11, top 10, under 6, none 5. **pad / side: 0** |
| holds with opposition ≥ 110° in ≥ 50 % of contact frames | 5 / 40 (median angle 86°) |
| ep12 blue cup (a successful, certainly opposed grasp) | opposed in 16 % of frames, median 76° |
| R vs H agreement | per hold 0.52; per frame 0.43 (median) |
| noise 1 cm / 2 cm: per-frame agreement | 0.56 / 0.36 |
| noise 1 cm / 2 cm: per-hold agreement | 0.79 / 0.45 |
| noise 1 cm / 2 cm: stages per hold | 4.7 / 5.5 |
| perceived thumb contact share, corrected slot labels (§9) | 0.03–0.36 in 9 of 14 plate / board / sweeper holds, e.g. ep18 pan 0.19, sweeper 0.15 / 0.03; ep24 boards 0.32 / 0.36; ep39 carry 0.27; eval 19 pan 0.25, sweeper 0.06; eval 25 board 0.12. Also eval 1 lid 0.25, eval 33 spoon 0.21 |

**Reading.**
- [I] Opposition defines every pad and side grasp (VF1 = the thumb). Our perception does not resolve it on features
  1–2.7 cm thick: board 0.8 cm, strap 1.4 cm, ring band 1.2–2.3 cm, spoon 2.7 cm.
- [I] The joint centres' ±1–2 cm error is the size of the feature. The thumb, the most occluded digit in egocentric
  views, drops out first.
- [I] A rule-based classifier is feasible only for **power vs not-power**: palm contact on a handle, already
  0.87–0.98 palm share on the pot holds.
- [I] Realistic accuracy for fine types from our input: at or below the GUN-71 / Cai real-world range (20–59 %), and
  below the human κ of 0.54.

## 3. Human-to-robot use of grasp types

| method | uses types? | hand / sim | code, licence | usable on Sharpa in 10 days? |
|---|---|---|---|---|
| Dexonomy (RSS 2025) [L] | Yes: 31 GRASP types. One human-annotated template per hand and type; object-to-template alignment, then local MuJoCo refinement; contact-aware squeeze (Jᵀf) | Shadow, Allegro, Leap, MANO, G1 (README); MuJoCo CPU + GPU | Code released. Licence CC BY-NC per the 24 Oct work-log check (LICENSE file not retrievable today) | Partly. A Sharpa MJCF plus one template per type, about 1–2 days. See the notes below. |
| GenDexGrasp (ICRA 2023) [L-abs] | No: contact maps as a hand-agnostic representation | 5 hands (MultiDex) | GitHub | Low: a new hand needs data; our contact maps come from perception (§2). |
| FunGrasp (2024) [L-abs, robot-thin report] | Functional pose from one RGB-D human grasp, then RL | LEAP, Allegro, Inspire | released | Already mirrored in grasp-lock (copy + losses + RL). |
| DexTOG (RA-L 2025) [L-abs] | Language and task-conditioned, not taxonomy | Shadow, 80 objects | – | No. |
| DexGraspNet 2.0, UniDexGrasp | No (force closure / RL) | LEAP / Shadow | CC BY-NC (DGN 2.0) | Seeds only (learned-grasp-models report). |
| ManipTrans, DexMachina, SPIDER (the metrics' namesakes) | **No.** They track human hand and object trajectories; grasp choice is left to residual RL (ManipTrans), virtual object controllers (DexMachina) or sampling with contact guidance (SPIDER) (robot-thin report, notes 04) | Inspire, Allegro, Shadow, others | SPIDER CC BY-NC | Already used as ideas: the VOC curriculum, residual RL, contact guidance. |

Dexonomy notes:
- Its synthesis success is low and drops with friction. GSR is 24 / 23 / 36 % under the normal friction setting
  (μ 0.6, torsional 0.02) and **12.8 / 6.6 / 11.4 %** under the hard setting (0.3 / 0.002), for power / intermediate /
  precision.
- Our evaluator has no torsional friction (condim 3), so it is closest to the hard setting: intermediate (lateral) and
  precision types suffer most.
- The validation is a static 2 s six-direction push, not our acquisition from the table and the human's tilts.
- Its real-world failure mode is "unsuitable grasp types for the object, especially Lateral (#16)". The type is chosen
  by **simulated success** (the Top-1 oracle), not by what the human did [L].
- [I] This matches our ep39 result: physics fitness, not the human's type, picks the grasp.

## 4. The grasp-related eval failures, one by one

Twin mapping: ep3 and ep35 are **eval** spoon episodes (no public twin, no mocap). The spoon twins below are evals
16 and 33 themselves.

| eval (twin), sim_vs_ref | human grasp per hold (video / audits; Feix label inferred) [I] | perceived: classifier (thumb, palm share) [M] | our locked grasp [M, audits] | would a correct type change the robot grasp? | where it really fails |
|---|---|---|---|---|---|
| **1 (ep2)**, 0.205 | Lid: fingers and thumb pinch the bridge strap from above (strip f30; pad / prismatic, #8 / #9-like). The palm is not on the lid: the old "palm 0.80" was the thumb-tip slot (§9). Pot: medium wrap of the stick handle, thumb on top (#3 / #4) | lid top / top (thumb 0.25 eval, 0.97 ep2; palm 0); pot power (palm 0.95) | lid: snapped copy, 52° opposition, flung at lift-off ±4 frames; pot: copied, 95°, the wrap rule never fires | Lid: no; it is already a strap pinch, but without real opposition. Pot: **yes** (wrap), via the local-PCA rule, not a classifier | lid: hull overlap 7.6 mm (mesh, frame 0) + no opposition at lift-off (boundary). pot: grasp-onset boundary (leaves the reference at hold start f96) |
| **25 (ep24)**, 0.232 | Board: palm / finger drag (non-prehensile), slide to the edge, parallel extension #22, two-hand turn, edge pinch while standing. **3–4 grasp changes per hold** | one-sided / under (thumb 0.12–0.91) | one static snap from the drag; thumb 2.2–4.8 cm off; never acquired (0 of 5 lift board 1) | **Yes** (B4 clamp), but the design is already in biomech §11.3; no classifier needed | slots missing (the cross cannot be assembled), acquisition (wrist lag 3–11 cm), staging |
| **19 (ep18)**, 0.627 | Pan: lateral key pinch on the ring band, then a hook through the ring for the lift (RL-found; the human's contacts are unreliable, §9); sweeper: thumb-fingers clamp | one-sided (pan thumb 0.25, sweeper 0.06) | copied; CMA-ES 0.18 → 0.36 (ep18: 0.50 → 0.957 after the fine-tune) | No: the type-correct template lost to the copy on ep39 | chaotic basin: no robust grasp found; pan lost 6 frames after lift-off (boundary) |
| **33**, 0.421 | Spoon stirring in a held cup: tripod / lateral family (#14 / #16, confusable even for humans) | one-sided / top (thumb 0.21) | wrap on the handle; search 0.11 → 0.32; lost at f110, mid-hold | A tripod copy would likely **hurt**: precision types are weakest without torsion (Dexonomy hard setting) | cup perception (B) dominates; spoon mid-hold slip (force) |
| **28 (ep27)**, 0.751 | Pot handle medium wrap #3 | power (palm 0.87) | copied, 160° opposition (ep27 0.95–0.97 after the fine-tune) | No | placement 8.5 cm off; rack knocked in the last frames (**release boundary**) |
| **16**, 0.850 | Spoon held at the handle (pad family) | one-sided (thumb 0.44) | wrap | No | spoon left 12.7 cm off after its hold (**release boundary**) |

## 5. Design options, ranked

| option | verdict | why |
|---|---|---|
| (a) per-hold-phase type classifier | **No** | §2: it never sees pad or side opposition; the labels flip under realistic noise. |
| (b) type → robot template (opposition, VF assignment, closing pattern, squeeze from statics) as the grasp-lock seed and CMA-ES bounds | **Only type-light, hand-picked**: the local wrap (pot handles) and the B4 clamp (boards), as extra CMA-ES starts next to the copy, never instead of it | The ep39 template seed lost to the copy (0.373 vs 0.81–0.865). The squeeze from statics already exists (`grasp_force.py`; the minimal-force version failed: ep3 0.309). |
| (c) type-aware RL reward | **No** | It needs a reliable label. FlashCHORD already has missed / unintended-contact reward terms driven by the reference's contact labels [C, objective config + reference loader]. |
| (d) mesh loop: contacts as shape evidence (fingers under ⇒ bottom face) | **Not with perceived contacts** | The constraint is finer than the hand error (8 mm board vs ±1–2 cm; the thumb is missing on thin objects). Only coarse rules are safe: graspable thickness ≤ aperture; support and interaction carving already exist. |
| (e) phase-structured events (owner's addition, §6) | **Yes, cheapest with the most impact** | Most failures are at boundaries, and the events are measurable. |

## 6. Phase-structured manipulation (owner's addition)

The human model is a sequence of action phases separated by contact events [L-abs]:
- Johansson & Flanagan 2009: action-phase controllers;
- Johansson & Westling 1988: lift-off and touchdown are signalled by somatosensory events;
- Romano 2011 implements the same on a robot as a state machine [L-2nd].

**Mapping to our code** [C]:

| phase | what we have | gap |
|---|---|---|
| reach / which hand | `hold_phases.py` (contact labels ≥ 2 slots + object moving); `grasp_lock --single_hand` (no hand-overs); `--approach_cm`, `--onset_anchor` | Hold start from contact labels is −24 … +22 frames off (below). |
| close (where, with what) | `grasp_lock` grasp frame g* (most fingers on), close ramp from h0 = min(hold start, move − CLOSE); snap / wrap / templates | – |
| load (how much) | `grasp_force.py` + `task_wrench.py` (LP squeeze, 2-frame lead), `--squeeze_profile anatomic` | The squeeze is not tied to lift-off. |
| lift / transport | locked wrist follows the object path; lift feed-forward; ILC | – |
| replace / unload / release | staged release after the hold end s1: relax → unroll → withdraw | s1 comes from contact labels, 26–116 frames after the final placement [D]. |
| spatial boundaries | `robot_clearance.py` (penetration), `rest_support.py` / `support_fill.py` (stable rests), `tools/manip_segments.py` (rest / carry / slide / lift labels; prototype, not wired in) | – |

**(a) Where the failures sit** [I, from the audit timelines]:
- **At boundaries, 14 of 17:**
  - frame 0 (ep21, ep26 / eval 28, ep31, ep2 lid overlap);
  - grasp onset or lift-off (lid lost at lift-off ±4 frames in all 5 variants, eval 1 lid lost 4 frames after its
    lift-off; ep18 pan flicked at closure, eval 19 pan lost 6 frames after lift-off; ep24 boards never acquired; ep18
    sweeper hold 22 frames late; eval 1 pot at hold start);
  - hand change (ep39 carrier merge, eval 35 switch);
  - release / placement (evals 16 and 28).
- **Inside phases, 3:** ep2 pot rotating in the hand; ep18 pan slipping during the tilt; eval 33 spoon at f110.

**(b) How precisely the events can be detected without ground truth** [M rules, D accuracy]:
`events.py`, `final_rest.py` on ep18, ep24 (the board names are swapped between our reference and mocap), ep39 and
ep31.

| event | source | error vs mocap, frames (20 fps) |
|---|---|---|
| lift-off (origin > 1.5 cm above start, 3 frames) | our object track | 0, 0, 0, +1, 0; −12 (board 1) |
| motion onset (> 1 cm or 8°) | our object track | 0, 0, +1, +1; −18, −65 (track jitter triggers it) |
| final rest (last movement + 1) | our object track | +1, +10, +16, +4; +50, +147 (a standing board and the sweeper in the rack jitter) |
| hold start | contact labels | +22, −7, −9, −7, −6, −16 vs onset |
| hold end | contact labels | **+26, +30, +31, +26, +47, +116** vs final rest |

Lift-off from the object track is the sharpest event. Onset and rest need a jitter guard (hysteresis, or a minimum
duration). Release timing from contact labels is 1.3–6 s late.

**(c) Event-triggered transitions under a time-indexed evaluator** [C, M]:
- The evaluator plays our policy against the time-indexed reference at 20 fps.
- The actor observes:
  - the current reference command (wrist, fingers, object);
  - object and hand state;
  - **the simulated contacts per hand link** (positions and force directions in the wrist frame): a tactile signal;
  - no phase variable. The normalised time phase goes only to the critic.
- New observation terms cannot be added: the pinned evaluator builds observations from FlashCHORD's own term set.
- What can be done:
  - **encode the phases in the reference**: the closure ramp, the load timing and the release are scheduled from
    object events known offline, like humans' feed-forward force programming;
  - let the policy react to the observed contacts within its residual (±0.2 m clip);
  - training-only patches: phase-weighted rewards (as the FDR port) and **boundary-focused reset sampling**. Today
    resets draw reference frames (90 %; frame 0 in 10 %, 50 % in the last curriculum stage); FC_DROP_START is the precedent patch.
- What waiting costs, `lag_cost.py` [M]: the object path is delayed K frames at an event, scored against our
  reference with the kit's ADD-AUC definition; episode AUC loss per object, 20 objects in 12 episodes.

| wait at | K = 1 | K = 2 | K = 3 | K = 5 |
|---|---|---|---|---|
| lift-off, delay persists (median / max) | 0.007 / 0.027 | 0.026 / 0.076 | 0.046 / 0.142 | 0.076 / 0.271 |
| lift-off, then catch up at 1.5× over 2K frames | 0.0001 / 0.0007 | 0.0007 / 0.004 | 0.002 / 0.009 | 0.008 / 0.019 |
| final placement / release, with catch-up | 0 | 0 | 0 / 0.0001 | 0 / 0.003 |

**(d) Cheapest version** (CPU, about 1.5 days):
1. **Event-anchored windows** in `grasp_lock.py`:
   - full squeeze by lift-off − 2 frames, so closure and load happen while the object rests;
   - the onset anchor is kept for pre-lift drags;
   - hold end = the object's final rest + 2 frames of unload, then the existing release;
   - the events come from the object track, with a 5-frame hysteresis.
2. **Hand changes** only where the object is resting or slower than 0.5 cm/frame; otherwise single_hand.
3. **Boundary resets** (training-only patch): 50 % of non-frame-0 resets within ±10 frames of a lift-off or a final
   rest.

The pre-registered test is T2 in §8.

## 7. Risks and expected effect

- **Hand-pose noise vs thin objects** [M]: decisive for (a) and (d); irrelevant for the object-event route.
- **Multi-stage grasps vs one lock** [M, boards audit]: the human regrasps 3–4 times; the event model gives stage
  boundaries, but a second lock per stage is new work.
- **Human-to-Sharpa gap** [biomech §1]: the thumb has ±20° abduction and no pronation, the palm is flat, the fingers are
  1.6× longer. A copied type is not a feasible robot grasp.
- **Simulator limits** [notes 24]: condim 3 (no torsion) makes single-pair pinches infeasible; finger kp 1.7 N m/rad
  caps forces at about 10 N.
- **Is the type the bottleneck?** No for 6 of 6 failures (§4).

| eval | expected Δ episode AUC [I] | from |
|---|---|---|
| 1 | +0.05 … +0.20 | lid seat (mesh) + pot local wrap; the type classifier contributes 0 |
| 25 | +0.03 … +0.15 | B4 clamp; capped by the missing slots |
| 19 | 0 … +0.10 | robust search (more seeds), not the type |
| 33 | 0 … +0.05 | perception first |
| 28, 16 | +0.02 … +0.08 each | event-anchored release / placement |

Sum on the 20-episode mean: about +0.01 to +0.03.

## 8. Experiments

**T1, falsifies the type idea; CPU, about 1 day of build + about 2 h of CPU search.**
- Episode: ep24, board 1 (left-hand hold f4–90).
- Two seeds for the same robust CMA-ES (8 worlds × 14 generations, K = 2 jitter copies, the ep39 budget):
  - (i) the current snapped copy;
  - (ii) the type template: B4 parallel-extension clamp, thumb DP on top 3 cm in, fingers under (biomech §11.3).
- Also recorded: the label `grasp_type_rules.py` gives this hold, at the commit of this report.
- Metric: GT-free sim_vs_ref over f4–90 and the simulated board-1 lift at f30. Registered AUC [D] is reported only.
- **The type idea is falsified if:**
  - (ii) − (i) < +0.10 in window sim_vs_ref, or the board-1 lift with (ii) is under 10 cm;
  - **or** the classifier's label is not pad or side (then the template cannot come from perception, whatever its
    value).

**T2, the phase model; CPU, zero action.**
- Episodes: ep2, ep18, ep24, ep39. Arms: contact-anchored (current) vs event-anchored windows (§6d), same everything
  else.
- **Pass** if hold-window sim_vs_ref rises by ≥ 0.05 on at least 3 of 4 episodes and drops by more than 0.02 on none.
- Registered AUC [D] is reported, not used.

**T3, the strongest test (GPU; owner: "we can do expensive tests").** Arms:
- A: the current grasp-lock (rerun at the same commit);
- B: phase-structured (§6d, including boundary resets);
- C: B plus the type-light templates (local wrap on pot handles, B4 on boards, pan key pinch + ring hook, lid strap
  side pinch L1) as extra CMA-ES starts.

Episodes: the targets ep24, ep2, ep39, ep18 and the controls ep27, ep12. The spoon has no public twin with mocap. Eval
3 and 35 may only be run afterwards as GT-free sim_vs_ref checks, never to choose.

Plan: 2 seeds (42, 43) × 70M fine-tunes (the grasp-lock length, 18.7 min measured), 5 official evaluations each,
checkpoint chosen by sim_vs_ref, then registered AUC vs mocap [D].

| item | count | estimate |
|---|---|---|
| fine-tunes | 3 arms × 6 eps × 2 seeds = 36 × ≈ 20 min | 12 GPU-h; 2 per GPU → ≈ 6 box-h |
| CMA-ES (GPU, 256 worlds) | ≈ 14 holds × ≈ 5 min | ≈ 1.2 box-h |
| setup, references, ILC, evaluations | 4 boxes | ≈ 1 box-h |
| **total** | | **≈ 8 box-h ≈ $11–15** (at $1.4–1.9/h); the 250M variant ≈ 45 box-h ≈ $63–86 |

Rules, fixed before the run:
- **Adopt B** if:
  - B − A ≥ +0.05 mean registered AUC over the 4 targets;
  - at least 3 of 4 targets improve in both seeds;
  - no control loses more than 0.02.
- **Adopt C** over B only if C − B ≥ +0.05 on the targets where C changes the seed; otherwise the type route ends.

What it decides: whether the eval rerun uses the event-anchored recipe, and whether any type template enters it.

## 9. Correction to earlier reports (found while testing) [M]

The reference's `mano_link_names` column lists MANO links (palm, thumb1 … pinky3). But `pipeline/mkref.py` writes the
16 contact slots in its PROBE_SITES order: tips, DPs, thumb MCP / finger MPs, then the palm.

`slot_order_check.py` on an unretargeted ep12 reference:
- every slot is within its threshold of the mkref site in **97–100 %** of its active frames;
- slot 0 has the palm probe within threshold in only 19 % of them.

So the per-link shares in `human_grasp_census.py` and in the plates, boards and starts audits (`mano_where.py`,
`refload.py`) are mislabelled:
- "palm" = thumb tip;
- "thumb1–3" = the index, middle and ring tips;
- "pinky3" = the palm.

Consequences:
- The ep2 lid is held by fingers and thumb, **not the palm**.
- The perceived thumb is mostly absent on the plates (`out/digit_shares.txt`).
- The claim "humans use thumb-vs-finger opposition in every hold [M]" (biomech §9.2) has no measured basis: it may hold
  in video, but our perception does not show it.
- Video-based readings (the boards audit) and FlashCHORD's rewards (which use any-slot activity) are unaffected.
- In contact-retargeted (`mck`) references the robot frames move after labelling (slot-site consistency 0.47–0.97).

## 10. Reproduction

- Machine: Claude cloud VM (4 CPU). Python: scratchpad `venv` (numpy, scipy, trimesh, pyarrow); `python -I`.
- Inputs: perceived references from the HF store, already in the scratchpad (paths in `out/inputs.txt`):
  - `runs/20261024-{e1,e3,w1,e2}-*/refs/perc2mck*`;
  - `runs/20261024-pack-31ef267/refs/perc2mck/ep*` (eval);
  - ep27 `runs/20261024-w2-37cc551/refs/glock/ep27/ref_gl.parquet`;
  - ep12 `runs/20261021-auto18-966eb96/refs/perc2mc/ep12`.
- Meshes: `meshes/library_v3`. Mocap (diagnostic only): public parquets for ep18, 24, 31 and 39.
- Commands:
  - `grasp_type_rules.py OUT TAG=REF …`
  - `digit_shares.py TAG=REF …`
  - `slot_order_check.py REF`
  - `events.py REF --gt GT`
  - `final_rest.py REF GT [swap]`
  - `lag_cost.py OUT TAG=REF …`
  - `fetch.sh NAME URL` (downloads)
- Outputs: `approach3-scripts/out/`.

## 11. Try every feasible grip type and keep the most stable (owner's follow-up, 25 Oct)

The idea is a generate-and-test portfolio:
- build one robot grasp per feasible type for each hold, with no classifier;
- simulate each over its whole phase chain;
- choose by a GT-free fitness on the object's motion against our reference, release included.

**Verdict.** Yes, as a portfolio of seeds for the existing search, with the human copy as the default. It sidesteps
§2's perception limit, because no label is needed. Two things are new:
- a fitness that runs from the evaluator's frame 0 through the release;
- a robust selection rule.

Without them the search keeps the failures we already measured: chaotic picks (ep18: 1e-5 jitter moves 0.37 to
0.18–0.44) and starts from a reset [M, work log].

### 11.1 Candidate types per object family (Sharpa-realisable; forces from the LP in biomech §10) [I + M]

| family (holds) | candidates (Feix #) | dropped as infeasible in this simulator |
|---|---|---|
| spoon handle, 2.7 cm | medium / small wrap (#3 / #2) at 2 positions along the handle × palm up / down; adducted-thumb wrap (#4) | tip and lateral pinch (one opposing pair: no torsion) |
| plates: dust pan, sweeper | P3 cage-hook (index through the ring, thumb on the band, middle under); lateral key pinch (#16, RL template); band / neck clamp (#22-like, S2); hook (#15) only as a lift stage | single pinch P1 / S3; key pinch along the band, P2 (30–60 N) |
| boards | B4 parallel extension (#22) at the long edge and the short end; B5 two pad pairs; platform (fingers under, palm up) | edge-only cantilever B2 / B3; lateral pinch |
| cups | side wrap (#1 / #3); rim precision disk (#12) from above; current copy | – |
| pot stick handle | local-PCA wrap (#3) near the middle vs at the end; adducted thumb (#4) | end pinch T1 |
| lid strap | strap side pinch L1 (#8 / #7 with a 2.4 cm spread) | hook under the strap (1.5 cm gap in our mesh); rim pinch L3 (25–48 N) |
| pitcher handle | wrap through the loop W1 (#3) | hook W2; pinch W3 |

That gives **3–6 typed candidates per hold**, plus the human copy.

Generation, in the style of `wrap_grasp.py`, with FlashCHORD's own geometry:
1. Find the held part from local geometry around our contact centroid: the local-PCA axis for handles, the plate
   normal and nearest edge for plates.
2. Place the palm frame by a per-type rule: palm normal and approach direction relative to the part axes, plus a grip
   offset (the B4 and P3 specs in biomech §11).
3. Close each digit until contact with `close_fingers`; abducted-thumb types close the thumb opposite the finger pads.
4. Pre-filter with the contact-force LP (`grasp_force.py`): a candidate whose wrench LP is infeasible, or that needs
   more than about 10 N per contact over the reference's load, is dropped before any simulation.

Dexonomy: its MANO / Shadow templates per type could be retargeted through our E2S IK. But the licence is CC BY-NC
(work log) and it validates static 6-axis pushes only, so our own constructors are preferred.

### 11.2 Fitness and selection

The current `grasp_evolve.py`:
- resets objects and hands onto the reference at f0 = approach start − PRE;
- scores the ADD-AUC of the held object (or all objects) up to the hold end + POST;
- takes the mean over K jittered copies.

Changes:
1. **No reset inside the episode.** Simulate from frame 0, as the evaluator does, with the grasps already chosen for
   earlier holds baked in (holds chosen in time order). A candidate is then judged in the state the evaluator will
   produce: the other hand's swing, an object that already slid, frame-0 transients.
2. **Window through the release.** Score up to the next hold of that object, or the episode end, with `--all_objects`.
   A knocked or dragged object stays wrong for all later frames, so the plain episode ADD-AUC already prices the
   release. Add two diagnostics:
   - in-hand slip during the hold (`grasp_search.py`'s slip test);
   - object drift in the 20 frames after the final rest.
3. **Disturbed trials.** K = 4–8 copies per candidate, each with:
   - jitter on the edit (5 mm / 0.05 rad);
   - an initial object offset (±3 mm / ±2°, perception scale);
   - a wrist push random walk (`grasp_search` NOISE).

   Fitness = the 25 % lower quantile (CVaR), not the mean: the evaluator gives one rollout, and bimodal episodes
   (evals 3, 5, 15) pay for the bad mode.
4. **Against winner's curse.**
   - Screen with one generation (64 × 4 worlds) per type.
   - Run a full CMA-ES (64 × 4 × 20 generations) only for the best 2 types plus the copy.
   - Re-score the 3 finalists in fresh single-world processes with K = 16 new disturbance seeds.
5. **Ties go to the copy.** Choose a typed candidate only if its re-scored CVaR beats the searched copy by ≥ 0.05 and
   by at least 2 standard errors. Basis: the ep39 template lost (0.373 vs 0.81–0.865), and the copy carries the human's
   timing.

### 11.3 Does the choice survive the RL fine-tune?

Partly [M, 18 public runs, EA-vs-RL report; work log]:
- Spearman ρ = 0.73 between zero-action and fine-tuned sim_vs_ref.
- Zero action ≥ 0.5 → ≥ 0.73 fine-tuned (8/8); < 0.36 → ≤ 0.43 (10/10).
- ep39: search window 0.857 → 0.958 vs mocap.
- ep18: windows 0.50 / 0.58 → 0.957.

**Above the "holds" threshold the order is not reliable.** On ep12 and ep27 the search raised the windows (0.563 → 0.772,
0.791 → 0.866). Yet the fine-tuned results, 0.868 ± 0.122 (one of five rollouts failing) and 0.949, did not beat the
earlier unsearched grasp-lock (0.854–0.910, 0.957–0.972). Other recipe changes confound this.

So the portfolio should be used to cross the about 0.5 hold threshold. When finalists are within 0.05, a short 20M
fine-tune tournament (about 6–8 min each) should decide [H, falsified if the 20M ranking disagrees with the 70M
ranking in ≥ 2 of 4 twins].

### 11.4 Compute and effort

**Measured unit costs:**
- GPU: ≤ 0.35 ms per world-frame (300 × 105 frames in 11 s, setup included); a 256-world robust search took
  "minutes" per hold.
- CPU: 10–34 ms per world-frame, about 6 s setup per fresh environment.

**Estimated per hold [I], full chain of about 300–400 frames:**
- screening 5 types × 1 generation: about 5 min;
- 3 full searches: about 30–40 min;
- re-scoring: about 2 min.

On one GPU with 2–3 searches running concurrently, that is about 15–20 min of box time per hold.

**For the 20 eval episodes** (about 30 holds after `single_hand`): about 8–10 box-h, **$12–19**, on top of the
unchanged fine-tunes. CPU is good only for one-hold falsifiers: 8 worlds × 14 generations ≈ 6 min per candidate on
ep24's 120-frame window.

**Engineering:**
- constructors for 4 families (B4 / B5, P3 / clamp, local wrap, L1): about 2 days;
- frame-0 sequential fitness, CVaR, object disturbances, fresh-process re-scoring in `grasp_evolve.py`: about 1 day;
- LP pre-filter and the `glock_public.sh` driver: about 0.5 day.

Total about 3.5 days. A reduced version takes about 2 days: B4 + local wrap + the fitness changes.

### 11.5 Expected gain [I] and tests

| eval | today | portfolio candidates that matter | expected Δ episode AUC |
|---|---|---|---|
| 25 boards | 0.232 (search found no basin: 0.47 / 0.20) | B4 long / short edge, platform | +0.05 … +0.15 (capped by the missing slots) |
| 1 lid + pot | 0.205 | L1 strap pinch; local wrap on the handle | +0.05 … +0.20 (the lid wedge is a mesh problem, frame 0) |
| 19 dust pan | 0.627 (search 0.18 → 0.36) | P3 cage-hook, key pinch, band clamp: more basins | 0 … +0.15 |
| 33 spoon | 0.421 | wrap positions | 0 … +0.05 (perception first) |
| 28 pot | 0.751 | release-aware fitness (rack knocked, placed 8.5 cm off) | +0.02 … +0.08 |
| 16 spoon | 0.850 | release-aware fitness (left 12.7 cm off) | +0.02 … +0.08 |

On the 20-episode mean that is about +0.01 to +0.03 (not additive with §6's event anchoring; the two overlap on 28 and
16).

**Cheapest CPU falsifier (pre-registered).** This is T1 widened to a portfolio.
- Hold: ep24 board 1, left hand.
- Candidates: the copy, B4 long edge, B4 short end, platform.
- Search: each gets the same CPU robust search (8 worlds × 14 generations, K = 2), with the new frame-0-to-f120
  fitness.
- Finalists are re-scored with K = 8.
- **Falsified if:**
  - no typed candidate beats the searched copy by ≥ 0.05 CVaR;
  - **or** no candidate lifts board 1 by ≥ 10 cm by f30.
- Cost: about 1 day of build plus about 1 h of CPU. [D] registered AUC is reported, not used.

**Strong GPU test (pre-registered).**
- Arms: A = the current recipe (copy + robust CMA-ES); P = the portfolio with the §11.2 rules.
- Episodes: ep24, ep2, ep18, ep39 + controls ep12, ep27.
- Each selected grasp: 70M fine-tune, 2 seeds × 5 official evaluations, scored by registered AUC [D].
- Cost: searches about 3 box-h + fine-tunes about 2 box-h + setup about 1 box-h ≈ 6 box-h, **≈ $8–12**. Arm A can be
  shared with §8 T3.
- **Adopt P** if:
  - P − A ≥ +0.05 mean over the 4 targets, in both seeds;
  - no control loses more than 0.02.
- Also report how often P picked a non-copy type, and whether its zero-action margin predicted its fine-tuned gain.
  This decides whether the portfolio enters the eval rerun.
