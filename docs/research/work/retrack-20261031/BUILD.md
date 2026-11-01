# Re-track build: P_o' (per-episode meshes as tracking templates) vs P_o (31 Oct 2026, ~18:35–19:05 UTC)

CPU only, this VM, $0. **Nothing is launched.** The meshes are not delivered yet. Pre-registration: `PREREG.md`. Job
strings and cost: `JOBS.txt`. Labels: [M] measured, [E] estimate, [H] hypothesis or threshold.

## 1. What a box does (`ops/jobs/perc_leak.sh`, LIB_EP_DIR mode)
It runs Phase 1's job (`../leak-decomp-20261030/phase1/BUILD.md` §1), with five differences, all opt-in through
`LIB_EP_DIR=<dir>`:

1. **Gate** (before any download):
   - `tools/rtk_mesh_check.py verify <dir> inputs.tsv` checks that `VALIDATION.json` exists with status pass or flagged,
     and that every mesh and `MANIFEST.json` still has its validated md5.
   - No mesh may sit outside the validation, and every name must be an object of its episode.
   - A second shell check repeats the names against `inputs.tsv`. Any failure: exit 1, with no download and no perc2.
2. **Per-episode template folder** `/content/rtk_templates/ep<N>/`, made of links: `<dir>/ep<N>/<obj>.glb` where
   delivered, else `$LIB/<obj>.glb`. It is logged per object (`ep2 templates: white_pot=episode white_pot_lid=library`).
3. **Arms o and o2** get `MESH_DIR=/content/rtk_templates/ep<N>`. Arm s is unchanged.
   - `run.json` adds `lib_ep_dir` and `lib`.
   - `tools/leak_p1.py bundle` records per object the real path, source (`episode` / `library`) and md5, and requires
     `templates_as_delivered` for ok. The summary line shows `ep-mesh k/n`.
4. **Run id**: `<yyyymmdd>-rtk<X>-<hex sha>` is accepted, only with LIB_EP_DIR and without arm s.
   - These are GT-free public tracks; arm s, the scan templates, still needs an `-orc` id.
   - The guard (`tools/no_oracle.py`) refuses every pushed `results/leak_p1/...` path by its folder name. The end of
     the job re-checks that for the record.
5. **Nothing else changes.** Same inputs, downloads (3 single files per episode), KF_MIN=120, Grounding DINO once
   with HF_HUB_OFFLINE=1, bundle, tar without `result.json` / `log.txt`, summary, one push and self-destroy.

## 2. Changes
| File | Change |
|---|---|
| `ops/jobs/perc_leak.sh` | opt-in `LIB_EP_DIR` (§1). Every new line sits under `[ -n "$LEP" ]` or gives the same bytes when unset: `md=$LIB` unless set; the `run.json` suffix `x` is empty when unset; the run-id rule's `else` branch is the old line. +52 / −4 lines |
| `tools/leak_p1.py` | (a) `bundle` / `summary`: per-object template source when `run.json` carries `lib_ep_dir`, with no new key otherwise. (b) new `score`: R (lib convention: the kit registration of the mesh the arm tracked with, `--lib-ep-dir` or env `LIB_EP_DIR`) + RPE + MPPE, through `tools/xstar_fit.py`'s own `kit_X` / `score_track` (Phase 1's chain). `score` reads mocap: CPU after inference only, public episodes only (refuses eval episodes and SPLIT≠public). The docstring says which commands read ground truth |
| `tools/rtk_mesh_check.py` | new: delivery validator (`check`, CPU) and box gate (`verify`, stdlib only), §4 |
| `docs/research/work/retrack-20261031/` | new: PREREG, BUILD, JOBS, `rtk_verdict.py`, `rtk_pull.py`, `scores/`, `po_bundles/` (Phase 1's 20 P_o bundles), `mock/` (scripts + `out/`) |

Not changed: `pipeline/perc2.py`, `pipeline/det_rules.py`, `ops/box/*` (all byte-identical to 87fc869 [M]: `git diff
--stat 87fc869 HEAD` empty), `tools/no_oracle.py`, `tools/xstar_fit.py`, the Phase-1 mock and its stored outputs.

## 3. Unset = byte-identical behaviour (evidence) [M]
- **Job-string replay** (`mock/replay.sh` → `mock/out/replay.txt`):
  - Phase 1's three exact `JOBS.txt` strings, parsed from the file, run through the Phase-1 mock twice: on the code
    before this change (HEAD e618f5c snapshot) and after it (working tree). Same mock path.
  - `mock/snap.py` snapshots every written and pushed file, `job.log`, the perc2 audit, the store traffic, `rc.txt` and
    `push.out`.
    - What perc2 saw is in the audit: MESH_DIR, the resolved templates, KF_MIN, SPLIT, HF_HUB_OFFLINE, the depth cache.
    - Before hashing, it blanks wall-clock and inode values only: UTC stamps, per-run seconds, run.json t0/t1, depth stat.
  - Result: **397 / 451 / 398 files, 0 differ** on boxes a / b / c.
  - The first pass differed only in `hf.log`: the push commit message carries a UTC stamp, now blanked.
- **Whole Phase-1 mock suite** (`mock/p1_suite.sh` → `mock/out/p1_suite.txt`): `run_all.sh` (boxes, B8 guard, faults,
  Grounding DINO, public data, refusals) run from scratch copies, before vs after. After blanking stamps and seconds,
  **9 / 9 output files are identical** (§8).
- **Scoring** (`scores/`): `leak_p1.py score` with LIB_EP_DIR unset, on Phase 1's stored P_o tracks, gives R and every
  per-object AUC **equal to Phase 1's stored lib numbers on 20 / 20 episodes**, with the same track md5.
  - Mean R 0.88986, RPE 1.6576 cm.
  - The RPE chain asserts its AUC equals `score_track`'s on every episode.

## 4. Delivery validator (`tools/rtk_mesh_check.py`) and the format asked of the mesh session
**Format**: `<dir>/ep<N>/<object>.glb`, plus `<dir>/MANIFEST.json`.
- N is one of the 20 public episodes and the object one of that episode's objects. Each `.glb` is GLB v2, in metres,
  with identity node transforms, in the body frame the mesh session wants tracked.
- `MANIFEST.json` gives the method, the commit, and per file `md5` and/or `sha256` and a `provenance_tier`. A top-level
  `provenance_tier` is accepted as the default.
- Sidecar `.json` / `.md` / `.txt` files are allowed. Objects not delivered fall back to library_v3.

**`check`** (`--write` adds `VALIDATION.json`):
- Hard failures (exit 1): layout, names, suffix, GLB v2, `extensionsRequired`, node transforms, load, budget_mesh,
  metres (largest extent 2 cm–1 m, sorted extents ×0.5–2 of library_v3), MANIFEST entry, hashes and tier, and
  `tools/no_oracle.py` (scan sha256s, oracle names).
- Flags (exit 2):
  - `tools/pack_swap_meshes.py`'s `frame_report` vs library_v3, same limits (5 mm, 5°, ±15 %);
  - more than 300k faces;
  - tier wording that mentions scan / mocap / oracle / GT.

**`verify`** is the box gate (§1).

**Fixture tests** (`mock/make_fixtures.py` → `mock/out/validator_*.txt`) [M]:
- Each of `bad_units` (mm export), `bad_node` (node translation 10 mm), `bad_name` (blue_cup in ep2), `bad_suffix`
  (`.obj`), `bad_md5` (MANIFEST md5 wrong), `no_manifest`, `no_tier`, `scan_copy` (the public white_pot scan: refused
  by the guard's sha256) and `bad_dir` (ep5) fails with the intended reason.
- `v3copy` (33 library_v3 byte copies, all 20 episodes) passes: 0 flags.
- `partial` (E0 scope: 21 meshes in 15 episodes; ep2 pot moved 2° / 3 mm, ep13 rack moved 10 mm) is FLAGGED, with only
  the ep13 rack's three frame flags (10.0 mm). The 2° / 3 mm pot stays under the limits.
- Cost: ~4.4 s per mesh (frame report at 200k samples), so ~2.5 min for 33 meshes.

## 5. CPU mock of the box job (`mock/run_rtk.sh` → `mock/out/rtk_*.txt`) [M]
Setup:
- Phase 1's mock (stub `hf` serving the refine mirror, stub transformers, placeholder public files, real scans), with
  the working-tree code.
- The stub perc2 is `mock/stub_rtk.py`: Phase 1's stub plus one change. An object whose template **bytes** differ from
  library_v3 gets a template-md5-dependent offset (1–5 mm), so a different mesh gives a different track and a byte
  copy gives exactly P_o's.

Scenarios:
- **ref**: LIB_EP_DIR unset, ARMS=o, all 20 episodes. These are the P_o tracks.
- **Boxes A and B**: JOBS.txt's exact strings (parsed), with `LIB_EP_DIR` pointed at the v3copy stub. Run ids
  `20261031-rtk{A,B}-abc1234`.
  - Every check passes: bundles ok, `ep-mesh 2/2` etc., the MESH_DIR perc2 saw, the template md5 in the bundle = in the
    perc2 audit = the delivered file, KF_MIN, SPLIT, HF_HUB_OFFLINE, depth reuse.
  - **The tracks reproduce P_o exactly: 16 + 17 objects identical, 0 different**, cameras identical.
  - Store: 30 single-file downloads per box, 0 listings, 1 upload.
  - The guard refuses all 156 / 158 pushed `results/leak_p1` files by store path.
  - Not refused: `COMMIT`, `job.log` and `run_state/*.ok`, which hold no tracks.
- **partial** (EPS 2 11 13 18):
  - Sources per object as delivered (ep11 beige and all of ep18 on library_v3).
  - Only ep2 white_pot and ep13 rack differ from P_o (6 identical, 2 different).
  - With `ARMS=o,o2 REPEAT=2`, the repeat arm uses the same template folder.
- **Refusals** (rc 1, 0 perc2 runs, 0 downloads):
  - rtk run id with LIB_EP_DIR unset;
  - rtk id with arm s;
  - rtk id with a non-hex sha;
  - LIB_EP_DIR missing;
  - a delivery without VALIDATION.json;
  - a mesh changed after validation;
  - an unlisted mesh added after validation.
- **Allowed**: an `-orc` run id with LIB_EP_DIR (rc 0).

## 6. Scoring switch (`tools/leak_p1.py score`; `scores/`) [M]
- Unset: equal to Phase 1 on 20 / 20 episodes (§3).
- `--lib-ep-dir` at the v3copy stub (library_v3 byte copies) gives **identical R, per-object AUC, RPE and MPPE on
  20 / 20 episodes**, with every mesh recorded as source `episode`. The env-var form `LIB_EP_DIR=...` gives the same
  (ep2, ep13).
- `partial` on the unchanged P_o tracks (mechanics only):
  - ep2 R 0.9866 → 0.9626 (pot moved 2° / 3 mm and registered). The lid's per-object AUC moves too, because the kit
    pins the scene on slot 0.
  - ep13 R 0.9595 → 0.9283 (rack moved 10 mm).
  - ep11 and ep18 are unchanged (blue-cup copy; nothing delivered).
  - So the switch registers the delivered mesh. In the real arm the track is made with that same mesh.
- **Noise floor**: Phase 1's P_o repeat (o2, 10 twins) in this scorer gives R mean |Δ| 0.0017, max 0.0136, and RPE mean
  |Δ| 0.0019 cm, max 0.0077 cm (`scores/R_Po2_noise.json`).
- Time: ~38 s per episode, ~7 min for 20 with `--jobs 2`.

## 7. Verdict tool (`rtk_verdict.py`; `mock/verdict_tests.py` → `mock/out/verdict_tests.txt`) [M]
The 14 fixtures are built on Phase 1's **real** P_o side: the 20 downloaded bundles, the real P_o cameras and
`R_Po.json`. The P_o' side is synthetic. All 14 behave as specified:
- F0: byte copies → FAIL (no changed episode).
- F1: 15 changed, 13 × +0.02 / 2 × −0.01 → PASS.
- Floor, mean, count and RPE failures → FAIL each.
- A missing episode → INCOMPLETE (rerun [45]).
- A depth sha, a 2 mm camera shift, a template md5 not as delivered, a missing tier, a scoring mesh not the tracked one,
  or a perc2-code difference by git → INVALID each.
- An unchanged episode with +0.05 → still PASS, with the cross-box NOTE.
- The code check runs `git diff 87fc869 <commit> -- pipeline/perc2.py pipeline/det_rules.py ops/box/`: identical for
  HEAD [M].
- The integrity cut of perc2's log was checked on a real Phase-1 log (ep13, box a; two single-file downloads):
  - `perc_log_inference.txt` (18 lines) equals the stamped lines before the first scoring line (` AUC `), and nothing
    before the cut mentions AUC, mocap or GT [M].
  - perc2 reads `pose` only at `perc2.py:508`, inside the scoring block (`:502-542`), after `poses.npz` (`:493`).

## 8. Phase-1 mock suite, before vs after [M]
`mock/p1_suite.sh` → `mock/out/p1_suite.txt`:
- **All 9 output files are identical**: boxes a/b/c, B8 guard, faults, Grounding DINO, public data, refusals and
  `run_all.txt`. LIB_EP_DIR was unset, on the code before (HEAD e618f5c) and after this change.
- `check.py` reports ALL CHECKS PASS on the three boxes.
- Against the stored 30 Oct outputs (`phase1/mock/out/`), 7 of the 9 files are identical. In the other 2, one refusal
  line is cut at 200 characters at a different place, because this mock's scratch path is longer. That happens on the
  "before" side too, so it is the environment, not the code.

## 9. Risks and open items
1. **Delivery timing.** The ETA is unknown; the deadline is ~1 Nov 09:00 UTC.
   - From delivery to verdict ≈ 2–3 h [E]: validate (3 min), commit, the owner's go, 2 boxes (0.4–1.4 h), pulls (82
     single files), scoring (7 min), verdict.
2. **Coverage.** If the delivery is E0's scope (pot, lid, rack, blue cup), 5 episodes stay unchanged and enter as 0.
   - Criterion 2 then needs 12 of the 15 changed episodes (80 %), and criterion 1 a mean of +0.0133 on them.
   - The pitcher, Phase 1's largest template lever, is out of scope (PREREG §9).
   - This was agreed as is. The "unchanged enters 0" clarification is mine [H]. The review showed it is NOT one-sided
     (it also drops unchanged episodes' negative drift); PREREG §11 amendment 1 now requires criteria 1–4 both on the
     measured dR of all 20 episodes and with unchanged episodes entered as 0.
3. **Cross-box GPU noise is unmeasured** (Phase 1 measured within-box only).
   - P_o' runs on other boxes than P_o did. The unchanged episodes and objects measure it in this run.
   - The camera tolerance 0.1 cm / 0.05° is [H] (Phase 1's cross-box max was 0.077 cm / 0.03°).
   - A larger VO difference would make the run INVALID, not a FAIL.
4. **GT-freeness cannot be validated by code.**
   - The tier is recorded verbatim.
   - C0's methods carried scan-derived constants (MK_R0 7 mm marker-ball prior, its 5–9.5 mm window, 2.5 mm walls). The
     C0b audit (bold-albattani 9451062, 163 records) is the mesh session's scan-free rebuild.
   - PREREG §6 makes a non-GT-free tier INVALID for this test. The validator flags tier wording for a human; it cannot
     judge it.
5. **Frames.**
   - The test is frame-consistent by construction: the arm tracks and registers the same mesh.
   - Using the meshes downstream (eval references on library_v3 simulator bodies) needs the frame gate (PREREG §7).
     Flagged objects in VALIDATION.json are the list to resolve.
6. **The stub perc2 never loads a mesh.**
   - Real FoundationPose and detection behaviour with the new meshes is not exercised on CPU. That includes the gray
     vertex-colour renders of untextured meshes in the DINOv2 frame-0 matching, render time for large meshes, and
     frame-0 init failures like ep0 with the scans.
   - That behaviour is what the test measures. A crash is caught as INCOMPLETE, then FAIL on a template-related second
     failure (PREREG §4).
   - The validator checks that trimesh `force='mesh'` loads each mesh, as perc2 does, and flags meshes over 300k faces.
7. **Guard scope.**
   - An `-rtk` run id is not refused by `tools/no_oracle.py`. Its `results/leak_p1` paths and `_oracle.tar` names are.
   - `job.log`, `COMMIT` and `run_state` are not refused; they hold no tracks.
   - Adding `rtk` to the guard's run-id pattern is a one-token change to a shared tool. Not done here; the orchestrator
     can decide.
8. **HF 429.**
   - Per box: setup, 30 single-file downloads and one push. Plus 82 single-file pulls afterwards. No listing anywhere.
   - Start box B ~10 min after box A.
9. **The control is from 30 Oct** (Phase 1, commit 87fc869). Library_v3, perc2, det_rules and ops/box are unchanged
   since then [M]. The depth caches and hands are checked by sha / md5 per episode (PREREG §5).
10. **Single-object episodes** (39–45) have RPE ≡ 0. The RPE criterion is carried by the 13 two-object episodes.
11. **The box reads the meshes from the commit** (as it reads `inputs.tsv`).
    - E0-sized meshes (0.05–0.4 MB, 20–35 files) are a few MB in git.
    - A delivery much larger than ~30 MB (C1's dust pan was 5.5 MB) would need a store pull instead. That is not
      implemented: ask the mesh session for meshes under ~2 MB each.
