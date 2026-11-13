# Dated correction to this folder's README (1 Nov 2026, 03:10 UTC, collision-carve round-2 Eval-carves step)

These fix statements in `README.md` (written 1 Nov 01:46 UTC). The README is left as written; read it together with
this file. Source: verify_cc2_0 B1 / N3 and verify_cc2_1 B2 / N8 / N9 (`build/I/verify_cc2_0.md`, `verify_cc2_1.md`).
[M] unless marked.

1. **Hands-off set (verify_cc2_1 B2).** The summary table and section 4 count H0 frames (no contact label). The rule's
   hands-off set is H30: no robot hand point within 30 mm (F-I5.3 (b), F-I5.16 (3)(a)). Many H0 frames have a hand
   0.4-3 mm from the object.
   - H30 tables, recomputed from this folder's per-frame records with its own `scripts/summarize.py`, are in
     `../collcarve2-eval/precheck_H30_tables.md` and `precheck_H30.json`. **Use those for any relay to the pose lanes.**
   - H30 failing / H30 frames (H0 in brackets):
     | eval | H30 failing / H30 frames | (H0) |
     |---|---|---|
     | 10 | 25 / 33 | (37 / 52) |
     | 1 | 50 / 50 | (56 / 56) |
     | 14 | 18 / 29 | (47 / 63) |
     | 15 | 12 / 54 | (24 / 92) |
     | 16 | 14 / 60 | (19 / 86) |
     | 30 | 22 / 22 | (59 / 63) |
     | 32 | 0 / 3 | (6 / 21) |
     | 33 | 0 / 14 | (4 / 30) |
   - No H30 frame fails the table check (a). The largest penetration is 3.94 mm (rack, eval 14 f157).
   - The 16.6 mm (eval 14 f42) and 19.5 mm (eval 32 f33) penetrations are at frames with a hand 3 mm or less away.
2. **"The c1 validity check ... has not run, because the ep24 v6 bundle is not on this machine"** (section 5) **is
   false.** Both ep24 bundles are on this machine, and c1 needs none.
   - c1 has now run, and it fails: `../collcarve-r2/t_i17_c1/README.md`. Plain MuJoCo flags the default ep24 pieces as
     overflowing (16 / 16, 688 rows), where MuJoCo-Warp shows none (416-425 rows).
   - So the contact numbers here are **plain MuJoCo only**, eval 10's 656-1,296 rows included. Eval 10's overflow
     itself rests on determined-wright's and focused-pascal's FlashCHORD measurements (work log, 1 Nov 02:50 UTC [R]).
3. **Eval 10 at rest (verify_cc2_1 N8).** f142 is the only H30 contact frame. There the copies reach 516-656 rows
   (median 536), and exactly 512 with no jitter. The 1,252 / 1,296 maxima come from f111 / f116, which are in hand,
   with the holding hand absent from the scene. So "656-1,296 at the nested rest" mixes in-hand frames into the rest
   numbers.
4. **Not stable (verify_cc2_1 N9).** On evals 14 and 30 the pair scene does not overflow, but the packed guest is
   thrown 132-140 mm (eval 14 cup, median) and 23-62 mm (eval 30 sweeper, median) within 2 s.
5. **Status of this check (verify_cc2_0 N3).** This precheck ran before the public verification and without a dated
   go. It uses the packed references' poses and faithful boxes of the pack's visual meshes, not our tracks and SHELLs.
   It is a consistency check of the pack's references and colliders, not the F-I5.15 (3) precheck of our eval twins.
   GT-freeness rests on code reading: the scripts ran outside the gmg guard (verify_cc2_0 N10).
