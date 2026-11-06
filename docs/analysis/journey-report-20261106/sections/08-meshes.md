## 8. Meshes, collision geometry and CD-O

A mesh does three jobs in this project, and the best mesh for one job is often not the best for another:

1. **Tracking template**: FoundationPose needs a mesh to track an object (section 5).
2. **Submitted mesh**: the kit scores it for CD-O and, since about 21 Oct, also registers it to the hidden scan before scoring the poses (section 3). So the submitted mesh moves all six boards.
3. **Simulator collision copy**: the physics engine needs convex pieces to simulate contacts. Only the simulator sees this copy.

CD-O numbers below are in cm, computed by the kit's Chamfer distance after a Sim(3) fit (scale, rotation, translation) against the public scan of the same object type, unless marked otherwise. Public-scan scores are [D] (they use ground truth for scoring, never for inference).

### 8.1 Rules: route A and disclosed GT-informed choices

- **Route A (owner, 21 Oct 13:20):** eval episodes use only our own meshes; public scans are a development aid. The FAQ says participants "should reconstruct the objects ... and submit their own reconstructed meshes". Libraries v1 and v2 had used public scans as helpers, so library_v5 was rebuilt from our own meshes (22-23 Oct). The owner also asked to rebuild meshes per eval episode from its own video (22 Oct 11:20).
- **GT-informed selections (2-3 Nov):** from pack 12c on, some meshes were chosen as "best of many candidates by public-scan CD-O". The candidates were made without ground truth, but the choice used public scans. The owner approved each step ("Okay I give you permission for all", 19:00 UTC 2 Nov) and every upload description discloses it. Section 12 lists the integrity rules.

### 8.2 Early pipelines (12-27 Oct)

| Pipeline | What it is | Key result |
|---|---|---|
| TSDF fusion (`recon_mesh.py`) | fuse FoundationStereo depth along our own tracks | ep41 pot: AUC 0.9979 vs 0.9985 with the scan; CD-O 0.564; registration rotation 1.12 degrees. v5 (`--close auto`): ep41 0.998, ep23 0.997 with no flips, ep39 dust pan 0.880 |
| Library v1 (21 Oct) | own meshes, scans as helpers | registered AUC ours vs scan: ep41 0.987 / 0.999, ep24 boards 0.864 / 0.840; sweeper flips 0.12-0.25 |
| Library v2 | pot and dust pan with `--below_carve` | lowest point vs table -3.3 to -5.5 cm -> -0.2 to -0.6 cm; pot CD-O 0.58 -> 0.44; dust pan 0.52 -> 0.33 |
| Library v3 | flattened sweeper base (`flatten_base.py`) | the sweeper could stand; ep18 policy 0.715 +/- 0.240 vs 0.368 with the round base |
| Library v4 | flattened boards | ep24 perception 0.029 (v2 0.795): unusable |
| Library v5 (25 Oct, about $4.2) | observation-first pipeline | pot, lid, boards failed to build; E2 test at eval seeds worse than v2 on 4 of 5 (rack 0.818 vs 0.555, sweeper 0.526 vs 0.316): not adopted |
| Beige cup v5 -> library_v3x | fused on the re-tracked ep11 | CD-O 0.730 vs 0.856, 0 flips; ep11 twin 0.525 -> 0.570; used on evals 8 and 10 |
| Lathe from observed points (26 Oct) | revolve the observed profile of round objects | blue cup 0.523 -> 0.364 (ADD 10.0 -> 4.7 mm); pot 0.437 -> 0.468 (worse); library lathe cup 0.307, pot 0.319 |
| Pitcher lathe (library_v3p) | complete the pitcher's missing base | public ep21: ours 0.776, lathe 0.874, scan 0.907; on the board it cost -0.0045 AUC (packs 5 and 6) |
| Arc foot (eval 20) | a curved foot so the pitcher stands | ep21 twin 0.6565 +/- 0.093 -> 0.7723 +/- 0.009 (pitcher 0.414 -> 0.591): adopted in pack 3 |
| Primitive assembly (27 Oct, pre-registered) | build pot, lid, rack, boards from simple shapes | pot 0.342 (library 0.437) PASS; lid 0.219 (0.421) PASS; rack 0.454 (0.555) PASS; board 1 0.189 but 1/6 flips FAIL; board 2 ADD 78.7 mm, 3/6 flips FAIL |

The primitive fits had a leak: wall and lid thickness and the rack lean were taken from the scans. A clean-up grid of {1.5, 2.5, 4.0} mm was then pre-registered; the shipped lid and rack used 2.5 mm (lid CD-O 0.220, rack 0.456). An automation audit (27 Oct) found that about a third of the fitter code is object-specific, and that a fitter run on the wrong object returns a clean but wrong mesh in 23 of 26 runs.

An eval mesh review (26 Oct, 36 pairs, visual, GT-free) ranked the problems: blue cup, white pot, dish rack, beige cup, pitcher, dust pan, sweeper, board 1, lid, board 2. The spoon template looked good.

### 8.3 The CD-O sprint (29 Oct - 3 Nov)

The 31 Oct rank-sum check showed CD-O at 18th of 20 (section 2). From then on, mesh rounds were run under frozen rules: a pre-registration file, a SHA256 freeze of all candidates before any scan was read, one scoring per mesh, an AUC guard on public twins (mean change at least -0.005, minimum at least -0.02, RPE and MPPE at most +0.2 cm worse), and later the D1 no-flip gate (0 of 6 flips in both raw-scan and budget-mesh reference modes). Adoption rules A/B/C are described in section 10.

| Round | Candidates | Result | Adopted? |
|---|---|---|---|
| Generators batch 2 (29 Oct, $4.36) | 104 one-shot scorings | mean CD-O over 10 objects: library_v3 0.477; SAM 3D 0.501 (beats library on 6/10); Pixal3D-MV 0.490; Hunyuan3D-2.1 0.602; TRELLIS.2 0.594; TripoSG 0.984. Best-of-all oracle 0.315. GT-free selector Spearman 0.46 | nothing |
| C0 (31 Oct) | primitive kits for pot, lid, rack, blue cup | public: pot 0.437 -> 0.342, lid 0.421 -> 0.220, rack 0.555 -> 0.456. AUC guard (51 runs, 15 twins): pot +0.0030, lid +0.0055, rack +0.0158, blue cup +0.0241 | pot, lid, rack in 9a+; blue cup held for selector integrity, shipped in 12c |
| C0a | C0 rigidly aligned to library_v3 | rack +0.0158 -> -0.0046 | no: the rotation was library_v3's own frame error |
| C1 (31 Oct) | beige cup observed lathe; dust pan placed pick | beige 0.856 -> 0.248 (eval 10), 0.730 -> 0.255 (eval 8), 0/32 flips; dust pan 0.331 -> 0.260 | yes, flagged provenance, in 9a+ |
| C0b (31 Oct) | scan-free rebuild | pot 0.3924 and beige 0.30 adopted as fallbacks; lid failed 16/16 builds; rack 1.632, cup 1.677 failed the guard. Audit: 163 constants, 16 scan-derived, 71 unknown | partly |
| E0 / E0b | eval-built meshes | in-sample fidelity only; E0b less accurate than 9a+ | no |
| C2 | pitcher observed lathe; rack parts | pitcher 1.160 vs gate 0.8742 (falsified); rack parts 0.4413 vs gate 0.43604 | no |
| Tier A / T3 (12d) | pre-registered generate-then-fit pot and pitcher | pot 0.3417 -> 0.3112, pitcher 0.894 -> 0.723 [D]; board CD-O 0.30008 -> 0.29029 but AUC -0.00733 | CD-O board only |
| G2 (2 Nov, $8.31) | 264 meshes (SAM 3D 88, Hunyuan 88, TRELLIS.2 88); 50-seed audit of 32 | pot sam3d 0.2861 vs 0.3107 (ADD 2.7 vs 6.3 mm); blue cup 0.2335 vs 0.2646; rack hy21 0.4016 vs 0.4182; no pitcher passed | yes, 13h (CD-O variant) |
| Tier B (2 Nov, owner yes) | best existing meshes by public-scan CD-O | pitcher hy21 0.3722 (ADD 15.8 mm, 0/31 flips); rack, sweeper, boards; board-2 plate flips in 34 % of 50 seeds | yes, 12e |
| Tier B+ | sam3d blue cup, hy21 dust pan | passed C3's 0.02 public-scan rule | yes, 13f |
| C4 audit (52 meshes x 50 seeds) | everything on disk | none passes rule A or B; the shipped meshes were already the best existing | 13g empty |
| G3 (3 Nov, $7.47) | 432 single-image + 36 Pixal3D-MV; 79 audited | pot trellis2 0.2399 vs 0.2861; dust pan Pixal3D-MV 0.2064 vs 0.2291; board 1 hy21 0.1593 vs 0.1872; rack 0.3934 (-0.008, too small); board 2 #43 failed the anchor rule (5.50 > 5.46 mm) | yes, 13i (CD-O variant) |
| Outer-shell / rack trim | extract the outer shell of generated meshes | rack trim -0.016 / -0.017 vs the -0.020 bar | no (first 13j attempt empty) |
| Rack round R (3 Nov, $5.95) | 120 rack candidates | hy21 ep12 k18 s31337 t3fit: 0.3775 vs 0.4016 (-0.0241), anchor 3.07 vs 3.78 mm, D1 0/6 | yes, 13j |

**How CD-O is made up.** The board is a flat mean over 36 (episode, object) pairs; 10 are spoon pairs with no public scan. Board 0.402 was about 0.18 for the spoon pairs [E] plus 0.491 for library_v3 over the other 26 pairs. From 9a+'s 0.33234 the implied spoon mean is (0.33234 x 36 - 10.156) / 10 = 0.181 [E]. So the spoon, a third of the pairs, was never the problem; the other objects were.

**Prediction accuracy.** The public-scan estimate predicted every CD-O upload within about 0.0007 cm: 9a+ 0.333 -> 0.33234; 12c 0.300 -> 0.30008; 12d 0.290 -> 0.29029; 12e 0.267-0.268 -> 0.26775; 13h 0.252 -> 0.25159; 13i 0.242 -> 0.24177; 13j 0.2384 -> 0.23856 (eval-seed spread +/- 0.002).

### 8.4 Meshes as a pose lever

Reading the kit scorer (2 Nov, about 19:40 UTC) explained why mesh changes moved the pose boards: `_register_object_body` registers our mesh to the hidden scan by trimmed ICP from 25 starts and converts our poses through that registration. A registration error of 2-4 degrees, or a flip on flat near-symmetric objects, enters every frame. Earlier signs had been there: the 21 Oct damaged-scan test (5 mm inflation 0.987 -> 0.608), and 12c, where library_v3's blue cup registered 9-10 mm off the anchor against 2-3.6 mm for C0 (+0.00333 AUC).

| Change | Effect on pose boards [M] |
|---|---|
| Tier B, 12e vs 12d (10 mesh rows, no pose row changed) | AUC +0.02900, RPE -0.75081 cm, MPPE -0.57191 cm, +1 SP-SR and +1 MP-SR episode; rank sum 54 -> 47 |
| Pose-CV meshes, 13p vs 13f1 (TSDF pot on 6 evals, library_c0 rack on 5) | AUC +0.01066, RPE -0.14853, MPPE -0.10157 |
| Pitcher placed from its own depth, 13p2 vs 13p | AUC +0.00146 |
| CD-O-chosen meshes, 13h / 13i / 13j vs 14p | AUC 0.88001 / 0.87593 / 0.87648 vs 0.88571 (G3 pot ADD 6.8 mm vs 2.7 mm) |

The lesson: a mesh chosen for scan Chamfer is not the best mesh for registration. Pose-board meshes were therefore chosen by a pre-registered public leave-one-episode-out pose CV with 10 registration seeds (round 1 held-out gains: TSDF pot +0.0206 with 9/9 episodes at or above zero, rack library_c0 +0.0234, pitcher 12c +0.0121, board 2 12c +0.1274). Two later picks were rejected for leakage because the generated mesh came from one of its own CV episodes (pitcher G2 #29 at +0.1125, and board-2 G3 #43 at +0.0053 in pack 14p1).

**Registration flips (D1).** The Tier B board-2 occupancy plate flipped 179.18 degrees against the raw public scan but registered at 1.05 degrees against the budget mesh (2 of 10 seeds flipped). Reverting it in 13f1 was expected to give +0.02 AUC and gave -0.00034, which suggests the hidden scorer does not flip it [I]. D1 was kept as a veto anyway. On the board-2 variants (C4, 50 seeds), a 12.5 mm slab cut the flip rate W30 from 0.34 to 0.12 at about 0.05 cm CD-O cost; library_v3 never flips but scores 0.2169.

**Single-twin mesh swaps fail.** The lathe pitcher gained +0.098 on its one public twin and lost 0.0045 on the board. After that, a mesh swap needed at least two twins or a reference-free argument.

### 8.5 Collision copies and carving

The convex decomposition (CoACD) fills slots and cavities. An interaction census (22 Oct) found boards without interlocking notches (a 10.8 cm3 column in ep23 and ep24), a 20-25 cm3 ring for the lid on the pot, and 42.7 cm3 for nested cups; CoACD refills the slot (16.9-17.0 cm3 hull overlap). So collision geometry, not the visual mesh, blocked interlocking and nesting.

| Work | Result | Verdict |
|---|---|---|
| Uncoloured simulator copy (21 Oct) | Newton split a colour-coded board into 174 pieces and CoACD ran past 10 min | fixed: scene build 4.2 s |
| Carved collision copies, pack 4 (eval 10 cup cavity, eval 25 board slots) | +0.02163 AUC with the submitted meshes unchanged [M]; eval 25 carve s42 0.7919 +/- 0.103 | adopted |
| Eval 10 hybrid cup collision copy | rest 0/6 falls (old beige cup 6/6 falls, 46-89 degrees); driven nest 0.44 cm / 2.5 degrees vs 4.45 cm / 8.6 degrees | the stacking policy still did not learn (0.4532 +/- 0.003) |
| Cavity-safe ev10cs4/cs5 (1 Nov) | packed overlap median/max 11.9 / 32.7 cm3 -> 0.21 / 2.61 cm3; 0 contact overflow lines | pack 10 (+0.00158) |
| Eval 14 carve (cup into rack) | s42 0.617 +/- 0.236, s43 0.579 +/- 0.099; rule needed 0.645 and sd 0.199 or less | not adopted |
| Eval 30 carve | sweeper fell through | dropped |
| Board slot rounds F-I4 (31 Oct - 1 Nov) | round 3: 5 slotted boxes per board, ep24 carves pass, but the contact-gate ratio 124 / 32 = 3.875 > 2.0 | not frozen; eval 25 kept its carve |
| Collision carve F-I5 (owner waiver for any colliding pair) | round 1: all ten objects fell to 6 mm boxes keeping 1.8-9.3 % of the body; round 2: wall check failed (min wall -21 to -173 mm) | nothing delivered |
| Rack-slot candidates (evals 30, 14) | the guest mesh sits inside the rack at every rest frame (eval 30: 22/22, 6.2 cm3 median); candidates empty the slot but throw the sweeper | none passed |
| New meshes as collision in retrains (3 Nov) | 1 of 7 retrains passed (eval 14 in 14p); eval 20 0.293 / 0.604 vs 0.926; eval 19 0.828 vs 0.929 | see section 7 |

Physical facts that limited the collision work: there are no measured object properties (all masses a 0.3 kg placeholder until the realistic-mass study), friction is one global 1.0, and the real boards are 8.5 mm thick against 2.7-3.1 cm in our meshes.

### 8.6 More from the chat sessions

- **Own versus scan meshes, first look (21 Oct, registered AUC, Kaggle-style):** pot 0.998 against 0.999; boards 0.992-0.997 against 0.999; dust pan 0.953 against 0.997; cup and pitcher 0.917 against 0.975 [D]. The route definitions at the time were A-lite (2-3 days, scans only as a development aid on public videos) and A-strict (5+ days, no scans at all); the owner chose route A (section 8.1).
- **False bottoms (21 Oct):** the dust pan came out 3.5 cm and the white pot 5.5 cm below the table, because the camera never sees the underside of a resting object. The ep18 brush was reconstructed with a closed, rounded underside: it touched the table on 0.3 cm2 with its centre of mass 3.3 cm outside that patch and fell in about five steps. The flattened underside (library_v3) fixed the stand; the 0.889 run combined flattened underside, settled start and 250M steps.
- **Do the organisers' meshes matter for training? (22 Oct):** on ep24, own meshes scored 0.307 (seed 42) and 0.306 (seed 43), mean 0.307; the organisers' meshes 0.389 and 0.245, mean 0.317. The agent's conclusion: "it's not the mesh". A CPU round over 186 mesh variants found that mesh polish barely moved the metric; mesh rebuilding gave small, risky gains [D].
- **Pack 9a and its provenance flag (31 Oct):** the pot, lid and rack carried marker-ball radii from a fallback `MK_R0 = 7 mm` and a fit window of 5-9.5 mm, both traced to the public scans (`prim_potlid.py`, marked "SCAN-DERIVED"); shipped balls were pot 7.00 / 7.00 / 7.00 / 6.94 mm, lid 7.00 mm, rack 7.00 and 5.22 mm, plus the disclosed 2.5 mm walls. The effect was judged small [H]; the AUC guard on 15 public twins (51 runs) gave mean +0.0079, minimum -0.0092, RPE -0.121 cm. The owner said "Ship 9a, flagged." and the README carries the flag text. The pack-10 clean rebuild audited every constant by origin (generic, own observation, scan-derived, unknown).
- **9a+ signed off with flags (31 Oct 17:15):** the beige cup on real public registration had a total rotation of 4.04 deg and an anchor shift of 0.47 cm (almost all free spin about the symmetry axis); 32-seed metric max 3.5 deg, 0 flips; end-to-end on ep11 the beige cup went 0.933 -> 0.949 (episode +0.008). Eval 8 was only a conditional yes (no public twin). Provenance flags written out: the lathe tool was developed in a loop that read public scans, with a 3 mm wall fallback, a floor rule, a minimum thickness of 1.5 mm and a tie factor, and its configuration was chosen after blue-cup scoring; the dust pan was a SAM 3D output placed by a GT-free ICP and picked by a GT-free metric (Spearman 0.46 against scans, measured after scoring). The board estimates by the mesh session [E]: pack 9a 0.3667, 9a+ 0.3327, beige on eval 10 only 0.3459; measured for 9a+: 0.33234.
- **Rotation and scale (31 Oct 16:02-16:16):** the leaderboard rescales our mesh to the true object size before scoring, so scale cannot cost points. The rack's 2.3 degree rotation against the old mesh was tested both ways: rotated back, the pose rows were -0.005 average and -0.036 worst (would fail the check); as fitted, +0.016 average and -0.009 worst. Decision: as fitted; the rotated-back versions were kept as a fallback. The offline imitation of the scorer flipped the near-symmetric lid by about 162 degrees, which the builder judged an artefact.
