# Collision carve round 2, eval carves: none run, because no eval pair qualifies (1 Nov 2026, 03:12 UTC)

This is the collision-carve round-2 Eval-carves step (rules PREREG F-I5.15 / F-I5.16 as built in F-I5.17). [M] marks a
measurement, [R] a reported value, [H] a hypothesis. CPU only, on this container. No rental, $0. No ground truth was
read.

## In plain words

- **No eval carve was run, and nothing was delivered.** The step may run an eval pair only if all three conditions
  hold, and none holds:
  - (i) the round-2 rule delivered at least one public pair;
  - (ii) no blocking verifier finding stands;
  - (iii) the eval precheck puts the pair in carve scope, meaning the packed collider blocks a pose that is otherwise
    feasible.
- **(i) fails** [M, T-I16]. All five public folders are do-not-use, and no public pair was carved. Every object fell
  to 6 mm boxes that keep 2-9 % of its shape. Every hands-off test frame is a physically impossible pose.
- **(ii) fails.** One blocking finding needs a new rule: no ring that stays out of the cavity keeps a 1.5 mm wall on
  our rough SHELLs (verify_cc2_1 B1). A second block arose in this step: the contact-gate check c1 fails, so no F-I5
  delivery can be called usable until the contact gate has run in the evaluator's engine.
- **(iii) fails for every eval pair** [M]. Use the rule's hands-off frames (no hand within 30 mm). Of those, take the
  ones that pass the pose check. In none of them do the packed colliders overlap by 1 cm3 or more.
  - Where they do overlap, the packed visual meshes overlap too, at the reference pose.
  - So the problem there is the pose, not the collider, and a carve is not the remedy.
- Fixed in this step: the two blocking findings that needed no new decision.
  - c1 was skipped because of a false premise. It has now run, and it fails.
  - The eval precheck tables now use the rule's hands-off set.
  - Dated corrections were written for the false statements.

## 1. The three conditions, per eval pair, in the owner's priority order

H30 = no robot hand point within 30 mm of either object (F-I5.3 (b), F-I5.16 (3)(a)). "Feasible" = the frame passes
the precheck: (a) at most 4 mm into the table, (b) supported within 4 mm, (c) faithful overlap under 1 cm3. "Blocked"
= packed-vs-packed overlap >= 1 cm3, or the guest mesh inside the receiver's packed pieces but outside its mesh by
>= 1 cm3. All numbers come from the eval precheck's per-frame records (`../collcarve2-evalcheck/per_frame/`), counted
by `scripts/scope_h30.py`, output `scope_H30.json`.

| Eval | Receiver <- guest | (i) public delivery | (ii) no blocking finding | H30 frames | feasible | feasible and blocked | (iii) | Run? |
|---|---|---|---|---|---|---|---|---|
| 32 | blue cup <- spoon | no | no | 3 | 3 | 0 (max packed overlap 0.0 cm3) | no | **no** |
| 33 | blue cup <- spoon | no | no | 14 | 14 | 0 (0.0) | no | **no** |
| 14 | rack <- blue cup | no | no | 29 | 11 | 0 (0.0) | no | **no** |
| 16 | rack <- spoon | no | no | 60 | 46 | 0 (0.71) | no | **no** |
| 30 | rack <- sweeper | no | no | 22 | 0 | 0 | no | **no** |
| 15 | rack <- spoon | no | no | 54 | 42 | 0 (0.73) | no | **no** |
| 10 | blue cup <- beige cup | no | no | 33 | 8 | 0 (0.0) | no | **no** |
| 1 | pot <- lid | no | no | 50 | 0 | 0 | no | **no** |

- On evals 32 and 33 the spoon is inside the cup only while a hand holds it. On the H30 frames neither the meshes nor
  the packed pieces touch.
- On evals 14, 30, 10 and 1 every H30 frame where the packed colliders overlap also has the faithful meshes
  overlapping by >= 1 cm3. Those frames are pose_impossible: they go to the pose lanes, not to a carve.
  - Eval 30: 22 of 22 H30 frames.
  - Eval 1: 50 of 50, although the packed `ev01` pieces do not overlap.
  - Eval 10: 25 of 33. At its 8 feasible frames the packed `ev10` pieces do not overlap.
- Counted over all frames, hands included (report only, not the rule), there are a few feasible-and-blocked frames:
  eval 32 6, eval 33 3, eval 14 4, eval 30 9, eval 1 1. Every one of them carries a hand-contact label (in hand).
- Caveat on (iii) (verify_cc2_0 N3). The precheck's "faithful" colliders are 2 mm boxes of the pack's visual meshes,
  placed at the packed references' poses. They are not our SHELLs on our eval tracks. A precheck on our own eval twins
  (bundles from `tools/ev_extract.py`) was not built, because (i) and (ii) already rule out a run.

## 2. Blocking findings: what was fixed here, and what stays open

| Finding | Needs a new decision? | Done in this step |
|---|---|---|
| verify_cc2_0 B1: c1 skipped on a false premise (four records say the ep24 bundle is absent) | no | (1) Dated corrections: `../collcarve2-public/CORRECTION_20261101.md`, `../collcarve2-evalcheck/CORRECTION_20261101.md`, and the build log. The two PREREG statements (F-I5.17 (14), F-I5.18) need an orchestrator entry (F-I5.19); PREREG is a shared file. (2) c1 run here; P125 could not be cited because its scene, table and draws differ. **c1 fails**: `../collcarve-r2/t_i17_c1/README.md`. (3) The verdict goes with the eval-10 numbers: hand-off text in section 4, relay for the orchestrator. |
| verify_cc2_1 B2: eval precheck "hands-off" = H0, not the rule's H30 | no | H30 tables recomputed from the precheck's own records with its own `summarize.py`: `precheck_H30_tables.md`, `precheck_H30.json` (`scripts/precheck_h30.py`). |
| verify_cc2_1 B1: B4's robust ring profile does not work (SHELL roughness about 1 mm per face) | **yes** (ring rule F-I5.15 (1a) / (1b)) | Not fixed. Recorded in the public correction file. |
| New in this step: c1 fails | follows from the rule | Per F-I5.16 (1)(h), no F-I5 delivery is called usable before G1 has run in MuJoCo-Warp. Every plain-MuJoCo contact number in round 2 is labelled plain MuJoCo only. |

**c1 in short** [M] (plain MuJoCo 3.17.0, sim=rl options and limits, ep24 r0 at f246, both boards free, determined-
wright's poses and 16 draws):

| | carved 57 / 77 | default 50 / 71 | c1 needs |
|---|---|---|---|
| copies over 512 rows | 12 / 16 | 16 / 16 | >= 15 and 0 |
| max rows | 2,948 | 688 | ratio >= 3 (4.29: holds) |

MuJoCo-Warp [R, determined-wright 3c7fd32] gives 16 / 16 vs 0 / 16 and 2,027 vs 416-425 rows. Plain MuJoCo flags the
default set, which the evaluator's engine handles. So c1 fails on 2 of its 3 legs.

## 3. What was not done, and why

- No eval bundle was built, no F-I5.15 run was made on an eval episode, and no eval r0 folder was written. That
  includes the Embodiment layout, the gmg-sim/2 manifest and p1_pending.
- `collcarve_deliveries.md` was not created: nothing was delivered.
- No pose correction and no carve on eval references. Off-axis nests such as eval 10 are not carved under F-I5.15
  (7) in any case.
- The orchestrator's separate lanes under the owner's 02:50 UTC permission (`../ev10-cavsafe/`, `../rackslot/`, evals
  10 / 30 / 14) are outside F-I5. This step neither read their results nor touched their folders.

## 4. Hand-off text (for the orchestrator to relay; nothing was sent from this step)

> Collision carve round 2 (gmg F-I5.15 / F-I5.16): no eval carve exists and none was run. No public pair passed the
> rule (all five public folders are DO_NOT_USE), and on the rule's hands-off frames (no hand within 30 mm) no eval pair
> has a feasible pose where the packed colliders block. Where packed pieces overlap at rest, the visual meshes overlap
> too at the reference pose (evals 14, 30, 10, 1), so those are pose issues. Our contact-gate validity check c1 failed.
> On the ep24 r0, plain MuJoCo with the sim=rl limits flags the default pieces (16/16 copies over 512 rows, max 688),
> where your MuJoCo-Warp run showed none (416-425). So our pair-scene numbers, eval 10's 656-1,296 rows included, are
> plain-MuJoCo only. Eval 10's overflow stands on your FlashCHORD measurements, not on ours. At eval 10's one
> hands-off contact frame (f142) our plain-MuJoCo count is 516-656 rows (median 536); the 1,252-1,296 maxima are at
> in-hand frames f111 / f116. The H30 precheck tables for the pose lanes are in
> `docs/research/mesh-2026-10-26/gmg/build/I/results/collcarve2-eval/precheck_H30_tables.md` (branch
> claude/bold-albattani-6qmxsv). Nothing for you to run from this step.

## 5. Files

- `README.md`: this file.
- `precheck_H30_tables.md`, `precheck_H30.json`: the eval precheck on H30 (verify_cc2_1 B2).
- `scope_H30.json`: condition (iii) per pair.
- `scripts/precheck_h30.py`, `scripts/scope_h30.py`: both read only `../collcarve2-evalcheck/`. Run them with
  `<venv>/python -I scripts/<name>.py ../collcarve2-evalcheck <out.json>`.
- c1: `../collcarve-r2/t_i17_c1/` (README, JSON, log, launch hashes, scripts) and the driver
  `build/I/fi516_c1_ep24.py`.
- Corrections: `../collcarve2-public/CORRECTION_20261101.md`, `../collcarve2-evalcheck/CORRECTION_20261101.md`.
- Log: `build/I.md`, section "Collision carve round 2", entries from 1 Nov 03:01.
