# Independent verification of the scorer check (verify_scorer, 27 Oct 2026, 05:15–06:35 UTC)

I tried to refute `README.md` of this folder. I wrote my own scorer and checks and did not re-run the scorer
check's scripts. The code and outputs are in `../verify_scorer/`, with every command in `../verify_scorer/commands.log`.
Everything ran on CPU in this container, one heavy process at a time. Nothing was spent and nothing was uploaded. Public
mocap was read only for scoring.

**What is my own code.** `vs_core.py` was written from the official metric file. It has its own:
- parquet readers: the ground truth is read w-first and converted to xyzw; rollouts are read with pyarrow, not with
  the kit's `read_trajectory`;
- surface centroid and cup axis;
- pose conversion to the anchor;
- frame-0 scene alignment;
- symmetric ADD, AUC, SP-SR and MP-SR.

**What is shared on purpose.**
- The registration itself: `_register_object_body`, loaded from `metric_code/track_3/AUC.py`, not from `v2dlb`.
- The packer's `budget_mesh`.
- The stand-in definition: 1000 surface points with seed 7+slot, the centroid anchor and the PCA cup axis. The numbers
  under test are defined with it.

Labels:
- **[M]** measured here;
- **[D]** derived by arithmetic;
- **[doc]** taken from a document.

## Verdict: partly confirmed

Everything I re-derived matches the scorer check to 4 decimals or better: the bookkeeping, the end-to-end match,
the pack-4 audit, the seed and host flips, the frame-0 diagnostic and the pitcher yaw spread.

Four claims do not survive as stated:
- **"Boards: no flips (11 hosts)" is refuted.** At Kaggle's eval-25 seed for board 2 (25000176), the submitted
  `wooden_piece_2` flips 179° with a 5000-face host. It also flips at 1 of 20 consecutive seeds on the full scan [M].
- **The headline "It explains the pack-5 pitcher swap" is too strong, and its key statistic does not hold.**
  - Over 30 twin seeds, the swap has mean −0.035 and median +0.030 [M]. The −0.089 mean of seeds 0–4 that "matches
    Kaggle's −0.09" was luck from a small sample.
  - My better evidence supports the mechanism. At Kaggle's eval-20 seed, over 22 stand-in hosts, the swap is
    negative on 20. Its median is −0.13 [M].
  - The v3p pitcher's registered yaw predicts the swap's AUC with r = 0.96.
  - The claim is consistent with the mechanism, but it is not proven: these are the ep21 twin rollouts, not the eval-20
    rollout, and the host is unknown.
- **"1 of 11 host resolutions each" is a property of the chosen list.** On a wider set of 24 hosts, including a second
  decimation method, the sweeper flips on 3 of 24 hosts (eval 30) and 4 of 24 (eval 19). Which resolutions flip
  changes with the decimation method. Read the result as a per-draw flip probability of about 3–17 %.
- **"The hidden scan is necessarily lower resolution" holds only for usual array types.**
  - As float64 soups the scans need 94.5 MB [M], as the README says.
  - Welded float32 / int32 still needs 17.7 MB for the 10 public scans [M], about 19.8 MB with the 11th object [D].
    So that does not fit either.
  - But float32 vertices with uint16 faces would fit: about 13.3 MB [D]. The kit accepts that, since it calls
    `.astype(np.int64)`. "Very likely" is accurate; "necessarily" is not.

## 1. Key numbers re-derived with my own code

| claim (scorer README) | my result [M] | file | verdict |
|---|---|---|---|
| e2e ep21 twin21arc r1 AUC 0.790323, SP 1, MP 0 | own scorer **0.790323**, SP 1, MP 0. Official `score()` on DataFrames I packed myself: 0.790323, with both the float64-soup host (limit raised) and the welded float32 host (fits 16 MB unpatched) | t1/ep21_r1.json, t7/ep21_r1.json | confirmed |
| e2e ep2 e3 r1 0.451348, SP 0, MP 0 | **0.451348**, SP 0, MP 0 (own scorer and official `score()`) | t1/ep2_r1.json, t7/ep2_r1.json | confirmed |
| e2e ep11 twin11v3x r1 0.566834 | **0.566834**, SP 1, MP 0 | t1/ep11_r1.json | confirmed |
| f0 = reference: ep31 r1 +0.053; ep21 r1 / r2 −0.018 / −0.010 | 0.76972 → 0.82306 (**+0.0533**); **−0.0183 / −0.0096** | t1/*.json | confirmed |
| ep31 sweep-base perception (library_v2) seed offsets 0 / 1 / 2 / 6 | 0.8050 / 0.8222 / **0.0959** (sweeper 177.3°) / **0.0958** (178.0°) | t2/ep31_perc.json | confirmed |
| ep31 host 50k / 20k / 4096 faces: −0.709 / −0.709 / +0.056 | 0.0957 / 0.0957 / 0.8609, i.e. **−0.709 / −0.709 / +0.056**. Vertex-clustering 50k: **no flip** (0.849) | t2/ep31_perc.json | confirmed; method-specific |
| ep24 host 20k: −0.424, board flip; 50k −0.015; 4096 +0.001; seed 6 0.837 | 0.3882 (**−0.4235**, board 2 179.6°, SP/MP 1 → 0); −0.0154; +0.0007; 0.8374. Vertex-clustering 20k: no flip | t2/ep24_perc.json | confirmed |
| ep2 base 0.9823; seed 2 0.969; host 50k −0.003 | 0.9823; 0.9686; 0.9791 (−0.0032) | t2/ep2_perc.json | confirmed |
| bbox anchor ep13 −0.025, ep18 −0.0007, ep11 +0.0016; 4000 points ep13 −0.0003, ep18 +0.0021 | −0.0250, −0.0007, +0.0016; −0.0003, +0.0021 | t2/ep13,18,11_perc.json | confirmed |
| pitcher swap on twin r1: seed 0 0.790 → 0.868; seed +3 0.768 → 0.436; seed +4 0.825 → 0.498; eval seed full 0.772 → 0.832; eval seed 20k 0.769 → 0.762 | 0.7903 → 0.8678; 0.7680 → 0.4360; 0.8249 → 0.4982; 0.7715 → 0.8323; 0.7685 → 0.7619 | t2/ep21_r1_swap.json | confirmed |
| pitcher yaw over 30 seeds from 20000161 (full host): v3 −2.7 … 0.0; v3p −14.2 … +7.0, 20 of 30 more than 5° from the median | v3 −2.68 / −1.16 / +0.02 (0 of 30); v3p −14.17 / −0.11 / +7.05; 19 of 30 by yaw alone (the scorer used full-pose distance) | t3/pitcher_*_ev20.json | confirmed |
| eval 30 sweeper (seed 30000090) flips at 4096 faces only; eval 19 (19000057) at 16000 only; full host no flip | 4096 flips (177.7°) and 16000 flips (177.5°); full host 2.8° / 3.1°. **But also** eval 30 at 60k and 2500; eval 19 at 10000, vertex-clustering 50k and 20k. Seeds at the full host: 1 of 40 (eval 30), 3 of 40 (eval 19) | t3/sweeper_v3_ev30.json, _ev19.json | confirmed; frequency understated |
| pack-4 file: 9120 rows, rows == rollouts, max abs diff 0.0, xyzw | own reader: 9120 rows, 1 world, max abs diff **0.0** in all 20 episodes. Control: reading the rollout as wxyz differs by ≥ 1.03 | t5_pack.json | confirmed |
| payload == budget_mesh(library_v3), eval 8 beige cup v3x | own base64 / npz decode: equal to v3 everywhere; eval 8 beige cup equals v3x only (v3: no). One payload per object, on the first row | t5_pack.json | confirmed |
| eval-20 cup free fall 14.71 mm vs g·dt²·15 = 14.715 mm | dz **−14.715 mm**, rotation 0.000°, xy 0. Prediction 9.81·0.01²·15 = 14.715 mm (20 fps × 5 substeps [doc]). Frame 1 is −32 mm, not 54 mm: the cup is caught after step 1 | t5_pack.json | confirmed |
| Kaggle −0.0045 × 20 = −0.09 on eval 20; pack 5 → 6 changed only that mesh | parquet diff: the pose rows are identical (max abs 0.0); the only payload difference is `e000020/f0/o1`; `code_commit_url` also differs (not scored). 0.80941 − 0.81391 = −0.00450 [doc]; × 20 = −0.090 [D] on a 100 %-public board [doc, track3-requirements.md] | inline | confirmed |
| five metric files differ only in `_METRIC`; v2dlb helpers AST-equal to the metric copies | diff confirms. AST is equal for all 21 helpers once docstrings and annotations are stripped. The raw AST differs (the participant copy has docstrings stripped) | inline | confirmed, with that caveat |
| 94.5 MB float64 soups | 94,451,592 bytes | t4_budget.json | confirmed (see the verdict on "necessarily") |
| `sim_vs_ref` unregistered, 5 cm sphere points, no symmetry | `pipeline/qa.py` lines 54–60: `_warp_to_reference_start`, 500 points on a 5 cm sphere, plain `_object_add` | code read | confirmed |
| f0 of 26 Oct was a no-op | `f0_INVALID_noop/ep21_r{1,2}.json`: base == f0ref (0.7903, 0.7712); the fixed re-run gives −0.0183 (reproduced) | file read | confirmed |

## 2. Classic errors I looked for

- **Quaternion order.** Physical test on 6 episodes [M, t6_quat.json]. Each scan was placed by its frame-0 ground
  truth, read w-first:
  - every resting object's lowest point lies at 0.598–0.605 m (the table);
  - the ep2 lid sits at 0.689 m, on the pot;
  - read x-first, the lowest points scatter from 0.55 to 0.66 m.

  The rollout metadata declares xyzw. Reading the packed rows as wxyz changes them by ≥ 1.0. **No error.**
- **Frame origins.** The anchor centroid is recomputed by my own code and gives identical scores.
  - The link frame = mesh frame result was not re-derived.
  - Frame-0 gaps match: 0.73 / 0.89 mm on ep21, against a 24 mm COM offset.
- **Wrong run, version or copy.**
  - The box-stored `score_registered*.json` of every rollout I used names the same library as the scorer check
    (v3; v3x for ep11).
  - The ev30rp run (24 Oct) predates the repo's oldest commit (25 Oct). It still reproduces exactly with today's
    `library_v3` (0.7697), so the sweeper mesh did not change in a way that matters.
  - The pack files are the uploaded ones (sha256 in the receipts).
- **Mesh library mismatch.** v2 and v3 differ only in the sweeper (payload test: every other v2 object equals v3). The
  ep31 flip cost of −0.709 was measured with **library_v2**, which is not submitted.
  - My own test of the **submitted v3 sweeper** on a real rollout (ev30rp r1, t2/ep31_r1_v3.json) flips at the 20k
    host and at seed +2: 0.770 → 0.095, i.e. **−0.675**, SP and MP 1 → 0 [M].
  - So the derived ≈ −0.035 Track 3 AUC per flipped episode holds (−0.034 [D]).
  - v3 flips at a different set of draws than v2: 20k and +2, against v2's 50k, 20k, +2 and +6.
- **Frame indexing.**
  - The rollout's `step` equals `reference_frame`, and T equals the parquet length in all 5 rollouts.
  - `sim[k]` is closest to `ref[k]` at lag 0 in all 5 (lags −2 … +2) [M]. No off-by-one there.
  - Against ground truth, scoring the perception track against GT[k−1] gives:
    - ep31 +0.071;
    - ep2 +0.001;
    - ep24 −0.010.

    That is not a consistent whole-frame shift. ep31's gain is confounded with the frame-0 alignment of the sweeper
    anchor. The sub-frame lag belongs to the timing check (`../timing/`: +0.54 frames). It is not a scorer bookkeeping
    error.
- **Per-object vs per-episode averaging.**
  - The kit takes the mean over bodies, then over episodes. My own AUC does the same and matches.
  - The README describes SP-SR as "per object … averaged over objects". The code instead thresholds the
    **object-averaged** time-mean errors, giving one boolean per episode. That is a wording slip only, since the
    numbers use the kit's code.
- **Symmetric objects.**
  - ep11 library_v2 beige cup: registered at 145° / 118°, with the cup-axis tilt about 6.5° (Rb·a vs a). This comes
    from the candidate's own axis sitting about 3° off the scan axis, combined with a large spin.
  - Its per-object AUC is 0.933 / 0.930 [M], so "harmless spin" holds.
  - The scorer check is right that `seed_noise.md`'s "flips [0, 1]" label for ep11 is wrong.
- **Selection bias.**
  - The anchor, points and axis sensitivities use 7 perception tracks (AUC 0.80–0.98), not policy rollouts. I did
    not test them on rollouts.
  - The "stable mesh ±0.01–0.03" claim understates the tail. The stable v3 pitcher over 30 twin seeds ranges
    0.667–0.833 (median 0.808, sd 0.036). One seed (offset 23) loses 0.14, with the pitcher registered at 5.2° [M].
- **Unbacked claims.**
  - The seed formula assumes the hidden solution's `episode_index` equals the eval number (row ids `e0000NN`). This
    cannot be checked from here, and every eval-seed result depends on it.
  - "Rack, dust pan, white_pot: no flips" rested on 3 hosts. I extended it to 24 hosts and 20 seeds at the
    eval seeds of rack ev14 slot 1, dust pan ev38 / ev19, white_pot ev1 and board 1 ev25: **0 flips**, max 3.7° [M].
    I did not cover every eval and slot pair. Not covered: rack 15 / 16 / 28 / 30, pot 3 / 5 / 6 / 8 / 28, lid,
    cups, spoon (no scan).

## 3. The scorer's problems: do they survive?

| # | problem | survives? | note |
|---|---|---|---|
| 1 | registration lottery is the dominant local-vs-Kaggle gap; flips cost up to −0.71 | **yes** | reproduced (v2 −0.709; submitted v3 on a rollout −0.675). Its rank as "dominant" against other gaps is not measured |
| 2 | eval 30 / eval 19 sweeper flips at 1 of 11 hosts; review §9 "majority" holds only for the full host | **yes, frequency understated** | 3 of 24 and 4 of 24 hosts; 1 of 40 and 3 of 40 seeds. **Add eval 25 board 2** (1 of 24 hosts, 1 of 20 seeds) |
| 3 | pack-5 swap failed because library_v3p is yaw-unstable, not because of anchor or points; work-log lesson names the wrong cause | **yes in substance; the evidence offered is weak, mine is stronger** | the seed-mean match is not robust (30 seeds: −0.035). Eval-seed host sweep: median −0.13, 20 of 22 negative, r(yaw, AUC) = 0.96. Anchor and points were tested only at the twin seed |
| 4 | single-draw twin A/Bs are unreliable (v3 0.768–0.825) | **yes, stronger** | over 30 seeds v3 0.667–0.833; v3p 0.419–0.899 |
| 5 | `sim_vs_ref` is not the kit metric | **yes** | `qa.py` read |
| 6 | frame 0 is after the first step; frame-0 = reference changes AUC −0.043 … +0.070 | **yes** | free fall 14.715 mm exact; ep31 +0.053, ep21 −0.018 / −0.010 reproduced; ep24 / 26 / 27 not re-run |
| 7 | own bugs (f0 no-op, unwelded decimation, ep11 label) | **yes** | f0 no-op confirmed from the files |
| 8 | box-built `/content/assets` not stored | **yes** (not testable) | — |
| new | "boards: no flips" | **refuted** | board 2 flips at the eval-25 seed with a 5000-face host |
| new | "hidden scan necessarily lower resolution" | **weakened** | true for float64 or int32 encodings; float32 + uint16 (~13.3 MB) would fit |

## 4. Hypotheses (mine), with the experiment that would falsify each

- **V1.** Registration flips are a per-draw lottery: any re-meshing of the host changes the 3000 ICP samples. So
  their probability, not the specific resolution, is the robust quantity.
  - Sweeper: about 3–17 %. Board 2: about 5 %. Pitcher v3p yaw beyond 5°: about 60 % of seeds.
  - Falsify: on a third decimation method (e.g. open3d quadric, or Poisson resampling), the flip rate falls outside
    these ranges at the same eval seeds.
- **V2.** The ep21 twin rewards v3p only when v3p registers at about +5° yaw (r = 0.96). That points to a yaw offset
  of a few degrees between our pitcher track and mocap on ep21, which a favourable mis-registration cancels.
  - Falsify: the per-frame pitcher yaw error of the ep21 rollout against mocap, under the v3 registration, has a
    median within ±2°.

## Files

All under `../verify_scorer/`:
- code: `vs_core.py`, `t1_rollouts.py`, `t2_variants.py`, `t3_evalreg.py`, `t4_budget.py`, `t5_pack.py`,
  `t6_quat.py`, `t7_official.py`, `t8_swapdist.py`, `run_t3_batch.sh`, `commands.log`;
- results: `t1/`, `t2/`, `t3/`, `t7/`, `t4_budget.json`, `t5_pack.json`, `t6_quat.json`, `t8_swapdist.json`.

Uncommitted (the main session commits).
