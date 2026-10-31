# E0 public context: how single-episode builds of the C0 methods scored on the public scans

Written 2026-10-31 (~17:10 UTC) for the CD-O sprint, candidate E0 (C0's methods rebuilt on each eval episode).
Machine-readable copy: `context_public.json` (same folder).

- **What this is:** numbers that already exist from the 26-27 Oct public rounds, regrouped. **No new scoring**, no scan
  or mesh read except a sha1 identity check of rack candidate files. CPU only, $0.
- **Metric:** `cdo_eval` in cm. It is the kit CD-O of the mesh against the **public** scan, averaged over the eval-pair
  seeds of that object (`scripts/mesh_metric.py`, the 22 Oct metric). There is no eval ground truth, so E0 itself
  cannot be scored. These numbers show what builds of the same methods scored on public data.
- **Computation:** `context_public.py` (scratchpad `cdo_e0/context/`, sha1 `f54b8300c1`). It reads the repo records
  listed below. Repo head at the time: d721d97.
- **Resume check:** the stopped first E0 run left only a NOTES line (record counts 36/6/6/12/16/11). The counts match;
  no earlier `context_public.md` existed.

## Summary [D: recorded scan scores; regrouped here]

| Object (eval pairs) | Single-episode builds: median [min–max] (n) | C0 GT-free pick | Own-episode mean | library_v3 |
|---|---|---|---|---|
| white pot (6) | **0.416** [0.309–0.653] (26 distinct meshes from 8 eps × 4 variants); fit only 0.357 [0.325–0.597] (8) | **0.342** (ep41 fit) | **0.415** (fit, 8 eps) | 0.437 |
| pot lid (1) | **0.218** [0.216–0.220] (2: ep2 fit and tsdf at T_LID 2.5 mm) | **0.220** (ep2 fit) | **0.220** (1 ep) | 0.421 |
| dish rack (5) | allowed config: **none scored (n = 0)**. MARKED leaked config: 0.443 [0.422–0.509] (8 distinct, 5 eps) | **0.456** (joint of eps 12/13/27, not single-episode) | 0.458 (MARKED, full, 5 eps) | 0.555 |
| blue cup (5) | **0.327** [0.291–0.364] (2: ep21, ep22) | **0.291** (ep21; selector flagged) | **0.327** (2 eps) | 0.523 |

- **Distinct meshes, not records:** the median is taken over distinct meshes (deduplicated by sha1). The pot's fit and
  nostem files are byte-identical on 6 of 8 episodes. Over all 32 pot records the median is 0.388.
- **Own-episode mean:** each public episode gets its own build with the shipped variant, and the CD-O is averaged over
  episodes. This is the public analogue of "each eval pair gets the mesh built from its own episode".

## What it means for E0

**Pot.** The spread between episodes is large.
- Two of the 8 fit builds are worse than library_v3: ep27 0.576 and ep45 0.597 (library 0.437).
- The mean of the per-episode builds (0.415) is only 0.022 cm better than library_v3.
- C0's gain (0.342) came from the GT-free pick across episodes. It was pre-registered, and recorded fidelity vs CD-O
  has Spearman 0.85 over the 32 candidates.
- So on eval, a single pick across the eval-episode candidates should do better than using each eval episode's own
  build. This is a hypothesis from public data.
- Picking the variant inside each episode by the recorded fidelity gives a mean of 0.397. On ep42 and ep45 it chooses
  `thick`, which scores worse.
- Oracle best variant per episode: mean 0.366 (oracle only, never used to decide).

**Lid.** Only one public episode can be fitted (ep0 cannot), so episode-to-episode variation is unknown.
- The allowed builds lie within 0.216–0.220.
- The whole thickness grid (1.5 / 2.5 / 4.0 mm, fit and tsdf) lies within 0.216–0.225.

**Rack.** No single-episode build in an allowed configuration (T_WALL 2.5 mm, CUP_LEAN=1) has ever been scored.
- Its 10 per-episode candidates have GT-free fidelity only (`results/prim/clean/rack_t2.5_lean1_candidates.jsonl`).
- The only scored per-episode builds are first-round builds with the leaked upright cup holder (T_WALL 2.5, CUP_LEAN=0).
  Their sha1 is byte-identical to the clean-round `t2.5_lean0` candidates (checked here).
- They are a marked proxy only. They lie 0.422–0.509, all below library_v3 (0.555).
- Effect of lean on the joint mesh: +0.004 cm at 1.5 mm, +0.003 at 2.5, −0.012 at 4.0.
- Fidelity does not track CD-O across rack episodes. ep31 has the worst fidelity (8.17 mm) and the best CD-O (0.422).
  ep26 has fidelity 7.80 and the worst CD-O (0.509).

**Blue cup** (n = 2):
- the ep21 and ep22 lathes score 0.291 and 0.364, both far below library_v3 (0.523);
- the merged two-episode lathe scores 0.396, worse than either (fusion hurts, as on 22 and 26 Oct);
- C0's pick (ep21) used `obs_fidelity.py`, which was written after these lathes were scored (flag).

**Board effect if the hidden scans equal the public ones** [E]. This is the pair-weighted change over 36 pairs vs
library_v3, for the 17 pairs of these four objects (pot 6, lid 1, rack 5, blue cup 5):
- C0 picks: −0.068 cm;
- own-episode means: −0.050 cm;
- family medians: −0.052 cm.

The rack terms of the last two use the marked leaked-config proxy. These are estimates, not measurements of E0.

## Pooled records (exact)

Paths are under `docs/research/mesh-2026-10-26/results/`.

- **White pot**, `prim/potlid/metric_all.jsonl`:
  - pooled: `potlid/{fit,nostem,thick,tsdf}/ep{2,26,27,41,42,43,44,45}`, object `white_pot`;
  - 32 records, 26 distinct meshes;
  - fit per episode: ep2 0.354, ep26 0.416, ep27 0.576, ep41 0.342, ep42 0.352, ep43 0.360, ep44 0.325, ep45 0.597;
  - pick: `potlid/fit/ep41` (fidelity 3.035 mm, `prim/potlid/selection.json`);
  - per-episode fidelity from `prim/potlid/fidelity.jsonl`;
  - the pot has no scan-informed parameter (wall measured from our points), so every variant is allowed.
- **Pot lid**, `prim/clean/lid_scores.jsonl`:
  - pooled: `clean/lid/t2.5_fit` 0.2199 and `clean/lid/t2.5_tsdf` 0.2164;
  - pick: `t2.5_fit`, fidelity 1.686 vs 1.913 mm (`prim/clean/lid_fidelity.jsonl`);
  - T_LID 2.5 mm is the grid midpoint. It equals the value that leaked into the first brief (flag kept from C0).
- **Dish rack**, MARKED proxy from `prim/rack/scores.jsonl`:
  - `rack/ep{12,13,26,27,31}_{full,nomk}`: 10 records, 8 distinct (ep26 and ep27 full = nomk);
  - full per episode: ep12 0.444, ep13 0.443, ep26 0.509, ep27 0.471, ep31 0.422;
  - the per-episode fidelity (`prim/rack/candidates.jsonl`) picks `full` on all 5;
  - pick: `prim/clean/rack_scores.jsonl` `clean/rack/t2.5_lean1/all_joint` 0.4560.
- **Blue cup**, `lathe_obs.jsonl`:
  - `lathe_obs_g/a1/ep21/blue_cup` 0.2906 (scratchpad `lathe/ep21_blue_cup_g1.glb`);
  - `lathe_obs_g/a1/blue_cup` 0.3637 (`lathe/ep22_blue_cup_g1.glb`);
  - both use g code with appendages=1 and default settings, the C0 setting.
  - Code note: ep22 g1 was built at 16:12 UTC on 26 Oct, before commit 15b860d; ep21 g1 at 16:27, after it. The
    lathe_obs.py diff 15b860d..8cb7994 only turns `--dh`, `--min_pts` and `--knn` into flags whose defaults are the
    old values. This was checked by reading the code, not by a rebuild.
- **library_v3:** `baseline_library.jsonl` `library_v3/<object>`.

## Excluded (and why)

- **Pot:**
  - `lathe_obs_g/{a0,a1}/white_pot` and `lathe_hyb_v3app/white_pot`: lathe methods, not the prim_potlid family.
- **Lid:**
  - `potlid/{fit,nostem,thick,tsdf}/ep2` lid (0.219, 0.219, 0.230, 0.216): first-round code (floating arch strap,
    fixed in the clean-up round) and the leaked T_LID default;
  - `potlid/tsdf/ep2` is byte-identical to `clean/lid/t2.5_tsdf` and is counted once there;
  - `clean/lid/t1.5_*` and `t4.0_*`: not the shipped thickness. They are shown only as grid context in the JSON.
- **Rack:**
  - `rack/epall_joint*` and all `clean/rack/*/all_joint`: multi-episode builds. The latter appear only in the JSON's
    lean-effect table.
- **Blue cup:**
  - `lathe_obs_g/a1/ep21+22` 0.396: merged episodes;
  - `lathe_obs_g/a0` 0.392: appendages off;
  - `lathe_obs/{a0,a1,b0,b1,solid1}` (0.372–0.493): earlier code and settings;
  - `lathe_hyb_v3app`: library appendages;
  - `lathe_f0/*`: frame-0 points only, a rejected method.

## Caveats

- All numbers are public builds scored against public scans. The eval objects are the same physical items, but eval
  episodes differ in views and coverage.
- The sample sizes are small: lid 1 episode, blue cup 2, rack 5 (leaked config only), pot 8.
- The rack and lid thickness of 2.5 mm stays flagged: it is the grid midpoint, and it equals a value that leaked from
  scan measurements.
