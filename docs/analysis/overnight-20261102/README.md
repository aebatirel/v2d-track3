# Night of 2–3 Nov 2026: morning report (written 03:20 UTC, 3 Nov)

**Result.** Every board improved, and the rank sum went from 58 (10th, yesterday morning) to **46 (7th)**. Most of the
gain came from meshes: better submitted meshes, chosen by pre-registered public evidence. GT-informed selections were
owner-approved and are disclosed in each pack README.

## Board bests now [M]
| Board | Yesterday 08:45 (12c) | Now | Pack | Rank now |
|---|---|---|---|---|
| AUC | 0.84738 | **0.88571** | 14p | 7 |
| SP-SR | 0.85 | **0.90** | 12e and later | 11 |
| MP-SR | 0.75 | **0.80** | 12e and later | 7 |
| RPE (cm) | 3.008 | **2.213** | 14p | 8 |
| MPPE (cm) | 2.467 | **1.798** | 14p | 8 |
| CD-O (cm) | 0.300 | **0.2516** | 13h | 5 |

Standings (API, 03:17 UTC):
- richchentw 6; DDD 10; rlwrld 19; Zihao Guo 20; SRL 26; Purple 32;
- **Imitation.Tech 46**;
- sam&alex 50; SoySauceChicken 53.

## Uploads after the owner went to sleep (all verified against their base before upload)
| Pack | What changed | AUC | RPE | MPPE | CD-O |
|---|---|---|---|---|---|
| 13f1 | Eval 25 board 2 back to the library mesh (D1 no-flip safety gate) | 0.87191 | 2.37520 | 1.92513 | 0.26393 |
| 13p | Pose-board meshes by public-pose CV: TSDF pot, library_c0 rack | 0.88257 | 2.22667 | 1.82356 | 0.26869 |
| 13p2 | + eval 20 pitcher placed from its own stereo depth (GT-free) | 0.88403 | 2.22531 | 1.80932 | 0.26869 |
| 14p | + eval 14 retrain with better collision meshes (two-host era rule: fresh 0.933 vs 0.875) | **0.88571** | **2.21325** | **1.79779** | 0.26869 |
| 13h | CD-O variant: G2 generated pot, blue cup and rack (best-of-N by scan, disclosed) | 0.88001 | 2.28085 | 1.85258 | **0.25159** |

Earlier in the evening, before sleep: 13, 13b, 12e (Tier B meshes: the big jump), 13e, 13f.

## What passed, what failed
**Passed and on the board:**
- per-object pose-mesh choice by pre-registered leave-one-episode-out CV on public mocap: pot +0.021, rack +0.023,
  board AUC +0.010;
- eval 20 pitcher placement from depth (+0.0015 board);
- eval 14 retrain with Tier B collision meshes;
- G2 meshes for CD-O (5th place).

**Failed or not adopted (all pre-registered):**
- mesh placement from depth for all objects (+0.0026, failed its bar);
- tracking with the new meshes as templates (−0.043);
- room-map cameras (our camera drift is only 2–9 mm);
- round-2 pose CV: only a pitcher mesh passed, and it duplicates the placement fix, so it was not adopted;
- C4 audit (no existing mesh beats the shipped ones);
- retrains of evals 20, 28 and 30: no swap. Eval 30 looked good on the training box but failed on fresh draws on one
  host;
- rack trim (below the rule margin);
- spoon-anchor re-evaluation: not run, because its expected value is about 0 and uploading it would probe the board.

**Learned:**
- **The registered scorer makes mesh shape and placement drive every pose board.** Choose pose meshes by public pose
  evidence, not by scan CD-O.
- Fresh-draw failures can be host-specific (the evaluator-gap test did not reproduce the gap). New rule: confirm on
  two hosts, both must pass.
- The Tier B board-2 plate flips under a raw-scan reference. A no-flip gate (D1) now vetoes such meshes.

## Still running (≈ 03:20 UTC)
- Retrains of evals 32 / 33 (blue cup) and 19 (sweeper) with two-host confirmation (perfect-following).
  Results ≈ 04:30–06:30 UTC → pack 15 on 14p.
- G3 mesh generation for sweeper / dust pan / lid / beige cup, plus more rack / pot crops (bold-albattani, cap $15)
  → CD-O pack 13i on 13h. Target: 4th on CD-O (−0.0049).

## Spend
- Credit $127.97 at 20:12 → $82.96 at 03:16: **≈ $45 overnight**, including boxes still running.
- About $6 was lost to job bugs and replaced boxes, plus about $2.80 to a preempted mesh box.

## Final-selection plan (unchanged unless new packs beat them)
- AUC / SP-SR / MP-SR / RPE / MPPE → **14p**;
- CD-O → **13h**.

## Next options for the owner
1. Wait for pack 15 and 13i this morning ($0 more beyond the running boxes).
2. More pose-CV candidates or placement for objects not yet covered: CPU, cheap.
3. The spoon (10 / 20 episodes, no public scan): only GT-free ideas; risky.
4. Larger: retrains of the remaining low episodes with two-host confirmation, ≈ $6–8 each.
