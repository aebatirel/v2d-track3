# C3: shape-score-only variant on top of pack 12c, from already-scored pre-registered candidates (2026-11-02 ~09:20 UTC)

**Context.** Pack 12c (12b plus the C0 blue cup) is live: CD-O 0.30008 (was 0.33232), rank 11th; AUC 0.84738.
keen-heisenberg (08:46 UTC): the owner wants to push; asked for another clean, pre-registered CD-O gain.
Leaders are at 0.21-0.29.

**Rule (written now, post hoc; no new scoring, nothing tuned).**
- Candidates: only the single pre-registered output per object of an earlier track, already scored once [D].
- Each must pass that track's pre-registered CD-O gate.
- Each must beat the shipped 12c mesh's [D] CD-O by >= 0.02 cm.
- The AUC/ADD pose gates are dropped for a CD-O-only submission, because each board keeps our best submission. This is
  the same logic as 12c, accepted by keen-heisenberg at 08:55 UTC.
- Labels: [D] public-scan diagnostic, [M] measured without GT, [E] estimate.

## Tier A: clean (recommended)
Source track: C1 T3 generate-then-fit. PREREG 2d2a8ee was pushed before scoring; there was one fitted mesh per object, each
scored once (`C1/T3-gen-fit/RESULTS.md`).

### White pot (6 pairs: eval 1, 3, 5, 6, 8, 28)
- Mesh: `C1/T3-gen-fit/meshes/white_pot_t3fit.glb`, md5 b19b2e2876945cba4d932ad531f049ce.
- Replaces library_c0/c0x white_pot, md5 0264da83fc0e396c652a43d282dbc0ea.
- [D] CD-O 0.3417 -> 0.3112.
- Board effect [E]: -0.0051.
- T3 gate: WIN. Pose guard: failed (mean dAUC -0.0099, min -0.042 ep45).
- Frame vs C0 pot [M]: ICP 1.65 mm / 0.53 deg; surface median / p95 2.3 / 9.1 mm.

### Water pitcher (1 pair: eval 20, slot 1)
- Mesh: `C1/T3-gen-fit/meshes/water_pitcher_t3fit.glb`, md5 61503a91d787ed0643ef40699805d1d0.
- Replaces library_v3 water_pitcher, md5 fc824fc5b0a9325c91b630c19ba32677.
- [D] CD-O 0.8942 -> 0.7226.
- Board effect [E]: -0.0048.
- T3 gate: CD-O ok; ADD failed (add_med 33.0 mm), so pose boards on eval 20 are at risk.
- Frame vs library_v3 [M]: ICP 2.76 mm / 2.15 deg; surface median / p95 4.3 / 23.3 mm.
- Not watertight, 7 bodies.

### Totals
- **Tier A total [E]: CD-O about 0.300 -> about 0.290.** By the 31 Oct table (0.297 -> 10th, 0.282 -> 6th), that is
  about 8th-9th [E].
- **Excluded: the mini dust pan.** The T3 fit beats the shipped T2 pick by only 0.005 cm (0.2594 -> 0.2541, board
  -0.0003), below the 0.02 margin.
- Both meshes have 4000 faces (within the kit budget) and were scored at transform none. A payload swap, as for 12c.

## Tier B: GT-informed selection (owner decision only; same qualifier as the 12c blue cup)
Each of these was picked as the best of many candidates by public-scan score:
- water_pitcher `gen/hy21/ep22_water_pitcher_k174_s42`: 0.378.
  - Best of the generator seeds; s7 scored 0.570.
  - Worth -0.0096 beyond tier A.
  - Needs placing in the body frame and one scoring.
- mini_sweeper part program P1: 0.2225 vs 0.317.
  - Worth -0.0053.
  - Two of its rules changed after a scan comparison (`diag-2026-10-30/sweeper/README.md` section 6).
- plastic_dish_rack `dev1/ep31_full`: 0.419 vs 0.456.
  - Worth -0.0052.
  - Best of the primitive fits.
- wooden_piece_1 / wooden_piece_2 occupancy fits: worth -0.0025 together.

Tier B total [E] beyond tier A: about -0.023, which gives about 0.267. It reads public ground truth in the selection.
Not recommended without an explicit owner yes.
