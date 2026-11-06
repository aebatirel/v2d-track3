# Digest: merged work log, part 4 (30 Oct to 3 Nov 2026)

Source: `corpus/worklog_part4.md`, read in full. Tags [M] measured, [D] diagnostic/public-only, [E] estimate, [H] hypothesis, [I] interpretation, as the log uses them. Times are the log's; from about 20:00 UTC on 31 Oct the session clock ran ahead, so git times are authoritative.

## Perception (depth, detection, identity, tracking, hands, room map, point tracks)

- **Room map (2 Nov, $0).** GT-free public-only map; all 20 eval clips relocalised (min 479 inliers). Perc2 camera vs map: object gap p95 2 to 9 mm on 19 of 20 clips. Camera-term AUC bound mean 0.0029; pre-registered G1 (at least 0.01) failed, so retrains stayed off. Public leave-out (19 eps): mean dAUC +0.0070, dMPPE -0.081 cm; ep24 +0.148, others about -0.0008, ep22 -0.016; G1 and G2 fail. Not adopted.
- **Half-frame lag (31 Oct to 1 Nov).** Measured perception delay 25 to 28 ms (median 0.50 frame over 20 episodes). Half-frame advance (S2) beats baseline on 32 of 33 objects (ADD -4.4 %). Adopted; later added to the eval-10 V4p chain, not in any packed reference as of 2 Nov.
- **Smoothers.** Roman's causal Kalman: +1.3 to +7.8 % worse. Offline RTS -0.7 %; zero-lag RTS -1.5 % (-5.1 % with S2, tuned on public). Position-only RTS refine S13 (31 Oct, gate mean dR at least +0.005): -0.00011, 9 better / 7 worse. FAIL, unused.
- **ep23 identity swap (2 Nov).** Frame-0 alignment hid a board swap; applying `identity_fix` on CPU lifts ep23 AUC 0.041 to 0.663, about +0.031 on the public mean. Eval 25 already uses the identity-correct reference.
- **Point tracks (2 Nov, $0).** BootsTAPIR/KLT points lifted by stereo depth. PT-lag dAUC -0.058 (0 better, 6 worse; min ep42 -0.366). FAIL.
- **Perception-tracking public tests (2 Nov, all FAIL).** Mask-guided tracking -0.0009; mask-restricted depth -0.0077; full-resolution stereo depth -0.0079; complete-base pitcher template -0.249; Stage-1 rest-segment depth fit -0.0088 (7 better, 12 worse). Test A, mesh placement from depth: +0.0026 (10 / 9; min ep18 -0.137). Tracker defaults score 0.945 on 19 public eps vs 0.921 for the 25 Oct base [M].
- **Pose-board mesh CV (2 Nov, leave-one-episode-out, 10 seeds).** PASS: white_pot to TSDF pot +0.0206 (9 of 9 at least 0); rack to library_c0 +0.0234; pitcher to 12c +0.0121; pitcher placement from depth +0.1064 (ep21 +0.133, ep22 +0.080). FAIL: blue cup, sweeper, dust pan, lid, board 1. Result: pose pack 13p. Round 2 (3 Nov) and round 3 passed only single candidates whose source episodes were in the CV set; held.
- **Bias calibration H1 (3 Nov; owner "yes to bias calibration").** Pitcher passes (+0.046 to +0.028; GT-free depth placement +0.106). Pot -0.002, rack -0.003, cup -0.035, lid -0.002; sweeper -0.20, dust pan -0.11, boards -0.38 / -0.19. Systematic-bias hypothesis falsified except pitcher and lid. No eval use.
- **Hand-aware lane (3 Nov, $0, closed).** Held frames carry 61 to 70 % of the AUC loss [D]. Rigid-in-grasp with hands: FAIL (dAUC -0.12 to -0.79 replacing the track). Held-phase error lies along the camera ray (ep18 sweeper up to +14 cm). Oracle ray ceiling +0.0195. Hand-masked ray correction: dev +0.0045 mean over 7 (single seed); holdout (13 eps, 10 seeds) mean -0.0042 (noise 0.0015), worst ep24 -0.047 (board shifted about 21 cm). FAIL.
- **Eval gross-failure audit (3 Nov, box H about $1.5).** No gross reference failure. Moderate: eval 32 cup about 4 cm (f18 to 25); eval 33 cup 4 to 5 cm (f87), spoon 5 to 8 cm (about f186, f263). Spoon flip check: no clear 180-degree flip in any packed reference.
- **Instance-pose pot network (3 Nov, about $0.8).** dAUC rendered-only -0.065 mean (ep27 -0.257); with mocap fine-tune -0.0085. FAIL.
- **Twist.** GRASP's canonicaliser is worse on 5 of 6 cups; a rest-only form improves 6 of 6 (ep13 74.6 to 57.7 degrees), AUC-neutral. Leaderboard is symmetric for cups, so twist costs only the proxy and physics.

## Policies and following (RL training, recipes, retrains, sim, seeds, flips)

- **Recipe screen (31 Oct, determined-wright; about $30.15 in six boxes [E]).** K inconclusive (-0.0018). D inconclusive (mean +0.049; sd falls on ep12 only). S no signal (min -0.133). V (actor sees object velocity, $7.02) inconclusive, mean -0.024 (ep2 -0.049, ep12 -0.026). No recipe change.
- **Command smoothing (31 Oct, test A, needs +0.03 on 2 of 4).** GL +0.002 to +0.014; SOL -0.027 to +0.014. FAIL.
- **Masses (31 Oct).** 0.3 kg vs realistic (run 20261031-mass-2ed46ea, $9.10): ep2 +0.157 (SE 0.105), ep12 -0.013; rule needed +0.03 on every episode. NOT ADOPTED. Masses v2 (4 eps, 31 Oct 23:33): mean +0.0034, 1 of 4 positive. NOT ADOPTED. One overnight summary line says "realistic masses adopted (+0.090)", which conflicts with this record; unresolved here.
- **Re-track (31 Oct, $1.54).** Per-episode mesh templates: mean dR -0.170, 3 of 20 positive, min -0.973 (white_pot template, ep45 0.9795 to 0.0063). FAIL.
- **Eval 10, V4p retrain (31 Oct, run e10v-caf38fb, 2 seeds, $3.25).** NO-SWAP: 0.4593 vs 0.4632 (V); both fail 10 of 10. Beige cup never lifted. Training logs: about 6.0 M and 5.8 M "nefc overflow" lines per seed.
- **Contact budget (sim=rl: nconmax 256, njmax 512 per world).** Eval 10 packed pieces: sampled nefc max 536, 13 % of world-steps over 512. Packed run: 8,368,544 overflow lines in training, 0 in its 5 scored draws. Training is corrupted; scoring is not (50 stored draws, 0 lines). Other evals: 33 about 21 k, 32 about 20 k, 14 about 4.6 k, rest 0 to 1.2 k [E, file sizes].
- **Eval 10, njmax-1024 diagnostic (owner "Okay go", 1 Nov 02:43; run e10nj-451b82d, $2.06; PREREG 086de63).** Overflow 0 (bar 1,000); beige lift max 23.9 cm (bar 5 cm); official sim_vs_ref vs V 0.913 (n 10, 0.869 to 0.933). Stock 512/256 readout of the same checkpoint: 0.9034 vs V (-0.0095). SUPPORTED. Diagnostic only, never packed without owner ruling.
- **Eval 10, no-overlap pieces (ev10cs4, then ev10cs5 with 8 mm floor plate).** Budget at 32 by 60: 0 overflow lines, max 448 (cs4), 503 (cs5). Known trade: blue kept volume 0.384 vs 0.80 gate, disclosed. Retrain (run e10cs-50c2d90, seed 43, $2.85, 1 Nov): vs V 0.5322 +/- 0.0615 vs packed 0.4632 +/- 0.0067 (+0.069); vs P +0.059; median RPE 13.94 cm; fail rate still 10 of 10. Overflow 992 (s42) and 660 (s43). Beige lift s42 239.8 cm was flagged as implausible. SWAP-ELIGIBLE, INCLUDE into pack 10.
- **Pack 11 (eval 10 trained at njmax 1024, scored at stock 512/256).** Owner "I give give you go" (09:11), sha-specific guard exception (11:40). vs V 0.9034 vs 0.5322 (+0.371); fails 0 of 10 vs 10 of 10. INCLUDE. Weights byte-identical to the 1024 checkpoint; stock config verified.
- **Eval 20 pitcher collision (b1, 41 pieces, clean budget).** Retrain (run e20b1-4207ce4, $2.14): s42 0.7861 +/- 0.147, s43 0.8929 +/- 0.036; bar above 0.8933, missed by 0.0004. Overflow 1,236 and 1,334 lines. NO-SWAP.
- **Eval 14 and 32 track-guard bridge (2 Nov, perfect-following).** A 19 cm one-frame cup jump removed. Eval 14 fresh 0.875 vs 0.706 packed; fails 1 of 10 vs 4 of 10. Eval 32 0.890 vs 0.851. Both in pack 12.
- **Eval 16 right-hand freeze (2 Nov, GT-free).** Hand held on spoon from f107. Fresh draws 0.974 vs 0.850; fails 0 vs 0; median RPE 1.18 vs 1.79 cm. Same-box control without freeze 0.769 and 0.787. Pack 12b.
- **Two-hand references (1 Nov, public ep13 and evals).** Public ep13: two-hand 0.587 / 0.553 vs single 0.378 / 0.554 (seed 43 at the floor). Eval 14 two-hand 0.603 vs 0.727; eval 16 0.713 vs 0.850. NO-SWAP on evals.
- **Lift-window starts (plw, 2 to 3 Nov).** Public ep31 PASS (0.730 and 0.704 vs control 0.589). Evals 3, 25, 28, 14 NO-SWAP (for example eval 25 0.529 / 0.541 vs 0.878). Eval 20 seed 43 fresh 0.926 vs 0.893 PASS (pack 13). Eval 15 near miss (fresh 0.958 vs 0.906; clause c off by 0.47 mm), accepted by owner waiver (pack 13b). Reading [H]: box draws overstate lift policies.
- **Mesh-collision retrains (2 to 3 Nov).** Zero-shot with Tier B collisions: eval 20 0.451 vs 0.926 (retrain then s42 0.293, s43 0.604, NO-SWAP); eval 28 0.906 vs 0.919; eval 30 0.829 vs 0.897. Eval 14 p0m seed 43 fresh 0.933 vs 0.875 (+0.058) PASS, pack 14p. Eval 30 NO-SWAP on fresh draws 0.768 vs 0.897 (fails 5 of 10 vs 1 of 10; box 0.938 and 0.932). Evals 32, 33, 19: zero swaps (0.790, 0.917, 0.828 vs 0.890, 0.923, 0.929).
- **Evaluator-gap test (3 Nov, pfgA, about $1.1, pre-registered).** NOT REPRODUCED: eval 30 sm 0.935 / 0.926 / 0.930 across box, pristine kit and patched-off tree. Two-host confirmation adopted for future swaps.
- **SR audit (3 Nov).** All 20 stored 14p rollouts pass SP-SR and MP-SR against our references. Worst MP margins: eval 10 beige 1.85 cm; eval 30 sweeper 1.82 cm / 11 degrees.
- **GRASP-style sampler, ep13 (1 Nov, CPU, $0).** Test B (two-hand vs single rebuilds): d_b +0.024, 95 % CI [-0.071, +0.115], 9 of 16 wins; bar +0.05; FAIL. Test A: 0.000; FAIL. Jittered means: P2 anneal 0.3935 +/- 0.146, P2 GRASP 0.4176 +/- 0.166, O2 anneal 0.6507, O2 GRASP 0.6241; floors 0.5561 (perceived) and 0.5727 (oracle). Falsified at this budget.
- **Hold-filter repair (1 Nov, pre-registered on 4 episodes).** M1 accuracy +0.0017 (holds); M2 followability -0.018 (needs +0.02). FAIL.

## Grasp and references (contact labels, reference building, lift windows, grip)

- **Single-hand locks.** `grasp_lock.py` keeps one carrier. ep13 twin references park the left hand at z 57.0 cm for all 190 frames while the cup rises 9 to 12 cm by f30 to 40. Eval 14's packed reference is also single-hand (left carries f18 to 118); the human hands over at about f40 to 46, matching the measured eval-14 failure onset (f42 to 45 in 7 of 10 draws). Reading [I]: "control-limited" may be "construction-limited".
- **First-picker lock (ep13).** Oracle O1F 0.672 +/- 0.062 vs O2 0.604; perceived P1F 0.323. With perceived motion every construction stays below floor.
- **Support fill, eval 19 sweeper (1 Nov).** Hands-free f0 settle 90.2 mm / 88.8 degrees, 16 of 16 falls; after `support_fill` 0.01 mm / 0.01 degrees. Certified by pre-registered gate; not yet retrained.
- **Eval 20 pitcher b1 clip.** Settle at f0 195 mm / 94.6 degrees becomes 8.5 mm / 3.2 degrees. f192 hands-off falls in both sets (b1 12.0 cm / 50 degrees vs packed 6.8 cm / 28 degrees): flagged risk.
- **Hands in replay (rest probe, 1 Nov).** Hands-replay vs parked: eval 5 pot 25.7 vs 3.3 mm; eval 8 pot 41.7 vs 8.9 mm; eval 33 spoon 87.0 vs 10.6 mm. Evals 5, 8, 33 already score 0.94 to 0.97; no rebuild.
- **Eval-10 nest.** Packed pieces overlap at the nested rest (median 11.9 cm^3 in plain MuJoCo). Nest test with ev10cs4: beige tracks blue nest at 0.14 cm median vs 1.02 cm packed.
- **Ep24 boards (P1, 31 Oct).** FAIL for carved and default: drift 3.7 / 3.2 cm (carved), 3.2 / 3.2 cm (default); limit 1 cm. Cause [H]: reference holds the assembled cross 27 to 36 mm above the table.
- **Eval 25 board slot (1 Nov).** Round 3 passes physics on public ep24 but fails its ratio clause (3.9x vs 2x). NO; `meshes/carve/ev25` kept. Tracked board pose 9.8 mm / 2.5 degrees off the packed reference.

## Meshes and CD-O (templates, scans, registration, mesh tiers, mesh adoption)

- **Pack 9a+ meshes (31 Oct).** Pack 8 plus C0 pot, lid, rack (guard mean dAUC +0.003 / +0.0055 / +0.0158, 0 failures), plus C1 beige cup on evals 8, 10 and C1 dust pan. CD-O 0.40188 to 0.33234. Blue cup held back: selector written after scoring.
- **Blue cup (C0).** Owner "For blue cup I give you mey yes" (2 Nov 08:10). Pack 12c, transform none (axis 1.24 degrees, offset 2.0 mm). CD-O 0.33234 to 0.30008. Flags (ICP 6.64 mm, proxy 9.91 mm) attributed to library_v3's own offset.
- **Tier A (generate-then-fit, pre-registered).** White_pot t3fit [D] 0.3417 to 0.3112; water_pitcher t3fit 0.894 to 0.723. Pack 12d: CD-O 0.29029, but pose boards worse (AUC 0.84005).
- **Tier B (GT-informed best-of-N; owner permission 2 Nov 19:00).** Pitcher hy21 s42 (scored [D] 0.3722), sweeper P1, rack ep31_full, wooden pieces, plus blue cup sam3d s7 and dust pan hy21 s42 in 13f. Pack 12e: CD-O 0.26775, best on every board. Flip: wooden_piece_2 at eval 25 slot 1 registers 179.9 degrees in the kit proxy; the earlier "eval seed does not flip" sign-off was wrong. Reverted in 13f1 (0.7 degrees).
- **D1 flip gate.** C4 50-seed audit: shipped 13f flips on board 2 wooden_piece_2 (34 % of seeds), wooden_piece_1 6 %; all else 0 of 50. D1 (0 flips at eval seed and at least 6 seeds, both reference modes) adopted as veto. Raw-scan flip 179.18 degrees; under budget reference 3 of 10 seeds (not the eval seed). Hidden scan presumed to behave like the budget reference [I].
- **G2 generation (bold-albattani, $8.31, cap $25).** 264 meshes, SHA-frozen before scan reads. Rules: (A) CD-O -0.020 with W30 at most +0.05; (B) W30 -0.20 with CD-O at most +0.005; (C) G2 only: ADD -2 mm, CD-O at most +0.005. Of 52 candidates audited, none passed A or B. Winners: pot sam3d ep44 (CD-O 0.2861 vs 0.3107), blue cup sam3d ep22 (0.2335 vs 0.2646), rack hy21 ep31 (0.4016 vs 0.4182). Pack 13h: CD-O 0.25159 (rank 5).
- **G3 generation (bold-albattani, $7.47).** 468 meshes; 79 stage-2 copies audited at 50 seeds. Pot trellis2 ep45 0.2399 vs 0.2861 (ADD 6.8 vs 2.7 mm, CD-O pack only); dust pan Pixal3D ep39 0.2064 vs 0.2291; board 1 hy21 ep24 0.1593 vs 0.1872. Pack 13i: CD-O 0.24177 (rank 4; 4th place 0.2467).
- **Rack round R (3 Nov, $5.95).** 390 new and 39 primitive-refit rack meshes; best 0.3876 vs 0.4016, none under the 0.3816 bar at first. Hy21 ep12 s31337 t3fit (50-seed 0.3775) passed; 13j built and passed D1 (3 Nov). Upload not recorded in this slice.
- **Pose boards.** 13p: TSDF pot on evals 1, 3, 5, 6, 8, 28; library_c0 rack on 14, 15, 16, 28, 30. 13p2 adds eval 20 pitcher placement (+0.0015 AUC vs predicted +0.004 to +0.006). 14p adds eval 14 rows. Board 2 stays library_v3 in pose packs.

## Scorer and task understanding (how the metric works, what it rewards, measured facts about the task)

- **Registration.** `_score_registered_track3` (with `_REGISTER_OBJECT_MESH = True`) registers our mesh to the reference scan (centroid and RMS normalisation, trimmed ICP from 25 starts; seed = 1,000,003 x episode + 101 x slot) and converts our poses through it. Mesh shape therefore changes every pose board. Cups are symmetric about the central axis (`_symmetry_point_errors`). Scene alignment is rigid at frame 0.
- **SP-SR / MP-SR.** SP-SR: mean position error at most 10 cm and orientation at most 0.5 rad. MP-SR: under 3 cm and 30 degrees for every object.
- **sim_vs_ref** (our GT-free proxy, plain ADD) charges cup twist that the board does not. Proxy differences near 0.02 on one episode carry no sign information about the board [I].
- **Board leverage (2 Nov).** One more SP-SR success (0.90 to 0.95) moves SP-SR 10th to 6th; MP-SR to 0.85 gives 6th; RPE -0.05 cm gives 8th; CD-O -0.0144 gives 5th.
- **Headroom.** Reference is about 10 % of RPE and 16 % of MPPE over 70 public draws; constant offset and frame-0 tilt dominate (+0.050 and +0.040 public upper bounds). Oracle twin with mocap object motion: 0.940 vs 0.595 (ep11).
- **NVIDIA default timing ceiling (30 Oct, $0).** Perfect perception and policy with default timing: AUC 0.415, SP-SR 0.30, MP-SR 0.00, MPPE 9.5 cm (floor 0.446 / 0.45 / 0.00 / 9.3 cm).
- **Physics limits.** Training sim limits (sim=rl) nconmax 256, njmax 512 per world. The evaluator inherits the checkpoint config, so a training-only override is scored too. `budget.py` at 32 by 60 is the binding check.

## Leaderboard and submissions (every upload: pack name, date, change, board scores, rank)

Board order: AUC, SP-SR, MP-SR, RPE, MPPE, CD-O. Ranks from score-status and keen-heisenberg reports.

- **Pack 9a+ (31 Oct 18:13; uploaded by score-status).** AUC 0.81757, SP-SR 0.85, MP-SR 0.65, RPE 3.87853, MPPE 2.89663, CD-O 0.33234. Rank sum 60, 11th.
- **Pack 9b (1 Nov 04:57 to 05:02; IDs 57860700 to 57860708).** Adds eval 33 D draw. AUC 0.81677, RPE 3.88283, MPPE 2.90186; slightly worse than 9a+. The log names two different uploading sessions.
- **Pack 10 (1 Nov 08:38 to 08:43).** ev10cs5 eval-10 draw. AUC 0.81915, SP-SR 0.80, MP-SR 0.65, RPE 3.68275, MPPE 2.84759, CD-O 0.33234. Rank sum 61, 11th.
- **Pack 11 (1 Nov 11:39 to 11:44).** Pack 10 plus eval 10 ck512. AUC 0.83921, SP-SR 0.85, MP-SR 0.70, RPE 3.17899, MPPE 2.54531, CD-O 0.33234. Rank sum 60, 11th.
- **Pack 12b (2 Nov 06:37 to 06:42).** Adds eval 16 freeze. AUC 0.84405, MP-SR 0.75, RPE 3.02339, MPPE 2.49546. Rank sum 61, 10th.
- **Pack 12c (2 Nov 08:38 to 08:43).** Adds C0 blue cup. AUC 0.84738, RPE 3.008, MPPE 2.467, CD-O 0.30008. Rank sum 58, 10th.
- **Pack 12d (2 Nov 12:42 to 12:47; owner "sure go ahead").** Tier A. CD-O 0.29029; AUC 0.84005, RPE 3.142, MPPE 2.525.
- **Pack 12e (2 Nov about 19:25).** Tier B. AUC 0.86905, SP-SR 0.90, MP-SR 0.80, RPE 2.39138, MPPE 1.95269, CD-O 0.26775. Best on every board. Rank sum 47, 7th (from 54).
- **Pack 13 (2 Nov about 18:50; IDs 57918229 to 57918242).** 12c plus eval 20 lift window. AUC 0.84924, RPE 3.00841, MPPE 2.45263. Rank sum 54.
- **Packs 13b, 13e, 13f (2 Nov, 19:20 to 19:45).** 13b = 13 plus eval 15 (AUC 0.84985, MPPE 2.43592). 13e = 13b poses plus 12e meshes (AUC 0.87166, MPPE 1.92180, RPE 2.39478, CD-O 0.26775). 13f = 13e plus blue cup and dust pan (AUC 0.87225, RPE 2.38260, MPPE 1.92530, CD-O 0.26249). Ranks unchanged at 47, 7th.
- **Pack 13f1 (2 Nov about 20:38).** 13f with eval 25 slot 1 reverted. AUC 0.87191, RPE 2.37520 (best). The expected +0.02 AUC did not appear.
- **Pack 13p (2 Nov about 21:55).** Pose-CV pot and rack on 13f1. AUC 0.88257, RPE 2.22667, MPPE 1.82356, SP-SR 0.90, MP-SR 0.80, CD-O 0.26869. Rank sum 46, 7th.
- **Pack 13p2 (2 Nov about 22:20).** Plus eval 20 pitcher placement. AUC 0.88403, RPE 2.22531, MPPE 1.80932.
- **Pack 14p (2 Nov about 23:35).** Plus eval 14 p0m rows. AUC 0.88571, RPE 2.21325, MPPE 1.79779, CD-O 0.26869.
- **Pack 13h (3 Nov about 00:07).** CD-O variant on 13f. CD-O 0.25159 (CD-O rank 5). Rank sum 45, 7th.
- **Pack 13i (3 Nov about 05:55; IDs 57935089 to 57935106).** CD-O variant on 13h. CD-O 0.24177 (CD-O rank 4). Rank sum 45, 7th.
- **Held / not recorded:** pack 14p1 (held: source-episode leakage; about +0.0003 expected). Pack 13j: passed checks; upload not in this slice.

Standings snapshot (2 Nov 06:50): AUC leaders 0.96804 / 0.93906 / 0.92754; RPE leaders 0.72 / 1.14 / 1.23; MPPE 0.82 / 1.16 / 1.35; CD-O 0.213 / 0.232 / 0.239.

## Process, cost and infrastructure (GPU rentals, $ spent, bugs, failures, tooling, rules adopted)

- **Credit.** $69.22 (31 Oct 21:20); $56.52 (22:58); $29.93 (1 Nov 05:06); $23.63 (08:58). Owner top-ups to $122.85 (1 Nov 19:34) and $127.97 (2 Nov 20:12). $75.62 at 3 Nov 06:40.
- **Spend.** Ledger $152.94 at 31 Oct 22:57; $200.12 of a $325 budget at 1 Nov 08:58. Recipe screen about $30.15 [E]; D arm training and confirmation $19.41 measured; masses check $9.10; e10v $3.25; e10cs $2.85; e10nj $2.06; e20b1 $2.14; h5p7 $5.85; h5e1 $6.95; mv2a2 $6.20; mv2b $10.45; re-track $1.54. Perception-tracking about $26 of $40. Perfect-following about $36 by 3 Nov 01:46. Mesh G2 $8.31, G3 $7.47, rack R $5.95.
- **Rates and losses.** RTX PRO 6000 $1.07 to $1.68/h; H200 $4.03/h. About $6.5 lost on failed or replaced boxes (2 Nov); a preempted H100-class box about $2.80.
- **Push race (bug).** Watchdog's interim `store.sh push-run` runs in the background; the final push-run rebuilds the same `/content/push/<run>` with `ln || cp`, so the second cp fails under `set -e`. H5p7 and mv2b both PUSH-FAILED. Interim push had saved results. Fix planned (`flock`), not built in this slice.
- **Pulls.** Pack 6 pull of 6,866 files took about 50 minutes (HF 429s, 1 Nov). Narrowed pull for videos: about 11 minutes vs about 6 hours on 30 Oct. Single-file downloads adopted.
- **Other bugs.** `pgrep -f` self-match in a wait loop (1 Nov); stale `asset_root` ran eval-14 zero-shot on old meshes (fixed c1a5471); missing support asset (fixed b0b4a31).
- **Rules adopted.** Pre-registration before any result, with dated addenda; swap rule (a/b/c/s); inclusion at least +0.02 on both references (1 Nov); two-host confirmation (3 Nov); mesh entry condition "zero-shot within 0.02 of control" (3 Nov); `no_oracle` guard refusing non-stock checkpoints (exception by owner word only); D1 flip veto; `budget.py` 32 by 60 binding; stall watchdog at 30 minutes; self-destroy after each job.
- **Permissions.** Uploads blocked by the permission classifier on 31 Oct (~16:40), 1 Nov (~08:35, and a guard denial 11:25), 2 Nov (01:15, 08:58, 19:15). Each waited for the owner's word. No session routed an upload through another.

## Owner decisions and quotes (short verbatim quotes with dates)

- 31 Oct 15:20: "get me into that top tier, I'm giving you everything you need"; 15:40: "I want a pack today".
- 31 Oct 21:14 (AskUserQuestion): "Yes, start tonight (Recommended)" (D cells); "Upload automatically" (pack 9b).
- 31 Oct 20:29: "No D" for pack 10; reversed about 20:40 via score-status: "sure add that whatev".
- 31 Oct 21:22: "okay I allow 3d mesh chat to do anything as long as it improves the score and doesnt intervine with the rules of the competiton. they can go crazy".
- 1 Nov 02:43: "Okay go" (njmax-1024 diagnostic, conditions stated).
- 1 Nov 02:50: "I give you permission for everything" (GPU work serving the score; uploads of packs passing pre-registered checks; not covered: njmax-1024 policies in packs, C0 blue cup, GT reads).
- 1 Nov 09:11: "I give give you go" (pack the njmax-1024 policy at stock limits).
- 1 Nov 11:40: a single sha-specific allowlist entry for the eval-10 ck512 checkpoint.
- 1 Nov 18:58: "I want robot hands as well".
- 1 Nov 19:34: "I got you credit include the spending permision and basically all the permisions needed to perfect those scores in any way possible. Make sure they colab with the grasp session needed or at least communicate with them."
- 2 Nov 07:30: "Go do as much as you can lets go to top also you can run another sesh for increasing general perception and experiment in public eps".
- 2 Nov 08:10: "For blue cup I give you mey yes".
- 2 Nov 19:00: "Okay I give you permission for all" (eval-15 waiver; Tier B).
- 2 Nov about 19:20: "Upload 13b, you dont need my permission to upload anymore."
- 2 Nov about 20:12: "you can upload as much as you want, go crazy, lets win this"; earlier: "If I give you this money I expect you to do anything in your power to reach top 3."
- 2 Nov 17:05: "first do the tests and let me add more money once we increase the perception."
- 3 Nov 03:50: "yes to bias calibration". 3 Nov 06:40: "go in all".

## Lessons stated in the log

- "When the expected gain is within noise, a swap is a coin flip on the board. The swap rule protects against large losses but not small ones." (1 Nov, after pack 9b.) Added: skip uploads whose expected AUC change is below board noise.
- A proxy difference of about 0.02 on one episode "carries no sign information about the board"; require a margin larger than the proxy-vs-mocap disagreement, sized on public data.
- "Training is corrupted; scoring is not." Overflow lines hit training on eval 10, not the 50 scored draws.
- The "poses are the problem" reading (1 Nov) was retracted as too strong: with our meshes at true mocap poses, overlaps persist (ep11 cups 65 cm^3, ep31 11.1, ep24 9.9, ep2 5.9).
- Many physics hypotheses failed their pre-registered falsifiers (smoothing, velocity input, masses, re-track, hold filter, twist canonicalisation, rigid-in-hand, point tracks). One variable at a time.
- "Better meshes are not a sure gain; any mesh lane needs its own public test" (2 Nov); the complete-base pitcher template test was -0.249.
- A sign-off can rest on a wrong claim ("the eval seed does not flip" was false for wooden_piece_2). Flip checks need several seeds and both reference modes.
- Box draws overstate lift policies; fresh draws on a second host are required.
- Post-hoc thresholds and best-per-board coin-flip variants were refused as eval-set probing.
