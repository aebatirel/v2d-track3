# verify_slot2_0: board slot round 2 (F-I4.15 outline body), rule-compliance lens

Verifier, 31 Oct 2026, 20:20-20:45 UTC. I did not build this; the job was to find what is wrong with it. Lens: rule
compliance. I checked five things:
- F-I4.15 was pushed before the first run (git times);
- the implementation is the written rule;
- the thickness and outline settings are as written;
- no ground truth was read;
- nothing was tuned after outcomes, and the controls are unchanged.

Scope:
- PREREG F-I4.15.0-F-I4.15.10 plus its Outcomes bullet; INTERLOCK 20.10-20.11; `build/I.md` "Board slot round 2";
- code `platebody.py`, `tests/test_fi415.py`, the shared-file edits in 19c4309;
- results `build/I/results/slot2-ep24/` and `slot2-ep23/`;
- run `<scratch>/gmg/runs-dev/20261031-i2probe-626ce13` and `<scratch>/fi415/`.

Labels: [M] measured or read from records, [R] code reading, [E] estimate, [H] hypothesis. My only computation was
`<scratch>/verify_slot2_0/recount.py`. It reruns the committed `convex_partition` / `slotted_polygon` on the
recorded polygons. I computed no counterfactual tolerance, cap or slot.

## Answer

**Compliant. No blocking finding.**
- The rule was pushed at 18:14:58. That is about 10 minutes before the first F-I4.15 code file was written (18:24:30),
  14 minutes before that code was committed (18:29:11), and before any run.
- Every run used one byte-identical `platebody.py`.
- The rule text was not edited after any outcome.
- The code does what F-I4.15 says, with one laxer synthetic threshold (N4).
- No ground-truth input was used.
- The freeze rule was applied as written: (b) failed, so the rule is not frozen and eval 25 was not run.

Two points matter for the next decision. Neither is a violation:
- **N1. The ep24 CARVE depends on F-I4.15.3's reading of "depth".** Depth is measured from the polygon edge. If it were
  measured from the rectangle edge, the cross-lap check would read 15.88 mm (more than the 10 mm window) and the pair
  would PUSH.
- **N2. ep23 can no longer serve as an independent freeze check** for any fix of the prism count.

## Verdict

| Item | Status |
| --- | --- |
| F-I4.15 committed and pushed before any F-I4.15 code or run | **confirmed [M]** (reflog push times, below) |
| No F-I4.15 code before the rule; one `platebody.py` for every run | **confirmed [M]** (blob hashes at 8 commits) |
| PREREG F-I4.15.0-.10 text unchanged after outcomes | **confirmed [M]** (only additions since 033d8a8; no removed line) |
| Implementation = written rule (t, outline, polygon, slot, budget, pieces, cap, gate, delivery) | **confirmed [R]**, one laxer test threshold (N4) |
| Thickness: step-2 estimator on all near points; outline: 2 mm, >= 3 frames, closing, fill, largest, DP 1.0 mm | **confirmed [R][M]** |
| GT-free (no scan, mocap, parquet pose, `*_align`, library shape; no `meshes/carve/ev25`; no ep25 output) | **confirmed [M]** for what the records show |
| Nothing tuned after outcomes (code, thresholds, tolerance, cap) | **confirmed [M]**; 2 harness edits after outcomes, both benign (C9) |
| Controls unchanged (acceptance, simphys / simpieces / physcheck, waiver-off suite, default = unslotted prisms) | **confirmed [M]** |
| Freeze rule (a) holds / (b) fails, not frozen, eval 25 not run, [H] fix not adopted | **confirmed [M]** |
| Prism counts 50 / 57, 71 / 77 (ep24), 85 / 56 (ep23) | **reproduced [M]** from the recorded polygons |
| Run order T-I1 -> T-I11 (F-I4.15.6 steps 2-3, F-I4.15.7 "before T-I11") | **deviation, no outcome effect** (N3) |
| Code identity in the records | **imprecise in 4 places** (N5) |

## What I checked (confirmed)

**C1 Timing [M].** Push times come from `git reflog` of `origin/claude/bold-albattani-6qmxsv` ("update by push").
File times come from mtimes in `<scratch>/fi415/`.

| Event | UTC |
| --- | --- |
| f62454a F-I4.15 committed / pushed | 18:14:55 / 18:14:58 |
| 033d8a8 time correction pushed | 18:15:09 |
| Build step starts, confirms the rule on origin (log) | 18:22 |
| First F-I4.15 code files in scratch (`geom2d.py`, `t_geom.py`) | 18:24:30 / 18:24:48 |
| Patches applied to `platebody.py` (`patch1.py`, `patch2.py`) | 18:27:22-18:27:43 |
| F-I4.15 `platebody.py` first in git: caefcb4 (an automatic WIP snapshot) | 18:29:11 (pushed 18:29:14) |
| Probes w1 / w8 (`probe_w8.py` written 18:31:56) | 18:30-18:36 |
| T-I1 suite, T-I11 fi4o, ep23 candidates, ep23 check launched | 18:38:09, 18:38:27, 18:39, 18:41:48 |

Before the rule, `platebody.py` was the same blob at 0358fa2 (17:08) and f62454a (702 lines, sha256 2616dda3...). So
no F-I4.15 code was committed before the rule. Every F-I4.15 file time is after the 18:14:58 push.

**C2 One code version [M].** `platebody.py` has blob sha256 a1ca8960... (1516 lines) at caefcb4, b738250, 6ed88f1,
19c4309, 3fbd467, HEAD and the current origin head. So the following all ran the same `platebody.py`:
- the probes (from 18:30);
- the T-I1 suite;
- fi4o;
- both ep23 runs;
- the w8 rerun;
- the waiver-off suite.

For fi4o, `report.json` `launch_code` agrees with 19c4309 on platebody, interlock, simphys, simpieces, physcheck,
gen_slot, silhouette and the driver.

**C3 Rule text frozen [M].** `git diff 033d8a8 <origin head> -- PREREG.md` has no removed line. The only changes in
F-I4.15 are the appended Outcomes bullet (1bd1392, 3fbd467). The rest of the diff is F-I5 entries from the other
workflow.

**C4 Implementation = rule [R].** Each F-I4.15 item maps to code as follows. "As written" means I found no difference.

- **F-I4.15.1 (t and mid plane from all points):**
  - `plate_info` calls `_apply_t_all` for step 1 (reference: the decided pair's mid_n / mid_d) and for step 2
    (reference: plane 0's normal and d, returned by `_camera_side` as `_a` / `_d_ref`).
  - `_t_all_points` uses all `_near_points` (6 mm filter, no downsample, no cap):
    - slab |a.x - d_ref| <= 25 mm (`structure.consts` slab [0.003, 0.025]);
    - camera-side split, medians, t = m+ - m-;
    - checks: >= 300 points (`plane_min`) from >= 3 frames on each side, t > 0, t within 3-25 mm;
    - a failure gives `t_all_points_fail`, so the object is not plate-like.
  - One-face plates: `_m_seen_all` takes the median of the seen side over all slab points.
    `resolve_one_face` sets mid_d = m_seen - seen_sign t / 2 with the partner's (all-point) t, and the extent test uses
    w = t + 2 mm. The plate TESTS stay on the downsample. As written.
- **F-I4.15.2 (polygon body):**
  - The frame is the unchanged F-I4.2 `plate_body`, with the F-I4.15.1 t and mid plane. The 0.9 fill gate is dropped;
    `plate_body_poly` only needs a box.
  - Re-raster at 2 mm along (a_L, a_W) from the rectangle's low sides, slab t / 2 + 3 sigma, the same cell rules.
  - `mask_ring` outer ring, `drop_collinear`, then `dp_ring` at `simplify_m` = 1.0 mm (generic), split at the farthest
    pair.
  - `ring_simple` with the fallbacks `outline_unsimplified` and then `plate_outline_not_simple`; ±t / 2 prism; no
    balls.
  - FREE share computed by the same code for the polygon and for the rectangle.
  - [M] The recorded ep24 polygons lie on the 2 mm rectangle lattice (max deviation 0.0002 cells) and are simple; 95-97
    % of their edges are axis-parallel.
- **F-I4.15.3 (slot on the polygon):** `slot_for_poly` wraps the unchanged `slot_for`:
  - width t_partner + 2 mm, the F-I4.12 centre at the middle of the rectangle-based range, and the split cap from the
    component centroid, as before;
  - b = u_rect - s_e D_rect;
  - u_e = the outermost polygon coordinate in |u - c_L| <= w / 2, and D = s_e (u_e - b);
  - box from u_rect + s_e 3 mm to b, thickness ±(t / 2 + 3 mm).
  - `crossing_extent_poly` uses the grid points inside both polygon prisms.
  - `slot_budget_poly`: area share (cumulative), reach on the clipped footprint, topology (one simple ring, area
    consistent, bottom inside, both prongs > 0); thresholds `IL.K('budget_vol')` / `budget_reach`, unchanged.
- **F-I4.15.4 (pieces):**
  - The footprint is subtracted in 2-D (Weiler-Atherton), then the polygon is partitioned.
  - `ear_clip`: first ear in ring order from the lowest index; strictly convex; closed-triangle test.
  - `hertel_mehlhorn`: diagonals longest first with index ties; a diagonal is removed if both ends have an interior
    angle <= 180 deg.
  - Parts over 32 vertices are split at vertex 0 to floor(k / 2).
  - Cap: floor(165 / len(objects)) for both the default and the slotted set; over the cap gives `fail(...)` without a
    push, which keeps the old decision.
  - `keepout_gate` is unchanged except `in_box(body)` becomes `in_body(body)` (the polygon prism), which the rule
    implies.
- **F-I4.15.5 (delivery):** the r0 `owner_waiver` block carries fi4_rev 15, the polygon (`poly_mm`), `tolerance_mm`
  and the piece counts. Also: `p1_pending` true, no `DO_NOT_USE.json`, `_default/` = 50 / 71 unslotted prisms, 57 / 77
  slotted at the top level.
- **F-I4.15.6 step 3:** the fi4o argv equals the fi4b argv except `--tag fi4o`. Same bundle `b4ext4-b61e8aa`, picks
  `shell_t5p36`, hands, video, calib, `--identity eval`, 16 copies, no `--gen`. The launch record names 19c4309.
- **F-I4.15.6 step 4 (ep23):** `fi415_ep23.py` runs `plate_info`, `resolve_one_face`, `plate_body_poly` and
  `pieces_poly` with cap = 82 (2 objects). It does no linking, slot, decision or physics. Bundle v6 `b4ext6-90c8cce`;
  picks `shell_t5p36` from `tools/interlock_cands`.
  - `dev_constants.json` has the same sha256 (6dd16e2e...) as for ep24's candidates. Every constant value is identical;
    only source line numbers differ.
  - The producer code changes since the ep24 candidates are only ball metadata: `pack.py` and
    `producers/__init__.py`, checked by diff; `shell` / `hull` are unchanged.
  - Both ep23 runs (18:41 and 19:11) give identical JSON apart from code / sec / png.

**C5 Thickness and outline settings [M].**
- ep24 board 1:
  - step 2;
  - t_down 6.212 mm, then all-point t 7.401 mm on 1,759,844 slab points (736,196 / 1,023,648, 38 / 101 frames);
  - polygon `used: simplified`, `tolerance_mm` 1.0, `loops` 1, `pinch_vertices` 0.
- ep24 board 2: step 3 with t := 7.401 mm; seen face over 1,408,169 points.
- ep23 board 1: step 3 with t := 10.785 mm from board 2, flagged `plate_t_partner_prior`. Board 2's track is the wrong
  board.

**C6 GT-free [M].**
- fi4o manifest:
  - inputs: calib, video, tracks P1 (`data/sweep/ep24/poses.npz`, the same as fi4b), hands (dev), and the clean-run
    bundle npz / json;
  - guard hook installed, 0 blocked, 0 refusals;
  - the guarded opens are only those four files.
- ep23 candidate manifest: dev_constants, tracks P1, bundle; hook installed, 0 refusals.
- `fi415_ep23.py`, `fi415_png.py`, `fi415_summary.py`, `test_fi415.py` and `platebody.py` contain no reference to
  parquet, mocap, `_align`, scan, library, `ev25` or `meshes/`.
- No ep25 run directory or output exists.
- Limit: the ep23 check script wrote no guard manifest of its own (its candidate build did).

**C7 Controls [M].**
- Since f62454a: `simphys.py`, `simpieces.py` and `physcheck.py` are unchanged; `platebody.acceptance` is unchanged;
  the only `interlock.py` change is the other agent's cbed3cb.
- The waiver-off suite ran all 11 non-Waiver classes of `test_interlock.py` (Sweep through PiecesGate): 24 tests, OK,
  2 expected failures.
- The old `Waiver` class is pinned to REV 14, so its F-I4.14 records stay reproducible.
- The default in P2-P7 is the unslotted polygon prisms, as F-I4.15.5 states.

**C8 Freeze and predictions [M].**
- (a): CARVE both, P2-P7 and keep-out pass.
- (b): ep23 board 1's default prisms are 85 > 82, reproduced by `recount.py` from the recorded polygon.
- So F-I4.15 is not frozen. No rerun, relabel or alternative tolerance was tried. The [H] fix is labelled and not
  adopted.
- P51-P58 are scored against their written thresholds.

**C9 Edits after outcomes, all benign [M].**
1. 6ed88f1 (18:37:01, after the w8 probe showed B over the cap) adds three lines to `w_checks`: a CARVE that did not
   come from the waiver route is recorded as a miss instead of raising a KeyError. The check is stricter, not laxer.
2. bf6d7f6 changes the physics guard of `_w8` from `decision == 'CARVE'` to "both carved by the waiver route". It also
   adds `out['misses'] = m`, the same list object, so a no-op. No threshold changed, and the w8 / w8b outcome is the
   same cap miss.

## Non-blocking findings

**N1 The ep24 CARVE rests on F-I4.15.3's choice to measure D from the polygon edge [M, R].**
- From the records: D sum 134.11 mm against W_x 128.23 mm (difference 5.88). With the rectangle-edge depths (77.55 +
  66.56 = 144.11 mm), the difference is **15.88 mm > 10 mm**, which gives `interlock_slot_inconsistent` and a PUSH.
- I read this as compliant with the decision:
  - decision (3) keeps "depth F-I4.3", and F-I4.3 measures depth from the body's entry edge;
  - under decision (1) the body is the polygon;
  - the slot bottom b, and so the cut, is unchanged;
  - W_x is taken between polygon bodies, so a rectangle-edge D would mix two bodies;
  - the choice was pre-registered at 18:14 with its reason.
- It was chosen with the ep24 geometry known: the "~15 mm" [E] from the fi4b rectangles and the verify_slot_1 waists,
  more than the window. This is the fourth outcome-informed step in the F-I4 chain (F-I4.12, F-I4.14, F-I4.15 body,
  this reading). The orchestrator should see it stated as the condition the ep24 CARVE depends on. A fresh plate
  episode would test it.

**N2 ep23 is spent as a freeze check for any prism-count fix [H, integrity].**
- The (b) failure is narrow: 85 against a cap of 82.
- Its inputs are weak: t is borrowed from a wrong-board track, and the outline is partial (waist 108 / ends 74 mm).
- The [H] fixes (a coarser tolerance or a rectilinear fit) would now be chosen after seeing the ep23 and ep24 counts. A
  fix that brings ep23 to <= 82 would be tuned on the freeze check.
- A next dated entry should:
  - state its tolerance or fit from a generic argument, or from the synthetic w7 / w8 shapes, before running;
  - name an untouched public plate episode, or a pre-written synthetic family, as the new freeze condition (b).

**N3 Run order deviates from F-I4.15.6 / F-I4.15.7 [M].**
- The rule says T-I1 (step 2, including the full waiver-off suite) runs "before T-I11".
- What happened:
  - T-I1 was launched 18 s before T-I11, and the two ran in parallel;
  - the waiver-off suite ran 19:23-20:29, after fi4o finished (19:22);
  - ep23 ran in parallel with fi4o.
- The build log (18:38) gives the reason: the code was frozen. The rule also says synthetic misses do not stop the
  round, so no outcome could change. The w8 cap miss was already known from the probe before the fi4o launch, and
  nothing was changed.
- Not recorded as a deviation in the PREREG Outcomes bullet. Suggest one line there.

**N4 One test threshold is laxer than written [R].**
- F-I4.15.7 w8 says "keep-out 0.0 cm3". `w_checks` flags keep-out only above 0.3 cm3, the F-I4.10 w1 threshold.
- It decided nothing: w8 and w8b stopped at the cap before keep-out, and w9 is report-only for P3.
- Record it, or align it in the next test revision.

**N5 Code-identity records are imprecise in four places [M].**
1. PREREG Outcomes says "code 19c4309 for every run below". In fact:
   - the committed `slot2-ep23/ep23_fi415.json` is the 19:11 rerun, with code_identity 3053a78 and the cbed3cb
     `interlock.py`;
   - the first run's identity is 5865276; both outputs are identical apart from code, sec and png;
   - the waiver-off suite ran at 7402553, which includes cbed3cb;
   - the w8 rerun ran at 212d2a1 with the uncommitted harness fix.
2. The build summary says "launch_code shows the 19c4309 file hashes". In fact `report.json` `launch_code` names commit
   3484d8d, taken about 18:41. Its hashes match 19c4309 for the F-I4 files. For `collcarve.py` and `cavpieces.py` they
   are 3484d8d's versions, which are not used with `--waiver-fi5` off.
3. The delivered `r0/manifest.json` code block names 7402553 with the cbed3cb `interlock.py` hash. The producing
   process loaded 19c4309. This is in `build/I.md` (19:22) but not in INTERLOCK 20.11, which is the text the
   Embodiment session reads for the P1 hand-off. Delivered rounds are never overwritten, so a note in 20.11 is the fix.
   The two `r0/sources/*.npz` listed in the manifest are gitignored, as disclosed. A clone lacks them.
4. The build says WIP snapshot 6ed88f1 committed "an in-progress copy of platebody.py". In fact the F-I4.15
   `platebody.py` first entered git in **caefcb4** (18:29:11), and it is byte-identical to the version that ran.
   6ed88f1 carried only the 3-line `w_checks` guard.

**N6 Some diagnostic runs are not logged [M].**
- `<scratch>/fi415/` holds `t_geom.py` (18:24), `dbg_b.py` (18:35, the per-slab FREE breakdown behind the w8 B tilt
  finding), `t_hm.py` (18:36, the partition on L / U / plus / smooth-I shapes, after the w8 cap probe) and
  `probe_w7.py` (19:27). None appears in `build/I.md`.
- CLAUDE.md asks for every run. None changed code: the `platebody.py` hash has been fixed since 18:29:11.

**N7 Two informed constants bypass the guard's register [R].**
- `k_()` now registers only `generic` constants. `shapes_max` (165) and `part_vmax` (32) are `informed:F-I4.15.9`, and
  `guard.constant` would refuse them because they name no PREREG A.6 row.
- This follows `simpieces` / `simphys`. As a result the run manifest's constants list omits them; the cap shows in the
  decision records (`cap: 82`).
- Record only.

**N8 F-I5 interface [R].**
- At REV 15, `plate_info` runs the all-point estimator, which can turn a step-1/2 plate into "not plate-like"
  (`t_all_points_fail`).
- `collcarve.object_routes` uses `plate_info` for F-I5.4's `plate_like` route choice. So since 18:29 F-I4.15 reaches
  F-I5, although F-I4.15.5 says "no change to F-I5 here".
- No case seen: `t_all_points_fail` appears nowhere in the committed results. The collision-carve workflow should
  record it.

**N9 w6c's "sigma 3" cells change only the declared sigma [R].**
- In those cells the points keep their 1 mm noise, as in w6, and the all-point estimator does not use sigma. So the
  sigma axis tests only which reference plane is chosen; the readings are 9.73 / 9.70 mm.
- This is consistent with the w6 semantics, but w6c does not show robustness to 3 mm point noise. Do not cite it as
  that.

## Cost

The build claims $0, all CPU work on this container, and no box. I found no rental in the records. I did not query the
HF-store ledger. My checks ran on this container and read records only, apart from the 1-second `recount.py`. Cost $0.
