# verify_slot3_0: board slot round 3 (F-I4.16 / F-I4.17), rule-compliance lens

Verifier, 31 Oct - 1 Nov 2026, 23:55-00:20 UTC. I did not build this. My job was to find what is wrong with it. Lens:
rule compliance. I checked six things:
- F-I4.16 and F-I4.17 were pushed before the first run with each (git times);
- the implementation is the written rule: the low-piece rectilinear body and its IoU fallback, the box partition, and
  the contact gate with its sim=rl limits and one-box control;
- the w10 seeds are new;
- the freeze conditions were evaluated exactly as written;
- no ground truth was read;
- nothing was tuned after outcomes.

Scope:
- PREREG F-I4.16 (all) and F-I4.17.0-F-I4.17.9; INTERLOCK 20.13-20.14; `build/I.md` "Board slot round 3" (all);
- code `platebody.py` (REV 17), `contactgate_fi4.py`, `tools/interlock_dev.py` (the F-I4.17 lines),
  `tests/test_fi416.py`, `tests/test_fi417.py`, `build/I/fi417_identity.py`, `build/I/fi417_ep23.py`;
- results `build/I/results/slot3-ep24/`, `slot3-ep23/`, `slot3-tests/fi416/`, `slot3-tests/fi417/`;
- scratch `<scratch>/slot3/`, `<scratch>/slot3b/` (launch scripts, identity attempts, smoke, result files).

Labels: [M] measured or read from records, [R] code or document reading, [E] estimate, [H] hypothesis. My only
computation was `<scratch>/verify_slot3_0/regate.py`. It re-runs the committed `contactgate_fi4.gate` on the committed
fi4q r0 piece files in the ep24 scenes (f246 / f218, our clean bundle `b4ext4-b61e8aa`), and recounts the recorded
per-copy rows. It is a reproduction only: I computed no other control, threshold, ratio or body.

## Answer

**Compliant. No blocking finding.**
- **Timing.** F-I4.16 was pushed at 21:36:32, 37 minutes before its first code commit and run. F-I4.17 was pushed at
  22:41:21, about 15 minutes before its first code run (22:56) and 17 minutes before its code was committed in full.
- **Code.** After the first F-I4.17 outcome (gate validity, 22:59:47), the only code change was a130449. That change
  touched the failure-message line and file handles; the pass logic did not change. `platebody.py` is byte-identical
  in every F-I4.17 run.
- **Rule text.** The F-I4.17 text was not edited after the push, apart from the 22:43 -> 22:41 stamp (c8d092a).
- **Implementation.** The code does what F-I4.17.1-F-I4.17.2 say. The differences are as-built readings that leave
  the result unchanged (N7, N8).
- **Seeds.** The w10 seeds are new.
- **Freeze.** The freeze rule was applied as written: (a) fails on the part-1 ratio, (b) holds as F-I4.17.3 reads
  it. The round is not frozen, nothing was tuned and eval 25 was not run.
- **Ground truth.** None was read.

**Measured.** I re-ran part 1 on the committed r0 files. The verdict reproduces: delivered 128 / control 32, ratio
4.0, against the record's 124 / 32 = 3.875. Default and control are identical to the record.

Three points matter for the next decision. None is a violation:
- **N3. The one-box control is not "a plain board" in the delivered configuration.**
  - Each control pair starts with its two unslotted boxes crossing each other: 4 contacts in every copy before
    anything reaches the table.
  - At its max-nefc step the control has 8 board-table and 0 board-board contacts. The delivered pair stays assembled
    on its edges (24-28 board-table, 0-3 board-board).
  - The 2.0 ratio therefore compares an assembled pair with two boards that no longer touch.
- **N4. "(b) holds" depends on F-I4.17.3's reading of the decision.** The rule gates only k5's contact count. If every
  w10 cell had to pass the gate, k2 (ratio 2.08) would fail (b) too.
- **N5. The max-nefc statistic moves by one contact (4 rows) when the vertices are rounded to 1e-8 m.** The thin w10
  margins (2.00-2.09) are within that.

## Verdict

| Item | Status |
| --- | --- |
| F-I4.16 committed and pushed before any F-I4.16 code or run | **confirmed [M]** (reflog, launch files) |
| F-I4.17 committed and pushed before any F-I4.17 code or run | **confirmed [M]** (reflog; first code run 22:56) |
| PREREG F-I4.16 / F-I4.17 text unchanged after outcomes | **confirmed [M]** (only c8d092a stamp fix and other lanes' new entries since 030260b) |
| Code unchanged after the first F-I4.17 outcome, except a message fix | **confirmed [M]** (diffs a130449..HEAD on every board-slot file) |
| Low-piece search, ties, IoU gate 0.90 and polygon fallback = F-I4.17.2 | **confirmed [R]**; fallback exercised on w10p (0.741) and ep23 board 1 (0.814) [M] |
| Box partition (slab A / B, fewer, tie A, tiling <= 1 mm2) = F-I4.17.2 | **confirmed [R][M]** (5 / 3 boxes, tiling 0.0 mm2 on every record) |
| Contact gate: sim=rl values, sha256, options, scenes S1 / S2, 16 copies, overflow rule, pass rule, control | **confirmed [R][M]**; synthetic table reading (N8) |
| One-box control = F-I4.2 frame box, t of F-I4.15.1, 0.3 kg | **confirmed [R]**; degenerate start (N3) |
| w10 seeds new; w10 fixtures unchanged since F-I4.16 | **confirmed [M]** (git grep at 782db1c; `test_fi416.py` untouched since 3b7e6d0) |
| Freeze (a) fails (part 1 ratio 3.875 > 2.0), (b) holds as read, not frozen, eval 25 not run | **confirmed [M]** (recomputed from the records; part 1 reproduced) |
| r0 DO_NOT_USE names `contact_budget`; not handed off (F-I4.17.6 step 8) | **confirmed [M]**; two field details (N7) |
| GT-free (no scan, mocap, parquet pose, `*_align`, library shape; `meshes/carve/ev25` not read) | **confirmed [R][M]** for what the code and records show |
| Run order: code checks before any freeze input (F-I4.17.6 step 2) | **deviation, no outcome effect** (N1) |
| "Committed before any run" (F-I4.17.6 step 1) | **deviation, no outcome effect** (N2: pre-commit smoke) |
| No rental, $0 | **consistent [R]**: every launch file names this container; no Vast step in the round-3 lines; ledger not read |

## What I checked (confirmed)

**C1 Timing [M].** Push times come from `git reflog` of `origin/claude/bold-albattani-6qmxsv` ("update by push").
Launch times come from the launch files. File times come from mtimes in `<scratch>/slot3*/`.

| Event | UTC |
| --- | --- |
| F-I4.16 (782db1c) committed / on origin | 21:36:31 / 21:36:32 |
| F-I4.16 code (3b7e6d0) committed / on origin; first F-I4.16 launches | 22:13:55 / 22:13:57; 22:14:17 |
| F-I4.16 geometric w10 records written (k1234, k6789); Identity | 22:19:35, 22:19:34; 22:32:44 |
| Orchestrator stops the round-3 runs (fi4p, k5 killed) | 22:17 (log line) |
| F-I4.17 (030260b) committed / on origin; stamp fix c8d092a | 22:41:19 / 22:41:21; 22:42:02 |
| F-I4.17 code first in git (another agent's WIP snapshot 76a72d1; 94b98f0 `with open` only) | 22:56:52, 22:57:41 |
| Pre-commit smoke (`smoke/smoke.json`, uncommitted code) | 22:56:58 |
| dc4a2a4 (adds `fi417_ep23.py`; tree = the build) committed / on origin | 22:58:26 / 22:58:28 |
| Gate validity launched (dc4a2a4) / result written (errored in its message line) | 22:58:59 / 22:59:47 |
| a130449 (message fix) committed / on origin | 23:00:50 / 23:00:52 |
| Freeze-input launches: ep24 fi4q, k5 (a130449); k1-k4, k6-k9 | 23:01:02; 23:03:30 / 23:03:31 |
| Code check (i) launched (4th attempt) / passed | 23:03:21 / 23:05:13 |
| Freeze decision logged / committed (19e044d) | 23:27 / 23:36:32 |

F-I4.17 says it was written 22:28-22:41 without reading the F-I4.16 w10 records. Those records existed from 22:19. I
cannot test the claim. The F-I4.17 text cites no number from them, and its predictions P127-P128 are not phrased in
F-I4.16 terms.

**C2 Code frozen [M].** Every commit after 94b98f0 that touches `platebody.py`, `contactgate_fi4.py`,
`tools/interlock_dev.py`, `simphys.py`, `simpieces.py`, `interlock.py`, `tests/test_fi416.py` or `tests/test_fi417.py`:
- dc4a2a4: `fi417_ep23.py` only;
- a130449: `summary_line` reads the set names now carried in the record, plus two new record keys and `with open` in
  the test. The pass line `ok = overflow_copies == 0 and ratio <= 2.0` is unchanged.

Nothing after a130449 touches these files. Two launches were at other agents' WIP commits: ReRuns at ced42fd (cavpieces,
collcarve, contactgate5, collcarve2_dev only) and ep23 at a130449 with collcarve.py dirty. `collcarve` is imported only
under `--waiver-fi5` (`interlock_dev.py:371-372`), so neither affects the board-slot path [R].

**C3 Rule text [M].** `git diff 030260b HEAD -- PREREG.md` contains one changed line, the 22:43 -> 22:41 stamp in
c8d092a. Every other change is the collision-carve lane's new entries (F-I5.16, F-I5.17). No F-I4.17 threshold,
ratio, IoU, search or freeze line changed.

**C4 Low-piece search = F-I4.17.2 [R].** `_LPFit` / `low_piece_fit`:
- The waist spans every column. Stage 1 is exhaustive over `0 <= w0 < w1 <= n_W`.
- Each end stage is exhaustive over `e in {0} U [1, floor(n_L / 3)]` (`lp_end_frac` 3), with `p0 <= w0`, `p1 >= w1`
  and the rest fixed.
- The waist-again stage covers rows inside the present ends.
- There are at most 10 passes, stopping when theta repeats.
- Ties follow `_lp_better`: IoU within 1e-12, then fewer rectangles, smaller union area, lexicographic theta.
- IoU is counted in cells by a 2-D prefix sum on the component raster cropped to its bounding box. That is the
  F-I4.15.2 (b) component, so the waist spans the full length as F-I4.17.2 states.
- Gate `iou >= 0.90` (`lp_iou_min`). Otherwise the flag is `low_piece_iou_fail` and the F-I4.16 ladder polygon (that
  rung's body, unchanged code) is used.
- The body is U's ring extruded through `_body_of`: frame axes, centre c0, half `[L/2, W/2, t/2]`.

Code check (ii) passed in the smoke [M]: the I-mask gives theta (3, 66, 10, 0, 69, 10, 0, 69) with IoU 1.0, the
rectangle gives 1 rectangle, the T gives 2.

**C5 Box partition [R][M].** `_slab_boxes` cuts at every distinct vertex coordinate along one axis. It takes the
section intervals at each slab's middle and merges identical intervals of adjacent slabs. `box_partition` runs both
axes and keeps the one with fewer boxes, A on a tie, then checks the tiling to <= 1 mm2.
- Every ep24, w10, w7, w8 and w8b record shows 5 slotted / 3 default boxes, with tiling difference 0.0 mm2.
- w1 at t = 10 shows 3 / 1.
- ep24 board 1's slotted boxes: smallest side 9.401 mm, equal to w.

**C6 Contact gate = F-I4.17.1 part 1 [R][M].**
- **sim=rl values.** Read from `docs/research/work/15-verify/cfg_sim_rl.yaml`. sha256 `695536b7...4b66` matches
  PREREG, and the same blob sits on `origin/claude/determined-wright-3joens`. `mismatch: null` in every record. Values:
  fps 20, substeps 5, newton, implicitfast, pyramidal, njmax 512, nconmax 256, impratio 20, iterations 100,
  ls_iterations 50.
- **Scene.** `count_xml` is `simphys.settle_xml` line for line (plane, friction 0.5, free bodies, `_inertial`,
  `_geoms` condim 3 / friction 0.5, gravity -9.81 n). It adds the sim=rl `<option>` (dt 1 / (20 x 5) = 0.01 s) and
  `<size njmax nconmax>`.
- **Frames and copies.** S1 = `asm[len // 2]`, as in `pair_physics`' P1 pre-check frame; S2 = `asm[0]`. 16 copies via
  `simphys.jitters(seed=1)`, with the guest jittered as `T_wg @ Jm` (as `settle`), 2.0 s = 200 steps.
- **Per copy.** `ncon` / `nefc` after every `mj_step`, the CONTACTFULL / CNSTRFULL counters, and the classes at the
  max-nefc step.
- **Overflow** = `max_ncon > 256 or max_nefc > 512 or a warning`.
- **Pass** = no delivered overflow in any scene or copy, and delivered max nefc <= 2.0 x control max nefc.
- **Control.** `control_hulls(body)` is the 8-vertex frame box (L x W of the F-I4.2 rectangle, all-point t, c0, axes),
  one mesh geom per board, 0.3 kg via `SP.props`.
- **Driver.** Part 1 runs after P2-P7 in `run_waiver` for REV >= 17. A fail appends `contact_gate_part1` and writes
  DO_NOT_USE naming `contact_budget` with the numbers. The r0 manifest gets the `manifest_fi417` keys, the part-1
  record, `contact_budget_pending: true` and part 2 marked pending with its reason.
- **Code check (iv)** (smoke) gave nefc = 4 ncon at every step.

**C7 Reproduction of the ep24 verdict [M]** (`<scratch>/verify_slot3_0/regate.py`, committed code, committed r0
files):

| set | recorded max nefc / ncon / overflow | from the committed .obj files |
| --- | --- | --- |
| delivered (5 + 5 boxes) | 124 / 31 / 0 of 32 | **128 / 32 / 0** (S1 128, S2 124) |
| default (3 + 3 boxes) | 112 / 28 / 0 | 112 / 28 / 0 |
| control (1 + 1) | 32 / 8 / 0 | 32 / 8 / 0 |
| ratio | 3.875 | 4.0 |

A recount of the 32 recorded per-copy rows per set gives 124 / 31 / 0, 112 / 28 / 0 and 32 / 8 / 0, ratio 3.875. The
difference from my re-run is the .obj text (8 significant digits); see N5. The verdict holds either way.

**C8 Seeds and fixtures [M].** The w10 records carry seeds pose 4160 + k, noise 4260 + k, samples 4360 + k / 4460 + k
for k = 1..9. w10p uses k = 10 and w10n k = 11.
- `git grep` at 782db1c finds none of these numbers in any `.py` file. The seed calls in `gmg/` code then were 0-9,
  20, 101 and 1000, as F-I4.16.2 states.
- `tests/test_fi416.py` (which `test_fi417` imports for `w10_episode`, `iplate10`, `CELLS`) is unchanged since
  3b7e6d0, so the fixtures are those of F-I4.16.2.

**C9 Freeze evaluated as written [M]** (recomputed from `slot3-tests/fi417/test_fi417_k*.json` and
`slot3-ep24/fi4q/`).
- **(b), all nine cells:** both boards CARVE T1 through the waiver route, `low_piece` on both, IoU 0.9719-0.9960.
  Boxes 5 / 3, keep-out max 0.0 cm3, |w - (t + 2)| <= 0.33 mm (largest: k8 A 11.67 vs 12).
- **(b), k5:** P2-P7 pass (`pass_P2_P7`, failing list empty). Part 1 passes: 84 vs 48 rows, ratio 1.75, no overflow.
- **(b), the other cells' ratios** (not freeze inputs): k1 1.67, k2 2.08, k3 1.83, k4 1.50, k6 2.00, k7 1.83, k8 1.67,
  k9 1.75.
- **(a), ep24 fi4q:**
  - Both boards CARVE T1 with `low_piece`, IoU 0.958 / 0.952 (not a fallback).
  - P2-P7 pass. `acceptance.failing` is `['contact_gate_part1']` only. P3 carved 0.074 cm / 0.68 deg, overlap 0.039
    cm3.
  - Part 1 fails on the ratio (3.875), with no overflow.
- So (a) fails. F-I4.17.3 says the round stops, nothing is tuned and eval 25 is not run. That is what happened: no
  eval-25 run or r0 exists, and no code changed after the outcome.
- **P128 [M].** At each t the IoU drops from sigma_e 1 to 2 and rises from 2 to 3: t 6 A 0.979 / 0.972 / 0.982; t 8
  A 0.983 / 0.980 / 0.982; t 10 B 0.996 / 0.976 / 0.987. So P128's "does not rise" clause fails, as reported.

**C10 GT-free [R][M].**
- The F-I4.17 code reads only our bundle poses (`world_T_cam`, `cam_T_obj`), our table estimate and our pieces.
  `mocap_pos` in `count_replay` is the MuJoCo replay target, not mocap data.
- Neither `fi417_ep23.py` nor the tests read scans, parquets, `*_align` files or library meshes.
- Prep25 read our own packed reference parquet (an mkref output of run c25s42, as F-I4.17.9 lists). It was read outside
  the gmg guard, for the mapping only. No eval-25 gmg run followed, and `meshes/carve/ev25` was not opened by any
  round-3 script I read.

**C11 Delivery [M].** `fi4q/r0/DO_NOT_USE.json` names `contact_budget (F-I4.17.1 part 1)` with the numbers for both
boards. Per F-I4.17.6 step 8 the r0 was not sent for P1 or part 2. The README gives the path and the four asks in case
of a new decision. Part 2 not running here is recorded: no warp, newton, mujoco_warp or FlashCHORD in the container,
checked at 22:55, as F-I4.17.1 asks.

**C12 Other checks [M].**
- Code check (i): 163 piece arrays byte-identical, 0 record differences (`identity_rev16.json`).
- The waiver-off `test_interlock` suite ran 24 tests: OK, 2 expected failures, as in round 2.
- Gate validity: run twice (dc4a2a4, a130449) with identical numbers. 868 rows, 3 / 16 overflow copies at S1, ratio
  27.125; control vs control passes with ratio 1.0.
- The pre-commit W1 t = 10 record equals the committed-code W1 record field for field, excluding timing (my
  comparison).

## Non-blocking notes

- **N1 Run order: freeze inputs were launched before code check (i) passed** [M].
  - F-I4.17.6 step 2 puts the code checks "before any freeze input". ep24 fi4q and k5 were launched at 23:01:02, and
    k1-k4 / k6-k9 at 23:03:30.
  - Check (i) passed only at 23:05:13. Its first three launches (22:59:00, 23:01:02, 23:01:34) failed because the
    3b7e6d0 tree extraction lacked `pipeline/provenance.py`, then `ops/provenance/denylist.json`, then `autokit`. The
    fourth (23:03:21) passed.
  - No outcome effect: (i) found 0 differences, and `platebody.py` did not change.
  - This is the same class as verify_slot2_0 N3. I.md does not label it as a deviation. The 23:02 line names one
    failed attempt; the 23:05 extraction note implies the other two.
  - Fix: one line in the F-I4.17 outcomes.
- **N2 Pre-commit smoke on uncommitted code** [M].
  - Code checks (ii)-(iv) and W1 t = 10 under REV 17 ran at about 22:56 (`smoke.json` 22:56:58). That was before
    dc4a2a4, with no launch file, against F-I4.17.6 step 1 ("Committed before any run; the launch commit of every run
    goes to a launch file").
  - (ii)-(iv) were never re-run at a commit. W1 was re-run at a130449 with an identical record.
  - The I.md line calls the smoke "code checks only", but it includes the P134 report.
  - The F-I4.16 build did the same before 3b7e6d0 (F-I4.16.6 has the same sentence).
  - No outcome effect. Fix: re-run `CodeChecks` at a130449 for the record, or add the deviation to the outcomes.
- **N3 The control is degenerate** [M numbers, E reading].
  - Every control copy starts with ncon0 = 4 at S1 and S2. The pair sits 16.7 / 17.0 mm above the table, so these
    are board-board contacts of two crossing unslotted boxes.
  - At the max-nefc step every control copy has 8 board-table and 0 board-board contacts. That step is 41-50 at S1.
    At S2 it is step 6 in 13 of 16 copies (about when a 17 mm drop reaches the table) and 46-52 in the other 3.
  - The delivered set at its max has 24-28 board-table and 0-3 board-board contacts. The default set has 14-20
    board-table and 4-8 board-board.
  - Reading [E]: the solver pushes the crossing control boxes apart, so the denominator measures two boards that do
    not touch. Each rests with about 4 plane contacts, whatever its pose.
  - This is the decision's control as written ("same scene"), so the gate was applied correctly. But "3.875 x a plain
    board" overstates what was compared. Any later decision on the ratio should use the per-class numbers, not the
    ratio alone.
- **N4 Reading of the decision's freeze (3)** [R].
  - The decision says the w10 full cells "must CARVE ... and pass the contact gate (geometry for all cells, physics +
    contact gate for the sigma 2 / t 8 cell)". F-I4.17.3 (b) gates part 1 on k5 only. That matches the parenthetical
    and was pushed before any run, so it is compliant.
  - Under the wider reading, k2 (2.0833) fails and (b) fails too.
  - No outcome effect (not frozen either way). Quote "(b) holds" with "as F-I4.17.3 reads it", and state the reading
    explicitly in any later entry that reuses w10.
- **N5 Count sensitivity** [M].
  - Re-running part 1 on the committed .obj pieces (vertices rounded to 1e-8 m) gives one more delivered contact (128
    vs 124 rows at S1); default and control are unchanged.
  - The max-nefc statistic is a maximum over 32 chaotic settles. It moves by at least 4 rows under 1e-8 m rounding.
  - Ratios within about 0.1 of 2.0 are within this noise: k2 2.08, k6 2.00, w10n 2.09, and k5's 84 / 48 is 1 contact
    from 1.83.
  - Recommend recording the counts' spread (for example, delivered from the written files as well as from memory)
    with any future gate.
- **N6 The gate validity check flags both round-2 sets but ranks them the other way from MuJoCo-Warp** [M].
  - In plain MuJoCo, the round-2 default prisms give 880 rows with 1 / 16 overflow and the carved prisms 868 with 3 /
    16. MuJoCo-Warp (determined-wright, large buffers, their reference) gave default 416 and carved 2027, and the
    default never overflowed under sim=rl.
  - P125 holds as written. The [E] "plain MuJoCo with multiccd is at least as strict" is better read as "it rejects
    both; its ordering differs". Part 1 would also have rejected pieces that the evaluator's engine handled without
    overflow.
  - The scenes differ (their reference holds the pair 27-36 mm up, ours 16.7 mm), so this is not like-for-like.
  - Part 2 (budget.py) stays the only evaluator-faithful number.
- **N7 r0 fields against F-I4.17.4** [M].
  - (a) The manifest has `p1_pending: false`, where F-I4.17.4 writes `p1_pending: true`. Yet each object's
    `carve.json` flags still list `p1_pending`, which is internally inconsistent. False is defensible for a
    DO_NOT_USE record that is not sent.
  - (b) The manifest's part-1 record drops `per_set`, so it has no per-copy rows, where F-I4.17.4 says "per scene and
    copy". The rows are in `fi4q/contact_gate_*.json`, outside the r0 folder, so a recipient of the r0 alone lacks
    them.
- **N8 Synthetic table placed over all sets** [R].
  - `scenes_synth` puts the table 1 mm beyond the lowest vertex along d over delivered, default and control together.
    F-I4.17.1 says "the pair's lowest piece vertex". The docstring discloses this ("so all sets share the table");
    PREREG and I.md do not.
  - For the delivered set the gap is therefore >= 1 mm, larger where the frame box or the unslotted default reaches
    farther along d [E: at most a raster cell or so].
  - It touches only the synthetic cells, where k5 is a freeze input that passed.
- **N9 sim=rl provenance** [R]. The values are measured from the committed copy, whose sha matches PREREG and
  determined-wright's branch. Its equality to FlashCHORD's `configs/sim/rl.yaml` at the pin rests on notes (the F-I5.16
  22:46 line), not on a sha of that source, which is not on this machine. F-I4.17.1 discloses this.
- **N10 Outcome records** [M].
  - PREREG F-I4.17 has no Outcomes bullet, INTERLOCK has no round-3 result section, and STATUS.md has no round-3 line
    (its last change, e5baab1, is the C0b report).
  - `build/I.md` and the work log hold the results.
  - CLAUDE.md asks for STATUS after each meaningful result. Left for the report step, which should also carry N1 / N2.
- **N11 Minor record details** [M].
  - dc4a2a4's message says "F-I4.17 build", but its diff is `fi417_ep23.py` only. The code entered git through
    another agent's WIP snapshots 76a72d1 / 94b98f0, which the builder disclosed; the tree at dc4a2a4 is the build.
  - The `fi417_ep23.py` docstring says it writes `ep23_fi416.json`; it writes `ep23_fi417.json`.
  - `test_counter_box_on_plane` (check (iv)) drops a second box onto the first, so it is not "one box at rest". The
    nefc = 4 ncon identity still holds over all 100 steps.

## Files

- This note: `build/I/verify_slot3_0.md` (the only file committed by this verifier).
- Reproduction: `<scratch>/verify_slot3_0/regate.py` and `regate.json` (not committed; scratch =
  `/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad`).
