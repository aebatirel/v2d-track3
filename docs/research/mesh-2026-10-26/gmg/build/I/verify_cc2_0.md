# verify_cc2_0: collision carve round 2 (F-I5.15 / F-I5.16, as built F-I5.17), rule-compliance lens

Verifier, 1 Nov 2026, 01:55-02:30 UTC. I did not build or run this round. My job was to find what is wrong with it.
Lens: rule compliance. I checked:
- that F-I5.15 and F-I5.16 were pushed before any code ran with them (git push times);
- that the implementation is the written rule and uses its thresholds;
- that no ground truth was read;
- that nothing was tuned after outcomes;
- that the DO_NOT_USE markers exist;
- that the eval precheck decided nothing.

Scope:
- PREREG F-I5.15-F-I5.18; INTERLOCK 21.13-21.14; `build/I.md` "Collision carve round 2" (all lines to 02:06).
- Code at 88f49df: `cavpieces.py` (rev-2 section, `keepout`, `repair`, `gate`, `search_layout`, `route_pieces2`,
  `exact_share`), `collcarve.py` (`precheck`, `carvable_mesh`, `FI5R2.apply`, `floor_frames`, `floor_and_gate`), and
  `simpieces.props`.
- Results `build/I/results/collcarve2-public/` (T-I16; commits 4023e4f and 719e1a8) and
  `build/I/results/collcarve2-evalcheck/` (commit cea1342), with their scripts.
- The scratch round folders `<scratch>/gmg/runs-dev/20261101-fi5r2pub-88f49df/sim/public/ep*-fi5r2/r0` and
  `.../20261031-fi5pub-3053a78/sim/public/ep*-fi5/r0`.

Labels: [M] measured or read from records, [R] code or document reading, [E] estimate, [H] hypothesis.
- **What I ran (read-only, this container, $0, no box):**
  - the push times from the remote-tracking reflog;
  - sha256 of the gmg modules at 88f49df against the launch records;
  - `sha256sum -c` of the 47 T-I16 inputs in both run folders;
  - a recount of the delivered piece volumes from the scratch piece files (`<scratch>/v2c/vol.py`);
  - a search for F-I5 round folders without a marker;
  - a check for leftover negative-nice scheduler groups;
  - `ledger.py show`.
- **What I did not compute:** no physics, no CoACD, no new threshold.

## Answer

**One blocking item, for the eval precheck's relay; none for the public verdict.** The public outcome holds as stated
and as the rule requires: nothing was carved or delivered, and all five round folders are DO_NOT_USE.
- **Timing.** The rule entries were pushed before any code ran with them.
- **Code.** The code that ran is the frozen 88f49df, and no gmg code changed after any outcome.
- **Thresholds.** The thresholds in code are the written ones.
- **Markers.** They are present on all ten public folders.
- **Ground truth.** None was read.
- **Eval precheck.** It changed nothing.

**What is wrong** (details below):
- **B1, blocking for the eval relay.** The pre-registered validity check of the contact engine (T-I17 c1) was skipped
  on a false premise. The reason given in four places is that "the ep24 v6 bundle is not on this machine". Both ep24
  bundles are on this machine, and so are the c1 pieces. The only comparable record on the branch shows plain MuJoCo
  misranking these same pieces against MuJoCo-Warp. The eval precheck's headline (eval 10 overflows the training
  limits) rests on that unchecked engine.
- **N1, records.** Four record items that F-I5.15 (8) lists as fixed before any delivery are not implemented, and
  F-I5.17 does not say so:
  - no F-I5.7 shift for any pair, and so none on the push list for the pose lanes;
  - no `sources/`;
  - no `decision_flag_off`;
  - props_gmg.json is still grid-based, with volumes 1.5-1.9 x the exact union.
- **N2, the repair-gate mismatch (H-d).** This is a code defect against F-I5.4, not "a rule-level choice", and it
  confounds P76.
- **N3, the eval precheck's order and method.** The eval precheck ran before the public verification. Several of its
  method choices were made during the run, after eval-10's reference had been measured, and no dated entry records
  them. P103 is unaffected.
- **N4-N10.** Smaller deviations and report precision; see below.

## Timeline [M: remote-tracking reflog, commit times, launch records, build log]

| UTC | event |
|---|---|
| 22:02:26 | F-I5.15 pushed (f00e657; time fix 22c88fd 22:02:47) |
| 22:04-22:17 | Build step 1: no code edited (log 22:55; no gmg code commit between 1b9f0c1 and ced42fd) |
| 22:46:41 | F-I5.16 pushed (217aa1f; push log 04146fa 22:46:54) |
| ~23:08 | first round-2 code runs (smokes, uncommitted; log 23:08) |
| 23:13:10 | WIP code ced42fd pushed |
| 23:40:18 | T-I14 nest runs launched (cite ba3387d) |
| 23:40:33 | ba3387d pushed (committed 23:40:30) |
| 23:41:51 | F-I5.17 (as built) pushed |
| 00:12:49 / 00:13:26 | F-I5.18 / code 88f49df pushed |
| 00:14 | T-I16 step and eval precheck step both start |
| 00:18:23 | T-I16 launched on 88f49df (`drv<N>_fi5r2.launch`) |
| 00:32:36 | T-I16 launch record pushed (eafd88d) |
| 00:50 | first eval contact numbers (log) |
| 01:47:23 | eval precheck pushed (cea1342) |
| 01:53:07 / 02:05:09 | T-I16 results (4023e4f) / S diagnostic (719e1a8) pushed |

The F-I5.15 / F-I5.16 text at HEAD is identical to the pushed text at 04146fa [M, diff].

## Blocking

**B1. T-I17 c1 was skipped on a false premise. Until it runs, or until a comparable record is cited, the eval-10
overflow must not be relayed as an overflow of the evaluator's limits.**
- **The claim** appears in four places:
  - PREREG F-I5.17 (14): "c1 needs the ep24 v6 bundle, not on this machine";
  - F-I5.18 "Not run in this step";
  - `collcarve2-public/README.md`, last section;
  - `collcarve2-evalcheck/README.md` section 5.
- **The facts [M]:**
  - **v6 bundle:** `<scratch>/gmg/runs/20261031-b4ext6-90c8cce/bundle/public/ep24/` has `episode.json` and
    `wooden_piece_1/2.npz` (28 + 16 MB), written 31 Oct 17:24 UTC.
  - **v4 bundle:** `<scratch>/gmg/runs/20261031-b4ext4-b61e8aa/bundle/public/ep24/` was written 31 Oct 09:10-11:36
    UTC. This is the bundle the round-2 r0 `fi4o` was built from (PREREG F-I4.15 inputs). verify_slot3_0 re-gated ep24
    at f246 on this machine with it around midnight.
  - **The c1 pieces** (carved 57 / 77, `_default/` 50 / 71) are committed in `build/I/results/slot2-ep24/fi4o/r0/`.
    determined-wright's z shifts are quoted in F-I5.16 (1)(h).
  - So c1 was runnable here in minutes [E, F-I5.16 (6)(i)].
- **The rule.** F-I5.16 (6)(i): "T-I17 c1 runs here first ...; its verdict is logged before T-I15 / T-I16." F-I5.16
  (1)(h): if c1 fails, "G1 in plain MuJoCo is recorded as weaker than MuJoCo-Warp, and no F-I5 delivery is called
  usable before G1 has run in MuJoCo-Warp".
- **The evidence already on the branch** [R]: F-I4.17's gate validity on the same r0 (612f350, 23:17 UTC; INTERLOCK
  20.15 item 7, 3fce701):
  - plain MuJoCo gives the carved set 868 rows with 3 of 16 copies over 512, and the default 880 rows with 1 of 16
    over;
  - MuJoCo-Warp ranks them the other way (2,027 vs 416).
  - [H] If c1's scene (the f246 settle, determined-wright's 16 draws) behaves the same, c1 fails all three of its
    conditions: carved over in >= 15/16, default in none, ratio >= 3. Falsifier: run c1.
- **Effect:**
  - **T-I16:** none [M]. No scene was gated, and every folder is DO_NOT_USE on the share floor.
  - **Eval precheck:** P103 is defined in G1's engine, so "falsified on eval 10" stands as defined. But the item it
    asks the orchestrator to relay ("eval 10's packed ev10 pieces overflow under sim=rl", README section 6) would reach
    the pack lane as an evaluator-limit result. The engine behind it has not been validated, the reason given for not
    validating it is false, and the only comparable record shows that engine misranking piece sets.
- **To clear before the relay:**
  1. A dated correction of the four statements.
  2. Run c1 here, or cite F-I4.17's P125 after checking that the scene, options and draws are identical.
  3. Send the c1 verdict with the eval-10 numbers. If c1 fails, send eval 10 as "plain MuJoCo only: 656-1,296 rows
     in the pair scene", together with a request for a MuJoCo-Warp count (determined-wright's `budget.py` on the
     packed eval-10 reference, which F-I5.16 (3)(b) asks for anyway).

## Non-blocking

**N1. Four record fixes of F-I5.15 (8) (INTERLOCK 21.13.9, "records fixed before any delivery") are not implemented,
and F-I5.17 does not list them as deviations [M, R].**
- **(a) F-I5.7 for every pair, with the shift on the push list (V0 N5).** `FI5R2.apply` computes `_rigid_shift` only
  after a carve set exists (`collcarve.py`, the `rep['rigid_shift']` line after `_carve2`). The early returns for
  out-of-scope pairs and for `pose_impossible_all` skip it.
  - So none of the five T-I16 pairs has a shift, and `push_list_fi5r2.json` has none.
  - The floor-frame entries also carry no numbers; only ep11 f126, the acceptance frame, has them. The numbers are
    in `floor.json`.
  - The push list is this round's hand-off to the pose lanes, and F-I5.15 (3) puts "the F-I5.7 shift when computed"
    in it. Round 1's verifier had flagged the narrower gap (F-I5.14 outcomes, "runs only for in-scope pairs"). It is
    now wider.
- **(b) `sources/` (V0 N2).** It is absent from all five round-2 r0 folders (F-I5.6 lists it).
- **(c) `decision_flag_off` from `decisions.json` (V0 N4).** It is in no record. The rename
  `decision_f_i3_logic_on_colliders` is done.
- **(d) Exact volumes, centre of mass and inertia from the hulls (V1 N2).** props_gmg.json still comes from
  `simpieces.props`: samples on a boundary-inclusive 1.5 mm grid. Its `volume_cm3` is 1.5-1.9 x the exact union for
  all ten objects. Example: the ep11 blue cup has 11.15 cm3 in props against 6.48 cm3 in floor.json, and my recount
  of its 17 piece files gives 6.48 cm3. `exact_props` exists, but it is used only for the S guest.
- **Effect.** No verdict of this round changes, because nothing is usable. Fix (a) before the push list goes to the
  pose lanes, and fix all four before any round-2 folder is called usable.

**N2. H-d is a code defect against the written rule, so P76 is confounded [R, M].**
- **The rule.** F-I5.4 defines one keep-out ("the 2 mm grid points outside the body ...") for both steps of route 3:
  the repair ("until each hull is <= 0.3 cm3 or the cap is reached") and the gate.
- **The code.** `cavpieces.keepout` anchors its grid at `lo - pitch` of the hull set it is given. `repair` scores on
  the CoACD hulls' grid and stops there, while `gate` re-grids on the repaired set.
- **Only the grid phase differs.** The repaired hulls are hulls of body points inside their parents, and `reduce_hull`
  keeps a vertex subset, so every repaired hull lies inside the original union.
- **The size of the disagreement.** The repair reads 0.272-0.296 cm3 and the gate 0.344-1.55 cm3, on the five objects
  that stopped below the cap. [H] So for thin hulls the 2 mm point count itself depends strongly on the grid phase, and
  a shared grid would make the two agree without making the measure stable.
- **What to change in the report:**
  - T-I16's text calls H-d "a rule-level choice for the orchestrator". It is a code fix (no rule change). Because it
    changes route-3 outcomes, it still needs a dated entry.
  - P76 should read "falsified as built; confounded by the repair / gate grid mismatch".
  - Round 1's route-3 outcomes carry the same confound.
- **Delivery verdicts are unaffected [E].** Every folder has an object whose repair reached the cap, or one split
  short of it, and still failed the gate with many hulls over:
  - ep12: both objects (82);
  - ep13: the rack (82);
  - ep31: the rack (82);
  - ep2: the pot (82);
  - ep11: the blue cup (81 of 82, 21 hulls over).

**N3. The eval precheck's order and method were decided partly during the run, and no dated entry records them
[M, R].**
- **Order.**
  - The eval precheck ran 00:14-01:46, in parallel with T-I16 and before the public verification.
  - F-I5.15 (11)(v) and INTERLOCK 21.13.12 (4) put the eval precheck after "an orchestrator go after the public
    verification". The go came from the workflow at 00:14.
  - No dated entry records the change of order. The outcome is not affected: T-I16 froze its code at 88f49df before
    the first eval number (00:50), and no public decision cites an eval number.
- **Method, against F-I5.15 (3) / F-I5.16 (3):**
  - **Poses:** the packed references' poses (tier P1), not our eval tracks.
  - **Faithful colliders:** 2 mm cells of the pack's visual meshes (library_v3 and sf), not our SHELLs.
  - **Check (c):** overlap >= 1 cm3, a threshold taken from spoon-diag. The carvability sub-check was not run.
  - **Hands-off in the precheck tables:** "no contact label" (H0), not the 30 mm rule.
  - **Contact frames:** a fallback (`not_static`, then `in_hand`), added after eval-10's 1-5 mm reference jitter had
    been measured (README section 2 calls it post hoc).
  - **Library meshes:** used as faithful and visual colliders, beyond "the packed comparison rows" that F-I5.16 (7)
    names. They diagnose the pack and are not shape evidence, but this should be recorded.
- **What the result is.** A consistency check of the pack's references and colliders. It is not "the precheck alone
  first" of the eval twins (F-I5.15 (11)(v)), and should not be cited as that.
- **P103 does not depend on the fallback [M, `eval_contact_precheck.json`].** Eval 10's only rule-conforming frame is
  f111: the one static stretch with the packed colliders within 4 mm, in hand. It overflows in 16 of 16 copies (313
  contacts, 1,252 rows). B1 still applies to what that number means.
- **Output paths.** `collcarve2-evalcheck/` and `collcarve2-public/`, where F-I5.16 (3) and F-I5.15 (11)(iv) name
  `collcarve-r2/`. Record only.

**N4. Departures from the T-I16 run plan [M]. They do not change the outcome; record them in the outcomes entry.**
- **Machine.** The runs used this container, not the box. The decision was logged at 00:17, before the 00:18:23
  launch, but pushed only at 00:32:36.
- **T-I15** was not run, so P71, P92 and P75's ep26 / ep27 legs are untested.
- **Inputs.** The round-1 candidates were copied rather than rebuilt with `interlock_cands.py`. All 47 input files
  hash-identical in both run folders [M, `sha256sum -c`].

**N5. Priority on a shared machine [M].**
- **What happened.** At 00:46 the T-I16 step set its own scheduler group to nice -3, while other lanes ran at nice
  15-19. The letter of "never kill / renice others" was kept. The "nice" of F-I5.16 (6)(i) and 21.13.12 (1) was not:
  a negative nice takes CPU from the other lanes.
- **Now.** No negative-nice group remains (`/proc/*/autogroup`).
- **For later runs.** Do not repeat this. A run that needs more CPU belongs on the box.

**N6. Report precision (T-I16 summary and records) [M].**
- **P75.** "holds" covers only 3 of its 5 racks; the README says so, the summary does not.
- **Prediction line.** The summary's falsified list leaves out P77 (a miss by its own "fails another check" clause)
  and P90 (falsified). Both are reported elsewhere.
- **"0.05 mm wall left" is the floor of the measurement.** The wall rays start 0.05 mm off the sample and add the
  offset back (F-I5.17 (6)). So 0.049-0.05 mm means "<= 0.05 mm", and a sample whose true wall is thinner than 0.05 mm
  is scored further along or as a miss. The failure itself is robust: topology and wall integrity both fail at all
  seven floor frames, with 1,386-8,221 bad wall samples.
- **`g1_pass`.** It is `true` in all five `contact_gate.json` files, although G1 gated nothing.
  - ep11 has no top-level vacuous flag. Its pair key exists with zero gated rows, and only the pair verdict says
    `contact_gate_pair_vacuous`.
  - A reader of `g1_pass` alone sees a pass. `null` plus the flag would be clearer.
- **The "exact" shares are not exact on two objects.** For the ep11 blue cup the volume inside the SHELL (6.76 cm3) is
  larger than the union (6.48 cm3), giving -0.28 cm3 outside. The sweeper gives -0.006 cm3. The verdicts do not change.
- **No intrusion reported.**
  - F-I5.15 (1f) asks for intrusion and continuity per set. `search_layout` stops at the first failing check, so no
    candidate reports its intrusion.
  - "P71 not tested" follows from that early stop, not from the rule.
  - Computing intrusion on every candidate is cheap. It would have tested P71, including the negative-wall clipping of
    F-I5.17 (3).

**N7. Time stamps of the as-built entry [M].**
- The T-I14 nest runs were launched at 23:40:18. The commit they cite, ba3387d, was made 12 s later.
- F-I5.17 says "decided 22:47-23:45 UTC", but it was committed at 23:41:49.
- These are synthetic runs, not "real runs", so no rule is broken. They are listed for the record.

**N8. Wording and the eval boundary.**
- **The nest.** L0 (rims 3.3 mm apart) falsifies P90 as defined. It shows that our points and tracks do not represent
  a nest, not that ep11 holds none. The README words this correctly ("that our data represent"); the summary's "no
  public episode shows a real nest" is stronger.
- **Eval references.** The README's "or on the eval twins' references" may only mean inference under a frozen rule.
  Developing or debugging the carve on eval references would be development on eval data (CLAUDE.md).

**N9. Open records.**
- The PREREG outcomes entry (F-I5.19) and the INTERLOCK plain-words section are not written.
- F-I5.17 (13) (round-1 scratch folders absent) and (14) (ep24 bundle absent) are both false. The dated entry must
  correct them; the README corrects only (13).
- STATUS and the work log are not updated.

**N10. The eval scripts ran outside the gmg guard, so GT-freeness rests on code reading.**
- I read the column list (`COLS` in `scripts/evalcheck.py`). The scripts read:
  - `object_body_*`, the mesh and URDF paths, `fps` and `sequence_id`;
  - the robot frames and the MANO contact labels.
- All of these come from FlashCHORD `refs/.../processed/*.parquet` reference files (our tier-P1 perception). No dataset
  parquet and no `pose` field is read [R].
- This is acceptable for a diagnostic. State in the record that the check is unaudited (no strace).

## Confirmed

- **C1. Pre-registration before code.**
  - F-I5.15 was pushed at 22:02:26 and F-I5.16 at 22:46:41.
  - The first round-2 code ran at about 23:08, and the first code commit was pushed at 23:13:10.
  - F-I5.17 (23:41:51) and F-I5.18 (00:12:49) were pushed before T-I16.
  - The rule text has not been edited since it was pushed.
- **C2. The code that ran is the frozen, committed code, and nothing was tuned after outcomes.**
  - T-I16 launched at 00:18:23 on 88f49df, which was pushed at 00:13:26.
  - The launch sha256 of `collcarve.py`, `cavpieces.py`, `contactgate5.py`, `interlock.py`, `platebody.py`,
    `tools/collcarve2_dev.py` and `tools/interlock_dev.py` equal the git blobs at 88f49df, and `launch_code.dirty` is
    false.
  - The gmg modules equal ba3387d apart from the one-line test rename.
  - From 88f49df to HEAD (719e1a8) no gmg module, tool or test changed. Only `build/I` scripts and results did.
- **C3. The thresholds are as written** (code constant tables against F-I5.15 (10) and F-I5.16 (5)):
  - s_max 4 mm; f_keep 0.5; w_min 1.5 mm; s_rm 0.5; c_min 0.05 mm and c_max 1.0 mm; topology grid 1 mm;
  - continuity: cover 50 %, gaps 1 % / 50 %; intrusion 1e-6 m; sectors {8, ..., 32}; reference 64 sectors and 10 mm;
  - CoACD 0.02, auto, max_convex_hull floor(82 / 2) = 41, repair to 82; keep-out 0.3 cm3 at weight 10;
  - the sim=rl sha256 is checked at run time.
- **C4. The implementation follows the text**, except for N1, N2 and N6 (code reading):
  - the precheck (a), (b) and (c), with (c) = topology plus wall integrity plus removed share against the uncut SHELL;
  - the choice of floor frames and receivers;
  - the floor share, and S_ref only where S fails;
  - the search order and the order of checks;
  - `pose_impossible_all` and the push entries.
- **C5. The floor outcome reproduces [M].**
  - The scratch piece files sum to the floor's union volumes: ep11 blue cup 17 boxes and 6.48 cm3, beige cup 20 and
    6.912 cm3, sweeper 3 and 0.648 cm3.
  - Every share is 0.018-0.086, below 0.5, so all five folders are DO_NOT_USE on (i) alone, whatever the S leg.
    P79 and P80 hold.
- **C6. The precheck verdicts at the seven floor frames are robust [M, `floor.json`].**
  - Every frame fails (c) on both topology and wall integrity; ep11 f127 also fails the removed share (0.53).
  - ep13 f181 also fails (a), at -5.73 mm.
  - ep31 is vacuous: the faithful gaps are 12.0 and 11.9 mm.
  - The precheck at round 1's frames supports P77 (4 of 5 frames, a miss by its own clause) and P78 as reported.
- **C7. The markers are present [M].**
  - DO_NOT_USE.json is in the five round-2 scratch r0 folders and in their committed copies.
  - It is in the five round-1 scratch r0 folders (written 00:17:54) and in their committed copies (23:19).
  - CONTACT_GATE_PENDING.json is in all five round-2 folders.
  - No other F-I5 round folder in scratch lacks a marker.
  - The round-2 DO_NOT_USE.json lists only the share reasons. The per-frame precheck numbers that F-I5.15 (4d) also
    names are in `floor.json` beside it.
- **C8. No ground truth was read.**
  - T-I16 read only our v6 bundles, our M1 hands and our SHELL candidates.
  - Its diagnostics ran under the guard.
  - The eval precheck read only reference columns (N10).
- **C9. The eval precheck decided nothing.**
  - cea1342 touches only `collcarve2-evalcheck/` and the build log: no marker, mesh, pack or code change, and no message
    to another session.
  - After the WIP snapshot (a54eff6, 00:47) the script changed only a 100 mm distance cap and the labels beyond
    100 mm. No threshold changed.
- **C10. Cost $0.** No box was rented, and the ledger has no `mesh-bold` line for this round.

## For the outcomes entry (F-I5.19), in addition to the README's outcomes

- B1:
  - correct F-I5.17 (14), F-I5.18 and both READMEs on the ep24 bundle;
  - record the c1 verdict, or the cited P125 with a check that the scene is the same;
  - label the eval-10 relay accordingly.
- N1 (a)-(d) as as-built gaps against F-I5.15 (8). Fix them before any usable round-2 folder, and fix (a) before the
  push list is handed to the pose lanes.
- N2 as a code defect: the P76 wording, the dated entry for the fix, and round 1 confounded the same way.
- N3 (order and method of the eval precheck) and N4 (machine, T-I15, inputs) as run-order deviations.
- N5 (nice -3) as a process note.
- F-I5.17 (13) corrected.
