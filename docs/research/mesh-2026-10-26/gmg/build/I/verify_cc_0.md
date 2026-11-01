# verify_cc_0: rule-compliance check of the T-I13 public collision-carve runs (PREREG F-I5, F-I5.14)

Verifier, rule-compliance lens. Written 31 Oct 2026, 21:00-21:25 UTC. Read-only: no run, no code change, nothing
uploaded. Object checked: the public-runs step summarised at head `124fc86` (20:58 UTC) on
`claude/bold-albattani-6qmxsv`, its records (`PREREG.md` F-I5 to F-I5.14 with outcomes, `INTERLOCK.md` 21.10-21.11,
`build/I.md`, `build/I/results/collcarve-public/`) and the scratch run `runs-dev/20261031-fi5pub-3053a78`.
Labels: [M] measured here (hashes, git and reflog times, JSON fields), [R] read from code or documents, [E] estimate,
[U] not verified.

## Verdict in plain words

**No blocking finding.** The entries were pushed before the runs that use them. The code that ran is byte-identical
to `1b9f0c1`. The inputs are our own (no scan, mocap, parquet pose or `*_align`). Nothing was changed after an
outcome. No out-of-scope pair was carved or relabelled. The summary's numbers match the records.

There are 13 nonblocking findings. Three should be fixed before the next F-I5 delivery:
- **N1.** The five round folders that the report says "must not be used" carry no do-not-use marker.
- **N2.** No F-I5 round folder has the `sources/` folder that F-I5.6 lists.
- **N3.** The carved receiver skips routes 2 and 3 of the piece ladder. The as-built record does not mention this.

Two record fields can mislead whoever reads the decisions (N4):
- `decision_f_i3` is not the flag-off decision. On ep11 it says CARVE where the flag-off rule says PUSH.
- One log line misstates ep2's flag-off decisions.

The "GT-free" claim needs a dev-tier qualifier (N7). The cups' SHELL walls use the dev thickness t0_dev, which was
fitted on library_v3-ROI crops. PREREG A.1 allows this in dev runs, but eval runs may not use it.

## Blocking findings

None.

## Nonblocking findings (most important first)

**N1. The round folders declared unusable carry no do-not-use marker.**
- [M] In each of the five folders `sim/public/ep{11,12,13,31,2}-fi5/r0/manifest.json` has `do_not_use: null` and
  `p1_pending: true`, and there is no `DO_NOT_USE.json`.
- The project already has this marker. The i2probe ep24 folders (`ep24-fi4b/r0`, `ep24-evalsem/r0`) carry one under
  F-I3.8.
- Under the rule (F-I5.4 / F-I5.6) these folders are deliverable, because 6 mm boxes pass the keep-out gate. "Must not
  be used" is the author's post-hoc judgement, based on diagnostic F-I5.14 (7), and (7) "decides nothing".
- Yet the outcomes bullet ("the round folders must not be used") and INTERLOCK 21.11 read like a decision.
- Risk: anyone given the scratch path, for example the Embodiment session, sees a valid round with `p1_pending`.
  Only P1 (the FlashCHORD settle) would stop it.
- Fix:
  - Add a labelled post-hoc marker file to the five folders, for example `NOT_FOR_USE_posthoc.json`. It names F-I5.14 (7)
    and INTERLOCK 21.11 item 2 and does not claim a rule. Adding a file overwrites nothing.
  - Word the outcome as "recommended not for use until 21.11 item 2 is decided".

**N2. `sources/` is missing from every F-I5 round folder.**
- [R] F-I5.6 lists `sources/` in the round folder. F-I3.1 requires round 0 to carry sources (a), (b) and the observed
  notches, because `carve_from_intrusions` reads them. That is the Embodiment path behind the owner's 30 Oct request.
- [R] Why they are missing:
  - `--waiver-fi5` sets `a.no_physics = True` (`tools/interlock_dev.py` line 114).
  - That skips the flag-off branch, which is the only caller of `IL.write_sources` (line 387).
  - `collcarve.deliver` writes no sources.
- [M] The five folders hold only `_default`, `_fit`, the objects, `manifest.json`, `props_gmg.json` and, for ep11,
  `_carved_failed`.
- The gap is not in F-I5.11 and not in the report.
- Effect today: none [E]. There is no `--video` or `--gen`, so (a) and (b) would be empty; only the notches are
  missing, and no decision changed.
- Fix: write the sources in `collcarve.deliver`, and list the gap as an as-built deviation.

**N3. The carved receiver skips part of the piece ladder; the as-built record does not mention it.**
- [R] F-I5.4 applies the ladder to the "default and carved" sets: the first route that applies and passes the gate.
- [R] `FI5._carve`, boolean path (`collcarve.py` line 396), calls `CP.route_pieces(..., skip=('2',) + (('3',) if
  ob['route'] == '4_voxels' else ()))`:
  - a receiver whose default did not take the lathe route never gets the profile-space lathe carve;
  - a receiver whose default fell to route 4 also skips CoACD.
- [M] ep11's carved beige cup went straight to 6 mm boxes (`carve.ladder` = `4_voxels` only), although its lathe test
  passed (rotc 2.60 sigma).
- This is not among F-I5.11 (1)-(5).
- Effect on the outcome [E, not measured]: probably none.
  - The uncarved lathe set and the CoACD set had already failed the gate (16 and 29 hulls over 0.3 cm3).
  - A carve only adds keep-out, at weight 10.
- Fix: a dated post-hoc as-built note, F-I5.11 (6).

**N4. `decision_f_i3` is not the flag-off decision, and two records state the flag-off decision wrongly.**
- [R] `FI5.apply` copies the F-I1..F-I3 logic's verdict on the components built from collider intrusions
  (`collcarve.py` line 672) and reports it as `decision_f_i3` and `report.decision_f_i3_same_sides`.
- F-I5.7 (iv) asks for "the F-I1 to F-I3 decision the same pair gets with the flag off". That is the evidence-based
  path in `decisions.json`.
- [M] They differ on the one in-scope pair:
  - ep11: `decision_f_i3_same_sides` = {beige_cup<-blue_cup: CARVE, tier T1};
  - the flag-off decisions are PUSH for the 2165- and 1848-voxel nest components ("more than 25 % of R is class O
    (seen solid): the pose is wrong, not the shape", `push_list.json`).
- [M] `I.md` 20:35 says ep2's "F-I1..F-I3 decisions stand (pot IGNORE, lid PUSH)". The flag-off decisions are:
  - pot PUSH for the 916, 630, 10 and 3-voxel components, IGNORE only for a 2-voxel one;
  - lid PUSH.
- The README's per-pair table has no flag-off column. Only `decisions.json` and two log lines (ep13, ep31) carry the
  F-I5.7 (iv) report.
- Latent issue for "non-carved pairs unchanged":
  - F-I5.2 says a component that fails a gate "keeps its F-I1 to F-I3 decision".
  - The code keeps the label but drops `_sim_solid` and sets `sim_carve` False for every component of the pair
    (`collcarve.py` line 680 ff.).
  - So a failing component whose collider-logic verdict was CARVE would read CARVE / T1 with nothing carved.
  - [M] No out-of-scope component had CARVE in these runs (ep12, ep2: PUSH / IGNORE; ep13, ep31: no component), so
    nothing changed.
- Fix:
  - Rename the field, for example `decision_f_i3_logic_on_colliders`.
  - Add the flag-off decision per pair to the README / 21.11: ep11 PUSH (class O); ep2 PUSH; ep12 PUSH; ep13 IGNORE
    (`c_absent_track`, good share 0.38 / 0.40); ep31 IGNORE (`one_sided_region`).
  - Correct the 20:35 line.

**N5. Two more parts of F-I5.7 are not built as written; the outcomes name only the rigid-shift scope gap.**
- (iii): "the shift goes to the push list for the tracker" is not implemented.
  - [M] `push_list.json` is the flag-off list.
  - [R] FI5 writes only `push_list_fi5` with the overshoot frames.
  - Here the shift is 0 mm, so nothing is lost.
- (ii): one-sidedness "for lathe receivers" comes back `null` whenever the receiver's lathe route failed, even when the
  structure test accepted the lathe (ep11 beige, 2.60 sigma).
  - [R] `_one_sided` needs `ob['lathe']`, line 522.
  - The README does not say why it is null, although one-sidedness is the eval-10 measurement that motivated F-I5.
- Fix: as-built note; with box colliders the numbers would say nothing anyway.

**N6. The public-semantics decision of F-I5.0 is not reported.**
- [R] F-I5.0: "Public runs ... use eval semantics ...; the public-semantics decision is also reported." F-I5.8 lists
  identity flags as an input.
- [M] The v6 bundles have no identity / B.2a output. The v4 run `20261031-b4ext4-b61e8aa` has `identity/` and
  `manifests/identity.json`.
- F-I5.14 (1) records the choice of v6 before the runs, so the choice complies.
- What is missing is one sentence: on these inputs public and eval semantics give the same decision, because no
  IDENTITY_SWAP flag exists.
- [E] On the earlier bundles ep11's blue cup was IDENTITY_SWAP on public (F-I5.0). With that flag, public semantics
  would remove the only in-scope pair.
- Fix: one line in the README and in the F-I5.14 outcomes.

**N7. "GT-free" needs a dev-tier qualifier.**
- [R] Every F-I5 body is `shell_t5p36`, the SHELL candidate at t0_dev = 5.36 mm.
  - `dev_constants.json`: "fitted: own t0_dev (PREREG A.1 statistic on obs_all)".
  - `obs_all` is "library_v3 ROI and --others" (PREREG, labels paragraph).
- PREREG A.1 allows t0_dev in dev runs only. These runs are dev (`run_tier.json`: mode dev, tier DEV), so they comply.
- But F-I5.8's "no ... library_v1..v4 geometry" reads stricter than this, and the summary says only "GT-free".
- [R] STATUS (C0 entry) calls our fitted tracks "library_v3-anchored". The guard admits `data/sweep/ep*/poses.npz` as
  role tracks, tier P1. That provenance is shared by every gmg interlock run and was not introduced here.
- Two consequences:
  1. The eval twins (P49) must use the clean t0, not t0_dev (A.1).
  2. A physical point for 21.11 item 1 [R, dev statistics]: the same file gives per-object medians of 1.5 mm (beige
     cup) and 1.6 mm (blue cup) against the pooled 5.36 mm used for their SHELL walls. That bears on how much a
     6 mm box grid can keep. Handed to the physics lens and the owner; not a finding about this run.

**N8. Four predictions are scored a little generously or without a label.**
- **P42 ("holds, trivially")** is about "the default lathe colliders". Neither cup got lathe colliders (both route 4),
  so P42 is **not tested as stated**, rather than held.
- **P44.**
  - As written it holds: c = 1.0 mm is the stated alternative "unless the guest's base lies in the pocket (then 1.0
    mm)", and the 20:17 log scored it that way.
  - The outcomes re-score it "void" after the fact. The reason is right [M, geometry]: for any set of axis-aligned
    boxes, some face has max(0, n.g) >= 1/sqrt(3), so c = min(1 mm, 0.5 x 4 mm x sigma_sup) = 1 mm whatever the cup.
  - The re-scoring should be labelled post hoc.
- **P47** is falsified only through diagnostic (7), S on the delivered pieces. The rule runs neither S nor P2 for the
  out-of-scope ep31 pair. The README says so in brackets; the PREREG outcomes line should too.
- **P45** is correctly falsified by the lid's route. Its S / P2 clause was not reached in the rule.

**N9. The code-identity records are slightly misdescribed.**
- [R] `launch_code` in `report.json` is computed after the bundle, candidates and evidence are loaded
  (`interlock_dev.py` line 143), not at launch.
- [M] Launch times and HEAD:
  - ep13 and ep31 launched at 19:29:48, ep11 at 19:30:28, all at HEAD `cdc8b40` (their `.launch` files);
  - their `report.json` says `407a18e`, which was committed at 19:30:44.
- [M] The round manifests' `code.commit` is `3926430`, the HEAD at delivery.
- So the summary's "launch_code ... records HEAD at launch" is not accurate.
- No effect: the sha256 of every module (29 in each `.launch`, 10 in each `report.json`) equals the blob at `1b9f0c1`,
  `dirty` is false, and no gmg code differs between `1b9f0c1` and `124fc86` except `tests/test_fi415.py` [M].

**N10. Some steps ran just before the entry that governs them was pushed; no outcome existed yet.**
- [M] The dev run folder was created and the hands copied at 19:15:26 (`run_tier.json`, `in/SOURCES.txt`), and the
  candidate builds ran 19:15-19:32. F-I5.14 reached origin at 19:17:17. No F-I5 code ran before the push, and the
  producers were unchanged.
- The first, buggy version of `fi5_default_sink.py` was run at a time that is not logged. Its fix is logged at
  20:30:57; (7) reached origin at 20:30:13; every output file dates from 20:31:09 or later [M]. That first run produced
  no S number.
- Advisory: log the launch time of diagnostics too.

**N11. A kept gate that decided two pairs is not in the decision list.**
- The moves-through sweep share put ep12 and ep2 out of scope (0.0 on both sides) [M].
- F-I5.2 keeps it in writing, and F-I5 was pushed before the runs, so the runs comply.
- But the 17:30 orchestrator note lists only persistence and the acceptance tests (keep-out, hands-off sink, free
  travel, replay drift, overlap), not this gate.
- INTERLOCK 21.11's decision list names the caps (through 21.10 item 4) but not this gate.
- With today's near-empty colliders it is moot (overlap 0.16-0.23 cm3) [M].
- After a pieces fix it will decide exactly the resting pairs (lid on pot, cup in rack): the owner's "if 2 mesh collide
  we can carve it" case.
- Fix: add "sweep gate for SEAT pairs" to 21.11's list.

**N12. Small record items.**
- F-I5.0 says every record in scope carries `owner_waiver_fi5` and tier T1. The guest's two records in the in-scope ep11
  pair are tier T0 with no `owner_waiver_fi5` flag; they carry a `waiver_fi5` role block [M].
- The manifest's `owner_waiver_fi5` block quotes only the 17:30 quote, while F-I5.6 says "the quotes".
- The default's per-copy S rows are dropped (`_accept` strips `per_copy` from the default). F-I5.5 says "Per-copy dz,
  lateral and tilt are reported, and the default's".
- The ep11 volume cap passes at 0.0997 against 0.10 [M]. That margin is about 0.002 cm3, under one cell of the
  200,000-point grid estimate (pitch about 1.5 mm) [E], so the cap verdict is within the estimate's resolution. The
  delivery would be the same (default) either way.
- The 20:08 log time, which was ahead of the clock, was corrected in a commit at 20:13 (1bd1392), not "right after"
  its own commit at 20:07 [M].

**N13. The proposed fixes need a review first.**
- The 21.11 proposals are labelled [H] with falsifiers. Those falsifiers are measured "on these 10 objects", the same
  public objects that motivated them. That is acceptable for public development, but:
  - CLAUDE.md asks for a focused review of evidence and open-source prior work before a fix is chosen;
  - the share threshold for any delivery floor (item 2) must be fixed before an eval twin runs.
- [R] Closest prior for item 1's handle bound: focused-pascal's `pipeline/lathe_collision.py` (`334393e`). It builds
  rings and base only, has no handle step, and has an opt-in `--base_from_hulls`.

## Confirmed

- **C1. Push order.**
  - F-I5 was committed as `d156571` at 17:34:08 and reached origin at 17:34:10, before any F-I5 code (first commit
    `fae78de`, 18:11). The F-I5.0-F-I5.10 text is unchanged since `6b16c2f` (block diff empty) [M].
  - F-I5.14 was committed as `1b9f0c1` at 19:17:15 and reached origin at 19:17:17 (reflog of the remote-tracking ref).
  - First T-I13 launch: 19:29:39 (ep12); last: 19:32:47 (ep2). The first F-I5 result line is at 19:44 [M].
  - F-I5.14 (7) reached origin at 20:30:13, before any diagnostic output (from 20:31:09). The ep2, ep31 and ep13
    outcomes (20:33-20:52) came after (7) [M].
  - Since 19:17 the F-I5.14 text has only had additions: the dated (7) and the outcomes bullet [M].
- **C2. Code that ran.**
  - The module sha256 in all five `.launch` records (29 files) and `report.json` records (10 files) equal the blobs at
    `1b9f0c1`; `dirty` is false [M].
  - The candidate manifests (commits `7402553`, `cdc8b40`, `407a18e`) differ from `1b9f0c1` in no gmg module [M].
  - `3053a78..1b9f0c1` adds only the `diag_sink` flag and its report-only branch [M].
  - That branch never fired: ep11 passed the caps and the other pairs were out of scope, and no `fi5.json` has
    `diag_S_rows` [M].
- **C3. Command and inputs as pre-registered.**
  - All five launch records carry `--waiver-fi5 --identity eval --proxy-copies 16 --no-physcheck --tag fi5`, with no
    `--video` [M].
  - Picks as stated. F-I5 body = `shell_t5p36` for all ten objects, the ep2 lid included [M].
  - Hands: the sha256 of the five copies equal the v6 M1 outputs [M].
  - Bundles: v6 clean (`run_tier` clean / P1); table plane from frame-0 depth RANSAC [M].
  - The report scripts (`fi5_*.py`) read only run outputs, candidates and the bundle [R].
  - No scan, mocap, parquet `pose`, `*_align` or library mesh is opened by these code paths [R]. The strace audit was
    not re-run [U].
- **C4. Gates and decision steps as written (ep11, the in-scope pair).**
  - Gates: persistence nmin 5 = max(5, ceil(0.25 x 11)); sweep share on OBSERVED voxels, U-only components = 1.0 (F-I1.3
    step 3); SEAT admitted (F-I5.2); the track gate under eval semantics (`interlock.py` line 1612) [R/M].
  - Receiver by containment: 0.617 against 0.401 (> 0.1) [M].
  - T_rest from 11 assembled hands-off frames; S frame 126 [M].
  - 7 overshoot frames (> 4 mm along d or g) not carved; 4 frames carved [M].
  - c = min(1.0, 0.5 x 4 x 0.999) = 1.0 mm [M].
  - Caps: 0.0997 <= 0.10; reach not applied to SEAT (as written); topology 14 / 14 [M].
  - The F-I5.5 tests use the F-I5.10 constants (`collcarve.K`). P3 is evaluated at the S frames [R].
  - S, P3 and P4 fail, so the default was delivered, as F-I5.5 requires [M].
- **C5. Piece ladder as written.**
  - CoACD runs with `max_convex_hull` = 82 = floor(165 / 2). The repair stops at the cap [M]: 0 splits on 9 objects,
    2 on the ep13 rack.
  - Route 4 keeps a coarse cell only when all its 2 mm cells are kept. All ten objects end at 6 mm with gate 0.0 [M].
  - Do-not-use is set only on a gate failure (F-I5.6).
  - So "the rule as written delivers these pieces" is correct.
- **C6. Non-carved pairs are unchanged in decision and delivery.**
  - Every out-of-scope component keeps `decision == decision_f_i3`, carries `waiver_gate_fail:<gate>`, and none is
    CARVE [M].
  - The flag-off decisions come from the unchanged F-I1..F-I3 path in the same process; F-I5.12 x10 (flag off: identical
    records) and the 20:29 waiver-off T-I1 suite exercise that path [R].
  - Nothing was carved in any delivered folder, and `submitted` is False on every record [M].
- **C7. Numbers in the summary match the records** [M].
  - Box shares 1.8-9.3 %; CoACD 82 hulls on 9 objects and 80 on the ep13 rack; 2-75 hulls over 0.3 cm3.
  - ep11 blue cup rotc 3.0126 sigma.
  - ep11 S: 31.56 mm / 42.4 deg carved, 80.47 mm / 67.9 deg default; P3 12.31 deg; P4 0.68 against 1.5 x 0.414 cm3.
  - Rigid shift 11 / 11 frames at 0 mm.
  - Delivered-pieces S: 126.8 / 8.2 (ep12), 90.6 (ep13), 84.2 / 86.7 (ep31), 84.8 / 88.0 (ep2) mm.
  - Overlap along the track 0.0-0.48 cm3.
- **C8. Other claims.**
  - Fixed run order, all launches within 3 min, frozen code: the order change (F-I5.14 (3)) cannot have changed an
    outcome [M].
  - No eval bundle exists under `runs/`, so the twins could not run [M].
  - No rental; the machine load is as recorded [M: uptime, logs].
  - The diagnostic's stride fix aligned it with the in-run rule (`interlock._static_stretches`, the same hands-off
    segmentation as `FI5._rest`), not a new threshold [M].

## Not checked

- Uploads to the HF store and the spend ledger: the claims "not uploaded" and "$0" were not checked [U].
- The strace audit of the v6 extract was not re-run [U].
- Physics numbers were not re-simulated. That is verify_cc_1's lens.
- The T-I12 / D2 synthetic step is outside this check.
