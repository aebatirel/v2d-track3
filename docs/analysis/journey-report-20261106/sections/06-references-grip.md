## 6. References, contacts and grip

The **reference** is the target the RL policy follows: per-frame object poses from perception plus robot-hand wrist and finger targets retargeted from the perceived human hands, written by `mkref` into a parquet. This section covers how references were built and repaired, and how grasps were made. Policy training itself is in section 7.

### 6.1 Building references

| Step | What it does | Measured effect |
|---|---|---|
| Table plane fit | sequential RANSAC, nearest plane under the objects, abort guard (fix 30d3633, 20 Oct) | the first end-to-end ep12 score was 0.009 because one RANSAC picked the floor (55 % of points) over the table (39 %); a static-floor sanity check caught it |
| Contact-anchored retargeting (stage 3c, 21 Oct, CPU) | snap fingertips to object contacts, let the wrist follow (owner: "snap the fingertips, let the wrist follow") | ep24 dirty frames 242 of 275 -> 62; penetration p95 20.1 -> 6.0 mm; start pop 8.6 -> 2.9 degrees; ep18 p95 16 -> 2.7 mm. Adopted |
| Hand separation at reset | stop the two robot hands interpenetrating (-6 to -14 mm) | removed the pop of board 1 but did not raise the score (0.231, at the floor) |
| Support fill and arc foot | make resting objects stand: centre of mass inside the support polygon with margin of at least 3 mm and tilt of at least 3 degrees | pitcher arc foot: ep21 0.6565 -> 0.7723 (adopted, pack 3); eval 19 sweeper settle 90.2 mm / 88.8 degrees (16 of 16 falls) -> 0.01 mm, certified but not retrained; eval 20 b1 clip 195 mm / 94.6 degrees -> 8.5 mm / 3.2 degrees |
| Onset anchor | start the grasp when the object starts moving, not when the human hand label says | ep18 sweeper grasp moved from frame 53 to 29; part of the ep18 jump to 0.957 |
| TRACK_GUARD and guard_bridge | repair implausible tracks in the reference (section 5) | eval 14 fails 4/10 -> 1/10 |
| Half-frame advance S2 | shift poses half a frame earlier to remove the measured 25-28 ms delay | +0.0061 public; never wired into a packed eval reference |

Known reference faults found later: mkref's per-object table snap (plus or minus 2 cm) is wrong for objects resting on other objects (pot in rack, lid on pot, cup in rack); the onset anchor counted a cup's spin about its own axis instead of its swing; resting objects that drift in our tracks fire the anchor early; and several job scripts kept stale library defaults (v1 or v2). A gated table snap was proposed as a $0 CPU test on 27 Oct and never decided.

### 6.2 The contact-slot label bug (25 Oct)

`mkref` fills 16 contact slots in PROBE_SITES order (5 tips, 5 distal pads, thumb MCP, four MP sites, palm mean in slot 15), but the parquet's `mano_link_names` column is in MANO order. Four analysis scripts and two plot tools read the wrong labels, so "palm" was really the thumb tip. FlashCHORD never reads that column, so training was not affected. On the owner's choice ("New column (Recommended)") a `contact_slot_names` column was added, 10 tests pass (including a kit round trip on ep12), and the old tables were first reproduced byte for byte and then corrected as dated additions. Corrections: ep2 lid palm 0.76-0.80 -> 0.00; pitcher palm 0.33 -> 0.92 (a palm power grasp); pot handle reading reversed; plate thumb-finger opposition 0.38-0.69 -> 0.05-0.22. Earlier design claims about "the human's clamp" and "palm on the knob" lost their human-contact basis and now rest on mechanics only. A separate friction calculation had the same index-order problem (pitcher palm share 0.93, not 39 %).

### 6.3 Grasp research and audits (24-25 Oct, CPU)

Audits of the failing public episodes showed that **reference construction caused more failures than grasp design**:

| Episode | Finding | Class |
|---|---|---|
| ep39 dust pan (0.174) | a carrier merge deleted the left-hand pick-up; the pan rises at f51 while the retargeted hand is 48-51 cm away | reference building |
| ep18 sweeper | no human contact until f60 | hold timing |
| ep18 dust pan (0.302) | no opposition, thumb 20 mm off, closing flicks the pan 63-80 mm | grasp |
| ep24 boards (0.202) | 0 of 5 rollouts lift board 1; following the reference would give 0.803 | grasp (needs a designed clamp) |
| ep31 sweeper in rack (0.767) | the first control step ejects the sweeper from the rack hulls (11.3 degrees / 1.07 cm); fixing that one frame gives 0.840 | start and collision geometry |
| ep21 pitcher (0.281) | the mesh misses half its base and falls with no hand | mesh |
| ep2 lid (0.306) | flicked out at lift onset (f59-63) in all 5 variants | grasp |
| ep26 pot (0.383) | perceived pot 29 mm too deep, ejected 152 mm by f30 | perception |

What the successful RL policy found on ep18 (0.889): a lateral key pinch on the dust pan with thumb and index touching in the same frame (f16, pan moved at most 2.9 mm before lift), and a neck-and-head clamp on the sweeper. Lesson: copy the contact roles and timing relative to the object, not the human wrist path (the policy's wrist was 14 cm / 38 degrees away from the human's).

Other grasp studies:

- **Grasp taxonomy classifier:** opposition of at least 110 degrees in half the frames in only 5 of 40 holds; 14 of 17 grasp failures sat at phase boundaries [I]. Classifier rejected; event timing, not grip type, is the bottleneck.
- **CMA-ES grasp edit** (28 parameters): ep39 0.176 -> 0.877 zero-action sim_vs_ref using 40,640 world-steps (about 14 min on 4 CPUs), vs 0.826 for standard RL. But a MuJoCo-Warp warm-start state survived `env.reset`, so early searches picked lucky trajectories (jitter of 1e-5 moved a best score to 0.18-0.44); fixed by a fresh environment per generation.
- **Zero action vs fine-tune:** across 18 grasp-lock runs, Spearman 0.73 (p 0.0007); zero-action at least 0.5 ended at 0.73 or more (8/8), below 0.36 ended at 0.43 or less (10/10). Fine-tuning finishes a working reference but does not rescue a broken one.
- **Grip portfolio on ep24 board** (CVaR 25 %): copy 0.321, clamp_long 0.297, clamp_short 0.475, platform 0.392; never tested on GPU. Event-anchored windows T2 failed (ep24 0.160 -> 0.058).
- **Required forces** (friction LP, 0.3 kg, safety factor 1.5): dust pan 5.0-7.8 N per contact; sweeper neck 1.4-3.7 N; boards 3.0-9.5 N; pitcher 3.3-5.3 N; lid side pinch 6.2-15.2 N.
- **Learned grasp models** (literature): GraspGen supports three grippers only; GraspGen-X zero-shot on another hand 0.363; DexGraspNet 2.0 non-commercial; usable at most as seeds.

### 6.4 Non-RL grasping and the spoon

The spoon was the hardest object to hold: zero action does not grip, pinch locks lift at most 1.7 cm, and the spoon rolls up to 72 degrees in hand with the default wrist (63 with kp 400).

| Step (eval 3 / eval 35, scored against our own reference) | Result |
|---|---|
| Plain RL, 250M | at most 0.41; eval 3 0.380 (floor 0.439) |
| Wrap grasp + ILC (owner: "wrap the hand around the handle, that's the strongest grasp") | eval 3 zero action 0.462 |
| Wrap with a kp 400 wrist | 0.658; spoon within 3 cm in 87.5 % of frames vs 16.9 %; 8 of 8 hold trials at 1.5 cm / 5 degree disturbance |
| Anatomy closing rule (MCP first, 10-frame close, palm press) | eval 35 0.521 vs 0.150-0.267; but eval 3 fell to 0.429-0.454 |
| RL fine-tune on the kp 400 wrap reference | eval 3 70M 0.981, five repeats 0.968 (sd 0.020, min 0.928); eval 35 40M 0.979, five repeats 0.978 (sd 0.002) |

Two integrity notes: these rules were developed on eval episodes 3 and 35 using our own GT-free reference (no ground truth and no board feedback), and the note itself asked for public-episode confirmation, which was never done; and the kp 400 wrist was "owner to confirm before any submission uses it", with no confirmation recorded. The FAQ says "Other embodiments are welcome", but this is a disclosure item for the technical report.

More from the early chat (22-23 Oct) on how the spoon recipe was reached:

- **The recipe in four parts:** (1) build the grip from video (wrap the hand round the handle, knuckles first, thumb last, palm pressing); (2) lock the hand while the spoon is carried and correct wrist lag; (3) the stiffer-wrist setting; (4) an RL fine-tune of 40-70M steps (11-19 minutes on one GPU). Means of five official runs against our own reconstruction: eval 3 (spoon and pot) do nothing 0.439, RL alone 0.38-0.41, new recipe 0.968; eval 35 (spoon) do nothing 0.112, RL alone 0.29-0.34, new recipe 0.978 [M, own reference, not mocap]. Seed 43 reproduced eval 35 (0.971 at 30M, 0.973 at 40M); eval 3 seed 43 reached only 0.843 at 40M because the pot, held by a copied grip, was within 3 cm in 54 % of frames. The rule adopted: train 70M steps, re-run each candidate several times, keep the best by the agent's own reconstruction score.
- **Why RL alone failed:** pick-up appears only at about 90M steps, and from 100M to 250M the spoon drops at the same frame in every checkpoint (frames 141-147 in eval 35, 105-109 in eval 3). About 370 grip variants in the evaluator's physics held nothing; a pot grasp-lock with lag correction lifted the pot with no policy (6 cm against the reference's 8.3 cm), the spoon did not.
- **Dead ends the same day:** opening fingertips before the knuckles kept the spoon within 2 mm but pulling away dragged it (0.150 against 0.267 for the same grip, replayed three times); a 25-degree angled grip 0.093; the anatomy rule lifted eval 35 (about 0.18 -> 0.52) but cost eval 3 (0.658 -> 0.429) and was rejected for it.
- **The organisers' kit (research note 23, 23 Oct):** other embodiments are allowed (FlashCHORD ships a simpler-collision Sharpa, a stiffer-wrist Sharpa, an arm plus Sharpa and a three-finger hand); no official Sharpa grasp library exists (BODex and Dexonomy could be adapted in one to two days); anything magnetic must be gone by evaluation (training uses a fading helper force); holding from below is physically right and the wrap does it.
- **Hand placement (21 Oct):** the CPU-tested hand-placement fix cut frames with the robot hand more than 2 mm inside something from 242 of 275 to 62 (ep24) and from about 77 % to 41 of 361 frames (ep18). The "fixed hand reference" cost ep27 (0.942 -> 0.911) and the primitive hand was mixed (ep18 0.377 +/- 0.021 against base 0.345; ep24 slightly below), so neither became default.
- **Official material vs our reading (22 Oct):** the whole object motion is fed to the policy and the robot is allowed corrections of +/-5 cm and +/-0.15 rad around the human motion. A competing method, FlashDexRetarget (arXiv 2610.01849, authors' numbers 86 % success on this hand against 50 % for NVIDIA's retargeter), inspired our FDR rewards; its numbers were not reproduced, and each of its changes needs training from scratch.

### 6.5 Grasp locks, carry and hand-overs

- `grasp_lock.py` keeps one carrier hand. On public ep13 the reference parked the left hand at z = 57.0 cm for all 190 frames while the cup rose 9-12 cm. Eval 14's packed reference was also single-hand, while the human hands over at about f40-46: exactly the measured failure onset (f42-45 in 7 of 10 draws). So "control-limited" may have been "construction-limited" [I].
- The **lane finding** that the grasp-lock "fine-tune" is a fresh 70M run on a reference that already carries the object, which ends before the training assist is fully off, so those policies never train under the exact scoring conditions [H].
- Hand-held repairs that passed: eval 16's right hand kept on the spoon through release (+0.124) and the guard bridge on evals 14 and 32 (section 7). Two-hand references and a first-picker lock did not transfer to eval.
- **Lift-window resets** (training starts sampled around the grasp and lift windows) passed on eval 20 and, by owner waiver, eval 15; 1 of 8 eval tries passed on its own merits.
- **Carry-aware ideas** (note 26): the kp 25 N/m wrist has a natural frequency of about 0.64 Hz with an object and saturates on 23 of 27 moving public tracks; kp of 100 or more removed saturation in reruns; an 18 mm contact threshold can mislabel a carry as "no contact"; a 16-30 run wrist-gain study ($35-100) was planned and never approved. Restricting the wrist residual during holds (DexMachina-style) was never tested. From the builder chat (27 Oct) [E, CPU model]: median hand error while carrying and hand jump after release were 11.9 cm and 1.4 cm for the default PD, 3.7 cm and 0.5 cm for kp 100, 8-9 cm and 11-14 cm for a PID on the soft wrist, and 0.6 cm and 0.2 cm for feed-forward. PID was rejected (unstable at strong gain, slow grip build-up, pushes after release). A dropped object costs about 0.3-0.6 AUC on its episode, roughly 0.015-0.03 on the 20-episode mean; a lag of 0.2 s costs about 0.07 AUC and 0.3 s about 0.11. Rule: keep kp 100 only if it wins on at least 3 of 4 episodes. The soft wrist is 12-14 times softer than DexMachina's (300-350 N/m) and 40 times softer than SPIDER's.
- **Hands in replay:** moving hands knock resting objects (eval 5 pot 25.7 vs 3.3 mm parked; eval 8 pot 41.7 vs 8.9 mm; eval 33 spoon 87.0 vs 10.6 mm), but these episodes already scored 0.94-0.97, so no rebuild.
