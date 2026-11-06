## 3. The task and the scorer: what we learned

### 3.1 The task in one paragraph

Each episode is a short head-mounted stereo video of a person handling one or two kitchen objects (pots, cups, a lid, a pitcher, a dish rack, a sweeper, a dust pan, two wooden boards, a wooden spoon). We must (1) reconstruct each object's mesh, (2) estimate each object's 6-DoF trajectory from the video, and (3) train a simulated robot hand pair to make the simulated objects follow that trajectory. Kaggle scores the robot's simulated object motion against hidden motion-capture (mocap) ground truth, and scores our meshes against hidden scans. There are 20 public episodes with mocap and scans (for development) and 20 eval episodes without them (for the board). The public set has 5,246 frames (mean 262 per episode) at 20.25 fps, 10 tasks and 10 object types; 13 of the 20 public episodes have two objects. Public mocap holds object poses only: no hands, no camera.

### 3.2 How the six boards work

| Board | What it measures | Notes we measured |
|---|---|---|
| AUC | per frame and object, the ADD error after registration and frame-0 alignment, mapped to a score: 1.0 below 1 cm, minus 0.125 per further cm, 0 at 9 cm; averaged over frames, then objects, then a plain mean over the 20 episodes | symmetric objects are handled (cups any spin; lid 0 or 180 degrees). A 1.5 cm track error costs about 0.06 AUC per object [E] |
| SP-SR | share of episodes where the mean position error is at most 10 cm and the mean orientation error at most 0.5 rad | one episode = 0.05 |
| MP-SR | share of episodes where every object stays under 3 cm and 30 degrees | one episode = 0.05 |
| RPE (cm) | mean over object pairs of the second object's position in the first object's body frame; 0 for single-object episodes; plain mean over episodes | unbounded: one failed rollout dominates |
| MPPE (cm) | mean per-object position error | unbounded |
| CD-O (cm) | Chamfer distance after a Sim(3) fit (scale from area-weighted RMS radii) between our mesh and the hidden scan; a flat mean over 36 (episode, object) pairs | 10 of the 36 pairs are the spoon, which has no public scan |

The final rank is the **sum of the six board ranks** (FAQ). An early research note (6 Oct) assumed AUC alone ranked teams; the first rank-sum check came only on 31 Oct (section 4). Each board keeps a team's best (or selected) submission, so a variant that is worse on five boards and better on one costs nothing. Rank arithmetic (coordinator, 2 Nov): each board ranks us separately and the sum decides, so one more SP-SR episode was worth about 4 rank points while five teams stood at 1.00. Two scores must not be confused: our "own score" (sim_vs_ref, mean of 10 official runs against our own reference, about 0.94 on average at the end) measures how well the robot follows our reference, while the board scores one stored run against real motion, so a high own score does not guarantee a high board score. The scorer also aligns the whole scene once at frame 0, using the first object without a symmetry axis, and fits our submitted mesh onto its scan of the real object, so the submitted mesh changes the pose scores and not only CD-O.

**Two "lotteries" inside the scorer** (robustness review, 26-27 Oct):

1. **Frame-0 alignment.** The kit aligns the whole achieved scene once, at frame 0: rotation from the first object without a symmetry axis, translation from slot 0. Any anchor error reaches every object and every frame, while RPE is blind to such common-mode error. Our frame 0 is the noisiest frame (FoundationPose register: 1.07 degrees median against about 0.5 later), and in rollouts frame 0 is recorded after the first control step. A slot-0 mesh offset (the blue cup, about 1 cm along its axis) moves every object.
2. **Mesh registration.** Since about 21 Oct the kit registers our submitted mesh to the hidden scan (`_register_object_body`: centroid and RMS normalisation, trimmed ICP from 25 starts, seed 1,000,003 x episode + 101 x slot) and converts our poses through it. So mesh shape is a first-order term of every pose board. Measured on 6 public episodes: clean scan 0.987, x1.10 scale 0.987 (scale is free), convex hull 0.947, bottom 20 % removed 0.904, 3 mm noise 0.825, 5 mm inflation 0.608 (wooden piece and sweeper flipped 180 degrees). Even the stable library pitcher spans 0.667-0.833 AUC across 30 registration seeds.

### 3.3 What the scorer rewards (measured)

- **Continuity beats precision** (note 02, public mocap perturbed and scored with the kit, 8 seeds per case): static predictor AUC 0.446 / SP 0.45 / MP 0.00 / RPE 10.87 cm / MPPE 9.31 cm; losing the most-moving object 0.550; 5 cm drift 0.799; slot-0 start 3 cm off 0.740; 10 degree cup spin on a cup anchor 0.714 (30 degrees: 0.279); lag about 1 % AUC per frame; scale errors under 5 % matter little.
- **Pose, not shape, separates teams.** Across teams on 25 Oct, AUC correlated with MPPE at Spearman -0.97 (n 18), RPE -0.93, MP-SR +0.93, SP-SR +0.90, and CD-O only -0.51 (n 16). The CD-O leader then was 17th on AUC. But our own mesh was a pose lever through registration (section 8).
- **Failures dominate the unbounded boards.** On public data, successful draws have RPE 1.4-3.5 cm and failed draws 10-77 cm. Over 70 public draws the reference itself is only about 10 % of RPE and 16 % of MPPE [D].
- **Board leverage on 2 Nov** [M from the board]: one more SP-SR success (0.90 -> 0.95) would have moved SP-SR from 10th to 6th; MP-SR 0.85 -> 6th; RPE -0.05 cm -> 8th; CD-O -0.0144 cm -> 5th.
- **Timing is a silent killer.** NVIDIA's default `motion_speed` 0.5 makes the packer keep source frame about 0.508 x f in row f. With perfect perception and robot, that alone caps public AUC at 0.415 (SP 0.30, MP 0.00), below the do-nothing floor of 0.446 [C, 30 Oct]. We trained at real speed.
- **What Kaggle does not do:** nothing is re-run (kit `AUC.py`); submitted draws are banked. Results stay provisional until the organisers' container reproduces each counted file (PR #215: `run.sh reproduce`, policy weights for every sequence, matching hashes, a score "within your own run-to-run variation"). The sponsor also runs a held-out evaluation after close on undistributed data, so per-episode hand fixes would not carry over.

### 3.4 What sim_vs_ref can and cannot see

sim_vs_ref scores a rollout against our own reference with the kit's plain ADD. It is GT-free, so it is the only number available on eval episodes.

- **It works for ranking policies on the same reference.** On 27 stored public policies it correlated 0.997 with the registered AUC against mocap (mean difference 0.021); pairs 0.02 or more apart were ranked correctly 63 of 63 times. GT-free RPE against our reference tracked RPE against mocap at r = 0.9998 over 70 public draws.
- **It cannot see a wrong reference.** Pack 1 followed our references at 0.710 and scored 0.575. A swapped board identity on eval 25 scores near zero whatever the robot does. The 3 Nov SR audit showed all 20 14p rollouts pass SP-SR and MP-SR against our references while the board shows 2 SP-SR and 4 MP-SR failures.
- **It cannot rank small differences.** Pack 9b's +0.0018 proxy gain became -0.0008 on the board. A proxy difference of about 0.02 on one episode carries no sign information about the board [I].
- **It charges cup twist that the board ignores** (symmetric minus plain sim_vs_ref at most +0.009 everywhere, so spin is not where losses are).
- **The loss model is not linear.** "True AUC about 0.979 x sim_vs_ref" holds only where the reference itself scores about 0.93 or more; at high sim_vs_ref, true is about 1.025 x S x R. Only about 74-76 % of the pack 3 -> 4 gain reached the board.

### 3.5 Loss budgets measured over time

| Date and pack | Board AUC | Our sim_vs_ref | Loss split |
|---|---|---|---|
| 24 Oct, pack 1 | 0.575 | 0.710 | reference vs truth about 0.135 [M]; by cause: mesh about 0.08, perception about 0.09 (objects lost to the wrist), grasps about 0.11-0.13, objects that cannot stand about 0.09 [E] |
| 26 Oct, pack 3 | 0.789 | 0.883 | policy 0.117 [M]; reference, anchor and mesh about 0.075 [derived] |
| 26 Oct, pack 4 | 0.8106 | 0.9121 | total loss 0.189: policy 0.088, reference about 0.10 [E]; draw luck +0.027 in our favour; implied hidden loss about 0.082 |
| 30 Oct, pack 7 | 0.8146 | 0.911 (GT-free audit) | policy 0.083 [M]; reference about 0.10 [E], of which spoon about 0.06-0.07 [E] |
| 31 Oct, pack 7 | - | RPE vs own reference 2.45 cm vs board 3.93 cm | about 1.5 cm of board RPE is reference or registration [E]; eval 10 alone 0.79 cm of the mean |
| 3 Nov, pack 14p | 0.88571 | all 20 pass SR vs own reference | remaining SR failures are reference vs truth, about 2-3 cm [I] |

The spoon estimate moved over time: an inferred 0.12 spoon gap (24 Oct) was later judged overstated and replaced by a start-roll effect of 0.03-0.15 per spoon-anchored episode [E], while the robustness review found the implied spoon accuracy sensitive to the loss-model scale (0.80 -> 0.73-0.76). This is a real conflict in the sources; the spoon was never measurable.

### 3.6 Facts about the data

- **Objects and weights** (eval roster): wooden spoon 32.5 %, white pot 15 %, blue cup 12.5 %, dish rack 12.5 %, dust pan 7.5 %, beige cup 5 %, sweeper 5 %, lid, pitcher and the two wooden pieces 2.5 % each.
- **The spoon** is in 10 of 20 eval episodes and anchors the scene in five (evals 32, 33, 35, 36, 37). It has no public scan and no public mocap. A 10 degree roll error on an anchor costs 0.09-0.28 AUC on those episodes (eval 32's ratio drops to 0.72; 20 degrees: 0.34). Its frame sign stayed unresolved: P(frame B) estimates ranged from 0.09 to 0.87 across notes. Observed length 30.0-30.7 cm vs template 30.7-31.0 cm; 0 registration flips in 300 fits.
- **Symmetric and look-alike objects.** Cups are featureless: spin is visible only through mocap markers (beige cup with two markers flips in 21-28 of 40 frames). The two wooden boards are look-alikes that appearance-based detection names almost at random; a swap alone drops a 0.795 track to 0.057. The rack's marker spacing (153.5 mm) matches the spoon's (154.3 mm). Flat near-symmetric objects flip during registration.
- **Camera timing.** Cameras b and c are hardware-synchronous (-0.01 +/- 0.09 ms, 39 clips); camera a pairs a[k+1] with b[k] in 36 of 39 clips; rolling shutter is 31.6 ms per image height. `capture_time` steps average 50.0 ms with sd 1.0-4.3 ms per episode. Mocap row k sits about 25 ms after camera frame k, and our perceived paths are 25-28 ms (about half a frame) late.
- **Eval scenes** have a seated second person at the left edge of 19-20 of 20 clips, and the wearer has a white smartwatch on the left wrist; cups and the sweeper latched onto the wrist in evals 30, 14, 32 and 33. Evals 20 and 32 have no still window before contact; eval 20 starts with a cup in mid-air. No public episode starts with an object in hand or has a spoon in a cup.
- **The camera sees only 60-90 degrees of azimuth** around an object, so the far side of the pitcher is never observed; our pitcher mesh lacks about half its base, which causes a stable 6.1-6.3 degree tilt (ep21/22), 3-3.4 cm over the MP-SR limit. Three lanes found this independently.
- **Physical properties** are unknown: every object was a 0.3 kg placeholder (plausible: cup 128 g, lid 88 g, dust pan 44 g), friction is one global 1.0, and the real boards are 8.5 mm thick against 2.7-3.1 cm in our meshes.
