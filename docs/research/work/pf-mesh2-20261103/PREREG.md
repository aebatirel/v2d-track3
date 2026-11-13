# Tier B collision retrains, batch 2 — PRE-REGISTRATION (3 Nov 2026 ~01:49 UTC, before any box)

Coordinator (keen-heisenberg, 01:47 UTC; owner: maximum work tonight): one more batch ≤ $35, stop if credit < $15;
the eval-14 p0m recipe (+0.058, held on fresh draws) on other low episodes whose collision meshes changed; zero-shot
overflow check; **two-host confirmation** (docs/research/work/pack9b-20261031/PREREG.md amendment); pack 15 on 14p
(b6c6100d…).

GROUND-TRUTH FLAG as in docs/research/work/pf-mesh-20261102/PREREG.md: the collision shapes are GT-selected (owner-approved
tier); these rollouts depend on them.

## Episodes and arms (ops/jobs/pf_arms.sh at the launch commit; seeds 42 / 43)
| eval | arm | collision change | board policy (control draws / old row; 14p rows checked equal [M]) |
|---|---|---|---|
| 32 | p0m | blue_cup := meshes/tierB_collision/blue_cup.glb (13f Tier B+ cup, 20k faces; the cup that passed eval 14) | pfD s43 9a2c2f7c… (pfD conf draws / pfD conf r1); table pf-lift-20261102/packed_refs_12b.json |
| 33 | p0m | the same cup (no Tier B / 13h spoon mesh exists: spoon unchanged) | rcB df90b216… (H5p7 / c33B submission draw); packed_refs.json |
| 19 | sm | mini_sweeper := Tier B sweeper (std recipe, packed base byte copy) | fdc4c491… (H5p7 / pack 6 draw); packed_refs.json |
Not run: eval 10 (its cups collide through carved convex pieces meshes/carve/ev10 in the shared /content/assets, so a
mesh-file swap would not change its collision); eval 20 (grasp mismatch with the new pitcher, tonight).

## Procedure
1. Training box T (per episode): zero-shot (board policy on the new collision; refuse on any overflow line), 2 seeds, seed
   choice, training-box gate (> control mean), 10 fresh official draws on T, tools/pf_verdict.py eval → V_T.
2. Second host H (a different Vast machine, launched after T pushed its choice): `CONF_FROM=<T's run>`: the same inputs and
   collision swap rebuilt, T's chosen checkpoint (sha256-checked against T's choice), 10 fresh official draws on H, same
   scoring → V_H.
3. tools/pf_twohost.py: SWAP iff V_T and V_H are both PASS (a / b / c / s) and both clear +0.02; the packed rollout is T's
   draw 1. Passing episodes → pack 15 on 14p. No host dropped or re-run after the fact.
Cost [E]: T boxes 32 / 33 ≈ 2.5 h ≈ $3.5 each, 19 ≈ 4.5 h ≈ $7; H boxes ≈ 0.6 h ≈ $1 each → ≈ $17.
