# E0: C0's mesh methods rebuilt on the eval episodes (CD-O sprint)

Status, 2026-10-31 ~18:30 UTC: **packaged and verified, not scored.** There is no eval ground truth, so E0 cannot be
scored. The pre-registered rule (PREREG.md sections 4 and 6) recommends **E0 for all four objects** (pot, lid, rack,
blue cup), with no PREREG rule flags. That is the rule's output, not a ship decision: **two ship gates are open (G1, G2
below) and need the owner or the pack builder.** The owner decides what ships.

Labels: [M] measured, [D] quoted from an earlier record, [E] estimate, [H] hypothesis.

Why E0 exists. The owner, 31 Oct 15:50 UTC: "if the method of mesh creation better just recreate the meshes in the eval
and use that". At 16:40 UTC he asked whether Vast machines could make it faster. The box run took about 15 minutes; the
prep had estimated 40-60 minutes.

## 1. What E0 is

- **Same methods, same settings.** C0 swaps four objects with methods built on public episodes: pot, lid and rack are
  kit-of-parts primitive fits, and the blue cup is an observed-point lathe. E0 runs exactly those methods with the same
  frozen settings on every eval episode where the object appears. The code is the public code of commit 2971a10, frozen
  in `jobs/frozen` (SHA1SUMS). The commands are the public ones: `prep_obs.sh` obs_points, `run_fit.sh`,
  `run_rack.sh`, the clean-up round's lid command and the lathe defaults (g1).
- **Pre-registered.** PREREG.md fixes the inputs, the code, the commands, the exclusions, the pick and the
  recommendation rule. It was committed at 16:08 UTC (705652a), before any eval candidate existed, and is unchanged since.
- **Inputs (eval inference only).** Our eval tracks (`poses.npz`, `result.json`), the eval cam_a videos, FoundationStereo
  eval depth (`cache/depth/eval`), the OAK factory calibration, the kit's `mesh_budget.py`, and library_v3 (ROI,
  `--others`, frame check). Hands were made on the box with MediaPipe `hands_mp.py`, as for the public runs. Nothing
  read a scan, mocap, a parquet pose field or an `*_align` file (verify_0 C1, C2).
- **Pick.** Per object, the candidate with the lowest obs_fidelity (sum_mm on all eval points of the object) after the
  exclusions. That one mesh ships on every eval pair of the object.
- **Recommendation rule (section 6).** Pot, lid and rack: E0 unless C0 < 0.85 x pick. Blue cup (C0's cup was never
  shipped): E0 unless library_v3 < 0.85 x pick.

## 2. Picks and rule result [M; fidelity in mm, in-sample for E0]

Fidelity is GT-free and is not CD-O. On public data its Spearman with CD-O was 0.85 for the pot and 0.5 for the cup.

| Object (eval pairs) | E0 pick | Fidelity E0 / C0 / library_v3 | Runner-up | Eligible | Ratio for the rule | Rule result |
|---|---|---|---|---|---|---|
| white_pot (6: eval 1, 3, 5, 6, 8, 28) | pot/ep3/fit | 2.922 / 2.914 / 3.881 | ep3/nostem is byte-identical; first different mesh ep3/thick 3.077 | 18/24 (6 tsdf not watertight) | C0/pick 0.997 | E0 |
| white_pot_lid (1: eval 1) | lid/ep1/t2.5_fit | 1.675 / 1.772 / 5.186 | none eligible (t2.5_tsdf 1.787, not watertight) | 1/2 | C0/pick 1.058 | E0 |
| plastic_dish_rack (5: eval 14, 15, 16, 28, 30) | rack/joint/joint (joint fit over the 5 episodes) | 6.419 / 6.245 / 5.881 | joint_nomk 6.432 | 12/12 | C0/pick 0.973 | E0 |
| blue_cup (5: eval 10, 14, 20, 32, 33) | cup/ep32/g1 | 2.646 / 2.723 / 2.906 | ep32/g0 2.664 | 11/11 | v3/pick 1.098 (C0/pick 1.029, reported only) | E0 |

- The box's `jobs/e0_select.py`, the packager `scripts/e0_package.py` and verify_0's own recompute are three separate
  implementations of sections 4 and 6. All three agree on every pick, eligible set, exclusion and recommendation
  (verify_0 C6).
- **Pot and rack do not beat C0, even in-sample.** They reach E0 only through the 15 % margin.
- **Rack:** library_v3 has the lowest fidelity of all 14 rack meshes, on all points and on eval 14, 15, 16 and 28. The
  rack rule compares only against C0, so this is a reviewer note, not a rule flag.
- **Blue cup:** eval 10 (blue cup nested in the beige cup) is the pick's worst episode: 7.748 mm, against 5.624 mm for
  eval 10's own build.

## 3. Open ship gates (need a decision; nothing was changed to close them)

Both are in `MANIFEST.json` (`ship_gates`; each E0 pair lists the gates that apply to it).

**G1. Scan-derived marker-ball prior: pot, lid and rack (verify_0 B1).**
- The frozen `prim_potlid.py` (also used by `prim_rack.py`) uses a fixed ball radius MK_R0 = 7 mm and accepts a free
  sphere fit only inside 5-9.5 mm. Both values were measured on the public scans (C0b AUDIT ids 12 and 13).
- What the picks keep [M]:
  - pot: 2 balls at the 7 mm prior (free fits 7.34 and 32.52 mm);
  - lid: 1 free 7.74 mm ball, accepted only because it falls inside the scan window, and 1 cluster of 12.07 mm set
    to 7 mm;
  - rack: 2 balls at 7 mm (free fits 6.52 and 6.24 mm). The rack's in_basin rule rejected 4 more clusters; that rule
    is suspected to be scan-influenced (C0b AUDIT id 101).
- The owner's "Ship 9a, flagged" covers the C0 meshes in pack 9a only.
- **Needs:** an explicit owner decision before E0's pot, lid or rack ships. The alternative is the scan-free E0b
  rebuild (C0b PREREG section 9; C0b box running since 18:22 UTC). The blue cup is a lathe with no marker balls and is
  not affected.

**G2. The packed mesh also drives the five pose boards, and E0 has no pose-board guard (verify_1 B1).**
- AUC, MPPE, RPE, SP-SR and MP-SR each register the submitted mesh to the hidden reference and convert the submitted
  poses with that registration (kit `metric_code/track_3/*.py` lines 867-869). `ops/jobs/submit_pack.sh` puts
  `LIB/<object>.glb` into the pose submission. Pack 9a+ moved AUC +0.003, RPE -0.053 and MPPE -0.025 with mesh changes
  only [D].
- C0 had a pre-registered public-twin AUC guard. E0 has none.
- GT-free proxy [M]: the kit's own registration, with library_v3 standing in for the hidden reference. Pot, lid and
  rack move by the same amount as the guarded C0 meshes (anchor shift 5.2-5.4 / 11.8 / 4.6-6.1 mm; rotation up to
  2.2 deg). The blue cup is different: the kit tilts its axis 3.3-7.3 deg, against 0.9-2.3 deg for the C0 cup.
- **Needs a choice:**
  - (a) use the E0 meshes for the CD-O (reconstruction) submission only, and keep the current pack's meshes in the
    pose-board parquet; or
  - (b) first run C0's guard unchanged with the E0 meshes (`../C0/scripts/run_auc_guard.sh`, `guard_eval.py`; 15
    public twins; thresholds mean dAUC >= -0.005, min dAUC >= -0.02, mean dMPPE and dRPE <= +0.2 cm). It ran in about
    35 min at $0 for C0. It reads public scans and parquets for scoring, which E0's eval-only rules exclude, so it was
    not run here.
- [H] For pot, lid and rack, C0's guard result probably transfers. For the blue cup it does not transfer
  automatically. The same gap applies to E0b if its eval-built meshes go into the pose parquet.

## 4. Public context [D: recorded public-scan CD-O, regrouped; no new scoring]

From `context_public.md`. These are CD-O scores (cm) of builds made with the same methods on public episodes. They are
not E0 scores.

| Object | Single-episode builds, median [range] (n) | C0 pick | Own-episode mean | library_v3 |
|---|---|---|---|---|
| white_pot | 0.416 [0.309-0.653] (26) | 0.342 | 0.415 | 0.437 |
| white_pot_lid | 0.218 [0.216-0.220] (2) | 0.220 | 0.220 | 0.421 |
| plastic_dish_rack | allowed config never scored; marked proxy 0.443 [0.422-0.509] (8) | 0.456 (joint) | 0.458 (proxy) | 0.555 |
| blue_cup | 0.327 [0.291-0.364] (2) | 0.291 | 0.327 | 0.523 |

- On the pot, the spread between episodes is large. Two of the 8 public fit builds score worse than library_v3, and
  most of C0's gain came from picking across episodes.
- [E] If the hidden scans match the public ones, the 36-pair board changes against library_v3 by -0.068 cm with C0's
  picks, -0.050 with own-episode means and -0.052 with family medians. The rack terms use the marked proxy.

## 5. Frame and kit checks [M, verify_1]

- **Tracks.** The 14 eval `poses.npz` used are byte-identical to store run `20261025-evperc-4f596df`, which tracked
  library_v3 bodies (job.log: LIB meshes/library_v3). library_v3 is unchanged since then. Pot, lid, rack and cup are
  byte-identical in library_v3 and library_v3x. So the meshes are in the library_v3 body frame.
- **Identity frame check** (PREREG gates, all pass). Centroid offsets: pot 6.475, lid 7.188, rack 9.396, cup 4.038 mm.
  The box's C0 rows reproduce `../C0/frame_check.json` exactly. The centroid gate also measures shape: ICP moves the
  centroids only 3.81 / 0.62 / 3.91 / 3.39 mm.
- **Rigid ICP from identity.**

  | Object | E0 -> library_v3 | E0 -> C0 |
  |---|---|---|
  | white_pot | 0.93 deg / 3.81 mm | 0.95 deg / 1.47 mm |
  | white_pot_lid | 2.22 deg / 0.62 mm | 0.94 deg / 0.55 mm |
  | plastic_dish_rack | 0.96 deg / 3.91 mm | 0.25 deg / 0.80 mm |
  | blue_cup | 4.74 deg (4.44 deg axis tilt) / 3.39 mm | 3.69 deg / 2.79 mm |

- **Blue-cup tilt.** The g1 lathe axes of the five eval cup builds lie 0.93-4.10 deg from library_v3's PCA axis
  (ep32: 2.99 deg). The ep32 pick therefore carries ep32's track tilt into evals 10, 14, 20 and 33. CD-O removes
  rotation and is not affected; the pose boards may be (G2).
- **Lid spin.** The kit treats the lid as half-turn symmetric. The PREREG check does not gate its in-plane spin, but
  measured directly it is fine: in the 48-hypothesis flip test, identity ranks first (7.132 mm against 7.347 mm for the
  half-turn).
- **Units, up axis and handedness are right.** Units are metres. The best upside-down hypothesis is 1.08-2.51x worse.
  Handedness is confirmed on the rack and lid; the pot and cup are mirror-symmetric.
- **Kit path.** `budget_mesh` -> encode -> decode passes for all four objects. Faces 4096 / 4096 / 2638 / 4096
  (pot / lid / rack / cup), watertight, 3 / 1 / 3 / 2 bodies, no quality flags. Maximum decimation deviation is
  1.7 / 1.2 / 2.5 / 2.7 mm. Payloads are 38-86 k characters against the 800 k limit.

## 6. Box: speed and cost [M]

- **Run** `mesh-20261031-e0-b05f001`, code b05f001 (clean). Vast instance 58555214 on offer 57321792: Connecticut US,
  AMD EPYC 7K62, 96 of 96 cores effective, 252 GB RAM, $0.487/h all-in, image vastai/pytorch py313, SETUP=none,
  DISK=80.
- **Timeline (UTC).** Created 16:25:29; job start 16:28:50; `E0-DONE rc=0` at 16:40:22 (11.5 min); self-destroyed, gone
  from `ops/vast.sh show` at 16:40:39. verify_0 confirmed it was still absent at 17:26.
- **Stages.** setup 10 s; inputs plus 21.43 GB eval depth 2.8 min; hands 14/14 2.5 min; obs_points 17/17 2.8 min;
  builds 20/20 2.1 min (the serial rack run took 123 s); fidelity 352/352 28 s; checks 53/53 9 s. Pairs: 17 OK, 0 failed.
- **Cost.** Ledger (session mesh-bold): planned $1.00 before the create; actual **$0.13 [E]**, a clock estimate of
  about 15.2 min x $0.486/h plus download, not a Vast invoice.
- **Results.** HF store `aebatirel/v2d-store` `runs/mesh-20261031-e0-b05f001/results/e0/` (530 MB); local copy
  sha256-checked 1062/1062. Report: `BOX.md`; small results in `box/`.

## 7. Flags (all also in MANIFEST.json)

- **Provenance tier P1.** The eval tracks are `20261025-evperc-4f596df`, templated on library_v3 (gmg SPEC section 3;
  owner decision O1). obs_points also read library_v3 for `--roi` and `--others`. library_v3 is on
  `ops/provenance/denylist.json`, and C0b AUDIT classes it as derived from scan-based work (verify_0 N2).
- **Eval tracks used.** Every observed point comes from our eval tracks (the pack's poses), our eval depth and our
  hands. Each pack episode's poses were not compared to these tracks one by one (verify_0 N7). Evals 8, 14, 32 and 33
  had their references rebuilt on 25 Oct. The frame argument does not depend on this.
- **Thickness 2.5 mm** (lid T_LID, rack T_WALL) is the midpoint of the public clean-up grid, which passed at 1.5, 2.5
  and 4.0 mm. It equals a value that once leaked from the scans. It was not chosen by any eval number.
- **Marker-ball prior** (pot, lid, rack): G1.
- **In-sample picks.** Each pick was chosen on the points it was fitted to; C0 and library_v3 are out-of-sample there.
- **Method qualifier.** The object set and the methods come from C0, which was chosen with public-scan scores (C0
  README F3).
- **Other inherited constants (verify_0 N3, N4).**
  - The pot handle thickness comes from BAR_T0 = 5 mm, a default with no recorded derivation. C0 measured 5.8 mm from
    the side.
  - The blue-cup lathe floor rule was set in response to a scan diagnostic (C0b id 131). In all 5 eval g1 builds no
    floor was observed, so the floor sits at base + t (t = 3.32 mm for the pick).
  - Two scan-valued fallbacks did not trigger: the cup's 3 mm wall fallback and the pot's 4 mm wall fallback.
- **Threads (verify_0 N1).** The box ran with OMP/OPENBLAS/MKL threads = 2. With the 4-core default threads, the public
  rack re-run with the frozen code is byte-identical to the public run (12/12). With 1 thread, faces differ by up to 4
  and fidelity by up to 0.004 mm. This is negligible against the 15 % margin; the thread count is now a recorded
  setting.
- **Depth inputs (verify_0 N5).** The 14 eval depth caches were checked by byte size, not sha256. The other 45 inputs
  were sha256-checked.

## 8. Packing notes

- **Merge per object; do not pack the folders whole.** `meshes/library_e0` and `meshes/library_e0x` are library_v3 /
  library_v3x with four files swapped. Pack 9a+ also ships the C1 beige-cup lathe (evals 8, 10) and the C1 dust pan
  (evals 19, 38). Packing either E0 folder whole would revert those 4 pairs (verify_1 N6). Take E0's objects one by one
  into the current pack library: `library_e0x` for eval 8, `library_e0` for every other pair.
- **Packed files** (byte-identical in library_e0 and library_e0x, and in `meshes/` here):

  | File | md5 | sha256 (16) | Source in `E0/meshes/` |
  |---|---|---|---|
  | white_pot.glb | 858fc4c64b147eb2245bdcced9a29f73 | af321725727cb1d5 | white_pot_eval3_fit.glb |
  | white_pot_lid.glb | 08b65d4f7080e55c6ee81be9fa19cf8f | e3dd5861a5081e44 | white_pot_lid_eval1_t2.5_fit.glb |
  | plastic_dish_rack.glb | 9b8adbe3bbdf09666f604436aa4cade4 | fc67c59baa1cab06 | plastic_dish_rack_eval_joint_joint.glb |
  | blue_cup.glb | b479269e3ee21266db84df8a17bfdc1c | e6c18b2ae40dcdeb | blue_cup_eval32_g1.glb |

- **Pairs.** 17 of the 36 eval pairs carry an E0 mesh: pot 6, lid 1, rack 5, cup 5. All 17 differ from C0 and from pack
  7. The other 19 are unchanged against C0 and pack 7, not against pack 9a+.
- The E0 folders hold no `*.recon.json` files (library_v3 has 10, v3x has 9). No packer reads them (verify_1 N4).
- Packed mesh only. The simulator copies and rollouts stay as they are.

## 9. Files

- `PREREG.md` (frozen rule), `jobs/` (box job, frozen code), `inputs/` (plan, thresholds), `BOX.md`, `box/`.
- `scripts/e0_package.py`: independent re-application of sections 4 and 6, and packaging. Outputs `selection_final.json`
  (PREREG rule output only; its "no flags" refers to rule flags), `MANIFEST.json`, `meshes/`, `meshes/library_e0`,
  `meshes/library_e0x`.
- `scripts/e0_status.py` (report step): adds `ship_gates`, `pose_boards`, `verification`, `provenance_note`,
  `not_a_drop_in`, `status_history` and per-pair `ship_gates` to `MANIFEST.json`. It asserts that every field written by
  `e0_package.py` is unchanged. MANIFEST sha256 went from 3528f561... (3fbc1d1) to 84bfa9a4....
- `verify_0.md` (integrity; 42ab815) and `verify_1.md` (frame and kit; f302485).
- `context_public.md` / `.json` (public context numbers). `NOTES.md` (step log).
