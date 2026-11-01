# Overnight 31 Oct → 1 Nov 2026: results in one place

Compiled by keen-heisenberg at 08:55 UTC 1 Nov from the lanes' records:
- focused-pascal: `claude/focused-pascal-2nz9s1`;
- bold-albattani: `claude/bold-albattani-6qmxsv`;
- determined-wright: `claude/determined-wright-3joens`;
- score-status: `claude/standings-20261031`.

Evidence labels: [M] measured, [E] estimate, [D] measured on public data (development), [H] hypothesis.
"Proxy" is sim_vs_ref against our own reference (ground-truth-free), over 10 official evaluator draws unless stated.

## Kaggle uploads

| Pack | When (UTC) | AUC | SP-SR | MP-SR | RPE cm | MPPE cm | CD-O cm |
|---|---|---|---|---|---|---|---|
| 9a+ (previous best, 31 Oct) | 18:18 | 0.81757 | **0.85** | 0.65 | 3.87853 | 2.89663 | 0.33234 |
| 9b = 9a+ + eval 33 (D arm) | 05:02 | 0.81677 | 0.85 | 0.65 | 3.88283 | 2.90186 | 0.33234 |
| **10 = 9a+ + eval 10 (ev10cs5)** | 08:43 | **0.81915** | 0.80 | 0.65 | **3.68275** | **2.84759** | 0.33234 |

- Each board counts our best submission (or the selected Final Submission). Now pack 10 counts for AUC, RPE and
  MPPE, and 9a+ for SP-SR.
- Ranks at 08:50: AUC 8, SP-SR 10, MP-SR 8, RPE 10, MPPE 11, CD-O 14. Rank sum 61, **11th**; DSAIL is 10th on 59.
- Receipts and records:
  - `results/submissions/20261101-track3j-candidate/build_9b/UPLOAD.md` (this branch);
  - `results/submissions/20261101-track3k-candidate/build_10/UPLOAD.md` (this branch).

## Experiments, in order of value

| # | Item | Result | Verdict | Cost |
|---|---|---|---|---|
| 1 | Eval 10 at njmax 1024 (diagnostic) | [M] proxy 0.913 vs 0.459. 0.903 when evaluated at the stock 512 limits; training overflow 0 vs ~6 M lines | SUPPORTED: training-time contact overflow caused eval 10's floor. Never packed; the organisers' OK is needed | $2.06 |
| 2 | Eval 10 on cavity-safe pieces ev10cs5, stock limits | [M] proxy 0.532 vs 0.463 (+0.069) | PASS, in pack 10 (+0.0016 AUC on the board) | $2.85 |
| 3 | D arm (start-state randomisation), evals 14 / 16 / 25 / 30 / 33 | [M] new vs packed: 14 0.686 / 0.727; 16 0.831 / 0.850; 25 0.858 / 0.878; 30 0.816 / 0.897; 33 0.936 / 0.923 | Only 33 passes; in 9b, which scored −0.0008 AUC (within noise) | $19.41 |
| 4 | Eval-10 V4p retrain (e10v) | [M] 0.459 vs 0.463 | NO-SWAP | $3.25 |
| 5 | Masses v1 (check) / v2 | [M] v1: ep2 +0.157, ep12 −0.013. v2: mean +0.0034 | NOT ADOPTED | ~$12 |
| 6 | Arm V (actor sees object velocity) | [M] mean −0.024 | inconclusive, not used | $7.02 |
| 7 | Arm S (solver re-test), recipe screen K / D | [M] no signal / inconclusive | not used | – |
| 8 | Command smoothing (test A) | [M] fail | not used | – |
| 9 | Zero-lag RTS smoother on tracks | [D] kit gate −0.00011 | FAIL | $0 |
| 10 | Re-track | [M] fail | not used | $1.54 |
| 11 | Eval-25 board slot pieces | [M] fails its contact clause | NO | $0 |
| 12 | Collision carve round 2 (evals 10 / 14 / 30) | [M] ev10cs v1–v3 overflow; rack sets add overflow | only ev10cs4 / 5 usable | $0 |
| 13 | Public pose fix (rest projection) | [D] ΔAUC −0.0107, 17 / 20 worse; pushes point toward the truth on only 22 / 50 segments | FALSIFIED. Rest overlaps are largely mesh shape | $0 |
| 14 | Pot / pitcher re-base; eval-20 b1 retrain | [M] sim pot already rests correctly; eval-20 pitcher falls at f0 (195 mm) and the b1 clip fixes it (8.5 mm); retrain gate missed by 0.0004 (0.8929 vs > 0.8933) | NO-SWAP, no pack 10b | ~$3.5 |
| 15 | f0 settle survey, rest probe, ep2 draw divergence, overflow counts | [M] diagnostics: eval 19 sweeper falls at f0; hands push objects on evals 5 / 8 / 33; ep2 lid fails first (lid inside the pot's hulls) | report-only | $0 |
| 16 | H5p7 / H5e1 fresh-draw sets (for the swap rule) | [M] packed baselines | used by 3 | $12.80 |

## Spend
- [M] Credit $56.52 at 22:58 UTC, $23.67 at 08:54 UTC: $32.85 spent since 22:58.
- Earlier evening runs, from the logged actuals before 22:58: e10v $3.25, h5p7 $5.85, h5e1 $6.95, mv2a2 $6.20,
  rtkA/B $1.54. The night in total is about $56 [E].
- 09:00 UTC: nothing running, ledger closed, credit $23.63 [M]. focused-pascal's cumulative project ledger: $200.12.

## Lessons
- A swap whose expected gain is below the noise of our own proxy is a coin flip on the board (9b). From pack 10 on,
  a swap needs a proxy gain of at least +0.02 on its episode.
- The biggest wins came from finding the failing moment and its physical cause (contact overflow on eval 10), not from
  robot-side or learner tweaks. Every robot-side tweak tested tonight was negative or inconclusive.
</content>
</invoke>
<invoke name="Bash">
<parameter name="command">cd /home/user/v2d-track3 && git add docs/analysis/overnight-20261101/README.md && git commit -qm "Overnight 31 Oct-1 Nov results in one place (uploads, experiments, spend)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01D9UJC7JP3bbasvhFUrxyf7" && git push -q -u origin claude/keen-heisenberg-engcwz && git log --oneline -1
## Where things stand (09:00 UTC, all four lanes reported; nothing running; every branch pushed)

### Decisions for the owner
1. **Organisers question on njmax 1024 training.** The policy evaluated at stock 512 limits scores 0.903 on eval 10,
   against 0.532 in pack 10. [E] about +0.015 AUC, and it likely wins back the SP-SR episode. $0 if allowed. A
   paste-ready question is in the work log (07:27 entry).
2. **CD-O-only variant: 9a+ (or pack 10) plus the C0 blue cup.**
   - [D] Public CD-O for the blue cup goes 0.523 → 0.291. [E] The board goes 0.332 → ~0.300, ~14th → ~11th, about +3
     ranks. $0, no retrain, and it can't hurt the other boards (best per board).
   - Compliance point: the mesh was chosen against public scans with a selector written after scoring. That is a
     GT-informed public selection, not eval tuning.
3. **Credit top-up.** $23.63 now. Each retrain costs ~$3–6 [E] plus ~$2 for confirmation.
4. **Near the close:** choose a Final Submission per board, then run the PR #215 container on every counted file.
   Keep every receipt and checkpoint.
5. **Mesh-lane calls:** E0b compliance; the $1 grey-template re-track.

### Half-done (what would finish each)
- **Eval-10 nest completion, legal route.** 660–992 overflow lines remain at 512, and the beige base wobbles
  6.5 mm / 4° at f0. [H] Clipping the beige low corner fixes both. CPU build + budget.py, then ~$3 per retrain.
- **Eval-19 sweeper support_fill.** Certified on CPU (4fa6ec4). Needs budget.py, then a retrain gated at ≥ +0.02 over
  the packed 0.921, so little headroom.
- **store.sh interim/final push race.** The fix (flock or a staging folder) is described in focused-pascal's work log
  at 00:50; not built.
- **main is stale since 30 Oct.** Merge the session branches.

### Room for improvement, by expected rank gain per cost
| Item | Expected gain | Cost | Evidence |
|---|---|---|---|
| CD-O blue-cup variant | about +3 CD-O ranks, enough alone to pass DSAIL (rank sum 61 → ~58) | $0 | [D] / [E]; owner's compliance call |
| Eval-10 nest completion (route A organisers / route B clip + retrain) | +0.015 AUC; SP-SR / MP-SR +1 episode each (+1 to +3 ranks) | $0 / ~$3 a try | [M] diagnostic 0.913 vs 0.532 |
| Eval 14 (packed 0.727, 4 / 10 fails, largest spread) | +0.005–0.01 AUC | ~$3–4 | [E]. Needs its own public test of a pose rule; the general rest projection is falsified |
| Evals 1 / 30 overlaps; eval 19 / 20 starts | small (already 0.89–0.92) | ~$3 each | [H] |

Skip: robot-side tweaks (all negative tonight), the public ep2 / ep12 njmax-1024 test, solver v2, synergy B.
