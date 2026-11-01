# ev10w: widened eval-10 blue-cup cavity — results (31 Oct 2026, CPU, $0)

Labels: [M] measured here, [E] estimate, [H] hypothesis. Pre-registration: `PREREG.md`, written 12:58 UTC and
committed in 3f058d2 before any ev10w number existed. Its sha256 is `45baf74c…`, unchanged since then.
Everything below is GT-free. Eval 10 has no ground truth, and nothing here reads mocap or `observation.objects`.
No GPU, Vast or Kaggle was used.

## Verdict
**NOT-GEOMETRY, and ev10w FAILS both gates. ev10w is not used.** The packed eval-10 policy keeps `meshes/carve/ev10`,
which is unchanged.

- **M2 (diagnostic gate): NOT-GEOMETRY on both of its criteria [M].**
  - The f100–160 intrusion is one-sided in 60 of 61 frames.
  - A rigid motion of the beige cup within 1 cm / 3° brings it to ≤ 2 cm³ in 30 of 31 frames (median 4 mm, 0°).
  - The beige cup's axis sits 4–7 mm off the blue cavity's axis (median 5.4 mm at the floor) and is tilted 1.6°
    (median) relative to it.
  - If the beige is made coaxial (post hoc), it fits ev10's cavity: f118–160 median 0.04 cm³.
- **The exception case does not rescue it.** The PREREG allowed a widening below the seat line alone if it passed
  both gates. It fails both:
  - **G1 (intrusion ≤ 2 cm³ on every frame f100–160):**
    - gl10A2 reference: max 30.2 cm³, 60 of 61 frames over 2 cm³ (ev10: 36.4 cm³, 61 of 61).
    - V4p track: max 11.4 cm³, 19 of 61 frames over (ev10 on V4p: 12.3 cm³, 19 of 61).
  - **G2 (settle):** 29 of 61 frames pass. The gate needs at least 55, and at least ev10's 41. On the hands-off
    frames the beige sinks 11.6 mm (median) into the widened cavity, which is the sink M3 predicted.
- **H-nest-a as worded cannot be built.**
  - Its target radius is the beige radius plus 1 mm: 40.7–42.4 mm about the blue cup's lathe axis.
  - That is outside the blue cup's own outer wall, which is 34.4–36.6 mm there.
  - So the pre-registered 1.5 mm wall cap binds in all 19 bins.

**Reading [H]:** the nest intrusion is a relative-pose (track) error, not a narrow cavity. This goes to the V4p /
perception side. See the last section for the falsifiable next step.

## 1. Reproduction of the Embodiment session's baseline (mesh set A = `meshes/carve/ev10`, packed gl10A2 reference) [M]
- **Reference:** `runs/20261026-gl10A2-5e0e100/refs/glockt/ep10/processed/sequence_id=t3_ep010/robot_name=sharpa_wave/ref_gl_ilc.parquet`.
  - Fetched with one `hf_hub_download` (`scripts/dl.py`); no listing.
  - md5 `1a5003d94852c275519066645a1b9869` (matches).
- **Their code:** commit 2a11301, extracted with `git archive` into the scratchpad; this repo's branch was not switched.
  - `tools/intrusion.py` was used from the scratchpad copy and was **not** added to this repo.
  - My edits to their scripts are in `scripts/from_2a11301.patch`:
    - the path to that copy;
    - a `NOPUSH=1` switch that skips the push search, used for the new cells only.
  - The deny-list hits (`library_v3`) are recorded, not enforced, as in their wrapper.
- **Result: exact match.**
  - Per-frame intrusion volumes match their `ev10_intrusion_per_frame.csv`: maximum absolute difference 1.7e-6 cm³
    (beige-in-blue) and 1.5e-6 cm³ (blue-in-beige).
  - Floor gap matches to ≤ 0.005 mm (the CSV's rounding).
  - Max depth: 4.91 vs 4.912 mm.
  - `radii.py` output is byte-identical to their `radii_A.txt`.
  - Ranges match their README table:

| range | intruding frames | intrusion cm³ (min / median / max) | floor gap mm (min / median / max) |
|---|---|---|---|
| f47–99 | 22 | 0.01 / 8.05 / 23.75 | — |
| f100–117 | 18 | 18.47 / 29.11 / 36.40 | −1.39 / −0.14 / 7.52 |
| f118–160 | 43 | 3.14 / 14.48 / 32.57 | 2.51 / 13.07 / 27.32 |

- Max depth ≤ 4.91 mm. `results/repro_check.json`.
- **Not reproduced:** their push search (intrusion_diag's direction search on the reference poses). I stopped it after
  23 min of CPU because it was not needed for any PREREG reading. The volumes, depths, floor gaps and radii above match.

## 2. M2 and taper (before building) [M]
**Axes.**
- The carved blue cavity is built on the approach-2 lathe axis. That axis is tilted 2.37° from the blue file z. It
  passes (2.8, 4.3) mm at the mouth and (−0.9, −0.8) mm at the base (review F3: the verifier measures (−1.0, −1.1) mm
  at the floor).
- `radii.py` and `gap.py` measure about a vertical axis at (2.6, 4.1) mm. That axis is up to ~5.7 mm off the cavity
  axis at the bottom (review F3: 5.9 mm at h −75 mm and 6.35 mm at the floor; this strengthens the reading).
- About that vertical axis, the maximum outer radius over azimuths near the bottom is 40–41.5 mm (`out/geom_ev10.json`
  in the scratchpad). This is consistent with their "blue outer 40.8 mm".
- About the lathe axis, the blue cup's outer radius at h −47 to −83 mm is 34.4–36.6 mm.
- M2 therefore uses the lathe axes of both cups (`scripts/m2.py`). Results are in `results/m2_gl_ev10.json`.

**Azimuthal distribution (f100–160).**
- 60 of 61 intruding frames are one-sided, meaning at least 75 % of the volume lies in one 180° half.
- The half-plane fraction has median 1.00 (min 0.67). The resultant length has median 0.83.
- The mean direction is −93° in the blue lathe frame (range −117° to −59°): the same side in every frame.
- Only 39 % (median) of the intruding volume lies below h = −40 mm. A widening below −40 mm cannot reach the rest.

**Relative pose.**

| range | beige axis tilt vs blue axis, median (max) | axis offset at the floor, median (max) | axis offset at h = −40 mm |
|---|---|---|---|
| f100–117 | 2.3° (6.4°) | 7.3 mm (11.0) | — |
| f118–160 | 1.1° (4.7°) | 4.2 mm (9.9) | — |
| f100–160 | — | — | 4.2 mm median (6.8 max) |

- The beige base sits on the carved floor at f100–117: −0.9 to +7.8 mm above it, median +0.1 mm.

**Minimal clearing rigid shift** (`scripts/rigid_shift.py`; every second frame, as the PREREG allows;
`results/rs_gl_ev10_*.json`).
- Search space: tilts of 0–3° in 1° steps at 8 azimuths, combined with translations up to 10 mm (2 mm grid, then a
  0.5 mm refinement).
- I is evaluated on a 0.5 mm occupancy grid. Against the tool's exact I at the reference pose it is off by at most
  0.31 cm³.

| range | frames | cleared to ≤ 2 cm³ | cleared to 0 | translation only: min I (median) |
|---|---|---|---|---|
| f100–117 | 9 | 8 | 0 | 7.8 cm³ |
| f118–160 | 22 | 22 | 14 | 0.30 cm³ |

- Median clearing motion: 4.0 mm, 0°.
- The typical motion is +4–4.5 mm along the blue e2 axis, which is opposite the intrusion. At f100–117 it also needs
  about 6 mm up the axis and a 1–2° tilt.
- Only f100 is not cleared: its minimum I within the bound is 8.1 cm³.

**Coaxial check (post hoc, not in the PREREG; `scripts/coaxial_I.py`, `results/coaxial_gl_*.json`).** Only the beige
cup's tilt and lateral offset from the blue axis are removed; its height and spin are kept.

| mesh set | f100–117 median I: tracked → coaxial | f118–160 median I: tracked → coaxial | frames ≤ 2 cm³ when coaxial (of 61) |
|---|---|---|---|
| ev10 | 29.1 → 3.9 cm³ | 14.5 → 0.04 cm³ | 43 |
| ev10w | 22.9 → 1.8 cm³ | 10.7 → 0.03 cm³ | 52 |

- At least 87 % of the median intrusion is the relative offset and tilt.
- The coaxial residual at f100–117 is the floor: the beige bottom lies 0–1.4 mm below the carved floor there.

**Taper** (`results/taper_seat_gl_ev10.json`).

| cup | taper | dr/ds |
|---|---|---|
| blue outer, whole body | 4.7° | 0.083 |
| blue outer, below h = −40 mm | 2.8° | 0.049 |
| beige carve outer, lower 60 mm | 3.4° | 0.059 |

- Expected sink per mm of radial widening on a tapered seat: about 17–20 mm (the mesh session estimated about 10 mm
  for a 5° taper).
- **Seat line** (coaxial beige, the largest excess above its bottom 8 mm): h = −47.4 mm, median over f100–160. The
  median excess there is −0.2 mm, so the beige just touches.
- **Decision (PREREG rule).** M2 says NOT-GEOMETRY, so ev10w is the exception case: widen below the seat line
  (h < −47.4 mm) only.

**Deviations from PREREG (review F1, F2).**
- The minimal clearing rigid shift was found with a 2 mm grid plus 0.5 mm refinement, not with the diagnostic's own push
  search that PREREG named. The verifier applied each reported motion and recomputed the intrusion exactly: 30 of 31
  frames reach ≤ 2 cm³ (max 1.94; f100 does not clear). The reading is unchanged.
- G2's 90 % bar cannot be met by ev10 either (41/61, 40/61) because f100–117 are hands-on frames. Restricted to the
  hands-off frames f118–160 the verdict is the same FAIL: V4p 4/43 (ev10w) vs 40/43 (ev10); gl10A2 14/43 vs 25/43.
  At the training physics step (10 ms) the verifier finds V4p hands-off ev10 14/15 vs ev10w 2/15 (median sink 10.8 mm).
  Future settle gates should use hands-off frames only.

## 3. How ev10w was built [M]
**Profiles.**
- The approach-2 inputs (`blue_cup_profile.npz`, `blue_cup.json`, `beige_cup_v3_*`) were not on disk. I regenerated
  them with `approach2-scripts/lathe_fit2.py` from `meshes/library_v3` (fcvenv, trimesh 4.12.2).
- Check: rebuilding ev10 with carve.json's exact commands reproduces `meshes/carve/ev10`'s geometry.
  - Every piece is matched at vertex Hausdorff 0.0 mm.
  - COM and inertia are equal to 1e-14.
  - The bytes differ only in vertex/face order and in the order of the CoACD base hulls.
- Profile hashes are in `meshes/carve/ev10w/carve.json`. The files are regenerable, so they are not in git.

**Tool.** `pipeline/lathe_collision.py` has a new opt-in `--inner INNER.npz` option.
- The file holds `h` and `r_in`: the cavity radius per profile bin, NaN meaning the default r − wall.
- It can also hold `band_edges`, which replace the `--band` edges.
- New report keys appear only with `--inner`.
- **Default path byte-identical:** ev10 rebuilt with the original and the modified tool in the same environment gives
  106/106 files with equal sha256 (`results/rebuild_ev10_{origtool,newtool}_sha256.txt`).

**Rule** (`scripts/make_ev10w_inner.py`, output `build/ev10w_blue_inner.{npz,json}`).
- For profile bins with h_diag < −47.4 mm: r_in = min(max(r − 3 mm, R_g + 1 mm), r − 1.5 mm).
- R_g is the maximum, over f100–160 of the gl10A2 reference, of the radial distance of the ev10 beige surface samples
  from the blue lathe axis.
- R_g is 39.7–41.4 mm. The cap binds in all 19 of 19 bins, so the wall is 1.5 mm.
- Band edges are profile bins: [−83.61, −23.61, 38.39, 48.39, 58.39, 68.39, 74.39] mm. That gives 10 mm pieces in the
  widened band.
  - A 60 mm piece would bridge the widened cavity by convexity.
  - The same bridging already makes ev10's lower cavity 1.6–1.8 mm narrower than its nominal r − 3 mm (the verifier
    measures 1.0–1.9 mm, median; immaterial).
- **Defect found and fixed (v0 → v1).** The first build put the band edges between bins, which left 2 mm rings with
  no wall at h −45/−55/−65/−75 mm. The wall probe found it.
  - The v0 readings are kept in `results/v0slots_superseded.json` and labelled invalid.
  - v1 has the same r_in and only bin-snapped edges.
  - Every number in this README is v1.

**Measured geometry** (`scripts/wall.py`, rays about the lathe axis, `results/wall_ev10*.json`).

| measure | ev10 | ev10w |
|---|---|---|
| cavity radius, h −47 to −82 mm | 31.2–32.9 mm | 32.6–34.2 mm (+1.3 to +2.2) |
| wall in that band | 2.9–4.1 mm | 1.4–1.7 mm (min 1.4, median 1.6) |
| blue pieces | 53 | 89 |
| blue volume | 152.9 cm³ | 136.6 cm³ |

- Floor (h −85.1 mm), outer profile and base hulls are unchanged. The beige cup is a byte-identical copy.
- **Inertia** (`inertia.json`, uniform solid, 0.3 kg; `results/inertia_cmp.json`):
  - the COM moves 7.5 mm up;
  - Ixx and Iyy change by −6.3 %, Izz by +3.1 %.
- **M4** (`scripts/m4.py`, `results/m4_ev10*.json`).
  - Each piece was passed through FlashCHORD's own `convex_decompose` with the scene builder's defaults (CoACD 0.05,
    preprocess auto).
  - All 138 ev10w pieces and all 102 ev10 pieces come back as one hull each, with volume within 0.05 % and surface
    deviation ≤ 0.006 mm.
  - The 1.4 mm wall therefore survives as delivered. `make_assets.py --pieces` writes one `<collision>` per piece, and
    FlashCHORD decomposes each shape separately.
- **Pre-existing in ev10 (not changed):** a ~1 mm ring slot with no solid between the last wall bin and the clipped
  base hulls (h ≈ −83.4 to −84.4 mm).

## 4. Falsifier results [M]
**References.**
- **(a)** gl10A2 as packed.
- **(b)** V4p: the gl10A2 parquet with only the two cups' poses replaced (`scripts/v4p_parquet.py`, `results/v4p_mapping.json`).
  - Both have 161 frames with the same index.
  - The cup poses are mapped by one rigid G, fitted on f0–52 (fit residual median 3.1 mm, under the PREREG's 5 mm bar).
  - V4p carries S2's 0.545-frame advance on every frame, so on f0–52 it is not exactly the stored track. My PREREG
    premise said it was; it was wrong, but the bar holds.
  - Intrusion and floor gap depend only on the relative pose, so they do not depend on G. Only the settle's gravity
    direction does: the two candidate fits differ by 0.83°.
- **Control:** the stored track itself, mapped the same way. It matches gl10A2 to 0.97 mm (median), so gl10A2 was built
  from it. The glock/ILC/mkref chain moved the beige by ~3 mm.

**Intrusion table.** Each cell: intruding frames; I median / max over the intruding frames (cm³); max depth; floor gap
median.

| reference | mesh | f0–46 | f47–99 | f100–117 | f118–160 | G1 (max I f100–160) |
|---|---|---|---|---|---|---|
| gl10A2 (a) | ev10 | 0/47 | 22/53; 8.05 / 23.75; 4.90 mm; 123 mm | 18/18; 29.11 / 36.40; 4.91 mm; −0.14 mm | 43/43; 14.48 / 32.57; 4.29 mm; 13.07 mm | FAIL (36.4) |
| gl10A2 (a) | **ev10w** | 0/47 | 22/53; 8.05 / 19.32; 4.90 mm; 123 mm | 18/18; 22.90 / 30.22; 4.91 mm; −0.14 mm | 43/43; 10.69 / 26.89; 4.29 mm; 13.07 mm | **FAIL (30.2)** |
| V4p (b) | ev10 | 0/47 | 26/53; 11.12 / 18.37; 4.91 mm; 122 mm | 18/18; 8.46 / 12.27; 3.91 mm; 30.99 mm | 41/43; 0.01 / 3.89; 2.94 mm; 13.27 mm | FAIL (12.3) |
| V4p (b) | **ev10w** | 0/47 | 26/53; 11.12 / 18.37; 4.91 mm; 122 mm | 18/18; 7.67 / 11.35; 3.91 mm; 30.99 mm | 6/43; 0.08 / 3.03; 2.78 mm; 13.27 mm | **FAIL (11.4)** |
| stored track (control) | ev10 | 0/47 | 26/53; 12.65 / 27.34; 4.95 mm; 118 mm | 18/18; 37.09 / 44.29; 4.91 mm; −3.18 mm | 43/43; 20.89 / 35.24; 4.47 mm; 5.44 mm | FAIL (44.3) |
| stored track (control) | ev10w | 0/47 | 26/53; 12.48 / 22.18; 4.95 mm; 118 mm | 18/18; 30.58 / 38.18; 4.91 mm; −3.18 mm | 43/43; 16.28 / 29.01; 4.47 mm; 5.44 mm | FAIL (38.2) |

Notes on the table:
- **Depth targets missed.** The floor gap and max depth are nowhere near the ≤ ~1 mm target of a clean nest. The depth
  is capped by the 3 mm blue wall and the 7.4 mm beige wall.
- **f0–99 is not worse with ev10w:** max 19.3 vs 23.8 cm³ on (a), and 18.4 for both on (b).
- **V4p's own effect** (ev10 on (a) vs ev10 on (b)):
  - **f118–160 (hands off):** V4p's physics-seated beige is coaxial (offset 0.13 mm, tilt 0.4°) and nearly
    intrusion-free (median 0.01 cm³).
  - **f100–117 (hands on):** the beige keeps its tracked world pose 31 mm above the carved floor. It is still 7.8 mm
    off-axis and one-sided, at 3–12 cm³.
- **`radii.py` on V4p** (`results/radii_v4p_ev10.txt`), beige lowest point:
  - f110: −54.6 mm (gl10A2: −85.1);
  - f140: −71.9 mm (gl10A2: −66.8).
  - Its "excess" columns still use the vertical axis, so they overstate the mismatch. See section 2.

**M3 settle (G2; `scripts/settle_m3.py`, `results/settle_*.json`).**
- Setup: plain MuJoCo 3.8.1. The blue cup is static at its reference pose. The beige cup is free with its `inertia.json`.
  Gravity −z, dt 2 ms, 2.0 s, default contacts, no hands. Every frame f100–160 is settled independently.
- A frame passes if |dz| ≤ 4 mm and tilt ≤ 5°.

| reference | mesh | pass f100–117 / f118–160 / all | dz median (min) | tilt median (max) | lateral median |
|---|---|---|---|---|---|
| gl10A2 | ev10 | 16/18 / 25/43 / **41/61** | +0.5 (−15.7) mm | 1.7° (6.4°) | 3.5 mm |
| gl10A2 | **ev10w** | 15/18 / 14/43 / **29/61** | −2.7 (−25.8) mm; f118–160 −11.6 | 1.8° (6.5°) | 3.5 mm |
| V4p | ev10 | 0/18 / 40/43 / 40/61 | −2.1 (−20.6) mm | 0.4° (5.6°) | 0.5 mm |
| V4p | ev10w | 0/18 / 4/43 / 4/61 | −12.7 (−31.7) mm | 0.6° (5.2°) | 0.6 mm |

- G2 for ev10w: 29/61 < 55 needed and < ev10's 41, so **FAIL**.
- The hands-off beige sinks 11–12 mm toward the floor in the widened cavity: the M3 mechanism.
- On ev10 the solver mostly moves the beige 3.5 mm sideways, toward coaxial; M2 reads the same offset.
- V4p at f100–117 has the beige 31 mm above the floor (hands on), so it falls about 17–32 mm with both meshes.

**Rest robustness** (FlashCHORD harness, `tools/carve_fc_test.py` on the gl10A2 tree; hands parked, no drive;
`results/final_table.json` → `rest`; reported, not gating).
- Both mesh sets fall over in 2 of 6 rest starts:
  - ev10: beige at s4, blue at s6;
  - ev10w: beige at s0 and s8. The beige pieces are identical to ev10's.
- The harness is chaotic at this level. It also differs from the 26 Oct carve.json numbers, which had 0/6 falls on the
  older eval-10 tree.
- The blue cup alone never falls with ev10w (max 14.7°).
- The nested pair resting hands-free from f120 stands with both: blue 19.7° / 19.8°, beige 11.2° / 10.4°.

## 5. Risks if ev10w (or any widening) were used anyway
- **Thin wall [H]:** 1.4 mm. MuJoCo contacts are soft and discrete in time (training sim_dt 10 ms, 5 substeps). A
  hand-driven beige could tunnel through a 1.4 mm wall. This was not tested.
- **Sink [M]:** 11–12 mm on hands-off frames. This is the opposite of a stable nest.
- **Stability:** the blue cup's COM is 7.5 mm higher [M]. The rest harness is too noisy to resolve the effect.
- **Cost [E]:** 89 vs 53 blue pieces, so more contact pairs and slower steps.
- **Inherited [M]:** the ev10 1 mm slot above the floor is present in both.

## 6. Next step for the track side (hypothesis, not run)
**[H] H-coax.**
- Extend V4p's physics seat, or a coaxial projection of the beige onto the blue cavity axis, to the hands-on nest frames
  (f100–117), keeping the hand-held axial height.
- Prediction: the nest becomes nearly intrusion-free with the unchanged ev10. Post hoc on gl10A2, coaxial projection
  alone gives 43/61 frames ≤ 2 cm³; the residual is the 0–1.4 mm floor overlap at f100–117.

**Falsifier.**
- With ev10 and that track, fewer than 90 % of f100–160 frames reach ≤ 2 cm³; or
- the ep11 rollout gate (control vs variant, 2 seeds, ≥ +0.05 vs mocap, as in the mask10 plan) fails.

The ~5 mm offset is in the reference's relative pose. Our two collision copies' axes come from lathe fits of our own
meshes, so part of it could be a mesh-frame offset rather than a tracking error. This is not separable here
(GT-free).

## 7. Exact commands, machine, code, outputs
- **Machine:** this Claude cloud container (4 CPU), 12:58–13:35 UTC, $0.
- **Code:**
  - repo HEAD 3f058d2, plus the uncommitted `pipeline/lathe_collision.py` `--inner` option (sha256 `5892cbdc…`;
    original `6d517afc…`);
  - this folder's `scripts/`;
  - the Embodiment session's commit **2a11301** (`tools/intrusion.py` and their scripts, used from a scratchpad copy).
- **Environments:**
  - fcvenv: MuJoCo 3.8.1, trimesh 4.12.2, FlashCHORD at the pinned `video_to_data` 7eb9721;
  - `FLASH_CHORD_CACHE_DIR` set to scratchpad dirs.
- **Scratchpad** `S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/ev10w`:
  - `dl/` (reference), `prof/` (profiles), `build/` (ev10w v1), `v0slots/` (superseded v0), `sim/`, `assets/`;
  - `out/` (all outputs, including `DIAG_*.npz`), `logs/`;
  - V4p and control parquets in `v4p/` and `trk/`.
- **Order run:**
  1. `scripts/dl.py`
  2. `make_manifest_ev10.py`, `make_prov.py`
  3. `intrusion_diag.py REF sim/ev10/ep10/r0 out/DIAG_ev10_gl.npz prov_reconstructed.json`
  4. `gapA.py`, `summarize.py`, `repro_check.py`, `radii.py`
  5. `m2.py`, `taper_seat.py`, `run_rs.sh` (`rigid_shift.py`)
  6. `lathe_fit2.py` ×2 and the ev10 rebuild (both tools)
  7. `make_ev10w_inner.py`, `lathe_collision.py --inner`
  8. `v4p_parquet.py` (V4p and control)
  9. `run_cells.sh` (ev10 cells), `run_ev10w.sh` (ev10w cells, settles, M4, M2)
  10. `run_settle.sh` (ev10 settles)
  11. `run_rest.sh`, `run_rest2.sh`
  12. `wall.py`, `coaxial_I.py`, `final_table.py`

  Each script's header has its usage. `carve.json` has the build commands.
- **Repo outputs:**
  - `meshes/carve/ev10w/{blue_cup,beige_cup,carve.json}`;
  - this folder: `PREREG.md`, `README.md`, `build/`, `results/` (small JSONs; no npz over 3 KB), `scripts/`.
