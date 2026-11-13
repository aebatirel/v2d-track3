## 7. Robot movement: policies, training and following

The robot is a simulated dexterous hand pair (the kit's Sharpa embodiment) in MuJoCo-Warp. For each eval episode we train a policy with reinforcement learning (RL) to make the simulated objects follow our reference (section 6). Kaggle scores the submitted rollouts as they are; nothing is re-run.

Two measures appear everywhere in this section:

- **sim_vs_ref**: how well a rollout follows our own reference (plain ADD-AUC, no ground truth). It is GT-free, so it can be used on eval episodes. On 27 stored public policies it correlated 0.997 with the registered AUC against mocap (mean difference 0.021), and pairs that differed by 0.02 or more were ranked correctly 63 of 63 times [D]. It cannot see a wrong reference, and it charges cup twist that the board ignores.
- **Draws**: one official evaluation of a checkpoint is one draw. Draws of the same checkpoint differ a lot (section 10).

### 7.1 Simulator and evaluator facts that shaped the work

| Fact | Consequence |
|---|---|
| 20 fps x 5 substeps, friction 1.0 for everything, finger kp 1.7 Nm/rad, wrist kp 25 N/m; every object 0.3 kg placeholder | grip and carry depend on contact geometry more than on mass |
| Training resets hold the reference for 20 steps with the virtual object controller (VOC) at 1.0 and random finger scaling U(0, 0.7); the evaluator starts at frame 0 with exact fingers, VOC 0, no hold | a train/eval start mismatch; opt-in fix `FC_IMMEDIATE_FIRST_FRAME=0.25` |
| Termination at wrist error 0.15 m, object 0.10 m or 0.50 rad | a dropped object ends the rollout |
| The policy sees contact points and force directions (no magnitudes), no look-ahead, no object velocity | adding object velocity (arm V) was tested: -0.024 |
| Hands pass through the table | references with hands below the table are not penalised physically |
| Contact buffer njmax 512 / nconmax 256 per world (NVIDIA's own recipe uses 1024); the evaluator inherits the checkpoint config | the eval 10 floor (7.5) |
| Default soft wrist saturates on 23 of 27 moving public tracks (5.8 % of moving frames); PD kp 100 carry error 3.7 cm vs 11.9 cm | the FAQ says "other embodiments are welcome"; a kp 400 wrist was used for the spoon work, pending owner confirmation for submission |

### 7.2 Learners and recipes

| Learner / recipe | What it is | Measured result |
|---|---|---|
| Standard RL (FlashCHORD `sharpa_flash_sac`, 250M steps) | the kit's RL recipe | Colab smoke: about 45,300 env steps/s on 4,096 worlds, 40.5 GB. First valid ep12 run (20 Oct): sim vs mocap 0.890, reference 0.973, sim_vs_ref 0.863, static floor 0.604. Policy tracking cost about 0.14 AUC, perception about 0.03 |
| Contact retargeting "k" (22 Oct) | retarget the human hand to the object contacts | narrowed spread (ep12 0.725 +/- 0.067 -> 0.790 +/- 0.023, 6 evaluations each) but the mean moved within noise and ep27 lost 0.031: not a blanket change |
| FDR rewards (23 Oct, default from 04:40 that day) | object point-match reward on 128 surface points, a one-sided fingertip bound, down-weighted wrench terms. Hypothesis: the stock object reward has no gradient past 0.3-0.5 rad (0.00 vs 0.15 at 1.5 rad on a CPU check) | ep12 s42 0.891 +/- 0.015 vs 0.790; ep18 s43 0.889 +/- 0.011; the pre-set rule was not strictly met (ep12 s43 0.762), the owner made it default |
| VOC inertia fix (`FC_VOC_INERTIA`) | the VOC used the mean inertia diagonal; the spoon's inertia ratio is 38, so damping diverged above VOC about 0.13 and the first ~64M of 250M steps trained on exploding spoon episodes | ep35 0.105 -> 0.289 (7 evaluations); training 54-61k vs 27.5k steps/s |
| Grasp lock + fine-tune ("glock", frozen 24 Oct) | evolve a grasp (64 candidates x 4 jittered copies, 20 generations), lock it, then 70M steps of RL | ep39 0.958 +/- 0.002 (standard 0.802 +/- 0.280), ep18 0.957 +/- 0.002, ep27 0.949, ep12 0.868 +/- 0.122 (1 rollout in 5 fails), ep24 boards 0.241 +/- 0.125. Wins on grippable objects with 3.5x fewer steps; weak on plates, boards and tools. About $8 |
| "Use both" (owner, 25 Oct) | pick the learner per eval by the higher 5-evaluation mean on the same reference | the standard learner won evals 1 (0.9122 vs 0.2969), 19 (0.935 vs 0.6534), 25 (0.712 vs 0.376), 28 (0.9347 vs 0.6938), 30 (0.9188 vs 0.7216); glock kept 8, 14, 16, 20; frozen recipe chosen for 32 and 33. This was the policy side of pack 3 (+0.206) |

Other early public A/Bs (one seed unless stated) that were not adopted: wrist IK cost 3.0 (ep44 wrist p95 11.7 -> 2.5 cm, but ep12 fell to the 0.604 floor when the cup flipped); Viterbi hands with a kp 400 wrist (0.860 vs 0.890); own route-A meshes on ep18 and ep24 (0.381, 0.096: harmful); mid-wrist (falsified); hand separation at reset (0.231, at the floor); support fill (ep12 0.886 vs 0.910); recovery drops (ep12 0.869); re-planning from the simulated trace (ep18 0.405); grasp lock on settled ep18 (0.302, and the curve fell from 0.446 at 10M to 0.060 at 70M: training degraded the grip). The spoon work (wrap grasp, kp 400 wrist, RL fine-tune) is in section 6.

### 7.3 The eval batches (24-26 Oct)

The 24 Oct run trained all 20 eval episodes with the frozen recipe. sim_vs_ref per eval: 1 0.297, 3 0.851, 5 0.855, 6 0.982, 8 0.777, 10 0.334, 14 0.506, 15 0.901, 16 0.795, 19 0.647, 20 0.287, 25 0.243, 28 0.694, 30 0.469, 32 0.838, 33 0.391, 35 0.992, 36 0.994, 37 0.998, 38 1.000. Mean 0.692 (spoon episodes 0.860, others 0.525). Estimates moved from 0.74 to 0.66 to 0.68 as results came in; the board gave 0.57468.

Then a second seed (43) on the same references was chosen per eval by the 5-evaluation mean (evals 3, 5, 15, 16, 19; eval 28 kept seed 42), and the learner choice above was made. Packed sim_vs_ref rose 0.710 (pack 1) -> 0.7218 (pack 2) -> 0.883 (pack 3) -> 0.9121 (pack 4) -> 0.9164 (pack 6). Other per-eval choices in packs 3 and 4: eval 32 seeds s43 0.7016, s44 0.397, s45 0.634, s46 0.803 +/- 0.105 (chosen in pack 5); eval 33 s43 0.7853 +/- 0.255; eval 25 carve s42 0.7919 +/- 0.103 vs s43 0.4739.

### 7.4 Eval 10: from a 0.45 floor to the biggest policy gain

Eval 10 (nesting two cups) sat at about 0.45 for a week: H5 measured 0.450 +/- 0.007 (10 draws). Failed attempts, each pre-registered:

| Attempt | Result | Verdict |
|---|---|---|
| Early checkpoints B' (1M-8M), C' object ILC on the cup at rest | 0.446-0.465; 0.450-0.456 from 1M to 70M | falsified (bar: any checkpoint over 0.47) |
| Residual head with zero-initialised mean (plan's zero action 0.526) | 0.4459 at 25M | falsified: RL leaves the plan within about 1M steps and settles on not touching the cups |
| Carved hybrid cups, standard and glock | 0.4532 +/- 0.003, 0.4520 +/- 0.0014; glock 0.4539 vs needed 0.462 | falsified; glock logged "nefc overflow" every step |
| V4p retrain (31 Oct, 2 seeds, $3.25) | 0.459 vs 0.463; both fail 10 of 10, RPE about 15.9 cm | no swap (the public ep11 gate had passed at +0.142) |

The root cause was found on 31 Oct: about 6.0 M "nefc overflow" lines per training seed. The contact solver needed a median of 580 and a maximum of about 1,050 rows against the 512 limit; 13 % of world-steps overflowed, and the packed run logged 8,368,544 overflow lines in training but 0 in its scored draws. "Training is corrupted; scoring is not." Other evals had far fewer overflow lines (eval 33 about 21k, 32 about 20k, 14 about 4.6k, the rest 0-1.2k [E, from file sizes]).

| Fix | Result | Upload |
|---|---|---|
| Cavity-safe collision pieces ev10cs5 (8 mm floor plate), stock limits, seed 43 ($2.85) | vs reference V 0.5322 +/- 0.0615 vs packed 0.4632 +/- 0.0067 (+0.069); still fails 10 of 10; median RPE 13.94 cm | pack 10: +0.00158 AUC, -1 SP-SR episode |
| njmax 1024 diagnostic (owner "Okay go", 1 Nov 02:43, $2.06) | 0 overflow lines (bar 1,000); cup lifted 23.9 cm; sim_vs_ref 0.913 (10 draws, 0.869-0.933) vs 0.459 at stock; read out at stock 512/256: 0.9034 | diagnostic |
| Train at njmax 1024 / nconmax 512, evaluate at stock 512/256 (owner "I give give you go", 09:11; disclosed) | proxy +0.371 vs V, +0.361 vs P; fails 0 of 10 vs 10 of 10; weights byte-identical to the 1024 checkpoint | pack 11: **+0.02006 AUC**, +1 SP, +1 MP, RPE -0.50 cm |

A `budget.py` check at 32 worlds x 60 steps became the binding test for every new collision set. The eval 20 pitcher collision set b1 (41 pieces) missed its retrain bar by 0.0004 (0.8929 vs more than 0.8933) and was not packed.

### 7.5 Recipe screens and physics changes (29 Oct - 1 Nov)

None of these changed the recipe. All numbers are registered AUC against mocap on public episodes, mean (draw sd).

| Test | Result | Verdict |
|---|---|---|
| Arms A control / B CURR_SCALE 0.4 / C ball-wrist kd 2 (29-30 Oct; $6.37 / $3.82 / $4.26) | ep12 0.912 / 0.892 / 0.909; eval 32 0.631 / 0.743 / 0.702 (sd 0.14-0.20); eval 33 0.906 / 0.923 / 0.883 | inconclusive; B's eval 33 checkpoint later confirmed (0.934 +/- 0.008, pack 7) |
| Screen C scan-free / K longer horizon, lower LR / D start-state randomisation / S solved references / V object velocity (31 Oct, about $30.15) | ep2 s42: C 0.955 (0.029), K 0.965 (0.009), D 0.743 (0.269), S 0.751 (0.211); ep12 s42: C 0.576, D 0.924 (0.021), S 0.832; ep18 about 0.60-0.62 for all; ep24 0.19-0.25 for all; V -0.024 | K inconclusive (-0.0018), D inconclusive (+0.049, sd fell on ep12 only), S no signal (min -0.133). One re-run of a cell moved it by up to 0.07 |
| Targeted D arm on evals 14, 16, 25, 30, 33 ($19.41) | only eval 33 passed (0.9358 vs 0.9234); 14 0.686 vs 0.727 (fails 8 vs 4); 30 0.816 vs 0.897 | pack 9b, which scored -0.0008 |
| Scan masses S1 vs 0.3 kg S0 (30 Oct) | ep2 0.736 vs 0.944 (collapsed after 20M), ep12 0.885 vs 0.862, ep18 0.625 vs 0.573, ep24 0.232 vs 0.207 | not adopted |
| Realistic masses, glock (other session) | +0.090 on 4 public episodes (ep2 +0.160, ep12 +0.103) | see the conflict note below |
| Mass transfer check (31 Oct, $9.10, 10 draws) | ep2 +0.157 (SE 0.105), ep12 -0.013 | not adopted (rule: +0.03 on every episode) |
| Masses v2 (4 episodes) | mean +0.0034, 1 of 4 positive | not adopted |
| Command smoothing (test A) | glock +0.002 to +0.014; solver -0.027 to +0.014; needed +0.03 on 2 of 4 | failed |
| Sampling-MPC solver (CPU, then GPU G1-G3) | CPU robustness falsified; G1 with 1,024 worlds passed (+0.080 / +0.063 / -0.004 / +0.005, $1.29); RL from solved references (G3) harmed ep2 on one seed ($6.48) | not adopted |
| Solver-RL loop O3 vs O1 | pre-registered "signal" +0.068, but 3 of 4 checkpoints came from before the loop and the solver changed 0 frames in 4 of 8 turns | not credited |
| Own 22-DoF capsule human hand (Apache-2.0) | squeeze and lock hypotheses falsified; human hand + RL -0.161 vs the Sharpa hand | not adopted |
| GRASP-style sampler, ep13 (CPU) | two-hand vs single +0.024 (95 % CI -0.071 to +0.115), bar +0.05 | falsified at this budget |
| Hold-filter repair | M1 +0.0017; followability M2 -0.018 (needed +0.02) | failed |

**Conflict in the sources on masses.** One overnight summary and the 31 Oct round-3 entry say "realistic masses adopted (+0.090)". The more specific later entries say the transfer check and Masses v2 failed and masses were not adopted. The packs do not show a mass change, so this report treats masses as not adopted.

### 7.6 Seeds, draws and what a packed draw is worth

- **Single evaluations mislead.** Eight repeat evaluations of one ep18 policy: mean 0.332, sd 0.08, range 0.131-0.410 [D]. Eval 1 at pack 6: 0.822 +/- 0.239 over 10 draws.
- **Training curves** (29 standard curves): 22 started below 0.5 at 100M, the median gained only +0.04 by 250M, and 13 of 22 ended below the static floor. Pick-up on the spoon appeared at 70-90M and stayed flat.
- **Seed races** (31 standard, 66 glock curves): the score at 40 % of training correlates 0.89 with the final score for the standard learner, and the early leader ends better in 30 of 36 cases (glock 22 of 38). Early cuts would suit the standard learner only; not adopted.
- **H5 (29 Oct):** 10 fresh draws of each pack-6 checkpoint gave a mean of 0.8755 against 0.9164 packed. Packed draws were lucky (rank sums 69 and 80 vs 40 expected, z about 3.2). Because Kaggle banks the submitted draws, an "insurance" swap to a steadier policy was worth only +0.0003 to +0.0007 [E].
- **Zero action:** in 15 of 64 stored results the plan's zero action beat the trained policy by more than 0.02 (eval 10: 0.663 vs 0.447), but the 22 Oct rule allowed only learned policies.

### 7.7 Following repairs (1-3 Nov)

From 1 Nov a swap needed: 10 fresh official draws against the packed draws, a gain of at least +0.02 on both references, no more failed draws, and a median RPE that is not worse (clauses a, b, c and s).

| Repair | Result (10 fresh draws) | Verdict |
|---|---|---|
| Guard bridge, eval 14 (single-hand, seed 43) | 0.875 vs packed 0.706; fails 1 vs 4; median RPE 2.71 vs 4.38 cm | included (12b) |
| Guard bridge, eval 32 | 0.890 vs 0.851; fails 0 vs 4 | included (12b) |
| Guard bridge, eval 33 | 0.9395 vs 0.9199 (+0.0196) | below the +0.02 bar by 0.0004; not included |
| Eval 16 right hand kept on the spoon from f107 | 0.974 vs 0.850; fails 0 vs 0; median RPE 1.18 vs 1.79 cm; same-box controls 0.769 / 0.787 | included (12b) |
| Eval 16 hold to end (pfF) | 0.687 / 0.719 vs 0.769 / 0.792 | no swap |
| Two-hand references | public ep13 +0.104 (one seed carries it); eval 14 0.603 vs 0.727; eval 16 0.713 vs 0.850 | no swap on eval |
| Lift-window training starts (plw) | public ep31 0.730 vs 0.589 (control collapsed); on eval 1 of 8 passed: eval 20 0.926 vs 0.893 (pack 13); eval 15 0.958 vs 0.906 but median RPE 1.346 vs 1.299 cm (pack 13b by owner waiver); eval 3 0.888 vs 0.933; 14 box 0.923 but fresh 0.826; 25 0.529 vs 0.878; 28 0.864 vs 0.919; 30 0.787 vs 0.897 | 2 included |

### 7.8 Retrains with the new meshes as collision: 1 of 7 passed

After 12e, the Tier B and generated meshes were tried as simulator collision shapes.

| Eval | Zero-shot with new collision vs control | Retrain result | Verdict |
|---|---|---|---|
| 14 (rack + blue cup, p0m) | close to control | fresh 0.933 vs 0.875; fails 0 vs 1; RPE 1.97 vs 2.71 cm | PASS, pack 14p (+0.00168) |
| 20 (pitcher) | 0.451 vs 0.926 | s42 0.293, s43 0.604 +/- 0.266 | no swap: the grasp was built on the old pitcher shape |
| 28 (rack) | 0.906 vs 0.919 | s43 0.914 vs 0.919 | no swap |
| 30 (sweeper + rack) | 0.829 vs 0.897 | box s42 0.938, s43 0.932; fresh 0.768 vs 0.897, fails 5 vs 1, RPE 4.74 vs 2.93 cm | no swap (box-to-fresh drop -0.170) |
| 32 (cup) | - | 0.790 / 0.826 vs 0.890 | no swap |
| 33 (cup) | - | 0.917 vs 0.923 | no swap |
| 19 (sweeper) | 0.226 vs 0.929 | 0.828 / 0.655 | no swap |

Two lessons came out of this: an entry rule ("zero-shot within 0.02 of control") and two-host confirmation, because box draws overstated fresh draws (eval 14 lift 0.923 -> 0.826; eval 30 0.938 -> 0.768). A pre-registered evaluator-gap test ($1.1) did not reproduce the drop (eval 30: 0.935 / 0.926 / 0.930 across the training box, the pristine kit and a patched-off tree; eval 14: 0.925 / 0.937 / 0.938), so its cause is unexplained [H]. One host fault was seen directly: a box ran at 14.4k env steps/s instead of about 50k with the GPU at its 500 W cap.

### 7.9 How closely the rollouts follow the references

| Measurement | Number |
|---|---|
| Packed sim_vs_ref, pack 1 -> pack 6 | 0.710 -> 0.9164 [M] |
| Fresh-draw mean of pack-6 checkpoints | 0.8755 (10 draws each) [M] |
| Board loss split at pack 7 | policy 0.083 [M], reference about 0.10 [E] |
| RPE of a rollout vs our reference (public) | successful draws 1.4-3.5 cm; failed draws 10-77 cm; the reference itself costs 1.2-2.1 cm per rollout [D] |
| GT-free RPE vs own reference against RPE vs mocap | r = 0.9998 over 70 draws [D] |
| 31 Oct eval audit | only eval 10 failed (beige cup left behind, RPE 15.76 cm, 0.79 cm of the board mean); borderline evals 32 (3.69), 14 (3.39), 1 (2.89) |
| 3 Nov SR audit of the 14p rollouts | all 20 pass SP-SR and MP-SR against our references, none within 20 % of a threshold; tightest MP margins eval 10 beige 1.85 cm, eval 30 sweeper 1.82 cm / 11 degrees |

So by the end the policies follow our references well; what remains is mostly the gap between our reference and the truth (sections 5 and 6), plus draw-to-draw failures on a few hard episodes.
