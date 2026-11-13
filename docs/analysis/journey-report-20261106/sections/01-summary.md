## 1. Summary

This report covers our NVIDIA V2D Challenge Track 3 entry (team Imitation.Tech, 20 Oct - 6 Nov 2026), from the October side research to the leaderboard reading on 6 Nov. Evidence labels: [M] measured, [D] measured on public data against mocap, [E] estimate, [H] hypothesis, [I] inference.

### Where we ended

| Board | Best score [M] | From pack | Rank 3 Nov | Rank 6 Nov | 3rd place 6 Nov |
|---|---|---|---|---|---|
| AUC | 0.88571 | 14p | 7 | 9 | 0.93486 |
| SP-SR | 0.90 | 12e and later | 11 | 12 | 1.00 |
| MP-SR | 0.80 | 12e and later | 7 | 10 | 1.00 |
| RPE | 2.21325 cm | 14p | 8 | 10 | 1.05155 cm |
| MPPE | 1.79779 cm | 14p | 8 | 10 | 1.16684 cm |
| CD-O | 0.23856 cm | 13j | 4 | 5 | 0.23213 cm |

The final rank is the sum of the six board ranks. Ours was 45 (7th) on 3 Nov and 56 (8th among teams in all six top-20 lists) on 6 Nov, without any new upload of ours, because other teams kept improving. The leaders on 6 Nov: richchentw 7, DDD 15, rlwrld 23, Zihao Guo 24, SRL 37.

### The score journey in a few lines

AUC 0.575 on the first upload (24 Oct, 9th) -> 0.789 the next day (25 Oct, 4th on AUC) -> 0.811-0.815 for a week of small swaps (26-30 Oct) while the field passed us -> 0.839 after the eval-10 contact fix (1 Nov) -> 0.869 when we learned that our mesh is registered to the hidden scan and changed the meshes (2 Nov) -> 0.886 the same night. CD-O went 0.405 -> 0.239 cm in eight mesh steps after 31 Oct, when we found it was anchoring our rank sum. In total: 26 uploads, AUC +0.311, RPE -10.37 cm, MPPE -6.86 cm, CD-O -0.167 cm, SP-SR and MP-SR +0.45 each.

### Levers ranked by measured board gain (AUC)

| Rank | Lever | AUC gain [M] |
|---|---|---|
| 1 | Reference rebuild, second learner and identity fixes (pack 3) | +0.206 |
| 2 | Submitted-mesh changes on the pose boards (Tier B +0.029, pose-CV meshes +0.011, others) | +0.046 |
| 3 | Policy retrains and training fixes (eval 10 trained at njmax 1024: +0.020) | +0.024 |
| 4 | Carving the simulator collision copies (pack 4) | +0.022 |
| 5 | Reference repairs and lift-window retrains | +0.010 |
| 6 | Detection fix + seed picks (pack 2) | +0.008 |

Mesh-only CD-O work gave the cheapest rank points: CD-O rank 18th -> 4th for about $22 of GPU mesh generation (G2, G3 and rack round R; the earlier mesh steps ran on CPU).

### Biggest failures and their margins

- **First projection:** 0.68 expected, 0.575 scored (-0.105). Eval perception lost about 19 % against 3-4 % on public twins.
- **Lathe pitcher swap:** +0.098 on its one public twin, -0.0045 on the board.
- **Pack 9b:** proxy +0.0018, board -0.0008; the per-swap board noise is about +/-0.008.
- **Board-2 flip revert (13f1):** expected +0.02, got -0.0003.
- **About 20 GT-free perception ideas** (30 Oct - 3 Nov) all failed their gates; the closest missed by 0.00002 (physics priors) and the room map by 0.007.
- **Retrains with the new meshes:** 1 of 7 passed. Eval 20 fell to 0.451 zero-shot against 0.926.
- **Top 3** was not reached. On 6 Nov we needed +0.049 AUC, two more SP-SR episodes, four more MP-SR episodes, and RPE 52 % lower. On CD-O, 13j beat the earlier 3rd place by 0.00044 cm, but SRL improved to 0.20994 the same morning.

### The 10 most important lessons

1. **Read the scorer's code first.** The kit registers the submitted mesh to the hidden scan and aligns the whole scene once at frame 0. We learned this fully only on 2 Nov; after that, mesh-only changes gave +0.04 AUC with no retraining.
2. **Read the ranking rule first.** The final rank is the sum of six board ranks, not AUC alone. We found this on 31 Oct, with CD-O at 18th of 20.
3. **Gross failures first.** Objects tracked onto the wrist, swapped look-alike boards, a falling pitcher and failed learners cost far more than cm-level precision. One pack that fixed them gave two thirds of all our points.
4. **The remaining error was bias, not noise.** Constant offsets, frame-0 tilt, the pitcher's missing base and a half-frame delay. Smoothing, filtering and "second sensors" cannot remove bias, and every one we tried failed.
5. **Our GT-free proxy (sim_vs_ref) ranks policies well but cannot see a wrong reference.** By 3 Nov all 20 rollouts passed the success thresholds against our own references, so the board's remaining failures were reference-vs-truth errors.
6. **Noise decides small swaps.** Single draws spread by sd 0.07-0.26; packed draws were lucky (z about 3.2); box draws overstated fresh draws by 0.10-0.17. Pre-registration, the +0.02 swap bar and two-host confirmation protected us.
7. **Look for silent physics failures.** The eval-10 floor was a contact-buffer overflow in training (about 6-8 million warnings), not a policy problem. One setting fixed it: +0.020 AUC.
8. **Policies are tied to the shapes they were trained on.** A better collision mesh broke grasps that the policy had built on the old shape.
9. **Single-twin or single-seed wins do not transfer.** Use leave-one-episode-out public CV with several seeds, and exclude generation-source episodes.
10. **The field moves late and fast.** Our AUC rank fell from 4th to 8th in six days without our score getting worse. Small insurance swaps (+0.001) could not keep pace.
