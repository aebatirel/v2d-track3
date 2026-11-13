## 2. Scores and where the points came from

The chart shows our best-so-far AUC as a line and every one of the 26 uploads as a dot; hover over a dot to see which pack it was.

{{CHART_BOARDS}}

All board numbers in this section are [M] from the Kaggle API. AUC, SP-SR and MP-SR are "higher is better". RPE, MPPE and CD-O are "lower is better" (centimetres). Each board keeps each team's best upload, so a worse upload costs nothing on that board.

### AUC change per upload

Each bar is that upload's AUC minus the best AUC we had before it. Packs 12d, 13h, 13i and 13j were CD-O-only variants: they deliberately gave up AUC to lower CD-O, so their negative bars are planned, not failures.

{{CHART_DELTAS}}

### Attribution: which lever gave which points

Each row compares an upload with the upload it was built on (its base), so only one change, or one named group of changes, separates them. AUC, SP-SR and MP-SR changes are absolute; RPE, MPPE and CD-O changes are in cm (negative is better). "-" means CD-O was not uploaded with that pack and the board kept the older value.

| Lever group | Upload vs its base | Change | dAUC | dRPE cm | dMPPE cm | dCD-O cm |
|---|---|---|---|---|---|---|
| Detection and identity | pack 2 vs pack 1 | eval 30 sweeper detection fix + seed-43 picks (evals 3, 5, 15, 16, 19) | +0.00784 | -3.76471 | -1.96534 | - |
| Reference rebuild (mixed) | pack 3 vs pack 2 | track-guard references (8, 14, 20, 32, 33), second learner (1, 19, 25, 28, 30), eval 25 board identities, eval 20 arc foot, v5 beige cup | **+0.20641** | -4.23036 | -3.40366 | -0.00325 (vs pack 1) |
| Simulator collision carving | pack 4 vs pack 3 | carved collision copies (eval 10 cup cavity, eval 25 board slots), eval 33 s43, seed-43 rollouts restored | +0.02163 | -0.55647 | -0.35365 | - |
| Submitted mesh (failed) | pack 5 vs pack 4 | lathe pitcher on eval 20 + eval 32 s46 + eval 10 gl10A2 | -0.00115 | -0.02473 | +0.02636 | - |
| Submitted mesh (revert) | pack 6 vs pack 5 | lathe pitcher reverted to library_v3 | +0.00450 | -0.06665 | -0.03733 | - |
| Policy swap | pack 7 vs pack 6 | eval 33 from arm B (10-draw confirmed) | +0.00069 | -0.00997 | -0.00367 | - |
| Submitted mesh (CD-O) | 9a+ vs pack 7 | C0 pot, lid, rack; C1 beige cup, dust pan (+ fresh eval 1 draw, about +0.0002 [E]) | +0.00297 | -0.05326 | -0.02463 | **-0.06954** |
| Policy swap (failed) | 9b vs 9a+ | eval 33 start-randomisation (D arm) rollout | -0.00080 | +0.00430 | +0.00523 | 0 |
| Policy retrain | pack 10 vs 9a+ | eval 10 retrain on cavity-safe collision pieces | +0.00158 | -0.19578 | -0.04904 | 0 |
| Training fix | pack 11 vs pack 10 | eval 10 trained at njmax 1024 (training only) | **+0.02006** | -0.50376 | -0.30228 | 0 |
| Reference repair | 12b vs pack 11 | evals 14, 32 guard-bridged; eval 16 hand held through release | +0.00484 | -0.15560 | -0.04985 | 0 |
| Submitted mesh (CD-O) | 12c vs 12b | C0 blue cup on 5 evals | +0.00333 | -0.01496 | -0.02810 | -0.03226 |
| Submitted mesh (CD-O variant) | 12d vs 12c | pre-registered T3 pot and pitcher | -0.00733 | +0.13376 | +0.05724 | -0.00979 |
| Lift-window retrain | 13 vs 12c | eval 20 lift window | +0.00186 | -0.00002 | -0.01473 | 0 |
| Lift-window retrain | 13b vs 13 | eval 15 lift window | +0.00061 | +0.00434 | -0.01671 | 0 |
| Submitted mesh (Tier B, GT-informed) | 12e vs 12d | rack x5, sweeper x2, pitcher, boards on eval 25 (10 mesh rows, no pose row) | **+0.02900** | **-0.75081** | **-0.57191** | -0.02254 |
| Lift windows under new meshes | 13e vs 12e | 13b poses + 12e meshes | +0.00261 | +0.00340 | -0.03089 | 0 |
| Submitted mesh (Tier B+) | 13f vs 13e | generated blue cup and dust pan | +0.00059 | -0.01218 | +0.00350 | -0.00526 |
| Mesh veto (D1 no-flip) | 13f1 vs 13f | eval 25 board 2 back to library_v3 | -0.00034 | -0.00740 | -0.00017 | +0.00144 |
| Pose-board mesh by public CV | 13p vs 13f1 | TSDF pot (6 evals), library_c0 rack (5 evals) | **+0.01066** | -0.14853 | -0.10157 | +0.00476 |
| Placement from depth | 13p2 vs 13p | eval 20 pitcher placed from its own stereo depth (GT-free) | +0.00146 | -0.00136 | -0.01424 | 0 |
| Policy retrain | 14p vs 13p2 | eval 14 retrain with Tier B collision | +0.00168 | -0.01206 | -0.01153 | 0 |
| CD-O variant | 13h vs 13f | G2 generated pot, blue cup, rack (best-of-N on public scans) | +0.00776 | -0.10175 | -0.07272 | -0.01090 |
| CD-O variant | 13i vs 13h | G3 pot, dust pan, board 1 | -0.00408 | +0.04737 | +0.04122 | -0.00982 |
| CD-O variant | 13j vs 13i | round-R rack | +0.00055 | -0.01121 | -0.00508 | -0.00321 |

Success-rate changes, in episodes (20 eval episodes, so one episode = 0.05): pack 2 +1 SP / +1 MP; pack 3 +6 SP / +4 MP; pack 4 +1 SP / +1 MP; pack 10 -1 SP (an eval 10 cup that now moves about 10 cm but does not nest [H]); pack 11 +1 SP / +1 MP; 12b +1 MP; 12e +1 SP / +1 MP. No other upload changed a success rate.

#### Totals by lever (kept changes only, AUC)

| Lever | AUC gained | Share of the +0.31103 total | Uploads |
|---|---|---|---|
| Reference rebuild, learner change and identity fixes (pack 3) | +0.20641 | 66 % | 1 |
| Submitted-mesh changes on the pose boards (9a+, 12c, 12e, 13f, 13f1, 13p) | +0.04621 | 15 % | 6 |
| Policy retrains and training fixes (packs 7, 10, 11, 14p) | +0.02401 | 8 % | 4 |
| Simulator collision carving (pack 4) | +0.02163 | 7 % | 1 |
| Detection fix + seed picks (pack 2) | +0.00784 | 3 % | 1 |
| Reference repairs and lift-window retrains (12b, 13, 13b, 13e) | +0.00992 | 3 % | 4 |
| Failed pitcher swap and its revert (packs 5, 6) | +0.00335 | 1 % | 2 |
| Pitcher placement from depth (13p2) | +0.00146 | 0.5 % | 1 |

The lever rows add to +0.32083, not +0.31103, for two bookkeeping reasons: 12e was built on the CD-O variant 12d, whose -0.00733 is left out, and the two lift-window retrains are counted both in 13/13b and again in 13e (+0.00247). Remove both and the sum is exactly the +0.31103 from pack 1 to 14p. The pack 3 row is one upload that bundled five kinds of fixes; the logs do not split it.

CD-O moved in eight steps: 0.40513 (pack 1) -> 0.40188 (pack 3) -> 0.33234 (9a+) -> 0.30008 (12c) -> 0.29029 (12d) -> 0.26775 (12e) -> 0.26249 (13f) -> 0.25159 (13h) -> 0.24177 (13i) -> 0.23856 (13j). Three steps did most of the work: the kit-of-parts meshes in 9a+ (-0.070), the C0 blue cup (-0.032) and the Tier B selection (-0.023). Every CD-O prediction from the public scans landed within about 0.001 cm of the board (for example 13j predicted 0.2384, scored 0.23856).

Three readings of this table matter for the rest of the report:

1. **One big fix, then many small ones.** Pack 3 gave two thirds of all AUC points. It fixed gross failures (objects tracked onto the wrist, swapped identities, falling pitcher, learner failures). After it, the typical kept change was +0.001 to +0.005.
2. **Meshes were a pose lever, not only a CD-O lever.** The scorer registers our mesh to the hidden scan (section 3), so the 12e mesh change, with no pose row changed, gave +0.029 AUC and -0.75 cm RPE. The pose-CV meshes in 13p added +0.011. Mesh work produced more pose-board points after 31 Oct than all policy work.
3. **Policy swaps under the noise bound did not show.** The measured per-swap noise is about +/-0.008 AUC (section 10). 9b (proxy +0.0018) came out -0.0008. After that, a swap needed a proxy gain of at least +0.02.

### Gap to the leaders (6 Nov)

{{TABLE_GAP}}

Reading the margins (board values [M], read 6 Nov about 06:15 UTC; our bests are 14p for the five pose boards and 13j for CD-O):

| Board | Ours (rank) | 3rd place | Gap to 3rd | What closing it means |
|---|---|---|---|---|
| AUC | 0.88571 (9th) | 0.93486 | +0.04915 | about 2.3 times our largest single policy gain (pack 11, +0.020) |
| SP-SR | 0.90 (12th) | 1.00 | +0.10 | 2 more episodes within 10 cm and 0.5 rad; 1st to 3rd are all at 1.00 |
| MP-SR | 0.80 (10th) | 1.00 | +0.20 | 4 more episodes with every object under 3 cm and 30 degrees |
| RPE | 2.21325 cm (10th) | 1.05155 cm | -1.16 cm | cut our error by 52 % |
| MPPE | 1.79779 cm (10th) | 1.16684 cm | -0.63 cm | cut our error by 35 % |
| CD-O | 0.23856 cm (5th) | 0.23213 cm | -0.00643 cm | 2.7 % better meshes |

What the evidence says about reachability:

- **CD-O was the only board within reach.** Our last three CD-O rounds each gained 0.003 to 0.011 cm, at about $6 to $8 a round. One or two more rounds might have closed 0.006 cm [E]. On 3 Nov 13j would have been 3rd, but SRL improved to 0.20994 the same morning. By 6 Nov we had also dropped from 4th to 5th.
- **SP-SR and MP-SR need zero failed episodes.** The top teams have 1.00 on both. Our remaining failures sit in a few hard episodes (eval 10 cup nesting, eval 25 boards, eval 30 sweeper, eval 14 rack); section 7 shows that retrains with new meshes passed their gate 1 time in 7, and the fresh-draw spread on eval 1, 14 and 30 is 0.20 to 0.26 AUC per draw.
- **RPE and MPPE need about half our error.** The 2 Nov coordinator estimate [E] was: 6th about 30 %, 5th about 10 %, top 3 under 5 %, with $100 to $200 of compute. Our RPE/MPPE ratio was 1.35 against 0.88 to 1.03 for the top six (31 Oct), which points to a few large per-episode errors rather than a uniform offset [I].
- **The field kept moving.** Between 30 Oct and 6 Nov the 3rd-place AUC rose from 0.883 to 0.935. Our rank sum went 62 (31 Oct) -> 45 (7th, 3 Nov) -> 56 (8th among teams in all six top-20 lists, 6 Nov) without any new upload of ours after 3 Nov, because other teams kept improving.
