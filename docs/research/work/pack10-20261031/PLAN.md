# Pack 10: cell list and cost (draft, 31 Oct 2026 ~18:40 UTC; nothing launched)

Owner (~18:30 UTC, via the score-status session): improve the weak episodes with the new methods and collision carves
("blue cup and spoon ... the spoon doesnt enter the cup proper and for some rack things"), aiming at ~0.9. Schedule: one
combined retrain starting ~1 Nov 18:00 UTC, pack ~2 Nov evening, 3–4 Nov kept for a fallback. One owner go for the total.

## Inputs and their status (each enters only through its own pre-registered verdict)
| Input | Source | Verdict / ETA | Enters as |
|---|---|---|---|
| Eval-10 V4p reference | ep11 gate (this session) | ~19:30–21:00 UTC tonight | eval 10's reference (ev10_v4p.sh) |
| Collision carves (GT-free) | bold-albattani | asked for by 1 Nov 12:00 | `PIECES` per episode (sim assets only) |
| – carved blue cup (spoon entry) | | | evals 32, 33 |
| – rack seats | | | evals 14, 16 (grasp-lock), 30 (standard) |
| – board slot | | | eval 25 (standard; replaces meshes/carve/ev25) |
| Physics solver (arm S) | determined-wright | ~23:00 tonight; if it signals, solved eval refs for the 15 grasp-lock evals by 1 Nov 14:00 | reference per grasp-lock episode |
| Realistic masses (Masses v2) | this session | ~23:00–01:00 | `MA_ARGS --physics` / `mass_arm.py` (all episodes) |
| Recipe change (K or D) | determined-wright's screen | ~22:30 tonight | grasp-lock episodes only |

Learners (packed_refs.json): grasp-lock 3, 5, 6, 8, 10, 14, 15, 16, 20, 32, 33, 35–38; standard 1, 19, 25, 28, 30.

## Cells (2 seeds each; the per-episode swap rule decides; the packed policy stays unless every clause passes)
**Tier 1 — the owner's weak episodes (always run, whatever the global verdicts):**
| Eval | Learner | Change | Cells |
|---|---|---|---|
| 10 | grasp-lock | V4p reference (if the gate passes; tonight's retrain, then folded in) | 2 |
| 32, 33 | grasp-lock | carved blue cup (spoon entry) | 2 × 2 |
| 14, 16 | grasp-lock | rack seats | 2 × 2 |
| 30 | standard | rack seat | 2 |
| 25 | standard | new board slot | 2 |
→ 8 grasp-lock + 4 standard cells (+ eval 10's 2 tonight).

**Tier 2 — everything else, only for global changes that pass** (masses ADOPT, solver signal, recipe winner): the
remaining grasp-lock evals 3, 5, 6, 8, 15, 20, 35–38 and standard evals 1, 19, 28. Tier-1 episodes also take these
changes. Where a recipe change applies (grasp-lock only), a combined-minus-recipe control arm runs beside it.

## Cost [E] (measured: grasp-lock ~$1.0–1.5 per cell with 4 cells per GPU; standard ~$2.4–3.4 per cell; 10-draw
confirmation ~$1–2 per box of candidates)
| Scenario | Cells | Cost |
|---|---|---|
| Tier 1 only (no global change passes) | 8 GL + 4 STD + confirmation | ≈ $20–33 |
| Tier 1 + Tier 2, one arm (masses and/or solver pass, no recipe) | ~30 GL + 10 STD | ≈ $55–90 |
| Tier 1 + Tier 2 with a recipe winner (+ minus-recipe control on grasp-lock) | ~60 GL + 10 STD | ≈ $95–130 |
Wall clock: ~8–13 h on 5–13 RTX PRO 6000s in two staggered waves (store 429 limits; Vast availability).

## Swap rule (pre-registration to be committed before any pack-10 result; agreed with the score-status session)
Per episode, over ≥ 10 fresh official draws, GT-free: (a) mean sim_vs_ref ≥ the packed policy's fresh-draw mean (runs
20261031-h5p7-1a7cdff / -h5e1-1a7cdff); (b) failure rate (GT-free RPE vs our reference > 5 cm, audit.py) ≤ the packed
policy's; (c) median GT-free RPE not worse; secondary: new packed draw (draw 1 by position) ≥ old packed draw − 0.05.
Where the reference changed (eval 10; solver-solved references), (a)–(c) hold against BOTH references. New collision
carves change only the simulator assets (the reference is unchanged), so one reference suffices there.

## Update (31 Oct ~20:35 UTC)
- Owner chose "No D" (in determined-wright's session): no recipe change in pack 10 (K inconclusive, D not used).
- Physics solver re-test: no signal → no eval solving; solved references are not for eval.
- So Tier 2 depends on Masses v2 (verdict ~23:00–01:00) and, for references, on the re-track test (if it passes:
  every eval reference is rebuilt and scored against both references). Recipe-control arms are dropped, so the cost
  line "with a recipe winner" no longer applies: Tier 1 ≈ $20–33; Tier 1 + Tier 2 one arm ≈ $55–90 [E].
