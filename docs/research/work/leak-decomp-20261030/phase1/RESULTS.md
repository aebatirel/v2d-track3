# Phase 1 results: template (L2), tracker (L3) and registration (L1) leaks on the 20 public episodes

30 Oct 2026, 22:00–22:50 UTC. Readings of `../PLAN.md` §2 and §4 at the reference level, from the Phase-1 tracks
(runs `20261030-orcP1{a,b,c}-87fc869`). CPU only, on this VM (4 cores), $0. Labels: [M] measured, [E] estimate,
[H] hypothesis.

**Oracle side.** Everything here reads public mocap and the public scans, after inference. Nothing feeds eval
inference. No X\*_trk and no registration correction becomes a default anywhere. All outputs sit under this folder
(`leak-decomp`) or under `scratchpad/leak/p1/oracle_*`; `tools/no_oracle.py` refuses both.

Arms (one depth cache, box and commit per episode; BUILD.md §1):
- **P_o**: our templates (library_v3);
- **P_s**: the organiser scans as templates, tracked in the scans' own frames [oracle];
- **P_o2**: a P_o repeat, on the 10 Phase-2 twins;
- **refine P**: the 25 Oct baseline tracks (`refine/in`, library_v2), for drift.

Scoring conventions (PLAN §2), through the kit's own chain (`tools/xstar_fit.py score_track`):
- **lib**: library_v3 submitted at the kit registration X_kit (the leaderboard convention).
- **\***: scan frames by X\*_geom, scored with the scan. P_s is native here: its \* is the identity registration.
- **trk**: X\*_trk refitted to mocap for each track. Diagnostic only; an upper bound of what one constant body offset
  per (episode, object) recovers.

## Verdict (reference-level rule, PLAN §4, fixed before the reading)
Rule: leaks = mean ΔR ≥ 0.01, ≥ 12/20 episodes of that sign, and for tracking arms > 2× the P_o-repeat noise;
no leak = |ΔR| < 0.005. Primary = all 20 episodes; beside it, without the two known outliers ep0 and ep23.

| Reading | Mean ΔR (20) | w/o ep0, ep23 | + / − | Verdict [M] | LB, 7 twin evals with S_e ≥ 0.8, c 0.74–1.0 [E] |
|---|---|---|---|---|---|
| **L2 template**, \*: R\*(P_s) − R\*(P_o) | **+0.0387** (median +0.029) | +0.0382 | 17 / 3 | **leaks** (noise ×2 = 0.0024) | **+0.012 to +0.017**; spoon evals +0.010 to +0.013 [E-analogy] |
| L2, template also submitted: R\*(P_s) − R_lib(P_o) | +0.0342 | +0.0340 | 16 / 4 | leaks | +0.012 to +0.016 |
| L2, library_v3 still submitted: R_lib(P_s) − R_lib(P_o) | +0.0060 | +0.0027 | 12 / 8 | inconclusive (no leak w/o outliers) | +0.008 to +0.010 |
| L2 after a constant offset: R_trk(P_s) − R_trk(P_o) [oracle] | +0.0060 | +0.0044 | 15 / 5 | inconclusive (no leak w/o outliers) | – |
| **L3 tracker, given a true template**: 1 − R\*(P_s) | **+0.0759** | +0.0330 | 20 / 0 | **leaks** | **+0.008 to +0.010**; spoon +0.010 to +0.014 [E-analogy]; evals 10, 30 (L3 0.092, 0.132) not converted |
| – of it, constant part R_trk(P_s) − R\*(P_s) | +0.0222 | +0.0246 | 19 / 0 | leaks | – |
| – of it, varying part 1 − R_trk(P_s) | +0.0537 | +0.0085 | 20 / 0 | leaks (inconclusive w/o outliers) | – |
| **L1 registration loss** on P_o: R\* − R_lib | −0.0045 | −0.0042 | 7 / 13 | **no leak** (lib scores higher) | −0.0003 to −0.0004 |
| L1 registration loss on P_s | +0.0282 | +0.0313 | 17 / 3 | leaks | – |
| L1 registration loss on refine P (Tier A input) | −0.0029 | −0.0031 | 7 / 12 | no leak | – |
| Drift: R\*(P_o) − R\*(refine P) | −0.0038 | −0.0035 | 4 / 7 | no leak (ep18 sweeper −0.096) | – |

Reading [M]:
1. **The template leaks at the reference level.** With the true shape as template, the track gains +0.039 in \*.
   - It is positive on 17 of 20 episodes, and 32× the mean GPU repeat noise (0.0012).
   - The gain is carried by:
     - the pitcher: +0.281 on ep21, +0.249 on ep22, per object;
     - the boards: ep23's identity swap disappears (0.04 → 0.998); ep24 +0.039;
     - ep13: +0.094 (blue cup +0.125, rack +0.062);
     - ep27: +0.059 (pot +0.117);
     - ep43 (+0.050), ep18 (+0.045, see drift) and the dust pans (+0.017 / +0.023).
   - It is negative on 3 episodes:
     - ep0 (−0.869), where the scan template fails at frame 0;
     - ep12 (−0.035), where P_s carries a constant offset: P_s trk 0.998;
     - ep45 (−0.012).
   - The mean is fragile to dropping one outlier: without ep23 alone it is −0.0096, without ep0 alone +0.087. Without
     both it is +0.038 and still leaks; the median is +0.029.
2. **Most of the template gain is a constant body offset, not better per-frame tracking.**
   - After X\*_trk removes one constant offset per (episode, object), P_s gains only +0.006 over P_o (+0.004 without
     the outliers; no leak).
     - The pitcher shows it most clearly: ep21 P_o \* 0.831 → trk 0.9945; P_s \* 0.976 → trk 0.9956.
   - The constant offset of the track from X\*_geom shrinks with the true template: median 1.07 cm for P_o vs 0.62 cm
     for P_s, over 29 (episode, object) pairs without ep0 and ep23.
   - So our templates mostly move where the tracker puts the body frame. ep23 is the exception: there the true
     template fixes a real tracking failure (the swap).
3. **The leaderboard value of a template depends on which mesh is submitted.**
   - If the true-shape mesh is tracked and also submitted, the gain is +0.034 (leaks): R\*(P_s) is the score of
     submitting the scan itself (FRAMES.md (b1′): budget-scan Δ −0.0002 mean).
   - If library_v3 stays the submitted mesh, its kit registration taxes the better track: R_lib(P_s) − R_lib(P_o) =
     +0.006, inconclusive. The same tax appears as L1 on P_s (+0.028, leaks). It matches FRAMES.md (a3): a perfect
     motion scores 0.9795 in lib.
   - [E] A GT-free template improvement pays on the leaderboard only if the improved mesh is also the submitted one.
4. **L3: with a true template, the tracker still loses 0.076 in \* (0.033 without ep0 and ep23).**
   - The largest losses:
     - ep0: 0.922, an init failure;
     - ep24: 0.151, boards; trk recovers to 0.986;
     - ep31: 0.132; the rack is at 0.803, trk 1.000;
     - ep11: 0.092; the blue cup is at 0.823, trk 0.823, so this one is NOT constant;
     - ep12: 0.062; trk 0.998;
     - ep18: 0.038; the dust pan.
   - Without the outliers, three quarters of L3 is a constant per-object offset (0.025 of 0.033). It is consistent
     with frame-0/init error on near-static objects; see [H1].
   - The varying part is 0.0085, inconclusive. It is concentrated in ep11's blue cup (cups nested; the oracle-twin
     result for eval 10 was perception-limited).
5. **L1 does not leak on our own tracks.**
   - On P_o: −0.0045 (lib slightly above \*). On refine P: −0.0029, the Tier A number reproduced on the Phase-1 tracks.
   - It does leak on P_s: +0.028.
   - So the kit registration of library_v3 is not a loss for the tracks we actually make. It becomes one as soon as
     the poses are physically right (item 3).
6. **Drift and noise are small.** Both readings are needed before Phase 2 can attribute anything to a stage.
   - P_o repeat on the same box:
     - 14 of 19 objects are bit-identical;
     - the rest (4 racks, 1 pitcher) differ by ≤ 0.21 cm and ≤ 0.72°;
     - ΔR\* is mean 0.0012, max 0.0063 (ep27).
   - P_o vs the 25 Oct tracks:
     - 18 of 33 objects are bit-identical;
     - mean ΔR\* is −0.0038 (no leak);
     - one large change: ep18's sweeper −0.096 (\* 0.9956 → 0.8994; mean shift 1.23 cm, max 15.7 cm), the library_v3
       flattened-underside sweeper vs library_v2 [H2]. ep31's sweeper is unchanged (+0.001).

Per object class [M] (per-object AUCs: the kit pins the scene on slot 0's frame 0, so they are not independent of the
other object; n is small, so these rows are indicative):

| Class | pairs | L2 \* | L3 | L1 loss on P_o | Reading |
|---|---|---|---|---|---|
| pitcher (ep21, ep22) | 2 | **+0.265 leaks** | +0.031 leaks | −0.013 (lib better) | the largest template lever; eval 20 |
| boards (ep23, ep24) | 4 | +0.498 leaks (+0.039 w/o ep23) | +0.076 leaks (ep24 0.16 / 0.14) | −0.000 no leak | ep23 swap fixed by the scans; ep24 loss mostly constant |
| rack (ep12, 13, 26, 27, 31) | 5 | +0.021 leaks (3 / 1) | +0.052 leaks (ep31 0.197) | −0.007 inconclusive | ep31 rack: constant offset (trk 1.000) |
| spoon proxies (sweeper ep18/31, dust pan ep18/39/40) | 5 | +0.028 leaks (4 / 1) | +0.029 leaks | **+0.011 leaks (5 / 0)** | thin objects: template, tracker and registration all leak a little; ep18 sweeper L2 is mostly the v3 regression |
| cups (ep11, 12, 13, 21, 22) | 6 | +0.025 inconclusive (3 / 2) | +0.042 leaks (ep11 blue 0.177) | −0.006 inconclusive | ep11 blue cup worse with the scan (−0.039), beige better (+0.108) |
| pot / lid (ep0, 2, 26, 27, 41–45) | 11 | −0.134 inconclusive (+0.029 w/o ep0) | +0.177 leaks (+0.012 w/o ep0) | −0.013 truth worse (lib better) | ep0 scan failure dominates |

## What this hands to the plan (PLAN §4 acting table; each item needs its own public gate and the owner's go-ahead)
- **L2 leaks at the reference level.**
  - LB [E]: +0.012 to +0.017 on the twin evals; with the improved mesh also submitted, +0.012 to +0.016. That is
    "top priority" by the plan's thresholds.
  - The plan's L2 trigger is the rollout contrast (AOI c2 − c1). This reading is its prior, not the decision.
  - Eval-side candidates, in LB order [E]:
    - the pitcher (eval 20: dT +0.13 at S 0.89);
    - the boards (eval 25);
    - the pot (evals 28, 1, 8);
    - the sweeper and dust pan (eval 19, and the spoon analogy).
  - A template fix is worth doing only together with the submitted mesh (Reading 3).
- **L3 leaks.**
  - The phase split decides the fix (Tier A A2/A5 on the Phase-1 tracks, still to run).
  - Here the constant part dominates: frame-0/init and the static rest of the rack and boards.
  - ep11's blue cup is the varying exception. Evals 10 and 30 are not converted (S_e < 0.8), though their twins carry
    the largest L3 (0.092, 0.132).
- **L1 does not leak on our tracks.** No registration-safe mesh is triggered (PLAN: needs L1 ≥ 0.03 on an object in
  ≥ 2 episodes; Tier A's flip rates are still to come). It becomes relevant only together with a template change.
- **Phase-2 inputs are sound.**
  - Grounding DINO ran on every arm; the depth cache was reused on all.
  - The cameras of the arms agree. Their cameras match the refine cameras that the hands were made on within ≤ 0.08 cm
    and ≤ 0.03° (ep13; ep45 0.03 cm; all others ≤ 5e-8). That is above the 1e-6 expectation of BUILD.md §5 risk 4,
    but sub-millimetre.
  - P_s of ep0 is unusable, but ep0 is not a Phase-2 twin.

## Outliers and caveats
- **ep0** [M]: P_s fails at frame 0 with the scan templates (pot 0.156, lid 0.001; job log 0.078). This was known from
  the 20 Oct code (refcheck chain §4), so it is not new. P_o on ep0 is 0.948.
- **ep23** [M]: P_o keeps the identity swap of the two boards (0.084 / 0.000, as on 25 Oct). P_s tracks both at
  0.999 / 0.997. The swap is template-dependent [H3].
- **The two outliers nearly cancel** in the 20-episode mean of L2 (−0.869 and +0.956). Every reading is given with
  and without them, and the verdicts agree except where noted.
- **ep12 P_s** carries a constant offset of both objects:
  - \* 0.938, but trk 0.998; lib 0.804;
  - perc2's own scorer says 0.997.
- **The job-log P_s numbers came from perc2's own scorer** (the old AUC code: no cup symmetry, 500 points,
  warp-to-start).
  - They differ from the kit chain by up to 0.06 (ep11 0.863 vs 0.908; ep12 0.997 vs 0.938; ep22, ep31).
  - The kit-chain numbers here supersede the work-log entry of 22:05.
- **Per-object values** depend on the slot-0 track through the kit's scene alignment.
- **The noise floor is within one box only** (BUILD.md risk 8). Cross-box GPU noise is not measured.
- **trk is a mocap fit and an upper bound.** It is never a fix.

## Hypotheses [H] and the experiments that would falsify them
- **H1:** L3's constant part is frame-0/init error on near-static objects (rack, boards), not a tracking bias.
  - Test: Tier A A5 (frame-0 re-anchor, body form) on P_s.
  - Falsified if the re-anchor recovers < 50 % of R_trk − R\* on ep12, ep24 and ep31.
- **H2:** ep18's sweeper regression comes from library_v3's flattened underside used as a tracking template.
  - Test: P_o on ep18 with library_v2's sweeper on the same commit and cache.
  - Falsified if it also scores ≈ 0.90 on the sweeper.
  - Before any eval action, check which template the eval-19 and eval-30 perception used.
- **H3:** ep23's swap is caused by our board templates.
  - Test: P_o on ep23 with one board's template replaced by its scan.
  - Falsified if the swap persists with either single replacement.
- **H4:** [E] the LB value of a GT-free template lies between the lib reading (+0.006) and the "also submitted"
  reading (+0.034), set by how close the new mesh's kit registration lands to the tracker's frame.
  - Test: rollout cells c1/c2 scored in lib and \* (Phase 2), plus a CPU check that submits the candidate mesh.

## Inputs, checks and cost
- **Store.** 3 summaries + 70 poses files, 5.0 MB, each by one `hf_hub_download`. No listing, no 429, no retry.
  - Per episode: `perc2/poses_world_vo.npz`, `perc2/poses.npz`, `perc2scan/poses_world_vo.npz`, and on the 10 twins
    `perc2rep/poses_world_vo.npz`.
- **summary.json** [M]: all 20 episodes ok on all 3 boxes, `all_ok` and `all_ran` true.
  - Every arm (50) has gdino true and the depth cache reused (`depth_ready` 0.9–11.5 s).
  - Camera max diff vs P_o: 0.0 on every arm.
- **Frame invariance [M]:** R\*(P_s) native (identity registration, scan frames) = R\*(P_s) via lib frames (X\*_geom
  there and back), 0.0000 on all 20 episodes (rule ≤ 0.002, PLAN §7 (b)).
- **perc2 time on the boxes [M]** (BUILD.md risk 2 was unmeasured): P_s 38–133 s per run, 1261 s in all, vs P_o
  36–78 s, 1119 s in all; that is 1.13×, inside the 1.0–2.0× estimate.
- **Scoring cost [M]:** P_o 6 min 38 s, P_s 10 min 32 s, P_o2 7 min 53 s (4 processes), plus `p1_check.py`. $0.
- **Code [M]:** scoring ran on the working tree on 0ec6b5a plus this step's new files. `p1_check.py` was first
  committed in the WIP a960523. `tools/xstar_fit.py`, `pipeline/frame_xform.py` and `tools/leak_read.py` are unchanged
  since 87fc869. `xstar_geom.json` md5 919ea341…; the refine `xstar_trk.json` md5 bd8432f1….

Files (this folder):
- `p1_check.py`, `p1_tables.py` and `scripts/p1_pull.py` (new);
- `p1_results.json`: every number above;
- `scores/xstar_trk_{Po,Ps,Po2}.json`: per-track lib / \* / trk / trk_ls with per-object AUCs and fits;
- `scores/p1_check.json`;
- `scores/xstar_trk_p1.log`.

## Tables (`p1_tables.py` output, verbatim; † = known outlier: ep0 P_s frame-0 failure, ep23 identity swap)

### Checks [M]

| ep | camera vs refine: max entry, max shift cm | P_o repeat: objects bit-identical; max shift cm, rot ° | P_s native \* | P_s via lib frames \* | Δ | perc2 vo AUC (other scorer) | frames |
|---|---|---|---|---|---|---|---|
| 0 | 1.1e-16, 0.000 | – | 0.0783 | 0.0783 | +0.0000 | 0.0778 | 373 |
| 2 | 1.4e-17, 0.000 | 2/2; 0.000, 0.00 | 0.9933 | 0.9933 | +0.0000 | 0.9933 | 343 |
| 11 | 2.5e-08, 0.000 | 2/2; 0.000, 0.00 | 0.9081 | 0.9081 | +0.0000 | 0.8629 | 137 |
| 12 | 2.1e-08, 0.000 | 1/2; 0.118, 0.50 | 0.9382 | 0.9382 | +0.0000 | 0.9974 | 181 |
| 13 | 5.8e-04, 0.077 | 1/2; 0.148, 0.50 | 0.9974 | 0.9974 | +0.0000 | 0.9977 | 190 |
| 18 | 2.3e-08, 0.000 | 2/2; 0.000, 0.00 | 0.9622 | 0.9622 | +0.0000 | 0.9625 | 353 |
| 21 | 2.6e-08, 0.000 | 1/2; 0.116, 0.58 | 0.9755 | 0.9755 | +0.0000 | 0.9748 | 186 |
| 22 | 3.3e-08, 0.000 | – | 0.9929 | 0.9929 | +0.0000 | 0.9873 | 189 |
| 23 | 3.3e-08, 0.000 | – | 0.9980 | 0.9980 | +0.0000 | 0.9986 | 325 |
| 24 | 2.4e-08, 0.000 | 2/2; 0.000, 0.00 | 0.8494 | 0.8494 | +0.0000 | 0.8490 | 275 |
| 26 | 2.2e-16, 0.000 | – | 0.9836 | 0.9836 | +0.0000 | 0.9836 | 158 |
| 27 | 1.8e-08, 0.000 | 1/2; 0.083, 0.72 | 0.9963 | 0.9963 | +0.0000 | 0.9963 | 246 |
| 31 | 4.9e-08, 0.000 | 1/2; 0.205, 0.58 | 0.8685 | 0.8685 | +0.0000 | 0.8628 | 290 |
| 39 | 4.9e-08, 0.000 | 1/1; 0.000, 0.00 | 0.9978 | 0.9978 | +0.0000 | 0.9976 | 319 |
| 40 | 2.4e-08, 0.000 | – | 0.9971 | 0.9971 | +0.0000 | 0.9976 | 260 |
| 41 | 1.4e-17, 0.000 | – | 0.9981 | 0.9981 | +0.0000 | 0.9981 | 299 |
| 42 | 2.6e-08, 0.000 | – | 0.9893 | 0.9893 | +0.0000 | 0.9891 | 257 |
| 43 | 4.1e-08, 0.000 | – | 0.9921 | 0.9921 | +0.0000 | 0.9921 | 326 |
| 44 | 6.9e-18, 0.000 | – | 0.9990 | 0.9990 | +0.0000 | 0.9990 | 249 |
| 45 | 2.7e-04, 0.028 | – | 0.9666 | 0.9666 | +0.0000 | 0.9668 | 290 |

frame invariance max |native − via lib| = 0.0000 (rule ≤ 0.002)

### Per episode [M]

| ep | objects | refine P lib / \* | P_o lib / \* / trk | P_o repeat \* | P_s lib / \* / trk | L2 = \*(P_s) − \*(P_o) | L3 = 1 − \*(P_s) | L1 on P_o: lib − \* | drift \*(P_o) − \*(refine) |
|---|---|---|---|---|---|---|---|---|---|
| 0 † | pot + lid | 0.9641 / 0.9612 | 0.9620 / 0.9476 / 0.9956 | – | 0.0778 / 0.0783 / 0.0790 | -0.8693 | 0.9217 | +0.0144 | -0.0136 |
| 2 | pot + lid | 0.9823 / 0.9792 | 0.9866 / 0.9805 / 0.9957 | 0.9805 | 0.9636 / 0.9933 / 0.9952 | +0.0128 | 0.0067 | +0.0061 | +0.0013 |
| 11 | blue + beige | 0.8978 / 0.8739 | 0.8978 / 0.8739 / 0.9302 | 0.8739 | 0.8825 / 0.9081 / 0.9097 | +0.0342 | 0.0919 | +0.0239 | +0.0000 |
| 12 | blue + rack | 0.9662 / 0.9738 | 0.9662 / 0.9734 / 0.9991 | 0.9736 | 0.8042 / 0.9382 / 0.9978 | -0.0352 | 0.0618 | -0.0072 | -0.0004 |
| 13 | blue + rack | 0.9605 / 0.9036 | 0.9595 / 0.9039 / 0.9748 | 0.9012 | 0.9645 / 0.9974 / 0.9985 | +0.0935 | 0.0026 | +0.0556 | +0.0003 |
| 18 | sweeper + pan | 0.9642 / 0.9680 | 0.9144 / 0.9168 / 0.9488 | 0.9168 | 0.9629 / 0.9622 / 0.9974 | +0.0454 | 0.0378 | -0.0024 | -0.0512 |
| 21 | blue + pitcher | 0.8325 / 0.8313 | 0.8325 / 0.8313 / 0.9945 | 0.8327 | 0.9634 / 0.9755 / 0.9956 | +0.1442 | 0.0245 | +0.0012 | +0.0000 |
| 22 | blue + pitcher | 0.8710 / 0.8710 | 0.8707 / 0.8684 / 0.9950 | – | 0.9654 / 0.9929 / 0.9957 | +0.1245 | 0.0071 | +0.0023 | -0.0026 |
| 23 † | board1 + board2 | 0.0414 / 0.0418 | 0.0414 / 0.0418 / 0.0418 | – | 0.9981 / 0.9980 / 0.9994 | +0.9562 | 0.0020 | -0.0004 | +0.0000 |
| 24 | board1 + board2 | 0.8117 / 0.8105 | 0.8117 / 0.8105 / 0.9859 | 0.8105 | 0.8498 / 0.8494 / 0.9863 | +0.0389 | 0.1506 | +0.0012 | +0.0000 |
| 26 | rack + pot | 0.9652 / 0.9565 | 0.9717 / 0.9602 / 0.9951 | – | 0.9442 / 0.9836 / 0.9970 | +0.0234 | 0.0164 | +0.0115 | +0.0037 |
| 27 | rack + pot | 0.9611 / 0.9376 | 0.9605 / 0.9378 / 0.9971 | 0.9441 | 0.9428 / 0.9963 / 0.9975 | +0.0585 | 0.0037 | +0.0227 | +0.0002 |
| 31 | sweeper + rack | 0.7999 / 0.8391 | 0.7998 / 0.8351 / 0.9977 | 0.8336 | 0.8096 / 0.8685 / 0.9974 | +0.0334 | 0.1315 | -0.0353 | -0.0040 |
| 39 | pan | 0.9602 / 0.9804 | 0.9602 / 0.9804 / 0.9961 | 0.9804 | 0.9935 / 0.9978 / 0.9978 | +0.0174 | 0.0022 | -0.0202 | +0.0000 |
| 40 | pan | 0.9570 / 0.9740 | 0.9570 / 0.9740 / 0.9853 | – | 0.9764 / 0.9971 / 0.9993 | +0.0231 | 0.0029 | -0.0170 | +0.0000 |
| 41 | pot | 0.9910 / 0.9881 | 0.9910 / 0.9881 / 0.9941 | – | 0.9954 / 0.9981 / 0.9983 | +0.0100 | 0.0019 | +0.0029 | +0.0000 |
| 42 | pot | 0.9915 / 0.9740 | 0.9903 / 0.9638 / 0.9954 | – | 0.9424 / 0.9893 / 0.9961 | +0.0255 | 0.0107 | +0.0265 | -0.0102 |
| 43 | pot | 0.9482 / 0.9429 | 0.9477 / 0.9425 / 0.9952 | – | 0.9525 / 0.9921 / 0.9954 | +0.0496 | 0.0079 | +0.0052 | -0.0004 |
| 44 | pot | 0.9967 / 0.9982 | 0.9967 / 0.9982 / 0.9987 | – | 0.9982 / 0.9990 / 0.9997 | +0.0008 | 0.0010 | -0.0015 | +0.0000 |
| 45 | pot | 0.9795 / 0.9789 | 0.9795 / 0.9789 / 0.9903 | – | 0.9306 / 0.9666 / 0.9931 | -0.0123 | 0.0334 | +0.0006 | +0.0000 |
| mean 20 | | 0.8921 / 0.8892 | 0.8899 / 0.8854 / 0.9403 | | 0.8959 / 0.9241 / 0.9463 | +0.0387 | 0.0759 | +0.0045 | -0.0038 |
| mean 18 (no ep0, ep23) | | 0.9354 / 0.9323 | 0.9330 / 0.9288 / 0.9872 | | 0.9357 / 0.9670 / 0.9915 | +0.0382 | 0.0330 | +0.0042 | -0.0035 |
| mean 10 twins | | | 0.9089 / 0.9044 / 0.9820 | 0.9047 | 0.9137 / 0.9487 / 0.9873 | +0.0443 | 0.0513 | +0.0046 | -0.0054 |

### Noise floor (P_o repeat, same box and cache) [M]

\*: mean |Δ| 0.00121, max 0.00630, RMS 0.00226, 5/10 episodes exactly 0; lib: mean 0.00170, max 0.01360; trk: mean 0.00006, max 0.00050. Per twin \*: ep2 +0.0000, ep11 +0.0000, ep12 +0.0002, ep13 -0.0027, ep18 +0.0000, ep21 +0.0014, ep24 +0.0000, ep27 +0.0063, ep31 -0.0015, ep39 +0.0000

### Verdicts, reference-level rule (PLAN §4) [M]

| reading | n | mean | mean w/o ep0, ep23 | + / − | min, max | noise ×2 | verdict (20) | verdict w/o ep0, ep23 | note |
|---|---|---|---|---|---|---|---|---|---|
| L2 template, \*: R\*(P_s) − R\*(P_o) | 20 | +0.0387 | +0.0382 | 17 / 3 | -0.8693, +0.9562 | 0.0024 | **leaks** | leaks | tracking arms; noise rule applies |
| L2 template, lib: R_lib(P_s) − R_lib(P_o) | 20 | +0.0060 | +0.0027 | 12 / 8 | -0.8842, +0.9567 | 0.0034 | **inconclusive** | no leak | beside: leaderboard convention |
| L2 template, trk: R_trk(P_s) − R_trk(P_o) | 20 | +0.0060 | +0.0044 | 15 / 5 | -0.9166, +0.9576 | 0.0001 | **inconclusive** | no leak | beside: after a constant offset per (ep, object) [oracle] |
| L2 with the template also submitted: R\*(P_s) − R_lib(P_o) | 20 | +0.0342 | +0.0340 | 16 / 4 | -0.8837, +0.9566 | 0.0034 | **leaks** | leaks | beside: leaderboard convention when the true-shape mesh is tracked AND submitted (= L2 \* − L1 on P_o) |
| L3 tracker given a true template: 1 − R\*(P_s) | 20 | +0.0759 | +0.0330 | 20 / 0 | +0.0010, +0.9217 | 0.0024 | **leaks** | leaks | tracking arm |
|   L3 constant part: R_trk(P_s) − R\*(P_s) | 20 | +0.0222 | +0.0246 | 19 / 0 | +0.0000, +0.1369 | 0.0024 | **leaks** | leaks | oracle fit, upper bound |
|   L3 varying part: 1 − R_trk(P_s) | 20 | +0.0537 | +0.0085 | 20 / 0 | +0.0003, +0.9210 | 0.0024 | **leaks** | inconclusive |  |
| L2 + L3 = 1 − R\*(P_o) (all tracking loss) | 20 | +0.1147 | +0.0712 | 20 / 0 | +0.0018, +0.9582 | 0.0024 | **leaks** | leaks | for scale |
| L1 registration loss on P_o: R\* − R_lib | 20 | -0.0045 | -0.0042 | 7 / 13 | -0.0556, +0.0353 | – | **no leak** | no leak | identical poses; no noise rule |
| L1 registration loss on P_s: R\* − R_lib | 20 | +0.0282 | +0.0313 | 17 / 3 | -0.0007, +0.1340 | – | **leaks** | leaks | P_s taken to lib frames by X\*_geom |
| L1 registration loss on refine P: R\* − R_lib | 20 | -0.0029 | -0.0031 | 7 / 12 | -0.0569, +0.0392 | – | **no leak** | no leak | Tier A input (FRAMES.md) |
| drift: R\*(P_o) − R\*(refine P) | 20 | -0.0038 | -0.0035 | 4 / 7 | -0.0512, +0.0037 | 0.0024 | **no leak** | no leak | code 87fc869 + library_v3 vs 25 Oct tracks |

### Per object class [M]

| class | reading | (ep, object) pairs | mean | mean w/o ep0, ep23 | + / − | min, max | repeat noise mean \|Δ\| | verdict | per pair |
|---|---|---|---|---|---|---|---|---|---|
| cups | L2 \* | 6 | +0.0247 | +0.0247 | 3 / 2 | -0.052, +0.125 | 0.0012 | **inconclusive** | 11 blue -0.039, 11 beige +0.108, 12 blue -0.052, 13 blue +0.125, 21 blue +0.007, 22 blue +0.000 |
| cups | L3 = 1 − \*(P_s) | 6 | +0.0418 | +0.0418 | 6 / 0 | +0.000, +0.177 | 0.0012 | **leaks** | 11 blue +0.177, 11 beige +0.006, 12 blue +0.061, 13 blue +0.005, 21 blue +0.000, 22 blue +0.000 |
| cups | L1 loss on P_o \* − lib | 6 | -0.0056 | -0.0056 | 3 / 3 | -0.062, +0.058 | – | **inconclusive** | 11 blue -0.000, 11 beige -0.047, 12 blue +0.058, 13 blue -0.062, 21 blue +0.011, 22 blue +0.007 |
| cups | drift \*(P_o) − \*(refine) | 6 | +0.0001 | +0.0001 | 1 / 0 | +0.000, +0.001 | 0.0012 | **no leak** | 11 blue +0.000, 11 beige +0.000, 12 blue +0.000, 13 blue +0.001, 21 blue +0.000, 22 blue +0.000 |
| rack | L2 \* | 5 | +0.0208 | +0.0208 | 3 / 1 | -0.018, +0.062 | 0.0009 | **leaks** | 12 -0.018, 13 +0.062, 26 +0.002, 27 +0.000, 31 +0.059 |
| rack | L3 = 1 − \*(P_s) | 5 | +0.0524 | +0.0524 | 4 / 0 | +0.000, +0.197 | 0.0009 | **leaks** | 12 +0.062, 13 +0.000, 26 +0.002, 27 +0.000, 31 +0.197 |
| rack | L1 loss on P_o \* − lib | 5 | -0.0069 | -0.0069 | 2 / 2 | -0.049, +0.057 | – | **inconclusive** | 12 -0.044, 13 -0.049, 26 +0.001, 27 +0.000, 31 +0.057 |
| rack | drift \*(P_o) − \*(refine) | 5 | -0.0016 | -0.0016 | 1 / 2 | -0.009, +0.002 | 0.0009 | **no leak** | 12 -0.001, 13 +0.000, 26 +0.002, 27 +0.000, 31 -0.009 |
| pitcher | L2 \* | 2 | +0.2651 | +0.2651 | 2 / 0 | +0.249, +0.281 | 0.0027 | **leaks** | 21 +0.281, 22 +0.249 |
| pitcher | L3 = 1 − \*(P_s) | 2 | +0.0313 | +0.0313 | 2 / 0 | +0.014, +0.049 | 0.0027 | **leaks** | 21 +0.049, 22 +0.014 |
| pitcher | L1 loss on P_o \* − lib | 2 | -0.0127 | -0.0127 | 0 / 2 | -0.013, -0.012 | – | **truth worse** | 21 -0.013, 22 -0.012 |
| pitcher | drift \*(P_o) − \*(refine) | 2 | -0.0027 | -0.0027 | 0 / 1 | -0.005, +0.000 | 0.0027 | **no leak** | 21 +0.000, 22 -0.005 |
| boards | L2 \* | 4 | +0.4975 | +0.0390 | 4 / 0 | +0.013, +0.997 | 0.0000 | **leaks** | 23 board1 +0.916, 23 board2 +0.997, 24 board1 +0.065, 24 board2 +0.013 |
| boards | L3 = 1 − \*(P_s) | 4 | +0.0763 | +0.1505 | 4 / 0 | +0.001, +0.162 | 0.0000 | **leaks** | 23 board1 +0.001, 23 board2 +0.003, 24 board1 +0.162, 24 board2 +0.139 |
| boards | L1 loss on P_o \* − lib | 4 | -0.0004 | -0.0013 | 2 / 1 | -0.003, +0.001 | – | **no leak** | 23 board1 +0.001, 23 board2 +0.000, 24 board1 -0.003, 24 board2 +0.000 |
| boards | drift \*(P_o) − \*(refine) | 4 | +0.0000 | +0.0000 | 0 / 0 | +0.000, +0.000 | 0.0000 | **no leak** | 23 board1 +0.000, 23 board2 +0.000, 24 board1 +0.000, 24 board2 +0.000 |
| spoon proxies | L2 \* | 5 | +0.0279 | +0.0279 | 4 / 1 | -0.004, +0.095 | 0.0000 | **leaks** | 18 sweeper +0.095, 18 pan -0.004, 31 sweeper +0.008, 39 pan +0.017, 40 pan +0.023 |
| spoon proxies | L3 = 1 − \*(P_s) | 5 | +0.0293 | +0.0293 | 5 / 0 | +0.002, +0.070 | 0.0000 | **leaks** | 18 sweeper +0.006, 18 pan +0.070, 31 sweeper +0.066, 39 pan +0.002, 40 pan +0.003 |
| spoon proxies | L1 loss on P_o \* − lib | 5 | +0.0112 | +0.0112 | 5 / 0 | +0.002, +0.020 | – | **leaks** | 18 sweeper +0.002, 18 pan +0.003, 31 sweeper +0.014, 39 pan +0.020, 40 pan +0.017 |
| spoon proxies | drift \*(P_o) − \*(refine) | 5 | -0.0203 | -0.0203 | 1 / 2 | -0.096, +0.001 | 0.0000 | **inconclusive** | 18 sweeper -0.096, 18 pan -0.006, 31 sweeper +0.001, 39 pan +0.000, 40 pan +0.000 |
| pot/lid | L2 \* | 11 | -0.1343 | +0.0290 | 7 / 4 | -0.901, +0.117 | 0.0042 | **inconclusive** | 0 pot -0.837, 0 lid -0.901, 2 pot -0.002, 2 lid +0.028, 26 pot +0.045, 27 pot +0.117, 41 pot +0.010, 42 pot +0.025, 43 pot +0.050, 44 pot +0.001, 45 pot -0.012 |
| pot/lid | L3 = 1 − \*(P_s) | 11 | +0.1773 | +0.0118 | 11 / 0 | +0.001, +0.999 | 0.0042 | **leaks** | 0 pot +0.845, 0 lid +0.999, 2 pot +0.009, 2 lid +0.005, 26 pot +0.031, 27 pot +0.007, 41 pot +0.002, 42 pot +0.011, 43 pot +0.008, 44 pot +0.001, 45 pot +0.033 |
| pot/lid | L1 loss on P_o \* − lib | 11 | -0.0131 | -0.0128 | 3 / 8 | -0.045, +0.002 | – | **truth worse** | 0 pot +0.002, 0 lid -0.031, 2 pot +0.001, 2 lid -0.013, 26 pot -0.024, 27 pot -0.046, 41 pot -0.003, 42 pot -0.026, 43 pot -0.005, 44 pot +0.001, 45 pot -0.001 |
| pot/lid | drift \*(P_o) − \*(refine) | 11 | -0.0027 | -0.0003 | 5 / 3 | -0.027, +0.006 | 0.0042 | **no leak** | 0 pot +0.000, 0 lid -0.027, 2 pot +0.000, 2 lid +0.002, 26 pot +0.006, 27 pot +0.000, 41 pot +0.000, 42 pot -0.010, 43 pot -0.000, 44 pot +0.000, 45 pot +0.000 |

### Leaderboard terms [E] (PLAN §2 map: a = 1.025, H5 S_e, c 0.74–1.0; S_e < 0.8 not converted)

| reading | eval 1 | eval 8 | eval 10 | eval 14 | eval 19 | eval 20 | eval 25 | eval 28 | eval 30 | eval 38 | L_LB twin evals, c 0.74 / 1.0 | spoon evals [E-analogy], c 0.74 / 1.0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S_e (H5 mean) | 0.822 | 0.969 | 0.450 | 0.615 | 0.921 | 0.888 | 0.850 | 0.931 | 0.798 | 1.000 | | |
| twin | 2 | 27+39 | 11 | 12+13 | 18 | 21 | 24 | 27 | 31 | 39 | | |
| L2 template (\*) | dR +0.013 → +0.011 | dR +0.038 → +0.038 | dR +0.034 (–) | dR +0.029 (–) | dR +0.045 → +0.043 | dR +0.144 → +0.131 | dR +0.039 → +0.034 | dR +0.059 → +0.056 | dR +0.033 (–) | dR +0.017 → +0.018 | +0.0122 / +0.0165 | +0.0098 / +0.0133 (proxy dR +0.0279) |
| L2 template (lib, library_v3 submitted) | dR -0.023 → -0.019 | dR +0.008 → +0.008 | dR -0.015 (–) | dR -0.079 (–) | dR +0.049 → +0.046 | dR +0.131 → +0.119 | dR +0.038 → +0.033 | dR -0.018 → -0.017 | dR +0.010 (–) | dR +0.033 → +0.034 | +0.0075 / +0.0102 | +0.0119 / +0.0161 (proxy dR +0.0340) |
| L2 with the template also submitted (\*(P_s) − lib(P_o)) | dR +0.007 → +0.006 | dR +0.037 → +0.036 | dR +0.010 (–) | dR +0.005 (–) | dR +0.048 → +0.045 | dR +0.143 → +0.130 | dR +0.038 → +0.033 | dR +0.036 → +0.034 | dR +0.069 (–) | dR +0.038 → +0.039 | +0.0120 / +0.0162 | +0.0137 / +0.0186 (proxy dR +0.0391) |
| L3 tracker given a true template (1 − \*(P_s)) | dR +0.007 → +0.006 | dR +0.003 → +0.003 | dR +0.092 (–) | dR +0.032 (–) | dR +0.038 → +0.036 | dR +0.025 → +0.022 | dR +0.151 → +0.131 | dR +0.004 → +0.004 | dR +0.132 (–) | dR +0.002 → +0.002 | +0.0075 / +0.0102 | +0.0103 / +0.0139 (proxy dR +0.0293) |
| L1 registration loss on P_o (\* − lib) | dR -0.006 → -0.005 | dR -0.001 → -0.001 | dR -0.024 (–) | dR -0.024 (–) | dR +0.002 → +0.002 | dR -0.001 → -0.001 | dR -0.001 → -0.001 | dR -0.023 → -0.022 | dR +0.035 (–) | dR +0.020 → +0.021 | -0.0003 / -0.0004 | – |
| all tracking loss on P_o (1 − \*(P_o)) | dR +0.019 → +0.016 | dR +0.041 → +0.041 | dR +0.126 (–) | dR +0.061 (–) | dR +0.083 → +0.079 | dR +0.169 → +0.154 | dR +0.190 → +0.165 | dR +0.062 → +0.059 | dR +0.165 (–) | dR +0.020 → +0.020 | +0.0198 / +0.0267 | +0.0201 / +0.0272 (proxy dR +0.0572) |


## Commands (this VM; run from the repo root; code = working tree on 0ec6b5a plus this step's new files)
Paths:
- `S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad`, `PY=$S/map/scoring/venv/bin/python`;
- `KIT=$S/map/scoring/kit/v2d_submission_kit`, `T3=$S/map/scoring/t3`;
- `D=docs/research/work/leak-decomp-20261030`, `R=$S/leak/p1/oracle_roots`, `O=$S/leak/p1/oracle_scores`.

1. Pull, one run at a time, single files:
   - per run, `hf_hub_download('aebatirel/v2d-store', 'runs/<rid>/results/leak_p1/summary.json', repo_type='dataset', local_dir=$S/leak/p1)`;
   - then `python3 -I $D/phase1/scripts/p1_pull.py $S/leak/p1 20261030-orcP1{a,b,c}-87fc869`;
   - 23 / 25 / 22 files.
2. Roots:
   - `$R/{Po,Po2,Ps_scan}/ep<N>/` link the pulled `perc2/`, `perc2rep/` and `perc2scan/` files;
   - P_s to lib frames:
     `SPLIT=public $PY -I pipeline/frame_xform.py N $R/Ps_scan/epN $R/Ps_lib/epN --xform $D/tierA/xstar_geom.json --to lib`
     (20 episodes).
3. Scores, lib / \* / trk / trk_ls (with `OMP_NUM_THREADS=1 SPLIT=public`; log `scores/xstar_trk_p1.log`):
   - `$PY -I tools/xstar_fit.py trk --perc $R/Po --geom $D/tierA/xstar_geom.json --lib meshes/library_v3 --t3 $T3 --kit $KIT --out $O/xstar_trk_Po_oracle.json --jobs 4`;
   - the same with `--perc $R/Ps_lib --out $O/xstar_trk_Ps_oracle.json`;
   - and with `--perc $R/Po2 --out $O/xstar_trk_Po2_oracle.json --episodes 2,11,12,13,18,21,24,27,31,39`;
   - all three copied to `$D/phase1/scores/xstar_trk_{Po,Ps,Po2}.json`.
4. Checks: `SPLIT=public $PY -I $D/phase1/p1_check.py --roots $R --refine $S/refine/in --t3 $T3 --kit $KIT --summaries <the 3 summary.json> --out $O/p1_check_oracle.json`,
   copied to `$D/phase1/scores/p1_check.json`.
5. Readings and tables: `$PY -I $D/phase1/p1_tables.py --json $D/phase1/p1_results.json`. Its output is the Tables
   section above, verbatim.
