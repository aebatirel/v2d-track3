# C0 blue cup on top of pack 9a+: incremental AUC guard (31 Oct 2026, ~21:35 UTC)

**Why now.** The owner, relayed by keen-heisenberg at 21:22 UTC, gave the mesh lane a broad mandate: anything that
improves the score within the competition rules. The C0 blue cup (`meshes/library_c0/blue_cup.glb`, md5
9e3a74fd98921c4c589cee7956da457c, obs-lathe on public ep21) was held out of pack 9a because its selector was not
pre-registered (C0 PREREG section 5 deviation). It is the largest ready CD-O gain: public CD-O 0.523 -> 0.291 [D] on
5 of 36 eval pairs, board about 0.332 -> 0.300 [E].
It is the same provenance tier (P1) as the C0 pot, lid and rack already shipped under the owner's "Ship 9a, flagged".
The lathe_obs flag (developed in a scan-reading loop) applies, as it does to the shipped beige cup.

**Question.** Does adding it to the shipped 9a+ configuration pass C0's guard rule (mean dAUC >= -0.005, min >= -0.02,
mean dMPPE and dRPE <= +0.2 cm), measured against 9a+ rather than against library_v3?

**Runs [D]** (public twins only; `pipeline/score_registered.py`, kit unchanged; nothing on eval):
- ep11 (blue + beige): one NEW run, `joint_c0blue` = C1/T1 `single` dir (beige T1) with the C0 blue cup; C1/T1 tracks
  (sha256 29a449b9...). Command: `score_registered.py 11 <C1 tracks ep11> --meshes <scratch>/cdo_c1/t1/auc/joint_c0blue
  --t3 <C1 t3> --kit <kit> --out joint_c0blue_ep11.json`, 21:25:39-21:26:35 UTC, HEAD 0683232, this container.
  Compared with C1's `single_ep11` (= the 9a+ configuration on ep11).
- ep12, ep13 (blue + rack): stored C0 runs, `c0` (C0 rack + C0 blue) vs `single_plastic_dish_rack` (= 9a+ on these).
- ep21, ep22 (blue + pitcher): stored C0 runs, `single_blue_cup` vs `base` (9a+ = library on these).

| twin | objects | dAUC | dMPPE cm | dRPE cm | dMP-SR |
|---|---|---|---|---|---|
| 11 | blue, beige | +0.0071 | -0.192 | +0.154 | 0 |
| 12 | blue, rack | +0.0332 | -0.426 | -0.288 | 0 |
| 13 | blue, rack | **-0.0296** | +0.204 | +0.236 | 0 |
| 21 | blue, pitcher | +0.0502 | -0.364 | +0.747 | +1 |
| 22 | blue, pitcher | +0.0493 | -0.341 | +0.021 | 0 |
| **mean** | | **+0.0220** | **-0.224** | **+0.174** | +0.2 |

**Verdict under the rule: FAIL on one clause.** The min dAUC is -0.0296 on ep13 (limit -0.02). The mean dAUC, dMPPE
and dRPE clauses pass; dRPE is close to its limit, driven by ep21 (the spin noted in C0 AUC_RESULTS 3.3). The ep13
interaction (C0 rack + C0 blue cup) was already flagged in C0 (joint -0.0240).

**Orchestrator recommendation (to the pack lane, decision theirs/owner's):** include it, flagged. Expected board
effect [E]: CD-O about -0.032 (5/36 pairs x -0.232), AUC about +0.003, MPPE about -0.03 cm, RPE about +0.02 cm. The
risk is concentrated on rack + blue-cup episodes (one twin of five at -0.03 AUC).
