# pf-hands results (batch 1 + pfE), [M] unless labelled

## pfA: public ep13 (eval 14's twin), registered AUC vs mocap, chosen checkpoint, NREP 10
| arm | seed 42 | seed 43 |
|---|---|---|
| s (single-hand, packed construction; right hand from f46) | 0.378 ± 0.110 | 0.554 ± 0.006 |
| 2h (two-hand) | **0.587** ± 0.156 | 0.553 ± 0.006 |
| f (first picker, pfE, other box) | 0.555 ± 0.131 | pending |
Static floor ≈ 0.542 (orcB). Paired Δ(2h − s): +0.209 / −0.001, mean **+0.104** → **PASS by the §3 rule**.
Honest reading [I]: the pass comes from one seed where the single-hand policy fell below the floor; on seed 43 both arms
sit at the floor (the cup is not carried). Not a robust "two-hand is followable" result.

## pfB: evals 14 and 16, two-hand on P (training box, sim_vs_ref vs P)
| eval | seed 42 | seed 43 | packed H5p7 | verdict |
|---|---|---|---|---|
| 14 | 0.603 ± 0.110 | 0.581 ± 0.108 | 0.727 | NO-SWAP (gate) |
| 16 | 0.713 ± 0.039 | 0.696 ± 0.062 | 0.850 | NO-SWAP (gate) |
Two-hand references are worse than the packed single-hand ones on both eval episodes. Cost: pfA $3.7 (≈ 2.6 h), pfB
$3.9 (159 min at $1.49/h) [E from run times].
