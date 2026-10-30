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
