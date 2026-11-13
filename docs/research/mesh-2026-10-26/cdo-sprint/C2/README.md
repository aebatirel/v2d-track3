# C2: scan-free pitcher and rack rebuilds (CD-O sprint)

**Status (2026-10-31 ~22:00 UTC).** Done. CPU only. Cost about $0.02 [E]: one Vast box was created for track R and
destroyed unused; everything else ran locally at $0.
- **Nothing is adopted.** Neither track is a CD-O WIN, so pack 9a+ is unchanged: eval 20 keeps the library_v3 pitcher
  and the 5 rack pairs keep the C0 rack.
- Both pre-registered hypotheses are **falsified**: H-P (pitcher) and H-R (rack).
- The two verifiers found **no blocking item**. So in this step nothing was fixed, re-run or re-scored. Their
  non-blocking corrections are listed in section 6.
- Nothing was packed or sent to the pack lane.

Tags: [M] measured without ground truth; [D] diagnostic, scored against the public scan after inference; [E] estimate;
[H] hypothesis. Repo paths are relative to `docs/research/mesh-2026-10-26/` unless they start with `docs/`.
`SCR` = `/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad`.

## 1. Answer

| Track | Object (eval pairs) | Baseline CD-O cm [D] | Pick CD-O cm [D] | add_med mm (gate) | Flips | WIN | AUC guard [D] | Adopted |
|---|---|---|---|---|---|---|---|---|
| P | water_pitcher (1: eval 20, slot 1) | library_v3 0.8942 | **1.1600** (gate <= 0.8742) | 11.165 (<= 9.97): FAIL | 0/32 | **no** | not run (WIN-gated, PREREG 6) | no |
| R | plastic_dish_rack (5: evals 14, 15, 16, 28, 30) | C0 prim 0.45604 | **0.4413** (gate <= 0.43604) | 6.56 (<= 7.79): pass | 0/7 | **no** | PASS, reported only | no |

- **Board.** Pack 9a+ scored **0.33234** on Kaggle (measured). C2 changes no shipped mesh, so the board stays at
  0.33234.
- **If the picks had shipped [E]** (C0's model: hidden scans = public scans; one-shot public CD-O at the eval seed;
  board = pair-weighted mean over 36 pairs):
  - rack: 5 x (0.4413 - 0.45604) / 36 = **-0.0020**, giving 0.3303;
  - pitcher: 1 x (1.1600 - 0.8942) / 36 = **+0.0074**, giving 0.3397.
- **Rack gain.** The rack pick is better than C0 by 0.0147 cm, but this is below the 0.02 margin. The gain mixes three
  changes, which one scoring cannot separate:
  - C0b's scan-free replacements (wall T 4.56 mm, s0 >= T, no marker balls);
  - the A1 point cleaning;
  - option K (fitted peg aspect).

## 2. Verdicts

**P, water_pitcher: H-P FALSIFIED.** H-P needed CD-O <= 0.60 and a WIN; neither holds. The PREREG predicted "likely
falsified" before any build.
- **GT-free cause [M].**
  - Our ep22 RGB crop shows an elephant-shaped watering can, not a near-axial pitcher.
  - Every axis tried gives rotational consistency >= 9.15 mm.
  - lathe_obs's fitted axis is near-horizontal:
    - ep22's axis (the pick's) is 88.2-89.2 deg from the observed resting up;
    - ep21's is 80.5-81.3 deg from it.
  - The camera covers only 60-90 deg of azimuth, so the far side is never seen.
- **The pick.** The fidelity selector picked a lathe plus a splat of the seen surface: a closed, thickened shell of
  one side only.
  - The lathe body is 28.8 % of the pick's area, and about 80 % of it lies more than 5 mm from the splat [M] (verify N10).
  - This hurts CD-O and registration [H].
  - The selector prefers one-sided splats [H], as C1/T2 also noted.
- **Rest check, reported only [M].** library_v3 and the pick are both UNSTABLE at every observed rest.
  - The rest-up-axis lathes stand at all 9 ep22 rests, but that is in-sample: the axis is the resting up of those same
    frames.
  - On ep21's 8 rests, ep22r_g0 passes 1 and mergedr_g0 passes 3 (verify N5).

**R, plastic_dish_rack: H-R FALSIFIED.** CD-O is 0.4413, above the 0.436 gate; the strong claim (<= 0.40) also fails.
- **The pick: K/ep12_nomk**, by obs_fidelity: 5.483 mm, against 5.533 mm for the best base mesh and 5.536 mm for the
  C0 mesh, all on the same cleaned points.
- **Residuals are near the noise level** (obs->mesh 2.49 mm). The largest outside cluster is depth-edge smear.
- **Predictions.**

  | Prediction | Result | Verdict |
  |---|---|---|
  | E (right-end draft), s1e >= 0.2 | joint s1e 0.082 | falsified |
  | K (peg aspect), kappa > 1.2 | joint 1.43 / 1.57; picked ep12 fit: front row 0.956 | holds on the joint, fails on the picked fit |
  | Q (quadratic cup holder) | gy -0.77 /m | holds |
  | fidelity gain >= 0.05 mm | 0.050 at 3 decimals; 0.0498 unrounded (verify N1) | holds at 3 decimals, fails unrounded |

- **ADD is worse** than both baselines: 6.56 mm against C0's 5.63 and the library's 5.79. It is still inside the gate.

## 3. Files

| Track | Folder | Pick (committed, byte-identical to the scored file) | sha256 | PREREG / amendments | Pick commit, score | Verify |
|---|---|---|---|---|---|---|
| P | `cdo-sprint/C2/P-pitcher/` | `meshes/ep22_water_pitcher_g1_a2.glb` (sha1[:16] `478b9fb3cc65c841`) | `fadf3e7b7c5104b2c68799a3d9da6af42a881624caea7f405d8529010ec6d1f6` | 5982c31; A1 07d2536 (before build); A2 cc63fc2, text repaired in 1230b6d (post hoc, GT-free, before scoring) | 3ded2f9; d8ff6ac | `verify.md` (3020cd4) |
| R | `cdo-sprint/C2/R-rack/` | `meshes/plastic_dish_rack_c2r_K_ep12_nomk.glb` (sha1[:16] `7f4eab701769d264`) | `92d9fed04f938f1859f4bcbf488babee0dd4582ee71d8e08aa1c9ecb53703966` | 01c25d2; A1 945baa5 (before any C2/R build) | 8d53a60; 0683232 | `verify.md` (9174cde) |

- Each track folder holds PREREG.md, NOTES.md, RESULTS.md, scripts/, results/ and meshes/.
- Score records:
  - P: `results/score_p.jsonl` (1 line, 32 seeds).
  - R: `results/score.jsonl` (1 record, 7 seeds).
- The verifiers checked that each mesh_metric sha1 has exactly one score record.
- R's guard: `R-rack/results/guard_result_c2r.json`, with the run JSONs in `R-rack/results/auc/`.
- Report-step files: this README and `NOTES.md`.

## 4. Rules and integrity (as C0b; both verifiers confirmed these)

- **GT-free construction and choice.**
  - No scan, mocap, parquet pose or `*_align` file was read before scoring.
  - Neither track aligns to library_v3: there is no ICP to it and no frame_tf.
  - The frame comes from our library-seeded tracks (C0b AUDIT 161, open question F4). That is inherited, not an
    alignment.
- **Constants trace to C0b AUDIT / REPLACEMENTS**, with no scan-derived or undecided-U constant. Citation slips:
  - P cites id 121 for `--tmax 0.008`. The value comes from C0b lathe_args and REPLACEMENTS 16/40/58.
  - R's kappa bounds (0.5, 3.0) are a new generic value with no audit id, and they never bind.
  - R calls id 87 KEEP; REPLACEMENTS classes it TH, and the kept values were used.
- **Order.** Each PREREG was pushed before building, and each pick was pushed before its one scoring (git and
  push-reflog times are in each verify.md).
- **Inputs.** Both tracks used the C0b box's pass-B observed points (store run `mesh-20261031-c0b-00e8584`), with input
  shas checked.
  - P: the PREREG says local `obs_c0b.sh`. The swap is recorded only in NOTES and RESULTS (verify N7). Equivalence is
    proven for ep21 pass A; elsewhere it rests on identical code and identical input shas.
  - R: the points were cleaned by `clean_pts.py` under amendment A1.

## 5. AUC guard [D]

- **P:** not run. Under PREREG 6 the guard runs only after a WIN. The runner (`run_auc_guard_p.sh`, `check_base_p.py`,
  `guard_eval_p.py`) is ready for ep21 / ep22.
- **R:** **PASS** under C0's rule: mean dAUC >= -0.005, min >= -0.02, mean dMPPE and dRPE <= +0.2 cm.
  - Setup: 5 single runs; the C0 base runs were reused after all reuse checks passed.
  - Overall: mean dAUC **+0.0147**, min -0.0076 (ep12), mean dMPPE -0.0855 cm (printed as -0.086), mean dRPE
    -0.038 cm.
  - Per twin:

    | Twin | dAUC |
    |---|---|
    | ep12 | -0.0076 |
    | ep13 | +0.0078 |
    | ep26 | -0.0048 |
    | ep27 | +0.0169 |
    | ep31 | +0.0612 |

  - The biggest drop, ep12, is the build episode, so it is in-sample (rack AUC 0.9997 -> 0.9665).
  - For comparison, C0's rack scored +0.0158 / -0.0092.
  - This PASS is reported only: adoption needs a WIN as well.

## 6. Verifier corrections (non-blocking; nothing changes a decision)

**P** (`P-pitcher/verify.md`):
- **N1.** "87-89 deg" holds only for ep22's axis; ep21's is 80.5-81.3 deg from the resting up.
- **N2.** "80-85 % outside any lathe" holds only for the fit-axis lathe. The rest-up lathes leave 23-37 %.
- **N3.** The tmax citation (see section 4).
- **N4.** Every lathe_obs appendage splat is inside out (negative signed volume): the pick's splat is -964 cm3, and
  -754 cm3 is the whole mesh. The same holds for other g1 meshes, including C0's blue cup and C0b's blue and beige
  cups. CD-O and AUC do not depend on face orientation, but any COM, rest or simulator use of these meshes does.
  **For the C0b / E0b owners and lathe_obs's splat step.**
- **N5.** The rest check is in-sample (see section 2).
- **N6.** A better pitcher is worth more than "at most -0.01". At the disclosed generator best (0.38 cm) it would give
  -0.014 [E]; a perfect mesh would give -0.025 [E]. The rack still ranks higher.
- **N7.** The input source (see section 4).
- **N8.** "mesh_metric sha1" is the mesh's sha1[:16]. The splat is closed, not "open".
- **N9.** A1 drew its rationale from the obs_all previews (library_v3 ROI). A1 only added candidates, none of which
  was picked.
- **N10.** The off-surface lathe body (see section 2). Proposed falsifier: one scoring of the splat-only variant.

**R** (`R-rack/verify.md`):
- **N1.** The fidelity gain is 0.0498 mm unrounded.
- **N2 / N9.** Box 58571056's destroy time is inconsistent (19:56 or 19:58 UTC), and "gone from `vast show`" is
  **not confirmed**: neither the verifier nor this report session has a Vast key. **Open: the orchestrator should run
  `ops/vast.sh show` once.** The box never started, so if it still exists it bills storage only.
- **N3.** The dev smoke build finished 45 s before the PREREG commit. The thresholds do not look fitted to it: the E
  prediction already failed on the smoke values.
- **N4.** The byte-identity regression covered C0's code path. The C0b path was checked by reading the diff.
- **N5.** The options came from obs_all diagnostics (S-input). No constant of the pick comes from them.
- **N6.** The kappa bounds (see section 4).
- **N7.** The id 87 class (see section 4).
- **N8.** The inherited frame (see section 4).
- **N10.** ADD is worse; the CD-O change also mixes the point source and the ep12-only fit; the ep12 guard drop is
  in-sample (see section 5).

## 7. What an eval-built version would need

There is no eval ground truth, so an eval-built mesh cannot be scored. A method should first WIN on its public twins.
Neither C2 method has, so **neither qualifies for an eval build as it stands**. If a later version wins, the eval build
would need the following.
- **Rack (evals 14, 15, 16, 28, 30).**
  - Inputs: E0b's C0b-rule pass-B eval rack points. E0b X1 covers all 5 rack episodes; that run is in progress.
  - Cleaning: `R-rack/scripts/clean_pts.py` (A1), run unchanged. The eval points will likely carry the same clutter:
    E0b X15 notes that rack candidates built on uncleaned C0b points span metres [M, public].
  - Build: `c2r_build.sh` with the frozen option set. Pick by obs_fidelity on all eval rack points, then kit
    `budget_mesh(4096, 4096)`.
  - The frame check needs a usable reference: E0b's public rack references are metres wide (X15).
  - A PREREG written before any eval candidate.
- **Pitcher (eval 20).**
  - Eval 20 is one of E0b's 14 episodes, because its slot 0 is the blue cup. So E0b's pass A should hold the pitcher
    [E; check when the box finishes].
  - E0b's pass B covers only the 19 target object-episodes, so a pass-B pitcher file for eval 20 would need its own
    C0b-rule build.
  - A pitcher method also needs more than a lathe: H-P2, a mirror-completed closed shell picked by a rule that is not
    fidelity-only.
  - The splat orientation (P N4) must be fixed before any simulator use.
  - The simulator copy on eval 20 stays library_v3 with the 25 Oct arc foot, whatever the scored mesh.

## 8. Next (proposals, not run)

- **Rack** remains the largest weighted term: 5 pairs x 0.456 cm.
  - The cleaned points leave little structure to fit, since residuals are at the noise level.
  - [H] Next options: score the C2/R base mesh to separate the replacements and cleaning from K (one more scoring:
    needs a dated PREREG), or a joint eval-pair fit once E0b's points exist.
- **Pitcher:** H-P2 (above). Falsifier: one scoring of the splat-only variant (P N10). Worth up to -0.014 to -0.025 on
  the board [E].
- **Housekeeping:** confirm Vast box 58571056 is gone (R N2). Send P N4 (inverted splats) to the C0b / E0b owners.
