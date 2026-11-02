# C4: multi-seed registration audit of packs 13e/13f, and the 13g adoption verdict (2 Nov 2026)

Rules: `PREREG.md` (section 2 protocol, section 3 rules A/B, addenda 1-4), pushed before each run. All numbers are [D]:
kit registration and CD-O against the public scan, 50 seeds 3001-3050, no eval seed, budgeted reference.
CPU only, $0. Table: `results/audit_table.md`; verdicts: `results/adoption.json`; per-seed records: `results/raw/`.

## Verdict
- **Rules (A)/(B): no candidate qualifies for any object, so the 13f meshes stay and pack 13g is empty.** This includes
  library_v3 and the 30 best existing candidates.
- **Flips:** only the boards flip. Every other shipped mesh is 0/50, with rotation p90 <= 4.9 deg.
  - Board 2 (Tier B occupancy plate): W30 0.34, the only rule-flagged priority.
  - Under a raw-scan reference it also flips at eval 25's own seed (addendum 4 correction). Pack 13f1, by the
    coordinator and focused-pascal, restores library_v3 board 2 (0/50 here; D1 passes in both reference modes per
    focused-pascal).
  - Board 1: W30 0.06.
- **Board 2 variants: none passes rule (B).**
  - Addenda 1 and 3 (GT-free grafts of library_v3 features onto the plate): v1 0.18, v3 0.22, v4 0.12, v5 0.18 W30.
  - The thickness that removes flips costs about +0.05 cm CD-O (v4 0.2163).
- **Observations outside the frozen rule** (not acted on; any rule written now for these meshes would be post hoc):
  - pot `potlid/tsdf/ep43`: same CD-O as shipped (0.3097 vs 0.3107), registration ADD 2.9 vs 6.3 mm;
  - dust pan Pixal3D-MV ep39 s7: CD-O +0.005 (0.2341 vs 0.2291), ADD 4.0 vs 6.1 mm;
  - beige C0b: ADD 3.0 vs 5.8 mm, but CD-O +0.05.
  These could matter for the AUC board through registered scoring.
- **Spoon:** no public scan. The 25 Oct GT-free study found 0/300 flips; its loss is anchor roll (perception lane).

## Predictions (section 4 / addenda)
- H1 cups and lid W30 = 0: held.
- H2 board plates FLIP > 0.10: held for board 2 (0.34); board 1 only 0.06.
- H3 rack ep31 candidates share the 9 mm anchor: held (9.6-9.8 mm).
- H4 no rule-(B) pass: held.
- H5 graft_v2 < 10% flips: falsified (0.70).
- H6 v1 keeps an extra ball: held (2 kept).
- H7 v1 CD-O within +0.005: held.
- H9 thickness matters more than the +1 feature: held.
- H10 v4 W30 <= 0.14: held at 0.12, but the CD-O gate fails.
