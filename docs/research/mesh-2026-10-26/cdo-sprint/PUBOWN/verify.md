# PUBOWN box step: adversarial verification

Written 2026-10-31 ~21:10 UTC by the verification step of the PUBOWN workflow. Scope: the box run
`mesh-20261031-pubown-ed7171c` and its report (`BOX.md`, `MANIFEST.json`, `checks/`, commits 753a9f6 and 0c33080).
Labels: [M] measured here, [D] diagnostic that reads ground truth (cited, not produced here), [E] estimate,
[H] hypothesis. Nothing here reads a scan, mocap, a parquet pose or an `*_align` file, and nothing is scored.

Everything below was re-derived from the HF store itself (API tree listing with LFS sha256, files fetched fresh into
an empty folder), from git at the frozen commit, or from my own scripts. The PUBOWN agent's local download was used
only after its bytes were shown equal to the store.

## Verdict

**No blocking finding in the box step.** The checks the workflow asked for all hold [M]:

| Check | Result |
|---|---|
| Each mesh built only from its own episode's points | holds for points; one pooled scalar constant (t0_C0b) enters, as C0b intends (note 1) |
| Flags = C0b's scan-free ones | holds: all 69 builder calls have the exact flag sets of C0b's own box `build.txt` |
| No GT read | holds: no GT path or token in any PUBOWN or upstream C0b command line; inputs = sweep tracks, C0b points, roster names |
| MANIFEST complete, sha256 = store | holds: 20/20 picks and the 4 Set-B cup candidates match the store LFS sha256, `SHA256SUMS`, `manifest.tsv`, `selection.json` |
| Frame / kit numbers | kit rows reproduced 20/20; extents and bodies reproduced; E0 gate decisions reproduced with E0's own `frame_check.py` (section 5) |
| Ledger, box gone | holds: planned 0.40 and actual 0.15 rows in `ledger/spend.jsonl`; instance 58572720 absent at 20:54:50Z |

The report's main finding also holds: Set A (the pre-registered rule) contains 7 templates that are broken in frame,
and the 5 racks are metre-scale. I add four things the consumer should know before choosing A or B: ep11 blue cup g1
(in both sets) carries two extra bodies; ep45's pot pick sits at 0.94 of the E0 centroid gate; the rack is not
bitwise reproducible even on one machine; and 5 public episodes have no MANIFEST row.

## 1. Store and MANIFEST [M]

- Store tree (`api/datasets/aebatirel/v2d-store/tree/main/runs/mesh-20261031-pubown-ed7171c/results/pubown/...`):
  20 files under `meshes/` and 66 `.glb` under `cand/` (58 candidates + 8 rack `joint` files, not candidates).
- For every MANIFEST `pubown` row: the store LFS sha256 and size equal MANIFEST `sha256` / `bytes`; the same sha256
  is in the store's `SHA256SUMS`, in `manifest.tsv` and in `candidate_src`; md5 recomputed on the bytes matches.
  Same for the 4 Set-B candidates (`cand/blue_cup/ep{12,13,21,22}_blue_cup_g0.glb`).
- library_v3 rows: sha256 of `meshes/library_v3/<object>.glb` in the repo equals the MANIFEST value (5/5).
- Every LFS file in the store tree (155) has its sha256 in `SHA256SUMS`; no mismatch. The store `SHA256SUMS`,
  `selection.json`, `manifest.tsv`, `params.json`, `plan.json` and `commands/*.txt` are byte-equal to the agent's local
  download, and `sha256sum -c` over that download passes 514/514.
- Completeness: every slot object of the 15 episodes in `plan.json` (roster names only) has a MANIFEST row (25 rows:
  20 pubown, 5 library_v3). `counts` is right.
- **Gap (non-blocking):** public episodes 18, 23, 24, 39 and 40 have no object with a PUBOWN method and no MANIFEST
  row. The re-track must read them as all-library_v3; the MANIFEST does not say so.
- Picks recomputed from `selection.json` `table` and the raw `fid/*/<label>@own.jsonl` (lowest sum_mm at 3 decimals,
  then fewer raw faces, then label): 20/20 equal to `selection`. All 58 fidelity values equal their jsonl.

## 2. Own-episode inputs [M]

- `commands/build.txt`: 69 builder invocations (pot 36, lid 16, blue cup 10, beige 2, rack 5). Every one names
  exactly one episode in all of its paths (points, output, marker json, axis cache).
- Rack: `prim_rack.py run --obs_dir pts/B --episodes <e>`. In the frozen code (`00e8584`, `run()`), the job list is
  built only from `ep<e>_plastic_dish_rack.npz` for the listed episodes, the floor depth is the max over that list
  (one episode: its own cut, logged `pass1_lip_above_cut_mm {"12": 22.8}`), and balls come from `markers/ep<e>.json`.
- `commands/fid.txt`: 58 calls, each candidate judged on its own episode's points. `sigma.txt` (4) and
  `markers.txt` (ep0) use only ep<e> points and the ep<e> sweep track.
- Upstream C0b commands (fetched from the C0b run): `obsA` 33, `obsB` 33, `measure` 52, `markers` 12 calls each name
  one episode. The only multi-episode calls are `derive` (the merged ep21+22 blue cup) and `t0`; no PUBOWN call
  reads `pts/M/merged_blue_cup.npz`.
- **Note 1, pooled constant:** `t0_c0b.json` (t0_C0b = 4.559 mm) is a statistic over the thickness rows of all 33
  public object-episodes. It is used as `--bar_t0` in every pot and lid build, and as the wall thickness where the
  own chain had no measurement: all 5 racks, both lids, beige ep11, pots ep0 and 44, blue cups ep11 and 22
  (`params.json`). That is C0b PREREG 3.3 and the same constant E0b uses, so it is within the brief, but "built only
  from its own episode" holds for points, not for this one scalar.
- 97 reused C0b files: the `plan.json` sha256 equals C0b's store `SHA256SUMS` for all 97, and the box fetch logged
  `sha_bad []` for them and for the 18 staged inputs. The store `inputs/SHA256SUMS` equals the local copy.
- Sweep tracks: sha256 of `SCR/data/sweep/ep<e>/poses.npz` (the brief's tracks), of the staged copies and of
  `plan.json` `poses_sha256` agree for all 15 episodes.

## 3. Flags and code identity [M]

- Flag sets, with per-pair numeric values masked (`--sigma`, `--t_fallback`, `--bar_t0`, `--app_d`, `--t_lid`,
  `--t_wall`, paths): PUBOWN's 69 calls give exactly the sets in C0b's box `build.txt` for each family:
  - pot: `--c0b --variant {fit,nostem,nomk,thick} --sigma --t_fallback --bar_t0 --markers_json --axis_cache`;
  - lid: `--c0b --lid_win {a6b1,a6b2} --variant ... --sigma --t_lid --bar_t0 --markers_json`;
  - lathe: `--tie 1.0 --floor base_t --t_fallback --tmax 0.008 --tmin 0.0015 --app_d [--appendages 0]`;
  - rack: `PRIM_CUP_LEAN=1 run --t_wall --s0_min_t --markers_dir --episodes`.
- `--c0b` in the frozen `prim_potlid.py` sets h_o 0.5, reach_rel 0.5, arch_ext_rel 0.5, t_clip and strap_t_clip
  [1.5, 8] mm, tie 1.0, app_d 3 sigma (C0b PREREG 3.10). Each pot candidate json records these in `c0b_options`
  (9 distinct blocks, one per episode). The rack json records `c0b: t_wall = s0_min = 4.5594 mm, cup_lean, markers_dir`.
  The marker files carry the frozen settings sha256 `488ac3b6...`.
- The thickness chain is per pair (`chain([own thick row], t0)`); C0b's rack pooling over the run episodes is replaced
  by the own episode, as PLAN s2 says. The value is t0_C0b on all 5 racks either way (own n = 0 or 3).
- Code: box `COMMIT` = ed7171c; `jobs/` is unchanged from ed7171c to HEAD. `plan.json` tree hashes equal
  `git rev-parse 00e8584:<dir>` for all 6 frozen directories, and the box logged `trees_equal: true`.
- No GT: no token `scan`, `mocap`, `align`, `parquet`, `observation`, `truth`, `library`, `meshes/` in any PUBOWN or
  C0b upstream command line. `library_v3` is read only by the post-hoc checks (section 5).

## 4. Kit path, extents and bodies (independent scripts) [M]

- Kit (`v2dlb` from the submission kit; `mesh_budget.py` sha256 `8f29481d...` = the box input): budget_mesh,
  `_encode_archive` / `_decode_object_mesh` and `mesh_quality_flags` on the 20 picks. Faces, vertices, watertight and
  flags equal the MANIFEST `kit_budget` rows 20/20; decode equal 20/20; no quality flag. Watertight after budget: 5
  (pots ep0, 41, 42, 43 and rack ep26), as corrected in NOTES 20:46Z.
- Extents and bodies (own split): all 20 extents equal the MANIFEST. Bodies beyond the report:
  - **ep11 blue cup g1 (in Set A and Set B): 3 bodies.** Besides the cup, extra bodies 74 mm and 52 mm across, at
    33 and 40 mm from the cup centre. It passes the E0 gate (centroid 5.2 mm), but it is the same g1 appendage
    failure as ep12/13/21/22, smaller. [H] beige-cup points (ep11 is the nested pair). Its g0 has 1 body after budget
    and also passes the gate (own fid 5.741 vs 5.171).
  - ep13 blue cup g1: a second body 179 mm across, 16 mm off centre ([H] a second shell).
  - pot ep2: 3 stray balls (238, 228 and 149 mm from the pot), not 2. pot ep44: 4 (340, 335, 301 and 163 mm),
    not 3. pot ep45 (fit, Set A and B): 2 stray bodies (21 mm at 145 mm, 14 mm at 84 mm), not mentioned in BOX.md.
  - beige ep11 g1: 4 bodies (174 mm at 35 mm, 97 mm at 42 mm, 2 mm at 54 mm), as reported.
- I did not re-run the trimmed ICP. Its pot numbers in MANIFEST (0.88-3.31 deg, 1.4-8.9 mm) match BOX.md.

## 5. E0 frame gate re-derived with E0's own measurement [M]

Set B depends on PUBOWN's re-implementation of the E0 gate (`scripts/pubown_gate_alt.py`). I re-measured every
candidate with E0's own measurement script, `cdo-sprint/C0/scripts/frame_check.py` (no registration, exact
closest-point median on 20 k samples, PCA on 200 k samples, kit budget), and applied `e0_select.py`'s rule with
`E0/inputs/thresholds.json` (`scripts/v5_gate.py`).

- **48 non-rack candidates** (36 pot, 10 blue cup, 2 beige): the gate decision is the same for all 46 gated ones,
  and beige has no threshold. The centroid offsets agree to 0.01 mm (the same deterministic area-weighted centroid).
  Medians differ by -0.01 to +0.13 mm (sample-to-sample nearest neighbour reads slightly high), far below the
  limits. Checked axis angles agree within 0.8 deg (pot: all 3 axes; blue cup: axis 0 only). The two cup axes that
  differ by up to 50 deg are the ill-defined lathe axes, which the gate does not check.
- **Closest calls**, all decided by the centroid:
  - pot ep45 fit / nostem: 15.27 mm against 16.31 mm, PASS (0.94 of the limit). This is Set A's and Set B's pick;
  - pot ep2 fit 13.82 (PASS), ep44 nostem 8.01 (PASS, the pick), ep44 thick 19.86 and fit 26.67 (FAIL);
  - blue cup ep13 g1: 12.49 mm against 10.58 mm, FAIL (1.18 x). The switch to g0 there rests on this one number.
- **10 rack candidates:** `frame_check.py` died silently on rack ep12 (16 m mesh; no traceback, most likely memory on
  this 15 GB VM), so I re-computed only the deterministic area-weighted centroid offset for all 10. All fail the
  34.39 mm limit: ep12 6475 / 6495 mm, ep13 48.0 / 50.1, ep26 2924 / 2952, ep27 73.1 / 76.9, ep31 2503 / 2508
  (full / nomk). Set B's "library_v3 for all 5 racks" follows from the centroid alone.
- **Set B re-derived:** applying the C0b s5 pick to the candidates that pass gives the MANIFEST `alt_e0_gated` for all
  20 pairs: 8 pots unchanged, pot ep27 to library_v3 (4/4 fail), blue cup ep11 g1 kept and ep12/13/21/22 to g0, beige
  ungated, 5 racks to library_v3. Kit budget is OK (<= 4096 faces and vertices) for all 48 measured candidates.

## 6. Reproducibility claims [M]

- C0b byte-identity: **38** candidates are shared with C0b's store (pot ep2, 26, 27, 41-45 = 32; blue cup ep21, 22
  = 4; beige = 2), and all 38 sha256 are equal. BOX.md says 32; the stronger statement holds.
- ep21 blue cup g1 = C0b's cross-episode blue-cup pick (`27957f76`), confirmed. The C0b working-copy NOTES
  (uncommitted, 20:30:51Z) give its AUC guard FAIL (mean -0.5462) and the rack's (mean -0.1325) [D].
- Rack ep12: I re-ran the frozen `prim_rack.py run --episodes 12` here (4 shared cores) on the C0b store inputs
  (`pts/B/ep12_plastic_dish_rack.npz` 9b17f51c..., `markers/ep12.json` 810e02ee..., equal to `plan.json`):
  - default threads: full `5de37db2`, nomk `cb19bc03`, own fid 23.606 mm, n_lip 69, 4 lip segments,
    201 x 328 x 647 mm. Byte-identical to the agent's dry run 2;
  - 1 thread (`OMP/OPENBLAS/MKL_NUM_THREADS=1`): full `4c42f44b`, nomk `c9553be2`. Different bytes (41 numeric
    fields differ, largest 13 % on a 0.8 mm attach gap), the same gross fit (n_lip 69, 4 segments, same extents);
  - box (64 cores): `c845d4f9`, 16.3 m, n_lip 2, 5 segments.
  - So the rack fit is not bitwise reproducible even on one machine across thread counts, and on the box the
    floating-point differences flipped the lip-plane step. This narrows the report's [H] (CPU type) to "any
    floating-point path change, threads included". The falsifier for "thread count alone explains the box" is a rerun
    on this VM with 64 threads forced, not run. Both local results are broken against library_v3 (109 x 159 x 496 mm)
    anyway.

## 7. Ledger and box [M]

- `ledger/spend.jsonl` (store): planned `mesh-20261031-pubown-ed7171c` 0.40 at 19:58Z, session mesh-bold, approval
  "owner standing go-ahead 2026-10-30 12:20 UTC"; actual 0.15 at 20:20Z. Cap $2 respected.
- Box clock: create 19:58:30Z, job 20:01:40-20:19:10Z (`run_job.log`: exit 0, self-destroy), gone from show at
  20:19:48Z per NOTES. 21.3 min x $0.410/h = $0.146 [E]; the image pull is not in the bandwidth term, so the actual
  may be a cent or two higher [E].
- `ops/vast.sh show` at 20:54:50Z: 58572720 absent. Two instances of other sessions are running (58556043
  `20261031-mv2b-...`, 58556438 `20261031-h5p7-...` labelled "PUSH-FAILED, destroying in 60 min unless HOLD"); not
  PUBOWN's, not touched.
- Secrets: no API key, bearer or HF token in the box logs pulled from the store or in the PUBOWN folder. The only
  64-hex string in the logs is cloudflared's binary checksum.

## 8. Non-blocking notes for the consumer

1. **Choose B over A, or at least drop the racks.** Set A's racks are 16.3 m, 5.9 m and 6.1 m long on ep12, 26 and
   31 [M]; as templates they test nothing. If A is kept for rule purity, score it per object so the racks do not hide
   the pot and cup result.
2. ep11 blue cup g1 is in both sets with two extra bodies (section 4). A consumer who wants B's logic ("no appendage
   bodies") would take ep11 g0 instead; that is a new rule, so it should be stated before the scores.
3. ep45 pot fit passes the E0 gate at 0.94 of the centroid limit (15.3 / 16.31 mm), partly from stray bodies.
4. MANIFEST omits episodes 18, 23, 24, 39, 40 (all library_v3).
5. The A/B choice is not fully blind: C0b's [D] scores of ep21 g1 (add_med 120 mm, 7 flips) and of its ep13 rack
   (add_med 31 mm) are already in C0b's NOTES.
6. Set B's gate reads `meshes/library_v3` (on the v5 provenance denylist; P1 tier) as the frame reference. That is
   E0's pre-registered gate and the tracks are library_v3-seeded already, but B's provenance is P1, like the tracks.
7. Set B was computed by `pubown_gate_alt.py`, a re-implementation of E0's gate (100 k samples, sample-to-sample
   nearest neighbour) rather than E0's `frame_check.py` (exact closest point, 20 k samples). Section 5 shows the
   decisions agree.
8. rack ep31: the build task is FAIL (joint step `IndexError`) but its full / nomk files were written before the
   crash and were used as candidates. Disclosed; moot, since both fail the gate.
9. BOX.md counts: 38 (not 32) byte-identical C0b candidates; ep2 has 3 and ep44 4 stray balls.
10. STATUS.md and docs/work-log.md still lack the PUBOWN result (disclosed; commits were limited to PUBOWN/).

## Files

- This file: `docs/research/mesh-2026-10-26/cdo-sprint/PUBOWN/verify.md` (the only committed file of this step).
- Scratch (not committed): `SCR/pubown_verify/` with `scripts/v1_manifest.py` (store / MANIFEST / roster),
  `v2_cmds.py` (flags, own-episode, GT tokens), `v3_bodies.py`, `v4_kit.py`, `v5_gate.py`; `fc/` (E0
  `frame_check.py` logs); `rack_out/`, `rack_out1/` (rack ep12 reruns). SCR =
  `/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad`.
- Commands: `python -I`, `nice -n 19`, scratchpad venv (numpy 2.5.4, scipy 1.18.1, trimesh 5.2.0).
