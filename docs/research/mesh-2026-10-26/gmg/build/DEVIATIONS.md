# gmg build: deviations from SPEC v1 rev 1 / PREREG v1 rev 1

Each entry: date, step, what, why, and whether any scan or eval number was seen. SPEC.md and PREREG.md are not edited.
An entry here changes no pre-registered test, threshold or constant unless it says so (then it is also in PREREG F).

## B0 (2026-10-30, guard, io_gt fix, roster)

No scan, eval output or scan-derived number was seen or used for any entry below. None changes a pre-registered test,
threshold or constant, so none goes in PREREG section F.

1. **Extra role `frozen`** (`gmg/frozen_constants.json`, `gmg/deploy_variant.json`, tier P1). SPEC section 2's
   allow-list has no role for them, but sections 6 and 17 say the eval run reads them. Without the role the guard
   would refuse them.
2. **npz key filter for role `tracks`** (`world_T_cam`, `cam_T_*`). Stricter than SPEC, which filters only
   `det_f0.npz`. The current `poses.npz` files hold only these keys [M], so nothing is lost; any extra key a future
   tracker writes is refused until it is reviewed.
3. **Kit scorer exclusion, interpreted.** SPEC says "kit code and config, scorer excluded". Refused for role `kit`:
   `metric_code/**`, `v2dlb/object_mesh.py` (CD-O), `object_pose.py`, `track3_pose.py`, `mhr_metrics.py`,
   `vertices.py` (ADD sample), `trajectory.py` (reads reference poses) and `dataset.py` (reads parquets).
4. **`scratchpad/gen/mesh-*` is refused**, a superset of SPEC's `gen/mesh-20261029-gen-*` (the build brief names
   `gen/mesh-*`). Every generator run folder there was seeded with library_v3 crops.
5. **Depth and video allow-lists, interpreted.** Depth: `DATA/cache/depth/{public,eval}/ep*/depths_fs*.npy` (the HF
   store layout) and the existing public download folder `DATA/data/depth/ep*/` (`scripts/prep_obs.sh`). Video:
   `DATA/data/store/ep*_[abc].mp4`, `DATA/data/eval/ep*_[abc].mp4`, the `pipeline/fetch_data.sh` layout
   (`DATA/t3/v`, `DATA/t3/eval/v`) and the HF download (`DATA/hfds/track_3/{public,evaluation}/videos/**`). Note for
   B2/B4: `fetch_data.sh` hard-links the HF files into `t3/v`, and the guard refuses any file with more than one hard
   link, so a gmg video download must copy, not link.
6. **No `hands` role.** SPEC section 2 lists none: M1 (`hands_cpu.py`) runs MediaPipe and writes into RUN (role
   `own`). The existing `data/sweep/ep*/hands.npz` (G1 refs) are therefore refused in clean and dev mode. Faithful to
   SPEC, recorded because B1 cannot use those files.
7. **Default mode.** `GMG_MODE` unset means `clean` (SPEC does not say); an unknown value stops the import.
8. **Constant origins.** Heads `sensor`, `generic`, `kit`, `informed` (optional `:note`), `fitted:<what>`,
   `fallback:<what>`. `kit` and `fallback` come from PREREG A.6 rows ("4000 faces (kit 4096)"; the t0 fallback
   "scan-coincident"). Added guard: `fitted:` naming scans, GT, library, CD-O or ADD is refused, and the three
   scan-informed values SPEC section 2 bans (ball radius 7 mm, thickness 2.5 mm, V3 tau 0.20) are refused unless
   fitted (or, for the thickness, the pre-registered fallback). A name keeps one value per run.
9. **Own-tier mechanism.** Files in RUN carry the tier in `RUN/run_tier.json` (written by the bundle step, B1/B4);
   default P1. A clean run refuses its own folder if that file says DEV. Dev-mode runs are always tier DEV.
10. **In-process open hook.** SPEC says the guard "wraps every file open". Implemented as a Python audit hook that
    refuses `open()`/`os.open()` of GT-substring, deny-glob and refused-folder paths (code files are exempt from the
    substrings only, since e.g. `json/scanner.py` contains `/scan`; in dev mode a refused-folder file admitted through
    `open_input` under its dev role passes). Opens from C code are covered by the strace audit only.
11. **Deny-list sources are a union.** The guard and io_gt use the repo file plus whatever `pipeline/provenance.py`
    loaded (`V2D_DENYLIST`) plus `GMG_EXTRA_DENYLIST`: an environment variable can add entries, never remove them.
12. **Dev-role exemptions.** In dev mode only: `x0_pool` may read `results/gen-probe/**`, `results/prim/**`,
    `results/lathe_obs.jsonl`, `scratchpad/{gen/mesh-*,prim,lathe}/**` (the X0 pools and their existing labels,
    PREREG B.1); `fixture` may read `gmg/tests/fixtures/**`, the named T-V2d lid
    `scratchpad/prim/potlid/cand/white_pot_lid_ep2_fit.glb` only with sha256 prefix `e1be3218a8608793` (PREREG B.14),
    and folders a test registers. Library meshes, scans and `auto/` stay refused in dev mode.
13. **io_gt keeps its legacy obs roots** (`obs_all`, `obs`, `auto/stage1/refined`) for non-gmg use; the gmg guard
    refuses them in clean mode (obs_all passes in dev mode under role `obs_all`). The gmg run folders
    (`DATA/gmg/runs`, honouring `GMG_DATA_ROOT`) are added to the obs and mesh roots. Consequence: the stage-1b
    autokit tests that read library_v3 (`test_gates.py`, `test_programs.py`, `test_shell.py`) are now refused by
    design (stage 1b is closed and superseded); `parts.load_mesh_guarded(library_v3/...)` raises [M].
14. **Roster file content.** `gmg/roster_public.json` keys episodes by the `episode_index` in the parquet file names
    and records each file's sha256, row count and the compressed size of the one column chunk read. The parquets
    were deleted after the audited build.

## B0 round 2 (2026-10-30, fixes after verification round 1)

No scan, eval output or scan-derived number was seen or used for any entry below. The only label-file facts used are
the verifier's statement that the PREREG B.14 label sha prefix `e1be3218a8608793` belongs to the budgeted mesh (the
verifier read the object, path, sha and mesh_mode fields of two label lines, no score values); this round did not open
the label file. None of the entries changes a pre-registered test, threshold or constant, so none goes in PREREG F.

15. **det key filter by file identity** (supersedes the role-based filter of round 1). A file is a det file if its
    name is `det_f<N>.npz`, it is an `.npz` under `DATA/data/store/ep*/`, its sha256 is in the det registry
    (`gmg/det_registry.json`: sha256, size and zip member names of the 15 local dumps, written by
    `tools/det_registry.py`, which hashes bytes and lists names only; plus the local dumps hashed lazily and every det
    file hashed in the process), or its zip members include at least 2 of the distinctive library-derived names
    (`sim`, `chosen`, `gdino`, `template_extent`, `template_intensity`, `verify`, `verify_matched`, `score_rules`,
    `reprop`; generic names such as `area`, `score`, `params` are not used, so an own bundle is not mistaken for a det
    dump). A det file is read only through `load_npz` and only its seven mask keys, under any role.
    `open_input(..., 'det')` outside `load_npz` is refused; the hook refuses any other open of a det file (np.load,
    open, os.open, shutil.copy); the hook counts the opens it lets through inside `load_npz` (`guarded_opens` in the
    manifest) and the strace audit flags any det-file open beyond that count. Stricter than SPEC section 2, which
    states the rule for `det_f0.npz` only.
16. **Run roots and markers** (supersedes entry 9). Clean runs: `DATA/gmg/runs/<name>/` (SPEC section 6, unchanged).
    Dev runs: `DATA/gmg/runs-dev/<name>/` (new; SPEC section 6 names only `gmg/runs/`). `set_run` writes
    `RUN/run_tier.json` (`{mode, tier}`: clean P1, dev DEV) into a new or empty folder; an existing folder needs a
    marker of the same mode, and clean mode refuses a missing, invalid or DEV marker. A missing marker never means P1
    (own files are then DEV and refused in clean mode). The hook refuses writes under either run root outside the
    current run folder. `autokit/io_gt.py` gains the dev run root for its obs and mesh kinds; the gmg guard admits it
    only in dev mode.
17. **KIT and WEIGHTS roots are checked at import.** `GMG_KIT_ROOT` and `GMG_WEIGHTS_ROOT` may not contain or equal
    DATA, `DATA/data`, `DATA/cache`, `DATA/gmg`, either run root, the repository or a refused folder, and may not lie
    inside `DATA/data`, `DATA/cache`, `DATA/gmg`, the repository or a refused folder; otherwise the import fails.
18. **Named fixture pinned by its raw-file sha256 prefix** `4bd1751e84052f05` [M] instead of `e1be3218a8608793`.
    PREREG B.14 T-V2d names the hand-kit lid by its label sha prefix, which is the sha of the budgeted mesh the label
    scored, not of the raw file `scratchpad/prim/potlid/cand/white_pot_lid_ep2_fit.glb`. The pre-registered
    identifier is unchanged: the guard keeps it as `FIXTURE_LABEL_SHA`, and B1 must check that the budgeted fixture
    (after `fit_budget`) has that prefix before T-V2d counts.
19. **strace audit rules narrowed** (SPEC section 2 audit). System = `/proc`, `/sys`, `/dev` (not `/dev/shm`), the
    interpreter and venv, `/usr/lib*`, `/lib*` and execve; a named list of system files (`ld.so.cache`, `localtime`,
    locale, git config, ...) is exempt from the allow-list only. Every other successful read gets the GT substrings
    (only code-suffix files are exempt), deny glob, refused folder, deny sha256, det identity and allow-list checks;
    O_RDWR opens get the read and the write checks; writes outside the run folder, `--out` and `--allow-write` count
    as forbidden; written files are checked for det copies and deny-listed content. Later steps that need more (fonts,
    `/dev/shm`) must name them with `--allow` / `--allow-write`, which keep the content checks.
20. **Constants.** An `informed` origin must name its PREREG A.6 row (`INFORMED_A6`, checked against A.6 by a test).
    The banned-value names are matched more loosely (radius, `_r_`, ball, marker, sphere, bead; diameter 14 mm;
    thick, wall, shell, `t`/`t0` tokens; tau, v3, thresh, veto). Not covered: the "other brief thicknesses" and the
    "hand-kit windows" of SPEC section 2, which SPEC and PREREG name but give no values for (the t grid
    {1.5, 2.5, 4.0} mm also holds the A.6 sensor floor 1.5 mm and the 4 mm voxel, so only 2.5 mm is banned). B7
    freezes the detector settings.
21. **Frozen eval tracks (SPEC section 17).** The guard checks `data/eval/ep*/poses.npz` against
    `gmg/frozen_eval_tracks.json` automatically once that file exists (B19 writes it from the store run
    `20261025-evperc-4f596df`); until then the input record says `registry absent`. `expect_sha256` stays available.
22. **dir_fd and C-level opens.** `os.open` is wrapped so the hook sees the directory of a `dir_fd` open; direct
    `posix.open` calls and opens from C code are covered by the strace audit only.
23. **Manifest** schema `gmg-manifest/2`: adds `guarded_opens`, `run_marker`, `own_tier`, `runs_root`,
    `det_registry`, and `code_dirty` now covers `gmg/`, `autokit/`, `scripts/` and `pipeline/` (round 1:
    `gmg/`, `autokit/` and `pipeline/provenance.py`).

## B0 round 3 (2026-10-30, fixes after verification round 2)

No scan, eval output, label value or scan-derived number was seen or used for any entry below. The eval-track sha256
values of entry 31 are file hashes of P1 inputs (from the Hugging Face listing of our own store run), not eval
results. None of the entries changes a pre-registered test, threshold or constant, so none goes in PREREG F.

24. **The open hook covers more than `open`** (blocking item 1). Audit events `os.rename` (also `os.replace` and
    `shutil.move`), `os.link`, `os.symlink`, `os.remove`, `os.rmdir`, `shutil.rmtree`, `os.mkdir` and `os.truncate`
    get the path rules on every path they name, and the write rule on what they change: nothing under a run root
    outside the current run folder, no run root or parent of one, no rename of the current run folder. In clean mode
    a rename into the run from outside it is refused (a clean run writes its temporary files inside RUN), a symlink in
    the run must point inside it, and the dev run root is never touched. A hard link is never made inside a run root
    (SPEC section 2 refuses files with more than one link). Stricter than SPEC section 2, which speaks of opens.
25. **Run marker bound to its folder and written by set_run only.** The marker now holds `run` (the folder name) and
    `root` (`runs` or `runs-dev`); a marker that names another folder or root, or a marker of one mode in the other
    mode's root, is invalid (catches a copied marker and a folder moved between roots by `mv`). The hook refuses every
    write, rename, link or symlink onto `run_tier.json` and `outputs.jsonl` unless `set_run` / `write_manifest` is on
    the call stack (the private thread-local flag alone is not enough). Round-2 markers lack the binding and are
    invalid; no production run exists, so nothing is lost.
26. **Run provenance ledger** (`RUN/outputs.jsonl`, check 9; answers "whoever wrote it"). `write_manifest` records the
    files this process wrote in the run folder (Python opens for writing, renames inside RUN, `register_output`) as
    `outputs` in the manifest (schema `gmg-manifest/3`) and appends them, with sha256 and the run name, to the ledger.
    In clean mode a run file is read (open_input, load_npz, or any plain open the hook sees, unless the open
    truncates it) only if this process wrote it or the ledger lists it with its current sha256. A file moved, linked
    or copied into a clean run by a dev process, a shell command or an unguarded byte copy of a refused folder is
    therefore never an input, even under a forged marker; this also closes the round-2 non-blocking items on byte
    copies of refused folders and hard links placed in RUN. New API `register_output(path)` (not in SPEC section 7;
    additive) for files a process writes through C code or a child process; the file must be in RUN, one link,
    modified after the process started, and the strace audit checks that every manifest output was written by the
    audited command. Consequence for B1+: a stage reads an earlier stage's files only after that stage's
    `write_manifest`; C-level writers (torch.save to a path, cv2, open3d, ffmpeg) call `register_output`.
27. **GuardError is no longer an OSError** (round 1 made it `PermissionError, ValueError`). A refusal raised inside a
    library call that catches OSError would otherwise be swallowed: `shutil.move` falls back to copy and delete when
    the rename is refused, which would launder the file into RUN by the copy. Now refusals always propagate.
28. **strace audit** (blocking item 2). Each call is attributed to the image its pid ran when the call started (last
    successful execve that ended before it; a forked child before its execve inherits the parent's image at the
    clone, so clone/clone3/fork/vfork are traced); unknown means full checks. The git exemption covers read-only
    opens of the repository's `.git/` by a git image only; every other git open gets the full checks, and work-tree
    files git reads are exempt from the allow-list only. Traced in addition: rename, renameat, renameat2, link, linkat,
    symlink, symlinkat, chdir, fchdir, connect (names an architecture lacks are skipped with `?`). Relative paths
    are resolved through the dirfd annotation or the tracked working directory. New forbidden classes: a hard link
    created in the run folder, a read data file with more than one link, a run file read that neither the command
    wrote before nor the ledger lists, a manifest output the command did not write, a symlink target that fails the
    path rules, a network connection (AF_INET/AF_INET6) unless `--allow-net`; a rename source or destination, link or
    symlink outside the run folder counts as a write outside it. The CA bundle named by SSL_CERT_FILE /
    REQUESTS_CA_BUNDLE / CURL_CA_BUNDLE is a system file (content still checked).
29. **Non-blocking items of verification round 2.** (a) The deep det check runs for every open whose access mode is
    not O_WRONLY (`a+b` included). (b) The HF dataset's `track_3/*/mesh/**` and `track_3/*/urdf/**` (public scans and
    URDFs) are refused folders, and `DATA/hfds` joins the KIT/WEIGHTS root check. (c) `fitted:` origins that name
    eval episodes are refused. (d) The 0.2 ban matches names with tau, v3, veto or fold (bare `thresh` dropped, so an
    A.6 FREE threshold named `free_thresh` passes). (e) The hook refuses reads of data files with more than one link
    under DATA, KIT, WEIGHTS and gmg/ (outside the interpreter); the audit checks every data read. (f) The hook
    refuses opens of the kit scorer files and their `__pycache__` byte code in both modes, so they cannot be imported.
    (g) The det door (load_npz, hashing, member names) and the protected-file door need a guard function on the call
    stack; setting `_TLS.det_ok`, `_internal()` or `_TLS.protected` by hand opens nothing. (h) Process arguments
    (subprocess, exec, posix_spawn, spawn, os.system) with an absolute path that fails the path rules, the kit scorer
    or the dev run root, or with a URL naming ground truth (GT substrings, `track_3/*/{mesh,urdf,data}/`), and such
    URLs in urllib requests and http.client request lines, are refused before anything is sent or started. Not
    covered in-process: raw sockets and other clients (the audit's connect check is the backstop).
30. **Dummy run** gains the round-3 refusal classes (73 refused attempts, was 56) and two allowed patterns (write to a
    temporary file in RUN then `os.replace`; a child process writes a run file and the parent calls
    `register_output`).
31. **Frozen eval-track registry written in B0** (supersedes entry 21; SPEC section 17 leaves the check to the eval
    path, entry 21 to B19). `tools/frozen_eval_tracks.py` lists store run `20261025-evperc-4f596df`
    (`results/evalperc/ep<N>/poses.npz`) through the Hugging Face API and takes the LFS sha256 the hub keeps per file
    (no download) into `gmg/frozen_eval_tracks.json`; all 20 local `data/eval/ep*/poses.npz` match [M]. Clean mode
    now refuses eval tracks while the registry is absent (fail closed; the verifier's suggestion); dev mode notes it.
32. **Residuals (stated, not fixed).** An unguarded process that deliberately forges both a bound marker and ledger
    lines with the right sha256 is caught by neither the guard nor the audit of a later clean run (it is visible only
    in that process's own audit, if it ran under one). Code in the same interpreter can tamper with the guard's private
    state (`_WRITTEN`, `CFG`, caches); the strace audit re-derives run provenance and outputs from the log, so such
    tampering is caught when the run is audited. Direct `posix.*` calls with `dir_fd` and C-level opens are seen by
    the audit only. Plain reads of unlisted files are refused by the audit (default-deny), not by the hook, as in
    round 2.
33. **Roster audit: the parquets are no longer hashed by the auditor, and the round-2 report was silently weaker.**
    In policy roster the auditor exempts the --src parquets from the path rules, then (round 2) tried to hash them for
    the deny-sha check; its own guard hook refused the `.parquet` open and, GuardError being an OSError then, the
    auditor's `_content` swallowed the refusal: the round-2 roster audit's "0 forbidden opens" did not include a
    deny-sha check of the 20 parquets (found in round 3 when entry 27 made the refusal propagate). Round 3 skips the
    content check for the --src parquets explicitly (the roster tool records each parquet's sha256 itself; no
    deny-list entry is a parquet). The auditor launches strace through `guard.audit_spawn` (a call-stack door), since
    the hook's new process-argument check (entry 29h) would refuse an audited command line that names a parquet.

## B1 (2026-10-30, walking skeleton; dev mode only)

No scan, eval output, label value or scan-derived number was seen or used for any entry below. None changes a
pre-registered test, threshold or constant, so none goes in PREREG F. Entries 34-50 are interpretations where SPEC or
PREREG leave a detail open, or B1 limits (the full forms come in the steps named).

34. **Dev-only guard role `dev_frozen`** (`gmg/dev_constants.json`, tier DEV, refused in clean mode like every dev
    role). PREREG A.1 says dev runs use t0_dev ("the same statistic on obs_all") but SPEC section 2 names no role for
    it. `tools/t0_dev.py` computes it in an audited dev run over the 33 obs_all object-episodes of the roster and
    writes the committed copy with the run name, commit and input sha256.
35. **T-V2d fixture identity, corrected.** DEVIATIONS 18 assumed the PREREG label sha `e1be3218a8608793` is the sha
    of a budgeted mesh. It is `scripts/mesh_metric.sha()`, i.e. sha1[:16] of the file the label row scored, and the
    raw fixture `prim/potlid/cand/white_pot_lid_ep2_fit.glb` has exactly that sha1 prefix (hashed in B1; its sha256
    prefix is the guard's `4bd1751e84052f05`). The B.14 test checks the raw file's sha1 against `FIXTURE_LABEL_SHA`
    before T-V2d counts. No label file was opened.
36. **Contact frame, 2-D clause** (PREREG A.6 "masks, dilated by 10 px, overlap"): read as a mask gap of at most
    10 px (one dilation of 10 px), so a contact frame (gap <= 10 px) can never also be separated (gap > 16 px), as SPEC
    section 4 intends ("cannot flicker"). Masks are the projected footprints, on the 1600 x 1000 rectified image, of
    the owned points reduced to 2 mm centroids, dilated by the centroid spacing at their median depth and closed
    (3 x 3). The 3-D gap uses the same 2 mm centroids (error at most about 1.7 mm against the raw points).
37. **V4 rest frames.** "The lowest owned points within 5 mm of the table plane" cannot hold literally: the 8 mm table
    band (obs_points.py, SPEC M2) removes every point within 8 mm of the plane. B1 measures the 1st percentile of the
    frame's owned-point heights and requires it within 5 mm of the band's top (<= 13 mm). Speed = world displacement
    of the object origin between consecutive track frames. The at-rest table plane (episode.json `rest.n_obj`,
    `d_obj`) is the normalised mean normal and the median offset over the rest frames, in the object frame.
38. **Dev table plane** from the frame-0 depth of the det dump (keys `depth`, `K` only; half resolution with the
    half-resolution camera matrix) by `recon_mesh.table_plane`, moved to each frame by VO, with no per-frame refit
    (obs_points.py refits within 10 degrees). Dev only; B4 uses the depth cache.
39. **sigma even/odd** (A.2): parity of the frame's index in the stride-2 extraction sequence (every extracted track
    frame index is even). The median distance uses 50,000 odd-frame points (seed 0), exact point-triangle distances
    to the even-frame sheet.
40. **V3 is reported, not applied, in B1.** tau is fitted on the public clean CPU batch at B13 (A.3). B1 reports
    fsv_far(c) - fsv_far(s) with s the SHELL; no dev tau is invented (tau_X0 of B.1 needs the B5 fold rebuilds).
41. **V2 (a) inside test.** For a watertight candidate, ray parity (equal to winding number >= 0.5 for a closed mesh
    without self-intersection) is checked against the exact winding number on 2,000 random queries per call; on any
    disagreement, and for any non-watertight candidate, the exact winding number is computed for every query. Partner
    samples outside the candidate's bounding box grown by b can satisfy neither clause and are not evaluated.
42. **Partner sample normals** (A.2 "oriented towards the cameras that saw it"): PCA over the 12 nearest
    OBSERVED-voxel samples, turned towards the mean unit viewing direction of the voxel's own points.
43. **HULL in B1.** Seeded component = the 6-connected component of kept voxels with the most OBSERVED voxels (dev
    bundles carry no seeds; the grid is the old obs_all box, SPEC M2d). Above the table = the at-rest plane (no cut if
    the object has no rest plane, flag). Partner clip = non-OBSERVED voxels with pocc > 0, grown by one voxel at a
    time, at most twice, while the construction-time V2 (a) check still finds partner samples deeper than b; the
    target's OBSERVED voxels are its own evidence and are never clipped. Fold rebuilds raise (B5).
44. **SHELL in B1** is the plain route-A thin shell at t0_dev; the support-plane closing of SPEC section 8 is B8.
45. **Features are computed on the packed mesh.** In B1 every candidate's E, fsv_far, V2 and V4 are computed on its
    packed (fit_budget <= 4000 faces) mesh, i.e. the mesh that would ship; V1 on its kit decode (A.3).
46. **Selection skeleton** (in run_episode.py; select.py is B5): vetoes V1, V2, V4; tie set E(c) - E(best) <= b_tie x
    SE_diff(c) with the paired moving-block bootstrap of A.4; then class order and lower E. V5, the marker and
    parameter-prior keys are not in B1. No feasible candidate: ABSTAIN_HULL only.
47. **Blocks over all extraction frames** with owned points (track sanity is B4); E is the all-frames form (no fold
    rebuilds; B5).
48. **B.14 wording.** "United" = the two closed meshes concatenated; "route-A shell" = producers/shell at t0_dev;
    "median contact-frame relative pose" = the medoid contact frame of T_{o<-p} under the A.2 jitter metric (mean
    displacement of 600 partner samples, seed 0).
49. **Bundle format.** `hits`/`free` stored as uint16 (clipped); `hi` added (obs_all compatibility); `args` is a JSON
    string holding the obs_all args; episode.json adds `K`, `table_band_m`, `sigma_info` and `flags`.
50. **t0 measurements** (A.1 "the finite two-sided thicknesses that shell_sheet measures"): `thickness.py` repeats
    shell_sheet steps 1-3 with the same calls and stops before resolve_sides, so each sample's measurement counts once
    (shell_sheet's report rounds the share and the median).
51. **strace auditor, dev mode.** In dev mode the auditor exempts files the manifest lists under a dev role from the
    refused-folder rule, but its own content hashing (deny sha256, det identity) then opened them through its own
    guard hook, which refused them (`obs_all/`), and the analysis crashed (found on the t0_dev run; B0 audited clean
    runs only). Fix: such a file is admitted in the auditor's guard (`_ADMITTED`) before it is hashed. Clean mode is
    unchanged. The t0_dev log was re-analysed with the fixed auditor (0 forbidden opens).
52. **HULL surface coarsening when the 4 mm surface cannot be packed watertight** (2026-10-30, B1; SPEC section 8
    P-HULL "always closed", section 14 V1). The 4 mm marching-cubes hull is of high genus (ep11 beige cup: one
    watertight body, Euler number -134, 17016 faces [M, dev]); no fast_simplification setting decimates it to <= 4000
    faces without non-manifold edges (agg 1 stalls at 6310 faces; agg 3, 5, 7 at targets 3000-4000, Taubin smoothing
    first, and halving steps all leave it non-watertight [M, dev]), so the beige cup's HULL failed V1 in the first ep11
    run. The producer now marches the finest coarsening k = 1, 2, 3 of the 4 mm grid whose `fit_budget` result is
    watertight (k = 1 whenever it packs, so nothing changes for packable hulls). Coarse rule, chosen on dev ep11 among
    four variants measured on both cups (any / majority of the fine voxels x keep-unless-clipped / drop any block with
    a non-OBSERVED partner voxel; `<scratchpad>/gmg/b1/diag/hullk2_ep11.log`, GT-free features only): majority and
    drop-partner-blocks, the only variant that passed V1 and V2 on both cups with the smaller free-space share
    (beige k = 2: V1 pass, 0 deep partner samples, fsv_far 0.042; blue: 0, 0.20). The 'any' rule swelled the hull over
    the partner (beige 4685 deep samples, V2 veto). The fine grid, its states, the 4 mm construction check and the
    PREREG A.2 grid definition are unchanged; this is the shipped surface's resolution only. Report keys
    `coarsen_k`, `surface_vox_mm`, `coarsen_tries`; flags `surface_coarsened_x<k>` or `not_packable_watertight`
    (then the 4 mm surface is kept and V1 vetoes it). No scan, eval output or label value was seen; no
    pre-registered test, threshold or constant changes.
53. **Observation, not a change: the ep2 lid's SHELL is vetoed by V4 in dev** (run `20261030-b1ep2-edf9735` [M, dev]):
    1.08 % of its volume samples lie more than 2.21 mm (3 sigma) below the at-rest table plane (threshold 1 %;
    min height -4.98 mm; rest share 0.42), so the skeleton picks the lid's HULL (E 8.81 against the shell's 1.83).
    Likely causes [H]: the dev table plane (DEVIATIONS 38: frame-0 det depth moved by VO, no per-frame refit) and the
    8 mm table band of obs_all (DEVIATIONS 37). Falsifying check: B4's clean bundle (depth-cache table plane with the
    per-frame refit) gives the same lid shell a V4 share <= 1 %. V4 is applied as pre-registered; nothing is tuned.

## B5 (2026-10-30, score.py full and select.py; synthetic tests)

No scan, eval output, label value or scan-derived number was seen or used for any entry below (the only reference run
was the original `mesh_metric.ambiguity` on synthetic primitives, GT-free, strace-checked). None changes a
pre-registered test, threshold or constant, so none goes in PREREG F. They are interpretations where SPEC or PREREG
leave a detail open.

54. **Interfaces take the Bundle.** SPEC M13 lists `evidence(mesh, obs, heldout_frames, state, sigma,
    exclude_views=())`; the gmg form is `plan(bundle, obj, K, gen_views)` + `evidence(meshes, bundle, obj, blocks,
    fsv)`: the same information (owned points, grids, sigma, poses) read from the bundle; `exclude_views` is the plan's
    generator hold-out. `score_pool(...)` assembles every feature of one pool for `select.pick`.
55. **View direction** (A.2 "frames whose view direction (object frame) lies within 8 degrees of any generator input
    view"): the unit vector from the object's centre (median of its owned points over all frames) to the camera
    centre inv(cam_T_obj[f]) . 0, in the object frame. Generator input views are the GEN / FUSE candidates'
    `gen_input_frames` (or directions). The removal share is taken over the object's good frames; removed frames
    leave the held-out sets only (fold rebuilds still train on them). The hold-out runs only when the pool holds a GEN
    or FUSE candidate.
56. **Fold bookkeeping.** Fold candidates are matched to the all-frames candidate by cid (cid stability across folds
    is a producer duty: B8 / B11 name STRUCT candidates by structure, not by fitted values). A fold in which the
    producer yields no such candidate is scored on an empty mesh: every held-out ray of that block costs 10 sigma (the
    candidate did not exist on those training frames). A producer that cannot rebuild on a frame subset
    (NotImplementedError) is scored in the all-frames form (`fold: fixed` on the row). Today this is the B1 HULL: its
    fold grid needs per-frame-block hit/free votes, which obs_all and the B1 dev bundle do not hold (obs_points votes
    per frame from the depth maps); handed to B4 (extract_joint keeps per-block votes) and B8
    (`hull.produce(frames=...)`). [H] A fixed candidate's E is optimistic (its mesh saw the held-out block); the HULL
    is last in the class order, so the main exposure is the tau null of A.3, which needs the HULL folds at B13.
57. **Bootstrap frames.** Unchanged from B1 except that a block's frames are those left after the generator hold-out
    (`kept`). A block with no held-out point is left out of R_k (nanmean) and of the replicates; a candidate with no
    held-out point in any block has an undefined E (select ranks it +inf, flag `E_undefined`). SE_diff is the
    population SD (ddof 0) over the 200 replicates.
58. **Self-ambiguity copy.** `score.ambiguity` and the kit AUC helpers it calls are copied line for line (constants
    registered with origin `kit`); `tests/test_score.py` checks the copy equals the original `mesh_metric.ambiguity` to
    1e-9 on six synthetic meshes (`build/b5/amb_reference.py`, fixture `tests/fixtures/amb_reference.json`). It is
    computed on the mesh as passed: callers pass the packed mesh (<= 4000 faces), which the kit decode only welds,
    where mesh_metric used the decoded one. "Trusted balls only" (A.3 V5): the caller supplies the ball-free
    `base_mesh` with each candidate; the ambiguity uses the mesh with balls only if the object's balls are trusted
    (B.4), else the base mesh (flag `amb_includes_untrusted_balls` if no base mesh was supplied). No start that stays a
    flip (amb infinite): flip_units 10^6 (safest), not flip-risk. The kit symmetry is read from the kit's
    `config/tracks.json` (role kit; kit metadata).
59. **obs_flip_margin** (diagnostic, SPEC section 10; not used by S1): ICP moves 3000 owned points (seed 0) onto 3000
    surface samples of the candidate (seed 101) from the identity start and the kit's 24 PCA starts; the residual is
    the mean observed-to-model distance (the owned points cover one side, so a model-to-observed term would charge
    unseen surface alike for every start); margin = best flipped (> 90 deg, symmetry-aware) minus the identity-start
    residual, mm.
60. **select.pick details.** (i) A.5 leaves full ties (equal on all five keys) unordered: best = min (E, cid) and a
    sixth key, the cid string, make the result independent of the input order (the B5 pass condition "the tie order
    is deterministic"). (ii) V5 "feasible" = passing V1-V4; a candidate without an ambiguity counts as neither risky
    nor safe for V5 and ranks last on the flip key. (iii) V3 counts only when applied (tau set; before B13 it is
    reported, `not_applied`). (iv) TRACK_FAIL and IDENTITY_SWAP go straight to the ladder's PRIOR_GEN / PRIOR_PUBLIC
    (SPEC 13 names them in rungs 3-4; no S1 pick on a broken track). (v) ABSTAIN_HULL and PRIOR_GEN need a mesh that
    passes V1 (it is shipped); PRIOR_GEN = the lowest-E GEN candidate (ties by cid); PRIOR_PUBLIC returns no cid (the
    caller resolves it under owner decision O2). (vi) Low coverage with a feasible candidate: the Normal pick (the
    ladder is in order), flagged `low_coverage`. (vii) A variant outside the 8-entry A.7 menu is refused.
61. **tau_q99** (A.3): numpy's percentile with linear interpolation between order statistics (A.3 names no
    estimator); differences that are None or not finite are dropped.
62. **Constants added** (all generic, kit or informed as in A.6): `variant_menu_K`, `variant_menu_b_tie`,
    `variant_v0`, `gen_view_holdout_deg` 8, `gen_view_holdout_skip_frac` 0.8, `bootstrap_block_rate` 1/3,
    `v3_tau_percentile` 99, `amb_samples` 3000, `amb_icp_iterations` 40, `amb_icp_trim` 0.9 (kit), `amb_flip_deg` 90,
    `class_order` and `class_order_gen_view_overlap` (informed: class order), `v5_flip_rule` (informed: V5). B1's
    `blocks_K` = 3 stays (the A.6 default); a run's K is its variant's, recorded with the variant.
63. **Synthetic test fixtures** (`tests/synth.py`, `tests/amb_meshes.py`): geometry chosen for the tests, not
    constants of the gmg. The marker fixture uses balls of radius 10 mm on 25-35 mm posts; with 8 mm balls on 18-25 mm
    posts the slab stays flip-risk [M, synthetic] (B5 notes), an early sign [H] that few small markers near the
    surface may not lift real candidates out of V5's flip-risk; checked at B7 / B13.
64. **Module name `select`.** It shadows the standard-library `select` if the gmg folder itself is put on sys.path
    (running `python gmg/run_episode.py` instead of `python -m gmg.run_episode`). The gmg is always imported as a
    package (SPEC section 7); `tests/test_select.py` checks the standard module is intact under the test invocation.

## B2 (2026-10-30, generator views and Phase-1 exclusive masks; dev only)

No scan, eval output, label value or scan-derived number was seen or used for any entry below. The only data looked at
are dev bundles (obs_all + tracks), our depth, our hands and the public colour videos of ep2, ep11 and ep26. None of the
entries changes a pre-registered test, threshold or constant, so none goes in PREREG F.

65. **Dev-only guard role `dev_hands`** (`data/sweep/ep*/hands.npz`; npz keys `joints_left`, `joints_right`,
    `valid_left`, `valid_right`, `a_offset` only; tier DEV; refused in clean mode like every dev role). SPEC M9 removes
    hand pixels, but the hands module M1 (`hands_cpu.py`) is build step B4, and DEVIATIONS 6 refuses the existing
    hands files in both modes. These files are `pipeline/hands_mp.py` outputs (MediaPipe on the cam_a video, our depth,
    VO `world_T_cam`; no GT is read there [R]); they stand in for M1 in dev runs only. Clean runs use M1's output in RUN.
    The copies under `data/store/ep*/` are not admitted (any `.npz` there is a det file by identity, DEVIATIONS 15).
66. **Generator image = the cam_a colour stream.** Views and masks live on the `ep<N>_a.mp4` image (2028 x 1520,
    OpenCV 14-coefficient distortion); the track frame k pairs with colour frame j = k + 1 (hands_mp.py `a_offset`;
    the video has T frames, so the last track frame has no colour frame and is skipped). Camera chain rectified-left ->
    cam_a as in `pipeline/hands_mp.py` / `scripts/crops.py` (only the chain is reused; crops.py seeded masks with
    library_v3 renders and is not used). The A.6 / SPEC section 4 partner dilation "10 px" is stated on the rectified
    image (focal 600 px; "10 px ~ 10 mm at 0.5-0.6 m"); on cam_a (focal 1150 px) the same 10 mm is
    round(10 x 1150 / 600) = 19 px, which is used (stricter than a literal 10 px, which would be ~5 mm on cam_a).
    Separated / contact frames still come from the bundle census on the rectified image (unchanged A.6 rule).
67. **Hand pixels.** (a) MediaPipe capsules with the SPEC M2 radii (hand 30 mm, forearm 45 mm, 0.15 m long, as
    `obs_points.py` / `recon_mesh.hand_segments`), drawn as discs of radius f r / z along each bone, counted only where
    the capsule's near surface (z - r) is not behind the target's projected front surface (a hand behind the object is
    not visible). (b) **Depth occluders** (added, not in SPEC): footprint pixels whose reprojected depth lies more than
    20 mm in front of the target's projected front surface, grown by the depth edge band (2 rectified px x f_a / f_rect
    = 4 px), count as hand pixels too (removed from the mask and counted in the 25 % hand share). Reason: in ep2
    hands_mp rejected the right hand's 3-D fit from k 77 on (valid False) although MediaPipe detected it (n_det 2) [M],
    so the first lid view (k 78) had a hand on the lid inside the mask (trial 1). 20 mm is the A.6 3-D separation gap;
    it was chosen over the 10 mm contact gap after a GT-free dev check (`build/B2/diag/occl.log`): the pot's own
    surface reaches -15 to -19 mm at the 1st percentile (track and template error), 0.6-0.7 % of its pixels lie beyond
    -20 mm and none beyond -30 mm, while the hand on the lid covers 21 % of the lid footprint beyond -20 mm [M, dev].
    Partner pixels are removed by their dilated footprint regardless of depth order (exclusive, SPEC section 4).
68. **SAM2 refinement (B.11 "if it runs on the local CPU": it does).** Checkpoint `facebook/sam2.1-hiera-tiny`
    (transformers format, in the weights root, role weights; 0 missing / 0 unexpected keys in `Sam2Model`) [M]. Prompts:
    5 positives spread over the eroded exclusive mask, 5 negatives per partner (A.6 Phase-2 count) and, added, 5
    negatives on the removed hand pixels; image crop = square box around the projected mask (+25 % per side);
    multimask output, the candidate with the highest IoU against the projected mask is taken (GT-free). The logits are
    low-pass filtered (Gaussian, sigma = one cell of SAM2's 256-px low-resolution mask grid) before the threshold 0 and
    the mask's holes are filled: without it, the unfiltered masks had pinhole lattices (a transposed-convolution
    checkerboard) inside the cups [M, trial 2]. SPEC rule kept as written: a refined mask that gains any dilated-partner
    pixel is cut back to the projected mask (flag `refine_cut_back`). SPEC leaves open what the refinement may change
    otherwise; here it **only trims the outline band**: pixels of the projected exclusive mask within the partner
    margin (19 px) of its outline that SAM2 leaves out are removed; the interior is our geometry and stays (SAM2 dropped
    the dark inside of the beige cup and grew over the hand and forearm in trials 1-3 [M]). A refinement keeping less
    than 0.6 of the projected mask (the A.6 visible-area share) is rejected (`refine_rejected`; SAM2 segmented
    something else). Fragments of the final mask smaller than a disc of the partner margin are dropped (projected or
    refined). Hand and partner pixels can therefore never enter the final mask through the refinement.
69. **View choice details** (SPEC section 4 mechanism 2, A.6 row "generator views"). Candidate frames: the object's
    good frames (dev: every extraction frame with owned points) that have a colour frame and a depth frame. Visible
    area = the exclusive mask's pixel count; "episode maximum" = its maximum over those frames. Hand share = removed
    hand pixels (67 a and b) / (footprint minus dilated partners). First view = the **hand-free** qualifying frame
    (no hand pixel on the target) with the largest visible area, else the qualifying frame with the largest visible
    area (B.12 asks for "M9's best separated, hand-free view"; in trial 2 the largest-area rule picked a pot view with
    the hand on the handle (16 %) although hand-free separated frames reach 97 % of that area [M, dev]); then
    farthest-point sampling on the view direction (cam_a centre in the object frame), >= 8 deg, <= 6 views. One view
    (x seeds, `one_view`) whenever the sampling returns one view (this includes a pool span >= 8 deg with no frame
    >= 8 deg from the first view: ep2 pot, span 11.2 deg). Contact mode only when **no** frame is separated (SPEC
    wording); if separated frames exist but none qualifies, no view is chosen (`no_qualifying_view`, generator not run).
    Contact-mode order: least partner overlap (share of the footprint under the dilated partners), then hand-free, then
    larger area; each taken frame >= 8 deg from the earlier ones. An object with no partner has every frame separated.
    Contact mode inpaints the partners' dilated pixels outside the target mask (OpenCV Telea, crop box) for the image.
70. **Valid depth** (A.6 "valid depth >= 0.6 of the mask"): the FoundationStereo depth of frame k, `obs_points.py`
    validity (finite, 0.05-1.5 m, 5 x 5 dilate - erode <= 2 cm), back-projected from a box around all tracked objects,
    moved into cam_a, projected with its distortion and z-buffered with a 3 x 3 min filter for the 1.9x focal ratio.
    A mask pixel counts if it receives a valid sample (this is the pointmap SAM 3D will get). A depth-agreement share
    (|depth - target front| <= 3 cm) is reported as a diagnostic only.
71. **B.11 test as run.** Partner pixels = (a) every owned point of every partner projected one by one into cam_a at
    the view's frame (no centroids, no dilation) and (b) every pixel of the partners' footprints (closed, filled, not
    dilated). A view passes if neither touches the projected mask (after closing and filling) nor the final mask (after
    refinement), the final mask holds no removed hand pixel, it is not empty, and, in separated mode, the frame is in
    the census's separated set for every partner. Footprints: 2 mm centroids of the owned points, dilated by their
    spacing at the median depth, closed (3 x 3) and holes filled (the census `_mask` on cam_a plus the fill).
72. **Dev-data weakness of B.11.** obs_all removed partner points within 12 mm of the library_v3 meshes, so dev
    partner footprints can miss partner pixels next to the contact; the 10 mm margin covers part of that. The
    owner-relevant ep2 views are separated frames (lid-to-pot gap >= 186 px on cam_a [M, dev]), where this does not
    matter. B.11 should run again on clean bundles (B4) or on the G0 box before SAM 3D (PREREG B.11, B.12).
73. **(2026-10-31, B2) Audit environment of runs that load SAM2 (transformers).** The first final B.11 run
    (`runs-dev/20261030-b2views-fd7b357`) had forbidden 0, unlisted 0, network 0 but 7 writes outside the run folder,
    all library side effects, none a data read: a stale `.pyc` written under a temporary name (the audit exempts only
    names ending in `.pyc`), Python `tempfile`'s writability probe in `/tmp`, `filelock._strict`'s import-time
    hard-link probe (`/tmp/tmp*/probe-source`, `probe-link`; filelock comes in with transformers) and one POSIX
    semaphore in `/dev/shm` (a multiprocessing lock). Audited runs that load SAM2 therefore run with
    `PYTHONDONTWRITEBYTECODE=1`, `TMPDIR` = a per-run folder outside the run folder (`<scratchpad>/gmg/tmp/<run>`; inside
    the run folder the filelock probe's hard link would count as forbidden), progress bars off
    (`HF_HUB_DISABLE_PROGRESS_BARS=1`, `TQDM_DISABLE=1`) and `--allow-write '<that TMPDIR>/**' --allow-write
    '/dev/shm/sem.*'`. Reads stay fully checked (the allow-list only exempts writes). `b11_views` also records the HEAD
    commit at its start in the manifest (`extra.start_commit`), because the manifest takes HEAD when it is written and
    another agent committed B7 files to the shared checkout during that run (manifest commit f286e79 = fd7b357 plus
    `structure.py` and `build/B7.md`, neither imported by B2). No scan or eval number involved; no PREREG value changed.

## B7 (2026-10-31, structure.py and markers.py; synthetic tests and dev run)

No scan or eval output was read or scored for any entry below (zero scan scorings; the dev run reads obs_all, tracks,
calib, roster and the det depth/K keys only). Known to this build before any choice: the frozen SPEC/PREREG text,
including SPEC section 10's scan-catalogue marker numbers (about 7 mm, about 5 balls) and the obs-first design-probe
summaries (disclosed in `build/B7.md`). No pre-registered test, threshold or constant is changed, so nothing goes in
PREREG F.

74. **"Recovered within 1 sigma" (SPEC 24, B7 pass condition) is measured as a position error over the object**, so an
    angle error counts with its lever arm: lathe = distance from the true axis to the estimated axis at the two ends
    of the object's span along the true axis; mirror = max over the true mesh's vertices of the difference of the
    signed distances to the estimated and the true plane; plate = |thickness error| and the mid plane by the mirror
    measure. sigma = the 1 mm range noise of the synthetic renderer. The spec gives no measure; an angle-only or
    offset-only test would ignore the other half of the error. Chosen before the test ran (the trial numbers of the
    30 Oct notes were known: 0.15-0.2 deg, 0.5 mm).
75. **Mirror search and evaluation** (structure.py; sym_probe logic): the probe's 400-normal search with the pairing
    offset is followed by a Nelder-Mead refinement of (two tilts, offset) on the same ranking score (synthetic
    finding, 30 Oct notes: on boxy shapes the pairing offset stalls 4 mm off). A symmetry's shares are taken over the
    points it MOVES by more than the 3 sigma noise band ("observed" = lands in a voxel with any evidence, "free" =
    lands in a FREE voxel, residual = 80 % trimmed mean nearest-neighbour distance of the moved points that land in
    observed voxels), and a symmetry that moves fewer than half the points is not accepted (it holds the surface,
    e.g. a plate's face plane, and completes nothing). PREREG A.6's three acceptance thresholds are applied as
    written; the moved-share condition only removes degenerate planes.
76. **Axis, repeats, planes.** Axis: two candidates, lathe_obs.fit_axis + parts.refine_axis_rot and parts.axis_search
    (rim window E1 of A.6b), the lower rotational consistency wins; rotational consistency = lathe_obs.rot_consistency
    with its defaults (45/90/135 deg, 80 % trimmed mean) on a fixed 20,000-point subsample of the 2 mm-downsampled
    owned points (the SPEC names this function; no other definition was tried). lathe_mad_sigma (sym_probe's
    partial-view lathe score) is reported only. Repeats: C2-C6 about the axis candidate and the three principal axes,
    accepted with the mirror rule (entry 75). Planes: parts.segment_planes with the 3 sigma band and the plate_set
    defaults; plane pair = two opposed, parallel (< 30 deg) faces with the material between them, footprint overlap
    >= 0.5 and a gap in the slab window 3-25 mm (A.6, informed).
77. **A flat plate passes the lathe test.** PREREG A.6 accepts a lathe on rotational consistency <= 3 sigma alone; the
    synthetic 10 mm slab scores 2.80 sigma (rotating a plate about its normal keeps most points on the plate; the 80 %
    trim drops the corners), so it is accepted as a lathe. Not changed (a pre-registered threshold). The share of
    rotated points landing in FREE voxels (`rot_free_viol`, 39 % for the slab, 3 % for the cup) and lathe_mad_sigma
    (13.5 vs 0.2) are reported as diagnostics. [H] Downstream, a lathe candidate of a plate fills free space and is
    charged by fsv_far and E (B8/B5); falsified if a dev plate's SYM lathe candidate is picked at B8/B10.
78. **Marker detector details the SPEC leaves open** (markers.py): one RANDOM point per 1.5 mm voxel (the probe's first
    point favours early frames when points are stored frame by frame); votes computed batched (same fits as
    parts.sphere_fit_free; tested); the vote residual limit max(1.5 sigma, 0.12 r) uses the bundle's sigma (A.2) in
    place of the probe's own split floor; "fit residual" = the median |d - r| over the fit inliers (the value
    parts.sphere_fit_free / sphere_fit_ransac return); observed cap = 2 a with cos a = 1 - 2 x cap spread; convex =
    share of the points within the 3 sigma band that face their camera (parts.fit_ball's RANSAC rule, >= 0.8); frames
    and "both halves" (frames < T/2 and >= T/2) are counted on the raw owned points within the band that face their
    camera; overlap suppression keeps the ball with more votes; consensus = the plain median of the accepted radii
    pooled over the episode's objects (SPEC section 10; ball_nms.py's support-weighted median and its +-25 % filter
    are not applied: the SPEC text names neither); the second pass bounds the votes and the robust fit to consensus
    +-10 % and adds only balls that overlap no kept ball; posts are decided in attach() against the candidate mesh
    (the stem rule needs the host surface). Frozen in `gmg/marker_settings.json` (3f7f661) before the dev run.
79. **Known limitation: the frozen detector accepts sharp corners and edges as balls** [M, synthetic]. On a 100 x 60 x
    30 mm box with four 6.5 mm balls (1 mm noise) the four balls are found within 0.35 mm, but 9 corner/edge fits
    (r 8.9-12.5 mm, median residual 1.0-1.4 mm <= 1.5 sigma, cap 155-210 deg, convex 0.89-0.94) pass every frozen
    test, and the radius consensus lands on them (10.9 mm). Two GT-free statistics separate the 171 pass-1
    candidates completely on this scene: the median angle between local PCA normals and the fitted radial direction
    (balls 11-19 deg, corners 29-67 deg; the normal-compatibility test of Schnabel, Wahl and Klein 2007, "Efficient
    RANSAC for point-cloud shape detection", which parts.sphere_fit_ransac cites but does not implement) and the
    ratio of points just outside the sphere to points on it (0.02-0.28 vs 0.21-4.3, overlapping). **Not adopted**:
    a new acceptance test changes the pre-registered detector, and the scan-catalogue marker numbers are known to
    this build (SPEC section 10), so the amendment rule does not allow it here. Both statistics are computed and
    reported for every candidate and ball as diagnostics only (`normal_dev_deg`, `outside_ratio`), so the owner can
    decide. Pre-registered guard: B.4 (bimodal radius in >= 2 episodes turns balls off; the corner radii differ from
    the balls'). Risk [H]: real sharp corners (boards, dust pan, rack) repeat across episodes, so B.4's repeatability
    can pass and make corner "balls" trusted; falsified if the dev run finds no ball with normal_dev_deg > 25 deg on
    the boards, dust pan and rack.
80. **Speed only** (markers.py, no change of result): voting chunks sorted by neighbourhood size; the batched
    Gauss-Newton stops once every fit converged (|step| < 1e-10 m).
81. **Dev run** (`tools/b7_dev.py`): the 10 anchors of PREREG C.2 are the first episode of each list (track sanity is
    B4 and not built, so no anchor is replaced); dev bundles from obs_all (tier DEV, never scored); structure for the
    anchor object only; markers for every tracked object of the episode (the consensus is pooled over them); ep40 has
    one tracked object (mini_dust_pan). Notes edited while the run ran make the end manifest `code_dirty` (B7 notes and
    this file only); `b7_summary.json` records HEAD and the dirty files at the start.

## B4 (2026-10-31, joint extraction, hands, track sanity, contact; clean public bundles)

Written before any B4 output was looked at (interpretations of SPEC section 7 M1-M4 and PREREG B.2a, B.3, B.15). No
scan number was seen; none bears on these choices.

82. **Dev-only guard role `clean_run`** (`DATA/gmg/runs/*/bundle/**`, `DATA/gmg/runs/*/aux/**`; tier DEV, refused in
    clean mode like every dev role). PREREG B.3 compares the clean extraction with obs_all; obs_all is dev-only, so the
    comparison runs in a dev process (`tools/b4_roi_swap.py`), which must read the clean run's grids and its owner
    labels. A clean process still reads only its own run (role own).
83. **Lattice and final grid box.** The cube lattice puts the track origin on a voxel corner (generic: no library box
    sets the phase). The final grids (SPEC section 6) cover a sub-lattice of the cube: the seeded component's box plus
    2 cm (obs_points.py's ROI margin; obs_all used library box + 2 cm) or, when the 1.5 x guard fires, the guard box
    (seed box + max(2 cm, 25 %) per side). SPEC does not say where the grids end after the crop.
84. **Voxel-centric votes, kept from obs_points.py.** "`hits`: owned samples of this object only" is the obs_points hit
    (|sdf| < 4 mm between the voxel centre and the depth at the voxel's pixel) counted only when that pixel's sample is
    owned by o (`shared`: when it is shared and o is in the tie set). `free`: every valid depth ray after the edge
    filter carves (table and hand pixels too), as in obs_points.py. Pass 0 counts hits from every valid sample.
85. **Ownership tie, "within 2 binomial standard errors"**: |r_best - r_k| <= 2 sqrt(se_best^2 + se_k^2) (the SE of a
    difference of two proportions), each se from the Agresti-Caffo adjusted proportion (h + 1) / (n + 2), so a ratio
    of 0 or 1 from 3 frames is not certain (the plain SE would be 0). The tie set holds every keep-rule object within
    2 SE of the best; two or more members = shared.
86. **Seeds and seeded components.** SPEC: "provisional owned points of o's 3-D-separated frames ...; or, if frame 0 is
    3-D-separated for o, the frame-0 SAM2 proposal ...". Read as: the det proposal (B) when frame 0 is 3-D-separated
    from every other tracked object in the pass-1 census and an exclusive proposal exists; otherwise the separated-frame
    points (A). Reason: in a single-object episode (A) is every persistent point within 0.30 m, so it cannot separate a
    static object from static clutter, which is what the guard is for; (B) is the Phase-1 analogue of the Phase-2
    start-frame mask. Proposal choice: proposals holding o's projected frame-0 origin (half-resolution det mask pixel),
    minus those holding another tracked object's projected origin, then the largest IoU with o's provisional (owned or
    o-tied) footprint at frame 0; seed points = frame-0 samples inside it that are provisionally o-owned or o-tied
    (so no table, hand or partner pixel of a loose mask seeds). (A) uses owned points only. Det dumps exist for 15 of
    the 20 public episodes (none for ep12, ep18, ep24, ep27, ep40). Component voxel set = cube voxels holding at least
    one provisional o-owned or o-tied sample (all pass the pass-0 keep rule); 8 mm connectivity = voxel centres at
    most 2 voxels apart (Euclidean); the seeded component = every component holding a seed point's voxel. Guard: per
    axis, component box (voxel centres +- half a voxel) > 1.5 x seed-point box; fallback box = seed box +-
    max(2 cm, 25 % of the seed extent on that axis); the component is clipped to it. Nearest-seed tie-break uses the
    seed points as 2 mm centroids (object frame).
87. **Co-moving bookkeeping.** tied fraction = share of o's pass-1 samples (owned or o-tied) that were tied with p;
    `co_moving` if > 0.5; `co_moving_unresolved` if co_moving and rule (c) left more than half of those tied samples
    shared; `tie_break` = the more frequent of mask and seed among the pass-3 tie decisions of the pair, `none` if
    neither decided any. Rule (a) (Phase 1) applies at frame 0 only and assigns a tied sample when exactly one tied
    object's chosen proposal holds its pixel. With more than two tied objects, (b) compares the two nearest seeds.
88. **Frames with a cube corner behind the camera** (obs_points.py skipped the frame when a ROI corner had z < 5 cm):
    the pixel box becomes the whole image, so a 0.6 m cube near the camera (object held close) does not drop the frame.
89. **Table.** Frame-0 RANSAC (recon_mesh.table_plane on the full-resolution frame-0 depth) under the first tracked
    object (slot order) whose origin admits a plane; per-frame refits (obs_points.py rule) on the samples of the union
    of the cubes; refits stored as `table_frames` (camera frame) for M3. V4's `rest` keeps B1's world plane moved by VO.
90. **Track sanity (M3).** Owned points of a frame lie above the 8 mm table band by construction, so the below-table
    test places the object's surface samples (one per OBSERVED voxel, `contact.observed_samples`) with the frame's
    track and tests them against that frame's refit table plane. Block-vs-rest residual: the blocks are A.2's K = 3
    contiguous blocks of the object's frames with owned points; residual(f) = median distance of up to 2000 of f's
    owned points (seed 0) to the 2 mm centroids of the owned points of the other two blocks. "Its frames" (TRACK_FAIL)
    = the object's frames with owned points; good = such a frame that is not bad.
91. **Identity shells (M3).** "Route-A shell" = the route-A sheet of `autokit.shell.shell_sheet` (the shell's
    mid-surface: t0 is fitted only at B13), from up to 400k random owned points (seed 0) of the object's good frames;
    4000 area-weighted samples; chamfer = mean of the two mean nearest distances (mm) after registering A onto B
    (24 starts = the 24 proper axis permutations of A's PCA frame onto B's, centroids aligned, 30 point-to-point ICP
    iterations on 1500 points per side, best final chamfer). Split test: first and second half (time order) of the good
    frames; the partner's shell from its good frames; pass if chamfer(h1, h2) < min(chamfer(h1, p), chamfer(h2, p)).
    Cross test: references are the other object-episodes without TRACK_FAIL. A failed split or cross test marks o
    IDENTITY_SWAP (SPEC: "a failure marks o IDENTITY_SWAP"). `register` lives in track_sanity.py until M11 (B6).
92. **M1 environment.** `uv venv --python /usr/bin/python3.12 <DATA>/mpvenv`; mediapipe 0.10.14, numpy 2.5.4,
    opencv-python-headless and opencv-contrib-python 5.0.0.93 (uv's resolution), scipy 1.18.1. hands_mp.py runs with
    its defaults (a_offset 1, legacy API, greedy linker), as the existing sweep. Videos: the public dataset's cam_a
    files (`DATA/hfds/track_3/public/videos/...`; the local `data/store/ep<N>_a.mp4` copies have the same sizes). The
    strace audit gets `--allow <DATA>/mpvenv/**`: the child reads its model files (.tflite, .binarypb), which are data
    files by suffix.
93. **B.3 as run.** Old OBSERVED = the A.2 rule on obs_all hits/free (B1's `state_grid`); new OBSERVED on the OLD
    lattice = the clean final owner labels (aux `owners.npz`) re-voted with the same vote function and A.2 rule (a
    lattice-phase difference alone would otherwise lower the Jaccard); "new outside the old box" uses the clean grid on
    its own lattice (voxel centres outside [lo, hi] of the obs_all file).
94. **B.2a as run.** The reference sheet takes up to 600k random owned points (seed 0) of the 3-D-separated frames
    (final census, gap > 20 mm) that hold o's owned points; testable if >= 10 such frames; "p's owned samples in the
    same frame" = p's `own == 0` points of that frame moved by T_{o<-p}[f]; contact frames from the final census.
95. **(2026-10-31, B4, after the ep2 trial) Below-table test on the raw owned points** (supersedes the sample choice of
    entry 90). The first implementation placed one sample per OBSERVED voxel by each frame's track; on the ep2 trial
    (`runs/20261031-b4try1-738976b`, not audited) it marked 80 of 172 white_pot frames and 34 of 172 lid frames bad,
    all while the objects rest on the table: the underside, seen only while lifted, is about 5 % of the voxel samples
    and sits 4-15 mm under the table at rest [M]. SPEC says "more than 5 % of its owned points"; the raw owned points
    (all frames, 50k at random, seed 0) weight each surface by how often it was seen, as the text reads. Same trial:
    0 of 172 pot frames and 7 of 172 lid frames bad [M]. Thresholds unchanged. No scan number seen.
96. **(2026-10-31, B4) B.3 diagnostic added (not a pass condition).** obs_points.py never removed partner surfaces from
    its hit votes (`--others` filtered the saved points only; the hit vote excludes table and hand pixels only), so
    an obs_all OBSERVED grid holds the partner's voxels where the partner sat persistently in the object's frame;
    ownership removes them by design. b4_roi_swap therefore also reports the Jaccard over old-lattice voxels whose clean
    voxel has no partner evidence (pocc = 0 and shared = 0) and the number of lost voxels with partner evidence. The
    B.3 verdict stays the pre-registered one. Seen before adding it: the ep2 trial values (pot Jaccard 0.907, lid
    0.918; 532 of the pot's 1005 lost voxels and 286 of the lid's 351 carry partner evidence) [M, dev comparison].
82. **(2026-10-31, B7) Marker settings version 2 after dev run 1 (informed by a GT-free dev result).** Dev run 1
    (3f7f661; group A at ep27, group B through ep2; stopped at 05:57 UTC) gave on ep2 38 "balls", all with robust-fit
    radii 9.7-13.2 mm although their vote clusters had radii 4.8-10.9 mm (lid: mostly 4.8-5.9 mm), caps 96-191 deg,
    normal deviation 35-71 deg and outside ratio 0.5-4: the RANSAC fit on the points within 2 r_cl of the cluster
    centre grew a large sphere through the ball and the host surface around it (a ball on a short post has its host
    inside 2 r; the synthetic posts were 15 mm long, so the synthetic tests did not show it). Second, the second pass
    window (consensus 12.0 mm +-10 %) reached 13.2 mm, outside the A.6 window. Changes: the robust fit uses the points
    within r_cl + 3 sigma (the voted sphere and its noise band), and the second-pass window is intersected with the
    A.6 window. Both are implementation settings of `marker_settings.json` (v1 sha 8a4d5ed7..., v2 sha 488ac3b6...,
    history kept in the file), not PREREG A.6 values (unchanged). Origin: informed (the dev result above). Disclosure:
    the scan-catalogue marker numbers (SPEC section 10: about 7 mm, about 5 balls) were known; the change was chosen
    from the failure mode (fit radius running to the window's upper bound, host points in the fit), not from a radius
    value, and nothing snaps to a size. The stopped run's outputs are kept (`build/b7/runs/20261031-b7devb-3f7f661/`,
    ep2 only). No scan or eval number was seen.
97. **(2026-10-31, B4) M1 environment for a clean audit** (supersedes the venv of entry 92). The first audited batch
    (`runs/20261031-b4ext-0eb8016`, ep0 complete, ep2 and ep18 stopped) failed the strace audit with 57 forbidden
    opens, all from the MediaPipe child, none a data input: 37 venv files with 2 hard links (uv links package files
    from its cache; the audit refuses data files with more than one link), `/sbin/ldconfig` and gcc/ld temp files in
    `/tmp` (sounddevice's import probes for portaudio with `ctypes.util.find_library`), and matplotlib's font cache in
    `~/.cache`. Fix: venv rebuilt with `UV_LINK_MODE=copy` (0 files with more than one link), `sounddevice` uninstalled
    (mediapipe's hands do not need it; import verified), the matplotlib font cache prebuilt in `<venv>/mplconfig` and
    passed as MPLCONFIGDIR, the child's TMPDIR set inside the run (`hands/<split>/ep<N>/tmp`, removed when empty). The
    stopped run is kept (scratchpad) as a failed attempt; its outputs are not used.
98. **(2026-10-31, B4) Speed only: pass-0 votes at the sampled voxels.** Pass 0 now counts hits/free only at the cube
    voxels that hold a sample (the only voxels passes 1-3 read) and the final grids' free counts are voted in the pass-4
    sweep on the final box. The counts are those of the dense vote (`tests/test_extract.VotePointsTests`; on ep2 frames
    0 and 150, 0 mismatches over 800k voxels [M]). No result changes.
99. **(2026-10-31, B4, after seeing the ep0 bundle of the stopped run) TRACK_FAIL counts all extraction frames**
    (supersedes the denominator of entry 90). SPEC: "fewer than 30 % of its frames, or fewer than 20 frames, are
    good". Entry 90 read "its frames" as the frames holding the object's owned points; a track that loses its object
    then hides, because frames without owned points drop out of the denominator. Seen [M]: the ep0 lid has owned points
    in 32 of 187 extraction frames (3094 owned points, 21 OBSERVED voxels, sigma clamped at 3 mm), 30 of them good:
    not TRACK_FAIL under entry 90, TRACK_FAIL (30 / 187 = 16 %) under the literal reading, which is applied here: the
    tracked object's frames are every frame of its track. Applied uniformly to all 20 episodes by `tools/b4_identity.py`
    (before the cross test, whose references are the non-TRACK_FAIL object-episodes); both readings are stored per
    object (`sanity.track_fail_readings`) and reported. Disclosure for B.15 / P22: P22 predicts that the lid is not
    testable; that outcome now rests on this reading, chosen after the ep0 lid was seen. No scan number seen.
100. **(2026-10-31, B4, after seeing the B.3 records of ep0, ep2 and ep18) B.3 attribution diagnostic; fresh batch.**
    Seen [M, dev comparison]: Jaccard ep0 pot 0.931 (781 lost voxels, 3 with partner evidence), ep0 lid 0.351 (34 old
    OBSERVED voxels: the lost lid track), ep2 pot 0.907, ep2 lid 0.918, ep18 sweeper 0.649 and dust pan 0.782 (ep18's
    obs_all files had no hands removed). The lost voxels are mostly old OBSERVED voxels with few hits. Hypothesis [H]:
    an obs_points.py hit at voxel V comes from a pixel whose sample may lie in a neighbouring voxel; SPEC section 7
    gives that sample an owner only if some object's keep rule passes at the sample's own voxel, so V loses the hit
    (literal SPEC behaviour, not changed). To test it without changing any rule, the aux file `owners.npz` now holds
    every in-cube sample (code NONE = unowned) and `tools/b4_roi_swap.py` reports, per file, the re-voted hits of the
    lost voxels by pixel category (owned, shared with o, other object, unowned) and diagnostic Jaccards with other
    categories counted (`attribution_diag`). Falsified if the lost voxels' hits are mostly not "unowned". The B.3 pass
    rule and its inputs are unchanged. The second batch (`runs/20261031-b4ext2-74fabc9`: ep2 and ep18 complete, ep0
    and ep31 started) was killed by a machine restart at about 06:58 UTC; it is kept as a stopped attempt. All 20
    episodes are rerun in one fresh run on one commit (the aux change touches no bundle file). No scan number seen.
101. **(2026-10-31, B4, after seeing the ep31 bundle of run `20261031-b4ext3-8885ae0`) Seed fallback when no
    3-D-separated frame exists.** Seen [M]: in ep31 the pass-1 census on provisional owned points finds 0 of 145
    frames 3-D-separated (pass-1 3-D gap at most 2.1 mm in every frame: the static rack's and the sweeper's provisional
    clouds hold each other's surfaces), so neither seed of SPEC section 7 pass 2 exists (rule A has no frames, rule B
    needs frame 0 to be 3-D-separated); the seeded components were empty and both objects got no owned point (both
    TRACK_FAIL, B.3 Jaccard 0). SPEC does not cover this case. Closest faithful choice: when o's seed is empty, (1) the
    exclusive frame-0 det proposal is used without the frame-0 separation test (SPEC's own exclusivity rule, "a proposal
    containing two objects' origins is not used", keeps a two-object proposal out; seed points as entry 86), flag
    `seed_fallback:<o>`; (2) without a det dump or an exclusive proposal, o has no seed: its pass-3 candidates are not
    restricted to a seeded component (pass-1 ownership among the keep-rule objects), there is no guard (no seed box),
    the grid box is the provisional voxel box + 2 cm, flag `no_seed:<o>`; (3) the nearest-seed tie-break (b) needs a
    seed for both compared objects, else the sample stays shared (rule c); before, a tied object without a seed lost
    every tie to a seeded one (distance infinity). Episodes whose seeds are non-empty are unchanged by (1)-(3). The run
    `20261031-b4ext3-8885ae0` (ep0, ep2, ep31 complete; ep18, ep23, ep24 started) is stopped and kept as a failed
    attempt; all 20 episodes are rerun in a fresh run on the commit of this entry. No scan number seen.
102. **(2026-10-31, B7) Numbering note.** The B7 entry "82" (marker settings version 2) shares its number with B4's
    entry 82 (dev-only guard role `clean_run`); B7 notes, commit messages and the `markers.py` origin string cite the
    marker one as "DEVIATIONS 82". Read it as "B7-82". No content change.
103. **(2026-10-31, B7) Marker dev runs on the anchor objects only** (supersedes the marker half of entry 81). SPEC
    section 10 pools the radius consensus over all tracked objects of an episode; the B7 marker dev runs detect on the
    C.2 anchor object of each episode only (`b7_dev.py --marker-objects anchors`), so the consensus is the anchor
    object's own (one anchor object per episode). Reason: compute (ep2 with both objects took 1845 s; the B7 processes
    share 4 cores with another agent's batch). The B7 task asks for the 10 anchor dev PAIRS, which this covers; ep2
    also has the full-episode run (`b7mkchk-a1bc5f7`: pot and lid, consensus pooled), which is the lid's B7 record.
    Seen before choosing: ep2's full-episode result (dev, GT-free). Dev outputs only; nothing downstream reads them.
    No scan or eval number seen.
104. **(2026-10-31, B7) GT-free visual ball check** (`tools/b7_ball_crops.py`, a dev diagnostic outside every run):
    each detected ball is moved by OUR track into the camera, projected into the colour camera ego_cam_a and cropped
    in the 3 frames whose raw owned points support it most. Inputs: obs_all (dev), tracks, calib, the public colour
    videos (ego_cam_a; those of ep12, 18, 21, 24, 27 and 40 were downloaded from the public HF dataset into
    `<scratchpad>/data/store/`, camera a only, no parquet, mesh or scan). Read visually by the agent and reported for
    the owner; NOT used to change any detector setting (marker settings v2, sha 488ac3b6..., stay frozen) or to pick
    anything. Findings in `build/B7.md` [M, dev, visual].
105. **(2026-10-31, B7) Runs after the machine restart.** The 06:36 UTC runs died at about 07:00 UTC. The structure run
    `b7struct-0eb8016` (8 of 10 anchors, no manifest) is kept with an audit analysed without a manifest (flagged only:
    dev-role obs_all reads, det_f0 opens and writes into its own run folder; no GT path, no network); its 8 results
    are used as they are (structure code unchanged since f286e79; a full audited rerun would cost several CPU-hours
    under the shared CPU). The two missing anchors (ep27, ep31) and all marker anchors were rerun on c56d473 (gmg,
    autokit, scripts and pipeline code identical to a11866e) with `OMP_NUM_THREADS=1` (speed only; single-threaded
    BLAS can change last-digit rounding, not a setting).
102. **(2026-10-31, B4) Speed only, and how B.15 is reported.** `tools/b4_identity.py` computes the cross-test
    registrations first (`track_sanity.cross_pairs`, a thread pool) and passes them to `cross_test`; the values equal
    the serial loop (`tests/test_extract.RegistrationTests.test_cross_precomputed_threads`); in practice no speed-up (the ICP
    loop holds the GIL; 1024 registrations in 2658 s). `tools/b4_report.py` lists the cross-test flags and the split-test
    flags apart, because P22 is stated for the cross-object test, while SPEC section 7 marks IDENTITY_SWAP on either;
    written after the identity log was seen (ep24 board 1 fails the split test). No rule or threshold changes. No scan
    number seen.
106. **(2026-10-31, B3) M10 remesh method as built** (`gmg/remesh.py`; SPEC section 7 M10 says "generalised winding
    number or SDF voxelisation, marching cubes, largest-component cleanup, then fit_budget"). (a) The inside test is
    the GWN >= 0.5 estimated by six axis-direction ray votes per node (a ray votes inside if its signed crossing count
    is non-zero or its crossing count is odd; inside if more than 3 of 6 vote; exact winding number per ray for a
    closed oriented mesh; the six-direction share approximates the GWN's solid-angle mean for open meshes; the ray
    voting of Nooruddin and Turk 2003); nodes near the surface with 2-4 inside votes get the exact solid-angle GWN of a
    3000-face copy (at most 5000 nodes, nearest the surface first). Reason: exact GWN at every node did not finish
    20k queries x 12k faces in 2 min on this shared CPU [M]; grids hold 0.2-5 M nodes. (b) Voxel cleanup before
    marching cubes: enclosed outside regions filled, largest 6-connected solid kept (the "largest-component cleanup",
    done on the solid; the mesh split after marching cubes stays as a second guard). (c) Numerical choices: grid origin
    shifted by 0.382 pitch (nodes exactly on CAD planes gave zero-volume slivers); exact distances only within 2
    pitches of the surface; thin-part retry (union with a 0.75-pitch shell) when < 90 % of the input surface lies
    within one pitch of the result; budget ladder 4000, 3992, ..., 3744 checked with the kit decode (float32 vertices,
    zero-area faces dropped) and accepted only with |area change| <= 5 %; then the fallback rungs (the solid closed by 1,
    then 2 nodes; a 2x, then 3x pitch grid with the thin shell), each counted only if its coverage stays within 0.02 of
    min(0.90, base coverage) (a first 3 mm rung without the shell kept 14 % of a thin-walled pot); none accepted -> the
    decoded-watertight try with the best coverage (budget_unaccepted). Seen before (c)'s area tolerance and fallback
    rungs, and before (a)'s parity and (b): the GT-free remesh outcomes of 1-6 of the 104 B.10 meshes (dev trial runs
    `runs-dev/20261031-b10try*`, kept). B.10's threshold is unchanged; the final B.10 run (a1402f0) covers all 104 with
    the final code. No scan or eval number seen.
107. **(2026-10-31, B3) G0 inputs are prepared on the local CPU, not on the box** (SPEC section 18 G0 row: "SAM2 masks
    for ep2; the mask test of PREREG B.11 runs on the box first"). PREREG B.11 allows the local CPU when SAM2 runs there
    (it does, B2); `tools/g0_inputs.py` re-runs M9 and B.11 on the CLEAN ep2 bundle of B4 (PREREG B.12: clean if B4 has
    run; DEVIATIONS 72 asked for this re-run) and writes the SAM 3D inputs only if B.11 passes; the box runs SAM 3D
    only. The process is dev (the clean bundle is read through the dev role clean_run, as `interlock.load_bundle_any`),
    so every G0 output is tier DEV (flag dev_process_clean_bundle). Hands: role dev_hands (`data/sweep/ep2/hands.npz`,
    `pipeline/hands_mp.py` output) as in B2; B4's M1 hands (same `hands_mp.py`) sit in the B4 run folder, which no
    dev role admits. No scan or eval number seen.
108. **(2026-10-31, B3) SAM 3D input camera and pointmap filter.** The colour frame is undistorted to a pinhole
    camera with cam_a's own K (same camera frame); the mask is remapped with nearest interpolation; the pointmap is
    our depth of frame k reprojected into that camera (z-buffer, 3x3 gap fill, back-projected along the pixel rays),
    NaN outside the mask (lit note 1.1; organiser `_depth_to_pointmap`). Added after seeing the trial inputs (GT-free,
    before any SAM 3D output): depth samples more than 20 mm (the A.6 occluder / separated-frame gap, constant
    `genmask_occluder_gap_m`) behind the target's projected front surface, or at filled-hole pixels of the footprint
    (no owned point: a handle loop), are NaN. In trial 1, 1-3 % of the pot's and the lid control's samples lay at
    1.36-1.51 m inside the mask [M] (background past the silhouette: the depth camera and cam_a see it from different
    places, and through the handle loop). Masks are unchanged (B2 design).
109. **(2026-10-31, B3) G0 control runs (report only; not part of the B.12 outcome)**, asked for by the task brief
    ("plus whatever controls B.12 names (e.g. the old contact-frame input)"); B.12 itself names none. Per target: a
    census contact frame with 3-D contact (d3 <= 10 mm), largest target footprint first, whose naive mask is
    hand-free with valid depth >= 0.6 (else the smallest hand share <= 25 %); naive mask = target footprint minus
    MediaPipe hand capsules and depth occluders outside the partner's dilated footprint (the partner stays in the
    mask, as in the 29 Oct input whose mask was the library-render silhouette), largest component, no SAM2; seeds 0
    and 1; same pointmap rule. Changed after trial 1 (GT-free montages, no SAM 3D output): the first rule used the
    frame table's hand share, which is relative to the exclusive mask, and picked lid k276 with a hand on the lid; and
    the depth-occluder rule had removed the lid from the pot control (k24).
110. **(2026-10-31, B3) The G0 lid view is M9's first view, which on the clean bundle is not strictly hand-free.**
    PREREG B.12 asks for "M9's best separated, hand-free view". On the clean ep2 bundle no qualifying lid frame is
    hand-free: every frame has 1.3-1.7 % depth-occluder pixels at the lid's lower rim (no MediaPipe hand) [M], so M9's
    rule (hand-free first, else the largest visible area) takes k132 (dev bundle in B2: k118, hand-free). The montage
    shows the lid alone on the table, no hand. Used as is; M9 is not changed. No scan or eval number seen.
111. **(2026-10-31, B5 round 2) Self-ambiguity "trusted balls only" with standard Candidate objects.** PREREG A.3 V5
    and A.5 key 2 measure the self-ambiguity with trusted balls only, otherwise ball-free. The round-1 `score_pool`
    measured it on the mesh WITH untrusted balls when no ball-free mesh was supplied (the default path for Candidate
    objects, which had no such field; verifier's break input, synthetic). Now: untrusted balls and no ball-free mesh
    -> the value is unknown (`score.amb_unknown`: flip_risk None, flip_units None), which select.pick already treats
    as neither risky nor safe for V5 and last on key 2 (entry 60 (ii)); the row is flagged
    `amb_unknown_untrusted_balls_no_base` and a pick with it `flip_risk_unknown`. `Candidate` gets an optional last
    field `base_mesh = None` (backward compatible) so producers / markers.attach callers can pass the ball-free mesh;
    the ball count is max(declared, len(mesh.metadata['balls'])). An interpretation of A.3 / A.5 as frozen; no
    pre-registered test, threshold or constant changes. No scan or eval number seen.
112. **(2026-10-31, B5 round 2) Bootstrap replicate with an empty resampled block.** A.4's ratio estimator per block
    is undefined when a replicate's resampled frames of a block hold no held-out point; round 1 scored it R_k = 0 (a
    perfect fit), while the point estimate drops a block without points (nanmean). Now the replicate drops that
    block too (NaN replicate if no block is left) and SE_diff is the SD over the replicates where both E are
    defined. Pairing is kept (per-frame point counts are the same for every candidate). Latent on the public data:
    0 replicates hit it on the 33 clean public object-episodes of run 20261031-b4ext4-b61e8aa, K = 3 (verifier, [M,
    GT-free]). Interpretation of A.4; no constant changes. No scan or eval number seen.
113. **(2026-10-31, B5 round 2) select.pick input contract, V3 reference s, V1 source.** (i) `pick` takes the
    score_pool dict (kit_symmetric, gen_view_overlap and the pool flags come from it) or its rows (each carries them
    under `pool`); for untagged rows both keywords are required, and a keyword that contradicts the pool raises
    (round 1 defaulted both to False: V5 and the flip key would have applied to kit-symmetric objects). (ii) V3's s
    ("the route-A shell at t0", A.3): `shell_fsv` (the t0 shell's fsv_far from the main run, for the A.1
    t0-alternate re-runs), else `shell_cid`, else the SHELL row with t_mm == `t0_mm`, else the only SHELL row;
    several SHELL rows otherwise raise (round 1 took the first in input order); no SHELL -> pool flag
    `v3_no_shell_reference`. (iii) V1 computed on the in-memory mesh (no packer v1 supplied) flags the row
    `v1_in_memory` (A.3 V1 is defined on the shipped, packed mesh; B10 passes the packer's v1). Code contracts only;
    no pre-registered test, threshold or constant changes. No scan or eval number seen.
111. **(2026-10-31, B3) How the G0 report computes K-a / K-b (PREREG B.12 with the B.9 definitions)**, fixed before
    the box ran (`tools/g0_report.py` at 937f9d7, dry-run on a fake box output whose "generated" mesh was the SHELL
    itself): placement = the box's camA_T_mesh (SAM 3D layout, library compose_transform) times inv(camA_T_obj[k])
    only; remesh M10 then `pack.pack`; fsv_far and V2 from `score.py` on the clean ep2 bundle read by a dev process;
    the reference SHELL is `producers/shell.py` on the same bundle at the dev t0 (5.36 mm, `dev_constants.json`,
    because the frozen t0 of B13 does not exist yet); a run passes if fsv_far(c) - fsv_far(SHELL) <= 0.05 and V2 does
    not veto against the partner; K-a / K-b pass if at least half of the target's primary runs pass. Reported only:
    PCA extents of the placed mesh against the owned points' extents, on all owned points and on their largest 8 mm
    component (1.8 % of the clean ep2 lid's owned points lie outside it, up to 330 mm from the median [M], which
    inflates the all-points extent; seen in the dry run), share outside the grid, `physcheck.placement` (F-I1.9), montage.

## B4 round 2 (2026-10-31, fixes after B4 verification round 1)

Written 14:05-14:40 UTC, **after** the v4 run (`20261031-b4ext4-b61e8aa`) and its B.2a, B.3 and B.15 results and the
verifier's report were seen. No scan or eval number was seen; none bears on these entries. The v4 verdicts (B.2a FAIL,
B.3 FAIL, P22 falsified) are the pre-registered outcomes and are not changed by anything below (PREREG D.3). Round-2
entries carry labels `B4-R2.n` instead of numbers, because parallel sessions append to this file.

B4-R2.0. **Numbering and disclosure note.** Numbers 82 and 102 are each used twice: read B4's entries as "B4-82" (dev
    role `clean_run`) and "B4-102" (speed only; how B.15 is reported), B7's as "B7-82" and "B7-102". Number 111 is
    also used twice (B5 round 2 and B3; not B4's). Entries 95, 99, 100 and 101 were written after outputs were seen;
    each says so; none involved a scan or eval number and none changes a pre-registered verdict.
B4-R2.1. **Rule-B seed points = the proposal's samples that no other object owns** (supersedes the seed-point
    sentence of entry 86; applies to the fallback seed of entry 101 too). Entry 86 kept only frame-0 samples inside
    the chosen proposal that were provisionally o-owned or o-tied. Seen [M, GT-free, `<DATA>/gmg/b4fix/det_diag.py`:
    det masks, tracks, calib and v4 bundle points]: in ep23 both boards' proposals are whole-board masks (half-res
    areas 7016 / 7028 and 6804 cells; each covers 100 % / 95 % of the board's frame-0 footprint), but only 96 / 260 of
    their cells held a provisionally owned point of the board (IoU 0.013 / 0.038), so board 1's seed was 283 points
    (box 11 x 66 x 39 mm) and the 1.5 x guard clipped its component from 1864 to 335 voxels. SPEC section 7 calls the
    proposal itself the seed ("the frame-0 SAM2 proposal ... assigned exclusively"); the ownership filter was this
    builder's addition. Now: seed points = every frame-0 sample of o's cube inside the chosen proposal that is not
    provisionally owned by another tracked object (o-owned, o-tied and unowned samples; a sample owned by another
    object, or shared without o in its tie set, is excluded). The proposal choice (exclusive, holding o's projected
    origin, largest IoU with o's provisional footprint), the guard, its constants and every other rule are unchanged.
    The seed's category counts are stored (`crop.<o>.seed_in_proposal`, `seed_mine`, `seed_unowned`,
    `seed_other_excluded`). Affects the det-seeded episodes (v4: ep11, 22, 23, 26 pot, 31, 39, 41-45); rule-A episodes
    are unchanged. Not fixed by it: a proposal that is itself a partial mask (ep31 sweeper: it covers 64 % of the
    sweeper's frame-0 footprint), and a rule-A seed that already holds clutter (ep24 board 1: seed box 131 x 191 x
    372 mm, so the guard cannot act). Both are properties of SPEC's one-view seed and guard and are reported, not
    changed.
B4-R2.2. **Identity-test distance less dependent on the ICP subsample** (track_sanity `reg_chamfers`; SPEC section 7
    "symmetric chamfer in mm after rigid best-of-24 PCA-start ICP"). Seen (verifier, `verif_b4/cross_seed.py` [M]):
    with the round-1 distance (one 1500-point subsample, seed 0, chamfer on that subsample) the ep11 blue cup is
    flagged at seeds 0-2 and passes at seed 3; the ep22 blue cup is flagged at seed 0 only. Now: register() with
    subsample seeds 0-3 (24 PCA starts each, unchanged), each final transform's chamfer evaluated on the full
    4000-sample shells, the lowest wins; the split and cross tests both use it. The round-1 seed-0 values and verdicts
    are stored beside (`seed0`) and set no flag. No threshold or rule changes; the decision is still d_own < d_other.
    b4_identity runs the registrations on a fork process pool (3 workers; speed only).
B4-R2.3. **Census diagnostic: the gap between each frame's own owned points** (`contact.frame_gaps`; pass-4 census
    records gain `d3_frame_mm` and `sep3d_frame`). Seen (verifier, `verif_b4/perframe_gap.py` [M]): the census gap
    (whole-episode owned clouds placed by the tracks, the reading of the design probe `gen-first/contact_census.py`
    that SPEC M4 reuses) is <= 0.8 mm in every ep26 frame although the pot moves 208 x 206 x 56 mm relative to the
    rack; each frame's own points are > 20 mm apart in 17 of 79 frames (ep26) and 43 of 123 (ep27). The census rule is
    NOT changed: the per-frame reading misses contact hidden by occlusion (a seated lid's visible top lies far from the
    pot's visible wall), and SPEC names the probe's logic. No rule, flag or seed reads the new fields. b4_b2a reports
    beside the pre-registered B.2a a diagnostic leakage (`diag_frame_gap`): reference from the `sep3d_frame` frames,
    test frames = census contact frames outside them. It is not B.2a and changes no verdict.
B4-R2.4. **Interface deviations from the SPEC section 7 table (not recorded in round 1).** M2: `extract_episode`
    returns the in-memory `Bundle`, not `bundle_dir`; `out_dir` is ignored (b4_extract saves the bundle after M3 has
    added good frames, sanity, rest planes and shells); extra keywords `aux_dir`, `log`, `roster`; `seed_masks` is the
    det-dump path. M4: `census(objs, poses, frames, K)` works on centroid clouds; SPEC's `census(bundle)` is
    `census_bundle(bundle)`, which returns the census fields only: `j_mm`, `co_moving`, `co_moving_unresolved`,
    `tie_break`, `band_mm` and `census_unstable` are added by extract_joint to the pass-4 records it stores in
    `meta['contact']` (what later steps read). M3: `check(bundle, obj)` returns good, flags, below_table_frac,
    block_resid_mm and extra fields, but not identity_split / identity_cross: those need the partner's shell and all
    public bundles, so b4_extract writes `identity_split` and b4_identity writes `identity_cross` into
    `meta['sanity'][obj]`. Round 2 adds the pass-2/3 helpers (`det_candidates`, `det_seed_select`,
    `seeded_component`, `crop_guard`, `resolve_ties`, `pair_flags`) as module functions so tests reach them; apart from
    B4-R2.1 they compute what round 1 computed inline. No result changes.
B4-R2.5. **Run v5** (`<DATA>/gmg/runs/20261031-b4ext5-a776e8e`, all 20 public episodes on one commit, clean,
    strace-audited, 2 local streams because of disk). v4 stays the pre-registered B4 record; v5's B.2a, B.3 and B.15
    numbers are post-hoc [M] (after the v4 numbers were seen) and are reported beside v4, never in place of it. Which
    bundle set later steps consume (v4 as pre-registered, or v5 without the known crop defect) is left to the
    orchestrator / owner; the C.2 anchor table is given for both.
112. **(2026-10-31, B3) G0 post-hoc diagnostics (not pre-registered).** After the B.12 report (all 8 runs fail the
    fsv_far term, all pass V2), `tools/g0_diag.py` re-aligns each layout-placed mesh to the target's owned core by a
    trimmed ICP from the layout start (variant similarity; then variant rigid_extent, added after the first gave lid
    scales x1.32-1.38) and recomputes the B.9 measures. Reported beside the frozen outcome, never instead of it; the
    B.12 outcome (NOT SUPPORTED) and every PREREG threshold are unchanged. The finding that K-a's measure would pass the
    contact-frame pot+lid blob is recorded as an open problem for the orchestrator / owner (no PREREG F entry: scan-free
    but post-hoc, and K-a numbers have been seen). Seeds: PREREG B.12's 0 and 1 (the 29 Oct probe used 42 and 7).
    No scan or eval number seen.
