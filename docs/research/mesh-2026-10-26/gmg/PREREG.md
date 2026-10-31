# gmg pre-registration v1, revision 1 (frozen)

**Frozen:** 2026-10-30, at the git commit that adds this revision. That commit is the freeze time; this text was
written between 13:35 and 14:20 UTC. It comes before any gmg code exists and before any new scan scoring. The
orchestrator records that commit and this file's sha256 in `docs/work-log.md` and `STATUS.md`.
The workflow brief asked for the freeze time to be marked 2026-10-30T09:40Z. That is when the design workflow
started; neither this file nor SPEC.md existed then (v1 was written at 13:34 UTC and never committed). Writing
09:40Z would misstate the record, so the real time is given instead.
**Specification frozen with it:** `SPEC.md` in this folder, sha256 `181ecc39b4ce076512d1242d966f1e61dfa2a6fa35fc2aee8d06891558a119fe`.
**New scan scorings used to write this file:** zero (v1 and revision 1).

**What the author had already seen** (so it is development knowledge, not evidence for this rule):
- the existing CD-O, ADD and flips of the 104 gen-probe meshes, the hand kits (pot, lid, rack, boards, clean lid and
  rack), the lathe fits and library_v3/v3x/v5;
- the hybrid design's post-hoc analyses: argmin o2m regret 0.054 cm; the FSV veto at τ 0.1, 0.2 and 0.3 with scan
  regret 0.137, 0.063 and 0.063 cm (`hybrid-selector/looo_L0_veto.log`);
- the X0-mini pools; the GT-free self-ambiguity values of library and board meshes; the GT-free FSV of generator
  outputs (0.02-0.20; SAM 3D pot-with-lid 0.50-0.52);
- the window values of the four JSON programs; the scan rack wall median 2.5 mm and scan lid 1.8 mm (leaked through a
  brief on 27 Oct); the ep23 board-2 track problem (found through scan ADD 78.7 mm);
- **eval-track analyses** made during design: `neural-recon/contact_states.txt` (eval 1, 10, 14, 30),
  `neural-recon/relmotion.jsonl` (eval 1, 8, 10, 14, 19, 25, 28, 30), `gen-first/eval_contact_proxy.txt` (all 20 eval
  episodes); also the Grounding DINO boxes of the ep2 frame-0 det dump;
- the design review of v1 (its [M] numbers; it contained no new scan number).

No constant below was fitted to scan numbers. Constants chosen after seeing results are labelled informed in A.6.
Section B.1 says which tests are therefore weak.

Labels: [D] measured against the scan, [M] measured without the scan, [E] estimate, [H] hypothesis, [R] read from
code or documents, [U] unverified; "dev" = computed from `obs_all` (library_v3 ROI and `--others`).

**Change control.** Sections A, C and D are frozen. Until the first scoring of round R1 starts, an amendment is
allowed only as a dated entry in section F. It must give its reason and state that its author saw no new scan
number. After R1 starts, nothing in A, C or D changes. A redesign then needs a new pre-registration file and a new
counted round. Revision 1 is a whole-file amendment made under this rule before any code or scoring (section F).

**Inconclusive zone.** Where a claim's bound and its falsifier leave a gap (P4, P11, P12 and others), a result in the
gap is reported as "inconclusive": the claim is not supported and not falsified. It changes no decision unless a rule
below says so.

---

## A. The frozen selection rule S1

### A.1 Candidates and thickness
Per object and episode, the pool holds every candidate built by the producers in SPEC §8, each with markers attached
when detected (SPEC §10). Classes: STRUCT (P-SYM, P-PROG), FUSE, GEN, SHELL, HULL. Walls with both faces observed keep
their measured thickness.

**Unseen-thickness default t0 (fitted:own).** For each public object-episode, take the finite two-sided thicknesses
that `autokit/shell.shell_sheet` measures on the owned points and their median. Per object, take the median over its
episodes. t0 = the median over objects, clamped to [1.5 mm, 8 mm] (sensor floor of about 2 sigma; two voxels). It is
computed from the clean public bundles at build step B13, before that batch builds any candidate, and written to
`gmg/frozen_constants.json`, which is committed before R1. The eval run uses the frozen value.
- **Fittable** if at least 5 objects have at least 200 finite measurements over their episodes.
- **Fallback** if not fittable: t0 = 2.5 mm, labelled "scan-coincident (brief leak)", and R1 item C.3 (c) applies.
- **Alternates:** after the pick, the rule is re-run with 0.6 × t0 and 1.6 × t0 (each at least 1.5 mm), rebuilding
  only the candidates in the pick's tie set. A different pick only raises the flag `t_sensitive`.
- Dev runs use t0_dev, the same statistic on `obs_all`; it is never used in a clean run.

### A.2 Shared quantities
- **sigma** (per object and episode): build a route-A sheet (`autokit/shell.shell_sheet`) from even frames; sigma is
  the median distance of odd-frame owned points to it, clamped to [0.5, 3.0] mm.
- **Grids** (4 mm voxels; which samples feed them: SPEC §6). `hits` from owned samples only; `free` carved along every
  valid ray up to 10 mm before its sample; `shared`; `pocc`. OBSERVED if hits ≥ 3 and hits/(hits+free) ≥ 0.5; FREE if
  free ≥ 3 and hits/(hits+free) < 0.2; otherwise UNKNOWN.
- **Partner samples P_p:** one sample per p-OBSERVED voxel (centroid of p's owned points in it), with a normal
  oriented towards the cameras that saw it; in p's frame. In contact frame f they are moved into o's frame by
  T_{o←p}[f] = inv(cam_T_o[f]) · cam_T_p[f].
- **Jitter j (fitted:own, per pair and episode):** over consecutive contact frames f, f′ (adjacent in the stride-2
  sequence), d(f, f′) = mean over P_p of |T_{o←p}[f′]x − T_{o←p}[f]x|; j = median d / √2. j = 0 if there are fewer
  than 5 such pairs.
- **Band b** = min(8 mm, 3 · sqrt(sigma_o² + sigma_p² + j²)).
- **Blocks:** the object's good frames (track sanity), in time order, split into K contiguous blocks of equal frame
  count.
- **Held-out set H_k:** owned points (`own` = 0) of the frames in block k. If the pool contains any GEN or FUSE
  candidate, frames whose view direction (object frame) lies within 8 degrees of any generator input view are removed
  for all candidates (so the comparison stays paired). If that removes more than 80 % of the object's held-out frames,
  nothing is removed and the pool is flagged `gen_view_overlap` (A.5). Subsample: at most one point per 4 mm voxel per
  frame, then at most 20,000 points at random (seed 0).
- **Fold candidate c_k:** the candidate rebuilt by its producer on the frames outside block k. GEN candidates keep
  their shape and are re-placed (SPEC §15) on the frames outside block k. FUSE candidates use the re-placed GEN mesh
  and the shell rebuilt outside block k. Markers are detected once on all frames and attached to every fold
  candidate alike.

### A.3 Vetoes (applied to the all-frames candidate)
- **V1 watertight:** the gmg's copy of the kit decode of the shipped mesh (kit `budget_mesh` at 4096) is not
  watertight (`trimesh.is_watertight`).
- **V2 contact:** for each other tracked object p with contact frames (A.6), in each contact frame f a partner sample
  x ∈ T_{o←p}[f] P_p violates if (a) it lies inside the candidate's closed volume (generalised winding number ≥ 0.5)
  deeper than b below its surface, or (b) it lies within b of the candidate's surface, the cosine between its normal and
  the candidate's surface normal at the nearest point is above 0.5, and it is farther than b from every owned point of
  o. Veto if the median over contact frames of the number of violating samples exceeds max(3, 1 % of |P_p|).
- **V3 hallucination:** `fsv_far(c) − fsv_far(s) > tau`, where s is the route-A shell at t0 of the same episode.
  `fsv_far(m)` = the share of 20,000 area-weighted surface samples of m (seed 0) that lie in FREE voxels with no
  OBSERVED voxel within 2 voxels (Chebyshev).
  **tau (fitted:own):** the 99th percentile of D(c, k) = fsv_far(c_k) − fsv_far(s_k) over every CPU candidate c
  (STRUCT, SHELL, HULL) of every public object-episode in the clean CPU batch (B13) and every fold k (K = 3), with
  fsv_far measured against the all-frames grid. No floor, no cap. Frozen in `frozen_constants.json` before R1 and
  not refitted after G2. Rationale [H]: CPU completions are built to stay out of FREE space, so this is how much free
  space honest completion hits when a block is withheld; a generated neighbour lies far outside it.
- **V4 below table:** only for objects at rest on the table in at least 10 % of good frames (rest = speed below 2
  mm per frame and the lowest owned points within 5 mm of the table plane). Veto if more than 1 % of 20,000 volume
  samples lie more than max(3 sigma, 2 mm) below the at-rest table plane.
- **V5 flip-risk:** `amb_mm − amb_floor_mm < amb_floor_mm` from the gmg's copy of `mesh_metric.ambiguity` (GT-free),
  computed with **trusted** balls only (balls of objects that passed B.4 repeatability; otherwise ball-free), and the
  kit does not declare the object symmetric (kit symmetric: beige_cup, blue_cup, white_pot_lid). Applied only if at
  least one feasible candidate is not flip-risk.

### A.4 Evidence score E
For each held-out point i (camera centre `cam_i`, point `p_i`, object frame): cast the ray from `cam_i` through `p_i`
against `c_k`. `d_obs = |p_i − cam_i|`; `d_hit` = range of the first intersection (infinite if none);
`Δ = d_hit − d_obs`.
- `cost_i = huber(Δ, sigma)` if `|Δ| ≤ 3 sigma`;
- `cost_i = min(−Δ, 10 sigma)` if `Δ < −3 sigma` (extra surface in front of an observed point);
- `cost_i = min(Δ, 10 sigma)` if `Δ > 3 sigma` (missing surface; infinite gives 10 sigma);
- `huber(x, δ) = x²/(2δ)` if `|x| ≤ δ`, else `|x| − δ/2`.

`R_k = mean_i(cost_i) / sigma`. `E = mean_k(R_k) + 10 × fsv_far(c)`. Lower is better.
Standard error: 200 moving-block bootstrap replicates (seed 0). Inside each held-out block of n_k frames, contiguous
runs of L = max(1, round(n_k^(1/3))) frames are resampled with replacement. Every candidate is scored on the same
replicates. `SE_diff(c)` = standard deviation over replicates of `E(c) − E(best)`.

### A.5 Pick
1. Remove vetoed candidates (V1-V5).
2. `best` = the lowest E. Tie set T = feasible candidates with `E(c) − E(best) ≤ b_tie × SE_diff(c)`.
3. Order T lexicographically by:
   1. class: STRUCT, then FUSE, then GEN, then SHELL, then HULL; in a pool flagged `gen_view_overlap`: STRUCT, SHELL,
      FUSE, GEN, HULL (generated E is optimistic there);
   2. flip safety: larger `floor((amb_mm − amb_floor_mm) / amb_floor_mm)` first, trusted balls only (skipped for
      kit-symmetric objects);
   3. trusted markers attached first;
   4. fewer free parameters first (only if the parameter prior is on);
   5. lower E.
4. The first candidate in T is the pick. Its all-frames build is shipped.
5. If nothing is feasible: the fallback ladder, SPEC §13 (ABSTAIN_HULL, PRIOR_GEN, PRIOR_PUBLIC; never library_v1-v4).

### A.6 Constants (name, value, origin)

Origins: `sensor`, `generic` (domain knowledge or statistics, chosen without a result in view), `fitted:own` (from our
own observations), `informed` (chosen after seeing results; the result is named).

| Constant | Value | Origin |
|---|---|---|
| vote voxel | 4 mm | generic (existing grid) |
| keep / OBSERVED | hits ≥ 3, ratio ≥ 0.5 | generic (existing `obs_points.py` default) |
| FREE | free ≥ 3, ratio < 0.2 | generic |
| free carving | all rays, up to 10 mm before the sample | generic (existing `obs_points.py` default) |
| crop | ±0.30 m cube; seeded component at 8 mm; guard 1.5 × seed box, else seed box + max(2 cm, 25 %) | generic |
| ownership tie | 2 binomial SE | generic statistics |
| co-moving | flag if > 50 % of samples tied; nearest seed wins if its distance < 0.5 × the other; `census_unstable` if > 10 % of separated frames change | generic |
| sigma | even/odd split floor, clamp [0.5, 3] mm | fitted:own per object-episode; clamp sensor |
| t0 | median of per-object medians of measured two-sided thickness, clamp [1.5, 8] mm; fallback 2.5 mm | fitted:own (public); fallback scan-coincident (brief leak) |
| thickness alternates | 0.6 × t0, 1.6 × t0 | generic (geometric bracket) |
| thickness floor and wall clip | 1.5 mm; 8 mm | sensor (about 2 sigma); two voxels |
| ray band, clip, Huber δ | 3 sigma, 10 sigma, sigma | generic, relative to measured noise |
| fsv_far band, weight | 2 voxels, 10 | generic (all surface in free space costs as much as all points missing) |
| K, bootstrap, seed, tie band b_tie | 3, 200, 0, 1 SE | generic statistics (one-standard-error rule) |
| bootstrap block length | round(n_k^(1/3)) frames | generic statistics (standard block-bootstrap rate) [R] |
| generator view hold-out | views within 8° of a generator input view; skipped if > 80 % removed | generic (8° = the view-spacing constant) |
| contact frame | 3-D gap ≤ 10 mm or masks dilated by 10 px overlap | generic: > 10 sigma of depth noise and 2.5 voxels; 10 px ≈ 10 mm at 0.5-0.6 m |
| separated frame | 3-D gap > 20 mm and 2-D gap > 16 px to every partner | generic: twice the contact thresholds |
| 3-D-separated frame | 3-D gap > 20 mm | generic |
| V2 | band b (A.2); normal cosine > 0.5; count > max(3, 1 % of the partner's samples) | generic, with fitted:own sigma and j; cap 8 mm = two voxels |
| V3 | tau = q99 of the CPU fold-rebuild null | fitted:own (public) |
| V4 | 1 % below max(3 sigma, 2 mm); rest: < 2 mm/frame, within 5 mm, ≥ 10 % of frames | generic |
| V5 | amb − floor < floor; trusted balls only | generic; informed (seen on library and board meshes) |
| class order | STRUCT > FUSE > GEN > SHELL > HULL | informed ([D] hand kits against generators) |
| generator views | hands ≤ 25 % of mask; visible ≥ 0.6 × episode max; valid depth ≥ 0.6; ≥ 1 frame; ≤ 6 views; ≥ 8° apart; if the span is < 8°: one view × 4 seeds (G1) or × 2 seeds (G2); Pixal3D-MV only with ≥ 3 views | generic |
| ball radius window | 1.5-12.5 mm | generic: commercial passive markers about 3-25 mm diameter [U] |
| ball detector | 15,000 seeds; ≥ 3 frames; residual ≤ 1.5 sigma; cap ≥ 90°; both halves; second pass ± 10 % of consensus | generic; seed count informed (changed once after a first run) |
| trusted balls | B.4 repeatability ≥ 60 % for the object | generic |
| symmetry acceptance | rotational consistency ≤ 3 sigma; mirror residual ≤ 3 sigma, observed share ≥ 0.7, free share < 5 % | generic |
| grammar | ≤ 1 body + 2 appendages; appendage points > 3 sigma outside the body; MDL cost sigma² per parameter; extent windows by A.6b, tried ×1 and ×2 | generic; part vocabulary and A.6b table informed |
| slab two-face thickness | 3-25 mm | informed (parts.py default carried from the prim_boards hand kit) |
| placement | per-axis scale [0.8, 1.25] | generic (organiser SRT / AGILE practice) |
| remesh, budget | 1.5 mm pitch; 4000 faces (kit 4096) | sensor; kit |
| track sanity | bad frame: > 5 % of owned points below max(3 sigma, 3 mm) under the table, or block residual > 3 × median; TRACK_FAIL: < 30 % or < 20 good frames | informed (built after tracks were found bad through scan ADD) |
| identity tests | split halves; cross-object: nearest shell must be o's own (symmetric chamfer after rigid best-of-24 PCA-start ICP, no scale normalisation) | informed (written after the ep23 swap was found through scan ADD 78.7 mm) |
| low coverage, ABSTAIN_HULL minimum | < 20 good frames or < 20,000 owned points = low; ABSTAIN_HULL needs the opposite | generic |
| B.2 reference minimum | ≥ 10 3-D-separated frames | generic |
| Phase-2 masks | chosen boxes of two objects may not have IoU > 0.5; start frame: IoU ≤ 0.1 with every other chosen box, hands ≤ 25 %; 5 negative points per partner | generic |
| K-a / K-b FSV difference (G0, G1) | ≤ 0.05 | informed by GT-free FSV values (no scan link) |
| rest check | ≤ 10° | generic |

### A.6b P-PROG extent table (frozen now; v1 left it to `prog.py`)
s = `parts.robust_scale` of the owned points. Each required shape window (`Wr`) of the part types in the gmg
vocabulary gets one class by its meaning. Every program is run with this table and with all extents doubled.

| Class | Value | Meaning | Windows |
|---|---|---|---|
| E1 | 0.05 s | a band at an edge or rim; the inner radius of a near-axis region | `lathe.rim_w`, `sheet_of_revolution.resid_edge`, `sheet_of_revolution.dome_r0` |
| E2 | 0.2 s | a local reach from a feature | `lathe.body_w`, `sheet_of_revolution.dome_r1`, `plate.inner_search` (bar), `plate.hole_tip` (bar) |
| E3 | 0.6 s | an inner radius at body scale | `sheet_of_revolution.flange_r0`, `sheet_of_revolution.tilt_rmin` |
| E4 | 1.2 s | an outer reach at body scale | `sheet_of_revolution.flange_r1` |
| clip | 8 mm | largest wall thickness accepted | `lathe.t_max`, `plate.T_max` (bar) |

The author had seen the four JSON programs' window values; this table was assigned by meaning and was not matched
to them (several differ). Parts outside the vocabulary (strap, peg rows, rounded tubes, lip) have no entry.

### A.7 Variant menu and deployment
- Menu (8): K ∈ {3, 5} × b_tie ∈ {1, 2} × parameter prior ∈ {on, off}. Default V0 = (3, 1, on).
- **Cross-episode proxy X** (development only). For object o, build episode A and every other episode B of o that
  passes track sanity and the identity tests. Register each candidate c of A onto B's owned points (M11 `register`:
  24 PCA starts, rigid ICP, both members of every flip pair, no identity start, so the shared track frame is not
  used). Then `X(c) = mean_B [R(c on all of B's owned points) × sigma_B + 10 sigma_B × fsv_far(c against B's grid)]`,
  in mm. X-regret(A, v) = X(pick_v(A)) − min over A's pool of X.
- **X is used to choose the variant only if B.13 passed.** Otherwise V0 is deployed and the LOOO is reported only.
- **Fold** for each object o with X: v* = argmin over the menu of the mean X-regret on the other X objects (ties: V0,
  then K = 3, then b_tie = 1, then prior on). Record o's X-regret under v* and whether v* picked o's X-best.
- **Deployment:** if one variant wins at least ceil(0.7 × number of folds) folds, it is deployed for every object.
  Otherwise V0. It is written to `gmg/deploy_variant.json` and committed before R1. The LOOO is re-run on the enlarged
  pools after G2 and committed again before R2, by the same rule.

---

## B. GT-free experiments (zero scan scorings)

### B.1 X0 replay on existing scores: the cheapest kill test of the selection half
- **When:** build step B6. $0, CPU 1-2 h.
- **Data:** `obs_all` in `GMG_MODE=dev` (library_v3 ROI and `--others`; flagged). Existing labels only: cdo_eval
  from `results/gen-probe/scores.jsonl`, `results/prim/potlid/metric_all.jsonl`, `prim/rack/scores.jsonl`,
  `prim/boards/scores.jsonl`, `prim/clean/lid_scores.jsonl`, `results/lathe_obs.jsonl`.
- **Pools:** one pool per (object, episode) taken from the labels. Excluded as library-derived: `potlid/tsdf/*`,
  `clean/lid/*_tsdf`, `lathe_hyb*`, `library_*` rows. Excluded as multi-episode: `rack/epall_joint*`,
  `clean/rack/*/all_joint`, `lathe_obs_g/a1/ep21+22/*`. Hand kits with the 7 mm ball prior stay in the primary
  analysis and are removed in a secondary one. Note that `potlid/*/ep2` labels exist for both the pot and the lid; the
  object field decides.
- **Primary pool per object:** its (object, episode) pool with the most labelled candidates. Others are secondary.
- **Unlabelled shell:** the route-A shell at t0_dev is built for each pool (needed by V3) and added as an unlabelled
  SHELL candidate. If S1 picks it, the count of shell picks is reported, and the pick among labelled candidates (S1
  with the shell removed) is used for the metrics.
- **tau for X0:** tau_X0 = the A.3 statistic over the SHELL and HULL fold rebuilds of the X0 pools' episodes (dev).
  It is a dev constant, reported, and never used in a clean run.
- **Rule form:** S1 with V0, all-frames form: candidates are not rebuilt per block (they are fixed meshes); blocks
  only define the bootstrap; the generator view hold-out is not applied. V1 is skipped (the labels are for raw
  generator meshes; remeshing would change them). Candidates are used as stored (sim3_fit placement for SAM 3D,
  Hunyuan3D, TRELLIS.2, TripoSG; Pixal3D frame; kits in our frame).
- **Measures:** per object pick CD-O, pool median, pool 25th percentile, pool best, regret; eval-pair-weighted mean pick
  (library_v3 0.491 on the same weighting [D]); comparison with the old GT-free metric (regret 0.120 cm, 6/10 below
  median) and R3 (0.123 cm, 8/10).
- **Pass (both):** (a) mean regret over the 10 primary pools < 0.10 cm; (b) pick at or below the pool median on ≥ 7 of
  10 objects.
- **Reported, not a pass condition:** whether V2 and V3 veto the two SAM 3D pot-with-lid meshes in the ep2 lid pool.
  Their FSV of 0.50-0.52 was known before this rule was written, so that check could not fail (removed in revision 1).
  X0's V2 and contact numbers are dev numbers; they overstate separation and are not evidence for the pot-and-lid rule.
- **Kill:** (a) or (b) fails. S1 is then declared dead. A successor may be pre-registered in section F before R1,
  marked as designed after X0; only R1 can then support it. **The successor comes from a menu fixed now** (lit
  `gmg-2026-10-30.md` §4.4): L-R1 visibility-aware two-sided residual; L-R2 held-out temporal blocks with silhouette
  IoU and z-buffered depth; L-R3 cross-candidate consensus medoid; L-R4 asymmetric costs (Thrun-Wegbreit). Each enters
  as a replacement for E inside S1. The choice among them uses no scan label: if B.13 passed, the menu item with the
  lowest mean X-regret over the X objects; otherwise L-R2. Their X0 numbers are reported after the choice, never used
  for it.
- **Weakness, stated in advance.** E's ray term behaves like observed-point fidelity, and argmin o2m is already known to
  do well on these pools (0.054 cm, post hoc). Passing X0 is weak evidence. Failing it is strong evidence.

### B.2 Ownership separates touching objects (prediction P2)
- **Pairs:** pot/lid ep2; cups ep11; boards ep24; pot/rack ep26, ep27; cup/rack ep12, ep13; sweeper/rack ep31;
  sweeper/dust pan ep18 (added in revision 1); boards ep23 only if both boards pass the identity tests.
- **B.2a leakage, at build step B4** (after the clean extraction of all 20 public episodes; needs `HF_TOKEN`). For
  target o and partner p, build o's route-A sheet from o's **3-D-separated** frames only (gap > 20 mm; the 2-D test is
  dropped, because ep12, ep13, ep26 and ep31 have no frame where the masks are apart in 2-D [M, dev]). A direction is
  **testable** if o has at least 10 such frames. Expected [M, dev, upper bounds from frames with gap > 10 mm]: ep12
  blue cup up to 57, ep13 up to 48, ep31 sweeper up to 26, ep26 rack up to 9 (so probably not testable). Leakage = the
  share of o's owned samples from contact frames that lie more than 3 sigma from that sheet and within 4 mm of p's
  owned samples in the same frame.
- **B.2b, at build step B13:** V2 = 0 for the final ep2 pot pick against lid samples and for the ep2 lid pick against
  pot samples.
- **Pass:** leakage ≤ 1 % on every testable direction, and B.2b holds.
- **Fail:** leakage > 1 % on 2 or more testable pairs (a pair fails if either direction fails), or B.2b fails.
- **Inconclusive:** fewer than 4 pairs have a testable direction. Untestable directions are listed.

### B.3 ROI swap (P3)
- Compare the clean extraction with `obs_all` (dev read) at the voxel level, inside the old library_v3 box, on the 25
  files that had hands (the 8 hands-null files are reported apart; MediaPipe now removes their hands). The old box is
  taken from the `lo` and `hi` keys of each `obs_all` file; the deny-listed mesh is not opened.
- **Pass:** Jaccard of OBSERVED voxels ≥ 0.95 on at least 23 of 25 files, and new OBSERVED voxels outside the old box
  ≤ 5 % of the total on at least 23 of 25.
- **Fail:** otherwise. Then the crop rule is not a drop-in replacement, and the difference is reported per file.

### B.4 Markers without a radius prior (P4)
- **Unimodal radius:** in each episode, at least 80 % of accepted radii lie within ±15 % of the episode median.
- **Repeatability:** for objects with two or more public episodes (pot, rack, blue cup, dust pan, pitcher, sweeper,
  board 2), at least 60 % of an episode's accepted balls have a ball within 5 mm in another episode of the same object
  (after the A.7 registration). An object whose balls pass is "trusted" for V5 and the tie-break (A.3, A.5).
- **Fail:** repeatability below 40 %, or a bimodal radius in 2 or more episodes. Then balls are turned off by default
  (a flag), and V5 alone guards flips.
- **Inconclusive (40-60 %):** balls stay attached, but the object is not trusted.

### B.5 Completion explains unseen observations (P5)
- For each X object, the S1 pick of every build episode A, registered onto each other episode B (A.7): the median ray
  error |Δ| (mm, not clipped) on B's points that A never saw (unseen-in-A).
- **Pass:** pot and blue cup ≤ 2.0 mm; dust pan and sweeper ≤ 3.5 mm; pitcher ≤ 5.0 mm. The rack is reported only
  (its episodes share one view cone).
- **Fail:** any of those objects misses its bound by more than 1 mm.

### B.6 LOOO (P6)
- Runs as a selector only if B.13 passed; otherwise it is reported and V0 is deployed.
- **Pass:** one variant wins at least ceil(0.7 × folds) folds, and the held-out X-regret is ≤ 0.3 mm on at least
  ceil(0.7 × folds) objects.
- **Fail:** either part fails. V0 is then deployed (A.7), and the failure is reported.

### B.7 Simulator readiness (P7)
- **Pass:** every one of the 33 public picks is watertight after the kit decode; the rest-pose error is ≤ 10° for at
  least 9 of 10 objects (an object counts if most of its picks pass).
- **Fail:** any pick not watertight, or 2 or more objects failing the rest check.

### B.8 Generator placement on synthetic perturbations (P10; before G2)
- Stand-in truth: our own all-frames STRUCT pick (else the SHELL) for pot ep41, dust pan ep39, blue cup ep22, lid ep2,
  sweeper ep31. Ten Sim(3) perturbations each (rotation 10°, translation 10 mm, scale ±10 %, seed 0). `place.fit`
  must bring the mesh back using the real observations.
- **Pass:** median recovery error (mean vertex displacement) ≤ 3 mm and no rotation error above 30° on at least 4 of 5
  objects.
- **Fail:** median > 5 mm, or any flip on a non-symmetric object. G2 is then not run; GEN and FUSE enter only with
  Pixal3D-MV's own frame (identity start, no re-placement), flagged.

### B.9 G1 kill test (GPU; zero scan scorings)
- **Runs.** SAM 3D with our depth on the views M9 chooses. If an object's qualifying views span less than 8°, it gets
  one view × 4 seeds; otherwise up to 4 views × 2 seeds. Objects: lid ep2 (separated, hand-free frames; expected one
  view, spread 2.0° [M, dev]), pot ep2 (lid-off frames; expected one view, 4.5°, 12 frames), pot ep41, sweeper ep18,
  blue cup ep22, dust pan ep40 (added in revision 1 so that K-c and K-d can be tested). Pixal3D-MV × 2 seeds only where
  M9 gives at least 3 views; never on contact frames.
- **Testable objects for K-c and K-d:** those whose chosen views span at least 15°. Expected [M, dev spreads]: pot ep41,
  sweeper ep18, dust pan ep40; the lid, the ep2 pot and the blue cup ep22 (8.4°) probably not. With one view the test
  would pass trivially, so untestable objects are reported "not testable" and not counted.
- **Thresholds fixed now:**
  - **K-a lid is a lid:** at least half of the lid's SAM 3D runs have `fsv_far(c) − fsv_far(shell) ≤ 0.05` and pass V2
    against pot samples. (The contact-frame outputs had FSV 0.50-0.52 [M, hybrid definition].)
  - **K-b pot without lid:** at least half of the ep2 pot runs pass V2 against lid samples and have
    `fsv_far(c) − fsv_far(shell) ≤ 0.05`.
  - **K-c layout:** SAM 3D layout mapped by `inv(cam_T_obj)`: median distance between the centroid of the placed mesh's
    surface visible from that view and the centroid of that view's owned points ≤ 10 mm, and inter-view rotation spread
    ≤ 15° (axis only for kit-symmetric objects). Pass on at least n − 1 of the n testable objects, n ≥ 3.
  - **K-d agreement:** after `place.fit`, the median pairwise symmetric chamfer between per-view meshes ≤ 8 mm; pass on
    at least n − 1 of the n testable objects, n ≥ 3.
  - **K-e sweeper shape:** generated width/length within 25 % of the width/length of our owned points projected on the
    table plane, on at least half of the face-on runs.
- **Kill rules:** K-c and K-d both fail → generator placement is dead; G2 is not run; GEN and FUSE are dropped. If
  fewer than 3 objects are testable, K-c and K-d are "not testable", their kill rule cannot fire, and G2 additionally
  requires B.8 to pass and is flagged. K-a fails → contact-aware input alone does not separate objects for SAM 3D;
  GEN and FUSE are kept only for objects with no contact partner in the episode. K-e fails → GEN is off for the
  sweeper.
- Pixal3D-MV is reported against K-a and K-d separately.

### B.10 Remesh
- The 104 gen-probe meshes after `remesh.watertight` + `fit_budget(4000)` + kit decode: at least 100 of 104
  watertight. Fail: fewer. GT-free; runs at B3.

### B.11 Generator views and masks on the CPU (P20; build step B2, $0)
- **Data:** dev bundles (`obs_all` + tracks) for ep2 (pot, lid), ep11 (blue cup, beige cup), ep26 (pot, rack); local
  videos `ep2_a.mp4`, `ep11_a.mp4`, `ep26_a.mp4`.
- **Method:** M9 chooses views per target. Target mask = projected owned points (closed, filled) minus partner pixels
  (projected partner owned points, dilated by 10 px) minus hand pixels. SAM2 refinement is added if it runs on the
  local CPU; otherwise the same test runs on the G0 box on the SAM2 masks before any SAM 3D run.
- **Pass:** no partner pixel inside any chosen target mask, after closing and after refinement; every view chosen in
  separated mode is a separated frame. ep26 is expected to run in contact mode (no 2-D separated frame [M, dev]).
- **Report:** number of views and their spread per target; a montage of the chosen views with masks.
- **Fail:** any partner pixel inside a target mask, or a non-separated frame chosen in separated mode. It is a code
  test: the fix and its reason are logged and the test re-run. On the G0 box a failure stops G0 before SAM 3D runs.

### B.12 G0: the owner's hypothesis, early (P18; build step B3; GPU about $1-2 [E])
- **When:** after B2 and owner decision D1 (`HF_TOKEN`, `VAST_API_KEY`).
- **Bundle:** ep2, clean if B4 has run, else dev (flagged; dev V2 numbers may overstate separation).
- **Runs:** SAM 3D with our depth, the lid on M9's best separated, hand-free view and the pot on M9's best lid-off
  (separated) view, seeds 0 and 1: 4 runs. Placement by SAM 3D's layout mapped by `inv(cam_T_obj[k])` only; remesh M10.
- **Measures:** K-a for the lid and K-b for the pot (B.9 definitions). Also reported: the placed mesh's extents along
  the owned points' PCA axes against the owned points' own extents; the share of placed surface outside the bundle grid
  (a dev grid covers only the old box, so fsv_far under-counts there); a montage.
- **Outcome:** SUPPORTED if at least 1 of 2 lid runs passes K-a and at least 1 of 2 pot runs passes K-b; NOT SUPPORTED
  if no lid run passes K-a; otherwise MIXED. G0 is a probe. It kills nothing; G1 is the kill test.

### B.13 X-check against existing labels (P19; build step B6, $0, zero new scorings)
- **Pools:** the X0 primary pools of white_pot and blue_cup (B.1), labelled candidates only.
- **X(c):** A.7, with registration, over the object's other public episodes that pass dev track sanity and the
  identity tests.
- **Statistic:** Spearman ρ between X(c) and the existing cdo_eval within each pool.
- **Pass:** ρ > 0.46 (the old GT-free metric's Spearman) on both pools. X may then choose the variant (A.7, B.6) and
  the B.1 successor.
- **Fail:** ρ ≤ 0.46 on either pool. X is then used for reporting only; V0 is deployed.
- **Weakness:** the author has seen these pools' scores. ρ is computed once, with the registration and X frozen above.

### B.14 V2 synthetic tests (P21; build step B1, dev, test fixtures)
- **T-V2a** ep11: the blue cup's route-A shell united with the beige cup's route-A shell placed at the beige cup's
  median contact-frame relative pose (a fused double cup) → must be vetoed.
- **T-V2b** ep11: the convex hull of the blue cup's owned points (cavity filled) → must be vetoed.
- **T-V2c** ep2: the lid's route-A shell united with the pot's route-A shell placed at the pot's median contact-frame
  relative pose (a lid with a phantom pot body) → must be vetoed.
- **T-V2d** ep2: the hand-kit lid `potlid/fit/ep2` (cdo_eval 0.2186 [D]; label sha prefix `e1be3218a8608793`; role
  fixture) → must not be vetoed against pot samples.
- **Pass:** all four as stated. **Fail:** any other outcome; V2 is fixed before B5 and the fix and reason are logged.
  These are dev data (library_v3 `--others` removed), so the tests check the logic, not ownership.

### B.15 Identity tests (P22; build step B4)
- The split and cross-object tests of SPEC §7 run on every public object-episode. Predictions [H, informed]: the
  cross-object test flags ep23 board 2 (IDENTITY_SWAP); it flags no other public object-episode; the lid and the beige
  cup are not testable. A flagged episode routes like TRACK_FAIL and moves the anchor (C.2).

---

## C. Scan rounds (counted)

### C.1 Rules for every round
- Scorer: `scripts/mesh_metric.py` at the frozen commit, default mode (kit budget, eval-pair seeds plus its default
  extra seeds). For `mini_sweeper`, `wooden_piece_1` and `wooden_piece_2`, add `--seeds 1001,1002,...,1030` (30 seeds)
  for the flip count.
- One scoring = one distinct mesh (sha256), scored once. Duplicates are scored once.
- Before a round: the candidate and pick SHA256SUMS, `deploy_variant.json`, `frozen_constants.json`, the scoring
  manifest (`validate/round.py`) and the code commit are pushed to git, and the work log states the plan.
- All items of a round are scored in one batch and read together. No partial looks, no re-scoring, no added items.
- Only clean-mode outputs (bundles from `extract_joint.py`) may be scored. Dev-mode outputs never are.

### C.2 Anchor episodes (fixed now; GT-free rule: largest view_cap60 in `obs_census.jsonl`, ties by points). If an
anchor fails track sanity or the identity tests, the next one in its list is used.

| Object | Order |
|---|---|
| white_pot | ep27, ep43, ep26, ep45, ep41, ep42, ep44, ep0, ep2 |
| white_pot_lid | ep2, ep0 |
| plastic_dish_rack | ep31, ep26, ep12, ep13, ep27 |
| blue_cup | ep12, ep13, ep11, ep22, ep21 |
| beige_cup | ep11 |
| water_pitcher | ep21, ep22 |
| mini_dust_pan | ep40, ep39, ep18 |
| mini_sweeper | ep18, ep31 |
| wooden_piece_1 | ep24, ep23 |
| wooden_piece_2 | ep23, ep24 |

The census is a dev file (from `obs_all`); `view_cap60` is a coverage statistic, so the library ROI has low impact on
this order.

### C.3 Round R1: the CPU core
- **When:** after the clean public CPU run of all 33 public object-episode pairs (build step B13), after B.2-B.7 are
  reported, and after `deploy_variant.json` and `frozen_constants.json` are committed. Needs `HF_TOKEN`.
- **Items:**
  - (a) the mesh shipped for each of the 33 pairs, fallback outputs included (at most 33);
  - (b) on each object's anchor episode, the best-E feasible candidate of each class in {STRUCT, SHELL, HULL} other
    than the pick's class (at most 2 per object, at most 20);
  - (c) only under the thickness fallback (A.1): on each anchor whose pick raises `t_sensitive`, the pick rebuilt at
    1.5 mm and at 4.0 mm (at most 20).
- **Cap: 53 scorings (73 under the thickness fallback).**

### C.4 Round R2: with generators (only if G2 ran)
- **When:** after G2, the public re-run with GEN and FUSE added, and the re-frozen `deploy_variant.json` (A.7).
- **Items:** (a) every shipped mesh whose sha256 differs from its R1 counterpart (at most 33); (b) on each anchor
  episode, the best-E feasible GEN and the best-E feasible FUSE candidate if not already scored (at most 20).
- **Cap: 53 scorings.**

### C.5 Round R3: poses of the clean re-track (only if G3 ran)
- Registered pose AUC (`pipeline/score_registered.py`) of the Phase-2 final tracks with their gmg meshes, on the 20
  public episodes. At most 20 pose scorings.

### C.6 Count
X0, B.13: 0 new. R1 ≤ 53 (≤ 73 under the thickness fallback). R2 ≤ 53. R3 ≤ 20 pose scorings. **Total ≤ 106 mesh
scorings (≤ 126 under the fallback).** Any other scoring needs a new pre-registration.

---

## D. Adoption criteria

### D.1 Per object
- `m_o` = the mean, over **all** of object o's public episodes, of the cdo_eval of the mesh the gmg ships for that
  episode (the eval emulation: one mesh per episode). Fallback outputs count. TRACK_FAIL and IDENTITY_SWAP episodes
  count with whatever the fallback ladder ships (expected: the ep0 lid, the ep23 boards). A mesh shipped for several
  episodes (a reused PRIOR_PUBLIC mesh, for example the ep2 lid pick shipped for ep0) is scored once (one sha256) and
  enters `m_o` once per episode it is shipped for.
- `L_o` = library_v3 cdo_eval [D, `results/baseline_library.jsonl`]: white_pot 0.437, white_pot_lid 0.421,
  plastic_dish_rack 0.555, blue_cup 0.523, beige_cup 0.856, water_pitcher 0.894, mini_dust_pan 0.331, mini_sweeper
  0.317, wooden_piece_1 0.222, wooden_piece_2 0.216.
- `A_o` = library_v3 add_med in mm [D]: 6.69, 8.13, 5.79, 10.14, 6.97, 7.97, 5.65, 5.25, 2.49, 3.32 (same order).
- **Outcome:** WIN if `m_o ≤ L_o − 0.02`; TIE if `|m_o − L_o| < 0.02`; LOSS if `m_o ≥ L_o + 0.02`.
- **Guards** (all must pass):
  - ADD: the median add_med over o's shipped meshes whose frame is defined ≤ `A_o + 2.0` mm (TRACK_FAIL,
    IDENTITY_SWAP and `frame_undefined` outputs are excluded and listed);
  - flips: for the sweeper and both boards, every shipped mesh flips on at most 1 of the 30 extra seeds; for other
    objects not declared symmetric by the kit, flips_eval = 0 on every shipped mesh;
  - simulator: every shipped mesh watertight after the kit decode, and its rest error ≤ 10° or repaired in the
    simulator copy;
  - **contact subset** (revision 1): for objects with at least 2 contact and 2 lone public episodes, fixed now from the
    dev census and the roster: white_pot contact {0, 2, 26, 27}, lone {41, 42, 43, 44, 45}; blue_cup contact {11, 12,
    13}, lone {21, 22}. A contact episode has another tracked object with at least one contact frame (ep0's single
    2-D-overlap frame counts). The mean cdo_eval over the contact subset must not be a LOSS against `L_o`. The lone
    mean is reported. Reason: every eval pot pair has a partner, and the eval blue-cup pairs mostly do;
  - integrity: the run's strace audit shows zero forbidden opens.
- **Adopt object o** if the outcome is WIN or TIE and every guard passes. A TIE is enough because the gmg mesh is
  compliant and library_v3 is deny-listed.
- **Low confidence, labelled now:** beige_cup (one public episode, 6 separated hand-free frames, nested in the blue cup
  54-67 % of frames [M, dev]). Its outcome counts like any other; every report marks it.

### D.2 Overall
- `W` = the eval-pair-weighted mean of `m_o` (weights: pot 6, rack 5, blue cup 5, beige cup 2, dust pan 2, sweeper 2,
  lid 1, pitcher 1, board 1 1, board 2 1). Library_v3 on this weighting: 0.491 [D].
- **SUCCESS:** W ≤ 0.42 and at least 7 of 10 objects adopted and at most 1 LOSS.
- **PARTIAL:** W ≤ 0.46 and at least 5 of 10 adopted. Adopted objects use the gmg; the owner decides the others (O2).
- **FAILURE:** W > 0.46, or at most 4 of 10 adopted, or any integrity breach. The gmg is not adopted; the current
  submission stays.
- **Scan-informed choices.** Three choices use scan numbers, each as a fixed rule applied once, none tuning a
  parameter: the per-object adoption (D.1), the overall verdict above, and the configuration choice: CPU+GEN (R2)
  replaces CPU-only (R1) for all objects if its W is lower by at least 0.01 and its adopted count is not lower. There
  is no per-object choice between R1 and R2 meshes.

### D.3 What counts as failure, and what follows
- Any FAILURE above; X0 kill (B.1); G1 kill rules (B.9); B.2 failing on its testable pairs (ownership does not
  separate contact pairs). G0 (B.12), B.11, B.13 and B.14 outcomes are not failure criteria of the gmg; they gate or
  fix steps as stated in each.
- After a failure nothing is tuned on its numbers. A redesign needs a new pre-registration and a new counted round.

### D.4 The spoon (no public scan)
The gmg spoon is built for every eval spoon pair, with its report (flags, fallback, watertightness, E). Whether it is
submitted is the owner's decision O5. Default if there is no answer: the current submitted spoon stays, flagged. The
gmg spoon is unvalidated in every case. (v1's 90th-percentile E rule had no validation and is withdrawn.)

### D.5 Phase 2 (clean re-track)
Phase-2 tracks and meshes replace Phase 1 only if R3 passes: mean registered AUC ≥ 0.848 (sweep `a894083` 0.868 [D]
minus 0.02) and no object's mean AUC drops by more than 0.05.

---

## E. Predictions

| ID | Claim | Falsifier | Label |
|---|---|---|---|
| P1 | S1 passes X0 (B.1): mean regret < 0.10 cm, ≥ 7/10 picks at or below the pool median | either fails | [H] |
| P2 | Ownership leaks ≤ 1 % on every testable contact pair; the ep2 pot and lid picks pass V2 against each other (B.2) | > 1 % on ≥ 2 testable pairs, or B.2b fails | [H] |
| P3 | The generic crop reproduces the old in-box voxels (B.3) | Jaccard < 0.95 or > 5 % new outside on > 2 of 25 files | [H] |
| P4 | Ball radii are unimodal per episode; ≥ 60 % of balls repeat across episodes (B.4) | < 40 % repeat, or bimodal in ≥ 2 episodes | [H] |
| P5 | Completions explain unseen observations: lathes ≤ 2.0 mm, mirror objects ≤ 3.5 mm, pitcher ≤ 5.0 mm (B.5) | a miss by > 1 mm | [H] |
| P6 | One selector variant wins ≥ 70 % of LOOO folds (B.6) | no such variant | [H] |
| P7 | All 33 picks watertight after decode; rest error ≤ 10° on ≥ 9/10 objects (B.7) | any non-watertight pick, or ≥ 2 objects failing | [H] |
| P8 | Contact-aware input makes SAM 3D's lid a lid and its pot lid-free (B.9 K-a, K-b) | fewer than half of the runs pass | [H] |
| P9 | SAM 3D's metric layout from our depth places meshes within 10 mm and 15° without ICP (B.9 K-c, testable objects) | fails on ≥ 2 testable objects | [H] |
| P10 | `place.fit` recovers 10 mm / 10° perturbations to ≤ 3 mm median (B.8) | > 5 mm or any flip | [H] |
| P11 | R1: W ≤ 0.42 (point estimate 0.39 [E]); ≥ 7/10 objects WIN or TIE | W > 0.45, or ≤ 5/10 WIN or TIE | [H] |
| P12 | R2: W ≤ 0.39 (point 0.37 [E]); pitcher ≤ 0.60; dust pan ≤ 0.28 | W > 0.42, or pitcher > 0.70 | [H] |
| P13 | ADD guard passes on ≥ 8/10 objects; the sweeper and both boards flip on ≤ 1/30 seeds | fails on ≥ 3 objects, or ≥ 3/30 flips on any of the three | [H] |
| P14 | Phase 2 changes little: pass-1 to pass-2 mesh change ≤ 2 mm median; re-tracked poses within 5 mm / 5° median of today's | > 4 mm change, or > 5 mm / 5° | [H] |
| P15 | Selection does not collapse to fallbacks: ≤ 3 of 33 public pairs use the fallback ladder | ≥ 5 pairs | [H] |
| P16 | On the R1 anchors, the pick's CD-O is at or below every scored alternate on ≥ 7/10 objects | ≤ 5/10 | [H] |
| P17 | The route-A SHELL is not the pick on any static-episode anchor (view_cap60 < 0.4) | SHELL picked on ≥ 2 such anchors | [H] |
| P18 | G0: a separated view gives SAM 3D a lid-only mesh, and a lid-off view a lid-free pot (B.12 SUPPORTED) | NOT SUPPORTED | [H] |
| P19 | X with GT-free registration ranks labelled candidates better than the old metric (B.13: ρ > 0.46 on pot and blue cup) | ρ ≤ 0.46 on either | [H] |
| P20 | M9 masks contain no partner pixel (B.11) | any partner pixel | [H] |
| P21 | V2 vetoes the fused, filled and phantom-body meshes and passes the kit lid (B.14) | any other outcome | [H] |
| P22 | The cross-object identity test flags ep23 board 2 and no other public object-episode (B.15) | flags nothing, or flags another | [H, informed] |
| P23 | t0 is fittable and lies in 1.5-5 mm | not fittable, or outside | [H] |
| P24 | tau lies in 0.02-0.30 | outside | [H] |
| P25 | The contact-subset guard holds for the pot and the blue cup (D.1) | a LOSS on either | [H] |

**Per-object expectations [E]** (R1 CPU core; R2 with generators). Basis numbers are [D] unless marked.

| Object | L_o | R1 [E] | R2 [E] | Basis |
|---|---|---|---|---|
| white_pot | 0.437 | 0.36-0.45 (0.40) | 0.34-0.42 (0.38) | hand kit per episode 0.325-0.597, mean 0.415 (provisional, 7 mm prior); obs lathes 0.413-0.468; SAM 3D ep41 0.328 |
| white_pot_lid | 0.421 | 0.22-0.30 (0.25) | 0.22-0.28 (0.24) | hand kit 0.219-0.224 over the t grid (provisional); Pixal3D-MV 0.253 |
| plastic_dish_rack | 0.555 | 0.46-0.58 (0.51) | same | single-episode kits 0.422-0.509 (leak-affected); all generators ≥ 0.604 |
| blue_cup | 0.523 | 0.29-0.42 (0.35) | 0.27-0.38 (0.32) | lathe ep21 0.291, ep22 0.364-0.493; SAM 3D 0.268-0.299 |
| beige_cup (low confidence) | 0.856 | 0.32-0.60 (0.45) | 0.28-0.55 (0.40) | lathe test passes on ep11 [M]; generators 0.274-0.526; nested in the blue cup 54-67 % of frames [M, dev] |
| water_pitcher | 0.894 | 0.55-0.85 (0.70) | 0.40-0.75 (0.58) | not a lathe [M]; Hunyuan 0.378, SAM 3D 0.649-0.771 |
| mini_dust_pan | 0.331 | 0.26-0.34 (0.30) | 0.23-0.30 (0.26) | clean mirror plane [M]; Pixal3D-MV 0.236-0.240 |
| mini_sweeper | 0.317 | 0.27-0.40 (0.33) | same | depends on the balls; generators ≥ 0.437 |
| wooden_piece_1 | 0.222 | 0.18-0.23 (0.20) | same | prim_boards ep24 0.189-0.212 |
| wooden_piece_2 | 0.216 | 0.16-0.24 (0.20) | same | ep24 slabs 0.164-0.180, flipping 1-4/6 |

Board estimate [E], assuming the spoon stays near 0.18: R1 about 0.33, R2 about 0.32, against 0.402 today.

---

## F. Amendment log

- **2026-10-30, revision 1 (before any gmg code, before any scoring).** Whole-file revision in answer to the design
  review of v1. Its author saw no new scan number; the review itself quoted only existing [M] and [D] numbers. The
  changes are listed in the changelog below.
- **2026-10-31, F-I1: INTERLOCK stage (slots, seats, cavities) and the placement/physics checks along the track.**
  Written 08:50-09:20 UTC at commit `de64bd3` (v1, committed `2eb8397`); **revised 09:30-10:00 UTC (v2) after the
  design review of v1**. Both versions were written before any gmg scoring round (R1 has not started; zero gmg scan
  scorings exist). Their author saw **no new scan number**: the design used zero scan scorings; the only [D] numbers it
  quotes are older ledger entries (XCarve, the planar cut, the October carve tests). v2's new inputs are dev re-runs
  without a scan and documents (carve-20261030, the physics README, `phys_fit.py`, `props_masses_only.json`). Design
  text: `INTERLOCK.md` (this folder; its section 16 maps every review item to its resolution); where it and this entry
  differ, this entry wins. SPEC.md is not edited.
  **Reason.** Owner, 31 Oct ~08:50-09:00 UTC: the boards cannot interlock in a simulator without their slot; let the
  frame-by-frame physics fix carve meshes where pieces must interlock or nest. Dev measurements without a scan
  (`INTERLOCK.md` section 1): along our ep24 track the partner board passes through each board in 56 of 79 contact
  frames on a straight 118.6 mm path, through a band centred 10.5-12.9 mm from where SAM 3D draws the slot; 96-100 % of
  the entered voxels are OBSERVED in the dev grids (bridging and likely partner contamination); V2 finds 0 partner
  samples deeper than its band, so V2 cannot see plate crossings; board 2's S1 pick on the B5 dev pool is a HULL
  (6.8 cm oriented-box thickness) because V5 removed the thin flip-risk shell. October's simulator-copy carves let
  guests sink or fall through (E1 lid 6 mm free travel, E30 sweeper > 40 mm). The rules below are generic, carried over
  from earlier pre-registrations, or labelled informed in F-I1.14; nothing is fitted.
  - **F-I1.0 SPEC rule overridden (declared).** SPEC section 14: interaction carving "only in this copy, never in the
    packed mesh (carving the packed mesh hurt: lid +0.14 to +0.18 [D])". F-I1.4 overrides this sentence for the ICARVE
    and FUSE-I candidates only; the rest of SPEC section 14 stands. Allowed because PREREG section F records amendments
    made before any scoring round and none has run; declared here rather than by editing the frozen SPEC. Justified
    because the October harm came from unconditional single-source carves of the packed mesh, while ICARVE and FUSE-I
    enter only as candidates (two agreeing sources, none disagreeing), compete in the frozen S1 selection, and are
    reverted globally at R1 (F-I1.11) unless they help. Also reconciled with SPEC section 7: on eval the identity test
    only flags (F-I1.2).
  - **F-I1.1 Engaged runs, frames, pose sources** (per ordered pair o <- p): maximal runs of contact frames in which the
    partner evidence occupancy (p's OBSERVED and shared voxel centres plus 2 mm sub-samples, minus p's carved region,
    decided jointly with o's) enters o's candidate by >= 3 voxels; gaps <= 2 stride frames bridged. Kind: INSERTION if
    the partner origin path in o's frame has travel >= 20 mm and straightness (s1 / (s1 + s2 + s3)) >= 0.7; SEAT/REST if
    not INSERTION and the relative speed is < 2 mm per frame for >= 5 frames; SLIDE otherwise; TRANSIENT if < 5 frames.
    Assembled frames = the last stretch of >= 5 frames with relative speed < 2 mm per frame in an INSERTION or SEAT run.
    **Build and check frames:** each run is cut into consecutive 10-frame blocks, even blocks build, odd blocks are held
    out for acceptance; runs < 20 frames use all frames and have no held-out test (flag `no_holdout`). **Pose sources:**
    P_sel (the gmg tracks) for everything that decides submitted meshes; P_sim (the reference the simulator replays: the
    packed policy's reference, or the current Embodiment round's reference) for the simulator copy, if its provenance
    passes F-I1.13 step 2, else P_sel with flag `sim_pose_fallback`. Eval 25: P_sim = the packed eval-25 policy's
    reference (pack 3: `20261025-ev25idfix-02de0c7`), subject to the same check.
  - **F-I1.2 Sources and tiers.** (a) concavity of the placed GEN mesh (notches: closing radius max(6 mm, partner
    thickness at the crossing); cavities: convex hull minus solid), near R_c (2 voxels) or within 20 mm for OFFSET;
    absent if < 80 % of its volume survives remesh and budget; its flip member is chosen by trusted markers, then the
    depth residual, never by the slot side; if neither separates the flips by >= 1 sigma its side is unresolved. (b)
    silhouette: per-pixel two-class 3-component GMMs on Lab colour and a 5 x 5 texture, fitted on the episode's own
    pixels; voxel see-through (SIL) if NMF >= 3 and NMF >= 0.5 NMV over 2-D-separated good frames (hands <= 25 % of the
    mask, no hand pixel within 16 px); used only if held-out pixel accuracy >= 0.9 and false see-through <= 2 % on
    interior voxels with hits >= 10; notch set N_b = SIL components inside the candidate. (c) motion, from build frames:
    voxel persistent if entered in >= max(5, ceil(0.25 N_build)) build frames; swept if the partner-local positions
    entering it span >= max(8 mm, 3 j) at their 90th-percentile extent; d = the principal direction of the partner path,
    signed by its mean velocity; the entry side is where the partner comes from (a physical requirement, not evidence);
    a persistent component is split only if it is a true through-column (along d it exits o at both ends: the voxels 1
    voxel beyond each end are outside the candidate or FREE), by one plane normal to d through its centroid (or the end
    of (a) if (a) agrees), o keeping the far side, one plane per linked pair (F-I1.3) at the median assembled pose. On
    public, (c) is absent if either object is TRACK_FAIL or IDENTITY_SWAP or good in < 80 % of the run's frames; on eval
    IDENTITY_SWAP only flags (SPEC section 7). Agreement: (a, c) centroid distance <= 10 mm, angle between the principal
    axes as unsigned lines <= 15 deg, >= 50 % of R_c inside (a) dilated by 1 voxel, (a) open toward the entry side
    (tested only when (a)'s side is resolved); (b, c) >= 50 % of R_c's testable voxels (NMV >= 3) are SIL; (a, b) >= 50 %
    of R_b (or N_b) inside (a) dilated by 1 voxel. **Any present source that disagrees blocks submitted candidates.** A
    component pushed or ignored by F-I1.3 never yields submitted candidates except at T2o, where (c)'s position is
    excluded from the agreement tests and (a) and (b) must both be present and agree on the notch. Tiers: T3 all three present
    and agreeing; T2 exactly two present and agreeing, the third absent; T2o the OFFSET case with (a) and (b) agreeing on
    the notch; T1 (c) present and CARVE, (a) and (b) absent or disagreeing; T0 otherwise. Submitted candidates (F-I1.4)
    at T2, T3 and T2o; the simulator copy at T1 and above (and T2o as N + t), subject to F-I1.3 and F-I1.8.
  - **F-I1.3 Carve rule** (`gmg/interlock.py decide_pair`; one implementation shared with the Embodiment session; the
    same region builder for our tracks and for the export). Voxel classes on o's 4 mm grid: U = FREE or UNKNOWN; SIL =
    OBSERVED and see-through; GAP = OBSERVED, silhouette absent for it (gate failed or NMV < 3), the component's
    **image width** (median over the views in which >= 3 of its voxels have depth hits, of 2 x the largest inscribed
    radius of its projected 2 mm sub-samples at the depth input's resolution) <= 8 depth pixels, and removing it keeps
    o's component count and genus; O = any other OBSERVED voxel. Per persistent 26-connected component R: IGNORE if
    TRANSIENT or < 3 voxels; PUSH all of R if > 25 % of R is class O (then OFFSET is tried); else R_U is CARVED if the
    carved solid keeps its component count and genus (else PUSH); the SIL and GAP voxels of R_O are CARVED only if (i)
    >= 50 % of R_O's voxels are swept and the run is INSERTION or SLIDE, (ii) not pushable: over the build frames in
    which R is entered, the median of the smallest rigid translation of the partner (26 directions plus R's normal) that
    leaves < 3 entered voxels exceeds 10 mm (with an Embodiment export whose fit block validates: `pushed_residual_m` > b
    in >= 50 % of those frames), (iii) >= 75 % of R_O is SIL or GAP, (iv) measured after the split and at width w_sim:
    the voxels carved for o over all components and rounds total <= 10 % of the candidate's solid volume, R reaches
    <= 0.6 of o's extent along d, and the topology test holds; otherwise PUSH (`interlock_unresolved` when not pushable
    either). **Pair level:** components R_o and R_p are linked if each lies by >= 50 % inside the crossing volume (o's
    candidate intersected with p's at the median assembled relative pose, dilated by 1 voxel); linked components are
    CARVED together only if both pass, else both PUSH (`interlock_pair_fail`); unlinked components are decided per
    target. **Widths:** w_sim = max(1-99 % extent across the feature of the partner samples that entered R at the
    assembled build frames, the partner's delivered simulator collider thickness at the crossing) + 2 x 1 mm; if w_sim
    breaks (iv) the linked pair is pushed (`interlock_partner_too_thick`); w_sub = the partner's evidence two-sided
    thickness at the crossing (else its pick's), capped at w_sim. **OFFSET:** for a component (or linked pair) pushed by
    the class-O step, with an observed notch N (a SIL component, or a placed GEN notch that survived remesh) within
    20 mm: t = the translation on a 2 mm grid, |t| <= 20 mm and |t . d| <= 0.5 |t|, maximising the overlap of N + t with
    R; OFFSET holds if >= 50 % of R lies inside N + t dilated by 1 voxel and N passes the topology test; then the
    simulator copy (P_sim) carves N + t at width w_sim under (iv) and F-I1.8 (class-O voxels inside it listed as
    `o_displaced`), t and the frames go to the tracker, and submitted ICARVE is built at N only at T2o for INSERTION or
    SEAT runs. A shift mostly along d is never OFFSET. Outside OFFSET, class O voxels are never carved.
  - **F-I1.4 New candidates (A.1 addition; overrides SPEC section 14 for these two types, F-I1.0).** ICARVE(c) for every
    feasible STRUCT, FUSE, GEN or SHELL candidate c (never HULL) of an object with a T2, T3 or T2o component: c minus the
    carve solid (width w_sub; at N for T2o) by a manifold boolean; class of c; flag `interlock_carved`. FUSE-I (with GEN
    meshes): FUSE whose observed shell is cut by those carve solids before the union. Both are rebuilt per fold like
    their base.
  - **F-I1.5 Evidence score (A.2, A.4 addition).** Held-out points whose voxel lies in a T2, T3 or T2o carve solid of the
    object are removed for every candidate of that object (paired); the count is reported.
  - **F-I1.6 Vetoes (A.3 additions) and ranking.** **VI:** with I(c) = the median over assembled frames of the partner
    evidence occupancy volume inside c, c is vetoed if I(c) - min over the object's feasible candidates of I(c') > 1.0 cm3.
    **V4t:** more than 1 % of 20,000 volume samples lie more than max(3 sigma, 2 mm) below the table in >= 25 % of good
    frames; applied only if at least one feasible candidate passes it (else flag `track_below_table`). **VP** (GEN,
    FUSE, FUSE-I only): on held-out frames the per-frame placement offset's robust median exceeds 10 mm or 15 deg. **VF**
    (ICARVE, FUSE-I): observed flip margin smaller than the base's by more than 1 sigma (expected to fire rarely; the
    R1 revert of F-I1.11 is the guard against a submitted-mesh flip). **Flip units (A.5 step 3.2):** ICARVE(c) and FUSE-I
    are ranked with their base's flip units. **V5 clarification:** a HULL candidate does not count as the feasible
    non-flip-risk candidate that makes V5 apply (SPEC section 8: HULL is fallback only); every pick it changes is
    flagged `v5_hull_clarified` (dev: `wooden_piece_2` only, of the 4 dev objects with an S1 pick).
  - **F-I1.7 Pick (A.5).** Unchanged; vetoes now V1-V5 plus VI, V4t, VP, VF; the flip-unit rule above.
  - **F-I1.8 Simulator copy (SPEC section 14 copy rule).** Convex pieces of the pick (`gmg/simpieces.py`) at poses
    P_sim: solid at 1.5-2 mm minus the carves at width w_sim; keep-out = carved + FREE + SIL + persistent partner
    occupancy within 2 voxels of the surface; split until every hull holds <= 0.3 cm3 of keep-out; <= 32 pieces (64 if
    the solid > 300 cm3); <= 64 vertices per hull. Layout per episode and round, never overwritten:
    `<obj>/<obj>.glb` + `piece_XX.obj` (same file coordinates) + `inertia.json` + `carve.json`; `_fit/<obj>.glb` (union of
    the pieces); `props_gmg.json` (mass = the 0.3 kg placeholder until owner decision D-I1, since
    `props_masses_only.json` is scan-derived; COM and inertia from the pieces); `manifest.json` (episode, round, P_sim
    and its provenance, sha256 of every file, 8 fiducials per object). **Physical acceptance for every carved pair, any
    kind, any voxel class** (means over 16 jittered copies at 0.5 mm / 0.005 rad, common random numbers), at the
    assembled frame (INSERTION, SEAT), the middle of each static contact segment (<= 3; SEAT, REST, SLIDE, R_U carves) and
    frame 0 if in contact: **P1** 2 s hands-free settle under gravity, hands parked, no drive, in the FlashCHORD scene
    (the carve-20261030 `settle_at.py` recipe): guest and host mean drift <= 1 cm and mean tilt <= 5 deg, mean relative
    sink of the guest along gravity <= 4 mm, no NaN, no fall-through copy; **P2** Monte Carlo free travel of the carved
    guest pieces along gravity, +d and +-n (0.5 mm steps until the overlap with the host pieces exceeds 0.05 cm3 on
    200,000 points) <= max(4 mm, default + 1 mm); **P3** (INSERTION) the replay proxy of `interaction_carve.py` driven
    by P_sim: carved median lag <= 0.5 cm and <= 5 deg at the assembled frames, collider overlap < 1.0 cm3, lag never
    > 1.0 cm after the first assembled frame; **P4** removed collider volume <= 1.5 x the carved region at w_sim and
    >= 90 % of each object's default collider volume kept; **P5** <= 165 collision shapes per episode (merge hulls,
    smallest keep-out increase first; else the pair with the smallest P1 gain gets default pieces); **P6** at every
    checked frame (stride 4 plus rest frames) carved overlap <= default + 0.1 cm3; **P7** (runs with check frames) the
    carved pieces' collider overlap on check frames <= half the default's. Carved pieces are delivered only if all
    applicable tests pass; otherwise the default pieces (flag `interlock_physics_fail`). One asset folder per episode:
    `interlock.load_sim` refuses another episode's folder, and the pack must build per-episode asset roots and pass the
    URDF collision-count check before any launch.
  - **F-I1.9 Features and flags along the track (every candidate, P_sel).** Per-frame 6-DoF placement offsets (trimmed
    point-to-plane, unconstrained directions below 1 % of the largest information eigenvalue excluded): flags
    `placement_offset` (|median| > max(3 sigma, 2 mm) or > 2 deg) and `placement_drift` (MAD > 3 sigma or a 10-frame
    block deviation > max(3 sigma, 5 mm)); interpenetration volume per partner and phase (apart, contact, engaged,
    assembled); table penetration per frame; rest consistency at static segments (speed < 2 mm per frame for >= 15
    frames, no hand within 30 mm: lowest point within max(3 sigma, 2 mm), stable pose within 10 deg, centre of mass
    inside the support; on a partner: contact within b, no penetration deeper than b): flag `rest_mismatch`; hands
    inside the candidate: reported only.
  - **F-I1.10 Generator batches (B.9, B.10, B.12 additions).** G1 and G2 add ep24 board 1 and board 2 on M9's
    separated, hand-free views (1 view x 4 seeds or up to 4 views x 2 seeds; ep23 boards only if they pass B.15); G4
    applies the same rule on eval 25. G0, G1, G2 and G4 record per run: view frame, `cam_T_obj` of that frame, mask PNG
    and sha256, pointmap sha256, seed, the raw mesh before remesh, the layout in camera and object frame, runtime.
    Layout consensus (chordal L1 rotation mean modulo the mesh's flip set, geometric-median translation, median scale;
    outliers > 15 deg or > 10 mm; flip member by markers then depth residual, never by the slot side) and the F-I1.9
    placement features over all good frames are reported next to K-c and K-d (K-c', report only); G0 also reports them
    for the ep2 lid and pot. K-f (report only): share of board runs whose placed mesh has a notch >= 0.3 of the board
    width from one edge that survives remesh. B.10 addition: a GEN mesh's concavity near R_c must keep >= 80 % of its
    volume after remesh and budget, else (a) is absent for it.
  - **F-I1.11 Rounds and adoption (C.3, C.4, C.6, D.2 additions).** R1: for each anchor whose pick is ICARVE, its base
    candidate is also scored, and for each anchor flagged `v5_hull_clarified`, its pre-clarification pick (together at
    most +10). R2: the same for ICARVE or FUSE-I picks (at most +20). Caps: R1 <= 63 (<= 83 under the thickness
    fallback), R2 <= 73; total <= 136 mesh scorings (<= 156); expected use: 2-4 (the boards). **Two global method
    choices, applied once before D.1 is computed:** (1) over all anchors whose pick is ICARVE or FUSE-I, if mean
    (cdo_eval(pick) - cdo_eval(base)) > 0, or any such pick flips on more of the 30 extra seeds than its base or has
    flips_eval > 0 where its base has 0, every ICARVE and FUSE-I pick reverts to its base for submission (the simulator
    copy keeps its carve); (2) over the `v5_hull_clarified` anchors, the same test against the pre-clarification picks;
    if it fails, those picks revert. Tolerance 0 (v1's +0.005 cm was set from XCarve's scan results and is withdrawn);
    per-object differences and their 30-seed spread are reported. These are the fourth and fifth scan-informed choices
    (D.2), each applied once as a method choice, never per object.
  - **F-I1.12 New tests B.16 (build steps BI1-BI4; zero scan scorings)** T-I1 to T-I10 and K-f exactly as in
    `INTERLOCK.md` section 13 (T-I1 sweeps the plate thickness over 6, 10, 13, 18, 25 mm with pre-registered GAP
    outcomes and runs the silhouette on rendered images; T-I2a and T-I2b are reported without prediction), with these
    predictions (E additions):
    - P26 T-I1 synthetic plates and controls pass as stated | any miss (a code bug, fixed and logged) | [H]
    - P27a clean ep24: entry-side share of frame counts >= 0.6 on both boards | < 0.6 on either | [H; dev 0.54-0.57]
    - P27b clean ep24: (a, c) offset along the long axis <= 10 mm on both boards | > 10 mm | [H; dev 10.5-12.9 mm]
    - P27c clean ep24: >= 50 % of R_c OBSERVED | < 20 % (GAP and OFFSET unused on the boards) | [H]
    - P28 T-I3: if T-I2b carves the boards, the carved pieces pass P1-P7 and P3 and the default pieces fail P3 | any
      carved failure | [H]; void, not passed, if T-I2b pushes the boards
    - P29 T-I4: on clean ep24, an existing ICARVE(shell) overlaps >= 1 cm3 less than the slot-less shell and VI removes
      the slot-less shell and HULL | otherwise | [H]
    - P30 T-I5 to T-I7: no class-O voxel carved on ep2, ep11, ep12, ep13, ep18; no delivered carve with free travel
      > 4 mm; <= 165 shapes per episode | any | [H]
    - P31 T-I8: CPU picks' constant placement offset <= 1 mm on >= 9 of 10 anchor pairs; `placement_drift` on the
      ep11 blue cup | < 8 of 10, or no flag | [H]
    - P32 T-I9 on ep24: round 1 reduces the check-frame intrusion volume by >= 50 % and its carved copies pass P1-P7;
      on ep11 no observed floor voxel is carved | either fails | [H]
    - P33 K-f: >= half of the board runs show a notch that survives remesh | fewer | [H]
    - P34 T-I10 negative control (ep31, the eval-30 twin): the rack-sweeper pair delivers its default pieces or a carve
      with gravity free travel <= 4 mm and mean tilt <= 5 deg | any delivered copy outside these bounds | [H]
    These tests gate or fix steps; none is a failure criterion of the gmg (D.3).
  - **F-I1.13 Embodiment contract (operational).** Export schema `gmg-intrusion/2` (`INTERLOCK.md` section 11.2).
    Partner samples (grid pitch <= 2 mm) and target depth come from the union of the delivered round's collision pieces,
    never from the visual GLB; `pts_local` and `rel_T` are in the delivered files' coordinates (never MuJoCo geom
    frames). Header: `meshes` (sha256 of every file read), `reference` with its provenance chain back to perception
    outputs, `fit` (tool, commit, argv, `--meshes` hashes, `--props` path and hash, prior), `pose_source`, fiducials.
    `interlock.validate`: (1) refuse on any mesh hash mismatch, out-of-range frame, non-rigid `rel_T`, fiducial round
    trip > 0.5 mm, `fiducials_world` off the reference pose by > 0.5 mm, or < 99 % of 10,000 samples inside the
    target's pieces (or, mapped back, inside the partner's); (2) refuse if the reference provenance is missing,
    incomplete, or touches a denied input (gmg guard, `ops/provenance/denylist.json`); (3) set every `pushed_residual_m`
    to NaN (flag `fit_provenance_refused`, our push proxy decides) unless the fit's `--meshes` are exactly the round's
    `_fit/<obj>.glb`, its `--props` exactly the round's `props_gmg.json`, and its prior 1 cm / 3 deg. Identical on
    public and eval. Export samples enter the same region builder (build and check frames, persistence, sweep,
    through-column split with the pair's shared plane) and decide_pair; the reach and volume budget are measured after
    the split; the partner's carved region is already absent from its pieces. Round k is accepted only if (A1) on check
    frames the persistent intrusion volume at engaged frames falls by >= 10 % against round k-1 and no other pair or
    phase gains > 0.1 cm3, (A2) check-frame pairs with `pushed_residual_m` > b do not increase (only with a validated
    fit block), (A3) every carved pair passes F-I1.8 P1-P7 and its settle means are no worse than round k-1's by more
    than one standard error, (A4) the cumulative budget, the 90 % collider-volume floor, topology and the 165-shape cap
    hold; otherwise round k is reverted and its budget released. At most 3 rounds; stop early if a round adds no CARVE
    or A1 fails. Round 0 is built from P_sim. Build-frame reductions and zero-action sim_vs_ref are reported, never used
    to decide.
  - **F-I1.14 Constants and origins (A.6 additions).** Engaged >= 3 voxels; TRANSIENT < 5 frames; static < 2 mm per
    frame; persistence max(5, 25 %); sweep max(8 mm, 3 j); through-column test 1 voxel; 10-frame build/check blocks and
    the 20-frame minimum; 50 % majorities and the linking share; 25 % class-O and V4t persistence; budget 10 % and 0.6
    reach; GMM 3 components, 5 x 5 texture, 20 % pixel split; agreement 10 mm / 15 deg (= K-c); offset flags 3 sigma,
    2 mm, 2 deg, 5 mm; 10-frame drift blocks; rest 15 frames and 30 mm hands distance; 16 jittered copies; OFFSET lateral share
    0.5 and 2 mm grid; 99 % containment, 0.5 mm fiducials; A1 10 %: **generic** (statistics, voxel counts, existing K-c /
    V4 / rest definitions, the Embodiment session's minimum-frame and jitter settings). Travel 20 mm and straightness 0.7:
    **informed** (XCarve design of 22 Oct, initial values; its ep24 insertion 11.3 cm / 0.89 and ep2 lid 1.7 cm were
    seen). Push prior 10 mm / 3 deg: **generic** (phys_fit v1's prior). w_bridge 8 depth pixels: **generic [H]** (two
    cells of a quarter-resolution stereo cost volume). Silhouette NMF >= 3, 0.5 and the 2 % false-free gate:
    **informed** (22 Oct S2 design; 1 % / 0 % on the boards seen with a scan slot box). VI 1.0 cm3 margin, collider
    overlap 1.0 cm3, proxy lag 0.5 cm / 5 deg vs default 2 cm / 20 deg, 1 mm clearance, 0.3 cm3 keep-out, 32/64 pieces,
    64 vertices: **informed** (26 Oct pre-registered carve rule and `collision_decomp.py`, written before their results).
    Settle 2 s, 1 cm / 5 deg, P6 0.1 cm3: **informed** (carve-20261030 criteria 2 and 3, written before its results).
    Free travel and relative sink 4 mm (2 x 1 mm clearance + one 2 mm carve voxel), P4 1.5 x and 90 %, the 165-shape cap:
    **informed** (chosen after seeing carve-20261030's 6 mm / > 40 mm travel, 4-13 x removal, 35 % loss and note 19's
    budget). OFFSET t_max 20 mm (two push-prior widths): **informed** (the dev offset 10.5-12.9 mm was seen). 80 % remesh
    survival, 0.3 W notch: **generic**. Global carve and V5-clarification tolerance 0: **generic**. Placeholder mass
    0.3 kg: **generic** (make_assets default).

- **2026-10-31, F-I2: INTERLOCK build-time corrections (build step BI1, T-I1 synthetic tests).** Written 11:10-11:30
  UTC while building `interlock.py`, `silhouette.py`, `gen_slot.py`, `physcheck.py`, `simpieces.py`, `simphys.py`
  (commit recorded in `build/I.md`). Still before any gmg scoring round (zero gmg scan scorings exist; no scan number
  was read for this entry). Inputs: the T-I1 synthetic runs (`tests/test_interlock.py`) and dev runs without a scan.
  **No numeric threshold of F-I1.14 changes.** F-I1.12 says a T-I1 miss is a code bug, fixed and logged before BI2;
  these are the fixes and the definitions they make explicit. Where F-I1 and this entry differ, this entry wins.
  - **F-I2.1 Silhouette classes at 2 mm.** Votes are also cast on the 2 mm sub-grid; a 4 mm voxel is SIL if any of
    its 8 sub-voxels is see-through (NMF >= 3, NMF >= 0.5 NMV) and SOLID if none is and one is testable. Reason: a
    4 mm voxel straddling a slot edge was "seen solid" by its centre pixel (T-I1 s1, t = 6 mm: 36 of 96 voxels O).
  - **F-I2.2 Across axis n.** n = the direction perpendicular to d in which the partner's evidence near the crossing
    (inside the target candidate dilated by 2 voxels, median assembled pose) is thinnest (the partner plate's
    normal); fallback the component's thinnest axis (export input, < 20 samples). Reason: the component's thinnest
    axis is min(target thickness, partner thickness) and picked the target's own thickness (w_sim 24.5 mm for a 6 mm
    partner in T-I1).
  - **F-I2.3 Image width (GAP).** Measured on the region closed in 3-D (2 iterations, inside the voxels it spans) with
    2-D hole filling, pixel-centre convention (radius = distance transform - 0.5). Reason: the partner's evidence is
    its observed faces (its interior is UNKNOWN), so the region is hollow and its projection too narrow (t = 18 mm gave
    8.0 px against the pre-registered 10.8 px).
  - **F-I2.4 Unseen orphans.** If the R_U carve fails the topology guard, candidate components it cuts off that hold
    no OBSERVED voxel and lie inside the convex hull of R are carved with it, and the guard is re-tested. Reason: a
    hollow inner-cup region leaves the unseen core of a filled outer candidate as a separate component (T-I1 n9).
  - **F-I2.5 Carve solid.** Every carve (CARVE and OFFSET) is the candidate's 2 mm sub-voxels inside the region's
    (d, m) footprint with |n - c_n| <= w / 2; sub-voxels of class-O voxels are excluded (step 4 never carves them);
    it is also written as an exact oriented box when the region's extent along d is >= 2 w (v2 also required the m
    extent, which a plate thinner than twice its partner never has) and the box cuts no class-O voxel.
  - **F-I2.6 Budget (iv) scope.** (iv) applies to carves that hold R_O voxels (INTERLOCK 4.2 step 4 lists it there);
    an R_U-only carve has the topology guard of step 3 and the physical tests of F-I1.8; the cumulative 10 % volume
    counts every carve. Reason: a filled outer cup's cavity is far above 10 % of the candidate (T-I1 n9).
  - **F-I2.7 U voxels with R_O.** U voxels rejected alone (an internal void) are carved with the R_O voxels when the
    union keeps the topology (the interior of a thick plate's slot).
  - **F-I2.8 Pair level.** A linked pair carves when each side either carves on its own or has a holding OFFSET;
    {OFFSET, CARVE} is allowed (a lateral offset of one plate is no offset in the crossing plate's frame, T-I1 o1);
    two OFFSETs need t_p = -R^T t_o within two grid steps; otherwise both PUSH (`interlock_pair_fail`).
  - **F-I2.9 Through-column ends.** "Each end of the component" = its end layer (voxels within one voxel of its
    smallest / largest coordinate along d); the end exits if the majority of its layer does.
  - **F-I2.10 Generator placement without saved layouts.** The 29 Oct SAM 3D meshes have no layout (unit size): dev
    placement = similarity ICP to our observed samples within 6 mm of our pick (clean OBSERVED grids hold voxels far
    from the object: ep24 board 1's span 417 mm), 4 PCA sign starts, flip member by the residual (margin in sigma);
    `gen_slot.layout_consensus` is built for G1/G2 runs that save layouts. Remesh survival uses our watertight 2 mm
    remesh + fit_budget(4000) until B15's M10 exists.
  - **F-I2.11 Silhouette negatives.** Pixels 8-40 px outside the target's projected mask, outside every other
    object's (dilated 8 px) and the hands' masks, instead of "depth > 20 mm behind": build 1's batch deletes the depth
    caches to save disk (5 GB free). The colour model needs background colour samples only.
  - **F-I2.12 P1 here.** The FlashCHORD scene is not in this container: no carve is delivered from it (the default
    pieces are delivered and the carved pieces kept under `_carved_pending_p1/` for the FlashCHORD settle); the
    plain-MuJoCo settle is reported as the pre-check (INTERLOCK 6.2: it does not decide).
  - **F-I2.13 Contract clarifications.** The reference may be a parquet file (their reference format); the guard is
    applied to every input of its provenance chain and to the reference path except for the `.parquet` suffix itself;
    the export header carries `reference_poses_f_star` (the reference pose of each object at f_star) and `T`, so the
    fiducial check needs no parquet reader (the guard refuses `.parquet` reads).
  - **F-I2.14 Known miss of P26 (kept, not tuned).** T-I1 s1 at t = 6 mm decides PUSH, not CARVE: the 4 mm motion
    region overhangs a 6 mm slot by one voxel column of seen wood (32 of 96 voxels class O > 25 %). A resolution limit
    of the 4 mm evidence; the ep24 boards are 13-19 mm thick in our observations [M]. The test is marked as an
    expected failure, so a change that silently "fixes" it is visible. Second known miss: T-I1 (g) gives T3 on
    plate A but T1 on plate B: a 5 deg error about the plate centre plus 4 mm moves B's 10 mm slot by 6.7 mm, so 42 %
    of R lies in C_a dilated by one voxel (< 50 %) and (a) disagrees; the agreement rule is kept as pre-registered.
  - **F-I2.16 Generator closing radius cap.** r = min(max(6 mm, the partner pick's thinnest 1-99 % extent), 20 mm):
    the thinnest extent of a pot or cup is its diameter (a 150 mm closing ball ran out of memory on ep2).
  - **F-I2.17 Generator notches inside the candidate.** C_a is restricted to the target candidate's occupancy, as N_b
    is (3.2): generator concavities where our candidate has no material (around marker posts, above faces) are not
    notches of our mesh.
  - **F-I2.15 T-I1 coverage in BI1.** Run and passing: s0 sweep (6, 10, 13, 18, 25 mm), s1 with synthetic votes
    (10-25 mm), o1, o2, w, n2, n3, n4, n5, n6, n7 (geometry: slot travel <= 4 mm, through-cut > 40 mm), n8, n9, (g)
    (plate A T3; plate B the known miss above), the export round trip and the fiducial refusal. Not run in BI1
    (open): s2 and the rendered-image silhouette cases.

- **2026-10-31, F-I3: INTERLOCK round-1 fixes (after the verifier's review of the BI1/BI2 build).** Written 13:55-15:30
  UTC. Still before any gmg scoring round (zero gmg scan scorings exist; no scan number was read for this entry; the
  only new inputs are the review, synthetic tests, the Embodiment tool's code at `48cda9f` and dev runs without a
  scan). **No numeric threshold of F-I1.14 changes**; the new definitions reuse existing constants (50 % majority,
  0.3 cm3, 0.5 mm, 10 %). Where F-I1 / F-I2 and this entry differ, this entry wins. Code: `interlock.py`,
  `simpieces.py`, `simphys.py`, `tools/interlock_dev.py`, `tests/test_interlock.py`; notes `build/I.md`.
  - **F-I3.1 One rule on both paths (review B2).** `interlock.make_side` builds a target of a pair the same way on our
    tracks and on an Embodiment export: engaged runs (with a fixed hold-out, F-I3.3), persistent regions, the identity
    / track gate of F-I1.2 from our bundle (public: TRACK_FAIL or IDENTITY_SWAP makes (c) absent; eval: IDENTITY_SWAP
    only flags), sources (a) and (b) and the observed notches. The gmg writes (a), (b) and the notches of every target
    to `<round>/sources/<obj>.npz` when it delivers round 0, and every later round carries them; `carve_from_intrusions`
    reads them, so SIL, GAP, OFFSET and the tiers can fire on the export path. On the export path the partner's full
    samples are the union of its delivered pieces at 2 mm (what the exporter samples): the across axis n (F-I2.2) and
    the push proxy use them, as the partner evidence is used on the tracks path.
  - **F-I3.2 The submitted solid obeys class O (review B4a).** ICARVE carves exactly the voxels the rule carved (R_U,
    SIL, GAP and the unseen orphans) at width w_sub, minus the sub-voxels of every class-O voxel, as the simulator solid
    does; at T2o the notch N minus its class-O voxels (OBSERVED and not see-through). An empty submitted solid is no
    submission (flag `submitted_solid_empty`).
  - **F-I3.3 Iteration as pre-registered (review B3).** (a) The budget (iv) is cumulative over rounds and over the
    components of one call, against the ROUND-0 solid volume (stored in each round's `manifest.json` `interlock`
    block with the carved volume so far); a reverted round releases its budget because the next round starts from the
    previous folder. (b) `round_accept` computes nothing if either export fails `validate` (not accepted). (c) A1 =
    on the engaged check frames, the persistent intrusion (export samples inside the regions the round carved, on the
    target's grid) falls by >= 10 % AND no ordered pair gains > 0.1 cm3 of intrusion in either phase (engaged check
    frames; all other frames), the targeted pair's engaged-check phase excepted. (d) Check frames are fixed when a run
    is first built and stored in the round (`interlock.holdout`); a later round never builds from them and never
    recomputes them (`engaged_runs(..., holdout=)`). (e) A3 = the carved pair passed P2-P7 here AND the Embodiment's
    jitter_check settle (`--k 16`) reports a pass; without that report A3 is pending and the round is not accepted.
    A4 = cumulative carve <= 10 % of the round-0 solid, >= 90 % of the round-0 default collider volume, topology kept,
    <= 165 shapes, read from the round folder. Measured on the synthetic cross (15:40 UTC) [M]: the export path's
    round-1 carve is a voxel carve (its region holds class-O voxels), our splitter re-decomposes the carved solid and
    partly refills it, the persistent check-frame intrusion falls only 435.3 -> 403.5 cm3 (-7 %), A1 fails and the
    round is rejected: the acceptance test works, the splitter is the open problem (F-I3.8).
  - **F-I3.4 OFFSET carves have a budget (review B4b).** N + t at width w_sim is measured by (iv) (cumulative volume,
    reach <= 0.6 along d, topology of the carved sub-voxels) before the pair level decides; an OFFSET that fails it does
    not hold (`budget_iv_fail (N + t)`), so its linked partner cannot carve on it.
  - **F-I3.5 Two-way, notch-shaped (a) (review B5; required before any submitted ICARVE).** The (a) notch near R is
    the WHOLE connected components of C_a that touch R dilated by 2 voxels (v1 cut C_a down to that neighbourhood, so a
    concavity covering the whole candidate agreed with any R). Agreement adds the reverse share: >= 50 % of those
    components must lie in R dilated by one voxel (besides >= 50 % of R in them, centroid <= 10 mm, axes <= 15 deg).
    The (a, b) test is two-way the same way, and an OFFSET notch N + t must also lie by >= 50 % in R dilated by one
    voxel. On ep24 the placed SAM 3D concavities (63 x 117 mm blocks) therefore disagree; P27b's pass is not evidence
    of a slot.
  - **F-I3.6 Class-O residual and test o2b (review B7; written before o2b's first run).** The class-O voxels of a
    carved region are never carved; the intrusion left there is a pose error and goes to the push list next to the
    carve (`PUSH_RESIDUAL`, flag `o_residual_push`). Pre-registered T-I1 o2b: a track offset of 11 mm ALONG d at every
    frame with silhouettes that see the true slots (and their notches): both plates CARVE, never OFFSET, every carved
    sub-voxel (simulator and submitted solid) within one 4 mm voxel past the true slot end, flag `o_residual_push`.
    *Correction after o2b's first run (14:40 UTC; the rule is unchanged, only my expectation was wrong):* the flag
    is expected on plate A only. The offset pushes the partner past A's slot end (class O on A's carve side), while
    on B the overshoot lies beyond B's split plane, in A's half of the cross, so B's carve side has no class O
    (measured: B U 31 / SIL 35 / O 0).
    o2 (now o2a) keeps its F-I1.12 form (testable silhouette that sees wood: PUSH, no OFFSET). n4 asserts that the
    3-frame contact is seen (>= 3 voxels entered), its run is TRANSIENT and nothing is carved (no vacuous pass).
  - **F-I3.7 One-sided region.** When only one target of a pair has a persistent region (e.g. a sparse partner
    evidence), every record of the pair carries `one_sided_region`.
  - **F-I3.8 Delivered pieces obey the F-I1.8 keep-out (review B6).** A delivery uses our pieces only if every hull
    holds <= 0.3 cm3 of keep-out; else CoACD's pieces of the pick checked against the same keep-out; if neither set
    complies, the round folder is marked do-not-use (`DO_NOT_USE.json`, `manifest.do_not_use`) and `load_sim` refuses
    it (diagnostics may override explicitly). The 31 Oct r0 folders that violate F-I1.8 (ep2 pot 1250 cm3, ep11 cups
    945 / 533 cm3, ep24 boards 0.72 / 2.0 cm3 per hull) are marked do-not-use in `build/I/sim_r0/`. Measured on the
    ep24 re-run (14:37 UTC) [M]: our board pieces 0.72 / 2.0 cm3 max (13 / 21 of 32 hulls over 0.3), CoACD's
    (threshold 0.05) 52.9 / 77.3 cm3 max (12 of 13 / 15 over): neither complies, so the new ep24 round 0 is
    do-not-use as well (keep-out weights as in F-I1.8: partner occupancy counts 10 x).
  - **F-I3.9 Delivery layout (contract).** `props_gmg.json` in the phys_fit layout {obj: {physics: {mass_kg, com_m,
    inertia_kgm2, ...}}} (the layout of `props_masses_only.json`; mass still the 0.3 kg placeholder, D-I1 open);
    `manifest.json` schema `gmg-sim/2` with `objects.<obj>.{files, fiducials}` (the Embodiment reader's layout) plus
    the gmg-sim/1 top-level `files` / `fiducials`, the code identity (sha256 of the interlock code files and a dirty
    flag) and the `interlock` state. Fiducials (definition in `simpieces.fiducials`): the 8 corners of the oriented
    bounding box (principal axes of all piece vertices) of the pieces, each coordinate 1 mm inward along each box axis.
    One pending folder name: `_carved_pending_p1/`.
  - **F-I3.10 Validator on the Embodiment tool's export (review B1; the orchestrator's 10:55 resolutions).** Header:
    `meshes` keyed by basename or `<obj>/` path, the set of piece files must equal the round's; `frames` or `T`;
    `fiducials_file` must equal the round's fiducials. A malformed export (missing arrays, out-of-range frames or
    indices, sample groups without a frame-pair row, f_star out of range) is refused, never raises. Provenance: the
    chain's per-step `inputs` and artifacts are read (and a top-level `inputs`); every step names a tool and a run id;
    a perception `poses.npz` with a sha256 must be in the chain (resolution 3: `poses_world_vo.npz` is not required);
    a chain given by `--prov`, inferred or marked reconstructed is accepted with flag `prov_reconstructed`; refused:
    mocap, `/scan`, `_scan`, `_align`, `oracle`, `/loc/`, deny-list globs and sha256, the gmg refused folders, and a
    dataset episode parquet (by location: `track_3/`, `/hfds/`, `/data/chunk-`, `episode_0`); other `.parquet` files
    (references) pass; library_v1..v4 files pass only as simulator mesh assets (a mesh suffix or `/content/assets`;
    flag `ref_sim_assets_library`), never as an object-motion source. **Independent reference pose (resolution 2):**
    the header's own poses are never used; the pose at f_star comes from (i) an independent reader of the reference
    (`ref_poses`; hook for B10: a guard role that reads only the `object_body_*` columns of our reference parquets,
    since guard.py refuses `.parquet` and is build 1's file), or (ii) our tracks (role tracks) when their sha256 is
    the chain's `poses.npz`: one rigid transform common to all objects plus a per-object vertical shift (mkref's
    table snap) fitted on the fiducials, then every object's fiducials AND the export's rel_T at f_star (the partner's
    fiducials mapped by rel_T and by the poses) must agree within 0.5 mm. No independent source: refused. Known blind
    spot of (ii): a re-centring along the reference's vertical axis at f_star is absorbed by that object's vertical
    shift; the rel_T deviation over all rows is reported (not enforced: a reference may legitimately change object
    poses frame by frame).
  - **F-I3.11 Correction of F-I2.14's justification (review B8).** "The ep24 boards are 13-19 mm thick in our
    observations" is the stereo EVIDENCE thickness, not the boards'. In cam_a frame 26 of `ep24_a.mp4` board 2's slot
    is about 10-12 px wide at about 1.6 px/mm along the long axis, roughly 6-8 mm including the visible inner wall
    [E, by eye, GT-free; looked at again for this entry]. So the t = 6 mm known miss is the regime of ep24 and eval 25,
    not a corner case. INTERLOCK 18.1's explanation is withdrawn: the motion region is 19-25 mm wide (the partner's
    evidence thickness plus jitter), 2-4 times the slot, so even a perfect silhouette that sees the true slot would leave
    most of R class O (> 25 %) and step 2 would still PUSH; the brown table may also hurt the colour model, but it is
    not why the boards PUSH, and the [H] that a depth-free see-through test would separate the cases is withdrawn.
    New [H] (not pre-registered, not used): the region must be measured against the partner's PLATE thickness, not
    its evidence thickness; falsified if, on ep24, the entering partner samples restricted to the partner's own
    two-sided plate thickness still give a region wider than 2 x the video slot width.
  - **F-I3.12 Column rule (no pockets under seen faces; written 14:43 UTC after o2b's second run failed its
    pre-registered bound).** For INSERTION and SLIDE runs a partner that passes through a plate fills the plate's
    thickness (the carve frame's m axis). A voxel of R whose column along m (same d and n cell, 4 mm raster) holds a
    class-O voxel of R is not carved, and is kept out of the carve solid's footprint (simulator and submitted): carving
    it would only open a pocket under a seen face. If nothing carvable remains, the component is PUSHED. Reason [M]:
    o2b carved A's unseen mid-plane voxels past the slot end, reaching 7.5 mm beyond it (the round-1 review saw the
    same in o2sil and a half-thickness pocket in offset_asm); with the rule A's carve ends 1.5 mm past the slot end
    (sub-voxel centre). Cavity carves (SEAT, REST, the n9 cup) are not affected. No constant is added.
  - **F-I3.13 Known difference between the paths (logged, not tuned; measured 15:20 UTC).** With the same rule and the
    same sources, the export path decides from the partner's delivered PIECES (F-I1.13) and our tracks path from the
    partner's stereo EVIDENCE (F-I1.1). On the synthetic cross the two agree with see-through silhouettes (t = 10 and
    18 mm: CARVE T2 on both plates on both paths) but not without one at t = 10 mm: GAP image width 5.0 px on the
    tracks path (the evidence partner is about 6 mm thick on the 4 mm grid) against 7.0 / 9.0 px on the export path
    (the 10 mm pieces), so board B is class O and the pair PUSHES on the export path while the tracks path CARVES at T1.
    The test is kept as an expected failure. [H, not used] Deciding the export's regions from our partner evidence
    moved by the export's rel_T (P_sim), with the export's own samples used for validation and acceptance only, would
    make the two paths identical up to the pose source; falsified if that variant still differs on this case.

- **2026-10-31, F-I4: board slot under the owner's waiver of the camera rule (plate-plate INSERTION pairs, simulator
  copy only).** Written 16:03-16:25 UTC and committed and pushed **before any code or run uses it**. Still before any
  gmg scoring round (zero gmg scan scorings exist; no scan number was read for this entry). **Post hoc** with respect
  to the ep24 dev results of `INTERLOCK.md` sections 18-19, which the author has seen: both boards PUSH at the class-O
  step; the motion band is 25.1 / 19.1 mm wide against a slot of about 6-8 mm in the video [E]; DIAG motion-band slot
  replay 0.33 cm / 9.4 deg against 1.85 cm / 113 deg for the default (16 copies); P2 +n 13 mm with w_sim 21.7 mm; our
  pieces hold 0.72 / 2.0 cm3 of keep-out per hull, CoACD's 52.9 / 77.3 cm3. No number of a run under this entry exists
  when it is committed. Where F-I1 to F-I3 and this entry differ, this entry wins for the pairs in its scope, and only
  there. Design text and the run plan: `INTERLOCK.md` section 20. Code (a later build step; new code paths only, the
  F-I3 behaviour stays the default): `interlock.py` (the waiver branch), a new `platebody.py` (plate body, analytic
  slot, pieces), `simphys.py` (the P3 overlap clause, F-I4.7), `tools/interlock_dev.py` (flag `--waiver-fi4`),
  `tests/test_interlock.py` (F-I4.10).
  - **F-I4.0 The waiver (verbatim) and its scope.** Owner, session_01W8Softjo2xx7o6ofSiheuQ, 31 Oct ~16:00 UTC:
    "Okay I waive that camera rule". It answers the report that the pre-registered rule pushes the ep24 boards because
    stereo calls the slot observed solid (class O) and the RGB silhouette cannot confirm it (board 1: a hand within
    16 px in 33 of 34 separated frames; board 2: a testable silhouette that sees wood, SIL share 0.008) [M, INTERLOCK
    18.1, 19.1]. **Scope:** a linked pair (F-I1.3 linking) whose two targets are both plate-like (F-I4.1) and whose
    linked components both come from INSERTION runs (travel >= 20 mm, straightness >= 0.7; F-I1.1, unchanged). For
    these pairs only, and for the simulator copy only: (a) **class O no longer blocks a carve**: F-I1.3 step 2 (PUSH when
    more than 25 % of R is class O), step 4 (iii) (>= 75 % of R_O SIL or GAP), the column rule F-I3.12 and the clause "class-O
    voxels are never carved" (F-I1.3, F-I2.5, F-I3.2 for the simulator solid, F-I3.6) do not apply to the analytic slot
    of F-I4.3; (b) **an absent or failing silhouette no longer blocks it** (gate failed, NMV < 3, or a testable
    silhouette that sees wood). **Every other gate stays, unchanged:** engaged runs and the INSERTION kind; persistence
    n_v >= max(5, ceil(0.25 N_build)); the sweep test (>= 50 % of R's OBSERVED voxels swept at max(8 mm, 3 j): the
    partner moves through); not pushable (F-I1.3 (ii): the median smallest rigid partner translation over the build
    frames in which R is entered > 10 mm, or a validated `pushed_residual_m`); budget (iv) and topology (on the
    analytic slot, F-I4.4); the linked pair carves both or neither (F-I1.3, F-I2.8); the identity / track gate (F-I1.2,
    F-I3.1: on public, TRACK_FAIL or IDENTITY_SWAP makes (c) absent; on eval IDENTITY_SWAP only flags); the physical
    acceptance (F-I4.7); the pieces keep-out gate (F-I3.8, F-I4.6). **Outside the scope nothing changes:** cups, pot,
    lid, rack, sweeper, dust pan and spoon pairs, every SEAT, REST, SLIDE or TRANSIENT run, and any pair with a target
    that is not plate-like follow F-I1 to F-I3 exactly (the ev10w measurements say cup intrusions are track errors).
    **Submitted meshes are unchanged:** the waiver never creates an ICARVE or FUSE-I candidate; F-I3.2 (the submitted
    solid obeys class O) and the tier rules stand; the board's submitted (CD-O) mesh is not touched in this step. A pair
    in scope that fails a kept gate gets its F-I1 to F-I3 decision (PUSH, or OFFSET as before) and the record names the
    failing gate (`waiver_gate_fail:<gate>`). Every record in scope carries the flag `owner_waiver_fi4`; its tier is T1
    (simulator only; `interlock_disagree` if (a) or (b) is present and disagrees). One branch serves both paths (F-I3.1:
    our tracks and an Embodiment export); round 0 is built from our tracks.
  - **F-I4.1 Plate-like (the existing code path) and plate thickness.** An object is plate-like if
    `structure.hypotheses` (`structure.py`, build step B7; its `_points` and `_planes` steps may be called alone, the
    same code) finds at least one **plane pair** (`accepted['plate']`): two planes parallel within 30 deg, seen from
    opposite sides with the material between them, footprints overlapping by >= 0.5, the gap inside the slab two-face
    window 3-25 mm (PREREG A.6, informed). The window is the thin-extent part of the test. Input: the object's owned
    points (`own == 0`) in the episode's clean bundle that lie within 6 mm of its pick's surface (the F-I2.10 filter:
    the clean OBSERVED grid of ep24 board 1 spans 417 mm, and its owned points in frames ~72-240 lie about 125 mm from
    its candidate [M, INTERLOCK 18.1]); sigma = the bundle's sigma of the object. **The plate pair** of the object is
    the pair with the largest footprint overlap, ties broken by the larger inlier count of its two planes. It gives the
    object's **plate thickness t** (`thickness_mm`) and its mid plane (`mid_n`, `mid_d`). Seen before this entry [M,
    dev obs_all files, B7]: ep24 board 1 one pair, 7.4 mm (overlap 0.98); ep23 board 2 two pairs, 11.6 mm (1.00) and
    4.4 mm (0.75); none on the lid, the two cups, the sweeper, the pitcher, the pot, the rack or the dust pan. The clean
    ep24 values are unknown when this is written. Not used for t: the evidence thickness w_sub (12.6 / 14.6 mm on the
    DIAG; F-I3.11 says the evidence thickness is not the plate's) and `thickness.two_sided_measurements`.
  - **F-I4.2 Plate body (the simulator body of each target in scope).** If a STRUCT plate candidate (P-PROG slab, B8 or
    B11) exists for the object, it is the body, and its marker balls are kept. Otherwise the body is the **extrusion of
    the observed outline** at thickness t. This is the expected case on ep24 [M, listing at 16:10 UTC]: the candidate
    folder holds only `shell_t5p36` and `hull`, and the STRUCT producers are not built. Outline: the F-I4.1 points with
    |mid_n . x - mid_d| <= t / 2 + 3 sigma, projected on the mid plane and rasterised at 2 mm; a cell is in the outline
    if it holds points of >= 3 distinct frames (the OBSERVED rule hits >= 3, A.6); one 3 x 3 closing, holes filled, the
    largest 8-connected component kept. Its minimum-area rectangle (over the cell corners) gives the long axis a_L and
    length L (the longer side), the width axis a_W and width W_o, and the normal a_T = mid_n. Body = the box
    L x W_o x t centred on the rectangle's centre in the mid plane, with no marker balls (flag `plate_body_no_markers`).
    If the component fills less than 0.9 of its rectangle, no analytic body exists and the pair leaves the waiver route
    (`plate_outline_not_rectangular`). Reported, not used: the volume share of the body inside FREE voxels of the
    object's grid. The body replaces the pick (shell or HULL) in the simulator copy of both targets of the pair; the
    visual `<obj>.glb` stays the submitted mesh (unchanged).
  - **F-I4.3 Slot geometry from GT-free evidence (not from the motion band's width).** Per target o of the linked pair,
    in o's frame, with partner p and o's own run direction d (F-I1.1):
    - **width** along a_L: w = t_p + 2 x 1.0 mm (t_p = the partner's plate thickness, F-I4.1; the 1 mm clearance of
      F-I1.14);
    - **centre line**: c_L = the centroid along a_L of o's linked persistent component (all its 4 mm voxel centres,
      unweighted, before the split);
    - **entry edge**: the edge of o's body, along a_W, on the side the partner comes from (F-I1.2: the -d side);
    - **depth** along a_W from the entry edge: D = P + 2.0 mm, with P = the partner's deepest penetration = the 99th
      percentile, along a_W from the entry edge, of the partner evidence samples that entered o's region R (the
      component after the pre-registered through-column split, F-I1.2) in the assembled build frames, capped at the
      depth of the pair's shared split plane when that split applied. Reason [M, INTERLOCK 18.1]: the partner's own
      slot is bridged in its evidence, so the unsplit region spans the full width (131 / 128 mm) and the unsplit
      penetration is the full width by construction. With both slots bridged, the evidence constrains only the sum of
      the two depths; the split plane (the pre-registered tie-break through the centroid of both components at the
      median assembled pose) sets each board's share. Each depth is therefore a prior [E], not a measurement; the check
      below tests the sum;
    - **through the full thickness**: along a_T the slot spans t + 2 x 3 mm; along a_W it starts 3 mm outside the entry
      edge (the 3 mm extension of `carve_solid`), so the slot box opens the edge and both faces cleanly.
    - **Cross-lap consistency (both targets, once per pair):** W_x = the extent along d (o's frame) of the intersection
      of the two unslotted bodies at the median assembled relative pose (2 mm grid points inside both). If
      |D_o + D_p - W_x| > 10 mm, the linked pair is PUSHED with flag `interlock_slot_inconsistent` and nothing is
      delivered. Reported per target: the angle between d and a_W, and between the partner's plate normal (mapped into
      o at the median assembled pose) and a_L.
  - **F-I4.4 Budget (iv) and topology on the analytic slot (unchanged thresholds).** Volume share = volume of
    (slot box intersected with the body) / body volume, cumulative over rounds against the round-0 body (F-I3.3),
    <= 10 %; reach = extent along d of (slot box intersected with the body) / extent of the body along d, <= 0.6;
    topology: D < W_o and both prongs keep a positive length along a_L (one connected body of genus 0). A failure is
    `budget_iv_fail` and the pair PUSHES.
  - **F-I4.5 Width for P2 (post hoc; fixes open problem 2 of INTERLOCK 18.4).** For pairs in scope w_sim = w of F-I4.3
    (t_p + 2 mm). F-I1.3's terms "1-99 % extent across the feature of the entering partner samples" and "the partner's
    collider thickness at the crossing" are not used. The partner's simulator body is its plate body (thickness t_p,
    no bump), so the slot is 2.0 mm wider than the partner's collider by construction. The failure it answers [M,
    seen]: DIAG w_sim 21.7 mm from the partner's 1-99 % extent near the crossing (19.7 mm, marker bump included)
    against w_sub 12.6 mm, P2 +n 13 mm. w_sub is not used (no submission).
  - **F-I4.6 Pieces (analytic; keep-out met by construction; the gate still runs).** Slotted body = three boxes that
    share faces: the solid part (full length L, from the slot bottom to the far edge, full t) and two prongs (from the
    entry edge to the slot bottom, along a_L from each end of the body to the side of the slot, full t); plus one
    convex piece per marker ball the body carries (an icosphere hull of <= 64 vertices). Default (for P2-P7) = the
    unslotted body (one box, plus the balls). The F-I3.8 gate runs on the slotted pieces with the F-I1.8 keep-out
    (carved slot + FREE + SIL + the partner's persistent occupancy, within 2 voxels of the slotted body's surface;
    partner and carve weight 10): every hull <= 0.3 cm3, else the delivery is do-not-use. No splitter and no CoACD.
  - **F-I4.7 Acceptance (thresholds unchanged; 16 jittered copies, 0.5 mm / 0.005 rad, common random numbers, where
    the simulator runs).** Poses P_sim (public ep24 dev: P_sel, flag `sim_pose_fallback`); carved = the slotted bodies;
    default = the unslotted bodies. **P2** free travel along gravity, +d and +-n <= max(4 mm, default + 1 mm). **P3**
    replay proxy: carved median lag <= 0.5 cm and <= 5 deg at the assembled frames, lag never > 1.0 cm after the first
    assembled frame, no NaN copy, and collider overlap < 1.0 cm3 at the assembled frames (the median carved overlap of
    the P6 series; this F-I1.8 clause is missing from `simphys.p3_pass` and is restored, not new). **P4** removed
    collider volume <= 1.5 x the slot's volume inside the body, and >= 90 % of the default collider volume kept. **P5**
    <= 165 shapes per episode. **P6** carved overlap <= default + 0.1 cm3 at every checked frame. **P7** carved
    check-frame overlap <= 0.5 x the default's. **Keep-out** F-I4.6. **P1** (FlashCHORD 2 s settle: drift <= 1 cm,
    tilt <= 5 deg, relative sink <= 4 mm, no NaN, no fall-through) remains the Embodiment session's
    `jitter_check --k 16` on the delivered folder (F-I2.12, A3 of F-I3.3); the plain-MuJoCo pre-check is reported and
    does not decide. Expected [H]: with an unslotted default that already interpenetrates at the crossing, the
    "default + 1 mm" clause leaves the +-n and +d bounds of P2 loose (the default's travel there is the 60 mm search
    cap); the slot's clearance is fixed by construction (F-I4.5), and P3 and P7 are the binding geometric tests.
    Reported, never deciding: the carved travel in absolute mm in all 26 directions.
  - **F-I4.8 Delivery (simulator copy only).** If every test of F-I4.7 except P1 passes: a new round folder in the
    Embodiment layout (INTERLOCK 6.1, F-I3.9): `<obj>/<obj>.glb` = the submitted mesh, unchanged; `<obj>/piece_XX.obj`
    = the slotted plate pieces; `inertia.json`; `carve.json`; `_fit/<obj>.glb`; `props_gmg.json` (the 0.3 kg
    placeholder, D-I1 open); `manifest.json` gmg-sim/2 with an `owner_waiver` block (F-I4, the quote, the slot geometry
    and checks) and `p1_pending: true`; `sources/`; the unslotted plate pieces under `_default/`. **This amends F-I2.12
    for this route only:** the slotted pieces sit at the top level because the P1 test (their jitter_check) reads a
    round folder; no pack may use the folder until their report passes P1 for it; a P1 failure marks it do-not-use
    (the F-I3.8 mechanism). If any other test fails, the folder is still written for the record, with
    `DO_NOT_USE.json` naming the failing test, and nothing is offered. A new tag per run; never overwritten. The
    submitted (CD-O) board mesh is unchanged.
  - **F-I4.9 Integrity.** Inputs: our clean bundle (owned points, grids, tracks, census, identity flags), our picks,
    and our video for source (b), which is reported only. GT-free: no scan, mocap, dataset-parquet `pose`, `*_align`,
    or library_v1..v4 geometry as shape evidence (library meshes may set ROI boxes as before). `meshes/carve/ev25` and
    every other library-based slot mesh are never read. The 29 Oct SAM 3D board meshes (library-seeded crops, dev only)
    are not passed to F-I4 runs (`--gen` omitted): source (a) cannot change a simulator decision, and no submission is
    made. Public development (ep24) and eval inference (eval 25) stay separate. Nothing is tuned on eval. Eval 25 later
    runs the identical code with P_sim = the packed eval-25 reference (F-I1.1). A failed acceptance is reported; any
    fix after it is a new dated F entry labelled post hoc.
  - **F-I4.10 Pre-registered tests and predictions (written before any run).** T-I1 additions (synthetic,
    `tests/test_interlock.py`; the synthetic owned points get camera centres on both faces of each plate so that a
    plane pair can exist):
    - **w1** s0 cross without a silhouette, t = 6, 10, 18 mm, waiver on: both plates CARVE (simulator only, tier T1,
      `submitted` False); |w - (t + 2 mm)| <= 1.0 mm; |c_L - the true slot centre| <= 2.0 mm;
      |D_A + D_B - W_x| <= 10 mm; three box pieces per plate; keep-out <= 0.3 cm3 per hull;
    - **w2** waiver off: every existing T-I1 decision is unchanged;
    - **w3** waiver on, unchanged decisions: n9 cup nesting (no plane pair), n2 resting pose error (not INSERTION),
      n4 short contact (TRANSIENT), and a plate whose partner is a cylinder (not plate-like);
    - **w4** waiver on, o2a and o2b (11 mm overshoot along d): nothing carved (budget (iv) or
      `interlock_slot_inconsistent`);
    - **w5** P3 on w1 at t = 10 mm (16 copies): carved lag <= 0.5 cm and <= 5 deg.
    Predictions (E additions; the T-I11 run is clean ep24 with eval semantics):
    - P35 both ep24 boards are plate-like, with t inside 5-10 mm (the video slot is about 6-8 mm [E]) | no plane pair
      on either board, or t outside 5-10 mm | [H]
    - P36 the waiver route decides CARVE on both boards and |D_1 + D_2 - W_x| <= 10 mm | PUSH, or
      `interlock_slot_inconsistent` | [H]
    - P37 the slotted pieces pass the keep-out gate (<= 0.3 cm3 per hull) | any hull over | [H, near-certain by
      construction]
    - P38 P2-P7 pass on 16 copies, with P3 carved <= 0.5 cm and <= 5 deg (the DIAG motion-band slot gave 0.33 cm /
      9.4 deg) | any fails | [H]
    - P39 (only if run) ep2 pot + lid and ep11 cups: decisions unchanged (no plane pair) | any carve under the waiver
      | [H]
    These tests gate or fix steps; none is a failure criterion of the gmg (D.3).
  - **F-I4.11 Constants and origins.** Width clearance 2 x 1.0 mm: **informed** (F-I1.14). Depth margin 2.0 mm:
    **generic** (the same clearance at the slot bottom; fixed in the task text before any F-I4 run). Consistency window
    10 mm: **generic** (= K-c). Outline: 2 mm raster (= the carve sub-grid), >= 3 frames per cell (= OBSERVED hits
    >= 3, A.6), slab margin 3 sigma (A.6 noise band), rectangle fill share 0.9: **generic**. The 6 mm point filter:
    carried over from F-I2.10. The 3 mm extension: the existing `carve_solid` value. Plane-pair window 3-25 mm:
    **informed** (A.6); parallel 30 deg and overlap 0.5: **generic** (structure.py). Every acceptance threshold: as in
    F-I1.14.

- **2026-10-31, F-I4.12 (post hoc): slot centre from the partner's plate body, not from the component's voxel
  centroid.** Written 16:55 UTC after the first synthetic w1 probe of the F-I4 build and committed and pushed **before
  T-I11 (ep24) or any other real-data run with F-I4**; no real-data F-I4 number exists when it is committed. Labelled
  post hoc: it changes F-I4.3 after a pre-registered test (F-I4.10 w1) missed. Measured [M, synthetic, T-I1 cross,
  t = 10 mm, two-sided cameras, waiver on; probe `<scratch>/interlock/fi4/probe_w.py`, 4 copies]: the F-I4.3 centre
  (the unweighted 4 mm voxel centroid of the linked component along a_L) lies **2.76 mm (A) and -2.81 mm (B)** from
  the true slot centre (w1 tolerance 2.0 mm: **w1 fails**). Cause: the partner's OBSERVED evidence voxels sit
  asymmetrically about its mid plane in its own 4 mm grid, and the component's 4 mm voxels quantise again. Effect:
  the slotted plates overlap by **2.69 cm3** at the assembled frames, so P3's restored overlap clause (< 1.0 cm3) fails
  while its lag passes (0.22 cm / 0.5 deg); P2, P4, P6, P7 and the keep-out gate (0.0 cm3 per hull) pass. Other
  w1 quantities in the same probe: plate thickness 10.17 / 10.12 mm (true 10), slot width 12.12 / 12.17 mm, depth sum
  137.75 mm against W_x 134.02 mm (difference 3.7 mm), plate bodies 238.4 x 133.4 mm (true 230 x 125: the outline
  rectangle over 2 mm cells and 1 mm noise is about 4 mm larger on each side [M]).
  **Change:** c_L = the coordinate along a_L, in o's mid plane at the middle of the slot's depth range, at which the
  **partner's plate mid plane** (F-I4.1 mid_n, mid_d of p, mapped into o by the median assembled relative pose T_op of
  F-I4.3) crosses the slot's centre line. The slot then holds the partner's simulator body (its plate of thickness
  t_p) at the replayed assembled pose with the pre-registered 1 mm clearance on each side. The component centroid is
  still computed, used for the split-plane cap of the depth (F-I4.3, unchanged), and reported (`c_L_component_mm`,
  `c_L_shift_mm`); if the mapped partner normal is perpendicular to a_L (|n' . a_L| < 1e-6, a numerical guard) the
  centroid is used and flagged. **Nothing else changes:** no threshold, width, depth, entry side, budget, consistency
  window, pieces or acceptance test. The same code serves the synthetic tests and T-I11. Evidence it uses: our tracks
  (the pose) and the partner's owned points (its mid plane), both GT-free.
  [H] Falsified if w1 still misses the 2.0 mm centre tolerance at t = 6, 10 or 18 mm, or if the carved overlap at the
  assembled frames of the synthetic cross stays >= 1.0 cm3. Known limit [H]: the centre now follows the tracks at the
  assembled frames; a track error there moves the slot with it, which P6 / P7 (other frames) can expose.

- **2026-10-31, F-I4.13: T-I1 w1-w5 outcomes before T-I11 (no rule change).** Synthetic, code = F-I4 + F-I4.12, run
  17:00-17:15 UTC on this container [M]: w1 at t = 10, 13, 18 mm passes (CARVE T1, not submitted; plate thickness
  10.17/10.12, 13.43/13.34, 18.12/18.12 mm; width within 0.2 mm of t + 2; centre within 0.1 mm of the true slot, the
  F-I4.3 component centroid would have been 0.76-2.81 mm off; 3 pieces; keep-out 0.0 cm3 per hull; depth sum - W_x =
  2.6-4.3 mm). **Known miss at t = 6 mm (pre-registered w1 width tolerance):** the plane-pair thickness reads
  7.24 / 7.30 mm, so the slot is 9.30 / 9.24 mm wide against 8 +- 1 mm (everything else at t = 6 passes). Kept as an
  expected failure (`test_w1_t6_width_known_miss`); the thickness code is not changed. Implication for ep24 [H]: if the
  boards are about 6 mm thick, t and the slot may read about 1.2 mm too wide (more clearance; P2 does not bound it,
  the "default + 1 mm" clause being loose). **t = 25 mm (build-task extra, at the slab window's upper end):** no plane
  pair, out of scope, the old decision (PUSH) stands; reported, not a w1 case. w2 (waiver off unchanged, also on the
  two-sided bundles), w3 (n2, n4, n9 identical with the waiver on; a plate with a 30 mm cylinder partner unchanged;
  reported only: a 16 mm rod is not plate-like either), w4 (o2a and o2b: both PUSH with `interlock_slot_inconsistent`,
  depth sum - W_x = 22.0 mm) and w5 (t = 10 mm, 16 copies: carved lag 0.033 cm / 0.16 deg, overlap at the assembled
  frames 0.0 cm3; default 6.07 cm / 91 deg; P2-P7 pass) pass. Controls n2-n5, n9 pass with the waiver off.

## Revision 1 changelog

What changed, and why:
- **Freeze (F1).** v1 was never committed. This revision is committed and pushed before any gmg code, with both
  hashes recorded. The requested 09:40Z freeze time was not used because it predates the file (header).
- **Thickness (F3).** The default 2.5 mm equals the scan rack wall median leaked by a brief. It is replaced by t0,
  fitted on our own public observations, with a labelled fallback and extra R1 items if it cannot be fitted (A.1,
  C.3).
- **V3 (F4).** τ = 0.20 had scored best against existing scan regret. τ is now the 99th percentile of a GT-free null
  from the CPU fold rebuilds (A.3). The X0 pot-with-lid requirement, which could not fail, is removed (B.1).
- **Eval inspection (F5).** The eval-track analyses are added to "already seen"; no constant depends on them; the
  contact constants are justified generically (A.6).
- **V2 (F6).** Sample-based with a noise-scaled band and a normal-side clause; no interface exclusion zone; synthetic
  tests pre-registered (A.2, A.3, B.14).
- **Spoon and contact subset (F9).** Contact-subset adoption guard for the pot and the blue cup (D.1).
- **Similar views (F10).** One view × seeds; Pixal3D-MV only with ≥ 3 views; K-c and K-d count only testable
  objects; dust pan ep40 added to G1 (B.9).
- **B.2 (F11).** Reference from 3-D-separated frames, minimum 10 frames, testable pairs only; ep18 pair added.
- **Proxy X (F12).** GT-free registration replaces the shared library_v2 frame; X-check pre-registered (A.7, B.13).
- **Build order (F14).** M9 CPU check (B.11) and the G0 probe (B.12) come early.
- **Fallbacks and identity (F15).** `m_o` counts TRACK_FAIL and reused meshes; the ADD guard excludes undefined frames;
  identity tests pre-registered (D.1, B.15).
- **Other.** Informed constants labelled in A.6 (class order, track tests, part vocabulary, extent table, ball seed
  count, K-a threshold); the P-PROG extent table frozen (A.6b); markers count for V5 only when trusted (A.3, B.4);
  generator hold-out by view similarity and a moving-block bootstrap (A.2, A.4); the X0 successor menu fixed (B.1);
  the spoon defaults to the owner (D.4); D.2 names all scan-informed choices; the beige cup is pre-labelled
  low-confidence; an inconclusive zone is defined.
