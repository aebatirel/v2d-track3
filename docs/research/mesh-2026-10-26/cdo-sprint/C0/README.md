# C0: packed-mesh swap of pot, lid, rack (and blue cup) for the CD-O board

**Status (2026-10-31 ~16:45 UTC, stage 4 of 4).** Done; CPU only, $0.
- The AUC guard adopted all four objects under the frozen rule.
- **What ships is three objects: pot, lid and rack** (pack 9a, built by focused-pascal as 50004a7, 12 of 36 pairs).
  The blue cup is held back unless the owner includes it.
- Pot, lid and rack carry a scan-derived marker-ball prior (§6, flag F1). This goes to the owner before the pack 9a
  upload.

Tags: [M] measured without ground truth; [D] diagnostic, scored against public ground truth (scans, mocap); [E] estimate;
[H] hypothesis. Repo paths below are relative to `docs/research/mesh-2026-10-26/` unless they start with `meshes/` or
`docs/`.

## 1. What C0 is
- **The swap.** C0 replaces the **packed (submitted) mesh** of four objects in pack 7. The simulator copies and the
  rollouts stay unchanged.
- **Where the meshes come from.** Each was already built and already scored once against the public scans [D], on
  26-27 Oct. Each was picked under GT-free rules (obs_fidelity), but only pot, lid and rack had rules pre-registered
  before their scans were scored (flag F3).
- **Frame.** All four were fitted to our stereo points along library_v3-anchored tracks, so they sit in library_v3's
  object frame within a few mm, except the blue cup (§6, F5).
- **Why the AUC guard.** The packed mesh also sets the kit's registration (scan to our mesh). That registration defines
  the body frames of the pose boards (AUC, SP-SR, MP-SR, RPE, MPPE). So C0 was gated by a pre-registered AUC guard on
  the 15 public twins: `PREREG.md`, commit `081b37e`, pushed before any ground truth was read.
- **Stages.**
  1. Assembly, MANIFEST and PREREG (`081b37e`).
  2. 51 `score_registered.py` runs and the verdict (`edb4ffa`, `d495956`).
  3. Verifiers: `verify_handoff.md` (`694dc73`), `verify_0.md` (`72aadba`), `verify_1.md` (`88d2a79`).
  4. This README and the fixes (this commit).

## 2. Final set

| Object | AUC guard verdict (`guard_result.json`) | Ships in pack 9a | Pairs |
|---|---|---|---|
| white_pot | ADOPTED | **yes** | 6 (eval 1, 3, 5, 6, 8, 28) |
| white_pot_lid | ADOPTED | **yes** | 1 (eval 1) |
| plastic_dish_rack | ADOPTED | **yes** | 5 (eval 14, 15, 16, 28, 30) |
| blue_cup | ADOPTED | **no, held back** | 5 (stays library_v3) |

**C0-final for packing = {white_pot, white_pot_lid, plastic_dish_rack}.**
- **Why the blue cup is held back.** The score session and focused-pascal decided this at ~16:20 UTC. The blue cup's
  `obs_fidelity.py` selector was written after its lathes were scored against the scan, and it picks the lowest-CD-O
  of the 12 blue-cup lathe records. So the blue cup does not meet "picked GT-free under pre-registered rules".
- **This is a deviation from PREREG §5** ("C0-final = the adopted objects. There is no other selection."). It was made
  for integrity, not on scores. Nothing was added and no mesh was re-selected.
- The blue cup ships only if the owner explicitly includes it. The planned replacement is the E0 eval-built lathe
  (`cdo-sprint/E0/`).
- **Eval 8 beige cup.** The pot's eval-8 pair comes from `meshes/library_c0x`, which is library_v3x. That keeps pack 7's
  v3x beige cup on eval 8.

## 3. Files
| What | Path | sha256 |
|---|---|---|
| MANIFEST (36 pairs; status and flags updated in stage 4) | `cdo-sprint/C0/MANIFEST.json` | `5a87a85392cfebc7d3fa0fdd96c9c3f1819a7bee639fd88936f838ca5ef8cb7c` |
| frozen MANIFEST at PREREG (in `status_history`) | `git show 081b37e:...C0/MANIFEST.json` | `22209582f5698543a9220ff1dcdaeeb3e4605dcef30bea56761d9596950c55b5` |
| white_pot | `results/prim/meshes/white_pot_ep41_fit.glb` | `355ad72e397e1080c0c8b066ac83efd1f6536eae6048497f11198fe8aaffc263` |
| white_pot_lid | `results/prim/meshes/white_pot_lid_ep2_fit_v2.glb` | `0bac47f4b86e9ae36b082ffde7e04ce29bf1170481e02151d4cfbdb393c5a53b` |
| plastic_dish_rack | `results/prim/meshes/plastic_dish_rack_joint_v2.glb` | `c22f504ccb8855418c0cb15e44ba4f394e5e2f8b696b17ce937ab7294743dc02` |
| blue_cup (held back) | `cdo-sprint/C0/meshes/ep21_blue_cup_g1.glb` (+ `.lathe.json`) | `81a201cb2332516191937c80fb4993cea38fed93ba2332674a2cb3d282f129f1` |

- **Ready-to-pack folders.** `meshes/library_c0` is library_v3 with the 4 files swapped; `meshes/library_c0x` is
  library_v3x with the same 4 swaps (commit `5cce3d2`). Each differs from its base in exactly those 4 files.
  - md5 of the swapped files: pot `0264da83`, lid `35727a10`, rack `bbca8ec0`, blue cup `9e3a74fd`.
  - For pack 9a, take only pot, lid and rack from them.
- **How to apply.** Replace the packed mesh of each swapped pair (`MANIFEST.json` `pack_9a.swapped_pairs`, or
  `in_pack_9a: true` per pair) with the file above, byte for byte.
  - Leave the simulator assets and rollouts alone.
  - The kit's `budget_mesh(4096, 4096)` is applied at packing as for every mesh (deterministic; fast_simplification
    0.2.0). Pin that version.
- **Other files.**
  - `roster.json`: the kit's 36-pair roster.
  - `cdo_estimate.json`: the [E] arithmetic.
  - `frame_check.json`: centroid, axes and surface distance against library_v3.
  - `guard_result.json` and `AUC_RESULTS.md`: the verdict and full tables.
  - `auc/`: the 51 run JSONs.
  - `pack9a_config.json`: the shipped configuration rebuilt from the stored runs.
  - `scripts/`: `build_c0`, `frame_check`, `run_auc_guard.sh`, `guard_eval`, `report_auc`, `verify_inputs`,
    `pack9a_config`, `stage4_manifest`.
  - `NOTES.md`: the step log.

## 4. Public-scan CD-O [D] and board estimate [E]

Each figure is one scoring per mesh (26-27 Oct, kit-budgeted mesh), matched to the file by sha1[:16].

| Object | eval pairs | CD-O cm, library_v3 -> C0 | ADD mm | flips | board delta [E] |
|---|---|---|---|---|---|
| white_pot | 6 | 0.4371 -> 0.3417 | 6.67 -> 3.05 | 0 / 8 | -0.0159 |
| white_pot_lid | 1 | 0.4211 -> 0.2199 | 8.12 -> 4.46 | 0 / 6 | -0.0056 |
| plastic_dish_rack | 5 | 0.5551 -> 0.4560 | 5.99 -> 5.37 | 0 / 7 | -0.0138 |
| blue_cup (held back) | 5 | 0.5233 -> 0.2906 | 9.97 -> 4.09 | 0 / 7 | -0.0323 |

**Board CD-O [E]:**
- **pack 9a (pot, lid, rack): 0.402 -> 0.367 cm.** Under the brief's table that does not reach 14th (0.338).
- With the blue cup as well: 0.334 cm. The blue cup carries 48 % of the 4-object gain.

**How the estimate is built.** Board = pair-weighted mean over the 36 eval pairs. The spoon (10 pairs) is inferred at
0.182 from the board (pack-7 non-spoon mean 0.4865, with v3x for the eval-8 beige cup). It assumes:
- the hidden scans match the public ones;
- the [D] values hold at the eval seeds.

**Support.** One calibration point (n = 1): pack 3's eval-8 beige swap was predicted at -0.0035, and the board moved
0.405 -> 0.402 (verify_1 N8).

**[H] Marker balls (F1).** The balls are a small share of the surface, so their effect on these CD-O values is
probably small. This is untested.

## 5. AUC guard [D] (public twins, our perception tracks, public scans in place of the hidden ones)

**The rule** (PREREG §5, frozen): per swapped object, over its twins, (single swap) - (base library_v3) must give:
- mean dAUC >= -0.005;
- min dAUC >= -0.02;
- mean dMPPE <= +0.2 cm;
- mean dRPE <= +0.2 cm.

**Runs.** 51 runs, 51/51 OK, 34.5 min wall on this 4-core VM, $0. verify_1 re-ran 4 of them and got byte-identical
output.

| Object | twins | mean dAUC | min dAUC | mean dMPPE cm | mean dRPE cm | dSP-SR / dMP-SR | verdict |
|---|---|---|---|---|---|---|---|
| white_pot | 0, 2, 26, 27, 41-45 | +0.0030 | -0.0159 (ep2) | -0.057 | -0.108 | 0 / 0 | ADOPTED |
| white_pot_lid | 0, 2 | +0.0055 | 0.0000 | -0.079 | -0.121 | 0 / 0 | ADOPTED |
| plastic_dish_rack | 12, 13, 26, 27, 31 | +0.0158 | -0.0092 (ep12) | -0.043 | -0.097 | 0 / 0 | ADOPTED |
| blue_cup | 11, 12, 13, 21, 22 | +0.0241 | -0.0049 | -0.249 | +0.163 | 0 / +0.2 | ADOPTED |

**The shipped configuration (pack 9a) [D].** It equals a stored run on every twin: c0 where there is no blue cup,
single rack on ep12/13, base on 11/21/22. Reported only, not a selection. Source: `scripts/pack9a_config.py` ->
`pack9a_config.json`.
- **Over 15 twins:** mean dAUC **+0.0079**, min -0.0092 (ep12), dMPPE -0.059 cm, dRPE -0.121 cm, dSP-SR 0, dMP-SR 0.
- **Over the 12 twins with pot, lid or rack:** +0.0099, dMPPE -0.074 cm, dRPE -0.151 cm.
- The full 4-object joint c0 (+0.0148 mean, but -0.0240 on ep13) needs the blue cup, so it does not apply to pack 9a.

**Caveats on what the guard covers:**
- **Coupled objects.** The kit's `_align_registered_scene` takes the world rotation from the first non-symmetric
  object and the offset from object 0. Swapping an anchor object therefore moves its partners' frames: pot ep2 -0.0159
  comes from the lid (lid AUC 0.9723 -> 0.9397).
- **[H] The pot's main eval role is untested.** On eval the pot is the rotation anchor of a scored partner in 5 of its
  6 pairs (lid; spoon on eval 3, 5, 6; beige on eval 8). No public pot+spoon twin exists, and ep2 is the pot's only
  informative multi-object twin (verify_1 N2).
- **Lid evidence.** The lid rests on one informative twin (ep2, its build episode). On ep0 the lid's AUC is 0 in every
  run, because its track failed.
- **In-sample twins.** Every mesh was fitted on some of its own twins. Out-of-sample [D]:
  - pot without ep41: +0.0036 / -0.0159;
  - rack on 26 and 31: +0.0323 / +0.0034;
  - blue cup without ep21: +0.0175, dRPE +0.016.
- **Blue cup ep21** (moot for 9a). Raw registration of 146.9 deg on 1 of 5 seeds, and dRPE +0.747 cm. [H] A spin about
  the cup axis; testing this reads the scan and was not run.
- **What the board does differently.** It scores simulator rollouts against the hidden scans, with the host's anchor
  and sampling. Its AUC change can differ in sign from the twins' change (precedent: the 26 Oct pitcher swap).
- **C0a diagnostic** (`cdo-sprint/C0a-diag/`, post hoc). ICP-aligning C0 onto library_v3 lowers registered AUC (the
  rack would fail the guard). So the meshes ship as fitted.

## 6. Provenance and flags

**F1. Marker balls, pot, lid and rack (verify_0 B1; added in stage 4).**
- **The source of the prior.** `prim_potlid.py` `markers_from` (also used by `prim_rack.py`) uses a fixed radius
  `MK_R0 = 7 mm` and accepts a free fit only in 5-9.5 mm. Both values are scan-derived: spoon template note 17 is a
  marker catalogue fitted on the public scans. The audit is in the work log at 27 Oct ~17:20 UTC, blocker 1, and the
  code comment was corrected on 29 Oct in `14eaf37`.
- **What the audit concluded.** These objects' 27 Oct scan passes are "provisional until rebuilt with a generic ball
  rule". Stage 1b closed on 30 Oct without that rebuild.
- **What the meshes contain [M].**
  - Pot: 3 balls at 7.00 mm (prior) and 1 at 6.94 mm. The build record shows free fits of 11.96, 27.88 and 3.67 mm
    replaced by 7 mm.
  - Lid: one floating ball at 7.00 mm.
  - Rack: one ball at 7.00 mm (its free fit was 9.51 mm) and one at 5.22 mm.
- **Ball positions** come from our points. Only the radius and the acceptance window are priors.
- **Falsifier.** Rebuild with no balls or with generic free-radius balls (rack `joint_nomk` exists), then compare
  obs_fidelity. A CD-O number needs a new pre-registered scoring.
- **Correction.** verify_0 dates the audit 29 Oct. It is the 27 Oct entry; 29 Oct is the comment fix.

**F2. Thickness.** Lid T_LID and rack T_WALL are 2.5 mm, the values that leaked from the scans into the first brief.
- The 27 Oct clean-up round passed at 1.5, 2.5 and 4.0 mm (worst lid 0.224 / 5.06; worst rack 0.458 / 6.23).
- 2.5 was its pre-registered default (grid midpoint), not a post-hoc pick.
- GT-free fidelity prefers the lid at 1.5 mm (1.436 vs 1.686 mm).
- Lid thickness evidence: the C0 lid spans -5.0..+37.4 mm along the normal; our ep2 lid points span -5.3..+37.9 mm.

**F3. Selection.**
- The C0 object set was chosen with [D] scan scores. Pot, lid and rack passed a scan pass-rule pre-registered on
  27 Oct; the blue cup had no such rule, and its selector was written after its lathes were scored.
- So C0 is not "chosen GT-free" without this qualifier and F1.

**F4. Provenance tier.**
- "Same tier as library_v3" means fitted to our stereo points along library_v3-anchored tracks. library_v3 itself was
  fused along scan-templated tracks, which is an open organiser question.
- These are public-built meshes reused for eval. The owner's 22 Oct decision asks for eval meshes re-fused per eval
  episode, which is what E0 does.
- The blue-cup points came from the perc2m own-mesh tracks.

**F5. Frame and format [M].**
- Rigid ICP onto library_v3:
  - pot ~2 mm / ~1 deg;
  - lid ~2.5-3 mm / ~1.3 deg;
  - rack ~2.1 mm with a real ~2.3 deg rotation;
  - blue cup 6.7 mm / 2.6 deg, mostly along its axis, so "same frame" is not confirmed for it.
- After the kit budget:
  - pot 4096 faces, watertight, 5 bodies;
  - lid 4096 faces, watertight, 2 bodies;
  - rack 2356 faces, watertight, 3 bodies;
  - blue cup 4096 faces, **not watertight**, 11 bodies.
- The floating balls are known construction defects. The kit never checks watertightness, and the kit encode and
  decode pass for all four.

## 7. Open decisions (owner / score session; listed for the orchestrator)

1. **F1, before the pack 9a upload (~20:30 UTC).** Ship pot, lid and rack with the scan-derived balls, or hold them
   until a no-ball or generic-ball rebuild?
   - The rebuild is GT-free and CPU-only. Any CD-O number for it needs a new pre-registered scan scoring.
   - The pack notes on focused-pascal's side should carry F1 as well.
2. **Blue cup.** Include the held-back C0 cup (board CD-O -0.032 more [E], 0.367 -> 0.334), or wait for the E0 eval-built lathe (planned).
3. **Compliance (F4)**, and acceptance of the 2.5 mm thickness flags (F2).
4. **Optional.** The ep21 spin-vs-tilt diagnostic for the blue cup reads the scan and needs its own go-ahead.
5. **Outside C0 (E0).** `cdo-sprint/E0/jobs/frozen/.../prim_potlid.py` still has `MK_R0 = 7 mm` under the old comment
   "our own stereo". E0's eval-built pot, lid and rack inherit F1 unless they are built without balls or with generic
   balls, and the E0 PREREG does not mention it. Tell E0 before its box runs.

## 8. Failures, deviations, corrections
- **Run failures:** none. 51/51 guard runs; stage 0 downloaded 15/15 parquets with no failure; no re-runs.
- **Deviation 1.** The packing set drops the adopted blue cup (§2), against PREREG §5.
- **Deviation 2** (verify_handoff). Pack 9a files were sent before the AUC verdict; the verdict came back positive.
- **Fixed in stage 4.**
  - F1 was missing from every C0 document. It is now in `MANIFEST.json` flags, `AUC_RESULTS.md`, the
    `meshes/library_c0*` READMEs and here.
  - The C0-final statements disagreed. `MANIFEST.json` `status` and `c0_final` now state the guard verdict and the
    packing set.
  - The library READMEs no longer claim the same frame for the blue cup. The rack sha256 (16) typo is fixed, and they
    now point to this file.
- **Corrections, without editing the frozen files.**
  - PREREG.md says "Written ~15:40 UTC". It was committed at 15:32:36 and pushed at 15:32:38, before stage 0 started at
    15:34:15.
  - AUC_RESULTS says load ~11; NOTES says ~13.
- **Not done.**
  - No rebuild for F1 (needs a decision).
  - No message to the owner, score session or focused-pascal from this stage (the orchestrator relays).
  - No new scoring of any kind in stage 4. `pack9a_config.json` only recombines stored run JSONs.
