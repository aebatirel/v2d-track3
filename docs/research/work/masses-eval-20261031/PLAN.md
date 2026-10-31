# Eval retrain with realistic masses: plan (31 Oct 2026 ~08:30 UTC; nothing launched, nothing built)

Written while the transfer check runs (box 58502738, run `20261031-mass-2ed46ea`, launched ~06:45 UTC, expected end
≈ 12:10–14:15 UTC [E]). No result of that check exists yet, so the scope rule (section 0) and the adoption rule (section
5) are fixed here before any result. This step prepares the retrain; it rents nothing and uploads nothing.

Markers: [M] measured, [E] estimate, [H] hypothesis. Nothing in this plan reads ground truth (eval episodes have none);
the per-episode facts come from our own stored references, the packs' summaries and H5. Ranking inputs and scripts:
`rank/` (`motion.py`, `rank.py`, `motion.json`, `rank_out.txt`).

## 0. Gates before any launch
1. **Transfer check ADOPT** (`masses-transfer-20261031/PREREG.md` section 3) with `mass_verify` VERIFIED.
   - NOT ADOPTED or INVALID: this plan is void; the eval pipeline keeps 0.3 kg.
   - INCOMPLETE: wait for the completed reading.
2. **Selection metric moves with the truth metric** (pre-registered here). The eval rule (section 5) selects on
   sim_vs_ref against our reference, not on AUC vs mocap. Proceed only if the check's sim_vs_ref Δ (reported beside its
   verdict), averaged over ep2 and ep12, is ≥ −0.01. If it is lower while the AUC Δ passes, sim_vs_ref cannot see the
   mass gain on eval; stop and report to the owner.
3. **Scope by effect size** (pre-registered; the owner decides). Let Δ̂ = mean(Δ(ep2), Δ(ep12)), the check's registered
   AUC seed means.
   - ADOPT with Δ̂ < +0.06: propose option O2 (wave 1).
   - ADOPT with Δ̂ ≥ +0.06: propose O3 (wave 1, then wave 2 if the spoon pilots pass).
   - Why 0.06 [E]: below it, wave 2's four spoon episodes are worth ≈ +0.002–0.004 LB for ≈ $10 (section 3).
4. The owner's go-ahead for the option and its cost, and a ledger `planned` line per box.
5. The build items of section 6 are done, mocked on CPU and reviewed.

## 1. The 20 eval episodes as packed (pack 7 = the current submission)

**Provenance [M].**
- Checkpoints: `results/submissions/20261030-track3g-candidate/checkpoints.json`.
- Reference paths and checkpoint steps: the packed episode JSONs (`checkpoint`, `parquet`, `environment_steps`).
- md5 and fingerprint (`mass_arm.traj_fingerprint`: every column except the asset paths) are of the reference files
  pack 6's box evaluated with, `runs/20261026-pack6-5203d42/refs`.
  - The copies of c01s43, fr3233s43, evb1420, fr32s46b, evb0810, c25s42, std30 and seed43 are byte-identical for the
    episodes they hold.
- The pack-8 candidate (`20261030-track3h-candidate/`) differs only in eval 1.

| eval | packed policy run (pack 7) | learner, recipe | seed, step | reference the config names: md5 · fingerprint | URDFs from | pieces / lib | pull for reuse |
|---|---|---|---|---|---|---|---|
| 1 | `20261025-std0116-ee7ba8e`; pack 8: `20261030-c01s43-328139c` | std (std_learner → hard_ab: FDR + VOC, starts 0.25, 250M); pack 8: carve_rerun, same + ev01 | s42, 200M; pack 8 s43, 250M | `refs/perc2mcks/ep1/…/64333b0b…-0.parquet` 7f230466 · c94d59eb | `/content/assets` (make_assets) | none; pack 8: `meshes/carve/ev01` | `20261024-pack-31ef267` perc2mck/ep1 + perc2/ep1 (as c01) |
| 3 | `20261024-seed43-61101f5` | glock (glock_public SPLIT=eval REUSE_REF on pack-31ef267's 24 Oct ref, 70M) | s43, 70M | `refs/glockt/ep3/…/ref_gl_ilc.parquet` 732e44ea · 641bba6a | `refs/sf/ep3/assets` | – | `20261024-pack-31ef267` |
| 5 | `20261024-seed43-61101f5` | glock, as 3 | s43, 60M | `refs/glockt/ep5/…` aa2f4fc5 · 01745091 | `refs/sf/ep5/assets` | – | pack-31ef267 |
| 6 | `20261024-pack-31ef267` (24 Oct eval runs) | glock, 24 Oct recipe | s42 (default), 70M | `refs/glockt/ep6/…` 50445bc3 · 49fa0741 | `refs/sf/ep6/assets` | – | pack-31ef267 |
| 8 | `20261025-evb0810-ee7ba8e` | glock (eval_both: rebuilt ref, REPLAN 1) | s42, 70M | `refs/glockt/ep8/…` 9424b5a1 · 89ef51de | `refs/sf/ep8/assets` (v3x beige cup) | EP_LIB 8:library_v3x | evb0810 |
| 10 | `20261026-gl10A2-5e0e100` | glock (eval_both variant, REPLAN 1, SF 0, carved cups) | s42, 60M | `refs/glockt/ep10/…` 1a5003d9 · cbcd56d0 | **`/content/assets`** (library_v3 + ev10) | ASSET_PIECES ev10 | gl10A2 (glockt, glock; perc2mck ep10 and rest_check [E] present) |
| 14 | `20261025-evb1420-ee7ba8e` | glock (eval_both) | s42, 70M | `refs/glockt/ep14/…` 10d5f3ba · 71fa181b | `refs/sf/ep14/assets` | – | evb1420 |
| 15 | `20261024-seed43-61101f5` | glock, as 3 | s43, 70M | `refs/glockt/ep15/…` 1d7f2d1c · 5c7e694e | `refs/sf/ep15/assets` | – | pack-31ef267 |
| 16 | `20261024-seed43-61101f5` | glock, as 3 | s43, 60M | `refs/glockt/ep16/…` f7e2ea92 · ade67fc9 | `refs/sf/ep16/assets` | – | pack-31ef267 |
| 19 | `20261025-std1928-ee7ba8e` | std (std_learner) | s42, 250M | `refs/perc2mcks/ep19/…/afc53914…-0.parquet` 201f338a · 0e94714f | `/content/assets` | – | std1928 or its source pack-31ef267 (md5-checked) |
| 20 | `20261025-evb1420-ee7ba8e` | glock (eval_both, arc foot SF_ARC 1) | s42, 70M | `refs/glockt/ep20/…` 4d06d8d4 · c1e09fcc | `refs/sf/ep20/assets` | – | evb1420 |
| 25 | `20261026-c25s42-feb0407` | std carve (carve_rerun) | s42, 250M | `refs/perc2mcks/ep25/…/2057d9f1…-0.parquet` 71ac95f3 · 6f709837 | `/content/assets` | ASSET_PIECES ev25 | c25s42 |
| 28 | `20261025-std1928-ee7ba8e` | std (std_learner) | s42, 250M | `refs/perc2mcks/ep28/…/4327c2f4…-0.parquet` 6f57deb2 · 6cb4ddb8 | `/content/assets` | – (default pot: clashes with ev01) | std1928 or pack-31ef267 (md5-checked) |
| 30 | `20261025-std30-ee7ba8e` | std (std_learner) | s42, 250M | `refs/perc2mcks/ep30/…/a2eb7d27…-0.parquet` dd464c96 · c3510178 | `/content/assets` | – | std30 or `20261024-ev30rp-07eef1a` (md5-checked) |
| 32 | `20261026-fr32s46b-5e0e100` | glock, frozen recipe (on evb3233's ref) | s46, 50M | `refs/glockt/ep32/…` 36e600c8 · 4ae3f296 | `refs/sf/ep32/assets` | – | fr32s46b |
| 33 | `20261029-rcB-34bf6ae` | glock, frozen + CURR_SCALE 0.4 (arm B) | s43, 40M | `refs/glockt/ep33/…` 2a7173ab · e45b8179 | `refs/sf/ep33/assets` | – | fr3233s43 (as rcB) |
| 35 | `20261024-pack-31ef267` | glock, 24 Oct | s42, 70M | `refs/glockt/ep35/…` bc064b46 · 42de7879 | `refs/sf/ep35/assets` | – | pack-31ef267 |
| 36 | `20261024-pack-31ef267` | glock, 24 Oct | s42, 50M | `refs/glockt/ep36/…` 36e60e15 · b007f114 | `refs/sf/ep36/assets` | – | pack-31ef267 |
| 37 | `20261024-pack-31ef267` | glock, 24 Oct | s42, 70M | `refs/glockt/ep37/…` b78747bb · 432ba6d9 | `refs/sf/ep37/assets` | – | pack-31ef267 |
| 38 | `20261024-pack-31ef267` | glock, 24 Oct | s42, 70M | `refs/glockt/ep38/…` 33d3f4e2 · e13cda6d | `refs/sf/ep38/assets` | – | pack-31ef267 |

- Reference paths are under `/content`. Grasp-lock references name their own asset copy, except eval 10. Standard-learner
  references name the one shared `/content/assets`.
- A "glock" policy pulls, for REUSE_REF: `refs/perc2mck/ep<N>`, `refs/sf/ep<N>`, `refs/glockt/ep<N>` and
  `results/glock_public/ep<N>/rest_check.json` (with `zero_score.txt` and `support_fill.json` if present).
  - This is the recipe-arm pattern, which worked for 32 and 33 on 29 Oct.
  - That `pack-31ef267` holds `rest_check.json` for 6 and 35–38 is [E], not checked. The seed-43 box reused its
    references for 3, 5, 15 and 16, so it holds them for those. The build checks the rest with targeted single-file
    downloads (no listings).

**Scores and objects.**
- Packed draw: pack 7 `summary.txt`.
- Level ± sd (min): H5, 10 official draws of pack 6's policies (`docs/analysis/h5-20261029/h5_summary.json`).
  - Eval 33: the pack-7 policy's c33B (10 draws).
  - Eval 1, pack-8 policy: e1conf2 (20 draws).
- Masses: `docs/research/physics-2026-10-30/props_masses_only.json` (md5 d5508930…, commit 6bbb52a), with the ratio to
  0.3 kg.
- "moved": the largest displacement of that object in OUR reference [M, `rank/motion.json`].
- \* = the spoon prior (no scan; 30–70 g plausible).

| eval | packed | level ± sd (min) | objects: kg (× 0.3 kg), moved | stratum |
|---|---|---|---|---|
| 1 | 0.9196 (p8 0.9232) | std0116 0.822 ± 0.239 (0.150); c01s43 0.924 ± 0.017 (0.884) | pot 0.277 (×0.92) 18 cm; lid 0.088 (×0.29) 23 cm | masses |
| 3 | 0.9418 | 0.904 ± 0.072 (0.702) | pot (×0.92) 9 cm; spoon 0.05\* (×0.17) 29 cm | spoon |
| 5 | 0.9595 | 0.966 ± 0.006 (0.954) | pot (×0.92) 24 cm; spoon\* 32 cm | spoon |
| 6 | 0.9713 | 0.956 ± 0.021 (0.923) | pot (×0.92) 15 cm; spoon\* 28 cm | spoon |
| 8 | 0.9783 | 0.969 ± 0.024 (0.904) | beige cup 0.137 (×0.46) 22 cm; pot (×0.92) 10 cm | masses |
| 10 | 0.4563 | 0.450 ± 0.007 (0.431) | blue cup 0.128 (×0.43) 6 cm; beige cup (×0.46) 25 cm | masses |
| 14 | 0.9094 | 0.615 ± 0.199 (0.347) | blue cup (×0.43) 27 cm; rack 0.387 (×1.29) static | masses |
| 15 | 0.9465 | 0.960 ± 0.008 (0.951) | rack (×1.29) static; spoon\* 43 cm | spoon |
| 16 | 0.9079 | 0.813 ± 0.077 (0.685) | rack (×1.29) static; spoon\* 38 cm | spoon |
| 19 | 0.9278 | 0.921 ± 0.034 (0.830) | sweeper 0.045 (×0.15) 11 cm; dust pan 0.044 (×0.15) 15 cm | masses |
| 20 | 0.8948 | 0.888 ± 0.043 (0.768) | blue cup (×0.43) 8 cm; **pitcher 0.503 (×1.68)** 37 cm | masses |
| 25 | 0.8937 | 0.850 ± 0.099 (0.583) | boards 0.139 / 0.141 (×0.46 / 0.47) 20 / 25 cm | masses |
| 28 | 0.9290 | 0.931 ± 0.033 (0.872) | rack (×1.29) static; pot (×0.92) 42 cm | masses |
| 30 | 0.9229 | 0.798 ± 0.255 (0.262) | sweeper (×0.15) 25 cm; rack (×1.29) static | masses |
| 32 | 0.8656 | 0.838 ± 0.068 (0.655) | blue cup (×0.43) 16 cm; spoon\* 28 cm | spoon |
| 33 | 0.9401 | rcB 0.934 ± 0.008 (0.917); pack-6 policy 0.854 ± 0.137 | blue cup (×0.43) 10 cm; spoon\* 29 cm | spoon |
| 35 | 0.9829 | 0.986 ± 0.006 (0.970) | spoon\* 24 cm | spoon |
| 36 | 0.9912 | 0.990 ± 0.007 (0.969) | spoon\* 25 cm | spoon |
| 37 | 0.9979 | 0.998 ± 0.002 (0.995) | spoon\* 32 cm | spoon |
| 38 | 0.9998 | 1.000 ± 0.001 (0.998) | dust pan (×0.15) 26 cm | masses |

**Spoon stratum.** Ten evals (3, 5, 6, 15, 16, 32, 33, 35, 36, 37) carry the wooden spoon. Its 0.05 kg is a stated
prior, and no public measurement includes a spoon: Round 3 used ep2, ep12, ep18 and ep24, and the transfer check uses
ep2 and ep12. Spoon results are therefore reported apart, and the stratum starts with two pilots (section 5, rule 9).

## 2. What a retrain changes, and what it does not
- **Same reference.** Each retrain uses the packed policy's stored reference unchanged. The job checks the md5 for
  standard-learner references and the trajectory fingerprint for grasp-lock arm copies (section 1), and refuses on a
  mismatch.
  - Masses change only the simulator, in RL training and in evaluation.
  - The references were built at 0.3 kg (grasp lock, ILC and evolutionary search). This is exactly the transfer
    check's condition (its PREREG section 2, "known asymmetry").
- **Grasp lock, 15 evals.** `tools/mass_arm.py --arms "mass1:<props>"` copies `refs/sf/ep<N>/assets` to
  `refs/mass1_sf/ep<N>/assets` and rewrites the masses there (COM kept, inertia × m / 0.3). It writes per-seed parquet
  copies `refs/mass1s{42,43}_glockt/ep<N>`, in which only `object_urdf_paths` differs.
  - Eval 10's reference names `/content/assets`. Its box therefore builds `/content/assets` at 0.3 kg with PIECES ev10,
    which becomes mass_arm's source root. Its copy is then independent of any shared folder too.
- **Standard learner, 5 evals.** `MA_ARGS="--physics docs/research/physics-2026-10-30/props_masses_only.json"` together
  with the packed policy's PIECES (hard_ab.sh and carve_rerun.sh already pass it to make_assets).
  - One `/content/assets` serves the whole box. So a box holds only episodes whose pieces agree per object:
    - ev01 (pot, lid) clashes with eval 28 (default pot);
    - ev10 (cups) clashes with nothing standard;
    - ev25 (boards) clashes with nothing.
- **Training side: the packed run's settings.** That means 70,004,736 steps for grasp lock and 250,003,456 for the
  standard learner, the kp 400 embodiment, FDR + VOC, `ENV_EP33="CURR_SCALE=0.4"`, eval 8 on LIB library_v3x and eval 1
  on ev01.
  - [H] Recipe drift between the packed runs' commits (664e5fd / 61101f5 / ee7ba8e / 5e0e100 / 34bf6ae / 328139c) and
    the launch SHA is confounded with the masses.
  - The verification (B3) prints the config diff against the packed checkpoint. The per-episode rule does not depend on
    the cause, but the Δ vs level is labelled "masses + seed + code", not "masses".
- **What the transfer check does not cover** [H; read the eval results with these in mind]:
  - the standard learner (evals 1, 19, 25, 28, 30);
  - the spoon prior;
  - a carried object made HEAVIER (eval 20's pitcher ×1.68, while the grasp-lock lift feed-forward was set at 0.3 kg);
  - carved collision pieces (evals 1, 10, 25).
  - Sweeper / dust pan: public ep18 gained only +0.011 in Round 3 [M], although its mass ratio is the largest.

## 3. Expected-gain ranking [E]
**Model** (`rank/rank.py`; deterministic; every weight is a stated guess, not a fit):
- lift = L × wD × wR × wT, where L is the transfer check's mean gain (0.03 = its ADOPT bar, 0.05, 0.10).
  - wD: 1 if the largest |ln(m / 0.3)| over the objects our reference moves > 3 cm is ≥ 0.7; 0.5 if ≥ 0.3; else 0.1.
    Static racks do not count.
  - wR: 1 for grasp lock (the measured recipe), 0.5 for the standard learner (unmeasured).
  - wT: 0.5 for eval 20 (heavier carried object); 0.25 for eval 10 (geometry-limited reference: the oracle twin says
    C2, perception-limited); 0.25 for evals 19, 30 and 38 (ep18's +0.011).
- new mean = min(level + lift, max(0.99, level)).
- Board gain = max(0, new mean − packed draw): the leaderboard scores the submitted rollout. "Need" = packed − level is
  how far the packed draw sits above its policy's mean.
- Eval 1 uses the c01s43 carve recipe as its base (level 0.924) and pack 8's bar 0.9232. Against pack 7's 0.9196 its
  g(.05) is 0.0295.

| rank | eval | stratum | learner | wD·wR·wT | need | g(L=0) | g(.03) | g(.05) | g(.10) | reading |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 33 | spoon | glock | 1 | +0.006 | 0 | 0.024 | 0.044 | 0.050 | stable policy (sd 0.008), capped by 0.99 |
| 2 | 15 | spoon | glock | 1 | −0.013 | 0.013 | 0.043 | 0.044 | 0.044 | packed draw below its mean: 0.013 of it needs no masses |
| 3 | 5 | spoon | glock | 1 | −0.007 | 0.007 | 0.031 | 0.031 | 0.031 | same, 0.007 without masses |
| 4 | 1 | masses | std carve | 0.5 | −0.001 | 0.001 | 0.016 | 0.026 | 0.051 | twin ep2 measured largest (+0.160); unmeasured learner |
| 5 | 32 | spoon | glock | 1 | +0.028 | 0 | 0.002 | 0.022 | 0.072 | most room (0.12); seed-noisy (s42/43/46: 0.78/0.70/0.80, 5 draws) |
| 6 | 6 | spoon | glock | 1 | +0.015 | 0 | 0.015 | 0.019 | 0.019 | capped |
| 7 | 20 | masses | glock | 0.5 | +0.006 | 0 | 0.009 | 0.019 | 0.044 | heavier pitcher: direction unmeasured |
| 8 | 3 | spoon | glock | 1 | +0.038 | 0 | 0 | 0.012 | 0.048 | lucky packed draw |
| 9 | 8 | masses | glock | 1 | +0.009 | 0 | 0.012 | 0.012 | 0.012 | near ceiling |
| 10 | 35 | spoon | glock | 1 | −0.004 | 0.004 | 0.007 | 0.007 | 0.007 | near ceiling |
| 11 | 10 | masses | glock | 0.25 | +0.007 | 0 | 0.001 | 0.006 | 0.018 | reference-limited; the cup-nest lever (task 18) is the fix |
| 12 | 28 | masses | std | 0.05 | −0.002 | 0.002 | 0.004 | 0.005 | 0.007 | pot ×0.92: almost no mass change |
| – | 25 | masses | std carve | 0.5 | +0.044 | 0 | 0 | 0 | 0.006 | insurance only (sd 0.099) |
| – | 19 | masses | std | 0.125 | +0.007 | 0 | 0 | 0 | 0.006 | ep18 analogue +0.011 |
| – | 16 | spoon | glock | 1 | +0.095 | 0 | 0 | 0 | 0.005 | insurance only (sd 0.077) |
| – | 14, 30 | masses | glock, std | 1, 0.125 | +0.29, +0.12 | 0 | 0 | 0 | 0 | lucky packed draws: insurance only |
| – | 36, 37, 38 | spoon, spoon, masses | glock | – | ≈ 0 | 0 | 0 | 0 | 0 | no room (packed ≥ 0.991) |

- The g values are sim_vs_ref on one episode. The leaderboard effect is Σg / 20 × 0.76: transfer 0.74–0.78 [M, pack 7].
- Per option, as LB AUC at L = 0.03 / 0.05 / 0.10:
  - O1 (20, 8, 33, 15): +0.0033 / +0.0045 / +0.0057;
  - O2 (+ eval 1): +0.0039 / +0.0055 / +0.0076;
  - O3 (+ 5, 32, 6, 3): +0.0057 / +0.0086 / +0.0140;
  - all 20: +0.0062 / +0.0093 / +0.0159.
  - In each, ≈ +0.0005–0.0010 needs no masses (L = 0), mainly evals 15 and 5, whose packed draws sit below their means.
- **Reading.** Even at L = 0.10 the whole batch is worth ≈ +0.016 LB [E], against the ≈ +0.046 that 5th place needs.
  Masses are one component, not a rank change on their own.
  - The ranking is driven by "need" and by the 0.99 cap more than by mass deviation. The top 9 are the same set at
    L = 0.05 and 0.10 (at 0.03 eval 3 drops out and 35 comes in); their order changes with L.

## 4. Proposed batch
**Box layout** (glock_public and hard_ab take SEED per invocation):
- A grasp-lock box runs seed 42 over its episode list, then seed 43, in waves of TRAIN_SLOTS 2 (two episodes per wave),
  NREP 10, CURVE_REP 3, EVAL_TIMEOUT 1200.
  - This is the transfer check's own pattern, except that the pair is two episodes instead of two arms.
- A standard-learner box runs one seed, as the c01s42 / c01s43 boxes did.
- Run ids carry `-mev`. Each box makes one store push, then the platform pushes and self-destroys.

**Cost basis** [E, from measured runs]:
- Grasp-lock wave of 2 at 70M with curve and 10 evaluations: 1.2–1.5 h [M basis: orcB 30 Oct, 71–75 min training +
  6–7 min curve + 4–8 min evaluations; one training alone saturates the GPU at 36–44 min].
- Box overhead (boot, setup, pulls, verify, push): 0.3–1.0 h [M: 0.2–0.75 h setup, 43 min under HF 429].
- Standard learner, one training per box, 250M, NREP 10: 2.0–2.3 h [M: c01s42 / c01s43, actual $3.08 / $2.91].
- Two standard trainings on one box: 3.4–4.0 h [M: std0116 3.2 h, std1928 3.7 h at NREP 5; +0.2 h for NREP 10 is E].
- Confirmation box: $1.2–2.5 [M: c33B $1.21 for 1 episode × 10 draws, H5 $2.45 for 20 × 10].
- Price: RTX PRO 6000 on demand, $1.18–1.47/h [M 30–31 Oct]; central $1.40.

| box | content | hours | cost (central) | in |
|---|---|---|---|---|
| G1 `mevG1` | glock 20 + 8 (LIB library_v3x: v3x differs from v3 only in the beige cup), s42 then s43: 2 waves | 2.7–4.0 | $3.2–5.9 ($4.7) | O1–O4 |
| G2 `mevG2` | glock spoon pilots 33 (`ENV_EP33="CURR_SCALE=0.4"`) + 15: 2 waves | 2.7–4.0 | $3.2–5.9 ($4.7) | O1–O4 |
| S1a / S1b `mevS1s42` / `mevS1s43` | std eval 1, carve_rerun recipe (PIECES ev01, MA_ARGS), one seed each | 2.0–2.3 each | $2.4–3.4 each ($3.0) | O2–O4 |
| C1 `mevC1` | official confirmation of wave 1's candidates (section 5) + draw 1 for the pack | 0.8–1.7 | $1.2–2.5 ($1.8) | O1–O4 |
| G3 `mevG3` | glock spoon 5 + 32, 6 + 3: 4 waves (wave 2, only if the pilots pass) | 5.1–7.0 | $6.0–10.3 ($8.5) | O3–O4 |
| C2 `mevC2` | confirmation of wave 2 | 0.8–1.7 | $1.2–2.5 ($1.8) | O3–O4 |
| G4 | glock 14, 16, 10 (LIB v3, PIECES ev10 at 0.3 kg for eval 10's mass_arm source): 2 waves + 2 single | 4.1–5.7 | $4.8–8.4 ($6.9) | O4 |
| G5 | glock 35–38: 4 waves | 5.1–7.0 | $6.0–10.3 ($8.5) | O4 |
| S2a / S2b | std 19 + 30 (no pieces), one seed each | 3.4–4.0 each | $4.0–5.9 each ($5.2) | O4 |
| S3a / S3b | std carve 25 (ev25), one seed each | 2.0–2.3 each | $2.4–3.4 each ($3.0) | O4 |
| S4a / S4b | std 28 (its own boxes: default pot) | 2.0–2.3 each | $2.4–3.4 each ($3.0) | O4 |
| C3 | confirmation of the O4 additions; eval 28 never on a box with ev01 | 0.8–1.7 | $1.2–2.5 ($1.8) | O4 |

| option | boxes | cost [E] central (range) | LB at L = .05 [E] | $ per +0.001 LB |
|---|---|---|---|---|
| O1 cheapest (glock top 4: 20, 8, 33, 15) | G1, G2, C1 | $11.2 ($7.6–14.3) | +0.0045 | 2.5 |
| **O2 top-k = wave 1** (O1 + eval 1) | G1, G2, S1a, S1b, C1 | **$17.2 ($12.4–21.1)** | +0.0055 | 3.1 |
| **O3 recommended** (O2 + wave 2: 5, 32, 6, 3) | + G3, C2 | **$27.5 ($19.6–33.9)** | +0.0086 | 3.2 |
| O4 all 20 × 2 seeds | + G4, G5, S2–S4, C3 | $67.1 ($49–80) | +0.0093 | 7.2 (the additions: ≈ $57 per +0.001) |

- **Credit** [E]: ≈ $33 at 06:35 UTC (STATUS) minus the transfer check (central $8.7, $6.5–11) leaves ≈ $24 ($22–27).
  - O2 fits. O3 may need a small top-up (central ≈ +$4, up to ≈ +$12). O4 needs ≈ +$45.
  - Check the Vast balance before the GO; other sessions also spend.
- **Recommendation.** If gate 3 gives Δ̂ ≥ 0.06: O2 now, then wave 2 of O3 after C1 and the spoon-pilot reading, on a
  separate owner GO. If Δ̂ < 0.06: O2 only.
  - The O4 additions buy almost nothing on the board. Evals 14, 16, 25 and 30 can be retrained as insurance (≈ $5–10
    per pair) only if the owner wants robustness against a checkpoint re-run.
- **Order and wall clock.**
  - G1, G2, S1a and S1b in parallel, started 10–15 min apart. Each pulls ≤ 10 store files, which is easier on HF 429.
  - C1 when the last one ends: wave 1 takes ≈ 4–6 h end to end.
  - Wave 2 ≈ 6–8 h more. Everything fits before the 4 Nov freeze.
  - If HF 429 persists, run the boxes one at a time: ≈ 13 h for wave 1.

## 5. Pre-registered adoption rule (fixed now, before any transfer-check or retrain result; GT-free)
1. **Seeds and checkpoints.**
   - Seeds 42 and 43 for every retrained episode, fixed now.
   - Each training's checkpoint is chosen by its job's own rule, on sim_vs_ref against our reference: grasp lock takes
     the best mean of CURVE_REP 3 official evaluations per checkpoint; the standard learner takes hard_ab's sweep.
   - Then NREP 10 evaluations on the training box.
2. **Candidate per episode.** The seed with the higher training-box 10-evaluation mean. Within 0.005, the one with the
   lower sd (ddof 1). If still tied, seed 42.
3. **Verification** (B3). If it fails, that episode is INVALID and its packed policy stays.
4. **Confirmation.**
   - N = 10 draws of the candidate with the pristine kit evaluator, on a confirmation box (h5 protocol, as c33B and
     e1conf2).
   - Every other episode keeps its packed rollout (KEEP_RESULTS), and `EVAL_ONLY` / `EPS_ONLY` = the candidates.
   - Each draw is scored as sim_vs_ref against the same reference (fingerprint checked); the mean and sd use ddof 1.
   - Fewer than 8 scored draws: INCOMPLETE. Only the confirmation is repeated, never the training.
   - Reason [M]: the training box alone is not enough. It showed 0/10 bad draws for packed standard-learner policies
     that the official evaluator failed 5/22 times (30 Oct).
5. **BOARD SWAP** iff the confirmation mean ≥ the packed draw of the pack on the board when the rule is applied.
   - Pack 7: `summary.txt` above.
   - If pack 8 is uploaded first, eval 1's bar is 0.9232.
   - Eval 1 must also reach ≥ 0.9241, the c01s43 carve's 20-draw mean: the standing alternative swap.
6. **INSURANCE SWAP** (offered; the owner decides).
   - Condition: mean < the bar, mean ≥ level + 0.03 and sd ≤ the level's sd. Level and sd are those of section 1:
     eval 33 from c33B; eval 1 from std0116 under pack 7 or from c01s43 under pack 8.
   - It is reported with its expected board cost, (mean − bar) / 20 × 0.76 [E].
   - It can arise only where level + 0.03 < bar: evals 1 (pack-7 basis: ≥ 0.8519, sd ≤ 0.2387), 3 (≥ 0.9339,
     ≤ 0.0717), 14 (≥ 0.6452, ≤ 0.1989), 16 (≥ 0.8429, ≤ 0.0767), 25 (≥ 0.8801, ≤ 0.0988) and 30 (≥ 0.8284, ≤ 0.2552).
   - Everywhere else an insurance pass is also a board pass.
7. **Otherwise KEEP** the packed policy and its rollout.
8. **Packing.**
   - An adopted episode's rollout is draw 1 of the confirmation, taken by position, never by score.
   - All other rollouts are reused byte for byte.
   - A CPU repack (the pack 7 method) gives a pack-9 candidate. **The owner decides any upload.**
9. **Spoon stratum** (prior mass). Pilots 33 and 15 run in wave 1.
   - Wave 2 (5, 32, 6, 3) is proposed only if neither pilot's confirmation mean falls below its level − 0.02: 33
     below 0.914, 15 below 0.9397.
   - Both below: the stratum is closed (no more spoon retrains). One below: the owner decides.
   - The per-episode rule still governs every spoon swap.
10. **Reported with the readings, not part of the rule.** Per episode:
    - both seeds' training-box means and the confirmation mean, sd, min and n;
    - Δ vs level (masses + seed + code), the SE of the mean, and evaluation timeouts;
    - the config diff against the packed checkpoint and the masses loaded.
    - The spoon and masses strata are summarised apart.

## 6. Build items (next step, CPU only; nothing exists yet)
- **B1 `ops/jobs/mass_eval.sh`** (new), one job string per box.
  - **Pulls.** Episode sources as in section 1, with PULL_SUB and a single-file pull for `rest_check.json`. md5 and
    fingerprint are checked against section 1, with refusal on a mismatch. The props md5 d5508930… is asserted. The run
    id must contain `-mev`.
  - **glock mode.** `mass_arm.py --arms "mass1:<props>" --seeds "42 43"` per episode, then per seed `glock_public.sh
    SPLIT=eval REUSE_REF=1 REQUIRE_REUSE=1 NO_PUSH=1 EVAL_TIMEOUT=1200 NREP=10 CURVE_REP=3
    PAIRS="<N>:local:mck:mass1s<seed> …"`.
    - `ENV_EP33="CURR_SCALE=0.4"`. LIB is set per box.
    - Eval 10: `/content/assets` with PIECES ev10 and no MA_ARGS, as mass_arm's 0.3 kg source.
  - **std mode.** `carve_rerun.sh` / `hard_ab.sh SPLIT=eval CR=0 SUF=s` with MA_ARGS, the packed PIECES, `NREP=10` and
    `SEED`, on the pulled `refs/perc2mck/ep<N>` (as the c01 job string in `carve-20261030/RETRAIN_PLAN.md` section 3).
  - One store push at the end.
- **B2 `glock_public.sh`.** Today a PERC prefix needs SPLIT=public (line 159).
  - Allow it with SPLIT=eval only when RUN=local and REQUIRE_REUSE=1: no perception and no rebuild on eval. Off by
    default.
  - Old vs new with the hook off must give an identical result (as `masses-transfer-20261031/cpu/out/equiv.txt`).
- **B3 verification** (`tools/mass_verify.py --eval` or a sibling). For each chosen checkpoint it follows saved config →
  `task.parquet` → URDFs and checks:
  - the props masses, the COM unchanged, mesh files byte-identical to the source asset folder;
  - glock: the fingerprint as in section 1. std: the parquet md5 as in section 1, plus `/content/assets` URDF masses
    equal to props and the packed pieces;
  - steps 70,004,736 / 250,003,456 and `reset.seed`;
  - rollouts' `checkpoint_sha256`;
  - eval timeouts (rc 124/137).
  - It also prints the config diff against the packed checkpoint's saved config: one targeted download per packed
    checkpoint, header read only.
- **B4 `hard_ab.sh` EVAL_TIMEOUT hook** (opt-in, as glock_public). Physics box p3ms1 was lost to a 30-min evaluation
  stall.
- **B5 confirmation job.** `h5_reeval.sh` with:
  - `RUNS_EXTRA` (the mass runs' `refs/mass1_sf/ep<N>`, `refs/mass1s<seed>_glockt/ep<N>`);
  - `PICK_EXTRA="EP:RUN:ck=<path>"`;
  - `MA_ARGS`, plus `ASSET_PIECES_EXTRA=meshes/carve/ev01` only when eval 1 is a candidate;
  - `KEEP_RESULTS="20261026-pack6-5203d42 20261030-c33B-0202139"`, plus `20261030-e1conf2-d41382e` if pack 8 is on the
    board;
  - `EVAL_ONLY` = `EPS_ONLY` = the candidates;
  - `PACKED_TXT` = the on-board pack's `summary.txt` (h5 hard-codes pack 6's today);
  - an assertion of the `/content/assets` masses before the evaluator runs.
- **B6** A CPU mock of every box string (stub trainer and evaluator, as `masses-transfer-20261031/cpu/mock`), `bash -n`
  on every script, then two reviews.
- **B7** The CPU repack script for the pack-9 candidate.

## 7. Integrity
- **No ground truth.** Eval episodes have none. References, objects and slot order are our own and allowed. Choices
  are made on sim_vs_ref against our reference only.
- **Fixed masses.** The masses were fixed by the physics session before any eval work. They were never fitted to mocap
  or eval results, and they do not change after any result here.
- **Public and eval kept apart.** Only the public transfer check's verdict and its reported Δs decide the scope (gate
  3). No eval result tunes anything; the eval rule only accepts or rejects a swap.
- **Existing runs preserved.** Runs use new ids and new folders (`refs/mass1*`, `results/mass1s*_glock_public`). Packed
  runs and references are untouched, and `tools/no_oracle.py` still guards every pack input.
- **Spend.** Every box needs the owner's GO, a ledger line, self-destroy and the stall watchdog. Kaggle uploads are the
  owner's.
