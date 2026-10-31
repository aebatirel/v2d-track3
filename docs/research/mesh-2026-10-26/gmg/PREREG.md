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
  centroid.** Written 16:33 UTC after the first synthetic w1 probe of the F-I4 build (16:26-16:32) and committed and pushed (94eed1c, 16:35 UTC) **before
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
  16:38-16:50 UTC on this container [M]: w1 at t = 10, 13, 18 mm passes (CARVE T1, not submitted; plate thickness
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

- **2026-10-31, F-I4.14 (post hoc): plate test that works on real plates (camera-side face pair; one-face plate with
  the partner's thickness).** Written 17:03-17:06 UTC (pushed in dad65a1 at 17:06 UTC; the first text said 17:10-17:20, a guessed time, corrected) after T-I11 (tag `fi4evalsem`, code cd2383f, 16:51-16:58 UTC)
  found **no plane pair on either ep24 board** (F-I4.1 `no_plane_pair`), so the waiver never engaged and both boards
  were PUSHED again. Committed and pushed **before** any run that uses it. Labelled post hoc: it changes F-I4.1 after a
  real-data scope failure (not an acceptance failure). Decided from the GT-free diagnosis below only; no slot
  geometry or physics outcome exists for ep24 under F-I4 (the pair never entered the route), and none was looked at.
  - **Diagnosis [M]** (`<scratch>/interlock/fi4/diag14/diag_plane.py` / `.json`; our clean bundle's owned points within
    6 mm of the pick, their camera centres and frames, the object-episode sigma, our pick; nothing else). Board 1:
    sigma 3.0 mm, so the segment_planes inlier band is 3 sigma = 9.0 mm. **Both faces are seen**: 42 % of the points from
    the +n side (38 frames), 58 % from the -n side (101 frames); per-frame median offsets along the thinnest axis
    +3.88 mm (MAD 0.45) and -3.16 mm (MAD 0.32), i.e. faces about 7.0 mm apart, track jitter along n under 0.5 mm,
    within-frame IQR 1.75 mm. The 9 mm band merges both faces into **one** plane (26,022 points, two-sided share 0.49,
    rms 3.7 mm, offset 0.3 mm = the middle), so no pair can form. Cause: the inflated sigma (the B7 bundle had 1.21 mm
    for this object-episode), not missing faces. Board 2: sigma 0.74 mm; **one face only** (0 % of points from the +n
    side; all 117 frames see the -n face); segment_planes returns 4 parallel planes all seen from the same side
    (offsets -2.5 / 0 / +2.3 / +3.0 mm); 1-99 % extent along n 12.65 mm (the 1 % tail at -9.3 mm lies on the camera
    side: a bump; 5-95 % 4.6 mm). Its thickness is not observable two-sided in this episode, and the 1-99 % extent of
    one face (and the 12.6 mm w_sub, which is the same kind of extent at the crossing) measures face noise plus
    protrusions, not thickness.
  - **Change (F-I4.1 extended; tried in this order, the first that holds decides):**
    1. **F-I4.1 plane pair, unchanged** (so every synthetic w1-w5 result where it held stays as it was).
    2. **Camera-side face pair.** Same input as F-I4.1 (the 2 mm downsampled owned points within 6 mm of the pick,
       with their camera centres and frames). Reference plane = the largest plane of the F-I4.1 segmentation (normal
       a, oriented to its cameras; offset d_a). Slab = points with |a . x - d_a| <= 25 mm (the slab window's upper end,
       A.6). Split the slab points by the side their camera is on: S+ = (c - x) . a > 0, S- = (c - x) . a < 0. Each side
       is a face if it holds >= 300 points (plane_min) from >= 3 frames. Each face: PCA plane (normal oriented to its
       cameras), offset m+- = median of a . x over its points (robust to the merged band), rms about its own plane.
       Plate if all hold: (i) the two face normals antiparallel within 30 deg (plane_deg); (ii) material between them:
       t = m+ - m- > 0 (the face seen from +a lies further along +a); (iii) t in the slab window 3-25 mm; (iv) footprint
       overlap >= 0.5 (the 2-98 % boxes, as structure._planes); (v) each face's rms <= 3 sigma (the plane inlier band);
       (vi) **plate-like extents**: both in-plane 2-98 % extents of the slab points >= 2 w with w = t + 2 mm (the
       carve_solid plate-like test: both other extents >= 2 w). Thickness t, mid plane (a, (m+ + m-) / 2), outline axes
       from the reference plane. Flag `plate_pair_camera_side`.
    3. **One-face plate.** If one side holds >= 300 points from >= 3 frames and the other does not, and the 1-99 %
       extent of the slab points along a is <= 25 mm (thin-extent test, slab window upper end), the object is a
       one-face plate candidate. Its thickness is **not measured**: t := the **partner's** thickness when the partner
       is a two-sided plate by step 1 or 2 (prior [E]: the two boards of a cross-lap / halving joint are taken to be
       the same stock; flag `plate_t_partner_prior`). Mid plane = the seen face (median a . x of the seen side) moved by
       t / 2 away from its cameras. Test (vi) then applies with this t. If the partner has no measured thickness either,
       the object is not plate-like (`one_face_no_partner_t`) and the pair is out of scope (old decision).
    Not used for t, as before: w_sub, the 1-99 % extent of one face, thickness.py, any library mesh, any other
    episode's measurement (eval semantics: one episode at a time).
  - **Nothing else changes:** F-I4.2 body (outline at t about the mid plane), F-I4.3-F-I4.12 slot, budget, pieces,
    acceptance thresholds, delivery and integrity rules. Constants reused, none new: plane_min 300, plane_deg 30,
    slab window 3-25 mm (informed, A.6), overlap 0.5, band 3 sigma, >= 3 frames (generic), plate-like 2 w (generic,
    carve_solid). The partner-thickness prior is a modelling assumption [E], labelled as such in the records.
  - **Tests (synthetic T-I1, re-run before T-I11):** w1-w5 re-run unchanged (expected identical: step 1 holds there;
    t = 25 mm may now enter by step 2, which is reported and then checked like any other w1 thickness). New: **w6**
    (t = 10 mm, two-sided, object-episode sigma set to 3.0 mm so the F-I4.1 band merges the faces): plate by step 2,
    |t - 10| <= 1 mm, CARVE both, w1 checks; **w7** (t = 10 mm, B's -z face removed from its evidence so B is one-face):
    B plate by step 3 with t = A's t, CARVE both, w1 checks. w3 rods and cylinder reported as before (the cylinder
    must stay out of scope).
  - **Predictions for T-I11 re-run (tag `fi4b`, clean ep24, eval semantics, --waiver-fi4, physics 16 copies) [E]:**
    P40 board 1 plate by step 2 with t in 5-9 mm; board 2 plate by step 3 with t = board 1's t. Then P36-P38 apply as
    written (CARVE both and the depth-sum check passes; keep-out passes; P2-P7 pass with P3 <= 0.5 cm / 5 deg). If any
    acceptance test fails, the failure is reported with its numbers and nothing is tuned.
  - [H] Falsified if w6 does not recover t within 1 mm, if w7 does not carve, if the 30 mm cylinder of w3 becomes plate
    -like, or if on ep24 step 2 does not hold for board 1. Known limit: board 2's slot in board 1 is sized by a prior
    (board 2 = board 1's stock), not by a measurement; the depth of each slot is a prior as before (F-I4.3).
  - **Outcomes (17:08-17:35 UTC, no rule change; code 9ad1af9) [M].** Synthetic T-I1 Waiver + Controls re-run (14
    tests, 1081 s): OK with 3 expected failures. w1 identical to F-I4.13 (t = 6 width known miss; 10 / 13 / 18 pass;
    t = 25 still out of scope, now via `camera_side_two_sided_fail`); w2-w5 and Controls pass (w5 lag 0.033 cm / 0.16
    deg); w3: the 30 mm cylinder and the 16 mm rod stay out of scope. **w6 misses** (expected failure): at t = 10 mm
    with sigma 3 mm the synthetic faces are not merged, step 1 still holds and reads 8.07 / 8.39 mm. Step 2 checked
    directly (w6b): 5.81-5.82 / 9.57-9.66 / 17.12 mm for 6 / 10 / 18 mm (0.2-0.9 mm thin), one cell fails the rms check
    (t = 18, sigma 1). **w7 passes** (one-face B, t from A, CARVE both, widths 12.17 mm, centres <= 0.21 mm). The first
    w7 fixture kept B's edge points (float32 view along z of either sign) and made B 'two-sided'; corrected in the test
    only. **T-I11 re-run (tag fi4b, 914 s):** board 1 plate by step 2, t = 6.21 mm; board 2 plate by step 3, t := 6.21
    mm (P40 holds); in scope; sweep 1.0 / 1.0, push 19.0 / 22.0 mm pass; **F-I4.2 then fails on both boards**:
    min-area-rectangle fill 0.895 / 0.868 < 0.9 (`plate_outline_not_rectangular`; rectangles 234.5 x 142.3 / 231.1 x
    142.0 mm; the filled outline's 2-98 % extents are 220 x 124 / 216 x 124 mm: the outline flares by about 9 mm per side
    at the ends of the long axis, which sets the rectangle's width). Both boards stay PUSH; no slot, no physics, no
    F-I4 delivery. Stopped here: this step allowed one post-hoc entry (this one), so nothing is changed after the
    failure. [H] for the next decision (not adopted): a body that does not let end flares set the width (e.g. the
    rectangle of the 2-98 % outline, or fill measured on the 2-98 % box) would pass; it needs its own dated entry.
  - **Correction of the outcomes above (2026-10-31, 17:54 UTC, after `build/I/verify_slot_0.md` and
    `build/I/verify_slot_1.md`; record only: no rule, threshold or code changed, nothing run).**
    (a) **Cause of the F-I4.2 failure [M, verify_slot_1 B1]:** the "flares" are the boards' real I-shape (ends wider
    than the waist), not marker balls or bumps. The flare points lie in the face planes, none is within 30 mm of our
    hand joints in the same frame or within 3 mm of our table plane, they come from 138 / 81 frames, the committed RGB
    frames (`build/I/png/sil_ep24_b1.png`, `sil_ep24_b2.png`) show stepped wider ends, and inside the 2-98 % box the
    mask fills 0.996 / 0.983 (waist 130 / 125 mm, ends 137 / 136 mm, raster growth included; the parts at least 8 mm
    wider than the waist run 22 / 6 mm and 16 / 20 mm along the length at the two ends). The
    [H] above is **withdrawn**: the 2-98 % rectangle would cut off real wood, and the rectangle at the full end width
    puts 11.5 % / 9.9 % of its volume (22.9 / 19.5 cm3) in FREE voxels (the F-I4.2 "reported, not used" quantity), so
    P37 ("keep-out met by construction") cannot hold for these boards with any one-rectangle body [E: keep-out gate
    not run]. A body that follows the outline is a rule change and needs its own dated post-hoc entry; none is made here.
    (b) **Board-1 thickness [M, verify_slot_1 B2]:** t = 6.21 mm is the step-2 estimate on the 2 mm first-point-per-voxel
    downsample, as this entry specifies. The same camera-side split on all 1.76 M near points reads 7.40 mm (median of
    per-frame face medians 7.30 mm, interior points 7.35 mm). The two faces are seen in disjoint frame ranges (+ face
    frames 0-74, - face frames 74-274, one frame in common), so t is a cross-phase number (about +-1 mm [E]). Board 2's
    prior inherits 6.21 mm. P40 holds either way.
    (c) **Falsifier and prediction status [M, verify_slot_0 N1 / N4]:** the falsifier "w6 does not recover t within
    1 mm" **fired** (8.07 / 8.39 mm for 10 mm). w6 never reached step 2 (its faces did not merge), so it shows that the
    unchanged step 1 reads up to about 2 mm thin at sigma 3 mm; the step-2 estimator is checked by w6b. Predictions:
    P35 failed (fi4evalsem, no plane pair), P36 failed (F-I4.2 in fi4b), P37 and P38 not tested (no slot), P40 holds
    but is not independent (written after diag14 had measured the faces about 7 mm apart with the same split).

- **2026-10-31, F-I4.15 (post hoc): the plate body follows the observed outline (polygon prisms), and t comes from
  all points.** Written 18:00-18:14 UTC (pushed in f62454a, committed 18:14:55 UTC) from the orchestrator's decision (31 Oct, ~18:05 UTC as it states; F-I4.15.0) and
  committed and pushed **before any code or run uses it**. Placed with the F-I4 entries; in time it follows F-I5
  (17:34 UTC). Still before any gmg scoring round (zero gmg scan scorings exist; no scan number was read for this
  entry). Labelled **post hoc**: it replaces the F-I4.2 body, the F-I4.6 pieces and the thickness estimate of F-I4.1 /
  F-I4.14 after T-I11 `fi4b` failed F-I4.2 on both ep24 boards and after the verifiers' GT-free diagnosis
  (`build/I/verify_slot_1.md` B1-B3, `build/I/verify_slot_0.md` N1, N5). When it is committed no slot, slotted piece or
  physics result under F-I4 exists for any real episode (fi4b built none), and none was looked at. The real-data
  numbers it rests on are listed under "Evidence". **Forking path, stated plainly** (verify_slot_0 N5): F-I4.12 (after
  the synthetic w1 miss), F-I4.14 (after `no_plane_pair` on ep24) and this entry (after the F-I4.2 failure on ep24)
  each changed the route after an outcome, and each made it more permissive. This one was decided by the orchestrator
  from the measured cause of the failure (the boards' shape), not from a slot or physics outcome. It is checked on a
  second public plate episode (ep23) and frozen before eval 25 (F-I4.15.6). Where F-I4 to F-I4.14 and this entry
  differ, this entry wins for runs with code that implements it (records carry `fi4_rev: 15`). The F-I4.14 route (the
  rectangle body) stays reproducible from commit 9ad1af9. Design text for the owner: `INTERLOCK.md` section 20.10.
  - **F-I4.15.0 The decision (orchestrator, 31 Oct ~18:05 UTC, post hoc), as written in the task text:** "(1) plate
    body = the observed outline polygon (the same 2 mm raster, >= 3 frames per cell, one closing, holes filled, largest
    component), simplified (state the tolerance, generic, e.g. 1 mm) and extruded at thickness t; pieces = a convex
    decomposition of that polygon into prisms (state the method and cap), minus the analytic slot box, plus marker-ball
    hulls if the body carries balls; the keep-out gate decides, unchanged; (2) thickness t from the step-2 face
    estimator on ALL owned points within the filter (not the 2 mm downsample), justified by the fired w6 falsifier;
    (3) everything else in F-I4 unchanged (slot width t_partner + 2 mm, centre F-I4.12, depth F-I4.3, consistency,
    budget, P2-P7 acceptance, delivery with p1_pending); (4) a second public plate episode (ep23) is run for the plate
    test and body only (its board-2 track is known to be the wrong board: report, no adoption) before the rule is
    frozen for eval 25." The owner's waivers (F-I4.0, F-I5.0) are unchanged. Point (3) keeps F-I4.14 steps 2-3 as
    written. The decision does not otherwise answer verify_slot_0 N2 (the plate-like scope widened by F-I4.14), which
    therefore stands as labelled there.
  - **Evidence [M]** (GT-free; public ep24, dev, eval semantics; clean bundle `20261031-b4ext4-b61e8aa`):
    - (a) fi4b (code 9ad1af9): F-I4.2 failed on both boards. Fill of the min-area rectangle 0.895 / 0.868 < 0.9;
      rectangles 234.5 x 142.3 / 231.1 x 142.0 mm.
    - (b) verify_slot_1 B1: the boards are I-shaped. The outline mask is 130 / 125 mm wide at 30-70 % of the length and
      137 / 136 mm in the outer 10 % (raster growth included). The parts at least 8 mm wider than the waist run 22 / 6 mm
      and 16 / 20 mm along the length. Seen in our RGB frames; the flare points lie in the face planes, away from our
      hands and table. The mask fills 0.996 / 0.983 of its 2-98 % box. The full-width rectangle holds 22.9 / 19.5 cm3
      (11.5 % / 9.9 %) in FREE voxels; a waist-width rectangle cuts the lugs off.
    - (c) verify_slot_1 B2: board-1 t = 6.21 mm from step 2 on the 2 mm first-point-per-voxel downsample (36,675
      points). The same camera-side split on all 1.76 M near points reads 7.40 mm (median of per-frame face medians
      7.30 mm, interior points 7.35 mm). The two faces are seen in disjoint frame ranges (0-74 and 74-274).
    - (d) the F-I4.14 falsifier "w6 does not recover t within 1 mm" fired: step 1 read 8.07 / 8.39 mm for a true
      10 mm at sigma 3 mm (on the downsample); step 2 on the downsample read 0.2-0.9 mm thin (w6b).
  - **F-I4.15.1 Thickness and mid plane from all points** (replaces the t estimate of F-I4.1 / F-I4.14; the plate-like
    TESTS are unchanged).
    - The tests that make an object plate-like stay on the 2 mm downsample, exactly as F-I4.1 and F-I4.14 state: the
      plane pair (step 1), the camera-side checks (i)-(vi) (step 2), the one-face thin-extent test (step 3).
    - For a plate by step 1 or step 2, **t and the mid plane are re-estimated** by the step-2 estimator on **all** its
      owned points within 6 mm of the pick (the F-I2.10 filter, `_near_points`: no downsample, no cap):
      - reference normal a and offset d_ref: the decided plane pair's mid_n, mid_d (step 1), or the reference plane's
        normal and offset (step 2, as in F-I4.14);
      - slab: points with |a . x - d_ref| <= 25 mm;
      - S+ / S-: the slab points whose camera lies on the + / - side, (c - x) . a > 0 / < 0;
      - m+ and m-: the medians of a . x over S+ and S-; **t = m+ - m-**; mid plane (a, (m+ + m-) / 2).
    - Checks on this estimate: each side holds >= 300 points from >= 3 frames, t > 0, and t is in 3-25 mm. If one
      fails, the object is not plate-like (`t_all_points_fail`) and the pair leaves the route (old decision).
    - One-face plate (step 3): t := the partner's all-point t (same-stock prior [E], flag `plate_t_partner_prior`,
      unchanged). Mid plane = the median a . x of the seen side over all near points in the slab, moved t / 2 away from
      its cameras. The step-3 tests are unchanged; its plate-extent test (both in-plane extents >= 2 (t + 2 mm)) uses
      this t.
    - Reported per plate: the downsample t (as F-I4.1 / F-I4.14 compute it), the all-point t, the 5 / 50 / 95 %
      per-frame face medians, and each face's frame range.
    - This t sets the body thickness (F-I4.15.2), the partner's slot width w = t + 2 mm (F-I4.3, F-I4.5) and the
      outline slab (t / 2 + 3 sigma).
    - Reason: evidence (c) and (d). Expected [M, not independent]: board 1 about 7.4 mm (verify_slot_1 computed this
      split on all points before this entry). Board 2 inherits it.
  - **F-I4.15.2 Body: the observed outline polygon** (replaces F-I4.2's rectangle body).
    - Input: the object's near points (all of them, as F-I4.2 already used) with |mid_n . x - mid_d| <= t / 2 +
      3 sigma, with the F-I4.15.1 t and mid plane, and their frames.
    - (a) **Frame** (F-I4.2 code, unchanged): the raster in the reference plane's (e1, e2) (2 mm cells, >= 3 distinct
      frames per cell, one 3 x 3 closing, holes filled, the largest 8-connected component) and its minimum-area
      rectangle over the cell corners give a_L (long axis), a_W, a_T = mid_n, the centre c0, L and W. The rectangle is
      no longer the body: its fill is reported, and the 0.9 fill gate goes with the rectangle body.
    - (b) **Outline raster**: the same points rasterised again at 2 mm along (a_L, a_W), with cell edges on the
      rectangle's sides and the same cell rules (>= 3 distinct frames per cell, one 3 x 3 closing, holes filled, the
      largest 8-connected component). The pitch and the cell rules are F-I4.2's ("the same 2 mm raster" of the
      decision); only the orientation follows the rectangle. Reason, stated before any run: a board's straight edges
      parallel to its rectangle then lie on raster lines, so the outline is rectilinear where the board is. In a raster
      laid at an angle, every 2 mm step of a slanted edge survives a 1 mm simplification as a reflex vertex and adds
      pieces.
    - (c) **Polygon**: the outer boundary of the union of the component's cells (a closed rectilinear ring through cell
      corners), with collinear vertices removed. Then **Douglas-Peucker simplification at 1.0 mm** on the closed ring,
      split at the two ring vertices farthest apart.
      - The result must be a simple polygon (no self-intersection, no self-touching).
      - If it is not, the unsimplified ring is used (flag `outline_unsimplified`).
      - If that is not simple either (cells touching only at a corner), the body fails with
        `plate_outline_not_simple`, and the pair leaves the route (old decision; `waiver_gate_fail:<gate>`, F-I4.0).
    - (d) **Body** = the polygon extruded to +-t / 2 about the mid plane (a prism along a_T). The outline body carries
      no marker balls (flag `plate_body_no_markers`, as in F-I4.2): the balls stand on the face inside the outline
      [M, verify_slot_1 B1 item 2], so they do not change the polygon. A STRUCT plate candidate, if one ever exists, is
      still the body (F-I4.2, first sentence, unchanged); none exists.
    - (e) **Reported, not used**:
      - the polygon's area against the component's cell area;
      - its widths along a_W at 30-70 % of its length and in the outer 10 % (the I-shape);
      - its vertex and reflex-vertex counts;
      - the **FREE share**: the share of 2 mm grid points inside the body whose voxel in the object's grid is FREE
        (the F-I4.2 "reported, not used" quantity). It is computed by the same code for the polygon body and for the
        full rectangle body at the same t.
    - Known limit [M, w1]: the outline raster grows the body by about 4 mm per side (w1: 238.4 x 133.4 mm for a true
      230 x 125 mm). The decision does not erode the outline, and neither does this entry.
  - **F-I4.15.3 The slot on a polygon body.** F-I4.3 (width t_p + 2 mm; depth = the partner's 99th-percentile
    penetration + 2 mm, with the split cap; through the full thickness + 3 mm on each side), F-I4.12 (the centre) and
    the F-I4.4 thresholds are unchanged in substance. On a polygon they read as follows:
    - **Frame, d, entry side s_e (the -d side), c_L**: computed as now in the rectangle frame of F-I4.15.2 (a). c_L
      follows F-I4.12, at the middle of the rectangle-based depth range.
    - **Slot bottom b** (position along a_W): as now. b = u_rect - s_e (P + 2 mm), with u_rect = s_e W / 2 the
      rectangle's entry edge and P the 99th-percentile penetration measured from it, capped at the split plane. b is
      the deepest partner sample (or the split plane) plus 2 mm, so it does not depend on the edge that depth is
      measured from.
    - **Entry edge u_e**: the polygon's outermost coordinate along s_e a_W inside the slot band |u_L - c_L| <= w / 2.
      This is the polygon's edge at the slot's mouth: the waist edge on an I-shaped board.
    - **D = s_e (u_e - b)**, and P = D - 2 mm. Both are measured from u_e. They are the D and P that are reported and
      used in the cross-lap check and the budget.
    - **Slot box**: along a_L, c_L +- w / 2; along a_W, from u_rect + s_e 3 mm (outside every polygon edge) to b;
      along a_T, +-(t / 2 + 3 mm).
    - **W_x**: as F-I4.3. Points of the 2 mm grid inside both unslotted polygon bodies at the median assembled relative
      pose; W_x = their extent along d. The pair passes if |D_o + D_p - W_x| <= 10 mm (window unchanged).
    - **Budget (F-I4.4, thresholds unchanged)**:
      - volume share = area(slot footprint intersected with the polygon) / area(polygon), cumulative against the
        round-0 polygon body, <= 10 % (the slot spans the full thickness);
      - reach = extent along d of (slot box intersected with the body) / extent along d of the body, <= 0.6;
      - topology: the slotted polygon (the polygon minus the slot footprint) is one simple polygon without holes; the
        bottom b lies inside the polygon (D is smaller than the polygon's extent along a_W on the slot centre line);
        and there is polygon material on both sides of the slot band between u_e and b (both prongs have positive
        area).
    - Why D is measured from the polygon edge (stated before any run): the cross-lap check compares D_o + D_p with
      W_x, and W_x of two polygon bodies is set by their widths at the crossing (the waists). Measured from the
      rectangle edges, the sum would grow by about (142.3 - 130) / 2 + (142.0 - 125) / 2 = 15 mm on ep24 [E, from the
      fi4b rectangles and the verify_slot_1 waists]: more than the whole 10 mm window.
    - c_L is not recomputed with the polygon-based depth range. The difference is the partner's tilt against a_L times
      half the edge shift, about tan(2 deg) x 4 mm = 0.15 mm [E, arithmetic with verify_slot_1 B3's 2.1 / 1.5 deg].
  - **F-I4.15.4 Pieces** (replaces F-I4.6's three boxes; the keep-out gate is unchanged).
    - **Slotted pieces**: an exact convex partition of the slotted polygon (the polygon minus the slot footprint,
      which is the slot box's section in the mid plane), each part extruded to +-t / 2 into a convex prism. **Default
      pieces** (for P2-P7 and `_default/`): the same partition of the unslotted polygon. The box is subtracted in 2-D
      before the partition, not from each prism, so that every piece is convex and the union is exact (a prism notched
      by the box is not convex). This is the decision's "convex decomposition of that polygon into prisms, minus the
      analytic slot box", in the order that keeps the pieces convex.
    - **Method** (deterministic):
      - ear-clipping triangulation of the simple polygon: counter-clockwise ring, collinear vertices removed first;
        ears taken in ring order starting from the lowest-index vertex; an ear is a strictly convex vertex whose
        triangle contains no other ring vertex;
      - then **Hertel-Mehlhorn merging**: the internal diagonals are visited longest first (ties by vertex indices),
        and one is removed when both of its endpoints stay convex (interior angle <= 180 deg) in the merged part.
      - Guarantee: at most four times the minimum number of convex parts (Hertel and Mehlhorn 1983; the same algorithm
        as CGAL's `approx_convex_partition_2`, doc.cgal.org Partition_2, read 31 Oct).
    - **Vertex limit**: a part with more than 32 vertices (a prism over 64 vertices, the MuJoCo limit of F-I1.14) is
      split by the diagonal from its vertex 0 to its vertex floor(k / 2), repeatedly, until every part has <= 32.
    - **Cap**: at most floor(165 / objects in the episode) prisms per body (82 on ep24), for the slotted set and for
      the default set. This is F-I5.4's cap, from the P5 limit of 165 shapes per episode. Over the cap, the body fails
      with `plate_body_over_cap` and the pair leaves the route (old decision). There is no ladder of tolerances.
    - **Marker balls**: one icosphere hull (<= 64 vertices) per ball the body carries, as in F-I4.6. The outline body
      carries none.
    - **Keep-out gate**: F-I4.6, unchanged (`platebody.keepout_gate`: the F-I3.8 gate with the F-I1.8 keep-out within
      2 voxels, partner and carve weight 10, <= 0.3 cm3 per hull, else do-not-use). It decides.
    - **What the gate measures [R, code read: `platebody.keepout_gate`, `simpieces.keepout_points`,
      `simpieces.pieces_gate`]**:
      - It counts keep-out points that lie outside every slotted piece (`ins` False) and inside a hull. Pieces that
        tile the body exactly therefore hold 0.0 cm3 by construction, whatever the body's own FREE share. The gate
        checks that the pieces stay inside the body and out of the slot.
      - It cannot see a body that extends into seen-empty space. The F-I4.14 correction (a) and verify_slot_1 B1 (b)
        say a full-width rectangle "would fail" the keep-out gate [E, gate not run]; that does not follow from the
        code, and the correction here is a record correction only.
      - The body's fit to the observed space is the FREE share of F-I4.15.2 (e). It is reported, and tested by
        prediction P53. It is not a gate: the decision keeps the gate unchanged.
  - **F-I4.15.5 Unchanged.**
    - F-I4.0 scope and kept gates; the F-I4.1 / F-I4.14 plate tests.
    - F-I4.3 width, depth rule, split cap and the 3 mm extensions; the F-I4.12 centre; the 10 mm consistency window;
      the F-I4.4 thresholds; F-I4.5 w_sim.
    - F-I4.7 acceptance: P2-P7 on 16 copies with the same thresholds. The default is the unslotted body (now its
      prisms). P4's "slot's volume inside the body" = the slot footprint intersected with the polygon, times t.
    - F-I4.8 delivery: the slotted pieces at the top level, `_default/`, `p1_pending: true`, `DO_NOT_USE.json` naming
      any failing test. The `owner_waiver` block now also holds `fi4_rev: 15`, the polygon in the body frame, the
      tolerance and the piece counts.
    - F-I4.9 integrity.
    - With `--waiver-fi4` off, nothing changes.
    - Interface note for F-I5 (no change to F-I5 here): F-I5.4 route 1 ("F-I4.6 analytic boxes") and the body of a
      plate-like object paired with a non-plate ("its F-I4.2 plate body") refer to F-I4. Under F-I4.15 they read as
      the polygon prisms and the polygon body. The collision-carve workflow records whether its code follows.
  - **F-I4.15.6 Run order, ep23 and the freeze.**
    1. Build in `platebody.py` (new functions; the `--waiver-fi4` route uses F-I4.15) and the tests of F-I4.15.7.
    2. T-I1: w1-w7 re-run, the new w6c, w8, w8b and w9, and the **full** existing T-I1 suite with the waiver off
       (verify_slot_0 N6).
    3. **T-I11 ep24, tag `fi4o`** (new tag; nothing overwritten): the fi4b command with `--tag fi4o`. The code commit
       is recorded at launch (verify_slot_0 N8). P2-P7 run on 16 copies.
    4. **ep23** (public, dev): the plate test (F-I4.1 / F-I4.14 with F-I4.15.1) and the body (F-I4.15.2, its default
       prisms, FREE share) for both boards. No linking, slot, decision or physics.
       - Bundle: run `20261031-b4ext6-90c8cce` (v6). Chosen because the ep23 board 1 of the v4 bundle is the
         guard-clipped crop that B4 round 2 fixed (`build/B4.md`, 14:24-15:07 UTC, before this entry).
       - Picks: `shell_t5p36` for both boards, built for ep23 from that bundle with the producer and constants used for
         ep24 (`manifest_cands_ep24.json`).
       - Board 2's track is the wrong board (orchestrator; B4 identity flags). It is reported and never adopted. If
         board 1 is a one-face plate, its t comes from board 2; this is flagged and reported only.
    5. **Freeze.** F-I4.15 is frozen for eval 25 (code commit recorded; no further F-I4 change before eval 25) when
       both hold:
       - (a) T-I11 `fi4o` CARVEs both ep24 boards and every F-I4.7 test except P1 passes, keep-out included (P52);
       - (b) ep23 board 1 is plate-like (any step) and its F-I4.15 body is built without a gate failure (the first
         part of P57).
       If (a) or (b) fails, the round stops, nothing is tuned, and the failure is reported. Eval 25 is then not run
       under F-I4.15; any change is a new dated entry and an orchestrator decision. Synthetic misses (F-I4.15.7) and
       falsified predictions outside (a)-(b) are reported with their numbers and do not stop the round. This is stated
       now, so that no miss is relabelled afterwards (verify_slot_0 N1).
    6. **Eval 25** (after the freeze only; not a run of this entry): needs the gmg ep25 eval bundle and the per-board
       P_sel -> P_sim mapping check (INTERLOCK 20.9 open item 3; verify_slot_1 N6). Identical code; P_sim = the packed
       eval-25 reference; nothing tuned on eval.
  - **F-I4.15.7 Tests (synthetic T-I1, before T-I11).**
    - **w1-w7 re-run.** w1's "three box pieces per plate" now reads: prisms that tile the slotted polygon exactly (area
      difference <= 1 mm2), within the cap. Every other w1-w5 / w7 threshold is as before. The t = 6 mm width miss and
      t = 25 mm out of scope stay recorded cases; their outcomes may change because t now comes from all points, and
      they are reported either way.
    - **w6c** (the step-2 estimator on all points; replaces w6b, which used the downsample): synthetic two-sided plates
      at t = 6, 10, 18 mm and sigma 1, 3 mm. Pass: |t - true| <= 1.0 mm in every cell.
    - **w8** (I-shaped cross): two plates 230 mm long, 125 mm wide at the waist, 136 mm over 20 mm at each end (the
      ep24 shape in round numbers [M, verify_slot_1 B1]), t = 7 mm, two-sided cameras off the plate planes, sigma
      1 mm, a slot in the waist at mid-length, waiver on. Pass, all of:
      - both CARVE;
      - on both polygons, end width - waist width is within 3 mm of the true 11 mm;
      - D is measured from the waist edge, and |D_A + D_B - W_x| <= 10 mm;
      - w within 1 mm of t + 2 mm; centre within 2 mm of the true slot;
      - the prisms tile exactly, within the cap; keep-out 0.0 cm3;
      - the FREE share of the polygon body is below the rectangle body's;
      - P3 (16 copies): <= 0.5 cm and <= 5 deg, overlap < 1.0 cm3.
    - **w8b**: w8 at sigma 3 mm (the 9 mm inlier band then exceeds t, as on ep24 board 1).
    - **w9** (tilt; verify_slot_1 B3, INTERLOCK 20.9 open item 2): w8 with the partner turned 2.5 deg about a_T at
      the assembled frames. Reported (P56).
  - **F-I4.15.8 Predictions** (written before any run). P41-P50 are F-I5's, so the task text's "P41 / P42" are P51 /
    P52 here.
    - **P51** ep24 (fi4o): the slotted F-I4.15 pieces of both boards pass the keep-out gate (<= 0.3 cm3 per hull) |
      any hull over | [H, near-certain by construction: it tests the exact tiling and the slot subtraction, not the
      body's fit (F-I4.15.4)]
    - **P52** ep24: both boards CARVE under F-I4.15 (every kept gate; |D_1 + D_2 - W_x| <= 10 mm with polygon entry
      edges; budget and topology) and P2-P7 pass on 16 copies (P3 <= 0.5 cm and <= 5 deg, overlap < 1.0 cm3) | any
      gate PUSHes, or any of P2-P7 fails | [H]. Reported as P52a (CARVE both) and P52b (P2-P7).
    - **P53** ep24: the polygon body follows the outline. Its end widths exceed its waist width by >= 4 mm on both
      boards [not independent: verify_slot_1 measured the same mask], and its FREE share is <= 1/3 of the full
      rectangle body's FREE share at the same t on the same board [H; E: 1-4 % absolute, against the rectangle's
      11.5 / 9.9 % at 6.21 mm] | end - waist < 4 mm on a board, or FREE share > 1/3 of the rectangle's
    - **P54** ep24 board 1: all-point t in 6.8-8.0 mm; board 2 t := board 1's | outside | [not independent:
      verify_slot_1 B2 measured 7.30-7.40 mm with this estimator]
    - **P55** synthetic: w6c is within 1 mm in all 6 cells; w8 and w8b pass as stated; w1-w5 and w7 keep their F-I4.14
      outcomes | any miss | [H]
    - **P56** synthetic w9 (2.5 deg tilt): P3 passes (<= 0.5 cm / 5 deg, overlap < 1.0 cm3) | P3 fails | [H; E:
      overlap <= 0.1 cm3, verify_slot_1 B3]
    - **P57** ep23 board 1: plate-like (any step) with all-point t in 5-10 mm; the body is built (simple polygon,
      within the cap); I-shaped (end - waist >= 4 mm); FREE share <= 1/3 of its rectangle's | any fails | [H]. Board 2
      is reported only.
    - **P58** ep24: <= 16 prisms per slotted body (a measure of the outline's roughness) | > 16 | [H]
    These tests and predictions gate or fix steps only as F-I4.15.6 states. None is a failure criterion of the gmg
    (D.3).
  - **F-I4.15.9 Constants and origins.**
    - New:
      - simplification tolerance 1.0 mm: **generic** (half the 2 mm raster pitch, the position uncertainty of a cell
        edge; the decision's example value);
      - prism cap floor(165 / objects): **informed** (the P5 cap of 165 shapes, F-I1.14), as in F-I5.4;
      - <= 32 vertices per polygon part (64 per prism): **informed** (the MuJoCo limit, F-I1.14 `maxv`);
      - the prediction thresholds (4 mm I-shape, 1/3 FREE, 16 prisms, 6.8-8.0 mm, 2.5 deg tilt): set now for
        predictions only; they decide nothing.
    - Reused unchanged: raster 2 mm; >= 3 frames per cell; slab t / 2 + 3 sigma; the 6 mm filter; >= 300 points from
      >= 3 frames per face; slab window 3-25 mm; clearance 2 x 1 mm; depth margin 2 mm; the 3 mm extensions; W_x grid
      2 mm; consistency 10 mm; budget 10 % / 0.6; keep-out 0.3 cm3; every acceptance threshold (F-I1.14).
    - Dropped with the rectangle body: the fill share 0.9 (the fill is still reported).
  - **F-I4.15.10 Integrity and cost.**
    - GT-free, as F-I4.9. Inputs: our clean bundles (ep24 `b4ext4-b61e8aa`, ep23 `b4ext6-90c8cce`), our picks,
      tracks, hands and video (source (b) is reported only). No scan, mocap, dataset-parquet `pose`, `*_align`, or
      library geometry as shape evidence. `meshes/carve/ev25` is never read. No `--gen`.
    - Public development only. Eval 25 runs only after the freeze, with the identical code. Every miss and failure is
      reported. Any change after an outcome is a new dated entry.
    - Cost [E]: CPU on this container. fi4b took 914 s without slot physics; with P2-P7 on 16 copies about 20-40 min;
      the tests 30-40 min; the ep23 candidates, plate test and body 20-40 min. If the shared container cannot make
      progress, one self-destroying Vast CPU box (`docs/runbook-vast.md`, ledger session mesh-bold, cap $5, destroyed
      and confirmed). Expected spend $0-1.
  - **Outcomes (2026-10-31, 18:30-20:12 UTC; record only: no rule, threshold or constant changed after an outcome;
    code 19c4309 for every run below; log `build/I.md` "Board slot round 2"; results `build/I/results/slot2-ep24/`,
    `slot2-ep23/`) [M].**
    - **T-I11 ep24 tag fi4o** (launched 18:38:27, 2612.7 s, physics 1938 s; this container, 4 shared cores, load
      14-32): **both boards CARVE** (T1, simulator copy only; F-I3 decision PUSH / PUSH). Board 1 step 2, t 6.212 mm on
      the downsample, **7.401 mm on all 1.76 M near points** (faces +-3.70 mm, frames 0-74 / 74-274); board 2 step 3,
      t := 7.401 mm. Polygons 86 / 126 vertices (41 / 61 reflex), 297.96 / 287.16 cm2; widths waist 130 / 126 mm, ends
      137 / 135.9 mm; FREE share 4.08 % / 1.89 % against the full rectangle's 12.92 % / 10.33 % (ratios 0.316 / 0.183).
      Slot w 9.40 mm; c_L 3.97 / 1.36 mm; D from the polygon edge 67.55 / 66.56 mm (from the rectangle 77.55 /
      66.56); cross-lap D sum 134.11 vs W_x 128.23 mm (diff 5.88); budget 2.12 % / 1.95 %, reach 0.443 / 0.460,
      topology ok. Prisms: default 50 / 71, slotted 57 / 77 (cap 82), tiling exact. Keep-out 0.0 cm3 per hull. P2-P7 on
      16 copies all pass: P3 carved 0.078 cm / 0.74 deg (default 2.805 cm / 103.66 deg), overlap at the assembled
      frames 0.04 cm3; P2 0.5 / 0.5 / 0.0 / 2.0 mm; P4 kept 0.98 / 0.98; P5 134 shapes; P6 0 worse of 84 frames; P7
      3.80 vs 146.45 cm3. Plain-MuJoCo P1 pre-check (does not decide) fails for carved and default alike. **Delivered:
      r0 `carved_p1_pending` (p1_pending, no DO_NOT_USE; `_default/` = unslotted prisms; owner_waiver fi4_rev 15).**
    - **ep23 (step 4; v6 bundle, picks shell_t5p36 built 18:39-18:41)**: board 1 plate by step 3 (one face), t := board
      2's all-point t 10.785 mm (board 2's track is the wrong board: reported only); polygon 140 vertices (68 reflex) on a
      partial outline (waist 108 / ends 74 mm); FREE 4.27 % vs 16.9 %; **default prisms 85 > cap 82:
      `plate_body_over_cap`, no body**. Board 2 (reported only): plane pair 10.69 -> 10.785 mm, 102 vertices, 56 prisms,
      FREE 9.1 % vs 26.2 %.
    - **Freeze (F-I4.15.6 step 5): (a) holds, (b) fails** (ep23 board 1's body is not built). **F-I4.15 is not frozen
      for eval 25 and eval 25 is not run under it.** Any change is a new dated entry and an orchestrator decision.
    - **T-I1 (synthetic)**: w1 at t = 6 / 10 / 13 / 18 pass (all-point t 5.84 / 9.73 / 12.63 / 17.48 mm; t = 25 out of
      scope as before), **the F-I4.13 t = 6 width miss is gone** (7.84 vs 8 +- 1 mm); w2, w3, w4, w5 (0.033 cm / 0.16
      deg) pass; **w6 now passes** (9.70 / 9.73 mm at sigma 3); **w6c passes** in all 6 cells (0.15-0.52 mm thin);
      **w7 misses** (one-face B: 184-vertex polygon, 111 default prisms > 82: `plate_body_over_cap`); **w8 and w8b
      miss** (over the cap: w8 B slotted 83, w8b 90 / 84; first run ERROR from a test-harness bug, fixed and re-run,
      no rule change); w8 also shows B's step-1 plane pair tilted 3.4 deg (t 5.11 mm), which F-I4.15.1 keeps as the
      reference normal (B's polygon prism 21.8 % FREE vs A's 3.6 %); **w9 (2.5 deg tilt) passes P3** (0.282 cm / 3.99
      deg, overlap 0.33 cm3; slotted 72 / 81, under the cap). The waiver-off T-I1 suite (24 tests, every class but Waiver): OK with its 2 recorded expected failures.
    - **Predictions:** P51 holds (by construction), P52a holds, P52b holds, P53 holds (I-shape 7.0 / 9.9 mm; FREE
      ratios 0.316 / 0.183), P54 holds (7.401 mm; not independent), P55 **fails** (w7, w8, w8b), P56 holds, P57
      **fails** (t 10.785 > 10, body over the cap, end - waist -34 mm; FREE ratio 0.252 holds), P58 **fails** (57 / 77
      prisms > 16).
    - **Mechanism of the cap failures [M]:** with 2 mm cells and a 1.0 mm Douglas-Peucker tolerance, every one-cell
      step of a noisy edge survives as two reflex vertices, and Hertel-Mehlhorn gives about one prism per reflex vertex
      (ep24: 41 / 61 reflex -> 57 / 77 slotted prisms; ep23 board 1: 68 -> 85; synthetic w7 B: 90 -> 111). The P58
      expectation (<= 16) assumed a near-rectilinear outline. [H, not adopted]: a tolerance above the raster pitch, or
      an outline fitted to rectilinear segments, would cut the prism count; it would need its own dated entry.

- **2026-10-31, F-I5: collision carve for every colliding pair under the owner's extended waiver (simulator copy
  only; cavity-preserving pieces; hands-off sink test).** Written 17:14-17:34 UTC in a design step (no code edited,
  nothing run for it) and committed and pushed **before any code or run uses it**. Still before any gmg scoring round
  (zero gmg scan scorings exist; no scan number was read for this entry). **Post hoc** with respect to results the
  author has read: INTERLOCK sections 18-20 (every pre-registered decision so far is PUSH; our default pieces fill the
  container cavities: ep2 pot union 2776 cm3 vs solid 362, ep11 cups 453 / 793 vs 172 / 170 [M]; CoACD refills them
  too), the ev10w write-up (focused-pascal `334393e`: on eval 10 the cup intrusion is one-sided in 60 / 61 frames, the
  inner axis 5.4 mm off; a lathe-widened cavity let the guest sink 11.6 mm median and hands-off settles fell from 40 / 43
  to 4 / 43; taper 2.8-4.7 deg, about 17-20 mm of drop per mm of radial clearance; a ~1 mm empty ring between the wall
  bands and the base in ev10 [M, theirs]) and determined-wright's eval-10 diagnostic. No number of a run under this
  entry exists when it is committed. Where F-I1 to F-I4 and this entry differ, this entry wins for the pairs in its
  scope **when the run sets the new flag `--waiver-fi5`**; with the flag off nothing changes (F-I1 to F-I4 exactly).
  Plate-plate pairs keep F-I4 (F-I4.0-F-I4.14 and any later F-I4 entry). Design text, plain-language summary and run
  plan: `INTERLOCK.md` section 21.
  - **F-I5.0 The waiver (verbatim) and its scope.** Owner, session_01W8Softjo2xx7o6ofSiheuQ: (1) 31 Oct ~16:00 UTC,
    "Okay I waive that camera rule" (F-I4.0); (2) 31 Oct, recorded by the orchestrator note committed at 17:13 UTC
    (`cc95b9f`; the note says ~17:30): "but like we said it doesnt have to be a board it can be a cup of what ever like
    if 2 mesh collide we can carve it"; (3) 30 Oct, the request behind INTERLOCK section 11 as the orchestrator relays
    it: the Embodiment session's frame-by-frame physics fix should be able to carve the next object "when it enters it,
    or when the cups are stacked they carve themselves into the another". **Scope:** every pair of objects whose
    **simulator colliders** (F-I5.1) interpenetrate **persistently** along the pose source (F-I5.2), any object, any
    engaged run that is not TRANSIENT. A pair whose two objects are both plate-like (F-I4.1 / F-I4.14) is a **plate
    pair** and follows F-I4 unchanged; every other pair follows this entry. In scope: **class O, the silhouette (failing,
    absent or seeing wood), the GAP image width, the OFFSET route and the push test (F-I1.3 (ii)) no longer block or
    replace a carve.** The rigid-shift alternative is computed and reported for every pair (F-I5.7) and decides nothing.
    **Kept:** engaged runs and the hold-out of check frames (F-I1.1, F-I3.3), persistence and the moves-through sweep
    share (F-I5.2), the identity / track gate (F-I1.2, F-I3.1: on public TRACK_FAIL or IDENTITY_SWAP makes the region
    absent; on eval IDENTITY_SWAP only flags), the carve caps (F-I5.3 (e)), the physical acceptance (F-I5.5) and the
    pieces keep-out gate (F-I5.4). **Simulator copy only:** no ICARVE or FUSE-I candidate comes from this entry, the
    submitted (CD-O) meshes are not touched, F-I3.2 stands. Every record in scope carries `owner_waiver_fi5`, tier T1,
    `submitted` False. Public runs of this entry use eval semantics (`--identity eval`), as T-I11 and INTERLOCK 18-19 did
    (ep11's blue cup and both ep24 boards are IDENTITY_SWAP on public); the public-semantics decision is also reported.
  - **F-I5.1 Colliders and intrusion between colliders (both paths, F-I3.1).** Every object of an F-I5 run gets a
    **default collider**: the cavity-preserving pieces of its uncarved simulator body (F-I5.4). Intrusion is measured
    between colliders, not between evidence and candidate: partner samples = the points of a 2 mm grid inside the union
    of the partner's pieces (the Embodiment export's definition, F-I1.13); target occupancy = inside the union of the
    target's pieces (exact half-space test per piece), counted on the target's 4 mm bundle grid. The region builder is
    the existing one (engaged runs >= 3 voxels, kinds, 10-frame build / check blocks, persistence, per-voxel sweep
    extent, 26-connected components; F-I1.1, F-I1.2 (c), F-I2.9, F-I3.3). Poses: P_sim (F-I1.1; else P_sel with
    `sim_pose_fallback`). The through-column split (F-I1.2) is not applied to F-I5 pairs: it exists for a partner whose
    own slot is bridged in its evidence (plate pairs, F-I4); a partner's posed collider is what the simulator collides.
  - **F-I5.2 Gates (persistence and moves-through as now).** Per persistent component R of an ordered pair: IGNORE if
    the run is TRANSIENT or R has < 3 voxels. Persistence unchanged: n_v >= max(5, ceil(0.25 N_build)). Moves-through
    unchanged in its measurement: >= 50 % of R's OBSERVED voxels are swept at max(8 mm, 3 j) (F-I1.3 (i)); R's U voxels
    need no sweep (F-I1.3 step 3). **One clause changes:** the run kind of (i) ("INSERTION or SLIDE") becomes "any
    engaged run that is not TRANSIENT" (SEAT included), because the owner's scope names seated and stacked objects and
    the sweep share still requires the partner to move through the place; a partner resting with a pose error enters
    with the same few points and fails it. A component that fails a gate keeps its F-I1 to F-I3 decision and the record
    names the gate (`waiver_gate_fail:<gate>`).
  - **F-I5.3 Carve geometry (GT-free).**
    - (a) **One receiver per pair** (only plate pairs carve both objects, F-I4). Containment share s_t = the volume
      share of the other object's collider (2 mm grid points) inside the convex hull of t's collider, at the pair's
      median relative pose over the build frames in which R is entered. Receiver = the object with the larger s; if
      |s_o - s_p| < 0.1, the object whose own track moves less (median world speed over those frames). The receiver is
      carved by the guest; the guest is never carved by this pair; the guest's own components of the pair are reported.
    - (b) **Rest pose and overshoot frames.** Hands-off static frames of the pair = frames of its static stretches
      (relative speed < 2 mm per frame for >= 5 frames, F-I1.1) with no hand point within 30 mm of the guest's collider
      (our M1 hands; the F-I1.9 rest distance). Rest pose T_rest = the mean pose (`interlock.mean_pose`) of the guest
      in the receiver's frame over the hands-off static frames of the assembled stretch, else of all hands-off static
      frames. A build frame is an **overshoot frame** if the guest's collider centroid lies more than s_max = 4 mm past
      its T_rest position along the run direction d or along gravity (our table normal, in the receiver's frame at the
      rest frames). Overshoot frames are not carved; they go to the push list (`overshoot_frames`, with their offsets).
      Without a hands-off static frame there is no T_rest, nothing is excluded, and S is untestable (F-I5.5).
    - (c) **Swept solid.** F_carve = the build frames of the run in which R is entered, minus the overshoot frames;
      check frames are never used. K = the union over f in F_carve and over the guest's pieces g_j of T_{r<-g}[f]
      applied to offset_c(g_j), where offset_c moves every face plane of the convex piece outward by c (the face-offset
      polytope contains the exact dilation by c). K is restricted to R+ = R dilated by one 4 mm voxel (the union of
      those voxel boxes): transient contact elsewhere is not carved. Carved receiver body = body minus (K inside R+), by
      exact geometry: a manifold boolean for the others route, per-(sector, bin) radii for the lathe route (F-I5.4).
    - (d) **Clearance c** = min(c_0, 0.5 x s_max x sigma_sup), floored at 0 and rounded down to 0.05 mm; c_0 = 1.0 mm
      (the F-I1.14 clearance), s_max = 4 mm (the F-I1.14 sink and free-travel bound), sigma_sup = the 99th percentile of
      max(0, n . g) over the guest's collider surface samples (0.5 mm spacing) inside R+ at T_rest (the facets the pocket
      wraps; n the guest's outward normal, g the unit gravity vector; at the median engaged pose when there is no
      T_rest). Reason (geometry, stated
      before any run): a clearance c on a support facet whose outward normal has the downward component sigma lets the
      guest drop about c / sigma before it touches; on a 3 deg cup wall (sigma ~ 0.05) c = 1 mm is ~19 mm, the ev10w
      mechanism. The formula keeps that drop <= 2 mm, half of s_max (the other half is left for the pose spread of the
      swept frames and the jitter). A flat seat (a lid rim, a base on a shelf: sigma ~ 1) gets c = 1 mm. sigma_sup = 0
      gives c = 0 (exact fit, flag `c_zero`).
    - (e) **Caps** (thresholds of F-I1.14, unchanged): cumulative carved collider volume (Monte Carlo, all rounds,
      F-I3.3) <= 10 % of the receiver's round-0 collider volume, for every F-I5 carve (the F-I2.6 exemption of R_U-only
      carves is not used: a cavity-preserving body has no unseen cavity fill to remove); reach <= 0.6 of the receiver's
      extent along d for INSERTION and SLIDE runs; topology: the 2 mm grid points inside the carved pieces keep the
      default's 26-connected component count and Euler number (`interlock.topology`; a wall thinned below about one
      sub-voxel opens a hole there and fails). Failure: `budget_iv_fail` or `topology_fail`, default delivered.
  - **F-I5.4 Cavity-preserving pieces (default and carved, every object of an F-I5 run).** The first route that
    applies and passes the pieces gate is used; a route whose pieces fail the gate falls to the next:
    1. **Plate** (plate pair): F-I4.6 analytic boxes, unchanged. A plate-like object paired with a non-plate gets its
       F-I4.2 plate body, carved by F-I5.3, and goes to route 4.
    2. **Lathe container**: `structure.hypotheses` accepts the lathe (rotc <= 3 sigma, A.6, unchanged) **and** the
       object is not plate-like (F-I4.1 / F-I4.14 steps 1-2; a flat plate passes rotc alone, B7). Body: the profile of
       the object's SHELL candidate solid (the CPU producer's shell, present for every object; the visual GLB stays the
       submitted mesh) about the structure axis, 2 mm height bins and 16 azimuth sectors: per (sector, bin) the radial
       interval of the solid's 2 mm sub-samples; per bin the median over the sectors that hold material of the outer
       and inner radius; a bin is wall if that inner radius > max(3 sigma, 2 mm), else solid (base); more than two
       radial intervals in a bin -> route 3 (`lathe_profile_complex`). The body is the revolution of that profile
       (symmetry completion of the unseen sectors). Shell material outside the body by > 3 sigma in components of
       >= 0.3 cm3 (a handle) is decomposed by route 3 and added. Pieces: N_s = 16 sectors (12, then 8, if the object's
       piece cap is exceeded) x height bands <= 30 mm (<= 10 mm where a carve applies), band edges on profile bins and
       at the top and bottom of each sector's carve; each wall piece = the convex hull of its outer and inner profile
       points at the sector's two edge angles; base = a centre disc (r / 2) plus N_s rim sectors; **the lowest wall band
       of every sector starts exactly at that sector's base top** (no empty ring: the ev10 defect). Carve (F-I5.3) in
       profile space: a guest sample above the sector's base top sets that (sector, bin)'s inner radius to
       (its radius + c) / cos(pi / N_s) where larger (the inner chord then clears it by c); a sample below lowers that
       sector's base top to its height - c. **Wall-continuity check:** rays at the mid-wall radius every 0.5 mm in
       height from the base top to the rim and every 1 deg in azimuth must each lie inside a piece; a gap rejects the
       route (`lathe_wall_gap`).
    3. **Others** (or a lathe that failed): CoACD on the (carved) body mesh, threshold 0.02 (finer than its 0.05
       default), preprocess auto, max_convex_hull = the object's piece cap; then **keep-out repair**: every hull holding
       > 0.3 cm3 of keep-out is split by the plane that minimises the keep-out volume in its two children, repeated
       without any minimum-gain stop (the frozen-split failure of INTERLOCK 18.4 item 3) until each hull is <= 0.3 cm3
       or the cap is reached.
    4. **Voxel boxes** (exact fallback): the 2 mm grid points inside the (carved) body and outside the keep-out,
       merged greedily into maximal axis-aligned boxes (exact unions of their cells); over the cap, a 4, 6, then 8 mm
       grid whose cells are kept only when all their 2 mm cells are kept. Over the cap at 8 mm: the object has no
       compliant pieces.
    **Pieces gate** (F-I3.8 mechanism, F-I1.8 tolerance): every hull holds <= 0.3 cm3 of keep-out; keep-out = the 2 mm grid points
    outside the body the pieces stand for (the default or the carved body) that lie in K inside R+ (weight 10) or in a
    FREE voxel of the object's grid (weight 1), **without the 2-voxel distance limit of F-I1.8** (hulls spanning a
    container's opening hold FREE space far from its surface; INTERLOCK 18.4 item 3). The silhouette is not run (it cannot change an
    F-I5 decision), so SIL adds nothing. **Piece cap:** floor(165 / number of objects in the episode) per object, and
    P5 for the episode. An object without compliant default pieces makes the round folder do-not-use (F-I3.8). The old
    splitter (`simpieces.decompose`) is not used in F-I5 runs.
  - **F-I5.5 Acceptance per carved pair** (receiver carved against the same pair with both default colliders, poses
    P_sim; simulated tests as means over 16 jittered copies, 0.5 mm / 0.005 rad, common random numbers). Carved pieces
    are delivered only if **all** pass; otherwise the default pieces, with the numbers and the failing test reported.
    - **S, hands-off rest / sink (new; the ev10w failure mode)**: at up to 3 hands-off static frames (the middle frame
      of each hands-off static segment, longest first), plain MuJoCo (gmg venv, 3.17.0, default contacts), receiver
      fixed at its pose, guest free (uniform-solid inertia of its pieces, the 0.3 kg placeholder mass, D-I1), our table
      plane, gravity along its normal, dt 2 ms, 2.0 s, no hands (the ev10w M3 setup, informed). Pass at every S frame:
      the mean displacement of the guest from its tracked pose <= 4 mm and its mean tilt <= 5 deg; no NaN copy; no copy
      with the guest below the receiver's lowest point. Per-copy dz, lateral and tilt are reported, and the default's.
      No hands-off static frame: S is untestable (`sink_untestable`) and P2's gravity bound carries the sink check.
    - **P2** free travel (F-I1.8, unchanged): along gravity, +d and +-n (n = the component's thinnest axis normal to d)
      <= max(4 mm, default + 1 mm); 26 directions reported. At T_rest, else at the median assembled or engaged pose.
    - **P3** replay proxy (F-I1.8 / F-I4.7, for every run kind): carved median lag <= 0.5 cm and <= 5 deg at the S
      frames (at the engaged frames when there is none), never > 1.0 cm after the first of them, no NaN copy, collider
      overlap < 1.0 cm3 there.
    - **P4** removed collider volume <= 1.5 x the carve's volume inside the body, >= 90 % of the default kept.
    - **P5** <= 165 shapes per episode (merge adjacent hulls, smallest keep-out increase first, each still <= 0.3 cm3;
      else the pair whose carve gains least in S mean displacement over its default gets its default).
    - **P6** carved overlap <= default + 0.1 cm3 at every checked frame (stride 4 plus the rest frames), every pair of
      the episode; **P7** on the check frames of engaged runs, carved overlap <= 0.5 x the default's (`no_holdout` runs:
      reported only).
    - Pieces gate (F-I5.4) on the carved and the default sets.
    - **P1** (FlashCHORD 2 s settle) stays the Embodiment session's `jitter_check --k 16` on the delivered folder before
      any pack uses it (F-I2.12 as amended by F-I4.8); A1-A4 of F-I3.3 apply to later rounds, with S added to A3.
  - **F-I5.6 Delivery.** A new round folder per episode and tag (never overwritten) in the Embodiment layout (F-I3.9):
    per object `piece_XX.obj` = carved pieces when its pair passed F-I5.5, else its default pieces; `<obj>.glb` = the
    unchanged submitted mesh; `_default/` = every object's default pieces; `manifest.json` with an `owner_waiver_fi5`
    block (this entry, the quotes, per pair: receiver, c, sigma_sup, overshoot frames, caps, S and P2-P7 numbers, route
    per object) and `p1_pending: true`; `sources/`; `props_gmg.json` (0.3 kg placeholder). Carved pieces of a failed pair
    are kept under `_carved_failed/<pair>/` with the failing test, never used. Do-not-use only when a default fails the
    pieces gate.
  - **F-I5.7 Reported, never deciding.** Per pair: (i) the rigid-shift alternative: the push proxy (smallest partner
    translation over 26 directions plus R's normal, 2 mm steps, F-I1.3 (ii)) and a rotation-augmented search on at most
    12 build frames (tilts 0-3 deg in 1 deg steps at 8 azimuths, translations <= 10 mm on a 2 mm grid then 0.5 mm; the
    ev10w M2 search): the share of frames whose collider intrusion falls to <= 2 cm3 within 1 cm / 3 deg; (ii) for lathe
    receivers, one-sidedness: the share of build frames with >= 75 % of the intrusion volume in one 180 deg half about
    the axis; (iii) flag `carve_of_pose_error` when (i) clears >= 75 % of the frames: the carve then makes room for a
    track error, and the shift goes to the push list for the tracker; (iv) the F-I1 to F-I3 decision the same pair gets
    with the flag off; (v) S on plate pairs (F-I4 decides them).
  - **F-I5.8 Integrity.** Inputs: our clean bundle (owned points, grids, tracks, census, identity flags, sigma), our
    candidates (SHELL, pick), our hands (M1), our table plane, P_sim after the F-I1.13 / F-I3.10 provenance check.
    GT-free: no scan, mocap, dataset-parquet `pose` field, `*_align`, library_v1..v4 geometry or scan-derived constant
    (the mass is the 0.3 kg placeholder until D-I1). Public development and eval inference stay separate; constants are
    fixed here before any run and never tuned on eval; failures are reported with numbers; any change after a run is a
    new dated entry labelled post hoc. The F-I5 flag, its code paths and its tests are new; the F-I1 to F-I4 behaviour
    stays the default.
  - **F-I5.9 Tests and predictions (written before any code or run).** **T-I12** synthetic (`tests/test_interlock.py`,
    flag on unless stated): x1 nested tapered cups (taper 3 deg, host wall 4 mm, guest tracked 0.5 mm radially too deep
    at a hands-off rest, coaxial insertion along the axis): both lathe route, receiver = host (s >= 0.8 vs <= 0.2),
    c in 0.05-0.15 mm, no empty ring, gate passes, CARVE delivered with S, P2-P7 passing; x2 = x1 with a 3 mm one-sided
    lateral offset at the rest frames and the guest's bottom edge inside the host wall (a shelf): CARVE delivered;
    x3 = x2 without the shelf (the offset pockets only the tapered wall): S fails and the default is delivered (the
    acceptance catches the ev10w mechanism); x4 = x1 with c forced to 1.0 mm (diagnostic override, never delivered): S
    or P2 gravity fails (drop > 4 mm); x5 = x1 with 6 build frames 10 mm deeper along d: those frames are flagged
    overshoot and not carved, CARVE delivered; with the exclusion disabled (diagnostic) S fails; x6 plate pair: the
    F-I4 path, records identical to F-I4 alone (w1 cases); x7 controls n2 (resting pose error: not swept, no carve of
    OBSERVED voxels), n4 (TRANSIENT), wandering jitter (not persistent): no carve; x8 a flat plate passing rotc is
    routed as a plate, never as a lathe; a folded sheet passing rotc gets lathe pieces that fail the gate (FREE inside)
    and falls to route 3; x9 a lathe built with a forced 1 mm ring between base and wall is caught by the continuity
    check, the real builder has none; x10 flag off: every existing T-I1 decision unchanged; x11 an open box (pot-like)
    via route 3 passes the gate with its opening empty. **T-I13** real runs, eval semantics, in this order: public ep11
    (cups), ep2 (pot, lid), ep12 and ep13 (blue cup and rack), ep31 (sweeper and rack); ep24 boards come from the
    board-slot (F-I4) runs and are not re-run; then the eval twins 10, 1, 14, 30 (eval 25 from the board-slot work), each
    only once its eval bundle exists. Predictions (E additions; [H] unless marked):
    - **P41** ep11: both cups take the lathe route (B7 dev rotc 1.61 / 2.88 sigma) and their default pieces pass the
      gate with no empty ring | either cup leaves the lathe route, a hull > 0.3 cm3, or a continuity gap.
    - **P42** ep11: the default lathe colliders alone cut the maximum collider overlap along the track to <= 20 % of the
      old splitter's 544 cm3 (<= 109 cm3) | above.
    - **P43** ep11 (the owner's case): the receiver is the cup the other is lowered into; the swept-partner carve keeps
      the guest at its tracked pose: S passes at every hands-off frame (mean displacement <= 4 mm, tilt <= 5 deg; the
      ev10w lathe widening sank 11.6 mm), and P2-P7 pass | **the sink test fails on ep11**, or any other test fails.
    - **P44** [E] the cups' c is 0.05-0.2 mm (taper 2.8-4.7 deg, sigma_sup 0.05-0.08) unless the guest's base lies in
      the pocket (then 1.0 mm) | outside these values.
    - **P45** ep2: the pot takes route 3 or 4 (B7 dev, ep27 pot: rotc 3.01 sigma, rejected by 0.01 sigma), the lid the
      lathe route (B7 dev, ep2 lid: 2.04 sigma); receiver = pot; c = 1.0 mm (flat rim seat); S and P2 pass | S fails or the lid's gravity
      travel > 4 mm (October's carved lid sank 0.6-1.0 cm with 6 mm of free travel).
    - **P46** ep12, ep13: the rack's pieces pass the gate by route 3 within its cap (no voxel-box fallback); receiver =
      rack; S passes for the cup | route 4 is needed, or S fails.
    - **P47** ep31 (P34 restated for F-I5): every delivered copy lets the sweeper drop <= 4 mm (P2 gravity) and tilt
      <= 5 deg (S) | any delivered copy outside these bounds (October's rack carve dropped it 2.5-3.5 cm).
    - **P48** ep11 report: the rigid shift clears >= 75 % of the build frames within 1 cm / 3 deg
      (`carve_of_pose_error`), as on eval 10 (30 of 31 frames) | < 50 %.
    - **P49** each eval twin (10, 1, 14, 30) gets the same per-pair outcome (carved delivered or default) as its public
      twin (ep11, ep2, ep13, ep31) | any differs (reported, nothing tuned).
    - **P50** T-I12 x1-x11 pass as stated | any miss (logged; a code bug is fixed and logged, a rule change needs a
      dated post-hoc entry).
    These tests gate or fix steps; none is a failure criterion of the gmg (D.3).
  - **F-I5.10 Constants and origins.** c_0 1.0 mm and s_max 4 mm: **informed** (F-I1.14). The half-budget factor 0.5,
    the 99th percentile of the support slope, the 0.05 mm rounding: **generic**. Containment tie 0.1: **generic**.
    Overshoot bound = s_max: **informed** (F-I1.14). Hands distance 30 mm and the static rule: **generic** (F-I1.14).
    S: 2 s, 4 mm, 5 deg, 16 copies **informed** (F-I1.14); its setup (receiver fixed, guest free, 2 ms, plain MuJoCo)
    **informed** (the ev10w M3 settle, chosen after seeing its result). Lathe: 16 sectors, 30 mm bands, the centre-disc
    plus rim-sector base **generic** (`lathe_collision.py` defaults); 10 mm bands where carved **informed** (ev10w's
    widened band); 12 / 8 sector fallback, 2 mm bins, max(3 sigma, 2 mm) wall test, 0.5 mm x 1 deg continuity rays,
    0.3 cm3 handle residual (= the keep-out tolerance) **generic**. CoACD 0.02 **generic** (finer than its 0.05
    default). Voxel grids 2 / 4 / 6 / 8 mm **generic**. Piece cap floor(165 / objects) and the 0.3 cm3, weight-10
    keep-out **informed** (F-I1.14). Rigid-shift report (1 cm / 3 deg, 2 cm3, the tilt grid, 75 % one-sided) **informed**
    (ev10w M2); `carve_of_pose_error` 75 % **generic**. Every other threshold: as in F-I1.14 and F-I4.11.
  - **F-I5.11 As built (decided while building, 17:36-18:33 UTC, before any real run; recorded 18:37 UTC).** Code
    `gmg/collcarve.py`, `gmg/cavpieces.py`, `simphys.sink_test`, the `waiver_fi5` hook in `interlock.decide_pair`, the
    `--waiver-fi5` driver branch, `tests/test_collcarve.py` (T-I12 lives in this new file: `tests/test_interlock.py` was
    being edited by the board-slot workflow). Deviations from the text above, none of them a threshold:
    (1) lathe profile radii by casting rays from the axis through the SHELL mesh (3 azimuths per sector, median), not
    from the 2 mm sub-samples (which sit up to ~1 mm inside the surfaces); (2) the lathe carve works per piece, not per
    (sector, bin): each piece holding a posed K piece takes the option that keeps the most volume among a new linear
    inner face r(h) = alpha + beta h (linear programme over the vertices of K inside the piece, exact clearance), a new
    outer face, or its top or bottom trimmed to K's extreme height; a piece with no feasible option (K within 0.2 mm of
    its outer face) is removed and the caps then decide; carved wall ranges are re-banded at <= 10 mm and the 16 / 12 / 8
    sector fallback applies to the carved set; (3) in the lathe route the R+ restriction is applied per K-in-piece set
    (a set with no vertex or centroid in R+ is ignored, a set with one is carved whole: slightly more than K inside R+);
    the other routes use the exact boolean K inside R+; (4) K inside a piece by exact vertex enumeration (vertices of each
    inside the other plus edge-facet crossings); (5) CoACD runs in a forked child (CoACD 1.0.14 aborted the interpreter
    on a C++ assertion on the T-I12 rack fixture); an abort is a route-3 error and the ladder falls to route 4.
  - **F-I5.12 T-I12 outcomes (synthetic, 17:59-18:32 UTC, code fae78de and the WIP snapshots after it; logs in
    `build/I.md`).** **P50 is falsified**: x1, x2, x3, x4, x5 and the x7 wander control miss; x6, x7 n2 / n4, x8 (both),
    x9, x10, x11 pass as stated. Measured: every cup case (x1, x2, x4, x5 and the extra x2b, 5 mm offset) is in scope
    (receiver = host by containment 0.78-0.88 vs 0.06-0.21, INSERTION, sweep 0.87, c = 1.0 mm because sigma_sup = 1.0)
    and **stops at the caps before any physics**: topology 1/1 -> 33/31 (x1, x4, x5), 14/3 (x2), 1/0 (x2b); removed
    35-74 % of the receiver collider (cap 10 %); reach 0.81-0.91 (cap 0.6). x3: the receiver's component fails the sweep
    gate (0.378), `receiver_no_region`, no carve and no S. Sweeper fixture (holder with a blind hole): reach 0.96 >
    0.6, default. No cup case reached S, so P43's question (does the carve keep the guest at its tracked pose) is not
    answered by the pre-registered rule. Mechanisms [M]: (i) the swept union over raw build frames includes the track
    jitter (0.5 mm / 0.2 deg per frame in T-I12) and, with c = 1 mm and the face-offset corner growth, reaches up to
    r = 36.8 mm in a 33.7-37.7 mm wall, beyond the outer chord of a 12-sector piece (36.4 mm): no feasible option, the
    piece is removed; (ii) re-banding the carved wall at 10 mm over its full height exceeds the 82-piece cap, so the
    carve falls to 12 or 8 sectors (an 8-sector chord sits 2.9 mm inside a 37.7 mm outer radius); (iii) a wall-layer
    carve of a nest spans the whole wall height, so reach along the axis is 0.8-1.0 for every INSERTION nest; (iv)
    sigma_sup = 1 because R+ holds the guest's base corner (P44 anticipated this case: c = 1.0 mm). Without track jitter
    (diagnostic) the nest's main components fail the sweep gate (0.15 / 0.28, run SEAT) and S fails for the carved
    and the default pieces alike (the 9.5 mm-too-deep guest is pushed up 4.6 mm). No rule is changed by this entry.
  - **F-I5.13 Diagnostic D2, rest-anchored pocket (post hoc, written 18:37 UTC after F-I5.12, before D2 runs; NOT a
    rule: never delivered, decides nothing; for the orchestrator / owner).** Question: does a pocket cut at the guest's
    hands-off rest pose keep a nested guest where our track puts it (P43's question), once the noise of the raw frames
    is not carved? D2 = F-I5 with three changes: (a) when T_rest exists, K per guest piece g = the convex hull of
    T_rest . offset_c(g) and of the same copy translated along d by s_min, where s_min = min(0, min over the build
    frames entering R of s_f) and s_f = the guest centroid's offset from its rest position along d (deeper positive):
    the rest pose plus the straight approach channel along d; the frames' lateral and rotational deviations from the
    rest and every frame deeper than the rest are not carved (the overshoot rule becomes moot); without T_rest, F-I5.3
    (c) unchanged; (b) the lathe carve keeps the default band layout and sector count (no 10 mm re-banding); (c) the
    volume and reach caps are computed and reported but do not gate; topology still gates; when topology fails, S is
    still run on the default and the failed carve (diagnostic rows). Gates, receiver, c rule, S, P2-P7 and the pieces
    gate as F-I5. Cases: x1, x5, x2, x2b (5 mm, the eval-10 offset), sweeper, and a new fixture x2c (x2 with a 1 mm
    offset). Predictions [H], each with its falsifier:
    - **Q1** x1-D2: topology kept; removed about 20-30 % of the receiver collider (a 1 mm clearance layer over about
      17,600 mm2 of wall plus the 0.5 mm radial error: the 10 % cap would fail); S passes (the guest drops about c onto
      the ledge cut under its base corner) | S fails.
    - **Q2** x5-D2: as Q1, the dipped frames are not carved | S fails or a dipped frame is carved.
    - **Q3** x2-D2 (3 mm offset in a 4 mm wall, c = 1 mm): topology fails (wall pierced) | topology kept.
    - **Q4** x2b-D2 (5 mm offset): topology fails; no carve can hold a 5 mm off-axis cup in a 4 mm wall, the pose
      correction (F-I5.7 shift) is the remedy | topology kept.
    - **Q5** x2c-D2 (1 mm offset): topology kept, S passes | either fails.
    - **Q6** sweeper-D2: reach about 0.96 reported; S passes (the stick drops <= c onto its cut floor) | S fails.
    **Amendment to (b), 18:41 UTC, after the first D2 launch (18:39) and before any D2 result was produced (the run
    was stopped at 18:40 with no S, acceptance or summary line; its one carve-geometry line was not read):** the lathe
    carve keeps F-I5.4's band edges at each sector's carve top and bottom and drops only the 10 mm limit inside the
    carve (bands <= 30 mm there). Reason (geometry, stated before any result): with the default bands a single linear
    inner face per band also widens the wall below the guest's base corner, which removes the ledge Q1 relies on (the
    guest could drop onto the host base, about 4.5 mm in x1). Measured on the x1 host: default 65 pieces, this layout 81
    (16 sectors, cap 82), the pre-registered 10 mm re-banding 177 (hence its 12 / 8-sector fallback).
    Use: if Q1, Q2, Q5, Q6 hold, the remaining blockers for cups and holders are the 10 % volume cap and the 0.6 reach
    cap (F-I1.14 numbers made for board slots): a policy decision for the orchestrator / owner, to be written as a
    dated entry before any real run uses it. If Q1 or Q5 fails, a rest-anchored pocket does not keep a nested cup and
    the cups need the pose correction instead of a carve.
  - **F-I5.13 outcomes (measured 18:41-19:09 UTC, code 3484d8d and cbed3cb; recorded 19:10 UTC; nothing delivered).**
    Q3 (x2, 3 mm) and Q4 (x2b, 5 mm) **hold**: topology fails (5 / -10, 1 / -11; a 3-5 mm offset plus c = 1 mm in a 4 mm
    wall [E]; not re-checked on a 1 mm grid). Q1 (x1),
    Q2 (x5) and Q5 (x2c, 1 mm) are **falsified as written**: topology fails on the 2 mm grid (1 / -45, 1 / -45, 2 / -14).
    For x1 a diagnostic shows the same carve keeps the default topology on a 1 mm grid with a thinnest wall of 1.7 mm
    (median 2.0 mm, no ray under 0.5 mm): the failure is 2 mm aliasing of a wall thinned by c = 1 mm, not a hole. Q6
    (sweeper) is not testable as written (no T_rest, S untestable; P2 gravity 5.0 mm and P4 fail). Removed volume 19-36 %
    of the receiver collider, reach 0.57-0.89 on the cups. **S rows (diagnostic, never deciding): every cup carve keeps
    the guest within 4 mm and 5 deg** (displacement 2.25-3.03 mm, drop 1.6-2.9 mm, tilt <= 3.4 deg), including the 5 mm
    off-axis guest; **the default rings** move a 9.5 mm-too-deep guest up by 4.4-4.6 mm (fail), a 5 mm off-axis guest
    sideways by 4.9-5.0 mm (fail), a 3 mm one by 3.0 mm and a 1 mm one by 1.0-1.1 mm (pass). x2c also showed that the
    as-built lathe R+ rule (F-I5.11 (3)) can carve far more than K inside R+ (19.5 cm3 removed for 0.39 cm3). Code fix
    found by D2 (cbed3cb): `decide_component` returned CARVE with an empty carve set (crash in `carve_solid`); an empty
    set is now a PUSH. No rule is changed by this entry; the open decisions are listed in INTERLOCK 21.10.
  - **F-I5.14 T-I13 public runs as executed (written 19:17 UTC, before any T-I13 run; post hoc with respect to the
    F-I5.12 / F-I5.13 results, which the author has read).** No decision of INTERLOCK 21.10 has been written, so the
    public runs use **the rule as written**: F-I5.0-F-I5.10 as built (F-I5.11) with the cbed3cb fix (an empty carve set
    is a PUSH); D2 (F-I5.13) is not used. (1) **Inputs** (GT-free, F-I5.8): the newest clean bundles, v6
    (`runs/20261031-b4ext6-90c8cce`: ep11, ep2, ep12, ep13, ep31 extract rc 0, strace audit forbidden 0; the v6
    identity / B.2a step has not run, so no IDENTITY_SWAP flag is present; under `--identity eval` it would only flag);
    our M1 hands of the same run (`hands/public/epN/hands.npz`, copied into the dev run, sha256 in `in/SOURCES.sha256`);
    CPU candidates rebuilt from the v6 bundles by `tools/interlock_cands.py` (producers and dev t0 unchanged); picks as in
    the earlier dev runs: shell_t5p36 for every object except the ep2 lid (hull, as in drv2_t3); the F-I5 body is the
    driver's default (the pick if it is a SHELL candidate, else the first shell_* candidate). P_sim = P_sel
    (`sim_pose_fallback`). (2) **Command** per episode (dev run `runs-dev/20261031-fi5pub-3053a78`, one tag `fi5`):
    `GMG_MODE=dev nice -n 5 python -m gmg.tools.interlock_dev --run <run> --ep N --bundle <v6>/epN --cands
    <run>/cand/public/epN --pick <picks> --hands <run>/in/handsN/hands.npz --proxy-copies 16 --identity eval --waiver-fi5
    --no-physcheck --tag fi5`; no `--video`: the silhouette cannot change an F-I5 decision (F-I5.4), so the reported
    flag-off decision (F-I5.7 (iv)) is the no-silhouette one and is labelled so. (3) **Order:** ep12, ep13, ep31, ep11,
    ep2 (owner priority relayed by the task; F-I5.9 listed ep11 first; the code is frozen, so the order changes no
    outcome). (4) **Report-only addition (post hoc, decides nothing):** when an in-scope pair's carve stops before the
    acceptance (caps fail or no feasible carve) and a hands-off static frame and the table exist, S is also run on the
    default pieces and on the failed carve (`diag_S_rows`, the D2 rows mechanism, `collcarve.FI5(diag_sink=True)`,
    on by default in `run_episode` only; T-I12 / D2 unaffected), so that every in-scope pair reports how the delivered
    default holds the guest. Decisions, caps, acceptance and delivery are unchanged. (5) Predictions P41-P48 stand as
    written. Expectation [E, from F-I5.12, not a new prediction]: cup nests may stop at the caps before S, by mechanisms
    (i)-(iii) of F-I5.12. (6) Machine: this container (4 shared cores, load ~16); no rental.
    (7) **Addendum, 20:30 UTC (post hoc: written after the ep11 and ep12 results, before it runs; report only, decides
    nothing, never delivered):** the delivered round folders hold 6 mm voxel-box colliders of 3.6-6.5 % of the SHELL
    body volume [M], and S runs only inside the acceptance of an in-scope pair. So S is also run on the pieces each
    round folder delivers (and its `_default/` pieces when they differ), for every pair, in or out of scope:
    `build/I/fi5_default_sink.py` (static contact runs >= 5 frames at < 2 mm per frame, receiver by containment as
    F-I5.3 (a), hands-off as F-I5.3 (b), up to 3 S frames, `simphys.sink_test` with the F-I5.10 constants). Question: is
    the delivered copy physically usable? No threshold is new; the 4 mm / 5 deg bound is S's.

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
