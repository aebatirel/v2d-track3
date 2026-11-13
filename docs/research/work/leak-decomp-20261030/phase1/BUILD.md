# Phase 1 build: GPU perception on the 20 public episodes (30 Oct 2026, ~17:45 UTC; review fixes ~18:20 UTC)

Owner approval: Phase 1, ~14:50 UTC ("go ahead with phase"). Plan: `../PLAN.md` §3 Phase 1, §7 B4. **Nothing is
launched.** Job strings and cost: `JOBS.txt`. Labels: [M] measured, [E] estimate. The fixes from the integrity and
mechanics reviews (both GO) are in §6.

## 1. What a box does
`ops/jobs/perc_leak.sh` runs these steps on each public episode in `EPS`, on one box and one commit:
- **Before any download** it checks that the public files perc2 reads exist (`calib.json`, `ep<N>.parquet`, the
  a/b/c videos, every object's scan); if not, it re-runs `fetch_data.sh` once, then exits 1. It loads Grounding DINO
  once (5 tries) so every perc2 run can load it from the local cache with `HF_HUB_OFFLINE=1`.
- **Inputs.** It downloads the store's depth cache `cache/depth/public/ep<N>/depths_fs0.5.npy` and the refine
  inputs' two hands files, one file per download, in the background. `tools/leak_p1.py inputs` then checks them
  against `inputs.tsv`: the cache's size and shape, its frame-0 sha256, the hands md5 and the frame counts. It writes
  `depth0.npy` and `hands/`.
- **perc2, once per arm,** with the eval pipeline's settings (`KF_MIN=120`, all else perc2's defaults; plus
  `HF_HUB_OFFLINE=1`, which changes only where Grounding DINO is loaded from), on that one cache:
  - `o` = P_o, `MESH_DIR=$LIB` (library_v3), into `perc2/`;
  - `s` = P_s, `MESH_DIR` unset, so perc2 tracks with the organiser scans, into `perc2scan/` [oracle];
  - `o2` = the P_o repeat, only on `REPEAT` episodes, into `perc2rep/`.
- **Bundle.** `leak_p1.py bundle` writes `bundle.json`, which records per arm:
  - the template files perc2 resolves for that arm's environment (perc2's own `D`/`MESH_DIR`/`scan_path`/`mesh_path`,
    taken from its source), with their md5;
  - depth reuse (the cache's inode, size and mtime are unchanged, and `depth ready` comes in under 60 s);
  - the arm's camera vs P_o;
  - `perc_log_inference.txt`, the log cut before perc2's mocap-scoring lines;
  - `gdino`: no `grounding unavailable` line in the log. An arm without it is not ok (`NO-GDINO` in the summary).

  It also tars the episode into `bundle_ep<N>_oracle.tar`, without any `result.json` or `log.txt` (mocap scores), so
  a later pull of one episode's inference inputs is one download.
- **End of job.** `summary.json` and `RESULT` lines go to `job.log`. The job pushes nothing itself: `run_job.sh`'s
  final `push-run` uploads `results/leak_p1/` once, plus the watchdog's 30-min interim pushes. The job exits 3 if any
  arm failed, so `run_job.sh` holds the box 30 min for debugging.

## 2. Changes
| File | Change |
|---|---|
| `ops/jobs/perc_leak.sh` | new (B4). Based on `perc_ab.sh` (perc2 called directly on a linked cache) and `oracle_twins.sh` (the `-orc` run-id rule, `ensure_gdino`, log/label). It refuses: a run id that `tools/no_oracle.py` does not refuse, an unknown arm (P_gf is Phase 1b), `REPEAT` outside `EPS`, an episode not in `inputs.tsv`, a missing template, and missing public data after one `fetch_data.sh` re-run. It makes a relative `LIB` absolute, because perc2 `chdir`s to FoundationPose before it loads the templates (`perc2.py:178-184`) |
| `tools/leak_p1.py` | new: `inputs`, `bundle`, `summary`, `templates` |
| `ops/box/store.sh` | new `pull-files <path>...`. A single-file `hf download` is one `hf_hub_download`; `--include`, or several files in one call (`pull-depth`, `pull-run`), lists the whole store first (`huggingface_hub/cli/download.py`: one filename → `hf_hub_download`, otherwise `snapshot_download`). Each try is cut after `PULL_TIMEOUT_S` (1200 s); 5 tries with backoff `PULL_RETRY_S`·i. Purely additive |
| `tools/no_oracle.py` | B8 (PLAN §7) landed in e0f53ce, from the Tier A workflow: `BAD` also refuses `perc2scan`, `perc2gf`, `leak_p1`-style folders, `hT`, `scanlib` and the public scans. Not changed by this build |
| `phase1/scripts/balance.py` | rewritten. The WIP version searched all 3^19 splits and never finished; this one is greedy plus moves and swaps. Result: 4337 / 4338 / 4337 arm-frames per box |
| `phase1/mock/*` | CPU mock and real-code checks (§3, §4); outputs in `mock/out/` |

**Reviewed WIP from 2db247c:**
- Kept: `inputs.tsv` and `scripts/make_inputs.py`. Re-running `make_inputs.py` on the refine mirror reproduces
  `inputs.tsv` byte for byte [M].
- Replaced: `balance.py`.
- Left alone: the Tier A WIP (`xstar_fit.py`, `frame_xform.py`, `oracle_poses --xform`). Its own workflow is still
  running and editing those files.

## 3. Real-code checks of perc2.py on this VM, local public data (`mock/realcheck.sh` → `mock/out/realcheck.txt`)
The only change made to perc2.py is the path mapping `/content` → scratch (10 lines).

- **Template switch [M].** `MESH_DIR` appears only in `mesh_path`, and only `load_mesh` calls it (`perc2.py:47-52, 184`).
  Scoring always uses `scan_path` (`:515`). I ran perc2's own functions for the 10 Phase-1 objects:
  - with `MESH_DIR` unset, every object resolves to `<D>/mesh/<obj>/<obj>.glb` (`_visual.glb` for the sweeper and
    both wooden pieces), with D = `/content/t3`;
  - with `MESH_DIR=''`, the result is the same;
  - with `MESH_DIR=library_v3`, every object resolves to `library_v3/<obj>.glb`.

  Every md5 differs between the two sets. The scans have about 98k faces each; library_v3 has 4–33k.
- **Depth cache [M].** I built an ep11 cache at the store's size (876,800,128 B). Its frame 0 is the store's frame 0:
  the sha256 equals `inputs.tsv`. With that cache, the real perc2.py logs `depth ready 137` at 4.5 s and never enters
  the FoundationStereo branch. The cache's stat and md5 are unchanged afterwards. As a control, without the cache it
  goes into that branch (`perc2.py:106`), and fails there because this VM has no FoundationStereo. perc2 stops later in
  both runs, because this VM has no stereo videos and no GPU.

## 4. CPU mock (`mock/run_all.sh` → `mock/out/`; stub perc2 and stub `hf`, everything else real)
- **The three JOBS.txt strings run to rc 0.** Every `check.py` assertion passes (`mock_box{a,b,c}.txt`):
  - all 20 bundles are ok;
  - perc2 saw `MESH_DIR` unset only in `perc2scan`, and `$LIB` in `perc2` and `perc2rep`;
  - `KF_MIN=120`, `SPLIT=public`;
  - the cache already existed for every run, and the bundle's template paths equal what the stub perc2 resolved;
  - `o2` ran only on REPEAT episodes;
  - hands md5 and frame-0 sha256 equal `inputs.tsv` on all 20 episodes;
  - `perc_log_inference.txt` holds no scoring lines.
  - Grounding DINO is loaded once per box before perc2 (2 `from_pretrained` calls, online), and all 50 perc2 runs
    get `HF_HUB_OFFLINE=1`; every arm records `gdino` true.
- **Store traffic.** 21 / 21 / 18 single-file downloads (3 per episode), 0 listings, 1 upload per box.
- **Push list.** 200 / 227 / 200 files, 122.8 / 125.9 / 109.9 MB:
  - no depth cache and no symlink; the download log is `results/leak_p1/leak_pull.log`;
  - every bundle file and every tar is present; each tar equals its folder without `result.json` and `log.txt`.
- **Guard (`tools/no_oracle.py`, with B8).**
  - Refuses 100 % of pushed files by their store path `runs/<rid>/…`, and every bare `bundle_ep<N>_oracle.tar` name.
  - Refuses every bare P_s path as a tar member has it (`ep<N>/perc2scan/…`: 64/64, 67/67, 57/57) and bare
    `perc2gf` paths (`mock_b8.txt`); the bare P_o paths (`ep<N>/perc2/…`, `perc2rep/…`) are accepted, as intended.
- **Faults** (`mock_faults.txt`), all handled as intended. Job rc 3, as expected.
  - A 429 on a depth download: retried, then ok.
  - A corrupted hands file: md5 flagged; perception still runs.
  - perc2 crashing on one arm: arm FAIL, no tracks.
  - A crash after `poses.npz`: `poses_world_vo.npz` rebuilt, arm marked FAIL.
  - A truncated cache: inputs rc 2, perception skipped, reported.
- **Grounding DINO** (`mock_gdino.txt`, stub `transformers`):
  - the first download fails (429): retried, cached on try 2, all 5 perc2 runs offline, bundles ok (rc 0);
  - an injected `grounding unavailable` on one arm: that arm FAIL `NO-GDINO`, bundle NOT OK, job rc 0;
  - every download fails: 5 tries, one `NOT available` line, both arms `NO-GDINO`, job rc 0.
- **Public data** (`mock_data.txt`):
  - a missing video with a failing `fetch_data.sh` re-run: rc 1, 0 store downloads, 0 perc2 runs;
  - the same with a re-run that restores it: rc 0, 2 perc2 runs;
  - a missing scan: rc 1, 0 downloads, 0 perc2 runs.
- **Refusals** (`mock_refusals.txt`). Each of these gives rc 1 with no download and no perc2 run: run ids that
  `tools/no_oracle.py` accepts (`20261030-p1a-…`, `P1-orc-mocksha`, `x20261030-orcP1a`), arm `gf`, `REPEAT` outside
  `EPS`, ep 5. A relative `LIB` reaches perc2 as an absolute path.
- **Download timeout.** `store.sh pull-files` with an `hf` that hangs on the first try and `PULL_TIMEOUT_S=3`: the try
  is cut after 3 s, logged, retried, rc 0 (ad hoc test, not in `run_all.sh`).

## 5. Risks and open items
1. **B8 is in `tools/no_oracle.py`** (e0f53ce, Tier A workflow). The bundles are refused by the `-orc` run id, the
   `oracle` tar name and, once unpacked, the `perc2scan` folder name. The job refuses any run id the guard accepts.
2. **P_s run time is not measured** [E 1.0–2.0× P_o]. The scans have 3–23× the faces of library_v3. The cost upper
   bound applies 2× to every `s` run. There is no fixed limit; the watchdog counts GPU use as progress.
3. **The code date differs from the refine-input tracks** (25 Oct guard/sweep runs, library_v2 sweeper). P_o will
   therefore not equal refine P. This is intended: P_o and P_s share one commit, box and cache. Report Tier A on both.
4. **The hands were made on the 21/25 Oct cameras.** They stay valid only if each arm's `world_T_cam` matches the
   refine one (expected ≤ 1e-6; it was ≤ 5.2e-8 before [M]). This is checked on CPU after download, with no extra
   box traffic. Arms agree with each other in `bundle.json`.
5. **Mocap scores stay out of the bundle tar.** `result.json` and the end of `log.txt` hold perc2's mocap scores; the
   tar leaves both out, so the Phase-2 input has none (P_o's cell c1 reads no ground truth). Both stay in the folder
   push for diagnostics, and `job.log` quotes P_s's scan-frame vo AUC (oracle run). Downstream inference reads only
   `poses*.npz`, `vo.json`, `depth0.npy`, `hands/` and `perc_log_inference.txt`.
6. **The depth cache could change in the store.** A frame-0 sha mismatch is flagged and the episode still runs on
   that one cache. A size or shape mismatch skips the episode.
7. **HF 429.**
   - Per box: setup (env restore lists once), 18–21 single-file downloads, 1–3 interim pushes and one final push.
     Start the boxes 10 min apart.
   - A failed final push waits 60 min and retries (+~$1.5 per box).
   - The watchdog's `PUSH_MIN` cannot be set from the job string.
8. **The noise floor is within-box only.** o and o2 run on the same box, one after the other.
9. **ep0 and ep23.** ep0 is the known scan-template frame-0 failure; ep23 is the identity swap. Both run and are
   reported, not fixed.
10. **Cost estimate.**
    - Now ≈ 3 box-h, ≈ $4.4 (range $2.8–7.4), vs the plan's $11–15.
    - One box would cost ≈ $2.1–4.5 and use a third of the setup traffic, at about twice the wall time.

## 6. Review fixes (30 Oct ~18:20 UTC; both reviews GO)
| Review fix | Change | Test (`mock/out/`) |
|---|---|---|
| integrity F1 | the run id must be refused by `tools/no_oracle.py`, else exit 1 (was a looser `*-orc*` match) | `mock_refusals.txt`: `P1-orc-mocksha`, `x20261030-orcP1a` rc 1, 0 runs; the JOBS ids run |
| integrity F3 | tars exclude `result.json`, `log.txt`; tar stderr into `job.log`; `check.py` compares tar = folder minus those | `mock_box{a,b,c}.txt`: ALL CHECKS PASS |
| integrity F2 / B8 | already in `tools/no_oracle.py` (e0f53ce); no edit. `check.py` now requires bare `perc2scan` refused | `mock_b8.txt`, `mock_box*.txt` |
| mechanics F1 | Grounding DINO loaded once after `ensure_gdino` (5 tries); `prefetch &` moved after the pip install; perc2 with `HF_HUB_OFFLINE=1`; `leak_p1.py` records `gdino` per arm, requires it for ok, prints `NO-GDINO` | `mock_gdino.txt`; `check.py` (16/18/16 runs offline) |
| mechanics F2 | public data checked before any download; `fetch_data.sh` re-run once; else exit 1; the mock creates placeholder `/content/t3` files | `mock_data.txt` |
| mechanics F4 | `timeout ${PULL_TIMEOUT_S:-1200}` on each `pull-files` try; the pull log under `results/leak_p1/` (watched by the stall watchdog) | ad hoc hang test (§4); `mock_faults.txt` |
| mechanics F5 | this file, `JOBS.txt` and the job's comments no longer say B8 is pending | - |

A `NO-GDINO` arm makes its bundle NOT OK but leaves the job rc 0 (the summary exits 3 only when an arm did not run),
so the box does not hold; read the `RESULT` lines for `NO-GDINO` after the run. The mechanics review's F3 (start
`prefetch` after the pip install) is part of F1 above.
