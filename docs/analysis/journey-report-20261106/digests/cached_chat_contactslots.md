# Fix contact-slot labels in mkref references, then the $100 eval rerun batch and third submission (AUC 0.78893, 4th), Oct 25-27

### session
session_01FtXg7AwcVxLPzSrYtsfQW8

### period
2026-10-25 09:41 UTC to 2026-10-27 04:02 UTC. Active work ran 25 Oct 09:41-20:08 UTC. After that there was one owner question and one answer on 27 Oct 04:01-04:02 UTC. Owner times are often given in TRT, which is UTC+3.

### role_in_project
Cloud Claude Code session started from the desktop app on branch `claude/inspiring-mendel-lbgp9e`: Opus 5.5, effort xhigh, local scratchpad id 7b7a381a. It was moved forward onto `main-bsky37` and merged back into it twice. It did three jobs:
- a code and report correctness fix: the contact-slot names in mkref references, done on CPU only;
- a written answer on what the mesh research taught;
- the main event: the owner's $100 top-up. The session ran the pre-registered eval rerun batch (13 Vast boxes in total), packed and uploaded the third Track 3 submission, and moved the team from 9th to 4th on AUC (0.58252 to 0.78893).
It ran alongside at least two other chats on the repo. One of them, on `main-bsky37`, launched a duplicate batch on the same go-ahead.

### summary
The session opened at 25 Oct 09:41 UTC with a detailed brief the owner pasted in.

**Contact-slot fix (09:41-10:13 UTC).** `pipeline/mkref.py` stage (e) fills the 16 hand-object contact slots in PROBE_SITES order: the 5 tip sites, the 5 DP sites, thumb_MCP_VL and the index-to-pinky MP sites, then the palm mean in slot 15. But the parquet's `mano_link_names` column is in MANO link order. Four analysis scripts read it as slot labels, so "palm" was really the thumb tip, "thumb1-3" were the index, middle and ring tips, and "pinky3" was the palm.
- The session fetched the kit at the evaluator pin 8c778f90. FlashCHORD's `load_reference` never reads `mano_link_names`, and the kit's `ManoSharpaData.from_parquet` drops extra columns.
- It asked the owner through a question widget. The owner picked "New column (Recommended)".
- It added a `contact_slot_names` column in mkref, a shared helper `tools/contact_slots.py` and `tests/test_contact_slots.py` (7, then 10 tests pass, including the kit round trip on ep12).
- It fixed `human_grasp_census.py`, `mano_contacts.py`, `mano_where.py`, `refload.py`/`human_board.py` and `contact_plot.py`. The `ct_*.png` plots had been mislabelled too.
- Before fixing anything, it reproduced every old table byte-identically from the HF-store references.
- It added dated correction notes and corrected tables to four reports, as additions only (about 140 lines). Main corrections:
  - ep2 lid palm 0.76-0.80 is really 0.00; it was the thumb tip;
  - pitcher palm 0.33 is really 0.92;
  - the pot handle reading is reversed;
  - plate thumb-vs-finger opposition 0.38-0.69 is really 0.05-0.22.
- Commits 790e789, 6a00df1 and 2403a08. Training was unaffected. The only check still open is an end-to-end mkref run on a GPU box.

**Mesh-research answer (10:21 UTC).** The owner asked "What did we learned from mesh research btw?". The answer's main point: pose accuracy, not mesh shape, limits the score. On the leaderboard, CD-O rank tracks AUC rank only weakly (Spearman -0.51), while MPPE tracks it strongly (-0.97). Meshes matter mainly through physics in the simulator:
- the sweeper underside, the pitcher's missing flat base (the arc foot fix), the beige cup's cone tip, and the solid lower 37% of the blue cup;
- simulator collision inflation of up to about 9 mm;
- v5 meshes lost to v2 on CD-O;
- the owner's approaches 1 and 2. The finding that eval 25's two boards are swapped in our perception was the biggest one.

**$100 top-up and batch (14:45 UTC onward).** The owner wrote: "I topped up 100 buck go and get me a proper score, I need the ranking". Credit was $101.82; we were 9th at AUC 0.58252. The session launched 9 boxes (about $13.4/h) at code ee7ba8e / 02de0c7:
- `eval_both` rebuilds for 8+10 (library_v3x), 14+20 and 32+33;
- `std_learner` (the second learner) for 1+16, 19+28 and 30;
- the ep21 arc-foot twin (two arms);
- an eval-25 box with the newly ported GT-free board identity check (`pipeline/identity_fix.py`).

At about 15:52 it noticed that the `main-bsky37` chat had also got a go-ahead and launched 6 duplicate boxes. It messaged that chat, which destroyed them in setup.

It also found its own mistake: `eval_both.sh` defaults (REPLAN=1, EVOLVE=0, no onset anchor) are not the frozen recipe behind the submitted policies. The owner asked:
- "Wait what do you mean why did the number increased";
- "Do we need all there is the other chat";
- "Wait only run the extra if it makes sense".

The session explained, then added 4 frozen-recipe boxes (about $12) under a 3-way choice rule fixed before any results.

Over the evening:
- the arc foot passed its pre-registered twin test (ep21 0.657 to 0.772 vs mocap);
- the second learner won evals 1, 19, 25, 28 and 30;
- the frozen recipe won 32 and 33;
- eval 8's grasp lock reached 0.971.

Eval 10 was stopped as not worth it: about 15x slower simulation and njmax overflow from the stacked cups. Failures were handled along the way: an HF xet size-mismatch pull, which led to the new PULL_SUB option, and a missing `/content/assets` in `pack_eval`.

Pack 3 (code 3758189, about $0.7) was uploaded to all six boards at about 20:05 UTC:

| Board | Score | Rank |
|---|---|---|
| AUC | 0.78893 | 4th |
| SP-SR | 0.80 | 5th |
| MP-SR | 0.60 | 4th |
| RPE | 4.59 cm | 4th |
| MPPE | 3.29 cm | 4th |
| CD-O | 0.402 cm | 11th |

This reached the owner's 24 Oct target of 4th place. The top-up cost $54.6, leaving $47.20 of credit and no boxes running.

**27 Oct.** On 27 Oct 04:01 UTC the owner asked "Are the other chats aware of this problem?". The session checked `main-bsky37`:
- its branch had been merged on 25 Oct;
- the other chats use the eval-25 fix and both recipes;
- they had reached six submissions, best AUC 0.814; the 26 Oct submission placed 5th behind DDD (0.827).

The one unfixed issue is two chats acting on the same go-ahead. The session offered to add a batch-ownership rule to CLAUDE.md, pending the owner's approval. The session ends there.

### owner_requests_and_decisions
- **time**: 2026-10-25 09:41 UTC; **owner_said**: Pasted a detailed task brief (from the desktop app). mkref stage (e) fills the 16 contact slots in PROBE_SITES order plus palm, while `mano_link_names` is in MANO order; four analysis scripts mislabel the slots. Tasks: (1) decide with the owner on slot names, e.g. a `contact_slot_names` column, and check FlashCHORD accepts it; (2) fix the scripts; (3) add dated correction notes to biomech §0.2/§9.2, plates audit §3, boards audit §2.2 and starts audit §3.2 without overwriting.; **outcome**: All three parts were done on CPU only, with no rental. Commits 790e789, 6a00df1 and 2403a08 were pushed to `claude/inspiring-mendel-lbgp9e`. The branch was fast-forwarded onto `main-bsky37` 53929d0 and later merged with its T2 commit 3cb24dc. No PR was opened.
- **time**: 2026-10-25 09:57 UTC; **owner_said**: Answered the session's question on how mkref should record slot names. The owner chose "New column (Recommended)": `contact_slot_names` = PROBE_SITES + ['palm'], with `mano_link_names` left unchanged. The rejected options were overwriting `mano_link_names` and fixing the scripts only.; **outcome**: Implemented: `CONTACT_SLOT_NAMES` and `patch_logger(lay, slot_names=True)` in mkref, applied in the main process only (E2S keeps the kit class). The column is written into `loaded/` and `processed/`.
- **time**: 2026-10-25 10:21 UTC; **owner_said**: "What did we learned from mesh research btw?"; **outcome**: The session gave a long summary. Shape score (CD-O) explains little of the ranking, and pose error explains most. Meshes matter through physics: support, nesting, collision inflation. The v5 rebuild lost to v2 on CD-O. On the owner's approaches: carving the collision copy works, carving the submitted mesh does not, lathe primitives help the cups and pot, and eval 25's boards are swapped. Items left waiting on the owner: the eval 25 rerun, the lathe cups for CD-O (with the organiser question), the arc-foot GPU check and the collision carves.
- **time**: 2026-10-25 14:45 UTC; **owner_said**: "I topped up 100 buck go and get me a proper score, I need the ranking"; **outcome**: The session treated this as the go-ahead for the pre-registered 03:01 UTC eval rerun batch, which had been waiting on credit, plus a newly pre-registered eval-25 identity repair. It logged the plan at commit ee7ba8e with an estimate of about $50, keeping about $50 in reserve. It launched 9 boxes. It noted that the main-bsky37 chat looked idle, which turned out to be wrong: that chat also got a go-ahead at 15:51 UTC.
- **time**: 2026-10-25 15:54 UTC; **owner_said**: "Wait what do you mean why did the number increased" / "Do we need all there is the other chat" / "Wait only run the extra if it makes sense"; **outcome**: The session explained that the box count rose from 9 to 13 because it had added 4 frozen-recipe boxes itself, to correct its launch with the older eval_both defaults. Public evidence vs mocap, older vs newer recipe: ep18 0.30 vs 0.96, ep39 0.17 vs 0.96, ep24 0.20 vs 0.24. The other chat had launched 6 duplicate boxes and destroyed them after this session's message. The session recommended keeping the extras (about $12, total about $70 of $100) and offered to stop them. The owner gave no further reply, so they ran. The owner's "only if it makes sense" was later applied: eval 10's training and the standard learners for 8 and 10 were stopped at about 17:52 UTC.
- **time**: 2026-10-25 17:53 UTC; **owner_said**: (Applying the owner's 15:54 instruction, "only run the extra if it makes sense"); **outcome**: Eval 10's grasp-lock trainings were killed: 2.4k env steps/s, njmax overflow, ETA over 5 h, about $15 more. A watcher made the evb0810 box skip its standard learners for 8 and 10, which would have taken 5-10 h each. Eval 10 kept its pack2 policy.
- **time**: 2026-10-25 20:08 UTC; **owner_said**: (The session reported the result to the owner. The target "aim for 4th place" had been set by the owner on 24 Oct.); **outcome**: AUC 0.78893, 4th, up from 0.58252 (9th). The session listed next options, none started: fix eval 10's cup collision; extra seeds for the variable episodes 25 and 33; the second learner for 3 and 16; smoother cup/pot meshes for CD-O, which needs the owner's decision on the organiser question.
- **time**: 2026-10-27 04:01 UTC; **owner_said**: "Are the other chats aware of this problem?"; **outcome**: The answer was "mostly yes". The branch had been merged into main-bsky37 on 25 Oct. The other chats use the board-swap fix and both recipes, work on the eval-10 stack (box `20261027-e10Z-aa7b5f8` was running), have six submissions with best AUC 0.814, and found a bug where the launch script defaulted to the 20 Oct code. The unprevented problem is two chats launching the same work, with at least three chats on the repo. The session offered to add a CLAUDE.md rule (check `ops/vast.sh show` and the latest work-log entries, and launch only if no other chat has started the same batch) and asked the owner to approve. There was no reply in this session.

### experiments
- **time**: 2026-10-25 09:49 UTC; **what**: Reproduced the existing slot-order evidence: `slot_order_check.py` on the ep12 perc2mc reference, and `digit_shares.py` on the 11 tags of approach3 `out/inputs.txt`. Inputs were 19 files (27 MB) from the HF store. CPU, cloud VM.; **result**: Each slot lies within threshold of PROBE_SITES[k] in 97-100% of its active frames. Slot 0, which the MANO list calls palm, has the palm probe within threshold in only 19%. `digit_shares` output is byte-identical to the committed `digit_shares.txt` (35 holds).; **verdict**: The mislabel was confirmed. Measured, GT-free.
- **time**: 2026-10-25 09:58-10:02 UTC; **what**: Kit round trip of the new `contact_slot_names` column: the stage (e) write path on the ep12 reference, read back with the kit class, the extended class, pyarrow and FlashCHORD `load_reference` at pin 8c778f90. Run with pytest in `tests/test_contact_slots.py`.; **result**: 7 passed: identical kit fields, contacts, wrists and fingers (181 frames, 20 fps). 10 passed later with the full test folder.; **verdict**: Compatible. Not yet checked inside a real GPU mkref + E2S run.
- **time**: 2026-10-25 10:03-10:08 UTC; **what**: Reproduced the old report tables with the pre-fix scripts (commit 53929d0), then reran them with the fixed scripts into new versioned files. Covered: biomech census for 7 episodes, plates `mano_where`, boards ep24 `--mano`, starts audit windows for ep2/ep21/ep26, and `check_digit_shares.py`.; **result**: The old census is byte-identical on all 7 episodes. Corrected readings:
- ep2 lid palm 0.76/0.80 is really thumb_tip 0.76/0.80, with palm 0.00;
- pot handle reversed: palm at -18 to -21 cm, thumb at -11 to -15 cm;
- plates thumb share 0.09-0.52 and opposition 0.05-0.22, against 0.38-0.69 before; palm 0.00-0.02 except the ep39 carry at 0.73;
- boards drag "palm 0.79" is the thumb tip (palm 0.14), and the standing hold has thumb 0.00;
- starts audit: lid palm 0.00 (was 0.50), pitcher palm 0.92 (was 0.33), ep26 pot palm 0.70.
The helper matches `digit_shares` on 35 holds with 0 mismatches. Load and geometry columns are unchanged in all 24 holds.; **verdict**: The corrections were published as additions. Three design claims lose their human-contact basis: the plates "human's clamp" and the F4 "palm on the knob" lid design among them. Forces, robot geometry, failure verdicts and training are unaffected.
- **time**: 2026-10-25 ~14:52-15:10 UTC; **what**: The eval-25 board identity rule (approach-1 knob rule R1, GT-free), run on the stored eval-25 poses (frames 0,2,4,6; library_v3 boards). It was ported to `pipeline/identity_fix.py` and validated on public ep24.; **result**: Stored track: best assignment is swapped, with wooden_piece_1 taken from the old wooden_piece_2 at Rx (180° about x), score -20.9. The as-tracked assignment scores +50.0, rank 21 of 32. On ep24 the good 21 Oct track is kept (-79.9, rank 1) and the 24 Oct w1 track is flagged (as-tracked rank 22). The approach-1 repair had taken that track from 0.029 to 0.706 vs mocap. The port reproduces the scores exactly and is idempotent.; **verdict**: Adopted as a pipeline step (`ops/jobs/eval_idfix.sh`). On the box, fresh perception named the boards correctly (as tracked -63.9, rank 1 of 32), so nothing was applied. perc2's board naming is close to a coin flip.
- **time**: 2026-10-25 15:55-16:23 UTC; **what**: Public ep21 arc-foot twin (pre-registered rule from 02:40 UTC: adopt iff arc AUC ≥ base - 0.02 and the pitcher's AUC under arc ≥ base). Frozen recipe, 5 official evaluations each, only SF_ARC differs. Boxes `20261025-twin21base-ee7ba8e` (Japan Max-Q $1.43/h) and `-twin21arc-` (Czechia Max-Q $1.56/h).; **result**: Base: registered AUC vs mocap 0.6565 ± 0.093 (0.471-0.721); pitcher 0.414; blue cup 0.899; sim_vs_ref 0.8645. The pitcher was UNSTABLE and fell 117.5 mm / 70.9° by f19. Arc: 0.7723 ± 0.009 (0.766-0.790); pitcher 0.591; cup 0.954; sim_vs_ref 0.983. Cost about $1.6 + $2.3.; **verdict**: ADOPTED. Eval 20's rebuilt policies, which already have the arc foot, became eligible for the pack.
- **time**: 2026-10-25 16:49 UTC; **what**: std30: the second (standard FDR RL) learner for eval 30 on the ev30rp reference, 250M steps.; **result**: sim_vs_ref 0.9188 ± 0.012 (0.904-0.934), against the pack2 grasp-lock policy at 0.7216 (0.304-0.929, bimodal). Took about 1.8 h, cost about $3.; **verdict**: Chose the standard learner. Like-for-like comparison.
- **time**: 2026-10-25 17:05 UTC; **what**: fr25: frozen-recipe grasp lock for eval 25 on the identity-correct reference (Croatia Max-Q).; **result**: Search windows 0.296 to 0.401 and 0.137 to 0.300. Chose 50M; sim_vs_ref 0.297 ± 0.008, against eval_both's grasp lock at 0.376. Took about 1.1 h, cost about $1.6.; **verdict**: Lost. The newer recipe was worse here.
- **time**: 2026-10-25 17:21 UTC; **what**: fr1420: frozen-recipe grasp lock for evals 14 and 20 on the rebuilt references.; **result**: ep20 0.8888 ± 0.019 against eval_both's 0.8923. ep14 0.6293 ± 0.167 against 0.6595. Took about 1.4 h, cost about $2.3.; **verdict**: Near tie. Eval_both won both at choice time.
- **time**: 2026-10-25 17:25 UTC; **what**: ev25idfix: eval 25 rebuilt with the identity check, then grasp lock (eval_both), then the standard learner.; **result**: Grasp lock 0.3759 (below the 0.9 gate). Standard learner 0.712 ± 0.189 (0.335-0.815). Pack2's eval-25 rollout had scored 0.232 against the swapped reference. Took about 2.6 h, cost about $3.8.; **verdict**: Chose the standard learner, the biggest single fix. Its variance is high.
- **time**: 2026-10-25 17:51-17:57 UTC; **what**: fr3233 and fr0810b: frozen-recipe grasp locks for 32/33 and for 8 (with library_v3x).; **result**: ep32 0.779 ± 0.045 (30M) and ep33 0.7728 ± 0.053 (60M), against eval_both's 0.4969 and 0.4857. ep8 0.7615 ± 0.022 (20M). fr3233 took about 1.9 h and cost about $3.2.; **verdict**: The frozen recipe won 32 and 33 decisively. It lost on 8.
- **time**: 2026-10-25 17:52 UTC; **what**: Eval 10 grasp-lock training: v5 beige cup stacked in the v3 blue cup.; **result**: 2.4k env steps/s, against about 45k normally. 32% after 2.5 h, ETA 5:25. MuJoCo-Warp printed "nefc overflow - please increase njmax" on every step. fr0810b managed 8.9k steps/s, at 62%.; **verdict**: Stopped. Eval 10 keeps pack2. The real fix is carving the cavity in the blue cup's collision copy.
- **time**: 2026-10-25 18:08 UTC; **what**: evb0810: eval 8 grasp lock (eval_both recipe, library_v3x, rebuilt reference).; **result**: 0.9705 ± 0.016 (0.942-0.985), above the 0.9 gate. The old submission tracked 0.82 on the old reference. The ep8 run was slow at 6.5k env steps/s, against a usual 45k: the v5 beige cup has 32 collision pieces.; **verdict**: Chose the grasp lock over the frozen recipe (0.7615).
- **time**: 2026-10-25 18:10 UTC; **what**: std0116: standard learner for evals 1 and 16 on the stored references.; **result**: Eval 1: 0.9122 ± 0.014 (200M) against the grasp lock's 0.2969. Eval 16: 0.7691 against the seed-43 grasp lock's 0.8045. Took about 3.2 h, cost about $4.8.; **verdict**: Eval 1 went to the standard learner, a big win. Eval 16 kept its grasp lock.
- **time**: 2026-10-25 18:42 UTC; **what**: std1928: standard learner for evals 19 and 28.; **result**: Eval 19: 0.935 against 0.6534. Eval 28: 0.9347 against 0.6938. Took about 3.7 h, cost about $5.8.; **verdict**: Both went to the standard learner.
- **time**: 2026-10-25 19:12-19:24 UTC; **what**: evb3233 and evb1420 standard learners, then the 3-way choice (`choose3.sh` = `tools/choose_learner.py`; yardstick = standard-learner rollouts).; **result**: Standard learners: ep32 0.2988, ep33 0.2487, ep14 0.6192, ep20 0.1461. Choices: ep32 and ep33 to the frozen recipe (0.779 / 0.7728); ep14 to the eval_both grasp lock (0.6595); ep20 to the eval_both grasp lock (0.8923). Each box took about 4.3-4.4 h and cost about $6.4. The script reproduced eval 25's numbers exactly (std 0.712, glock 0.3759, frozen 0.297).; **verdict**: Choices fixed without ground truth.
- **time**: 2026-10-25 19:30-19:59 UTC; **what**: Pack 3 on box `20261025-pack3-3758189` (British Columbia, $1.35/h, code 3758189), using `pack_eval.sh` with RUN@refs pulls. One fresh official rollout each for 1, 8, 14, 19, 20, 25, 28, 30, 32 and 33; pack2 rollouts kept for 3, 5, 6, 10, 15, 16 and 35-38.; **result**: 20 of 20 checkpoints. 1,387,467 B, sha256 dc3a5ad1…, 0 mesh warnings. Packed sim_vs_ref mean 0.883 (pack2 0.7218). Per episode: 1 0.920, 8 0.978, 14 0.909, 19 0.928, 20 0.895, 25 0.837, 28 0.929, 30 0.923, 32 0.789, 33 0.611 (a low draw; its 5-eval mean was 0.773). About 30 min, about $0.7.; **verdict**: Packed and uploaded.

### uploads_and_scores
- Board status before this session's upload, at 14:55 UTC on 25 Oct: AUC 0.58252, 9th. The others were 1. richchentw 0.93158, 2. SoySauceChicken 0.88399, 3. Zihao Guo 0.86475, 4. SRL 0.75166, 5. DDD 0.72951, 6. Sambhav 0.66228, 7. Alcor Z 0.63618, 8. Zimo Li 0.63037, 10. venkitprasadreddy 0.53230. Only 2 of 5 weekly AUC submissions had been used: 24 Oct 0.575 and 25 Oct 0.583.
- Earlier boards, from the second pack: SP-SR 0.50 (10th), MP-SR 0.40 (7th), RPE 8.82 cm (9th), MPPE 6.69 cm (9th), CD-O 0.405 cm (10th). The first submission on 24 Oct scored AUC 0.57468 (9th), against an estimate of 0.68 (range 0.62-0.72).
- Third submission, 25 Oct about 20:05 UTC. The agent uploaded it through kit `v2d_submit.py` via `tools/kaggle_upload.py`, after a dry run that reported 9,120 rows, 20 episodes, 6 boards and 4 submissions left that day. Message: "25 Oct pack 3: second learner (1,19,25,28,30), rebuilt refs (8,14,20,32,33), eval 25 board identities fixed (commit 3758189)". Scores:
- AUC 0.78893, 4th (ref 57641652);
- SP-SR 0.80000, 5th, tied with 4th;
- MP-SR 0.60000, 4th;
- RPE 4.58961 cm, 4th;
- MPPE 3.28955 cm, 4th;
- CD-O 0.40188 cm, 11th.
On AUC, 5th was SRL at 0.75166 and 6th DDD at 0.72951. The receipts and README are in `results/submissions/20261025-track3c/` (commit eef07f6).
- Competitors' other boards at 20:07 UTC:
- RPE: richchentw 1.34, Zihao Guo 1.94, SoySauceChicken 1.97;
- MPPE: richchentw 1.24, SoySauceChicken 1.64, Zihao Guo 1.83;
- CD-O: Panav Raaj 0.11218, richchentw 0.15970, NVSimranPatil 0.17013, Ujjwal Patil 0.19257, SRL 0.23900, SoySauceChicken 0.25339.
- Other chats' scores, as reported on 27 Oct: six submissions in total, best AUC 0.814. The 26 Oct submission placed 5th behind DDD (0.827).

### problems_mistakes_costs
- MONEY: credit went from $101.82 to $47.20, so the $100 top-up cost $54.6. That includes the other chat's eval-25 video box and its six duplicate boxes destroyed in setup (about $1-2). The plan had estimated about $50; check-ins revised it to about $60, then $60-65; peak spend was about $20/h with 13 boxes. Session API cost was about $8.11 by 14:46 UTC.
- Per-box costs, measured: twin21base about $1.6; twin21arc about $2.3; std30 about $3; fr25 about $1.6; fr1420 about $2.3; ev25idfix about $3.8; fr3233 about $3.2; std0116 about $4.8; std1928 about $5.8; evb3233 about $6.4; evb1420 about $6.4; pack3 about $0.7. evb0810 and fr0810b were unreported.
- SESSION'S OWN MISTAKE: it launched the 6 rebuilt episodes and eval 25 with `eval_both.sh` defaults (REPLAN=1, EVOLVE=0, no `--onset_anchor`). That is an older recipe, not the frozen eval recipe (SF=1 REPLAN=0 EVOLVE=1 CURVE_REP=3 NREP=5 GL_ARGS + `--onset_anchor 1`). It corrected this with 4 extra frozen-recipe boxes, about $12. The frozen recipe then won only 32 and 33, tied on 14 and 20, and lost on 25 and 8.
- DUPLICATE LAUNCH: the owner's go-ahead reached two chats. The main-bsky37 chat (commit a842ab1, 15:51 UTC) launched 6 boxes (`twinA, twinB, eb814, eb3233, std1, std2 -a842ab1`). This session had wrongly judged that chat idle. It messaged the other chat, which destroyed its boxes in setup. By 27 Oct nothing in CLAUDE.md or STATUS prevented a repeat; a rule was proposed but not yet approved.
- fr0810 failed twice pulling a whole still-running run from HF: xet "File size mismatch: expected 112519585 bytes but downloaded 112592196 bytes". It was first misdiagnosed as a race with a push. An in-place restart with `restart_job.sh` failed identically, and the box self-destroyed. Fix: `store.sh pull-run` gained PULL_SUB (commit 4a71eaa). The relaunch `fr0810b` (Australia, $1.51/h) went ahead; the first offer, 56137469, had been taken meanwhile.
- Eval 10 could not be trained: the v5 beige cup stacked in a blue cup whose lower 37% is solid gave njmax/nefc overflow and about 15x slower simulation. Both eval-10 trainings were killed at about 17:52 UTC. The first kill attempt used `pgrep -f` patterns that also matched the remote shell; it killed the trainings but not the watcher install, and was redone with bracketed patterns.
- Wrong work-log timestamps for the launches were corrected: about 14:50-14:52 UTC, not 15:00/15:12. The batch also took longer and cost more than planned, because `hard_ab` runs one standard-learner training per GPU (TRAIN_LOCK).
- Packing gap caught before upload: `pack_eval.sh` never built `/content/assets`, which standard-learner references need. It was fixed in commit 1bc29cb, along with RUN@sub pulls.
- The box monitor printed false "GONE" lines because it misread the instance-count line; this was fixed. HF returned HTTP 429 (rate limit) while 9 boxes pulled at once; the pulls still completed.
- Eval 33's packed rollout was a low draw: 0.611 against a 5-evaluation mean of 0.773. Eval 25's spread was 0.335-0.815. One rollout per episode is noisy, and the session chose not to cherry-pick.
- The kept episodes' local QA numbers on the pack box differed from pack2's summary (3/15/16: 0.875/0.958/0.850 against 0.942/0.947/0.908), even though the rollout files were copied unchanged.
- LATER-FOUND BUG (cross-reference from the repo, `docs/analysis/forensics-20261026/README.md` on later branches, not found in this session): the third submission packed the first pack's seed-42 rollouts for evals 3/5/15/16 instead of the rule-chosen seed-43 ones, per a sha256 check. Estimated impact about +0.005 AUC if fixed.
- The original slot-label bug, which predates this session: four analysis scripts plus `contact_plot.py` and `human_board.py` had mislabelled human contact slots. Earlier report conclusions about the human "clamp", thumb opposition and "palm on the knob" rested on wrong labels.

### learnings
- mkref's 16 contact slots are in PROBE_SITES order: tips 0-4, DPs 5-9, thumb_MCP_VL 10, index-pinky MP 11-14, palm mean 15. The `mano_link_names` column is the kit's MANO list and does not describe them. FlashCHORD uses only any-slot activity and positions, so training was never affected.
- At pin 8c778f90, FlashCHORD `load_reference` / `load_mano_sharpa` read only the columns they name. The kit's `ManoSharpaData.from_parquet` drops extra columns. Our pyarrow-based tools (grasp_lock, contact_retarget, wrist_ilc, support_fill, sim_settle, grasp_evolve) keep extra columns. So adding a column is safe.
- Corrected human-grasp readings, from our perceived hands with no ground truth:
- humans do not use thumb-vs-finger opposition on plates (0.05-0.22);
- the ep2 lid grip has no palm;
- the pitcher is a palm power grasp (palm 0.92).
Designs that cited "the human's clamp" now rest on mechanics only.
- Mesh research summary:
- Pose accuracy, not mesh shape, drives the AUC ranking. Across teams, CD-O correlates with AUC at -0.51 and MPPE at -0.97 (Spearman). The top three have MPPE 1.2-1.8 cm against our 6.7 cm at the time.
- Meshes matter through simulator physics: standing, nesting, slotting.
- Keep two copies of each object: the scored mesh, changed cautiously, and a freely edited collision copy.
- The simulator's default convex decomposition inflates by a few mm, up to about 9 mm, and refills an 8 mm slot; carves must ship as our own convex pieces.
- v5 lost to v2 on CD-O; only the beige cup was kept.
- Lathe primitives cut CD-O for the blue cup (0.523 to 0.307 cm) and the pot (0.437 to 0.319), an estimated package CD-O of about 0.33.
- Box-shaped boards add registration flips.
- The second (standard FDR RL) learner beat the grasp lock clearly on evals 1 (0.912 vs 0.297), 19 (0.935 vs 0.653), 28 (0.935 vs 0.694), 30 (0.919 vs 0.722) and 25 (0.712 vs 0.376). It lost on 14, 16, 20, 32 and 33. Owning both learners and choosing per episode without ground truth (highest mean sim_vs_ref over 5 official evaluations) was the main lever.
- The frozen recipe (EVOLVE grasp search plus onset anchor) mattered a lot on the spoon-in-cup episodes 32 and 33 (0.78 vs 0.50). It did not help on 8, 14, 20 or 25. The old public evidence (ep18 0.30 vs 0.96, ep39 0.17 vs 0.96) did not carry over uniformly.
- Board identity: perc2's naming of the two near-identical boards is close to a coin flip. The GT-free knob rule detects swaps and flips: stored eval-25 track rank 21 of 32 (swapped); fresh track rank 1. A swapped reference scores near zero whatever the robot does. It should become a standard pipeline step, not one tied to a single episode.
- The arc foot under the pitcher (support fill with SF_ARC=1) makes the pitcher stand and stabilises the results: ep21 0.657 ± 0.093 rises to 0.772 ± 0.009 vs mocap, and the pitcher alone from 0.414 to 0.591.
- Heavier collision meshes slow MuJoCo-Warp training a lot. The v5 beige cup (32 pieces) ran at 6.5k steps/s against 45k. Stacked cups with a solid blue-cup bottom overflow njmax and run about 15x slower. Cavity carving of the collision copy is needed before eval 10 can improve.
- Rebuilding references with the latest perception fixes (track guard, support fill, arc foot, v5 beige cup) gave large gains on our own measure: eval 8 0.97, eval 20 0.89 against 0.34 before.
- Our own sim_vs_ref translated reasonably into the leaderboard this time: pack mean 0.883 corresponded to AUC 0.789. Earlier packs had a larger perception gap: on 24 Oct, perception cost 19% on eval against 3-4% on the public twins, with a spoon perception factor of about 0.72.
- Operations:
- Pull only the sub-folders a job needs (PULL_SUB / RUN@refs), not whole still-running runs.
- Standard-learner references need `/content/assets` rebuilt with `make_assets.py`; grasp-lock references carry their own assets.
- The kit uploader extracts and uploads CD-O itself, so one upload covers all six boards.
- `hard_ab` runs one training per GPU, so two-episode boxes take about 3.5-4 h.
- Coordination: several Claude chats on one repo can act on the same owner go-ahead. Batch ownership needs an explicit rule, for example checking `ops/vast.sh show` and the latest work-log entries before renting.

### external_inputs
- The owner's pasted task brief, 25 Oct 09:41 UTC, on contact-slot mislabelling. It cites the evidence in approach3-grasp-taxonomy.md §9 and slot_order_check.py.
- NVIDIA kit nvidia-isaac/video_to_data at evaluator pin 8c778f905cb3. The session read the FlashCHORD loader, mano_sharpa.py, parquet.py and the robotic_grounding data_logger.py.
- Submission kit from https://nvidia-isaac.github.io/video_to_data/v2d_challenge/assets/v2d_submission_kit.zip (v2d_submit.py, tracks.json with the Track 3 competition slugs v2d-challenge-track3-{auc,sp-sr,mp-sr,rpe,mppe}), plus the Kaggle client 2.2.5 with a proxy-injected token.
- HF dataset nvidia/video_to_data_challenge, for the eval-25 cam-c video, the calibration and the public ep24 video. The private HF store is aebatirel/v2d-store.
- Kaggle leaderboard data on competitors: richchentw, SoySauceChicken, Zihao Guo, SRL, DDD, Sambhav, Alcor Z, Zimo Li, venkitprasadreddy, EIG, Gravity Aligned, Open4D, Xueyi Wang (FF), and on CD-O Panav Raaj, NVSimranPatil and Ujjwal Patil, with the scores listed above.
- Vast.ai offers used: RTX PRO 6000 WS/S/Max-Q at $1.35-1.67/h, in Spain, Korea, New York, Virginia, Japan, Czechia, Sweden, the Netherlands, Croatia, Australia and British Columbia.
- Earlier work cited from the repo: the owner's approaches 1-3 (motion-constrained meshes, primitive meshes, grasp taxonomy), notes 19 (collision hulls) and 25 (support-consistent meshes), the mesh-v5 decision, and the robustness review of 26 Oct on main-bsky37, which the session read on 27 Oct. The owner's earlier list of learned grasp models (GraspGen/-X, DexGraspNet 2.0, DexEvolve, DemoGrasp) appears in the work log. HOGraspNet (ECCV 2024) is cited in the taxonomy report.
- Messages to and from the parallel main-bsky37 session: on 15:53 UTC this session sent the duplicate-batch notice and asked the other chat to hold launches. The other chat also ran a video-render box `20261025-vid25-b7dac7f` at the owner's request: eval 25's policy with the robot hands, about $0.3-0.5.

