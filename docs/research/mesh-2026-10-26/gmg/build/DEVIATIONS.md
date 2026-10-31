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
