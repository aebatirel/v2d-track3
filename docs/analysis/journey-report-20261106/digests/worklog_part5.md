# Digest: worklog_part5 (31 Oct to 3 Nov 2026, UTC)

Branches: PT = perception-tracking (2 Nov); PF = perfect-following (31 Oct to 3 Nov, includes pack builds); PTK = point-track (2 Nov); ST = standings (2 Nov). Swap rule = pre-registered GT-free rule: 10 fresh official draws vs packed draws, gain >= +0.02, no fail-count regression, median RPE not worse.

## Perception (depth, detection, identity, tracking, hands, room map, point tracks)

- **2 Nov, MG mask-guided tracking (PT, batch 1, 19 public eps):** hypothesis: SAM2 video masks reduce track loss. Falsifier dAUC <= 0 fired. Mean -0.0009, 7 better / 7 worse, min -0.069 (ep11; blue cup -0.128), MPPE -0.012, RPE -0.109, frames > 3 cm 368 to 382. **FAIL.**
- **2 Nov, MD (depth restricted to video mask, report only):** -0.0077, 5/9; restricting depth to the mask hurts.
- **2 Nov, MR (re-centre and re-register):** batch 1 +0.0029 (5/4, min -0.008). Replication on 20 eps: ep0 0.614 vs control 0.994 (-0.380, lid lost); ep18 +0.048; others within +/-0.002. **Closed**: wrong-mask re-registration. Batch-1 ep0 had crashed, hiding this.
- **Pitcher template (P):** ep21 P had 3 guard re-acquisitions (control 0). Lathe pitcher extents 0.218 x 0.274 x 0.412 m vs v3 0.148 x 0.261 x 0.412. ep21/22 P vs Cr dAUC -0.249, 10 interventions. **FAIL.**
- **FS1 full-resolution depth:** 19 eps vs C: mean -0.0079, 7/10, min -0.098 (ep13 blue cup in rack), MPPE +0.105, RPE -0.013, frames > 3 cm 368 to 418. **FAIL, falsified** (16-ep interim -0.0097, 5/9).
- **ep18 chaos (PT):** control sweeper partly lost (0.898). Every perturbation recovers it (MR +0.062, MG +0.060, FS1 +0.057; stored 25 Oct base 0.938). Lesson: small perception changes flip whole tracks; eval changes need per-episode checks.
- **25 Oct sweep re-read:** base/t4/t8 differ <= 0.01 except catastrophic losses (ep0 lid; ep18 sweeper t4/t8 -0.25 to -0.29; ep12 cup t8 -0.25). Best-of-3 oracle 0.894 vs base 0.868. Iteration settings are not a precision lever.
- **SAM-6D-style detector, ptrkE (owner: <= $6):** ISMa (added) +0.0010, 6/1, min -0.0009, MPPE -0.020, RPE -0.168, > 3 cm 1030 to 1032. **FAIL**. ISMr (replace) crashed on ep11/12/31, mean -0.204 over 17. **FAIL.** Cost ~$4.6.
- **ep23 identity swap (PT correction, 17:58 2 Nov):** the two boards are swapped at frame 0, hidden by the kit's frame-0 alignment. The earlier "joint tracking loss" reading was wrong. As-named rigid fit 7.8 / 7.4 cm vs swapped 3.2 / 5.0 cm; plain relabel scores 0.036. Fix: existing `pipeline/identity_fix.py` (GT-free board-knob darkness, 25 Oct): ep23 AUC 0.041 to 0.663 (piece 1 0.083 to 0.959; piece 2 0.000 to 0.368; MPPE 16.3 to 5.4 cm; RPE 16.1 to 7.3 cm); ep24 unchanged 0.8343; public mean ~+0.031. Eval 25 packed reference already uses it.
- **Stage 1 (owner: build and run, <= $4; CPU):** per-object rest-segment ICP of masked stereo depth vs library_v3, guards (>= 300 pts, <= 3 cm / 10 deg). VO-camera arm **FAIL**: 105 segments fitted, 6 kept, 5589 frames changed; dAUC -0.0088, 7/12, min ep18 -0.062; MPPE +0.054; RPE +0.206 cm; > 3 cm 971 to 896. Pitcher ep21 +0.051 / ep22 +0.019; pots -0.012 to -0.028; cups ep12/13 -0.031. Map-camera arm dropped. Reading [I]: depth fit helps where bias is large and moves good poses where the tracker is already within mesh error.
- **Marker correction layer (spoon and others, GT-free, PF 31 Oct):** public validation 16 units: mean -0.083, 1/16 improved, worst -0.407 (lid ep2); raw fixes -0.039. **FAIL.** Single-frame stereo marker fixes 1.0 to 2.2 cm vs our pot tracks 0.26 to 0.42 cm. Spoon >= 2 markers in 34 to 73 % of frames, >= 3 in 2 to 18 %. Third camera ego_cam_a: M1 visible 82.5 % rest / 64.8 % hand, but precondition failed (pot 3.35 vs 0.41 cm). Closed.
- **Point tracks (PTK, 2 Nov, CPU, $0):** KLT and BootsTAPIR-style lift tracking on Cr. PREREG 9203ccd, gate dAUC >= +0.005. **FAIL, falsified:** PT-lag mean -0.0578, min -0.366 (ep42), MPPE +0.27 cm, > 3 cm 955 to 1115; PT-all -0.1319. 5 of 17 flagged spans real. KLT slips on weak texture in grasps. CoTracker3 rejected (CC-BY-NC).

## Policies and following (RL training, recipes, retrains, sim, seeds, flips)

- **31 Oct, eval-10 V4p, ep11 gate: PASS.** Registered AUC vs mocap dAUC +0.142 (bar +0.05): seed 42 0.5947 to 0.6073 (+0.013); seed 43 0.5899 to 0.8613 (+0.271); beige +0.321, blue -0.037.
- **31 Oct, eval-10 V4p full retrain, 2 seeds + 10 draws: NO-SWAP.** Blue cup never lifted. New vs packed 0.459 vs 0.463 (V); 0.449 vs 0.453 (P); both fail 10/10 at RPE ~15.9 cm. $3.25.
- **31 Oct, masses v2 (2 boxes): NOT ADOPTED.** Mean +0.0034 (bar +0.03), 1/4 positive (needs 3): ep24 +0.038, ep11 -0.014, ep13 -0.002, ep31 -0.009.
- **Recipe screen (determined-wright, 31 Oct to 1 Nov, ~$30.15):** K inconclusive (-0.002); D inconclusive (sd fell on one ep); S no signal (ep2 -0.133); V (actor sees velocity) -0.024 (ep2 -0.049, ep12 -0.026). No recipe change; owner: "No D" (31 Oct 20:31).
- **Targeted D arm (owner "sure add that whatev", 31 Oct 20:40):** evals 14/16/25/30/33, 2 seeds; pack 9b (1 Nov 04:55) swapped only eval 33 (0.9358 vs 0.9234, 0 fails each). Eval 14 NO-SWAP (0.686 vs 0.727; fails 8 vs 4); 16 (0.831 vs 0.850); 25 (0.858 vs 0.878); 30 (0.816 vs 0.897). $19.41.
- **Eval 10 legal retrain ev10cs5 (carved pieces, stock limits), pack 10:** GT-free proxy +0.069 vs V, +0.059 vs P.
- **njmax-1024 training, eval 10 (pack 11):** trained at 1024, evaluated at stock 512/256 (disclosed). Proxy +0.371 (V) / +0.361 (P); fails 0/10 vs 10/10. Packed after owner's 1 Nov 09:11 "I give give you go".
- **Two-hand, PF batch 1 (1 Nov):** pfA public ep13 seed 42 s 0.378 +/- 0.110 vs 2h 0.587 +/- 0.156; seed 43 0.554 vs 0.553; mean paired dAUC +0.104, PASS but one seed carries it [I]. pfB evals 14/16 two-hand NO-SWAP (14: 0.603 / 0.581 vs 0.727; 16: 0.713 / 0.696 vs 0.850).
- **Guard bridge (GT-free repair of 11 to 20 cm re-acquisition jumps; batch 2, 2 Nov):**
  - Eval 14: bridged single-hand seed 43 box 0.892 (s42 0.880). Fresh vs bridged ref B: 0.875 (packed 0.706), fails 1/10 vs 4/10, median RPE 2.71 vs 4.38 cm; vs P 0.861 vs 0.727. **PASS + INCLUDE** (00:32).
  - Eval 32: vs B 0.890 (packed 0.851), fails 0/10 vs 4/10; +0.040. **PASS + INCLUDE** (00:58).
  - Eval 33: vs B 0.9395 (packed 0.9199); +0.0196 < +0.02. **PASS, NOT INCLUDED** (01:05).
- **Eval 16 hold-to-end (pfF):** s 0.687 +/- 0.083 vs se 0.769 +/- 0.021 (seed 42); seed 43 0.719 vs 0.792. NO-SWAP (packed 0.850, 24 Oct recipe).
- **Eval 16 spoon kept in hand from f107 (pz, pfG):** seeds 0.975 +/- 0.009 and 0.972 vs control p0 0.769 / 0.787. Fresh 10 draws 0.974 vs 0.850; fails 0/0; median RPE 1.18 vs 1.79 cm; +0.124. **PASS + INCLUDE** (2 Nov 06:30).
- **Lift-window training (PF, pfH public ep31, pre-registered):** lw 0.730 +/- 0.017 vs s 0.589 +/- 0.198 (seed 42); seed 43 0.704 vs 0.707. Paired dAUC +0.141 / -0.002, mean +0.069. **PASS.** [I] gain is seed 42 where control collapsed (sd 0.017 / 0.043 vs 0.198 / 0.104).
- **Lift batch on evals (2 Nov, 1 of 8 swapped):** eval 3 NO-SWAP (0.888 / 0.886 vs 0.933). Eval 14 box 0.923 passed gate, fresh 0.826 +/- 0.118 vs 0.875: NO-SWAP (box-to-fresh gap -0.097). Eval 15 fresh 0.958 vs 0.906 (+0.053), 0 vs 1/10 fails, clause c failed (1.346 vs 1.299 cm). **Eval 20 PASS + INCLUDE** (seed 43 box 0.921; s42 0.297 collapse; fresh 0.926 vs 0.893, 0/0 fails, RPE 1.378 vs 1.671, +0.033). Evals 25 (0.529 / 0.541 vs 0.878), 28 (0.864 vs 0.919), 30 (0.787 / 0.839 vs 0.897), 32 (0.876 vs 0.890): NO-SWAP.
- **Tier B collision meshes as swaps (pf-mesh, 2 Nov):** eval 14 p0m (rack + blue cup) box s43 0.946; fresh 0.933 vs 0.875; fails 0 vs 1/10; RPE 1.97 vs 2.71 cm; +0.058. **PASS + INCLUDE** (23:27). Eval 20 pitcher: zero-shot 0.451 (control 0.926); seeds 0.293 / 0.604 +/- 0.266, NO-SWAP. Eval 28 rack seed 43 0.914 vs 0.919, NO-SWAP. Eval 30 sweeper+rack: box s42 0.938 passed gate; fresh 0.768 vs 0.897, fails 5/10 vs 1/10, RPE 4.74 vs 2.93 cm, -0.130. NO-SWAP.
- **pf-mesh2 (3 Nov, ~$11 of $35):** eval 33 cup 0.917 vs 0.923; eval 32 cup 0.790 / 0.826 vs 0.890; eval 19 sweeper 0.828 / 0.655 vs 0.929 (zero-shot 0.226). All NO-SWAP.
- **Evaluator-gap test (pfgA, 3 Nov, ~$1.1):** hypothesis: patched training evaluator explains low fresh means. **NOT REPRODUCED**: eval 30 s42 A 0.935 / B 0.926 / C 0.930; eval 14 s42 A 0.925 / B 0.937 / C 0.938. Gap remains [H, unexplained]. No re-test.

## Grasp and references (contact labels, reference building, lift windows, grip)

- **hold_filter (GRASP, 1 Nov):** public gate **FAIL** (M2 zero-action symmetric -0.018 vs needed >= +0.02; M1 +0.0017 holds). Catches eval 32 flip f21 to 33 and edits eval 14 f28 to 52; misses eval 33 f91 jump. Not used.
- **RPE decomposition (PF, 31 Oct, public):** P_o vs mocap RPE 1.66 / MPPE 1.90 / AUC 0.890 over 20 eps; without ep23 1.00 / 1.18 / 0.935. Constant per-object offset dAUC +0.050, dRPE -0.22; anchor frame-0 orientation +0.026, dRPE 0; still frames at truth +0.055, dRPE -0.12. Reference costs 1.2 to 2.1 cm per rollout; successful draws 1.4 to 3.5 cm; failed draws 10 to 77 cm. GT-free RPE vs own reference r = 0.9998 vs mocap over 70 draws. K1 rest-hold / K2 initial-hold FAIL (+0.001).
- **Eval audit (GT-free, 16:45 31 Oct):** only eval 10 fails (beige cup left behind, RPE 15.76, 0.79 cm of board RPE; fix -> board ~3.24 [E]). Reference/registration side ~1.48 cm of board RPE [M]. Borderline: evals 32 (3.69), 14 (3.39), 1 (2.89).

## Meshes and CD-O (templates, scans, registration, mesh tiers, mesh adoption)

- **C0 (bold-albattani, 5cce3d2):** pot, lid, rack, blue cup. Public-twin AUC guard (51 runs, 15 twins), pack-9a configuration: mean +0.0079, min -0.0092, dRPE -0.121 cm. Flags kept in README: 7 mm marker-ball radius from public scans (window 5 to 9.5 mm); lid and rack 2.5 mm walls equal once-leaked values. Frame check: pot YES, lid YES (borderline), rack YES (2.3 deg; ~10 mm at ends), blue cup NO (6.7 mm axial) and held back.
- **C1 (AUC-guarded, pre-registered):** ADOPTED beige cup T1 (obs-lathe ep11): CD-O eval 10 0.856 to 0.248; eval 8 0.730 to 0.255; guard +0.008. ADOPTED dust pan T2: 0.331 to 0.260; guard +0.012. NOT adopted: generate-then-fit (fails guard); generated pitcher and beige (15 to 28 mm offsets). Board CD-O estimates: 9a 0.367; with C1 0.333; plus blue cup 0.300 [E].
- **E0b (scan-free, from eval data, 23:55 1 Nov):** pot ep3 thick; beige ep8 g1. Public CD-O worse than 9a+: pot 0.392 vs 0.342; beige 0.30 vs 0.25. Sim flags: 17 of 32 pot marker balls below base; beige has three inside-out shells. Not adopted; 9a+ kept.
- **Per-episode clean meshes as FoundationPose templates (Set B, 14 meshes), re-track test: FAIL** (PF, 31 Oct): mean dR -0.170 (bar +0.01), 3/20 positive (bar 12), min -0.973, dRPE +1.32 cm. White pot and two-cup templates break tracking (ep45 0.980 to 0.006; ep0 0.962 to 0.037; ep11 0.898 to 0.193). $1.54.
- **Pose-board mesh CV (13p baseline, 10 seeds, leave-one-episode-out, 1 Nov 21:50):**
  - PASS mesh: white_pot to X (+0.0206, min +0.0008; 12c/9a+ +0.0183); rack to 12c (+0.0234, min 0.0); water_pitcher to 12c (+0.0121, min +0.0103); wooden_piece_2 to 12c (+0.1274, the flip fix).
  - PASS placement from depth: water_pitcher +0.1064 (min +0.0803; ep21 +0.133, ep22 +0.080); rack +0.0096 (min -0.0077); pot +0.0070 (min -0.0018).
  - FAIL: blue cup, beige cup, sweeper, dust pan (incl. X -0.026), lid, board 1.
  - Eval 20 pitcher placement (13p2): Δ 2.89 deg / 0.47 cm; trimmed RMS 3.81 to 2.57 mm.
- **Round 2 (3 Nov 00:20):** G2 #29 pitcher +0.1125 (ep21 +0.132, ep22 +0.093): not adopted (ep22 not independent). FAIL: blue cup +0.0005, rack -0.0055, pot (none beat X), board 1 -0.033, sweeper, dust pan. Placement on 13p: pot 0.0, rack 0.0, blue cup -0.0022, sweeper 0.0.
- **Bias fit H1 (107 LOO runs, 3 Nov 05:40):** only pitcher passes: H1a +0.046 (ep21 +0.081, ep22 +0.012); H1b-rot +0.038; H1b-trans +0.028; H1c gated depth +0.106. Fails: pot -0.002, rack -0.003, blue cup -0.035, lid -0.002, sweeper -0.20, dust pan -0.11, boards -0.19 / -0.38. Dispersion: pitcher 0.14, lid 0.38 (systematic); pot 1.25, rack 1.7, blue cup 3.0 (not).
- **Round 3 (14p, 3 Nov 08:00):** wooden_piece_2 to G3 #43 PASS (held-out +0.0053, min +0.0046). FAIL: board 1 #24 (mean +0.0275, held-out -0.0064, min -0.013); pot #0 -0.005, #5 -0.004; dust pan #9 -0.027, #15 -0.025, #17 -0.013; rack #26 -0.003. Board 2 shell: ep23 +0.0041 < +0.005, ep24 +0.0055 (source). Rule adopted: source episodes excluded from held-out. 14p1 held (#43 from ep24).
- **Tier B meshes (12e / 13f):** wooden_piece_2 registers flipped 180 deg at some seeds (eval 25 slot 1 179.2 deg; ep24 piece_2 0.862 to 0.000). Public: 9a+ 0.8998 vs M13 0.8746 (ep24 -0.415; pots -0.02 to -0.05; ep0 lid -0.065; ep31 +0.083). Tier B chosen by public-scan CD-O (selection bias). Pitcher decimated to 20k faces (Chamfer 1.4 mm); vs library_v3 pitcher centroid -14 mm z, Chamfer 8 / p95 25 mm.

## Scorer and task understanding (how the metric works, what it rewards, measured facts about the task)

- **RPE** (`metric_code/track_3/RPE.py:543-566`): mean over object pairs of the second object's position in the first's body frame; 0 for single-object episodes; episodes averaged plainly (`:877`).
- **CD-O:** kit rescales submitted mesh to scan (scale non-issue); CD-O re-registers, so rack frame offset does not reduce its gain.
- **Board counting (PR #215 kit):** each board shows its best submission; counted file = selected Final Submission, else best per board. Ties do not penalise later uploads.
- **PR #215 (nvidia-isaac/video_to_data):** leaderboard provisional until containers are checked; Tracks 2 and 3 need policy weights for every sequence, a `run.sh reproduce` entry point and matching hashes. Reproduced score expected "within your own run-to-run variation".

## Leaderboard and submissions (every upload: pack name, date, change, board scores, rank)

Scores in order AUC / SP-SR / MP-SR / RPE / MPPE / CD-O. Ranks as read from the Kaggle API.

- **Standings (31 Oct ~15:00), pack 7 (AUC 0.81460, 30 Oct):** ranks AUC 8, SP 7, MP 8, RPE 11, MPPE 10, CD-O 18 of 20 (0.402). Rank sum 62, **11th**.
- **Pack 9a+ (31 Oct 18:13 to 18:18):** pack 8 + C0 pot/lid/rack + beige T1 (eval 10) + dust pan T2 (evals 19, 38). 0.81757 / 0.85 / 0.65 / 3.87853 / 2.89663 / 0.33234 (was 0.40188). Ranks 8/8/8/11/11/14; rank sum 60, 11th.
- **Pack 9b (1 Nov 04:57 to 05:02; uploaded by keen-heisenberg):** 9a+ with eval 33 D swap. 0.81677 / 0.85 / 0.65 / 3.88283 / 2.90186 / 0.33234. Rank sum 61, 11th. Swap gain "noise on the board".
- **Pack 10 (1 Nov 08:38 to 08:50):** eval 10 ev10cs5 retrain. 0.81915 (new best) / 0.80 / 0.65 / 3.68275 (best) / 2.84759 (best) / 0.33234. Ranks 8/10/8/10/11/14; rank sum 61, 11th.
- **Pack 11 (1 Nov 11:39 to 11:47):** eval 10 njmax policy at stock limits. 0.83921 (best) / 0.85 / 0.70 (best) / 3.17899 (best) / 2.54531 (best) / 0.33234. Ranks 8/10/8/10/10/14; rank sum 60, 11th; 10th DSAIL 59.
- **Pack 12b (2 Nov 06:37 to 06:43):** pack 11 + evals 14, 32 (bridged), 16 (hand held). 0.84405 (+0.0048) / 0.85 / 0.75 (best) / 3.02339 (best) / 2.49546 (best) / 0.33234. Ranks 8/10/9 (tie)/10/10/14; rank sum 61 to **10th**; DSAIL 60.
- **Packs 12e / 13e / 13f (2 Nov ~20:07, Tier B meshes; per keen-heisenberg):** best AUC 0.87225; rank sum 47 (7th).
- **Pack 13 (2 Nov 18:50):** pack 12c + eval 20 plw s43. 0.84924 (+0.00186 vs 12c) / 0.85 / 0.75 / 3.00841 / 2.45263 (-0.0147) / 0.30008. Rank sum 54.
- **Pack 13b (after owner waiver):** pack 13 + eval 15 plw s42 draw. AUC 0.84985.
- **Pack 13p (2 Nov ~22:55):** AUC 0.88257 (+0.0103 vs 13f); RPE 2.22667; MPPE 1.82356. **13p2** (eval-20 pitcher placement): AUC 0.88403.
- **Pack 14p (3 Nov 01:47):** 13p2 + eval 14 p0m rows. **AUC 0.88571; RPE 2.21325; MPPE 1.79779.** Pack 14 (on 13f) superseded.

## Process, cost and infrastructure (GPU rentals, $ spent, bugs, failures, tooling, rules adopted)

- **Spend (logged):** perception session ~$26 [E] (ptrkE ~$4.6; ptrkF $2.7; ptrkG $0.6). Recipe screen ~$30.15 (31 Oct). Eval-10 retrain $3.25. D arm $19.41. Lift batch ~$28 (pfI $6.0, pfJ $5.2, pfK $4.6, pfL $1.45, pfL2 $5.9, pfM $5.0). pf-mesh2 ~$11 (pfS $2.4, pfT $2.4, pfU $6.4, estimates). Evals pfF $3.5, pfG $4.8. Eval-20 pitcher placement box $0.6.
- **Credit (logged):** $127.97 after owner top-up (31 Oct 20:15; cited 2 Nov 20:12); $122.85 (1 Nov ~20:10); $91.37 (2 Nov 06:40; spend $31.48 of $102); $70.53 (12:56); $29.29 (18:02); $75.62 (3 Nov 05:56).
- **Budget decisions:** night tests <= $12 (31 Oct); GPU budget $102 (1 Nov); SAM-6D test <= $6 (2 Nov); +$50 from 07:32 (2 Nov); <= $45 retrain lane, stop below $15 (2 Nov 20:15); pf-mesh2 <= $35.
- **Bugs and failures:**
  - RTX 5090 32 GB OOM in track guard (see Perception).
  - Store `hf download --include` listed the whole repo: 12 to 15 min per episode on ptrkE. Fixed by parallel prefetch and `skip_pull.sh`.
  - ISMr crash: no proposal for an object under 'replace'.
  - pfC on-box scoring used `sets[0]` not `sets[1]`; re-scored on CPU from stored rollouts, rule unchanged.
  - Missing `rtree` on box image (~$0.7); CLONE-FAIL on one host; pfI stalled in setup (destroyed by watchdog, ~$0.9); mistaken ARMS (~$0.03).
  - pfL host fault: 14.4k env steps/s vs ~50k on same code; GPU at 500 W cap; replaced (~$1.45).
  - pf-mesh support-scene path bug (`reconstructed_stage/<seq>_support.usda` missing); fixed at b0b4a31.
  - pfR stale asset root silently skipped the swap; its "0.931" was an old-mesh draw. Fixed c1a5471.
  - Interleaved merge conflict in `glock_public.sh` and `pipeline_ep.sh` (syntax error); restored.
  - Permission guard blocked uploads of pack 9a and pack 12 until owner word was relayed.
  - Timestamps in several entries were estimated ~35 min late; corrected 2 Nov.
- **Rules adopted in the logs:** PREREG committed before any score; falsifier stated; swap rule with 10 fresh draws; two-host confirmation (3 Nov); source episodes excluded from held-out; no best-of-N draws; disclose njmax and training-only settings; never cut a job still making progress; ~30 min stall watchdog; destroy boxes at batch end; do not raise deadlines with the owner (26 Oct, repeated 31 Oct); method name left out of reports, STATUS and commits (2 Nov 07:12).

## Owner decisions and quotes (short verbatim quotes with dates)

- 31 Oct ~15:10 UTC: "Look other people achieved it, I dont care if you are using domain randomization physics based learning or just a better perception model get me into that top tier, Im giving you everything you need if others done it so can you!"
- 31 Oct ~15:30 UTC: "Lets do all the improvements that we planned and lets prepare a pack so that we see where we stand, like better perception better mesh better physics."
- 31 Oct 16:35 UTC: "Ship 9a, flagged".
- 31 Oct 18:13 UTC: "Upload which you think of the highest score potential".
- 31 Oct 20:40 UTC: "sure add that whatev" (targeted D arm). 20:31: owner chose "No D".
- 2 Nov 07:20 UTC (relayed): "Go do as much as you can lets go to top".

## Lessons stated in the log

- "The tracker's failure mode is chaotic loss of track"; iteration settings are not a precision lever (PT, 2 Nov).
- Small perception changes flip whole tracks; eval perception changes need per-episode checks (PT, ep18).
- Rebuilt references lost to packed ones (eval 16); a rebuild is not an independent test.
- Box gates can overstate fresh draws (eval 14 0.923 to 0.826; eval 30 0.938 to 0.768); two-host or fresh-draw confirmation before inclusion. The evaluator-gap test did not reproduce it.
- Two seeds cannot separate a lift effect from the usual seed split (eval 25). Lift gain on ep31 came from a collapsed control: fewer failed draws, not a higher ceiling.
- GT-free RPE tracks RPE vs mocap at r = 0.9998; RPE has no single dominant reference error type.
- Source episodes must be excluded from their candidate's held-out score (3 Nov rule).
