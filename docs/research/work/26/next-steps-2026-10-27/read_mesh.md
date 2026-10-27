Short answer: yes for the CD-O board, only a little for AUC. A better mesh is close to the only lever on CD-O. On AUC, the board that ranks us, it is worth about +0.00 to +0.02 at most, and swapping meshes has already cost us score once (−0.0045). AUC is held back much more by policies not following our reference (≈0.09–0.115) and by spoon pose (up to ≈0.045–0.06). The one place mesh shape clearly moved AUC is the simulator's collision copy, and we already fix that per episode.

Branch shorthand: **M** = `origin/main-bsky37`, **B** = `origin/claude/bold-albattani-6qmxsv`. Labels: [M] measured, [D] checked against the public scans after inference, [E] estimate, [H] hypothesis.

## 1. How the object mesh enters the score

**(a) CD-O board, directly.**
- The kit rescales our mesh to the hidden scan (ratio of area-weighted RMS radii), runs trimmed ICP from 25 PCA starts, and scores the symmetric Chamfer distance in cm.
- The board is a flat mean over 36 (episode, object) pairs (B:`docs/research/mesh-2026-10-26/README.md` §1).
- Because of the radius-based rescale, missing or extra surfaces are punished, not only wrong shape. Example: blue-cup lathe 0.382 as scored vs 0.316 at its true scale [D] (same file).
- Pairs per object: pot 6, rack 5, blue cup 5, spoon 10, beige cup 2, dust pan 2, sweeper 2, lid 1, pitcher 1, board 1 and board 2 one each.

**(b) Body frame of the submitted poses: AUC registers our mesh, then measures error on the organisers' scan.**
- Each submitted pose is converted into the scan's body frame by registering our embedded mesh (`object_mesh_b64` = `budget_mesh(glb, 4096, 4096)`) to the hidden scan. The registration uses a fixed seed: 1,000,003·episode + 101·slot.
- The ADD error points are the hidden scan's own points minus its anchor (M:`docs/analysis/robustness-review-20261026/refcheck/scorer/README.md` §1).
- So a registration error of θ in our mesh rotates or offsets that object in every frame. The kit aligns the whole scene once at frame 0: rotation from the lowest-slot object without a symmetry axis, translation always from slot 0.
  - A bad mesh on slot 0 or on the rotation anchor therefore moves the whole scene.
  - Cups are slot 0 in evals 8, 10, 14, 20, 32 and 33 (same file).
- The hidden scan is necessarily lower resolution than the public one (16 MB decode limit). Near-symmetric meshes can therefore flip 180° depending on seed or scan resolution [M] (same file, §2b–2d).
- CD-O is a separate Kaggle upload: the uploader has an `--only` flag, and pack 4's README says "CD-O was not re-uploaded" (M:`docs/work-log.md` around line 3145; M:`results/submissions/20261026-track3d/README.md`).
  - So the CD-O mesh and the mesh inside the AUC file can differ.
  - Whether that is acceptable under the rules is an open question for you or the organisers.

**(c) FoundationPose tracking quality (the mesh is the tracking template).**
- With the exact scan as template, perception scored 0.993–0.998. Today's own-mesh perception on the same episodes scores 0.961 / 0.871 / 0.957 / 0.948 (ep13 / 22 / 40 / 43) [M, but code versions differ] (M:`.../refcheck/chain/README.md` §4).
- The flattened v4 boards broke ep24 perception: 0.795 → 0.029 [M] (M:`docs/work-log.md` line 2614).
- An important catch: tracking with a biased mesh partly cancels the same mesh's registration bias. With our meshes, the pot (ep26, 27), the boards (ep24) and cup + rack (ep13) score +0.02 to +0.07 better than with the scan [M] (chain README §2).
  - So swapping only the packed mesh, without re-tracking, can lose that cancellation.

**(d) Simulator collision copy** (CoACD hulls, carves, cavities, stacking, flat bases; M:`docs/research/notes/19-collision-hulls.md`).
- Hull inflation: voxel preprocessing of non-watertight meshes plus a concavity tolerance up to 0.025 × object size (rack 12.6 mm, pot 8.7 mm).
- Each centimetre an object stays off costs about 0.125 of that object's AUC [V, note 19 §1.7].
- A watertight input removes 31–44 % of the excess inflation.
- Open shells, filled cavities and missing bases changed rollouts drastically (section 2).

**(e) Contacts and grasps in simulation.**
- `pipeline/grasp_lock.py` and `pipeline/contact_retarget.py` both use a signed-distance field built from our collision mesh (`HullSDF`) to place and snap grasps (M, code).
- Example: a copied grasp on eval 35 sat 11.5 mm off the bowl (grasp_lock.py, around line 94).
- Resting-height errors from the mesh [M] (M:`.../refcheck/README.md` R7):
  - blue cup sits 8–13 mm low;
  - lid sits 7–9 mm into the pot;
  - sweeper sits 9–11 mm low.
- There is no isolated AUC measurement for this channel [H].

## 2. What mesh changes have measurably done so far

**AUC board (Kaggle):**
- **Lathe pitcher swap, eval 20:** −0.0045 Track 3 AUC [M], packs 5 → 6, where only that mesh differed (M:`results/submissions/20261026-track3f/README.md`).
  - On the public twin it had looked like +0.098, but that was one lucky draw.
  - Across 30 seeds the lathe's yaw spreads −14° to +7° (library_v3: −2.7° to 0°). Across 5 twin seeds the swap ranged from −0.33 to +0.10, mean −0.089 [M] (M:`.../refcheck/scorer/README.md` §2e).
- **Carved collision copies, evals 10 and 25:** these changed the simulator copy only (eval 10 hybrid cups; eval 25 board slot).
  - Eval 10: 0.342 → 0.452 (mean of 5 evaluations).
  - Eval 25: mean 0.71 → 0.792.
  - On CPU, the eval-25 board went from 104° to 0.5°.
  - Pack 3 → 4 went 0.78893 → 0.81056 [M], but that pack also changed eval 33 and fixed a packing bug (M:`results/submissions/20261026-track3d/README.md`; M:`docs/analysis/episode-scoreboard-20261026.md`).
- **Other simulator-copy effects:**
  - Eval 20 arc foot: twin 0.657 → 0.772 [M] (M:`STATUS.md`).
  - A ragged sweeper underside dropped ep18 from 0.889 to 0.320 [M] (M:`docs/research/notes/25-support-consistent-meshes.md`).
- **Swap tests on public twins, one draw each (unreliable):**
  - Blue-cup lathe: −0.022 / −0.044 / +0.023.
  - Pot lathe: −0.003 / +0.002.
  - Sweeper v3 vs v2: +0.007 / −0.005.
  - Source: M:`docs/analysis/meshswap-20261026/README.md`.

**What our meshes cost at registration vs the scan, same tracks** [M] (M:`.../refcheck/chain/README.md` §2):
- Mean −0.016, median 0.000 over 33 object-episodes. The loss is concentrated:

| Object (public episode) | Our mesh vs scan (object AUC) |
|---|---|
| Pitcher (ep21, ep22) | −0.230, −0.215 (about half comes from the blue cup's ≈ 0.9 cm offset in slot 0) |
| Rack, via the sweeper as anchor (ep31) | −0.144 |
| Lid | −0.060 |
| Beige cup | −0.059 |
| Blue cup (ep12) | −0.053 |
| Sweeper | −0.038 |
| Pot (ep43) | −0.033 |

- **Sweeper flip risk at Kaggle's own seeds:** 3 of 24 stand-in scan resolutions flip on eval 30 and 4 of 24 on eval 19. Each flip costs about −0.034 Track 3 [M] (M:`.../refcheck/README.md` R3).

**CD-O board, scored against the public scans [D]** (B:`docs/research/mesh-2026-10-26/README.md` §4, §9):

| Object | CD-O (cm) | Registration offset (mm) | Flips |
|---|---|---|---|
| Pot | 0.437 → 0.342 | 6.7 → 3.05 | 0/8 |
| Lid | 0.421 → 0.220 | 8.1 → 4.46 | 0/6 |
| Rack | 0.555 → 0.456 | 6.0 → 5.37 | 0/7 |
| Blue cup, lathe from ep21 points | 0.523 → 0.291 | 10.0 → 4.1 | 0/7 |
| Board 1 | 0.222 → 0.189 | — | 1/6 (fail) |
| Board 2 | 0.216 → 0.229 | 3.6 → 78.7 | 3/6 (fail) |

- The blue-cup lathe from ep22 points scored 0.364, and merging both episodes 0.396.
- Screened Poisson on the raw points failed (0.96–1.11).
- Swapping pot, lid and rack moves our board from 0.402 to about 0.367 [E].
- Our board history: 0.405 → 0.402. Library_v3 averages 0.491 over the 26 pairs that have a public scan, so the spoon is inferred at about 0.18 [E] (M:`docs/work-log.md` around line 3705).

**Leaders' CD-O.**
- 26 Oct 08:50 UTC: richchentw 0.154, NVSimranPatil 0.170, Panav Raaj 0.112 (B:`docs/work-log.md` line 4361).
- richchentw improved from 0.228 (M:`docs/research/leaderboard-20261025-0720utc.json`) to 0.154 while their AUC stayed at 0.932 (M:`results/submissions/20261026-track3d/README.md`). That fits a weak link between the boards but proves nothing.
- Across teams, CD-O correlates with AUC at only −0.51 (Spearman), vs −0.97 for MPPE. Panav Raaj leads CD-O but is 17th on AUC (0.341) [M] (M:`docs/work-log.md` lines 3701–3704).

## 3. The current mesh plan (A + B "autokit")

**Plan** (B:`STATUS.md` 27 Oct 13:30; B:`docs/work-log.md` lines 4603 onward):
- **Stage 1:** a shared engine that never reads ground truth.
  - Committed so far: `io_gt.py` (an allow-listed loader that refuses scan, mocap and parquet paths), `refine.py` (per-frame pose refinement of the observed points) and `shell.py` (a directional thin-shell mesher).
  - Not yet committed: the part library and program language, gates v2, the integration run and the audits. Commit 9e908d8 is only a WIP snapshot.
- **Stage 2:** part programs written per object by agents (B) plus the engine's generic routes (A).
  - Selection stays free of ground truth (`obs_fidelity.py`).
  - Then one pre-registered scoring round against the public scans; oracle numbers are reported separately and never shipped.

**Expected gains [E]:**
- Cup ≈ 0.29, pot ≤ 0.32, boards ≤ 0.18, rack ≤ 0.40.
- CD-O board 0.40 → 0.20–0.28, and AUC +0.00 to +0.02 from smaller registration offsets (B README §6, P4/P5/P7).
- My own arithmetic, using the best measured fit per object (pot / lid / rack kit-of-parts, blue-cup lathe 0.291, beige-cup lathe about 0.30, everything else as now): about 0.31 cm [E].
- Reaching the leaders (≤ 0.15) would need about 0.14 cm on all 26 scanned pairs. The literature reaches that only with "generate, then fit to observations" methods, which we have never run [L] (B README §3).

**Costs:**
- Stage 1–2: cloud CPU, $0.
- Eval depth: about $2–4 GPU (`ops/jobs/eval_perc.sh`, ≈ 4 min per episode). It is only needed if your 22 Oct rule (re-fuse each eval mesh from that episode's own video) applies. A swap of meshes built from public episodes shares library_v3's frame and needs no eval depth (B:`docs/work-log.md` 07:35 vs 13:20 entries).
- Generative probe P1: about $4–8 (ceiling $12). It needs your permission to run third-party code and a licence choice.
- Swapping only the packed mesh: $0, plus about $0.7 if a pack box is used.
- Swapping the simulator copy too means GPU reruns, about $2–5 per episode per seed. A full 20-episode re-reference and retrain previously cost about $27–31 for the boxes plus about $1.5 to pack (M:`STATUS.md` 24 Oct entry).

**Risks:**
- Both generic-only probes were refuted (pot structure, dust pan). The pot needed the hand kit's axis; the generic axis fit was 5.9° off.
- The quality gate passed a mesh with its largest wall removed.
- A fitter run on the wrong object quietly returns a clean but wrong mesh (23 of 26 test runs).
- Nearly round meshes are unstable in yaw at registration (the pitcher precedent). Board identity and flips are unsolved.
- Swapping only the packed mesh loses the tracking/registration cancellation described in 1(c) (pot, boards, cup + rack: +0.02 to +0.07 per object).
- A single public-twin A/B is noise of about ±0.03.
- The "own reconstruction" rules question is still unsent (B README §7). Library_v3 itself was fused using the public scans to carve neighbouring objects (B:`docs/work-log.md` line 1521), so a ground-truth-free rebuild would also tidy compliance.

## 4. Verdict per board

**CD-O (separate board; does not rank Track 3):** a better mesh is essentially the whole lever.
- Pot / lid / rack swap: 0.402 → about 0.367 [E].
- Adding the blue-cup and beige-cup lathes: about 0.31 [E].
- Adding generate-then-fit: 0.20–0.28 [E, never run].
- Leaders are at 0.11–0.15. On the 25 Oct snapshot, 0.31 would rank about 7th and ≤ 0.25 about 4th–5th, up from 11th [E].

**AUC (ranking metric), through registration (b):**
- Ceiling if every mesh were scan-perfect: about +0.01 to +0.02 [E, from the −0.016 mean per object-episode, with the spoon unknown].
- Realistic swap of only the packed mesh: −0.005 to +0.01 [E]. The one real swap measured −0.0045 [M].
- The best targets:
  - **Blue cup:** symmetric, so yaw drift does not hurt it; slot 0 in five evals; offset 10 → 4.1 mm [D].
  - **Sweeper:** break its near-symmetry to remove the flip risk on evals 19 and 30, ≈ 0.034 per flip [M].
  - **Pitcher:** −0.22 object AUC [M], but the lathe failed on yaw stability.

**AUC, through tracking (c):** unmeasured [H]. It needs re-tracking and retraining (≈ $30–55 for all 20 episodes, one seed). It may gain +0.005 to +0.02 [E], or lose the cancellation.

**AUC, through the simulator copy (d, e):** the largest mesh-related effects measured.
- Per-episode swings of 0.1–0.57 (ep18, evals 10, 20, 25) [M].
- What remains: placements in evals 14 / 28 / 30 / 1, about +0.005 to +0.012 [E]; eval-10 stacking, +0.01 to +0.025 if the policy learns it [E].
- This needs watertight, correct cavities and bases, not leaderboard-grade CD-O.

**Context:** our best is 0.81391 (5th). 4th place (DDD) is 0.827, +0.013 away; 3rd is 0.865, +0.051 away.

**Suggested order:**
1. Build a registration-stability gate plus a seed × scan-resolution ensemble re-score of the stored public rollouts. CPU, $0. Reject a mesh if more than 10 % of 30 seeds land more than 5° from the median pose (M:`.../refcheck/README.md` §4.1). Run every candidate through it before it touches the AUC file.
2. Ship CD-O meshes separately ($0, or $2–4 for eval depth), once you decide on the 22 Oct per-episode rule.
3. Test the blue-cup lathe and a symmetry-broken sweeper in the AUC file only if the ensemble mean is positive. It is falsified if the ensemble mean Δ ≤ 0 or any flip appears.
4. Spend AUC money on policies and spoon perception before re-tracking with new meshes.

I wrote no files. The scratch folder `/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/nextsteps/` exists but is empty.