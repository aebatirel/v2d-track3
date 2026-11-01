# verify_slot_0: did the board-slot build follow the rules? (rule-compliance check, 31 Oct 2026)

Verifier: a separate agent in the board-slot workflow. It did not build this code; its job was to look for what is
wrong. Lens: **rule compliance**. Four questions:
1. Was F-I4 (and each later F-I4.x entry) pushed before the first run that used it?
2. Does the code do exactly what F-I4 says? The waiver should cover only plate-plate INSERTION pairs, every other gate
   should stay on, and the geometry should come from evidence, never from outcomes.
3. Was any ground truth read?
4. Do non-plate pairs behave exactly as before? (One control re-run.)

Code checked: HEAD `871f8b7`. The gmg files the runs used (`platebody.py`, `interlock.py`, `simphys.py`,
`simpieces.py`, `structure.py`, `tools/interlock_dev.py`) are byte-identical to `9ad1af9` (sha256 compared).
Labels: [M] measured or read from a file or log; [E] estimate; [H] hypothesis.

## Answer to the owner's question ("Did we manage to get the faster notch?")

**No.** No board slot (notch) was built, so none was physics-tested or delivered [M]. In both T-I11 runs on public
ep24 (dev, eval semantics) both boards stay PUSH:
- **Run 1** (`fi4evalsem`): the plate test found no plane pair on either board.
- **Run 2** (`fi4b`, after the post-hoc F-I4.14): both boards pass the plate test and the kept gates. The plate-body
  step (F-I4.2) then fails on both boards: rectangle fill 0.895 and 0.868 against a minimum of 0.9.

The builder stopped there and did not tune. I confirm that.

## Verdict

**No blocking rule violation found.**
- The pre-registration was pushed before every run that used it.
- The waiver code engages only for plate-plate INSERTION pairs. The kept gates are re-checked.
- No ground-truth input was read.
- A real non-plate INSERTION control (ep11 cups) gives identical decisions with the waiver on and off [M, this check].

There are 10 non-blocking findings (section 6). Three of them should be settled before any further F-I4 entry (an
"F-I4.15") is used to build a slot:
- **N1**: F-I4.14's own pre-registered falsifier fired, and the report does not say so.
- **N2**: F-I4.14 widens the waiver's plate-like scope beyond "the test the code already has". Board 2 is now
  plate-like with an unmeasured thickness.
- **N3**: the P3 overlap clause was switched on for every pair, not only for waiver pairs.

## 1. Timeline: pre-registration vs runs [M]

Push times come from the reflog of `refs/remotes/origin/claude/bold-albattani-6qmxsv`. Run times come from the first
and last lines of the driver logs and from file times in the scratchpad.

| Step | Commit, push (UTC) | First use (UTC) | Order |
|---|---|---|---|
| F-I4 + INTERLOCK 20 | `c13f53c`, committed 16:18:55, pushed 16:18:58 | first synthetic probe 16:26-16:32 (`probe_w.py`, file time 16:30:54) | OK |
| F-I4.12 (post hoc, slot centre) | `94eed1c`, 16:35:26 / 16:35:29 | probe log `probe_w10_fi412.log` 16:37:40; T-I1 w1-w5 16:38-16:50; T-I11 16:51 | OK |
| F-I4 build code | first committed inside another agent's WIP snapshot `a03affc` (16:37:06); then `1756947` 16:50:33, `cd2383f` 16:50:58 / 16:51:00 | T-I11 `fi4evalsem` started 16:51:14 (driver log), ended 16:58:48 | OK |
| GT-free diagnosis of `no_plane_pair` | not a rule | `diag_plane.py` 17:00:49, JSON 17:03:00 | before F-I4.14, as stated |
| F-I4.14 (post hoc, plate test) | `dad65a1`, 17:06:51 / 17:06:53 | w6/w7 tests `test_w67.json` 17:10:39; w6b/w7 17:14:18 | OK |
| F-I4.14 code | `platebody.py` first committed inside another agent's WIP `0358fa2` (17:08:59); tests in `3462278` / `da9296e`; `9ad1af9` 17:14:55 / 17:14:57 | T-I11 `fi4b` started 17:15:14, ended 17:30:27 | OK |
| w6 miss on record | I.md entry pushed in `3462278` (17:12:43) | before `fi4b` | OK |

Code identity of the runs [M]: the r0 manifest sha256 of each gmg code file matches `cd2383f` for `fi4evalsem` and
`9ad1af9` for `fi4b`. The `commit` field in both manifests names a different commit: `5ae9361` and `42ab815`, other
agents' commits that were HEAD when the manifest was written. No gmg `.py` file differs between those commits and the
code commits (`git diff --name-only`).

## 2. Does the code apply F-I4 exactly? [M, code read; line numbers at HEAD]

- **Off by default.** `decide_pair(..., waiver_fi4=False)`, driver `--waiver-fi4` (store_true), and
  `carve_from_intrusions(waiver_fi4=False)`. The hook is the last statement of `decide_pair` (`interlock.py:1420`), so
  every F-I1..F-I3 decision is made first.
- **Scope** (`platebody.py:576`): both targets are plate-like AND both linked components come from INSERTION runs. An
  out-of-scope pair only gets the info block `waiver_fi4` attached; its decision, tier, flags and solids are untouched.
- **Kept gates, re-checked in `_pair`:**
  - track/identity gate (`:598`);
  - F-I1.3 step 1, TRANSIENT or fewer than 3 voxels (`:606`);
  - sweep share of R's OBSERVED voxels, at least 50 % (`:614`);
  - not pushable: median rigid push over the build frames in which R is entered must exceed 10 mm, or a validated
    `pushed_residual_m` decides (`:616`, the same code as `decide_component`);
  - plate body (`:623`);
  - cross-lap consistency within 10 mm, which PUSHES on failure (`:651`);
  - budget (iv) and topology on the analytic slot, which PUSH on failure (`:660`);
  - the linked pair carves both or neither (pair loop);
  - persistence (components are built only from voxels with n_v >= max(5, ceil(0.25 N_build)), `interlock.regions`).
- **Downstream of the decision** (`tools/interlock_dev.py` `run_waiver`): the pieces keep-out gate, P2-P7 acceptance,
  and `DO_NOT_USE.json` when any test other than P1 fails.
- **Waived, as F-I4.0 says, and only for in-scope pairs:**
  - the class-O step (more than 25 % of R is class O);
  - step 4 (iii) (at least 75 % SIL or GAP);
  - the F-I3.12 column rule;
  - "class-O voxels are never carved";
  - the silhouette.

  The analytic slot ignores the voxel classes, and `interlock_disagree` stays as a flag on a T1 record, as F-I4.0
  allows.
- **Geometry source:**
  - thickness and mid plane: our owned points within 6 mm of our pick (`plate_info`);
  - body: the observed outline (`plate_body`);
  - slot centre: the partner's mid plane at the median assembled relative pose from our tracks (`slot_for`, F-I4.12);
  - depth: the 99th percentile of the partner evidence samples that entered R, capped at the shared split plane;
  - width: t_p + 2 mm.

  None of these reads a physics, slot or score outcome.
- **F-I4.14 as written:**
  - step order: plane pair, then camera-side pair, then one-face plate;
  - reference plane = `planes[0]`, which `segment_planes` returns largest first and `_planes` orients to its cameras;
  - each face needs at least 300 points from at least 3 frames;
  - the six checks (i)-(vi) use the existing constants (`plane_deg` 30, `slab` 3-25 mm, `pair_overlap` 0.5, `band`
    3 sigma, extents at least 2(t + 2 mm));
  - one-face plate: 1-99 % extent along a of at most 25 mm. Its t is taken from the partner only when the partner's t
    comes from step 1 or step 2 (`resolve_one_face`). Its mid plane is the seen face moved t/2 away from the cameras.

  No threshold was changed.
- **Deviations from the text:** N3, N6 and N7 below.

## 3. Ground truth: none read [M]

- **Grep.** I searched `platebody.py`, `interlock.py`, `simphys.py`, `simpieces.py`, `structure.py`,
  `tools/interlock_dev.py`, `build/I/fi4_png.py` and the two diagnosis scripts for: parquet, mocap, `_align`,
  `library_v`, `/scan`, `ev25`, `observation.objects`. There is no read of a ground-truth source:
  - the only `mocap` hits are MuJoCo mocap bodies in `simphys.py`;
  - `interlock.py` names the dataset parquets and scans only in its refusal list (`chain_path_reason`).
- **Run inputs** (guard manifests of `fi4evalsem`, `fi4b` and my control; hook installed, 0 blocked, 0 refusals):
  - `calib.json` (P0) and `ep24_a.mp4` / `ep11_a.mp4` (P0);
  - `data/sweep/ep*/poses.npz` (tracks, P1);
  - our hands file (DEV);
  - the clean B4 bundle `20261031-b4ext4-b61e8aa` (`episode.json` plus per-object npz, DEV).

  No `--gen` was passed, as F-I4.9 requires. No `meshes/carve/ev25` or library file was read.
- **Candidate meshes.** The pick meshes (`cand/public/ep24/*/shell_t5p36.glb`) are loaded with `trimesh` outside the
  guard, so the run manifests do not list them. Their own manifest (`manifest_cands_ep24.json`) shows they were built
  from the same clean bundle, the tracks and `dev_constants.json`, with 0 refusals.
- **Inherited caveat, not new here.** The guard classes the tracks as P1, "Phase-1 tracks (library-templated)". The
  slot centre and depth depend on these poses. This is the accepted SPEC tiering: library shape is not used as shape
  evidence.
- **Diagnosis scripts.** `diag14/diag_plane.py` and `diag15/diag_outline.py` read only the bundle and the pick. Neither
  reads a slot or physics output.

## 4. Control re-run: a non-plate INSERTION pair, waiver off vs on [M, this check]

Why ep11 cups: it is the only real control that is an **INSERTION** pair (f42-136, travel 190 mm, straightness 0.91 /
0.92). Only the plate test stands between it and the waiver. ep2 pot + lid is a SEAT and is out of scope by run kind.

Setup:
- `<scratch>/verify_slot0/ctl_off_on.py` wraps the unchanged driver. It calls `decide_pair` twice on the same sides in
  one process: first with `waiver_fi4=False`, then with `True`, resetting `carved_now_cm3` in between. It compares
  every public record except the `waiver_fi4` info block.
- Inputs: the clean ep11 bundle, shell picks, video and hands, eval semantics, no `--gen`, `--no-physics
  --no-physcheck`.
- Code: HEAD `871f8b7`, gmg files identical to `9ad1af9`. Machine: this container, 4 shared cores, nice 10.
- Time: 127 s, 17:41:15-17:43:22 UTC.
- Outputs:
  - `<run>/interlock/public/ep11-verify0ctl/`, where `<run>` =
    `<scratch>/gmg/runs-dev/20261031-i2probe-626ce13`;
  - `<scratch>/verify_slot0/ctl_ep11.json` and `ctl_ep11.log`.

Command:

```
cd docs/research/mesh-2026-10-26 && GMG_MODE=dev GMG_RUN=<run> nice -n 10 <scratch>/venv/bin/python
  <scratch>/verify_slot0/ctl_off_on.py <scratch>/verify_slot0/ctl_ep11.json --run <run> --ep 11
  --bundle <scratch>/gmg/runs/20261031-b4ext4-b61e8aa/bundle/public/ep11 --cands <run>/cand/public/ep11
  --pick blue_cup=shell_t5p36,beige_cup=shell_t5p36 --video <scratch>/data/store/ep11_a.mp4
  --calib <scratch>/data/calib.json --hands <run>/in/hands11/hands.npz --proxy-copies 16 --identity eval
  --waiver-fi4 --no-physics --no-physcheck --tag verify0ctl
```

Result:
- **All 6 records are identical** between waiver off and on:
  - blue cup: PUSH T0 (`interlock_disagree`, `interlock_push`), IGNORE, IGNORE;
  - beige cup: PUSH T0, IGNORE, and the 3-voxel U CARVE T1 (`interlock_disagree`).
- Both cups are out of scope (`not plate-like: blue_cup, beige_cup`). F-I4.1: no plane pair. F-I4.14 step 2: the slab
  is seen from one side only (9,440 / 10,267 points, 69 frames, 0 from the other side). Step 3 fails its thin-extent
  check: 1-99 % extent along a is **29.67 / 29.84 mm** against at most 25 mm. Step 3 would also need a partner with a
  measured thickness, which a cup does not have.
- This answers P39 for ep11: decisions unchanged, no carve under the waiver.
- The synthetic w2 (waiver off) and w3 (n2, n4, n9, the 30 mm cylinder) passed in the builder's re-run on code
  `9ad1af9` (`results/slot-ep24/tests/test_waiver.log`) [M, their log, not re-run].

## 5. What I confirm from the build report [M]

- Run 1 (`fi4evalsem`, 454.6 s): `no_plane_pair` on both boards. sigma 3.0 / 0.74 mm; 36,675 / 22,304 downsampled
  points. Decisions: board 1 PUSH T0 (U 2 / O 65); board 2 PUSH T0 with `interlock_disagree` (U 41 / O 77).
- Run 2 (`fi4b`, 914.4 s), board 1: plate by step 2, t = 6.212 mm (faces +4.19 / -2.02 mm, overlap 0.968, 1.3 deg,
  rms 2.49 / 1.66 mm, extents 215.9 x 121.2 mm).
- Run 2, board 2: plate by step 3. 22,304 points all from one side, 119 frames, 1-99 % extent 14.77 mm, t := 6.212 mm
  (`plate_t_partner_prior`).
- Run 2, scope and kept gates: in scope; sweep 1.0 / 1.0; push 19.0 / 22.0 mm (not reused, computed in the waiver
  branch).
- Run 2, plate body: fill 0.895 / 0.868; rectangles 234.5 x 142.3 / 231.1 x 142.0 mm. The fallback to the old decision
  is applied correctly (no `push=True` for this gate).
- Diagnosis `diag15`: 2-98 % filled extents 220 x 124 / 216 x 124 mm; full extents 234 x 142 / 230 x 142 mm.
- Both r0 folders carry `DO_NOT_USE.json` (rule F-I3.8: ours 0.72 / 2.0 cm3, CoACD 52.9 / 77.3 cm3 per hull). Their
  manifests have no `owner_waiver` block, so nothing was offered under F-I4.

## 6. Findings

### Blocking
None.

### Non-blocking (most important first)

**N1. F-I4.14's own falsifier fired, and the outcome text does not say so.**
- F-I4.14 says: "[H] Falsified if w6 does not recover t within 1 mm".
- w6 read **8.07 / 8.39 mm for a true 10 mm** (1.6-1.9 mm off). The builder relabelled it `expectedFailure` and ran
  `fi4b`. The miss was in the pushed I.md before the run, so it was reported in time.
- The PREREG outcomes still call it only "w6 misses (expected failure)". They do not state that a pre-registered
  falsifier fired.
- w6 also never tested what it was written for. The synthetic faces did not merge, so step 2 was not reached. On real
  data, step 2 has been exercised only by board 1. Its synthetic check (w6b) was added after the miss; it reads
  0.2-0.9 mm thin and fails one cell.
- The w6 number is a finding in its own right [M]: the unchanged step 1 reads up to about 2 mm thin at sigma 3 mm.
  That would give a slot narrower than its partner for any plate that enters by step 1 with a large sigma [H].
- Fix: one sentence in the F-I4.14 outcomes, plus a w6 fixture that really merges the faces (for example t = 6 mm at
  sigma 3).

**N2. The waiver's plate-like scope was widened by the builder (F-I4.14 step 3), and board 2's thickness is not
measured.**
- The orchestrator's scope said plate-like "by the structure/thin-extent test the code already has". Steps 2 and 3 are
  new tests, written post hoc after the boards failed the old one.
- By step 3, board 2 is plate-like from one face plus a 25 mm thin-extent test. Its t, and so the width of the slot cut
  in board 1, is the partner's t (the same-stock prior [E]).
- It is labelled post hoc and [E], and the owner's later extension to every colliding pair (F-I5, pushed 17:34) covers
  the intent. Even so, no owner or orchestrator line accepts the widened F-I4 scope itself.
- Fix: before an F-I4.15 is allowed to carve, the orchestrator should acknowledge it in writing. A note in the
  F-I5-era scope would do.

**N3. The P3 overlap clause was switched on for every pair, not only for waiver pairs.**
- `simphys.pair_physics` now always calls `p3_pass(res, overlap_cm3=...)` (`simphys.py:405`, first committed in
  `a03affc`).
- So with `--waiver-fi4` off, P3 for every carved, OFFSET or DIAG pair (cups, pot/lid, the Embodiment path through
  `interlock.default_physics`) now also needs less than 1.0 cm3 overlap at the assembled frames.
- This contradicts "new code paths only, the F-I3 behaviour stays the default" (F-I4 header, INTERLOCK 20.6) and
  "with the flag off nothing changes".
- It restores an F-I1.8 clause, so it moves toward the pre-registration. No delivered or accepted result changes.
  The earlier carved-physics results are DIAG counterfactuals, computed before the change and never delivered. For
  example, the ep24 DIAG had overlap 0.76 cm3 and already failed P3 on rotation.
- Fix: one DEVIATIONS line or dated F note that says the restoration is global.

**N4. Pre-registered predictions are not reported as such.**
- INTERLOCK 20.6 item 4 asks for "P35-P38 as written ... failures included". The status is:
  - **P35 failed** (run 1, its own falsifier "no plane pair on either board");
  - **P36 failed** (F-I4.2);
  - **P37 and P38 not tested**.
- Only P36 is named as failed (I.md).
- P40 "holds" is not independent evidence. It was written after `diag14` had measured the two faces about 7.0 mm apart
  by the same camera-side split.

**N5. Each new F-I4 step so far has made the route more permissive after an outcome.**
- F-I4.12 changed the centre after a w1 miss. F-I4.14 changed the plate test after `no_plane_pair`.
- The builder's [H] for the next step, "the rectangle of the 2-98 % outline", was proposed after seeing fill
  0.895 / 0.868 against 0.9.
- Each is labelled post hoc, which the rules allow. The forking path should still be stated plainly in any F-I4.15
  [H]. A body change would best be checked on another public plate episode (ep23 boards, dev) before it is applied to
  ep24, and frozen before eval 25.

**N6. The pre-registered "existing suite with the waiver off" was not re-run in full after the shared-file edits.**
- INTERLOCK 20.6 step 1 asks for it.
- After the edits to `interlock.py`, `simphys.py` and `simpieces.py`, only the Controls and Waiver classes were re-run
  (14 tests).
- Not re-run: Sweep, Silhouette, Offset, Sources, Partner, Pieces, Agreement, Contract, Iteration, PiecesGate.
- Risk is low [E]: those tests use stub or no physics, and w2 covers the decisions.

**N7. A waiver CARVE does not reset `submitted`.**
- In the CARVE branch (`platebody.py:663-680`), the tier is set to T1, but `submitted` and `_sub_solid` from an earlier
  F-I3 T2/T3 CARVE would survive.
- A record could then read tier T1 with `submitted` True, against the F-I3 rule that submitted means T2, T3 or T2o.
- Not exercised: every in-scope F-I3 decision so far is PUSH.

**N8. Traceability of the code.**
- The F-I4 and F-I4.14 code reached git through other agents' WIP snapshots: `a03affc` "work log: C0b ...",
  `0358fa2` "work log: C1 results ...", and `3462278` / `da9296e`.
- The commit titled "F-I4.14 build" (`9ad1af9`) holds only I.md and a two-line driver change.
- The manifests stamp the HEAD at write time, not the code that was loaded. The sha256 code identity is correct.
- Fix: record the commit at process start, and commit your own code paths under your own message.

**N9. One guessed time is still in the text.**
- The F-I4 header says "Written 16:03-16:25 UTC". The commit was at 16:18:55.
- The order is unaffected: everything was pushed before any code existed.

**N10. Robustness notes on step 3 [H, from the w7 fixture and the control].**
- A real one-face plate whose edge points are seen from the other side by at least 300 points from at least 3 frames
  becomes "two-sided" and fails the checks. The first w7 fixture showed exactly this.
- The cups failed the step-3 thin-extent check by about 5 mm (29.7 / 29.8 against 25 mm). The second guard, that the
  partner's t must be measured, is what keeps a cup out when its partner is a measured plate.

## 7. Cost

- Verification compute: one 127 s CPU run on this container, plus reads.
- No Vast box, no spend, no ledger line.
- Files written outside git:
  - `<scratch>/verify_slot0/` (script, JSON, log);
  - `<run>/interlock/public/ep11-verify0ctl/` (new tag; no existing run was touched).
