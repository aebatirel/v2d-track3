## 9. Every test that failed or was declined

"Margin" is the result minus the pass gate (or the board change against the expectation). Public results are [D] registered AUC averaged over the episodes named; eval results are sim_vs_ref over 10 fresh draws unless stated; board results are [M]. Costs are GPU dollars where the sources state them ("CPU" = $0). Details and context are in the stage sections (5-8).

### 9.1 Perception

| Date | Test | Hypothesis | Gate | Result | Margin | Why it failed | Cost |
|---|---|---|---|---|---|---|---|
| 13 Oct | OWLv2 detector | open-vocabulary boxes find the objects | works on 20 public | missed the pot (ep0, ep2), swapped ep11 cups (0.10); 4/10 at frame 0 | - | weak on grey mono frames | Colab |
| 20 Oct | Viterbi hand linker | global path removes wrist jumps | fewer jumps than greedy | 276 vs 255 jumps over 5 cm | +21 jumps | follows the second person's hands; forearm cue near-random | GPU (small) |
| 24 Oct | plain SAM2 re-proposal | re-prompting fixes eval 30 | no regression | 2 regressions | fails | needed a gate (the gated version passed) | CPU |
| 25 Oct | FoundationPose t4 / t8 iterations | more refinement = precision | +0.005, no episode -0.02 | 0.8551 / 0.8640 vs 0.8677 | -0.013 / -0.004 | whole objects jump to wrong optima (ep18 -0.25 to -0.29) | $3.7 |
| 25 Oct | spoon rest-averaged anchor A-f0 | averaging the still frames fixes roll | +0.01 | +0.001 | -0.009 | anchor noise is small next to bias | CPU |
| 26 Oct | S6 static hold | freezing still objects helps | no-harm | +0.004 mean, fails no-harm | -0.0003 | moves some good poses | CPU |
| 27 Oct | per-frame pose refinement | slide frames along cylinder axes | pre-registered falsifier | falsifier fired; shells worse | - | jitter stays above within-frame width | CPU |
| 30 Oct | free-space depth audit | depth flags > 2 cm reference errors | AUROC 0.75 | 0.600 (CI 0.40-0.78) | -0.15 | depth sees large offsets, not 2-3 cm errors | CPU |
| 30 Oct | refine S1 / S3 / S4 | snap, tilt-to-plane, pre-contact hold | positive mean | -0.0077 / -0.0013 / +0.0003 | - | snap to wrong-shape priors | CPU |
| 31 Oct | marker correction layer | marker blobs correct the tracker | positive, 16 units | -0.083, 1/16 better, worst -0.407 | -0.083 | marker fixes 1.0-2.2 cm vs tracker 0.26-0.42 cm | CPU |
| 31 Oct | S11 offset ICP / S10 held pose / K1 / K2 | fit constant offsets or holds | +0.005 / +0.01 | +0.0005 / -0.018 / +0.001 / +0.001 | all below | bias not observable this way | CPU |
| 31 Oct | per-episode Set B templates | own clean templates track better | mean dR +0.01, 12/20 better | -0.170, 3/20, min -0.973 | -0.18 | template changes break FoundationPose | $1.54 |
| 31 Oct | causal Kalman / RTS smoothers | the error is noise | +0.005 | Kalman 1.3-22 % worse; RTS -0.00011 | -0.005 | the error is bias plus a half-frame delay | CPU |
| 1 Nov | rest projection pose fix | remove mesh interpenetration | +0.002 | -0.0107, 17/20 worse | -0.013 | overlaps are mostly mesh shape | CPU |
| 1 Nov | physics as a sensor (F1P1 stack) | tilt, axis and no-float priors | mean +0.003 | +0.00298 (CI +0.0008 to +0.0059) | -0.00002 | physics facet about 2 degrees, same as tracker | CPU |
| 1 Nov | hold-filter repair | clean held phases | followability +0.02 | +0.0017 accuracy, -0.018 followability | -0.038 | edits help accuracy, hurt following | CPU |
| 2 Nov | mask-guided tracking MG / MD / MR | SAM2 video masks clean depth | +0.005 and 2x noise | -0.0009 / -0.0077 / MR lost ep0 lid (-0.380) | -0.006 | masks cut by hands; wrong-mask re-registration | part of the ~$26 tracking lane |
| 2 Nov | full-resolution stereo | finer depth | +0.005 | -0.0079 | -0.013 | tracker sensitive to input change | part of the ~$26 tracking lane |
| 2 Nov | SAM-6D-style detector scores | ISM terms improve detection | +0.005 | +0.0010 added; -0.204 replacing (3 crashes) | -0.004 | perc2 already had the semantic term | ~$4.6 |
| 2 Nov | lathe pitcher as tracking template | closed base fixes tilt | positive | -0.249 | -0.249 | lower, wider template breaks tracking | GPU (in lane) |
| 2 Nov | Stage 1 rest-segment depth fit | multi-frame fit of still objects | 14/20 lower rest ADD | -0.0088, 9/20 | -5 episodes | fitting to a wrong shape moves good poses | CPU |
| 2 Nov | KLT point tracks | second opinion on lagging tracks | +0.005 | -0.0578 (all flags -0.1319) | -0.063 | KLT slips on weak texture; 5/17 flags real | CPU |
| 2 Nov | room-map cameras | fixed map removes drift | G1 bound 0.01; G2 no episode < -0.01 | bound 0.0029; ep22 -0.0164 | -0.007 / -0.006 | drift already only 2-9 mm | CPU |
| 2 Nov | placement from depth, all objects (Test A) | depth corrects every placement | +0.005 | +0.0026 | -0.0024 | only the pitcher bias is real; thin objects get wrong rotations | CPU |
| 2 Nov | tracking with submitted 13f meshes (Test B) | the scored mesh is the best template | positive | -0.043 (ep0 lid -0.901) | -0.043 | better CD-O mesh is not a better template | GPU (in lane) |
| 3 Nov | pose CV rounds 2-3 (other objects) | more mesh swaps pay | held-out +0.005, source-excluded | blue cup +0.0005, rack -0.0055, board 1 -0.033, board-2 shell +0.0041 | below | shipped meshes already near best | CPU |
| 3 Nov | H1 learned bias per object | biases are systematic per object | per-object pass | only pitcher (+0.046, weaker than depth +0.106); boards -0.19 / -0.38 | fails 9 of 10 objects | bias is episode-specific (spread/mean 0.95 or more) | CPU |
| 3 Nov | GDRN-style pot network | an object-specific network beats the tracker | +0.02 (ceiling +0.017) | -0.0647 / -0.0085 | -0.085 / -0.029 | render-to-real gap, no temporal prior | ~$0.8 |
| 3 Nov | board-face cue | detect board face flips | false flags 5 %, recall 50 % | 5.2 %, 24 % | -26 points recall | ep23 error is a merge, not a face flip | CPU |
| 3 Nov | hand-aware ray correction | correct held objects along the ray | +0.005; worst -0.01; held ADD -10 % | -0.0042; ep24 -0.047; -4.3 % | -0.009 | depth sees surfaces behind thin boards | CPU |
| 2-3 Nov | declined: eval-35-only camera guard; BootsTAPIR GPU arm; spoon-anchor re-evaluation | - | - | not run | - | threshold formed after seeing public scores; KLT condition unmet; eval-probing coin flip | $0 |

### 9.2 References and grip

| Date | Test | Hypothesis | Gate | Result | Margin | Why | Cost |
|---|---|---|---|---|---|---|---|
| 21 Oct | wrist IK cost 3.0 | stiffer wrist path tracks better | multi-seed gain | ep12 0.604 = floor (cup flipped) | -0.29 vs default | one seed; cup flips | small |
| 21 Oct | mid-wrist; hand separation | fix wrist and reset pops | gain | ep18 0.193 vs 0.381; ep24 0.231 = floor | falsified | not the limiting factor | small |
| 22 Oct | contact retargeting "k" as a blanket change | contact anchoring helps everywhere | both episodes gain | ep27 -0.031; others within noise | fails | narrows spread, not mean | ~$5 |
| 23 Oct | support fill; recovery drops | stable starts; drops are recoverable | gain | ep12 0.886 vs 0.910; 0.869 | -0.024 / -0.041 | not the bottleneck there | small |
| 24 Oct | grasp lock on settled ep18 | lock + fine-tune works | rising curve | 0.446 at 10M -> 0.060 at 70M | falls | training degrades the open-loop grip | small |
| 25 Oct | event-anchored windows T2 | grasp windows at events help | +0.05 on 3 of 4 | ep24 0.160 -> 0.058, others flat | fails | - | CPU |
| 25 Oct | grasp-type classifier | grip type label helps | gain | adds about 0 | - | timing, not type, is the limit | CPU |
| 1 Nov | two-hand references on eval | two-hand carry is closer to the human | swap rule | eval 14 0.603 vs 0.727; eval 16 0.713 vs 0.850 | -0.12 / -0.14 | public gain carried by one seed | GPU (lane) |
| 1 Nov | GRASP window optimiser (ep13) | GRASP beats our sampler | +0.05 | +0.024 (CI -0.071 to +0.115); test A 0.000 | -0.026 | the reference parked a hand; solver not the limit | CPU |
| 1-2 Nov | lift windows on evals 3, 14, 25, 28, 30, 32 | lift resets fix the failing phase | swap rule | e.g. eval 25 0.529 vs 0.878; eval 14 box 0.923 but fresh 0.826 | -0.05 to -0.35 | box draws overstate lift policies | ~$28 batch |
| 2 Nov | eval 16 hold-to-end | holding to the end helps | swap rule | 0.687 / 0.719 vs 0.769 / 0.792 | -0.08 | - | $3.5 |
| 2 Nov | eval 33 guard bridge | bridge the cup jump | +0.02 | +0.0196 | -0.0004 | just below the bar | in batch |
| 25-31 Oct | board slot rounds F-I4; carve F-I5 | slotted collision boards interlock | contact ratio 2.0; wall 1.5 mm | ratio 3.875; walls -21 to -173 mm | fails | collision budget and geometry | CPU |
| 22 Oct | rest settling on ep12 | settling resting objects stabilises starts | beat retargeting alone (0.790) | 0.740 (one seed) | -0.050 | one seed; kept as opt-in `SETTLE=1`, off by default | small |
| 22 Oct | primitive hand model | simpler hand collision helps | both episodes | ep18 0.377 +/- 0.021 vs 0.345 (+0.032); ep24 slightly below base (-0.015) | mixed | gain on one episode only | small |
| 23 Oct | anatomy closing rule (knuckles first, palm press) for the spoon | one rule for both spoon evals | both evals | eval 35 about 0.18 -> 0.52, eval 3 0.658 -> 0.429 | -0.23 on eval 3 | helped one eval, hurt the other | small |
| 23 Oct | opening fingertips first; 25-degree angled grip (eval 35) | cleaner release or hold | gain over 0.267 | 0.150 (replayed 3 times); 0.093 | -0.12 / -0.17 | pulling away dragged the spoon | small |
| 24 Oct | the 0.889 run's pinch used directly as a template; template-seeded search | copy the grip that worked once | beat the copied-grasp search (0.81-0.865) | 0.243 at zero action; search stayed at the template's 0.373 | -0.44 | not stated in the sources | CPU |
| 24 Oct | recovery training, early approach 15 cm, re-plan on a knocked brush (ep18) | fix the ep18 start or drops | gain over 0.30 | 0.22; 0.302; 0.22 | -0.08 to 0 | the grasp failure remained | small |
| 24 Oct | SETTLE start-overlap box | removing start overlaps helps | - | destroyed before running (~$0.2) | est. at most +0.002 | not worth it | $0.2 |

### 9.3 Policies and training

| Date | Test | Hypothesis | Gate | Result | Margin | Why | Cost |
|---|---|---|---|---|---|---|---|
| 21 Oct | route-A own meshes on ep18 / ep24 | own meshes work for training | no harm | 0.381 / 0.096 | harmful | wrist tracking fails | small |
| 21 Oct | stiff wrist kp 400 (ep18) | stiffer wrist follows better | gain | 0.193 vs 0.381 | falsified | - | small |
| 22 Oct | FDR rewards | object reward needs gradient | both episodes, both seeds | ep12 s43 0.762 below its baseline | rule not strictly met (adopted by owner) | seed spread | ~$10.4 |
| 26 Oct | eval 10 early checkpoints, ILC, zero-start, carve, glock | the floor is a policy problem | over 0.47 / 0.462 / 0.4539 | 0.446-0.465; 0.4459; 0.4532; 0.4539 | all below | contact overflow in training (found 31 Oct) | part of the 26-27 Oct batches |
| 26 Oct | seed races | early leaders win | - | glock leader wins only 22/38 | not adopted | coin flip for glock | CPU |
| 29-30 Oct | recipe arms B and C | curriculum scale or wrist damping helps | pre-registered | inconclusive (sd 0.14-0.20) | - | too few seeds | $14.45 |
| 30 Oct | scan masses S1 | true masses help | no harm | ep2 0.736 vs 0.944 | -0.208 | collapse after 20M on one seed | $8.70 |
| 30 Oct | own 22-DoF human hand | a human-like hand copies better | gain | -0.161 vs Sharpa | -0.161 | perceived fingers 25-40 % too short | CPU |
| 30 Oct | sampling-MPC robustness (CPU) | solved references are robust | jitter mean 0.586 | 0.556-0.564 | -0.02 | lucky trajectories of a chaotic system | CPU |
| 30-31 Oct | RL from solved references (G3); solver-RL loop | solved references train better | no harm; signal | ep2 harm (one seed); loop barely exercised | not credited | confounds | ~$13 |
| 31 Oct | recipe screen K / D / S / V | horizon, start randomisation, solved refs, velocity | pre-registered | -0.0018 / +0.049 (one episode) / -0.133 / -0.024 | inconclusive or negative | one re-run moved a cell by 0.07 | ~$30.15 |
| 31 Oct | command smoothing | smoother targets track better | +0.03 on 2 of 4 | +0.002 to +0.014 | -0.016 | undoes solver tuning | CPU |
| 31 Oct | mass transfer; Masses v2 | realistic masses transfer | +0.03 every episode | ep12 -0.013; v2 +0.0034, 1/4 | -0.043 / -0.027 | mass is second-order | $9.10 + ~$16.65 |
| 31 Oct | eval 10 V4p retrain | public gate +0.142 carries | swap rule | 0.459 vs 0.463, fails 10/10 | -0.004 | contact overflow still present | $3.25 |
| 31 Oct-1 Nov | targeted D arm, evals 14, 16, 25, 30 | start randomisation fixes variance | swap rule | 0.686 / 0.831 / 0.858 / 0.816 vs 0.727 / 0.850 / 0.878 / 0.897 | -0.02 to -0.08 | - | part of $19.41 |
| 1 Nov | pack 9b (eval 33 D draw) | +0.0018 proxy transfers | board gain | -0.0008 | -0.0026 vs proxy | below board noise | upload $0 |
| 1 Nov | eval 20 b1 pitcher collision | clean collision helps eval 20 | > 0.8933 | 0.8929 | -0.0004 | - | $2.14 |
| 2-3 Nov | retrains with new mesh collision: evals 20, 28, 30, 32, 33, 19 | new shapes help policies | swap rule, two hosts | 0.604 / 0.914 / 0.768 / 0.826 / 0.917 / 0.828 vs 0.926 / 0.919 / 0.897 / 0.890 / 0.923 / 0.929 | -0.006 to -0.32 | grasps were built on the old shapes; box-to-fresh drop | ~$36 + ~$11 |
| 3 Nov | evaluator-gap test | the patched training evaluator explains fresh drops | reproduce gap | 0.935 / 0.926 / 0.930 | not reproduced | cause unknown [H] | $1.1 |
| 30 Oct | widened blue-cup collision shape (eval 10) | a wider cup stops the clash | clash gone, no sinking | the beige cup sat about 5 mm off-centre, clashed on the same side in 60 of 61 frames; wider shape still clashed and let the beige cup sink about 11 mm with no hands | fails both checks | reference-side problem; led to corrected reference V4p | CPU |
| 30 Oct | PID on the soft wrist (CPU model) | feedback force fixes carry | stable, no push after release | hand jump after release 11-14 cm | rejected | unstable at strong gain, slow grip build-up | CPU |
| 30 Oct | eval 14 reshaped collision meshes | carve helps the hand-over | 0.645 | 0.617 +/- 0.236 and 0.579 +/- 0.099 | -0.03 | packed eval 14 stayed | - |
| 30 Oct | static freeze of non-moving objects | freezing helps ep11 | no-harm limit 0.002 | +0.07 on ep11 but harm 0.0023 | -0.0003 | fired on 20/20 static objects, never on eval 10 (the cup slides 4 cm) | CPU |
| 31 Oct | home-made smoother cross-check | smoother halves agree | same settings | the halves chose 16 mm and 8 mm; a 0.5-1.2 % gain came from a rotation smoothing too small to act | corrected | reported gain was an artefact | CPU |
| 22-31 Oct | declined or never run: 125M vs 250M A/B ($9-29); seed race ($12-23); domain randomisation GPU check ($1.5-2); wrist-gain study ($35-100); NVIDIA baseline rerun ($15-70); interruptible-only batches | - | - | not run | - | owner priority or preempted boxes | $0 |

### 9.4 Meshes and submissions

| Date | Test | Hypothesis | Gate | Result | Margin | Why | Cost |
|---|---|---|---|---|---|---|---|
| 22 Oct | mesh v5 spec | observation-first meshes win | no worse on 186 meshes | only lid, dust pan, pot pass; sweeper 0.510 with 6/6 flips | spec not adopted | fallback much worse | CPU |
| 23 Oct | library v4 flat boards | flat boards track | works | ep24 0.029 vs 0.795 | -0.766 | perception breaks | small |
| 25 Oct | library v5 (E2 at eval seeds) | v5 beats v2 | no worse | worse on 4 of 5 (rack 0.818 vs 0.555) | fails | - | $4.2 |
| 26 Oct | pack 5 lathe pitcher | single-twin +0.098 transfers | board gain +0.005 to +0.007 | -0.00115 (pitcher cost -0.0045) | -0.0095 | the hidden anchor and points differ | upload |
| 26 Oct | submitted-mesh carves; appendage-only meshes | carve the scored mesh | CD-O / AUC | lid +0.14-0.18 cm CD-O; appendage-only scores above the scan | rejected | a mesh beating the true shape compensates errors | CPU |
| 27 Oct | primitive boards | boxes with slots | flips 0 | 1/6 and 3/6 flips | fails | primitives add symmetry, symmetry flips | CPU |
| 29 Oct | generator batch 2 | one-shot generators beat library | Pixal3D median 0.08 below 0.40 | 0.399 | falsified | typical outputs far worse than best | $4.36 |
| 31 Oct | C0a, C2, C0b rack/cup/lid, E0b, T3 in C1 | other mesh routes | guard and CD-O gates | C0a rack -0.036; pitcher 1.160 vs 0.8742; rack 0.4413 vs 0.436; lid 16/16 builds fail | all fail | frame errors, unseen far side | ~$1.3 |
| 2 Nov | pack 12d on pose boards | (disclosed CD-O variant) | - | AUC -0.00733 | planned | T3 shapes register worse | upload |
| 2 Nov | 13f1 board-2 revert | the flip costs +0.02 | board +0.02 | -0.00034 | -0.020 | hidden scorer likely does not flip [I] | upload |
| 2 Nov | pack 13g (C4 audit) | any mesh passes rule A/B | rule A/B | none of 52 | empty | shipped meshes already best | CPU |
| 2 Nov | 13p2 pitcher placement | public +0.106 transfers | +0.004 to +0.006 | +0.00146 | -0.0025 | eval tilt smaller than public | upload |
| 3 Nov | 14p1 board 2 #43; pitcher G2 #29 | CV gains are real | source-excluded CV | generated from its own CV episode | held | leakage | CPU |
| 3 Nov | first 13j (outer shell, rack trim) | outer shells lower CD-O | -0.020 | -0.016 / -0.017 | -0.003 | - | CPU |
| 3 Nov | 13j for 3rd on CD-O | beat 0.23900 | 3rd place | 0.23856 beat it by 0.00044, but SRL moved to 0.20994 | 4th | competitor moved | $5.95 |

### 9.5 Patterns

Most failures were **small misses under pre-registered gates**, not disasters: physics fusion missed by 0.00002, the eval 33 bridge by 0.0004, the eval 20 retrain by 0.0004, GRASP by 0.026, the room map by 0.007. Run-to-run noise (about 0.0012-0.0015 per public episode, 0.07 per training cell) set the gates, and the gates held. Four themes repeat:

1. **Bias, not noise.** Every smoothing, filtering, re-weighting or "second sensor" idea failed because the remaining error was a constant offset, a tilt or a template error that those methods cannot see.
2. **The tracker is fragile to its inputs.** Template, depth, mask and iteration changes all broke whole tracks somewhere.
3. **Policies are tied to the shapes they were trained on.** New collision meshes broke 6 of 7 retrains, and box draws overstated fresh draws.
4. **Single-twin or single-seed wins do not transfer.** The lathe pitcher, the two-hand public gain and the lift-window public gain all rested on one twin or one collapsed control seed.
