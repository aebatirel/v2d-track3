# C1: further per-object CD-O wins on top of C0 (beige cup, dust pan)

**Status (2026-10-31 ~17:10 UTC).** Done; CPU only, $0.
- **C1 adopts two objects:**
  - beige cup = the T1 obs-lathe;
  - mini dust pan = the T2 generated pick, placed in the library_v3 frame.
- They touch 4 of the 36 pairs and no C0 object. Nothing from T3 is adopted.
- No verifier found a blocking item in any track. So in this step nothing was fixed, re-run or re-scored. Nothing has
  been packed or sent to focused-pascal (§9).

Tags: [M] measured without ground truth; [D] diagnostic, scored against public ground truth (scans, mocap) after
inference; [E] estimate; [H] hypothesis. Repo paths are relative to `docs/research/mesh-2026-10-26/` unless they start
with `meshes/` or `docs/`.

## 1. Answer
- **[E] board CD-O:**
  - pack 9a (C0 pot, lid, rack): 0.367;
  - pack 9a + C1: **0.333**. The beige cup gives -0.030 and the dust pan -0.004.
  - Also with C0's held-back blue cup: 0.300.
  - Brief's table: 0.338 would be 14th and 0.297 10th.
  - Model and assumptions are C0's: hidden scans = public scans; one-shot public CD-O at the eval seed
    (`c1_cdo_estimate.json`).
- **AUC guard [D]:** both C1 objects PASS on their public twins.
  - Combined configuration (pack 9a + C1) over 18 twins, rebuilt from stored runs (no new scoring): mean dAUC
    **+0.0091**, min -0.0092 (ep12, the C0 rack), dMPPE -0.074 cm, dRPE -0.103 cm, dSP-SR and dMP-SR 0.
- **The weakest pair is eval 8 (beige cup).**
  - No public twin has the beige cup together with the pot, and eval 8 has both.
  - Its rollouts were tracked with library_v3x.
  - Packing the beige cup on eval 10 only gives 0.346 [E] (§5, §9).

## 2. Per-object verdicts and the C1 choice
The rule is fixed precedence among ADOPTED candidates: T1 > T3 > T2 for the beige cup; for other objects, the single
adopted candidate, or T3 over T2 if both are adopted. No object had two adopted candidates. So the precedence never had
to break a tie, and nothing was chosen by comparing scores.

| Object (eval pairs) | T1 obs-lathe | T2 probe pick, library frame | T3 generate-then-fit | **C1 choice** |
|---|---|---|---|---|
| beige_cup (2) | **ADOPTED**: WIN both pairs, guard PASS | rejected: add_med 15.0 > 8.97 mm | rejected: add_med 21.7 > 8.97 / 7.51 mm | **T1 lathe** |
| mini_dust_pan (2) | - | **ADOPTED**: WIN both pairs, guard PASS | CD-O WIN, guard FAIL (mean -0.0056, min -0.0425 ep18) | **T2 pick** |
| white_pot (6) | - | - | CD-O WIN, guard FAIL (mean -0.0099, min -0.0416 ep45) | none (C0 pot stays) |
| blue_cup (5) | - | - | CD-O WIN, guard FAIL (min -0.0422 ep13) | none (library_v3; C0 cup held back) |
| water_pitcher (1) | - | rejected: add_med 28.4 > 9.97 mm | rejected: add_med 33.0 mm | none |
| white_pot_lid (1) | - | - | rejected: add_med 39.7 mm | none (C0 lid stays) |
| plastic_dish_rack (5) | - | - | rejected: CD-O 0.572, add_med 21.6 mm | none (C0 rack stays) |
| mini_sweeper (2) | - | - | rejected: CD-O, add_med, 5/30 flips | none |
| wooden_piece_1 / _2 (1 + 1) | - | - | rejected: CD-O, add_med, flips 7/30 and 25/30 | none |
| wooden_spoon (10) | not in C1 (no public scan) | | | none |

## 3. Files (adopted; both committed, byte-identical across build, scoring, AUC dir and git per the verifiers)

| Object | Path | sha256 | md5 | bytes |
|---|---|---|---|---|
| beige_cup | `cdo-sprint/C1/T1-beige-lathe/meshes/ep11_beige_cup_sep_g1.glb` (+ `.lathe.json`) | `60e398b0f8006c6608e40b1988047aa89e35533e8bb85906c36cf9f9f8370078` | `8c8be2b0747d234706913a2360e90570` | 653,516 |
| mini_dust_pan | `cdo-sprint/C1/T2-probe-picks/meshes/mini_dust_pan_k297_s42_lib.glb` (also HF store `aebatirel/v2d-store` `runs/cdo-c1-t2-20261031/place/`) | `2fb147b535c9f8b863b56ec80239f28809b10fe9ca881a10a5c724f209777d02` | `1976540525ecca181c9ed83ba953e165` | 5,585,744 |

**Pairs to replace** (kit roster, slot order; the rollouts and simulator assets stay unchanged):

| Eval (slot) | Object | Replaces (pack 7 / 9a) | Partner on that eval |
|---|---|---|---|
| 10 (1) | beige_cup | `meshes/library_v3/beige_cup.glb` (`f7309312...`, md5 `6226281f...`) | blue_cup (slot 0), library_v3 |
| 8 (0) | beige_cup | `meshes/library_v3x/beige_cup.glb` (`af327b80...`, md5 `ebea224c...`) | white_pot (slot 1), **C0 pot in pack 9a** |
| 19 (1) | mini_dust_pan | `meshes/library_v3/mini_dust_pan.glb` (`412a665e...`, md5 `c33fa411...`) | mini_sweeper (slot 0), library_v3 |
| 38 (0) | mini_dust_pan | same | none |

- Apply as for C0: replace the packed mesh byte for byte. The kit's `budget_mesh(4096, 4096)` runs at packing
  (fast_simplification 0.2.0, the version the [D] scores used; pin it).
- T2's verifier confirmed that pack 4's dust-pan rows on evals 19 and 38 equal `budget_mesh(library_v3)`. T1 confirmed
  that eval 10 packs library_v3's beige cup and eval 8 packs v3x's.

**Report-step files (this commit):**
- `c1_cdo_estimate.json` and `scripts/c1_estimate.py`: the [E] arithmetic.
- `c1_config.json` and `scripts/c1_config.py`: the pack 9a + C1 twin configuration, recombined from stored run JSONs.
- `NOTES.md`: the step log.
- Track folders: `T1-beige-lathe/`, `T2-probe-picks/`, `T3-gen-fit/`, each with PREREG, RESULTS, NOTES and verify.md.

## 4. Public-scan CD-O [D] and board estimate [E]
Each value comes from one scoring of the adopted file (kit-budgeted), at that pair's eval seed. The baseline per pair
is the value C0's estimate used for pack 7 (`results/baseline_library.jsonl`).

| Pair | Baseline CD-O cm | C1 CD-O cm [D] | delta | board delta [E] |
|---|---|---|---|---|
| eval 10 beige_cup | 0.85625 (library_v3) | 0.2475 | -0.6088 | -0.0169 |
| eval 8 beige_cup | 0.72995 (library_v3x) | 0.2549 | -0.4751 | -0.0132 |
| eval 19 mini_dust_pan | 0.3307 (library_v3) | 0.2587 | -0.0720 | -0.0020 |
| eval 38 mini_dust_pan | 0.3307 (library_v3) | 0.2601 | -0.0706 | -0.0020 |
| **C1 total** | | | | **-0.0341** |

The dust-pan values are the placed (packed) file's own scoring. T2's gate used the probe mesh's 0.2619 / 0.2592 as
pre-registered; either set gives -0.004.

| Configuration [E] | Board CD-O cm |
|---|---|
| pack 7 (measured board) | 0.402 |
| pack 9a (C0 pot, lid, rack) | 0.3667 |
| **pack 9a + C1 (beige both pairs, dust pan)** | **0.3327** |
| pack 9a + C1, beige on eval 10 only | 0.3459 |
| pack 9a + C0 blue cup + C1 | 0.3004 |

**Other registration gates [D]:**
- beige add_med 5.70 mm (library 6.97, v3x 5.51), 0/32 flips with symmetry taken into account;
- dust pan add_med 4.83 mm (library 5.65), 0/32 flips.

## 5. AUC guard [D] (public twins, our perception tracks, public scans in place of the hidden ones)
Rule (the same as C0's): mean dAUC >= -0.005, min dAUC >= -0.02, mean dMPPE <= +0.2 cm, mean dRPE <= +0.2 cm.

| Object | Twins | mean dAUC | min dAUC | mean dMPPE cm | mean dRPE cm | Verdict |
|---|---|---|---|---|---|---|
| beige_cup (T1) | 11 | +0.0080 | +0.0080 | -0.064 | -0.044 | PASS |
| mini_dust_pan (T2) | 18, 39, 40 | +0.0124 | -0.0014 (ep18) | -0.128 | +0.002 | PASS |
| white_pot (T3) | 0, 2, 26, 27, 41-45 | -0.0099 | -0.0416 (ep45) | +0.148 | +0.088 | FAIL |
| blue_cup (T3) | 11, 12, 13, 21, 22 | +0.0217 | -0.0422 (ep13) | -0.228 | +0.009 | FAIL |
| mini_dust_pan (T3) | 18, 39, 40 | -0.0056 | -0.0425 (ep18) | -0.031 | +0.106 | FAIL |

**Pack 9a + C1 on the twins** (`c1_config.json`; reported only, not a selection):
- Every twin's configuration equals a stored run:
  - C0's pack-9a run on the 14 C0 twins without the beige cup;
  - T1 `single_ep11`;
  - T2 `single_mini_dust_pan_ep18/39/40`.
- The C1 objects share no twin with pot, lid or rack, and the script asserts this.
- 18 twins: mean dAUC +0.0091, min -0.0092 (ep12), dMPPE -0.074 cm, dRPE -0.103 cm.
- The 4 C1 twins alone: +0.0113, min -0.0014 (ep18).

**What the guard does not cover:**
- **Eval 8 beige cup [H, untested].**
  - On eval 8 the beige cup is object 0. The kit's `_align_registered_scene` takes the scene offset from object 0, and
    the rotation from the first non-symmetric object, which is the pot (C0-swapped in pack 9a). So C1 changes eval 8's
    offset anchor while C0 changes its rotation anchor.
  - No public episode has the beige cup with the pot. ep11 (beige with blue cup) is the beige cup's only twin.
  - Separately, eval 8's rollouts were tracked with library_v3x, and the guard used only a library_v3-family track
    (T1 verify N2).
  - GT-free trimmed ICP [M] puts the lathe 2.4 mm / 5.2 deg from v3x and 2.6 mm / 8.8 deg from v3. These numbers are
    noisy, because the shapes differ.
  - Cheapest test: one ep11 run with beige = library_v3x on the same track, against base. Otherwise pack eval 10 first.
- **Eval 10 is covered structurally.** ep11 has the same two objects in the same slot order (blue_cup, beige_cup). This
  holds only while the blue cup stays library_v3.
  - If the C0 blue cup or E0's lathe is packed, the joint ep11 run (both cups swapped) is not measured.
  - C0's `single_blue_cup` already moves the beige cup's per-object AUC on ep11 (0.9334 -> 0.9361) and adds +0.214 cm
    dRPE.
- **Eval 19 is covered** by ep18 (mini_sweeper, mini_dust_pan, the same order). If any sweeper swap enters the same
  pack, ep18 needs a joint base/swap run first.
- **In-sample twins.**
  - The beige lathe was built on ep11, its only twin, so its guard is fully in-sample.
  - The dust pan was generated from an ep39 crop. On its out-of-sample twins it gives ep18 -0.0014 and ep40 +0.0233.
- **The board is not the twins.** The board scores simulator rollouts against the hidden scans, with the host's
  anchor. Its AUC change can differ in sign from the twins' change (precedent: the 26 Oct pitcher swap).

## 6. Hypothesis verdicts
- **H-BL (the adopted blue-cup lathe method transfers to the beige cup): survives [D].**
  - Result: WIN on both pairs (0.2475 vs the 0.836 threshold, 0.2549 vs 0.710), add_med 5.70 mm, 0/32 flips, ep11
    guard PASS.
  - Built with `lathe_obs.py` at its defaults (= the blue-cup g1 settings, which rebuild byte-identically). One
    GT-free addition: the M_sep frame mask (separated frames t0-62). The nested frames had put 5,891 points about
    30 mm below the base, which made the unmasked lathe 191 mm tall.
  - Whether the mask mattered is not measured: M_all and M_sephf were never scored.
- **H-GF (fitting a generated mesh to our observed points makes it better): not falsified by the pre-registered rule,
  but the fit created no new WIN [D].**
  - The rule's 3-WIN arm is met by pot, blue cup and dust pan. Their raw picks already pass the same gate, so the
    verdict says nothing about the fitting step.
  - Against the raw pick, the fit changes CD-O by mean -0.018 cm (median -0.011), better on 7/10. That arm is
    confounded by the uncontrolled decimation path: raw 100-400k faces -> 4k, against 12k -> fit -> 4k.
  - The fit is worse than raw on 3/10 objects (lid, blue cup, beige cup).
  - All 3 WINs fail the AUC guard.
  - `T3-gen-fit/gates.json` labels the verdict "SUPPORTED". A falsify-only rule can only return "not falsified",
    which is the reading here.
  - The held-out-sign vs CD-O-sign agreement (9/10) is weak evidence. The marginals allow at most 9, and its
    permutation probability is about 0.067 [M].
- **H-T2 (placing a generated pick in the library_v3 frame makes it pose-safe): survives for the dust pan only;
  falsified for the pitcher and the beige cup [D].**
  - Placement lowered ADD for all three (7.47 -> 4.83, 33.4 -> 28.4, 21.8 -> 15.0 mm). The pitcher and the beige cup
    stay 2-3.5 times the library's ADD.
  - This replicates the 30 Oct diag (`diag-2026-10-30/sam-placement-verify/m7_*`, kit-like ADD 4.3 / 23.8 / 16.2 mm).
    It is not an independent test.

## 7. Integrity and provenance
- **Pre-registration before any scan read** (verified from the origin reflog and file times):

  | Track | PREREG | first scan read | results | verify |
  |---|---|---|---|---|
  | T1 | `4c757ea`, pushed 15:42:23 | 15:42:46 | `c6cbc9e`, `9f35c0d` | `26b2f76` |
  | T2 | `6f71234`, pushed 16:24:49 (text first in WIP `0e64c7f` 16:23:57) | 16:25:01 | `9e41d09` | `507709c` |
  | T3 | `2d2a8ee`, pushed 16:02:53 | 16:02:59 | `66d60c0` | `d8df274` |

- **Scorings used** (one per distinct mesh, never re-scored):
  - T1: 1 `mesh_metric` and 2 `score_registered` runs;
  - T2: 3 `mesh_metric` and 6 `score_registered` runs;
  - T3: 10 `mesh_metric` and 20 `score_registered` runs (14 base runs reused from C0).
  - Each verifier also re-ran one ep11 or ep18 twin, byte-identical, and chose nothing from it.
- **Construction and choices are GT-free** in direct reads. The verifiers grepped every construction script and
  re-built the beige lathe, the dust-pan placement and one T3 fit byte-identically.
- **Disclosures carried from the tracks:**
  - T1 read the README's scan-extents table (beige 16.9 cm tall) before choosing the mask.
  - T2's three objects were chosen post hoc on the probe's [D] CD-O, and its outcome was already known from the
    30 Oct diag.
- **Provenance tier: the same as library_v3, with the owner's decision O1 open.** Under a scan-free standard both
  meshes need the same re-track or rebuild as the C0 blue cup.
  - Beige lathe inputs: sweep tracks templated on library_v2; obs ROI and `--others` from library_v3; G1 hands. It
    also inherits `lathe_obs.py`'s constants. The C0b audit (`C0b/AUDIT.md`, records 107, 117, 118, 121, 128, 131)
    flags them: they were set inside or alongside the 26 Oct scan-scored lathe loop (§3.3), or have no derivation.
    Its non-binding checks (e.g. TIE) were done on the blue cup, not the beige.
  - Dust pan: placed by ICP onto library_v3, which is on the provenance denylist.
- **The GT-free obs_fidelity selector pointed the wrong way in T1 and in T2** (T1: library meshes 3.41 mm against the
  winning lathe's 5.82; T2: it preferred the probe pose on 6/6 twin pairs). Do not use it to choose between a lathe
  and a library mesh, or to choose a frame.

## 8. Non-blocking verifier findings (none blocking; listed, not fixed)
**T1** (`T1-beige-lathe/verify.md`)
- N1 provenance (§7).
- N2 eval-8 frame (§5).
- N3: `results/pack_check.txt` omits the script's meaningless `_1` rows. Re-running reproduces the conclusion.
- N4, wording:
  - "64 frames t0..62 (even)" means census frames 0-63, with points from the 32 even frames;
  - M_all was built before the mask was declared. M_sep and M_sephf were built after, all GT-free.
- N5: joint ep11 with the blue cup, and the mask effect, are not measured.
- N6: STATUS and work-log entries (done here).

**T2** (`T2-probe-picks/verify.md`)
- Replication, not a test (§6).
- The gate used the probe CD-O as pre-registered; the placed copy's own values also pass.
- Eval-8 beige ADD threshold: 7.51 mm (v3x) would be the stricter one. The pick fails either way.
- ep39 is in-sample.
- ep18 needs a joint run if a sweeper swap is packed.
- A better [D] dust pan (gen/hy21 k297, 0.230 / 0.233) exists but was not the GT-free pick. Choosing it now would be
  selection on [D], so it is listed only.
- The fidelity gap is 0.67-2.0 mm, not 0.5-2.0 mm.

**T3** (`T3-gen-fit/verify.md`)
- The falsifier cannot credit the fit.
- `gates.json` "SUPPORTED" should read "not falsified".
- The 9/10 sign agreement is weak.
- The hold-out is interleaved 10-frame blocks, so it mainly detects noise fitting.
- The self-intersection limit was checked on the dev pot only. The dust pan (527), rack (389) and sweeper (355) would
  fail it; this is moot because nothing is adopted.
- The `2d2a8ee` message is inaccurate (its files entered 4 s earlier in `f0a1e2c`, byte-identical).
- Small rounding mismatches.
- The run JSONs lack per-object mesh hashes. Add them in future guards.
- [H] The ep13 175 deg blue-cup registration may be upside-down rather than a spin.

## 9. Failures and open items
**Failures:**
- T3 found no adoptable mesh.
  - Dev fit versions v0-v4 failed the GT-free check; v5 was frozen.
  - pymeshlab hole closing does not load (libOpenGL), and 8/10 fitted meshes are not watertight.
  - Self-intersections rose.
  - The stiff fit does not repair the probe's biased Sim(3) placement (add_med 20-85 mm).
  - `mesh_metric.py run --seeds` uses only max(2, 6 - n_eval) of the given extra seeds; the 30-seed flip counts came
    from `scripts/score.py`.
- H-T2 is falsified for the pitcher and the beige cup.
- T1's GT-free prediction (that H-BL would fail) was wrong.
- The scored beige lathe has known GT-free flaws:
  - its axis is 4.3 deg from the more self-consistent M_all axis;
  - 19 % of the points became a 92 x 104 x 93 mm appendage shell.

**Not measured:**
- the eval-8 pot + beige coupling and the v3x frame;
- joint runs if the blue cup or a sweeper swap is packed;
- whether T1's frame mask mattered.

**Open decisions (for the owner / score session; this step sends nothing):**
1. Pack C1 (beige cup on evals 10 and 8, dust pan on evals 19 and 38) on top of pack 9a: 0.367 -> 0.333 [E]. Or pack
   beige on eval 10 only until the eval-8 coupling is tested: 0.346 [E].
2. Provenance O1 for both meshes (§7).
3. The ep11 v3x-frame run (one `score_registered` scan read), if eval 8 is wanted with evidence.
4. If the blue cup (C0 or E0) or any sweeper candidate joins the same pack, run the joint ep11 / ep18 twin first.
5. `meshes/library_c1*` folders were not created. The two files above are the hand-off, with the pair table in §3.
