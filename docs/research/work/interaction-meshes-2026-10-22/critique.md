**Verdict: the plan's direction (observation-first fusion as the backbone, interaction rules as a gated add-on) holds up. But its decision metric, its gains and its priorities need correcting, and several of its own checks would not pass as written.** Labels: [M] measured with method inputs only, [D] diagnostic using public scans or mocap, [E] estimate, [H] hypothesis.

**New measurements from this review** (scripts in /tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/review2/: regdiag.py, regseeds.py, cdo_both.py, largest.py, ep_align.py, potsingle/)

- **N1 [D] The §0 CD-O table reproduces exactly.** Library 0.415 / 0.333 / 0.223 / 0.220 / 0.440 / 0.526 / 0.885 / 0.557; Design O 0.385 / 0.251 / 0.189 / 0.227 / 0.727. The kit packer's decimation (budget_mesh) changes CD-O by at most 0.005 cm, so the plan's decimation caveat can be dropped.
- **N2 [D] Kit pose registration offset.** I ran AUC.py `_register_object_body` on 3 seeds. Because our tracks were made with scan templates, the ideal answer is identity, so any offset is error. ADD_static = mean |Δanchor + (Rᵀ−I)p| over scan points:

  | Object | Library | Design O |
  |---|---|---|
  | lid | 7.6 mm | 14.0 mm |
  | pot | 6.8 mm | 11.5 mm |
  | board 1 | 2.8 mm | 4.3 mm |
  | board 2 | 3.7 mm | 4.2 mm |
  | dust pan | 5.9 mm | 3.4 mm |

  Other pot variants: ep27-only O pot 3.4 mm; O pot with band mask and no below-table carve (potbmnb) 2.8 mm, even though its CD-O is worse (0.634).
  - CD-O and registration move in opposite directions for the lid, board 1 and potbmnb.
  - The five pose leaderboards all depend on this registration. The plan only checks CD-O.
- **N3 [D] Registration flips.**
  - The library_v3 sweeper flips 178° about its long axis on 1 of 6 seeds (45 mm error). The v2 sweeper flips on 0 of 6, so the hand flattening made the shape more ambiguous.
  - The beige cup's 65–143° rotations are about its central axis. The kit README declares that spin unscored, so it does no harm.
- **N4 [M] Eval counts.** The two boards have 1 eval pair each (episode 25), not 2 each; the total of 36 pairs only adds up with 1 each. Weighting by eval pairs and keeping the pot on its fallback, the measured CD-O change of the §0 Design O meshes is −0.006 cm (−0.221 cm summed over 36 pairs). That is far below the "Gain 7" score.
- **N5 [M] All §0 Design O meshes fail S1's own watertight gate.** The 4096-face files are not watertight and have 21 to 146 components. The full-resolution files are watertight and single-body. CD-O barely notices (lid 0.382 vs 0.385).
- **N6 [D/M] The pot regression depends on the episode, not the truncation.**
  - Design O pot from a single episode, CD-O [D]: ep27 0.323 (better than the library's 0.440), ep41 0.746, ep44 0.809, ep2 0.740. All four together: 0.727.
  - The GT-free "unsupported share" ranks ep27 first [M]: 0.089 against 0.31–0.44.
  - The episodes are not misaligned [M]: rigid offsets between episodes are ≤ 0.4 mm and 0.2° (at the 2 mm voxel limit).
  - Depth noise σ is 0.2–1.1 mm (noise.json), so 2.5σ < 4 mm and the plan's σ-adaptive truncation would leave the pot unchanged.
- **N7 [M] Data.**
  - All 14 loc/depth/ep* directories have been empty since 11:01 UTC today.
  - The HF store (private; the proxy adds the auth) serves depth for all 18 public episodes I checked (0, 2, 11, 12, 13, 18, 21, 22, 26, 27, 31, 39–45) to this CPU session. ep11 is 877 MB. 17 GB of disk is free.
  - loc/v lacks video for ep24 (a copy exists only in interact/obs/v), ep0, ep26, ep42, ep43 and ep45.
- **N8 A spoon template already exists.** spoon/wooden_spoon.glb is a 3,224-face watertight parametric model (README dated 2026-10-13; frame A/B is a near-tie). The plan does not mention it.

**Corrections**

*Numbers*
1. **Not in the evidence JSON or local files:**
   - leaderboard 0.313 / 0.065;
   - "8 → 14 pieces";
   - "1.45%" (results.json passing cases top out at 0.91%);
   - "4.2 s, 0.61 GB";
   - "$2 per training";
   - ep24 "0.23–0.31" (STATUS gives 0.297 and 0.31);
   - "Design J 0.0–0.04 cm³" is the bleed case only; the ideal-depth case gave 0.45 / 1.16 cm³.
2. **Labels.** "89% of slot voxels vs 1% of solid wood" and the S2 "board 1 1%, board 2 0%" use slot and control boxes defined from the public scan, so they are [D], not [M]. The S2 gate statistic itself (false-free share on strongly observed inside voxels) was never measured. Board 2 silhouette coverage is only 51%.
3. **Unexplained-evidence gate.** "Others ≤ 0.024" covers only the dust pan, lid and board 1; board 2 was never measured. The "0.00 / 0.05" slot fill is silhouette plus the residual step, not silhouette alone. Without the silhouette, depth alone leaves 0.67 / 0.88 fill and 8.68 cm³ overlap.
4. **"Assembled overlap 1.0 cm³, below the 1.4 cm³ scan floor" is a warning, not a success.** The mocap scan floor is 0.68–0.88 cm³. Design O board 1 is missing 53.4 cm³ against 38.7 for v4 (volume 146.9 vs 207.4 cm³): real wood was removed.

*Scoring logic*
5. **Weight CD-O by eval pairs** (pot 6, blue cup 5, rack 5, spoon 10) instead of the unweighted 10-object mean. Then S1's "≥ 0.04 cm" target is reachable only through the cups, rack and pot, and the spoon dominates.
6. **Add the kit registration offset (N2) as a second acceptance metric for every mesh change.** It takes seconds per mesh. Rule: no worse on either CD-O or registration. Under that rule the Design O lid and pot fail today.
7. **The §0 meshes are not watertight (N5).** Make the split explicit: submit the decimated mesh, but build the simulator collision geometry from the full-resolution watertight mesh in the same body frame. A watertight 4096-face mesh with 2 mm walls is still unsolved.
8. **Replace S1's pot hypothesis (N6).** New [H]: weight or select episodes by GT-free evidence quality. Falsify with leave-one-episode-out on the pot, dust pan, blue cup and rack: weighting by unsupported share must beat all-episode fusion on both metrics for at least 3 of the 4.

*Rules*
9. **Per-object switches driven by [D] would leak the scans.** The public scans are of the same physical objects as the hidden ones. This applies to S1(d) "keep it for objects that pass", S3(d) if applied per object, and S4's scan-pose acceptance. Scans may decide only global method choices; every per-object switch must be a GT-free gate.
10. **G0's path check misses transitive contamination:**
    - library_v1–v4 were built with scan `--others`;
    - the loc/perc tracks were templated on the scans;
    - the prototypes used library_v2 as ROI and `--others`, and library_v4 as the silhouette colour source.

    Use a provenance manifest with input hashes and a deny-list that includes derived artifacts.
11. **Day 1's "baseline eval submission with the current pipeline" means v1–v4 meshes and tracks templated on them.** That contradicts §4. Base the insurance submission on a compliant pass-0 rebuild instead.
12. **Run perc2m before freezing any S1 or S3 threshold.** Every gate was calibrated on scan-templated tracks (ep24 relative error 3.6 mm).
13. **S7 rehearsal on twins is optimistic**, because v5 contains the twin episode. Use a leave-one-out v5.

*Ways interaction carving can make meshes worse*
14. **Track bias passes G1 and K≥5.** Examples: the ep0 lid flip (179°) and ep11's inner cup sunk 2.7 cm (static CV 0.13). Only the observed-carve-share gate defends against this, and it was tested once (ep0's relative pose on ep2 grids; 3.65% vs 0.91%). Add a bias-injection test and the real ep11 case.
15. **ep31's compliant bristles.** The overlap is persistent in the sweeper frame (171 frames above 1 cm³). The defects study found 18 cm³ carved at ≥3 frames, half of it real bristle (conflict 9 cm³). S3 checks only the rack side, and R2 may treat the 1–26 cm drag along the rack as an insertion. ep31 is the twin of eval episode 30.
16. **R2's halving prior is wrong outside cross-halving joints.**
    - ep13 cup-in-rack: 100% of the rack's overlap core is off-scan but only 3% of the cup's, so any split removes real cup.
    - ep11 nested cups: a straight vertical insertion, so R2 would split the walls.
    - Restrict R2 to cases with strong evidence on both sides, and add ep11/12/13 to S3's diagnostics. These episodes cover 12 of the 26 eval pairs of known objects.
17. **Thin walls.** After S1, walls are 1–2 voxels (real 1.4–2.6 mm), while penetrations are 6–10 mm. "Components unchanged" does not catch holes. Gate on an unchanged Euler characteristic and at least 2 voxels of material remaining.
18. **Gate claims per episode before summing them.** ep0's bad track claims 208 cm³ of the lid with our tracks.
19. **K ≥ 5 sampled frames at stride 2** leaves a thin margin against ep18's bristle contact (8 frames under mocap, i.e. 4 sampled).

*Interactions and defects the plan ignores*
20. **The spoon:** 10 of 36 CD-O pairs and 10 of 20 eval episodes.
    - In 7 eval episodes it is inside or among cavities with no public twin: pot (3, 5, 6), rack (15, 16), blue cup (32, 33). The blue cup is filled 37% (about 6 cm) up from the base, so a spoon in it hits a false floor.
    - Today's rules would throw away the spoon's own depth: hand capsules of 3 cm radius cover a handle while it is held, and a spoon lying on the table sits inside the 15 mm table band.
    - Start from the existing template (N8).
21. **Beige cup** (no base, IoU 0.13) and **pitcher** (cannot stand upright: base 0.1 cm², margin −11 mm) are outside S3 and S4's checks. Eval episodes 8 (beige cup + pot) and 20 (blue cup + pitcher) need them.
22. **Support and stability:**
    - Objects float 1–4 cm in our references.
    - Single-frame table planes span 2.8 cm (0.518–0.546 m) on ep23/24. S1, S4 and mkref need one robust plane per episode.
    - The ep24 "two hands snapping onto one board" issue the owner raised is not addressed.
    - S4 flattening can create registration flips (N3): add a GT-free ambiguity gate (the mesh compared with its own 180° rotations about its principal axes).

*Feasibility and cheaper options*
23. **Depth fetch list (N7).** S0 must re-fetch every episode, not just ep11, 12, 13, 21, 22 and 31. Fetch every 2nd frame as float16 (about 6 GB in total) and delete minimal/dl/ep24 (a 1.76 GB float32 duplicate). No GPU box is needed. Saved grids (obs/grids2, minimal/grids) already allow post-pass variants without depth.
24. **S8 with one seed cannot resolve the effect.** Repeat evaluations spread ±0.02–0.03, against effects of about 0.01–0.05, and ep25 is 1 of 20 pose episodes. Run S5(d)'s CPU replay of the ep24 end state first.
25. **S5 may need no evaluator decision.** Rollouts come from our own run of the kit's policy evaluator with our assets. Check `mkref --assets` before asking the owner (owner decisions 2 and 4).

**Top 5 next actions, in order**
1. **Re-baseline the acceptance metric (CPU, under 1 h):** CD-O weighted by eval pairs, plus the kit registration offset and flip test on ≥6 seeds, including the actual eval seeds (1_000_003·episode + 101·slot). Run it on v2, v3, v4 and every Design O variant, and adopt "no worse on either".
2. **Spoon first:** take the existing template, specify fusion rules that keep its depth (finger-scale hand masks; no table band inside its own silhouette, as obsfuse3 already does), run a GT-free ambiguity test, and ask the owner whether a fitted template counts as "reconstructing it ourselves".
3. **Re-fetch depth and run S1's falsification on the blue cup, beige cup, pitcher and rack before porting any code.** In the same pass, run the pot episode-weighting test on the saved grids (possible today).
4. **Adversarial test of the S3 gates (CPU, about 1 h):** inject 2/5/10 mm, 2/5/10° and 180° biases into the ep2 and ep24 tracks; run the real ep0, 11, 12, 13 and 31 cases; report the real material carved per object [D] and the thin-wall holes. Do not freeze S3 until it passes.
5. **Owner package before any GPU spend:** perc2m before freezing thresholds (≈$3–6 [E]); no insurance submission from v1–v4; and resolve S5 with a local `mkref --assets` check and a CPU replay instead of the single-seed S8.