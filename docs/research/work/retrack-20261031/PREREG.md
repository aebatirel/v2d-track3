# Re-track with per-episode meshes: pre-registration (P_o' vs P_o, 20 public episodes)

**Written 2026-10-31, 18:58–19:05 UTC** (focused-pascal, CPU only), **before any P_o' result**: the per-episode meshes
are not delivered yet, no P_o' track exists and no box is launched. The orchestrator commits this file unchanged
before the launch. Any later change goes into a dated "Amendment" section with its reason, before the result is read.
Labels: [M] measured, [E] estimate, [H] hypothesis or threshold chosen here.

Proposed by the score-status session after the owner asked how to improve perception, and agreed there. Build and
mock: `BUILD.md`. Job strings and cost: `JOBS.txt`. Verdict tool: `rtk_verdict.py`. Phase 1 background:
`../leak-decomp-20261030/phase1/{RESULTS,BUILD,JOBS}`.

## 1. Question and hypothesis
Phase 1 measured the template leak at the reference level. Tracking with the true shape (the organiser scans) and
submitting it gains R\*(P_s) − R_lib(P_o) = **+0.034** (16 / 20 episodes), and +0.039 in the \* convention [M]. Those
are oracle upper bounds: the scans are ground-truth geometry.

- **H-RT** [H]: tracking with GT-free per-episode meshes improves our references. The meshes are built by the mesh
  session's clean C0b/E0b method from each public episode's own video. The arm also submits the same mesh (lib
  convention). The gain is measured as registered AUC over library_v3 templates.
- **Falsified** by a FAIL under §4.
- **Prior** [E]:
  - The gain is below +0.034, because the meshes sit between library_v3 and the scans in shape quality.
  - It can be negative where a new template breaks frame-0 initialisation. The scans did that on ep0 (−0.87).

## 2. Arms
| | P_o (control) | P_o' (treatment) |
|---|---|---|
| runs | `20261030-orcP1{a,b,c}-87fc869` (Phase 1, stored; **not re-run**) | `<date>-rtk{A,B}-<sha7>` (JOBS.txt) |
| tracks | `results/leak_p1/ep<N>/perc2/` | `results/leak_p1/ep<N>/perc2/` of the rtk runs |
| templates | `meshes/library_v3/<obj>.glb` | `meshes/rtk_e0b_public/ep<N>/<obj>.glb` where delivered, else library_v3 |
| submitted mesh (lib convention) | library_v3 | the mesh the arm tracked with |
| commit | 87fc869 | the launch commit (perc2 code byte-identical, §5 (e)) |
| everything else | depth caches, hands, KF_MIN=120, Grounding DINO, perc2 settings, RTX PRO 6000, env snapshot pt2.11-cu130-py313-20261020 | identical (§5) |

The P_o scores are committed: `scores/R_Po.json` (LIB_EP_DIR unset).
- Every episode's R and per-object AUC equal Phase 1's stored lib numbers (`phase1/scores/xstar_trk_Po.json`) on all
  20 episodes [M].
- The track md5s are equal too.

## 3. Measurements
- **R_e**: registered ADD-AUC vs public mocap in the **lib convention**, computed by `tools/leak_p1.py score`.
  - It uses Phase 1's kit chain, `tools/xstar_fit.py` `kit_X` and `score_track`.
  - The kit registers the tracked mesh onto the public scan, budget 4096/4096, seed 1 000 003·ep + 101·slot.
  - Then: body conversion, frame-0 scene alignment, and the declared symmetries (cups: axis; lid: half turn).
  - Rounded to 4 decimals.
- **RPE_e**: the kit's registered RPE (cm), on the same aligned poses, rounded to 4 decimals.
  - It is 0 by construction on the 7 single-object episodes (39–45).
- **dR_e** = R_e(P_o') − R_e(P_o), and **dRPE_e** likewise, from the rounded values. RPE is lower-is-better.
- **Changed episode**: at least one object's P_o' template md5 differs from P_o's (library_v3).
  - An episode with nothing delivered, or only byte copies of library_v3, enters the rule with dR_e = dRPE_e = 0. It
    tested nothing.
  - Its measured values are reported as the cross-box control. This clarifies the agreed rule (§4) so that cross-box
    noise on unchanged episodes cannot count as wins. It can only make PASS harder [H].

Control values [M] (`scores/R_Po.json`), R / RPE cm:

| ep | objects | R(P_o) | RPE(P_o) | | ep | objects | R(P_o) | RPE(P_o) |
|---|---|---|---|---|---|---|---|---|
| 0 | pot, lid | 0.9620 | 1.3825 | | 24 | board1, board2 | 0.8117 | 0.9832 |
| 2 | pot, lid | 0.9866 | 1.4386 | | 26 | rack, pot | 0.9717 | 1.2928 |
| 11 | blue, beige | 0.8978 | 1.7390 | | 27 | rack, pot | 0.9605 | 1.1550 |
| 12 | blue, rack | 0.9662 | 1.1393 | | 31 | sweeper, rack | 0.7998 | 1.9084 |
| 13 | blue, rack | 0.9595 | 1.3872 | | 39 | dust pan | 0.9602 | 0 |
| 18 | sweeper, dust pan | 0.9144 | 4.0676 | | 40 | dust pan | 0.9570 | 0 |
| 21 | blue, pitcher | 0.8325 | 1.2549 | | 41 | pot | 0.9910 | 0 |
| 22 | blue, pitcher | 0.8707 | 1.2229 | | 42 | pot | 0.9903 | 0 |
| 23 | board1, board2 | 0.0414 | 14.1797 | | 43 | pot | 0.9477 | 0 |
| | | | | | 44 | pot | 0.9967 | 0 |
| | | | | | 45 | pot | 0.9795 | 0 |

Mean of 20: R 0.88986, RPE 1.6576 cm, MPPE 1.8999 cm [M].

## 4. Rule (fixed here)
**PASS** iff all four hold:
1. mean over the 20 episodes of dR_e **≥ +0.01**;
2. dR_e **> 0 on ≥ 12 of 20** episodes (dR_e = 0 does not count);
3. **no episode with dR_e < −0.03**;
4. mean over the 20 episodes of dRPE_e **≤ 0** cm.

**FAIL** otherwise.

**INCOMPLETE** applies if any episode has no P_o' track, a failed arm (rc ≠ 0 or no poses) or a bundle that is not ok.
- Rerun only those episodes, on the same commit and the same delivery (VALIDATION.json unchanged; JOBS.txt "Rerun").
  No other episode is rerun or replaced.
- If an episode fails again with a template-related cause (perc2 errors while loading or registering the delivered
  mesh), it counts as failed: R_e(P_o') = 0, so dR_e < −0.03 and the verdict is FAIL. The new template broke
  tracking, which is a real harm.
- An infrastructure cause (download, HF 429, a dead host) is rerun again.

**INVALID** applies if the arms differ in anything but the templates (§5).
- There is no reading. Fix the cause and rerun the affected episodes, or all of them if the code or the delivery
  changed.

**Precedence**: INVALID > INCOMPLETE > PASS / FAIL.
- Tool: `rtk_verdict.py`. Exit codes: 0 PASS, 1 FAIL, 2 INCOMPLETE, 3 INVALID.
- 14 fixture cases behave as specified (`mock/out/verdict_tests.txt`) [M].

Per-object readings are reported but do not change the verdict. Nothing is adopted per object or per episode after
the reading. A partial adoption would need its own pre-registration and a fresh test.

## 5. Identity checks (INVALID if any fails; from the bundles, poses and git)
- (a) **Depth**, per episode: the store path, bytes, shape and frame-0 sha256 are equal to P_o's (= `phase1/inputs.tsv`).
  The cache is reused on both arms.
- (b) **Hands**: the md5 of `hands.npz` and `hands_refined.npz` are equal.
- (c) **Inputs**: the objects (slot order) and the frame count are equal.
- (d) **Camera**: world_T_cam of P_o' vs P_o on every frame differs by ≤ **0.1 cm** and ≤ **0.05°** [H].
  - Phase 1 measured ≤ 0.077 cm / 0.03° between boxes and commits (ep13) and ≤ 5e-8 elsewhere.
  - VO does not depend on the template (camera diff 0.0 between P_o and P_s on the same box) [M].
- (e) **Code**: `pipeline/perc2.py`, `pipeline/det_rules.py` and `ops/box/` are byte-identical between 87fc869 and the
  P_o' commit (git diff).
  - The P_o bundles carry 87fc869; the P_o' bundles carry the launch commit.
  - The env snapshot (pt2.11-cu130-py313-20261020) and the GPU model (RTX PRO 6000) are checked by hand from the create
    strings and the job.log `gpu` line, and recorded.
  - perc_leak.sh and leak_p1.py differ only by the opt-in. With LIB_EP_DIR unset it is byte-identical in effect
    (BUILD.md §3).
- (f) **perc2 settings**: KF_MIN=120 (run.json), Grounding DINO loaded on both arms (gdino), HF_HUB_OFFLINE=1, SPLIT
  public, template kind 'library' (no scan) on both arms.
- (g) **Templates**:
  - For each object, the P_o' bundle records source 'episode' iff VALIDATION.json lists `ep<N>/<obj>.glb`, with that
    md5.
  - Otherwise the source is library_v3, with P_o's md5.
  - `templates_as_delivered` is true.
- (h) **Scoring**: each arm was scored with the mesh it tracked with (score mesh md5 = bundle template md5).
- (i) **Delivery**: VALIDATION.json has status pass or flagged, and every mesh has a provenance tier.

## 6. Integrity (CLAUDE.md)
- **Public episodes only.**
  - P_o' inference reads no ground truth. perc2 reads mocap only in its own scoring block (`perc2.py:502-542`), which
    runs after `poses.npz` is written (`:493`). Before that it reads only the object names, slot order and row count from
    the episode parquet (`:61-62, :86`), which CLAUDE.md allows.
  - `perc_log_inference.txt` is cut before the first scoring line (`' AUC |anchor:|] DONE'`). The bundle tar leaves
    `result.json` and `log.txt` out.
  - `leak_p1.py score` reads mocap only on this VM, after inference.
  - The rtk outputs live under `runs/<rtk id>/results/leak_p1/`, which `tools/no_oracle.py` refuses by name.
- **GT-free meshes.**
  - The validator cannot prove GT-freeness. `tools/rtk_mesh_check.py` records each mesh's MANIFEST provenance tier
    verbatim in VALIDATION.json, and it is copied into the work log before launch.
  - The test asks for the **scan-free C0b/E0b method**. If the MANIFEST states that a delivered mesh uses mocap, scan
    geometry or scan-derived constants beyond what library_v3 already carries, the reading is **INVALID** as a GT-free
    test. Examples: C0's MK_R0 marker-ball radius prior, or scan-informed wall thicknesses that C0b did not remove.
  - It may still be reported as a diagnostic.
  - The validator flags tier wording that mentions scan / mocap / oracle / GT for a human to read.
  - The library_v3 fallback (tier P1, fused along scan-templated tracks; on the deny-list) is the owner-accepted status
    quo and is shared by both arms.
- **No tuning on eval**: nothing here reads an eval episode. The eval re-track that PASS would buy reads no eval score.
- **No tuning on this result**:
  - The delivery is used as delivered.
  - No mesh is swapped back to library_v3 after a score is seen.
  - The thresholds and the 12/20 bar are fixed above.

## 7. What PASS buys, what FAIL leaves
**PASS** buys the following, each step on the owner's go:
- **Eval re-track** of the 20 eval episodes with the E0b meshes (the mesh session's eval packaging: one mesh per
  object) as tracking templates. This is ~$2–4 [E] on 1–2 boxes.
- **References rebuilt** in the pack-10 retrain from those tracks. The submitted mesh = the tracking template (lib
  convention).
- **Frame gate first**: the E0b meshes vs the simulator's bodies (library_v3), using the validator's frame report.
  - A flagged object needs the simulator asset built from the same mesh (or the measured transform) before any
    training.
  - A reference in the E0b body frame on a library_v3 body would shift every scored pose.
- **The pack-10 swap rule scores against both references**: the old library_v3-tracked one and the new E0b-tracked one.
  - Metrics: sim_vs_ref, the GT-free RPE failure rate (> 5 cm) and the median RPE.
  - A reference change then cannot hide a policy regression, and a policy is swapped only if it wins on the agreed rule
    against both.
- **Value** [E]: Phase 1's oracle bound (true shape tracked and submitted) maps to +0.012–0.016 LB on the twin evals.
  The measured mean dR on the public twins, through the PLAN §2 map, gives the expectation for this mesh quality.

**FAIL** leaves:
- library_v3 stays the eval tracking template. No eval re-track.
- E0b meshes can still be swapped in as **submitted meshes only** (pack 9a-style), under their own registered-AUC guard
  and CD-O reading. That decision is separate from this test.
- The per-episode, per-object readings go to the mesh session (which shapes helped or hurt tracking).
- The template lever stays open only for better meshes, or for a per-object design pre-registered anew.
  Phase 1's oracle bound (+0.034) is unchanged by a FAIL.

**INCOMPLETE** → rerun the listed episodes. **INVALID** → fix, then rerun.

## 8. Noise floor [M]
Phase 1's P_o repeat (o vs o2: same box, cache and commit; 10 twins: 2, 11, 12, 13, 18, 21, 24, 27, 31, 39), scored
here in the lib convention (`scores/R_Po2_noise.json`):
- **R**: mean |Δ| 0.0017, max 0.0136 (ep27), RMS 0.0044; 6 / 10 episodes exactly 0.
- **RPE**: mean |Δ| 0.0019 cm, max 0.0077 cm. **MPPE**: mean |Δ| 0.016 cm, max 0.116 cm.
- **\* convention** (RESULTS.md): mean 0.0012, max 0.0063.
- The PASS margin (mean +0.01) is 5.9× the mean |Δ|. The −0.03 floor is 2.2× the largest repeat difference.
- **Cross-box noise is not measured** (Phase 1 risk 8). The unchanged episodes measure it in this run. rtk_verdict.py
  prints a NOTE when one of them moves by more than 0.0136, and the margins are then read with that noise.

## 9. Power and coverage [E]
- If the delivery covers E0's objects (pot, lid, rack, blue cup), 15 episodes change.
  - ep18, 23, 24, 39 and 40 (sweeper, dust pan, boards) do not.
  - Criterion 2 then needs 12 of the 15 changed episodes to improve, which is 80 %.
  - Criterion 1 needs a mean of +0.0133 over the changed ones.
- With the beige cup (C0b extended to it), ep11 changes in both objects.
- The pitcher (ep21, ep22: Phase 1's largest template lever, +0.265 per object with the scans) is not in E0's scope.
  Without it, the largest known gain is out of reach of this test.
- That is a property of the delivery, not a reason to change the rule.

## 10. Files
- `scores/R_Po.json`: the control, LIB_EP_DIR unset.
- `scores/R_Po2_noise.json`: the noise floor.
- `scores/R_Po_v3copy_check.json`: library_v3 byte copies given as per-episode meshes. Identical outputs on all 20
  episodes [M].
- `scores/R_Po_partial_check.json`: the switch acts on the registration. It moves ep2's white_pot by 2° / 3 mm on the
  unchanged P_o track: R 0.9866 → 0.9626 [M, mechanics only].
- `po_bundles/`: the 20 Phase-1 P_o bundles (single-file downloads, 31 Oct ~18:55 UTC).
- After the run: `scores/R_Pop.json`, `verdict.{json,txt}`, then RESULTS.md.
