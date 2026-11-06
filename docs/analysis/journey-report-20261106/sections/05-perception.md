## 5. Perception

Perception is everything that turns the video into object poses: depth, detection (which pixels are which object), identity (which of two look-alikes is which), 6-DoF tracking (position and rotation over time), the camera's own motion, and the hands. Its output is the **reference**: one trajectory per object that the robot policy later tries to follow (section 6). All public numbers here are [D] (public episodes scored against mocap) unless marked otherwise. "AUC" in this section means the registered public AUC averaged over the public episodes named.

### 5.1 Design input from the October research (4-7 Oct)

The side research before building (notes 01-21) set the priorities. The most important measured facts:

| Note | Finding | Number |
|---|---|---|
| 01 | NVIDIA's ego baseline uses only monocular MoGe-2 depth, tracks one object and hard-codes 30 fps | Track 3 video is about 20.25 fps; the 75 mm stereo pair is never used |
| 02 | Error budget, made by perturbing public mocap and scoring with the official code (8 seeds per random case) | static predictor AUC 0.446 / SP 0.45 / MP 0.00; dropping the most-moving object 0.550; 5 cm drift 0.799; slot-0 start 3 cm off 0.740; slot-0 10 degrees off 0.813; 10 degree cup spin 0.714; "careful stereo" 0.889 vs "rough mono" 0.531 |
| 03 | Literature and licences | HOT3D recall at 10 cm: 96.8 % stereo vs 30.2 % mono. FoundationPose YCB-V ADD 96.0. SAM 3 vs SAM2 on MOSEv2: 60.3 vs 47.9 J&F |
| 12 | Spin of near-symmetric cups is visible only through the mocap markers | beige cup with 2 markers: 21-28 of 40 flips; with the third marker 0-1 of 40 |
| 13 | Spoon frame and roll | any complete spoon-shaped mesh gives CD-O 0.11-0.16 cm; stereo roll error median 2.5-6 degrees; the frame-sign bit stayed unresolved (P(B) estimates moved from 0.80-0.87 to 0.33-0.5) |
| 15 | Eval video survey, no labels | the same seated second person is at the left edge of 19-20 of 20 eval clips; the wearer has a white smartwatch on the left wrist; evals 20 and 32 have no still window before contact |
| 17 | Mocap-marker tracking | stand-alone fails except for the lid (0.977); as a correction layer on an emulated 10 mm / 5 degree prior +0.03 to +0.12 |
| 18 | Room map (structure-from-motion on public frames only) | relocalises 100 % of the 20 eval clips; public edge residual 0.10-0.18 cm; estimated +0.06 to +0.07 board AUC after a sceptic review |
| 20 | Camera timing | cameras b and c are hardware-synchronous (-0.01 +/- 0.09 ms, 39 clips); camera a pairs a[k+1] with b[k] in 36 of 39 clips; rolling shutter 31.6 ms per image height |

Three "trap areas" were known in advance: near-symmetric anchors, the spoon frame and roll, and camera drift. Section 3 explains why the slot-0 frame-0 pose matters so much.

### 5.2 The stack that worked

| Component | What it does | Evidence |
|---|---|---|
| FoundationStereo depth, half resolution (0.27 s/frame on Colab) | metric depth from the 7.5 cm stereo pair | first run on ep12 (13 Oct): cup AUC 0.927, median position error 1.30 cm (p90 2.26), both objects 0.964; on Vast (20 Oct) ep12 AUC 0.997, MPPE 0.52 cm in 96 s |
| perc2 detector (SAM2 automatic proposals scored by DINOv2-L CLS against 42 grey renders of each mesh, a 3-D size gate and Hungarian assignment) | finds each listed object at frame 0 | replaced OWLv2, which missed the pot on grey frames (ep0, ep2) and swapped the twin cups on ep11 (0.10 -> 0.871) |
| FoundationPose register (5 iterations) and track (2 iterations) | 6-DoF pose per frame from mesh + depth | median position error 0.3-2.3 cm when detection is right; no mid-episode losses |
| Keyframe SIFT / stereo PnP visual odometry | camera motion | eval camera drift small: perc2 camera vs room map gap p95 2-9 mm on 19 of 20 clips |
| Compactness prior (DET_PRIOR=compact, DET_K=80) | objects of one task start within about 0.45 m of each other | public mean 0.883 -> 0.932 (20 Oct); ep26 0.065 -> 0.988; worst -0.003 |
| Detection rules (reach gate 1.0 m, size term 0.05, Grounding DINO 0.2) | reject people, chairs and object parts | correct labelled public instances 78 -> 93 of 116, 0 lost; chosen from a 1,248-variant grid replayed on stored dumps with the rule fixed first |
| Gated re-proposal (re-prompt SAM2 from Grounding DINO boxes when agreement G < 0.2) | second chance at frame 0 | 93 -> 95; moved eval 30's sweeper from the watch strap (G 0.001) to the broom (G 0.284); board 0.57468 -> 0.58252 [M] |
| On-table rule (no proposals below the table) | removes below-table blobs | 95 -> 97; ep11 0.102 -> 0.898 (beige cup 0.000 -> 0.933) |
| TRACK_GUARD (flag: lowest 5 % of the surface more than 2 cm under the table; then retry frame 0 or re-detect) | catches catastrophic tracks | flag fires on exactly the three known public failures and on no good track; 8 episodes 0.7239 -> 0.7821; ep0 lid 0.496 -> 0.964; on eval it acted on evals 8, 14, 32, 33, never on a spoon |
| Board knob identity rule (identity_fix.py) | names the two look-alike wooden boards by knob darkness | ep24 0.029 -> 0.706; ep23 0.041 -> 0.663 (about +0.031 on the 20-episode mean); fixed eval 25's swapped reference (rank 21 of 32 -> the fresh run ranked it 1 of 32: naming without the rule is close to a coin flip) |
| guard_bridge repair | bridges the one-frame 19 cm cup jump the guard left on eval 14 (also eval 32) | eval 14 failed draws 4/10 -> 1/10; swap verdict +0.169 [M]; part of pack 12b (+0.00484 [M]) |
| Colour camera a for MediaPipe hands | hands need colour and resolution | two-hand detections: grey camera c about 0 frames, camera a 173 of 181 (ep12), 338 of 373 (ep0) |

Public mean progress of the perception stack alone: 0.809 (13 Oct, Colab, 20 episodes) -> 0.932 (20 Oct, compactness prior). Under the registered scorer with our own meshes the default tracker scored 0.868 on 20 episodes (25 Oct) and 0.945 on 19 episodes (2 Nov, library_v3 templates + TRACK_GUARD).

### 5.3 What eval perception cost

On eval the reference was much worse than on public twins. Pack 1 rollouts followed our own reference at sim_vs_ref 0.710, while the board gave 0.575: about 0.135 AUC [M] was reference-vs-truth error, against only 3-4 % on public twins. Losing an object to the wearer's wrist cost about 0.09 [I] (evals 30, 14, 33, 8, 32). Later measurements narrowed this down:

- 31 Oct: packed rollouts vs our own references gave RPE 2.45 cm against the board's 3.93 cm, so about 1.5 cm of board RPE was reference or registration error [M/I]. The gross-error screen of 36 eval reference objects found no persistent gross error (more than 5 cm or 20 degrees over a large share), only transient 10-45-frame errors in held phases (eval 32 cup latched onto the watch, a 19.7 cm step; eval 14 cup lag; eval 33 cup), worth about 0.15-0.2 cm RPE [E].
- 3 Nov: all 20 stored 14p rollouts pass SP-SR and MP-SR against our own references, none within 20 % of a threshold. So the board's 2 SP-SR and 4 MP-SR failures are reference-vs-truth errors of about 2-3 cm that we cannot see [I]. The gross-failure audit of the 14p references (SAM2 masks + depth + hands) found 12 clean episodes (median mask IoU 0.70-0.89, depth residual 0.6-0.9 cm) and moderate cup and spoon offsets of about 4-8 cm for 5-20 frames on evals 32 and 33.
- Oracle twin: on public ep11, using mocap object motion as the reference scored 0.940 against 0.595 with our perception [D].

### 5.4 Everything else that was tried

About 30 further perception ideas were tested, most of them from 30 Oct to 3 Nov on the 20 public episodes, each under a pre-registered gate (usually a mean gain of at least +0.005, no episode below -0.01, and MPPE/RPE not worse). Only mesh choice and mesh placement passed. Section 9.1 lists every test with its hypothesis, gate, result, margin and cost; here they are grouped by what they tried to fix, with the key number and the reason.

| Target | Ideas tried | Best result | Why it did not work |
|---|---|---|---|
| **Noise and jitter** | causal Kalman, offline and zero-lag RTS smoothers, rest-averaged spoon anchor, static hold, per-frame refinement | RTS -0.00011; Kalman 1.3-22 % worse ADD; A-f0 +0.001 vs +0.01 | the error is bias plus a 25-28 ms delay, not noise; causal filters add lag |
| **Constant offsets and tilt** | constant-offset ICP, refine S1/S3 (snap, tilt-to-plane), rest projection, physics priors (fused tilt, axis prior, "resting objects do not float"), H1 learned bias per object | physics stack +0.00298 vs +0.003 (CI +0.0008 to +0.0059); H1 passed only for the pitcher (+0.046) | the bias is episode-specific for every object except the pitcher (spread-to-mean 0.95 or more); priors snap to wrong mesh shapes; overlaps at rest are mostly mesh shape (the C0 pot base sits 7-8 mm low) |
| **Depth as a corrector** | full-resolution stereo, mask-restricted depth, multi-frame rest-segment fit, placement from depth for all objects, hand-aware ray correction, free-space depth audit | placement +0.0026 (pitcher alone +0.106); hand-aware holdout -0.0042 (noise 0.0015); audit AUROC 0.600 | depth cannot tell template error from pose error; on thin or oblique objects it measures surfaces behind them (ep24 board moved 21 cm) |
| **A second sensor** | mocap-marker layer, KLT point tracks, MediaPipe hand-rigid transport, GDRN-style pot network, room-map cameras | markers -0.083; KLT -0.0578; hands -0.12 to -0.79; pot network -0.0085 with mocap fine-tune; room map +0.0070 public but ep22 -0.0164 | FoundationPose with stereo is already more accurate (pot 0.26-0.42 cm vs marker fixes 1.0-2.2 cm); KLT precision 5/17; camera drift already only 2-9 mm |
| **Better templates** | per-episode Set B templates, lathe pitcher template, tracking with the submitted 13f meshes, FoundationPose t4/t8 iterations | t8 -0.004; Set B -0.170; lathe -0.249; Test B -0.043 | FoundationPose is fragile to template and setting changes; a better CD-O mesh is not a better tracking template |
| **Detection and masks** | Viterbi hand linker, SAM2 mask-guided tracking and re-registration, SAM-6D-style detector scores, board-face cue, spoon flip check | SAM-6D added +0.0010; MR +0.0029 then lost the ep0 lid (-0.380) | frame-0 assignments were already right on all 20 public episodes; masks are cut by hands; a wrong frame-0 mask poisons re-registration |

The half-frame advance (S2, +0.0061 public, 17/20 better) is the one perception gain that passed on public data and was never used in a packed eval reference (pipeline_ep.sh does not call refine.py).

### 5.5 What bounded the remaining perception error

Oracles (mocap used only for diagnosis, never for inference) measured how much each kind of error was worth:

| Oracle (public) | Gain if perfect |
|---|---|
| perfect poses on still (rest) frames only, 19 episodes | +0.032 (ep24 +0.118, ep31 +0.112) |
| constant translation offset per object after kit alignment | +0.030 (vertical +0.019, along the camera ray +0.020) |
| constant per-object body offset (reference level) | +0.050 (19 of 20 better) |
| frame-0 scene alignment (reference level) | +0.040 |
| exact anchor tilt | +0.0164 (ep21 +0.135, ep22 +0.098; about +0.004 without the pitcher) |
| held-phase ray error | +0.0195 |

The measured picture by 3 Nov [D/I]: the tracker is accurate, camera drift is small, and public loss comes from frame-0 detection and identity failures plus systematic biases (template shape, pitcher tilt of about 6 degrees, along-ray offsets). Smoothing cannot remove bias, and depth fitting cannot tell pose error from template error. The one perception lever that kept paying was making the submitted mesh and its placement agree with our own trajectory, because the kit registers our mesh to the hidden scan (section 8). The coordinator's inference on 3 Nov was that the FoundationPose + stereo tracker had reached the limit of cheap fixes [I].

### 5.6 Noise, cost and open points in perception

- **Tracker run-to-run noise** on public episodes: mean absolute change 0.0012 AUC per episode, mean -0.00002 [D]. The tracker is chaotic: ep18's sweeper is lost by both control runs and recovered by every perturbation. A single-episode gain is weak evidence, so gates used 20-episode means, a no-harm clause and a noise term.
- **Loss split at pack 7** (board): policy 0.083 [M]; reference about 0.10 [E], of which about 0.06-0.07 is the spoon [E]. A perception gain reaches the board at about 0.74 of its size, and only through rebuilt references and retrains at $3-8 per episode, so public gains under 0.005 were not worth deploying.
- **Where public loss sits:** 70 % of it is in hand-held frames (board merge at assembly, pitcher bias, along-ray offsets that depth cannot see). Public per-object check: 37 of 40 object-episodes pass MP-SR in all 10 seeds; the misses are the ep23 board-2 merge, the pitcher's 3-3.4 cm bias and one registration flip on ep24.
- **Hands:** the perceived hand is small (wrist to middle fingertip 11.9 cm vs an 18.5 cm adult template) and collapses to 3.8-5.2 cm while gripping (ep24). Moving an object rigidly with the MediaPipe hand cost -0.12 to -0.79.
- **Room map:** a public-only map (370 images, 1.11 px) relocalised every eval frame (at least 442 inliers) after about 22 min of CPU build. Only public ep24 had real drift (perc2 chain 37 mm / 1.66 degrees off; map cameras 0.834 -> 0.982). Eval 35 was the one eval clip with a larger gap (17.9 mm; AUC bound 0.056, about +0.002 board [E]); a guard for it alone was never pre-registered or run.
- **GPU cost of perception work** [E, from instance hours]: about $45 in total, for example the 2 Nov tracking lane about $25-26 (five boxes), TRACK_GUARD validation $0.8, the iteration sweep $3.7, the re-track test $1.54. The physics, room map, point track, hand-aware, marker, depth-audit, H1 and pose-CV work ran on CPU at $0.
- **Not tested:** a BootsTAPIR learned point tracker (its trigger rule was never met, section 5.8), a VLM candidate selector, running perception twice per eval episode to check repeatability, a frozen all-rules-together scoring, and the half-frame advance (S2) inside packed eval references (about +0.004 board [E]).
- **Spoon:** 10 of 20 eval episodes contain the spoon and 5 use it as the anchor, but there is no public spoon scan or ground truth. Its roll frame bit, a roughly 5 degree disagreement between our track's mean roll and the template's marker model, and hidden phases (stirring inside a pot or cup) stayed unmeasured.

### 5.7 Further measurements from the chat sessions

These come from the builder and coordinator chats (26 Oct - 3 Nov) and the early chat (20-23 Oct); they add to, and do not replace, the numbers above.

- **Early perception checks (20-22 Oct).** The compact prior's A/B showed no regressions on episodes 0, 12, 27 and 39 (within +/-0.003); ep26 went 0.065 -> 0.988, ep2 0.977 -> 0.993, ep31 0.876 -> 0.887. Ep39 scored 0.998 on Vast against 0.55 on Colab, a sign of large run-to-run variance in the first stack. The detection rules found the spoon in all 10 eval spoon episodes at frame 0; in evals 3, 5 and 6 the pot and the spoon's handle merge into one object. Ground-truth masks for a spoon detector were rendered for 18 of 20 public episodes (ep0 and ep26 excluded because their tracking was 5.7 cm and 35 cm off). The kit lists the objects of each eval episode, which fixes slot order: spoon alone in evals 35-37, pot and spoon in 3, 5, 6, rack and spoon in 15, 16, cup and spoon in 32, 33, and no spoon in the other 10.
- **Hand audit on 20 public episodes (27 Oct, $0).** MediaPipe saw at least one hand on 2,610 of 2,612 carry frames (99.9 %). In the pour episodes 21 and 22 both hands were visible on only 22-25 % of pour frames, because the pitcher hand is outside the colour camera's view (gaps of 1.5-1.7 s). Left and right labels flipped up to 50 times in one clip. NVIDIA's own reference had hand contact on 100 % of moving frames, with a peak object speed of 0.08 m/s against about 0.33 m/s in our clips. The tool `pipeline/audit_ref.py` now runs after every reference build. An independent reviewer with synthetic tests found six bugs in it (for example a `table_z` default equal to the lowest object's height, so that object always read 0 cm, and a crash at T=1); all were fixed and NVIDIA's reference output did not change.
- **Perception accuracy by object (29 Oct, registered AUC against mocap, own meshes) [D].** Original pipeline 0.809; current, all 20 episodes, 0.868; with the newest meshes and the identity guard about 0.892 (derived); after building the final reference 0.915-0.902 on 10 episodes (reference building loses about 0.013, the frame-0 table snap alone about 0.016). Per object: lid 0.97, sweeper and dust pan 0.95, blue cup 0.93, pot and rack 0.92, beige cup 0.91, boards 0.82, pitcher 0.575 (weakest). Resting objects jitter at 1.9 cm/s and 13 deg/s against 0.27 cm/s and 2.8 deg/s in mocap. The spoon has no public ground truth; the leaderboard implied 0.73-0.80 for it [E].
- **Camera fix.** A depth cut at 2 m took public ep24 from 0.81 to 0.994 (the 2 m clip had been hiding the camera motion); no eval episode showed that jump (eval 25 clean, eval 35 unverifiable), so it was kept in the pipeline at no cost. The static-object freeze (no motion for objects that do not move) was right on 20 of 20 static objects and fixed ep11 (+0.07), but failed its no-harm rule by 0.0023 against a 0.002 limit and never fires on eval 10, where the outer cup really slides about 4 cm; it was dropped. (Section 9.1 lists the older "S6" static-hold test at -0.0003 against the same kind of rule; the two are different versions.)
- **Why ep0 is a trap (30 Oct).** The detector took the round table top for the pot in frame 0 and fitted it upside down. The scorer aligns the scene from frame 0, so one bad frame wrecks the whole episode; the table is a decoy in 8 of 9 public pot episodes. With exact scanned meshes as templates ep0 still scored only 0.08 while 16 of 20 episodes reached 0.96-1.00 [D].
- **Cup spin (1 Nov, 19:53).** Following our perceived blue cup scored 0.34 against 0.60 for true motion. The tracker spins the resting cup (12 degrees by frame 8, 140 by frame 30). After the official code was read, the finding was corrected: the leaderboard ignores spin about a cup's axis, but our own score counts it. This is one reason our own score can disagree with the board.

### 5.8 What the perception lanes tried before their final verdicts

Verdicts and gates are in section 9.1. This adds the first steps and intermediate numbers that the work logs skip, read from the lane sessions' own turn summaries. [D] unless marked. Only the tracking lane and the pot network rented GPUs; the rest ran on CPU at $0.

| Lane (dates) | Tried first | Intermediate numbers | Why it stopped |
|---|---|---|---|
| Marker layer and third camera (31 Oct) | GT-free marker correction; colour camera a as a third view for the markers | markers: mean dAUC -0.083, 1 of 16 units better, worst -0.407. Third view raised spoon roll-marker visibility at rest from 43 % to 83 % but fixed 0 of 3 objects (2 needed) | both gates failed; spoon roll stayed the unexplained suspect |
| Physics priors (1-2 Nov) | frame-0 tilt from the tracker and the mesh's stable rest pose (P1); symmetry axis as "up"; lowering floating objects (F1); cup twist from the GRASP tool | P1 +0.00156 (13 better, 0 worse); axis variant +0.00067; F1 +0.00142; twist worse on 5 of 6 cups (twist held only at rest: AUC unchanged) | stack +0.00298, short by 0.00002. Left behind `qa_physics.py`: flags exactly the two catastrophic public failures (ep0 lid, ep23 boards) plus one false positive |
| Room map (2 Nov) | October map rebuilt without ground truth: 370 public images, 100 % of eval frames relocalised | G1 bound failed (objects differ from the map by 2-9 mm at p95 on 19 of 20 eval clips; eval 35 18 mm). Public mean +0.0070, but ep22 -0.0164. On ep24 the map recovered 84 % of its bound (0.834 -> 0.982; perc2 camera 37 mm off). | a camera guard "only where bound >= 0.02" was not run, because the threshold would be set after seeing public scores |
| Point tracks (2 Nov) | KLT tracker seeded from the template at FoundationPose's frame-0 pose | repair of lagging tracks -0.058; every flag -0.132; frames over 3 cm off 955 -> 1,115 and 1,609. Only 5 of 17 flagged spans were real | points slid onto hands and background on white, light-wood objects; one false flag replaces the rest of a clip |

**Perception-accuracy lane (2-3 Nov, mostly RTX 5090 boxes at $0.6-0.7/h; about $25-26 [E] of $40 granted).**

- It first reproduced the physics lane's baseline exactly (mean AUC 0.8769). Six runs crashed out of memory on 32 GB cards; the pre-registration counted a crashed cell as control.
- The re-centre variant (+0.0029) was chosen after scoring, so it could not be adopted; its replication lost the ep0 lid (-0.380) because the re-detection guard rejected the frame-0 lid mask but the video mask was still propagated from it. Depth limited to the object mask cost the blue cup -0.128 on ep11. A complete-base pitcher template made the tracker re-detect three times against none for control.
- ep23 was first described as a joint tracking loss. Later measurement showed a board identity swap at frame 0, which the scorer's frame-0 alignment hides. `identity_fix.py` ran only inside the eval job; applied to the public control it moved ep23 from 0.041 to 0.663 (error 16.3 -> 5.4 cm).
- Public mesh sets on the same tracks: 9a+ 0.8998 against 13f 0.8746. The owner ruled that a "$6 cap overrides the never-cut rule" for one detector box, an explicit exception to the no-time-limit rule.

**Pot pose network (3 Nov, one RTX 4090, about 1.4 h, about $0.8 [E]).** Train on ep0, 26, 41, 42, 43; test on ep2, 27, 44, 45 (pot AUC already 0.968-0.998). The first gate could never pass (maximum gain +0.017 against +0.02), so a second gate (median pot ADD down 20 %) was added before training; the agent's own pass chance was about 25 % [E]. The first job died in two minutes because `.gitignore` excludes `*.npz`, so tracks and labels never reached the box. Result: R (rendered data only) -0.065, R+M (fine-tuned on mocap) -0.0085. The error sits in hand-held frames on ep27 (ADD 2-6 cm, rotation about 10 degrees off); the rendered pot interior does not look like the real one. A spoon network would have no public mocap labels to close that gap.

**Hand-aware tracking (3 Nov, CPU).** Literature first: HOnnotate's objective was adopted for the object only; HOLD, MagicHOI and HaWoR were set aside (monocular, template-free, hours per sequence). The first diagnostics used the wrong control; redone on the real one, 70 % of public AUC loss is in frames where the object moves, and a half-frame shift gives +0.005. Development: ep18 0.9246 -> 0.9487, but on ep11 depth agrees with the track while mocap says 2 cm off. Holdout: ep24 board 2 was moved about 21 cm against a real ray error of about 2 cm (MP-SR 0.9 -> 0.0); ep26's rack moved 4 cm though nobody holds it. The development episodes had no board, so tuning could not show this.
