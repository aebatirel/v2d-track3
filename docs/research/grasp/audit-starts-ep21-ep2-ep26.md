# Root-cause audit: the start-instability episodes ep21, ep2 and ep26 under the grasp-lock recipe

2026-10-24. Analysis only: CPU, no rentals, no commits. Workflow `wf_cdd41283-528` asked one question: are these
failures really grasp failures, and which are not?

Evidence labels:
- **[M]** measured by us from simulator traces, policy rollouts or our reference. No ground truth.
- **[M-GT]** measured with mocap ground truth or the public scans. Diagnostic only, after inference; never used for a
  choice. It is used here to split the score loss and to separate perception error from geometry error.
- **[M-CPU]** a counterfactual zero-action replay that we ran on CPU (FlashCHORD at the evaluator pin, Warp CPU,
  `sharpa_hands_mid` kp 400 embodiment, VOC 0, frame-0 start, terminations off). The CPU replay reproduces the stored GPU
  zero-action traces over the first frames. Example, ep2 lid displacement at f1/f2/f4: CPU 3/8/16 mm, GPU 3/8/15 mm.
  Later frames diverge by a few mm.
- **[C]** checked in code or config. **[L]** literature, opened at the URL given. **[I]** inference.
  **[H]** hypothesis, with the experiment that would falsify it.

Scripts are in `docs/research/grasp/audit-starts-scripts/` (commands in section 7). Downloads, traces and CPU variants
are in the scratchpad: `grasp_work/audit-starts/{data,sim,out}`.

## 0. Answer

| episode (eval twin) | grasp-lock score, registered, 5 evaluations | binding constraint | is it a grasp problem? | fix class |
|---|---|---|---|---|
| **ep21** blue cup + water pitcher (eval 20) | **0.281 ± 0.012** (our reference vs mocap: 0.775) | **The start.** Our pitcher mesh is missing about half of its base. Its centre of mass lies 2.8–4.1 cm outside its support, so it falls over with no hand present (CPU, hands parked: 34 mm / 13° by f4, off the table by f14). The same 30M policy, in the one evaluation where its right hand caught the falling pitcher at f6–9, carried both objects: registered AUC **0.665** (cup 0.921, pitcher 0.409). In 5 of 5 repeats the pitcher was not caught: 0.26–0.30. | **Partly.** At zero action, once the pitcher stands (our base completion, CPU), the copied grasps still fail. The pitcher closure tips it over (f32–50) and the cup slips (lifted 3.3–5.7 of 8.6 cm). The RL fine-tune repaired both grasps in the rollout where the start survived. | **Support-consistent mesh**: complete the base from the observed rim arc, as several convex pieces. CPU: it then stands ≥ 60 frames. Then a designed grasp. Separately, the pitcher's reference itself scores only 0.571 vs mocap (mesh and perception). |
| **ep2** white pot + lid (eval 1) | **0.306 ± 0.115** (reference 0.980) | **The lid grasp.** In all 5 zero-action variants that reach the lid, it is flicked out of the hand at the lift onset (f59–63), whatever its start: the GPU run, the lid raised clear, the GT-relative start with the hands unchanged, the simulator-settled start with the grasp-lock rebuilt, and the GT-relative start with the grasp-lock rebuilt. The start overlap is real: the lid sits 9.6 mm inside the pot's hulls and slides 2.1–2.5 cm / 9–13° in 6–8 frames with no hand. But it costs only 0.042 AUC directly. | **Yes** for the lid. **Partly** for the pot: the left hand lifts it 5–8 cm of 10.6 and it rotates in the hand. In 2 of 5 policy rollouts the pot is carried part of the way (pot AUC 0.63–0.65). | A **designed lid grasp** whose contacts oppose and which does not squeeze before the lift, plus a **hull-consistent seat**. Even at the GT pose the lid stays 7.4 mm inside our pot hulls (CoACD tolerance, note 19): split the pot's rim (RIM33 / S120). |
| **ep26** white pot in the dish rack (eval 28) | **0.383 ± 0.131** (reference 0.923) | **The start.** Our perceived pot sits 29 mm too deep in the rack ([M-GT]), 10.4 mm inside the rack's hulls. With no hand it is ejected and falls out of the rack: 152 mm / 99° by f30 (CPU). At the GT-relative pose it stays within 12 mm / 10° (CPU). The rack, slot 0, also jumps 0.9 cm / 1.7° in the first step in every rollout. `sim_settle` does not help: it settles the pot to its fallen pose, 115 mm / 95°. | **Partly.** With the GT-relative start and the grasp-lock rebuilt on it, the copied handle grasp first touches the pot at f52, tips it at f56–60 and never lifts it (1.2 of 14.8 cm). | **Start-pose consistency for nested objects**: depenetrate the guest out of the host's hulls toward the host's up, then a short assisted settle, and re-certify. Then a **tolerant handle grasp** that closes until contact. |

How much of the loss sits before vs after the first hold. The figures are [M-GT], exact: the ADD-AUC per object is a mean
over frames, so the loss splits additively over frame windows (`cf_window.py`). The figures are in episode-AUC units:

| ep | mean AUC | reference | loss in the frames before each object's first hold | loss from its first hold on | AUC if the pre-hold frames were perfect | AUC if all frames from the first hold were perfect |
|---|---|---|---|---|---|---|
| 21 (r1–r5) | 0.281 | 0.775 | 0.073 (pitcher 0.072, cup 0.001) | 0.64 (pitcher 0.414, cup 0.22–0.25) | 0.31–0.34 | 0.715 |
| 2 (r1–r5) | 0.306 | 0.980 | 0.042 (pot 0.033, lid 0.009) | 0.651 (pot 0.263, lid 0.388) | 0.343 | 0.946 |
| 26 (r1–r5) | 0.383 | 0.923 | pot 0.058; rack (never held) 0.206 over all frames | pot 0.354 | 0.420 (all objects perfect until f42); 0.602 (rack perfect throughout) | 0.709 |

**The pre-hold window holds little of the loss: 6–15% directly. That does not mean the start is harmless.** The start
failure *causes* most of the later loss in ep21 and in ep26: the object is lost before the hand arrives and is never
re-acquired. It does not do so in ep2: the lid grasp fails at f59–63 whatever the start. Section 5 gives the causal
attribution.

## 1. Data and method

| what | where (HF store `aebatirel/v2d-store`) |
|---|---|
| ep21 | `runs/20261024-e2-e49e83d`. Code e49e83d, GL_ARGS `--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 6`, SF=1, REPLAN=1. The re-plan scored 0.297 < 0.357 and was not kept. Trained on `ref_gl_ilc`. Chosen checkpoint 30M. |
| ep2 | `runs/20261024-e3-e49e83d`. Same code and arguments. The re-plan scored 0.144 < 0.185 and was not kept. Chosen 30M. |
| ep26 | `runs/20261024-w1-37cc551`. `--approach_cm 15`. The re-plan scored 0.490 > 0.212 and was **kept**, so training used `ref_gl_r1_ilc`. Chosen 10M. |
| ground truth | `scratchpad/loc/t3/ep{2,21,26}.parquet` (public episodes) and `loc/t3/mesh/*` (public scans). |
| simulator geometry | FlashCHORD's own CoACD hulls of our sim assets. They come from the local FlashCHORD convex cache: the key is computed exactly as `flash_chord/assets/mesh.py` does on the mesh loaded by newton's URDF loader (`hull_key.py`). Cache hits: pot (31 hulls), lid (41), rack (43), cup (74). The pitcher (33 hulls) we built with the same call (`hull_build.py`). The sim assets of these runs are md5-identical to `assets_v3`. |

Tools:
- `start_timeline.py`: per frame, each object's displacement and its error to the reference. Hand proximity uses the
  Sharpa collision-mesh samples on the simulated link poses, measured against the object's hulls. It also reports
  object–object hull penetration.
- `hold_audit.py`: per hold, lift, the share of frames within 3 cm, slip in the palm frame, and hand–hull contact points.
- `wrist_track.py`: the hand against the designed grasp-lock pose.
- `rollouts.py`: the policy rollouts against our reference.
- `geom_audit.py`, `underside.py`, `slices.py`: support and overlap at frame 0.
- `depen6.py`: the GT-consistent relative pose.
- `cf_window.py`: the official-style registered scorer. It uses kit `v2dlb.track3_pose`, as `pipeline/score_registered.py`
  does, with the cup-axis and lid half-turn symmetries.
- CPU counterfactuals: `mkvariant.py` (hands parked 0.6 m up, an object shifted or set to a pose, a URDF swapped),
  `mkfoot_mesh.py` (base completion), and `run_glock_cpu.sh` (grasp_lock → wrist ILC → zero-action replay, with the
  code at e49e83d).

Code facts used:
- [C] `tools/trace_rollout.py zero` records q[0] at reset and then after every step. The evaluator's frame 0 is the
  state after one step, so the policy rollouts' "first-step jump" is that first step.
- [C] The hands do not collide with the table (`robot_support_collision: false`). Note 23 and the sibling audit
  record this too.
- [C] The re-plan (`--sim_trace`) grasps the object where it lay **in the previous zero-action trace**. It does not
  re-plan where the object lies in the new replay.

## 2. ep21: blue cup + water pitcher (pouring)

### 2.1 The start failure (a)
- **Rest check [M]:** the pitcher moves 134.1 mm / 72.7° by f20 (after the re-plan: 146.8 mm / 87.3°). The cup moves
  3.3 mm / 2.1°, a marginal fail on the 2° limit.
- **GPU zero-action timeline [M]:**

  | frame | pitcher | right hand (nearest collision point) |
  |---|---|---|
  | f1 | 2.7 mm / 1.0° | 50 mm away |
  | f2 | 9.5 mm / 3.8° | 45 mm away |
  | f3 | 19.8 mm / 8.3° | 29 mm away |
  | f4 | 34 mm / 13.5° | first touch |
  | f13–14 | lying at about 72°, 127–131 mm off | — |

  The first four frames are identical in `zero_r1`.
- **The pitcher falls by itself [M-CPU].** With both hands parked 0.6 m above the scene, it moves 3 / 9 / 20 / 34 mm
  at f1–4 (13° by f4) and 158 mm / 81° by f8, and leaves the table by f14. The hand contact at f4 in the GPU trace
  accelerates a fall that has already started.
- **Why [M]:** at the reference's frame-0 pose, the pitcher's hull points within 1 mm of the table form a 0.5 × 1.0 cm
  patch, and those within 3 mm a 3.8 × 4.0 cm patch. The COM (the URDF inertial origin, 16.1 cm high) projects
  **2.8–4.1 cm outside** the support polygon. Horizontal slices of our mesh (`slices.py`):

  | height band | our mesh | public scan [M-GT] |
  |---|---|---|
  | 0–7 cm | 10–37 cm² | 57–88 cm² |
  | 8–9 cm and above | 143–208 cm² (the body) | — |

  The observed base is an arc of 160–170° of a circle of radius 3.5 cm (0–2 cm band) to 4.5 cm (2–5 cm band). The
  circle centre is 0.7–1.3 cm from the COM projection.
- **Mesh or pose?** At the mocap-consistent pose of our mesh [M-GT], the COM is still 1.3–2.4 cm outside the support
  and the mesh pokes 8.6 mm below the table. Our perceived pose is tilted 6° from it. So the cause is **the mesh**
  (unobserved lower body), not the perceived pose. The support certificate (`support_fill.py`) already said UNSTABLE:
  no fill up to 2 cm certifies it.
- **Base completion works [M-CPU].** We completed the base from the observed arc (`mkfoot_mesh.py`, no GT: circle fit
  to the 0–2 cm band, r 3.48 cm, a 2 cm-high prism under the table normal). Four variants:

  | foot (hands parked) | result |
  |---|---|
  | one URDF `<cylinder>` primitive | wobbles from f8, about 60° by f30 |
  | one convex 24-gon prism | stands to f16, then falls (151 mm / 63° at f59) |
  | one convex 24-gon prism, r 4.28 cm | falls by f16–20 |
  | **the same prism split into 8 convex sectors** | **stands ≤ 5 mm / 0° for 60 frames** |

  [L1] [I]: MuJoCo's general convex–convex collider makes one contact point per geom pair, which on flat contacts
  "leads to instabilities that typically manifest as sliding or wobbling" (MuJoCo `multiccd` flag). A foot must
  therefore be several convex pieces so that the support polygon is made of several contacts.

### 2.2 Is the grasp also failing? (b, d)
- **The re-plan did not help.** It grasps the pitcher where it lay in the *original* trace at f22 (13.5 cm / 70.7°
  off), but in the new replay the pitcher falls differently (85° by f18). Its zero-action score was 0.297 against 0.357
  before, so it was not kept. The fall is chaotic, so replanning against one trace cannot work [I].
- **Zero action on the run's reference [M]:**
  - **cup:** 0.3 cm off at the hold start, but lifted only 5.1 of 8.6 cm; within 3 cm in 19% of hold frames; slip in
    the palm frame median 2.5 cm, max 4.0 cm / 20°; lost at f98 (f66 after the re-plan). The wrist tracks its designed
    pose (1.2 cm / 0.9°), but the cup in the hand is 2.9 cm / 16° off the design at closing and 4.1 cm / 29° during the
    hold. The cup slips in a correctly placed hand.
  - **pitcher:** 13.6 cm / 72° off at the hold start, never touched (0 contact points).
- **With the start fixed [M-CPU].** We rebuilt the grasp-lock on CPU (code e49e83d) with the 8-sector foot, approach
  6 cm (`glA`) and 15 cm (`glB`):
  - The pitcher stays ≤ 5 mm until f30 in both. The hand does not knock it on the way in.
  - Contrast: the run's GPU-ILC'd reference with the foot swapped in did knock it at f6. That ILC had been fitted in a
    scene where the pitcher was falling.
  - Then the **closure** (hold from f32, fingers closed by f45) pushes the pitcher 28–35 mm by f35, about 66° by f42 and
    over by f50. The hand lifts it in the wrong pose: lift 36.8 cm vs 32.3, within 3 cm 5–7%, mean error 14–67 cm.
  - The **cup** again slips (lost at f43 in `glB`): within 3 cm 10–26%, lift 3.3–4.3 of 8.6 cm.
  - So at zero action both copied grasps fail even with a good start: the pitcher by closure disturbance, the cup by
    slip.
- **Human grasps** [M], from our MANO contact labels:
  - cup: a whole-hand wrap. Palm 0.62 of hold frames, index2 0.92, ring 0.62–0.73, thumb2 0.51.
  - pitcher handle: a fingers-and-thumb handle grasp. Pinky3 0.92, thumb2 0.86, ring2 0.72, palm 0.33.
  - The grasp-lock snapped (copied) both. Neither got a wrap: the PCA ratio is < 3.

### 2.3 Policy rollouts (c) [M]

| | pitcher | cup |
|---|---|---|
| first-step jump | 0.27 cm / 1.0° | 0.05 cm / 0.3° |
| error appears | > 2 cm / 10° at f3 and > 5 cm at f7, in 5 of 5 | > 2 cm at f23–38, > 5 cm at f41–42 (as the reference lift starts at f37) |
| recovery | never | back within 2 cm at f138–158 in 4 of 5 (around the put-down) |
| during its hold | mean error 9.6–60 cm | mean error 6.1–6.7 cm, within 3 cm 18–26% |
| lift | — | 0.3–0.5 cm, against 8.6 |

The cup is **never lifted** in any of the 5 repeats.

**The 30M checkpoint's single curve evaluation is the counter-example.** It is the same policy that was evaluated 5
times:
- the pitcher was > 5 cm off at f6 but **recovered at f9**: the right hand caught it;
- pitcher hold error 1.8 cm / 6.7°, within 3 cm 92%, lifted 31.4 of 32.3 cm;
- cup hold error 0.8 cm, within 3 cm 100%, lifted 8.7 cm;
- registered AUC [M-GT] **0.665** (cup 0.921, pitcher 0.409); sim_vs_ref 0.831.

So **when the start survives, the fine-tuned policy carries both objects**. When it does not, it loses both, the cup
included: one network drives both hands, and a fallen pitcher puts the observation out of distribution [I]. This is the
only rollout of that kind, n = 1.

### 2.4 Score split [M-GT]
- Per object (r1–r5): pitcher AUC 0.029 (it is lost for the whole episode); cup 0.50–0.56.
- Counterfactuals:
  - the pitcher replaced by our reference: 0.53–0.57;
  - the cup replaced: 0.50;
  - every frame from the first hold on: 0.715;
  - the whole reference: 0.775. The pitcher's reference scores only **0.571**; the cup's 0.979.
- So even perfect tracking of our reference caps ep21 at 0.775. The pitcher's reference loses 0.21 on its own: our
  pitcher mesh is incomplete (it registers to the scan with the missing base) and its tracking is weaker.
  Earlier, with the organisers' scan meshes, plain RL scored 0.826 on ep21 (work log, 21 Oct).

### 2.5 Verdict for ep21
**The start is the binding constraint; the grasp is a second, real, but fixable problem.** Evidence:
1. The pitcher falls with no hand.
2. Its mesh, not its pose, is unsupported.
3. The one rollout where the start survived scored 0.665 against 0.28, with the same policy.

Zero action shows that the copied grasps are weak (pitcher closure, cup slip); the RL fine-tune fixed both in that one
rollout. Needed: base completion (support-consistent mesh), then the designed grasps, then better pitcher geometry for
registration.

## 3. ep2: white pot + lid

### 3.1 The start failure (a)
- **Rest check [M]:** lid 31.1 mm / 26.6° by f23; pot 71.1 mm / 12.5°, worst at f64 (window to f102).
- **GPU timeline [M]:**

  | frame | lid | note |
  |---|---|---|
  | f1 | 3.1 mm | |
  | f2 | 7.8 mm | |
  | f4 | 15.4 mm | |
  | f6 | 22.6 mm / 9.3° | |
  | f8 | 25.4 mm / 10.7° | plateau to f19 |
  | f23 | 31 mm / 18.5° | |
  | f27 | — | no hand within 41 mm until here |

  The pot stays ≤ 3 mm until f43.
- **No hands [M-CPU]:** the lid slides 21–25 mm / 9–13° in 6–8 frames and then rests, tilted on the pot. The pot stays
  ≤ 5 mm. So the lid's start failure is intrinsic.
- **Why [M]:** at frame 0 the lid's hull samples are up to **9.6 mm inside the pot's hulls**, 13% of them. Lifting the
  lid straight up needs 24 mm to clear them, because the rim and seat region is filled by hulls.
- **[M-GT]:** at the mocap-consistent relative pose the lid is still **7.4–7.6 mm** inside, 4–7% of samples. Our
  relative pose error is 10.5 mm / 2.9°, the lid 9.5 mm too low. So the hull inflation of CoACD (note 19: lid-in-pot
  union depth 7.5–8.3 mm for the public assets at GT states) is the main cause, and perception adds about half again.
  In the GT-relative variant without hands the lid still drifts 6–15 mm / 2–6° over 80 frames.
- **Settling:** `sim_settle` puts the lid at 20.3 mm / 27.6° from its perceived pose. The lid has no stable pose near
  the observed one on our pot hulls (reproduces the work log's CPU result).

### 3.2 Is the grasp also failing? (b, d): yes, independently of the start
The lid's hold starts at f49 and the reference starts moving the lid at f59. Every variant, zero action:

| variant | lid at hold start | what happens | lost at |
|---|---|---|---|
| run (GPU) | 3.5 cm / 28° | flung | f60 |
| re-plan r1 (GPU) | 6.6 cm / 26° | not acquired | f49 |
| lid raised 24 mm (lands 1.0–1.4 cm / 4–6° off) | 1.8 cm / 3.4° | right hand in contact f45–60, lid **ejected 41 → 117 mm at f62–64** | f63 |
| lid at the GT-relative pose | 2.6 cm / 13° | ejected 62 → 101 mm at f59–63 | f59–63 |
| settled start + grasp-lock rebuilt on it | 0.5 cm / 9.5° | lid jumps 17 → 76 mm at f59–63 and **drags the pot** (77 mm at f63, 221 mm / 75° at f100) | f63 |
| GT-relative start + grasp-lock rebuilt on it (lift onset f62) | 1.4 cm / 6.4° | lid 30 → 53 mm at f59–63, 191 mm at f70; drags the pot (139 mm at f66) | f59–66 |

[M-CPU] for all but the first two. In every case the lid is lost **within ±4 frames of the lift onset**, so it is the
grasp at the moment load is applied, not the start offset. The design is a snapped human grasp: 4 fingers on, grasp gap
2.4 mm, closing thumb 0.2 rad and others 0.025 rad, plus the uniform 0.4 rad squeeze.

Hypothesis on the mechanism [H]: the squeeze closes contacts whose normals do not oppose on a smooth convex lid, so the
lid is squeezed out as soon as the lift loads it.

Human [M], MANO: middle 0.50–0.54, thumb3 0.53, palm 0.50, index1 0.49. A palm-and-fingers grip over the lid, not a
knob pinch.

- **Pot (left hand, handle):**
  - In the GPU run the left hand's approach (from f45) touches the pot at f43–47, 60 frames before its hold, and pushes
    it 1–2 cm. The lid fiasco at f63 then drags it 7 cm.
  - With a clean start (lid raised), the pot is lifted 8.2 of 10.6 cm, rotates in the hand (mean 88°) and is lost at
    f121.
  - It is partly carried by the policy in r1 and r5: within 3 cm 66% in r1; pot AUC 0.63–0.65.
  - The same copied handle grasp reached 0.957–0.972 on ep27 after the fine-tune. The pot grasp is weak at zero action
    but repairable by RL [I].

### 3.3 Policy rollouts (c) [M]

| | lid | pot |
|---|---|---|
| first-step jump | 0.30 cm / 0.7° | 0.10 cm |
| error appears | > 2 cm at **f10** in 5 of 5 (the start slide); > 5 cm at f40–66 (the grasp) | > 2 cm at f39–63; > 5 cm at f57–124 |
| during its hold | 9–25 cm, within 3 cm 0–13% | 4.2–19.7 cm |
| recovery | 1 of 5 (r3 at f276) | — |

The curve checkpoints (10–70M, one evaluation each) all show the lid > 2 cm at f5–9 and > 5 cm at f59–63.

### 3.4 Score split and verdict [M-GT]
- Of the 0.674 lost against the reference (0.980), **0.042 is before the holds and 0.651 is in them**. A perfect
  pre-hold window gives 0.343; perfect hold windows give 0.946. The lid alone, replaced by the reference, gives 0.695.
- **Verdict: a grasp problem first.** The lid grasp fails at the lift onset in every start we tried, and the pot grasp
  is weak. The start (hull overlap) is a secondary, but real, problem: it moves the lid 2–2.5 cm before the grasp, and
  no stable seat exists on our hulls.
- The organisers' scan meshes with plain RL scored 0.926 on ep2 on 20–21 Oct (the left hand took the lid off), so the
  task is solvable.

## 4. ep26: white pot taken out of the dish rack

### 4.1 The start failure (a)
- **Rest check [M]:** pot 117.1 mm / 51.5°, rack 40.2 mm / 44.1° by f37. After the re-plan: 94.4 mm / 55.4° and
  22.0 mm / 24.3°.
- **GPU timeline [M]:**
  - rack: jumps 9.0 mm / 1.7° at f1 (no hand within 45 mm);
  - pot: 4.1 mm / 0.9° at f1, 7.7 mm / 6.3° at f3 (hand 24 mm away);
  - the right hand first touches the pot at f4, while it is already being ejected;
  - pot 80 mm / 43° at f16;
  - at frame 0: pot hull samples 10.4 mm inside the rack's hulls, rack samples 11.5 mm inside the pot's.
- **No hands [M-CPU]:** the pot is ejected and falls out of the rack: 16 mm / 11° at f4, 44 mm / 28° at f12, 122 mm /
  79° at f16, 152 mm / 99° at f30. The rack tilts 22–27° by f30–59. The hand contact at f4 is coincidental, not
  necessary.
- **Pose, not hulls [M-GT]:** at the mocap-consistent relative pose the pot is only **2.5–2.7 mm** inside the rack's
  hulls (0.05–0.1% of samples). Our perceived pot is **29 mm too deep** in the rack and 8.7 mm off sideways (6.1°). Set
  to the GT-relative pose, the pot stays ≤ 12 mm / ≤ 10° for 60 frames with no hands (CPU). The ep26 overlap is a
  perception error amplified by hull overlap.
- **GT-free alternatives [M-CPU]:**
  - Lifting the pot straight up out of the rack hulls needs 37 mm. It then drops into the rack and rests 18–21 mm /
    8–13° off, without being flung.
  - `sim_settle` (VOC hold 20 steps, then 30 free) settles the pot to its fallen pose (115 mm / 95°) and tilts the rack
    27°. Settling accepts the fall.
- **Rack, slot 0:** a first-step jump of 0.9 cm / 1.7° in all 5 rollouts and in all CPU variants, with or without
  hands. It rocks onto its base: perceived tilt 1.4°, lowest point 0.8 mm above the table. Fixing frame 0 alone gains
  only +0.013.

### 4.2 Is the grasp also failing? (b, d)
- **Re-plan r1** (kept for training): it grasps the pot where it lay in the original trace at f32. In the new replay
  the pot again lies elsewhere: 10.0 cm / 62° off at the hold start, 0 contact points, never lifted (5.4 cm). The
  zero-action score rose to 0.490 because the objects ended nearer their references, not because of a grasp.
- **Run reference [M]:** the pot is 9.9 cm / 43° off at the hold start. The hand catches it in the wrong pose: lift 14.9
  of 17.7 cm, within 3 cm 0%.
- **With a near-correct start, three tests [M-CPU]:**

  | start | grasp-lock | result |
  |---|---|---|
  | lifted 37 mm, pot rests 2 cm / 10° off | unchanged | the right hand **never touches** the pot (min gap 17 mm, f42–45); lift −0.4 cm |
  | GT-relative | rebuilt on CPU, approach 15 | pot ≤ 12 mm / 4.5° until f44; first touch at f52; pot **tipped 31 mm / 25° at f56–60**, then left behind; lift 1.2 of 14.8 cm, within 3 cm 16%, contact points median 0 |
  | settled (fallen) | rebuilt | lift 0.3 cm |

  The copied handle grasp (5 fingers on, gap 0.3 mm, closing pinky 0.325 / ring 0.3 rad) has no tolerance and no
  closing-until-contact.
- **Human [M]:** palm 0.60, index1 0.68, pinky3 0.70, thumb 0.45–0.48: a whole-hand handle grasp. The same kind of
  copied grasp worked on ep27 after the RL fine-tune (zero action 0.59 → 0.957–0.972).

### 4.3 Policy rollouts (c) [M]
- **Pot:**
  - first-step jump 0.41 cm / 0.9°;
  - > 2 cm / 10° at **f3** in 5 of 5 (the ejection);
  - > 5 cm at f21–55;
  - during its hold 17–36 cm / 107–135° off, within 3 cm 0–4%;
  - never recovered; lift 3.2–13.3 of 17.7 cm.
- **Rack:** in r4 and r5 it is pushed off from f17–21 (finals 22–33 cm) by the falling pot or the hand. In r1–r3 it ends
  2.0–2.6 cm off.
- The policy is chosen at 10M and the curve is 0.53 / 0.31 / 0.46 / 0.52. The fine-tune never learns to re-acquire the
  pot.

### 4.4 Score split and verdict [M-GT]
- Rack loss 0.206 (r1–r2: 0.13 per object; r3–r5: 0.48–0.69, pushed). Pot pre-hold 0.058, pot from the hold on 0.354.
- Counterfactuals: perfect start window for both objects to f42: 0.420; rack perfect throughout: 0.585; pot perfect
  throughout: 0.741; reference: 0.923.
- **Verdict: the start is binding** (perception-driven nested overlap ejects the pot in every rollout), **and the grasp
  is also weak**: at zero action it never acquires the pot even from the GT-relative start.

## 5. Start versus grasp: causal attribution [I, from the measurements above]

| ep | gap to our reference | removed by a surviving or fixed start | grasp-caused | reference (perception + mesh) below 1.0 |
|---|---|---|---|---|
| 21 | 0.775 − 0.281 = 0.49 | **≈ 0.38** (same policy, start survived: 0.665; n = 1) | ≈ 0.11 left after a surviving start | 0.225 (pitcher reference 0.571) |
| 2 | 0.980 − 0.306 = 0.67 | ≈ 0.04 direct. The lid grasp fails at f59–63 whatever the start, so most of the 0.65 hold loss is grasp | **≈ 0.6** | 0.02 |
| 26 | 0.923 − 0.383 = 0.54 | Unknown under the policy: no rollout survived the start. At zero action the GT-relative start removes the ejection, but the grasp still fails. Both are needed. | not separable yet | 0.08 |

## 6. Fix classes, hypotheses and the experiments that would falsify them

**F1. Support-consistent meshes by base completion** (ep21; also eval 20). It generalises note 25's fill, which stops at
2 cm and cannot certify the pitcher.
- Rule (GT-free): for an object resting on the table whose certificate fails, fit a circle (or the observed convex arc
  mirrored, symmetry prior [L4]) to the lowest observed rim band. Add it as **several convex collision pieces** (8
  sectors) under the table normal. Keep the mass and COM; scoring keeps the library mesh.
- **[H1]** With F1, the eval-20-like start stands until the first hold on the GPU (rest check ≤ 5 mm / 2°), and the ep21
  grasp-lock fine-tune averages ≥ 0.55 over 5 evaluations. That is between 0.28 and the single survived rollout's
  0.665. Falsified if the rest check fails on the GPU (a CPU/GPU contact difference), or the mean stays < 0.4.
- **[H2]** A single convex foot is not enough: the contact is single-point [L1]. Falsified if a one-piece prism foot
  stands ≥ 60 frames on the GPU.
- **[H3]** Completing the base also raises the pitcher reference vs mocap (registration) from 0.571. Falsified if the
  registered reference AUC of the pitcher with the completed mesh is < 0.6.

**F2. Nested start-pose consistency** (ep26; eval 28 and the rack episodes 14/15/16/30).
- Rule (GT-free): if a guest's hull samples are inside a host's hulls at frame 0, move the guest along the host's up
  (or by the minimal rigid motion) until the overlap is ≤ 2 mm. Then settle with the object assist on, and certify with
  a no-hands replay (≤ 5 mm / 2° over 40 frames).
- Measured [M-CPU]: straight-up depenetration keeps the pot in the rack (it is not flung), but the drop leaves it 2 cm
  off. The GT says the truth is 29 mm up, the same direction.
- **[H4]** A depenetrate-then-assisted-settle start keeps ep26's pot within 1.5 cm / 8° of its frame-0 pose until the
  hold (CPU, then GPU). Falsified if it is flung (> 5 cm) or falls out of the rack.
- **[H5]** Note 19's split rack (S120) removes the rest of the overlap. Falsified if the pot-in-rack union depth at our
  perceived pose stays > 5 mm.

**F3. Hull-consistent seats for lid-on-pot** (ep2; eval 1). Note 19 measured, on the scans, a lid-on-pot jolt of 10.6 →
1.7 mm with the pot split into ≤ 120 mm parts (or its rim band, RIM33).
- **[H6]** The pot rim split built from our pot mesh brings the lid's no-hands slide below 5 mm / 2°. Falsified if the
  lid still moves > 1 cm with no hands (CPU replay, about 20 s per variant).

**F4. Designed grasps** for these objects. The three copied grasps fail at zero action even when the start is fine.
- Shared design rule:
  - close until each link touches, as the wrap does;
  - only then squeeze, and raise the squeeze with load, as humans do [L7]: grip force scales with load force at a small
    safety margin and adapts to slips within 60–80 ms;
  - contact normals must oppose about the COM.
- Per object:
  - **lid:** a palm-down rim grasp, the palm on the knob, fingers and thumb on opposite sides of the rim;
  - **pitcher:** a handle power grasp, the fingers through the handle and the thumb on top. A hook alone is
    gravity-dependent and fails when the pitcher is tilted to pour [L6];
  - **cup:** a cylindrical medium wrap around the body;
  - **pot handle:** a power wrap with closure-until-contact. It must tolerate 2 cm / 10° of object offset.
- **[H7]** A designed lid grasp keeps the lid within 2 cm of its path from f59 to f100 at zero action in ≥ 4 of 5
  perturbed CPU replays (1.5 cm / 5°). Falsified if the lid still leaves the hand within 5 frames of the lift onset.
- **[H8]** Closure-until-contact on the ep26 pot handle lifts the pot ≥ 10 cm at zero action from both the GT-relative
  and the depenetrated start. Falsified if contact points stay 0 or the lift is < 5 cm.

**F5. A no-hands start gate before training** (all episodes).
- The slot-0 first-step jump the sibling audit proposed does not catch these failures: 0.05–0.30 cm for ep21 and ep2,
  because the failing object is not slot 0 and the failure unfolds over 3–20 frames.
- Replay 40 frames with the hands parked, about 20 s on CPU. Flag any object moving > 5 mm / 2° before its first hold.
  This separates intrinsic start failures from hand knocks, which `rest_check.py` on the zero-action trace cannot.
- **[H9]** The gate flags ep21, ep2, ep26 and ep31 and passes ep12, ep27 and ep39. Falsified by any miss or false alarm
  on the stored public references.

**What does not work (measured):**
- `REPLAN=1` against a chaotic start (ep21, ep26): it grasps where the object lay in a *different* replay.
- `SETTLE=1` (ep26): it settles to the fallen pose.
- The support fill ≤ 2 cm (ep21): there is no certifiable fill.
- A single convex or cylinder foot.

## 7. Commands (scratchpad venv; `python -I`)

```
start_timeline.py EP zero|zero_r1|<trace.npz> ref_gl_ilc|ref_gl_r1_ilc F_END [EVERY]   # REFDIR=<tree> for CPU rebuilds
hold_audit.py EP <trace> ref_gl_ilc ; wrist_track.py EP zero ref_gl ; rollouts.py EP [curve]
geom_audit.py EP ; underside.py 21 water_pitcher ; slices.py 21 water_pitcher 16
SKIP_MIN=1 depen6.py 26 white_pot plastic_dish_rack ; depen6.py 2 white_pot_lid white_pot      # [GT] relative pose
cf_window.py EP [zero] ; cf_one.py 21 <curve rollout parquet> ; cf_summary.py out/cf_window_ep*.json   # [GT]
mkvariant.py EP ref_gl_ilc NAME nohands|urdf:OBJ:URDF|setpose:OBJ:JSON:KEY|depen:OBJ:HOST ; run_sims.sh EP:NAME:FRAMES ...
NSEC=8 mkfoot_mesh.py 21 water_pitcher OUTDIR 0.02 1.0 0.02 ; localise.py EP TREE [OBJ=URDF] ; setstart.py TREE OBJ JSON KEY MOVE
run_glock_cpu.sh TREE NAME "<GL_ARGS>" ; run_settle_glock.sh EP NAME "<GL_ARGS>"
hull_key.py <fc src> assets_v3 <fc cache> OUT obj... ; hull_build.py <fc src> assets_v3 CACHE OUT water_pitcher
```

CPU cost: each zero-action replay takes 15 s (30 frames) to about 2 min (343 frames). A grasp-lock rebuild with 4 ILC
iterations takes 5–10 min on one loaded core.

## Sources

- [L1] MuJoCo XML reference, `option/flag/multiccd`: "the single contact point generated by the convex-convex collider
  cannot accurately capture the surface contact, leading to instabilities that typically manifest as sliding or
  wobbling". The same page: each constraint "behaves approximately as a damped second-order system whose time constant
  and damping ratio are set by the solref". https://raw.githubusercontent.com/google-deepmind/mujoco/main/doc/XMLreference.rst
  (opened; the readthedocs host was unreachable from this session).
- [L2] MuJoCo computation chapter: the reference acceleration is a spring–damper on the constraint residual ("similar
  in spirit to Baumgarte stabilization"); "non-convex meshes are replaced with their convex hulls".
  https://raw.githubusercontent.com/google-deepmind/mujoco/main/doc/computation/index.rst (opened). [I] So an initial
  interpenetration is pushed out over a few time constants: the lid's 9.6 mm overlap becomes a 2.5 cm slide in 6–8
  frames.
- [L3] Wei, Liu, Mu, Liu, Su, "Approximate Convex Decomposition for 3D Meshes with Collision-Aware Concavity and Tree
  Search" (CoACD), SIGGRAPH 2022. https://arxiv.org/abs/2205.02961 (abstract opened). Hulls approximate the part within
  a concavity threshold; note 19 measured our consequence (0.025 × L per mesh handed in).
- [L4] Bohg et al., "Mind the Gap – Robotic Grasping under Incomplete Observation", ICRA 2011, 686–693,
  doi:10.1109/ICRA.2011.5980354. Abstract via OpenAlex (https://api.openalex.org/works/doi:10.1109/ICRA.2011.5980354)
  and the authors' code https://github.com/jbohg/mirror_objects (README opened). They complete unseen object parts from
  a fitted symmetry before grasp planning in simulation, which is the prior behind F1.
- [L5] Zeybek, Newbury, Dikhale, Jamali, Iba, Cosgun, "Geometrically Plausible Object Pose Refinement using
  Differentiable Simulation", arXiv 2603.20992 (2026). https://arxiv.org/abs/2603.20992 (abstract opened). Pose
  estimates "often intersect with the robotic hand or are not lying on a support surface"; refining with differentiable
  physics cuts intersection volume by 73–87% and also reduces translation and orientation error. That is the same
  direction as F2: our ep26 pot is 29 mm too deep, and correcting the overlap moves it toward the truth.
- [L6] Feix, Romero, Schmiedmayer, Dollar, Kragic, "The GRASP Taxonomy of Human Grasp Types", IEEE THMS 46(1):66–77,
  2016. https://www.eng.yale.edu/grablab/pubs/Feix_THMS2016.pdf (PDF opened). The hook grasp is excluded as
  gravity-dependent ("If one turns the hand, the object may fall down"); 33 prehensile types.
- [L7] Johansson, Westling, "Roles of glabrous skin receptors and sensorimotor memory in automatic control of precision
  grip when lifting rougher or more slippery objects", Exp Brain Res 56:550–564, 1984. PubMed 6499981 (abstract opened
  via NCBI E-utilities, https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=6499981&rettype=abstract).
  Grip force changes in parallel with load force at a small, friction-adapted safety margin; slip-triggered adjustments
  follow in 0.06–0.08 s.
- [L8] Napier, "The prehensile movements of the human hand", J Bone Joint Surg Br 38-B:902–913, 1956. PubMed 13376678.
  Only the metadata was opened (no abstract online); it is cited only for the power/precision distinction.
- Could not be opened: Strecke & Stückler, "Physically Plausible Object Pose Refinement in Cluttered Scenes" (GCPR 2024);
  the host was refused by the session proxy. It is not cited for any claim.
- In-repo: notes 19 (hulls), 23, 24, 25 (support certificate), `docs/work-log.md` 23–24 Oct, and the sibling audit
  `docs/research/grasp/audit-boards-ep24-sweeper-rack-ep31.md` (slot-0 jump, first-step recording).
