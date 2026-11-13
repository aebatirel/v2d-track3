# Digest: worklog_part3 (22 Oct to 3 Nov 2026)

Source: `worklog_part3.md`, read in full. Three lanes: mesh/CD-O (branch `affectionate-turing`; gmg work on `bold-albattani`), physics/policy (`determined-wright`), and one 22 Oct training-budget note. Dates as written; not strictly ordered. Tags as in the log: [M] measured, [D] diagnostic (scan-scored where stated), [E] estimate, [H] hypothesis, [R] review, [I] inference. "Post hoc" marks rules written after results were seen.

## Perception (depth, detection, identity, tracking, hands, room map, point tracks)

- **27 Oct, frame check (CPU, GT-free).** Shipped pot, lid, rack meshes lie a median 2-4 mm from library_v3 meshes of the same objects; public blue-cup lathes ep21/22 lie 2.7-3.4 mm from library_v3 blue cup. Read as one shared library object frame [M].
- **27 Oct, per-frame pose refinement (critic test).** Track jitter on ep41 handle: between-frame plane-offset spread 5.6-9.3 mm vs within-frame width 3.7-5.5 mm [M]. Refinement (frames slid along cylinder axes, 10 mm bound) recovered injected errors, but its pre-registered falsifier failed (spread roughly halves, stays above within-frame width in one band per episode). Refined shells were worse; not used.
- **27 Oct, leak study (focused-pascal data, not re-verified).** Re-tracking with scan-derived vs library_v3 templates: +0.039 mean, +0.006 after one body offset per episode-object. Body offsets: lid 1.4-1.8 cm (ep0), beige base +1.8 cm (ep11).
- **30 Oct, uncovered-object extraction (CPU, public depth).** Beige 11; blue 11/12/13/21/22; pitcher 21/22; dust pan 18/39/40; sweeper 18/31. Last run about 52 min for 17 episode-objects (40-300 s each).
- **31 Oct to 1 Nov, hands-off track audit (GT-free).** Every hands-off public frame tested is impossible: overlaps of 2.7-85 cm3 or table penetration (ep13 cup 5.7 mm into table; ep31 sweeper 45 mm above it). Later correction: much of the overlap is mesh shape (overlaps persist at mocap poses: ep11 cups 65 cm3, ep31 11.1, ep24 9.9, ep2 5.9).
- **Other tracking facts.** Eval-25 board pose at assembly differs from the packed parquet (md5 71ac95f3) by 9.8 mm / 2.5 deg [M]. A -15 % board-1 size error traced to a broken ep23 track (ep24 refit +4.5 / +0.6 %). MediaPipe misses held hands; view and crop frames are limited to at-rest frames (speed < 1.5 mm/frame). ep12 has no hands.npz; ep18 hands=null.

## Policies and following (RL training, recipes, retrains, sim, seeds, flips)

- **22 Oct, training-budget note 23.** Schedule validated but not shown minimal; our references play 2x faster than NVIDIA's; with logging disabled, no learning curve on day 1; checkpoint cadence 10,000,384 steps, not 5M (corrected). Proposed stage B: {250M, 125M} x 2 seeds on eps 12/22/27, 18 GPU-h, about $9-29 [E]. Nothing rented.
- **30 Oct, mass arms S0 vs S1 (GPU, registered AUC vs mocap; ep2/12/18/24).** Hypothesis: scan masses help. S0 0.944 / 0.862 / 0.573 / 0.207; S1 0.736 / 0.885 / 0.625 / 0.232. Harm on ep2 (-0.208; S1 collapsed after 20M). Not adopted. Cost S1 $3.31, S0 $5.39 (est).
- **30 Oct, CPU zero-action mass test (pre-registered).** Mean delta S1-S0 +0.021: neutral. COM test [H-com]: +0.215 / -0.024 / -0.060 / +0.021, but a 2 mm control moved as much (+0.109 / -0.005 / -0.116 / +0.151): zero-action replays are chaotic in object parameters.
- **30 Oct, own 22-DoF capsule human hand (Apache-2.0).** [H-squeeze] +0.3 rad: +0.009 / -0.019 / +0.019 / +0.002, falsified. Perceived-motion copy: P 0.323 / 0.617 / 0.331 / 0.194 vs floors 0.506 / 0.605 / 0.619 / 0.220, so it does not carry objects. [H-lock] valid run: +0.117 / -0.039 / -0.055 / -0.092, falsified. Round 2: human hand + RL mean -0.161 vs Sharpa.
- **30 Oct, sampling-MPC solver (CPU).** ep12 nominal zero-action sim_vs_ref 0.600 (floor 0.605) -> v3 0.6899. Jitter (8 copies, 0.5 mm / 0.005 rad): GL 0.556 +/- 0.031, v3 0.564 +/- 0.039; bar 0.586 not met: [H-robust] falsified at CPU scale.
- **30 Oct, solver G1 (GPU, 1,024 worlds, 64-copy jitter; gate: beats GL+ILC by >= 0.03 on >= 2 of 4 eps).** Jittered delta +0.080 / +0.063 / -0.004 / +0.005. PASS. $1.29.
- **30 Oct, G2/G3 (scale; RL from solved refs).** G2 jittered ep2 0.763, ep12 0.832 vs GL+ILC 0.524 / 0.578. G3 final 0.584 / 0.892 / 0.622 / 0.244 vs 0.736 / 0.885 / 0.625 / 0.232: harm by rule, but on ep2 seed 42 only (seeds 43/44 reach 0.98). $6.48.
- **31 Oct, realistic masses round 3 (seeds 43; ep12/18/24; rule mean delta >= +0.03).** Mean delta +0.090, adopted. Box p3ms1 watchdog-destroyed after a 30-min stall ($3.88); p3ms0 $3.28.
- **31 Oct, solver-RL loop (O3) vs O1.** AUC ep2 0.835 / 0.585, ep12 0.904 / 0.893, ep18 0.620 / 0.579, ep24 0.224 / 0.254. Pre-registered "signal" (+0.068). Post hoc: 3 of 4 O3 checkpoints from pre-loop round A (LR-horizon confound); the solver changed 0 frames in 4 of 8 turns. Not credited to the loop. About $6.48 [E].
- **31 Oct, mass transfer check (focused-pascal; library_v3 at 0.3 kg vs realistic masses; NREP 10).** ep2 0.552 to 0.633 (s42), 0.581 to 0.814 (s43), delta +0.157 (SE 0.105); ep12 delta -0.013 (SE 0.007). Not adopted (ep12 misses +0.03). Box $9.10. Re-test "Masses v2" (ep24/11/13/31; adopt iff mean delta >= +0.03, >= 3 of 4 > 0, none <= -0.05) approved, about $18 [E]; no result in slice.
- **31 Oct, eval-10 overflow.** Retrain logs: ~6.0 M "nefc overflow" lines per seed (njmax needed median 580, max ~1,050 vs 512). njmax 1024 diagnostic: 0 overflow lines, beige lifted 23.9 cm, official sim_vs_ref 0.913 (stock 0.459); never packed. Legal fix: eval-10 retrain at stock limits on ev10cs5 (1 Nov). Budget 32x60: packed ev10 380 rows / 9,723 overflow lines; ev10cs4 0 / 0.
- **31 Oct, recipe screen (C = scan-free recipe; K = longer horizon, lower LR; D = start-state DR; S = solved refs; AUC mean (draw sd)).**
  - ep2 s42: C .955 (.029), K .965 (.009), D .743 (.269), S .751 (.211). ep2 s43: C .869 (.174), K .959 (.020), D .862 (.236), S .808 (.225).
  - ep12 s42: C .576 (.066), K .519, D .924 (.021), S .832. ep12 s43: C .612 (.014), K .582, D .919 (.022), S .802.
  - ep18 s42: C .620, K .623, D .603, S .553. ep18 s43: C .624, K .620, D .600, S .616. ep24 s42: C .234, K .191, D .233, S .249. ep24 s43: C .238 with 4 of 10 draws (6 crashed: pthread EAGAIN, infrastructure), K .251, D .230.
  - Verdicts: K vs C inconclusive; D vs C not determined; S vs C no signal (delta ep2 -0.132). One reference re-run moved a cell by up to 0.07 AUC.
  - Post hoc: sim_vs_ref picked the higher-AUC arm in 7/7 C-vs-D and 7/7 C-vs-K pairs; a selector adds +0.094 over 7 cells, all from ep12. Falsifier: train D on more public eps.
  - Cost (ledger est): $8.22, $7.73, $3.30 for three boxes; eval solve not launched.

## Grasp and references (contact labels, reference building, lift windows, grip)

- **Spoon.** No public scan exists. GT-free ambiguity 3.41 / floor 1.41 mm at 177.5 deg [H]. 25 Oct study: 0/300 flips vs 30 plausible spoons; the loss is frame-0 anchor roll (pose), not the mesh (2 Nov correction).
- **31 Oct, spoon-in-cup (GT-free, reference poses).** Eval 33: packed blue cup >= 50 % solid to 66 mm above base; spoon in cup 66 frames, deepest 128.7 mm below rim; worst intrusion 9.8 / 85 cm3, 19 mm deep. Eval 32: <= 3.2 cm3. Eval 16: no rack seat filled; spoon 1-8 mm off the rack.
- **1 Nov, f0 settle survey (20 packed eval refs).** Falls at f0 with no hand near: eval 20 pitcher 195 mm / 94.6 deg (b1 fix: 8.5 mm / 3.2 deg); eval 19 sweeper 90 mm / 89 deg; eval 30 sweeper 24 mm / 25 deg (starts 12.2 cm3 inside rack); others within 3.3 mm / 5.1 deg.
- **1 Nov, eval-19 support_fill (focused-pascal tool).** E1 f0 90.2 mm / 88.8 deg -> 0.01 / 0.01; E1 f2 92.4 / 90.1 -> 1.70 / 1.53 [M, collision-only overlay]. Pitcher b1 clip passes settle G3 (1.6 mm / < 0.6 deg; packed 3.2-3.3 mm / 6.4-7.5 deg).
- **30 Oct, reference noise (R5-lite, zero action, jitter 16).** Mocap-motion vs perceived reference: ep13 0.569 +/- 0.008 vs 0.551 +/- 0.007; ep31 0.556 +/- 0.091 vs 0.554 +/- 0.096. True motion barely helps executability.

## Meshes and CD-O (templates, scans, registration, mesh tiers, mesh adoption)

- **27 Oct, primitive kit fits (6 scorings each; gate CD-O/ADD).** Lid: CD-O 0.224 / 0.220 / 0.221, ADD 4.56 / 4.46 / 5.06 mm at 1.5 / 2.5 / 4.0 mm; gate <= 0.391 / 9.1; shipped 2.5 mm. Rack lean (pre-scan design): CD-O 0.458 / 0.456 / 0.449, ADD 6.06 / 5.37 / 6.23 mm; upright (scan-informed) worse on fidelity and ADD (7.22 at 1.5 mm, fails); gate <= 0.525 / 7.0; shipped lean 2.5 mm. Pot PASS (0.342 / 3.05); boards FAIL.
- **27 Oct, automation audit.** About a third of fitter code is object-specific; a fitter run on the wrong object returns a clean wrong mesh (23 of 26 runs). Probes P1 (pot, name-blind) and P2 (dust pan) REFUTED. Stage-1 DSL reproduces hand kits (pot/cup 0.000 mm, lid 0.003 mm); thin shells watertight; cup fidelity 1.4 vs 6.1 mm (library).
- **29 Oct, batch 2 generators (104 one-shot scorings).** Mean CD-O over 10 objects: library_v3 0.477 (median 0.429); SAM 3D 0.501 (beats library 6/10); Pixal3D-MV 0.490 (5/10); Hunyuan3D-2.1 0.602; TRELLIS.2 0.594; TripoSG 0.984. Oracle best-of-all 0.315 (not a method). Pixal3D falsifier (median >= 0.08 below 0.40) FALSIFIED at 0.399. Pixal3D ADD median 10.3 mm, 6/20 flips; single-image Sim(3) ADD 26-29 mm. GT-free selector Spearman 0.46, picks CD-O best on 2/10. Nothing adopted. $4.36.
- **31 Oct, C0 set (pot, lid, rack, blue cup; marker balls at MK_R0 = 7 mm).** Rigid ICP vs library_v3: pot 2.49 mm, lid 3.03, rack 2.09 (2.3 deg rotation), blue cup 6.67. AUC guard (51 runs, 15 twins; mean dAUC >= -0.005, min >= -0.02, dMPPE/dRPE <= +0.2 cm): pot +0.0030 (min -0.0159), lid +0.0055, rack +0.0158 (min -0.0092), blue cup +0.0241 (min -0.0049). All pass. Blue cup held back from pack 9a (selector integrity). Board estimate 0.402 to 0.367 [E].
- **31 Oct, C0a (C0 rigidly ICP-aligned to library_v3).** Hurts: rack +0.0158 to -0.0046 (min -0.036). The rotation is library_v3's frame error; do not align eval-built meshes to it.
- **31 Oct, C1 (beige obs-lathe; dust pan placed pick).** Beige CD-O 0.856 to 0.248 (eval 10), 0.730 to 0.255 (eval 8); add_med 5.70 mm; 0/32 flips; guard +0.008. Adopted. Dust pan 0.331 to 0.260; add_med 4.83 mm; guard +0.012 (min -0.0014). Adopted. T3 generate-then-fit: 3 CD-O wins, all fail the guard (min about -0.04). Pitcher and beige picks fail ADD (28 / 15 mm). Board 0.367 to 0.333 [E].
- **31 Oct, C0b (scan-free rebuild; markers.py balls; t0 4.559 mm).** Adopted: pot CD-O 0.3924 (guard +0.0009 / -0.0107); beige 0.3007 / 0.2983 (guard +0.0139). Not adopted: lid (16/16 builds failed on cube clutter); rack 1.632 and blue cup 1.677 (guard fails). Audit: 163 constants; 16 scan-derived, 71 unknown.
- **31 Oct, E0 (eval-built; in-sample fidelity, no eval GT).** Picks: pot ep3/fit 2.922 (C0 2.914, library 3.881); lid 1.675 (1.772; 5.186); rack joint 6.419 (6.245; 5.881); blue cup ep32/g1 2.646 (2.723; 2.906). Box $0.13. E0b (generic balls): pot 0.392, beige 0.30 public CD-O, less accurate than 9a+.
- **31 Oct, C2.** Pitcher obs-lathe CD-O 1.160 vs gate 0.8742: falsified. Rack parts CD-O 0.4413 vs gate 0.43604 (C0 0.4560): not a win; guard PASS (+0.0147), not adopted.
- **31 Oct to 1 Nov, board slot (F-I4 rounds 1-3, eval 25).** Round 1: no plane pair; fixes were post hoc. Round 2: prisms 57-77 vs cap 82 (ep23 needs 85); no freeze. Round 3: 5 slotted boxes per board; ep24 carves, P2-P7 pass (P3 0.074 cm / 0.68 deg), but the contact-gate ratio is 124 vs 32 rows = 3.875 > 2.0; not frozen. Eval 25: NO; keep meshes/carve/ev25.
- **31 Oct to 3 Nov, collision carve (F-I5; owner waiver: any colliding pair).** Round 1: all ten objects fell to 6 mm boxes keeping 1.8-9.3 % of body. Round 2: rings fail the 1.5 mm wall check (min wall -21 to -173 mm; ~1 mm roughness per face); CoACD fails the gate; nothing delivered. Evals 10/1/14/30 not run.
- **1 Nov, cavity-safe ev10 candidates (plain MuJoCo, indicative).** Packed overlap f124-160 median / max 11.9 / 32.7 cm3; ev10cs4 0.21 / 2.61 cm3; ev10cs4 at 32x60: 0 overflow lines (hold max 448). Blue kept-volume gate fails.
- **1 Nov, rack-slot candidates (evals 30, 14).** None passes. Guest mesh is inside the rack mesh at every H30 rest frame (eval 30: 22/22, 6.2 cm3 median). Candidates empty the slot but throw the sweeper further. Keep packed racks.
- **2 Nov, G2 generation.** 264 meshes (SAM 3D 88/88, Hunyuan 88/88, TRELLIS.2 82/88 + 6 at 1024). 50-seed audit of 32: pot sam3d ep44 k0 s7 CD-O 0.2861 vs 13f 0.3107 (ADD 2.7 vs 6.3 mm); blue cup sam3d ep22 k159 s7 0.2335 vs 0.2646 (ADD 6.0 vs 8.1); rack hy21 ep31 k282 s123 0.4016 vs 0.4182 (ADD 4.3 vs 10.0). Pitcher: none passes. Adopted pot, blue cup, rack (D1 0/6 flips). Selection is GT-informed best-of-N, disclosed.
- **2 Nov, Tier B (owner yes).** Pitcher hy21 ep22 s42 CD-O 0.3722, ADD 15.8 mm, 0/31 flips. Board 2 occupancy plate flips 34 % of 50 seeds (raw reference: 179.18 deg at eval 25 slot 1). Board 2 library_v3 has no flip.
- **2 Nov, C4 board-2 variants (50 seeds).** Shipped: W30 0.34, CD-O 0.1649. library_v3: W30 0.00, CD-O 0.2169. +2 balls: W30 0.18 (fails -20 bar); all clusters: W30 0.70; 12.5 mm slab: W30 0.12, CD-O 0.2163. Thickness stops flips at ~0.05 CD-O cost.
- **3 Nov, G3 (432 single-image + 36 Pixal3D; 79 audited; $7.47).** Adopted for 13i: pot trellis2 ep45 k9 s2025 CD-O 0.2399 vs 0.2861 (ADD 6.8 vs 2.7, worse for pose); dust pan Pixal3D-MV ep39 0.2064 vs 0.2291; board 1 hy21 ep24 k3 0.1593 vs 0.1872. Not adopted: rack 0.3934 (-0.008); board 2 #43 (anchor rule fails: 5.50 > 5.46 mm); outer-shell and rack-trim copies (rack trim -0.016 vs -0.020 bar).
- **3 Nov, rack round R (120 candidates; $5.95).** hy21 ep12 k18 s31337 t3fit: CD-O 0.3775 vs 0.4016 (delta -0.0241, rule A passes); anchor 3.07 vs 3.78 mm; ADD 3.74 vs 4.30; D1 0/6. Adopted for 13j.

## Scorer and task understanding (how the metric works, what it rewards, measured facts about the task)

- **CD-O normalises scale and re-registers the mesh to the scan.** It is blind to our placement; ADD shows it (generator placements 18-34 mm ADD). Registration absorbs body-frame translations, so a flagged centroid shift can be library_v3's own error (anchor error 9.1-10.4 mm vs C0 2.1-3.6 mm [M]).
- **Board math.** The CD-O board is a mean over 36 pairs, 10 of them spoon pairs. Board 0.402 = spoon pairs about 0.18 (inferred) + library_v3 over 26 pairs (0.491). For 9a+ (0.33234), implied spoon = (0.33234 x 36 - 10.156) / 10 = 0.181 [E].
- **Board selection.** Each Kaggle board keeps its best or selected submission (organiser PR #215), so a CD-O-only variant cannot lower the other boards.
- **AUC guard.** Public twins only. A single-twin pitcher swap cost -0.0045 on Kaggle (other session).
- **Object physics.** No measured properties: 0.3 kg placeholder mass. Most objects are rigid plastic; boards are wood, 8.5 mm real vs our 2.7-3.1 cm. Friction is one global 1.0.
- **Eval meshes** are rebuilt per eval episode from its own video (owner decision, 22 Oct). Eval depth exists for all 20 eval episodes (29 Oct).
- **Solver limits.** Sim=rl nconmax 256, njmax 512 per world; evaluator runs VOC 0. Eval-25 packed budget: median 201 rows, max 276.
- **Marker balls.** MK_R0 = 7 mm and its 5-9.5 mm window come from the public-scan marker catalogue (spoon template note 17), not our stereo.
- **Rules.** Leaderboard freeze (critic): 2026-11-04. Kaggle §8.d requires website registration; §9.a requires the commit in a repo shared with the organisers.

## Leaderboard and submissions (every upload: pack name, date, change, board scores, rank)

- **30 Oct ~18:30, AUC board:** 0.81460, 7th (top: richchentw 0.940, DDD 0.932). 31 Oct: 8th.
- **31 Oct ~15:15, pre-9a board:** CD-O 0.40188, 18th of 20 (leaders 0.213 / 0.239 / 0.250). SP-SR 0.85, MP-SR 0.65, RPE 3.93179, MPPE 2.92126.
- **Pack 9a+ (31 Oct ~18:20):** 9a (C0 pot/lid/rack) + beige T1 + dust pan T2. CD-O **0.33234** (from 0.40188; estimate 0.333), rank 18 to 14. AUC 0.81757 (+0.003); RPE 3.879 (-0.053); MPPE 2.897 (-0.025); SR unchanged.
- **Pack 12c (2 Nov 08:46):** 12b + C0 blue cup. CD-O **0.30008** (from 0.33232), rank 11th. AUC 0.84738; MPPE 2.467.
- **Pack 12e (uploaded 2 Nov 19:22):** Tier B; best on every board. AUC **0.86905**; SP-SR 0.90; MP-SR 0.80; RPE 2.391; MPPE 1.953; CD-O **0.26775** (est 0.268). Rank sum 47, 7th.
- **Pack 13f (built 2 Nov 19:35):** 12e + blue cup and dust pan extras; expected 0.2627; score not in slice.
- **Pack 13h (built 3 Nov 00:05; on 13f):** pot, rack, blue cup G2 picks. CD-O **0.25159** (est 0.252), 5th; rank sum 45.
- **Pack 13p (~2 Nov 22:00; pose pack):** TSDF pot + library_c0 rack chosen by perception CV. AUC **0.88257** (+0.010); RPE 2.227; MPPE 1.824 (coordinator report).
- **Pack 13i (scored 3 Nov 07:18):** on 13h; pot, dust pan, board 1. CD-O **0.24177** (est 0.242), 4th; 3rd is 0.23900.
- **Pack 13j (built 3 Nov 10:32; confirmed 12:20):** on 13i; rack round R. Score not in slice.
- **Held:** pack 14p1 (CV leakage: #43 generated from a CV episode).

## Process, cost and infrastructure (GPU rentals, $ spent, bugs, failures, tooling, rules adopted)

- **Spend (Vast records).** Eval depth $2.95; generative probe $4.36; G2 $8.31 (includes a preempted box, $2.80); G3 $7.47; R $5.95; mass check $9.10; C0b $0.68; E0 $0.13; E0b $0.49. Summing the actuals listed in this slice gives about $99 for all lanes (derived; excludes one unstated box).
- **Budget and credit.** Mesh allocation $25 (spent $7.31 by 30 Oct). Shared ledger 31 Oct 10:50: budget $225, actual $93.21; 21:38: budget $325, actual $131.91. Owner top-ups: $100 on 29 Oct, $100 on 31 Oct, $127.97 credit on 2 Nov.
- **Rentals.** RTX PRO 6000 ~$1.27-1.51/h; H100 NVL $1.398/h all-in; H200 NVL $4.033/h. An interruptible H100 was outbid (29 Oct) and another preempted (2 Nov, switched to on-demand). Offers vanished (404) at create.
- **Interruptions.** Weekly usage limit 29 Oct 21:00 UTC (stage 1b: 6 agents, 0 results). 5-hour limits about 30 Oct 10:20, 14:58, 17:55; 31 Oct 23:30, 06:50. Container restarts 30 Oct 12:05 and 17:08; 31 Oct 04:47; 2 Nov 23:22 (killed a Sim(3) batch); 3 Nov 06:43 and 07:14.
- **Bugs.** ledger.py treated a failed read as empty; one write erased two lines (fixed in 8be9e27). hf CLI 2.2.0 misreads a second --include. Pixal3D wheels need compute_90 (H100-class). flash_attn 2.8.3 ABI mismatch. lathe_obs splats are inside out in every g1 mesh (CD-O/AUC unaffected).
- **Rules adopted.** PREREG committed before runs; SHA256 freeze before any scan read; one scoring per mesh; AUC guard; D1 flip gate (0/6 flips in raw and budget reference modes); ledger planned/actual lines with mesh-* run ids; one box at a time; amendments labelled post hoc; no GT in inference.

## Owner decisions and quotes (short verbatim quotes with dates)

- 27 Oct, 13:15: "I want a combination of A and B and want the minimal CD-O vs public scan."
- 27 Oct, ~13:40: "don't worry about the deadline / leaderboard freeze, that's for me to worry". Planning ignores the freeze from then on.
- 29 Oct, 21:45 (relayed): "you can give mesh improvements session vast credits ... I think that can improve our score". Mesh allocation $25.
- 30 Oct, ~07:15: "SAM seems to do a great job but the orientation and the size seem off ... also we messed up the mini sweeper again".
- 30 Oct, 09:40: "do whatever you like to make a generalized mesh generator".
- 30 Oct, 12:00: "for sam to perform better on the pots we need to know they are 2 separate meshes and feed that accordingly".
- 30 Oct, 12:20: "you can spend money and go ahead in all btw" (standing spending go-ahead).
- 31 Oct, 08:50: "We don't have the placement slot in any of that." Corrected at 09:10: "how do you expect the wooden blocks to interlock in a physical simulation without the slot?"
- 31 Oct, 15:25: "Lets do all the improvements that we planned and lets prepare a pack so that we see where we stand, like better perception better mesh better physics."
- 31 Oct, 15:50 (relayed): "if the method of mesh creation better just recreate the meshes in the eval and use that".
- 31 Oct, 16:00: "Okay I waive that camera rule" (board slot).
- 31 Oct, ~16:55: chose "Ship 9a, flagged" after a question was put to the owner.
- 31 Oct, 17:35: "it doesnt have to be a board it can be a cup of what ever like if 2 mesh collide we can carve it".
- 31 Oct, 21:22 (relayed): "I allow 3d mesh chat to do anything as long as it improves the score and doesnt intervine with the rules of the competiton. they can go crazy".
- 1 Nov, 02:50 (relayed): "I give you permission for everything" (collision overlap fixes).
- 2 Nov, 19:00: "Okay I give you permission for all" (Tier B). 20:13: "go crazy, let's win this" (credit $127.97).
- 3 Nov, 01:47: "do as much as you can tonight" (G3, cap $15).

## Lessons stated in the log

- A fitter run on the wrong object returns a clean but wrong mesh (23 of 26 test runs).
- The GT-free selector prefers route-A shells at the thinnest t, since it only measures observed surface; an incomplete shell cannot lose.
- Aligning eval-built meshes to library_v3 hurts; the few-degree rotation is library_v3's frame error.
- A better mesh pays mainly if it is also the submitted mesh.
- Single zero-action replays are noisy estimates; one re-run of a recipe cell moved AUC by up to 0.07.
- Summaries overstated results (the G3 "harm" was one seed; the loop was barely exercised); corrections were logged.
- Scan-derived constants (marker balls, thickness) leaked into earlier passes; those passes are provisional.
