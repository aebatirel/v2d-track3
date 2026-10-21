# Track 3 forensics and ideas (2026-10-21, evening)

Owner's question: what is wrong with our approach and its architecture, is it the only way to the goal, and what out-of-the-box
ideas (other embodiments, detecting the manipulation type) could get us past the leader (AUC 0.831). Evidence is from today's
validation runs and CPU replays (`docs/work-log.md`, 2026-10-21 entries). Measured numbers are marked as such; everything in
§3 is a hypothesis with the experiment that would falsify it.

## 0. Where we stand (measured)

| episode | task | our score (sim vs mocap) | our reference vs mocap (ceiling) | objects never moved (floor) |
|---|---|---|---|---|
| ep27 | pot into rack | 0.965 | — | — |
| ep2 | pot + lid | 0.926 | — | — |
| ep12 | cup onto rack | 0.890 (another seed 0.604) | — | — |
| ep21 | pouring | 0.826 | 0.985 | — |
| ep18 | sweeper + dust pan (tool use) | **0.396** registered (8 rollouts of that policy: 0.13–0.41) | 0.982 | **0.637** |
| ep24 | slide a board to the edge, lift it | **0.232** registered | 0.799 | 0.229 |

(ep27/ep2/ep12/ep21: scans as meshes, earlier pipeline, one seed. ep18/ep24: today, our own meshes, registered scorer.)

Reading:
- **Perception is not the bottleneck on the hard episodes.** Our reference already scores 0.98 (ep18) and 0.80 (ep24) against
  mocap. The robot policy loses almost all of it.
- **On ep18 the trained policy is worse than doing nothing** (0.40 vs floor 0.64). The scorer only looks at object poses:
  every object the robot knocks over costs more than not touching it.
- To beat 0.831 we need the hard episodes (about 4 of the 20 eval episodes are their twins) at ~0.55–0.7, with the easy ones
  holding ~0.9.

## 1. Forensics: what is wrong, by layer

### 1.1 Architecture: a long kinematic chain with physics only at the very end
Our pipeline is open-loop: perception → MediaPipe hands → kinematic IK to the Sharpa hand (NVIDIA E2S) → reference →
per-episode RL (FlashSAC, 250M steps) → one evaluator rollout. Physics enters only in RL. Every upstream artefact that is
physically impossible becomes a target the policy cannot follow, and FlashCHORD's terminations (wrist > 15 cm, object > 10 cm
or 0.5 rad off the reference) then end the training episode before the policy ever sees the task:
- ep24 (old reference): with no policy and the real soft wrists, the near board popped 20° on the first physics step and the
  episode ended at once. **Every training episode starting at frame 0 died immediately**, so the policy could not learn the
  start of the episode (measured, CPU replay).
- ep18: with no policy the episode ends at ~frame 20, where the right hand cannot follow a 0.6 m/s reach (measured).
- We had **no physics preflight**: today four root causes were found on the CPU at no cost (dust pan / pot undersides,
  Newton's colour split, overlapping hands, finger penetration), after GPU runs had already failed on them.

### 1.2 Embodiment mismatch: human hand → Sharpa hand
- The robot hand is larger than a human hand. E2S fits joint and fingertip targets with a heavy wrist cost and does not
  know the robot's collision geometry. Result at reset in ep24: the two robot hands inside each other by up to 14 mm, a
  finger 12.7 mm inside a board (measured contact dump).
- Joint-target clearance does not transfer to the robot: raising it from 6 to 10 mm made a fingertip go from 3.5 to 8 mm
  inside the board (measured). Clearance must be enforced on the robot's own geometry after retargeting.
- Wrist stiffness is not the limit: the mid-stiffness wrist (kp 400 vs 25) made both hard episodes worse (ep18 0.193 vs
  0.381, ep24 0.050 vs 0.096). Hypothesis falsified.

### 1.3 Hand perception
- Monocular MediaPipe loses hands in fast motion (ep18 right hand, frames 18–22) and does not see hands outside the view (ep24
  right hand, frames 0–16). Our fill held the first seen pose back to frame 0 → the two robot hands overlapped. Fixed today
  (lead-in from outside + 4 cm hand separation): ep24 0.080 → 0.232.

### 1.4 Learning
- Per-episode RL from scratch; the virtual object controller (VOC: an assist force that moves the object along the
  reference) fades to zero by 123M of 250M steps. Both first runs picked the 150M checkpoint, right after the assist ended: the
  policy learned with help but never learned to take the object over.
- **Rollout noise is large:** one policy, 8 evaluations: 0.13–0.41 vs mocap (std 0.08). A single seed and a single rollout is
  a noisy decision; our no-ground-truth QA (`sim_vs_ref`) correlates 0.98 with the true score.
- Training is blind: logging is disabled, so we cannot see termination causes or reward per curriculum stage.

### 1.5 Objects
- Fixed today: hidden undersides filled solid (pot 5.5 cm, dust pan 3.5 cm under the table); coloured meshes split into
  174 shapes by Newton (training killed for memory).
- Open: our thin board meshes cost ~0.05 in tracking (ep24 0.795 vs 0.843 with the scan). All objects use the kit's
  placeholder mass 0.3 kg.

### 1.6 Process
- GPU end-to-end runs (1.5–2 h, $2–5) were our main debugging tool. CPU replays (`replay_probe.py`, `contact_probe.py` with
  FlashCHORD's exact pins) answer the same questions in minutes for free and should come first.

## 2. Is our approach the only way? No.

The rule (FAQ): object trajectories must come **from learned policies**, with our own reconstructed meshes; any embodiment is
welcome ("including fixed-base arm-and-hand setups and floating hands"). Nothing requires that the policy imitates the human
hand, that the reference comes from kinematic retargeting, or that we use five-finger hands. The scorer only sees the
objects. That opens four families of approaches:
1. **Fix the kinematic route** (what we did today): clean references so RL can learn. Necessary in every family.
2. **Physics-based references** (sim-in-the-loop): generate a robot trajectory that is dynamically feasible and moves the object
   along the perceived trajectory, then train or distil the policy on it.
3. **Object-centric primitives** (the owner's manipulation-type idea): recognise what is happening (grasp-carry-place, slide,
   pour, sweep, lift lid) and build the robot motion from grasps planned on our mesh rather than copied fingers.
4. **A different embodiment** that makes the object task easier for the policy.

## 3. Ideas, ranked by expected value per cost (all hypotheses; each has its falsification test)

**A. Physics preflight gate (do first; CPU, free).** For every reference before any GPU training: (1) contacts at reset — no
hand–hand or hand–object penetration > 2 mm; (2) no-policy replay with stiff wrists — resting objects stay within 2°, wrists
follow within 2 cm; (3) no-policy replay with the real wrists — frames survived before termination. Fail → fix, do not train.
Falsified if references that pass still produce `harmful` policies at the same rate as today.

**B. Robot-geometry-aware retargeting (CPU).** After E2S, compute the Sharpa collision bodies by forward kinematics (Newton,
as in our probes) and remove penetrations at the robot level: per frame, shift the wrist out of objects/table/the other hand
along the contact normal, smooth over time; keep contact (≤ 1 mm gap) where the reference grasps. Falsified if the ep24
reset contacts and the early board drift in the no-policy replay do not drop to ~0.

**C. Manipulation-type detection + primitives (owner's idea; 1–3 days).** We already have per-frame hand–object distances,
object velocities and the table plane, so segments can be labelled without a learned classifier: *at rest*, *approach*,
*grasp-carry* (object moves with a hand in contact), *slide* (object moves, stays on the table), *lift*, *tool use* (object A
moves object B), *release*. Per segment, the robot target is built from the object, not the fingers: a grasp synthesised on
our mesh for the Sharpa hand (or the gripper of idea E), then rigidly carried along the perceived object trajectory; slides
become pushing contacts. The policy is still learned (residual RL on the primitive reference, or behaviour cloning of a
scripted controller then RL fine-tuning), which satisfies "from learned policies". Falsified if ep24 (slide + lift) and ep18
(sweep) policies trained on primitive references stay below their floors.

**D. Physics-based reference generation (SPIDER-style sampling MPC; 2–4 days).** Use the simulator itself to find robot
actions that make the object follow the perceived trajectory (batched rollouts on the GPU, cost = object tracking + contact
guidance + hand prior), then distil into the policy. This attacks the root cause in §1.1 directly: references become
feasible by construction. Literature: SPIDER (arXiv 2511.09484), DexMachina (virtual object controllers + curriculum),
ManipTrans (2503.21860, residual learning on a hand-imitation base). Falsified if the MPC itself cannot move the ep24 board
to its reference on its own; that test needs no policy training.

**E. Embodiment change (rules allow it).**
- *E1, `sharpa_hands_primitive`* (NVIDIA ships it: the same hands with 24 collision primitives per hand; one config line).
  **CPU test done (measured):** ep24 (separated reference), no policy, real soft wrists: board 1 tilts 2° / 5° / 13° at frames
  1 / 5 / 10 (standard hands: 6° / 8° / 20°) and the episode survives to ~frame 20 (standard: ~10); reset penetrations drop
  to one 3.6 mm fingertip. ep18 unchanged (0 contacts at reset, sweeper still). Worth one GPU run on ep24.
- *E2, a floating parallel-jaw gripper per hand* (most out-of-the-box). The scored quantity is the object pose; a pinch grip on
  a board edge, a sweeper handle or a cup rim is far easier to learn than a five-finger grasp, and grasp synthesis on our mesh
  is simple (antipodal points). Needs a new FlashCHORD embodiment (URDF, layout, keypoints) and a MANO → gripper mapping (thumb
  and index midpoint, aperture). **Rule risk:** "floating hands" and "arm-and-hand" are the examples given; a gripper is
  plausibly allowed but we should ask the organisers before investing.
- *E3, Dexmate Vega (fixed-base 7-DoF arms + Sharpa fingers)*: stiff, gravity-compensated wrists, but the mid wrist showed that
  stiffness is not our limit; low priority.

**F. Learning.** Log training metrics (termination cause per stage) so failures are visible; for hard episodes slower VOC decay
and 500M steps; 2–3 seeds per episode with selection by `sim_vs_ref` (no ground truth). Falsified per episode by `qa.py
policy` against the floor.

**G. Rollout selection and "first, do no harm" (owner/organiser decision).** Best-of-N rollouts chosen by `sim_vs_ref` gave
+0.08 on ep18 (measured), but it picks the luckiest stochastic rollout and the organisers may re-run policies. Separately, when
a policy is `harmful` the static floor beats it; a policy trained to keep its hands off objects would score the floor (ep18
0.64 vs 0.40). Both are within the letter of the rules but against their spirit; we should ask before using either.

**H. Thin-object meshes.** Add the public episodes where the boards appear (23, 24, …) to their fusion and evaluate the
flatness and registration; the eval twins use those meshes for tracking.

## 4. What the leaders probably do differently

See §5 (research on the two leading participants, their supervisors and labs; filled in from the research report).

## 6. Recommended next steps (Nov 4 freeze)

1. Preflight gate (A) and robot-level depenetration (B) on CPU; rerun ep18/ep24 only when they pass.
2. Test E1 (`sharpa_hands_primitive`) on CPU, then one GPU run per hard episode.
3. In parallel, get a first full 20-episode submission on the board with the current pipeline (needs a Vast top-up of
   ~$50–70): easy episodes near 0.9 already; it also exercises packing, provenance and upload.
4. Prototype C (manipulation-type segmentation, grasp-carry primitive) on ep24 and ep18; ask the organisers about E2
   (gripper) and G (rollout selection) before building them.
