# SP-SR / MP-SR of pack 14p against OUR OWN references (3 Nov 2026, CPU, GT-free)

Coordinator's question: do the board's SR losses (SP-SR 0.90, MP-SR 0.80) sit in the stored rollouts? Method:
tools/sr_vs_ref.py, the kit's per-world logic (metric_code/track_3/MP-SR.py) with OUR packed reference as the target
(docs/research/work/pf-mesh-20261102/refs_14p.json; no registration / alignment needed: same frame, same frame 0), the
kit's symmetry-aware orientation (axes from our library meshes, kit eigen rule).

## Result [M]
- **14p submitted rows: all 20 episodes pass SP-SR and MP-SR vs our reference.** Largest SP margin 0.29 of a threshold
  (eval 25 orientation); largest per-object MP margin 0.62 (eval 10 beige_cup 1.85 cm), then eval 30 sweeper 0.61
  (1.82 cm, 11°), eval 14 cup 0.59, eval 28 pot 0.56. No episode within 20 % of a threshold. (sr_14p_rows.json)
- **Board policies' 10-draw rates** (confirmation / H5p7 / h5e1 draws of the 14p checkpoints; eval 10's H5p7 draws are of an
  older checkpoint, not scored): SP-SR 1.0 on all 19; MP-SR 0.9 on evals 1 (lid), 20 (pitcher), 28 (pot), 30 (sweeper):
  one bad draw each; 1.0 elsewhere. (sr_board_draws.json)
## Reading [I]
The rollouts track our references well inside both SR thresholds, so the board's 2 SP-SR and 4 MP-SR failures (vs ground
truth) come from our references vs the truth (perception), at levels below what a gross-failure audit flags (MP-SR fails
at 3 cm / 30° per object). A policy fix cannot buy an SR episode on the stored rows; only reference (perception) accuracy can.
