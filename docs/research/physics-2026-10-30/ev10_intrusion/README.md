# Eval 10 cup nest: intrusion diagnostic (31 Oct 2026, CPU)

**Diagnostic only, not contract-valid.** No ground truth was read and no score was computed. `tools/intrusion.py`
refuses both mesh sets, because the reconstructed provenance chain contains `make_assets(library_v3)`, which is on its
deny-list. `scripts/intrusion_diag.py` runs the tool's own `main()` and records the deny-list hits instead of
enforcing them. Commands, machine and paths are in `RUN_RECORD.txt`; the scripts are in `scripts/`. The large `.npz`
outputs (46 MB) stayed in the scratchpad, and `scripts/` regenerates them.

**Reference:** `runs/20261026-gl10A2-5e0e100/refs/glockt/ep10/.../ref_gl_ilc.parquet`, md5 `1a5003d9…`, which
matches. The library_v3 cups and `meshes/carve/ev10` are git-identical to the run commit 5e0e100.

**Mesh sets:**
- **A:** the carved pieces, `meshes/carve/ev10`.
- **Bm:** plain library_v3 meshes, using an exact winding-number SDF.
- **Bd:** the library_v3 `collision_decomp` pieces. Not usable: one blue piece fills the cavity, so the union is
  2.19× the solid volume.

## Results [M] (on the reference poses, f0–160)

| Range | A: carved | Bm: plain library_v3 |
|---|---|---|
| f0–46 | no intrusion | no intrusion |
| f47–99 (starts f77 / f74) | 22 frames; max depth 2.5 / 4.9 mm; ≤ 24 cm³ (median 8) | 26 frames; ≤ 81 cm³ |
| f100–117 | 18 frames; 18–36 cm³ (median 29); max depth ≤ 4.9 mm; push 49–84 mm straight along the axis (blue DOWN relative to beige) | 72–94 cm³; separating needs 13–16 cm vertically |
| f118–160 | 43 frames; 3–33 cm³ (median 14); push 4–81 mm (median 16) | 43 frames; 68–93 cm³ |

**Why A still intrudes:**
- The cavity is too narrow, not too shallow.
- At f110, the beige cup's outer radius exceeds the carved blue cavity radius by ~5–7 mm (median) at depths −80 to
  −40 mm. For example, at −80 mm the beige radius is 36.6 mm and the cavity's is 30.2 mm.
- At f140 the beige cup sits higher, and the mismatch drops to about 0–1 mm.
- The depth figures understate the clash, because the carved inner wall is 3 mm thick.
- The blue cup's outer radius at −85 mm is 40.8 mm, so a cavity of 38 mm radius would still leave a wall of
  about 2.8 mm.

**Floor:**
- **A:** the carved floor is 3.6 mm above the blue cup's base. The beige cup sits on it at f100–117 (gap −1.4 to
  +7.5 mm, median −0.1) and floats 2.5–27 mm above it (median 13) at f118–160.
- **Bm:** the library blue cup's inner floor is 66 mm above its base. The beige bottom sits 38–68 mm below that
  floor, so the track nests the cups far deeper than library_v3 allows.

**Blue cup rise:** the track's +3.1–3.7 cm rise of the blue cup is **not** explained by penetration avoidance. Every
separation in A needs the blue cup to go down relative to the beige.

## Reading [H]

- **H-nest-a:** the carved ev10 blue cup fixes the floor problem (Bm's 66 mm false floor). The remaining clash is the
  lower cavity's radius: about 6 mm too small over the bottom ~50 mm.
- **Falsifier for H-nest-a:** widen the carved cavity below −40 mm to the beige cup's radius plus ~1 mm (≈ 38–40 mm;
  the beige maximum there is 37.1–38.8 mm), keep the 3.6 mm floor, and rerun this diagnostic. Intrusion at f100–160 should fall to ≲ 2 cm³ per frame.
- **The blue cup's rise has another source:** perception or ILC, not contact.

## Correction (31 Oct 14:45 UTC): H-nest-a is falsified

focused-pascal's pre-registered test (PREREG 3f058d2, write-up `docs/research/work/perception-sprint-20261031/ev10w/README.md`
on claude/focused-pascal-2nz9s1, 334393e) reproduced the numbers above exactly. Their reading is the one that holds:

- **My radius comparison used the wrong axis.** `radii.py` and `gap.py` measure about the world vertical. The carved
  cavity's lathe axis is tilted 2.37° and sits 5.9–6.35 mm from it near the bottom. About the lathe axis, the blue
  cup's outer radius below the seat is 34.4–36.6 mm, not 40.8 mm. "Beige radius + 1 mm" would therefore lie outside the
  blue cup's own wall, and the "cavity too narrow" reading above is wrong.
- **The intrusion is a pose offset.** 60 of 61 nest frames intrude on one side only, always in the same direction.
  The beige cup's axis is 5.4 mm (median) off the cavity axis. Placing the beige coaxially (a post-hoc check) cuts the
  median intrusion from 29.1 to 3.9 cm³ (f100–117) and from 14.5 to 0.04 cm³ (f118–160).
- **The widened cavity fails both gates.** ev10w fails G1 (max 30.2 cm³) and G2: the beige sinks ~11 mm on
  hands-off frames.
- **Still valid from above:** the floor findings (library_v3's 66 mm false floor; the carved floor is fixed) and "the
  blue cup's rise is not contact".
