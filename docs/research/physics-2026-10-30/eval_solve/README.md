# Eval solving for pack 10 (prepared 31 Oct 2026 ~16:30–17:30 UTC; NOT launched)

Launch condition: the pre-registered clean re-test (`../physics-solver.md` §9) reads **"signal"**. The owner
pre-approved eval solving in that case (~$15 [E]). On "no signal" or INCOMPLETE nothing here runs.

Integrity: eval episodes have no ground truth. The job reads our stored references, our URDFs/meshes and the pack
builder's table only. Every score is sim_vs_ref against OUR reference. Nothing opens mocap or the `pose` field of
`observation.objects`.

Markers: [M] measured, [E] estimate, [H] hypothesis.

## 1. Inputs: the 15 grasp-lock eval episodes as packed [M]

Source: focused-pascal's `docs/research/work/masses-eval-20261031/packed_refs.json` (commit 71bac00 on
`claude/focused-pascal-2nz9s1`). Byte copy here: `packed_refs.json`, md5 `a7ed39d65e522c22aa9d04bb22d15a6e`.
The pack builder confirmed this scope on 31 Oct ~16:40 UTC: 15 grasp-lock evals. The standard-learner evals
(1, 19, 25, 28, 30) are out of scope; the job refuses them.

Check on 31 Oct ~16:35 UTC (CPU, `scripts in tools/physics_solve/tests/eval_solve/`, single-file HF downloads):
- all 15 references download and match the table's md5;
- every object URDF and every mesh it names is present in the stored asset copy;
- every support stage is present;
- all masses are the 0.3 kg placeholder.

| eval | learner | reference the packed policy trained on (store path) | md5 | frames | sim assets | packed policy run |
|---|---|---|---|---|---|---|
| 1 | standard learner (out of scope) | – | – | – | – | – |
| 3 | grasp lock | `runs/20261024-pack-31ef267/refs/glockt/ep3/processed/sequence_id=t3_ep003/robot_name=sharpa_wave/ref_gl_ilc.parquet` | `732e44ea7bab2ad29256ebb072996adc` | 313 | own copy `refs/sf/ep3/assets` (library_v3) | 20261024-seed43-61101f5 |
| 5 | grasp lock | `runs/20261024-pack-31ef267/refs/glockt/ep5/processed/sequence_id=t3_ep005/robot_name=sharpa_wave/ref_gl_ilc.parquet` | `aa2f4fc5b72c927ddb8affec95000309` | 288 | own copy `refs/sf/ep5/assets` (library_v3) | 20261024-seed43-61101f5 |
| 6 | grasp lock | `runs/20261024-pack-31ef267/refs/glockt/ep6/processed/sequence_id=t3_ep006/robot_name=sharpa_wave/ref_gl_ilc.parquet` | `50445bc36436bab8b46c6d36cc267e02` | 243 | own copy `refs/sf/ep6/assets` (library_v3) | 20261024-pack-31ef267 |
| 8 | grasp lock | `runs/20261025-evb0810-ee7ba8e/refs/glockt/ep8/processed/sequence_id=t3_ep008/robot_name=sharpa_wave/ref_gl_ilc.parquet` | `9424b5a1a3f7257566c856a6cc34f745` | 219 | own copy `refs/sf/ep8/assets` (library_v3x) | 20261025-evb0810-ee7ba8e |
| 10 | grasp lock | `runs/20261026-gl10A2-5e0e100/refs/glockt/ep10/processed/sequence_id=t3_ep010/robot_name=sharpa_wave/ref_gl_ilc.parquet` | `1a5003d94852c275519066645a1b9869` | 161 | shared `/content/assets` = make_assets library_v3 + `meshes/carve/ev10`, built by the job | 20261026-gl10A2-5e0e100 |
| 14 | grasp lock | `runs/20261025-evb1420-ee7ba8e/refs/glockt/ep14/processed/sequence_id=t3_ep014/robot_name=sharpa_wave/ref_gl_ilc.parquet` | `10d5f3ba6b7368ed30dad9d0c9c30df1` | 158 | own copy `refs/sf/ep14/assets` (library_v3) | 20261025-evb1420-ee7ba8e |
| 15 | grasp lock | `runs/20261024-pack-31ef267/refs/glockt/ep15/processed/sequence_id=t3_ep015/robot_name=sharpa_wave/ref_gl_ilc.parquet` | `1d7f2d1c086f825c575d8845131222c9` | 166 | own copy `refs/sf/ep15/assets` (library_v3) | 20261024-seed43-61101f5 |
| 16 | grasp lock | `runs/20261024-pack-31ef267/refs/glockt/ep16/processed/sequence_id=t3_ep016/robot_name=sharpa_wave/ref_gl_ilc.parquet` | `f7e2ea9260106425be6163553aac5af9` | 173 | own copy `refs/sf/ep16/assets` (library_v3) | 20261024-seed43-61101f5 |
| 19 | standard learner (out of scope) | – | – | – | – | – |
| 20 | grasp lock | `runs/20261025-evb1420-ee7ba8e/refs/glockt/ep20/processed/sequence_id=t3_ep020/robot_name=sharpa_wave/ref_gl_ilc.parquet` | `4d06d8d42d57d84b1d25a166e8a90adc` | 202 | own copy `refs/sf/ep20/assets` (library_v3) | 20261025-evb1420-ee7ba8e |
| 25 | standard learner (out of scope) | – | – | – | – | – |
| 28 | standard learner (out of scope) | – | – | – | – | – |
| 30 | standard learner (out of scope) | – | – | – | – | – |
| 32 | grasp lock | `runs/20261026-fr32s46b-5e0e100/refs/glockt/ep32/processed/sequence_id=t3_ep032/robot_name=sharpa_wave/ref_gl_ilc.parquet` | `36e600c8346f9d2bd89dc47447ea55fc` | 259 | own copy `refs/sf/ep32/assets` (library_v3) | 20261026-fr32s46b-5e0e100 |
| 33 | grasp lock | `runs/20261026-fr3233s43-6a8a0e2/refs/glockt/ep33/processed/sequence_id=t3_ep033/robot_name=sharpa_wave/ref_gl_ilc.parquet` | `2a7173ab1d4248433bd049bc43f6878a` | 348 | own copy `refs/sf/ep33/assets` (library_v3) | 20261029-rcB-34bf6ae (REUSE_REF on fr3233s43's reference) |
| 35 | grasp lock | `runs/20261024-pack-31ef267/refs/glockt/ep35/processed/sequence_id=t3_ep035/robot_name=sharpa_wave/ref_gl_ilc.parquet` | `bc064b462f0e9791ec77f22dbb5a2344` | 421 | own copy `refs/sf/ep35/assets` (library_v3) | 20261024-pack-31ef267 |
| 36 | grasp lock | `runs/20261024-pack-31ef267/refs/glockt/ep36/processed/sequence_id=t3_ep036/robot_name=sharpa_wave/ref_gl_ilc.parquet` | `36e60e15163f47486e6bcf85b93fb22e` | 407 | own copy `refs/sf/ep36/assets` (library_v3) | 20261024-pack-31ef267 |
| 37 | grasp lock | `runs/20261024-pack-31ef267/refs/glockt/ep37/processed/sequence_id=t3_ep037/robot_name=sharpa_wave/ref_gl_ilc.parquet` | `b78747bb1d941fa56121886cc15ec225` | 151 | own copy `refs/sf/ep37/assets` (library_v3) | 20261024-pack-31ef267 |
| 38 | grasp lock | `runs/20261024-pack-31ef267/refs/glockt/ep38/processed/sequence_id=t3_ep038/robot_name=sharpa_wave/ref_gl_ilc.parquet` | `33d3f4e217426b797d0371849f9ee1fd` | 263 | own copy `refs/sf/ep38/assets` (library_v3) | 20261024-pack-31ef267 |

Notes:
- **Assets.** 14 of the 15 references name their own stored asset copy (`/content/refs/sf/ep<N>/assets/...`). The job
  pulls those files byte for byte, so the solver sees exactly the training's simulator objects.
- **Eval 10** names the shared `/content/assets`. The job rebuilds it as `mass_eval.sh` does: `make_assets.py
  meshes/library_v3 /content/assets --pieces meshes/carve/ev10`, 0.3 kg. Equivalence checks [M]:
  - gl10A2's own `job.log` prints, for both cups, the same vertex counts, COM (0.01 cm resolution) and piece counts
    (53 / 49) as today's build;
  - every mesh and piece file is byte-identical across make_assets versions d7576a4 / a0baeef / HEAD;
  - the URDFs differ only in a comment from a0baeef's;
  - d7576a4's URDFs have a different COM: that version did not read the pieces' `inertia.json`, and gl10A2 did not
    use it.
- **Solver gate.** It is active on almost every frame (a hand within 10 cm of a moving object): 3,627 of 3,772 frames;
  374 of 382 G2-size replans plan. So the solve time scales with the episode length.
- **C0 meshes** change only the packed submission meshes. They bring no simulator change.
- **Masses** enter pack 10 later via MA_ARGS. **[H] caveat:** the solver plans at 0.3 kg, the trained references'
  mass. If Masses v2 ADOPTs and pack 10 trains with realistic masses, the solved plans were found under other object
  dynamics. Pack 10's per-episode GT-free rule (its own rollouts under its own masses) is what catches a mismatch.

## 2. The job: `ops/jobs/eval_solve.sh`

Per episode:
1. Pull the table's files: the reference, the support stage and the asset copy. Each is one single-file download
   (`store.sh pull-files`, the same text as focused-pascal's).
2. Build `/content/assets` only if a reference names it.
3. `tools/physics_solve/eval_inputs.py check`:
   - md5 = the table's;
   - objects and asset root as the table;
   - every URDF and mesh present;
   - the stage that FlashCHORD loads is present;
   - writes md5s of all of them.
4. Make a byte copy `refs/evsolve/ep<N>/processed/<seq>/<robot>/ref_in.parquet`, plus the stage.
5. Run the 64-copy jitter check of the input (G2's check: seed 0, 0.5 mm / 0.005 rad).
6. Run the official zero-action replay and `rest_check` of the input.
7. Solve at G2 scale: the default `SOLVE_ARGS` = `physics_solve_rl.sh` `G2_ARGS` byte for byte, pace 14.4 s/frame,
   hard deadline 18 s × frames. Output: `ref_ps.parquet` (+ `_solve.json/.npz/.log`) next to `ref_in.parquet`.
8. Run the zero-action replay, `trace_score` and `rest_check` of the output. These are the files `glock_public.sh`
   REUSE_REF needs.
9. Run the 64-copy jitter check of the output: the same noise draws as the input's (common random numbers).

At the end: `tools/physics_solve/eval_solve_summary.py` → `results/eval_solve/{summary.json, handoff.tsv,
handoff.md}`, then a store push.
- Runs 2 episodes at a time, longest first. This is the concurrency G2 ran safely: two 4,096-world solves on one 96 GB
  card. One jitter run goes first, alone, so the CUDA kernels compile once.
- The stall watchdog, self-destroy and interim pushes are the standard `run_job.sh` / `watchdog.sh` ones. The solver
  writes its log line by line under `/content/refs`, and the GPU stays busy.
- Exit 0 if at least one episode was solved (failures are listed in `summary.json`); 1 if none was.
- **Eval 10 override** (if the ep11 gate passes and pack 10 trains eval 10 on V4p):
  - `REF_EP10=<store path of the V4p parquet>`;
  - its stage `<base>/reconstructed_stage/t3_ep010_support.usda` is pulled automatically (or set `STAGE_EP10`);
  - `MD5_EP10=<md5>` is checked when given;
  - if the V4p reference names its own asset copy instead of `/content/assets`, list the files in
    `FILES_EP10="runs/... runs/..."`. The check refuses any missing URDF or mesh.
- Other knobs: `EPS PAR JK DLPF PACE SOLVE_ARGS DEV ASSET_LIB ASSET_PIECES TAB`.

## 3. Box plan and cost [E]

Measured basis (G2, box 20261030-psolverl-04301a2, $1.467/h):
- ep2: 343 frames in 3,952 s (11.5 s/frame);
- ep12: 181 frames in 2,471 s (13.7 s/frame);
- the two ran concurrently on one GPU, with no pacing and no deadline hit.

Planning figures:
- 11.5–14.4 s per frame per solve (pace cap), 2 at a time;
- a hard bound of 18 s/frame (deadline);
- +4 min per episode for 2 jitter checks, 2 replays and env builds;
- +0.6 h per box for setup (snapshot restore), pulls, kernel compile and push.

Total 3,772 frames. Split balanced longest-first over two slots:

| box | episodes (launch order irrelevant; the job sorts) | frames | wall expected (11.5–14.4 s/frame) | worst (deadline) |
|---|---|---|---|---|
| evsolve1 | 35 36 33 20 16 15 37 | 1,868 | 3.9–4.7 h | 5.6 h |
| evsolve2 | 3 5 38 32 6 8 10 14 | 1,904 | 3.9–4.7 h | 5.6 h |

- **Cost (2 boxes at $1.1–1.5/h):** expected 7.8–9.4 box-hours ≈ **$9–14**; worst case 11.3 box-hours ≈ $12–17.
- 3 boxes (1,251–1,267 frames each) would end in 2.9–3.5 h (worst 4.2 h), but cost about the same or more ($10–19)
  because of the extra setup. Two boxes is the recommendation.
- **Timing:** launched ~23:00 UTC, done ~03:00–04:45 UTC. That leaves room for one full re-run before the 1 Nov 14:00
  UTC cut-off.
- **Offers:** prefer RTX PRO 6000 WS/S over Max-Q. A slower card does not lengthen the run (pace and deadline bound
  it) but lowers the iterations per replan, i.e. the search quality.
- **Eval 10 timing:** if V4p's store path is not known at launch, drop 10 from box 2 and run it later alone (161
  frames ≈ 0.6 h solve + 0.6 h setup ≈ $1.3–1.8).

Launch strings (`<sha>` = the commit that holds this job; ledger `planned` line per box first, as usual):
```bash
ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer1> 20261101-evsolve1-<sha7> \
  'EPS="35 36 33 20 16 15 37" bash ops/jobs/eval_solve.sh'
ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer2> 20261101-evsolve2-<sha7> \
  'EPS="3 5 38 32 6 8 10 14" bash ops/jobs/eval_solve.sh'
# box 2 if pack 10 trains eval 10 on the V4p reference:
#   'EPS="3 5 38 32 6 8 10 14" REF_EP10=runs/<run>/refs/<...>/ep10/processed/sequence_id=t3_ep010/robot_name=sharpa_wave/<file>.parquet MD5_EP10=<md5> bash ops/jobs/eval_solve.sh'
```

## 4. Hand-off to pack 10 (format)

Per box: `runs/<run>/results/eval_solve/handoff.tsv`, `handoff.md` and `summary.json`. Also copied into the job log.

One row per episode:

| field | meaning |
|---|---|
| `ep`, `status` | solved / failed / dropped (reason in `summary.json`) |
| `input_store_path`, `md5_in` | the reference the packed policy trained on (table md5, or the REF_EP override) |
| `solved_store_path`, `md5_out` | `runs/<run>/refs/evsolve/ep<N>/processed/<seq>/<robot>/ref_ps.parquet`; `ref_in.parquet` (the byte copy of the input) sits next to it |
| `stage_store_path` | `runs/<run>/refs/evsolve/ep<N>/reconstructed_stage/<seq>_support.usda` (= the input's stage, md5 in `summary.json`) |
| `asset_root`, `asset_digest` | the asset root the solved reference names (unchanged from the input), and the md5 digest of every URDF and mesh file used |
| `jit_in_mean/sd`, `jit_ps_mean/sd`, `delta` | GT-free check, as in G2: 64-copy jittered zero-action sim_vs_ref of the input and of the solved reference, same noise draws; delta = solved − input |
| `nominal_in`, `nominal_ps` | copy 0 (no noise) of each |
| `frames_edited`, `deadline_t` | how much the solver changed; the frame at which the deadline stopped optimisation (None = never) |
| `rest_check_ps` | store path of `rest_check_ps.json`; `zero_score_ps.txt` sits beside it |

`summary.json` also carries, per episode:
- the packed policy's run, checkpoint and sha256;
- solve statistics (wall time, rollbacks, paced replans, mean iterations);
- `changed_columns`, which must be a subset of `robot_<side>_{wrist_position, wrist_wxyz, finger_joints}`.
  `robot_<side>_frames` (the RL tracking target), the object reference and `object_urdf_paths` are unchanged.

To train on a solved reference, use the G3 placement (`physics_solve_rl.sh`):
- `ref_ps.parquet` becomes the ONLY parquet in `refs/glockt/ep<N>/processed/<seq>/<robot>/`, named
  `ref_gl_ilc.parquet`;
- the stage goes to `refs/glockt/ep<N>/reconstructed_stage/`;
- `rest_check_ps.json` becomes `results/glock_public/ep<N>/rest_check.json`;
- the asset copy `refs/sf/ep<N>/assets` comes from the source run, unchanged. Eval 10's `/content/assets` is built as
  in the job.

No verdict is attached. Pack 10's per-episode GT-free rule decides what is packed (§9 "Actions").

## 5. CPU tests (31 Oct, this container) [M]

Scripts and logs: `tools/physics_solve/tests/eval_solve/`.
- `bash -n` (`eval_solve.sh`, `store.sh`, test scripts) and `py_compile` (`eval_inputs.py`, `eval_solve_summary.py`,
  `fcstub.py`): pass.
- **Real solver, tiny scale, real eval reference** (`cpu_solve_ep37.sh`; eval 37, md5 b78747bb; stored asset copy;
  `--workers 0`, i.e. the CUDA code path on the CPU; 8 worlds = 4 candidates × 2 copies, horizon 8, 2 iterations,
  jitter k = 4):
  - input check passes;
  - jitter of the input: 0.890 ± 0.006, nominal 0.948;
  - solve 116 s;
  - fresh load bit-identical;
  - official zero replay of the output equals the solver's truth (0.9470 / 0.9470);
  - jitter of the output: 0.938 ± 0.017;
  - only `robot_right_{finger_joints, wrist_position, wrist_wxyz}` changed, on 11 frames;
  - summary and hand-off written.
  - The one test-side change: `object_urdf_paths` in a copy point at the local asset copy (no `/content` here). It was
    checked to be the only differing column.
  - The tiny-scale numbers are a smoke test, not a result.
- **Job dry runs** (`dryrun.sh`: `/content` → a scratch root; the store is a local mirror of REAL store files; the GPU
  tools are stubbed by `fcstub.py`; `eval_inputs`, `make_assets`, `trace_score`, `rest_check` and the summary are real):
  1. evals 37 / 10 / 8 / 35:
     - all solved;
     - eval 10's `/content/assets` built (library_v3 + ev10);
     - order longest first;
     - md5s in the hand-off equal the table's;
     - push listing includes `refs/evsolve` and `results/eval_solve`.
  2. Failure modes, 40 s stub solves:
     - eval 1 refused (standard learner);
     - eval 14 refused (corrupted download → md5);
     - eval 3 dropped (a missing asset file);
     - eval 37's solve fails;
     - 36 and 38 solved;
     - never more than 2 solves at once;
     - exit 0 with the failures listed.
  3. `REF_EP10` override with the right md5: solved, input path = the override. With a wrong `MD5_EP10`: refused,
     exit 1.
- **CPU zero-action replays vs the training boxes' stored scores** (`cpu_zero_ep10.sh`):
  - eval 37 0.948 (CPU) vs 0.921 (GPU, stored);
  - eval 10 0.517 (CPU, rebuilt assets) vs 0.579 (GPU, stored).
  - Both gaps are within the replay chaos seen before (G1: GPU replay ≠ the solver's truth by up to 0.39), so they
    neither confirm nor refute asset equivalence. The make_assets log match above is the evidence for eval 10.

Not testable on CPU:
- the GPU solve at G2 scale on eval references (time, memory, and whether G2's gains carry over to eval episodes);
- `pull-files` against the live store from a box (the same code as focused-pascal's, used by its launched jobs).
